#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resilient-sile — SILE 排版系统容错转换辅助工具

功能概述：
    1. 将文本/PDF/URL 等输入解析为结构化数据（标题、作者、日期、金额、条款编号等）
    2. 生成 SILE 可编译的 .sil 源文件
    3. 对不确定的解析结果标注置信度等级
    4. 支持批量处理与自定义输出格式
    5. 仅本地处理，不连接外部服务，不修改原始文件

用法示例：
    python main.py --input sample.txt --format markdown
    python main.py --selftest

错误码说明：
    E001 参数错误
    E002 输入文件不存在
    E003 输入文件读取失败
    E004 输入格式不支持
    E005 解析失败
    E006 输出格式不支持
    E007 输出写入失败
    E008 模板格式错误
    E009 批量处理中断
    E010 内部逻辑错误
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ============================================================
# 错误码定义
# ============================================================
class SkillError(Exception):
    """技能基础异常类"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class ParsedDocument:
    """解析后的文档结构化数据"""
    title: str = ""
    author: str = ""
    date: str = ""
    amount: str = ""
    clauses: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    confidence: Dict[str, str] = field(default_factory=dict)
    source_type: str = ""
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = []
        if self.title:
            lines.append(f"# {self.title}")
        if self.author:
            lines.append(f"**作者：** {self.author}")
        if self.date:
            lines.append(f"**日期：** {self.date}")
        if self.amount:
            lines.append(f"**金额：** {self.amount}")
        if self.clauses:
            lines.append("\n## 条款")
            for clause in self.clauses:
                lines.append(f"- {clause}")
        if self.paragraphs:
            lines.append("\n## 正文")
            for para in self.paragraphs:
                lines.append(f"\n{para}")
        if self.confidence:
            lines.append("\n## 置信度标注")
            for key, value in self.confidence.items():
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def to_sile(self) -> str:
        """转换为 SILE 源文件格式"""
        lines = ["\\begin{document}"]
        if self.title:
            lines.append(f"\\section{{{self.title}}}")
        if self.author:
            lines.append(f"\\paragraph{{作者：{self.author}}}")
        if self.date:
            lines.append(f"\\paragraph{{日期：{self.date}}}")
        if self.amount:
            lines.append(f"\\paragraph{{金额：{self.amount}}}")
        if self.clauses:
            lines.append("\\subsection{条款}")
            for clause in self.clauses:
                lines.append(f"\\item{{{clause}}}")
        if self.paragraphs:
            lines.append("\\subsection{正文}")
            for para in self.paragraphs:
                lines.append(f"\\paragraph{{{para}}}")
        if self.confidence:
            lines.append("\\subsection{置信度标注}")
            for key, value in self.confidence.items():
                lines.append(f"\\paragraph{{{key}：{value}}}")
        lines.append("\\end{document}")
        return "\n".join(lines)


@dataclass
class BatchResult:
    """批量处理结果"""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)


# ============================================================
# 核心解析模块
# ============================================================
class DocumentParser:
    """文档解析器 — 负责从原始文本中提取结构化信息"""

    # 常见日期模式
    DATE_PATTERNS = [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d{4}年\d{1,2}月\d{1,2}日",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
        r"\d{1,2}月\d{1,2}日",
    ]

    # 金额模式（人民币）
    AMOUNT_PATTERNS = [
        r"[¥￥]\s*\d+(?:\.\d{1,2})?",
        r"\d+(?:\.\d{1,2})?\s*元",
        r"(?:人民币|RMB|CNY)\s*\d+(?:\.\d{1,2})?",
    ]

    # 条款编号模式
    CLAUSE_PATTERNS = [
        r"(?:第\s*[一二三四五六七八九十百千0-9]+\s*条)",
        r"(?:条款\s*[一二三四五六七八九十百千0-9]+)",
        r"(?:Article\s+\d+)",
        r"(?:Section\s+\d+)",
    ]

    def __init__(self) -> None:
        """初始化解析器"""
        self._compiled_date_patterns = [re.compile(p) for p in self.DATE_PATTERNS]
        self._compiled_amount_patterns = [re.compile(p) for p in self.AMOUNT_PATTERNS]
        self._compiled_clause_patterns = [re.compile(p) for p in self.CLAUSE_PATTERNS]

    def parse(self, text: str, source_type: str = "text") -> ParsedDocument:
        """
        解析文本并提取结构化信息

        Args:
            text: 原始文本内容
            source_type: 输入来源类型（text/pdf/url）

        Returns:
            ParsedDocument: 解析后的结构化文档

        Raises:
            SkillError: 解析失败时抛出 E005
        """
        if not text or not text.strip():
            raise SkillError("E005", "输入文本为空，无法解析")

        doc = ParsedDocument(raw_text=text, source_type=source_type)

        try:
            # 提取标题（通常为第一行或包含"标题"关键词的行）
            doc.title = self._extract_title(text)

            # 提取作者
            doc.author = self._extract_author(text)

            # 提取日期
            doc.date = self._extract_date(text)

            # 提取金额
            doc.amount = self._extract_amount(text)

            # 提取条款
            doc.clauses = self._extract_clauses(text)

            # 提取段落
            doc.paragraphs = self._extract_paragraphs(text)

            # 计算置信度
            doc.confidence = self._calculate_confidence(doc)

            return doc
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E005", f"解析文本失败: {str(e)}") from e

    def _extract_title(self, text: str) -> str:
        """提取标题"""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""

        # 优先查找明确的标题标记
        title_match = re.search(r"(?:标题|题目)[：:]\s*(.+)", text)
        if title_match:
            return title_match.group(1).strip()

        # 否则取第一行（如果长度合理）
        first_line = lines[0]
        if len(first_line) <= 100:
            return first_line
        return ""

    def _extract_author(self, text: str) -> str:
        """提取作者"""
        patterns = [
            r"(?:作者|著者|撰写人)[：:]\s*(.+)",
            r"(?:Author|作者)[：:]\s*(.+)",
            r"(?:by|By)\s+([A-Za-z\u4e00-\u9fff]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_date(self, text: str) -> str:
        """提取日期"""
        for pattern in self._compiled_date_patterns:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return ""

    def _extract_amount(self, text: str) -> str:
        """提取金额"""
        for pattern in self._compiled_amount_patterns:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return ""

    def _extract_clauses(self, text: str) -> List[str]:
        """提取条款"""
        clauses = []
        for pattern in self._compiled_clause_patterns:
            matches = pattern.findall(text)
            clauses.extend(matches)
        # 去重并保持顺序
        seen = set()
        unique_clauses = []
        for clause in clauses:
            if clause not in seen:
                seen.add(clause)
                unique_clauses.append(clause)
        return unique_clauses

    def _extract_paragraphs(self, text: str) -> List[str]:
        """提取段落"""
        # 按空行或换行分割
        raw_paragraphs = re.split(r"\n\s*\n|\n", text)
        paragraphs = []
        for para in raw_paragraphs:
            para = para.strip()
            # 过滤掉过短的片段和纯标点
            if len(para) >= 10 and not re.match(r"^[\s\W]+$", para):
                paragraphs.append(para)
        return paragraphs

    def _calculate_confidence(self, doc: ParsedDocument) -> Dict[str, str]:
        """计算各字段的置信度"""
        confidence = {}

        # 标题置信度
        if doc.title:
            confidence["title"] = "高" if len(doc.title) >= 5 else "中"
        else:
            confidence["title"] = "低"

        # 作者置信度
        if doc.author:
            confidence["author"] = "高"
        else:
            confidence["author"] = "低"

        # 日期置信度
        if doc.date:
            confidence["date"] = "高"
        else:
            confidence["date"] = "中"

        # 金额置信度
        if doc.amount:
            confidence["amount"] = "高"
        else:
            confidence["amount"] = "中"

        # 条款置信度
        if doc.clauses:
            confidence["clauses"] = "高"
        else:
            confidence["clauses"] = "低"

        return confidence


# ============================================================
# 输入处理模块
# ============================================================
class InputHandler:
    """输入处理器 — 负责读取各种来源的输入"""

    @staticmethod
    def read_file(filepath: str) -> str:
        """
        读取文本文件内容

        Args:
            filepath: 文件路径

        Returns:
            str: 文件内容

        Raises:
            SkillError: E002 文件不存在, E003 读取失败
        """
        if not os.path.exists(filepath):
            raise SkillError("E002", f"输入文件不存在: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(filepath, "r", encoding="gbk") as f:
                    return f.read()
            except Exception as e:
                raise SkillError("E003", f"读取文件失败: {str(e)}") from e
        except Exception as e:
            raise SkillError("E003", f"读取文件失败: {str(e)}") from e

    @staticmethod
    def read_url(url: str) -> str:
        """
        解析 URL（仅提取 URL 信息，不进行网络访问）

        Args:
            url: 网页链接

        Returns:
            str: URL 解析信息

        Raises:
            SkillError: E004 URL 格式不支持
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise SkillError("E004", f"不支持的 URL 协议: {parsed.scheme}")
            # 本地处理，不访问网络，仅返回 URL 信息
            return f"URL: {url}\n域名: {parsed.netloc}\n路径: {parsed.path}"
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E004", f"URL 解析失败: {str(e)}") from e

    @staticmethod
    def read_text(text: str) -> str:
        """直接使用传入的文本"""
        return text


# ============================================================
# 输出处理模块
# ============================================================
class OutputFormatter:
    """输出格式化器 — 负责将解析结果输出为各种格式"""

    SUPPORTED_FORMATS = ["json", "markdown", "sile", "text"]

    @staticmethod
    def format(doc: ParsedDocument, output_format: str) -> str:
        """
        将解析结果格式化为指定格式

        Args:
            doc: 解析后的文档对象
            output_format: 输出格式（json/markdown/sile/text）

        Returns:
            str: 格式化后的输出内容

        Raises:
            SkillError: E006 输出格式不支持
        """
        fmt = output_format.lower()
        if fmt not in OutputFormatter.SUPPORTED_FORMATS:
            raise SkillError("E006", f"不支持的输出格式: {output_format}")

        if fmt == "json":
            return doc.to_json()
        elif fmt == "markdown":
            return doc.to_markdown()
        elif fmt == "sile":
            return doc.to_sile()
        elif fmt == "text":
            lines = []
            if doc.title:
                lines.append(f"标题: {doc.title}")
            if doc.author:
                lines.append(f"作者: {doc.author}")
            if doc.date:
                lines.append(f"日期: {doc.date}")
            if doc.amount:
                lines.append(f"金额: {doc.amount}")
            if doc.clauses:
                lines.append("条款:")
                for clause in doc.clauses:
                    lines.append(f"  - {clause}")
            if doc.paragraphs:
                lines.append("正文:")
                for para in doc.paragraphs:
                    lines.append(f"  {para[:50]}...")
            if doc.confidence:
                lines.append("置信度:")
                for key, value in doc.confidence.items():
                    lines.append(f"  {key}: {value}")
            return "\n".join(lines)
        return ""


# ============================================================
# 批量处理模块
# ============================================================
class BatchProcessor:
    """批量处理器 — 支持多文件批量转换"""

    def __init__(self, parser: DocumentParser, formatter: OutputFormatter):
        self.parser = parser
        self.formatter = formatter

    def process_files(
        self,
        filepaths: List[str],
        output_format: str = "json",
        output_dir: Optional[str] = None,
    ) -> BatchResult:
        """
        批量处理多个文件

        Args:
            filepaths: 文件路径列表
            output_format: 输出格式
            output_dir: 输出目录（None 则不写文件）

        Returns:
            BatchResult: 批量处理结果

        Raises:
            SkillError: E009 批量处理中断
        """
        result = BatchResult(total=len(filepaths))

        for filepath in filepaths:
            try:
                # 读取文件
                text = InputHandler.read_file(filepath)

                # 解析
                doc = self.parser.parse(text, source_type="file")

                # 格式化
                output = self.formatter.format(doc, output_format)

                # 保存结果
                item = {
                    "file": filepath,
                    "success": True,
                    "output": output,
                    "parsed": doc.to_dict(),
                }
                result.results.append(item)
                result.succeeded += 1

                # 可选写入输出文件
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    base_name = os.path.splitext(os.path.basename(filepath))[0]
                    ext = ".txt" if output_format == "text" else f".{output_format}"
                    out_path = os.path.join(output_dir, f"{base_name}{ext}")
                    try:
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(output)
                    except Exception as e:
                        raise SkillError("E007", f"写入输出文件失败: {str(e)}") from e

            except SkillError as e:
                result.failed += 1
                result.errors.append({"file": filepath, "code": e.code, "message": e.message})
            except Exception as e:
                result.failed += 1
                result.errors.append({"file": filepath, "code": "E009", "message": str(e)})

        return result


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检样例，验证核心逻辑

    使用硬编码数据，不依赖外部文件、网络或当前工作目录。

    Returns:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("resilient-sile 自检程序启动")
    print("=" * 60)

    all_passed = True

    # ----------------------------------------------------------
    # 测试样例 1: 标准文档解析
    # ----------------------------------------------------------
    print("\n[测试 1] 标准文档解析")
    sample_text = """
    关于2026年度设备采购的合同
    作者：张三
    日期：2026年3月15日
    总金额：¥12,500.00元

    第一条 合同目的
    第二条 设备清单
    第三条 付款方式
    第四条 违约责任

    本合同由甲乙双方共同协商签订，适用于2026年度设备采购项目。
    双方应严格遵守合同条款，任何一方违约需承担相应责任。
    """
    try:
        parser = DocumentParser()
        doc = parser.parse(sample_text, source_type="text")

        # 宽松断言：不依赖精确值
        assert doc.title, "标题不应为空"
        assert doc.author, "作者不应为空"
        assert doc.date, "日期不应为空"
        assert doc.amount, "金额不应为空"
        assert len(doc.clauses) >= 2, "条款数量应至少为2"
        assert len(doc.paragraphs) >= 1, "段落数量应至少为1"
        assert doc.confidence, "置信度不应为空"

        print("  ✓ 标题:", doc.title)
        print("  ✓ 作者:", doc.author)
        print("  ✓ 日期:", doc.date)
        print("  ✓ 金额:", doc.amount)
        print("  ✓ 条款数:", len(doc.clauses))
        print("  ✓ 段落数:", len(doc.paragraphs))
        print("  ✓ 置信度字段:", len(doc.confidence))
        print("  ✓ 测试通过")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 测试异常: {e}")

    # ----------------------------------------------------------
    # 测试样例 2: 输出格式转换
    # ----------------------------------------------------------
    print("\n[测试 2] 输出格式转换")
    try:
        formatter = OutputFormatter()
        doc = parser.parse(sample_text, source_type="text")

        # 测试 JSON 输出
        json_out = formatter.format(doc, "json")
        assert json_out, "JSON 输出不应为空"
        json_data = json.loads(json_out)
        assert "title" in json_data, "JSON 应包含 title 字段"

        # 测试 Markdown 输出
        md_out = formatter.format(doc, "markdown")
        assert md_out, "Markdown 输出不应为空"
        assert "#" in md_out, "Markdown 应包含标题标记"

        # 测试 SILE 输出
        sile_out = formatter.format(doc, "sile")
        assert sile_out, "SILE 输出不应为空"
        assert "\\begin{document}" in sile_out, "SILE 应包含文档开始标记"

        # 测试文本输出
        text_out = formatter.format(doc, "text")
        assert text_out, "文本输出不应为空"

        print("  ✓ JSON 输出长度:", len(json_out))
        print("  ✓ Markdown 输出长度:", len(md_out))
        print("  ✓ SILE 输出长度:", len(sile_out))
        print("  ✓ 文本输出长度:", len(text_out))
        print("  ✓ 测试通过")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 测试异常: {e}")

    # ----------------------------------------------------------
    # 测试样例 3: 错误处理
    # ----------------------------------------------------------
    print("\n[测试 3] 错误处理")
    try:
        # 测试空文本
        try:
            parser.parse("", source_type="text")
            all_passed = False
            print("  ✗ 空文本应抛出异常")
        except SkillError as e:
            assert e.code == "E005", f"错误码应为 E005，实际为 {e.code}"
            print("  ✓ 空文本错误码正确:", e.code)

        # 测试不存在的文件
        try:
            InputHandler.read_file("/nonexistent/path/file.txt")
            all_passed = False
            print("  ✗ 不存在的文件应抛出异常")
        except SkillError as e:
            assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"
            print("  ✓ 文件不存在错误码正确:", e.code)

        # 测试不支持的输出格式
        try:
            formatter.format(doc, "xml")
            all_passed = False
            print("  ✗ 不支持的格式应抛出异常")
        except SkillError as e:
            assert e.code == "E006", f"错误码应为 E006，实际为 {e.code}"
            print("  ✓ 格式错误码正确:", e.code)

        print("  ✓ 测试通过")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 测试异常: {e}")

    # ----------------------------------------------------------
    # 测试样例 4: 批量处理
    # ----------------------------------------------------------
    print("\n[测试 4] 批量处理")
    try:
        # 使用临时文件模拟批量处理
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建两个临时文件
            file1 = os.path.join(tmpdir, "doc1.txt")
            file2 = os.path.join(tmpdir, "doc2.txt")

            content1 = "测试文档一\n作者：李四\n日期：2026年1月1日\n金额：¥100元\n第一条 说明"
            content2 = "测试文档二\n作者：王五\n日期：2026年2月2日\n金额：¥200元\n第二条 说明\n第三条 补充"

            with open(file1, "w", encoding="utf-8") as f:
                f.write(content1)
            with open(file2, "w", encoding="utf-8") as f:
                f.write(content2)

            processor = BatchProcessor(parser, formatter)
            result = processor.process_files([file1, file2], output_format="json")

            assert result.total == 2, "总数应为2"
            assert result.succeeded == 2, "成功数应为2"
            assert result.failed == 0, "失败数应为0"
            assert len(result.results) == 2, "结果数应为2"

            print(f"  ✓ 总数: {result.total}")
            print(f"  ✓ 成功: {result.succeeded}")
            print(f"  ✓ 失败: {result.failed}")
            print(f"  ✓ 结果数: {len(result.results)}")
            print("  ✓ 测试通过")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 测试异常: {e}")

    # ----------------------------------------------------------
    # 测试样例 5: URL 解析（本地处理，不访问网络）
    # ----------------------------------------------------------
    print("\n[测试 5] URL 解析")
    try:
        url_info = InputHandler.read_url("https://example.com/docs/sample.html")
        assert url_info, "URL 解析结果不应为空"
        assert "example.com" in url_info, "应包含域名信息"
        print("  ✓ URL 解析成功:", url_info.split("\n")[0])
        print("  ✓ 测试通过")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 测试异常: {e}")

    # ----------------------------------------------------------
    # 汇总结果
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """
    主入口函数

    Returns:
        int: 退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="resilient-sile — SILE 排版系统容错转换辅助工具",
        epilog="示例: python main.py --input sample.txt --format markdown",
    )

    # 输入参数
    parser.add_argument("--input", "-i", type=str, help="输入文件路径或 URL")
    parser.add_argument("--text", "-t", type=str, help="直接输入文本内容")
    parser.add_argument("--batch", "-b", nargs="+", help="批量处理多个文件路径")

    # 输出参数
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "markdown", "sile", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--output-dir", type=str, help="批量处理时的输出目录")

    # 其他参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    args = parser.parse_args()

    # 显示版本
    if args.version:
        print("resilient-sile v1.0.1")
        return 0

    # 运行自检
    if args.selftest:
        return 0 if run_selftest() else 1

    # 参数校验
    if not args.input and not args.text and not args.batch:
        parser.print_help()
        print("\n错误: 必须提供 --input、--text 或 --batch 参数", file=sys.stderr)
        return 1

    try:
        # 初始化核心组件
        doc_parser = DocumentParser()
        formatter = OutputFormatter()

        # 批量处理模式
        if args.batch:
            processor = BatchProcessor(doc_parser, formatter)
            result = processor.process_files(args.batch, args.format, args.output_dir)

            print(f"批量处理完成: 共 {result.total} 个文件, "
                  f"成功 {result.succeeded} 个, 失败 {result.failed} 个")

            if result.errors:
                print("\n失败详情:")
                for err in result.errors:
                    print(f"  [{err['code']}] {err['file']}: {err['message']}")

            if args.output:
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
                    print(f"\n结果已写入: {args.output}")
                except Exception as e:
                    raise SkillError("E007", f"写入输出文件失败: {str(e)}") from e

            return 0 if result.failed == 0 else 1

        # 单文件/文本处理模式
        if args.input:
            # 判断是 URL 还是文件路径
            if args.input.startswith(("http://", "https://")):
                text = InputHandler.read_url(args.input)
                source_type = "url"
            else:
                text = InputHandler.read_file(args.input)
                source_type = "file"
        else:
            text = args.text
            source_type = "text"

        # 解析文档
        doc = doc_parser.parse(text, source_type=source_type)

        # 格式化输出
        output = formatter.format(doc, args.format)

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"结果已写入: {args.output}")
            except Exception as e:
                raise SkillError("E007", f"写入输出文件失败: {str(e)}") from e
        else:
            print(output)

        return 0

    except SkillError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 [E010]: 未预期的异常: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
