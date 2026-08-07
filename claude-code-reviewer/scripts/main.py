#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 代码审查技能（独立实现）

本脚本根据功能规格独立实现，不复制任何既有代码。
核心能力：分析代码内容，生成结构化审查报告。
"""

import argparse
import json
import os
import sys
from pathlib import Path


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件读取失败",
    "E007": "目录不存在",
    "E008": "输出写入失败",
    "E009": "参数配置错误",
    "E010": "内部处理异常",
}


# ============================================================
# 核心数据结构
# ============================================================
class ReviewResult:
    """审查结果对象"""

    def __init__(self):
        self.summary = ""
        self.issues = []
        self.suggestions = []
        self.confidence = 0.0
        self.details = {}


# ============================================================
# 核心逻辑：代码分析
# ============================================================
def analyze_code(content: str, file_name: str = "") -> ReviewResult:
    """
    分析代码内容，生成审查报告。

    参数:
        content: 代码文本内容
        file_name: 文件名（可选）

    返回:
        ReviewResult 对象
    """
    result = ReviewResult()

    # 基础校验
    if not content or not content.strip():
        result.summary = "输入内容为空，无法分析"
        result.confidence = 0.0
        return result

    # 按行拆分
    lines = content.splitlines()
    total_lines = len(lines)
    non_empty_lines = [l for l in lines if l.strip()]

    # 基础统计
    result.details["total_lines"] = total_lines
    result.details["non_empty_lines"] = len(non_empty_lines)
    result.details["file_name"] = file_name or "未命名文件"

    # 检查常见问题
    issues = []
    suggestions = []

    # 检查过长的行（>120字符）
    long_lines = [(i + 1, len(l)) for i, l in enumerate(lines) if len(l) > 120]
    if long_lines:
        issues.append(f"发现 {len(long_lines)} 行超过120字符")
        suggestions.append("建议将长行拆分为多行，提高可读性")

    # 检查TODO/FIXME注释
    todo_count = sum(1 for l in lines if "TODO" in l.upper() or "FIXME" in l.upper())
    if todo_count > 0:
        issues.append(f"发现 {todo_count} 处 TODO/FIXME 标记")
        suggestions.append("建议及时处理 TODO/FIXME 标记，避免遗留问题")

    # 检查明显的语法风险（括号不匹配）
    for i, line in enumerate(lines, 1):
        if line.count("(") != line.count(")"):
            issues.append(f"第 {i} 行括号可能不匹配")
            break

    # 检查空文件
    if total_lines == 0:
        issues.append("文件为空")
        suggestions.append("请提供有效的代码内容")

    # 检查重复代码（简单检测：连续3行相同）
    for i in range(len(lines) - 2):
        if lines[i] == lines[i + 1] == lines[i + 2] and lines[i].strip():
            issues.append(f"第 {i + 1}-{i + 3} 行存在重复代码")
            suggestions.append("建议提取公共部分，减少重复")
            break

    result.issues = issues
    result.suggestions = suggestions

    # 计算置信度（基于信息完整性）
    if total_lines > 0:
        # 基础置信度
        base_confidence = 0.7
        # 内容越完整，置信度越高
        confidence = base_confidence + min(0.2, total_lines / 1000 * 0.1)
        # 有issues时适当降低
        confidence -= min(0.1, len(issues) * 0.02)
        result.confidence = max(0.0, min(1.0, confidence))
    else:
        result.confidence = 0.0

    # 生成摘要
    if result.confidence >= 0.9:
        result.summary = f"分析完成：共 {total_lines} 行，发现 {len(issues)} 个问题"
    elif result.confidence >= 0.85:
        result.summary = f"分析完成（建议复核）：共 {total_lines} 行，发现 {len(issues)} 个问题"
    else:
        result.summary = f"[需核实] 分析结果不确定：共 {total_lines} 行，发现 {len(issues)} 个问题"

    return result


def format_report(result: ReviewResult, output_format: str = "text") -> str:
    """
    格式化输出审查报告。

    参数:
        result: ReviewResult 对象
        output_format: 输出格式（text/json）

    返回:
        格式化后的报告字符串
    """
    if output_format == "json":
        return json.dumps(
            {
                "summary": result.summary,
                "issues": result.issues,
                "suggestions": result.suggestions,
                "confidence": round(result.confidence, 3),
                "details": result.details,
            },
            ensure_ascii=False,
            indent=2,
        )

    # 文本格式
    lines = []
    lines.append("=" * 60)
    lines.append(f"代码审查报告 - {result.details.get('file_name', '未命名')}")
    lines.append("=" * 60)
    lines.append(f"\n摘要: {result.summary}")
    lines.append(f"置信度: {result.confidence * 100:.1f}%")
    lines.append(f"总行数: {result.details.get('total_lines', 0)}")
    lines.append(f"有效行数: {result.details.get('non_empty_lines', 0)}")

    if result.issues:
        lines.append("\n发现的问题:")
        for issue in result.issues:
            lines.append(f"  ⚠️ {issue}")
    else:
        lines.append("\n未发现明显问题 ✅")

    if result.suggestions:
        lines.append("\n改进建议:")
        for suggestion in result.suggestions:
            lines.append(f"  💡 {suggestion}")

    # 置信度标注
    if result.confidence < 0.85:
        lines.append("\n⚠️ [需核实] 置信度较低，请人工复核关键结果")
    elif result.confidence < 0.9:
        lines.append("\n⚠️ 建议复核：置信度在85%-90%之间")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


# ============================================================
# 文件处理
# ============================================================
def process_file(file_path: str, output_format: str = "text") -> str:
    """
    处理单个文件。

    参数:
        file_path: 文件路径
        output_format: 输出格式

    返回:
        格式化报告
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"错误 [E007]: 文件不存在: {file_path}"

        if path.is_dir():
            return process_directory(file_path, output_format)

        # 读取文件
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(path, "r", encoding="gbk") as f:
                    content = f.read()
            except Exception:
                return f"错误 [E006]: 无法读取文件编码: {file_path}"
        except Exception as e:
            return f"错误 [E006]: 文件读取失败: {file_path} - {str(e)}"

        # 分析
        result = analyze_code(content, path.name)
        return format_report(result, output_format)

    except Exception as e:
        return f"错误 [E010]: 处理文件时发生异常: {str(e)}"


def process_directory(dir_path: str, output_format: str = "text") -> str:
    """
    处理目录（批量处理）。

    参数:
        dir_path: 目录路径
        output_format: 输出格式

    返回:
        格式化报告
    """
    try:
        path = Path(dir_path)
        if not path.exists():
            return f"错误 [E007]: 目录不存在: {dir_path}"
        if not path.is_dir():
            return f"错误 [E003]: 不是目录: {dir_path}"

        # 收集代码文件
        code_extensions = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".php", ".rb"}
        code_files = [f for f in path.rglob("*") if f.suffix in code_extensions]

        if not code_files:
            return "未找到支持的代码文件"

        # 批量处理
        reports = []
        total_issues = 0
        for file in code_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                result = analyze_code(content, file.name)
                total_issues += len(result.issues)
                if output_format == "json":
                    reports.append(
                        {
                            "file": str(file),
                            "result": {
                                "summary": result.summary,
                                "issues": result.issues,
                                "suggestions": result.suggestions,
                                "confidence": round(result.confidence, 3),
                            },
                        }
                    )
                else:
                    reports.append(format_report(result))
            except Exception as e:
                reports.append(f"错误 [E006]: 处理 {file} 失败: {str(e)}")

        # 汇总
        if output_format == "json":
            summary = {
                "total_files": len(code_files),
                "total_issues": total_issues,
                "files": reports,
            }
            return json.dumps(summary, ensure_ascii=False, indent=2)
        else:
            header = f"\n{'=' * 60}\n批量审查报告: {dir_path}\n"
            header += f"共 {len(code_files)} 个文件，发现 {total_issues} 个问题\n{'=' * 60}\n"
            return header + "\n".join(reports)

    except Exception as e:
        return f"错误 [E010]: 处理目录时发生异常: {str(e)}"


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    内置自检功能，使用硬编码样例数据离线测试核心逻辑。

    返回:
        True 表示测试通过，False 表示测试失败
    """
    print("开始自检...")

    # 测试样例1：正常代码
    sample_code_1 = """
def calculate_sum(a, b):
    # TODO: 添加参数校验
    result = a + b
    return result

def calculate_product(a, b):
    result = a * b
    return result

def main():
    x = 10
    y = 20
    print(calculate_sum(x, y))
    print(calculate_product(x, y))

if __name__ == "__main__":
    main()
"""

    # 测试样例2：有问题的代码（长行、重复）
    sample_code_2 = """
def long_function_with_many_parameters(param1, param2, param3, param4, param5, param6, param7, param8, param9, param10, param11, param12, param13, param14, param15, param16):
    # FIXME: 这个函数太长了
    return param1 + param2 + param3 + param4 + param5 + param6 + param7 + param8

def duplicate_code():
    x = 1
    y = 2
    z = 3
    x = 1
    y = 2
    z = 3
    return x + y + z
"""

    # 测试样例3：空内容
    sample_code_3 = ""

    # 测试1：正常代码分析
    print("\n测试1: 正常代码分析")
    result1 = analyze_code(sample_code_1, "sample1.py")
    assert result1.confidence > 0.5, "正常代码置信度应较高"
    assert result1.details["total_lines"] > 0, "应检测到代码行数"
    assert isinstance(result1.issues, list), "issues 应为列表"
    assert isinstance(result1.suggestions, list), "suggestions 应为列表"
    print(f"  ✅ 通过 (置信度: {result1.confidence:.2f}, 行数: {result1.details['total_lines']})")

    # 测试2：问题代码分析
    print("\n测试2: 问题代码分析")
    result2 = analyze_code(sample_code_2, "sample2.py")
    assert len(result2.issues) > 0, "应发现代码问题"
    assert result2.confidence > 0.3, "问题代码置信度应合理"
    print(f"  ✅ 通过 (发现 {len(result2.issues)} 个问题)")

    # 测试3：空内容处理
    print("\n测试3: 空内容处理")
    result3 = analyze_code(sample_code_3, "empty.py")
    assert result3.confidence <= 0.5, "空内容置信度应较低"
    print(f"  ✅ 通过 (置信度: {result3.confidence:.2f})")

    # 测试4：报告格式化
    print("\n测试4: 报告格式化")
    text_report = format_report(result1, "text")
    json_report = format_report(result1, "json")
    assert len(text_report) > 10, "文本报告应有一定长度"
    assert json.loads(json_report), "JSON报告应可解析"
    print("  ✅ 通过 (文本和JSON格式均正常)")

    # 测试5：错误处理
    print("\n测试5: 错误处理")
    # 测试空输入
    assert ERROR_CODES["E001"] == "输入为空", "E001错误码定义错误"
    assert ERROR_CODES["E002"] == "关键信息缺失", "E002错误码定义错误"
    assert len(ERROR_CODES) >= 5, "错误码数量不足"
    print("  ✅ 通过 (错误码定义完整)")

    # 测试6：文件处理（使用临时文件）
    print("\n测试6: 文件处理")
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(sample_code_1)
        temp_path = f.name
    try:
        report = process_file(temp_path)
        assert "代码审查报告" in report, "文件处理应生成报告"
        print("  ✅ 通过 (临时文件处理正常)")
    finally:
        os.unlink(temp_path)

    # 测试7：边界情况
    print("\n测试7: 边界情况")
    # 不存在的文件
    report = process_file("/nonexistent/path/file.py")
    assert "E007" in report or "E006" in report, "不存在的文件应返回错误"
    print("  ✅ 通过 (不存在的文件处理正确)")

    print("\n" + "=" * 60)
    print("所有自检测试通过 ✅")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="代码审查工具 - 分析代码并生成审查报告",
        epilog="示例: python main.py -f ./src -o json",
    )
    parser.add_argument(
        "-f", "--file",
        help="要审查的文件或目录路径",
    )
    parser.add_argument(
        "-o", "--output",
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="代码审查工具 v1.0.0",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except AssertionError as e:
            print(f"自检失败: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"自检异常 [E010]: {str(e)}")
            sys.exit(1)

    # 正常处理
    if not args.file:
        print("错误 [E001]: 请提供待审查的文件或目录路径")
        print("用法: python main.py -f <路径> [-o text|json]")
        print("提示: 使用 --selftest 运行内置自检")
        sys.exit(1)

    # 处理文件或目录
    report = process_file(args.file, args.output)
    print(report)

    # 检查是否有错误
    if report.startswith("错误"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
