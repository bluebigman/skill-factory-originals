#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ape - 协议探测、数据转换、结构校验工具

功能说明：
    将任意输入解析为结构化结果，标注置信度并支持批量处理。
    支持 JSON / XML / CSV / 纯文本 四种格式的探测与解析。

用法示例：
    python main.py --input '{"name": "张三", "age": 30}' --format json
    python main.py --file data.txt --batch
    python main.py --selftest
"""

import argparse
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "文件错误：文件不存在或无法读取",
    "E003": "URL错误：URL格式不正确或无法访问",
    "E004": "JSON解析错误：输入不是合法的JSON格式",
    "E005": "XML解析错误：输入不是合法的XML格式",
    "E006": "CSV解析错误：输入不是合法的CSV格式",
    "E007": "格式错误：不支持的输入格式",
    "E008": "批量处理错误：批量处理过程中发生异常",
    "E009": "内部错误：未预期的运行时错误",
    "E010": "参数错误：不支持的输出格式",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出程序"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg} - {message}"
    print(f"[错误] {code}: {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 协议探测模块
# ============================================================
class ProtocolDetector:
    """协议探测器：识别输入数据的格式类型"""

    @staticmethod
    def detect(data: str) -> Tuple[str, float]:
        """
        探测输入数据的格式类型

        返回: (格式类型, 置信度)
        格式类型: json / xml / csv / text
        置信度: 0.0 ~ 1.0
        """
        if not data or not data.strip():
            return "text", 0.1

        stripped = data.strip()

        # 先尝试 JSON
        json_score = ProtocolDetector._score_json(stripped)
        if json_score >= 0.8:
            return "json", json_score

        # 再尝试 XML
        xml_score = ProtocolDetector._score_xml(stripped)
        if xml_score >= 0.8:
            return "xml", xml_score

        # 然后尝试 CSV
        csv_score = ProtocolDetector._score_csv(stripped)
        if csv_score >= 0.7:
            return "csv", csv_score

        # 检查是否是键值对格式的文本
        if ProtocolDetector._is_key_value_text(stripped):
            return "text", 0.8

        # 默认返回文本
        return "text", 0.5

    @staticmethod
    def _score_json(data: str) -> float:
        """JSON 格式评分"""
        score = 0.0
        if data.startswith("{") or data.startswith("["):
            score += 0.4
        if data.endswith("}") or data.endswith("]"):
            score += 0.3
        try:
            json.loads(data)
            score += 0.3
        except (json.JSONDecodeError, ValueError):
            pass
        return min(score, 1.0)

    @staticmethod
    def _score_xml(data: str) -> float:
        """XML 格式评分"""
        score = 0.0
        if data.startswith("<") and data.endswith(">"):
            score += 0.4
        if "<" in data and ">" in data and "/" in data:
            score += 0.2
        try:
            ET.fromstring(data)
            score += 0.4
        except ET.ParseError:
            pass
        return min(score, 1.0)

    @staticmethod
    def _score_csv(data: str) -> float:
        """CSV 格式评分"""
        score = 0.0
        lines = data.strip().split("\n")
        if len(lines) >= 2:
            # 检查是否有分隔符
            for sep in [",", ";", "\t", "|"]:
                if sep in lines[0] and sep in lines[1]:
                    score += 0.4
                    break
            # 检查行数
            if len(lines) >= 3:
                score += 0.2
            # 检查列数一致性
            try:
                first_cols = len(next(csv.reader([lines[0]])))
                all_same = all(
                    len(next(csv.reader([line]))) == first_cols
                    for line in lines[1:]
                )
                if all_same:
                    score += 0.3
            except (csv.Error, StopIteration):
                pass
        return min(score, 1.0)

    @staticmethod
    def _is_key_value_text(data: str) -> bool:
        """检查是否为键值对格式的文本"""
        lines = data.split("\n")
        if len(lines) < 2:
            return False
        
        key_value_count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            for sep in [":", "=", "："]:
                if sep in line:
                    key_value_count += 1
                    break
        
        # 如果大部分行都是键值对格式
        return key_value_count >= len([l for l in lines if l.strip()]) * 0.7


# ============================================================
# 数据转换模块
# ============================================================
class DataParser:
    """数据解析器：将输入解析为结构化字典"""

    @staticmethod
    def parse(data: str, fmt: Optional[str] = None) -> Tuple[Dict[str, Any], str, float]:
        """
        解析输入数据为结构化结果

        返回: (结构化结果, 格式, 置信度)
        """
        if not data or not data.strip():
            return {"content": "", "fields": []}, "text", 0.1

        # 自动探测格式
        if fmt is None or fmt == "auto":
            fmt, confidence = ProtocolDetector.detect(data)
        else:
            fmt = fmt.lower()
            confidence = 0.9

        try:
            if fmt == "json":
                return DataParser._parse_json(data), "json", confidence
            elif fmt == "xml":
                return DataParser._parse_xml(data), "xml", confidence
            elif fmt == "csv":
                return DataParser._parse_csv(data), "csv", confidence
            elif fmt == "text":
                return DataParser._parse_text(data), "text", confidence
            else:
                error_exit("E007", f"不支持的格式: {fmt}")
        except Exception as e:
            error_exit("E009", f"解析失败: {str(e)}")

    @staticmethod
    def _parse_json(data: str) -> Dict[str, Any]:
        """解析 JSON 数据"""
        try:
            obj = json.loads(data)
            return {
                "type": "object" if isinstance(obj, dict) else "array",
                "data": obj,
                "field_count": len(obj) if isinstance(obj, dict) else len(obj),
                "fields": list(obj.keys()) if isinstance(obj, dict) else [],
            }
        except json.JSONDecodeError as e:
            error_exit("E004", str(e))

    @staticmethod
    def _parse_xml(data: str) -> Dict[str, Any]:
        """解析 XML 数据"""
        try:
            root = ET.fromstring(data)
            fields = []
            for child in root:
                fields.append(child.tag)
            return {
                "type": "xml",
                "root": root.tag,
                "field_count": len(fields),
                "fields": fields,
                "data": {child.tag: child.text for child in root},
            }
        except ET.ParseError as e:
            error_exit("E005", str(e))

    @staticmethod
    def _parse_csv(data: str) -> Dict[str, Any]:
        """解析 CSV 数据"""
        try:
            lines = data.strip().split("\n")
            if len(lines) < 1:
                error_exit("E006", "CSV内容为空")

            # 尝试自动识别分隔符
            delimiter = ","
            for sep in [",", ";", "\t", "|"]:
                if sep in lines[0]:
                    delimiter = sep
                    break

            # 读取表头
            header_line = next(csv.reader([lines[0]], delimiter=delimiter))
            headers = [h.strip() for h in header_line]

            # 读取数据行
            rows = []
            for line in lines[1:]:
                if not line.strip():
                    continue
                row = next(csv.reader([line], delimiter=delimiter))
                row_dict = {}
                for i, val in enumerate(row):
                    key = headers[i] if i < len(headers) else f"col_{i}"
                    row_dict[key] = val.strip()
                rows.append(row_dict)

            return {
                "type": "csv",
                "headers": headers,
                "row_count": len(rows),
                "rows": rows,
                "field_count": len(headers),
                "fields": headers,
            }
        except (csv.Error, StopIteration) as e:
            error_exit("E006", str(e))

    @staticmethod
    def _parse_text(data: str) -> Dict[str, Any]:
        """解析纯文本数据"""
        lines = data.strip().split("\n")
        # 尝试提取键值对
        fields = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            for sep in [":", "=", "："]:
                if sep in line:
                    key, value = line.split(sep, 1)
                    fields[key.strip()] = value.strip()
                    break

        return {
            "type": "text",
            "line_count": len(lines),
            "field_count": len(fields),
            "fields": list(fields.keys()),
            "data": fields,
            "content": data,
        }


# ============================================================
# 结构校验模块
# ============================================================
class StructureValidator:
    """结构校验器：校验结构化结果的完整性"""

    @staticmethod
    def validate(parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        校验解析结果的完整性

        返回: 校验结果（包含置信度标注）
        """
        result = {
            "valid": True,
            "issues": [],
            "confidence": "高",
            "field_confidence": {},
        }

        # 检查字段数量
        field_count = parsed.get("field_count", 0)
        if field_count == 0:
            result["valid"] = False
            result["issues"].append("未提取到任何字段")
            result["confidence"] = "低"
        elif field_count < 3:
            result["confidence"] = "中"
            result["issues"].append("字段数量较少，置信度降低")
        else:
            result["confidence"] = "高"

        # 为每个字段标注置信度
        fields = parsed.get("fields", [])
        for field in fields:
            # 根据字段名特征判断置信度
            if len(str(field)) < 2:
                result["field_confidence"][str(field)] = "低"
            elif any(c.isdigit() for c in str(field)):
                result["field_confidence"][str(field)] = "中"
            else:
                result["field_confidence"][str(field)] = "高"

        # 特殊格式的额外校验
        if parsed.get("type") == "csv":
            rows = parsed.get("rows", [])
            if len(rows) == 0:
                result["valid"] = False
                result["issues"].append("CSV没有数据行")
                result["confidence"] = "低"

        return result


# ============================================================
# 批量处理模块
# ============================================================
class BatchProcessor:
    """批量处理器：顺序处理多个输入"""

    @staticmethod
    def process(inputs: List[str], fmt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        批量处理输入列表

        返回: 处理结果列表
        """
        results = []
        for i, input_data in enumerate(inputs):
            try:
                parsed, detected_fmt, confidence = DataParser.parse(input_data, fmt)
                validated = StructureValidator.validate(parsed)
                results.append({
                    "index": i,
                    "success": True,
                    "format": detected_fmt,
                    "confidence": confidence,
                    "parsed": parsed,
                    "validated": validated,
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "error": str(e),
                })
        return results


# ============================================================
# 输入获取模块
# ============================================================
class InputFetcher:
    """输入获取器：从不同来源获取输入数据"""

    @staticmethod
    def from_text(text: str) -> str:
        """从文本获取输入"""
        return text

    @staticmethod
    def from_file(filepath: str) -> str:
        """从文件获取输入"""
        if not os.path.exists(filepath):
            error_exit("E002", f"文件不存在: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, UnicodeDecodeError) as e:
            error_exit("E002", str(e))

    @staticmethod
    def from_url(url: str) -> str:
        """从 URL 获取输入"""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            error_exit("E003", f"不支持的URL协议: {parsed.scheme}")
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=10) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            error_exit("E003", str(e))


# ============================================================
# 输出格式化模块
# ============================================================
class OutputFormatter:
    """输出格式化器：将结果格式化为指定格式"""

    @staticmethod
    def format(result: Dict[str, Any], output_format: str = "json") -> str:
        """
        格式化输出结果

        支持格式: json, markdown, table
        """
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif output_format == "markdown":
            return OutputFormatter._to_markdown(result)
        elif output_format == "table":
            return OutputFormatter._to_table(result)
        else:
            error_exit("E010", f"不支持的输出格式: {output_format}")

    @staticmethod
    def _to_markdown(result: Dict[str, Any]) -> str:
        """转换为 Markdown 格式"""
        lines = ["## 解析结果", ""]

        # 基本信息
        lines.append(f"- **格式**: {result.get('format', '未知')}")
        lines.append(f"- **置信度**: {result.get('confidence', '未知')}")
        lines.append("")

        # 字段信息
        parsed = result.get("parsed", {})
        fields = parsed.get("fields", [])
        if fields:
            lines.append("### 字段列表")
            lines.append("")
            for field in fields:
                lines.append(f"- {field}")
            lines.append("")

        # 校验信息
        validated = result.get("validated", {})
        lines.append("### 校验结果")
        lines.append(f"- **有效性**: {'通过' if validated.get('valid') else '未通过'}")
        lines.append(f"- **置信度**: {validated.get('confidence', '未知')}")
        issues = validated.get("issues", [])
        if issues:
            lines.append("- **问题**:")
            for issue in issues:
                lines.append(f"  - {issue}")

        return "\n".join(lines)

    @staticmethod
    def _to_table(result: Dict[str, Any]) -> str:
        """转换为表格格式"""
        parsed = result.get("parsed", {})
        fields = parsed.get("fields", [])
        rows = parsed.get("rows", [])

        if not fields:
            return "无字段数据"

        # 表头
        lines = ["| " + " | ".join(fields) + " |", "|" + "|".join(["---"] * len(fields)) + "|"]

        # 数据行
        if rows:
            for row in rows:
                values = [str(row.get(field, "")) for field in fields]
                lines.append("| " + " | ".join(values) + " |")
        else:
            data = parsed.get("data", {})
            if isinstance(data, dict):
                values = [str(data.get(field, "")) for field in fields]
                lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> None:
    """内置自检：使用硬编码样例数据验证核心逻辑"""
    print("=" * 60)
    print("ape 自检程序启动")
    print("=" * 60)

    # 测试用例 1: JSON 解析
    print("\n[测试 1] JSON 格式探测与解析")
    json_data = '{"name": "张三", "age": 30, "city": "北京"}'
    fmt, conf = ProtocolDetector.detect(json_data)
    assert fmt == "json", f"JSON格式探测失败: {fmt}"
    assert conf > 0.5, f"JSON置信度偏低: {conf}"
    parsed, detected_fmt, _ = DataParser.parse(json_data)
    assert detected_fmt == "json", f"JSON解析格式错误: {detected_fmt}"
    assert parsed["field_count"] >= 2, f"JSON字段数量不足: {parsed['field_count']}"
    print(f"  ✓ JSON 格式探测成功，置信度: {conf:.2f}")
    print(f"  ✓ JSON 解析成功，字段数: {parsed['field_count']}")

    # 测试用例 2: CSV 解析
    print("\n[测试 2] CSV 格式探测与解析")
    csv_data = "姓名,年龄,城市\n李四,25,上海\n王五,35,广州"
    fmt, conf = ProtocolDetector.detect(csv_data)
    assert fmt == "csv", f"CSV格式探测失败: {fmt}"
    parsed, detected_fmt, _ = DataParser.parse(csv_data)
    assert detected_fmt == "csv", f"CSV解析格式错误: {detected_fmt}"
    assert parsed["row_count"] >= 1, f"CSV行数不足: {parsed['row_count']}"
    print(f"  ✓ CSV 格式探测成功，置信度: {conf:.2f}")
    print(f"  ✓ CSV 解析成功，行数: {parsed['row_count']}")

    # 测试用例 3: XML 解析
    print("\n[测试 3] XML 格式探测与解析")
    xml_data = '<root><item id="1">苹果</item><item id="2">香蕉</item></root>'
    fmt, conf = ProtocolDetector.detect(xml_data)
    assert fmt == "xml", f"XML格式探测失败: {fmt}"
    parsed, detected_fmt, _ = DataParser.parse(xml_data)
    assert detected_fmt == "xml", f"XML解析格式错误: {detected_fmt}"
    assert parsed["root"] == "root", f"XML根节点错误: {parsed['root']}"
    print(f"  ✓ XML 格式探测成功，置信度: {conf:.2f}")
    print(f"  ✓ XML 解析成功，根节点: {parsed['root']}")

    # 测试用例 4: 纯文本解析
    print("\n[测试 4] 纯文本解析")
    text_data = "姓名: 赵六\n年龄: 40\n城市: 深圳"
    fmt, conf = ProtocolDetector.detect(text_data)
    assert fmt == "text", f"文本格式探测失败: {fmt}"
    parsed, detected_fmt, _ = DataParser.parse(text_data)
    assert detected_fmt == "text", f"文本解析格式错误: {detected_fmt}"
    assert parsed["field_count"] >= 2, f"文本字段数量不足: {parsed['field_count']}"
    print(f"  ✓ 文本格式探测成功，置信度: {conf:.2f}")
    print(f"  ✓ 文本解析成功，字段数: {parsed['field_count']}")

    # 测试用例 5: 结构校验
    print("\n[测试 5] 结构校验")
    parsed, _, _ = DataParser.parse(json_data)
    validated = StructureValidator.validate(parsed)
    assert validated["valid"] is True, "结构校验应通过"
    assert validated["confidence"] in ("高", "中", "低"), "置信度等级不合法"
    print(f"  ✓ 结构校验通过，置信度: {validated['confidence']}")

    # 测试用例 6: 批量处理
    print("\n[测试 6] 批量处理")
    batch_inputs = [
        '{"a": 1, "b": 2}',
        "col1,col2\n1,2\n3,4",
        "简单文本内容",
    ]
    results = BatchProcessor.process(batch_inputs)
    assert len(results) == len(batch_inputs), f"批量处理数量错误: {len(results)}"
    success_count = sum(1 for r in results if r["success"])
    assert success_count >= 2, f"批量处理成功率过低: {success_count}/{len(results)}"
    print(f"  ✓ 批量处理成功，成功率: {success_count}/{len(results)}")

    # 测试用例 7: 输出格式化
    print("\n[测试 7] 输出格式化")
    parsed, fmt, conf = DataParser.parse(json_data)
    result = {
        "format": fmt,
        "confidence": conf,
        "parsed": parsed,
        "validated": StructureValidator.validate(parsed),
    }
    json_output = OutputFormatter.format(result, "json")
    assert json_output.startswith("{"), "JSON输出格式错误"
    md_output = OutputFormatter.format(result, "markdown")
    assert md_output.startswith("##"), "Markdown输出格式错误"
    print("  ✓ JSON 输出格式正确")
    print("  ✓ Markdown 输出格式正确")

    # 测试用例 8: 错误处理
    print("\n[测试 8] 错误处理")
    try:
        DataParser.parse("{invalid json", "json")
        assert False, "应抛出JSON解析错误"
    except SystemExit as e:
        assert e.code == 1, f"错误退出码错误: {e.code}"
    print("  ✓ JSON 错误处理正确")

    print("\n" + "=" * 60)
    print("全部自检通过！")
    print("=" * 60)


# ============================================================
# 主程序
# ============================================================
def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="ape - 协议探测、数据转换、结构校验工具",
        epilog="示例: python main.py --input '{\"name\": \"张三\"}'",
    )

    # 输入参数
    parser.add_argument("--input", "-i", type=str, help="输入文本数据")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径")
    parser.add_argument("--url", "-u", type=str, help="输入URL地址")
    parser.add_argument("--batch-file", type=str, help="批量处理文件（每行一条记录）")

    # 处理参数
    parser.add_argument("--format", type=str, choices=["auto", "json", "xml", "csv", "text"],
                        default="auto", help="指定输入格式（默认自动探测）")
    parser.add_argument("--output", "-o", type=str, choices=["json", "markdown", "table"],
                        default="json", help="输出格式（默认JSON）")

    # 功能参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="ape 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 获取输入数据
    input_data = None
    if args.input:
        input_data = InputFetcher.from_text(args.input)
    elif args.file:
        input_data = InputFetcher.from_file(args.file)
    elif args.url:
        input_data = InputFetcher.from_url(args.url)
    elif args.batch_file:
        # 读取批量文件
        content = InputFetcher.from_file(args.batch_file)
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if not lines:
            error_exit("E001", "批量文件为空")
        results = BatchProcessor.process(lines, args.format)
        # 输出批量结果
        output_data = {
            "type": "batch_result",
            "total": len(results),
            "success": sum(1 for r in results if r["success"]),
            "results": results,
        }
        print(OutputFormatter.format(output_data, args.output))
        return
    else:
        error_exit("E001", "请提供 --input, --file, --url 或 --batch-file 参数")

    # 解析数据
    parsed, fmt, confidence = DataParser.parse(input_data, args.format)

    # 校验结构
    validated = StructureValidator.validate(parsed)

    # 构建结果
    result = {
        "format": fmt,
        "confidence": confidence,
        "parsed": parsed,
        "validated": validated,
    }

    # 输出结果
    print(OutputFormatter.format(result, args.output))


if __name__ == "__main__":
    main()
