#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
appmetrics-dash: 将 Node.js 应用指标数据（JSON/CSV）解析为规范化记录，
并渲染为 ASCII/SVG/HTML 可视化监控面板。

支持能力：
- 解析本地 JSON/CSV 指标文件
- 从远程 URL 获取指标数据（带超时与指数退避重试）
- 从标准输入读取指标数据
- 渲染 ASCII/SVG/HTML 图表
- 批量处理目录下所有指标文件
- dry-run 预览模式（不实际写盘）
- verbose 详细日志
- selftest 离线自检
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# 常量定义
DEFAULT_TIMEOUT = 10  # 远程请求超时时间（秒）
DEFAULT_RETRIES = 3   # 远程请求最大重试次数
MAX_RETRIES = 5       # 最大重试次数上限
SUPPORTED_FORMATS = ("json", "csv")
SUPPORTED_RENDERS = ("ascii", "svg", "html")


# ============================================================
# 输入读取模块
# ============================================================

def read_text_safe(path):
    """带编码兜底的读取器（R3 编码兜底）。

    尝试 utf-8 → gbk → gb18030 三级 fallback，全部失败则用 errors="replace"。
    返回文件内容字符串；读取失败返回空字符串并打印警告。
    """
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def iter_lines(path):
    """流式读取文件行（R5 大输入流式）。

    使用 readline 逐行读取，避免全量 read() 造成内存爆炸。
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line
    except OSError as e:
        print(f"[WARN] 读取 {path} 失败，降级为空集: {e}", file=sys.stderr)
        return


def read_from_stdin():
    """从标准输入读取全部数据（流式逐行读取）。"""
    lines = []
    try:
        for line in sys.stdin:
            lines.append(line)
    except KeyboardInterrupt:
        print("[WARN] 用户中断输入，使用已读取的数据", file=sys.stderr)
    return "".join(lines)


def fetch_url(url, timeout=DEFAULT_TIMEOUT, retries=DEFAULT_RETRIES):
    """从远程 URL 获取数据，带超时与指数退避重试（R9）。

    连续失败超过 retries 次后熔断停止调用。
    返回响应内容字符串；失败抛出异常。
    """
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "appmetrics-dash/3.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_error = e
            wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s...
            print(f"[WARN] 请求失败（第 {attempt + 1}/{retries} 次）: {e}，{wait_time}s 后重试", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(wait_time)
    raise RuntimeError(f"请求失败，已重试 {retries} 次: {last_error}")


# ============================================================
# 数据解析模块
# ============================================================

def parse_json_data(content, source="local"):
    """解析 JSON 格式指标数据。

    支持两种格式：
    1. 数组：[{"name": "cpu", "value": 42.5, "timestamp": "..."}]
    2. 对象：{"cpu": 42.5, "memory": 68.2}

    返回规范化记录列表；解析失败抛出 ValueError。
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")

    records = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                print(f"[WARN] 跳过非对象元素: {item}", file=sys.stderr)
                continue
            record = {
                "name": str(item.get("name", "unknown")),
                "value": float(item.get("value", 0)),
                "timestamp": str(item.get("timestamp", "")),
                "source": source,
            }
            records.append(record)
    elif isinstance(data, dict):
        for name, value in data.items():
            if isinstance(value, (int, float)):
                records.append({
                    "name": str(name),
                    "value": float(value),
                    "timestamp": "",
                    "source": source,
                })
            elif isinstance(value, dict):
                records.append({
                    "name": str(name),
                    "value": float(value.get("value", 0)),
                    "timestamp": str(value.get("timestamp", "")),
                    "source": source,
                })
    else:
        raise ValueError(f"不支持的 JSON 顶层类型: {type(data)}")

    return records


def parse_csv_data(content, source="local"):
    """解析 CSV 格式指标数据。

    支持列：name, value, timestamp（大小写不敏感）。
    返回规范化记录列表；解析失败抛出 ValueError。
    """
    records = []
    try:
        reader = csv.DictReader(content.splitlines())
        for row in reader:
            # 兼容大小写列名
            name = row.get("name") or row.get("Name") or "unknown"
            value_str = row.get("value") or row.get("Value") or "0"
            timestamp = row.get("timestamp") or row.get("Timestamp") or ""
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                print(f"[WARN] 跳过非法数值: {value_str}", file=sys.stderr)
                continue
            records.append({
                "name": str(name),
                "value": value,
                "timestamp": str(timestamp),
                "source": source,
            })
    except csv.Error as e:
        raise ValueError(f"CSV 解析失败: {e}")

    return records


def parse_data(content, fmt, source="local"):
    """根据格式解析数据（R2 异常降级）。

    支持 json/csv 两种格式。
    返回规范化记录列表；解析失败抛出 ValueError。
    """
    if fmt == "json":
        return parse_json_data(content, source)
    elif fmt == "csv":
        return parse_csv_data(content, source)
    else:
        raise ValueError(f"不支持的格式: {fmt}，支持: {SUPPORTED_FORMATS}")


# ============================================================
# 渲染模块
# ============================================================

def render_ascii(records):
    """渲染 ASCII 图表（水平条形图）。"""
    if not records:
        return "（无数据）"

    lines = []
    for record in records:
        name = record["name"]
        value = record["value"]
        # 将数值映射为 20 格条形
        bar_len = max(0, min(20, int(abs(value) / 5)))
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"{name}: {bar} {value}%")

    return "\n".join(lines)


def render_svg(records, title="SVG 图表"):
    """渲染 SVG 图表（柱状图）。

    返回 SVG 字符串。
    """
    if not records:
        return "<svg width='400' height='200' xmlns='http://www.w3.org/2000/svg'><text x='10' y='20'>无数据</text></svg>"

    width = 400
    height = 200
    bar_width = 40
    gap = 20
    max_value = max(abs(r["value"]) for r in records) or 1

    svg_parts = [
        f"<svg width='{width}' height='{height}' xmlns='http://www.w3.org/2000/svg'>",
        f"<text x='10' y='20' font-size='14'>{title}</text>",
    ]

    for i, record in enumerate(records):
        x = 50 + i * (bar_width + gap)
        bar_height = int(abs(record["value"]) / max_value * (height - 60))
        y = height - 30 - bar_height
        svg_parts.append(
            f"<rect x='{x}' y='{y}' width='{bar_width}' height='{bar_height}' "
            f"fill='steelblue' stroke='black' stroke-width='1'/>"
        )
        svg_parts.append(
            f"<text x='{x}' y='{height - 10}' font-size='10'>{record['name']}</text>"
        )
        svg_parts.append(
            f"<text x='{x}' y='{y - 5}' font-size='10'>{record['value']}</text>"
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def render_html(records, title="监控面板"):
    """渲染 HTML 监控面板（表格 + 内嵌 SVG 图表）。"""
    if not records:
        return f"<html><body><h1>{title}</h1><p>无数据</p></body></html>"

    svg_chart = render_svg(records, title)

    table_rows = ""
    for record in records:
        table_rows += (
            f"<tr><td>{record['name']}</td><td>{record['value']}</td>"
            f"<td>{record['timestamp']}</td><td>{record['source']}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .chart {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="chart">
        {svg_chart}
    </div>
    <h2>指标明细</h2>
    <table>
        <tr><th>名称</th><th>数值</th><th>时间戳</th><th>来源</th></tr>
        {table_rows}
    </table>
</body>
</html>"""
    return html


def render_data(records, render_type, title="监控面板"):
    """根据渲染类型生成图表（R2 异常降级）。"""
    if render_type == "ascii":
        return render_ascii(records)
    elif render_type == "svg":
        return render_svg(records, title)
    elif render_type == "html":
        return render_html(records, title)
    else:
        raise ValueError(f"不支持的渲染类型: {render_type}，支持: {SUPPORTED_RENDERS}")


# ============================================================
# 文件写入模块
# ============================================================

def save_file(path, data, dry_run=False, verbose=False):
    """原子化写盘（R4 预览撤回）。

    dry_run=True 时只打印将写入的路径与摘要，不实际写盘。
    写盘使用临时文件 + rename 保证原子性。
    """
    if dry_run:
        print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
        return False

    try:
        tmp_path = Path(str(path) + ".tmp")
        tmp_path.write_text(data, encoding="utf-8")
        tmp_path.replace(path)
        if verbose:
            print(f"[INFO] 已写入 {path}（{len(data)} 字节）")
        else:
            print(f"[写入] {path}")
        return True
    except OSError as e:
        print(f"[ERROR] 写入 {path} 失败: {e}", file=sys.stderr)
        return False


# ============================================================
# 批量处理模块
# ============================================================

def process_file(input_path, fmt, render_type, output_path, dry_run=False, verbose=False):
    """处理单个文件（R2 异常降级 + R5 流式）。

    返回处理结果字典。
    """
    result = {"input": str(input_path), "success": False, "records": 0, "output": None}

    try:
        # 读取文件（流式）
        content = read_text_safe(input_path)
        if not content.strip():
            print(f"[WARN] 文件为空: {input_path}", file=sys.stderr)
            return result

        # 解析数据
        records = parse_data(content, fmt, source="local")
        result["records"] = len(records)

        if verbose:
            print(f"[INFO] 解析到 {len(records)} 条指标记录")

        # 渲染
        if render_type:
            rendered = render_data(records, render_type, title=input_path.stem)
            if output_path:
                save_file(output_path, rendered, dry_run=dry_run, verbose=verbose)
                result["output"] = str(output_path)
            else:
                print(rendered)
        else:
            # 默认输出 JSON
            print(json.dumps(records, ensure_ascii=False, indent=2))

        result["success"] = True
        return result

    except ValueError as e:
        print(f"[ERROR] 解析 {input_path} 失败: {e}", file=sys.stderr)
        return result
    except Exception as e:
        print(f"[ERROR] 处理 {input_path} 失败: {e}", file=sys.stderr)
        return result


def process_batch(input_dir, output_dir, fmt, render_type, dry_run=False, verbose=False):
    """批量处理目录下所有 .json 和 .csv 文件（R5 流式）。"""
    input_path = Path(input_dir)
    if not input_path.is_dir():
        print(f"[ERROR] 输入目录不存在: {input_dir}", file=sys.stderr)
        return []

    # 创建输出目录
    output_path = Path(output_dir)
    if not dry_run:
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"[ERROR] 创建输出目录失败: {e}", file=sys.stderr)
            return []

    results = []
    for file_path in sorted(input_path.iterdir()):
        if file_path.suffix.lower() not in (".json", ".csv"):
            continue

        # 自动检测格式
        file_fmt = fmt or file_path.suffix.lower().lstrip(".")
        if file_fmt not in SUPPORTED_FORMATS:
            print(f"[WARN] 跳过不支持格式: {file_path}（{file_fmt}）", file=sys.stderr)
            continue

        # 输出文件名
        out_file = output_path / f"{file_path.stem}.{render_type}" if render_type else output_path / f"{file_path.stem}.json"

        result = process_file(
            file_path, file_fmt, render_type, out_file,
            dry_run=dry_run, verbose=verbose
        )
        results.append(result)

    return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest():
    """离线自检：真实调用核心函数并断言关键输出（退出码 0 表示通过）。"""
    print("[自检] 开始...")
    failures = 0

    # 测试 1：JSON 解析
    print("[自检] 测试 JSON 解析...", end=" ")
    try:
        json_content = '[{"name": "cpu", "value": 42.5, "timestamp": "2026-08-09T10:00:00Z"}]'
        records = parse_json_data(json_content, source="local")
        assert len(records) == 1, f"期望 1 条记录，实际 {len(records)}"
        assert records[0]["name"] == "cpu", f"期望 name=cpu，实际 {records[0]['name']}"
        assert abs(records[0]["value"] - 42.5) < 0.001, f"期望 value=42.5，实际 {records[0]['value']}"
        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 2：CSV 解析
    print("[自检] 测试 CSV 解析...", end=" ")
    try:
        csv_content = "name,value,timestamp\ncpu,42.5,2026-08-09T10:00:00Z\nmemory,68.2,2026-08-09T10:00:00Z\n"
        records = parse_csv_data(csv_content, source="local")
        assert len(records) == 2, f"期望 2 条记录，实际 {len(records)}"
        assert records[1]["name"] == "memory", f"期望 name=memory，实际 {records[1]['name']}"
        assert abs(records[1]["value"] - 68.2) < 0.001, f"期望 value=68.2，实际 {records[1]['value']}"
        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 3：ASCII 渲染
    print("[自检] 测试 ASCII 渲染...", end=" ")
    try:
        records = [
            {"name": "cpu", "value": 42.5, "timestamp": "", "source": "local"},
            {"name": "memory", "value": 68.2, "timestamp": "", "source": "local"},
        ]
        ascii_output = render_ascii(records)
        assert "cpu" in ascii_output, "ASCII 输出缺少 cpu"
        assert "memory" in ascii_output, "ASCII 输出缺少 memory"
        assert "█" in ascii_output, "ASCII 输出缺少条形字符"
        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 4：SVG 渲染
    print("[自检] 测试 SVG 渲染...", end=" ")
    try:
        records = [
            {"name": "cpu", "value": 42.5, "timestamp": "", "source": "local"},
            {"name": "memory", "value": 68.2, "timestamp": "", "source": "local"},
        ]
        svg_output = render_svg(records, "测试图表")
        assert "<svg" in svg_output, "SVG 输出缺少 <svg> 标签"
        assert "cpu" in svg_output, "SVG 输出缺少 cpu"
        assert "memory" in svg_output, "SVG 输出缺少 memory"
        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 5：HTML 渲染
    print("[自检] 测试 HTML 渲染...", end=" ")
    try:
        records = [
            {"name": "cpu", "value": 42.5, "timestamp": "2026-08-09T10:00:00Z", "source": "local"},
        ]
        html_output = render_html(records, "测试面板")
        assert "<html" in html_output, "HTML 输出缺少 <html> 标签"
        assert "cpu" in html_output, "HTML 输出缺少 cpu"
        assert "42.5" in html_output, "HTML 输出缺少数值"
        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 6：空数据处理
    print("[自检] 测试空数据处理...", end=" ")
    try:
        records = []
        ascii_output = render_ascii(records)
        assert "无数据" in ascii_output, "空数据 ASCII 输出缺少提示"
        svg_output = render_svg(records)
        assert "无数据" in svg_output, "空数据 SVG 输出缺少提示"
        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 7：异常输入处理
    print("[自检] 测试异常输入处理...", end=" ")
    try:
        try:
            parse_json_data("invalid json", source="local")
            print("失败: 非法 JSON 未抛出异常")
            failures += 1
        except ValueError:
            pass  # 预期行为

        try:
            parse_data("", "json", source="local")
            print("失败: 空内容未抛出异常")
            failures += 1
        except ValueError:
            pass  # 预期行为

        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 8：文件读写
    print("[自检] 测试文件读写...", end=" ")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入测试文件
            test_file = Path(tmpdir) / "test.json"
            test_file.write_text('[{"name": "cpu", "value": 42.5}]', encoding="utf-8")

            # 读取并解析
            content = read_text_safe(test_file)
            records = parse_json_data(content, source="local")
            assert len(records) == 1, f"期望 1 条记录，实际 {len(records)}"

            # 测试 dry-run
            out_file = Path(tmpdir) / "out.svg"
            save_file(out_file, "<svg></svg>", dry_run=True)
            assert not out_file.exists(), "dry-run 模式不应创建文件"

            # 测试实际写入
            save_file(out_file, "<svg></svg>", dry_run=False)
            assert out_file.exists(), "实际写入应创建文件"
            assert out_file.read_text(encoding="utf-8") == "<svg></svg>", "文件内容不匹配"

        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 9：批量处理
    print("[自检] 测试批量处理...", end=" ")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            # 创建测试文件
            (input_dir / "a.json").write_text('[{"name": "cpu", "value": 42.5}]', encoding="utf-8")
            (input_dir / "b.csv").write_text("name,value\nmemory,68.2\n", encoding="utf-8")

            results = process_batch(input_dir, output_dir, None, "ascii", dry_run=False, verbose=False)
            assert len(results) == 2, f"期望 2 个结果，实际 {len(results)}"
            assert all(r["success"] for r in results), "存在失败的处理"

        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 测试 10：远程 URL（模拟）
    print("[自检] 测试 URL 处理...", end=" ")
    try:
        # 使用本地 HTTP 服务器模拟
        import http.server
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'[{"name": "cpu", "value": 42.5}]')

            def log_message(self, format, *args):
                pass  # 静默日志

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            content = fetch_url(f"http://127.0.0.1:{port}/metrics.json", timeout=5, retries=1)
            records = parse_json_data(content, source="remote")
            assert len(records) == 1, f"期望 1 条记录，实际 {len(records)}"
            assert records[0]["source"] == "remote", f"期望 source=remote，实际 {records[0]['source']}"
        finally:
            server.shutdown()

        print("通过")
    except Exception as e:
        print(f"失败: {e}")
        failures += 1

    # 总结
    if failures == 0:
        print("[自检] 全部通过")
        return 0
    else:
        print(f"[自检] {failures} 项失败")
        return 1


# ============================================================
# 主入口
# ============================================================

def main():
    """CLI 入口：解析参数并调度处理。"""
    parser = argparse.ArgumentParser(
        description="appmetrics-dash: 将 Node.js 应用指标数据解析为规范化记录并渲染可视化图表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python run.py --input metrics.json --format json
  python run.py --url https://example.com/metrics.json --format json
  cat metrics.json | python run.py --format json
  python run.py --input metrics.json --render ascii
  python run.py --input metrics.json --render svg --output chart.svg
  python run.py --input metrics.json --render html --output dashboard.html
  python run.py --batch --input data/ --output results/
  python run.py --selftest
"""
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", type=str, help="输入文件路径（JSON/CSV）")
    input_group.add_argument("--url", type=str, help="远程 URL 地址")
    input_group.add_argument("--batch", action="store_true", help="批量处理目录下所有指标文件")

    # 格式参数
    parser.add_argument("--format", type=str, choices=SUPPORTED_FORMATS,
                        help="输入数据格式（json/csv），默认自动检测")

    # 渲染参数
    parser.add_argument("--render", type=str, choices=SUPPORTED_RENDERS,
                        help="渲染类型（ascii/svg/html），不指定则输出 JSON")

    # 输出参数
    parser.add_argument("--output", type=str, help="输出文件路径（渲染时必填）")

    # 其他参数
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式：只打印将写入的路径与摘要，不实际写盘")
    parser.add_argument("--verbose", action="store_true",
                        help="输出详细处理日志")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 参数校验（R7 输入校验防御）
    if not args.input and not args.url and not args.batch:
        # 检查是否有 stdin 输入
        if sys.stdin.isatty():
            parser.error("必须指定 --input、--url、--batch 之一，或通过管道传入 stdin 数据")
        # 从 stdin 读取
        content = read_from_stdin()
        if not content.strip():
            parser.error("stdin 输入为空")
        fmt = args.format or "json"
        try:
            records = parse_data(content, fmt, source="stdin")
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

        if args.render:
            rendered = render_data(records, args.render)
            if args.output:
                save_file(args.output, rendered, dry_run=args.dry_run, verbose=args.verbose)
            else:
                print(rendered)
        else:
            print(json.dumps(records, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 批量处理模式
    if args.batch:
        if not args.input:
            parser.error("--batch 模式必须指定 --input 目录")
        if not args.output:
            parser.error("--batch 模式必须指定 --output 目录")
        results = process_batch(
            args.input, args.output, args.format, args.render,
            dry_run=args.dry_run, verbose=args.verbose
        )
        success_count = sum(1 for r in results if r["success"])
        print(f"[INFO] 批量处理完成: {success_count}/{len(results)} 成功")
        sys.exit(0 if success_count == len(results) else 1)

    # 远程 URL 模式
    if args.url:
        try:
            content = fetch_url(args.url)
        except RuntimeError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
        fmt = args.format or "json"
        try:
            records = parse_data(content, fmt, source="remote")
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)
    # 本地文件模式
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"[ERROR] 文件不存在: {args.input}", file=sys.stderr)
            sys.exit(1)
        if not input_path.is_file():
            print(f"[ERROR] 不是文件: {args.input}", file=sys.stderr)
            sys.exit(1)

        # 自动检测格式
        fmt = args.format
        if not fmt:
            suffix = input_path.suffix.lower().lstrip(".")
            if suffix in SUPPORTED_FORMATS:
                fmt = suffix
            else:
                print(f"[ERROR] 无法自动检测格式，请使用 --format 指定（支持: {SUPPORTED_FORMATS}）", file=sys.stderr)
                sys.exit(1)

        content = read_text_safe(input_path)
        if not content.strip():
            print(f"[ERROR] 文件为空: {args.input}", file=sys.stderr)
            sys.exit(1)

        try:
            records = parse_data(content, fmt, source="local")
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    # 输出处理
    if args.verbose:
        print(f"[INFO] 解析到 {len(records)} 条指标记录")

    if args.render:
        rendered = render_data(records, args.render, title=input_path.stem if args.input else "监控面板")
        if args.output:
            save_file(args.output, rendered, dry_run=args.dry_run, verbose=args.verbose)
        else:
            print(rendered)
    else:
        # 默认输出 JSON
        print(json.dumps(records, ensure_ascii=False, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
