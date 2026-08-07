#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoZest 独立实现脚本
================================
基于功能规格的 clean-room 重写实现。

功能概述：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

错误码：
- E001: 输入为空
- E002: 关键信息缺失
- E003: 输入格式错误
- E004: 超出能力边界
- E005: 置信度过低
- E006: 参数解析错误
- E007: 内部逻辑错误
- E008: 批量处理中断
- E009: 输出生成失败
- E010: 未知异常

仅使用 Python 标准库实现。
"""

import argparse
import json
import re
import sys
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 版本信息
VERSION = "1.0.0"
TOOL_NAME = "autozest"

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 0.90
MEDIUM_CONFIDENCE_THRESHOLD = 0.85

# 默认支持的关键字段（可根据输入动态扩展）
DEFAULT_KEY_FIELDS = [
    "name", "title", "type", "url", "date", "amount",
    "description", "status", "category", "id"
]

# 输入类型标识
INPUT_TYPE_TEXT = "text"
INPUT_TYPE_FILE = "file"
INPUT_TYPE_URL = "url"


# ============================================================
# 错误处理
# ============================================================

class AutoZestError(Exception):
    """AutoZest 基础异常类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def raise_error(code: str, message: str) -> None:
    """抛出标准错误"""
    raise AutoZestError(code, message)


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: Any) -> None:
    """
    校验输入是否有效。
    
    Args:
        raw_input: 用户提供的原始输入
        
    Raises:
        AutoZestError: E001 输入为空
    """
    if raw_input is None:
        raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    
    if isinstance(raw_input, str):
        if not raw_input.strip():
            raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    elif isinstance(raw_input, (list, tuple, dict)):
        if len(raw_input) == 0:
            raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    else:
        # 其他类型（数字、布尔等）视为有效
        pass


def detect_input_type(raw_input: Any) -> str:
    """
    检测输入类型。
    
    Args:
        raw_input: 用户提供的原始输入
        
    Returns:
        str: 输入类型标识（text/file/url）
    """
    if isinstance(raw_input, str):
        text = raw_input.strip()
        # 检测 URL
        url_pattern = re.compile(
            r'^(https?://|ftp://|file://)',
            re.IGNORECASE
        )
        if url_pattern.match(text):
            return INPUT_TYPE_URL
        
        # 检测文件路径
        if len(text) < 500 and os.path.exists(text):
            return INPUT_TYPE_FILE
        
        return INPUT_TYPE_TEXT
    
    return INPUT_TYPE_TEXT


def extract_key_fields(data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入数据中提取关键字段。
    
    Args:
        data: 输入数据（字符串、字典、列表等）
        
    Returns:
        Tuple[Dict[str, Any], float]: (提取的字段字典, 置信度)
        
    Raises:
        AutoZestError: E003 输入格式错误
    """
    if isinstance(data, dict):
        # 字典输入：直接提取已知字段
        extracted = {}
        for key, value in data.items():
            if isinstance(key, str) and key.strip():
                extracted[key.strip()] = value
        
        if not extracted:
            raise_error("E003", "输入格式不符合要求，示例：{'name': '示例', 'type': '数据'}")
        
        # 置信度：字段越多越确定
        confidence = min(0.95, 0.70 + 0.05 * len(extracted))
        return extracted, confidence
    
    elif isinstance(data, str):
        # 字符串输入：尝试解析
        text = data.strip()
        if not text:
            raise_error("E003", "输入格式不符合要求，示例：'名称: 示例, 类型: 数据'")
        
        extracted = {}
        
        # 尝试 JSON 解析
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return extract_key_fields(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # 尝试键值对解析（支持多种分隔符）
        # 格式：key: value, key2: value2
        pair_patterns = [
            re.compile(r'([^:,]+)\s*[:：]\s*([^,，]+)'),
            re.compile(r'([^=]+)\s*=\s*([^;；]+)'),
        ]
        
        for pattern in pair_patterns:
            matches = pattern.findall(text)
            if matches:
                for key, value in matches:
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        extracted[key] = value
                break
        
        # 如果没有找到键值对，将整个文本作为内容
        if not extracted:
            extracted = {"content": text}
        
        confidence = 0.80 if len(extracted) > 1 else 0.70
        return extracted, confidence
    
    elif isinstance(data, (list, tuple)):
        # 列表输入：批量处理，每个元素作为独立项
        if len(data) == 0:
            raise_error("E003", "输入格式不符合要求，示例：['项目1', '项目2']")
        
        # 提取每个元素的字段
        items = []
        for item in data:
            try:
                item_fields, _ = extract_key_fields(item)
                items.append(item_fields)
            except AutoZestError:
                # 单个元素解析失败不影响整体
                items.append({"content": str(item)})
        
        extracted = {"items": items, "count": len(items)}
        confidence = 0.85
        return extracted, confidence
    
    else:
        # 其他类型
        extracted = {"value": str(data)}
        confidence = 0.60
        return extracted, confidence


def check_key_info_completeness(fields: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    检查关键信息是否完整。
    
    Args:
        fields: 已提取的字段字典
        
    Returns:
        Tuple[bool, List[str]]: (是否完整, 缺失字段列表)
    """
    # 核心必需字段（按需调整）
    required_fields = ["name", "type"]
    
    missing = []
    for field in required_fields:
        if field not in fields or not str(fields[field]).strip():
            missing.append(field)
    
    return (len(missing) == 0, missing)


def generate_output(
    extracted: Dict[str, Any],
    confidence: float,
    custom_format: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成结构化输出。
    
    Args:
        extracted: 提取的字段字典
        confidence: 置信度
        custom_format: 自定义输出格式
        
    Returns:
        Dict[str, Any]: 结构化输出结果
        
    Raises:
        AutoZestError: E009 输出生成失败
    """
    try:
        result = {
            "tool": TOOL_NAME,
            "version": VERSION,
            "status": "success",
            "confidence": round(confidence, 2),
            "data": extracted,
        }
        
        # 置信度标注
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            result["confidence_label"] = "高置信度"
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            result["confidence_label"] = "建议复核"
        else:
            result["confidence_label"] = "[需核实]"
            result["uncertainty_note"] = "结果无法确定，建议人工复核关键信息"
        
        # 自定义格式处理
        if custom_format and isinstance(custom_format, dict):
            # 按自定义字段顺序重新组织
            ordered_data = {}
            for field in custom_format.get("fields", []):
                if field in extracted:
                    ordered_data[field] = extracted[field]
            
            if ordered_data:
                result["data"] = ordered_data
            
            # 自定义格式类型
            if custom_format.get("format") == "compact":
                result["compact"] = True
        
        # 关键信息完整性检查
        complete, missing = check_key_info_completeness(extracted)
        result["info_complete"] = complete
        if not complete:
            result["missing_fields"] = missing
        
        return result
    
    except Exception as e:
        raise_error("E009", f"输出生成失败: {str(e)}")


def process_single_item(
    raw_input: Any,
    custom_format: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    处理单个输入项。
    
    Args:
        raw_input: 原始输入
        custom_format: 自定义格式
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    # 1. 输入校验
    validate_input(raw_input)
    
    # 2. 检测输入类型
    input_type = detect_input_type(raw_input)
    
    # 3. 提取字段
    extracted, confidence = extract_key_fields(raw_input)
    
    # 4. 检查关键信息
    complete, missing = check_key_info_completeness(extracted)
    if not complete and confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        raise_error("E002", f"还缺少以下信息，请补充：{', '.join(missing)}")
    
    # 5. 生成输出
    result = generate_output(extracted, confidence, custom_format)
    result["input_type"] = input_type
    
    return result


def process_batch(
    items: List[Any],
    custom_format: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    批量处理多个输入项。
    
    Args:
        items: 输入项列表
        custom_format: 自定义格式
        
    Returns:
        Dict[str, Any]: 批量处理结果
        
    Raises:
        AutoZestError: E008 批量处理中断
    """
    if not items:
        raise_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    
    results = []
    error_count = 0
    
    for i, item in enumerate(items):
        try:
            result = process_single_item(item, custom_format)
            result["index"] = i
            results.append(result)
        except AutoZestError as e:
            error_count += 1
            results.append({
                "index": i,
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
            })
    
    batch_result = {
        "tool": TOOL_NAME,
        "version": VERSION,
        "status": "success" if error_count == 0 else "partial",
        "total": len(items),
        "success_count": len(items) - error_count,
        "error_count": error_count,
        "results": results,
    }
    
    if error_count > 0:
        batch_result["note"] = "部分项目处理失败，请查看各项目错误信息"
    
    return batch_result


# ============================================================
# 能力边界检查
# ============================================================

def check_capability_boundary(request: str) -> Optional[str]:
    """
    检查请求是否超出能力边界。
    
    Args:
        request: 用户请求描述
        
    Returns:
        Optional[str]: 如果超出边界，返回原因；否则返回 None
    """
    if not request:
        return None
    
    # 超出边界的场景
    out_of_scope = [
        "网络", "联网", "下载", "爬取", "抓取",
        "法律", "财务", "税务", "投资", "医疗",
        "合同", "报税", "诊疗",
    ]
    
    for keyword in out_of_scope:
        if keyword in request:
            return f"这超出了本工具的能力范围（涉及{keyword}相关操作），建议咨询持证专业人士"
    
    return None


# ============================================================
# 命令行接口
# ============================================================

def run_selftest() -> bool:
    """
    内置自检功能：使用硬编码样例数据验证核心逻辑。
    
    Returns:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("AutoZest 自检开始")
    print("=" * 60)
    
    # 测试用例 1: 字符串键值对输入
    print("\n[测试 1] 字符串键值对输入")
    try:
        result = process_single_item("name: 测试项目, type: 数据文件, size: 1024KB")
        assert result["status"] == "success", "状态应为成功"
        assert "name" in result["data"], "应提取 name 字段"
        assert result["data"]["name"] == "测试项目", "name 值应正确"
        assert result["confidence"] >= 0.70, "置信度应不低于 0.70"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    # 测试用例 2: 字典输入
    print("\n[测试 2] 字典输入")
    try:
        dict_input = {"name": "报告", "type": "文档", "pages": 10, "author": "测试"}
        result = process_single_item(dict_input)
        assert result["status"] == "success", "状态应为成功"
        assert result["data"]["name"] == "报告", "name 值应正确"
        assert result["confidence"] >= 0.80, "字典输入置信度应较高"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    # 测试用例 3: 列表批量输入
    print("\n[测试 3] 列表批量输入")
    try:
        list_input = ["项目A", "项目B", "项目C"]
        result = process_batch(list_input)
        assert result["status"] == "success", "批量处理应全部成功"
        assert result["total"] == 3, "总数应为 3"
        assert result["success_count"] == 3, "成功数应为 3"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    # 测试用例 4: 空输入错误
    print("\n[测试 4] 空输入错误处理")
    try:
        process_single_item("")
        print("  ✗ 失败: 未触发 E001 错误")
        return False
    except AutoZestError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    # 测试用例 5: 置信度标注
    print("\n[测试 5] 置信度标注")
    try:
        result = process_single_item("简单内容")
        assert "confidence_label" in result, "应包含置信度标注"
        assert result["confidence"] > 0, "置信度应大于 0"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    # 测试用例 6: 能力边界检查
    print("\n[测试 6] 能力边界检查")
    try:
        boundary_reason = check_capability_boundary("帮我做法律咨询")
        assert boundary_reason is not None, "法律咨询应超出能力边界"
        
        boundary_reason = check_capability_boundary("帮我处理数据")
        assert boundary_reason is None, "数据处理应在能力范围内"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    # 测试用例 7: 自定义格式
    print("\n[测试 7] 自定义格式")
    try:
        custom_format = {"fields": ["name", "type"], "format": "compact"}
        result = process_single_item(
            "name: 自定义测试, type: 演示, extra: 不需要",
            custom_format
        )
        assert "name" in result["data"], "应包含 name 字段"
        assert "extra" not in result["data"], "自定义格式应过滤 extra 字段"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    # 测试用例 8: URL 输入识别
    print("\n[测试 8] URL 输入识别")
    try:
        result = process_single_item("https://example.com/data")
        assert result["input_type"] == "url", f"输入类型应为 url，实际为 {result['input_type']}"
        assert "content" in result["data"], "URL 应被识别为内容"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    # 测试用例 9: JSON 输入
    print("\n[测试 9] JSON 输入")
    try:
        json_input = '{"name": "JSON测试", "type": "结构化", "count": 5}'
        result = process_single_item(json_input)
        assert result["data"]["name"] == "JSON测试", "JSON 解析应正确"
        assert result["data"]["count"] == 5, "数字字段应保留"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    # 测试用例 10: 混合批量（含错误项）
    print("\n[测试 10] 混合批量处理")
    try:
        mixed_list = ["正常项目", "", "另一个项目"]
        result = process_batch(mixed_list)
        assert result["total"] == 3, "总数应为 3"
        assert result["error_count"] >= 1, "应至少有 1 个错误项"
        assert result["status"] == "partial", "状态应为 partial"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except AutoZestError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return False
    
    print("\n" + "=" * 60)
    print("所有自检测试通过 ✓")
    print("=" * 60)
    return True


def main() -> int:
    """
    主入口函数。
    
    Returns:
        int: 退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description=f"{TOOL_NAME} v{VERSION} - 数据处理工具",
        epilog="示例: python main.py 'name: 示例, type: 数据'"
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的数据（字符串、JSON、文件路径或 URL）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，不依赖外部文件）"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为 JSON 数组）"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        help="自定义输出格式（JSON 字符串）"
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    
    args = parser.parse_args()
    
    # 版本信息
    if args.version:
        print(f"{TOOL_NAME} v{VERSION}")
        return 0
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 无输入参数
    if not args.input:
        parser.print_help()
        print("\n错误: 请提供输入内容")
        return 1
    
    try:
        # 解析自定义格式
        custom_format = None
        if args.format:
            try:
                custom_format = json.loads(args.format)
            except json.JSONDecodeError:
                raise_error("E006", f"自定义格式参数无效: {args.format}")
        
        # 批量模式
        if args.batch:
            try:
                items = json.loads(args.input)
                if not isinstance(items, list):
                    raise_error("E003", "批量模式要求输入为 JSON 数组")
                result = process_batch(items, custom_format)
            except json.JSONDecodeError:
                raise_error("E003", "批量模式要求输入为 JSON 数组，示例: [\"项目1\", \"项目2\"]")
        else:
            # 能力边界检查
            boundary_reason = check_capability_boundary(args.input)
            if boundary_reason:
                raise_error("E004", boundary_reason)
            
            result = process_single_item(args.input, custom_format)
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
        
    except AutoZestError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 未知异常: {str(e)}", file=sys.stderr)
        return 1


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
