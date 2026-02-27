from __future__ import annotations

from datetime import datetime

from paper_digest.models import Paper


def render_digest_markdown(
    papers: list[Paper],
    window_start: datetime,
    window_end: datetime,
) -> str:
    lines: list[str] = []
    lines.append("# 论文周报")
    lines.append("")
    lines.append(f"- 时间范围：{window_start.date()} ~ {window_end.date()}")
    lines.append(f"- 收录数量：{len(papers)}")
    lines.append("")

    if not papers:
        lines.append("本周没有新增且未去重命中的论文。")
        lines.append("")
        return "\n".join(lines)

    for idx, paper in enumerate(papers, start=1):
        lines.append(f"## {idx}. {paper.title}")
        lines.append("")
        lines.append(f"- 来源：{paper.source}")
        if paper.journal:
            lines.append(f"- 期刊：{paper.journal}")
        lines.append(f"- 日期：{paper.published_at.date()}")
        if paper.authors:
            authors = ", ".join(paper.authors[:6])
            if len(paper.authors) > 6:
                authors += ", et al."
            lines.append(f"- 作者：{authors}")
        lines.append(f"- 链接：[{paper.url}]({paper.url})")
        if paper.matched_keywords:
            lines.append(f"- 命中关键词：{', '.join(paper.matched_keywords)}")
        lines.append(f"- 中文导读：{build_cn_summary(paper)}")
        lines.append("")

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
