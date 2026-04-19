import uuid
import json
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import relationship
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    query_sessions = relationship("QuerySession", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Document(db.Model):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    total_pages = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    query_sessions = relationship("QuerySession", back_populates="document", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "filename": self.filename,
            "total_pages": self.total_pages,
            "total_chunks": self.total_chunks,
            "status": self.status,
            "error_message": self.error_message,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_document_chunks_document_id", "document_id"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "text": self.text,
            "embedding": json.loads(self.embedding) if self.embedding else None,
            "text_preview": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QuerySession(db.Model):
    __tablename__ = "query_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=False)
    retrieved_chunk_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="query_sessions")
    document = relationship("Document", back_populates="query_sessions")
    llm_results = relationship("LLMResult", back_populates="query_session", cascade="all, delete-orphan")
    final_answer = relationship("FinalAnswer", back_populates="query_session", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "document_id": str(self.document_id),
            "query_text": self.query_text,
            "query_type": self.query_type,
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LLMResult(db.Model):
    __tablename__ = "llm_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_session_id = Column(String(36), ForeignKey("query_sessions.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(100), nullable=False)
    answer_text = Column(Text, nullable=False)
    cited_chunk_ids = Column(JSON, nullable=False, default=list)
    latency_ms = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    query_session = relationship("QuerySession", back_populates="llm_results")

    def to_dict(self):
        return {
            "id": str(self.id),
            "query_session_id": str(self.query_session_id),
            "model_name": self.model_name,
            "answer_text": self.answer_text,
            "cited_chunk_ids": self.cited_chunk_ids or [],
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FinalAnswer(db.Model):
    __tablename__ = "final_answers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_session_id = Column(String(36), ForeignKey("query_sessions.id", ondelete="CASCADE"), nullable=False)
    answer_text = Column(Text, nullable=False)
    citation_chunk_ids = Column(JSON, nullable=False, default=list)
    winning_model = Column(String(100), nullable=False)
    agreement_score = Column(Float, nullable=True)
    citation_overlap = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    query_session = relationship("QuerySession", back_populates="final_answer")

    def to_dict(self):
        return {
            "id": str(self.id),
            "query_session_id": str(self.query_session_id),
            "answer_text": self.answer_text,
            "citation_chunk_ids": self.citation_chunk_ids or [],
            "winning_model": self.winning_model,
            "agreement_score": self.agreement_score,
            "citation_overlap": self.citation_overlap,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
