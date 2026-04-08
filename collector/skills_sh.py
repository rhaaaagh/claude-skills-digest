"""Scrape skills.sh leaderboard — links point to skills.sh, not GitHub."""
import logging
import re
from typing import List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base import SkillItem

logger = logging.getLogger(__name__)

BASE = "https://skills.sh"
HEADERS = {
    "User-Agent": "ClaudeSkillsDigest/1.0 (GitHub Actions bot)",
    "Accept": "text/html,application/xhtml+xml",
}
TIMEOUT = 25

# /owner/repo/skill-name (skill may contain : for scoped names)
HREF_RE = re.compile(r"^/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.:-]+$")


def _parse_install_label(text: str) -> str:
    t = (text or "").strip()
    if re.search(r"[KM]", t, re.I):
        return t
    return ""


def collect(max_items: int = 30) -> List[SkillItem]:
    """
    Parse skills.sh homepage leaderboard: each row links to a skill page on skills.sh.
    github_url is always empty — primary link is page_url on skills.sh.
    """
    try:
        r = httpx.get(BASE + "/", headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        logger.error("skills.sh fetch failed: %s", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items: List[SkillItem] = []
    seen_href = set()

    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not HREF_RE.match(href) or href in seen_href:
            continue
        seen_href.add(href)

        h3 = a.find("h3")
        p = a.find("p")
        title = (h3.get_text(strip=True) if h3 else "") or href.rstrip("/").split("/")[-1]
        repo = (p.get_text(strip=True) if p else "") or ""

        install_label = ""
        for span in a.find_all("span"):
            txt = span.get_text(strip=True)
            if _parse_install_label(txt):
                install_label = txt
                break

        slug = href.rstrip("/").split("/")[-1]
        page_url = urljoin(BASE, href)
        desc_parts = [f"Каталог: skills.sh — репозиторий `{repo}`" if repo else "Каталог: skills.sh"]
        if install_label:
            desc_parts.append(f"установок (по данным сайта): {install_label}")
        description = ". ".join(desc_parts)

        rating = max(1, 100 - len(items))

        items.append(
            SkillItem(
                title=title,
                slug=slug,
                page_url=page_url,
                github_url="",
                description=description,
                rating=rating,
                category="skills.sh leaderboard",
                author=repo.split("/")[0] if "/" in repo else "",
                item_type="skill",
                source="skills.sh",
            )
        )

        if len(items) >= max_items:
            break

    logger.info("skills.sh: collected %d items", len(items))
    return items
