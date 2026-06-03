"""
需求文档归一化器 (Document Normalizer)
======================================
把混合格式文档批量转成 LLM 友好的 Markdown。

策略：
  1) 本地 MarkItDown 优先（免费、快）
  2) 启发式质量评估（字符数 / 文本密度 / 异常）
  3) 不达标或异常时，回退 Azure Document Intelligence（扫描件/复杂表格更强）

认证（Azure DI 回退）：
  - 优先 Managed Identity / DefaultAzureCredential（VM、容器、本地 az login 均可）
  - 兜底 API key（环境变量 DOCINTEL_KEY）

⚠️ MarkItDown 迭代较快，docintel_endpoint / llm_client 等入参名可能随版本变化。
   开发时请 `pip show markitdown` 确认版本，并用 help(MarkItDown) 核实签名。
"""
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---- 配置 ----------------------------------------------------------------

SUPPORTED_EXT = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".html", ".htm",
                 ".csv", ".json", ".xml", ".epub", ".png", ".jpg", ".jpeg"}

# 质量阈值：低于这些值判定本地转换"可能不达标"，触发 Azure DI 回退
MIN_CHARS = 200            # Markdown 文本太短 → 可能是扫描件/解析失败
MIN_ALNUM_RATIO = 0.50     # 字母数字占比太低 → 可能是乱码/纯符号

DOCINTEL_ENDPOINT = os.getenv("DOCINTEL_ENDPOINT")  # https://<res>.cognitiveservices.azure.com/
DOCINTEL_KEY = os.getenv("DOCINTEL_KEY")            # 可选；不设则用 Managed Identity

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("doc-normalizer")


# ---- 数据结构 ------------------------------------------------------------

@dataclass
class ConvertResult:
    src: Path
    markdown: str = ""
    engine: str = ""          # "local" | "azure-di" | "failed"
    ok: bool = False
    reason: str = ""          # 失败或回退原因


# ---- 质量评估 ------------------------------------------------------------

def assess_quality(text: str) -> tuple[bool, str]:
    """启发式判断本地转换结果是否够好。返回 (是否达标, 原因)。"""
    if not text or len(text.strip()) < MIN_CHARS:
        return False, f"文本过短 (<{MIN_CHARS} 字符)"
    alnum = sum(c.isalnum() for c in text)
    ratio = alnum / max(len(text), 1)
    if ratio < MIN_ALNUM_RATIO:
        return False, f"文本密度过低 (alnum ratio={ratio:.2f})"
    return True, "ok"


# ---- 引擎：本地 MarkItDown ----------------------------------------------

def convert_local(path: Path) -> ConvertResult:
    try:
        from markitdown import MarkItDown
    except ImportError:
        return ConvertResult(path, engine="failed",
                             reason="未安装 markitdown，请 pip install 'markitdown[all]'")
    try:
        md = MarkItDown()
        text = md.convert(str(path)).text_content or ""
        return ConvertResult(path, markdown=text, engine="local", ok=True)
    except Exception as e:  # noqa: BLE001  fail loud
        return ConvertResult(path, engine="failed", reason=f"local error: {e}")


# ---- 引擎：Azure Document Intelligence 回退 ------------------------------

def convert_azure_di(path: Path) -> ConvertResult:
    """
    用 MarkItDown 的 Azure Document Intelligence 集成做高质量转换。
    认证优先级：DOCINTEL_KEY > DefaultAzureCredential(Managed Identity / az login)。
    """
    if not DOCINTEL_ENDPOINT:
        return ConvertResult(path, engine="failed",
                             reason="未配置 DOCINTEL_ENDPOINT，无法回退 Azure DI")
    try:
        from markitdown import MarkItDown
    except ImportError:
        return ConvertResult(path, engine="failed", reason="未安装 markitdown")

    try:
        kwargs = {"docintel_endpoint": DOCINTEL_ENDPOINT}
        if DOCINTEL_KEY:
            # key 认证（部分版本参数名可能不同，详见注意事项）
            kwargs["docintel_credential"] = DOCINTEL_KEY
        else:
            # Managed Identity / az login —— 推荐，无明文密钥
            from azure.identity import DefaultAzureCredential
            kwargs["docintel_credential"] = DefaultAzureCredential()

        md = MarkItDown(**kwargs)
        text = md.convert(str(path)).text_content or ""
        ok, reason = assess_quality(text)
        return ConvertResult(path, markdown=text, engine="azure-di",
                             ok=ok, reason="" if ok else f"DI 结果仍不达标: {reason}")
    except Exception as e:  # noqa: BLE001  fail loud
        return ConvertResult(path, engine="failed", reason=f"azure-di error: {e}")


# ---- 编排：本地优先 + 回退 ----------------------------------------------

def normalize_one(path: Path, allow_fallback: bool = True) -> ConvertResult:
    res = convert_local(path)

    if res.ok:
        good, reason = assess_quality(res.markdown)
        if good:
            return res
        log.warning("本地结果不达标 [%s]: %s", path.name, reason)
        res.reason = reason
    else:
        log.warning("本地转换失败 [%s]: %s", path.name, res.reason)

    if allow_fallback and DOCINTEL_ENDPOINT:
        log.info("→ 回退 Azure Document Intelligence: %s", path.name)
        di = convert_azure_di(path)
        if di.ok:
            return di
        log.error("Azure DI 回退仍失败 [%s]: %s", path.name, di.reason)
        return di

    # 本地勉强有内容但没回退条件：返回本地结果并标注
    if res.markdown:
        res.ok = True
        res.reason = f"本地结果质量存疑且无回退条件: {res.reason}"
        return res
    return res


def normalize_dir(src: Path, out: Path, allow_fallback: bool = True) -> list[ConvertResult]:
    out.mkdir(parents=True, exist_ok=True)
    results: list[ConvertResult] = []
    files = [f for f in sorted(src.iterdir())
             if f.is_file() and f.suffix.lower() in SUPPORTED_EXT]

    if not files:
        log.warning("目录中没有支持的文件: %s", src)
        return results

    for f in files:
        r = normalize_one(f, allow_fallback=allow_fallback)
        results.append(r)
        if r.markdown:
            (out / f"{f.stem}.md").write_text(r.markdown, encoding="utf-8")
        flag = "✓" if r.ok else "✗"
        log.info("%s [%s] %s%s", flag, r.engine, f.name,
                 f"  ({r.reason})" if r.reason else "")
    return results


# ---- CLI -----------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="需求文档归一化器：混合格式 → LLM 友好 Markdown")
    p.add_argument("src", help="输入文件或目录")
    p.add_argument("-o", "--out", default="./md_out", help="输出目录 (默认 ./md_out)")
    p.add_argument("--no-fallback", action="store_true", help="禁用 Azure DI 回退")
    args = p.parse_args(argv)

    src = Path(args.src)
    out = Path(args.out)
    allow = not args.no_fallback

    if not src.exists():
        log.error("路径不存在: %s", src)
        return 2

    if src.is_file():
        out.mkdir(parents=True, exist_ok=True)
        r = normalize_one(src, allow_fallback=allow)
        if r.markdown:
            (out / f"{src.stem}.md").write_text(r.markdown, encoding="utf-8")
        log.info("%s [%s] %s %s", "✓" if r.ok else "✗", r.engine, src.name, r.reason)
        return 0 if r.ok else 1

    results = normalize_dir(src, out, allow_fallback=allow)
    ok_n = sum(1 for r in results if r.ok)
    di_n = sum(1 for r in results if r.engine == "azure-di")
    log.info("完成：%d/%d 成功，其中 %d 个走了 Azure DI 回退 → %s",
             ok_n, len(results), di_n, out)
    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
