from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PubMedConfig:
    enabled: bool
    retmax: int


@dataclass(frozen=True)
class SourceConfig:
    pubmed: PubMedConfig


@dataclass(frozen=True)
class JournalConfig:
    name: str
    aliases: list[str]


@dataclass(frozen=True)
class JournalGroupConfig:
    name: str
    journals: list[JournalConfig]


@dataclass(frozen=True)
class FilterConfig:
    keywords: list[str]
    journal_groups: list[JournalGroupConfig]


@dataclass(frozen=True)
class OutputConfig:
    dir: str
    filename_prefix: str


@dataclass(frozen=True)
class StateConfig:
    enable_dedup: bool
    seen_index_path: str
    retention_days: int


@dataclass(frozen=True)
class AppConfig:
    sources: SourceConfig
    filters: FilterConfig
    output: OutputConfig
    state: StateConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    sources_data = dict(data.get("sources", {}))
    pubmed_data = dict(sources_data.get("pubmed", {}))
    filters_data = dict(data.get("filters", {}))
    output_data = dict(data.get("output", {}))
    state_data = dict(data.get("state", {}))

    return AppConfig(
        sources=SourceConfig(
            pubmed=PubMedConfig(
                enabled=bool(pubmed_data.get("enabled", True)),
                retmax=int(pubmed_data.get("retmax", 200)),
            ),
        ),
        filters=FilterConfig(
            keywords=[str(v) for v in filters_data.get("keywords", []) if str(v).strip()],
            journal_groups=_parse_journal_groups(filters_data),
        ),
        output=OutputConfig(
            dir=str(output_data.get("dir", "output")),
            filename_prefix=str(output_data.get("filename_prefix", "digest")),
        ),
        state=StateConfig(
            enable_dedup=bool(state_data.get("enable_dedup", False)),
            seen_index_path=str(state_data.get("seen_index_path", "state/seen_ids.json")),
            retention_days=int(state_data.get("retention_days", 365)),
        ),
    )


def _parse_journal_groups(filters_data: dict[str, Any]) -> list[JournalGroupConfig]:
    raw_groups = filters_data.get("journal_groups", [])
    groups: list[JournalGroupConfig] = []

    if isinstance(raw_groups, list):
        for raw_group in raw_groups:
            if not isinstance(raw_group, dict):
                continue
            group_name = str(raw_group.get("name", "")).strip()
            if not group_name:
                continue
            journals = _parse_journals(raw_group.get("journals", []))
            groups.append(JournalGroupConfig(name=group_name, journals=journals))
        if groups:
            return groups

    # Backward compatibility for old config schema.
    legacy_journals = _parse_journals(filters_data.get("include_journals", []))
    if legacy_journals:
        return [JournalGroupConfig(name="未分组期刊", journals=legacy_journals)]
    return []


def _parse_journals(raw_value: Any) -> list[JournalConfig]:
    if not isinstance(raw_value, list):
        return []

    journals: list[JournalConfig] = []
    for item in raw_value:
        if isinstance(item, str):
            journal_name = item.strip()
            if not journal_name:
                continue
            journals.append(JournalConfig(name=journal_name, aliases=[journal_name]))
            continue

        if not isinstance(item, dict):
            continue
        journal_name = str(item.get("name", "")).strip()
        if not journal_name:
            continue
        raw_aliases = item.get("aliases", [])
        alias_values = [journal_name]
        if isinstance(raw_aliases, list):
            alias_values.extend([str(v).strip() for v in raw_aliases if str(v).strip()])
        journals.append(JournalConfig(name=journal_name, aliases=_dedup_list(alias_values)))
    return journals


def _dedup_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output
