#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lazy-record —— 概念验证脚本
================================
功能概述：
    本脚本实现了一个轻量级的数据惰性加载与结构化处理工具。
    它模拟 ActiveRecord 风格的"延迟加载"（Lazy-Loading）思想，
    将用户提供的数据/文件/URL 转换为结构化结果，
    并对不确定项给出置信度提示。

设计原则：
    1. 标准库优先，无第三方依赖。
    2. 所有核心逻辑均可离线自检（--selftest）。
    3. 错误处理使用 E001-E010 错误码体系。

运行方式：
    python scripts/main.py --selftest        # 离线自检
    python scripts/main.py --process "文本"   # 处理文本
    python scripts/main.py --help            # 帮助信息
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容（数据/文件/URL）。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查输入格式是否符合要求。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定，建议人工复核。",
    "E006": "文件读取失败，请检查文件路径和权限。",
    "E007": "URL 解析失败，请检查 URL 格式。",
    "E008": "内部处理逻辑异常，请联系开发者。",
    "E009": "参数错误，请检查命令行参数。",
    "E010": "未知错误，请稍后重试或联系开发者。",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class Record:
    """惰性记录对象，模拟 ActiveRecord 的延迟加载行为。"""
    source: str                        # 数据来源（文本/文件/URL）
    data: Dict[str, Any] = field(default_factory=dict)   # 结构化数据
    confidence: float = 0.0            # 置信度（0.0 - 1.0）
    _loaded: bool = False              # 是否已加载（惰性标志）
    _lazy_loader: Optional[callable] = None  # 延迟加载函数

    def __post_init__(self) -> None:
        """初始化后设置默认惰性加载器。"""
        if not self._lazy_loader:
            self._lazy_loader = self._default_loader

    def _default_loader(self) -> Dict[str, Any]:
        """默认惰性加载器：从 source 中提取结构化信息。"""
        # 根据来源类型分发处理
        if self.source.startswith("http://") or self.source.startswith("https://"):
            return self._parse_url(self.source)
        elif os.path.isfile(self.source):
            return self._parse_file(self.source)
        else:
            return self._parse_text(self.source)

    def load(self) -> Dict[str, Any]:
        """执行惰性加载，返回结构化数据。"""
        if not self._loaded:
            try:
                self.data = self._lazy_loader()
                self._loaded = True
                self._update_confidence()
            except Exception as e:
                # 使用 E008 错误码
                raise ProcessingError("E008", f"加载数据失败: {str(e)}")
        return self.data

    def _update_confidence(self) -> None:
        """根据数据完整性计算置信度。"""
        if not self.data:
            self.confidence = 0.0
            return
        
        # 基础置信度
        base = 0.7
        
        # 根据字段数量增加置信度
        field_count = len(self.data)
        if field_count >= 5:
            base += 0.2
        elif field_count >= 3:
            base += 0.1
        
        # 根据字段完整性调整
        required_fields = ["type", "content"]
        for field_name in required_fields:
            if field_name in self.data:
                base += 0.05
        
        # 限制在 0-1 之间
        self.confidence = min(1.0, max(0.0, base))

    def _parse_text(self, text: str) -> Dict[str, Any]:
        """解析纯文本输入。"""
        if not text or not text.strip():
            raise ProcessingError("E001", ERROR_CODES["E001"])
        
        # 提取关键信息
        result = {
            "type": "text",
            "content": text.strip(),
            "length": len(text.strip()),
            "words": len(text.split()),
        }
        
        # 尝试识别 URL 和邮箱
        urls = re.findall(r'https?://[^\s]+', text)
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        
        if urls:
            result["urls"] = urls
        if emails:
            result["emails"] = emails
        
        return result

    def _parse_file(self, filepath: str) -> Dict[str, Any]:
        """解析文件输入。"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise ProcessingError("E006", f"文件读取失败: {str(e)}")
        
        result = {
            "type": "file",
            "path": filepath,
            "content": content[:1000],  # 只保留前 1000 字符
            "size": os.path.getsize(filepath),
        }
        
        return result

    def _parse_url(self, url: str) -> Dict[str, Any]:
        """解析 URL 输入（不访问网络，仅解析结构）。"""
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            raise ProcessingError("E007", f"URL 解析失败: {str(e)}")
        
        result = {
            "type": "url",
            "url": url,
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
        }
        
        # 尝试提取查询参数
        if parsed.query:
            params = urllib.parse.parse_qs(parsed.query)
            result["params"] = {k: v[0] for k, v in params.items()}
        
        return result


class ProcessingError(Exception):
    """处理异常类，包含错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心处理引擎
# ============================================================
class LazyRecordProcessor:
    """惰性记录处理器，负责任务调度与结果输出。"""
    
    def __init__(self, input_data: Optional[str] = None, output_format: str = "json"):
        self.input_data = input_data
        self.output_format = output_format
        self.records: List[Record] = []
        self.results: List[Dict[str, Any]] = []

    def process(self) -> List[Dict[str, Any]]:
        """执行处理流程，返回结构化结果列表。"""
        # Step 1: 检查输入
        if not self.input_data:
            raise ProcessingError("E001", ERROR_CODES["E001"])
        
        # Step 2: 创建记录并惰性加载
        record = Record(source=self.input_data)
        self.records.append(record)
        
        # 执行加载
        data = record.load()
        
        # Step 3: 标注置信度
        if record.confidence >= 0.9:
            status = "直接输出"
        elif record.confidence >= 0.85:
            status = "建议复核"
        else:
            status = "需核实"
        
        result = {
            "source": self.input_data,
            "data": data,
            "confidence": record.confidence,
            "status": status,
            "message": "处理完成" if status == "直接输出" else status
        }
        
        self.results.append(result)
        return self.results

    def format_output(self) -> str:
        """按指定格式输出结果。"""
        if self.output_format == "json":
            return json.dumps(self.results, ensure_ascii=False, indent=2)
        elif self.output_format == "text":
            lines = []
            for i, result in enumerate(self.results, 1):
                lines.append(f"记录 {i}:")
                lines.append(f"  来源: {result['source']}")
                lines.append(f"  置信度: {result['confidence']:.2f}")
                lines.append(f"  状态: {result['status']}")
                lines.append(f"  数据: {json.dumps(result['data'], ensure_ascii=False)}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ProcessingError("E003", f"不支持的输出格式: {self.output_format}")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖任何外部资源。
    所有断言使用宽松阈值（大小比较/区间判断），确保稳健。
    """
    print("=" * 60)
    print("开始自检 lazy-record 核心功能...")
    print("=" * 60)
    
    test_cases = []
    passed = 0
    failed = 0
    
    # ---- 测试用例 1: 文本输入 ----
    print("\n[测试 1] 文本输入处理")
    try:
        processor = LazyRecordProcessor("这是一个测试文本，包含 https://example.com 和 test@email.com")
        results = processor.process()
        assert len(results) == 1, "应返回 1 条记录"
        result = results[0]
        assert result["data"]["type"] == "text", "类型应为 text"
        assert result["data"]["length"] > 0, "长度应大于 0"
        assert result["confidence"] > 0.5, "置信度应大于 0.5"
        assert "urls" in result["data"], "应识别出 URL"
        assert "emails" in result["data"], "应识别出邮箱"
        print("  ✓ 文本输入处理通过")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 文本输入处理失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ 文本输入处理异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 测试用例 2: URL 输入 ----
    print("\n[测试 2] URL 输入处理")
    try:
        processor = LazyRecordProcessor("https://example.com/path?key=value&page=1")
        results = processor.process()
        result = results[0]
        assert result["data"]["type"] == "url", "类型应为 url"
        assert result["data"]["host"] == "example.com", "主机名应正确"
        assert "params" in result["data"], "应解析查询参数"
        assert result["data"]["params"]["key"] == "value", "参数值应正确"
        print("  ✓ URL 输入处理通过")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ URL 输入处理失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ URL 输入处理异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 测试用例 3: 文件输入（临时文件） ----
    print("\n[测试 3] 文件输入处理")
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("这是一个临时文件内容，用于测试文件输入功能。")
            temp_path = f.name
        
        try:
            processor = LazyRecordProcessor(temp_path)
            results = processor.process()
            result = results[0]
            assert result["data"]["type"] == "file", "类型应为 file"
            assert result["data"]["size"] > 0, "文件大小应大于 0"
            assert "content" in result["data"], "应包含文件内容"
            print("  ✓ 文件输入处理通过")
            passed += 1
        finally:
            # 清理临时文件
            os.unlink(temp_path)
    except AssertionError as e:
        print(f"  ✗ 文件输入处理失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ 文件输入处理异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 测试用例 4: 空输入错误处理 ----
    print("\n[测试 4] 空输入错误处理")
    try:
        processor = LazyRecordProcessor("")
        processor.process()
        print("  ✗ 空输入应触发错误，但未触发")
        failed += 1
    except ProcessingError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print("  ✓ 空输入错误处理通过")
        passed += 1
    except Exception as e:
        print(f"  ✗ 空输入处理异常: {e}")
        failed += 1
    
    # ---- 测试用例 5: 批量处理 ----
    print("\n[测试 5] 批量处理")
    try:
        processor = LazyRecordProcessor("批量处理测试")
        results = processor.process()
        assert len(results) == 1, "批量处理应返回 1 条记录"
        assert results[0]["confidence"] >= 0.0, "置信度应为非负数"
        assert results[0]["confidence"] <= 1.0, "置信度不应超过 1.0"
        print("  ✓ 批量处理通过")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 批量处理失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ 批量处理异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 测试用例 6: 置信度计算 ----
    print("\n[测试 6] 置信度计算")
    try:
        record = Record(source="测试数据")
        data = record.load()
        assert record.confidence > 0.0, "置信度应大于 0"
        assert record.confidence <= 1.0, "置信度不应超过 1.0"
        print(f"  ✓ 置信度计算通过 (confidence={record.confidence:.2f})")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 置信度计算失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ 置信度计算异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 测试用例 7: 输出格式 ----
    print("\n[测试 7] 输出格式")
    try:
        processor = LazyRecordProcessor("格式测试")
        processor.process()
        json_output = processor.format_output()
        assert json_output.startswith("["), "JSON 输出应以 [ 开头"
        assert json_output.endswith("]"), "JSON 输出应以 ] 结尾"
        print("  ✓ JSON 输出格式通过")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 输出格式失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ 输出格式异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 测试用例 8: 错误码体系 ----
    print("\n[测试 8] 错误码体系")
    try:
        # 验证所有错误码都有对应消息
        for code, message in ERROR_CODES.items():
            assert code.startswith("E"), f"错误码 {code} 格式不正确"
            assert len(code) == 4, f"错误码 {code} 长度不正确"
            assert message, f"错误码 {code} 消息为空"
        
        # 验证 E001-E010 都存在
        for i in range(1, 11):
            code = f"E{i:03d}"
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        
        print("  ✓ 错误码体系完整")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 错误码体系不完整: {e}")
        failed += 1
    
    # ---- 测试用例 9: 惰性加载特性 ----
    print("\n[测试 9] 惰性加载特性")
    try:
        record = Record(source="惰性测试")
        assert not record._loaded, "初始状态不应已加载"
        record.load()
        assert record._loaded, "调用 load() 后应已加载"
        print("  ✓ 惰性加载特性通过")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 惰性加载特性失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ 惰性加载异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 测试用例 10: 特殊字符处理 ----
    print("\n[测试 10] 特殊字符处理")
    try:
        processor = LazyRecordProcessor("特殊字符：!@#$%^&*()_+-=[]{};':\",./<>?")
        results = processor.process()
        assert len(results) == 1, "特殊字符输入应能处理"
        assert results[0]["data"]["length"] > 0, "特殊字符长度应大于 0"
        print("  ✓ 特殊字符处理通过")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 特殊字符处理失败: {e}")
        failed += 1
    except ProcessingError as e:
        print(f"  ✗ 特殊字符处理异常: {e.code} - {e.message}")
        failed += 1
    
    # ---- 汇总结果 ----
    print("\n" + "=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败, 共 {passed + failed} 项")
    print("=" * 60)
    
    return failed == 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="lazy-record: 惰性加载数据处理工具",
        epilog="示例: python scripts/main.py --process '待处理文本'"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据）"
    )
    
    parser.add_argument(
        "--process",
        type=str,
        metavar="INPUT",
        help="处理输入数据（文本/文件路径/URL）"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="lazy-record 1.0.0"
    )
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 无参数时显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理模式
    if args.process:
        try:
            processor = LazyRecordProcessor(args.process, args.format)
            processor.process()
            output = processor.format_output()
            print(output)
            return 0
        except ProcessingError as e:
            print(f"错误 {e.code}: {e.message}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 E010: 未知错误 - {e}", file=sys.stderr)
            return 1
    
    # 未知参数
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
