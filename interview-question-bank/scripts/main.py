#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interview-question-bank: 岗位JD解析 面试题库生成
=================================================
根据岗位JD文本，自动生成行为、专业、压力三类面试题及评分标准。

功能规格:
- 输入: 岗位JD文本（纯文本或Markdown）
- 输出: 结构化面试题库（每类3-5题，附评分维度、等级、观察点）
- 自检: --selftest 使用内置样例离线验证核心逻辑

错误码:
  E001 参数错误
  E002 输入为空或格式非法
  E003 JD解析失败（无法提取有效信息）
  E004 题库生成失败（内部逻辑异常）
  E005 输出序列化失败
  E006 文件读取失败
  E007 文件写入失败
  E008 自检数据缺失
  E009 自检断言失败
  E010 未知运行时错误

仅依赖Python标准库。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Question:
    """单道面试题"""
    category: str          # 题目类别: behavior / professional / stress
    question: str          # 题目内容
    dimension: str         # 评分维度
    levels: Dict[int, str] # 评分等级 1-5 对应的行为描述
    observation: str       # 参考观察点


@dataclass
class InterviewBank:
    """完整面试题库"""
    jd_summary: str                      # JD要点摘要
    behavior: List[Question] = field(default_factory=list)
    professional: List[Question] = field(default_factory=list)
    stress: List[Question] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return {
            "jd_summary": self.jd_summary,
            "behavior": [asdict(q) for q in self.behavior],
            "professional": [asdict(q) for q in self.professional],
            "stress": [asdict(q) for q in self.stress],
        }


# ---------------------------------------------------------------------------
# JD解析模块
# ---------------------------------------------------------------------------

# 常见软性素质关键词（用于行为面试题）
SOFT_SKILLS = [
    "沟通", "协作", "团队", "领导", "抗压", "责任心", "主动性",
    "学习能力", "逻辑思维", "解决问题", "时间管理", "适应能力",
    "创新", "细节", "执行力", "谈判", "影响力", "情商",
]

# 常见专业能力关键词（用于专业面试题）
TECH_SKILLS = [
    "Java", "Python", "C++", "Go", "JavaScript", "TypeScript",
    "SQL", "NoSQL", "Redis", "Kafka", "Docker", "Kubernetes",
    "Linux", "算法", "数据结构", "机器学习", "深度学习", "NLP",
    "前端", "后端", "全栈", "测试", "运维", "架构", "大数据",
    "数据分析", "产品设计", "用户研究", "项目管理", "运营",
]

# 压力场景关键词（用于压力面试题）
STRESS_KEYWORDS = [
    "高压", "紧急", "冲突", "失败", "批评", "拒绝", "加班",
    "赶进度", "多任务", "变化", "不确定", "困难", "挑战",
]


def parse_jd(raw_text: str) -> Dict[str, List[str]]:
    """
    解析JD文本，提取硬性技能与软性素质。

    返回:
        {
            "skills":    [...],  # 硬性技能/专业关键词
            "soft":      [...],  # 软性素质关键词
            "stress":    [...],  # 压力相关关键词
            "responsibilities": [...],  # 职责句（简单切分）
        }
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("E002: 输入为空或格式非法")

    # 统一大小写（英文关键词匹配用）
    text_lower = raw_text.lower()

    # 提取硬性技能
    skills = []
    for kw in TECH_SKILLS:
        if kw.lower() in text_lower:
            skills.append(kw)

    # 提取软性素质
    soft = []
    for kw in SOFT_SKILLS:
        if kw in raw_text:  # 中文关键词直接匹配
            soft.append(kw)

    # 提取压力相关
    stress_kw = []
    for kw in STRESS_KEYWORDS:
        if kw in raw_text:
            stress_kw.append(kw)

    # 简单切分职责句（按换行/分号/句号）
    lines = re.split(r"[\n;；。]+", raw_text)
    responsibilities = [ln.strip() for ln in lines if len(ln.strip()) > 5]

    return {
        "skills": skills,
        "soft": soft,
        "stress": stress_kw,
        "responsibilities": responsibilities,
    }


# ---------------------------------------------------------------------------
# 题目生成模块
# ---------------------------------------------------------------------------

def _make_question(category: str, question: str, dimension: str,
                   levels: Dict[int, str], observation: str) -> Question:
    """构造Question对象（带基本校验）"""
    if not question or not dimension:
        raise ValueError("E004: 题目或评分维度为空")
    return Question(
        category=category,
        question=question,
        dimension=dimension,
        levels=levels,
        observation=observation,
    )


def _default_levels() -> Dict[int, str]:
    """默认评分等级（1-5分）"""
    return {
        1: "完全不符合要求，表现很差",
        2: "大部分不符合，存在明显不足",
        3: "基本符合要求，有少量瑕疵",
        4: "较为符合，表现良好",
        5: "完全符合且超出预期，表现优秀",
    }


def generate_behavior_questions(parsed: Dict[str, List[str]], jd_raw: str) -> List[Question]:
    """生成行为面试题（STAR法则）"""
    soft = parsed.get("soft", [])
    if not soft:
        soft = ["团队协作", "沟通能力"]  # 兜底默认维度

    questions = []
    used = set()

    for skill in soft[:5]:  # 最多5题
        if skill in used:
            continue
        used.add(skill)

        q_text = (
            f"请分享一个你在过往工作中体现「{skill}」的具体案例。"
            "请按照STAR法则（情境-任务-行动-结果）描述，"
            "并说明你在其中扮演的角色和最终取得的成果。"
        )
        obs = (
            f"观察候选人能否清晰描述情境背景；"
            f"是否明确个人职责与贡献；"
            f"行动步骤是否具体可验证；"
            f"结果是否有量化数据支撑；"
            f"是否体现「{skill}」的核心特质。"
        )
        questions.append(
            _make_question(
                category="behavior",
                question=q_text,
                dimension=f"行为面试-{skill}",
                levels=_default_levels(),
                observation=obs,
            )
        )

    return questions


def generate_professional_questions(parsed: Dict[str, List[str]], jd_raw: str) -> List[Question]:
    """生成专业面试题（技术/业务深度）"""
    skills = parsed.get("skills", [])
    if not skills:
        skills = ["岗位核心技能"]  # 兜底

    questions = []
    used = set()

    for skill in skills[:5]:
        if skill in used:
            continue
        used.add(skill)

        q_text = (
            f"针对「{skill}」，请说明你在实际项目中是如何应用的？"
            "请具体描述一个你使用该技能解决复杂问题的案例，"
            "包括技术选型理由、实现方案、遇到的难点及优化过程。"
        )
        obs = (
            f"考察对「{skill}」的理解深度；"
            "是否能讲清楚原理与机制；"
            "是否有真实项目经验支撑；"
            "能否说明技术方案的权衡与取舍；"
            "是否关注性能、可维护性等工程实践。"
        )
        questions.append(
            _make_question(
                category="professional",
                question=q_text,
                dimension=f"专业面试-{skill}",
                levels=_default_levels(),
                observation=obs,
            )
        )

    return questions


def generate_stress_questions(parsed: Dict[str, List[str]], jd_raw: str) -> List[Question]:
    """生成压力面试题（情境压力测试）"""
    stress_kw = parsed.get("stress", [])
    if not stress_kw:
        stress_kw = ["高压环境"]  # 兜底

    questions = []
    used = set()

    for kw in stress_kw[:5]:
        if kw in used:
            continue
        used.add(kw)

        q_text = (
            f"假设你正在处理一项核心任务，突然遇到「{kw}」的情况："
            "客户/上级临时提出紧急且不合理的要求，且资源受限、时间紧迫。"
            "请描述你会如何应对，以及具体的处理步骤。"
        )
        obs = (
            "观察候选人是否保持冷静；"
            "能否快速分析问题优先级；"
            "是否提出可操作的解决方案；"
            "是否善于调动资源或寻求支持；"
            "事后是否有复盘与改进意识。"
        )
        questions.append(
            _make_question(
                category="stress",
                question=q_text,
                dimension=f"压力面试-{kw}",
                levels=_default_levels(),
                observation=obs,
            )
        )

    return questions


def generate_bank(jd_text: str) -> InterviewBank:
    """核心入口：根据JD文本生成完整面试题库"""
    try:
        parsed = parse_jd(jd_text)
    except ValueError as e:
        raise ValueError(str(e)) from e

    # 生成JD摘要（取前若干职责句）
    resp = parsed.get("responsibilities", [])
    summary = "；".join(resp[:3]) if resp else jd_text.strip()[:100]

    bank = InterviewBank(jd_summary=summary)
    bank.behavior = generate_behavior_questions(parsed, jd_text)
    bank.professional = generate_professional_questions(parsed, jd_text)
    bank.stress = generate_stress_questions(parsed, jd_text)

    # 确保每类至少1题（兜底）
    if not bank.behavior:
        bank.behavior = [_make_question(
            "behavior", "请分享一个你克服重大困难完成目标的经历，并说明你的思考过程。",
            "行为面试-通用", _default_levels(), "观察候选人的韧性、问题解决与目标达成能力。"
        )]
    if not bank.professional:
        bank.professional = [_make_question(
            "professional", "请介绍你最擅长的一项专业技能，并说明其核心原理与应用场景。",
            "专业面试-通用", _default_levels(), "考察专业基础扎实程度与表达清晰度。"
        )]
    if not bank.stress:
        bank.stress = [_make_question(
            "stress", "如果项目上线前夜发现严重Bug，你如何处理？请给出具体步骤。",
            "压力面试-通用", _default_levels(), "考察应急处理能力、优先级判断与沟通协调。"
        )]

    return bank


# ---------------------------------------------------------------------------
# 输出模块
# ---------------------------------------------------------------------------

def format_output(bank: InterviewBank, fmt: str = "json") -> str:
    """将题库格式化为指定格式（json / text）"""
    try:
        if fmt == "json":
            return json.dumps(bank.to_dict(), ensure_ascii=False, indent=2)
        elif fmt == "text":
            lines = [f"JD摘要: {bank.jd_summary}", ""]
            for cat_name, cat_list in [
                ("行为面试题", bank.behavior),
                ("专业面试题", bank.professional),
                ("压力面试题", bank.stress),
            ]:
                lines.append(f"=== {cat_name} ===")
                for i, q in enumerate(cat_list, 1):
                    lines.append(f"{i}. {q.question}")
                    lines.append(f"   评分维度: {q.dimension}")
                    lines.append(f"   观察点: {q.observation}")
                    lines.append("   评分等级:")
                    for score, desc in q.levels.items():
                        lines.append(f"     {score}分: {desc}")
                    lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError(f"E005: 不支持的输出格式: {fmt}")
    except (TypeError, ValueError) as e:
        raise ValueError(f"E005: 输出序列化失败 - {e}") from e


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

SELFTEST_JD = """\
岗位名称：高级Java开发工程师
岗位职责：
- 负责核心业务系统的设计与开发，保障系统高可用性；
- 参与技术方案评审，推动团队技术能力提升；
- 与产品、测试紧密协作，快速迭代交付高质量代码。
任职资格：
- 精通Java编程，熟悉Spring Boot框架；
- 熟悉MySQL、Redis等存储组件；
- 具备良好的沟通能力和团队协作精神；
- 能承受高压工作环境，具备较强的问题解决能力。
加分项：
- 有分布式系统架构经验；
- 熟悉Docker/Kubernetes容器化技术。
"""


def run_selftest() -> None:
    """离线自检核心逻辑"""
    try:
        # 1. 基础解析
        parsed = parse_jd(SELFTEST_JD)
        assert "Java" in parsed["skills"], "E009: 未提取到Java技能"
        assert "沟通" in parsed["soft"], "E009: 未提取到沟通素质"
        assert "高压" in parsed["stress"], "E009: 未提取到压力关键词"

        # 2. 题库生成
        bank = generate_bank(SELFTEST_JD)
        assert len(bank.behavior) >= 1, "E009: 行为题为空"
        assert len(bank.professional) >= 1, "E009: 专业题为空"
        assert len(bank.stress) >= 1, "E009: 压力题为空"
        assert len(bank.behavior) <= 5, "E009: 行为题超过5道"
        assert len(bank.professional) <= 5, "E009: 专业题超过5道"
        assert len(bank.stress) <= 5, "E009: 压力题超过5道"

        # 3. 题目结构校验
        for q in bank.behavior + bank.professional + bank.stress:
            assert q.category in ("behavior", "professional", "stress"), "E009: 类别非法"
            assert len(q.question) > 10, "E009: 题目过短"
            assert len(q.dimension) > 0, "E009: 评分维度为空"
            assert set(q.levels.keys()) == {1, 2, 3, 4, 5}, "E009: 评分等级缺失"
            assert len(q.observation) > 0, "E009: 观察点为空"

        # 4. 输出序列化
        json_out = format_output(bank, "json")
        data = json.loads(json_out)
        assert data["jd_summary"], "E009: 摘要为空"
        assert len(data["behavior"]) >= 1, "E009: 序列化后行为题缺失"

        text_out = format_output(bank, "text")
        assert "行为面试题" in text_out, "E009: 文本输出缺少行为题标题"

        # 5. 边界测试
        try:
            parse_jd("")
            raise AssertionError("E009: 空输入未报错")
        except ValueError:
            pass  # 预期内

        print("[selftest] 全部自检通过 ✔")
        print(f"  行为题: {len(bank.behavior)} 道")
        print(f"  专业题: {len(bank.professional)} 道")
        print(f"  压力题: {len(bank.stress)} 道")

    except AssertionError as e:
        print(f"[selftest] 失败: {e}", file=sys.stderr)
        sys.exit(9)  # E009
    except Exception as e:
        print(f"[selftest] 异常: {e}", file=sys.stderr)
        sys.exit(10)  # E010


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="岗位JD解析 面试题库生成器",
        epilog="示例: python main.py --jd jd.txt --format json --output bank.json",
    )
    parser.add_argument(
        "--jd", type=str,
        help="JD文本文件路径（UTF-8编码）",
    )
    parser.add_argument(
        "--text", type=str,
        help="直接传入JD文本内容（与--jd二选一）",
    )
    parser.add_argument(
        "--format", type=str, choices=["json", "text"], default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        help="输出文件路径（默认输出到stdout）",
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行离线自检并退出",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return 0

    # 参数校验
    if not args.jd and not args.text:
        print("E001: 必须提供 --jd 或 --text 参数", file=sys.stderr)
        return 1

    if args.jd and args.text:
        print("E001: --jd 与 --text 不能同时使用", file=sys.stderr)
        return 1

    # 读取输入
    try:
        if args.jd:
            with open(args.jd, "r", encoding="utf-8") as f:
                jd_text = f.read()
        else:
            jd_text = args.text
    except OSError as e:
        print(f"E006: 文件读取失败 - {e}", file=sys.stderr)
        return 6
    except Exception as e:
        print(f"E010: 未知运行时错误 - {e}", file=sys.stderr)
        return 10

    # 生成题库
    try:
        bank = generate_bank(jd_text)
    except ValueError as e:
        print(f"{e}", file=sys.stderr)
        return 3  # E003 或 E004
    except Exception as e:
        print(f"E010: 未知运行时错误 - {e}", file=sys.stderr)
        return 10

    # 格式化输出
    try:
        output = format_output(bank, args.format)
    except ValueError as e:
        print(f"{e}", file=sys.stderr)
        return 5  # E005

    # 写输出
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"题库已保存至: {args.output}")
        else:
            print(output)
    except OSError as e:
        print(f"E007: 文件写入失败 - {e}", file=sys.stderr)
        return 7
    except Exception as e:
        print(f"E010: 未知运行时错误 - {e}", file=sys.stderr)
        return 10

    return 0


if __name__ == "__main__":
    sys.exit(main())
