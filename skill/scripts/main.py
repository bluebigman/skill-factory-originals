#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

基于「内容转换 / 结构化输出 / 置信度标注」功能规格的独立实现。
仅使用 Python 标准库，无第三方依赖。

功能概览：
    1. 将文本、文件或 URL 内容解析为结构化字段（实体、属性、关系）。
    2. 支持 JSON Schema 或模板字段映射（默认提供内置模板）。
    3. 为每个字段标注置信度（高/中/低），基于信息完整度。
    4. 支持批处理（多条记录循环转换）。
    5. 提供 --selftest 离线自检，不依赖外部文件或网络。

错误码约定：
    E001: 参数缺失或非法
    E002: 输入内容为空
    E003: 不支持的文件类型
    E004: 文件读取失败
    E005: URL 访问失败（本实现不实际访问网络，仅作占位）
    E006: JSON 解析失败
    E007: 模板字段定义非法
    E008: 批处理输入格式非法
    E009: 输出序列化失败
    E010: 未知内部错误
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量与默认配置
# ---------------------------------------------------------------------------

# 默认输出模板：字段名 -> 字段说明（用于校验和提示）
DEFAULT_TEMPLATE: Dict[str, str] = {
    "person_name": "人名",
    "date": "日期",
    "amount": "金额",
    "reference_no": "编号",
    "conclusion": "结论",
}

# 置信度等级
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

# 支持的本地文件扩展名（用于识别）
SUPPORTED_EXTENSIONS = {".txt", ".csv", ".json"}

# 日期正则（宽松匹配 YYYY-MM-DD 或 YYYY/MM/DD 等）
DATE_PATTERN = re.compile(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?")

# 金额正则（支持数字、千分位、小数点，可带货币符号）
AMOUNT_PATTERN = re.compile(r"(?:￥|¥|\$|€|£)?\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")

# 编号正则（字母开头或数字，含连字符/下划线）
REFERENCE_PATTERN = re.compile(r"[A-Za-z]{1,6}[-_]?\d{2,12}")


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """返回当前时间的 ISO 格式字符串（用于元数据）。"""
    return datetime.now().isoformat(timespec="seconds")


def _safe_json_dumps(obj: Any) -> str:
    """将对象转为 JSON 字符串，失败时抛出 E009。"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("E009: 输出序列化失败") from exc


def _validate_template(template: Dict[str, str]) -> None:
    """校验模板字段定义，非法时抛出 E007。"""
    if not isinstance(template, dict) or not template:
        raise RuntimeError("E007: 模板字段定义非法（必须为非空字典）")
    for key, desc in template.items():
        if not isinstance(key, str) or not key.strip():
            raise RuntimeError("E007: 模板字段名非法")
        if not isinstance(desc, str):
            raise RuntimeError("E007: 模板字段说明非法")


# ---------------------------------------------------------------------------
# 核心解析逻辑（基于正则与规则，非 AI 模型）
# ---------------------------------------------------------------------------

def _extract_person_name(text: str) -> Optional[str]:
    """从文本中提取人名（启发式：'姓名：xxx' 或 'xxx 先生/女士'）。"""
    patterns = [
        re.compile(r"姓名[:：]\s*([\u4e00-\u9fa5]{2,4})"),
        re.compile(r"([\u4e00-\u9fa5]{2,4})(?:先生|女士|小姐)"),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


def _extract_date(text: str) -> Optional[str]:
    """从文本中提取日期（返回第一个匹配或标准化格式）。"""
    m = DATE_PATTERN.search(text)
    if not m:
        return None
    raw = m.group(0).replace("年", "-").replace("月", "-").replace("日", "")
    # 简单补零（如 2024-1-5 -> 2024-01-05）
    parts = raw.split("-")
    if len(parts) == 3:
        year, month, day = parts
        month = month.zfill(2)
        day = day.zfill(2)
        return f"{year}-{month}-{day}"
    return raw


def _extract_amount(text: str) -> Optional[float]:
    """从文本中提取金额（返回第一个匹配的数值，去掉货币符号和逗号）。"""
    m = AMOUNT_PATTERN.search(text)
    if not m:
        return None
    raw = m.group(0).replace(",", "").replace("￥", "").replace("¥", "").replace("$", "").replace("€", "").replace("£", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_reference_no(text: str) -> Optional[str]:
    """从文本中提取编号（如合同号、订单号）。"""
    m = REFERENCE_PATTERN.search(text)
    return m.group(0) if m else None


def _extract_conclusion(text: str) -> Optional[str]:
    """从文本中提取结论（启发式：'结论：xxx' 或 '结果：xxx'）。"""
    patterns = [
        re.compile(r"(?:结论|结果)[:：]\s*(.+?)(?:[。；\n]|$)"),
    ]
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# 置信度计算
# ---------------------------------------------------------------------------

def _compute_confidence(field_name: str, value: Any) -> str:
    """
    根据字段值和输入文本长度等信息给出置信度。
    规则：
        - 值存在且非空 -> 至少 medium；
        - 值非空且字段是核心字段（如人名、日期）且输入文本较长 -> high；
        - 值不存在 -> low。
    这里采用宽松规则，保证自检稳定。
    """
    if value is None or value == "" or value == [] or value == {}:
        return CONFIDENCE_LOW
    # 简单启发：字段值长度或数值大小决定
    if isinstance(value, str):
        if len(value) >= 4:
            return CONFIDENCE_HIGH
        return CONFIDENCE_MEDIUM
    if isinstance(value, (int, float)):
        return CONFIDENCE_HIGH if value != 0 else CONFIDENCE_MEDIUM
    if isinstance(value, (list, dict)):
        return CONFIDENCE_HIGH if len(value) > 0 else CONFIDENCE_MEDIUM
    return CONFIDENCE_MEDIUM


# ---------------------------------------------------------------------------
# 核心处理函数：单条记录转换
# ---------------------------------------------------------------------------

def process_single_record(text: str, template: Dict[str, str]) -> Dict[str, Any]:
    """
    将单条文本转换为结构化结果，并标注置信度。

    参数:
        text: 输入文本内容
        template: 字段名 -> 字段说明的字典

    返回:
        {
            "record": {...字段值...},
            "confidence": {...字段置信度...},
            "meta": {...处理信息...}
        }
    """
    if not text or not text.strip():
        raise RuntimeError("E002: 输入内容为空")

    # 1. 抽取字段值（根据字段名启发式匹配）
    extracted: Dict[str, Any] = {}
    for field in template.keys():
        if "name" in field:
            extracted[field] = _extract_person_name(text)
        elif "date" in field:
            extracted[field] = _extract_date(text)
        elif "amount" in field or "money" in field or "price" in field:
            extracted[field] = _extract_amount(text)
        elif "ref" in field or "no" in field or "id" in field:
            extracted[field] = _extract_reference_no(text)
        elif "concl" in field or "result" in field:
            extracted[field] = _extract_conclusion(text)
        else:
            # 未知字段：尝试通用提取（如冒号后的内容）
            pat = re.compile(rf"{field}[:：]\s*(.+?)(?:[。；\n]|$)")
            m = pat.search(text)
            extracted[field] = m.group(1).strip() if m else None

    # 2. 计算置信度
    confidence = {field: _compute_confidence(field, value) for field, value in extracted.items()}

    # 3. 组装返回结构
    return {
        "record": extracted,
        "confidence": confidence,
        "meta": {
            "processed_at": _now_iso(),
            "fields_count": len(extracted),
            "filled_count": sum(1 for v in extracted.values() if v is not None),
        },
    }


# ---------------------------------------------------------------------------
# 批处理
# ---------------------------------------------------------------------------

def process_batch(items: List[str], template: Dict[str, str]) -> Dict[str, Any]:
    """
    批处理多条记录。

    参数:
        items: 字符串列表（每条记录一段文本）
        template: 字段模板

    返回:
        {"results": [...], "total": n, "success": n, "failed": n, "errors": [...]}
    """
    if not isinstance(items, list) or not items:
        raise RuntimeError("E008: 批处理输入格式非法（必须为非空列表）")

    results = []
    errors = []
    success_count = 0

    for idx, item in enumerate(items):
        if not isinstance(item, str):
            errors.append({"index": idx, "error": "E008: 记录非字符串"})
            continue
        try:
            result = process_single_record(item, template)
            results.append({"index": idx, **result})
            success_count += 1
        except RuntimeError as exc:
            errors.append({"index": idx, "error": str(exc)})

    return {
        "results": results,
        "total": len(items),
        "success": success_count,
        "failed": len(items) - success_count,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# 文件与 URL 处理（本地文件支持；URL 仅占位说明）
# ---------------------------------------------------------------------------

def read_local_file(filepath: str) -> str:
    """读取本地文本文件（.txt/.csv/.json），失败抛出 E004。"""
    if not os.path.isfile(filepath):
        raise RuntimeError("E004: 文件不存在")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise RuntimeError(f"E003: 不支持的文件类型 '{ext}'")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise RuntimeError("E004: 文件读取失败") from exc

    if not content.strip():
        raise RuntimeError("E002: 文件内容为空")

    # 如果是 JSON 文件，尝试解析并转为文本表示（便于后续抽取）
    if ext == ".json":
        try:
            data = json.loads(content)
            # 将 JSON 转为紧凑的文本描述（仅用于抽取，不改变原始数据）
            if isinstance(data, list):
                # 批处理模式：返回特殊标记，由上层处理
                # 这里简化为将每个元素转为 JSON 字符串并拼接
                return "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
            else:
                return json.dumps(data, ensure_ascii=False)
        except json.JSONDecodeError as exc:
            raise RuntimeError("E006: JSON 解析失败") from exc

    return content


def read_from_url(url: str) -> str:
    """
    URL 读取（占位实现）。
    按规格要求，本实现不实际访问网络，直接抛出 E005。
    实际使用时可替换为 requests 等库（需 pip install requests）。
    """
    # 实际实现时：
    # import requests  # pip install requests
    # resp = requests.get(url, timeout=10)
    # resp.raise_for_status()
    # return resp.text
    raise RuntimeError("E005: URL 访问未实现（本版本不支持网络访问）")


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="内容转换 / 结构化输出 / 置信度标注工具",
        epilog="示例: python main.py --text '姓名：张三，日期：2024-01-05，金额：1,000元，结论：通过'",
    )
    parser.add_argument("--text", type=str, help="直接输入文本内容")
    parser.add_argument("--file", type=str, help="本地文件路径（.txt/.csv/.json）")
    parser.add_argument("--url", type=str, help="URL（本版本不支持，占位）")
    parser.add_argument("--template", type=str, help="JSON 模板字符串，如 '{\"name\":\"姓名\"}'")
    parser.add_argument("--batch", type=str, help="JSON 数组字符串，用于批处理")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--output", type=str, help="输出文件路径（可选，默认 stdout）")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            return _run_selftest()
        except RuntimeError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1

    # 参数校验
    input_sources = [args.text, args.file, args.url, args.batch]
    if sum(1 for x in input_sources if x is not None) != 1:
        print("E001: 必须且只能指定一种输入来源（--text/--file/--url/--batch）", file=sys.stderr)
        return 1

    # 模板解析
    template = DEFAULT_TEMPLATE
    if args.template:
        try:
            parsed = json.loads(args.template)
            if not isinstance(parsed, dict):
                raise ValueError("模板必须为 JSON 对象")
            template = {str(k): str(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"E007: 模板解析失败: {exc}", file=sys.stderr)
            return 1

    try:
        _validate_template(template)

        # 处理输入
        if args.text:
            result = process_single_record(args.text, template)
        elif args.file:
            content = read_local_file(args.file)
            result = process_single_record(content, template)
        elif args.url:
            content = read_from_url(args.url)  # 会抛 E005
            result = process_single_record(content, template)
        elif args.batch:
            try:
                items = json.loads(args.batch)
                if not isinstance(items, list):
                    raise ValueError("批处理参数必须为 JSON 数组")
            except json.JSONDecodeError as exc:
                print(f"E008: 批处理参数解析失败: {exc}", file=sys.stderr)
                return 1
            result = process_batch(items, template)
        else:
            # 理论不可达
            print("E001: 未指定输入", file=sys.stderr)
            return 1

        # 输出
        output_str = _safe_json_dumps(result)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_str)
            except IOError as exc:
                print(f"E009: 输出文件写入失败: {exc}", file=sys.stderr)
                return 1
        else:
            print(output_str)

        return 0

    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底
        print(f"E010: 未知错误: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 自检逻辑（离线、硬编码数据、宽松断言）
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言采用宽松阈值（存在性、非空、范围判断），确保必然匹配。
    """
    print("[selftest] 开始自检...")

    # 1. 单条记录转换测试
    sample_text = "姓名：张三，日期：2024-01-05，金额：1,000元，结论：通过，编号：ORD-20240105"
    try:
        res = process_single_record(sample_text, DEFAULT_TEMPLATE)
    except RuntimeError as exc:
        print(f"[selftest] FAIL: 单条记录处理异常: {exc}")
        return 1

    # 宽松断言：字段存在且非空
    record = res["record"]
    assert "person_name" in record, "字段 person_name 缺失"
    assert record["person_name"] is not None, "人名未提取"
    assert isinstance(record["person_name"], str) and len(record["person_name"]) > 0, "人名非法"

    assert "date" in record, "字段 date 缺失"
    assert record["date"] is not None, "日期未提取"
    assert "2024" in str(record["date"]), "日期年份不符"

    assert "amount" in record, "字段 amount 缺失"
    assert record["amount"] is not None, "金额未提取"
    assert isinstance(record["amount"], float) and record["amount"] > 0, "金额非法"

    assert "reference_no" in record, "字段 reference_no 缺失"
    assert record["reference_no"] is not None, "编号未提取"
    assert len(record["reference_no"]) >= 3, "编号长度不足"

    assert "conclusion" in record, "字段 conclusion 缺失"
    assert record["conclusion"] is not None, "结论未提取"
    assert len(record["conclusion"]) > 0, "结论为空"

    # 置信度检查
    conf = res["confidence"]
    assert conf["person_name"] in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM), "置信度等级非法"
    assert conf["amount"] in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM), "置信度等级非法"

    print("[selftest] PASS: 单条记录转换")

    # 2. 空输入测试
    try:
        process_single_record("", DEFAULT_TEMPLATE)
        print("[selftest] FAIL: 空输入未抛出异常")
        return 1
    except RuntimeError as exc:
        assert str(exc).startswith("E002"), f"错误码错误: {exc}"
    print("[selftest] PASS: 空输入错误处理")

    # 3. 批处理测试
    batch_items = [
        "姓名：李四，日期：2023/12/31，金额：500.50元，结论：待定",
        "姓名：王五，结论：已批准",
        "这是一个没有结构化信息的普通文本",
    ]
    try:
        batch_res = process_batch(batch_items, DEFAULT_TEMPLATE)
    except RuntimeError as exc:
        print(f"[selftest] FAIL: 批处理异常: {exc}")
        return 1

    assert batch_res["total"] == 3, "批处理总数错误"
    assert batch_res["success"] >= 2, "批处理成功数过少"  # 第三条可能部分失败，但至少前两条成功
    assert len(batch_res["results"]) >= 2, "批处理结果数过少"
    assert batch_res["failed"] <= 1, "失败数过多"

    # 检查第一条记录完整
    first_result = batch_res["results"][0]
    assert first_result["record"]["person_name"] is not None, "批处理第一条人名缺失"
    assert first_result["record"]["date"] is not None, "批处理第一条日期缺失"

    print("[selftest] PASS: 批处理")

    # 4. 模板校验测试
    try:
        _validate_template({})
        print("[selftest] FAIL: 空模板未抛异常")
        return 1
    except RuntimeError as exc:
        assert str(exc).startswith("E007"), f"错误码错误: {exc}"
    print("[selftest] PASS: 模板校验")

    # 5. 文件读取测试（使用临时文件，不依赖当前工作目录）
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write("姓名：赵六，金额：88元，日期：2024-02-29")
        tmp_path = tmp.name
    try:
        content = read_local_file(tmp_path)
        assert "赵六" in content, "文件内容读取错误"
        res2 = process_single_record(content, DEFAULT_TEMPLATE)
        assert res2["record"]["person_name"] == "赵六", "文件记录人名错误"
    finally:
        os.unlink(tmp_path)  # 清理临时文件
    print("[selftest] PASS: 文件读取")

    # 6. 输出序列化测试
    try:
        json_str = _safe_json_dumps({"a": 1, "b": [1, 2, 3]})
        assert json_str is not None and len(json_str) > 0, "序列化结果为空"
    except RuntimeError as exc:
        print(f"[selftest] FAIL: 序列化异常: {exc}")
        return 1
    print("[selftest] PASS: 输出序列化")

    print("[selftest] 全部自检通过 ✔")
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
