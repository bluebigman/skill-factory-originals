#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同审查风险清单核查工具
功能：对合同文本进行违约、付款、保密、知识产权归属四类风险点审查，
      输出带风险等级和条款原文摘录的核查清单。
支持：纯文本(.txt)和Word(.docx)格式，单文件或多文件批量审查。
输出：JSON（默认）或 Markdown 格式。
"""

import argparse
import json
import re
import sys
import os
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

# 尝试导入 python-docx，失败时给出提示
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# ============================================================
# 风险规则定义
# ============================================================

RISK_RULES: Dict[str, Dict[str, Any]] = {
    "违约": {
        "high_risk": [
            (r"违约金[^。；;]*?\d+%", "违约金比例过高，建议协商调整至合理范围（通常不超过30%）"),
            (r"赔偿[^。；;]*?全部损失", "赔偿范围过大，建议限定为直接损失"),
            (r"承担[^。；;]*?一切责任", "责任范围过于宽泛，建议明确具体责任类型"),
        ],
        "medium_risk": [
            (r"违约金[^。；;]*?\d+", "违约金金额需核实是否合理，建议明确计算方式"),
            (r"赔偿损失", "赔偿范围不够明确，建议明确赔偿范围和计算标准"),
        ],
        "low_risk": [
            (r"违约责任", "违约责任条款存在，建议补充具体违约情形和后果"),
        ],
    },
    "付款": {
        "high_risk": [
            (r"付款[^。；;]*?后[^。；;]*?交货", "先付款后交货风险高，建议改为货到验收后付款"),
            (r"先付款[^。；;]*?后[^。；;]*?验收", "先付款后验收风险高，建议增加验收合格后付款条款"),
            (r"一次性[^。；;]*?付款", "一次性付款风险高，建议分期付款并绑定履约节点"),
        ],
        "medium_risk": [
            (r"付款期限", "付款期限需明确具体日期或条件，避免模糊表述"),
            (r"付款条件", "付款条件需明确，建议列出所有前置条件"),
        ],
        "low_risk": [
            (r"付款方式", "付款方式需明确，建议补充逾期付款违约责任"),
        ],
    },
    "保密": {
        "high_risk": [
            (r"保密[^。；;]*?无限期", "无限期保密不合理，建议设定合理保密期限"),
            (r"保密[^。；;]*?永久", "永久保密不合理，建议设定合理保密期限"),
        ],
        "medium_risk": [
            (r"保密期限", "保密期限需明确，建议设定具体年限"),
            (r"保密范围", "保密范围需明确，建议列出具体保密信息类型"),
        ],
        "low_risk": [
            (r"保密协议", "保密条款存在，建议明确保密信息定义和例外情形"),
        ],
    },
    "知识产权": {
        "high_risk": [
            (r"知识产权[^。；;]*?归[^。；;]*?甲方", "知识产权单方归属甲方，建议协商共同拥有或明确使用许可"),
            (r"成果[^。；;]*?归[^。；;]*?甲方", "成果单方归属甲方，建议协商共同拥有或明确使用许可"),
        ],
        "medium_risk": [
            (r"知识产权归属", "知识产权归属需明确，建议明确所有权和使用权"),
            (r"许可使用", "许可使用范围需明确，建议明确许可类型和期限"),
        ],
        "low_risk": [
            (r"知识产权", "知识产权条款存在，建议明确成果归属和侵权责任"),
        ],
    },
}


def get_risk_level(category: str, text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    根据规则匹配文本，返回风险等级和风险描述。
    
    Args:
        category: 风险类别（违约/付款/保密/知识产权）
        text: 合同文本
    
    Returns:
        (风险等级, 风险描述) 或 (None, None) 表示未匹配
    """
    rules = RISK_RULES.get(category, {})
    
    # 先匹配高风险
    for pattern, desc in rules.get("high_risk", []):
        if re.search(pattern, text):
            return "high", desc
    
    # 再匹配中风险
    for pattern, desc in rules.get("medium_risk", []):
        if re.search(pattern, text):
            return "medium", desc
    
    # 最后匹配低风险
    for pattern, desc in rules.get("low_risk", []):
        if re.search(pattern, text):
            return "low", desc
    
    return None, None


def extract_matched_sentence(text: str, pattern: str, max_len: int = 100) -> str:
    """
    提取匹配到的句子片段。
    
    Args:
        text: 合同文本
        pattern: 正则表达式
        max_len: 最大提取长度
    
    Returns:
        匹配的句子片段
    """
    match = re.search(pattern, text)
    if not match:
        return ""
    
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 20)
    snippet = text[start:end].replace("\n", " ").strip()
    
    if len(snippet) > max_len:
        snippet = snippet[:max_len] + "..."
    
    return snippet


def review_contract(text: str) -> Dict[str, Any]:
    """
    对合同文本进行风险审查。
    
    Args:
        text: 合同文本
    
    Returns:
        审查结果字典
    """
    findings = []
    
    for category in RISK_RULES:
        rules = RISK_RULES[category]
        all_patterns = []
        for level in ["high_risk", "medium_risk", "low_risk"]:
            for pattern, desc in rules.get(level, []):
                all_patterns.append((pattern, desc, level.replace("_risk", "")))
        
        for pattern, desc, level in all_patterns:
            if re.search(pattern, text):
                snippet = extract_matched_sentence(text, pattern)
                findings.append({
                    "category": category,
                    "level": level,
                    "description": desc,
                    "matched_text": snippet,
                    "pattern": pattern,
                })
    
    # 去重（同一类别同一等级只保留第一个）
    seen = set()
    unique_findings = []
    for finding in findings:
        key = (finding["category"], finding["level"], finding["pattern"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(finding)
    
    # 统计风险等级
    high_count = sum(1 for f in unique_findings if f["level"] == "high")
    medium_count = sum(1 for f in unique_findings if f["level"] == "medium")
    low_count = sum(1 for f in unique_findings if f["level"] == "low")
    
    return {
        "findings": unique_findings,
        "summary": {
            "total": len(unique_findings),
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }


def read_text_file(file_path: Path) -> str:
    """
    读取文本文件内容。
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件内容
    
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件为空
    """
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    content = file_path.read_text(encoding="utf-8", errors="replace")
    if not content.strip():
        raise ValueError(f"文件内容为空: {file_path}")
    
    return content


def read_docx_file(file_path: Path) -> str:
    """
    读取 Word 文档内容。
    
    Args:
        file_path: 文件路径
    
    Returns:
        文档文本内容
    
    Raises:
        ImportError: 缺少 python-docx 库
        FileNotFoundError: 文件不存在
        ValueError: 文件为空
    """
    if not DOCX_AVAILABLE:
        raise ImportError("缺少 python-docx 库，请安装: pip install python-docx")
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    doc = Document(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    content = "\n".join(paragraphs)
    
    if not content.strip():
        raise ValueError(f"文件内容为空: {file_path}")
    
    return content


def read_input_file(file_path: Path) -> str:
    """
    根据文件扩展名读取内容。
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件文本内容
    
    Raises:
        ValueError: 不支持的文件格式
    """
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        return read_text_file(file_path)
    elif suffix == ".docx":
        return read_docx_file(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，仅支持 .txt 和 .docx")


def format_markdown(result: Dict[str, Any], source: str = "") -> str:
    """
    将审查结果格式化为 Markdown 报告。
    
    Args:
        result: 审查结果字典
        source: 来源标识（文件名或"用户输入"）
    
    Returns:
        Markdown 格式报告
    """
    lines = []
    lines.append("# 合同审查风险清单报告")
    lines.append("")
    
    if source:
        lines.append(f"**审查对象**: {source}")
    lines.append(f"**审查时间**: {result['reviewed_at']}")
    lines.append("")
    
    summary = result["summary"]
    lines.append("## 风险统计")
    lines.append("")
    lines.append(f"- 总风险点: {summary['total']}")
    lines.append(f"- 高风险: {summary['high']}")
    lines.append(f"- 中风险: {summary['medium']}")
    lines.append(f"- 低风险: {summary['low']}")
    lines.append("")
    
    if not result["findings"]:
        lines.append("## 审查结果")
        lines.append("")
        lines.append("未发现明显风险点。")
        return "\n".join(lines)
    
    lines.append("## 风险明细")
    lines.append("")
    
    for i, finding in enumerate(result["findings"], 1):
        level_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(finding["level"], "⚪")
        lines.append(f"### {i}. {level_icon} [{finding['category']}] {finding['level'].upper()}")
        lines.append("")
        lines.append(f"**风险描述**: {finding['description']}")
        lines.append("")
        lines.append(f"**匹配原文**: {finding['matched_text']}")
        lines.append("")
    
    return "\n".join(lines)


def atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """
    原子化写入 JSON 文件。
    
    Args:
        file_path: 输出文件路径
        data: 要写入的数据
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=str(file_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # 原子替换
        os.replace(temp_path, file_path)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def atomic_write_markdown(file_path: Path, content: str) -> None:
    """
    原子化写入 Markdown 文件。
    
    Args:
        file_path: 输出文件路径
        content: 要写入的内容
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=str(file_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子替换
        os.replace(temp_path, file_path)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def process_file(file_path: Path, output_format: str = "json") -> Dict[str, Any]:
    """
    处理单个文件。
    
    Args:
        file_path: 文件路径
        output_format: 输出格式（json/markdown）
    
    Returns:
        处理结果
    """
    try:
        content = read_input_file(file_path)
    except (FileNotFoundError, ValueError, ImportError) as e:
        return {
            "status": "error",
            "error_code": 1 if isinstance(e, FileNotFoundError) else (3 if isinstance(e, ValueError) else 4),
            "error_message": str(e),
            "file": str(file_path),
        }
    
    result = review_contract(content)
    result["source"] = str(file_path)
    
    # 生成输出文件
    output_path = file_path.with_suffix(".review.json" if output_format == "json" else ".review.md")
    
    try:
        if output_format == "json":
            atomic_write_json(output_path, result)
        else:
            markdown_content = format_markdown(result, source=str(file_path))
            atomic_write_markdown(output_path, markdown_content)
    except Exception as e:
        return {
            "status": "error",
            "error_code": 5,
            "error_message": f"写入输出文件失败: {e}",
            "file": str(file_path),
        }
    
    return {
        "status": "success",
        "file": str(file_path),
        "output": str(output_path),
        "summary": result["summary"],
    }


def run_selftest() -> int:
    """
    自测函数：验证核心功能是否正常。
    
    Returns:
        0 表示成功，非 0 表示失败
    """
    print("=" * 60)
    print("开始自测...")
    print("=" * 60)
    
    # 测试 1: 高风险违约条款
    print("\n[测试 1] 高风险违约条款检测")
    test_text_1 = "若乙方违约，需支付违约金20%，并赔偿全部损失。"
    result_1 = review_contract(test_text_1)
    assert result_1["summary"]["high"] >= 1, "应检测到高风险违约条款"
    assert any(f["category"] == "违约" and f["level"] == "high" for f in result_1["findings"]), "应检测到违约高风险"
    print(f"  ✓ 通过，检测到 {result_1['summary']['high']} 个高风险点")
    
    # 测试 2: 高风险付款条款
    print("\n[测试 2] 高风险付款条款检测")
    test_text_2 = "甲方需先付款后交货，且一次性付清全部款项。"
    result_2 = review_contract(test_text_2)
    assert result_2["summary"]["high"] >= 1, "应检测到高风险付款条款"
    assert any(f["category"] == "付款" and f["level"] == "high" for f in result_2["findings"]), "应检测到付款高风险"
    print(f"  ✓ 通过，检测到 {result_2['summary']['high']} 个高风险点")
    
    # 测试 3: 中风险保密条款
    print("\n[测试 3] 中风险保密条款检测")
    test_text_3 = "双方应遵守保密期限和保密范围的规定。"
    result_3 = review_contract(test_text_3)
    assert result_3["summary"]["medium"] >= 1, "应检测到中风险保密条款"
    assert any(f["category"] == "保密" and f["level"] == "medium" for f in result_3["findings"]), "应检测到保密中风险"
    print(f"  ✓ 通过，检测到 {result_3['summary']['medium']} 个中风险点")
    
    # 测试 4: 高风险知识产权条款
    print("\n[测试 4] 高风险知识产权条款检测")
    test_text_4 = "本项目产生的知识产权归甲方所有。"
    result_4 = review_contract(test_text_4)
    assert result_4["summary"]["high"] >= 1, "应检测到高风险知识产权条款"
    assert any(f["category"] == "知识产权" and f["level"] == "high" for f in result_4["findings"]), "应检测到知识产权高风险"
    print(f"  ✓ 通过，检测到 {result_4['summary']['high']} 个高风险点")
    
    # 测试 5: 无风险文本
    print("\n[测试 5] 无风险文本检测")
    test_text_5 = "本合同自双方签字之日起生效。"
    result_5 = review_contract(test_text_5)
    assert result_5["summary"]["total"] == 0, "不应检测到风险点"
    print("  ✓ 通过，未检测到风险点")
    
    # 测试 6: 文件读取功能
    print("\n[测试 6] 文件读取功能")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("甲方需一次性付款给乙方，违约金为30%。")
        temp_file = f.name
    
    try:
        content = read_input_file(Path(temp_file))
        assert "一次性付款" in content, "文件内容读取失败"
        print("  ✓ 通过，文件读取成功")
    finally:
        os.unlink(temp_file)
    
    # 测试 7: 输出格式
    print("\n[测试 7] Markdown 输出格式")
    test_result = review_contract("违约金为20%，赔偿全部损失。")
    md_content = format_markdown(test_result, source="测试文件")
    assert "# 合同审查风险清单报告" in md_content, "Markdown 格式错误"
    assert "风险统计" in md_content, "Markdown 缺少风险统计"
    print("  ✓ 通过，Markdown 格式正确")
    
    # 测试 8: 时间戳格式
    print("\n[测试 8] 时间戳格式")
    test_result = review_contract("测试文本")
    from datetime import datetime
    try:
        datetime.fromisoformat(test_result["reviewed_at"])
        print("  ✓ 通过，时间戳格式正确")
    except ValueError:
        print("  ✗ 失败，时间戳格式错误")
        return 1
    
    print("\n" + "=" * 60)
    print("所有自测通过！")
    print("=" * 60)
    return 0


def main() -> int:
    """
    主函数。
    
    Returns:
        退出码
    """
    parser = argparse.ArgumentParser(
        description="合同审查风险清单核查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -f contract.txt
  %(prog)s -f contract.docx -o markdown
  %(prog)s -d ./contracts/
  %(prog)s --selftest
        """,
    )
    
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="合同文件路径（.txt 或 .docx）",
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        help="批量审查目录下的所有合同文件",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测",
    )
    
    args = parser.parse_args()
    
    # 自测模式
    if args.selftest:
        return run_selftest()
    
    # 参数检查
    if not args.file and not args.directory:
        parser.print_help()
        print("\n错误: 必须指定 -f 或 -d 参数", file=sys.stderr)
        return 5
    
    # 单文件模式
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"错误: 文件不存在: {file_path}", file=sys.stderr)
            return 1
        
        result = process_file(file_path, args.output)
        
        if result["status"] == "error":
            print(f"错误: {result['error_message']}", file=sys.stderr)
            return result.get("error_code", 5)
        
        print(f"审查完成: {result['file']}")
        print(f"输出文件: {result['output']}")
        print(f"风险统计: 总{result['summary']['total']} 高{result['summary']['high']} 中{result['summary']['medium']} 低{result['summary']['low']}")
        return 0
    
    # 目录批量模式
    if args.directory:
        dir_path = Path(args.directory)
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"错误: 目录不存在: {dir_path}", file=sys.stderr)
            return 1
        
        files = list(dir_path.glob("*.txt")) + list(dir_path.glob("*.docx"))
        if not files:
            print(f"错误: 目录中没有找到 .txt 或 .docx 文件: {dir_path}", file=sys.stderr)
            return 3
        
        success_count = 0
        error_count = 0
        
        for file_path in files:
            result = process_file(file_path, args.output)
            if result["status"] == "success":
                success_count += 1
                print(f"✓ {file_path.name}: 总{result['summary']['total']} 高{result['summary']['high']} 中{result['summary']['medium']} 低{result['summary']['low']}")
            else:
                error_count += 1
                print(f"✗ {file_path.name}: {result['error_message']}", file=sys.stderr)
        
        print(f"\n批量处理完成: 成功 {success_count} 个，失败 {error_count} 个")
        return 0 if error_count == 0 else 5
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
