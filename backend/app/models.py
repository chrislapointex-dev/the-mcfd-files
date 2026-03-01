from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

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
