from __future__ import annotations

import re

from paper_digest.config import JournalGroupConfig


def normalize_journal_name(value: str) -> str:
    lowered = value.lower().strip()
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
