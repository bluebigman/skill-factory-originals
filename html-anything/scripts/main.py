#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
html-anything - 数据转HTML多场景输出工具

功能：
- 将文本、CSV、JSON、URL内容转换为结构化HTML
- 支持表格、卡片、文章三种输出格式
- 支持批量输入与自定义标题
- 内置离线自检模式

仅依赖Python标准库，无第三方依赖。
"""

import argparse
import csv
import html
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用自定义异常，携带错误码"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 工具函数
# ============================================================
def _escape_text(text: str) -> str:
    """HTML转义文本内容"""
    return html.escape(str(text), quote=True)


def _detect_format(content: str, filename: str = "") -> str:
    """
    检测数据格式类型
    返回: 'csv' | 'json' | 'md' | 'text'
    """
    # 根据文件扩展名判断
    ext = Path(filename).suffix.lower()
    if ext in ('.csv',):
        return 'csv'
    if ext in ('.json',):
        return 'json'
    if ext in ('.md', '.markdown'):
        return 'md'

    # 根据内容特征判断
    stripped = content.strip()

    # JSON检测：以 { 或 [ 开头
    if stripped.startswith('{') or stripped.startswith('['):
        # 尝试解析，如果失败也返回json，让后续处理抛出异常
        try:
            json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            pass
        return 'json'

    # CSV检测：包含逗号且有多行
    if ',' in stripped and '\n' in stripped:
        # 尝试解析CSV
        try:
            sample = list(csv.reader(io.StringIO(stripped)))
            # 至少2行且每行列数一致
            if len(sample) >= 2 and len(set(len(row) for row in sample)) == 1:
                return 'csv'
        except Exception:
            pass

    # Markdown检测
    if stripped.startswith('#') or ('**' in stripped and '\n' in stripped):
        return 'md'

    return 'text'


def _extract_fields(data: Dict[str, Any], parent_key: str = "") -> List[Tuple[str, str]]:
    """
    递归提取JSON中的字段键值对
    返回 [(字段名, 值字符串), ...]
    """
    fields: List[Tuple[str, str]] = []
    for key, value in data.items():
        full_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            # 嵌套对象递归展开
            nested = _extract_fields(value, full_key)
            fields.extend(nested)
        elif isinstance(value, list):
            # 列表转为JSON字符串
            fields.append((full_key, json.dumps(value, ensure_ascii=False)))
        else:
            fields.append((full_key, str(value)))
    return fields


def _parse_json_data(content: str) -> List[Dict[str, Any]]:
    """解析JSON内容为记录列表"""
    data = json.loads(content)
    if isinstance(data, list):
        # 列表形式：每个元素是一条记录
        records = []
        for item in data:
            if isinstance(item, dict):
                records.append(item)
            else:
                records.append({"value": item})
        return records
    elif isinstance(data, dict):
        # 对象形式：检查是否包含列表字段
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
        # 单个对象作为一条记录
        return [data]
    return []


def _parse_csv_data(content: str) -> List[Dict[str, str]]:
    """解析CSV内容为字典列表"""
    reader = csv.DictReader(io.StringIO(content))
    return [dict(row) for row in reader]


def _parse_md_data(content: str) -> Dict[str, Any]:
    """简单解析Markdown，提取标题和正文"""
    lines = content.strip().split('\n')
    title = "Markdown 文档"
    body_lines = []

    for line in lines:
        if line.startswith('# '):
            title = line[2:].strip()
        else:
            body_lines.append(line)

    return {
        "title": title,
        "content": '\n'.join(body_lines)
    }


# ============================================================
# HTML生成器
# ============================================================
def _generate_table_html(records: List[Dict[str, Any]], title: str) -> str:
    """生成表格HTML"""
    if not records:
        return f"<html><body><h1>{_escape_text(title)}</h1><p>无数据</p></body></html>"

    # 收集所有字段名
    field_names: List[str] = []
    for record in records:
        for key in record.keys():
            if key not in field_names:
                field_names.append(key)

    # 构建表格
    parts = [
        "<!DOCTYPE html>",
        "<html lang=\"zh-CN\">",
        "<head>",
        "<meta charset=\"UTF-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        f"<title>{_escape_text(title)}</title>",
        "<style>",
        "body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; }",
        "h1 { color: #333; text-align: center; }",
        "table { width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }",
        "th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }",
        "th { background: #4CAF50; color: white; }",
        "tr:hover { background: #f5f5f5; }",
        ".container { max-width: 1200px; margin: 0 auto; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class=\"container\">",
        f"<h1>{_escape_text(title)}</h1>",
        "<table>",
        "<thead><tr>"
    ]

    # 表头
    for field in field_names:
        parts.append(f"<th>{_escape_text(field)}</th>")
    parts.append("</tr></thead><tbody>")

    # 数据行
    for record in records:
        parts.append("<tr>")
        for field in field_names:
            value = record.get(field, "")
            parts.append(f"<td>{_escape_text(value)}</td>")
        parts.append("</tr>")

    parts.append("</tbody></table></div></body></html>")
    return '\n'.join(parts)


def _generate_card_html(records: List[Dict[str, Any]], title: str) -> str:
    """生成卡片HTML"""
    if not records:
        return f"<html><body><h1>{_escape_text(title)}</h1><p>无数据</p></body></html>"

    parts = [
        "<!DOCTYPE html>",
        "<html lang=\"zh-CN\">",
        "<head>",
        "<meta charset=\"UTF-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        f"<title>{_escape_text(title)}</title>",
        "<style>",
        "body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f0f2f5; }",
        "h1 { color: #333; text-align: center; margin-bottom: 30px; }",
        ".card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }",
        ".card { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); transition: transform 0.2s; }",
        ".card:hover { transform: translateY(-4px); box-shadow: 0 4px 20px rgba(0,0,0,0.15); }",
        ".card h3 { color: #1890ff; margin: 0 0 15px 0; border-bottom: 2px solid #e8e8e8; padding-bottom: 10px; }",
        ".field { margin-bottom: 8px; font-size: 14px; color: #666; }",
        ".field span { color: #333; font-weight: 500; }",
        ".field-name { color: #999; margin-right: 8px; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{_escape_text(title)}</h1>",
        "<div class=\"card-grid\">"
    ]

    # 生成卡片
    for idx, record in enumerate(records, 1):
        parts.append("<div class=\"card\">")
        # 卡片标题：优先取第一个字段
        first_key = next(iter(record.keys()), "记录")
        first_val = record.get(first_key, f"记录 {idx}")
        parts.append(f"<h3>{_escape_text(first_val)}</h3>")

        # 剩余字段
        for key, value in record.items():
            if key == first_key:
                continue
            parts.append(
                f"<div class=\"field\"><span class=\"field-name\">{_escape_text(key)}:</span>"
                f"<span>{_escape_text(value)}</span></div>"
            )
        parts.append("</div>")

    parts.append("</div></body></html>")
    return '\n'.join(parts)


def _generate_article_html(data: Dict[str, Any], title: str) -> str:
    """生成文章HTML"""
    content = data.get("content", data.get("text", ""))
    if not content and data:
        # 尝试将数据转为文本
        content = json.dumps(data, ensure_ascii=False, indent=2)

    parts = [
        "<!DOCTYPE html>",
        "<html lang=\"zh-CN\">",
        "<head>",
        "<meta charset=\"UTF-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        f"<title>{_escape_text(title)}</title>",
        "<style>",
        "body { font-family: 'Georgia', 'Times New Roman', serif; margin: 0; padding: 20px; background: #fafafa; }",
        ".article { max-width: 800px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 4px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }",
        "h1 { color: #1a1a1a; font-size: 28px; margin-bottom: 20px; }",
        "p { line-height: 1.8; color: #444; font-size: 16px; }",
        "hr { border: none; border-top: 1px solid #eee; margin: 30px 0; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class=\"article\">",
        f"<h1>{_escape_text(title)}</h1>",
        "<hr>"
    ]

    # 正文段落
    paragraphs = str(content).split('\n')
    for para in paragraphs:
        para = para.strip()
        if para:
            parts.append(f"<p>{_escape_text(para)}</p>")

    parts.append("</div></body></html>")
    return '\n'.join(parts)


# ============================================================
# 核心转换逻辑
# ============================================================
def convert_data(
    content: str,
    output_format: str = "auto",
    title: str = "数据展示",
    filename: str = "",
    source_type: str = "text"
) -> str:
    """
    将输入内容转换为HTML

    参数:
        content: 原始内容字符串
        output_format: 输出格式 'table' | 'card' | 'article' | 'auto'
        title: HTML页面标题
        filename: 源文件名（用于格式检测）
        source_type: 输入类型 'text' | 'file' | 'url'

    返回:
        HTML字符串

    错误码:
        E001: 输入内容为空
        E002: 内容格式无法识别
        E003: 输出格式无效
        E004: JSON解析失败
        E005: CSV解析失败
    """
    if not content or not content.strip():
        raise AppError("E001", "输入内容为空")

    # 检测数据格式
    data_format = _detect_format(content, filename)

    # 确定输出格式
    if output_format == "auto":
        if data_format == "json":
            output_format = "card"
        elif data_format == "csv":
            output_format = "table"
        else:
            output_format = "article"

    if output_format not in ("table", "card", "article"):
        raise AppError("E003", f"无效的输出格式: {output_format}")

    # 解析数据
    try:
        if data_format == "json":
            records = _parse_json_data(content)
            if output_format == "article" and records:
                # 文章模式：取第一条记录
                article_data = records[0] if records else {}
                return _generate_article_html(article_data, title)
            return _generate_card_html(records, title) if output_format == "card" else _generate_table_html(records, title)

        elif data_format == "csv":
            records = _parse_csv_data(content)
            if output_format == "card":
                return _generate_card_html(records, title)
            elif output_format == "table":
                return _generate_table_html(records, title)
            else:
                # CSV转文章：转为文本
                article_data = {"content": content}
                return _generate_article_html(article_data, title)

        elif data_format == "md":
            md_data = _parse_md_data(content)
            return _generate_article_html(md_data, title)

        else:
            # 纯文本
            text_data = {"content": content}
            return _generate_article_html(text_data, title)

    except json.JSONDecodeError as e:
        raise AppError("E004", f"JSON解析失败: {str(e)}")
    except csv.Error as e:
        raise AppError("E005", f"CSV解析失败: {str(e)}")
    except Exception as e:
        raise AppError("E006", f"数据转换失败: {str(e)}")


def convert_file(
    file_path: str,
    output_format: str = "auto",
    title: str = ""
) -> str:
    """
    从文件读取内容并转换为HTML

    参数:
        file_path: 文件路径
        output_format: 输出格式
        title: 页面标题（默认使用文件名）

    错误码:
        E007: 文件不存在
        E008: 文件读取失败
    """
    path = Path(file_path)
    if not path.exists():
        raise AppError("E007", f"文件不存在: {file_path}")
    if not path.is_file():
        raise AppError("E008", f"不是有效文件: {file_path}")

    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            content = path.read_text(encoding='gbk')
        except Exception as e:
            raise AppError("E008", f"文件读取失败(编码问题): {str(e)}")
    except Exception as e:
        raise AppError("E008", f"文件读取失败: {str(e)}")

    if not title:
        title = path.stem

    return convert_data(
        content,
        output_format=output_format,
        title=title,
        filename=path.name,
        source_type="file"
    )


def convert_url(
    url: str,
    output_format: str = "auto",
    title: str = ""
) -> str:
    """
    从URL获取内容并转换为HTML

    参数:
        url: 网页URL
        output_format: 输出格式
        title: 页面标题

    错误码:
        E009: URL访问失败
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; html-anything/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        raise AppError("E009", f"URL访问失败: {str(e)}")

    if not title:
        title = url

    return convert_data(
        content,
        output_format=output_format,
        title=title,
        source_type="url"
    )


# ============================================================
# 自检函数
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑
    使用内置硬编码样例数据，不依赖外部环境
    """
    print("=" * 60)
    print("html-anything 自检开始")
    print("=" * 60)

    # ---------- 测试1: CSV转表格 ----------
    print("\n[测试1] CSV转表格")
    csv_data = """姓名,年龄,城市,职业
张三,28,北京,工程师
李四,35,上海,设计师
王五,42,深圳,产品经理
赵六,31,杭州,数据分析师"""
    try:
        html_result = convert_data(csv_data, output_format="table", title="团队成员")
        # 宽松断言：包含关键标签
        assert "<table" in html_result, "缺少table标签"
        assert "张三" in html_result, "缺少数据内容"
        assert "团队成员" in html_result, "缺少标题"
        assert html_result.count("<tr>") >= 3, "行数不足"
        print("  ✓ CSV转表格成功")
    except Exception as e:
        print(f"  ✗ CSV转表格失败: {e}")
        return False

    # ---------- 测试2: JSON转卡片 ----------
    print("\n[测试2] JSON转卡片")
    json_data = json.dumps([
        {"id": 1, "name": "产品A", "price": 99.9, "description": "高质量产品"},
        {"id": 2, "name": "产品B", "price": 199.9, "description": "旗舰产品"},
        {"id": 3, "name": "产品C", "price": 59.9, "description": "入门产品"}
    ], ensure_ascii=False)
    try:
        html_result = convert_data(json_data, output_format="card", title="产品列表")
        assert "card" in html_result, "缺少card样式"
        assert "产品A" in html_result, "缺少产品A"
        assert "产品C" in html_result, "缺少产品C"
        assert "card-grid" in html_result, "缺少网格布局"
        print("  ✓ JSON转卡片成功")
    except Exception as e:
        print(f"  ✗ JSON转卡片失败: {e}")
        return False

    # ---------- 测试3: 纯文本转文章 ----------
    print("\n[测试3] 纯文本转文章")
    text_data = """这是一个测试标题

这是第一段内容，用于测试文章生成功能。
这是第二段内容，包含一些示例文本。"""
    try:
        html_result = convert_data(text_data, output_format="article", title="测试文章")
        assert "<p>" in html_result, "缺少段落标签"
        assert "测试标题" in html_result or "测试文章" in html_result, "缺少标题内容"
        assert "第一段内容" in html_result, "缺少正文内容"
        print("  ✓ 文本转文章成功")
    except Exception as e:
        print(f"  ✗ 文本转文章失败: {e}")
        return False

    # ---------- 测试4: 自动格式检测 ----------
    print("\n[测试4] 自动格式检测")
    try:
        # JSON自动检测
        result_json = convert_data('{"name":"test","value":123}', title="自动检测")
        assert result_json and len(result_json) > 100, "JSON自动检测结果异常"

        # CSV自动检测
        result_csv = convert_data("a,b\n1,2\n3,4", title="CSV自动检测")
        assert "<table" in result_csv, "CSV自动检测未识别为表格"

        # 文本自动检测
        result_text = convert_data("纯文本内容测试", title="文本自动检测")
        assert "<p>" in result_text, "文本自动检测未识别为文章"

        print("  ✓ 自动格式检测成功")
    except Exception as e:
        print(f"  ✗ 自动格式检测失败: {e}")
        return False

    # ---------- 测试5: 错误处理 ----------
    print("\n[测试5] 错误处理")
    try:
        # 空内容
        try:
            convert_data("", title="空测试")
            print("  ✗ 空内容未抛出异常")
            return False
        except AppError as e:
            assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
            print("  ✓ 空内容错误处理正确")

        # 无效格式
        try:
            convert_data("测试内容", output_format="invalid", title="无效格式")
            print("  ✗ 无效格式未抛出异常")
            return False
        except AppError as e:
            assert e.code == "E003", f"错误码应为E003，实际为{e.code}"
            print("  ✓ 无效格式错误处理正确")

        # 无效JSON
        try:
            convert_data("{invalid json", title="坏JSON")
            print("  ✗ 坏JSON未抛出异常")
            return False
        except AppError as e:
            assert e.code in ("E004", "E006"), f"错误码应为E004或E006，实际为{e.code}"
            print("  ✓ 坏JSON错误处理正确")

    except Exception as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        return False

    # ---------- 测试6: 批量处理 ----------
    print("\n[测试6] 批量处理")
    try:
        records = [
            {"name": "项目1", "status": "进行中", "progress": 60},
            {"name": "项目2", "status": "已完成", "progress": 100},
            {"name": "项目3", "status": "规划中", "progress": 10}
        ]
        html_result = convert_data(json.dumps(records), output_format="table", title="项目进度")
        assert "项目1" in html_result and "项目3" in html_result, "批量数据不完整"
        assert "进行中" in html_result and "规划中" in html_result, "状态数据缺失"
        print("  ✓ 批量处理成功")
    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        return False

    # ---------- 测试7: HTML转义 ----------
    print("\n[测试7] HTML转义")
    try:
        malicious = "<script>alert('xss')</script>"
        html_result = convert_data(malicious, title="安全测试")
        assert "<script>" not in html_result, "未转义危险内容"
        print("  ✓ HTML转义正确")
    except Exception as e:
        print(f"  ✗ HTML转义测试失败: {e}")
        return False

    # ---------- 测试8: 文件读取 ----------
    print("\n[测试8] 文件读取")
    try:
        import tempfile
        import os

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("id,name\n1,测试1\n2,测试2")
            tmp_path = f.name

        try:
            result = convert_file(tmp_path, title="临时文件")
            assert "测试1" in result, "文件内容未正确读取"
            print("  ✓ 文件读取成功")
        finally:
            # 清理临时文件
            os.unlink(tmp_path)

        # 不存在的文件
        try:
            convert_file("/nonexistent/file.csv")
            print("  ✗ 不存在文件未抛出异常")
            return False
        except AppError as e:
            assert e.code == "E007", f"错误码应为E007，实际为{e.code}"
            print("  ✓ 文件不存在错误处理正确")

    except Exception as e:
        print(f"  ✗ 文件读取测试失败: {e}")
        return False

    # ---------- 测试9: 复杂JSON结构 ----------
    print("\n[测试9] 复杂JSON结构")
    try:
        complex_json = {
            "project": "数据平台",
            "version": "2.0",
            "modules": [
                {"name": "采集", "status": "稳定"},
                {"name": "处理", "status": "开发中"},
                {"name": "展示", "status": "测试中"}
            ],
            "metadata": {
                "owner": "数据组",
                "created": "2026-01-01",
                "tags": ["bigdata", "analytics"]
            }
        }
        html_result = convert_data(json.dumps(complex_json, ensure_ascii=False), title="复杂结构")
        assert "数据平台" in html_result, "嵌套数据未解析"
        assert "采集" in html_result, "列表数据未解析"
        print("  ✓ 复杂JSON处理成功")
    except Exception as e:
        print(f"  ✗ 复杂JSON处理失败: {e}")
        return False

    # ---------- 测试10: 空数据边界 ----------
    print("\n[测试10] 空数据边界")
    try:
        # 空JSON数组
        html_result = convert_data("[]", title="空数组")
        assert html_result and "无数据" in html_result, "空数组处理异常"

        # 空CSV
        html_result = convert_data("", title="空CSV")
        assert html_result, "空CSV处理异常"

        print("  ✓ 空数据边界处理正常")
    except Exception as e:
        print(f"  ✗ 空数据边界测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有自检测试通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="html-anything: 数据转HTML多场景输出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --text "姓名,年龄\\n张三,28" --format table --title "人员表"
  %(prog)s --file data.csv --format card --title "数据卡片"
  %(prog)s --url https://example.com --format article
  %(prog)s --selftest
        """
    )

    # 输入源（三选一）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text", help="直接输入文本内容")
    input_group.add_argument("--file", help="从文件读取内容")
    input_group.add_argument("--url", help="从URL获取内容")
    input_group.add_argument("--selftest", action="store_true", help="运行离线自检")

    # 输出选项
    parser.add_argument("--format", choices=["table", "card", "article", "auto"],
                        default="auto", help="输出格式（默认auto自动检测）")
    parser.add_argument("--title", default="数据展示", help="HTML页面标题")

    # 输出方式
    parser.add_argument("--output", "-o", help="输出到文件（默认输出到stdout）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    try:
        if args.text:
            html_result = convert_data(args.text, output_format=args.format, title=args.title)
        elif args.file:
            html_result = convert_file(args.file, output_format=args.format, title=args.title)
        elif args.url:
            html_result = convert_url(args.url, output_format=args.format, title=args.title)
        else:
            parser.error("必须指定 --text、--file、--url 或 --selftest 之一")

        # 输出结果
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_result, encoding='utf-8')
            print(f"HTML已保存到: {output_path}")
        else:
            print(html_result)

        return 0

    except AppError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 E010: 未预期的异常: {str(e)}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
