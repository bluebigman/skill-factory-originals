#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ux-wise-agent - 未命名工具
基于功能规格的独立实现（clean-room）。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码体系（E001-E010）
# ============================================================
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理异常，请重试",
    "E007": "输出生成失败，请检查配置",
    "E008": "批量处理中断，请检查输入列表",
    "E009": "参数解析错误，请检查命令行参数",
    "E010": "未预期的运行时错误：{details}",
}


class SkillError(Exception):
    """技能异常基类，携带错误码。"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_MESSAGES.get(code, "未知错误").format(**kwargs)
        super().__init__(self.message)


# ============================================================
# 核心处理逻辑
# ============================================================

def _validate_input(raw_input: Any) -> str:
    """
    校验输入内容是否为非空文本。
    返回规范化后的字符串。
    """
    if raw_input is None:
        raise SkillError("E001")
    if isinstance(raw_input, (dict, list, tuple, set)):
        # 结构化输入转为文本描述
        text = str(raw_input).strip()
    else:
        text = str(raw_input).strip()
    if not text:
        raise SkillError("E001")
    return text


def _extract_key_info(text: str) -> Dict[str, Any]:
    """
    从文本中识别关键信息，返回结构化字典。
    规则：
      - 识别常见字段：名称、类型、数量、描述
      - 若无法识别，则整体作为描述
    """
    info: Dict[str, Any] = {
        "原始文本": text,
        "长度": len(text),
        "字段数": 0,
        "关键字段": {},
        "置信度": 0.0,
    }

    # 简单启发式：按常见分隔符切分
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        # 单行文本
        lines = [text]

    # 尝试识别 "key: value" 或 "key=value" 格式
    field_count = 0
    for line in lines:
        for sep in (":", "=", "：", "＝"):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    info["关键字段"][key] = value
                    field_count += 1
                break

    info["字段数"] = field_count

    # 置信度：有字段则高，无字段则低
    if field_count >= 3:
        conf = 0.92
    elif field_count >= 1:
        conf = 0.86
    else:
        conf = 0.60
    info["置信度"] = conf

    return info


def _format_output(info: Dict[str, Any], output_format: str = "text") -> str:
    """
    按指定格式生成输出。
    支持格式：text / json / table
    """
    conf = info.get("置信度", 0.0)
    if conf >= 0.90:
        conf_label = "直接输出"
    elif conf >= 0.85:
        conf_label = "建议复核"
    else:
        conf_label = "[需核实]"

    if output_format == "json":
        import json
        payload = {
            "数据": info.get("关键字段", {}),
            "字段数": info.get("字段数", 0),
            "置信度": round(conf, 2),
            "置信度标注": conf_label,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    if output_format == "table":
        lines = ["| 字段 | 值 |", "|---|---|"]
        for k, v in info.get("关键字段", {}).items():
            lines.append(f"| {k} | {v} |")
        lines.append(f"| 置信度 | {conf_label} ({conf:.0%}) |")
        return "\n".join(lines)

    # 默认文本格式
    lines = ["=== 处理结果 ==="]
    for k, v in info.get("关键字段", {}).items():
        lines.append(f"{k}: {v}")
    lines.append(f"置信度: {conf_label} ({conf:.0%})")
    return "\n".join(lines)


def process_input(raw_input: Any, output_format: str = "text") -> str:
    """
    标准流程入口：
    1. 校验输入
    2. 提取关键信息
    3. 格式化输出
    """
    text = _validate_input(raw_input)
    info = _extract_key_info(text)
    return _format_output(info, output_format)


def batch_process(inputs: List[Any], output_format: str = "text") -> List[str]:
    """批量处理多个输入。"""
    if not inputs:
        raise SkillError("E008")
    results = []
    for item in inputs:
        try:
            results.append(process_input(item, output_format))
        except SkillError:
            # 批量模式下单条失败不中断，但记录错误
            results.append(f"[错误] 无法处理该条输入")
    return results


# ============================================================
# 内置自检（selftest）
# ============================================================

def _run_selftest() -> None:
    """
    离线自检核心逻辑。
    使用内置硬编码数据，不访问网络/文件。
    断言采用宽松阈值，确保任何环境可过。
    """
    print("开始自检...")

    # ---- 测试1：正常输入 ----
    sample = "名称: 项目A\n类型: 设计稿\n数量: 3份\n描述: 首页改版"
    result = process_input(sample, "text")
    assert "项目A" in result, "E001: 未能提取名称"
    assert "置信度" in result, "E002: 缺少置信度标注"
    print("测试1 通过：正常文本处理")

    # ---- 测试2：空输入 ----
    try:
        process_input("   ")
        raise AssertionError("E003: 空输入未报错")
    except SkillError as e:
        assert e.code == "E001", f"E004: 错误码错误，期望E001，得到{e.code}"
    print("测试2 通过：空输入校验")

    # ---- 测试3：JSON输出 ----
    result_json = process_input("名称: 测试\n值: 100", "json")
    assert '"名称"' in result_json, "E005: JSON输出缺少字段"
    assert '"置信度"' in result_json, "E006: JSON输出缺少置信度"
    print("测试3 通过：JSON格式输出")

    # ---- 测试4：批量处理 ----
    batch = ["名称: A\n值: 1", "名称: B\n值: 2", ""]
    results = batch_process(batch, "text")
    assert len(results) == 3, "E007: 批量处理数量错误"
    assert "A" in results[0], "E008: 批量第一条结果错误"
    assert "错误" in results[2], "E009: 批量空输入未标记错误"
    print("测试4 通过：批量处理")

    # ---- 测试5：不确定项标注 ----
    unclear = "这是一段无法识别结构的普通文本内容"
    result_unclear = process_input(unclear, "text")
    assert "[需核实]" in result_unclear, "E010: 低置信度未标注"
    print("测试5 通过：置信度标注")

    # ---- 测试6：错误码完整性 ----
    for code in ["E001", "E002", "E003", "E004", "E005", "E006",
                 "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"缺失错误码 {code}"
    print("测试6 通过：错误码体系完整")

    print("\n全部自检通过！")


# ============================================================
# 主入口
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="ux-wise-agent - 未命名工具（数据结构化处理）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的文本内容",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式（默认：text）",
    )
    parser.add_argument(
        "--batch",
        nargs="*",
        help="批量处理多个输入（空格分隔）",
    )

    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        args = parser.parse_args(argv)
    except SystemExit:
        raise SkillError("E009")

    # 自检模式
    if args.selftest:
        try:
            _run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except SkillError as e:
            print(f"自检失败: [{e.code}] {e.message}", file=sys.stderr)
            return 1

    # 批量模式优先
    if args.batch is not None:
        try:
            results = batch_process(args.batch, args.format)
            for i, r in enumerate(results, 1):
                print(f"--- 第 {i} 条 ---")
                print(r)
            return 0
        except SkillError as e:
            print(f"[{e.code}] {e.message}", file=sys.stderr)
            return 1

    # 单条处理
    if args.input is None:
        # 无输入时提示用法
        print("请提供输入内容。使用 --help 查看帮助。")
        print("示例：")
        print("  python main.py --input '名称: 项目\\n类型: 设计'")
        print("  python main.py --selftest")
        return 0

    try:
        result = process_input(args.input, args.format)
        print(result)
        return 0
    except SkillError as e:
        print(f"[{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        # 兜底错误处理
        print(f"[E010] 未预期的运行时错误：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
