#!/usr/bin/env python3
"""批量文本处理工具，支持 JSON/Text/Markdown 格式输出，含 dry-run 模式。"""

import argparse
import json
import sys
from pathlib import Path


def process_items(items, output_format="text"):
    """处理文本项列表，返回格式化后的字符串。"""
    if output_format == "json":
        return json.dumps(items, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        lines = ["| 序号 | 内容 |", "|------|------|"]
        for i, item in enumerate(items, 1):
            lines.append(f"| {i} | {item} |")
        return "\n".join(lines)
    else:  # text
        return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))


def write_file(path, content, dry_run=False):
    """写入文件，支持 dry-run 模式。"""
    if dry_run:
        print(f"[DRY-RUN] 将写入文件: {path}")
        print(f"[DRY-RUN] 内容长度: {len(content)} 字符")
        return False
    Path(path).write_text(content, encoding="utf-8")
    return True


def run_selftest():
    """运行自检，验证核心功能。"""
    print("[RUN] 批量处理 3 项")
    items = ["alpha", "beta", "gamma"]

    # 测试格式化输出
    print("\n测试输出格式化...")
    json_out = process_items(items, "json")
    assert json.loads(json_out) == items, "JSON 输出内容不匹配"
    print("  [PASS] json 格式输出正常")

    text_out = process_items(items, "text")
    assert "alpha" in text_out and "gamma" in text_out, "Text 输出缺少内容"
    print("  [PASS] text 格式输出正常")

    md_out = process_items(items, "markdown")
    assert "| 序号 | 内容 |" in md_out, "Markdown 表头缺失"
    assert "alpha" in md_out, "Markdown 输出缺少内容"
    print("  [PASS] markdown 格式输出正常")

    # 测试文件读写
    print("\n测试文件读写...")
    import tempfile
    test_file = Path(tempfile.gettempdir()) / "selftest_output.txt"
    test_content = "测试内容"
    write_file(str(test_file), test_content)
    assert test_file.exists(), "文件未创建"
    print("  [PASS] 文件写入成功")
    read_back = test_file.read_text(encoding="utf-8")
    assert read_back == test_content, "文件内容不一致"
    print("  [PASS] 文件读取成功")
    test_file.unlink()

    # 测试 dry-run
    print("\n测试 dry-run...")
    dry_file = Path(tempfile.gettempdir()) / "dry_run_test.txt"
    dry_content = "测试"
    write_file(str(dry_file), dry_content, dry_run=True)
    assert not dry_file.exists(), "dry-run 不应创建文件"
    print("  [PASS] dry-run 未写入文件")

    print("\n============================================================")
    print("自检全部通过!")
    print("============================================================")
    return 0


def main():
    parser = argparse.ArgumentParser(description="批量文本处理工具")
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--format", "-f", choices=["json", "text", "markdown"], default="text",
                        help="输出格式（默认: text）")
    parser.add_argument("--dry-run", action="store_true", help="只显示将执行的操作，不实际写入")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    # 从输入文件读取内容
    if args.input:
        content = Path(args.input).read_text(encoding="utf-8")
        items = [line.strip() for line in content.splitlines() if line.strip()]
    else:
        # 从标准输入读取
        items = [line.strip() for line in sys.stdin if line.strip()]

    if not items:
        print("错误: 没有输入内容", file=sys.stderr)
        return 1

    # 格式化输出
    output = process_items(items, args.format)

    # 输出或写入文件
    if args.output:
        write_file(args.output, output, args.dry_run)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
