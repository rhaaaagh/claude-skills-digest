# Claude Code Skills & Agents Digest Bot

Автоматический Telegram-бот, который ежедневно собирает материалы из **[skills.sh](https://skills.sh/)** (лидерборд по установкам) и **[cultofclaude.com](https://cultofclaude.com)** (топ skills/agents), генерирует сводку на русском через **Groq (Llama 3.3)** и отправляет в Telegram. Для записей с **skills.sh** в сообщении указывается прямая ссылка на карточку на сайте, без ссылки на GitHub.

Работает полностью автоматизированно через **GitHub Actions** — бесплатно, без локального компьютера.

## Как это работает

```
GitHub Actions (cron ежедневно 09:00 UTC)
  → Парсинг skills.sh (лидерборд) + cultofclaude.com
  → Для cultofclaude — GitHub с detail-страниц; для skills.sh — только URL на skills.sh
  → Фильтрация уже отправленных (seen.json)
  → Генерация сводки через Groq LLM
  → Отправка в Telegram
  → Сохранение отправленных URL (коммит seen.json)
```

## Быстрый старт

### 1. Форкните / создайте репозиторий на GitHub

### 2. Добавьте Secrets

`Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Описание |
|--------|----------|
| `BOT_TOKEN` | Токен Telegram-бота от @BotFather |
| `CHAT_ID` | ID чата (получить: отправить боту сообщение, затем `https://api.telegram.org/bot<TOKEN>/getUpdates`) |
| `GROQ_API_KEY` | API-ключ Groq (бесплатно: [console.groq.com](https://console.groq.com)) |

### 3. Готово

GitHub Actions запустится:
- **Автоматически** — каждый день в 09:00 UTC
- **Вручную** — вкладка Actions → Run workflow

## Локальный запуск (опционально)

```bash
pip install -r requirements.txt
cp .env.example .env
# заполнить .env своими ключами
python run_pipeline.py
```

## Структура

```
collector/
  skills_sh.py      — парсинг skills.sh (лидерборд, ссылка на карточку сайта)
  cultofclaude.py   — парсинг cultofclaude.com
  base.py           — модель данных SkillItem
  runner.py         — оркестратор коллекторов
pipeline/
  normalize.py      — дедупликация
  filter.py         — фильтрация seen + лимиты
  summarizer.py     — генерация сводки через Groq
storage/
  json_store.py     — хранение seen URLs в JSON
delivery/
  telegram.py       — отправка в Telegram
config.py           — конфигурация из .env
run_pipeline.py     — точка входа
```
