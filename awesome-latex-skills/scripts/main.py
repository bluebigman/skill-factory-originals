#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-latex-skills 独立实现脚本
=================================
基于功能规格的 clean-room 重写，提供 LaTeX 错误诊断、文档恢复、
文献阅读辅助、写作润色与投稿格式适配等核心能力。

用法:
    python scripts/main.py --selftest    # 离线自检
    python scripts/main.py --analyze-log <logfile>   # 分析编译日志
    python scripts/main.py --extract-bib <bibfile>   # 提取文献信息
    python scripts/main.py --restore-tex <texfile>   # 恢复损坏文档
    python scripts/main.py --polish <texfile>        # 润色建议
    python scripts/main.py --adapt <texfile> --template ieee   # 格式适配

错误码:
    E001: 参数错误
    E002: 文件不存在
    E003: 文件读取失败
    E004: 文件写入失败
    E005: 文件编码错误
    E006: 日志解析失败
    E007: 文献解析失败
    E008: 文档恢复失败
    E009: 模板适配失败
    E010: 未知错误
"""

import sys
import os
import re
import json
import argparse
from collections import OrderedDict
from datetime import datetime
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 常量定义
# ============================================================

ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "文件读取失败",
    "E004": "文件写入失败",
    "E005": "文件编码错误",
    "E006": "日志解析失败",
    "E007": "文献解析失败",
    "E008": "文档恢复失败",
    "E009": "模板适配失败",
    "E010": "未知错误",
}

# 常见 LaTeX 错误模式
COMMON_ERROR_PATTERNS = [
    (r"! LaTeX Error: (.*?)\.", "宏包/语法错误"),
    (r"! Undefined control sequence\.", "未定义的控制序列"),
    (r"! Package .*? Error: (.*?)\.", "宏包错误"),
    (r"! Missing \$ inserted\.", "数学模式错误"),
    (r"! Extra \}, or forgotten \$\.", "括号不匹配"),
    (r"! File .*? not found\.", "文件缺失"),
    (r"! Emergency stop\.", "紧急停止"),
    (r"! Argument of .*? has an extra \}", "参数错误"),
]

# 常见宏包冲突
COMMON_PACKAGE_CONFLICTS = [
    ("amsmath", "mathtools"),
    ("graphicx", "epsfig"),
    ("hyperref", "url"),
    ("algorithm", "algorithmic"),
    ("subfigure", "subcaption"),
    ("times", "mathptmx"),
]

# 投稿模板关键词
TEMPLATE_KEYWORDS = {
    "ieee": ["IEEEtran", "IEEE Transactions", "conference"],
    "acm": ["acmart", "ACM", "sigconf"],
    "elsevier": ["elsarticle", "Elsevier", "journal"],
    "springer": ["svjour3", "Springer", "lncs"],
    "nature": ["sn-jnl", "Nature"],
    "misc": ["article", "report"],
}

# 写作润色规则（简单启发式）
POLISH_RULES = [
    (r"\bdon't\b", "do not", "缩写展开"),
    (r"\bcan't\b", "cannot", "缩写展开"),
    (r"\bwon't\b", "will not", "缩写展开"),
    (r"\bI'm\b", "I am", "缩写展开"),
    (r"\bIt's\b", "It is", "缩写展开"),
    (r"\bit's\b", "it is", "缩写展开"),
    (r"\bwe're\b", "we are", "缩写展开"),
    (r"\bthey're\b", "they are", "缩写展开"),
    (r"\bisn't\b", "is not", "缩写展开"),
    (r"\baren't\b", "are not", "缩写展开"),
]


# ============================================================
# 工具函数
# ============================================================

def err_exit(code: str, message: str = "") -> None:
    """输出错误信息并退出。"""
    desc = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {desc}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {desc}", file=sys.stderr)
    sys.exit(1)


def read_text_file(filepath: str) -> str:
    """读取文本文件内容，支持 UTF-8 带/不带 BOM。"""
    if not os.path.exists(filepath):
        err_exit("E002", f"文件不存在: {filepath}")
    if not os.path.isfile(filepath):
        err_exit("E002", f"不是普通文件: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as f:
                return f.read()
        except Exception:
            err_exit("E005", f"无法解码文件: {filepath}")
    except PermissionError:
        err_exit("E003", f"权限不足: {filepath}")
    except Exception as e:
        err_exit("E003", f"读取失败: {e}")


def write_text_file(filepath: str, content: str) -> None:
    """写入文本文件。"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        err_exit("E004", f"写入失败: {e}")


def is_tex_file(filepath: str) -> bool:
    """判断是否为 .tex 文件。"""
    return filepath.lower().endswith((".tex", ".ltx", ".dtx"))


def is_bib_file(filepath: str) -> bool:
    """判断是否为 .bib 文件。"""
    return filepath.lower().endswith(".bib")


# ============================================================
# 核心功能实现
# ============================================================

def analyze_log(content: str) -> dict:
    """
    分析 LaTeX 编译日志，提取错误、警告和宏包信息。
    
    Args:
        content: 日志文件内容
        
    Returns:
        包含诊断结果的字典
    """
    result = {
        "errors": [],
        "warnings": [],
        "packages": [],
        "summary": "",
    }
    
    lines = content.splitlines()
    current_line = 0
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 检测错误
        for pattern, err_type in COMMON_ERROR_PATTERNS:
            m = re.search(pattern, line)
            if m:
                detail = m.group(1) if m.lastindex else ""
                error_entry = {
                    "line": current_line + 1,
                    "type": err_type,
                    "message": detail or line,
                    "context": lines[max(0, i-2):i+3],
                }
                result["errors"].append(error_entry)
                break
        
        # 检测警告
        if re.search(r"Warning|警告", line, re.IGNORECASE):
            result["warnings"].append({
                "line": current_line + 1,
                "message": line,
            })
        
        # 检测宏包加载
        pkg_match = re.search(r"Package: (\w+)", line)
        if pkg_match:
            pkg = pkg_match.group(1)
            if pkg not in result["packages"]:
                result["packages"].append(pkg)
        
        # 检测文件信息
        file_match = re.search(r"\(([^)]+\.tex)", line)
        if file_match:
            fname = file_match.group(1)
            if fname not in result["packages"]:
                result["packages"].append(fname)
        
        current_line += 1
        i += 1
    
    # 生成摘要
    err_count = len(result["errors"])
    warn_count = len(result["warnings"])
    result["summary"] = f"发现 {err_count} 个错误，{warn_count} 个警告"
    
    return result


def extract_bib_info(content: str) -> dict:
    """
    解析 .bib 文件，提取文献信息。
    
    Args:
        content: .bib 文件内容
        
    Returns:
        包含文献条目的字典
    """
    entries = []
    current_entry = None
    current_key = ""
    current_type = ""
    current_fields = {}
    
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        
        # 开始新条目
        m = re.match(r"@(\w+)\s*\{\s*([^,]+),", line)
        if m:
            # 保存前一个条目
            if current_entry:
                entries.append(current_entry)
            current_type = m.group(1).lower()
            current_key = m.group(2).strip()
            current_fields = {}
            current_entry = {
                "key": current_key,
                "type": current_type,
                "fields": current_fields,
            }
            continue
        
        # 解析字段
        if current_entry:
            fm = re.match(r"(\w+)\s*=\s*\{(.*?)\}", line)
            if fm:
                field_name = fm.group(1).lower()
                field_value = fm.group(2).strip()
                current_fields[field_name] = field_value
            elif line == "}":
                entries.append(current_entry)
                current_entry = None
    
    # 处理最后一条
    if current_entry:
        entries.append(current_entry)
    
    # 统计信息
    types = {}
    for e in entries:
        t = e["type"]
        types[t] = types.get(t, 0) + 1
    
    # 提取作者摘要
    authors = set()
    for e in entries:
        auth = e["fields"].get("author", "")
        for a in re.split(r"\s+and\s+", auth):
            a = a.strip()
            if a:
                authors.add(a)
    
    result = {
        "total": len(entries),
        "types": types,
        "authors": sorted(authors)[:20],
        "entries": entries,
    }
    
    return result


def restore_tex(content: str) -> dict:
    """
    从损坏/不完整的 .tex 文件中恢复可编译文档。
    
    Args:
        content: 原始文件内容
        
    Returns:
        包含恢复结果和修复建议的字典
    """
    issues = []
    fixes = []
    
    # 检查并修复文档类
    if not re.search(r"\\documentclass", content):
        issues.append("缺少 documentclass 声明")
        content = "\\documentclass{article}\n" + content
        fixes.append("添加默认 documentclass{article}")
    
    # 检查并修复 begin/end 配对
    for env in ["document", "equation", "figure", "table", "itemize", "enumerate"]:
        begin_count = len(re.findall(rf"\\begin\{{{env}\}}", content))
        end_count = len(re.findall(rf"\\end\{{{env}\}}", content))
        if begin_count > end_count:
            issues.append(f"环境 {env} 缺少 \\end{{{env}}}")
            content += f"\n\\end{{{env}}}\n"
            fixes.append(f"补充缺失的 \\end{{{env}}}")
        elif end_count > begin_count:
            issues.append(f"环境 {env} 缺少 \\begin{{{env}}}")
            content = f"\\begin{{{env}}}\n" + content
            fixes.append(f"补充缺失的 \\begin{{{env}}}")
    
    # 检查括号配对
    open_braces = content.count("{")
    close_braces = content.count("}")
    if open_braces > close_braces:
        diff = open_braces - close_braces
        issues.append(f"缺少 {diff} 个右花括号")
        content += "}" * diff
        fixes.append(f"补充 {diff} 个右花括号")
    elif close_braces > open_braces:
        diff = close_braces - open_braces
        issues.append(f"缺少 {diff} 个左花括号")
        content = "{" * diff + content
        fixes.append(f"补充 {diff} 个左花括号")
    
    # 检查数学模式
    math_dollars = content.count("$")
    if math_dollars % 2 != 0:
        issues.append("数学模式 $ 未配对")
        content += " $"
        fixes.append("补充数学模式结束符")
    
    # 检查是否缺少必要宏包
    if "\\usepackage" not in content:
        content = "\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath}\n" + content
        fixes.append("添加常用宏包 inputenc 和 amsmath")
    
    # 确保有 document 环境
    if "\\begin{document}" not in content:
        issues.append("缺少 \\begin{document}")
        content += "\n\\begin{document}\n"
        fixes.append("添加 \\begin{document}")
    if "\\end{document}" not in content:
        issues.append("缺少 \\end{document}")
        content += "\n\\end{document}\n"
        fixes.append("添加 \\end{document}")
    
    result = {
        "recovered": content,
        "issues": issues,
        "fixes": fixes,
        "recoverable": len(issues) > 0,
    }
    
    return result


def polish_writing(content: str) -> dict:
    """
    对 LaTeX 文档进行写作润色建议。
    
    Args:
        content: .tex 文件内容
        
    Returns:
        包含润色建议的字典
    """
    suggestions = []
    lines = content.splitlines()
    
    # 检查缩写
    for i, line in enumerate(lines):
        # 跳过注释和命令
        if line.strip().startswith("%"):
            continue
        for pattern, replacement, desc in POLISH_RULES:
            matches = re.findall(pattern, line, re.IGNORECASE)
            if matches:
                suggestions.append({
                    "line": i + 1,
                    "type": desc,
                    "original": line.strip(),
                    "suggestion": re.sub(pattern, replacement, line, flags=re.IGNORECASE),
                    "found": matches,
                })
    
    # 检查被动语态（简单启发式）
    passive_patterns = [
        (r"\bwas\s+(\w+ed)\b", "被动语态"),
        (r"\bwere\s+(\w+ed)\b", "被动语态"),
        (r"\bis\s+(\w+ed)\b", "被动语态"),
        (r"\bare\s+(\w+ed)\b", "被动语态"),
    ]
    for i, line in enumerate(lines):
        if line.strip().startswith("%"):
            continue
        for pattern, desc in passive_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            if matches:
                suggestions.append({
                    "line": i + 1,
                    "type": desc,
                    "original": line.strip(),
                    "suggestion": f"考虑改为主动语态: {line.strip()}",
                    "found": matches,
                })
    
    # 检查重复词
    for i, line in enumerate(lines):
        words = re.findall(r"\b(\w+)\b", line.lower())
        for j in range(len(words) - 1):
            if words[j] == words[j+1] and len(words[j]) > 2:
                suggestions.append({
                    "line": i + 1,
                    "type": "重复词",
                    "original": line.strip(),
                    "suggestion": f"删除重复的 '{words[j]}'",
                    "found": [words[j]],
                })
    
    # 统计
    stats = {
        "total_lines": len(lines),
        "total_words": sum(len(line.split()) for line in lines if not line.strip().startswith("%")),
        "suggestion_count": len(suggestions),
    }
    
    result = {
        "suggestions": suggestions,
        "stats": stats,
    }
    
    return result


def adapt_template(content: str, template: str) -> dict:
    """
    适配投稿模板格式。
    
    Args:
        content: .tex 文件内容
        template: 目标模板名称 (ieee/acm/elsevier/springer/nature/misc)
        
    Returns:
        包含适配结果的字典
    """
    template = template.lower()
    
    # 模板配置
    templates = {
        "ieee": {
            "documentclass": "IEEEtran",
            "packages": ["cite", "amsmath", "amssymb", "graphicx", "textcomp"],
            "options": ["conference"],
            "bibstyle": "IEEEtran",
        },
        "acm": {
            "documentclass": "acmart",
            "packages": ["amsmath", "amssymb", "graphicx"],
            "options": ["sigconf"],
            "bibstyle": "ACM-Reference-Format",
        },
        "elsevier": {
            "documentclass": "elsarticle",
            "packages": ["amsmath", "amssymb", "graphicx"],
            "options": ["preprint"],
            "bibstyle": "elsarticle-num",
        },
        "springer": {
            "documentclass": "svjour3",
            "packages": ["amsmath", "amssymb", "graphicx"],
            "options": [],
            "bibstyle": "spbasic",
        },
        "nature": {
            "documentclass": "sn-jnl",
            "packages": ["amsmath", "amssymb", "graphicx"],
            "options": [],
            "bibstyle": "sn-mathphys-num",
        },
        "misc": {
            "documentclass": "article",
            "packages": ["amsmath", "amssymb", "graphicx"],
            "options": [],
            "bibstyle": "plain",
        },
    }
    
    if template not in templates:
        err_exit("E009", f"不支持的模板: {template}")
    
    cfg = templates[template]
    changes = []
    
    # 替换 documentclass
    new_docclass = f"\\documentclass"
    if cfg["options"]:
        new_docclass += f"[{','.join(cfg['options'])}]"
    new_docclass += f"{{{cfg['documentclass']}}}"
    
    old_docclass_match = re.search(r"\\documentclass(\[[^\]]*\])?\{[^}]+\}", content)
    if old_docclass_match:
        content = content.replace(old_docclass_match.group(0), new_docclass)
        changes.append(f"替换文档类为 {cfg['documentclass']}")
    else:
        content = new_docclass + "\n" + content
        changes.append(f"添加文档类声明 {cfg['documentclass']}")
    
    # 清理已有宏包
    content = re.sub(r"\\usepackage(\[[^\]]*\])?\{[^}]+\}\n?", "", content)
    changes.append("清理原有宏包声明")
    
    # 添加模板所需宏包
    pkg_lines = []
    for pkg in cfg["packages"]:
        pkg_lines.append(f"\\usepackage{{{pkg}}}")
    pkg_text = "\n".join(pkg_lines) + "\n"
    
    # 在 documentclass 后插入宏包
    docclass_end = content.find("\n", content.find("\\documentclass"))
    if docclass_end == -1:
        docclass_end = len(content)
    content = content[:docclass_end+1] + "\n" + pkg_text + content[docclass_end+1:]
    changes.append(f"添加 {len(cfg['packages'])} 个模板宏包")
    
    # 处理 bibstyle
    bibstyle_match = re.search(r"\\bibliographystyle\{[^}]+\}", content)
    new_bibstyle = f"\\bibliographystyle{{{cfg['bibstyle']}}}"
    if bibstyle_match:
        content = content.replace(bibstyle_match.group(0), new_bibstyle)
        changes.append(f"替换参考文献样式为 {cfg['bibstyle']}")
    else:
        # 在 bibliography 前添加
        content = content.replace("\\begin{thebibliography}", 
                                  f"\\bibliographystyle{{{cfg['bibstyle']}}}\n\\begin{{thebibliography}}")
        changes.append(f"添加参考文献样式 {cfg['bibstyle']}")
    
    result = {
        "adapted": content,
        "template": template,
        "changes": changes,
        "change_count": len(changes),
    }
    
    return result


def detect_template(content: str) -> str:
    """检测文档当前使用的模板。"""
    content_lower = content.lower()
    for tpl, keywords in TEMPLATE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in content_lower:
                return tpl
    return "unknown"


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。
    
    Returns:
        True 表示全部通过
    """
    print("=" * 60)
    print("awesome-latex-skills 自检开始")
    print("=" * 60)
    
    all_passed = True
    
    # --- 测试 1: 日志分析 ---
    print("\n[测试 1] 日志分析")
    test_log = r"""
This is pdfTeX, Version 3.14159265 (TeX Live 2020)
LaTeX2e <2020-02-02> patch level 5
Package: amsmath 2020-01-20 v2.17
! LaTeX Error: File `missing.sty' not found.
l.12 \usepackage{missing}
! Undefined control sequence.
l.15 \unknowncommand
! Missing $ inserted.
l.18 \alpha + \beta
! Extra }, or forgotten $.
l.20 x = 2}
"""
    try:
        log_result = analyze_log(test_log)
        assert len(log_result["errors"]) >= 3, f"期望至少 3 个错误，实际 {len(log_result['errors'])}"
        assert "amsmath" in log_result["packages"], "应检测到 amsmath 宏包"
        assert log_result["summary"], "摘要不应为空"
        print(f"  ✓ 通过: 检测到 {len(log_result['errors'])} 个错误, {len(log_result['warnings'])} 个警告")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # --- 测试 2: 文献解析 ---
    print("\n[测试 2] 文献解析")
    test_bib = r"""
% 测试文献库
@article{knuth1984,
  author = {Knuth, Donald E. and others},
  title = {Literate Programming},
  journal = {The Computer Journal},
  year = {1984},
  volume = {27},
  pages = {97--111}
}

@book{lamport1994,
  author = {Lamport, Leslie},
  title = {LaTeX: A Document Preparation System},
  year = {1994},
  publisher = {Addison-Wesley}
}

@inproceedings{smith2020,
  author = {Smith, John and Doe, Jane},
  title = {A Test Paper},
  booktitle = {Proceedings of Test},
  year = {2020}
}
"""
    try:
        bib_result = extract_bib_info(test_bib)
        assert bib_result["total"] == 3, f"期望 3 条文献，实际 {bib_result['total']}"
        assert "article" in bib_result["types"], "应有 article 类型"
        assert "book" in bib_result["types"], "应有 book 类型"
        assert len(bib_result["authors"]) >= 3, "应提取到多个作者"
        print(f"  ✓ 通过: 解析 {bib_result['total']} 条文献, {len(bib_result['types'])} 种类型")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # --- 测试 3: 文档恢复 ---
    print("\n[测试 3] 文档恢复")
    test_broken_tex = r"""
\documentclass{article}
\begin{document}
Hello world
\begin{equation}
x = 1
"""
    try:
        restore_result = restore_tex(test_broken_tex)
        recovered = restore_result["recovered"]
        assert "\\end{document}" in recovered, "恢复后应包含 \\end{document}"
        assert "\\end{equation}" in recovered, "恢复后应包含 \\end{equation}"
        assert len(restore_result["issues"]) > 0, "应检测到问题"
        assert len(restore_result["fixes"]) > 0, "应提供修复建议"
        print(f"  ✓ 通过: 检测到 {len(restore_result['issues'])} 个问题, 提供 {len(restore_result['fixes'])} 个修复")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # --- 测试 4: 写作润色 ---
    print("\n[测试 4] 写作润色")
    test_paper = r"""
\documentclass{article}
\begin{document}
This paper don't use proper grammar.
It's a common mistake that can't be ignored.
The experiment was conducted by the team.
The data was analyzed carefully.
This is a very very long sentence.
\end{document}
"""
    try:
        polish_result = polish_writing(test_paper)
        assert len(polish_result["suggestions"]) >= 3, f"期望至少 3 条建议，实际 {len(polish_result['suggestions'])}"
        assert polish_result["stats"]["total_words"] > 0, "应统计到单词数"
        print(f"  ✓ 通过: 生成 {len(polish_result['suggestions'])} 条润色建议")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # --- 测试 5: 模板适配 ---
    print("\n[测试 5] 模板适配")
    test_tex = r"""
\documentclass[12pt]{article}
\usepackage{graphicx}
\usepackage{amsmath}
\begin{document}
\title{Test Paper}
\author{Author Name}
\maketitle
\section{Introduction}
This is a test.
\begin{thebibliography}{9}
\bibitem{ref1} Reference 1
\end{thebibliography}
\end{document}
"""
    try:
        adapt_result = adapt_template(test_tex, "ieee")
        adapted = adapt_result["adapted"]
        assert "IEEEtran" in adapted, "应替换为 IEEEtran 文档类"
        assert "\\bibliographystyle{IEEEtran}" in adapted, "应设置 IEEE 参考文献样式"
        assert adapt_result["change_count"] > 0, "应有变更记录"
        print(f"  ✓ 通过: 适配 IEEE 模板, {adapt_result['change_count']} 项变更")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # --- 测试 6: 模板检测 ---
    print("\n[测试 6] 模板检测")
    try:
        detected = detect_template(test_tex)
        assert detected == "misc", f"期望 misc，实际 {detected}"
        print(f"  ✓ 通过: 检测到模板 {detected}")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # --- 汇总 ---
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="awesome-latex-skills - LaTeX 排版错误修复与论文润色工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/main.py --selftest
  python scripts/main.py --analyze-log compile.log
  python scripts/main.py --extract-bib references.bib
  python scripts/main.py --restore-tex broken.tex
  python scripts/main.py --polish paper.tex
  python scripts/main.py --adapt paper.tex --template ieee
        """
    )
    
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--analyze-log", metavar="FILE", help="分析 LaTeX 编译日志")
    parser.add_argument("--extract-bib", metavar="FILE", help="提取 .bib 文献信息")
    parser.add_argument("--restore-tex", metavar="FILE", help="恢复损坏的 .tex 文档")
    parser.add_argument("--polish", metavar="FILE", help="对 .tex 文档进行润色建议")
    parser.add_argument("--adapt", metavar="FILE", help="适配投稿模板格式")
    parser.add_argument("--template", metavar="NAME", default="ieee",
                        choices=["ieee", "acm", "elsevier", "springer", "nature", "misc"],
                        help="目标模板 (默认: ieee)")
    parser.add_argument("--output", "-o", metavar="FILE", help="输出文件（默认输出到 stdout）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自检模式
    if args.selftest:
        ok = run_selftest()
        sys.exit(0 if ok else 1)
    
    # 检查是否有操作参数
    operations = [
        args.analyze_log,
        args.extract_bib,
        args.restore_tex,
        args.polish,
        args.adapt,
    ]
    if not any(operations):
        parser.print_help()
        err_exit("E001", "请指定操作参数")
    
    # 确保互斥
    active_ops = [op for op in operations if op]
    if len(active_ops) > 1:
        err_exit("E001", "一次只能执行一个操作")
    
    try:
        # 日志分析
        if args.analyze_log:
            content = read_text_file(args.analyze_log)
            result = analyze_log(content)
            
            # 输出错误详情
            print(f"分析结果: {result['summary']}")
            for err in result["errors"][:10]:
                print(f"  [行 {err['line']}] {err['type']}: {err['message']}")
            
            if args.json:
                output = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                output = json.dumps({
                    "summary": result["summary"],
                    "error_count": len(result["errors"]),
                    "warning_count": len(result["warnings"]),
                    "packages": result["packages"],
                }, ensure_ascii=False, indent=2)
        
        # 文献解析
        elif args.extract_bib:
            content = read_text_file(args.extract_bib)
            result = extract_bib_info(content)
            
            print(f"文献总数: {result['total']}")
            print(f"类型统计: {result['types']}")
            print(f"作者数: {len(result['authors'])}")
            
            if args.json:
                output = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                # 只输出摘要信息
                output = json.dumps({
                    "total": result["total"],
                    "types": result["types"],
                    "authors": result["authors"][:5],
                }, ensure_ascii=False, indent=2)
        
        # 文档恢复
        elif args.restore_tex:
            content = read_text_file(args.restore_tex)
            result = restore_tex(content)
            
            print(f"恢复状态: {'可恢复' if result['recoverable'] else '无需恢复'}")
            print(f"发现 {len(result['issues'])} 个问题:")
            for issue in result["issues"]:
                print(f"  - {issue}")
            print(f"提供 {len(result['fixes'])} 个修复:")
            for fix in result["fixes"]:
                print(f"  + {fix}")
            
            if args.output:
                write_text_file(args.output, result["recovered"])
                print(f"恢复内容已写入: {args.output}")
            
            output = json.dumps({
                "recoverable": result["recoverable"],
                "issues": result["issues"],
                "fixes": result["fixes"],
            }, ensure_ascii=False, indent=2)
        
        # 写作润色
        elif args.polish:
            content = read_text_file(args.polish)
            result = polish_writing(content)
            
            print(f"统计: {result['stats']['total_lines']} 行, {result['stats']['total_words']} 词, "
                  f"{result['stats']['suggestion_count']} 条建议")
            
            for sug in result["suggestions"][:20]:
                print(f"  [行 {sug['line']}] ({sug['type']})")
                print(f"    原文: {sug['original'][:80]}")
                print(f"    建议: {sug['suggestion'][:80]}")
            
            output = json.dumps(result, ensure_ascii=False, indent=2)
        
        # 模板适配
        elif args.adapt:
            content = read_text_file(args.adapt)
            result = adapt_template(content, args.template)
            
            print(f"适配模板: {result['template']}")
            print(f"变更数: {result['change_count']}")
            for change in result["changes"]:
                print(f"  * {change}")
            
            if args.output:
                write_text_file(args.output, result["adapted"])
                print(f"适配内容已写入: {args.output}")
            
            output = json.dumps({
                "template": result["template"],
                "changes": result["changes"],
                "change_count": result["change_count"],
            }, ensure_ascii=False, indent=2)
        
        else:
            err_exit("E001", "未知操作")
        
        # 输出结果
        if args.output:
            # 已写入文件
            pass
        elif args.json:
            print(output)
        
    except Exception as e:
        err_exit("E010", str(e))


if __name__ == "__main__":
    main()
