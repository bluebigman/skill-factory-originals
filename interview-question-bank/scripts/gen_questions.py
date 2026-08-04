#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interview-question-bank — 面试题库生成器（原创实现 v2.0）

仅依据 SKILL.md 功能规格独立编写，不参考任何既有实现 / 不复制他人代码。

功能：
  - 解析岗位 JD → 提取方向 / 技能项 / 资历层级 / 年限 / 置信度
  - 生成三类题（行为 behavioral / 专业 technical / 压力 stress），每题附
    评估要点、追问方向、难度、置信度分级
  - 支持 json / markdown / text 输出，确定性（同 seed 同结果）
  - 零依赖（仅标准库），离线自检：python gen_questions.py --selftest

错误码 E001-E010。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

__version__ = "2.0.0"

# 错误码定义
ERR: Dict[str, str] = {
    "E001": "缺少 JD 输入（--jd-file 或 --jd-text）",
    "E002": "JD 文件不可读",
    "E003": "读取失败（编码 / IO）",
    "E004": "JD 过短（少于 20 字符）",
    "E005": "未从 JD 识别出任何岗位方向或技能项",
    "E006": "数量越界（1-50）",
    "E007": "题型非法（behavioral/technical/stress）",
    "E008": "难度非法（basic/intermediate/advanced/all）",
    "E009": "格式非法（json/markdown/text）",
    "E010": "未知内部异常",
}

# 常量定义
FORMATS: Tuple[str, ...] = ("json", "markdown", "text")
TYPES: Tuple[str, ...] = ("behavioral", "technical", "stress")
DIFFS: Tuple[str, ...] = ("basic", "intermediate", "advanced")
MAX_COUNT = 50
MIN_LEN = 20


class QError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        message = f"[{code}] {ERR.get(code, '未知错误')}"
        if detail:
            message += f" | {detail}"
        super().__init__(message)


# --------------------------------------------------------------------------
# 领域题库（独立组织：关键词 -> (领域, 专业题列表)），题目措辞为原创重写
# --------------------------------------------------------------------------
# 类型别名
Question = Tuple[str, List[str]]
Domain = Tuple[str, List[Question]]

DOMAINS: Dict[str, Domain] = {
    "python": ("后端开发", [
        ("解释 GIL 对多线程 CPU 密集型任务的影响，你会如何规避？",
         ["说清 GIL 是解释器级锁", "区分 IO 密集与 CPU 密集", "提出多进程 / C 扩展 / 异步等方案"]),
        ("生成器与列表推导在内存上的差异？举一个你实际优化过的场景。",
         ["理解惰性求值", "能量化内存差异", "有真实案例"]),
        ("你如何组织中大型 Python 项目的依赖与虚拟环境？",
         ["了解 venv/poetry/uv", "有依赖锁定意识", "考虑 CI 复现"]),
    ]),
    "java": ("后端开发", [
        ("HashMap 在并发下会出现什么问题？ConcurrentHashMap 如何化解？",
         ["知道扩容死循环 / 数据丢失", "理解分段锁与 CAS", "能说适用边界"]),
        ("讲讲 JVM 内存结构，Full GC 频发你会怎么排查？",
         ["能画堆 / 栈 / 方法区", "熟悉 jstat/jmap/MAT", "有真实经历"]),
    ]),
    "go": ("后端开发", [
        ("Goroutine 泄漏通常由什么引起？如何检测？",
         ["理解 channel 阻塞致泄漏", "会用 pprof", "有防御性 context 习惯"]),
    ]),
    "前端": ("前端开发", [
        ("浏览器输入 URL 到渲染完成发生了什么？挑你最熟的一环讲深。",
         ["链路完整", "深入某一环（DNS/TCP/渲染树）", "有性能视角"]),
        ("如何定位并优化首屏加载慢？",
         ["会用 Lighthouse/Performance", "懂懒加载/分包/CDN", "能给量化指标"]),
    ]),
    "react": ("前端开发", [
        ("useEffect 依赖数组写错会出什么问题？如何避免？",
         ["理解闭包陷阱", "知道 eslint 插件", "有真实踩坑"]),
    ]),
    "sql": ("数据开发", [
        ("一条查询突然变慢，你的排查顺序？",
         ["看执行计划", "懂索引失效场景", "考虑数据量与统计信息"]),
        ("说明索引在哪些情况下会失效？",
         ["列出隐式转换/函数包裹/最左前缀", "能结合业务举例"]),
    ]),
    "数据分析": ("数据分析", [
        ("业务方说『这周 DAU 掉了 5%』，你如何拆解定位？",
         ["有拆解框架（维度下钻）", "区分噪声与真实下跌", "给验证方案"]),
        ("如何设计 A/B 实验验证新功能效果？",
         ["懂分流与样本量", "知显著性检验", "考虑实验污染"]),
    ]),
    "机器学习": ("算法", [
        ("模型线下好、线上掉点，可能原因？",
         ["想到特征穿越/分布漂移", "懂线上线下一致", "有监控意识"]),
        ("如何处理严重类别不平衡？",
         ["了解采样/加权/阈值", "知换评估指标（AUC/PR）"]),
    ]),
    "产品": ("产品经理", [
        ("如何判断一个需求该不该做？给出框架。",
         ["有优先级框架（RICE/KANO）", "考虑投入产出", "对齐业务目标"]),
        ("如何衡量功能上线后的成败？",
         ["能定义北极星指标", "有埋点意识", "考虑负向指标"]),
    ]),
    "运营": ("运营", [
        ("新社区产品冷启动，你会怎么做？",
         ["有种子用户策略", "考虑内容供给", "有可量化目标"]),
    ]),
    "测试": ("测试开发", [
        ("如何设计支付流程的测试用例集？",
         ["覆盖正常/异常/边界", "考虑幂等与对账", "有自动化思路"]),
    ]),
    "运维": ("运维/SRE", [
        ("线上服务 CPU 打满，你的应急步骤？",
         ["先止损再定位", "熟悉 top/perf/火焰图", "有复盘意识"]),
    ]),
    "销售": ("销售", [
        ("客户说『你们太贵了』，你怎么应对？",
         ["不立刻降价", "挖掘真实异议", "转向价值沟通"]),
    ]),
}

# 行为面试题
BEHAVIOR: List[Question] = [
    ("讲一次你主导推动、且跨团队协作的项目，你具体做了什么？",
     ["用 STAR 表述", "说清独立贡献", "体现推动而非执行"]),
    ("说一个最终失败的项目，你学到了什么？",
     ["敢于承认失败", "归因客观不甩锅", "有可迁移结论"]),
    ("与同事在技术方案上严重分歧时，你如何处理？",
     ["以数据/目标说服而非情绪", "有妥协与坚持边界", "结果导向"]),
    ("讲一次你在信息不充分时做决策的经历。",
     ["识别关键未知项", "有风险对冲", "事后验证"]),
    ("最近一年你主动学了什么？为什么？",
     ["动机与规划一致", "有实际产出", "讲清收获"]),
]

# 压力面试题
STRESS: List[Question] = [
    ("你的方案被当面指出有明显缺陷，重新想一个？",
     ["顶住压力复述论据", "区分被质疑与被否定", "不轻易自我否定也不固执"]),
    ("履历跳槽频繁，凭什么相信你会留下？",
     ["回应真诚不回避", "给稳定性证据", "引向职业规划"]),
    ("今天入职明天独立负责模块，你敢接吗？",
     ["评估能力边界", "主动索要资源", "不盲目承诺"]),
    ("你刚才有个技术细节说错了，意识到了吗？",
     ["冷静复盘", "承认不慌", "有纠错力"]),
]

# 资历识别规则
SENIORITY: List[Tuple[str, str, str]] = [
    (r"(专家|principal|staff|架构师)", "专家", "advanced"),
    (r"(高级|senior|资深|leader|主管|经理)", "高级", "advanced"),
    (r"(中级|3-5\s*年|三到五年)", "中级", "intermediate"),
    (r"(初级|junior|应届|实习|1-3\s*年|校招)", "初级", "basic"),
]

# 中文映射
TYPE_CN: Dict[str, str] = {"behavioral": "行为面试题", "technical": "专业技能题", "stress": "压力测试题"}
DIFF_CN: Dict[str, str] = {"basic": "基础", "intermediate": "进阶", "advanced": "高级"}

# 类型别名
Profile = Dict[str, Any]
QuestionItem = Dict[str, Any]


# --------------------------------------------------------------------------
# JD 解析
# --------------------------------------------------------------------------
def read_jd(jd_file: str = "", jd_text: str = "") -> str:
    """
    读取 JD 内容。
    
    Args:
        jd_file: JD 文件路径
        jd_text: 直接传入的 JD 文本
        
    Returns:
        JD 文本内容
        
    Raises:
        QError: 各种输入错误
    """
    # 校验输入
    if not jd_text and not jd_file:
        raise QError("E001")
    
    if jd_text:
        text = jd_text
    else:
        # 文件路径校验
        p = Path(jd_file)
        if not p.is_file():
            raise QError("E002", jd_file)
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            raise QError("E003", str(e))
    
    # 长度校验
    stripped = text.strip()
    if len(stripped) < MIN_LEN:
        raise QError("E004", f"有效字符 {len(stripped)}")
    
    return text


def parse_jd(text: str) -> Profile:
    """
    解析 JD 文本，提取岗位信息。
    
    Args:
        text: JD 文本
        
    Returns:
        岗位画像字典
        
    Raises:
        QError: 无法识别岗位方向
    """
    low = text.lower()
    
    # 匹配技能关键词
    matched = [k for k in DOMAINS if k in low]
    if not matched:
        raise QError("E005", "JD 未明确技术栈或岗位方向")
    
    # 去重领域
    domains: List[str] = []
    for k in matched:
        d = DOMAINS[k][0]
        if d not in domains:
            domains.append(d)
    
    # 识别资历
    seniority, default_diff = "中级", "intermediate"
    for pat, label, diff in SENIORITY:
        if re.search(pat, low):
            seniority, default_diff = label, diff
            break
    
    # 提取年限
    years: Optional[str] = None
    ym = re.search(r"(\d+)\s*[-~到]\s*(\d+)\s*年", text) or re.search(r"(\d+)\s*年以上", text)
    if ym:
        years = ym.group(0)
    
    # 计算置信度
    conf = 70 + min(len(matched), 4) * 6
    if years:
        conf += 4
    if seniority != "中级" or re.search(r"(初级|中级|高级|专家|senior|junior)", low):
        conf += 4
    
    return {
        "domains": domains,
        "skills": matched,
        "seniority": seniority,
        "years": years,
        "default_difficulty": default_diff,
        "confidence": min(conf, 98),
    }


def confidence_label(c: int) -> str:
    """将置信度数值转换为文字标签"""
    if c >= 90:
        return "高（可直接使用）"
    if c >= 85:
        return "中（建议人工复核）"
    return "低（需人工核实）"


# --------------------------------------------------------------------------
# 出题
# --------------------------------------------------------------------------
def _diff_for(idx: int, base: str) -> str:
    """
    根据索引和基础难度计算题目难度。
    
    Args:
        idx: 题目索引
        base: 基础难度
        
    Returns:
        题目难度
    """
    table = {
        "basic": ("basic", "basic", "intermediate"),
        "advanced": ("intermediate", "advanced", "advanced"),
    }
    return table.get(base, ("basic", "intermediate", "advanced"))[idx % 3]


def generate(
    profile: Profile,
    count: int,
    types: List[str],
    difficulty: str,
    seed: int,
) -> List[QuestionItem]:
    """
    生成面试题目。
    
    Args:
        profile: 岗位画像
        count: 题目数量
        types: 题型列表
        difficulty: 难度过滤
        seed: 随机种子
        
    Returns:
        题目列表
    """
    rng = random.Random(seed)
    base = profile["default_difficulty"]
    
    # 构建题目池
    pool: List[Tuple[str, str, str, List[str]]] = []
    
    if "technical" in types:
        for kw in profile["skills"]:
            for q, pts in DOMAINS[kw][1]:
                pool.append(("technical", kw, q, pts))
    
    if "behavioral" in types:
        for q, pts in BEHAVIOR:
            pool.append(("behavioral", "通用", q, pts))
    
    if "stress" in types:
        for q, pts in STRESS:
            pool.append(("stress", "抗压", q, pts))
    
    if not pool:
        raise QError("E007", f"题型 {types} 未产出题目")
    
    # 洗牌并筛选
    rng.shuffle(pool)
    out: List[QuestionItem] = []
    
    for i, (qt, tag, q, pts) in enumerate(pool):
        diff = _diff_for(i, base)
        if difficulty != "all" and diff != difficulty:
            continue
        
        out.append({
            "id": f"Q{len(out) + 1:03d}",
            "type": qt,
            "tag": tag,
            "difficulty": diff,
            "question": q,
            "evaluation_points": pts,
            "follow_up": _follow(qt),
        })
        
        if len(out) >= count:
            break
    
    return out


def _follow(qt: str) -> str:
    """根据题型返回追问方向"""
    follow_ups = {
        "technical": "若回答流畅，追问『线上真实遇到过吗？当时数据量级与处理结果？』",
        "behavioral": "若回答笼统，追问『这件事里只由你独立决定的部分是哪些？』",
        "stress": "观察情绪稳定，追问『如果我坚持我的看法，你会怎么做？』",
    }
    return follow_ups.get(qt, "视回答深度追问细节")


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------
def render(profile: Profile, questions: List[QuestionItem], fmt: str) -> str:
    """
    渲染输出内容。
    
    Args:
        profile: 岗位画像
        questions: 题目列表
        fmt: 输出格式
        
    Returns:
        渲染后的文本
    """
    if fmt not in FORMATS:
        raise QError("E009", fmt)
    
    if fmt == "json":
        return json.dumps({
            "status": "success",
            "profile": {**profile, "confidence_level": confidence_label(profile["confidence"])},
            "total": len(questions),
            "questions": questions,
        }, ensure_ascii=False, indent=2)
    
    # 构建头部信息
    head = (
        f"岗位方向: {' / '.join(profile['domains'])}\n"
        f"识别技能: {', '.join(profile['skills'])}\n"
        f"资历层级: {profile['seniority']}"
        + (f"（{profile['years']}）" if profile["years"] else "") + "\n"
        f"置信度: {profile['confidence']}% - {confidence_label(profile['confidence'])}\n"
        f"题目总数: {len(questions)}"
    )
    
    if fmt == "text":
        lines = [head, "-" * 60]
        for q in questions:
            lines.append(f"[{q['id']}][{TYPE_CN[q['type']]}][{DIFF_CN[q['difficulty']]}] {q['question']}")
            for p in q["evaluation_points"]:
                lines.append(f"    · {p}")
            lines.append(f"    追问: {q['follow_up']}")
        return "\n".join(lines)
    
    # markdown 格式
    lines = ["# 面试题库", "", "## 岗位画像", "", head.replace("\n", "  \n"), ""]
    for qt in TYPES:
        group = [q for q in questions if q["type"] == qt]
        if not group:
            continue
        lines += [f"## {TYPE_CN[qt]}（{len(group)} 题）", ""]
        for q in group:
            lines += [
                f"### {q['id']}　{q['question']}", "",
                f"- 难度：{DIFF_CN[q['difficulty']]}　标签：{q['tag']}",
                "- 评估要点：",
            ]
            lines += [f"  - {p}" for p in q["evaluation_points"]]
            lines += [f"- 追问方向：{q['follow_up']}", ""]
    
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 参数校验
# --------------------------------------------------------------------------
def _vcount(c: int) -> int:
    """校验题目数量"""
    if not 1 <= c <= MAX_COUNT:
        raise QError("E006", str(c))
    return c


def _vtypes(s: str) -> List[str]:
    """校验题型"""
    picked = [t.strip().lower() for t in s.split(",") if t.strip()]
    if not picked:
        raise QError("E007", "空")
    for t in picked:
        if t not in TYPES:
            raise QError("E007", t)
    return picked


def _vdiff(d: str) -> str:
    """校验难度"""
    d = d.strip().lower()
    if d != "all" and d not in DIFFS:
        raise QError("E008", d)
    return d


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
SAMPLE = (
    "招聘高级后端开发工程师，5年以上经验。"
    "要求精通 Python，熟悉 SQL 优化与分布式系统设计，"
    "有大规模数据处理经验者优先。"
)


def selftest() -> int:
    """运行离线自检"""
    passed: List[str] = []
    failed: List[str] = []
    
    def chk(name: str, fn: Callable[[], None]) -> None:
        """执行测试并记录结果"""
        try:
            fn()
            passed.append(name)
            print(f"  [OK] {name}")
        except Exception as e:
            failed.append(name)
            print(f"  [FAIL] {name} -> {type(e).__name__}: {e}")
    
    def expect(code: str, fn: Callable[[], Any]) -> Callable[[], None]:
        """构造期望抛出指定错误的测试函数"""
        def _inner() -> None:
            try:
                fn()
            except QError as e:
                assert e.code == code, f"期望 {code} 实得 {e.code}"
                return
            raise AssertionError(f"期望抛 {code}")
        return _inner
    
    print("== gen_questions.py 离线自检 ==")
    
    # 输入校验测试
    chk("E001 无输入", expect("E001", lambda: read_jd()))
    chk("E004 过短", expect("E004", lambda: read_jd(jd_text="太短")))
    chk("E005 无法识别", expect("E005", lambda: parse_jd("需要良好沟通与协作精神。")))
    chk("E006 越界", expect("E006", lambda: _vcount(999)))
    chk("E007 题型非法", expect("E007", lambda: _vtypes("bad")))
    chk("E008 难度非法", expect("E008", lambda: _vdiff("bad")))
    chk("E009 格式非法", expect("E009", lambda: render(parse_jd(SAMPLE), [], "yaml")))
    
    # 功能测试
    chk("JD 解析技能与资历", lambda: _assert_profile())
    chk("出题数量", lambda: _assert_count())
    chk("同 seed 确定性", lambda: _assert_det())
    chk("字段齐全", lambda: _assert_fields())
    chk("json 可反序列化", lambda: _assert_json())
    chk("markdown 标题", lambda: _assert_md())
    chk("text 含置信度", lambda: _assert_text())
    chk("难度过滤", lambda: _assert_filter())
    
    # 边界测试
    chk("count=1 最小数量", lambda: _assert_min_count())
    chk("count=50 最大数量", lambda: _assert_max_count())
    chk("空题型列表", expect("E007", lambda: _vtypes("")))
    chk("空 JD 文件", expect("E004", lambda: read_jd(jd_text=" ")))
    
    print(f"== 自检完成：{len(passed)} 通过 / {len(failed)} 失败 ==")
    return 0 if not failed else 1


def _assert_profile() -> None:
    """验证 JD 解析功能"""
    p = parse_jd(SAMPLE)
    assert "python" in p["skills"] and "sql" in p["skills"], p
    assert p["seniority"] == "高级" and p["confidence"] >= 85, p


def _assert_count() -> None:
    """验证出题数量"""
    p = parse_jd(SAMPLE)
    assert len(generate(p, 5, list(TYPES), "all", 42)) == 5


def _assert_det() -> None:
    """验证确定性"""
    p = parse_jd(SAMPLE)
    assert generate(p, 6, list(TYPES), "all", 7) == generate(p, 6, list(TYPES), "all", 7)


def _assert_fields() -> None:
    """验证题目字段完整性"""
    p = parse_jd(SAMPLE)
    for q in generate(p, 4, list(TYPES), "all", 1):
        assert q["evaluation_points"] and q["follow_up"] and q["id"], q


def _assert_json() -> None:
    """验证 JSON 输出"""
    p = parse_jd(SAMPLE)
    obj = json.loads(render(p, generate(p, 3, list(TYPES), "all", 3), "json"))
    assert obj["status"] == "success" and obj["total"] == 3


def _assert_md() -> None:
    """验证 Markdown 输出"""
    p = parse_jd(SAMPLE)
    assert render(p, generate(p, 3, list(TYPES), "all", 3), "markdown").startswith("# 面试题库")


def _assert_text() -> None:
    """验证文本输出"""
    p = parse_jd(SAMPLE)
    assert "置信度" in render(p, generate(p, 3, list(TYPES), "all", 3), "text")


def _assert_filter() -> None:
    """验证难度过滤"""
    p = parse_jd(SAMPLE)
    qs = generate(p, 10, list(TYPES), "advanced", 5)
    assert qs and all(q["difficulty"] == "advanced" for q in qs)


def _assert_min_count() -> None:
    """验证最小数量"""
    p = parse_jd(SAMPLE)
    assert len(generate(p, 1, list(TYPES), "all", 42)) == 1


def _assert_max_count() -> None:
    """验证最大数量"""
    p = parse_jd(SAMPLE)
    assert len(generate(p, MAX_COUNT, list(TYPES), "all", 42)) == MAX_COUNT


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    p = argparse.ArgumentParser(
        prog="gen_questions.py",
        description="岗位 JD → 面试题库（行为/专业/压力），附评估要点与追问",
    )
    p.add_argument("--jd-file", default="", help="JD 文件路径(UTF-8)")
    p.add_argument("--jd-text", default="", help="直接传 JD 文本")
    p.add_argument("--count", type=int, default=10, help=f"题目数 1-{MAX_COUNT}")
    p.add_argument("--types", default="behavioral,technical,stress", help="题型逗号分隔")
    p.add_argument("--difficulty", default="all", help="all/basic/intermediate/advanced")
    p.add_argument("--format", default="markdown", help="json/markdown/text")
    p.add_argument("--seed", type=int, default=20260804, help="随机种子（确定性）")
    p.add_argument("--selftest", action="store_true", help="离线自检")
    p.add_argument("--version", action="version", version=f"gen_questions.py {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    args = build_parser().parse_args(argv)
    
    # 自检模式
    if args.selftest:
        return selftest()
    
    try:
        # 参数校验
        count = _vcount(args.count)
        types = _vtypes(args.types)
        difficulty = _vdiff(args.difficulty)
        if args.format not in FORMATS:
            raise QError("E009", args.format)
        
        # 读取并解析 JD
        text = read_jd(args.jd_file, args.jd_text)
        profile = parse_jd(text)
        
        # 生成题目并输出
        questions = generate(profile, count, types, difficulty, args.seed)
        print(render(profile, questions, args.format))
        return 0
        
    except QError as e:
        # 输出错误信息
        print(
            json.dumps(
                {"status": "error", "code": e.code, "message": ERR.get(e.code, "")},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        # 未知异常兜底
        print(
            json.dumps(
                {"status": "error", "code": "E010", "message": str(e)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
