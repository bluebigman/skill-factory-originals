#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
技能功能实现：ai-restaurant-claude（代码审查）

本脚本依据功能规格独立实现（clean-room），不包含任何既有代码。
支持命令行参数 --selftest 进行离线自检（不读取外部文件、不访问网络）。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
SKILL_NAME = "ai-restaurant-claude"
DISPLAY_NAME = "代码审查"
VERSION = "1.0.0"

# 错误码体系（对应规格"四、异常处理"）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值（对应规格"Step 2"）
CONFIDENCE_HIGH = 90      # 高置信度阈值
CONFIDENCE_MEDIUM = 85    # 中置信度阈值


# ============================================================
# 数据结构定义
# ============================================================
class ProcessingResult:
    """处理结果数据结构"""
    def __init__(self) -> None:
        self.status: str = "success"           # 状态：success / error
        self.error_code: Optional[str] = None  # 错误码
        self.error_message: Optional[str] = None  # 错误信息
        self.data: Optional[Dict[str, Any]] = None  # 结构化结果
        self.confidence: int = 100             # 置信度（0-100）
        self.warnings: List[str] = []          # 警告列表

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result: Dict[str, Any] = {
            "status": self.status,
            "confidence": self.confidence,
        }
        if self.error_code:
            result["error_code"] = self.error_code
        if self.error_message:
            result["error_message"] = self.error_message
        if self.data:
            result["data"] = self.data
        if self.warnings:
            result["warnings"] = self.warnings
        return result


# ============================================================
# 核心处理函数
# ============================================================
def validate_input(raw_input: Any) -> Tuple[bool, Optional[str]]:
    """
    校验输入内容（对应规格"Step 1"和错误码 E001/E002/E003）
    
    参数:
        raw_input: 用户提供的原始输入
        
    返回:
        (是否有效, 错误码或None)
    """
    if raw_input is None:
        return False, "E001"
    
    if isinstance(raw_input, str):
        content = raw_input.strip()
        if not content:
            return False, "E001"
        # 检查是否为合法 JSON（如果看起来像 JSON）
        if content.startswith("{") or content.startswith("["):
            try:
                json.loads(content)
            except json.JSONDecodeError:
                return False, "E003"
    elif isinstance(raw_input, (dict, list)):
        if len(raw_input) == 0:
            return False, "E001"
    else:
        return False, "E003"
    
    return True, None


def extract_key_fields(input_data: Any) -> Dict[str, Any]:
    """
    识别输入中的关键信息并结构化（对应规格"Step 2"）
    
    参数:
        input_data: 输入数据（可能是字符串、字典或列表）
        
    返回:
        结构化字典
    """
    # 解析输入
    if isinstance(input_data, str):
        content = input_data.strip()
        if content.startswith("{") or content.startswith("["):
            parsed = json.loads(content)
        else:
            # 纯文本：按行解析
            parsed = {"text": content, "lines": content.split("\n")}
    else:
        parsed = input_data
    
    # 结构化处理
    result: Dict[str, Any] = {}
    
    if isinstance(parsed, dict):
        # 字典输入：保留关键字段
        for key, value in parsed.items():
            if value is not None and value != "":
                result[str(key)] = value
    elif isinstance(parsed, list):
        # 列表输入：批量处理
        result["items"] = []
        for item in parsed:
            if isinstance(item, dict):
                result["items"].append(item)
            else:
                result["items"].append({"value": item})
        result["count"] = len(result["items"])
    elif isinstance(parsed, dict) and "text" in parsed:
        # 文本输入：识别关键字段
        text = parsed["text"]
        result["content"] = text
        result["length"] = len(text)
        # 简单关键信息识别
        if "http" in text:
            result["has_url"] = True
        if "@" in text:
            result["has_email"] = True
    
    # 添加元数据
    result["_meta"] = {
        "skill": SKILL_NAME,
        "version": VERSION,
        "processed_at": "offline",
    }
    
    return result


def calculate_confidence(data: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    计算置信度并生成警告（对应规格"Step 2"置信度规则）
    
    参数:
        data: 结构化数据
        
    返回:
        (置信度, 警告列表)
    """
    confidence = 100
    warnings: List[str] = []
    
    # 检查数据完整性
    if not data:
        confidence = 0
        warnings.append("输入数据为空，无法确定结果")
        return confidence, warnings
    
    # 检查是否有不确定项
    uncertain_keys = []
    for key, value in data.items():
        if key.startswith("_"):
            continue
        if value is None:
            uncertain_keys.append(key)
        elif isinstance(value, str) and value.startswith("?"):
            uncertain_keys.append(key)
    
    if uncertain_keys:
        confidence -= len(uncertain_keys) * 5
        warnings.append(f"以下字段存在不确定性: {', '.join(uncertain_keys)}")
    
    # 检查数据规模（大数据量可能影响准确性）
    if isinstance(data.get("items"), list):
        item_count = len(data["items"])
        if item_count > 100:
            confidence -= 5
            warnings.append("数据量较大，建议抽样复核")
    
    # 边界检查
    confidence = max(0, min(100, confidence))
    
    return confidence, warnings


def format_output(result: ProcessingResult) -> str:
    """
    按约定格式生成输出（对应规格"Step 3"）
    
    参数:
        result: 处理结果
        
    返回:
        格式化字符串
    """
    if result.status == "error":
        return f"[错误 {result.error_code}] {result.error_message}"
    
    output_lines = []
    
    # 输出数据
    if result.data:
        output_lines.append("=== 处理结果 ===")
        for key, value in result.data.items():
            if key.startswith("_"):
                continue
            output_lines.append(f"{key}: {json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else value}")
    
    # 输出置信度标注
    confidence = result.confidence
    if confidence >= CONFIDENCE_HIGH:
        output_lines.append(f"\n置信度: {confidence}%")
    elif confidence >= CONFIDENCE_MEDIUM:
        output_lines.append(f"\n置信度: {confidence}% 建议复核")
    else:
        output_lines.append(f"\n置信度: {confidence}% [需核实]")
    
    # 输出警告
    if result.warnings:
        output_lines.append("\n警告:")
        for warning in result.warnings:
            output_lines.append(f"  - {warning}")
    
    return "\n".join(output_lines)


def process_input(raw_input: Any) -> ProcessingResult:
    """
    主处理流程（对应规格"Step 1-3"完整流程）
    
    参数:
        raw_input: 用户输入
        
    返回:
        处理结果
    """
    result = ProcessingResult()
    
    # Step 1: 收集最小信息集（校验输入）
    is_valid, error_code = validate_input(raw_input)
    if not is_valid:
        result.status = "error"
        result.error_code = error_code
        result.error_message = ERROR_MESSAGES[error_code]
        return result
    
    # Step 2: 执行核心流程
    try:
        # 解析输入
        data = extract_key_fields(raw_input)
        
        # 计算置信度
        confidence, warnings = calculate_confidence(data)
        result.confidence = confidence
        result.warnings = warnings
        
        # 检查置信度是否过低（对应 E005）
        if confidence < CONFIDENCE_MEDIUM:
            result.status = "error"
            result.error_code = "E005"
            result.error_message = ERROR_MESSAGES["E005"] + " 建议补充更多信息后重试"
            return result
        
        result.data = data
        
    except Exception as e:
        result.status = "error"
        result.error_code = "E003"
        result.error_message = f"{ERROR_MESSAGES['E003']} 解析错误: {str(e)}"
    
    return result


# ============================================================
# 自检功能（--selftest）
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑（不读取外部文件、不访问网络）
    
    使用内置硬编码样例数据，宽松阈值断言。
    
    返回:
        自检是否通过
    """
    print(f"开始自检 {DISPLAY_NAME} (v{VERSION})...")
    all_passed = True
    
    # 测试用例 1: 正常输入（字典）
    print("\n[测试 1] 正常字典输入")
    test_data_1 = {
        "name": "测试餐厅",
        "rating": 4.5,
        "reviews": 120,
        "address": "北京市朝阳区",
        "menu": ["宫保鸡丁", "麻婆豆腐"]
    }
    result_1 = process_input(test_data_1)
    assert result_1.status == "success", f"测试 1 失败: 期望 success，实际 {result_1.status}"
    assert result_1.confidence >= 80, f"测试 1 失败: 置信度应 >= 80，实际 {result_1.confidence}"
    assert result_1.data is not None, "测试 1 失败: 数据不应为空"
    assert "name" in result_1.data, "测试 1 失败: 应包含 name 字段"
    print(f"  通过 (置信度: {result_1.confidence}%)")
    
    # 测试用例 2: JSON 字符串输入
    print("\n[测试 2] JSON 字符串输入")
    test_data_2 = json.dumps({"type": "review", "score": 8.5, "comment": "味道不错"})
    result_2 = process_input(test_data_2)
    assert result_2.status == "success", f"测试 2 失败: {result_2.error_message}"
    assert result_2.confidence >= 80, f"测试 2 失败: 置信度应 >= 80"
    print(f"  通过 (置信度: {result_2.confidence}%)")
    
    # 测试用例 3: 空输入（应返回 E001）
    print("\n[测试 3] 空输入")
    result_3 = process_input("")
    assert result_3.status == "error", "测试 3 失败: 应为错误状态"
    assert result_3.error_code == "E001", f"测试 3 失败: 应返回 E001，实际 {result_3.error_code}"
    print(f"  通过 (错误码: {result_3.error_code})")
    
    # 测试用例 4: 列表批量输入
    print("\n[测试 4] 列表输入")
    test_data_4 = [
        {"id": 1, "name": "菜品A", "price": 28},
        {"id": 2, "name": "菜品B", "price": 35}
    ]
    result_4 = process_input(test_data_4)
    assert result_4.status == "success", f"测试 4 失败: {result_4.error_message}"
    assert result_4.data is not None, "测试 4 失败: 数据不应为空"
    assert result_4.data.get("count") == 2, f"测试 4 失败: 应包含 2 个条目"
    print(f"  通过 (条目数: {result_4.data.get('count')})")
    
    # 测试用例 5: 无效输入（应返回 E003）
    print("\n[测试 5] 无效输入")
    result_5 = process_input(12345)  # 数字类型
    assert result_5.status == "error", "测试 5 失败: 应为错误状态"
    assert result_5.error_code == "E003", f"测试 5 失败: 应返回 E003，实际 {result_5.error_code}"
    print(f"  通过 (错误码: {result_5.error_code})")
    
    # 测试用例 6: 低置信度场景
    print("\n[测试 6] 不确定字段")
    test_data_6 = {"name": "测试", "unknown_field": "?"}
    result_6 = process_input(test_data_6)
    # 允许成功或 E005，但必须有警告或低置信度
    if result_6.status == "success":
        assert result_6.confidence < 100, "测试 6 失败: 置信度应小于 100"
        assert len(result_6.warnings) > 0, "测试 6 失败: 应有警告"
    else:
        assert result_6.error_code == "E005", f"测试 6 失败: 应为 E005"
    print(f"  通过 (置信度: {result_6.confidence}%, 警告数: {len(result_6.warnings)})")
    
    # 测试用例 7: 格式化输出
    print("\n[测试 7] 输出格式化")
    test_result = process_input({"name": "测试", "score": 90})
    output_text = format_output(test_result)
    assert len(output_text) > 0, "测试 7 失败: 输出不应为空"
    assert "处理结果" in output_text, "测试 7 失败: 应包含结果标记"
    assert "置信度" in output_text, "测试 7 失败: 应包含置信度"
    print(f"  通过 (输出长度: {len(output_text)} 字符)")
    
    # 总结
    print(f"\n{'='*40}")
    if all_passed:
        print("✅ 所有自检测试通过")
        return True
    else:
        print("❌ 存在自检失败项")
        return False


# ============================================================
# 主程序入口
# ============================================================
def main() -> int:
    """
    主程序入口
    
    返回:
        退出码（0=成功，非0=失败）
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - {SKILL_NAME} v{VERSION}"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置数据，不访问外部资源）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串、JSON 或文件路径）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理输入
    if args.input:
        # 检查是否为文件路径
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                input_content = f.read()
        except (FileNotFoundError, IsADirectoryError):
            # 不是文件，当作普通字符串处理
            input_content = args.input
        
        # 尝试解析 JSON
        try:
            parsed_input = json.loads(input_content)
        except (json.JSONDecodeError, TypeError):
            parsed_input = input_content
        
        # 处理输入
        result = process_input(parsed_input)
        
        # 输出结果
        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(format_output(result))
        
        # 根据状态返回退出码
        return 0 if result.status == "success" else 1
    else:
        # 无输入参数
        print(ERROR_MESSAGES["E001"])
        print("\n用法示例:")
        print("  python main.py --input '{\"name\": \"测试\"}'")
        print("  python main.py --input input.json --json")
        print("  python main.py --selftest")
        return 1


if __name__ == "__main__":
    sys.exit(main())
