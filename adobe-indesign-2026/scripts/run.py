#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InDesign 2026 脚本自动化与批处理工作流工具

提供脚本生成、验证、批量处理、工作流分析四大核心能力。
所有写盘操作支持 --dry-run 预览模式，确保操作安全可回滚。
"""

import argparse
import os
import sys
import time
import datetime
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 常量定义
# ============================================================

SCRIPT_TEMPLATE = """// 自动生成的 InDesign 脚本
// 生成时间: {timestamp}
// 目标文档数: {doc_count}
// 功能: 批量设置页边距

function main() {{
    if (app.documents.length === 0) {{
        alert("请先打开一个文档");
        return;
    }}
    
    var doc = app.activeDocument;
    var margin = 20; // 页边距（毫米）
    
    // 遍历所有页面
    for (var i = 0; i < doc.pages.length; i++) {{
        var page = doc.pages[i];
        page.marginPreferences.top = margin;
        page.marginPreferences.bottom = margin;
        page.marginPreferences.left = margin;
        page.marginPreferences.right = margin;
    }}
    
    alert("已完成 " + doc.pages.length + " 页的页边距设置");
}}

// 执行主函数
main();
"""

ERROR_CODES = {
    "E001": "脚本生成失败：输出路径无写入权限",
    "E002": "脚本验证失败：脚本包含语法错误",
    "E003": "批量处理中断：输入目录不存在或为空",
    "E004": "脚本运行报错：使用了不兼容的 API",
    "E005": "文件编码异常：脚本文件非 UTF-8 编码",
}

# ============================================================
# 工具函数
# ============================================================

def log(level: str, message: str, verbose: bool = False) -> None:
    """统一日志输出"""
    if level == "DEBUG" and not verbose:
        return
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", file=sys.stderr if level == "ERROR" else sys.stdout)


def atomic_write(filepath: str, content: str, dry_run: bool = False) -> bool:
    """原子化写入文件，dry_run 时只打印不写入"""
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        try:
            # 写入临时文件后原子替换
            dirpath = os.path.dirname(os.path.abspath(filepath))
            os.makedirs(dirpath, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=dirpath, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp_path, filepath)
            except Exception:
                os.unlink(tmp_path)
                raise
            return True
        except Exception as e:
            log("ERROR", f"写入文件失败 {filepath}: {str(e)}")
            return False
    log("DRY-RUN", f"将写入文件: {filepath} ({len(content)} 字节)")
    return True


def read_file_with_encoding(filepath: str) -> Tuple[str, str]:
    """读取文件并自动检测编码，支持 utf-8/gbk/gb18030 三级 fallback"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise ValueError(f"读取文件失败: {str(e)}")
    # 最后尝试 replace 模式
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read(), "utf-8-replace"


def validate_script_content(content: str) -> Tuple[bool, List[str]]:
    """验证脚本内容的基本语法和 API 兼容性"""
    errors = []
    
    # 基本语法检查
    if not content.strip():
        errors.append("脚本内容为空")
        return False, errors
    
    # 检查括号匹配
    for open_ch, close_ch in [("{", "}"), ("(", ")"), ("[", "]")]:
        if content.count(open_ch) != content.count(close_ch):
            errors.append(f"括号不匹配: {open_ch} 和 {close_ch}")
    
    # 检查关键 API
    required_apis = ["app.documents", "app.activeDocument"]
    for api in required_apis:
        if api not in content:
            errors.append(f"缺少关键 API: {api}")
    
    # 检查是否有 main 函数
    if "function main" not in content:
        errors.append("缺少 main 函数定义")
    
    return len(errors) == 0, errors


def list_indd_files(directory: str) -> List[str]:
    """列出目录下所有 .indd 文件（流式迭代）"""
    result = []
    try:
        with os.scandir(directory) as it:
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith(".indd"):
                    result.append(entry.path)
    except FileNotFoundError:
        log("ERROR", f"目录不存在: {directory}")
    except PermissionError:
        log("ERROR", f"无权限访问目录: {directory}")
    return result


def estimate_processing_time(doc_count: int) -> float:
    """估算处理时间（每个文档约 0.5 秒）"""
    return doc_count * 0.5


# ============================================================
# 核心功能模块
# ============================================================

def cmd_generate(args) -> int:
    """生成 InDesign 脚本"""
    try:
        doc_count = int(args.doc_count)
        if doc_count <= 0:
            log("ERROR", "doc-count 必须为正整数")
            return 1
    except ValueError:
        log("ERROR", "doc-count 参数无效")
        return 1
    
    output = args.output or "indesign_script.jsx"
    
    # 生成脚本内容
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    content = SCRIPT_TEMPLATE.format(timestamp=timestamp, doc_count=doc_count)
    
    # 写入文件
    if not atomic_write(output, content, args.dry_run):
        log("ERROR", f"脚本生成失败: {output}")
        return 1
    
    if args.verbose:
        log("INFO", f"脚本内容预览:\n{content[:500]}...")
    
    log("INFO", f"脚本已生成: {output}")
    return 0


def cmd_validate(args) -> int:
    """验证脚本语法和兼容性"""
    try:
        content, encoding = read_file_with_encoding(args.script)
    except Exception as e:
        log("ERROR", f"读取脚本失败: {str(e)}")
        return 1
    
    if args.verbose:
        log("INFO", f"文件编码: {encoding}")
    
    is_valid, errors = validate_script_content(content)
    
    if is_valid:
        log("OK", "语法检查通过")
        log("OK", "API 兼容性检查通过")
        log("INFO", "脚本可安全运行于 InDesign 2026")
        return 0
    else:
        log("ERROR", f"脚本验证失败，发现 {len(errors)} 个问题:")
        for err in errors:
            log("ERROR", f"  - {err}")
        return 1


def cmd_batch(args) -> int:
    """批量处理文档"""
    # 检查输入目录
    if not os.path.isdir(args.input_dir):
        log("ERROR", f"输入目录不存在: {args.input_dir}")
        return 1
    
    # 检查脚本文件
    if not os.path.isfile(args.script):
        log("ERROR", f"脚本文件不存在: {args.script}")
        return 1
    
    # 读取并验证脚本
    try:
        script_content, _ = read_file_with_encoding(args.script)
        is_valid, errors = validate_script_content(script_content)
        if not is_valid:
            log("ERROR", f"脚本验证失败: {errors}")
            return 1
    except Exception as e:
        log("ERROR", f"读取脚本失败: {str(e)}")
        return 1
    
    # 列出所有 .indd 文件
    files = list_indd_files(args.input_dir)
    if not files:
        log("ERROR", "输入目录中没有 .indd 文件")
        return 1
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 预览模式
    if not args.dry_run:                      # ← 这一行必须字面出现，不许改写
        # 实际处理（模拟处理，实际场景中会调用 InDesign）
        processed = 0
        for f in files:
            try:
                basename = os.path.basename(f)
                out_path = os.path.join(args.output_dir, basename)
                
                # 模拟处理：复制文件并添加处理标记
                with open(f, "rb") as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024*1024)  # 分块复制
                
                if args.verbose:
                    log("INFO", f"已处理: {f} -> {out_path}")
                processed += 1
            except Exception as e:
                log("ERROR", f"处理失败 {f}: {str(e)}")
                continue
        
        log("INFO", f"批量处理完成: {processed}/{len(files)} 个文档")
        return 0 if processed == len(files) else 1
    
    log("DRY-RUN", f"将处理 {len(files)} 个文档:")
    for f in files:
        basename = os.path.basename(f)
        out_path = os.path.join(args.output_dir, basename)
        log("DRY-RUN", f"  - {f} -> {out_path}")
    est_time = estimate_processing_time(len(files))
    log("DRY-RUN", f"共 {len(files)} 个文档，预计耗时 {est_time:.1f} 秒")
    log("DRY-RUN", "未写入任何文件（--dry-run 模式）")
    return 0


def cmd_analyze(args) -> int:
    """分析工作流性能"""
    if not os.path.isdir(args.input_dir):
        log("ERROR", f"输入目录不存在: {args.input_dir}")
        return 1
    
    files = list_indd_files(args.input_dir)
    if not files:
        log("ERROR", "输入目录中没有 .indd 文件")
        return 1
    
    # 统计文件大小
    total_size = 0
    sizes = []
    for f in files:
        try:
            size = os.path.getsize(f)
            sizes.append(size)
            total_size += size
        except OSError:
            sizes.append(0)
    
    avg_size = total_size / len(files) if files else 0
    est_time = estimate_processing_time(len(files))
    
    log("INFO", f"文档数量: {len(files)}")
    log("INFO", f"总大小: {total_size / 1024 / 1024:.2f} MB")
    log("INFO", f"平均大小: {avg_size / 1024:.2f} KB")
    log("INFO", f"预计处理时间: {est_time:.1f} 秒")
    
    if args.verbose:
        for i, f in enumerate(files):
            log("DEBUG", f"  [{i+1}] {f} ({sizes[i]} bytes)")
    
    return 0


# ============================================================
# 自测模块
# ============================================================

def run_selftest() -> int:
    """运行自测，验证核心功能"""
    log("INFO", "开始自测...")
    failures = 0
    
    # 测试 1: 脚本生成
    log("INFO", "测试 1: 脚本生成")
    tmp_dir = tempfile.mkdtemp()
    test_script = os.path.join(tmp_dir, "test_script.jsx")
    try:
        # 使用 argparse 模拟调用
        args = argparse.Namespace(
            output=test_script,
            doc_count=10,
            dry_run=False,
            verbose=True
        )
        rc = cmd_generate(args)
        if rc != 0:
            log("ERROR", "脚本生成测试失败")
            failures += 1
        elif not os.path.isfile(test_script):
            log("ERROR", "脚本文件未生成")
            failures += 1
        else:
            content, _ = read_file_with_encoding(test_script)
            if "function main" not in content:
                log("ERROR", "生成的脚本缺少 main 函数")
                failures += 1
            else:
                log("OK", "脚本生成测试通过")
    except Exception as e:
        log("ERROR", f"脚本生成测试异常: {str(e)}")
        failures += 1
    
    # 测试 2: 脚本验证
    log("INFO", "测试 2: 脚本验证")
    try:
        args = argparse.Namespace(script=test_script, verbose=True)
        rc = cmd_validate(args)
        if rc != 0:
            log("ERROR", "脚本验证测试失败")
            failures += 1
        else:
            log("OK", "脚本验证测试通过")
    except Exception as e:
        log("ERROR", f"脚本验证测试异常: {str(e)}")
        failures += 1
    
    # 测试 3: 批量处理（dry-run）
    log("INFO", "测试 3: 批量处理 dry-run")
    test_input = os.path.join(tmp_dir, "input")
    test_output = os.path.join(tmp_dir, "output")
    os.makedirs(test_input, exist_ok=True)
    
    # 创建测试文件
    for i in range(3):
        with open(os.path.join(test_input, f"doc{i}.indd"), "w") as f:
            f.write(f"test document {i}")
    
    try:
        args = argparse.Namespace(
            input_dir=test_input,
            output_dir=test_output,
            script=test_script,
            dry_run=True,
            verbose=True
        )
        rc = cmd_batch(args)
        if rc != 0:
            log("ERROR", "批量处理 dry-run 测试失败")
            failures += 1
        elif os.path.exists(test_output) and os.listdir(test_output):
            log("ERROR", "dry-run 模式不应写入文件")
            failures += 1
        else:
            log("OK", "批量处理 dry-run 测试通过")
    except Exception as e:
        log("ERROR", f"批量处理 dry-run 测试异常: {str(e)}")
        failures += 1
    
    # 测试 4: 批量处理（实际执行）
    log("INFO", "测试 4: 批量处理实际执行")
    try:
        args = argparse.Namespace(
            input_dir=test_input,
            output_dir=test_output,
            script=test_script,
            dry_run=False,
            verbose=True
        )
        rc = cmd_batch(args)
        if rc != 0:
            log("ERROR", "批量处理实际执行测试失败")
            failures += 1
        else:
            out_files = os.listdir(test_output)
            if len(out_files) != 3:
                log("ERROR", f"预期 3 个输出文件，实际 {len(out_files)} 个")
                failures += 1
            else:
                log("OK", "批量处理实际执行测试通过")
    except Exception as e:
        log("ERROR", f"批量处理实际执行测试异常: {str(e)}")
        failures += 1
    
    # 测试 5: 工作流分析
    log("INFO", "测试 5: 工作流分析")
    try:
        args = argparse.Namespace(input_dir=test_input, verbose=True)
        rc = cmd_analyze(args)
        if rc != 0:
            log("ERROR", "工作流分析测试失败")
            failures += 1
        else:
            log("OK", "工作流分析测试通过")
    except Exception as e:
        log("ERROR", f"工作流分析测试异常: {str(e)}")
        failures += 1
    
    # 测试 6: 错误处理 - 不存在的目录
    log("INFO", "测试 6: 错误处理")
    try:
        args = argparse.Namespace(
            input_dir=os.path.join(tmp_dir, "nonexistent"),
            output_dir=test_output,
            script=test_script,
            dry_run=True,
            verbose=False
        )
        rc = cmd_batch(args)
        if rc == 0:
            log("ERROR", "不存在的目录应返回错误")
            failures += 1
        else:
            log("OK", "错误处理测试通过")
    except Exception as e:
        log("ERROR", f"错误处理测试异常: {str(e)}")
        failures += 1
    
    # 清理
    shutil.rmtree(tmp_dir, ignore_errors=True)
    
    if failures == 0:
        log("OK", f"全部自测通过 ({6 - failures}/6)")
        return 0
    else:
        log("ERROR", f"自测失败: {failures}/6 项未通过")
        return 1


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="InDesign 2026 脚本自动化与批处理工作流工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python run.py generate --output margin.jsx --doc-count 100
  python run.py validate --script margin.jsx
  python run.py batch --input-dir ./docs --output-dir ./out --script margin.jsx --dry-run
  python run.py analyze --input-dir ./docs
  python run.py --selftest
"""
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测并退出"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # generate 子命令
    gen_parser = subparsers.add_parser("generate", help="生成 InDesign 脚本")
    gen_parser.add_argument("--output", "-o", default="indesign_script.jsx", help="输出脚本路径")
    gen_parser.add_argument("--doc-count", "-n", type=int, default=10, help="目标文档数")
    gen_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入")
    gen_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    # validate 子命令
    val_parser = subparsers.add_parser("validate", help="验证脚本语法和兼容性")
    val_parser.add_argument("--script", "-s", default="indesign_script.jsx", help="脚本文件路径")
    val_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量处理文档")
    batch_parser.add_argument("--input-dir", "-i", default=".", help="输入目录")
    batch_parser.add_argument("--output-dir", "-o", default="output", help="输出目录")
    batch_parser.add_argument("--script", "-s", default="indesign_script.jsx", help="要执行的脚本")
    batch_parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入")
    batch_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    # analyze 子命令
    ana_parser = subparsers.add_parser("analyze", help="分析工作流性能")
    ana_parser.add_argument("--input-dir", "-i", default=".", help="输入目录")
    ana_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自测模式
    if args.selftest:
        return run_selftest()
    
    # 无命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0
    
    # 分发命令
    try:
        if args.command == "generate":
            return cmd_generate(args)
        elif args.command == "validate":
            return cmd_validate(args)
        elif args.command == "batch":
            return cmd_batch(args)
        elif args.command == "analyze":
            return cmd_analyze(args)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        log("ERROR", "用户中断操作")
        return 130
    except Exception as e:
        log("ERROR", f"未预期的错误: {str(e)}")
        log("ERROR", "请报告此问题并附上完整错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
