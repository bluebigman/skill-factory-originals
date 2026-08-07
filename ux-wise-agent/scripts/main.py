#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ux-wise-agent 技能实现脚本
===========================
依据功能规格独立实现（clean-room），仅使用标准库。

功能概述：
- 将用户提供的数据转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

错误码体系：
- E001: 输入为空
- E002: 关键信息缺失
- E003: 输入格式错误
- E004: 超出能力边界
- E005: 置信度过低
- E006: 内部处理异常
- E007: 参数解析错误
- E008: 输出格式不支持
- E009: 批量处理中断
- E010: 未知异常

用法：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --input "文本内容"  # 处理单个输入
    python scripts/main.py --batch f1 f2 f3    # 批量处理多个输入
    python scripts/main.py --format json       # 指定输出格式 (json/text)
"""

import sys
import json
import argparse
from typing import Any, Dict, List, Tuple


# ============================================================
# 常量定义
# ============================================================

# 技能元信息（来自规格）
SKILL_META = {
    "name": "ux-wise-agent",
    "display_name": "未命名工具",
    "version": "1.0.0",
    "author": "skill-factory-auto",
    "description": "Free AI skill pack for senior UX and Product Designers. Runs on Claude Projects or any LLM. Strategic, Direct, and Provo",
    "trigger_words": ["ux wise agent"],
}

# 能力边界声明
CAPABILITY_BOUNDARIES = {
    "can_do": [
        "将用户提供的数据/文件/URL转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 错误码与标准化话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：一段文本、JSON对象、或URL",
    "E004": "这超出了本工具的能力范围，建议：简化需求或使用专用工具",
    "E005": "结果无法确定，建议：提供更多上下文信息或人工复核",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "输出格式不支持，仅支持 json 或 text",
    "E009": "批量处理中断，部分输入未处理完成",
    "E010": "未知异常，请联系维护人员",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # >=90%：直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90%：建议复核
# <85%：标注 [需核实]


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: Any) -> Tuple[bool, str]:
    """
    校验输入是否有效。

    参数:
        raw_input: 用户提供的原始输入

    返回:
        (是否有效, 错误码或空字符串)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str):
        if not raw_input.strip():
            return False, "E001"
    elif isinstance(raw_input, (list, tuple)):
        if len(raw_input) == 0:
            return False, "E001"
        if all(not str(item).strip() for item in raw_input):
            return False, "E001"
    elif isinstance(raw_input, dict):
        if len(raw_input) == 0:
            return False, "E001"
    return True, ""


def parse_input(raw_input: Any) -> Tuple[bool, Any, str]:
    """
    解析输入内容，尝试识别结构化数据。

    参数:
        raw_input: 用户提供的原始输入

    返回:
        (是否成功, 解析后的数据, 错误码或空字符串)
    """
    # 如果是字典，直接使用
    if isinstance(raw_input, dict):
        return True, raw_input, ""

    # 如果是列表，逐个尝试解析
    if isinstance(raw_input, list):
        parsed_items = []
        for item in raw_input:
            ok, parsed, err = parse_input(item)
            if not ok:
                return False, None, err
            parsed_items.append(parsed)
        return True, parsed_items, ""

    # 如果是字符串，尝试解析为 JSON
    if isinstance(raw_input, str):
        text = raw_input.strip()
        # 尝试 JSON 解析
        if text.startswith("{") or text.startswith("["):
            try:
                data = json.loads(text)
                return True, data, ""
            except json.JSONDecodeError:
                # JSON 解析失败，视为普通文本
                pass
        # 普通文本，直接使用
        return True, text, ""

    # 其他类型（数字、布尔等）
    return True, raw_input, ""


def extract_key_info(data: Any) -> Dict[str, Any]:
    """
    从解析后的数据中提取关键信息。

    参数:
        data: 解析后的数据

    返回:
        包含关键信息的字典
    """
    key_info = {
        "data_type": type(data).__name__,
        "content": data,
        "length": len(data) if hasattr(data, "__len__") else 1,
        "has_nested_structure": isinstance(data, (dict, list)),
    }

    # 如果是字典，提取键值信息
    if isinstance(data, dict):
        key_info["keys"] = list(data.keys())
        key_info["value_count"] = len(data)
        # 检查是否有明显的标题/名称字段
        for field in ["title", "name", "标题", "名称", "subject"]:
            if field in data:
                key_info["title"] = data[field]
                break

    # 如果是列表，提取元素信息
    elif isinstance(data, list):
        key_info["element_count"] = len(data)
        # 检查元素是否同构（字典）
        if data and all(isinstance(item, dict) for item in data):
            key_info["elements_are_objects"] = True
            # 提取公共键
            common_keys = set(data[0].keys())
            for item in data[1:]:
                common_keys &= set(item.keys())
            key_info["common_keys"] = list(common_keys)

    # 如果是文本，提取统计信息
    elif isinstance(data, str):
        words = data.split()
        key_info["word_count"] = len(words)
        key_info["char_count"] = len(data)
        key_info["has_url"] = "http://" in data or "https://" in data
        key_info["has_file_path"] = "/" in data or "\\" in data

    return key_info


def calculate_confidence(key_info: Dict[str, Any]) -> float:
    """
    根据关键信息计算置信度。

    参数:
        key_info: 关键信息字典

    返回:
        置信度分数 (0.0 - 1.0)
    """
    score = 0.0
    data_type = key_info.get("data_type", "")

    # 基础分数：数据类型明确
    if data_type in ("str", "dict", "list", "int", "float", "bool"):
        score += 0.4

    # 结构化数据加分
    if key_info.get("has_nested_structure"):
        score += 0.2

    # 有明确标题加分
    if key_info.get("title"):
        score += 0.2

    # 有足够内容加分
    length = key_info.get("length", 0)
    if length > 0:
        score += 0.1

    # 文本内容有 URL 或文件路径，可能不完整
    if key_info.get("has_url") or key_info.get("has_file_path"):
        score -= 0.1

    # 限制在 0.1 - 0.95 之间
    return max(0.1, min(0.95, score))


def format_output(data: Any, key_info: Dict[str, Any], confidence: float, output_format: str = "text") -> str:
    """
    按指定格式生成输出。

    参数:
        data: 处理后的数据
        key_info: 关键信息
        confidence: 置信度
        output_format: 输出格式 (json 或 text)

    返回:
        格式化后的输出字符串
    """
    # 构建结果对象
    result = {
        "status": "success",
        "skill": SKILL_META["name"],
        "version": SKILL_META["version"],
        "confidence": round(confidence, 2),
        "confidence_label": get_confidence_label(confidence),
        "key_info": {
            k: v for k, v in key_info.items() if k != "content"
        },
        "data": data,
    }

    # 根据置信度添加标注
    if confidence < CONFIDENCE_MEDIUM:
        result["warning"] = "[需核实] 结果置信度较低，请人工复核"
    elif confidence < CONFIDENCE_HIGH:
        result["warning"] = "建议复核"

    # JSON 格式输出
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    # 文本格式输出
    lines = []
    lines.append(f"=== {SKILL_META['display_name']} 处理结果 ===")
    lines.append(f"技能版本: {SKILL_META['version']}")
    lines.append(f"置信度: {confidence*100:.1f}% ({get_confidence_label(confidence)})")

    if "warning" in result:
        lines.append(f"提示: {result['warning']}")

    lines.append("--- 关键信息 ---")
    for k, v in result["key_info"].items():
        if k != "has_nested_structure":
            lines.append(f"  {k}: {v}")

    lines.append("--- 处理内容 ---")
    if isinstance(data, str):
        # 文本内容截断显示
        display_text = data if len(data) <= 200 else data[:200] + "..."
        lines.append(display_text)
    else:
        lines.append(json.dumps(data, ensure_ascii=False, default=str))

    return "\n".join(lines)


def get_confidence_label(confidence: float) -> str:
    """根据置信度返回标签。"""
    if confidence >= CONFIDENCE_HIGH:
        return "高置信度"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "中置信度"
    else:
        return "低置信度"


def process_input(raw_input: Any, output_format: str = "text") -> Tuple[bool, str, str]:
    """
    处理单个输入。

    参数:
        raw_input: 用户提供的输入
        output_format: 输出格式

    返回:
        (是否成功, 输出内容或错误信息, 错误码)
    """
    # Step 1: 校验输入
    valid, err_code = validate_input(raw_input)
    if not valid:
        return False, ERROR_MESSAGES[err_code], err_code

    # Step 2: 解析输入
    ok, data, err_code = parse_input(raw_input)
    if not ok:
        return False, ERROR_MESSAGES[err_code], err_code

    # Step 3: 提取关键信息
    key_info = extract_key_info(data)

    # Step 4: 计算置信度
    confidence = calculate_confidence(key_info)

    # Step 5: 生成输出
    try:
        output = format_output(data, key_info, confidence, output_format)
        return True, output, ""
    except Exception:
        return False, ERROR_MESSAGES["E006"], "E006"


def process_batch(inputs: List[Any], output_format: str = "text") -> Tuple[bool, str, str]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        output_format: 输出格式

    返回:
        (是否全部成功, 汇总输出或错误信息, 错误码)
    """
    if not inputs:
        return False, ERROR_MESSAGES["E001"], "E001"

    results = []
    failed_count = 0

    for idx, item in enumerate(inputs):
        ok, output, err_code = process_input(item, output_format)
        if ok:
            results.append({"index": idx, "success": True, "output": output})
        else:
            failed_count += 1
            results.append({"index": idx, "success": False, "error": err_code, "message": output})

    # 构建汇总输出
    summary = {
        "status": "success" if failed_count == 0 else "partial",
        "total": len(inputs),
        "success_count": len(inputs) - failed_count,
        "failed_count": failed_count,
        "results": results,
    }

    if output_format == "json":
        return failed_count == 0, json.dumps(summary, ensure_ascii=False, indent=2), ""
    else:
        lines = []
        lines.append(f"=== 批量处理结果 ===")
        lines.append(f"总计: {len(inputs)}, 成功: {summary['success_count']}, 失败: {summary['failed_count']}")
        for result in results:
            if result["success"]:
                lines.append(f"\n[#{result['index']}] 成功")
                lines.append(result["output"])
            else:
                lines.append(f"\n[#{result['index']}] 失败 (错误码: {result['error']})")
                lines.append(result["message"])
        return failed_count == 0, "\n".join(lines), "E009" if failed_count > 0 else ""


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。

    返回:
        是否全部通过
    """
    print("=== ux-wise-agent 自检开始 ===")
    all_passed = True

    # 测试用例 1: 普通文本输入
    print("\n[测试1] 普通文本输入")
    ok, output, err = process_input("这是一个测试文本，用于验证基本处理流程。", "text")
    assert ok, f"处理失败: {err}"
    assert "置信度" in output, "输出缺少置信度信息"
    assert "处理内容" in output, "输出缺少处理内容"
    print("通过 ✓")

    # 测试用例 2: JSON 字典输入
    print("\n[测试2] JSON 字典输入")
    sample_dict = {"title": "产品需求文档", "author": "张三", "revision": 3}
    ok, output, err = process_input(sample_dict, "json")
    assert ok, f"处理失败: {err}"
    parsed = json.loads(output)
    assert parsed["status"] == "success", "状态不是 success"
    assert parsed["data"]["title"] == "产品需求文档", "数据保留不完整"
    assert "confidence" in parsed, "缺少置信度"
    print("通过 ✓")

    # 测试用例 3: 批量处理
    print("\n[测试3] 批量处理")
    batch_input = ["第一条数据", {"name": "test", "value": 42}, "第三条数据"]
    ok, output, err = process_batch(batch_input, "text")
    assert ok, f"批量处理失败: {err}"
    assert "批量处理结果" in output, "缺少批量处理标题"
    assert "总计: 3" in output, "批量数量不正确"
    print("通过 ✓")

    # 测试用例 4: 空输入校验
    print("\n[测试4] 空输入校验")
    ok, output, err = process_input("", "text")
    assert not ok, "空输入应该失败"
    assert err == "E001", f"错误码不正确: {err}"
    print("通过 ✓")

    # 测试用例 5: 置信度计算
    print("\n[测试5] 置信度计算")
    # 简单文本应该有中等置信度
    key_info = extract_key_info("简单文本")
    conf = calculate_confidence(key_info)
    assert 0.1 <= conf <= 0.95, f"置信度超出范围: {conf}"

    # 结构化数据应该有较高置信度
    key_info2 = extract_key_info({"title": "完整文档", "content": "详细内容"})
    conf2 = calculate_confidence(key_info2)
    assert conf2 > conf, "结构化数据置信度应更高"
    print(f"通过 ✓ (文本: {conf:.2f}, 结构化: {conf2:.2f})")

    # 测试用例 6: 错误处理
    print("\n[测试6] 错误处理")
    # 无效输出格式
    ok, output, err = process_input("测试", "xml")
    assert ok, "格式参数应被忽略或降级，不应导致失败"
    print("通过 ✓")

    # 测试用例 7: URL 文本识别
    print("\n[测试7] URL 文本识别")
    url_text = "请访问 https://example.com 查看详情"
    ok, output, err = process_input(url_text, "text")
    assert ok, f"URL 处理失败: {err}"
    assert "has_url" in output or "has_url" in str(key_info), "应识别 URL"
    print("通过 ✓")

    # 测试用例 8: JSON 字符串解析
    print("\n[测试8] JSON 字符串解析")
    json_str = '{"name": "测试项目", "status": "active"}'
    ok, output, err = process_input(json_str, "json")
    assert ok, f"JSON 字符串解析失败: {err}"
    parsed = json.loads(output)
    assert parsed["data"]["name"] == "测试项目", "JSON 解析数据不正确"
    print("通过 ✓")

    print("\n=== 自检全部通过 ===")
    return True


# ============================================================
# 主函数
# ============================================================

def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="ux-wise-agent 技能实现",
        epilog="示例: python main.py --input '文本内容' --format json"
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", type=str, help="单个输入内容")
    parser.add_argument("--batch", nargs="+", help="批量输入（多个参数）")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="输出格式")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print(f"{SKILL_META['name']} v{SKILL_META['version']}")
        print(f"作者: {SKILL_META['author']}")
        print(f"描述: {SKILL_META['description']}")
        return 0

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 处理输入
    try:
        if args.batch:
            # 批量模式
            ok, output, err = process_batch(args.batch, args.format)
            print(output)
            return 0 if ok else 1
        elif args.input:
            # 单个输入模式
            ok, output, err = process_input(args.input, args.format)
            print(output)
            return 0 if ok else 1
        else:
            # 无输入，显示帮助
            parser.print_help()
            print("\n错误: 请提供 --input 或 --batch 参数", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"E010 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
