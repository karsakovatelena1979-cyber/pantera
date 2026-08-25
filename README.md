# 🎬 Pantera Bot

Telegram-бот для продажи доступа к папке с видео за Stars или через TikTok-задание.

---

## 📁 Структура

```
pantera_bot/
├── bot.py           # Основной файл бота
├── config.py        # Конфигурация (читает env)
├── database.py      # SQLite через aiosqlite
├── requirements.txt
├── railway.json
├── Procfile
└── пантера.zip      # ← Архив с видео (добавь сам)
```

---

## 🚀 Деплой на Railway

### 1. Подготовка репозитория

```bash
git init
git add .
git commit -m "init"
# Создай репо на GitHub и запушь
git remote add origin https://github.com/твой-ник/pantera-bot.git
git push -u origin main
```

### 2. Деплой на Railway

1. Зайди на [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Выбери репо `pantera-bot`
3. В разделе **Variables** добавь переменные:

| Переменная | Значение |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `ADMIN_ID` | Твой Telegram ID (узнай у @userinfobot) |
| `VIDEO_ARCHIVE_PATH` | `пантера.zip` |
| `STARS_PRICE` | `25` |

### 3. Загрузка архива с видео

Так как Railway не поддерживает загрузку больших файлов через git — **загрузи архив через Volume** или используй ссылку.

**Вариант A — Railway Volume:**
- В Railway добавь Volume, примонтируй на `/data`
- Загрузи `пантера.zip` в Volume через Railway CLI:
  ```bash
  railway volume upload пантера.zip /data/пантера.zip
  ```
- Измени `VIDEO_ARCHIVE_PATH` на `/data/пантера.zip`

**Вариант B — через git (если архив < 100MB):**
- Убери `*.zip` из `.gitignore`
- Добавь архив в репо и запушь

---

## 🤖 Команды бота

### Для пользователей
- `/start` — начало работы

### Для администратора
- `/admin` — панель администратора
- `/stats` — статистика бота
- `/users` — список пользователей
- `/broadcast Текст` — рассылка всем пользователям

---

## 💡 Логика бота

```
/start
  └── Кнопка "Получить за 25 ⭐" → Инвойс → Оплата → Архив моментально
  └── Кнопка "Получить бесплатно"
        └── Инструкция + текст для TikTok
              └── Пользователь отправляет 10 скриншотов
                    └── Алерт админу с кнопками ✅/❌
                          ├── Принять → Архив пользователю
                          └── Отклонить → Уведомление пользователю
```
