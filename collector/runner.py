"""Run collector and return skill/agent items."""
import logging
from typing import List

from .base import SkillItem
from .cultofclaude import collect as collect_cultofclaude

logger = logging.getLogger(__name__)


def run_collectors(max_items: int = 20) -> List[SkillItem]:
    """Scrape Cult of Claude for top skills & agents."""
    try:
        items = collect_cultofclaude(max_items=max_items)
    except Exception as e:
        logger.exception("CultOfClaude collector failed: %s", e)
        items = []
    return items
