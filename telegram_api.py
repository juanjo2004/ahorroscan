from __future__ import annotations

import time

import requests


class TelegramRequestRejected(RuntimeError):
    """Telegram explicitly rejected the request; retrying is unsafe or useless."""


class TelegramOutcomeUnknown(RuntimeError):
    """The request may have reached Telegram; do not automatically resend it."""


def _retry_after(response) -> float:
    try:
        body = response.json()
        value = body.get("parameters", {}).get("retry_after")
        if value is not None:
            return max(1.0, float(value))
    except (ValueError, TypeError, AttributeError):
        pass
    try:
        return max(1.0, float(response.headers.get("Retry-After", "1")))
    except (TypeError, ValueError, AttributeError):
        return 1.0


def send(token: str, method: str, payload: dict, timeout: int = 60) -> dict:
    """Send once; only retry Telegram's explicit rate-limit rejection."""
    endpoint = f"https://api.telegram.org/bot{token}/{method}"
    rate_limit_retries = 0
    while True:
        try:
            response = requests.post(endpoint, data=payload, timeout=timeout)
        except requests.RequestException as exc:
            raise TelegramOutcomeUnknown(type(exc).__name__) from None

        if response.status_code == 429:
            if rate_limit_retries >= 2:
                raise TelegramRequestRejected("http_429")
            time.sleep(_retry_after(response))
            rate_limit_retries += 1
            continue
        if response.status_code >= 500:
            raise TelegramOutcomeUnknown(f"http_{response.status_code}")
        if response.status_code >= 400:
            raise TelegramRequestRejected(f"http_{response.status_code}")

        try:
            data = response.json()
        except ValueError:
            raise TelegramOutcomeUnknown("invalid_json_response") from None

        if not data.get("ok"):
            code = data.get("error_code", "unknown")
            raise TelegramRequestRejected(f"telegram_api_error_{code}")
        if data.get("result", {}).get("message_id") is None:
            raise TelegramOutcomeUnknown("missing_message_id")
        return data
