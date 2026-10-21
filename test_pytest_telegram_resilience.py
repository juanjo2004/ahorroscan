import pytest
import telegram_publisher
from telegram_api import TelegramOutcomeUnknown


class FakeResponse:
    def __init__(self, status, data=None, headers=None):
        self.status_code = status
        self._data = data or {"ok": True, "result": {"message_id": 1}}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._data


class FakeRequests:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def post(self, *args, **kwargs):
        self.calls += 1
        return next(self.responses)


def test_telegram_does_not_retry_ambiguous_5xx(monkeypatch):
    fake = FakeRequests([FakeResponse(503), FakeResponse(200)])
    sleeps = []
    monkeypatch.setattr(telegram_publisher.requests, "post", fake.post)
    monkeypatch.setattr(telegram_publisher.time, "sleep", sleeps.append)

    with pytest.raises(TelegramOutcomeUnknown, match="http_503"):
        telegram_publisher._telegram_request("sendMessage", {"x": "y"})

    assert fake.calls == 1
    assert sleeps == []


def test_telegram_respects_retry_after(monkeypatch):
    fake = FakeRequests([
        FakeResponse(429, headers={"Retry-After": "5"}),
        FakeResponse(200),
    ])
    sleeps = []
    monkeypatch.setattr(telegram_publisher.requests, "post", fake.post)
    monkeypatch.setattr(telegram_publisher.time, "sleep", sleeps.append)

    result = telegram_publisher._telegram_request("sendMessage", {"x": "y"})

    assert result["ok"] is True
    assert fake.calls == 2
    assert sleeps == [5.0]
