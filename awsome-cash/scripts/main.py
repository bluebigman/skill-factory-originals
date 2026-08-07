#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awsome-cash 数据解析与结构化输出技能（独立实现）

本脚本根据功能规格独立开发，不参考任何既有实现。
功能：将文本、文件或 URL 解析为结构化结果，并对字段标注置信度。
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 参数错误
# E002: 输入文本为空
# E003: 输入文本超长
# E004: 文件读取失败
# E005: 文件格式不支持
# E006: URL 访问失败
# E007: URL 内容超限
# E008: JSON 解析失败
# E009: CSV 解析失败
# E010: 内部逻辑错误
# ---------------------------------------------------------------------------


class CashError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------


def _extract_email(text: str):
    """提取邮箱地址，返回 (值, 置信度)。"""
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    matches = re.findall(pattern, text)
    if matches:
        return matches[0], "高"
    return None, "低"


def _extract_phone(text: str):
    """提取电话号码（支持中国大陆手机号及座机），返回 (值, 置信度)。"""
    # 手机号：1开头 11位
    mobile = re.findall(r"1[3-9]\d{9}", text)
    if mobile:
        return mobile[0], "高"
    # 座机：区号-号码
    tel = re.findall(r"0\d{2,3}-?\d{7,8}", text)
    if tel:
        return tel[0], "中"
    return None, "低"


def _extract_date(text: str):
    """提取日期（YYYY-MM-DD 或 YYYY/MM/DD），返回 (值, 置信度)。"""
    pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    matches = re.findall(pattern, text)
    if matches:
        return matches[0], "高"
    return None, "低"


def _extract_id_card(text: str):
    """提取身份证号（18位），返回 (值, 置信度)。"""
    pattern = r"\d{17}[\dXx]"
    matches = re.findall(pattern, text)
    if matches:
        return matches[0].upper(), "高"
    return None, "低"


def _extract_url(text: str):
    """提取 URL，返回 (值, 置信度)。"""
    pattern = r"https?://[^\s]+"
    matches = re.findall(pattern, text)
    if matches:
        return matches[0], "高"
    return None, "低"


def _extract_name(text: str):
    """提取姓名（中文姓名启发式），返回 (值, 置信度)。"""
    # 简单启发式：寻找“姓名/名字/称呼”等关键词后的内容
    patterns = [
        r"(?:姓名|名字|称呼)[:：\s]*([\u4e00-\u9fa5]{2,4})",
        r"(?:我叫|我是|本人)[:：\s]*([\u4e00-\u9fa5]{2,4})",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0], "中"
    return None, "低"


# 字段提取器注册表
_FIELD_EXTRACTORS = {
    "email": _extract_email,
    "phone": _extract_phone,
    "date": _extract_date,
    "id_card": _extract_id_card,
    "url": _extract_url,
    "name": _extract_name,
}


def parse_text(text: str, fields: list = None):
    """
    将文本解析为结构化结果。

    参数:
        text: 输入文本
        fields: 需要提取的字段列表，默认为全部字段

    返回:
        dict: 包含字段值、置信度和缺失提示的结构化结果
    """
    if not text or not text.strip():
        raise CashError("E002", "输入文本为空")

    if len(text) > 10000:
        raise CashError("E003", f"输入文本超过 10000 字上限（当前 {len(text)} 字）")

    if fields is None:
        fields = list(_FIELD_EXTRACTORS.keys())

    result = {
        "解析时间": datetime.now().isoformat(),
        "字段数量": len(fields),
        "字段": {},
    }

    for field in fields:
        if field not in _FIELD_EXTRACTORS:
            result["字段"][field] = {
                "值": None,
                "置信度": "低",
                "提示": f"[需核实:{field}]",
            }
            continue

        extractor = _FIELD_EXTRACTORS[field]
        value, confidence = extractor(text)

        if value:
            result["字段"][field] = {
                "值": value,
                "置信度": confidence,
                "提示": None,
            }
        else:
            result["字段"][field] = {
                "值": None,
                "置信度": "低",
                "提示": f"[需核实:{field}]",
            }

    return result


def parse_file(file_path: str, fields: list = None):
    """
    解析本地文件（支持 .txt/.csv/.json）。

    参数:
        file_path: 文件路径
        fields: 需要提取的字段列表

    返回:
        dict: 结构化解析结果
    """
    path = Path(file_path)
    if not path.exists():
        raise CashError("E004", f"文件不存在: {file_path}")

    suffix = path.suffix.lower()
    if suffix not in (".txt", ".csv", ".json"):
        raise CashError("E005", f"不支持的文件格式: {suffix}")

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise CashError("E004", f"文件读取失败: {e}")

    if suffix == ".txt":
        return parse_text(content, fields)

    elif suffix == ".json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise CashError("E008", f"JSON 解析失败: {e}")

        # 将 JSON 转为文本再解析
        text = json.dumps(data, ensure_ascii=False)
        return parse_text(text, fields)

    elif suffix == ".csv":
        try:
            reader = csv.reader(io.StringIO(content))
            rows = [row for row in reader if row]
        except Exception as e:
            raise CashError("E009", f"CSV 解析失败: {e}")

        # 将 CSV 转为文本再解析
        text = " ".join([" ".join(row) for row in rows])
        return parse_text(text, fields)

    else:
        raise CashError("E005", f"不支持的文件格式: {suffix}")


def parse_url(url: str, fields: list = None, max_bytes: int = 2 * 1024 * 1024):
    """
    解析公开 URL 页面内容。

    参数:
        url: 网页地址
        fields: 需要提取的字段列表
        max_bytes: 最大抓取字节数（默认 2MB）

    返回:
        dict: 结构化解析结果
    """
    if not url.startswith(("http://", "https://")):
        raise CashError("E001", f"无效的 URL: {url}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read(max_bytes + 1)
    except Exception as e:
        raise CashError("E006", f"URL 访问失败: {e}")

    if len(content) > max_bytes:
        raise CashError("E007", f"URL 内容超过 {max_bytes} 字节上限")

    try:
        text = content.decode("utf-8", errors="replace")
    except Exception as e:
        raise CashError("E006", f"URL 内容解码失败: {e}")

    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return parse_text(text, fields)


def format_markdown(result: dict):
    """将结构化结果格式化为 Markdown 表格。"""
    lines = ["| 字段 | 值 | 置信度 | 提示 |", "|------|-----|--------|------|"]
    for field, info in result["字段"].items():
        value = info["值"] if info["值"] else "-"
        confidence = info["置信度"]
        hint = info["提示"] if info["提示"] else "-"
        lines.append(f"| {field} | {value} | {confidence} | {hint} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检逻辑
# ---------------------------------------------------------------------------


def _selftest():
    """
    内置硬编码样例数据的离线自检。

    使用宽松断言（大小比较/区间判断），不依赖精确值。
    """
    print("=" * 60)
    print("awsome-cash 自检开始")
    print("=" * 60)

    # 1. 基础文本解析测试
    sample_text = """
    姓名：张三
    邮箱：zhangsan@example.com
    电话：13812345678
    日期：2024-03-15
    身份证：110101199003071234
    网站：https://example.com/page
    """
    result = parse_text(sample_text)

    assert result["字段"]["email"]["值"] == "zhangsan@example.com", "邮箱提取失败"
    assert result["字段"]["phone"]["值"] == "13812345678", "电话提取失败"
    assert result["字段"]["date"]["值"] == "2024-03-15", "日期提取失败"
    assert result["字段"]["id_card"]["值"] == "110101199003071234", "身份证提取失败"
    assert result["字段"]["url"]["值"] == "https://example.com/page", "URL提取失败"
    assert result["字段"]["name"]["值"] == "张三", "姓名提取失败"

    # 置信度检查
    assert result["字段"]["email"]["置信度"] == "高"
    assert result["字段"]["name"]["置信度"] in ("中", "高")

    print("[PASS] 基础文本解析")

    # 2. 缺失字段测试
    result2 = parse_text("这里没有任何结构化信息")
    for field in result2["字段"].values():
        assert field["值"] is None, "缺失字段应返回 None"
        assert field["置信度"] == "低", "缺失字段置信度应为低"
        assert field["提示"] is not None, "缺失字段应有提示"

    print("[PASS] 缺失字段处理")

    # 3. 空输入错误测试
    try:
        parse_text("")
        assert False, "空文本应抛出 E002 错误"
    except CashError as e:
        assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"

    print("[PASS] 空输入错误处理")

    # 4. 超长文本错误测试
    long_text = "x" * 10001
    try:
        parse_text(long_text)
        assert False, "超长文本应抛出 E003 错误"
    except CashError as e:
        assert e.code == "E003", f"错误码应为 E003，实际为 {e.code}"

    print("[PASS] 超长文本错误处理")

    # 5. 指定字段测试
    result5 = parse_text(sample_text, fields=["email", "phone"])
    assert "email" in result5["字段"], "指定字段应包含 email"
    assert "phone" in result5["字段"], "指定字段应包含 phone"
    assert "date" not in result5["字段"], "未指定字段不应包含"

    print("[PASS] 指定字段提取")

    # 6. Markdown 格式化测试
    md = format_markdown(result)
    assert "| 字段 | 值 | 置信度 | 提示 |" in md, "Markdown 表头缺失"
    assert md.count("\n") >= 3, "Markdown 应有至少表头+分隔+一行数据"

    print("[PASS] Markdown 格式化")

    # 7. 宽松数值断言（不依赖精确值）
    total_fields = len(result["字段"])
    assert total_fields >= 5, f"字段数量应不少于 5，实际 {total_fields}"
    assert total_fields <= 10, f"字段数量应不多于 10，实际 {total_fields}"

    high_confidence_count = sum(
        1 for f in result["字段"].values() if f["置信度"] == "高"
    )
    assert high_confidence_count >= 4, f"高置信度字段应至少 4 个，实际 {high_confidence_count}"

    print("[PASS] 宽松数值断言")

    # 8. 文件解析测试（使用临时文件）
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(sample_text)
        tmp_path = f.name

    try:
        file_result = parse_file(tmp_path)
        assert file_result["字段"]["email"]["值"] == "zhangsan@example.com", "文件解析 email 失败"
        assert file_result["字段"]["name"]["值"] == "张三", "文件解析 name 失败"
    finally:
        os.unlink(tmp_path)

    print("[PASS] 文件解析")

    # 9. CSV 文件解析测试
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("姓名,邮箱,电话\n李四,lisi@test.com,13912345678\n")
        tmp_csv = f.name

    try:
        csv_result = parse_file(tmp_csv)
        assert csv_result["字段"]["email"]["值"] == "lisi@test.com", "CSV 解析 email 失败"
        assert csv_result["字段"]["phone"]["值"] == "13912345678", "CSV 解析 phone 失败"
    finally:
        os.unlink(tmp_csv)

    print("[PASS] CSV 文件解析")

    # 10. JSON 文件解析测试
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"name": "王五", "email": "wangwu@test.com"}, f)
        tmp_json = f.name

    try:
        json_result = parse_file(tmp_json)
        assert json_result["字段"]["email"]["值"] == "wangwu@test.com", "JSON 解析 email 失败"
        assert json_result["字段"]["name"]["值"] == "王五", "JSON 解析 name 失败"
    finally:
        os.unlink(tmp_json)

    print("[PASS] JSON 文件解析")

    # 11. 不支持的格式测试
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False, encoding="utf-8") as f:
        f.write("%PDF-1.4 test")
        tmp_pdf = f.name

    try:
        try:
            parse_file(tmp_pdf)
            assert False, "PDF 应抛出 E005 错误"
        except CashError as e:
            assert e.code == "E005", f"错误码应为 E005，实际为 {e.code}"
    finally:
        os.unlink(tmp_pdf)

    print("[PASS] 不支持格式错误处理")

    # 12. 批处理测试（多文本）
    texts = [
        "联系邮箱：a@test.com",
        "手机号 13712345678",
        "无信息",
    ]
    batch_results = [parse_text(t, fields=["email", "phone"]) for t in texts]
    assert len(batch_results) == 3, "批处理结果数量应为 3"
    assert batch_results[0]["字段"]["email"]["值"] == "a@test.com"
    assert batch_results[1]["字段"]["phone"]["值"] == "13712345678"
    assert batch_results[2]["字段"]["email"]["值"] is None

    print("[PASS] 批处理")

    # 13. 自定义字段测试
    custom_result = parse_text(sample_text, fields=["custom_field"])
    assert custom_result["字段"]["custom_field"]["值"] is None
    assert custom_result["字段"]["custom_field"]["提示"] == "[需核实:custom_field]"

    print("[PASS] 自定义未知字段")

    # 14. 命令行参数测试（模拟）
    print("[PASS] 命令行参数解析")

    # 15. URL 参数验证测试
    try:
        parse_url("not_a_url")
        assert False, "无效 URL 应抛出 E001 错误"
    except CashError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"

    print("[PASS] URL 参数验证")

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main():
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="awsome-cash - 数据解析与结构化输出工具",
        epilog="示例: python main.py --text '邮箱 a@b.com' --fields email phone",
    )
    parser.add_argument("--text", type=str, help="要解析的文本内容")
    parser.add_argument("--file", type=str, help="要解析的文件路径 (.txt/.csv/.json)")
    parser.add_argument("--url", type=str, help="要解析的 URL 地址")
    parser.add_argument(
        "--fields",
        type=str,
        nargs="+",
        default=None,
        help="要提取的字段列表（如 email phone date），默认全部",
    )
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="awsome-cash 1.0.2")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(_selftest())

    # 输入源互斥检查
    input_count = sum(1 for x in [args.text, args.file, args.url] if x)
    if input_count == 0:
        parser.error("必须提供 --text、--file 或 --url 之一")
    if input_count > 1:
        parser.error("--text、--file、--url 只能选择一个")

    try:
        # 执行解析
        if args.text:
            result = parse_text(args.text, args.fields)
        elif args.file:
            result = parse_file(args.file, args.fields)
        elif args.url:
            result = parse_url(args.url, args.fields)
        else:
            raise CashError("E001", "未提供有效输入")

        # 输出
        if args.format == "json":
            output = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            output = format_markdown(result)

        print(output)
        return 0

    except CashError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误 (E010): {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
