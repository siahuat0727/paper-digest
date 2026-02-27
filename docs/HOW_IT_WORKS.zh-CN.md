# Paper Weekly Digest 工作机制详解（中文）

本文档说明当前 MVP 版本如何运行，重点解释“无聊天上下文依赖 + 长期状态可持久化”的实现方式。

## 1. 设计目标与边界

- 目标：每次执行都只依赖三类输入
  - 当前配置（`config/config.yaml`）
  - 本次时间窗口内抓取到的候选论文
  - 历史去重索引（`state/seen_ids.json`）
- 不依赖：Chat 对话历史、人工临时上下文
- MVP 输出：一份中文 Markdown 周报（`output/digest_YYYY-Www.md`）

## 2. 目录与模块职责

- 入口脚本：`scripts/run_digest.py`
  - 解析命令行参数（`--config`、`--days`）
  - 加载配置并调用主流程
- 主流程：`src/paper_digest/digest.py`
  - 组织抓取、筛选、去重、渲染、落盘
- 数据抓取：
  - `src/paper_digest/fetchers/arxiv.py`
  - `src/paper_digest/fetchers/pubmed.py`
- 筛选逻辑：`src/paper_digest/filtering.py`
- 状态管理：`src/paper_digest/state.py`
- Markdown 渲染：`src/paper_digest/markdown.py`
- 配置解析：`src/paper_digest/config.py`
- 统一数据模型：`src/paper_digest/models.py`

## 3. 一次运行的完整时序

1. `scripts/run_digest.py` 读取配置文件。
2. 计算时间窗口：
   - `window_end = now(UTC)`
   - `window_start = now - days`
3. 按配置启用的数据源进行抓取：
   - arXiv：按关键词构造搜索语句，按提交时间倒序获取。
   - PubMed：按关键词 + 日期范围检索 ID，再批量拉取详情。
4. 将不同来源映射为统一 `Paper` 结构。
5. 执行筛选：
   - 关键词命中
   - 期刊白名单（可选）
   - 排除关键词（可选）
6. 加载历史状态并执行保留期裁剪（retention）。
7. 去重：
   - 主键：`source:source_id`
   - 兜底：规范化标题（去符号小写）
8. 仅对“新论文”生成周报 Markdown。
9. 写入输出文件与新状态索引。

## 4. 数据源实现细节

### 4.1 arXiv

- 接口：`https://export.arxiv.org/api/query`
- 查询方式：将关键词拼接为 `OR`（`all:"keyword"`）
- 结果排序：`submittedDate desc`
- 字段提取：
  - `title`、`summary`、`id`、`authors`、`published`
- 时间过滤：本地按 `start_date <= published_at <= end_date` 二次过滤

说明：即使 API 返回了更广时间范围，主流程仍会依据时间窗口做最终约束，保证可重复执行一致性。

### 4.2 PubMed

- 检索接口：`esearch.fcgi`
  - 使用 `mindate/maxdate + datetype=pdat` 控制时间范围
- 详情接口：`efetch.fcgi`
  - 批量按 PMID 拉取 XML
- 字段提取：
  - 标题、摘要、作者、期刊、发布日期
- 日期解析：
  - 优先 `JournalIssue/PubDate`
  - 回退 `ArticleDate`

说明：PubMed 记录结构不完全一致，代码包含了缺失字段回退逻辑。

## 5. 筛选策略

筛选在 `filtering.apply_filters(...)` 中执行，顺序如下：

1. 若设置 `include_journals`：
   - 仅保留期刊名在白名单中的论文
   - 无期刊信息的论文在该模式下会被丢弃
2. 若命中 `exclude_keywords` 任意词，直接丢弃
3. 若设置了 `keywords`：
   - 标题 + 摘要必须命中至少一个关键词
   - 命中的关键词会回填到 `matched_keywords`

这使得“业务意图（看什么/不看什么）”完全配置化，无需改代码。

## 6. 去重与长期状态

### 6.1 状态文件结构

`state/seen_ids.json`：

```json
{
  "seen_ids": {
    "arXiv:2602.12345v1": "2026-02-27T00:00:00+00:00"
  },
  "seen_titles": {
    "normalizedtitleexample": "2026-02-27T00:00:00+00:00"
  }
}
```

### 6.2 去重规则

- 第一层：`dedup_id = "{source}:{source_id}"`
- 第二层：规范化标题（移除符号、转小写）

只有“两层都未命中”的论文才会进入本周输出，并写回状态。

### 6.3 retention 机制

- 配置项：`state.retention_days`
- 每次运行开始会先裁剪过旧记录，防止状态无限膨胀

## 7. Markdown 产出规则

渲染在 `markdown.render_digest_markdown(...)` 中完成。

- 文件名：`{prefix}_{year}-W{week}.md`
- 内容包括：
  - 时间范围
  - 收录数量
  - 每篇论文的来源、日期、作者、链接、命中关键词、中文导读
- 中文导读策略（MVP）：
  - 模板化中文句式 + 摘要首句
  - 目标是“可快速扫读”，不是深度综述

## 8. GitHub Actions 定时运行

工作流文件：`.github/workflows/weekly_digest.yml`

- 触发：
  - `schedule`：每周一 UTC 01:00
  - `workflow_dispatch`：手动触发
- 步骤：
  1. 拉取仓库
  2. 安装依赖
  3. 若不存在 `config/config.yaml`，用示例模板复制
  4. 执行 digest 生成
  5. 提交 `output/` 与 `state/` 的变更并推送

这保证了“输出 + 去重状态”都持久化在仓库里，下一次运行可继续增量。

## 9. 配置项说明（MVP）

示例见 `config/config.example.yaml`。

- `sources.arxiv.enabled`: 是否启用 arXiv
- `sources.arxiv.max_results`: arXiv 最大拉取数
- `sources.pubmed.enabled`: 是否启用 PubMed
- `sources.pubmed.retmax`: PubMed 最大检索数
- `filters.keywords`: 关注关键词列表
- `filters.include_journals`: 期刊白名单（空数组代表不限制）
- `filters.exclude_keywords`: 排除关键词
- `output.dir`: 输出目录
- `output.filename_prefix`: 输出文件名前缀
- `state.seen_index_path`: 去重状态文件路径
- `state.retention_days`: 去重状态保留天数

## 10. 失败场景与恢复建议

- API 短时失败（网络/限流）：
  - 现状：请求失败会抛错终止本次执行
  - 建议：后续可加入重试与退避
- 配置错误（字段缺失/类型错误）：
  - 现状：会在配置解析阶段失败
  - 建议：后续可加入 schema 校验
- 输出为空：
  - 可能原因：窗口内无新增、筛选条件过严、全部被历史去重

恢复原则：状态文件是唯一长期索引；如需“全量重跑”，可备份后清空 `seen_ids.json`。

## 11. 后续演进建议

- 增加测试：
  - 配置解析、筛选逻辑、去重逻辑的单元测试
- 增强可靠性：
  - 请求重试、超时分级、源级失败降级
- 提升摘要质量：
  - 接入可选 LLM 摘要步骤（仍保持状态与调度独立）
- 通知渠道：
  - 在产出稳定后增加邮件发送（不影响核心抓取/去重管线）
