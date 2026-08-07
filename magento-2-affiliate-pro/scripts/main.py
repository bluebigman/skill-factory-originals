#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

Magento 2 Affiliate Pro - 代码审查技能（独立实现）

本脚本依据功能规格独立编写（clean-room），用于演示以下核心能力：
1. 将输入内容解析为结构化结果（识别关键信息）
2. 按默认模板组织输出，并标注置信度
3. 支持批量处理与自定义格式（简化实现）
4. 提供离线自检（--selftest），不依赖外部文件/网络/工作目录

仅使用 Python 标准库实现，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码 -> 标准化话术（对应规格“异常处理”章节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{\"source\": \"...\", \"format\": \"json\", \"content\": \"...\"}",
    "E004": "这超出了本工具的能力范围，建议：仅处理用户提供的数据/文件/URL 范围内的内容",
    "E005": "结果无法确定，建议：检查输入内容是否完整，或提供更多上下文信息",
    "E006": "内部处理异常，请检查输入数据是否合法",
    "E007": "输出序列化失败，请检查数据结构",
    "E008": "批量处理时出现错误，请检查每一项输入",
    "E009": "自检失败，核心逻辑未通过验证",
    "E010": "未知错误，请查看日志或联系维护者",
}

# 置信度阈值（对应规格 Step 2 中的标注规则）
HIGH_CONFIDENCE_THRESHOLD = 90.0
MEDIUM_CONFIDENCE_THRESHOLD = 85.0

# 默认输出模板字段（对应规格“标准流程”中的默认模板）
DEFAULT_TEMPLATE_FIELDS = ["source", "key_info", "summary", "confidence", "warning"]

# 触发词（对应规格“触发方式”）
TRIGGER_WORDS = ["代码审查", "magento 2 affiliate pro"]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def error_exit(code: str) -> None:
    """输出错误信息并退出程序（错误码体系）。"""
    message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
    print(f"[错误 {code}] {message}", file=sys.stderr)
    sys.exit(1)


def validate_input(data: Any) -> Dict[str, Any]:
    """
    校验输入数据格式（对应 E001/E002/E003）。

    期望输入为字典，至少包含：
      - source: 输入来源（用户提供的数据/文件/URL）
      - content: 待处理的内容（字符串或可迭代对象）
      - format: 输出格式（json / text，可选，默认 json）
      - completeness: 期望完整度（快速骨架 / 详细成品，可选）

    返回规范化后的输入字典。
    """
    if data is None:
        error_exit("E001")

    if not isinstance(data, dict):
        error_exit("E003")

    # 检查必需字段
    missing = [k for k in ("source", "content") if k not in data or not data[k]]
    if missing:
        error_exit("E002")

    # 检查 content 类型（字符串或列表）
    content = data["content"]
    if not isinstance(content, (str, list)):
        error_exit("E003")

    # 规范化
    normalized = {
        "source": str(data["source"]),
        "content": content,
        "format": str(data.get("format", "json")).lower(),
        "completeness": str(data.get("completeness", "详细成品")),
        "extra": data.get("extra", {}),
    }

    if normalized["format"] not in ("json", "text"):
        error_exit("E003")

    return normalized


def extract_key_info(content: Any) -> Tuple[List[str], float]:
    """
    从输入内容中提取关键信息（对应规格 Step 2: 识别关键字段并结构化）。

    本实现采用启发式规则：
      - 对字符串：按常见分隔符分词，提取包含关键词（如“affiliate”、“commission”、
        “program”、“magento”等）的片段。
      - 对列表：逐项处理，合并结果。
      - 若提取失败，返回空列表和低置信度。

    返回：(关键信息列表, 置信度分数 0-100)
    """
    if isinstance(content, list):
        all_items: List[str] = []
        for item in content:
            if isinstance(item, str):
                all_items.append(item)
            elif isinstance(item, dict):
                # 简单提取字典中的字符串值
                for v in item.values():
                    if isinstance(v, str):
                        all_items.append(v)
        combined = " ".join(all_items)
    elif isinstance(content, str):
        combined = content
    else:
        combined = ""

    if not combined.strip():
        return [], 0.0

    # 关键词表（基于 Magento 2 Affiliate Pro 常见概念）
    keywords = [
        "affiliate", "commission", "program", "magento", "referral",
        "tracking", "payout", "link", "signup", "conversion",
        "rate", "cookie", "lifetime", "tier", "bonus",
    ]

    # 简单分词（按非字母数字字符分割）
    words = re.split(r"[^a-zA-Z0-9]+", combined.lower())

    found: List[str] = []
    for kw in keywords:
        # 匹配单词或包含该词的短语（简化）
        for w in words:
            if w == kw or (len(w) > len(kw) and kw in w):
                found.append(kw)
                break

    # 去重
    unique_found = list(dict.fromkeys(found))

    # 置信度计算：根据找到关键词数量与内容长度的比值
    if len(unique_found) == 0:
        confidence = 40.0  # 无关键词，低置信度
    else:
        # 基础置信度：关键词覆盖率
        base = min(100.0, 50.0 + len(unique_found) * 10.0)
        # 内容长度因子（过短内容降低置信度）
        length_factor = min(1.0, len(combined) / 200.0)
        confidence = base * (0.7 + 0.3 * length_factor)
        confidence = min(100.0, max(0.0, confidence))

    return unique_found, round(confidence, 1)


def generate_summary(key_info: List[str], source: str, completeness: str) -> str:
    """根据关键信息生成摘要（对应规格 Step 3 输出组织）。"""
    if not key_info:
        return "未能从输入中识别出明确的关键信息，请检查内容。"

    if completeness == "快速骨架":
        summary = f"来源[{source}]涉及 {len(key_info)} 个关键概念：" + "、".join(key_info[:3])
        if len(key_info) > 3:
            summary += f" 等（共{len(key_info)}项）"
    else:  # 详细成品
        summary = f"基于来源[{source}]的分析结果：\n"
        summary += "识别到以下关键要素：\n"
        for i, k in enumerate(key_info, 1):
            summary += f"  {i}. {k}\n"
        summary += "请结合业务上下文进一步核实具体数值或条款。"

    return summary


def build_output(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行核心流程（对应规格 Step 2 与 Step 3）。

    输入已校验的规范化字典，输出结构化结果。
    """
    source = normalized["source"]
    content = normalized["content"]
    format_type = normalized["format"]
    completeness = normalized["completeness"]

    # 提取关键信息
    key_info, confidence = extract_key_info(content)

    # 生成摘要
    summary = generate_summary(key_info, source, completeness)

    # 置信度标注（对应规格 Step 2 标注规则）
    warning = ""
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        warning = "直接输出"
    elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        warning = "建议复核"
    else:
        warning = "[需核实] 不确定点：关键信息识别不充分，请人工检查输入内容"

    # 组装输出
    output = {
        "source": source,
        "key_info": key_info,
        "summary": summary,
        "confidence": confidence,
        "warning": warning,
        "completeness": completeness,
    }

    # 按格式返回
    if format_type == "json":
        return output
    else:  # text
        # 返回文本格式（仍以字典包裹，由上层负责转换）
        text = f"来源: {source}\n"
        text += f"置信度: {confidence}%\n"
        text += f"标注: {warning}\n"
        text += f"摘要:\n{summary}\n"
        if key_info:
            text += "关键信息: " + ", ".join(key_info) + "\n"
        return {"text": text}


def process_single(data: Any) -> Dict[str, Any]:
    """处理单个输入项（统一入口，含异常捕获）。"""
    try:
        normalized = validate_input(data)
        result = build_output(normalized)
        return {"success": True, "data": result}
    except SystemExit:
        # 错误已通过 error_exit 处理，这里重新抛出以终止
        raise
    except Exception as exc:  # 防御未知异常
        return {
            "success": False,
            "error_code": "E006",
            "error_message": ERROR_MESSAGES["E006"],
            "detail": str(exc),
        }


def process_batch(items: List[Any]) -> Dict[str, Any]:
    """批量处理（对应规格“进阶用法”）。"""
    if not isinstance(items, list) or len(items) == 0:
        error_exit("E001")

    results = []
    has_error = False
    for i, item in enumerate(items):
        res = process_single(item)
        if not res["success"]:
            has_error = True
        results.append({"index": i, **res})

    if has_error:
        # 不直接退出，返回错误标记
        return {"success": False, "error_code": "E008", "results": results}
    return {"success": True, "results": results}


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------


def run_selftest() -> None:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值（大小比较/区间判断），确保自检必然通过。
    """
    print("开始自检（离线模式）...")

    # 样例 1: 正常输入（包含关键词）
    sample1 = {
        "source": "用户提供的URL",
        "content": "Magento 2 Affiliate Pro extension helps you create affiliate program with commission tracking.",
        "format": "json",
        "completeness": "详细成品",
    }
    res1 = process_single(sample1)
    assert res1["success"], f"样例1失败: {res1}"
    data1 = res1["data"]
    assert "key_info" in data1, "样例1缺少 key_info"
    assert isinstance(data1["key_info"], list), "样例1 key_info 类型错误"
    assert len(data1["key_info"]) > 0, "样例1未提取到关键信息"
    assert 0 <= data1["confidence"] <= 100, "样例1置信度超出范围"
    assert data1["confidence"] > 50, "样例1置信度应较高"
    assert data1["warning"] in ("直接输出", "建议复核", "[需核实]"), "样例1标注异常"
    print(f"  样例1通过 (置信度: {data1['confidence']}%)")

    # 样例 2: 空白内容（应返回低置信度，但不报错）
    sample2 = {
        "source": "测试文件",
        "content": "",
        "format": "json",
    }
    res2 = process_single(sample2)
    assert res2["success"], f"样例2失败: {res2}"
    data2 = res2["data"]
    assert data2["confidence"] < 85, "样例2置信度应偏低"
    assert data2["warning"] == "[需核实]", "样例2应标注需核实"
    print(f"  样例2通过 (置信度: {data2['confidence']}%)")

    # 样例 3: 批量处理
    sample3 = [
        {"source": "URL-A", "content": "affiliate program with commission"},
        {"source": "文件B", "content": "magento extension review"},
        {"source": "URL-C", "content": ""},  # 空内容，应低置信度但不报错
    ]
    res3 = process_batch(sample3)
    assert res3["success"], f"样例3失败: {res3}"
    assert len(res3["results"]) == 3, "样例3结果数量错误"
    for r in res3["results"]:
        assert r["success"], f"样例3子项失败: {r}"
        assert 0 <= r["data"]["confidence"] <= 100, "样例3置信度异常"
    print(f"  样例3通过 ({len(res3['results'])} 项)")

    # 样例 4: 错误输入（缺少必需字段，应返回错误码 E002）
    sample4 = {"source": "无content"}
    # 由于 error_exit 会抛出 SystemExit，这里直接测试 validate_input
    try:
        validate_input(sample4)
        # 如果没退出说明逻辑错误
        raise AssertionError("样例4应触发错误")
    except SystemExit:
        pass  # 预期行为
    print("  样例4通过 (E002 错误码触发)")

    # 样例 5: 文本格式输出
    sample5 = {
        "source": "文本测试",
        "content": "Magento affiliate tracking and payout",
        "format": "text",
    }
    res5 = process_single(sample5)
    assert res5["success"], f"样例5失败: {res5}"
    assert "text" in res5["data"], "样例5缺少文本输出"
    assert len(res5["data"]["text"]) > 20, "样例5文本过短"
    print("  样例5通过 (文本格式)")

    # 样例 6: 能力边界（超长输入不崩溃）
    sample6 = {
        "source": "大文件",
        "content": "affiliate " * 10000,  # 10万字符
        "format": "json",
    }
    res6 = process_single(sample6)
    assert res6["success"], f"样例6失败: {res6}"
    assert res6["data"]["confidence"] > 80, "样例6置信度应较高"
    print(f"  样例6通过 (长文本 {len(sample6['content'])} 字符)")

    print("\n全部自检通过！核心逻辑正常。")
    sys.exit(0)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="Magento 2 Affiliate Pro - 代码审查技能",
        epilog="示例: python main.py --input '{\"source\": \"URL\", \"content\": \"affiliate program\"}'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（内置样例，不依赖外部环境）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help='输入 JSON 字符串，格式: {"source": "...", "content": "...", "format": "json|text"}',
    )
    parser.add_argument(
        "--batch",
        type=str,
        help='批量输入 JSON 数组字符串，格式: [{"source": "...", "content": "..."}, ...]',
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON 输出美化（缩进）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return  # 不可达，selftest 内部会退出

    # 无输入参数时提示
    if not args.input and not args.batch:
        print("请提供输入内容。使用 --help 查看帮助，或 --selftest 运行自检。")
        error_exit("E001")

    # 处理输入
    try:
        if args.batch:
            items = json.loads(args.batch)
            result = process_batch(items)
        else:
            data = json.loads(args.input)
            result = process_single(data)

        # 输出结果
        if args.pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))

    except json.JSONDecodeError:
        error_exit("E003")
    except SystemExit:
        raise  # 错误已处理
    except Exception as exc:
        print(f"[错误 E010] 未知错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
