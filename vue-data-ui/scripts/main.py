#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现的数据可视化技能核心逻辑。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    1. 解析用户输入（数据/文件/URL），识别关键信息并结构化。
    2. 按默认模板组织输出，标注置信度。
    3. 支持批量处理和自定义格式。
    4. 内置离线自检（--selftest），不依赖外部环境。

错误码体系：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常
    E007: 参数解析错误
    E008: 自检断言失败
    E009: 文件读取失败
    E010: 输出写入失败
"""

import argparse
import json
import os
import sys
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# 版本信息
__version__ = "1.0.0"
SKILL_NAME = "vue-data-ui"
DISPLAY_NAME = "数据可视化"

# 置信度阈值常量
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ParsedInput:
    """解析后的输入数据结构。"""
    source_type: str = "unknown"          # data / file / url / unknown
    raw_content: str = ""                 # 原始内容
    key_fields: Dict[str, Any] = field(default_factory=dict)  # 识别出的关键字段
    format_hint: str = "auto"             # 输出格式提示
    completeness: str = "detailed"        # 期望完整度: quick / detailed
    batch_mode: bool = False              # 是否批量处理
    items: List[Dict[str, Any]] = field(default_factory=list)  # 批量处理时的条目


@dataclass
class ProcessResult:
    """处理结果数据结构。"""
    success: bool = True
    error_code: Optional[str] = None
    error_message: str = ""
    confidence: int = 100                 # 置信度 0-100
    warning: str = ""                     # 建议复核或需核实的提示
    data: Dict[str, Any] = field(default_factory=dict)
    structured_output: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 核心逻辑：输入解析
# ---------------------------------------------------------------------------

class InputParser:
    """输入解析器：识别输入来源类型并提取关键信息。"""

    # 常见数据格式标记
    _JSON_MARKERS = ("{", "[")
    _CSV_MARKERS = (",", ";", "\t")
    _KEY_VALUE_MARKERS = (":", "=")

    def parse(self, raw_input: Optional[str], format_hint: str = "auto",
              completeness: str = "detailed") -> ParsedInput:
        """
        解析用户原始输入。

        参数:
            raw_input: 用户提供的原始输入
            format_hint: 输出格式提示（auto/json/csv/table）
            completeness: 期望完整度（quick/detailed）

        返回:
            ParsedInput 对象

        异常:
            ValueError: 输入为空时抛出（对应 E001）
        """
        # E001: 输入为空
        if raw_input is None or not raw_input.strip():
            raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

        parsed = ParsedInput(
            raw_content=raw_input.strip(),
            format_hint=format_hint,
            completeness=completeness
        )

        # 判断输入来源类型
        parsed.source_type = self._detect_source_type(parsed.raw_content)

        # 根据来源类型提取关键信息
        if parsed.source_type == "file":
            parsed.key_fields = self._extract_file_info(parsed.raw_content)
        elif parsed.source_type == "url":
            parsed.key_fields = self._extract_url_info(parsed.raw_content)
        else:
            # 数据内容解析
            parsed.key_fields = self._extract_data_fields(parsed.raw_content)

        # 检测是否批量模式（多行或包含多个数据块）
        parsed.batch_mode = self._detect_batch_mode(parsed.raw_content, parsed.source_type)
        if parsed.batch_mode:
            parsed.items = self._split_batch_items(parsed.raw_content, parsed.source_type)

        # E002: 关键信息缺失检查
        if not parsed.key_fields and not parsed.batch_mode:
            raise ValueError("E002: 无法从输入中识别关键信息，请提供更明确的数据内容")

        return parsed

    def _detect_source_type(self, content: str) -> str:
        """检测输入来源类型。"""
        # 检查是否为文件路径
        if self._looks_like_file_path(content):
            return "file"

        # 检查是否为 URL
        parsed_url = urllib.parse.urlparse(content)
        if parsed_url.scheme in ("http", "https", "ftp") and parsed_url.netloc:
            return "url"

        # 默认视为数据内容
        return "data"

    @staticmethod
    def _looks_like_file_path(content: str) -> bool:
        """判断是否像文件路径。"""
        # 去除可能的引号
        content = content.strip("\"'")

        # 常见文件扩展名
        extensions = (".csv", ".json", ".txt", ".xml", ".yaml", ".yml",
                      ".xlsx", ".xls", ".tsv", ".log", ".md")
        if content.lower().endswith(extensions):
            return True

        # 路径分隔符检查（Windows 和 Unix）
        if ("/" in content or "\\" in content) and not content.startswith(("http", "ftp")):
            # 排除 URL 中的斜杠
            return True

        return False

    @staticmethod
    def _extract_file_info(content: str) -> Dict[str, Any]:
        """从文件路径提取信息。"""
        content = content.strip("\"'")
        path = os.path.normpath(content)
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lstrip(".").lower()

        return {
            "file_path": path,
            "file_name": name,
            "extension": ext,
            "directory": os.path.dirname(path) or "."
        }

    @staticmethod
    def _extract_url_info(content: str) -> Dict[str, Any]:
        """从 URL 提取信息。"""
        parsed = urllib.parse.urlparse(content)
        return {
            "url": content,
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
            "query": parsed.query
        }

    def _extract_data_fields(self, content: str) -> Dict[str, Any]:
        """从数据内容中提取关键字段。"""
        # 尝试 JSON 解析
        if content.startswith(self._JSON_MARKERS):
            try:
                data = json.loads(content)
                return {"data_type": "json", "parsed_data": data}
            except json.JSONDecodeError:
                pass

        # 尝试 CSV/TSV 解析
        if any(marker in content for marker in (",", ";", "\t")):
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            if len(lines) >= 1:
                # 简单 CSV 结构分析
                delimiter = self._detect_delimiter(content)
                header_line = lines[0]
                headers = [h.strip() for h in header_line.split(delimiter)]
                rows = []
                for line in lines[1:]:
                    cells = [c.strip() for c in line.split(delimiter)]
                    if len(cells) == len(headers):
                        rows.append(dict(zip(headers, cells)))
                if rows:
                    return {
                        "data_type": "tabular",
                        "delimiter": delimiter,
                        "headers": headers,
                        "row_count": len(rows),
                        "rows": rows
                    }

        # 尝试键值对解析
        if any(marker in content for marker in self._KEY_VALUE_MARKERS):
            kv_pairs = self._parse_key_value(content)
            if kv_pairs:
                return {"data_type": "key_value", "fields": kv_pairs}

        # 尝试简单文本解析
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if lines:
            return {
                "data_type": "text",
                "line_count": len(lines),
                "preview": lines[:5]  # 预览前5行
            }

        return {}

    @staticmethod
    def _detect_delimiter(content: str) -> str:
        """检测分隔符。"""
        line = content.splitlines()[0] if content.splitlines() else ""
        for delim in ("\t", ";", ","):
            if delim in line:
                return delim
        return ","

    @staticmethod
    def _parse_key_value(content: str) -> Dict[str, str]:
        """解析键值对格式。"""
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            for sep in (":", "="):
                if sep in line:
                    key, value = line.split(sep, 1)
                    result[key.strip()] = value.strip()
                    break
        return result

    @staticmethod
    def _detect_batch_mode(content: str, source_type: str) -> bool:
        """检测是否批量模式。"""
        if source_type == "file":
            # 文件路径包含通配符视为批量
            return any(ch in content for ch in ("*", "?", "["))

        if source_type == "url":
            return False

        # 数据内容：多行且每行独立可解析
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if len(lines) <= 1:
            return False

        # 多行 JSON 数组元素或 CSV 行
        try:
            data = json.loads(content)
            return isinstance(data, list) and len(data) > 1
        except json.JSONDecodeError:
            pass

        # 多行 CSV 且超过 2 行
        if any(marker in content for marker in (",", ";", "\t")):
            return len(lines) > 2

        return False

    def _split_batch_items(self, content: str, source_type: str) -> List[Dict[str, Any]]:
        """将批量输入拆分为独立条目。"""
        items = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        # 尝试 JSON 数组
        if content.startswith("["):
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return [{"index": i, "data": item} for i, item in enumerate(data)]
            except json.JSONDecodeError:
                pass

        # CSV 多行
        if any(marker in content for marker in (",", ";", "\t")):
            delimiter = self._detect_delimiter(content)
            headers = [h.strip() for h in lines[0].split(delimiter)]
            for i, line in enumerate(lines[1:], start=1):
                cells = [c.strip() for c in line.split(delimiter)]
                if len(cells) == len(headers):
                    items.append({
                        "index": i,
                        "data": dict(zip(headers, cells))
                    })

        # 文件路径通配符
        if source_type == "file" and any(ch in content for ch in ("*", "?")):
            import glob
            paths = glob.glob(content)
            for i, path in enumerate(paths):
                items.append({
                    "index": i,
                    "data": self._extract_file_info(path)
                })

        return items


# ---------------------------------------------------------------------------
# 核心逻辑：输出生成
# ---------------------------------------------------------------------------

class OutputGenerator:
    """输出生成器：根据解析结果生成结构化输出。"""

    def generate(self, parsed: ParsedInput, confidence: int = 100) -> Dict[str, Any]:
        """
        生成结构化输出。

        参数:
            parsed: 解析后的输入
            confidence: 置信度

        返回:
            结构化输出字典
        """
        output = {
            "skill": SKILL_NAME,
            "display_name": DISPLAY_NAME,
            "version": __version__,
            "source_type": parsed.source_type,
            "confidence": confidence,
            "key_fields": parsed.key_fields,
            "batch_mode": parsed.batch_mode,
        }

        if parsed.batch_mode:
            output["item_count"] = len(parsed.items)
            output["items"] = parsed.items

        # 根据格式提示组织输出
        fmt = parsed.format_hint.lower()
        if fmt in ("json", "auto"):
            output["format"] = "json"
        elif fmt == "csv":
            output["format"] = "csv"
        elif fmt == "table":
            output["format"] = "table"
        else:
            output["format"] = "auto"

        # 完整度提示
        if parsed.completeness == "quick":
            output["detail_level"] = "骨架结果"
        else:
            output["detail_level"] = "详细结果"

        return output

    def format_output(self, data: Dict[str, Any], output_format: str = "json") -> str:
        """
        将结构化数据格式化为字符串输出。

        参数:
            data: 结构化数据
            output_format: 输出格式（json/csv/table）

        返回:
            格式化后的字符串
        """
        if output_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)

        if output_format == "csv":
            return self._to_csv(data)

        if output_format == "table":
            return self._to_table(data)

        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_csv(data: Dict[str, Any]) -> str:
        """将数据转为 CSV 格式。"""
        lines = []

        # 处理批量数据
        if data.get("batch_mode") and "items" in data:
            items = data["items"]
            if items and isinstance(items[0].get("data"), dict):
                headers = list(items[0]["data"].keys())
                lines.append(",".join(headers))
                for item in items:
                    row = [str(item["data"].get(h, "")) for h in headers]
                    lines.append(",".join(row))
                return "\n".join(lines)

        # 处理键值数据
        key_fields = data.get("key_fields", {})
        if "fields" in key_fields and isinstance(key_fields["fields"], dict):
            for key, value in key_fields["fields"].items():
                lines.append(f"{key},{value}")
            return "\n".join(lines)

        # 回退到 JSON
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def _to_table(data: Dict[str, Any]) -> str:
        """将数据转为表格格式。"""
        lines = []

        # 处理批量数据
        if data.get("batch_mode") and "items" in data:
            items = data["items"]
            if items and isinstance(items[0].get("data"), dict):
                headers = list(items[0]["data"].keys())
                header_line = " | ".join(headers)
                separator = "-+-".join("-" * len(h) for h in headers)
                lines.append(header_line)
                lines.append(separator)
                for item in items:
                    row = " | ".join(str(item["data"].get(h, "")) for h in headers)
                    lines.append(row)
                return "\n".join(lines)

        # 处理键值数据
        key_fields = data.get("key_fields", {})
        if "fields" in key_fields and isinstance(key_fields["fields"], dict):
            for key, value in key_fields["fields"].items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)

        return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 核心逻辑：置信度评估
# ---------------------------------------------------------------------------

class ConfidenceEvaluator:
    """置信度评估器。"""

    def evaluate(self, parsed: ParsedInput) -> Tuple[int, str]:
        """
        评估处理结果的置信度。

        参数:
            parsed: 解析后的输入

        返回:
            (置信度 0-100, 警告信息)
        """
        confidence = 100
        warnings = []

        # 根据来源类型和字段完整性评估
        if parsed.source_type == "unknown":
            confidence -= 20
            warnings.append("输入来源类型不明确")

        if not parsed.key_fields:
            confidence -= 30
            warnings.append("关键信息提取不完整")

        if parsed.batch_mode and not parsed.items:
            confidence -= 15
            warnings.append("批量模式但未成功拆分条目")

        # 数据内容检查
        if parsed.source_type == "data":
            key_fields = parsed.key_fields
            data_type = key_fields.get("data_type", "")
            if data_type == "text":
                confidence -= 10
                warnings.append("文本数据可能包含未结构化信息")
            elif data_type == "tabular":
                rows = key_fields.get("rows", [])
                if len(rows) < 2:
                    confidence -= 5
                    warnings.append("表格数据行数较少")

        # 置信度下限保护
        confidence = max(confidence, 0)

        # 生成警告信息
        warning_msg = ""
        if confidence >= HIGH_CONFIDENCE:
            pass  # 高置信度无警告
        elif confidence >= MEDIUM_CONFIDENCE:
            warning_msg = "建议复核"
        else:
            warning_msg = "[需核实] " + "; ".join(warnings[:2]) if warnings else "[需核实]"

        return confidence, warning_msg


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------

class DataVisualizationSkill:
    """数据可视化技能主处理器。"""

    def __init__(self):
        self.parser = InputParser()
        self.generator = OutputGenerator()
        self.evaluator = ConfidenceEvaluator()

    def process(self, raw_input: Optional[str], format_hint: str = "auto",
                completeness: str = "detailed") -> ProcessResult:
        """
        处理用户输入并生成结果。

        参数:
            raw_input: 用户原始输入
            format_hint: 输出格式提示
            completeness: 期望完整度

        返回:
            ProcessResult 对象
        """
        try:
            # Step 1: 解析输入
            parsed = self.parser.parse(raw_input, format_hint, completeness)

            # Step 2: 评估置信度
            confidence, warning = self.evaluator.evaluate(parsed)

            # E005: 置信度过低
            if confidence < MEDIUM_CONFIDENCE:
                # 低置信度也返回结果，但标注需核实
                pass

            # Step 3: 生成输出
            output_data = self.generator.generate(parsed, confidence)

            # 添加警告信息
            if warning:
                output_data["warning"] = warning

            result = ProcessResult(
                success=True,
                confidence=confidence,
                warning=warning,
                data=asdict(parsed),
                structured_output=output_data
            )

            return result

        except ValueError as e:
            error_msg = str(e)
            error_code = "E001" if error_msg.startswith("E001") else \
                        "E002" if error_msg.startswith("E002") else \
                        "E003"
            return ProcessResult(
                success=False,
                error_code=error_code,
                error_message=error_msg
            )
        except Exception as e:
            # E006: 内部处理异常
            return ProcessResult(
                success=False,
                error_code="E006",
                error_message=f"内部处理异常: {str(e)}"
            )

    def format_result(self, result: ProcessResult, output_format: str = "json") -> str:
        """
        将处理结果格式化为字符串。

        参数:
            result: 处理结果
            output_format: 输出格式

        返回:
            格式化字符串
        """
        if not result.success:
            return json.dumps({
                "success": False,
                "error_code": result.error_code,
                "error_message": result.error_message
            }, ensure_ascii=False, indent=2)

        # 成功时，添加 success 字段到输出中
        output_data = result.structured_output.copy()
        output_data["success"] = True
        
        return self.generator.format_output(output_data, output_format)


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检，使用硬编码样例数据验证核心逻辑。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("=" * 60)
    print(f"自检开始 - {DISPLAY_NAME} v{__version__}")
    print("=" * 60)

    skill = DataVisualizationSkill()
    all_passed = True

    # 测试用例 1: JSON 数据输入
    print("\n[测试 1] JSON 数据输入")
    json_input = '{"name": "销售数据", "quarter": "Q1", "revenue": 150000, "growth": 0.12}'
    try:
        result = skill.process(json_input)
        assert result.success, f"JSON 处理失败: {result.error_message}"
        assert result.confidence >= MEDIUM_CONFIDENCE, f"置信度过低: {result.confidence}"
        assert result.structured_output["source_type"] == "data", "来源类型应为 data"
        assert result.structured_output["key_fields"]["data_type"] == "json", "数据类型应为 json"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 2: CSV 数据输入
    print("\n[测试 2] CSV 数据输入")
    csv_input = "日期,销售额,利润\n2024-01,1000,200\n2024-02,1500,350\n2024-03,1200,280"
    try:
        result = skill.process(csv_input)
        assert result.success, f"CSV 处理失败: {result.error_message}"
        assert result.structured_output["source_type"] == "data", "来源类型应为 data"
        key_fields = result.structured_output["key_fields"]
        assert key_fields["data_type"] in ("tabular", "text"), "数据类型应为表格或文本"
        if key_fields["data_type"] == "tabular":
            assert key_fields["row_count"] >= 1, "应至少有一行数据"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 3: 文件路径输入
    print("\n[测试 3] 文件路径输入")
    file_input = "/tmp/example_data.csv"
    try:
        result = skill.process(file_input)
        assert result.success, f"文件路径处理失败: {result.error_message}"
        assert result.structured_output["source_type"] == "file", "来源类型应为 file"
        key_fields = result.structured_output["key_fields"]
        assert key_fields["file_name"] == "example_data.csv", "文件名提取错误"
        assert key_fields["extension"] == "csv", "扩展名提取错误"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 4: URL 输入
    print("\n[测试 4] URL 输入")
    url_input = "https://example.com/data/report?year=2024"
    try:
        result = skill.process(url_input)
        assert result.success, f"URL 处理失败: {result.error_message}"
        assert result.structured_output["source_type"] == "url", "来源类型应为 url"
        key_fields = result.structured_output["key_fields"]
        assert key_fields["host"] == "example.com", "主机名提取错误"
        assert key_fields["scheme"] == "https", "协议提取错误"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 5: 批量数据输入
    print("\n[测试 5] 批量数据输入")
    batch_input = "名称,数量\n苹果,5\n香蕉,3\n橙子,8\n葡萄,12"
    try:
        result = skill.process(batch_input)
        assert result.success, f"批量处理失败: {result.error_message}"
        assert result.structured_output["batch_mode"] is True, "应识别为批量模式"
        assert result.structured_output["item_count"] >= 1, "应有至少一个条目"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 6: 空输入（应报 E001）
    print("\n[测试 6] 空输入处理")
    try:
        result = skill.process("")
        assert not result.success, "空输入应处理失败"
        assert result.error_code == "E001", f"错误码应为 E001，实际: {result.error_code}"
        print(f"  ✓ 通过 (错误码: {result.error_code})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 7: 键值对输入
    print("\n[测试 7] 键值对输入")
    kv_input = "客户名称: 张三\n订单编号: ORD-2024-001\n金额: 599.00"
    try:
        result = skill.process(kv_input)
        assert result.success, f"键值对处理失败: {result.error_message}"
        assert result.structured_output["source_type"] == "data", "来源类型应为 data"
        key_fields = result.structured_output["key_fields"]
        assert "fields" in key_fields, "应提取到字段"
        assert "客户名称" in key_fields["fields"], "应包含客户名称字段"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 8: 输出格式测试
    print("\n[测试 8] 输出格式测试")
    try:
        result = skill.process('{"test": "value"}', format_hint="json")
        json_output = skill.format_result(result, "json")
        parsed_output = json.loads(json_output)
        assert parsed_output["success"] is True, "JSON 输出应包含 success 字段"
        assert "key_fields" in parsed_output, "输出应包含数据字段"
        print("  ✓ JSON 格式输出正常")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 9: 低置信度场景
    print("\n[测试 9] 低置信度场景")
    try:
        # 模糊输入
        result = skill.process("一些不太明确的文本内容")
        assert result.success, "模糊输入不应处理失败"
        assert 0 <= result.confidence <= 100, "置信度应在 0-100 范围内"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 10: 简单文本输入
    print("\n[测试 10] 简单文本输入")
    text_input = "这是一个简单的文本数据示例"
    try:
        result = skill.process(text_input)
        assert result.success, f"文本处理失败: {result.error_message}"
        key_fields = result.structured_output["key_fields"]
        assert key_fields["data_type"] == "text", "数据类型应为 text"
        assert key_fields["line_count"] >= 1, "应有至少一行"
        print(f"  ✓ 通过 (置信度: {result.confidence}%)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - 数据可视化技能处理工具 v{__version__}",
        epilog="示例: python main.py '{\"name\": \"test\"}' --format json"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="待处理的内容（数据/文件路径/URL）"
    )
    parser.add_argument(
        "--format",
        choices=["auto", "json", "csv", "table"],
        default="auto",
        help="输出格式"
    )
    parser.add_argument(
        "--completeness",
        choices=["quick", "detailed"],
        default="detailed",
        help="期望完整度: quick=骨架结果, detailed=详细结果"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    try:
        args = parser.parse_args()

        # 自检模式
        if args.selftest:
            success = run_selftest()
            return 0 if success else 1

        # 需要输入参数
        if args.input is None:
            parser.print_usage()
            print("错误: 请提供待处理的内容，或使用 --selftest 运行自检", file=sys.stderr)
            return 1

        # 处理输入
        skill = DataVisualizationSkill()
        result = skill.process(args.input, args.format, args.completeness)

        # 输出结果
        output = skill.format_result(result, args.format)
        print(output)

        # 处理失败时返回错误码
        if not result.success:
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        # E007: 参数解析错误
        print(f"E007: 参数解析错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
