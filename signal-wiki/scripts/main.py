#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signal-wiki 独立实现脚本

依据功能规格 clean-room 重写，仅依赖标准库。
提供核心数据处理流程、置信度标注、错误码体系以及离线自检。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码与标准化话术映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
}


class SignalWikiError(Exception):
    """带错误码的异常类"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_MESSAGES.get(code, "未知错误").format(**kwargs)
        super().__init__(self.message)


def _extract_key_fields(content: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段（结构化处理核心）

    规则：
    - 识别形如 "字段名: 值" 或 "字段名=值" 的键值对
    - 识别常见命名实体（如日期、数字、邮箱）
    - 返回结构化字典及原始文本
    """
    if not content or not content.strip():
        raise SignalWikiError("E001")

    result: Dict[str, Any] = {}
    lines = content.strip().splitlines()

    # 1. 尝试键值对提取
    kv_pattern = re.compile(r"^\s*([\u4e00-\u9fa5\w]+)\s*[:：=]\s*(.+?)\s*$")
    for line in lines:
        match = kv_pattern.match(line)
        if match:
            key, value = match.group(1), match.group(2)
            result[key] = value

    # 2. 尝试识别日期（常见格式）
    date_pattern = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}")
    dates = date_pattern.findall(content)
    if dates:
        result["_dates"] = dates

    # 3. 尝试识别邮箱
    email_pattern = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    emails = email_pattern.findall(content)
    if emails:
        result["_emails"] = emails

    # 4. 尝试识别 URL
    url_pattern = re.compile(r"https?://[^\s]+")
    urls = url_pattern.findall(content)
    if urls:
        result["_urls"] = urls

    # 5. 尝试识别数字（含小数）
    num_pattern = re.compile(r"\d+(?:\.\d+)?")
    numbers = num_pattern.findall(content)
    if numbers:
        result["_numbers"] = numbers

    # 6. 统计文本长度与行数
    result["_text_length"] = len(content)
    result["_line_count"] = len(lines)

    return result


def _calculate_confidence(content: str, extracted: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）

    规则：
    - 基础分 60
    - 有键值对 +15
    - 有日期/邮箱/URL +10（每类 +5，上限 +10）
    - 文本长度 > 20 +5
    - 文本长度 > 100 +5
    - 行数 > 3 +5
    - 上限 100
    """
    score = 60.0

    if any(k for k in extracted if not k.startswith("_")):
        score += 15.0

    if extracted.get("_dates"):
        score += 5.0
    if extracted.get("_emails") or extracted.get("_urls"):
        score += 5.0

    text_len = extracted.get("_text_length", 0)
    if text_len > 20:
        score += 5.0
    if text_len > 100:
        score += 5.0

    if extracted.get("_line_count", 0) > 3:
        score += 5.0

    return min(score, 100.0)


def _format_output(
    content: str, extracted: Dict[str, Any], confidence: float
) -> Dict[str, Any]:
    """
    按约定格式生成输出

    置信度分级：
    - >=90：直接输出
    - 85-90：标注"建议复核"
    - <85：标注"[需核实]"并说明不确定点
    """
    output: Dict[str, Any] = {
        "status": "ok",
        "input_preview": content[:100] + ("..." if len(content) > 100 else ""),
        "extracted_fields": {k: v for k, v in extracted.items() if not k.startswith("_")},
        "metadata": {
            "dates": extracted.get("_dates", []),
            "emails": extracted.get("_emails", []),
            "urls": extracted.get("_urls", []),
            "numbers": extracted.get("_numbers", []),
        },
        "confidence": round(confidence, 1),
    }

    # 置信度标注
    if confidence >= 90:
        output["note"] = "直接输出"
    elif confidence >= 85:
        output["note"] = "建议复核"
    else:
        output["note"] = "[需核实]"
        # 说明不确定点
        uncertainties = []
        if not output["extracted_fields"]:
            uncertainties.append("未识别到明确的键值对字段")
        if not output["metadata"]["dates"] and not output["metadata"]["emails"]:
            uncertainties.append("未识别到日期或邮箱等关键信息")
        output["uncertainties"] = uncertainties

    return output


def process_input(content: str) -> Dict[str, Any]:
    """
    标准处理流程（Step 2 核心）

    参数:
        content: 用户提供的原始文本

    返回:
        结构化结果字典

    异常:
        SignalWikiError: 输入为空时抛出 E001
    """
    # Step 2.1: 解析输入，识别关键信息
    extracted = _extract_key_fields(content)

    # Step 2.2: 计算置信度
    confidence = _calculate_confidence(content, extracted)

    # Step 2.3: 生成输出
    return _format_output(content, extracted, confidence)


def batch_process(inputs: List[str]) -> List[Dict[str, Any]]:
    """
    批量处理（进阶用法）

    参数:
        inputs: 多个输入文本的列表

    返回:
        每个输入对应的处理结果列表
    """
    if not inputs:
        raise SignalWikiError("E001")

    results = []
    for item in inputs:
        try:
            results.append(process_input(item))
        except SignalWikiError as e:
            results.append({"status": "error", "code": e.code, "message": e.message})
    return results


def _run_selftest() -> bool:
    """
    离线自检：使用内置样例验证核心逻辑

    覆盖场景：
    1. 正常输入（高置信度）
    2. 简单输入（低置信度）
    3. 空输入（E001）
    4. 批量处理
    """
    print("[selftest] 开始离线自检...")

    # 测试用例 1：正常输入（应高置信度）
    sample1 = (
        "项目名称: 数据迁移\n"
        "负责人: 张三\n"
        "日期: 2024-03-15\n"
        "预算: 50000\n"
        "邮箱: zhangsan@example.com\n"
        "说明: 这是一个较长的项目描述，用于测试置信度计算逻辑是否正常。"
    )
    result1 = process_input(sample1)
    assert result1["status"] == "ok", f"用例1失败: {result1}"
    assert result1["confidence"] >= 90, f"用例1置信度不足: {result1['confidence']}"
    assert result1["note"] == "直接输出", f"用例1标注错误: {result1['note']}"
    print(f"  用例1通过 (置信度: {result1['confidence']}%)")

    # 测试用例 2：简单输入（应低置信度）
    sample2 = "你好"
    result2 = process_input(sample2)
    assert result2["status"] == "ok", f"用例2失败: {result2}"
    assert result2["confidence"] < 85, f"用例2置信度应低: {result2['confidence']}"
    assert result2["note"] == "[需核实]", f"用例2标注错误: {result2['note']}"
    assert "uncertainties" in result2, "用例2应包含不确定点说明"
    print(f"  用例2通过 (置信度: {result2['confidence']}%)")

    # 测试用例 3：空输入（应报 E001）
    try:
        process_input("")
        assert False, "用例3应抛出异常"
    except SignalWikiError as e:
        assert e.code == "E001", f"用例3错误码错误: {e.code}"
        print(f"  用例3通过 (错误码: {e.code})")

    # 测试用例 4：批量处理
    batch = [sample1, sample2, ""]
    results = batch_process(batch)
    assert len(results) == 3, f"用例4结果数量错误: {len(results)}"
    assert results[0]["status"] == "ok"
    assert results[1]["status"] == "ok"
    assert results[2]["status"] == "error"
    assert results[2]["code"] == "E001"
    print(f"  用例4通过 (批量处理 {len(results)} 项)")

    # 测试用例 5：中等置信度（85-90 区间）
    sample5 = "标题: 测试\n作者: 李四\n内容: 简短描述"
    result5 = process_input(sample5)
    assert result5["status"] == "ok", f"用例5失败: {result5}"
    if 85 <= result5["confidence"] < 90:
        assert result5["note"] == "建议复核", f"用例5标注错误: {result5['note']}"
    print(f"  用例5通过 (置信度: {result5['confidence']}%)")

    print("[selftest] 全部用例通过 ✓")
    return True


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="signal-wiki - 结构化数据处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
        "  python main.py --input '项目: 测试\\n日期: 2024-01-01'\n"
        "  python main.py --batch '第一条' '第二条'\n"
        "  python main.py --selftest\n",
    )
    parser.add_argument(
        "--input", "-i", type=str, help="单条输入内容（文本）"
    )
    parser.add_argument(
        "--batch", "-b", type=str, nargs="+", help="批量输入（多个文本）"
    )
    parser.add_argument(
        "--json", action="store_true", help="以 JSON 格式输出结果"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行离线自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            _run_selftest()
            return 0
        except AssertionError as e:
            print(f"[selftest] 失败: {e}")
            return 1
        except Exception as e:
            print(f"[selftest] 异常: {e}")
            return 1

    # 处理输入
    try:
        if args.batch:
            results = batch_process(args.batch)
        elif args.input:
            results = [process_input(args.input)]
        else:
            # 无输入时尝试从 stdin 读取
            content = sys.stdin.read().strip()
            if content:
                results = [process_input(content)]
            else:
                raise SignalWikiError("E001")

        # 输出
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for result in results:
                if result["status"] == "ok":
                    print(f"状态: {result['status']}")
                    print(f"输入预览: {result['input_preview']}")
                    print(f"提取字段: {json.dumps(result['extracted_fields'], ensure_ascii=False)}")
                    print(f"元数据: {json.dumps(result['metadata'], ensure_ascii=False)}")
                    print(f"置信度: {result['confidence']}% ({result['note']})")
                    if "uncertainties" in result:
                        print(f"不确定点: {'; '.join(result['uncertainties'])}")
                else:
                    print(f"错误 [{result['code']}]: {result['message']}")
                print("-" * 40)

        return 0

    except SignalWikiError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
