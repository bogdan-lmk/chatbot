# src/app/api/v1/api.py
from fastapi import APIRouter
from src.app.api.v1.endpoints import history, messages, upload

api_router = APIRouter()
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(messages.router, prefix="/message", tags=["message"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])