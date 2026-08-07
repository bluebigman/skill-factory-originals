#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 编码智能体规则手册 规范速查

依据功能规格独立实现（clean-room），提供：
1. 规则文档结构化解析（关键约束、目录结构、命令示例、命名约定）
2. 非结构化文本转 Markdown 表格/清单
3. 置信度标注与缺失值占位
4. 离线自检（--selftest）

错误码约定：
    E001: 参数错误
    E002: 文件读取失败
    E003: URL 获取失败（本实现不联网，仅预留）
    E004: 输入为空
    E005: 解析失败
    E006: 输出写入失败
    E007: 内部逻辑错误
    E008: 不支持的格式
    E009: 自检失败
    E010: 未捕获异常
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class RuleDocument:
    """规则文档的解析结果。"""
    raw_text: str
    constraints: List[Dict[str, str]] = field(default_factory=list)
    directory_structure: List[str] = field(default_factory=list)
    command_examples: List[str] = field(default_factory=list)
    naming_conventions: List[str] = field(default_factory=list)
    confidence: Dict[str, str] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 JSON 序列化。"""
        return {
            "constraints": self.constraints,
            "directory_structure": self.directory_structure,
            "command_examples": self.command_examples,
            "naming_conventions": self.naming_conventions,
            "confidence": self.confidence,
            "missing_fields": self.missing_fields,
        }


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------

class RuleParser:
    """规则文档解析器：从非结构化文本中提取结构化信息。"""

    # 关键约束的常见模式（宽松匹配）
    CONSTRAINT_PATTERNS = [
        r"(?:必须|禁止|不得|应当|务必|严禁|always|never|must|shall|should)\s*[^。\n]{2,80}",
        r"(?:规则|约束|限制|requirement|constraint)\s*[:：]\s*[^。\n]{2,80}",
    ]

    # 命令示例的常见模式
    COMMAND_PATTERNS = [
        r"(?:命令|示例|command|example)\s*[:：]\s*[^\n]{2,100}",
        r"`[^`]{2,100}`",  # 反引号包裹的内容
        r"(?:^|\n)\s*(?:npm|pip|git|python|node|curl|docker|make|yarn|pnpm)\s+[^\n]{2,100}",
    ]

    # 目录结构模式
    DIRECTORY_PATTERNS = [
        r"(?:目录|结构|tree|structure)\s*[:：]?\s*\n((?:\s*[│├└─|+-]?\s*[\w./-]+\n?)+)",
        r"(?:^|\n)\s*(?:src|lib|bin|test|tests|docs|config|public|app|pages|components)\s*/[^\n]{2,60}",
    ]

    # 命名约定模式
    NAMING_PATTERNS = [
        r"(?:命名|naming|case|风格|style)\s*(?:规则|约定|规范)?\s*[:：]\s*[^。\n]{2,80}",
        r"(?:camelCase|PascalCase|snake_case|kebab-case|SCREAMING_SNAKE_CASE)[^。\n]{0,60}",
    ]

    # 置信度关键词
    HIGH_CONF_KEYWORDS = ["必须", "禁止", "always", "never", "must", "shall", "明确", "规定"]
    MED_CONF_KEYWORDS = ["建议", "推荐", "should", "may", "通常", "一般"]

    def parse(self, text: str) -> RuleDocument:
        """解析文本，返回结构化文档。"""
        if not text or not text.strip():
            raise ValueError("E004: 输入文本为空")

        doc = RuleDocument(raw_text=text)

        # 提取各类信息
        doc.constraints = self._extract_constraints(text)
        doc.directory_structure = self._extract_directories(text)
        doc.command_examples = self._extract_commands(text)
        doc.naming_conventions = self._extract_naming(text)

        # 计算置信度与缺失字段
        doc.confidence = self._calculate_confidence(doc)
        doc.missing_fields = self._find_missing_fields(doc)

        return doc

    def _extract_constraints(self, text: str) -> List[Dict[str, str]]:
        """提取关键约束。"""
        results: List[Dict[str, str]] = []
        seen: set = set()

        for pattern in self.CONSTRAINT_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                item = match.group(0).strip()
                if item and item not in seen:
                    seen.add(item)
                    # 判断约束强度
                    strength = "high" if any(k in item for k in ["必须", "禁止", "always", "never", "must"]) else "medium"
                    results.append({"rule": item, "strength": strength})

        return results[:20]  # 限制数量，避免过度提取

    def _extract_directories(self, text: str) -> List[str]:
        """提取目录结构信息。"""
        results: List[str] = []
        seen: set = set()

        for pattern in self.DIRECTORY_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                item = match.group(0).strip()
                # 清理多余空白
                clean = re.sub(r"\s+", " ", item)
                if clean and clean not in seen:
                    seen.add(clean)
                    results.append(clean)

        return results[:15]

    def _extract_commands(self, text: str) -> List[str]:
        """提取命令示例。"""
        results: List[str] = []
        seen: set = set()

        for pattern in self.COMMAND_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                item = match.group(0).strip()
                # 去掉可能的标记符号
                clean = item.lstrip(":：`").rstrip("`")
                if clean and clean not in seen:
                    seen.add(clean)
                    results.append(clean)

        return results[:15]

    def _extract_naming(self, text: str) -> List[str]:
        """提取命名约定。"""
        results: List[str] = []
        seen: set = set()

        for pattern in self.NAMING_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                item = match.group(0).strip()
                if item and item not in seen:
                    seen.add(item)
                    results.append(item)

        return results[:10]

    def _calculate_confidence(self, doc: RuleDocument) -> Dict[str, str]:
        """计算各字段的置信度。"""
        confidence: Dict[str, str] = {}

        # 基于提取结果数量与关键词判断
        field_map = {
            "constraints": (doc.constraints, self.HIGH_CONF_KEYWORDS),
            "directory_structure": (doc.directory_structure, ["目录", "结构", "tree", "structure"]),
            "command_examples": (doc.command_examples, ["命令", "示例", "command", "example"]),
            "naming_conventions": (doc.naming_conventions, ["命名", "naming", "case", "风格"]),
        }

        for field_name, (items, keywords) in field_map.items():
            if not items:
                confidence[field_name] = "low"
            else:
                # 检查原文中是否有相关关键词
                text_lower = doc.raw_text.lower()
                has_keyword = any(k.lower() in text_lower for k in keywords)
                if len(items) >= 3 and has_keyword:
                    confidence[field_name] = "high"
                elif len(items) >= 1 and has_keyword:
                    confidence[field_name] = "medium"
                else:
                    confidence[field_name] = "low"

        return confidence

    def _find_missing_fields(self, doc: RuleDocument) -> List[str]:
        """找出缺失的信息字段。"""
        missing: List[str] = []

        if not doc.constraints:
            missing.append("constraints")
        if not doc.directory_structure:
            missing.append("directory_structure")
        if not doc.command_examples:
            missing.append("command_examples")
        if not doc.naming_conventions:
            missing.append("naming_conventions")

        return missing


# ---------------------------------------------------------------------------
# 格式化输出
# ---------------------------------------------------------------------------

class RuleFormatter:
    """将解析结果格式化为 Markdown。"""

    @staticmethod
    def to_markdown(doc: RuleDocument) -> str:
        """生成 Markdown 格式的输出。"""
        lines: List[str] = []

        # 约束表格
        lines.append("## 关键约束")
        if doc.constraints:
            lines.append("| 规则 | 强度 |")
            lines.append("|------|------|")
            for item in doc.constraints:
                lines.append(f"| {item['rule']} | {item['strength']} |")
        else:
            lines.append("> [需核实:constraints]")

        # 目录结构
        lines.append("\n## 目录结构")
        if doc.directory_structure:
            for item in doc.directory_structure:
                lines.append(f"- `{item}`")
        else:
            lines.append("> [需核实:directory_structure]")

        # 命令示例
        lines.append("\n## 命令示例")
        if doc.command_examples:
            for cmd in doc.command_examples:
                lines.append(f"- `{cmd}`")
        else:
            lines.append("> [需核实:command_examples]")

        # 命名约定
        lines.append("\n## 命名约定")
        if doc.naming_conventions:
            for item in doc.naming_conventions:
                lines.append(f"- {item}")
        else:
            lines.append("> [需核实:naming_conventions]")

        # 置信度
        lines.append("\n## 置信度")
        for field, level in doc.confidence.items():
            lines.append(f"- {field}: {level}")

        # 缺失字段
        if doc.missing_fields:
            lines.append("\n## 缺失信息")
            for field in doc.missing_fields:
                lines.append(f"- [需核实:{field}]")

        return "\n".join(lines)

    @staticmethod
    def to_json(doc: RuleDocument) -> str:
        """生成 JSON 格式的输出。"""
        return json.dumps(doc.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 主入口与命令行处理
# ---------------------------------------------------------------------------

def read_input(source: str) -> str:
    """读取输入：文件路径或直接文本。"""
    if not source:
        raise ValueError("E001: 缺少输入")

    # 检查是否为文件路径
    if os.path.isfile(source):
        try:
            with open(source, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, OSError) as e:
            raise ValueError(f"E002: 文件读取失败 - {e}")

    # 否则视为直接文本
    return source


def run_parse(args: argparse.Namespace) -> int:
    """执行解析流程。"""
    try:
        # 读取输入
        text = read_input(args.input)

        # 解析
        parser = RuleParser()
        doc = parser.parse(text)

        # 格式化输出
        if args.format == "json":
            output = RuleFormatter.to_json(doc)
        else:
            output = RuleFormatter.to_markdown(doc)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            except (IOError, OSError) as e:
                print(f"E006: 输出写入失败 - {e}", file=sys.stderr)
                return 6
        else:
            print(output)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        # 提取错误码
        code = str(e).split(":")[0] if ":" in str(e) else "E005"
        return int(code[1:]) if code[1:].isdigit() else 5
    except Exception as e:
        print(f"E010: 未捕获异常 - {e}", file=sys.stderr)
        return 10


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """离线自检核心逻辑，使用内置硬编码样例数据。"""
    try:
        # 内置样例数据
        sample_text = """
        # 项目编码规范

        ## 关键约束
        必须使用 TypeScript 编写所有源代码。
        禁止在提交前运行未通过的测试。
        所有函数必须有 JSDoc 注释。
        不得使用 any 类型。

        ## 目录结构
        src/
          components/
          utils/
          hooks/
        tests/
          unit/
          integration/

        ## 命令示例
        npm run build
        npm test
        git commit -m "feat: add new feature"
        python -m pytest

        ## 命名约定
        组件使用 PascalCase 命名。
        函数使用 camelCase。
        常量使用 SCREAMING_SNAKE_CASE。
        文件使用 kebab-case。
        """

        # 解析
        parser = RuleParser()
        doc = parser.parse(sample_text)

        # 宽松断言（不依赖精确值）
        assertions = [
            # 约束提取应至少找到 3 条
            ("约束数量", len(doc.constraints) >= 3),
            # 目录结构应至少找到 1 条
            ("目录结构", len(doc.directory_structure) >= 1),
            # 命令示例应至少找到 2 条
            ("命令示例", len(doc.command_examples) >= 2),
            # 命名约定应至少找到 2 条
            ("命名约定", len(doc.naming_conventions) >= 2),
            # 置信度应包含 4 个字段
            ("置信度字段数", len(doc.confidence) == 4),
            # 缺失字段应为空（样例数据完整）
            ("缺失字段", len(doc.missing_fields) == 0),
            # 约束强度应包含 high
            ("约束强度", any(c["strength"] == "high" for c in doc.constraints)),
        ]

        failed = []
        for name, result in assertions:
            if not result:
                failed.append(name)

        if failed:
            print(f"E009: 自检失败 - 未通过项: {', '.join(failed)}", file=sys.stderr)
            return 9

        # 测试格式化
        md = RuleFormatter.to_markdown(doc)
        if not md or "关键约束" not in md:
            print("E009: 自检失败 - Markdown 格式化异常", file=sys.stderr)
            return 9

        js = RuleFormatter.to_json(doc)
        if not js:
            print("E009: 自检失败 - JSON 格式化异常", file=sys.stderr)
            return 9

        # 测试空输入错误处理
        try:
            parser.parse("")
            print("E009: 自检失败 - 空输入未抛出异常", file=sys.stderr)
            return 9
        except ValueError:
            pass  # 预期行为

        print("自检通过: 所有核心逻辑验证成功")
        return 0

    except Exception as e:
        print(f"E009: 自检异常 - {e}", file=sys.stderr)
        return 9


# ---------------------------------------------------------------------------
# 参数解析与主函数
# ---------------------------------------------------------------------------

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="编码智能体规则手册 规范速查 - 规则文档结构化解析工具",
        epilog="示例: python main.py --input rules.txt --format markdown --output result.md"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本或文件路径（若为文件路径则读取文件内容）"
    )

    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式 (默认: markdown)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（默认输出到 stdout）"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不读取外部文件）"
    )

    return parser


def main() -> int:
    """主函数。"""
    parser = create_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入
    if not args.input:
        parser.print_help()
        print("\nE001: 缺少输入参数 --input 或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    # 运行解析
    return run_parse(args)


if __name__ == "__main__":
    sys.exit(main())
