from html import escape

from redirector.link_manager import get_or_create_product_link
from telegram_format import format_channel_offer


def format_eur(value):
    """Formatea un importe con convención española."""
    if value is None:
        return "n/d"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


CATEGORY_LABELS = {
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
    "peripherals": "⌨️ Periféricos",
    "mice": "🖱️ Ratones",
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


def clean_title(title, max_len=82):
    """Acorta títulos sin cortar una frase cuando sea posible."""
    title = " ".join((title or "").split())

    if len(title) <= max_len:
        return title

    for sep in [" | ", " – ", " - ", ", "]:
        positions = [
            i for i in range(len(title))
            if title.startswith(sep, i)
        ]

        valid = [i for i in positions if 30 <= i <= max_len]

        if valid:
            return title[:valid[-1]].strip()

    return title[:max_len - 1].rstrip() + "…"


def format_checked_at():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y · %H:%M")


def format_offer(offer, score=None, classification=None):
    return format_channel_offer(offer, "tech")


def build_offer_keyboard(offer):
    """
    Construye el botón real de Telegram.

    La URL de afiliado se mantiene como destino del botón,
    no dentro del texto visible del anuncio.
    """

    if str(getattr(offer, "source", "")).lower() == "amazon":
        if not offer.affiliate_url:
            raise ValueError("La oferta Amazon no contiene affiliate_url")
        public_url = offer.affiliate_url
    else:
        product_id = getattr(offer, "product_id", None)
        if product_id is None:
            raise ValueError("La oferta no contiene product_id.")
        public_url = get_or_create_product_link(
            int(product_id),
            offer.affiliate_url,
            "tech",
            "telegram_tech",
        )

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🛒 VER OFERTA",
                    "url": public_url,
                }
            ]
        ]
    }


def build_dry_run(publicable_rows):
    return "\n\n".join(
        f"--- PUBLICACIÓN {i} ---\n"
        f"{format_offer(offer, score, classification)}\n"
        f"[BOTÓN] 🛒 VER OFERTA → {offer.affiliate_url}"
        for i, (
            score,
            offer,
            history,
            breakdown,
            classification,
        ) in enumerate(publicable_rows, 1)
    )
