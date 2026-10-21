from __future__ import annotations

import json
import os
import time

import requests

import config
from ha_publish_guard import deny_reason, publishing_enabled
from telegram_format import format_channel_offer
from pet_channel import (
    pet_kind, record_pet_publication, is_recent_pet_duplicate,
    claim_pet_publication, release_pet_publication_claim,
)
from redirector.link_manager import get_or_create_product_link
from telegram_api import TelegramOutcomeUnknown, TelegramRequestRejected, send as telegram_send

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
CHAT_ID = os.getenv("MASCOTAS_TELEGRAM_CHAT_ID", "")
DRY_RUN = os.getenv("MASCOTAS_TELEGRAM_DRY_RUN", "1") not in {"0", "false", "no"}
MAX_PER_RUN = int(os.getenv("MASCOTAS_MAX_PUBLICATIONS_PER_RUN", "8"))

LABELS = {
    "dog": "🐶 PERROS",
    "cat": "🐱 GATOS",
    "pet_care": "🧼 CUIDADO",
    "pet_accessories": "🐾 ACCESORIOS",
    "aquarium": "🐠 ACUARIO",
}


def _api(method, payload):
    return telegram_send(BOT_TOKEN, method, payload)


def _caption(row):
    score, offer, history, breakdown, classification = row
    return format_channel_offer(offer, "mascotas", history=history)


def publish_pet(publicable_rows, force=False):
    if not publishing_enabled("mascotas"):
        print(f"[PET-PUBLISHER] BLOQUEADA HA: {deny_reason('mascotas')}")
        return []

    if not CHAT_ID:
        print("[PET-PUBLISHER] Sin MASCOTAS_TELEGRAM_CHAT_ID: canal aún no conectado.")
        return []

    results = []
    for row in publicable_rows[:MAX_PER_RUN]:
        score, offer, history, breakdown, classification = row
        if DRY_RUN and not force:
            results.append({
                "status": "dry_run",                "source": offer.source,
                "external_id": offer.external_id,
                "kind": pet_kind(offer),
            })
            continue

        product_id = int(getattr(offer, "product_id"))
        blocked, reason = is_recent_pet_duplicate(product_id=product_id, current_title=offer.title)
        if blocked:
            results.append({"status": "skipped_duplicate", "source": offer.source, "external_id": offer.external_id, "reason": reason})
            continue
        if not claim_pet_publication(product_id, offer.title):
            results.append({"status": "skipped_claimed", "source": offer.source, "external_id": offer.external_id})
            continue

        try:
            public_url = offer.affiliate_url
            if offer.source != "amazon":
                public_url = get_or_create_product_link(
                    int(getattr(offer, "product_id")),
                    offer.affiliate_url,
                    "mascotas",
                    "telegram_mascotas",
                )
            reply_markup = json.dumps({
                "inline_keyboard": [[{"text": "🛒 VER OFERTA", "url": public_url}]]
            }, ensure_ascii=False)
        except Exception as exc:
            release_pet_publication_claim(product_id)
            results.append({"status": "error", "source": offer.source,
                            "external_id": offer.external_id,
                            "error_type": type(exc).__name__})
            continue

        request_started = False
        telegram_accepted = False
        try:
            request_started = True
            response = _api("sendPhoto", {
                "chat_id": CHAT_ID,
                "photo": offer.image_url,
                "caption": _caption(row),
                "parse_mode": "HTML",
                "reply_markup": reply_markup,
            })
            telegram_accepted = True
            message_id = response["result"]["message_id"]
            publication_id = record_pet_publication(
                offer, score, telegram_message_id=message_id
            )
            results.append({
                "status": "published",
                "publication_id": publication_id,
                "telegram_message_id": message_id,
                "source": offer.source,
                "external_id": offer.external_id,
            })
            release_pet_publication_claim(product_id)
            time.sleep(2)
        except TelegramRequestRejected as exc:
            release_pet_publication_claim(product_id)
            results.append({"status": "rejected", "source": offer.source,
                            "external_id": offer.external_id, "error": str(exc)})
        except TelegramOutcomeUnknown as exc:
            # Retain the claim: Telegram may already have accepted the message.
            results.append({"status": "unknown_outcome", "source": offer.source,
                            "external_id": offer.external_id, "error": str(exc)})
        except Exception as exc:
            if not request_started:
                release_pet_publication_claim(product_id)
            results.append({"status": "published_unrecorded" if telegram_accepted else "error",
                            "source": offer.source, "external_id": offer.external_id,
                            "error_type": type(exc).__name__})
    return results


if __name__ == "__main__":
    print("AhorroScan Mascotas publisher preparado. Requiere el canal Telegram y MASCOTAS_TELEGRAM_CHAT_ID.")