# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "AI Agent Chat" in r.text

def test_history_empty():
    r = client.get("/api/v1/history?thread_id=none")
    assert r.status_code == 200
    assert r.json() == []

def test_message_and_history():
    # отправка сообщения
    resp1 = client.post("/api/v1/message", json={"thread_id":"t1","message":"Hello"})
    assert resp1.status_code == 200
    assert "reply" in resp1.json()

    # проверка истории
    resp2 = client.get("/api/v1/history?thread_id=t1")
    assert resp2.status_code == 200
    hist = resp2.json()
    assert len(hist) == 2
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"