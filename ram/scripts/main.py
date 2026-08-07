#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ram — 资源解析与结构化转换工具
功能：将文本、文件路径或URL内容解析为结构化结果，并标注置信度。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from urllib.parse import urlparse

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或格式无效",
    "E002": "文件不存在或无法读取",
    "E003": "URL格式无效",
    "E004": "不支持的输入类型",
    "E005": "JSON解析失败",
    "E006": "CSV解析失败",
    "E007": "输出格式不支持",
    "E008": "内部处理错误",
    "E009": "参数冲突或无效组合",
    "E010": "自检失败",
}


class RamError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def detect_input_type(source: str) -> str:
    """检测输入类型：text / file / url"""
    if not source or not source.strip():
        raise RamError("E001")
    # 检查是否为URL
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return "url"
    # 检查是否为文件路径
    if os.path.isfile(source):
        return "file"
    # 默认为文本
    return "text"


def read_file_content(file_path: str) -> str:
    """读取文本文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise RamError("E002", f"文件不存在: {file_path}")
    except Exception as e:
        raise RamError("E002", f"读取文件失败: {str(e)}")


def parse_json_content(content: str) -> dict:
    """解析JSON格式内容"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise RamError("E005")


def parse_csv_content(content: str) -> list:
    """解析CSV格式内容（简单实现）"""
    try:
        lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
        if not lines:
            return []
        header = [h.strip() for h in lines[0].split(",")]
        result = []
        for line in lines[1:]:
            values = [v.strip() for v in line.split(",")]
            row = {}
            for i, h in enumerate(header):
                row[h] = values[i] if i < len(values) else ""
            result.append(row)
        return result
    except Exception:
        raise RamError("E006")


def extract_key_info(content: str) -> dict:
    """从文本内容中提取关键信息"""
    info = {
        "title": "",
        "keywords": [],
        "entities": [],
        "summary": "",
        "confidence": "medium",
    }
    # 提取标题：第一行非空内容
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    if lines:
        info["title"] = lines[0][:100]

    # 提取关键词：常见词频统计
    words = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", content.lower())
    stop_words = {"的", "了", "和", "是", "在", "有", "与", "及", "等", "the", "a", "an", "is", "are", "of", "to"}
    word_count = {}
    for w in words:
        if w not in stop_words and len(w) > 1:
            word_count[w] = word_count.get(w, 0) + 1
    top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:5]
    info["keywords"] = [w for w, _ in top_words]

    # 提取实体：URL、邮箱、日期等
    urls = re.findall(r'https?://[^\s]+', content)
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', content)
    dates = re.findall(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?', content)
    info["entities"] = list(set(urls + emails + dates))[:10]

    # 生成摘要：前200字符
    info["summary"] = content[:200] + ("..." if len(content) > 200 else "")

    # 置信度评估
    if len(content) < 50:
        info["confidence"] = "low"
    elif len(content) < 500:
        info["confidence"] = "medium"
    else:
        info["confidence"] = "high"

    return info


def process_text(source: str) -> dict:
    """处理纯文本输入"""
    result = {
        "source_type": "text",
        "content": source,
        "parsed": extract_key_info(source),
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.1",
    }
    return result


def process_file(file_path: str) -> dict:
    """处理文件输入"""
    content = read_file_content(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    result = {
        "source_type": "file",
        "file_path": file_path,
        "file_ext": ext,
        "content": content,
        "parsed": None,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.1",
    }

    if ext == ".json":
        result["parsed"] = parse_json_content(content)
    elif ext == ".csv":
        result["parsed"] = parse_csv_content(content)
    else:
        result["parsed"] = extract_key_info(content)

    return result


def process_url(url: str) -> dict:
    """处理URL输入（不发起网络请求，仅解析URL结构）"""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise RamError("E003", f"无效URL: {url}")

    result = {
        "source_type": "url",
        "url": url,
        "domain": parsed.netloc,
        "path": parsed.path or "/",
        "query_params": dict(p.split("=", 1) for p in parsed.query.split("&") if "=" in p),
        "parsed": {
            "title": parsed.netloc,
            "keywords": [parsed.netloc.split(".")[0]],
            "entities": [url],
            "summary": f"URL: {url}",
            "confidence": "low",
        },
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.1",
    }
    return result


def process_input(source: str, output_format: str = "json") -> str:
    """主处理函数：根据输入类型解析并输出"""
    if not source or not source.strip():
        raise RamError("E001")

    input_type = detect_input_type(source)
    if input_type == "text":
        result = process_text(source)
    elif input_type == "file":
        result = process_file(source)
    elif input_type == "url":
        result = process_url(source)
    else:
        raise RamError("E004")

    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        return format_as_markdown(result)
    else:
        raise RamError("E007", f"不支持输出格式: {output_format}")


def format_as_markdown(result: dict) -> str:
    """将结果格式化为Markdown"""
    lines = [
        "# 资源解析结果",
        "",
        f"- **来源类型**: {result.get('source_type', 'unknown')}",
        f"- **处理时间**: {result.get('timestamp', '')}",
        f"- **版本**: {result.get('version', '')}",
        "",
        "## 解析内容",
        "",
    ]

    parsed = result.get("parsed", {})
    if isinstance(parsed, dict):
        for key, value in parsed.items():
            if isinstance(value, list):
                lines.append(f"**{key}**: {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"**{key}**: {value}")
            lines.append("")
    elif isinstance(parsed, list):
        for i, item in enumerate(parsed):
            lines.append(f"### 记录 {i+1}")
            for key, value in item.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

    return "\n".join(lines)


def run_selftest() -> bool:
    """内置自检逻辑：使用硬编码样例数据验证核心功能"""
    print("开始自检...")

    # 测试1: 文本解析
    sample_text = "这是一个测试文档，包含URL https://example.com 和邮箱 test@example.com。"
    try:
        result = process_input(sample_text)
        data = json.loads(result)
        assert data["source_type"] == "text"
        assert data["parsed"]["confidence"] in ("low", "medium", "high")
        assert len(data["parsed"]["summary"]) > 0
        print("  ✓ 文本解析测试通过")
    except Exception as e:
        print(f"  ✗ 文本解析测试失败: {e}")
        return False

    # 测试2: JSON文件解析
    sample_json = '{"name": "test", "value": 123}'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(sample_json)
        tmp_file = f.name
    try:
        result = process_input(tmp_file)
        data = json.loads(result)
        assert data["source_type"] == "file"
        assert data["parsed"]["name"] == "test"
        print("  ✓ JSON文件解析测试通过")
    except Exception as e:
        print(f"  ✗ JSON文件解析测试失败: {e}")
        return False
    finally:
        os.unlink(tmp_file)

    # 测试3: URL解析
    sample_url = "https://example.com/path?param=value"
    try:
        result = process_input(sample_url)
        data = json.loads(result)
        assert data["source_type"] == "url"
        assert data["domain"] == "example.com"
        assert data["query_params"].get("param") == "value"
        print("  ✓ URL解析测试通过")
    except Exception as e:
        print(f"  ✗ URL解析测试失败: {e}")
        return False

    # 测试4: CSV解析
    sample_csv = "name,age,city\nalice,30,beijing\nbob,25,shanghai"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(sample_csv)
        tmp_csv = f.name
    try:
        result = process_input(tmp_csv)
        data = json.loads(result)
        assert data["source_type"] == "file"
        assert len(data["parsed"]) == 2
        assert data["parsed"][0]["name"] == "alice"
        print("  ✓ CSV解析测试通过")
    except Exception as e:
        print(f"  ✗ CSV解析测试失败: {e}")
        return False
    finally:
        os.unlink(tmp_csv)

    # 测试5: Markdown输出
    try:
        result_md = process_input(sample_text, output_format="markdown")
        assert "# 资源解析结果" in result_md
        print("  ✓ Markdown输出测试通过")
    except Exception as e:
        print(f"  ✗ Markdown输出测试失败: {e}")
        return False

    # 测试6: 错误处理
    try:
        process_input("")
        print("  ✗ 空输入错误处理测试失败")
        return False
    except RamError as e:
        assert e.code == "E001"
        print("  ✓ 错误处理测试通过")

    print("所有自检通过!")
    return True


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="ram - 资源解析与结构化转换工具",
        epilog="示例: python main.py --input '文本内容' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容：文本、文件路径或URL")
    parser.add_argument("--format", "-f", choices=["json", "markdown"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 版本信息
    if args.version:
        print("ram version 1.0.1")
        print("资源解析 结构化转换 资产管理")
        print("License: MIT")
        return 0

    # 正常处理模式
    if not args.input:
        parser.print_help()
        print("\n错误: 必须提供 --input 参数或使用 --selftest", file=sys.stderr)
        return 1

    try:
        output = process_input(args.input, args.format)
        print(output)
        return 0
    except RamError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E008] 内部处理错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
