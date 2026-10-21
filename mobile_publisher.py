from __future__ import annotations

import os
import time
import json
import requests

import config
from ha_publish_guard import deny_reason, publishing_enabled
from telegram_format import format_channel_offer
from mobile_channel import record_mobile_publication, mobile_recently_published
from publication_guard import claim_publication, release_publication_claim
from telegram_api import TelegramOutcomeUnknown, TelegramRequestRejected, send as telegram_send
from redirector.link_manager import get_or_create_product_link

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
CHAT_ID = os.getenv("MOVILES_TELEGRAM_CHAT_ID", "")
DRY_RUN = os.getenv("MOVILES_TELEGRAM_DRY_RUN", "1") not in {"0", "false", "no"}
MAX_PER_RUN = int(os.getenv("MOVILES_MAX_PUBLICATIONS_PER_RUN", "8"))


def _api(method, payload):
    return telegram_send(BOT_TOKEN, method, payload)


def _caption(row):
    score, offer, history, breakdown, classification = row
    return format_channel_offer(offer, "moviles", history=history)


def publish_mobile(publicable_rows, force=False):
    if not publishing_enabled("moviles"):
        print(f"[MOBILE-PUBLISHER] BLOQUEADA HA: {deny_reason('moviles')}")
        return []

    if not CHAT_ID:
        print("[MOBILE-PUBLISHER] Sin MOVILES_TELEGRAM_CHAT_ID: canal aún no conectado.")
        return []

    results = []

    for row in publicable_rows[:MAX_PER_RUN]:
        score, offer, history, breakdown, classification = row
        product_id = getattr(offer, "product_id", None)
        source = getattr(offer, "source", "") or ""
        external_id = getattr(offer, "external_id", "") or ""
        title = getattr(offer, "title", "") or ""

        if product_id is None or not title.strip():
            results.append({
                "status": "invalid_identity",
                "source": source,
                "external_id": external_id,
            })
            continue

        identity = {
            "product_id": product_id,
            "source": source,
            "external_id": external_id,
            "title": title,
        }
        try:
            if mobile_recently_published(**identity):
                results.append({
                    "status": "recently_published",
                    "source": source,
                    "external_id": external_id,
                    "product_id": product_id,
                })
                continue
        except Exception as exc:
            # Fail closed if publication history cannot be read.
            results.append({
                "status": "history_unavailable",
                "source": source,
                "external_id": external_id,
                "error_type": type(exc).__name__,
            })
            continue

        if DRY_RUN and not force:
            results.append({
                "status": "dry_run",
                "source": source,
                "external_id": external_id,
                "kind": "smartphone" if getattr(offer, "category", "") == "smartphones" else "accessory",
            })
            continue

        try:
            claimed = claim_publication("moviles", int(product_id), title)
        except Exception as exc:
            results.append({
                "status": "guard_unavailable",
                "source": source,
                "external_id": external_id,
                "error_type": type(exc).__name__,
            })
            continue

        if not claimed:
            results.append({
                "status": "already_claimed",
                "source": source,
                "external_id": external_id,
                "product_id": product_id,
            })
            continue

        request_started = False
        telegram_accepted = False
        try:
            caption = _caption(row)
            public_url = offer.affiliate_url
            if source != "amazon":
                public_url = get_or_create_product_link(
                    int(product_id),
                    offer.affiliate_url,
                    "moviles",
                    "telegram_moviles",
                )

            reply_markup = json.dumps({
                "inline_keyboard": [[{"text": "🛒 VER OFERTA", "url": public_url}]]
            }, ensure_ascii=False)
            payload = {
                "chat_id": CHAT_ID,
                "photo": offer.image_url,
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": reply_markup,
            }

            request_started = True
            response = _api("sendPhoto", payload)
            telegram_accepted = True
            message_id = response["result"]["message_id"]

            try:
                publication_id = record_mobile_publication(
                    offer, score, telegram_message_id=message_id
                )
            except Exception as exc:
                # Keep the claim: the post exists, but its local record needs reconciliation.
                results.append({
                    "status": "published_unrecorded",
                    "telegram_message_id": message_id,
                    "source": source,
                    "external_id": external_id,
                    "error_type": type(exc).__name__,
                })
                continue

            try:
                release_publication_claim("moviles", int(product_id))
            except Exception as exc:
                # The publication row itself still prevents a repeat.
                results.append({
                    "status": "published_claim_retained",
                    "publication_id": publication_id,
                    "telegram_message_id": message_id,
                    "source": source,
                    "external_id": external_id,
                    "error_type": type(exc).__name__,
                })
                continue

            results.append({
                "status": "published",
                "publication_id": publication_id,
                "telegram_message_id": message_id,
                "source": source,
                "external_id": external_id,
            })
            time.sleep(2)

        except TelegramRequestRejected as exc:
            try:
                release_publication_claim("moviles", int(product_id))
            except Exception:
                pass
            results.append({
                "status": "rejected",
                "source": source,
                "external_id": external_id,
                "error": str(exc),
            })
        except Exception as exc:
            if not request_started:
                try:
                    release_publication_claim("moviles", int(product_id))
                except Exception:
                    pass
            results.append({
                "status": "published_unrecorded" if telegram_accepted else "unknown_outcome" if request_started else "error",
                "source": source,
                "external_id": external_id,
                "error_type": type(exc).__name__,
            })

    return results


if __name__ == "__main__":
    print("AhorroScan Móviles publisher preparado. Requiere el canal Telegram y MOVILES_TELEGRAM_CHAT_ID.")