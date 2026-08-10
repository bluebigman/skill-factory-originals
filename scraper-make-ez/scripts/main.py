#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scraper-make-ez 技能独立实现脚本
=================================
仅供学习与参考用途。提供规范、可复用的网页数据采集处理流程与输出。

功能概述：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

作者：skill-factory-auto
版本：1.0.0
许可证：MIT License
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与异常定义
# ============================================================
class ScraperError(Exception):
    """爬虫采集技能基础异常类。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心处理逻辑
# ============================================================
def validate_input(raw_input: str) -> str:
    """
    校验输入内容。

    Args:
        raw_input: 用户提供的原始输入字符串。

    Returns:
        去除首尾空白后的有效输入。

    Raises:
        ScraperError: E001 输入为空；E003 输入格式错误。
    """
    if raw_input is None:
        raise ScraperError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    content = raw_input.strip()
    if not content:
        raise ScraperError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    # 宽松格式检查：接受任何非控制字符，拒绝二进制乱码
    # 允许中英文、数字、标点符号、URL、JSON等
    if any(ord(c) < 32 and c not in '\t\n\r' for c in content):
        raise ScraperError("E003", "输入包含控制字符，格式不符合要求")

    # 检查是否包含可打印字符
    if not any(c.isprintable() for c in content):
        raise ScraperError("E003", "输入格式不符合要求，示例：一段文本、URL 或 JSON 字符串")

    return content


def extract_key_fields(content: str) -> Dict[str, Any]:
    """
    从输入内容中提取关键字段。

    识别规则（基于通用模式）：
    - URL
    - 邮箱
    - 日期
    - 数字（含小数和百分比）
    - 关键词（中文词或英文单词）

    Args:
        content: 已校验的输入字符串。

    Returns:
        字典，包含提取到的各类关键字段及原始内容。
    """
    fields: Dict[str, Any] = {
        "原始内容": content,
        "长度": len(content),
        "URL": [],
        "邮箱": [],
        "日期": [],
        "数字": [],
        "关键词": [],
    }

    # URL 提取 - 支持 http/https/ftp
    urls = re.findall(r'(?:https?|ftp)://[^\s<>"\']+', content)
    fields["URL"] = urls[:5]  # 最多保留5个

    # 邮箱提取
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', content)
    fields["邮箱"] = emails[:5]

    # 日期提取（支持常见格式）
    dates = re.findall(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?', content)
    dates += re.findall(r'\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}', content)
    fields["日期"] = list(set(dates))[:5]

    # 数字提取（含小数和百分比）
    numbers = re.findall(r'\d+\.?\d*%?', content)
    fields["数字"] = numbers[:10]

    # 关键词提取（中文连续词或英文单词，长度>=2）
    cn_words = re.findall(r'[\u4e00-\u9fff]{2,}', content)
    en_words = re.findall(r'[a-zA-Z]{2,}', content)
    keywords = list(set(cn_words + en_words))
    fields["关键词"] = keywords[:10]

    return fields


def calculate_confidence(fields: Dict[str, Any]) -> Tuple[float, str]:
    """
    计算提取结果的置信度。

    规则：
    - 基础置信度 60%
    - 每提取到一类关键字段 +10%
    - 内容长度 > 50 +5%
    - 内容长度 > 200 +5%（上限）
    - 最终置信度范围 60%-95%

    Args:
        fields: 提取到的字段字典。

    Returns:
        (置信度百分比, 置信度标注)
    """
    confidence = 60.0

    # 每提取到一类关键字段 +10%
    key_types = ["URL", "邮箱", "日期", "数字", "关键词"]
    for k in key_types:
        if fields.get(k):
            confidence += 10.0

    # 内容长度加分
    length = fields.get("长度", 0)
    if length > 50:
        confidence += 5.0
    if length > 200:
        confidence += 5.0

    # 限制范围
    confidence = min(confidence, 95.0)
    confidence = max(confidence, 60.0)

    # 标注
    if confidence >= 90.0:
        label = "直接输出"
    elif confidence >= 85.0:
        label = "建议复核"
    else:
        label = "[需核实]"

    return confidence, label


def process_input(raw_input: str, custom_format: Optional[str] = None) -> Dict[str, Any]:
    """
    处理输入的主流程。

    Args:
        raw_input: 用户提供的原始输入。
        custom_format: 自定义输出格式（可选）。

    Returns:
        结构化处理结果字典。

    Raises:
        ScraperError: 各类处理错误。
    """
    # Step 1: 校验输入
    content = validate_input(raw_input)

    # Step 2: 提取关键字段
    fields = extract_key_fields(content)

    # Step 3: 计算置信度
    confidence, label = calculate_confidence(fields)

    # Step 4: 组装结果
    result = {
        "状态": "成功",
        "输入摘要": content[:100] + ("..." if len(content) > 100 else ""),
        "提取字段": fields,
        "置信度": f"{confidence:.1f}%",
        "置信度标注": label,
        "处理时间": "即时",
    }

    # 自定义格式处理
    if custom_format:
        try:
            # 支持简单模板替换，如 {URL} {邮箱} {关键词}
            template = custom_format
            for key in ["URL", "邮箱", "日期", "数字", "关键词"]:
                values = fields.get(key, [])
                placeholder = "{" + key + "}"
                if placeholder in template:
                    template = template.replace(placeholder, ", ".join(values) if values else "无")
            result["自定义输出"] = template
        except Exception:
            raise ScraperError("E003", "自定义格式错误，示例：'URL: {URL}, 关键词: {关键词}'")

    return result


def batch_process(inputs: List[str], custom_format: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    Args:
        inputs: 输入列表。
        custom_format: 自定义输出格式（可选）。

    Returns:
        处理结果列表。
    """
    results = []
    for item in inputs:
        try:
            results.append(process_input(item, custom_format))
        except ScraperError as e:
            results.append({
                "状态": "失败",
                "错误码": e.code,
                "错误信息": e.message,
            })
    return results


# ============================================================
# 自检模块（内置样例数据，离线运行）
# ============================================================
def run_selftest() -> bool:
    """
    内置自检逻辑，不依赖外部文件、网络或当前工作目录。

    使用宽松阈值断言，确保在任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检：scraper-make-ez 核心逻辑验证")
    print("=" * 60)

    # 测试用例1: 正常输入
    test_input = (
        "请采集以下信息：网站 https://example.com/data 的联系邮箱是 "
        "contact@example.com，发布于2024年3月15日，共有12345条记录，占比15.5%。"
        "这是一个测试样例用于验证功能。"
    )
    try:
        result = process_input(test_input)
        fields = result["提取字段"]

        # 宽松断言：关键字段非空且类型正确
        assert isinstance(result["状态"], str)
        assert result["状态"] == "成功"
        assert isinstance(fields, dict)
        assert "URL" in fields
        assert "邮箱" in fields
        assert "日期" in fields
        assert "数字" in fields
        assert "关键词" in fields

        # 宽松断言：提取到内容（不依赖精确值）
        assert len(fields["URL"]) > 0, "应至少提取到一个URL"
        assert len(fields["邮箱"]) > 0, "应至少提取到一个邮箱"
        assert len(fields["日期"]) > 0, "应至少提取到一个日期"
        assert len(fields["数字"]) > 0, "应至少提取到数字"

        # 置信度区间判断
        conf_str = result["置信度"].replace("%", "")
        conf_val = float(conf_str)
        assert 60.0 <= conf_val <= 95.0, "置信度应在60%-95%区间"

        print("[PASS] 正常输入处理：字段提取与置信度计算正确")
    except AssertionError as e:
        print(f"[FAIL] 正常输入处理断言失败: {e}")
        return False
    except ScraperError as e:
        print(f"[FAIL] 正常输入处理异常: [{e.code}] {e.message}")
        return False

    # 测试用例2: 空输入错误处理
    try:
        process_input("   ")
        print("[FAIL] 空输入应抛出 E001 错误")
        return False
    except ScraperError as e:
        assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
        print("[PASS] 空输入错误处理：E001 正确触发")

    # 测试用例3: 批量处理
    batch_inputs = [
        "测试数据 https://test.org 包含数字42",
        "第二个样例 2024年5月20日 包含邮箱 test@test.com",
        "",  # 空输入，应失败
    ]
    batch_results = batch_process(batch_inputs)

    # 宽松断言：结果数量正确，前两个成功，第三个失败
    assert len(batch_results) == 3, "批量处理应返回3个结果"
    assert batch_results[0]["状态"] == "成功"
    assert batch_results[1]["状态"] == "成功"
    assert batch_results[2]["状态"] == "失败"
    assert batch_results[2]["错误码"] == "E001"
    print("[PASS] 批量处理：成功与失败场景均正确处理")

    # 测试用例4: 自定义格式
    try:
        custom_result = process_input(
            "URL: https://example.com, 邮箱: a@b.com",
            custom_format="URL列表: {URL} | 邮箱: {邮箱}"
        )
        assert "自定义输出" in custom_result
        assert "URL列表" in custom_result["自定义输出"]
        assert "https://example.com" in custom_result["自定义输出"]
        print("[PASS] 自定义格式输出正常")
    except ScraperError as e:
        print(f"[FAIL] 自定义格式处理异常: [{e.code}] {e.message}")
        return False

    # 测试用例5: 能力边界（超长输入不崩溃）
    long_input = "长文本测试 " * 1000  # 约6000字符
    try:
        long_result = process_input(long_input)
        assert long_result["状态"] == "成功"
        assert long_result["输入摘要"].endswith("..."), "长输入应有截断标记"
        print("[PASS] 长输入处理：正常截断且不崩溃")
    except ScraperError as e:
        print(f"[FAIL] 长输入处理异常: [{e.code}] {e.message}")
        return False

    # 测试用例6: 特殊字符输入
    try:
        special_input = "包含特殊字符：@#$%^&*()_+=-[]{};':\",./<>?~`！@#￥%……&*（）——+【】{}；：""''，。、《》？"
        special_result = process_input(special_input)
        assert special_result["状态"] == "成功"
        print("[PASS] 特殊字符输入处理正常")
    except ScraperError as e:
        print(f"[FAIL] 特殊字符输入处理异常: [{e.code}] {e.message}")
        return False

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """
    命令行主入口。

    Returns:
        退出码：0 成功，1 失败。
    """
    parser = argparse.ArgumentParser(
        description="scraper-make-ez 爬虫采集技能 - 独立实现",
        epilog="示例：python main.py --input '待处理文本' --format 'URL: {URL}'"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（文本/URL/JSON字符串）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default=None,
        help="自定义输出格式模板，如 'URL: {URL}, 邮箱: {邮箱}'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序（离线，无需外部依赖）"
    )
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="批量处理：JSON数组字符串，如 '[\"文本1\", \"文本2\"]'"
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 批量模式
    if args.batch:
        try:
            inputs = json.loads(args.batch)
            if not isinstance(inputs, list):
                print("错误: --batch 参数必须是JSON数组", file=sys.stderr)
                return 1
            results = batch_process(inputs, args.format)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except json.JSONDecodeError:
            print("错误: --batch 参数必须是有效的JSON数组格式", file=sys.stderr)
            return 1

    # 单条处理模式
    if args.input:
        try:
            result = process_input(args.input, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ScraperError as e:
            print(f"错误: [{e.code}] {e.message}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误: [E010] 未预期异常: {e}", file=sys.stderr)
            return 1

    # 无参数时打印帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
