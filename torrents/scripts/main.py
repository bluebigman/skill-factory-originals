#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - torrents 技能核心实现（clean-room 重写）

本脚本仅依据功能规格说明独立实现，不包含任何既有代码。
功能：将用户输入的数据/文件/URL 解析为结构化结果，并支持自检。
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "文件读取失败，请检查路径",
    "E008": "JSON 解析失败，请检查格式",
    "E009": "输出写入失败，请检查权限",
    "E010": "参数错误，请检查命令行参数",
}


class SkillError(Exception):
    """技能异常基类"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class StructuredRecord:
    """结构化记录类"""

    def __init__(self, raw_text: str):
        self.raw_text = raw_text.strip()
        self.fields: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.notes: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "raw_text": self.raw_text,
            "fields": self.fields,
            "confidence": self.confidence,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def parse_input(raw_input: str) -> StructuredRecord:
    """解析输入内容，识别关键信息并结构化"""
    if not raw_input or not raw_input.strip():
        raise SkillError("E001")

    record = StructuredRecord(raw_input)

    # 尝试解析 JSON 格式
    try:
        data = json.loads(raw_input)
        if isinstance(data, dict):
            record.fields = data
            record.confidence = 0.95  # 宽松阈值
            record.notes.append("已识别为 JSON 字典格式")
            return record
        elif isinstance(data, list):
            record.fields = {"items": data}
            record.confidence = 0.90
            record.notes.append("已识别为 JSON 数组格式")
            return record
    except json.JSONDecodeError:
        pass  # 非 JSON，继续尝试其他格式

    # 尝试解析 key=value 格式（支持多行）
    kv_pairs: Dict[str, str] = {}
    lines = raw_input.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            kv_pairs[key.strip()] = value.strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            kv_pairs[key.strip()] = value.strip()

    if kv_pairs:
        record.fields = kv_pairs
        record.confidence = 0.88  # 宽松阈值
        record.notes.append("已识别为 key=value 格式")
        return record

    # 尝试解析 CSV 格式（简单按逗号分隔）
    if "," in raw_input:
        parts = [p.strip() for p in raw_input.split(",") if p.strip()]
        if len(parts) >= 2:
            record.fields = {"values": parts}
            record.confidence = 0.85
            record.notes.append("已识别为逗号分隔格式")
            return record

    # 无法识别为结构化格式，按纯文本处理
    record.fields = {"text": record.raw_text}
    record.confidence = 0.75  # 宽松阈值
    record.notes.append("未识别为结构化格式，按纯文本处理")
    return record


def process_input(raw_input: str, output_format: str = "json") -> Dict[str, Any]:
    """执行核心流程：解析输入并生成输出"""
    record = parse_input(raw_input)

    # 根据置信度设置标注
    if record.confidence >= 0.90:
        marker = "直接输出"
    elif record.confidence >= 0.85:
        marker = "建议复核"
    else:
        marker = "[需核实]"

    result = record.to_dict()
    result["marker"] = marker

    # 按输出格式组织
    if output_format == "json":
        return result
    elif output_format == "text":
        # 文本格式输出
        lines = [f"原始输入: {record.raw_text}"]
        lines.append(f"置信度: {record.confidence:.0%} ({marker})")
        lines.append("字段:")
        for key, value in record.fields.items():
            lines.append(f"  {key}: {value}")
        lines.append("备注:")
        for note in record.notes:
            lines.append(f"  - {note}")
        return {"text_output": "\n".join(lines)}
    else:
        raise SkillError("E003", f"不支持的输出格式: {output_format}")


def process_file(file_path: str, output_format: str = "json") -> Dict[str, Any]:
    """处理文件输入"""
    if not os.path.exists(file_path):
        raise SkillError("E007", f"文件不存在: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise SkillError("E007", f"读取文件失败: {e}")

    if not content.strip():
        raise SkillError("E001")

    return process_input(content, output_format)


def process_url(url: str, output_format: str = "json") -> Dict[str, Any]:
    """处理 URL 输入（仅解析 URL 本身，不访问网络）"""
    # 本技能不访问网络，仅解析 URL 字符串
    record = StructuredRecord(url)
    record.fields = {
        "url": url,
        "scheme": url.split("://")[0] if "://" in url else "",
        "path": url.split("://")[-1].split("/")[0] if "://" in url else url,
    }
    record.confidence = 0.80  # 宽松阈值
    record.notes.append("已解析 URL 基本信息（未访问网络）")

    result = record.to_dict()
    result["marker"] = "[需核实]"
    return result


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("=== 开始自检 (selftest) ===")
    all_passed = True

    # 样例 1: JSON 字典输入
    print("\n[测试 1] JSON 字典输入")
    try:
        sample = '{"name": "测试", "age": 25}'
        result = process_input(sample, "json")
        assert result["fields"].get("name") == "测试", "字段 name 解析错误"
        assert result["confidence"] >= 0.90, "JSON 解析置信度应较高"
        assert result["marker"] == "直接输出", "高置信度应直接输出"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")

    # 样例 2: key=value 输入
    print("\n[测试 2] key=value 输入")
    try:
        sample = "name=张三\nage=30\ncity=北京"
        result = process_input(sample, "json")
        assert result["fields"].get("name") == "张三", "key=value 解析错误"
        assert result["confidence"] >= 0.85, "key=value 置信度应较高"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")

    # 样例 3: 逗号分隔输入
    print("\n[测试 3] 逗号分隔输入")
    try:
        sample = "苹果,香蕉,橙子"
        result = process_input(sample, "json")
        assert "values" in result["fields"], "逗号分隔应生成 values 字段"
        assert len(result["fields"]["values"]) >= 3, "应有至少3个值"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")

    # 样例 4: 空输入应报 E001
    print("\n[测试 4] 空输入错误处理")
    try:
        process_input("")
        all_passed = False
        print("  失败: 空输入未抛出异常")
    except SkillError as e:
        assert e.code == "E001", f"期望 E001，实际 {e.code}"
        print("  通过")

    # 样例 5: 文件处理
    print("\n[测试 5] 文件处理")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("name=测试文件\nsize=1024")
            tmp_path = f.name
        try:
            result = process_file(tmp_path, "json")
            assert result["fields"].get("name") == "测试文件", "文件内容解析错误"
            print("  通过")
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")

    # 样例 6: URL 输入
    print("\n[测试 6] URL 输入")
    try:
        sample = "https://example.com/path/to/resource"
        result = process_url(sample, "json")
        assert result["fields"].get("scheme") == "https", "URL scheme 解析错误"
        assert result["fields"].get("path") == "example.com", "URL 域名解析错误"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")

    # 样例 7: 文本输出格式
    print("\n[测试 7] 文本输出格式")
    try:
        sample = "name=测试"
        result = process_input(sample, "text")
        assert "text_output" in result, "文本输出应包含 text_output 字段"
        assert "置信度" in result["text_output"], "文本输出应包含置信度"
        print("  通过")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")

    print(f"\n=== 自检完成: {'全部通过' if all_passed else '存在失败项'} ===")
    return all_passed


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="torrents 技能 - SQL查询辅助工具",
        epilog="示例: python main.py --input 'name=张三,age=30' --format json",
    )
    parser.add_argument("--input", "-i", help="输入内容（文本/JSON/URL）")
    parser.add_argument("--file", "-f", help="输入文件路径")
    parser.add_argument("--url", "-u", help="输入 URL")
    parser.add_argument("--format", "-o", choices=["json", "text"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version="torrents 1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 正常处理模式
    try:
        # 确定输入来源
        if args.input:
            result = process_input(args.input, args.format)
        elif args.file:
            result = process_file(args.file, args.format)
        elif args.url:
            result = process_url(args.url, args.format)
        else:
            raise SkillError("E001")

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["text_output"])

        return 0

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E006']}] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
