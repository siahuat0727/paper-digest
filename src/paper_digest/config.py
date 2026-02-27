from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ArxivConfig:
    enabled: bool
    max_results: int


@dataclass(frozen=True)
class PubMedConfig:
    enabled: bool
    retmax: int


@dataclass(frozen=True)
class SourceConfig:
    arxiv: ArxivConfig
    pubmed: PubMedConfig


@dataclass(frozen=True)
class FilterConfig:
    keywords: list[str]
    include_journals: list[str]
    exclude_keywords: list[str]


@dataclass(frozen=True)
class OutputConfig:
    dir: str
    filename_prefix: str


@dataclass(frozen=True)
class StateConfig:
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
        data = yaml.safe_load(f)

    return AppConfig(
        sources=SourceConfig(
            arxiv=ArxivConfig(
                enabled=bool(data["sources"]["arxiv"].get("enabled", True)),
                max_results=int(data["sources"]["arxiv"].get("max_results", 100)),
            ),
            pubmed=PubMedConfig(
                enabled=bool(data["sources"]["pubmed"].get("enabled", True)),
                retmax=int(data["sources"]["pubmed"].get("retmax", 200)),
            ),
        ),
        filters=FilterConfig(
            keywords=list(data["filters"].get("keywords", [])),
            include_journals=list(data["filters"].get("include_journals", [])),
            exclude_keywords=list(data["filters"].get("exclude_keywords", [])),
        ),
        output=OutputConfig(
            dir=str(data["output"].get("dir", "output")),
            filename_prefix=str(data["output"].get("filename_prefix", "digest")),
        ),
        state=StateConfig(
            seen_index_path=str(data["state"].get("seen_index_path", "state/seen_ids.json")),
            retention_days=int(data["state"].get("retention_days", 365)),
        ),
    )
