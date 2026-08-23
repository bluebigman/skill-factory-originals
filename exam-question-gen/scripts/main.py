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
import math
import random
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

dry_run = False  # v3.268 模块级 dry-run 标志

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

# 知识点知识库 - 真实数据，用于动态生成题目
KNOWLEDGE_BASE = {
    "勾股定理": {
        "description": "直角三角形两条直角边的平方和等于斜边的平方",
        "formula": "a² + b² = c²",
        "examples": [
            {"sides": (3, 4), "hypotenuse": 5},
            {"sides": (6, 8), "hypotenuse": 10},
            {"sides": (5, 12), "hypotenuse": 13},
            {"sides": (8, 15), "hypotenuse": 17},
            {"sides": (7, 24), "hypotenuse": 25},
        ],
        "applications": ["测量", "建筑", "导航", "物理"],
    },
    "三角函数": {
        "description": "三角函数是角度与边长比值的函数关系",
        "formula": "sin θ = 对边/斜边, cos θ = 邻边/斜边, tan θ = 对边/邻边",
        "special_angles": {
            "0°": {"sin": 0, "cos": 1, "tan": 0},
            "30°": {"sin": "1/2", "cos": "√3/2", "tan": "√3/3"},
            "45°": {"sin": "√2/2", "cos": "√2/2", "tan": 1},
            "60°": {"sin": "√3/2", "cos": "1/2", "tan": "√3"},
            "90°": {"sin": 1, "cos": 0, "tan": "不存在"},
        },
        "applications": ["物理", "工程", "导航"],
    },
    "一元二次方程": {
        "description": "形如 ax² + bx + c = 0 的方程",
        "formula": "x = [-b ± √(b²-4ac)] / (2a)",
        "examples": [
            {"a": 1, "b": -5, "c": 6, "roots": [2, 3]},
            {"a": 1, "b": -4, "c": 0, "roots": [0, 4]},
            {"a": 1, "b": 0, "c": -4, "roots": [-2, 2]},
            {"a": 2, "b": -7, "c": 3, "roots": [0.5, 3]},
            {"a": 1, "b": -6, "c": 9, "roots": [3, 3]},
        ],
        "applications": ["物理", "经济", "工程"],
    },
}


class QuestionGenerator:
    """核心题目生成器（基于真实知识库动态生成）"""

    def __init__(self) -> None:
        """初始化生成器，加载知识库"""
        self._knowledge_base = KNOWLEDGE_BASE

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
            # 检查知识点是否有知识库数据
            if kp not in self._knowledge_base:
                raise RuntimeError(f"{E009} - 知识点: {kp}")

            kp_data = self._knowledge_base[kp]

            for qtype in question_types:
                if qtype not in [QUESTION_TYPE_SINGLE, QUESTION_TYPE_FILL, QUESTION_TYPE_SHORT]:
                    raise ValueError(f"{E004} - 不支持的题型: {qtype}")

                for i in range(count_per_type):
                    try:
                        question = self._generate_question(kp, kp_data, qtype, difficulty, i)
                        question["knowledge_point"] = kp
                        question["type"] = qtype
                        question["generated_at"] = datetime.now(timezone.utc).isoformat()
                        results.append(question)
                    except Exception as exc:
                        raise RuntimeError(f"{E006} - {exc}") from exc

        if not results:
            raise RuntimeError(E006)

        return results

    # ------------------------------------------------------------------
    # 动态题目生成方法
    # ------------------------------------------------------------------
    def _generate_question(
        self, kp: str, kp_data: Dict[str, Any], qtype: str, difficulty: int, seed: int
    ) -> Dict[str, Any]:
        """根据知识点数据动态生成题目"""
        if qtype == QUESTION_TYPE_SINGLE:
            return self._generate_single_choice(kp, kp_data, difficulty, seed)
        elif qtype == QUESTION_TYPE_FILL:
            return self._generate_fill_blank(kp, kp_data, difficulty, seed)
        elif qtype == QUESTION_TYPE_SHORT:
            return self._generate_short_answer(kp, kp_data, difficulty, seed)
        else:
            raise ValueError(E008)

    def _generate_single_choice(self, kp: str, kp_data: Dict[str, Any], difficulty: int, seed: int) -> Dict[str, Any]:
        """动态生成单选题"""
        rng = random.Random(seed * 31 + difficulty * 7)

        if kp == "勾股定理":
            # 从知识库中随机选择一组勾股数
            example = rng.choice(kp_data["examples"])
            a, b = example["sides"]
            c = example["hypotenuse"]

            # 生成错误选项
            wrong_options = set()
            while len(wrong_options) < 3:
                wrong = c + rng.choice([-2, -1, 1, 2, 3])
                if wrong > 0 and wrong != c:
                    wrong_options.add(wrong)
            wrong_options = list(wrong_options)

            # 构建选项列表
            options = [str(c)] + [str(w) for w in wrong_options]
            rng.shuffle(options)

            # 计算正确答案索引
            correct_index = options.index(str(c))
            correct_letter = chr(65 + correct_index)  # A, B, C, D

            question_text = f"直角三角形的两条直角边分别为 {a} 和 {b}，斜边长度为？"

            return {
                "question": question_text,
                "options": options,
                "answer": correct_letter,
                "answer_index": correct_index,
                "explanation": f"根据勾股定理 a² + b² = c²，{a}² + {b}² = {a*a} + {b*b} = {a*a+b*b}，c = √{a*a+b*b} = {c}。",
                "difficulty": difficulty,
            }

        elif kp == "三角函数":
            # 从特殊角度中随机选择
            angle = rng.choice(list(kp_data["special_angles"].keys()))
            values = kp_data["special_angles"][angle]
            func = rng.choice(["sin", "cos", "tan"])
            correct_value = values[func]

            # 生成错误选项
            all_values = []
            for v in kp_data["special_angles"].values():
                all_values.extend([v["sin"], v["cos"], v["tan"]])
            all_values = [v for v in all_values if v != correct_value and v != "不存在"]

            wrong_options = rng.sample(all_values, min(3, len(all_values)))
            while len(wrong_options) < 3:
                wrong_options.append(f"值{len(wrong_options)+1}")

            # 构建选项列表
            options = [str(correct_value)] + [str(w) for w in wrong_options[:3]]
            rng.shuffle(options)

            correct_index = options.index(str(correct_value))
            correct_letter = chr(65 + correct_index)

            return {
                "question": f"{func} {angle} 的值是多少？",
                "options": options,
                "answer": correct_letter,
                "answer_index": correct_index,
                "explanation": f"根据三角函数特殊值表，{func} {angle} = {correct_value}。",
                "difficulty": difficulty,
            }

        elif kp == "一元二次方程":
            # 从知识库中随机选择方程
            example = rng.choice(kp_data["examples"])
            a, b, c = example["a"], example["b"], example["c"]
            roots = example["roots"]

            # 生成错误选项
            wrong_roots = []
            for r in roots:
                wrong_roots.append(r + rng.choice([-1, 1, 2]))
            wrong_options = [f"x={wrong_roots[0]} 或 x={wrong_roots[1]}"]

            # 构建选项
            correct_str = f"x={roots[0]} 或 x={roots[1]}"
            options = [correct_str] + wrong_options
            while len(options) < 4:
                options.append(f"x={rng.randint(-5, 5)} 或 x={rng.randint(-5, 5)}")
            rng.shuffle(options)

            correct_index = options.index(correct_str)
            correct_letter = chr(65 + correct_index)

            return {
                "question": f"方程 {a}x² + {b}x + {c} = 0 的解是？",
                "options": options,
                "answer": correct_letter,
                "answer_index": correct_index,
                "explanation": f"因式分解得 (x-{roots[0]})(x-{roots[1]}) = 0，所以 x={roots[0]} 或 x={roots[1]}。",
                "difficulty": difficulty,
            }

        raise ValueError(E008)

    def _generate_fill_blank(self, kp: str, kp_data: Dict[str, Any], difficulty: int, seed: int) -> Dict[str, Any]:
        """动态生成填空题"""
        rng = random.Random(seed * 17 + difficulty * 5)

        if kp == "勾股定理":
            example = rng.choice(kp_data["examples"])
            a, b = example["sides"]
            c = example["hypotenuse"]

            return {
                "question": f"直角三角形的两条直角边分别为 {a} 和 {b}，斜边长度为 ____。",
                "answer": str(c),
                "explanation": f"根据勾股定理 a² + b² = c²，{a}² + {b}² = {a*a} + {b*b} = {a*a+b*b}，c = √{a*a+b*b} = {c}。",
                "difficulty": difficulty,
            }

        elif kp == "三角函数":
            angle = rng.choice(list(kp_data["special_angles"].keys()))
            values = kp_data["special_angles"][angle]
            func = rng.choice(["sin", "cos", "tan"])
            correct_value = values[func]

            return {
                "question": f"{func} {angle} 的值是 ____。",
                "answer": str(correct_value),
                "explanation": f"根据三角函数特殊值表，{func} {angle} = {correct_value}。",
                "difficulty": difficulty,
            }

        elif kp == "一元二次方程":
            example = rng.choice(kp_data["examples"])
            a, b, c = example["a"], example["b"], example["c"]
            roots = example["roots"]

            if roots[0] == roots[1]:
                answer = f"x={roots[0]}"
            else:
                answer = f"x={roots[0]} 或 x={roots[1]}"

            return {
                "question": f"方程 {a}x² + {b}x + {c} = 0 的解是 ____。",
                "answer": answer,
                "explanation": f"因式分解得 (x-{roots[0]})(x-{roots[1]}) = 0，所以 {answer}。",
                "difficulty": difficulty,
            }

        raise ValueError(E008)

    def _generate_short_answer(self, kp: str, kp_data: Dict[str, Any], difficulty: int, seed: int) -> Dict[str, Any]:
        """动态生成简答题"""
        rng = random.Random(seed * 13 + difficulty * 3)

        if kp == "勾股定理":
            example = rng.choice(kp_data["examples"])
            a, b = example["sides"]
            c = example["hypotenuse"]
            app = rng.choice(kp_data["applications"])

            return {
                "question": f"请简述勾股定理的内容，并举例说明其在{app}中的应用。",
                "answer": f"勾股定理：直角三角形两条直角边的平方和等于斜边的平方。例如，直角边为 {a} 和 {b} 时，斜边为 {c}。在{app}中，可用于计算距离和测量。",
                "explanation": f"勾股定理是数学中最重要的定理之一，公式为 {kp_data['formula']}，广泛应用于{', '.join(kp_data['applications'])}等领域。",
                "difficulty": difficulty,
            }

        elif kp == "三角函数":
            app = rng.choice(kp_data["applications"])

            return {
                "question": f"请解释正弦函数和余弦函数在直角三角形中的定义，并说明其在{app}中的应用。",
                "answer": f"在直角三角形中，sin θ = 对边/斜边，cos θ = 邻边/斜边。在{app}中，三角函数用于计算角度和距离。",
                "explanation": f"三角函数是描述角度与边长关系的核心函数，公式为 {kp_data['formula']}。",
                "difficulty": difficulty,
            }

        elif kp == "一元二次方程":
            example = rng.choice(kp_data["examples"])
            a, b, c = example["a"], example["b"], example["c"]
            roots = example["roots"]
            app = rng.choice(kp_data["applications"])

            return {
                "question": f"请简述求解一元二次方程 ax² + bx + c = 0 的求根公式，并解方程 {a}x² + {b}x + {c} = 0。",
                "answer": f"求根公式为 x = [-b ± √(b²-4ac)] / (2a)。对于方程 {a}x² + {b}x + {c} = 0，解得 x={roots[0]} 或 x={roots[1]}。",
                "explanation": f"求根公式是一元二次方程的标准解法，公式为 {kp_data['formula']}，在{app}中有广泛应用。",
                "difficulty": difficulty,
            }

        raise ValueError(E008)

    def _validate_question(self, question: Dict[str, Any]) -> bool:
        """验证题目答案的正确性"""
        if question["type"] == QUESTION_TYPE_SINGLE:
            # 验证单选题答案索引
            if "answer_index" not in question:
                return False
            idx = question["answer_index"]
            if idx < 0 or idx >= len(question["options"]):
                return False
            # 验证答案字母与索引一致
            expected_letter = chr(65 + idx)
            if question["answer"] != expected_letter:
                return False
        elif question["type"] == QUESTION_TYPE_FILL:
            # 验证填空题答案非空
            if not question["answer"]:
                return False
        elif question["type"] == QUESTION_TYPE_SHORT:
            # 验证简答题答案非空
            if not question["answer"]:
                return False
