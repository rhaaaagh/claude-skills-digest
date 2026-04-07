"""Normalize and deduplicate collected items."""
import logging
from typing import List
from urllib.parse import urlparse

from collector.base import SkillItem

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    s = (url or "").strip().lower()
    if not s:
        return ""
    parsed = urlparse(s)
    netloc = parsed.netloc or ""
    path = (parsed.path or "").rstrip("/") or "/"
    return f"{parsed.scheme or 'https'}://{netloc}{path}"


def normalize(items: List[SkillItem]) -> List[SkillItem]:
    """Deduplicate by page_url, trim descriptions."""
    seen = set()
    out = []
    for item in items:
        key = _normalize_url(item.page_url)
        if not key or key in seen:
            continue
        seen.add(key)
        item.description = (item.description or "").strip()[:500]
        item.title = (item.title or "").strip() or "Untitled"
        out.append(item)
    return out
