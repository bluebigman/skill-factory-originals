#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anime-dl 技能核心实现

将用户提供的动漫相关链接或数据，转换为结构化、可复用的规范输出。
仅依据功能规格独立实现（clean-room），不复制任何既有代码。

功能要点：
- 解析 URL、文本片段中的关键信息
- 识别标题、集数、画质、字幕组、发布时间等字段
- 将非结构化文本转为 JSON / Markdown 表格 / CSV
- 一次处理多条记录，保持字段一致性
- 对不确定字段标注 [需核实:字段名]

运行方式：
    python scripts/main.py --selftest
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERR_INVALID_INPUT = "E001"      # 输入为空或类型错误
ERR_INVALID_URL = "E002"        # URL 格式无效
ERR_NO_FIELDS = "E003"          # 无法从输入中提取任何字段
ERR_INVALID_FORMAT = "E004"     # 输出格式不受支持
ERR_INVALID_JSON = "E005"       # JSON 解析失败
ERR_INVALID_CSV = "E006"        # CSV 解析失败
ERR_FILE_NOT_FOUND = "E007"     # 文件不存在
ERR_FILE_READ = "E008"          # 文件读取失败
ERR_INTERNAL = "E009"           # 内部逻辑错误
ERR_SELFTEST = "E010"           # 自检失败


# ============================================================
# 常量定义
# ============================================================
SUPPORTED_FORMATS = ("json", "markdown", "csv")

# 常见字幕组关键词（用于识别）
SUBGROUP_KEYWORDS = [
    "字幕组", "字幕", "Sub", "sub", "CHT", "CHS", "BIG5", "GB",
    "DHR", "CASO", "KTXP", "YYDM", "FZSD", "Kamigami", "LoliHouse",
]

# 常见画质关键词（用于识别）
QUALITY_KEYWORDS = [
    "1080P", "1080p", "720P", "720p", "480P", "480p", "4K", "2160P",
    "BD", "BDRip", "WEB", "WEBRip", "HDR", "HDRip", "TV", "TVRip",
]


# ============================================================
# 工具函数
# ============================================================
def _now_timestamp() -> str:
    """返回当前时间戳字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _error(code: str, message: str) -> None:
    """统一错误输出"""
    raise RuntimeError(f"[{code}] {message}")


def _is_valid_url(url: str) -> bool:
    """检查 URL 格式是否基本有效"""
    pattern = re.compile(
        r"^(https?|ftp)://"
        r"([A-Za-z0-9-]+\.)+[A-Za-z]{2,}"
        r"(:\d+)?(/[^\s]*)?$"
    )
    return bool(pattern.match(url.strip()))


def _extract_episode(text: str) -> Optional[str]:
    """从文本中提取集数信息"""
    # 匹配形如 "第12集"、"EP12"、"ep.12"、"12话" 等
    patterns = [
        r"第\s*(\d+)\s*[集话話]",
        r"[Ee][Pp]\.?\s*(\d+)",
        r"(\d+)\s*[集话話]",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            return match.group(1)
    return None


def _extract_quality(text: str) -> Optional[str]:
    """从文本中提取画质信息"""
    for kw in QUALITY_KEYWORDS:
        if kw.lower() in text.lower():
            return kw
    return None


def _extract_subgroup(text: str) -> Optional[str]:
    """从文本中提取字幕组信息"""
    for kw in SUBGROUP_KEYWORDS:
        if kw in text:
            return kw
    return None


def _extract_title(text: str) -> Optional[str]:
    """从文本中提取标题信息"""
    # 去除 URL 前缀
    cleaned = re.sub(r"^https?://[^\s]+", "", text).strip()
    # 去除常见扩展名
    cleaned = re.sub(r"\.(mp4|mkv|avi|rmvb|torrent)$", "", cleaned, flags=re.I)
    # 去除集数标记
    cleaned = re.sub(r"[Ee][Pp]\.?\s*\d+", "", cleaned)
    cleaned = re.sub(r"第\s*\d+\s*[集话話]", "", cleaned)
    cleaned = cleaned.strip("[]()【】《》")
    return cleaned if cleaned else None


def _extract_date(text: str) -> Optional[str]:
    """从文本中提取发布时间"""
    # 匹配 2024-01-15、2024/01/15、2024.01.15 等格式
    patterns = [
        r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})",
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            y, m, d = match.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return None


# ============================================================
# 核心解析逻辑
# ============================================================
def parse_single_entry(raw: str) -> Dict[str, Any]:
    """
    解析单条动漫资源信息

    参数:
        raw: 原始文本（URL、文件名或描述文本）

    返回:
        结构化字典，包含提取的字段
    """
    if not raw or not isinstance(raw, str):
        _error(ERR_INVALID_INPUT, "输入内容为空或类型错误")

    raw = raw.strip()
    if not raw:
        _error(ERR_INVALID_INPUT, "输入内容为空")

    entry: Dict[str, Any] = {
        "raw_input": raw,
        "url": None,
        "title": None,
        "episode": None,
        "quality": None,
        "subgroup": None,
        "date": None,
        "confidence": {},
        "needs_verification": [],
        "timestamp": _now_timestamp(),
    }

    # 提取 URL
    url_match = re.search(r"https?://[^\s]+", raw)
    if url_match:
        url = url_match.group(0)
        if _is_valid_url(url):
            entry["url"] = url
            entry["confidence"]["url"] = "high"
        else:
            entry["confidence"]["url"] = "low"
            entry["needs_verification"].append("url")
    else:
        entry["confidence"]["url"] = "absent"

    # 提取标题（优先从 URL 路径中提取）
    title_source = raw
    if entry["url"]:
        path_part = entry["url"].split("://")[-1].split("/", 1)
        if len(path_part) > 1:
            title_source = path_part[1]

    title = _extract_title(title_source)
    if title:
        entry["title"] = title
        entry["confidence"]["title"] = "medium"
    else:
        entry["needs_verification"].append("title")

    # 提取集数
    episode = _extract_episode(raw)
    if episode:
        entry["episode"] = episode
        entry["confidence"]["episode"] = "high"
    else:
        entry["needs_verification"].append("episode")

    # 提取画质
    quality = _extract_quality(raw)
    if quality:
        entry["quality"] = quality
        entry["confidence"]["quality"] = "high"
    else:
        entry["needs_verification"].append("quality")

    # 提取字幕组
    subgroup = _extract_subgroup(raw)
    if subgroup:
        entry["subgroup"] = subgroup
        entry["confidence"]["subgroup"] = "medium"
    else:
        entry["needs_verification"].append("subgroup")

    # 提取日期
    date = _extract_date(raw)
    if date:
        entry["date"] = date
        entry["confidence"]["date"] = "high"
    else:
        entry["needs_verification"].append("date")

    # 标注不确定字段
    for field in entry["needs_verification"]:
        entry[field] = f"[需核实:{field}]"

    return entry


def parse_batch(raw_items: List[str]) -> List[Dict[str, Any]]:
    """批量解析多条记录"""
    if not raw_items:
        _error(ERR_INVALID_INPUT, "批量输入为空")

    results = []
    for item in raw_items:
        try:
            results.append(parse_single_entry(item))
        except RuntimeError as e:
            # 单条失败不影响整体，记录错误信息
            results.append({
                "raw_input": item,
                "error": str(e),
                "timestamp": _now_timestamp(),
            })
    return results


# ============================================================
# 输出格式化
# ============================================================
def format_json(entries: List[Dict[str, Any]]) -> str:
    """格式化为 JSON 输出"""
    try:
        return json.dumps(entries, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        _error(ERR_INVALID_JSON, "JSON 序列化失败")


def format_markdown(entries: List[Dict[str, Any]]) -> str:
    """格式化为 Markdown 表格输出"""
    if not entries:
        return "| 标题 | 集数 | 画质 | 字幕组 | 日期 | URL |\n|------|------|------|--------|------|-----|"

    lines = ["| 标题 | 集数 | 画质 | 字幕组 | 日期 | URL |",
             "|------|------|------|--------|------|-----|"]
    for e in entries:
        title = e.get("title", "-") or "-"
        episode = e.get("episode", "-") or "-"
        quality = e.get("quality", "-") or "-"
        subgroup = e.get("subgroup", "-") or "-"
        date = e.get("date", "-") or "-"
        url = e.get("url", "-") or "-"
        lines.append(f"| {title} | {episode} | {quality} | {subgroup} | {date} | {url} |")
    return "\n".join(lines)


def format_csv(entries: List[Dict[str, Any]]) -> str:
    """格式化为 CSV 输出"""
    if not entries:
        return "title,episode,quality,subgroup,date,url"

    fieldnames = ["title", "episode", "quality", "subgroup", "date", "url"]
    try:
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for e in entries:
            writer.writerow({k: e.get(k, "-") for k in fieldnames})
        return output.getvalue().strip()
    except (csv.Error, IOError):
        _error(ERR_INVALID_CSV, "CSV 生成失败")


def format_output(entries: List[Dict[str, Any]], fmt: str) -> str:
    """根据指定格式输出结果"""
    fmt = fmt.lower()
    if fmt not in SUPPORTED_FORMATS:
        _error(ERR_INVALID_FORMAT, f"不支持的输出格式: {fmt}，可选: {', '.join(SUPPORTED_FORMATS)}")

    if fmt == "json":
        return format_json(entries)
    elif fmt == "markdown":
        return format_markdown(entries)
    elif fmt == "csv":
        return format_csv(entries)
    else:
        _error(ERR_INVALID_FORMAT, f"未知格式: {fmt}")


# ============================================================
# 文件读取
# ============================================================
def read_input_file(filepath: str) -> List[str]:
    """从文件读取多行输入"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            _error(ERR_INVALID_INPUT, "输入文件为空")
        return lines
    except FileNotFoundError:
        _error(ERR_FILE_NOT_FOUND, f"文件不存在: {filepath}")
    except (IOError, OSError):
        _error(ERR_FILE_READ, f"文件读取失败: {filepath}")


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> int:
    """
    内置自检功能：使用硬编码样例数据验证核心逻辑
    不读外部文件、不依赖当前工作目录、不访问网络
    """
    print("=" * 60)
    print("anime-dl 自检开始")
    print("=" * 60)

    # 硬编码测试样例
    test_samples = [
        "https://example.com/anime/进击的巨人/第5集_1080P_字幕组.mp4",
        "https://example.org/download/EP12_720P_CHS.mkv",
        "鬼灭之刃 第3话 1080P 2023-05-20",
        "https://example.net/archive/2024/01/15/某科学的超电磁炮_S01E08_BDRip_720P",
        "https://example.com/anime/间谍过家家/第2集.mp4",
    ]

    print("\n[1/3] 测试单条解析...")
    single_results = []
    for sample in test_samples:
        try:
            entry = parse_single_entry(sample)
            single_results.append(entry)
            print(f"  ✓ 解析成功: {sample[:50]}...")
            print(f"    → 标题: {entry['title']}, 集数: {entry['episode']}, "
                  f"画质: {entry['quality']}, 字幕组: {entry['subgroup']}")
        except RuntimeError as e:
            print(f"  ✗ 解析失败: {e}")
            return 1

    # 稳健断言：检查关键字段是否被正确提取
    assert single_results[0]["episode"] == "5", "样例1集数提取错误"
    assert single_results[0]["quality"] == "1080P", "样例1画质提取错误"
    assert single_results[0]["subgroup"] == "字幕组", "样例1字幕组提取错误"
    assert single_results[2]["episode"] == "3", "样例3集数提取错误"
    assert single_results[3]["date"] == "2024-01-15", "样例4日期提取错误"
    print("  ✓ 关键字段断言通过")

    print("\n[2/3] 测试批量解析...")
    batch_results = parse_batch(test_samples)
    assert len(batch_results) == len(test_samples), "批量解析数量不一致"
    print(f"  ✓ 批量解析 {len(batch_results)} 条记录成功")

    print("\n[3/3] 测试输出格式...")
    # 测试 JSON
    json_out = format_output(batch_results, "json")
    json_data = json.loads(json_out)
    assert isinstance(json_data, list), "JSON 输出格式错误"
    assert len(json_data) == len(test_samples), "JSON 输出数量错误"
    print("  ✓ JSON 输出正常")

    # 测试 Markdown
    md_out = format_output(batch_results, "markdown")
    assert "| 标题 |" in md_out, "Markdown 表格头缺失"
    assert md_out.count("|") >= 6, "Markdown 表格列数不足"
    print("  ✓ Markdown 输出正常")

    # 测试 CSV
    csv_out = format_output(batch_results, "csv")
    csv_lines = csv_out.split("\n")
    assert len(csv_lines) >= 1, "CSV 输出为空"
    assert "title" in csv_lines[0], "CSV 表头缺失"
    print("  ✓ CSV 输出正常")

    # 测试错误处理
    print("\n[附加] 测试错误处理...")
    try:
        parse_single_entry("")
        print("  ✗ 空输入未报错")
        return 1
    except RuntimeError as e:
        assert "E001" in str(e), "错误码不正确"
        print("  ✓ 空输入正确报错")

    try:
        format_output([], "xml")
        print("  ✗ 非法格式未报错")
        return 1
    except RuntimeError as e:
        assert "E004" in str(e), "错误码不正确"
        print("  ✓ 非法格式正确报错")

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="anime-dl: 动漫资源采集与结构化输出工具",
        epilog="示例: python scripts/main.py --input 'https://example.com/anime/xxx' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：URL、文本或文件路径（文件路径以 @ 开头）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=SUPPORTED_FORMATS,
        help=f"输出格式（默认: json，可选: {', '.join(SUPPORTED_FORMATS)}）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件或网络）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except Exception as e:
            print(f"[{ERR_SELFTEST}] 自检异常: {e}")
            return 1

    # 正常模式
    if not args.input:
        parser.print_help()
        _error(ERR_INVALID_INPUT, "请提供 --input 参数")

    # 判断输入类型
    raw_input = args.input
    if raw_input.startswith("@"):
        # 文件输入
        filepath = raw_input[1:]
        try:
            items = read_input_file(filepath)
        except RuntimeError as e:
            print(f"错误: {e}")
            return 1
    else:
        # 直接文本输入，支持分号/换行分隔多条
        items = [x.strip() for x in raw_input.split(";") if x.strip()]
        if not items:
            _error(ERR_INVALID_INPUT, "输入内容为空")

    # 解析
    try:
        entries = parse_batch(items)
        output = format_output(entries, args.format)
        print(output)
        return 0
    except RuntimeError as e:
        print(f"错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
