# src/app/services/faiss_index.py
from pathlib import Path
from dotenv import load_dotenv
from langchain.vectorstores import FAISS
from src.app.services.embeddings import embeddings

load_dotenv()
INDEX_PATH = Path("data/faiss_index")

def get_vectorstore():
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found at {INDEX_PATH}. Run ingest script.")
    return FAISS.load_local(str(INDEX_PATH), embeddings)

def query_index(query: str, k: int = 5):
    store = get_vectorstore()
    docs_and_scores = store.similarity_search_with_score(query, k=k)
    return [doc.page_content for doc, _ in docs_and_scores]