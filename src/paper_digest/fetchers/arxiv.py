from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import requests

from paper_digest.models import Paper

ARXIV_API = "https://export.arxiv.org/api/query"
DEFAULT_HEADERS = {"User-Agent": "paper-weekly-digest/0.1 (https://github.com)"}


def _build_search_query(keywords: Iterable[str]) -> str:
    terms = [f'all:"{kw}"' for kw in keywords if kw.strip()]
    if not terms:
        return "all:*"
    return " OR ".join(terms)


def fetch_arxiv(
    keywords: list[str],
    start_date: datetime,
    end_date: datetime,
    max_results: int = 100,
) -> list[Paper]:
    query = _build_search_query(keywords)
    params = (
        f"search_query={quote_plus(query)}"
        f"&start=0&max_results={max_results}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    url = f"{ARXIV_API}?{params}"

    resp = requests.get(url, timeout=30, headers=DEFAULT_HEADERS)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.text)

    papers: list[Paper] = []
    for entry in parsed.entries:
        published_at = _parse_arxiv_time(entry.get("published", ""))
        if published_at is None:
            continue
        if not (start_date <= published_at <= end_date):
            continue

        title = (entry.get("title") or "").replace("\n", " ").strip()
        abstract = (entry.get("summary") or "").replace("\n", " ").strip()
        paper_url = entry.get("id") or ""
        source_id = paper_url.rsplit("/", 1)[-1] if paper_url else title
        authors = [a.get("name", "") for a in entry.get("authors", []) if a.get("name")]

        papers.append(
            Paper(
                source="arXiv",
                source_id=source_id,
                title=title,
                abstract=abstract,
                url=paper_url,
                published_at=published_at,
                authors=authors,
                journal=None,
            )
        )

    return papers


def _parse_arxiv_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
