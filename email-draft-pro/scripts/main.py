#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
email-draft-pro 技能独立实现脚本
================================
按场景生成专业商务邮件，自动匹配语气与格式，支持中英双语与批量起草。

仅依据功能规格独立实现（clean-room），不含任何既有代码。
标准库实现，无第三方依赖。

用法示例:
    python scripts/main.py --scenario 客户跟进 --recipient 张总 --sender 李明
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
import os
from typing import Dict, List, Optional, Any

# 错误码定义
ERROR_CODES = {
    "E001": "参数缺失：scenario、recipient、sender 为必填项",
    "E002": "不支持的场景关键词",
    "E003": "不支持的语种（仅支持 zh/en）",
    "E004": "不支持的语气（仅支持 formal/semi/friendly）",
    "E005": "批量收件人列表超过20项限制",
    "E006": "批量收件人列表格式错误（需为包含name字段的对象数组）",
    "E007": "JSON 解析失败",
    "E008": "输出格式不支持（仅支持 text/markdown/html）",
    "E009": "场景模板生成失败（内部错误）",
    "E010": "未知错误",
}


# ============================================================
# 一、场景模板库（核心数据）
# ============================================================

# 场景关键词 -> 中文模板函数
# 每个模板函数接收参数 dict，返回邮件正文（不含称呼和署名）

def _tmpl_business_invite(ctx: Dict[str, str]) -> str:
    """商务邀约场景"""
    context = ctx.get("context", "")
    action = ctx.get("action_item", "期待您的确认")
    deadline = ctx.get("deadline", "方便的时间")
    lines = [
        "您好！",
        "",
        f"冒昧打扰，{context}",
        f"我们诚挚邀请您参与此次合作交流，{action}。",
        f"如您在{deadline}前有空，烦请告知，我们将进一步安排。",
        "",
        "期待您的回复！",
    ]
    return "\n".join(lines)


def _tmpl_customer_followup(ctx: Dict[str, str]) -> str:
    """客户跟进场景"""
    context = ctx.get("context", "上次沟通后")
    action = ctx.get("action_item", "同步最新进展")
    deadline = ctx.get("deadline", "本周内")
    lines = [
        "您好！",
        "",
        f"自{context}以来，我们一直关注您的需求。",
        f"现向您{action}，如有任何问题请随时联系。",
        f"我们计划在{deadline}前与您再次沟通确认。",
        "",
        "感谢您的支持与信任！",
    ]
    return "\n".join(lines)


def _tmpl_project_report(ctx: Dict[str, str]) -> str:
    """项目汇报场景"""
    context = ctx.get("context", "项目当前阶段")
    action = ctx.get("action_item", "审阅报告内容")
    deadline = ctx.get("deadline", "本周末")
    lines = [
        "您好！",
        "",
        f"现将{context}的情况向您汇报如下。",
        f"请您{action}，{deadline}前如需调整请告知。",
        "",
        "感谢您的指导！",
    ]
    return "\n".join(lines)


def _tmpl_meeting_minutes(ctx: Dict[str, str]) -> str:
    """会议纪要场景"""
    context = ctx.get("context", "昨日会议")
    action = ctx.get("action_item", "确认会议纪要内容")
    deadline = ctx.get("deadline", "两日内")
    lines = [
        "您好！",
        "",
        f"根据{context}的讨论，现将纪要整理如下。",
        f"请您{action}，如有遗漏或修正请在{deadline}反馈。",
        "",
        "感谢配合！",
    ]
    return "\n".join(lines)


def _tmpl_quotation(ctx: Dict[str, str]) -> str:
    """报价说明场景"""
    context = ctx.get("context", "您咨询的产品/服务")
    action = ctx.get("action_item", "查看附件报价单")
    deadline = ctx.get("deadline", "本周五前")
    lines = [
        "您好！",
        "",
        f"针对{context}，我们已准备好详细报价。",
        f"请您{action}，如有疑问欢迎随时咨询。",
        f"该报价有效期至{deadline}，期待您的回复。",
        "",
        "顺祝商祺！",
    ]
    return "\n".join(lines)


def _tmpl_complaint_reply(ctx: Dict[str, str]) -> str:
    """投诉回复场景"""
    context = ctx.get("context", "您反馈的问题")
    action = ctx.get("action_item", "告知处理方案")
    deadline = ctx.get("deadline", "三个工作日内")
    lines = [
        "您好！",
        "",
        f"非常抱歉给您带来不便。关于{context}，我们深表歉意。",
        f"我们已成立专项小组处理此事，将{action}。",
        f"预计在{deadline}给您明确答复。",
        "",
        "再次感谢您的反馈，我们会持续改进！",
    ]
    return "\n".join(lines)


def _tmpl_cooperation_intent(ctx: Dict[str, str]) -> str:
    """合作意向场景"""
    context = ctx.get("context", "双方业务互补性")
    action = ctx.get("action_item", "探讨合作可能性")
    deadline = ctx.get("deadline", "近期")
    lines = [
        "您好！",
        "",
        f"我们关注到{context}，认为存在良好的合作空间。",
        f"希望能与贵方{action}，{deadline}是否方便安排交流？",
        "",
        "期待您的积极回应！",
    ]
    return "\n".join(lines)


def _tmpl_farewell(ctx: Dict[str, str]) -> str:
    """离职告别场景"""
    context = ctx.get("context", "多年共事")
    action = ctx.get("action_item", "保持联系")
    deadline = ctx.get("deadline", "离职前")
    lines = [
        "您好！",
        "",
        f"感谢您在过去{context}中的支持与关照。",
        f"因个人职业规划调整，我将{deadline}离开公司。",
        f"希望未来仍能{action}，我的联系方式不变。",
        "",
        "祝您一切顺利！",
    ]
    return "\n".join(lines)


# 场景注册表：中文关键词 -> 模板函数
SCENARIO_TEMPLATES_ZH = {
    "商务邀约": _tmpl_business_invite,
    "客户跟进": _tmpl_customer_followup,
    "项目汇报": _tmpl_project_report,
    "会议纪要": _tmpl_meeting_minutes,
    "报价说明": _tmpl_quotation,
    "投诉回复": _tmpl_complaint_reply,
    "合作意向": _tmpl_cooperation_intent,
    "离职告别": _tmpl_farewell,
}


# 英文模板（对应英文场景关键词）
def _tmpl_en_business_invite(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "our recent discussion")
    action = ctx.get("action_item", "confirm your availability")
    deadline = ctx.get("deadline", "your earliest convenience")
    return (
        f"Dear Sir/Madam,\n\n"
        f"We are writing regarding {context}.\n"
        f"We would like to invite you to participate in this cooperation. "
        f"Could you please {action} by {deadline}?\n\n"
        f"Looking forward to your reply!"
    )


def _tmpl_en_customer_followup(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "our last communication")
    action = ctx.get("action_item", "share the latest updates")
    deadline = ctx.get("deadline", "this week")
    return (
        f"Dear Sir/Madam,\n\n"
        f"Since {context}, we have been following your needs closely.\n"
        f"We would like to {action}. Please feel free to reach out if you have any questions.\n"
        f"We plan to follow up with you again before {deadline}.\n\n"
        f"Thank you for your continued support!"
    )


def _tmpl_en_project_report(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "the current project phase")
    action = ctx.get("action_item", "review the report")
    deadline = ctx.get("deadline", "this weekend")
    return (
        f"Dear Sir/Madam,\n\n"
        f"Please find below the status report regarding {context}.\n"
        f"We kindly ask you to {action} and provide feedback by {deadline} if adjustments are needed.\n\n"
        f"Thank you for your guidance!"
    )


def _tmpl_en_meeting_minutes(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "yesterday's meeting")
    action = ctx.get("action_item", "confirm the minutes")
    deadline = ctx.get("deadline", "two days")
    return (
        f"Dear Sir/Madam,\n\n"
        f"Based on {context}, please find the meeting minutes below.\n"
        f"Please {action}. Kindly provide any corrections within {deadline}.\n\n"
        f"Thank you for your cooperation!"
    )


def _tmpl_en_quotation(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "the product/service you inquired about")
    action = ctx.get("action_item", "review the attached quotation")
    deadline = ctx.get("deadline", "this Friday")
    return (
        f"Dear Sir/Madam,\n\n"
        f"Regarding {context}, we have prepared a detailed quotation for you.\n"
        f"Please {action}. Feel free to contact us with any questions.\n"
        f"This quotation is valid until {deadline}. We look forward to your response.\n\n"
        f"Best regards!"
    )


def _tmpl_en_complaint_reply(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "the issue you reported")
    action = ctx.get("action_item", "share our resolution plan")
    deadline = ctx.get("deadline", "three business days")
    return (
        f"Dear Sir/Madam,\n\n"
        f"We sincerely apologize for the inconvenience caused by {context}.\n"
        f"We have established a dedicated team to address this matter and will {action}.\n"
        f"We expect to provide you with a clear response within {deadline}.\n\n"
        f"Thank you for your feedback. We are committed to continuous improvement!"
    )


def _tmpl_en_cooperation_intent(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "the complementary strengths of our businesses")
    action = ctx.get("action_item", "explore potential cooperation")
    deadline = ctx.get("deadline", "the near future")
    return (
        f"Dear Sir/Madam,\n\n"
        f"We have noticed {context} and believe there is great potential for collaboration.\n"
        f"We would like to {action} with your team. Would {deadline} be convenient for a discussion?\n\n"
        f"We look forward to your positive response!"
    )


def _tmpl_en_farewell(ctx: Dict[str, str]) -> str:
    context = ctx.get("context", "years of working together")
    action = ctx.get("action_item", "keep in touch")
    deadline = ctx.get("deadline", "my departure")
    return (
        f"Dear Sir/Madam,\n\n"
        f"Thank you for your support during {context}.\n"
        f"Due to personal career planning, I will be leaving the company {deadline}.\n"
        f"I hope we can {action}. My contact information remains unchanged.\n\n"
        f"Wishing you all the best!"
    )


# 英文场景注册表
SCENARIO_TEMPLATES_EN = {
    "business_invite": _tmpl_en_business_invite,
    "customer_followup": _tmpl_en_customer_followup,
    "project_report": _tmpl_en_project_report,
    "meeting_minutes": _tmpl_en_meeting_minutes,
    "quotation": _tmpl_en_quotation,
    "complaint_reply": _tmpl_en_complaint_reply,
    "cooperation_intent": _tmpl_en_cooperation_intent,
    "farewell": _tmpl_en_farewell,
}

# 场景关键词映射（英文场景关键词 -> 英文模板键）
EN_SCENARIO_ALIASES = {
    "invite": "business_invite",
    "invitation": "business_invite",
    "followup": "customer_followup",
    "follow_up": "customer_followup",
    "report": "project_report",
    "meeting": "meeting_minutes",
    "minutes": "meeting_minutes",
    "quote": "quotation",
    "quotation": "quotation",
    "complaint": "complaint_reply",
    "cooperation": "cooperation_intent",
    "partnership": "cooperation_intent",
    "farewell": "farewell",
    "goodbye": "farewell",
}


# ============================================================
# 二、语气修饰器
# ============================================================

def _apply_tone(body: str, tone: str, language: str) -> str:
    """根据语气调整邮件正文（增加开场/结尾修饰）"""
    if language == "zh":
        if tone == "formal":
            return f"尊敬的先生/女士：\n\n{body}\n\n此致敬礼！"
        elif tone == "friendly":
            return f"嗨，朋友：\n\n{body}\n\n祝好！"
        else:  # semi
            return body
    else:  # en
        if tone == "formal":
            return f"Dear Sir/Madam,\n\n{body}\n\nYours faithfully,"
        elif tone == "friendly":
            return f"Hi there,\n\n{body}\n\nBest wishes,"
        else:  # semi
            return body


# ============================================================
# 三、核心生成逻辑
# ============================================================

def generate_email(params: Dict[str, Any]) -> Dict[str, str]:
    """
    生成单封邮件。
    返回 {"subject": ..., "body": ...}
    """
    # 参数校验
    scenario = params.get("scenario", "")
    recipient = params.get("recipient", "")
    sender = params.get("sender", "")
    language = params.get("language", "zh")
    tone = params.get("tone", "semi")

    if not scenario or not recipient or not sender:
        raise ValueError(ERROR_CODES["E001"])

    if language not in ("zh", "en"):
        raise ValueError(ERROR_CODES["E003"])

    if tone not in ("formal", "semi", "friendly"):
        raise ValueError(ERROR_CODES["E004"])

    # 选择模板
    if language == "zh":
        if scenario not in SCENARIO_TEMPLATES_ZH:
            raise ValueError(ERROR_CODES["E002"])
        template_fn = SCENARIO_TEMPLATES_ZH[scenario]
    else:
        # 英文场景关键词映射
        en_key = EN_SCENARIO_ALIASES.get(scenario.lower(), scenario.lower())
        if en_key not in SCENARIO_TEMPLATES_EN:
            raise ValueError(ERROR_CODES["E002"])
        template_fn = SCENARIO_TEMPLATES_EN[en_key]

    # 生成正文
    try:
        body = template_fn(params)
    except Exception as exc:
        raise ValueError(f"{ERROR_CODES['E009']} ({exc})")

    # 应用语气修饰
    body = _apply_tone(body, tone, language)

    # 生成主题
    if language == "zh":
        subject = f"关于{scenario}的邮件"
    else:
        subject = f"Regarding {scenario}"

    # 组装完整邮件（含称呼和署名）
    if language == "zh":
        greeting = f"{recipient}，您好！"
        full_body = f"{greeting}\n\n{body}\n\n{recipient}\n{sender}"
    else:
        greeting = f"Dear {recipient},"
        full_body = f"{greeting}\n\n{body}\n\nBest regards,\n{sender}"

    return {
        "subject": subject,
        "body": full_body,
    }


def generate_batch(params: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    批量生成邮件。
    参数中需包含 batch_list（≤20项），每项含 name 字段。
    返回邮件列表。
    """
    batch_list = params.get("batch_list", [])
    if not batch_list:
        raise ValueError(ERROR_CODES["E005"])

    if len(batch_list) > 20:
        raise ValueError(ERROR_CODES["E005"])

    results = []
    for item in batch_list:
        if not isinstance(item, dict) or "name" not in item:
            raise ValueError(ERROR_CODES["E006"])

        # 复制参数并替换收件人
        item_params = dict(params)
        item_params["recipient"] = item["name"]
        # 支持自定义公司名
        if "company" in item:
            item_params["context"] = item_params.get("context", "") + f"（{item['company']}）"

        results.append(generate_email(item_params))

    return results


# ============================================================
# 四、输出格式化
# ============================================================

def format_output(emails: List[Dict[str, str]], fmt: str = "text") -> str:
    """将邮件列表格式化为指定格式"""
    if fmt not in ("text", "markdown", "html"):
        raise ValueError(ERROR_CODES["E008"])

    if fmt == "text":
        parts = []
        for i, email in enumerate(emails, 1):
            parts.append(f"邮件 {i}")
            parts.append(f"主题: {email['subject']}")
            parts.append("正文:")
            parts.append(email["body"])
            parts.append("=" * 50)
        return "\n".join(parts)

    elif fmt == "markdown":
        parts = []
        for i, email in enumerate(emails, 1):
            parts.append(f"## 邮件 {i}")
            parts.append(f"**主题:** {email['subject']}")
            parts.append("")
            parts.append("
