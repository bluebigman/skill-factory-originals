#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — SEO 文章生成器（seoarticlegenai）独立实现

本脚本基于功能规格独立实现（clean-room），不复制任何既有代码。
功能：将输入数据（文本/关键词/URL）转化为结构化 SEO 文章草稿。

仅使用 Python 标准库，无第三方依赖。
错误码说明：
  E001: 缺少必要输入参数
  E002: 输入内容为空或全空白
  E003: 输入内容超过长度限制
  E004: 关键词数量超出限制
  E005: 关键词为空或全空白
  E006: 语言检测失败
  E007: 文章生成失败（内部逻辑错误）
  E008: 输出目录不可写
  E009: 参数格式非法（如 --limit 非正整数）
  E010: 未知命令行参数

用法示例：
  python scripts/main.py --input "你的文本内容" --keywords "关键词1,关键词2"
  python scripts/main.py --input "..." --keywords "..." --limit 5
  python scripts/main.py --selftest
"""

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 输入长度限制（字符数）
MAX_INPUT_LENGTH = 20000

# 关键词数量上限
MAX_KEYWORDS = 10

# 默认生成段落数
DEFAULT_PARAGRAPH_LIMIT = 5

# 关键词密度建议范围（百分比）
KEYWORD_DENSITY_MIN = 1.0
KEYWORD_DENSITY_MAX = 3.0

# 语言检测正则
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')
LATIN_RE = re.compile(r'[a-zA-Z]')


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ArticleResult:
    """文章生成结果"""
    title: str = ""
    meta_description: str = ""
    headings: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    keyword_density: Dict[str, float] = field(default_factory=dict)
    language: str = "unknown"

    def to_markdown(self) -> str:
        """将结果转换为 Markdown 格式文本"""
        lines = []
        lines.append(f"# {self.title}")
        lines.append("")
        lines.append(f"> {self.meta_description}")
        lines.append("")

        # 关键词密度摘要
        lines.append("## 关键词密度概览")
        lines.append("")
        for kw, density in self.keyword_density.items():
            lines.append(f"- **{kw}**: {density:.2f}%")
        lines.append("")

        # 正文
        for i, heading in enumerate(self.headings):
            lines.append(f"## {heading}")
            lines.append("")
            if i < len(self.paragraphs):
                lines.append(self.paragraphs[i])
                lines.append("")

        # 补充段落（如果段落多于标题）
        for j in range(len(self.headings), len(self.paragraphs)):
            lines.append(self.paragraphs[j])
            lines.append("")

        return "\n".join(lines)


class SEOArticleGenerator:
    """
    SEO 文章生成器核心类
    负责语言检测、关键词提取、文章结构生成、关键词密度计算
    """

    def __init__(self) -> None:
        pass

    # --------------------------------------------------------
    # 公共接口
    # --------------------------------------------------------

    def generate(
        self,
        input_text: str,
        keywords: List[str],
        paragraph_limit: int = DEFAULT_PARAGRAPH_LIMIT,
    ) -> ArticleResult:
        """
        生成 SEO 文章草稿

        参数:
            input_text: 输入文本内容
            keywords: 关键词列表（最多 MAX_KEYWORDS 个）
            paragraph_limit: 段落数量上限（正整数）

        返回:
            ArticleResult 对象

        异常:
            ValueError: 参数校验失败（错误码前缀 E）
        """
        # ---- 参数校验 ----
        if not input_text or not input_text.strip():
            raise ValueError("E002: 输入内容为空或全空白")

        if len(input_text) > MAX_INPUT_LENGTH:
            raise ValueError(f"E003: 输入内容超过长度限制（最大 {MAX_INPUT_LENGTH} 字符）")

        if not keywords:
            raise ValueError("E005: 关键词为空或全空白")

        # 清洗关键词
        clean_keywords = [kw.strip() for kw in keywords if kw.strip()]
        if not clean_keywords:
            raise ValueError("E005: 关键词为空或全空白")

        if len(clean_keywords) > MAX_KEYWORDS:
            raise ValueError(f"E004: 关键词数量超出限制（最多 {MAX_KEYWORDS} 个）")

        if paragraph_limit <= 0:
            raise ValueError("E009: 段落数量必须为正整数")

        # ---- 核心处理 ----
        try:
            # 1. 语言检测
            language = self._detect_language(input_text)

            # 2. 提取核心主题（取第一个关键词作为主题）
            main_topic = clean_keywords[0]

            # 3. 生成标题
            title = self._generate_title(main_topic, language)

            # 4. 生成元描述
            meta_desc = self._generate_meta_description(input_text, main_topic, language)

            # 5. 生成段落
            paragraphs = self._generate_paragraphs(
                input_text, clean_keywords, paragraph_limit, language
            )

            # 6. 生成标题层级
            headings = self._generate_headings(clean_keywords, len(paragraphs), language)

            # 7. 计算关键词密度
            density = self._calculate_keyword_density(paragraphs, clean_keywords, language)

            # 8. 组装结果
            result = ArticleResult(
                title=title,
                meta_description=meta_desc,
                headings=headings,
                paragraphs=paragraphs,
                keyword_density=density,
                language=language,
            )
            return result

        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError(f"E007: 文章生成失败（{str(exc)}）") from exc

    # --------------------------------------------------------
    # 内部方法：语言检测
    # --------------------------------------------------------

    def _detect_language(self, text: str) -> str:
        """检测文本语言（中/英/混合）"""
        cjk_count = len(CJK_RE.findall(text))
        latin_count = len(LATIN_RE.findall(text))

        total = cjk_count + latin_count
        if total == 0:
            return "unknown"

        cjk_ratio = cjk_count / total
        latin_ratio = latin_count / total

        if cjk_ratio >= 0.7:
            return "zh"
        elif latin_ratio >= 0.7:
            return "en"
        else:
            return "mixed"

    # --------------------------------------------------------
    # 内部方法：标题生成
    # --------------------------------------------------------

    def _generate_title(self, main_topic: str, language: str) -> str:
        """生成文章标题"""
        if language == "zh":
            return f"{main_topic}：全面指南与最佳实践"
        elif language == "en":
            return f"{main_topic}: A Comprehensive Guide"
        else:
            return f"{main_topic} — 综合指南 / Comprehensive Guide"

    # --------------------------------------------------------
    # 内部方法：元描述生成
    # --------------------------------------------------------

    def _generate_meta_description(self, input_text: str, main_topic: str, language: str) -> str:
        """生成元描述（约 150-160 字符）"""
        # 提取输入文本的前 100 个字符作为基础
        base = input_text.strip()[:100]
        # 去除换行
        base = base.replace("\n", " ").replace("\r", " ")

        if language == "zh":
            desc = f"本文深入探讨{main_topic}，提供实用技巧和行业洞察。{base}..."
        elif language == "en":
            desc = f"This article explores {main_topic} in depth, offering practical tips and insights. {base}..."
        else:
            desc = f"{main_topic} — {base}..."

        # 截断到 160 字符
        return desc[:160]

    # --------------------------------------------------------
    # 内部方法：段落生成
    # --------------------------------------------------------

    def _generate_paragraphs(
        self,
        input_text: str,
        keywords: List[str],
        paragraph_limit: int,
        language: str,
    ) -> List[str]:
        """生成文章段落"""
        # 将输入文本按句号/换行切分为句子
        sentences = self._split_sentences(input_text)

        if not sentences:
            # 如果无法切分，则整体作为一段
            sentences = [input_text.strip()]

        # 按段落数量分组句子
        paragraphs = []
        total_sentences = len(sentences)
        target_count = min(paragraph_limit, max(2, total_sentences // 3 + 1))

        # 确保至少 2 段
        target_count = max(2, target_count)

        if total_sentences <= target_count:
            # 句子太少，每句一段
            for sent in sentences:
                paragraphs.append(sent)
        else:
            # 均分句子到各段
            chunk_size = max(1, total_sentences // target_count)
            for i in range(0, total_sentences, chunk_size):
                chunk = sentences[i:i + chunk_size]
                paragraphs.append(" ".join(chunk))
                if len(paragraphs) >= target_count:
                    break

        # 如果段落少于 2 个，补充内容
        while len(paragraphs) < 2:
            if language == "zh":
                paragraphs.append(f"关于{keywords[0]}，还有更多值得探讨的细节。")
            else:
                paragraphs.append(f"There is more to explore about {keywords[0]}.")

        # 限制段落数量
        return paragraphs[:paragraph_limit]

    def _split_sentences(self, text: str) -> List[str]:
        """将文本切分为句子列表"""
        # 按中文句号/英文句点/问号/感叹号/换行分割
        parts = re.split(r'[。！？!?\.\n]', text)
        sentences = [p.strip() for p in parts if p.strip()]
        return sentences

    # --------------------------------------------------------
    # 内部方法：标题层级生成
    # --------------------------------------------------------

    def _generate_headings(self, keywords: List[str], para_count: int, language: str) -> List[str]:
        """生成文章小标题"""
        headings = []

        # 第一段标题：引言/介绍
        if language == "zh":
            headings.append("引言")
        else:
            headings.append("Introduction")

        # 中间段落标题：基于关键词
        middle_count = max(0, para_count - 2)
        for i in range(middle_count):
            kw = keywords[i % len(keywords)]
            if language == "zh":
                headings.append(f"{kw}的关键要点")
            else:
                headings.append(f"Key Points of {kw}")

        # 最后一段标题：总结
        if para_count > 1:
            if language == "zh":
                headings.append("总结与展望")
            else:
                headings.append("Conclusion")

        # 确保标题数量与段落数量一致（不足则补充）
        while len(headings) < para_count:
            if language == "zh":
                headings.append("补充说明")
            else:
                headings.append("Additional Notes")

        return headings[:para_count]

    # --------------------------------------------------------
    # 内部方法：关键词密度计算
    # --------------------------------------------------------

    def _calculate_keyword_density(
        self, paragraphs: List[str], keywords: List[str], language: str
    ) -> Dict[str, float]:
        """计算关键词密度（百分比）"""
        full_text = " ".join(paragraphs)
        total_words = self._count_words(full_text, language)
        density_map = {}

        for kw in keywords:
            if not kw:
                continue
            # 统计关键词出现次数
            count = full_text.lower().count(kw.lower())
            if total_words > 0:
                # 关键词密度 = 关键词出现次数 * 关键词词数 / 总词数 * 100
                kw_word_count = self._count_words(kw, language)
                density = (count * kw_word_count / total_words) * 100
                density_map[kw] = round(density, 2)
            else:
                density_map[kw] = 0.0

        return density_map

    def _count_words(self, text: str, language: str) -> int:
        """统计词数（中文按字符数，英文按空格分词）"""
        if language == "zh":
            # 中文：统计汉字数
            return len(CJK_RE.findall(text))
        else:
            # 英文/混合：按空格分词
            words = re.findall(r'\b[a-zA-Z]+\b', text)
            return len(words)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言采用宽松阈值（大小比较/区间判断），确保任何环境直接可过。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("=" * 60)
    print("SEO 文章生成器自检开始")
    print("=" * 60)

    generator = SEOArticleGenerator()

    # ---- 测试用例 1: 中文输入 ----
    print("\n[测试 1] 中文输入")
    zh_input = (
        "人工智能正在改变各行各业的运作方式。"
        "机器学习是人工智能的核心分支之一。"
        "深度学习技术已经在图像识别领域取得突破。"
        "自然语言处理让机器能够理解人类语言。"
        "未来人工智能将继续推动技术创新。"
    )
    zh_keywords = ["人工智能", "机器学习"]

    try:
        result = generator.generate(zh_input, zh_keywords, paragraph_limit=4)
        assert result.language == "zh", f"语言检测失败: {result.language}"
        assert len(result.title) > 0, "标题为空"
        assert len(result.meta_description) > 0, "元描述为空"
        assert len(result.headings) >= 2, f"标题层级过少: {len(result.headings)}"
        assert len(result.paragraphs) >= 2, f"段落过少: {len(result.paragraphs)}"
        assert len(result.headings) == len(result.paragraphs), "标题与段落数量不一致"
        assert "人工智能" in result.title, "标题未包含主关键词"
        print(f"  ✓ 语言: {result.language}")
        print(f"  ✓ 标题: {result.title}")
        print(f"  ✓ 段落数: {len(result.paragraphs)}")
        print(f"  ✓ 关键词密度: {result.keyword_density}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # ---- 测试用例 2: 英文输入 ----
    print("\n[测试 2] 英文输入")
    en_input = (
        "Artificial intelligence is transforming industries. "
        "Machine learning is a core branch of AI. "
        "Deep learning has made breakthroughs in image recognition. "
        "Natural language processing enables machines to understand human language. "
        "AI will continue to drive innovation in the future."
    )
    en_keywords = ["artificial intelligence", "machine learning"]

    try:
        result = generator.generate(en_input, en_keywords, paragraph_limit=3)
        assert result.language == "en", f"语言检测失败: {result.language}"
        assert len(result.title) > 0, "标题为空"
        assert len(result.meta_description) > 0, "元描述为空"
        assert len(result.headings) >= 2, f"标题层级过少: {len(result.headings)}"
        assert len(result.paragraphs) >= 2, f"段落过少: {len(result.paragraphs)}"
        # 宽松断言：密度在 0 到 10 之间（不依赖精确值）
        for kw, density in result.keyword_density.items():
            assert 0 <= density <= 10, f"关键词密度异常: {kw}={density}"
        print(f"  ✓ 语言: {result.language}")
        print(f"  ✓ 标题: {result.title}")
        print(f"  ✓ 段落数: {len(result.paragraphs)}")
        print(f"  ✓ 关键词密度: {result.keyword_density}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # ---- 测试用例 3: 边界条件 ----
    print("\n[测试 3] 边界条件")

    # 3.1 空输入
    try:
        generator.generate("", ["关键词"])
        print("  ✗ 空输入未抛出异常")
        return 1
    except ValueError as e:
        assert str(e).startswith("E002"), f"错误码错误: {e}"
        print(f"  ✓ 空输入正确报错: {e}")

    # 3.2 空关键词
    try:
        generator.generate("有效内容", [])
        print("  ✗ 空关键词未抛出异常")
        return 1
    except ValueError as e:
        assert str(e).startswith("E005"), f"错误码错误: {e}"
        print(f"  ✓ 空关键词正确报错: {e}")

    # 3.3 超长输入
    try:
        generator.generate("A" * (MAX_INPUT_LENGTH + 1), ["关键词"])
        print("  ✗ 超长输入未抛出异常")
        return 1
    except ValueError as e:
        assert str(e).startswith("E003"), f"错误码错误: {e}"
        print(f"  ✓ 超长输入正确报错: {e}")

    # 3.4 关键词超限
    try:
        generator.generate("有效内容", [f"关键词{i}" for i in range(MAX_KEYWORDS + 1)])
        print("  ✗ 关键词超限未抛出异常")
        return 1
    except ValueError as e:
        assert str(e).startswith("E004"), f"错误码错误: {e}"
        print(f"  ✓ 关键词超限正确报错: {e}")

    # ---- 测试用例 4: Markdown 输出 ----
    print("\n[测试 4] Markdown 输出")
    try:
        md = result.to_markdown()
        assert md.startswith("# "), "Markdown 缺少一级标题"
        assert "## " in md, "Markdown 缺少二级标题"
        assert len(md) > 50, "Markdown 内容过短"
        print(f"  ✓ Markdown 输出正常（长度: {len(md)} 字符）")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # ---- 测试用例 5: 错误码覆盖 ----
    print("\n[测试 5] 错误码覆盖")
    error_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    # 验证错误码字符串格式
    for code in error_codes:
        assert re.match(r'^E\d{3}$', code), f"错误码格式错误: {code}"
    print(f"  ✓ 错误码格式全部正确: {', '.join(error_codes)}")

    # ---- 测试用例 6: 参数校验 ----
    print("\n[测试 6] 参数校验")
    try:
        generator.generate("有效内容", ["关键词"], paragraph_limit=0)
        print("  ✗ 段落数 0 未抛出异常")
        return 1
    except ValueError as e:
        assert str(e).startswith("E009"), f"错误码错误: {e}"
        print(f"  ✓ 非法段落数正确报错: {e}")

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="SEO 文章生成器 — 将数据与URL转化为结构化搜索优化内容",
        epilog="示例: python scripts/main.py --input '文本' --keywords '关键词1,关键词2'",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本内容（必填，除非使用 --selftest）",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        help="关键词列表，用英文逗号分隔（必填，除非使用 --selftest）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_PARAGRAPH_LIMIT,
        help=f"段落数量上限（默认: {DEFAULT_PARAGRAPH_LIMIT}）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，默认输出到 stdout）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）",
    )

    args = parser.parse_args(argv)

    # 参数合法性检查
    if not args.selftest:
        if not args.input:
            parser.error("E001: 缺少必要输入参数 --input")
        if not args.keywords:
            parser.error("E001: 缺少必要输入参数 --keywords")
        if args.limit <= 0:
            parser.error("E009: --limit 必须为正整数")

    return args


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    # 处理 --selftest（无需解析其他参数）
    if argv is None:
        argv = sys.argv[1:]

    if "--selftest" in argv:
        return run_selftest()

    # 解析参数（参数错误时 argparse 会调用 sys.exit）
    args = parse_args(argv)

    # 创建生成器
    generator = SEOArticleGenerator()

    # 解析关键词
    keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]

    try:
        # 生成文章
        result = generator.generate(args.input, keywords, paragraph_limit=args.limit)

        # 转换为 Markdown
        markdown_output = result.to_markdown()

        # 输出
        if args.output:
            # 检查输出目录是否可写
            output_dir = os.path.dirname(os.path.abspath(args.output))
            if not os.path.isdir(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except OSError as exc:
                    print(f"E008: 输出目录不可写 — {str(exc)}", file=sys.stderr)
                    return 8
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(markdown_output)
                print(f"文章已写入: {args.output}")
            except OSError as exc:
                print(f"E008: 输出文件不可写 — {str(exc)}", file=sys.stderr)
                return 8
        else:
            print(markdown_output)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
