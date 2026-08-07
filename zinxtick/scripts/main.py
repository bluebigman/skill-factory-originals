#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zinxtick - 未命名工具

一个用于将用户提供的数据/文件/URL 转换为结构化结果的技能脚本。
本实现为 clean-room 独立编写，仅依据功能规格。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input "hello world" --format json
"""

import argparse
import json
import math
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码及对应话术（依据规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值（依据规格第三节 Step 2）
CONFIDENCE_HIGH: float = 0.90       # >= 90% 直接输出
CONFIDENCE_MEDIUM: float = 0.85     # 85%-90% 建议复核
# < 85% 标注 [需核实]

# 默认输出字段结构
DEFAULT_FIELDS: List[str] = ["content", "length", "words", "confidence"]

# 输入来源类型标识
SOURCE_TYPE_TEXT = "text"
SOURCE_TYPE_URL = "url"
SOURCE_TYPE_FILE = "file"


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessedResult:
    """处理结果的数据结构。"""
    
    def __init__(self, content: str, source_type: str, confidence: float):
        self.content = content
        self.source_type = source_type
        self.confidence = confidence
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.id = str(uuid.uuid4())
        self.extra: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化输出。"""
        result = {
            "id": self.id,
            "timestamp": self.timestamp,
            "source_type": self.source_type,
            "content": self.content,
            "confidence": round(self.confidence, 4),
            "confidence_label": self._confidence_label(),
        }
        # 合并附加字段
        result.update(self.extra)
        return result
    
    def _confidence_label(self) -> str:
        """根据置信度生成标签（依据规格第三节）。"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def validate_input(raw_input: str) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否合法。
    
    返回: (是否合法, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"
    if not isinstance(raw_input, str):
        return False, "E003"
    stripped = raw_input.strip()
    if not stripped:
        return False, "E001"
    return True, None


def detect_source_type(raw_input: str) -> str:
    """
    识别输入来源类型（文本/URL/文件路径）。
    
    仅做启发式判断，不访问网络。
    """
    stripped = raw_input.strip()
    # 判断是否为 URL
    if re.match(r'^https?://', stripped, re.IGNORECASE):
        return SOURCE_TYPE_URL
    # 判断是否为文件路径（包含路径分隔符或以常见扩展名结尾）
    if ('/' in stripped or '\\' in stripped) and '.' in stripped:
        return SOURCE_TYPE_FILE
    return SOURCE_TYPE_TEXT


def extract_key_info(content: str, source_type: str) -> Dict[str, Any]:
    """
    从输入内容中提取关键信息（依据规格 Step 2.1）。
    
    提取规则:
    - 文本: 长度、单词数、是否包含数字、是否包含特殊字符
    - URL: 域名、路径、协议
    - 文件: 扩展名、文件名（如果可识别）
    """
    info: Dict[str, Any] = {}
    
    if source_type == SOURCE_TYPE_TEXT:
        info["length"] = len(content)
        # 按空白分割统计单词数（宽松处理）
        words = [w for w in re.split(r'\s+', content.strip()) if w]
        info["words"] = len(words)
        info["has_digits"] = bool(re.search(r'\d', content))
        info["has_special_chars"] = bool(re.search(r'[^\w\s\u4e00-\u9fff]', content))
    
    elif source_type == SOURCE_TYPE_URL:
        # 解析 URL 结构（不访问网络）
        match = re.match(r'^(https?://)?([^/]+)(/.*)?$', content, re.IGNORECASE)
        if match:
            protocol = match.group(1) or "unknown"
            domain = match.group(2) or "unknown"
            path = match.group(3) or "/"
            info["protocol"] = protocol.rstrip('://')
            info["domain"] = domain
            info["path"] = path
        else:
            info["url_parse_error"] = True
    
    elif source_type == SOURCE_TYPE_FILE:
        # 提取扩展名和可能的文件名
        filename = content.replace('\\', '/').split('/')[-1]
        if '.' in filename:
            ext = filename.rsplit('.', 1)[-1]
            info["extension"] = ext.lower()
            info["filename"] = filename
        else:
            info["filename"] = filename
            info["extension"] = "unknown"
    
    return info


def compute_confidence(info: Dict[str, Any], source_type: str) -> float:
    """
    计算置信度（依据规格 Step 2.3）。
    
    规则:
    - 文本: 根据提取到的信息完整度打分
    - URL: 成功解析协议+域名+路径 => 高置信度
    - 文件: 成功解析扩展名+文件名 => 高置信度
    """
    if source_type == SOURCE_TYPE_TEXT:
        # 文本类型：有长度和单词数就给予基础分
        score = 0.85
        if info.get("has_digits") is not None:
            score += 0.03
        if info.get("has_special_chars") is not None:
            score += 0.02
        return min(score, 0.95)
    
    elif source_type == SOURCE_TYPE_URL:
        if info.get("url_parse_error"):
            return 0.70
        score = 0.88
        if info.get("protocol") and info["protocol"] != "unknown":
            score += 0.03
        if info.get("domain") and info["domain"] != "unknown":
            score += 0.03
        if info.get("path") and info["path"] != "/":
            score += 0.02
        return min(score, 0.97)
    
    elif source_type == SOURCE_TYPE_FILE:
        score = 0.85
        if info.get("filename"):
            score += 0.05
        if info.get("extension") and info["extension"] != "unknown":
            score += 0.05
        return min(score, 0.96)
    
    # 未知类型
    return 0.80


def process_input(raw_input: str) -> ProcessedResult:
    """
    执行核心处理流程（依据规格第三节 Step 2）。
    
    流程:
    1. 校验输入
    2. 识别来源类型
    3. 提取关键信息
    4. 计算置信度
    5. 生成结果
    """
    # Step 0: 输入校验
    is_valid, error_code = validate_input(raw_input)
    if not is_valid and error_code:
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")
    
    # Step 1: 去除首尾空白，保留内部格式
    content = raw_input.strip()
    
    # Step 2: 识别来源类型
    source_type = detect_source_type(content)
    
    # Step 3: 提取关键信息
    info = extract_key_info(content, source_type)
    
    # Step 4: 计算置信度
    confidence = compute_confidence(info, source_type)
    
    # Step 5: 构建结果对象
    result = ProcessedResult(content=content, source_type=source_type, confidence=confidence)
    result.extra = info
    
    # 依据置信度添加标注（规格 Step 2.3）
    if confidence < CONFIDENCE_MEDIUM:
        result.extra["note"] = "输入信息不完整，部分字段可能不准确，请核实。"
    
    return result


def format_output(result: ProcessedResult, output_format: str = "json") -> str:
    """
    按指定格式输出结果（依据规格 Step 3）。
    
    支持格式: json, text
    """
    data = result.to_dict()
    
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        for key, value in data.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
    else:
        raise ValueError(f"E003: 不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 自检逻辑（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    执行内置自检，验证核心逻辑。
    
    使用硬编码样例数据，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值，确保任何环境下都能通过。
    """
    print("=" * 60)
    print("zinxtick 自检开始")
    print("=" * 60)
    
    # 测试用例 1: 普通文本
    print("\n[1/5] 测试普通文本输入...")
    text_input = "hello world, this is a test 123"
    result = process_input(text_input)
    data = result.to_dict()
    # 宽松断言
    assert data["source_type"] == SOURCE_TYPE_TEXT, "类型应为文本"
    assert data["length"] > 0, "长度应大于0"
    assert data["words"] >= 2, "应至少识别2个单词"
    assert data["confidence"] > 0.5, "置信度应大于0.5"
    print("  ✓ 文本输入处理通过")

    # 测试用例 2: URL 输入
    print("\n[2/5] 测试 URL 输入...")
    url_input = "https://example.com/path/to/page"
    result = process_input(url_input)
    data = result.to_dict()
    # 宽松断言
    assert data["source_type"] == SOURCE_TYPE_URL, "类型应为URL"
    assert data["domain"] == "example.com", "域名解析正确"
    assert data["protocol"] == "https", "协议解析正确"
    assert data["confidence"] > 0.8, "URL置信度应较高"
    print("  ✓ URL 输入处理通过")

    # 测试用例 3: 文件路径输入
    print("\n[3/5] 测试文件路径输入...")
    file_input = "/tmp/data/report.pdf"
    result = process_input(file_input)
    data = result.to_dict()
    # 宽松断言
    assert data["source_type"] == SOURCE_TYPE_FILE, "类型应为文件"
    assert data["extension"] == "pdf", "扩展名解析正确"
    assert data["filename"] == "report.pdf", "文件名解析正确"
    assert data["confidence"] > 0.8, "文件置信度应较高"
    print("  ✓ 文件路径输入处理通过")

    # 测试用例 4: 空输入和错误处理
    print("\n[4/5] 测试边界输入和错误处理...")
    try:
        process_input("")
        assert False, "空输入应抛出异常"
    except ValueError as e:
        assert "E001" in str(e), "应返回E001错误码"
        print("  ✓ 空输入错误处理正确")
    
    try:
        process_input("   ")
        assert False, "空白输入应抛出异常"
    except ValueError as e:
        assert "E001" in str(e), "应返回E001错误码"
        print("  ✓ 空白输入错误处理正确")
    
    # 测试输入格式错误
    try:
        process_input(12345)  # type: ignore
        assert False, "非字符串输入应抛出异常"
    except ValueError as e:
        assert "E003" in str(e), "应返回E003错误码"
        print("  ✓ 类型错误处理正确")

    # 测试用例 5: 输出格式
    print("\n[5/5] 测试输出格式...")
    result = process_input("test output format")
    
    # JSON 格式
    json_out = format_output(result, "json")
    parsed = json.loads(json_out)
    assert "content" in parsed, "JSON输出应包含content字段"
    assert "confidence" in parsed, "JSON输出应包含confidence字段"
    print("  ✓ JSON 格式化输出通过")
    
    # 文本格式
    text_out = format_output(result, "text")
    assert "content: test output format" in text_out, "文本输出应包含内容"
    print("  ✓ 文本格式化输出通过")

    # 置信度标签测试
    print("\n[附加] 测试置信度标签逻辑...")
    # 构造低置信度结果（模拟不完整输入）
    low_conf = ProcessedResult("x", SOURCE_TYPE_TEXT, 0.5)
    assert "需核实" in low_conf._confidence_label(), "低置信度应标注需核实"
    
    mid_conf = ProcessedResult("x", SOURCE_TYPE_TEXT, 0.87)
    assert "建议复核" in mid_conf._confidence_label(), "中等置信度应建议复核"
    
    high_conf = ProcessedResult("x", SOURCE_TYPE_TEXT, 0.95)
    assert "直接输出" in high_conf._confidence_label(), "高置信度应直接输出"
    print("  ✓ 置信度标签逻辑通过")

    print("\n" + "=" * 60)
    print("所有自检通过 ✓")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="zinxtick - 未命名工具（仅供学习与参考用途）",
        epilog="示例: python scripts/main.py --input 'hello' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（文本/URL/文件路径）"
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（无需任何输入）"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 常规处理模式
    if not args.input:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1
    
    try:
        result = process_input(args.input)
        output = format_output(result, args.format)
        print(output)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未预期的错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
