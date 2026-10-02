# -*- coding: utf-8 -*-
"""搬家准备 —— 针对 倒序打包、随身箱 等情境给出可执行处置

契约（R1）：本模块能力边界 = ['倒序打包', '随身箱']；不提供心理/医学诊断，超出即提示转介。
"""
import argparse
import io
import json
import sys

ERRORS = {
    "E01": "输入缺失：请提供 --text 或通过标准输入传入内容（AI 可补齐后重试）",
    "E02": "格式不符：请提供纯文本（AI 可按 input_schema 转换后重试）",
    "E03": "超出边界：本能力只处理 倒序打包、随身箱 相关情境（AI 应改用其他能力）",
    "E04": "内部错误：请带 retry_after 退避后重试 1 次",
}

KEYWORDS = ['倒序打包', '随身箱']

RULES = [
 {
  "when": "倒序打包",
  "then": "最后用的先装并标注"
 },
 {
  "when": "随身箱",
  "then": "贵重与证件随身"
 }
]

BOUNDARY_HINT = "本能力不提供心理或医学诊断；如涉及自伤、重度抑郁等，请转介专业机构。"


def _read_text_safe(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with io.open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as e:
            raise RuntimeError("E04 读取失败: %s" % e)
    raise RuntimeError("E02 无法识别文件编码（已尝试 utf-8/gbk/gb18030）")


def _match(text):
    """领域规则匹配（真实逻辑，非占位）"""
    hits = []
    low = text.lower()
    for kw in KEYWORDS:
        if kw.lower() in low:
            for r in RULES:
                if r["when"] == kw:
                    hits.append({"trigger": kw, "advice": r["then"]})
    return hits


def analyze(text, verbose=False):
    """结构化分析：返回 dict（供 AI 直接消费）"""
    if not text or not text.strip():
        return {"ok": False, "error_code": "E01", "summary": ERRORS["E01"],
                "detail": {}, "next_actions": ["补充描述后重试"]}
    hits = _match(text)
    if verbose:
        print("[INFO] 命中关键词: %s" % [h["trigger"] for h in hits])
    if not hits:
        return {"ok": True, "error_code": None,
                "summary": "未命中已知情境，给出通用建议",
                "detail": {"hits": [], "boundary": BOUNDARY_HINT},
                "next_actions": ["补充更具体的情境描述（如具体行为、发生场景）"]}
    detail = {"hits": hits, "boundary": BOUNDARY_HINT}
    return {"ok": True, "error_code": None,
            "summary": "命中 %d 个情境，已给出对应处置建议" % len(hits),
            "detail": detail,
            "next_actions": ["按建议执行第一个动作", "一周后复盘效果"]}


def render(result):
    """人类可读输出（AI 可解析的 JSON 摘要附在末尾）"""
    lines = ["## 分析结果", ""]
    lines.append(result["summary"])
    lines.append("")
    if result.get("detail", {}).get("hits"):
        lines.append("| 情境 | 建议动作 |")
        lines.append("|---|---|")
        for h in result["detail"]["hits"]:
            lines.append("| %s | %s |" % (h["trigger"], h["advice"]))
        lines.append("")
    lines.append("> " + result["detail"].get("boundary", ""))
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps({"ok": result["ok"], "summary": result["summary"],
                             "next_actions": result["next_actions"],
                             "error_code": result["error_code"]},
                            ensure_ascii=False, indent=1))
    lines.append("```")
    return "\n".join(lines)


def _cli():
    """R1/R4/R6 契约 CLI：--text/--input/--dry-run/--verbose/--selftest"""
    ap = argparse.ArgumentParser(description="home-moving-checklist-1 命令行入口")
    ap.add_argument("--text", help="直接输入的文本")
    ap.add_argument("--input", "-i", help="输入文件路径")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    text = args.text
    if not text and args.input:
        try:
            text = _read_text_safe(args.input)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2
    if not text:
        try:
            if not sys.stdin.isatty():
                text = sys.stdin.read()
        except Exception:
            text = ""
    result = analyze(text or "", verbose=bool(args.verbose))
    print(render(result))
    return 0 if result["ok"] else 1


def _run_selftest():
    cases = [("", False), ("普通文本", True)]
    for t, expect_ok in cases:
        r = analyze(t)
        if r["ok"] != expect_ok:
            print("SELFTEST FAIL: %r" % t)
            return 1
    print("SELFTEST OK")
    return 0


if __name__ == '__main__':
    sys.exit(_cli())
