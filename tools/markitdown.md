# MarkItDown 技术笔记

> 微软开源的轻量级 Python 文档转换工具，把各种格式统一转成 **对 LLM 友好的 Markdown**。
> 系列：每天了解一个 vibe coding 框架
> 来源：知乎 @dreaaim · 整理日期 2026-06-03

---

## 1. 一句话定位

把 PDF / Word / PPT / Excel / 图片 / 音频 / HTML / CSV / JSON / XML / EPub / ZIP **转成保留结构的 Markdown**，专为喂给大模型设计。

**与普通转换器的本质区别**：普通转换器只关注"视觉还原"，会丢掉标题层级、表格关系、列表结构、链接引用——而这些恰恰是 LLM 理解文档最需要的结构信息。MarkItDown 保留这些结构，输出适合 LLM 分析的结构化文本。

- GitHub: [microsoft/markitdown](https://github.com/microsoft/markitdown)
- 许可证: MIT
- 要求: Python 3.10+

---

## 2. 解决的痛点

vibe coding / AI 文档分析时，最痛的往往不是写代码，而是**描述需求**：

- 业务/产品给的需求文档通常是 PDF、PPT、Excel，而不是整理好的 Markdown
- 直接转换会丢失结构 → AI 理解出现偏差 → 关键信息遗漏
- 一批混合格式文档（PDF 设计 + Excel 数据 + PPT 汇报）需要逐个手动转换，低效且不可靠

MarkItDown 作为"非文本技术文档 ↔ LLM 分析"之间的桥梁，让 AI 能像读普通文本一样理解各类格式材料。

---

## 3. 支持的格式

| 类别 | 格式 |
|---|---|
| 文档 | PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx/.xls) |
| 文本/数据 | HTML, CSV, JSON, XML |
| 媒体 | 图片 (EXIF + OCR + LLM 描述), 音频 (EXIF + 语音转写) |
| 电子书 | EPub |
| 归档 | ZIP（遍历内部文件） |
| 其他 | YouTube URL、Outlook .msg 等 |

---

## 4. 安装

```bash
# 全功能（推荐，装上所有可选依赖）
pip install 'markitdown[all]'

# 按需安装（更轻量）
pip install 'markitdown[pdf,docx,pptx,xlsx]'

# 仅核心
pip install markitdown
```

> 建议在虚拟环境中安装：`python -m venv .venv && source .venv/bin/activate`

---

## 5. 基本用法

### 5.1 命令行

```bash
markitdown input.pdf > output.md
markitdown input.pptx -o output.md
cat input.docx | markitdown   # 也支持管道
```

### 5.2 Python API

```python
from markitdown import MarkItDown

md = MarkItDown()
result = md.convert("path/to/file.pdf")
print(result.text_content)   # 转换后的 Markdown 字符串
```

### 5.3 批量转换（混合格式目录）

```python
from pathlib import Path
from markitdown import MarkItDown

md = MarkItDown()
src = Path("./docs")
out = Path("./md_out")
out.mkdir(exist_ok=True)

for f in src.iterdir():
    if f.suffix.lower() in {".pdf", ".docx", ".pptx", ".xlsx", ".html"}:
        try:
            text = md.convert(str(f)).text_content
            (out / f"{f.stem}.md").write_text(text, encoding="utf-8")
            print(f"✓ {f.name}")
        except Exception as e:
            print(f"✗ {f.name}: {e}")
```

---

## 6. 进阶能力（demo 重点）

### 6.1 LLM 驱动的图片描述

传入一个支持视觉的模型 client，MarkItDown 会为图片生成自然语言描述并写入 Markdown。

```python
from markitdown import MarkItDown
from openai import OpenAI   # 或 Azure OpenAI client

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")
result = md.convert("slide_with_charts.png")
print(result.text_content)   # 含 AI 生成的图片描述
```

### 6.2 Azure 云端增强引擎（复杂文档 / 扫描件）

本地解析对扫描件、多栏排版、复杂表格效果有限时，可接 Azure 服务提升质量：

- **Azure Document Intelligence**（原 Form Recognizer）
- **Azure Content Understanding**

```python
from markitdown import MarkItDown

md = MarkItDown(docintel_endpoint="https://<resource>.cognitiveservices.azure.com/")
result = md.convert("scanned_contract.pdf")
print(result.text_content)
```

> 认证建议用 Managed Identity（VM/容器场景），避免硬编码 key。参考最小权限角色：Cognitive Services User。

### 6.3 插件生态

- `markitdown-ocr` — 给 PDF / Office 文档中的**内嵌图片**加 OCR 能力
- 可通过插件机制扩展自定义格式转换器

```bash
pip install markitdown-ocr
markitdown --use-plugins input.pdf > output.md
```

---

## 7. SA 视角 / 商业化钩子

| 维度 | 说明 |
|---|---|
| 本地版 | 免费、轻量，覆盖大部分结构清晰的文档 |
| **Azure 上钩点** | 扫描件 / 复杂表格 / 多栏 PDF → 接 **Azure Document Intelligence** 是天然付费转化点 |
| RAG 场景 | 可作为 **文档预处理入口**（ingestion 前的格式归一化层） |
| Agent 场景 | 让 coding agent 直接消费 PDF/PPT 需求，减少人工整理 |

---

## 8. Demo 设想（后续开发）

1. **需求文档归一化器**：上传混合格式 → 批量转 Markdown → 直接喂给 Copilot / LLM 生成需求规格
2. **RAG ingestion 管线**：MarkItDown（本地）→ 失败/低质回退 Azure DI → 切块 → 向量化入库
3. **多模态 PPT 分析**：MarkItDown + LLM 图片描述 → 把图表型 PPT 转成可检索文本

```
                    ┌──────────────────────┐
  混合格式文档  ───▶ │     MarkItDown        │
  (PDF/PPT/XLSX)    │  结构保留 Markdown 化  │
                    └──────────┬───────────┘
                               │ 复杂/扫描件回退
                               ▼
                    ┌──────────────────────┐
                    │ Azure Document Intel. │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Chunk + Embedding    │ ──▶ Vector DB / LLM
                    └──────────────────────┘
```

---

## 9. 注意事项 / 待验证

> ⚠️ 以下为基于文档与常见用法的整理，**实际 API 命名与参数请在开发前 `pip install` 后用 `help()` 核实**（库迭代较快）：
> - `docintel_endpoint` 参数名、`llm_client`/`llm_model` 入参在不同版本可能有差异
> - `[all]` extra 包含的依赖列表以官方 `pyproject.toml` 为准
> - 插件命令 `--use-plugins` 行为按已装插件而定

---

## 参考

- GitHub: https://github.com/microsoft/markitdown
- Azure Document Intelligence: https://learn.microsoft.com/azure/ai-services/document-intelligence/
- 原文：知乎 @dreaaim「每天了解一个 vibe coding 框架——MarkItDown」
