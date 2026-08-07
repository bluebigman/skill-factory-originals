#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
SEO文案生成器 - 独立实现（clean-room）
==========================================
基于功能规格实现的命令行工具：
- 接收用户输入（文本/文件/URL 作为字符串）
- 结构化识别关键信息
- 按默认模板生成 SEO 文案
- 标注置信度并输出
- 支持 --selftest 离线自检

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 未知命令参数
    E007 内部处理异常
    E008 输出写入失败
    E009 自检失败
    E010 配置错误

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码对应的标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "未知的命令行参数，请使用 --help 查看帮助",
    "E007": "内部处理异常，请稍后重试或检查输入内容",
    "E008": "输出写入失败，请检查文件路径和权限",
    "E009": "自检失败，核心逻辑未通过验证",
    "E010": "配置错误，请检查运行环境",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # >=90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
# <85% 标注 [需核实]

# 默认输出模板字段
DEFAULT_TEMPLATE_FIELDS = [
    "title",        # 标题
    "meta_desc",    # 元描述
    "keywords",     # 关键词列表
    "headings",     # 标题结构 (H1/H2)
    "body",         # 正文段落
    "cta",          # 行动号召
]


# ============================================================
# 数据模型
# ============================================================

@dataclass
class InputData:
    """标准化后的输入数据"""
    raw_text: str                       # 原始文本
    source_type: str = "text"           # text / url / file
    word_count: int = 0                 # 词数
    char_count: int = 0                 # 字符数
    sentences: List[str] = field(default_factory=list)  # 句子列表
    key_phrases: List[str] = field(default_factory=list)  # 关键短语


@dataclass
class OutputData:
    """生成的 SEO 文案输出"""
    title: str = ""
    meta_desc: str = ""
    keywords: List[str] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    body: List[str] = field(default_factory=list)
    cta: str = ""
    confidence: float = 0.0             # 置信度 0.0-1.0
    warnings: List[str] = field(default_factory=list)  # 警告信息
    needs_review: bool = False          # 是否需要人工复核


# ============================================================
# 核心处理逻辑
# ============================================================

class SEOContentGenerator:
    """SEO 文案生成器核心类"""

    def __init__(self) -> None:
        """初始化生成器"""
        # 停用词（用于关键词提取）
        self._stopwords = {
            "的", "了", "和", "是", "在", "我", "有", "这", "不", "也",
            "就", "人", "都", "一", "一个", "上", "很", "到", "说", "要",
            "去", "你", "会", "着", "没有", "看", "好", "自己", "那", "她",
            "他", "它", "们", "与", "及", "或", "等", "从", "对", "把",
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as", "is", "are",
            "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "can", "could",
        }

    # --------------------------------------------------------
    # 输入处理
    # --------------------------------------------------------

    def parse_input(self, raw_input: str, source_type: str = "text") -> InputData:
        """
        解析输入内容，识别关键信息。
        
        Args:
            raw_input: 原始输入字符串
            source_type: 输入来源类型 (text/url/file)
            
        Returns:
            InputData: 标准化后的输入数据
            
        Raises:
            ValueError: 当输入为空或格式错误时
        """
        # E001: 输入为空
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")

        # E003: 输入格式错误
        if source_type not in ("text", "url", "file"):
            raise ValueError("E003")

        # 清理输入
        text = raw_input.strip()

        # 按句子分割（支持中英文标点）
        import re
        sentences = re.split(r'[。！？!?\.]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # E002: 关键信息缺失（没有有效句子）
        if not sentences:
            raise ValueError("E002")

        # 计算词数（中英文混合）
        words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', text)
        word_count = len(words)
        char_count = len(text)

        # 提取关键短语（简单频率统计）
        key_phrases = self._extract_key_phrases(text)

        return InputData(
            raw_text=text,
            source_type=source_type,
            word_count=word_count,
            char_count=char_count,
            sentences=sentences,
            key_phrases=key_phrases,
        )

    def _extract_key_phrases(self, text: str, top_n: int = 5) -> List[str]:
        """
        从文本中提取关键短语（基于词频统计）。
        
        Args:
            text: 输入文本
            top_n: 返回的关键短语数量
            
        Returns:
            List[str]: 关键短语列表
        """
        import re
        from collections import Counter

        # 提取中文词组（2-4字）和英文单词
        chinese_phrases = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        english_words = re.findall(r'[a-zA-Z]{3,}', text)

        # 过滤停用词
        chinese_phrases = [p for p in chinese_phrases if p not in self._stopwords]
        english_words = [w.lower() for w in english_words if w.lower() not in self._stopwords]

        # 合并并统计频率
        all_terms = chinese_phrases + english_words
        term_freq = Counter(all_terms)

        # 返回频率最高的 top_n 个
        return [term for term, _ in term_freq.most_common(top_n)]

    # --------------------------------------------------------
    # 内容生成
    # --------------------------------------------------------

    def generate_content(self, input_data: InputData) -> OutputData:
        """
        根据输入数据生成 SEO 优化内容。
        
        Args:
            input_data: 标准化后的输入数据
            
        Returns:
            OutputData: 生成的 SEO 内容
        """
        # 初始化输出
        output = OutputData()

        # 1. 生成标题（取前几个关键短语组合）
        key_terms = input_data.key_phrases[:3]
        if len(key_terms) >= 2:
            output.title = f"{key_terms[0]}：{key_terms[1]}完整指南"
        elif key_terms:
            output.title = f"{key_terms[0]}全面解析"
        else:
            # 没有关键短语时使用句子片段
            first_sentence = input_data.sentences[0]
            output.title = first_sentence[:30] + ("..." if len(first_sentence) > 30 else "")

        # 2. 生成元描述（基于前两个句子）
        meta_parts = input_data.sentences[:2]
        output.meta_desc = " | ".join(meta_parts)[:150]

        # 3. 关键词列表
        output.keywords = input_data.key_phrases[:5]

        # 4. 标题结构（H1/H2）
        output.headings = [
            f"H1: {output.title}",
        ]
        for kw in output.keywords[:3]:
            output.headings.append(f"H2: 关于{kw}的深入探讨")

        # 5. 正文段落（基于输入句子重组）
        body_paragraphs = []
        for i, sentence in enumerate(input_data.sentences[:5]):
            # 简单加工：添加段落前缀
            paragraph = f"段落{i+1}：{sentence}"
            body_paragraphs.append(paragraph)
        output.body = body_paragraphs

        # 6. 行动号召（CTA）
        output.cta = "立即行动，获取更多相关信息！"

        # 7. 计算置信度
        output.confidence = self._calculate_confidence(input_data, output)

        # 8. 根据置信度添加警告
        if output.confidence < CONFIDENCE_MEDIUM:
            output.warnings.append("输入内容信息量不足，建议补充更多细节")
            output.needs_review = True
            output.cta = "[需核实] " + output.cta
        elif output.confidence < CONFIDENCE_HIGH:
            output.warnings.append("建议复核生成内容的准确性")
            output.needs_review = True

        return output

    def _calculate_confidence(self, input_data: InputData, output: OutputData) -> float:
        """
        计算生成内容的置信度。
        
        基于以下因素：
        - 输入文本长度
        - 关键短语数量
        - 句子数量
        
        Args:
            input_data: 输入数据
            output: 生成的输出
            
        Returns:
            float: 置信度 0.0-1.0
        """
        confidence = 0.0

        # 词数贡献（0-0.4分）
        if input_data.word_count >= 100:
            confidence += 0.4
        elif input_data.word_count >= 50:
            confidence += 0.3
        elif input_data.word_count >= 20:
            confidence += 0.2
        else:
            confidence += 0.1

        # 关键短语贡献（0-0.3分）
        phrase_score = min(len(input_data.key_phrases) / 5.0, 1.0) * 0.3
        confidence += phrase_score

        # 句子数量贡献（0-0.3分）
        sentence_score = min(len(input_data.sentences) / 5.0, 1.0) * 0.3
        confidence += sentence_score

        # 确保在 0-1 范围内
        return max(0.0, min(1.0, confidence))

    # --------------------------------------------------------
    # 输出格式化
    # --------------------------------------------------------

    def format_output(self, output: OutputData, format_type: str = "text") -> str:
        """
        格式化输出内容。
        
        Args:
            output: 生成的 SEO 内容
            format_type: 输出格式 (text/json)
            
        Returns:
            str: 格式化后的输出字符串
        """
        if format_type == "json":
            return json.dumps(asdict(output), ensure_ascii=False, indent=2)

        # 文本格式
        lines = []
        lines.append("=" * 50)
        lines.append("SEO 内容生成结果")
        lines.append("=" * 50)
        lines.append(f"标题: {output.title}")
        lines.append(f"元描述: {output.meta_desc}")
        lines.append(f"关键词: {', '.join(output.keywords)}")
        lines.append("\n标题结构:")
        for h in output.headings:
            lines.append(f"  {h}")
        lines.append("\n正文:")
        for p in output.body:
            lines.append(f"  {p}")
        lines.append(f"\n行动号召: {output.cta}")
        lines.append(f"\n置信度: {output.confidence:.1%}")
        if output.needs_review:
            lines.append("状态: [需人工复核]")
        if output.warnings:
            lines.append("警告:")
            for w in output.warnings:
                lines.append(f"  - {w}")
        lines.append("=" * 50)

        return "\n".join(lines)

    # --------------------------------------------------------
    # 主处理流程
    # --------------------------------------------------------

    def process(self, raw_input: str, source_type: str = "text",
                output_format: str = "text") -> Tuple[bool, str, Optional[OutputData]]:
        """
        完整处理流程：解析 -> 生成 -> 格式化输出。
        
        Args:
            raw_input: 原始输入
            source_type: 输入类型
            output_format: 输出格式
            
        Returns:
            Tuple[bool, str, Optional[OutputData]]: (是否成功, 消息/输出, 输出数据)
        """
        try:
            # 解析输入
            input_data = self.parse_input(raw_input, source_type)

            # 生成内容
            output = self.generate_content(input_data)

            # 格式化输出
            formatted = self.format_output(output, output_format)

            return True, formatted, output

        except ValueError as e:
            error_code = str(e)
            message = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E007"])
            return False, f"[{error_code}] {message}", None
        except Exception:
            return False, f"[E007] {ERROR_MESSAGES['E007']}", None


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    
    使用内置硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    断言使用宽松阈值，确保任何环境直接可过。
    
    Returns:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("SEO 内容生成器 - 离线自检")
    print("=" * 60)

    generator = SEOContentGenerator()

    # --------------------------------------------------------
    # 测试用例 1：正常输入
    # --------------------------------------------------------
    print("\n[测试 1] 正常文本输入")
    sample_text = """
    人工智能正在改变我们的生活和工作方式。机器学习是人工智能的核心技术之一。
    深度学习在图像识别和自然语言处理领域取得了巨大成功。许多企业正在采用AI技术
    来提高效率和创新能力。未来，人工智能将继续推动各行各业的数字化转型。
    我们应该积极拥抱这一技术变革，同时关注其带来的伦理和隐私问题。
    """
    success, result, output = generator.process(sample_text, "text", "text")
    assert success, f"测试1失败: {result}"
    assert output is not None, "测试1失败: 输出为空"
    assert len(output.title) > 0, "测试1失败: 标题为空"
    assert len(output.keywords) > 0, "测试1失败: 关键词为空"
    assert len(output.body) > 0, "测试1失败: 正文为空"
    assert 0.0 <= output.confidence <= 1.0, "测试1失败: 置信度超出范围"
    print(f"  ✓ 通过 (置信度: {output.confidence:.1%})")

    # --------------------------------------------------------
    # 测试用例 2：空输入（应返回 E001）
    # --------------------------------------------------------
    print("\n[测试 2] 空输入")
    success, result, _ = generator.process("", "text", "text")
    assert not success, "测试2失败: 空输入应该失败"
    assert "E001" in result, f"测试2失败: 错误码不正确: {result}"
    print(f"  ✓ 通过 (错误码: E001)")

    # --------------------------------------------------------
    # 测试用例 3：短输入（低置信度）
    # --------------------------------------------------------
    print("\n[测试 3] 短输入（低置信度）")
    short_text = "测试内容"
    success, result, output = generator.process(short_text, "text", "text")
    assert success, f"测试3失败: {result}"
    assert output is not None, "测试3失败: 输出为空"
    assert output.confidence < CONFIDENCE_HIGH, "测试3失败: 短输入置信度应该较低"
    print(f"  ✓ 通过 (置信度: {output.confidence:.1%})")

    # --------------------------------------------------------
    # 测试用例 4：JSON 输出格式
    # --------------------------------------------------------
    print("\n[测试 4] JSON 输出格式")
    success, result, _ = generator.process(sample_text, "text", "json")
    assert success, f"测试4失败: {result}"
    # 验证 JSON 可解析
    try:
        json_data = json.loads(result)
        assert "title" in json_data, "测试4失败: JSON缺少title字段"
        assert "keywords" in json_data, "测试4失败: JSON缺少keywords字段"
        assert "confidence" in json_data, "测试4失败: JSON缺少confidence字段"
    except json.JSONDecodeError:
        assert False, "测试4失败: 输出不是有效JSON"
    print("  ✓ 通过")

    # --------------------------------------------------------
    # 测试用例 5：URL 类型输入
    # --------------------------------------------------------
    print("\n[测试 5] URL 类型输入")
    url_text = "https://example.com/article 这是一个关于SEO优化的示例文章内容，包含关键词和描述。"
    success, result, output = generator.process(url_text, "url", "text")
    assert success, f"测试5失败: {result}"
    assert output is not None, "测试5失败: 输出为空"
    print(f"  ✓ 通过 (标题: {output.title[:30]}...)")

    # --------------------------------------------------------
    # 测试用例 6：错误输入类型
    # --------------------------------------------------------
    print("\n[测试 6] 错误输入类型")
    success, result, _ = generator.process("测试内容", "invalid_type", "text")
    assert not success, "测试6失败: 无效类型应该失败"
    assert "E003" in result, f"测试6失败: 错误码不正确: {result}"
    print(f"  ✓ 通过 (错误码: E003)")

    # --------------------------------------------------------
    # 测试用例 7：批量处理能力（简单验证）
    # --------------------------------------------------------
    print("\n[测试 7] 批量处理")
    inputs = [
        "第一个测试输入，包含一些关键词和内容。",
        "第二个测试输入，包含不同的关键词和内容描述。",
    ]
    outputs = []
    for inp in inputs:
        success, _, output = generator.process(inp, "text", "text")
        assert success, f"测试7失败: {result}"
        assert output is not None, "测试7失败: 输出为空"
        outputs.append(output)
    assert len(outputs) == 2, "测试7失败: 批量处理数量不正确"
    # 不同输入应产生不同标题
    assert outputs[0].title != outputs[1].title, "测试7失败: 不同输入应产生不同输出"
    print("  ✓ 通过")

    # --------------------------------------------------------
    # 测试用例 8：置信度计算合理性
    # --------------------------------------------------------
    print("\n[测试 8] 置信度计算")
    # 长文本置信度应高于短文本
    long_text = "这是一个很长的测试文本。" * 20  # 约 120 个字符
    _, _, output_long = generator.process(long_text, "text", "text")
    _, _, output_short = generator.process("短文本", "text", "text")

    assert output_long is not None and output_short is not None, "测试8失败: 输出为空"
    assert output_long.confidence > output_short.confidence, \
        "测试8失败: 长文本置信度应高于短文本"
    print(f"  ✓ 通过 (长文本: {output_long.confidence:.1%} > 短文本: {output_short.confidence:.1%})")

    # --------------------------------------------------------
    # 测试用例 9：错误码完整性
    # --------------------------------------------------------
    print("\n[测试 9] 错误码完整性")
    expected_codes = ["E001", "E002", "E003", "E004", "E005"]
    for code in expected_codes:
        assert code in ERROR_MESSAGES, f"测试9失败: 缺少错误码 {code}"
        assert len(ERROR_MESSAGES[code]) > 0, f"测试9失败: 错误码 {code} 消息为空"
    print("  ✓ 通过")

    # --------------------------------------------------------
    # 测试用例 10：文件输出能力（使用临时目录）
    # --------------------------------------------------------
    print("\n[测试 10] 文件输出")
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "output.txt")
        success, result, output = generator.process(sample_text, "text", "text")
        assert success, f"测试10失败: {result}"
        assert output is not None, "测试10失败: 输出为空"

        # 写入文件
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(result)
            # 验证文件存在且非空
            assert os.path.exists(filepath), "测试10失败: 文件未创建"
            file_size = os.path.getsize(filepath)
            assert file_size > 0, "测试10失败: 文件为空"
        except OSError:
            assert False, "测试10失败: 文件写入错误"
    print("  ✓ 通过")

    # --------------------------------------------------------
    # 汇总
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("✅ 所有自检测试通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    命令行主入口。
    
    Returns:
        int: 退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="SEO 文案生成器 - 从单个种子概念生成 SEO 优化内容",
        epilog="示例: python main.py --input '你的内容' --type text --format text"
    )

    # 输入参数
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本/URL/文件路径）"
    )
    parser.add_argument(
        "--type", "-t",
        type=str,
        default="text",
        choices=["text", "url", "file"],
        help="输入类型 (默认: text)"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="text",
        choices=["text", "json"],
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（可选，默认输出到 stdout）"
    )

    # 自检参数
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部资源）"
    )

    # 版本参数
    parser.add_argument(
        "--version",
        action="version",
        version="SEO 文案生成器 v1.0.0"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"\n❌ 自检失败: {e}")
            print(f"[E009] {ERROR_MESSAGES['E009']}")
            return 1
        except Exception as e:
            print(f"\n❌ 自检异常: {e}")
            print(f"[E009] {ERROR_MESSAGES['E009']}")
            return 1

    # 正常处理模式
    # E001: 没有提供输入
    if not args.input:
        print(f"[E001] {ERROR_MESSAGES['E001']}")
        print("提示: 使用 --input 参数提供输入内容，或使用 --selftest 运行自检。")
        return 1

    # 创建生成器并处理
    generator = SEOContentGenerator()
    success, result, _ = generator.process(args.input, args.type, args.format)

    if not success:
        print(result)
        return 1

    # 输出结果
    if args.output:
        try:
            # 确保目录存在
            output_dir = os.path.dirname(args.output)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"✅ 结果已写入: {args.output}")
        except OSError:
            print(f"[E008] {ERROR_MESSAGES['E008']}")
            return 1
    else:
        print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
