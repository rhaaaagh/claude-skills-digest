"""Build digest text via LLM (Groq / Llama)."""
import logging
from typing import List

from openai import OpenAI

from collector.base import SkillItem
from config import GROQ_API_KEY, GROQ_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — помощник, который подробно описывает инструменты (skills/agents) для Claude Code на русском.\n"
    "Тебе дают 1-2 item. Для КАЖДОГО напиши:\n\n"
    "1) Что это и что делает (2-3 предложения)\n"
    "2) Кому полезен и зачем нужен (1-2 предложения)\n"
    "3) Примеры реализации — дай 2-3 конкретных идеи, как я могу это применить "
    "в своих проектах или заработать на этом. Каждую идею начинай с '•'\n\n"
    "ФОРМАТ ОТВЕТА — строго такой (N — номер item):\n"
    "[N:desc] текст описания\n"
    "[N:use] текст кому полезен\n"
    "[N:ideas]\n"
    "• идея 1\n"
    "• идея 2\n"
    "• идея 3\n\n"
    "Пример:\n"
    "[1:desc] AI Engineer — это агент-специалист по проектированию и развертыванию систем "
    "искусственного интеллекта. Помогает с архитектурой ML-пайплайнов, выбором моделей "
    "и настройкой инфраструктуры для обучения.\n"
    "[1:use] Полезен разработчикам и инженерам, которые внедряют ML/AI в продакшн "
    "и хотят ускорить процесс проектирования.\n"
    "[1:ideas]\n"
    "• Использовать как консультанта при создании своего AI-стартапа — агент поможет "
    "спроектировать архитектуру перед написанием кода\n"
    "• Подключить к CI/CD для автоматической проверки ML-кода и конфигов перед деплоем\n"
    "• Создать на его основе платный сервис код-ревью для AI/ML проектов на фрилансе\n\n"
    "Пиши по делу, с конкретикой. Без общих фраз."
)


def _format_items_for_prompt(items: List[SkillItem]) -> str:
    lines = []
    for i, it in enumerate(items, 1):
        lines.append(
            f"{i}. [{it.item_type.upper()}] {it.title}\n"
            f"   Описание (en): {it.description or 'нет'}\n"
            f"   GitHub: {it.github_url or 'нет'}"
        )
    return "\n\n".join(lines)


def _parse_llm_summaries(text: str, count: int) -> dict:
    """
    Parse LLM output into {item_number: {desc, use, ideas}} dict.
    """
    summaries = {}
    for n in range(1, count + 1):
        desc, use, ideas = "", "", ""

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith(f"[{n}:desc]"):
                desc = stripped[len(f"[{n}:desc]"):].strip()
            elif stripped.startswith(f"[{n}:use]"):
                use = stripped[len(f"[{n}:use]"):].strip()

        in_ideas = False
        idea_lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith(f"[{n}:ideas]"):
                in_ideas = True
                continue
            if in_ideas:
                if stripped.startswith("•") or stripped.startswith("-"):
                    idea_lines.append(stripped)
                elif stripped.startswith(f"[") and ":" in stripped:
                    in_ideas = False
                elif stripped == "":
                    if idea_lines:
                        in_ideas = False

        ideas = "\n".join(idea_lines)
        summaries[n] = {"desc": desc, "use": use, "ideas": ideas}

    return summaries


def build_summary(items: List[SkillItem]) -> str:
    """Call Groq LLM, get detailed per-item summaries with usage ideas."""
    if not items:
        return ""
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set, falling back to plain format")
        return ""

    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

    user_msg = (
        "Вот Claude Code skills/agents. Опиши каждый подробно по формату из инструкции.\n\n"
        + _format_items_for_prompt(items)
    )

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=3000,
            temperature=0.4,
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
    """Build the final Telegram message."""
    header = "🤖 Claude Code — Находка дня\n"
    header += "━" * 30 + "\n"

    parts = [header]
    for i, it in enumerate(items, 1):
        tag = it.item_type.upper()
        gh = it.github_url or it.page_url
        s = summaries.get(i, {})

        block = f"\n{i}. [{tag}] {it.title}\n"
        if s.get("desc"):
            block += f"{s['desc']}\n"
        if s.get("use"):
            block += f"\n{s['use']}\n"
        if s.get("ideas"):
            block += f"\n💡 Как применить:\n{s['ideas']}\n"
        block += f"\n🔗 {gh}"

        parts.append(block)

    return "\n".join(parts).strip()


def build_fallback_summary(items: List[SkillItem]) -> str:
    """Plain-text digest without LLM."""
    if not items:
        return ""

    header = "🤖 Claude Code — Находка дня\n"
    header += "━" * 30 + "\n"

    parts = [header]
    for i, it in enumerate(items, 1):
        tag = it.item_type.upper()
        desc = (it.description or "")[:200]
        gh = it.github_url or it.page_url

        block = f"\n{i}. [{tag}] {it.title}\n{desc}\n\n🔗 {gh}"
        parts.append(block)

    return "\n".join(parts).strip()
