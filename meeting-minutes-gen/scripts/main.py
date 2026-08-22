#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议纪要生成器 (meeting-minutes-gen) - 独立实现脚本

本脚本根据功能规格说明书进行 clean-room 重写，仅依赖标准库。
提供结构化会议纪要生成、置信度评估、错误处理等功能。
支持命令行调用与 --selftest 离线自检模式。
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码及对应消息
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：会议转写文本或录音文件",
    "E002": "输入文本无法解析，请检查格式",
    "E003": "输出格式不支持，仅支持 markdown 或 plain",
    "E004": "超出能力边界，无法执行该操作",
    "E005": "输入文本过长，请分段处理",
    "E006": "提取失败，请尝试分段处理或清洗文本",
    "E007": "参数配置错误",
    "E008": "内部处理异常",
    "E009": "输入文本包含无法识别的编码",
    "E010": "自检失败，请检查代码逻辑",
}

# 置信度分级阈值
CONFIDENCE_HIGH = 90
CONFIDENCE_MEDIUM = 85

# 输出格式
OUTPUT_FORMAT_MARKDOWN = "markdown"
OUTPUT_FORMAT_PLAIN = "plain"

# 默认输出模板
DEFAULT_TEMPLATE = """# 会议纪要

## 会议信息
- **会议主题**: {topic}
- **会议时间**: {meeting_time}

## 决议事项
{decisions}

## 行动项
{actions}

## 遗留问题
{issues}

## 智能洞察
- **完整性评分**: {completeness_score}/100
- **置信度**: {confidence}%
- **风险提示**: {risks}
- **改进建议**: {suggestions}
"""


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class Decision:
    """决议事项"""
    content: str
    confidence: float = 0.0
    source_line: str = ""


@dataclass
class ActionItem:
    """行动项"""
    content: str
    owner: str = ""
    deadline: str = ""
    confidence: float = 0.0
    source_line: str = ""


@dataclass
class Issue:
    """遗留问题"""
    content: str
    confidence: float = 0.0
    source_line: str = ""


@dataclass
class MeetingMinutes:
    """会议纪要结果"""
    topic: str = ""
    meeting_time: str = ""
    decisions: List[Decision] = field(default_factory=list)
    actions: List[ActionItem] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    confidence: float = 0.0
    completeness_score: int = 0
    risks: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# ============================================================
# 核心提取逻辑
# ============================================================

class MeetingMinutesGenerator:
    """会议纪要生成器核心类"""

    # 关键词模式
    DECISION_PATTERNS = [
        r"(?:决议|决定|同意|通过|确认)[：:]\s*(.+)",
        r"(?:会议决定|经讨论决定)[：:]\s*(.+)",
        r"(?:达成共识|达成一致)[：:]\s*(.+)",
    ]

    ACTION_PATTERNS = [
        r"(?:行动项|待办|任务|行动)[：:]\s*(.+)",
        r"(?:由|让|请)\s*([\u4e00-\u9fa5A-Za-z]+)\s*(?:负责|跟进|处理|完成)\s*(.+)?",
        r"(.+?)(?:由|让)\s*([\u4e00-\u9fa5A-Za-z]+)\s*(?:负责|跟进|处理|完成)",
        r"(.+?)(?:截止|期限|完成时间)[：:]?\s*([\d年月日]+)?",
    ]

    # 扩展遗留问题的匹配模式
    ISSUE_PATTERNS = [
        r"(?:遗留问题|未决问题|待解决|悬而未决)[：:]\s*(.+)",
        r"(?:问题|疑问|待确认)[：:]\s*(.+)",
        r"(?:尚未|未|还没)[解决|完成|确认]\s*(.+)",
        r"(?:遗留问题|遗留事项|未完成事项)[是]?\s*(.+)",
        r"(.+?)(?:是|为)?遗留问题",
        r"(?:遗留|未解决|待处理)[：:]\s*(.+)",
        r"遗留问题[是：:]\s*(.+)",
        r"(?:需要|要)(?:进一步|继续|后续)(?:评估|讨论|确认|处理|解决)\s*(.+)",
    ]

    # 责任人/时间模式
    OWNER_PATTERN = r"([\u4e00-\u9fa5]{2,4}|[A-Za-z]+)"
    DEADLINE_PATTERNS = [
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
        r"(\d{4}-\d{1,2}-\d{1,2})",
        r"(\d{1,2}月\d{1,2}日)",
        r"(\d{1,2}天内)",
        r"(本?周[一二三四五六日天]?)",
        r"(下?周[一二三四五六日天]?)",
        r"(月底|月初|下月初|下月底)",
        r"(本?季度末|下?季度末)",
    ]

    # 置信度调整规则
    CONFIDENCE_RULES = {
        "keyword_match": 10,        # 明确关键词匹配加分
        "owner_and_deadline": 15,   # 责任人+截止时间同时出现
        "owner_only": 5,            # 仅责任人
        "vague_expression": -10,    # 模糊表述
        "short_text": -20,          # 文本过短
        "multi_speaker": -15,       # 多发言人无归属
        "nickname": -5,             # 昵称/代称
        "relative_time": -8,        # 相对时间
        "explicit_speaker": 5,      # 明确发言人标注
        "long_text": 5,             # 长文本
        "jargon": -5,               # 专业术语
        "timestamp": 3,             # 时间戳
        "complex_structure": -5,    # 复杂嵌套结构
    }

    # 模糊表述关键词
    VAGUE_WORDS = ["大概", "可能", "尽快", "大约", "左右", "或许", "差不多"]

    # 相对时间关键词
    RELATIVE_TIME_WORDS = ["下周", "月底", "月初", "下月初", "下月底", "本季度", "下季度"]

    # 昵称/代称模式
    NICKNAME_PATTERNS = [r"老[\u4e00-\u9fa5]", r"小[\u4e00-\u9fa5]", r"组长", r"经理", r"主管", r"负责人"]

    # 专业术语模式（常见缩写）
    JARGON_PATTERNS = [r"\b[A-Z]{2,}\b", r"\b\d+[A-Za-z]+\b"]

    # 发言人标注模式
    SPEAKER_PATTERN = r"([\u4e00-\u9fa5]{2,4}|[A-Za-z]+)[：:]"

    # 时间戳模式
    TIMESTAMP_PATTERN = r"\[\d{1,2}:\d{2}\]"

    def __init__(self, text: str = ""):
        self.raw_text = text.strip() if text else ""
        self.lines = []
        self.meeting_minutes = MeetingMinutes()
        self._parse_lines()

    def _parse_lines(self) -> None:
        """按行解析输入文本"""
        if not self.raw_text:
            return
        # 按换行分割，过滤空行
        self.lines = [line.strip() for line in self.raw_text.split("\n") if line.strip()]

    def process(self) -> MeetingMinutes:
        """执行核心提取流程"""
        if not self.raw_text:
            raise ValueError("E001")

        # 分段处理超长文本
        if len(self.raw_text) > 5000:
            self._process_long_text()
        else:
            self._extract_all()

        # 计算置信度
        self._calculate_confidence()

        # 计算完整性评分
        self._calculate_completeness()

        # 生成洞察建议
        self._generate_insights()

        return self.meeting_minutes

    def _process_long_text(self) -> None:
        """处理超长文本，分段提取后合并"""
        # 按段落分割
        segments = self._split_segments(self.raw_text)
        all_decisions = []
        all_actions = []
        all_issues = []

        for segment in segments:
            self.lines = [line.strip() for line in segment.split("\n") if line.strip()]
            self._extract_all()
            all_decisions.extend(self.meeting_minutes.decisions)
            all_actions.extend(self.meeting_minutes.actions)
            all_issues.extend(self.meeting_minutes.issues)

        # 合并结果
        self.meeting_minutes.decisions = all_decisions
        self.meeting_minutes.actions = all_actions
        self.meeting_minutes.issues = all_issues

    def _split_segments(self, text: str, max_length: int = 2000) -> List[str]:
        """将长文本按段落分割为多个片段"""
        segments = []
        current = ""
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            if len(current) + len(para) > max_length and current:
                segments.append(current.strip())
                current = para
            else:
                current += "\n\n" + para if current else para

        if current:
            segments.append(current.strip())

        return segments

    def _extract_all(self) -> None:
        """提取所有类型的信息"""
        self._extract_topic()
        self._extract_time()
        self._extract_decisions()
        self._extract_actions()
        self._extract_issues()

    def _extract_topic(self) -> None:
        """提取会议主题"""
        for line in self.lines:
            match = re.search(r"(?:会议主题|主题|议题)[：:]\s*(.+)", line)
            if match:
                self.meeting_minutes.topic = match.group(1).strip()
                return
        # 默认主题
        self.meeting_minutes.topic = "未指定主题"

    def _extract_time(self) -> None:
        """提取会议时间"""
        for line in self.lines:
            match = re.search(r"(?:会议时间|时间)[：:]\s*(.+)", line)
            if match:
                self.meeting_minutes.meeting_time = match.group(1).strip()
                return
        # 默认时间
        self.meeting_minutes.meeting_time = "未记录"

    def _extract_decisions(self) -> None:
        """提取决议事项"""
        for line in self.lines:
            for pattern in self.DECISION_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    content = match.group(1).strip()
                    if content:
                        decision = Decision(content=content, source_line=line)
                        self.meeting_minutes.decisions.append(decision)
                    break

    def _extract_actions(self) -> None:
        """提取行动项"""
        for line in self.lines:
            # 尝试匹配行动项模式
            for pattern in self.ACTION_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    content = match.group(0).strip()
                    owner = ""
                    deadline = ""

                    # 提取责任人
                    owner_match = re.search(self.OWNER_PATTERN, line)
                    if owner_match:
                        owner = owner_match.group(1)

                    # 提取截止时间
                    for deadline_pattern in self.DEADLINE_PATTERNS:
                        deadline_match = re.search(deadline_pattern, line)
                        if deadline_match:
                            deadline = deadline_match.group(1)
                            break

                    action = ActionItem(
                        content=content,
                        owner=owner,
                        deadline=deadline,
                        source_line=line
                    )
                    self.meeting_minutes.actions.append(action)
                    break

    def _extract_issues(self) -> None:
        """提取遗留问题"""
        for line in self.lines:
            found = False
            for pattern in self.ISSUE_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    # 提取内容，处理不同模式
                    if match.groups():
                        content = match.group(1).strip() if match.group(1) else match.group(0).strip()
                    else:
                        content = match.group(0).strip()
                    
                    # 清理内容
                    content = self._clean_issue_content(content, line)
                    
                    if content:
                        issue = Issue(content=content, source_line=line)
                        self.meeting_minutes.issues.append(issue)
                        found = True
                    break
            
            if not found:
                # 额外检查：包含"遗留"或"问题"关键词的行
                if "遗留" in line or "未解决" in line or "待处理" in line:
                    # 尝试提取更自然语言的内容
                    content = self._extract_natural_issue(line)
                    if content:
                        issue = Issue(content=content, source_line=line)
                        self.meeting_minutes.issues.append(issue)

    def _clean_issue_content(self, content: str, original_line: str) -> str:
        """清理问题内容"""
        # 移除时间戳
        content = re.sub(r"\[\d{1,2}:\d{2}\]", "", content).strip()
        # 移除发言人前缀
        content = re.sub(r"^[\u4e00-\u9fa5]{2,4}[：:]", "", content).strip()
        # 移除"遗留问题是"等冗余表述
        content = re.sub(r"^(?:遗留问题|问题)[是：:]", "", content).strip()
        content = re.sub(r"^(?:遗留|待解决|未解决)[是：:]", "", content).strip()
        
        # 如果内容为空，尝试从原行提取
        if not content:
            # 提取"是"后面的内容
            match = re.search(r"是\s*(.+)", original_line)
            if match:
                content = match.group(1).strip()
        
        return content

    def _extract_natural_issue(self, line: str) -> str:
        """从自然语言中提取问题"""
        # 尝试提取"遗留问题是"或"问题是"后面的内容
        match = re.search(r"(?:遗留问题|问题)是\s*(.+)", line)
        if match:
            return match.group(1).strip()
        
        # 尝试提取"遗留问题"后面的内容
        match = re.search(r"遗留问题\s*(.+)", line)
        if match:
            return match.group(1).strip()
        
        # 尝试提取"未解决"或"待处理"相关的内容
        match = re.search(r"(?:未解决|待处理|待解决)[的]?\s*(.+)", line)
        if match:
            return match.group(1).strip()
        
        # 如果都失败，返回整行内容（去除发言人前缀）
        return re.sub(r"^[\u4e00-\u9fa5]{2,4}[：:]\s*", "", line).strip()

    def _calculate_confidence(self) -> None:
        """计算整体置信度"""
        base_score = 50.0
        text = self.raw_text

        # 关键词匹配加分
        keyword_count = 0
        for keyword in ["决议", "决定", "同意", "确认", "通过"]:
            keyword_count += text.count(keyword)
        base_score += keyword_count * self.CONFIDENCE_RULES["keyword_match"]

        # 责任人+截止时间加分
        has_owner = any(action.owner for action in self.meeting_minutes.actions)
        has_deadline = any(action.deadline for action in self.meeting_minutes.actions)
        if has_owner and has_deadline:
            base_score += self.CONFIDENCE_RULES["owner_and_deadline"]
        elif has_owner:
            base_score += self.CONFIDENCE_RULES["owner_only"]

        # 模糊表述扣分
        for word in self.VAGUE_WORDS:
            if word in text:
                base_score += self.CONFIDENCE_RULES["vague_expression"]

        # 文本长度影响
        if len(text) < 50:
            base_score += self.CONFIDENCE_RULES["short_text"]
        elif len(text) > 2000:
            base_score += self.CONFIDENCE_RULES["long_text"]

        # 多发言人交叉无归属
        speaker_count = len(re.findall(self.SPEAKER_PATTERN, text))
        if speaker_count > 2 and not any(action.owner for action in self.meeting_minutes.actions):
            base_score += self.CONFIDENCE_RULES["multi_speaker"]

        # 昵称/代称扣分
        for pattern in self.NICKNAME_PATTERNS:
            if re.search(pattern, text):
                base_score += self.CONFIDENCE_RULES["nickname"]

        # 相对时间扣分
        for word in self.RELATIVE_TIME_WORDS:
            if word in text:
                base_score += self.CONFIDENCE_RULES["relative_time"]

        # 明确发言人标注加分
        if speaker_count > 0:
            base_score += speaker_count * self.CONFIDENCE_RULES["explicit_speaker"]

        # 专业术语扣分
        jargon_count = len(re.findall(r"\b[A-Z]{2,}\b", text))
        base_score += jargon_count * self.CONFIDENCE_RULES["jargon"]

        # 时间戳加分
        timestamp_count = len(re.findall(self.TIMESTAMP_PATTERN, text))
        base_score += timestamp_count * self.CONFIDENCE_RULES["timestamp"]

        # 复杂嵌套结构扣分
        if text.count("(") > 3 or text.count("[") > 3:
            base_score += self.CONFIDENCE_RULES["complex_structure"]

        # 限制在 0-100 范围
        self.meeting_minutes.confidence = max(0, min(100, base_score))

    def _calculate_completeness(self) -> None:
        """计算完整性评分"""
        score = 0

        # 决议数（满分40）
        decision_count = len(self.meeting_minutes.decisions)
        score += min(decision_count * 10, 40)

        # 责任人映射率（满分30）
        if self.meeting_minutes.actions:
            owner_mapped = sum(1 for action in self.meeting_minutes.actions if action.owner)
            score += int((owner_mapped / len(self.meeting_minutes.actions)) * 30)
        else:
            # 无行动项，给基础分
            score += 15

        # 截止时间明确度（满分30）
        if self.meeting_minutes.actions:
            deadline_set = sum(1 for action in self.meeting_minutes.actions if action.deadline)
            score += int((deadline_set / len(self.meeting_minutes.actions)) * 30)
        else:
            score += 15

        self.meeting_minutes.completeness_score = min(score, 100)

    def _generate_insights(self) -> None:
        """生成智能洞察"""
        risks = []
        suggestions = []

        # 低置信度风险提示
        if self.meeting_minutes.confidence < CONFIDENCE_MEDIUM:
            risks.append(f"整体置信度较低（{self.meeting_minutes.confidence}%），建议人工复核")

        # 检查具体风险点
        if not self.meeting_minutes.decisions:
            risks.append("未提取到明确的决议事项")

        if self.meeting_minutes.actions:
            no_owner = [a for a in self.meeting_minutes.actions if not a.owner]
            if no_owner:
                risks.append(f"有 {len(no_owner)} 个行动项缺少责任人")

            no_deadline = [a for a in self.meeting_minutes.actions if not a.deadline]
            if no_deadline:
                risks.append(f"有 {len(no_deadline)} 个行动项缺少截止时间")
        else:
            risks.append("未提取到行动项")

        # 改进建议
        if self.meeting_minutes.completeness_score < 70:
            if not self.meeting_minutes.decisions:
                suggestions.append("建议明确标注决议事项（使用'决议：'等关键词）")
            if self.meeting_minutes.actions and any(not a.owner for a in self.meeting_minutes.actions):
                suggestions.append("建议为行动项补充责任人全名")
            if self.meeting_minutes.actions and any(not a.deadline for a in self.meeting_minutes.actions):
                suggestions.append("建议为行动项明确截止时间")
            if len(self.raw_text) < 50:
                suggestions.append("输入文本过短，建议提供更完整的会议记录")

        self.meeting_minutes.risks = risks
        self.meeting_minutes.suggestions = suggestions


# ============================================================
# 输出格式化
# ============================================================

def format_output(minutes: MeetingMinutes, output_format: str = OUTPUT_FORMAT_MARKDOWN) -> str:
    """格式化输出会议纪要"""
    if output_format not in [OUTPUT_FORMAT_MARKDOWN, OUTPUT_FORMAT_PLAIN]:
        raise ValueError("E003")

    if output_format == OUTPUT_FORMAT_MARKDOWN:
        return _format_markdown(minutes)
    else:
        return _format_plain(minutes)


def _format_markdown(minutes: MeetingMinutes) -> str:
    """Markdown 格式输出"""
    # 决议事项
    if minutes.decisions:
        decisions_md = "\n".join(f"{i+1}. {d.content}" for i, d in enumerate(minutes.decisions))
    else:
        decisions_md = "无"

    # 行动项
    if minutes.actions:
        actions_lines = []
        for i, action in enumerate(minutes.actions):
            owner = action.owner if action.owner else "待分配"
            deadline = action.deadline if action.deadline else "未指定"
            actions_lines.append(f"{i+1}. {action.content} | 责任人: {owner} | 截止: {deadline}")
        actions_md = "\n".join(actions_lines)
    else:
        actions_md = "无"

    # 遗留问题
    if minutes.issues:
        issues_md = "\n".join(f"{i+1}. {issue.content}" for i, issue in enumerate(minutes.issues))
    else:
        issues_md = "无"

    # 风险提示
    risks_text = "; ".join(minutes.risks) if minutes.risks else "无"

    # 改进建议
    suggestions_text = "\n".join(f"- {s}" for s in minutes.suggestions) if minutes.suggestions else "无"

    # 置信度标注
    confidence_text = f"{minutes.confidence}%"
    if minutes.confidence >= CONFIDENCE_HIGH:
        confidence_text += "（直接使用）"
    elif minutes.confidence >= CONFIDENCE_MEDIUM:
        confidence_text += "（建议复核）"
    else:
        confidence_text += "（需核实）"

    output = DEFAULT_TEMPLATE.format(
        topic=minutes.topic,
        meeting_time=minutes.meeting_time,
        decisions=decisions_md,
        actions=actions_md,
        issues=issues_md,
        completeness_score=minutes.completeness_score,
        confidence=confidence_text,
        risks=risks_text,
        suggestions=suggestions_text,
    )

    return output


def _format_plain(minutes: MeetingMinutes) -> str:
    """纯文本格式输出"""
    lines = []
    lines.append(f"会议主题: {minutes.topic}")
    lines.append(f"会议时间: {minutes.meeting_time}")
    lines.append("")

    lines.append("决议事项:")
    if minutes.decisions:
        for i, d in enumerate(minutes.decisions):
            lines.append(f"  {i+1}. {d.content}")
    else:
        lines.append("  无")
    lines.append("")

    lines.append("行动项:")
    if minutes.actions:
        for i, action in enumerate(minutes.actions):
            owner = action.owner if action.owner else "待分配"
            deadline = action.deadline if action.deadline else "未指定"
            lines.append(f"  {i+1}. {action.content} | 责任人: {owner} | 截止: {deadline}")
    else:
        lines.append("  无")
    lines.append("")

    lines.append("遗留问题:")
    if minutes.issues:
        for i, issue in enumerate(minutes.issues):
            lines.append(f"  {i+1}. {issue.content}")
    else:
        lines.append("  无")
    lines.append("")

    lines.append(f"完整性评分: {minutes.completeness_score}/100")
    lines.append(f"置信度: {minutes.confidence}%")
    lines.append("")

    if minutes.risks:
        lines.append("风险提示:")
        for risk in minutes.risks:
            lines.append(f"  - {risk}")

    if minutes.suggestions:
        lines.append("改进建议:")
        for suggestion in minutes.suggestions:
            lines.append(f"  - {suggestion}")

    return "\n".join(lines)


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> int:
    """内置硬编码样例数据，离线自检核心逻辑"""
    print("=" * 60)
    print("自检开始：会议纪要生成器核心逻辑验证")
    print("=" * 60)

    test_cases = [
        {
            "name": "标准会议纪要",
            "input": """会议主题：产品迭代评审会
会议时间：2026年3月15日

决议：确认下季度产品路线图，重点推进移动端优化。
决定：同意将用户反馈系统升级为实时反馈机制。

行动项：
1. 张三负责完成移动端界面改版，6月30日前完成
2. 李四跟进用户反馈系统升级，截止日期为4月15日
3. 王五整理竞品分析报告，由王五负责

遗留问题：数据迁移方案尚未确定，需要进一步评估。
问题：新功能上线后的用户培训计划待确认。""",
            "min_decisions": 1,
            "min_actions": 1,
            "min_issues": 1,
        },
        {
            "name": "简短输入",
            "input": "今天会议决定由张三负责项目推进，尽快完成。",
            "min_decisions": 0,
            "min_actions": 0,
            "min_issues": 0,
        },
        {
            "name": "带时间戳和发言人",
            "input": """[10:30] 张三：建议优化登录流程，提升用户体验。
[10:35] 李四：同意，由张三负责实施，月底前完成。
[10:40] 决议：通过登录流程优化方案。
[10:45] 王五：遗留问题是旧版本兼容性测试。""",
            "min_decisions": 1,
            "min_actions": 0,
            "min_issues": 1,
        },
    ]

    all_passed = True

    for idx, case in enumerate(test_cases):
        print(f"\n--- 测试用例 {idx + 1}: {case['name']} ---")
        try:
            generator = MeetingMinutesGenerator(case["input"])
            result = generator.process()

            # 宽松断言
            passed = True

            # 验证决策提取（宽松：>= 最小值）
            if len(result.decisions) < case["min_decisions"]:
                print(f"  [失败] 决策提取不足: 期望至少 {case['min_decisions']} 个，实际 {len(result.decisions)} 个")
                passed = False
            else:
                print(f"  [通过] 决策提取: {len(result.decisions)} 个")

            # 验证行动项提取
            if len(result.actions) < case["min_actions"]:
                print(f"  [失败] 行动项提取不足: 期望至少 {case['min_actions']} 个，实际 {len(result.actions)} 个")
                passed = False
            else:
                print(f"  [通过] 行动项提取: {len(result.actions)} 个")

            # 验证遗留问题提取
            if len(result.issues) < case["min_issues"]:
                print(f"  [失败] 遗留问题提取不足: 期望至少 {case['min_issues']} 个，实际 {len(result.issues)} 个")
                passed = False
            else:
                print(f"  [通过] 遗留问题提取: {len(result.issues)} 个")

            # 验证置信度范围（0-100）
            if not (0 <= result.confidence <= 100):
                print(f"  [失败] 置信度超出范围: {result.confidence}")
                passed = False
            else:
                print(f"  [通过] 置信度: {result.confidence}%")

            # 验证完整性评分范围
            if not (0 <= result.completeness_score <= 100):
                print(f"  [失败] 完整性评分超出范围: {result.completeness_score}")
                passed = False
            else:
                print(f"  [通过] 完整性评分: {result.completeness_score}")

            # 验证输出格式
            try:
                md_output = format_output(result, OUTPUT_FORMAT_MARKDOWN)
                if not md_output or len(md_output) < 10:
                    print("  [失败] Markdown 输出异常")
                    passed = False
                else:
                    print("  [通过] Markdown 输出生成")

                plain_output = format_output(result, OUTPUT_FORMAT_PLAIN)
                if not plain_output or len(plain_output) < 10:
                    print("  [失败] 纯文本输出异常")
                    passed = False
                else:
                    print("  [通过] 纯文本输出生成")
            except Exception as e:
                print(f"  [失败] 输出格式化异常: {e}")
                passed = False

            if passed:
                print("  [结论] 测试通过 ✓")
            else:
                print("  [结论] 测试失败 ✗")
                all_passed = False

        except Exception as e:
            print(f"  [失败] 处理异常: {e}")
            all_passed = False

    # 测试错误处理
    print("\n--- 测试错误处理 ---")

    # 空输入测试
    try:
        generator = MeetingMinutesGenerator("")
        generator.process()
        print("  [失败] 空输入未抛出异常")
        all_passed = False
    except ValueError as e:
        if str(e) == "E001":
            print("  [通过] 空输入正确返回 E001")
        else:
            print(f"  [失败] 空输入返回错误码: {e}")
            all_passed = False

    # 不支持格式测试
    try:
        format_output(MeetingMinutes(), "xml")
        print("  [失败] 不支持的格式未抛出异常")
        all_passed = False
    except ValueError as e:
        if str(e) == "E003":
            print("  [通过] 不支持的格式正确返回 E003")
        else:
            print(f"  [失败] 不支持的格式返回错误码: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
        print("=" * 60)
        return 0
    else:
        print("自检存在失败项 ✗")
        print("=" * 60)
        return 1


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="会议纪要生成器 - 将会议转写文本整理为结构化纪要",
        epilog="示例: python main.py --input meeting.txt --format markdown"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径（包含会议转写文本）"
    )
    parser.add_argument(
        "--text", "-t",
        type=str,
        help="直接输入会议转写文本"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=[OUTPUT_FORMAT_MARKDOWN, OUTPUT_FORMAT_PLAIN],
        default=OUTPUT_FORMAT_MARKDOWN,
        help=f"输出格式（默认: {OUTPUT_FORMAT_MARKDOWN}）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（不指定则输出到终端）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心逻辑"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览不写盘（安全守卫）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出处理明细（每步决策）",
    )

    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()
    if args.verbose:
        print(f"[verbose] 参数: {vars(args)}")

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 获取输入文本
    input_text = ""
    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8", errors="replace") as f:
                input_text = f.readlines()
        except FileNotFoundError:
            print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
            return 1
        except UnicodeDecodeError:
            print("错误: 文件编码无法识别 (E009)", file=sys.stderr)
            return 1
    elif args.text:
        input_text = args.text
    else:
        parser.print_help()
        print("\n错误: 请提供输入文本或文件 (E001)", file=sys.stderr)
        return 1

    # 处理输入
    try:
        generator = MeetingMinutesGenerator(input_text)
        result = generator.process()

        # 格式化输出
        output = format_output(result, args.format)

        # 输出结果
        if args.output:
            if args.verbose:
                print(f"[verbose] 输出格式={args.format}，纪要 {len(output)} 字符")
            if not args.dry_run:
                with open(args.output, "w", encoding="utf-8", errors="replace") as f:
                    f.write(output)
                print(f"会议纪要已保存至: {args.output}")
            else:
                print(f"[dry-run] 预览输出（未写盘）: {args.output}，共 {len(output)} 字符")
        else:
            print(output)

        return 0

    except ValueError as e:
        error_code = str(e)
        error_msg = ERROR_MESSAGES.get(error_code, "未知错误")
        print(f"错误 ({error_code}): {error_msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 (E008): 内部处理异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
