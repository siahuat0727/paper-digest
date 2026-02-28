from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from paper_digest.config import AppConfig
from paper_digest.fetchers.pubmed import fetch_pubmed
from paper_digest.filtering import apply_filters, normalize_title
from paper_digest.journals import count_papers_by_group_journal
from paper_digest.markdown import render_digest_markdown
from paper_digest.models import Paper
from paper_digest.state import SeenState, load_state, prune_state, save_state


@dataclass(frozen=True)
class RunResult:
    total_candidates: int
    total_filtered: int
    total_new: int
    dedup_enabled: bool
    output_path: Path
    state_path: Path | None


def run_digest(config: AppConfig, days: int = 7, now: datetime | None = None) -> RunResult:
    now_utc = now or datetime.now(timezone.utc)
    window_end = now_utc
    window_start = now_utc - timedelta(days=days)

    candidates: list[Paper] = []
    if config.sources.pubmed.enabled:
        candidates.extend(
            fetch_pubmed(
                keywords=config.filters.keywords,
                start_date=window_start,
                end_date=window_end,
                retmax=config.sources.pubmed.retmax,
            )
        )

    filtered = apply_filters(
        papers=candidates,
        keywords=config.filters.keywords,
        journal_groups=config.filters.journal_groups,
    )
    journal_counts_before_filter = count_papers_by_group_journal(candidates, config.filters.journal_groups)
    journal_counts_after_filter = count_papers_by_group_journal(filtered, config.filters.journal_groups)

    state_path: Path | None = None
    if config.state.enable_dedup:
        state_path = Path(config.state.seen_index_path)
        state = prune_state(load_state(state_path), config.state.retention_days)
        new_papers, updated_state = dedup_with_state(filtered, state, now_utc)
        save_state(state_path, updated_state)
    else:
        new_papers = filtered

    sorted_papers = sorted(new_papers, key=lambda p: p.published_at, reverse=True)
    output_dir = Path(config.output.dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    year, week, _ = window_end.isocalendar()
    output_path = output_dir / f"{config.output.filename_prefix}_{year}-W{week:02d}.md"
    markdown = render_digest_markdown(
        sorted_papers,
        window_start=window_start,
        window_end=window_end,
        journal_groups=config.filters.journal_groups,
        total_before_filter=len(candidates),
        total_after_filter=len(filtered),
        journal_counts_before_filter=journal_counts_before_filter,
        journal_counts_after_filter=journal_counts_after_filter,
    )
    output_path.write_text(markdown, encoding="utf-8")

    return RunResult(
        total_candidates=len(candidates),
        total_filtered=len(filtered),
        total_new=len(new_papers),
        dedup_enabled=config.state.enable_dedup,
        output_path=output_path,
        state_path=state_path,
    )


def dedup_with_state(papers: list[Paper], state: SeenState, now: datetime) -> tuple[list[Paper], SeenState]:
    seen_ids = dict(state.seen_ids)
    seen_titles = dict(state.seen_titles)

    output: list[Paper] = []
    now_iso = now.isoformat()

    for p in papers:
        nid = p.dedup_id
        ntitle = normalize_title(p.title)
        if nid in seen_ids:
            continue
        if ntitle in seen_titles:
            continue

        output.append(p)
        seen_ids[nid] = now_iso
        if ntitle:
            seen_titles[ntitle] = now_iso

    return output, SeenState(seen_ids=seen_ids, seen_titles=seen_titles)
