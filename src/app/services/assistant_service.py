# src/app/services/assistant_service.py
import time
import asyncio
from typing import Optional, Dict, Any
from openai import OpenAI
from src.app.core.config import settings
from src.app.core.logger import logger

class CFAnatolikService:
    """Сервис для работы с ассистентом CF Anatolik через Assistants API"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.assistant_id = settings.assistant_id
        self.timeout = settings.assistant_timeout
        
    async def ask_assistant(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Отправляет вопрос ассистенту CF Anatolik и возвращает ответ
        
        Args:
            message: Сообщение пользователя
            thread_id: ID существующего потока (если None, создается новый)
            
        Returns:
            Dict с ответом ассистента и метаданными
        """
        try:
            # Создаем или используем существующий thread
            if thread_id:
                thread = self._get_or_create_thread(thread_id)
            else:
                thread = self.client.beta.threads.create()
                logger.info(f"Создан новый thread: {thread.id}")
            
            # Добавляем сообщение пользователя в thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            
            # Запускаем ассистента
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            logger.info(f"Запущен ассистент {self.assistant_id} для thread {thread.id}")
            
            # Ждем завершения выполнения
            completed_run = await self._wait_for_completion(thread.id, run.id)
            
            if completed_run.status == "completed":
                # Получаем последнее сообщение ассистента
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id,
                    limit=1
                )
                
                if messages.data:
                    assistant_message = messages.data[0]
                    content = assistant_message.content[0].text.value
                    
                    return {
                        "success": True,
                        "content": content,
                        "thread_id": thread.id,
                        "run_id": completed_run.id,
                        "usage": getattr(completed_run, 'usage', None),
                        "model": getattr(completed_run, 'model', 'gpt-4o'),
                        "annotations": self._extract_annotations(assistant_message)
                    }
                else:
                    raise Exception("Не удалось получить ответ от ассистента")
                    
            else:
                # Обработка различных статусов ошибок
                error_details = self._handle_run_error(completed_run)
                return {
                    "success": False,
                    "error": f"Ассистент завершил работу со статусом: {completed_run.status}",
                    "details": error_details,
                    "thread_id": thread.id
                }
                
        except Exception as e:
            logger.error(f"Ошибка при работе с ассистентом: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "thread_id": thread_id
            }
    
    async def _wait_for_completion(self, thread_id: str, run_id: str):
        """Асинхронно ждет завершения выполнения ассистента"""
        max_attempts = self.timeout
        
        for attempt in range(max_attempts):
            await asyncio.sleep(1)  # Ждем 1 секунду между проверками
            
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            logger.debug(f"Статус выполнения: {run.status} (попытка {attempt + 1})")
            
            if run.status in ["completed", "failed", "cancelled", "expired"]:
                return run
            elif run.status == "requires_action":
                # Если ассистент требует действий (например, вызов функций)
                logger.info("Ассистент требует дополнительных действий")
                # Здесь можно добавить обработку required_action
                continue
                
        # Если превышен таймаут
        raise TimeoutError(f"Ассистент не ответил в течение {self.timeout} секунд")
    
    def _get_or_create_thread(self, thread_id: str):
        """Получает существующий thread или создает новый"""
        try:
            # Пытаемся получить существующий thread
            thread = self.client.beta.threads.retrieve(thread_id)
            return thread
        except:
            # Если thread не найден, создаем новый
            logger.info(f"Thread {thread_id} не найден, создаем новый")
            return self.client.beta.threads.create()
    
    def _handle_run_error(self, run) -> Dict[str, Any]:
        """Обрабатывает ошибки выполнения ассистента"""
        error_details = {
            "status": run.status,
            "last_error": getattr(run, 'last_error', None)
        }
        
        if run.status == "failed":
            if hasattr(run, 'last_error') and run.last_error:
                error_details["error_code"] = run.last_error.code
                error_details["error_message"] = run.last_error.message
        
        return error_details
    
    def _extract_annotations(self, message) -> list:
        """Извлекает аннотации из сообщения (ссылки на файлы, цитаты и т.д.)"""
        annotations = []
        
        try:
            if hasattr(message.content[0], 'text') and hasattr(message.content[0].text, 'annotations'):
                for annotation in message.content[0].text.annotations:
                    ann_data = {
                        "type": annotation.type,
                        "text": annotation.text
                    }
                    
                    if hasattr(annotation, 'file_citation'):
                        ann_data["file_citation"] = {
                            "file_id": annotation.file_citation.file_id,
                            "quote": getattr(annotation.file_citation, 'quote', '')
                        }
                    elif hasattr(annotation, 'file_path'):
                        ann_data["file_path"] = {
                            "file_id": annotation.file_path.file_id
                        }
                    
                    annotations.append(ann_data)
        except Exception as e:
            logger.warning(f"Не удалось извлечь аннотации: {e}")
        
        return annotations
    
    def get_thread_messages(self, thread_id: str, limit: int = 20) -> list:
        """Получает историю сообщений из thread"""
        try:
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                limit=limit,
                order="asc"  # Сортируем по возрастанию для правильного порядка
            )
            
            formatted_messages = []
            for msg in messages.data:
                formatted_messages.append({
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content[0].text.value if msg.content else "",
                    "created_at": msg.created_at,
                    "annotations": self._extract_annotations(msg)
                })
            
            return formatted_messages
        except Exception as e:
            logger.error(f"Ошибка получения истории thread {thread_id}: {e}")
            return []

# Создаем экземпляр сервиса
cf_anatolik_service = CFAnatolikService()