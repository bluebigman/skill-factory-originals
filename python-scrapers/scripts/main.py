#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
python-scrapers 技能独立实现
============================
功能：网页/文件/原始数据 -> 结构化表格（CSV/Markdown）
     支持批量处理、字段映射、简单清洗。

仅依据功能规格文档实现，clean-room 重写。
依赖：仅 Python 标准库（无需 pip install）。
"""

import argparse
import csv
import html
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_INPUT_TYPE = "E001"      # 输入类型不支持
ERR_FILE_READ = "E002"       # 文件读取失败
ERR_HTTP_FETCH = "E003"      # 网络请求失败（本实现不主动联网，保留码位）
ERR_PARSE_FAIL = "E004"      # 解析失败
ERR_MAPPING_INVALID = "E005" # 字段映射配置非法
ERR_EMPTY_DATA = "E006"      # 数据源为空或无有效行
ERR_OUTPUT_WRITE = "E007"    # 输出写入失败
ERR_BATCH_ABORT = "E008"     # 批量处理中断
ERR_INTERNAL = "E009"        # 内部未知错误
ERR_USAGE = "E010"           # 命令行参数错误


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _strip_html_tags(text: str) -> str:
    """去除 HTML 标签，返回纯文本。"""
    if not text:
        return ""
    # 移除注释
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 移除脚本/样式块
    text = re.sub(r"<(script|style)[^>]*>.*?</\\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # 移除所有标签
    text = re.sub(r"<[^>]+>", " ", text)
    # 反转义常见实体
    text = html.unescape(text)
    # 压缩空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_date(text: str) -> str:
    """
    宽松的日期规范化：尝试提取 YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY年M月D日。
    若无法识别，原样返回。
    """
    if not text:
        return text
    s = str(text).strip()
    # 匹配 YYYY-MM-DD 或 YYYY/MM/DD 或 YYYY年M月D日
    m = re.search(r"(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})", s)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}-{mo}-{d}"
    return s


def _to_number(value: Any) -> Any:
    """尝试转为 int/float，失败返回原值。"""
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip().replace(",", "")
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return value


# ---------------------------------------------------------------------------
# 数据源解析
# ---------------------------------------------------------------------------
def parse_csv(text: str) -> List[Dict[str, str]]:
    """解析 CSV 文本为字典列表（首行为表头）。"""
    # 使用 splitlines 处理换行符
    lines = text.strip().splitlines()
    if not lines:
        return []
    
    # 解析表头
    headers = [h.strip() for h in lines[0].split(",")]
    
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        # 处理简单 CSV（支持引号）
        values = []
        current = ""
        in_quotes = False
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                values.append(current.strip())
                current = ""
            else:
                current += char
        values.append(current.strip())
        
        # 确保值数量与表头一致
        row = {}
        for i, header in enumerate(headers):
            row[header] = values[i] if i < len(values) else ""
        rows.append(row)
    
    return rows


def parse_json(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为字典列表。支持顶层为数组或对象。"""
    data = json.loads(text)
    if isinstance(data, dict):
        # 尝试从常见键中提取列表
        for key in ("data", "rows", "items", "list", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            # 若对象本身是单行，包装为列表
            data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON 顶层既不是数组也不是可识别的对象")
    # 确保每个元素是字典
    rows = []
    for item in data:
        if isinstance(item, dict):
            rows.append({str(k): v for k, v in item.items()})
        else:
            rows.append({"value": item})
    return rows


def parse_xml(text: str) -> List[Dict[str, str]]:
    """解析 XML 文本为字典列表（每个元素一行，子元素为字段）。"""
    root = ET.fromstring(text)
    rows = []
    # 找到重复的子元素作为行
    if len(root) > 0:
        for child in root:
            row = {}
            # 子元素的子元素作为字段
            for sub in child:
                tag = sub.tag.split("}")[-1]  # 去除命名空间
                row[tag] = (sub.text or "").strip()
            if row:
                rows.append(row)
    return rows


def parse_html_tables(text: str) -> List[List[Dict[str, str]]]:
    """
    解析 HTML 中所有 <table>，每个表格转换为字典列表。
    返回表格列表（每个表格是行字典列表）。
    """
    # 简单正则提取表格块（不依赖第三方库）
    tables = []
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL | re.IGNORECASE)
    tr_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)

    for tm in table_pattern.finditer(text):
        headers: List[str] = []
        rows: List[Dict[str, str]] = []
        for rm in tr_pattern.finditer(tm.group(1)):
            # 提取所有 th/td 内容
            all_cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", rm.group(1), re.DOTALL | re.IGNORECASE)
            cleaned = [_strip_html_tags(c) for c in all_cells]
            if not headers:
                # 第一行作为表头（若含 th）
                if re.search(r"<th", rm.group(1), re.IGNORECASE):
                    headers = cleaned
                    continue
                else:
                    headers = [f"col{i+1}" for i in range(len(cleaned))]
            if cleaned:
                row = {}
                for i, val in enumerate(cleaned):
                    key = headers[i] if i < len(headers) else f"col{i+1}"
                    row[key] = val
                rows.append(row)
        if rows:
            tables.append(rows)
    return tables


def load_source(source: str, source_type: str = "auto") -> List[Dict[str, Any]]:
    """
    从文本加载数据，自动或指定类型解析。
    source_type: auto/csv/json/xml/html
    返回统一的行字典列表。
    """
    text = source.strip()
    if not text:
        raise ValueError("数据源为空")

    if source_type == "auto":
        # 自动检测
        if text.startswith("{"):
            return parse_json(text)
        if text.startswith("<"):
            # 尝试 XML 或 HTML
            if "<table" in text.lower():
                tables = parse_html_tables(text)
                if tables:
                    return tables[0]  # 取第一个表格
                return []
            return parse_xml(text)
        # 默认按 CSV 处理
        return parse_csv(text)
    elif source_type == "csv":
        return parse_csv(text)
    elif source_type == "json":
        return parse_json(text)
    elif source_type == "xml":
        return parse_xml(text)
    elif source_type == "html":
        tables = parse_html_tables(text)
        if tables:
            return tables[0]
        return []
    else:
        raise ValueError(f"不支持的来源类型: {source_type}")


# ---------------------------------------------------------------------------
# 字段映射与清洗
# ---------------------------------------------------------------------------
def apply_mapping(rows: List[Dict[str, Any]],
                  mapping: Dict[str, str],
                  transforms: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, Any]]:
    """
    字段映射与转换。
    mapping: {目标字段: 源字段} 或 {目标字段: "源字段1|源字段2"}（合并）
             {目标字段: "源字段1|源字段2|SPLIT|分隔符"} 可拆分
    transforms: {目标字段: ["strip", "date", "number", "upper", "lower"]}
    """
    transforms = transforms or {}
    result = []
    for row in rows:
        new_row = {}
        for target, source_expr in mapping.items():
            # 处理合并/拆分表达式
            parts = str(source_expr).split("|")
            if "SPLIT" in parts:
                # 拆分：源字段|SPLIT|分隔符
                idx = parts.index("SPLIT")
                src_key = parts[0]
                sep = parts[idx+1] if idx+1 < len(parts) else ","
                raw = str(row.get(src_key, ""))
                values = [v.strip() for v in raw.split(sep)]
                new_row[target] = values
            else:
                # 合并多个源字段
                values = []
                for p in parts:
                    v = row.get(p.strip(), "")
                    if v is not None:
                        values.append(str(v))
                new_row[target] = " ".join(values) if values else ""

            # 应用转换
            if target in transforms:
                val = new_row[target]
                for op in transforms[target]:
                    if op == "strip":
                        val = str(val).strip()
                    elif op == "date":
                        val = _normalize_date(str(val))
                    elif op == "number":
                        val = _to_number(val)
                    elif op == "upper":
                        val = str(val).upper()
                    elif op == "lower":
                        val = str(val).lower()
                new_row[target] = val
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def to_csv(rows: List[Dict[str, Any]]) -> str:
    """转为 CSV 字符串。"""
    if not rows:
        return ""
    output = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        # 将列表值转为字符串
        clean = {k: (",".join(v) if isinstance(v, list) else v) for k, v in row.items()}
        writer.writerow(clean)
    return output.getvalue()


def to_markdown(rows: List[Dict[str, Any]]) -> str:
    """转为 Markdown 表格字符串。"""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        cells = []
        for h in headers:
            v = row.get(h, "")
            if isinstance(v, list):
                v = ", ".join(v)
            cells.append(str(v).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_text(source: str,
                 source_type: str = "auto",
                 mapping: Optional[Dict[str, str]] = None,
                 transforms: Optional[Dict[str, List[str]]] = None,
                 output_format: str = "csv") -> str:
    """
    完整处理流程：加载 -> 映射 -> 转换 -> 输出。
    返回字符串结果。
    """
    try:
        rows = load_source(source, source_type)
        if not rows:
            raise ValueError("未提取到任何数据行")
        if mapping:
            rows = apply_mapping(rows, mapping, transforms)
        if output_format == "csv":
            return to_csv(rows)
        elif output_format == "markdown":
            return to_markdown(rows)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    except Exception as e:
        raise RuntimeError(f"{ERR_PARSE_FAIL}: {e}") from e


# ---------------------------------------------------------------------------
# 命令行
# ---------------------------------------------------------------------------
def _selftest() -> int:
    """内置自检：使用硬编码样例数据验证核心逻辑，不读外部文件、不联网。"""
    print("[selftest] 开始自检...")
    errors = []

    # --- 测试 1: CSV 解析 ---
    csv_data = "name,age,city\nalice,30,beijing\nbob,25,shanghai\n"
    try:
        rows = load_source(csv_data, "csv")
        assert len(rows) == 2, f"CSV 行数错误: {len(rows)}"
        assert rows[0]["name"] == "alice", "CSV 首行名称错误"
        print("[selftest] CSV 解析: PASS")
    except Exception as e:
        errors.append(f"CSV 解析失败: {e}")
        print(f"[selftest] CSV 解析: FAIL ({e})")

    # --- 测试 2: JSON 解析 ---
    json_data = '{"items": [{"id": 1, "val": "x"}, {"id": 2, "val": "y"}]}'
    try:
        rows = load_source(json_data, "json")
        assert len(rows) == 2, f"JSON 行数错误: {len(rows)}"
        assert rows[1]["id"] == 2, "JSON 第二行 id 错误"
        print("[selftest] JSON 解析: PASS")
    except Exception as e:
        errors.append(f"JSON 解析失败: {e}")
        print(f"[selftest] JSON 解析: FAIL ({e})")

    # --- 测试 3: HTML 表格解析 ---
    html_data = """<html><body><table>
        <tr><th>产品</th><th>价格</th></tr>
        <tr><td>苹果</td><td>5.5</td></tr>
        <tr><td>香蕉</td><td>3.2</td></tr>
    </table></body></html>"""
    try:
        rows = load_source(html_data, "html")
        assert len(rows) == 2, f"HTML 行数错误: {len(rows)}"
        assert rows[0]["产品"] == "苹果", "HTML 首行产品错误"
        print("[selftest] HTML 表格解析: PASS")
    except Exception as e:
        errors.append(f"HTML 解析失败: {e}")
        print(f"[selftest] HTML 表格解析: FAIL ({e})")

    # --- 测试 4: 字段映射与转换 ---
    src_rows = [{"发布信息": "2024-01-15 10:30", "金额": "1,234.56"}]
    mapping = {"日期": "发布信息", "金额数值": "金额"}
    transforms = {"日期": ["date"], "金额数值": ["number"]}
    try:
        result = apply_mapping(src_rows, mapping, transforms)
        assert len(result) == 1, "映射结果行数错误"
        assert result[0]["日期"] == "2024-01-15", f"日期转换错误: {result[0]['日期']}"
        assert isinstance(result[0]["金额数值"], float), "金额类型错误"
        assert result[0]["金额数值"] > 1000, "金额数值范围错误"
        print("[selftest] 字段映射/转换: PASS")
    except Exception as e:
        errors.append(f"字段映射失败: {e}")
        print(f"[selftest] 字段映射/转换: FAIL ({e})")

    # --- 测试 5: 输出格式 ---
    out_rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    try:
        csv_out = to_csv(out_rows)
        assert "a,b" in csv_out, "CSV 表头缺失"
        assert csv_out.count("\n") >= 2, "CSV 行数不足"
        md_out = to_markdown(out_rows)
        assert "| a | b |" in md_out, "Markdown 表头缺失"
        assert "---" in md_out, "Markdown 分隔线缺失"
        print("[selftest] 输出格式: PASS")
    except Exception as e:
        errors.append(f"输出格式失败: {e}")
        print(f"[selftest] 输出格式: FAIL ({e})")

    # --- 测试 6: 完整流程 ---
    try:
        full_result = process_text(
            "名称,备注\n苹果,好吃的水果\n香蕉,热带水果",
            source_type="csv",
            mapping={"产品名": "名称", "描述": "备注"},
            transforms={"描述": ["strip"]},
            output_format="markdown"
        )
        assert "产品名" in full_result, "完整流程输出缺少映射字段"
        assert "苹果" in full_result, "完整流程输出缺少数据"
        print("[selftest] 完整流程: PASS")
    except Exception as e:
        errors.append(f"完整流程失败: {e}")
        print(f"[selftest] 完整流程: FAIL ({e})")

    # --- 汇总 ---
    if errors:
        print(f"[selftest] 失败项: {len(errors)}")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("[selftest] 全部通过 (6/6)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="python-scrapers: 网页/文件/原始数据 -> 结构化表格",
        epilog="示例: python main.py --input data.csv --type csv --format markdown"
    )
    parser.add_argument("--input", "-i", help="输入文件路径（或使用 --text 直接传文本）")
    parser.add_argument("--text", "-t", help="直接传入文本数据（优先级高于 --input）")
    parser.add_argument("--type", "-ty", default="auto",
                        choices=["auto", "csv", "json", "xml", "html"],
                        help="数据源类型")
    parser.add_argument("--format", "-f", default="csv",
                        choices=["csv", "markdown"],
                        help="输出格式")
    parser.add_argument("--mapping", "-m", help="字段映射 JSON: {\"目标\":\"源\"} 或 {\"目标\":\"源1|源2\"}")
    parser.add_argument("--transforms", "-tr", help="转换规则 JSON: {\"目标\":[\"strip\",\"date\",\"number\",\"upper\",\"lower\"]}")
    parser.add_argument("--output", "-o", help="输出文件路径（默认 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    if args.selftest:
        return _selftest()

    # 获取数据源
    try:
        if args.text is not None:
            source_text = args.text
        elif args.input:
            path = Path(args.input)
            if not path.exists():
                print(f"{ERR_FILE_READ}: 文件不存在: {args.input}", file=sys.stderr)
                return 1
            source_text = path.read_text(encoding="utf-8", errors="replace")
        else:
            # 从 stdin 读取
            source_text = sys.stdin.read()
    except Exception as e:
        print(f"{ERR_FILE_READ}: 读取输入失败: {e}", file=sys.stderr)
        return 1

    # 解析映射配置
    mapping = None
    transforms = None
    try:
        if args.mapping:
            mapping = json.loads(args.mapping)
            if not isinstance(mapping, dict):
                raise ValueError("mapping 必须是 JSON 对象")
        if args.transforms:
            transforms = json.loads(args.transforms)
            if not isinstance(transforms, dict):
                raise ValueError("transforms 必须是 JSON 对象")
    except Exception as e:
        print(f"{ERR_MAPPING_INVALID}: 配置解析失败: {e}", file=sys.stderr)
        return 1

    # 执行处理
    try:
        result = process_text(
            source_text,
            source_type=args.type,
            mapping=mapping,
            transforms=transforms,
            output_format=args.format
        )
    except Exception as e:
        print(f"{ERR_PARSE_FAIL}: 处理失败: {e}", file=sys.stderr)
        return 1

    # 输出
    try:
        if args.output:
            if not dry_run or getattr(args, "force", False):
                Path(args.output).write_text(result, encoding="utf-8")
        else:
            print(result)
    except Exception as e:
        print(f"{ERR_OUTPUT_WRITE}: 输出失败: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
