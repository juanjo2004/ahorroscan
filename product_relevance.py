"""Conservative shared filter for repair and replacement items."""
from __future__ import annotations

import re
import unicodedata


_BLOCKED_TOKENS = frozenset({
    "repuesto", "repuestos", "recambio", "recambios",
    "reemplazo", "reemplazos", "sustitucion", "sustituciones",
    "reparacion", "reparaciones", "reparar", "reparando",
    "refaccion", "refacciones",
    "replacement", "replacements", "replaceable", "replacing",
    "spare", "spares",
    "repair", "repairs", "repairing",
})

_PART_FOR_PATTERN = re.compile(
    r"\b(?:piece|pieces|part|parts|component|components|"
    r"pieza|piezas|parte|partes|componente|componentes)\s+"
    r"(?:for|para)\b"
)
_LOOSE_PART_PATTERN = re.compile(
    r"\b(?:(?:loose|individual|suelto|suelta|sueltos|sueltas)\s+"
    r"(?:piece|pieces|part|parts|component|components|pieza|piezas|"
    r"parte|partes|componente|componentes)|"
    r"(?:piece|pieces|part|parts|component|components|pieza|piezas|"
    r"parte|partes|componente|componentes)\s+"
    r"(?:loose|individual|suelto|suelta|sueltos|sueltas))\b"
)


def normalize_product_title(title: str | None) -> str:
    """Normalize accents and punctuation without changing word boundaries."""
    text = unicodedata.normalize("NFKD", (title or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def is_repair_related(title: str | None) -> bool:
    """Return True for spare parts, replacement items, or repair supplies.

    The filter deliberately requires an explicit repair/replacement cue or a
    part-for-device construction; ordinary complete products and useful
    accessories remain eligible.
    """
    normalized = normalize_product_title(title)
    tokens = set(normalized.split())
    return bool(
        tokens.intersection(_BLOCKED_TOKENS)
        or _PART_FOR_PATTERN.search(normalized)
        or _LOOSE_PART_PATTERN.search(normalized)
    )
