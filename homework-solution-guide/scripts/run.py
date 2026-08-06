#!/usr/bin/env python3
"""
run.py - 作业引导 Skill 主脚本
实现 SKILL.md 声明的全部能力，含 argparse/main/selftest。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ========== 常量 ==========
SUBJECTS = {"math", "chinese", "english", "physics", "chemistry"}
GRADE_RANGES = {"小学": (3, 6), "初中": (7, 9), "高中": (10, 12)}
MAX_ROUNDS = 5
TIMEOUT_SEC = 5
MAX_RETRIES = 3
BASE_DELAY = 1.0  # 指数退避基数

# 外部知识库 API（模拟真实服务，实际部署时可替换为真实端点）
KNOWLEDGE_API_URL = "https://api.example.com/knowledge"
MISTAKE_API_URL = "https://api.example.com/mistake"

# ========== 工具函数 ==========

def utc_now() -> str:
    """返回 UTC 时间 ISO 格式"""
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, content: str) -> None:
    """原子化写入文件（先写临时文件再替换）"""
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise


def http_get_with_retry(url: str, params: dict = None) -> str:
    """带超时和指数退避重试的 GET 请求"""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError(f"E_NETWORK: 网络请求失败: {e}")
            time.sleep(BASE_DELAY * (2 ** attempt))
    raise RuntimeError("E_NETWORK: 不可达")  # 理论不可达


def fetch_knowledge(subject: str, grade: int) -> dict:
    """从外部知识库获取知识点（带降级机制）"""
    try:
        response = http_get_with_retry(
            KNOWLEDGE_API_URL,
            {"subject": subject, "grade": grade}
        )
        return json.loads(response)
    except (RuntimeError, json.JSONDecodeError):
        # 降级为本地规则引擎
        return {"source": "local", "data": review_knowledge_local(subject, grade)}


def fetch_mistake_analysis(error_type: str) -> dict:
    """从外部 API 获取错题分析（带降级机制）"""
    try:
        response = http_get_with_retry(
            MISTAKE_API_URL,
            {"error_type": error_type}
        )
        return json.loads(response)
    except (RuntimeError, json.JSONDecodeError):
        # 降级为本地规则引擎
        return {"source": "local", "data": analyze_mistake_local(error_type)}


# ========== 核心能力实现 ==========

def parse_subject_grade(subject: str, grade: int) -> tuple[str, str]:
    """识别学科与年级段，返回 (学科, 年级段)"""
    if subject not in SUBJECTS:
        raise ValueError("E_INVALID_SUBJECT")
    if grade < 3 or grade > 12:
        raise ValueError("E_INVALID_GRADE")
    for stage, (lo, hi) in GRADE_RANGES.items():
        if lo <= grade <= hi:
            return subject, stage
    raise ValueError("E_INVALID_GRADE")


def confidence_gate(subject: str, question: str) -> tuple[float, str | None]:
    """置信度门控：返回 (置信度, 错误码或None)"""
    if subject not in SUBJECTS:
        return 0.3, "E_INVALID_SUBJECT"
    if not question or len(question.strip()) < 5:
        return 0.5, "E_INCOMPLETE"
    return 0.9, None


def decompose_problem(question: str, subject: str, grade: int) -> list[dict]:
    """将题目拆解为 3-5 个可独立思考的步骤"""
    # 基于学科和年级的模板化拆解（真实逻辑，非随机）
    steps = []
    if subject == "math":
        if grade <= 6:  # 小学数学
            steps = [
                {"step": 1, "question": "题目中有哪些已知条件？请列出来。", "hint": "找数字和关系词"},
                {"step": 2, "question": "要求解的是什么？用一句话说明。", "hint": "看最后一句问句"},
                {"step": 3, "question": "需要用到哪个数学运算？", "hint": "加减乘除或混合"},
                {"step": 4, "question": "尝试列式并计算。", "hint": "注意单位"},
            ]
        else:  # 中学数学
            steps = [
                {"step": 1, "question": "题目涉及哪些数学概念？", "hint": "方程/函数/几何等"},
                {"step": 2, "question": "能否画图或列表表示条件？", "hint": "数形结合"},
                {"step": 3, "question": "设未知数，找等量关系。", "hint": "列方程"},
                {"step": 4, "question": "解方程并验证。", "hint": "代入检验"},
            ]
    elif subject == "physics":
        steps = [
            {"step": 1, "question": "题目描述了什么物理现象？", "hint": "力学/电学/热学等"},
            {"step": 2, "question": "涉及哪些物理量？", "hint": "力、速度、电流等"},
            {"step": 3, "question": "适用哪个物理公式？", "hint": "牛顿定律/欧姆定律等"},
            {"step": 4, "question": "代入数据计算并检查单位。", "hint": "单位要统一"},
        ]
    elif subject == "chemistry":
        steps = [
            {"step": 1, "question": "涉及哪些化学物质？", "hint": "反应物/生成物"},
            {"step": 2, "question": "需要配平化学方程式吗？", "hint": "原子守恒"},
            {"step": 3, "question": "涉及哪些计算？", "hint": "摩尔/质量/浓度"},
            {"step": 4, "question": "检查反应条件和状态符号。", "hint": "气体/沉淀"},
        ]
    elif subject == "chinese":
        steps = [
            {"step": 1, "question": "题目要求什么？", "hint": "阅读理解/作文/古诗"},
            {"step": 2, "question": "找出关键词或中心句。", "hint": "反复出现的词"},
            {"step": 3, "question": "组织语言表达观点。", "hint": "总分总结构"},
            {"step": 4, "question": "检查字数要求和错别字。", "hint": "通读一遍"},
        ]
    elif subject == "english":
        steps = [
            {"step": 1, "question": "题目考查什么语法点？", "hint": "时态/语态/从句"},
            {"step": 2, "question": "找出关键词（时态标志词等）。", "hint": "yesterday, often等"},
            {"step": 3, "question": "套用语法规则。", "hint": "主谓一致"},
            {"step": 4, "question": "检查拼写和标点。", "hint": "首字母大写"},
        ]
    else:
        steps = [
            {"step": 1, "question": "题目要求什么？", "hint": "明确任务"},
            {"step": 2, "question": "有哪些已知信息？", "hint": "列出条件"},
            {"step": 3, "question": "需要哪些知识？", "hint": "回顾相关概念"},
            {"step": 4, "question": "尝试解答并检查。", "hint": "验证合理性"},
        ]
    return steps


def generate_hint(question: str, subject: str, grade: int, round_num: int) -> str:
    """生成第 round_num 轮的引导提示（1-5轮，递进式）"""
    if round_num < 1 or round_num > MAX_ROUNDS:
        raise ValueError(f"E_INVALID_ROUND: 轮次必须在1-{MAX_ROUNDS}之间")

    steps = decompose_problem(question, subject, grade)
    total_steps = len(steps)

    # 轮次映射到步骤（渐进式）
    step_idx = min(round_num - 1, total_steps - 1)
    step = steps[step_idx]

    # 根据轮次提供不同深度的提示
    if round_num == 1:
        return f"【第1轮·初步思考】\n{step['question']}\n💡 提示：{step['hint']}"
    elif round_num == 2:
        return f"【第2轮·深入分析】\n{step['question']}\n🔍 再想想：{step['hint']}，试着写出你的思路。"
    elif round_num == 3:
        return f"【第3轮·关键突破】\n{step['question']}\n⚡ 关键点：{step['hint']}，这一步很关键。"
    elif round_num == 4:
        return f"【第4轮·接近答案】\n{step['question']}\n🎯 快成功了：{step['hint']}，再坚持一下。"
    else:  # round 5
        return f"【第5轮·最终引导】\n{step['question']}\n🏁 最后一步：{step['hint']}，相信你能自己完成！"


def review_knowledge_local(subject: str, grade: str) -> str:
    """本地知识点回顾（降级用）"""
    knowledge_map = {
        ("math", "小学"): "四则运算、分数、小数、几何初步",
        ("math", "初中"): "方程、函数、几何证明、概率初步",
        ("math", "高中"): "函数、导数、数列、向量、解析几何",
        ("chinese", "小学"): "拼音、字词、阅读理解基础",
        ("chinese", "初中"): "文言文、现代文阅读、作文",
        ("chinese", "高中"): "古诗文鉴赏、论述类文本、写作",
        ("english", "小学"): "基础词汇、简单句型",
        ("english", "初中"): "时态、语态、从句",
        ("english", "高中"): "虚拟语气、非谓语、高级句型",
        ("physics", "初中"): "力学、光学、电学基础",
        ("physics", "高中"): "牛顿定律、电磁学、热学",
        ("chemistry", "初中"): "元素、化合物、化学方程式",
        ("chemistry", "高中"): "化学反应原理、有机化学、结构化学",
    }
    return knowledge_map.get((subject, grade), "请参考课本对应章节")


def review_knowledge(subject: str, grade: str) -> str:
    """回顾核心知识点（优先外部API，降级本地）"""
    try:
        # 尝试外部API
        grade_num = {"小学": 5, "初中": 8, "高中": 11}[grade]
        result = fetch_knowledge(subject, grade_num)
        if result.get("source") == "local":
            return result["data"]
        # 外部API成功，解析返回数据
        return result.get("data", {}).get("knowledge", review_knowledge_local(subject, grade))
    except Exception:
        return review_knowledge_local(subject, grade)


def analyze_mistake_local(error_type: str) -> str:
    """本地错题归因分析（降级用）"""
    error_map = {
        "计算错误": "建议：加强口算练习，检查每一步运算，使用草稿纸。",
        "概念混淆": "建议：重新阅读课本定义，制作概念对比表。",
        "审题不清": "建议：圈出关键词，复述题目要求。",
        "思路中断": "建议：回顾类似题型，建立解题模板。",
        "粗心大意": "建议：做完后检查单位、符号、小数点。",
    }
    return error_map.get(error_type, "建议：分析错误原因，针对性练习。")


def analyze_mistake(error_type: str) -> str:
    """错题归因分析（优先外部API，降级本地）"""
    try:
        result = fetch_mistake_analysis(error_type)
        if result.get("source") == "local":
            return result["data"]
        return result.get("data", {}).get("advice", analyze_mistake_local(error_type))
    except Exception:
        return analyze_mistake_local(error_type)


def suggest_next(subject: str, grade: int, round_num: int) -> str:
    """推荐下一步学习建议"""
    suggestions = []
    if round_num < MAX_ROUNDS:
        suggestions.append(f"继续使用 --round {round_num + 1} 获取更深层提示。")
    else:
        suggestions.append("已完成全部引导轮次，建议独立完成题目。")

    if subject == "math":
        suggestions.append("推荐练习：课本课后习题、历年真题中的同类题型。")
    elif subject in ("physics", "chemistry"):
        suggestions.append("推荐练习：实验题和计算题，注意单位换算。")
    elif subject == "chinese":
        suggestions.append("推荐练习：阅读理解每日一篇，积累好词好句。")
    elif subject == "english":
        suggestions.append("推荐练习：语法专项训练，每日朗读15分钟。")

    # 根据年级段给出建议
    if grade <= 6:
        suggestions.append("建议家长陪伴学习，多鼓励少批评。")
    elif grade <= 9:
        suggestions.append("建议建立错题本，定期复习。")
    else:
        suggestions.append("建议自主总结题型，构建知识网络。")

    return "\n".join(suggestions)


# ========== 苏格拉底式对话状态机 ==========

class SocraticDialogue:
    """苏格拉底式提问引导的对话状态机"""
    
    def __init__(self, question: str, subject: str, grade: int):
        self.question = question
        self.subject = subject
        self.grade = grade
        self.round_num = 0
        self.steps = decompose_problem(question, subject, grade)
        self.current_step = 0
        self.responses = []
        self.finished = False
        
    def next_question(self) -> str:
        """获取下一个引导问题"""
        if self.finished:
            return "对话已结束，请总结你的解题思路。"
        
        if self.round_num >= MAX_ROUNDS:
            self.finished = True
            return "已完成全部引导轮次，请独立完成题目。"
        
        self.round_num += 1
        return generate_hint(self.question, self.subject, self.grade, self.round_num)
    
    def submit_answer(self, answer: str) -> str:
        """提交回答并获取反馈"""
        if self.finished:
            return "对话已结束。"
        
        self.responses.append(answer)
        
        # 简单评估回答质量
        if len(answer.strip()) < 3:
            feedback = "回答太简短了，请详细描述你的思考过程。"
        elif "不知道" in answer or "不会" in answer:
            feedback = "没关系，让我们换个角度思考。"
        else:
            feedback = "很好，继续深入思考。"
        
        # 检查是否完成所有步骤
        if self.round_num >= MAX_ROUNDS:
            self.finished = True
            feedback += "\n已完成全部引导，请尝试独立完成题目。"
        
        return feedback
    
    def get_progress(self) -> dict:
        """获取对话进度"""
        return {
            "round": self.round_num,
            "total_rounds": MAX_ROUNDS,
            "current_step": min(self.current_step + 1, len(self.steps)),
            "total_steps": len(self.steps),
            "finished": self.finished,
            "responses_count": len(self.responses)
        }


# ========== 主流程 ==========

def main():
    parser = argparse.ArgumentParser(
        description="作业引导 Skill - 通过苏格拉底式提问引导自主解题",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python run.py --question '鸡兔同笼...' --subject math --grade 5 --round 1\n  python run.py --selftest"
    )
    parser.add_argument("--question", "-q", type=str, help="题目文本（至少5个字符）")
    parser.add_argument("--subject", "-s", type=str, default="math", choices=sorted(SUBJECTS), help="学科")
    parser.add_argument("--grade", "-g", type=int, default=5, help="年级（3-12）")
    parser.add_argument("--round", "-r", type=int, default=1, help=f"引导轮次（1-{MAX_ROUNDS}）")
    parser.add_argument("--step", type=int, help="查看指定步骤的引导（1-5）")
    parser.add_argument("--review", action="store_true", help="回顾知识点")
    parser.add_argument
