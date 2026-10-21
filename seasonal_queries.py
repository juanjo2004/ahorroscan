"""Seasonal discovery queries for AhorroScan Tech and Hogar in Spain."""
from __future__ import annotations
from datetime import date

WINDOWS = (
    ("halloween", (9, 20), (11, 1), (
        ("seasonal_halloween", ["halloween", "disfraces halloween"]),
        ("seasonal_halloween_home", ["decoracion halloween", "luces halloween"]),
        ("seasonal_halloween_party", ["fiesta halloween", "maquillaje halloween"]),
    )),
    ("black_friday", (11, 1), (12, 1), (
        ("seasonal_black_friday", ["black friday", "ofertas black friday"]),
        ("seasonal_cyber_monday", ["cyber monday", "ofertas cyber monday"]),
    )),
    ("christmas", (11, 15), (12, 26), (
        ("seasonal_christmas", ["navidad", "regalos navidad"]),
        ("seasonal_christmas_home", ["decoracion navidad", "luces navidad"]),
        ("seasonal_christmas_gifts", ["ideas regalo", "juguetes navidad"]),
    )),
    ("new_year", (12, 20), (1, 7), (
        ("seasonal_new_year", ["nochevieja", "cotillon"]),
        ("seasonal_party", ["fiesta", "uvas nochevieja"]),
    )),
    ("valentines", (1, 25), (2, 15), (
        ("seasonal_valentines", ["san valentin", "regalos pareja"]),
        ("seasonal_valentines_home", ["decoracion romantica", "regalo romantico"]),
    )),
    ("fathers_day", (3, 1), (3, 20), (
        ("seasonal_fathers", ["dia del padre", "regalos padre"]),
        ("seasonal_fathers_tools", ["herramientas regalo", "gadgets padre"]),
    )),
    ("easter", (3, 15), (4, 15), (
        ("seasonal_easter", ["pascua", "semana santa"]),
        ("seasonal_easter_home", ["decoracion pascua", "jardin primavera"]),
    )),
    ("mothers_day", (4, 15), (5, 15), (
        ("seasonal_mothers", ["dia de la madre", "regalos madre"]),
        ("seasonal_mothers_home", ["decoracion regalo", "jardin regalo"]),
    )),
    ("summer", (5, 15), (8, 31), (
        ("seasonal_summer", ["ventilador", "aire acondicionado"]),
        ("seasonal_summer_outdoor", ["piscina", "camping"]),
        ("seasonal_summer_home", ["barbacoa", "terraza jardin"]),
    )),
)


def active(today=None):
    today = today or date.today()
    cur = (today.month, today.day)
    out = []
    for name, start, end, queries in WINDOWS:
        if start <= end:
            ok = start <= cur < end
        else:
            ok = cur >= start or cur < end
        if ok:
            out.extend(queries)
    return out


def queries(today=None):
    return active(today)
