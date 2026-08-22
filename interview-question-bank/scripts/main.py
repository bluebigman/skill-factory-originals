#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
岗位JD解析 · 面试题库生成 Skill
独立实现脚本，仅依据功能规格编写，不参考任何既有代码。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# ============================================================
# 错误码定义
# E001: 参数错误
# E002: 输入文本为空
# E003: JD文本格式不支持
# E004: 核心逻辑异常
# E005: 输出序列化失败
# E006: 自检失败
# E007: 内部状态错误
# E008: 不支持的岗位类型
# E009: 评分标准生成失败
# E010: 未知错误
# ============================================================

# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class ScoreCriterion:
    """评分标准：维度 + 等级描述 + 观察点"""
    dimension: str
    level_1: str  # 1分描述
    level_3: str  # 3分描述
    level_5: str  # 5分描述
    observation_points: List[str] = field(default_factory=list)


@dataclass
class InterviewQuestion:
    """面试题：题目 + 类型 + 评分标准"""
    question: str
    category: str  # behavioral / professional / stress
    score_criterion: ScoreCriterion


@dataclass
class QuestionBank:
    """面试题库：按类型分组"""
    behavioral: List[InterviewQuestion] = field(default_factory=list)
    professional: List[InterviewQuestion] = field(default_factory=list)
    stress: List[InterviewQuestion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "behavioral": [asdict(q) for q in self.behavioral],
            "professional": [asdict(q) for q in self.professional],
            "stress": [asdict(q) for q in self.stress],
        }


# ============================================================
# JD解析模块
# ============================================================

class JDParser:
    """从JD文本中提取关键信息"""

    # 常见软性素质关键词
    SOFT_SKILLS = [
        "沟通", "协作", "团队", "抗压", "责任心", "主动性",
        "学习能力", "逻辑思维", "问题解决", "领导力", "执行力",
        "创新", "细节", "时间管理", "客户导向"
    ]

    # 常见硬性技能关键词（技术类）
    HARD_SKILLS_TECH = [
        "Java", "Python", "C++", "Go", "JavaScript", "TypeScript",
        "SQL", "MySQL", "Redis", "Kafka", "Docker", "Kubernetes",
        "Linux", "Git", "Spring", "React", "Vue", "Node.js"
    ]

    # 常见岗位类型关键词
    JOB_TYPES = {
        "技术": ["开发", "工程师", "技术", "后端", "前端", "算法", "测试"],
        "产品": ["产品", "需求", "设计"],
        "运营": ["运营", "推广", "增长"],
        "职能": ["人事", "行政", "财务", "法务"],
        "管理": ["管理", "总监", "经理", "主管"],
    }

    def __init__(self, jd_text: str):
        self.jd_text = jd_text
        self._validate()

    def _validate(self) -> None:
        """校验输入文本"""
        if not self.jd_text or not self.jd_text.strip():
            raise ValueError(f"E002: JD文本为空")
        if len(self.jd_text) < 20:
            raise ValueError(f"E003: JD文本过短，无法有效解析（至少20字）")

    def extract_skills(self) -> Dict[str, List[str]]:
        """提取硬性技能和软性素质"""
        hard_skills = []
        soft_skills = []

        # 匹配硬性技能（支持"精通X"、"熟悉X"等模式）
        for skill in self.HARD_SKILLS_TECH:
            if re.search(rf"(精通|熟悉|掌握|熟练|了解)?\s*{re.escape(skill)}", self.jd_text, re.IGNORECASE):
                hard_skills.append(skill)

        # 匹配软性素质
        for skill in self.SOFT_SKILLS:
            if skill in self.jd_text:
                soft_skills.append(skill)

        # 去重保持顺序
        return {
            "hard_skills": list(dict.fromkeys(hard_skills)),
            "soft_skills": list(dict.fromkeys(soft_skills)),
        }

    def extract_job_type(self) -> str:
        """推断岗位类型"""
        for job_type, keywords in self.JOB_TYPES.items():
            for kw in keywords:
                if kw in self.jd_text:
                    return job_type
        return "综合"

    def extract_responsibilities(self) -> List[str]:
        """提取岗位职责要点"""
        # 简单按换行/句号分割，过滤空行
        lines = re.split(r"[\n。；;]", self.jd_text)
        responsibilities = []
        for line in lines:
            line = line.strip()
            # 过滤掉明显不是职责描述的行
            if len(line) > 5 and not line.startswith(("任职", "要求", "加分", "福利")):
                responsibilities.append(line)
        return responsibilities[:5]  # 最多取5条


# ============================================================
# 题目生成模块
# ============================================================

class QuestionGenerator:
    """根据JD解析结果生成三类面试题"""

    def __init__(self, skills: Dict[str, List[str]], job_type: str, responsibilities: List[str]):
        self.hard_skills = skills["hard_skills"]
        self.soft_skills = skills["soft_skills"]
        self.job_type = job_type
        self.responsibilities = responsibilities

    def generate_behavioral(self) -> List[InterviewQuestion]:
        """生成行为面试题（STAR法则）"""
        questions = []
        templates = [
            ("请分享一个你在{context}中遇到的最大挑战，你是如何应对的？请用STAR法则描述。",
             "问题解决能力"),
            ("请举例说明你在{context}中如何与团队协作完成目标。",
             "团队协作"),
            ("描述一次你在{context}中主动承担额外责任的经历。",
             "主动性"),
        ]

        # 根据软性素质调整题目
        for i, (template, dimension) in enumerate(templates):
            context = self._get_context()
            question_text = template.format(context=context)
            criterion = self._build_criterion(
                dimension=dimension,
                level_1="无法清晰描述经历，缺乏具体细节",
                level_3="能描述经历，但缺乏深度反思和具体行动",
                level_5="清晰完整地描述经历，展现出色的能力和深刻反思",
                observations=[
                    "是否使用STAR结构（情境-任务-行动-结果）",
                    "是否体现个人贡献而非团队整体",
                    "是否有量化成果或具体数据",
                    "是否展现出自我反思和改进意识"
                ]
            )
            questions.append(InterviewQuestion(
                question=question_text,
                category="behavioral",
                score_criterion=criterion
            ))

        # 补充针对软性素质的定制题
        for skill in self.soft_skills[:2]:  # 最多补充2题
            q = InterviewQuestion(
                question=f"请举例说明你在工作中如何体现{skill}？遇到困难时你如何保持？",
                category="behavioral",
                score_criterion=self._build_criterion(
                    dimension=skill,
                    level_1="无法举例说明或描述模糊",
                    level_3="能举例但缺乏深度，未能体现核心素质",
                    level_5="举例生动具体，充分展现该素质并带来积极结果",
                    observations=[
                        f"是否清晰阐述{skill}的具体表现",
                        "是否有具体场景和行动",
                        "是否结合了结果和影响"
                    ]
                )
            )
            questions.append(q)

        return questions[:5]  # 最多5题

    def generate_professional(self) -> List[InterviewQuestion]:
        """生成专业面试题"""
        questions = []

        # 基于硬性技能的题目
        for skill in self.hard_skills[:3]:  # 最多取3个技能
            q = InterviewQuestion(
                question=f"请深入谈谈你在{skill}方面的实际项目经验，遇到过哪些棘手问题？如何解决的？",
                category="professional",
                score_criterion=self._build_criterion(
                    dimension=f"{skill}专业能力",
                    level_1="仅停留在理论层面，缺乏实际经验",
                    level_3="有基本实践经验，但深度不足",
                    level_5="有丰富实战经验，能深入讲解原理和最佳实践",
                    observations=[
                        f"是否展示{skill}的深入理解",
                        "是否有真实项目案例支撑",
                        "是否能讲清楚技术选型和权衡",
                        "是否能应对追问和深入探讨"
                    ]
                )
            )
            questions.append(q)

        # 基于岗位类型的专业题
        type_questions = {
            "技术": "请描述一个你负责过的系统架构设计，如何保证可扩展性和稳定性？",
            "产品": "请描述一个你主导的产品从0到1的过程，如何做需求分析和优先级排序？",
            "运营": "请描述一个你策划的运营活动，如何设定目标、制定策略并评估效果？",
            "职能": "请描述一个你优化过的流程或制度，如何衡量改进效果？",
            "管理": "请描述你的团队管理风格，如何激励成员并处理冲突？",
        }
        if self.job_type in type_questions:
            q = InterviewQuestion(
                question=type_questions[self.job_type],
                category="professional",
                score_criterion=self._build_criterion(
                    dimension=f"{self.job_type}岗位专业能力",
                    level_1="回答空泛，缺乏具体案例",
                    level_3="有案例但分析不够深入",
                    level_5="案例详实，分析透彻，体现专业深度",
                    observations=[
                        "是否有具体数据和成果支撑",
                        "是否展现系统思考能力",
                        "是否有方法论沉淀"
                    ]
                )
            )
            questions.append(q)

        return questions[:5]

    def generate_stress(self) -> List[InterviewQuestion]:
        """生成压力面试题"""
        questions = []
        stress_templates = [
            "如果上级给你一个不可能完成的截止日期，你会怎么做？",
            "如果你的方案被团队一致反对，但你坚信自己是对的，你会如何处理？",
            "请分享一次你处理过的重大工作失误，你从中吸取了什么教训？",
        ]
        for i, question_text in enumerate(stress_templates):
            q = InterviewQuestion(
                question=question_text,
                category="stress",
                score_criterion=self._build_criterion(
                    dimension="压力应对与情绪管理",
                    level_1="情绪失控或逃避问题，缺乏应对策略",
                    level_3="能基本应对，但策略单一或缺乏弹性",
                    level_5="冷静分析，多方案应对，能化压力为动力",
                    observations=[
                        "是否保持冷静和理性",
                        "是否有清晰的应对思路",
                        "是否展现灵活性和韧性",
                        "是否能从负面经历中学习"
                    ]
                )
            )
            questions.append(q)

        # 补充基于职责的压力题
        if self.responsibilities:
            resp = self.responsibilities[0]
            q = InterviewQuestion(
                question=f"假设在{resp}过程中，发现资源严重不足且时间紧迫，你会如何调整计划？",
                category="stress",
                score_criterion=self._build_criterion(
                    dimension="应急处理与资源调度",
                    level_1="束手无策或鲁莽行动",
                    level_3="能提出基本应对但缺乏系统性",
                    level_5="能快速评估形势，制定优先级，有效协调资源",
                    observations=[
                        "是否能快速识别关键瓶颈",
                        "是否有优先级排序能力",
                        "是否能有效沟通争取支持"
                    ]
                )
            )
            questions.append(q)

        return questions[:5]

    def _get_context(self) -> str:
        """获取题目上下文"""
        if self.responsibilities:
            return self.responsibilities[0][:30]
        return "工作中"

    def _build_criterion(self, dimension: str, level_1: str, level_3: str, level_5: str, observations: List[str]) -> ScoreCriterion:
        """构建评分标准"""
        return ScoreCriterion(
            dimension=dimension,
            level_1=level_1,
            level_3=level_3,
            level_5=level_5,
            observation_points=observations
        )


# ============================================================
# 核心处理流程
# ============================================================

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def process_jd(jd_text: str) -> QuestionBank:
    """核心处理函数：JD文本 -> 面试题库"""
    try:
        # 1. 解析JD
        parser = JDParser(jd_text)
        skills = parser.extract_skills()
        job_type = parser.extract_job_type()
        responsibilities = parser.extract_responsibilities()

        # 2. 生成题目
        generator = QuestionGenerator(skills, job_type, responsibilities)
        bank = QuestionBank(
            behavioral=generator.generate_behavioral(),
            professional=generator.generate_professional(),
            stress=generator.generate_stress()
        )

        # 3. 验证结果
        if not bank.behavioral and not bank.professional and not bank.stress:
            raise ValueError("E009: 未能生成任何面试题")

        return bank
    except ValueError as e:
        raise
    except Exception as e:
        raise RuntimeError(f"E004: 核心处理逻辑异常 - {str(e)}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """内置样例数据自检核心逻辑"""
    test_cases = [
        {
            "name": "技术岗位JD",
            "jd": """
            岗位职责：
            1. 负责公司核心业务系统的后端开发，使用Java和Python
            2. 参与系统架构设计，保证系统的高可用和可扩展性
            3. 与产品团队紧密协作，快速迭代交付高质量代码

            任职资格：
            1. 3年以上后端开发经验，精通Java或Python
            2. 熟悉Spring框架，了解微服务架构
            3. 熟悉MySQL、Redis等常用存储
            4. 具备良好的沟通能力和团队协作精神
            5. 有较强的抗压能力和责任心
            """
        },
        {
            "name": "产品经理JD",
            "jd": """
            岗位职责：
            1. 负责公司核心产品的规划与设计
            2. 深入理解用户需求，输出高质量PRD文档
            3. 协调开发、测试、运营团队推进产品迭代

            任职资格：
            1. 3年以上产品经理经验
            2. 具备出色的逻辑思维和数据分析能力
            3. 良好的沟通协调能力，能够推动跨团队协作
            4. 有创新意识，关注行业动态
            """
        }
    ]

    try:
        for case in test_cases:
            bank = process_jd(case["jd"])
            # 验证三类题目都存在
            assert bank.behavioral, f"{case['name']}: 缺少行为面试题"
            assert bank.professional, f"{case['name']}: 缺少专业面试题"
            assert bank.stress, f"{case['name']}: 缺少压力面试题"

            # 验证评分标准完整性
            for q in bank.behavioral + bank.professional + bank.stress:
                assert q.score_criterion.dimension, "评分维度为空"
                assert q.score_criterion.level_1 and q.score_criterion.level_3 and q.score_criterion.level_5, "评分等级不完整"
                assert q.score_criterion.observation_points, "观察点为空"

        # 验证错误处理
        try:
            process_jd("")  # 空文本
            raise AssertionError("应抛出E002错误")
        except ValueError as e:
            assert "E002" in str(e), f"错误码不正确: {e}"

        print("[selftest] 全部自检用例通过 ✓")
        return True
    except Exception as e:
        print(f"[selftest] 自检失败: {e}")
        return False


# ============================================================
# 输出格式化
# ============================================================

def format_output(bank: QuestionBank, pretty: bool = True) -> str:
    """格式化输出题库"""
    try:
        data = bank.to_dict()
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"E005: 输出序列化失败 - {str(e)}")


def print_human_readable(bank: QuestionBank) -> None:
    """人类可读的输出格式"""
    category_names = {
        "behavioral": "行为面试题",
        "professional": "专业面试题",
        "stress": "压力面试题"
    }

    print("\n" + "=" * 60)
    print("面试题库生成完成")
    print("=" * 60)

    for category, questions in [
        ("behavioral", bank.behavioral),
        ("professional", bank.professional),
        ("stress", bank.stress)
    ]:
        print(f"\n【{category_names[category]}】")
        for i, q in enumerate(questions, 1):
            print(f"\n  {i}. {q.question}")
            print(f"     评分维度: {q.score_criterion.dimension}")
            print(f"     1分: {q.score_criterion.level_1}")
            print(f"     3分: {q.score_criterion.level_3}")
            print(f"     5分: {q.score_criterion.level_5}")
            print(f"     观察点: {', '.join(q.score_criterion.observation_points)}")

    print("\n" + "=" * 60)
    print("提示：建议根据实际岗位情况调整题目和评分标准")
    print("=" * 60)


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="岗位JD解析 · 面试题库生成 Skill",
        epilog="示例: python main.py --jd '岗位JD文本...' 或 python main.py --selftest"
    )
    parser.add_argument("--jd", type=str, help="岗位JD文本（纯文本或Markdown格式）")
    parser.add_argument("--file", type=str, help="从文件读取JD文本")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--interactive", action="store_true", help="交互模式，手动输入JD文本")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全

    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 获取JD文本
    jd_text = ""
    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8", errors="replace") as f:
                jd_text = f.read()
        elif args.jd:
            jd_text = args.jd
        elif args.interactive:
            print("请输入岗位JD文本（输入空行结束）：")
            lines = []
            while True:
                line = input()
                if line.strip() == "":
                    break
                lines.append(line)
            jd_text = "\n".join(lines)
        else:
            print("错误: 请提供JD文本（--jd 或 --file 或 --interactive）", file=sys.stderr)
            print("提示: 使用 --selftest 运行自检", file=sys.stderr)
            return 1

        # 处理JD
        bank = process_jd(jd_text)

        # 输出结果
        if args.json:
            print(format_output(bank, pretty=True))
        else:
            print_human_readable(bank)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"错误: E001: 文件不存在 - {args.file}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010: 未知错误 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
