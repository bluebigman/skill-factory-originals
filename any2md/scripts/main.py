#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
any2md - 文档转Markdown 结构化整理 格式转换
版本: 2.0.0 (clean-room 独立实现)
"""

import sys
import re
import argparse
import os
from typing import List, Tuple, Dict, Any


# ============================================================
# 错误码定义
# ============================================================
ERR_OK = 0
ERR_INPUT_EMPTY = "E001"      # 输入内容为空
ERR_INPUT_NOT_STRING = "E002" # 输入不是字符串
ERR_OUTPUT_FAIL = "E003"      # 输出写入失败
ERR_PARSE_FAIL = "E004"       # 解析失败
ERR_TABLE_FAIL = "E005"       # 表格转换失败
ERR_CODE_FAIL = "E006"        # 代码块处理失败
ERR_HEADING_FAIL = "E007"     # 标题处理失败
ERR_LINK_FAIL = "E008"        # 链接处理失败
ERR_LIST_FAIL = "E009"        # 列表处理失败
ERR_UNKNOWN = "E010"          # 未知错误


# ============================================================
# 核心转换逻辑
# ============================================================

def _detect_heading(line: str) -> Tuple[int, str]:
    """检测是否为Markdown标题，返回(级别, 标题内容)。非标题返回(0, 原行)。"""
    stripped = line.lstrip()
    if stripped.startswith('#'):
        # 计算 # 数量
        level = 0
        for ch in stripped:
            if ch == '#':
                level += 1
            else:
                break
        if 1 <= level <= 6 and (len(stripped) == level or stripped[level] in (' ', '\t')):
            content = stripped[level:].strip()
            return level, content
    return 0, line


def _detect_code_fence(line: str) -> bool:
    """检测是否为代码围栏开始/结束行。"""
    stripped = line.strip()
    return stripped.startswith('```')
