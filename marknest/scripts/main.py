#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
marknest - PDF转文档 技能实现脚本
=================================
依据功能规格独立实现的命令行工具，提供：
- 输入解析与结构化
- 置信度评估与标注
- 批量处理
- 离线自检（--selftest）

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 输出目录不可写
    E007 批量输入为空
    E008 单条输入格式错误
    E009 自检失败
    E010 未知错误
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------- 工具函数 ----------

def _build_error(code: str, message: str) -> Dict[str, str]:
    """构造标准错误结构。"""
    return {"error_code": code, "message": message}


def _confidence_label(confidence: float) -> str:
    """根据置信度返回标注。"""
    if confidence >= 90.0:
        return "直接输出"
    elif confidence >= 85.0:
        return "建议复核"
    else:
        return "[需核实]"


def _extract_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段。
    识别规则：
      - 形如 "key: value" 或 "key=value" 的行作为字段
      - 其余内容作为正文
    """
    fields: Dict[str, Any] = {}
    body_lines: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # 尝试解析 key: value 或 key=value
        field_found = False
        for sep in (":", "="):
            if sep in stripped:
                key, _, value = stripped.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    fields[key] = value
                    field_found = True
                    break
        if not field_found:
            body_lines.append(stripped)

    fields["_body"] = "\n".join(body_lines)
    return fields


def _evaluate_confidence(fields: Dict[str, Any], required_keys: List[str]) -> float:
    """
    简单置信度评估：
      - 基础 50 分
      - 每个存在的必需字段 +10 分
      - 正文非空 +20 分
      - 字段数量超过 3 个 +10 分
    上限 100。
    """
    score = 50.0
    present = [k for k in required_keys if k in fields and fields[k]]
    score += len(present) * 10.0
    if fields.get("_body", "").strip():
        score += 20.0
    if len([k for k in fields if not k.startswith("_")]) > 3:
        score += 10.0
    return min(100.0, score)


def _process_single(input_text: str, required_keys: List[str]) -> Dict[str, Any]:
    """
    处理单条输入，返回结构化结果。
    错误码：E001（空输入）、E002（关键信息缺失）、E005（置信度过低）
    """
    if not input_text or not input_text.strip():
        return _build_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    fields = _extract_fields(input_text)
    confidence = _evaluate_confidence(fields, required_keys)

    result: Dict[str, Any] = {
        "fields": {k: v for k, v in fields.items() if not k.startswith("_")},
        "body": fields.get("_body", ""),
        "confidence": round(confidence, 1),
        "confidence_label": _confidence_label(confidence),
    }

    # 检查必需字段
    missing = [k for k in required_keys if k not in result["fields"]]
    if missing:
        result["error_code"] = "E002"
        result["message"] = f"还缺少以下信息，请补充：{', '.join(missing)}"
        return result

    # 置信度过低检查
    if confidence < 85.0:
        result["error_code"] = "E005"
        result["message"] = "结果无法确定，建议：请补充更多关键信息或核对输入内容"
        return result

    result["status"] = "ok"
    return result


def _batch_process(inputs: List[str], required_keys: List[str]) -> Dict[str, Any]:
    """
    批量处理多条输入。
    错误码：E007（批量输入为空）、E008（单条输入格式错误）
    """
    if not inputs:
        return _build_error("E007", "批量输入不能为空，请提供至少一条待处理内容")

    results = []
    for idx, item in enumerate(inputs):
        if not isinstance(item, str) or not item.strip():
            results.append({
                "index": idx,
                **(_build_error("E008", f"第 {idx + 1} 条输入格式错误，应为非空字符串"))
            })
            continue
        processed = _process_single(item, required_keys)
        processed["index"] = idx
        results.append(processed)

    # 统计成功/失败
    success_count = sum(1 for r in results if r.get("status") == "ok")
    return {
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count,
        "results": results,
    }


def _save_output(data: Dict[str, Any], output_path: str) -> None:
    """将结果保存为 JSON 文件。错误码：E006（目录不可写）"""
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError:
            raise OSError("E006: 输出目录不可写")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- 自检函数 ----------

def _run_selftest() -> int:
    """
    离线自检核心逻辑，使用内置硬编码数据。
    返回 0 表示通过，非 0 表示失败。
    """
    test_cases = [
        # (输入, 必需字段, 期望状态)
        ("标题: 测试文档\n作者: Alice\n内容: 这是一个测试", ["标题", "作者"], "ok"),
        ("标题: 不完整文档", ["标题", "作者"], "E002"),
        ("", ["标题"], "E001"),
        ("随便一段没有结构化字段的文本，但比较长，用来测试置信度是否足够高。"
         "这里继续补充一些内容，让文本量更多一些。", [], "ok"),
    ]

    try:
        # 测试1: 正常处理
        for input_text, required, expected_status in test_cases:
            result = _process_single(input_text, required)
            if expected_status == "ok":
                assert result.get("status") == "ok", f"期望成功但失败: {result}"
                assert result.get("confidence", 0) >= 85.0, "高置信度输入应>=85"
            else:
                assert result.get("error_code") == expected_status, \
                    f"期望错误码 {expected_status}，实际 {result.get('error_code')}"

        # 测试2: 置信度标注
        low_conf = _process_single("只有一点点内容", ["必需字段A", "必需字段B", "必需字段C"])
        assert low_conf.get("error_code") == "E002", "缺少必需字段应报 E002"

        # 测试3: 批量处理
        batch_result = _batch_process(
            ["标题: 文档1\n作者: Bob", "标题: 文档2\n作者: Carol"],
            ["标题", "作者"]
        )
        assert batch_result.get("total") == 2, "批量应处理2条"
        assert batch_result.get("success_count") == 2, "两条都应成功"

        # 测试4: 批量空输入
        empty_batch = _batch_process([], ["标题"])
        assert empty_batch.get("error_code") == "E007", "空批量应报 E007"

        # 测试5: 置信度标签
        assert _confidence_label(95.0) == "直接输出"
        assert _confidence_label(87.0) == "建议复核"
        assert _confidence_label(80.0) == "[需核实]"

        # 测试6: 字段提取
        fields = _extract_fields("名称: 测试\n值=123\n正文内容")
        assert fields.get("名称") == "测试", "冒号分隔应正确解析"
        assert fields.get("值") == "123", "等号分隔应正确解析"
        assert "正文内容" in fields.get("_body", ""), "非字段行应进入正文"

        print("[selftest] 全部断言通过 ✅")
        return 0

    except AssertionError as e:
        print(f"[selftest] 失败: {e} ❌")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[selftest] 异常: {e} ❌")
        return 1


# ---------- 主流程 ----------

def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="marknest - PDF转文档 技能实现",
        epilog="示例: python main.py --input '标题: 报告\n作者: 张三' --required 标题 作者"
    )
    parser.add_argument("--input", "-i", type=str, default=None,
                        help="单条输入文本")
    parser.add_argument("--batch", "-b", type=str, default=None,
                        help="批量输入 JSON 数组字符串，如 '[{\"text\":\"...\"}]'")
    parser.add_argument("--required", "-r", nargs="*", default=[],
                        help="必需字段名列表")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="输出 JSON 文件路径")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检并退出")
    return parser.parse_args()


def _main() -> int:
    """主入口。返回进程退出码。"""
    args = _parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 标准处理模式
    try:
        # 单条处理
        if args.input:
            result = _process_single(args.input, args.required)
            if result.get("status") != "ok":
                # 输出错误信息
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if args.output:
                _save_output(result, args.output)
            return 0

        # 批量处理
        if args.batch:
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    raise ValueError("批量输入应为数组")
                inputs = [item.get("text", "") if isinstance(item, dict) else str(item)
                          for item in batch_data]
            except (json.JSONDecodeError, ValueError):
                print(json.dumps(_build_error("E003", "输入格式错误，批量输入应为 JSON 数组"),
                                 ensure_ascii=False))
                return 1

            result = _batch_process(inputs, args.required)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if args.output:
                _save_output(result, args.output)
            return 0 if result.get("failed_count", 0) == 0 else 1

        # 无有效输入
        print(json.dumps(_build_error("E001", "请提供待处理的内容"),
                         ensure_ascii=False))
        return 1

    except OSError as e:
        if str(e).startswith("E006"):
            print(json.dumps(_build_error("E006", "输出目录不可写"), ensure_ascii=False))
        else:
            print(json.dumps(_build_error("E010", f"系统错误: {e}"), ensure_ascii=False))
        return 1
    except Exception as e:  # noqa: BLE001
        print(json.dumps(_build_error("E010", f"未知错误: {e}"), ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(_main())
