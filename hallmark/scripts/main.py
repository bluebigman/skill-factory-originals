#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hallmark — 内容甄别与风格净化工具
独立实现脚本，基于功能规格 clean-room 重写。
仅使用标准库，支持离线自检（--selftest）。
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "输入为空：没有提供任何文本内容",
    "E003": "文本块数量超过上限（最多5个）",
    "E004": "输出格式不支持（仅支持 json 或 markdown）",
    "E005": "文件读取失败：文件不存在或无法访问",
    "E006": "URL 访问失败：无法获取远程内容",
    "E007": "内部计算错误：文本分析过程中出现异常",
    "E008": "自检失败：核心逻辑验证未通过",
    "E009": "参数冲突：同时指定了互斥的参数",
    "E010": "未知错误：未预期的异常发生",
}


class HallmarkError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================

@dataclass
class AnalysisResult:
    """单个文本块的分析结果。"""
    index: int
    text_length: int
    sentence_count: int
    avg_sentence_length: float
    paragraph_lengths: List[int]
    paragraph_length_std: float
    repeated_connectors: Dict[str, int]
    template_openings: List[str]
    template_closings: List[str]
    overly_neat_ratio: float
    ai_trace_score: float  # 0~100，越高越像 AI 痕迹
    suggestions: List[str] = field(default_factory=list)


@dataclass
class BatchReport:
    """批量分析报告。"""
    results: List[AnalysisResult]
    generated_at: str
    version: str


# ============================================================
# 文本分析核心逻辑
# ============================================================

# 高频连接词（AI 文本中常见）
HIGH_FREQ_CONNECTORS = [
    "首先", "其次", "最后", "总之", "总而言之",
    "此外", "另外", "同时", "然而", "因此",
    "所以", "但是", "不过", "换句话说", "综上所述",
    "值得注意的是", "毫无疑问", "显而易见", "事实上",
    "实际上", "总的来说", "具体来说", "换句话说",
]

# 模板化开头模式（AI 文本常见开头）
TEMPLATE_OPENING_PATTERNS = [
    r"^在当今(社会|时代|世界)",
    r"^随着(社会|科技|时代|经济)的(发展|进步|变革)",
    r"^众所周知",
    r"^近年来",
    r"^在这个(充满|快速|日益)",
    r"^随着(人们|现代|数字)",
    r"^首先[,，]?让我们",
    r"^本文(将|旨在|试图)",
    r"^这是一个(值得|需要|引人)",
]

# 模板化结尾模式
TEMPLATE_CLOSING_PATTERNS = [
    r"综上所述[,，]?$",
    r"总而言之[,，]?$",
    r"总之[,，]?$",
    r"相信(通过|经过|随着).*(一定|必将|将会|能够)",
    r"让我们(一起|共同).*(吧|！|!)",
    r"这就是.*(意义|价值|所在)",
    r"希望.*能够(帮助|提供|带来)",
    r"未来(已来|可期|充满)",
]


def split_sentences(text: str) -> List[str]:
    """将文本拆分为句子列表（简单启发式）。"""
    # 按中英文句号、感叹号、问号、分号拆分
    parts = re.split(r'[。！？!?；;\n]+', text)
    return [p.strip() for p in parts if p.strip()]


def split_paragraphs(text: str) -> List[str]:
    """将文本拆分为段落列表。"""
    # 按换行符拆分，过滤空段落
    paragraphs = re.split(r'\n\s*\n|\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def calculate_std(values: List[int]) -> float:
    """计算标准差（宽松实现，避免空列表）。"""
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def count_connectors(text: str) -> Dict[str, int]:
    """统计高频连接词出现次数。"""
    counts = {}
    for conn in HIGH_FREQ_CONNECTORS:
        count = text.count(conn)
        if count > 0:
            counts[conn] = count
    return counts


def detect_template_openings(text: str) -> List[str]:
    """检测模板化开头。"""
    matches = []
    for pattern in TEMPLATE_OPENING_PATTERNS:
        if re.search(pattern, text[:200]):  # 只检查前200字符
            matches.append(pattern)
    return matches


def detect_template_closings(text: str) -> List[str]:
    """检测模板化结尾。"""
    matches = []
    tail = text[-200:] if len(text) > 200 else text
    for pattern in TEMPLATE_CLOSING_PATTERNS:
        if re.search(pattern, tail):
            matches.append(pattern)
    return matches


def analyze_text(text: str, index: int) -> AnalysisResult:
    """分析单个文本块，返回结构化结果。"""
    try:
        # 基础统计
        text_length = len(text)
        sentences = split_sentences(text)
        sentence_count = len(sentences)
        avg_sentence_length = (text_length / sentence_count) if sentence_count > 0 else 0.0

        # 段落分析
        paragraphs = split_paragraphs(text)
        paragraph_lengths = [len(p) for p in paragraphs]
        paragraph_length_std = calculate_std(paragraph_lengths)

        # 连接词统计
        connector_counts = count_connectors(text)

        # 模板化检测
        template_openings = detect_template_openings(text)
        template_closings = detect_template_closings(text)

        # 过度工整比率：段落长度标准差归一化
        # 段落长度越均匀（std 越小），越可能 AI 生成
        max_std = 200.0  # 宽松上限
        neat_score = max(0.0, 1.0 - (paragraph_length_std / max_std)) if paragraph_lengths else 0.0

        # AI 痕迹综合评分（0~100）
        score = 0.0
        # 1. 连接词密度（最多贡献30分）
        connector_count = sum(connector_counts.values())
        connector_density = connector_count / max(1, sentence_count)
        score += min(30.0, connector_density * 30.0)

        # 2. 模板化开头（最多贡献25分）
        if template_openings:
            score += min(25.0, len(template_openings) * 12.5)

        # 3. 模板化结尾（最多贡献20分）
        if template_closings:
            score += min(20.0, len(template_closings) * 10.0)

        # 4. 段落均匀度（最多贡献15分）
        score += neat_score * 15.0

        # 5. 平均句长过短或过长惩罚（最多贡献10分）
        if avg_sentence_length > 0:
            if avg_sentence_length < 10 or avg_sentence_length > 80:
                score += 10.0  # 异常句长

        # 生成建议
        suggestions = []
        if connector_density > 0.3:
            suggestions.append(f"连接词使用较密集（每句约{connector_density:.1f}个），建议替换部分连接词为具体描述。")
        if template_openings:
            suggestions.append("检测到模板化开头，建议改写为更具个性化的切入方式。")
        if template_closings:
            suggestions.append("检测到模板化结尾，建议使用更自然、具体的收束方式。")
        if paragraph_length_std < 50 and len(paragraph_lengths) >= 3:
            suggestions.append("段落长度过于均匀，建议调整段落节奏，增加长短变化。")
        if not suggestions:
            suggestions.append("未发现明显AI痕迹，文本风格较为自然。")

        return AnalysisResult(
            index=index,
            text_length=text_length,
            sentence_count=sentence_count,
            avg_sentence_length=round(avg_sentence_length, 2),
            paragraph_lengths=paragraph_lengths,
            paragraph_length_std=round(paragraph_length_std, 2),
            repeated_connectors=connector_counts,
            template_openings=template_openings,
            template_closings=template_closings,
            overly_neat_ratio=round(neat_score, 4),
            ai_trace_score=round(score, 2),
            suggestions=suggestions,
        )
    except Exception as e:
        raise HallmarkError("E007", f"文本分析失败：{str(e)}")


def analyze_batch(texts: List[str]) -> BatchReport:
    """批量分析多个文本块。"""
    if not texts:
        raise HallmarkError("E002")
    if len(texts) > 5:
        raise HallmarkError("E003")

    results = []
    for i, text in enumerate(texts):
        if not text.strip():
            raise HallmarkError("E002", f"第{i+1}个文本块为空")
        results.append(analyze_text(text, i))

    from datetime import datetime
    return BatchReport(
        results=results,
        generated_at=datetime.now().isoformat(),
        version="1.0.1",
    )


# ============================================================
# 输出格式化
# ============================================================

def format_markdown(report: BatchReport) -> str:
    """输出 Markdown 格式报告。"""
    lines = []
    lines.append("# hallmark 分析报告")
    lines.append(f"\n> 版本 {report.version} | 生成时间 {report.generated_at}\n")

    for result in report.results:
        lines.append(f"\n## 文本块 #{result.index + 1}\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 文本长度 | {result.text_length} 字符 |")
        lines.append(f"| 句子数 | {result.sentence_count} |")
        lines.append(f"| 平均句长 | {result.avg_sentence_length:.2f} 字符 |")
        lines.append(f"| 段落数 | {len(result.paragraph_lengths)} |")
        lines.append(f"| 段落长度标准差 | {result.paragraph_length_std:.2f} |")
        lines.append(f"| AI痕迹评分 | **{result.ai_trace_score:.1f}/100** |")

        if result.repeated_connectors:
            lines.append(f"\n**高频连接词：**")
            for conn, count in sorted(result.repeated_connectors.items(), key=lambda x: -x[1]):
                lines.append(f"- {conn}：{count} 次")

        if result.template_openings:
            lines.append(f"\n**模板化开头：**")
            for p in result.template_openings:
                lines.append(f"- `{p}`")

        if result.template_closings:
            lines.append(f"\n**模板化结尾：**")
            for p in result.template_closings:
                lines.append(f"- `{p}`")

        lines.append(f"\n**建议：**")
        for s in result.suggestions:
            lines.append(f"- {s}")

    return "\n".join(lines)


def format_json(report: BatchReport) -> str:
    """输出 JSON 格式报告。"""
    data = {
        "version": report.version,
        "generated_at": report.generated_at,
        "results": [
            {
                "index": r.index,
                "text_length": r.text_length,
                "sentence_count": r.sentence_count,
                "avg_sentence_length": r.avg_sentence_length,
                "paragraph_lengths": r.paragraph_lengths,
                "paragraph_length_std": r.paragraph_length_std,
                "repeated_connectors": r.repeated_connectors,
                "template_openings": r.template_openings,
                "template_closings": r.template_closings,
                "overly_neat_ratio": r.overly_neat_ratio,
                "ai_trace_score": r.ai_trace_score,
                "suggestions": r.suggestions,
            }
            for r in report.results
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 自检逻辑（离线硬编码数据）
# ============================================================

def run_selftest() -> bool:
    """离线自检核心逻辑。使用硬编码数据，不读文件、不联网。"""
    try:
        # 构造两组对比文本：一组明显像AI，一组更像人类
        ai_like_text = (
            "首先，随着科技的快速发展，人工智能已经深刻改变了我们的生活。"
            "其次，它为我们带来了前所未有的便利和效率。"
            "此外，我们还需要关注它带来的潜在风险。"
            "最后，我们应该以积极的态度迎接这场变革。"
            "综上所述，人工智能的未来充满希望。"
            "总而言之，我们需要在发展中保持警惕。"
            "值得注意的是，这是一个值得深入思考的话题。"
        )

        human_like_text = (
            "昨天下午我去了趟菜市场。"
            "卖菜的大姐说今年雨水多，青菜都涨价了。"
            "我买了把韭菜，想着晚上包饺子。"
            "回家路上遇到隔壁老王，他正遛他那条胖得跑不动的柯基。"
            "这种日常琐碎的日子，其实也挺好的。"
        )

        texts = [ai_like_text, human_like_text]
        report = analyze_batch(texts)

        # 断言1：AI样本评分应显著高于人类样本
        ai_score = report.results[0].ai_trace_score
        human_score = report.results[1].ai_trace_score
        assert ai_score > human_score, f"AI样本({ai_score})应高于人类样本({human_score})"

        # 断言2：AI样本应检测到连接词
        assert len(report.results[0].repeated_connectors) >= 2, "AI样本应检测到多个连接词"

        # 断言3：人类样本连接词应较少
        assert len(report.results[1].repeated_connectors) <= 1, "人类样本连接词应很少"

        # 断言4：评分应在合理区间（宽松阈值）
        assert 0 <= ai_score <= 100, f"评分应在0-100区间，实际{ai_score}"
        assert 0 <= human_score <= 100, f"评分应在0-100区间，实际{human_score}"

        # 断言5：AI样本应检测到模板化开头或结尾
        assert (
            len(report.results[0].template_openings) > 0
            or len(report.results[0].template_closings) > 0
        ), "AI样本应检测到模板化模式"

        # 断言6：建议列表非空
        assert len(report.results[0].suggestions) > 0, "建议列表不应为空"
        assert len(report.results[1].suggestions) > 0, "建议列表不应为空"

        # 断言7：句子数应为正数
        assert report.results[0].sentence_count > 0, "句子数应为正数"
        assert report.results[1].sentence_count > 0, "句子数应为正数"

        # 断言8：段落长度列表应与文本匹配
        assert len(report.results[0].paragraph_lengths) >= 1, "至少应有一个段落"

        # 断言9：JSON 输出应可序列化
        json_out = format_json(report)
        parsed = json.loads(json_out)
        assert len(parsed["results"]) == 2, "JSON 应包含2个结果"

        # 断言10：Markdown 输出应包含关键信息
        md_out = format_markdown(report)
        assert "AI痕迹评分" in md_out, "Markdown 应包含评分信息"

        print("[SELFTEST] 全部核心逻辑验证通过 ✅")
        print(f"[SELFTEST] AI样本评分: {ai_score:.1f}, 人类样本评分: {human_score:.1f}")
        return True

    except AssertionError as e:
        print(f"[SELFTEST] 断言失败: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[SELFTEST] 异常: {e}", file=sys.stderr)
        return False


# ============================================================
# 命令行入口
# ============================================================

def read_input_file(path: str) -> str:
    """读取文本文件内容。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HallmarkError("E005", f"文件不存在: {path}")
    except Exception as e:
        raise HallmarkError("E005", f"文件读取失败: {str(e)}")


def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="hallmark — 内容甄别与风格净化工具",
        epilog="示例: python main.py --text '你的文本' --format json",
    )
    parser.add_argument("--text", type=str, help="待分析文本（直接传入）")
    parser.add_argument("--file", type=str, help="待分析文本文件路径（.txt 或 .md）")
    parser.add_argument("--format", type=str, choices=["json", "markdown"], default="markdown",
                        help="输出格式（默认 markdown）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="hallmark 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        if args.text or args.file:
            raise HallmarkError("E009", "--selftest 不能与其他输入参数同时使用")
        ok = run_selftest()
        return 0 if ok else 1

    # 收集输入文本
    texts = []
    try:
        if args.text:
            texts.append(args.text)
        elif args.file:
            content = read_input_file(args.file)
            texts.append(content)
        else:
            # 从标准输入读取
            content = sys.stdin.read().strip()
            if content:
                texts.append(content)
            else:
                raise HallmarkError("E001", "请通过 --text、--file 或标准输入提供文本")

        # 执行分析
        report = analyze_batch(texts)

        # 输出结果
        if args.format == "json":
            print(format_json(report))
        else:
            print(format_markdown(report))

        return 0

    except HallmarkError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
