"""Scrape cultofclaude.com for top-rated skills and agents."""
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base import SkillItem

logger = logging.getLogger(__name__)

BASE_URL = "https://cultofclaude.com"
HEADERS = {
    "User-Agent": "CultOfClaude-Digest/1.0 (GitHub Actions bot)",
    "Accept": "text/html,application/xhtml+xml",
}
TIMEOUT = 20

_GH_RE = re.compile(
    r"https?://(?:raw\.)?github(?:usercontent)?\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"
)


def _extract_github_url(text: str) -> str:
    """Find first github.com/owner/repo URL in text and normalise it."""
    m = _GH_RE.search(text)
    if not m:
        return ""
    owner, repo = m.group(1), m.group(2)
    repo = repo.split("/")[0].removesuffix(".git")
    return f"https://github.com/{owner}/{repo}"


def _parse_homepage_section(soup: BeautifulSoup, heading_text: str) -> List[dict]:
    """
    Find a heading containing `heading_text` and collect <a> links after it
    that point to /skills/ or /agents/ detail pages.
    Returns list of dicts: {slug, page_url, rating, title, description, item_type}.
    """
    items: List[dict] = []
    heading = None
    for h in soup.find_all(["h2", "h3"]):
        if heading_text.lower() in (h.get_text() or "").lower():
            heading = h
            break
    if not heading:
        return items

    container = heading.find_next_sibling() or heading.parent
    if container is None:
        container = heading.parent or soup

    links = container.find_all("a", href=True) if container else []
    if not links:
        links = []
        for el in heading.find_all_next("a", href=True, limit=20):
            href = el["href"]
            if "/skills/" in href or "/agents/" in href:
                links.append(el)

    for a in links:
        href = a["href"]
        if "/skills/" not in href and "/agents/" not in href:
            continue
        full_url = urljoin(BASE_URL, href)
        item_type = "skill" if "/skills/" in href else "agent"
        slug = href.rstrip("/").split("/")[-1]

        text = (a.get_text(separator=" ", strip=True) or "").strip()
        rating = 0
        title = text
        description = ""

        m = re.match(r"(\d{1,3})\s+(.+)", text)
        if m:
            rating = int(m.group(1))
            rest = m.group(2).strip()
            parts = re.split(r"\s{2,}|\|", rest, maxsplit=1)
            title = parts[0].strip()
            if len(parts) > 1:
                description = parts[1].strip()
            elif len(rest) > len(title) + 3:
                first_sentence_end = rest.find(". ", len(title))
                if first_sentence_end == -1:
                    first_sentence_end = min(len(rest), 80)
                title_candidate = rest[:first_sentence_end + 1].strip()
                if len(title_candidate) > 60:
                    title = rest[:50].strip()
                    description = rest[50:].strip()
                else:
                    title = title_candidate

        items.append({
            "slug": slug,
            "page_url": full_url,
            "rating": rating,
            "title": title,
            "description": description,
            "item_type": item_type,
        })

    return items


def fetch_homepage_items() -> List[dict]:
    """
    Fetch cultofclaude.com homepage and extract top-rated skills + agents.
    """
    try:
        r = httpx.get(BASE_URL, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        logger.error("Failed to fetch homepage: %s", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    items: List[dict] = []
    for section in ["Top Rated Skills", "Top Rated Agents", "Discover"]:
        found = _parse_homepage_section(soup, section)
        logger.info("Homepage section '%s': found %d items", section, len(found))
        items.extend(found)

    seen_slugs = set()
    deduped = []
    for it in items:
        if it["slug"] not in seen_slugs:
            seen_slugs.add(it["slug"])
            deduped.append(it)

    return deduped


def fetch_detail_page(page_url: str) -> dict:
    """
    Fetch a skill/agent detail page and extract github_url, description, author, category.
    """
    info = {"github_url": "", "description": "", "author": "", "category": ""}
    try:
        r = httpx.get(page_url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", page_url, e)
        return info

    soup = BeautifulSoup(r.text, "html.parser")
    page_text = soup.get_text(separator="\n")

    info["github_url"] = _extract_github_url(page_text)

    h1 = soup.find("h1")
    if h1:
        prev_text = ""
        for sib in h1.previous_siblings:
            t = getattr(sib, "get_text", lambda: str(sib))()
            t = t.strip()
            if t and len(t) < 60:
                prev_text = t
                break
        info["author"] = prev_text

        next_text = ""
        for sib in h1.next_siblings:
            t = getattr(sib, "get_text", lambda **kw: str(sib))(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if t and len(t) > 3:
                next_text = t
                break
        if next_text:
            info["category"] = next_text.split("\n")[0].strip()

    desc_heading = None
    for h in soup.find_all(["h2", "h3"]):
        if "description" in (h.get_text() or "").lower():
            desc_heading = h
            break
    if desc_heading:
        desc_parts = []
        for sib in desc_heading.next_siblings:
            if hasattr(sib, "name") and sib.name in ("h1", "h2", "h3"):
                break
            t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if t:
                desc_parts.append(t)
        info["description"] = " ".join(desc_parts)[:500]

    return info


def collect(max_items: int = 20) -> List[SkillItem]:
    """
    Main entry: scrape homepage for top items, fetch detail pages, return SkillItems.
    """
    homepage_items = fetch_homepage_items()
    logger.info("Total homepage items (deduped): %d", len(homepage_items))

    results: List[SkillItem] = []
    for item in homepage_items[:max_items]:
        detail = fetch_detail_page(item["page_url"])

        description = detail["description"] or item.get("description", "")

        results.append(SkillItem(
            title=item["title"],
            slug=item["slug"],
            page_url=item["page_url"],
            github_url=detail["github_url"],
            description=description,
            rating=item.get("rating", 0),
            category=detail.get("category", ""),
            author=detail.get("author", ""),
            item_type=item["item_type"],
        ))

    results.sort(key=lambda x: -x.rating)
    logger.info("Collected %d skills/agents with details", len(results))
    return results
