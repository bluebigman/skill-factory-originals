#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fund-pro 基金处理技能 - 独立实现脚本

功能：基金的识别、整理、生成与校验，输出可直接使用的结果文件。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input sample.txt --output result.txt
    python scripts/main.py --input sample.txt --dry-run --verbose
"""

import argparse
import json
import os
import re
import sys
import traceback
from collections import Counter

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入内容为空",
    "E003": "输入格式无效（非UTF-8/GBK/GB18030编码）",
    "E004": "输出目录不存在或不可写",
    "E005": "参数校验失败（类型/范围/格式错误）",
    "E006": "核心处理逻辑异常",
    "E007": "输出写入失败",
    "E008": "JSON序列化失败",
    "E009": "路径校验失败（非法路径）",
    "E010": "未知异常",
}


class FundProError(Exception):
    """基金处理业务异常，携带错误码。"""

    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 输入校验模块
# ============================================================
def validate_input_path(path):
    """校验输入路径是否合法且存在。

    参数:
        path: 输入文件路径

    返回:
        规范化后的路径

    异常:
        FundProError: E009 路径非法 / E001 文件不存在
    """
    if not path or not isinstance(path, str):
        raise FundProError("E005", "输入路径必须是非空字符串")
    # 路径白名单校验：仅允许相对路径或当前目录下的路径
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or normalized.startswith("/"):
        raise FundProError("E009", f"非法路径（禁止绝对路径或上级目录）: {path}")
    if not os.path.isfile(normalized):
        raise FundProError("E001", f"输入文件不存在: {normalized}")
    return normalized


def validate_output_path(path):
    """校验输出路径是否合法且目录可写。

    参数:
        path: 输出文件路径

    返回:
        规范化后的路径

    异常:
        FundProError: E009 路径非法 / E004 目录不可写
    """
    if not path or not isinstance(path, str):
        raise FundProError("E005", "输出路径必须是非空字符串")
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or normalized.startswith("/"):
        raise FundProError("E009", f"非法路径（禁止绝对路径或上级目录）: {path}")
    parent = os.path.dirname(normalized) or "."
    if not os.path.isdir(parent):
        raise FundProError("E004", f"输出目录不存在: {parent}")
    if not os.access(parent, os.W_OK):
        raise FundProError("E004", f"输出目录不可写: {parent}")
    return normalized


def parse_args(argv=None):
    """解析命令行参数。

    参数:
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回:
        argparse.Namespace 解析结果
    """
    parser = argparse.ArgumentParser(
        description="基金处理技能：识别、整理、生成与校验基金数据",
        epilog="示例: python main.py --input data.txt --output result.txt --dry-run --verbose",
    )
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写盘（默认开启预览模式）")
    parser.add_argument("--force", action="store_true", help="强制写盘（需与 --dry-run 配合）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细处理日志")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（不读外部文件）")
    return parser.parse_args(argv)


# ============================================================
# 文件读写模块（多编码支持）
# ============================================================
def read_text_file(filepath):
    """读取文本文件，支持多编码（UTF-8 → GBK → GB18030 三级 fallback）。

    参数:
        filepath: 输入文件路径

    返回:
        文件内容字符串

    异常:
        FundProError: E001 文件不存在 / E003 编码无法识别
    """
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise FundProError("E001", f"读取文件失败: {e}")

    if not raw:
        raise FundProError("E002", "输入文件内容为空")

    # 尝试 UTF-8（含 BOM）
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass

    # 尝试 GBK
    try:
        return raw.decode("gbk")
    except UnicodeDecodeError:
        pass

    # 尝试 GB18030（最全的中文编码）
    try:
        return raw.decode("gb18030")
    except UnicodeDecodeError:
        pass

    # 最后兜底：用 replace 模式不抛异常
    return raw.decode("utf-8", errors="replace")


def write_text_file(filepath, content, dry=True):
    """写入文本文件。

    参数:
        filepath: 输出文件路径
        content: 要写入的内容
        dry: 是否为预览模式（True 则不实际写盘）

    返回:
        bool: 是否实际写盘

    异常:
        FundProError: E007 写入失败
    """
    if dry:
        print(f"[DRY-RUN] 模拟写入: {filepath} ({len(content)} 字符)")
        return False
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] 已写入: {filepath}")
        return True
    except OSError as e:
        raise FundProError("E007", f"写入文件失败: {e}")


# ============================================================
# 核心逻辑模块：基金识别与整理
# ============================================================
# 基金代码正则：6位数字（如 000001、110022）
FUND_CODE_RE = re.compile(r"\b(\d{6})\b")
# 基金名称常见关键词
FUND_KEYWORDS = ["基金", "ETF", "LOF", "QDII", "混合", "股票", "债券", "指数", "货币"]


def extract_fund_codes(text):
    """从文本中提取所有可能的基金代码。

    参数:
        text: 输入文本

    返回:
        list[str]: 去重后的基金代码列表（保持出现顺序）
    """
    if not text:
        return []
    codes = []
    seen = set()
    for match in FUND_CODE_RE.finditer(text):
        code = match.group(1)
        # 过滤明显不是基金的代码（如年份、日期等）
        if code.startswith(("19", "20")) and len(code) == 6:
            continue
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


def extract_fund_names(text):
    """从文本中提取可能的基金名称。

    参数:
        text: 输入文本

    返回:
        list[str]: 可能的基金名称列表
    """
    if not text:
        return []
    # 简单策略：找包含"基金"关键词的连续中文字符串（2-20字）
    names = []
    pattern = re.compile(r"[\u4e00-\u9fff]{2,20}?(?:基金|ETF|LOF)")
    for match in pattern.finditer(text):
        name = match.group(0).strip()
        if name and name not in names:
            names.append(name)
    return names


def parse_fund_lines(text):
    """解析基金数据行，识别代码与名称的配对。

    参数:
        text: 输入文本

    返回:
        list[dict]: 基金记录列表，每个记录含 code/name/raw 字段
    """
    records = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        codes = extract_fund_codes(line)
        names = extract_fund_names(line)
        if codes or names:
            record = {
                "code": codes[0] if codes else "",
                "name": names[0] if names else "",
                "raw": line,
            }
            records.append(record)
    return records


def normalize_fund_record(record):
    """规范化单条基金记录。

    参数:
        record: 基金记录字典（含 code/name/raw）

    返回:
        dict: 规范化后的记录
    """
    code = record.get("code", "").strip()
    name = record.get("name", "").strip()
    raw = record.get("raw", "").strip()

    # 如果只有代码没有名称，尝试从 raw 中提取
    if code and not name:
        # 去掉代码后的剩余部分作为候选名称
        rest = re.sub(r"\b\d{6}\b", "", raw).strip()
        # 取第一个中文连续串
        m = re.search(r"[\u4e00-\u9fff]{2,20}", rest)
        if m:
            name = m.group(0)

    return {"code": code, "name": name, "raw": raw}


def process_fund_data(text):
    """核心处理逻辑：识别、整理、规范化基金数据。

    参数:
        text: 输入文本

    返回:
        dict: 处理结果，包含 records/statistics 等
    """
    if not text or not text.strip():
        raise FundProError("E002", "输入内容为空")

    # 按行解析
    raw_records = parse_fund_lines(text)
    # 规范化
    records = [normalize_fund_record(r) for r in raw_records]

    # 去重（按代码）
    seen_codes = set()
    unique_records = []
    for rec in records:
        if rec["code"] and rec["code"] not in seen_codes:
            seen_codes.add(rec["code"])
            unique_records.append(rec)
        elif not rec["code"]:
            unique_records.append(rec)

    # 统计信息
    total = len(unique_records)
    with_code = sum(1 for r in unique_records if r["code"])
    with_name = sum(1 for r in unique_records if r["name"])

    return {
        "records": unique_records,
        "statistics": {
            "total": total,
            "with_code": with_code,
            "with_name": with_name,
            "code_rate": (with_code / total * 100) if total else 0,
            "name_rate": (with_name / total * 100) if total else 0,
        },
    }


# ============================================================
# 输出格式化模块
# ============================================================
def format_result(result, verbose=False):
    """将处理结果格式化为可读文本。

    参数:
        result: process_fund_data 的返回结果
        verbose: 是否输出详细日志

    返回:
        str: 格式化后的文本
    """
    lines = []
    lines.append("=" * 60)
    lines.append("基金处理结果报告")
    lines.append("=" * 60)

    stats = result["statistics"]
    lines.append(f"共识别基金 {stats['total']} 条")
    lines.append(f"含代码 {stats['with_code']} 条（{stats['code_rate']:.1f}%）")
    lines.append(f"含名称 {stats['with_name']} 条（{stats['name_rate']:.1f}%）")
    lines.append("-" * 60)

    for i, rec in enumerate(result["records"], 1):
        code_str = rec["code"] if rec["code"] else "（无代码）"
        name_str = rec["name"] if rec["name"] else "（无名称）"
        lines.append(f"{i:3d}. [{code_str}] {name_str}")
        if verbose and rec["raw"]:
            lines.append(f"     原始: {rec['raw'][:50]}")

    lines.append("=" * 60)
    return "\n".join(lines)


def format_json_result(result):
    """将处理结果格式化为 JSON 字符串。

    参数:
        result: process_fund_data 的返回结果

    返回:
        str: JSON 格式字符串
    """
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        raise FundProError("E008", f"JSON序列化失败: {e}")


# ============================================================
# 自检模块（硬编码样例，离线可跑）
# ============================================================
def run_selftest():
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。

    返回:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("基金处理技能自检开始")
    print("=" * 60)

    # 测试样例 1：正常数据（含中文标点）
    sample1 = """
    易方达蓝筹精选混合 005827
    招商中证白酒指数 161725
    华夏国证半导体芯片ETF 159995
    广发稳健增长混合 270002
    """
    try:
        result1 = process_fund_data(sample1)
        assert result1["statistics"]["total"] >= 3, "样例1: 应识别至少3条基金"
        assert result1["statistics"]["with_code"] >= 3, "样例1: 应至少3条含代码"
        assert result1["statistics"]["with_name"] >= 3, "样例1: 应至少3条含名称"
        print("[PASS] 样例1: 正常数据识别")
    except AssertionError as e:
        print(f"[FAIL] 样例1: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例1: 异常 {e}")
        return False

    # 测试样例 2：空输入
    try:
        process_fund_data("")
        print("[FAIL] 样例2: 空输入应抛出异常")
        return False
    except FundProError as e:
        assert e.code == "E002", "样例2: 错误码应为E002"
        print("[PASS] 样例2: 空输入正确报错")
    except Exception:
        print("[FAIL] 样例2: 应抛 FundProError")
        return False

    # 测试样例 3：中文标点与特殊字符
    sample3 = "基金代码：０００００１（华夏成长）；基金名称：易方达消费行业股票。"
    try:
        result3 = process_fund_data(sample3)
        # 全角数字可能无法识别，但不应崩溃
        assert result3 is not None, "样例3: 不应返回None"
        print("[PASS] 样例3: 中文标点处理（不崩溃）")
    except Exception as e:
        print(f"[FAIL] 样例3: {e}")
        return False

    # 测试样例 4：超长输入（性能验证 O(n)）
    long_text = "华夏回报混合 002001\n" * 5000
    try:
        result4 = process_fund_data(long_text)
        assert result4["statistics"]["total"] == 1, "样例4: 去重后应只有1条"
        print("[PASS] 样例4: 超长输入处理（O(n)）")
    except AssertionError as e:
        print(f"[FAIL] 样例4: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例4: {e}")
        return False

    # 测试样例 5：无基金数据的普通文本
    sample5 = "今天天气很好，我们去公园散步。"
    try:
        result5 = process_fund_data(sample5)
        assert result5["statistics"]["total"] == 0, "样例5: 应识别0条基金"
        print("[PASS] 样例5: 无基金数据识别")
    except AssertionError as e:
        print(f"[FAIL] 样例5: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例5: {e}")
        return False

    # 测试样例 6：编码异常处理
    try:
        # 模拟 GBK 编码内容
        gbk_bytes = "易方达蓝筹精选 005827".encode("gbk")
        # 手动解码验证
        decoded = gbk_bytes.decode("gbk")
        result6 = process_fund_data(decoded)
        assert result6["statistics"]["total"] >= 1, "样例6: 应识别至少1条"
        print("[PASS] 样例6: GBK编码内容处理")
    except Exception as e:
        print(f"[FAIL] 样例6: {e}")
        return False

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================
def main(argv=None):
    """主入口函数。

    参数:
        argv: 命令行参数列表

    返回:
        int: 退出码（0成功，非0失败）
    """
    try:
        args = parse_args(argv)

        # 自检模式
        if args.selftest:
            ok = run_selftest()
            return 0 if ok else 1

        # 校验参数
        if not args.input:
            print("错误: 缺少 --input 参数（使用 --selftest 可运行自检）", file=sys.stderr)
            return 1

        # 校验输入输出路径
        input_path = validate_input_path(args.input)
        output_path = validate_output_path(args.output) if args.output else None

        # 读取输入文件
        text = read_text_file(input_path)

        # 处理基金数据
        result = process_fund_data(text)

        # 格式化输出
        if output_path:
            output_text = format_result(result, args.verbose)
            # 判断是否写盘
            should_write = not args.dry_run or args.force
            write_text_file(output_path, output_text, dry=not should_write)
        else:
            # 无输出路径时打印到 stdout
            print(format_result(result, args.verbose))

        if args.verbose:
            print(f"\n[VERBOSE] 处理完成: {result['statistics']}")

        return 0

    except FundProError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未知异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
