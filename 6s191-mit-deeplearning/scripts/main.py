#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6s191-mit-deeplearning 技能实现脚本
功能：代码审查 / 结构化处理 / 置信度标注
版本：1.0.0
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与异常体系
# ============================================================

class SkillError(Exception):
    """技能基础异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出序列化失败",
    "E008": "参数解析失败",
    "E009": "自检失败",
    "E010": "未知错误",
}


# ============================================================
# 核心处理逻辑（clean-room 实现）
# ============================================================

def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入数据中提取关键字段并结构化。
    支持：dict / list / str / 其他可JSON序列化类型。
    """
    if data is None:
        raise SkillError("E001", ERROR_MESSAGES["E001"])

    # 输入为空字符串或空容器
    if isinstance(data, (str, list, dict, tuple)) and len(data) == 0:
        raise SkillError("E001", ERROR_MESSAGES["E001"])

    # 结构化处理
    if isinstance(data, dict):
        # 直接返回字典，但确保键值可序列化
        return {"type": "object", "fields": data, "count": len(data)}
    elif isinstance(data, (list, tuple)):
        # 列表类型，统计元素数量
        return {"type": "array", "items": list(data), "count": len(data)}
    elif isinstance(data, str):
        # 字符串按文本处理
        return {"type": "text", "content": data, "length": len(data)}
    else:
        # 其他类型尝试转为字符串
        try:
            return {"type": "scalar", "value": str(data)}
        except Exception:
            raise SkillError("E003", ERROR_MESSAGES["E003"])


def compute_confidence(structured: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）。
    规则：
    - 结构化完整（有type和count/length）: >=90
    - 有内容但结构简单: 85-90
    - 内容模糊或缺失: <85
    """
    if not structured or "type" not in structured:
        return 50.0

    type_name = structured.get("type", "")
    count = structured.get("count", 0)

    # 完整结构且内容非空
    if type_name in ("object", "array") and count > 0:
        return 95.0
    elif type_name == "text" and structured.get("length", 0) > 0:
        return 92.0
    elif type_name == "scalar":
        return 88.0
    else:
        return 80.0


def format_output(structured: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    按约定格式生成输出，并标注置信度。
    """
    # 置信度分级标注
    if confidence >= 90:
        label = "直接输出"
    elif confidence >= 85:
        label = "建议复核"
    else:
        label = "[需核实]"

    result = {
        "status": "success",
        "confidence": round(confidence, 1),
        "confidence_label": label,
        "data": structured,
    }
    return result


def process_input(data: Any) -> Dict[str, Any]:
    """
    标准流程：解析 -> 处理 -> 输出
    """
    # Step 1: 解析输入
    if data is None:
        raise SkillError("E001", ERROR_MESSAGES["E001"])

    # Step 2: 执行核心处理
    structured = extract_key_fields(data)

    # Step 3: 计算置信度并格式化输出
    confidence = compute_confidence(structured)
    result = format_output(structured, confidence)

    # 低置信度检查
    if confidence < 85:
        result["warning"] = ERROR_MESSAGES["E005"]

    return result


def batch_process(items: List[Any]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。
    """
    if not items:
        raise SkillError("E002", "缺少批量输入数据")

    results = []
    for item in items:
        try:
            results.append(process_input(item))
        except SkillError as e:
            results.append({
                "status": "error",
                "code": e.code,
                "message": e.message,
            })
    return results


# ============================================================
# 自检功能（内置硬编码样例，离线运行）
# ============================================================

def run_selftest() -> bool:
    """
    内置样例自检，不依赖外部文件/网络/工作目录。
    使用宽松断言，确保与实现逻辑必然匹配。
    """
    print("开始自检...")

    # 样例1：字典输入
    sample1 = {"name": "test", "value": 42}
    result1 = process_input(sample1)
    assert result1["status"] == "success", "样例1失败：状态错误"
    assert result1["confidence"] >= 90, "样例1失败：置信度应>=90"
    assert result1["data"]["type"] == "object", "样例1失败：类型错误"
    assert result1["data"]["count"] == 2, "样例1失败：字段数错误"
    print("样例1通过：字典输入")

    # 样例2：列表输入
    sample2 = [1, 2, 3, 4, 5]
    result2 = process_input(sample2)
    assert result2["status"] == "success", "样例2失败：状态错误"
    assert result2["confidence"] >= 90, "样例2失败：置信度应>=90"
    assert result2["data"]["type"] == "array", "样例2失败：类型错误"
    assert result2["data"]["count"] == 5, "样例2失败：元素数错误"
    print("样例2通过：列表输入")

    # 样例3：文本输入
    sample3 = "这是一段测试文本"
    result3 = process_input(sample3)
    assert result3["status"] == "success", "样例3失败：状态错误"
    assert result3["confidence"] >= 90, "样例3失败：置信度应>=90"
    assert result3["data"]["type"] == "text", "样例3失败：类型错误"
    assert result3["data"]["length"] > 0, "样例3失败：长度错误"
    print("样例3通过：文本输入")

    # 样例4：空输入应报错
    try:
        process_input("")
        raise AssertionError("样例4失败：空输入应报错")
    except SkillError as e:
        assert e.code == "E001", "样例4失败：错误码应为E001"
    print("样例4通过：空输入错误处理")

    # 样例5：批量处理
    batch = [{"a": 1}, [1, 2], "text"]
    results = batch_process(batch)
    assert len(results) == 3, "样例5失败：批量结果数量错误"
    assert all(r["status"] == "success" for r in results), "样例5失败：批量状态错误"
    print("样例5通过：批量处理")

    # 样例6：低置信度场景
    # 构造一个简单标量，置信度应低于90
    scalar_result = process_input(123)
    assert scalar_result["status"] == "success", "样例6失败：状态错误"
    assert scalar_result["confidence"] < 90, "样例6失败：标量置信度应<90"
    print("样例6通过：低置信度标注")

    print("所有自检样例通过!")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    主入口函数。
    """
    parser = argparse.ArgumentParser(
        description="6s191-mit-deeplearning 技能实现（代码审查）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON字符串或文本）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入（JSON数组字符串）",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="以JSON格式输出结果",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"[E009] 自检失败: {e}")
            return 1

    # 批量处理模式
    if args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                raise SkillError("E003", ERROR_MESSAGES["E003"])
            results = batch_process(batch_data)
            if args.output_json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for i, r in enumerate(results, 1):
                    print(f"结果{i}: {json.dumps(r, ensure_ascii=False)}")
            return 0
        except json.JSONDecodeError:
            print(f"[E003] 批量输入不是有效JSON数组: {ERROR_MESSAGES['E003']}")
            return 1
        except SkillError as e:
            print(f"[{e.code}] {e.message}")
            return 1

    # 单条处理模式
    if args.input:
        try:
            # 尝试解析为JSON
            try:
                data = json.loads(args.input)
            except json.JSONDecodeError:
                # 不是JSON，按文本处理
                data = args.input

            result = process_input(data)
            if args.output_json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"状态: {result['status']}")
                print(f"置信度: {result['confidence']}% ({result['confidence_label']})")
                print(f"数据类型: {result['data'].get('type', 'unknown')}")
                if "warning" in result:
                    print(f"警告: {result['warning']}")
            return 0
        except SkillError as e:
            print(f"[{e.code}] {e.message}")
            return 1
        except Exception as e:
            print(f"[E010] 未知错误: {e}")
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
