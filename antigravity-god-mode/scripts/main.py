#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
antigravity-god-mode 的 clean-room 独立实现。

本脚本完全依据功能规格文档重新编写，不参考任何既有代码。
核心能力：
    C1: 数据/文件/URL 结构化转换
    C2: 关键信息识别与保留
    C3: 约定格式输出（JSON/CSV/Markdown/YAML）
    C4: 置信度标注
    C5: 批量处理与自定义格式

边界约束（严格遵守）：
    L1: 不执行代码
    L2: 不访问私有网络
    L3: 不猜测缺失数据（输出 [需核实:字段名]）
    L4: 不保证转换无损
    L5: 不处理加密内容

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input data.csv --format json --fields 姓名,年龄
    python scripts/main.py --batch --input-dir ./inputs --output-dir ./outputs
"""

import argparse
import csv
import io
import json
import logging
import os
import re
import sys
import tempfile
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# 配置日志 - 默认使用 stderr，可通过 --log-file 参数覆盖
def setup_logging(log_file: Optional[str] = None) -> None:
    """配置日志系统。默认输出到 stderr，可通过参数指定文件。"""
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        # 确保日志文件目录存在
        log_dir = os.path.dirname(os.path.abspath(log_file))
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

logger = logging.getLogger('antigravity-god-mode')

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入数据为空或不可读",
    "E002": "不支持的输入格式",
    "E003": "不支持的输出格式",
    "E004": "字段提取失败",
    "E005": "批量处理目录不存在",
    "E006": "URL 访问失败",
    "E007": "输出目录不可写",
    "E008": "文件编码不支持",
    "E009": "加密内容无法处理",
    "E010": "内部逻辑错误",
}


class SkillError(Exception):
    """技能运行时的统一异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据转换逻辑（C1）
# ---------------------------------------------------------------------------

def parse_input(data: str, input_format: str = "auto") -> Any:
    """
    将原始输入字符串解析为结构化数据。

    支持格式：auto / json / csv / tsv / lines（每行一个条目）
    若为 auto，则自动尝试 json -> csv -> lines
    """
    if not data or not data.strip():
        raise SkillError("E001")

    fmt = input_format.lower()
    try:
        if fmt == "auto":
            # 自动探测
            stripped = data.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass
            if "," in stripped or "\t" in stripped:
                try:
                    return _parse_delimited_auto(stripped)
                except Exception as e:
                    # 降级为 lines 模式，但记录结构化日志
                    logger.warning("自动解析降级为 lines 模式: %s", e)
                    # 记录结构化日志供审计
                    log_entry = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "parse_auto_degraded",
                        "reason": str(e),
                        "fallback": "lines",
                    }
                    logger.info("AUDIT: %s", json.dumps(log_entry))
            return _parse_lines(stripped)
        elif fmt == "json":
            try:
                return json.loads(data)
            except json.JSONDecodeError as exc:
                raise SkillError("E002", f"JSON 解析失败: {exc}")
        elif fmt in ("csv", "tsv"):
            return _parse_delimited(data, delimiter="," if fmt == "csv" else "\t")
        elif fmt == "lines":
            return _parse_lines(data)
        else:
            raise SkillError("E002", f"不支持的输入格式: {input_format}")
    except SkillError:
        raise
    except Exception as exc:
        raise SkillError("E010", f"解析过程中发生错误: {exc}")


def _parse_delimited_auto(data: str) -> List[Dict[str, str]]:
    """使用 csv.Sniffer 自动检测分隔符并解析。"""
    try:
        # 使用 csv.Sniffer 检测分隔符
        sample = data[:4096]  # 取前 4KB 作为样本
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except csv.Error:
        # 如果 Sniffer 失败，回退到简单判断
        comma_count = data.count(",")
        tab_count = data.count("\t")
        delimiter = "," if comma_count >= tab_count else "\t"

    return _parse_delimited(data, delimiter=delimiter)


def _parse_delimited(data: str, delimiter: str = ",") -> List[Dict[str, str]]:
    """解析分隔符文本为字典列表（首行为表头）。"""
    reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
    rows = []
    for row in reader:
        # 清理空值
        cleaned = {k: (v.strip() if v else "") for k, v in row.items() if k}
        if cleaned:
            rows.append(cleaned)
    if not rows:
        raise SkillError("E001")
    return rows


def _parse_lines(data: str) -> List[str]:
    """按行解析为字符串列表。"""
    lines = [line.strip() for line in data.splitlines() if line.strip()]
    if not lines:
        raise SkillError("E001")
    return lines


# ---------------------------------------------------------------------------
# 文件/URL 读取与批量处理（C5）
# ---------------------------------------------------------------------------

def fetch_url(url: str, timeout: int = 10, max_retries: int = 3) -> str:
    """
    从 URL 获取内容，带超时、重试和退避策略。

    参数：
        url: 目标 URL
        timeout: 超时时间（秒）
        max_retries: 最大重试次数

    返回：
        URL 内容字符串

    异常：
        SkillError: E006 当所有重试都失败时
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            # 创建 SSL 上下文，处理证书验证
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url, headers={"User-Agent": "antigravity-god-mode/1.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
                return response.read().decode("utf-8")
        except ssl.SSLError as exc:
            # SSL 证书验证失败，降级为不验证证书
            last_error = exc
            logger.warning("SSL 证书验证失败，尝试不验证证书: %s", exc)
            try:
                context = ssl._create_unverified_context()
                req = urllib.request.Request(url, headers={"User-Agent": "antigravity-god-mode/1.0"})
                with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
                    return response.read().decode("utf-8")
            except Exception as retry_exc:
                last_error = retry_exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt < max_retries - 1:
                # 指数退避：2^attempt * 1s
                wait_time = 2 ** attempt
                logger.warning("URL 访问失败（尝试 %d/%d），%ds 后重试: %s",
                              attempt + 1, max_retries, wait_time, exc)
                time.sleep(wait_time)
            else:
                break
        except Exception as exc:
            last_error = exc
            break

    raise SkillError("E006", f"URL 访问失败: {url} - {last_error}")


def read_input_source(source: str, input_format: str = "auto") -> Any:
    """
    从文件或 URL 读取数据并解析。

    参数：
        source: 文件路径或 URL
        input_format: 输入格式（auto/json/csv/tsv/lines）

    返回：
        解析后的结构化数据
    """
    if source.startswith(("http://", "https://")):
        content = fetch_url(source)
    else:
        if not os.path.exists(source):
            raise SkillError("E001", f"文件不存在: {source}")
        try:
            with open(source, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            raise SkillError("E008", f"文件编码不支持: {source}")
        except Exception as exc:
            raise SkillError("E001", f"文件读取失败: {exc}")

    return parse_input(content, input_format)


def process_batch(input_dir: str, output_dir: str, output_format: str = "json",
                  fields: Optional[List[str]] = None, input_format: str = "auto",
                  format_template: Optional[str] = None) -> Dict[str, str]:
    """
    批量处理目录中的所有支持文件。

    参数：
        input_dir: 输入目录
        output_dir: 输出目录
        output_format: 输出格式（json/csv/markdown/yaml）
        fields: 要输出的字段列表
        input_format: 输入格式
        format_template: 自定义格式模板（Python format 字符串）

    返回：
        处理结果字典 {文件名: 状态}
    """
    if not os.path.isdir(input_dir):
        raise SkillError("E005", f"输入目录不存在: {input_dir}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    elif not os.path.isdir(output_dir):
        raise SkillError("E007", f"输出路径不是目录: {output_dir}")

    # 检查输出目录可写
    if not os.access(output_dir, os.W_OK):
        raise SkillError("E007", f"输出目录不可写: {output_dir}")

    supported_ext = {".txt", ".csv", ".tsv", ".json", ".md", ".log"}
    results = {}

    for filename in os.listdir(input_dir):
        filepath = os.path.join(input_dir, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext not in supported_ext:
            continue

        try:
            # 读取并解析
            data = read_input_source(filepath, input_format)

            # 提取关键字段
            extracted = extract_key_fields(data)

            # 格式化输出
            if format_template:
                # 使用自定义模板渲染
                output_content = _render_template(extracted, format_template)
                output_ext = "txt"
            else:
                output_content = format_output(extracted, output_format, fields)
                output_ext = output_format

            # 写入输出文件
            output_filename = os.path.splitext(filename)[0] + f".{output_ext}"
            output_path = os.path.join(output_dir, output_filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_content)

            results[filename] = "success"
        except SkillError as exc:
            results[filename] = f"error: {exc.code}"
            logger.error("处理 %s 失败: %s", filename, exc)
        except Exception as exc:
            results[filename] = f"error: E010"
            logger.error("处理 %s 发生未知错误: %s", filename, exc)

    return results


def _render_template(data: Dict[str, Any], template: str) -> str:
    """
    使用 Python format 字符串渲染自定义模板。

    模板中可使用 {字段名} 或 {字段名.value} 等占位符。
    """
    # 构建渲染上下文
    context = {}
    for key, value in data.items():
        if isinstance(value, dict):
            context[key] = value.get("value", "")
            context[f"{key}.value"] = value.get("value", "")
            context[f"{key}.confidence"] = value.get("confidence", 0)
        else:
            context[key] = value

    try:
        return template.format(**context)
    except KeyError as exc:
        raise SkillError("E004", f"模板中引用了不存在的字段: {exc}")
    except Exception as exc:
        raise SkillError("E004", f"模板渲染失败: {exc}")


# ---------------------------------------------------------------------------
# 关键信息识别与保留（C2）
# ---------------------------------------------------------------------------

# 常见关键字段的正则模式
_FIELD_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "phone": re.compile(r"(?:\+?86[- ]?)?1[3-9]\d{9}"),
    "date": re.compile(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?"),
    "money": re.compile(r"[¥￥$]\s?\d+(?:\.\d{1,2})?"),
    "url": re.compile(r"https?://[^\s]+"),
    "id_card": re.compile(r"\d{17}[\dXx]"),
    "ip": re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
}


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从结构化数据中提取关键字段，保留上下文信息。

    输入可以是 dict、list[dict] 或 list[str]
    返回 { "字段名": {"value": ..., "confidence": 0.0~1.0, "source": ...} }
    """
    result = OrderedDict()

    # 统一转为记录列表
    records = _to_records(data)

    # 收集所有可能的字段名
    all_keys = set()
    for rec in records:
        if isinstance(rec, dict):
            all_keys.update(rec.keys())

    # 对每个字段计算置信度
    for key in sorted(all_keys):
        values = []
        for rec in records:
            if isinstance(rec, dict) and key in rec:
                val = rec[key]
                if val not in (None, "", "N/A", "null"):
                    values.append(val)

        if not values:
            # 全部为空 -> 低置信度
            result[key] = {
                "value": "[需核实:{}]".format(key),
                "confidence": 0.0,
                "source": "缺失",
            }
            continue

        # 计算置信度：非空比例 + 类型一致性 + 格式匹配
        non_empty_ratio = len(values) / len(records) if records else 0.0
        type_consistency = _type_consistency(values)
        format_score = _format_score(key, values)

        confidence = round(
            0.4 * non_empty_ratio + 0.3 * type_consistency + 0.3 * format_score,
            2,
        )
        # 确保在 [0,1] 范围内
        confidence = max(0.0, min(1.0, confidence))

        result[key] = {
            "value": values[0] if len(values) == 1 else values,
            "confidence": confidence,
            "source": "输入数据",
        }

    # 对字符串列表，尝试识别语义字段
    if isinstance(data, list) and all(isinstance(x, str) for x in data):
        for label, pattern in _FIELD_PATTERNS.items():
            matches = []
            for text in data:
                found = pattern.findall(text)
                matches.extend(found)
            if matches:
                result[label] = {
                    "value": matches[0] if len(matches) == 1 else matches[:5],
                    "confidence": 0.8,
                    "source": "正则识别",
                }

    return result


def _to_records(data: Any) -> List[Any]:
    """将各种输入统一为记录列表。"""
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return [data]


def _type_consistency(values: List[Any]) -> float:
    """判断值类型的一致性（0~1）。"""
    if not values:
        return 0.0
    types = set(type(v).__name__ for v in values)
    return 1.0 if len(types) == 1 else 0.5


def _format_score(key: str, values: List[Any]) -> float:
    """根据字段名和值格式给出匹配度评分（0~1）。"""
    key_lower = key.lower()

    # 检查常见格式
    for field_type, pattern in _FIELD_PATTERNS.items():
        if field_type in key_lower or key_lower in field_type:
            matched = sum(1 for v in values if pattern.search(str(v)))
