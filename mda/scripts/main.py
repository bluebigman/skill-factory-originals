#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mda - 数据编译 文档生成 批量转换

将数据源编译为标准化 Markdown 文档，支持批量处理与置信度标注。
仅依赖 Python 标准库实现。

用法示例:
    python main.py --selftest
    python main.py --input data.json --output out.md
    python main.py --input input_dir/ --output out_dir/ --batch
"""

import argparse
import csv
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib
import tempfile
import shutil
import sqlite3
import io
import urllib.request
import urllib.error
import threading

# 错误码定义
ERR_SUCCESS = 0
ERR_FILE_NOT_FOUND = "E001"
ERR_INVALID_FORMAT = "E002"
ERR_OUTPUT_WRITE_FAIL = "E003"
ERR_INVALID_INPUT = "E004"
ERR_BATCH_PARTIAL_FAIL = "E005"
ERR_DIR_NOT_EXIST = "E006"
ERR_URL_FETCH_FAIL = "E007"
ERR_TEMPLATE_INVALID = "E008"
ERR_EMPTY_DATA = "E009"
ERR_UNKNOWN = "E010"

# 支持的文件扩展名
SUPPORTED_EXTS = {'.json', '.csv', '.xml', '.txt', '.sqlite', '.db'}

# 文件锁管理器
_file_locks = {}
_file_locks_lock = threading.Lock()

def _get_file_lock(path):
    """获取文件锁（线程安全）"""
    with _file_locks_lock:
        if path not in _file_locks:
            _file_locks[path] = threading.Lock()
        return _file_locks[path]


class MDADataError(Exception):
    """MDA 数据编译异常基类"""
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _read_file_content(file_path):
    """统一文件读取入口，带文件锁和原子操作"""
    if not os.path.exists(file_path):
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    
    lock = _get_file_lock(str(file_path))
    with lock:
        # 读取原始字节
        with open(file_path, 'rb') as f:
            raw = f.read()
        
        # 尝试解码
        for enc in ("utf-8", "gbk", "gb18030"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        raise MDADataError(ERR_INVALID_FORMAT, f"无法解码文件: {file_path}")


def _iter_lines(path):
    """流式读取文件行（复用 _read_file_content 逻辑）"""
    content = _read_file_content(path)
    for line in content.splitlines():
        yield line


def read_json_file(file_path):
    """读取 JSON 文件并返回数据"""
    try:
        content = _read_file_content(file_path)
        return json.loads(content)
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except json.JSONDecodeError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"JSON 解析失败: {e}")


def read_csv_file(file_path):
    """读取 CSV 文件并返回字典列表（严格编码校验）"""
    try:
        content = _read_file_content(file_path)
        reader = csv.DictReader(io.StringIO(content))
        # 检查表头
        if reader.fieldnames is None or len(reader.fieldnames) == 0:
            raise MDADataError(ERR_INVALID_FORMAT, f"CSV 文件缺少表头: {file_path}")
        rows = list(reader)
        if len(rows) == 0:
            raise MDADataError(ERR_EMPTY_DATA, f"CSV 文件为空: {file_path}")
        return rows
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except PermissionError:
        raise MDADataError(ERR_INVALID_FORMAT, f"CSV 文件权限不足: {file_path}")
    except csv.Error as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"CSV 解析失败: {e}")
    except OSError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"CSV 文件读取失败: {e}")


def read_xml_file(file_path):
    """读取 XML 文件并转换为字典结构"""
    try:
        content = _read_file_content(file_path)
        root = ET.fromstring(content)

        def element_to_dict(element):
            """将 XML 元素递归转换为字典"""
            result = {}
            # 处理属性
            for attr_name, attr_val in element.attrib.items():
                result[f"@{attr_name}"] = attr_val

            # 处理子元素
            child_elements = list(element)
            if child_elements:
                for child in child_elements:
                    child_data = element_to_dict(child)
                    tag = child.tag
                    if tag in result:
                        # 同标签多元素转为列表
                        if isinstance(result[tag], list):
                            result[tag].append(child_data)
                        else:
                            result[tag] = [result[tag], child_data]
                    else:
                        result[tag] = child_data
            else:
                # 叶子节点取文本内容
                text = (element.text or "").strip()
                if text:
                    result["text"] = text

            return result

        return {root.tag: element_to_dict(root)}
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except PermissionError:
        raise MDADataError(ERR_INVALID_FORMAT, f"XML 文件权限不足: {file_path}")
    except ET.ParseError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"XML 解析失败: {e}")
    except OSError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"XML 文件读取失败: {e}")


def read_txt_file(file_path):
    """读取 TXT 文件为纯文本"""
    try:
        return _read_file_content(file_path)
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except PermissionError:
        raise MDADataError(ERR_INVALID_FORMAT, f"TXT 文件权限不足: {file_path}")
    except OSError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"TXT 文件读取失败: {e}")


def read_sqlite_file(file_path):
    """读取 SQLite 数据库文件（只读模式，验证表存在性）"""
    conn = None
    try:
        # 使用只读模式连接，避免资源泄漏
        conn = sqlite3.connect(f'file:{file_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            raise MDADataError(ERR_EMPTY_DATA, f"SQLite 数据库中没有表: {file_path}")
        
        result = {}
        for table in tables:
            table_name = table[0]
            # 验证表存在性
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if cursor.fetchone() is None:
                raise MDADataError(ERR_INVALID_FORMAT, f"表不存在: {table_name}")
            
            cursor.execute(f"SELECT * FROM {table_name}")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            result[table_name] = [dict(zip(columns, row)) for row in rows]
        
        return result
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except PermissionError:
        raise MDADataError(ERR_INVALID_FORMAT, f"SQLite 文件权限不足: {file_path}")
    except sqlite3.Error as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"SQLite 解析失败: {e}")
    except OSError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"SQLite 文件读取失败: {e}")
    finally:
        if conn:
            conn.close()


def read_remote_url(url, max_retries=3, timeout=10):
    """读取远程 URL 数据（支持 HTTP/HTTPS，带重试退避）"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise MDADataError(ERR_INVALID_INPUT, f"不支持的 URL 协议: {parsed.scheme}")

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'MDA-Client/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                data = response.read().decode("utf-8")

                if "json" in content_type:
                    return json.loads(data)
                elif "csv" in content_type:
                    reader = csv.DictReader(io.StringIO(data))
                    if reader.fieldnames is None or len(reader.fieldnames) == 0:
                        raise MDADataError(ERR_INVALID_FORMAT, f"CSV 数据缺少表头: {url}")
                    return list(reader)
                elif "xml" in content_type:
                    return ET.fromstring(data)
                else:
                    return data
        except urllib.error.URLError as e:
            if attempt == max_retries - 1:
                raise MDADataError(ERR_URL_FETCH_FAIL, f"URL 获取失败: {e}")
            time.sleep(2 ** attempt)  # 指数退避
        except Exception as e:
            if attempt == max_retries - 1:
                raise MDADataError(ERR_URL_FETCH_FAIL, f"URL 获取失败: {e}")
            time.sleep(2 ** attempt)  # 指数退避


def read_data_source(source):
    """根据数据源类型读取数据"""
    # 判断是否是 URL
    if source.startswith("http://") or source.startswith("https://"):
        return read_remote_url(source)

    # 判断本地文件
    if not os.path.exists(source):
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {source}")

    ext = Path(source).suffix.lower()
    if ext == ".json":
        return read_json_file(source)
    elif ext == ".csv":
        return read_csv_file(source)
    elif ext == ".xml":
        return read_xml_file(source)
    elif ext == ".txt":
        return read_txt_file(source)
    elif ext in (".sqlite", ".db"):
        return read_sqlite_file(source)
    else:
        raise MDADataError(ERR_INVALID_FORMAT, f"不支持的文件格式: {ext}")


def check_confidence(data):
    """
    置信度检查 - 对数据中的缺失值、类型不匹配进行标注
    返回 (标注后的数据, 置信度问题列表)
    """
    issues = []

    def annotate_recursive(obj, path=""):
        """递归检查并标注数据"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                annotate_recursive(value, current_path)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                annotate_recursive(item, f"{path}[{idx}]")
        elif obj is None:
            issues.append(f"{path}: 值为空")
        elif isinstance(obj, str) and not obj.strip():
            issues.append(f"{path}: 空字符串")
        elif isinstance(obj, (int, float)):
            # 数值范围检查（宽松）
            if isinstance(obj, float) and (obj != obj):  # NaN 检查
                issues.append(f"{path}: 非数值(NaN)")

    annotate_recursive(data)
    return data, issues


def format_value(value):
    """格式化值为 Markdown 友好字符串"""
    if value is None:
        return "*空*"
    elif isinstance(value, bool):
        return "是" if value else "否"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, dict):
        # 嵌套字典转为内联描述
        parts = [f"{k}: {format_value(v)}" for k, v in value.items()]
        return "; ".join(parts)
    elif isinstance(value, list):
        return ", ".join(format_value(v) for v in value)
    else:
        return str(value)


def dict_to_markdown_table(data, title="数据表"):
    """将字典列表转换为 Markdown 表格"""
    if not data:
        return f"## {title}\n\n*无数据*"

    # 收集所有键（保持顺序）
    all_keys = []
    for item in data:
        if isinstance(item, dict):
            for key in item.keys():
                if key not in all_keys:
                    all_keys.append(key)

    if not all_keys:
        return f"## {title}\n\n*无有效数据*"

    # 生成表头
    lines = [f"## {title}", ""]
    lines.append("| " + " | ".join(all_keys) + " |")
    lines.append("|" + "|".join(["---"] * len(all_keys)) + "|")

    # 生成数据行
    for item in data:
        if isinstance(item, dict):
            row = []
            for key in all_keys:
                row.append(format_value(item.get(key)))
            lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def dict_to_markdown_sections(data, title="数据详情"):
    """将字典转换为 Markdown 章节格式"""
    if not data:
        return f"## {title}\n\n*无数据*"

    lines = [f"## {title}", ""]

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"### {key}")
                lines.append("")
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    # 列表中的字典转为子表格
                    lines.append(dict_to_markdown_table(value, key))
                else:
                    lines.append(format_value(value))
                lines.append("")
            else:
                lines.append(f"- **{key}**: {format_value(value)}")
    elif isinstance(data, list):
        lines.append(dict_to_markdown_table(data, title))
    else:
        lines.append(format_value(data))

    return "\n".join(lines)


def generate_markdown(data, title="编译文档", include_confidence=True):
    """将数据编译为标准化 Markdown 文档"""
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 添加置信度检查
    if include_confidence:
        _, issues = check_confidence(data)
        if issues:
            lines.append("## 置信度提示")
            lines.append("")
            lines.append("> 以下字段存在数据质量问题，请核实：")
            lines.append(">")
            for issue in issues[:20]:  # 最多列出 20 条
                lines.append(f"> - [需核实:{issue}]")
            lines.append("")

    # 根据数据类型选择输出格式
    if isinstance(data, list):
        # 列表：可能是表格数据或嵌套对象
        if data and isinstance(data[0], dict):
            lines.append(dict_to_markdown_table(data))
        else:
            lines.append("## 数据列表")
            lines.append("")
            if data:
                for idx, item in enumerate(data, 1):
                    lines.append(f"{idx}. {format_value(item)}")
            else:
                lines.append("*无数据*")
    elif isinstance(data, dict):
        lines.append(dict_to_markdown_sections(data))
    else:
        lines.append("## 数据内容")
        lines.append("")
        lines.append(format_value(data))

    return "\n".join(lines)


def process_file(input_path, output_path, title=None, include_confidence=True):
    """处理单个文件：读取数据并生成 Markdown"""
    try:
        data = read_data_source(input_path)
        if title is None:
            title = Path(input_path).stem
        markdown = generate_markdown(data, title=title, include_confidence=include_confidence)
        
        # 写入输出文件（带锁）
        lock = _get_file_lock(str(output_path))
        with lock:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown)
            except OSError as e:
                raise MDADataError(ERR_OUTPUT_WRITE_FAIL, f"写入输出文件失败: {e}")
        
        return True, None
    except MDADataError as e:
        return False, str(e)
    except Exception as e:
        return False, f"未知错误: {e}"


def process_batch(input_dir, output_dir, max_workers=4, include_confidence=True, max_retries=2):
    """批量处理目录中的所有支持文件"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.exists() or not input_path.is_dir():
        raise MDADataError(ERR_DIR_NOT_EXIST, f"输入目录不存在: {input_dir}")
    
    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 收集所有支持
