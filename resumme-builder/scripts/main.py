#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resumme-builder 简历优化工具

基于功能规格独立实现（clean-room），仅使用标准库。
功能：将输入的结构化简历数据转换为 HTML 模板渲染结果。
支持命令行参数：--selftest 离线自检，--input 输入文件，--output 输出文件。
"""

import argparse
import json
import sys
from html import escape

# 错误码常量定义
ERR_INPUT_EMPTY = "E001"          # 输入为空
ERR_KEY_MISSING = "E002"          # 关键信息缺失
ERR_FORMAT_BAD = "E003"           # 输入格式错误
ERR_OUT_OF_SCOPE = "E004"         # 超出能力边界
ERR_CONFIDENCE_LOW = "E005"       # 置信度过低
ERR_INTERNAL = "E006"             # 内部错误
ERR_FILE_READ = "E007"            # 文件读取失败
ERR_FILE_WRITE = "E008"           # 文件写入失败
ERR_JSON_PARSE = "E009"           # JSON 解析失败
ERR_UNKNOWN = "E010"              # 未知错误


def _error_message(code: str) -> str:
    """根据错误码返回标准化话术（对应规格中的错误码体系）。"""
    messages = {
        ERR_INPUT_EMPTY: "E001: 请提供待处理的内容，格式为：用户提供的数据/文件/URL",
        ERR_KEY_MISSING: "E002: 还缺少以下信息，请补充：...（逐项追问）",
        ERR_FORMAT_BAD: "E003: 输入格式不符合要求，示例：JSON 对象，需包含 name 字段",
        ERR_OUT_OF_SCOPE: "E004: 这超出了本工具的能力范围，建议咨询专业人士",
        ERR_CONFIDENCE_LOW: "E005: 结果无法确定，建议：人工复核关键字段",
        ERR_INTERNAL: "E006: 内部处理错误，请检查输入数据",
        ERR_FILE_READ: "E007: 文件读取失败，请检查路径和权限",
        ERR_FILE_WRITE: "E008: 文件写入失败，请检查路径和权限",
        ERR_JSON_PARSE: "E009: JSON 解析失败，请提供合法的 JSON 数据",
        ERR_UNKNOWN: "E010: 未知错误，请稍后重试",
    }
    return messages.get(code, messages[ERR_UNKNOWN])


def _validate_input(data: dict) -> None:
    """校验输入数据结构，不符合规格时抛出 ValueError（带错误码）。"""
    if not data:
        raise ValueError(_error_message(ERR_INPUT_EMPTY))

    # 关键字段检查：name 必须存在且非空字符串
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(_error_message(ERR_KEY_MISSING) + " 缺少 name 字段")

    # 类型检查：若存在 skills，必须是列表
    if "skills" in data and not isinstance(data["skills"], list):
        raise ValueError(_error_message(ERR_FORMAT_BAD) + " skills 字段必须是数组")

    # 类型检查：若存在 education，必须是列表
    if "education" in data and not isinstance(data["education"], list):
        raise ValueError(_error_message(ERR_FORMAT_BAD) + " education 字段必须是数组")


def _compute_confidence(data: dict) -> float:
    """根据输入数据完整度计算置信度（0~100）。"""
    score = 0.0
    total = 0.0

    # 每个关键字段按权重打分
    fields = {
        "name": 1.0,
        "email": 1.0,
        "phone": 1.0,
        "summary": 1.0,
        "skills": 1.0,
        "experience": 1.0,
        "education": 1.0,
    }

    for field, weight in fields.items():
        total += weight
        value = data.get(field)
        if value is not None and value != "" and value != []:
            score += weight

    if total == 0:
        return 0.0

    confidence = (score / total) * 100.0
    return round(confidence, 1)


def _render_html(data: dict) -> str:
    """将结构化数据渲染为 HTML 模板（纯标准库实现）。"""
    name = escape(data.get("name", "未知"))
    email = escape(data.get("email", ""))
    phone = escape(data.get("phone", ""))
    summary = escape(data.get("summary", ""))

    # 技能列表渲染
    skills = data.get("skills", [])
    skills_html = ""
    if skills:
        items = "".join(f"<li>{escape(str(s))}</li>" for s in skills)
        skills_html = f"<ul>{items}</ul>"

    # 教育经历渲染
    education = data.get("education", [])
    edu_html = ""
    if education:
        edu_blocks = []
        for edu in education:
            if isinstance(edu, dict):
                school = escape(str(edu.get("school", "")))
                degree = escape(str(edu.get("degree", "")))
                year = escape(str(edu.get("year", "")))
                edu_blocks.append(f"<p>{school} - {degree} ({year})</p>")
            else:
                edu_blocks.append(f"<p>{escape(str(edu))}</p>")
        edu_html = "".join(edu_blocks)

    # 工作经历渲染
    experience = data.get("experience", [])
    exp_html = ""
    if experience:
        exp_blocks = []
        for exp in experience:
            if isinstance(exp, dict):
                company = escape(str(exp.get("company", "")))
                title = escape(str(exp.get("title", "")))
                period = escape(str(exp.get("period", "")))
                exp_blocks.append(f"<p>{company} - {title} ({period})</p>")
            else:
                exp_blocks.append(f"<p>{escape(str(exp))}</p>")
        exp_html = "".join(exp_blocks)

    # 组装完整 HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>简历 - {name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        .contact {{ color: #7f8c8d; margin-bottom: 20px; }}
        .section {{ margin-bottom: 25px; }}
        ul {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <h1>{name}</h1>
    <div class="contact">
        {f"邮箱: {email}<br>" if email else ""}
        {f"电话: {phone}<br>" if phone else ""}
    </div>
    {f"<div class='section'><h2>个人简介</h2><p>{summary}</p></div>" if summary else ""}
    {f"<div class='section'><h2>技能</h2>{skills_html}</div>" if skills_html else ""}
    {f"<div class='section'><h2>工作经历</h2>{exp_html}</div>" if exp_html else ""}
    {f"<div class='section'><h2>教育经历</h2>{edu_html}</div>" if edu_html else ""}
</body>
</html>"""
    return html


def process_data(data: dict) -> dict:
    """核心处理流程：校验、计算置信度、渲染 HTML。

    返回结构：{"html": str, "confidence": float, "warning": str}
    """
    try:
        # Step 1: 输入校验
        _validate_input(data)

        # Step 2: 计算置信度
        confidence = _compute_confidence(data)

        # Step 3: 渲染 HTML
        html = _render_html(data)

        # Step 4: 根据置信度添加标注
        warning = ""
        if confidence < 85:
            warning = "[需核实] 部分字段缺失，结果仅供参考，请人工复核。"
        elif confidence < 90:
            warning = "建议复核：部分字段可能不完整。"

        return {
            "html": html,
            "confidence": confidence,
            "warning": warning,
        }

    except ValueError as e:
        # 将业务校验错误原样抛出（已带错误码）
        raise
    except Exception:
        # 其他异常统一转换为内部错误
        raise ValueError(_error_message(ERR_INTERNAL))


def _run_selftest() -> int:
    """离线自检：使用内置硬编码样例数据验证核心逻辑。

    不读取外部文件、不访问网络、不依赖当前工作目录。
    断言使用宽松阈值，避免精确值依赖。
    """
    print("=== resumme-builder 自检开始 ===")

    # 内置测试样例（硬编码，保证任何环境可运行）
    sample_data = {
        "name": "张三",
        "email": "zhangsan@example.com",
        "phone": "13800001234",
        "summary": "5年Python开发经验，专注于后端服务与数据处理。",
        "skills": ["Python", "Go", "SQL", "Docker"],
        "experience": [
            {"company": "某科技公司", "title": "高级工程师", "period": "2020-2023"},
            {"company": "某互联网公司", "title": "工程师", "period": "2018-2020"},
        ],
        "education": [
            {"school": "某大学", "degree": "本科", "year": "2018"},
        ],
    }

    # 测试1：正常处理应该成功
    try:
        result = process_data(sample_data)
        html = result["html"]
        confidence = result["confidence"]
        warning = result["warning"]
    except ValueError as e:
        print(f"[FAIL] 正常样例处理失败: {e}")
        return 1

    # 宽松断言：HTML 应包含关键字段
    assert "张三" in html, "HTML 未包含姓名"
    assert "Python" in html, "HTML 未包含技能"
    assert "某科技公司" in html, "HTML 未包含工作经历"
    assert "某大学" in html, "HTML 未包含教育经历"

    # 宽松断言：置信度应在合理区间（样例数据完整，应较高）
    assert confidence > 85, f"置信度异常偏低: {confidence}"
    assert confidence <= 100, f"置信度超过上限: {confidence}"

    # 宽松断言：warning 可以是空或字符串（不强制内容）
    assert isinstance(warning, str), "warning 类型错误"

    print(f"[PASS] 正常样例处理成功，置信度: {confidence}%")

    # 测试2：空输入应触发 E001
    try:
        process_data({})
        print("[FAIL] 空输入未触发 E001")
        return 1
    except ValueError as e:
        assert "E001" in str(e), f"错误码不是 E001: {e}"
        print("[PASS] 空输入正确触发 E001")

    # 测试3：缺少 name 字段应触发 E002
    try:
        process_data({"email": "test@test.com"})
        print("[FAIL] 缺少 name 未触发 E002")
        return 1
    except ValueError as e:
        assert "E002" in str(e), f"错误码不是 E002: {e}"
        print("[PASS] 缺少 name 正确触发 E002")

    # 测试4：类型错误应触发 E003
    try:
        process_data({"name": "测试", "skills": "not-a-list"})
        print("[FAIL] skills 类型错误未触发 E003")
        return 1
    except ValueError as e:
        assert "E003" in str(e), f"错误码不是 E003: {e}"
        print("[PASS] skills 类型错误正确触发 E003")

    # 测试5：不完整数据应给出低置信度提示
    try:
        incomplete = {"name": "李四"}
        result = process_data(incomplete)
        conf = result["confidence"]
        # 宽松断言：不完整数据置信度应显著低于完整数据
        assert conf < 85, f"不完整数据置信度应较低，实际: {conf}"
        assert "需核实" in result["warning"], "低置信度应包含 [需核实] 标注"
        print(f"[PASS] 不完整数据正确标注低置信度: {conf}%")
    except ValueError as e:
        print(f"[FAIL] 不完整数据处理失败: {e}")
        return 1

    # 测试6：HTML 转义安全性
    try:
        xss_data = {
            "name": "<script>alert('xss')</script>",
            "email": "test@test.com",
        }
        result = process_data(xss_data)
        html = result["html"]
        assert "<script>" not in html, "HTML 转义失败，存在 XSS 风险"
        assert "&lt;script&gt;" in html, "HTML 转义未正确执行"
        print("[PASS] HTML 转义安全")
    except ValueError as e:
        print(f"[FAIL] XSS 测试失败: {e}")
        return 1

    print("=== resumme-builder 自检全部通过 ===")
    return 0


def main() -> int:
    """主入口：解析命令行参数，执行相应操作。"""
    parser = argparse.ArgumentParser(
        description="resumme-builder 简历优化工具",
        epilog="示例: python main.py --input resume.json --output resume.html",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 文件路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出 HTML 文件路径（默认 stdout）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 处理模式：需要输入文件
    if not args.input:
        print(_error_message(ERR_INPUT_EMPTY), file=sys.stderr)
        return 1

    # 读取输入文件
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(_error_message(ERR_FILE_READ), file=sys.stderr)
        return 1
    except PermissionError:
        print(_error_message(ERR_FILE_READ), file=sys.stderr)
        return 1
    except Exception:
        print(_error_message(ERR_FILE_READ), file=sys.stderr)
        return 1

    # 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"{_error_message(ERR_JSON_PARSE)}: {e}", file=sys.stderr)
        return 1

    # 确保是字典类型
    if not isinstance(data, dict):
        print(_error_message(ERR_FORMAT_BAD), file=sys.stderr)
        return 1

    # 执行核心处理
    try:
        result = process_data(data)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    # 输出结果
    html = result["html"]
    confidence = result["confidence"]
    warning = result["warning"]

    if warning:
        print(f"提示: {warning}", file=sys.stderr)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"HTML 已写入: {args.output} (置信度: {confidence}%)")
        except Exception:
            print(_error_message(ERR_FILE_WRITE), file=sys.stderr)
            return 1
    else:
        print(html)

    return 0


if __name__ == "__main__":
    sys.exit(main())
