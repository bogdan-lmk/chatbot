# src/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str = "sqlite+aiosqlite:///./data/db.sqlite3"
    assistant_id: str = ""
    use_assistant_api: bool = False
    assistant_timeout: int = 60
    max_assistant_tokens: int = 1000
    vector_store_id: str = ""  # ← ДОБАВИТЬ ЭТУ СТРОКУ

    class Config:
        env_file = ".env"

settings = Settings()