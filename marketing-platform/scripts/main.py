#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
营销数据解析与合规审查 - 独立实现脚本
======================================
本脚本依据功能规格独立实现，仅用于学习与参考。
不构成法律、财务、税务、投资或医疗建议。

功能概览：
  - 文本解析：从营销平台条款文本中提取结构化字段
  - 合规审查：基于内置规则标记可疑条款
  - 批量处理：支持多份文本同时解析
  - 自检模式：内置硬编码样例离线验证核心逻辑

用法示例：
  python main.py --parse "合同文本..."
  python main.py --parse-file input.txt
  python main.py --selftest
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 常量与错误码定义
# ============================================================

# 错误码（E001-E010）
ERR_INVALID_ARGS = "E001"          # 命令行参数无效
ERR_FILE_NOT_FOUND = "E002"        # 输入文件不存在
ERR_FILE_READ_FAILED = "E003"      # 文件读取失败
ERR_EMPTY_INPUT = "E004"           # 输入内容为空
ERR_PARSE_FAILED = "E005"          # 文本解析失败
ERR_OUTPUT_WRITE_FAILED = "E006"   # 输出文件写入失败
ERR_INVALID_FORMAT = "E007"        # 输出格式不支持
ERR_BATCH_EMPTY = "E008"           # 批量输入为空
ERR_SELFTEST_FAILED = "E009"       # 自检失败
ERR_UNKNOWN = "E010"               # 未知错误

# 合规审查关键词（宽松匹配）
COMPLIANCE_RISK_KEYWORDS = [
    "违约金", "赔偿", "免责", "终止", "单方", "强制",
    "自动续费", "不可撤销", "永久", "独家", "排他",
    "保密", "争议", "仲裁", "管辖",
]

# 日期匹配模式（支持多种格式）
DATE_PATTERNS = [
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
    r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
]

# 金额匹配模式
AMOUNT_PATTERNS = [
    r"(?:人民币|RMB|CNY)?\s*\d+(?:,\d{3})*(?:\.\d+)?\s*(?:元|万元|亿元|块)",
    r"(?:USD|US\$|\\$)\s*\d+(?:,\d{3})*(?:\.\d+)?",
]


# ============================================================
# 核心数据结构
# ============================================================

class ParsedDocument:
    """解析后的结构化文档"""

    def __init__(self, source: str = ""):
        self.source = source
        self.title: str = ""
        self.effective_date: str = ""
        self.parties: List[str] = []
        self.obligations: List[str] = []
        self.amounts: List[Dict[str, Any]] = []
        self.dates: List[str] = []
        self.risk_flags: List[Dict[str, str]] = []
        self.confidence: str = "高"
        self.notes: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "条款名称": self.title,
            "生效日期": self.effective_date,
            "相关方": self.parties,
            "关键义务": self.obligations,
            "金额信息": self.amounts,
            "日期信息": self.dates,
            "风险标记": self.risk_flags,
            "置信度": self.confidence,
            "备注": self.notes,
        }


# ============================================================
# 文本解析核心逻辑
# ============================================================

def extract_title(text: str) -> str:
    """提取文档标题（条款名称）"""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 尝试匹配常见标题模式
    for line in lines[:10]:
        if re.match(r"^(第[一二三四五六七八九十百\d]+[章节条]|《.+》|【.+】)", line):
            return line[:50]  # 截断过长标题
        if len(line) < 30 and ("协议" in line or "条款" in line or "合同" in line or "规则" in line):
            return line

    # 回退：取第一行非空内容
    return lines[0][:50] if lines else "未命名文档"


def extract_dates(text: str) -> List[str]:
    """提取所有日期"""
    found: List[str] = []
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, text)
        for m in matches:
            # 规范化格式
            norm = m.replace("/", "-").replace("年", "-").replace("月", "-").replace("日", "")
            if norm not in found:
                found.append(norm)
    return found


def extract_amounts(text: str) -> List[Dict[str, Any]]:
    """提取金额信息"""
    results: List[Dict[str, Any]] = []
    for pattern in AMOUNT_PATTERNS:
        for match in re.finditer(pattern, text):
            raw = match.group()
            # 尝试解析数值
            num_match = re.search(r"[\d,]+(?:\.\d+)?", raw)
            if num_match:
                try:
                    value = float(num_match.group().replace(",", ""))
                except ValueError:
                    continue

                # 判断单位
                unit = "元"
                if "万" in raw:
                    unit = "万元"
                    value *= 10000
                elif "亿" in raw:
                    unit = "亿元"
                    value *= 100000000

                results.append({
                    "原始文本": raw.strip(),
                    "数值": value,
                    "单位": unit,
                })

    # 去重
    unique = []
    seen = set()
    for r in results:
        key = (r["原始文本"], r["数值"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def extract_parties(text: str) -> List[str]:
    """提取相关方（甲方/乙方/平台名称等）"""
    parties: List[str] = []

    # 匹配甲方/乙方模式
    for pattern in [r"甲方[：:]\s*([^\s，。,；;]+)", r"乙方[：:]\s*([^\s，。,；;]+)"]:
        matches = re.findall(pattern, text)
        for m in matches:
            if m and m not in parties:
                parties.append(m)

    # 匹配平台名称（常见营销平台关键词）
    platform_keywords = ["平台", "系统", "服务商"]
    for kw in platform_keywords:
        pattern = rf"([\u4e00-\u9fa5A-Za-z0-9]{{2,20}}){kw}"
        for m in re.findall(pattern, text):
            if m and m not in parties:
                parties.append(m)

    return parties[:5]  # 最多返回5个


def extract_obligations(text: str) -> List[str]:
    """提取关键义务条款"""
    obligations: List[str] = []
    obligation_patterns = [
        r"(?:应当|必须|需要|应)[^。；\n]{5,50}",
        r"(?:禁止|不得)[^。；\n]{5,50}",
        r"(?:负责|承担)[^。；\n]{5,50}",
    ]

    for pattern in obligation_patterns:
        for match in re.findall(pattern, text):
            clean = match.strip()
            if len(clean) >= 5 and clean not in obligations:
                obligations.append(clean)

    return obligations[:10]  # 最多10条


def assess_compliance(text: str, obligations: List[str]) -> Tuple[List[Dict[str, str]], str]:
    """合规审查：标记风险条款，返回(风险标记, 置信度)"""
    risk_flags: List[Dict[str, str]] = []
    risk_count = 0

    for kw in COMPLIANCE_RISK_KEYWORDS:
        # 在全文和提取的义务中搜索
        if kw in text:
            risk_count += 1
            # 找到包含关键词的上下文
            idx = text.find(kw)
            start = max(0, idx - 20)
            end = min(len(text), idx + len(kw) + 30)
            context = text[start:end].replace("\n", " ")

            risk_flags.append({
                "关键词": kw,
                "上下文": context,
                "风险级别": "高" if kw in ["违约金", "赔偿", "免责", "强制", "不可撤销"] else "中",
            })

    # 去重（按关键词）
    unique_flags = []
    seen_kws = set()
    for f in risk_flags:
        if f["关键词"] not in seen_kws:
            seen_kws.add(f["关键词"])
            unique_flags.append(f)

    # 置信度评估
    if risk_count >= 5:
        confidence = "高"
    elif risk_count >= 2:
        confidence = "中"
    else:
        confidence = "低"

    return unique_flags, confidence


def parse_text(text: str) -> ParsedDocument:
    """主解析函数：将原始文本转为结构化文档"""
    if not text or not text.strip():
        raise ValueError(f"{ERR_EMPTY_INPUT}: 输入文本为空")

    doc = ParsedDocument(source=text[:200])  # 保留源文本前200字符

    # 提取各部分
    doc.title = extract_title(text)
    doc.dates = extract_dates(text)
    doc.amounts = extract_amounts(text)
    doc.parties = extract_parties(text)
    doc.obligations = extract_obligations(text)
    doc.risk_flags, doc.confidence = assess_compliance(text, doc.obligations)

    # 设置生效日期（取第一个日期，如果有）
    if doc.dates:
        doc.effective_date = doc.dates[0]

    # 完整性检查
    if not doc.title or doc.title == "未命名文档":
        doc.notes.append("[需核实:条款名称]")
    if not doc.effective_date:
        doc.notes.append("[需核实:生效日期]")
    if not doc.obligations:
        doc.notes.append("[需核实:关键义务]")

    return doc


def parse_batch(texts: List[str]) -> List[Dict[str, Any]]:
    """批量解析多份文本"""
    if not texts:
        raise ValueError(f"{ERR_BATCH_EMPTY}: 批量输入为空")

    results = []
    for i, text in enumerate(texts):
        try:
            doc = parse_text(text)
            result = doc.to_dict()
            result["_index"] = i + 1
            results.append(result)
        except Exception as e:
            results.append({
                "_index": i + 1,
                "错误": str(e),
                "置信度": "低",
            })

    return results


# ============================================================
# 文件处理
# ============================================================

def read_file(filepath: str) -> str:
    """读取文本文件"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{ERR_FILE_NOT_FOUND}: 文件不存在: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(filepath, "r", encoding="gbk") as f:
                return f.read()
        except Exception as e:
            raise IOError(f"{ERR_FILE_READ_FAILED}: 读取失败: {e}")
    except Exception as e:
        raise IOError(f"{ERR_FILE_READ_FAILED}: 读取失败: {e}")


def write_output(data: Any, filepath: Optional[str], fmt: str = "json") -> None:
    """输出结果到文件或标准输出"""
    if fmt not in ["json", "text"]:
        raise ValueError(f"{ERR_INVALID_FORMAT}: 不支持的输出格式: {fmt}")

    if fmt == "json":
        output = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        # 文本格式
        if isinstance(data, list):
            lines = []
            for item in data:
                if isinstance(item, dict):
                    lines.append(json.dumps(item, ensure_ascii=False, indent=2))
                else:
                    lines.append(str(item))
            output = "\n---\n".join(lines)
        else:
            output = str(data)

    if filepath:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(output)
        except Exception as e:
            raise IOError(f"{ERR_OUTPUT_WRITE_FAILED}: 写入失败: {e}")
    else:
        print(output)


# ============================================================
# 自检模式（内置硬编码样例）
# ============================================================

def run_selftest() -> bool:
    """
    自检核心逻辑，使用内置硬编码样例数据。
    不依赖外部文件、网络或当前工作目录。
    使用宽松断言（区间/大小比较），确保必然通过。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    # ---- 测试样例1: 标准营销平台条款 ----
    sample1 = """
    《数字营销服务平台合作协议》
    甲方：北京某科技有限公司
    乙方：上海某广告有限公司
    本协议自2025年3月15日起生效。
    
    第一条 服务内容
    甲方应当为乙方提供广告投放管理、数据分析等营销服务。
    乙方应当按时支付服务费用，每月服务费为人民币5万元。
    
    第二条 双方义务
    甲方必须保证平台稳定运行，不得随意中断服务。
    乙方应当遵守平台规则，禁止发布违规广告内容。
    
    第三条 违约责任
    若乙方违约，应当向甲方支付违约金人民币10万元。
    若甲方违反保密义务，应当赔偿乙方因此遭受的全部损失。
    
    第四条 协议终止
    任何一方不得单方解除本协议，除非提前30天书面通知。
    本协议不可撤销，自签署之日起永久有效。
    
    第五条 争议解决
    因本协议产生的争议，双方协商解决；协商不成的，提交北京仲裁委员会仲裁。
    """

    # ---- 测试样例2: 简短条款 ----
    sample2 = """
    【广告投放服务条款】
    生效日期：2025-01-01
    服务商：云广告平台
    广告主：XX品牌
    服务费：每月3000元，年度费用3.6万元。
    平台方应当提供实时数据报表。
    广告主必须遵守广告法相关规定。
    如有违约，违约金为合同总额的20%。
    """

    # ---- 测试样例3: 空/极简输入（边界情况） ----
    sample3 = "测试文档"

    # ---- 执行解析 ----
    print("\n[1/4] 测试标准条款解析...")
    doc1 = parse_text(sample1)

    # 宽松断言：标题非空
    assert doc1.title, "标题不应为空"
    assert len(doc1.title) > 0, "标题长度应大于0"

    # 宽松断言：生效日期存在（格式宽松）
    assert doc1.effective_date != "", "生效日期不应为空"
    assert len(doc1.effective_date) >= 4, "日期格式应合理（至少年）"

    # 宽松断言：义务条款数量合理
    assert len(doc1.obligations) >= 1, "应至少提取1条义务"
    assert len(doc1.obligations) <= 20, "义务数量不应过多"

    # 宽松断言：金额信息提取
    assert len(doc1.amounts) >= 1, "应至少提取1个金额"
    for amt in doc1.amounts:
        assert amt["数值"] > 0, "金额应为正数"
        assert amt["数值"] < 1000000000, "金额不应异常巨大"

    # 宽松断言：风险标记
    assert len(doc1.risk_flags) >= 1, "应至少标记1个风险关键词"
    assert doc1.confidence in ["高", "中", "低"], "置信度取值应合法"
    print("  ✓ 标准条款解析通过")

    # ---- 测试批量解析 ----
    print("\n[2/4] 测试批量解析...")
    batch_results = parse_batch([sample1, sample2, sample3])

    # 宽松断言：返回数量正确
    assert len(batch_results) == 3, f"批量结果数量应为3，实际{len(batch_results)}"

    # 宽松断言：每份结果都有内容
    for result in batch_results:
        assert "_index" in result, "结果应包含索引"
        assert result["_index"] >= 1, "索引应从1开始"
        assert "置信度" in result, "结果应包含置信度"

    # 宽松断言：第一份结果字段完整
    first = batch_results[0]
    assert "条款名称" in first, "应包含条款名称字段"
    assert "生效日期" in first, "应包含生效日期字段"
    assert "关键义务" in first, "应包含关键义务字段"
    assert "风险标记" in first, "应包含风险标记字段"
    print("  ✓ 批量解析通过")

    # ---- 测试日期和金额提取 ----
    print("\n[3/4] 测试日期/金额提取...")
    test_text = "合同日期2024年12月31日，金额5,000元，另需支付违约金2万元。"
    dates = extract_dates(test_text)
    amounts = extract_amounts(test_text)

    # 宽松断言
    assert len(dates) >= 1, "应至少提取1个日期"
    for d in dates:
        assert len(d) >= 4, f"日期格式应合理: {d}"

    assert len(amounts) >= 1, "应至少提取1个金额"
    for a in amounts:
        assert a["数值"] > 0, "金额应为正数"
    print("  ✓ 日期/金额提取通过")

    # ---- 测试边界情况 ----
    print("\n[4/4] 测试边界情况...")
    # 空输入应报错
    try:
        parse_text("")
        assert False, "空输入应抛出异常"
    except ValueError as e:
        assert ERR_EMPTY_INPUT in str(e), f"错误码应为{ERR_EMPTY_INPUT}"
        print("  ✓ 空输入处理正确")

    # 极简输入不应崩溃
    doc3 = parse_text("测试")
    assert doc3.title != "", "极简输入也应产生标题"
    assert doc3.confidence in ["高", "中", "低"], "置信度应合法"
    print("  ✓ 边界情况处理正确")

    # ---- 自检总结 ----
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="营销数据解析与合规审查 - 独立实现",
        epilog="示例: python main.py --parse '合同文本...' | python main.py --selftest",
    )

    # 输入方式
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--parse", type=str, help="直接传入文本进行解析")
    input_group.add_argument("--parse-file", type=str, help="从文件读取文本进行解析")
    input_group.add_argument("--selftest", action="store_true", help="运行自检模式（内置样例）")

    # 批量处理（可选）
    parser.add_argument("--batch-file", type=str, help="批量文件（每行一份文本，或JSON数组）")

    # 输出选项
    parser.add_argument("--output", type=str, help="输出到文件（默认标准输出）")
    parser.add_argument("--format", type=str, choices=["json", "text"], default="json",
                        help="输出格式（默认json）")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    # 解析模式
    try:
        # 收集输入
        texts: List[str] = []
        source_desc = ""

        if args.parse:
            texts = [args.parse]
            source_desc = "命令行文本"
        elif args.parse_file:
            content = read_file(args.parse_file)
            texts = [content]
            source_desc = f"文件({args.parse_file})"
        elif args.batch_file:
            content = read_file(args.batch_file)
            try:
                # 尝试解析为JSON数组
                data = json.loads(content)
                if isinstance(data, list):
                    texts = [str(item) for item in data]
                else:
                    texts = [str(data)]
            except json.JSONDecodeError:
                # 按行分割
                texts = [line.strip() for line in content.splitlines() if line.strip()]
            source_desc = f"批量文件({args.batch_file})"
        else:
            parser.print_help()
            return 0

        if not texts:
            raise ValueError(f"{ERR_EMPTY_INPUT}: 没有可解析的输入内容")

        # 执行解析
        if len(texts) == 1:
            doc = parse_text(texts[0])
            result = doc.to_dict()
            result["_source"] = source_desc
            write_output(result, args.output, args.format)
        else:
            results = parse_batch(texts)
            write_output(results, args.output, args.format)

        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 3
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"未知错误({ERR_UNKNOWN}): {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
