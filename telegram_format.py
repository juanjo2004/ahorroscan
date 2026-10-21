from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo


CHANNEL_HEADERS = {
    "tech": "💻 AHORROSCAN TECH",
    "moviles": "📱 AHORROSCAN MÓVILES",
    "mascotas": "🐾 AHORROSCAN MASCOTAS",
    "moda": "👗 AHORROSCAN MODA",
    "deportes": "🏅 AHORROSCAN DEPORTES",
}

TECH_CATEGORIES = {
    "smartphones": "📱 Smartphones",
    "tablets": "📲 Tablets",
    "laptops": "💻 Portátiles",
    "desktops": "🖥️ PCs",
    "monitors": "🖥️ Monitores",
    "televisores": "📺 TV",
    "networking": "📡 Redes",
    "storage": "💾 Almacenamiento",
    "components": "🧩 Componentes",
    "cpu": "🧠 Procesadores",
    "motherboards": "🧱 Placas base",
    "peripherals": "⌨️ Periféricos",    "mice": "🖱️ Ratones",
    "audio": "🎧 Audio",
    "smart_home": "🏠 Smart Home",
    "wearables": "⌚ Wearables",
    "gaming": "🎮 Gaming",
    "charging": "🔌 Cargadores",
    "power": "🔋 Energía",
    "cameras": "📷 Cámaras",
    "drones": "🚁 Drones",
    "projectors": "📽️ Proyectores",
    "vr": "🥽 VR",
    "printers": "🖨️ Impresoras",
    "ereaders": "📚 E-readers",
    "microphones": "🎙️ Micrófonos",
    "accessories": "🧰 Accesorios",
    "cables": "🔗 Cables",
}

CHANNEL_CATEGORIES = {
    "moviles": {
        "smartphones": "📱 Smartphones",
        "accessories": "🔌 Accesorios móviles",
    },
    "mascotas": {
        "dog": "🐶 Perros",
        "cat": "🐱 Gatos",
        "pet_care": "🧼 Cuidado",
        "pet_accessories": "🐾 Accesorios",        "aquarium": "🐠 Acuario",
    },
    "moda": {
        "women_fashion": "👗 Mujer",
        "men_fashion": "👔 Hombre",
        "footwear": "👟 Calzado",
        "bags": "👜 Bolsos",
        "accessories": "🕶️ Accesorios",
        "sportswear": "🏃 Deporte",
        "underwear": "🩲 Ropa interior",
    },
    "deportes": {
        "fitness": "🏋️ Fitness",
        "running": "🏃 Running",
        "cycling": "🚴 Ciclismo",
        "outdoor": "🏔️ Outdoor",
        "camping": "⛺ Camping",
        "team_sports": "⚽ Deportes de equipo",
    },
}


def _price(value):
    if value is None:
        return "n/d"
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

def _checked_at():
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y · %H:%M")


def _field(offer, *names):
    for name in names:
        value = getattr(offer, name, None)
        if value is not None:
            return value
    return None


def format_channel_offer(offer, channel, history=None, stats=None):
    """Formato Telegram común, basado en el formato público de Hogar."""
    stats = stats or {}
    header = CHANNEL_HEADERS.get(channel, f"🏠 AHORROSCAN {channel.upper()}")
    title = str(getattr(offer, "title", "") or "").strip()

    current = _field(offer, "current_price", "price")
    reference = _field(offer, "reference_price", "original_price")
    discount = _field(offer, "discount_pct", "discount_percent")

    lines = [
        f"<b>{escape(header)}</b>",
        "",
        f"<b>{escape(title)}</b>",
        "",
        f"🔥 <b>Precio SUPER OFERTA: {_price(current)}</b>",    ]

    if reference is not None and current is not None and float(reference) > float(current):
        lines.append(f"💰 Precio normal: {_price(reference)}")
        if discount is not None:
            lines.append(f"📉 Descuento: {float(discount):.0f}%")

    history_conf = str(stats.get("history_confidence") or "")
    history_factor = float(stats.get("history_confidence_factor", 0) or 0)
    if history_conf == "historical" and history_factor >= 0.50:
        if stats.get("is_historical_minimum"):
            lines.append("📊 <b>Mínimo histórico observado</b>")
        drop = stats.get("drop_from_first_percent")
        if drop is not None and float(drop) > 0:
            lines.append(f"📉 {float(drop):.0f}% por debajo de la primera observación")

    merchant = getattr(offer, "merchant", None)
    if merchant:
        lines.append(f"🏪 {escape(str(merchant))}")
    else:
        source = getattr(offer, "source", None)
        if source:
            source_labels = {"amazon": "Amazon", "aliexpress": "AliExpress"}
            lines.append(f"🏪 {escape(source_labels.get(str(source).lower(), str(source)))}")

    category = getattr(offer, "category", None)
    if category:
        labels = dict(TECH_CATEGORIES)
        labels.update(CHANNEL_CATEGORIES.get(channel, {}))
        category_label = labels.get(category, str(category).replace("_", " ").title())
        lines.append(f"🗂️ {escape(category_label)}")

    rating = getattr(offer, "rating", None)
    reviews = getattr(offer, "reviews", None)
    if rating is not None:
        rating_text = f"{float(rating):.1f}".replace(".", ",")
        quality = f"⭐ Valoración: {rating_text}/5"
        if reviews is not None:
            quality += f" · ({int(reviews):,} valoraciones)".replace(",", ".")
        lines.append(quality)

    lines.extend([
        "",
        f"🕒 Precio comprobado: {_checked_at()}",
        "",
        "📣 <a href=\"https://ahorroscan.es\">Descubre todos los canales de AhorroScan</a>",
        "",
        "⚠️ Enlace de afiliado. Podemos recibir una comisión por compras que cumplan los requisitos, sin cambiar el precio.",
    ])

    return "\n".join(lines)
