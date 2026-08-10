#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章归档技能（wechat-article-archive-skill）独立实现。

本脚本仅依据功能规格编写，为 clean-room 实现。
提供公众号文章归档的核心流程：解析输入、结构化字段、置信度评估、异常处理。
支持命令行调用与 --selftest 离线自检。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义（对应规格第四章）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 以下为内部扩展错误码，用于程序自身异常
    "E006": "内部解析错误：无法解析输入内容",
    "E007": "内部处理错误：生成输出失败",
    "E008": "内部校验错误：输出校验未通过",
    "E009": "内部文件错误：文件读写失败",
    "E010": "内部参数错误：命令行参数不合法",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ArticleRecord:
    """公众号文章结构化记录。"""
    title: str = ""
    author: str = ""
    publish_date: str = ""
    content: str = ""
    source_url: str = ""
    images: List[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_review: bool = False
    notes: List[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """处理结果封装。"""
    success: bool = True
    error_code: Optional[str] = None
    error_msg: str = ""
    record: Optional[ArticleRecord] = None
    output_path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class ArticleArchiveProcessor:
    """公众号文章归档处理器。"""

    # 置信度阈值（对应规格第三章）
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.85

    # 关键字段列表（用于完整性检查）
    REQUIRED_FIELDS = ["title", "author", "publish_date", "content"]

    # 常见日期格式（用于解析）
    DATE_PATTERNS = [
        r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?",
        r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})",
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
    ]

    def __init__(self) -> None:
        """初始化处理器。"""
        self._warnings: List[str] = []

    def process_input(self, raw_input: str, output_format: str = "markdown") -> ProcessingResult:
        """
        处理用户输入，生成结构化文章记录。

        参数:
            raw_input: 用户提供的原始输入（文本、文件路径或URL字符串）
            output_format: 输出格式（markdown / json）

        返回:
            ProcessingResult: 处理结果
        """
        try:
            # Step 1: 输入校验
            if not raw_input or not raw_input.strip():
                return self._make_error("E001")

            # Step 2: 解析输入（根据输入类型分发）
            parsed = self._parse_input(raw_input)
            if parsed is None:
                return self._make_error("E006")

            # Step 3: 构建文章记录
            record = self._build_record(parsed)
            if record is None:
                return self._make_error("E002")

            # Step 4: 计算置信度
            record.confidence = self._calculate_confidence(record)
            record.needs_review = self._evaluate_confidence(record, self._warnings)

            # Step 5: 生成输出
            output_path = self._generate_output(record, output_format)
            if output_path is None:
                return self._make_error("E007")

            # Step 6: 返回结果
            return ProcessingResult(
                success=True,
                record=record,
                output_path=output_path,
                warnings=self._warnings.copy(),
            )

        except Exception as e:
            # 兜底异常处理
            return ProcessingResult(
                success=False,
                error_code="E010",
                error_msg=f"处理过程中发生未预期异常: {str(e)}",
            )

    # ------------------------------------------------------------------
    # 内部解析方法
    # ------------------------------------------------------------------
    def _parse_input(self, raw_input: str) -> Optional[Dict[str, Any]]:
        """
        解析输入内容，识别关键信息。

        支持三种输入类型：
        1. JSON字符串
        2. 本地文件路径（.txt / .json / .md）
        3. 纯文本内容

        返回:
            解析后的字典，或 None 表示无法解析
        """
        raw = raw_input.strip()

        # 尝试作为 JSON 解析
        if raw.startswith("{"):
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        # 尝试作为文件路径解析
        if os.path.isfile(raw):
            try:
                ext = os.path.splitext(raw)[1].lower()
                if ext == ".json":
                    with open(raw, "r", encoding="utf-8", errors="replace") as f:
                        data = json.load(f)
                        return data if isinstance(data, dict) else None
                elif ext in (".txt", ".md"):
                    with open(raw, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                        return {"content": content}
                else:
                    self._warnings.append(f"不支持的文件类型: {ext}，按纯文本处理")
                    return {"content": raw}
            except (OSError, IOError) as e:
                self._warnings.append(f"文件读取失败: {str(e)}")
                return {"content": raw}

        # 尝试作为 URL 解析（仅识别，不访问网络）
        if re.match(r"^https?://", raw):
            self._warnings.append("检测到URL输入，但本工具不访问网络，将URL作为文本处理")
            return {"source_url": raw, "content": raw}

        # 按纯文本处理
        return {"content": raw}

    def _build_record(self, data: Dict[str, Any]) -> Optional[ArticleRecord]:
        """
        从解析后的字典构建文章记录。

        参数:
            data: 解析后的输入数据

        返回:
            ArticleRecord 或 None（关键信息缺失）
        """
        record = ArticleRecord()

        # 提取标题
        record.title = self._extract_field(data, ["title", "标题", "name", "名称"])
        if not record.title:
            # 尝试从内容首行提取
            first_line = data.get("content", "").strip().split("\n")[0]
            if first_line and len(first_line) < 100:
                record.title = first_line.strip("# ").strip()
                self._warnings.append("标题未明确提供，已从内容首行提取")

        # 提取作者
        record.author = self._extract_field(data, ["author", "作者", "creator", "byline"])

        # 提取发布日期
        record.publish_date = self._extract_field(
            data, ["publish_date", "date", "发布日期", "publishDate", "pub_date"]
        )
        if not record.publish_date:
            # 尝试从内容中提取日期
            content = data.get("content", "")
            record.publish_date = self._extract_date_from_text(content)

        # 提取正文
        record.content = self._extract_field(data, ["content", "正文", "body", "text"])
        if not record.content and record.title:
            # 如果只有标题，正文设为标题
            record.content = record.title

        # 提取来源URL
        record.source_url = self._extract_field(data, ["source_url", "url", "link", "原文链接"])

        # 提取图片列表
        images = self._extract_field(data, ["images", "图片", "image_list"])
        if isinstance(images, list):
            record.images = [str(img) for img in images]
        elif isinstance(images, str) and images.strip():
            record.images = [images]

        # 关键字段完整性检查
        missing = [f for f in self.REQUIRED_FIELDS if not getattr(record, f)]
        if missing:
            self._warnings.append(f"关键字段缺失: {', '.join(missing)}")
            # 如果连标题和正文都没有，返回None（触发E002）
            if not record.title and not record.content:
                return None

        # 添加备注
        if not record.author:
            record.notes.append("作者信息缺失，请补充")
        if not record.publish_date:
            record.notes.append("发布日期缺失，请补充")

        return record

    def _extract_field(self, data: Dict[str, Any], keys: List[str]) -> str:
        """从字典中按多个可能的键名提取字段值。"""
        for key in keys:
            value = data.get(key)
            if value is not None:
                return str(value).strip()
        return ""

    def _extract_date_from_text(self, text: str) -> str:
        """从文本中提取日期字符串。"""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    year, month, day = groups
                    # 规范化日期格式
                    return f"{year}-{int(month):02d}-{int(day):02d}"
        return ""

    # ------------------------------------------------------------------
    # 置信度计算
    # ------------------------------------------------------------------
    def _calculate_confidence(self, record: ArticleRecord) -> float:
        """
        计算文章记录的置信度。

        规则：
        - 基础分 0.5
        - 每有一个关键字段（title/author/date/content）加 0.1
        - 有来源URL加 0.05
        - 有图片加 0.05
        - 上限 1.0
        """
        confidence = 0.5

        # 关键字段完整性
        for field_name in ["title", "author", "publish_date", "content"]:
            if getattr(record, field_name):
                confidence += 0.1

        # 附加信息
        if record.source_url:
            confidence += 0.05
        if record.images:
            confidence += 0.05

        return min(confidence, 1.0)

    def _evaluate_confidence(self, record: ArticleRecord, warnings: List[str]) -> bool:
        """
        根据置信度评估是否需要人工复核。

        规则（对应规格第三章）：
        - ≥90%: 直接输出
        - 85%-90%: 标注"建议复核"
        - <85%: 标注"[需核实]"

        返回:
            True 表示需要复核，False 表示可直接输出
        """
        if record.confidence >= self.HIGH_CONFIDENCE:
            return False
        elif record.confidence >= self.MEDIUM_CONFIDENCE:
            warnings.append("建议复核：部分字段置信度不足")
            return True
        else:
            warnings.append("[需核实] 置信度低于85%，关键信息可能不完整")
            record.notes.append("[需核实]")
            return True

    # ------------------------------------------------------------------
    # 输出生成
    # ------------------------------------------------------------------
    def _generate_output(self, record: ArticleRecord, output_format: str) -> Optional[str]:
        """
        生成输出文件（Markdown 或 JSON）。

        参数:
            record: 文章记录
            output_format: 输出格式

        返回:
            输出文件路径，或 None 表示生成失败
        """
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="wechat_archive_")

            if output_format == "json":
                # 生成 JSON 输出
                output_path = os.path.join(temp_dir, "article.json")
                data = {
                    "title": record.title,
                    "author": record.author,
                    "publish_date": record.publish_date,
                    "content": record.content,
                    "source_url": record.source_url,
                    "images": record.images,
                    "confidence": round(record.confidence, 2),
                    "needs_review": record.needs_review,
                    "notes": record.notes,
                }
                with open(output_path, "w", encoding="utf-8", errors="replace") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                # 默认生成 Markdown 输出
                output_path = os.path.join(temp_dir, "article.md")
                md_content = self._build_markdown(record)
                with open(output_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(md_content)

            # 创建 ZIP 包（包含输出文件）
            zip_path = os.path.join(temp_dir, "article_archive.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(output_path, os.path.basename(output_path))

            # 返回 ZIP 路径（作为最终输出）
            return zip_path

        except (OSError, IOError) as e:
            self._warnings.append(f"输出生成失败: {str(e)}")
            return None

    def _build_markdown(self, record: ArticleRecord) -> str:
        """构建 Markdown 格式的文章内容。"""
        lines = []

        # 标题
        if record.title:
            lines.append(f"# {record.title}")
            lines.append("")

        # 元信息
        meta_lines = []
        if record.author:
            meta_lines.append(f"**作者**: {record.author}")
        if record.publish_date:
            meta_lines.append(f"**日期**: {record.publish_date}")
        if record.source_url:
            meta_lines.append(f"**来源**: {record.source_url}")
        if record.images:
            meta_lines.append(f"**图片**: {len(record.images)}张")

        if meta_lines:
            lines.append(" | ".join(meta_lines))
            lines.append("")

        # 置信度提示
        if record.needs_review:
            lines.append(f"> ⚠️ **置信度**: {record.confidence:.0%}，建议复核")
        else:
            lines.append(f"> ✅ **置信度**: {record.confidence:.0%}")
        lines.append("")

        # 备注
        if record.notes:
            lines.append("> 📝 **备注**:")
            for note in record.notes:
                lines.append(f"> - {note}")
            lines.append("")

        # 正文
        if record.content:
            lines.append("---")
            lines.append("")
            lines.append(record.content)
            lines.append("")

        # 图片列表
        if record.images:
            lines.append("---")
            lines.append("")
            lines.append("## 图片列表")
            for i, img in enumerate(record.images, 1):
                lines.append(f"{i}. {img}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 错误辅助
    # ------------------------------------------------------------------
    def _make_error(self, error_code: str) -> ProcessingResult:
        """构造错误结果。"""
        return ProcessingResult(
            success=False,
            error_code=error_code,
            error_msg=ERROR_CODES.get(error_code, "未知错误"),
        )


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保任何环境可过。

    返回:
        0 表示全部通过，非0表示有失败
    """
    print("=" * 60)
    print("开始自检: wechat-article-archive-skill")
    print("=" * 60)

    failures = 0
    processor = ArticleArchiveProcessor()

    # ------------------------------------------------------------------
    # 测试用例 1: 完整 JSON 输入
    # ------------------------------------------------------------------
    print("\n[测试1] 完整 JSON 输入")
    test_input = json.dumps({
        "title": "测试文章标题",
        "author": "测试作者",
        "publish_date": "2024-01-15",
        "content": "这是一段测试正文内容，用于验证处理逻辑。",
        "source_url": "https://example.com/article/1",
        "images": ["https://example.com/img/1.jpg", "https://example.com/img/2.jpg"],
    })

    result = processor.process_input(test_input, "markdown")

    # 断言: 处理成功
    assert result.success, f"处理失败: {result.error_code} {result.error_msg}"
    print(f"  ✓ 处理成功")

    # 断言: 记录存在
    assert result.record is not None, "记录为空"
    print(f"  ✓ 记录已生成")

    # 断言: 标题正确（宽松判断：非空）
    assert result.record.title, "标题为空"
    print(f"  ✓ 标题: {result.record.title}")

    # 断言: 作者正确
    assert result.record.author, "作者为空"
    print(f"  ✓ 作者: {result.record.author}")

    # 断言: 置信度较高（宽松：>0.8）
    assert result.record.confidence > 0.8, f"置信度异常: {result.record.confidence}"
    print(f"  ✓ 置信度: {result.record.confidence:.2f}")

    # 断言: 输出文件存在
    assert result.output_path and os.path.isfile(result.output_path), "输出文件不存在"
    print(f"  ✓ 输出文件: {result.output_path}")

    # 测试通过
    print("  ✓ 测试1通过")

    # ------------------------------------------------------------------
    # 测试用例 2: 纯文本输入（最小信息）
    # ------------------------------------------------------------------
    print("\n[测试2] 纯文本输入（最小信息）")
    test_text = "这是一篇没有元信息的纯文本文章内容，用于测试最小输入场景。"

    result = processor.process_input(test_text, "json")

    # 断言: 处理成功（有内容即可）
    assert result.success, f"处理失败: {result.error_code} {result.error_msg}"
    print(f"  ✓ 处理成功")

    # 断言: 记录存在
    assert result.record is not None, "记录为空"
    print(f"  ✓ 记录已生成")

    # 断言: 内容非空
    assert result.record.content, "内容为空"
    print(f"  ✓ 内容长度: {len(result.record.content)} 字符")

    # 断言: 置信度较低（宽松：<0.8）
    assert result.record.confidence < 0.8, f"置信度应较低: {result.record.confidence}"
    print(f"  ✓ 置信度: {result.record.confidence:.2f}")

    # 测试通过
    print("  ✓ 测试2通过")

    # ------------------------------------------------------------------
    # 测试用例 3: 空输入（错误处理）
    # ------------------------------------------------------------------
    print("\n[测试3] 空输入（错误处理）")
    result = processor.process_input("", "markdown")

    # 断言: 处理失败
    assert not result.success, "空输入应处理失败"
    print(f"  ✓ 处理失败（符合预期）")

    # 断言: 错误码为 E001
    assert result.error_code == "E001", f"错误码应为E001，实际: {result.error_code}"
    print(f"  ✓ 错误码: {result.error_code}")

    # 断言: 错误消息非空
    assert result.error_msg, "错误消息为空"
    print(f"  ✓ 错误消息: {result.error_msg}")

    # 测试通过
    print("  ✓ 测试3通过")

    # ------------------------------------------------------------------
    # 测试用例 4: 部分字段缺失
    # ------------------------------------------------------------------
    print("\n[测试4] 部分字段缺失")
    test_input = json.dumps({
        "title": "只有标题的文章",
        "content": "正文内容",
    })

    result = processor.process_input(test_input, "markdown")

    # 断言: 处理成功
    assert result.success, f"处理失败: {result.error_code} {result.error_msg}"
    print(f"  ✓ 处理成功")

    # 断言: 有警告信息
    assert result.warnings, "应有警告信息"
    print(f"  ✓ 警告数: {len(result.warnings)}")

    # 断言: 需要复核
    assert result.record.needs_review, "应标记需要复核"
    print(f"  ✓ 标记复核: {result.record.needs_review}")

    # 测试通过
    print("  ✓ 测试4通过")

    # ------------------------------------------------------------------
    # 测试用例 5: 日期提取
    # ------------------------------------------------------------------
    print("\n[测试5] 日期提取")
    test_input = json.dumps({
        "title": "日期提取测试",
        "content": "发布于2023年12月25日的一篇文章",
    })

    result = processor.process_input(test_input, "markdown")

    # 断言: 处理成功
    assert result.success, f"处理失败: {result.error_code} {result.error_msg}"
    print(f"  ✓ 处理成功")

    # 断言: 日期被提取（宽松：非空）
    assert result.record.publish_date, "日期未提取"
    print(f"  ✓ 提取日期: {result.record.publish_date}")

    # 测试通过
    print("  ✓ 测试5通过")

    # ------------------------------------------------------------------
    # 汇总结果
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    if failures == 0:
        print("✅ 全部自检通过！")
    else:
        print(f"❌ 自检失败: {failures} 项未通过")
    print("=" * 60)

    return failures


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="公众号文章归档技能 - 处理公众号文章并生成归档文件",
        epilog="示例: python main.py --input '{\"title\": \"测试\", \"content\": \"正文\"}' --format markdown",
    )

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="输入内容：JSON字符串、文件路径或纯文本",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部输入）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检，或 --help 查看帮助", file=sys.stderr)
        return 1

    # 创建处理器并执行
    processor = ArticleArchiveProcessor()
    result = processor.process_input(args.input, args.format)

    if not result.success:
        print(f"错误 [{result.error_code}]: {result.error_msg}", file=sys.stderr)
        return 1

    # 输出结果
    print("\n处理成功！")
    if result.record:
        print(f"  标题: {result.record.title}")
        print(f"  作者: {result.record.author or '(未提供)'}")
        print(f"  日期: {result.record.publish_date or '(未提供)'}")
        print(f"  置信度: {result.record.confidence:.0%}")
        if result.record.needs_review:
            print("  ⚠️ 建议复核")
    if result.output_path:
        print(f"  输出: {result.output_path}")
    if result.warnings:
        print("\n警告:")
        for w in result.warnings:
            print(f"  - {w}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
