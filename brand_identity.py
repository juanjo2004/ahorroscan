"""Conservative manufacturer recognition for editorial ranking and product metadata."""
import re
import unicodedata

_RAW = {
    "Apple": ("apple", "iphone", "ipad", "macbook"),
    "Samsung": ("samsung", "galaxy"),
    "Google": ("google", "pixel"),
    "Xiaomi": ("xiaomi", "redmi"),
    "POCO": ("poco",),
    "OnePlus": ("oneplus",),
    "Motorola": ("motorola", "moto"),
    "Huawei": ("huawei",),
    "Honor": ("honor",),
    "OPPO": ("oppo",),
    "realme": ("realme",),
    "Sony": ("sony", "xperia", "playstation"),
    "LG": ("lg",),
    "Lenovo": ("lenovo", "thinkpad", "legion"),
    "ASUS": ("asus", "rog"),
    "Acer": ("acer",),
    "Dell": ("dell", "alienware"),
    "HP": ("hp", "hewlett packard", "omen"),
    "MSI": ("msi",),
    "AMD": ("amd", "ryzen"),
    "Intel": ("intel",),
    "NVIDIA": ("nvidia", "geforce"),
    "Logitech": ("logitech", "logi"),
    "Razer": ("razer",),
    "Corsair": ("corsair",),
    "JBL": ("jbl",),
    "Bose": ("bose",),
    "Sennheiser": ("sennheiser",),
    "Anker": ("anker", "soundcore"),
    "Belkin": ("belkin",),
    "Baseus": ("baseus",),
    "UGREEN": ("ugreen",),
    "CUKTECH": ("cuktech",),
    "TP-Link": ("tp link", "tplink"),
    "NETGEAR": ("netgear",),
    "Philips": ("philips",),
    "Canon": ("canon",),
    "Nikon": ("nikon",),
    "GoPro": ("gopro",),
    "DJI": ("dji",),
    "Nintendo": ("nintendo",),
    "8BitDo": ("8bitdo",),
    "Sonoff": ("sonoff",),
    "ORICO": ("orico",),
    "Kingston": ("kingston",),
    "SanDisk": ("sandisk",),
    "Seagate": ("seagate",),
    "Western Digital": ("western digital", "wd black", "wd blue", "wd red", "wd purple"),
    "Garmin": ("garmin",),
    "Reolink": ("reolink",),
    "Wacom": ("wacom",),
    "Synology": ("synology",),
    "QNAP": ("qnap",),
    "Roborock": ("roborock",),
    "Eufy": ("eufy",),
    "Amazfit": ("amazfit",),
    "Jabra": ("jabra",),
    "Marshall": ("marshall",),
    "Fujifilm": ("fujifilm",),
    "Panasonic": ("panasonic",),
    "Hisense": ("hisense",),
    "TCL": ("tcl",),
    "Crucial": ("crucial",),
    "Lexar": ("lexar",),
    "Edifier": ("edifier",),
    "Ubiquiti": ("ubiquiti",),
    "Dreame": ("dreame",),
    "Ecovacs": ("ecovacs",),
    "Brother": ("brother",),
    "Epson": ("epson",),
    "Amazon Basics": ("amazon basics",),
    "Nothing": ("nothing",),
}


def _normalize(value):
    value = unicodedata.normalize("NFKD", (value or "").casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


_ALIASES = sorted(
    ((_normalize(alias), brand) for brand, aliases in _RAW.items() for alias in aliases),
    key=lambda item: len(item[0]),
    reverse=True,
)


def extract_brand(title):
    """Return a known brand only when its name leads the product title."""
    normalized = _normalize(title)
    for alias, brand in _ALIASES:
        if normalized == alias or normalized.startswith(alias + " "):
            return brand
    return None
