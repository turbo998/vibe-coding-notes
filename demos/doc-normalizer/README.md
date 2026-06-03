# 需求文档归一化器 (Document Normalizer)

把一批**混合格式文档**（PDF / Word / PPT / Excel / 图片 / HTML…）批量转成 **LLM 友好的 Markdown**，直接喂给 Copilot / 大模型生成需求规格、入 RAG 库。

## 核心策略

```
混合格式文档
     │
     ▼
┌─────────────────────┐
│ 本地 MarkItDown      │  免费、快
└──────────┬──────────┘
           │ 质量启发式评估
           │ (字符数 / 文本密度 / 异常)
     不达标 │ 或解析失败
           ▼
┌─────────────────────┐
│ Azure Document Intel.│  扫描件 / 复杂表格更强
│ (Managed Identity)   │
└──────────┬──────────┘
           ▼
      结构化 Markdown  → LLM / RAG
```

- **本地优先**：MarkItDown 处理结构清晰的文档，零成本。
- **智能回退**：仅当本地结果"过短 / 文本密度过低 / 抛异常"时，才调用 Azure DI——把付费调用花在刀刃上（扫描件、多栏、复杂表格）。
- **认证安全**：Azure DI 默认走 `DefaultAzureCredential`（Managed Identity / `az login`），不硬编码密钥；也支持 key 兜底。

## 安装

```bash
cd demos/doc-normalizer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 使用

### 纯本地（不回退）

```bash
python normalizer.py ./docs -o ./md_out --no-fallback
```

### 启用 Azure DI 回退

```bash
# 推荐：Managed Identity / az login，无明文密钥
az login
export DOCINTEL_ENDPOINT="https://<your-resource>.cognitiveservices.azure.com/"
python normalizer.py ./docs -o ./md_out

# 或 key 兜底
export DOCINTEL_ENDPOINT="https://<your-resource>.cognitiveservices.azure.com/"
export DOCINTEL_KEY="<your-key>"
python normalizer.py ./docs -o ./md_out
```

### 单文件

```bash
python normalizer.py ./spec.pdf -o ./md_out
```

## 输出

- 每个输入文件 → `md_out/<同名>.md`
- 日志标注每个文件走的引擎：`[local]` / `[azure-di]` / `[failed]`，并打印回退原因。

## 质量阈值（可调）

在 `normalizer.py` 顶部：

| 参数 | 默认 | 含义 |
|---|---|---|
| `MIN_CHARS` | 200 | Markdown 短于此 → 疑似扫描件/失败，触发回退 |
| `MIN_ALNUM_RATIO` | 0.50 | 字母数字占比低于此 → 疑似乱码，触发回退 |

## Azure 角色 / 权限

调用 Document Intelligence 时，给 Managed Identity / 用户分配最小权限角色：

- **Cognitive Services User**（数据面调用）

> 资源所在 RG 的 endpoint 形如 `https://<resource>.cognitiveservices.azure.com/`。

## ⚠️ 注意事项 / 待验证

- MarkItDown 迭代快，`docintel_endpoint` / `docintel_credential` / `llm_client` 等入参名可能随版本变化。开发前 `pip show markitdown` 确认版本，并 `help(MarkItDown)` 核实签名——本骨架按常见用法编写，**未在所有版本实测**。
- 质量启发式是简单规则，生产环境建议结合：页数、表格数、置信度（若 DI 返回）等更细指标。
- 回退判定目前只看本地结果文本；如需"本地成功但质量明显差于 DI"的对比择优，可扩展 `normalize_one`。
