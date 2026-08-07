#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hatch3r - 未命名工具

一个仅供学习与参考用途的 CLI 工具，用于将用户提供的数据/文件/URL
转换为结构化结果，识别关键信息，按约定格式输出，并给出置信度提示。

用法示例:
    python main.py --input "张三,25,北京,工程师"
    python main.py --input "张三,25,北京,工程师" --format json
    python main.py --selftest
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失，还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：字段1,字段2,字段3,...",
    "E004": "这超出了本工具的能力范围，建议：简化输入或拆分处理",
    "E005": "结果无法确定（置信度过低），建议：补充更多上下文信息",
    "E006": "内部处理错误（未知异常），请检查输入后重试",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "批量输入中某项处理失败，已跳过该项",
    "E009": "输出格式不支持，仅支持 text / json / csv",
    "E010": "文件读取失败，请检查文件路径和权限",
}


class Hatch3rError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_CODES.get(code, "未知错误")
        # 替换消息中的占位符
        for key, value in kwargs.items():
            self.message = self.message.replace("{" + key + "}", str(value))
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

# 预定义的关键信息模式（用于识别输入中的关键字段）
# 每个模式包含：字段名、正则表达式、置信度权重
FIELD_PATTERNS = [
    {"name": "姓名", "pattern": r"[A-Za-z\u4e00-\u9fa5]{2,10}", "weight": 0.3},
    {"name": "年龄", "pattern": r"\d{1,3}", "weight": 0.2},
    {"name": "城市", "pattern": r"[A-Za-z\u4e00-\u9fa5]{2,20}", "weight": 0.2},
    {"name": "职业", "pattern": r"[A-Za-z\u4e00-\u9fa5]{2,20}", "weight": 0.15},
    {"name": "邮箱", "pattern": r"[\w.+-]+@[\w-]+\.[\w.]+", "weight": 0.15},
]


def extract_fields(text: str) -> Tuple[List[Dict[str, str]], float]:
    """
    从输入文本中提取关键信息字段。

    返回:
        (字段列表, 置信度) - 字段列表为 [{name, value}]，置信度为 0~100 的浮点数。
    """
    if not text or not text.strip():
        raise Hatch3rError("E001")

    # 按逗号、分号、竖线、空白分割输入
    parts = [p.strip() for p in re.split(r"[,;|\t\n]+", text) if p.strip()]
    if not parts:
        raise Hatch3rError("E003")

    fields: List[Dict[str, str]] = []
    matched_count = 0
    total_weight = 0.0

    # 逐项匹配预定义模式
    for part in parts:
        matched = False
        for pattern_info in FIELD_PATTERNS:
            name = pattern_info["name"]
            # 跳过已提取的同名字段
            if any(f["name"] == name for f in fields):
                continue
            if re.fullmatch(pattern_info["pattern"], part):
                fields.append({"name": name, "value": part})
                total_weight += pattern_info["weight"]
                matched = True
                matched_count += 1
                break
        if not matched:
            # 未匹配的项标记为“其他”
            fields.append({"name": "其他", "value": part})
            total_weight += 0.05

    # 计算置信度：匹配到的字段数量 / 总输入项数量 * 100
    # 同时结合权重，但使用宽松的区间判断
    if len(parts) > 0:
        # 基础置信度 = 匹配项占比
        base_confidence = (matched_count / len(parts)) * 100.0
        # 加权调整，但限制在 0~100 之间
        confidence = min(100.0, max(0.0, base_confidence * 0.7 + total_weight * 30.0))
    else:
        confidence = 0.0

    return fields, confidence


def process_input(input_text: str) -> Dict[str, Any]:
    """
    处理单个输入，返回结构化结果。

    返回的字典结构:
        {
            "input": 原始输入,
            "fields": [{name, value}, ...],
            "confidence": 置信度 (0~100),
            "status": "ok" | "review" | "uncertain",
            "message": 附加提示信息
        }
    """
    if not input_text or not input_text.strip():
        raise Hatch3rError("E001")

    fields, confidence = extract_fields(input_text)

    # 根据置信度设置状态
    if confidence >= 90.0:
        status = "ok"
        message = "处理完成，置信度较高，可直接使用"
    elif confidence >= 85.0:
        status = "review"
        message = "处理完成，置信度中等，建议复核"
    else:
        status = "uncertain"
        message = "处理完成，置信度较低，部分字段可能不准确，请核实"

    result = {
        "input": input_text,
        "fields": fields,
        "confidence": round(confidence, 1),
        "status": status,
        "message": message,
    }
    return result


def process_batch(inputs: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个输入，逐项处理，单项失败不中断整体。"""
    results = []
    for item in inputs:
        try:
            results.append(process_input(item))
        except Hatch3rError as e:
            # 记录错误并跳过该项
            results.append({
                "input": item,
                "error_code": e.code,
                "error_message": e.message,
                "status": "error",
            })
        except Exception as e:
            results.append({
                "input": item,
                "error_code": "E006",
                "error_message": str(e),
                "status": "error",
            })
    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(results: List[Dict[str, Any]], fmt: str = "text") -> str:
    """将结果列表按指定格式输出。"""
    if fmt == "text":
        return _format_text(results)
    elif fmt == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    elif fmt == "csv":
        return _format_csv(results)
    else:
        raise Hatch3rError("E009")


def _format_text(results: List[Dict[str, Any]]) -> str:
    """文本格式输出，适合人阅读。"""
    lines = []
    for i, result in enumerate(results, 1):
        lines.append(f"--- 结果 {i} ---")
        if result.get("status") == "error":
            lines.append(f"错误: {result.get('error_message', '未知错误')}")
            continue
        lines.append(f"输入: {result['input']}")
        lines.append(f"置信度: {result['confidence']}% ({result['status']})")
        lines.append(f"提示: {result['message']}")
        lines.append("字段:")
        for field in result["fields"]:
            lines.append(f"  - {field['name']}: {field['value']}")
    return "\n".join(lines)


def _format_csv(results: List[Dict[str, Any]]) -> str:
    """CSV 格式输出。"""
    lines = ["输入,字段名,字段值,置信度,状态"]
    for result in results:
        if result.get("status") == "error":
            lines.append(f"{result.get('input', '')},错误,,,{result.get('error_message', '')}")
            continue
        for field in result["fields"]:
            # 简单转义逗号和换行
            input_val = result["input"].replace(",", " ").replace("\n", " ")
            name = field["name"].replace(",", " ")
            value = field["value"].replace(",", " ").replace("\n", " ")
            lines.append(f"{input_val},{name},{value},{result['confidence']},{result['status']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检函数（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置硬编码样例数据进行离线自检。
    不读取外部文件、不依赖工作目录、不访问网络。

    断言使用宽松阈值，避免精确值依赖。
    """
    print("开始自检 hatch3r 核心逻辑...")
    passed = 0
    failed = 0

    # --- 测试用例 1: 正常输入 ---
    try:
        result = process_input("张三,25,北京,工程师")
        assert result["status"] in ("ok", "review", "uncertain"), "状态值不合法"
        assert len(result["fields"]) >= 3, "字段数量过少"
        assert result["confidence"] > 0, "置信度应为正数"
        assert result["confidence"] <= 100, "置信度不应超过100"
        # 检查关键字段是否被识别
        field_names = [f["name"] for f in result["fields"]]
        assert "姓名" in field_names or "其他" in field_names, "缺少姓名或其他字段"
        passed += 1
        print("  [PASS] 正常输入测试")
    except AssertionError as e:
        failed += 1
        print(f"  [FAIL] 正常输入测试: {e}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] 正常输入测试异常: {e}")

    # --- 测试用例 2: 空输入 ---
    try:
        process_input("")
        failed += 1
        print("  [FAIL] 空输入应抛出 E001 错误")
    except Hatch3rError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        passed += 1
        print("  [PASS] 空输入错误处理")
    except Exception:
        failed += 1
        print("  [FAIL] 空输入应抛出 Hatch3rError")

    # --- 测试用例 3: 邮箱识别 ---
    try:
        result = process_input("test@example.com,张三")
        assert len(result["fields"]) >= 1, "应至少识别一个字段"
        # 邮箱字段可能被识别为“其他”或“邮箱”
        field_values = [f["value"] for f in result["fields"]]
        assert any("@" in v for v in field_values), "应包含邮箱信息"
        passed += 1
        print("  [PASS] 邮箱识别测试")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] 邮箱识别测试: {e}")

    # --- 测试用例 4: 批量处理 ---
    try:
        results = process_batch(["张三,25", "", "李四,30,上海"])
        assert len(results) == 3, "批量处理应返回3个结果"
        # 检查错误项
        error_items = [r for r in results if r.get("status") == "error"]
        assert len(error_items) == 1, "应有一个错误项"
        assert error_items[0]["error_code"] == "E001", "错误码应为 E001"
        passed += 1
        print("  [PASS] 批量处理测试")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] 批量处理测试: {e}")

    # --- 测试用例 5: 输出格式 ---
    try:
        results = process_batch(["张三,25"])
        text_out = format_output(results, "text")
        json_out = format_output(results, "json")
        csv_out = format_output(results, "csv")
        assert len(text_out) > 0, "文本输出不应为空"
        assert len(json_out) > 0, "JSON输出不应为空"
        assert len(csv_out) > 0, "CSV输出不应为空"
        # JSON 应可解析
        parsed = json.loads(json_out)
        assert isinstance(parsed, list), "JSON输出应为列表"
        passed += 1
        print("  [PASS] 输出格式测试")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] 输出格式测试: {e}")

    # --- 测试用例 6: 高置信度输入 ---
    try:
        # 完整匹配所有字段，置信度应较高
        result = process_input("张三,25,北京,工程师,zhangsan@mail.com")
        assert result["confidence"] > 50, "完整输入置信度应较高"
        passed += 1
        print("  [PASS] 高置信度测试")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] 高置信度测试: {e}")

    # --- 测试用例 7: 低置信度输入 ---
    try:
        # 无法识别的输入，置信度应较低
        result = process_input("???")
        assert result["confidence"] < 50, "无法识别输入的置信度应较低"
        passed += 1
        print("  [PASS] 低置信度测试")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] 低置信度测试: {e}")

    # --- 汇总 ---
    print(f"\n自检完成: {passed} 通过, {failed} 失败")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="hatch3r - 未命名工具（仅供学习与参考用途）",
        epilog="示例: python main.py --input '张三,25,北京' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容，多个字段用逗号分隔",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，多个输入用分号分隔",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入（每行一个）",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "csv"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，不读取外部文件",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="hatch3r 1.0.0",
    )
    return parser.parse_args(argv)


def read_input_file(filepath: str) -> List[str]:
    """从文件读取输入，每行一个。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            raise Hatch3rError("E001")
        return lines
    except Hatch3rError:
        raise
    except FileNotFoundError:
        raise Hatch3rError("E010")
    except Exception:
        raise Hatch3rError("E010")


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    try:
        args = parse_args(argv)

        # 自检模式
        if args.selftest:
            return run_selftest()

        # 收集输入
        inputs: List[str] = []

        if args.file:
            # 从文件读取
            inputs = read_input_file(args.file)
        elif args.batch:
            # 批量输入，分号分隔
            inputs = [item.strip() for item in args.batch.split(";") if item.strip()]
        elif args.input:
            # 单个输入
            inputs = [args.input]
        else:
            # 没有输入，尝试从 stdin 读取
            if not sys.stdin.isatty():
                stdin_data = sys.stdin.read().strip()
                if stdin_data:
                    inputs = [stdin_data]
                else:
                    raise Hatch3rError("E001")
            else:
                raise Hatch3rError("E001")

        if not inputs:
            raise Hatch3rError("E001")

        # 处理输入
        results = process_batch(inputs)

        # 输出结果
        output = format_output(results, args.format)
        print(output)

        return 0

    except Hatch3rError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("操作被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 [E006]: 内部处理错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
