"""Base types for collected items."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SkillItem:
    """One skill or agent from Cult of Claude."""
    title: str
    slug: str
    page_url: str
    github_url: str
    description: str
    rating: int = 0
    category: str = ""
    author: str = ""
    item_type: str = "skill"  # "skill" | "agent"
