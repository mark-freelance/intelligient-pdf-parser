# Sentiment based PDF Parser

## Background

目标是在 444 个长篇论文里挖掘某种语义的表格数据。

![img.png](assets/target-table.png)

## Insights

比较有意思、有启发的点：

- 调研与了解了 claude、gemini、kimi、千问等模型对 pdf 多模态的理解能力与差异
- 研究学习了 sentence-transformer 等小模型的语义匹配算法、基于 alembic + sqlmodel 的数据库迁移技术、基于 pymupdf 的 pdf 跨页表格处理技术
- 实现了基于 rich 的狂拽酷炫吊炸天的实时多线程动态更新监控
- 深刻领悟了基于数据库状态控制实现增量开发、异步开发、减而治之的思想与方法论
- 大致了解了某教育领域科研论文的核心研究目标、方法论与风格差异

## Solutions

- 一开始尝试地看起来很酷炫但实际低可用的高并发解决方案：[v1_plain](src/v1_plain)

- 基于大模型（效果确实好）但并发不够以及太贵以至于只适合某些场景的解决方案：[v2_llm](src/v2_llm)

- 【推荐：☆☆☆☆☆】基于数据库控制 + 人工筛查 + 傻瓜单进程的稳健解决方案：[v3_stable](src/v3_stable)

## Other References

- [analysis.md](../../docs/analysis.md)
- [notes.md](../../docs/notes.md)