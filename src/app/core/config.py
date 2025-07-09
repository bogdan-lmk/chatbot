from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str = "sqlite+aiosqlite:///./data/db.sqlite3"

    class Config:
        env_file = ".env"

settings = Settings()