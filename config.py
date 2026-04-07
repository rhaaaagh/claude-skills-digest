"""Configuration: load .env and constants."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SEEN_JSON = DATA_DIR / "seen.json"

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

MAX_ITEMS_IN_DIGEST = int(os.getenv("MAX_ITEMS_IN_DIGEST", "2"))
