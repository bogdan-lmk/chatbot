# src/app/api/v1/endpoints/history.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime
from pydantic import BaseModel

from src.app.db.models import Message
from src.app.db.session import SessionLocal

router = APIRouter()

class HistoryResponse(BaseModel):
    thread_id: str
    role: str
    content: str
    timestamp: datetime

async def get_session():
    async with SessionLocal() as session:
        yield session

@router.get("/", response_model=List[HistoryResponse])
async def get_history(thread_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Message).where(Message.thread_id == thread_id).order_by(Message.id)
    )
    messages = result.scalars().all()
    return messages