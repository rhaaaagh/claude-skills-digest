"""Persistent seen-URLs storage via JSON file (git-friendly)."""
import json
import logging
from datetime import datetime, timedelta
from typing import Set

from config import SEEN_JSON

logger = logging.getLogger(__name__)


def _load() -> list:
    if not SEEN_JSON.exists():
        return []
    try:
        data = json.loads(SEEN_JSON.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(entries: list) -> None:
    SEEN_JSON.parent.mkdir(parents=True, exist_ok=True)
    SEEN_JSON.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_seen_urls(limit_days: int = 90) -> Set[str]:
    """Return set of URLs already sent (within limit_days)."""
    entries = _load()
    cutoff = (datetime.utcnow() - timedelta(days=limit_days)).isoformat()
    return {e["url"] for e in entries if e.get("date", "") >= cutoff}


def save_urls(urls: list) -> None:
    """Append new URLs as seen."""
    if not urls:
        return
    entries = _load()
    existing = {e["url"] for e in entries}
    now = datetime.utcnow().isoformat()
    for u in urls:
        if u and u not in existing:
            entries.append({"url": u, "date": now})
    _save(entries)
    logger.info("Saved %d new URLs to seen.json", len(urls))


def cleanup_old(days: int = 90) -> None:
    """Remove entries older than `days`."""
    entries = _load()
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    fresh = [e for e in entries if e.get("date", "") >= cutoff]
    if len(fresh) < len(entries):
        logger.info("Cleanup: removed %d old entries", len(entries) - len(fresh))
        _save(fresh)
