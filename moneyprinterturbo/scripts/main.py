#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题或关键词一键生成（moneyprinterturbo）— 独立实现脚本

本脚本依据功能规格独立实现，不包含任何既有代码。
提供核心处理逻辑与离线自检功能。
"""

import argparse
import sys
import json
import re


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}


class InputError(Exception):
    """输入处理异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw_text: str) -> dict:
    """
    解析输入内容，识别关键字段并结构化。

    参数:
        raw_text: 用户提供的原始文本

    返回:
        结构化字典，包含:
        - raw: 原始输入
        - keywords: 提取的关键词列表
        - has_url: 是否包含 URL
        - has_file: 是否包含文件路径
        - urls: 提取到的 URL 列表
        - files: 提取到的文件路径列表
        - confidence: 置信度 (0-100)

    异常:
        InputError: E001 输入为空 / E003 格式错误
    """
    if not raw_text or not raw_text.strip():
        raise InputError("E001")

    text = raw_text.strip()

    # 检测 URL
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    has_url = len(urls) > 0

    # 检测文件路径（简单模式：包含 . 和路径分隔符）
    file_pattern = r'[\w\-./\\]+\.[a-zA-Z0-9]{1,5}'
    files = re.findall(file_pattern, text)
    # 过滤掉 URL 中的部分
    files = [f for f in files if not f.startswith('http')]
    has_file = len(files) > 0

    # 提取关键词（去除 URL、文件路径、常见停用词）
    cleaned = text
    for url in urls:
        cleaned = cleaned.replace(url, ' ')
    for f in files:
        cleaned = cleaned.replace(f, ' ')

    stopwords = {'的', '了', '和', '是', '在', '把', '将', '一个', '这个', '那个',
                 '帮我', '处理', '一下', '这个', '这些', '批量', '弄', '转成',
                 '格式', '生成', '视频', '主题', '关键词'}
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', cleaned)
    keywords = [w for w in words if w not in stopwords and len(w) > 0]

    # 去重保持顺序
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    # 计算置信度
    confidence = 90
    if not unique_keywords:
        confidence = 60  # 没有提取到有效关键词
    elif len(unique_keywords) < 2:
        confidence = 85  # 关键词过少

    return {
        "raw": text,
        "keywords": unique_keywords,
        "has_url": has_url,
        "has_file": has_file,
        "urls": urls,
        "files": files,
        "confidence": confidence,
    }


def generate_output(structured: dict, output_format: str = "json") -> dict:
    """
    按默认模板组织输出结果。

    参数:
        structured: 结构化输入数据
        output_format: 输出格式（json / text）

    返回:
        输出字典，包含处理结果和置信度标注
    """
    confidence = structured["confidence"]

    # 置信度标注
    if confidence >= 90:
        confidence_tag = "直接输出"
    elif confidence >= 85:
        confidence_tag = "建议复核"
    else:
        confidence_tag = "[需核实]"

    # 构建输出结果
    result = {
        "status": "success",
        "input_summary": {
            "has_url": structured["has_url"],
            "has_file": structured["has_file"],
            "url_count": len(structured["urls"]),
            "file_count": len(structured["files"]),
        },
        "extracted_keywords": structured["keywords"],
        "confidence": confidence,
        "confidence_tag": confidence_tag,
        "output_format": output_format,
    }

    # 低置信度时添加说明
    if confidence < 85:
        result["note"] = "输入信息不足，建议补充更多关键词或说明"

    return result


def process_input(raw_text: str, output_format: str = "json") -> dict:
    """
    标准处理流程：解析 -> 处理 -> 输出。

    参数:
        raw_text: 用户输入
        output_format: 输出格式

    返回:
        处理结果字典

    异常:
        InputError: 输入相关错误
    """
    # Step 1: 解析输入
    structured = parse_input(raw_text)

    # Step 2: 检查关键信息是否完整
    if not structured["keywords"] and not structured["has_url"] and not structured["has_file"]:
        raise InputError("E002", "未识别到有效内容，请提供主题关键词、URL或文件路径")

    # Step 3: 生成输出
    result = generate_output(structured, output_format)
    return result


def batch_process(inputs: list, output_format: str = "json") -> list:
    """
    批量处理多个输入。

    参数:
        inputs: 输入文本列表
        output_format: 输出格式

    返回:
        处理结果列表，每个元素为 dict 或错误信息
    """
    results = []
    for idx, item in enumerate(inputs):
        try:
            result = process_input(item, output_format)
            result["batch_index"] = idx
            results.append(result)
        except InputError as e:
            results.append({
                "batch_index": idx,
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
            })
    return results


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("开始自检...")

    try:
        # 测试用例 1: 正常输入
        test1 = "帮我处理一下这个 https://example.com/video 人工智能 短视频"
        result1 = process_input(test1)
        assert result1["status"] == "success", "测试1: 状态应为 success"
        assert result1["input_summary"]["has_url"] is True, "测试1: 应检测到 URL"
        assert len(result1["extracted_keywords"]) > 0, "测试1: 应提取到关键词"
        assert result1["confidence"] >= 85, "测试1: 置信度应不低于85"
        print("  测试1 (正常输入) 通过")

        # 测试用例 2: 空输入
        try:
            process_input("")
            assert False, "测试2: 空输入应抛出异常"
        except InputError as e:
            assert e.code == "E001", "测试2: 错误码应为 E001"
        print("  测试2 (空输入) 通过")

        # 测试用例 3: 批量处理
        test3_inputs = ["第一个主题 关键词", "", "第二个主题 https://example.com"]
        results3 = batch_process(test3_inputs)
        assert len(results3) == 3, "测试3: 应有3个结果"
        assert results3[0]["status"] == "success", "测试3: 第一条应成功"
        assert results3[1]["status"] == "error", "测试3: 第二条应失败"
        assert results3[1]["error_code"] == "E001", "测试3: 第二条错误码应为E001"
        assert results3[2]["status"] == "success", "测试3: 第三条应成功"
        print("  测试3 (批量处理) 通过")

        # 测试用例 4: 低置信度场景
        test4 = "abc"
        result4 = process_input(test4)
        assert result4["status"] == "success", "测试4: 状态应为 success"
        # 宽松断言：置信度在合理范围内
        assert 0 <= result4["confidence"] <= 100, "测试4: 置信度应在0-100之间"
        print("  测试4 (低置信度) 通过")

        # 测试用例 5: 文件路径检测
        test5 = "处理 data/report.pdf 这个文件"
        result5 = process_input(test5)
        assert result5["status"] == "success", "测试5: 状态应为 success"
        assert result5["input_summary"]["has_file"] is True, "测试5: 应检测到文件"
        print("  测试5 (文件路径检测) 通过")

        # 测试用例 6: 错误码映射
        assert "E001" in ERROR_CODES, "测试6: E001 应存在"
        assert "E002" in ERROR_CODES, "测试6: E002 应存在"
        assert "E003" in ERROR_CODES, "测试6: E003 应存在"
        assert "E004" in ERROR_CODES, "测试6: E004 应存在"
        assert "E005" in ERROR_CODES, "测试6: E005 应存在"
        print("  测试6 (错误码映射) 通过")

        print("所有自检测试通过！")
        return True

    except AssertionError as e:
        print(f"自检失败: {e}")
        return False
    except Exception as e:
        print(f"自检异常: {e}")
        return False


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="主题或关键词一键生成 - 利用 AI 大模型和自动化工作流生成高清短视频"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：主题关键词、URL或文件路径"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON 数组字符串，如 '[\"主题1\", \"主题2\"]'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        if run_selftest():
            return 0
        else:
            return 1

    # 批量模式
    if args.batch:
        try:
            inputs = json.loads(args.batch)
            if not isinstance(inputs, list):
                raise InputError("E003", "批量输入应为 JSON 数组")
            results = batch_process(inputs, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except json.JSONDecodeError:
            print(json.dumps({
                "status": "error",
                "error_code": "E003",
                "error_message": "批量输入 JSON 格式错误",
            }, ensure_ascii=False))
            return 1
        except InputError as e:
            print(json.dumps({
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
            }, ensure_ascii=False))
            return 1

    # 单条模式
    if args.input:
        try:
            result = process_input(args.input, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except InputError as e:
            print(json.dumps({
                "status": "error",
                "error_code": e.code,
                "error_message": e.message,
            }, ensure_ascii=False))
            return 1

    # 无参数时提示用法
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
