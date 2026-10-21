from __future__ import annotations

import html
import json
import os
import time
import requests

import config
from ha_publish_guard import deny_reason, publishing_enabled
from telegram_format import format_channel_offer
from redirector.link_manager import get_or_create_product_link
from vertical_channel import (
    CHANNELS,
    already_published,
    record_publication,
)
from publication_guard import claim_publication, release_publication_claim
from telegram_api import TelegramOutcomeUnknown, TelegramRequestRejected, send as telegram_send


BOT_TOKEN = config.TELEGRAM_BOT_TOKEN


def _api(method, payload):
    return telegram_send(BOT_TOKEN, method, payload)


def publish(channel, rows, force=False):
    cfg = CHANNELS[channel]

    chat = os.getenv(cfg["telegram_env"], "")
    dry = os.getenv(cfg["dry_env"], "1").lower() not in {
        "0",
        "false",
        "no",
    }

    maximum = int(os.getenv(cfg["max_env"], "5"))

    if not publishing_enabled(channel):
        print(
            f"[VERTICAL-PUBLISHER] {channel} BLOQUEADA HA: "
            f"{deny_reason(channel)}"
        )
        return []

    if not chat:
        print(
            f"[VERTICAL-PUBLISHER] {channel} sin chat ID"
        )
        return []

    results = []

    for row in rows[:maximum]:
        score, offer, history, breakdown, classification = row

        product_id = getattr(offer, "product_id", None)

        # Comprobación inmediatamente antes de publicar.
        # La ventana actual es de 7 días.
        if already_published(
            channel,
            product_id,
            current_price=getattr(offer, "current_price", None),
            current_discount_pct=getattr(offer, "discount_pct", None),
            current_title=getattr(offer, "title", None),
        ):
            results.append(
                {
                    "status": "recently_published",
                    "external_id": offer.external_id,
                    "product_id": product_id,
                }
            )
            continue

        caption = format_channel_offer(offer, channel)

        public_url = offer.affiliate_url

        if offer.source != "amazon":
            public_url = get_or_create_product_link(
                int(offer.product_id),
                offer.affiliate_url,
                channel,
                f"telegram_{channel}",
            )

        markup = json.dumps(
            {
                "inline_keyboard": [
                    [
                        {
                            "text": "🛒 VER OFERTA",
                            "url": public_url,
                        }
                    ]
                ]
            },
            ensure_ascii=False,
        )

        if dry and not force:
            results.append(
                {
                    "status": "dry_run",
                    "external_id": offer.external_id,
                    "category": offer.category,
                }
            )
            continue

        if product_id is None or not claim_publication(channel, int(product_id), offer.title):
            results.append({"status": "already_claimed", "external_id": offer.external_id})
            continue

        request_started = False
        telegram_accepted = False
        try:
            request_started = True
            d = _api(
                "sendPhoto",
                {
                    "chat_id": chat,
                    "photo": offer.image_url,
                    "caption": caption,
                    "parse_mode": "HTML",
                    "reply_markup": markup,
                },
            )

            telegram_accepted = True
            mid = d["result"]["message_id"]

            publication_id = record_publication(
                channel,
                offer,
                score,
                mid,
            )

            results.append(
                {
                    "status": "published",
                    "publication_id": publication_id,
                    "telegram_message_id": mid,
                    "external_id": offer.external_id,
                    "product_id": product_id,
                }
            )

            release_publication_claim(channel, int(product_id))
            time.sleep(2)

        except TelegramRequestRejected as exc:
            release_publication_claim(channel, int(product_id))
            results.append({"status": "rejected", "external_id": offer.external_id,
                            "product_id": product_id, "error": str(exc)})
        except TelegramOutcomeUnknown as exc:
            # Keep the claim because Telegram may already have accepted the post.
            results.append({"status": "unknown_outcome", "external_id": offer.external_id,
                            "product_id": product_id, "error": str(exc)})
        except Exception as exc:
            if not request_started:
                release_publication_claim(channel, int(product_id))
            results.append({"status": "published_unrecorded" if telegram_accepted else "error",
                            "external_id": offer.external_id, "product_id": product_id,
                            "error_type": type(exc).__name__})

    return results
