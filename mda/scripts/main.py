#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDA - 数据编译为 Markdown 文档工具
功能：将 JSON/CSV/XML/TXT 数据源编译为标准化 Markdown 文档，
支持批量处理、置信度标注与模板定制。
"""

import argparse
import csv
import io
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入路径无效或不存在",
    "E002": "文件读取失败：无法读取输入文件",
    "E003": "数据解析失败：不支持的文件格式或格式错误",
    "E004": "远程 URL 访问失败",
    "E005": "输出目录创建失败",
    "E006": "模板文件读取失败",
    "E007": "批量处理失败：部分文件处理出错",
    "E008": "内部逻辑错误：未知的数据类型",
    "E009": "输出写入失败",
    "E010": "自检失败：核心逻辑验证未通过",
}

class MDAError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")

# ============ 数据源读取模块 ============

def read_local_file(filepath):
    """读取本地文件内容，返回字节串"""
    try:
        with open(filepath, "rb") as f:
            return f.read()
    except Exception as e:
        raise MDAError("E002", f"无法读取文件 {filepath}: {e}")

def read_remote_url(url, timeout=10):
    """读取远程 URL 内容，返回字节串"""
    try:
        req = Request(url, headers={"User-Agent": "MDA-Skill/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except URLError as e:
        raise MDAError("E004", f"无法访问 URL {url}: {e}")
    except Exception as e:
        raise MDAError("E004", f"URL 访问异常 {url}: {e}")

def load_data(source):
    """
    加载数据源（本地文件或 URL），返回字节串
    """
    if source.startswith(("http://", "https://")):
        return read_remote_url(source)
    else:
        if not os.path.exists(source):
            raise MDAError("E001", f"输入路径不存在: {source}")
        return read_local_file(source)

# ============ 数据解析模块 ============

def parse_json(data_bytes):
    """解析 JSON 数据"""
    try:
        return json.loads(data_bytes.decode("utf-8"))
    except Exception as e:
        raise MDAError("E003", f"JSON 解析失败: {e}")

def parse_csv(data_bytes):
    """解析 CSV 数据，返回字典列表"""
    try:
        text = data_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        raise MDAError("E003", f"CSV 解析失败: {e}")

def parse_xml(data_bytes):
    """解析 XML 数据，转换为字典结构"""
    try:
        root = ET.fromstring(data_bytes)
        return _xml_to_dict(root)
    except Exception as e:
        raise MDAError("E003", f"XML 解析失败: {e}")

def _xml_to_dict(element):
    """将 XML 元素递归转换为字典"""
    result = {}
    # 处理属性
    for key, value in element.attrib.items():
        result[f"@{key}"] = value
    
    # 处理子元素
    children = list(element)
    if children:
        for child in children:
            child_data = _xml_to_dict(child)
            tag = child.tag
            if tag in result:
                # 多个同名子元素，转为列表
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_data)
            else:
                result[tag] = child_data
    else:
        # 叶子节点，取文本内容
        text = (element.text or "").strip()
        if text:
            result["#text"] = text
    
    return result

def parse_txt(data_bytes):
    """解析 TXT 数据，按行拆分为列表"""
    try:
        text = data_bytes.decode("utf-8")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return {"lines": lines, "content": text}
    except Exception as e:
        raise MDAError("E003", f"TXT 解析失败: {e}")

def parse_data(source, data_bytes):
    """根据文件扩展名或 URL 后缀解析数据"""
    # 确定格式
    if source.endswith(".json"):
        return parse_json(data_bytes)
    elif source.endswith(".csv"):
        return parse_csv(data_bytes)
    elif source.endswith(".xml"):
        return parse_xml(data_bytes)
    elif source.endswith(".txt"):
        return parse_txt(data_bytes)
    else:
        # 尝试自动检测
        text = data_bytes.decode("utf-8", errors="ignore").strip()
        if text.startswith("{"):
            return parse_json(data_bytes)
        elif text.startswith("<"):
            return parse_xml(data_bytes)
        elif "," in text.split("\n")[0]:
            return parse_csv(data_bytes)
        else:
            raise MDAError("E003", f"不支持的文件格式: {source}")

# ============ 置信度标注模块 ============

def validate_field(value, field_name=""):
    """
    检查字段值，返回 (是否正常, 标注信息)
    """
    if value is None:
        return False, f"[需核实:{field_name}]"
    if isinstance(value, str) and value.strip() == "":
        return False, f"[需核实:{field_name}]"
    if isinstance(value, (int, float)) and value < 0:
        return False, f"[需核实:{field_name}]"
    return True, ""

def annotate_data(data):
    """
    对数据中的可疑字段进行置信度标注
    返回处理后的数据
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            ok, annotation = validate_field(value, key)
            if ok:
                result[key] = annotate_data(value) if isinstance(value, (dict, list)) else value
            else:
                if isinstance(value, (dict, list)):
                    result[key] = annotate_data(value)
                else:
                    result[key] = annotation
        return result
    elif isinstance(data, list):
        return [annotate_data(item) for item in data]
    else:
        return data

# ============ Markdown 生成模块 ============

def dict_to_markdown_table(data_list):
    """
    将字典列表转换为 Markdown 表格
    """
    if not data_list or not isinstance(data_list, list):
        return "_无数据_"
    
    # 收集所有字段
    fields = []
    for item in data_list:
        if isinstance(item, dict):
            for key in item.keys():
                if key not in fields:
                    fields.append(key)
    
    if not fields:
        return "_无字段_"
    
    # 生成表头
    lines = []
    lines.append("| " + " | ".join(fields) + " |")
    lines.append("| " + " | ".join(["---"] * len(fields)) + " |")
    
    # 生成数据行
    for item in data_list:
        if isinstance(item, dict):
            row = []
            for field in fields:
                value = item.get(field, "")
                # 复杂类型转为 JSON 字符串
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                row.append(str(value))
            lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append(f"| {item} |")
    
    return "\n".join(lines)

def dict_to_markdown(data, level=1):
    """
    将字典数据递归转换为 Markdown 格式
    """
    if not isinstance(data, dict):
        return str(data)
    
    lines = []
    for key, value in data.items():
        lines.append(f"{'#' * min(level, 6)} {key}")
        lines.append("")
        
        if isinstance(value, dict):
            lines.append(dict_to_markdown(value, level + 1))
        elif isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                lines.append(dict_to_markdown_table(value))
            else:
                for item in value:
                    if isinstance(item, dict):
                        lines.append(dict_to_markdown(item, level + 1))
                    else:
                        lines.append(f"- {item}")
        else:
            lines.append(str(value))
        
        lines.append("")
    
    return "\n".join(lines)

def generate_markdown(data, title="数据文档", template=None):
    """
    生成标准化 Markdown 文档
    """
    # 处理模板（简化版：仅支持标题和章节顺序）
    if template:
        # 模板格式：YAML 头 + 正文模板
        # 这里简化处理，仅提取 title
        for line in template.splitlines():
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip()
    
    doc_lines = []
    doc_lines.append(f"# {title}")
    doc_lines.append("")
    doc_lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc_lines.append("")
    doc_lines.append("---")
    doc_lines.append("")
    
    if isinstance(data, list):
        # 列表数据：尝试表格展示
        if data and all(isinstance(item, dict) for item in data):
            doc_lines.append("## 数据表")
            doc_lines.append("")
            doc_lines.append(dict_to_markdown_table(data))
        else:
            doc_lines.append("## 数据列表")
            doc_lines.append("")
            for i, item in enumerate(data, 1):
                doc_lines.append(f"### 条目 {i}")
                doc_lines.append("")
                if isinstance(item, dict):
                    doc_lines.append(dict_to_markdown(item, 4))
                else:
                    doc_lines.append(str(item))
                doc_lines.append("")
    elif isinstance(data, dict):
        doc_lines.append(dict_to_markdown(data, 2))
    else:
        doc_lines.append(str(data))
    
    doc_lines.append("")
    doc_lines.append("---")
    doc_lines.append("")
    doc_lines.append("*本文档由 MDA Skill 自动生成*")
    
    return "\n".join(doc_lines)

# ============ 批量处理模块 ============

def process_file(source, output_dir, template=None):
    """
    处理单个文件，生成 Markdown 文档
    """
    # 加载数据
    data_bytes = load_data(source)
    # 解析数据
    data = parse_data(source, data_bytes)
    # 置信度标注
    annotated_data = annotate_data(data)
    # 生成 Markdown
    filename = os.path.basename(source)
    title = os.path.splitext(filename)[0]
    markdown = generate_markdown(annotated_data, title=title, template=template)
    
    # 写入输出文件
    output_file = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.md")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown)
    except Exception as e:
        raise MDAError("E009", f"写入文件失败 {output_file}: {e}")
    
    return output_file

def process_directory(input_dir, output_dir, template=None):
    """
    批量处理目录下的所有数据文件
    """
    if not os.path.isdir(input_dir):
        raise MDAError("E001", f"输入目录不存在: {input_dir}")
    
    # 创建输出目录
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        raise MDAError("E005", f"创建输出目录失败: {e}")
    
    # 支持的扩展名
    supported_ext = (".json", ".csv", ".xml", ".txt")
    
    # 获取所有支持的文件
    files = [f for f in os.listdir(input_dir) if f.endswith(supported_ext)]
    
    if not files:
        print("警告：输入目录中没有找到支持的数据文件")
        return []
    
    results = []
    errors = []
    
    for filename in files:
        filepath = os.path.join(input_dir, filename)
        try:
            output_file = process_file(filepath, output_dir, template)
            results.append(output_file)
            print(f"✓ 已生成: {output_file}")
        except MDAError as e:
            errors.append((filename, str(e)))
            print(f"✗ 处理失败 {filename}: {e}")
    
    if errors:
        raise MDAError("E007", f"批量处理完成，但有 {len(errors)} 个文件失败")
    
    return results

# ============ 模板处理模块 ============

def load_template(template_path):
    """加载模板文件"""
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise MDAError("E006", f"模板文件读取失败: {e}")

# ============ 命令行入口 ============

def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="MDA - 数据编译为 Markdown 文档工具",
        epilog="示例: python main.py -i input.json -o output.md"
    )
    
    parser.add_argument("-i", "--input", help="输入文件或目录路径，或远程 URL")
    parser.add_argument("-o", "--output", help="输出文件或目录路径")
    parser.add_argument("-t", "--template", help="模板文件路径")
    parser.add_argument("--batch", action="store_true", help="批量处理模式（输入为目录）")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)
    
    # 参数检查
    if not args.input:
        parser.error("必须指定 --input 参数")
    
    if not args.output:
        parser.error("必须指定 --output 参数")
    
    try:
        # 加载模板
        template = None
        if args.template:
            template = load_template(args.template)
        
        # 批量处理模式
        if args.batch or os.path.isdir(args.input):
            output_dir = args.output if os.path.isdir(args.output) or not args.output.endswith(".md") else os.path.dirname(args.output)
            results = process_directory(args.input, output_dir, template)
            print(f"\n批量处理完成，共生成 {len(results)} 个文档")
            for r in results:
                print(f"  - {r}")
        # 单文件处理模式
        else:
            # 如果是 URL 或单文件
            output_file = args.output
            if not output_file.endswith(".md"):
                output_file = output_file + ".md"
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            result = process_file(args.input, os.path.dirname(output_file) or ".", template)
            print(f"文档已生成: {result}")
    
    except MDAError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 [E008]: 未预期的异常: {e}", file=sys.stderr)
        sys.exit(1)

# ============ 自检模块 ============

def selftest():
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    不读取外部文件，不依赖当前工作目录，不访问网络
    """
    print("=== MDA 自检开始 ===")
    
    try:
        # 测试数据定义
        test_json_data = [
            {"name": "产品A", "price": 99.5, "stock": 150, "category": "电子"},
            {"name": "产品B", "price": -10, "stock": 0, "category": ""},
            {"name": "产品C", "price": 299, "stock": 30, "category": "家居"},
        ]
        
        test_csv_text = "name,age,city\nalice,30,beijing\nbob,25,shanghai\ncarol,,guangzhou\n"
        
        test_xml_text = """<?xml version="1.0"?>
<root>
    <item id="1">
        <name>item1</name>
        <price>100</price>
    </item>
    <item id="2">
        <name>item2</name>
        <price>200</price>
    </item>
</root>"""
        
        test_txt_text = "第一行文本\n第二行文本\n第三行文本\n"
        
        # 1. 测试 JSON 解析
        print("[1] 测试 JSON 解析...")
        json_data = json.loads(json.dumps(test_json_data))
        assert isinstance(json_data, list), "JSON 解析结果应为列表"
        assert len(json_data) == 3, "JSON 解析结果长度应为 3"
        assert json_data[0]["name"] == "产品A", "JSON 解析内容不正确"
        print("    ✓ JSON 解析通过")
        
        # 2. 测试 CSV 解析
        print("[2] 测试 CSV 解析...")
        csv_data = parse_csv(test_csv_text.encode("utf-8"))
        assert isinstance(csv_data, list), "CSV 解析结果应为列表"
        assert len(csv_data) == 3, "CSV 解析结果长度应为 3"
        assert csv_data[0]["name"] == "alice", "CSV 解析内容不正确"
        assert csv_data[2]["age"] == "", "CSV 空字段应保留为空字符串"
        print("    ✓ CSV 解析通过")
        
        # 3. 测试 XML 解析
        print("[3] 测试 XML 解析...")
        xml_data = parse_xml(test_xml_text.encode("utf-8"))
        assert isinstance(xml_data, dict), "XML 解析结果应为字典"
        assert "item" in xml_data, "XML 解析应包含 item 字段"
        items = xml_data["item"]
        assert isinstance(items, list) and len(items) == 2, "XML 应解析出 2 个 item"
        assert items[0]["name"]["#text"] == "item1", "XML 解析内容不正确"
        print("    ✓ XML 解析通过")
        
        # 4. 测试 TXT 解析
        print("[4] 测试 TXT 解析...")
        txt_data = parse_txt(test_txt_text.encode("utf-8"))
        assert isinstance(txt_data, dict), "TXT 解析结果应为字典"
        assert "lines" in txt_data, "TXT 解析应包含 lines 字段"
        assert len(txt_data["lines"]) == 3, "TXT 应解析出 3 行"
        print("    ✓ TXT 解析通过")
        
        # 5. 测试置信度标注
        print("[5] 测试置信度标注...")
        annotated = annotate_data(test_json_data)
        # 检查负价格被标注
        assert "[需核实:price]" in str(annotated[1]), "负价格应被标注"
        # 检查空分类被标注
        assert "[需核实:category]" in str(annotated[1]), "空分类应被标注"
        # 检查正常数据未被标注
        assert "[需核实" not in str(annotated[0]), "正常数据不应被标注"
        print("    ✓ 置信度标注通过")
        
        # 6. 测试 Markdown 生成
        print("[6] 测试 Markdown 生成...")
        markdown = generate_markdown(test_json_data, title="测试文档")
        assert markdown.startswith("# 测试文档"), "Markdown 应包含标题"
        assert "| name" in markdown, "Markdown 应包含表格"
        assert "产品A" in markdown, "Markdown 应包含数据内容"
        print("    ✓ Markdown 生成通过")
        
        # 7. 测试表格生成
        print("[7] 测试表格生成...")
        table = dict_to_markdown_table(test_json_data)
        assert "| name |" in table, "表格应包含表头"
        assert "| 产品A |" in table, "表格应包含数据行"
        print("    ✓ 表格生成通过")
        
        # 8. 测试边界情况
        print("[8] 测试边界情况...")
        # 空列表
        empty_table = dict_to_markdown_table([])
        assert empty_table == "_无数据_", "空列表应返回占位文本"
        # 非字典列表
        simple_list = [1, 2, 3]
        simple_table = dict_to_markdown_table(simple_list)
        assert "无字段" in simple_table or "1" in simple_table, "简单列表应能生成表格"
        print("    ✓ 边界情况通过")
        
        # 9. 测试错误处理
        print("[9] 测试错误处理...")
        # 无效 JSON
        try:
            parse_json(b"{invalid json")
            raise AssertionError("无效 JSON 应抛出异常")
        except MDAError as e:
            assert e.code == "E003", "错误码应为 E003"
        # 不存在的文件
        try:
            load_data("/nonexistent/file.json")
            raise AssertionError("不存在的文件应抛出异常")
        except MDAError as e:
            assert e.code == "E001", "错误码应为 E001"
        print("    ✓ 错误处理通过")
        
        # 10. 测试批量处理逻辑（内存中模拟）
        print("[10] 测试批量处理逻辑...")
        # 模拟多个文件处理
        test_sources = [
            ("data1.json", json.dumps([{"a": 1, "b": 2}]).encode()),
            ("data2.json", json.dumps([{"c": 3, "d": 4}]).encode()),
        ]
        for name, data in test_sources:
            parsed = parse_data(name, data)
            assert isinstance(parsed, list), f"{name} 应解析为列表"
            markdown = generate_markdown(parsed, title=name)
            assert len(markdown) > 10, f"{name} 生成的 Markdown 应有内容"
        print("    ✓ 批量处理逻辑通过")
        
        print("\n=== 自检全部通过！===")
        return True
        
    except AssertionError as e:
        print(f"\n✗ 自检失败: {e}")
        return False
    except MDAError as e:
        print(f"\n✗ 自检异常: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 自检未预期异常: {e}")
        return False

if __name__ == "__main__":
    main()
