"""Build digest text via LLM (Groq / Llama)."""
import logging
from typing import List

from openai import OpenAI

from collector.base import SkillItem
from config import GROQ_API_KEY, GROQ_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — помощник, который пишет краткие описания инструментов для Claude Code на русском.\n"
    "Тебе дают список items. Для КАЖДОГО напиши РОВНО 2 строки:\n"
    "- Строка 1: Что это и что делает (1 предложение, начни с описания)\n"
    "- Строка 2: Кому полезен / зачем нужен (1 предложение, начни со слова 'Полезен')\n\n"
    "ФОРМАТ ОТВЕТА — строго такой (N — номер item):\n"
    "[N] строка1\n"
    "[N] строка2\n\n"
    "Пример:\n"
    "[1] Это агент для проектирования и развертывания AI-систем.\n"
    "[1] Полезен разработчикам, которые внедряют машинное обучение в продакшн.\n\n"
    "Не добавляй ничего кроме этого формата. Без вступлений, без заключений."
)


def _format_items_for_prompt(items: List[SkillItem]) -> str:
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(
            f"{i}. [{it.item_type.upper()}] {it.title}\n"
            f"   Описание (en): {it.description or 'нет'}"
        )
    return "\n".join(lines)


def _parse_llm_summaries(text: str, count: int) -> dict:
    """Parse LLM output into {item_number: (line1, line2)} dict."""
    summaries = {}
    for n in range(1, count + 1):
        lines_for_n = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith(f"[{n}]"):
                content = stripped[len(f"[{n}]"):].strip()
                if content:
                    lines_for_n.append(content)
        if len(lines_for_n) >= 2:
            summaries[n] = (lines_for_n[0], lines_for_n[1])
        elif len(lines_for_n) == 1:
            summaries[n] = (lines_for_n[0], "")
    return summaries


def build_summary(items: List[SkillItem]) -> str:
    """
    Call Groq LLM, get per-item Russian summaries,
    format final message with GitHub links inline.
    """
    if not items:
        return ""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set, falling back to plain format")
        return ""

    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

    user_msg = (
        "Вот список Claude Code skills/agents. Опиши каждый по формату из инструкции.\n\n"
        + _format_items_for_prompt(items)
    )

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if not raw:
            return ""
    except Exception as e:
        logger.exception("LLM request failed: %s", e)
        return ""

    summaries = _parse_llm_summaries(raw, len(items))
    return _format_message(items, summaries)


def _format_message(items: List[SkillItem], summaries: dict) -> str:
    """Build the final Telegram message with inline GitHub links."""
    header = "🤖 Claude Code — Дайджест Skills & Agents\n"
    header += f"Новых: {len(items)}\n"
    header += "━" * 30 + "\n\n"

    parts = [header]
    for i, it in enumerate(items, 1):
        tag = it.item_type.upper()
        desc_short = (it.description or "")[:80]
        gh = it.github_url or it.page_url

        line1, line2 = summaries.get(i, ("", ""))

        block = f"{i}. [{tag}] {it.title} {desc_short}"
        if line1:
            block += f": {line1}"
        if line2:
            block += f"\n{line2}"
        block += f"\n{gh}\n"

        parts.append(block)

    return "\n".join(parts).strip()


def build_fallback_summary(items: List[SkillItem]) -> str:
    """Plain-text digest without LLM — same inline format."""
    if not items:
        return ""

    header = "🤖 Claude Code — Дайджест Skills & Agents\n"
    header += f"Новых: {len(items)}\n"
    header += "━" * 30 + "\n\n"

    parts = [header]
    for i, it in enumerate(items, 1):
        tag = it.item_type.upper()
        desc = (it.description or "")[:150]
        gh = it.github_url or it.page_url

        block = f"{i}. [{tag}] {it.title} {desc}\n{gh}\n"
        parts.append(block)

    return "\n".join(parts).strip()
