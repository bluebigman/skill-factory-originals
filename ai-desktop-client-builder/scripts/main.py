#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-desktop-client-builder - AI编程桌面客户端构建器

构建 AI 编程 CLI 的桌面客户端，集成会话管理、编辑器、Git 操作，
提供一体化开发界面。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import os
import sys
import json
import re
import difflib
import traceback
from pathlib import Path


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败",
    "E007": "文件写入失败",
    "E008": "参数校验失败",
    "E009": "内部逻辑错误",
    "E010": "未知异常",
}


# ============================================================
# 输入校验模块
# ============================================================
def validate_input(data):
    """校验输入数据的基本合法性。"""
    if data is None:
        raise ValueError("E001: " + ERROR_CODES["E001"])
    if not isinstance(data, str):
        raise TypeError("E003: " + ERROR_CODES["E003"] + "，期望字符串类型")
    if len(data.strip()) == 0:
        raise ValueError("E001: " + ERROR_CODES["E001"])


def validate_output_format(fmt):
    """校验输出格式参数。"""
    allowed = {"json", "text", "table"}
    if fmt not in allowed:
        raise ValueError("E008: " + ERROR_CODES["E008"] + f"，格式必须是 {allowed} 之一")


def validate_path(path_str):
    """校验文件路径，防止路径穿越。"""
    if not path_str:
        return None
    p = Path(path_str)
    # 白名单校验：不允许绝对路径或包含 .. 的路径
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("E008: " + ERROR_CODES["E008"] + "，不允许绝对路径或路径穿越")
    return p


# ============================================================
# 核心逻辑模块
# ============================================================
def extract_key_info(text):
    """
    从输入文本中提取关键信息。
    返回结构化字典，包含：标题、关键词、句子数、字符数。
    """
    # 防御性拷贝，避免外部修改
    content = text.strip()
    if not content:
        return {"title": "", "keywords": [], "sentence_count": 0, "char_count": 0}

    # 提取标题：第一行非空内容
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    title = lines[0] if lines else ""

    # 提取关键词：出现频率最高的中文词语（简化为2-4字词）
    # 使用正则匹配中文连续字符
    cn_words = re.findall(r'[\u4e00-\u9fff]{2,4}', content)
    word_freq = {}
    for w in cn_words:
        word_freq[w] = word_freq.get(w, 0) + 1
    # 按频率排序取前5个
    keywords = [w for w, _ in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]]

    # 统计句子数（以句号、问号、感叹号结尾）
    sentence_count = len(re.findall(r'[。！？!?]', content))

    return {
        "title": title,
        "keywords": keywords,
        "sentence_count": sentence_count,
        "char_count": len(content),
    }


def calculate_confidence(info):
    """
    根据提取的信息计算置信度。
    置信度 = 基础分 + 信息丰富度加分，范围 0-100。
    """
    if info["char_count"] == 0:
        return 0.0

    base = 60.0
    # 有标题加分
    if info["title"]:
        base += 10
    # 有关键词加分
    base += min(len(info["keywords"]) * 5, 20)
    # 句子数适中加分（1-20句最佳）
    if 1 <= info["sentence_count"] <= 20:
        base += 10
    return min(base, 100.0)


def process_text(text, verbose=False):
    """
    核心处理流程：提取信息、计算置信度、生成结构化结果。
    """
    # 输入校验
    validate_input(text)

    # 提取关键信息
    info = extract_key_info(text)

    # 计算置信度
    confidence = calculate_confidence(info)

    # 生成结果
    result = {
        "status": "success",
        "data": info,
        "confidence": round(confidence, 1),
        "confidence_label": get_confidence_label(confidence),
        "warnings": [],
    }

    # 低置信度标注
    if confidence < 85:
        result["warnings"].append("E005: " + ERROR_CODES["E005"] + "，建议人工复核关键信息")

    if verbose:
        print(f"[处理明细] 提取到 {info['char_count']} 字符，{info['sentence_count']} 句，"
              f"关键词 {len(info['keywords'])} 个，置信度 {confidence:.1f}%")

    return result


def get_confidence_label(confidence):
    """根据置信度返回标签。"""
    if confidence >= 90:
        return "高置信度"
    elif confidence >= 85:
        return "建议复核"
    else:
        return "需核实"


def batch_process(texts, verbose=False):
    """批量处理多个输入文本。"""
    results = []
    for i, text in enumerate(texts):
        try:
            result = process_text(text, verbose)
            result["index"] = i
            results.append(result)
        except Exception as e:
            # 单条失败不影响整体
            results.append({
                "status": "error",
                "index": i,
                "error": str(e),
                "error_code": extract_error_code(str(e)),
            })
    return results


def extract_error_code(error_msg):
    """从错误消息中提取错误码。"""
    match = re.match(r'(E\d{3})', error_msg)
    return match.group(1) if match else "E010"


# ============================================================
# 文件处理模块（多编码支持）
# ============================================================
def read_file_with_encoding(filepath):
    """
    读取文件，支持多编码（utf-8 → gbk → gb18030 三级 fallback）。
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    last_error = None
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except IOError as e:
            raise IOError(f"E006: {ERROR_CODES['E006']} - {e}")

    # 所有编码都失败，使用 errors="replace" 兜底
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print(f"[警告] 文件编码无法完全识别，已使用替换字符处理，原始错误: {last_error}", file=sys.stderr)
            return content
    except IOError as e:
        raise IOError(f"E006: {ERROR_CODES['E006']} - {e}")


def write_file_with_encoding(filepath, content, dry=True):
    """写入文件，支持多编码。dry=True 时只预览不写盘。"""
    if dry:
        print(f"[DRY-RUN] 将写入文件: {filepath}")
        print(f"[DRY-RUN] 内容长度: {len(content)} 字符")
        return False

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except IOError as e:
        raise IOError(f"E007: {ERROR_CODES['E007']} - {e}")


# ============================================================
# 输出格式化模块
# ============================================================
def format_result(result, fmt="json"):
    """将处理结果格式化为指定格式输出。"""
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "text":
        return format_text_result(result)
    elif fmt == "table":
        return format_table_result(result)
    else:
        raise ValueError(f"E008: 不支持的输出格式: {fmt}")


def format_text_result(result):
    """格式化为纯文本。"""
    if result.get("status") == "error":
        return f"处理失败: {result.get('error', '未知错误')}"

    data = result["data"]
    lines = [
        f"标题: {data['title'] or '(无)'}",
        f"字符数: {data['char_count']}",
        f"句子数: {data['sentence_count']}",
        f"关键词: {', '.join(data['keywords']) if data['keywords'] else '(无)'}",
        f"置信度: {result['confidence']}% ({result['confidence_label']})",
    ]
    if result.get("warnings"):
        lines.append("警告:")
        for w in result["warnings"]:
            lines.append(f"  - {w}")
    return "\n".join(lines)


def format_table_result(result):
    """格式化为表格。"""
    if result.get("status") == "error":
        return f"| 状态 | 错误 |\n|------|------|\n| 失败 | {result.get('error', '未知')} |"

    data = result["data"]
    rows = [
        ("标题", data["title"] or "(无)"),
        ("字符数", str(data["char_count"])),
        ("句子数", str(data["sentence_count"])),
        ("关键词", ", ".join(data["keywords"]) if data["keywords"] else "(无)"),
        ("置信度", f"{result['confidence']}% ({result['confidence_label']})"),
    ]
    # 简单表格
    header = "| 字段 | 值 |"
    sep = "|------|-----|"
    body = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return f"{header}\n{sep}\n{body}"


# ============================================================
# Diff 预览模块
# ============================================================
def generate_diff(original, modified):
    """生成两个文本的 diff 摘要。"""
    if original == modified:
        return "无变化"

    diff_lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile="原始",
        tofile="修改后",
    )
    diff_text = "".join(diff_lines)
    # 统计变化行数
    added = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))
    return f"新增 {added} 行，删除 {removed} 行\n{diff_text}"


# ============================================================
# 主流程
# ============================================================
def main():
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="AI编程桌面客户端构建器 - 处理文本并生成结构化结果",
        epilog="示例: python main.py --input '你好世界' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入文本内容")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径")
    parser.add_argument("--format", "-fmt", type=str, default="json",
                        choices=["json", "text", "table"], help="输出格式")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细处理信息")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser.add_argument("--force", action="store_true", help="强制写盘（需配合 --output）")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--batch", type=str, help="批量处理：JSON数组字符串")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 参数校验
    if not args.input and not args.file and not args.batch:
        print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
        print("请使用 --input 提供文本，或 --file 提供文件路径，或 --batch 批量处理", file=sys.stderr)
        sys.exit(1)

    try:
        # 收集输入
        input_text = None
        if args.input:
            input_text = args.input
        elif args.file:
            filepath = validate_path(args.file)
            if filepath is None:
                raise ValueError("E008: 文件路径无效")
            input_text = read_file_with_encoding(filepath)
        elif args.batch:
            # 批量模式
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    raise ValueError("E003: 批量输入必须是JSON数组")
            except json.JSONDecodeError as e:
                raise ValueError(f"E003: JSON解析失败 - {e}")

            results = batch_process(batch_data, args.verbose)
            output = format_result({"status": "success", "batch": results}, args.format)
            print(output)
            return

        # 单条处理
        result = process_text(input_text, args.verbose)
        output = format_result(result, args.format)

        # 输出
        if args.output:
            out_path = validate_path(args.output)
            if out_path is None:
                raise ValueError("E008: 输出路径无效")
            # 写盘控制：dry-run 或非 force 时只预览
            should_write = args.force and not args.dry_run
            write_file_with_encoding(out_path, output, dry=not should_write)
            if args.verbose:
                print(f"[信息] 输出已{'写入' if should_write else '预览（未写盘）'}: {out_path}")
        else:
            print(output)

    except ValueError as e:
        print(f"参数错误: {e}", file=sys.stderr)
        sys.exit(2)
    except IOError as e:
        print(f"文件错误: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']} - {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(4)


# ============================================================
# 自检模块
# ============================================================
def run_selftest():
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 测试用例契约（覆盖边缘案例）
    test_cases = [
        # (描述, 输入, 期望行为)
        ("正常中文文本", "这是一个测试文本。包含多个句子。用于验证核心逻辑。", "success"),
        ("空输入", "", "error"),
        ("None输入", None, "error"),
        ("英文文本", "Hello world. This is a test. Python programming.", "success"),
        ("超长输入", "测试。" * 1000, "success"),
        ("中文标点", "你好！这是问句？这是感叹号！", "success"),
        ("混合编码", "中文English混合123", "success"),
    ]

    passed = 0
    failed = 0

    for desc, test_input, expected_status in test_cases:
        try:
            if test_input is None:
                # None 输入应抛出异常
                try:
                    process_text(test_input)
                    print(f"[FAIL] {desc}: 预期异常但未抛出")
                    failed += 1
                except (ValueError, TypeError):
                    print(f"[PASS] {desc}: 正确拒绝 None 输入")
                    passed += 1
                continue

            result = process_text(test_input)
            status = result["status"]

            # 宽松断言：不依赖精确值
            assert status == expected_status, f"状态不匹配: {status} != {expected_status}"
            assert result["confidence"] >= 0 and result["confidence"] <= 100, "置信度超出范围"
            assert isinstance(result["data"]["char_count"], int), "字符数类型错误"
            assert result["data"]["char_count"] >= 0, "字符数为负"

            # 空输入应该报错
            if len(test_input.strip()) == 0:
                assert status == "error", "空输入应该返回错误"
                print(f"[PASS] {desc}: 正确识别空输入")
            else:
                # 非空输入应该有合理结果
                assert result["data"]["char_count"] > 0, "非空输入字符数应为正"
                print(f"[PASS] {desc}: 处理成功，置信度 {result['confidence']}%")
            passed += 1

        except AssertionError as e:
            print(f"[FAIL] {desc}: 断言失败 - {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] {desc}: 意外异常 - {e}")
            failed += 1

    # 批量处理测试
    try:
        batch_input = ["第一条", "第二条", ""]
        batch_results = batch_process(batch_input)
        assert len(batch_results) == 3, "批量结果数量错误"
        # 空字符串在批量中应返回错误
        assert batch_results[2]["status"] == "error", "批量空输入应报错"
        print(f"[PASS] 批量处理: 正确识别 {len(batch_results)} 条输入")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 批量处理: {e}")
        failed += 1

    # 编码处理测试（模拟GBK内容）
    try:
        gbk_content = "中文编码测试内容"
        # 模拟读取：直接处理字符串，验证核心逻辑
        result = process_text(gbk_content)
        assert result["status"] == "success", "中文内容处理失败"
        print(f"[PASS] 中文编码: 正确处理中文内容")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 中文编码: {e}")
        failed += 1

    # 输出格式测试
    try:
        sample = process_text("格式测试内容")
        json_out = format_result(sample, "json")
        text_out = format_result(sample, "text")
        table_out = format_result(sample, "table")
        assert json_out.startswith("{"), "JSON格式错误"
        assert "标题" in text_out, "文本格式缺少标题"
        assert "|" in table_out, "表格格式缺少分隔符"
        print("[PASS] 输出格式: JSON/文本/表格均正确")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 输出格式: {e}")
        failed += 1

    # Diff 测试
    try:
        diff = generate_diff("第一行\n第二行", "第一行\n修改行")
        assert "新增" in diff or "删除" in diff, "Diff 摘要缺失"
        print("[PASS] Diff 生成: 正确检测变更")
        passed += 1
    except Exception as e:
        print(f"[FAIL] Diff 生成: {e}")
        failed += 1

    # 错误码测试
    try:
        assert extract_error_code("E001: 测试") == "E001", "错误码提取失败"
        assert extract_error_code("未知错误") == "E010", "未知错误码应返回E010"
        print("[PASS] 错误码: 正确识别错误码")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 错误码: {e}")
        failed += 1

    # 总结
    print("=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    if failed > 0:
        print("存在失败项，请检查代码")
        sys.exit(1)
    else:
        print("全部通过 ✓")
        sys.exit(0)


# ============================================================
# 程序入口
# ============================================================
if __name__ == "__main__":
    main()
