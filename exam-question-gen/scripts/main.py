#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组卷出题技能 - 独立实现脚本

功能:
    根据知识点、难度、题型配置，批量生成带解析的练习题。
    支持三种题型: 单选题、填空题、简答题。

用法示例:
    python main.py --help
    python main.py --selftest
    python main.py --knowledge "勾股定理,三角函数" --difficulty 中等 --count 5
"""

import argparse
import json
import random
import sys
from typing import Any, Dict, List, Optional

# 错误码定义
E001 = "E001: 参数错误 - 知识点列表为空"
E002 = "E002: 参数错误 - 题目数量必须为正整数"
E003 = "E003: 参数错误 - 难度系数必须在 1-5 之间"
E004 = "E004: 参数错误 - 题型配置无效"
E005 = "E005: 运行时错误 - 内置题库为空"
E006 = "E006: 运行时错误 - 生成题目失败"
E007 = "E007: 运行时错误 - JSON 序列化失败"
E008 = "E008: 运行时错误 - 未知题型"
E009 = "E009: 运行时错误 - 知识点未找到匹配模板"
E010 = "E010: 运行时错误 - 内部状态异常"

# 难度映射: 用户输入 -> 数值等级
DIFFICULTY_MAP = {
    "简单": 1,
    "容易": 1,
    "中等": 3,
    "困难": 5,
    "较难": 4,
}

# 题型枚举
QUESTION_TYPE_SINGLE = "single_choice"
QUESTION_TYPE_FILL = "fill_blank"
QUESTION_TYPE_SHORT = "short_answer"


class QuestionGenerator:
    """核心题目生成器（基于内置模板库）"""

    def __init__(self) -> None:
        """初始化生成器，加载内置模板库"""
        # 内置模板库: 每个知识点包含三种题型的生成模板
        # 模板为函数，接收难度等级，返回题目字典
        self._knowledge_templates: Dict[str, Dict[str, Any]] = {
            "勾股定理": {
                QUESTION_TYPE_SINGLE: self._gen_pythagoras_single,
                QUESTION_TYPE_FILL: self._gen_pythagoras_fill,
                QUESTION_TYPE_SHORT: self._gen_pythagoras_short,
            },
            "三角函数": {
                QUESTION_TYPE_SINGLE: self._gen_trig_single,
                QUESTION_TYPE_FILL: self._gen_trig_fill,
                QUESTION_TYPE_SHORT: self._gen_trig_short,
            },
            "一元二次方程": {
                QUESTION_TYPE_SINGLE: self._gen_quadratic_single,
                QUESTION_TYPE_FILL: self._gen_quadratic_fill,
                QUESTION_TYPE_SHORT: self._gen_quadratic_short,
            },
        }

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def generate(
        self,
        knowledge_points: List[str],
        question_types: List[str],
        difficulty: int = 3,
        count_per_type: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        生成题目列表

        参数:
            knowledge_points: 知识点名称列表
            question_types: 题型列表 (可选值: single_choice, fill_blank, short_answer)
            difficulty: 难度等级 1-5
            count_per_type: 每种题型生成的题数

        返回:
            题目字典列表
        """
        # 参数校验
        if not knowledge_points:
            raise ValueError(E001)
        if count_per_type <= 0:
            raise ValueError(E002)
        if difficulty < 1 or difficulty > 5:
            raise ValueError(E003)
        if not question_types:
            raise ValueError(E004)

        results: List[Dict[str, Any]] = []

        for kp in knowledge_points:
            # 检查知识点是否有模板
            if kp not in self._knowledge_templates:
                raise RuntimeError(f"{E009} - 知识点: {kp}")

            kp_templates = self._knowledge_templates[kp]

            for qtype in question_types:
                if qtype not in kp_templates:
                    raise ValueError(f"{E004} - 不支持的题型: {qtype}")

                generator_fn = kp_templates[qtype]

                for _ in range(count_per_type):
                    try:
                        question = generator_fn(difficulty)
                        question["knowledge_point"] = kp
                        question["type"] = qtype
                        results.append(question)
                    except Exception as exc:
                        raise RuntimeError(f"{E006} - {exc}") from exc

        if not results:
            raise RuntimeError(E006)

        return results

    # ------------------------------------------------------------------
    # 内置题目模板（仅用于自测/演示，实际使用时可扩展）
    # ------------------------------------------------------------------
    @staticmethod
    def _gen_pythagoras_single(difficulty: int) -> Dict[str, Any]:
        """勾股定理 - 单选题模板"""
        return {
            "question": "直角三角形的两条直角边分别为 3 和 4，斜边长度为？",
            "options": ["5", "6", "7", "8"],
            "answer": "A",
            "explanation": "根据勾股定理 a² + b² = c²，3² + 4² = 9 + 16 = 25，c = 5。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_pythagoras_fill(difficulty: int) -> Dict[str, Any]:
        """勾股定理 - 填空题模板"""
        return {
            "question": "直角三角形的两条直角边分别为 6 和 8，斜边长度为 ____。",
            "answer": "10",
            "explanation": "根据勾股定理 a² + b² = c²，6² + 8² = 36 + 64 = 100，c = 10。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_pythagoras_short(difficulty: int) -> Dict[str, Any]:
        """勾股定理 - 简答题模板"""
        return {
            "question": "请简述勾股定理的内容，并举例说明其应用。",
            "answer": "勾股定理：直角三角形两条直角边的平方和等于斜边的平方。例如，直角边为 3 和 4 时，斜边为 5。",
            "explanation": "勾股定理是数学中最重要的定理之一，广泛应用于几何计算、工程测量等领域。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_trig_single(difficulty: int) -> Dict[str, Any]:
        """三角函数 - 单选题模板"""
        return {
            "question": "sin 30° 的值是多少？",
            "options": ["1/2", "√3/2", "1", "√2/2"],
            "answer": "A",
            "explanation": "sin 30° = 1/2，这是三角函数的基本值。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_trig_fill(difficulty: int) -> Dict[str, Any]:
        """三角函数 - 填空题模板"""
        return {
            "question": "cos 60° 的值是 ____。",
            "answer": "1/2",
            "explanation": "cos 60° = 1/2，这是三角函数的基本值。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_trig_short(difficulty: int) -> Dict[str, Any]:
        """三角函数 - 简答题模板"""
        return {
            "question": "请解释正弦函数和余弦函数在直角三角形中的定义。",
            "answer": "在直角三角形中，sin θ = 对边/斜边，cos θ = 邻边/斜边。",
            "explanation": "正弦和余弦是描述角度与边长关系的核心三角函数。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_quadratic_single(difficulty: int) -> Dict[str, Any]:
        """一元二次方程 - 单选题模板"""
        return {
            "question": "方程 x² - 5x + 6 = 0 的解是？",
            "options": ["x=2 或 x=3", "x=1 或 x=6", "x=-2 或 x=-3", "x=-1 或 x=-6"],
            "answer": "A",
            "explanation": "因式分解得 (x-2)(x-3)=0，所以 x=2 或 x=3。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_quadratic_fill(difficulty: int) -> Dict[str, Any]:
        """一元二次方程 - 填空题模板"""
        return {
            "question": "方程 x² - 4 = 0 的解是 x = ____。",
            "answer": "±2",
            "explanation": "x² = 4，所以 x = ±2。",
            "difficulty": difficulty,
        }

    @staticmethod
    def _gen_quadratic_short(difficulty: int) -> Dict[str, Any]:
        """一元二次方程 - 简答题模板"""
        return {
            "question": "请简述求解一元二次方程 ax² + bx + c = 0 的求根公式。",
            "answer": "x = [-b ± √(b²-4ac)] / (2a)，当判别式 b²-4ac ≥ 0 时有实数解。",
            "explanation": "求根公式是一元二次方程的标准解法，适用于所有情况。",
            "difficulty": difficulty,
        }


def parse_difficulty(value: str) -> int:
    """解析难度字符串为数值等级"""
    normalized = value.strip()
    if normalized.isdigit():
        level = int(normalized)
        if 1 <= level <= 5:
            return level
        raise ValueError(E003)

    if normalized in DIFFICULTY_MAP:
        return DIFFICULTY_MAP[normalized]

    raise ValueError(f"{E003} - 无法识别的难度: {value}")


def parse_question_types(type_str: str) -> List[str]:
    """解析题型字符串为类型列表"""
    type_map = {
        "选择": QUESTION_TYPE_SINGLE,
        "单选": QUESTION_TYPE_SINGLE,
        "single": QUESTION_TYPE_SINGLE,
        "填空": QUESTION_TYPE_FILL,
        "fill": QUESTION_TYPE_FILL,
        "简答": QUESTION_TYPE_SHORT,
        "short": QUESTION_TYPE_SHORT,
    }

    # 支持用逗号、空格、顿号分隔
    parts = [p.strip() for p in type_str.replace("，", ",").replace("、", ",").replace(" ", ",").split(",") if p.strip()]

    result = []
    for part in parts:
        if part in type_map:
            result.append(type_map[part])
        else:
            raise ValueError(f"{E004} - 未知题型: {part}")

    if not result:
        raise ValueError(E004)

    return result


def run_selftest() -> None:
    """内置自测函数，验证核心逻辑"""
    print("开始自测...")

    generator = QuestionGenerator()

    # 测试用例 1: 基本生成
    try:
        questions = generator.generate(
            knowledge_points=["勾股定理"],
            question_types=[QUESTION_TYPE_SINGLE],
            difficulty=3,
            count_per_type=1,
        )
        assert len(questions) == 1, "测试1失败: 应生成1道题"
        assert questions[0]["type"] == QUESTION_TYPE_SINGLE, "测试1失败: 题型错误"
        assert questions[0]["knowledge_point"] == "勾股定理", "测试1失败: 知识点错误"
        assert "answer" in questions[0], "测试1失败: 缺少答案"
        assert "explanation" in questions[0], "测试1失败: 缺少解析"
        print("测试1通过: 基本生成")
    except Exception as exc:
        print(f"测试1失败: {exc}")
        sys.exit(1)

    # 测试用例 2: 多知识点多题型
    try:
        questions = generator.generate(
            knowledge_points=["勾股定理", "三角函数"],
            question_types=[QUESTION_TYPE_SINGLE, QUESTION_TYPE_FILL],
            difficulty=4,
            count_per_type=2,
        )
        assert len(questions) == 8, f"测试2失败: 应生成8道题，实际 {len(questions)}"
        types = set(q["type"] for q in questions)
        assert types == {QUESTION_TYPE_SINGLE, QUESTION_TYPE_FILL}, "测试2失败: 题型种类错误"
        print("测试2通过: 多知识点多题型")
    except Exception as exc:
        print(f"测试2失败: {exc}")
        sys.exit(1)

    # 测试用例 3: 难度解析
    try:
        assert parse_difficulty("中等") == 3, "测试3失败: 中等应映射为3"
        assert parse_difficulty("5") == 5, "测试3失败: 5应映射为5"
        print("测试3通过: 难度解析")
    except Exception as exc:
        print(f"测试3失败: {exc}")
        sys.exit(1)

    # 测试用例 4: 异常处理
    try:
        generator.generate(
            knowledge_points=["不存在的知识点"],
            question_types=[QUESTION_TYPE_SINGLE],
        )
        print("测试4失败: 应抛出异常")
        sys.exit(1)
    except RuntimeError:
        print("测试4通过: 异常处理")

    # 测试用例 5: JSON 序列化
    try:
        questions = generator.generate(
            knowledge_points=["一元二次方程"],
            question_types=[QUESTION_TYPE_SHORT],
            difficulty=2,
            count_per_type=1,
        )
        json_str = json.dumps(questions, ensure_ascii=False, indent=2)
        assert json_str, "测试5失败: JSON 序列化为空"
        print("测试5通过: JSON 序列化")
    except Exception as exc:
        print(f"测试5失败: {exc}")
        sys.exit(1)

    print("全部自测通过 ✓")


def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="组卷出题工具 - 按知识点与难度批量生成带解析的练习题",
        epilog="示例: python main.py --knowledge '勾股定理,三角函数' --difficulty 中等 --count 2 --types 单选,填空",
    )

    parser.add_argument(
        "--knowledge",
        type=str,
        help="知识点列表，用逗号分隔，例如: '勾股定理,三角函数'",
    )
    parser.add_argument(
        "--difficulty",
        type=str,
        default="中等",
        help="难度: 简单/中等/困难 或 1-5 的数字",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="每种题型生成的题目数量 (正整数)",
    )
    parser.add_argument(
        "--types",
        type=str,
        default="单选",
        help="题型列表，用逗号分隔，可选: 单选,填空,简答",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径 (JSON 格式)，不指定则输出到控制台",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测并退出",
    )

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        run_selftest()
        return

    # 参数校验
    if not args.knowledge:
        print(f"错误: {E001}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    try:
        # 解析参数
        knowledge_points = [kp.strip() for kp in args.knowledge.split(",") if kp.strip()]
        if not knowledge_points:
            raise ValueError(E001)

        difficulty = parse_difficulty(args.difficulty)
        question_types = parse_question_types(args.types)

        if args.count <= 0:
            raise ValueError(E002)

        # 生成题目
        generator = QuestionGenerator()
        questions = generator.generate(
            knowledge_points=knowledge_points,
            question_types=question_types,
            difficulty=difficulty,
            count_per_type=args.count,
        )

        # 构建输出
        output_data = {
            "meta": {
                "version": "1.0.1",
                "knowledge_points": knowledge_points,
                "difficulty": difficulty,
                "total_count": len(questions),
            },
            "questions": questions,
        }

        # 输出
        json_str = json.dumps(output_data, ensure_ascii=False, indent=2)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"已生成 {len(questions)} 道题目，保存至: {args.output}")
        else:
            print(json_str)

    except ValueError as exc:
        print(f"参数错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"运行时错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"未知错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
