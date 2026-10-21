"""AhorroScan seasonal ranking and publication guard for Spain.

Seasonality boosts products that match the current shopping calendar and also
blocks clearly future-season products from reaching public channels too early.
"""
from __future__ import annotations

from datetime import date
import re


SEASONS = {
    "halloween": {
        "start": (9, 20), "end": (11, 1), "boost": 9.0,
        "keywords": (
            "halloween", "disfraz", "disfraces", "calabaza", "pumpkin",
            "decoracion halloween", "decoración halloween", "terror",
            "bruja", "brujo", "maquillaje halloween", "fiesta halloween",
            "araña", "telaraña", "spider", "spooky",
        ),
        "categories": ("lighting", "garden", "organization", "textiles"),
    },
    "black_friday": {
        "start": (11, 1), "end": (12, 1), "boost": 7.0,
        "keywords": ("black friday", "blackfriday", "cyber monday", "oferta"),
        "categories": (),
    },
    "christmas": {
        # Empezamos a principios de noviembre para absorber posibles retrasos
        # de envío en compras internacionales y dar margen al comprador.
        "start": (11, 1), "end": (12, 26), "boost": 10.0,
        "keywords": (
            "navidad", "navideño", "navideña", "christmas", "regalo",
            "regalos", "juguete", "juguetes", "belén", "belen",
            "árbol de navidad", "arbol de navidad", "luces navideñas",
            "decoración navideña", "decoracion navideña", "calcetines navidad",
        ),
        "categories": ("lighting", "toys", "furniture", "kitchen", "textiles"),
    },
    "new_year": {
        "start": (12, 20), "end": (1, 7), "boost": 5.0,
        "keywords": ("nochevieja", "fin de año", "fin de ano", "cotillón",
                     "cotillon", "uvas", "fiesta"),
        "categories": (),
    },
    "valentines": {
        "start": (1, 25), "end": (2, 15), "boost": 6.0,
        "keywords": ("san valentín", "san valentin", "valentín", "valentin",
                     "pareja", "romántico", "romantico", "corazón", "corazon"),
        "categories": ("lighting", "textiles", "kitchen"),
    },
    "fathers_day": {
        "start": (3, 1), "end": (3, 20), "boost": 5.0,
        "keywords": ("día del padre", "dia del padre", "padre", "papá", "papa"),
        "categories": ("tools", "kitchen", "technology"),
    },
    "easter": {
        "start": (3, 15), "end": (4, 15), "boost": 4.0,
        "keywords": ("pascua", "semana santa", "monas de pascua"),
        "categories": ("kitchen", "garden"),
    },
    "mothers_day": {
        "start": (4, 15), "end": (5, 15), "boost": 5.0,
        "keywords": ("día de la madre", "dia de la madre", "madre", "mamá", "mama"),
        "categories": ("lighting", "kitchen", "textiles", "garden"),
    },
    "summer": {
        "start": (5, 15), "end": (8, 31), "boost": 5.0,
        "keywords": (
            "ventilador", "aire acondicionado", "piscina", "playa",
            "camping", "barbacoa", "bbq", "sombrilla", "terraza",
            "jardín", "jardin", "hielo",
        ),
        "categories": ("climate", "garden"),
    },
}


def _active(season: dict, today: date) -> bool:
    month = today.month
    day = today.day
    start_m, start_d = season["start"]
    end_m, end_d = season["end"]
    current = (month, day)
    start = (start_m, start_d)
    end = (end_m, end_d)
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def active_seasons(today: date | None = None) -> list[str]:
    today = today or date.today()
    return [name for name, season in SEASONS.items() if _active(season, today)]


EARLY_SEASONAL_KEYWORDS = {
    "christmas": (
        "navidad", "navideño", "navideña", "christmas",
        "árbol de navidad", "arbol de navidad", "luces navideñas",
        "decoración navideña", "decoracion navideña", "belen", "belén",
    ),
    "new_year": (
        "nochevieja", "fin de año", "fin de ano", "cotillón", "cotillon",
        "uvas nochevieja",
    ),
    "valentines": (
        "san valentín", "san valentin", "día de los enamorados",
        "dia de los enamorados",
    ),
    "fathers_day": (
        "día del padre", "dia del padre",
    ),
    "mothers_day": (
        "día de la madre", "dia de la madre",
    ),
}


def is_seasonally_premature(title: str = "", today: date | None = None) -> bool:
    """Bloquea productos con una temporada futura claramente identificable."""
    today = today or date.today()
    text = re.sub(r"\s+", " ", (title or "").lower()).strip()

    for season_name, keywords in EARLY_SEASONAL_KEYWORDS.items():
        season = SEASONS[season_name]
        if not _active(season, today) and any(k in text for k in keywords):
            start = season["start"]
            end = season["end"]
            current = (today.month, today.day)
            if start <= end:
                # Campaña dentro del mismo año: solo es prematura antes del inicio.
                if current < start:
                    return True
            else:
                # Campaña que cruza diciembre: es prematura entre el final
                # de la campaña anterior y el próximo inicio.
                if end < current < start:
                    return True
    return False


def seasonal_score(title: str = "", category: str | None = None,
                   today: date | None = None) -> tuple[float, list[str]]:
    """Return (boost, matched seasons). Never returns a negative score."""
    today = today or date.today()
    text = re.sub(r"\s+", " ", (title or "").lower()).strip()
    category = (category or "").lower()
    total = 0.0
    matched = []

    for name, season in SEASONS.items():
        if not _active(season, today):
            continue
        keyword_hit = any(k in text for k in season["keywords"])
        category_hit = category in season["categories"]
        if keyword_hit or category_hit:
            total += season["boost"]
            matched.append(name)

    return round(min(total, 15.0), 2), matched


def explain(title: str = "", category: str | None = None,
            today: date | None = None) -> str:
    boost, seasons = seasonal_score(title, category, today)
    return f"+{boost:.1f} ({','.join(seasons) or 'sin coincidencia'})"
