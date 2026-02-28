from __future__ import annotations

from datetime import datetime

from paper_digest.config import JournalGroupConfig
from paper_digest.journals import build_alias_mapping, normalize_journal_name
from paper_digest.models import Paper


def render_digest_markdown(
    papers: list[Paper],
    window_start: datetime,
    window_end: datetime,
    journal_groups: list[JournalGroupConfig] | None = None,
) -> str:
    configured_groups = [g for g in (journal_groups or []) if g.journals]
    configured_journal_count = sum(len(group.journals) for group in configured_groups)
    lines: list[str] = []
    lines.append("# 论文周报")
    lines.append("")
    lines.append(f"- 时间范围：{window_start.date()} ~ {window_end.date()}")
    lines.append(f"- 收录数量：{len(papers)}")
    if configured_groups:
        lines.append(f"- 目标大类数量：{len(configured_groups)}")
        lines.append(f"- 目标期刊数量：{configured_journal_count}")
    lines.append("")

    if not papers and not configured_groups:
        lines.append("本周没有新增命中论文。")
        lines.append("")
        return "\n".join(lines)

    if configured_groups:
        grouped = _group_by_journal_groups(papers, configured_groups)
        for group in configured_groups:
            group_data = grouped[group.name]
            group_total = sum(len(group_data[journal.name]) for journal in group.journals)
            lines.append(f"## {group.name}（{group_total}）")
            lines.append("")

            for journal in group.journals:
                journal_papers = group_data[journal.name]
                lines.append(f"### {journal.name}（{len(journal_papers)}）")
                lines.append("")
                if not journal_papers:
                    lines.append("- 本期无命中")
                    lines.append("")
                    continue

                for idx, paper in enumerate(journal_papers, start=1):
                    _append_paper_block(lines, paper, idx=idx, include_journal=False, heading_level=4)
        return "\n".join(lines)

    for idx, paper in enumerate(papers, start=1):
        _append_paper_block(lines, paper, idx=idx, include_journal=True, heading_level=3)

    return "\n".join(lines)


def build_cn_summary(paper: Paper) -> str:
    focus = "、".join(paper.matched_keywords) if paper.matched_keywords else "未显式标注关键词"
    sentence = _first_sentence(paper.abstract)
    if sentence:
        return f"该研究与「{focus}」相关。原文要点：{sentence}"
    return f"该研究与「{focus}」相关。摘要原文缺失。"


def _first_sentence(text: str) -> str:
    raw = " ".join(text.split())
    if not raw:
        return ""
    for sep in [". ", "! ", "? ", "。", "；", ";"]:
        if sep in raw:
            return raw.split(sep)[0].strip()[:260]
    return raw[:260]


def _group_by_journal_groups(
    papers: list[Paper],
    configured_groups: list[JournalGroupConfig],
) -> dict[str, dict[str, list[Paper]]]:
    grouped: dict[str, dict[str, list[Paper]]] = {
        group.name: {journal.name: [] for journal in group.journals}
        for group in configured_groups
    }
    mapper = build_alias_mapping(configured_groups)

    for paper in papers:
        key = normalize_journal_name(paper.journal or "")
        mapped = mapper.get(key)
        if not mapped:
            continue
        group_name, journal_name = mapped
        grouped[group_name][journal_name].append(paper)

    for group in configured_groups:
        for journal in group.journals:
            grouped[group.name][journal.name].sort(key=lambda p: p.published_at, reverse=True)
    return grouped


def _append_paper_block(
    lines: list[str],
    paper: Paper,
    idx: int,
    include_journal: bool,
    heading_level: int,
) -> None:
    lines.append(f"{'#' * heading_level} {idx}. {paper.title}")
    lines.append("")
    lines.append(f"- 来源：{paper.source}")
    if include_journal and paper.journal:
        lines.append(f"- 期刊：{paper.journal}")
    lines.append(f"- 日期：{paper.published_at.date()}")
    if paper.authors:
        authors = ", ".join(paper.authors[:6])
        if len(paper.authors) > 6:
            authors += ", et al."
        lines.append(f"- 作者：{authors}")
    if paper.url:
        lines.append(f"- 链接：[{paper.url}]({paper.url})")
    else:
        lines.append("- 链接：无")
    if paper.matched_keywords:
        lines.append(f"- 命中关键词：{', '.join(paper.matched_keywords)}")
    lines.append(f"- 中文导读：{build_cn_summary(paper)}")
    lines.append("")
