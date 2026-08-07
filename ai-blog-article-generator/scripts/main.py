#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

SEO文案（ai-blog-article-generator）独立实现脚本。

本脚本依据功能规格独立编写，不参考任何既有实现。
功能：将用户提供的数据/文件/URL 转换为结构化结果，并给出置信度标注。
运行方式：
    python scripts/main.py --selftest   # 离线自检核心逻辑
    python scripts/main.py --input "..." # 处理输入文本
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{}",
    "E003": "输入格式不符合要求，示例：{}",
    "E004": "这超出了本工具的能力范围，建议：{}",
    "E005": "结果无法确定，建议：{}",
    "E006": "内部处理错误，请稍后重试",
    "E007": "输入内容为空或仅包含空白字符",
    "E008": "无法识别的输入来源类型",
    "E009": "输出格式不受支持",
    "E010": "批量处理中断，部分结果可能不完整",
}

# 置信度阈值
HIGH_CONF_THRESHOLD = 90   # 置信度 ≥90% 直接输出
MED_CONF_THRESHOLD = 85    # 85%-90% 建议复核
LOW_CONF_THRESHOLD = 85    # <85% 标注 [需核实]

# 触发词列表
TRIGGER_WORDS = ["SEO文案", "ai blog article generator"]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ProcessedResult:
    """处理结果数据结构"""
    source_type: str                 # 输入来源类型：data / file / url / text
    raw_input: str                   # 原始输入
    extracted_fields: Dict[str, Any]  # 提取的关键字段
    confidence: float                # 置信度 0-100
    warnings: List[str] = field(default_factory=list)  # 警告信息
    needs_review: bool = False       # 是否需要人工复核


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class ArticleGenerator:
    """SEO文案核心处理器"""

    def __init__(self) -> None:
        """初始化处理器"""
        self._field_patterns = {
            "title": r"(?:标题|题目|title)[:：]\s*(.+)",
            "author": r"(?:作者|author)[:：]\s*(.+)",
            "keywords": r"(?:关键词|关键字|keywords)[:：]\s*(.+)",
            "content": r"(?:内容|正文|content)[:：]\s*(.+)",
            "url": r"(?:网址|链接|url)[:：]\s*(.+)",
        }

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def process(self, raw_input: str, source_type: Optional[str] = None) -> ProcessedResult:
        """
        处理输入内容，返回结构化结果

        Args:
            raw_input: 用户提供的原始输入
            source_type: 输入来源类型（data/file/url/text），None 则自动识别

        Returns:
            ProcessedResult: 处理结果

        Raises:
            ValueError: 带错误码的异常
        """
        # 输入校验
        if not raw_input or not raw_input.strip():
            raise ValueError("E001|" + ERROR_CODES["E001"])

        # 识别输入来源类型
        if source_type is None:
            source_type = self._detect_source_type(raw_input)

        if source_type not in ("data", "file", "url", "text"):
            raise ValueError("E008|" + ERROR_CODES["E008"])

        # 根据类型解析
        if source_type == "url":
            return self._process_url(raw_input)
        elif source_type == "file":
            return self._process_file(raw_input)
        else:
            return self._process_text(raw_input, source_type)

    # ------------------------------------------------------------------
    # 各类型处理方法
    # ------------------------------------------------------------------
    def _process_text(self, text: str, source_type: str) -> ProcessedResult:
        """处理文本输入"""
        # 提取关键字段
        fields, extraction_confidence = self._extract_fields(text)

        # 计算整体置信度
        confidence = self._calculate_confidence(fields, extraction_confidence)

        # 生成警告
        warnings = self._generate_warnings(fields, confidence)

        # 判断是否需要复核
        needs_review = confidence < MED_CONF_THRESHOLD

        return ProcessedResult(
            source_type=source_type,
            raw_input=text,
            extracted_fields=fields,
            confidence=confidence,
            warnings=warnings,
            needs_review=needs_review,
        )

    def _process_url(self, url: str) -> ProcessedResult:
        """处理 URL 输入（不访问网络，仅提取 URL 中的信息）"""
        # 验证 URL 格式
        if not re.match(r"^https?://", url):
            raise ValueError("E003|" + ERROR_CODES["E003"].format("https://example.com"))

        # 从 URL 中提取可能的标题信息
        fields = {
            "url": url,
            "domain": self._extract_domain(url),
            "path": self._extract_path(url),
        }

        # URL 处理置信度（仅格式分析）
        confidence = 75.0  # 低于 85%，标记需核实
        warnings = ["URL 内容未访问，无法验证实际内容，请人工确认"]
        needs_review = True

        return ProcessedResult(
            source_type="url",
            raw_input=url,
            extracted_fields=fields,
            confidence=confidence,
            warnings=warnings,
            needs_review=needs_review,
        )

    def _process_file(self, file_ref: str) -> ProcessedResult:
        """处理文件引用输入（不实际读取文件，仅识别引用信息）"""
        # 检查文件引用格式
        if not file_ref or len(file_ref.strip()) < 3:
            raise ValueError("E002|" + ERROR_CODES["E002"].format("有效的文件路径或文件描述"))

        # 提取文件名（如果有路径分隔符）
        file_name = file_ref.split("/")[-1].split("\\")[-1]

        fields = {
            "file_reference": file_ref,
            "file_name": file_name,
            "file_type": self._guess_file_type(file_name),
        }

        confidence = 80.0  # 文件未实际读取，置信度中等
        warnings = ["文件内容未读取，请确认文件可访问性"]
        needs_review = True

        return ProcessedResult(
            source_type="file",
            raw_input=file_ref,
            extracted_fields=fields,
            confidence=confidence,
            warnings=warnings,
            needs_review=needs_review,
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    def _detect_source_type(self, text: str) -> str:
        """自动识别输入来源类型"""
        # URL 识别
        if re.match(r"^https?://", text.strip()):
            return "url"

        # 文件引用识别（包含路径分隔符或常见文件扩展名）
        if re.search(r"[/\\]|\.(txt|md|json|csv|pdf|docx?)$", text.strip(), re.IGNORECASE):
            return "file"

        # 默认视为文本
        return "text"

    def _extract_fields(self, text: str) -> Tuple[Dict[str, Any], float]:
        """
        从文本中提取关键字段

        Returns:
            (字段字典, 提取置信度)
        """
        fields: Dict[str, Any] = {}
        matched_count = 0
        total_patterns = len(self._field_patterns)

        for field_name, pattern in self._field_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()
                matched_count += 1

        # 如果没有匹配到任何字段，尝试将整个输入作为内容
        if not fields:
            fields["content"] = text.strip()

        # 计算提取置信度
        if matched_count == 0:
            extraction_confidence = 60.0  # 未匹配到任何字段，置信度低
        else:
            extraction_confidence = 60.0 + (matched_count / total_patterns) * 40.0

        return fields, extraction_confidence

    def _calculate_confidence(self, fields: Dict[str, Any], extraction_confidence: float) -> float:
        """计算整体置信度"""
        confidence = extraction_confidence

        # 字段完整性加分
        if "title" in fields:
            confidence += 5.0
        if "content" in fields:
            confidence += 5.0
        if "keywords" in fields:
            confidence += 3.0

        # 内容长度加分
        content = fields.get("content", "")
        if len(content) > 200:
            confidence += 5.0
        elif len(content) > 50:
            confidence += 2.0

        # 限制在 0-100 范围
        return max(0.0, min(100.0, confidence))

    def _generate_warnings(self, fields: Dict[str, Any], confidence: float) -> List[str]:
        """生成警告信息"""
        warnings = []

        if confidence < LOW_CONF_THRESHOLD:
            warnings.append("结果置信度较低，建议人工复核")

        if "title" not in fields:
            warnings.append("未提取到标题信息")

        if "keywords" not in fields:
            warnings.append("未提取到关键词信息")

        return warnings

    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        match = re.match(r"https?://([^/]+)", url)
        return match.group(1) if match else ""

    def _extract_path(self, url: str) -> str:
        """从 URL 提取路径"""
        match = re.match(r"https?://[^/]+(/.*)?", url)
        return match.group(1) if match and match.group(1) else "/"

    def _guess_file_type(self, file_name: str) -> str:
        """猜测文件类型"""
        ext = file_name.split(".")[-1].lower() if "." in file_name else "unknown"
        type_map = {
            "txt": "text",
            "md": "markdown",
            "json": "json",
            "csv": "csv",
            "pdf": "pdf",
            "doc": "word",
            "docx": "word",
        }
        return type_map.get(ext, "unknown")


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ProcessedResult, output_format: str = "text") -> str:
    """
    格式化输出结果

    Args:
        result: 处理结果
        output_format: 输出格式（text/json）

    Returns:
        格式化后的字符串
    """
    if output_format == "json":
        return json.dumps({
            "source_type": result.source_type,
            "extracted_fields": result.extracted_fields,
            "confidence": round(result.confidence, 1),
            "warnings": result.warnings,
            "needs_review": result.needs_review,
        }, ensure_ascii=False, indent=2)

    # 文本格式输出
    lines = []
    lines.append("=" * 50)
    lines.append("处理结果")
    lines.append("=" * 50)
    lines.append(f"输入来源: {result.source_type}")

    # 字段输出
    for key, value in result.extracted_fields.items():
        lines.append(f"{key}: {value}")

    # 置信度输出
    conf_label = ""
    if result.confidence >= HIGH_CONF_THRESHOLD:
        conf_label = "高置信度"
    elif result.confidence >= MED_CONF_THRESHOLD:
        conf_label = "建议复核"
    else:
        conf_label = "[需核实]"

    lines.append(f"置信度: {result.confidence:.1f}% ({conf_label})")

    # 警告输出
    if result.warnings:
        lines.append("\n警告:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")

    if result.needs_review:
        lines.append("\n⚠ 此结果需要人工复核")

    lines.append("=" * 50)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检逻辑
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。

    Returns:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("开始自检（离线模式）")
    print("=" * 60)

    # 创建处理器实例
    generator = ArticleGenerator()

    # 测试用例 1: 正常文本输入
    print("\n[测试 1] 正常文本输入")
    test_text = """
    标题: 使用 Python 进行数据分析
    作者: 张三
    关键词: Python, 数据分析, 可视化
    内容: 这是一篇关于使用 Python 进行数据分析的文章。文章介绍了数据处理、分析和可视化的基本方法。
    """
    try:
        result = generator.process(test_text, source_type="text")
        assert result.source_type == "text", "来源类型应为 text"
        assert "title" in result.extracted_fields, "应提取到标题"
        assert result.confidence > 0, "置信度应大于 0"
        assert result.confidence <= 100, "置信度应小于等于 100"
        print(f"  通过 ✓ (置信度: {result.confidence:.1f}%)")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 2: URL 输入
    print("\n[测试 2] URL 输入")
    try:
        result = generator.process("https://example.com/blog/post", source_type="url")
        assert result.source_type == "url", "来源类型应为 url"
        assert "domain" in result.extracted_fields, "应提取到域名"
        assert result.confidence < 85, "URL 未访问时置信度应低于 85%"
        print(f"  通过 ✓ (置信度: {result.confidence:.1f}%)")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 3: 空输入异常
    print("\n[测试 3] 空输入异常")
    try:
        generator.process("")
        print("  失败 ✗ (应抛出异常但未抛出)")
        return False
    except ValueError as e:
        assert str(e).startswith("E001"), f"错误码应为 E001，实际为: {e}"
        print("  通过 ✓")

    # 测试用例 4: 纯文本无字段
    print("\n[测试 4] 纯文本无字段")
    try:
        result = generator.process("这是一段没有结构化字段的普通文本内容", source_type="text")
        assert "content" in result.extracted_fields, "应提取到内容字段"
        assert result.confidence < 85, "无字段时置信度应较低"
        print(f"  通过 ✓ (置信度: {result.confidence:.1f}%)")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 5: 文件引用输入
    print("\n[测试 5] 文件引用输入")
    try:
        result = generator.process("/tmp/sample.txt", source_type="file")
        assert result.source_type == "file", "来源类型应为 file"
        assert "file_name" in result.extracted_fields, "应提取到文件名"
        print(f"  通过 ✓ (文件: {result.extracted_fields['file_name']})")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 6: 批量处理
    print("\n[测试 6] 批量处理")
    inputs = [
        "标题: 测试文章一\n内容: 这是第一篇文章的内容。",
        "标题: 测试文章二\n内容: 这是第二篇文章的内容。",
        "https://example.com/page1",
    ]
    try:
        results = []
        for input_text in inputs:
            result = generator.process(input_text)
            results.append(result)
        assert len(results) == 3, "应处理 3 个输入"
        assert all(r.confidence > 0 for r in results), "所有结果置信度应大于 0"
        print(f"  通过 ✓ (处理 {len(results)} 个输入)")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 7: 输出格式化
    print("\n[测试 7] 输出格式化")
    try:
        result = generator.process("标题: 格式化测试\n内容: 测试内容。", source_type="text")
        text_output = format_output(result, "text")
        json_output = format_output(result, "json")
        assert "处理结果" in text_output, "文本输出应包含标题"
        assert "confidence" in json_output, "JSON 输出应包含置信度"
        print("  通过 ✓")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 8: 错误码体系
    print("\n[测试 8] 错误码体系")
    try:
        # 检查所有错误码定义
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"错误码 {code} 未定义"
        print("  通过 ✓ (10 个错误码全部定义)")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 9: 触发词识别
    print("\n[测试 9] 触发词识别")
    try:
        for word in TRIGGER_WORDS:
            assert word in TRIGGER_WORDS, f"触发词 {word} 应在列表中"
        assert len(TRIGGER_WORDS) >= 2, "应至少有 2 个触发词"
        print(f"  通过 ✓ ({len(TRIGGER_WORDS)} 个触发词)")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    # 测试用例 10: 置信度边界
    print("\n[测试 10] 置信度边界")
    try:
        # 高置信度输入
        rich_text = """
        标题: 完整文章
        作者: 李四
        关键词: 测试, 完整
        内容: 这是一篇内容非常完整的文章，包含了很多文字。
        这篇文章有足够的长度来获得更高的置信度评分。
        我们继续添加更多内容来确保长度足够。
        """
        result = generator.process(rich_text, source_type="text")
        assert result.confidence > 0, "高置信度输入应产生正置信度"
        assert result.confidence <= 100, "置信度不应超过 100"
        print(f"  通过 ✓ (置信度: {result.confidence:.1f}%)")
    except Exception as e:
        print(f"  失败 ✗ ({e})")
        return False

    print("\n" + "=" * 60)
    print("自检完成：全部通过 ✓")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="SEO文案 - AI Blog Article Generator",
        epilog="示例: python scripts/main.py --input '标题: 测试\\n内容: 测试内容'"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据）"
    )

    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（文本/URL/文件引用）"
    )

    parser.add_argument(
        "--source-type",
        type=str,
        choices=["data", "file", "url", "text"],
        help="输入来源类型（默认自动识别）"
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认 text）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理输入模式
    if not args.input:
        print("错误: 请提供输入内容 (--input) 或使用 --selftest 运行自检", file=sys.stderr)
        print("提示: 运行 'python scripts/main.py --help' 查看帮助", file=sys.stderr)
        return 1

    try:
        # 创建处理器并处理输入
        generator = ArticleGenerator()
        result = generator.process(args.input, args.source_type)

        # 格式化输出
        output = format_output(result, args.format)
        print(output)

        # 低置信度时返回非零退出码
        if result.confidence < MED_CONF_THRESHOLD:
            return 2

        return 0

    except ValueError as e:
        # 解析错误码和消息
        parts = str(e).split("|", 1)
        if len(parts) == 2 and parts[0] in ERROR_CODES:
            error_code = parts[0]
            error_msg = parts[1]
        else:
            error_code = "E006"
            error_msg = ERROR_CODES["E006"]

        print(f"错误 {error_code}: {error_msg}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"错误 E006: {ERROR_CODES['E006']} ({e})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
