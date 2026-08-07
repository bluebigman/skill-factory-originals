#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deeppapernote — 论文精读 Obsidian 笔记生成器（独立实现）

本脚本依据功能规格独立编写，不包含任何既有代码。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input paper.txt --template standard
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 未知错误
# E002: 输入参数无效
# E003: 文件读取失败
# E004: 文本解析失败
# E005: 模板生成失败
# E006: 输出写入失败
# E007: 输入为空
# E008: 批量输入超过限制
# E009: URL 格式无效
# E010: 自检失败
# ---------------------------------------------------------------------------

ERROR_CODES = {
    "E001": "未知错误",
    "E002": "输入参数无效",
    "E003": "文件读取失败",
    "E004": "文本解析失败",
    "E005": "模板生成失败",
    "E006": "输出写入失败",
    "E007": "输入为空",
    "E008": "批量输入超过限制（最多 5 篇）",
    "E009": "URL 格式无效",
    "E010": "自检失败",
}

MAX_BATCH_SIZE = 5  # 批量处理最多 5 篇

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class PaperInfo:
    """论文信息结构体"""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    institutions: List[str] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    core_method: str = ""
    experiments: List[str] = field(default_factory=list)
    results: List[str] = field(default_factory=list)
    conclusions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    personal_thoughts: str = ""
    citation: str = ""
    confidence_flags: List[str] = field(default_factory=list)  # 低置信度字段标记


@dataclass
class NoteConfig:
    """笔记生成配置"""
    template: str = "standard"  # standard / concise / detailed
    include_personal: bool = True
    include_limitations: bool = True
    include_citation: bool = True


# ---------------------------------------------------------------------------
# 核心逻辑：文本解析
# ---------------------------------------------------------------------------

def parse_paper_text(text: str) -> PaperInfo:
    """
    从纯文本中解析论文信息。
    支持常见的论文文本结构（标题、作者、摘要、关键词等）。
    使用宽松的启发式规则，不依赖精确格式。
    """
    if not text or not text.strip():
        raise ValueError("E007: 输入为空")

    paper = PaperInfo()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 标题：通常在第一行或前几行
    if lines:
        paper.title = lines[0][:200]  # 限制长度

    # 作者：常见模式 "作者: xxx" 或 "Authors: xxx"
    for i, line in enumerate(lines[:20]):
        lower = line.lower()
        if lower.startswith(("作者", "authors", "author", "by ")):
            raw = re.sub(r"^(作者|authors|author|by)\s*[:：]?\s*", "", line, flags=re.I)
            paper.authors = [a.strip() for a in re.split(r"[;,，、]", raw) if a.strip()][:10]
            break

    # 机构：常见模式 "机构" 或 "affiliation"
    for i, line in enumerate(lines[:30]):
        lower = line.lower()
        if lower.startswith(("机构", "affiliation", "institution", "单位")):
            raw = re.sub(r"^(机构|affiliation|institution|单位)\s*[:：]?\s*", "", line, flags=re.I)
            paper.institutions = [a.strip() for a in re.split(r"[;,，、]", raw) if a.strip()][:5]
            break

    # 摘要：常见模式 "摘要" 或 "abstract"
    for i, line in enumerate(lines):
        lower = line.lower()
        if lower.startswith(("摘要", "abstract")):
            # 收集后续行直到遇到下一个常见章节
            abstract_lines = []
            for j in range(i + 1, min(i + 30, len(lines))):
                if re.match(r"^(关键词|keywords|引言|introduction|方法|method|结论|conclusion)", lines[j], re.I):
                    break
                abstract_lines.append(lines[j])
            paper.abstract = " ".join(abstract_lines)[:2000]
            break

    # 关键词：常见模式 "关键词" 或 "keywords"
    for i, line in enumerate(lines[:50]):
        lower = line.lower()
        if lower.startswith(("关键词", "keywords", "关键字")):
            raw = re.sub(r"^(关键词|keywords|关键字)\s*[:：]?\s*", "", line, flags=re.I)
            paper.keywords = [k.strip() for k in re.split(r"[;,，、\s]+", raw) if k.strip()][:10]
            break

    # 核心方法：查找 "方法" 或 "method" 章节
    for i, line in enumerate(lines):
        if re.match(r"^(方法|method|方法论|approach)", line, re.I):
            method_lines = []
            for j in range(i + 1, min(i + 20, len(lines))):
                if re.match(r"^(实验|结果|结论|讨论|result|experiment|conclusion)", lines[j], re.I):
                    break
                method_lines.append(lines[j])
            paper.core_method = " ".join(method_lines)[:1500]
            break

    # 实验结果
    for i, line in enumerate(lines):
        if re.match(r"^(实验|结果|result|experiment)", line, re.I):
            result_lines = []
            for j in range(i + 1, min(i + 20, len(lines))):
                if re.match(r"^(结论|讨论|局限|conclusion|discussion|limitation)", lines[j], re.I):
                    break
                result_lines.append(lines[j])
            if result_lines:
                paper.results = [r[:300] for r in result_lines[:5]]
            break

    # 结论
    for i, line in enumerate(lines):
        if re.match(r"^(结论|conclusion|总结)", line, re.I):
            conclusion_lines = []
            for j in range(i + 1, min(i + 15, len(lines))):
                if re.match(r"^(局限|参考文献|reference|附录)", lines[j], re.I):
                    break
                conclusion_lines.append(lines[j])
            paper.conclusions = [c[:300] for c in conclusion_lines[:5]]
            break

    # 局限
    for i, line in enumerate(lines):
        if re.match(r"^(局限|limitation|不足)", line, re.I):
            limit_lines = []
            for j in range(i + 1, min(i + 10, len(lines))):
                if re.match(r"^(参考文献|reference|附录)", lines[j], re.I):
                    break
                limit_lines.append(lines[j])
            paper.limitations = [l[:300] for l in limit_lines[:5]]
            break

    # 置信度检查：如果某些关键字段缺失，标记为低置信度
    _check_confidence(paper)

    return paper


def _check_confidence(paper: PaperInfo) -> None:
    """检查字段完整性，标记低置信度字段"""
    if not paper.title:
        paper.confidence_flags.append("title")
    if not paper.authors:
        paper.confidence_flags.append("authors")
    if not paper.abstract:
        paper.confidence_flags.append("abstract")
    if not paper.keywords:
        paper.confidence_flags.append("keywords")
    if not paper.core_method:
        paper.confidence_flags.append("core_method")


# ---------------------------------------------------------------------------
# 模板生成
# ---------------------------------------------------------------------------

def generate_note(paper: PaperInfo, config: NoteConfig) -> str:
    """根据配置生成 Obsidian 风格 Markdown 笔记"""
    try:
        template_funcs = {
            "standard": _generate_standard,
            "concise": _generate_concise,
            "detailed": _generate_detailed,
        }
        if config.template not in template_funcs:
            raise ValueError(f"E002: 未知模板类型 '{config.template}'")

        return template_funcs[config.template](paper, config)
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"E005: 模板生成失败 - {str(e)}")


def _yaml_frontmatter(paper: PaperInfo) -> str:
    """生成 YAML frontmatter"""
    authors_str = ", ".join(paper.authors) if paper.authors else "未知"
    keywords_str = ", ".join(paper.keywords) if paper.keywords else "未提供"
    date_str = __import__("datetime").date.today().isoformat()

    lines = [
        "---",
        "title: \"" + paper.title + "\"",
        "authors: [" + authors_str + "]",
        "keywords: [" + keywords_str + "]",
        "date: " + date_str,
        "type: paper-note",
        "tags: [论文笔记, 文献阅读]",
        "---",
        "",
    ]
    return "\n".join(lines)


def _confidence_marker(paper: PaperInfo, field_name: str) -> str:
    """为低置信度字段添加标记"""
    if field_name in paper.confidence_flags:
        return " [需核实:" + field_name + "]"
    return ""


def _generate_standard(paper: PaperInfo, config: NoteConfig) -> str:
    """标准模板"""
    parts = [_yaml_frontmatter(paper)]

    # 元数据
    parts.append("## 📋 元数据")
    parts.append("- **标题**: " + paper.title + _confidence_marker(paper, "title"))
    parts.append("- **作者**: " + (", ".join(paper.authors) if paper.authors else "未知") + _confidence_marker(paper, "authors"))
    parts.append("- **机构**: " + (", ".join(paper.institutions) if paper.institutions else "未提供"))
    parts.append("- **关键词**: " + (", ".join(paper.keywords) if paper.keywords else "未提供") + _confidence_marker(paper, "keywords"))
    parts.append("")

    # 核心问题
    parts.append("## 🎯 核心问题")
    parts.append("本文主要解决：" + (paper.abstract[:200] if paper.abstract else "未明确提供") + _confidence_marker(paper, "abstract"))
    parts.append("")

    # 方法
    parts.append("## 🔬 方法")
    parts.append(paper.core_method if paper.core_method else "未提取到方法描述")
    parts.append("")

    # 结果
    parts.append("## 📊 实验结果")
    if paper.results:
        for r in paper.results:
            parts.append("- " + r)
    else:
        parts.append("未提取到实验结果")
    parts.append("")

    # 结论
    parts.append("## 💡 结论")
    if paper.conclusions:
        for c in paper.conclusions:
            parts.append("- " + c)
    else:
        parts.append("未提取到明确结论")
    parts.append("")

    # 局限
    if config.include_limitations:
        parts.append("## ⚠️ 局限")
        if paper.limitations:
            for l in paper.limitations:
                parts.append("- " + l)
        else:
            parts.append("未提取到局限说明")
        parts.append("")

    # 个人思考
    if config.include_personal:
        parts.append("## 💭 个人思考")
        parts.append("- 本文的亮点：")
        parts.append("- 可改进之处：")
        parts.append("- 与已有知识的关系：")
        parts.append("")

    # 引用
    if config.include_citation and paper.citation:
        parts.append("## 📚 引用")
        parts.append(paper.citation)
        parts.append("")

    return "\n".join(parts)


def _generate_concise(paper: PaperInfo, config: NoteConfig) -> str:
    """简洁模板"""
    parts = [_yaml_frontmatter(paper)]

    parts.append("## 核心信息")
    parts.append("- **标题**: " + paper.title)
    parts.append("- **作者**: " + (", ".join(paper.authors) if paper.authors else "未知"))
    parts.append("- **关键词**: " + (", ".join(paper.keywords) if paper.keywords else "未提供"))
    parts.append("")

    parts.append("## 方法")
    parts.append(paper.core_method if paper.core_method else "未提取到方法描述")
    parts.append("")

    parts.append("## 结论")
    if paper.conclusions:
        for c in paper.conclusions:
            parts.append("- " + c)
    else:
        parts.append("未提取到明确结论")

    return "\n".join(parts)


def _generate_detailed(paper: PaperInfo, config: NoteConfig) -> str:
    """详细模板"""
    parts = [_yaml_frontmatter(paper)]

    # 元数据
    parts.append("## 📋 元数据详情")
    parts.append("- **标题**: " + paper.title + _confidence_marker(paper, "title"))
    parts.append("- **作者**: " + (", ".join(paper.authors) if paper.authors else "未知") + _confidence_marker(paper, "authors"))
    parts.append("- **机构**: " + (", ".join(paper.institutions) if paper.institutions else "未提供"))
    parts.append("- **关键词**: " + (", ".join(paper.keywords) if paper.keywords else "未提供") + _confidence_marker(paper, "keywords"))
    parts.append("")

    # 摘要
    parts.append("## 📄 摘要")
    parts.append(paper.abstract if paper.abstract else "未提供摘要")
    parts.append("")

    # 核心问题
    parts.append("## 🎯 核心问题")
    parts.append("本文主要解决：" + (paper.abstract[:200] if paper.abstract else "未明确提供"))
    parts.append("")

    # 方法
    parts.append("## 🔬 方法详解")
    parts.append(paper.core_method if paper.core_method else "未提取到方法描述")
    parts.append("")

    # 实验结果
    parts.append("## 📊 实验结果")
    if paper.results:
        for r in paper.results:
            parts.append("- " + r)
    else:
        parts.append("未提取到实验结果")
    parts.append("")

    # 结论
    parts.append("## 💡 结论")
    if paper.conclusions:
        for c in paper.conclusions:
            parts.append("- " + c)
    else:
        parts.append("未提取到明确结论")
    parts.append("")

    # 局限
    if config.include_limitations:
        parts.append("## ⚠️ 局限与不足")
        if paper.limitations:
            for l in paper.limitations:
                parts.append("- " + l)
        else:
            parts.append("未提取到局限说明")
        parts.append("")

    # 个人思考
    if config.include_personal:
        parts.append("## 💭 个人思考")
        parts.append("- 本文的创新点：")
        parts.append("- 本文的局限性：")
        parts.append("- 改进建议：")
        parts.append("- 与已有知识的联系：")
        parts.append("- 未来研究方向：")
        parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 文件处理
# ---------------------------------------------------------------------------

def read_input_file(filepath: str) -> str:
    """读取输入文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"E003: 文件不存在 - {filepath}")
    except Exception as e:
        raise IOError(f"E003: 文件读取失败 - {str(e)}")


def write_output_file(filepath: str, content: str) -> None:
    """写入输出文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        raise IOError(f"E006: 输出写入失败 - {str(e)}")


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def process_batch(input_files: List[str], output_dir: str, config: NoteConfig) -> Dict[str, Any]:
    """批量处理多篇论文"""
    if len(input_files) > MAX_BATCH_SIZE:
        raise ValueError(f"E008: 批量输入超过限制（最多 {MAX_BATCH_SIZE} 篇）")

    results = {
        "success": [],
        "failed": []
    }

    for filepath in input_files:
        try:
            # 读取文件
            text = read_input_file(filepath)

            # 解析论文
            paper = parse_paper_text(text)

            # 生成笔记
            note_content = generate_note(paper, config)

            # 生成输出文件名
            basename = os.path.splitext(os.path.basename(filepath))[0]
            output_file = os.path.join(output_dir, basename + ".md")

            # 写入输出
            write_output_file(output_file, note_content)

            results["success"].append({
                "input": filepath,
                "output": output_file,
                "title": paper.title
            })

        except Exception as e:
            results["failed"].append({
                "input": filepath,
                "error": str(e)
            })

    return results


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """运行自检，验证功能完整性"""
    test_results = []
    
    # 测试1: 基本解析
    try:
        test_text = """深度学习在医学影像分析中的应用

作者: 张三, 李四, 王五
机构: 清华大学, 北京大学

摘要: 本文探讨了深度学习技术在医学影像分析中的应用，包括图像分割、病灶检测和疾病分类等方面。我们提出了一个基于卷积神经网络的创新方法，在多个公开数据集上取得了优异性能。

关键词: 深度学习, 医学影像, 卷积神经网络, 图像分割

方法: 我们使用了一种改进的U-Net架构，结合注意力机制和残差连接，用于医学图像分割任务。

实验: 在LUNA16数据集上进行了实验，Dice系数达到0.92。在BraTS数据集上，分割精度提升了15%。

结论: 实验结果表明，我们的方法在医学影像分析任务中具有显著优势，为临床诊断提供了有力支持。

局限: 我们的方法在计算资源需求方面较高，且在小样本场景下的泛化能力有待提升。
"""
        paper = parse_paper_text(test_text)
        assert paper.title, "标题解析失败"
        assert len(paper.authors) == 3, "作者解析失败"
        assert len(paper.keywords) >= 3, "关键词解析失败"
        assert paper.abstract, "摘要解析失败"
        assert paper.core_method, "方法解析失败"
        test_results.append(("基本解析测试", True, ""))
    except Exception as e:
        test_results.append(("基本解析测试", False, str(e)))

    # 测试2: 模板生成
    try:
        paper = PaperInfo(
            title="测试论文",
            authors=["测试作者"],
            keywords=["测试", "关键词"],
            abstract="这是一个测试摘要。",
            core_method="这是一个测试方法描述。",
            results=["结果1", "结果2"]
        )
        config = NoteConfig(template="standard")
        note = generate_note(paper, config)
        assert "## 📋 元数据" in note
        assert "测试论文" in note
        assert "测试作者" in note
        test_results.append(("标准模板生成测试", True, ""))
    except Exception as e:
        test_results.append(("标准模板生成测试", False, str(e)))

    # 测试3: 简洁模板
    try:
        paper = PaperInfo(
            title="测试论文",
            authors=["测试作者"],
            keywords=["测试"]
        )
        config = NoteConfig(template="concise")
        note = generate_note(paper, config)
        assert "## 核心信息" in note
        test_results.append(("简洁模板生成测试", True, ""))
    except Exception as e:
        test_results.append(("简洁模板生成测试", False, str(e)))

    # 测试4: 详细模板
    try:
        paper = PaperInfo(
            title="测试论文",
            authors=["测试作者"],
            keywords=["测试"],
            abstract="测试摘要",
            core_method="测试方法",
            results=["结果"],
            conclusions=["结论"],
            limitations=["局限"]
        )
        config = NoteConfig(template="detailed")
        note = generate_note(paper, config)
        assert "## 📋 元数据详情" in note
        assert "## 📄 摘要" in note
        test_results.append(("详细模板生成测试", True, ""))
    except Exception as e:
        test_results.append(("详细模板生成测试", False, str(e)))

    # 测试5: 空输入处理
    try:
        try:
            parse_paper_text("")
            test_results.append(("空输入处理测试", False, "应该抛出异常但未抛出"))
        except ValueError as e:
            assert "E007" in str(e)
            test_results.append(("空输入处理测试", True, ""))
    except Exception as e:
        test_results.append(("空输入处理测试", False, str(e)))

    # 测试6: 批量处理
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file1 = os.path.join(tmpdir, "test1.txt")
            test_file2 = os.path.join(tmpdir, "test2.txt")
            
            with open(test_file1, "w", encoding="utf-8") as f:
                f.write("测试论文1\n作者: 张三\n摘要: 这是第一篇测试论文")
            
            with open(test_file2, "w", encoding="utf-8") as f:
                f.write("测试论文2\n作者: 李四\n摘要: 这是第二篇测试论文")
            
            output_dir = os.path.join(tmpdir, "output")
            config = NoteConfig()
            
            results = process_batch([test_file1, test_file2], output_dir, config)
            assert len(results["success"]) == 2, "批量处理应成功处理2篇论文"
            assert len(results["failed"]) == 0, "批量处理不应有失败项"
            
            # 验证输出文件存在
            assert os.path.exists(os.path.join(output_dir, "test1.md"))
            assert os.path.exists(os.path.join(output_dir, "test2.md"))
            
            test_results.append(("批量处理测试", True, ""))
    except Exception as e:
        test_results.append(("批量处理测试", False, str(e)))

    # 测试7: 批量限制
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_files = []
            for i in range(6):  # 6个文件，超过限制
                test_file = os.path.join(tmpdir, f"test{i}.txt")
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(f"测试论文{i}")
                test_files.append(test_file)
            
            config = NoteConfig()
            try:
                process_batch(test_files, tmpdir, config)
                test_results.append(("批量限制测试", False, "应该抛出异常但未抛出"))
            except ValueError as e:
                assert "E008" in str(e)
                test_results.append(("批量限制测试", True, ""))
    except Exception as e:
        test_results.append(("批量限制测试", False, str(e)))

    # 测试8: 置信度标记
    try:
        paper = PaperInfo(title="")  # 缺少标题
        paper.confidence_flags = ["title"]
        marker = _confidence_marker(paper, "title")
        assert "需核实" in marker
        test_results.append(("置信度标记测试", True, ""))
    except Exception as e:
        test_results.append(("置信度标记测试", False, str(e)))

    # 输出测试结果
    print("=" * 60)
    print("自检测试结果")
    print("=" * 60)
    
    all_passed = True
    for name, passed, error in test_results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
        if error:
            print(f"  错误信息: {error}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    print(f"总结: {sum(1 for _, p, _ in test_results if p)}/{len(test_results)} 测试通过")
    
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="deeppapernote - 论文精读 Obsidian 笔记生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python scripts/main.py --selftest
  python scripts/main.py --input paper.txt --template standard
  python scripts/main.py --input paper1.txt paper2.txt --output-dir notes
"""
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--selftest", action="store_true", help="运行自检")
    group.add_argument("--input", nargs="+", help="输入文件路径（支持批量）")
    
    parser.add_argument("--template", choices=["standard", "concise", "detailed"], 
                       default="standard", help="笔记模板类型")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    parser.add_argument("--no-personal", action="store_true", help="不包含个人思考部分")
    parser.add_argument("--no-limitations", action="store_true", help="不包含局限部分")
    parser.add_argument("--no-citation", action="store_true", help="不包含引用部分")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"E010: 自检失败 - {str(e)}")
            return 1
    
    # 处理模式
    try:
        # 创建配置
        config = NoteConfig(
            template=args.template,
            include_personal=not args.no_personal,
            include_limitations=not args.no_limitations,
            include_citation=not args.no_citation
        )
        
        # 批量处理
        results = process_batch(args.input, args.output_dir, config)
        
        # 输出结果
        print(f"处理完成：{len(results['success'])} 篇成功，{len(results['failed'])} 篇失败")
        
        for item in results["success"]:
            print(f"✅ {item['input']} -> {item['output']}")
        
        for item in results["failed"]:
            print(f"❌ {item['input']}: {item['error']}")
        
        # 如果有失败项，返回错误码
        if results["failed"]:
            return 1
        
        return 0
        
    except ValueError as e:
        print(f"错误: {str(e)}")
        return 1
    except Exception as e:
        print(f"E001: 未知错误 - {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
