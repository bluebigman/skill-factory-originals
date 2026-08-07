#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫采集工具 - 独立实现脚本

本脚本根据功能规格独立编写，不参考任何既有实现。
功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理和自定义格式。
"""

import argparse
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "参数解析错误",
    "E008": "输出格式不支持",
    "E009": "批量处理中断",
    "E010": "未知错误",
}


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class ProcessedItem:
    """处理结果项"""
    source: str
    key_fields: Dict[str, Any]
    confidence: float
    warning: Optional[str] = None
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProcessingResult:
    """批量处理结果"""
    items: List[ProcessedItem]
    total_count: int
    success_count: int
    failed_count: int
    batch_id: str


# ============================================================
# 核心处理逻辑
# ============================================================
class DataProcessor:
    """数据处理器 - 核心业务逻辑"""
    
    # 常见关键词模式（用于识别关键字段）
    KEY_PATTERNS = {
        "name": ["name", "名称", "标题", "title"],
        "url": ["url", "link", "链接", "网址"],
        "price": ["price", "价格", "费用"],
        "category": ["category", "分类", "类型", "type"],
        "description": ["description", "描述", "说明", "desc"],
    }
    
    # 置信度阈值
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.85
    
    def __init__(self):
        self.error_log: List[Tuple[str, str]] = []
    
    def parse_input(self, raw_input: str) -> Dict[str, Any]:
        """
        解析输入内容，识别关键信息
        
        支持格式：
        - JSON 字符串
        - 键值对格式（key=value;key2=value2）
        - 简单文本（尝试提取关键字段）
        """
        if not raw_input or not raw_input.strip():
            self._log_error("E001", "输入为空")
            raise ValueError("E001")
        
        raw_input = raw_input.strip()
        
        # 尝试 JSON 解析
        if raw_input.startswith("{"):
            try:
                return json.loads(raw_input)
            except json.JSONDecodeError:
                self._log_error("E003", "JSON 格式错误")
                raise ValueError("E003")
        
        # 尝试键值对解析
        if "=" in raw_input and (";" in raw_input or "," in raw_input):
            result = {}
            pairs = raw_input.replace(",", ";").split(";")
            for pair in pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    result[key.strip()] = value.strip()
            if result:
                return result
        
        # 简单文本处理 - 尝试识别关键字段
        return self._extract_from_text(raw_input)
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """从纯文本中提取关键字段"""
        result = {}
        
        # 按行处理
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        for line in lines:
            # 尝试匹配 key: value 或 key：value
            for sep in [":", "："]:
                if sep in line:
                    key, value = line.split(sep, 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 匹配已知字段
                    for field_name, patterns in self.KEY_PATTERNS.items():
                        if key.lower() in patterns or key in patterns:
                            result[field_name] = value
                            break
                    break
        
        # 如果没有识别到字段，将整个文本作为描述
        if not result:
            result["description"] = text
        
        return result
    
    def process_single(self, raw_input: str) -> ProcessedItem:
        """
        处理单个输入
        
        返回结构化结果，包含置信度评估
        """
        try:
            # 解析输入
            parsed = self.parse_input(raw_input)
            
            # 提取关键字段
            key_fields = self._extract_key_fields(parsed)
            
            # 计算置信度
            confidence = self._calculate_confidence(parsed, key_fields)
            
            # 生成警告信息
            warning = self._generate_warning(confidence, key_fields)
            
            return ProcessedItem(
                source=raw_input[:100] + ("..." if len(raw_input) > 100 else ""),
                key_fields=key_fields,
                confidence=confidence,
                warning=warning
            )
            
        except ValueError as e:
            error_code = str(e)
            self._log_error(error_code, ERROR_CODES.get(error_code, "未知错误"))
            raise
    
    def _extract_key_fields(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """从解析结果中提取关键字段"""
        key_fields = {}
        
        # 遍历已知字段模式
        for field_name, patterns in self.KEY_PATTERNS.items():
            for key, value in parsed.items():
                key_lower = key.lower().strip()
                if key_lower in patterns or key in patterns:
                    key_fields[field_name] = value
                    break
        
        return key_fields
    
    def _calculate_confidence(self, parsed: Dict[str, Any], key_fields: Dict[str, Any]) -> float:
        """计算置信度"""
        if not parsed:
            return 0.0
        
        # 基础置信度
        confidence = 0.5
        
        # 根据字段匹配情况增加置信度
        field_count = len(key_fields)
        total_possible = len(self.KEY_PATTERNS)
        
        if field_count > 0:
            confidence += 0.3 * (field_count / total_possible)
        
        # 根据输入格式增加置信度
        if isinstance(parsed, dict) and len(parsed) > 0:
            confidence += 0.1
        
        # 如果识别到关键字段，增加置信度
        if "name" in key_fields:
            confidence += 0.1
        
        # 限制在 0-1 之间
        return min(max(confidence, 0.0), 1.0)
    
    def _generate_warning(self, confidence: float, key_fields: Dict[str, Any]) -> Optional[str]:
        """生成警告信息"""
        if confidence < self.MEDIUM_CONFIDENCE:
            return "[需核实] 置信度较低，建议人工复核"
        elif confidence < self.HIGH_CONFIDENCE:
            return "建议复核"
        elif not key_fields:
            return "未识别到关键字段"
        return None
    
    def process_batch(self, inputs: List[str], output_format: str = "json") -> ProcessingResult:
        """
        批量处理输入
        
        支持格式：json, text
        """
        items = []
        success_count = 0
        failed_count = 0
        
        for i, raw_input in enumerate(inputs, 1):
            try:
                item = self.process_single(raw_input)
                items.append(item)
                success_count += 1
            except ValueError as e:
                failed_count += 1
                error_code = str(e)
                self._log_error(error_code, f"第 {i} 项处理失败")
        
        result = ProcessingResult(
            items=items,
            total_count=len(inputs),
            success_count=success_count,
            failed_count=failed_count,
            batch_id=f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        # 格式化输出
        if output_format == "json":
            return self._format_json_output(result)
        elif output_format == "text":
            return self._format_text_output(result)
        else:
            self._log_error("E008", f"不支持的输出格式: {output_format}")
            raise ValueError("E008")
    
    def _format_json_output(self, result: ProcessingResult) -> ProcessingResult:
        """JSON 格式输出"""
        # 在 JSON 模式下，结果已结构化，直接返回
        return result
    
    def _format_text_output(self, result: ProcessingResult) -> ProcessingResult:
        """文本格式输出"""
        # 将 key_fields 转换为文本描述
        for item in result.items:
            if isinstance(item.key_fields, dict):
                text_parts = []
                for key, value in item.key_fields.items():
                    text_parts.append(f"{key}: {value}")
                item.key_fields = {"text": "\n".join(text_parts)}
        
        return result
    
    def _log_error(self, code: str, message: str):
        """记录错误日志"""
        self.error_log.append((code, message))
    
    def get_error_summary(self) -> str:
        """获取错误摘要"""
        if not self.error_log:
            return "无错误"
        
        summary = []
        for code, message in self.error_log:
            summary.append(f"[{code}] {message}")
        
        return "\n".join(summary)


# ============================================================
# 自测试模块
# ============================================================
def run_selftest() -> bool:
    """
    自测试函数 - 使用内置硬编码样例数据离线自检
    
    不读外部文件、不依赖当前工作目录、不访问网络
    """
    print("=" * 60)
    print("开始自测试...")
    print("=" * 60)
    
    processor = DataProcessor()
    test_passed = True
    
    # 测试用例 1: JSON 输入
    print("\n[测试 1] JSON 输入解析")
    test_json = '{"name": "Python 课程", "price": "免费", "category": "编程"}'
    try:
        item = processor.process_single(test_json)
        assert item.confidence > 0.5, "JSON 输入置信度过低"
        assert "name" in item.key_fields, "JSON 输入未识别到名称"
        print(f"  ✓ 通过 (置信度: {item.confidence:.2f})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        test_passed = False
    
    # 测试用例 2: 键值对输入
    print("\n[测试 2] 键值对输入解析")
    test_kv = "name=Web开发;price=免费;url=https://example.com"
    try:
        item = processor.process_single(test_kv)
        assert item.confidence > 0.5, "键值对输入置信度过低"
        assert "name" in item.key_fields, "键值对输入未识别到名称"
        print(f"  ✓ 通过 (置信度: {item.confidence:.2f})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        test_passed = False
    
    # 测试用例 3: 文本输入
    print("\n[测试 3] 文本输入解析")
    test_text = "名称: 数据分析课程\n价格: 免费\n描述: 学习数据处理"
    try:
        item = processor.process_single(test_text)
        assert item.confidence > 0.3, "文本输入置信度过低"
        print(f"  ✓ 通过 (置信度: {item.confidence:.2f})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        test_passed = False
    
    # 测试用例 4: 空输入错误处理
    print("\n[测试 4] 空输入错误处理")
    try:
        processor.process_single("")
        print("  ✗ 失败: 空输入未抛出异常")
        test_passed = False
    except ValueError as e:
        assert str(e) == "E001", f"错误码不正确: {e}"
        print("  ✓ 通过 (正确抛出 E001)")
    
    # 测试用例 5: 批量处理
    print("\n[测试 5] 批量处理")
    test_batch = [
        '{"name": "课程1", "price": "免费"}',
        "name=课程2;price=免费",
        "名称: 课程3\n价格: 免费",
        ""  # 空输入，应失败
    ]
    try:
        result = processor.process_batch(test_batch)
        assert result.total_count == 4, f"总数不正确: {result.total_count}"
        assert result.success_count == 3, f"成功数不正确: {result.success_count}"
        assert result.failed_count == 1, f"失败数不正确: {result.failed_count}"
        print(f"  ✓ 通过 (成功: {result.success_count}, 失败: {result.failed_count})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        test_passed = False
    
    # 测试用例 6: 置信度标注
    print("\n[测试 6] 置信度标注")
    test_low_conf = "一些不太明确的文本内容"
    try:
        item = processor.process_single(test_low_conf)
        assert item.confidence < 0.85, f"低置信度文本置信度应低于 0.85: {item.confidence}"
        assert item.warning is not None, "低置信度应有警告"
        print(f"  ✓ 通过 (置信度: {item.confidence:.2f}, 警告: {item.warning})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        test_passed = False
    
    # 测试用例 7: 错误码完整性
    print("\n[测试 7] 错误码完整性")
    required_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    all_codes_present = all(code in ERROR_CODES for code in required_codes)
    assert all_codes_present, "错误码不完整"
    print(f"  ✓ 通过 ({len(ERROR_CODES)} 个错误码)")
    
    # 测试用例 8: 批量处理结果完整性
    print("\n[测试 8] 批量处理结果完整性")
    try:
        result = processor.process_batch(['{"name": "测试"}'])
        assert result.items, "结果项为空"
        assert result.batch_id, "批次 ID 为空"
        first_item = result.items[0]
        assert hasattr(first_item, 'source'), "缺少来源字段"
        assert hasattr(first_item, 'key_fields'), "缺少关键字段"
        assert hasattr(first_item, 'confidence'), "缺少置信度"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        test_passed = False
    
    # 测试用例 9: 文本输出格式
    print("\n[测试 9] 文本输出格式")
    try:
        result = processor.process_batch(['{"name": "测试"}'], output_format="text")
        assert result.items, "结果项为空"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        test_passed = False
    
    # 测试用例 10: 不支持的输出格式
    print("\n[测试 10] 不支持的输出格式")
    try:
        processor.process_batch(['{"name": "测试"}'], output_format="xml")
        print("  ✗ 失败: 未抛出异常")
        test_passed = False
    except ValueError as e:
        assert str(e) == "E008", f"错误码不正确: {e}"
        print("  ✓ 通过 (正确抛出 E008)")
    
    # 测试总结
    print("\n" + "=" * 60)
    if test_passed:
        print("自测试全部通过 ✓")
    else:
        print("自测试存在失败项 ✗")
    print("=" * 60)
    
    return test_passed


# ============================================================
# 主程序入口
# ============================================================
def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="爬虫采集工具 - 将用户提供的数据/文件/URL 转换为结构化结果",
        epilog="示例: python main.py --input '{\"name\": \"Python课程\", \"price\": \"免费\"}'"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（JSON、键值对或文本）"
    )
    
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入，用分号分隔多个输入"
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
        help="运行自测试（使用内置样例数据，不依赖外部资源）"
    )
    
    args = parser.parse_args()
    
    # 自测试模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 参数验证
    if not args.input and not args.batch:
        print(f"错误 [E001]: {ERROR_CODES['E001']}")
        print("请使用 --input 或 --batch 提供输入内容")
        sys.exit(1)
    
    processor = DataProcessor()
    
    try:
        if args.batch:
            # 批量处理模式
            inputs = [item.strip() for item in args.batch.split(";") if item.strip()]
            if not inputs:
                print(f"错误 [E001]: {ERROR_CODES['E001']}")
                sys.exit(1)
            
            result = processor.process_batch(inputs, args.format)
            
            # 输出结果
            print(f"批次 ID: {result.batch_id}")
            print(f"总数: {result.total_count}, 成功: {result.success_count}, 失败: {result.failed_count}")
            print("\n处理结果:")
            
            for i, item in enumerate(result.items, 1):
                print(f"\n--- 第 {i} 项 ---")
                print(f"来源: {item.source}")
                print(f"关键字段: {json.dumps(item.key_fields, ensure_ascii=False, indent=2)}")
                print(f"置信度: {item.confidence:.2%}")
                if item.warning:
                    print(f"提示: {item.warning}")
            
            if processor.error_log:
                print("\n错误日志:")
                print(processor.get_error_summary())
        
        else:
            # 单条处理模式
            item = processor.process_single(args.input)
            
            print("处理结果:")
            print(f"来源: {item.source}")
            print(f"关键字段: {json.dumps(item.key_fields, ensure_ascii=False, indent=2)}")
            print(f"置信度: {item.confidence:.2%}")
            if item.warning:
                print(f"提示: {item.warning}")
    
    except ValueError as e:
        error_code = str(e)
        error_msg = ERROR_CODES.get(error_code, f"未知错误 [{error_code}]")
        print(f"错误 [{error_code}]: {error_msg}")
        sys.exit(1)
    except Exception as e:
        print(f"错误 [E010]: {ERROR_CODES['E010']} - {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
