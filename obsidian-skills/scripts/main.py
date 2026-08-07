#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obsidian-skills — Obsidian 笔记自动化与知识库构建工具
版本: 1.0.1
许可: MIT
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用异常基类，携带错误码"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def err(code: str, message: str) -> AppError:
    """便捷构造错误"""
    return AppError(code, message)


# ============================================================
# 数据模型与常量
# ============================================================
DEFAULT_TEMPLATE = """---
title: "{title}"
author: "{author}"
date: "{date}"
tags: [{tags}]
source: "{source}"
confidence: {confidence}
---

# {title}

{content}
"""

# 需要核实字段的前缀标记
UNCERTAIN_PREFIX = "[需核实:"

# 支持解析的文本扩展名（用于文件转笔记）
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html", ".htm", ".xml", ".yaml", ".yml", ".log"}

# 单文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024


# ============================================================
# 核心功能：数据/文件/URL → 结构化笔记
# ============================================================
class NoteBuilder:
    """将原始数据转换为结构化 Obsidian 笔记"""

    def __init__(self, template: Optional[str] = None):
        self.template = template or DEFAULT_TEMPLATE

    def build(self, data: Dict[str, Any]) -> str:
        """
        根据数据字典生成 Markdown 笔记。
        数据字典字段: title, author, date, tags, source, content, confidence
        """
        # 字段缺失时标注需核实
        title = data.get("title") or self._uncertain("title")
        author = data.get("author") or self._uncertain("author")
        date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
        tags = data.get("tags") or []
        source = data.get("source") or self._uncertain("source")
        content = data.get("content") or self._uncertain("content")
        confidence = data.get("confidence", "low")

        # 标签格式化为逗号分隔
        tag_str = ", ".join(f'"{t}"' for t in tags)

        # 渲染模板
        try:
            return self.template.format(
                title=title,
                author=author,
                date=date,
                tags=tag_str,
                source=source,
                confidence=confidence,
                content=content,
            )
        except KeyError as e:
            raise err("E001", f"模板字段缺失: {e}")

    @staticmethod
    def _uncertain(field: str) -> str:
        """生成需核实标记"""
        return f"{UNCERTAIN_PREFIX}{field}]"


def parse_text_to_note(text: str, source: str = "", tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """从纯文本提取结构化笔记数据"""
    if not text or not text.strip():
        raise err("E002", "输入文本为空")

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        raise err("E002", "输入文本无有效内容")

    # 第一行作为标题
    title = lines[0][:80]  # 限制长度
    # 其余作为正文
    content = "\n".join(lines[1:]) if len(lines) > 1 else ""

    # 简单启发式提取作者（含"作者"或"by"的行）
    author = ""
    for line in lines[1:5]:
        if re.match(r"^(作者|by|author)\s*[:：]", line, re.IGNORECASE):
            author = re.sub(r"^(作者|by|author)\s*[:：]\s*", "", line, flags=re.IGNORECASE)
            break

    # 简单日期提取
    date_match = re.search(r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?)", text)
    date = date_match.group(1) if date_match else ""

    # 简单标签提取（#开头的词）
    found_tags = re.findall(r"#([\w\u4e00-\u9fa5-]+)", text)
    all_tags = list(dict.fromkeys(found_tags + (tags or [])))[:10]

    return {
        "title": title,
        "author": author,
        "date": date,
        "tags": all_tags,
        "source": source,
        "content": content,
        "confidence": "medium" if author and date else "low",
    }


def parse_json_to_note(json_data: Dict[str, Any], source: str = "") -> Dict[str, Any]:
    """从 JSON 数据提取结构化笔记"""
    if not isinstance(json_data, dict):
        raise err("E003", "JSON 数据必须是对象")

    # 常见字段映射
    title = json_data.get("title") or json_data.get("name") or json_data.get("标题") or ""
    author = json_data.get("author") or json_data.get("creator") or json_data.get("作者") or ""
    date = json_data.get("date") or json_data.get("created") or json_data.get("日期") or ""
    tags = json_data.get("tags") or json_data.get("labels") or []
    content = json_data.get("content") or json_data.get("body") or json_data.get("text") or ""
    source_url = json_data.get("source") or json_data.get("url") or source

    # 如果 content 是字典或列表，转为 JSON 字符串
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False, indent=2)

    return {
        "title": title,
        "author": author,
        "date": date,
        "tags": tags if isinstance(tags, list) else [tags] if tags else [],
        "source": source_url,
        "content": content,
        "confidence": "high" if title and content else "medium",
    }


def extract_meta_from_url(url: str) -> Dict[str, str]:
    """从 URL 提取元数据（无需网络访问）"""
    parsed = urllib.parse.urlparse(url)
    path = Path(parsed.path)
    title = path.stem.replace("-", " ").replace("_", " ").title() if path.stem else parsed.netloc
    return {
        "title": title,
        "source": url,
        "domain": parsed.netloc,
    }


# ============================================================
# 批量处理与文件操作
# ============================================================
def read_file_safe(filepath: Path) -> str:
    """安全读取文件，带大小和编码检查"""
    if not filepath.exists():
        raise err("E004", f"文件不存在: {filepath}")

    if not filepath.is_file():
        raise err("E005", f"不是文件: {filepath}")

    size = filepath.stat().st_size
    if size > MAX_FILE_SIZE:
        raise err("E006", f"文件超过 10MB 限制: {filepath} ({size} bytes)")

    # 尝试多种编码
    for encoding in ["utf-8", "gbk", "latin-1"]:
        try:
            return filepath.read_text(encoding=encoding)
        except (UnicodeDecodeError, PermissionError):
            continue

    raise err("E007", f"无法读取文件（编码不支持）: {filepath}")


def process_file(filepath: Path, output_dir: Path, template: Optional[str] = None) -> Path:
    """处理单个文件，生成笔记"""
    if filepath.suffix.lower() not in TEXT_EXTENSIONS:
        raise err("E008", f"不支持的文件类型: {filepath.suffix}")

    text = read_file_safe(filepath)
    note_data = parse_text_to_note(text, source=str(filepath))

    # 根据文件扩展名选择解析方式
    if filepath.suffix.lower() == ".json":
        try:
            json_data = json.loads(text)
            note_data = parse_json_to_note(json_data, source=str(filepath))
        except json.JSONDecodeError:
            # JSON 解析失败则退回文本解析
            pass

    builder = NoteBuilder(template)
    note = builder.build(note_data)

    # 生成输出文件名（时间戳避免冲突）
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", note_data["title"])[:50]
    output_path = output_dir / f"{safe_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    output_path.write_text(note, encoding="utf-8")

    return output_path


def process_url(url: str, output_dir: Path, template: Optional[str] = None) -> Path:
    """处理 URL（不访问网络，仅提取 URL 元数据）"""
    meta = extract_meta_from_url(url)
    note_data = {
        "title": meta["title"],
        "author": "",
        "date": "",
        "tags": ["未分类"],
        "source": url,
        "content": f"来源: {url}\n\n请手动补充内容。",
        "confidence": "low",
    }

    builder = NoteBuilder(template)
    note = builder.build(note_data)

    safe_title = re.sub(r'[\\/:*?"<>|]', "_", note_data["title"])[:50]
    output_path = output_dir / f"{safe_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    output_path.write_text(note, encoding="utf-8")

    return output_path


def process_batch(inputs: List[str], output_dir: Path, template: Optional[str] = None) -> Dict[str, Any]:
    """批量处理多个输入（文件或 URL）"""
    results = {"success": [], "failed": []}

    for item in inputs:
        try:
            if item.startswith(("http://", "https://")):
                output = process_url(item, output_dir, template)
            else:
                filepath = Path(item)
                output = process_file(filepath, output_dir, template)
            results["success"].append({"input": item, "output": str(output)})
        except AppError as e:
            results["failed"].append({"input": item, "error": e.code, "message": e.message})
        except Exception as e:
            results["failed"].append({"input": item, "error": "E009", "message": str(e)})

    return results


# ============================================================
# 自检功能（--selftest）
# ============================================================
def run_selftest() -> int:
    """离线自检核心逻辑，使用硬编码样例数据"""
    print("=== obsidian-skills 自检开始 ===")
    failures = 0

    # 测试 1: 文本解析
    print("\n[1/5] 测试文本解析...")
    sample_text = """Obsidian 使用指南
作者: 张三
日期: 2026-03-15

这是一段测试内容，用于验证解析功能。
#obsidian #笔记
"""
    try:
        note_data = parse_text_to_note(sample_text, source="test://sample")
        assert note_data["title"] == "Obsidian 使用指南", f"标题解析错误: {note_data['title']}"
        assert note_data["author"] == "张三", f"作者解析错误: {note_data['author']}"
        assert len(note_data["tags"]) >= 1, "标签解析错误"
        assert note_data["content"], "内容解析错误"
        print("  ✓ 文本解析通过")
    except AssertionError as e:
        print(f"  ✗ 文本解析失败: {e}")
        failures += 1
    except AppError as e:
        print(f"  ✗ 文本解析异常: {e.code} {e.message}")
        failures += 1

    # 测试 2: JSON 解析
    print("\n[2/5] 测试 JSON 解析...")
    sample_json = {
        "title": "项目报告",
        "author": "李四",
        "date": "2026-01-01",
        "tags": ["报告", "项目"],
        "content": "这是项目报告的正文内容。",
        "source": "test://json",
    }
    try:
        json_note = parse_json_to_note(sample_json)
        assert json_note["title"] == "项目报告", f"JSON 标题解析错误: {json_note['title']}"
        assert json_note["author"] == "李四", f"JSON 作者解析错误: {json_note['author']}"
        assert len(json_note["tags"]) == 2, "JSON 标签解析错误"
        print("  ✓ JSON 解析通过")
    except AssertionError as e:
        print(f"  ✗ JSON 解析失败: {e}")
        failures += 1

    # 测试 3: 笔记生成
    print("\n[3/5] 测试笔记生成...")
    try:
        builder = NoteBuilder()
        note = builder.build(note_data)
        assert "---" in note, "缺少 YAML frontmatter"
        assert "# Obsidian 使用指南" in note, "缺少标题"
        assert "[需核实:" not in note, "不应有需核实标记"
        print("  ✓ 笔记生成通过")
    except AssertionError as e:
        print(f"  ✗ 笔记生成失败: {e}")
        failures += 1
    except AppError as e:
        print(f"  ✗ 笔记生成异常: {e.code} {e.message}")
        failures += 1

    # 测试 4: URL 元数据提取
    print("\n[4/5] 测试 URL 元数据提取...")
    try:
        meta = extract_meta_from_url("https://example.com/blog/my-article")
        assert meta["title"], "URL 标题为空"
        assert meta["source"] == "https://example.com/blog/my-article", "URL 来源错误"
        assert meta["domain"] == "example.com", f"域名错误: {meta['domain']}"
        print("  ✓ URL 元数据提取通过")
    except AssertionError as e:
        print(f"  ✗ URL 元数据提取失败: {e}")
        failures += 1

    # 测试 5: 文件处理（使用临时文件）
    print("\n[5/5] 测试文件处理...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_file = tmp_path / "test_input.txt"
            input_file.write_text("测试文件标题\n\n这是文件内容。\n#测试标签", encoding="utf-8")

            output_dir = tmp_path / "output"
            output_dir.mkdir()

            result = process_file(input_file, output_dir)
            assert result.exists(), "输出文件不存在"
            content = result.read_text(encoding="utf-8")
            assert "测试文件标题" in content, "输出内容缺少标题"
            assert "这是文件内容" in content, "输出内容缺少正文"
            print("  ✓ 文件处理通过")
    except AssertionError as e:
        print(f"  ✗ 文件处理失败: {e}")
        failures += 1
    except AppError as e:
        print(f"  ✗ 文件处理异常: {e.code} {e.message}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 文件处理未知错误: {e}")
        failures += 1

    # 汇总
    print(f"\n=== 自检完成: {5 - failures}/5 通过 ===")
    if failures > 0:
        print(f"存在 {failures} 项失败")
        return 1
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Obsidian 笔记自动化工具 — 将数据/文件/URL 转换为结构化笔记",
        epilog="示例: python main.py --input note.txt --output vault/",
    )

    parser.add_argument(
        "--input", "-i",
        nargs="+",
        help="输入文件路径或 URL（支持多个）",
    )
    parser.add_argument(
        "--output", "-o",
        default="./notes_output",
        help="输出目录（默认: ./notes_output）",
    )
    parser.add_argument(
        "--template", "-t",
        help="自定义笔记模板文件路径",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部环境）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="obsidian-skills 1.0.1",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常运行模式
    if not args.input:
        parser.error("必须提供 --input 或使用 --selftest")

    # 读取模板
    template = None
    if args.template:
        try:
            template_path = Path(args.template)
            template = read_file_safe(template_path)
        except AppError as e:
            print(f"错误: {e.code} {e.message}", file=sys.stderr)
            return 2

    # 创建输出目录
    try:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[E010] 无法创建输出目录: {e}", file=sys.stderr)
        return 2

    # 批量处理
    try:
        results = process_batch(args.input, output_dir, template)

        # 输出结果
        print(f"处理完成: {len(results['success'])} 成功, {len(results['failed'])} 失败")

        for item in results["success"]:
            print(f"  ✓ {item['input']} → {item['output']}")

        for item in results["failed"]:
            print(f"  ✗ {item['input']}: [{item['error']}] {item['message']}")

        # 有失败时返回非零
        return 1 if results["failed"] else 0

    except AppError as e:
        print(f"错误: {e.code} {e.message}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[E009] 未预期错误: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
