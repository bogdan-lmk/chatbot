#!/usr/bin/env python3
# scripts/ingest.py

import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

def load_documents(folder_path: Path):
    """Загружает документы из папки"""
    docs = []
    supported_extensions = {'.pdf', '.txt', '.md'}
    
    print(f"🔍 Сканируем папку: {folder_path}")
    
    for file in folder_path.glob("*"):
        if file.suffix.lower() in supported_extensions:
            print(f"📄 Обрабатываем: {file.name}")
            try:
                if file.suffix.lower() == ".pdf":
                    loader = PyPDFLoader(str(file))
                else:
                    loader = TextLoader(str(file), encoding="utf-8")
                file_docs = loader.load()
                docs.extend(file_docs)
                print(f"  ✅ Загружено {len(file_docs)} частей")
            except Exception as e:
                print(f"  ❌ Ошибка загрузки {file.name}: {e}")
                continue
        else:
            print(f"  ⏩ Пропускаем {file.name} (неподдерживаемый формат)")
    
    return docs

def main():
    print("🚀 СОЗДАНИЕ FAISS ИНДЕКСА ДЛЯ ДОКУМЕНТОВ")
    print("="*50)
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Проверяем API ключ
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY не найден в переменных окружения")
        print("💡 Убедитесь, что файл .env содержит:")
        print("   OPENAI_API_KEY=ваш_ключ_здесь")
        return
    
    print(f"✅ API ключ найден: {api_key[:15]}...")
    
    # Проверяем папку с документами
    docs_folder = Path("data/docs")
    if not docs_folder.exists():
        print(f"❌ Папка {docs_folder} не существует")
        print(f"💡 Создайте папку и поместите туда ваши PDF/TXT файлы:")
        print(f"   mkdir -p {docs_folder}")
        return
    
    # Загружаем документы
    docs = load_documents(docs_folder)
    
    if not docs:
        print("❌ Документы не найдены")
        print(f"💡 Поместите PDF или TXT файлы в папку {docs_folder}")
        return
    
    print(f"\n📚 Найдено документов: {len(docs)}")
    
    # Разбиваем на части
    print("✂️ Разбиваем документы на части...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        length_function=len,
    )
    texts = splitter.split_documents(docs)
    print(f"📝 Создано частей: {len(texts)}")
    
    # Создаем embeddings
    print("🔧 Инициализируем OpenAI Embeddings...")
    embeddings = OpenAIEmbeddings(
        openai_api_key=api_key,
        model="text-embedding-ada-002"
    )
    
    # Создаем FAISS индекс по частям
    print("🔄 Создаем FAISS индекс...")
    index_path = Path("data/faiss_index")
    
    batch_size = 50  # Уменьшенный размер батча для стабильности
    vectorstore = None
    
    total_batches = (len(texts) + batch_size - 1) // batch_size
    
    for i in range(0, len(texts), batch_size):
        batch_num = i // batch_size + 1
        batch = texts[i:i+batch_size]
        
        print(f"  📦 Обрабатываем батч {batch_num}/{total_batches} ({len(batch)} частей)...")
        
        try:
            if vectorstore is None:
                vectorstore = FAISS.from_documents(batch, embeddings)
                print(f"    ✅ Создан базовый индекс")
            else:
                vectorstore.add_documents(batch)
                print(f"    ✅ Добавлен батч в индекс")
                
        except Exception as e:
            print(f"    ❌ Ошибка обработки батча {batch_num}: {e}")
            continue
    
    if vectorstore is None:
        print("❌ Не удалось создать векторное хранилище")
        return
    
    # Сохраняем индекс
    print("💾 Сохраняем FAISS индекс...")
    index_path.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_path))
    
    print(f"\n🎉 УСПЕШНО ЗАВЕРШЕНО!")
    print(f"📊 Статистика:")
    print(f"  • Документов обработано: {len(docs)}")
    print(f"  • Частей создано: {len(texts)}")
    print(f"  • Индекс сохранен в: {index_path}")
    print(f"\n💡 Теперь можно запускать приложение: uvicorn src.app.main:app --reload")

if __name__ == "__main__":
    main()