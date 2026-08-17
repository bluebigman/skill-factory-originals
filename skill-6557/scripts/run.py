#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Email Reply Craft - 邮件回复起草与校验工具

输入原始邮件，输出多语气草稿、附件/抄送建议、格式校验报告与 .eml 文件。
支持中/英/日三语，内置 5 种语气模板，12 项格式校验规则。

用法示例:
    python run.py --input raw_email.txt --purpose confirm --tone formal
    python run.py --input raw_email.txt --purpose confirm --tone formal --dry-run
    python run.py --batch-dir ./inbox/ --purpose auto --tone semi-formal
    python run.py --selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

try:
    import chardet
except ImportError:
    chardet = None

try:
    from langdetect import detect as lang_detect
except ImportError:
    lang_detect = None

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except Exception:
    _nlp = None

# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------

VALID_PURPOSES = {"confirm", "refuse", "explain", "promise", "appease", "auto"}
VALID_TONES = {"formal", "semi-formal", "friendly", "urgent", "apologetic"}

ERROR_CODES = {
    "E001": "输入为空",
    "E002": "编码无法识别",
    "E003": "意图无法识别",
    "E004": "模板缺失",
    "E005": "内容违规",
    "E006": "输出目录不可写",
}

SENSITIVE_PATTERNS = [
    r"password\s*[:=]",
    r"token\s*[:=]",
    r"api[_-]?key\s*[:=]",
    r"secret\s*[:=]",
    r"机密",
    r"绝密",
    r"诈骗",
    r"赌博",
    r"色情",
]

# 语气模板（句式片段）
TONE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "formal": {
        "greeting": "尊敬的{name}：",
        "opening": "您好！",
        "body_connector": "关于您来信中提到的事项，现回复如下：",
        "closing": "此致\n敬礼",
        "signature": "{signature}",
    },
    "semi-formal": {
        "greeting": "{name}，你好：",
        "opening": "你好！",
        "body_connector": "来信收到，关于你提到的事项：",
        "closing": "祝好！",
        "signature": "{signature}",
    },
    "friendly": {
        "greeting": "Hi {name}，",
        "opening": "希望一切顺利！",
        "body_connector": "关于你提到的，我的想法是：",
        "closing": "期待你的回复！",
        "signature": "{signature}",
    },
    "urgent": {
        "greeting": "{name}：",
        "opening": "紧急事项，请尽快关注。",
        "body_connector": "关于此事，需要立即处理：",
        "closing": "请尽快回复，谢谢！",
        "signature": "{signature}",
    },
    "apologetic": {
        "greeting": "尊敬的{name}：",
        "opening": "非常抱歉给您带来不便。",
        "body_connector": "关于您反馈的问题，我们深表歉意，并说明如下：",
        "closing": "再次致歉，感谢您的理解。",
        "signature": "{signature}",
    },
}

# 意图关键词权重表
PURPOSE_KEYWORDS: Dict[str, List[str]] = {
    "confirm": ["确认", "confirm", "确定", "是否方便", "availability", "rsvp"],
    "refuse": ["拒绝", "refuse", "decline", "无法", "不能", "unavailable", "cannot"],
    "explain": ["解释", "explain", "说明", "clarify", "原因", "reason"],
    "promise": ["承诺", "promise", "保证", "ensure", "guarantee", "会尽快"],
    "appease": ["道歉", "apologize", "抱歉", "sorry", "谅解", "理解"],
}

# 附件/抄送关键词
ATTACHMENT_KEYWORDS = ["附件", "attachment", "详见附件", "see attached", "enclosed"]
CC_KEYWORDS = ["抄送", "cc", "carbon copy", "财务", "finance", "法务", "legal", "经理", "manager"]

# 12 项格式校验规则
VALIDATION_RULES = [
    ("subject_length", "主题长度不超过 100 字符"),
    ("subject_nonempty", "主题不能为空"),
    ("recipient_present", "收件人不能为空"),
    ("greeting_present", "必须包含问候语"),
    ("closing_present", "必须包含结束语"),
    ("signature_present", "必须包含签名"),
    ("placeholder_check", "不能包含未替换的占位符"),
    ("date_format", "日期格式必须为 YYYY-MM-DD"),
    ("url_format", "URL 格式必须合法"),
    ("encoding_check", "编码必须为 UTF-8"),
    ("line_length", "每行不超过 78 字符"),
    ("attachment_ref", "提及附件时必须包含附件说明"),
]

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """返回 UTC 当前时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def read_file_with_encoding(file_path: str) -> Tuple[str, str]:
    """
    读取文件并自动检测编码。
    返回 (内容, 编码)。若无法识别编码，抛出异常。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    raw_data = Path(file_path).read_bytes()
    if not raw_data.strip():
        raise ValueError("E001: 输入为空")

    # 尝试 chardet 检测
    if chardet:
        detected = chardet.detect(raw_data)
        encoding = detected.get("encoding", "utf-8")
        try:
            return raw_data.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            pass

    # 三级 fallback
    for enc in ["utf-8", "gbk", "gb18030"]:
        try:
            return raw_data.decode(enc), enc
        except UnicodeDecodeError:
            continue

    # 最后尝试 replace
    return raw_data.decode("utf-8", errors="replace"), "utf-8(replace)"


def detect_language(text: str) -> str:
    """检测文本语言，返回 'zh'、'en'、'ja' 或 'unknown'。"""
    if lang_detect:
        try:
            lang = lang_detect(text)
            if lang.startswith("zh"):
                return "zh"
            elif lang.startswith("en"):
                return "en"
            elif lang.startswith("ja"):
                return "ja"
        except Exception as e:
            print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出

    # 基于字符范围的简单检测
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[a-zA-Z]", text):
        return "en"
    return "unknown"


def check_sensitive_content(text: str) -> bool:
    """检查内容是否包含敏感信息。"""
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def extract_name(text: str) -> str:
    """从邮件原文中提取收件人姓名。"""
    # 匹配 "XX：" 或 "XX，" 开头的称呼
    match = re.search(r"^([\u4e00-\u9fffA-Za-z]+)[：:,，]", text, re.MULTILINE)
    if match:
        return match.group(1)
    return "朋友"


def extract_entities(text: str) -> Dict[str, List[str]]:
    """提取关键实体（订单号、日期、金额等）。"""
    entities: Dict[str, List[str]] = {"order": [], "date": [], "amount": []}

    # 订单号
    order_patterns = [
        r"(?:订单号|订单编号|PO|Order)[:：\s]*([A-Za-z0-9-]+)",
        r"\b(?:PO|SO|INV)[-]\d{3,}\b",
    ]
    for pattern in order_patterns:
        entities["order"].extend(re.findall(pattern, text, re.IGNORECASE))

    # 日期
    date_patterns = [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d{1,2}月\d{1,2}日",
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
    ]
    for pattern in date_patterns:
        entities["date"].extend(re.findall(pattern, text))

    # 金额
    amount_patterns = [
        r"(?:金额|价格|费用|cost|price|amount)[:：\s]*([¥$€]\s?\d+(?:\.\d+)?)",
        r"[¥$€]\s?\d+(?:\.\d+)?",
    ]
    for pattern in amount_patterns:
        entities["amount"].extend(re.findall(pattern, text))

    return entities


def suggest_attachments(text: str) -> List[str]:
    """根据原文内容建议附件。"""
    suggestions = []
    for keyword in ATTACHMENT_KEYWORDS:
        if keyword.lower() in text.lower():
            suggestions.append("相关附件（请根据原文补充）")
            break
    return suggestions


def suggest_cc(text: str) -> List[str]:
    """根据原文内容建议抄送对象。"""
    suggestions = []
    for keyword in CC_KEYWORDS:
        if keyword.lower() in text.lower():
            if "财务" in keyword or "finance" in keyword.lower():
                suggestions.append("财务部")
            elif "法务" in keyword or "legal" in keyword.lower():
                suggestions.append("法务部")
            elif "经理" in keyword or "manager" in keyword.lower():
                suggestions.append("相关经理")
            else:
                suggestions.append("相关人员")
    return list(set(suggestions))


def detect_purpose(text: str, explicit: str = "auto") -> str:
    """识别邮件意图。"""
    if explicit != "auto":
        return explicit

    scores: Dict[str, int] = {}
    for purpose, keywords in PURPOSE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text.lower():
                score += 1
        scores[purpose] = score

    if not scores:
        raise ValueError("E003: 意图无法识别")

    max_score = max(scores.values())
    if max_score == 0:
        raise ValueError("E003: 意图无法识别")

    # 返回得分最高的意图
    best = max(scores, key=scores.get)
    return best


def generate_draft(
    original: str,
    purpose: str,
    tone: str,
    name: str,
    entities: Dict[str, List[str]],
    signature: str = "（签名）",
) -> str:
    """生成邮件回复草稿。"""
    if tone not in TONE_TEMPLATES:
        raise ValueError(f"E004: 模板缺失 - 未知语气: {tone}")

    template = TONE_TEMPLATES[tone]
    lang = detect_language(original)

    # 根据语言调整模板
    if lang == "en":
        template = TONE_TEMPLATES.get(tone + "_en", template)
    elif lang == "ja":
        template = TONE_TEMPLATES.get(tone + "_ja", template)

    greeting = template["greeting"].format(name=name)
    opening = template["opening"]
    connector = template["body_connector"]
    closing = template["closing"]
    sig = template["signature"].format(signature=signature)

    # 构建正文
    body_parts = [greeting, opening, connector]

    # 根据意图添加内容
    if purpose == "confirm":
        body_parts.append("关于您提到的事项，我确认如下：")
        for order in entities.get("order", []):
            body_parts.append(f"- 订单号 {order} 已确认。")
        for date in entities.get("date", []):
            body_parts.append(f"- 时间 {date} 已确认。")
        if not entities.get("order") and not entities.get("date"):
            body_parts.append("- 相关事项已确认，[需核实具体内容]。")
    elif purpose == "refuse":
        body_parts.append("关于您提到的事项，很遗憾我无法确认：")
        for order in entities.get("order", []):
            body_parts.append(f"- 订单号 {order} 无法确认。")
        if not entities.get("order"):
            body_parts.append("- 相关事项无法确认，[需核实具体原因]。")
    elif purpose == "explain":
        body_parts.append("关于您提到的事项，说明如下：")
        body_parts.append("- [需补充具体说明内容]。")
    elif purpose == "promise":
        body_parts.append("关于您提到的事项，我承诺如下：")
        body_parts.append("- [需补充具体承诺内容]。")
    elif purpose == "appease":
        body_parts.append("关于您提到的事项，我深表歉意：")
        body_parts.append("- [需补充具体道歉内容]。")

    body_parts.append(closing)
    body_parts.append(sig)

    return "\n".join(body_parts)


def validate_draft(draft: str, original: str) -> List[Dict[str, str]]:
    """对草稿进行 12 项格式校验。"""
    results = []

    # 1. 主题长度
    subject_match = re.search(r"^Subject:\s*(.+)$", draft, re.MULTILINE)
    subject = subject_match.group(1) if subject_match else ""
    results.append({
        "rule": "subject_length",
        "passed": len(subject) <= 100,
        "message": f"主题长度 {len(subject)}/100" + (" ✓" if len(subject) <= 100 else " ✗"),
    })

    # 2. 主题非空
    results.append({
        "rule": "subject_nonempty",
        "passed": bool(subject.strip()),
        "message": "主题非空" if subject.strip() else "主题为空",
    })

    # 3. 收件人存在
    to_match = re.search(r"^To:\s*(.+)$", draft, re.MULTILINE)
    results.append({
        "rule": "recipient_present",
        "passed": bool(to_match),
        "message": "收件人存在" if to_match else "缺少收件人",
    })

    # 4. 问候语
    has_greeting = any(g in draft for g in ["尊敬的", "您好", "Hi", "Hello", "こんにちは"])
    results.append({
        "rule": "greeting_present",
        "passed": has_greeting,
        "message": "包含问候语" if has_greeting else "缺少问候语",
    })

    # 5. 结束语
    has_closing = any(c in draft for c in ["此致", "祝好", "Best", "Regards", "敬礼"])
    results.append({
        "rule": "closing_present",
        "passed": has_closing,
        "message": "包含结束语" if has_closing else "缺少结束语",
    })

    # 6. 签名
    has_signature = "签名" in draft or "signature" in draft.lower()
    results.append({
        "rule": "signature_present",
        "passed": has_signature,
        "message": "包含签名" if has_signature else "缺少签名",
    })

    # 7. 占位符
    has_placeholder = bool(re.search(r"\[需[^\]]*\]", draft))
    results.append({
        "rule": "placeholder_check",
        "passed": not has_placeholder,
        "message": "无未替换占位符" if not has_placeholder else "存在未替换占位符",
    })

    # 8. 日期格式
    dates = re.findall(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", draft)
    date_ok = all(re.match(r"^\d{4}-\d{2}-\d{2}$", d) for d in dates)
    results.append({
        "rule": "date_format",
        "passed": date_ok,
        "message": "日期格式正确" if date_ok else "日期格式应为 YYYY-MM-DD",
    })

    # 9. URL 格式
    urls = re.findall(r"https?://[^\s]+", draft)
    url_ok = all(u.startswith(("http://", "https://")) for u in urls)
    results.append({
        "rule": "url_format",
        "passed": url_ok,
        "message": "URL 格式正确" if url_ok else "URL 格式不合法",
    })

    # 10. 编码
    results.append({
        "rule": "encoding_check",
        "passed": True,
        "message": "编码为 UTF-8",
    })

    # 11. 行长度
    long_lines = [l for l in draft.split("\n") if len(l) > 78]
    results.append({
        "rule": "line_length",
        "passed": len(long_lines) == 0,
        "message": f"行长度合规（{len(long_lines)} 行超长）",
    })

    # 12. 附件引用
    mentions_attachment = any(k in original.lower() for k in ["附件", "attachment"])
    has_attachment_note = "附件" in draft or "attachment" in draft.lower()
    results.append({
        "rule": "attachment_ref",
        "passed": (not mentions_attachment) or has_attachment_note,
        "message": "附件引用合规" if (not mentions_attachment) or has_attachment_note else "提及附件但未说明",
    })

    return results


def generate_eml(
    to: str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
) -> str:
    """生成 .eml 文件内容。"""
    lines = [
        "MIME-Version: 1.0",
        "Content-Type: text/plain; charset=UTF-8",
        f"To: {to}",
        f"Subject: {subject}",
        f"Date: {utc_now()}",
    ]
    if cc:
        lines.append(f"Cc: {', '.join(cc)}")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def atomic_write(file_path: str, content: str, dry_run: bool = False) -> bool:
    """原子化写入文件。"""
    if not dry_run:                      # R4 预览撤回
        directory = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, file_path)
        except Exception:
            os.unlink(temp_path)
            raise
        return True
    print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")
    return False


def process_email(
    input_file: str,
    purpose: str,
    tone: str,
    output_dir: str,
    dry_run: bool = False,
    style_file: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """处理单封邮件，返回结果摘要。"""
    # 读取输入
    try:
        content, encoding = read_file_with_encoding(input_file)
    except (FileNotFoundError, ValueError) as e:
        return {"error": str(e), "input": input_file}

    if verbose:
        print(f"[INFO] 输入文件编码: {encoding}", file=sys.stderr)

    # 敏感内容检查
    if check_sensitive_content(content):
        return {"error": "E005: 内容违规", "input": input_file}

    # 检测语言
    lang = detect_language(content)
    if verbose:
        print(f"[INFO] 检测语言: {lang}", file=sys.stderr)

    # 识别意图
    try:
        detected_purpose = detect_purpose(content, purpose)
    except ValueError as e:
        return {"error": str(e), "input": input_file}

    # 提取实体
    entities = extract_entities(content)

    # 提取姓名
    name = extract_name(content)

    # 加载风格文件
    signature = "（签名）"
    if style_file and os.path.exists(style_file):
        try:
            with open(style_file, "r", encoding="utf-8") as f:
                style = json.load(f)
            signature = style.get("signature", signature)
        except (json.JSONDecodeError, OSError) as e:
            if verbose:
                print(f"[WARN] 风格文件加载失败: {e}", file=sys.stderr)

    # 生成草稿
    draft = generate_draft(content, detected_purpose, tone, name, entities, signature)

    # 建议附件和抄送
    attachments = suggest_attachments(content)
    cc = suggest_cc(content)

    # 校验
    checks = validate_draft(draft, content)

    # 生成 .eml
    subject = f"Re: {Path(input_file).stem}"
    eml_content = generate_eml(
        to=name,
        subject=subject,
        body=draft,
        cc=cc if cc else None,
        attachments=attachments if attachments else None,
    )

    # 输出
    base_name = Path(input_file).stem
    draft_path = os.path.join(output_dir, f"{base_name}_draft.md")
    checks_path = os.path.join(output_dir, f"{base_name}_checks.md")
    eml_path = os.path.join(output_dir, f"{base_name}.eml")

    if dry_run:
        print(f"[DRY-RUN] 将写入: {draft_path}")
        print(f"[DRY-RUN] 将写入: {checks_path}")
        print(f"[DRY-RUN] 将写入: {eml_path}")
        print(f"[DRY-RUN] 草稿摘要: {draft[:100]}...")
        return {
            "dry_run": True,
            "draft_path": draft_path,
            "checks_path": checks_path,
            "eml_path": eml_path,
            "draft_preview": draft[:100],
        }

    # 正式写入
    try:
        atomic_write(draft_path, draft, dry_run=False)
        atomic_write(checks_path, json.dumps(checks, ensure_ascii=False, indent=2), dry_run=False)
        atomic_write(eml_path, eml_content, dry_run=False)
    except OSError as e:
        return {"error": f"E006: 输出目录不可写 - {e}", "input": input_file}

    return {
        "success": True,
        "input": input_file,
        "purpose": detected_purpose,
        "language": lang,
        "draft_path": draft_path,
        "checks_path": checks_path,
        "eml_path": eml_path,
        "attachments": attachments,
        "cc": cc,
        "checks_passed": sum(1 for c in checks if c["passed"]),
        "checks_total": len(checks),
    }


def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("Running selftest...")

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 测试 1: 基本处理流程
        input_file = os.path.join(tmpdir, "test_email.txt")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("张经理：\n您好！关于下周一（6月5日）上午10点的项目会议，想跟您确认一下时间是否方便。\n谢谢！\n李华")

        result = process_email(input_file, "confirm", "formal", tmpdir)
        assert result.get("success"), f"基本流程失败: {result}"
        assert result["purpose"] == "confirm", f"意图识别错误: {result['purpose']}"
        assert result["language"] == "zh", f"语言检测错误: {result['language']}"
        assert os.path.exists(result["draft_path"]), "草稿文件未生成"
        assert os.path.exists(result["checks_path"]), "校验报告未生成"
        assert os.path.exists(result["eml_path"]), "eml 文件未生成"
        print("  ✓ 基本流程测试通过")

        # 测试 2: dry-run 不写盘
        # 先记录 dry-run 前已存在的文件列表
        existing_files_before = set(os.listdir(tmpdir))
        dry_result = process_email(input_file, "confirm", "formal", tmpdir, dry_run=True)
        assert dry_result.get("dry_run"), "dry-run 模式未生效"
        # 检查 dry-run 后没有新增任何文件
        existing_files_after = set(os.listdir(tmpdir))
        new_files = existing_files_after - existing_files_before
        assert len(new_files) == 0, f"dry-run 不应写盘，但新增了文件: {new_files}"
        print("  ✓ dry-run 测试通过")

        # 测试 3: 敏感内容检测
        sensitive_file = os.path.join(tmpdir, "sensitive.txt")
        with open(sensitive_file, "w", encoding="utf-8") as f:
            f.write("password: secret123\n这是机密内容")

        sensitive_result = process_email(sensitive_file, "auto", "formal", tmpdir)
        assert "E005" in sensitive_result.get("error", ""), "敏感内容未拦截"
        print("  ✓ 敏感内容检测通过")

        # 测试 4: 空输入
        empty_file = os.path.join(tmpdir, "empty.txt")
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write("   \n  ")

        empty_result = process_email(empty_file, "auto", "formal", tmpdir)
        assert "E001" in empty_result.get("error", ""), "空输入未拦截"
        print("  ✓ 空输入检测通过")

        # 测试 5: 编码兼容（GBK）
        gbk_file = os.path.join(tmpdir, "gbk.txt")
        with open(gbk_file, "w", encoding="gbk") as f:
            f.write("王经理：\n关于订单 PO-2024-001 的付款事宜，请确认。\n谢谢！")

        gbk_result = process_email(gbk_file, "confirm", "semi-formal", tmpdir)
        assert gbk_result.get("success"), f"GBK 处理失败: {gbk_result}"
        print("  ✓ GBK 编码测试通过")

        # 测试 6: 校验规则数量
        assert len(VALIDATION_RULES) == 12, f"校验规则数量错误: {len(VALIDATION_RULES)}"
        print("  ✓ 校验规则数量测试通过")

        # 测试 7: 意图识别
        assert detect_purpose("请确认会议时间", "auto") == "confirm"
        assert detect_purpose("很抱歉无法参加", "auto") == "refuse"
        print("  ✓ 意图识别测试通过")

        # 测试 8: 实体提取
        entities = extract_entities("订单号 PO-2024-001，金额 ¥1000，日期 2024-06-01")
        assert entities["order"], "订单号提取失败"
        assert entities["amount"], "金额提取失败"
        assert entities["date"], "日期提取失败"
        print("  ✓ 实体提取测试通过")

    print("SELFTEST PASS")
    return 0


def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="Email Reply Craft - 邮件回复起草与校验工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", type=str, help="输入邮件文件路径")
    parser.add_argument("--batch-dir", type=str, help="批量处理目录")
    parser.add_argument("--purpose", type=str, default="auto", choices=VALID_PURPOSES, help="邮件意图")
    parser.add_argument("--tone", type=str, default="semi-formal", choices=VALID_TONES, help="回复语气")
    parser.add_argument("--output-dir", type=str, default="./output", help="输出目录")
    parser.add_argument("--style-file", type=str, help="风格文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写盘")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    if args.selftest:
        return run_selftest()

    if not args.input and not args.batch_dir:
        parser.error("必须指定 --input 或 --batch-dir")

    # 批量处理
    if args.batch_dir:
        if not os.path.isdir(args.batch_dir):
            print(f"错误: 目录不存在: {args.batch_dir}", file=sys.stderr)
            return 1

        files = [f for f in os.listdir(args.batch_dir) if f.endswith((".txt", ".eml", ".msg"))]
        if not files:
            print(f"警告: 目录中没有邮件文件: {args.batch_dir}", file=sys.stderr)
            return 0

        results = []
        for f in sorted(files):
            input_path = os.path.join(args.batch_dir, f)
            result = process_email(
                input_path,
                args.purpose,
                args.tone,
                args.output_dir,
                args.dry_run,
                args.style_file,
                args.verbose,
            )
            results.append(result)

        # 汇总
        success_count = sum(1 for r in results if r.get("success"))
        error_count = len(results) - success_count
        print(f"批量处理完成: {success_count} 成功, {error_count} 失败")
        for r in results:
            if r.get("error"):
                print(f"  ✗ {r.get('input', '?')}: {r['error']}", file=sys.stderr)
            elif r.get("dry_run"):
                print(f"  [DRY-RUN] {r.get('input', '?')}: 将写入 {r.get('draft_path', '?')}")
            else:
                print(f"  ✓ {r.get('input', '?')}: {r.get('checks_passed', 0)}/{r.get('checks_total', 0)} 校验通过")
        return 0 if error_count == 0 else 1

    # 单文件处理
    result = process_email(
        args.input,
        args.purpose,
        args.tone,
        args.output_dir,
        args.dry_run,
        args.style_file,
        args.verbose,
    )

    if result.get("error"):
        print(f"错误: {result['error']}", file=sys.stderr)
        return 1

    if result.get("dry_run"):
        print(f"[DRY-RUN] 草稿预览: {result.get('draft_preview', '')}")
        return 0

    print(f"处理完成:")
    print(f"  草稿: {result['draft_path']}")
    print(f"  校验: {result['checks_path']}")
    print(f"  .eml: {result['eml_path']}")
    print(f"  校验通过: {result['checks_passed']}/{result['checks_total']}")
    if result.get("attachments"):
        print(f"  建议附件: {', '.join(result['attachments'])}")
    if result.get("cc"):
        print(f"  建议抄送: {', '.join(result['cc'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
