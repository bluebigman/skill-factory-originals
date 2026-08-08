import argparse
import json
import os
import sys
import tempfile
import re
from typing import Dict, List, Optional, Any

# --- 技能核心逻辑 ---

def generate_gzh_design(topic: str, style: str = "简洁", word_count: int = 800) -> Dict[str, Any]:
    """
    根据主题生成公众号文章的设计方案（标题、摘要、结构、视觉建议等）。
    这是一个离线模拟实现，用于演示和测试。
    """
    if not topic or not topic.strip():
        raise ValueError("主题不能为空")

    # 清洗主题
    clean_topic = topic.strip()

    # 生成标题（基于主题的简单规则）
    title = f"深度解析：{clean_topic}的底层逻辑与实战指南"

    # 生成摘要
    summary = f"本文围绕「{clean_topic}」展开，从核心概念到落地实践，为你提供一套完整的认知框架和操作步骤，助你快速掌握关键要点。"

    # 生成文章结构（模拟）
    sections = [
        {"heading": "一、为什么需要关注这个主题", "content": f"在当前环境下，{clean_topic} 已成为不可忽视的趋势。理解其本质，是做出正确决策的第一步。"},
        {"heading": "二、核心概念与常见误区", "content": f"很多人对 {clean_topic} 存在误解。我们首先厘清定义，再剖析三个最常见的认知偏差。"},
        {"heading": "三、实操步骤与案例分析", "content": f"通过一个具体案例，演示如何将 {clean_topic} 应用到实际工作中。步骤清晰，可立即上手。"},
        {"heading": "四、总结与行动清单", "content": "最后，给出一个简明的行动清单，帮助你立刻开始实践。"}
    ]

    # 视觉建议
    visual_tips = {
        "封面图": f"建议使用与 {clean_topic} 相关的抽象概念图，色调统一，避免花哨。",
        "排版": "正文使用 15px 字号，行间距 1.75，段间距 20px。重点内容加粗或使用引用块。",
        "配图": "每 300 字配一张信息图或示意图，增强可读性。"
    }

    # 根据风格调整标题（简单演示）
    if style == "幽默":
        title = f"别再说你不懂 {clean_topic}，这篇让你笑出腹肌还学会干货"
    elif style == "专业":
        title = f"专业视角：{clean_topic} 的系统性方法论"

    return {
        "title": title,
        "summary": summary,
        "sections": sections,
        "visual_tips": visual_tips,
        "word_count_estimate": word_count,
        "style": style
    }


def format_output(design: Dict[str, Any], format_type: str = "text") -> str:
    """将设计方案格式化为指定输出格式。"""
    if format_type == "json":
        return json.dumps(design, ensure_ascii=False, indent=2)
    elif format_type == "markdown":
        lines = [f"# {design['title']}", "", design["summary"], ""]
        for sec in design["sections"]:
            lines.append(f"## {sec['heading']}")
            lines.append(sec["content"])
            lines.append("")
        lines.append("## 视觉建议")
        for k, v in design["visual_tips"].items():
            lines.append(f"- **{k}**：{v}")
        return "\n".join(lines)
    else:  # text
        lines = [f"标题：{design['title']}", "", f"摘要：{design['summary']}", ""]
        for sec in design["sections"]:
            lines.append(f"{sec['heading']}")
            lines.append(sec["content"])
            lines.append("")
        lines.append("视觉建议：")
        for k, v in design["visual_tips"].items():
            lines.append(f"  - {k}：{v}")
        return "\n".join(lines)


# --- 自测功能 ---

def run_selftest() -> bool:
    """运行离线自测，确保核心功能正常。"""
    try:
        # 测试1：正常生成
        result = generate_gzh_design("人工智能", style="专业", word_count=1000)
        assert result["title"], "标题为空"
        assert len(result["sections"]) == 4, "章节数量不对"
        assert "封面图" in result["visual_tips"], "缺少视觉建议"

        # 测试2：不同风格
        result_humor = generate_gzh_design("编程", style="幽默")
        assert "笑出腹肌" in result_humor["title"], "幽默风格标题未生效"

        # 测试3：空主题异常
        try:
            generate_gzh_design("")
            assert False, "空主题未抛出异常"
        except ValueError:
            pass

        # 测试4：输出格式
        text_out = format_output(result, "text")
        json_out = format_output(result, "json")
        md_out = format_output(result, "markdown")
        assert "标题" in text_out, "文本格式缺少标题"
        assert json.loads(json_out)["title"], "JSON格式解析失败"
        assert md_out.startswith("# "), "Markdown格式错误"

        print("[SELFTEST] 全部通过")
        return True
    except Exception as e:
        print(f"[SELFTEST] 失败: {e}")
        return False


# --- 主入口 ---

def main():
    parser = argparse.ArgumentParser(description="公众号文章设计技能")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--topic", type=str, help="文章主题")
    parser.add_argument("--style", type=str, default="简洁", help="文章风格")
    parser.add_argument("--words", type=int, default=800, help="目标字数")
    parser.add_argument("--format", type=str, default="text", choices=["text", "json", "markdown"], help="输出格式")
    parser.add_argument("--output", type=str, help="输出文件路径（可选）")

    args = parser.parse_args()

    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    if not args.topic:
        print("错误：请提供 --topic 参数（文章主题）", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    try:
        design = generate_gzh_design(args.topic, style=args.style, word_count=args.words)
        output_text = format_output(design, args.format)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"已保存到 {args.output}")
        else:
            print(output_text)
    except Exception as e:
        print(f"生成失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
