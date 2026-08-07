#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm-kit 独立实现脚本
仅依据功能规格设计，clean-room 重写
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional


# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式生成失败，请检查参数",
    "E008": "批量处理中断，请检查输入列表",
    "E009": "参数解析错误，请检查命令行参数",
    "E010": "未知错误，请联系维护者",
}


class PMKitError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


def validate_input(data: Any) -> None:
    """校验输入是否为空（E001）"""
    if data is None:
        raise PMKitError("E001")
    if isinstance(data, str) and not data.strip():
        raise PMKitError("E001")
    if isinstance(data, (list, dict)) and len(data) == 0:
        raise PMKitError("E001")


def check_required_fields(data: Dict, required: List[str]) -> None:
    """检查关键字段是否缺失（E002）"""
    missing = [field for field in required if field not in data or data[field] in (None, "", [])]
    if missing:
        raise PMKitError("E002", ERROR_CODES["E002"] + "、".join(missing))


def validate_format(data: Any, expected_type: type) -> None:
    """校验输入格式（E003）"""
    if not isinstance(data, expected_type):
        raise PMKitError("E003", ERROR_CODES["E003"] + f"期望类型: {expected_type.__name__}")


def check_capability(task: str) -> None:
    """检查是否超出能力边界（E004）"""
    # 定义不支持的操作关键词
    unsupported_keywords = ["网络请求", "外部API", "实时数据", "股票交易", "医疗诊断"]
    for keyword in unsupported_keywords:
        if keyword in str(task):
            raise PMKitError("E004", ERROR_CODES["E004"] + "请提供本地数据或文件")


def calculate_confidence(data: Dict) -> float:
    """计算置信度（基于字段完整度）"""
    if not data:
        return 0.0
    # 基础字段权重
    weights = {
        "title": 0.3,
        "content": 0.3,
        "author": 0.2,
        "date": 0.2,
    }
    score = 0.0
    for field, weight in weights.items():
        if field in data and data[field]:
            score += weight
    # 额外字段加分
    extra_fields = ["tags", "priority", "status"]
    for field in extra_fields:
        if field in data and data[field]:
            score += 0.05
    return min(score, 1.0) * 100


def format_output(data: Dict, confidence: float) -> Dict:
    """按模板组织输出"""
    result = {
        "processed_at": datetime.now().isoformat(),
        "confidence": f"{confidence:.1f}%",
        "data": data,
    }

    # 根据置信度添加标注
    if confidence >= 90:
        result["status"] = "可直接使用"
    elif confidence >= 85:
        result["status"] = "建议复核"
    else:
        result["status"] = "[需核实]"

    return result


def process_single_input(input_data: Any) -> Dict:
    """处理单个输入的核心流程"""
    # Step 1: 校验输入
    validate_input(input_data)
    check_capability(str(input_data))

    # Step 2: 结构化处理
    if isinstance(input_data, str):
        # 尝试解析JSON字符串
        try:
            parsed = json.loads(input_data)
            if isinstance(parsed, dict):
                data = parsed
            else:
                data = {"content": input_data}
        except json.JSONDecodeError:
            data = {"content": input_data}
    elif isinstance(input_data, dict):
        data = input_data
    elif isinstance(input_data, list):
        data = {"items": input_data}
    else:
        raise PMKitError("E003", ERROR_CODES["E003"] + "支持字符串、字典或列表")

    # 检查关键字段
    check_required_fields(data, ["content"] if "content" in data else [])

    # Step 3: 计算置信度并输出
    confidence = calculate_confidence(data)
    if confidence < 85:
        # 低置信度处理（E005）
        result = format_output(data, confidence)
        result["warning"] = ERROR_CODES["E005"] + "请补充更多字段信息"
        return result

    return format_output(data, confidence)


def batch_process(inputs: List[Any]) -> List[Dict]:
    """批量处理输入"""
    validate_input(inputs)
    validate_format(inputs, list)

    results = []
    for idx, item in enumerate(inputs):
        try:
            result = process_single_input(item)
            result["batch_index"] = idx + 1
            results.append(result)
        except PMKitError as e:
            results.append({
                "batch_index": idx + 1,
                "error": e.code,
                "message": e.message,
                "skipped": True,
            })

    return results


def run_selftest() -> bool:
    """内置自检函数，使用硬编码样例数据"""
    print("开始离线自检...")

    # 测试用例1: 基本字符串输入
    test1 = "这是一个测试内容"
    try:
        result1 = process_single_input(test1)
        assert "processed_at" in result1, "缺少时间戳"
        assert "confidence" in result1, "缺少置信度"
        assert result1["data"]["content"] == test1, "内容未正确保留"
        print("✓ 测试1通过: 基本字符串输入")
    except AssertionError as e:
        print(f"✗ 测试1失败: {e}")
        return False
    except PMKitError as e:
        print(f"✗ 测试1异常: {e}")
        return False

    # 测试用例2: 字典输入
    test2 = {
        "title": "项目周报",
        "content": "本周完成了核心模块开发",
        "author": "张三",
        "date": "2026-01-01",
        "tags": ["开发", "周报"],
    }
    try:
        result2 = process_single_input(test2)
        # 宽松断言：置信度应该较高（>=85）
        confidence = float(result2["confidence"].rstrip("%"))
        assert confidence >= 85, f"置信度应>=85%，实际{confidence}%"
        assert result2["status"] in ["可直接使用", "建议复核"], "状态标注异常"
        print(f"✓ 测试2通过: 字典输入 (置信度{confidence}%)")
    except AssertionError as e:
        print(f"✗ 测试2失败: {e}")
        return False
    except PMKitError as e:
        print(f"✗ 测试2异常: {e}")
        return False

    # 测试用例3: 空输入处理
    try:
        process_single_input("")
        print("✗ 测试3失败: 空输入应报错")
        return False
    except PMKitError as e:
        assert e.code == "E001", f"错误码应为E001，实际{e.code}"
        print("✓ 测试3通过: 空输入正确报错")

    # 测试用例4: JSON字符串输入
    test4 = '{"title": "测试", "content": "JSON内容", "priority": "high"}'
    try:
        result4 = process_single_input(test4)
        assert result4["data"]["title"] == "测试", "JSON解析失败"
        print("✓ 测试4通过: JSON字符串解析")
    except AssertionError as e:
        print(f"✗ 测试4失败: {e}")
        return False
    except PMKitError as e:
        print(f"✗ 测试4异常: {e}")
        return False

    # 测试用例5: 批量处理
    test5 = ["内容1", {"content": "内容2"}, ""]
    try:
        results5 = batch_process(test5)
        assert len(results5) == 3, "批量处理数量不对"
        # 第三个应该被跳过
        assert results5[2].get("skipped", False), "空输入应被跳过"
        # 前两个应该有结果
        assert "processed_at" in results5[0], "第一个结果异常"
        assert "processed_at" in results5[1], "第二个结果异常"
        print("✓ 测试5通过: 批量处理")
    except AssertionError as e:
        print(f"✗ 测试5失败: {e}")
        return False
    except PMKitError as e:
        print(f"✗ 测试5异常: {e}")
        return False

    # 测试用例6: 能力边界检查
    try:
        check_capability("需要访问网络请求获取数据")
        print("✗ 测试6失败: 应拒绝网络请求")
        return False
    except PMKitError as e:
        assert e.code == "E004", f"错误码应为E004，实际{e.code}"
        print("✓ 测试6通过: 能力边界检查")

    # 测试用例7: 格式校验
    try:
        validate_format("不是列表", list)
        print("✗ 测试7失败: 格式校验应失败")
        return False
    except PMKitError as e:
        assert e.code == "E003", f"错误码应为E003，实际{e.code}"
        print("✓ 测试7通过: 格式校验")

    # 测试用例8: 低置信度处理
    test8 = {"content": "只有内容字段"}
    try:
        result8 = process_single_input(test8)
        confidence = float(result8["confidence"].rstrip("%"))
        assert confidence < 85, f"置信度应<85%，实际{confidence}%"
        assert result8["status"] == "[需核实]", "状态应为[需核实]"
        print(f"✓ 测试8通过: 低置信度处理 (置信度{confidence}%)")
    except AssertionError as e:
        print(f"✗ 测试8失败: {e}")
        return False
    except PMKitError as e:
        print(f"✗ 测试8异常: {e}")
        return False

    print("\n所有自检测试通过！")
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="pm-kit 工具 - 处理结构化数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检测试（不依赖外部文件或网络）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容：字符串、JSON字符串或文件路径",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON数组字符串",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "pretty"],
        default="json",
        help="输出格式（默认json）",
    )

    try:
        args = parser.parse_args()

        # 自检模式
        if args.selftest:
            success = run_selftest()
            sys.exit(0 if success else 1)

        # 处理输入
        if args.batch:
            # 批量处理模式
            try:
                batch_data = json.loads(args.batch)
                results = batch_process(batch_data)
            except json.JSONDecodeError:
                raise PMKitError("E003", ERROR_CODES["E003"] + "批量输入需为JSON数组")
            except PMKitError as e:
                print(json.dumps({"error": e.code, "message": e.message}, ensure_ascii=False))
                sys.exit(1)
        elif args.input:
            # 单条处理模式
            try:
                results = process_single_input(args.input)
            except PMKitError as e:
                print(json.dumps({"error": e.code, "message": e.message}, ensure_ascii=False))
                sys.exit(1)
        else:
            # 无输入，显示帮助
            parser.print_help()
            sys.exit(0)

        # 输出结果
        if args.output_format == "pretty":
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(results, ensure_ascii=False))

    except PMKitError as e:
        print(json.dumps({"error": e.code, "message": e.message}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": "E010", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
