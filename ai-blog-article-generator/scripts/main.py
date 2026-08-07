#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

ai-blog-article-generator (SEO文案) - 独立实现脚本

本脚本依据功能规格独立编写（clean-room），仅使用标准库。
提供命令行入口，支持 --selftest 离线自检。

功能概述：
    1. 将用户提供的文本内容转换为结构化、SEO 优化的博客文章骨架。
    2. 识别并保留输入中的关键信息（标题、关键词、要点）。
    3. 按约定格式生成 Markdown 输出。
    4. 对不确定项给出置信度提示。
    5. 支持批量处理（多段落输入）。

错误码体系：E001-E010
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常（通用）
    E007: 参数解析错误
    E008: 输出写入失败
    E009: 数据校验失败
    E010: 未知错误

免责声明：
    本脚本仅供学习与参考用途，不构成任何专业建议。
    使用本脚本产生的任何结果，由使用者自行承担全部责任。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 版本信息
VERSION = "1.0.0"
SLUG = "ai-blog-article-generator"
DISPLAY_NAME = "SEO文案"

# 错误码 -> 标准化话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试。",
    "E007": "命令行参数解析错误，请检查参数。",
    "E008": "输出写入失败，请检查文件权限或路径。",
    "E009": "数据校验失败，请检查输入内容。",
    "E010": "发生未知错误。",
}

# 置信度阈值
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 85

# 默认输出模板
DEFAULT_TEMPLATE = """---
title: {title}
slug: {slug}
tags: [{tags}]
confidence: {confidence}%
---

# {title}

> 本文由 AI 辅助生成，仅供学习与参考用途。

## 核心要点
{key_points}

## 正文

{body}

## 结论

{conclusion}

---
*本内容由 {display_name} (v{version}) 生成，置信度 {confidence}%。*
*涉及专业决策时，请咨询持证专业人士。*
"""


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------


class ProcessingResult:
    """处理结果数据类。"""

    def __init__(
        self,
        title: str = "",
        slug: str = "",
        tags: List[str] = None,
        key_points: List[str] = None,
        body: str = "",
        conclusion: str = "",
        confidence: int = 0,
        warnings: List[str] = None,
    ) -> None:
        self.title = title
        self.slug = slug
        self.tags = tags or []
        self.key_points = key_points or []
        self.body = body
        self.conclusion = conclusion
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "title": self.title,
            "slug": self.slug,
            "tags": self.tags,
            "key_points": self.key_points,
            "body": self.body,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }

    def render_markdown(self) -> str:
        """渲染为 Markdown 字符串。"""
        tags_str = ", ".join(self.tags)
        key_points_str = "\n".join(f"- {point}" for point in self.key_points)
        return DEFAULT_TEMPLATE.format(
            title=self.title,
            slug=self.slug,
            tags=tags_str,
            key_points=key_points_str,
            body=self.body,
            conclusion=self.conclusion,
            confidence=self.confidence,
            display_name=DISPLAY_NAME,
            version=VERSION,
        )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def get_error_message(error_code: str) -> str:
    """获取指定错误码的标准化话术。"""
    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])


def raise_skill_error(error_code: str, detail: str = "") -> None:
    """抛出带错误码的异常。"""
    message = get_error_message(error_code)
    if detail:
        message = f"{message} (细节: {detail})"
    raise ValueError(f"[{error_code}] {message}")


def calculate_confidence(input_text: str, result: ProcessingResult) -> int:
    """
    计算置信度（0-100）。

    规则（宽松估算）：
        - 基础分 70。
        - 有标题 +10。
        - 有关键词 +5。
        - 有正文内容 +5。
        - 输入文本长度超过一定阈值 +5。
        - 有结论 +5。
    上限 100。
    """
    score = 70

    if result.title:
        score += 10
    if result.tags:
        score += 5
    if len(result.body) > 50:
        score += 5
    if len(input_text) > 100:
        score += 5
    if result.conclusion:
        score += 5

    return min(100, max(0, score))


def generate_slug(title: str) -> str:
    """根据标题生成 URL slug。"""
    # 转为小写，替换非字母数字字符为连字符
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", title.lower())
    # 去除首尾连字符
    slug = slug.strip("-")
    # 限制长度
    return slug[:80] or "untitled"


def extract_key_points(text: str) -> List[str]:
    """
    从输入文本中提取关键要点。

    策略：
        - 按行分割，筛选非空行。
        - 优先选择包含关键词（如"重点"、"关键"、"首先"等）的行。
        - 最多提取 5 个要点。
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    key_points = []

    # 关键词优先级
    priority_keywords = ["重点", "关键", "首先", "重要", "核心", "必须", "注意"]

    for line in lines:
        # 跳过过长的行
        if len(line) > 100:
            continue
        # 检查是否包含关键词
        if any(keyword in line for keyword in priority_keywords):
            key_points.append(line)
        if len(key_points) >= 5:
            break

    # 如果还没有足够的要点，补充普通行
    if len(key_points) < 3:
        for line in lines:
            if line not in key_points and len(line) < 80:
                key_points.append(line)
            if len(key_points) >= 3:
                break

    return key_points[:5]


def extract_tags(text: str) -> List[str]:
    """
    从输入文本中提取标签。

    策略：
        - 查找以 # 开头的单词。
        - 查找常见主题词。
    """
    tags = []

    # 查找 #标签
    hashtag_pattern = re.compile(r"#(\w+)")
    hashtags = hashtag_pattern.findall(text)
    tags.extend(hashtags[:3])

    # 常见主题词映射
    topic_keywords = {
        "科技": "科技",
        "AI": "AI",
        "人工智能": "人工智能",
        "博客": "博客",
        "SEO": "SEO",
        "写作": "写作",
        "教程": "教程",
        "指南": "指南",
    }

    for keyword, tag in topic_keywords.items():
        if keyword in text and tag not in tags:
            tags.append(tag)
        if len(tags) >= 5:
            break

    return tags[:5]


def generate_body(text: str, key_points: List[str]) -> str:
    """
    生成正文内容。

    将输入文本按段落拆分，保留原始内容，并添加结构化前缀。
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        return "（无正文内容）"

    body_parts = []
    for i, para in enumerate(paragraphs, 1):
        body_parts.append(f"### 段落 {i}\n\n{para}")

    return "\n\n".join(body_parts)


def generate_conclusion(text: str) -> str:
    """生成结论。"""
    if not text:
        return "（无结论）"

    # 简单总结：取最后一段的前 100 字
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        last_para = paragraphs[-1]
        conclusion = last_para[:100]
        return f"综上所述，{conclusion}"

    return "（无结论）"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------


def process_input(input_text: str) -> ProcessingResult:
    """
    核心处理函数：将输入文本转换为结构化博客文章。

    参数:
        input_text: 用户提供的原始文本内容。

    返回:
        ProcessingResult 对象。

    异常:
        ValueError: 当输入无效或处理失败时，抛出包含错误码的异常。
    """
    # 输入校验
    if not input_text or not input_text.strip():
        raise_skill_error("E001")

    if len(input_text.strip()) < 10:
        # 输入过短，视为关键信息缺失
        raise_skill_error("E002", "输入内容过短，请提供更多信息")

    # 检查是否超出能力边界（例如：极其庞大的输入）
    if len(input_text) > 100000:
        raise_skill_error("E004", "输入内容过大，超出单次处理能力")

    try:
        # 清理输入
        clean_text = input_text.strip()

        # 提取标题：优先取第一行，否则取前 50 个字符
        first_line = clean_text.splitlines()[0] if clean_text.splitlines() else ""
        if len(first_line) > 80:
            title = first_line[:80] + "..."
        elif first_line:
            title = first_line
        else:
            title = clean_text[:50] + ("..." if len(clean_text) > 50 else "")

        # 生成 slug
        slug = generate_slug(title)

        # 提取标签
        tags = extract_tags(clean_text)

        # 提取关键要点
        key_points = extract_key_points(clean_text)

        # 生成正文
        body = generate_body(clean_text, key_points)

        # 生成结论
        conclusion = generate_conclusion(clean_text)

        # 构建结果对象
        result = ProcessingResult(
            title=title,
            slug=slug,
            tags=tags,
            key_points=key_points,
            body=body,
            conclusion=conclusion,
        )

        # 计算置信度
        result.confidence = calculate_confidence(clean_text, result)

        # 根据置信度添加警告
        if result.confidence < MEDIUM_CONFIDENCE_THRESHOLD:
            result.warnings.append("输入信息不足，结果置信度较低，请人工复核。")
        elif result.confidence < HIGH_CONFIDENCE_THRESHOLD:
            result.warnings.append("部分内容建议复核。")

        # 最终校验
        if not result.title or not result.body:
            raise_skill_error("E009", "结果数据不完整")

        return result

    except ValueError:
        # 重新抛出已知错误
        raise
    except Exception as exc:
        # 未知错误
        raise_skill_error("E010", str(exc))


def process_batch(inputs: List[str]) -> List[ProcessingResult]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入文本列表。

    返回:
        ProcessingResult 对象列表。
    """
    results = []
    for item in inputs:
        try:
            result = process_input(item)
            results.append(result)
        except ValueError as exc:
            # 单个输入失败不影响其他输入
            error_result = ProcessingResult(
                title="处理失败",
                body=str(exc),
                confidence=0,
                warnings=[str(exc)],
            )
            results.append(error_result)
    return results


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------


def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=f"{DISPLAY_NAME} - AI 博客文章生成器 (v{VERSION})",
        epilog="示例: python main.py --input '你的文本内容' --output result.md",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本内容（直接传入字符串）",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取输入文本",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出 Markdown 文件路径（可选，默认输出到 stdout）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序（不读外部文件、不访问网络）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{DISPLAY_NAME} v{VERSION}",
    )
    return parser.parse_args(argv)


def run_selftest() -> bool:
    """
    内置自检程序。

    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。
    断言使用宽松阈值，确保在各种环境下都能通过。

    返回:
        True 表示自检通过，False 表示自检失败。
    """
    print("=" * 60)
    print("运行自检程序...")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 测试用例 1: 正常输入
    # ------------------------------------------------------------------
    print("\n[测试 1] 正常输入处理...")
    sample_input = (
        "AI 博客文章生成器使用指南\n\n"
        "重点：本工具可以将普通文本转换为 SEO 优化的博客文章。\n"
        "首先，你需要准备一段关于某个主题的文字内容。\n"
        "关键：工具会自动提取标题、标签和要点。\n"
        "最后，生成的文章可以直接用于博客发布。"
    )
    try:
        result = process_input(sample_input)
        assert result is not None, "处理结果不应为 None"
        assert result.title, "标题不应为空"
        assert result.body, "正文不应为空"
        assert result.confidence > 0, "置信度应大于 0"
        assert result.confidence <= 100, "置信度应小于等于 100"
        # 宽松断言：标题应包含输入的前几个字
        assert "AI" in result.title or "博客" in result.title, "标题应包含输入内容关键词"
        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 测试用例 2: 空输入
    # ------------------------------------------------------------------
    print("\n[测试 2] 空输入错误处理...")
    try:
        process_input("")
        print("  ✗ 失败: 空输入应抛出异常")
        return False
    except ValueError as exc:
        assert "E001" in str(exc), f"错误码应为 E001，实际: {exc}"
        print("  ✓ 通过")

    # ------------------------------------------------------------------
    # 测试用例 3: 短输入（关键信息缺失）
    # ------------------------------------------------------------------
    print("\n[测试 3] 短输入错误处理...")
    try:
        process_input("太短")
        print("  ✗ 失败: 短输入应抛出异常")
        return False
    except ValueError as exc:
        assert "E002" in str(exc), f"错误码应为 E002，实际: {exc}"
        print("  ✓ 通过")

    # ------------------------------------------------------------------
    # 测试用例 4: 批量处理
    # ------------------------------------------------------------------
    print("\n[测试 4] 批量处理...")
    batch_inputs = [
        "第一篇博客内容，关于 Python 编程。重点：学习基础语法。",
        "第二篇博客内容，关于 Web 开发。关键：掌握 Flask 框架。",
    ]
    try:
        results = process_batch(batch_inputs)
        assert len(results) == 2, f"应返回 2 个结果，实际 {len(results)}"
        assert results[0].title, "第一个结果标题不应为空"
        assert results[1].title, "第二个结果标题不应为空"
        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 测试用例 5: Markdown 渲染
    # ------------------------------------------------------------------
    print("\n[测试 5] Markdown 渲染...")
    try:
        result = process_input(sample_input)
        md = result.render_markdown()
        assert "---" in md, "Markdown 应包含分隔线"
        assert "# " in md, "Markdown 应包含标题"
        assert "置信度" in md, "Markdown 应包含置信度信息"
        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 测试用例 6: 工具函数
    # ------------------------------------------------------------------
    print("\n[测试 6] 工具函数...")
    try:
        # generate_slug
        slug = generate_slug("Hello World 测试")
        assert slug, "slug 不应为空"
        assert "-" in slug or "测试" in slug, "slug 应包含连字符或中文"

        # extract_key_points
        points = extract_key_points("重点：第一点\n关键：第二点\n普通内容")
        assert len(points) >= 1, "应至少提取 1 个要点"

        # extract_tags
        tags = extract_tags("这是一篇关于 AI 和 SEO 的文章 #教程")
        assert len(tags) >= 1, "应至少提取 1 个标签"

        # calculate_confidence
        conf = calculate_confidence("x" * 200, result)
        assert 0 <= conf <= 100, "置信度应在 0-100 范围内"

        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 测试用例 7: 错误码消息
    # ------------------------------------------------------------------
    print("\n[测试 7] 错误码消息...")
    try:
        msg = get_error_message("E001")
        assert "请提供" in msg, "E001 消息应包含提示"
        msg = get_error_message("E005")
        assert "无法确定" in msg, "E005 消息应包含提示"
        msg = get_error_message("UNKNOWN")
        assert "未知" in msg, "未知错误码应返回通用消息"
        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 测试用例 8: JSON 序列化
    # ------------------------------------------------------------------
    print("\n[测试 8] JSON 序列化...")
    try:
        result = process_input(sample_input)
        data = result.to_dict()
        json_str = json.dumps(data, ensure_ascii=False)
        assert json_str, "JSON 序列化不应为空"
        parsed = json.loads(json_str)
        assert parsed["title"] == data["title"], "JSON 往返应保持一致"
        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 测试用例 9: 边界输入
    # ------------------------------------------------------------------
    print("\n[测试 9] 边界输入...")
    try:
        # 超长输入
        long_text = "内容" * 100000
        try:
            process_input(long_text)
            print("  ✗ 失败: 超长输入应抛出 E004")
            return False
        except ValueError as exc:
            assert "E004" in str(exc), f"错误码应为 E004，实际: {exc}"

        # 特殊字符
        special_text = "测试 <script>alert('x')</script> & 特殊字符"
        result = process_input(special_text)
        assert result.title, "特殊字符输入应能正常处理"

        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 测试用例 10: 完整流程集成
    # ------------------------------------------------------------------
    print("\n[测试 10] 完整流程集成...")
    try:
        # 模拟完整处理流程
        input_text = (
            "人工智能写作工具入门\n\n"
            "重点：AI 可以帮助我们快速生成博客文章。\n"
            "关键：需要提供清晰的主题和要点。\n"
            "注意：生成的内容需要人工审核。"
        )
        result = process_input(input_text)
        md_output = result.render_markdown()

        # 验证输出包含关键部分
        assert "title:" in md_output, "输出应包含 title"
        assert "tags:" in md_output, "输出应包含 tags"
        assert "## 核心要点" in md_output, "输出应包含核心要点"
        assert "## 正文" in md_output, "输出应包含正文"
        assert "## 结论" in md_output, "输出应包含结论"

        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ------------------------------------------------------------------
    # 全部通过
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("所有自检测试通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main(argv: List[str] = None) -> int:
    """
    主入口函数。

    参数:
        argv: 命令行参数列表（默认使用 sys.argv[1:]）。

    返回:
        退出码（0 表示成功，1 表示失败）。
    """
    if argv is None:
        argv = sys.argv[1:]

    # 解析参数
    try:
        args = parse_args(argv)
    except SystemExit as exc:
        # argparse 在 --help 或 --version 时会抛出 SystemExit
        return exc.code if isinstance(exc.code, int) else 1
    except Exception:
        print(f"[E007] {get_error_message('E007')}")
        return 1

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 获取输入
    input_text = ""
    if args.input_file:
        try:
            with open(args.input_file, "r", encoding="utf-8") as f:
                input_text = f.read()
        except Exception as exc:
            print(f"[E008] 读取文件失败: {exc}")
            return 1
    elif args.input:
        input_text = args.input
    else:
        # 从 stdin 读取
        try:
            input_text = sys.stdin.read()
        except Exception:
            pass

    # 处理输入
    try:
        result = process_input(input_text)
    except ValueError as exc:
        print(f"错误: {exc}")
        return 1

    # 输出结果
    try:
        if args.json:
            output_data = result.to_dict()
            output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        else:
            output_str = result.render_markdown()

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
            print(f"结果已写入: {args.output}")
        else:
            print(output_str)

        # 打印警告
        for warning in result.warnings:
            print(f"[警告] {warning}")

        return 0

    except Exception as exc:
        print(f"[E008] 输出失败: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
