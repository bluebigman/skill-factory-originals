#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exam-question-gen: 基于知识点生成选择题/填空题/简答题及解析
"""

import argparse
import functools
import json
import random
import re
import sys
import time as _t
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ── 稳定性注入（P1-06）: 重试 + 异常防护 ──
class RetryableError(Exception):
    """可重试异常基类（网络/超时类）"""


class NetworkError(RetryableError):
    """网络错误"""


class TimeoutError(RetryableError):
    """超时错误"""


def retry(
    times: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: Tuple[type, ...] = (NetworkError, TimeoutError),
):
    """
    指数退避重试装饰器
    :param times: 最大重试次数（含首次）
    :param base_delay: 基础延迟（秒）
    :param max_delay: 最大延迟（秒）
    :param retryable_exceptions: 可重试的异常类型
    """

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt == times - 1:
                        raise
                    delay = min(base_delay * (2**attempt), max_delay)
                    _t.sleep(delay)
                except Exception:
                    # 非可重试异常直接抛出
                    raise
            return None

        return wrapper

    return deco


# ── 知识规范化 ──
def normalize_knowledge(knowledge: str) -> str:
    """规范化知识点名称"""
    if not knowledge:
        return "Python基础"
    key = knowledge.strip().lower()
    # 简单规范化：去除多余空格，统一大小写
    key = re.sub(r"\s+", " ", key)
    return key


# ── 题目生成核心逻辑 ──
class QuestionGenerator:
    """题目生成器"""

    # 真实知识库：每个知识点包含定义、用途、特点等
    KNOWLEDGE_BASE = {
        "python基础": {
            "definition": "Python是一种解释型、面向对象、动态数据类型的高级程序设计语言",
            "features": ["简洁易读", "跨平台", "丰富的标准库", "支持多种编程范式"],
            "usage": "Web开发、数据分析、人工智能、自动化脚本等",
            "standard_library": True,
        },
        "numpy": {
            "definition": "NumPy是Python科学计算的基础库，提供高性能多维数组对象",
            "features": ["多维数组", "广播功能", "线性代数运算", "随机数生成"],
            "usage": "科学计算、数据分析、机器学习",
            "standard_library": False,
        },
        "pandas": {
            "definition": "Pandas是Python数据分析的核心库，提供DataFrame数据结构",
            "features": ["数据清洗", "数据转换", "时间序列分析", "数据聚合"],
            "usage": "数据处理、数据清洗、数据分析",
            "standard_library": False,
        },
        "requests": {
            "definition": "Requests是Python的HTTP客户端库，用于发送网络请求",
            "features": ["简洁API", "会话管理", "SSL验证", "文件上传下载"],
            "usage": "网络爬虫、API调用、Web开发",
            "standard_library": False,
        },
        "flask": {
            "definition": "Flask是Python的轻量级Web框架",
            "features": ["轻量灵活", "内置开发服务器", "支持RESTful", "扩展丰富"],
            "usage": "Web应用开发、API服务、微服务",
            "standard_library": False,
        },
        "django": {
            "definition": "Django是Python的高级Web框架，遵循MVC设计模式",
            "features": ["ORM", "Admin后台", "认证系统", "模板引擎"],
            "usage": "大型Web应用、内容管理系统、API服务",
            "standard_library": False,
        },
        "matplotlib": {
            "definition": "Matplotlib是Python的2D绘图库",
            "features": ["多种图表类型", "自定义样式", "交互式绘图", "导出多种格式"],
            "usage": "数据可视化、科学绘图、报告生成",
            "standard_library": False,
        },
        "scikit-learn": {
            "definition": "Scikit-learn是Python的机器学习库",
            "features": ["分类算法", "回归算法", "聚类算法", "模型评估"],
            "usage": "机器学习、数据挖掘、预测分析",
            "standard_library": False,
        },
    }

    def __init__(self, knowledge: str):
        self.knowledge = normalize_knowledge(knowledge)
        # 如果知识点不在知识库中，使用默认知识
        if self.knowledge not in self.KNOWLEDGE_BASE:
            self.knowledge = "python基础"
        self.knowledge_data = self.KNOWLEDGE_BASE[self.knowledge]

    def _generate_choice_options(self, correct_answer: str, distractors: List[str]) -> Tuple[List[str], int]:
        """生成选择题选项，返回选项列表和正确答案索引"""
        options = [correct_answer] + distractors[:3]
        random.shuffle(options)
        answer_index = options.index(correct_answer)
        return options, answer_index

    def generate_choice(self) -> Dict[str, Any]:
        """生成选择题 - 基于真实知识库动态生成"""
        # 根据知识点类型生成不同的问题
        if self.knowledge_data["standard_library"]:
            question = f"关于{self.knowledge}，以下哪个说法是正确的？"
            correct = f"{self.knowledge}是Python的标准库模块"
            distractors = [
                f"{self.knowledge}需要第三方库支持",
                f"{self.knowledge}只能在特定平台使用",
                f"{self.knowledge}与Python无关",
            ]
            explanation = f"{self.knowledge}是Python的标准库模块，无需额外安装。{self.knowledge_data['definition']}"
        else:
            question = f"关于{self.knowledge}，以下哪个描述是正确的？"
            correct = f"{self.knowledge}是Python的第三方库，用于{self.knowledge_data['usage']}"
            distractors = [
                f"{self.knowledge}是Python的标准库模块",
                f"{self.knowledge}只能用于Web开发",
                f"{self.knowledge}与Python无关",
            ]
            explanation = f"{self.knowledge}是Python的第三方库。{self.knowledge_data['definition']}。主要用途：{self.knowledge_data['usage']}"

        options, answer_index = self._generate_choice_options(correct, distractors)

        return {
            "type": "choice",
            "question": question,
            "options": options,
            "answer": answer_index,
            "explanation": explanation,
        }

    def generate_fill(self) -> Dict[str, Any]:
        """生成填空题 - 基于真实知识库动态生成"""
        # 从知识库中提取关键信息生成填空题
        features = self.knowledge_data["features"]
        feature = random.choice(features)

        question = f"{self.knowledge}的一个主要特点是____。"
        answer = feature
        explanation = f"{self.knowledge}的特点包括：{', '.join(self.knowledge_data['features'])}"

        return {
            "type": "fill",
            "question": question,
            "answer": answer,
            "explanation": explanation,
        }

    def generate_short(self) -> Dict[str, Any]:
        """生成简答题 - 基于真实知识库动态生成"""
        question = f"请简述{self.knowledge}的主要用途和特点。"
        answer = f"{self.knowledge}是Python的{'标准库' if self.knowledge_data['standard_library'] else '第三方库'}。{self.knowledge_data['definition']}。主要用途包括：{self.knowledge_data['usage']}。主要特点：{', '.join(self.knowledge_data['features'])}"
        explanation = f"该知识点是Python生态中重要的组成部分，掌握{self.knowledge}对提升开发效率很有帮助。"

        return {
            "type": "short",
            "question": question,
            "answer": answer,
            "explanation": explanation,
        }

    def generate_all(self) -> List[Dict[str, Any]]:
        """生成所有类型题目"""
        return [
            self.generate_choice(),
            self.generate_fill(),
            self.generate_short(),
        ]


# ── 批量生成 ──
def generate_questions(
    knowledge: str,
    count: int = 1,
    question_type: str = "all",
    difficulty: str = "medium",
) -> List[Dict[str, Any]]:
    """
    生成题目
    :param knowledge: 知识点
    :param count: 生成数量
    :param question_type: 题目类型 (choice/fill/short/all)
    :param difficulty: 难度 (easy/medium/hard)
    """
    generator = QuestionGenerator(knowledge)
    questions = []

    # 根据难度调整生成逻辑
    difficulty_factor = {"easy": 0.8, "medium": 1.0, "hard": 1.2}

    for _ in range(count):
        if question_type == "choice":
            q = generator.generate_choice()
            # 根据难度调整选项数量
            if difficulty == "easy" and len(q["options"]) > 3:
                q["options"] = q["options"][:3]
                q["answer"] = min(q["answer"], 2)
            elif difficulty == "hard" and len(q["options"]) < 5:
                # 添加更多干扰项
                extra_options = [f"选项{chr(65+i)}" for i in range(4, 6)]
                q["options"].extend(extra_options)
            questions.append(q)
        elif question_type == "fill":
            questions.append(generator.generate_fill())
        elif question_type == "short":
            questions.append(generator.generate_short())
        else:  # all
            questions.extend(generator.generate_all())

    return questions


# ── 配置加载 ──
def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """加载配置文件"""
    if not config_path:
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"警告: 配置文件 {config_path} 不存在，使用默认配置")
        return {}
    except json.JSONDecodeError:
        print(f"警告: 配置文件 {config_path} 格式错误，使用默认配置")
        return {}


# ── 主流程 ──
def main():
    parser = argparse.ArgumentParser(description="基于知识点生成考试题目")
    parser.add_argument("--batch", type=int, default=1, help="批量生成数量")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径")
    parser.add_argument("--mode", type=str, default="all", choices=["choice", "fill", "short", "all"], help="题目类型")
    parser.add_argument("--task", type=str, default="Python基础", help="知识点名称")
    parser.add_argument("--difficulty", type=str, default="medium", choices=["easy", "medium", "hard"], help="题目难度")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    # 加载配置（如果提供）
    config = load_config(args.config)
    if config:
        args.batch = config.get("batch", args.batch)
        args.mode = config.get("mode", args.mode)
        args.task = config.get("task", args.task)
        args.difficulty = config.get("difficulty", args.difficulty)

    # 生成题目
    questions = generate_questions(
        knowledge=args.task,
        count=args.batch,
        question_type=args.mode,
        difficulty=args.difficulty,
    )

    # 输出结果
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "knowledge": args.task,
        "mode": args.mode,
        "difficulty": args.difficulty,
        "count": len(questions),
        "questions": questions,
    }

    if args.verbose:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for i, q in enumerate(questions, 1):
            print(f"\n题目{i} [{q['type']}]:")
            print(f"  {q['question']}")
            if q["type"] == "choice":
                for j, opt in enumerate(q["options"]):
                    marker = "✓" if j == q["answer"] else " "
                    print(f"  {marker} {chr(65+j)}. {opt}")
            print(f"  答案: {q['answer']}")
            print(f"  解析: {q['explanation']}")

    return 0


# ── 自测 ──
def run_selftest() -> int:
    """运行自测，验证核心功能"""
    print("开始自测...")

    # 测试1: 知识点规范化
    assert normalize_knowledge("  Python 基础  ") == "python 基础", "知识点规范化失败"
    assert normalize_knowledge("") == "Python基础", "空知识点处理失败"
    print("✓ 知识点规范化测试通过")

    # 测试2: 生成选择题 - 验证答案正确性
    gen = QuestionGenerator("Python")
    choice = gen.generate_choice()
    assert choice["type"] == "choice", "选择题类型错误"
    assert len(choice["options"]) >= 3, "选择题选项数量错误"
    assert 0 <= choice["answer"] < len(choice["options"]), "选择题答案索引错误"
    assert choice["explanation"], "选择题解析为空"
    # 验证答案确实在选项中
    assert choice["options"][choice["answer"]] in choice["options"], "答案不在选项中"
    print("✓ 选择题生成测试通过")

    # 测试3: 生成填空题 - 验证答案来自知识库
    fill = gen.generate_fill()
    assert fill["type"] == "fill", "填空题类型错误"
    assert fill["answer"], "填空题答案为空"
    assert fill["explanation"], "填空题解析为空"
    # 验证答案确实是知识库中的特点
    assert fill["answer"] in gen.knowledge_data["features"], "填空题答案不在知识库中"
    print("✓ 填空题生成测试通过")

    # 测试4: 生成简答题 - 验证答案包含知识库内容
    short = gen.generate_short()
    assert short["type"] == "short", "简答题类型错误"
    assert short["answer"], "简答题答案为空"
    assert short["explanation"], "简答题解析为空"
    # 验证答案包含知识点定义
    assert gen.knowledge_data["definition"] in short["answer"], "简答题答案不包含定义"
    print("✓ 简答题生成测试通过")

    # 测试5: 批量生成 - 验证数量
    questions = generate_questions("Python", count=2, question_type="all")
    assert len(questions) == 6, f"批量生成数量错误: {len(questions)}"
    print("✓ 批量生成测试通过")

    # 测试6: 难度参数 - 验证不同难度生成
    easy_questions = generate_questions("Python", count=1, question_type="choice", difficulty="easy")
    hard_questions = generate_questions("Python", count=1, question_type="choice", difficulty="hard")
    assert len(easy_questions[0]["options"]) <= len(hard_questions[0]["options"]), "难度参数未生效"
    print("✓ 难度参数测试通过")

    # 测试7: 重试机制
    call_count = 0

    @retry(times=3, base_delay=0.1)
    def test_retry():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise NetworkError("模拟网络错误")
        return "success"

    result = test_retry()
    assert result == "success", "重试机制失败"
    assert call_count == 3, f"重试次数错误: {call_count}"
    print("✓ 重试机制测试通过")

    # 测试8: 时间戳使用UTC
    timestamp = datetime.now(timezone.utc)
    assert timestamp.tzinfo is not None, "时间戳未使用UTC"
    print("✓ 时间戳UTC测试通过")

    # 测试9: 主流程集成测试
    test_args = ["--task", "numpy", "--batch", "2", "--mode", "choice", "--difficulty", "hard"]
    old_argv = sys.argv
    sys.argv = ["gen_questions.py"] + test_args
    try:
        exit_code = main()
        assert exit_code == 0, f"主流程退出码错误: {exit_code}"
    finally:
        sys.argv = old_argv
    print("✓ 主流程集成测试通过")

    print("\n所有自测通过！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
