#!/usr/bin/env python3
from __future__ import annotations

import os

import config
from scanner import run
from telegram_publisher import send_message
from telegram_sender import format_offer


CONFIRM_WORD = "PUBLICAR"


def main() -> int:
    print("=== V2 ONE-SHOT REAL PUBLISH ===")
    print("Ejecuta el scanner completo y considera SOLO 1 oferta publicable.")
    print(f"Telegram chat configurado: {bool(config.TELEGRAM_CHAT_ID)}")
    print(f"Token configurado: {bool(config.TELEGRAM_BOT_TOKEN)}")
    print(f"TELEGRAM_DRY_RUN actual: {int(config.TELEGRAM_DRY_RUN)}")
    print()

    scored, publicable = run(return_publicable=True)

    if not publicable:
        print("NO PUBLICADO: el scanner no encontró ninguna oferta publicable.")
        return 0

    score, offer, history, breakdown, classification = publicable[0]

    print("=== OFERTA SELECCIONADA ===")
    print(f"Fuente: {offer.source}")
    print(f"Título: {offer.title}")
    print(f"Precio: {offer.current_price:.2f} €")
    print(
        f"Referencia: "
        f"{offer.reference_price:.2f} €"
        if offer.reference_price is not None
        else "Referencia: n/d"
    )
    print(
        f"Descuento: "
        f"{offer.discount_pct:.1f}%"
        if offer.discount_pct is not None
        else "Descuento: n/d"
    )
    print(f"Rating: {offer.rating if offer.rating is not None else 'n/d'}")
    print(f"Valoraciones: {offer.reviews if offer.reviews is not None else 'n/d'}")
    print(f"Score publicación: {score:.2f}")
    print(f"Clasificación: {classification}")
    print(f"Categoría: {offer.category or '-'}")
    print()

    # Seguro de doble confirmación. No modifica .env ni TELEGRAM_DRY_RUN.
    if os.getenv("ONE_SHOT_CONFIRM", "") != CONFIRM_WORD:
        print(
            "NO PUBLICADO: falta la confirmación explícita.\n"
            "Para realizar ESTA única publicación real, ejecuta:\n"
            "  ONE_SHOT_CONFIRM=PUBLICAR python publish_one_real.py"
        )
        return 0

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("NO PUBLICADO: Telegram no está configurado.")
        return 1

    text = format_offer(offer, score, classification)
    result = send_message(text)

    if not result.get("ok"):
        print("ERROR: Telegram no confirmó la publicación.")
        return 1

    message_id = result.get("result", {}).get("message_id")
    print()
    print("✅ PUBLICACIÓN REAL ENVIADA")
    print(f"message_id={message_id}")
    print("Solo se ha enviado 1 mensaje.")
    print("TELEGRAM_DRY_RUN no ha sido modificado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
