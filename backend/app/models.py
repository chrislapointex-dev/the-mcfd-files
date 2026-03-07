from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from .database import Base


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    citation: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    court: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_decisions_citation", "citation"),
        Index("ix_decisions_date", "date"),
        Index("ix_decisions_court", "court"),
        Index("ix_decisions_source", "source"),
    )

    def __repr__(self) -> str:
        return f"<Decision {self.citation or self.id}>"


class Memory(Base):
    __tablename__ = "memory"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_memory_region", "user_id", "region"),
        Index("ix_memory_key", "user_id", "key"),
    )

    def __repr__(self) -> str:
        return f"<Memory {self.region}/{self.key}>"


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_value: Mapped[str] = mapped_column(Text, nullable=False)
    context_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_entities_decision_id", "decision_id"),
        Index("ix_entities_type", "entity_type"),
    )

    def __repr__(self) -> str:
        return f"<Entity {self.entity_type}:{self.entity_value}>"


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_num: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    page_estimate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(384), nullable=True)

    __table_args__ = (
        Index("ix_chunks_decision_id", "decision_id"),
        # Unique constraint so re-runs don't double-insert
        Index("ix_chunks_decision_chunk", "decision_id", "chunk_num", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Chunk decision={self.decision_id} #{self.chunk_num}>"


class Contradiction(Base):
    __tablename__ = "contradictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_doc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Contradiction {self.id}: {self.severity}>"


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    item: Mapped[str] = mapped_column(Text, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ChecklistItem {self.id}: {self.category}>"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(String(100), nullable=False)
    file_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    filed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    last_update: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Complaint {self.id}: {self.body} [{self.status}]>"
