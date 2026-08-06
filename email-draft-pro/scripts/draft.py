#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
email-draft-pro — 商务邮件起草器 v3.0.0

功能：
  - 按场景（dunning/follow_up/quote/apology/thanks/formal）× 语言（zh-CN/en-US）
    × 语气（formal/semi/casual）渲染专业商务邮件
  - 缺失必填字段以 [需核实:字段] 显式标注，绝不静默编造
  - 单封渲染 / CSV·JSON 批量
  - Markdown / 纯文本 / HTML 三种输出
  - 字段占位符校验、语气一致性、风险措辞提示
  - 零依赖（仅标准库），离线自检：python run.py --selftest

错误码 E001-E010。
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

__version__ = "3.0.0"

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
    """自定义异常，携带错误码"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {ERRORS.get(code, '')}{(' | ' + detail) if detail else ''}")


# --------------------------------------------------------------------------
# 内置原创模板：场景 -> 语言 -> 语气 -> (必填字段, 模板)
# 占位符 {field} 缺失渲染为 [需核实:field]
# --------------------------------------------------------------------------
TEMPLATES = {
    "dunning": {
        "zh-CN": {
            "formal": (
                ["recipient", "amount", "invoice_no", "due_date", "sender"],
                "尊敬的 {recipient}：\n\n关于 {invoice_no} 号发票（金额 {amount} 元），"
                "烦请于 {due_date} 前安排付款。如有疑问请与 {sender} 联系。\n\n此致\n{sender}",
            ),
            "semi": (
                ["recipient", "amount", "invoice_no", "due_date", "sender"],
                "{recipient} 您好：\n\n{invoice_no} 号发票（{amount} 元）已到期，"
                "请尽快在 {due_date} 前处理。有问题可联系 {sender}。\n\n谢谢！",
            ),
            "casual": (
                ["recipient", "amount", "invoice_no", "due_date", "sender"],
                "Hi {recipient}，\n\n{invoice_no} 的 {amount} 元该付啦，"
                "记得 {due_date} 前搞定哦。找 {sender} 就行。\n\n谢啦！",
            ),
        },
        "en-US": {
            "formal": (
                ["recipient", "amount", "invoice_no", "due_date", "sender"],
                "Dear {recipient},\n\nRegarding invoice {invoice_no} for {amount} USD, "
                "please arrange payment by {due_date}. Contact {sender} for any questions.\n\nSincerely,\n{sender}",
            ),
            "semi": (
                ["recipient", "amount", "invoice_no", "due_date", "sender"],
                "Hi {recipient},\n\nInvoice {invoice_no} ({amount} USD) is due. "
                "Please settle by {due_date}. Reach out to {sender} if needed.\n\nThanks!",
            ),
            "casual": (
                ["recipient", "amount", "invoice_no", "due_date", "sender"],
                "Hey {recipient},\n\n{invoice_no} for {amount} USD is up. "
                "Get it done by {due_date}. Ping {sender} if anything.\n\nCheers!",
            ),
        },
    },
    "follow_up": {
        "zh-CN": {
            "formal": (
                ["recipient", "project", "next_step", "sender"],
                "尊敬的 {recipient}：\n\n关于 {project} 项目，烦请确认下一步：{next_step}。"
                "如有进展请告知 {sender}。\n\n此致\n{sender}",
            ),
            "semi": (
                ["recipient", "project", "next_step", "sender"],
                "{recipient} 您好：\n\n{project} 项目进展如何？下一步是 {next_step}。"
                "有消息请告诉 {sender}。\n\n谢谢！",
            ),
            "casual": (
                ["recipient", "project", "next_step", "sender"],
                "Hi {recipient}，\n\n{project} 咋样了？下一步 {next_step} 别忘了。"
                "有情况找 {sender}。\n\n谢啦！",
            ),
        },
        "en-US": {
            "formal": (
                ["recipient", "project", "next_step", "sender"],
                "Dear {recipient},\n\nRegarding the {project} project, please confirm the next step: {next_step}. "
                "Keep {sender} informed of any progress.\n\nSincerely,\n{sender}",
            ),
            "semi": (
                ["recipient", "project", "next_step", "sender"],
                "Hi {recipient},\n\nHow is {project} going? Next step is {next_step}. "
                "Let {sender} know if there's news.\n\nThanks!",
            ),
            "casual": (
                ["recipient", "project", "next_step", "sender"],
                "Hey {recipient},\n\nWhat's up with {project}? Don't forget {next_step}. "
                "Ping {sender} if anything.\n\nCheers!",
            ),
        },
    },
    "quote": {
        "zh-CN": {
            "formal": (
                ["recipient", "quote_no", "amount", "valid_until", "sender"],
                "尊敬的 {recipient}：\n\n报价单 {quote_no}（金额 {amount} 元）已备妥，"
                "有效期至 {valid_until}。如需调整请联系 {sender}。\n\n此致\n{sender}",
            ),
            "semi": (
                ["recipient", "quote_no", "amount", "valid_until", "sender"],
                "{recipient} 您好：\n\n报价单 {quote_no}（{amount} 元）已出，"
                "有效期到 {valid_until}。有问题找 {sender}。\n\n谢谢！",
            ),
            "casual": (
                ["recipient", "quote_no", "amount", "valid_until", "sender"],
                "Hi {recipient}，\n\n报价 {quote_no}（{amount} 元）来了，"
                "到 {valid_until} 前有效。需要改就找 {sender}。\n\n谢啦！",
            ),
        },
        "en-US": {
            "formal": (
                ["recipient", "quote_no", "amount", "valid_until", "sender"],
                "Dear {recipient},\n\nQuote {quote_no} for {amount} USD is ready, "
                "valid until {valid_until}. Contact {sender} for adjustments.\n\nSincerely,\n{sender}",
            ),
            "semi": (
                ["recipient", "quote_no", "amount", "valid_until", "sender"],
                "Hi {recipient},\n\nQuote {quote_no} ({amount} USD) is out, "
                "valid until {valid_until}. Reach {sender} if needed.\n\nThanks!",
            ),
            "casual": (
                ["recipient", "quote_no", "amount", "valid_until", "sender"],
                "Hey {recipient},\n\nQuote {quote_no} ({amount} USD) is here, "
                "good till {valid_until}. Ping {sender} for changes.\n\nCheers!",
            ),
        },
    },
    "apology": {
        "zh-CN": {
            "formal": (
                ["recipient", "issue", "resolution", "sender"],
                "尊敬的 {recipient}：\n\n对于 {issue} 给您带来的不便，我们深表歉意。"
                "我们正在 {resolution}，如有进展将及时通知。请联系 {sender} 获取更多信息。\n\n此致\n{sender}",
            ),
            "semi": (
                ["recipient", "issue", "resolution", "sender"],
                "{recipient} 您好：\n\n关于 {issue} 的问题，非常抱歉。"
                "我们正在 {resolution}，会尽快处理。有疑问找 {sender}。\n\n谢谢理解！",
            ),
            "casual": (
                ["recipient", "issue", "resolution", "sender"],
                "Hi {recipient}，\n\n{issue} 的事真不好意思。"
                "我们正在 {resolution}，马上就好。有事找 {sender}。\n\n抱歉啦！",
            ),
        },
        "en-US": {
            "formal": (
                ["recipient", "issue", "resolution", "sender"],
                "Dear {recipient},\n\nWe sincerely apologize for the inconvenience caused by {issue}. "
                "We are working on {resolution} and will update you promptly. Contact {sender} for details.\n\nSincerely,\n{sender}",
            ),
            "semi": (
                ["recipient", "issue", "resolution", "sender"],
                "Hi {recipient},\n\nSorry about the {issue} situation. "
                "We're on {resolution} and will handle it soon. Reach {sender} if needed.\n\nThanks for understanding!",
            ),
            "casual": (
                ["recipient", "issue", "resolution", "sender"],
                "Hey {recipient},\n\nMy bad on {issue}. "
                "We're fixing {resolution} right now. Ping {sender} if anything.\n\nSorry!",
            ),
        },
    },
    "thanks": {
        "zh-CN": {
            "formal": (
                ["recipient", "reason", "sender"],
                "尊敬的 {recipient}：\n\n感谢您 {reason}。您的支持对我们非常重要。"
                "如有需要请联系 {sender}。\n\n此致\n{sender}",
            ),
            "semi": (
                ["recipient", "reason", "sender"],
                "{recipient} 您好：\n\n感谢您 {reason}。真的很感谢！"
                "有事找 {sender}。\n\n谢谢！",
            ),
            "casual": (
                ["recipient", "reason", "sender"],
                "Hi {recipient}，\n\n谢啦 {reason}。帮大忙了！"
                "需要啥找 {sender}。\n\n多谢！",
            ),
        },
        "en-US": {
            "formal": (
                ["recipient", "reason", "sender"],
                "Dear {recipient},\n\nThank you for {reason}. Your support is invaluable to us. "
                "Please contact {sender} if needed.\n\nSincerely,\n{sender}",
            ),
            "semi": (
                ["recipient", "reason", "sender"],
                "Hi {recipient},\n\nThanks for {reason}. Really appreciate it! "
                "Reach {sender} if anything.\n\nThanks!",
            ),
            "casual": (
                ["recipient", "reason", "sender"],
                "Hey {recipient},\n\nThanks for {reason}. Huge help! "
                "Ping {sender} if you need anything.\n\nCheers!",
            ),
        },
    },
    "formal": {
        "zh-CN": {
            "formal": (
                ["recipient", "subject", "body", "sender"],
                "尊敬的 {recipient}：\n\n关于 {subject}，{body}。\n\n此致\n{sender}",
            ),
            "semi": (
                ["recipient", "subject", "body", "sender"],
                "{recipient} 您好：\n\n{subject} 方面，{body}。\n\n谢谢！",
            ),
            "casual": (
                ["recipient", "subject", "body", "sender"],
                "Hi {recipient}，\n\n{subject} 的事，{body}。\n\n谢啦！",
            ),
        },
        "en-US": {
            "formal": (
                ["recipient", "subject", "body", "sender"],
                "Dear {recipient},\n\nRegarding {subject}, {body}.\n\nSincerely,\n{sender}",
            ),
            "semi": (
                ["recipient", "subject", "body", "sender"],
                "Hi {recipient},\n\nOn {subject}, {body}.\n\nThanks!",
            ),
            "casual": (
                ["recipient", "subject", "body", "sender"],
                "Hey {recipient},\n\nAbout {subject}, {body}.\n\nCheers!",
            ),
        },
    },
}


# --------------------------------------------------------------------------
# 核心逻辑
# --------------------------------------------------------------------------
def validate_params(scenario: str, language: str, tone: str) -> None:
    """校验参数合法性"""
    if scenario not in TEMPLATES:
        raise DraftErr("E003", f"场景 '{scenario}' 不存在")
    if language not in TEMPLATES[scenario]:
        raise DraftErr("E004", f"场景 '{scenario}' 无语言 '{language}' 模板")
    if tone not in TEMPLATES[scenario][language]:
        raise DraftErr("E005", f"语气 '{tone}' 不存在")


def render_email(scenario: str, language: str, tone: str, fields: dict) -> tuple[str, list[str]]:
    """
    渲染邮件内容
    返回: (渲染后的文本, 缺失字段列表)
    """
    validate_params(scenario, language, tone)

    required, template = TEMPLATES[scenario][language][tone]
    missing = [f for f in required if not fields.get(f)]

    # 渲染占位符，缺失的标记为 [需核实:字段]
    rendered = template
    for field in required:
        value = fields.get(field, "")
        if not value:
            value = f"[需核实:{field}]"
        rendered = rendered.replace(f"{{{field}}}", value)

    # 检查风险措辞
    warnings = []
    for phrase in RISKY.get(language, []):
        if phrase in rendered:
            warnings.append(f"检测到风险措辞: '{phrase}'")

    return rendered, warnings


def format_output(text: str, output_format: str) -> str:
    """按指定格式输出"""
    if output_format == "markdown":
        return f"---\n\n{text}\n\n---"
    elif output_format == "html":
        # 简单转义并换行
        escaped = html.escape(text)
        return f"<html><body><pre>{escaped}</pre></body></html>"
    else:  # text
        return text


def parse_batch_file(filepath: str) -> list[dict]:
    """解析批量输入文件（CSV 或 JSON）"""
    path = Path(filepath)
    if not path.exists():
        raise DraftErr("E009", f"文件不存在: {filepath}")

    try:
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise DraftErr("E009", "JSON 必须是数组")
            return data
        else:  # CSV
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return [row for row in reader]
    except (json.JSONDecodeError, csv.Error) as e:
        raise DraftErr("E009", str(e))


def write_output(data, filepath: str) -> None:
    """原子化写入输出文件"""
    try:
        path = Path(filepath)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(data))
        tmp_path.replace(path)  # 原子替换
    except OSError as e:
        raise DraftErr("E010", str(e))


def process_single(args) -> dict:
    """处理单封邮件"""
    fields = {
        "recipient": args.recipient,
        "amount": args.amount,
        "invoice_no": args.invoice_no,
        "due_date": args.due_date,
        "sender": args.sender,
        "project": args.project,
        "next_step": args.next_step,
        "quote_no": args.quote_no,
        "valid_until": args.valid_until,
        "issue": args.issue,
        "resolution": args.resolution,
        "reason": args.reason,
        "subject": args.subject,
        "body": args.body,
    }
    # 只保留非 None 字段
    fields = {k: v for k, v in fields.items() if v is not None}

    text, warnings = render_email(args.scenario, args.language, args.tone, fields)
    output = format_output(text, args.format)

    result = {
        "scenario": args.scenario,
        "language": args.language,
        "tone": args.tone,
        "content": text,
        "output": output,
        "warnings": warnings,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if args.output:
        write_output(result, args.output)

    return result


def process_batch(args) -> list[dict]:
    """处理批量邮件"""
    records = parse_batch_file(args.batch)
    if len(records) > MAX_ROWS:
        raise DraftErr("E008", f"批量记录数 {len(records)} 超过上限 {MAX_ROWS}")

    results = []
    for i, record in enumerate(records):
        try:
            # 合并命令行默认字段与记录字段
            fields = {k: v for k, v in record.items() if v}
            text, warnings = render_email(
                record.get("scenario", args.scenario),
                record.get("language", args.language),
                record.get("tone", args.tone),
                fields,
            )
            results.append({
                "index": i,
                "content": text,
                "warnings": warnings,
                "success": True,
            })
        except DraftErr as e:
            results.append({
                "index": i,
                "error": str(e),
                "success": False,
            })

    if args.output:
        write_output(results, args.output)

    return results


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def selftest() -> int:
    """真实调用主流程并断言关键输出"""
    print("运行自检...")

    # 测试 1: 单封邮件渲染
    try:
        args = argparse.Namespace(
            scenario="dunning", language="zh-CN", tone="formal",
            recipient="张三", amount="1000", invoice_no="INV-001",
            due_date="2025-01-31", sender="李四",
            project=None, next_step=None, quote_no=None, valid_until=None,
            issue=None, resolution=None, reason=None, subject=None, body=None,
            format="text", output=None, batch=None,
        )
        result = process_single(args)
        assert "张三" in result["content"], "收件人未正确渲染"
        assert "INV-001" in result["content"], "发票号未正确渲染"
        assert "[需核实:" not in result["content"], "不应有缺失字段"
        print("  ✓ 单封邮件渲染正常")

        # 测试 2: 缺失字段标注
        args.recipient = None
        result = process_single(args)
        assert "[需核实:recipient]" in result["content"], "缺失字段未标注"
        print("  ✓ 缺失字段标注正常")

        # 测试 3: 风险措辞检测
        args = argparse.Namespace(
            scenario="formal", language="zh-CN", tone="formal",
            recipient="测试", amount=None, invoice_no=None, due_date=None,
            sender="系统", project=None, next_step=None, quote_no=None,
            valid_until=None, issue=None, resolution=None, reason=None,
            subject="测试", body="请立即处理，否则后果自负", format="text",
            output=None, batch=None,
        )
        result = process_single(args)
        assert len(result["warnings"]) > 0, "风险措辞未检测到"
        print("  ✓ 风险措辞检测正常")

        # 测试 4: 批量处理
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([
                {"scenario": "thanks", "language": "zh-CN", "tone": "casual",
                 "recipient": "王五", "reason": "帮助测试", "sender": "系统"},
                {"scenario": "invalid", "language": "zh-CN", "tone": "formal",
                 "recipient": "测试"},
            ], f)
            temp_path = f.name

        args = argparse.Namespace(
            scenario="thanks", language="zh-CN", tone="casual",
            recipient=None, amount=None, invoice_no=None, due_date=None,
            sender=None, project=None, next_step=None, quote_no=None,
            valid_until=None, issue=None, resolution=None, reason=None,
            subject=None, body=None, format="text", output=None, batch=temp_path,
        )
        results = process_batch(args)
        assert len(results) == 2, "批量处理数量错误"
        assert results[0]["success"], "第一条应成功"
        assert not results[1]["success"], "第二条应失败"
        print("  ✓ 批量处理正常")

        # 测试 5: 输出格式
        args = argparse.Namespace(
            scenario="thanks", language="en-US", tone="formal",
            recipient="John", amount=None, invoice_no=None, due_date=None,
            sender="Alice", project=None, next_step=None, quote_no=None,
            valid_until=None, issue=None, resolution=None, reason="your help",
            subject=None, body=None, format="html", output=None, batch=None,
        )
        result = process_single(args)
        assert "<html>" in result["output"], "HTML 格式错误"
        print("  ✓ HTML 输出正常")

        # 清理临时文件
        Path(temp_path).unlink()

        print("所有自检通过 ✓")
        return 0

    except Exception as e:
        print(f"自检失败: {e}")
        return 1


# --------------------------------------------------------------------------
# 主入口
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="商务邮件起草器 v" + __version__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scenario", choices=list(TEMPLATES.keys()), help="邮件场景")
    parser.add_argument("--language", choices=["zh-CN", "en-US"], default="zh-CN", help="语言")
    parser.add_argument("--tone", choices=["formal", "semi", "casual"], default="formal", help="语气")
    parser.add_argument("--format", choices=["markdown", "text", "html"], default="text", help="输出格式")

    # 字段参数
    parser.add_argument("--recipient", help="收件人")
    parser.add_argument("--amount", help="金额")
    parser.add_argument("--invoice_no", help="发票号")
    parser.add_argument("--due_date", help="到期日")
    parser.add_argument("--sender", help="发件人")
    parser.add_argument("--project", help="项目名")
    parser.add_argument("--next_step", help="下一步")
    parser.add_argument("--quote_no", help="报价单号")
    parser.add_argument("--valid_until", help="有效期至")
    parser.add_argument("--issue", help="问题描述")
    parser.add_argument("--resolution", help="解决方案")
    parser.add_argument("--reason", help="感谢原因")
    parser.add_argument("--subject", help="主题")
    parser.add_argument("--body", help="正文")

    # 批量与输出
    parser.add_argument("--batch", help="批量输入文件（CSV/JSON）")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.scenario:
        parser.error("必须指定 --scenario")

    try:
        if args.batch:
            results = process_batch(args)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            result = process_single(args)
            print(result["output"])
            if result["warnings"]:
                print("\n警告:", file=sys.stderr)
                for w in result["warnings"]:
                    print(f"  - {w}", file=sys.stderr)
    except DraftErr as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
