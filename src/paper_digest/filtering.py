from __future__ import annotations

import re

from paper_digest.models import Paper


def apply_filters(
    papers: list[Paper],
    keywords: list[str],
    include_journals: list[str],
    exclude_keywords: list[str],
) -> list[Paper]:
    include_journals_lower = {j.lower().strip() for j in include_journals if j.strip()}
    exclude_keywords_lower = [k.lower().strip() for k in exclude_keywords if k.strip()]
    keyword_list = [k.strip() for k in keywords if k.strip()]

    result: list[Paper] = []
    for paper in papers:
        if include_journals_lower:
            journal = (paper.journal or "").lower().strip()
            if not journal:
                continue
            if journal not in include_journals_lower:
                continue

        full_text = f"{paper.title} {paper.abstract}".lower()
        if any(ex_kw in full_text for ex_kw in exclude_keywords_lower):
            continue

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
