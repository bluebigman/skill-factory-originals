#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
email-draft-pro 独立实现脚本
-----------------------------
依据功能规格 clean-room 重写，不参考任何既有实现。

功能：
  - 按场景生成商务邮件（中文 / 英文）
  - 支持语气风格（正式 / 半正式 / 亲切 / 紧迫 / 委婉 / 坚定）
  - 支持批量起草（单批 ≤ 100 条）
  - 自动质量评分（0-100），低于 70 分附修改建议
  - `--selftest` 离线自检（内置硬编码样例，不读文件、不联网）

用法示例：
  python scripts/main.py --scene follow_up --lang zh --tone formal \
      --recipient "张经理" --sender "李华" --subject "项目跟进"
  python scripts/main.py --batch batch_input.json --out results.json
  python scripts/main.py --selftest
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义（E001 - E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数缺失或格式错误",
    "E002": "场景类型不受支持",
    "E003": "语言类型不受支持",
    "E004": "语气风格不受支持",
    "E005": "批量数量超出限制（>100）",
    "E006": "输入文件读取失败",
    "E007": "输出文件写入失败",
    "E008": "JSON 解析失败",
    "E009": "内部逻辑错误（未知分支）",
    "E010": "自检失败",
}


def fail(code: str, detail: str = "") -> None:
    """抛出带错误码的异常信息并退出。"""
    msg = f"[{code}] {ERROR_CODES.get(code, '未知错误')}"
    if detail:
        msg += f" - {detail}"
    print(msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class EmailDraft:
    """单封邮件草稿的数据结构。"""

    scene: str
    language: str
    tone: str
    recipient: str
    sender: str
    subject: str
    body: str
    score: int = 0
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene": self.scene,
            "language": self.language,
            "tone": self.tone,
            "recipient": self.recipient,
            "sender": self.sender,
            "subject": self.subject,
            "body": self.body,
            "score": self.score,
            "suggestions": self.suggestions,
        }


# ---------------------------------------------------------------------------
# 模板库（完整覆盖所有场景×语言×语气组合）
# ---------------------------------------------------------------------------
# 每个场景包含中英文的称呼、正文模板、结束语模板
SCENE_TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    "follow_up": {
        "zh": {
            "greeting": "尊敬的{recipient}，",
            "body": (
                "感谢您对{subject}的关注。\n"
                "我上次于{date}与您沟通相关事项，现想确认一下进展。\n"
                "如您有任何疑问或需要进一步信息，请随时与我联系。"
            ),
            "closing": "此致\n{recipient}\n{sender}",
        },
        "en": {
            "greeting": "Dear {recipient},",
            "body": (
                "Thank you for your interest in {subject}.\n"
                "I contacted you on {date} regarding this matter and would like to follow up.\n"
                "Please feel free to reach out if you have any questions."
            ),
            "closing": "Best regards,\n{recipient}\n{sender}",
        },
    },
    "internal_report": {
        "zh": {
            "greeting": "各位同事，",
            "body": (
                "现就{subject}进行阶段性汇报。\n"
                "当前进展顺利，预计{date}前完成主要工作。\n"
                "如有建议请在本周内反馈。"
            ),
            "closing": "谢谢\n{sender}",
        },
        "en": {
            "greeting": "Dear team,",
            "body": (
                "I would like to provide a progress update on {subject}.\n"
                "The work is on track, expected to complete by {date}.\n"
                "Please share your feedback by the end of this week."
            ),
            "closing": "Thank you,\n{sender}",
        },
    },
    "meeting_invite": {
        "zh": {
            "greeting": "尊敬的{recipient}，",
            "body": (
                "邀请您参加关于{subject}的会议。\n"
                "会议时间：{date}。\n"
                "期待您的参与，共同讨论重要议题。"
            ),
            "closing": "祝好\n{sender}",
        },
        "en": {
            "greeting": "Dear {recipient},",
            "body": (
                "You are invited to a meeting on {subject}.\n"
                "Time: {date}.\n"
                "We look forward to your participation."
            ),
            "closing": "Best,\n{sender}",
        },
    },
    "thank_you": {
        "zh": {
            "greeting": "尊敬的{recipient}，",
            "body": (
                "衷心感谢您在{subject}中给予的支持与帮助。\n"
                "您的协助对我们意义重大，期待未来更多合作。"
            ),
            "closing": "再次感谢\n{sender}",
        },
        "en": {
            "greeting": "Dear {recipient},",
            "body": (
                "I sincerely appreciate your support on {subject}.\n"
                "Your assistance means a lot to us, and I look forward to future collaboration."
            ),
            "closing": "With gratitude,\n{sender}",
        },
    },
    "payment_reminder": {
        "zh": {
            "greeting": "尊敬的{recipient}，",
            "body": (
                "温馨提醒：关于{subject}的款项已过约定日期。\n"
                "请在{date}前完成支付，如有特殊情况请及时沟通。\n"
                "感谢您的配合。"
            ),
            "closing": "此致\n{sender}",
        },
        "en": {
            "greeting": "Dear {recipient},",
            "body": (
                "A friendly reminder that the payment for {subject} is due.\n"
                "Please complete the payment by {date}, or contact us if there is an issue.\n"
                "Thank you for your cooperation."
            ),
            "closing": "Sincerely,\n{sender}",
        },
    },
    "complaint_reply": {
        "zh": {
            "greeting": "尊敬的{recipient}，",
            "body": (
                "关于您提出的{subject}问题，我们深表歉意。\n"
                "我们将于{date}前给出解决方案，并持续跟进。\n"
                "感谢您的耐心与理解。"
            ),
            "closing": "诚挚道歉\n{sender}",
        },
        "en": {
            "greeting": "Dear {recipient},",
            "body": (
                "We sincerely apologize for the issue you raised regarding {subject}.\n"
                "We will provide a solution by {date} and keep you updated.\n"
                "Thank you for your patience."
            ),
            "closing": "Sincerely,\n{sender}",
        },
    },
}

# 支持的场景列表
SUPPORTED_SCENES = list(SCENE_TEMPLATES.keys())
SUPPORTED_LANGUAGES = ["zh", "en"]
SUPPORTED_TONES = ["formal", "semi_formal", "friendly", "urgent", "euphemistic", "firm"]
MAX_BATCH_SIZE = 100

# 语气风格对正文的修饰（前缀/后缀）
TONE_MODIFIERS: Dict[str, Dict[str, Dict[str, str]]] = {
    "formal": {
        "zh": {"prefix": "【正式】", "suffix": "此邮件为正式商务沟通，请妥善处理。"},
        "en": {"prefix": "[Formal]", "suffix": "This is an official business communication."},
    },
    "semi_formal": {
        "zh": {"prefix": "", "suffix": "如有问题请随时联系。"},
        "en": {"prefix": "", "suffix": "Feel free to reach out anytime."},
    },
    "friendly": {
        "zh": {"prefix": "嘿，", "suffix": "期待您的回复！"},
        "en": {"prefix": "Hi there,", "suffix": "Looking forward to your reply!"},
    },
    "urgent": {
        "zh": {"prefix": "【紧急】", "suffix": "此事项需要您尽快处理，感谢配合。"},
        "en": {"prefix": "[URGENT]", "suffix": "Your prompt attention is required."},
    },
    "euphemistic": {
        "zh": {"prefix": "", "suffix": "若有不妥之处，敬请谅解。"},
        "en": {"prefix": "", "suffix": "Please excuse any inconvenience."},
    },
    "firm": {
        "zh": {"prefix": "【重要】", "suffix": "请您务必重视此事。"},
        "en": {"prefix": "[Important]", "suffix": "Please treat this matter with due importance."},
    },
}


# ---------------------------------------------------------------------------
# 核心生成逻辑
# ---------------------------------------------------------------------------
def generate_email(
    scene: str,
    language: str,
    tone: str,
    recipient: str,
    sender: str,
    subject: str,
    date: Optional[str] = None,
) -> EmailDraft:
    """根据参数生成一封邮件草稿。"""
    # 参数校验
    if scene not in SUPPORTED_SCENES:
        fail("E002", f"场景 '{scene}' 不受支持，可选: {SUPPORTED_SCENES}")
    if language not in SUPPORTED_LANGUAGES:
        fail("E003", f"语言 '{language}' 不受支持，可选: {SUPPORTED_LANGUAGES}")
    if tone not in SUPPORTED_TONES:
        fail("E004", f"语气 '{tone}' 不受支持，可选: {SUPPORTED_TONES}")

    # 获取模板
    lang_templates = SCENE_TEMPLATES[scene][language]
    if date is None:
        date = "近日" if language == "zh" else "recently"

    # 填充模板
    try:
        greeting = lang_templates["greeting"].format(recipient=recipient)
        body = lang_templates["body"].format(subject=subject, date=date)
        closing = lang_templates["closing"].format(recipient=recipient, sender=sender)
    except KeyError as e:
        fail("E009", f"模板占位符缺失: {e}")

    # 应用语气修饰
    tone_mod = TONE_MODIFIERS[tone][language]
    full_body = f"{tone_mod['prefix']}\n{body}\n{tone_mod['suffix']}"

    # 组装完整邮件
    full_text = f"{greeting}\n\n{full_body}\n\n{closing}"

    # 质量评分（基于长度和完整性，宽松规则）
    score = _quality_score(full_text, scene, language, tone)
    suggestions = _get_suggestions(score, full_text, language)

    return EmailDraft(
        scene=scene,
        language=language,
        tone=tone,
        recipient=recipient,
        sender=sender,
        subject=subject,
        body=full_text,
        score=score,
        suggestions=suggestions,
    )


def _quality_score(text: str, scene: str, language: str, tone: str) -> int:
    """简单质量评分：长度、结构完整性、语气匹配度。"""
    score = 50  # 基础分

    # 长度加分（宽松判断）
    if len(text) > 100:
        score += 15
    if len(text) > 200:
        score += 10

    # 结构完整性（包含称呼、正文、结束语）
    if text.count("\n") >= 4:
        score += 10

    # 场景关键词覆盖（宽松）
    scene_keywords = {
        "follow_up": ["确认", "进展", "联系"] if language == "zh" else ["follow", "progress", "contact"],
        "internal_report": ["汇报", "进展", "完成"] if language == "zh" else ["report", "progress", "complete"],
        "meeting_invite": ["会议", "时间", "参加"] if language == "zh" else ["meeting", "time", "attend"],
        "thank_you": ["感谢", "帮助", "支持"] if language == "zh" else ["thank", "help", "support"],
        "payment_reminder": ["款项", "支付", "日期"] if language == "zh" else ["payment", "due", "date"],
        "complaint_reply": ["歉意", "问题", "解决"] if language == "zh" else ["apologize", "issue", "solution"],
    }
    for kw in scene_keywords.get(scene, []):
        if kw in text:
            score += 3

    # 语气匹配（宽松）
    tone_indicators = {
        "formal": ["正式", "妥善", "official"] if language == "zh" else ["formal", "official"],
        "friendly": ["嘿", "期待", "Hi"] if language == "zh" else ["Hi", "looking forward"],
        "urgent": ["紧急", "尽快", "URGENT"] if language == "zh" else ["URGENT", "prompt"],
        "euphemistic": ["谅解", "不便", "excuse"] if language == "zh" else ["excuse", "inconvenience"],
        "firm": ["务必", "重视", "Important"] if language == "zh" else ["Important", "due importance"],
    }
    for ind in tone_indicators.get(tone, []):
        if ind in text:
            score += 5

    # 封顶 100
    return min(100, max(0, score))


def _get_suggestions(score: int, text: str, language: str) -> List[str]:
    """根据评分给出修改建议（宽松规则）。"""
    suggestions = []
    if score < 70:
        suggestions.append(
            "邮件内容略显单薄，建议补充更多细节。"
            if language == "zh"
            else "The email appears thin; consider adding more details."
        )
    if len(text) < 150:
        suggestions.append(
            "建议适当扩充正文内容，使表达更完整。"
            if language == "zh"
            else "Consider expanding the body for completeness."
        )
    if score >= 70:
        suggestions.append(
            "整体质量良好。"
            if language == "zh"
            else "Overall quality is good."
        )
    return suggestions


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def batch_generate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量生成邮件草稿。每项需包含 scene/language/tone/recipient/sender/subject。"""
    if len(items) > MAX_BATCH_SIZE:
        fail("E005", f"批量数量 {len(items)} 超过上限 {MAX_BATCH_SIZE}")

    results = []
    for idx, item in enumerate(items):
        try:
            draft = generate_email(
                scene=item["scene"],
                language=item.get("language", "zh"),
                tone=item.get("tone", "formal"),
                recipient=item["recipient"],
                sender=item["sender"],
                subject=item["subject"],
                date=item.get("date"),
            )
            results.append(draft.to_dict())
        except KeyError as e:
            fail("E001", f"第 {idx+1} 条缺少必要字段: {e}")
    return results


# ---------------------------------------------------------------------------
# 格式转换函数
# ---------------------------------------------------------------------------
def format_output(results: List[Dict[str, Any]], fmt: str = "md") -> str:
    """将结果转换为指定格式（md/txt/html）。"""
    if fmt == "md":
        return _to_markdown(results)
    elif fmt == "txt":
        return _to_plain_text(results)
    elif fmt == "html":
        return _to_html(results)
    else:
        fail("E001", f"不支持的输出格式: {fmt}")


def _to_markdown(results: List[Dict[str, Any]]) -> str:
    """转换为 Markdown 格式。"""
    lines = []
    for r in results:
        lines.append(f"## {r['subject']}\n")
        lines.append(f"**场景**: {r['scene']} | **语言**: {r['language']} | **语气**: {r['tone']}")
        lines.append(f"**评分**: {r['score']}/100\n")
        if r['suggestions']:
            lines.append("**建议**:")
            for s in r['suggestions']:
                lines.append(f"- {s}")
            lines.append("")
        lines.append(r['body'])
        lines.append("\n---\n")
    return "\n".join(lines)


def _to_plain_text(results: List[Dict[str, Any]]) -> str:
    """转换为纯文本格式。"""
    lines = []
    for r in results:
        lines.append(f"主题: {r['subject']}")
        lines.append(f"场景: {r['scene']} | 语言: {r['language']} | 语气: {r['tone']}")
        lines.append(f"评分: {r['score']}/100")
        if r['suggestions']:
            lines.append("建议:")
            for s in r['suggestions']:
                lines.append(f"  - {s}")
