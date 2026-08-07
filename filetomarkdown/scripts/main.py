#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filetomarkdown: 将用户提供的文件或链接转为结构化 Markdown，保留关键信息并标注置信度。
版本: 1.0.1
仅依据功能规格独立实现（clean-room）。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# 错误码定义
ERR_OK = 0
ERR_INPUT = "E001"       # 输入参数无效
ERR_FILE_NOT_FOUND = "E002"  # 文件不存在
ERR_FILE_TOO_LARGE = "E003"  # 文件超过大小限制
ERR_UNSUPPORTED_TYPE = "E004" # 不支持的文件类型
ERR_PARSE_FAILED = "E005"   # 内容解析失败
ERR_NETWORK = "E006"       # 网络访问失败
ERR_OUTPUT = "E007"        # 输出写入失败
ERR_INTERNAL = "E008"      # 内部逻辑错误
ERR_SELFTEST = "E009"      # 自检失败
ERR_URL_INVALID = "E010"   # URL 无效

# 常量
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".json"}
DEFAULT_CONFIDENCE = 0.95
LOW_CONFIDENCE = 0.6


class FileToMarkdownError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------- 核心解析函数 ----------

def parse_text_content(content: str) -> dict:
    """
    解析纯文本内容，提取段落、标题等。
    返回包含结构化信息的字典。
    """
    if not content or not content.strip():
        return {"title": "空文档", "paragraphs": [], "headings": [], "confidence": LOW_CONFIDENCE}

    lines = content.splitlines()
    headings = []
    paragraphs = []
    current_para = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue
        # 识别简单标题（以 # 开头）
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip())
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue
        current_para.append(stripped)

    if current_para:
        paragraphs.append(" ".join(current_para))

    # 提取可能的标题（第一行非空且较短）
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            if len(stripped) <= 80 and not stripped.startswith("#"):
                title = stripped
            break

    return {
        "title": title or "未命名文档",
        "headings": headings,
        "paragraphs": paragraphs,
        "confidence": DEFAULT_CONFIDENCE if len(paragraphs) > 0 else LOW_CONFIDENCE
    }


def parse_csv_content(content: str) -> dict:
    """解析 CSV 内容为表格结构"""
    try:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return {"title": "空CSV", "headers": [], "rows": [], "confidence": LOW_CONFIDENCE}
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
        return {
            "title": "CSV表格",
            "headers": headers,
            "rows": data_rows,
            "confidence": DEFAULT_CONFIDENCE if data_rows else LOW_CONFIDENCE
        }
    except Exception as e:
        raise FileToMarkdownError(ERR_PARSE_FAILED, f"CSV解析失败: {str(e)}")


def parse_json_content(content: str) -> dict:
    """解析 JSON 内容为结构化数据"""
    try:
        data = json.loads(content)
        # 简单处理：将 JSON 转为可读的 Markdown 结构
        if isinstance(data, dict):
            items = []
            for key, value in data.items():
                items.append({"key": key, "value": value})
            return {
                "title": "JSON文档",
                "items": items,
                "confidence": DEFAULT_CONFIDENCE
            }
        elif isinstance(data, list):
            return {
                "title": "JSON数组",
                "items": data,
                "confidence": DEFAULT_CONFIDENCE
            }
        else:
            return {
                "title": "JSON值",
                "value": data,
                "confidence": DEFAULT_CONFIDENCE
            }
    except Exception as e:
        raise FileToMarkdownError(ERR_PARSE_FAILED, f"JSON解析失败: {str(e)}")


def parse_file(file_path: str) -> dict:
    """根据文件扩展名解析文件内容"""
    path = Path(file_path)

    if not path.exists():
        raise FileToMarkdownError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise FileToMarkdownError(ERR_FILE_TOO_LARGE, f"文件超过10MB限制: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise FileToMarkdownError(ERR_UNSUPPORTED_TYPE, f"不支持的文件类型: {ext}")

    try:
        if ext == ".txt":
            content = path.read_text(encoding="utf-8", errors="replace")
            return parse_text_content(content)
        elif ext == ".csv":
            content = path.read_text(encoding="utf-8", errors="replace")
            return parse_csv_content(content)
        elif ext == ".json":
            content = path.read_text(encoding="utf-8", errors="replace")
            return parse_json_content(content)
        elif ext == ".pdf":
            # 简化处理：PDF 无法直接解析文本层，返回提示
            return {
                "title": path.stem,
                "note": "PDF文件需额外库支持文本提取",
                "confidence": LOW_CONFIDENCE
            }
        elif ext == ".docx":
            # 简化处理：DOCX 无法直接解析
            return {
                "title": path.stem,
                "note": "DOCX文件需额外库支持文本提取",
                "confidence": LOW_CONFIDENCE
            }
        else:
            raise FileToMarkdownError(ERR_UNSUPPORTED_TYPE, f"不支持的文件类型: {ext}")
    except FileToMarkdownError:
        raise
    except Exception as e:
        raise FileToMarkdownError(ERR_PARSE_FAILED, f"文件解析失败: {str(e)}")


def fetch_url_content(url: str) -> str:
    """从 URL 获取文本内容"""
    if not url.startswith(("http://", "https://")):
        raise FileToMarkdownError(ERR_URL_INVALID, f"无效的URL: {url}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            # 只读取部分内容避免过大
            content = response.read(MAX_FILE_SIZE).decode("utf-8", errors="replace")
            return content
    except urllib.error.URLError as e:
        raise FileToMarkdownError(ERR_NETWORK, f"网络访问失败: {str(e)}")
    except Exception as e:
        raise FileToMarkdownError(ERR_NETWORK, f"URL访问异常: {str(e)}")


def extract_text_from_html(html: str) -> str:
    """从 HTML 中提取纯文本（简化实现）"""
    # 移除 script 和 style 标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 移除标签
    text = re.sub(r'<[^>]+>', ' ', text)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def process_url(url: str) -> dict:
    """处理 URL 输入"""
    html = fetch_url_content(url)
    text = extract_text_from_html(html)
    if not text:
        return {"title": url, "note": "未提取到文本内容", "confidence": LOW_CONFIDENCE}
    parsed = parse_text_content(text)
    parsed["title"] = parsed["title"] or url
    return parsed


def process_text(text: str) -> dict:
    """处理纯文本输入"""
    return parse_text_content(text)


# ---------- Markdown 生成 ----------

def dict_to_markdown(data: dict) -> str:
    """将解析结果转为 Markdown 字符串"""
    md_lines = []
    md_lines.append(f"# {data.get('title', '未命名文档')}")
    md_lines.append("")

    confidence = data.get("confidence", LOW_CONFIDENCE)
    md_lines.append(f"> 置信度: {confidence:.2f}")
    md_lines.append("")

    # 处理标题
    headings = data.get("headings", [])
    if headings:
        md_lines.append("## 目录")
        for i, h in enumerate(headings, 1):
            md_lines.append(f"{i}. {h}")
        md_lines.append("")

    # 处理段落
    paragraphs = data.get("paragraphs", [])
    if paragraphs:
        md_lines.append("## 正文")
        for p in paragraphs:
            md_lines.append(p)
            md_lines.append("")

    # 处理 CSV 表格
    if "headers" in data and "rows" in data:
        headers = data["headers"]
        rows = data["rows"]
        if headers:
            md_lines.append("## 表格数据")
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("|" + "---|" * len(headers))
            for row in rows:
                # 填充不足的列
                padded = row + [""] * (len(headers) - len(row))
                md_lines.append("| " + " | ".join(padded[:len(headers)]) + " |")
            md_lines.append("")

    # 处理 JSON
    if "items" in data:
        md_lines.append("## 数据项")
        items = data["items"]
        if isinstance(items, list) and items and isinstance(items[0], dict):
            # 键值对列表
            md_lines.append("| 键 | 值 |")
            md_lines.append("|---|---|")
            for item in items:
                key = item.get("key", "")
                value = item.get("value", "")
                md_lines.append(f"| {key} | {value} |")
        else:
            for item in items:
                md_lines.append(f"- {item}")
        md_lines.append("")

    # 处理备注
    note = data.get("note", "")
    if note:
        md_lines.append(f"> 备注: {note}")
        md_lines.append("")

    return "\n".join(md_lines)


def convert_to_markdown(input_source: str, input_type: str = "auto") -> str:
    """统一入口：根据输入类型转换"""
    if input_type == "file":
        data = parse_file(input_source)
    elif input_type == "url":
        data = process_url(input_source)
    elif input_type == "text":
        data = process_text(input_source)
    elif input_type == "auto":
        # 自动判断：文件路径存在则按文件处理，否则按文本处理
        if os.path.exists(input_source):
            data = parse_file(input_source)
        elif input_source.startswith(("http://", "https://")):
            data = process_url(input_source)
        else:
            data = process_text(input_source)
    else:
        raise FileToMarkdownError(ERR_INPUT, f"无效的输入类型: {input_type}")

    return dict_to_markdown(data)


# ---------- 自检功能 ----------

def run_selftest() -> bool:
    """内置硬编码样例数据，离线自检核心逻辑"""
    print("开始自检...")

    # 测试1: 文本解析
    test_text = "这是一个测试文档\n# 第一章\n这是第一段内容。\n\n# 第二章\n这是第二段内容，包含更多文字。"
    try:
        result = parse_text_content(test_text)
        assert len(result["headings"]) >= 1, "标题解析失败"
        assert len(result["paragraphs"]) >= 1, "段落解析失败"
        assert result["confidence"] > 0.5, "置信度异常"
        print("✓ 文本解析测试通过")
    except AssertionError as e:
        print(f"✗ 文本解析测试失败: {e}")
        return False

    # 测试2: CSV 解析
    test_csv = "姓名,年龄,城市\n张三,25,北京\n李四,30,上海"
    try:
        result = parse_csv_content(test_csv)
        assert len(result["headers"]) == 3, "CSV表头解析失败"
        assert len(result["rows"]) == 2, "CSV行解析失败"
        print("✓ CSV解析测试通过")
    except AssertionError as e:
        print(f"✗ CSV解析测试失败: {e}")
        return False

    # 测试3: JSON 解析
    test_json = '{"name": "测试", "version": 1}'
    try:
        result = parse_json_content(test_json)
        assert len(result["items"]) == 2, "JSON键值对解析失败"
        print("✓ JSON解析测试通过")
    except AssertionError as e:
        print(f"✗ JSON解析测试失败: {e}")
        return False

    # 测试4: Markdown 生成
    try:
        test_data = {
            "title": "测试文档",
            "headings": ["标题1", "标题2"],
            "paragraphs": ["段落内容"],
            "confidence": 0.9
        }
        md = dict_to_markdown(test_data)
        assert "# 测试文档" in md, "Markdown标题缺失"
        assert "置信度" in md, "置信度标注缺失"
        print("✓ Markdown生成测试通过")
    except AssertionError as e:
        print(f"✗ Markdown生成测试失败: {e}")
        return False

    # 测试5: 完整转换流程
    try:
        md = convert_to_markdown(test_text, "text")
        assert len(md) > 10, "转换结果过短"
        print("✓ 完整转换流程测试通过")
    except AssertionError as e:
        print(f"✗ 完整转换流程测试失败: {e}")
        return False

    # 测试6: 错误处理
    try:
        parse_file("/nonexistent/file.txt")
        print("✗ 错误处理测试失败: 未抛出异常")
        return False
    except FileToMarkdownError as e:
        assert e.code == ERR_FILE_NOT_FOUND, "错误码不正确"
        print("✓ 错误处理测试通过")

    print("全部自检通过！")
    return True


# ---------- 主程序 ----------

def main():
    parser = argparse.ArgumentParser(
        description="filetomarkdown - 文档转写格式转换工具",
        epilog="示例: python main.py input.txt -o output.md"
    )
    parser.add_argument("input", nargs="?", help="输入文件路径、URL或文本")
    parser.add_argument("-t", "--type", choices=["file", "url", "text", "auto"],
                        default="auto", help="输入类型 (默认: auto)")
    parser.add_argument("-o", "--output", help="输出Markdown文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 需要输入参数
    if not args.input:
        parser.print_help()
        print("\n错误: 需要提供输入内容", file=sys.stderr)
        sys.exit(1)

    try:
        # 执行转换
        md_content = convert_to_markdown(args.input, args.type)

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(md_content)
                print(f"已输出到: {args.output}")
            except Exception as e:
                raise FileToMarkdownError(ERR_OUTPUT, f"输出文件写入失败: {str(e)}")
        else:
            print(md_content)

    except FileToMarkdownError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 [{ERR_INTERNAL}]: 未预期异常: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
