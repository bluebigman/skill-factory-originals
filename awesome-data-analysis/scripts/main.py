#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-data-analysis 独立实现脚本
====================================
依据功能规格 clean-room 实现的数据分析与洞察工具。

功能：
  - 解析 CSV / JSON / 纯文本表格数据
  - 自动识别字段类型（数值 / 日期 / 分类）
  - 生成统计摘要（缺失值、均值、极值、唯一值等）
  - 输出 Markdown 表格 / JSON / CSV 格式
  - 生成简单的可视化配置（折线图 / 柱状图 JSON）
  - 批量处理多个文件（支持并发）
  - 内置离线自检（--selftest）

用法示例：
  python main.py --input data.csv --format md
  python main.py --input a.json --input b.csv --format json
  python main.py --selftest

错误码说明：
  E001 参数错误
  E002 文件不存在或不可读
  E003 文件格式不支持
  E004 数据解析失败
  E005 数据为空
  E006 字段类型识别失败
  E007 可视化配置生成失败
  E008 输出格式不支持
  E009 批量处理失败
  E010 内部未知错误
"""

import argparse
import csv
import io
import json
import os
import sys
import datetime
import hashlib
import urllib.request
import urllib.error
import time
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# 尝试导入 BeautifulSoup，若不可用则使用正则解析
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INVALID_ARGS = "E001"
ERR_FILE_READ = "E002"
ERR_FORMAT_UNSUPPORTED = "E003"
ERR_PARSE_FAILED = "E004"
ERR_EMPTY_DATA = "E005"
ERR_TYPE_INFER = "E006"
ERR_VISUAL_FAILED = "E007"
ERR_OUTPUT_FORMAT = "E008"
ERR_BATCH_FAILED = "E009"
ERR_UNKNOWN = "E010"

# 资源聚合配置
RESOURCE_INDEX_URLS = [
    "https://raw.githubusercontent.com/onurakpolat/awesome-analytics/master/README.md",
    "https://raw.githubusercontent.com/igorbarinov/awesome-data-engineering/master/README.md",
    "https://raw.githubusercontent.com/numetriclabz/awesome-db/master/README.md",
    "https://raw.githubusercontent.com/awesome-foss/awesome-sysadmin/master/README.md",
    "https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md",
]
RESOURCE_TIMEOUT = 10  # 秒
RESOURCE_MAX_RETRIES = 3
RESOURCE_RETRY_BACKOFF = 2  # 指数退避基数

# 预置静态索引（降级方案）
STATIC_RESOURCE_INDEX = [
    {"title": "Awesome Analytics", "url": "https://github.com/onurakpolat/awesome-analytics"},
    {"title": "Awesome Data Engineering", "url": "https://github.com/igorbarinov/awesome-data-engineering"},
    {"title": "Awesome Databases", "url": "https://github.com/numetriclabz/awesome-db"},
    {"title": "Awesome Sysadmin", "url": "https://github.com/awesome-foss/awesome-sysadmin"},
    {"title": "Awesome Selfhosted", "url": "https://github.com/awesome-selfhosted/awesome-selfhosted"},
]


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------

def _err(msg, code=ERR_UNKNOWN):
    """统一错误输出，返回错误码。"""
    sys.stderr.write(f"[{code}] {msg}\n")
    return code


def _read_file_text(filepath):
    """读取文本文件，尝试常见编码。成功返回字符串，失败返回 None。"""
    if not os.path.isfile(filepath):
        return None
    for enc in ("utf-8", "gbk", "ascii"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    return None


def _parse_csv_text(text):
    """解析 CSV 文本为列表字典。"""
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        # 去除空键
        clean = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k and k.strip()}
        if clean:
            rows.append(clean)
    return rows


def _parse_json_text(text):
    """解析 JSON 文本为列表字典。"""
    data = json.loads(text)
    if isinstance(data, dict):
        # 尝试提取常见数组字段
        for key in ("data", "rows", "items", "records"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # 单条记录包装为列表
            data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON 顶层必须是数组或对象")
    rows = []
    for item in data:
        if isinstance(item, dict):
            rows.append({str(k): (str(v) if v is not None else "") for k, v in item.items()})
    return rows


def _infer_field_type(values):
    """
    根据一组字符串值推断字段类型。
    返回 "number" / "date" / "category" / "unknown"。
    使用宽松规则：多数值 -> number，多数日期 -> date，否则 category。
    """
    if not values:
        return "unknown"
    num_count = 0
    date_count = 0
    total = 0
    for v in values:
        s = str(v).strip()
        if not s:
            continue
        total += 1
        # 数值判断：宽松（允许逗号、百分号）
        try:
            float(s.replace(",", "").replace("%", "").replace("$", ""))
            num_count += 1
            continue
        except ValueError:
            pass
        # 日期判断：常见格式
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
            try:
                datetime.datetime.strptime(s, fmt)
                date_count += 1
                break
            except ValueError:
                continue
    if total == 0:
        return "unknown"
    if num_count / total >= 0.7:
        return "number"
    if date_count / total >= 0.7:
        return "date"
    return "category"


def _safe_float(v):
    """安全转浮点，失败返回 None。"""
    try:
        return float(str(v).replace(",", "").replace("%", "").replace("$", ""))
    except (ValueError, TypeError):
        return None


@lru_cache(maxsize=128)
def _get_file_cache_key(filepath):
    """生成文件缓存键（基于文件内容哈希）。"""
    text = _read_file_text(filepath)
    if text is None:
        return None
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _parse_markdown_links(content):
    """
    解析 Markdown 中的链接列表。
    支持标准格式: - [标题](链接) - 描述
    返回资源列表。
    """
    resources = []
    # 正则匹配 Markdown 链接
    pattern = r'^\s*[-*]\s+\[([^\]]+)\]\(([^)]+)\)(?:\s*[-–—]\s*(.*))?'
    for line in content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            title = match.group(1).strip()
            url = match.group(2).strip()
            desc = match.group(3).strip() if match.group(3) else ""
            if title and url:
                resources.append({
                    "title": title,
                    "url": url,
                    "description": desc
                })
    return resources


def _fetch_url_with_retry(url):
    """
    带超时和指数退避重试的 URL 获取。
    返回响应内容字符串，失败返回 None。
    """
    retries = 0
    last_error = None
    while retries < RESOURCE_MAX_RETRIES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "awesome-data-analysis/1.0"})
            with urllib.request.urlopen(req, timeout=RESOURCE_TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_error = e
            retries += 1
            if retries >= RESOURCE_MAX_RETRIES:
                print(f"[WARN] 网络请求失败（{retries}次重试后）: {url} - {e}", file=sys.stderr)
                return None
            # 指数退避
            backoff_time = RESOURCE_RETRY_BACKOFF ** retries
            print(f"[INFO] 网络请求失败，{backoff_time}秒后重试 ({retries}/{RESOURCE_MAX_RETRIES}): {url} - {e}", file=sys.stderr)
            time.sleep(backoff_time)
    return None


def _parse_resources_from_content(content, source_url):
    """
    从内容中解析资源列表。
    优先使用 BeautifulSoup，否则使用正则。
    返回资源列表。
    """
    resources = []
    if HAS_BS4:
        try:
            soup = BeautifulSoup(content, 'html.parser')
            for li in soup.find_all('li'):
                a = li.find('a', href=True)
                if a:
                    title = a.get_text(strip=True)
                    url = a['href']
                    desc = li.get_text(strip=True).replace(title, '', 1).strip()
                    if title and url:
                        resources.append({
                            "title": title,
                            "url": url,
                            "description": desc,
                            "source": source_url
                        })
        except Exception as e:
            print(f"[WARN] BeautifulSoup 解析失败，使用正则: {e}", file=sys.stderr)
            resources = _parse_markdown_links(content)
    else:
        # 使用正则解析
        resources = _parse_markdown_links(content)
    
    # 为资源添加来源信息
    for r in resources:
        r["source"] = source_url
    return resources


def _fetch_resource_index():
    """
    获取资源索引（多源聚合，带重试退避和超时）。
    返回资源列表或 None。
    """
    all_resources = []
    seen_urls = set()
    
    # 并发获取多个源
    with ThreadPoolExecutor(max_workers=min(5, len(RESOURCE_INDEX_URLS))) as executor:
        future_to_url = {executor.submit(_fetch_url_with_retry, url): url for url in RESOURCE_INDEX_URLS}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            content = future.result()
            if content:
                resources = _parse_resources_from_content(content, url)
                for r in resources:
                    if r['url'] not in seen_urls:
                        seen_urls.add(r['url'])
                        all_resources.append(r)
    
    # 如果聚合结果为空，使用静态索引
    if not all_resources:
        print("[WARN] 所有远程源获取失败，使用静态索引", file=sys.stderr)
        return STATIC_RESOURCE_INDEX
    
    # 去重并限制数量
    unique_resources = []
    seen = set()
    for r in all_resources:
        if r['url'] not in seen:
            seen.add(r['url'])
            unique_resources.append(r)
    
    print(f"[INFO] 聚合资源索引完成，共 {len(unique_resources)} 条资源", file=sys.stderr)
    return unique_resources[:500]  # 最多返回500条


# ---------------------------------------------------------------------------
# 数据分析核心逻辑
# ---------------------------------------------------------------------------

def analyze_rows(rows):
    """
    对行列表执行分析。
    返回 dict：字段摘要、统计信息、置信度。
    """
    if not rows:
        raise ValueError("数据为空")

    # 收集所有字段名
    fields = []
    for r in rows:
        for k in r.keys():
            if k not in fields:
                fields.append(k)

    if not fields:
        raise ValueError("无有效字段")

    # 字段统计
    field_stats = {}
    for f in fields:
        values = [r.get(f, "") for r in rows]
        non_empty = [v for v in values if str(v).strip() != ""]
        missing = len(values) - len(non_empty)
        unique_vals = set(str(v) for v in non_empty)
        ftype = _infer_field_type(non_empty)

        stat = {
            "field": f,
            "type": ftype,
            "missing": missing,
            "missing_ratio": round(missing / len(values), 2) if values else 0,
            "unique_count": len(unique_vals),
            "sample_values": list(unique_vals)[:5],
        }

        # 数值统计
        if ftype == "number":
            nums = [_safe_float(v) for v in non_empty]
            nums = [n for n in nums if n is not None]
            if nums:
                stat["min"] = min(nums)
                stat["max"] = max(nums)
                stat["mean"] = round(sum(nums) / len(nums), 2)
                stat["sum"] = round(sum(nums), 2)

        # 日期统计
        if ftype == "date":
            dates = []
            for v in non_empty:
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
                    try:
                        dates.append(datetime.datetime.strptime(str(v).strip(), fmt))
                        break
                    except ValueError:
                        continue
            if dates:
                stat["min_date"] = min(dates).strftime("%Y-%m-%d")
                stat["max_date"] = max(dates).strftime("%Y-%m-%d")

        field_stats[f] = stat

    # 整体置信度：根据缺失率估算
    total_missing = sum(s["missing"] for s in field_stats.values())
    total_cells = len(rows) * len(fields)
    missing_ratio = total_missing / total_cells if total_cells else 0
    confidence = max(0.1, min(0.99, 1.0 - missing_ratio))

    return {
        "row_count": len(rows),
        "field_count": len(fields),
        "fields": fields,
        "field_stats": field_stats,
        "confidence": round(confidence, 2),
        "summary": {
            "total_rows": len(rows),
            "total_fields": len(fields),
            "total_missing_cells": total_missing,
            "missing_ratio": round(missing_ratio, 2),
        },
    }


def generate_visual_config(analysis):
    """
    根据分析结果生成可视化配置 JSON。
    返回 dict 列表，每个含 type / title / data。
    """
    configs = []
    try:
        for fname, stat in analysis["field_stats"].items():
            if stat["type"] == "number":
                configs.append({
                    "type": "bar",
                    "title": f"{fname} 分布",
                    "data": {
                        "labels": [fname],
                        "values": [stat.get("mean", 0)],
                    },
                })
            elif stat["type"] == "date":
                configs.append({
                    "type": "line",
                    "title": f"{fname} 时间序列",
                    "data": {
                        "labels": [stat.get("min_date", ""), stat.get("max_date", "")],
                        "values": [1, 2],  # 简化示意
                    },
                })
            elif stat["type"] == "category":
                configs.append({
                    "type": "pie",
                    "title": f"{fname} 类别占比",
                    "data": {
                        "labels": stat["sample_values"][:5],
                        "values": [1] * min(5, len(stat["sample_values"])),
                    },
                })
        if not configs:
            raise ValueError("没有可可视化的字段")
        return configs
    except Exception as e:
        raise ValueError(f"可视化配置生成失败: {e}")


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_markdown(analysis, visual_configs=None):
    """输出 Markdown 报告。"""
    lines = []
    lines.append("# 数据分析报告")
    lines.append("")
    lines.append(f"- 总行数: {analysis['row_count']}")
    lines.append(f"- 总字段数: {analysis['field_count']}")
    lines.append(f"- 置信度: {analysis['confidence']}")
    lines.append("")
    lines.append("## 字段统计")
    lines.append("")
    lines.append("| 字段 | 类型 | 缺失数 | 缺失率 | 唯一值 | 均值 | 最小值 | 最大值 |")
    lines.append("|------|------|--------|--------|--------|------|--------|--------|")

    for fname, stat in analysis["field_stats"].items():
        mean = stat.get("mean", "-")
        minv = stat.get("min", "-")
        maxv = stat.get("max", "-")
        lines.append(
            f"| {fname} | {stat['type']} | {stat['missing']} | "
            f"{stat['missing_ratio']} | {stat['unique_count']} | {mean} | {minv} | {maxv} |"
        )

    if visual_configs:
        lines.append("")
        lines.append("## 可视化建议")
