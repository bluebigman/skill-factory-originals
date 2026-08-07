#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gstack - 数据整理、结构化转换、批量处理
版本: 1.0.1 (clean-room 独立实现)
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERR_INVALID_INPUT = "E001"      # 输入数据无效
ERR_INVALID_FORMAT = "E002"     # 输出格式不支持
ERR_INVALID_URL = "E003"        # URL 格式错误
ERR_FIELD_MISSING = "E004"      # 字段缺失
ERR_BATCH_EMPTY = "E005"        # 批量处理列表为空
ERR_JSON_DECODE = "E006"        # JSON 解析失败
ERR_CSV_PARSE = "E007"          # CSV 解析失败
ERR_INTERNAL = "E008"           # 内部错误
ERR_SELFTEST_FAIL = "E009"      # 自检失败
ERR_UNKNOWN = "E010"            # 未知错误


def _make_error(code: str, message: str) -> Dict[str, str]:
    """构造标准错误结构。"""
    return {"error_code": code, "error_message": message}


def _validate_text_input(data: Any) -> Tuple[bool, str]:
    """校验输入是否为有效文本。"""
    if data is None:
        return False, "输入数据为空"
    if not isinstance(data, str):
        return False, "输入必须是字符串类型"
    if not data.strip():
        return False, "输入内容为空"
    return True, ""


def _extract_email(text: str) -> List[str]:
    """从文本中提取电子邮件地址。"""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


def _extract_url(text: str) -> List[str]:
    """从文本中提取 URL。"""
    pattern = r"https?://[^\s<>\"']+"
    return list(set(re.findall(pattern, text)))


def _extract_phone(text: str) -> List[str]:
    """从文本中提取电话号码（宽松匹配）。"""
    pattern = r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}(?!\d)"
    return list(set(re.findall(pattern, text)))


def _extract_dates(text: str) -> List[str]:
    """从文本中提取日期（支持常见格式）。"""
    patterns = [
        r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",
        r"\d{4}年\d{1,2}月\d{1,2}日",
        r"\d{1,2}月\d{1,2}日",
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text))
    return list(set(results))


def _calculate_confidence(extracted_count: int, total_checks: int) -> float:
    """根据提取成功率计算置信度。"""
    if total_checks <= 0:
        return 0.0
    ratio = extracted_count / total_checks
    if ratio >= 0.8:
        return 0.95
    if ratio >= 0.5:
        return 0.75
    if ratio >= 0.2:
        return 0.5
    return 0.25


def _parse_json_content(content: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
    """尝试解析 JSON 内容。"""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data, None
        return {"data": data}, None
    except json.JSONDecodeError:
        return None, _make_error(ERR_JSON_DECODE, "JSON 解析失败")


def _parse_csv_content(content: str) -> Tuple[Optional[List[Dict[str, str]]], Optional[Dict[str, str]]]:
    """尝试解析 CSV 内容。"""
    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = [row for row in reader if any(row.values())]
        if not rows:
            return [], None
        return rows, None
    except Exception:
        return None, _make_error(ERR_CSV_PARSE, "CSV 解析失败")


def _detect_content_type(content: str) -> str:
    """检测内容类型。"""
    stripped = content.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    if "," in stripped.split("\n")[0] and "\n" in stripped:
        return "csv"
    return "text"


def _transform_to_structured(content: str) -> Dict[str, Any]:
    """将文本内容转换为结构化结果。"""
    valid, msg = _validate_text_input(content)
    if not valid:
        return _make_error(ERR_INVALID_INPUT, msg)

    content_type = _detect_content_type(content)

    # 初始化结果结构
    result: Dict[str, Any] = {
        "content_type": content_type,
        "extracted": {},
        "statistics": {},
        "confidence": 0.0,
        "processed_at": datetime.utcnow().isoformat() + "Z",
    }

    # 提取各类信息
    emails = _extract_email(content)
    urls = _extract_url(content)
    phones = _extract_phone(content)
    dates = _extract_dates(content)

    # 根据内容类型决定是否保留原始解析
    if content_type == "json":
        parsed, err = _parse_json_content(content)
        if err:
            result["parse_error"] = err
        else:
            result["parsed_json"] = parsed
    elif content_type == "csv":
        parsed, err = _parse_csv_content(content)
        if err:
            result["parse_error"] = err
        else:
            result["parsed_csv"] = parsed

    # 填充提取结果
    result["extracted"]["emails"] = emails
    result["extracted"]["urls"] = urls
    result["extracted"]["phones"] = phones
    result["extracted"]["dates"] = dates

    # 统计信息
    result["statistics"] = {
        "total_length": len(content),
        "line_count": len(content.splitlines()),
        "email_count": len(emails),
        "url_count": len(urls),
        "phone_count": len(phones),
        "date_count": len(dates),
    }

    # 计算置信度
    checks = [
        len(emails) > 0,
        len(urls) > 0,
        len(phones) > 0,
        len(dates) > 0,
    ]
    result["confidence"] = _calculate_confidence(sum(checks), len(checks))

    return result


def _format_output(data: Dict[str, Any], output_format: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """按指定格式输出结果。"""
    if output_format == "json":
        try:
            return json.dumps(data, ensure_ascii=False, indent=2), None
        except Exception:
            return None, _make_error(ERR_INTERNAL, "JSON 序列化失败")

    if output_format == "csv":
        try:
            # 扁平化提取结果用于 CSV 输出
            output = io.StringIO()
            writer = csv.writer(output)

            # 写头部
            headers = ["field", "value"]
            writer.writerow(headers)

            # 写提取结果
            for category, values in data.get("extracted", {}).items():
                for value in values:
                    writer.writerow([category, value])

            # 写统计信息
            for key, value in data.get("statistics", {}).items():
                writer.writerow([f"stat_{key}", str(value)])

            writer.writerow(["confidence", str(data.get("confidence", 0))])
            return output.getvalue(), None
        except Exception:
            return None, _make_error(ERR_INTERNAL, "CSV 序列化失败")

    if output_format == "markdown":
        try:
            lines = []
            lines.append(f"# 数据整理结果")
            lines.append(f"- **内容类型**: {data.get('content_type', '未知')}")
            lines.append(f"- **置信度**: {data.get('confidence', 0):.2f}")
            lines.append(f"- **处理时间**: {data.get('processed_at', '未知')}")
            lines.append("")
            lines.append("## 提取结果")
            lines.append("")
            lines.append("| 类别 | 值 |")
            lines.append("|------|-----|")
            for category, values in data.get("extracted", {}).items():
                for value in values:
                    lines.append(f"| {category} | {value} |")
            lines.append("")
            lines.append("## 统计信息")
            lines.append("")
            for key, value in data.get("statistics", {}).items():
                lines.append(f"- {key}: {value}")
            return "\n".join(lines), None
        except Exception:
            return None, _make_error(ERR_INTERNAL, "Markdown 生成失败")

    return None, _make_error(ERR_INVALID_FORMAT, f"不支持的输出格式: {output_format}")


def _process_batch(items: List[str], output_format: str = "json") -> Dict[str, Any]:
    """批量处理多个输入项。"""
    if not items:
        return _make_error(ERR_BATCH_EMPTY, "批量处理列表为空")

    results = []
    for item in items:
        # 检查是否为 URL
        if item.startswith(("http://", "https://")):
            # 检查 URL 格式
            parsed = urllib.parse.urlparse(item)
            if not parsed.netloc:
                results.append(_make_error(ERR_INVALID_URL, f"URL 格式无效: {item}"))
                continue
            # 仅做格式校验，不实际访问网络
            results.append({
                "source": item,
                "type": "url",
                "note": "URL 内容需另行获取（本技能不访问网络）",
            })
        else:
            # 作为文本处理
            structured = _transform_to_structured(item)
            structured["source"] = item
            results.append(structured)

    # 汇总结果
    summary = {
        "total_items": len(items),
        "success_count": sum(1 for r in results if "error_code" not in r),
        "error_count": sum(1 for r in results if "error_code" in r),
    }

    batch_result = {
        "batch": results,
        "summary": summary,
    }

    formatted, err = _format_output(batch_result, output_format)
    if err:
        return err
    return {"output": formatted}


def _run_selftest() -> Tuple[bool, str]:
    """运行内置自检。"""
    # 测试样例数据
    test_cases = [
        # (输入文本, 预期包含的字段)
        (
            "联系人: 张三 (zhangsan@example.com), 电话: 138-1234-5678\n"
            "网址: https://example.com/page?q=test\n"
            "日期: 2024-01-15 和 2024年3月20日",
            ["emails", "urls", "phones", "dates"]
        ),
        (
            "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai",
            ["parsed_csv"]
        ),
        (
            '{"name": "test", "value": 123, "items": [1, 2, 3]}',
            ["parsed_json"]
        ),
        (
            "纯文本内容，没有特殊信息",
            ["emails", "urls", "phones", "dates"]
        ),
    ]

    try:
        # 测试 1: 基本文本提取
        for idx, (text, expected_fields) in enumerate(test_cases):
            result = _transform_to_structured(text)
            if "error_code" in result:
                return False, f"自检失败 (用例{idx+1}): 返回错误 {result['error_code']}"

            # 验证提取字段存在
            for field in expected_fields:
                if field not in result and field not in result.get("extracted", {}):
                    return False, f"自检失败 (用例{idx+1}): 缺少字段 {field}"

            # 验证置信度在合理范围
            if not (0 <= result.get("confidence", -1) <= 1):
                return False, f"自检失败 (用例{idx+1}): 置信度超出范围"

            # 验证统计信息合理
            stats = result.get("statistics", {})
            if stats.get("total_length", 0) <= 0:
                return False, f"自检失败 (用例{idx+1}): 文本长度统计异常"

        # 测试 2: 输出格式
        test_result = _transform_to_structured(test_cases[0][0])
        for fmt in ["json", "csv", "markdown"]:
            output, err = _format_output(test_result, fmt)
            if err:
                return False, f"自检失败: 格式 {fmt} 输出错误 {err['error_code']}"
            if output is None or len(output) == 0:
                return False, f"自检失败: 格式 {fmt} 输出为空"

        # 测试 3: 批量处理
        batch_result = _process_batch(
            ["test@example.com", "https://example.com", "普通文本"],
            "json"
        )
        if "error_code" in batch_result:
            return False, f"自检失败: 批量处理错误 {batch_result['error_code']}"
        if "output" not in batch_result:
            return False, "自检失败: 批量处理缺少输出"

        # 测试 4: 错误处理
        bad_result = _transform_to_structured("")
        if "error_code" not in bad_result:
            return False, "自检失败: 空输入未返回错误"

        # 测试 5: 无效格式
        _, err = _format_output({}, "xml")
        if err is None or err.get("error_code") != ERR_INVALID_FORMAT:
            return False, "自检失败: 无效格式未返回正确错误码"

        return True, "所有自检通过"

    except Exception as e:
        return False, f"自检异常: {str(e)}"


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="gstack - 数据整理、结构化转换、批量处理工具",
        epilog="示例: python main.py --input '文本内容' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入文本内容")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径")
    parser.add_argument("--format", "-F", type=str, default="json",
                        choices=["json", "csv", "markdown"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--batch", "-b", action="store_true",
                        help="批量处理模式（输入以换行分隔）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    parser.add_argument("--version", "-v", action="version",
                        version="gstack 1.0.1 (clean-room)")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success, message = _run_selftest()
        print(f"[SELFTEST] {'通过' if success else '失败'}: {message}")
        return 0 if success else 1

    # 获取输入内容
    content = None
    if args.input:
        content = args.input
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(json.dumps(_make_error(ERR_INTERNAL, f"无法读取文件: {str(e)}"),
                           ensure_ascii=False))
            return 1
    else:
        # 从标准输入读取
        try:
            content = sys.stdin.read()
        except Exception:
            print(json.dumps(_make_error(ERR_INVALID_INPUT, "无法读取标准输入"),
                           ensure_ascii=False))
            return 1

    # 处理输入
    try:
        if args.batch:
            # 批量模式：按行分割
            items = [line.strip() for line in content.splitlines() if line.strip()]
            result = _process_batch(items, args.format)
        else:
            # 单条模式
            structured = _transform_to_structured(content)
            output, err = _format_output(structured, args.format)
            if err:
                print(json.dumps(err, ensure_ascii=False))
                return 1
            result = {"output": output}

        # 输出结果
        if "output" in result:
            print(result["output"])
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except Exception as e:
        error = _make_error(ERR_UNKNOWN, f"处理过程中发生错误: {str(e)}")
        print(json.dumps(error, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
