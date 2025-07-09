# src/app/schemas/message.py
from pydantic import BaseModel

class MessageRequest(BaseModel):
    thread_id: str
    message: str

class MessageReply(BaseModel):
    status: str
    reply: str