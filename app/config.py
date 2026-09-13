import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    ai_provider: str = os.getenv("AI_PROVIDER", "local")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    telegram_token: str | None = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    mt5_login: str | None = os.getenv("MT5_LOGIN")
    mt5_password: str | None = os.getenv("MT5_PASSWORD")
    mt5_server: str | None = os.getenv("MT5_SERVER")
    fred_api_key: str | None = os.getenv("FRED_API_KEY")
    db_path: str = os.getenv("DB_PATH", "data/signals.db")
    data_dir: str = os.getenv("DATA_DIR", "data")

    @property
    def db_path_obj(self) -> Path:
        return Path(self.db_path)


settings = Settings()
