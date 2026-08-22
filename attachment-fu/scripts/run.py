#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
attachment-fu — 将文件、数据或 URL 转换为结构化附件记录。

本脚本实现 SKILL.md 声明的全部能力：
- 本地文件转结构化记录（--input）
- 多文件批量处理（多个 --input）
- URL 文件信息提取（--url）
- 输出格式选择（--format json|csv）
- 置信度标注（confidence 字段）
- 预览模式（--dry-run）
- 详细日志（--verbose）
- 自检测试（--selftest）

零第三方依赖，仅使用标准库。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import mimetypes
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 30  # URL 请求默认超时（秒）
MAX_RETRIES = 3  # URL 请求最大重试次数
RETRY_BACKOFF_BASE = 2.0  # 指数退避基数（秒）
OUTPUT_ENCODING = "utf-8"  # 输出文件编码

# 错误码定义
ERR_OK = 0
ERR_INPUT_INVALID = 1
ERR_FILE_NOT_FOUND = 2
ERR_URL_FAILED = 3
ERR_OUTPUT_WRITE_FAILED = 4
ERR_INTERNAL = 5

# 已知 MIME 类型映射（补充 mimetypes 库的不足）
EXTRA_MIME_TYPES = {
    ".md": "text/markdown",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".toml": "application/toml",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".log": "text/plain",
    ".env": "text/plain",
    ".lock": "application/json",
    ".ipynb": "application/json",
    ".parquet": "application/parquet",
    ".avro": "application/avro",
    ".orc": "application/orc",
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def safe_filename(filename: str) -> str:
    """清理文件名，移除不安全字符。"""
    # 移除路径分隔符和特殊字符
    cleaned = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", filename)
    # 移除首尾空白和点
    cleaned = cleaned.strip().strip(".")
    return cleaned or "unnamed"


def get_mime_type(filename: str) -> str:
    """根据文件扩展名推断 MIME 类型。"""
    ext = Path(filename).suffix.lower()
    if ext in EXTRA_MIME_TYPES:
        return EXTRA_MIME_TYPES[ext]
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def get_extension(filename: str) -> str:
    """获取文件扩展名（含点）。"""
    return Path(filename).suffix.lower()


def format_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读的字符串。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def read_file_metadata(path: str) -> Dict[str, Any]:
    """
    读取本地文件的元数据。

    参数:
        path: 文件路径

    返回:
        包含文件元数据的字典

    异常:
        FileNotFoundError: 文件不存在
        PermissionError: 无读取权限
        OSError: 其他文件系统错误
    """
    file_path = Path(path)

    # 检查文件是否存在
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    # 检查是否为文件（而非目录）
    if not file_path.is_file():
        raise OSError(f"路径不是文件: {path}")

    # 获取文件统计信息
    stat = file_path.stat()

    # 获取修改时间（UTC）
    modified_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    # 构建元数据记录
    record = {
        "source": "file",
        "path": str(file_path),
        "filename": file_path.name,
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size),
        "mime_type": get_mime_type(file_path.name),
        "extension": get_extension(file_path.name),
        "modified_time": modified_time,
        "confidence": 0.95,  # 本地文件元数据置信度高
        "warnings": [],
    }

    return record


def fetch_url_with_retry(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[bytes, Dict[str, str]]:
    """
    带重试机制的 URL 请求。

    参数:
        url: 目标 URL
        timeout: 超时时间（秒）

    返回:
        (响应内容, 响应头字典)

    异常:
        urllib.error.URLError: URL 请求失败
        ValueError: URL 格式无效
    """
    # 校验 URL 格式
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"无效的 URL 格式: {url}")

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "attachment-fu/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read()
                headers = dict(response.headers)
                return content, headers
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                # 指数退避
                wait_time = RETRY_BACKOFF_BASE ** attempt
                time.sleep(wait_time)

    # 所有重试都失败
    raise last_error if last_error else RuntimeError(f"URL 请求失败: {url}")


def parse_url_metadata(url: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    从 URL 获取文件元数据。

    参数:
        url: 目标 URL
        timeout: 超时时间（秒）

    返回:
        包含文件元数据的字典

    异常:
        ValueError: URL 格式无效
        urllib.error.URLError: URL 请求失败
    """
    # 从 URL 中提取文件名
    url_path = urllib.request.urlparse(url).path
    filename = Path(url_path).name or "unnamed"

    # 获取 URL 内容（用于推断大小）
    content, headers = fetch_url_with_retry(url, timeout)

    # 从 Content-Disposition 头中提取文件名（如果有）
    content_disposition = headers.get("Content-Disposition", "")
    if "filename=" in content_disposition:
        match = re.search(r'filename="?([^"]+)"?', content_disposition)
        if match:
            filename = match.group(1)

    # 从 Content-Type 头中获取 MIME 类型
    content_type = headers.get("Content-Type", "")
    mime_type = content_type.split(";")[0].strip() if content_type else get_mime_type(filename)

    # 获取内容长度
    content_length = headers.get("Content-Length")
    size_bytes = int(content_length) if content_length and content_length.isdigit() else len(content)

    # 构建元数据记录
    warnings = []
    if not content_length:
        warnings.append("URL 内容长度未知，大小字段为推断值")

    record = {
        "source": "url",
        "url": url,
        "filename": safe_filename(filename),
        "size_bytes": size_bytes,
        "size_human": format_size(size_bytes),
        "mime_type": mime_type or "application/octet-stream",
        "extension": get_extension(filename),
        "modified_time": utc_now_iso(),
        "confidence": 0.8,  # URL 来源置信度略低
        "warnings": warnings,
    }

    return record


def parse_json_data(data: str) -> Dict[str, Any]:
    """
    解析 JSON 字符串并提取附件元数据。

    参数:
        data: JSON 字符串

    返回:
        包含附件元数据的字典

    异常:
        json.JSONDecodeError: JSON 解析失败
    """
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")

    if not isinstance(parsed, dict):
        raise ValueError("JSON 数据必须是对象类型")

    # 提取元数据字段
    filename = str(parsed.get("filename", parsed.get("name", "unnamed")))
    size_bytes = parsed.get("size_bytes", parsed.get("size", 0))
    mime_type = parsed.get("mime_type", parsed.get("mime", get_mime_type(filename)))
    modified_time = parsed.get("modified_time", parsed.get("timestamp", utc_now_iso()))

    # 确保 size_bytes 是整数
    try:
        size_bytes = int(size_bytes)
    except (TypeError, ValueError):
        size_bytes = 0

    record = {
        "source": "json",
        "filename": safe_filename(filename),
        "size_bytes": size_bytes,
        "size_human": format_size(size_bytes),
        "mime_type": mime_type or "application/octet-stream",
        "extension": get_extension(filename),
        "modified_time": modified_time,
        "confidence": 0.7,  # JSON 数据置信度中等
        "warnings": [],
    }

    return record


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------


def format_json_output(records: List[Dict[str, Any]]) -> str:
    """将记录列表格式化为 JSON 字符串。"""
    return json.dumps(records, ensure_ascii=False, indent=2)


def format_csv_output(records: List[Dict[str, Any]]) -> str:
    """将记录列表格式化为 CSV 字符串。"""
    if not records:
        return ""

    # 确定 CSV 字段（取所有记录字段的并集）
    fieldnames: List[str] = []
    for record in records:
        for key in record.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    # 生成 CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        # 将 warnings 列表转为字符串
        record_copy = dict(record)
        if isinstance(record_copy.get("warnings"), list):
            record_copy["warnings"] = json.dumps(record_copy["warnings"], ensure_ascii=False)
        writer.writerow(record_copy)

    return output.getvalue()


def write_output_atomic(content: str, output_path: str, dry_run: bool = False) -> bool:
    """
    原子化写入输出文件。

    参数:
        content: 要写入的内容
        output_path: 输出文件路径
        dry_run: 是否为预览模式（不实际写盘）

    返回:
        是否成功写入
    """
    if not dry_run:
        try:
            # 确保输出目录存在
            output_dir = Path(output_path).parent
            if output_dir and not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)

            # 写入临时文件，然后原子替换
            fd, temp_path = tempfile.mkstemp(dir=str(output_dir) if str(output_dir) else ".", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding=OUTPUT_ENCODING) as f:
                    f.write(content)
                # 原子替换
                os.replace(temp_path, output_path)
            except Exception:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

            return True
        except OSError as e:
            print(f"错误: 写入文件失败 {output_path}: {e}", file=sys.stderr)
            return False
    print(f"[DRY-RUN] 将写入文件: {output_path}")
    print(f"[DRY-RUN] 内容摘要: {content[:200]}...")
    return True


# ---------------------------------------------------------------------------
# 主处理逻辑
# ---------------------------------------------------------------------------


def process_inputs(
    input_paths: List[str],
    urls: List[str],
    json_data: Optional[str],
    output_format: str,
    output_path: Optional[str],
    dry_run: bool,
    verbose: bool,
    timeout: int,
) -> int:
    """
    处理所有输入并生成输出。

    返回:
        退出码
    """
    records: List[Dict[str, Any]] = []
    has_error = False
    changed_items = []

    # 处理本地文件
    for path in input_paths:
        try:
            if verbose:
                print(f"处理文件: {path}")
            record = read_file_metadata(path)
            records.append(record)
            changed_items.append({
                "name": record["filename"],
                "before": "未处理",
                "after": f"{record['size_human']} ({record['mime_type']})"
            })
            if verbose:
                print(f"  成功: {record['filename']} ({record['size_human']})")
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"错误: {e}", file=sys.stderr)
            has_error = True

    # 处理 URL
    for url in urls:
        try:
            if verbose:
                print(f"处理 URL: {url}")
            record = parse_url_metadata(url, timeout)
            records.append(record)
            changed_items.append({
                "name": record["filename"],
                "before": "未处理",
                "after": f"{record['size_human']} ({record['mime_type']})"
            })
            if verbose:
                print(f"  成功: {record['filename']} ({record['size_human']})")
        except (ValueError, urllib.error.URLError, TimeoutError) as e:
            print(f"错误: URL 处理失败 {url}: {e}", file=sys.stderr)
            has_error = True

    # 处理 JSON 数据
    if json_data:
        try:
            if verbose:
                print("处理 JSON 数据")
            record = parse_json_data(json_data)
            records.append(record)
            changed_items.append({
                "name": record["filename"],
                "before": "未处理",
                "after": f"{record['size_human']} ({record['mime_type']})"
            })
            if verbose:
                print(f"  成功: {record['filename']} ({record['size_human']})")
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            has_error = True

    # 如果没有成功处理任何记录，返回错误
    if not records:
        print("错误: 没有成功处理任何输入", file=sys.stderr)
        return ERR_INPUT_INVALID

    # 格式化输出
    if output_format == "json":
        content = format_json_output(records)
    else:
        content = format_csv_output(records)

    # 输出到文件或 stdout
    if output_path:
        success = write_output_atomic(content, output_path, dry_run)
        if not success:
            return ERR_OUTPUT_WRITE_FAILED
        if not dry_run:
            print(f"已写入 {len(records)} 条记录到 {output_path}")
    else:
        print(content)

    # 如果有错误但部分成功，返回警告状态
    if has_error:
        print("警告: 部分输入处理失败，请查看上方错误信息", file=sys.stderr)

    # 详细日志：逐条打印修改明细
    if verbose:
        for idx, item in enumerate(changed_items, 1):
            print(f"[明细] {idx}. {item['name']}: {item['before']} -> {item['after']}")
        print(f"[汇总] changed={len(changed_items)} 项，skipped={len(input_paths) + len(urls) + (1 if json_data else 0) - len(changed_items)} 项")

    return ERR_OK


# ---------------------------------------------------------------------------
# 自检测试
# ---------------------------------------------------------------------------


def run_selftest() -> int:
    """
    运行自检测试，验证核心功能。

    返回:
        退出码（0 表示全部通过）
    """
    print("=== attachment-fu 自检测试 ===")
    failures = 0

    # 测试 1: 本地文件元数据提取
    print("\n[测试 1] 本地文件元数据提取")
    try:
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Hello, attachment-fu test file!")
            temp_path = f.name

        try:
            record = read_file_metadata(temp_path)
            assert record["source"] == "file", f"source 应为 file，实际为 {record['source']}"
            assert record["filename"].endswith(".txt"), f"filename 应以 .txt 结尾，实际为 {record['filename']}"
            assert record["size_bytes"] > 0, f"size_bytes 应大于 0，实际为 {record['size_bytes']}"
            assert record["mime_type"] == "text/plain", f"mime_type 应为 text/plain，实际为 {record['mime_type']}"
            assert record["confidence"] > 0.5, f"confidence 应大于 0.5，实际为 {record['confidence']}"
            print("  ✓ 通过")
        finally:
            # 清理临时文件
            os.unlink(temp_path)
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 2: URL 元数据提取（使用本地 HTTP 服务器）
    print("\n[测试 2] URL 元数据提取")
    try:
        import http.server
        import threading

        # 创建临时文件作为 HTTP 响应内容
        test_content = b"attachment-fu URL test content"
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(test_content)
            temp_path = f.name

        # 启动本地 HTTP 服务器，使用自定义 handler 从临时目录提供文件
        temp_dir = os.path.dirname(temp_path)
        handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=temp_dir, **kwargs)
        httpd = http.server.HTTPServer(("127.0.0.1", 0), handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        try:
            url = f"http://127.0.0.1:{port}/{Path(temp_path).name}"
            record = parse_url_metadata(url, timeout=5)
            assert record["source"] == "url", f"source 应为 url，实际为 {record['source']}"
            assert record["size_bytes"] == len(test_content), f"size_bytes 应为 {len(test_content)}，实际为 {record['size_bytes']}"
            assert record["confidence"] > 0.5, f"confidence 应大于 0.5，实际为 {record['confidence']}"
            print("  ✓ 通过")
        finally:
            httpd.shutdown()
            os.unlink(temp_path)
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 3: JSON 数据解析
    print("\n[测试 3] JSON 数据解析")
    try:
        json_str = '{"filename": "test.json", "size_bytes": 1234, "mime_type": "application/json"}'
        record = parse_json_data(json_str)
        assert record["source"] == "json", f"source 应为 json，实际为 {record['source']}"
        assert record["filename"] == "test.json", f"filename 应为 test.json，实际为 {record['filename']}"
        assert record["size_bytes"] == 1234, f"size_bytes 应为 1234，实际为 {record['size_bytes']}"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 4: 输出格式化
    print("\n[测试 4] 输出格式化")
    try:
        records = [
            {
                "source": "file",
                "path": "/tmp/test.txt",
                "filename": "test.txt",
                "size_bytes": 100,
                "size_human": "100 B",
                "mime_type": "text/plain",
                "extension": ".txt",
                "modified_time": "2026-08-09T00:00:00+00:00",
                "confidence": 0.95,
                "warnings": [],
            }
        ]

        # JSON 输出
        json_output = format_json_output(records)
        parsed = json.loads(json_output)
        assert len(parsed) == 1, f"JSON 输出应有 1 条记录，实际为 {len(parsed)}"
        assert parsed[0]["filename"] == "test.txt", "JSON 输出 filename 不正确"

        # CSV 输出
        csv_output = format_csv_output(records)
        assert "filename" in csv_output, "CSV 输出应包含 filename 字段"
        assert "test.txt" in csv_output, "CSV 输出应包含 test.txt"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 5: 原子写入
    print("\n[测试 5] 原子写入")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "output.json")

            # 正常写入
            success = write_output_atomic('{"test": true}', output_path, dry_run=False)
            assert success, "原子写入应成功"
            assert os.path.exists(output_path), "输出文件应存在"

            # 读取验证
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            assert content == '{"test": true}', "写入内容应正确"

            # Dry-run 模式
            success = write_output_atomic('{"test": false}', output_path, dry_run=True)
            assert success, "dry-run 应成功"
            # 验证文件未被修改
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            assert content == '{"test": true}', "dry-run 不应修改文件"

            print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 6: 边界情况 - 空输入
    print("\n[测试 6] 边界情况 - 空输入")
    try:
        records = []
        json_output = format_json_output(records)
        assert json_output == "[]", f"空记录 JSON 输出应为 []，实际为 {json_output}"
        csv_output = format_csv_output(records)
        assert csv_output == "", f"空记录 CSV 输出应为空字符串，实际为 {csv_output}"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 7: 边界情况 - 中文文件名
    print("\n[测试 7] 边界情况 - 中文文件名")
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", prefix="测试文件_", delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            record = read_file_metadata(temp_path)
            assert "测试文件" in record["filename"], f"文件名应包含中文，实际为 {record['filename']}"
            print("  ✓ 通过")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 8: 边界情况 - 不存在的文件
    print("\n[测试 8] 边界情况 - 不存在的文件")
    try:
        try:
            read_file_metadata("/nonexistent/path/to/file.txt")
            print("  ✗ 失败: 应抛出 FileNotFoundError")
            failures += 1
        except FileNotFoundError:
            print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 9: 边界情况 - 无效 URL
    print("\n[测试 9] 边界情况 - 无效 URL")
    try:
        try:
            parse_url_metadata("not-a-valid-url")
            print("  ✗ 失败: 应抛出 ValueError")
            failures += 1
        except ValueError:
            print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 测试 10: 边界情况 - 无效 JSON
    print("\n[测试 10] 边界情况 - 无效 JSON")
    try:
        try:
            parse_json_data("{invalid json")
            print("  ✗ 失败: 应抛出 ValueError")
            failures += 1
        except ValueError:
            print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        failures += 1

    # 汇总
    print(f"\n=== 自检测试完成: {10 - failures}/10 通过 ===")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="attachment-fu",
        description="将文件、数据或 URL 转为结构化附件记录，提取元数据并输出 JSON/CSV。",
        epilog="示例: python run.py --input ./report.pdf --format json",
    )

    # 输入参数
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        default=[],
        help="本地文件路径（可多次指定）",
    )
    parser.add_argument(
        "--url",
        action="append",
        dest="urls",
        default=[],
        help="URL 地址（可多次指定）",
    )
    parser.add_argument(
        "--json",
        dest="json_data",
        default=None,
        help="JSON 字符串（包含附件元数据）",
    )

    # 输出参数
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "csv"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=None,
        help="输出文件路径（默认输出到 stdout）",
    )

    # 行为参数
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="预览模式，不实际写盘",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="输出详细日志",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"URL 请求超时时间（秒，默认: {DEFAULT_TIMEOUT}）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        dest="selftest",
        default=False,
        help="运行自检测试",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    args = parse_args(argv)

    # 自检测试模式
    if args.selftest:
        return run_selftest()

    # 校验输入
    if not args.inputs and not args.urls and not args.json_data:
        print("错误: 至少需要提供一个输入（--input、--url 或 --json）", file=sys.stderr)
        print("使用 --help 查看帮助", file=sys.stderr)
        return ERR_INPUT_INVALID

    # 校验 timeout
    if args.timeout <= 0:
        print("错误: --timeout 必须大于 0", file=sys.stderr)
        return ERR_INPUT_INVALID

    # 处理输入
    return process_inputs(
        input_paths=args.inputs,
        urls=args.urls,
        json_data=args.json_data,
        output_format=args.output_format,
        output_path=args.output_path,
        dry_run=args.dry_run,
        verbose=args.verbose,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
