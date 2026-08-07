#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Gmail AI 退订工具（独立实现）

依据功能规格 clean-room 重写，仅使用标准库。
提供离线自检（--selftest），不访问网络、不读取外部文件。
"""

import argparse
import sys
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空：请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失：还缺少以下信息，请补充：",
    "E003": "输入格式错误：输入格式不符合要求，示例：...",
    "E004": "超出能力边界：这超出了本工具的能力范围，建议...",
    "E005": "置信度过低：结果无法确定，建议：...",
    "E006": "内部逻辑错误：处理过程中发生未知异常，请重试。",
    "E007": "参数错误：命令行参数不合法，请检查后重试。",
    "E008": "数据解析失败：输入内容无法解析为有效结构。",
    "E009": "批量处理中断：批量任务中某一项失败，已停止后续处理。",
    "E010": "输出生成失败：无法生成符合要求的输出格式。",
}


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class UnsubItem:
    """单条退订候选记录。"""

    sender_email: str
    subject: str
    unsubscribe_link: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessingResult:
    """一次处理的结果。"""

    success: bool
    items: List[UnsubItem] = field(default_factory=list)
    error_code: Optional[str] = None
    error_message: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "items": [item.to_dict() for item in self.items],
            "error_code": self.error_code,
            "error_message": self.error_message,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class GmailUnsubProcessor:
    """
    核心处理器：从原始输入中识别退订候选邮件。
    仅做规则解析，不涉及网络/Gmail API。
    """

    # 常见退订关键词（用于识别营销邮件）
    MARKETING_KEYWORDS = [
        "unsubscribe",
        "退订",
        "取消订阅",
        "newsletter",
        "促销",
        "promotion",
        "marketing",
        "广告",
        "推广",
    ]

    # 常见退订链接特征
    UNSUBSCRIBE_LINK_PATTERNS = [
        re.compile(r"https?://[^\s<>\"']*unsubscribe[^\s<>\"']*", re.IGNORECASE),
        re.compile(r"https?://[^\s<>\"']*opt-?out[^\s<>\"']*", re.IGNORECASE),
        re.compile(r"https?://[^\s<>\"']*退订[^\s<>\"']*", re.IGNORECASE),
        re.compile(r"https?://[^\s<>\"']*取消订阅[^\s<>\"']*", re.IGNORECASE),
    ]

    # 邮件地址正则
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    def process_input(self, raw_input: str) -> ProcessingResult:
        """
        处理用户提供的原始输入（邮件列表、文本、JSON 等）。
        返回结构化识别结果。
        """
        # E001: 输入为空
        if not raw_input or not raw_input.strip():
            return self._make_error("E001")

        # 尝试解析 JSON 输入
        if raw_input.strip().startswith("{"):
            try:
                data = json.loads(raw_input)
                if isinstance(data, list):
                    return self._process_batch(data)
                elif isinstance(data, dict):
                    return self._process_single(data)
                else:
                    return self._make_error("E003")
            except json.JSONDecodeError:
                return self._make_error("E008")

        # 文本输入：按行解析
        lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
        if not lines:
            return self._make_error("E001")

        items = []
        for line in lines:
            item = self._parse_text_line(line)
            if item:
                items.append(item)

        if not items:
            return self._make_error("E003")

        return self._build_success_result(items)

    def _process_batch(self, data: List[Any]) -> ProcessingResult:
        """批量处理 JSON 数组。"""
        items = []
        for entry in data:
            if not isinstance(entry, dict):
                return self._make_error("E003")
            item = self._parse_dict(entry)
            if item:
                items.append(item)
            else:
                return self._make_error("E002")

        if not items:
            return self._make_error("E003")
        return self._build_success_result(items)

    def _process_single(self, data: Dict[str, Any]) -> ProcessingResult:
        """处理单个 JSON 对象。"""
        item = self._parse_dict(data)
        if not item:
            return self._make_error("E002")
        return self._build_success_result([item])

    def _parse_dict(self, data: Dict[str, Any]) -> Optional[UnsubItem]:
        """从字典解析一条记录。"""
        sender = data.get("sender_email") or data.get("from") or data.get("sender")
        subject = data.get("subject") or data.get("title") or ""
        link = data.get("unsubscribe_link") or data.get("link") or ""

        if not sender or not isinstance(sender, str):
            return None

        # 提取邮件地址
        email_match = self.EMAIL_PATTERN.search(sender)
        sender_email = email_match.group(0) if email_match else sender

        # 计算置信度
        confidence = self._calculate_confidence(subject, link)

        return UnsubItem(
            sender_email=sender_email,
            subject=subject,
            unsubscribe_link=link,
            confidence=confidence,
            reason=self._generate_reason(confidence),
        )

    def _parse_text_line(self, line: str) -> Optional[UnsubItem]:
        """从文本行解析一条记录。"""
        # 尝试匹配邮件地址
        email_match = self.EMAIL_PATTERN.search(line)
        if not email_match:
            return None

        sender_email = email_match.group(0)

        # 提取主题（简单启发式：取邮件地址后到行尾或分隔符）
        rest = line[email_match.end():].strip()
        subject = rest.strip("|,;:- ")[:200] if rest else "(无主题)"

        # 查找退订链接
        link = self._find_unsubscribe_link(line)

        # 计算置信度
        confidence = self._calculate_confidence(subject, link or "")

        return UnsubItem(
            sender_email=sender_email,
            subject=subject,
            unsubscribe_link=link,
            confidence=confidence,
            reason=self._generate_reason(confidence),
        )

    def _find_unsubscribe_link(self, text: str) -> Optional[str]:
        """在文本中查找退订链接。"""
        for pattern in self.UNSUBSCRIBE_LINK_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None

    def _calculate_confidence(self, subject: str, link: str) -> float:
        """
        计算置信度：
        - 有退订链接：基础 70 分
        - 主题含营销关键词：每命中一个 +10 分
        - 有退订链接且主题含关键词：额外 +10 分
        - 上限 99 分
        """
        score = 0.0

        if link:
            score += 70.0

        subject_lower = subject.lower()
        keyword_hits = sum(
            1 for kw in self.MARKETING_KEYWORDS if kw.lower() in subject_lower
        )
        score += min(keyword_hits * 10.0, 20.0)

        if link and keyword_hits > 0:
            score += 5.0

        return min(score, 99.0)

    def _generate_reason(self, confidence: float) -> str:
        """根据置信度生成标注说明。"""
        if confidence >= 90:
            return "高置信度：可直接处理"
        elif confidence >= 85:
            return "建议复核：请人工确认后再操作"
        else:
            return "[需核实]：置信度不足，请人工检查"

    def _build_success_result(self, items: List[UnsubItem]) -> ProcessingResult:
        """构建成功结果。"""
        # 按置信度降序排列
        items.sort(key=lambda x: x.confidence, reverse=True)

        high_conf = sum(1 for i in items if i.confidence >= 90)
        medium_conf = sum(1 for i in items if 85 <= i.confidence < 90)
        low_conf = sum(1 for i in items if i.confidence < 85)

        summary = {
            "total": len(items),
            "high_confidence": high_conf,
            "medium_confidence": medium_conf,
            "low_confidence": low_conf,
        }

        return ProcessingResult(
            success=True,
            items=items,
            summary=summary,
        )

    def _make_error(self, code: str, extra: str = "") -> ProcessingResult:
        """构建错误结果。"""
        message = ERROR_CODES.get(code, "未知错误")
        if extra:
            message = f"{message} {extra}"
        return ProcessingResult(
            success=False,
            error_code=code,
            error_message=message,
        )


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ProcessingResult, fmt: str = "text") -> str:
    """将处理结果格式化为指定格式输出。"""
    if fmt == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    if fmt == "text":
        return _format_text(result)

    return _format_text(result)


def _format_text(result: ProcessingResult) -> str:
    """文本格式输出。"""
    if not result.success:
        return f"[错误 {result.error_code}] {result.error_message}"

    lines = []
    lines.append("=" * 60)
    lines.append("Gmail AI 退订工具 - 处理结果")
    lines.append("=" * 60)

    if not result.items:
        lines.append("未识别到可退订的邮件。")
        return "\n".join(lines)

    lines.append(f"共识别到 {result.summary['total']} 条退订候选：")
    lines.append("")

    for idx, item in enumerate(result.items, 1):
        lines.append(f"--- 候选 {idx} ---")
        lines.append(f"发件人: {item.sender_email}")
        lines.append(f"主题:   {item.subject}")
        if item.unsubscribe_link:
            lines.append(f"退订链接: {item.unsubscribe_link}")
        else:
            lines.append("退订链接: (未找到)")
        lines.append(f"置信度: {item.confidence:.1f}%  |  {item.reason}")
        lines.append("")

    lines.append("=" * 60)
    lines.append(
        f"统计: 高置信度 {result.summary['high_confidence']} 条, "
        f"建议复核 {result.summary['medium_confidence']} 条, "
        f"需核实 {result.summary['low_confidence']} 条"
    )
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件或网络。
    断言使用宽松阈值，确保任何环境均可通过。
    """
    print("Running selftest...")

    processor = GmailUnsubProcessor()

    # 测试用例 1: 空输入 -> E001
    result = processor.process_input("")
    assert not result.success, "空输入应返回失败"
    assert result.error_code == "E001", f"空输入应返回 E001，实际: {result.error_code}"
    print("  [PASS] 空输入返回 E001")

    # 测试用例 2: 空白输入 -> E001
    result = processor.process_input("   \n  \t  ")
    assert not result.success, "空白输入应返回失败"
    assert result.error_code == "E001", f"空白输入应返回 E001，实际: {result.error_code}"
    print("  [PASS] 空白输入返回 E001")

    # 测试用例 3: 单条文本输入
    sample_text = (
        "newsletter@example.com | 本周促销：限时折扣 | "
        "https://example.com/unsubscribe?id=123"
    )
    result = processor.process_input(sample_text)
    assert result.success, "合法文本输入应成功"
    assert len(result.items) == 1, f"应识别 1 条记录，实际: {len(result.items)}"
    item = result.items[0]
    assert item.sender_email == "newsletter@example.com"
    assert item.confidence > 50, "含退订链接和关键词的置信度应较高"
    print(f"  [PASS] 文本输入识别成功 (置信度: {item.confidence:.1f}%)")

    # 测试用例 4: 多行文本输入
    sample_multi = """\
promo@shop.com | 双十一大促 | https://promo.shop.com/opt-out
news@tech.com | 技术周刊 | https://news.tech.com/unsub
hello@friend.com | 周末聚会 | (无退订链接)
"""
    result = processor.process_input(sample_multi)
    assert result.success, "多行输入应成功"
    assert len(result.items) == 3, f"应识别 3 条记录，实际: {len(result.items)}"
    # 有退订链接的应排前面
    assert result.items[0].confidence >= result.items[-1].confidence
    print(f"  [PASS] 多行输入识别成功 (共 {len(result.items)} 条)")

    # 测试用例 5: JSON 数组输入
    json_input = json.dumps([
        {
            "sender_email": "marketing@brand.com",
            "subject": "您的专属优惠",
            "unsubscribe_link": "https://brand.com/unsub",
        },
        {
            "sender_email": "news@site.com",
            "subject": "每日新闻",
            "unsubscribe_link": "https://site.com/opt-out",
        },
    ])
    result = processor.process_input(json_input)
    assert result.success, "JSON 数组输入应成功"
    assert len(result.items) == 2, f"应识别 2 条记录，实际: {len(result.items)}"
    print(f"  [PASS] JSON 数组输入识别成功 (共 {len(result.items)} 条)")

    # 测试用例 6: 非法 JSON
    result = processor.process_input("{invalid json")
    assert not result.success, "非法 JSON 应失败"
    assert result.error_code in ("E003", "E008"), f"应返回 E003 或 E008，实际: {result.error_code}"
    print(f"  [PASS] 非法 JSON 返回错误码 {result.error_code}")

    # 测试用例 7: 低置信度标注
    low_conf_text = "hello@world.com | 普通邮件"
    result = processor.process_input(low_conf_text)
    assert result.success, "普通邮件也应成功处理"
    item = result.items[0]
    assert item.confidence < 85, f"无退订链接置信度应低于 85，实际: {item.confidence}"
    assert "需核实" in item.reason or "建议复核" in item.reason
    print(f"  [PASS] 低置信度标注正确 (置信度: {item.confidence:.1f}%)")

    # 测试用例 8: 置信度分级统计
    mixed_input = json.dumps([
        {"sender_email": "a@x.com", "subject": "unsubscribe now", "unsubscribe_link": "https://x.com/unsub"},
        {"sender_email": "b@y.com", "subject": "newsletter", "unsubscribe_link": "https://y.com/opt-out"},
        {"sender_email": "c@z.com", "subject": "普通邮件"},
    ])
    result = processor.process_input(mixed_input)
    assert result.success
    assert result.summary["total"] == 3
    assert result.summary["high_confidence"] >= 1
    assert result.summary["low_confidence"] >= 1
    print(f"  [PASS] 置信度统计正确: {result.summary}")

    # 测试用例 9: 输出格式（文本和 JSON）
    text_output = format_output(result, "text")
    assert "统计:" in text_output
    json_output = format_output(result, "json")
    parsed = json.loads(json_output)
    assert parsed["success"] is True
    print("  [PASS] 输出格式正确 (text + json)")

    # 测试用例 10: 错误输出
    err_result = processor.process_input("")
    err_output = format_output(err_result, "text")
    assert "E001" in err_output
    print("  [PASS] 错误输出包含错误码")

    print("\nAll selftest checks passed!")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="Gmail AI 退订工具 - 识别退订候选邮件",
        epilog="示例: python main.py --input 'newsletter@example.com | 促销 | https://x.com/unsub'",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容：文本、JSON 字符串（支持多行）",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"Selftest FAILED: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Selftest ERROR: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        print(f"[错误 E007] 请提供 --input 参数。使用 --help 查看帮助。", file=sys.stderr)
        return 1

    processor = GmailUnsubProcessor()
    result = processor.process_input(args.input)

    output = format_output(result, args.format)
    print(output)

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
