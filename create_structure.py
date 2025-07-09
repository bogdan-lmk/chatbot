#!/usr/bin/env python3
# create_structure.py

import os
from pathlib import Path

# списки директорий и файлов
dirs = [
    "docs",
    "scripts",
    "data/docs",
    "src/app/core",
    "src/app/db",
    "src/app/api/v1/endpoints",
    "src/app/services",
    "src/app/schemas",
    "src/app/templates",
    "tests",
]

files = {
    ".env.example": "",
    ".gitignore": (
        "__pycache__/\n"
        "*.py[cod]\n"
        ".venv/\n"
        "data/\n"
        "*.sqlite3\n"
        ".env\n"
        "venv/\n"
    ),
    "README.md": "# Название проекта\n\nКраткое описание.\n",
    "requirements.txt": "\n".join([
        "fastapi",
        "uvicorn[standard]",
        "python-dotenv",
        "sqlalchemy",
        "PyPDF2",
        "langchain",
        "faiss-cpu",
        "openai",
    ]) + "\n",
    "Dockerfile": "",               # заполните по своему шаблону
    "docker-compose.yml": "",       # заполните по своему шаблону
    "Makefile": "run:\n\tuvicorn src.app.main:app --reload\n",
    ".flake8": (
        "[flake8]\n"
        "max-line-length = 88\n"
        "extend-ignore = E203, W503\n"
    ),
    "pre-commit-config.yaml": "",   # при необходимости
    "docs/architecture.md": "# Архитектура проекта\n",
    "scripts/ingest.py": "#!/usr/bin/env python3\n# Скрипт для загрузки документов в FAISS\n",
    "src/app/__init__.py": "",
    "src/app/main.py": (
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        "@app.get('/')\n"
        "async def root():\n"
        "    return {'status': 'ok'}\n"
    ),
    "src/app/core/config.py": (
        "from pydantic import BaseSettings\n\n"
        "class Settings(BaseSettings):\n"
        "    openai_api_key: str\n"
        "    database_url: str = 'sqlite+aiosqlite:///./data/db.sqlite3'\n\n"
        "    class Config:\n"
        "        env_file = '.env'\n\n"
        "settings = Settings()\n"
    ),
    "src/app/core/logger.py": (
        "import logging\n\n"
        "logging.basicConfig(level=logging.INFO)\n"
        "logger = logging.getLogger(__name__)\n"
    ),
    "src/app/db/base.py": (
        "from sqlalchemy.orm import declarative_base\n\n"
        "Base = declarative_base()\n"
    ),
    "src/app/db/session.py": (
        "from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession\n"
        "from sqlalchemy.orm import sessionmaker\n"
        "from src.app.core.config import settings\n\n"
        "engine = create_async_engine(settings.database_url, echo=True)\n"
        "SessionLocal = sessionmaker(\n"
        "    autocommit=False, autoflush=False,\n"
        "    bind=engine, class_=AsyncSession\n"
        ")\n"
    ),
    "src/app/db/models.py": (
        "from sqlalchemy import Column, Integer, String, DateTime\n"
        "from datetime import datetime\n"
        "from src.app.db.base import Base\n\n"
        "class Message(Base):\n"
        "    __tablename__ = 'messages'\n"
        "    id = Column(Integer, primary_key=True, index=True)\n"
        "    thread_id = Column(String, index=True)\n"
        "    role = Column(String)\n"
        "    content = Column(String)\n"
        "    timestamp = Column(DateTime, default=datetime.utcnow)\n"
    ),
    "src/app/api/v1/api.py": (
        "from fastapi import APIRouter\n"
        "from src.app.api.v1.endpoints import history, messages\n\n"
        "api_router = APIRouter()\n"
        "api_router.include_router(history.router, prefix='/history', tags=['history'])\n"
        "api_router.include_router(messages.router, prefix='/message', tags=['message'])\n"
    ),
    "src/app/api/v1/endpoints/history.py": (
        "from fastapi import APIRouter, Depends\n\n"
        "router = APIRouter()\n\n"
        "@router.get('/')\n"
        "async def get_history(thread_id: str):\n"
        "    return []  # TODO: достать из БД\n"
    ),
    "src/app/api/v1/endpoints/messages.py": (
        "from fastapi import APIRouter\n\n"
        "router = APIRouter()\n\n"
        "@router.post('/')\n"
        "async def post_message(thread_id: str, message: str):\n"
        "    return {'status': 'success', 'reply': '...'}\n"
    ),
    "src/app/services/embeddings.py": "# тут логика OpenAIEmbeddings\n",
    "src/app/services/faiss_index.py": "# тут логика FAISS Index\n",
    "src/app/schemas/message.py": "from pydantic import BaseModel\n\nclass Message(BaseModel):\n    thread_id: str\n    message: str\n",
    "src/app/templates/index.html": (
        "<!DOCTYPE html>\n<html><head><title>Chat</title></head><body>\n"
        "<h1>Тестовый UI</h1>\n<form action='/api/v1/message' method='post'>\n"
        "<input name='thread_id' value='main'><br>\n"
        "<textarea name='message'></textarea><br>\n"
        "<button type='submit'>Send</button>\n</form>\n</body></html>\n"
    ),
    "tests/__init__.py": "",
    "tests/test_api.py": (
        "import pytest\nfrom fastapi.testclient import TestClient\nfrom src.app.main import app\n\nclient = TestClient(app)\n\ndef test_root():\n    r = client.get('/')\n    assert r.status_code == 200\n    assert r.json() == {'status': 'ok'}\n"
    ),
}

def main():
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✔ dir: {d}")
    for filepath, content in files.items():
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(content, encoding='utf-8')
            # если скрипт, делаем исполняемым
            if filepath.startswith("scripts/") and filepath.endswith(".py"):
                p.chmod(p.stat().st_mode | 0o111)
            print(f"✔ file: {filepath}")
        else:
            print(f"⚠ exists: {filepath}")
    print("\n✅ Готово — ваш проект теперь имеет современную, расширяемую структуру!")

if __name__ == "__main__":
    main()