# src/app/api/v1/endpoints/messages.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

import openai

from src.app.db.models import Message
from src.app.db.session import SessionLocal
from src.app.services.faiss_index import query_index
from src.app.core.config import settings

class MessageRequest(BaseModel):
    thread_id: str
    message: str

class MessageReply(BaseModel):
    status: str
    reply: str

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=MessageReply)
async def post_message(req: MessageRequest, session: AsyncSession = Depends(get_session)):
    # Сохраняем входящее
    user_msg = Message(
        thread_id=req.thread_id, role="user", content=req.message, timestamp=datetime.utcnow()
    )
    session.add(user_msg)
    await session.commit()

    # Достаём релевантный контекст
    try:
        docs = query_index(req.message, k=5)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Формируем сообщения для OpenAI
    system_prompt = "You are an AI assistant. Use the provided context to answer concisely."
    chat_messages = [{"role": "system", "content": system_prompt}]
    for doc in docs:
        chat_messages.append({"role": "system", "content": doc})
    chat_messages.append({"role": "user", "content": req.message})

    # Вызываем OpenAI
    openai.api_key = settings.openai_api_key
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chat_messages,
        temperature=0.2
    )
    reply_text = resp.choices[0].message.content.strip()

    # Сохраняем ответ
    assistant_msg = Message(
        thread_id=req.thread_id, role="assistant", content=reply_text, timestamp=datetime.utcnow()
    )
    session.add(assistant_msg)
    await session.commit()

    return {"status": "success", "reply": reply_text}