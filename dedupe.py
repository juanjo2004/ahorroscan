"""Identificación y deduplicación conservadora de productos."""

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_PARAMS = {
    "aff", "affiliate", "campaign", "clickid", "fbclid", "gclid",
    "mc_cid", "mc_eid", "ref", "ref_", "source", "subid", "sub_id", "tag",
}


def norm_text(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def canonical_url(url):
    if not url:
        return None
    parsed = urlsplit(str(url).strip())
    if not parsed.scheme or not parsed.netloc:
        return str(url).strip() or None
    query = []
    for name, value in parse_qsl(parsed.query, keep_blank_values=True):
        low = name.lower()
        if low in _TRACKING_PARAMS or any(low.startswith(p) for p in _TRACKING_PREFIXES):
            continue
        query.append((name, value))
    return urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        urlencode(sorted(query)),
        "",
    ))


def title_key(title):
    """Identidad conservadora del título para evitar duplicados editoriales."""
    return norm_text(title)


def product_key(offer):
    """Genera una identidad estable, sin fuzzy matching."""
    source = (getattr(offer, "source", "") or "").lower().strip()
    external_id = str(getattr(offer, "external_id", "") or "").strip()
    if external_id:
        return f"{source}:{external_id}"

    url = canonical_url(getattr(offer, "url", None))
    if url:
        return f"{source}:url:{url}"

    return f"{source}:title:{norm_text(getattr(offer, 'title', ''))}"


def similar_title(a, b):
    """Conservado solo para compatibilidad; no se usa para fusionar."""
    from difflib import SequenceMatcher
    a = norm_text(a)
    b = norm_text(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

