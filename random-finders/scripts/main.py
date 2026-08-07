#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
random-finders 独立实现（clean-room 重写）

功能概述：
    根据功能规格实现一个通用的“随机查找/随机排序”工具。
    支持从输入数据中随机抽取记录，或按随机顺序返回记录。
    提供命令行接口，并内置 --selftest 离线自检。

错误码：
    E001 输入为空
    E002 关键信息缺失（如样本集为空）
    E003 输入格式错误（如数量参数非法）
    E004 超出能力边界（如请求数量超过样本量）
    E005 置信度过低（自检失败等异常情况）
    E006 内部状态错误（如随机种子非法）
    E007 参数解析错误
    E008 文件读取失败（预留，本实现不使用）
    E009 输出写入失败（预留，本实现不使用）
    E010 未知错误
"""

import argparse
import random
import sys
from typing import Any, List, Optional, Sequence


# ---------------------------------------------------------------------------
# 核心逻辑（与 CLI 解耦，便于测试）
# ---------------------------------------------------------------------------

def random_record(samples: Sequence[Any]) -> Any:
    """
    从样本集中随机返回一条记录。

    参数:
        samples: 非空序列（列表、元组等）

    返回:
        随机选取的一个元素

    异常:
        E001: 输入为空
        E002: 样本集为空（关键信息缺失）
    """
    if samples is None:
        raise RuntimeError("E001: 输入为空，请提供待处理的内容")
    if len(samples) == 0:
        raise RuntimeError("E002: 样本集为空，缺少关键信息")
    return random.choice(list(samples))


def random_records(samples: Sequence[Any], count: int) -> List[Any]:
    """
    从样本集中随机抽取 count 条不重复记录。

    参数:
        samples: 非空序列
        count:   抽取数量（正整数）

    返回:
        随机抽取的记录列表

    异常:
        E001: 输入为空
        E002: 样本集为空
        E003: count 不是正整数
        E004: count 大于样本量（超出能力边界）
    """
    if samples is None:
        raise RuntimeError("E001: 输入为空，请提供待处理的内容")
    if len(samples) == 0:
        raise RuntimeError("E002: 样本集为空，缺少关键信息")
    if not isinstance(count, int) or count <= 0:
        raise RuntimeError("E003: 抽取数量必须为正整数")
    if count > len(samples):
        raise RuntimeError(
            f"E004: 请求抽取 {count} 条，但样本仅有 {len(samples)} 条，超出能力边界"
        )
    return random.sample(list(samples), count)


def random_order(samples: Sequence[Any]) -> List[Any]:
    """
    将样本集按随机顺序返回（洗牌）。

    参数:
        samples: 非空序列

    返回:
        随机排序后的列表（原样本不变）

    异常:
        E001: 输入为空
        E002: 样本集为空
    """
    if samples is None:
        raise RuntimeError("E001: 输入为空，请提供待处理的内容")
    if len(samples) == 0:
        raise RuntimeError("E002: 样本集为空，缺少关键信息")
    result = list(samples)
    random.shuffle(result)
    return result


def parse_input_line(line: str) -> Any:
    """
    将单行文本解析为一条记录（去除首尾空白）。

    参数:
        line: 输入行

    返回:
        去除空白后的字符串

    异常:
        E001: 行内容为空
    """
    if line is None:
        raise RuntimeError("E001: 输入为空，请提供待处理的内容")
    cleaned = line.strip()
    if not cleaned:
        raise RuntimeError("E001: 输入为空，请提供待处理的内容")
    return cleaned


def read_samples_from_text(text: str) -> List[Any]:
    """
    从多行文本中解析样本集（每行一条记录）。

    参数:
        text: 多行文本

    返回:
        非空记录列表

    异常:
        E001: 文本为空
        E002: 解析后无有效记录
    """
    if text is None or text.strip() == "":
        raise RuntimeError("E001: 输入为空，请提供待处理的内容")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("E002: 解析后无有效记录，缺少关键信息")
    return lines


# ---------------------------------------------------------------------------
# 自检（内置硬编码样例，离线运行）
# ---------------------------------------------------------------------------

def _selftest() -> None:
    """
    内置离线自检：使用硬编码样例数据验证核心逻辑。

    断言策略：
        - 使用宽松阈值（大小比较/区间判断）
        - 不依赖精确值或边界值
        - 确保自检样例与实际逻辑必然匹配
    """
    # 固定随机种子，保证可重复性（但断言不依赖具体值）
    random.seed(42)

    # 硬编码样例数据（不读外部文件、不依赖工作目录、不访问网络）
    sample_data = ["apple", "banana", "cherry", "date", "elderberry"]

    # --- 测试 random_record ---
    rec = random_record(sample_data)
    assert rec in sample_data, "random_record 返回值不在样本集中"

    # --- 测试 random_records ---
    picked = random_records(sample_data, 3)
    assert len(picked) == 3, "random_records 返回数量错误"
    assert len(set(picked)) == 3, "random_records 出现重复"

    # --- 测试 random_order ---
    shuffled = random_order(sample_data)
    assert len(shuffled) == len(sample_data), "random_order 长度不一致"
    assert set(shuffled) == set(sample_data), "random_order 元素集合不一致"

    # --- 测试 read_samples_from_text ---
    text_data = "line1\nline2\nline3\n"
    parsed = read_samples_from_text(text_data)
    assert len(parsed) == 3, "read_samples_from_text 解析行数错误"

    # --- 测试 parse_input_line ---
    single = parse_input_line("  hello  ")
    assert single == "hello", "parse_input_line 去除空白失败"

    # --- 错误处理测试（宽松断言：确认抛出 RuntimeError 即可）---
    error_cases = [
        lambda: random_record([]),                     # E002
        lambda: random_records(sample_data, 0),        # E003
        lambda: random_records(sample_data, 999),      # E004
        lambda: random_order([]),                      # E002
        lambda: read_samples_from_text("   "),         # E001
        lambda: parse_input_line("   "),               # E001
    ]
    for fn in error_cases:
        try:
            fn()
            raise AssertionError("预期抛出 RuntimeError，但未抛出")
        except RuntimeError:
            pass  # 符合预期

    # 自检通过
    print("[selftest] 全部自检通过（核心逻辑正常）")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="random-finders",
        description="随机查找/随机排序工具：从输入数据中随机抽取记录或随机排序。"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="输入文本（多行，每行一条记录）；与 --file 互斥",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="输入文件路径（每行一条记录）；与 --input 互斥",
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["one", "many", "shuffle"],
        default="one",
        help="操作类型：one=随机取一条；many=随机取多条；shuffle=随机排序",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="--action=many 时的抽取数量（正整数）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子（可选，便于复现）",
    )
    return parser


def _load_samples(args: argparse.Namespace) -> List[Any]:
    """
    根据命令行参数加载样本集。

    参数:
        args: 解析后的命令行参数

    返回:
        非空样本列表

    异常:
        E001: 未提供任何输入来源
        E003: 同时提供了 --input 和 --file
        E008: 文件读取失败（预留）
    """
    if args.input is not None and args.file is not None:
        raise RuntimeError("E003: --input 与 --file 不能同时使用")

    if args.input is not None:
        return read_samples_from_text(args.input)

    if args.file is not None:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            raise RuntimeError(f"E008: 文件读取失败: {exc}") from exc
        return read_samples_from_text(content)

    raise RuntimeError("E001: 请提供输入内容（--input 或 --file）")


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。

    参数:
        argv: 命令行参数列表（默认取 sys.argv[1:]）

    返回:
        进程退出码（0=成功，非0=失败）
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse 在 -h/--help 或参数错误时会抛 SystemExit
        return int(exc.code) if exc.code is not None else 0

    # 自检模式：不读取外部输入，直接运行并返回
    if args.selftest:
        try:
            _selftest()
            return 0
        except AssertionError as exc:
            print(f"[selftest] 自检失败: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"[selftest] 自检异常: {exc}", file=sys.stderr)
            return 1

    # 设置随机种子（可选）
    if args.seed is not None:
        random.seed(args.seed)

    # 加载样本
    try:
        samples = _load_samples(args)
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    # 执行核心操作
    try:
        if args.action == "one":
            result = random_record(samples)
            print(result)
        elif args.action == "many":
            results = random_records(samples, args.count)
            for item in results:
                print(item)
        elif args.action == "shuffle":
            results = random_order(samples)
            for item in results:
                print(item)
        else:
            # 理论上 argparse 已限制，但保留防御
            raise RuntimeError("E007: 未知操作类型")
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底未知错误
        print(f"错误: E010 未知错误: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
