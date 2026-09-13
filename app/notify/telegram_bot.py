"""Telegram notification wrapper."""

import os

import requests


class TelegramBot:
    def __init__(self, token=None, chat_id=None):
        self.token = token or os.getenv("TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    @staticmethod
    def format_signal_message(payload):
        direction = str(payload.get("direction", "WAIT")).upper()
        confidence = payload.get("confidence", 0.0)
        regime = payload.get("regime", "unknown")
        source = payload.get("data_source", "unknown")
        reasoning = payload.get("reasoning", "No reasoning")
        russian = payload.get("russian_explanation") or payload.get("reasoning_russian")
        base = (
            f"<b>GOLD AI SIGNAL</b>\n"
            f"Direction: <b>{direction}</b>\n"
            f"Confidence: {confidence}\n"
            f"Regime: {regime}\n"
            f"Source: {source}\n"
            f"Reason: {reasoning}"
        )
        if russian:
            return base + f"\n\n<b>Объяснение:</b> {russian}"
        return base

    @staticmethod
    def format_backtest_message(summary):
        return (
            "<b>GOLD BACKTEST REPORT</b>\n"
            f"Trades: <b>{summary.get('trades', 0)}</b>\n"
            f"Net return: {summary.get('total_return', 0.0)}%\n"
            f"Win rate: {summary.get('win_rate', 0.0)}%\n"
            f"Profit: {summary.get('profit', 0.0)}\n"
            f"Final balance: {summary.get('final_balance', 0.0)}\n"
            f"Summary: {summary.get('summary', 'Backtest completed.') }"
        )

    def send_message(self, text):
        if not self.token:
            return {"status": "skipped", "reason": "Telegram token is missing"}
        if not self.chat_id:
            return {
                "status": "waiting_for_chat_id",
                "reason": "Start the bot and send /start to receive a chat_id, then set TELEGRAM_CHAT_ID in .env",
                "bot_url": "https://t.me/tradingaiaas_bot",
            }

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        try:
            response = requests.post(url, data=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return {"status": "sent", "chat_id": self.chat_id, "message_id": data.get("result", {}).get("message_id")}
            return {"status": "failed", "error": data}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}
