#!/usr/bin/env python3
# scripts/ingest.py

import os
from pathlib import Path
from langchain.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from dotenv import load_dotenv

def load_documents(folder_path: Path):
    docs = []
    for file in folder_path.glob("*"):
        if file.suffix.lower() == ".pdf":
            loader = PyPDFLoader(str(file))
        else:
            loader = TextLoader(str(file), encoding="utf-8")
        docs.extend(loader.load())
    return docs

def main():
    load_dotenv()
    docs_folder = Path("data/docs")
    index_path = Path("data/faiss_index")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = load_documents(docs_folder)
    texts = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings()

    # Build FAISS index in batches to avoid OpenAI token-limit errors
    batch_size = 500
    vectorstore = None
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        if vectorstore is None:
            vectorstore = FAISS.from_documents(batch, embeddings)
        else:
            vectorstore.add_documents(batch)

    index_path.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_path))
    print(f"✅ Ingested {len(texts)} chunks into FAISS index at {index_path}")

if __name__ == "__main__":
    main()