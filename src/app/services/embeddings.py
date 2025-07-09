# src/app/services/embeddings.py
from langchain.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
embeddings = OpenAIEmbeddings()