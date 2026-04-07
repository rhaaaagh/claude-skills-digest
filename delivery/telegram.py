"""Send message to user via Telegram Bot API."""
import logging
from typing import Optional

import httpx

from config import BOT_TOKEN, CHAT_ID

logger = logging.getLogger(__name__)

TELEGRAM_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4096


def send_message(text: str, chat_id: Optional[str] = None) -> bool:
    """
    Send text to Telegram. If text exceeds 4096 chars, split into multiple messages.
    """
    chat = chat_id or CHAT_ID
    if not BOT_TOKEN or not chat:
        logger.warning("BOT_TOKEN or CHAT_ID not set; skip send")
        return False
    url = TELEGRAM_SEND_URL.format(token=BOT_TOKEN)
    payload = {"chat_id": chat, "text": text, "disable_web_page_preview": True}
    if len(text) <= MAX_MESSAGE_LENGTH:
        try:
            r = httpx.post(url, json=payload, timeout=30)
            r.raise_for_status()
            return True
        except Exception as e:
            logger.exception("Telegram send failed: %s", e)
            return False
    # Split by paragraphs, then by length if needed
    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH and current:
            parts.append(current.strip())
            current = ""
        current += line + "\n"
    if current.strip():
        parts.append(current.strip())
    # Ensure no part exceeds limit (e.g. single very long line)
    final_parts = []
    for part in parts:
        if len(part) <= MAX_MESSAGE_LENGTH:
            final_parts.append(part)
        else:
            for i in range(0, len(part), MAX_MESSAGE_LENGTH):
                final_parts.append(part[i : i + MAX_MESSAGE_LENGTH])
    ok = True
    for part in final_parts:
        try:
            r = httpx.post(url, json={**payload, "text": part}, timeout=30)
            r.raise_for_status()
        except Exception as e:
            logger.exception("Telegram send failed: %s", e)
            ok = False
    return ok


def send_message_plain(text: str, chat_id: Optional[str] = None) -> bool:
    """Send without parse_mode (avoid HTML errors)."""
    chat = chat_id or CHAT_ID
    if not BOT_TOKEN or not chat:
        return False
    url = TELEGRAM_SEND_URL.format(token=BOT_TOKEN)
    payload = {"chat_id": chat, "text": text, "disable_web_page_preview": True}
    if len(text) > MAX_MESSAGE_LENGTH:
        for i in range(0, len(text), MAX_MESSAGE_LENGTH):
            chunk = text[i : i + MAX_MESSAGE_LENGTH]
            try:
                r = httpx.post(url, json={**payload, "text": chunk}, timeout=30)
                r.raise_for_status()
            except Exception as e:
                logger.exception("Telegram send chunk failed: %s", e)
                return False
        return True
    try:
        r = httpx.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.exception("Telegram send failed: %s", e)
        return False
