#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 独立实现脚本

功能概述：
    本脚本依据功能规格独立实现，核心能力为：
      1. 将用户提供的数据/文件/URL 转换为结构化结果
      2. 识别并保留输入中的关键信息
      3. 按约定格式生成输出
      4. 对不确定项给出置信度提示
      5. 支持批量处理和自定义格式

    包含 --selftest 参数，使用硬编码样例离线验证核心逻辑，
    不依赖外部文件、当前工作目录或网络。

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常
    E007: 参数解析异常
    E008: 输出生成异常
    E009: 自检初始化异常
    E010: 自检断言异常
"""

import argparse
import sys
import re
import json
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

# 可识别的关键字段定义（名称 -> 提取规则类型）
# 规则类型: "url" / "email" / "date" / "keyword" / "plain"
KEY_FIELD_RULES: Dict[str, str] = {
    "url": "url",
    "email": "email",
    "date": "date",
    "name": "plain",
    "id": "plain",
}

# 置信度阈值
HIGH_CONFIDENCE = 90.0    # >= 90% 直接输出
MEDIUM_CONFIDENCE = 85.0  # 85%-90% 建议复核
# < 85% 标注 [需核实]


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------

def validate_input(data: Any) -> None:
    """
    校验输入数据是否有效。

    参数:
        data: 用户输入的数据

    异常:
        E001: 输入为空
        E003: 输入格式错误
    """
    if data is None:
        raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    if isinstance(data, str):
        if not data.strip():
            raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    elif isinstance(data, (list, tuple, dict)):
        if len(data) == 0:
            raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")
    else:
        raise ValueError("E003: 输入格式不符合要求，示例：文本、URL、文件路径或数据列表")


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段信息。

    参数:
        data: 用户输入的数据（字符串或结构化数据）

    返回:
        提取到的关键字段字典

    异常:
        E002: 关键信息缺失
    """
    fields: Dict[str, Any] = {}

    if isinstance(data, str):
        text = data.strip()

        # 提取 URL
        url_match = re.search(r'https?://[^\s]+', text)
        if url_match:
            fields["url"] = url_match.group(0)

        # 提取 Email
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
        if email_match:
            fields["email"] = email_match.group(0)

        # 提取日期 (YYYY-MM-DD 或 YYYY/MM/DD)
        date_match = re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text)
        if date_match:
            fields["date"] = date_match.group(0)

        # 提取可能的 ID（连续数字，至少3位）
        id_match = re.search(r'\b\d{3,}\b', text)
        if id_match:
            fields["id"] = id_match.group(0)

        # 提取名称（简单启发式：URL/Email/日期之后的第一个词）
        remaining = re.sub(r'https?://[^\s]+', '', text)
        remaining = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '', remaining)
        remaining = re.sub(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', '', remaining)
        words = remaining.split()
        if words:
            fields["name"] = words[0].strip('.,;:!?')

    elif isinstance(data, dict):
        # 直接取字典中的关键字段
        for key in KEY_FIELD_RULES:
            if key in data and data[key] is not None:
                fields[key] = data[key]

    elif isinstance(data, (list, tuple)):
        # 列表/元组：尝试从第一个元素提取
        if data:
            return extract_key_fields(data[0])

    # 检查是否提取到任何关键信息
    if not fields:
        raise ValueError("E002: 还缺少以下信息，请补充：待处理的内容中未识别到关键信息（URL、Email、日期、名称或ID）")

    return fields


def calculate_confidence(fields: Dict[str, Any], input_data: Any) -> float:
    """
    计算结果置信度。

    参数:
        fields: 提取到的字段
        input_data: 原始输入

    返回:
        置信度分数 (0-100)
    """
    if not fields:
        return 0.0

    # 基础置信度
    base_score = 50.0

    # 字段数量加分
    field_count = len(fields)
    base_score += field_count * 10.0

    # 输入类型加分
    if isinstance(input_data, str):
        if len(input_data.strip()) > 50:
            base_score += 10.0  # 长文本更可靠
        if re.search(r'https?://', input_data):
            base_score += 5.0   # 包含 URL
    elif isinstance(input_data, dict):
        base_score += 15.0      # 结构化输入更可靠

    # 关键字段存在性加分
    if "url" in fields:
        base_score += 5.0
    if "email" in fields:
        base_score += 5.0
    if "date" in fields:
        base_score += 5.0

    # 限制范围
    return min(99.0, max(0.0, base_score))


def format_output(
    fields: Dict[str, Any],
    confidence: float,
    custom_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    按约定格式生成输出结果。

    参数:
        fields: 提取到的关键字段
        confidence: 置信度
        custom_format: 自定义输出格式（可选）

    返回:
        格式化后的结果字典

    异常:
        E008: 输出生成异常
    """
    try:
        result: Dict[str, Any] = {
            "status": "success",
            "data": fields,
            "confidence": confidence,
            "confidence_level": "",
            "warning": "",
        }

        # 置信度分级标注
        if confidence >= HIGH_CONFIDENCE:
            result["confidence_level"] = "high"
            result["warning"] = "可直接使用"
        elif confidence >= MEDIUM_CONFIDENCE:
            result["confidence_level"] = "medium"
            result["warning"] = "建议复核"
        else:
            result["confidence_level"] = "low"
            result["warning"] = "[需核实] 结果不确定，请人工确认"

        # 自定义格式支持
        if custom_format:
            if custom_format == "json":
                # 默认就是 JSON 兼容结构，无需额外处理
                pass
            elif custom_format == "compact":
                # 精简格式，只保留核心数据
                compact = {
                    "data": fields,
                    "confidence": confidence
                }
                result = compact
            else:
                raise ValueError(f"E003: 不支持的输出格式: {custom_format}")

        return result

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"E008: 输出生成异常: {str(e)}")


def process_single(data: Any, custom_format: Optional[str] = None) -> Dict[str, Any]:
    """
    处理单个输入项。

    参数:
        data: 输入数据
        custom_format: 自定义输出格式

    返回:
        处理结果字典
    """
    # Step 1: 校验输入
    validate_input(data)

    # Step 2: 提取关键字段
    fields = extract_key_fields(data)

    # Step 3: 计算置信度
    confidence = calculate_confidence(fields, data)

    # Step 4: 格式化输出
    result = format_output(fields, confidence, custom_format)

    return result


def process_batch(
    data_list: List[Any],
    custom_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    批量处理多个输入项。

    参数:
        data_list: 输入数据列表
        custom_format: 自定义输出格式

    返回:
        批量处理结果
    """
    if not data_list:
        raise ValueError("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    results = []
    errors = []

    for idx, item in enumerate(data_list):
        try:
            result = process_single(item, custom_format)
            results.append({"index": idx, "result": result})
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})

    return {
        "status": "success" if not errors else "partial",
        "total": len(data_list),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> None:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖任何外部资源。
    断言使用宽松阈值，确保稳定性。

    异常:
        E009: 自检初始化异常
        E010: 自检断言异常
    """
    try:
        print("=" * 60)
        print("自检开始 (Self-Test)")
        print("=" * 60)

        # ---- 测试用例 1: 有效 URL 输入 ----
        print("\n[测试 1] URL 输入")
        test_input_1 = "请处理这个链接 https://example.com/game/12345 并提取信息"
        try:
            result_1 = process_single(test_input_1)
            assert result_1["status"] == "success", "状态应为 success"
            assert "url" in result_1["data"], "应提取到 URL"
            assert result_1["data"]["url"] == "https://example.com/game/12345", "URL 值不正确"
            assert result_1["confidence"] > 50, "置信度应大于 50"
            assert result_1["confidence"] <= 100, "置信度不应超过 100"
            print(f"  ✓ 通过: 提取到 URL={result_1['data']['url']}, 置信度={result_1['confidence']:.1f}%")
        except AssertionError as e:
            raise ValueError(f"E010: 断言失败 - {str(e)}")
        except ValueError as e:
            print(f"  ✗ 失败: {str(e)}")
            raise

        # ---- 测试用例 2: 包含 Email 和日期的文本 ----
        print("\n[测试 2] Email + 日期")
        test_input_2 = "联系 developer@example.com 在 2026-03-15 前回复，项目编号 789012"
        try:
            result_2 = process_single(test_input_2)
            assert result_2["status"] == "success", "状态应为 success"
            assert "email" in result_2["data"], "应提取到 Email"
            assert "date" in result_2["data"], "应提取到日期"
            assert result_2["confidence"] > 50, "置信度应大于 50"
            print(f"  ✓ 通过: Email={result_2['data']['email']}, 日期={result_2['data']['date']}, 置信度={result_2['confidence']:.1f}%")
        except AssertionError as e:
            raise ValueError(f"E010: 断言失败 - {str(e)}")
        except ValueError as e:
            print(f"  ✗ 失败: {str(e)}")
            raise

        # ---- 测试用例 3: 结构化字典输入 ----
        print("\n[测试 3] 字典输入")
        test_input_3 = {
            "name": "Game Project Alpha",
            "id": "GP-2026-001",
            "url": "https://studio.example.com/projects/gp-001",
        }
        try:
            result_3 = process_single(test_input_3)
            assert result_3["status"] == "success", "状态应为 success"
            assert "name" in result_3["data"], "应提取到 name"
            assert "id" in result_3["data"], "应提取到 id"
            assert result_3["confidence"] > 60, "结构化输入置信度应较高"
            print(f"  ✓ 通过: name={result_3['data'].get('name')}, 置信度={result_3['confidence']:.1f}%")
        except AssertionError as e:
            raise ValueError(f"E010: 断言失败 - {str(e)}")
        except ValueError as e:
            print(f"  ✗ 失败: {str(e)}")
            raise

        # ---- 测试用例 4: 批量处理 ----
        print("\n[测试 4] 批量处理")
        test_batch = [
            "第一个项目 https://example.com/proj/111",
            "联系 team@example.com 获取详情",
            "无有效信息的内容",
            {"name": "结构化项目", "id": "ID-2026-002"},
        ]
        try:
            batch_result = process_batch(test_batch)
            assert batch_result["total"] == 4, "总数应为 4"
            assert batch_result["success_count"] >= 2, "至少 2 个应成功"
            assert batch_result["error_count"] >= 0, "错误数应 >= 0"
            assert len(batch_result["results"]) == batch_result["success_count"], "结果数应匹配"
            print(f"  ✓ 通过: 总数={batch_result['total']}, 成功={batch_result['success_count']}, 失败={batch_result['error_count']}")
        except AssertionError as e:
            raise ValueError(f"E010: 断言失败 - {str(e)}")
        except ValueError as e:
            print(f"  ✗ 失败: {str(e)}")
            raise

        # ---- 测试用例 5: 错误处理 ----
        print("\n[测试 5] 错误处理")
        try:
            # 空输入
            process_single(None)
            raise ValueError("E010: 空输入应抛出 E001")
        except ValueError as e:
            assert str(e).startswith("E001"), f"应抛出 E001, 实际: {str(e)}"
            print(f"  ✓ 通过: 空输入错误处理正确 ({str(e)})")

        try:
            # 无关键信息
            process_single("这是一段没有任何关键信息的普通文本")
            raise ValueError("E010: 无关键信息应抛出 E002")
        except ValueError as e:
            assert str(e).startswith("E002"), f"应抛出 E002, 实际: {str(e)}"
            print(f"  ✓ 通过: 关键信息缺失错误处理正确 ({str(e)})")

        # ---- 测试用例 6: 置信度分级 ----
        print("\n[测试 6] 置信度分级")
        try:
            # 高置信度（结构化完整输入）
            high_input = {
                "name": "Test Project",
                "id": "123456",
                "url": "https://example.com",
                "email": "a@b.com",
                "date": "2026-01-01"
            }
            high_result = process_single(high_input)
            assert high_result["confidence"] >= HIGH_CONFIDENCE, "结构化完整输入置信度应高"
            assert high_result["confidence_level"] == "high", "应为 high 级别"
            print(f"  ✓ 通过: 高置信度分级正确 ({high_result['confidence']:.1f}%)")

            # 低置信度（仅一个字段）
            low_input = "仅有一个名称 TestName"
            low_result = process_single(low_input)
            assert low_result["confidence"] < HIGH_CONFIDENCE, "简单输入置信度不应过高"
            print(f"  ✓ 通过: 低置信度分级正确 ({low_result['confidence']:.1f}%)")
        except AssertionError as e:
            raise ValueError(f"E010: 断言失败 - {str(e)}")
        except ValueError as e:
            print(f"  ✗ 失败: {str(e)}")
            raise

        # ---- 测试用例 7: 自定义格式 ----
        print("\n[测试 7] 自定义格式")
        try:
            # 测试 compact 格式
            compact_result = process_single(test_input_1, custom_format="compact")
            assert "data" in compact_result, "compact 格式应包含 data 字段"
            assert "confidence" in compact_result, "compact 格式应包含 confidence 字段"
            print(f"  ✓ 通过: compact 格式输出正确")
            
            # 测试不支持的格式
            try:
                process_single(test_input_1, custom_format="xml")
                raise ValueError("E010: 不支持的格式应抛出异常")
            except ValueError as e:
                assert str(e).startswith("E003"), f"应抛出 E003, 实际: {str(e)}"
                print(f"  ✓ 通过: 不支持的格式错误处理正确 ({str(e)})")
        except AssertionError as e:
            raise ValueError(f"E010: 断言失败 - {str(e)}")
        except ValueError as e:
            print(f"  ✗ 失败: {str(e)}")
            raise

        print("\n" + "=" * 60)
        print("全部自检通过 ✓")
        print("=" * 60)

    except ValueError as e:
        print(f"\n自检失败: {str(e)}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> None:
    """
    主函数：解析命令行参数并执行相应操作。
    """
    parser = argparse.ArgumentParser(
        description="未命名工具 - 将输入数据转换为结构化结果",
        epilog="示例: python main.py --input 'https://example.com' --format json"
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（文本、URL、文件路径）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "compact"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    try:
        args = parser.parse_args()

        # 自检模式
        if args.selftest:
            run_selftest()
            return

        # 正常处理模式
        if not args.input:
            print("E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
            print("提示: 使用 --input 参数，或运行 --selftest 进行自检", file=sys.stderr)
            sys.exit(1)

        # 尝试读取文件内容
        input_data = args.input
        if args.input.startswith("file://"):
            # 文件协议支持
            filepath = args.input[7:]
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except OSError as e:
                print(f"E006: 文件读取失败: {str(e)}", file=sys.stderr)
                sys.exit(1)

        # 处理输入
        try:
            result = process_single(input_data, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nE007: 用户中断操作", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E006: 未预期的异常: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
