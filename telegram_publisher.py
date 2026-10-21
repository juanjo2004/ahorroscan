from __future__ import annotations

import time
from typing import Optional

import json
import requests

import config
from telegram_api import TelegramOutcomeUnknown, TelegramRequestRejected, send as telegram_send
from publication_guard import (
    can_publish,
    record_publication,
    claim_publication,
    release_publication_claim,
)
from ha_publish_guard import deny_reason, publishing_enabled

API_BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def check_connection() -> dict:
    """
    Comprueba que el token de Telegram funciona.
    """
    response = requests.get(
        f"{API_BASE}/getMe",
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def _telegram_request(method: str, payload: dict) -> dict:
    return telegram_send(config.TELEGRAM_BOT_TOKEN, method, payload)


def send_message(
    text: str,
    reply_markup: dict | None = None,
) -> dict:
    """
    Envía una publicación de texto, opcionalmente con teclado inline.
    """
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }

    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    return _telegram_request(
        "sendMessage",
        payload,
    )


def send_photo(
    photo_url: str,
    caption: str,
    reply_markup: dict | None = None,
) -> dict:
    """
    Envía una foto con caption y, opcionalmente, teclado inline.
    """
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }

    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    return _telegram_request(
        "sendPhoto",
        payload,
    )


def _publish_one(
    row,
    dry_run: bool = True,
) -> Optional[dict]:
    """
    Publica una oferta individual.

    row:
        Tupla producida por selection.py:
        (score, offer, history, breakdown, classification)
    """
    score, offer, history, breakdown, classification = row

    # product_id debe haber sido asociado al objeto Offer por scanner.
    product_id = getattr(offer, "product_id", None)

    if product_id is None:
        raise RuntimeError(
            "La oferta no contiene product_id. "
            "No se puede aplicar el guardián de publicaciones."
        )

    current_discount = offer.discount_pct

    # El contador de ejecución se gestiona en publish().
    return {
        "score": score,
        "offer": offer,
        "history": history,
        "breakdown": breakdown,
        "classification": classification,
        "product_id": product_id,
        "current_discount": current_discount,
    }


def publish(
    publicable_rows,
    force: bool = False,
) -> list[dict]:
    """
    Publica ofertas respetando:

    - TELEGRAM_DRY_RUN
    - máximo por ejecución
    - máximo diario
    - anti-duplicado
    - registro solo después de Telegram OK

    force=True:
        permite publicación real aunque TELEGRAM_DRY_RUN esté activo.
        Debe usarse exclusivamente para pruebas controladas.
    """

    if not publishing_enabled("telegram"):
        print(f"[PUBLISHER] BLOQUEADA HA: {deny_reason('telegram')}")
        return []

    results = []

    # Import local para evitar dependencias circulares.
    from telegram_sender import format_offer, build_offer_keyboard

    run_count = 0

    for row in publicable_rows:
        prepared = _publish_one(row)

        score = prepared["score"]
        offer = prepared["offer"]
        classification = prepared["classification"]
        product_id = prepared["product_id"]
        current_discount = prepared["current_discount"]

        allowed, reason = can_publish(
            run_publication_count=run_count,
            product_id=product_id,
            current_price=offer.current_price,
            current_discount_pct=current_discount,
            current_title=offer.title,
        )

        if not allowed:
            print(
                f"[PUBLISHER] BLOQUEADA: "
                f"{offer.source}:{offer.external_id} -> {reason}"
            )
            results.append({
                "status": "blocked",
                "product_id": product_id,
                "external_id": offer.external_id,
                "source": offer.source,
                "reason": reason,
            })
            continue

        caption = format_offer(
            offer,
            score,
            classification,
        )

        # DRY RUN: no se toca Telegram ni se registra publicación.
        if config.TELEGRAM_DRY_RUN and not force:
            print(
                f"[PUBLISHER] DRY RUN: "
                f"{offer.source}:{offer.external_id}"
            )

            results.append({
                "status": "dry_run",
                "product_id": product_id,
                "external_id": offer.external_id,
                "source": offer.source,
            })

            # El contador NO aumenta en dry-run.
            continue

        if not claim_publication("tech", int(product_id), offer.title):
            print(f"[PUBLISHER] BLOQUEADA: título/producto ya reclamado -> {offer.title[:100]}")
            continue

        request_started = False
        telegram_accepted = False
        try:
            # Solo se crea el enlace trackeable cuando vamos a publicar de verdad.
            reply_markup = build_offer_keyboard(offer)
            request_started = True

            if offer.image_url:
                response = send_photo(
                    offer.image_url,
                    caption,
                    reply_markup=reply_markup,
                )
                send_mode = "photo+caption"
            else:
                response = send_message(
                    caption,
                    reply_markup=reply_markup,
                )
                send_mode = "text"

            if not response.get("ok"):
                raise TelegramOutcomeUnknown("response_missing_success_confirmation")
            telegram_accepted = True

            telegram_message_id = (
                response.get("result", {}).get("message_id")
            )

            # SOLO después de Telegram OK.
            publication_id = record_publication(
                product_id=product_id,
                source=offer.source,
                external_id=offer.external_id,
                title=offer.title,
                category=offer.category,
                price=offer.current_price,
                discount_pct=current_discount,
                score=score,
                telegram_message_id=telegram_message_id,
            )

            run_count += 1

            print(
                f"[PUBLISHER] ✅ PUBLICADA "
                f"{offer.source}:{offer.external_id} "
                f"({send_mode}) "
                f"message_id={telegram_message_id} "
                f"publication_id={publication_id}"
            )

            results.append({
                "status": "published",
                "product_id": product_id,
                "external_id": offer.external_id,
                "source": offer.source,
                "telegram_message_id": telegram_message_id,
                "publication_id": publication_id,
            })

            # El claim es exclusivamente un bloqueo de concurrencia.
            # Una vez registrada correctamente la publicación, se libera.
            release_publication_claim("tech", int(product_id))

            # Pausa entre publicaciones.
            if run_count < len(publicable_rows):
                time.sleep(2)

        except TelegramRequestRejected as exc:
            release_publication_claim("tech", int(product_id))
            results.append({"status": "rejected", "product_id": product_id,
                            "external_id": offer.external_id, "source": offer.source,
                            "error": str(exc)})
        except TelegramOutcomeUnknown as exc:
            # Retain the claim until expiry to prevent a blind duplicate resend.
            results.append({"status": "unknown_outcome", "product_id": product_id,
                            "external_id": offer.external_id, "source": offer.source,
                            "error": str(exc)})
        except Exception as exc:
            if not request_started:
                release_publication_claim("tech", int(product_id))
            results.append({"status": "published_unrecorded" if telegram_accepted else "error",
                            "product_id": product_id, "external_id": offer.external_id,
                            "source": offer.source, "error_type": type(exc).__name__})

            # No se registra la publicación.
            # Continuamos con las demás ofertas.

    return results
