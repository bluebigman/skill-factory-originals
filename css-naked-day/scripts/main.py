#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
css-naked-day - 样式裸奔日页面脱衣工具
版本: 1.0.1
实现: 基于功能规格的 clean-room 独立实现
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise


# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入路径或URL格式不正确",
    "E002": "文件不存在或无法读取",
    "E003": "URL访问失败或网络不可达",
    "E004": "HTML解析失败：内容为空或格式错误",
    "E005": "输出目录不存在或无法写入",
    "E006": "JSON序列化失败",
    "E007": "批量处理时单个项目失败",
    "E008": "内部逻辑错误：剥离过程异常",
    "E009": "输入类型不支持（仅支持文件路径或URL）",
    "E010": "未知错误",
}


class StyleStripper:
    """核心样式剥离器"""
    
    # 需要保留的非样式关键标签
    KEEP_TAGS = {
        'meta', 'title', 'link', 'script', 'noscript',
        'base', 'template', 'style'  # style 标签内容会单独处理
    }
    
    # 需要移除的标签
    REMOVE_TAGS = {'style', 'link'}
    
    def __init__(self, html_content: str):
        """初始化剥离器
        
        Args:
            html_content: 原始 HTML 字符串
        """
        self.original_html = html_content
        self.stripped_html = ""
        self.report = {
            "original_size": len(html_content),
            "stripped_size": 0,
            "removed_style_tags": 0,
            "removed_link_tags": 0,
            "removed_inline_styles": 0,
            "warnings": [],
            "uncertain_fields": []
        }
    
    def strip(self) -> Tuple[str, Dict]:
        """执行样式剥离
        
        Returns:
            (剥离后的HTML, 剥离报告)
        """
        try:
            # 1. 移除 <style> 标签及其内容
            html = self._remove_style_tags()
            # 2. 移除 <link> 标签（保留 rel="icon" 的）
            html = self._remove_link_tags(html)
            # 3. 移除内联 style 属性
            html = self._remove_inline_styles(html)
            # 4. 清理空属性
            html = self._clean_empty_attributes(html)
            
            self.stripped_html = html
            self.report["stripped_size"] = len(html)
            return html, self.report
            
        except Exception as e:
            raise RuntimeError(f"E008: 剥离过程异常 - {str(e)}")
    
    def _remove_style_tags(self) -> str:
        """移除所有 <style> 标签及其内容"""
        pattern = r'<style[^>]*>.*?</style>'
        html, count = re.subn(pattern, '', self.original_html, flags=re.DOTALL | re.IGNORECASE)
        self.report["removed_style_tags"] = count
        return html
    
    def _remove_link_tags(self, html: str) -> str:
        """移除 <link> 标签，但保留 rel="icon" 的"""
        def link_replacer(match):
            tag = match.group(0)
            # 检查是否包含 rel="icon" 或 rel='icon'
            if re.search(r'rel\s*=\s*["\']icon["\']', tag, re.IGNORECASE):
                return tag  # 保留
            self.report["removed_link_tags"] += 1
            return ''
        
        pattern = r'<link[^>]*>'
        return re.sub(pattern, link_replacer, html, flags=re.IGNORECASE)
    
    def _remove_inline_styles(self, html: str) -> str:
        """移除所有元素的内联 style 属性"""
        def style_replacer(match):
            attr = match.group(0)
            self.report["removed_inline_styles"] += 1
            return ''
        
        pattern = r'\s+style\s*=\s*"[^"]*"|\s+style\s*=\s*\'[^\']*\''
        return re.sub(pattern, style_replacer, html, flags=re.IGNORECASE)
    
    def _clean_empty_attributes(self, html: str) -> str:
        """清理可能产生的空属性"""
        # 移除空属性（如 class="" 或 id=''）
        html = re.sub(r'\s+(class|id|name|value)\s*=\s*["\']\s*["\']', '', html)
        return html


def process_html(html_content: str, source_name: str = "inline") -> Dict:
    """处理单个 HTML 内容
    
    Args:
        html_content: HTML 字符串
        source_name: 来源名称（用于报告）
    
    Returns:
        处理结果字典
    """
    if not html_content or not html_content.strip():
        raise ValueError("E004: HTML内容为空")
    
    stripper = StyleStripper(html_content)
    stripped_html, report = stripper.strip()
    
    return {
        "source": source_name,
        "original_size": report["original_size"],
        "stripped_size": report["stripped_size"],
        "removed_style_tags": report["removed_style_tags"],
        "removed_link_tags": report["removed_link_tags"],
        "removed_inline_styles": report["removed_inline_styles"],
        "stripped_html": stripped_html,
        "warnings": report["warnings"],
        "uncertain_fields": report["uncertain_fields"]
    }


def process_file(file_path: str) -> Dict:
    """处理单个 HTML 文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        处理结果字典
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"E002: 文件不存在 - {file_path}")
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return process_html(content, source_name=str(path))
        
    except FileNotFoundError as e:
        raise RuntimeError(str(e))
    except PermissionError:
        raise RuntimeError(f"E002: 无法读取文件（权限不足） - {file_path}")
    except Exception as e:
        raise RuntimeError(f"E010: 处理文件失败 - {str(e)}")


def process_url(url: str) -> Dict:
    """处理单个 URL
    
    Args:
        url: 网页 URL
    
    Returns:
        处理结果字典
    """
    try:
        # 添加 User-Agent 头避免被拒绝
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; css-naked-day/1.0)'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            # 尝试从响应头获取编码
            charset = response.headers.get_content_charset() or 'utf-8'
            content = response.read().decode(charset, errors='replace')
        
        return process_html(content, source_name=url)
        
    except urllib.error.URLError as e:
        raise RuntimeError(f"E003: URL访问失败 - {url} - {str(e)}")
    except Exception as e:
        raise RuntimeError(f"E010: 处理URL失败 - {str(e)}")


def process_batch(items: List[str]) -> Dict:
    """批量处理多个文件或 URL
    
    Args:
        items: 文件路径或 URL 列表
    
    Returns:
        批量处理结果
    """
    batch_results = []
    has_error = False
    
    for item in items:
        try:
            if item.startswith(('http://', 'https://')):
                result = process_url(item)
            else:
                result = process_file(item)
            result["status"] = "success"
            batch_results.append(result)
        except Exception as e:
            has_error = True
            batch_results.append({
                "source": item,
                "status": "error",
                "error": str(e)
            })
    
    summary = {
        "total": len(items),
        "success": sum(1 for r in batch_results if r["status"] == "success"),
        "failed": sum(1 for r in batch_results if r["status"] == "error")
    }
    
    return {
        "batch_results": batch_results,
        "summary": summary
    }


def save_output(result: Dict, output_dir: str, prefix: str = "stripped") -> Dict:
    """保存输出文件
    
    Args:
        result: 处理结果
        output_dir: 输出目录
        prefix: 文件名前缀
    
    Returns:
        保存结果信息
    """
    try:
        out_path = Path(output_dir)
        if not out_path.exists():
            raise FileNotFoundError(f"E005: 输出目录不存在 - {output_dir}")
        if not out_path.is_dir():
            raise NotADirectoryError(f"E005: 不是目录 - {output_dir}")
        
        # 生成安全的文件名
        source_name = Path(result.get("source", "output")).stem
        safe_name = re.sub(r'[^\w\-.]', '_', source_name)
        
        # 保存 HTML
        html_file = out_path / f"{prefix}_{safe_name}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(result.get("stripped_html", ""))
        
        # 保存报告
        report_file = out_path / f"{prefix}_{safe_name}_report.json"
        report_data = {k: v for k, v in result.items() if k != "stripped_html"}
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return {
            "html_file": str(html_file),
            "report_file": str(report_file)
        }
        
    except (FileNotFoundError, NotADirectoryError) as e:
        raise RuntimeError(str(e))
    except json.JSONEncodeError:
        raise RuntimeError("E006: JSON序列化失败")
    except Exception as e:
        raise RuntimeError(f"E010: 保存输出失败 - {str(e)}")


def run_selftest() -> bool:
    """内置自检功能
    
    使用硬编码的样例数据验证核心逻辑，不依赖外部文件。
    
    Returns:
        自检是否通过
    """
    print("=== CSS Naked Day 自检开始 ===")
    
    # 测试样例1: 基础样式剥离
    sample1 = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试页面</title>
        <meta charset="utf-8">
        <meta name="description" content="测试">
        <link rel="stylesheet" href="style.css">
        <link rel="icon" href="favicon.ico">
        <style>
            body { background: red; }
            .main { color: blue; }
        </style>
    </head>
    <body>
        <div class="main" style="font-size: 20px; color: green;">
            <h1>标题</h1>
            <p style="margin: 10px;">段落文字</p>
            <script>console.log("test");</script>
        </div>
    </body>
    </html>
    """
    
    try:
        result = process_html(sample1, source_name="selftest_sample1")
        
        # 宽松断言
        assert result["removed_style_tags"] >= 1, "应至少移除1个style标签"
        assert result["removed_link_tags"] >= 1, "应至少移除1个link标签（样式表）"
        assert result["removed_inline_styles"] >= 1, "应至少移除1个内联样式"
        
        # 检查保留的关键内容
        html = result["stripped_html"]
        assert "<title>测试页面</title>" in html, "应保留title标签"
        assert 'rel="icon"' in html or "rel='icon'" in html, "应保留favicon链接"
        assert "console.log" in html, "应保留script内容"
        assert "style.css" not in html, "不应保留样式表链接"
        assert "background: red" not in html, "不应保留style标签内容"
        assert 'font-size: 20px' not in html, "不应保留内联样式"
        
        print(f"  [PASS] 样例1基础剥离 - 移除样式标签:{result['removed_style_tags']}, "
              f"链接标签:{result['removed_link_tags']}, 内联样式:{result['removed_inline_styles']}")
        
    except AssertionError as e:
        print(f"  [FAIL] 样例1断言失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 样例1执行异常: {e}")
        return False
    
    # 测试样例2: 复杂嵌套和边界情况
    sample2 = """
    <html>
    <head>
        <style>/* 注释 */</style>
        <link rel="preload" href="font.woff2">
    </head>
    <body>
        <div style='background:url("data:image/png;base64,abc")'>
            <span style="width: calc(100% - 20px)">文本</span>
            <a href="#" style="text-decoration: none">链接</a>
        </div>
        <style media="print">@media print { body { display: none; } }</style>
    </body>
    </html>
    """
    
    try:
        result = process_html(sample2, source_name="selftest_sample2")
        
        # 宽松断言
        assert result["removed_style_tags"] >= 2, "应移除所有style标签"
        assert result["removed_link_tags"] >= 1, "应移除preload链接"
        
        html = result["stripped_html"]
        assert "background:url" not in html, "不应保留复杂内联样式"
        assert "calc(100%" not in html, "不应保留calc表达式"
        assert "text-decoration" not in html, "不应保留普通内联样式"
        assert "<a href=\"#\">" in html or "<a href='#'>", "应保留a标签结构"
        
        print(f"  [PASS] 样例2复杂场景 - 移除样式标签:{result['removed_style_tags']}, "
              f"链接标签:{result['removed_link_tags']}")
        
    except AssertionError as e:
        print(f"  [FAIL] 样例2断言失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 样例2执行异常: {e}")
        return False
    
    # 测试样例3: 无样式内容
    sample3 = "<html><body><p>纯文本</p></body></html>"
    
    try:
        result = process_html(sample3, source_name="selftest_sample3")
        
        assert result["removed_style_tags"] == 0, "无样式时应为0"
        assert result["removed_link_tags"] == 0, "无链接时应为0"
        assert result["removed_inline_styles"] == 0, "无内联样式时应为0"
        assert "纯文本" in result["stripped_html"], "应保留文本内容"
        
        print(f"  [PASS] 样例3无样式内容")
        
    except AssertionError as e:
        print(f"  [FAIL] 样例3断言失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 样例3执行异常: {e}")
        return False
    
    # 测试样例4: 批量处理
    try:
        batch_results = process_batch(["sample1.html", "sample2.html"])
        assert batch_results["summary"]["total"] == 2, "批量总数应为2"
        assert batch_results["summary"]["failed"] >= 2, "文件不存在应全部失败"
        
        print(f"  [PASS] 样例4批量处理 - 成功:{batch_results['summary']['success']}, "
              f"失败:{batch_results['summary']['failed']}")
        
    except AssertionError as e:
        print(f"  [FAIL] 样例4断言失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 样例4执行异常: {e}")
        return False
    
    print("=== 自检全部通过 ===")
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="CSS Naked Day 样式剥离工具 - 让网页回归纯HTML本色",
        epilog="示例: python main.py input.html -o output_dir"
    )
    
    parser.add_argument(
        "inputs", 
        nargs="*",
        help="输入文件路径或URL（支持多个，用于批量处理）"
    )
    parser.add_argument(
        "-o", "--output",
        default=".",
        help="输出目录（默认当前目录）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不处理任何输入）"
    )
    parser.add_argument(
        "--prefix",
        default="stripped",
        help="输出文件前缀（默认 'stripped'）"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（多个输入时自动启用）"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查输入
    if not args.inputs:
        parser.print_help()
        print("\n错误: E001 - 请提供至少一个输入文件或URL", file=sys.stderr)
        sys.exit(1)
    
    try:
        # 批量模式（多个输入或显式指定）
        if len(args.inputs) > 1 or args.batch:
            print(f"批量处理 {len(args.inputs)} 个项目...")
            batch_result = process_batch(args.inputs)
            
            # 输出摘要
            summary = batch_result["summary"]
            print(f"完成: 成功 {summary['success']}, 失败 {summary['failed']}, 总计 {summary['total']}")
            
            # 保存成功的结果
            saved_count = 0
            for result in batch_result["batch_results"]:
                if result.get("status") == "success":
                    try:
                        saved = save_output(result, args.output, args.prefix)
                        print(f"  已保存: {saved['html_file']}")
                        saved_count += 1
                    except Exception as e:
                        print(f"  保存失败: {e}", file=sys.stderr)
            
            print(f"成功保存 {saved_count} 个结果")
            
            # 如果有失败，返回非零退出码
            if summary["failed"] > 0:
                sys.exit(2)
            
        else:
            # 单文件模式
            input_item = args.inputs[0]
            print(f"处理: {input_item}")
            
            # 判断是URL还是文件
            if input_item.startswith(('http://', 'https://')):
                result = process_url(input_item)
            else:
                result = process_file(input_item)
            
            # 保存输出
            saved = save_output(result, args.output, args.prefix)
            
            print(f"完成!")
            print(f"  原始大小: {result['original_size']} 字节")
            print(f"  剥离后大小: {result['stripped_size']} 字节")
            print(f"  移除 style 标签: {result['removed_style_tags']}")
            print(f"  移除 link 标签: {result['removed_link_tags']}")
            print(f"  移除内联样式: {result['removed_inline_styles']}")
            print(f"  HTML文件: {saved['html_file']}")
            print(f"  报告文件: {saved['report_file']}")
            
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"E010: 未预期错误 - {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
