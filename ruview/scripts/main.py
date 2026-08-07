#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruview - 未命名工具
将用户提供的数据/文件/URL 转换为结构化结果，支持置信度标注与批量处理。
仅依据功能规格独立实现（clean-room），不依赖任何既有代码。
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 版本信息
VERSION = "1.0.0"
SLUG = "ruview"
DISPLAY_NAME = "未命名工具"

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "文件读取失败：{detail}",
    "E007": "JSON 解析失败：{detail}",
    "E008": "URL 格式无效：{detail}",
    "E009": "内部处理错误：{detail}",
    "E010": "未知错误：{detail}",
}


class RuViewError(Exception):
    """自定义异常，携带错误码和详细信息"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_CODES.get(code, "未知错误").format(**kwargs)
        super().__init__(self.message)


class ConfidenceCalculator:
    """置信度计算器"""

    @staticmethod
    def calculate(data: Dict[str, Any]) -> float:
        """根据数据完整性和类型一致性计算置信度"""
        if not data:
            return 0.0

        scores = []
        # 字段完整性：每个非空字段加 10 分
        for key, value in data.items():
            if value is not None and value != "":
                scores.append(10)
            else:
                scores.append(0)

        # 类型合理性：字符串长度合理、数字在有效范围等
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 0:
                scores.append(min(len(value) / 50, 1.0) * 10)
            elif isinstance(value, (int, float)) and value >= 0:
                scores.append(10)
            elif isinstance(value, list) and len(value) > 0:
                scores.append(min(len(value) / 3, 1.0) * 10)
            else:
                scores.append(5)

        if not scores:
            return 0.0
        return min(sum(scores) / (len(scores) * 10) * 100, 100.0)


class InputParser:
    """输入解析器：处理字符串、文件、URL 三种来源"""

    @staticmethod
    def parse_text(text: str) -> Dict[str, Any]:
        """解析普通文本，提取关键信息"""
        if not text or not text.strip():
            raise RuViewError("E001")

        result = {
            "content": text.strip(),
            "length": len(text.strip()),
            "type": "text",
        }

        # 尝试解析 JSON
        try:
            parsed = json.loads(text)
            result["type"] = "json"
            result["parsed"] = parsed
        except json.JSONDecodeError:
            pass

        # 尝试识别 URL
        url_pattern = re.compile(r'https?://[^\s]+')
        urls = url_pattern.findall(text)
        if urls:
            result["urls"] = urls
            result["type"] = "text_with_url"

        return result

    @staticmethod
    def parse_file(filepath: str) -> Dict[str, Any]:
        """解析文件内容"""
        path = Path(filepath)
        if not path.exists():
            raise RuViewError("E006", detail=f"文件不存在: {filepath}")
        if not path.is_file():
            raise RuViewError("E006", detail=f"不是文件: {filepath}")

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise RuViewError("E006", detail=str(e))

        result = InputParser.parse_text(content)
        result["source"] = str(path)
        result["file_name"] = path.name
        result["file_size"] = path.stat().st_size
        return result

    @staticmethod
    def parse_url(url: str) -> Dict[str, Any]:
        """解析 URL（仅校验格式，不访问网络）"""
        # 简化但更健壮的 URL 验证
        url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}'  # 域名
            r'|localhost'  # localhost
            r'|(?:\d{1,3}\.){3}\d{1,3})'  # IP
            r'(?::\d+)?'  # 端口
            r'(?:[/?#][^\s]*)?'  # 路径、查询参数、片段（可包含特殊字符）
            r'$', re.IGNORECASE
        )

        if not url_pattern.match(url):
            raise RuViewError("E008", detail=url)

        return {
            "url": url,
            "type": "url",
            "content": f"URL 引用: {url}",
        }


class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format_result(data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """按标准模板组织输出"""
        level = "直接输出" if confidence >= 90 else ("建议复核" if confidence >= 85 else "[需核实]")
        flags = []
        if confidence < 85:
            flags.append("[需核实]")
        if confidence < 90:
            flags.append("建议复核")

        return {
            "meta": {
                "tool": SLUG,
                "version": VERSION,
                "confidence": round(confidence, 1),
                "confidence_level": level,
                "flags": flags,
            },
            "data": data,
        }

    @staticmethod
    def to_json(data: Dict[str, Any]) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(data, ensure_ascii=False, indent=2)


class RuViewProcessor:
    """核心处理器"""

    def __init__(self):
        self.parser = InputParser()
        self.formatter = OutputFormatter()
        self.confidence_calc = ConfidenceCalculator()

    def process(self, input_data: str, input_type: str = "auto") -> Dict[str, Any]:
        """
        处理输入数据

        Args:
            input_data: 输入内容
            input_type: 输入类型（auto/text/file/url）

        Returns:
            处理结果字典
        """
        try:
            # Step 1: 解析输入
            if input_type == "auto":
                parsed = self._auto_parse(input_data)
            elif input_type == "text":
                parsed = self.parser.parse_text(input_data)
            elif input_type == "file":
                parsed = self.parser.parse_file(input_data)
            elif input_type == "url":
                parsed = self.parser.parse_url(input_data)
            else:
                raise RuViewError("E003", example="auto/text/file/url")

            # Step 2: 检查关键信息
            if not parsed:
                raise RuViewError("E002", missing="输入内容")

            # Step 3: 结构化处理
            structured = self._structure_data(parsed)

            # Step 4: 计算置信度
            confidence = self.confidence_calc.calculate(structured)

            # Step 5: 格式化输出
            return self.formatter.format_result(structured, confidence)

        except RuViewError:
            raise
        except Exception as e:
            raise RuViewError("E010", detail=str(e))

    def _auto_parse(self, input_data: str) -> Dict[str, Any]:
        """自动判断输入类型"""
        # 检查是否是文件路径
        path = Path(input_data)
        if path.exists() and path.is_file():
            return self.parser.parse_file(input_data)

        # 检查是否是 URL
        if input_data.startswith(("http://", "https://")):
            return self.parser.parse_url(input_data)

        # 默认按文本处理
        return self.parser.parse_text(input_data)

    def _structure_data(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """将解析结果转化为结构化数据"""
        structured = {}

        # 根据类型提取关键字段
        if parsed.get("type") == "json" and "parsed" in parsed:
            # JSON 输入：直接使用解析结果
            parsed_data = parsed["parsed"]
            if isinstance(parsed_data, dict):
                structured.update(parsed_data)
            elif isinstance(parsed_data, list):
                structured["items"] = parsed_data
                structured["item_count"] = len(parsed_data)
        else:
            # 文本输入：提取关键信息
            content = parsed.get("content", "")

            # 提取时间信息
            time_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # 日期
                r'\d{2}:\d{2}:\d{2}',  # 时间
                r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}',  # 完整时间戳
            ]
            for pattern in time_patterns:
                match = re.search(pattern, content)
                if match:
                    structured["time"] = match.group(0)
                    break

            # 提取数字信息
            numbers = re.findall(r'\d+(?:\.\d+)?', content)
            if numbers:
                structured["numbers"] = [float(n) for n in numbers[:5]]

            # 提取邮箱
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', content)
            if emails:
                structured["emails"] = emails

            # 提取电话号码
            phones = re.findall(r'\b1[3-9]\d{9}\b', content)
            if phones:
                structured["phones"] = phones

            # 保留原文
            structured["content"] = content[:200]  # 截断长文本

            # 提取 URL
            if "urls" in parsed:
                structured["urls"] = parsed["urls"]

        # 添加来源信息
        if "source" in parsed:
            structured["source"] = parsed["source"]
        if "file_name" in parsed:
            structured["file_name"] = parsed["file_name"]

        return structured

    def batch_process(self, inputs: List[str], input_type: str = "auto") -> List[Dict[str, Any]]:
        """批量处理多个输入"""
        results = []
        for item in inputs:
            try:
                result = self.process(item, input_type)
                results.append(result)
            except RuViewError as e:
                results.append({
                    "error": e.code,
                    "message": e.message,
                    "input": item,
                })
        return results


def run_selftest() -> bool:
    """内置自检程序，不依赖外部文件/网络"""
    print("=== ruview 自检开始 ===")

    processor = RuViewProcessor()

    # 测试样例 1: 文本输入
    test_text = "用户张三，邮箱 zhangsan@example.com，电话 13800138000，日期 2024-01-15"
    try:
        result = processor.process(test_text, "text")
        assert result["meta"]["confidence"] > 0, "置信度应为正数"
        assert "content" in result["data"], "应包含 content 字段"
        print("[PASS] 文本输入处理")
    except Exception as e:
        print(f"[FAIL] 文本输入处理: {e}")
        return False

    # 测试样例 2: JSON 输入
    test_json = '{"name": "测试", "value": 42, "items": [1, 2, 3]}'
    try:
        result = processor.process(test_json, "text")
        assert result["data"]["name"] == "测试", "JSON 解析失败"
        assert result["data"]["value"] == 42, "JSON 数值解析失败"
        print("[PASS] JSON 输入处理")
    except Exception as e:
        print(f"[FAIL] JSON 输入处理: {e}")
        return False

    # 测试样例 3: URL 输入（仅校验格式）
    test_url = "https://example.com/path?query=1"
    try:
        result = processor.process(test_url, "url")
        assert result["data"]["url"] == test_url, "URL 解析失败"
        print("[PASS] URL 输入处理")
    except Exception as e:
        print(f"[FAIL] URL 输入处理: {e}")
        return False

    # 测试样例 4: 空输入错误处理
    try:
        processor.process("", "text")
        print("[FAIL] 空输入应抛出 E001")
        return False
    except RuViewError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print("[PASS] 空输入错误处理")

    # 测试样例 5: 批量处理
    batch_inputs = ["第一条数据", "第二条数据", "第三条数据", ""]
    try:
        results = processor.batch_process(batch_inputs, "text")
        assert len(results) == 4, "批量处理数量不对"
        assert "error" in results[3], "空输入应产生错误结果"
        print("[PASS] 批量处理")
    except Exception as e:
        print(f"[FAIL] 批量处理: {e}")
        return False

    # 测试样例 6: 置信度计算
    try:
        high_conf = processor.process("完整数据：姓名张三，年龄30，城市北京，职业工程师", "text")
        assert high_conf["meta"]["confidence"] > 0, "置信度计算异常"
        print(f"[PASS] 置信度计算 (当前: {high_conf['meta']['confidence']:.1f}%)")
    except Exception as e:
        print(f"[FAIL] 置信度计算: {e}")
        return False

    # 测试样例 7: 错误码体系
    try:
        processor.process("not_a_file_path.txt", "file")
        print("[FAIL] 无效文件路径应抛出错误")
        return False
    except RuViewError as e:
        assert e.code in ["E006", "E001"], f"错误码应为 E006 或 E001，实际为 {e.code}"
        print(f"[PASS] 错误码体系 (触发 {e.code})")

    print("=== 所有自检通过 ===")
    return True


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - {SLUG} v{VERSION}",
        epilog="示例: python main.py --input '待处理数据' --type text"
    )
    parser.add_argument("--input", "-i", help="输入内容（文本、文件路径或 URL）")
    parser.add_argument("--type", "-t", choices=["auto", "text", "file", "url"],
                        default="auto", help="输入类型")
    parser.add_argument("--batch", "-b", nargs="+", help="批量输入（多个值）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json",
                        help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", "-v", action="version",
                        version=f"{SLUG} {VERSION}")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 检查输入
    if not args.input and not args.batch:
        print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
        sys.exit(1)

    processor = RuViewProcessor()

    try:
        # 批量处理
        if args.batch:
            results = processor.batch_process(args.batch, args.type)
        # 单条处理
        else:
            results = [processor.process(args.input, args.type)]

        # 输出结果
        if args.format == "json":
            output = json.dumps(results, ensure_ascii=False, indent=2)
        else:
            # 文本格式输出
            lines = []
            for i, result in enumerate(results, 1):
                if "error" in result:
                    lines.append(f"条目 {i}: 错误 {result['error']} - {result['message']}")
                else:
                    conf = result["meta"]["confidence"]
                    level = result["meta"]["confidence_level"]
                    lines.append(f"条目 {i}: 置信度 {conf:.1f}% ({level})")
                    for key, value in result["data"].items():
                        lines.append(f"  {key}: {value}")
            output = "\n".join(lines)

        print(output)

    except RuViewError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("操作已取消", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误 [E010]: {ERROR_CODES['E010'].format(detail=str(e))}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
