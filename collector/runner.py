"""Run collector and return skill/agent items."""
import logging
from typing import List

from .base import SkillItem
from .cultofclaude import collect as collect_cultofclaude
from .skills_sh import collect as collect_skills_sh

logger = logging.getLogger(__name__)


def run_collectors(max_items: int = 20) -> List[SkillItem]:
    """Scrape skills.sh leaderboard + Cult of Claude; merge lists."""
    out: List[SkillItem] = []
    try:
        out.extend(collect_skills_sh(max_items=max_items))
    except Exception as e:
        logger.exception("skills.sh collector failed: %s", e)
    try:
        out.extend(collect_cultofclaude(max_items=max_items))
    except Exception as e:
        logger.exception("CultOfClaude collector failed: %s", e)
    return out
