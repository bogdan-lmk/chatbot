# src/app/services/openai_vector_service.py - версия с загрузкой целых файлов
from openai import OpenAI
from typing import Dict, Any, List, Optional
import tempfile
import os
from pathlib import Path
import json
from datetime import datetime

from src.app.core.config import settings
from src.app.core.logger import logger

class OpenAIVectorStoreService:
    """Сервис для работы с OpenAI Vector Stores и file search"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.vector_store_id = settings.vector_store_id
        
        # Проверяем наличие vector_store_id
        if not self.vector_store_id:
            raise ValueError(
                "VECTOR_STORE_ID не задан в переменных окружения. "
                "Добавьте VECTOR_STORE_ID=vs_... в файл .env"
            )
        
    def _create_safe_filename(self, original_filename: str) -> str:
        """Создает безопасное и читаемое имя файла"""
        # Получаем имя без расширения
        base_name = Path(original_filename).stem
        
        # Убираем лишние пробелы и заменяем на подчеркивания
        clean_name = base_name.strip()
        
        # Заменяем проблемные символы
        replacements = {
            ' ': '_',
            '-': '_',
            '(': '',
            ')': '',
            '[': '',
            ']': '',
            '{': '',
            '}': '',
            '.': '_',
            ',': '',
            ';': '',
            ':': '',
            '!': '',
            '?': '',
            '"': '',
            "'": '',
            '/': '_',
            '\\': '_',
            '|': '_',
            '*': '',
            '<': '',
            '>': ''
        }
        
        for old, new in replacements.items():
            clean_name = clean_name.replace(old, new)
        
        # Убираем множественные подчеркивания
        while '__' in clean_name:
            clean_name = clean_name.replace('__', '_')
        
        # Убираем подчеркивания в начале и конце
        clean_name = clean_name.strip('_')
        
        # Ограничиваем длину (OpenAI имеет лимиты на имена файлов)
        if len(clean_name) > 100:
            clean_name = clean_name[:100]
        
        # Если имя стало пустым, используем fallback
        if not clean_name:
            clean_name = f"document_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return f"{clean_name}.txt"
    
    def get_vector_store_info(self) -> Dict[str, Any]:
        """Получает информацию о vector store"""
        try:
            store_info = self.client.vector_stores.retrieve(self.vector_store_id)
            
            # Получаем список файлов
            files = self.client.vector_stores.files.list(
                vector_store_id=self.vector_store_id
            )
            
            logger.info(f"✅ Получена информация о Vector Store: {store_info.name}")
            
            return {
                "success": True,
                "vector_store_id": self.vector_store_id,
                "name": getattr(store_info, 'name', 'Unknown'),
                "file_counts": getattr(store_info, 'file_counts', {"total": 0, "completed": 0}),
                "status": getattr(store_info, 'status', 'unknown'),
                "created_at": getattr(store_info, 'created_at', 0),
                "usage_bytes": getattr(store_info, 'usage_bytes', 0),
                "files": [
                    {
                        "id": f.id,
                        "status": getattr(f, 'status', 'unknown'),
                        "created_at": getattr(f, 'created_at', 0)
                    }
                    for f in files.data
                ] if hasattr(files, 'data') else []
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о vector store: {e}")
            return {
                "success": False,
                "error": str(e),
                "vector_store_id": self.vector_store_id
            }
    
    async def upload_text_as_file(self, text_content: str, filename: str, metadata: Dict = None) -> Dict[str, Any]:
        """Загружает весь текст как один файл в OpenAI Vector Store"""
        
        try:
            logger.info(f"📄 Загружаем файл целиком: {filename} ({len(text_content)} символов)")
            
            # Создаем читаемое и безопасное имя файла
            safe_filename = self._create_safe_filename(filename)
            logger.info(f"📝 Безопасное имя файла: {safe_filename}")
            
            # Создаем временный файл с полным текстом
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.txt', 
                delete=False, 
                encoding='utf-8'
            ) as tmp_file:
                # Добавляем метаданные в начало файла
                file_header = f"""# {safe_filename}
# Источник PDF: {filename}
# Дата загрузки: {datetime.utcnow().isoformat()}
# Размер: {len(text_content)} символов
# Vector Store: {self.vector_store_id}

"""
                if metadata:
                    file_header += f"# Метаданные: {json.dumps(metadata, ensure_ascii=False)}\n\n"
                
                file_header += "="*50 + "\n"
                file_header += f"СОДЕРЖИМОЕ ДОКУМЕНТА: {filename}\n"
                file_header += "="*50 + "\n\n"
                
                # Добавляем весь текст
                tmp_file.write(file_header + text_content)
                tmp_file_path = tmp_file.name
            
            try:
                logger.info(f"🔄 Загружаем файл в OpenAI Files API с именем: {safe_filename}")
                
                # Загружаем файл в OpenAI с правильным именем
                with open(tmp_file_path, 'rb') as f:
                    file_obj = self.client.files.create(
                        file=(safe_filename, f),  # Передаем кортеж (имя, файл)
                        purpose='assistants'
                    )
                
                logger.info(f"✅ Файл создан в OpenAI: {file_obj.id}")
                logger.info(f"📄 Имя файла в OpenAI: {file_obj.filename}")
                
                # Добавляем файл в vector store
                logger.info(f"🔄 Добавляем файл в Vector Store...")
                
                vector_file = self.client.vector_stores.files.create(
                    vector_store_id=self.vector_store_id,
                    file_id=file_obj.id
                )
                
                logger.info(f"✅ Файл добавлен в Vector Store: {vector_file.id}, статус: {vector_file.status}")
                
                return {
                    "success": True,
                    "original_filename": filename,
                    "openai_filename": file_obj.filename,
                    "safe_filename": safe_filename,
                    "vector_store_id": self.vector_store_id,
                    "total_chunks": 1,  # Один файл
                    "uploaded_files": [{
                        "file_id": file_obj.id,
                        "vector_store_file_id": vector_file.id,
                        "original_name": filename,
                        "openai_name": file_obj.filename,
                        "safe_name": safe_filename,
                        "file_status": file_obj.status,
                        "vector_status": vector_file.status,
                        "file_size_chars": len(text_content)
                    }],
                    "total_chars": len(text_content),
                    "metadata": metadata,
                    "upload_method": "whole_file"
                }
                
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(tmp_file_path)
                    logger.info(f"🗑️ Временный файл удален: {tmp_file_path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл: {e}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки в vector store: {e}")
            return {
                "success": False,
                "error": str(e),
                "filename": filename
            }
    
    def search_in_vector_store(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Поиск в vector store через assistant"""
        try:
            logger.info(f"🔍 Выполняем поиск: '{query}'")
            
            # Создаем временный assistant для поиска
            assistant = self.client.beta.assistants.create(
                name="Search Assistant",
                instructions="Найди релевантную информацию в загруженных файлах. Отвечай на русском языке, основываясь только на информации из файлов.",
                model="gpt-4o",
                tools=[{"type": "file_search"}],
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [self.vector_store_id]
                    }
                }
            )
            
            # Создаем thread и отправляем запрос
            thread = self.client.beta.threads.create()
            
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=query
            )
            
            # Запускаем assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            logger.info(f"🔄 Ожидаем ответ от assistant...")
            
            # Ждем завершения
            import time
            max_attempts = 60  # Увеличили время ожидания
            for attempt in range(max_attempts):
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                if run_status.status == "completed":
                    logger.info(f"✅ Поиск завершен успешно")
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Поиск завершился со статусом: {run_status.status}")
                elif attempt % 10 == 0:  # Логируем прогресс каждые 10 секунд
                    logger.info(f"⏳ Статус поиска: {run_status.status} (попытка {attempt + 1}/{max_attempts})")
                
                time.sleep(1)
            
            # Получаем результаты
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id,
                limit=1
            )
            
            if messages.data:
                response = messages.data[0].content[0].text.value
                annotations = getattr(messages.data[0].content[0].text, 'annotations', [])
                
                # Очищаем ресурсы
                try:
                    self.client.beta.assistants.delete(assistant.id)
                    logger.info(f"🗑️ Временный assistant удален")
                except:
                    pass
                
                logger.info(f"✅ Найдено {len(annotations)} источников")
                
                return {
                    "success": True,
                    "response": response,
                    "annotations": annotations,
                    "sources_count": len(annotations)
                }
            else:
                logger.warning("⚠️ Нет ответа от assistant")
                return {
                    "success": False,
                    "error": "Нет ответа от assistant"
                }
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в vector store: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_file_from_vector_store(self, file_id: str) -> bool:
        """Удаляет файл из vector store"""
        try:
            logger.info(f"🗑️ Удаляем файл: {file_id}")
            
            # Удаляем файл из vector store
            self.client.vector_stores.files.delete(
                vector_store_id=self.vector_store_id,
                file_id=file_id
            )
            
            # Также удаляем сам файл
            self.client.files.delete(file_id)
            
            logger.info(f"✅ Файл {file_id} удален из vector store")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления файла {file_id}: {e}")
            return False