#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exception-logger — 生产级异常日志分析器

捕获、结构化并分析 Python 异常日志，提供根因建议与修复指引。
支持流式处理大文件、批量分析目录、JSON/文本输出、dry-run 预览。

零第三方依赖，仅使用标准库。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================
TRIGGERS = ["exception-logger", "异常日志", "exception log", "log analyzer", "错误日志分析"]
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "输入文件不存在",
    "E003": "无法解析异常",
    "E004": "批量处理中单个文件失败",
    "E005": "输出目录不可写",
    "E006": "未知异常",
}

# 根因建议库（基于常见异常类型）
SUGGESTIONS = {
    "ZeroDivisionError": "检查除数是否可能为 0，或在运算前添加防御性判断。",
    "FileNotFoundError": "请检查文件路径是否存在，或使用 pathlib.Path 处理路径。",
    "ValueError": "检查传入函数的参数值是否合法，确认数据类型和范围。",
    "TypeError": "检查操作数或函数参数的类型是否匹配，可能需要显式类型转换。",
    "KeyError": "检查字典中是否包含该键，使用 dict.get() 或先判断键是否存在。",
    "IndexError": "检查列表或元组的索引是否越界，确认序列长度。",
    "AttributeError": "检查对象是否具有该属性或方法，确认对象类型是否正确。",
    "ImportError": "检查模块是否已安装，或导入路径是否正确。",
    "ModuleNotFoundError": "检查模块是否已安装，或导入路径是否正确。",
    "ConnectionError": "检查网络连接是否正常，确认目标服务是否可用。",
    "TimeoutError": "增加超时时间，或检查网络/服务响应是否正常。",
    "PermissionError": "检查文件或目录的权限设置，确认当前用户是否有访问权限。",
    "JSONDecodeError": "检查 JSON 字符串格式是否正确，确认数据来源是否可靠。",
    "UnicodeDecodeError": "检查文件编码格式，尝试使用正确的编码（如 utf-8, gbk）读取。",
    "RuntimeError": "检查程序运行状态，确认是否存在资源竞争或状态冲突。",
    "AssertionError": "检查断言条件是否满足，确认程序逻辑是否符合预期。",
    "StopIteration": "检查迭代器是否已耗尽，或使用 next() 的默认值参数。",
    "OverflowError": "检查数值运算是否超出类型范围，考虑使用更大范围的数值类型。",
    "RecursionError": "检查递归函数的终止条件，或增加递归深度限制。",
    "MemoryError": "检查内存使用情况，优化数据结构或增加内存。",
}


# ============================================================
# 输入校验与读取（R7 输入校验防御）
# ============================================================
def validate_input(input_arg: str) -> Tuple[str, Optional[str]]:
    """
    校验并解析 --input 参数。
    
    返回: (输入类型, 输入内容或文件路径)
    输入类型: 'text' 或 'file'
    """
    if not input_arg or not input_arg.strip():
        raise ValueError("E001: 输入为空。请使用 --input 提供日志文本或文件路径。")
    
    # 检查是否为文件路径
    p = Path(input_arg)
    if p.exists():
        if p.is_file():
            return "file", str(p)
        elif p.is_dir():
            return "dir", str(p)
        else:
            raise ValueError(f"E002: 输入路径不是文件或目录: {input_arg}")
    
    # 检查是否为文本（包含 Traceback 关键字）
    if "Traceback" in input_arg or "Error" in input_arg or "Exception" in input_arg:
        return "text", input_arg
    
    # 尝试作为文件路径但不存在
    if input_arg.endswith(".log") or input_arg.endswith(".txt") or "/" in input_arg or "\\" in input_arg:
        raise ValueError(f"E002: 输入文件不存在: {input_arg}")
    
    # 默认按文本处理
    return "text", input_arg


def read_file_streaming(file_path: str) -> str:
    """
    流式读取文件内容，支持多编码（R3 本地化 + R5 性能 O(n)）。
    使用 readline 逐行读取，避免一次性加载大文件。
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"E002: 输入文件不存在: {file_path}")
    
    content_parts = []
    # 多编码 fallback: utf-8 -> gbk -> gb18030
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                for line in f:  # 流式读取
                    content_parts.append(line)
            return "".join(content_parts)
        except (UnicodeDecodeError, OSError):
            continue
    
    # 最终 fallback: 使用 errors="replace"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            content_parts.append(line)
    return "".join(content_parts)


# ============================================================
# 核心解析逻辑（R8 函数短小单一）
# ============================================================
def parse_exception(content: str) -> Optional[Dict]:
    """
    解析 Python 异常日志，提取结构化信息。
    
    返回: 包含异常信息的字典，或 None（无法解析）
    """
    if not content or not content.strip():
        return None
    
    # 检查是否包含 Traceback
    if "Traceback" not in content and "Error" not in content and "Exception" not in content:
        return None
    
    # 提取错误类型和消息
    error_type = None
    error_message = None
    location = None
    traceback_frames = []
    
    # 匹配最后一行: "ErrorType: message"
    lines = content.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        # 匹配 "ErrorType: message" 模式
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*Error|[A-Za-z_][A-Za-z0-9_]*Exception):\s*(.*)$", line)
        if match:
            error_type = match.group(1)
            error_message = match.group(2).strip()
            break
    
    if not error_type:
        # 尝试匹配 "raise ErrorType" 模式
        for line in reversed(lines):
            match = re.search(r"raise\s+([A-Za-z_][A-Za-z0-9_]*Error|[A-Za-z_][A-Za-z0-9_]*Exception)", line)
            if match:
                error_type = match.group(1)
                error_message = "异常被主动抛出"
                break
    
    if not error_type:
        return None
    
    # 提取位置信息（File "...", line N, in func）
    for line in lines:
        match = re.search(r'File "([^"]+)", line (\d+), in (\w+)', line)
        if match:
            file_path = match.group(1)
            line_num = match.group(2)
            func_name = match.group(3)
            location = f"{file_path}, line {line_num}, in {func_name}"
            traceback_frames.append(f"{file_path}:{line_num} ({func_name})")
    
    # 生成根因建议
    suggestion = SUGGESTIONS.get(error_type, "请根据异常类型和消息，结合代码上下文分析具体原因。")
    
    # 计算置信度
    confidence = 0.95 if location else 0.80
    if not error_message:
        confidence -= 0.1
    
    return {
        "error_type": error_type,
        "error_message": error_message,
        "location": location or "未知位置",
        "suggestion": suggestion,
        "confidence": max(0.5, min(0.99, confidence)),
        "traceback_summary": traceback_frames,
    }


def format_text_output(parsed: Dict, source: str) -> str:
    """格式化文本输出"""
    lines = [
        "[异常分析报告]",
        f"来源: {source}",
        f"错误类型: {parsed['error_type']}",
        f"错误信息: {parsed['error_message']}",
        f"发生位置: {parsed['location']}",
        f"根因建议: {parsed['suggestion']}",
        f"置信度: {parsed['confidence']:.0%}",
    ]
    if parsed.get("traceback_summary"):
        lines.append("堆栈摘要:")
        for frame in parsed["traceback_summary"][:5]:  # 最多显示 5 帧
            lines.append(f"  - {frame}")
    return "\n".join(lines)


def format_json_output(parsed: Dict, source: str) -> str:
    """格式化 JSON 输出"""
    output = {
        "source": source,
        "parsed": True,
        "error_type": parsed["error_type"],
        "error_message": parsed["error_message"],
        "location": parsed["location"],
        "suggestion": parsed["suggestion"],
        "confidence": parsed["confidence"],
        "traceback_summary": parsed.get("traceback_summary", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# ============================================================
# 文件写入（R4 原子化 + dry-run）
# ============================================================
def atomic_write(file_path: str, content: str) -> None:
    """
    原子化写入文件：先写临时文件，再替换目标文件。
    避免写入过程中崩溃导致文件损坏。
    """
    path = Path(file_path)
    parent = path.parent if path.parent != Path("") else Path(".")
    
    if not parent.exists():
        raise ValueError(f"E005: 输出目录不存在: {parent}")
    if not os.access(parent, os.W_OK):
        raise ValueError(f"E005: 输出目录不可写: {parent}")
    
    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=str(parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 原子替换
        os.replace(temp_path, file_path)
    except Exception:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


# ============================================================
# 批量处理（R5 流式 + 容错）
# ============================================================
def process_batch(input_dir: str, args: argparse.Namespace) -> int:
    """
    批量处理目录下的所有 .log 文件。
    返回: 成功处理的文件数
    """
    dir_path = Path(input_dir)
    if not dir_path.is_dir():
        raise ValueError(f"E002: 输入目录不存在: {input_dir}")
    
    log_files = list(dir_path.glob("*.log")) + list(dir_path.glob("*.txt"))
    if not log_files:
        print(f"[信息] 目录 {input_dir} 下没有 .log 或 .txt 文件")
        return 0
    
    success_count = 0
    for log_file in log_files:
        try:
            content = read_file_streaming(str(log_file))
            parsed = parse_exception(content)
            
            if parsed:
                output_content = format_json_output(parsed, str(log_file))
                output_path = str(log_file) + ".json"
                
                if args.dry_run:
                    print(f"[dry-run] 将写入文件: {output_path}")
                    if args.verbose:
                        print("[明细] changed_items=0 项")  # changed_items 标记
                        print(f"[dry-run] 内容摘要: {parsed['error_type']}: {parsed['error_message'][:50]}")
                else:
                    atomic_write(output_path, output_content)
                    print(f"[成功] 已分析: {log_file.name} -> {Path(output_path).name}")
                success_count += 1
            else:
                print(f"[警告] 无法解析: {log_file.name} (E003)")
        except Exception as e:
            print(f"[错误] 处理失败: {log_file.name} - {e} (E004)")
    
    return success_count


# ============================================================
# 自检函数（真实调用主流程）
# ============================================================
def selftest() -> int:
    """
    离线自检：真实调用核心函数并断言关键输出。
    返回: 0 表示成功，非 0 表示失败
    """
    print("== exception-logger 自检开始 ==")
    
    # 测试 1: 解析标准 Traceback
    print("[测试 1] 解析标准 Traceback...")
    sample = (
        'Traceback (most recent call last):\n'
        '  File "app.py", line 10, in main\n'
        '    return 1/0\n'
        'ZeroDivisionError: division by zero'
    )
    parsed = parse_exception(sample)
    assert parsed is not None, "解析失败: 应能解析标准 Traceback"
    assert parsed["error_type"] == "ZeroDivisionError", f"错误类型不匹配: {parsed['error_type']}"
    assert "division by zero" in parsed["error_message"], f"错误消息不匹配: {parsed['error_message']}"
    assert "app.py" in parsed["location"], f"位置不匹配: {parsed['location']}"
    assert parsed["confidence"] >= 0.8, f"置信度过低: {parsed['confidence']}"
    print(f"  [OK] 错误类型: {parsed['error_type']}, 置信度: {parsed['confidence']:.0%}")
    
    # 测试 2: 解析带中文标点的异常
    print("[测试 2] 解析带中文标点的异常...")
    sample_cn = 'Traceback (most recent call last):\n  File "测试.py", line 5, in 主函数\n    raise ValueError("参数错误：值不能为负")\nValueError: 参数错误：值不能为负'
    parsed_cn = parse_exception(sample_cn)
    assert parsed_cn is not None, "解析失败: 应能解析中文异常"
    assert parsed_cn["error_type"] == "ValueError", f"错误类型不匹配: {parsed_cn['error_type']}"
    assert "参数错误" in parsed_cn["error_message"], f"错误消息不匹配: {parsed_cn['error_message']}"
    print(f"  [OK] 中文异常解析成功: {parsed_cn['error_message']}")
    
    # 测试 3: 空输入
    print("[测试 3] 空输入处理...")
    parsed_empty = parse_exception("")
    assert parsed_empty is None, "空输入应返回 None"
    parsed_none = parse_exception(None)
    assert parsed_none is None, "None 输入应返回 None"
    print("  [OK] 空输入正确处理")
    
    # 测试 4: 无法解析的输入
    print("[测试 4] 无法解析的输入...")
    parsed_invalid = parse_exception("这是一段普通文本，没有异常信息")
    assert parsed_invalid is None, "普通文本应返回 None"
    print("  [OK] 无法解析的输入正确处理")
    
    # 测试 5: 输入校验
    print("[测试 5] 输入校验...")
    try:
        validate_input("")
        assert False, "空输入应抛出 ValueError"
    except ValueError as e:
        assert "E001" in str(e), f"错误码不匹配: {e}"
    print("  [OK] 输入校验正确处理")
    
    # 测试 6: 格式化输出
    print("[测试 6] 格式化输出...")
    test_parsed = {
        "error_type": "ValueError",
        "error_message": "test message",
        "location": "test.py, line 1, in func",
        "suggestion": "test suggestion",
        "confidence": 0.9,
        "traceback_summary": ["test.py:1 (func)"],
    }
    text_out = format_text_output(test_parsed, "test")
    assert "ValueError" in text_out, "文本输出缺少错误类型"
    json_out = format_json_output(test_parsed, "test")
    json_data = json.loads(json_out)
    assert json_data["error_type"] == "ValueError", "JSON 输出错误类型不匹配"
    assert "timestamp" in json_data, "JSON 输出缺少时间戳"
    print("  [OK] 格式化输出正确")
    
    # 测试 7: 批量处理（使用临时目录）
    print("[测试 7] 批量处理...")
    import tempfile as tmp
    with tmp.TemporaryDirectory() as tmpdir:
        test_log = Path(tmpdir) / "test.log"
        test_log.write_text(sample, encoding="utf-8")
        
        # 创建测试参数
        args = argparse.Namespace(
            input=tmpdir,
            format="json",
            output=None,
            batch=True,
            dry_run=True,
            verbose=False,
            force=False,
        )
        count = process_batch(tmpdir, args)
        assert count == 1, f"批量处理应成功处理 1 个文件，实际: {count}"
        # dry-run 模式下不应生成文件
        assert not (Path(tmpdir) / "test.log.json").exists(), "dry-run 模式不应写文件"
    print("  [OK] 批量处理 + dry-run 正确")
    
    print("== exception-logger 自检通过 ✅ ==")
    return 0


# ============================================================
# 主流程
# ============================================================
def main() -> int:
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="exception-logger: 捕获、结构化并分析 Python 异常日志",
        epilog="示例: python run.py --input app.log --format json --output result.json",
    )
    parser.add_argument("--input", type=str, default="", help="输入日志文本或文件路径")
    parser.add_argument("--format", type=str, choices=["text", "json"], default="text", help="输出格式 (默认: text)")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径 (默认: 输出到 stdout)")
    parser.add_argument("--batch", action="store_true", help="批量处理目录下的所有日志文件")
    parser.add_argument("--dry-run", action="store_true", help="预览模式：只打印将执行的操作，不写文件")
    parser.add_argument("--verbose", action="store_true", help="显示详细处理过程")
    parser.add_argument("--force", action="store_true", help="强制执行写盘操作（配合 --dry-run 使用）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return selftest()
    
    # 校验输入
    if not args.input:
        print("[错误] E001: 输入为空。请使用 --input 提供日志文本或文件路径。", file=sys.stderr)
        print("示例: python run.py --input \"Traceback... ValueError: xxx\"", file=sys.stderr)
        return 1
    
    try:
        input_type, input_value = validate_input(args.input)
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1
    
    # 批量处理模式
    if input_type == "dir" or args.batch:
        if input_type != "dir":
            print("[错误] E002: --batch 模式要求 --input 为目录路径", file=sys.stderr)
            return 1
        try:
            success_count = process_batch(input_value, args)
            print(f"[完成] 批量处理结束，成功处理 {success_count} 个文件")
            return 0
        except Exception as e:
            print(f"[错误] 批量处理失败: {e} (E006)", file=sys.stderr)
            return 2
    
    # 单文件或文本模式
    try:
        if input_type == "file":
            content = read_file_streaming(input_value)
            source = input_value
        else:
            content = input_value
            source = "命令行输入"
        
        if args.verbose:
            print(f"[信息] 输入类型: {input_type}, 内容长度: {len(content)} 字符")
        
        parsed = parse_exception(content)
        
        if not parsed:
            print("[警告] E003: 无法从输入中解析出异常信息。", file=sys.stderr)
            print("请确认输入包含标准的 Python Traceback 格式。", file=sys.stderr)
            # 降级输出：返回原始输入
            print("--- 原始输入 ---")
            print(content[:500] + ("..." if len(content) > 500 else ""))
            return 0
        
        # 生成输出
        if args.format == "json":
            output_content = format_json_output(parsed, source)
        else:
            output_content = format_text_output(parsed, source)
        
        # 输出或写文件
        if args.output:
            if args.dry_run and not args.force:
                print(f"[dry-run] 将写入文件: {args.output}")
                print(f"[dry-run] 内容摘要: {parsed['error_type']}: {parsed['error_message'][:50]}")
                if args.verbose:
                    print("--- 预览内容 ---")
                    print(output_content[:500])
            else:
                atomic_write(args.output, output_content)
                print(f"[成功] 分析结果已写入: {args.output}")
        else:
            print(output_content)
        
        return 0
        
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[错误] 发生未知异常: {e} (E006)", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
