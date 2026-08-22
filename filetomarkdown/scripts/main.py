#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filetomarkdown: 将用户提供的文件或链接转为结构化 Markdown，保留关键信息并标注置信度。
版本: 1.3.1
仅依据功能规格独立实现（clean-room）。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import socket
import urllib.request
import urllib.error
from pathlib import Path
import time
from datetime import datetime, timezone

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
_retry_timeout = 10  # 请求超时时间（秒）
_global_timeout = 30  # 全局超时上限（秒）

def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。
    对可重试错误（网络错误、5xx、429限流、超时）进行退避重试。
    设置全局超时上限，避免长时间阻塞。
    """
    start_time = time.time()
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except urllib.error.HTTPError as e:
            # HTTP错误：对5xx和429限流重试
            if (e.code >= 500 or e.code == 429) and attempt < _max_retry - 1:
                # 检查全局超时
                if time.time() - start_time > _global_timeout:
                    raise FileToMarkdownError(ERR_NETWORK, f"全局超时（{_global_timeout}秒）")
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # 网络错误/超时：重试
            if attempt < _max_retry - 1:
                # 检查全局超时
                if time.time() - start_time > _global_timeout:
                    raise FileToMarkdownError(ERR_NETWORK, f"全局超时（{_global_timeout}秒）")
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception as e:
            # 其他异常不重试
            raise

# 错误码定义
ERR_OK = 0
ERR_INPUT = "E001"       # 输入参数无效
ERR_FILE_NOT_FOUND = "E002"  # 文件不存在
ERR_FILE_TOO_LARGE = "E003"  # 文件超过大小限制
ERR_UNSUPPORTED_TYPE = "E004" # 不支持的文件类型
ERR_PARSE_FAILED = "E005"   # 内容解析失败
ERR_NETWORK = "E006"       # 网络访问失败
ERR_OUTPUT = "E007"        # 输出写入失败
ERR_INTERNAL = "E008"      # 内部逻辑错误
ERR_SELFTEST = "E009"      # 自检失败
ERR_URL_INVALID = "E010"   # URL 无效

# 常量
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".json"}
DEFAULT_CONFIDENCE = 0.95
LOW_CONFIDENCE = 0.6


class FileToMarkdownError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------- 核心解析函数 ----------

def parse_text_content(content: str) -> dict:
    """
    解析纯文本内容，提取段落、标题等。
    返回包含结构化信息的字典。
    改进：跳过代码块中的#，避免误判为标题。
    """
    if not content or not content.strip():
        return {"title": "空文档", "paragraphs": [], "headings": [], "confidence": LOW_CONFIDENCE}

    lines = content.splitlines()
    headings = []
    paragraphs = []
    current_para = []
    in_code_block = False

    # 改进的标题正则：要求 # 后至少一个空格，且不在代码块中
    heading_pattern = re.compile(r'^#{1,6}\s+(.*)$')

    for line in lines:
        stripped = line.strip()
        
        # 检测代码块开始/结束（
