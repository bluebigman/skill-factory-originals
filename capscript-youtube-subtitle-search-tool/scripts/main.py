#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capscript-youtube-subtitle-search-tool
字幕检索 / 时间轴定位 / 关键词过滤
版本: 1.0.3 (clean-room 独立实现)
"""

import re
import sys
import json
import argparse
from typing import List, Dict, Optional, Tuple


# ---------- 错误码定义 ----------
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"      # 输入为空或类型错误
ERR_PARSE_FAILED = "E002"       # 字幕解析失败
ERR_TIME_FORMAT = "E003"        # 时间格式错误
ERR_RANGE_INVALID = "E004"      # 时间范围无效（结束早于开始）
ERR_KEYWORD_EMPTY = "E005"      # 关键词为空
ERR_NO_MATCH = "E006"           # 无匹配结果
ERR_JSON_DUMP = "E007"          # JSON 序列化失败
ERR_INTERNAL = "E008"           # 内部未预期错误
ERR_SELFTEST_FAIL = "E009"      # 自检失败
ERR_USAGE = "E010"              # 参数使用错误


# ---------- 工具函数 ----------

def _normalize_text(text: str) -> str:
    """清理字幕文本：去空白、合并换行、去除时间标签残留。"""
    if not text:
        return ""
    # 去除 VTT 中常见的行内标签（如 <c>、<00:00:01.000> 等）
    text = re.sub(r"<[^>]+>", "", text)
    # 将多个空白字符（含换行）合并为单个空格
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_timestamp(ts: str) -> Optional[int]:
    """
    将字幕时间戳转为毫秒整数。
    支持格式:
      - SRT: 00:00:20,000
      - VTT: 00:00:20.000
      - 纯秒: 12.5 或 12
    返回 None 表示格式非法。
    """
    if not ts or not isinstance(ts, str):
        return None
    ts = ts.strip()
    if not ts:
        return None

    # 处理纯秒格式
    if re.fullmatch(r"\d+(\.\d+)?", ts):
        try:
            return int(float(ts) * 1000)
        except ValueError:
            return None

    # 处理 HH:MM:SS,mmm / HH:MM:SS.mmm / MM:SS.mmm 等
    # 统一分隔符：逗号转点
    ts = ts.replace(",", ".")

    # 尝试匹配 小时:分钟:秒.毫秒 或 分钟:秒.毫秒
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.(\d{1,3}))?", ts)
    if not m:
        return None

    hours = int(m.group(1))
    minutes = int(m.group(2))
    seconds = int(m.group(3)) if m.group(3) else 0
    millis_str = m.group(4) if m.group(4) else "0"
    # 不足3位时补零
    millis = int(millis_str.ljust(3, "0"))

    # 合理性校验：分钟/秒不能超过59，小时不能超过99（宽松）
    if minutes > 59 or seconds > 59:
        return None

    return hours * 3600000 + minutes * 60000 + seconds * 1000 + millis


def _format_timestamp(ms: int) -> str:
    """毫秒转 SRT 格式时间戳 (HH:MM:SS,mmm)。"""
    if ms < 0:
        ms = 0
    hours, rem = divmod(ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _parse_time_range(spec: str) -> Tuple[Optional[int], Optional[int]]:
    """
    解析时间范围字符串。
    支持:
      - "00:01:30"            -> 单点，返回 (ms, None)
      - "00:01:00-00:02:00"   -> 区间，返回 (start_ms, end_ms)
    返回 (None, None) 表示解析失败。
    """
    if not spec or not isinstance(spec, str):
        return (None, None)
    spec = spec.strip()
    if not spec:
        return (None, None)

    # 检查是否为区间
    if "-" in spec:
        parts = spec.split("-", 1)
        if len(parts) != 2:
            return (None, None)
        start_s, end_s = parts[0].strip(), parts[1].strip()
        start_ms = _parse_timestamp(start_s)
        end_ms = _parse_timestamp(end_s)
        if start_ms is None or end_ms is None:
            return (None, None)
        if end_ms < start_ms:
            # 区间非法
            return (None, None)
        return (start_ms, end_ms)
    else:
        # 单点
        ms = _parse_timestamp(spec)
        if ms is None:
            return (None, None)
        return (ms, None)


# ---------- 核心解析器 ----------

def parse_subtitles(raw_text: str) -> Dict:
    """
    解析字幕文本（SRT/VTT/纯文本）为结构化条目。
    返回: {"entries": [...], "error": None 或 错误码}
    """
    if not raw_text or not isinstance(raw_text, str):
        return {"entries": [], "error": ERR_INVALID_INPUT}

    entries = []
    
    # 移除 VTT 文件头（WEBVTT 及其可能的元数据）
    lines = raw_text.splitlines()
    cleaned_lines = []
    in_header = False
    for line in lines:
        stripped = line.strip()
        if stripped == "WEBVTT":
            in_header = True
            continue
        if in_header:
            # 跳过头部空行和元数据（如 NOTE、Kind 等）
            if stripped == "":
                continue
            if stripped.startswith("NOTE") or ":" in stripped and "-->" not in stripped:
                continue
            # 遇到第一条时间戳行，结束头部处理
            if "-->" in stripped or re.search(r"\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}", stripped):
                in_header = False
                cleaned_lines.append(line)
            continue
        cleaned_lines.append(line)
    
    # 重新组合文本
    cleaned_text = "\n".join(cleaned_lines)
    
    # 按空行分割字幕块
    blocks = re.split(r"\n\s*\n", cleaned_text.strip())
    if not blocks or (len(blocks) == 1 and not blocks[0].strip()):
        return {"entries": [], "error": ERR_PARSE_FAILED}

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        if not lines:
            continue

        # 尝试提取时间戳行（包含 "-->" 或 逗号/点 分隔的时间）
        time_line_idx = -1
        for i, line in enumerate(lines):
            if "-->" in line or re.search(r"\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}", line):
                time_line_idx = i
                break

        if time_line_idx == -1:
            # 无时间戳，按纯文本处理（整块作为一条）
            text = _normalize_text(" ".join(lines))
            if text:
                entries.append({
                    "index": len(entries) + 1,
                    "start_ms": None,
                    "end_ms": None,
                    "start": "",
                    "end": "",
                    "text": text
                })
            continue

        # 解析时间戳行
        time_line = lines[time_line_idx].strip()

        # 提取时间部分（兼容 SRT "00:00:01,000 --> 00:00:03,000" 和 VTT 带标签）
        time_matches = re.findall(r"\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}", time_line)
        if len(time_matches) < 2:
            # 尝试只匹配一个时间（罕见情况，跳过）
            continue

        start_ms = _parse_timestamp(time_matches[0])
        end_ms = _parse_timestamp(time_matches[1])
        if start_ms is None or end_ms is None:
            continue

        # 文本内容：时间行之后的所有行
        text_lines = lines[time_line_idx + 1:]
        text = _normalize_text(" ".join(text_lines))

        # 序号：时间行之前的数字行
        index = len(entries) + 1
        if time_line_idx > 0:
            try:
                idx_candidate = int(lines[0].strip())
                if idx_candidate > 0:
                    index = idx_candidate
            except (ValueError, IndexError):
                pass

        entries.append({
            "index": index,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start": _format_timestamp(start_ms),
            "end": _format_timestamp(end_ms),
            "text": text
        })

    if not entries:
        return {"entries": [], "error": ERR_PARSE_FAILED}

    # 按 start_ms 排序（若存在）
    entries.sort(key=lambda e: (e["start_ms"] if e["start_ms"] is not None else 0,
                                e["index"]))
    # 重新编号
    for i, e in enumerate(entries):
        e["index"] = i + 1

    return {"entries": entries, "error": None}


# ---------- 查询功能 ----------

def search_by_time(entries: List[Dict], time_spec: str) -> Dict:
    """
    按时间点或时间范围检索。
    时间点: 返回该时间点正在播放的字幕（start <= t <= end）
    时间范围: 返回与范围有交集的字幕
    """
    if not entries:
        return {"entries": [], "error": ERR_NO_MATCH}
    if not time_spec:
        return {"entries": [], "error": ERR_TIME_FORMAT}

    start_ms, end_ms = _parse_time_range(time_spec)
    if start_ms is None:
        return {"entries": [], "error": ERR_TIME_FORMAT}

    results = []
    if end_ms is None:
        # 单点查询
        for e in entries:
            if e["start_ms"] is None:
                continue
            if e["start_ms"] <= start_ms <= e["end_ms"]:
                results.append(e)
    else:
        # 范围查询：有交集
        for e in entries:
            if e["start_ms"] is None:
                continue
            # 区间重叠判断
            if e["start_ms"] <= end_ms and e["end_ms"] >= start_ms:
                results.append(e)

    if not results:
        return {"entries": [], "error": ERR_NO_MATCH}
    return {"entries": results, "error": None}


def search_by_keyword(entries: List[Dict], keywords: List[str]) -> Dict:
    """
    按关键词过滤（大小写不敏感，任一关键词命中即可）。
    """
    if not entries:
        return {"entries": [], "error": ERR_NO_MATCH}
    if not keywords or all(not k.strip() for k in keywords):
        return {"entries": [], "error": ERR_KEYWORD_EMPTY}

    # 清洗关键词
    clean_kw = [k.strip().lower() for k in keywords if k.strip()]
    if not clean_kw:
        return {"entries": [], "error": ERR_KEYWORD_EMPTY}

    results = []
    for e in entries:
        text_lower = e["text"].lower()
        if any(kw in text_lower for kw in clean_kw):
            results.append(e)

    if not results:
        return {"entries": [], "error": ERR_NO_MATCH}
    return {"entries": results, "error": None}


def combined_search(entries: List[Dict], time_spec: str, keywords: List[str]) -> Dict:
    """
    组合查询：时间范围 + 关键词联合过滤。
    """
    if not entries:
        return {"entries": [], "error": ERR_NO_MATCH}

    # 先按时间过滤
    time_result = search_by_time(entries, time_spec)
    if time_result["error"]:
        return time_result

    # 再按关键词过滤
    kw_result = search_by_keyword(time_result["entries"], keywords)
    return kw_result


def extract_segment(entries: List[Dict], selector: str) -> Dict:
    """
    提取指定片段（按序号或时间戳）。
    返回该片段及前后各一条上下文。
    """
    if not entries:
        return {"entries": [], "error": ERR_NO_MATCH}
    if not selector:
        return {"entries": [], "error": ERR_INVALID_INPUT}

    selector = selector.strip()
    target_idx = None

    # 尝试按序号
    try:
        idx = int(selector)
        # 查找匹配的条目
        for i, e in enumerate(entries):
            if e["index"] == idx:
                target_idx = i
                break
    except ValueError:
        # 尝试按时间戳
        ms = _parse_timestamp(selector)
        if ms is not None:
            for i, e in enumerate(entries):
                if e["start_ms"] is not None and e["start_ms"] <= ms <= e["end_ms"]:
                    target_idx = i
                    break

    if target_idx is None:
        return {"entries": [], "error": ERR_NO_MATCH}

    # 提取上下文（前后各一条）
    start = max(0, target_idx - 1)
    end = min(len(entries), target_idx + 2)
    results = entries[start:end]

    return {"entries": results, "error": None}


# ---------- 输出辅助 ----------

def _safe_json_dump(data: Dict) -> str:
    """安全 JSON 序列化。"""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return json.dumps({"error": ERR_JSON_DUMP, "message": "JSON 序列化失败"})


def _print_error(code: str, message: str) -> None:
    """统一错误输出。"""
    print(json.dumps({"error": code, "message": message}, ensure_ascii=False))


# ---------- 自检模块 ----------

def _selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("[selftest] 开始自检...")

    # 硬编码样例字幕（SRT 格式）
    sample_srt = """1
00:00:01,000 --> 00:00:04,000
大家好，欢迎观看本期视频

2
00:00:05,000 --> 00:00:08,500
今天我们来讨论机器学习的基础概念

3
00:00:09,000 --> 00:00:12,000
包括监督学习和无监督学习

4
00:00:13,000 --> 00:00:16,000
以及深度学习在图像识别中的应用

5
00:00:17,500 --> 00:00:20,000
感谢观看，我们下期再见
"""

    # 1. 解析测试
    parse_result = parse_subtitles(sample_srt)
    assert parse_result["error"] is None, f"解析失败: {parse_result['error']}"
    entries = parse_result["entries"]
    assert len(entries) == 5, f"期望5条字幕，实际 {len(entries)}"
    # 宽松检查：文本内容非空
    for e in entries:
        assert e["text"], "字幕文本为空"
        assert e["start_ms"] is not None and e["end_ms"] is not None, "时间戳缺失"
        assert e["start_ms"] < e["end_ms"], "开始时间应早于结束时间"
    print(f"  [OK] 解析测试: {len(entries)} 条字幕")

    # 2. 时间点定位测试
    time_result = search_by_time(entries, "00:00:06")
    assert time_result["error"] is None, f"时间点查询失败: {time_result['error']}"
    assert len(time_result["entries"]) == 1, f"时间点应命中1条，实际 {len(time_result['entries'])}"
    assert "机器学习" in time_result["entries"][0]["text"], "命中的文本应包含'机器学习'"
    print("  [OK] 时间点定位测试")

    # 3. 时间范围测试
    range_result = search_by_time(entries, "00:00:04-00:00:10")
    assert range_result["error"] is None, f"时间范围查询失败: {range_result['error']}"
    # 应命中第2条（5-8.5s），可能也命中第1条（1-4s，边界重叠）
    assert len(range_result["entries"]) >= 1, "时间范围应至少命中1条"
    print(f"  [OK] 时间范围测试: 命中 {len(range_result['entries'])} 条")

    # 4. 关键词过滤测试
    kw_result = search_by_keyword(entries, ["机器学习"])
    assert kw_result["error"] is None, f"关键词查询失败: {kw_result['error']}"
    assert len(kw_result["entries"]) == 1, f"关键词应命中1条，实际 {len(kw_result['entries'])}"
    assert "机器学习" in kw_result["entries"][0]["text"]
    print("  [OK] 关键词过滤测试")

    # 5. 多关键词测试
    multi_kw = search_by_keyword(entries, ["深度学习", "监督学习"])
    assert multi_kw["error"] is None, f"多关键词查询失败: {multi_kw['error']}"
    assert len(multi_kw["entries"]) == 2, f"多关键词应命中2条，实际 {len(multi_kw['entries'])}"
    print("  [OK] 多关键词测试")

    # 6. 组合查询测试
    combined = combined_search(entries, "00:00:00-00:00:15", ["学习"])
    assert combined["error"] is None, f"组合查询失败: {combined['error']}"
    assert len(combined["entries"]) >= 2, f"组合查询应命中至少2条，实际 {len(combined['entries'])}"
    print("  [OK] 组合查询测试")

    # 7. 片段提取测试
    extract = extract_segment(entries, "2")
    assert extract["error"] is None, f"片段提取失败: {extract['error']}"
    assert len(extract["entries"]) == 3, f"片段提取应返回3条（含上下文），实际 {len(extract['entries'])}"
    print("  [OK] 片段提取测试")

    # 8. 边界情况：无匹配
    no_match = search_by_keyword(entries, ["不存在的关键词xyz"])
    assert no_match["error"] == ERR_NO_MATCH, "应返回无匹配错误"
    print("  [OK] 无匹配错误处理")

    # 9. 时间格式容错测试
    ts_ms = _parse_timestamp("00:01:30.500")
    assert ts_ms is not None and ts_ms == 90500, f"时间戳解析错误: {ts_ms}"
    ts_ms2 = _parse_timestamp("00:00:05,250")
    assert ts_ms2 is not None and ts_ms2 == 5250, f"逗号时间戳解析错误: {ts_ms2}"
    ts_ms3 = _parse_timestamp("12.5")
    assert ts_ms3 is not None and ts_ms3 == 12500, f"纯秒解析错误: {ts_ms3}"
    print("  [OK] 时间戳格式容错")

    # 10. VTT 格式测试
    sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:03.000
第一行字幕

00:00:04.000 --> 00:00:06.000
第二行字幕
"""
    vtt_result = parse_subtitles(sample_vtt)
    assert vtt_result["error"] is None, f"VTT 解析失败: {vtt_result['error']}"
    assert len(vtt_result["entries"]) == 2, f"VTT 应解析2条，实际 {len(vtt_result['entries'])}"
    print("  [OK] VTT 格式解析")

    print("[selftest] 全部自检通过 ✅")
    return ERR_SUCCESS


# ---------- 命令行入口 ----------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="字幕检索工具：解析字幕、时间轴定位、关键词过滤",
        epilog="示例: python main.py --file sub.srt --time 00:01:30"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--file", help="字幕文件路径（SRT/VTT）")
    parser.add_argument("--text", help="直接传入字幕文本内容")
    parser.add_argument("--time", help="时间点或时间范围，如 00:01:30 或 00:01:00-00:02:00")
    parser.add_argument("--keyword", action="append", help="关键词（可多次指定）")
    parser.add_argument("--extract", help="提取片段序号或时间戳")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return _selftest()
        except AssertionError as e:
            _print_error(ERR_SELFTEST_FAIL, f"自检失败: {e}")
            return 1
        except Exception as e:
            _print_error(ERR_INTERNAL, f"自检异常: {e}")
            return 1

    # 获取输入字幕
    raw_text = None
    if args.text:
        raw_text = args.text
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_text = f.read()
        except (IOError, OSError) as e:
            _print_error(ERR_INVALID_INPUT, f"无法读取文件: {e}")
            return 1
    else:
        _print_error(ERR_USAGE, "请提供 --file 或 --text 参数，或使用 --selftest")
        return 1

    # 解析字幕
    parsed = parse_subtitles(raw_text)
    if parsed["error"]:
        _print_error(parsed["error"], "字幕解析失败")
        return 1
    entries = parsed["entries"]

    # 执行查询
    result_entries = entries
    error_code = None

    # 片段提取优先
    if args.extract:
        extract_result = extract_segment(entries, args.extract)
        if extract_result["error"]:
            error_code = extract_result["error"]
        else:
            result_entries = extract_result["entries"]
    else:
        # 组合查询
        if args.time and args.keyword:
            combined = combined_search(entries, args.time, args.keyword)
            error_code = combined["error"]
            result_entries = combined["entries"]
        elif args.time:
            time_result = search_by_time(entries, args.time)
            error_code = time_result["error"]
            result_entries = time_result["entries"]
        elif args.keyword:
            kw_result = search_by_keyword(entries, args.keyword)
            error_code = kw_result["error"]
            result_entries = kw_result["entries"]

    if error_code:
        _print_error(error_code, "查询无匹配结果")
        return 1

    # 输出结果
    output_data = {
        "total": len(result_entries),
        "entries": result_entries
    }

    if args.json:
        print(_safe_json_dump(output_data))
    else:
        # 人类可读输出
        for e in result_entries:
            time_str = f"[{e['start']} -> {e['end']}]" if e["start"] else "[无时间戳]"
            print(f"{e['index']:>4d} {time_str} {e['text']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
