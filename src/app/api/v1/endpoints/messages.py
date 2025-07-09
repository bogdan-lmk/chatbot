# src/app/api/v1/endpoints/messages.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from openai import OpenAI

from src.app.db.models import Message
from src.app.db.session import SessionLocal
from src.app.services.faiss_index import query_index
from src.app.core.config import settings

class MessageRequest(BaseModel):
    thread_id: str
    message: str
    debug: bool = False  # Флаг для отладочной информации

class SourceInfo(BaseModel):
    content_preview: str
    score: float
    metadata: Dict[str, Any]

class MessageReply(BaseModel):
    status: str
    reply: str
    sources_used: int = 0
    debug_info: Optional[Dict[str, Any]] = None

router = APIRouter()

async def get_session():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=MessageReply)
async def post_message(req: MessageRequest, session: AsyncSession = Depends(get_session)):
    """Обработка сообщения пользователя с контекстом из документов"""
    
    # Сохраняем входящее сообщение
    user_msg = Message(
        thread_id=req.thread_id, 
        role="user", 
        content=req.message, 
        timestamp=datetime.utcnow()
    )
    session.add(user_msg)
    await session.commit()

    try:
        # Ищем релевантные документы
        relevant_docs = query_index(req.message, k=5)
        
        # Фильтруем только самые релевантные (score < 1.0 обычно означает хорошее совпадение)
        good_docs = [doc for doc in relevant_docs if doc['score'] < 1.2]
        
        # Формируем контекст для GPT
        context_parts = []
        for i, doc in enumerate(good_docs[:3], 1):  # Берем топ-3 релевантных
            context_parts.append(
                f"[Источник {i}] (релевантность: {doc['score']:.3f})\n"
                f"{doc['content'][:800]}..."  # Увеличиваем размер контекста
            )
        
        context = "\n\n".join(context_parts) if context_parts else "Релевантный контекст не найден в документах."
        
        # Улучшенный системный промпт
        system_prompt = """Ты AI-ассистент, который отвечает на вопросы ТОЛЬКО на основе предоставленных документов.

        ВАЖНЫЕ ПРАВИЛА:
        1. Используй ТОЛЬКО информацию из предоставленного контекста
        2. Если в контексте нет ответа на вопрос, честно скажи: "В предоставленных документах нет информации по этому вопросу"
        3. Всегда указывай, из какого источника взята информация (например: "Согласно источнику 1...")
        4. Если информация неполная, укажи это
        5. НЕ ВЫДУМЫВАЙ информацию, которой нет в контексте
        6. Отвечай на русском языке"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"Контекст из ваших документов:\n\n{context}"},
            {"role": "user", "content": req.message}
        ]

        # Вызываем OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,  # Низкая температура для более точных ответов
            max_tokens=800
        )
        
        reply_text = response.choices[0].message.content.strip()
        
        # Сохраняем ответ
        assistant_msg = Message(
            thread_id=req.thread_id, 
            role="assistant", 
            content=reply_text, 
            timestamp=datetime.utcnow()
        )
        session.add(assistant_msg)
        await session.commit()

        # Подготавливаем отладочную информацию
        debug_info = None
        if req.debug:
            debug_info = {
                "query": req.message,
                "total_found": len(relevant_docs),
                "used_sources": len(good_docs),
                "context_length": len(context),
                "sources": [
                    {
                        "rank": i + 1,
                        "score": doc["score"],
                        "preview": doc["content"][:150] + "...",
                        "metadata": doc["metadata"]
                    }
                    for i, doc in enumerate(good_docs[:3])
                ],
                "full_context": context,
                "model_used": "gpt-3.5-turbo",
                "tokens_used": response.usage.total_tokens
            }

        return MessageReply(
            status="success", 
            reply=reply_text,
            sources_used=len(good_docs),
            debug_info=debug_info
        )
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, 
            detail="Индекс документов не найден. Запустите scripts/ingest.py"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка обработки запроса: {str(e)}"
        )