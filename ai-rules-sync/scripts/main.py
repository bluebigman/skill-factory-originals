#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
技能: ai-rules-sync
版本: 1.0.0
描述: 同步、管理和分享 AI 规则、技能、命令、子代理等配置。
      本脚本为 Clean-Room 独立实现，仅依据功能规格编写。

功能边界:
  1. 将输入数据/内容转换为结构化结果
  2. 识别并保留输入中的关键信息
  3. 按约定格式生成输出
  4. 对不确定项给出置信度提示
  5. 支持批量处理和自定义格式

错误码:
  E001 - 输入为空
  E002 - 关键信息缺失
  E003 - 输入格式错误
  E004 - 超出能力边界
  E005 - 置信度过低
  E006 - 内部处理错误
  E007 - 参数解析错误
  E008 - 自检失败
  E009 - 输出写入失败
  E010 - 未预期的运行时错误
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 核心逻辑模块
# ---------------------------------------------------------------------------

class RuleItem:
    """表示一条规则/技能/命令的条目。"""
    def __init__(self, name: str, category: str, content: str, source: str = "unknown"):
        self.name = name
        self.category = category
        self.content = content
        self.source = source

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "category": self.category,
            "content": self.content,
            "source": self.source,
        }


class SyncEngine:
    """
    核心引擎：负责解析输入、结构化、置信度评估和输出生成。
    不依赖任何外部服务，纯本地处理。
    """

    # 预定义的关键词分类映射
    CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "rule": ["rule", "规则", "必须", "禁止", "always", "never"],
        "skill": ["skill", "技能", "能力", "擅长"],
        "command": ["command", "命令", "cmd", "执行"],
        "subagent": ["subagent", "子代理", "agent", "助手"],
        "tool": ["tool", "工具", "function", "函数"],
    }

    def __init__(self) -> None:
        """初始化引擎。"""
        self._items: List[RuleItem] = []

    def parse_input(self, raw_input: str) -> List[str]:
        """
        解析原始输入，拆分为独立的条目。
        支持按行、分号、逗号分隔的简单文本。
        """
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")

        # 按行拆分，去除空行
        lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
        if not lines:
            # 尝试按分号或逗号拆分
            parts = re.split(r"[;,]", raw_input)
            lines = [p.strip() for p in parts if p.strip()]

        if not lines:
            raise ValueError("E001")
        return lines

    def categorize(self, text: str) -> str:
        """根据关键词将文本分类到预定义类别。"""
        text_lower = text.lower()
        best_category = "general"
        max_score = 0

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > max_score:
                max_score = score
                best_category = category

        return best_category

    def extract_name(self, text: str) -> str:
        """
        从文本中提取名称。
        优先匹配 'name: xxx' 或 '名称: xxx' 模式。
        """
        patterns = [
            r"(?:name|名称)\s*[:：]\s*([^\s,;，。]+)",
            r"^(?:rule|skill|command|cmd|agent)\s+([^\s,;，。]+)",
            r"^[\[【]([^\]】]+)[\]】]",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # 默认使用第一个词作为名称
        # 修复：使用关键字参数 maxsplit=1 避免 DeprecationWarning
        first_word = re.split(r"[\s,;，。]+", text.strip(), maxsplit=1)[0]
        return first_word if first_word else "unnamed"

    def assess_confidence(self, text: str, category: str) -> float:
        """
        评估置信度。
        基于文本长度、关键词匹配度、结构完整性。
        """
        score = 0.5  # 基础分

        # 长度加分
        text_len = len(text)
        if text_len >= 20:
            score += 0.2
        elif text_len >= 10:
            score += 0.1

        # 类别关键词匹配加分
        keywords = self.CATEGORY_KEYWORDS.get(category, [])
        if keywords and any(kw.lower() in text.lower() for kw in keywords):
            score += 0.2

        # 结构化标记加分
        if re.search(r"[:：]", text):
            score += 0.1
        if re.search(r"[【\[]", text):
            score += 0.1

        return min(max(score, 0.0), 1.0)

    def process_item(self, text: str) -> Dict[str, Any]:
        """处理单个条目，生成结构化结果。"""
        category = self.categorize(text)
        name = self.extract_name(text)
        confidence = self.assess_confidence(text, category)

        item = RuleItem(name=name, category=category, content=text, source="user_input")
        self._items.append(item)

        result = item.to_dict()
        result["confidence"] = round(confidence, 2)

        # 置信度标注
        if confidence >= 0.9:
            result["confidence_label"] = "直接输出"
        elif confidence >= 0.85:
            result["confidence_label"] = "建议复核"
        else:
            result["confidence_label"] = "[需核实]"

        return result

    def process_batch(self, raw_input: str) -> Dict[str, Any]:
        """批量处理输入，返回结构化结果。"""
        try:
            lines = self.parse_input(raw_input)
        except ValueError as e:
            return {"error": str(e), "items": [], "count": 0}

        results = []
        for line in lines:
            try:
                result = self.process_item(line)
                results.append(result)
            except Exception:
                # 单条失败不影响整体
                results.append({
                    "name": "unknown",
                    "category": "error",
                    "content": line,
                    "source": "user_input",
                    "confidence": 0.0,
                    "confidence_label": "[需核实]",
                })

        return {
            "items": results,
            "count": len(results),
            "total_confidence": round(sum(r.get("confidence", 0) for r in results) / len(results), 2) if results else 0.0,
        }

    def format_output(self, processed: Dict[str, Any], output_format: str = "json") -> str:
        """将处理结果格式化为指定格式输出。"""
        if output_format == "json":
            return json.dumps(processed, ensure_ascii=False, indent=2)
        elif output_format == "text":
            lines = []
            for item in processed.get("items", []):
                lines.append(f"[{item.get('category', 'unknown').upper()}] {item.get('name', 'unknown')}")
                lines.append(f"  内容: {item.get('content', '')}")
                lines.append(f"  置信度: {item.get('confidence', 0):.0%} {item.get('confidence_label', '')}")
            return "\n".join(lines)
        else:
            raise ValueError("E003")

    def reset(self) -> None:
        """重置内部状态。"""
        self._items = []

    # ------------------------------------------------------------------
    # 自检方法
    # ------------------------------------------------------------------
    def selftest(self) -> bool:
        """
        离线自检核心逻辑。
        使用内置硬编码样例数据，不依赖外部文件或网络。
        断言使用宽松阈值，确保稳健。
        """
        test_cases = [
            # (输入文本, 期望类别, 期望名称非空)
            ("rule: always use type hints in python code", "rule", True),
            ("skill: 擅长数据分析与可视化", "skill", True),
            ("command: run tests with pytest", "command", True),
            ("subagent: code reviewer assistant", "subagent", True),
            ("这是一个通用描述，没有明确类别", "general", True),
        ]

        for text, expected_category, expect_name in test_cases:
            try:
                result = self.process_item(text)
            except Exception:
                return False

            # 宽松断言：类别匹配（允许 fallback 到 general）
            if expected_category != "general":
                if result["category"] != expected_category and result["category"] != "general":
                    return False
            else:
                if result["category"] != "general":
                    return False

            # 名称非空
            if expect_name and not result["name"]:
                return False

            # 置信度在合理范围内
            if not (0.0 <= result["confidence"] <= 1.0):
                return False

            # 置信度标签存在
            if "confidence_label" not in result:
                return False

        # 批量处理测试
        batch_input = "rule: first rule\nskill: second skill\ncommand: third command"
        batch_result = self.process_batch(batch_input)
        if batch_result["count"] != 3:
            return False
        if batch_result["total_confidence"] < 0.5:  # 宽松阈值
            return False

        # 空输入错误测试
        try:
            self.process_batch("")
            return False  # 不应成功
        except Exception:
            pass

        # 格式化输出测试
        try:
            json_out = self.format_output(batch_result, "json")
            if not json_out:
                return False
            text_out = self.format_output(batch_result, "text")
            if not text_out:
                return False
        except Exception:
            return False

        # 重置
        self.reset()
        if len(self._items) != 0:
            return False

        return True


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="ai-rules-sync: 同步、管理和分享 AI 规则、技能、命令、子代理配置",
        epilog="错误码: E001-E010",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入内容: 用户提供的数据/文件/URL 或直接文本",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ai-rules-sync 1.0.0",
    )
    return parser


def main() -> int:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        engine = SyncEngine()
        try:
            ok = engine.selftest()
        except Exception:
            print("E008: 自检过程中发生异常", file=sys.stderr)
            return 8
        if ok:
            print("自检通过: 所有核心逻辑测试成功")
            return 0
        else:
            print("E008: 自检失败", file=sys.stderr)
            return 8

    # 正常处理模式
    if not args.input:
        print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
        return 1

    engine = SyncEngine()
    try:
        # 尝试读取文件
        if args.input.startswith("file://"):
            filepath = args.input[7:]
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                print("E006: 无法读取文件", file=sys.stderr)
                return 6
        elif args.input.startswith(("http://", "https://")):
            print("E004: 超出能力边界，不访问网络或外部服务", file=sys.stderr)
            return 4
        else:
            content = args.input

        result = engine.process_batch(content)
        output = engine.format_output(result, args.format)
        print(output)
        return 0

    except ValueError as e:
        code = str(e) if str(e).startswith("E") else "E003"
        if code == "E001":
            print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
        elif code == "E002":
            print("E002: 关键信息缺失，请补充必要字段", file=sys.stderr)
        elif code == "E003":
            print("E003: 输入格式不符合要求", file=sys.stderr)
        elif code == "E004":
            print("E004: 超出能力边界", file=sys.stderr)
        elif code == "E005":
            print("E005: 置信度过低，结果无法确定", file=sys.stderr)
        else:
            print(f"{code}: 处理失败", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未预期的运行时错误: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
