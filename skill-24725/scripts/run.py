#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-24725 主脚本
功能：根据房屋总价计算税费，支持 dry-run 预览、verbose 明细、selftest 自测
"""

import argparse
import sys
from pathlib import Path


def read_text_safe(path):
    """R3 编码兜底：依次尝试 utf-8 / gbk / gb18030，最后用 errors=replace 兜底"""
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
    """R2 异常降级：解析失败时降级为空集"""
    try:
        return _parse(path)
    except Exception as e:
        print(f"[WARN] 解析 {path} 失败，降级为空集: {e}", file=sys.stderr)
        return []


def _parse(path):
    """R5 大输入流式：逐行读取，不 f.read() 全量"""
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # 简单 CSV 解析：假设格式为 "名称,价格"
            parts = line.split(",")
            if len(parts) < 2:
                continue
            name = parts[0].strip()
            try:
                price = float(parts[1].strip())
            except ValueError:
                continue
            rows.append({"name": name, "price": price})
    return rows


def save(path, data, dry_run=False):
    """R4 预览撤回：写盘必须包在 if not dry_run 分支内"""
    if not dry_run:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


def calculate_tax(price):
    """根据价格计算税费（示例规则：价格*0.05）"""
    return price * 0.05


def process_items(rows, verbose=False):
    """处理数据：计算税费，返回修改明细"""
    changed_items = []
    skipped = 0
    for idx, item in enumerate(rows, 1):
        try:
            tax = calculate_tax(item["price"])
            before = item.get("tax", None)
            item["tax"] = tax
            after = tax
            changed_items.append({
                "name": item["name"],
                "before": before,
                "after": after,
                "idx": idx
            })
            if verbose:
                print(f"[明细] {idx}. {item['name']}: {before} -> {after}")
        except Exception as e:
            skipped += 1
            print(f"[WARN] 处理第 {idx} 条失败: {e}", file=sys.stderr)
    return changed_items, skipped


def _selftest():
    """R1 契约先于代码：自测函数，验证核心逻辑"""
    # 构造测试数据
    test_rows = [
        {"name": "房屋A", "price": 100.0},
        {"name": "房屋B", "price": 200.0},
        {"name": "房屋C", "price": 300.0},
    ]

    # 测试 calculate_tax
    assert calculate_tax(100.0) == 5.0, "calculate_tax(100) 应为 5.0"
    assert calculate_tax(200.0) == 10.0, "calculate_tax(200) 应为 10.0"
    assert calculate_tax(0.0) == 0.0, "calculate_tax(0) 应为 0.0"

    # 测试 process_items
    changed, skipped = process_items(test_rows, verbose=False)
    assert len(changed) == 3, f"应处理 3 条，实际 {len(changed)}"
    assert skipped == 0, f"不应有跳过，实际 {skipped}"
    assert changed[0]["before"] is None, "第一条 before 应为 None"
    assert changed[0]["after"] == 5.0, "第一条 after 应为 5.0"
    assert changed[1]["after"] == 10.0, "第二条 after 应为 10.0"
    assert changed[2]["after"] == 15.0, "第三条 after 应为 15.0"

    # 测试 save 的 dry-run 分支
    test_path = Path("_selftest_tmp.txt")
    result = save(str(test_path), "test data", dry_run=True)
    assert result is False, "dry_run=True 应返回 False"
    assert not test_path.exists(), "dry_run 不应创建文件"

    # 测试 save 的真实写入
    result = save(str(test_path), "test data", dry_run=False)
    assert result is True, "dry_run=False 应返回 True"
    assert test_path.exists(), "应创建文件"
    content = read_text_safe(str(test_path))
    assert content == "test data", f"文件内容应为 'test data'，实际 '{content}'"
    test_path.unlink()  # 清理

    # 测试 read_text_safe 的编码兜底
    # 创建一个 GBK 编码的文件
    gbk_path = Path("_selftest_gbk.txt")
    gbk_path.write_bytes("测试数据".encode("gbk"))
    content = read_text_safe(str(gbk_path))
    assert content == "测试数据", f"GBK 读取失败，实际 '{content}'"
    gbk_path.unlink()

    print("[selftest] 全部断言通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="skill-24725 税费计算工具")
    ap.add_argument("--input", help="输入文件路径（CSV：名称,价格）")
    ap.add_argument("--price", type=float, help="房屋总价（万元）")
    ap.add_argument("--selftest", action="store_true", help="运行自测")
    ap.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    ap.add_argument("--verbose", action="store_true", help="输出详细修改明细")
    args = ap.parse_args()

    # R1 契约先于代码：selftest 必须在所有必填校验之前
    if args.selftest:
        return _selftest()

    # 业务分支：手工校验必填参数
    if args.price is None and args.input is None:
        ap.error("--price 或 --input 至少提供一个")

    # 处理输入
    if args.input:
        rows = load_rows(args.input)
        if not rows:
            print("[WARN] 输入文件无有效数据", file=sys.stderr)
            return 0
        changed_items, skipped = process_items(rows, verbose=args.verbose)
        # 生成输出
        output_lines = []
        for item in rows:
            output_lines.append(f"{item['name']},{item['price']},{item.get('tax', 0.0)}")
        output = "\n".join(output_lines) + "\n"
        save(args.input + ".out", output, dry_run=args.dry_run)
        print(f"[汇总] changed={len(changed_items)} 项，skipped={skipped} 项")
    elif args.price is not None:
        # 单价格模式
        tax = calculate_tax(args.price)
        if args.verbose:
            print(f"[明细] 1. 房屋: {args.price} -> {tax}")
        print(f"[汇总] changed=1 项，skipped=0 项")
        if not args.dry_run:
            print(f"[结果] 税费: {tax:.2f} 万元")
        else:
            print(f"[dry-run] 将输出税费 {tax:.2f} 万元，未落盘")

    return 0


if __name__ == "__main__":
    sys.exit(main())
