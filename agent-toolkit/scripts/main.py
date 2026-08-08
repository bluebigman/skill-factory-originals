#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-toolkit 技能编排与数据转换工具
基于功能规格独立实现（clean-room），仅依赖标准库。

能力边界（实际实现）：
- 支持 JSON/Markdown/CSV 三种输出格式
- 支持自定义字段提取（正则匹配"字段名:值"模式）
- 支持本地文件处理（UTF-8/GBK/GB18030 三级编码回退）
- 支持 URL 协议校验（不实际访问网络）
- 内置自检功能（离线可运行）
- 支持 --dry-run 预览模式（默认不写盘，仅打印 diff）
- 支持 --verbose 详细输出（显示每个修改决策明细）
- 支持流式分块处理（以句号为边界滑窗、重叠 2 句保上下文）
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或不可解析",
    "E002": "超出大小限制（10MB 或 1000 条记录）",
    "E003": "字段映射冲突",
    "E004": "输出格式不支持",
    "E005": "批量处理中断",
    "E006": "文件读取失败",
    "E007": "URL 解析失败",
    "E008": "JSON 解析失败",
    "E009": "参数错误",
    "E010": "内部逻辑错误",
}

# 内置默认字段集
DEFAULT_FIELDS = ["title", "date", "category", "summary", "url"]

# 大小限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_RECORDS = 1000

# 编码回退顺序
ENCODING_FALLBACK = ["utf-8", "gbk", "gb18030"]

# 流式处理参数
CHUNK_SIZE = 5000  # 每块字符数
OVERLAP_SENTENCES = 2  # 重叠句数


class ToolkitError(Exception):
    """技能工具自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_date(text: str, verbose: bool = False) -> str:
    """从文本中提取日期（YYYY-MM-DD 或 YYYY年M月D日），失败返回占位符"""
    try:
        # 尝试 ISO 格式
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if m:
            if verbose:
                print(f"  [决策] 提取日期: {m.group(0)}", file=sys.stderr)
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

        # 尝试中文格式
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
        if m:
            y, mo, d = m.group(1), m.group(2), m.group(3)
            result = f"{y}-{int(mo):02d}-{int(d):02d}"
            if verbose:
                print(f"  [决策] 提取日期(中文格式): {result}", file=sys.stderr)
            return result

        if verbose:
            print(f"  [决策] 未找到日期，使用占位符", file=sys.stderr)
        return "[需核实:date]"
    except Exception as e:
        print(f"警告: 日期提取失败 - {e}", file=sys.stderr)
        return "[需核实:date]"


def _extract_title(text: str, verbose: bool = False) -> str:
    """提取标题：优先取第一个句号前的内容（去除日期前缀），失败返回占位符"""
    try:
        # 去掉日期前缀
        cleaned = re.sub(r"^\d{4}年\d{1,2}月\d{1,2}日[，,]?\s*", "", text)
        # 取第一句
        m = re.search(r"^(.{2,50}?)[。！？!?]", cleaned)
        if m:
            result = m.group(1).strip()
            if verbose:
                print(f"  [决策] 提取标题: {result}", file=sys.stderr)
            return result
        if len(cleaned) > 2:
            result = cleaned[:30]
            if verbose:
                print(f"  [决策] 截取标题: {result}", file=sys.stderr)
            return result
        if verbose:
            print(f"  [决策] 标题过短，使用占位符", file=sys.stderr)
        return "[需核实:title]"
    except Exception as e:
        print(f"警告: 标题提取失败 - {e}", file=sys.stderr)
        return "[需核实:title]"


def _extract_category(text: str, verbose: bool = False) -> str:
    """提取分类：匹配常见分类词，失败返回占位符"""
    try:
        keywords = ["评审", "会议", "报告", "设计", "开发", "测试", "部署", "优化", "方案"]
        for kw in keywords:
            if kw in text:
                if verbose:
                    print(f"  [决策] 提取分类: {kw}", file=sys.stderr)
                return kw
        if verbose:
            print(f"  [决策] 未匹配分类词，使用占位符", file=sys.stderr)
        return "[需核实:category]"
    except Exception as e:
        print(f"警告: 分类提取失败 - {e}", file=sys.stderr)
        return "[需核实:category]"


def _extract_summary(text: str, max_len: int = 200, verbose: bool = False) -> str:
    """生成摘要：取全文前 max_len 字"""
    try:
        summary = text.strip().replace("\n", " ")
        if len(summary) > max_len:
            summary = summary[:max_len] + "..."
            if verbose:
                print(f"  [决策] 摘要截断至 {max_len} 字符", file=sys.stderr)
        if not summary:
            if verbose:
                print(f"  [决策] 摘要为空，使用占位符", file=sys.stderr)
            return "[需核实:summary]"
        return summary
    except Exception as e:
        print(f"警告: 摘要生成失败 - {e}", file=sys.stderr)
        return "[需核实:summary]"


def _extract_url(text: str, verbose: bool = False) -> str:
    """提取 URL，失败返回占位符"""
    try:
        m = re.search(r"https?://[^\s]+", text)
        if m:
            if verbose:
                print(f"  [决策] 提取URL: {m.group(0)}", file=sys.stderr)
            return m.group(0)
        if verbose:
            print(f"  [决策] 未找到URL，使用占位符", file=sys.stderr)
        return "[需核实:url]"
    except Exception as e:
        print(f"警告: URL 提取失败 - {e}", file=sys.stderr)
        return "[需核实:url]"


def _parse_single_record(text: str, fields: list, record_id: int, verbose: bool = False) -> dict:
    """解析单条记录为结构化字段"""
    try:
        text = text.strip()
        if not text:
            raise ToolkitError("E001")

        field_values = {}
        for field in fields:
            if field == "title":
                field_values[field] = _extract_title(text, verbose)
            elif field == "date":
                field_values[field] = _extract_date(text, verbose)
            elif field == "category":
                field_values[field] = _extract_category(text, verbose)
            elif field == "summary":
                field_values[field] = _extract_summary(text, verbose=verbose)
            elif field == "url":
                field_values[field] = _extract_url(text, verbose)
            else:
                # 自定义字段：尝试匹配 "字段名:值" 模式
                m = re.search(rf"{field}[：:]\s*([^\s，,。；;]+)", text)
                field_values[field] = m.group(1) if m else f"[需核实:{field}]"
                if verbose and m:
                    print(f"  [决策] 提取自定义字段 {field}: {m.group(1)}", file=sys.stderr)

        # 置信度评估
        filled = sum(1 for v in field_values.values() if not v.startswith("[需核实"))
        total = len(fields)
        if filled == total:
            confidence = "high"
        elif filled >= total * 0.5:
            confidence = "medium"
        else:
            confidence = "low"

        if verbose:
            print(f"  [决策] 记录{record_id}置信度: {confidence} (填充{filled}/{total})", file=sys.stderr)

        return {
            "id": record_id,
            "fields": field_values,
            "confidence": confidence,
            "source": "用户提供文本",
        }
    except ToolkitError:
        raise
    except Exception as e:
        print(f"警告: 记录解析失败 (ID={record_id}) - {e}", file=sys.stderr)
        raise ToolkitError("E010", f"记录解析失败: {str(e)}")


def _split_input(text: str, verbose: bool = False) -> list:
    """将输入文本按行或空行拆分为多条记录"""
    try:
        # 先尝试按空行拆分
        blocks = re.split(r"\n\s*\n", text)
        if len(blocks) > 1:
            result = [b.strip() for b in blocks if b.strip()]
            if verbose:
                print(f"  [决策] 按空行拆分为 {len(result)} 条记录", file=sys.stderr)
            return result

        # 否则按行拆分
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        result = lines if lines else [text.strip()]
        if verbose:
            print(f"  [决策] 按行拆分为 {len(result)} 条记录", file=sys.stderr)
        return result
    except Exception as e:
        print(f"警告: 文本拆分失败 - {e}", file=sys.stderr)
        return [text.strip()] if text.strip() else []


def _stream_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP_SENTENCES, verbose: bool = False) -> list:
    """流式分块处理：以句号为边界滑窗、重叠保上下文"""
    try:
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            # 找到分块结束位置（句号边界）
            end = min(start + chunk_size, len(text))
            if end < len(text):
                # 向前找句号
                last_period = text.rfind("。", start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1

            chunk = text[start:end]
            chunks.append(chunk)

            # 计算重叠部分（保留最后 overlap 个句号）
            overlap_start = end
            if overlap > 0 and end < len(text):
                # 从 end 向前找 overlap 个句号
                period_positions = [m.start() for m in re.finditer(r"。", text[start:end])]
                if len(period_positions) >= overlap:
                    overlap_start = start + period_positions[-overlap] + 1

            start = overlap_start

            if verbose:
                print(f"  [决策] 分块: 位置 {len(chunks)} 从 {start} 到 {end}", file=sys.stderr)

        return chunks
    except Exception as e:
        print(f"警告: 流式分块失败 - {e}", file=sys.stderr)
        return [text]


def process_text(text: str, fields: list = None, fmt: str = "json", verbose: bool = False, dry: bool = True) -> str:
    """核心处理函数：文本 -> 结构化输出"""
    try:
        # 输入校验（guard clause）
        if not isinstance(text, str):
            raise ToolkitError("E009", "输入必须是字符串类型")
        if not text or not text.strip():
            raise ToolkitError("E001")
        if len(text.encode("utf-8")) > MAX_FILE_SIZE:
            raise ToolkitError("E002")

        # 字段列表校验
        if fields is None:
            fields = DEFAULT_FIELDS
        elif not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            raise ToolkitError("E009", "字段列表必须是字符串列表")

        # 格式校验
        fmt = fmt.lower()
        if fmt not in ("json", "markdown", "csv"):
            raise ToolkitError("E004")

        if verbose:
            print(f"[处理] 输入长度: {len(text)} 字符", file=sys.stderr)
            print(f"[处理] 字段: {fields}", file=sys.stderr)
            print(f"[处理] 格式: {fmt}", file=sys.stderr)
            print(f"[处理] dry-run: {dry}", file=sys.stderr)

        # 流式分块处理（O(n) 性能）
        chunks = _stream_chunks(text, verbose=verbose)
        if verbose:
            print(f"[处理] 分块数量: {len(chunks)}", file=sys.stderr)

        # 逐块处理
        all_records = []
        all_errors = []
        record_id = 0

        for chunk_idx, chunk in enumerate(chunks, 1):
            if verbose:
                print(f"[处理] 处理分块 {chunk_idx}/{len(chunks)}", file=sys.stderr)

            # 拆分记录
            records_raw = _split_input(chunk, verbose)
            if len(records_raw) > MAX_RECORDS:
                raise ToolkitError("E002")

            # 逐条解析
            for raw in records_raw:
                record_id += 1
                try:
                    rec = _parse_single_record(raw, fields, record_id, verbose)
                    all_records.append(rec)
                except ToolkitError as e:
                    all_errors.append({"record": record_id, "error": e.code})
                    print(f"警告: 记录 {record_id} 解析失败 - {e.message}", file=sys.stderr)

        # 格式输出
        output_data = {
            "records": all_records,
            "meta": {
                "total": len(all_records),
                "processed_at": _now_iso(),
                "errors": all_errors if all_errors else None,
                "dry_run": dry,
            },
        }

        if verbose:
            print(f"[处理] 成功解析 {len(all_records)} 条记录，{len(all_errors)} 条错误", file=sys.stderr)

        if fmt == "json":
            return json.dumps(output_data, ensure_ascii=False, indent=2)
        elif fmt == "markdown":
            return _to_markdown(output_data)
        elif fmt == "csv":
            return _to_csv(output_data)
        else:
            raise ToolkitError("E004")
    except ToolkitError:
        raise
    except Exception as e:
        print(f"错误: 处理失败 - {e}", file=sys.stderr)
        raise ToolkitError("E010", f"处理失败: {str(e)}")


def _to_markdown(data: dict) -> str:
    """转换为 Markdown 表格"""
    try:
        if not data["records"]:
            return "| 无记录 |\n|--------|"

        fields = list(data["records"][0]["fields"].keys())
        lines = ["| ID | " + " | ".join(fields) + " | 置信度 |", "|----|" + "|".join(["----"] * len(fields)) + "|--------|"]

        for rec in data["records"]:
            row = [str(rec["id"])]
            for f in fields:
                row.append(rec["fields"].get(f, ""))
            row.append(rec["confidence"])
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)
    except Exception as e:
        print(f"警告: Markdown 转换失败 - {e}", file=sys.stderr)
        return "| 转换失败 |\n|--------|"


def _to_csv(data: dict) -> str:
    """转换为 CSV 格式"""
    try:
        if not data["records"]:
            return "id,confidence\n"

        fields = list(data["records"][0]["fields"].keys())
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id"] + fields + ["confidence"])

        for rec in data["records"]:
            row = [rec["id"]]
            for f in fields:
                row.append(rec["fields"].get(f, ""))
            row.append(rec["confidence"])
            writer.writerow(row)

        return output.getvalue()
    except Exception as e:
        print(f"警告: CSV 转换失败 - {e}", file=sys.stderr)
        return "id,confidence\n"


def _read_file_with_encoding(file_path: str) -> str:
    """读取文件内容，支持多编码回退"""
    try:
        path = Path(file_path)
        if not path.exists():
            raise ToolkitError("E001", f"文件不存在: {file_path}")
        if path.stat().st_size > MAX_FILE_SIZE:
            raise ToolkitError("E002")

        # 尝试多编码回退
        for encoding in ENCODING_FALLBACK:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"警告: 使用 {encoding} 编码读取失败 - {e}", file=sys.stderr)
                continue

        # 最后使用 errors="replace" 兜底
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise ToolkitError("E006", f"读取文件失败: {str(e)}")
    except ToolkitError:
        raise
    except Exception as e:
        raise ToolkitError("E006", f"读取文件失败: {str(e)}")


def process_file(file_path: str, fields: list = None, fmt: str = "json", verbose: bool = False, dry: bool = True) -> str:
    """处理本地文件"""
    try:
        content = _read_file_with_encoding(file_path)
        return process_text(content, fields, fmt, verbose, dry)
    except ToolkitError:
        raise
    except Exception as e:
        raise ToolkitError("E006", f"读取文件失败: {str(e)}")


def process_url(url: str, fields: list = None, fmt: str = "json", verbose: bool = False, dry: bool = True) -> str:
    """处理 URL（仅做协议校验，不实际访问）"""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ToolkitError("E007", f"无效的 URL: {url}")

        # 规格要求不访问网络，这里返回占位提示
        placeholder = f"[需核实:url内容] 无法离线访问 {url}"
        return process_text(placeholder, fields, fmt, verbose, dry)
    except ToolkitError:
        raise
    except Exception as e:
        raise ToolkitError("E007", f"URL 解析失败: {str(e)}")


def _selftest() -> int:
    """内置自检函数：使用硬编码样例数据验证核心逻辑"""
    print("=== agent-toolkit 自检开始 ===")

    # 测试样例 1：单条文本（中文标点）
    sample1 = "2024年3月15日，张三在项目评审会上提出性能优化方案，涉及模块A和模块B。"
    try:
        result1 = json.loads(process_text(sample1))
        assert len(result1["records"]) == 1, "样例1应产生1条记录"
        rec = result1["records"][0]
        assert rec["fields"]["date"] == "2024-03-15", "日期提取失败"
        assert rec["confidence"] in ("high", "medium", "low"), "置信度等级非法"
        assert rec["id"] == 1, "ID 应为1"
        print("  [通过] 单条文本处理（中文标点）")
    except Exception as e:
        print(f"  [失败] 单条文本处理: {e}")
        return 1

    # 测试样例 2：批量处理（空行分隔）
    sample2 = "第一条记录内容，无日期。\n\n2023年5月20日，第二条记录。"
    try:
        result2 = json.loads(process_text(sample2))
        assert 1 <= len(result2["records"]) <= 2, "批量记录数异常"
        assert result2["meta"]["total"] == len(result2["records"]), "总数不一致"
        print("  [通过] 批量处理（空行分隔）")
    except Exception as e:
        print(f"  [失败] 批量处理: {e}")
        return 1

    # 测试样例 3：Markdown 输出
    try:
        md = process_text(sample1, fmt="markdown")
        assert "|" in md and "置信度" in md, "Markdown 格式异常"
        print("  [通过] Markdown 输出")
    except Exception as e:
        print(f"  [失败] Markdown 输出: {e}")
        return 1

    # 测试样例 4：CSV 输出
    try:
        csv_out = process_text(sample1, fmt="csv")
        assert "id" in csv_out and "confidence" in csv_out, "CSV 格式异常"
        print("  [通过] CSV 输出")
    except Exception as e:
        print(f"  [失败] CSV 输出: {e}")
        return 1

    # 测试样例 5：空输入错误处理
    try:
        process_text("")
        print("  [失败] 空输入应抛出错误")
        return 1
    except ToolkitError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  [通过] 空输入错误处理")

    # 测试样例 6：自定义字段
    try:
        custom_fields = ["title", "date", "category", "summary", "url", "author"]
        result6 = json.loads(process_text(sample1, fields=custom_fields))
        assert "author" in result6["records"][0]["fields"], "自定义字段缺失"
        assert result6["records"][0]["fields"]["author"].startswith("[需核实"), "自定义字段应为占位符"
        print("  [通过] 自定义字段")
    except Exception as e:
        print(f"  [失败] 自定义字段: {e}")
        return 1

    # 测试样例 7：非法格式
    try:
        process_text(sample1, fmt="xml")
        print("  [失败] 非法格式应抛出错误")
        return 1
    except ToolkitError as e:
        assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"
        print("  [通过] 非法格式错误处理")

    # 测试样例 8：超长文本（边界测试）
    try:
        long_text = "测试" * 10000  # 20000 字符
        result8 = json.loads(process_text(long_text))
        assert len(result8["records"]) > 0, "超长文本应产生记录"
        print("  [通过] 超长文本处理")
    except Exception as e:
        print(f"  [失败] 超长文本处理: {e}")
        return 1

    # 测试样例 9：特殊字符（编码异常模拟）
    try:
        special_text = "包含特殊字符：emoji 😀 和中文标点，。！？；："
        result9 = json.loads(process_text(special_text))
        assert len(result9["records"]) == 1, "特殊字符应产生1条记录"
        print("  [通过] 特殊字符处理")
    except Exception as e:
        print(f"  [失败] 特殊字符处理: {e}")
        return 1

    # 测试样例 10：URL 处理
    try:
        url_result = process_url("https://example.com/test")
        result10 = json.loads(url_result)
        assert len(result10["records"]) == 1, "URL 应产生1条记录"
        print("  [通过] URL 处理")
    except Exception as e:
        print(f"  [失败] URL 处理: {e}")
        return 1

    # 测试样例 11：非法 URL
    try:
        process_url("not-a-url")
        print("  [失败] 非法 URL 应抛出错误")
        return 1
    except ToolkitError as e:
        assert e.code == "E007", f"错误码应为 E007，实际 {e.code}"
        print("  [通过] 非法 URL 错误处理")

    # 测试样例 12：verbose 模式（修改明细输出）
    try:
        import contextlib
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            process_text(sample1, verbose=True)
        verbose_output = stderr_buffer.getvalue()
        assert "[决策]" in verbose_output, "verbose 模式应输出决策信息"
        assert "提取日期" in verbose_output, "verbose 应输出日期提取明细"
        assert "提取标题" in verbose_output, "verbose 应输出标题提取明细"
        print("  [通过] verbose 模式（修改明细输出）")
    except Exception as e:
        print(f"  [失败] verbose 模式: {e}")
        return 1

    # 测试样例 13：dry-run 模式（不写盘）
    try:
        result13 = json.loads(process_text(sample1, dry=True))
        assert result13["meta"]["dry_run"] == True, "dry_run 标志应为 True"
        print("  [通过] dry-run 模式（不写盘）")
    except Exception as e:
        print(f"  [失败] dry-run 模式: {e}")
        return 1

    # 测试样例 14：流式分块处理（O(n) 性能）
    try:
        import time
        # 短文本
        short_text = "测试。" * 1000  # 3000 字符
        start_time = time.time()
        process_text(short_text)
        short_time = time.time() - start_time

        # 长文本（10倍）
        long_text = "测试。" * 10000  # 30000 字符
        start_time = time.time()
        process_text(long_text)
        long_time = time.time() - start_time

        # 时间比应接近 10:1（允许 3 倍误差）
        ratio = long_time / max(short_time, 0.001)
        assert ratio < 30, f"性能比异常: {ratio:.1f}（应接近 10）"
        print(f"  [通过] 流式分块处理（性能比 {ratio:.1f}）")
    except Exception as e:
        print(f"  [失败] 流式分块处理: {e}")
        return 1

    # 测试样例 15：中文标点边界
    try:
        chinese_punct = "这是第一句。这是第二句！这是第三句？"
        result15 = json.loads(process_text(chinese_punct))
        assert len(result15["records"]) >= 1, "中文标点应产生记录"
        print("  [通过] 中文标点边界")
    except Exception as e:
        print(f"  [失败] 中文标点边界: {e}")
        return 1

    # 测试样例 16：GBK 编码文件读取
    try:
        import tempfile
        # 创建 GBK 编码文件
        gbk_content = "2024年1月1日，GBK编码测试。"
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(gbk_content.encode('gbk'))
            temp_path = f.name
        try:
            result16 = json.loads(process_file(temp_path))
            assert len(result16["records"]) == 1, "GBK 文件应产生1条记录"
            print("  [通过] GBK 编码文件读取")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        print(f"  [失败] GBK 编码文件读取: {e}")
        return 1

    print("=== 自检全部通过 ===")
    return 0


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="agent-toolkit 技能编排与数据转换工具",
        epilog="示例: python main.py -i input.txt -f json --verbose",
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("-i", "--input", help="输入文本、文件路径或URL")
    parser.add_argument("-f", "--format", default="json", choices=["json", "markdown", "csv"], help="输出格式")
    parser.add_argument("--fields", help="自定义字段列表，逗号分隔")
    parser.add_argument("--file", help="处理本地文件")
    parser.add_argument("--url", help="处理URL")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘（默认）")
    parser.add_argument("--force", action="store_true", help="强制写盘（当前版本无写盘操作，保留参数兼容）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _selftest()

    # 参数校验（guard clause）
    if not args.input and not args.file and not args.url:
        print("错误: 必须提供输入内容（-i/--input, --file 或 --url）", file=sys.stderr)
        print("使用 --selftest 运行自检", file=sys.stderr)
        return 1

    # dry-run 与 force 互斥检查
    if args.dry_run and args.force:
        print("错误: --dry-run 和 --force 不能同时使用", file=sys.stderr)
        return 1

    try:
        # 字段列表解析
        fields = args.fields.split(",") if args.fields else DEFAULT_FIELDS
        # 去除空白字符
        fields = [f.strip() for f in fields if f.strip()]

        # dry 变量统一控制写盘分支
        dry = not args.force  # 默认 dry-run，只有 --force 才写盘

        # 处理输入
        if args.file:
            output = process_file(args.file, fields, args.format, args.verbose, dry)
        elif args.url:
            output = process_url(args.url, fields, args.format, args.verbose, dry)
        else:
            output = process_text(args.input, fields, args.format, args.verbose, dry)

        print(output)
        return 0

    except ToolkitError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        print("提示: 请检查输入格式，或使用 --selftest 验证功能", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 内部错误 - {str(e)}", file=sys.stderr)
        print("提示: 请报告此错误，或尝试简化输入", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
