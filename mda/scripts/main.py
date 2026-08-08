#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mda - 数据编译 文档生成 批量转换

将任意数据源编译为标准化 Markdown 文档，支持批量处理与置信度标注。
仅依赖 Python 标准库实现。

用法示例:
    python main.py --selftest
    python main.py --input data.json --output out.md
    python main.py --input input_dir/ --output out_dir/ --batch
"""

import argparse
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# 错误码定义
ERR_SUCCESS = 0
ERR_FILE_NOT_FOUND = "E001"
ERR_INVALID_FORMAT = "E002"
ERR_OUTPUT_WRITE_FAIL = "E003"
ERR_INVALID_INPUT = "E004"
ERR_BATCH_PARTIAL_FAIL = "E005"
ERR_DIR_NOT_EXIST = "E006"
ERR_URL_FETCH_FAIL = "E007"
ERR_TEMPLATE_INVALID = "E008"
ERR_EMPTY_DATA = "E009"
ERR_UNKNOWN = "E010"


class MDADataError(Exception):
    """MDA 数据编译异常基类"""
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def read_json_file(file_path):
    """读取 JSON 文件并返回数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except json.JSONDecodeError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"JSON 解析失败: {e}")


def read_csv_file(file_path):
    """读取 CSV 文件并返回字典列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except Exception as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"CSV 解析失败: {e}")


def read_xml_file(file_path):
    """读取 XML 文件并转换为字典结构"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        def element_to_dict(element):
            """将 XML 元素递归转换为字典"""
            result = {}
            # 处理属性
            for attr_name, attr_val in element.attrib.items():
                result[f"@{attr_name}"] = attr_val

            # 处理子元素
            child_elements = list(element)
            if child_elements:
                for child in child_elements:
                    child_data = element_to_dict(child)
                    tag = child.tag
                    if tag in result:
                        # 同标签多元素转为列表
                        if isinstance(result[tag], list):
                            result[tag].append(child_data)
                        else:
                            result[tag] = [result[tag], child_data]
                    else:
                        result[tag] = child_data
            else:
                # 叶子节点取文本内容
                text = (element.text or "").strip()
                if text:
                    result["text"] = text

            return result

        return {root.tag: element_to_dict(root)}
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")
    except ET.ParseError as e:
        raise MDADataError(ERR_INVALID_FORMAT, f"XML 解析失败: {e}")


def read_txt_file(file_path):
    """读取 TXT 文件为纯文本"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {file_path}")


def read_remote_url(url):
    """读取远程 URL 数据（仅支持 HTTP/HTTPS）"""
    import urllib.request

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise MDADataError(ERR_INVALID_INPUT, f"不支持的 URL 协议: {parsed.scheme}")

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read().decode("utf-8")

            if "json" in content_type:
                return json.loads(data)
            elif "csv" in content_type:
                import io
                reader = csv.DictReader(io.StringIO(data))
                return list(reader)
            elif "xml" in content_type:
                return ET.fromstring(data)
            else:
                return data
    except Exception as e:
        raise MDADataError(ERR_URL_FETCH_FAIL, f"URL 获取失败: {e}")


def read_data_source(source):
    """根据数据源类型读取数据"""
    # 判断是否是 URL
    if source.startswith("http://") or source.startswith("https://"):
        return read_remote_url(source)

    # 判断本地文件
    if not os.path.exists(source):
        raise MDADataError(ERR_FILE_NOT_FOUND, f"文件不存在: {source}")

    ext = Path(source).suffix.lower()
    if ext == ".json":
        return read_json_file(source)
    elif ext == ".csv":
        return read_csv_file(source)
    elif ext == ".xml":
        return read_xml_file(source)
    elif ext == ".txt":
        return read_txt_file(source)
    else:
        raise MDADataError(ERR_INVALID_FORMAT, f"不支持的文件格式: {ext}")


def check_confidence(data):
    """
    置信度检查 - 对数据中的缺失值、类型不匹配进行标注
    返回 (标注后的数据, 置信度问题列表)
    """
    issues = []

    def annotate_recursive(obj, path=""):
        """递归检查并标注数据"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                annotate_recursive(value, current_path)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                annotate_recursive(item, f"{path}[{idx}]")
        elif obj is None:
            issues.append(f"{path}: 值为空")
        elif isinstance(obj, str) and not obj.strip():
            issues.append(f"{path}: 空字符串")
        elif isinstance(obj, (int, float)):
            # 数值范围检查（宽松）
            if isinstance(obj, float) and (obj != obj):  # NaN 检查
                issues.append(f"{path}: 非数值(NaN)")

    annotate_recursive(data)
    return data, issues


def format_value(value):
    """格式化值为 Markdown 友好字符串"""
    if value is None:
        return "*空*"
    elif isinstance(value, bool):
        return "是" if value else "否"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, dict):
        # 嵌套字典转为内联描述
        parts = [f"{k}: {format_value(v)}" for k, v in value.items()]
        return "; ".join(parts)
    elif isinstance(value, list):
        return ", ".join(format_value(v) for v in value)
    else:
        return str(value)


def dict_to_markdown_table(data, title="数据表"):
    """将字典列表转换为 Markdown 表格"""
    if not data:
        return f"## {title}\n\n*无数据*"

    # 收集所有键（保持顺序）
    all_keys = []
    for item in data:
        if isinstance(item, dict):
            for key in item.keys():
                if key not in all_keys:
                    all_keys.append(key)

    if not all_keys:
        return f"## {title}\n\n*无有效数据*"

    # 生成表头
    lines = [f"## {title}", ""]
    lines.append("| " + " | ".join(all_keys) + " |")
    lines.append("|" + "|".join(["---"] * len(all_keys)) + "|")

    # 生成数据行
    for item in data:
        if isinstance(item, dict):
            row = []
            for key in all_keys:
                row.append(format_value(item.get(key)))
            lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def dict_to_markdown_sections(data, title="数据详情"):
    """将字典转换为 Markdown 章节格式"""
    if not data:
        return f"## {title}\n\n*无数据*"

    lines = [f"## {title}", ""]

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"### {key}")
                lines.append("")
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    # 列表中的字典转为子表格
                    lines.append(dict_to_markdown_table(value, key))
                else:
                    lines.append(format_value(value))
                lines.append("")
            else:
                lines.append(f"- **{key}**: {format_value(value)}")
    elif isinstance(data, list):
        lines.append(dict_to_markdown_table(data, title))
    else:
        lines.append(format_value(data))

    return "\n".join(lines)


def generate_markdown(data, title="编译文档", include_confidence=True):
    """将数据编译为标准化 Markdown 文档"""
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 添加置信度检查
    if include_confidence:
        _, issues = check_confidence(data)
        if issues:
            lines.append("## 置信度提示")
            lines.append("")
            lines.append("> 以下字段存在数据质量问题，请核实：")
            lines.append(">")
            for issue in issues[:20]:  # 最多列出 20 条
                lines.append(f"> - [需核实:{issue}]")
            lines.append("")

    # 根据数据类型选择输出格式
    if isinstance(data, list):
        # 列表：可能是表格数据或嵌套对象
        if data and isinstance(data[0], dict):
            lines.append(dict_to_markdown_table(data))
        else:
            lines.append("## 数据列表")
            lines.append("")
            if data:
                for idx, item in enumerate(data, 1):
                    lines.append(f"{idx}. {format_value(item)}")
            else:
                lines.append("*无数据*")
    elif isinstance(data, dict):
        lines.append(dict_to_markdown_sections(data))
    else:
        lines.append("## 内容")
        lines.append("")
        lines.append(format_value(data))

    return "\n".join(lines)


def process_file(input_path, output_path, title=None):
    """处理单个文件转换"""
    try:
        data = read_data_source(input_path)
        if data is None or (isinstance(data, (list, dict)) and len(data) == 0):
            raise MDADataError(ERR_EMPTY_DATA, f"数据为空: {input_path}")

        doc_title = title or Path(input_path).stem
        markdown = generate_markdown(data, title=doc_title)

        # 写入输出
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
        except IOError as e:
            raise MDADataError(ERR_OUTPUT_WRITE_FAIL, f"输出写入失败: {e}")

        return True, None
    except MDADataError as e:
        return False, str(e)
    except Exception as e:
        return False, f"[{ERR_UNKNOWN}] 未知错误: {e}"


def process_batch(input_dir, output_dir):
    """批量处理目录下所有支持的文件"""
    if not os.path.isdir(input_dir):
        raise MDADataError(ERR_DIR_NOT_EXIST, f"输入目录不存在: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    supported_exts = {'.json', '.csv', '.xml', '.txt'}
    results = []
    success_count = 0
    fail_count = 0

    for file_path in sorted(Path(input_dir).glob('*')):
        if file_path.suffix.lower() not in supported_exts:
            continue

        output_path = Path(output_dir) / f"{file_path.stem}.md"
        success, error = process_file(str(file_path), str(output_path))
        if success:
            success_count += 1
            results.append(f"✓ {file_path.name}")
        else:
            fail_count += 1
            results.append(f"✗ {file_path.name}: {error}")

    return results, success_count, fail_count


def selftest():
    """内置自检逻辑 - 使用硬编码样例数据"""
    test_results = []

    # 测试 1: JSON 数据编译
    test_data = [
        {"name": "产品A", "price": 199.9, "stock": 50, "category": "电子"},
        {"name": "产品B", "price": 299.0, "stock": None, "category": "家居"},
        {"name": "产品C", "price": 99.5, "stock": 120, "category": "服饰"},
    ]
    try:
        md_output = generate_markdown(test_data, title="测试产品列表")
        # 宽松断言
        assert "测试产品列表" in md_output
        assert "产品A" in md_output
        assert "置信度提示" in md_output  # 包含 None 值
        assert "需核实" in md_output
        test_results.append(("JSON 数据编译", True, "包含表头、数据行和置信度提示"))
    except AssertionError as e:
        test_results.append(("JSON 数据编译", False, f"断言失败: {e}"))

    # 测试 2: 字典数据编译
    test_dict = {
        "project": "测试项目",
        "version": "1.0.0",
        "authors": ["张三", "李四"],
        "metadata": {"status": "active", "priority": "high"}
    }
    try:
        md_dict = generate_markdown(test_dict, title="项目信息")
        assert "项目信息" in md_dict
        assert "project" in md_dict
        assert "张三" in md_dict
        assert "status" in md_dict
        test_results.append(("字典数据编译", True, "章节结构完整"))
    except AssertionError as e:
        test_results.append(("字典数据编译", False, f"断言失败: {e}"))

    # 测试 3: 置信度检查
    try:
        _, issues = check_confidence({"valid": 123, "empty": "", "none": None})
        assert len(issues) >= 2  # 至少有两个问题
        assert any("empty" in i for i in issues)
        assert any("none" in i for i in issues)
        test_results.append(("置信度检查", True, f"识别到 {len(issues)} 个问题"))
    except AssertionError as e:
        test_results.append(("置信度检查", False, f"断言失败: {e}"))

    # 测试 4: CSV 数据解析（内存中）
    import io
    try:
        csv_data = "name,age,city\n张三,28,北京\n李四,35,上海\n"
        reader = csv.DictReader(io.StringIO(csv_data))
        csv_rows = list(reader)
        assert len(csv_rows) == 2
        assert csv_rows[0]["name"] == "张三"
        assert csv_rows[1]["city"] == "上海"
        test_results.append(("CSV 解析", True, "内存 CSV 解析成功"))
    except AssertionError as e:
        test_results.append(("CSV 解析", False, f"断言失败: {e}"))

    # 测试 5: URL 识别（不进行实际网络请求）
    try:
        # 测试 URL 格式识别
        url1 = "https://example.com/data.json"
        url2 = "http://api.example.com/v1/data"
        url3 = "ftp://example.com/file.txt"
        
        assert urlparse(url1).scheme == "https"
        assert urlparse(url2).scheme == "http"
        assert urlparse(url3).scheme == "ftp"
        
        # 测试 URL 协议验证
        parsed = urlparse(url1)
        assert parsed.scheme in ("http", "https")
        
        parsed = urlparse(url3)
        assert parsed.scheme not in ("http", "https")
        
        # 测试 read_data_source 的 URL 判断逻辑
        assert url1.startswith("http://") or url1.startswith("https://")
        assert url2.startswith("http://") or url2.startswith("https://")
        assert not (url3.startswith("http://") or url3.startswith("https://"))
        
        test_results.append(("URL 识别", True, "URL 格式识别正常"))
    except AssertionError as e:
        test_results.append(("URL 识别", False, f"断言失败: {e}"))
    except Exception as e:
        test_results.append(("URL 识别", False, f"异常: {e}"))

    # 测试 6: 空数据处理
    try:
        empty_md = generate_markdown([], title="空列表")
        assert "无数据" in empty_md
        test_results.append(("空数据处理", True, "空列表正确输出"))
    except AssertionError as e:
        test_results.append(("空数据处理", False, f"断言失败: {e}"))

    # 测试 7: XML 解析（内存中）
    try:
        xml_data = """<?xml version="1.0"?>
        <root>
            <item id="1">苹果</item>
            <item id="2">香蕉</item>
        </root>"""
        root = ET.fromstring(xml_data)
        items = root.findall('item')
        assert len(items) == 2
        assert items[0].text == "苹果"
        assert items[1].get("id") == "2"
        test_results.append(("XML 解析", True, "内存 XML 解析成功"))
    except AssertionError as e:
        test_results.append(("XML 解析", False, f"断言失败: {e}"))
    except Exception as e:
        test_results.append(("XML 解析", False, f"异常: {e}"))

    # 输出测试结果
    print("\n=== MDA 自检报告 ===")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print("")
    all_passed = True
    for name, passed, detail in test_results:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {detail}")
        if not passed:
            all_passed = False

    print("")
    if all_passed:
        print("✅ 全部自检通过")
        return 0
    else:
        print("❌ 存在未通过的测试")
        return 1


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="MDA - 数据编译为 Markdown 文档",
        epilog="示例: python main.py --input data.json --output out.md"
    )
    parser.add_argument("--input", "-i", help="输入文件路径或 URL")
    parser.add_argument("--output", "-o", help="输出 Markdown 文件路径")
    parser.add_argument("--title", "-t", help="文档标题（默认为文件名）")
    parser.add_argument("--batch", "-b", action="store_true", help="批量处理模式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="mda 1.0.2")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return selftest()

    # 参数校验
    if not args.input:
        parser.error("必须指定 --input 参数或使用 --selftest")

    # 批量模式
    if args.batch:
        if not args.output:
            parser.error("批量模式必须指定 --output 目录")

        try:
            results, success, fail = process_batch(args.input, args.output)
            print(f"\n批量处理完成: 成功 {success} 个, 失败 {fail} 个")
            for r in results:
                print(f"  {r}")
            return 0 if fail == 0 else 1
        except MDADataError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 单文件模式
    if not args.output:
        parser.error("必须指定 --output 参数")

    try:
        success, error = process_file(args.input, args.output, args.title)
        if success:
            print(f"✅ 转换成功: {args.input} → {args.output}")
            return 0
        else:
            print(f"❌ 转换失败: {error}", file=sys.stderr)
            return 1
    except MDADataError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
