#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cv-builder 独立实现脚本
========================
本脚本根据功能规格独立实现（clean-room），不参考任何既有代码。

功能概述：
- 将用户提供的简历数据（结构化字典）转换为单页简历文本。
- 支持能力边界检查、置信度标注、错误码体系（E001-E010）。
- 提供 --selftest 离线自检，使用内置硬编码样例，不依赖外部文件或网络。

运行方式：
    python scripts/main.py --selftest
    python scripts/main.py --input data.json --output result.txt
    python scripts/main.py --input data.json --output result.json --format json
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001 - E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失，请补充：{missing_fields}",
    "E003": "输入格式错误，示例：{\"name\": \"张三\", \"experience\": [...]}",
    "E004": "超出能力边界，本工具仅支持单页简历生成，无法处理该请求",
    "E005": "置信度过低，结果无法确定，建议人工复核",
    "E006": "内部处理错误，请检查输入数据后重试",
    "E007": "输出写入失败，请检查文件路径或权限",
    "E008": "输入文件读取失败，请检查文件路径或格式",
    "E009": "参数错误，请检查命令行参数",
    "E010": "未知错误，请查看日志或联系维护者",
}


def get_error_message(code: str, **kwargs: Any) -> str:
    """根据错误码返回标准话术，支持格式化参数。"""
    message = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if kwargs:
        try:
            return message.format(**kwargs)
        except KeyError:
            return message
    return message


# ============================================================
# 能力边界定义
# ============================================================
CAPABILITY_BOUNDARIES = {
    "max_pages": 1,  # 仅支持单页
    "max_sections": 6,  # 最多支持 6 个主要板块
    "supported_inputs": ["data", "file", "url"],  # 支持的数据来源类型
    "no_network": False,  # 支持网络访问（URL输入）
    "no_external_analysis": True,  # 不执行超出输入范围的分析
}


class CapabilityError(Exception):
    """超出能力边界时抛出的异常。"""

    def __init__(self, code: str = "E004", message: str = ""):
        self.code = code
        self.message = message or get_error_message(code)
        super().__init__(self.message)


# ============================================================
# 核心数据结构
# ============================================================
class ResumeData:
    """简历数据结构，包含所有可渲染的字段。"""

    REQUIRED_FIELDS = ["name"]  # 必填字段

    def __init__(self) -> None:
        self.name: str = ""
        self.title: str = ""  # 职位/头衔
        self.contact: Dict[str, str] = {}  # 联系方式
        self.summary: str = ""  # 个人简介
        self.education: List[Dict[str, str]] = []  # 教育经历
        self.experience: List[Dict[str, str]] = []  # 工作经历
        self.skills: List[str] = []  # 技能列表
        self.projects: List[Dict[str, str]] = []  # 项目经历
        self.certificates: List[str] = []  # 证书
        self.languages: List[str] = []  # 语言能力
        self.interests: List[str] = []  # 兴趣爱好
        self.custom: Dict[str, Any] = {}  # 自定义字段

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeData":
        """从字典构造 ResumeData 对象。"""
        resume = cls()
        if not isinstance(data, dict):
            raise ValueError("输入数据必须是字典类型")

        resume.name = str(data.get("name", "")).strip()
        resume.title = str(data.get("title", "")).strip()
        resume.contact = data.get("contact", {})
        resume.summary = str(data.get("summary", "")).strip()
        resume.education = data.get("education", [])
        resume.experience = data.get("experience", [])
        resume.skills = data.get("skills", [])
        resume.projects = data.get("projects", [])
        resume.certificates = data.get("certificates", [])
        resume.languages = data.get("languages", [])
        resume.interests = data.get("interests", [])
        resume.custom = data.get("custom", {})

        # 类型安全检查
        if not isinstance(resume.contact, dict):
            resume.contact = {}
        for field in ["education", "experience", "projects"]:
            if not isinstance(getattr(resume, field), list):
                setattr(resume, field, [])
        for field in ["skills", "certificates", "languages", "interests"]:
            if not isinstance(getattr(resume, field), list):
                setattr(resume, field, [])

        return resume

    def validate(self) -> Tuple[bool, List[str]]:
        """检查必填字段是否齐全，返回 (是否通过, 缺失字段列表)。"""
        missing = []
        for field in self.REQUIRED_FIELDS:
            if not getattr(self, field):
                missing.append(field)
        return (len(missing) == 0, missing)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化。"""
        return {
            "name": self.name,
            "title": self.title,
            "contact": self.contact,
            "summary": self.summary,
            "education": self.education,
            "experience": self.experience,
            "skills": self.skills,
            "projects": self.projects,
            "certificates": self.certificates,
            "languages": self.languages,
            "interests": self.interests,
            "custom": self.custom,
        }


# ============================================================
# 置信度评估
# ============================================================
class ConfidenceEvaluator:
    """评估结果置信度。"""

    @staticmethod
    def evaluate(resume: ResumeData) -> float:
        """
        计算置信度（0~100）。
        规则：
        - 基础分 30
        - 必填字段(name)完整 +20
        - 每个非空主要板块 +5，最多 +30
        - 联系方式完整 +10
        - 多个板块组合加分 +10
        """
        score = 30.0

        # 必填字段
        valid, _ = resume.validate()
        if valid:
            score += 20.0

        # 主要板块完整性
        sections = [
            resume.title,
            resume.summary,
            resume.education,
            resume.experience,
            resume.skills,
            resume.projects,
        ]
        for section in sections:
            if section:
                score += 5.0
        score = min(score, 80.0)  # 板块加分最多 30

        # 联系方式完整性
        if resume.contact and len(resume.contact) >= 2:
            score += 10.0

        # 多个板块组合加分（至少3个主要板块非空）
        non_empty_count = sum(1 for s in sections if s)
        if non_empty_count >= 3:
            score += 10.0

        return min(score, 100.0)

    @staticmethod
    def get_label(confidence: float) -> str:
        """根据置信度返回标注标签。"""
        if confidence >= 90:
            return ""  # 直接输出，无标注
        elif confidence >= 85:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 单页简历渲染器
# ============================================================
class SinglePageRenderer:
    """将 ResumeData 渲染为单页文本格式。"""

    MAX_LINES = 50  # 单页约 50 行

    @staticmethod
    def render(resume: ResumeData) -> str:
        """渲染简历为文本。"""
        lines: List[str] = []

        # 头部：姓名 + 头衔
        header = resume.name
        if resume.title:
            header += f"  |  {resume.title}"
        lines.append(header)
        lines.append("-" * 40)

        # 联系方式
        if resume.contact:
            contact_str = " | ".join(
                f"{k}: {v}" for k, v in resume.contact.items()
            )
            lines.append(f"联系方式: {contact_str}")

        # 个人简介
        if resume.summary:
            lines.append("")
            lines.append("【个人简介】")
            lines.append(resume.summary)

        # 教育经历
        if resume.education:
            lines.append("")
            lines.append("【教育经历】")
            for edu in resume.education:
                if isinstance(edu, dict):
                    school = edu.get("school", "")
                    degree = edu.get("degree", "")
                    period = edu.get("period", "")
                    lines.append(f"• {school} {degree} {period}".strip())

        # 工作经历
        if resume.experience:
            lines.append("")
            lines.append("【工作经历】")
            for exp in resume.experience:
                if isinstance(exp, dict):
                    company = exp.get("company", "")
                    role = exp.get("role", "")
                    period = exp.get("period", "")
                    desc = exp.get("description", "")
                    lines.append(f"• {company} | {role} | {period}".strip())
                    if desc:
                        lines.append(f"  {desc}")

        # 项目经历
        if resume.projects:
            lines.append("")
            lines.append("【项目经历】")
            for proj in resume.projects:
                if isinstance(proj, dict):
                    name = proj.get("name", "")
                    role = proj.get("role", "")
                    desc = proj.get("description", "")
                    lines.append(f"• {name} ({role})".strip())
                    if desc:
                        lines.append(f"  {desc}")

        # 技能
        if resume.skills:
            lines.append("")
            lines.append("【技能】")
            lines.append(", ".join(resume.skills))

        # 证书
        if resume.certificates:
            lines.append("")
            lines.append("【证书】")
            lines.append(", ".join(resume.certificates))

        # 语言
        if resume.languages:
            lines.append("")
            lines.append("【语言】")
            lines.append(", ".join(resume.languages))

        # 兴趣爱好
        if resume.interests:
            lines.append("")
            lines.append("【兴趣爱好】")
            lines.append(", ".join(resume.interests))

        # 自定义字段
        if resume.custom:
            lines.append("")
            lines.append("【其他】")
            for key, value in resume.custom.items():
                lines.append(f"{key}: {value}")

        # 截断到单页
        if len(lines) > SinglePageRenderer.MAX_LINES:
            lines = lines[: SinglePageRenderer.MAX_LINES]
            lines.append("... (内容已截断，请精简简历以适配单页)")

        return "\n".join(lines)


# ============================================================
# 主处理流程
# ============================================================
def process_resume(
    data: Dict[str, Any],
    output_format: str = "text",
) -> Tuple[str, float, str, Optional[str]]:
    """
    核心处理函数。
    返回: (渲染结果, 置信度, 置信度标签, 错误码或 None)
    """
    # 输入为空检查
    if not data:
        return "", 0.0, "", "E001"

    # 构造 ResumeData
    try:
        resume = ResumeData.from_dict(data)
    except (ValueError, TypeError):
        return "", 0.0, "", "E003"

    # 必填字段检查
    valid, missing = resume.validate()
    if not valid:
        missing_str = ", ".join(missing)
        msg = get_error_message("E002", missing_fields=missing_str)
        return "", 0.0, "", f"E002: {msg}"

    # 能力边界检查：单页限制
    try:
        rendered = SinglePageRenderer.render(resume)
    except Exception:
        return "", 0.0, "", "E006"

    # 置信度评估
    confidence = ConfidenceEvaluator.evaluate(resume)
    label = ConfidenceEvaluator.get_label(confidence)

    # 置信度过低处理
    if confidence < 60:
        return "", confidence, label, "E005"

    # 添加置信度标注
    if label:
        rendered = f"[置信度: {confidence:.0f}%] {label}\n\n" + rendered

    # 根据输出格式处理
    if output_format == "json":
        result = {
            "name": resume.name,
            "title": resume.title,
            "confidence": confidence,
            "label": label,
            "rendered": rendered,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        rendered = json.dumps(result, ensure_ascii=False, indent=2)

    return rendered, confidence, label, None


def fetch_url_with_retry(url: str, max_retries: int = 3, timeout: int = 10) -> str:
    """
    从URL获取内容，带重试退避和超时。
    重试策略：指数退避（1s, 2s, 4s...）
    """
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cv-builder/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise CapabilityError("E008", f"URL获取失败: {e}")
            wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
            print(f"  重试 {attempt + 1}/{max_retries}，等待 {wait_time}s...")
            time.sleep(wait_time)
    raise CapabilityError("E008", "URL获取失败")


def handle_input(
    input_source: str,
    input_type: str = "data",
) -> Dict[str, Any]:
    """
    根据输入来源类型获取数据。
    支持: data(直接字典), file(JSON文件), url(带重试和超时的网络请求)
    """
    if input_type == "data":
        if isinstance(input_source, dict):
            return input_source
        # 尝试解析 JSON 字符串
        try:
            parsed = json.loads(input_source)
            if isinstance(parsed, dict):
                return parsed
            return {}
        except json.JSONDecodeError:
            return {}

    elif input_type == "file":
        try:
            with open(input_source, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    elif input_type == "url":
        try:
            content = fetch_url_with_retry(input_source)
            data = json.loads(content)
            if isinstance(data, dict):
                return data
            return {}
        except json.JSONDecodeError:
            raise CapabilityError("E003", "URL内容不是有效的JSON格式")

    return {}


def run_batch(
    items: List[Dict[str, Any]],
    output_format: str = "text",
) -> List[Dict[str, Any]]:
    """批量处理多个简历数据。"""
    results = []
    for item in items:
        rendered, confidence, label, error = process_resume(item, output_format)
        results.append(
            {
                "rendered": rendered,
                "confidence": confidence,
                "label": label,
                "error": error,
            }
        )
    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> bool:
    """内置硬编码样例数据的离线自检，不依赖外部任何资源。"""
    print("=" * 60)
    print("运行自检 (--selftest)")
    print("=" * 60)

    # 样例 1: 完整简历（高置信度）
    sample_full = {
        "name": "张三",
        "title": "高级软件工程师",
        "contact": {"email": "zhangsan@example.com", "phone": "13800138000"},
        "summary": "8年后端开发经验，擅长分布式系统设计。",
        "education": [
            {"school": "清华大学", "degree": "硕士", "period": "2012-2015"}
        ],
        "experience": [
            {
                "company": "某科技公司",
                "role": "技术主管",
                "period": "2018-至今",
                "description": "负责核心系统架构设计，带领5人团队。",
            }
        ],
        "skills": ["Python", "Go", "Kubernetes", "微服务"],
        "projects": [
            {"name": "高并发订单系统", "role": "架构师", "description": "日处理百万订单。"}
        ],
        "certificates": ["PMP", "AWS认证"],
        "languages": ["中文(母语)", "英语(CET-6)"],
        "interests": ["阅读", "徒步"],
        "custom": {"GitHub": "github.com/zhangsan"},
    }

    # 样例
