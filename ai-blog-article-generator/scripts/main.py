#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py - ai-blog-article-generator 主脚本

将数据、文件或URL转换为结构化、SEO友好的博客文章草稿。
支持CSV/JSON/TXT/MD文件、公开网页URL和纯文本输入。

错误码体系：E001-E010
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常（通用）
    E007: 参数解析错误
    E008: 输出写入失败
    E009: 数据校验失败
    E010: 未知错误
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

VERSION = "2.0.0"
SLUG = "ai-blog-article-generator"
DISPLAY_NAME = "博客文章生成器"

ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：主题或关键词",
    "E003": "输入格式不符合要求，示例：CSV/JSON/TXT/MD 文件或公开 URL",
    "E004": "这超出了本工具的能力范围，建议：检查输入类型",
    "E005": "结果无法确定，建议：提供更多上下文或更明确的主题",
    "E006": "内部处理异常，请稍后重试。",
    "E007": "命令行参数解析错误，请检查参数。",
    "E008": "输出写入失败，请检查文件权限或路径。",
    "E009": "数据校验失败，请检查输入内容。",
    "E010": "发生未知错误。",
}

HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 70

REQUEST_TIMEOUT = 10  # 秒
REQUEST_MAX_RETRIES = 3
REQUEST_BACKOFF_FACTOR = 2

SUPPORTED_EXTENSIONS = {".csv", ".json", ".txt", ".md"}
MAX_TEXT_LENGTH = 5000
MAX_CSV_ROWS = 1000

# 默认输出模板
DEFAULT_TEMPLATE = """---
title: "{title}"
description: "{description}"
keywords: "{keywords}"
date: "{date}"
confidence: {confidence}%
---

# {title}

> 本文由 AI 辅助生成，仅供学习与参考用途。

## 核心要点

{key_points}

## 引言

{introduction}

## 主体内容

{body}

## 结论

{conclusion}

---

*本文由 AI 生成草稿，需人工审核后发布。*
"""


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def utc_now_str() -> str:
    """返回 UTC 当前时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_filename(text: str, max_len: int = 50) -> str:
    """将文本转换为安全的文件名。"""
    # 移除非法字符
    cleaned = re.sub(r'[\\/:*?"<>|]', '_', text)
    # 移除多余空白
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    # 限制长度
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned or "untitled"


def read_text_safe(path: str) -> str:
    """读取文本文件，带编码兜底。"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def read_file_content(file_path: str) -> Tuple[str, str]:
    """
    读取文件内容，支持多编码 fallback。
    返回 (内容, 检测到的编码)。
    """
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    last_error: Optional[Exception] = None

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            return content, encoding
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except FileNotFoundError:
            raise
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"无法读取文件 {file_path}，尝试了多种编码。最后错误: {last_error}")


def read_file_streaming(file_path: str, chunk_size: int = 8192) -> str:
    """
    流式读取大文件，避免一次性加载到内存。
    以行为单位迭代，按句号分块。
    """
    content_parts: List[str] = []
    buffer = ""

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                buffer += line
                # 按句号分块，保留上下文
                while "。" in buffer or ". " in buffer:
                    # 找到最后一个句号位置
                    last_period = max(buffer.rfind("。"), buffer.rfind(". "))
                    if last_period == -1:
                        break
                    chunk = buffer[: last_period + 1]
                    content_parts.append(chunk)
                    buffer = buffer[last_period + 1 :]

                    if len(content_parts) * chunk_size > MAX_TEXT_LENGTH:
                        break

            # 处理剩余内容
            if buffer.strip():
                content_parts.append(buffer)

    except FileNotFoundError:
        raise
    except Exception as e:
        raise ValueError(f"读取文件失败: {e}")

    return "".join(content_parts)


def fetch_url_content(url: str, timeout: int = REQUEST_TIMEOUT) -> str:
    """
    抓取 URL 内容，带超时和指数退避重试。
    """
    last_error: Optional[Exception] = None

    for attempt in range(REQUEST_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                # 读取内容，限制大小
                content = response.read(MAX_TEXT_LENGTH * 4).decode("utf-8", errors="replace")
                return content
        except Exception as e:
            last_error = e
            if attempt < REQUEST_MAX_RETRIES - 1:
                # 指数退避
                import time
                wait_time = REQUEST_BACKOFF_FACTOR ** attempt
                time.sleep(wait_time)

    raise ValueError(f"URL 抓取失败: {last_error}")


def extract_text_from_html(html: str) -> str:
    """从 HTML 中提取纯文本。"""
    # 移除 script 和 style 标签
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', html)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_csv_content(content: str) -> Dict[str, Any]:
    """解析 CSV 内容，提取列名和数据样例。"""
    lines = content.strip().split("\n")
    if not lines:
        raise ValueError("CSV 内容为空")

    # 解析表头
    headers = [h.strip() for h in lines[0].split(",")]
    if not headers:
        raise ValueError("CSV 表头为空")

    # 解析数据行（限制行数）
    rows = []
    for line in lines[1:MAX_CSV_ROWS + 1]:
        if line.strip():
            values = [v.strip() for v in line.split(",")]
            rows.append(dict(zip(headers, values)))

    return {
        "type": "csv",
        "headers": headers,
        "rows": rows,
        "row_count": len(rows),
    }


def parse_json_content(content: str) -> Dict[str, Any]:
    """解析 JSON 内容。"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")

    if isinstance(data, list):
        return {
            "type": "json",
            "items": data[:100],
            "item_count": len(data),
        }
    elif isinstance(data, dict):
        return {
            "type": "json",
            "data": data,
            "keys": list(data.keys())[:50],
        }
    else:
        raise ValueError("JSON 内容必须是对象或数组")


def parse_input_content(content: str, input_type: str) -> Dict[str, Any]:
    """根据输入类型解析内容。"""
    if input_type == "csv":
        return parse_csv_content(content)
    elif input_type == "json":
        return parse_json_content(content)
    elif input_type == "url":
        text = extract_text_from_html(content)
        return {"type": "text", "content": text[:MAX_TEXT_LENGTH]}
    else:  # txt, md, text
        return {"type": "text", "content": content[:MAX_TEXT_LENGTH]}


def detect_input_type(file_path: str) -> str:
    """根据文件扩展名检测输入类型。"""
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        return "csv"
    elif ext == ".json":
        return "json"
    elif ext in (".txt", ".md"):
        return "text"
    else:
        return "text"


# ---------------------------------------------------------------------------
# 核心生成逻辑
# ---------------------------------------------------------------------------

def generate_with_cohere(
    prompt: str,
    api_key: str,
    model: str = "command-r-plus",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """
    调用 Cohere API 生成内容。
    """
    if not COHERE_AVAILABLE:
        raise RuntimeError("cohere 库未安装，请运行: pip install cohere")

    if not api_key:
        raise ValueError("未提供 API Key，请设置 COHERE_API_KEY 环境变量")

    client = cohere.Client(api_key)

    try:
        response = client.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.generations[0].text.strip()
    except Exception as e:
        raise RuntimeError(f"Cohere API 调用失败: {e}")


def build_prompt(
    topic: str,
    keywords: List[str],
    input_data: Optional[Dict[str, Any]],
    length: str,
    tone: str,
    audience: str,
) -> str:
    """构建生成提示词。"""
    length_map = {
        "short": "800-1000字",
        "medium": "1200-1800字",
        "long": "2000-3000字",
    }

    prompt_parts = [
        f"请生成一篇关于「{topic}」的博客文章。",
        f"文章长度：{length_map.get(length, length_map['medium'])}",
        f"语气风格：{tone}",
        f"目标受众：{audience}",
    ]

    if keywords:
        prompt_parts.append(f"关键词：{', '.join(keywords)}")

    if input_data:
        if input_data["type"] == "csv":
            headers = ", ".join(input_data["headers"])
            sample_rows = json.dumps(input_data["rows"][:5], ensure_ascii=False)
            prompt_parts.append(f"数据来源（CSV）：\n列名：{headers}\n样例数据：{sample_rows}")
        elif input_data["type"] == "json":
            prompt_parts.append(f"数据来源（JSON）：\n{json.dumps(input_data, ensure_ascii=False)[:2000]}")
        elif input_data["type"] == "text":
            prompt_parts.append(f"素材内容：\n{input_data['content'][:2000]}")

    prompt_parts.append("""
请按以下结构输出：
1. SEO标题（30-60字符）
2. Meta描述（150-160字符）
3. 关键词列表（3-5个）
4. 正文（包含引言、主体内容、结论）
5. 置信度评估（0-100%）

要求：
- 使用 Markdown 格式
- 不确定的信息使用 [需核实:字段名] 占位符
- 内容需逻辑连贯、结构清晰
""")

    return "\n\n".join(prompt_parts)


def parse_generated_content(content: str) -> Dict[str, Any]:
    """解析生成的内容，提取结构化信息。"""
    result = {
        "title": "",
        "description": "",
        "keywords": "",
        "body": content,
        "confidence": MEDIUM_CONFIDENCE_THRESHOLD,
    }

    # 提取标题
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        result["title"] = title_match.group(1).strip()

    # 提取描述
    desc_match = re.search(r'(?:Meta描述|Description)[：:]\s*(.+)', content)
    if desc_match:
        result["description"] = desc_match.group(1).strip()

    # 提取关键词
    kw_match = re.search(r'(?:关键词|Keywords)[：:]\s*(.+)', content)
    if kw_match:
        result["keywords"] = kw_match.group(1).strip()

    # 提取置信度
    conf_match = re.search(r'(?:置信度|Confidence)[：:]\s*(\d+)%', content)
    if conf_match:
        result["confidence"] = int(conf_match.group(1))

    return result


def generate_article(
    topic: str,
    keywords: List[str],
    input_data: Optional[Dict[str, Any]],
    api_key: str,
    length: str = "medium",
    tone: str = "professional",
    audience: str = "general",
    model: str = "command-r-plus",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """生成文章的主函数。"""
    # 构建提示词
    prompt = build_prompt(topic, keywords, input_data, length, tone, audience)

    # 调用 API
    generated = generate_with_cohere(
        prompt=prompt,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # 解析结果
    parsed = parse_generated_content(generated)

    # 如果解析失败，使用默认值
    if not parsed["title"]:
        parsed["title"] = topic

    if not parsed["description"]:
        parsed["description"] = f"关于{topic}的深度分析文章。"

    if not parsed["keywords"]:
        parsed["keywords"] = ", ".join(keywords) if keywords else topic

    return parsed


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(article: Dict[str, Any], topic: str) -> str:
    """格式化输出为 Markdown。"""
    # 提取正文（去掉已解析的部分）
    body = article.get("body", "")
    # 移除标题行
    body = re.sub(r'^#\s+.+$', '', body, flags=re.MULTILINE).strip()

    # 简单分段
    sections = body.split("\n\n")
    key_points = ""
    introduction = ""
    conclusion = ""

    # 提取关键部分
    for section in sections:
        if "核心要点" in section or "引言" in section:
            key_points += section + "\n\n"
        elif "结论" in section or "总结" in section:
            conclusion += section + "\n\n"
        else:
            introduction += section + "\n\n"

    if not key_points:
        key_points = "- 本文要点将在人工审核后补充。"

    if not conclusion:
        conclusion = "## 结论\n\n本文为 AI 生成草稿，需人工审核后发布。"

    return DEFAULT_TEMPLATE.format(
        title=article.get("title", topic),
        description=article.get("description", f"关于{topic}的文章"),
        keywords=article.get("keywords", topic),
        date=utc_now_str()[:10],
        confidence=article.get("confidence", MEDIUM_CONFIDENCE_THRESHOLD),
        key_points=key_points.strip(),
        introduction=introduction.strip() or "## 引言\n\n本文由 AI 生成，介绍相关主题。",
        body=introduction.strip() or "（正文内容待补充）",
        conclusion=conclusion.strip(),
    )


def atomic_write_file(file_path: str, content: str) -> None:
    """原子化写入文件，避免写入中断导致文件损坏。"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=directory or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子替换
        os.replace(temp_path, file_path)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def save(path: str, data: str, dry_run: bool = False) -> bool:
    """保存文件，支持 dry-run 模式。"""
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("=" * 60)
    print("自检开始 - ai-blog-article-generator")
    print("=" * 60)

    failures = 0

    # 1. 测试工具函数
    print("\n[1/6] 测试工具函数...")
    try:
        # 测试 safe_filename
        assert safe_filename("测试/文件:名称") == "测试_文件_名称"
        assert safe_filename("") == "untitled"
        assert len(safe_filename("a" * 100)) <= 50
        print("  ✓ safe_filename 通过")

        # 测试 utc_now_str
        now = utc_now_str()
        assert re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', now)
        print("  ✓ utc_now_str 通过")

    except AssertionError as e:
        print(f"  ✗ 工具函数测试失败: {e}")
        failures += 1

    # 2. 测试 CSV 解析
    print("\n[2/6] 测试 CSV 解析...")
    try:
        csv_content = "季度,销售额\nQ1,120万\nQ2,135万"
        result = parse_csv_content(csv_content)
        assert result["type"] == "csv"
        assert result["row_count"] == 2
        assert result["headers"] == ["季度", "销售额"]
        print("  ✓ CSV 解析通过")

    except Exception as e:
        print(f"  ✗ CSV 解析失败: {e}")
        failures += 1

    # 3. 测试 JSON 解析
    print("\n[3/6] 测试 JSON 解析...")
    try:
        json_content = '{"title": "测试", "items": [1, 2, 3]}'
        result = parse_json_content(json_content)
        assert result["type"] == "json"
        assert "title" in result["keys"]
        print("  ✓ JSON 解析通过")

    except Exception as e:
        print(f"  ✗ JSON 解析失败: {e}")
        failures += 1

    # 4. 测试 HTML 文本提取
    print("\n[4/6] 测试 HTML 文本提取...")
    try:
        html = "<html><body><h1>标题</h1><p>这是正文内容</p><script>var x=1;</script></body></html>"
        text = extract_text_from_html(html)
        assert "标题" in text
        assert "正文内容" in text
        assert "var x" not in text
        print("  ✓ HTML 提取通过")

    except Exception as e:
        print(f"  ✗ HTML 提取失败: {e}")
        failures += 1

    # 5. 测试内容解析
    print("\n[5/6] 测试内容解析...")
    try:
        generated = """# 测试标题
Meta描述：这是一个测试描述
关键词：测试,示例
置信度：85%

## 引言
这是引言内容。
"""
        parsed = parse_generated_content(generated)
        assert parsed["title"] == "测试标题"
        assert parsed["confidence"] == 85
        assert "测试" in parsed["keywords"]
        print("  ✓ 内容解析通过")

    except Exception as e:
        print(f"  ✗ 内容解析失败: {e}")
        failures += 1

    # 6. 测试输出格式化
    print("\n[6/6] 测试输出格式化...")
    try:
        article = {
            "title": "测试文章",
            "description": "测试描述",
            "keywords": "测试,文章",
            "body": "## 引言\n这是正文。\n\n## 结论\n这是结论。",
            "confidence": 85,
        }
        output = format_output(article, "测试")
        assert "测试文章" in output
        assert "confidence: 85%" in output
        assert "---" in output  # frontmatter 分隔符
        print("  ✓ 输出格式化通过")

    except Exception as e:
        print(f"  ✗ 输出格式化失败: {e}")
        failures += 1

    # 汇总
    print("\n" + "=" * 60)
    if failures == 0:
        print("✓ 所有自检通过！")
        return 0
    else:
        print(f"✗ {failures} 项自检失败！")
        return 1


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="AI 博客文章生成器 - 将数据/文件/URL 转换为 SEO 友好的博客文章草稿",
        epilog="示例: python run.py --topic '远程办公趋势' --keywords '远程办公,混合办公'",
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", type=str, help="输入文件路径或 URL")
    input_group.add_argument("--text", type=str, help="直接传入的文本内容")
    input_group.add_argument("--topic", type=str, help="文章主题（纯主题生成）")

    # 内容参数
    parser.add_argument("--keywords", type=str, default="", help="关键词，逗号分隔")
    parser.add_argument("--length", type=str, choices=["short", "medium", "long"], default="medium", help="文章长度")
    parser.add_argument("--tone", type=str, choices=["professional", "casual", "persuasive"], default="professional", help="语气风格")
    parser.add_argument("--audience", type=str, default="general", help="目标受众")

    # API 参数
    parser.add_argument("--api-key", type=str, default=os.environ.get("COHERE_API_KEY", ""), help="Cohere API Key")
    parser.add_argument("--model", type=str, default="command-r-plus", help="Cohere 模型名称")
    parser.add_argument("--temperature", type=float, default=0.7, help="生成温度 (0.0-1.0)")
    parser.add_argument("--max-tokens", type=int, default=2000, help="最大输出 token 数")

    # 输出参数
    parser.add_argument("--output-dir", type=str, default="output", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    parser.add_argument("--verbose", action="store_true", help="详细日志")

    # 其他
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式（必须在所有必填校验之前）
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input and not args.text and not args.topic:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    if not args.api_key and not args.dry_run:
        print("E006: 未提供 API Key。请设置 COHERE_API_KEY 环境变量或使用 --api-key 参数。", file=sys.stderr)
        return 1

    try:
        # 确定主题
        topic = args.topic or (args.text[:50] if args.text else "未命名文章")

        # 解析关键词
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

        # 处理输入
        input_data = None
        changed_items = []
        if args.input:
            if args.input.startswith(("http://", "https://")):
                if args.verbose:
                    print(f"正在抓取 URL: {args.input}")
                html_content = fetch_url_content(args.input)
                input_data = parse_input_content(html_content, "url")
            else:
                if not os.path.exists(args.input):
                    print(f"E001: 文件不存在: {args.input}", file=sys.stderr)
                    return 1
                input_type = detect_input_type(args.input)
                if args.verbose:
                    print(f"正在读取文件: {args.input} (类型: {input_type})")
                content = read_file_streaming(args.input)
                input_data = parse_input_content(content, input_type)

        elif args.text:
            input_data = {"type": "text", "content": args.text[:MAX_TEXT_LENGTH]}

        # 生成文章
        if args.verbose:
            print(f"正在生成文章: 主题='{topic}', 关键词={keywords}")
            print(f"参数: length={args.length}, tone={args.tone}, model={args.model}")

        if args.dry_run:
            # 预览模式，不调用 API
            article = {
                "title": f"[预览] {topic}",
                "description": f"关于{topic}的文章（预览模式）",
                "keywords": ", ".join(keywords) if keywords else topic,
                "body": "## 引言\n\n（预览模式，未调用 API 生成内容）\n\n## 结论\n\n（预览模式，未调用 API 生成内容）",
                "confidence": 0,
            }
        else:
            article = generate_article(
                topic=topic,
                keywords=keywords,
                input_data=input_data,
                api_key=args.api_key,
                length=args.length,
                tone=args.tone,
                audience=args.audience,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )

        # 格式化输出
        output_content = format_output(article, topic)

        # 生成输出路径
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_filename(topic)}_{timestamp}.md"
        output_path = os.path.join(args.output_dir, filename)

        # 记录修改明细（R6 可解释输出）
        if args.verbose:
            changed_items.append({
                "name": "title",
                "before": "",
                "after": article.get("title", ""),
            })
            changed_items.append({
                "name": "description",
                "before": "",
                "after": article.get("description", ""),
            })
            changed_items.append({
                "name": "keywords",
                "before": "",
                "after": article.get("keywords", ""),
            })
            changed_items.append({
                "name": "confidence",
                "before": "0",
                "after": str(article.get("confidence", 0)),
            })
            for idx, item in enumerate(changed_items):
                print(f"[明细] {idx}. {item['name']}: {item['before']} -> {item['after']}")
            print(f"[汇总] changed={len(changed_items)} 项，skipped=0 项")

        # 保存文件（R4 预览撤回）
        save(output_path, output_content, dry_run=args.dry_run)

        if args.dry_run:
            # 预览模式：打印输出摘要
            print(f"[DRY-RUN] 将写入文件: {output_path}")
            print(f"[DRY-RUN] 文件大小: {len(output_content)} 字符")
            print(f"[DRY-RUN] 标题: {article.get('title', '')}")
            print(f"[DRY-RUN] 描述: {article.get('description', '')}")
            print(f"[DRY-RUN] 关键词: {article.get('keywords', '')}")
            if args.verbose:
                print("\n--- 内容预览 ---")
                print(output_content[:500])
                print("--- 预览结束 ---")
        else:
            print(f"✓ 文章已生成: {output_path}")
            print(f"  标题: {article.get('title', '')}")
            print(f"  置信度: {article.get('confidence', 0)}%")

            # 置信度提示
            confidence = article.get("confidence", 0)
            if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
                print(f"  ⚠ 置信度较低 ({confidence}%)，建议人工审核后发布。")
            elif confidence < HIGH_CONFIDENCE_THRESHOLD:
                print(f"  ℹ 置信度中等 ({confidence}%)，建议补充事实数据。")

        return 0

    except ValueError as e:
        print(f"E009: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"E006: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 发生未知错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
