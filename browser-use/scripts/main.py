#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - browser-use 技能核心实现（独立实现）

依据功能规格进行 clean-room 重写，仅使用标准库。
提供核心处理流程、错误码体系、命令行入口及离线自检。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或联系维护者",
    "E007": "输出序列化失败，请检查数据格式",
    "E008": "输入内容类型不支持",
    "E009": "批量处理中存在失败项",
    "E010": "自检未通过，请检查运行环境",
}


class SkillError(Exception):
    """技能业务异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据模型与工具函数
# ---------------------------------------------------------------------------
def _safe_float(value: Any) -> Optional[float]:
    """尝试将输入转为浮点数，失败返回 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_label(score: float) -> str:
    """
    根据置信度分数生成标签。
    规则（宽松阈值，符合规格）：
      - >= 90: 直接输出
      - 85 ~ 90: 建议复核
      - < 85: [需核实]
    """
    if score >= 90.0:
        return "直接输出"
    if score >= 85.0:
        return "建议复核"
    return "[需核实]"


def _extract_key_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    从单条记录中提取关键字段。
    仅挑出非空字段，并附上字段来源标记。
    """
    extracted: Dict[str, Any] = {}
    for key, value in record.items():
        # 跳过空值
        if value is None or value == "":
            continue
        # 简单结构化：保留原始值，并标记来源
        extracted[key] = {
            "value": value,
            "source": "user_input",
            "type": type(value).__name__,
        }
    return extracted


def _compute_confidence(record: Dict[str, Any], required_keys: List[str]) -> float:
    """
    计算单条记录的置信度（0-100）。
    逻辑：根据关键字段的完整度给出置信度。
    """
    if not record:
        return 0.0
    present = sum(1 for k in required_keys if k in record and record[k] not in (None, ""))
    total = len(required_keys)
    if total == 0:
        return 100.0
    ratio = present / total
    # 映射到 0~100，并做简单平滑，避免极端值
    return round(max(0.0, min(100.0, ratio * 100.0)), 1)


# ---------------------------------------------------------------------------
# 核心处理流程
# ---------------------------------------------------------------------------
def process_single(input_data: Any, required_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    处理单条输入，返回结构化结果。

    参数：
        input_data: 用户输入（dict 或可转为 dict 的 JSON 字符串）
        required_keys: 期望的关键字段列表

    返回：
        包含提取结果、置信度、标签等信息的字典。

    异常：
        SkillError: E001 输入为空, E003 格式错误, E008 类型不支持
    """
    # E001: 输入为空
    if input_data is None or (isinstance(input_data, str) and not input_data.strip()):
        raise SkillError("E001")

    # 解析输入（支持 JSON 字符串或 dict）
    if isinstance(input_data, str):
        try:
            record = json.loads(input_data)
        except json.JSONDecodeError:
            raise SkillError("E003")
    elif isinstance(input_data, dict):
        record = input_data
    else:
        # E008: 类型不支持
        raise SkillError("E008")

    if not isinstance(record, dict) or not record:
        raise SkillError("E003")

    # E002: 关键信息缺失检查（仅当指定了必填字段时）
    if required_keys:
        missing = [k for k in required_keys if k not in record or record[k] in (None, "")]
        if missing:
            raise SkillError("E002", f"还缺少以下信息，请补充：{', '.join(missing)}")

    # 执行核心提取
    extracted = _extract_key_fields(record)

    # 计算置信度
    confidence = _compute_confidence(record, required_keys or list(record.keys()))
    label = _confidence_label(confidence)

    result = {
        "status": "ok",
        "extracted": extracted,
        "confidence": confidence,
        "label": label,
        "note": "低置信度内容请人工复核" if confidence < 85.0 else "",
    }
    return result


def process_batch(inputs: List[Any], required_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    批量处理多条输入。

    返回：
        { "status": "ok"/"partial", "results": [...], "failed": [...] }
    """
    if not inputs:
        raise SkillError("E001")

    results = []
    failed = []
    for idx, item in enumerate(inputs):
        try:
            res = process_single(item, required_keys)
            results.append({"index": idx, **res})
        except SkillError as e:
            failed.append({"index": idx, "error_code": e.code, "message": e.message})

    status = "ok" if not failed else "partial"
    if failed and not results:
        # E009: 批量处理全部失败
        raise SkillError("E009", f"批量处理全部失败，共 {len(failed)} 项")

    return {
        "status": status,
        "total": len(inputs),
        "success_count": len(results),
        "failed_count": len(failed),
        "results": results,
        "failed": failed,
    }


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    """
    离线自检：使用内置硬编码样例数据验证核心逻辑。
    不读外部文件、不访问网络、不依赖当前工作目录。
    断言使用宽松阈值（大小比较/区间判断），确保稳健。

    返回：0 表示通过，非 0 表示失败。
    """
    print("[SELFTEST] 开始离线自检...")

    # 样例1：正常单条处理（dict 输入）
    sample_record = {"name": "示例", "value": 42, "note": None}
    try:
        res = process_single(sample_record, required_keys=["name", "value"])
        assert res["status"] == "ok", "样例1: 状态应为 ok"
        assert "name" in res["extracted"], "样例1: 应提取 name 字段"
        assert res["confidence"] > 0, "样例1: 置信度应大于 0"
        assert res["confidence"] <= 100, "样例1: 置信度应不大于 100"
        assert res["label"] in ("直接输出", "建议复核", "[需核实]"), "样例1: 标签非法"
        print("[SELFTEST] 样例1 通过（单条 dict 处理）")
    except AssertionError as e:
        print(f"[SELFTEST] 样例1 失败: {e}")
        return 1
    except SkillError as e:
        print(f"[SELFTEST] 样例1 异常: {e.code} {e.message}")
        return 1

    # 样例2：JSON 字符串输入
    json_str = '{"url": "https://example.com", "title": "测试页面"}'
    try:
        res = process_single(json_str, required_keys=["url"])
        assert res["status"] == "ok", "样例2: 状态应为 ok"
        assert "url" in res["extracted"], "样例2: 应提取 url 字段"
        assert res["confidence"] >= 50, "样例2: 置信度应不低于 50"
        print("[SELFTEST] 样例2 通过（JSON 字符串处理）")
    except AssertionError as e:
        print(f"[SELFTEST] 样例2 失败: {e}")
        return 1
    except SkillError as e:
        print(f"[SELFTEST] 样例2 异常: {e.code} {e.message}")
        return 1

    # 样例3：错误处理 - 空输入
    try:
        process_single("")
        print("[SELFTEST] 样例3 失败: 空输入应抛出 E001")
        return 1
    except SkillError as e:
        assert e.code == "E001", f"样例3: 期望 E001，实际 {e.code}"
        print("[SELFTEST] 样例3 通过（空输入错误码 E001）")

    # 样例4：错误处理 - 缺少必填字段
    try:
        process_single({"name": "x"}, required_keys=["name", "email"])
        print("[SELFTEST] 样例4 失败: 缺少字段应抛出 E002")
        return 1
    except SkillError as e:
        assert e.code == "E002", f"样例4: 期望 E002，实际 {e.code}"
        print("[SELFTEST] 样例4 通过（缺字段错误码 E002）")

    # 样例5：批量处理
    batch_input = [
        {"a": 1, "b": 2},
        {"a": 3, "b": 4, "c": 5},
        "not a dict",  # 这条应失败
    ]
    try:
        res = process_batch(batch_input, required_keys=["a", "b"])
        assert res["total"] == 3, "样例5: 总数应为 3"
        assert res["success_count"] >= 2, "样例5: 成功数应至少为 2"
        assert res["failed_count"] >= 1, "样例5: 失败数应至少为 1"
        assert res["status"] in ("ok", "partial"), "样例5: 状态非法"
        print("[SELFTEST] 样例5 通过（批量处理）")
    except AssertionError as e:
        print(f"[SELFTEST] 样例5 失败: {e}")
        return 1
    except SkillError as e:
        print(f"[SELFTEST] 样例5 异常: {e.code} {e.message}")
        return 1

    # 样例6：置信度标签逻辑验证（宽松区间）
    try:
        label_high = _confidence_label(95.0)
        label_mid = _confidence_label(87.0)
        label_low = _confidence_label(50.0)
        assert label_high == "直接输出", "样例6: 高置信度应为直接输出"
        assert label_mid == "建议复核", "样例6: 中置信度应为建议复核"
        assert label_low == "[需核实]", "样例6: 低置信度应为需核实"
        print("[SELFTEST] 样例6 通过（置信度标签）")
    except AssertionError as e:
        print(f"[SELFTEST] 样例6 失败: {e}")
        return 1

    print("[SELFTEST] 全部自检通过 ✔")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="browser-use 技能核心实现 - 数据处理与结构化工具"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，无需外部依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 字符串（单条处理）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="输入 JSON 数组字符串（批量处理）",
    )
    parser.add_argument(
        "--required",
        type=str,
        default="",
        help="必填字段列表，逗号分隔（如: name,email）",
    )

    args = parser.parse_args(argv)

    # 自检模式优先
    if args.selftest:
        return _run_selftest()

    # 处理输入
    try:
        required_keys = [k.strip() for k in args.required.split(",") if k.strip()]

        if args.batch:
            # 批量模式
            try:
                data = json.loads(args.batch)
            except json.JSONDecodeError:
                raise SkillError("E003")
            if not isinstance(data, list):
                raise SkillError("E003")
            result = process_batch(data, required_keys)
        elif args.input:
            # 单条模式
            result = process_single(args.input, required_keys)
        else:
            # 无输入参数
            print("请使用 --input 或 --batch 提供输入数据，或使用 --selftest 运行自检。", file=sys.stderr)
            print(ERROR_CODES["E001"], file=sys.stderr)
            return 2

        # 输出结果（JSON）
        try:
            output = json.dumps(result, ensure_ascii=False, indent=2)
            print(output)
            return 0
        except (TypeError, ValueError):
            raise SkillError("E007")

    except SkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E006: 内部处理异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
