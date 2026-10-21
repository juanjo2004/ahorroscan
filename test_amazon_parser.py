from bs4 import BeautifulSoup
from sources.amazon import _parse_eur, _parse_rating, _parse_reviews


HTML = """
<div data-component-type="s-search-result">
  <span class="a-icon-alt">4,6 de 5 estrellas</span>
  <span class="a-size-mini puis-normal-weight-text s-underline-text">(174)</span>
</div>
<div data-component-type="s-search-result">
  <span class="a-icon-alt">4,4 de 5 estrellas</span>
  <span class="a-size-mini puis-normal-weight-text s-underline-text">(3\xa0mil)</span>
</div>
<div data-component-type="s-search-result">
  <span class="a-icon-alt">4,4 de 5 estrellas</span>
  <span class="a-size-mini puis-normal-weight-text s-underline-text">(1,4 mil)</span>
</div>
<div data-component-type="s-search-result">
  <span class="a-icon-alt">5,0 de 5 estrellas</span>
  <span class="a-size-mini puis-normal-weight-text s-underline-text">(8)</span>
</div>
"""


soup = BeautifulSoup(HTML, "html.parser")
items = soup.find_all("div", {"data-component-type": "s-search-result"})
assert len(items) == 4
assert _parse_rating(items[0]) == 4.6
assert _parse_reviews(items[0]) == 174
assert _parse_reviews(items[1]) == 3000
assert _parse_reviews(items[2]) == 1400
assert _parse_reviews(items[3]) == 8
assert _parse_eur("1.234,56 €") == 1234.56
assert _parse_eur("27,99 €") == 27.99
print("OK: parser Amazon rating/reviews/precios, incluyendo formatos 'mil'")



def test_amazon_request_retries_503_then_recovers(monkeypatch):
    from sources import amazon

    class Response:
        def __init__(self, status_code, text="<html></html>"):
            self.status_code = status_code
            self.text = text
            self.headers = {}

    responses = [Response(503), Response(200)]
    sleeps = []

    monkeypatch.setattr(
        amazon.requests,
        "get",
        lambda *args, **kwargs: responses.pop(0),
    )
    monkeypatch.setattr(
        amazon.time,
        "sleep",
        lambda value: sleeps.append(value),
    )
    monkeypatch.setattr(amazon.random, "uniform", lambda low, high: low)

    response, attempts, reason = amazon._request_search(
        "https://www.amazon.es/s?k=teclado",
    )

    assert response.status_code == 200
    assert attempts == 2
    assert reason is None
    assert sleeps == [amazon.RETRY_DELAY_MIN]



def test_amazon_request_gives_up_after_transient_failures(monkeypatch):
    from sources import amazon

    class Response:
        status_code = 503
        text = "<html></html>"
        headers = {}

    sleeps = []
    monkeypatch.setattr(
        amazon.requests,
        "get",
        lambda *args, **kwargs: Response(),
    )
    monkeypatch.setattr(
        amazon.time,
        "sleep",
        lambda value: sleeps.append(value),
    )
    monkeypatch.setattr(amazon.random, "uniform", lambda low, high: low)

    response, attempts, reason = amazon._request_search(
        "https://www.amazon.es/s?k=movil+5g",
    )

    assert response.status_code == 503
    assert attempts == amazon.MAX_REQUEST_ATTEMPTS
    assert reason == "http_503"
    assert len(sleeps) == amazon.MAX_REQUEST_ATTEMPTS - 1


def test_amazon_buscar_records_retry_metadata(monkeypatch):
    from sources import amazon

    class Response:
        status_code = 200
        text = "<html></html>"
        headers = {}

    monkeypatch.setenv("AMAZON_TAG", "test-21")
    monkeypatch.setattr(amazon.requests, "get", lambda *args, **kwargs: Response())
    monkeypatch.setattr(amazon.time, "sleep", lambda value: None)

    result = amazon.buscar("prueba", category="storage")

    assert result == []
    status = amazon.get_last_status()
    assert status["ok"] is True
    assert status["failed"] is False
    assert status["attempts"] == 1
    assert status["retries"] == 0


def test_global_amazon_circuit_stops_followup_queries(monkeypatch, tmp_path):
    from sources import amazon

    class Response:
        status_code = 503
        text = "temporarily unavailable"
        headers = {}

    monkeypatch.setattr(amazon, "GLOBAL_LOCK_PATH", str(tmp_path / "lock"))
    monkeypatch.setattr(amazon, "GLOBAL_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(amazon, "GLOBAL_COOLDOWN_SECONDS", 900)
    monkeypatch.setattr(amazon, "GLOBAL_MIN_INTERVAL", 0)
    calls = []
    monkeypatch.setattr(
        amazon, "_request_search_uncoordinated",
        lambda url: (calls.append(url) or Response(), 3, "http_503"),
    )

    first = amazon._request_search("https://www.amazon.es/s?k=first")
    second = amazon._request_search("https://www.amazon.es/s?k=second")

    assert first[2] == "http_503"
    assert second == (None, 0, "global_circuit_open")
    assert len(calls) == 1
