#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 数据整理、结构化输出、信息提取工具

本脚本根据功能规格独立实现（clean-room），不复制任何既有代码。
提供命令行接口与离线自检（--selftest）功能。

功能概述：
    1. 将任意文本/JSON/CSV/URL 内容解析为结构化结果。
    2. 自动识别数据类型（文本、JSON、CSV、URL）。
    3. 提取关键信息并标注置信度。
    4. 支持 --selftest 参数进行离线自检。

错误码说明：
    E001: 参数解析错误
    E002: 输入内容为空
    E003: 不支持的输入类型
    E004: JSON 解析失败
    E005: CSV 解析失败
    E006: URL 格式无效
    E007: 输出序列化失败
    E008: 自检断言失败
    E009: 文件读取失败
    E010: 内部未知错误

依赖说明：
    仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 核心数据结构
# ============================================================

class StructuredResult:
    """结构化输出结果容器"""
    
    def __init__(self, data_type: str, content: Any, confidence: float, metadata: Optional[Dict] = None):
        self.data_type = data_type          # 数据类型: text/json/csv/url
        self.content = content              # 解析后的内容
        self.confidence = confidence        # 置信度 0.0~1.0
        self.metadata = metadata or {}      # 附加元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "type": self.data_type,
            "content": self.content,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心处理逻辑
# ============================================================

class DataProcessor:
    """数据处理器：负责解析、整理、结构化输出"""
    
    # 常见 URL 前缀
    URL_PREFIXES = ("http://", "https://", "ftp://", "ftps://")
    
    def __init__(self):
        self.processed_count = 0
    
    def process(self, raw_input: str) -> StructuredResult:
        """
        处理原始输入，返回结构化结果。
        
        Args:
            raw_input: 原始输入字符串
            
        Returns:
            StructuredResult: 结构化结果
            
        Raises:
            ValueError: 输入为空或不支持的类型
        """
        if not raw_input or not raw_input.strip():
            raise ValueError("E002: 输入内容为空")
        
        # 去除首尾空白
        text = raw_input.strip()
        
        # 判断数据类型
        data_type, confidence = self._detect_type(text)
        
        # 根据类型解析内容
        if data_type == "json":
            content = self._parse_json(text)
        elif data_type == "csv":
            content = self._parse_csv(text)
        elif data_type == "url":
            content = self._parse_url(text)
        else:
            content = self._parse_text(text)
        
        # 构建元数据
        metadata = {
            "length": len(text),
            "line_count": text.count("\n") + 1,
            "has_url": bool(re.search(r'https?://', text)),
            "has_email": bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)),
            "has_phone": bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)),
            "has_date": bool(re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text)),
        }
        
        self.processed_count += 1
        return StructuredResult(data_type, content, confidence, metadata)
    
    def _detect_type(self, text: str) -> Tuple[str, float]:
        """
        检测数据类型并返回置信度。
        
        Returns:
            (data_type, confidence) 元组
        """
        # URL 检测
        if text.lower().startswith(self.URL_PREFIXES):
            # 验证 URL 格式
            parsed = urllib.parse.urlparse(text)
            if parsed.scheme and parsed.netloc:
                return "url", 0.95
            return "text", 0.5
        
        # JSON 检测
        if text.startswith(("{", "[")):
            try:
                json.loads(text)
                return "json", 0.98
            except (json.JSONDecodeError, ValueError):
                pass
        
        # CSV 检测（包含逗号且多行）
        if "," in text and "\n" in text:
            # 简单验证 CSV 结构
            lines = [l for l in text.split("\n") if l.strip()]
            if len(lines) >= 2:
                first_line_cols = len(lines[0].split(","))
                if all(len(l.split(",")) == first_line_cols for l in lines[1:3]):
                    return "csv", 0.85
        
        # 默认为文本
        return "text", 0.7
    
    def _parse_json(self, text: str) -> Any:
        """解析 JSON 内容"""
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"E004: JSON 解析失败: {e}")
    
    def _parse_csv(self, text: str) -> List[List[str]]:
        """解析 CSV 内容为二维列表"""
        try:
            reader = csv.reader(io.StringIO(text))
            rows = [row for row in reader if any(cell.strip() for cell in row)]
            return rows
        except Exception as e:
            raise ValueError(f"E005: CSV 解析失败: {e}")
    
    def _parse_url(self, text: str) -> Dict[str, str]:
        """解析 URL 信息"""
        try:
            parsed = urllib.parse.urlparse(text)
            return {
                "scheme": parsed.scheme,
                "host": parsed.netloc,
                "path": parsed.path,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "full_url": text
            }
        except Exception as e:
            raise ValueError(f"E006: URL 格式无效: {e}")
    
    def _parse_text(self, text: str) -> Dict[str, Any]:
        """解析文本内容，提取关键信息"""
        # 提取关键实体
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
        phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text)
        dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text)
        urls = re.findall(r'https?://[^\s]+', text)
        
        # 统计词频
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq: Dict[str, int] = {}
        for word in words:
            if len(word) > 2:  # 忽略过短的词
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 提取高频词（前5个）
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "text": text,
            "word_count": len(words),
            "char_count": len(text),
            "emails": emails,
            "phones": phones,
            "dates": dates,
            "urls": urls,
            "top_words": top_words,
            "summary": self._generate_summary(text)
        }
    
    def _generate_summary(self, text: str, max_len: int = 100) -> str:
        """生成文本摘要"""
        # 简单摘要：取前 N 个字符
        clean_text = re.sub(r'\s+', ' ', text).strip()
        if len(clean_text) <= max_len:
            return clean_text
        return clean_text[:max_len] + "..."
    
    def extract_info(self, result: StructuredResult) -> Dict[str, Any]:
        """
        从结构化结果中提取关键信息。
        
        Args:
            result: 结构化结果对象
            
        Returns:
            提取的关键信息字典
        """
        info: Dict[str, Any] = {}
        
        if result.data_type == "json":
            # 从 JSON 中提取键值对
            content = result.content
            if isinstance(content, dict):
                info["keys"] = list(content.keys())
                info["key_count"] = len(content)
            elif isinstance(content, list):
                info["item_count"] = len(content)
                if content and isinstance(content[0], dict):
                    info["keys"] = list(content[0].keys())
        
        elif result.data_type == "csv":
            # 从 CSV 中提取表头和数据统计
            rows = result.content
            if rows:
                info["header"] = rows[0]
                info["row_count"] = len(rows) - 1
                info["column_count"] = len(rows[0])
        
        elif result.data_type == "url":
            # URL 信息已包含在 content 中
            info.update(result.content)
        
        else:  # text
            # 文本信息已包含在 content 中
            content = result.content
            if isinstance(content, dict):
                info["emails"] = content.get("emails", [])
                info["phones"] = content.get("phones", [])
                info["dates"] = content.get("dates", [])
                info["urls"] = content.get("urls", [])
                info["word_count"] = content.get("word_count", 0)
        
        return info


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    
    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    
    Returns:
        True 表示自检通过，否则抛出异常
        
    Raises:
        AssertionError: 自检断言失败
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)
    
    processor = DataProcessor()
    
    # ---------- 测试用例 1: 文本处理 ----------
    print("\n[测试 1] 文本处理")
    sample_text = """
    张三的联系方式是 zhang.san@example.com，电话 138-1234-5678。
    项目开始日期是 2024-01-15，预计 2024-06-30 完成。
    更多信息请访问 https://example.com/project。
    这是一个简单的测试文本，用于验证文本解析功能。
    """
    try:
        result = processor.process(sample_text)
        assert result.data_type == "text", f"预期 text，实际 {result.data_type}"
        assert result.confidence >= 0.5, f"置信度过低: {result.confidence}"
        assert isinstance(result.content, dict), "文本解析结果应为字典"
        assert result.content["word_count"] > 10, "词数应大于10"
        assert len(result.content["emails"]) >= 1, "应至少提取1个邮箱"
        assert len(result.content["phones"]) >= 1, "应至少提取1个电话"
        assert len(result.content["dates"]) >= 1, "应至少提取1个日期"
        assert len(result.content["urls"]) >= 1, "应至少提取1个URL"
        print(f"  ✓ 通过 (类型={result.data_type}, 置信度={result.confidence:.2f})")
    except AssertionError as e:
        raise AssertionError(f"E008: 文本处理自检失败: {e}")
    
    # ---------- 测试用例 2: JSON 处理 ----------
    print("\n[测试 2] JSON 处理")
    sample_json = """
    {
        "name": "测试项目",
        "version": "1.0.0",
        "dependencies": ["numpy", "pandas", "requests"],
        "settings": {
            "debug": true,
            "timeout": 30,
            "retry": 3
        },
        "tags": ["python", "test", "demo"]
    }
    """
    try:
        result = processor.process(sample_json)
        assert result.data_type == "json", f"预期 json，实际 {result.data_type}"
        assert result.confidence >= 0.8, f"JSON 置信度应较高: {result.confidence}"
        assert isinstance(result.content, dict), "JSON 解析结果应为字典"
        assert "name" in result.content, "JSON 应包含 name 字段"
        assert result.content["version"] == "1.0.0", "version 字段值错误"
        assert len(result.content["dependencies"]) >= 2, "依赖列表应包含多个元素"
        print(f"  ✓ 通过 (类型={result.data_type}, 置信度={result.confidence:.2f})")
    except AssertionError as e:
        raise AssertionError(f"E008: JSON 处理自检失败: {e}")
    
    # ---------- 测试用例 3: CSV 处理 ----------
    print("\n[测试 3] CSV 处理")
    sample_csv = """姓名,年龄,城市,职业
张三,28,北京,工程师
李四,35,上海,设计师
王五,42,广州,经理
赵六,31,深圳,产品经理
"""
    try:
        result = processor.process(sample_csv)
        assert result.data_type == "csv", f"预期 csv，实际 {result.data_type}"
        assert result.confidence >= 0.7, f"CSV 置信度应较高: {result.confidence}"
        assert isinstance(result.content, list), "CSV 解析结果应为列表"
        assert len(result.content) >= 3, "CSV 应包含多行数据"
        assert result.content[0] == ["姓名", "年龄", "城市", "职业"], "CSV 表头错误"
        assert len(result.content[1]) == 4, "CSV 数据列数应为4"
        print(f"  ✓ 通过 (类型={result.data_type}, 置信度={result.confidence:.2f})")
    except AssertionError as e:
        raise AssertionError(f"E008: CSV 处理自检失败: {e}")
    
    # ---------- 测试用例 4: URL 处理 ----------
    print("\n[测试 4] URL 处理")
    sample_url = "https://example.com/api/v1/users?page=2&limit=10#section"
    try:
        result = processor.process(sample_url)
        assert result.data_type == "url", f"预期 url，实际 {result.data_type}"
        assert result.confidence >= 0.8, f"URL 置信度应较高: {result.confidence}"
        assert isinstance(result.content, dict), "URL 解析结果应为字典"
        assert result.content["scheme"] == "https", "URL scheme 应为 https"
        assert result.content["host"] == "example.com", "URL host 应为 example.com"
        assert "path" in result.content, "URL 应包含 path"
        assert "query" in result.content, "URL 应包含 query"
        print(f"  ✓ 通过 (类型={result.data_type}, 置信度={result.confidence:.2f})")
    except AssertionError as e:
        raise AssertionError(f"E008: URL 处理自检失败: {e}")
    
    # ---------- 测试用例 5: 信息提取 ----------
    print("\n[测试 5] 信息提取")
    try:
        result = processor.process(sample_json)
        info = processor.extract_info(result)
        assert "keys" in info, "JSON 信息提取应包含 keys"
        assert info["key_count"] >= 3, "JSON 键数量应大于等于3"
        
        result = processor.process(sample_csv)
        info = processor.extract_info(result)
        assert "header" in info, "CSV 信息提取应包含 header"
        assert info["row_count"] >= 3, "CSV 行数应大于等于3"
        
        result = processor.process(sample_text)
        info = processor.extract_info(result)
        assert len(info["emails"]) >= 1, "文本信息提取应包含邮箱"
        assert len(info["phones"]) >= 1, "文本信息提取应包含电话"
        print(f"  ✓ 通过")
    except AssertionError as e:
        raise AssertionError(f"E008: 信息提取自检失败: {e}")
    
    # ---------- 测试用例 6: 错误处理 ----------
    print("\n[测试 6] 错误处理")
    try:
        # 空输入
        try:
            processor.process("")
            raise AssertionError("空输入应抛出异常")
        except ValueError as e:
            assert "E002" in str(e), f"错误码应为 E002，实际: {e}"
        
        # 无效 JSON
        try:
            processor.process('{"invalid": json}')
            raise AssertionError("无效 JSON 应抛出异常")
        except ValueError as e:
            assert "E004" in str(e), f"错误码应为 E004，实际: {e}"
        
        print(f"  ✓ 通过")
    except AssertionError as e:
        raise AssertionError(f"E008: 错误处理自检失败: {e}")
    
    # ---------- 测试用例 7: 边界情况 ----------
    print("\n[测试 7] 边界情况")
    try:
        # 纯数字文本
        result = processor.process("1234567890")
        assert result.data_type == "text", "纯数字应识别为文本"
        
        # 单行文本
        result = processor.process("Hello World")
        assert result.data_type == "text", "单行文本应识别为文本"
        assert result.content["word_count"] >= 2, "词数应大于等于2"
        
        # 带空格的 JSON
        result = processor.process('  {"key": "value"}  ')
        assert result.data_type == "json", "带空格的 JSON 应识别为 JSON"
        
        print(f"  ✓ 通过")
    except AssertionError as e:
        raise AssertionError(f"E008: 边界情况自检失败: {e}")
    
    # ---------- 测试用例 8: 处理计数 ----------
    print("\n[测试 8] 处理计数")
    try:
        initial_count = processor.processed_count
        processor.process("测试1")
        processor.process("测试2")
        processor.process("测试3")
        assert processor.processed_count == initial_count + 3, "处理计数应增加3"
        print(f"  ✓ 通过 (总处理数={processor.processed_count})")
    except AssertionError as e:
        raise AssertionError(f"E008: 处理计数自检失败: {e}")
    
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行接口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="数据整理、结构化输出、信息提取工具",
        epilog="示例: python main.py --input 'https://example.com' --output json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本、JSON、CSV 或 URL）"
    )
    
    parser.add_argument(
        "--input-file", "-f",
        type=str,
        help="从文件读取输入内容"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text", "info"],
        default="json",
        help="输出格式: json（默认）、text、info"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="ok 1.0.2"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"E010: 自检异常: {e}", file=sys.stderr)
            return 1
    
    # 处理模式
    try:
        # 获取输入
        if args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except Exception as e:
                print(f"E009: 文件读取失败: {e}", file=sys.stderr)
                return 1
        elif args.input:
            raw_input = args.input
        else:
            print("E001: 请提供 --input 或 --input-file 参数", file=sys.stderr)
            return 1
        
        # 处理数据
        processor = DataProcessor()
        result = processor.process(raw_input)
        
        # 输出结果
        if args.output == "json":
            print(result.to_json())
        elif args.output == "text":
            content = result.content
            if isinstance(content, dict):
                for key, value in content.items():
                    print(f"{key}: {value}")
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, list):
                        print(", ".join(str(x) for x in item))
                    else:
                        print(item)
            else:
                print(content)
        elif args.output == "info":
            info = processor.extract_info(result)
            print(json.dumps(info, ensure_ascii=False, indent=2))
        
        return 0
        
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
