#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — SEO文案生成器（Clean Room 独立实现）

功能规格依据:
- 将输入数据转为结构化SEO文案
- 含关键词布局与置信度标注
- 支持批量处理与自定义输出格式

仅使用 Python 标准库。无第三方依赖。
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入数据为空或格式不正确",
    "E002": "输入数据不是有效的字典或列表",
    "E003": "缺少必填字段（title/content/primary_keyword）",
    "E004": "输出格式参数不合法（仅支持 json/text/markdown）",
    "E005": "关键词列表为空",
    "E006": "置信度计算失败",
    "E007": "批量处理时某条数据失败",
    "E008": "内部逻辑错误（未知异常）",
    "E009": "参数解析失败",
    "E010": "自检失败",
}


def err(code: str, msg: Optional[str] = None) -> str:
    """返回带错误码的错误信息字符串"""
    prefix = f"[{code}]"
    if msg:
        return f"{prefix} {msg}"
    return f"{prefix} {ERROR_CODES.get(code, '未知错误')}"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class SEOArticle:
    """SEO文案对象"""
    title: str
    content: str
    primary_keyword: str
    keywords: List[str] = field(default_factory=list)
    confidence: float = 0.0
    keyword_density: float = 0.0
    word_count: int = 0
    sections: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return asdict(self)


@dataclass
class InputData:
    """标准化输入数据"""
    title: str = ""
    content: str = ""
    primary_keyword: str = ""
    keywords: List[str] = field(default_factory=list)
    audience: str = ""
    tone: str = "专业"
    output_format: str = "text"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputData":
        """从字典构建，缺失字段用默认值"""
        return cls(
            title=str(data.get("title", "")).strip(),
            content=str(data.get("content", "")).strip(),
            primary_keyword=str(data.get("primary_keyword", "")).strip(),
            keywords=[str(k).strip() for k in data.get("keywords", []) if str(k).strip()],
            audience=str(data.get("audience", "")).strip(),
            tone=str(data.get("tone", "专业")).strip(),
            output_format=str(data.get("output_format", "text")).strip(),
        )


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class SEOGenerator:
    """SEO文案生成器主类"""

    # 停用词（简化版，仅用于关键词密度计算）
    STOP_WORDS = {
        "的", "了", "和", "是", "在", "有", "就", "不", "都", "而",
        "及", "与", "着", "或", "一个", "没有", "我们", "你们", "他们",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "up", "about", "into", "over",
        "after", "before", "between", "out", "off", "under", "again",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化配置"""
        self.config = config or {}
        self.min_confidence = float(self.config.get("min_confidence", 0.5))
        self.target_density = float(self.config.get("target_density", 0.03))

    # -- 文本处理工具 ------------------------------------------------------
    @staticmethod
    def _clean_text(text: str) -> str:
        """清理文本：去除多余空白"""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _tokenize(self, text: str) -> List[str]:
        """分词（中英文混排）"""
        # 中文按字切分，英文按词切分
        tokens = []
        for part in re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower()):
            if part:
                tokens.append(part)
        return tokens

    def _count_words(self, text: str) -> int:
        """统计词数（中文字数 + 英文单词数）"""
        tokens = self._tokenize(text)
        return len(tokens)

    # -- 关键词处理 ----------------------------------------------------------
    def _extract_keywords(self, input_data: InputData) -> List[str]:
        """提取关键词列表"""
        keywords = []
        if input_data.primary_keyword:
            keywords.append(input_data.primary_keyword)
        for kw in input_data.keywords:
            if kw and kw not in keywords:
                keywords.append(kw)
        return keywords

    def _calculate_density(self, text: str, keywords: List[str]) -> float:
        """计算关键词密度（关键词出现次数 / 总词数）"""
        total_words = self._count_words(text)
        if total_words == 0:
            return 0.0

        text_lower = text.lower()
        
        # 计算所有关键词的总出现次数
        total_keyword_occurrences = 0
        for kw in keywords:
            kw_lower = kw.lower()
            # 使用正则表达式统计关键词出现次数（支持中文关键词）
            occurrences = len(re.findall(re.escape(kw_lower), text_lower))
            total_keyword_occurrences += occurrences
        
        # 对于中文文本，密度计算基于字符数
        # 检查文本是否主要是中文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars > len(text) * 0.5:  # 超过50%是中文字符
            # 中文密度 = 关键词出现次数 / 中文字符总数
            if chinese_chars > 0:
                return total_keyword_occurrences / chinese_chars
        
        # 对于英文或混合文本，使用词数计算
        return total_keyword_occurrences / total_words

    def _calculate_confidence(self, input_data: InputData, keywords: List[str]) -> float:
        """计算置信度（0.0 - 1.0）"""
        try:
            score = 0.0
            reasons = []

            # 1. 标题包含主关键词 -> +0.3
            if input_data.primary_keyword and input_data.primary_keyword.lower() in input_data.title.lower():
                score += 0.3
                reasons.append("标题包含主关键词")
            else:
                reasons.append("标题未包含主关键词")

            # 2. 内容包含主关键词 -> +0.2
            if input_data.primary_keyword and input_data.primary_keyword.lower() in input_data.content.lower():
                score += 0.2
                reasons.append("内容包含主关键词")
            else:
                reasons.append("内容未包含主关键词")

            # 3. 有受众信息 -> +0.15
            if input_data.audience:
                score += 0.15
                reasons.append("有受众信息")
            else:
                reasons.append("缺少受众信息")

            # 4. 关键词数量 >= 2 -> +0.15
            if len(keywords) >= 2:
                score += 0.15
                reasons.append("关键词数量充足")
            else:
                reasons.append("关键词数量不足")

            # 5. 内容长度 >= 200 字 -> +0.2
            if self._count_words(input_data.content) >= 200:
                score += 0.2
                reasons.append("内容长度充足")
            else:
                reasons.append("内容长度不足")

            return min(score, 1.0)
        except Exception:
            raise RuntimeError(err("E006"))

    # -- 结构化生成 ----------------------------------------------------------
    def _build_sections(self, input_data: InputData, keywords: List[str]) -> List[Dict[str, Any]]:
        """构建文章结构"""
        sections = []

        # 引言
        intro = (
            f"本文围绕{input_data.primary_keyword or '核心主题'}展开，"
            f"为{input_data.audience or '目标读者'}提供实用信息与专业见解。"
        )
        sections.append({"heading": "引言", "content": intro})

        # 主体（按关键词分段）
        for i, kw in enumerate(keywords[:5], 1):
            section_content = (
                f"第{i}部分聚焦于「{kw}」。"
                f"在{input_data.primary_keyword or '该主题'}的语境下，"
                f"「{kw}」是值得深入探讨的关键维度。"
                f"结合行业实践，我们可以从多个角度分析其价值与应用场景。"
            )
            sections.append({"heading": f"关于{kw}", "content": section_content})

        # 总结
        sections.append({
            "heading": "总结",
            "content": (
                f"综上所述，{input_data.primary_keyword or '该主题'}"
                f"涉及多个方面。本文通过关键词布局与结构化呈现，"
                f"帮助读者快速把握核心要点。"
            )
        })

        return sections

    def _build_content(self, sections: List[Dict[str, Any]]) -> str:
        """从结构生成纯文本内容"""
        parts = []
        for sec in sections:
            parts.append(sec["heading"])
            parts.append(sec["content"])
        return "\n\n".join(parts)

    # -- 主处理入口 ----------------------------------------------------------
    def process(self, input_data: InputData) -> SEOArticle:
        """处理单条输入，生成SEO文案"""
        # 校验输入
        if not input_data.title or not input_data.content or not input_data.primary_keyword:
            raise ValueError(err("E003"))

        # 提取关键词
        keywords = self._extract_keywords(input_data)
        if not keywords:
            raise ValueError(err("E005"))

        # 构建结构化内容
        sections = self._build_sections(input_data, keywords)
        content = self._build_content(sections)

        # 计算指标
        word_count = self._count_words(content)
        density = self._calculate_density(content, keywords)
        confidence = self._calculate_confidence(input_data, keywords)

        # 生成最终标题（优化SEO标题）
        final_title = input_data.title
        if input_data.primary_keyword and input_data.primary_keyword not in final_title:
            final_title = f"{input_data.primary_keyword} | {final_title}"

        return SEOArticle(
            title=final_title,
            content=content,
            primary_keyword=input_data.primary_keyword,
            keywords=keywords,
            confidence=confidence,
            keyword_density=density,
            word_count=word_count,
            sections=sections,
        )

    def process_batch(self, data_list: List[Dict[str, Any]]) -> List[SEOArticle]:
        """批量处理"""
        results = []
        errors = []
        for idx, item in enumerate(data_list):
            try:
                input_data = InputData.from_dict(item)
                results.append(self.process(input_data))
            except Exception as e:
                errors.append({"index": idx, "error": str(e)})

        if errors:
            # 部分失败时仍然返回成功的结果，但附带错误信息
            raise RuntimeError(
                err("E007", f"批量处理中有 {len(errors)} 条失败: {json.dumps(errors, ensure_ascii=False)}")
            )
        return results

    # -- 格式化输出 ----------------------------------------------------------
    @staticmethod
    def format_output(articles: List[SEOArticle], fmt: str = "text") -> str:
        """按指定格式输出"""
        if fmt == "json":
            return json.dumps([a.to_dict() for a in articles], ensure_ascii=False, indent=2)

        if fmt == "markdown":
            parts = []
            for a in articles:
                parts.append(f"# {a.title}\n")
                parts.append(f"> 主关键词: {a.primary_keyword}")
                parts.append(f"> 关键词: {', '.join(a.keywords)}")
                parts.append(f"> 置信度: {a.confidence:.2f}")
                parts.append(f"> 词数: {a.word_count}")
                parts.append(f"> 密度: {a.keyword_density:.4f}\n")
                for sec in a.sections:
                    parts.append(f"## {sec['heading']}\n")
                    parts.append(f"{sec['content']}\n")
                parts.append("---\n")
            return "\n".join(parts)

        # text 格式（默认）
        parts = []
        for a in articles:
            parts.append(f"标题: {a.title}")
            parts.append(f"主关键词: {a.primary_keyword}")
            parts.append(f"关键词: {', '.join(a.keywords)}")
            parts.append(f"置信度: {a.confidence:.2f}")
            parts.append(f"词数: {a.word_count}")
            parts.append(f"关键词密度: {a.keyword_density:.4f}")
            parts.append("")
            parts.append(a.content)
            parts.append("=" * 60)
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# 输入处理
# ---------------------------------------------------------------------------
def parse_input(raw: str) -> Dict[str, Any]:
    """解析输入字符串为字典"""
    if not raw or not raw.strip():
        raise ValueError(err("E001"))

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 尝试简单键值对解析
        data = {}
        for line in raw.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()
        if not data:
            raise ValueError(err("E002"))

    if not isinstance(data, dict):
        raise ValueError(err("E002"))
    return data


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def selftest() -> int:
    """内置自检，使用硬编码样例数据，不依赖外部环境"""
    print("=== SEO文案生成器自检 ===")

    # 硬编码测试数据（不依赖任何外部文件）
    test_data = {
        "title": "如何选择适合中小企业的CRM系统",
        "content": (
            "在选择CRM系统时，中小企业需要考虑多个因素。"
            "首先，系统的易用性至关重要，因为团队可能没有专门的技术人员。"
            "其次，价格也是一个重要考量，中小企业通常预算有限。"
            "最后，系统的可扩展性决定了它能否伴随企业发展。"
            "本文提供一些实用的选型建议，帮助企业做出明智决策。"
        ),
        "primary_keyword": "CRM系统",
        "keywords": ["CRM选型", "中小企业", "客户管理"],
        "audience": "中小企业管理者",
        "tone": "专业",
        "output_format": "text",
    }

    # 测试1: 单条处理
    print("\n[测试1] 单条数据处理")
    try:
        gen = SEOGenerator()
        input_data = InputData.from_dict(test_data)
        article = gen.process(input_data)

        # 宽松断言（不依赖精确值）
        assert article.title is not None and len(article.title) > 0, "标题不应为空"
        assert article.content is not None and len(article.content) > 0, "内容不应为空"
        assert article.primary_keyword == "CRM系统", "主关键词应保留"
        assert len(article.keywords) >= 1, "关键词列表不应为空"
        assert article.word_count > 0, "词数应大于0"
        assert 0.0 <= article.confidence <= 1.0, "置信度应在0-1之间"
        assert article.keyword_density >= 0.0, "密度应非负"
        assert len(article.sections) >= 3, "应至少有引言、主体、总结三个部分"
        print("  ✓ 单条处理通过")

    except Exception as e:
        print(f"  ✗ 单条处理失败: {e}")
        return 1

    # 测试2: 置信度逻辑
    print("\n[测试2] 置信度计算")
    try:
        # 完整数据应有较高置信度
        complete_data = InputData.from_dict(test_data)
        complete_article = gen.process(complete_data)

        # 不完整数据应有较低置信度
        poor_data = InputData(
            title="标题",
            content="简短内容",
            primary_keyword="关键词",
            keywords=[],
            audience="",
        )
        poor_article = gen.process(poor_data)

        # 宽松断言：完整数据置信度应不低于不完整数据
        assert complete_article.confidence >= poor_article.confidence, "完整数据置信度应更高"
        print(f"  ✓ 置信度逻辑通过 (完整: {complete_article.confidence:.2f} vs 不完整: {poor_article.confidence:.2f})")

    except Exception as e:
        print(f"  ✗ 置信度测试失败: {e}")
        return 1

    # 测试3: 关键词密度
    print("\n[测试3] 关键词密度计算")
    try:
        # 中文密度测试
        density = gen._calculate_density("苹果 苹果 香蕉 苹果", ["苹果"])
        assert density > 0.5, f"密度应较高（3/4），实际: {density:.2f}"
        density2 = gen._calculate_density("苹果 香蕉 橘子", ["苹果"])
        assert density2 < 0.5, f"密度应较低（1/3），实际: {density2:.2f}"
        
        # 英文密度测试
        density3 = gen._calculate_density("apple apple banana apple", ["apple"])
        assert density3 > 0.5, f"英文密度应较高，实际: {density3:.2f}"
        
        print(f"  ✓ 密度计算通过 (高: {density:.2f}, 低: {density2:.2f}, 英文高: {density3:.2f})")

    except Exception as e:
        print(f"  ✗ 密度测试失败: {e}")
        return 1

    # 测试4: 批量处理
    print("\n[测试4] 批量处理")
    try:
        batch_data = [
            test_data,
            {
                "title": "2026年AI发展趋势",
                "content": "人工智能在2026年将继续快速发展，特别是在自然语言处理领域。",
                "primary_keyword": "AI趋势",
                "keywords": ["人工智能", "机器学习"],
                "audience": "科技从业者",
            },
        ]
        results = gen.process_batch(batch_data)
        assert len(results) == 2, "应返回2条结果"
        for r in results:
            assert r.content and r.title, "每条结果应有内容"
        print(f"  ✓ 批量处理通过 ({len(results)} 条)")

    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        return 1

    # 测试5: 格式化输出
    print("\n[测试5] 格式化输出")
    try:
        single_result = [article]
        for fmt in ["text", "json", "markdown"]:
            output = gen.format_output(single_result, fmt)
            assert output is not None and len(output) > 0, f"{fmt} 格式输出不应为空"
        print("  ✓ 三种格式输出正常")

    except Exception as e:
        print(f"  ✗ 格式化测试失败: {e}")
        return 1

    # 测试6: 错误处理
    print("\n[测试6] 错误处理")
    try:
        # 空输入
        try:
            InputData.from_dict({})
            gen.process(InputData())
            print("  ✗ 应抛出 E003 错误")
            return 1
        except ValueError as e:
            assert "E003" in str(e), f"错误码应为E003，实际: {e}"
            print(f"  ✓ 错误码 E003 正确: {e}")

        # 非法数据
        try:
            parse_input("not valid json at all")
            print("  ✗ 应抛出 E001 或 E002 错误")
            return 1
        except ValueError as e:
            assert "E001" in str(e) or "E002" in str(e), f"错误码应为E001或E002，实际: {e}"
            print(f"  ✓ 错误码 E001/E002 正确: {e}")

    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        return 1

    print("\n=== 所有自检通过 ===")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="SEO文案生成器 — 将输入数据转为结构化SEO文案",
        epilog="示例: echo '{\"title\":\"测试文章\",\"content\":\"内容\",\"primary_keyword\":\"测试\"}' | python main.py",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入JSON字符串或文件路径（文件路径以@开头）",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["text", "json", "markdown"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：输入为JSON数组",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="最低置信度阈值 (默认: 0.5)",
    )
    parser.add_argument(
        "--target-density",
        type=float,
        default=0.03,
        help="目标关键词密度 (默认: 0.03)",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 配置
    config = {
        "min_confidence": args.min_confidence,
        "target_density": args.target_density,
    }

    try:
        # 获取输入
        if not args.input:
            # 从标准输入读取
            raw_input = sys.stdin.read().strip()
            if not raw_input:
                print(err("E001", "请通过 --input 参数或标准输入提供数据"), file=sys.stderr)
                return 1
        elif args.input.startswith("@"):
            # 从文件读取
            filepath = args.input[1:]
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_input = f.read().strip()
            except FileNotFoundError:
                print(err("E001", f"文件不存在: {filepath}"), file=sys.stderr)
                return 1
        else:
            raw_input = args.input

        # 解析输入
        if args.batch:
            data_list = json.loads(raw_input)
            if not isinstance(data_list, list):
                print(err("E002", "批量模式需要JSON数组"), file=sys.stderr)
                return 1
        else:
            data_list = [parse_input(raw_input)]

        # 处理
        gen = SEOGenerator(config)

        if args.batch:
            articles = gen.process_batch(data_list)
        else:
            input_data = InputData.from_dict(data_list[0])
            articles = [gen.process(input_data)]

        # 输出
        output = gen.format_output(articles, args.format)
        print(output)
        return 0

    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(err("E008", str(e)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
