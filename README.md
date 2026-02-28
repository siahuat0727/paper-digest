# Paper Weekly Digest (MVP)

每周自动生成一份论文周报（Markdown），当前仅使用 PubMed 数据源，按关键词与期刊分组规则筛选并输出。

## What

- 每周抓取 PubMed 新增论文
- 按关键词 + 期刊白名单筛选
- 按「大类 -> 期刊」结构输出周报
- 去重开关可配，默认关闭（便于测试）

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
python scripts/run_digest.py --config config/config.yaml --days 7
```

运行后会更新：

- `output/digest_YYYY-Www.md`（本周周报）
- `state/seen_ids.json`（仅在启用去重时更新）

## Config Highlights

- `sources.pubmed.enabled`: 是否启用 PubMed
- `sources.pubmed.retmax`: PubMed 最大检索数
- `filters.keywords`: 关键词列表
- `filters.journal_groups`: 期刊分组（支持别名）
- `state.enable_dedup`: 是否启用去重（默认 `false`）

## Project Structure

```text
.
├── .github/workflows/weekly_digest.yml
├── config/
│   └── config.example.yaml
├── output/
├── scripts/
│   └── run_digest.py
├── src/paper_digest/
│   ├── config.py
│   ├── digest.py
│   ├── filtering.py
│   ├── journals.py
│   ├── markdown.py
│   ├── models.py
│   ├── state.py
│   └── fetchers/
│       └── pubmed.py
└── state/
    └── seen_ids.json
```
