#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate weekly paper digest.")
    parser.add_argument("--config", default="config/config.yaml", help="Path to YAML config file.")
    parser.add_argument("--days", type=int, default=7, help="Look-back window in days.")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

    from paper_digest.config import load_config
    from paper_digest.digest import run_digest

    config = load_config(args.config)
    result = run_digest(config=config, days=args.days)
    print(f"Candidates: {result.total_candidates}")
    print(f"After filters: {result.total_filtered}")
    print(f"New papers: {result.total_new}")
    print(f"Digest written: {result.output_path}")
    print(f"State written: {result.state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
