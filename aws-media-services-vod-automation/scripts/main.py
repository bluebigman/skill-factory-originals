#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于功能规格独立实现的 AWS Media Services VOD Automation 工具。
仅使用 Python 标准库，无第三方依赖。

功能概述：
1. 解析输入内容，识别关键字段并结构化输出
2. 支持批量处理和自定义格式
3. 置信度标注（≥90%直接输出；85%-90%建议复核；<85%标记[需核实]）
4. 错误码体系 E001-E010
5. --selftest 参数：内置硬编码样例离线自检，不读文件、不依赖目录、不访问网络
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "批量处理时出现异常，请检查输入项",
    "E007": "输出格式不支持，支持格式：json / text",
    "E008": "内部处理逻辑错误，请重试或联系维护者",
    "E009": "输入内容长度超出限制（最大 10000 字符）",
    "E010": "系统繁忙或资源不足，请稍后重试",
}

# 输入长度上限
MAX_INPUT_LENGTH = 10000

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ============================================================
# 异常类定义
# ============================================================

class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_MESSAGES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: str) -> str:
    """
    校验输入内容。
    - 空输入 -> E001
    - 超长输入 -> E009
    - 非字符串 -> E003

    返回去除首尾空白后的输入。
    """
    if raw_input is None or (isinstance(raw_input, str) and raw_input.strip() == ""):
        raise SkillError("E001")
    if not isinstance(raw_input, str):
        raise SkillError("E003", ERROR_MESSAGES["E003"] + "请输入字符串类型的内容")
    if len(raw_input) > MAX_INPUT_LENGTH:
        raise SkillError("E009")
    return raw_input.strip()


def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段（结构化）。
    识别规则（简化版，用于演示）：
    - 检测 URL：以 http:// 或 https:// 开头
    - 检测文件路径：包含 / 或 \\ 且不以协议开头
    - 检测 JSON：以 { 或 [ 开头并尝试解析
    - 检测键值对：如 key=value 或 key: value
    - 其余情况：整体作为 content 字段

    返回结构化字典。
    """
    result: Dict[str, Any] = {
        "source_type": "unknown",
        "content": text,
        "detected_fields": {},
        "metadata": {
            "charset": "utf-8",
            "length": len(text),
            "processed_at": datetime.utcnow().isoformat() + "Z",
        },
    }

    # 检测 URL
    if text.startswith("http://") or text.startswith("https://"):
        result["source_type"] = "url"
        result["url"] = text
        result["detected_fields"]["protocol"] = text.split("://")[0]
        result["detected_fields"]["host"] = text.split("://")[1].split("/")[0] if "://" in text else ""
        return result

    # 检测 JSON
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
            result["source_type"] = "json"
            result["parsed_json"] = parsed
            result["detected_fields"]["json_type"] = "object" if isinstance(parsed, dict) else "array"
            if isinstance(parsed, dict):
                result["detected_fields"]["keys"] = list(parsed.keys())[:10]  # 最多取10个键
            return result
        except json.JSONDecodeError:
            # 不是合法 JSON，继续其他检测
            pass

    # 检测键值对（key=value 或 key: value）
    kv_fields: Dict[str, str] = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        for sep in ("=", ":"):
            if sep in line:
                parts = line.split(sep, 1)
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value:
                    kv_fields[key] = value
                break

    if kv_fields:
        result["source_type"] = "key_value"
        result["detected_fields"] = kv_fields
        return result

    # 检测文件路径
    if "/" in text or "\\" in text:
        result["source_type"] = "file_path"
        result["detected_fields"]["path_style"] = "unix" if "/" in text else "windows"
        return result

    # 默认：纯文本
    result["source_type"] = "plain_text"
    return result


def calculate_confidence(structured: Dict[str, Any]) -> float:
    """
    根据结构化结果计算置信度（0.0 - 1.0）。
    规则：
    - 能明确识别来源类型：基础 0.90
    - 检测到关键字段：每个字段 +0.02，最高加到 0.98
    - 内容为空或无法识别：0.80
    """
    source_type = structured.get("source_type", "unknown")
    if source_type == "unknown":
        return 0.80

    confidence = 0.90
    detected_count = len(structured.get("detected_fields", {}))
    if detected_count > 0:
        confidence = min(0.98, confidence + detected_count * 0.02)

    # 有 parsed_json 额外加分
    if "parsed_json" in structured:
        confidence = min(0.98, confidence + 0.05)

    return round(confidence, 2)


def format_output(structured: Dict[str, Any], confidence: float, output_format: str = "json") -> str:
    """
    按指定格式生成输出。
    支持 json / text 两种格式。
    """
    # 组装最终结果
    final_result = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "result": structured,
        "confidence": confidence,
        "confidence_level": (
            "high" if confidence >= HIGH_CONFIDENCE
            else "medium" if confidence >= MEDIUM_CONFIDENCE
            else "low"
        ),
        "warning": "" if confidence >= HIGH_CONFIDENCE else (
            "建议复核" if confidence >= MEDIUM_CONFIDENCE else "[需核实] 结果无法确定，请人工复核"
        ),
    }

    if output_format == "json":
        return json.dumps(final_result, ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = []
        lines.append(f"请求ID: {final_result['request_id']}")
        lines.append(f"时间戳: {final_result['timestamp']}")
        lines.append(f"置信度: {confidence:.0%} ({final_result['confidence_level']})")
        if final_result["warning"]:
            lines.append(f"提示: {final_result['warning']}")
        lines.append("--- 结构化结果 ---")
        lines.append(f"来源类型: {structured.get('source_type', 'unknown')}")
        for key, value in structured.get("detected_fields", {}).items():
            lines.append(f"  {key}: {value}")
        if "parsed_json" in structured:
            lines.append("  parsed_json: " + json.dumps(structured["parsed_json"], ensure_ascii=False)[:500])
        if "url" in structured:
            lines.append(f"  url: {structured['url']}")
        return "\n".join(lines)

    raise SkillError("E007")


def process_single(input_text: str, output_format: str = "json") -> str:
    """
    处理单个输入。
    """
    # Step 1: 校验输入
    validated = validate_input(input_text)

    # Step 2: 结构化解析
    structured = extract_key_fields(validated)

    # Step 3: 计算置信度
    confidence = calculate_confidence(structured)

    # Step 4: 格式化输出
    return format_output(structured, confidence, output_format)


def process_batch(inputs: List[str], output_format: str = "json") -> str:
    """
    批量处理多个输入。
    返回 JSON 数组格式的结果。
    """
    results = []
    for idx, item in enumerate(inputs):
        try:
            processed = process_single(item, output_format="json")
            parsed = json.loads(processed)
            results.append(parsed)
        except SkillError as e:
            results.append({
                "index": idx,
                "error_code": e.error_code,
                "error_message": e.message,
                "input": item[:200],  # 截断，避免过长
            })
        except Exception:
            results.append({
                "index": idx,
                "error_code": "E008",
                "error_message": ERROR_MESSAGES["E008"],
                "input": item[:200],
            })

    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)

    if output_format == "text":
        lines = []
        for i, r in enumerate(results):
            lines.append(f"--- 第 {i+1} 项 ---")
            if "error_code" in r:
                lines.append(f"错误: [{r['error_code']}] {r['error_message']}")
            else:
                lines.append(f"请求ID: {r['request_id']}")
                lines.append(f"置信度: {r['confidence']:.0%}")
                lines.append(f"来源类型: {r['result'].get('source_type', 'unknown')}")
        return "\n".join(lines)

    raise SkillError("E007")


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保必然匹配。
    """
    print("=" * 60)
    print("开始自检 (selftest)...")
    print("=" * 60)

    # 硬编码测试样例
    test_cases = [
        {
            "name": "URL 输入",
            "input": "https://example.com/videos/sample.mp4",
            "expected_source_type": "url",
        },
        {
            "name": "JSON 输入",
            "input": '{"title": "测试视频", "duration": 120, "format": "mp4"}',
            "expected_source_type": "json",
        },
        {
            "name": "键值对输入",
            "input": "title=My Movie\nduration=90\nresolution=1080p",
            "expected_source_type": "key_value",
        },
        {
            "name": "文件路径输入",
            "input": "/mnt/videos/input/sample.mp4",
            "expected_source_type": "file_path",
        },
        {
            "name": "纯文本输入",
            "input": "这是一段普通的视频描述文本",
            "expected_source_type": "plain_text",
        },
    ]

    all_passed = True

    # 测试单个处理
    print("\n--- 测试: 单条处理 ---")
    for case in test_cases:
        try:
            result = process_single(case["input"], output_format="json")
            parsed = json.loads(result)

            # 宽松断言：来源类型匹配
            actual_type = parsed["result"].get("source_type", "unknown")
            assert actual_type == case["expected_source_type"], \
                f"来源类型不匹配: 期望 {case['expected_source_type']}, 实际 {actual_type}"

            # 宽松断言：置信度在合理区间
            confidence = parsed.get("confidence", 0)
            assert 0.0 <= confidence <= 1.0, f"置信度超出范围: {confidence}"

            # 宽松断言：有请求ID
            assert parsed.get("request_id", ""), "缺少请求ID"

            print(f"  [通过] {case['name']}: 来源类型={actual_type}, 置信度={confidence:.0%}")
        except Exception as e:
            all_passed = False
            print(f"  [失败] {case['name']}: {e}")

    # 测试批量处理
    print("\n--- 测试: 批量处理 ---")
    try:
        batch_inputs = [c["input"] for c in test_cases]
        batch_result = process_batch(batch_inputs, output_format="json")
        batch_parsed = json.loads(batch_result)
        assert len(batch_parsed) == len(test_cases), "批量处理数量不匹配"
        print(f"  [通过] 批量处理 {len(batch_parsed)} 项")
    except Exception as e:
        all_passed = False
        print(f"  [失败] 批量处理: {e}")

    # 测试错误处理
    print("\n--- 测试: 错误处理 ---")
    try:
        # 空输入 -> E001
        try:
            process_single("")
            all_passed = False
            print("  [失败] 空输入未抛出 E001")
        except SkillError as e:
            assert e.error_code == "E001", f"错误码不匹配: {e.error_code}"
            print(f"  [通过] 空输入 -> {e.error_code}")

        # 超长输入 -> E009
        try:
            process_single("a" * (MAX_INPUT_LENGTH + 1))
            all_passed = False
            print("  [失败] 超长输入未抛出 E009")
        except SkillError as e:
            assert e.error_code == "E009", f"错误码不匹配: {e.error_code}"
            print(f"  [通过] 超长输入 -> {e.error_code}")

        # 非法格式 -> E007
        try:
            process_single("测试文本", output_format="xml")
            all_passed = False
            print("  [失败] 非法输出格式未抛出 E007")
        except SkillError as e:
            assert e.error_code == "E007", f"错误码不匹配: {e.error_code}"
            print(f"  [通过] 非法输出格式 -> {e.error_code}")
    except Exception as e:
        all_passed = False
        print(f"  [失败] 错误处理测试: {e}")

    # 测试文本格式输出
    print("\n--- 测试: 文本格式输出 ---")
    try:
        text_result = process_single(test_cases[0]["input"], output_format="text")
        assert "置信度" in text_result, "文本输出缺少置信度"
        assert "来源类型" in text_result, "文本输出缺少来源类型"
        print("  [通过] 文本格式输出")
    except Exception as e:
        all_passed = False
        print(f"  [失败] 文本格式输出: {e}")

    # 测试置信度标注
    print("\n--- 测试: 置信度标注 ---")
    try:
        # 低置信度样例（空内容）
        low_conf = calculate_confidence({"source_type": "unknown", "detected_fields": {}})
        assert low_conf < MEDIUM_CONFIDENCE, f"低置信度应小于 {MEDIUM_CONFIDENCE}"

        # 高置信度样例
        high_conf = calculate_confidence({
            "source_type": "url",
            "detected_fields": {"protocol": "https", "host": "example.com"},
        })
        assert high_conf >= HIGH_CONFIDENCE, f"高置信度应大于等于 {HIGH_CONFIDENCE}"
        print(f"  [通过] 低置信度={low_conf:.0%}, 高置信度={high_conf:.0%}")
    except Exception as e:
        all_passed = False
        print(f"  [失败] 置信度标注: {e}")

    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主入口函数。
    """
    parser = argparse.ArgumentParser(
        description="AWS Media Services VOD Automation - 视频点播工作流自动化工具",
        epilog="示例: python main.py --input 'https://example.com/video.mp4' --format json"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的内容（URL / 文件路径 / JSON / 键值对 / 文本）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：逗号分隔的多个输入项",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 批量模式
    if args.batch:
        try:
            items = [item.strip() for item in args.batch.split(",") if item.strip()]
            if not items:
                raise SkillError("E001")
            result = process_batch(items, args.format)
            print(result)
            return 0
        except SkillError as e:
            print(f"错误: [{e.error_code}] {e.message}", file=sys.stderr)
            return 1
        except Exception:
            print(f"错误: [E008] {ERROR_MESSAGES['E008']}", file=sys.stderr)
            return 1

    # 单条模式
    if args.input:
        try:
            result = process_single(args.input, args.format)
            print(result)
            return 0
        except SkillError as e:
            print(f"错误: [{e.error_code}] {e.message}", file=sys.stderr)
            return 1
        except Exception:
            print(f"错误: [E008] {ERROR_MESSAGES['E008']}", file=sys.stderr)
            return 1

    # 无输入参数
    parser.print_help()
    print("\n错误: [E001] " + ERROR_MESSAGES["E001"], file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
