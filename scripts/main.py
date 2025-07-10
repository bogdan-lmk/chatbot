import os
import fitz  # PyMuPDF
from pathlib import Path
import argparse
from typing import List, Optional, Dict
import logging
import json
import time
from datetime import datetime
import concurrent.futures
from threading import Lock

class PDFToTextConverter:
    """
    Оптимизированный конвертер PDF файлов в текст для обработки до 100 файлов
    """
    
    def __init__(self, output_format: str = "txt", max_workers: int = 4):
        """
        Args:
            output_format: "txt" или "md" для markdown
            max_workers: количество потоков для параллельной обработки
        """
        self.output_format = output_format
        self.max_workers = max_workers
        self.processed_files = {}  # Кэш обработанных файлов
        self.lock = Lock()
        self.setup_logging()
        
        # Создаем директории
        self.cache_dir = Path("./pdf_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        self.load_cache()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pdf_conversion.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_cache(self):
        """Загружает кэш обработанных файлов"""
        cache_file = self.cache_dir / "processed_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.processed_files = json.load(f)
                self.logger.info(f"Загружен кэш с {len(self.processed_files)} записями")
            except Exception as e:
                self.logger.warning(f"Не удалось загрузить кэш: {e}")
                self.processed_files = {}
    
    def save_cache(self):
        """Сохраняет кэш обработанных файлов"""
        cache_file = self.cache_dir / "processed_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_files, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить кэш: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Создает хэш файла для проверки изменений"""
        stat = os.stat(file_path)
        return f"{stat.st_size}_{stat.st_mtime}"
    
    def is_file_processed(self, file_path: str, output_path: str) -> bool:
        """Проверяет, был ли файл уже обработан"""
        file_hash = self.get_file_hash(file_path)
        file_key = str(Path(file_path).absolute())
        
        # Проверяем кэш
        if file_key in self.processed_files:
            cached_info = self.processed_files[file_key]
            if (cached_info.get("hash") == file_hash and 
                Path(output_path).exists()):
                return True
        
        return False
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict:
        """
        Извлекает текст из PDF файла с метаданными
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
                
                # Сохраняем текст каждой страницы отдельно
                metadata["page_texts"].append({
                    "page": page_num + 1,
                    "char_count": len(text),
                    "has_content": bool(text.strip())
                })
                
                if self.output_format == "md":
                    if page_num > 0:
                        text_content.append(f"\n\n---\n\n## Страница {page_num + 1}\n\n")
                    else:
                        text_content.append(f"# {Path(pdf_path).stem}\n\n## Страница {page_num + 1}\n\n")
                else:
                    if page_num > 0:
                        text_content.append(f"\n\n{'='*50}\nСтраница {page_num + 1}\n{'='*50}\n\n")
                
                # Очищаем и форматируем текст
                cleaned_text = self.clean_text(text)
                text_content.append(cleaned_text)
            
            doc.close()
            
            return {
                "text": "".join(text_content),
                "metadata": metadata,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            return {
                "text": "",
                "metadata": {},
                "success": False,
                "error": str(e)
            }
    
    def clean_text(self, text: str) -> str:
        """Очищает и форматирует извлеченный текст"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Убираем лишние пробелы
            line = line.strip()
            if line:
                cleaned_lines.append(line)
            # Сохраняем пустые строки для разделения абзацев
            elif cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
        
        return '\n'.join(cleaned_lines)
    
    def convert_single_file(self, input_path: str, output_dir: str) -> Dict:
        """
        Конвертирует один PDF файл с подробной информацией
        """
        try:
            input_file = Path(input_path)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Формируем имя выходного файла
            output_extension = ".md" if self.output_format == "md" else ".txt"
            output_file = output_dir / f"{input_file.stem}{output_extension}"
            
            # Проверяем кэш
            if self.is_file_processed(input_path, str(output_file)):
                self.logger.info(f"⏩ Пропуск (уже обработан): {input_file.name}")
                return {
                    "status": "skipped",
                    "input_file": str(input_file),
                    "output_file": str(output_file),
                    "reason": "already_processed"
                }
            
            self.logger.info(f"🔄 Обрабатываем: {input_file.name}")
            start_time = time.time()
            
            # Извлекаем текст
            result = self.extract_text_from_pdf(input_path)
            
            if not result["success"]:
                return {
                    "status": "error",
                    "input_file": str(input_file),
                    "output_file": str(output_file),
                    "error": result["error"]
                }
            
            if not result["text"].strip():
                self.logger.warning(f"⚠️  Пустой результат: {input_file.name}")
                return {
                    "status": "empty",
                    "input_file": str(input_file),
                    "output_file": str(output_file),
                    "metadata": result["metadata"]
                }
            
            # Сохраняем текст
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result["text"])
            
            # Сохраняем метаданные
            metadata_file = output_dir / f"{input_file.stem}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(result["metadata"], f, ensure_ascii=False, indent=2)
            
            processing_time = time.time() - start_time
            
            # Обновляем кэш
            with self.lock:
                file_key = str(Path(input_path).absolute())
                self.processed_files[file_key] = {
                    "hash": self.get_file_hash(input_path),
                    "processed_at": datetime.now().isoformat(),
                    "output_file": str(output_file),
                    "processing_time": processing_time,
                    "pages": result["metadata"]["total_pages"]
                }
            
            self.logger.info(f"✅ Готово: {input_file.name} ({processing_time:.2f}s)")
            
            return {
                "status": "success",
                "input_file": str(input_file),
                "output_file": str(output_file),
                "metadata": result["metadata"],
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка {input_path}: {str(e)}")
            return {
                "status": "error",
                "input_file": str(input_path),
                "error": str(e)
            }
    
    def convert_batch(self, input_dir: str, output_dir: str, 
                     file_pattern: str = "*.pdf", parallel: bool = True) -> Dict:
        """
        Массовая конвертация с параллельной обработкой
        """
        input_path = Path(input_dir)
        results = {
            "success": 0, 
            "failed": 0, 
            "skipped": 0,
            "empty": 0,
            "files": [],
            "total_time": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # Находим все PDF файлы
        pdf_files = list(input_path.glob(file_pattern))
        
        if not pdf_files:
            self.logger.warning(f"PDF файлы не найдены в {input_dir}")
            return results
        
        self.logger.info(f"🔍 Найдено {len(pdf_files)} PDF файлов")
        start_time = time.time()
        
        if parallel and len(pdf_files) > 1:
            # Параллельная обработка
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.convert_single_file, str(pdf_file), output_dir): pdf_file 
                    for pdf_file in pdf_files
                }
                
                for future in concurrent.futures.as_completed(future_to_file):
                    result = future.result()
                    self._update_results(results, result)
        else:
            # Последовательная обработка
            for pdf_file in pdf_files:
                result = self.convert_single_file(str(pdf_file), output_dir)
                self._update_results(results, result)
        
        results["total_time"] = time.time() - start_time
        results["end_time"] = datetime.now().isoformat()
        
        # Сохраняем кэш
        self.save_cache()
        
        return results
    
    def _update_results(self, results: Dict, result: Dict):
        """Обновляет статистику результатов"""
        results["files"].append(result)
        
        if result["status"] == "success":
            results["success"] += 1
        elif result["status"] == "error":
            results["failed"] += 1
        elif result["status"] == "skipped":
            results["skipped"] += 1
        elif result["status"] == "empty":
            results["empty"] += 1
    
    def generate_report(self, results: Dict, output_dir: str):
        """Генерирует подробный отчет о конвертации"""
        report_file = Path(output_dir) / "conversion_report.json"
        
        # Добавляем сводку
        results["summary"] = {
            "total_files": len(results["files"]),
            "success_rate": results["success"] / max(len(results["files"]), 1) * 100,
            "avg_time_per_file": results["total_time"] / max(len(results["files"]), 1)
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Генерируем читаемый отчет
        readable_report = Path(output_dir) / "conversion_report.txt"
        with open(readable_report, 'w', encoding='utf-8') as f:
            f.write("ОТЧЕТ О КОНВЕРТАЦИИ PDF\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Дата: {results['start_time']}\n")
            f.write(f"Общее время: {results['total_time']:.2f} секунд\n")
            f.write(f"Файлов обработано: {len(results['files'])}\n")
            f.write(f"Успешно: {results['success']}\n")
            f.write(f"Ошибки: {results['failed']}\n")
            f.write(f"Пропущено: {results['skipped']}\n")
            f.write(f"Пустые: {results['empty']}\n")
            f.write(f"Процент успеха: {results['summary']['success_rate']:.1f}%\n\n")
            
            if results["failed"] > 0:
                f.write("ФАЙЛЫ С ОШИБКАМИ:\n")
                f.write("-" * 30 + "\n")
                for file_result in results["files"]:
                    if file_result["status"] == "error":
                        f.write(f"❌ {Path(file_result['input_file']).name}: {file_result.get('error', 'Unknown error')}\n")
                f.write("\n")
        
        self.logger.info(f"📊 Отчет сохранен: {report_file}")


def main():
    parser = argparse.ArgumentParser(description='Оптимизированный конвертер PDF в текст')
    parser.add_argument('input', help='Путь к PDF файлу или папке с PDF файлами')
    parser.add_argument('-o', '--output', default='./output', 
                       help='Папка для сохранения результатов')
    parser.add_argument('-f', '--format', choices=['txt', 'md'], default='txt',
                       help='Формат вывода: txt или md')
    parser.add_argument('-w', '--workers', type=int, default=4,
                       help='Количество потоков для параллельной обработки')
    parser.add_argument('--no-parallel', action='store_true',
                       help='Отключить параллельную обработку')
    parser.add_argument('--info', action='store_true', 
                       help='Показать информацию о PDF файле(ах)')
    parser.add_argument('--clear-cache', action='store_true',
                       help='Очистить кэш обработанных файлов')
    
    args = parser.parse_args()
    
    converter = PDFToTextConverter(
        output_format=args.format,
        max_workers=args.workers
    )
    
    if args.clear_cache:
        cache_file = Path("./pdf_cache/processed_cache.json")
        if cache_file.exists():
            cache_file.unlink()
            print("🗑️  Кэш очищен")
        return
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Обработка одного файла
        result = converter.convert_single_file(str(input_path), args.output)
        if result["status"] == "success":
            print(f"✅ Конвертация завершена: {result['output_file']}")
        else:
            print(f"❌ Ошибка: {result.get('error', 'Unknown error')}")
    
    elif input_path.is_dir():
        # Массовая обработка
        print(f"🚀 Начинаем массовую обработку...")
        results = converter.convert_batch(
            str(input_path), 
            args.output,
            parallel=not args.no_parallel
        )
        
        # Выводим результаты
        print(f"\n📊 РЕЗУЛЬТАТЫ КОНВЕРТАЦИИ:")
        print(f"=" * 40)
        print(f"✅ Успешно: {results['success']}")
        print(f"❌ Ошибки: {results['failed']}")
        print(f"⏩ Пропущено: {results['skipped']}")
        print(f"⚠️  Пустые: {results['empty']}")
        print(f"⏱️  Время: {results['total_time']:.2f} сек")
        print(f"📁 Результаты: {args.output}")
        
        # Генерируем отчет
        converter.generate_report(results, args.output)
    
    else:
        print(f"❌ Путь {input_path} не найден")


if __name__ == "__main__":
    main()