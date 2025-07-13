# src/app/api/v1/endpoints/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
import os
from typing import Dict, Any, Optional, List
import aiofiles
import uuid
from datetime import datetime
from pydantic import BaseModel

from src.app.services.pdf_processor import PDFProcessor
from src.app.services.openai_vector_service import OpenAIVectorStoreService
from src.app.core.logger import logger

router = APIRouter()

class UploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    processing_stats: Optional[Dict[str, Any]] = None
    vector_store_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class PDFUploadService:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.vector_service = OpenAIVectorStoreService()
        self.upload_dir = Path("data/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_pdf_upload(self, file: UploadFile, process_async: bool = False) -> Dict[str, Any]:
        """Обрабатывает загруженный PDF файл"""
        
        # Проверяем тип файла
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Файл должен быть в формате PDF")
        
        # Генерируем уникальное имя файла
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = self.upload_dir / safe_filename
        
        try:
            # Сохраняем загруженный файл
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            logger.info(f"Файл сохранен: {file_path} ({len(content)} bytes)")
            
            # Проверяем валидность PDF
            validation = self.pdf_processor.validate_pdf(str(file_path))
            if not validation["valid"]:
                os.unlink(file_path)  # Удаляем невалидный файл
                raise HTTPException(status_code=422, detail=validation["error"])
            
            # Получаем информацию о PDF
            pdf_info = self.pdf_processor.get_pdf_info(str(file_path))
            
            # Конвертируем PDF в текст
            logger.info(f"Начинаем конвертацию PDF: {file.filename}")
            conversion_result = self.pdf_processor.extract_text_from_pdf(str(file_path))
            
            if not conversion_result["success"]:
                os.unlink(file_path)
                raise HTTPException(
                    status_code=422, 
                    detail=f"Ошибка конвертации PDF: {conversion_result['error']}"
                )
            
            if not conversion_result["text"].strip():
                os.unlink(file_path)
                raise HTTPException(
                    status_code=422, 
                    detail="PDF файл не содержит читаемого текста"
                )
            
            logger.info(f"Текст извлечен: {conversion_result['char_count']} символов, {conversion_result['pages_with_content']} страниц с контентом")
            
            # Подготавливаем метаданные
            metadata = {
                "original_filename": file.filename,
                "file_id": file_id,
                "upload_date": datetime.utcnow().isoformat(),
                "file_size_bytes": len(content),
                "pdf_info": pdf_info,
                "extraction_stats": {
                    "total_pages": conversion_result["metadata"]["total_pages"],
                    "pages_with_content": conversion_result["pages_with_content"],
                    "char_count": conversion_result["char_count"],
                    "title": conversion_result["metadata"]["title"],
                    "author": conversion_result["metadata"]["author"]
                }
            }
            
            # Загружаем в OpenAI Vector Store
            logger.info(f"Загружаем в Vector Store: {file.filename}")
            vector_result = await self.vector_service.upload_text_as_file(
                text_content=conversion_result["text"],
                filename=file.filename,
                metadata=metadata
            )
            
            # Удаляем временный файл (оставляем только в OpenAI)
            try:
                os.unlink(file_path)
                logger.info(f"Временный файл удален: {file_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
            
            return {
                "success": vector_result["success"],
                "file_id": file_id,
                "original_filename": file.filename,
                "processing_stats": {
                    "total_pages": conversion_result["metadata"]["total_pages"],
                    "pages_with_content": conversion_result["pages_with_content"],
                    "char_count": conversion_result["char_count"],
                    "file_size_bytes": len(content),
                    "chunks_created": vector_result.get("total_chunks", 0)
                },
                "vector_store_result": vector_result,
                "pdf_info": pdf_info
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # Очищаем файл в случае ошибки
            try:
                if file_path.exists():
                    os.unlink(file_path)
            except:
                pass
            
            logger.error(f"Ошибка обработки файла {file.filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Внутренняя ошибка при обработке файла: {str(e)}"
            )

# Создаем экземпляр сервиса
upload_service = PDFUploadService()

@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF файл для загрузки"),
    background_tasks: BackgroundTasks = None
):
    """
    Загрузка PDF файла в OpenAI Vector Store
    
    - Принимает PDF файл
    - Конвертирует в текст
    - Загружает как единый файл в Vector Store для поиска
    """
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")
    
    logger.info(f"Получен запрос на загрузку: {file.filename}")
    
    try:
        result = await upload_service.process_pdf_upload(file)
        
        if result["success"]:
            return UploadResponse(
                success=True,
                message=f"Файл '{file.filename}' успешно обработан и загружен в Vector Store",
                file_id=result["file_id"],
                processing_stats=result["processing_stats"],
                vector_store_result=result["vector_store_result"]
            )
        else:
            return UploadResponse(
                success=False,
                message="Ошибка загрузки в Vector Store",
                error=result["vector_store_result"].get("error", "Unknown error")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Неожиданная ошибка: {str(e)}"
        )

@router.post("/pdf/batch", response_model=List[UploadResponse])
async def upload_pdf_batch(
    files: List[UploadFile] = File(..., description="PDF файлы для загрузки (до 10 файлов)"),
    background_tasks: BackgroundTasks = None
):
    """
    Массовая загрузка PDF файлов в OpenAI Vector Store
    
    - Принимает до 10 PDF файлов одновременно
    - Обрабатывает их параллельно
    - Возвращает результат для каждого файла
    """
    
    # Проверяем количество файлов
    if len(files) > 10:
        raise HTTPException(
            status_code=400, 
            detail=f"Максимум 10 файлов за раз. Получено: {len(files)}"
        )
    
    if not files:
        raise HTTPException(status_code=400, detail="Файлы не предоставлены")
    
    logger.info(f"Получен запрос на массовую загрузку: {len(files)} файлов")
    
    # Проверяем имена файлов
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Один из файлов не имеет имени")
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=f"Файл {file.filename} не является PDF"
            )
    
    results = []
    
    # Обрабатываем файлы параллельно
    import asyncio
    
    async def process_single_file(file: UploadFile) -> UploadResponse:
        """Обрабатывает один файл и возвращает результат"""
        try:
            logger.info(f"🔄 Начинаем обработку: {file.filename}")
            result = await upload_service.process_pdf_upload(file)
            
            if result["success"]:
                logger.info(f"✅ Завершена обработка: {file.filename}")
                return UploadResponse(
                    success=True,
                    message=f"Файл '{file.filename}' успешно обработан",
                    file_id=result["file_id"],
                    processing_stats=result["processing_stats"],
                    vector_store_result=result["vector_store_result"]
                )
            else:
                logger.error(f"❌ Ошибка обработки: {file.filename}")
                return UploadResponse(
                    success=False,
                    message=f"Ошибка загрузки файла '{file.filename}'",
                    error=result["vector_store_result"].get("error", "Unknown error")
                )
                
        except Exception as e:
            logger.error(f"❌ Исключение при обработке {file.filename}: {e}")
            return UploadResponse(
                success=False,
                message=f"Неожиданная ошибка при обработке '{file.filename}'",
                error=str(e)
            )
    
    try:
        # Запускаем обработку всех файлов параллельно
        tasks = [process_single_file(file) for file in files]
        results = await asyncio.gather(*tasks)
        
        # Логируем общую статистику
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        logger.info(f"📊 Массовая загрузка завершена: {successful} успешно, {failed} ошибок")
        
        return results
        
    except Exception as e:
        logger.error(f"Критическая ошибка массовой загрузки: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Критическая ошибка массовой загрузки: {str(e)}"
        )

@router.get("/pdf/info")
async def get_upload_info():
    """Получить информацию о Vector Store"""
    try:
        info = upload_service.vector_service.get_vector_store_info()
        return info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения информации: {str(e)}"
        )

@router.post("/pdf/search")
async def search_in_uploads(query: str = Form(..., description="Поисковый запрос")):
    """Поиск в загруженных документах через Vector Store"""
    try:
        result = upload_service.vector_service.search_in_vector_store(query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка поиска: {str(e)}"
        )

@router.delete("/pdf/file/{file_id}")
async def delete_uploaded_file(file_id: str):
    """Удалить файл из Vector Store"""
    try:
        success = upload_service.vector_service.delete_file_from_vector_store(file_id)
        if success:
            return {"success": True, "message": f"Файл {file_id} удален"}
        else:
            raise HTTPException(status_code=404, detail="Файл не найден или ошибка удаления")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка удаления: {str(e)}"
        )