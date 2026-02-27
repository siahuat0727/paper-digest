# Paper Weekly Digest (MVP)

每周自动生成一份论文周报（Markdown），按你定义的期刊范围与关键词筛选新增论文，去重后输出，适合长期稳定运行。

## What

- 每周抓取公开数据源新增论文（MVP: arXiv + PubMed）
- 根据配置筛选（关键词、期刊白名单、排除词）
- 依据持久化去重索引过滤重复论文
- 生成中文周报 Markdown 文件

## Why

- 生成流程无聊天上下文依赖，可重复执行
- 长期状态（已推送索引）保存在仓库文件中，便于版本化与恢复
- 配置驱动，可随时调整关注方向而不改代码

## How

### 1) 准备

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
```

根据你的需求编辑 `config/config.yaml`。

### 2) 本地运行

```bash
python scripts/run_digest.py --config config/config.yaml --days 7
```

运行后会更新：

- `output/digest_YYYY-Www.md`（本周周报）
- `state/seen_ids.json`（去重状态）

### 3) GitHub Actions 定时运行

仓库已提供 `.github/workflows/weekly_digest.yml`：

- 每周一 UTC 01:00 自动执行
- 自动提交 `output/` 和 `state/` 的变更
- 可手动触发（workflow_dispatch）

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
│   ├── digest.py
│   ├── filtering.py
│   ├── markdown.py
│   ├── models.py
│   ├── state.py
│   └── fetchers/
│       ├── arxiv.py
│       └── pubmed.py
└── state/
    └── seen_ids.json
```

## Notes

- 周报语言为中文；摘要为“中文导读 + 原文关键句”形式，强调快速扫读。
- 如果你需要更强的中文摘要质量，可在稳定后接入大模型摘要步骤（可选）。
