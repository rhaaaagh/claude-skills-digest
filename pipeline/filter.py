"""Filter: exclude already-sent items, apply limits."""
import logging
from typing import List, Set

from collector.base import SkillItem
from config import MAX_ITEMS_IN_DIGEST

logger = logging.getLogger(__name__)


def filter_items(
    items: List[SkillItem],
    seen_urls: Set[str],
    max_items: int = MAX_ITEMS_IN_DIGEST,
) -> List[SkillItem]:
    """
    Remove items whose page_url or github_url was already sent.
    Sort by rating descending, limit to max_items.
    """
    fresh = []
    for item in items:
        if item.page_url in seen_urls:
            continue
        if item.github_url and item.github_url in seen_urls:
            continue
        fresh.append(item)

    fresh.sort(key=lambda x: -x.rating)
    result = fresh[:max_items]
    logger.info("Filter: %d -> %d items (seen=%d, limit=%d)",
                len(items), len(result), len(seen_urls), max_items)
    return result
