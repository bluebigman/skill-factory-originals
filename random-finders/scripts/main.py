#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
random-finders 技能实现脚本
===========================

本脚本依据功能规格独立实现（clean-room），提供：
1. 随机记录获取 / 随机顺序排列的核心逻辑
2. 结构化输入解析与置信度评估
3. 标准流程处理（收集信息 -> 执行 -> 输出）
4. 错误码体系（E001-E010）
5. 内置离线自检（--selftest）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import random
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：['item1', 'item2', 'item3']",
    "E004": "这超出了本工具的能力范围，建议使用专门的数据分析工具",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
    "E006": "内部错误：随机数生成失败",
    "E007": "内部错误：数据解析失败",
    "E008": "内部错误：输出格式化失败",
    "E009": "内部错误：自检失败",
    "E010": "内部错误：未知异常",
}


def get_error_message(code: str) -> str:
    """根据错误码获取标准话术"""
    return f"[{code}] {ERROR_MESSAGES.get(code, '未知错误')}"


# ============================================================
# 核心逻辑：随机记录获取与随机排列
# ============================================================
class RandomFinder:
    """
    随机记录查找器

    提供两种核心能力：
    1. random_record(items): 从列表中随机获取一条记录
    2. random_order(items):  将列表随机排列
    """

    def __init__(self, seed: Optional[int] = None):
        """
        初始化

        Args:
            seed: 随机种子（可选），便于测试复现
        """
        self._rng = random.Random(seed)

    def random_record(self, items: List[Any]) -> Any:
        """
        从列表中随机获取一条记录

        Args:
            items: 输入列表

        Returns:
            随机选中的一条记录

        Raises:
            E001: 输入为空
            E003: 输入不是列表
            E006: 随机数生成失败
        """
        if not items:
            raise ValueError(get_error_message("E001"))
        if not isinstance(items, list):
            raise TypeError(get_error_message("E003"))

        try:
            return self._rng.choice(items)
        except Exception:
            raise RuntimeError(get_error_message("E006"))

    def random_order(self, items: List[Any]) -> List[Any]:
        """
        将列表随机排列

        Args:
            items: 输入列表

        Returns:
            随机排列后的新列表

        Raises:
            E001: 输入为空
            E003: 输入不是列表
            E006: 随机数生成失败
        """
        if not items:
            raise ValueError(get_error_message("E001"))
        if not isinstance(items, list):
            raise TypeError(get_error_message("E003"))

        try:
            result = items.copy()
            self._rng.shuffle(result)
            return result
        except Exception:
            raise RuntimeError(get_error_message("E006"))


# ============================================================
# 输入解析与结构化
# ============================================================
def parse_input(raw_input: Any) -> Tuple[List[Any], float]:
    """
    解析输入内容，识别关键信息

    支持格式：
    - 列表：直接使用
    - 字符串：尝试按逗号/空格/换行分割
    - 其他：尝试转换为列表

    Args:
        raw_input: 原始输入

    Returns:
        (结构化列表, 置信度 0.0-1.0)

    Raises:
        E001: 输入为空
        E003: 输入格式错误
        E007: 解析失败
    """
    if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
        raise ValueError(get_error_message("E001"))

    try:
        # 已经是列表
        if isinstance(raw_input, list):
            if not raw_input:
                raise ValueError(get_error_message("E001"))
            return raw_input, 0.95

        # 字符串：按分隔符拆分
        if isinstance(raw_input, str):
            # 尝试 JSON 风格列表
            stripped = raw_input.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                inner = stripped[1:-1]
                items = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
            else:
                # 按逗号、分号、换行、制表符拆分
                import re
                parts = re.split(r"[,;\n\t]+", stripped)
                items = [p.strip() for p in parts if p.strip()]

            if not items:
                raise ValueError(get_error_message("E003"))
            return items, 0.90

        # 其他可迭代对象
        try:
            items = list(raw_input)
            if not items:
                raise ValueError(get_error_message("E001"))
            return items, 0.85
        except TypeError:
            raise TypeError(get_error_message("E003"))

    except (ValueError, TypeError) as e:
        if isinstance(e, ValueError):
            raise
        raise TypeError(get_error_message("E003"))
    except Exception:
        raise RuntimeError(get_error_message("E007"))


# ============================================================
# 置信度评估
# ============================================================
def evaluate_confidence(items: List[Any]) -> Tuple[float, Optional[str]]:
    """
    评估结果置信度

    Args:
        items: 结构化后的数据列表

    Returns:
        (置信度 0.0-1.0, 提示信息或 None)

    规则：
        - 列表非空且元素类型一致：>= 90%
        - 列表非空但元素类型不一致：85%-90%
        - 列表存在空值或异常值：< 85%
    """
    if not items:
        return 0.0, get_error_message("E005")

    # 检查元素类型一致性
    types = set(type(item) for item in items)

    if len(types) == 1:
        # 类型一致
        if all(str(item).strip() for item in items):
            return 0.95, None
        else:
            return 0.88, "存在空值，建议复核"
    elif len(types) <= 3:
        return 0.87, "元素类型不完全一致，建议复核"
    else:
        return 0.80, "[需核实] 元素类型差异较大"


def format_result(items: List[Any], operation: str, confidence: float, note: Optional[str]) -> Dict[str, Any]:
    """
    按约定格式生成输出

    Args:
        items: 处理后的数据
        operation: 操作类型（random_record / random_order）
        confidence: 置信度
        note: 提示信息

    Returns:
        结构化输出字典

    Raises:
        E008: 输出格式化失败
    """
    try:
        result: Dict[str, Any] = {
            "operation": operation,
            "result": items,
            "confidence": confidence,
            "confidence_label": _confidence_label(confidence),
        }
        if note:
            result["note"] = note
        return result
    except Exception:
        raise RuntimeError(get_error_message("E008"))


def _confidence_label(confidence: float) -> str:
    """将置信度转换为文字标签"""
    if confidence >= 0.90:
        return "直接输出"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


# ============================================================
# 标准流程
# ============================================================
def standard_process(raw_input: Any, operation: str = "random_order", seed: Optional[int] = None) -> Dict[str, Any]:
    """
    标准处理流程

    Step 1: 解析输入
    Step 2: 执行核心操作
    Step 3: 评估置信度并输出

    Args:
        raw_input: 用户输入
        operation: 操作类型（random_record / random_order）
        seed: 随机种子（可选）

    Returns:
        结构化输出

    Raises:
        E001-E008: 见各步骤错误
    """
    # Step 1: 解析输入
    items, parse_confidence = parse_input(raw_input)

    # Step 2: 执行核心操作
    finder = RandomFinder(seed)
    if operation == "random_record":
        result_item = finder.random_record(items)
        processed = result_item
    elif operation == "random_order":
        processed = finder.random_order(items)
    else:
        raise ValueError(get_error_message("E003"))

    # Step 3: 评估置信度并输出
    op_confidence, op_note = evaluate_confidence(items)
    final_confidence = min(parse_confidence, op_confidence)
    final_note = op_note

    return format_result(processed, operation, final_confidence, final_note)


# ============================================================
# 批量处理
# ============================================================
def batch_process(inputs: List[Any], operation: str = "random_order", seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    批量处理多个输入

    Args:
        inputs: 输入列表
        operation: 操作类型
        seed: 随机种子

    Returns:
        结果列表
    """
    results = []
    for raw_input in inputs:
        try:
            result = standard_process(raw_input, operation, seed)
            results.append({"status": "success", "data": result})
        except Exception as e:
            results.append({"status": "error", "error": str(e)})
    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================
def selftest() -> int:
    """
    内置离线自检

    使用硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。

    Returns:
        0 表示全部通过，非 0 表示失败
    """
    print("=" * 60)
    print("random-finders 自检开始")
    print("=" * 60)

    failures = 0

    # --- 测试 1: 基本随机记录获取 ---
    print("\n[1/8] 测试: 随机记录获取")
    try:
        sample = ["apple", "banana", "cherry", "date", "elderberry"]
        finder = RandomFinder(seed=42)
        for _ in range(20):
            record = finder.random_record(sample)
            assert record in sample, f"返回的记录 {record} 不在输入列表中"
        print("  ✓ 通过: 随机记录均在输入列表中")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试 2: 随机排列 ---
    print("\n[2/8] 测试: 随机排列")
    try:
        sample = list(range(1, 21))
        finder = RandomFinder(seed=123)
        for _ in range(10):
            shuffled = finder.random_order(sample)
            assert len(shuffled) == len(sample), "排列后长度不一致"
            assert sorted(shuffled) == sorted(sample), "排列后元素不一致"
        print("  ✓ 通过: 排列保持元素完整且长度不变")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试 3: 空输入错误处理 ---
    print("\n[3/8] 测试: 空输入错误处理")
    try:
        finder = RandomFinder()
        try:
            finder.random_record([])
            failures += 1
            print("  ✗ 失败: 空列表未抛出异常")
        except ValueError as e:
            assert "E001" in str(e), f"错误码不正确: {e}"
            print("  ✓ 通过: 空列表抛出 E001")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试 4: 输入解析 ---
    print("\n[4/8] 测试: 输入解析")
    try:
        # 列表输入
        items, conf = parse_input([1, 2, 3])
        assert items == [1, 2, 3], "列表解析失败"
        assert conf >= 0.90, f"置信度偏低: {conf}"

        # 字符串输入
        items, conf = parse_input("a, b, c")
        assert items == ["a", "b", "c"], f"字符串解析失败: {items}"
        assert conf >= 0.85, f"置信度偏低: {conf}"

        # 元组输入
        items, conf = parse_input((1, 2, 3))
        assert items == [1, 2, 3], "元组解析失败"
        print("  ✓ 通过: 列表/字符串/元组解析均正确")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试 5: 标准流程 ---
    print("\n[5/8] 测试: 标准流程")
    try:
        result = standard_process(["x", "y", "z"], operation="random_record", seed=7)
        assert result["operation"] == "random_record", "操作类型错误"
        assert result["result"] in ["x", "y", "z"], "结果不在输入中"
        assert result["confidence"] >= 0.80, f"置信度过低: {result['confidence']}"
        assert "confidence_label" in result, "缺少置信度标签"
        print(f"  ✓ 通过: 标准流程正常 (置信度={result['confidence']:.2f})")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试 6: 批量处理 ---
    print("\n[6/8] 测试: 批量处理")
    try:
        inputs = [
            ["a", "b", "c"],
            "1, 2, 3, 4",
            ["single"],
        ]
        results = batch_process(inputs, operation="random_order", seed=99)
        assert len(results) == 3, "批量处理数量错误"
        assert all(r["status"] == "success" for r in results), "存在失败项"
        print("  ✓ 通过: 批量处理全部成功")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试 7: 错误码完整性 ---
    print("\n[7/8] 测试: 错误码完整性")
    try:
        required_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
        for code in required_codes:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
            assert ERROR_MESSAGES[code].strip(), f"错误码 {code} 消息为空"
        print("  ✓ 通过: 错误码 E001-E010 均已定义且非空")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 测试 8: 随机性验证（宽松阈值）---
    print("\n[8/8] 测试: 随机性验证")
    try:
        sample = list(range(1, 101))
        finder = RandomFinder()  # 无种子，使用系统随机
        first_batch = set()
        for _ in range(30):
            first_batch.add(finder.random_record(sample))

        # 30 次采样应至少得到 10 个不同值（宽松阈值）
        assert len(first_batch) >= 10, f"随机性不足: 仅 {len(first_batch)} 个不同值"
        print(f"  ✓ 通过: 30 次采样得到 {len(first_batch)} 个不同值 (>=10)")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # --- 汇总 ---
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检全部通过 ✓")
        print("=" * 60)
        return 0
    else:
        print(f"自检失败: {failures} 项未通过 ✗")
        print("=" * 60)
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="random-finders - 随机记录获取与随机排列工具",
        epilog="示例: python main.py --input 'a,b,c' --operation random_record"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（列表或逗号分隔字符串）",
    )
    parser.add_argument(
        "--operation",
        type=str,
        choices=["random_record", "random_order"],
        default="random_order",
        help="操作类型: random_record(随机取一条) / random_order(随机排列)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子（可选，用于复现）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 正常处理模式
    try:
        if not args.input:
            print(get_error_message("E001"), file=sys.stderr)
            return 1

        result = standard_process(args.input, args.operation, args.seed)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except TypeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {get_error_message('E010')}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
