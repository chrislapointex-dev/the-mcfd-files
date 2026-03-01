from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class DecisionSummary(BaseModel):
    id: int
    source: str
    title: str
    citation: Optional[str]
    date: Optional[date]
    court: Optional[str]
    url: str
    snippet: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionDetail(DecisionSummary):
    full_text: Optional[str]
    scraped_at: Optional[datetime]


class PaginatedDecisions(BaseModel):
    items: list[DecisionSummary]
    total: int
    page: int
    per_page: int
    pages: int


class FiltersResponse(BaseModel):
    courts: list[str]
    year_min: Optional[int]
    year_max: Optional[int]
