#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: scripts/main.py
功能: 实现 uber-go-guide-pl 技能的核心处理流程（翻译润色）。
说明:
  - 仅依据功能规格独立实现（clean-room）。
  - 标准库实现，无第三方依赖。
  - 支持 --selftest 离线自检。
"""

import argparse
import sys
import re
from typing import Dict, List, Optional, Tuple, Any


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES: Dict[str, str] = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查输入格式。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部处理异常，请重试。",
    "E007": "参数解析失败，请检查命令行参数。",
    "E008": "输出写入失败，请检查权限或路径。",
    "E009": "输入内容过大，超出处理限制。",
    "E010": "未知错误，请查看日志。",
}


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# 置信度阈值
CONFIDENCE_HIGH = 90
CONFIDENCE_MEDIUM = 85

# 默认输出模板字段
DEFAULT_FIELDS = ["原文", "译文", "置信度", "备注"]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果数据类"""
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []
        self.overall_confidence: float = 0.0
        self.errors: List[str] = []

    def add_item(self, original: str, translated: str, confidence: float, note: str = "") -> None:
        self.items.append({
            "原文": original,
            "译文": translated,
            "置信度": confidence,
            "备注": note,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "结果数": len(self.items),
            "平均置信度": self.overall_confidence,
            "数据": self.items,
            "错误": self.errors,
        }


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------
def validate_input(data: Any) -> Tuple[bool, str]:
    """
    校验输入数据（Step 1: 收集最小信息集）
    返回: (是否通过, 错误码或空字符串)
    """
    if data is None:
        return False, "E001"
    if isinstance(data, str) and not data.strip():
        return False, "E001"
    if isinstance(data, (list, tuple)) and len(data) == 0:
        return False, "E001"
    return True, ""


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    提取输入中的关键信息（Step 2.1）
    支持: 文本、关键词、结构化占位符
    """
    info: Dict[str, Any] = {}

    # 检测是否包含 URL
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    if urls:
        info["urls"] = urls

    # 检测是否包含文件路径
    file_pattern = r'[\w\-./\\]+\.\w{1,5}'
    files = re.findall(file_pattern, text)
    if files:
        info["files"] = files

    # 统计文本长度
    info["length"] = len(text)

    # 检测关键词
    keywords = ["翻译", "润色", "格式化", "批量", "转换"]
    found_keywords = [kw for kw in keywords if kw in text]
    if found_keywords:
        info["keywords"] = found_keywords

    return info


def compute_confidence(info: Dict[str, Any]) -> float:
    """
    计算处理置信度（Step 2.3）
    规则:
      - 有明确关键词: 95
      - 有 URL/文件: 90
      - 文本较长(>50): 88
      - 文本较短: 80
    """
    score = 80.0

    if "keywords" in info and len(info["keywords"]) > 0:
        score += 10

    if "urls" in info or "files" in info:
        score += 5

    if info.get("length", 0) > 50:
        score += 3

    return min(score, 99.0)


def format_output(result: ProcessingResult, output_format: str = "text") -> str:
    """
    格式化输出结果（Step 3）
    支持: text / json / csv
    """
    if output_format == "json":
        import json
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    elif output_format == "csv":
        lines = [",".join(DEFAULT_FIELDS)]
        for item in result.items:
            lines.append(",".join([
                f'"{item["原文"]}"',
                f'"{item["译文"]}"',
                str(item["置信度"]),
                f'"{item["备注"]}"',
            ]))
        return "\n".join(lines)

    else:  # text 默认
        lines = []
        for i, item in enumerate(result.items, 1):
            lines.append(f"[{i}] 原文: {item['原文']}")
            lines.append(f"    译文: {item['译文']}")
            lines.append(f"    置信度: {item['置信度']}%")
            if item["备注"]:
                lines.append(f"    备注: {item['备注']}")
            lines.append("")
        lines.append(f"平均置信度: {result.overall_confidence:.1f}%")
        return "\n".join(lines)


def process_text(text: str, target_lang: str = "pl") -> ProcessingResult:
    """
    核心处理流程（Step 2: 执行核心流程）
    对输入文本进行翻译润色处理（模拟）。
    实际场景中，这里会调用翻译服务或语言模型。
    本实现中，使用规则进行简单处理。
    """
    result = ProcessingResult()

    # 校验输入
    ok, err_code = validate_input(text)
    if not ok:
        result.errors.append(ERROR_CODES[err_code])
        return result

    # 提取关键信息
    info = extract_key_info(text)

    # 计算置信度
    confidence = compute_confidence(info)

    # 模拟翻译润色（规则替换）
    # 注意: 这里仅做演示，实际应调用外部服务
    translated = _mock_translate(text, target_lang)

    # 构建结果
    note = ""
    if confidence < CONFIDENCE_MEDIUM:
        note = "[需核实]"
    elif confidence < CONFIDENCE_HIGH:
        note = "建议复核"

    result.add_item(text, translated, confidence, note)

    # 计算平均置信度
    if result.items:
        total_conf = sum(item["置信度"] for item in result.items)
        result.overall_confidence = total_conf / len(result.items)

    return result


def _mock_translate(text: str, target_lang: str) -> str:
    """
    模拟翻译函数（仅用于演示和自检）。
    实际实现中，应调用翻译 API 或语言模型。
    """
    # 简单规则: 将常见英文词替换为波兰语
    translations = {
        "hello": "cześć",
        "world": "świat",
        "good": "dobry",
        "morning": "poranek",
        "thank": "dziękuję",
        "please": "proszę",
        "yes": "tak",
        "no": "nie",
    }

    words = text.split()
    translated_words = []
    for word in words:
        lower_word = word.lower().strip(".,!?;:")
        if lower_word in translations:
            translated_words.append(translations[lower_word])
        else:
            translated_words.append(word)

    return " ".join(translated_words)


def batch_process(inputs: List[str], target_lang: str = "pl") -> ProcessingResult:
    """
    批量处理（进阶用法）
    """
    result = ProcessingResult()

    for text in inputs:
        sub_result = process_text(text, target_lang)
        result.items.extend(sub_result.items)
        result.errors.extend(sub_result.errors)

    if result.items:
        total_conf = sum(item["置信度"] for item in result.items)
        result.overall_confidence = total_conf / len(result.items)

    return result


# ---------------------------------------------------------------------------
# 自检函数（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部资源。
    断言使用宽松阈值，确保稳健。
    """
    print("[自检] 开始...")

    # 测试 1: 单条文本处理
    print("[自检] 测试1: 单条文本处理")
    text1 = "hello world"
    result1 = process_text(text1, "pl")
    assert len(result1.items) == 1, "测试1失败: 应产生1条结果"
    assert result1.items[0]["原文"] == text1, "测试1失败: 原文不匹配"
    assert result1.items[0]["译文"] != "", "测试1失败: 译文不应为空"
    assert 0 <= result1.items[0]["置信度"] <= 100, "测试1失败: 置信度应在0-100之间"
    print("[自检] 测试1: 通过")

    # 测试 2: 空输入处理
    print("[自检] 测试2: 空输入处理")
    result2 = process_text("", "pl")
    assert len(result2.errors) > 0, "测试2失败: 空输入应产生错误"
    assert result2.errors[0] == ERROR_CODES["E001"], "测试2失败: 错误码应为 E001"
    print("[自检] 测试2: 通过")

    # 测试 3: 批量处理
    print("[自检] 测试3: 批量处理")
    inputs = ["good morning", "thank you", "please help"]
    result3 = batch_process(inputs, "pl")
    assert len(result3.items) == 3, "测试3失败: 应产生3条结果"
    assert result3.overall_confidence > 0, "测试3失败: 平均置信度应大于0"
    print("[自检] 测试3: 通过")

    # 测试 4: 置信度计算
    print("[自检] 测试4: 置信度计算")
    info_with_keywords = {"keywords": ["翻译"], "length": 100}
    conf_high = compute_confidence(info_with_keywords)
    info_plain = {"length": 10}
    conf_low = compute_confidence(info_plain)
    assert conf_high > conf_low, "测试4失败: 有关键词时置信度应更高"
    assert conf_high >= 80, "测试4失败: 置信度应不低于80"
    print("[自检] 测试4: 通过")

    # 测试 5: 格式化输出
    print("[自检] 测试5: 格式化输出")
    result5 = process_text("hello world", "pl")
    text_out = format_output(result5, "text")
    json_out = format_output(result5, "json")
    csv_out = format_output(result5, "csv")
    assert len(text_out) > 0, "测试5失败: 文本输出不应为空"
    assert len(json_out) > 0, "测试5失败: JSON输出不应为空"
    assert len(csv_out) > 0, "测试5失败: CSV输出不应为空"
    print("[自检] 测试5: 通过")

    # 测试 6: 关键信息提取
    print("[自检] 测试6: 关键信息提取")
    test_text = "请翻译这个文件: /path/to/file.txt 以及 https://example.com"
    info6 = extract_key_info(test_text)
    assert "files" in info6, "测试6失败: 应提取到文件路径"
    assert "urls" in info6, "测试6失败: 应提取到URL"
    assert len(info6["files"]) > 0, "测试6失败: 文件列表不应为空"
    assert len(info6["urls"]) > 0, "测试6失败: URL列表不应为空"
    print("[自检] 测试6: 通过")

    # 测试 7: 错误处理
    print("[自检] 测试7: 错误处理")
    assert "E001" in ERROR_CODES, "测试7失败: 应包含 E001"
    assert "E010" in ERROR_CODES, "测试7失败: 应包含 E010"
    assert len(ERROR_CODES) == 10, "测试7失败: 应有10个错误码"
    print("[自检] 测试7: 通过")

    # 测试 8: 批量空输入
    print("[自检] 测试8: 批量空输入")
    result8 = batch_process([], "pl")
    assert len(result8.items) == 0, "测试8失败: 空批量应无结果"
    print("[自检] 测试8: 通过")

    print("[自检] 全部通过!")
    return True


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------
def main() -> int:
    """
    主入口函数
    """
    parser = argparse.ArgumentParser(
        description="uber-go-guide-pl 翻译润色技能工具",
        epilog="示例: python main.py --input 'hello world' --lang pl --format text"
    )

    # 输入参数
    parser.add_argument("--input", type=str, help="待处理的文本内容")
    parser.add_argument("--file", type=str, help="输入文件路径")
    parser.add_argument("--lang", type=str, default="pl", help="目标语言 (默认: pl)")

    # 输出参数
    parser.add_argument("--format", type=str, choices=["text", "json", "csv"],
                       default="text", help="输出格式 (默认: text)")
    parser.add_argument("--output", type=str, help="输出文件路径")

    # 功能参数
    parser.add_argument("--batch", action="store_true", help="批量处理模式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit as e:
        print(f"错误: {ERROR_CODES['E007']}")
        return 1

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"[自检] 失败: {e}")
            return 1

    # 检查是否有输入
    if not args.input and not args.file:
        print(f"错误: {ERROR_CODES['E001']}")
        print("请提供 --input 或 --file 参数")
        return 1

    # 读取输入
    input_text = args.input
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception as e:
            print(f"错误: {ERROR_CODES['E008']}: {e}")
            return 1

    # 处理输入
    try:
        if args.batch:
            # 批量模式: 按行处理
            lines = input_text.strip().split("\n")
            result = batch_process(lines, args.lang)
        else:
            result = process_text(input_text, args.lang)

        # 检查是否有错误
        if result.errors:
            for err in result.errors:
                print(f"警告: {err}")

        # 格式化输出
        output = format_output(result, args.format)

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"结果已写入: {args.output}")
            except Exception as e:
                print(f"错误: {ERROR_CODES['E008']}: {e}")
                return 1
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"错误: {ERROR_CODES['E006']}: {e}")
        return 1


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
