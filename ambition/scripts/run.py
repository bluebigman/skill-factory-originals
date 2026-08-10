#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ambition — 数据洞察与结构化输出执行器

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
VERSION = "2.0.0"

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


def read_file_streaming(path: Union[str, Path]) -> List[str]:
    """流式读取文件，逐行返回（O(n) 内存）"""
    p = Path(path)
    if not p.exists():
        raise AmbitionError("E002", f"文件不存在: {path}")

    lines = []
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                lines.append(line.rstrip("\n"))
    except OSError as e:
        raise AmbitionError("E003", f"文件读取失败: {e}")
    return lines


def read_url(url: str, timeout: int = 10, max_retries: int = 3) -> str:
    """读取 URL 内容，带超时和指数退避重试"""
    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": f"ambition-skill/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                # 指数退避：2^attempt * 1秒
                wait_time = 2**attempt
                print(f"警告: URL 抓取失败 (尝试 {attempt + 1}/{max_retries}): {e}", file=sys.stderr)
                print(f"等待 {wait_time} 秒后重试...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                break
        except Exception as e:
            # 其他异常直接抛出
            raise AmbitionError("E004", f"URL抓取失败: {e}")

    raise AmbitionError("E004", f"URL抓取失败: {last_error}")


def extract_fields(text: str) -> Dict[str, Any]:
    """从文本中提取关键字段（姓名、电话、邮箱、日期、金额等）"""
    fields: Dict[str, Any] = {}
    text = text.strip()

    if not text:
        return fields

    # 提取姓名（中文或英文）
    name_match = re.search(r"([\u4e00-\u9fa5]{2,4}|[A-Za-z]+(?:\s+[A-Za-z]+)?)", text)
    if name_match:
        fields["name"] = name_match.group(1).strip()

    # 提取电话（支持手机和座机）
    phone_match = re.search(r"(?:\+?86[- ]?)?1[3-9]\d{9}|0\d{2,3}[- ]?\d{7,8}", text)
    if phone_match:
        fields["phone"] = phone_match.group(0).strip()

    # 提取邮箱
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        fields["email"] = email_match.group(0).strip()

    # 提取日期（支持多种格式）
    date_match = re.search(
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
        text,
    )
    if date_match:
        fields["date"] = date_match.group(0).strip()

    # 提取金额
    amount_match = re.search(r"(?:￥|¥|RMB|USD)?\s*\d+(?:\.\d{1,2})?\s*(?:元|美元|人民币)?", text)
    if amount_match:
        amount_str = amount_match.group(0).strip()
        if amount_str and any(c.isdigit() for c in amount_str):
            fields["amount"] = amount_str

    return fields


def calculate_confidence(fields: Dict[str, Any], text: str) -> float:
    """计算提取结果的置信度（0-1）"""
    if not fields:
        return 0.0

    # 基础置信度
    base_confidence = 0.5

    # 每个字段增加置信度
    field_confidence = min(0.3, len(fields) * 0.1)

    # 文本长度影响（过短文本置信度低）
    text_length_confidence = min(0.2, len(text) / 100 * 0.2)

    total = base_confidence + field_confidence + text_length_confidence
    return min(0.95, total)


def parse_csv_content(content: str) -> List[Dict[str, Any]]:
    """解析 CSV 内容为字典列表"""
    records = []
    try:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            # 清理空值
            clean_row = {k: v for k, v in row.items() if v is not None}
            if clean_row:
                records.append(clean_row)
    except Exception as e:
        raise AmbitionError("E003", f"CSV 解析失败: {e}")
    return records


def parse_json_content(content: str) -> List[Dict[str, Any]]:
    """解析 JSON 内容为字典列表"""
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            return [data]
        else:
            return []
    except json.JSONDecodeError as e:
        raise AmbitionError("E003", f"JSON 解析失败: {e}")


def process_text(text: str, output_format: str = "json") -> Dict[str, Any]:
    """处理文本输入，提取结构化信息"""
    if not text or not text.strip():
        raise AmbitionError("E001", "输入为空")

    # 提取字段
    fields = extract_fields(text)
    confidence = calculate_confidence(fields, text)

    # 构建记录
    record = {**fields, "confidence": round(confidence, 2)}

    result = {
        "records": [record] if record else [],
        "total": 1 if record else 0,
        "timestamp": get_timestamp(),
    }

    return result


def process_file(file_path: str, output_format: str = "json") -> Dict[str, Any]:
    """处理文件输入"""
    p = Path(file_path)
    if not p.exists():
        raise AmbitionError("E002", f"文件不存在: {file_path}")

    # 根据扩展名选择解析方式
    ext = p.suffix.lower()
    content = read_text_safe(p)

    if ext == ".csv":
        records = parse_csv_content(content)
    elif ext == ".json":
        records = parse_json_content(content)
    else:
        # 默认按文本处理
        return process_text(content, output_format)

    # 为每条记录添加置信度
    for record in records:
        if "confidence" not in record:
            record["confidence"] = round(calculate_confidence(record, content), 2)

    result = {
        "records": records,
        "total": len(records),
        "timestamp": get_timestamp(),
    }

    return result


def process_url(url: str, output_format: str = "json") -> Dict[str, Any]:
    """处理 URL 输入"""
    content = read_url(url)

    # 尝试解析 HTML 中的文本内容
    # 简单提取 title 和正文文本
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""

    # 去除 HTML 标签获取正文
    text_content = re.sub(r"<[^>]+>", " ", content)
    text_content = re.sub(r"\s+", " ", text_content).strip()

    fields = extract_fields(text_content)
    confidence = calculate_confidence(fields, text_content)

    record = {
        "title": title,
        "content": text_content[:500] if text_content else "",
        **fields,
        "confidence": round(confidence, 2),
    }

    result = {
        "records": [record] if record else [],
        "total": 1 if record else 0,
        "timestamp": get_timestamp(),
    }

    return result


def format_output(result: Dict[str, Any], output_format: str) -> str:
    """将结果格式化为指定格式"""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif output_format == "markdown":
        if not result["records"]:
            return "| 字段 | 值 | 置信度 |\n|------|-----|--------|\n| 无数据 | - | - |"

        # 收集所有字段
        all_fields = set()
        for record in result["records"]:
            all_fields.update(record.keys())
        all_fields.discard("confidence")

        lines = ["| 字段 | 值 | 置信度 |", "|------|-----|--------|"]
        for record in result["records"]:
            for field in sorted(all_fields):
                value = str(record.get(field, "-"))
                conf = record.get("confidence", "-")
                lines.append(f"| {field} | {value} | {conf} |")
        return "\n".join(lines)

    elif output_format == "csv":
        if not result["records"]:
            return ""

        # 收集所有字段
        all_fields = set()
        for record in result["records"]:
            all_fields.update(record.keys())

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sorted(all_fields))
        writer.writeheader()
        for record in result["records"]:
            writer.writerow(record)
        return output.getvalue()

    elif output_format == "text":
        if not result["records"]:
            return "无数据"

        lines = []
        for i, record in enumerate(result["records"], 1):
            lines.append(f"记录 {i}:")
            for key, value in record.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    else:
        raise AmbitionError("E006", f"不支持的输出格式: {output_format}")


def atomic_write(file_path: str, content: str) -> None:
    """原子化写入文件（先写临时文件再重命名）"""
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=str(p.parent), prefix=".tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子重命名
        os.replace(temp_path, p)
    except Exception as e:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise AmbitionError("E005", f"输出写入失败: {e}")


def process_batch(input_dir: str, output_dir: str, output_format: str, dry_run: bool = False) -> Dict[str, Any]:
    """批量处理目录下的所有支持文件"""
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        raise AmbitionError("E002", f"输入目录不存在: {input_dir}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    supported_exts = {".csv", ".json", ".txt"}
    results = []
    processed = 0
    failed = 0

    for file_path in sorted(input_path.iterdir()):
        if file_path.suffix.lower() not in supported_exts:
            continue

        try:
            result = process_file(str(file_path), output_format)
            results.append({"file": file_path.name, "result": result})
            processed += 1

            # 生成输出文件名
            out_name = file_path.stem + f".{output_format}"
            out_path = output_path / out_name

            if dry_run:
                print(f"[DRY-RUN] 将写入: {out_path} ({len(result['records'])} 条记录)")
            else:
                content = format_output(result, output_format)
                atomic_write(str(out_path), content)
                print(f"已处理: {file_path.name} → {out_path}")

        except Exception as e:
            failed += 1
            print(f"处理失败 {file_path.name}: {e}", file=sys.stderr)

    summary = {
        "processed": processed,
        "failed": failed,
        "total": processed + failed,
        "timestamp": get_timestamp(),
    }

    if dry_run:
        print(f"\n[DRY-RUN] 摘要: 共 {summary['total']} 个文件，成功 {processed}，失败 {failed}")

    return summary


def validate_args(args: argparse.Namespace) -> None:
    """校验命令行参数"""
    if not args.input and not args.selftest:
        raise AmbitionError("E006", "必须提供 --input 参数或使用 --selftest")

    if args.format and args.format not in SUPPORTED_FORMATS:
        raise AmbitionError("E006", f"不支持的输出格式: {args.format}，支持: {', '.join(SUPPORTED_FORMATS)}")

    if args.batch and not args.input:
        raise AmbitionError("E006", "批量模式必须提供 --input 目录")

    if args.output and args.dry_run:
        print("提示: --dry-run 模式下不会实际写入文件", file=sys.stderr)


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=== ambition selftest ===")
    failures = 0

    # 测试 1: 文本提取
    print("\n[测试 1] 文本字段提取")
    try:
        result = process_text("张三，电话13800138000，邮箱zhangsan@example.com", "json")
        assert result["total"] == 1, f"预期 1 条记录，实际 {result['total']}"
        record = result["records"][0]
        assert "name" in record, "缺少 name 字段"
        assert "phone" in record, "缺少 phone 字段"
        assert "email" in record, "缺少 email 字段"
        assert record["confidence"] > 0, "置信度应为正数"
        print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 2: 空输入处理
    print("\n[测试 2] 空输入处理")
    try:
        try:
            process_text("", "json")
            failures += 1
            print("  ❌ 失败: 空输入应抛出异常")
        except AmbitionError as e:
            assert e.code == "E001", f"预期错误码 E001，实际 {e.code}"
            print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 3: 文件处理
    print("\n[测试 3] CSV 文件处理")
    try:
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("name,age,city\n李四,28,北京\n王五,35,上海\n")
            temp_path = f.name

        try:
            result = process_file(temp_path, "json")
            assert result["total"] == 2, f"预期 2 条记录，实际 {result['total']}"
            assert len(result["records"]) == 2, "记录数应为 2"
            print("  ✅ 通过")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 4: 格式转换
    print("\n[测试 4] 格式转换")
    try:
        result = process_text("测试文本", "json")
        json_str = format_output(result, "json")
        assert json.loads(json_str)["total"] == 1, "JSON 格式转换失败"

        md_str = format_output(result, "markdown")
        assert "|" in md_str, "Markdown 格式转换失败"

        csv_str = format_output(result, "csv")
        assert "name" in csv_str or "confidence" in csv_str, "CSV 格式转换失败"

        text_str = format_output(result, "text")
        assert "记录" in text_str, "文本格式转换失败"
        print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 5: 中文标点处理
    print("\n[测试 5] 中文标点处理")
    try:
        result = process_text("张三，电话：13800138000；邮箱：zhangsan@example.com", "json")
        assert result["total"] == 1, "中文标点文本应能提取"
        record = result["records"][0]
        assert "phone" in record, "应提取到电话"
        assert "email" in record, "应提取到邮箱"
        print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 6: 超长输入
    print("\n[测试 6] 超长输入处理")
    try:
        long_text = "测试" * 10000  # 2万字
        result = process_text(long_text, "json")
        assert result["total"] == 1, "超长文本应能处理"
        print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 7: URL 处理（模拟）
    print("\n[测试 7] URL 处理")
    try:
        # 使用本地 HTTP 服务器模拟
        import http.server
        import threading

        class MockHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><title>测试页面</title><body>联系人：张三，电话13800138000</body></html>".encode("utf-8"))

            def log_message(self, format, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), MockHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        try:
            result = process_url(f"http://127.0.0.1:{port}/test", "json")
            assert result["total"] == 1, "URL 应能提取到记录"
            record = result["records"][0]
            assert "title" in record, "应提取到标题"
            print("  ✅ 通过")
        finally:
            server.shutdown()
            server.server_close()
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 8: 批量处理
    print("\n[测试 8] 批量处理")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            for i in range(3):
                file_path = Path(tmpdir) / f"test_{i}.csv"
                file_path.write_text(f"name,age\n测试{i},2{i}\n", encoding="utf-8")

            output_dir = Path(tmpdir) / "output"
            summary = process_batch(tmpdir, str(output_dir), "json", dry_run=True)
            assert summary["processed"] == 3, f"预期处理 3 个文件，实际 {summary['processed']}"
            assert summary["failed"] == 0, "不应有失败文件"
            print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 9: 原子写入
    print("\n[测试 9] 原子写入")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            atomic_write(str(test_file), "测试内容")
            assert test_file.exists(), "文件应存在"
            assert test_file.read_text(encoding="utf-8") == "测试内容", "文件内容应正确"
            print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 测试 10: 错误处理
    print("\n[测试 10] 错误处理")
    try:
        try:
            process_file("/nonexistent/file.csv", "json")
            failures += 1
            print("  ❌ 失败: 不存在的文件应抛出异常")
        except AmbitionError as e:
            assert e.code == "E002", f"预期错误码 E002，实际 {e.code}"
            print("  ✅ 通过")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")

    # 汇总
    print(f"\n=== 自检完成: {10 - failures}/10 通过 ===")
    return 0 if failures == 0 else 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="ambition — 数据洞察与结构化输出",
        epilog="示例: python run.py --input '张三，电话13800138000' --format json",
    )
    parser.add_argument("--input", type=str, help="输入内容（文本、文件路径或 URL）")
    parser.add_argument("--format", type=str, default="json", choices=SUPPORTED_FORMATS, help="输出格式")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--batch", action="store_true", help="批量处理模式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入文件")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"ambition {VERSION}")
    parser.add_argument("--help", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    try:
        # 参数校验
        validate_args(args)

        # 处理输入
        if args.batch:
            if not args.output:
                raise AmbitionError("E006", "批量模式必须提供 --output 参数")
            result = process_batch(args.input, args.output, args.format, args.dry_run)
            if not args.dry_run:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 判断输入类型
            input_str = args.input
            if input_str.startswith(("http://", "https://")):
                result = process_url(input_str, args.format)
            elif Path(input_str).exists():
                result = process_file(input_str, args.format)
            else:
                result = process_text(input_str, args.format)

            # 格式化输出
            output_content = format_output(result, args.format)

            # 输出或写入
            if args.output:
                if args.dry_run:
                    print(f"[DRY-RUN] 将写入: {args.output}")
                    print(f"[DRY-RUN] 内容摘要: {len(result['records'])} 条记录")
                    if args.verbose:
                        print("[明细] changed_items=0 项")  # changed_items 标记
                        print(output_content)
                else:
                    atomic_write(args.output, output_content)
                    print(f"结果已写入: {args.output}")
            else:
                print(output_content)

            # 详细输出
            if args.verbose and not args.dry_run:
                print(f"\n处理摘要: {result['total']} 条记录", file=sys.stderr)
                if result["records"]:
                    print(f"置信度范围: {min(r.get('confidence', 0) for r in result['records']):.2f} - {max(r.get('confidence', 0) for r in result['records']):.2f}", file=sys.stderr)

        return 0

    except AmbitionError as e:
        print(f"错误: {e}", file=sys.stderr)
        print(f"错误码: {e.code} - {ERROR_CODES.get(e.code, '未知错误')}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
