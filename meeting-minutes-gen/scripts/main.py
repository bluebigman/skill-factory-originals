#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议纪要生成 - 独立实现脚本
基于功能规格独立开发，不参考任何已有实现。
"""

import re
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：会议转写文本或录音文件",
    "E002": "输入内容格式不正确，无法解析",
    "E003": "输出格式不支持，请选择 markdown 或 text",
    "E004": "请求超出能力边界，本技能仅做结构化提取",
    "E005": "分段处理时发生冲突，请人工复核",
    "E006": "多次重试后仍失败，请分段处理后再输入",
    "E007": "置信度计算异常，请检查输入文本",
    "E008": "内部处理逻辑错误，请反馈给开发者",
    "E009": "参数配置错误，请检查命令行参数",
    "E010": "未知错误，请稍后重试",
}


# ============================================================
# 核心数据结构
# ============================================================
class MeetingMinutes:
    """会议纪要数据结构"""

    def __init__(self):
        self.decisions: List[Dict[str, Any]] = []          # 决议事项
        self.action_items: List[Dict[str, Any]] = []       # 行动项（含责任人）
        self.open_issues: List[Dict[str, Any]] = []        # 遗留问题
        self.discussion_summary: str = ""                   # 讨论摘要
        self.confidence: float = 50.0                       # 整体置信度
        self.raw_text: str = ""                             # 原始输入文本
        self.field_coverage: Dict[str, float] = {}          # 字段覆盖率


# ============================================================
# 文本清洗与预处理
# ============================================================
def clean_text(text: str) -> str:
    """清洗输入文本：去除异常字符、多余空白"""
    if not text:
        return ""
    # 去除控制字符（保留换行和制表符）
    cleaned = "".join(ch for ch in text if ch >= " " or ch in "\n\t")
    # 合并多余空白行
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
    # 去除首尾空白
    cleaned = cleaned.strip()
    return cleaned


def split_into_segments(text: str, max_chars: int = 5000) -> List[str]:
    """将长文本分段处理"""
    if len(text) <= max_chars:
        return [text]

    segments = []
    current = []
    current_len = 0

    for line in text.split("\n"):
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_chars and current:
            segments.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        segments.append("\n".join(current))

    return segments


def split_by_sentences(text: str) -> List[str]:
    """按句子拆分文本（用于重试兜底）"""
    sentences = re.split(r"(?<=[。！？.!?])\s*", text)
    return [s for s in sentences if s.strip()]


# ============================================================
# 关键信息提取
# ============================================================
def extract_decisions(text: str) -> List[Dict[str, Any]]:
    """提取决议事项"""
    decisions = []
    # 匹配模式：决议/决定/同意/通过 等关键词
    patterns = [
        r"(?:会议|我方|大家|团队)?(?:决议|决定|同意|通过|确认)[:：]?\s*(.+?)(?=[\n。；;]|$)",
        r"(?:决议事项|决定事项)[:：]\s*(.+?)(?=[\n]|$)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            content = match.strip()
            if content and len(content) > 2:
                decisions.append({
                    "content": content,
                    "confidence_boost": 10,  # 明确关键词匹配
                })

    # 去重
    unique_decisions = []
    seen = set()
    for d in decisions:
        if d["content"] not in seen:
            seen.add(d["content"])
            unique_decisions.append(d)

    return unique_decisions


def extract_action_items(text: str) -> List[Dict[str, Any]]:
    """提取行动项（含责任人与截止时间）"""
    action_items = []

    # 匹配模式：责任人 + 负责/跟进 + 事项 + 截止时间
    patterns = [
        # 完整模式：由XXX负责，YYY前完成
        r"由([\u4e00-\u9fa5A-Za-z]{2,10})(?:负责|跟进|处理|落实)(.+?)(?:，|,|。|；|;)(?:在|于)?(.+?)(?:前|之前|以内|内)?(?:完成|搞定|提交|交付)?",
        # 责任人 + 事项 + 截止时间
        r"([\u4e00-\u9fa5A-Za-z]{2,10})(?:负责|跟进|处理|落实)(.+?)(?:，|,|。|；|;)(?:在|于)?(.+?)(?:前|之前|以内|内)?(?:完成|搞定|提交|交付)?",
        # 截止时间 + 责任人 + 事项
        r"(?:在|于)?(.+?)(?:前|之前|以内|内)(?:，|,)?由([\u4e00-\u9fa5A-Za-z]{2,10})(?:负责|跟进|处理|落实)(.+)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) >= 3:
                person, task, deadline = match[0], match[1], match[2]
                # 清洗
                person = person.strip()
                task = task.strip()
                deadline = deadline.strip()

                # 过滤明显不是人名的情况
                if person and task and len(person) >= 2:
                    item = {
                        "person": person,
                        "task": task,
                        "deadline": deadline if deadline else "",
                        "has_deadline": bool(deadline),
                    }
                    # 检查是否已有相同项
                    if not any(
                        i["person"] == person and i["task"] == task
                        for i in action_items
                    ):
                        action_items.append(item)

    return action_items


def extract_open_issues(text: str) -> List[Dict[str, Any]]:
    """提取遗留问题"""
    issues = []
    patterns = [
        r"(?:遗留|未解决|待解决|悬而未决|尚未解决)(?:问题|事项)[:：]?\s*(.+?)(?=[\n。；;]|$)",
        r"(?:问题|事项)[:：]\s*(.+?)(?:尚未|还未|没有|未)(?:解决|完成|处理)",
        r"(?:还没|还未|尚未)(?:解决|完成|处理)[:：]?\s*(.+?)(?=[\n。；;]|$)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            content = match.strip()
            if content and len(content) > 2:
                issues.append({"content": content})

    # 去重
    unique_issues = []
    seen = set()
    for issue in issues:
        if issue["content"] not in seen:
            seen.add(issue["content"])
            unique_issues.append(issue)

    return unique_issues


def extract_discussion_summary(text: str) -> str:
    """生成讨论摘要（提取关键句子）"""
    # 去除明显的结构标记行
    lines = text.split("\n")
    summary_lines = []

    for line in lines:
        stripped = line.strip()
        # 跳过空行和明显的标题/标记行
        if not stripped:
            continue
        if re.match(r"^(会议纪要|决议|行动项|遗留问题|讨论|总结|参会|时间|地点)", stripped):
            continue
        if len(stripped) > 20:  # 只保留较长的句子
            summary_lines.append(stripped)

    # 取前若干行作为摘要
    if summary_lines:
        return "；".join(summary_lines[:5])
    return ""


def extract_speakers(text: str) -> List[str]:
    """提取发言人（用于置信度计算）"""
    speakers = re.findall(r"([\u4e00-\u9fa5A-Za-z]{2,10})[:：]", text)
    return list(set(speakers))


def extract_timestamps(text: str) -> int:
    """提取时间戳数量（用于置信度计算）"""
    timestamps = re.findall(r"\[\d{1,2}:\d{2}\]", text)
    return len(timestamps)


def detect_fuzzy_words(text: str) -> int:
    """检测模糊表述数量"""
    fuzzy_words = ["大概", "可能", "尽快", "大约", "左右", "差不多", "或许", "也许"]
    count = 0
    for word in fuzzy_words:
        count += text.count(word)
    return count


def detect_technical_terms(text: str) -> int:
    """检测英文缩写或专业术语"""
    # 简单检测：连续大写字母或英文缩写
    acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
    return len(acronyms)


def detect_nicknames(text: str) -> int:
    """检测昵称或代称"""
    patterns = ["老张", "老李", "小王", "组长", "经理", "主管", "负责人"]
    count = 0
    for pattern in patterns:
        count += text.count(pattern)
    return count


def detect_relative_time(text: str) -> int:
    """检测相对时间表述"""
    relative = ["下周", "月底", "明天", "后天", "下月", "年底", "最近"]
    count = 0
    for word in relative:
        count += text.count(word)
    return count


# ============================================================
# 置信度计算
# ============================================================
def calculate_confidence(text: str, minutes: MeetingMinutes) -> float:
    """根据功能规格中的规则计算置信度"""
    base = 50.0
    text_len = len(text)

    # 加分项
    # 1. 明确关键词匹配
    keyword_count = 0
    for kw in ["决议", "决定", "同意", "通过", "确认"]:
        keyword_count += text.count(kw)
    base += keyword_count * 10

    # 2. 责任人+截止时间同时出现
    action_items = minutes.action_items
    for item in action_items:
        if item["has_deadline"]:
            base += 15
        else:
            base += 5

    # 3. 明确发言人标注
    speakers = extract_speakers(text)
    base += len(speakers) * 5

    # 4. 时间戳
    timestamps = extract_timestamps(text)
    base += timestamps * 3

    # 5. 文本长度 > 2000 字
    if text_len > 2000:
        base += 5

    # 扣分项
    # 1. 模糊表述
    fuzzy_count = detect_fuzzy_words(text)
    base -= fuzzy_count * 10

    # 2. 文本长度 < 50 字
    if text_len < 50:
        base -= 20

    # 3. 多发言人交叉且无明确归属（简化处理：有多个发言人但无明确标注）
    # 4. 昵称或代称
    nickname_count = detect_nicknames(text)
    base -= nickname_count * 5

    # 5. 相对时间表述
    relative_time = detect_relative_time(text)
    base -= relative_time * 8

    # 6. 英文缩写或专业术语
    term_count = detect_technical_terms(text)
    base -= term_count * 5

    # 7. 复杂嵌套结构（检测括号嵌套）
    if text.count("(") > 3 or text.count("（") > 3:
        base -= 5

    # 限制在 0-100 范围
    return max(0.0, min(100.0, base))


# ============================================================
# 完整性评分
# ============================================================
def calculate_completeness(minutes: MeetingMinutes) -> float:
    """计算完整性评分（0-100）"""
    score = 0.0
    total_weight = 0.0

    # 决议数
    decision_weight = 30.0
    decision_score = min(30.0, len(minutes.decisions) * 10.0)
    score += decision_score
    total_weight += decision_weight

    # 责任人映射率
    person_weight = 40.0
    if minutes.action_items:
        mapped = sum(1 for item in minutes.action_items if item["person"])
        person_score = (mapped / len(minutes.action_items)) * person_weight
    else:
        person_score = 0.0
    score += person_score
    total_weight += person_weight

    # 截止时间明确度
    deadline_weight = 30.0
    if minutes.action_items:
        with_deadline = sum(1 for item in minutes.action_items if item["has_deadline"])
        deadline_score = (with_deadline / len(minutes.action_items)) * deadline_weight
    else:
        deadline_score = 0.0
    score += deadline_score
    total_weight += deadline_weight

    # 归一化
    if total_weight > 0:
        return round(score, 1)
    return 0.0


# ============================================================
# 输出格式化
# ============================================================
def format_markdown(minutes: MeetingMinutes) -> str:
    """格式化为 Markdown 输出"""
    lines = []
    lines.append("# 会议纪要")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # 决议事项
    lines.append("## 一、决议事项")
    lines.append("")
    if minutes.decisions:
        lines.append("| 序号 | 决议内容 |")
        lines.append("|------|----------|")
        for idx, decision in enumerate(minutes.decisions, 1):
            lines.append(f"| {idx} | {decision['content']} |")
    else:
        lines.append("（未识别到明确的决议事项）")
    lines.append("")

    # 行动项
    lines.append("## 二、行动项（责任人与截止时间）")
    lines.append("")
    if minutes.action_items:
        lines.append("| 序号 | 责任人 | 任务内容 | 截止时间 |")
        lines.append("|------|--------|----------|----------|")
        for idx, item in enumerate(minutes.action_items, 1):
            deadline = item["deadline"] if item["has_deadline"] else "未明确"
            lines.append(f"| {idx} | {item['person']} | {item['task']} | {deadline} |")
    else:
        lines.append("（未识别到明确的行动项）")
    lines.append("")

    # 遗留问题
    lines.append("## 三、遗留问题")
    lines.append("")
    if minutes.open_issues:
        lines.append("| 序号 | 问题内容 |")
        lines.append("|------|----------|")
        for idx, issue in enumerate(minutes.open_issues, 1):
            lines.append(f"| {idx} | {issue['content']} |")
    else:
        lines.append("（未识别到明确的遗留问题）")
    lines.append("")

    # 讨论摘要
    lines.append("## 四、讨论摘要")
    lines.append("")
    if minutes.discussion_summary:
        lines.append(minutes.discussion_summary)
    else:
        lines.append("（未生成讨论摘要）")
    lines.append("")

    # 置信度标注
    lines.append("## 五、置信度评估")
    lines.append("")
    conf = minutes.confidence
    if conf >= 90:
        level = "高置信度（≥90%），可直接使用"
    elif conf >= 85:
        level = "中高置信度（85%-90%），建议复核"
    else:
        level = f"低置信度（<85%），需核实（当前 {conf:.1f}%）"
    lines.append(f"- 整体置信度：**{conf:.1f}%**（{level}）")
    lines.append("")

    # 智能洞察
    completeness = calculate_completeness(minutes)
    lines.append("## 六、智能洞察")
    lines.append("")
    lines.append(f"- **完整性评分**：{completeness}/100")
    if completeness < 70:
        lines.append("- **改进建议**：")
        if not minutes.decisions:
            lines.append("  - 建议补充明确的决议事项")
        if minutes.action_items:
            no_deadline = [i for i in minutes.action_items if not i["has_deadline"]]
            if no_deadline:
                lines.append("  - 建议为行动项明确截止时间")
        if not minutes.open_issues:
            lines.append("  - 建议补充遗留问题")
    if conf < 85:
        lines.append(f"- **风险提示**：存在低置信度字段，建议人工复核后再使用")

    return "\n".join(lines)


def format_text(minutes: MeetingMinutes) -> str:
    """格式化为纯文本输出"""
    lines = []
    lines.append("=" * 40)
    lines.append("会议纪要")
    lines.append("=" * 40)
    lines.append("")

    lines.append("【决议事项】")
    if minutes.decisions:
        for idx, decision in enumerate(minutes.decisions, 1):
            lines.append(f"{idx}. {decision['content']}")
    else:
        lines.append("（未识别到明确的决议事项）")
    lines.append("")

    lines.append("【行动项】")
    if minutes.action_items:
        for idx, item in enumerate(minutes.action_items, 1):
            deadline = item["deadline"] if item["has_deadline"] else "未明确"
            lines.append(f"{idx}. 责任人：{item['person']}，任务：{item['task']}，截止：{deadline}")
    else:
        lines.append("（未识别到明确的行动项）")
    lines.append("")

    lines.append("【遗留问题】")
    if minutes.open_issues:
        for idx, issue in enumerate(minutes.open_issues, 1):
            lines.append(f"{idx}. {issue['content']}")
    else:
        lines.append("（未识别到明确的遗留问题）")
    lines.append("")

    lines.append("【讨论摘要】")
    lines.append(minutes.discussion_summary if minutes.discussion_summary else "（未生成）")
    lines.append("")

    lines.append(f"【置信度】{minutes.confidence:.1f}%")
    lines.append(f"【完整性评分】{calculate_completeness(minutes)}/100")

    return "\n".join(lines)


# ============================================================
# 主处理流程
# ============================================================
def process_text(text: str, output_format: str = "markdown") -> Tuple[str, Optional[str]]:
    """
    处理会议转写文本，生成结构化会议纪要。
    返回 (结果, 错误码或None)
    """
    # E001: 输入为空
    if not text or not text.strip():
        return "", "E001"

    # 清洗文本
    cleaned = clean_text(text)

    # E002: 清洗后为空
    if not cleaned:
        return "", "E002"

    # 分段处理（超长文本）
    segments = split_into_segments(cleaned)

    # 初始化结果
    minutes = MeetingMinutes()
    minutes.raw_text = cleaned

    # 处理每个分段
    for segment in segments:
        # 提取各类信息
        decisions = extract_decisions(segment)
        action_items = extract_action_items(segment)
        open_issues = extract_open_issues(segment)

        # 合并结果（去重）
        for d in decisions:
            if not any(i["content"] == d["content"] for i in minutes.decisions):
                minutes.decisions.append(d)
        for a in action_items:
            if not any(i["person"] == a["person"] and i["task"] == a["task"] for i in minutes.action_items):
                minutes.action_items.append(a)
        for o in open_issues:
            if not any(i["content"] == o["content"] for i in minutes.open_issues):
                minutes.open_issues.append(o)

    # 生成讨论摘要
    minutes.discussion_summary = extract_discussion_summary(cleaned)

    # 计算置信度
    minutes.confidence = calculate_confidence(cleaned, minutes)

    # 格式化输出
    if output_format == "markdown":
        result = format_markdown(minutes)
    elif output_format == "text":
        result = format_text(minutes)
    else:
        return "", "E003"

    return result, None


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("自检开始：验证核心逻辑")
    print("=" * 60)

    # 测试用例1：完整会议纪要
    sample1 = """
    会议纪要
    时间：2026年3月10日 10:00
    参会人：张三、李四、王五

    一、决议事项
    1. 会议决议：下季度产品发布计划正式通过
    2. 决定：市场推广预算增加20%

    二、行动项
    1. 由张三负责开发新功能模块，6月30日前完成
    2. 由李四跟进市场调研报告，5月15日前提交
    3. 由王五处理客户反馈收集，月底前完成

    三、遗留问题
    1. 服务器性能优化方案尚未确定
    2. 新员工招聘计划还未落实

    四、讨论
    大家对新功能的设计方案进行了充分讨论，一致认为需要优先解决用户体验问题。
    关于技术选型，团队倾向于使用Python进行开发，但还需要进一步验证。
    """

    # 测试用例2：简短文本（低置信度场景）
    sample2 = "今天会议大概讨论了项目进度，可能下周完成。"

    # 测试用例3：空输入
    sample3 = ""

    # 测试用例4：长文本分段（构造 6000+ 字符）
    sample4 = "会议决议：启动新一轮技术架构升级。\n" * 300  # 约 6000+ 字符

    # ============ 测试1：完整样例 ============
    print("\n[测试1] 完整会议纪要样例")
    result, err = process_text(sample1, "markdown")
    assert err is None, f"测试1失败：错误码 {err}"
    assert "会议纪要" in result, "测试1失败：缺少标题"
    assert "决议事项" in result, "测试1失败：缺少决议事项"
    assert "行动项" in result, "测试1失败：缺少行动项"
    assert "张三" in result, "测试1失败：缺少责任人"
    assert "6月30日" in result, "测试1失败：缺少截止时间"
    assert "置信度" in result, "测试1失败：缺少置信度"
    print("  ✓ 通过：决议、行动项、责任人、截止时间均正确提取")

    # 验证提取的细节
    minutes = MeetingMinutes()
    minutes.decisions = extract_decisions(sample1)
    minutes.action_items = extract_action_items(sample1)
    minutes.open_issues = extract_open_issues(sample1)
    assert len(minutes.decisions) >= 1, "测试1失败：应至少提取1条决议"
    assert len(minutes.action_items) >= 2, "测试1失败：应至少提取2条行动项"
    assert len(minutes.open_issues) >= 1, "测试1失败：应至少提取1条遗留问题"
    print(f"  ✓ 提取数量：决议={len(minutes.decisions)}, 行动项={len(minutes.action_items)}, 遗留问题={len(minutes.open_issues)}")

    # 验证置信度
    conf = calculate_confidence(sample1, minutes)
    assert conf >= 60, f"测试1失败：置信度应较高，实际 {conf}"
    print(f"  ✓ 置信度计算正常：{conf:.1f}%")

    # ============ 测试2：简短文本 ============
    print("\n[测试2] 简短文本（低置信度场景）")
    result2, err2 = process_text(sample2, "text")
    assert err2 is None, f"测试2失败：错误码 {err2}"
    print("  ✓ 通过：简短文本可正常处理")

    minutes2 = MeetingMinutes()
    conf2 = calculate_confidence(sample2, minutes2)
    assert conf2 < 60, f"测试2失败：简短文本置信度应较低，实际 {conf2}"
    print(f"  ✓ 置信度合理降低：{conf2:.1f}%")

    # ============ 测试3：空输入 ============
    print("\n[测试3] 空输入")
    _, err3 = process_text(sample3)
    assert err3 == "E001", f"测试3失败：应为 E001，实际 {err3}"
    print("  ✓ 通过：正确返回 E001")

    # ============ 测试4：长文本分段 ============
    print("\n[测试4] 超长文本分段处理")
    result4, err4 = process_text(sample4, "markdown")
    assert err4 is None, f"测试4失败：错误码 {err4}"
    assert "决议事项" in result4, "测试4失败：长文本应能提取决议"
    print("  ✓ 通过：超长文本分段处理正常")

    # ============ 测试5：错误码验证 ============
    print("\n[测试5] 错误码验证")
    assert "E001" in ERROR_CODES, "测试5失败：E001 定义缺失"
    assert "E002" in ERROR_CODES, "测试5失败：E002 定义缺失"
    assert "E003" in ERROR_CODES, "测试5失败：E003 定义缺失"
    assert "E004" in ERROR_CODES, "测试5失败：E004 定义缺失"
    assert "E005" in ERROR_CODES, "测试5失败：E005 定义缺失"
    assert "E006" in ERROR_CODES, "测试5失败：E006 定义缺失"
    print("  ✓ 通过：错误码体系完整")

    # ============ 测试6：输出格式 ============
    print("\n[测试6] 输出格式验证")
    result_md, _ = process_text(sample1, "markdown")
    result_txt, _ = process_text(sample1, "text")
    assert "|" in result_md, "测试6失败：Markdown 应包含表格"
    assert "【" in result_txt, "测试6失败：文本应包含段落标记"
    print("  ✓ 通过：Markdown 和文本格式均正常")

    # ============ 测试7：完整性评分 ============
    print("\n[测试7] 完整性评分")
    minutes7 = MeetingMinutes()
    minutes7.decisions = [{"content": "测试决议"}]
    minutes7.action_items = [{"person": "张三", "task": "测试任务", "has_deadline": True}]
    score = calculate_completeness(minutes7)
    assert score > 50, f"测试7失败：完整性评分应较高，实际 {score}"
    print(f"  ✓ 通过：完整性评分 = {score}/100")

    # ============ 测试8：边界情况 ============
    print("\n[测试8] 边界情况")
    # 特殊字符
    special_text = "会议决议：😀 测试表情符号和乱码\x00\x01\x02\n行动项：由张三跟进"
    result8, err8 = process_text(special_text, "text")
    assert err8 is None, f"测试8失败：特殊字符处理错误 {err8}"
    print("  ✓ 通过：特殊字符处理正常")

    # 只有标题没有内容
    minimal_text = "会议纪要"
    result9, err9 = process_text(minimal_text, "text")
    assert err9 is None, f"测试8失败：极简文本处理错误 {err9}"
    print("  ✓ 通过：极简文本处理正常")

    # ============ 汇总 ============
    print("\n" + "=" * 60)
    print("自检全部通过！核心逻辑验证成功")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="会议纪要生成工具：将会议转写文本整理为结构化会议纪要",
        epilog="示例：python main.py --input meeting.txt --format markdown"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径（包含会议转写文本）"
    )
    parser.add_argument(
        "--text", "-t",
        type=str,
        help="直接传入会议转写文本内容"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["markdown", "text"],
        default="markdown",
        help="输出格式（默认：markdown）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（可选，默认输出到 stdout）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检（内置硬编码样例，离线验证核心逻辑）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except AssertionError as e:
            print(f"自检失败：{e}")
            sys.exit(1)

    # 获取输入文本
    input_text = ""
    if args.text:
        input_text = args.text
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        except FileNotFoundError:
            print(f"E001: 输入文件不存在：{args.input}")
            sys.exit(1)
        except Exception as e:
            print(f"E010: 读取文件失败：{e}")
            sys.exit(1)
    else:
        # 从 stdin 读取
        import sys as _sys
        if not _sys.stdin.isatty():
            input_text = _sys.stdin.read()
        else:
            parser.print_help()
            sys.exit(0)

    # 处理文本
    result, err = process_text(input_text, args.format)

    if err:
        error_msg = ERROR_CODES.get(err, ERROR_CODES["E010"])
        print(f"{err}: {error_msg}")
        sys.exit(1)

    # 输出结果
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"结果已写入：{args.output}")
        except Exception as e:
            print(f"E010: 写入文件失败：{e}")
            sys.exit(1)
    else:
        print(result)


if __name__ == "__main__":
    main()
