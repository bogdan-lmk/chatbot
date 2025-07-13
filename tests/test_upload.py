# test_upload.py - простой тест загрузки
import asyncio
from src.app.services.openai_vector_service import OpenAIVectorStoreService
from src.app.services.pdf_processor import PDFProcessor

async def test_upload():
    print("=== ТЕСТ ЗАГРУЗКИ В VECTOR STORE ===")
    
    # Создаем тестовый текст
    test_text = """
    Это тестовый документ для проверки загрузки в Vector Store.
    
    Он содержит несколько абзацев текста для демонстрации работы
    системы разбивки на чанки и загрузки в OpenAI.
    
    Каждый чанк будет загружен как отдельный файл в Vector Store,
    что позволит эффективно выполнять поиск по содержимому.
    """
    
    # Инициализируем сервис
    vector_service = OpenAIVectorStoreService()
    
    print(f"Vector Store ID: {vector_service.vector_store_id}")
    
    # Тестируем загрузку
    result = await vector_service.upload_text_as_file(
        text_content=test_text,
        filename="test_document.txt",
        metadata={"test": True, "source": "manual_test"}
    )
    
    print(f"Результат загрузки: {result}")
    
    if result["success"]:
        print(f"✅ Успешно загружено {result['total_chunks']} чанков")
        
        # Проверяем информацию о Vector Store
        info = vector_service.get_vector_store_info()
        print(f"Информация о Vector Store: {info}")
        
    else:
        print(f"❌ Ошибка загрузки: {result['error']}")

if __name__ == "__main__":
    asyncio.run(test_upload())