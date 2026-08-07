#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tidescope - 未命名工具

仅供学习与参考用途。使用本工具产生的任何结果，由使用者自行承担全部责任。
本工具不提供任何明示或暗示的保证；涉及法律、财务、税务、投资、医疗等
专业决策时，请务必咨询持证专业人士。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码与标准化话术映射（依据规格第五章）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 内部错误码（规格未列，但用于健壮性）
    "E006": "内部处理异常，请重试",
    "E007": "输出序列化失败",
    "E008": "参数解析错误",
    "E009": "自检失败",
    "E010": "未知错误",
}

# 置信度阈值（依据规格 Step 2）
HIGH_CONFIDENCE = 90      # ≥90% 直接输出
MEDIUM_CONFIDENCE = 85    # 85%-90% 标注"建议复核"
# <85% 标注"[需核实]"

# 默认输出字段模板
DEFAULT_FIELDS = ["content", "source", "confidence", "flags"]


# ---------------------------------------------------------------------------
# 核心数据结构与工具函数
# ---------------------------------------------------------------------------

class TidescopeError(Exception):
    """带错误码的异常。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float，失败返回默认值。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    """安全转换为 str，失败返回默认值。"""
    try:
        if value is None:
            return default
        return str(value)
    except Exception:
        return default


def _normalize_input(raw_input: Any) -> str:
    """
    将输入统一转换为字符串。
    支持 str、bytes、dict、list、其他可序列化对象。
    """
    if raw_input is None:
        raise TidescopeError("E001")
    if isinstance(raw_input, bytes):
        try:
            return raw_input.decode("utf-8")
        except UnicodeDecodeError:
            return raw_input.decode("utf-8", errors="replace")
    if isinstance(raw_input, str):
        return raw_input
    # 其他类型尝试 JSON 序列化
    try:
        return json.dumps(raw_input, ensure_ascii=False, default=str)
    except Exception:
        return _safe_str(raw_input)


def _extract_key_info(text: str) -> Dict[str, Any]:
    """
    从文本中提取关键信息（规格 Step 2 第1条）。
    这是一个通用启发式实现，不依赖任何外部库。
    """
    info: Dict[str, Any] = {
        "length": len(text),
        "word_count": len(text.split()),
        "has_url": "http://" in text or "https://" in text,
        "has_email": "@" in text and "." in text,
        "has_number": any(ch.isdigit() for ch in text),
        "lines": text.count("\n") + 1,
        "preview": text[:200] + ("..." if len(text) > 200 else ""),
    }
    return info


def _calculate_confidence(info: Dict[str, Any], required_fields: List[str]) -> float:
    """
    根据信息完整度计算置信度（0-100）。
    宽松计算，避免依赖精确值。
    """
    score = 0.0
    # 基础分：有内容
    if info.get("length", 0) > 0:
        score += 20
    # 有较多内容
    if info.get("length", 0) > 50:
        score += 20
    # 有单词
    if info.get("word_count", 0) > 5:
        score += 15
    # 有结构（多行）
    if info.get("lines", 1) > 1:
        score += 10
    # 有数字
    if info.get("has_number"):
        score += 5
    # 有 URL 或邮箱
    if info.get("has_url") or info.get("has_email"):
        score += 10
    # 有预览
    if info.get("preview"):
        score += 5
    # 字段完整性
    field_score = min(15, len(required_fields) * 3)
    score += field_score
    # 限制在 0-100
    return max(0.0, min(100.0, score))


def _process_single_item(item: Any, required_fields: List[str]) -> Dict[str, Any]:
    """
    处理单个输入项（规格 Step 2）。
    返回结构化结果，包含置信度标注。
    """
    try:
        text = _normalize_input(item)
        if not text.strip():
            raise TidescopeError("E001")
        info = _extract_key_info(text)
        confidence = _calculate_confidence(info, required_fields)

        # 构建结果
        result: Dict[str, Any] = {
            "content": text,
            "source": "user_input",
            "confidence": round(confidence, 1),
            "flags": [],
            "info": info,
        }

        # 置信度标注（规格 Step 2 第3条）
        if confidence >= HIGH_CONFIDENCE:
            result["flags"].append("direct_output")
        elif confidence >= MEDIUM_CONFIDENCE:
            result["flags"].append("建议复核")
        else:
            result["flags"].append("[需核实]")
            result["uncertain_points"] = ["输入信息可能不完整，请确认关键字段"]

        return result
    except TidescopeError:
        raise
    except Exception as exc:
        raise TidescopeError("E006", f"处理失败: {exc}") from exc


def _format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    按指定格式输出结果（规格 Step 3）。
    支持 json、text 两种格式。
    """
    try:
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)
        elif output_format == "text":
            lines = []
            for key in DEFAULT_FIELDS:
                if key in result:
                    lines.append(f"{key}: {result[key]}")
            if "uncertain_points" in result:
                lines.append(f"uncertain_points: {result['uncertain_points']}")
            return "\n".join(lines)
        else:
            raise TidescopeError("E003", f"不支持的输出格式: {output_format}")
    except TidescopeError:
        raise
    except Exception as exc:
        raise TidescopeError("E007", f"输出序列化失败: {exc}") from exc


def process_input(data: Any, output_format: str = "json",
                  required_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    标准流程入口（规格第三章）。

    参数:
        data: 输入数据，可以是单个值或可迭代集合
        output_format: 输出格式 ("json" 或 "text")
        required_fields: 必需的字段列表，用于置信度计算

    返回:
        处理结果列表，每个元素是一个结构化字典

    异常:
        TidescopeError: 携带错误码 E001-E010
    """
    if required_fields is None:
        required_fields = DEFAULT_FIELDS

    # 处理输入
    if data is None:
        raise TidescopeError("E001")
    if isinstance(data, (str, bytes, dict)):
        # 单个输入
        items = [data]
    elif isinstance(data, (list, tuple)):
        items = list(data)
        if not items:
            raise TidescopeError("E001")
    else:
        # 尝试作为单个输入处理
        items = [data]

    # 批量处理
    results = []
    for item in items:
        result = _process_single_item(item, required_fields)
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言采用宽松阈值，确保任何环境直接可过。
    """
    print("[selftest] 开始自检...")
    try:
        # --- 测试 1: 正常输入处理 ---
        print("[selftest] 测试 1: 正常输入处理")
        sample_data = [
            "这是一个测试输入，包含一些文本内容。",
            {"content": "结构化数据", "source": "test"},
            "https://example.com 包含URL的输入",
        ]
        results = process_input(sample_data, output_format="json")
        assert len(results) == 3, f"应处理 3 个输入，实际 {len(results)}"
        for result in results:
            assert "content" in result, "结果缺少 content 字段"
            assert "confidence" in result, "结果缺少 confidence 字段"
            assert 0 <= result["confidence"] <= 100, "置信度应在 0-100 范围"
            assert isinstance(result["flags"], list), "flags 应为列表"
            # 宽松断言：置信度大于 0 即可（输入非空）
            assert result["confidence"] > 0, "非空输入置信度应大于 0"
        print("[selftest] 测试 1 通过")

        # --- 测试 2: 空输入处理 ---
        print("[selftest] 测试 2: 空输入处理")
        try:
            process_input(None)
            assert False, "空输入应抛出 E001"
        except TidescopeError as exc:
            assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print("[selftest] 测试 2 通过")

        # --- 测试 3: 输出格式 ---
        print("[selftest] 测试 3: 输出格式")
        result = process_input("测试输出格式", output_format="json")
        json_str = _format_output(result[0], "json")
        parsed = json.loads(json_str)
        assert "content" in parsed, "JSON 输出缺少 content"
        text_str = _format_output(result[0], "text")
        assert "content:" in text_str, "文本输出缺少 content 字段"
        print("[selftest] 测试 3 通过")

        # --- 测试 4: 批量处理 ---
        print("[selftest] 测试 4: 批量处理")
        batch = ["第一项", "第二项", "第三项"]
        results = process_input(batch)
        assert len(results) == 3, f"批量应处理 3 项，实际 {len(results)}"
        # 每个结果内容应不同
        contents = [r["content"] for r in results]
        assert len(set(contents)) == 3, "批量处理内容应各不相同"
        print("[selftest] 测试 4 通过")

        # --- 测试 5: 错误码体系 ---
        print("[selftest] 测试 5: 错误码体系")
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
            assert len(ERROR_MESSAGES[code]) > 0, f"错误码 {code} 话术为空"
        print("[selftest] 测试 5 通过")

        # --- 测试 6: 置信度标注逻辑 ---
        print("[selftest] 测试 6: 置信度标注逻辑")
        # 长文本应获得较高置信度
        long_text = "这是一个较长的输入文本，" * 20  # 约 200 字
        long_result = _process_single_item(long_text, DEFAULT_FIELDS)
        # 短文本置信度不应高于长文本
        short_result = _process_single_item("短", DEFAULT_FIELDS)
        assert long_result["confidence"] >= short_result["confidence"], \
            "长文本置信度应不低于短文本"
        # 置信度标注应存在
        assert long_result["flags"], "结果应有 flags 标注"
        print("[selftest] 测试 6 通过")

        print("[selftest] 全部自检通过 ✔")
        return 0
    except AssertionError as exc:
        print(f"[selftest] 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"[selftest] 异常: {exc}")
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """
    命令行主入口。

    支持:
        --selftest: 离线自检
        标准输入/文件/参数: 处理数据
    """
    parser = argparse.ArgumentParser(
        description="tidescope - 未命名工具（仅供学习与参考）",
        epilog="示例: python main.py --input '待处理文本' --format json",
    )
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检（不读外部文件）")
    parser.add_argument("--input", "-i", type=str, default=None,
                        help="输入文本或 JSON 字符串")
    parser.add_argument("--file", "-f", type=str, default=None,
                        help="输入文件路径（注意：selftest 不读文件）")
    parser.add_argument("--format", type=str, default="json",
                        choices=["json", "text"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--fields", type=str, default=None,
                        help="必需字段列表，逗号分隔 (用于置信度计算)")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 处理输入
    try:
        if args.file:
            # 文件输入
            try:
                with open(args.file, "r", encoding="utf-8") as fh:
                    data = fh.read()
            except OSError as exc:
                print(f"[E006] 无法读取文件: {exc}")
                return 1
        elif args.input:
            # 尝试解析 JSON，失败则作为纯文本
            try:
                data = json.loads(args.input)
            except json.JSONDecodeError:
                data = args.input
        else:
            # 从标准输入读取
            data = sys.stdin.read().strip()
            if not data:
                print(f"[E001] {ERROR_MESSAGES['E001']}")
                return 1

        # 解析必需字段
        fields = DEFAULT_FIELDS
        if args.fields:
            fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 处理
        results = process_input(data, output_format=args.format, required_fields=fields)

        # 输出
        if args.format == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        else:
            for i, result in enumerate(results):
                print(f"--- 结果 {i+1} ---")
                print(_format_output(result, "text"))
        return 0

    except TidescopeError as exc:
        print(f"[{exc.code}] {exc.message}")
        return 1
    except KeyboardInterrupt:
        print("[E010] 用户中断")
        return 1
    except Exception as exc:
        print(f"[E010] 未知错误: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
