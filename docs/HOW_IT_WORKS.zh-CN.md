# Paper Weekly Digest 工作机制（中文）

本文档说明当前版本的运行流程。当前实现仅保留 PubMed，筛选规则用于初筛，输出按「大类 -> 期刊」组织。

## 1. 设计目标

- 只依赖三类输入：
  - 配置文件（`config/config.yaml`）
  - 时间窗口内抓取到的论文
  - 去重状态（仅在启用去重时使用）
- 输出固定为 Markdown 周报（`output/digest_YYYY-Www.md`）
- 便于测试，默认不自动去重（`state.enable_dedup: false`）

## 2. 模块职责

- 入口：`scripts/run_digest.py`
- 主流程：`src/paper_digest/digest.py`
- 数据抓取：`src/paper_digest/fetchers/pubmed.py`
- 筛选：`src/paper_digest/filtering.py`
- 期刊映射：`src/paper_digest/journals.py`
- 渲染：`src/paper_digest/markdown.py`
- 配置解析：`src/paper_digest/config.py`
- 状态管理：`src/paper_digest/state.py`

## 3. 一次运行时序

1. 读取配置。
2. 计算时间窗口（`now - days` 到 `now`）。
3. 从 PubMed 拉取候选论文。
4. 按规则筛选：
   - 期刊白名单（来自 `journal_groups`）
   - 关键词命中（标题 + 摘要）
5. 若开启去重：
   - 加载并裁剪历史状态
   - 执行双层去重（`source:source_id` + 规范化标题）
6. 生成 Markdown 周报并写入 `output/`。
7. 若开启去重，写回 `state/seen_ids.json`。

## 4. PubMed 抓取细节

- 检索接口：`esearch.fcgi`（按日期范围检索 PMID）
- 详情接口：`efetch.fcgi`（批量拉取 XML）
- 提取字段：标题、摘要、作者、期刊、发布日期、链接
- 日期解析优先 `JournalIssue/PubDate`，回退 `ArticleDate`

## 5. 筛选规则

- 期刊：将 `filters.journal_groups` 中所有期刊名与别名归一化后做白名单匹配。
- 关键词：标题与摘要至少命中一个关键词（若关键词列表非空）。
- `exclude_keywords` 已移除，不再做排除词过滤。

## 6. 期刊分组与展示

配置结构示意：

```yaml
filters:
  journal_groups:
    - name: "综合顶刊"
      journals:
        - "Nature"
        - name: "NEJM"
          aliases:
            - "The New England Journal of Medicine"
            - "N Engl J Med"
```

输出结构：

- 二级标题：大类（例如“综合顶刊”）
- 三级标题：期刊（例如“Nature”）
- 四级标题：论文条目

即使某期刊本周无命中，也会显示“本期无命中”，便于固定版式查看。

## 7. 去重机制

- 配置项：`state.enable_dedup`
- 默认：`false`（关闭）
- 开启后规则：
  - 第一层：`source:source_id`
  - 第二层：规范化标题
- 状态保留期由 `state.retention_days` 控制

## 8. 关键配置项

- `sources.pubmed.enabled`
- `sources.pubmed.retmax`
- `filters.keywords`
- `filters.journal_groups[].name`
- `filters.journal_groups[].journals[].name`
- `filters.journal_groups[].journals[].aliases`
- `state.enable_dedup`
- `state.seen_index_path`
- `state.retention_days`
