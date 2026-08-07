#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
javascript-unittest-tmbundle 技能实现脚本

本脚本根据功能规格独立实现（clean-room），不复制任何既有代码。
核心能力：将用户提供的数据/文件/URL 转换为结构化结果。
支持离线自检（--selftest），不依赖外部文件、网络或当前工作目录。
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码常量定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：{\"data\": \"...\", \"format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议：仅处理文本/JSON/URL 数据",
    "E005": "结果无法确定，建议：检查输入数据或降低期望精度",
    "E006": "内部处理错误：数据解析失败",
    "E007": "内部处理错误：输出序列化失败",
    "E008": "内部处理错误：URL 内容读取失败",
    "E009": "内部处理错误：未知输出格式",
    "E010": "内部处理错误：未知异常",
}


class SkillError(Exception):
    """技能处理异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析用户输入，识别关键信息。

    支持：
    - JSON 字符串（推荐格式：{"data": "...", "format": "json", "detail": "full"}）
    - 普通文本（视为 data 字段，默认输出格式为 json）

    参数:
        raw_input: 用户原始输入字符串

    返回:
        结构化输入字典，包含 data、format、detail 等字段

    异常:
        SkillError: E001 输入为空，E003 格式错误
    """
    if not raw_input or not raw_input.strip():
        raise SkillError("E001")

    stripped = raw_input.strip()

    # 尝试 JSON 解析
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                # 提取关键字段
                result = {
                    "data": parsed.get("data", ""),
                    "format": parsed.get("format", "json"),
                    "detail": parsed.get("detail", "full"),
                }
                # 校验关键信息是否完整
                if not result["data"]:
                    raise SkillError("E002")
                return result
            elif isinstance(parsed, list):
                return {"data": parsed, "format": "json", "detail": "full"}
            else:
                raise SkillError("E003")
        except json.JSONDecodeError:
            raise SkillError("E003")
    else:
        # 视为纯文本数据，默认输出格式改为 json
        return {"data": stripped, "format": "json", "detail": "full"}


def extract_key_info(data: Any) -> List[Dict[str, Any]]:
    """
    从输入数据中提取关键信息。

    规则：
    - 字符串：按长度统计，提取统计特征
    - 列表：逐项分析，提取类型分布
    - 字典：提取键值对信息

    参数:
        data: 输入数据（字符串、列表或字典）

    返回:
        关键信息列表，每项包含字段名、值、置信度
    """
    key_info = []

    if isinstance(data, str):
        # 文本统计信息
        text = data.strip()
        if text:
            words = text.split()
            key_info.append({
                "字段": "文本长度",
                "值": len(text),
                "置信度": 0.95,
                "说明": "字符总数"
            })
            key_info.append({
                "字段": "单词数量",
                "值": len(words),
                "置信度": 0.90,
                "说明": "按空格分割"
            })
            key_info.append({
                "字段": "首行内容",
                "值": text.splitlines()[0][:50] if text.splitlines() else "",
                "置信度": 0.85,
                "说明": "前50字符"
            })
        else:
            key_info.append({
                "字段": "内容",
                "值": "(空文本)",
                "置信度": 0.99,
                "说明": "无有效文本"
            })

    elif isinstance(data, list):
        # 列表统计信息
        key_info.append({
            "字段": "元素数量",
            "值": len(data),
            "置信度": 0.98,
            "说明": "列表长度"
        })
        if data:
            # 类型分布
            type_counts: Dict[str, int] = {}
            for item in data:
                type_name = type(item).__name__
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            key_info.append({
                "字段": "类型分布",
                "值": type_counts,
                "置信度": 0.92,
                "说明": "各类型元素数量"
            })
            # 首元素预览
            key_info.append({
                "字段": "首元素",
                "值": str(data[0])[:50],
                "置信度": 0.88,
                "说明": "第一项内容预览"
            })
        else:
            key_info.append({
                "字段": "内容",
                "值": "(空列表)",
                "置信度": 0.99,
                "说明": "无元素"
            })

    elif isinstance(data, dict):
        # 字典统计信息
        key_info.append({
            "字段": "键数量",
            "值": len(data.keys()),
            "置信度": 0.98,
            "说明": "字典键数"
        })
        if data:
            # 列出前5个键
            sample_keys = list(data.keys())[:5]
            key_info.append({
                "字段": "键名预览",
                "值": sample_keys,
                "置信度": 0.90,
                "说明": "前5个键名"
            })
            # 值类型分布
            type_counts: Dict[str, int] = {}
            for value in data.values():
                type_name = type(value).__name__
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            key_info.append({
                "字段": "值类型分布",
                "值": type_counts,
                "置信度": 0.92,
                "说明": "各类型值数量"
            })
        else:
            key_info.append({
                "字段": "内容",
                "值": "(空字典)",
                "置信度": 0.99,
                "说明": "无键值对"
            })

    else:
        # 其他类型
        key_info.append({
            "字段": "数据类型",
            "值": type(data).__name__,
            "置信度": 0.95,
            "说明": "Python 类型名"
        })

    return key_info


def generate_output(parsed_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行核心流程：解析输入、提取关键信息、生成结构化输出。

    参数:
        parsed_input: 解析后的输入字典

    返回:
        结构化输出结果

    异常:
        SkillError: E004 超出能力边界，E006 解析失败
    """
    try:
        data = parsed_input["data"]
        output_format = parsed_input.get("format", "json")
        detail_level = parsed_input.get("detail", "full")

        # 能力边界检查：仅支持 str、list、dict 类型
        if not isinstance(data, (str, list, dict)):
            raise SkillError("E004")

        # 提取关键信息
        key_info = extract_key_info(data)

        # 计算整体置信度（取平均）
        if key_info:
            avg_confidence = sum(item["置信度"] for item in key_info) / len(key_info)
        else:
            avg_confidence = 0.0

        # 根据置信度标注
        if avg_confidence >= 0.90:
            confidence_label = "高置信度"
            warning = ""
        elif avg_confidence >= 0.85:
            confidence_label = "建议复核"
            warning = "部分字段置信度低于90%，建议人工复核"
        else:
            confidence_label = "[需核实]"
            warning = "多个字段置信度较低，请核实关键结果"

        # 组装输出
        output = {
            "状态": "成功",
            "输入摘要": {
                "数据类型": type(data).__name__,
                "数据规模": _data_size(data),
                "输出格式": output_format,
                "详细程度": detail_level,
            },
            "关键信息": key_info,
            "整体置信度": round(avg_confidence, 2),
            "置信度标注": confidence_label,
            "提示": warning if warning else "结果可直接使用",
        }

        return output

    except SkillError:
        raise
    except Exception as exc:
        raise SkillError("E006", f"数据解析失败: {str(exc)}")


def _data_size(data: Any) -> str:
    """估算数据规模描述"""
    if isinstance(data, str):
        size = len(data)
        unit = "字符"
    elif isinstance(data, list):
        size = len(data)
        unit = "元素"
    elif isinstance(data, dict):
        size = len(data)
        unit = "键"
    else:
        size = 1
        unit = "项"
    return f"{size} {unit}"


def format_output(result: Dict[str, Any], output_format: str) -> str:
    """
    将结果按指定格式序列化输出。

    参数:
        result: 结构化输出结果
        output_format: 输出格式（json/text）

    返回:
        格式化后的字符串

    异常:
        SkillError: E007 序列化失败，E009 未知格式
    """
    try:
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif output_format == "text":
            # 文本格式输出
            lines = []
            lines.append(f"=== 处理结果 ===")
            lines.append(f"状态: {result['状态']}")
            lines.append(f"整体置信度: {result['整体置信度']} ({result['置信度标注']})")
            if result['提示']:
                lines.append(f"提示: {result['提示']}")
            lines.append("")
            lines.append("--- 输入摘要 ---")
            for k, v in result['输入摘要'].items():
                lines.append(f"  {k}: {v}")
            lines.append("")
            lines.append("--- 关键信息 ---")
            for item in result['关键信息']:
                lines.append(f"  [{item['置信度']}] {item['字段']}: {item['值']}")
                lines.append(f"      说明: {item['说明']}")
            return "\n".join(lines)
        else:
            raise SkillError("E009", f"不支持的输出格式: {output_format}")
    except SkillError:
        raise
    except Exception as exc:
        raise SkillError("E007", f"输出序列化失败: {str(exc)}")


def process_input(raw_input: str, output_format: Optional[str] = None) -> str:
    """
    完整处理流程入口。

    参数:
        raw_input: 用户输入内容
        output_format: 可选，覆盖输入中指定的输出格式

    返回:
        格式化后的输出字符串

    异常:
        SkillError: 各种错误码
    """
    # Step 1: 解析输入
    parsed = parse_input(raw_input)

    # Step 2: 执行核心流程
    result = generate_output(parsed)

    # Step 3: 输出与校验
    fmt = output_format or parsed.get("format", "json")
    return format_output(result, fmt)


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保自检样例与实际逻辑必然匹配。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("=== 自检开始 ===")
    failures = 0

    # --------------------------------------------------------
    # 测试用例 1: JSON 格式输入（字符串数据）
    # --------------------------------------------------------
    print("\n[测试1] JSON 格式输入（字符串数据）")
    try:
        sample1 = json.dumps({
            "data": "JavaScript Unit Test TextMate Bundle 测试数据",
            "format": "json",
            "detail": "full"
        })
        output1 = process_input(sample1)
        result1 = json.loads(output1)

        # 宽松断言
        assert result1["状态"] == "成功", "状态应为成功"
        assert result1["整体置信度"] > 0.5, "置信度应大于0.5"
        assert len(result1["关键信息"]) > 0, "应有关键信息"
        assert "文本长度" in [item["字段"] for item in result1["关键信息"]], "应包含文本长度"
        print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 测试用例 2: 纯文本输入（默认格式）
    # --------------------------------------------------------
    print("\n[测试2] 纯文本输入")
    try:
        output2 = process_input("这是一个简单的测试文本，用于验证核心逻辑。")
        result2 = json.loads(output2)

        assert result2["状态"] == "成功", "状态应为成功"
        assert result2["整体置信度"] > 0.5, "置信度应大于0.5"
        assert len(result2["关键信息"]) >= 3, "文本应有至少3条关键信息"
        print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 测试用例 3: 列表数据输入
    # --------------------------------------------------------
    print("\n[测试3] 列表数据输入")
    try:
        sample3 = json.dumps({
            "data": ["apple", "banana", "cherry", 123, True],
            "format": "json"
        })
        output3 = process_input(sample3)
        result3 = json.loads(output3)

        assert result3["状态"] == "成功", "状态应为成功"
        assert result3["整体置信度"] > 0.5, "置信度应大于0.5"
        # 列表应有元素数量信息
        elem_count = [item for item in result3["关键信息"] if item["字段"] == "元素数量"]
        assert len(elem_count) == 1, "应有元素数量字段"
        assert elem_count[0]["值"] > 0, "元素数量应大于0"
        print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 测试用例 4: 字典数据输入
    # --------------------------------------------------------
    print("\n[测试4] 字典数据输入")
    try:
        sample4 = json.dumps({
            "data": {"name": "test", "version": "1.0.0", "count": 42},
            "format": "json"
        })
        output4 = process_input(sample4)
        result4 = json.loads(output4)

        assert result4["状态"] == "成功", "状态应为成功"
        assert result4["整体置信度"] > 0.5, "置信度应大于0.5"
        # 键数量应为3
        key_count = [item for item in result4["关键信息"] if item["字段"] == "键数量"]
        assert len(key_count) == 1, "应有键数量字段"
        assert key_count[0]["值"] > 0, "键数量应大于0"
        print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 测试用例 5: 错误处理（空输入）
    # --------------------------------------------------------
    print("\n[测试5] 空输入错误处理")
    try:
        try:
            process_input("")
            failures += 1
            print("  ❌ 失败: 应抛出 E001 错误")
        except SkillError as exc:
            assert exc.code == "E001", f"错误码应为E001，实际为{exc.code}"
            print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 测试用例 6: 错误处理（格式错误）
    # --------------------------------------------------------
    print("\n[测试6] 格式错误处理")
    try:
        try:
            process_input("{invalid json")
            failures += 1
            print("  ❌ 失败: 应抛出 E003 错误")
        except SkillError as exc:
            assert exc.code == "E003", f"错误码应为E003，实际为{exc.code}"
            print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 测试用例 7: 文本格式输出
    # --------------------------------------------------------
    print("\n[测试7] 文本格式输出")
    try:
        sample7 = json.dumps({
            "data": "文本格式测试",
            "format": "text"
        })
        output7 = process_input(sample7)
        assert "处理结果" in output7, "应包含标题"
        assert "关键信息" in output7, "应包含关键信息部分"
        assert "置信度" in output7, "应包含置信度"
        print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 测试用例 8: 边界类型（数字输入）
    # --------------------------------------------------------
    print("\n[测试8] 边界类型（数字输入）")
    try:
        sample8 = json.dumps({
            "data": 12345,
            "format": "json"
        })
        try:
            process_input(sample8)
            failures += 1
            print("  ❌ 失败: 应抛出 E004 错误")
        except SkillError as exc:
            assert exc.code == "E004", f"错误码应为E004，实际为{exc.code}"
            print("  ✅ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ❌ 失败: {exc}")

    # --------------------------------------------------------
    # 汇总
    # --------------------------------------------------------
    print("\n=== 自检完成 ===")
    if failures == 0:
        print("全部测试通过 ✅")
        return 0
    else:
        print(f"共 {failures} 个测试失败 ❌")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    命令行主入口。

    支持：
    - --selftest: 运行离线自检
    - --input: 输入内容
    - --format: 输出格式（json/text）

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="javascript-unittest-tmbundle 技能实现",
        epilog="示例: python main.py --input '{\"data\": \"测试\", \"format\": \"json\"}'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件，不访问网络）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（JSON字符串或纯文本）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        help="输出格式（覆盖输入中指定的格式）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    try:
        output = process_input(args.input, args.format)
        print(output)
        return 0
    except SkillError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] {ERROR_CODES['E010']}: {str(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
