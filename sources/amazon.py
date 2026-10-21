

import os
import json
import random
import fcntl
import re
import time
from datetime import datetime, timezone
import requests
from urllib.parse import parse_qs, quote_plus, urlsplit
from bs4 import BeautifulSoup
from models import Offer
import config  # carga .env al importar

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
]

LAST_STATUS = {}

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_REQUEST_ATTEMPTS = 3
RETRY_DELAY_MIN = 4.0
RETRY_DELAY_MAX = 7.0
RETRY_DELAY_CAP = 30.0
REQUEST_DELAY_MIN = 2.5
REQUEST_DELAY_MAX = 4.5
GLOBAL_MIN_INTERVAL = float(os.getenv("AMAZON_GLOBAL_MIN_INTERVAL", "12"))
GLOBAL_COOLDOWN_SECONDS = int(os.getenv("AMAZON_GLOBAL_COOLDOWN_SECONDS", "900"))
GLOBAL_STATE_PATH = os.getenv("AMAZON_GLOBAL_STATE_PATH", "/tmp/ahorroscan-amazon-global-state.json")
GLOBAL_LOCK_PATH = os.getenv("AMAZON_GLOBAL_LOCK_PATH", "/tmp/ahorroscan-amazon-global.lock")




def _set_status(**values):
    LAST_STATUS.clear()
    LAST_STATUS.update(values)


def get_last_status():
    return dict(LAST_STATUS)


def _parse_eur(text):
    if not text:
        return None
    raw = str(text).replace("\xa0", " ").replace("EUR", "").replace("€", "").strip()
    raw = re.sub(r"[^0-9,.-]", "", raw)
    if not raw:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_rating(item):
    for tag in item.select("span.a-icon-alt"):
        text = tag.get_text(" ", strip=True)
        m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:de\s*5|/\s*5|estrellas?|stars?)", text, re.I)
        if not m:
            m = re.fullmatch(r"(\d+(?:[\.,]\d+)?)", text)
        if m:
            try:
                value = float(m.group(1).replace(",", "."))
                if 0 <= value <= 5:
                    return value
            except ValueError:
                pass
    return None


def _parse_compact_count(text):
    if not text:
        return None
    raw = str(text).replace("\xa0", " ").strip().lower()
    raw = raw.replace("(", "").replace(")", "").strip()
    m = re.fullmatch(r"([0-9]+(?:[\.,][0-9]+)?)\s*(mil|k)?", raw)
    if not m:
        return None
    number = m.group(1).replace(",", ".")
    try:
        value = float(number)
    except ValueError:
        return None
    if m.group(2) in ("mil", "k"):
        value *= 1000
    return int(round(value)) if value >= 0 else None


def _parse_reviews(item):
    for tag in item.select("span.s-underline-text"):
        parsed = _parse_compact_count(tag.get_text(" ", strip=True))
        if parsed is not None:
            return parsed
    for tag in item.select("a[href*='customerReviews'], a[href*='#customerReviews']"):
        parsed = _parse_compact_count(tag.get_text(" ", strip=True))
        if parsed is not None:
            return parsed
    for tag in item.select("[aria-label]"):
        label = tag.get("aria-label", "") or ""
        m = re.search(r"(?:\(|^)\s*([0-9]+(?:[\.,][0-9]+)?)\s*(mil|k)?\s*(?:\)|$)", label, re.I)
        if m:
            parsed = _parse_compact_count(f"{m.group(1)} {m.group(2) or ''}")
            if parsed is not None:
                return parsed
    return None


def _retry_delay(attempt, response=None):
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 1.0), RETRY_DELAY_CAP)
            except (TypeError, ValueError):
                pass

    low = RETRY_DELAY_MIN * (2 ** (attempt - 1))
    high = RETRY_DELAY_MAX * (2 ** (attempt - 1))
    return min(random.uniform(low, high), RETRY_DELAY_CAP)


def _request_search_uncoordinated(url):
    base_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }

    last_response = None
    last_exception = None

    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        headers = dict(base_headers)
        headers["User-Agent"] = random.choice(USER_AGENTS)

        try:
            response = requests.get(url, headers=headers, timeout=15)
            last_response = response

            blocked = (
                "captcha" in response.text.lower()
                or "api-services-support@amazon.com" in response.text
            )

            if response.status_code == 200 and not blocked:
                return response, attempt, None

            transient = (
                response.status_code in TRANSIENT_STATUS_CODES
                or blocked
            )

            if not transient or attempt >= MAX_REQUEST_ATTEMPTS:
                return response, attempt, (
                    "blocked" if blocked else f"http_{response.status_code}"
                )

            delay = _retry_delay(attempt, response)
            print(
                f"[AMAZON] Respuesta transitoria para la búsqueda "
                f"(status={response.status_code}, intento={attempt}/{MAX_REQUEST_ATTEMPTS}). "
                f"Reintento en {delay:.1f}s."
            )
            time.sleep(delay)

        except requests.RequestException as exc:
            last_exception = exc

            if attempt >= MAX_REQUEST_ATTEMPTS:
                raise

            delay = _retry_delay(attempt)
            print(
                f"[AMAZON] Error de red en intento "
                f"{attempt}/{MAX_REQUEST_ATTEMPTS}: {type(exc).__name__}. "
                f"Reintento en {delay:.1f}s."
            )
            time.sleep(delay)

    if last_exception is not None:
        raise last_exception

    return last_response, MAX_REQUEST_ATTEMPTS, None



def _request_search(url):
    """Coordina todas las consultas Amazon de los procesos locales del VPS.

    Mantiene un lock entre procesos, limita el ritmo global y abre un circuito
    compartido tras bloqueos/errores transitorios para evitar cascadas.
    """
    now = time.time()
    with open(GLOBAL_LOCK_PATH, "a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            try:
                state = json.loads(open(GLOBAL_STATE_PATH, encoding="utf-8").read())
            except (OSError, ValueError, TypeError):
                state = {}
            now = time.time()
            blocked_until = float(state.get("blocked_until", 0) or 0)
            if blocked_until > now:
                wait = blocked_until - now
                print(f"[AMAZON] Circuito global abierto; se omite petición durante {wait:.0f}s.")
                return None, 0, "global_circuit_open"

            last_request = float(state.get("last_request", 0) or 0)
            wait = GLOBAL_MIN_INTERVAL - (now - last_request)
            if wait > 0:
                time.sleep(wait)

            state["last_request"] = time.time()
            with open(GLOBAL_STATE_PATH, "w", encoding="utf-8") as state_file:
                json.dump(state, state_file)

            response, attempts, failure = _request_search_uncoordinated(url)
            state["last_request"] = time.time()
            if failure is not None or response is None or response.status_code in TRANSIENT_STATUS_CODES:
                state["blocked_until"] = time.time() + GLOBAL_COOLDOWN_SECONDS
                state["last_failure"] = failure or (f"http_{response.status_code}" if response else "no_response")
                print(f"[AMAZON] Circuito global abierto durante {GLOBAL_COOLDOWN_SECONDS}s tras error.")
            else:
                state["blocked_until"] = 0
                state["last_failure"] = None
            with open(GLOBAL_STATE_PATH, "w", encoding="utf-8") as state_file:
                json.dump(state, state_file)
            return response, attempts, failure
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _is_smartphone_title(title: str) -> bool:
    """Evita que búsquedas de móviles conviertan accesorios en smartphones."""
    text = " ".join((title or "").lower().split())
    device_terms = (
        "smartphone", "iphone", "galaxy", "redmi", "xiaomi", "poco", "pixel",
        "oneplus", "oppo", "realme", "motorola", "honor", "nothing phone",
        "vivo", "xperia", "tcl", "zte", "nubia", "asus", "zenfone", "rog phone",
        "nokia", "hmd", "doogee", "ulefone", "blackview", "fairphone",
        "telefono móvil", "teléfono móvil", "telefono movil", "teléfono movil",
        "teléfono inteligente", "telefono inteligente",
    )
    accessory_phrases = (
        "cargador para", "cargador inalámbrico", "cargador de teléfono", "charger for", "soporte para", "holder for", "mount for",
        "funda para", "case for", "carcasa para", "cover for", "protector para",
        "protector de pantalla", "screen protector", "cristal templado", "cable para",
        "adaptador para", "adapter for", "batería de reemplazo", "replacement battery",
        "pantalla de reemplazo", "replacement screen", "repuesto para", "replacement for",
        "accesorio para", "accessory for", "soporte de vídeo para", "video rig for",
        "jaula para", "cage for", "mango para", "grip for", "trípode para", "tripod for",
        "stylus para", "lápiz óptico para", "gimbal para",
    )
    return bool(any(term in text for term in device_terms) and not any(
        phrase in text for phrase in accessory_phrases
    ))


def buscar(keywords="teclado", limite=None, category=None):
    amazon_tag = os.getenv("AMAZON_TAG", config.AMAZON_TAG)
    started_at = datetime.now(timezone.utc).isoformat()
    if not amazon_tag:
        print("[AMAZON] AMAZON_TAG no configurado.")
        _set_status(
            query=keywords, ok=False, failed=True, reason="missing_tag",
            status_code=None, candidates=0, checked_at=started_at,
            attempts=0, retries=0,
        )
        return []

    limite = limite or config.MAX_PRODUCTS_PER_QUERY
    time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
    url = f"https://www.amazon.es/s?k={keywords.replace(' ', '+')}"
    out = []
    try:
        r, attempts, failure_reason = _request_search(url)
        retries = max(0, attempts - 1)

        if r is None:
            reason = failure_reason or "global_circuit_open"
            _set_status(
                query=keywords, ok=False, failed=True, reason=reason,
                status_code=None, candidates=0, checked_at=started_at,
                attempts=attempts, retries=retries,
            )
            return out

        if r.status_code != 200 or failure_reason is not None:
            reason = (
                "http_5xx" if 500 <= r.status_code < 600
                else failure_reason or f"http_{r.status_code}"
            )
            print(
                f"[AMAZON] HTTP/bloqueo para '{keywords}': "
                f"{r.status_code} tras {attempts} intento(s)"
            )
            _set_status(
                query=keywords, ok=False, failed=True, reason=reason,
                status_code=r.status_code, candidates=0,
                checked_at=started_at, attempts=attempts, retries=retries,
            )
            return out

        if retries:
            print(
                f"[AMAZON] Recuperada búsqueda '{keywords}' "
                f"tras {retries} reintento(s)."
            )

        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.find_all("div", {"data-component-type": "s-search-result"}):
            if len(out) >= limite:
                break
            asin = (item.get("data-asin") or "").strip()
            if not asin:
                continue
            h2 = item.find("h2")
            title = h2.get_text(" ", strip=True) if h2 else "Producto Amazon"
            if category == "smartphones" and not _is_smartphone_title(title):
                continue
            offscreen = item.select_one(".a-price .a-offscreen")
            current = _parse_eur(offscreen.get_text(strip=True)) if offscreen else None
            if current is None:
                whole = item.find("span", class_="a-price-whole")
                frac = item.find("span", class_="a-price-fraction")
                if whole:
                    current = _parse_eur(
                        whole.get_text(strip=True)
                        + ","
                        + (frac.get_text(strip=True) if frac else "00")
                    )

            strike = item.find("span", {"data-a-strike": "true"})
            reference = None
            if strike:
                strike_offscreen = strike.find("span", class_="a-offscreen")
                if strike_offscreen:
                    reference = _parse_eur(
                        strike_offscreen.get_text(strip=True)
                    )

            if current is None or reference is None or reference <= current:
                continue

            img = item.find("img", class_="s-image")
            image_url = img.get("src") if img else None
            product_url = f"https://www.amazon.es/dp/{asin}"
            out.append(Offer(
                source="amazon",
                external_id=asin,
                title=title,
                current_price=current,
                reference_price=reference,
                url=product_url,
                affiliate_url=f"{product_url}?tag={amazon_tag}",
                image_url=image_url,
                rating=_parse_rating(item),
                reviews=_parse_reviews(item),
                category=category,
            ))

        _set_status(
            query=keywords, ok=True, failed=False, reason=None,
            status_code=200, candidates=len(out), checked_at=started_at,
            attempts=attempts, retries=retries,
        )

    except requests.RequestException as exc:
        print(f"[AMAZON] Excepción de red: {exc}")
        _set_status(
            query=keywords, ok=False, failed=True,
            reason=type(exc).__name__, status_code=None,
            candidates=0, checked_at=started_at,
            attempts=MAX_REQUEST_ATTEMPTS, retries=MAX_REQUEST_ATTEMPTS - 1,
        )
    except Exception as exc:
        print(f"[AMAZON] Excepción: {exc}")
        _set_status(
            query=keywords, ok=False, failed=True,
            reason=type(exc).__name__, status_code=None,
            candidates=0, checked_at=started_at,
            attempts=MAX_REQUEST_ATTEMPTS, retries=MAX_REQUEST_ATTEMPTS - 1,
        )
    return out




DEAL_FILTER_CACHE = {"rh": None, "fetched_at": 0.0}

AMAZON_DEAL_DISCOVERY_QUERIES = (
    ("smartphones", "movil 5g"),
    ("laptops", "portatil"),
    ("storage", "ssd nvme"),
    ("monitors", "monitor 4k"),
    ("peripherals", "teclado mecanico"),
    ("mice", "raton gaming"),
    ("audio", "auriculares bluetooth"),
    ("networking", "router wifi 6"),
    ("gaming", "consola gaming"),
    ("charging", "cargador gan"),
    ("power", "power bank"),
    ("wearables", "smartwatch"),
    ("projectors", "proyector"),
    ("cameras", "camara deportiva"),
)


def _discover_deal_filter(force=False):
    """Descubre el filtro vivo de ofertas de Amazon.es."""
    now = time.time()
    if (
        not force
        and DEAL_FILTER_CACHE["rh"]
        and now - DEAL_FILTER_CACHE["fetched_at"] < 21600
    ):
        return DEAL_FILTER_CACHE["rh"]

    probe_url = "https://www.amazon.es/s?k=ofertas+electronica"
    try:
        response, _, failure = _request_search(probe_url)
    except requests.RequestException:
        return None

    if failure is not None or response is None or response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    candidates = []

    for anchor in soup.select("a[href*='p_n_deal_type']"):
        href = anchor.get("href") or ""
        label = anchor.get_text(" ", strip=True).lower()
        try:
            query = parse_qs(urlsplit(href).query)
        except ValueError:
            continue
        for rh in query.get("rh", []):
            if "p_n_deal_type:" not in rh:
                continue
            priority = 0
            if "ofertas del día" in label or "ofertas del dia" in label:
                priority += 100
            if "todos los ahorros" in label:
                priority += 80
            if "ofertas" in label:
                priority += 20
            candidates.append((priority, rh))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    rh = candidates[0][1]
    DEAL_FILTER_CACHE["rh"] = rh
    DEAL_FILTER_CACHE["fetched_at"] = now
    print(f"[AMAZON CENTRO] Filtro de ofertas descubierto: {rh}")
    return rh


def _parse_search_results(response, limite, category):
    """Convierte una página de resultados Amazon en Offer."""
    soup = BeautifulSoup(response.text, "html.parser")
    out = []

    for item in soup.find_all("div", {"data-component-type": "s-search-result"}):
        if len(out) >= limite:
            break

        asin = (item.get("data-asin") or "").strip()
        if not asin:
            continue

        h2 = item.find("h2")
        title = h2.get_text(" ", strip=True) if h2 else "Producto Amazon"
        if category == "smartphones" and not _is_smartphone_title(title):
            continue

        offscreen = item.select_one(".a-price .a-offscreen")
        current = _parse_eur(offscreen.get_text(strip=True)) if offscreen else None
        if current is None:
            whole = item.find("span", class_="a-price-whole")
            frac = item.find("span", class_="a-price-fraction")
            if whole:
                current = _parse_eur(
                    whole.get_text(strip=True)
                    + ","
                    + (frac.get_text(strip=True) if frac else "00")
                )

        reference = None
        strike = item.find("span", {"data-a-strike": "true"})
        if strike:
            strike_offscreen = strike.find("span", class_="a-offscreen")
            if strike_offscreen:
                reference = _parse_eur(strike_offscreen.get_text(strip=True))

        if reference is None:
            for tag in item.select(".a-text-price .a-offscreen"):
                candidate = _parse_eur(tag.get_text(strip=True))
                if candidate is not None and current is not None and candidate > current:
                    reference = candidate
                    break

        if current is None or reference is None or reference <= current:
            continue

        img = item.find("img", class_="s-image")
        image_url = img.get("src") if img else None
        product_url = f"https://www.amazon.es/dp/{asin}"

        out.append(
            Offer(
                source="amazon",
                external_id=asin,
                title=title,
                current_price=current,
                reference_price=reference,
                url=product_url,
                affiliate_url=f"{product_url}?tag={os.getenv('AMAZON_TAG', config.AMAZON_TAG)}",
                image_url=image_url,
                rating=_parse_rating(item),
                reviews=_parse_reviews(item),
                category=category,
            )
        )

    return out


def buscar_centro_ofertas(limite=60):
    """
    Descubrimiento masivo adicional desde el escaparate/filtro de ofertas.

    No sustituye las búsquedas normales. Añade una segunda vía de entrada
    para productos que Amazon está mostrando explícitamente como ofertas.
    """
    rh = _discover_deal_filter()
    if not rh:
        print("[AMAZON CENTRO] No se pudo descubrir el filtro de ofertas.")
        return []

    offers = []
    seen = set()
    attempted = 0
    failed = 0

    for category, query in AMAZON_DEAL_DISCOVERY_QUERIES:
        if len(offers) >= int(limite):
            break

        url = (
            f"https://www.amazon.es/s?k={quote_plus(query)}"
            f"&rh={quote_plus(rh)}"
        )
        attempted += 1
        try:
            response, attempts, failure = _request_search(url)
        except requests.RequestException as exc:
            failed += 1
            print(f"[AMAZON CENTRO] Error '{query}': {type(exc).__name__}")
            continue

        if failure is not None or response is None or response.status_code != 200:
            failed += 1
            status_code = response.status_code if response is not None else None
            print(
                f"[AMAZON CENTRO] Fallo '{query}': "
                f"status={status_code} reason={failure}"
            )
            if failure == "global_circuit_open":
                print("[AMAZON CENTRO] Se detiene el lote por circuito global abierto.")
                break
            continue

        found = _parse_search_results(
            response,
            min(6, int(limite) - len(offers)),
            category,
        )

        for offer in found:
            if offer.external_id in seen:
                continue
            seen.add(offer.external_id)

            if (offer.discount_pct or 0) < 12:
                continue
            if offer.rating is not None and offer.rating < 3.8:
                continue
            if offer.reviews is not None and offer.reviews < 10:
                continue

            offers.append(offer)
            if len(offers) >= int(limite):
                break

    LAST_STATUS["deal_center_attempted"] = attempted
    LAST_STATUS["deal_center_failed"] = failed
    LAST_STATUS["deal_center_candidates"] = len(offers)

    print(
        f"[AMAZON CENTRO] {len(offers)} candidatas "
        f"({attempted} consultas, {failed} fallos)"
    )
    return offers
