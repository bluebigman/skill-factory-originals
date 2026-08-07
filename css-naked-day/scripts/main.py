#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
css-naked-day - 样式剥离工具

在CSS裸奔日自动禁用全站样式，让网页回归纯HTML本色。
本脚本为 clean-room 独立实现，仅依据功能规格设计。

功能：
1. 样式剥离：移除 HTML 中全部样式规则，输出纯 HTML 结构
2. 关键信息保留：保留 <meta>、<title>、<link rel="icon">、<script> 等
3. 结构化输出：输出剥离后的 HTML 文件 + 剥离报告（JSON）
4. 置信度标注：对剥离不完整或存在歧义的部分输出 [需核实:字段名]
5. 批量处理：支持一次提交多个文件，按批次输出结果并汇总报告

用法示例：
    python main.py input.html -o output.html
    python main.py file1.html file2.html --batch
    python main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入内容不是有效的 HTML",
    "E003": "输出目录不存在或无法写入",
    "E004": "批量处理时未提供任何有效输入",
    "E005": "URL 格式无效或无法访问",
    "E006": "JSON 序列化失败",
    "E007": "参数组合无效",
    "E008": "内部处理异常",
    "E009": "输入为空",
    "E010": "文件编码不支持",
}


class StyleNakedError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心剥离逻辑
# ============================================================

# 需要保留的非样式关键标签
_KEEP_TAGS = {
    "meta", "title", "link", "script", "base", "noscript",
}


def _extract_strip_statistics(html_content: str) -> dict:
    """统计 HTML 中样式相关的元素数量"""
    stats = {
        "style_tags": len(re.findall(r"<style\b", html_content, re.IGNORECASE)),
        "link_stylesheets": len(re.findall(
            r'<link\b[^>]*rel=["\']stylesheet["\']', html_content, re.IGNORECASE
        )),
        "inline_style_attrs": len(re.findall(
            r'<[^>]+\sstyle\s*=', html_content, re.IGNORECASE
        )),
        "class_attrs": len(re.findall(
            r'<[^>]+\sclass\s*=', html_content, re.IGNORECASE
        )),
        "id_attrs": len(re.findall(
            r'<[^>]+\sid\s*=', html_content, re.IGNORECASE
        )),
    }
    return stats


def _strip_style_tags(html_content: str) -> str:
    """移除 <style> 标签及其内容"""
    return re.sub(
        r"<style\b[^>]*>.*?</style>",
        "",
        html_content,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _strip_link_stylesheets(html_content: str) -> str:
    """移除 <link rel="stylesheet"> 标签"""
    return re.sub(
        r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>',
        "",
        html_content,
        flags=re.IGNORECASE,
    )


def _strip_inline_style_attrs(html_content: str) -> str:
    """移除标签中的 style 属性（保留其他属性）"""
    # 使用回调函数保留标签其他部分
    def _remove_style_attr(match):
        tag = match.group(0)
        # 移除 style="..." 属性
        tag = re.sub(
            r'\s+style\s*=\s*("[^"]*"|\'[^\']*\')',
            "",
            tag,
            flags=re.IGNORECASE,
        )
        return tag

    # 匹配所有带 style 属性的标签
    return re.sub(
        r"<[^>]+\sstyle\s*=[^>]*>",
        _remove_style_attr,
        html_content,
        flags=re.IGNORECASE,
    )


def _strip_class_id_attrs(html_content: str) -> str:
    """移除 class 和 id 属性（这些是样式选择器钩子）"""
    def _remove_attrs(match):
        tag = match.group(0)
        # 移除 class="..." 属性
        tag = re.sub(
            r'\s+class\s*=\s*("[^"]*"|\'[^\']*\')',
            "",
            tag,
            flags=re.IGNORECASE,
        )
        # 移除 id="..." 属性（保留 id 用于锚点跳转，但规格说移除样式相关）
        # 注意：id 可能用于锚点，但这里按规格处理
        tag = re.sub(
            r'\s+id\s*=\s*("[^"]*"|\'[^\']*\')',
            "",
            tag,
            flags=re.IGNORECASE,
        )
        return tag

    return re.sub(
        r"<[^>]+(?:\s+class\s*=|\s+id\s*=)[^>]*>",
        _remove_attrs,
        html_content,
        flags=re.IGNORECASE,
    )


def _extract_uncertain_areas(html_content: str) -> list:
    """识别可能存在歧义或剥离不完整的区域"""
    uncertain = []
    
    # 检查是否有内联事件处理器（可能动态修改样式）
    if re.search(r"\son\w+\s*=", html_content, re.IGNORECASE):
        uncertain.append({
            "type": "inline_event_handler",
            "message": "检测到内联事件处理器，可能动态修改样式",
            "recommendation": "[需核实:inline_event_handler]",
        })
    
    # 检查是否有 data-* 属性可能用于样式控制
    if re.search(r"\sdata-[a-z-]+\s*=", html_content, re.IGNORECASE):
        uncertain.append({
            "type": "data_attributes",
            "message": "检测到 data-* 属性，可能被 JavaScript 用于样式控制",
            "recommendation": "[需核实:data_attributes]",
        })
    
    # 检查是否有 <font> 等过时标签
    if re.search(r"<font\b", html_content, re.IGNORECASE):
        uncertain.append({
            "type": "legacy_tags",
            "message": "检测到 <font> 等过时标签，可能包含样式信息",
            "recommendation": "[需核实:legacy_tags]",
        })
    
    return uncertain


def _validate_html(html_content: str) -> bool:
    """简单验证是否为有效的 HTML"""
    if not html_content or not html_content.strip():
        return False
    
    # 检查是否有基本的 HTML 结构标记
    has_tag = re.search(r"<[a-z!\/]", html_content, re.IGNORECASE)
    return bool(has_tag)


def strip_styles(html_content: str) -> dict:
    """
    核心剥离函数：从 HTML 中移除所有样式相关元素
    
    参数:
        html_content: 原始 HTML 字符串
    
    返回:
        dict: 包含剥离后的 HTML、统计信息和警告
    """
    if not html_content or not html_content.strip():
        raise StyleNakedError("E009", "输入为空")
    
    if not _validate_html(html_content):
        raise StyleNakedError("E002", "输入内容不是有效的 HTML")
    
    # 收集剥离前统计
    before_stats = _extract_strip_statistics(html_content)
    
    # 执行剥离
    stripped = html_content
    stripped = _strip_style_tags(stripped)
    stripped = _strip_link_stylesheets(stripped)
    stripped = _strip_inline_style_attrs(stripped)
    stripped = _strip_class_id_attrs(stripped)
    
    # 收集剥离后统计
    after_stats = _extract_strip_statistics(stripped)
    
    # 识别不确定区域
    uncertain_areas = _extract_uncertain_areas(stripped)
    
    # 计算剥离统计
    removed_count = {
        key: before_stats.get(key, 0) - after_stats.get(key, 0)
        for key in before_stats
    }
    
    result = {
        "stripped_html": stripped,
        "statistics": {
            "before": before_stats,
            "after": after_stats,
            "removed": removed_count,
        },
        "uncertain_areas": uncertain_areas,
        "timestamp": datetime.now().isoformat(),
        "tool": "css-naked-day",
        "version": "1.0.1",
    }
    
    return result


def process_file(input_path: str, output_path: str = None) -> dict:
    """
    处理单个 HTML 文件
    
    参数:
        input_path: 输入文件路径
        output_path: 输出文件路径（可选）
    
    返回:
        dict: 处理结果
    """
    input_file = Path(input_path)
    if not input_file.exists():
        raise StyleNakedError("E001", f"文件不存在: {input_path}")
    
    if not input_file.is_file():
        raise StyleNakedError("E001", f"不是文件: {input_path}")
    
    try:
        content = input_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise StyleNakedError("E010", f"文件编码不支持: {input_path}")
    except Exception as e:
        raise StyleNakedError("E008", f"读取文件失败: {e}")
    
    result = strip_styles(content)
    
    # 输出文件
    if output_path:
        output_file = Path(output_path)
        output_dir = output_file.parent
        if not output_dir.exists():
            raise StyleNakedError("E003", f"输出目录不存在: {output_dir}")
        try:
            output_file.write_text(result["stripped_html"], encoding="utf-8")
        except Exception as e:
            raise StyleNakedError("E008", f"写入文件失败: {e}")
    
    result["input_file"] = str(input_file)
    result["output_file"] = str(output_file) if output_path else None
    
    return result


def process_batch(input_paths: list, output_dir: str = None) -> dict:
    """
    批量处理多个 HTML 文件
    
    参数:
        input_paths: 输入文件路径列表
        output_dir: 输出目录（可选）
    
    返回:
        dict: 批量处理结果
    """
    if not input_paths:
        raise StyleNakedError("E004", "未提供任何输入文件")
    
    results = []
    errors = []
    
    for input_path in input_paths:
        try:
            output_path = None
            if output_dir:
                output_dir_path = Path(output_dir)
                if not output_dir_path.exists():
                    raise StyleNakedError("E003", f"输出目录不存在: {output_dir}")
                output_path = str(output_dir_path / f"stripped_{Path(input_path).name}")
            
            result = process_file(input_path, output_path)
            results.append({
                "success": True,
                "input": input_path,
                "output": output_path,
                "statistics": result["statistics"],
            })
        except StyleNakedError as e:
            errors.append({
                "success": False,
                "input": input_path,
                "error_code": e.code,
                "error_message": e.message,
            })
        except Exception as e:
            errors.append({
                "success": False,
                "input": input_path,
                "error_code": "E008",
                "error_message": str(e),
            })
    
    return {
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据离线验证核心逻辑
    
    返回:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("css-naked-day 自检开始")
    print("=" * 60)
    
    # 测试样例 1：包含各种样式元素的 HTML
    sample_html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>测试页面</title>
        <link rel="icon" href="/favicon.ico">
        <link rel="stylesheet" href="/css/main.css">
        <link rel="stylesheet" href="/css/theme.css">
        <style>
            body { font-family: Arial, sans-serif; }
            .container { max-width: 1200px; margin: 0 auto; }
            #header { background-color: #333; }
        </style>
        <script src="/js/app.js"></script>
    </head>
    <body>
        <div id="main" class="container">
            <h1 style="color: red; font-size: 24px;">欢迎</h1>
            <p class="intro" id="welcome">这是一个测试段落。</p>
            <p style="margin-top: 20px;">第二段内容。</p>
        </div>
    </body>
    </html>
    """
    
    print("\n[测试 1] 基本样式剥离")
    try:
        result = strip_styles(sample_html)
        stripped = result["stripped_html"]
        
        # 宽松断言：剥离后不应包含样式标签和样式表链接
        assert "<style" not in stripped.lower(), "剥离后仍包含 <style> 标签"
        assert 'rel="stylesheet"' not in stripped.lower(), "剥离后仍包含样式表链接"
        assert "style=" not in stripped.lower(), "剥离后仍包含 style 属性"
        
        # 应保留关键标签
        assert "<title>" in stripped.lower(), "标题被移除"
        assert "<meta" in stripped.lower(), "meta 标签被移除"
        assert "<script" in stripped.lower(), "script 标签被移除"
        assert 'rel="icon"' in stripped.lower(), "favicon 链接被移除"
        
        # 应保留文本内容
        assert "欢迎" in stripped, "文本内容丢失"
        assert "这是一个测试段落" in stripped, "段落内容丢失"
        
        # 统计信息应合理
        stats = result["statistics"]
        assert stats["removed"]["style_tags"] >= 1, "应至少移除 1 个 style 标签"
        assert stats["removed"]["link_stylesheets"] >= 2, "应至少移除 2 个样式表链接"
        assert stats["removed"]["inline_style_attrs"] >= 2, "应至少移除 2 个内联样式"
        
        print("  ✓ 基本剥离功能正常")
        print(f"  ✓ 移除统计: {stats['removed']}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except StyleNakedError as e:
        print(f"  ✗ 处理失败: {e}")
        return False
    
    # 测试样例 2：空输入
    print("\n[测试 2] 空输入处理")
    try:
        strip_styles("")
        print("  ✗ 空输入应该抛出异常")
        return False
    except StyleNakedError as e:
        assert e.code == "E009", "错误码应该是 E009"
        print("  ✓ 空输入正确抛出 E009")
    
    # 测试样例 3：无样式 HTML
    print("\n[测试 3] 无样式 HTML")
    try:
        plain_html = "<html><body><p>纯文本</p></body></html>"
        result = strip_styles(plain_html)
        assert "<p>纯文本</p>" in result["stripped_html"], "纯文本内容丢失"
        assert result["statistics"]["removed"]["style_tags"] == 0, "无样式时不应有移除"
        print("  ✓ 无样式 HTML 处理正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except StyleNakedError as e:
        print(f"  ✗ 处理失败: {e}")
        return False
    
    # 测试样例 4：文件处理
    print("\n[测试 4] 文件处理")
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(sample_html)
            temp_input = f.name
        
        temp_output = temp_input.replace(".html", "_stripped.html")
        
        result = process_file(temp_input, temp_output)
        
        assert result["output_file"] == temp_output, "输出文件路径不正确"
        assert Path(temp_output).exists(), "输出文件未创建"
        
        # 读取输出文件验证
        with open(temp_output, "r", encoding="utf-8") as f:
            output_content = f.read()
        assert "<style" not in output_content.lower(), "输出文件仍包含样式"
        assert "欢迎" in output_content, "输出文件内容缺失"
        
        # 清理
        os.unlink(temp_input)
        os.unlink(temp_output)
        
        print("  ✓ 文件处理正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except StyleNakedError as e:
        print(f"  ✗ 处理失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 意外错误: {e}")
        return False
    
    # 测试样例 5：批量处理
    print("\n[测试 5] 批量处理")
    try:
        # 创建两个临时文件
        temp_files = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(f"<html><head><style>body{{color:red}}</style></head><body><p>文件{i}</p></body></html>")
                temp_files.append(f.name)
        
        # 创建临时输出目录
        temp_output_dir = tempfile.mkdtemp()
        
        batch_result = process_batch(temp_files, temp_output_dir)
        
        assert batch_result["success_count"] == 2, "应成功处理 2 个文件"
        assert batch_result["error_count"] == 0, "不应有错误"
        
        # 检查输出文件
        for i, input_file in enumerate(temp_files):
            output_file = Path(temp_output_dir) / f"stripped_{Path(input_file).name}"
            assert output_file.exists(), f"输出文件 {output_file} 不存在"
            content = output_file.read_text(encoding="utf-8")
            assert f"文件{i}" in content, f"输出文件 {i} 内容不正确"
        
        # 清理
        for temp_file in temp_files:
            os.unlink(temp_file)
        for output_file in Path(temp_output_dir).glob("*"):
            os.unlink(output_file)
        os.rmdir(temp_output_dir)
        
        print("  ✓ 批量处理正常")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except StyleNakedError as e:
        print(f"  ✗ 处理失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 意外错误: {e}")
        return False
    
    # 测试样例 6：错误处理
    print("\n[测试 6] 错误处理")
    try:
        # 不存在的文件
        process_file("/nonexistent/path/file.html")
        print("  ✗ 应抛出 E001 错误")
        return False
    except StyleNakedError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print("  ✓ 不存在的文件正确抛出 E001")
    
    try:
        # 无效 HTML
        strip_styles("这不是 HTML")
        print("  ✗ 应抛出 E002 错误")
        return False
    except StyleNakedError as e:
        assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"
        print("  ✓ 无效 HTML 正确抛出 E002")
    
    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    """主函数：解析命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(
        description="css-naked-day - 样式剥离工具",
        epilog="示例: python main.py input.html -o output.html",
    )
    
    parser.add_argument(
        "inputs",
        nargs="*",
        help="输入 HTML 文件路径（支持多个用于批量处理）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径（单文件模式）",
    )
    parser.add_argument(
        "-d", "--output-dir",
        help="输出目录（批量模式）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（多个输入文件）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--report",
        help="输出 JSON 报告到指定文件",
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 参数验证
    if not args.inputs:
        parser.error("必须提供输入文件或使用 --selftest")
    
    try:
        # 批量模式
        if args.batch or len(args.inputs) > 1:
            if args.output:
                raise StyleNakedError("E007", "批量模式不能使用 -o/--output，请使用 -d/--output-dir")
            
            result = process_batch(args.inputs, args.output_dir)
            
            print(f"批量处理完成: 成功 {result['success_count']} 个, 失败 {result['error_count']} 个")
            
            for item in result["results"]:
                print(f"  ✓ {item['input']} -> {item['output']}")
            
            for item in result["errors"]:
                print(f"  ✗ {item['input']}: [{item['error_code']}] {item['error_message']}")
            
            # 输出报告
            if args.report:
                _write_report(result, args.report)
            
            # 如果有错误，返回非零退出码
            if result["error_count"] > 0:
                sys.exit(1)
        
        # 单文件模式
        else:
            if len(args.inputs) > 1:
                raise StyleNakedError("E007", "多个输入文件请使用 --batch 或指定输出目录")
            
            result = process_file(args.inputs[0], args.output)
            
            print(f"处理完成: {result['input_file']}")
            if result["output_file"]:
                print(f"输出文件: {result['output_file']}")
            else:
                # 无输出文件时打印剥离后的 HTML
                print("\n--- 剥离后的 HTML ---")
                print(result["stripped_html"])
                print("--- 结束 ---")
            
            print(f"\n统计信息:")
            for key, value in result["statistics"]["removed"].items():
                print(f"  {key}: 移除 {value} 个")
            
            if result["uncertain_areas"]:
                print(f"\n⚠️ 发现 {len(result['uncertain_areas'])} 个可能需要核实的区域:")
                for area in result["uncertain_areas"]:
                    print(f"  - {area['type']}: {area['recommendation']}")
            
            # 输出报告
            if args.report:
                _write_report(result, args.report)
    
    except StyleNakedError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


def _write_report(data: dict, report_path: str):
    """将数据写入 JSON 报告文件"""
    try:
        report_file = Path(report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"报告已写入: {report_path}")
    except Exception as e:
        raise StyleNakedError("E006", f"JSON 序列化失败: {e}")


if __name__ == "__main__":
    main()
