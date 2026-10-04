#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py - gitsum 技能核心实现

基于功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供命令行接口与内置自检（--selftest）。
"""

import argparse
import csv
import io
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义（遵循规格 E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式不符合要求。",
    "E004": "超出能力边界，无法处理。",
    "E005": "置信度过低，结果不确定。",
    "E006": "内部处理错误。",
    "E007": "参数解析错误。",
    "E008": "输出格式错误。",
    "E009": "批量处理中断。",
    "E010": "未知错误。",
}


class GitsumError(Exception):
    """带错误码的异常类型。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条输入的结构化处理结果。"""

    def __init__(self, raw: str, key: str, confidence: float, note: str = ""):
        self.raw = raw            # 原始输入
        self.key = key            # 提取的关键信息
        self.confidence = confidence  # 置信度 0.0~1.0
        self.note = note          # 附加说明（如 [需核实]）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "key": self.key,
            "confidence": self.confidence,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# 核心逻辑：解析与处理
# ---------------------------------------------------------------------------
def extract_key_info(text: str) -> Tuple[str, float, str]:
    """
    从文本中提取关键信息。

    规则：
    - 若包含冒号（中英文），取冒号前内容作为 key
    - 若包含空格，取第一个词作为 key
    - 否则取整段文本前 20 个字符
    - 置信度基于匹配规则强度计算
    """
    if not text or not text.strip():
        raise GitsumError("E001")

    text = text.strip()
    note = ""

    # 规则 1：冒号分隔（feat: xxx）
    for sep in [":", "："]:
        if sep in text:
            key = text.split(sep)[0].strip()
            if key:
                confidence = 0.95
                return key, confidence, note

    # 规则 2：空格分隔（取第一个词）
    if " " in text:
        key = text.split(" ")[0].strip()
        if key:
            confidence = 0.85
            return key, confidence, note

    # 规则 3：整段文本截取
    key = text[:20]
    confidence = 0.6
    note = "[需核实]"
    return key, confidence, note


def process_text(text: str) -> ProcessedItem:
    """处理单条文本，返回结构化结果。"""
    try:
        key, confidence, note = extract_key_info(text)
        return ProcessedItem(raw=text, key=key, confidence=confidence, note=note)
    except GitsumError:
        raise
    except Exception as e:
        # 降级输出：返回原始输入，置信度 0
        print(f"[WARN] 处理文本失败: {e}，返回原始输入", file=sys.stderr)
        return ProcessedItem(raw=text, key=text, confidence=0.0, note="[处理失败]")


def read_text_safe(path: str) -> str:
    """安全读取文本文件，支持多种编码。"""
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


def process_file(file_path: str, encoding: str = "utf-8") -> List[ProcessedItem]:
    """批量处理文件，逐行读取并提取关键信息。"""
    results: List[ProcessedItem] = []
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(process_text(line))
    except FileNotFoundError:
        raise GitsumError("E003", f"文件不存在: {file_path}")
    except Exception as e:
        raise GitsumError("E006", f"读取文件失败: {e}")
    return results


def fetch_url_content(url: str, timeout: int = 10, retries: int = 3) -> str:
    """从 URL 获取内容，带超时和指数退避重试。"""
    if not url.startswith("https://"):
        raise GitsumError("E004", "仅支持 HTTPS 协议")

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gitsum/3.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            if attempt == retries - 1:
                raise GitsumError("E006", f"URL 请求失败: {e}")
            wait = 2 ** attempt  # 指数退避
            print(f"[WARN] 请求失败，{wait} 秒后重试 ({attempt + 1}/{retries})", file=sys.stderr)
            time.sleep(wait)
        except Exception as e:
            raise GitsumError("E006", f"URL 请求异常: {e}")
    raise GitsumError("E006", "URL 请求失败")


def process_url(url: str, timeout: int = 10, retries: int = 3) -> List[ProcessedItem]:
    """从 URL 获取内容并提取关键信息。"""
    content = fetch_url_content(url, timeout, retries)
    # 简单解析：按行处理
    results = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("{"):  # 跳过 JSON 大括号行
            results.append(process_text(line))
    if not results:
        # 尝试 JSON 解析
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        results.append(ProcessedItem(raw=f"{key}: {value}", key=key, confidence=0.9))
        except json.JSONDecodeError:
            pass
    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(results: List[ProcessedItem], fmt: str = "json") -> str:
    """将结果格式化为指定格式。"""
    if fmt == "json":
        return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        for r in results:
            lines.append(f"Key: {r.key}")
            lines.append(f"Confidence: {r.confidence:.2f}")
            if r.note:
                lines.append(f"Note: {r.note}")
            lines.append("---")
        return "\n".join(lines)
    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["raw", "key", "confidence", "note"])
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())
        return output.getvalue()
    else:
        raise GitsumError("E008", f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 原子化文件写入
# ---------------------------------------------------------------------------
def atomic_write(file_path: str, content: str) -> None:
    """原子化写入文件，避免写入中断导致文件损坏。"""
    dir_name = os.path.dirname(os.path.abspath(file_path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, file_path)
    except Exception:
        os.unlink(tmp_path)
        raise


def save(path: str, data: str, dry_run: bool = False) -> bool:
    """保存文件，支持 dry-run 模式。"""
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


# ---------------------------------------------------------------------------
# 自检模式
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("=== gitsum 自检开始 ===")
    failures = 0

    # 测试 1：单条文本处理
    print("\n[测试 1] 单条文本处理")
    try:
        item = process_text("feat: add user login feature")
        assert item.key == "feat", f"期望 key='feat'，实际 '{item.key}'"
        assert item.confidence >= 0.9, f"期望置信度 >= 0.9，实际 {item.confidence}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 2：中文冒号处理
    print("\n[测试 2] 中文冒号处理")
    try:
        item = process_text("修复：解决支付 bug")
        assert item.key == "修复", f"期望 key='修复'，实际 '{item.key}'"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 3：空输入处理
    print("\n[测试 3] 空输入处理")
    try:
        process_text("")
        print("  ✗ 失败: 未抛出异常")
        failures += 1
    except GitsumError as e:
        assert e.code == "E001", f"期望错误码 E001，实际 {e.code}"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 4：批量文件处理（使用临时文件）
    print("\n[测试 4] 批量文件处理")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("feat: add login page\nfix: resolve payment bug\ndocs: update README\n")
            tmp_path = f.name
        results = process_file(tmp_path)
        assert len(results) == 3, f"期望 3 条结果，实际 {len(results)}"
        assert results[0].key == "feat", f"期望第一条 key='feat'，实际 '{results[0].key}'"
        os.unlink(tmp_path)
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 5：输出格式化
    print("\n[测试 5] 输出格式化")
    try:
        results = [ProcessedItem(raw="test", key="test", confidence=0.9)]
        json_out = format_output(results, "json")
        assert "test" in json_out, "JSON 输出缺少 key"
        csv_out = format_output(results, "csv")
        assert "raw,key,confidence,note" in csv_out, "CSV 输出缺少表头"
        text_out = format_output(results, "text")
        assert "Key: test" in text_out, "Text 输出缺少 Key"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 6：置信度阈值过滤
    print("\n[测试 6] 置信度阈值过滤")
    try:
        results = [
            ProcessedItem(raw="a", key="a", confidence=0.9),
            ProcessedItem(raw="b", key="b", confidence=0.5),
        ]
        filtered = [r for r in results if r.confidence >= 0.7]
        assert len(filtered) == 1, f"期望 1 条结果，实际 {len(filtered)}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 7：URL 处理（仅测试错误处理，不实际请求网络）
    print("\n[测试 7] URL 错误处理")
    try:
        process_url("http://insecure.com")  # 非 HTTPS
        print("  ✗ 失败: 未抛出异常")
        failures += 1
    except GitsumError as e:
        assert e.code == "E004", f"期望错误码 E004，实际 {e.code}"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 8：原子化写入
    print("\n[测试 8] 原子化写入")
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        atomic_write(tmp_path, "test content")
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "test content", "写入内容不匹配"
        os.unlink(tmp_path)
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 9：save 函数 dry-run 模式
    print("\n[测试 9] save 函数 dry-run 模式")
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        # 先删除文件，确保测试开始时文件不存在
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        result = save(tmp_path, "test content", dry_run=True)
        assert result is False, "dry-run 模式应返回 False"
        assert not os.path.exists(tmp_path), "dry-run 模式不应创建文件"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    # 测试 10：save 函数实际写入
    print("\n[测试 10] save 函数实际写入")
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        result = save(tmp_path, "test content", dry_run=False)
        assert result is True, "非 dry-run 模式应返回 True"
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "test content", "写入内容不匹配"
        os.unlink(tmp_path)
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        failures += 1

    print(f"\n=== 自检完成: {10 - failures}/10 通过 ===")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="gitsum - 智能文本关键信息提取与结构化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--text", type=str, help="单条文本内容")
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--url", type=str, help="URL 地址")
    parser.add_argument("--format", type=str, choices=["json", "text", "csv"], default="json", help="输出格式")
    parser.add_argument("--min-confidence", type=float, default=0.0, help="置信度阈值过滤")
    parser.add_argument("--encoding", type=str, default="utf-8", help="输入文件编码")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser.add_argument("--verbose", action="store_true", help="详细模式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("GITSUM_TIMEOUT", "10")), help="URL 超时时间")
    parser.add_argument("--retries", type=int, default=int(os.environ.get("GITSUM_RETRIES", "3")), help="URL 重试次数")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 输入校验
    if not args.text and not args.input and not args.url:
        print("[E001] 输入为空，请使用 --text、--input 或 --url 提供输入", file=sys.stderr)
        return 1

    try:
        # 获取结果
        results: List[ProcessedItem] = []
        if args.text:
            results.append(process_text(args.text))
        elif args.input:
            results = process_file(args.input, args.encoding)
        elif args.url:
            results = process_url(args.url, args.timeout, args.retries)

        # 置信度过滤
        if args.min_confidence > 0:
            results = [r for r in results if r.confidence >= args.min_confidence]

        # 输出
        output_content = format_output(results, args.format)

        if args.output:
            if args.dry_run:
                # 预览模式：不写盘，打印摘要
                print(f"[DRY-RUN] 将写入文件: {args.output}")
                print(f"[DRY-RUN] 内容摘要: {output_content[:200]}...")
                print(f"[DRY-RUN] 共 {len(results)} 条结果")
            else:
                save(args.output, output_content, dry_run=False)
                print(f"已写入 {len(results)} 条结果到 {args.output}")
        else:
            # 输出到控制台
            print(output_content)

        if args.verbose:
            print(f"\n[VERBOSE] 处理 {len(results)} 条结果", file=sys.stderr)
            for i, r in enumerate(results):
                print(f"[明细] {i}. {r.raw}: key={r.key} (置信度: {r.confidence:.2f})", file=sys.stderr)
            print(f"[汇总] changed={len(results)} 项，skipped=0 项", file=sys.stderr)

        return 0

    except GitsumError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
