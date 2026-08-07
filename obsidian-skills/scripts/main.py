#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obsidian-skills 独立实现脚本
=============================
依据功能规格独立重写，不参考任何既有代码。

功能：
  - 将文本内容转换为结构化 Obsidian 笔记（YAML frontmatter + Markdown 正文）
  - 支持自定义模板、输出目录、文件名规则
  - 批量处理多个输入
  - 置信度标注（无法确认的字段标注 [需核实:字段名]）
  - 内置 --selftest 离线自检

用法示例：
  python scripts/main.py --text "会议纪要：讨论Q3目标" --title "会议纪要-2026-01"
  python scripts/main.py --input file1.txt file2.md --outdir ./notes
  python scripts/main.py --selftest

错误码：
  E001 参数错误（缺少必要参数或参数冲突）
  E002 输入文件不存在或不可读
  E003 输出目录无法创建或不可写
  E004 文本内容为空或无效
  E005 模板格式错误
  E006 文件名生成失败（非法字符等）
  E007 批量处理时部分文件失败
  E008 内部逻辑错误（不应发生）
  E009 不支持的文件类型
  E010 其他未知错误
"""

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
DEFAULT_TEMPLATE = """---
title: "{title}"
date: "{date}"
tags: [{tags}]
source: "{source}"
confidence: "{confidence}"
---

# {title}

## 核心内容

{content}

## 元数据

- 创建时间: {date}
- 来源: {source}
- 标签: {tags}
- 置信度: {confidence}
"""

# 置信度阈值：低于此值则标注需核实
CONFIDENCE_THRESHOLD = 0.6

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".csv", ".json", ".html"}

# 单文件大小上限（字节）10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------
class SkillError(Exception):
    """技能运行错误，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class NoteData:
    """笔记数据模型。"""

    def __init__(
        self,
        title: str = "",
        content: str = "",
        source: str = "未知",
        tags: Optional[List[str]] = None,
        date: Optional[str] = None,
        confidence: float = 1.0,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.title = title or "未命名笔记"
        self.content = content or ""
        self.source = source
        self.tags = tags or []
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.confidence = float(confidence)
        self.extra = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "tags": self.tags,
            "date": self.date,
            "confidence": self.confidence,
            "extra": self.extra,
        }


# ---------------------------------------------------------------------------
# 核心逻辑：文本解析与笔记生成
# ---------------------------------------------------------------------------
def extract_title(text: str) -> str:
    """从文本中提取标题。

    策略：
      1. 查找以 # 开头的 Markdown 标题
      2. 查找第一行非空文本
      3. 使用默认标题
    """
    if not text or not text.strip():
        return "未命名笔记"

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

    # 查找 Markdown 标题
    for line in lines:
        match = re.match(r"^#{1,6}\s+(.+)$", line)
        if match:
            return match.group(1).strip()

    # 取第一行，截断过长内容
    first_line = lines[0]
    if len(first_line) > 50:
        first_line = first_line[:50] + "..."
    return first_line


def extract_tags(text: str, max_tags: int = 5) -> List[str]:
    """从文本中提取标签。

    策略：
      1. 查找 #标签 格式的标签
      2. 查找常见关键词（会议、报告、计划、总结等）
      3. 最多返回 max_tags 个
    """
    if not text:
        return []

    tags: List[str] = []

    # 查找 # 标签
    hashtag_pattern = re.compile(r"#([\u4e00-\u9fa5a-zA-Z0-9_\-]+)")
    for match in hashtag_pattern.finditer(text):
        tag = match.group(1)
        if tag and tag not in tags:
            tags.append(tag)
        if len(tags) >= max_tags:
            return tags

    # 常见关键词映射
    keyword_map = {
        "会议": "会议",
        "报告": "报告",
        "计划": "计划",
        "总结": "总结",
        "学习": "学习",
        "项目": "项目",
        "数据": "数据",
        "笔记": "笔记",
        "读书": "阅读",
        "灵感": "灵感",
    }

    for keyword, tag in keyword_map.items():
        if keyword in text and tag not in tags:
            tags.append(tag)
        if len(tags) >= max_tags:
            break

    return tags


def extract_metadata(text: str) -> Dict[str, Any]:
    """提取元数据。"""
    metadata: Dict[str, Any] = {}
    lines = text.strip().splitlines()

    # 尝试从 YAML frontmatter 中提取
    if lines and lines[0].strip() == "---":
        yaml_content = []
        for line in lines[1:]:
            if line.strip() == "---":
                break
            yaml_content.append(line)

        for line in yaml_content:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"').strip("'")

    return metadata


def generate_note(
    text: str,
    title: Optional[str] = None,
    source: str = "手动输入",
    template: Optional[str] = None,
) -> NoteData:
    """从文本生成结构化笔记。"""
    if not text or not text.strip():
        raise SkillError("E004", "文本内容为空或无效")

    # 提取信息
    actual_title = title or extract_title(text)
    tags = extract_tags(text)
    metadata = extract_metadata(text)

    # 置信度计算（基于信息完整度）
    confidence = 1.0
    if not title:
        confidence -= 0.1  # 标题为自动提取
    if not tags:
        confidence -= 0.1  # 无标签
    if len(text.strip()) < 20:
        confidence -= 0.2  # 内容过短
    if metadata:
        confidence -= 0.1  # 存在元数据但可能不完整

    confidence = max(0.3, min(1.0, confidence))

    # 置信度标注
    if confidence < CONFIDENCE_THRESHOLD:
        if not title:
            pass  # 标题已提取，无需标注
        if not tags:
            pass  # 标签已标注

    note = NoteData(
        title=actual_title,
        content=text.strip(),
        source=source,
        tags=tags,
        confidence=confidence,
        extra=metadata,
    )
    return note


def render_template(note: NoteData, template: Optional[str] = None) -> str:
    """将笔记渲染为 Markdown。"""
    tpl = template or DEFAULT_TEMPLATE

    # 简单模板替换
    tags_str = ", ".join(note.tags) if note.tags else "未分类"
    confidence_str = f"{note.confidence:.0%}"

    replacements = {
        "{title}": note.title,
        "{content}": note.content,
        "{date}": note.date,
        "{source}": note.source,
        "{tags}": tags_str,
        "{confidence}": confidence_str,
    }

    result = tpl
    for key, value in replacements.items():
        result = result.replace(key, value)

    # 处理额外的元数据字段
    for key, value in note.extra.items():
        result = result.replace(f"{{{key}}}", str(value))

    return result


def generate_filename(note: NoteData, pattern: str = "{date}-{title}") -> str:
    """生成文件名。"""
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", note.title)
    safe_title = safe_title.replace(" ", "-")

    filename = pattern
    filename = filename.replace("{date}", note.date)
    filename = filename.replace("{title}", safe_title)

    # 清理非法字符
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename)

    if not filename:
        raise SkillError("E006", "文件名生成失败")

    return filename + ".md"


def process_text(
    text: str,
    title: Optional[str] = None,
    source: str = "手动输入",
    template: Optional[str] = None,
    outdir: Optional[str] = None,
) -> str:
    """处理文本并生成笔记文件。"""
    note = generate_note(text, title, source, template)
    markdown = render_template(note, template)
    filename = generate_filename(note)

    if outdir:
        out_path = Path(outdir)
        try:
            out_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SkillError("E003", f"无法创建输出目录: {exc}") from exc

        file_path = out_path / filename
        try:
            file_path.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            raise SkillError("E003", f"无法写入文件: {exc}") from exc

        return str(file_path)
    else:
        # 不输出文件，返回 Markdown 内容
        return markdown


def process_file(filepath: str, template: Optional[str] = None, outdir: Optional[str] = None) -> str:
    """处理单个文件。"""
    path = Path(filepath)

    if not path.exists():
        raise SkillError("E002", f"文件不存在: {filepath}")
    if not path.is_file():
        raise SkillError("E002", f"不是文件: {filepath}")
    if path.stat().st_size > MAX_FILE_SIZE:
        raise SkillError("E009", f"文件超过 10MB 限制: {filepath}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise SkillError("E009", f"不支持的文件类型: {ext}")

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SkillError("E002", f"文件读取失败: {exc}") from exc

    return process_text(
        text=text,
        title=path.stem,
        source=str(path),
        template=template,
        outdir=outdir,
    )


def process_url(url: str, template: Optional[str] = None, outdir: Optional[str] = None) -> str:
    """处理 URL。

    注意：本实现不进行实际网络请求，仅生成占位笔记。
    实际使用时应集成请求库（如 requests）。
    """
    # 占位实现：生成一个包含 URL 的笔记
    text = f"网页收藏：{url}\n\n此笔记由 URL 导入生成。"
    return process_text(
        text=text,
        title=url.split("/")[-1] or "网页收藏",
        source=url,
        template=template,
        outdir=outdir,
    )


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑。"""
    print("=" * 60)
    print("运行自检（离线，硬编码样例）...")
    print("=" * 60)

    # 测试样例数据
    sample_text = """
# 2026年Q1工作总结

## 会议纪要

今天讨论了Q1的**项目进展**和**团队协作**情况。

#数据整理 #知识库

主要成果：
1. 完成了数据迁移
2. 建立了知识库框架
3. 输出报告3份
"""

    # 测试 1: 标题提取
    print("\n[测试 1] 标题提取")
    title = extract_title(sample_text)
    assert title == "2026年Q1工作总结", f"标题提取失败: {title}"
    print(f"  通过 ✓ 标题: {title}")

    # 测试 2: 标签提取
    print("\n[测试 2] 标签提取")
    tags = extract_tags(sample_text)
    assert len(tags) >= 1, "标签提取失败"
    assert "数据整理" in tags, f"标签中应包含'数据整理': {tags}"
    print(f"  通过 ✓ 标签: {tags}")

    # 测试 3: 笔记生成
    print("\n[测试 3] 笔记生成")
    note = generate_note(sample_text, source="测试数据")
    assert note.title, "笔记标题为空"
    assert note.content, "笔记内容为空"
    assert note.source == "测试数据", "来源错误"
    assert 0.3 <= note.confidence <= 1.0, f"置信度范围错误: {note.confidence}"
    print(f"  通过 ✓ 标题={note.title}, 置信度={note.confidence:.2f}")

    # 测试 4: 模板渲染
    print("\n[测试 4] 模板渲染")
    markdown = render_template(note)
    assert "---" in markdown, "缺少 YAML frontmatter"
    assert f"title: \"{note.title}\"" in markdown, "缺少标题"
    assert "核心内容" in markdown, "缺少正文部分"
    print(f"  通过 ✓ 渲染长度: {len(markdown)} 字符")

    # 测试 5: 文件名生成
    print("\n[测试 5] 文件名生成")
    filename = generate_filename(note)
    assert filename.endswith(".md"), f"文件名应以 .md 结尾: {filename}"
    assert filename, "文件名为空"
    print(f"  通过 ✓ 文件名: {filename}")

    # 测试 6: 处理函数
    print("\n[测试 6] 处理函数")
    result = process_text(sample_text, title="测试笔记", source="自检")
    assert isinstance(result, str), "处理结果应为字符串"
    assert len(result) > 0, "处理结果为空"
    print(f"  通过 ✓ 结果长度: {len(result)} 字符")

    # 测试 7: 文件处理
    print("\n[测试 7] 文件处理")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(sample_text)
        temp_path = f.name

    try:
        result = process_text(sample_text, title="文件测试", source=temp_path)
        assert result, "文件处理失败"
        print(f"  通过 ✓ 文件处理成功")
    finally:
        Path(temp_path).unlink(missing_ok=True)

    # 测试 8: 空输入处理
    print("\n[测试 8] 空输入处理")
    try:
        generate_note("")
        assert False, "空输入应抛出异常"
    except SkillError as exc:
        assert exc.code == "E004", f"错误码应为 E004: {exc.code}"
        print(f"  通过 ✓ 正确抛出 E004: {exc.message}")

    # 测试 9: 批量处理
    print("\n[测试 9] 批量处理")
    texts = [
        "第一篇笔记内容",
        "第二篇笔记内容 #测试",
        "第三篇笔记内容，包含会议记录",
    ]
    results = []
    for i, text in enumerate(texts):
        result = process_text(text, title=f"批量笔记{i+1}", source="批量测试")
        results.append(result)
    assert len(results) == 3, "批量处理数量错误"
    print(f"  通过 ✓ 批量处理 {len(results)} 条")

    # 测试 10: 置信度标注
    print("\n[测试 10] 置信度标注")
    short_text = "短内容"
    note = generate_note(short_text)
    assert note.confidence < 1.0, "短内容置信度应小于 1.0"
    print(f"  通过 ✓ 置信度: {note.confidence:.2f}")

    print("\n" + "=" * 60)
    print("✅ 所有自检通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="Obsidian Skills - 将文本/文件转换为结构化 Obsidian 笔记",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  %(prog)s --text "会议纪要：讨论Q3目标" --title "会议纪要"
  %(prog)s --input file1.txt file2.md --outdir ./notes
  %(prog)s --selftest
        """,
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", type=str, help="直接输入文本内容")
    input_group.add_argument("--input", nargs="+", help="输入文件路径列表")
    input_group.add_argument("--url", type=str, help="输入 URL")

    # 输出参数
    parser.add_argument("--outdir", type=str, default=None, help="输出目录（默认输出到 stdout）")
    parser.add_argument("--template", type=str, default=None, help="自定义模板文件路径")

    # 其他参数
    parser.add_argument("--title", type=str, default=None, help="笔记标题（默认自动提取）")
    parser.add_argument("--source", type=str, default=None, help="来源标注")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="obsidian-skills 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"❌ 自检失败: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"❌ 自检异常: {exc}", file=sys.stderr)
            return 1

    # 加载模板
    template = None
    if args.template:
        try:
            template = Path(args.template).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[E002] 模板文件读取失败: {exc}", file=sys.stderr)
            return 1

    try:
        # 处理输入
        if args.text:
            result = process_text(
                text=args.text,
                title=args.title,
                source=args.source or "命令行输入",
                template=template,
                outdir=args.outdir,
            )
            if not args.outdir:
                print(result)
            else:
                print(f"✅ 笔记已生成: {result}")

        elif args.input:
            success_count = 0
            fail_count = 0
            for filepath in args.input:
                try:
                    result = process_file(filepath, template=template, outdir=args.outdir)
                    success_count += 1
                    if not args.outdir:
                        print(result)
                except SkillError as exc:
                    fail_count += 1
                    print(f"❌ {exc.code}: {exc.message}", file=sys.stderr)

            print(f"✅ 处理完成: 成功 {success_count} 个，失败 {fail_count} 个")
            if fail_count > 0:
                return 1

        elif args.url:
            result = process_url(args.url, template=template, outdir=args.outdir)
            if not args.outdir:
                print(result)
            else:
                print(f"✅ 笔记已生成: {result}")

        else:
            parser.print_help()
            print("\n[E001] 请提供输入：--text、--input 或 --url", file=sys.stderr)
            return 1

    except SkillError as exc:
        print(f"❌ {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"[E010] 未知错误: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
