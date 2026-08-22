#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ambition — 纯文本 → 结构化 JSON 转换执行器

将任意数据源（文本、文件、URL）转化为结构化结果，保留关键信息并标注置信度。
纯标准库实现，零第三方依赖。

用法示例：
    python run.py --input "张三，电话13800138000" --format json
    python run.py --input data.csv --format json --output result.json
    python run.py --input "https://example.com" --format markdown
    python run.py --batch --input data/ --output results/
    python run.py --selftest
"""
from __future__ import annotations
dry_run = False  # v3.274 模块级 dry-run 标志

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# 版本信息
VERSION = "2.0.3"

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "文件不存在",
    "E003": "文件读取失败",
    "E004": "URL抓取失败",
    "E005": "输出写入失败",
    "E006": "参数校验失败",
    "E007": "批量处理中断",
}

# 支持的输入格式
SUPPORTED_FORMATS = ["json", "markdown", "csv", "text"]


class AmbitionError(Exception):
    """ambition 自定义异常，携带错误码"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def get_timestamp() -> str:
    """获取 UTC 时间戳"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text_safe(path: Union[str, Path]) -> str:
    """多编码安全读取文件（UTF-8 → GBK → GB18030 三级回退）"""
    p = Path(path)
    if not p.exists():
        raise AmbitionError("E002", f"文件不存在: {path}")

    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(p, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError) as e:
            last_error = e
            continue

    # 最终回退：使用 replace 模式
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        raise AmbitionError("E003", f"文件读取失败: {e}")


def read_text_stream(path: Union[str, Path]) -> str:
    """流式读取文件内容，避免大文件一次性加载"""
    p = Path(path)
    if not p.exists():
        raise AmbitionError("E002", f"文件不存在: {path}")

    chunks = []
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(p, encoding=enc, errors="replace") as f:
                for line in f:
                    chunks.append(line)
            return "".join(chunks)
        except (UnicodeDecodeError, OSError) as e:
            last_error = e
            continue

    # 最终回退
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                chunks.append(line)
        return "".join(chunks)
    except OSError as e:
        raise AmbitionError("E003", f"文件读取失败: {e}")


def fetch_url(url: str, timeout: int = 10, max_retries: int = 3) -> str:
    """抓取 URL 内容，带超时和指数退避重试"""
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = resp.read()
                # 尝试多种编码解码
                for enc in ("utf-8", "gbk", "gb18030"):
                    try:
                        return data.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return data.decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError) as e:
            if attempt == max_retries - 1:
                raise AmbitionError("E004", f"URL抓取失败: {e}")
            # 指数退避
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    raise AmbitionError("E004", "URL抓取失败")


def extract_fields(text: str, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """从文本中提取字段，返回字段列表（含置信度）"""
    if not text or not text.strip():
        return []

    # 定义字段提取器（正则 + 简单规则）
    extractors = {
        "日期": lambda t: _extract_date(t),
        "姓名": lambda t: _extract_person_name(t),
        "金额": lambda t: _extract_amount(t),
        "电话": lambda t: _extract_phone(t),
        "邮箱": lambda t: _extract_email(t),
        "编号": lambda t: _extract_id(t),
        "事项": lambda t: _extract_event(t),
    }

    # 如果指定了字段，只提取指定字段
    if fields:
        field_names = [f.strip() for f in fields if f.strip()]
    else:
        # 自动识别所有支持的字段
        field_names = list(extractors.keys())

    results = []
    for field_name in field_names:
        if field_name in extractors:
            value, confidence, method = extractors[field_name](text)
            if value is not None:
                results.append({
                    "name": field_name,
                    "value": value,
                    "confidence": confidence,
                    "extraction_method": method,
                })

    return results


def _extract_date(text: str) -> tuple:
    """提取日期字段"""
    patterns = [
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日", 0.98, "regex_date_cn"),
        (r"(\d{4})-(\d{1,2})-(\d{1,2})", 0.99, "regex_date_iso"),
        (r"(\d{4})/(\d{1,2})/(\d{1,2})", 0.99, "regex_date_slash"),
    ]
    for pattern, conf, method in patterns:
        m = re.search(pattern, text)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}", conf, method
    return None, 0.0, ""


def _extract_person_name(text: str) -> tuple:
    """提取人名（简单规则：常见姓氏 + 1-2 个汉字）"""
    # 常见姓氏列表
    surnames = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    pattern = rf"([{surnames}][\u4e00-\u9fa5]{{1,2}})"
    m = re.search(pattern, text)
    if m:
        name = m.group(1)
        # 排除常见非人名词汇
        if name not in ("中国", "美国", "日本", "公司", "项目"):
            return name, 0.85, "person_name"
    return None, 0.0, ""


def _extract_amount(text: str) -> tuple:
    """提取金额字段"""
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*元", 0.97, "currency_yuan"),
        (r"(\d+(?:\.\d+)?)\s*美元", 0.96, "currency_usd"),
        (r"(\d+(?:\.\d+)?)\s*人民币", 0.96, "currency_rmb"),
    ]
    for pattern, conf, method in patterns:
        m = re.search(pattern, text)
        if m:
            try:
                amount = float(m.group(1))
                return amount, conf, method
            except ValueError:
                continue
    return None, 0.0, ""


def _extract_phone(text: str) -> tuple:
    """提取电话号码"""
    patterns = [
        (r"1[3-9]\d{9}", 0.99, "phone_mobile"),
        (r"0\d{2,3}-?\d{7,8}", 0.95, "phone_landline"),
    ]
    for pattern, conf, method in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(0), conf, method
    return None, 0.0, ""


def _extract_email(text: str) -> tuple:
    """提取邮箱地址"""
    pattern = r"[\w.+-]+@[\w-]+\.[\w.-]+"
    m = re.search(pattern, text)
    if m:
        return m.group(0), 0.98, "regex_email"
    return None, 0.0, ""


def _extract_id(text: str) -> tuple:
    """提取编号（如订单号、合同号）"""
    patterns = [
        (r"(?:订单号|合同号|编号)[:：]\s*([A-Za-z0-9-]+)", 0.95, "id_labeled"),
        (r"\b[A-Z]{2,5}\d{6,}\b", 0.90, "id_pattern"),
    ]
    for pattern, conf, method in patterns:
        m = re.search(pattern, text)
        if m:
            return m.group(1) if m.lastindex else m.group(0), conf, method
    return None, 0.0, ""


def _extract_event(text: str) -> tuple:
    """提取事项/事件（基于关键词匹配）"""
    keywords = ["报销", "差旅", "采购", "会议", "培训", "招聘", "请假", "加班"]
    for kw in keywords:
        if kw in text:
            return kw, 0.80, "keyword_match"
    return None, 0.0, ""


def calculate_overall_confidence(fields: List[Dict[str, Any]]) -> float:
    """计算整体置信度（字段置信度的平均值）"""
    if not fields:
        return 0.0
    return sum(f["confidence"] for f in fields) / len(fields)


def format_output(data: Dict[str, Any], fmt: str) -> str:
    """格式化输出"""
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "markdown":
        return _format_markdown(data)
    elif fmt == "csv":
        return _format_csv(data)
    elif fmt == "text":
        return _format_text(data)
    else:
        raise AmbitionError("E006", f"不支持的输出格式: {fmt}")


def _format_markdown(data: Dict[str, Any]) -> str:
    """格式化为 Markdown 表格"""
    lines = ["| 字段 | 值 | 置信度 | 提取方法 |", "|------|-----|--------|----------|"]
    for field in data.get("fields", []):
        lines.append(f"| {field['name']} | {field['value']} | {field['confidence']:.2f} | {field['extraction_method']} |")
    return "\n".join(lines)


def _format_csv(data: Dict[str, Any]) -> str:
    """格式化为 CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["字段", "值", "置信度", "提取方法"])
    for field in data.get("fields", []):
        writer.writerow([field["name"], field["value"], field["confidence"], field["extraction_method"]])
    return output.getvalue()


def _format_text(data: Dict[str, Any]) -> str:
    """格式化为纯文本"""
    lines = []
    for field in data.get("fields", []):
        lines.append(f"{field['name']}: {field['value']} (置信度: {field['confidence']:.2f})")
    return "\n".join(lines)


def write_file_atomic(path: Union[str, Path], content: str) -> None:
    """原子化写入文件（先写临时文件再重命名）"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(p))
    except OSError as e:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise AmbitionError("E005", f"输出写入失败: {e}")


def process_text(text: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """处理单条文本，返回结构化结果"""
    start_time = time.time()
    extracted_fields = extract_fields(text, fields)
    overall_conf = calculate_overall_confidence(extracted_fields)
    processing_time = int((time.time() - start_time) * 1000)

    return {
        "schema_version": "1.0",
        "input_preview": text[:100] + ("..." if len(text) > 100 else ""),
        "fields": extracted_fields,
        "overall_confidence": round(overall_conf, 3),
        "processing_time_ms": processing_time,
    }


def process_batch(input_dir: Union[str, Path], output_dir: Union[str, Path],
                  fields: Optional[List[str]] = None, dry_run: bool = False,
                  verbose: bool = False) -> Dict[str, Any]:
    """批量处理目录下的所有 .txt 文件"""
    in_dir = Path(input_dir)
    out_dir = Path(output_dir)

    if not in_dir.exists() or not in_dir.is_dir():
        raise AmbitionError("E002", f"输入目录不存在: {input_dir}")

    records = []
    txt_files = sorted(in_dir.glob("*.txt"))

    if not txt_files:
        if verbose:
            print(f"警告: 目录 {input_dir} 下没有 .txt 文件", file=sys.stderr)
        return {
            "schema_version": "1.0",
            "batch_size": 0,
            "records": [],
            "batch_summary": {"avg_confidence": 0.0, "low_confidence_count": 0},
        }

    for idx, file_path in enumerate(txt_files, 1):
        try:
            text = read_text_stream(file_path)
            result = process_text(text, fields)

            if dry_run:
                if verbose:
                    print(f"[DRY-RUN] 将处理: {file_path.name} → {out_dir / (file_path.stem + '.json')}")
                records.append({"id": idx, "filename": file_path.name, **result})
            else:
                out_file = out_dir / (file_path.stem + ".json")
                write_file_atomic(out_file, json.dumps(result, ensure_ascii=False, indent=2))
                if verbose:
                    print(f"已处理: {file_path.name} → {out_file}")
                records.append({"id": idx, "filename": file_path.name, **result})

        except AmbitionError as e:
            if verbose:
                print(f"警告: 处理 {file_path.name} 失败: {e}", file=sys.stderr)
            records.append({"id": idx, "filename": file_path.name, "error": str(e)})

    # 计算批量统计
    confidences = [r.get("overall_confidence", 0.0) for r in records if "overall_confidence" in r]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    low_conf_count = sum(1 for c in confidences if c < 0.6)

    return {
        "schema_version": "1.0",
        "batch_size": len(records),
        "records": records,
        "batch_summary": {
            "avg_confidence": round(avg_conf, 3),
            "low_confidence_count": low_conf_count,
        },
    }


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("运行自检...")
    failures = 0

    # 测试 1: 单条文本提取
    try:
        result = process_text("2024年3月15日张三报销差旅费1200元")
        assert result["fields"], "应提取到字段"
        assert result["overall_confidence"] > 0.5, "置信度应大于 0.5"
        print("  ✓ 单条文本提取")
    except AssertionError as e:
        print(f"  ✗ 单条文本提取失败: {e}")
        failures += 1

    # 测试 2: 指定字段提取
    try:
        result = process_text("张三 13800138000", fields=["姓名", "电话"])
        field_names = [f["name"] for f in result["fields"]]
        assert "姓名" in field_names, "应包含姓名字段"
        assert "电话" in field_names, "应包含电话字段"
        print("  ✓ 指定字段提取")
    except AssertionError as e:
        print(f"  ✗ 指定字段提取失败: {e}")
        failures += 1

    # 测试 3: 空输入处理
    try:
        result = process_text("")
        assert result["fields"] == [], "空输入应返回空字段列表"
        print("  ✓ 空输入处理")
    except AssertionError as e:
        print(f"  ✗ 空输入处理失败: {e}")
        failures += 1

    # 测试 4: 中文标点/编码
    try:
        result = process_text("张三，电话：13800138000，邮箱：zhangsan@example.com")
        field_names = [f["name"] for f in result["fields"]]
        assert "电话" in field_names, "应提取电话字段"
        assert "邮箱" in field_names, "应提取邮箱字段"
        print("  ✓ 中文标点/编码处理")
    except AssertionError as e:
        print(f"  ✗ 中文标点/编码处理失败: {e}")
        failures += 1

    # 测试 5: 批量处理
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = Path(tmpdir) / "test.txt"
            if not dry_run:
                test_file.write_text("2024年3月15日张三报销差旅费1200元", encoding="utf-8")

            result = process_batch(tmpdir, Path(tmpdir) / "out", dry_run=True)
            assert result["batch_size"] == 1, "应处理 1 个文件"
            print("  ✓ 批量处理")
    except AssertionError as e:
        print(f"  ✗ 批量处理失败: {e}")
        failures += 1

    # 测试 6: 输出格式化
    try:
        data = {"fields": [{"name": "测试", "value": "值", "confidence": 0.9, "extraction_method": "test"}]}
        for fmt in SUPPORTED_FORMATS:
            output = format_output(data, fmt)
            assert output, f"格式 {fmt} 应产生输出"
        print("  ✓ 输出格式化")
    except AssertionError as e:
        print(f"  ✗ 输出格式化失败: {e}")
        failures += 1

    if failures == 0:
        print("自检通过 ✓")
        return 0
    else:
        print(f"自检失败: {failures} 项未通过 ✗")
        return 1


def main() -> int:
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="ambition — 纯文本 → 结构化 JSON 转换",
        epilog="示例: python run.py --input '2024年3月15日张三报销差旅费1200元'"
    )
    parser.add_argument("--input", "-i", help="输入文本、文件路径或 URL")
    parser.add_argument("--fields", "-f", help="指定提取字段，逗号分隔（如: 日期,金额,姓名）")
    parser.add_argument("--format", "-fmt", choices=SUPPORTED_FORMATS, default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--batch", "-b", action="store_true", help="批量处理模式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"ambition {VERSION}")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input:
        parser.error("必须提供 --input 参数")

    # 解析字段列表
    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    try:
        # 批量模式
        if args.batch:
            input_path = Path(args.input)
            if not input_path.is_dir():
                raise AmbitionError("E006", f"批量模式输入必须是目录: {args.input}")

            output_dir = Path(args.output) if args.output else Path("output")
            result = process_batch(input_path, output_dir, fields, args.dry_run, args.verbose)

            if args.dry_run:
                print(f"[DRY-RUN] 将处理 {result['batch_size']} 个文件到 {output_dir}")
                for record in result["records"]:
                    print(f"  - {record.get('filename', '?')}")
            else:
                # 写入批量结果摘要
                if args.output:
                    summary_file = Path(args.output) / "batch_summary.json"
                    write_file_atomic(summary_file, json.dumps(result, ensure_ascii=False, indent=2))
                    print(f"批量处理完成: {result['batch_size']} 个文件")
                    print(f"摘要已写入: {summary_file}")
                else:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        # 单条模式
        input_text = args.input
        # 检查是否为文件路径
        if Path(input_text).exists():
            input_text = read_text_stream(input_text)
        # 检查是否为 URL
        elif input_text.startswith(("http://", "https://")):
            input_text = fetch_url(input_text)

        result = process_text(input_text, fields)
        output = format_output(result, args.format)

        if args.output:
            if args.dry_run:
                print(f"[DRY-RUN] 将写入: {args.output}")
                print(output)
            else:
                write_file_atomic(args.output, output)
                print(f"结果已写入: {args.output}")
        else:
            print(output)

        return 0

    except AmbitionError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
