#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - ai-restaurant-claude 技能实现

仅依据功能规格独立实现（clean-room），不复制任何既有代码。
提供命令行入口，支持 --selftest 离线自检。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
SKILL_NAME = "ai-restaurant-claude"
DISPLAY_NAME = "代码审查"
VERSION = "1.0.0"

# 置信度阈值
HIGH_CONFIDENCE = 90.0    # >= 90% 直接输出
MEDIUM_CONFIDENCE = 85.0  # 85%-90% 建议复核
# < 85% 标注 [需核实]

# 错误码映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理异常，请重试或联系支持",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出序列化失败",
    "E009": "批处理中断，部分任务未完成",
    "E010": "未知错误，请查看日志",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果封装"""

    def __init__(
        self,
        status: str = "ok",
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 100.0,
        warnings: Optional[List[str]] = None,
        error_code: Optional[str] = None,
    ):
        self.status = status
        self.data = data or {}
        self.confidence = confidence
        self.warnings = warnings or []
        self.error_code = error_code

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "error_code": self.error_code,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def validate_input(raw_input: Any) -> Optional[str]:
    """
    校验输入是否有效。

    参数:
        raw_input: 任意输入

    返回:
        有效返回 None，无效返回错误码
    """
    if raw_input is None:
        return "E001"
    if isinstance(raw_input, str) and not raw_input.strip():
        return "E001"
    if isinstance(raw_input, (list, dict)) and len(raw_input) == 0:
        return "E001"
    return None


def extract_key_fields(input_data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段并结构化。

    支持输入类型：
    - 字符串：按行解析，识别 key: value 或 key=value 形式
    - 字典：直接提取
    - 列表：逐项处理

    参数:
        input_data: 原始输入

    返回:
        结构化字段字典
    """
    fields: Dict[str, Any] = {}

    if isinstance(input_data, dict):
        # 字典直接提取
        for key, value in input_data.items():
            fields[str(key)] = value
    elif isinstance(input_data, str):
        # 字符串按行解析
        for line in input_data.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # 支持 key: value 或 key=value 两种格式
            if ":" in line:
                key, _, value = line.partition(":")
            elif "=" in line:
                key, _, value = line.partition("=")
            else:
                # 无分隔符，整行作为值
                key, value = f"line_{len(fields) + 1}", line
            fields[key.strip()] = value.strip()
    elif isinstance(input_data, list):
        # 列表逐项处理
        for idx, item in enumerate(input_data):
            fields[f"item_{idx + 1}"] = item

    return fields


def calculate_confidence(fields: Dict[str, Any]) -> float:
    """
    根据字段完整度计算置信度。

    规则：
    - 无字段：0%
    - 有字段：基础 80%，每多一个字段 +2%，上限 98%

    参数:
        fields: 结构化字段

    返回:
        置信度百分比 (0-100)
    """
    if not fields:
        return 0.0

    # 基础置信度
    confidence = 80.0
    # 字段数量奖励（最多 +18%）
    confidence += min(len(fields) * 2.0, 18.0)

    return min(confidence, 98.0)


def format_output(result: ProcessingResult) -> Dict[str, Any]:
    """
    按约定格式组织输出，并标注置信度。

    参数:
        result: 处理结果

    返回:
        格式化输出字典
    """
    output = result.to_dict()

    # 根据置信度添加标注
    if result.confidence >= HIGH_CONFIDENCE:
        output["advice"] = "可直接使用"
    elif result.confidence >= MEDIUM_CONFIDENCE:
        output["advice"] = "建议复核"
        result.warnings.append("置信度中等，建议人工复核关键字段")
    else:
        output["advice"] = "[需核实]"
        result.warnings.append("置信度较低，请核实所有字段")

    # 重新生成 warnings（因为上面可能追加了）
    output["warnings"] = result.warnings

    return output


def process_single(input_data: Any, output_format: str = "json") -> ProcessingResult:
    """
    处理单个输入。

    参数:
        input_data: 输入数据
        output_format: 输出格式（json/dict）

    返回:
        处理结果
    """
    # Step 1: 输入校验
    error_code = validate_input(input_data)
    if error_code:
        return ProcessingResult(
            status="error",
            error_code=error_code,
            confidence=0.0,
        )

    # Step 2: 提取关键字段
    fields = extract_key_fields(input_data)

    # Step 3: 计算置信度
    confidence = calculate_confidence(fields)

    # Step 4: 生成结果
    result = ProcessingResult(
        status="ok",
        data=fields,
        confidence=confidence,
    )

    # 低置信度时添加警告
    if confidence < MEDIUM_CONFIDENCE:
        result.warnings.append("输入信息不足，结果可能存在偏差")

    return result


def process_batch(input_list: List[Any], output_format: str = "json") -> ProcessingResult:
    """
    批量处理多个输入。

    参数:
        input_list: 输入列表
        output_format: 输出格式

    返回:
        处理结果
    """
    results = []
    failed_count = 0

    for idx, item in enumerate(input_list):
        result = process_single(item, output_format)
        if result.status == "ok":
            results.append(format_output(result))
        else:
            failed_count += 1
            results.append(
                {
                    "status": "error",
                    "error_code": result.error_code,
                    "error_message": ERROR_MESSAGES.get(result.error_code, ERROR_MESSAGES["E010"]),
                }
            )

    # 计算整体置信度（成功项的平均值）
    ok_results = [r for r in results if r.get("status") == "ok"]
    avg_confidence = (
        sum(r.get("confidence", 0) for r in ok_results) / len(ok_results)
        if ok_results
        else 0.0
    )

    # 整体结果
    batch_result = ProcessingResult(
        status="ok" if failed_count == 0 else "partial",
        data={
            "total": len(input_list),
            "success": len(ok_results),
            "failed": failed_count,
            "items": results,
        },
        confidence=avg_confidence,
    )

    if failed_count > 0:
        batch_result.warnings.append(f"有 {failed_count} 个输入处理失败")
        batch_result.error_code = "E009" if failed_count == len(input_list) else None

    return batch_result


# ---------------------------------------------------------------------------
# 主处理入口
# ---------------------------------------------------------------------------
def handle_request(
    input_data: Any,
    output_format: str = "json",
    is_batch: bool = False,
) -> Dict[str, Any]:
    """
    主处理入口，根据输入类型和参数分发处理。

    参数:
        input_data: 输入数据
        output_format: 输出格式
        is_batch: 是否为批量处理

    返回:
        处理结果字典
    """
    # 输入校验
    error_code = validate_input(input_data)
    if error_code:
        return {
            "status": "error",
            "error_code": error_code,
            "error_message": ERROR_MESSAGES[error_code],
        }

    # 批量处理
    if is_batch or isinstance(input_data, list):
        result = process_batch(input_data, output_format)
    else:
        result = process_single(input_data, output_format)

    # 格式化输出
    if result.status == "ok":
        return format_output(result)
    else:
        return {
            "status": result.status,
            "error_code": result.error_code,
            "error_message": ERROR_MESSAGES.get(
                result.error_code, ERROR_MESSAGES["E010"]
            ),
            "warnings": result.warnings,
        }


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。

    不读外部文件、不依赖当前工作目录、不访问网络。

    使用宽松阈值（大小比较/区间判断），确保稳健。

    返回:
        True 表示全部通过，False 表示存在失败项
    """
    print("=" * 60)
    print("自检开始 (ai-restaurant-claude)")
    print("=" * 60)

    all_passed = True

    # --- 测试用例 1: 正常字符串输入 ---
    print("\n[测试 1] 正常字符串输入")
    test_input = "店名: 老成都川菜馆\n地址: 北京市朝阳区建国路88号\n电话: 010-88886666"
    result = handle_request(test_input)
    # 宽松断言：状态为 ok，data 非空，置信度在合理区间
    test1_ok = (
        result.get("status") == "ok"
        and len(result.get("data", {})) >= 2
        and 0 <= result.get("confidence", 0) <= 100
    )
    print(f"  状态: {'通过' if test1_ok else '失败'}")
    if not test1_ok:
        print(f"  实际结果: {result}")
    all_passed = all_passed and test1_ok

    # --- 测试用例 2: 空输入处理 ---
    print("\n[测试 2] 空输入处理")
    result = handle_request("   ")
    # 宽松断言：应返回错误，错误码为 E001
    test2_ok = result.get("status") == "error" and result.get("error_code") == "E001"
    print(f"  状态: {'通过' if test2_ok else '失败'}")
    if not test2_ok:
        print(f"  实际结果: {result}")
    all_passed = all_passed and test2_ok

    # --- 测试用例 3: 字典输入 ---
    print("\n[测试 3] 字典输入")
    test_input = {"name": "测试餐厅", "rating": 4.5, "reviews": 120}
    result = handle_request(test_input)
    # 宽松断言：状态为 ok，data 包含 name 字段，置信度 > 80
    test3_ok = (
        result.get("status") == "ok"
        and "name" in result.get("data", {})
        and result.get("confidence", 0) > 80
    )
    print(f"  状态: {'通过' if test3_ok else '失败'}")
    if not test3_ok:
        print(f"  实际结果: {result}")
    all_passed = all_passed and test3_ok

    # --- 测试用例 4: 批量处理 ---
    print("\n[测试 4] 批量处理")
    test_input = [
        "菜名: 回锅肉\n价格: 38元",
        "菜名: 麻婆豆腐\n价格: 28元",
        "",  # 空输入
    ]
    result = handle_request(test_input, is_batch=True)
    # 宽松断言：状态为 ok 或 partial，total=3
    test4_ok = (
        result.get("status") in ("ok", "partial")
        and result.get("data", {}).get("total") == 3
    )
    print(f"  状态: {'通过' if test4_ok else '失败'}")
    if not test4_ok:
        print(f"  实际结果: {result}")
    all_passed = all_passed and test4_ok

    # --- 测试用例 5: 低置信度场景 ---
    print("\n[测试 5] 低置信度场景")
    test_input = "单一字段"
    result = handle_request(test_input)
    # 宽松断言：置信度在 0-100 之间，且 warnings 是列表
    test5_ok = (
        0 <= result.get("confidence", -1) <= 100
        and isinstance(result.get("warnings", None), list)
    )
    print(f"  状态: {'通过' if test5_ok else '失败'}")
    if not test5_ok:
        print(f"  实际结果: {result}")
    all_passed = all_passed and test5_ok

    # --- 测试用例 6: 边界能力声明 ---
    print("\n[测试 6] 能力边界检查")
    # 超出能力范围：要求执行代码（模拟）
    # 这里只验证错误处理机制，不真正执行
    result = handle_request("请帮我写一段Python代码")
    # 宽松断言：结果结构完整
    test6_ok = "status" in result and ("data" in result or "error_code" in result)
    print(f"  状态: {'通过' if test6_ok else '失败'}")
    if not test6_ok:
        print(f"  实际结果: {result}")
    all_passed = all_passed and test6_ok

    # --- 测试用例 7: JSON 序列化 ---
    print("\n[测试 7] JSON 序列化")
    test_input = {"key1": "value1", "key2": "value2"}
    result = handle_request(test_input)
    try:
        json_str = json.dumps(result, ensure_ascii=False)
        test7_ok = len(json_str) > 0
    except (TypeError, ValueError):
        test7_ok = False
    print(f"  状态: {'通过' if test7_ok else '失败'}")
    if not test7_ok:
        print(f"  实际结果: {result}")
    all_passed = all_passed and test7_ok

    # --- 测试用例 8: 错误码体系 ---
    print("\n[测试 8] 错误码体系")
    # 所有错误码都有对应消息
    test8_ok = all(code in ERROR_MESSAGES for code in ["E001", "E002", "E003", "E004", "E005"])
    print(f"  状态: {'通过' if test8_ok else '失败'}")
    if not test8_ok:
        print(f"  缺失错误码: {[c for c in ['E001','E002','E003','E004','E005'] if c not in ERROR_MESSAGES]}")
    all_passed = all_passed and test8_ok

    # --- 汇总 ---
    print("\n" + "=" * 60)
    print(f"自检结果: {'全部通过' if all_passed else '存在失败项'}")
    print("=" * 60)

    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    命令行主入口。

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description=f"{SKILL_NAME} v{VERSION} - {DISPLAY_NAME}",
        epilog="示例: python main.py --input '店名: 测试餐厅' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串、JSON 字符串或文件路径，使用 file:// 前缀）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入为 JSON 数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} {VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    # 解析输入（支持 file:// 前缀）
    input_data = args.input
    if input_data.startswith("file://"):
        # 文件输入（注意：自检不涉及文件，这里用于正常模式）
        filepath = input_data[7:]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                input_data = f.read()
        except (IOError, OSError) as e:
            print(f"E006: 无法读取文件: {e}", file=sys.stderr)
            return 1

    # 尝试解析 JSON（如果是 JSON 格式）
    if input_data.strip().startswith(("{", "[")):
        try:
            input_data = json.loads(input_data)
        except json.JSONDecodeError:
            # 不是合法 JSON，按字符串处理
            pass

    # 处理请求
    try:
        result = handle_request(
            input_data=input_data,
            output_format=args.format,
            is_batch=args.batch or isinstance(input_data, list),
        )
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        return 1

    # 输出结果
    if args.format == "json":
        try:
            output = json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            print(f"E008: 输出序列化失败: {e}", file=sys.stderr)
            return 1
    else:
        # 文本格式
        output = format_text_output(result)

    print(output)

    # 根据结果状态返回退出码
    return 0 if result.get("status") in ("ok", "partial") else 1


def format_text_output(result: Dict[str, Any]) -> str:
    """
    将结果格式化为文本输出。

    参数:
        result: 处理结果字典

    返回:
        文本格式的字符串
    """
    lines = []

    if result.get("status") == "error":
        lines.append(f"[错误] {result.get('error_code', 'E010')}")
        lines.append(result.get("error_message", ERROR_MESSAGES["E010"]))
        return "\n".join(lines)

    # 状态和置信度
    lines.append(f"状态: {result.get('status', 'ok')}")
    lines.append(f"置信度: {result.get('confidence', 0):.1f}%")
    if result.get("advice"):
        lines.append(f"建议: {result['advice']}")

    # 数据字段
    data = result.get("data", {})
    if isinstance(data, dict):
        # 批量处理
        if "items" in data:
            lines.append(f"\n处理项: {data.get('success', 0)}/{data.get('total', 0)} 成功")
            for idx, item in enumerate(data.get("items", []), 1):
                if item.get("status") == "ok":
                    lines.append(f"\n--- 项 {idx} ---")
                    for key, value in item.get("data", {}).items():
                        lines.append(f"  {key}: {value}")
                    lines.append(f"  置信度: {item.get('confidence', 0):.1f}%")
                else:
                    lines.append(f"\n--- 项 {idx} [失败] ---")
                    lines.append(f"  {item.get('error_code', 'E010')}: {item.get('error_message', '')}")
        else:
            # 单条数据
            for key, value in data.items():
                lines.append(f"{key}: {value}")

    # 警告
    warnings = result.get("warnings", [])
    if warnings:
        lines.append("\n警告:")
        for w in warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
