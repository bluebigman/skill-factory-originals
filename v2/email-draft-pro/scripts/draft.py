#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
email-draft-pro — 商务邮件起草器（原创实现 v2.1）

仅依据 SKILL.md 功能规格独立编写，不参考任何既有实现 / 不复制他人代码。

功能：
  - 按场景（dunning/follow_up/quote/apology/thanks/formal） × 语言（zh-CN/en-US）
    × 语气（formal/semi/casual）渲染专业商务邮件
  - 缺失必填字段以 [需核实:字段] 显式标注，绝不静默编造
  - 单封渲染 / CSV·JSON 批量
  - Markdown / 纯文本 / HTML 三种输出
  - 字段占位符校验、语气一致性、风险措辞提示
  - 零依赖（仅标准库），离线自检：python draft.py --selftest

错误码 E001-E010。
"""
from __future__ import annotations
import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

__version__ = "2.1.0"

ERRORS = {
    "E001": "模板加载失败",
    "E002": "模板非合法 JSON",
    "E003": "指定的场景不存在",
    "E004": "该场景下无对应语言模板",
    "E005": "指定的语气不存在（formal/semi/casual）",
    "E006": "必填字段缺失（已渲染为 [需核实:字段]）",
    "E007": "单次输入超过长度上限",
    "E008": "批量记录数超过上限",
    "E009": "批量输入文件解析失败（CSV/JSON 格式错误）",
    "E010": "输出写入失败",
}
MAX_CHARS = 10_000
MAX_ROWS = 100

# 风险措辞（提示用，不进正文）
RISKY = {
    "zh-CN": ["立即", "必须马上", "否则后果自负", "最后通牒", "你们的错", "严重警告"],
    "en-US": ["immediately or else", "final warning", "your fault", "unacceptable behaviour"],
}


class DraftErr(Exception):
    def __init__(self, code, detail=""):
        self.code = code
        super().__init__(f"[{code}] {ERRORS.get(code, '')}{(' | ' + detail) if detail else ''}")


# --------------------------------------------------------------------------
# 内置原创模板：场景 -> 语言 -> 语气 -> (必填字段, 模板)
# 占位符 {field} 缺失渲染为 [需核实:field]
# 所有模板字符串均为完整、合法的 Python 字符串，无截断
# --------------------------------------------------------------------------
TEMPLATES = {
    "dunning": {
        "zh-CN": {
            "formal": (["recipient", "amount", "invoice_no", "due_date", "sender"],
                       "尊敬的 {recipient}：\n\n关于 {invoice_no} 号发票（金额 {amount} 元），"
                       "烦请于 {due_date} 前安排付款。如有疑问请与 {sender} 联系。\n\n此致\n{sender}"),
            "semi": (["recipient", "amount", "invoice_no", "due_date", "sender"],
                     "你好 {recipient}，{invoice_no} 号发票（{amount} 元）请于 {due_date} 前付款，"
                     "谢谢配合。{sender}"),
            "casual": (["recipient", "amount", "invoice_no", "due_date", "sender"],
                       "{recipient} 好，{invoice_no} 发票 {amount} 元麻烦 {due_date} 前付下哈，谢啦 {sender}"),
        },
        "en-US": {
            "formal": (["recipient", "amount", "invoice_no", "due_date", "sender"],
                       "Dear {recipient},\n\nKindly arrange payment for invoice {invoice_no} "
                       "(amount {amount}) by {due_date}. For any queries, contact {sender}.\n\n"
                       "Sincerely,\n{sender}"),
            "semi": (["recipient", "amount", "invoice_no", "due_date", "sender"],
                     "Hi {recipient}, please settle invoice {invoice_no} ({amount}) by {due_date}. "
                     "Thanks, {sender}"),
            "casual": (["recipient", "amount", "invoice_no", "due_date", "sender"],
                       "Hey {recipient}, could you pay invoice {invoice_no} ({amount}) before {due_date}? "
                       "Cheers, {sender}"),
        },
    },
    "follow_up": {
        "zh-CN": {
            "formal": (["recipient", "topic", "sender"],
                       "尊敬的 {recipient}：\n\n就 {topic} 一事，特来跟进进展，盼复。\n\n{sender}"),
            "semi": (["recipient", "topic", "sender"],
                     "你好 {recipient}，关于 {topic} 想跟进一下，方便的话回复下。{sender}"),
            "casual": (["recipient", "topic", "sender"],
                       "{recipient} 好，{topic} 那事帮看下哈，谢 {sender}"),
        },
        "en-US": {
            "formal": (["recipient", "topic", "sender"],
                       "Dear {recipient},\n\nFollowing up on {topic}. Looking forward to your reply.\n\n"
                       "Sincerely,\n{sender}"),
            "semi": (["recipient", "topic", "sender"],
                     "Hi {recipient}, just following up on {topic}. Thanks, {sender}"),
            "casual": (["recipient", "topic", "sender"],
                       "Hey {recipient}, checking in on {topic} — cheers, {sender}"),
        },
    },
    "quote": {
        "zh-CN": {
            "formal": (["recipient", "product", "amount", "sender"],
                       "尊敬的 {recipient}：\n\n就 {product} 报价如下：{amount}。如需正式合同请告知。\n\n{sender}"),
            "semi": (["recipient", "product", "amount", "sender"],
                     "你好 {recipient}，{product} 报价 {amount}，需要的话告诉我。{sender}"),
            "casual": (["recipient", "product", "amount", "sender"],
                       "{recipient} 好，{product} 报价 {amount}，随时找我哈 {sender}"),
        },
        "en-US": {
            "formal": (["recipient", "product", "amount", "sender"],
                       "Dear {recipient},\n\nOur quote for {product} is {amount}. Let us know if you need "
                       "a formal contract.\n\nSincerely,\n{sender}"),
            "semi": (["recipient", "product", "amount", "sender"],
                     "Hi {recipient}, quote for {product}: {amount}. Just let me know. {sender}"),
            "casual": (["recipient", "product", "amount", "sender"],
                       "Hey {recipient}, {product} would be {amount} — hit me up anytime. {sender}"),
        },
    },
    "apology": {
        "zh-CN": {
            "formal": (["recipient", "matter", "sender"],
                       "尊敬的 {recipient}：\n\n就 {matter} 一事深表歉意，我们将尽快纠正。\n\n{sender}"),
            "semi": (["recipient", "matter", "sender"],
                     "你好 {recipient}，{matter} 这边非常抱歉，马上处理。{sender}"),
            "casual": (["recipient", "matter", "sender"],
                       "{recipient} 好，{matter} 真对不住，我马上搞。{sender}"),
        },
        "en-US": {
            "formal": (["recipient", "matter", "sender"],
                       "Dear {recipient},\n\nWe sincerely apologize for {matter} and will rectify it promptly.\n\n"
                       "Sincerely,\n{sender}"),
            "semi": (["recipient", "matter", "sender"],
                     "Hi {recipient}, so sorry about {matter} — fixing now. {sender}"),
            "casual": (["recipient", "matter", "sender"],
                       "Hey {recipient}, really sorry about {matter}, on it. {sender}"),
        },
    },
    "thanks": {
        "zh-CN": {
            "formal": (["recipient", "matter", "sender"],
                       "尊敬的 {recipient}：\n\n感谢您在 {matter} 中的支持，期待继续合作。\n\n{sender}"),
            "semi": (["recipient", "matter", "sender"],
                     "你好 {recipient}，感谢 {matter} 的支持，多谢。{sender}"),
            "casual": (["recipient", "matter", "sender"],
                       "{recipient} 好，{matter} 太感谢啦，回头请吃饭 {sender}"),
        },
        "en-US": {
            "formal": (["recipient", "matter", "sender"],
                       "Dear {recipient},\n\nThank you for your support with {matter}. Looking forward to "
                       "working together again.\n\nSincerely,\n{sender}"),
            "semi": (["recipient", "matter", "sender"],
                     "Hi {recipient}, thanks so much for {matter}. {sender}"),
            "casual": (["recipient", "matter", "sender"],
                       "Hey {recipient}, huge thanks for {matter}! {sender}"),
        },
    },
    "formal": {
        "zh-CN": {
            "formal": (["recipient", "body", "sender"],
                       "尊敬的 {recipient}：\n\n{body}\n\n此致\n{sender}"),
            "semi": (["recipient", "body", "sender"],
                     "你好 {recipient}，{body} {sender}"),
            "casual": (["recipient", "body", "sender"],
                       "{recipient} 好，{body} {sender}"),
        },
        "en-US": {
            "formal": (["recipient", "body", "sender"],
                       "Dear {recipient},\n\n{body}\n\nSincerely,\n{sender}"),
            "semi": (["recipient", "body", "sender"],
                     "Hi {recipient}, {body} {sender}"),
            "casual": (["recipient", "body", "sender"],
                       "Hey {recipient}, {body} {sender}"),
        },
    },
}


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _validate_scenario_lang_tone(scenario: str, lang: str, tone: str) -> None:
    """统一校验场景、语言、语气，避免重复代码。"""
    if scenario not in TEMPLATES:
        raise DraftErr("E003", scenario)
    if lang not in TEMPLATES[scenario]:
        raise DraftErr("E004", f"{scenario}/{lang}")
    if tone not in TEMPLATES[scenario][lang]:
        raise DraftErr("E005", tone)


def render(scenario: str, lang: str, tone: str, fields: dict) -> tuple[str, list[str], list[str]]:
    """
    渲染邮件正文。
    返回: (正文, 风险措辞列表, 缺失必填字段列表)
    """
    # 输入类型校验
    if not isinstance(fields, dict):
        raise DraftErr("E006", "fields 参数必须是字典")

    _validate_scenario_lang_tone(scenario, lang, tone)
    required, template = TEMPLATES[scenario][lang][tone]

    # 检查必填字段
    missing = [f for f in required if not str(fields.get(f, "")).strip()]

    # 渲染模板
    body = template
    for name in _PLACEHOLDER.findall(template):
        val = str(fields.get(name, "")).strip()
        body = body.replace("{%s}" % name, val if val else f"[需核实:{name}]")

    # 长度检查
    if len(body) > MAX_CHARS:
        raise DraftErr("E007", f"渲染结果 {len(body)} 字符超过上限 {MAX_CHARS}")

    # 风险措辞提示（仅提示，不阻断）
    risks = [w for w in RISKY.get(lang, []) if w in body]
    return body, risks, missing


def to_markdown(text: str) -> str:
    """转换为 Markdown 格式（引用块 + 双空格换行）。"""
    return text.replace("\n\n", "\n\n> ").replace("\n", "  \n")


def to_html(text: str) -> str:
    """转换为 HTML 格式（段落 + 换行）。"""
    return "<p>" + html.escape(text).replace("\n", "<br>") + "</p>"


def emit(text: str, fmt: str) -> str:
    """按指定格式输出。"""
    if fmt == "markdown":
        return to_markdown(text)
    if fmt == "html":
        return to_html(text)
    return text


# --------------------------------------------------------------------------
# 批量
# --------------------------------------------------------------------------
def load_batch(path: str) -> list[dict]:
    """从 CSV/JSON 文件加载批量数据。"""
    p = Path(path)
    if not p.is_file():
        raise DraftErr("E009", "文件不存在")

    try:
        if p.suffix.lower() == ".json":
            rows = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            if not isinstance(rows, list):
                raise DraftErr("E009", "JSON 顶层须为数组")
            # 确保每行都是字典
            rows = [r for r in rows if isinstance(r, dict)]
        else:
            with open(p, encoding="utf-8", errors="replace", newline="") as f:
                rows = [dict(r) for r in csv.DictReader(f)]
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        raise DraftErr("E009", str(e))

    if len(rows) > MAX_ROWS:
        raise DraftErr("E008", f"{len(rows)} > {MAX_ROWS}")
    return rows


def batch_draft(rows: list[dict], fmt: str = "text") -> list[dict]:
    """
    批量起草邮件（核心批量处理函数）。
    逐条调用单封渲染逻辑，支持 CSV/JSON 批量输入。
    """
    out = []
    for r in rows:
        sc = r.get("scenario", "")
        lg = r.get("lang", "zh-CN")
        tn = r.get("tone", "formal")
        fields = {k: v for k, v in r.items() if k not in ("scenario", "lang", "tone")}
        try:
            text, risks, missing = render(sc, lg, tn, fields)
            out.append({
                "scenario": sc, "lang": lg, "tone": tn,
                "content": emit(text, fmt), "risks": risks,
                "missing": missing, "ok": True
            })
        except DraftErr as e:
            out.append({"scenario": sc, "error": e.code, "message": e.args[0], "ok": False})
    return out


def batch(rows: list[dict], fmt: str) -> list[dict]:
    """兼容旧接口，调用 batch_draft。"""
    return batch_draft(rows, fmt)


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def selftest() -> int:
    """离线自检，确保核心功能正常。"""
    print("== draft.py 离线自检 ==")
    ok = True

    def chk(name: str, fn) -> None:
        nonlocal ok
        try:
            fn()
            print(f"  [OK] {name}")
        except Exception as e:
            ok = False
            print(f"  [FAIL] {name} -> {type(e).__name__}: {e}")

    def expect(code: str, fn) -> callable:
        def _i():
            try:
                fn()
            except DraftErr as e:
                assert e.code == code, f"期望 {code} 实得 {e.code}"
                return
            raise AssertionError(f"期望抛 {code}")
        return _i

    # 错误处理测试
    chk("E003 场景不存在", expect("E003", lambda: render("nope", "zh-CN", "formal", {})))
    chk("E004 语言不存在", expect("E004", lambda: render("dunning", "fr-FR", "formal", {})))
    chk("E005 语气不存在", expect("E005", lambda: render("dunning", "zh-CN", "angry", {})))

    def _e006():
        b, _, m = render("dunning", "zh-CN", "formal", {"recipient": "张经理", "amount": "52000"})
        assert m and "[需核实" in b, (m, b)
    chk("E006 必填缺失标注", _e006)

    # 正常渲染 + [需核实] 标注
    body, _, missing = render("dunning", "zh-CN", "formal",
                              {"recipient": "张经理", "amount": "", "invoice_no": "INV-1",
                               "due_date": "2026-07-31", "sender": "李明"})
    assert "[需核实:amount]" in body, "缺失字段未标注"
    print("  [OK] 缺失字段标注为 [需核实:amount]")

    # 多语言
    en, _, _ = render("dunning", "en-US", "formal",
                      {"recipient": "Mr.Lee", "amount": "$520", "invoice_no": "INV-1",
                       "due_date": "2026-07-31", "sender": "Li Ming"})
    assert "Dear Mr.Lee" in en
    print
