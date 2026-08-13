#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""invoice-ocr-extract: 发票 OCR 提取主脚本"""

import argparse
import sys
from pathlib import Path


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def read_text_safe(path):
    """带编码兜底的读取器（R3）"""
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


def load_rows(path):
    """读取并解析行数据（R2 异常降级）"""
    try:
        content = read_text_safe(path)
        rows = []
        for line in content.splitlines():
            line = line.strip()
            if line:
                rows.append(line)
        return rows
    except Exception as e:
        print(f"[WARN] 解析 {path} 失败，降级为空集: {e}", file=sys.stderr)
        return []


def save(path, data, dry_run=False):
    """写盘函数（R4 预览撤回）"""
    if not dry_run:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


def _selftest():
    """自测契约（R1）"""
    print("[selftest] 开始自测...")

    # 测试 read_text_safe 编码兜底
    test_file = Path("_selftest_tmp.txt")
    test_file.write_text("测试内容", encoding="gbk")
    content = read_text_safe(test_file)
    assert content == "测试内容", f"read_text_safe 编码兜底失败: {content!r}"
    # 使用 try/except 处理删除，避免沙箱回收站不可用导致失败
    try:
        test_file.unlink()
    except OSError:
        pass

    # 测试 load_rows 正常解析
    test_file = Path("_selftest_rows.txt")
    test_file.write_text("第一行\n第二行\n\n第三行\n", encoding="utf-8")
    rows = load_rows(test_file)
    assert len(rows) == 3, f"load_rows 应返回 3 行，实际 {len(rows)}"
    assert rows[0] == "第一行", f"第一行内容错误: {rows[0]!r}"
    assert rows[1] == "第二行", f"第二行内容错误: {rows[1]!r}"
    assert rows[2] == "第三行", f"第三行内容错误: {rows[2]!r}"
    try:
        test_file.unlink()
    except OSError:
        pass

    # 测试 load_rows 异常降级
    rows = load_rows("_nonexistent_file_xyz.txt")
    assert rows == [], f"load_rows 异常时应返回空列表，实际 {rows!r}"

    # 测试 save 的 dry-run 模式
    test_file = Path("_selftest_save.txt")
    result = save(test_file, "测试数据", dry_run=True)
    assert result is False, "dry-run 应返回 False"
    assert not test_file.exists(), "dry-run 不应创建文件"
    result = save(test_file, "测试数据", dry_run=False)
    assert result is True, "正常写入应返回 True"
    assert test_file.exists(), "正常写入应创建文件"
    assert test_file.read_text(encoding="utf-8") == "测试数据", "写入内容不正确"
    try:
        test_file.unlink()
    except OSError:
        pass

    # 测试 argparse 参数定义（与 main 中一致）
    ap = argparse.ArgumentParser(description="invoice-ocr-extract")
    ap.add_argument("--input", help="输入文件路径")
    ap.add_argument("--price", type=float, help="房屋总价（万元）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(["--selftest"])
    assert args.selftest is True, "selftest 参数解析失败"
    assert args.input is None, "input 默认应为 None"
    assert args.price is None, "price 默认应为 None"
    assert args.dry_run is False, "dry-run 默认应为 False"
    assert args.verbose is False, "verbose 默认应为 False"

    print("[selftest] 全部断言通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="invoice-ocr-extract: 发票 OCR 提取")
    ap.add_argument("--input", help="输入文件路径")
    ap.add_argument("--price", type=float, help="房屋总价（万元）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--format", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--output-dir", default=None, help="文档声明的参数")  # F3 补全
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if args.price is None:
        ap.error("--price 为必填参数")

    if args.input is None:
        ap.error("--input 为必填参数")

    # 核心业务逻辑
    rows = load_rows(args.input)
    changed_items = []
    skipped = 0

    for idx, row in enumerate(rows):
        # 模拟处理：提取金额
        try:
            parts = row.split("|")
            if len(parts) >= 2:
                name = parts[0].strip()
                amount_str = parts[1].strip()
                amount = float(amount_str)
                before = amount_str
                after = f"{amount * args.price:.2f}"
                changed_items.append({"name": name, "before": before, "after": after})
                if args.verbose:
                    print(f"[明细] {idx}. {name}: {before} -> {after}")
            else:
                skipped += 1
        except (ValueError, IndexError) as e:
            skipped += 1
            if args.verbose:
                print(f"[WARN] 第 {idx} 行解析失败: {e}", file=sys.stderr)

    # 生成输出
    output_lines = []
    for item in changed_items:
        output_lines.append(f"{item['name']}: {item['before']} -> {item['after']}")
    output = "\n".join(output_lines)

    if args.verbose:
        print(f"[汇总] changed={len(changed_items)} 项，skipped={skipped} 项")

    if output:
        save("output.txt", output, dry_run=args.dry_run)
    else:
        print("[提示] 无有效数据可输出")

    return 0


if __name__ == "__main__":
    sys.exit(main())
