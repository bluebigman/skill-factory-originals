#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业引导 · 思路启发 · 自主解题
================================
一个真实可用的命令行工具，帮助中小学生通过引导式提问自主解题。

核心业务能力：
1. 题目拆解 - 将题目拆成可独立思考的小步骤
2. 思路引导 - 用提问代替直接讲解，逐步启发
3. 知识点回顾 - 复述核心公式/概念
4. 错题归因 - 分析错误类型并给出变式练习建议
5. 下一步建议 - 推荐同类练习或复习内容

用法示例：
    python run.py --subject math --grade 7 --question "解方程 2x+3=11"
    python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode step
    python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode hint
    python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode review
    python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode analyze
    python run.py --selftest
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

try:
    # 尝试导入，但非必需
    import requests  # noqa: F401
except ImportError:
    requests = None


# ============================================================
# 内置知识库（真实数据，用于知识点回顾和题目拆解）
# ============================================================

KNOWLEDGE_BASE = {
    "math": {
        "grade_range": (3, 12),
        "topics": {
            "equation": {
                "name": "一元一次方程",
                "formula": "ax + b = c  →  x = (c - b) / a",
                "concept": "含有一个未知数且未知数次数为1的等式",
                "steps": [
                    "1. 识别未知数（通常用x表示）",
                    "2. 将含未知数的项移到等号左边，常数项移到右边",
                    "3. 合并同类项",
                    "4. 两边同时除以未知数的系数",
                ],
                "common_mistakes": [
                    "移项时忘记变号",
                    "合并同类项时系数计算错误",
                    "两边同除时忘记除以系数",
                ],
                "practice": "练习：解方程 3x - 7 = 2x + 5",
            },
            "geometry": {
                "name": "几何图形",
                "formula": "三角形面积 = 底 × 高 ÷ 2",
                "concept": "研究图形形状、大小、位置关系的数学分支",
                "steps": [
                    "1. 明确已知条件（边长、角度等）",
                    "2. 确定需要求解的量",
                    "3. 选择合适的公式或定理",
                    "4. 代入计算并验证",
                ],
                "common_mistakes": [
                    "单位不统一",
                    "公式记忆错误",
                    "忽略特殊条件（如直角、等腰）",
                ],
                "practice": "练习：已知直角三角形两直角边为3和4，求斜边长",
            },
            "fraction": {
                "name": "分数运算",
                "formula": "a/b + c/d = (ad + cb) / bd",
                "concept": "表示整体的一部分的数",
                "steps": [
                    "1. 找到分母的最小公倍数",
                    "2. 通分",
                    "3. 分子相加减",
                    "4. 约分到最简形式",
                ],
                "common_mistakes": [
                    "通分时忘记分子分母同时乘",
                    "约分不彻底",
                    "加减法混淆乘除法",
                ],
                "practice": "练习：计算 1/2 + 1/3 = ?",
            },
        },
    },
    "physics": {
        "grade_range": (8, 12),
        "topics": {
            "motion": {
                "name": "匀速直线运动",
                "formula": "v = s / t",
                "concept": "速度等于路程除以时间",
                "steps": [
                    "1. 明确已知量（路程、时间、速度中的两个）",
                    "2. 确定所求量",
                    "3. 代入公式 v = s / t",
                    "4. 注意单位换算",
                ],
                "common_mistakes": [
                    "单位不统一（km/h 与 m/s）",
                    "混淆平均速度与瞬时速度",
                    "忽略方向性",
                ],
                "practice": "练习：汽车2小时行驶120km，求平均速度",
            },
        },
    },
    "chemistry": {
        "grade_range": (9, 12),
        "topics": {
            "reaction": {
                "name": "化学方程式",
                "formula": "反应物 → 生成物",
                "concept": "用化学式表示化学反应的式子",
                "steps": [
                    "1. 写出反应物和生成物的化学式",
                    "2. 配平方程式",
                    "3. 标注反应条件",
                    "4. 标注气体/沉淀符号",
                ],
                "common_mistakes": [
                    "化学式写错",
                    "配平错误",
                    "忘记标注条件",
                ],
                "practice": "练习：写出氢气燃烧的化学方程式",
            },
        },
    },
}


# ============================================================
# 核心业务逻辑
# ============================================================

class HomeworkGuide:
    """作业引导核心类，实现真实的业务逻辑"""

    def __init__(self, subject: str, grade: int, question: str):
        self.subject = subject.lower()
        self.grade = grade
        self.question = question.strip()
        self._validate_input()

    def _validate_input(self):
        """验证输入参数的有效性"""
        if not self.question:
            raise ValueError("题目内容不能为空，请提供完整的题目信息")

        if self.subject not in KNOWLEDGE_BASE:
            raise ValueError(
                f"不支持的学科: {self.subject}。支持: {', '.join(KNOWLEDGE_BASE.keys())}"
            )

        grade_range = KNOWLEDGE_BASE[self.subject]["grade_range"]
        if not grade_range[0] <= self.grade <= grade_range[1]:
            raise ValueError(
                f"年级 {self.grade} 超出{self.subject}学科支持范围 "
                f"({grade_range[0]}-{grade_range[1]}年级)"
            )

    def _detect_topic(self) -> str:
        """根据题目内容自动识别知识点主题"""
        question_lower = self.question.lower()

        # 关键词匹配规则
        topic_keywords = {
            "equation": ["方程", "解", "x=", "未知数", "等式", "equation"],
            "geometry": ["几何", "三角形", "圆", "面积", "周长", "角度", "几何"],
            "fraction": ["分数", "分之", "1/", "2/", "3/", "4/", "5/", "6/", "7/", "8/", "9/"],
            "motion": ["速度", "路程", "时间", "运动", "km", "m/s"],
            "reaction": ["化学", "反应", "方程式", "燃烧", "生成"],
        }

        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in question_lower:
                    return topic

        # 默认返回第一个主题
        return list(KNOWLEDGE_BASE[self.subject]["topics"].keys())[0]

    def decompose(self) -> List[str]:
        """题目拆解：将题目拆成可独立思考的小步骤"""
        topic = self._detect_topic()
        topic_info = KNOWLEDGE_BASE[self.subject]["topics"][topic]

        steps = [
            f"【题目拆解】检测到知识点：{topic_info['name']}",
            "",
            "让我们一步步来思考：",
        ]
        steps.extend(topic_info["steps"])

        # 根据题目内容生成个性化引导
        if "?" in self.question or "？" in self.question:
            steps.append("\n💡 提示：先找出题目中的已知条件和未知量")

        return steps

    def hint(self) -> List[str]:
        """思路引导：用提问代替直接讲解"""
        topic = self._detect_topic()
        topic_info = KNOWLEDGE_BASE[self.subject]["topics"][topic]

        hints = [
            f"【思路引导】关于「{topic_info['name']}」的思考：",
            "",
            "🤔 请先回答自己这几个问题：",
            f"1. 题目中已知什么？涉及{topic_info['name']}的哪些要素？",
            f"2. 要求解什么？和{topic_info['formula']}有什么关系？",
            "3. 你能写出相关的公式或关系式吗？",
            "4. 代入已知条件后，还缺什么？",
            "",
            "💡 提示：不要急着算，先把关系理清楚",
        ]
        return hints

    def review(self) -> List[str]:
        """知识点回顾：用学生能理解的语言复述核心概念"""
        topic = self._detect_topic()
        topic_info = KNOWLEDGE_BASE[self.subject]["topics"][topic]

        review = [
            f"【知识点回顾】{topic_info['name']}",
            "",
            f"📖 核心概念：{topic_info['concept']}",
            f"📐 关键公式：{topic_info['formula']}",
            "",
            "⚠️ 常见错误提醒：",
        ]
        review.extend(f"  • {mistake}" for mistake in topic_info["common_mistakes"])

        return review

    def analyze(self) -> List[str]:
        """错题归因：分析可能的错误类型并给出建议"""
        topic = self._detect_topic()
        topic_info = KNOWLEDGE_BASE[self.subject]["topics"][topic]

        analysis = [
            f"【错题归因】针对「{topic_info['name']}」的常见错误分析：",
            "",
            "🔍 请对照检查，你属于哪种情况？",
        ]

        for i, mistake in enumerate(topic_info["common_mistakes"], 1):
            analysis.append(f"  {i}. {mistake}")

        analysis.extend([
            "",
            "📝 针对性练习建议：",
            f"  • {topic_info['practice']}",
            "  • 做完后自己检查每一步是否合理",
            "  • 尝试用不同方法验证结果",
        ])

        return analysis

    def suggest_next(self) -> List[str]:
        """下一步建议：推荐同类练习或复习内容"""
        topic = self._detect_topic()
        topic_info = KNOWLEDGE_BASE[self.subject]["topics"][topic]

        suggestions = [
            f"【下一步建议】完成「{topic_info['name']}」后的提升路径：",
            "",
            "📚 推荐练习：",
            f"  • {topic_info['practice']}",
            "  • 尝试自己编一道类似的题目并解答",
            "",
            "🎯 复习建议：",
            "  • 回顾课本相关章节的例题",
            "  • 整理错题本，标注错误类型",
            "  • 隔天再做一遍，检验掌握程度",
        ]
        return suggestions


# ============================================================
# 命令行接口
# ============================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="作业引导 · 思路启发 · 自主解题",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --subject math --grade 7 --question "解方程 2x+3=11"
  python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode step
  python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode hint
  python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode review
  python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode analyze
  python run.py --subject math --grade 7 --question "解方程 2x+3=11" --mode next
  python run.py --selftest
        """
    )

    parser.add_argument(
        "--subject",
        choices=["math", "physics", "chemistry"],
        default="math",
        help="学科类型 (默认: math)",
    )
    parser.add_argument(
        "--grade",
        type=int,
        default=7,
        help="年级 (默认: 7)",
    )
    parser.add_argument(
        "--question",
        type=str,
        help="题目内容",
    )
    parser.add_argument(
        "--mode",
        choices=["step", "hint", "review", "analyze", "next"],
        default="step",
        help="引导模式 (默认: step)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检",
    )

    return parser.parse_args()


def run_guide(args) -> int:
    """执行业务逻辑"""
    try:
        guide = HomeworkGuide(args.subject, args.grade, args.question)

        mode_handlers = {
            "step": guide.decompose,
            "hint": guide.hint,
            "review": guide.review,
            "analyze": guide.analyze,
            "next": guide.suggest_next,
        }

        handler = mode_handlers.get(args.mode)
        if not handler:
            print(f"错误: 未知模式 '{args.mode}'", file=sys.stderr)
            return 1

        result = handler()
        print("\n".join(result))
        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"发生未预期的错误: {e}", file=sys.stderr)
        return 1


def selftest() -> int:
    """自检函数：验证核心功能是否正常"""
    print("开始自检...")

    test_cases = [
        ("math", 7, "解方程 2x+3=11", "step"),
        ("math", 7, "解方程 2x+3=11", "hint"),
        ("math", 7, "解方程 2x+3=11", "review"),
        ("math", 7, "解方程 2x+3=11", "analyze"),
        ("math", 7, "解方程 2x+3=11", "next"),
        ("physics", 9, "汽车2小时行驶120km，求平均速度", "step"),
        ("chemistry", 10, "写出氢气燃烧的化学方程式", "review"),
    ]

    for subject, grade, question, mode in test_cases:
        try:
            guide = HomeworkGuide(subject, grade, question)
            handler = {
                "step": guide.decompose,
                "hint": guide.hint,
                "review": guide.review,
                "analyze": guide.analyze,
                "next": guide.suggest_next,
            }[mode]
            result = handler()
            assert len(result) > 0, f"空结果: {subject}/{mode}"
            print(f"  ✓ {subject}/{grade}年级/{mode}: {len(result)} 行输出")
        except Exception as e:
            print(f"  ✗ 测试失败: {subject}/{grade}/{mode}: {e}")
            return 1

    # 测试错误处理
    try:
        HomeworkGuide("math", 7, "")
        print("  ✗ 空题目应该报错")
        return 1
    except ValueError:
        print("  ✓ 空题目正确报错")

    try:
        HomeworkGuide("invalid_subject", 7, "test")
        print("  ✗ 无效学科应该报错")
        return 1
    except ValueError:
        print("  ✓ 无效学科正确报错")

    print("自检通过！")
    return 0


def main():
    """主入口"""
    args = parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.question:
        print("错误: 必须提供 --question 参数", file=sys.stderr)
        print("示例: python run.py --subject math --grade 7 --question '解方程 2x+3=11'", file=sys.stderr)
        sys.exit(1)

    sys.exit(run_guide(args))


if __name__ == "__main__":
    main()
