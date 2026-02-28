from __future__ import annotations

import re

from paper_digest.config import JournalGroupConfig
from paper_digest.journals import build_alias_mapping, normalize_journal_name
from paper_digest.models import Paper


def apply_filters(
    papers: list[Paper],
    keywords: list[str],
    journal_groups: list[JournalGroupConfig],
) -> list[Paper]:
    journal_aliases = set(build_alias_mapping(journal_groups).keys())
    keyword_list = [k.strip() for k in keywords if k.strip()]

    result: list[Paper] = []
    for paper in papers:
        if journal_aliases:
            journal_key = normalize_journal_name(paper.journal or "")
            if not journal_key:
                continue
            if journal_key not in journal_aliases:
                continue

        full_text = f"{paper.title} {paper.abstract}".lower()

        matched = [kw for kw in keyword_list if kw.lower() in full_text]
        if keyword_list and not matched:
            continue

        result.append(
            Paper(
                source=paper.source,
                source_id=paper.source_id,
                title=paper.title,
                abstract=paper.abstract,
                url=paper.url,
                published_at=paper.published_at,
                authors=paper.authors,
                journal=paper.journal,
                matched_keywords=matched,
            )
        )

    return result


def normalize_title(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"\W+", "", lowered)
