import os

# ─── ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ─────────────────────────────
BOT_TOKEN: str = os.environ["BOT_TOKEN"]          # Токен от @BotFather
ADMIN_ID: int = int(os.environ["ADMIN_ID"])       # Твой Telegram ID

# ─── ФАЙЛ С АРХИВОМ ──────────────────────────────────────
# Путь до zip-архива с видео (лежит рядом с ботом)
VIDEO_ARCHIVE_PATH: str = os.environ.get("VIDEO_ARCHIVE_PATH", "пантера.zip")

# ─── СТОИМОСТЬ В STARS ───────────────────────────────────
STARS_PRICE: int = int(os.environ.get("STARS_PRICE", "25"))
