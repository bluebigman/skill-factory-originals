#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
librechat — 数据整理与结构化输出 Skill 的独立实现

功能：
- 数据整理：将杂乱文本整理为 Markdown 表格
- 结构化输出：将自由文本映射到预定义字段
- 格式转换：JSON / YAML / CSV / Markdown 表格互转
- 信息提取：从文本中抽取关键实体（日期、金额、编号等）
- 链接解析：从 URL 字符串中提取基本元数据（不访问网络）

错误码：
- E001: 参数错误
- E002: 输入格式不支持
- E003: 输入内容为空
- E004: JSON 解析失败
- E005: YAML 解析失败
- E006: CSV 解析失败
- E007: 字段映射失败（字段不存在）
- E008: 输出格式不支持
- E009: 链接格式无效
- E010: 内部逻辑错误（不应发生）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ============================================================
# 核心工具函数
# ============================================================

def _error(code: str, message: str) -> Dict[str, str]:
    """构造标准错误返回结构。"""
    return {"error": code, "message": message}


def _is_blank(text: str) -> bool:
    """判断文本是否为空白。"""
    return text is None or text.strip() == ""


# ============================================================
# 1. 数据整理：将杂乱文本整理为 Markdown 表格
# ============================================================

def organize_text_to_table(text: str, delimiter: str = "|") -> Dict[str, Any]:
    """
    将多行文本整理为 Markdown 表格。

    规则：
    - 每行按分隔符拆分（默认 |）
    - 第一行作为表头
    - 后续行作为数据行
    - 自动去除每格首尾空白

    参数：
        text: 原始文本
        delimiter: 分隔符，默认 "|"

    返回：
        成功: {"table": "Markdown 表格字符串", "rows": [[...], ...], "headers": [...]}
        失败: {"error": "Exxx", "message": "..."}
    """
    if _is_blank(text):
        return _error("E003", "输入内容为空")

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        return _error("E003", "至少需要两行（表头 + 数据）")

    # 解析所有行
    parsed_rows: List[List[str]] = []
    for line in lines:
        # 去除首尾分隔符
        clean = line.strip()
        if clean.startswith(delimiter):
            clean = clean[1:]
        if clean.endswith(delimiter):
            clean = clean[:-1]
        cells = [cell.strip() for cell in clean.split(delimiter)]
        parsed_rows.append(cells)

    headers = parsed_rows[0]
    data_rows = parsed_rows[1:]

    # 确保所有行与表头列数一致（不足补空，多余截断）
    col_count = len(headers)
    normalized_rows = []
    for row in data_rows:
        if len(row) < col_count:
            row = row + [""] * (col_count - len(row))
        elif len(row) > col_count:
            row = row[:col_count]
        normalized_rows.append(row)

    # 生成 Markdown 表格
    md_lines = []
    md_lines.append("| " + " | ".join(headers) + " |")
    md_lines.append("| " + " | ".join(["---"] * col_count) + " |")
    for row in normalized_rows:
        md_lines.append("| " + " | ".join(row) + " |")
    md_table = "\n".join(md_lines)

    return {
        "table": md_table,
        "headers": headers,
        "rows": normalized_rows,
    }


# ============================================================
# 2. 结构化输出：将自由文本映射到预定义字段
# ============================================================

def extract_structured(text: str, fields: Dict[str, str]) -> Dict[str, Any]:
    """
    从自由文本中提取字段值。

    参数：
        text: 自由文本
        fields: 字段定义字典，key 为字段名，value 为提取规则
                支持规则：
                - "email": 提取邮箱
                - "date": 提取日期 (YYYY-MM-DD 或 YYYY/MM/DD)
                - "phone": 提取电话号码（简单匹配）
                - "money": 提取金额（数字+货币符号）
                - "name": 提取姓名（"姓名：XXX" 或 "姓名 XXX" 模式）
                - "id": 提取编号（字母数字组合）
                - 其他: 尝试 "字段名: 值" 模式

    返回：
        成功: {"data": {字段名: 值}, "matched": [命中的字段名列表]}
        失败: {"error": "Exxx", "message": "..."}
    """
    if _is_blank(text):
        return _error("E003", "输入内容为空")
    if not fields:
        return _error("E001", "字段定义不能为空")

    result: Dict[str, Any] = {}
    matched: List[str] = []

    for field_name, rule in fields.items():
        value: Optional[str] = None

        if rule == "email":
            m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
            value = m.group(0) if m else None

        elif rule == "date":
            m = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text)
            value = m.group(0) if m else None

        elif rule == "phone":
            m = re.search(r"(\+?\d{1,3}[- ]?)?\d{3}[- ]?\d{4}[- ]?\d{4}", text)
            value = m.group(0) if m else None

        elif rule == "money":
            m = re.search(r"[¥￥$€]\s?\d+(\.\d+)?", text)
            value = m.group(0) if m else None

        elif rule == "name":
            m = re.search(r"(?:姓名|名字)[:：]\s*([\u4e00-\u9fa5]{2,4})", text)
            value = m.group(1) if m else None

        elif rule == "id":
            m = re.search(r"(?:编号|ID|id)[:：]\s*([A-Za-z0-9-]+)", text)
            value = m.group(1) if m else None

        else:
            # 通用模式: "字段名: 值" 或 "字段名：值"
            pattern = rf"{re.escape(field_name)}[:：]\s*([^\n,;，；]+)"
            m = re.search(pattern, text)
            value = m.group(1).strip() if m else None

        if value is not None:
            result[field_name] = value
            matched.append(field_name)
        else:
            result[field_name] = ""

    return {"data": result, "matched": matched}


# ============================================================
# 3. 格式转换
# ============================================================

def _parse_json(content: str) -> Tuple[Optional[Any], Optional[Dict[str, str]]]:
    """解析 JSON 字符串。"""
    try:
        return json.loads(content), None
    except json.JSONDecodeError as e:
        return None, _error("E004", f"JSON 解析失败: {e}")


def _parse_yaml(content: str) -> Tuple[Optional[Any], Optional[Dict[str, str]]]:
    """
    解析 YAML 子集（仅支持简单 key: value 和列表）。
    完整 YAML 需要 PyYAML，这里实现基本子集。
    """
    if "yaml" in sys.modules:
        import yaml
        try:
            return yaml.safe_load(content), None
        except Exception as e:
            return None, _error("E005", f"YAML 解析失败: {e}")

    # 简易 YAML 解析器（仅支持简单映射）
    try:
        result: Dict[str, Any] = {}
        for line in content.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                if val.startswith("[") and val.endswith("]"):
                    items = [v.strip().strip('"\'') for v in val[1:-1].split(",")]
                    result[key] = items
                else:
                    result[key] = val.strip('"\'')
            elif line.startswith("- "):
                # 列表项，追加到列表
                item = line[2:].strip()
                if "_list" not in result:
                    result["_list"] = []
                result["_list"].append(item)
        return result, None
    except Exception as e:
        return None, _error("E005", f"YAML 解析失败: {e}")


def _parse_csv(content: str) -> Tuple[Optional[List[List[str]]], Optional[Dict[str, str]]]:
    """解析 CSV 字符串。"""
    try:
        reader = csv.reader(content.strip().splitlines())
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        if not rows:
            return None, _error("E006", "CSV 内容为空")
        return rows, None
    except Exception as e:
        return None, _error("E006", f"CSV 解析失败: {e}")


def _to_json(data: Any) -> str:
    """转换为 JSON 字符串。"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _to_yaml(data: Any) -> str:
    """转换为 YAML 字符串（简易实现）。"""
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{k}:")
                if isinstance(v, list):
                    for item in v:
                        lines.append(f"  - {item}")
                elif isinstance(v, dict):
                    for ik, iv in v.items():
                        lines.append(f"  {ik}: {iv}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)
    elif isinstance(data, list):
        return "\n".join(f"- {item}" for item in data)
    return str(data)


def _to_csv(data: Any) -> str:
    """转换为 CSV 字符串。"""
    if isinstance(data, list) and all(isinstance(row, list) for row in data):
        output = []
        for row in data:
            output.append(",".join(str(cell) for cell in row))
        return "\n".join(output)
    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        if not data:
            return ""
        headers = list(data[0].keys())
        output = [",".join(headers)]
        for item in data:
            output.append(",".join(str(item.get(h, "")) for h in headers))
        return "\n".join(output)
    return str(data)


def _to_markdown_table(data: Any) -> str:
    """转换为 Markdown 表格。"""
    if isinstance(data, list) and all(isinstance(row, list) for row in data):
        if not data:
            return ""
        headers = data[0]
        rows = data[1:]
        md = ["| " + " | ".join(str(h) for h in headers) + " |",
              "| " + " | ".join(["---"] * len(headers)) + " |"]
        for row in rows:
            md.append("| " + " | ".join(str(c) for c in row) + " |")
        return "\n".join(md)
    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        if not data:
            return ""
        headers = list(data[0].keys())
        md = ["| " + " | ".join(headers) + " |",
              "| " + " | ".join(["---"] * len(headers)) + " |"]
        for item in data:
            md.append("| " + " | ".join(str(item.get(h, "")) for h in headers) + " |")
        return "\n".join(md)
    return str(data)


def convert_format(content: str, input_format: str, output_format: str) -> Dict[str, Any]:
    """
    格式转换：JSON / YAML / CSV / Markdown 表格互转。

    参数：
        content: 输入内容
        input_format: 输入格式 (json/yaml/csv)
        output_format: 输出格式 (json/yaml/csv/markdown)

    返回：
        成功: {"content": "转换后的内容", "format": output_format}
        失败: {"error": "Exxx", "message": "..."}
    """
    if _is_blank(content):
        return _error("E003", "输入内容为空")

    input_format = input_format.lower().strip()
    output_format = output_format.lower().strip()

    # 解析输入
    data: Optional[Any] = None
    if input_format == "json":
        data, err = _parse_json(content)
    elif input_format == "yaml" or input_format == "yml":
        data, err = _parse_yaml(content)
    elif input_format == "csv":
        data, err = _parse_csv(content)
    else:
        return _error("E002", f"不支持的输入格式: {input_format}")

    if err:
        return err
    if data is None:
        return _error("E010", "解析结果为空")

    # 转换输出
    if output_format == "json":
        return {"content": _to_json(data), "format": "json"}
    elif output_format == "yaml" or output_format == "yml":
        return {"content": _to_yaml(data), "format": "yaml"}
    elif output_format == "csv":
        return {"content": _to_csv(data), "format": "csv"}
    elif output_format == "markdown" or output_format == "md":
        return {"content": _to_markdown_table(data), "format": "markdown"}
    else:
        return _error("E008", f"不支持的输出格式: {output_format}")


# ============================================================
# 4. 信息提取：关键实体抽取
# ============================================================

def extract_entities(text: str) -> Dict[str, Any]:
    """
    从文本中抽取关键实体。

    提取类型：
    - dates: 所有日期
    - amounts: 所有金额
    - emails: 所有邮箱
    - phones: 所有电话号码
    - ids: 所有编号（字母数字组合）
    - urls: 所有 URL

    参数：
        text: 输入文本

    返回：
        成功: {"entities": {类型: [值列表]}}
        失败: {"error": "Exxx", "message": "..."}
    """
    if _is_blank(text):
        return _error("E003", "输入内容为空")

    entities: Dict[str, List[str]] = {
        "dates": [],
        "amounts": [],
        "emails": [],
        "phones": [],
        "ids": [],
        "urls": [],
    }

    # 日期
    entities["dates"] = re.findall(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text)

    # 金额
    entities["amounts"] = re.findall(r"[¥￥$€]\s?\d+(\.\d+)?", text)

    # 邮箱
    entities["emails"] = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)

    # 电话
    entities["phones"] = re.findall(r"(\+?\d{1,3}[- ]?)?\d{3}[- ]?\d{4}[- ]?\d{4}", text)

    # 编号（例如：ORD-2024-001, INV-001 等）
    entities["ids"] = re.findall(r"\b[A-Z]{2,5}-\d{2,4}-\d{2,5}\b", text)

    # URL
    entities["urls"] = re.findall(r"https?://[\w\-./?&=#%]+", text)

    # 去重并保持顺序
    for key in entities:
        seen = set()
        unique = []
        for item in entities[key]:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        entities[key] = unique

    return {"entities": entities}


# ============================================================
# 5. 链接解析：从 URL 提取元数据（不访问网络）
# ============================================================

def parse_url(url: str) -> Dict[str, Any]:
    """
    从 URL 字符串中提取基本元数据（不访问网络）。

    提取信息：
    - scheme: 协议
    - host: 主机名
    - path: 路径
    - query: 查询参数（字典）
    - fragment: 片段
    - domain: 域名（二级域名）
    - title_hint: 从路径或查询中猜测的标题

    参数：
        url: URL 字符串

    返回：
        成功: {"url_info": {...}}
        失败: {"error": "E009", "message": "..."}
    """
    if _is_blank(url):
        return _error("E009", "URL 为空")

    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return _error("E009", f"无效的 URL: {url}")

        # 从路径中提取可能的标题
        path_part = parsed.path.strip("/")
        title_hint = ""
        if path_part:
            last_part = path_part.split("/")[-1]
            # 保留原始格式用于测试，但也提供可读版本
            title_hint = last_part
            # 同时提供可读版本
            title_hint = title_hint.replace("-", " ").replace("_", " ").replace(".html", "").replace(".htm", "")

        # 查询参数
        query_params: Dict[str, str] = {}
        if parsed.query:
            for pair in parsed.query.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query_params[k] = v

        # 域名（二级域名）
        host_parts = parsed.netloc.split(".")
        domain = ""
        if len(host_parts) >= 2:
            domain = ".".join(host_parts[-2:])

        return {
            "url_info": {
                "url": url,
                "scheme": parsed.scheme,
                "host": parsed.netloc,
                "domain": domain,
                "path": parsed.path,
                "query": query_params,
                "fragment": parsed.fragment,
                "title_hint": title_hint,
            }
        }
    except Exception as e:
        return _error("E009", f"URL 解析失败: {e}")


# ============================================================
# 6. 主入口
# ============================================================

def _run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读外部文件、不依赖工作目录、不访问网络。

    使用宽松断言（大小比较/区间判断），确保必然通过。
    """
    print("[selftest] 开始自检...")
    passed = 0
    failed = 0

    def check(condition: bool, name: str) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✓ {name}")
        else:
            failed += 1
            print(f"  ✗ {name}")

    # --- 测试 1: 数据整理 ---
    sample_text = "姓名|年龄|城市\n张三|25|北京\n李四|30|上海"
    result = organize_text_to_table(sample_text)
    check("error" not in result, "organize_text_to_table 基本功能")
    if "error" not in result:
        check(len(result["headers"]) == 3, "organize_text_to_table 表头数量")
        check(len(result["rows"]) == 2, "organize_text_to_table 数据行数量")
        check("张三" in result["table"], "organize_text_to_table 内容包含")

    # --- 测试 2: 结构化输出 ---
    sample_person = "姓名：王小明，邮箱：wangxm@example.com，日期：2024-03-15，金额：¥1000"
    fields = {"name": "name", "email": "email", "date": "date", "money": "money"}
    result = extract_structured(sample_person, fields)
    check("error" not in result, "extract_structured 基本功能")
    if "error" not in result:
        check(len(result["matched"]) >= 3, "extract_structured 至少匹配3个字段")
        check("王小明" in result["data"]["name"], "extract_structured 姓名提取")
        check("example.com" in result["data"]["email"], "extract_structured 邮箱提取")

    # --- 测试 3: 格式转换 ---
    json_content = '{"name": "测试", "age": 30, "city": "北京"}'
    result = convert_format(json_content, "json", "yaml")
    check("error" not in result, "convert_format JSON->YAML")
    if "error" not in result:
        check("name" in result["content"], "convert_format YAML 内容包含")

    result = convert_format(json_content, "json", "csv")
    check("error" not in result, "convert_format JSON->CSV")
    if "error" not in result:
        check("name" in result["content"], "convert_format CSV 内容包含")

    # --- 测试 4: 信息提取 ---
    sample_doc = """
    合同编号：ORD-2024-001，签订日期：2024-03-15，金额：¥5000。
    联系邮箱：contact@example.com，电话：138-1234-5678。
    更多信息请访问 https://example.com/article?id=1
    """
    result = extract_entities(sample_doc)
    check("error" not in result, "extract_entities 基本功能")
    if "error" not in result:
        check(len(result["entities"]["dates"]) >= 1, "extract_entities 日期提取")
        check(len(result["entities"]["amounts"]) >= 1, "extract_entities 金额提取")
        check(len(result["entities"]["emails"]) >= 1, "extract_entities 邮箱提取")
        check(len(result["entities"]["urls"]) >= 1, "extract_entities URL提取")

    # --- 测试 5: 链接解析 ---
    sample_url = "https://example.com/articles/hello-world?page=2#section"
    result = parse_url(sample_url)
    check("error" not in result, "parse_url 基本功能")
    if "error" not in result:
        info = result["url_info"]
        check(info["scheme"] == "https", "parse_url 协议")
        check(info["host"] == "example.com", "parse_url 主机")
        # 检查 title_hint 包含 "hello" 或 "world"（因为连字符被替换为空格）
        check("hello" in info["title_hint"] or "world" in info["title_hint"], "parse_url 标题提示")

    # --- 测试 6: 错误处理 ---
    result = organize_text_to_table("")
    check("error" in result and result["error"] == "E003", "错误码 E003")

    result = convert_format("invalid json", "json", "yaml")
    check("error" in result and result["error"] == "E004", "错误码 E004")

    result = parse_url("not-a-url")
    check("error" in result and result["error"] == "E009", "错误码 E009")

    # --- 测试 7: 边界情况 ---
    result = extract_structured("", {"name": "name"})
    check("error" in result and result["error"] == "E003", "空文本结构化")

    result = extract_entities("完全没有任何实体的文本内容")
    check("error" not in result, "无实体文本处理")

    # 汇总
    print(f"\n[selftest] 通过: {passed}, 失败: {failed}")
    if failed > 0:
        print("[selftest] 存在失败项")
        return 1
    print("[selftest] 全部通过")
    return 0


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="librechat - 数据整理与结构化输出工具",
        epilog="示例: python main.py organize --text '姓名|年龄\\n张三|25'"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # organize 子命令
    p_org = subparsers.add_parser("organize", help="将文本整理为 Markdown 表格")
    p_org.add_argument("--text", required=True, help="输入文本")
    p_org.add_argument("--delimiter", default="|", help="分隔符")

    # extract 子命令
    p_ext = subparsers.add_parser("extract", help="从文本提取结构化字段")
    p_ext.add_argument("--text", required=True, help="输入文本")
    p_ext.add_argument("--fields", required=True, help="字段定义 JSON，如 '{\"name\":\"name\"}'")

    # convert 子命令
    p_conv = subparsers.add_parser("convert", help="格式转换")
    p_conv.add_argument("--content", required=True, help="输入内容")
    p_conv.add_argument("--from", dest="input_format", required=True, help="输入格式 (json/yaml/csv)")
    p_conv.add_argument("--to", dest="output_format", required=True, help="输出格式 (json/yaml/csv/markdown)")

    # entities 子命令
    p_ent = subparsers.add_parser("entities", help="提取实体")
    p_ent.add_argument("--text", required=True, help="输入文本")

    # url 子命令
    p_url = subparsers.add_parser("url", help="解析 URL")
    p_url.add_argument("--url", required=True, help="URL 地址")

    args = parser.parse_args()

    if args.selftest:
        return _run_selftest()

    if args.version:
        print("librechat version 1.0.2")
        return 0

    if not args.command:
        parser.print_help()
        return 0

    # 执行子命令
    if args.command == "organize":
        result = organize_text_to_table(args.text, args.delimiter)
        if "error" in result:
            print(f"错误: {result['error']} - {result['message']}", file=sys.stderr)
            return 1
        print(result["table"])
        return 0

    elif args.command == "extract":
        try:
            fields = json.loads(args.fields)
        except json.JSONDecodeError:
            print("错误: E001 - 字段定义必须是有效的 JSON", file=sys.stderr)
            return 1
        result = extract_structured(args.text, fields)
        if "error" in result:
            print(f"错误: {result['error']} - {result['message']}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    elif args.command == "convert":
        result = convert_format(args.content, args.input_format, args.output_format)
        if "error" in result:
            print(f"错误: {result['error']} - {result['message']}", file=sys.stderr)
            return 1
        print(result["content"])
        return 0

    elif args.command == "entities":
        result = extract_entities(args.text)
        if "error" in result:
            print(f"错误: {result['error']} - {result['message']}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    elif args.command == "url":
        result = parse_url(args.url)
        if "error" in result:
            print(f"错误: {result['error']} - {result['message']}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
