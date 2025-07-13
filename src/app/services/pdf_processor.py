# src/app/services/pdf_processor.py
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any
import logging

from src.app.core.logger import logger

class PDFProcessor:
    """Сервис для обработки PDF файлов, основанный на существующем конвертере"""
    
    def __init__(self):
        self.logger = logger
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Извлекает текст из PDF файла с метаданными
        Адаптированный метод из scripts/main.py
        """
        try:
            doc = fitz.open(pdf_path)
            text_content = []
            metadata = {
                "total_pages": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "page_texts": []
            }
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text")
                
                # Сохраняем информацию о каждой странице
                metadata["page_texts"].append({
                    "page": page_num + 1,
                    "char_count": len(text),
                    "has_content": bool(text.strip())
                })
                
                # Добавляем разделитель страниц для лучшей структуры
                if page_num > 0:
                    text_content.append(f"\n\n--- СТРАНИЦА {page_num + 1} ---\n\n")
                else:
                    # Для первой страницы добавляем заголовок документа
                    document_title = metadata["title"] or Path(pdf_path).stem
                    text_content.append(f"# {document_title}\n\n--- СТРАНИЦА {page_num + 1} ---\n\n")
                
                # Очищаем и форматируем текст
                cleaned_text = self.clean_text(text)
                text_content.append(cleaned_text)
            
            doc.close()
            
            full_text = "".join(text_content)
            
            return {
                "text": full_text,
                "metadata": metadata,
                "success": True,
                "error": None,
                "char_count": len(full_text),
                "pages_with_content": sum(1 for p in metadata["page_texts"] if p["has_content"])
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из {pdf_path}: {e}")
            return {
                "text": "",
                "metadata": {},
                "success": False,
                "error": str(e),
                "char_count": 0,
                "pages_with_content": 0
            }
    
    def clean_text(self, text: str) -> str:
        """
        Очищает и форматирует извлеченный текст
        Адаптированный метод из scripts/main.py
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Убираем лишние пробелы
            line = line.strip()
            if line:
                cleaned_lines.append(line)
            # Сохраняем пустые строки для разделения абзацев, но не более одной подряд
            elif cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
        
        # Убираем пустые строки в конце
        while cleaned_lines and cleaned_lines[-1] == "":
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def validate_pdf(self, file_path: str) -> Dict[str, Any]:
        """Проверяет валидность PDF файла"""
        try:
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            
            if page_count == 0:
                return {
                    "valid": False,
                    "error": "PDF файл не содержит страниц"
                }
            
            return {
                "valid": True,
                "pages": page_count
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Невалидный PDF файл: {e}"
            }
    
    def get_pdf_info(self, file_path: str) -> Dict[str, Any]:
        """Получает информацию о PDF файле без извлечения текста"""
        try:
            doc = fitz.open(file_path)
            
            info = {
                "success": True,
                "filename": Path(file_path).name,
                "pages": len(doc),
                "metadata": {
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "creator": doc.metadata.get("creator", ""),
                    "producer": doc.metadata.get("producer", ""),
                    "creation_date": doc.metadata.get("creationDate", ""),
                    "modification_date": doc.metadata.get("modDate", "")
                },
                "encrypted": doc.needs_pass,
                "page_sizes": []
            }
            
            # Получаем размеры страниц
            for page_num in range(min(5, len(doc))):  # Проверяем первые 5 страниц
                page = doc.load_page(page_num)
                rect = page.rect
                info["page_sizes"].append({
                    "page": page_num + 1,
                    "width": rect.width,
                    "height": rect.height
                })
            
            doc.close()
            return info
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "filename": Path(file_path).name
            }