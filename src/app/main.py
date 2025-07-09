# src/app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncio

from src.app.core.config import settings
from src.app.core.logger import logger
from src.app.db.base import Base
from src.app.db.session import engine
from src.app.api.v1.api import api_router

app = FastAPI(title="AI Agent")

# Статика и шаблоны
app.mount("/static", StaticFiles(directory="src/app/templates"), name="static")
templates = Jinja2Templates(directory="src/app/templates")

@app.on_event("startup")
async def on_startup():
    # Инициализируем БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

app.include_router(api_router, prefix="/api/v1")

@app.get("/", response_class=HTMLResponse)
async def get_ui(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})