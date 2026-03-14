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
    vault_file: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
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


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_timeline_events_date", "event_date"),
    )

    def __repr__(self) -> str:
        return f"<TimelineEvent {self.event_date}: {self.title}>"


class ContradictionEvidence(Base):
    __tablename__ = "contradiction_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        ForeignKey("contradictions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
    )
    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ce_contradiction_id", "contradiction_id"),
    )

    def __repr__(self) -> str:
        return f"<ContradictionEvidence contradiction={self.contradiction_id} chunk={self.chunk_id}>"


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


class CrossExamQuestion(Base):
    __tablename__ = "crossexam_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    contradiction_id: Mapped[int] = mapped_column(
        ForeignKey("contradictions.id", ondelete="CASCADE"), nullable=False
    )
    questions_text: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[str] = mapped_column(String(50), nullable=False, default="cross-examination")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        Index("ix_crossexam_contradiction_id", "contradiction_id"),
    )

    def __repr__(self) -> str:
        return f"<CrossExamQuestion contradiction={self.contradiction_id}>"


class CostEntry(Base):
    __tablename__ = "cost_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    line_item: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    amount_per_unit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    units: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    date_range_start: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date_range_end: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<CostEntry {self.id}: {self.category} — {self.line_item}>"


class ShareView(Base):
    __tablename__ = "share_views"

    id: Mapped[int] = mapped_column(primary_key=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    referrer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<ShareView {self.id}: {self.viewed_at}>"


class ScrapedDecision(Base):
    __tablename__ = "scraped_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citation: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, unique=True)
    court: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="canlii")
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    embedded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_scraped_decisions_url", "url"),
        Index("ix_scraped_decisions_embedded", "embedded"),
    )

    def __repr__(self) -> str:
        return f"<ScrapedDecision {self.citation or self.id}>"


class ScrapedReport(Base):
    __tablename__ = "scraped_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="rcy")
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    embedded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_scraped_reports_embedded", "embedded"),
    )

    def __repr__(self) -> str:
        return f"<ScrapedReport {self.id}: {self.title[:40]}>"


class ScrapedHansard(Base):
    __tablename__ = "scraped_hansard"

    id: Mapped[int] = mapped_column(primary_key=True)
    debate_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    speaker: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    session: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="hansard")
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    embedded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_scraped_hansard_url_speaker", "url", "speaker", unique=True),
        Index("ix_scraped_hansard_embedded", "embedded"),
    )

    def __repr__(self) -> str:
        return f"<ScrapedHansard {self.debate_date}: {self.speaker}>"
