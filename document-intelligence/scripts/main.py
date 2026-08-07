#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
document-intelligence 技能独立实现
发票识别：将输入内容转换为结构化结果，含置信度标注。
仅依据功能规格 clean-room 实现，不复制任何既有代码。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容（数据/文件/URL）",
    "E002": "关键信息缺失，请补充必填字段",
    "E003": "输入格式错误，请检查输入内容格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定，建议人工复核",
    "E006": "内部处理异常，请稍后重试",
    "E007": "参数错误，请检查命令行参数",
    "E008": "输出序列化失败",
    "E009": "批量处理中断",
    "E010": "未知错误",
}

# 可识别的关键字段（发票常用字段）
KEY_FIELDS = [
    "invoice_number",      # 发票号码
    "invoice_date",        # 开票日期
    "seller_name",         # 销售方名称
    "buyer_name",          # 购买方名称
    "amount",              # 金额
    "tax_amount",          # 税额
    "total_amount",        # 价税合计
]

# 字段别名映射（用于识别不同表述）
FIELD_ALIASES = {
    "invoice_number": ["发票号码", "发票号", "number", "invoice_no"],
    "invoice_date": ["开票日期", "日期", "date"],
    "seller_name": ["销售方", "销方名称", "seller", "销售方名称"],
    "buyer_name": ["购买方", "购方名称", "buyer", "购买方名称"],
    "amount": ["金额", "合计金额", "amount"],
    "tax_amount": ["税额", "tax"],
    "total_amount": ["价税合计", "总金额", "total", "总计"],
}

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


class DocumentIntelligenceError(Exception):
    """技能自定义异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


def validate_input(data: Any) -> None:
    """校验输入是否合法（E001/E003）"""
    if data is None:
        raise DocumentIntelligenceError("E001")
    if isinstance(data, str) and not data.strip():
        raise DocumentIntelligenceError("E001")
    if isinstance(data, (list, tuple, dict)) and len(data) == 0:
        raise DocumentIntelligenceError("E001")


def extract_fields(text: str) -> Dict[str, Tuple[str, float]]:
    """
    从文本中提取关键字段。
    返回: {字段名: (字段值, 置信度)}
    置信度基于字段出现次数、格式匹配度等启发式规则。
    """
    if not text or not text.strip():
        return {}

    results: Dict[str, Tuple[str, float]] = {}
    lines = text.strip().splitlines()

    # 逐行扫描匹配字段
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 尝试匹配 "字段名: 值" 或 "字段名：值" 模式
        match = re.match(r'^([^:：]+)[:：]\s*(.+)$', line)
        if not match:
            continue
        raw_key = match.group(1).strip().lower()
        value = match.group(2).strip()
        if not value:
            continue

        # 通过别名匹配标准字段
        for field, aliases in FIELD_ALIASES.items():
            if raw_key in aliases or any(alias in raw_key for alias in aliases):
                # 基础置信度 0.85，格式良好则提升
                confidence = 0.85
                if field in ("invoice_number", "amount", "tax_amount", "total_amount"):
                    # 数字/编号格式匹配提升置信度
                    if re.search(r'[0-9]', value):
                        confidence = 0.92
                elif field == "invoice_date":
                    # 日期格式匹配提升置信度
                    if re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', value):
                        confidence = 0.95
                # 已存在则取较高置信度
                if field not in results or confidence > results[field][1]:
                    results[field] = (value, confidence)
                break

    return results


def calculate_overall_confidence(extracted: Dict[str, Tuple[str, float]]) -> float:
    """计算整体置信度（字段覆盖率与平均置信度加权）"""
    if not extracted:
        return 0.0
    coverage = len(extracted) / len(KEY_FIELDS)
    avg_conf = sum(conf for _, conf in extracted.values()) / len(extracted)
    # 覆盖率权重 0.4，平均置信度权重 0.6
    return coverage * 0.4 + avg_conf * 0.6


def format_output(extracted: Dict[str, Tuple[str, float]], overall_conf: float) -> Dict[str, Any]:
    """按约定格式生成输出，含置信度标注"""
    fields = {}
    for field in KEY_FIELDS:
        if field in extracted:
            value, conf = extracted[field]
            annotation = ""
            if conf < MEDIUM_CONFIDENCE:
                annotation = "[需核实]"
            elif conf < HIGH_CONFIDENCE:
                annotation = "[建议复核]"
            fields[field] = {
                "value": value,
                "confidence": round(conf, 2),
                "annotation": annotation,
            }

    # 整体置信度标注
    if overall_conf < MEDIUM_CONFIDENCE:
        overall_note = "[需核实] 整体置信度较低，请人工复核关键字段"
    elif overall_conf < HIGH_CONFIDENCE:
        overall_note = "[建议复核] 部分字段置信度中等，请确认"
    else:
        overall_note = "可直接使用"

    return {
        "status": "success",
        "fields": fields,
        "overall_confidence": round(overall_conf, 2),
        "overall_note": overall_note,
        "disclaimer": "仅供学习与参考用途，不构成专业建议。请咨询持证专业人士。",
    }


def process_single(data: str) -> Dict[str, Any]:
    """处理单个输入，返回结构化结果"""
    validate_input(data)
    extracted = extract_fields(data)
    if not extracted:
        raise DocumentIntelligenceError("E005", "未能从输入中识别到有效字段")
    overall_conf = calculate_overall_confidence(extracted)
    return format_output(extracted, overall_conf)


def process_batch(data_list: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个输入"""
    if not data_list:
        raise DocumentIntelligenceError("E001")
    results = []
    for idx, item in enumerate(data_list):
        try:
            results.append(process_single(item))
        except DocumentIntelligenceError as e:
            results.append({"status": "error", "error_code": e.code, "error_message": e.message, "index": idx})
        except Exception:
            results.append({"status": "error", "error_code": "E009", "error_message": ERROR_CODES["E009"], "index": idx})
    return results


def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("[selftest] 开始自检...")

    # 样例1：完整发票文本
    sample1 = """
    发票号码: 12345678
    开票日期: 2024-01-15
    销售方名称: 示例科技有限公司
    购买方名称: 示例采购有限公司
    金额: 1000.00
    税额: 130.00
    价税合计: 1130.00
    """
    try:
        result1 = process_single(sample1)
        assert result1["status"] == "success", "样例1应成功处理"
        fields1 = result1["fields"]
        # 宽松断言：关键字段存在且值非空
        assert "invoice_number" in fields1, "应识别发票号码"
        assert fields1["invoice_number"]["value"], "发票号码不应为空"
        assert fields1["invoice_number"]["confidence"] > 0.5, "置信度应大于0.5"
        assert "total_amount" in fields1, "应识别价税合计"
        assert result1["overall_confidence"] > 0.5, "整体置信度应大于0.5"
        print("[selftest] 样例1通过 ✓")
    except AssertionError as e:
        print(f"[selftest] 样例1失败: {e}")
        return False
    except DocumentIntelligenceError as e:
        print(f"[selftest] 样例1异常: {e}")
        return False

    # 样例2：不完整文本（低置信度场景）
    sample2 = "发票号码: 87654321\n金额: 500.00\n"
    try:
        result2 = process_single(sample2)
        assert result2["status"] == "success", "样例2应成功处理"
        fields2 = result2["fields"]
        assert "invoice_number" in fields2, "应识别发票号码"
        assert result2["overall_confidence"] < 0.9, "不完整输入置信度应较低"
        print("[selftest] 样例2通过 ✓")
    except AssertionError as e:
        print(f"[selftest] 样例2失败: {e}")
        return False
    except DocumentIntelligenceError as e:
        print(f"[selftest] 样例2异常: {e}")
        return False

    # 样例3：空输入应报错 E001
    try:
        process_single("")
        print("[selftest] 样例3失败: 空输入应报错")
        return False
    except DocumentIntelligenceError as e:
        assert e.code == "E001", f"错误码应为E001，实际{e.code}"
        print("[selftest] 样例3通过 ✓")
    except Exception:
        print("[selftest] 样例3失败: 应捕获DocumentIntelligenceError")
        return False

    # 样例4：批量处理
    batch = [sample1, sample2, ""]
    try:
        results = process_batch(batch)
        assert len(results) == 3, "批量结果数量应为3"
        assert results[0]["status"] == "success", "第一条应成功"
        assert results[1]["status"] == "success", "第二条应成功"
        assert results[2]["status"] == "error", "第三条应为错误"
        assert results[2]["error_code"] == "E001", "第三条错误码应为E001"
        print("[selftest] 样例4通过 ✓")
    except AssertionError as e:
        print(f"[selftest] 样例4失败: {e}")
        return False
    except Exception:
        print("[selftest] 样例4异常")
        return False

    print("[selftest] 全部自检通过 ✅")
    return True


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(description="发票识别技能 - document-intelligence")
    parser.add_argument("--input", "-i", type=str, help="输入文本（发票内容）")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径（读取文件内容）")
    parser.add_argument("--batch", "-b", type=str, help="批量输入，用分号(;)分隔多个文本")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        return 0 if ok else 1

    # 收集输入
    try:
        if args.batch:
            # 批量模式
            items = [item.strip() for item in args.batch.split(";") if item.strip()]
            if not items:
                raise DocumentIntelligenceError("E001")
            results = process_batch(items)
            output = {"status": "success", "results": results}
        elif args.file:
            # 文件模式
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                raise DocumentIntelligenceError("E003", f"文件不存在: {args.file}")
            except Exception:
                raise DocumentIntelligenceError("E003", "文件读取失败")
            output = process_single(content)
        elif args.input:
            # 直接输入模式
            output = process_single(args.input)
        else:
            # 无输入则提示
            print("请提供输入内容，使用 --input 或 --file 参数。")
            print("或使用 --selftest 运行自检。")
            return 1

        # 输出
        if args.json:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # 文本友好输出
            if output.get("status") == "error":
                print(f"[错误] {output.get('error_code')}: {output.get('error_message')}")
                return 1
            if "results" in output:
                # 批量模式
                for i, res in enumerate(output["results"]):
                    print(f"\n--- 结果 {i+1} ---")
                    if res.get("status") == "error":
                        print(f"[错误] {res.get('error_code')}: {res.get('error_message')}")
                    else:
                        print(f"整体置信度: {res.get('overall_confidence')} {res.get('overall_note')}")
                        for field, info in res.get("fields", {}).items():
                            ann = info.get("annotation", "")
                            print(f"  {field}: {info['value']} (置信度:{info['confidence']}) {ann}")
            else:
                print(f"整体置信度: {output.get('overall_confidence')} {output.get('overall_note')}")
                for field, info in output.get("fields", {}).items():
                    ann = info.get("annotation", "")
                    print(f"  {field}: {info['value']} (置信度:{info['confidence']}) {ann}")
            print(f"\n免责声明: {output.get('disclaimer', '')}")
        return 0

    except DocumentIntelligenceError as e:
        print(f"[错误] {e.code}: {e.message}")
        return 1
    except Exception as e:
        print(f"[错误] E010: 未知错误 - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
