#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bedrock 技能实现
数据解析 / 信息抽取 / 结构化输出，支持批量处理与置信度标注。
仅依赖标准库，独立实现（clean-room）。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或不是有效文本",
    "E002": "输入数据格式不支持（仅支持文本/JSON/CSV）",
    "E003": "JSON 解析失败",
    "E004": "字段提取失败：未找到任何关键信息",
    "E005": "批量处理输入格式错误",
    "E006": "输出序列化失败",
    "E007": "置信度计算异常",
    "E008": "参数校验失败",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class BedrockError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class FieldResult:
    """单个字段的提取结果。"""

    def __init__(self, name: str, value: Any, confidence: float):
        self.name = name
        self.value = value
        self.confidence = confidence  # 0.0 ~ 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence,
        }


class ParseResult:
    """一条数据解析的完整结果。"""

    def __init__(self, source: str = "", fields: Optional[List[FieldResult]] = None):
        self.source = source
        self.fields = fields or []
        self.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> Dict[str, Any]:
        data = {}
        for field in self.fields:
            data[field.name] = field.to_dict()
        return {
            "data": data,
            "summary": self._build_summary(),
        }

    def _build_summary(self) -> Dict[str, Any]:
        if not self.fields:
            return {
                "total_fields": 0,
                "needs_review": 0,
                "avg_confidence": 0.0,
            }
        total = len(self.fields)
        needs_review = sum(1 for f in self.fields if f.confidence < 0.7)
        avg_conf = sum(f.confidence for f in self.fields) / total
        return {
            "total_fields": total,
            "needs_review": needs_review,
            "avg_confidence": round(avg_conf, 4),
        }


# ============================================================
# 内置字段提取规则（自动推断）
# ============================================================

BUILTIN_RULES = [
    {
        "name": "order_id",
        "pattern": r"订单号[：:\s]*([A-Z]\d{4,6})",
        "type": "string",
    },
    {
        "name": "amount",
        "pattern": r"金额[：:\s]*([0-9.]+)\s*元",
        "type": "float",
    },
    {
        "name": "date",
        "pattern": r"日期[：:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        "type": "date",
    },
    {
        "name": "user_id",
        "pattern": r"用户[IDid]{0,2}[：:\s]*([a-zA-Z0-9_]+)",
        "type": "string",
    },
    {
        "name": "phone",
        "pattern": r"电话[：:\s]*(1[3-9]\d{9})",
        "type": "string",
    },
    {
        "name": "email",
        "pattern": r"邮箱[：:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        "type": "string",
    },
]


# ============================================================
# 字段提取核心逻辑
# ============================================================

def _convert_type(value: str, field_type: str) -> Tuple[Any, float]:
    """类型转换，返回 (转换后的值, 置信度)。"""
    try:
        if field_type == "int":
            return int(value), 0.95
        elif field_type == "float":
            return float(value), 0.95
        elif field_type == "date":
            # 尝试解析 ISO 8601 日期
            datetime.strptime(value, "%Y-%m-%d")
            return value, 0.95
        else:
            return value, 0.95
    except (ValueError, TypeError):
        # 类型转换失败，降级为字符串
        return value, 0.75


def extract_fields(text: str, config: Optional[Dict] = None) -> List[FieldResult]:
    """从文本中提取字段。"""
    if not text or not text.strip():
        raise BedrockError("E001")

    # 合并内置规则与自定义规则
    rules = list(BUILTIN_RULES)
    custom_rules = []
    if config and "field_mappings" in config:
        for name, rule in config["field_mappings"].items():
            custom_rules.append({
                "name": name,
                "pattern": rule.get("pattern", ""),
                "type": rule.get("type", "string"),
                "required": rule.get("required", False),
            })
        # 自定义规则优先
        rules = custom_rules + rules

    fields = []
    for rule in rules:
        try:
            pattern = rule.get("pattern", "")
            if not pattern:
                continue
            match = re.search(pattern, text)
            if match:
                raw_value = match.group(1)
                value, conf = _convert_type(raw_value, rule.get("type", "string"))
                fields.append(FieldResult(rule["name"], value, conf))
            elif rule.get("required", False):
                # 必填字段缺失，标记低置信度
                fields.append(FieldResult(rule["name"], None, 0.0))
        except re.error as e:
            print(f"WARNING: 正则错误 [{rule.get('name', 'unknown')}]: {e}", file=sys.stderr)
            continue

    if not fields:
        raise BedrockError("E004")

    return fields


# ============================================================
# 输入处理
# ============================================================

def _read_with_encoding(file_path: str) -> str:
    """多编码读取文件：utf-8 → gbk → gb18030 三级 fallback。"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise BedrockError("E001", f"文件不存在: {file_path}")
    # 最后兜底：errors="replace"
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _parse_single_input(raw: str) -> str:
    """解析单条输入，支持 JSON 包装或纯文本。"""
    raw = raw.strip()
    if not raw:
        raise BedrockError("E001")

    # 尝试 JSON 解析
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "raw" in data:
            return str(data["raw"])
        elif isinstance(data, str):
            return data
        else:
            return json.dumps(data, ensure_ascii=False)
    except json.JSONDecodeError:
        # 纯文本，直接返回
        return raw


# ============================================================
# 批量处理
# ============================================================

def process_batch(input_file: str, config: Optional[Dict] = None,
                  dry_run: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """批量处理输入文件，返回汇总统计。"""
    stats = {
        "total_records": 0,
        "success_count": 0,
        "needs_review_count": 0,
        "avg_confidence": 0.0,
        "failed_records": [],
    }
    conf_sum = 0.0

    try:
        with open(input_file, "r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                stats["total_records"] += 1
                try:
                    text = _parse_single_input(line)
                    fields = extract_fields(text, config)
                    result = ParseResult(source=line, fields=fields)
                    result_dict = result.to_dict()

                    if verbose:
                        print(f"行 {line_num}: 提取 {len(fields)} 个字段", file=sys.stderr)
                        for field in fields:
                            print(f"  - {field.name}: {field.value} (置信度: {field.confidence})", file=sys.stderr)

                    # 输出结果
                    output_line = json.dumps(result_dict, ensure_ascii=False)
                    if not dry_run:
                        print(output_line)
                    else:
                        print(f"[DRY-RUN] 行 {line_num}: {output_line}")

                    stats["success_count"] += 1
                    if result_dict["summary"]["needs_review"] > 0:
                        stats["needs_review_count"] += 1
                    conf_sum += result_dict["summary"]["avg_confidence"]

                except BedrockError as e:
                    stats["failed_records"].append(line_num)
                    print(f"ERROR: 行 {line_num}: {e}", file=sys.stderr)
                except Exception as e:
                    stats["failed_records"].append(line_num)
                    print(f"ERROR: 行 {line_num}: 未知错误 {e}", file=sys.stderr)

    except FileNotFoundError:
        raise BedrockError("E001", f"文件不存在: {input_file}")
    except Exception as e:
        raise BedrockError("E005", f"批量处理失败: {e}")

    if stats["total_records"] > 0:
        stats["avg_confidence"] = round(conf_sum / stats["total_records"], 4)

    return stats


# ============================================================
# 原子化文件写入
# ============================================================

def atomic_write(file_path: str, content: str, dry_run: bool = False) -> bool:
    """原子化写入文件：先写临时文件，再 rename。"""
    if not dry_run:
        dir_name = os.path.dirname(os.path.abspath(file_path))
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, file_path)
            print(f"[写入] {file_path}")
            return True
        except Exception:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")
    return False


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("=== bedrock selftest ===")

    # 测试 1：单条解析
    print("\n[测试 1] 单条解析")
    test_input = "订单号 A12345，金额 89.90 元，日期 2024-03-15"
    try:
        fields = extract_fields(test_input)
        assert len(fields) >= 3, f"期望至少 3 个字段，实际 {len(fields)}"
        field_names = [f.name for f in fields]
        assert "order_id" in field_names, f"缺少 order_id: {field_names}"
        assert "amount" in field_names, f"缺少 amount: {field_names}"
        assert "date" in field_names, f"缺少 date: {field_names}"
        for f in fields:
            assert 0.0 <= f.confidence <= 1.0, f"置信度越界: {f.confidence}"
        print(f"  PASS: 提取 {len(fields)} 个字段，置信度均有效")
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return 1
    except Exception as e:
        print(f"  FAIL: 异常 {e}")
        return 1

    # 测试 2：空输入
    print("\n[测试 2] 空输入处理")
    try:
        extract_fields("")
        print("  FAIL: 空输入未抛出异常")
        return 1
    except BedrockError as e:
        assert e.code == "E001", f"错误码错误: {e.code}"
        print(f"  PASS: 正确抛出 E001")
    except Exception as e:
        print(f"  FAIL: 异常类型错误 {e}")
        return 1

    # 测试 3：自定义配置
    print("\n[测试 3] 自定义配置")
    config = {
        "field_mappings": {
            "custom_id": {
                "pattern": r"编号[：:\s]*([A-Z]\d{3})",
                "type": "string",
                "required": True,
            }
        },
        "confidence_threshold": 0.7,
    }
    try:
        fields = extract_fields("编号 X123，金额 45 元", config)
        assert len(fields) >= 1, "自定义配置未生效"
        custom_fields = [f for f in fields if f.name == "custom_id"]
        assert len(custom_fields) == 1, f"custom_id 提取失败: {fields}"
        assert custom_fields[0].value == "X123", f"custom_id 值错误: {custom_fields[0].value}"
        print(f"  PASS: 自定义配置生效，提取值 {custom_fields[0].value}")
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return 1
    except Exception as e:
        print(f"  FAIL: 异常 {e}")
        return 1

    # 测试 4：类型转换
    print("\n[测试 4] 类型转换")
    try:
        fields = extract_fields("金额 89.90 元")
        amount_fields = [f for f in fields if f.name == "amount"]
        assert len(amount_fields) == 1, "amount 提取失败"
        assert isinstance(amount_fields[0].value, float), f"amount 类型错误: {type(amount_fields[0].value)}"
        assert abs(amount_fields[0].value - 89.9) < 0.01, f"amount 值错误: {amount_fields[0].value}"
        print(f"  PASS: 类型转换正确，值 {amount_fields[0].value}")
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return 1
    except Exception as e:
        print(f"  FAIL: 异常 {e}")
        return 1

    # 测试 5：批量处理（临时文件）
    print("\n[测试 5] 批量处理")
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("订单号 A12345，金额 89.90 元，日期 2024-03-15\n")
        f.write("订单号 B67890，金额 12.50 元，日期 2024-03-16\n")
        f.write("无效数据行\n")
        tmp_file = f.name
    try:
        stats = process_batch(tmp_file, dry_run=True)
        assert stats["total_records"] == 3, f"总记录数错误: {stats['total_records']}"
        assert stats["success_count"] >= 2, f"成功数错误: {stats['success_count']}"
        assert len(stats["failed_records"]) >= 1, f"失败数错误: {stats['failed_records']}"
        print(f"  PASS: 批量处理统计正确 (成功 {stats['success_count']}/{stats['total_records']})")
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return 1
    except Exception as e:
        print(f"  FAIL: 异常 {e}")
        return 1
    finally:
        os.unlink(tmp_file)

    # 测试 6：中文编码
    print("\n[测试 6] 中文编码")
    try:
        fields = extract_fields("订单号 A12345，金额 89.90 元")
        assert len(fields) >= 2, f"中文解析失败: {fields}"
        print(f"  PASS: 中文解析正常")
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return 1
    except Exception as e:
        print(f"  FAIL: 异常 {e}")
        return 1

    # 测试 7：ParseResult 序列化
    print("\n[测试 7] 序列化")
    try:
        fields = extract_fields("订单号 A12345，金额 89.90 元")
        result = ParseResult(source="test", fields=fields)
        result_dict = result.to_dict()
        assert "data" in result_dict, "缺少 data 键"
        assert "summary" in result_dict, "缺少 summary 键"
        assert "total_fields" in result_dict["summary"], "缺少 total_fields"
        assert "avg_confidence" in result_dict["summary"], "缺少 avg_confidence"
        json_str = json.dumps(result_dict, ensure_ascii=False)
        assert len(json_str) > 0, "序列化结果为空"
        print(f"  PASS: 序列化正常")
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return 1
    except Exception as e:
        print(f"  FAIL: 异常 {e}")
        return 1

    print("\n=== SELFTEST PASSED ===")
    return 0


# ============================================================
# CLI 入口
# ============================================================

def main() -> int:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        prog="bedrock",
        description="数据规整与结构化抽取工具",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse 子命令
    parse_parser = subparsers.add_parser("parse", help="解析数据")
    parse_parser.add_argument("--single", action="store_true", help="单条解析（从 stdin 读取）")
    parse_parser.add_argument("--batch", action="store_true", help="批量解析（从文件读取）")
    parse_parser.add_argument("--input", type=str, help="输入文件路径（批量模式）")
    parse_parser.add_argument("--config", type=str, help="配置文件路径（JSON）")
    parse_parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parse_parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    # selftest 子命令
    subparsers.add_parser("selftest", help="运行自检")

    # 添加 --selftest 顶层参数（兼容验收脚本调用方式）
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 优先处理 --selftest 顶层参数
    if args.selftest:
        return run_selftest()

    if args.command == "selftest":
        return run_selftest()

    if args.command == "parse":
        # 加载配置
        config = None
        if args.config:
            try:
                with open(args.config, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except FileNotFoundError:
                print(f"ERROR: 配置文件不存在: {args.config}", file=sys.stderr)
                return 1
            except json.JSONDecodeError as e:
                print(f"ERROR: 配置文件 JSON 解析失败: {e}", file=sys.stderr)
                return 1

        if args.single:
            # 单条解析
            try:
                raw = sys.stdin.read()
                text = _parse_single_input(raw)
                fields = extract_fields(text, config)
                result = ParseResult(source=text, fields=fields)
                print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
                return 0
            except BedrockError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"ERROR: 未知错误 {e}", file=sys.stderr)
                return 1

        elif args.batch:
            # 批量解析
            if not args.input:
                print("ERROR: 批量模式需要 --input 参数", file=sys.stderr)
                return 1
            try:
                stats = process_batch(args.input, config, args.dry_run, args.verbose)
                # 输出汇总统计（到 stderr，不污染 stdout 的 JSON Lines）
                print(json.dumps(stats, ensure_ascii=False, indent=2), file=sys.stderr)
                return 0
            except BedrockError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"ERROR: 未知错误 {e}", file=sys.stderr)
                return 1
        else:
            print("ERROR: 请指定 --single 或 --batch", file=sys.stderr)
            return 1

    # 无子命令，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
