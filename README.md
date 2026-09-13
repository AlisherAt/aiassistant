# Gold Trading AI Assistant

Полностью бесплатный и рабочий каркас ИИ-ассистента для торговли золотом на основе Yahoo Finance, FRED и локального AI fallback.

## Бесплатный стек

- Цена золота: Yahoo Finance (`GC=F` / `XAUUSD=X`)
- DXY: Yahoo Finance (`DX-Y.NYB` / `DX=F`)
- Real yield: FRED (`DFII10`)
- AI: local fallback без ключей
- Telegram: бесплатный бот
- SQLite: локальная база данных

## Что включено

- OHLCV-данные за 60 дней интервалом 15m, и более длинные дневные данные при необходимости
- режим рынка: trending / ranging / news_window
- стратегии: trend-following, mean reversion, correlation, ICT/SMC
- финальный AI-арбитр с weighted consensus
- SQLite для хранения сигналов
- Telegram-уведомления
- CLI-оркестратор в demo/live режимах

## Быстрый старт

```bash
cd "c:\Users\Alisher\Desktop\ии ассистент"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --demo --json
```

## Live-режим без платных ключей

```bash
python main.py --live --json
```

## Файлы проекта

- app/data — источники данных и коннекторы
- app/strategies — торговые сигналы
- app/regime — режим рынка
- app/ai — AI-арбитр и Claude-клиент
- app/storage — SQLite
- app/notify — Telegram
- app/orchestrator.py — связка всего в один движок
- main.py — точка входа

## Переменные окружения

Скопируй [.env.example](.env.example) в `.env` и заполни только при необходимости:

- AI_PROVIDER=local
- ANTHROPIC_API_KEY (необязательно)
- TELEGRAM_TOKEN (необязательно)
- TELEGRAM_CHAT_ID (необязательно)
- MT5_LOGIN / MT5_PASSWORD / MT5_SERVER (необязательно)
- FRED_API_KEY (необязательно)

Большая часть запуска работает без ключей и без платных подписок.
