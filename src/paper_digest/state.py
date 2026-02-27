from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass
class SeenState:
    seen_ids: dict[str, str]
    seen_titles: dict[str, str]


def load_state(path: str | Path) -> SeenState:
    p = Path(path)
    if not p.exists():
        return SeenState(seen_ids={}, seen_titles={})
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return SeenState(
        seen_ids=dict(data.get("seen_ids", {})),
        seen_titles=dict(data.get("seen_titles", {})),
    )


def save_state(path: str | Path, state: SeenState) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "seen_ids": state.seen_ids,
        "seen_titles": state.seen_titles,
    }
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def prune_state(state: SeenState, retention_days: int) -> SeenState:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    def _keep(ts: str) -> bool:
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt >= cutoff
        except ValueError:
            return False

    return SeenState(
        seen_ids={k: v for k, v in state.seen_ids.items() if _keep(v)},
        seen_titles={k: v for k, v in state.seen_titles.items() if _keep(v)},
    )
