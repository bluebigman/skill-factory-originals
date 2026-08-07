#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mofo - 通用数据处理与格式化工具

基于功能规格独立实现（clean-room）。
提供数据解析、结构化、置信度评估与输出格式化能力。
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class MofoError(Exception):
    """基础异常类，携带错误码与用户可读信息。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def err_input_empty() -> MofoError:
    return MofoError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")


def err_missing_info(details: str = "") -> MofoError:
    msg = f"还缺少以下信息，请补充：{details}" if details else "还缺少以下信息，请补充：..."
    return MofoError("E002", msg)


def err_bad_format(expected: str = "") -> MofoError:
    msg = f"输入格式不符合要求，示例：{expected}" if expected else "输入格式不符合要求"
    return MofoError("E003", msg)


def err_out_of_scope(suggestion: str = "") -> MofoError:
    msg = f"这超出了本工具的能力范围，建议：{suggestion}" if suggestion else "这超出了本工具的能力范围"
    return MofoError("E004", msg)


def err_low_confidence(suggestion: str = "") -> MofoError:
    msg = f"结果无法确定，建议：{suggestion}" if suggestion else "结果无法确定"
    return MofoError("E005", msg)


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ParsedRecord:
    """单条解析记录。"""
    def __init__(self, key: str, value: Any, confidence: float, note: str = ""):
        self.key = key
        self.value = value
        self.confidence = confidence   # 0.0 ~ 1.0
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "note": self.note,
        }


class ProcessResult:
    """处理结果容器。"""
    def __init__(self):
        self.records: List[ParsedRecord] = []
        self.created_at: str = datetime.now().isoformat(timespec="seconds")

    def add(self, rec: ParsedRecord) -> None:
        self.records.append(rec)

    def overall_confidence(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.confidence for r in self.records) / len(self.records)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at,
            "overall_confidence": round(self.overall_confidence(), 3),
            "records": [r.to_dict() for r in self.records],
        }


# ---------------------------------------------------------------------------
# 核心解析逻辑
# ---------------------------------------------------------------------------
def _detect_format(raw: str) -> str:
    """识别输入格式：json / keyvalue / plain。"""
    if not raw or not raw.strip():
        raise err_input_empty()

    s = raw.strip()
    if s.startswith("{") and s.endswith("}"):
        try:
            json.loads(s)
            return "json"
        except json.JSONDecodeError:
            pass

    # 简单键值对检测：每行包含 "=" 或 ":"
    lines = [ln for ln in s.splitlines() if ln.strip()]
    if lines and all(("=" in ln or ":" in ln) for ln in lines):
        return "keyvalue"

    return "plain"


def _parse_json(raw: str) -> List[ParsedRecord]:
    """解析 JSON 输入。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise err_bad_format(f'{{"name": "张三", "age": 30}} （JSON解析失败: {e}）')

    if not isinstance(data, dict):
        raise err_bad_format('{"key": "value", ...} 对象格式')

    records = []
    for k, v in data.items():
        # 简单置信度评估：非空且非None则较高置信度
        conf = 0.95 if v is not None and v != "" else 0.6
        note = "" if conf >= 0.9 else "值为空或缺失"
        records.append(ParsedRecord(str(k), v, conf, note))
    return records


def _parse_keyvalue(raw: str) -> List[ParsedRecord]:
    """解析 key=value 或 key:value 格式。"""
    records = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        sep = "=" if "=" in ln else ":"
        if sep not in ln:
            continue
        k, _, v = ln.partition(sep)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        conf = 0.9 if v else 0.6
        note = "" if conf >= 0.9 else "值为空"
        records.append(ParsedRecord(k, v, conf, note))
    return records


def _parse_plain(raw: str) -> List[ParsedRecord]:
    """解析纯文本：按行切分，每行作为一条记录。"""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        raise err_input_empty()

    records = []
    for idx, ln in enumerate(lines, 1):
        # 纯文本置信度较低，因为缺少结构
        conf = 0.7
        records.append(ParsedRecord(f"line_{idx}", ln, conf, "纯文本输入，结构不确定"))
    return records


def parse_input(raw: str) -> List[ParsedRecord]:
    """根据输入格式自动选择解析策略。"""
    fmt = _detect_format(raw)
    if fmt == "json":
        return _parse_json(raw)
    elif fmt == "keyvalue":
        return _parse_keyvalue(raw)
    else:
        return _parse_plain(raw)


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: ProcessResult, fmt: str = "json") -> str:
    """将结果格式化为 JSON 或文本。"""
    if fmt == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    # 文本格式
    lines = [f"处理时间: {result.created_at}"]
    lines.append(f"整体置信度: {result.overall_confidence():.1%}")
    lines.append("")
    for rec in result.records:
        conf_str = f"{rec.confidence:.0%}"
        flag = ""
        if rec.confidence < 0.85:
            flag = " [需核实]"
        elif rec.confidence < 0.9:
            flag = " [建议复核]"
        note = f" ({rec.note})" if rec.note else ""
        lines.append(f"  {rec.key}: {rec.value} (置信度: {conf_str}){flag}{note}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def process_input(raw: str, out_fmt: str = "json") -> str:
    """
    处理用户输入并返回格式化结果。
    若整体置信度低于0.85，抛出 E005。
    """
    records = parse_input(raw)
    result = ProcessResult()
    for rec in records:
        result.add(rec)

    overall = result.overall_confidence()
    if overall < 0.85:
        raise err_low_confidence("请人工复核关键结果，或补充更明确的信息")

    return format_output(result, out_fmt)


# ---------------------------------------------------------------------------
# 文件/URL 处理（仅本地文件，不访问网络）
# ---------------------------------------------------------------------------
def read_local_file(path: str) -> str:
    """读取本地文件内容。若路径无效抛出 E003。"""
    if not os.path.isfile(path):
        raise err_bad_format("本地文件路径无效，请提供存在的文件")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise err_bad_format(f"文件读取失败: {e}")


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------
def _selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值断言。
    """
    print("[selftest] 开始自检...")

    # --- 测试1: JSON 输入 ---
    sample_json = '{"name": "张三", "age": 30, "city": "北京"}'
    try:
        records = parse_input(sample_json)
        assert len(records) == 3, "JSON解析应产生3条记录"
        names = [r.key for r in records]
        assert "name" in names and "age" in names and "city" in names, "键名不正确"
        # 宽松断言：置信度应较高（>=0.85）
        assert all(r.confidence >= 0.85 for r in records), "JSON字段置信度应较高"
        print("  [OK] JSON 输入解析")
    except Exception as e:
        print(f"  [FAIL] JSON 输入解析: {e}")
        return 1

    # --- 测试2: key=value 输入 ---
    sample_kv = "name=李四\nage=25\ncity=上海"
    try:
        records = parse_input(sample_kv)
        assert len(records) == 3, "KV解析应产生3条记录"
        assert all(r.confidence >= 0.85 for r in records), "KV字段置信度应较高"
        print("  [OK] key=value 输入解析")
    except Exception as e:
        print(f"  [FAIL] key=value 输入解析: {e}")
        return 1

    # --- 测试3: 纯文本输入 ---
    sample_plain = "第一行内容\n第二行内容\n第三行内容"
    try:
        records = parse_input(sample_plain)
        assert len(records) == 3, "纯文本应产生3条记录"
        # 宽松断言：置信度应低于0.85（因为无结构）
        assert all(r.confidence < 0.85 for r in records), "纯文本置信度应较低"
        print("  [OK] 纯文本输入解析")
    except Exception as e:
        print(f"  [FAIL] 纯文本输入解析: {e}")
        return 1

    # --- 测试4: 空输入错误码 ---
    try:
        parse_input("")
        print("  [FAIL] 空输入应抛出 E001")
        return 1
    except MofoError as e:
        assert e.code == "E001", f"错误码应为E001，实际{e.code}"
        print("  [OK] 空输入错误码 E001")

    # --- 测试5: 完整流程 + 输出 ---
    try:
        out = process_input(sample_json, out_fmt="json")
        parsed_out = json.loads(out)
        assert "records" in parsed_out, "输出应包含records"
        assert "overall_confidence" in parsed_out, "输出应包含overall_confidence"
        # 宽松断言：整体置信度应 > 0.9
        assert parsed_out["overall_confidence"] > 0.9, "JSON输入整体置信度应较高"
        print("  [OK] 完整流程 JSON 输出")
    except Exception as e:
        print(f"  [FAIL] 完整流程 JSON 输出: {e}")
        return 1

    # --- 测试6: 文本输出 ---
    try:
        out = process_input(sample_kv, out_fmt="text")
        assert "置信度" in out, "文本输出应包含置信度"
        assert "name" in out, "文本输出应包含字段名"
        print("  [OK] 文本输出格式")
    except Exception as e:
        print(f"  [FAIL] 文本输出格式: {e}")
        return 1

    # --- 测试7: 低置信度场景（纯文本） ---
    try:
        process_input(sample_plain)
        print("  [FAIL] 纯文本应触发低置信度错误 E005")
        return 1
    except MofoError as e:
        assert e.code == "E005", f"错误码应为E005，实际{e.code}"
        print("  [OK] 低置信度错误码 E005")

    # --- 测试8: 本地文件读取（使用临时文件） ---
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(sample_kv)
            tmp_path = tf.name
        try:
            content = read_local_file(tmp_path)
            assert "name" in content, "文件内容应包含name"
            print("  [OK] 本地文件读取")
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        print(f"  [FAIL] 本地文件读取: {e}")
        return 1

    print("[selftest] 全部自检通过 ✔")
    return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="mofo - 通用数据处理与格式化工具",
        epilog="示例: python main.py --input '{\"name\": \"张三\"}' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容（字符串）")
    parser.add_argument("--file", "-f", help="输入文件路径（本地文件）")
    parser.add_argument("--format", "-o", choices=["json", "text"], default="json",
                        help="输出格式（默认 json）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    if args.selftest:
        return _selftest()

    try:
        # 获取输入内容
        if args.file:
            raw = read_local_file(args.file)
        elif args.input:
            raw = args.input
        else:
            # 尝试从 stdin 读取
            if not sys.stdin.isatty():
                raw = sys.stdin.read()
            else:
                raise err_input_empty()

        # 处理并输出
        output = process_input(raw, out_fmt=args.format)
        print(output)
        return 0

    except MofoError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 99


if __name__ == "__main__":
    sys.exit(main())
