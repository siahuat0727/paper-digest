from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Paper:
    source: str
    source_id: str
    title: str
    abstract: str
    url: str
    published_at: datetime
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def dedup_id(self) -> str:
        return f"{self.source}:{self.source_id}"
