#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
from xml.etree import ElementTree as ET

import requests

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
DEFAULT_HEADERS = {"User-Agent": "paper-weekly-digest/0.1 (https://github.com)"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate journal alias mapping against PubMed.")
    parser.add_argument("--config", default="config/config.yaml", help="Path to YAML config file.")
    parser.add_argument("--days", type=int, default=365, help="Look-back window for validation.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Enable full validation (check all aliases and sample-title reverse mapping).",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from paper_digest.config import load_config
    from paper_digest.journals import build_alias_mapping, normalize_journal_name

    config = load_config(args.config)
    alias_mapping = build_alias_mapping(config.filters.journal_groups)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    start_str = start.strftime("%Y/%m/%d")
    end_str = end.strftime("%Y/%m/%d")

    ok_count = 0
    warn_count = 0
    miss_count = 0
    error_count = 0
    total = 0

    print(f"Validation window: {start.date()} ~ {end.date()} ({args.days} days)")
    print("")

    for group in config.filters.journal_groups:
        print(f"[Group] {group.name}")
        for journal in group.journals:
            total += 1
            best_alias, best_hits, best_pmid, has_error = _best_alias_hit(
                journal.aliases,
                start_str,
                end_str,
                full=args.full,
            )
            if has_error:
                error_count += 1
            if best_hits <= 0 or not best_alias:
                miss_count += 1
                print(f"  [MISS] {journal.name} | no hits for configured aliases")
                continue

            if not args.full:
                ok_count += 1
                print(
                    f"  [OK]   {journal.name} | alias='{best_alias}' hits={best_hits}"
                )
                continue

            sample_title = _fetch_sample_journal_title(best_pmid) if best_pmid else ""
            mapped = alias_mapping.get(normalize_journal_name(sample_title)) if sample_title else None
            expected = (group.name, journal.name)
            if mapped != expected:
                warn_count += 1
                print(
                    f"  [WARN] {journal.name} | alias='{best_alias}' hits={best_hits} "
                    f"| sample='{sample_title or '<no sample>'}' | mapped_to={mapped}"
                )
                continue

            ok_count += 1
            print(
                f"  [OK]   {journal.name} | alias='{best_alias}' hits={best_hits} "
                f"| sample='{sample_title}'"
            )
        print("")

    print("Summary")
    print(f"- Total journals: {total}")
    print(f"- OK: {ok_count}")
    print(f"- WARN: {warn_count}")
    print(f"- MISS: {miss_count}")
    print(f"- Network errors: {error_count}")
    return 0 if warn_count == 0 and miss_count == 0 else 1


def _best_alias_hit(
    aliases: list[str],
    start_str: str,
    end_str: str,
    full: bool,
) -> tuple[str, int, str, bool]:
    best_alias = ""
    best_hits = -1
    best_pmid = ""
    has_error = False
    for alias in aliases:
        term = f'"{alias}"[Journal] AND ("{start_str}"[Date - Publication] : "{end_str}"[Date - Publication])'
        params = {
            "db": "pubmed",
            "term": term,
            "retmax": 1,
            "retmode": "json",
            "sort": "pub_date",
        }
        data = _safe_esearch(params)
        if data is None:
            has_error = True
            continue
        hits = int(data.get("count", "0"))
        idlist = data.get("idlist", []) or []
        pmid = idlist[0] if idlist else ""
        if not full and hits > 0:
            return alias, hits, pmid, has_error
        if hits > best_hits:
            best_alias = alias
            best_hits = hits
            best_pmid = pmid
    return best_alias, max(best_hits, 0), best_pmid, has_error


def _safe_esearch(params: dict[str, str]) -> dict | None:
    for attempt in range(3):
        try:
            resp = requests.get(PUBMED_ESEARCH, params=params, timeout=30, headers=DEFAULT_HEADERS)
            resp.raise_for_status()
            return resp.json().get("esearchresult", {})
        except requests.RequestException:
            if attempt == 2:
                return None
            time.sleep(0.8 * (attempt + 1))
    return None


def _fetch_sample_journal_title(pmid: str) -> str:
    if not pmid:
        return ""
    payload = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
    }
    resp = requests.post(PUBMED_EFETCH, data=payload, timeout=30, headers=DEFAULT_HEADERS)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    node = root.find(".//PubmedArticle/MedlineCitation/Article/Journal/Title")
    if node is None or node.text is None:
        return ""
    return node.text.strip()


if __name__ == "__main__":
    raise SystemExit(main())
