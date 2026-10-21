from html import escape


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
    """Acorta títulos de marketplace sin cortar una frase cuando sea posible."""
    title = " ".join((title or "").split())
    if len(title) <= max_len:
        return title

    # Preferimos cortes naturales antes de un máximo duro.
    for sep in [" | ", " – ", " - ", ", "]:
        positions = [i for i in range(len(title)) if title.startswith(sep, i)]
        valid = [i for i in positions if 30 <= i <= max_len]
        if valid:
            return title[:valid[-1]].strip()

    return title[:max_len - 1].rstrip() + "…"


def format_offer(offer, score=None, classification=None):
    # score se mantiene en la firma por compatibilidad con el código existente,
    # pero nunca se muestra al público.
    label = classification or getattr(offer, "label", "BUENA OFERTA")
    title = clean_title(offer.title)
    discount = offer.discount_pct

    price_line = f"💰 <b>{offer.current_price:.2f} €</b>"
    savings_line = ""
    if offer.reference_price is not None and offer.reference_price > offer.current_price:
        price_line += f"  <s>{offer.reference_price:.2f} €</s>"
        savings = offer.reference_price - offer.current_price
        savings_line = f"💸 Ahorras <b>{savings:.2f} €</b>"
    if discount is not None:
        price_line += f"  <b>-{discount:.0f}%</b>"

    lines = [
        f"🔥 <b>{escape(label)}</b>",
        "",
        f"<b>{escape(title)}</b>",
        "",
        price_line,
    ]

    if savings_line:
        lines.append(savings_line)

    if offer.rating is not None:
        quality = f"⭐ {offer.rating:.1f}/5"
        if offer.reviews is not None:
            quality += f" · {offer.reviews:,} valoraciones"
        lines.append(quality)

    category = CATEGORY_LABELS.get(offer.category, offer.category or "Tecnología")
    lines.append(escape(category))

    lines.extend([
        "",
        f'🛒 <a href="{escape(offer.affiliate_url, quote=True)}">VER OFERTA</a>',
    ])

    return "\n".join(lines)


def build_dry_run(publicable_rows):
    return "\n\n".join(
        f"--- PUBLICACIÓN {i} ---\n{format_offer(offer, score, classification)}"
        for i, (score, offer, history, breakdown, classification) in enumerate(publicable_rows, 1)
    )
