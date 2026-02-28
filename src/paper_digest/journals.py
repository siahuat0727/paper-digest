from __future__ import annotations

import re

from paper_digest.config import JournalGroupConfig
from paper_digest.models import Paper


def normalize_journal_name(value: str) -> str:
    lowered = value.lower().strip()
    lowered = lowered.replace("&", " and ")
    lowered = re.sub(r"^the\s+", "", lowered)
    return re.sub(r"[^a-z0-9]+", "", lowered)


def build_alias_mapping(journal_groups: list[JournalGroupConfig]) -> dict[str, tuple[str, str]]:
    mapping: dict[str, tuple[str, str]] = {}
    for group in journal_groups:
        for journal in group.journals:
            for alias in journal.aliases:
                key = normalize_journal_name(alias)
                if not key or key in mapping:
                    continue
                mapping[key] = (group.name, journal.name)
    return mapping


def count_papers_by_group_journal(
    papers: list[Paper],
    journal_groups: list[JournalGroupConfig],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {
        group.name: {journal.name: 0 for journal in group.journals}
        for group in journal_groups
    }
    mapping = build_alias_mapping(journal_groups)

    for paper in papers:
        key = normalize_journal_name(paper.journal or "")
        mapped = mapping.get(key)
        if not mapped:
            continue
        group_name, journal_name = mapped
        counts[group_name][journal_name] += 1

    return counts
