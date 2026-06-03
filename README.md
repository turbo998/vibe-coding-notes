# vibe-coding-notes

每天了解一个 vibe coding 框架/工具的技术笔记。每篇笔记面向"后续开发 demo"，包含定位、安装、基本用法、进阶能力、SA 商业化视角与 demo 设想。

## 目录

| 工具 | 笔记 | 一句话 |
|---|---|---|
| MarkItDown | [tools/markitdown.md](tools/markitdown.md) | 微软开源，把 PDF/PPT/Word/Excel/图片 等转成 LLM 友好的结构化 Markdown |

## Demos

| Demo | 说明 |
|---|---|
| [需求文档归一化器](demos/doc-normalizer/) | 混合格式文档批量转 Markdown，本地 MarkItDown 优先 + Azure Document Intelligence 智能回退 |

## 约定

- 每个工具一篇 `tools/<name>.md`
- 结构：定位 → 痛点 → 格式/能力 → 安装 → 用法 → 进阶 → SA 视角 → demo 设想 → 注意事项
- 凡未实测的 API/参数，统一在「注意事项」标注待验证
