#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 编码智能体规则手册 规范速查

依据功能规格独立实现（clean-room），提供：
1. 规则文档结构化解析（关键约束、目录结构、命令示例、命名约定）
2. 非结构化文本转 Markdown 表格/清单
3. 置信度标注与缺失值占位
4. 离线自检（--selftest）
5. 预览模式（--dry-run）与详细输出（--verbose）

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
import time
import tempfile
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
    parse_details: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 JSON 序列化。"""
        return {
            "constraints": self.constraints,
            "directory_structure": self.directory_structure,
            "command_examples": self.command_examples,
            "naming_conventions": self.naming_conventions,
            "confidence": self.confidence,
            "missing_fields": self.missing_fields,
            "parse_details": self.parse_details,
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

    def parse(self, text: str, verbose: bool = False) -> RuleDocument:
        """解析文本，返回结构化文档。

        参数:
            text: 输入文本，必须非空且为字符串类型
            verbose: 是否记录详细解析信息

        返回:
            RuleDocument: 解析结果

        异常:
            ValueError: 输入为空或类型错误时抛出，错误码 E004
        """
        # 输入校验（R7: guard clause 顶部先校验）
        if not isinstance(text, str):
            raise ValueError("E001: 输入必须是字符串类型")
        if not text or not text.strip():
            raise ValueError("E004: 输入文本为空")

        doc = RuleDocument(raw_text=text)

        # 提取各类信息
        doc.constraints = self._extract_constraints(text, verbose, doc)
        doc.directory_structure = self._extract_directories(text, verbose, doc)
        doc.command_examples = self._extract_commands(text, verbose, doc)
        doc.naming_conventions = self._extract_naming(text, verbose, doc)

        # 计算置信度与缺失字段
        doc.confidence = self._calculate_confidence(doc)
        doc.missing_fields = self._find_missing_fields(doc)

        return doc

    def _extract_constraints(self, text: str, verbose: bool, doc: RuleDocument) -> List[Dict[str, str]]:
        """提取关键约束。

        参数:
            text: 输入文本
            verbose: 是否记录详细解析信息
            doc: 文档对象，用于记录解析详情

        返回:
            List[Dict[str, str]]: 约束列表，每项包含规则内容和强度
        """
        results: List[Dict[str, str]] = []
        seen: set = set()

        try:
            for pattern in self.CONSTRAINT_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                    item = match.group(0).strip()
                    if item and item not in seen:
                        seen.add(item)
                        # 判断约束强度
                        strength = "high" if any(k in item for k in ["必须", "禁止", "always", "never", "must"]) else "medium"
                        results.append({"rule": item, "strength": strength})
                        if verbose:
                            doc.parse_details.append({
                                "action": "extract_constraint",
                                "detail": f"提取约束: {item[:50]}...",
                                "strength": strength
                            })
        except re.error as e:
            # 正则表达式错误不应导致崩溃，降级返回空列表
            print(f"警告: 约束提取正则错误 - {e}", file=sys.stderr)
            return []

        return results[:20]  # 限制数量，避免过度提取

    def _extract_directories(self, text: str, verbose: bool, doc: RuleDocument) -> List[str]:
        """提取目录结构信息。

        参数:
            text: 输入文本
            verbose: 是否记录详细解析信息
            doc: 文档对象，用于记录解析详情

        返回:
            List[str]: 目录结构列表
        """
        results: List[str] = []
        seen: set = set()

        try:
            for pattern in self.DIRECTORY_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                    item = match.group(0).strip()
                    # 清理多余空白
                    clean = re.sub(r"\s+", " ", item)
                    if clean and clean not in seen:
                        seen.add(clean)
                        results.append(clean)
                        if verbose:
                            doc.parse_details.append({
                                "action": "extract_directory",
                                "detail": f"提取目录: {clean[:50]}..."
                            })
        except re.error as e:
            print(f"警告: 目录提取正则错误 - {e}", file=sys.stderr)
            return []

        return results[:15]

    def _extract_commands(self, text: str, verbose: bool, doc: RuleDocument) -> List[str]:
        """提取命令示例。

        参数:
            text: 输入文本
            verbose: 是否记录详细解析信息
            doc: 文档对象，用于记录解析详情

        返回:
            List[str]: 命令示例列表
        """
        results: List[str] = []
        seen: set = set()

        try:
            for pattern in self.COMMAND_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                    item = match.group(0).strip()
                    # 去掉可能的标记符号
                    clean = item.lstrip(":：`").rstrip("`")
                    if clean and clean not in seen:
                        seen.add(clean)
                        results.append(clean)
                        if verbose:
                            doc.parse_details.append({
                                "action": "extract_command",
                                "detail": f"提取命令: {clean[:50]}..."
                            })
        except re.error as e:
            print(f"警告: 命令提取正则错误 - {e}", file=sys.stderr)
            return []

        return results[:15]

    def _extract_naming(self, text: str, verbose: bool, doc: RuleDocument) -> List[str]:
        """提取命名约定。

        参数:
            text: 输入文本
            verbose: 是否记录详细解析信息
            doc: 文档对象，用于记录解析详情

        返回:
            List[str]: 命名约定列表
        """
        results: List[str] = []
        seen: set = set()

        try:
            for pattern in self.NAMING_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                    item = match.group(0).strip()
                    if item and item not in seen:
                        seen.add(item)
                        results.append(item)
                        if verbose:
                            doc.parse_details.append({
                                "action": "extract_naming",
                                "detail": f"提取命名约定: {item[:50]}..."
                            })
        except re.error as e:
            print(f"警告: 命名提取正则错误 - {e}", file=sys.stderr)
            return []

        return results[:10]

    def _calculate_confidence(self, doc: RuleDocument) -> Dict[str, str]:
        """计算各字段的置信度。

        参数:
            doc: 解析后的文档对象

        返回:
            Dict[str, str]: 各字段的置信度等级
        """
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
        """找出缺失的信息字段。

        参数:
            doc: 解析后的文档对象

        返回:
            List[str]: 缺失字段列表
        """
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
    def to_markdown(doc: RuleDocument, verbose: bool = False) -> str:
        """生成 Markdown 格式的输出。

        参数:
            doc: 解析后的文档对象
            verbose: 是否包含详细解析信息

        返回:
            str: Markdown 格式文本
        """
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

        # 详细解析信息
        if verbose and doc.parse_details:
            lines.append("\n## 解析详情")
            for detail in doc.parse_details:
                lines.append(f"- [{detail['action']}] {detail['detail']}")

        return "\n".join(lines)

    @staticmethod
    def to_json(doc: RuleDocument, verbose: bool = False) -> str:
        """生成 JSON 格式的输出。

        参数:
            doc: 解析后的文档对象
            verbose: 是否包含详细解析信息

        返回:
            str: JSON 格式文本
        """
        try:
            data = doc.to_dict()
            if not verbose:
                data.pop("parse_details", None)
            return json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            # JSON 序列化失败时降级返回空对象
            print(f"警告: JSON 序列化失败 - {e}", file=sys.stderr)
            return "{}"


# ---------------------------------------------------------------------------
# 文件读写工具函数
# ---------------------------------------------------------------------------

def read_file_with_encoding(filepath: str) -> str:
    """读取文件内容，支持多编码。

    优先尝试 UTF-8，失败后依次尝试 GBK、GB18030，最后使用 errors="replace" 兜底。

    参数:
        filepath: 文件路径

    返回:
        str: 文件内容

    异常:
        ValueError: 文件读取失败时抛出，错误码 E002
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    
    for encoding in encodings:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except (IOError, OSError) as e:
            raise ValueError(f"E002: 文件读取失败 - {e}")

    # 所有编码都失败，使用 replace 兜底
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (IOError, OSError) as e:
        raise ValueError(f"E002: 文件读取失败 - {e}")


def write_file_with_encoding(filepath: str, content: str) -> None:
    """写入文件内容，使用 UTF-8 编码。

    参数:
        filepath: 文件路径
        content: 要写入的内容

    异常:
        ValueError: 文件写入失败时抛出，错误码 E006
    """
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except (IOError, OSError) as e:
        raise ValueError(f"E006: 输出写入失败 - {e}")


# ---------------------------------------------------------------------------
# 输入处理
# ---------------------------------------------------------------------------

def read_input(source: str) -> str:
    """读取输入：文件路径或直接文本。

    参数:
        source: 输入文本或文件路径

    返回:
        str: 输入内容

    异常:
        ValueError: 输入为空或文件读取失败时抛出
    """
    if not source:
        raise ValueError("E001: 缺少输入")

    # 检查是否为文件路径
    if os.path.isfile(source):
        return read_file_with_encoding(source)

    # 否则视为直接文本
    return source


# ---------------------------------------------------------------------------
# 主执行逻辑
# ---------------------------------------------------------------------------

def run_parse(args: argparse.Namespace) -> int:
    """执行解析流程。

    参数:
        args: 命令行参数

    返回:
        int: 退出码
    """
    try:
        # 读取输入
        text = read_input(args.input)

        # 解析
        parser = RuleParser()
        doc = parser.parse(text, verbose=args.verbose)

        # 格式化输出
        if args.format == "json":
            output = RuleFormatter.to_json(doc, verbose=args.verbose)
        else:
            output = RuleFormatter.to_markdown(doc, verbose=args.verbose)

        # 输出（支持 --dry-run 预览模式）
        if args.output:
            if args.dry_run:
                # 预览模式：打印 diff 摘要
                print(f"[DRY-RUN] 将写入文件: {args.output}")
                print(f"[DRY-RUN] 内容长度: {len(output)} 字符")
                print(f"[DRY-RUN] 内容预览:")
                print(output[:500] + ("..." if len(output) > 500 else ""))
                if args.verbose:
                    print(f"\n[DRY-RUN] 解析详情:")
                    for detail in doc.parse_details:
                        print(f"  - [{detail['action']}] {detail['detail']}")
            else:
                # 实际写入
                try:
                    write_file_with_encoding(args.output, output)
                    if args.verbose:
                        print(f"已写入文件: {args.output}")
                        for detail in doc.parse_details:
                            print(f"  - [{detail['action']}] {detail['detail']}")
                except ValueError as e:
                    print(f"错误: {e}", file=sys.stderr)
                    return 6
        else:
            # 输出到 stdout
            print(output)
            if args.verbose:
                print("\n解析详情:")
                for detail in doc.parse_details:
                    print(f"  - [{detail['action']}] {detail['detail']}")

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        # 提取错误码
        error_msg = str(e)
        code = error_msg.split(":")[0] if ":" in error_msg else "E005"
        return int(code[1:]) if code[1:].isdigit() else 5
    except Exception as e:
        print(f"E010: 未捕获异常 - {e}", file=sys.stderr)
        return 10


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """离线自检核心逻辑，使用内置硬编码样例数据。

    返回:
        int: 退出码，0 表示通过，9 表示失败
    """
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
        doc = parser.parse(sample_text, verbose=True)

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
            # 详细解析信息应非空（verbose 模式）
            ("解析详情", len(doc.parse_details) > 0),
        ]

        failed = []
        for name, result in assertions:
            if not result:
                failed.append(name)

        if failed:
            print(f"E009: 自检失败 - 未通过项: {', '.join(failed)}", file=sys.stderr)
            return 9

        # 测试格式化
        md = RuleFormatter.to_markdown(doc, verbose=True)
        if not md or "关键约束" not in md:
            print("E009: 自检失败 - Markdown 格式化异常", file=sys.stderr)
            return 9

        js = RuleFormatter.to_json(doc, verbose=True)
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

        # 测试中文标点输入
        chinese_punctuation_text = "必须使用中文标点：句号。逗号，分号；"
        try:
            doc_cn = parser.parse(chinese_punctuation_text)
            if not doc_cn.constraints:
                print("E009: 自检失败 - 中文标点输入未提取到约束", file=sys.stderr)
                return 9
        except Exception as e:
            print(f"E009: 自检失败 - 中文标点输入处理异常: {e}", file=sys.stderr)
            return 9

        # 测试超长输入（性能验证，O(n) 复杂度）
        long_text = "必须遵守规则。" * 10000  # 约 10 万字
        try:
            start_time = time.time()
            doc_long = parser.parse(long_text)
            elapsed_time = time.time() - start_time
            if elapsed_time > 5.0:  # 5 秒内完成
                print(f"E009: 自检失败 - 超长输入处理超时: {elapsed_time:.2f}秒", file=sys.stderr)
                return 9
        except Exception as e:
            print(f"E009: 自检失败 - 超长输入处理异常: {e}", file=sys.stderr)
            return 9

        # 测试文件读取（多编码）
        test_content = "必须使用 UTF-8 编码。"
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        try:
            file_content = read_file_with_encoding(temp_path)
            if file_content != test_content:
                print("E009: 自检失败 - 文件读取内容不匹配", file=sys.stderr)
                return 9
        except Exception as e:
            print(f"E009: 自检失败 - 文件读取异常: {e}", file=sys.stderr)
            return 9
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        # 测试 GBK 编码文件读取
        gbk_content = "必须支持 GBK 编码。"
        try:
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
                f.write(gbk_content.encode("gbk"))
                gbk_path = f.name
            try:
                gbk_read = read_file_with_encoding(gbk_path)
                if gbk_read != gbk_content:
                    print("E009: 自检失败 - GBK 文件读取内容不匹配", file=sys.stderr)
                    return 9
            except Exception as e:
                print(f"E009: 自检失败 - GBK 文件读取异常: {e}", file=sys.stderr)
                return 9
            finally:
                try:
                    os.unlink(gbk_path)
                except OSError:
                    pass
        except Exception as e:
            print(f"E009: 自检失败 - GBK 文件创建异常: {e}", file=sys.stderr)
            return 9

        # 测试 dry-run 模式（不实际写入）
        test_output_path = os.path.join(tempfile.gettempdir(), "test_dry_run_output.md")
        try:
            # 模拟 dry-run 参数
            args_dry = argparse.Namespace(
                input=sample_text,
                format="markdown",
                output=test_output_path,
                dry_run=True,
                verbose=True
            )
            result = run_parse(args_dry)
            if result != 0:
                print(f"E009: 自检失败 - dry-run 模式返回非零退出码: {result}", file=sys.stderr)
                return 9
            # 验证文件未被实际创建
            if os.path.exists(test_output_path):
                print("E009: 自检失败 - dry-run 模式实际写入了文件", file=sys.stderr)
                return 9
        except Exception as e:
            print(f"E009: 自检失败 - dry-run 模式异常: {e}", file=sys.stderr)
            return 9

        # 测试 force 模式（实际写入）
        test_force_path = os.path.join(tempfile.gettempdir(), "test_force_output.md")
        try:
            # 模拟 force 参数（dry_run=False）
            args_force = argparse.Namespace(
                input=sample_text,
                format="markdown",
                output=test_force_path,
                dry_run=False,
                verbose=False
            )
            result = run_parse(args_force)
            if result != 0:
                print(f"E009: 自检失败 - force 模式返回非零退出码: {result}", file=sys.stderr)
                return 9
            # 验证文件已被实际创建
            if not os.path.exists(test_force_path):
                print("E009: 自检失败 - force 模式未实际写入文件", file=sys.stderr)
                return 9
        except Exception as e:
            print(f"E009: 自检失败 - force 模式异常: {e}", file=sys.stderr)
            return 9
        finally:
            # 清理临时文件
            try:
                os.unlink(test_force_path)
            except OSError:
                pass

        print("自检通过: 所有核心逻辑验证成功")
        return 0

    except Exception as e:
        print(f"E009: 自检异常 - {e}", file=sys.stderr)
        return 9


# ---------------------------------------------------------------------------
# 参数解析与主函数
# ---------------------------------------------------------------------------

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。

    返回:
        argparse.ArgumentParser: 参数解析器
    """
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
        "--dry-run",
        action="store_true",
        help="预览模式：只打印输出内容，不实际写入文件"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="强制模式：实际写入文件（需与 --output 配合使用）"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细模式：输出每个解析决策的明细"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不读取外部文件）"
    )

    return parser


def main() -> int:
    """主函数。

    返回:
        int: 退出码
    """
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

    # 检查输出模式
    if args.output and not args.dry_run and not args.force:
        print("E001: 输出到文件需要 --force 参数（实际写入）或 --dry-run 参数（预览）", file=sys.stderr)
        return 1

    # 运行解析
    return run_parse(args)


if __name__ == "__main__":
    sys.exit(main())
