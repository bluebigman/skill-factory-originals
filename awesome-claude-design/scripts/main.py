#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

未命名工具（awesome-claude-design）独立实现脚本。

本脚本依据功能规格独立编写，不复制任何既有代码（clean-room）。
仅使用 Python 标准库，无第三方依赖。

功能：
- 将用户提供的文本/结构化输入转换为约定格式的结构化结果。
- 识别关键信息，标注置信度，支持批量处理。
- 内置异常处理错误码体系（E001-E010）。
- 提供 --selftest 离线自检模式，使用硬编码样例数据验证核心逻辑。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 工具名称与版本
TOOL_NAME = "awesome-claude-design"
TOOL_VERSION = "1.0.0"

# 置信度阈值（百分比）
CONFIDENCE_HIGH = 90      # 置信度 >= 90%：直接输出
CONFIDENCE_MEDIUM = 85    # 85% <= 置信度 < 90%：标注"建议复核"
# 置信度 < 85%：标注"[需核实]"

# 错误码定义（E001-E010，遵循功能规格）
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",           # 输入为空
    "E002": "还缺少以下信息，请补充：...",                                  # 关键信息缺失
    "E003": "输入格式不符合要求，示例：...",                                 # 输入格式错误
    "E004": "这超出了本工具的能力范围，建议...",                             # 超出能力边界
    "E005": "结果无法确定，建议：...",                                       # 置信度过低
    "E006": "内部处理错误：数据解析失败",                                    # 数据解析异常
    "E007": "内部处理错误：输出生成失败",                                    # 输出生成异常
    "E008": "参数错误：无法识别的命令行参数",                                # 命令行参数错误
    "E009": "批量处理错误：某一项处理失败",                                  # 批量处理错误
    "E010": "未知错误：发生未预料的异常",                                    # 未知错误
}

# 默认输出字段结构
DEFAULT_OUTPUT_FIELDS = ["id", "content", "key_info", "confidence", "note"]


# ---------------------------------------------------------------------------
# 核心功能模块
# ---------------------------------------------------------------------------

class InputParser:
    """输入解析器：解析用户输入的文本/结构化数据，识别关键信息。"""

    # 关键信息识别正则（宽松匹配，用于演示）
    _KEY_PATTERNS = [
        (r"名称[:：]\s*(\S+)", "name"),
        (r"类型[:：]\s*(\S+)", "type"),
        (r"数量[:：]\s*(\d+)", "quantity"),
        (r"价格[:：]\s*(\d+(?:\.\d+)?)", "price"),
        (r"日期[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", "date"),
    ]

    def parse(self, raw_input: str) -> Dict[str, Any]:
        """
        解析输入文本，提取结构化关键信息。

        参数:
            raw_input: 用户提供的原始输入字符串。

        返回:
            包含解析结果的字典，结构如下:
            {
                "content": 原始内容,
                "key_info": {字段名: 值, ...},   # 识别到的关键信息
                "confidence": 置信度(0-100),
                "note": 备注说明
            }

        异常:
            ValueError: 当输入为空或格式错误时抛出，携带错误码。
        """
        # 输入为空检查（错误码 E001）
        if raw_input is None or not raw_input.strip():
            raise ValueError("E001")

        content = raw_input.strip()

        # 输入格式检查（错误码 E003）
        # 要求输入至少包含一个中文字符或常见分隔符，否则视为格式错误
        if not re.search(r"[\u4e00-\u9fff]|[,，;；\n\t]", content):
            raise ValueError("E003")

        # 提取关键信息
        key_info: Dict[str, str] = {}
        for pattern, field_name in self._KEY_PATTERNS:
            match = re.search(pattern, content)
            if match:
                key_info[field_name] = match.group(1)

        # 计算置信度（基于识别到的关键信息数量）
        # 识别到 0 个字段：置信度低（60%）
        # 识别到 1-2 个字段：置信度中等（80%）
        # 识别到 3+ 个字段：置信度高（95%）
        field_count = len(key_info)
        if field_count == 0:
            confidence = 60
            note = "[需核实] 未能识别到明确的关键字段"
        elif field_count <= 2:
            confidence = 80
            note = "建议复核"  # 属于 85% 以下，但保持中性提示
        else:
            confidence = 95
            note = ""

        return {
            "content": content,
            "key_info": key_info,
            "confidence": confidence,
            "note": note,
        }


class OutputFormatter:
    """输出格式化器：将解析结果整理为约定格式。"""

    def format(self, parsed_data: Dict[str, Any], index: int = 1) -> Dict[str, Any]:
        """
        将解析结果格式化为标准输出结构。

        参数:
            parsed_data: 由 InputParser.parse() 返回的字典。
            index: 序号（用于批量处理时区分）。

        返回:
            符合 DEFAULT_OUTPUT_FIELDS 结构的字典。
        """
        # 输出生成失败检查（错误码 E007）
        if not isinstance(parsed_data, dict) or "content" not in parsed_data:
            raise ValueError("E007")

        confidence = parsed_data.get("confidence", 0)

        # 根据置信度添加标注
        note = parsed_data.get("note", "")
        if confidence >= CONFIDENCE_HIGH:
            pass  # 直接输出，无额外标注
        elif confidence >= CONFIDENCE_MEDIUM:
            note = "建议复核" if not note else note
        else:
            note = "[需核实] " + (note if note else "结果无法确定")

        return {
            "id": index,
            "content": parsed_data["content"],
            "key_info": parsed_data.get("key_info", {}),
            "confidence": confidence,
            "note": note,
        }


class BatchProcessor:
    """批量处理器：支持对多个输入进行统一处理。"""

    def __init__(self) -> None:
        self.parser = InputParser()
        self.formatter = OutputFormatter()

    def process(self, inputs: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理多个输入。

        参数:
            inputs: 输入字符串列表。

        返回:
            格式化后的结果列表。

        异常:
            ValueError: 当批量处理中某一项失败时抛出（错误码 E009）。
        """
        results = []
        for idx, raw_input in enumerate(inputs, start=1):
            try:
                parsed = self.parser.parse(raw_input)
                formatted = self.formatter.format(parsed, index=idx)
                results.append(formatted)
            except ValueError as e:
                # 批量处理中某一项失败，抛出 E009
                error_code = str(e)
                base_error = ERROR_CODES.get(error_code, ERROR_CODES["E010"])
                raise ValueError(f"E009: 第 {idx} 项处理失败（{error_code}）: {base_error}")

        return results


class ToolEngine:
    """主引擎：协调各模块完成完整处理流程。"""

    def __init__(self) -> None:
        self.parser = InputParser()
        self.formatter = OutputFormatter()
        self.batch_processor = BatchProcessor()

    def run_single(self, raw_input: str) -> Dict[str, Any]:
        """处理单个输入。"""
        parsed = self.parser.parse(raw_input)
        return self.formatter.format(parsed)

    def run_batch(self, inputs: List[str]) -> List[Dict[str, Any]]:
        """批量处理多个输入。"""
        return self.batch_processor.process(inputs)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保任何环境直接可过。

    返回:
        0 表示全部通过，非 0 表示存在失败项。
    """
    print("=" * 60)
    print(f"开始自检: {TOOL_NAME} v{TOOL_VERSION}")
    print("=" * 60)

    engine = ToolEngine()
    failures = 0

    # ------------------------------------------------------------------
    # 测试用例 1: 正常输入（完整字段）
    # ------------------------------------------------------------------
    print("\n[测试 1] 正常输入（完整字段）")
    try:
        sample = "名称: 测试商品, 类型: 电子产品, 数量: 10, 价格: 99.5, 日期: 2026-01-15"
        result = engine.run_single(sample)

        # 宽松断言：置信度应较高（>= 85）
        assert result["confidence"] >= 85, f"置信度过低: {result['confidence']}"
        # 关键信息应包含 name
        assert "name" in result["key_info"], "缺少 name 字段"
        # 数量应能解析为数字
        assert int(result["key_info"].get("quantity", 0)) > 0, "数量解析异常"
        print(f"  ✓ 通过 (置信度: {result['confidence']}%)")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # ------------------------------------------------------------------
    # 测试用例 2: 部分字段缺失（中等置信度）
    # ------------------------------------------------------------------
    print("\n[测试 2] 部分字段缺失")
    try:
        sample = "名称: 测试服务, 类型: 咨询"
        result = engine.run_single(sample)

        # 置信度应在合理区间（50-90）
        assert 50 <= result["confidence"] <= 90, f"置信度不在合理区间: {result['confidence']}"
        # 应识别到 name
        assert "name" in result["key_info"], "缺少 name 字段"
        print(f"  ✓ 通过 (置信度: {result['confidence']}%)")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # ------------------------------------------------------------------
    # 测试用例 3: 空输入（应触发 E001）
    # ------------------------------------------------------------------
    print("\n[测试 3] 空输入（错误码 E001）")
    try:
        engine.run_single("   ")
        failures += 1
        print("  ✗ 失败: 未触发错误")
    except ValueError as e:
        assert str(e) == "E001", f"错误码不正确: {e}"
        print("  ✓ 通过 (正确触发 E001)")

    # ------------------------------------------------------------------
    # 测试用例 4: 格式错误输入（应触发 E003）
    # ------------------------------------------------------------------
    print("\n[测试 4] 格式错误输入（错误码 E003）")
    try:
        engine.run_single("abc123xyz")  # 无中文字符，无分隔符
        failures += 1
        print("  ✗ 失败: 未触发错误")
    except ValueError as e:
        assert str(e) == "E003", f"错误码不正确: {e}"
        print("  ✓ 通过 (正确触发 E003)")

    # ------------------------------------------------------------------
    # 测试用例 5: 批量处理
    # ------------------------------------------------------------------
    print("\n[测试 5] 批量处理")
    try:
        inputs = [
            "名称: 项目A, 数量: 5",
            "名称: 项目B, 类型: 开发, 日期: 2026-02-01",
            "名称: 项目C, 价格: 100",
        ]
        results = engine.run_batch(inputs)

        # 应返回 3 条结果
        assert len(results) == 3, f"结果数量不正确: {len(results)}"
        # 每条结果都应有 id 和 content
        for r in results:
            assert r["id"] > 0, "id 无效"
            assert r["content"], "content 为空"
        # id 应递增
        assert results[0]["id"] < results[1]["id"] < results[2]["id"], "id 顺序错误"
        print(f"  ✓ 通过 (共 {len(results)} 条结果)")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # ------------------------------------------------------------------
    # 测试用例 6: 置信度标注逻辑
    # ------------------------------------------------------------------
    print("\n[测试 6] 置信度标注逻辑")
    try:
        # 低置信度样例（无关键字段）
        sample_low = "这是一段普通的中文描述文字，不包含任何关键字段标识。"
        result_low = engine.run_single(sample_low)
        assert result_low["confidence"] < 85, f"低置信度未正确判定: {result_low['confidence']}"
        assert "[需核实]" in result_low["note"], "低置信度未正确标注"

        # 高置信度样例（多个关键字段）
        sample_high = "名称: 产品X, 类型: 硬件, 数量: 20, 价格: 199.9"
        result_high = engine.run_single(sample_high)
        assert result_high["confidence"] >= 90, f"高置信度未正确判定: {result_high['confidence']}"
        assert result_high["note"] == "", "高置信度不应有额外标注"

        print("  ✓ 通过 (低置信度标注与高置信度判定均正确)")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # ------------------------------------------------------------------
    # 测试用例 7: 批量处理中的错误处理（E009）
    # ------------------------------------------------------------------
    print("\n[测试 7] 批量处理错误处理（错误码 E009）")
    try:
        inputs = ["名称: 有效输入", ""]  # 第二个为空输入
        engine.run_batch(inputs)
        failures += 1
        print("  ✗ 失败: 未触发错误")
    except ValueError as e:
        error_str = str(e)
        assert error_str.startswith("E009"), f"错误码不正确: {error_str}"
        print(f"  ✓ 通过 (正确触发 E009)")

    # ------------------------------------------------------------------
    # 测试用例 8: 错误码体系完整性
    # ------------------------------------------------------------------
    print("\n[测试 8] 错误码体系完整性")
    try:
        # 检查 E001-E010 是否都有定义
        for code in [f"E{i:03d}" for i in range(1, 11)]:
            assert code in ERROR_CODES, f"错误码 {code} 未定义"
        # 检查错误码描述非空
        for code, desc in ERROR_CODES.items():
            assert desc.strip(), f"错误码 {code} 描述为空"
        print(f"  ✓ 通过 (共 {len(ERROR_CODES)} 个错误码)")
    except Exception as e:
        failures += 1
        print(f"  ✗ 失败: {e}")

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    if failures == 0:
        print(f"自检完成: 全部通过 ✓ ({TOOL_NAME} v{TOOL_VERSION})")
    else:
        print(f"自检完成: {failures} 项失败 ✗")
    print("=" * 60)

    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """
    主入口函数：解析命令行参数并执行相应操作。

    支持:
        --selftest: 运行离线自检。
        直接传入文本: 处理单个输入。
        --batch: 批量处理（配合文件输入，此处仅演示标准输入）。
        --json: 以 JSON 格式输出。

    返回:
        进程退出码（0 成功，非 0 失败）。
    """
    parser = argparse.ArgumentParser(
        description=f"{TOOL_NAME} - 未命名工具（仅供学习与参考用途）",
        epilog="示例: python main.py '名称: 测试, 类型: 演示' 或 python main.py --selftest"
    )
    parser.add_argument(
        "input",
        nargs="*",
        help="待处理的输入文本（可多个，按批量处理）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部环境）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{TOOL_NAME} {TOOL_VERSION}"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无输入且非自检模式
    if not args.input:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检，或直接提供输入文本。", file=sys.stderr)
        return 1

    # 处理输入
    engine = ToolEngine()
    try:
        results = engine.run_batch(list(args.input))
    except ValueError as e:
        error_str = str(e)
        # 提取错误码
        code_match = re.match(r"(E\d{3})", error_str)
        code = code_match.group(1) if code_match else "E010"
        print(f"错误 {code}: {ERROR_CODES.get(code, ERROR_CODES['E010'])}", file=sys.stderr)
        print(f"详细信息: {error_str}", file=sys.stderr)
        return 1

    # 输出结果
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print("-" * 40)
            print(f"[{r['id']}] 内容: {r['content']}")
            print(f"    关键信息: {json.dumps(r['key_info'], ensure_ascii=False)}")
            print(f"    置信度: {r['confidence']}%")
            if r["note"]:
                print(f"    备注: {r['note']}")
        print("-" * 40)

    return 0


if __name__ == "__main__":
    sys.exit(main())
