#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notewise — 知识笔记结构化整理（独立实现）
=========================================
依据功能规格独立开发的 clean-room 实现。
将零散笔记转换为结构化知识卡片（JSON 格式）。

用法:
    python scripts/main.py --selftest
    python scripts/main.py --input note.txt --output out.json
    python scripts/main.py --batch batch.json

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================================
# 常量定义
# ============================================================

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入文件不存在或不可读",
    "E002": "输出文件无法写入",
    "E003": "输入内容为空",
    "E004": "批量模式输入格式非法（需为 JSON 列表）",
    "E005": "单条笔记内容不是字符串",
    "E006": "批量列表为空",
    "E007": "JSON 序列化失败",
    "E008": "参数组合非法",
    "E009": "内部逻辑错误（未知类型）",
    "E010": "未知错误",
}

# 模板版本号
TEMPLATE_VERSION = "1.0.0"

# 置信度阈值（宽松区间，用于自检）
CONFIDENCE_LOW = 0.3
CONFIDENCE_MID = 0.6
CONFIDENCE_HIGH = 0.9


# ============================================================
# 核心数据结构与处理逻辑
# ============================================================

class NoteParser:
    """笔记解析器：将原始文本转换为结构化知识卡片。"""

    # 概念/定义关键词
    CONCEPT_KEYWORDS = [
        "定义", "概念", "什么是", "即", "是指", "称为", "意味着", "本质",
        "定义:", "概念:", "什么是:", "即:", "是指:", "称为:", "意味着:",
    ]

    # 流程关键词
    PROCESS_KEYWORDS = [
        "流程", "步骤", "过程", "方法", "算法", "如何", "怎么做",
        "流程:", "步骤:", "过程:", "方法:", "算法:", "如何:", "怎么做:",
    ]

    # 结论关键词
    CONCLUSION_KEYWORDS = [
        "结论", "总结", "因此", "所以", "总之", "综上", "最终",
        "结论:", "总结:", "因此:", "所以:", "总之:", "综上:", "最终:",
    ]

    # 待办关键词
    TODO_KEYWORDS = [
        "待办", "任务", "需要", "必须", "记得", "别忘了", "TODO", "todo",
        "待办:", "任务:", "需要:", "必须:", "记得:", "别忘了:", "TODO:", "todo:",
    ]

    # 标签关键词（用于提取标签）
    TAG_KEYWORDS = [
        "标签", "主题", "分类", "领域", "关键词",
        "标签:", "主题:", "分类:", "领域:", "关键词:",
    ]

    def __init__(self, content: str):
        """初始化解析器。

        Args:
            content: 原始笔记内容（字符串）。

        Raises:
            ValueError: 当内容为空或不是字符串时抛出 E003/E005 错误。
        """
        if not isinstance(content, str):
            raise ValueError(f"E005: {ERROR_CODES['E005']}")
        if not content.strip():
            raise ValueError(f"E003: {ERROR_CODES['E003']}")

        self.content = content
        self.lines = content.splitlines()
        self._clean_lines = [line.strip() for line in self.lines if line.strip()]

    def parse(self) -> Dict[str, Any]:
        """执行解析，返回结构化知识卡片。

        Returns:
            Dict: 结构化知识卡片字典。
        """
        title = self._extract_title()
        summary = self._extract_summary()
        tags = self._extract_tags()
        entities = self._extract_entities()
        confidence = self._compute_confidence()
        needs_verification = self._find_verification_needs()

        card = {
            "title": title,
            "summary": summary,
            "tags": tags,
            "entities": entities,
            "confidence": confidence,
            "needs_verification": needs_verification,
            "template_version": TEMPLATE_VERSION,
            "parsed_at": datetime.now().isoformat(timespec="seconds"),
        }
        return card

    def _extract_title(self) -> str:
        """提取标题。优先使用 # 标题，否则使用第一行。"""
        for line in self._clean_lines:
            if line.startswith("#"):
                # 去掉所有 # 和空格
                title = line.lstrip("#").strip()
                if title:
                    return title
        # 无标题时取第一行前 50 字符
        first_line = self._clean_lines[0] if self._clean_lines else "未命名笔记"
        return first_line[:50]

    def _extract_summary(self) -> str:
        """提取摘要。优先使用摘要标记，否则取前 200 字符。"""
        # 查找摘要标记
        for line in self._clean_lines:
            if line.startswith("摘要") or line.startswith("概述"):
                # 去掉标记本身
                summary = re.sub(r"^(摘要|概述)\s*[:：]?\s*", "", line)
                if summary:
                    return summary[:200]

        # 无摘要标记时，取首段（第一段非空文本）
        paragraphs = self._split_paragraphs()
        if paragraphs:
            return paragraphs[0][:200]
        return self._clean_lines[0][:200] if self._clean_lines else ""

    def _split_paragraphs(self) -> List[str]:
        """将文本分割为段落列表。"""
        paragraphs = []
        current = []
        for line in self.lines:
            if line.strip():
                current.append(line.strip())
            else:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
        if current:
            paragraphs.append(" ".join(current))
        return paragraphs

    def _extract_tags(self) -> List[str]:
        """提取标签。优先使用标签标记，否则从内容中提取关键词。"""
        tags = []

        # 尝试从标签标记中提取
        for line in self._clean_lines:
            for keyword in self.TAG_KEYWORDS:
                if line.startswith(keyword):
                    tag_part = line[len(keyword):].strip()
                    # 支持逗号、顿号、空格分隔
                    candidates = re.split(r"[,，、\s]+", tag_part)
                    tags.extend([c for c in candidates if c])
                    break

        # 如果没有找到标签，从内容中提取关键词
        if not tags:
            # 提取中文词汇（2-6字）作为潜在标签
            words = re.findall(r"[\u4e00-\u9fff]{2,6}", self.content)
            # 过滤常见停用词
            stopwords = {"我们", "你们", "他们", "这个", "那个", "一个", "可以", "需要", "进行", "以及"}
            candidates = [w for w in words if w not in stopwords and len(w) >= 2]
            # 去重并限制数量
            seen = set()
            for w in candidates:
                if w not in seen:
                    seen.add(w)
                    tags.append(w)
                if len(tags) >= 5:
                    break

        return tags[:10]  # 最多 10 个标签

    def _extract_entities(self) -> List[Dict[str, str]]:
        """提取实体（概念、流程、结论、待办）。"""
        entities = []

        # 按行扫描，识别实体类型
        for i, line in enumerate(self._clean_lines):
            # 识别概念
            if self._is_concept_line(line):
                concept = self._extract_concept(line)
                if concept:
                    entities.append({"type": "概念/定义", "content": concept})

            # 识别流程
            if self._is_process_line(line):
                process = self._extract_process(line)
                if process:
                    entities.append({"type": "流程/步骤", "content": process})

            # 识别结论
            if self._is_conclusion_line(line):
                conclusion = self._extract_conclusion(line)
                if conclusion:
                    entities.append({"type": "结论", "content": conclusion})

            # 识别待办
            if self._is_todo_line(line):
                todo = self._extract_todo(line)
                if todo:
                    entities.append({"type": "待办", "content": todo})

        return entities

    def _is_concept_line(self, line: str) -> bool:
        """判断是否包含概念/定义。"""
        return any(kw in line for kw in self.CONCEPT_KEYWORDS)

    def _extract_concept(self, line: str) -> str:
        """提取概念内容。"""
        # 尝试匹配 "XXX 是 YYY" 或 "XXX 即 YYY"
        patterns = [
            r"(.+?)\s+是\s+(.+)",
            r"(.+?)\s+即\s+(.+)",
            r"(.+?)\s+是指\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return f"{match.group(1)}: {match.group(2)}"
        # 默认返回整行
        return line[:100]

    def _is_process_line(self, line: str) -> bool:
        """判断是否包含流程/步骤。"""
        return any(kw in line for kw in self.PROCESS_KEYWORDS)

    def _extract_process(self, line: str) -> str:
        """提取流程内容。"""
        return line[:150]

    def _is_conclusion_line(self, line: str) -> bool:
        """判断是否包含结论。"""
        return any(kw in line for kw in self.CONCLUSION_KEYWORDS)

    def _extract_conclusion(self, line: str) -> str:
        """提取结论内容。"""
        return line[:100]

    def _is_todo_line(self, line: str) -> bool:
        """判断是否包含待办。"""
        return any(kw in line for kw in self.TODO_KEYWORDS)

    def _extract_todo(self, line: str) -> str:
        """提取待办内容。"""
        return line[:100]

    def _compute_confidence(self) -> float:
        """计算置信度（0.0-1.0）。

        置信度基于信息完整度：实体数量、标签数量、是否有摘要。
        """
        score = 0.3  # 基础分

        # 有摘要加分
        summary = self._extract_summary()
        if summary and len(summary) >= 20:
            score += 0.2

        # 有实体加分
        entities = self._extract_entities()
        if entities:
            score += min(0.3, len(entities) * 0.1)

        # 有标签加分
        tags = self._extract_tags()
        if tags:
            score += min(0.2, len(tags) * 0.05)

        return min(1.0, score)

    def _find_verification_needs(self) -> List[str]:
        """查找需要核实的信息字段。

        当内容较短、缺少关键信息时，标记需要核实的字段。
        """
        needs = []

        # 检查是否有摘要
        if len(self._extract_summary()) < 20:
            needs.append("摘要")

        # 检查是否有实体
        if not self._extract_entities():
            needs.append("概念/定义")

        # 检查是否有标签
        if not self._extract_tags():
            needs.append("标签")

        # 检查内容长度
        if len(self.content) < 100:
            needs.append("详细内容")

        return needs


def parse_single_note(content: str) -> Dict[str, Any]:
    """解析单条笔记。

    Args:
        content: 笔记内容字符串。

    Returns:
        Dict: 结构化知识卡片。

    Raises:
        ValueError: 当内容非法时抛出对应错误。
    """
    parser = NoteParser(content)
    return parser.parse()


def parse_batch_notes(notes: List[str]) -> List[Dict[str, Any]]:
    """批量解析笔记。

    Args:
        notes: 笔记字符串列表。

    Returns:
        List[Dict]: 结构化知识卡片列表。

    Raises:
        ValueError: 当输入非法时抛出对应错误。
    """
    if not isinstance(notes, list):
        raise ValueError(f"E004: {ERROR_CODES['E004']}")
    if not notes:
        raise ValueError(f"E006: {ERROR_CODES['E006']}")

    results = []
    for i, note in enumerate(notes):
        try:
            card = parse_single_note(note)
            results.append(card)
        except ValueError as e:
            # 批量模式下，单条失败不中断，标记错误
            results.append({
                "error": str(e),
                "index": i,
            })
    return results


# ============================================================
# 文件处理与命令行接口
# ============================================================

def read_input_file(filepath: str) -> str:
    """读取输入文件。

    Args:
        filepath: 文件路径。

    Returns:
        str: 文件内容。

    Raises:
        ValueError: 当文件不存在或不可读时抛出 E001。
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"E001: {ERROR_CODES['E001']}: {filepath}")
    except PermissionError:
        raise ValueError(f"E001: {ERROR_CODES['E001']}: {filepath} (权限不足)")
    except Exception as e:
        raise ValueError(f"E001: {ERROR_CODES['E001']}: {filepath} ({e})")


def write_output_file(filepath: str, data: Any) -> None:
    """写入输出文件。

    Args:
        filepath: 文件路径。
        data: 要写入的数据（JSON 序列化）。

    Raises:
        ValueError: 当写入失败时抛出 E002 或 E007。
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ValueError(f"E007: {ERROR_CODES['E007']}: {e}")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception as e:
        raise ValueError(f"E002: {ERROR_CODES['E002']}: {filepath} ({e})")


def process_batch_file(filepath: str) -> List[Dict[str, Any]]:
    """处理批量输入文件。

    Args:
        filepath: JSON 文件路径，内容为字符串数组。

    Returns:
        List[Dict]: 解析结果列表。

    Raises:
        ValueError: 当文件格式非法时抛出 E001/E004/E006。
    """
    content = read_input_file(filepath)
    try:
        notes = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"E004: {ERROR_CODES['E004']}: JSON 解析失败 ({e})")

    if not isinstance(notes, list):
        raise ValueError(f"E004: {ERROR_CODES['E004']}: 顶层必须是数组")

    return parse_batch_notes(notes)


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> int:
    """运行内置自检。

    使用硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。

    Returns:
        int: 0 表示自检通过，非 0 表示失败。
    """
    print("=" * 60)
    print("notewise 自检开始")
    print("=" * 60)

    # ---- 测试用例 1：单条笔记解析 ----
    print("\n[测试 1] 单条笔记解析")
    sample_note = """
    # 机器学习基础笔记

    机器学习是人工智能的一个分支，其核心是让计算机从数据中学习规律。

    定义：机器学习是一种通过数据驱动的方式，让计算机自动改进性能的方法。

    主要流程包括：
    1. 数据收集
    2. 数据预处理
    3. 模型选择
    4. 模型训练
    5. 评估与优化

    结论：机器学习已经在图像识别、自然语言处理等领域取得显著成果。

    待办：需要进一步学习深度学习相关内容。

    标签：人工智能, 数据科学, 算法
    """

    try:
        card = parse_single_note(sample_note)

        # 断言：标题非空
        assert card["title"], "标题不应为空"
        print(f"  [OK] 标题: {card['title']}")

        # 断言：摘要非空
        assert card["summary"], "摘要不应为空"
        print(f"  [OK] 摘要: {card['summary'][:30]}...")

        # 断言：标签数量 > 0
        assert len(card["tags"]) > 0, "标签不应为空"
        print(f"  [OK] 标签数量: {len(card['tags'])}")

        # 断言：实体数量 > 0（应该有概念、流程、结论、待办）
        assert len(card["entities"]) >= 3, f"实体数量应 >= 3，实际: {len(card['entities'])}"
        print(f"  [OK] 实体数量: {len(card['entities'])}")

        # 断言：置信度在合理区间（宽松判断）
        assert 0.0 <= card["confidence"] <= 1.0, "置信度应在 [0, 1] 区间"
        assert card["confidence"] > CONFIDENCE_LOW, f"置信度应 > {CONFIDENCE_LOW}"
        print(f"  [OK] 置信度: {card['confidence']:.2f}")

        # 断言：需要核实字段是列表
        assert isinstance(card["needs_verification"], list), "needs_verification 应为列表"
        print(f"  [OK] 需要核实字段数: {len(card['needs_verification'])}")

        print("  [通过] 单条笔记解析测试")

    except AssertionError as e:
        print(f"  [失败] 断言错误: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 未预期异常: {e}")
        return 1

    # ---- 测试用例 2：批量解析 ----
    print("\n[测试 2] 批量解析")
    batch_notes = [
        "会议纪要：讨论了项目进度，结论是按时交付。",
        "读书笔记：第二章介绍了分布式系统的基本概念。",
    ]

    try:
        results = parse_batch_notes(batch_notes)

        # 断言：结果数量与输入一致
        assert len(results) == len(batch_notes), "结果数量应与输入一致"
        print(f"  [OK] 结果数量: {len(results)}")

        # 断言：每条结果都有标题
        for i, r in enumerate(results):
            assert r.get("title"), f"结果 {i} 缺少标题"
        print("  [OK] 所有结果都有标题")

        print("  [通过] 批量解析测试")

    except AssertionError as e:
        print(f"  [失败] 断言错误: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 未预期异常: {e}")
        return 1

    # ---- 测试用例 3：空内容处理 ----
    print("\n[测试 3] 空内容处理")
    try:
        parse_single_note("")
        print("  [失败] 空内容应抛出异常")
        return 1
    except ValueError as e:
        assert "E003" in str(e), f"错误码应为 E003，实际: {e}"
        print(f"  [OK] 正确抛出 E003: {e}")
        print("  [通过] 空内容处理测试")

    # ---- 测试用例 4：非字符串处理 ----
    print("\n[测试 4] 非字符串处理")
    try:
        parse_single_note(123)  # type: ignore
        print("  [失败] 非字符串应抛出异常")
        return 1
    except ValueError as e:
        assert "E005" in str(e), f"错误码应为 E005，实际: {e}"
        print(f"  [OK] 正确抛出 E005: {e}")
        print("  [通过] 非字符串处理测试")

    # ---- 测试用例 5：批量空列表 ----
    print("\n[测试 5] 批量空列表")
    try:
        parse_batch_notes([])
        print("  [失败] 空列表应抛出异常")
        return 1
    except ValueError as e:
        assert "E006" in str(e), f"错误码应为 E006，实际: {e}"
        print(f"  [OK] 正确抛出 E006: {e}")
        print("  [通过] 批量空列表测试")

    # ---- 测试用例 6：短文本解析 ----
    print("\n[测试 6] 短文本解析")
    short_note = "简单笔记。"
    try:
        card = parse_single_note(short_note)

        # 断言：短文本也能生成卡片
        assert card["title"], "短文本也应生成标题"
        print(f"  [OK] 标题: {card['title']}")

        # 断言：短文本应该有需要核实的内容
        assert len(card["needs_verification"]) > 0, "短文本应有需要核实的字段"
        print(f"  [OK] 需要核实字段: {card['needs_verification']}")

        print("  [通过] 短文本解析测试")

    except AssertionError as e:
        print(f"  [失败] 断言错误: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 未预期异常: {e}")
        return 1

    # ---- 测试用例 7：Markdown 格式解析 ----
    print("\n[测试 7] Markdown 格式解析")
    markdown_note = """
    ## 分布式系统

    分布式系统是由多台计算机组成的系统，这些计算机通过网络通信协作完成共同任务。

    ### 关键特性
    - 可扩展性
    - 容错性
    - 一致性

    总结：分布式系统设计需要在一致性、可用性和分区容错性之间权衡。
    """

    try:
        card = parse_single_note(markdown_note)

        # 断言：Markdown 标题被正确提取
        assert "分布式系统" in card["title"], f"标题应包含'分布式系统'，实际: {card['title']}"
        print(f"  [OK] 标题: {card['title']}")

        # 断言：摘要非空
        assert card["summary"], "摘要不应为空"
        print(f"  [OK] 摘要: {card['summary'][:30]}...")

        # 断言：有结论实体
        conclusion_found = any(e["type"] == "结论" for e in card["entities"])
        assert conclusion_found, "应识别出结论实体"
        print("  [OK] 识别出结论实体")

        print("  [通过] Markdown 格式解析测试")

    except AssertionError as e:
        print(f"  [失败] 断言错误: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 未预期异常: {e}")
        return 1

    # ---- 总结 ----
    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数。

    Returns:
        int: 退出码，0 表示成功，非 0 表示失败。
    """
    parser = argparse.ArgumentParser(
        description="notewise — 知识笔记结构化整理工具",
        epilog="示例: python scripts/main.py --input note.txt --output out.json",
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径（纯文本/Markdown）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（JSON）",
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量模式：输入 JSON 文件（字符串数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if args.batch:
        # 批量模式
        if args.input:
            print(f"E008: {ERROR_CODES['E008']} --batch 与 --input 不能同时使用", file=sys.stderr)
            return 8

        try:
            results = process_batch_file(args.batch)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        # 输出
        output = {"results": results, "count": len(results)}
        if args.output:
            try:
                write_output_file(args.output, output)
                print(f"已写入 {args.output}")
            except ValueError as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))

    elif args.input:
        # 单条模式
        try:
            content = read_input_file(args.input)
            card = parse_single_note(content)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        # 输出
        if args.output:
            try:
                write_output_file(args.output, card)
                print(f"已写入 {args.output}")
            except ValueError as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1
        else:
            print(json.dumps(card, ensure_ascii=False, indent=2))

    else:
        # 未提供输入
        print(f"E008: {ERROR_CODES['E008']} 请提供 --input 或 --batch 参数", file=sys.stderr)
        parser.print_help()
        return 8

    return 0


if __name__ == "__main__":
    sys.exit(main())
