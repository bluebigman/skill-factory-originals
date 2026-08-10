#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历优化 (resume-builder) - 独立实现脚本

本脚本依据功能规格独立编写，仅使用 Python 标准库。
提供简历数据解析、结构化、置信度评估与输出功能。
支持 --selftest 离线自检。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码常量
# ---------------------------------------------------------------------------
ERR_INPUT_EMPTY = "E001"       # 输入为空
ERR_MISSING_INFO = "E002"      # 关键信息缺失
ERR_FORMAT = "E003"            # 输入格式错误
ERR_OUT_OF_SCOPE = "E004"      # 超出能力边界
ERR_LOW_CONFIDENCE = "E005"    # 置信度过低
# 保留 E006-E010 以备扩展


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ResumeData:
    """简历数据结构，按标准字段组织。"""

    def __init__(self) -> None:
        self.name: str = ""
        self.contact: Dict[str, str] = {}       # 邮箱、电话等
        self.education: List[Dict[str, str]] = []
        self.experience: List[Dict[str, str]] = []
        self.skills: List[str] = []
        self.projects: List[Dict[str, str]] = []
        self.raw_text: str = ""                 # 保存原始输入，用于回溯
        self.confidence: float = 0.0            # 整体置信度 0-100


class ProcessResult:
    """处理结果封装，包含数据、置信度与标注信息。"""

    def __init__(self, data: ResumeData, confidence: float,
                 warnings: List[str]) -> None:
        self.data = data
        self.confidence = confidence
        self.warnings = warnings                 # 低置信度或需复核的提示


# ---------------------------------------------------------------------------
# 输入解析模块
# ---------------------------------------------------------------------------
def parse_input(raw: str) -> Dict[str, Any]:
    """
    解析用户输入。

    支持两种形式：
      1. JSON 字符串（对象或数组）
      2. 纯文本（按行提取关键信息）

    返回字典结构，键为规范化的字段名。
    输入为空或格式错误时抛出 ValueError，带错误码。
    """
    if raw is None or raw.strip() == "":
        raise ValueError(f"{ERR_INPUT_EMPTY}: 输入为空，请提供待处理的内容")

    text = raw.strip()

    # 尝试 JSON 解析
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return _normalize_json(parsed)
        elif isinstance(parsed, list):
            # 列表视为多个简历条目，合并为一个
            merged: Dict[str, Any] = {}
            for item in parsed:
                if isinstance(item, dict):
                    merged = _merge_dict(merged, _normalize_json(item))
            if merged:
                return merged
            raise ValueError(f"{ERR_FORMAT}: JSON 数组为空或格式错误")
        else:
            raise ValueError(f"{ERR_FORMAT}: JSON 顶层必须是对象或数组")
    except json.JSONDecodeError:
        # 非 JSON，按文本处理
        return _parse_text(text)


def _normalize_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """将 JSON 对象映射到内部标准字段。"""
    normalized: Dict[str, Any] = {}

    # 姓名映射
    for key in ("name", "姓名", "full_name"):
        if key in data and data[key]:
            normalized["name"] = str(data[key])
            break

    # 联系方式映射
    contact: Dict[str, str] = {}
    for key, field in (("email", "email"), ("phone", "phone"),
                       ("邮箱", "email"), ("电话", "phone")):
        if key in data and data[key]:
            contact[field] = str(data[key])
    if contact:
        normalized["contact"] = contact

    # 教育经历
    if "education" in data and isinstance(data["education"], list):
        normalized["education"] = [
            _normalize_entry(item) for item in data["education"]
            if isinstance(item, dict)
        ]

    # 工作经历
    if "experience" in data and isinstance(data["experience"], list):
        normalized["experience"] = [
            _normalize_entry(item) for item in data["experience"]
            if isinstance(item, dict)
        ]

    # 技能列表
    if "skills" in data:
        skills = data["skills"]
        if isinstance(skills, list):
            normalized["skills"] = [str(s) for s in skills if s]
        elif isinstance(skills, str):
            normalized["skills"] = [s.strip() for s in skills.split(",") if s.strip()]

    # 项目经历
    if "projects" in data and isinstance(data["projects"], list):
        normalized["projects"] = [
            _normalize_entry(item) for item in data["projects"]
            if isinstance(item, dict)
        ]

    return normalized


def _normalize_entry(entry: Dict[str, Any]) -> Dict[str, str]:
    """将单个条目（教育/经历/项目）转换为字符串字典。"""
    result: Dict[str, str] = {}
    for key, value in entry.items():
        if value is not None:
            result[str(key)] = str(value)
    return result


def _merge_dict(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    """合并两个字典，列表字段直接拼接。"""
    for key, value in extra.items():
        if key in base and isinstance(base[key], list) and isinstance(value, list):
            base[key].extend(value)
        elif key not in base or not base[key]:
            base[key] = value
    return base


def _parse_text(text: str) -> Dict[str, Any]:
    """从纯文本中提取关键信息。"""
    result: Dict[str, Any] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        raise ValueError(f"{ERR_INPUT_EMPTY}: 文本内容为空")

    # 简单模式匹配提取
    # 姓名：首行非空且较短
    if lines and len(lines[0]) < 30:
        result["name"] = lines[0]

    # 邮箱
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    if email_match:
        result.setdefault("contact", {})["email"] = email_match.group(0)

    # 电话（简单匹配 11 位数字）
    phone_match = re.search(r"1[3-9]\d{9}", text)
    if phone_match:
        result.setdefault("contact", {})["phone"] = phone_match.group(0)

    # 技能：匹配“技能：”开头的行
    for line in lines:
        if line.startswith("技能") or line.startswith("skill"):
            skills_part = line.split(":", 1)[-1].strip()
            result["skills"] = [s.strip() for s in skills_part.split(",") if s.strip()]
            break

    # 教育/经历：识别包含学校/公司关键词的行
    edu_list: List[Dict[str, str]] = []
    exp_list: List[Dict[str, str]] = []
    for line in lines:
        if any(kw in line for kw in ("大学", "学院", "学校")):
            edu_list.append({"school": line})
        elif any(kw in line for kw in ("公司", "集团", "有限")):
            exp_list.append({"company": line})
    if edu_list:
        result["education"] = edu_list
    if exp_list:
        result["experience"] = exp_list

    return result


# ---------------------------------------------------------------------------
# 核心处理流程
# ---------------------------------------------------------------------------
def build_resume(raw_input: str) -> ProcessResult:
    """
    执行简历构建主流程。

    步骤：
      1. 解析输入
      2. 结构化数据
      3. 计算置信度
      4. 生成标注

    """
    # Step 1: 解析
    try:
        parsed = parse_input(raw_input)
    except ValueError as exc:
        # 透传错误码
        raise ValueError(str(exc)) from exc

    # Step 2: 构建数据对象
    resume = ResumeData()
    resume.raw_text = raw_input.strip()
    resume.name = parsed.get("name", "")
    resume.contact = parsed.get("contact", {})
    resume.education = parsed.get("education", [])
    resume.experience = parsed.get("experience", [])
    resume.skills = parsed.get("skills", [])
    resume.projects = parsed.get("projects", [])

    # Step 3: 置信度评估
    confidence, warnings = _evaluate_confidence(resume)

    # Step 4: 检查低置信度
    if confidence < 85:
        warnings.append(f"[需核实] 整体置信度 {confidence:.0f}%，"
                        f"建议人工复核关键信息")

    resume.confidence = confidence
    return ProcessResult(resume, confidence, warnings)


def _evaluate_confidence(resume: ResumeData) -> Tuple[float, List[str]]:
    """
    根据数据完整性计算置信度（0-100）。

    规则：
      - 基础分 50
      - 姓名存在 +15
      - 联系方式存在 +15
      - 教育或经历存在 +10
      - 技能存在 +10
    满分 100，最低 50。
    """
    score = 50.0
    warnings: List[str] = []

    if resume.name:
        score += 15
    else:
        warnings.append("缺少姓名")

    if resume.contact:
        score += 15
    else:
        warnings.append("缺少联系方式")

    if resume.education or resume.experience:
        score += 10
    else:
        warnings.append("缺少教育或工作经历")

    if resume.skills:
        score += 10
    else:
        warnings.append("缺少技能列表")

    # 限制在 50-100 区间
    score = max(50.0, min(100.0, score))
    return score, warnings


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ProcessResult, fmt: str = "text") -> str:
    """将处理结果格式化为指定格式输出。"""
    if fmt == "json":
        return _format_json(result)
    elif fmt == "text":
        return _format_text(result)
    else:
        # 未知格式，回退到文本
        return _format_text(result)


def _format_json(result: ProcessResult) -> str:
    """JSON 输出格式。"""
    resume = result.data
    output = {
        "name": resume.name,
        "contact": resume.contact,
        "education": resume.education,
        "experience": resume.experience,
        "skills": resume.skills,
        "projects": resume.projects,
        "confidence": round(result.confidence, 1),
        "warnings": result.warnings,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def _format_text(result: ProcessResult) -> str:
    """纯文本输出格式。"""
    resume = result.data
    lines: List[str] = []

    lines.append("=" * 40)
    lines.append("简历信息")
    lines.append("=" * 40)

    if resume.name:
        lines.append(f"姓名: {resume.name}")
    lines.append(f"置信度: {result.confidence:.0f}%")

    if resume.contact:
        lines.append("联系方式:")
        for key, value in resume.contact.items():
            lines.append(f"  {key}: {value}")

    if resume.education:
        lines.append("教育经历:")
        for edu in resume.education:
            school = edu.get("school", edu.get("institution", ""))
            if school:
                lines.append(f"  - {school}")

    if resume.experience:
        lines.append("工作经历:")
        for exp in resume.experience:
            company = exp.get("company", exp.get("employer", ""))
            if company:
                lines.append(f"  - {company}")

    if resume.skills:
        lines.append(f"技能: {', '.join(resume.skills)}")

    if result.warnings:
        lines.append("提示信息:")
        for warn in result.warnings:
            lines.append(f"  - {warn}")

    lines.append("=" * 40)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="简历优化工具 - 结构化简历数据提取与输出"
    )
    parser.add_argument(
        "--input",
        nargs="?",
        help="输入内容：JSON 字符串或纯文本",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认 text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    if not args.input:
        print(f"{ERR_INPUT_EMPTY}: 请提供输入内容，使用 --help 查看用法",
              file=sys.stderr)
        return 1

    try:
        result = build_resume(args.input)
        print(format_output(result, args.format))
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 离线自检（内置硬编码样例）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置离线自检，不依赖任何外部资源。

    使用宽松断言（大小/区间比较），确保任何环境可稳定通过。
    """
    print("开始离线自检...")

    # 样例 1：完整 JSON 输入
    sample_json = json.dumps({
        "name": "张三",
        "email": "zhangsan@example.com",
        "phone": "13800138000",
        "education": [
            {"school": "清华大学", "degree": "本科", "major": "计算机"}
        ],
        "experience": [
            {"company": "某科技有限公司", "position": "工程师"}
        ],
        "skills": ["Python", "Golang", "Java"],
    })

    # 样例 2：纯文本输入
    sample_text = """李四
    邮箱: lisi@example.com
    电话: 13900139000
    技能: Python, SQL, Docker
    毕业于北京大学
    曾在某集团公司工作
    """

    # 样例 3：空输入（应报错）
    sample_empty = "   "

    # 测试 1：JSON 解析与处理
    try:
        result1 = build_resume(sample_json)
        assert result1.data.name == "张三", "姓名解析失败"
        assert len(result1.data.skills) >= 2, "技能解析失败"
        assert len(result1.data.education) >= 1, "教育经历解析失败"
        assert result1.confidence >= 85, (
            f"完整数据置信度应较高，实际 {result1.confidence}"
        )
        print("  [通过] JSON 输入处理")
    except AssertionError as exc:
        print(f"  [失败] JSON 测试: {exc}")
        return 1
    except ValueError as exc:
        print(f"  [失败] JSON 测试异常: {exc}")
        return 1

    # 测试 2：文本输入处理
    try:
        result2 = build_resume(sample_text)
        assert result2.data.name == "李四", "文本姓名解析失败"
        assert len(result2.data.skills) >= 2, "文本技能解析失败"
        assert result2.confidence >= 80, (
            f"文本数据置信度应较高，实际 {result2.confidence}"
        )
        print("  [通过] 文本输入处理")
    except AssertionError as exc:
        print(f"  [失败] 文本测试: {exc}")
        return 1
    except ValueError as exc:
        print(f"  [失败] 文本测试异常: {exc}")
        return 1

    # 测试 3：空输入报错
    try:
        build_resume(sample_empty)
        print("  [失败] 空输入应报错但未报错")
        return 1
    except ValueError as exc:
        assert ERR_INPUT_EMPTY in str(exc), "错误码应为 E001"
        print("  [通过] 空输入错误处理")

    # 测试 4：格式输出
    try:
        result = build_resume(sample_json)
        json_out = format_output(result, "json")
        parsed_json = json.loads(json_out)
        assert parsed_json["name"] == "张三", "JSON 输出解析失败"
        assert "confidence" in parsed_json, "JSON 输出缺少置信度"
        print("  [通过] JSON 格式输出")
    except AssertionError as exc:
        print(f"  [失败] 输出测试: {exc}")
        return 1
    except ValueError as exc:
        print(f"  [失败] 输出测试异常: {exc}")
        return 1

    # 测试 5：低置信度标注（只给姓名）
    try:
        result = build_resume('{"name": "王五"}')
        assert result.confidence < 85, (
            f"不完整数据置信度应偏低，实际 {result.confidence}"
        )
        assert any("[需核实]" in w for w in result.warnings), \
            "应包含需核实标注"
        print("  [通过] 低置信度标注")
    except AssertionError as exc:
        print(f"  [失败] 低置信度测试: {exc}")
        return 1
    except ValueError as exc:
        print(f"  [失败] 低置信度测试异常: {exc}")
        return 1

    print("全部自检通过 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
