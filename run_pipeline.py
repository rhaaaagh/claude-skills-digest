#!/usr/bin/env python3
"""
Single run: collect -> normalize -> filter -> summarize -> deliver.
Designed to run via GitHub Actions cron or manually.
"""
import logging
import sys

from config import BOT_TOKEN, CHAT_ID, GROQ_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("digest")


def main() -> None:
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("BOT_TOKEN and CHAT_ID must be set")
        sys.exit(1)

    from collector.runner import run_collectors
    from pipeline.normalize import normalize
    from pipeline.filter import filter_items
    from pipeline.summarizer import build_summary, build_fallback_summary
    from storage.json_store import get_seen_urls, save_urls, cleanup_old
    from delivery.telegram import send_message

    logger.info("Starting pipeline: collect -> filter -> summarize -> deliver")

    cleanup_old(days=90)

    raw_items = run_collectors(max_items=20)
    logger.info("Collected: %d items", len(raw_items))

    items = normalize(raw_items)
    seen = get_seen_urls()
    filtered = filter_items(items, seen)
    logger.info("After filter: %d new items", len(filtered))

    if not filtered:
        logger.info("No new items; sending short notice.")
        send_message("Сегодня новых Claude Code skills/agents не найдено. Всё уже было отправлено ранее.")
        return

    message = build_summary(filtered)
    if not message:
        logger.warning("LLM summary failed or no API key; using fallback format")
        message = build_fallback_summary(filtered)

    send_message(message)

    urls_to_save = []
    for it in filtered:
        urls_to_save.append(it.page_url)
        if it.github_url:
            urls_to_save.append(it.github_url)
    save_urls(urls_to_save)

    logger.info("Done. Delivered %d items, saved %d URLs.", len(filtered), len(urls_to_save))


if __name__ == "__main__":
    main()
