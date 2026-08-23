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
    python scripts/main.py --parse-structure <texfile>  # 解析论文结构

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
import tempfile
import threading
import time
import urllib.request
import urllib.error
from collections import OrderedDict
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

dry_run = False  # v3.268 模块级 dry-run 标志

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

# 常见 LaTeX 错误模式（支持多行上下文）
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

# 多行错误模式（用于捕获上下文）
MULTILINE_ERROR_PATTERNS = [
    (r"! LaTeX Error: (.*?)\n", "宏包/语法错误"),
    (r"! Undefined control sequence\.\n", "未定义的控制序列"),
    (r"! Package .*? Error: (.*?)\n", "宏包错误"),
    (r"! Missing \$ inserted\.\n", "数学模式错误"),
    (r"! Extra \}, or forgotten \$\.\n", "括号不匹配"),
    (r"! File .*? not found\.\n", "文件缺失"),
    (r"! Emergency stop\.\n", "紧急停止"),
    (r"! Argument of .*? has an extra \}\n", "参数错误"),
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

# 写作润色规则（增强版：包含语法、风格、学术表达检测）
POLISH_RULES = [
    # 缩写展开
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
    # 冗余词检测
    (r"\bvery\s+", "", "冗余词: very"),
    (r"\breally\s+", "", "冗余词: really"),
    (r"\bquite\s+", "", "冗余词: quite"),
    (r"\bbasically\s+", "", "冗余词: basically"),
    (r"\bactually\s+", "", "冗余词: actually"),
    # 被动语态检测（不替换，仅标记）
    (r"\b\w+ed\s+by\b", None, "被动语态检测"),
    # 学术表达改进
    (r"\bget\b", "obtain", "学术表达: get → obtain"),
    (r"\bgot\b", "obtained", "学术表达: got → obtained"),
    (r"\bgood\b", "effective", "学术表达: good → effective"),
    (r"\bbad\b", "poor", "学术表达: bad → poor"),
    (r"\bbig\b", "significant", "学术表达: big → significant"),
    (r"\bsmall\b", "minor", "学术表达: small → minor"),
    (r"\bshow\b", "demonstrate", "学术表达: show → demonstrate"),
    (r"\bshows\b", "demonstrates", "学术表达: shows → demonstrates"),
    (r"\bshowed\b", "demonstrated", "学术表达: showed → demonstrated"),
]

# 语法检测规则（新增）
GRAMMAR_RULES = [
    (r"\b(a)\s+([aeiou]\w+)", "冠词错误: a → an"),
    (r"\b(an)\s+([^aeiou\s]\w+)", "冠词错误: an → a"),
    (r"\b(is|are|was|were)\s+(\w+ed)\b", "被动语态建议"),
    (r"\b(has|have)\s+(\w+ed)\b", "完成时态检查"),
    (r"\b(does|do|did)\s+(\w+ed)\b", "助动词+过去式错误"),
]

# 学术表达检测规则（新增）
ACADEMIC_RULES = [
    (r"\b(a lot of)\b", "学术表达: a lot of → many/much"),
    (r"\b(lots of)\b", "学术表达: lots of → many/much"),
    (r"\b(kids)\b", "学术表达: kids → children"),
    (r"\b(guys)\b", "学术表达: guys → individuals"),
    (r"\b(stuff)\b", "学术表达: stuff → materials"),
    (r"\b(things)\b", "学术表达: things → items"),
    (r"\b(okay)\b", "学术表达: okay → acceptable"),
    (r"\b(fine)\b", "学术表达: fine → satisfactory"),
]

# 默认模板配置（完整且合法JSON）
DEFAULT_TEMPLATE_CONFIG = {
    "ieee": {
        "documentclass": "IEEEtran",
        "packages": ["cite", "amsmath", "amssymb", "graphicx", "textcomp"],
        "options": ["conference"],
        "bibstyle": "IEEEtran",
        "keywords": ["IEEEtran", "IEEE Transactions", "conference"]
    },
    "acm": {
        "documentclass": "acmart",
        "packages": ["amsmath", "amssymb", "graphicx"],
        "options": ["sigconf"],
        "bibstyle": "ACM-Reference-Format",
        "keywords": ["acmart", "ACM", "sigconf"]
    },
    "elsevier": {
        "documentclass": "elsarticle",
        "packages": ["amsmath", "amssymb", "graphicx"],
        "options": ["preprint"],
        "bibstyle": "elsarticle-num",
        "keywords": ["elsarticle", "Elsevier", "journal"]
    },
    "springer": {
        "documentclass": "svjour3",
        "packages": ["amsmath", "amssymb", "graphicx"],
        "options": [],
        "bibstyle": "spbasic",
        "keywords": ["svjour3", "Springer", "lncs"]
    },
    "nature": {
        "documentclass": "sn-jnl",
        "packages": ["amsmath", "amssymb", "graphicx"],
        "options": [],
        "bibstyle": "sn-mathphys-num",
        "keywords": ["sn-jnl", "Nature"]
    },
    "misc": {
        "documentclass": "article",
        "packages": ["amsmath", "amssymb", "graphicx"],
        "options": [],
        "bibstyle": "plain",
        "keywords": ["article", "report"]
    }
}

# ============================================================
# 工具函数
# ============================================================

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030", "latin-1"):
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


def err_exit(code: str, message: str = "") -> None:
    """输出错误信息并退出。"""
    desc = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[{code}] {desc}: {message}", file=sys.stderr)
    else:
        print(f"[{code}] {desc}", file=sys.stderr)
    sys.exit(1)


def read_text_file(filepath: str) -> str:
    """读取文本文件内容，支持 UTF-8 带/不带 BOM，带编码降级。"""
    if not os.path.exists(filepath):
        err_exit("E002", f"文件不存在: {filepath}")
    if not os.path.isfile(filepath):
        err_exit("E002", f"不是普通文件: {filepath}")
    
    # 尝试多种编码
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1"]
    last_error = None
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except PermissionError:
            err_exit("E003", f"权限不足: {filepath}")
        except Exception as e:
            err_exit("E003", f"读取失败: {e}")
    
    # 所有编码都失败，使用 replace 模式
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        err_exit("E005", f"无法解码文件: {filepath} - {last_error}")


def write_text_file(filepath: str, content: str) -> None:
    """原子写入文本文件，使用临时文件+os.replace。"""
    if dry_run:
        print(f"[DRY-RUN] 跳过写入: {filepath}")
        return
    
    # 确保目录存在
    dirname = os.path.dirname(filepath)
    if dirname and not os.path.exists(dirname):
        try:
            os.makedirs(dirname, exist_ok=True)
        except Exception as e:
            err_exit("E004", f"创建目录失败: {e}")
    
    # 原子写入
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dirname or ".", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except Exception as e:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass
        err_exit("E004", f"写入失败: {e}")


def is_tex_file(filepath: str) -> bool:
    """判断是否为 .tex 文件。"""
    return filepath.lower().endswith((".tex", ".ltx", ".dtx"))


def is_bib_file(filepath: str) -> bool:
    """判断是否为 .bib 文件。"""
    return filepath.lower().endswith(".bib")


def load_template_config(config_path: str = None) -> dict:
    """加载模板配置，支持外部JSON覆盖。"""
    config = json.loads(json.dumps(DEFAULT_TEMPLATE_CONFIG))  # 深拷贝
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            # 合并配置
            for tpl, cfg in user_config.items():
                if tpl in config:
                    config[tpl].update(cfg)
                else:
                    config[tpl] = cfg
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}", file=sys.stderr)
    
    return config


def get_timestamp() -> str:
    """获取UTC时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def http_request_with_retry(url: str, timeout: float = 10.0, max_retries: int = 3) -> str:
    """
    带重试退避和超时的HTTP请求。
    
    Args:
        url: 请求URL
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        
    Returns:
        响应内容
        
    Raises:
        RuntimeError: 所有重试都失败时
    """
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "awesome-latex-skills/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"HTTP请求失败（重试{max_retries}次）: {e}")
            # 指数退避
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    
    raise RuntimeError("HTTP请求失败")


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
        "timestamp": get_timestamp(),
    }
    
    lines = content.splitlines()
    current_line = 0
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 检测错误（单行模式）
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
        
        # 检测多行错误模式
        if i + 1 < len(lines):
            multi_line = line + "\n" + lines[i+1].strip()
            for pattern, err_type in MULTILINE_ERROR_PATTERNS:
                m = re.search(pattern, multi_line)
                if m:
                    detail = m.group(1) if m.lastindex else ""
                    error_entry = {
                        "line": current_line + 1,
                        "type": err_type,
                        "message": detail or line,
                        "context": lines[max(0, i-2):i+4],
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
