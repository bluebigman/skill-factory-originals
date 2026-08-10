#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trae-skills 技能导航与任务编排助手
- 技能检索（按关键词、场景匹配）
- 任务编排建议（将复杂任务拆解为多技能流程）
- 输入结构化（URL/文件路径/原始数据 -> 结构化描述）
- 置信度标注（区分确定与推测）
- 批量处理（一次处理多个输入项）

仅依赖标准库实现，支持 --selftest 离线自检。
错误码约定：
    E001 参数解析失败
    E002 未知命令或参数
    E003 输入内容为空
    E004 技能库为空或未初始化
    E005 检索条件不合法
    E006 编排任务描述为空
    E007 结构化输入为空
    E008 批量输入列表为空
    E009 内部数据异常（技能条目缺失字段）
    E010 未知运行时错误
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class SkillItem:
    """技能条目：包含标识、名称、关键词、场景标签与描述。"""
    skill_id: str
    name: str
    keywords: List[str]
    scenes: List[str]
    description: str
    confidence: float = 1.0  # 默认置信度（1.0 表示确定）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于 JSON 序列化输出。"""
        return asdict(self)


@dataclass
class MatchResult:
    """单项匹配结果：技能 + 匹配分数 + 置信度标注。"""
    skill: SkillItem
    score: float
    confidence_label: str  # "high" / "medium" / "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill.to_dict(),
            "score": round(self.score, 4),
            "confidence": self.confidence_label,
        }


@dataclass
class OrchestrationPlan:
    """任务编排方案：拆解步骤 + 建议技能组合。"""
    task_description: str
    steps: List[Dict[str, Any]]
    overall_confidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task_description,
            "steps": self.steps,
            "overall_confidence": self.overall_confidence,
        }


# ---------------------------------------------------------------------------
# 内置技能库（硬编码样例数据，用于演示与自检）
# ---------------------------------------------------------------------------

def _builtin_skill_library() -> List[SkillItem]:
    """返回内置技能库。此数据仅用于演示与 selftest，实际使用可替换。"""
    return [
        SkillItem(
            skill_id="skill_frontend_perf",
            name="前端性能优化",
            keywords=["前端", "性能", "优化", "加载", "渲染", "web", "页面"],
            scenes=["性能优化", "前端开发", "网页加速"],
            description="分析并优化前端页面加载速度、渲染效率与资源体积。",
        ),
        SkillItem(
            skill_id="skill_backend_api",
            name="后端接口开发",
            keywords=["后端", "接口", "api", "服务", "数据库", "服务器"],
            scenes=["后端开发", "接口设计", "系统架构"],
            description="设计并实现后端 RESTful API 与数据持久化。",
        ),
        SkillItem(
            skill_id="skill_blog_setup",
            name="博客系统搭建",
            keywords=["博客", "搭建", "建站", "cms", "写作", "发布"],
            scenes=["建站", "内容管理", "个人博客"],
            description="从零搭建带后台管理的个人博客系统。",
        ),
        SkillItem(
            skill_id="skill_log_analysis",
            name="日志分析",
            keywords=["日志", "分析", "排查", "错误", "监控", "追踪"],
            scenes=["运维", "故障排查", "可观测性"],
            description="解析并分析日志文件，定位错误与性能瓶颈。",
        ),
        SkillItem(
            skill_id="skill_code_review",
            name="代码评审",
            keywords=["代码", "评审", "质量", "规范", "审查", "复查"],
            scenes=["代码质量", "团队协作", "开发流程"],
            description="对代码进行系统性审查，发现潜在缺陷与改进点。",
        ),
        SkillItem(
            skill_id="skill_docker_deploy",
            name="容器化部署",
            keywords=["docker", "容器", "部署", "镜像", "云原生", "k8s"],
            scenes=["部署运维", "云原生", "DevOps"],
            description="使用 Docker/K8s 完成应用容器化与自动化部署。",
        ),
        SkillItem(
            skill_id="skill_security_scan",
            name="安全扫描",
            keywords=["安全", "漏洞", "扫描", "渗透", "风险", "审计"],
            scenes=["安全", "合规", "风险控制"],
            description="对系统进行安全漏洞扫描与风险评估。",
        ),
        SkillItem(
            skill_id="skill_db_optimize",
            name="数据库优化",
            keywords=["数据库", "sql", "索引", "优化", "查询", "慢查询"],
            scenes=["数据库", "性能调优", "后端开发"],
            description="分析并优化数据库查询性能与结构设计。",
        ),
    ]


# ---------------------------------------------------------------------------
# 核心逻辑：技能检索
# ---------------------------------------------------------------------------

class SkillMatcher:
    """技能匹配器：负责关键词/场景检索与评分。"""

    def __init__(self, skills: Optional[List[SkillItem]] = None):
        self.skills = skills if skills is not None else _builtin_skill_library()
        if not self.skills:
            raise ValueError("技能库为空")  # 调用方捕获后转 E004

    def search(self, query: str, top_k: int = 3) -> List[MatchResult]:
        """根据查询字符串检索技能，返回按相关度排序的 TOP K 结果。

        评分策略（简单加权）：
            - 查询词命中的关键词权重 +2
            - 查询词命中的场景标签权重 +3
            - 技能名称包含查询词 +1（额外奖励）
        最终分数归一化到 0~1 区间（除以总命中项数最大值，保证宽松可比）。
        """
        if not query or not query.strip():
            raise ValueError("检索条件为空")  # 调用方转 E005

        query_tokens = self._tokenize(query)
        if not query_tokens:
            raise ValueError("检索条件无有效词")  # 调用方转 E005

        results: List[MatchResult] = []
        for skill in self.skills:
            # 检查技能字段完整性
            if not skill.skill_id or not skill.name:
                raise RuntimeError("技能条目缺失必要字段")  # 调用方转 E009

            score = 0.0
            hit_count = 0

            # 关键词匹配（权重 2）
            for kw in skill.keywords:
                if self._token_hit(query_tokens, kw):
                    score += 2.0
                    hit_count += 1

            # 场景匹配（权重 3）
            for sc in skill.scenes:
                if self._token_hit(query_tokens, sc):
                    score += 3.0
                    hit_count += 1

            # 名称包含查询词（奖励 +1）
            if any(q in skill.name for q in query_tokens):
                score += 1.0
                hit_count += 1

            # 归一化：命中次数越多分数越高，但除以 (hit_count + 1) 防止分数无限膨胀
            # 最终分数范围大致在 0~3 之间，便于比较
            if hit_count > 0:
                final_score = score / (hit_count + 1)
                confidence_label = self._confidence_label(final_score)
                results.append(MatchResult(skill=skill, score=final_score, confidence_label=confidence_label))

        # 按分数降序排序
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """将文本切分为小写词元（支持中文与英文混合）。"""
        # 中文按字切分，英文按单词切分；这里简化：按空白与标点切分 + 保留中文连续片段
        text = text.lower()
        # 将中文连续片段整体作为一个词元，英文单词单独
        parts = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", text)
        # 中文片段进一步按字拆开（因为中文关键词通常为二字词）
        tokens: List[str] = []
        for p in parts:
            if re.fullmatch(r"[\u4e00-\u9fff]+", p):
                # 中文：整体作为一个词，同时也拆成单字（但单字匹配意义不大，这里只保留整体）
                tokens.append(p)
            else:
                tokens.append(p)
        # 去重
        seen = set()
        unique_tokens = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                unique_tokens.append(t)
        return unique_tokens

    @staticmethod
    def _token_hit(query_tokens: List[str], target: str) -> bool:
        """判断查询词元是否命中目标字符串（宽松：子串匹配即可）。"""
        target_lower = target.lower()
        for q in query_tokens:
            if q in target_lower or target_lower in q:
                return True
        return False

    @staticmethod
    def _confidence_label(score: float) -> str:
        """根据分数区间给出置信度标签（宽松阈值，避免边界依赖）。"""
        if score >= 1.2:
            return "high"
        elif score >= 0.6:
            return "medium"
        else:
            return "low"


# ---------------------------------------------------------------------------
# 核心逻辑：任务编排
# ---------------------------------------------------------------------------

class TaskOrchestrator:
    """任务编排器：将复杂任务拆解为多技能协作流程。"""

    # 预定义的任务拆解模板（基于关键词识别）
    TEMPLATES = [
        {
            "keywords": ["博客", "建站", "网站", "cms"],
            "steps": [
                {"order": 1, "action": "需求分析与技术选型", "suggested_skill": "skill_blog_setup"},
                {"order": 2, "action": "前端页面设计与实现", "suggested_skill": "skill_frontend_perf"},
                {"order": 3, "action": "后端接口与数据存储", "suggested_skill": "skill_backend_api"},
                {"order": 4, "action": "容器化部署上线", "suggested_skill": "skill_docker_deploy"},
            ],
        },
        {
            "keywords": ["性能", "优化", "慢", "卡顿"],
            "steps": [
                {"order": 1, "action": "前端资源分析与优化", "suggested_skill": "skill_frontend_perf"},
                {"order": 2, "action": "数据库查询优化", "suggested_skill": "skill_db_optimize"},
                {"order": 3, "action": "日志分析与瓶颈定位", "suggested_skill": "skill_log_analysis"},
            ],
        },
        {
            "keywords": ["部署", "上线", "发布", "运维"],
            "steps": [
                {"order": 1, "action": "代码评审与质量检查", "suggested_skill": "skill_code_review"},
                {"order": 2, "action": "容器化打包", "suggested_skill": "skill_docker_deploy"},
                {"order": 3, "action": "安全扫描与合规检查", "suggested_skill": "skill_security_scan"},
            ],
        },
    ]

    def __init__(self, matcher: SkillMatcher):
        self.matcher = matcher

    def orchestrate(self, task_description: str) -> OrchestrationPlan:
        """根据任务描述生成编排方案。"""
        if not task_description or not task_description.strip():
            raise ValueError("任务描述为空")  # 调用方转 E006

        task_lower = task_description.lower()

        # 匹配模板
        matched_template = None
        for template in self.TEMPLATES:
            if any(kw in task_lower for kw in template["keywords"]):
                matched_template = template
                break

        if matched_template:
            steps = matched_template["steps"]
            # 对每个步骤，尝试用技能库补充更精确的建议
            enriched_steps = []
            for step in steps:
                skill_id = step["suggested_skill"]
                # 查找技能库中的对应技能（若无则保留原样）
                skill_found = None
                for skill in self.matcher.skills:
                    if skill.skill_id == skill_id:
                        skill_found = skill
                        break
                if skill_found:
                    enriched_steps.append({
                        "order": step["order"],
                        "action": step["action"],
                        "skill_id": skill_found.skill_id,
                        "skill_name": skill_found.name,
                        "confidence": "high",  # 模板匹配视为高置信
                    })
                else:
                    enriched_steps.append({
                        "order": step["order"],
                        "action": step["action"],
                        "skill_id": skill_id,
                        "skill_name": skill_id,  # 占位
                        "confidence": "medium",
                    })
            return OrchestrationPlan(
                task_description=task_description,
                steps=enriched_steps,
                overall_confidence="high",
            )

        # 无模板匹配：基于检索的通用编排
        results = self.matcher.search(task_description, top_k=3)
        if not results:
            # 无任何匹配，给出通用建议
            return OrchestrationPlan(
                task_description=task_description,
                steps=[
                    {"order": 1, "action": "明确需求与目标", "skill_id": None, "skill_name": "需求分析", "confidence": "low"},
                    {"order": 2, "action": "搜索可用技能", "skill_id": None, "skill_name": "技能检索", "confidence": "low"},
                    {"order": 3, "action": "手动查阅文档", "skill_id": None, "skill_name": "文档阅读", "confidence": "low"},
                ],
                overall_confidence="low",
            )

        steps = []
        for i, res in enumerate(results, start=1):
            steps.append({
                "order": i,
                "action": f"使用技能 {res.skill.name} 处理相关子任务",
                "skill_id": res.skill.skill_id,
                "skill_name": res.skill.name,
                "confidence": res.confidence_label,
            })
        overall_conf = "high" if results[0].confidence_label == "high" else "medium"
        return OrchestrationPlan(
            task_description=task_description,
            steps=steps,
            overall_confidence=overall_conf,
        )


# ---------------------------------------------------------------------------
# 核心逻辑：输入结构化
# ---------------------------------------------------------------------------

class InputStructurer:
    """输入结构化：将 URL、文件路径、原始文本转换为结构化描述。"""

    @staticmethod
    def structure(raw_input: str) -> Dict[str, Any]:
        """识别输入类型并生成结构化描述。"""
        if not raw_input or not raw_input.strip():
            raise ValueError("输入内容为空")  # 调用方转 E007

        raw = raw_input.strip()
        result: Dict[str, Any] = {"original": raw, "type": "unknown", "structured": {}}

        # 识别 URL
        if re.match(r"^https?://", raw, re.IGNORECASE):
            result["type"] = "url"
            result["structured"] = {
                "protocol": raw.split("://")[0].lower(),
                "domain": raw.split("://")[1].split("/")[0] if "://" in raw else "",
                "path": "/" + "/".join(raw.split("://")[1].split("/")[1:]) if "://" in raw and "/" in raw.split("://")[1] else "/",
                "is_secure": raw.lower().startswith("https"),
            }
        # 识别文件路径（常见模式）
        elif re.search(r"[\\/][\w.\-]+$", raw) or "." in raw.split("/")[-1]:
            result["type"] = "file_path"
            parts = raw.replace("\\", "/").split("/")
            filename = parts[-1] if parts else raw
            result["structured"] = {
                "filename": filename,
                "extension": filename.split(".")[-1] if "." in filename else "",
                "directory": "/".join(parts[:-1]) if len(parts) > 1 else ".",
                "is_absolute": raw.startswith("/") or re.match(r"^[A-Za-z]:", raw) is not None,
            }
        # 否则视为原始文本
        else:
            result["type"] = "text"
            word_count = len(re.findall(r"\S+", raw))
            char_count = len(raw)
            result["structured"] = {
                "length": char_count,
                "word_count": word_count,
                "preview": raw[:100] + ("..." if len(raw) > 100 else ""),
                "has_code": bool(re.search(r"[{}();]", raw)),
            }

        return result

    @staticmethod
    def batch_structure(inputs: List[str]) -> List[Dict[str, Any]]:
        """批量结构化处理。"""
        if not inputs:
            raise ValueError("批量输入列表为空")  # 调用方转 E008
        return [InputStructurer.structure(item) for item in inputs]


# ---------------------------------------------------------------------------
# 主程序与 CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="trae-skills",
        description="技能导航与任务编排助手（clean-room 实现）",
        epilog="错误码: E001-E010",
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检并退出")
    parser.add_argument("--search", type=str, metavar="QUERY", help="检索技能（关键词/场景）")
    parser.add_argument("--orchestrate", type=str, metavar="TASK", help="生成任务编排方案")
    parser.add_argument("--structure", type=str, metavar="INPUT", help="结构化单条输入（URL/路径/文本）")
    parser.add_argument("--batch", type=str, metavar="JSON_ARRAY", help="批量结构化输入（JSON 数组）")
    parser.add_argument("--topk", type=int, default=3, help="检索返回数量（默认3）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    return parser


def _safe_run(func, *args, error_code: str = "E010", **kwargs):
    """统一异常处理包装：将内部异常映射为错误码。"""
    try:
        return func(*args, **kwargs)
    except ValueError as e:
        # 根据错误信息映射
        msg = str(e)
        if "检索" in msg or "条件" in msg:
            code = "E005"
        elif "排列" in msg or "任务" in msg:
            code = "E006"
        elif "输入" in msg or "内容" in msg:
            code = "E007"
        elif "批量" in msg:
            code = "E008"
        elif "技能库" in msg:
            code = "E004"
        else:
            code = error_code
        return {"error": code, "message": msg}
    except RuntimeError as e:
        return {"error": "E009", "message": str(e)}
    except Exception as e:
        return {"error": error_code, "message": str(e)}


def _format_output(data: Any, as_json: bool) -> str:
    """格式化输出。"""
    if as_json:
        return json.dumps(data, ensure_ascii=False, indent=2)
    # 文本友好输出
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict) and "skill" in item:
                skill = item["skill"]
                lines.append(f"[{skill['skill_id']}] {skill['name']} (置信度: {item['confidence']}, 分数: {item['score']:.2f})")
                lines.append(f"    描述: {skill['description']}")
            elif isinstance(item, dict):
                lines.append(json.dumps(item, ensure_ascii=False, indent=2))
        return "\n".join(lines)
    elif isinstance(data, dict) and "steps" in data:
        lines = [f"任务: {data['task']}", f"整体置信度: {data['overall_confidence']}", "步骤:"]
        for step in data["steps"]:
            lines.append(f"  {step['order']}. {step['action']} (技能: {step.get('skill_name', 'N/A')}, 置信度: {step.get('confidence', 'N/A')})")
        return "\n".join(lines)
    else:
        return json.dumps(data, ensure_ascii=False, indent=2)


def _run_selftest() -> int:
    """离线自检核心逻辑。使用内置硬编码数据，不依赖外部资源。"""
    print("[selftest] 开始离线自检...")

    # 1. 初始化技能库与匹配器
    skills = _builtin_skill_library()
    matcher = SkillMatcher(skills)
    orchestrator = TaskOrchestrator(matcher)
    structurer = InputStructurer()

    # 2. 测试技能检索
    print("[selftest] 测试技能检索...")
    results = matcher.search("前端性能优化", top_k=3)
    assert len(results) > 0, "检索结果为空"
    assert results[0].score > 0, "检索分数应大于0"
    assert results[0].confidence_label in ("high", "medium", "low"), "置信度标签非法"
    print(f"  [OK] 检索到 {len(results)} 条结果，最高分: {results[0].score:.2f}")

    # 3. 测试空检索（应报错）
    print("[selftest] 测试空检索异常...")
    try:
        matcher.search("   ")
        assert False, "空检索应抛出异常"
    except ValueError:
        print("  [OK] 空检索正确抛出异常")

    # 4. 测试任务编排
    print("[selftest] 测试任务编排...")
    plan = orchestrator.orchestrate("我要搭建一个博客系统")
    assert len(plan.steps) > 0, "编排步骤为空"
    assert plan.overall_confidence in ("high", "medium", "low"), "编排置信度非法"
    print(f"  [OK] 编排生成 {len(plan.steps)} 个步骤，置信度: {plan.overall_confidence}")

    # 5. 测试通用编排（无模板匹配）
    print("[selftest] 测试通用编排...")
    plan2 = orchestrator.orchestrate("写一个python脚本")
    assert len(plan2.steps) > 0, "通用编排步骤为空"
    print(f"  [OK] 通用编排生成 {len(plan2.steps)} 个步骤")

    # 6. 测试输入结构化（URL）
    print("[selftest] 测试 URL 结构化...")
    url_struct = structurer.structure("https://example.com/path/to/page")
    assert url_struct["type"] == "url", "URL 类型识别错误"
    assert url_struct["structured"]["domain"] == "example.com", "域名提取错误"
    assert url_struct["structured"]["is_secure"] is True, "HTTPS 识别错误"
    print(f"  [OK] URL 结构化: {url_struct['structured']['domain']}")

    # 7. 测试输入结构化（文件路径）
    print("[selftest] 测试文件路径结构化...")
    file_struct = structurer.structure("/home/user/code/main.py")
    assert file_struct["type"] == "file_path", "文件路径类型识别错误"
    assert file_struct["structured"]["extension"] == "py", "扩展名提取错误"
    print(f"  [OK] 文件路径结构化: {file_struct['structured']['filename']}")

    # 8. 测试输入结构化（纯文本）
    print("[selftest] 测试文本结构化...")
    text_struct = structurer.structure("这是一段测试文本，包含代码 {print('hello')}")
    assert text_struct["type"] == "text", "文本类型识别错误"
    assert text_struct["structured"]["has_code"] is True, "代码检测错误"
    print(f"  [OK] 文本结构化: 长度={text_struct['structured']['length']}, 词数={text_struct['structured']['word_count']}")

    # 9. 测试批量结构化
    print("[selftest] 测试批量结构化...")
    batch_inputs = ["https://a.com/b", "/tmp/file.txt", "普通文本"]
    batch_results = structurer.batch_structure(batch_inputs)
    assert len(batch_results) == 3, "批量结果数量错误"
    assert batch_results[0]["type"] == "url", "批量第1项类型错误"
    assert batch_results[1]["type"] == "file_path", "批量第2项类型错误"
    assert batch_results[2]["type"] == "text", "批量第3项类型错误"
    print(f"  [OK] 批量结构化完成 {len(batch_results)} 项")

    # 10. 测试技能库完整性
    print("[selftest] 测试技能库完整性...")
    for skill in skills:
        assert skill.skill_id and skill.name, "技能ID或名称为空"
        assert len(skill.keywords) > 0, "技能关键词为空"
        assert len(skill.scenes) > 0, "技能场景为空"
    print(f"  [OK] 技能库共 {len(skills)} 条，全部有效")

    print("[selftest] 全部自检通过 ✔")
    return 0


def main() -> int:
    """主入口。"""
    parser = _build_parser()
    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 在错误时退出，这里捕获并返回错误码
        return 2 if e.code != 0 else 0
    except Exception:
        print(json.dumps({"error": "E001", "message": "参数解析失败"}, ensure_ascii=False))
        return 1

    # 自检模式
    if args.selftest:
        try:
            return _run_selftest()
        except AssertionError as e:
            print(f"[selftest] 失败: {e}")
            return 1
        except Exception as e:
            print(f"[selftest] 异常: {e}")
            return 1

    # 初始化核心组件
    try:
        skills = _builtin_skill_library()
        matcher = SkillMatcher(skills)
        orchestrator = TaskOrchestrator(matcher)
        structurer = InputStructurer()
    except Exception as e:
        print(json.dumps({"error": "E010", "message": f"初始化失败: {e}"}, ensure_ascii=False))
        return 1

    # 分发子命令
    output = None
    if args.search:
        output = _safe_run(matcher.search, args.search, top_k=args.topk, error_code="E005")
    elif args.orchestrate:
        output = _safe_run(orchestrator.orchestrate, args.orchestrate, error_code="E006")
    elif args.structure:
        output = _safe_run(structurer.structure, args.structure, error_code="E007")
    elif args.batch:
        try:
            batch_list = json.loads(args.batch)
            if not isinstance(batch_list, list):
                output = {"error": "E008", "message": "批量输入必须是 JSON 数组"}
            else:
                output = _safe_run(structurer.batch_structure, batch_list, error_code="E008")
        except json.JSONDecodeError:
            output = {"error": "E001", "message": "批量参数不是合法 JSON"}
    else:
        # 无参数时打印帮助
        parser.print_help()
        return 0

    # 输出结果
    if isinstance(output, dict) and "error" in output:
        # 错误情况
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1
    else:
        print(_format_output(output, args.json))
        return 0


if __name__ == "__main__":
    sys.exit(main())
