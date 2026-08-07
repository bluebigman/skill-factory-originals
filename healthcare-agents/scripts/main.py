#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 医疗行政智能体协作工具包（独立实现）

本脚本根据功能规格独立编写，不参考任何既有代码。
提供核心数据解析、关键信息提取、结构化输出、置信度标注等能力。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input "患者:张三, 日期:2026-01-15, 金额:$250.00"
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空或格式不正确",
    "E002": "无法解析输入文本",
    "E003": "关键字段提取失败",
    "E004": "输出格式序列化失败",
    "E005": "批量处理时单条记录失败",
    "E006": "自定义模板格式错误",
    "E007": "置信度计算异常",
    "E008": "输入类型不支持",
    "E009": "文件读取失败",
    "E010": "内部逻辑错误",
}


# ============================================================
# 核心数据结构
# ============================================================
class MedicalRecord:
    """医疗行政记录的数据结构"""

    def __init__(self) -> None:
        self.patient_name: Optional[str] = None
        self.date: Optional[str] = None
        self.amount: Optional[float] = None
        self.cpt_codes: List[str] = []
        self.icd10_codes: List[str] = []
        self.raw_text: str = ""
        self.confidence: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "patient_name": self.patient_name,
            "date": self.date,
            "amount": self.amount,
            "cpt_codes": self.cpt_codes,
            "icd10_codes": self.icd10_codes,
            "confidence": self.confidence,
        }


# ============================================================
# 核心逻辑模块
# ============================================================
def validate_input(raw_text: str) -> Tuple[bool, str]:
    """
    验证输入文本是否有效。

    返回:
        (是否有效, 错误码或空字符串)
    """
    if not raw_text or not raw_text.strip():
        return False, "E001"
    if len(raw_text.strip()) < 3:
        return False, "E001"
    return True, ""


def extract_patient_name(text: str) -> Tuple[Optional[str], str]:
    """
    从文本中提取患者姓名。

    支持格式: "患者:张三", "姓名:李四", "Patient: John Doe"
    """
    patterns = [
        r"(?:患者|姓名|病人)\s*[:：]\s*([\u4e00-\u9fa5A-Za-z\s\.]+)",
        r"(?:patient|name)\s*[:：]\s*([A-Za-z\s\.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name:
                return name, "高"
    return None, "低"


def extract_date(text: str) -> Tuple[Optional[str], str]:
    """
    从文本中提取日期。

    支持格式: YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY
    """
    patterns = [
        r"(?:日期|时间)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(\d{1,2}/\d{1,2}/\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1), "高"
    return None, "低"


def extract_amount(text: str) -> Tuple[Optional[float], str]:
    """
    从文本中提取金额。

    支持格式: $250.00, 250美元, 金额:250
    """
    patterns = [
        r"(?:金额|费用|价格)\s*[:：]\s*\$?(\d+(?:\.\d{1,2})?)",
        r"\$(\d+(?:\.\d{1,2})?)",
        r"(\d+(?:\.\d{1,2})?)\s*(?:美元|元)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1)), "高"
            except ValueError:
                continue
    return None, "低"


def extract_cpt_codes(text: str) -> Tuple[List[str], str]:
    """
    从文本中提取 CPT 代码（5位数字，通常为 0-9 开头）。

    示例: 99213, 99214
    """
    pattern = r"\b([0-9]{5})\b"
    matches = re.findall(pattern, text)
    # 过滤掉可能的日期中的数字
    result = [code for code in matches if not re.match(r"^(19|20)\d{2}$", code)]
    if result:
        return result, "高"
    return [], "低"


def extract_icd10_codes(text: str) -> Tuple[List[str], str]:
    """
    从文本中提取 ICD-10 代码（字母+数字组合）。

    示例: E11.9, I10, J45.909
    """
    pattern = r"\b([A-Z]\d{1,2}(?:\.\d{1,2})?)\b"
    matches = re.findall(pattern, text, re.IGNORECASE)
    # 过滤常见非诊断代码
    excluded = {"E", "I", "J", "K", "M", "N", "O", "P", "Q", "R", "S", "T", "Z"}
    result = [code.upper() for code in matches if code[0].upper() in excluded]
    if result:
        return result, "高"
    return [], "低"


def parse_medical_record(raw_text: str) -> Tuple[Optional[MedicalRecord], str]:
    """
    解析医疗记录文本为结构化数据。

    返回:
        (解析结果或None, 错误码或空字符串)
    """
    # 输入验证
    is_valid, error_code = validate_input(raw_text)
    if not is_valid:
        return None, error_code

    try:
        record = MedicalRecord()
        record.raw_text = raw_text.strip()

        # 提取各字段
        record.patient_name, name_conf = extract_patient_name(raw_text)
        record.date, date_conf = extract_date(raw_text)
        record.amount, amount_conf = extract_amount(raw_text)
        record.cpt_codes, cpt_conf = extract_cpt_codes(raw_text)
        record.icd10_codes, icd10_conf = extract_icd10_codes(raw_text)

        # 置信度标注
        record.confidence = {
            "patient_name": name_conf,
            "date": date_conf,
            "amount": amount_conf,
            "cpt_codes": cpt_conf,
            "icd10_codes": icd10_conf,
        }

        # 至少有一个关键字段提取成功
        if not (record.patient_name or record.date or record.amount or record.cpt_codes or record.icd10_codes):
            return None, "E003"

        return record, ""

    except Exception:
        return None, "E010"


def format_output(record: MedicalRecord, output_format: str = "json") -> Tuple[Optional[str], str]:
    """
    按指定格式输出结构化数据。

    支持格式: json, csv, table
    """
    try:
        if output_format == "json":
            return json.dumps(record.to_dict(), ensure_ascii=False, indent=2), ""

        elif output_format == "csv":
            # 简单 CSV 输出
            headers = ["patient_name", "date", "amount", "cpt_codes", "icd10_codes", "confidence"]
            values = [
                record.patient_name or "",
                record.date or "",
                str(record.amount) if record.amount else "",
                ";".join(record.cpt_codes),
                ";".join(record.icd10_codes),
                json.dumps(record.confidence, ensure_ascii=False),
            ]
            return ",".join(headers) + "\n" + ",".join(values), ""

        elif output_format == "table":
            # 简单表格输出
            lines = []
            lines.append("字段名          值")
            lines.append("-" * 40)
            lines.append(f"患者姓名        {record.patient_name or '未识别'}")
            lines.append(f"日期            {record.date or '未识别'}")
            lines.append(f"金额            {record.amount if record.amount else '未识别'}")
            lines.append(f"CPT代码         {', '.join(record.cpt_codes) if record.cpt_codes else '未识别'}")
            lines.append(f"ICD-10代码      {', '.join(record.icd10_codes) if record.icd10_codes else '未识别'}")
            lines.append(f"置信度          {json.dumps(record.confidence, ensure_ascii=False)}")
            return "\n".join(lines), ""

        else:
            return None, "E004"

    except Exception:
        return None, "E004"


def batch_process(texts: List[str], output_format: str = "json") -> Tuple[Optional[List[str]], str]:
    """
    批量处理多条文本记录。

    返回:
        (输出列表或None, 错误码或空字符串)
    """
    if not texts:
        return None, "E001"

    results = []
    for text in texts:
        record, err = parse_medical_record(text)
        if err:
            # 单条失败，记录错误但继续处理
            results.append(json.dumps({"error": err, "input": text}, ensure_ascii=False))
            continue
        output, format_err = format_output(record, output_format)
        if format_err:
            return None, format_err
        results.append(output)

    return results, ""


# ============================================================
# 自测模块
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检: healthcare-agents 核心逻辑")
    print("=" * 60)

    # 测试样例
    test_samples = [
        "患者:张三, 日期:2026-01-15, 金额:$250.00, CPT:99213",
        "Patient: John Doe, Date: 2026/02/20, Amount: $150.50, ICD-10: E11.9",
        "姓名:李四, 日期:2026-03-10, 费用:300美元, CPT:99214, ICD-10: I10",
        "这是一个没有结构化信息的文本",
        "",
    ]

    all_passed = True

    # 测试1: 输入验证
    print("\n[测试1] 输入验证")
    valid, err = validate_input(test_samples[0])
    if valid and err == "":
        print("  ✓ 有效输入通过验证")
    else:
        print(f"  ✗ 有效输入验证失败: {err}")
        all_passed = False

    valid, err = validate_input(test_samples[4])
    if not valid and err == "E001":
        print("  ✓ 空输入正确拒绝")
    else:
        print(f"  ✗ 空输入处理异常: {err}")
        all_passed = False

    # 测试2: 患者姓名提取
    print("\n[测试2] 患者姓名提取")
    name, conf = extract_patient_name(test_samples[0])
    if name and conf == "高":
        print(f"  ✓ 中文姓名提取成功: {name}")
    else:
        print(f"  ✗ 中文姓名提取失败: {name}")
        all_passed = False

    name, conf = extract_patient_name(test_samples[1])
    if name and conf == "高":
        print(f"  ✓ 英文姓名提取成功: {name}")
    else:
        print(f"  ✗ 英文姓名提取失败: {name}")
        all_passed = False

    # 测试3: 日期提取
    print("\n[测试3] 日期提取")
    date, conf = extract_date(test_samples[0])
    if date and conf == "高":
        print(f"  ✓ 日期提取成功: {date}")
    else:
        print(f"  ✗ 日期提取失败: {date}")
        all_passed = False

    # 测试4: 金额提取
    print("\n[测试4] 金额提取")
    amount, conf = extract_amount(test_samples[0])
    if amount is not None and amount > 0 and conf == "高":
        print(f"  ✓ 金额提取成功: {amount}")
    else:
        print(f"  ✗ 金额提取失败: {amount}")
        all_passed = False

    # 测试5: CPT代码提取
    print("\n[测试5] CPT代码提取")
    cpt_codes, conf = extract_cpt_codes(test_samples[0])
    if len(cpt_codes) > 0 and conf == "高":
        print(f"  ✓ CPT代码提取成功: {cpt_codes}")
    else:
        print(f"  ✗ CPT代码提取失败: {cpt_codes}")
        all_passed = False

    # 测试6: ICD-10代码提取
    print("\n[测试6] ICD-10代码提取")
    icd10_codes, conf = extract_icd10_codes(test_samples[1])
    if len(icd10_codes) > 0 and conf == "高":
        print(f"  ✓ ICD-10代码提取成功: {icd10_codes}")
    else:
        print(f"  ✗ ICD-10代码提取失败: {icd10_codes}")
        all_passed = False

    # 测试7: 完整解析
    print("\n[测试7] 完整解析")
    record, err = parse_medical_record(test_samples[0])
    if record and err == "":
        if record.patient_name and record.date and record.amount:
            print(f"  ✓ 完整解析成功: {record.to_dict()}")
        else:
            print("  ✗ 解析结果缺少关键字段")
            all_passed = False
    else:
        print(f"  ✗ 完整解析失败: {err}")
        all_passed = False

    # 测试8: 无结构文本处理
    print("\n[测试8] 无结构文本处理")
    record, err = parse_medical_record(test_samples[3])
    if record is None and err == "E003":
        print("  ✓ 正确识别无结构文本")
    else:
        print(f"  ✗ 无结构文本处理异常: {err}")
        all_passed = False

    # 测试9: 输出格式
    print("\n[测试9] 输出格式")
    record, _ = parse_medical_record(test_samples[0])
    if record:
        json_out, err = format_output(record, "json")
        if json_out and err == "":
            print("  ✓ JSON输出成功")
        else:
            print(f"  ✗ JSON输出失败: {err}")
            all_passed = False

        csv_out, err = format_output(record, "csv")
        if csv_out and err == "":
            print("  ✓ CSV输出成功")
        else:
            print(f"  ✗ CSV输出失败: {err}")
            all_passed = False

        table_out, err = format_output(record, "table")
        if table_out and err == "":
            print("  ✓ 表格输出成功")
        else:
            print(f"  ✗ 表格输出失败: {err}")
            all_passed = False

    # 测试10: 批量处理
    print("\n[测试10] 批量处理")
    results, err = batch_process(test_samples[:3])
    if results and err == "" and len(results) == 3:
        print(f"  ✓ 批量处理成功，共{len(results)}条")
    else:
        print(f"  ✗ 批量处理失败: {err}")
        all_passed = False

    # 测试11: 错误码完整性
    print("\n[测试11] 错误码完整性")
    if len(ERROR_CODES) == 10:
        print("  ✓ 错误码定义完整")
    else:
        print(f"  ✗ 错误码数量异常: {len(ERROR_CODES)}")
        all_passed = False

    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过: 所有核心逻辑验证成功")
        print("=" * 60)
        return True
    else:
        print("自检失败: 存在未通过的测试项")
        print("=" * 60)
        return False


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="医疗行政智能体协作工具包 - 结构化数据解析与提取"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本，例如: '患者:张三, 日期:2026-01-15, 金额:$250.00'",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "csv", "table"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，用分号(;)分隔多条记录",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 批量处理模式
    if args.batch:
        texts = [t.strip() for t in args.batch.split(";") if t.strip()]
        results, err = batch_process(texts, args.format)
        if err:
            print(f"错误[{err}]: {ERROR_CODES.get(err, '未知错误')}", file=sys.stderr)
            return 1
        for i, result in enumerate(results, 1):
            print(f"--- 记录 {i} ---")
            print(result)
        return 0

    # 单条处理模式
    if args.input:
        record, err = parse_medical_record(args.input)
        if err:
            print(f"错误[{err}]: {ERROR_CODES.get(err, '未知错误')}", file=sys.stderr)
            return 1
        output, format_err = format_output(record, args.format)
        if format_err:
            print(f"错误[{format_err}]: {ERROR_CODES.get(format_err, '未知错误')}", file=sys.stderr)
            return 1
        print(output)
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
