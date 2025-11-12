from sqlalchemy import String, Integer, Text, Enum, JSON, ForeignKey, DateTime, func, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db import Base
import enum, uuid

def gen_uuid(): return str(uuid.uuid4())

class Risk(str, enum.Enum): low="low"; medium="medium"; high="high"

class User(Base):
    __tablename__="users"
    id:Mapped[str]=mapped_column(String, primary_key=True, default=gen_uuid)
    username:Mapped[str]=mapped_column(String, unique=True, index=True)
    password_hash:Mapped[str]=mapped_column(String)
    name:Mapped[str]=mapped_column(String, default="")
    age:Mapped[int]=mapped_column(Integer, default=0)
    annual_income:Mapped[Numeric]=mapped_column(Numeric, default=0)
    risk_tolerance:Mapped[Risk]=mapped_column(Enum(Risk), default=Risk.medium)
    financial_goal:Mapped[str]=mapped_column(Text, default="")
    retirement_age:Mapped[int]=mapped_column(Integer, default=65)
    created_at:Mapped[str]=mapped_column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__="documents"
    id:Mapped[str]=mapped_column(String, primary_key=True, default=gen_uuid)
    title:Mapped[str]=mapped_column(String)
    category:Mapped[str]=mapped_column(String)
    source_tag:Mapped[str]=mapped_column(String, default="wm-guide")
    created_at:Mapped[str]=mapped_column(DateTime(timezone=True), server_default=func.now())

class Chunk(Base):
    __tablename__="chunks"
    id:Mapped[str]=mapped_column(String, primary_key=True)
    doc_id:Mapped[str]=mapped_column(String, ForeignKey("documents.id"))
    content:Mapped[str]=mapped_column(Text)
    meta:Mapped[dict]=mapped_column(JSON, default={})
    embedding:Mapped[list]=mapped_column(Vector(1536))

class Chat(Base):
    __tablename__="chats"
    id:Mapped[str]=mapped_column(String, primary_key=True, default=gen_uuid)
    user_id:Mapped[str]=mapped_column(String, ForeignKey("users.id"))
    title:Mapped[str]=mapped_column(String, default="")
    created_at:Mapped[str]=mapped_column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__="messages"
    id:Mapped[str]=mapped_column(String, primary_key=True, default=gen_uuid)
    chat_id:Mapped[str]=mapped_column(String, ForeignKey("chats.id"))
    role:Mapped[str]=mapped_column(String)
    content:Mapped[str]=mapped_column(Text)
    retrieval_meta:Mapped[dict|None]=mapped_column(JSON, nullable=True)
    created_at:Mapped[str]=mapped_column(DateTime(timezone=True), server_default=func.now())
