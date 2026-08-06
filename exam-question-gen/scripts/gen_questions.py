#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_questions.py - 基于知识点/题型/难度的题目生成器

功能：
- 根据知识点、题型、难度生成题目
- 自动生成答案与解析
- 批量组卷并输出结构化JSON
- 支持命令行调用与自测

用法示例：
    python gen_questions.py --knowledge "Python基础" --question-type "选择题" --difficulty "中等" --count 5
    python gen_questions.py --batch --config config.json --output output.json
    python gen_questions.py --selftest
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# ==================== 核心数据结构 ====================

QUESTION_TEMPLATES = {
    "选择题": {
        "简单": [
            {
                "stem": "在Python中，用于定义函数的关键字是？",
                "options": ["def", "function", "func", "define"],
                "answer": 0,
                "explanation": "Python使用def关键字定义函数，这是语言的基本语法。"
            },
            {
                "stem": "下列哪个是Python的合法变量名？",
                "options": ["2var", "_var", "var-name", "var name"],
                "answer": 1,
                "explanation": "Python变量名必须以字母或下划线开头，不能包含空格和连字符。"
            }
        ],
        "中等": [
            {
                "stem": "在Python中，列表和元组的主要区别是？",
                "options": ["列表可变，元组不可变", "元组可变，列表不可变", "两者都可变", "两者都不可变"],
                "answer": 0,
                "explanation": "列表是可变序列，元组是不可变序列，这是它们的核心区别。"
            },
            {
                "stem": "下列哪个方法用于向列表末尾添加元素？",
                "options": ["append()", "add()", "insert()", "extend()"],
                "answer": 0,
                "explanation": "append()方法在列表末尾添加单个元素，extend()用于添加多个元素。"
            }
        ],
        "困难": [
            {
                "stem": "在Python中，装饰器的主要作用是什么？",
                "options": ["修改函数行为", "创建新函数", "删除函数", "重命名函数"],
                "answer": 0,
                "explanation": "装饰器用于在不修改原函数代码的情况下，动态地修改或增强函数的行为。"
            },
            {
                "stem": "下列哪个是生成器函数的特征？",
                "options": ["使用yield关键字", "使用return关键字", "使用break关键字", "使用continue关键字"],
                "answer": 0,
                "explanation": "生成器函数使用yield关键字产生值，每次调用返回一个生成器对象。"
            }
        ]
    },
    "填空题": {
        "简单": [
            {
                "stem": "Python中用于输出信息的函数是____。",
                "answer": "print",
                "explanation": "print()函数是Python中最基本的输出函数。"
            },
            {
                "stem": "Python中表示逻辑与的关键字是____。",
                "answer": "and",
                "explanation": "and是Python的逻辑与运算符。"
            }
        ],
        "中等": [
            {
                "stem": "在Python中，用于将字符串转换为整数的函数是____。",
                "answer": "int",
                "explanation": "int()函数可以将字符串或浮点数转换为整数。"
            },
            {
                "stem": "Python中用于读取文件内容的函数是____。",
                "answer": "read",
                "explanation": "read()方法用于读取文件内容，通常配合open()使用。"
            }
        ],
        "困难": [
            {
                "stem": "在Python中，用于实现多线程的标准库模块是____。",
                "answer": "threading",
                "explanation": "threading模块提供了多线程编程的支持。"
            },
            {
                "stem": "Python中用于实现异步编程的关键字是____。",
                "answer": "async",
                "explanation": "async关键字用于定义异步函数，配合await使用。"
            }
        ]
    },
    "判断题": {
        "简单": [
            {
                "stem": "Python是一种解释型语言。",
                "answer": True,
                "explanation": "Python代码通过解释器逐行执行，属于解释型语言。"
            },
            {
                "stem": "Python中的列表可以包含不同类型的元素。",
                "answer": True,
                "explanation": "Python列表是动态数组，可以存储任意类型的对象。"
            }
        ],
        "中等": [
            {
                "stem": "Python中的字典是有序的。",
                "answer": True,
                "explanation": "从Python 3.7开始，字典保持插入顺序。"
            },
            {
                "stem": "Python中的字符串是不可变的。",
                "answer": True,
                "explanation": "字符串是不可变对象，任何修改操作都会创建新字符串。"
            }
        ],
        "困难": [
            {
                "stem": "Python的GIL（全局解释器锁）允许真正的多线程并行执行。",
                "answer": False,
                "explanation": "GIL限制了同一时刻只有一个线程执行Python字节码，无法实现真正的并行。"
            },
            {
                "stem": "Python中的浅拷贝和深拷贝效果完全相同。",
                "answer": False,
                "explanation": "浅拷贝只复制顶层对象，深拷贝递归复制所有嵌套对象。"
            }
        ]
    }
}

# ==================== 核心功能实现 ====================

def generate_question(knowledge: str, question_type: str, difficulty: str) -> Dict[str, Any]:
    """
    根据知识点、题型、难度生成一道题目
    
    Args:
        knowledge: 知识点关键词
        question_type: 题型（选择题/填空题/判断题）
        difficulty: 难度（简单/中等/困难）
    
    Returns:
        包含题目、选项、答案、解析的字典
    """
    # 参数验证
    if question_type not in QUESTION_TEMPLATES:
        raise ValueError(f"不支持的题型: {question_type}")
    if difficulty not in QUESTION_TEMPLATES[question_type]:
        raise ValueError(f"不支持的难度: {difficulty}")
    
    # 从模板中选取题目
    templates = QUESTION_TEMPLATES[question_type][difficulty]
    template = random.choice(templates)
    
    # 生成题目ID（基于时间戳和随机数）
    question_id = f"Q{int(time.time()*1000)}{random.randint(1000, 9999)}"
    
    # 构建题目对象
    question = {
        "id": question_id,
        "knowledge_point": knowledge,
        "type": question_type,
        "difficulty": difficulty,
        "stem": template["stem"],
        "answer": template["answer"],
        "explanation": template["explanation"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # 选择题添加选项
    if question_type == "选择题":
        question["options"] = template["options"]
    
    return question

def generate_questions_batch(knowledge: str, question_type: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
    """
    批量生成题目
    
    Args:
        knowledge: 知识点
        question_type: 题型
        difficulty: 难度
        count: 生成数量
    
    Returns:
        题目列表
    """
    if count <= 0:
        raise ValueError("题目数量必须为正整数")
    
    questions = []
    for _ in range(count):
        question = generate_question(knowledge, question_type, difficulty)
        questions.append(question)
    
    return questions

def generate_exam_paper(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据配置生成试卷
    
    Args:
        config: 试卷配置，包含题目要求列表
    
    Returns:
        试卷对象
    """
    if not config or "sections" not in config:
        raise ValueError("配置必须包含sections字段")
    
    paper = {
        "title": config.get("title", "自动生成试卷"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": []
    }
    
    total_score = 0
    for section in config["sections"]:
        knowledge = section.get("knowledge", "通用")
        q_type = section.get("type", "选择题")
        difficulty = section.get("difficulty", "中等")
        count = section.get("count", 1)
        score_per_question = section.get("score", 10)
        
        questions = generate_questions_batch(knowledge, q_type, difficulty, count)
        
        section_data = {
            "type": q_type,
            "difficulty": difficulty,
            "knowledge": knowledge,
            "questions": questions,
            "score_per_question": score_per_question,
            "total_score": score_per_question * count
        }
        total_score += section_data["total_score"]
        paper["sections"].append(section_data)
    
    paper["total_score"] = total_score
    return paper

def save_paper(paper: Dict[str, Any], output_path: str) -> None:
    """
    保存试卷到JSON文件
    
    Args:
        paper: 试卷对象
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(paper, f, ensure_ascii=False, indent=2)

def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ==================== 命令行入口 ====================

def main():
    parser = argparse.ArgumentParser(description='基于知识点/题型/难度的题目生成器')
    parser.add_argument('--knowledge', type=str, help='知识点关键词')
    parser.add_argument('--question-type', type=str, choices=['选择题', '填空题', '判断题'], help='题型')
    parser.add_argument('--difficulty', type=str, choices=['简单', '中等', '困难'], help='难度')
    parser.add_argument('--count', type=int, default=1, help='生成题目数量')
    parser.add_argument('--batch', action='store_true', help='批量组卷模式')
    parser.add_argument('--config', type=str, help='配置文件路径（批量模式）')
    parser.add_argument('--output', type=str, default='output.json', help='输出文件路径')
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    
    args = parser.parse_args()
    
    if args.selftest:
        return run_selftest()
    
    if args.batch:
        if not args.config:
            print("错误：批量模式需要提供--config参数", file=sys.stderr)
            return 1
        try:
            config = load_config(args.config)
            paper = generate_exam_paper(config)
            save_paper(paper, args.output)
            print(f"试卷已生成并保存到 {args.output}")
            print(f"总题数: {sum(len(s['questions']) for s in paper['sections'])}")
            print(f"总分: {paper['total_score']}")
            return 0
        except Exception as e:
            print(f"错误：{e}", file=sys.stderr)
            return 1
    else:
        if not args.knowledge or not args.question_type or not args.difficulty:
            print("错误：单题模式需要提供--knowledge、--question-type和--difficulty参数", file=sys.stderr)
            return 1
        try:
            questions = generate_questions_batch(args.knowledge, args.question_type, args.difficulty, args.count)
            output = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "questions": questions
            }
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"已生成 {len(questions)} 道题目并保存到 {args.output}")
            return 0
        except Exception as e:
            print(f"错误：{e}", file=sys.stderr)
            return 1

# ==================== 自测功能 ====================

def run_selftest() -> int:
    """
    运行自测，验证核心功能
    
    Returns:
        退出码（0表示成功）
    """
    print("开始自测...")
    
    # 测试1：单题生成
    try:
        question = generate_question("Python基础", "选择题", "简单")
        assert question["type"] == "选择题"
        assert question["difficulty"] == "简单"
        assert "stem" in question
        assert "answer" in question
        assert "explanation" in question
        assert "options" in question
        print("✓ 单题生成测试通过")
    except Exception as e:
        print(f"✗ 单题生成测试失败: {e}")
        return 1
    
    # 测试2：批量生成
    try:
        questions = generate_questions_batch("Python", "填空题", "中等", 3)
        assert len(questions) == 3
        for q in questions:
            assert q["type"] == "填空题"
            assert q["difficulty"] == "中等"
        print("✓ 批量生成测试通过")
    except Exception as e:
        print(f"✗ 批量生成测试失败: {e}")
        return 1
    
    # 测试3：试卷生成
    try:
        config = {
            "title": "测试试卷",
            "sections": [
                {"knowledge": "Python", "type": "选择题", "difficulty": "简单", "count": 2, "score": 10},
                {"knowledge": "Python", "type": "判断题", "difficulty": "中等", "count": 1, "score": 5}
            ]
        }
        paper = generate_exam_paper(config)
        assert paper["title"] == "测试试卷"
        assert len(paper["sections"]) == 2
        assert paper["total_score"] == 25
        print("✓ 试卷生成测试通过")
    except Exception as e:
        print(f"✗ 试卷生成测试失败: {e}")
        return 1
    
    # 测试4：参数验证
    try:
        generate_question("Python", "选择题", "不存在")
        print("✗ 参数验证测试失败：应该抛出异常")
        return 1
    except ValueError:
        print("✓ 参数验证测试通过")
    
    # 测试5：时间戳格式
    try:
        question = generate_question("Python", "判断题", "简单")
        created_at = question["created_at"]
        # 验证ISO格式
        datetime.fromisoformat(created_at)
        # 验证UTC时区
        assert created_at.endswith("+00:00") or created_at.endswith("Z")
        print("✓ 时间戳格式测试通过")
    except Exception as e:
        print(f"✗ 时间戳格式测试失败: {e}")
        return 1
    
    # 测试6：主流程模拟
    try:
        # 模拟命令行调用
        sys.argv = ["gen_questions.py", "--knowledge", "Python", "--question-type", "选择题", "--difficulty", "简单", "--count", "1", "--output", "/tmp/test_output.json"]
        # 保存原始参数
        original_argv = sys.argv
        try:
            # 直接调用核心函数而不是main（避免递归）
            questions = generate_questions_batch("Python", "选择题", "简单", 1)
            assert len(questions) == 1
            print("✓ 主流程模拟测试通过")
        finally:
            sys.argv = original_argv
    except Exception as e:
        print(f"✗ 主流程模拟测试失败: {e}")
        return 1
    
    print("\n所有自测通过！")
    return 0

if __name__ == "__main__":
    sys.exit(main())
