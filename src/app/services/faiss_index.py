# src/app/services/faiss_index.py
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from src.app.services.embeddings import embeddings

load_dotenv()
INDEX_PATH = Path("data/faiss_index")

def get_vectorstore():
    """Загружает FAISS векторное хранилище"""
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"FAISS индекс не найден в {INDEX_PATH}. "
            f"Запустите сначала: python scripts/ingest.py"
        )
    
    try:
        return FAISS.load_local(
            str(INDEX_PATH), 
            embeddings, 
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки FAISS индекса: {e}")

def query_index(query: str, k: int = 5):
    """Поиск похожих документов в индексе"""
    try:
        store = get_vectorstore()
        docs_and_scores = store.similarity_search_with_score(query, k=k)
        
        # Возвращаем только текст документов с их релевантностью
        results = []
        for doc, score in docs_and_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            })
        
        return results
    except Exception as e:
        raise RuntimeError(f"Ошибка поиска в индексе: {e}")

def test_index():
    """Тестирование индекса"""
    try:
        store = get_vectorstore()
        # Простой тест поиска
        results = store.similarity_search("тест", k=1)
        return len(results) > 0
    except:
        return False