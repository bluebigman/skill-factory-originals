#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filetomarkdown: 将用户提供的文件或链接转为结构化 Markdown，保留关键信息并标注置信度。
版本: 1.1.0
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
import time
from datetime import datetime, timezone

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
_retry_timeout = 10  # 请求超时时间（秒）

def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。
    仅对可重试错误（网络错误、5xx、超时）进行退避重试。
    """
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except urllib.error.HTTPError as e:
            # HTTP错误：仅对5xx重试
            if e.code >= 500 and attempt < _max_retry - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # 网络错误/超时：重试
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception as e:
            # 其他异常不重试
            raise

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

    # 改进的标题正则：支持 # 后无空格的标准 Markdown ATX 标题
    heading_pattern = re.compile(r'^#{1,6}\s*(.*)$')

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue
        # 识别标题（支持 # 后无空格）
        heading_match = heading_pattern.match(stripped)
        if heading_match:
            headings.append(heading_match.group(1).strip())
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
            if len(stripped) <= 80 and not heading_pattern.match(stripped):
                title = stripped
            break

    return {
        "title": title or "未命名文档",
        "headings": headings,
        "paragraphs": paragraphs,
        "confidence": DEFAULT_CONFIDENCE if len(paragraphs) > 0 else LOW_CONFIDENCE
    }


def parse_pdf_content(file_path: str) -> dict:
    """解析 PDF 文件内容（使用 PyPDF2）"""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise FileToMarkdownError(ERR_PARSE_FAILED, "PDF解析需要安装PyPDF2库: pip install PyPDF2")

    try:
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        content = "\n".join(text_parts)
        if not content.strip():
            return {
                "title": Path(file_path).stem,
                "note": "PDF文件未提取到文本内容（可能为扫描件）",
                "confidence": LOW_CONFIDENCE
            }
        result = parse_text_content(content)
        result["title"] = result["title"] or Path(file_path).stem
        return result
    except FileToMarkdownError:
        raise
    except Exception as e:
        raise FileToMarkdownError(ERR_PARSE_FAILED, f"PDF解析失败: {str(e)}")


def parse_docx_content(file_path: str) -> dict:
    """解析 DOCX 文件内容（使用 python-docx）"""
    try:
        import docx
    except ImportError:
        raise FileToMarkdownError(ERR_PARSE_FAILED, "DOCX解析需要安装python-docx库: pip install python-docx")

    try:
        doc = docx.Document(file_path)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        content = "\n".join(text_parts)
        if not content.strip():
            return {
                "title": Path(file_path).stem,
                "note": "DOCX文件未提取到文本内容",
                "confidence": LOW_CONFIDENCE
            }
        result = parse_text_content(content)
        result["title"] = result["title"] or Path(file_path).stem
        return result
    except FileToMarkdownError:
        raise
    except Exception as e:
        raise FileToMarkdownError(ERR_PARSE_FAILED, f"DOCX解析失败: {str(e)}")


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
            return parse_pdf_content(file_path)
        elif ext == ".docx":
            return parse_docx_content(file_path)
        else:
            raise FileToMarkdownError(ERR_UNSUPPORTED_TYPE, f"不支持的文件类型: {ext}")
    except FileToMarkdownError:
        raise
    except Exception as e:
        raise FileToMarkdownError(ERR_PARSE_FAILED, f"文件解析失败: {str(e)}")


def fetch_url_content(url: str) -> str:
    """从 URL 获取文本内容（带超时和重试退避）"""
    if not url.startswith(("http://", "https://")):
        raise FileToMarkdownError(ERR_URL_INVALID, f"无效的URL: {url}")

    def _fetch():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=_retry_timeout) as response:
            # 只读取部分内容避免过大
            content = response.read(MAX_FILE_SIZE).decode("utf-8", errors="replace")
            return content

    try:
        return _retry_request(_fetch)
    except urllib.error.HTTPError as e:
        raise FileToMarkdownError(ERR_NETWORK, f"HTTP错误 {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise FileToMarkdownError(ERR_NETWORK, f"网络访问失败: {str(e.reason)}")
    except TimeoutError:
        raise FileToMarkdownError(ERR_NETWORK, f"请求超时（{_retry_timeout}秒）")
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
    all_passed = True

    # 测试1: 空文档解析
    try:
        result = parse_text_content("")
        assert result["title"] == "空文档", "空文档标题错误"
        assert result["confidence"] == LOW_CONFIDENCE, "空文档置信度错误"
        print("✓ 空文档解析测试通过")
    except AssertionError as e:
        print(f"✗ 空文档解析测试失败: {e}")
        all_passed = False

    # 测试2: 标题解析（含无空格变体）
    test_text = "# 一级标题\n##二级标题\n### 三级标题\n\n这是第一段内容。\n\n这是第二段内容。"
    try:
        result = parse_text_content(test_text)
        assert len(result["headings"]) == 3, f"标题解析失败: {result['headings']}"
        assert result["headings"][0] == "一级标题", "一级标题错误"
        assert result["headings"][1] == "二级标题", "二级标题错误（无空格变体）"
        assert result["headings"][2] == "三级标题", "三级标题错误"
        assert len(result["paragraphs"]) == 2, "段落解析失败"
        print("✓ 标题解析测试通过（含无空格变体）")
    except AssertionError as e:
        print(f"✗ 标题解析测试失败: {e}")
        all_passed = False

    # 测试3: CSV 解析
    test_csv = "姓名,年龄,城市\n张三,25,北京\n李四,30,上海"
    try:
        result = parse_csv_content(test_csv)
        assert len(result["headers"]) == 3, "CSV表头解析失败"
        assert len(result["rows"]) == 2, "CSV行解析失败"
        print("✓ CSV解析测试通过")
    except AssertionError as e:
        print(f"✗ CSV解析测试失败: {e}")
