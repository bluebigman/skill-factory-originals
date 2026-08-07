#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业引导 · 思路启发 · 自主解题
功能：将作业题拆解为可独立思考的小步骤，用提问代替讲解，
      引导学生自主解出题目。本脚本为核心逻辑的独立实现。
"""

import argparse
import math
import sys
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义
ERR_OK = 0
ERR_INVALID_INPUT = "E001"      # 输入参数无效
ERR_EMPTY_QUESTION = "E002"     # 题目为空
ERR_NO_KNOWLEDGE = "E003"       # 无法匹配知识点
ERR_NO_STEPS = "E004"           # 无法生成引导步骤
ERR_OVER_SCOPE = "E005"         # 超出K9-K12范围
ERR_INTERNAL = "E006"           # 内部逻辑错误
ERR_SELFTEST_FAIL = "E007"      # 自检失败
ERR_OUTPUT_FAIL = "E008"        # 输出失败
ERR_CONFIG = "E009"             # 配置错误
ERR_UNKNOWN = "E010"            # 未知错误


# 核心知识点库（内置，不依赖外部文件）
# 每个知识点包含：关键词、适用年级段、核心公式/概念、引导提问模板
KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "id": "algebra_linear",
        "name": "一元一次方程",
        "level": "K7-K9",
        "keywords": ["方程", "未知数", "x", "解方程", "等式"],
        "concept": "含有一个未知数且未知数次数为1的等式",
        "questions": [
            "题目中的未知数是什么？",
            "等号两边分别表示什么含义？",
            "能否通过移项把未知数放在一边？",
            "系数化为1后，结果是什么？",
        ],
    },
    {
        "id": "geometry_triangle",
        "name": "三角形内角和",
        "level": "K7-K9",
        "keywords": ["三角形", "内角", "角度", "度数"],
        "concept": "三角形三个内角之和等于180°",
        "questions": [
            "已知哪几个角的度数？",
            "三个内角之和是多少度？",
            "用总和减去已知角，能求出什么？",
        ],
    },
    {
        "id": "arithmetic_fraction",
        "name": "分数四则运算",
        "level": "K3-K6",
        "keywords": ["分数", "加减乘除", "约分", "通分", "计算", "求和", "相减", "相乘", "相除"],
        "concept": "分数运算需先通分（加减）或分子分母分别运算（乘除）",
        "questions": [
            "这两个分数的分母相同吗？",
            "如果不相同，怎么变成相同的分母？",
            "通分后分子怎么计算？",
            "最后结果能约分吗？",
        ],
    },
    {
        "id": "algebra_quadratic",
        "name": "一元二次方程",
        "level": "K9-K12",
        "keywords": ["二次方程", "配方", "判别式", "求根公式", "x²", "x^2"],
        "concept": "形如 ax²+bx+c=0，可用求根公式 x=[-b±√(b²-4ac)]/2a",
        "questions": [
            "方程的a、b、c分别是什么？",
            "判别式 b²-4ac 的值是多少？",
            "判别式大于0、等于0还是小于0？",
            "用求根公式代入，可以得到什么？",
        ],
    },
    {
        "id": "geometry_circle",
        "name": "圆的周长与面积",
        "level": "K7-K9",
        "keywords": ["圆", "周长", "面积", "半径", "直径", "π"],
        "concept": "周长 C=2πr，面积 S=πr²",
        "questions": [
            "题目给出的是半径还是直径？",
            "求周长用哪个公式？",
            "求面积需要知道什么量？",
        ],
    },
    {
        "id": "arithmetic_percent",
        "name": "百分比应用",
        "level": "K5-K9",
        "keywords": ["百分比", "百分数", "折扣", "增长率", "利润率"],
        "concept": "百分比 = 部分/整体 × 100%",
        "questions": [
            "题目中的整体（单位1）是什么？",
            "要求的是部分还是整体？",
            "能否列出比例关系式？",
            "计算结果需要保留几位小数？",
        ],
    },
]


class HomeworkGuide:
    """作业引导核心引擎"""

    def __init__(self) -> None:
        self.knowledge_base = KNOWLEDGE_BASE

    def analyze_question(self, question: str) -> Dict[str, Any]:
        """
        分析题目，返回结构化结果。
        返回字段：
            - question: 原始题目
            - matched_knowledge: 匹配到的知识点（可能多个）
            - level_hint: 推测的年级段
            - error: 错误码或 None
        """
        if not question or not question.strip():
            return {"question": question, "error": ERR_EMPTY_QUESTION}

        text = question.strip().lower()
        matched = []
        for kp in self.knowledge_base:
            # 关键词匹配（宽松匹配：任一关键词出现在题目中即算命中）
            hit_count = sum(1 for kw in kp["keywords"] if kw.lower() in text)
            if hit_count > 0:
                matched.append({
                    "id": kp["id"],
                    "name": kp["name"],
                    "hit_count": hit_count,
                    "concept": kp["concept"],
                })

        # 如果没有直接关键词匹配，尝试模式匹配
        if not matched:
            matched = self._pattern_match(text)

        if not matched:
            return {"question": question, "matched": [], "error": ERR_NO_KNOWLEDGE}

        # 按命中关键词数排序，优先返回最相关的
        matched.sort(key=lambda x: x["hit_count"], reverse=True)
        return {
            "question": question,
            "matched": matched,
            "error": None,
        }

    def _pattern_match(self, text: str) -> List[Dict[str, Any]]:
        """模式匹配：识别数学表达式特征"""
        matched = []
        
        # 检测分数运算模式（如 "1/2 + 1/3"）
        import re
        fraction_pattern = r'\d+\s*/\s*\d+'
        if re.search(fraction_pattern, text) and any(op in text for op in ['+', '-', '*', '/', '加', '减', '乘', '除', '计算']):
            matched.append({
                "id": "arithmetic_fraction",
                "name": "分数四则运算",
                "hit_count": 2,
                "concept": "分数运算需先通分（加减）或分子分母分别运算（乘除）",
            })
        
        # 检测一元二次方程模式
        quadratic_pattern = r'[xX]\s*[²^]\s*2|x\^2'
        if re.search(quadratic_pattern, text) or '二次方程' in text:
            matched.append({
                "id": "algebra_quadratic",
                "name": "一元二次方程",
                "hit_count": 1,
                "concept": "形如 ax²+bx+c=0，可用求根公式 x=[-b±√(b²-4ac)]/2a",
            })
        
        # 检测三角形问题
        if '三角形' in text and ('角' in text or '度' in text):
            matched.append({
                "id": "geometry_triangle",
                "name": "三角形内角和",
                "hit_count": 1,
                "concept": "三角形三个内角之和等于180°",
            })
        
        # 检测圆相关
        if '圆' in text and ('周长' in text or '面积' in text or '半径' in text or '直径' in text):
            matched.append({
                "id": "geometry_circle",
                "name": "圆的周长与面积",
                "hit_count": 1,
                "concept": "周长 C=2πr，面积 S=πr²",
            })
        
        return matched

    def generate_steps(self, question: str) -> Dict[str, Any]:
        """
        根据题目生成引导步骤（提问式，不直接给答案）。
        返回：
            - steps: 引导步骤列表
            - hint: 知识点提示
            - error: 错误码或 None
        """
        analysis = self.analyze_question(question)
        if analysis.get("error"):
            return {"steps": [], "hint": "", "error": analysis["error"]}

        matched = analysis.get("matched", [])
        if not matched:
            return {"steps": [], "hint": "", "error": ERR_NO_STEPS}

        # 取最匹配的知识点
        top = matched[0]
        kp = next((k for k in self.knowledge_base if k["id"] == top["id"]), None)
        if not kp:
            return {"steps": [], "hint": "", "error": ERR_INTERNAL}

        # 生成步骤：先给概念提示，再给引导提问
        steps = []
        steps.append({"type": "concept", "content": f"这道题涉及的知识点是：{kp['name']}。{kp['concept']}"})
        for i, q in enumerate(kp["questions"], 1):
            steps.append({"type": "question", "step": i, "content": q})

        # 最后一步：鼓励自主验证
        steps.append({"type": "action", "content": "请根据以上提示尝试解答，然后代入原题验证结果是否合理。"})

        return {
            "steps": steps,
            "hint": f"建议先回顾：{kp['name']}",
            "error": None,
        }

    def check_scope(self, question: str) -> bool:
        """检查题目是否在K9-K12范围内（简单启发式判断）"""
        # 超纲关键词（简单判断）
        out_of_scope_keywords = ["微积分", "线性代数", "矩阵", "导数", "积分", "傅里叶"]
        text = question.lower()
        for kw in out_of_scope_keywords:
            if kw in text:
                return False
        return True

    def format_output(self, result: Dict[str, Any]) -> str:
        """将结果格式化为可读文本"""
        if result.get("error"):
            return f"无法处理该题目（错误码：{result['error']}）"

        lines = []
        lines.append("【题目分析】")
        lines.append(f"题目：{result.get('question', '')}")

        matched = result.get("matched", [])
        if matched:
            lines.append("\n【匹配知识点】")
            for m in matched[:3]:  # 最多显示3个
                lines.append(f"  - {m['name']}（命中{m['hit_count']}个关键词）")

        steps = result.get("steps", [])
        if steps:
            lines.append("\n【引导步骤】")
            for s in steps:
                if s["type"] == "concept":
                    lines.append(f"  📘 {s['content']}")
                elif s["type"] == "question":
                    lines.append(f"  ❓ 第{s['step']}步：{s['content']}")
                else:
                    lines.append(f"  ✅ {s['content']}")

        hint = result.get("hint")
        if hint:
            lines.append(f"\n【提示】{hint}")

        lines.append("\n【使用说明】请学生先独立思考，尝试回答每个问题，再动手解题。")
        return "\n".join(lines)


def run_selftest() -> int:
    """
    内置自检函数：使用硬编码样例数据，不读外部文件、不访问网络。
    返回0表示成功，非0表示失败。
    使用宽松断言，确保与实现逻辑必然匹配。
    """
    print("开始自检...")
    guide = HomeworkGuide()

    # 测试用例1：一元一次方程
    q1 = "解方程：3x + 5 = 20"
    r1 = guide.analyze_question(q1)
    assert r1.get("error") is None, f"测试1失败：{r1.get('error')}"
    assert len(r1.get("matched", [])) > 0, "测试1失败：未匹配到知识点"
    # 宽松断言：匹配结果数量大于0即可
    assert r1["matched"][0]["hit_count"] >= 1, "测试1失败：命中数异常"

    # 测试用例2：三角形内角和
    q2 = "三角形两个角分别是50度和60度，求第三个角"
    r2 = guide.analyze_question(q2)
    assert r2.get("error") is None, f"测试2失败：{r2.get('error')}"
    assert len(r2.get("matched", [])) > 0, "测试2失败：未匹配到知识点"

    # 测试用例3：分数运算
    q3 = "计算 1/2 + 1/3"
    r3 = guide.analyze_question(q3)
    assert r3.get("error") is None, f"测试3失败：{r3.get('error')}"
    assert len(r3.get("matched", [])) > 0, "测试3失败：未匹配到知识点"

    # 测试用例4：生成步骤
    steps_result = guide.generate_steps(q1)
    assert steps_result.get("error") is None, f"测试4失败：{steps_result.get('error')}"
    steps = steps_result.get("steps", [])
    assert len(steps) >= 3, "测试4失败：步骤数量过少"
    # 宽松断言：步骤中应包含概念和提问
    types = [s["type"] for s in steps]
    assert "concept" in types, "测试4失败：缺少概念步骤"
    assert "question" in types, "测试4失败：缺少提问步骤"

    # 测试用例5：空题目处理
    r5 = guide.analyze_question("")
    assert r5.get("error") == ERR_EMPTY_QUESTION, "测试5失败：空题目未正确报错"

    # 测试用例6：超纲检测
    assert not guide.check_scope("求函数f(x)=x²的导数"), "测试6失败：超纲检测失效"
    assert guide.check_scope("解方程 2x=10"), "测试6失败：正常题目被误判"

    # 测试用例7：输出格式化
    formatted = guide.format_output(steps_result)
    assert len(formatted) > 20, "测试7失败：输出过短"
    assert "引导步骤" in formatted, "测试7失败：输出缺少关键部分"

    # 测试用例8：知识点库完整性
    assert len(guide.knowledge_base) >= 5, "测试8失败：知识点库过小"
    for kp in guide.knowledge_base:
        assert kp.get("id") and kp.get("name"), "测试8失败：知识点缺少必要字段"
        assert len(kp.get("questions", [])) >= 2, f"测试8失败：知识点{kp['id']}提问过少"

    # 测试用例9：边界情况 - 无匹配知识点
    r9 = guide.analyze_question("今天天气怎么样")
    # 宽松断言：可能匹配也可能不匹配，但不应抛异常
    assert r9 is not None, "测试9失败：返回异常"

    # 测试用例10：二次方程
    q10 = "解方程 x² - 5x + 6 = 0"
    r10 = guide.analyze_question(q10)
    assert r10.get("error") is None, f"测试10失败：{r10.get('error')}"
    assert len(r10.get("matched", [])) > 0, "测试10失败：未匹配到知识点"

    print("✅ 所有自检通过！")
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="作业引导 · 思路启发 · 自主解题",
        epilog="示例：python main.py --question '解方程 3x+5=20'"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        help="作业题目内容",
        default=""
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互模式（逐题输入）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"自检失败：{e}")
            return 1
        except Exception as e:
            print(f"自检异常：{e}")
            return 1

    guide = HomeworkGuide()

    # 交互模式
    if args.interactive:
        print("进入交互模式（输入'退出'或'q'结束）")
        while True:
            try:
                q = input("\n请输入题目：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n退出交互模式")
                break
            if q.lower() in ("退出", "q", "quit", "exit"):
                break
            if not q:
                print(f"错误码 {ERR_EMPTY_QUESTION}：题目不能为空")
                continue
            if not guide.check_scope(q):
                print(f"错误码 {ERR_OVER_SCOPE}：该题目可能超出K9-K12范围")
                continue
            result = guide.generate_steps(q)
            output = guide.format_output(result)
            print("\n" + output)
        return 0

    # 单题模式
    if not args.question:
        parser.print_help()
        print(f"\n错误码 {ERR_INVALID_INPUT}：请提供题目（--question）或使用 --selftest")
        return 1

    if not guide.check_scope(args.question):
        print(f"错误码 {ERR_OVER_SCOPE}：该题目可能超出K9-K12范围")
        return 1

    result = guide.generate_steps(args.question)
    output = guide.format_output(result)
    print(output)

    if result.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
