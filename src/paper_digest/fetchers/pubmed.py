from __future__ import annotations

from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests

from paper_digest.models import Paper

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
DEFAULT_HEADERS = {"User-Agent": "paper-weekly-digest/0.1 (https://github.com)"}


def fetch_pubmed(
    keywords: list[str],
    start_date: datetime,
    end_date: datetime,
    retmax: int = 200,
) -> list[Paper]:
    ids = _search_ids(
        keywords=keywords,
        start_date=start_date,
        end_date=end_date,
        retmax=retmax,
    )
    if not ids:
        return []

    papers: list[Paper] = []
    for root in _fetch_details_roots(ids):
        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            if medline is None:
                continue
            article_node = medline.find("Article")
            if article_node is None:
                continue

            pmid = _text_or_empty(medline.find("PMID"))
            title = _node_text(article_node.find("ArticleTitle")).replace("\n", " ").strip()
            abstract = _extract_abstract(article_node)
            journal = _extract_journal(article_node)
            published_at = _extract_published_at(article_node)
            if not published_at:
                continue
            if not (start_date <= published_at <= end_date):
                continue

            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            authors = _extract_authors(article_node)

            papers.append(
                Paper(
                    source="PubMed",
                    source_id=pmid or title,
                    title=title,
                    abstract=abstract,
                    url=url,
                    published_at=published_at,
                    authors=authors,
                    journal=journal or None,
                )
            )

    return papers


def _search_ids(
    keywords: list[str],
    start_date: datetime,
    end_date: datetime,
    retmax: int,
) -> list[str]:
    base = " OR ".join([f'"{k}"[Title/Abstract]' for k in keywords if k.strip()]) or "all[sb]"
    term = f"({base})"
    params = {
        "db": "pubmed",
        "term": term,
        "datetype": "pdat",
        "mindate": start_date.strftime("%Y/%m/%d"),
        "maxdate": end_date.strftime("%Y/%m/%d"),
        "retmax": retmax,
        "retmode": "json",
    }
    resp = requests.get(PUBMED_ESEARCH, params=params, timeout=30, headers=DEFAULT_HEADERS)
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def _fetch_details_roots(ids: list[str], batch_size: int = 120) -> list[ET.Element]:
    roots: list[ET.Element] = []
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        payload = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
        }
        resp = requests.post(PUBMED_EFETCH, data=payload, timeout=30, headers=DEFAULT_HEADERS)
        resp.raise_for_status()
        roots.append(ET.fromstring(resp.text))
    return roots


def _extract_abstract(article_node: ET.Element) -> str:
    nodes = article_node.findall(".//Abstract/AbstractText")
    parts = [_node_text(n).strip() for n in nodes if _node_text(n).strip()]
    return " ".join(parts)


def _extract_journal(article_node: ET.Element) -> str:
    return _text_or_empty(article_node.find(".//Journal/Title")).strip()


def _extract_authors(article_node: ET.Element) -> list[str]:
    authors: list[str] = []
    for node in article_node.findall(".//AuthorList/Author"):
        last = _text_or_empty(node.find("LastName")).strip()
        fore = _text_or_empty(node.find("ForeName")).strip()
        collective = _text_or_empty(node.find("CollectiveName")).strip()
        if collective:
            authors.append(collective)
            continue
        if last or fore:
            authors.append(f"{fore} {last}".strip())
    return authors


def _extract_published_at(article_node: ET.Element) -> datetime | None:
    year = _text_or_empty(article_node.find(".//JournalIssue/PubDate/Year"))
    month = _text_or_empty(article_node.find(".//JournalIssue/PubDate/Month"))
    day = _text_or_empty(article_node.find(".//JournalIssue/PubDate/Day"))

    if not year.isdigit():
        return None
    mm = _month_to_int(month)
    dd = int(day) if day.isdigit() else 1
    try:
        return datetime(int(year), mm, dd, tzinfo=timezone.utc)
    except ValueError:
        pass

    # Fallback for records without complete JournalIssue/PubDate.
    alt_year = _text_or_empty(article_node.find(".//ArticleDate/Year"))
    alt_month = _text_or_empty(article_node.find(".//ArticleDate/Month"))
    alt_day = _text_or_empty(article_node.find(".//ArticleDate/Day"))
    if alt_year.isdigit():
        try:
            return datetime(
                int(alt_year),
                _month_to_int(alt_month),
                int(alt_day) if alt_day.isdigit() else 1,
                tzinfo=timezone.utc,
            )
        except ValueError:
            return None
    return None


def _month_to_int(value: str) -> int:
    value = value.strip()
    if value.isdigit():
        month = int(value)
        return month if 1 <= month <= 12 else 1
    mapping = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }
    return mapping.get(value[:3], 1)


def _text_or_empty(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext())
