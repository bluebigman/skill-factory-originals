#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gmail-ai-unsub 邮件退订智能助手 - 独立实现脚本

功能：解析邮件退订请求，生成结构化处理方案与操作指引。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

注意：本工具处理纯文本/JSON 格式的邮件内容输入，不直接解析 EML/MIME 文件。
如需处理真实邮件，请先通过 Gmail API 或邮件客户端导出为 JSON 格式。
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入格式无效（非 JSON 或结构错误）",
    "E003": "邮件内容解析失败",
    "E004": "无法识别有效的退订链接",
    "E005": "发件人信息缺失",
    "E006": "批量处理时存在无效条目",
    "E007": "输出序列化失败",
    "E008": "内部逻辑错误",
    "E009": "不支持的输入类型",
    "E010": "命令行参数错误",
}


# ============================================================
# 核心数据结构
# ============================================================

class ParsedEmail:
    """解析后的邮件结构化数据"""
    def __init__(self):
        self.sender: Optional[str] = None          # 发件人
        self.sender_email: Optional[str] = None    # 发件人邮箱
        self.subject: str = ""                      # 邮件主题
        self.body: str = ""                         # 邮件正文
        self.unsub_links: List[str] = []            # 退订链接列表
        self.email_type: str = "unknown"            # 邮件类型
        self.reason: str = ""                       # 退订原因
        self.confidence: Dict[str, float] = {}      # 字段置信度


# ============================================================
# 工具函数
# ============================================================

def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_id() -> str:
    """生成唯一工单 ID"""
    return f"TICKET-{uuid.uuid4().hex[:8].upper()}"


def _safe_json_dumps(data: Any) -> str:
    """安全 JSON 序列化，失败时抛出 E007"""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"E007: {ERROR_CODES['E007']} - {exc}") from exc


# ============================================================
# 核心解析逻辑
# ============================================================

def extract_sender(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    从文本中提取发件人名称和邮箱地址。
    返回 (发件人名称, 发件人邮箱)。
    
    处理逻辑：
    1. 优先匹配 "名称 <email>" 格式
    2. 其次匹配纯邮箱地址
    3. 支持 HTML 实体解码
    4. 对空输入和畸形格式返回 (None, None)
    """
    if not text or not isinstance(text, str):
        return None, None

    # HTML 实体解码（简单处理常见实体）
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    text = text.replace('&quot;', '"').replace('&#39;', "'")

    # 匹配 "名称 <email>" 格式
    pattern = r'([^<>\n]+?)\s*<([^<>\s@]+@[^<>\s@]+)>'
    match = re.search(pattern, text)
    if match:
        name = match.group(1).strip().strip('"\'')
        email = match.group(2).strip().lower()
        # 验证邮箱格式
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return name or None, email

    # 匹配纯邮箱地址
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    if match:
        email = match.group(0).strip().lower()
        # 尝试从邮箱前缀推导名称
        name_part = email.split('@')[0]
        name = name_part.replace('.', ' ').replace('_', ' ').title()
        return name, email

    return None, None


def extract_unsub_links(text: str) -> List[str]:
    """
    从文本中提取退订链接。
    支持 http/https 链接，优先识别包含 unsubscribe 关键字的链接。
    
    处理逻辑：
    1. 提取所有 http/https 链接
    2. 清理 URL 末尾标点
    3. 去重
    4. 优先返回包含退订关键字的链接
    """
    if not text or not isinstance(text, str):
        return []

    # 提取所有 http/https 链接
    url_pattern = r'https?://[^\s<>"\']+'
    all_urls = re.findall(url_pattern, text)

    # 清理 URL 末尾标点并去重
    cleaned_urls = []
    seen = set()
    for url in all_urls:
        url = url.rstrip('.,;:!?)>]')
        # 去除 HTML 实体
        url = url.replace('&amp;', '&')
        if url and url not in seen:
            seen.add(url)
            cleaned_urls.append(url)

    if not cleaned_urls:
        return []

    # 优先返回包含退订关键字的链接
    unsub_keywords = ['unsub', 'opt-out', 'optout', 'remove', 'cancel']
    priority_links = []
    other_links = []

    for url in cleaned_urls:
        url_lower = url.lower()
        if any(kw in url_lower for kw in unsub_keywords):
            priority_links.append(url)
        else:
            other_links.append(url)

    # 最多返回 3 个链接，优先退订相关
    result = priority_links + other_links
    return result[:3]


def classify_email_type(subject: str, body: str) -> str:
    """
    根据主题和正文判断邮件类型。
    """
    if not subject and not body:
        return "unknown"

    combined = f"{subject} {body}".lower()

    type_keywords = {
        "newsletter": ["newsletter", "weekly", "monthly", "digest", "update"],
        "promotion": ["promo", "sale", "discount", "offer", "deal", "coupon"],
        "notification": ["notification", "alert", "reminder", "notice"],
        "social": ["social", "friend", "connect", "follow", "invite"],
        "product": ["product", "order", "invoice", "receipt", "purchase"],
    }

    for email_type, keywords in type_keywords.items():
        if any(kw in combined for kw in keywords):
            return email_type

    return "unknown"


def infer_unsub_reason(email_type: str) -> str:
    """根据邮件类型推断退订原因"""
    reason_map = {
        "newsletter": "不再需要定期资讯",
        "promotion": "促销信息过多",
        "notification": "通知过于频繁",
        "social": "不想接收社交互动通知",
        "product": "已不再使用相关产品或服务",
        "unknown": "用户主动选择退订",
    }
    return reason_map.get(email_type, "用户主动选择退订")


def parse_email_content(content: Dict[str, Any]) -> ParsedEmail:
    """
    解析单封邮件内容。
    输入结构: {"sender": "...", "subject": "...", "body": "..."}
    或: {"from": "...", "subject": "...", "text": "..."}
    
    注意：本函数处理纯文本/JSON 格式的邮件内容，不解析 EML/MIME 文件。
    """
    if not isinstance(content, dict):
        raise ValueError(f"E002: {ERROR_CODES['E002']}")

    email = ParsedEmail()

    # 提取原始文本（支持多种字段名）
    sender_text = content.get("sender") or content.get("from") or ""
    subject = content.get("subject") or content.get("title") or ""
    body = content.get("body") or content.get("text") or content.get("content") or ""

    # 确保所有字段都是字符串
    sender_text = str(sender_text) if sender_text else ""
    subject = str(subject) if subject else ""
    body = str(body) if body else ""

    if not sender_text and not subject and not body:
        raise ValueError(f"E003: {ERROR_CODES['E003']}")

    # 解析发件人
    name, address = extract_sender(sender_text)
    if not address and sender_text:
        # 尝试从 body 中提取
        name, address = extract_sender(body)

    email.sender = name or (address.split('@')[0] if address else None)
    email.sender_email = address
    email.subject = subject
    email.body = body

    # 提取退订链接
    combined_text = f"{subject} {body} {sender_text}"
    email.unsub_links = extract_unsub_links(combined_text)

    # 分类与原因
    email.email_type = classify_email_type(email.subject, email.body)
    email.reason = infer_unsub_reason(email.email_type)

    # 置信度标注
    email.confidence = {
        "sender": 0.9 if address else 0.3,
        "unsub_links": 0.8 if email.unsub_links else 0.2,
        "email_type": 0.7 if email.email_type != "unknown" else 0.3,
    }

    return email


# ============================================================
# 工单生成
# ============================================================

def generate_ticket(email: ParsedEmail) -> Dict[str, Any]:
    """
    根据解析结果生成退订处理工单。
    """
    ticket = {
        "ticket_id": _generate_id(),
        "created_at": _now_iso(),
        "status": "pending_review",
        "summary": {
            "sender": email.sender,
            "sender_email": email.sender_email,
            "subject": email.subject,
            "email_type": email.email_type,
            "unsubscribe_reason": email.reason,
        },
        "action_plan": [],
        "risk_warnings": [],
        "confidence": email.confidence,
        "raw_links": email.unsub_links,
    }

    # 构建操作步骤
    if email.unsub_links:
        ticket["action_plan"].append({
            "step": 1,
            "action": "访问退订链接",
            "detail": f"点击以下链接完成退订: {email.unsub_links[0]}",
            "requires_captcha": False,
        })
        if len(email.unsub_links) > 1:
            ticket["action_plan"].append({
                "step": 2,
                "action": "备用退订方式",
                "detail": f"备用链接: {email.unsub_links[1]}",
                "requires_captcha": False,
            })
    else:
        ticket["action_plan"].append({
            "step": 1,
            "action": "手动退订",
            "detail": "未检测到自动退订链接，建议手动联系发件方或使用邮件客户端退订功能",
            "requires_captcha": False,
        })

    # 风险提示
    if not email.sender_email:
        ticket["risk_warnings"].append("发件人邮箱未确认，请核实邮件来源真实性")
    if not email.unsub_links:
        ticket["risk_warnings"].append("未找到退订链接，请谨慎处理避免误操作")
    if email.email_type == "unknown":
        ticket["risk_warnings"].append("邮件类型无法自动判断，请人工复核")

    # 标注需核实字段
    for field, conf in email.confidence.items():
        if conf < 0.5:
            field_display = {
                "sender": "发件人",
                "unsub_links": "退订链接",
                "email_type": "邮件类型",
            }.get(field, field)
            ticket["summary"][field] = f"[需核实:{field_display}]"

    return ticket


def process_batch(items: List[Any]) -> Dict[str, Any]:
    """
    批量处理多个邮件条目。
    """
    if not isinstance(items, list):
        raise ValueError(f"E002: {ERROR_CODES['E002']}")

    results = []
    errors = []
    valid_count = 0

    for idx, item in enumerate(items):
        try:
            email = parse_email_content(item)
            ticket = generate_ticket(email)
            results.append(ticket)
            valid_count += 1
        except (ValueError, RuntimeError) as exc:
            errors.append({
                "index": idx,
                "error": str(exc),
            })

    if valid_count == 0 and errors:
        raise ValueError(f"E006: {ERROR_CODES['E006']}")

    return {
        "total": len(items),
        "success": valid_count,
        "failed": len(errors),
        "tickets": results,
        "errors": errors,
    }


# ============================================================
# 主处理入口
# ============================================================

def process_input(data: Any) -> Dict[str, Any]:
    """
    统一处理入口。
    支持:
    - 单封邮件: {"sender": "...", "subject": "...", "body": "..."}
    - 批量邮件: [{"sender": "...", ...}, ...]
    - 带包裹的结构: {"emails": [...]} 或 {"items": [...]}
    
    注意：本工具处理纯文本/JSON 格式的邮件内容，不直接解析 EML/MIME 文件。
    """
    if data is None:
        raise ValueError(f"E001: {ERROR_CODES['E001']}")

    # 解包包裹结构
    if isinstance(data, dict):
        if "emails" in data:
            data = data["emails"]
        elif "items" in data:
            data = data["items"]
        elif "messages" in data:
            data = data["messages"]

    # 单封邮件
    if isinstance(data, dict):
        email = parse_email_content(data)
        ticket = generate_ticket(email)
        return {
            "mode": "single",
            "result": ticket,
        }

    # 批量邮件
    if isinstance(data, list):
        batch_result = process_batch(data)
        batch_result["mode"] = "batch"
        return batch_result

    raise ValueError(f"E009: {ERROR_CODES['E009']}")


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件或网络。
    覆盖核心链路：parse_email_content -> generate_ticket -> process_input
    """
    print("=" * 60)
    print("gmail-ai-unsub 自检开始")
    print("=" * 60)

    # ---- 测试用例 1: 单封邮件解析 ----
    print("\n[测试 1] 单封邮件解析")
    sample_email = {
        "sender": "TechNews <newsletter@technews.example.com>",
        "subject": "Weekly Tech Update - Issue #42",
        "body": "Hello! Here is your weekly tech newsletter.\n"
                "To unsubscribe, click here: https://technews.example.com/unsubscribe?token=abc123\n"
                "Or visit our preferences page: https://technews.example.com/preferences",
    }

    try:
        email = parse_email_content(sample_email)
        assert email.sender_email == "newsletter@technews.example.com", "发件人邮箱解析错误"
        assert email.sender is not None, "发件人名称不应为空"
        assert len(email.unsub_links) > 0, "应至少提取到一个退订链接"
        assert email.email_type == "newsletter", f"邮件类型应为 newsletter, 实际为 {email.email_type}"
        assert email.reason != "", "退订原因不应为空"
        print(f"  ✓ 发件人: {email.sender} <{email.sender_email}>")
        print(f"  ✓ 退订链接数: {len(email.unsub_links)}")
        print(f"  ✓ 邮件类型: {email.email_type}")
        print(f"  ✓ 退订原因: {email.reason}")
    except AssertionError as exc:
        print(f"  ✗ 断言失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ---- 测试用例 2: 工单生成 ----
    print("\n[测试 2] 工单生成")
    try:
        ticket = generate_ticket(email)
        assert ticket["ticket_id"].startswith("TICKET-"), "工单 ID 格式错误"
        assert ticket["status"] == "pending_review", "工单状态错误"
        assert len(ticket["action_plan"]) > 0, "应有操作步骤"
        assert len(ticket["risk_warnings"]) == 0, "此样例不应有风险警告"
        print(f"  ✓ 工单 ID: {ticket['ticket_id']}")
        print(f"  ✓ 操作步骤数: {len(ticket['action_plan'])}")
        print(f"  ✓ 风险警告数: {len(ticket['risk_warnings'])}")
    except AssertionError as exc:
        print(f"  ✗ 断言失败: {exc}")
        return 1
