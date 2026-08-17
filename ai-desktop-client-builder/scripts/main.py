#!/usr/bin/env python3
"""AI 桌面客户端构建器 - 主脚本"""
import argparse
import sys
from pathlib import Path


def read_text_safe(path):
    """安全读取文本文件，支持多编码降级"""
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
    """加载数据行，带异常降级"""
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
    """写入文件，支持 dry-run 预览"""
    if not dry_run:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


def _selftest():
    """自测函数：验证核心功能"""
    import tempfile
    import os

    # 测试数据
    test_content = "line1\nline2\nline3\n"
    test_path = Path(tempfile.mktemp(suffix=".txt"))

    # 测试 read_text_safe
    test_path.write_text(test_content, encoding="utf-8")
    assert read_text_safe(test_path) == test_content, "read_text_safe 读取失败"

    # 测试 load_rows
    rows = load_rows(test_path)
    assert len(rows) == 3, f"load_rows 应返回 3 行，实际 {len(rows)}"
    assert rows[0] == "line1", "第一行内容错误"
    assert rows[1] == "line2", "第二行内容错误"
    assert rows[2] == "line3", "第三行内容错误"

    # 测试 save 的 dry-run 模式
    save_path = Path(tempfile.mktemp(suffix=".txt"))
    result = save(save_path, "test data", dry_run=True)
    assert result is False, "dry-run 应返回 False"
    assert not save_path.exists(), "dry-run 不应创建文件"

    # 测试 save 的正常写入
    result = save(save_path, "test data", dry_run=False)
    assert result is True, "正常写入应返回 True"
    assert save_path.exists(), "正常写入应创建文件"
    assert save_path.read_text(encoding="utf-8") == "test data", "写入内容不匹配"

    # 测试异常降级
    nonexist_path = Path("/nonexistent/path/file.txt")
    assert load_rows(nonexist_path) == [], "不存在的文件应返回空列表"

    # 清理测试文件
    for p in [test_path, save_path]:
        if p.exists():
            p.unlink()

    print("[selftest] 全部断言通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="AI 桌面客户端构建器")
    ap.add_argument("--input", help="输入文件路径")
    ap.add_argument("--price", type=float, help="房屋总价（万元）")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if args.price is None:
        ap.error("--price 为必填参数")

    # 业务逻辑
    if args.input:
        rows = load_rows(args.input)
        changed_items = []
        skipped = 0

        for idx, row in enumerate(rows):
            # 模拟处理：计算价格相关指标
            try:
                price = args.price
                before = row
                after = f"{row} (价格: {price}万)"
                changed_items.append({"name": row, "before": before, "after": after})

                if args.verbose:
                    print(f"[明细] {idx}. {row}: {before} -> {after}")
            except Exception as e:
                skipped += 1
                print(f"[WARN] 处理第 {idx} 行失败: {e}", file=sys.stderr)

        print(f"[汇总] changed={len(changed_items)} 项，skipped={skipped} 项")

        if not args.dry_run:
            output_path = Path("output.txt")
            output_data = "\n".join([item["after"] for item in changed_items])
            save(output_path, output_data, dry_run=False)
    else:
        print("[INFO] 未提供输入文件，仅演示参数校验")
        print(f"[INFO] 价格: {args.price} 万元")

    return 0


if __name__ == "__main__":
    sys.exit(main())
