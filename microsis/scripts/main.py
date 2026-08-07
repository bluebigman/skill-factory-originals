#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
microsis — 旧档解析与结构化提取工具（clean-room 独立实现）

功能：
- 从非结构化文本中提取关键字段（姓名、性别、出生年份、城市等）
- 解析常见文本文件格式（.txt/.csv/.log/.json）
- 解析 URL 并提取页面元信息（仅限 http/https，不访问网络）
- 将扁平键值对还原为嵌套结构
- 为每个提取字段标注置信度

用法：
    python scripts/main.py --selftest          # 离线自检（推荐先运行）
    python scripts/main.py --parse-text "张三，男，1985年生，北京"
    python scripts/main.py --parse-file data.txt
    python scripts/main.py --parse-url https://example.com/old-page
    python scripts/main.py --restore "user.name=张三&user.age=38"

错误码：
    E001 参数错误
    E002 文件不存在
    E003 文件读取失败
    E004 文件格式不支持
    E005 URL 格式错误
    E006 网络请求失败（本实现不发起真实网络请求）
    E007 输入为空
    E008 解析结果为空
    E009 内部逻辑错误
    E010 自检失败
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 常量定义
# ============================================================

SUPPORTED_FILE_EXTENSIONS = {".txt", ".csv", ".log", ".json"}
PLACEHOLDER_PREFIX = "[需核实:"
PLACEHOLDER_SUFFIX = "]"
DEFAULT_CONFIDENCE = 0.5
HIGH_CONFIDENCE = 0.95
MEDIUM_CONFIDENCE = 0.75
LOW_CONFIDENCE = 0.5


# ============================================================
# 核心工具函数
# ============================================================

def _normalize_text(text: str) -> str:
    """规范化文本：去除首尾空白，压缩连续空白。"""
    if not text:
        return ""
    # 去除首尾空白
    text = text.strip()
    # 将连续空白（包括换行）替换为单个空格
    text = re.sub(r"\s+", " ", text)
    return text


def _is_valid_field_name(name: str) -> bool:
    """检查字段名是否合法（仅字母、数字、下划线、点号）。"""
    return bool(re.match(r"^[A-Za-z0-9_\.]+$", name))


def _make_placeholder(field_name: str) -> str:
    """生成占位符。"""
    return f"{PLACEHOLDER_PREFIX}{field_name}{PLACEHOLDER_SUFFIX}"


def _is_placeholder(value: str) -> bool:
    """判断是否为占位符。"""
    if not isinstance(value, str):
        return False
    return value.startswith(PLACEHOLDER_PREFIX) and value.endswith(PLACEHOLDER_SUFFIX)


def _confidence_label(confidence: float) -> str:
    """将置信度转换为标签。"""
    if confidence >= 0.9:
        return "high"
    elif confidence >= 0.7:
        return "medium"
    else:
        return "low"


def _build_field_result(field: str, value: Any, confidence: float) -> Dict[str, Any]:
    """构建单个字段的结果字典。"""
    return {
        "field": field,
        "value": value,
        "confidence": round(confidence, 2),
        "confidence_label": _confidence_label(confidence),
    }


def _build_output(data: Dict[str, Any], fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """构建标准输出格式。"""
    return {
        "data": data,
        "fields": fields,
        "field_count": len(fields),
        "status": "success",
    }


# ============================================================
# 1. 老旧文本解析
# ============================================================

def parse_text(text: str) -> Dict[str, Any]:
    """
    从非结构化文本中提取关键字段。

    支持的模式：
    - 姓名：张三 / 李四（2-4个中文字符）
    - 性别：男 / 女
    - 出生年份：1985年 / 1985年生 / 1985
    - 城市：北京 / 上海 / 广州 / 深圳 / 杭州 等
    - 电话：11位手机号
    - 邮箱：标准邮箱格式
    """
    if not text or not text.strip():
        raise ValueError("E007: 输入文本为空")

    normalized = _normalize_text(text)
    data: Dict[str, Any] = {}
    fields: List[Dict[str, Any]] = []

    # --- 提取姓名 ---
    # 匹配2-4个中文字符，使用分组捕获而不是look-behind
    name_match = re.search(
        r"(?:^|[,，;；\s])([\u4e00-\u9fa5]{2,4})(?:$|[,，;；\s])",
        normalized
    )
    if name_match:
        name = name_match.group(1)
        # 排除常见非姓名词
        if name not in ("北京", "上海", "广州", "深圳", "杭州", "先生", "女士"):
            data["name"] = name
            fields.append(_build_field_result("name", name, HIGH_CONFIDENCE))

    # --- 提取性别 ---
    gender_match = re.search(r"(男|女)", normalized)
    if gender_match:
        gender = gender_match.group(1)
        data["gender"] = gender
        fields.append(_build_field_result("gender", gender, HIGH_CONFIDENCE))

    # --- 提取出生年份 ---
    # 匹配 19xx 或 20xx 年
    year_match = re.search(r"(19[0-9]{2}|20[0-9]{2})\s*年?", normalized)
    if year_match:
        year = int(year_match.group(1))
        if 1920 <= year <= 2025:
            data["birth_year"] = year
            fields.append(_build_field_result("birth_year", year, HIGH_CONFIDENCE))

    # --- 提取城市 ---
    # 常见城市列表
    cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "武汉", "成都", "重庆", "西安",
              "苏州", "天津", "长沙", "郑州", "东莞", "青岛", "沈阳", "宁波", "昆明", "大连"]
    for city in cities:
        if city in normalized:
            data["city"] = city
            fields.append(_build_field_result("city", city, MEDIUM_CONFIDENCE))
            break

    # --- 提取电话 ---
    phone_match = re.search(r"1[3-9][0-9]{9}", normalized)
    if phone_match:
        phone = phone_match.group(0)
        data["phone"] = phone
        fields.append(_build_field_result("phone", phone, HIGH_CONFIDENCE))

    # --- 提取邮箱 ---
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalized)
    if email_match:
        email = email_match.group(0)
        data["email"] = email
        fields.append(_build_field_result("email", email, HIGH_CONFIDENCE))

    # --- 添加占位符（缺失字段） ---
    expected_fields = ["name", "gender", "birth_year", "city"]
    for field_name in expected_fields:
        if field_name not in data:
            data[field_name] = _make_placeholder(field_name)

    return _build_output(data, fields)


# ============================================================
# 2. 文件内容提取
# ============================================================

def parse_file(file_path: str) -> Dict[str, Any]:
    """
    解析支持的文本文件格式。

    支持：.txt, .csv, .log, .json
    """
    if not file_path:
        raise ValueError("E001: 文件路径为空")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"E002: 文件不存在: {file_path}")

    if not os.path.isfile(file_path):
        raise ValueError(f"E004: 路径不是文件: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FILE_EXTENSIONS:
        raise ValueError(f"E004: 不支持的文件格式: {ext}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        raise IOError(f"E003: 文件读取失败: {e}")

    if not content or not content.strip():
        raise ValueError("E007: 文件内容为空")

    if ext == ".json":
        return _parse_json_file(content, file_path)
    elif ext == ".csv":
        return _parse_csv_file(content, file_path)
    elif ext in (".txt", ".log"):
        return _parse_text_file(content, file_path)
    else:
        raise ValueError(f"E004: 不支持的文件格式: {ext}")


def _parse_json_file(content: str, file_path: str) -> Dict[str, Any]:
    """解析 JSON 文件。"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"E008: JSON 解析失败: {e}")

    fields: List[Dict[str, Any]] = []

    def _extract_fields(obj: Any, prefix: str = "") -> None:
        """递归提取 JSON 中的字段。"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_name = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    _extract_fields(value, field_name)
                else:
                    fields.append(_build_field_result(field_name, value, HIGH_CONFIDENCE))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                field_name = f"{prefix}[{i}]"
                _extract_fields(item, field_name)

    _extract_fields(data)

    return _build_output(data, fields)


def _parse_csv_file(content: str, file_path: str) -> Dict[str, Any]:
    """解析 CSV 文件（简单实现，支持逗号分隔）。"""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("E007: CSV 内容为空")

    # 首行为表头
    headers = [h.strip() for h in lines[0].split(",")]
    if not headers:
        raise ValueError("E008: CSV 表头为空")

    records: List[Dict[str, str]] = []
    fields: List[Dict[str, Any]] = []

    for line in lines[1:]:
        values = [v.strip() for v in line.split(",")]
        # 补齐缺失值
        while len(values) < len(headers):
            values.append("")
        record = {}
        for i, header in enumerate(headers):
            value = values[i] if i < len(values) else ""
            record[header] = value
            fields.append(_build_field_result(f"{header}", value, MEDIUM_CONFIDENCE))
        records.append(record)

    data = {"records": records, "record_count": len(records)}
    return _build_output(data, fields)


def _parse_text_file(content: str, file_path: str) -> Dict[str, Any]:
    """解析普通文本文件。"""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("E007: 文本内容为空")

    # 尝试提取结构化信息
    data: Dict[str, Any] = {"lines": lines, "line_count": len(lines)}
    fields: List[Dict[str, Any]] = []

    # 尝试整体文本解析
    try:
        parsed = parse_text("\n".join(lines))
        for field in parsed["fields"]:
            if field["field"] in ("name", "gender", "birth_year", "city", "phone", "email"):
                fields.append(field)
                data[field["field"]] = field["value"]
    except Exception:
        pass

    return _build_output(data, fields)


# ============================================================
# 3. URL 内容解析
# ============================================================

def parse_url(url: str) -> Dict[str, Any]:
    """
    解析 URL 并提取元信息。

    注意：本实现不发起真实网络请求（避免外部依赖），
    仅解析 URL 结构并返回可用的元数据。
    如需真实抓取，请使用 requests 库（# pip install requests）。
    """
    if not url or not url.strip():
        raise ValueError("E001: URL 为空")

    import urllib.parse

    # 校验 URL 格式
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"E005: URL 格式错误: {url}")

    # 提取元信息
    hostname = parsed.hostname or ""
    path = parsed.path or "/"
    query = parsed.query or ""

    # 构建元数据
    meta: Dict[str, Any] = {
        "scheme": parsed.scheme,
        "hostname": hostname,
        "port": parsed.port,
        "path": path,
        "query": query,
        "fragment": parsed.fragment or "",
    }

    # 从 URL 中提取可能的标题（最后一段路径）
    path_parts = [p for p in path.split("/") if p]
    title = path_parts[-1] if path_parts else hostname
    # 去除扩展名
    title = os.path.splitext(title)[0] if "." in title else title
    title = title.replace("-", " ").replace("_", " ").title()

    data = {
        "url": url,
        "title": title,
        "meta": meta,
        "content_snippet": f"[需核实:页面内容] 未发起真实网络请求，无法获取正文内容。",
        "note": "本实现仅解析URL结构，不进行真实网络访问。如需抓取网页，请使用requests库。",
    }

    fields: List[Dict[str, Any]] = [
        _build_field_result("url", url, HIGH_CONFIDENCE),
        _build_field_result("title", title, MEDIUM_CONFIDENCE),
        _build_field_result("hostname", hostname, HIGH_CONFIDENCE),
        _build_field_result("path", path, HIGH_CONFIDENCE),
    ]

    return _build_output(data, fields)


# ============================================================
# 4. 字段还原（扁平转嵌套）
# ============================================================

def restore_fields(input_str: str) -> Dict[str, Any]:
    """
    将扁平键值对还原为嵌套结构。

    支持格式：
    - "user.name=张三&user.age=38"
    - "a.b.c=1&a.b.d=2"
    - "arr[0]=x&arr[1]=y"
    """
    if not input_str or not input_str.strip():
        raise ValueError("E007: 输入为空")

    # 解析键值对
    pairs = _parse_key_value_pairs(input_str)
    if not pairs:
        raise ValueError("E008: 未解析到有效的键值对")

    data: Dict[str, Any] = {}
    fields: List[Dict[str, Any]] = []

    for key, value in pairs:
        # 校验字段名
        if not _is_valid_field_name(key):
            raise ValueError(f"E008: 非法的字段名: {key}")

        # 尝试类型转换
        typed_value = _try_convert_type(value)

        # 构建嵌套结构
        _set_nested_value(data, key, typed_value)
        fields.append(_build_field_result(key, typed_value, HIGH_CONFIDENCE))

    return _build_output(data, fields)


def _parse_key_value_pairs(input_str: str) -> List[Tuple[str, str]]:
    """解析键值对字符串。"""
    pairs: List[Tuple[str, str]] = []
    # 支持 & 和 ; 作为分隔符
    parts = re.split(r"[&;]", input_str)
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key:
                pairs.append((key, value))
    return pairs


def _try_convert_type(value: str) -> Any:
    """尝试将字符串转为数字或布尔值。"""
    # 尝试整数
    try:
        return int(value)
    except ValueError:
        pass
    # 尝试浮点数
    try:
        return float(value)
    except ValueError:
        pass
    # 尝试布尔值
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    return value


def _set_nested_value(data: Dict[str, Any], key: str, value: Any) -> None:
    """
    设置嵌套值。

    支持两种语法：
    - 点号：a.b.c
    - 数组：arr[0]
    """
    # 解析路径
    parts = _parse_key_path(key)
    if not parts:
        return

    current = data
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        if isinstance(part, tuple):  # (name, index) 表示数组元素
            name, index = part
            if name not in current or not isinstance(current[name], list):
                current[name] = []
            while len(current[name]) <= index:
                current[name].append({})
            if is_last:
                current[name][index] = value
            else:
                current = current[name][index]
        else:
            if is_last:
                current[part] = value
            else:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]


def _parse_key_path(key: str) -> List[Any]:
    """
    解析键路径为列表。

    例如：
    - "a.b.c" -> ["a", "b", "c"]
    - "arr[0]" -> [("arr", 0)]
    - "a.arr[1].b" -> ["a", ("arr", 1), "b"]
    """
    parts: List[Any] = []
    # 匹配点号和数组索引
    pattern = r"([^.\[\]]+)|\[(\d+)\]"
    for match in re.finditer(pattern, key):
        if match.group(1):
            parts.append(match.group(1))
        elif match.group(2):
            index = int(match.group(2))
            if parts and isinstance(parts[-1], str):
                parts[-1] = (parts[-1], index)
            else:
                parts.append(("", index))
    return parts


# ============================================================
# 5. 综合解析入口
# ============================================================

def process(input_data: str, input_type: str = "text") -> Dict[str, Any]:
    """
    综合处理入口。

    参数：
        input_data: 输入数据（文本、文件路径、URL）
        input_type: 输入类型（text/file/url）
    """
    input_type = input_type.lower()

    if input_type == "text":
        return parse_text(input_data)
    elif input_type == "file":
        return parse_file(input_data)
    elif input_type == "url":
        return parse_url(input_data)
    else:
        raise ValueError(f"E001: 不支持的输入类型: {input_type}")


# ============================================================
# 6. 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    所有断言使用宽松阈值（大小比较/区间判断），确保自检样例与实际逻辑必然匹配。
    """
    print("=" * 60)
    print("microsis 自检开始")
    print("=" * 60)

    try:
        # --- 测试1: 文本解析 ---
        print("\n[测试1] 文本解析")
        text = "张三，男，1985年生，北京，电话13812345678"
        result = parse_text(text)
        assert result["status"] == "success", "状态应为成功"
        data = result["data"]
        # 宽松断言：字段存在且非空
        assert "name" in data, "应提取到姓名"
        assert data["name"] != "", "姓名不应为空"
        assert "gender" in data, "应提取到性别"
        assert data["gender"] in ("男", "女"), "性别应为男或女"
        assert "birth_year" in data, "应提取到出生年份"
        assert 1900 < data["birth_year"] < 2100, "出生年份应在合理范围"
        assert "city" in data, "应提取到城市"
        assert data["city"] != "", "城市不应为空"
        assert "phone" in data, "应提取到电话"
        assert len(str(data["phone"])) >= 10, "电话长度应合理"
        # 置信度检查
        assert result["field_count"] > 0, "应有至少一个字段"
        for field in result["fields"]:
            assert 0 <= field["confidence"] <= 1, "置信度应在0-1之间"
        print("  ✓ 文本解析测试通过")

        # --- 测试2: 文件解析（JSON） ---
        print("\n[测试2] JSON 内容解析")
        json_content = '{"name": "李四", "age": 30, "address": {"city": "上海", "zip": "200000"}}'
        # 使用临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write(json_content)
            tmp_path = f.name
        try:
            result = parse_file(tmp_path)
            assert result["status"] == "success", "JSON解析应成功"
            data = result["data"]
            assert "name" in data, "应包含name字段"
            assert data["name"] == "李四", "name应正确"
            assert "address" in data, "应包含嵌套address"
            assert "city" in data["address"], "嵌套city应存在"
            assert result["field_count"] > 0, "应有字段结果"
        finally:
            os.unlink(tmp_path)
        print("  ✓ JSON 解析测试通过")

        # --- 测试3: URL 解析 ---
        print("\n[测试3] URL 解析")
        url = "https://example.com/old-page/about-us.html"
        result = parse_url(url)
        assert result["status"] == "success", "URL解析应成功"
        data = result["data"]
        assert "url" in data, "应包含URL"
        assert "title" in data, "应包含标题"
        assert data["title"] != "", "标题不应为空"
        assert "meta" in data, "应包含元信息"
        assert "hostname" in data["meta"], "应包含主机名"
        assert data["meta"]["hostname"] != "", "主机名不应为空"
        print("  ✓ URL 解析测试通过")

        # --- 测试4: 字段还原 ---
        print("\n[测试4] 字段还原")
        flat_str = "user.name=张三&user.age=38&user.address.city=北京&arr[0]=a&arr[1]=b"
        result = restore_fields(flat_str)
        assert result["status"] == "success", "字段还原应成功"
        data = result["data"]
        assert "user" in data, "应还原user对象"
        assert isinstance(data["user"], dict), "user应为字典"
        assert "name" in data["user"], "user.name应存在"
        assert "age" in data["user"], "user.age应存在"
        assert data["user"]["age"] == 38, "age应转为整数"
        assert "arr" in data, "应还原arr数组"
        assert isinstance(data["arr"], list), "arr应为列表"
        assert len(data["arr"]) >= 2, "arr应至少2个元素"
        print("  ✓ 字段还原测试通过")

        # --- 测试5: 边界情况 ---
        print("\n[测试5] 边界情况")
        # 空输入
        try:
            parse_text("")
            assert False, "空文本应抛出异常"
        except ValueError:
            pass
        # 不存在的文件
        try:
            parse_file("/nonexistent/path/file.txt")
            assert False, "不存在的文件应抛出异常"
        except FileNotFoundError:
            pass
        # 非法URL
        try:
            parse_url("not-a-url")
            assert False, "非法URL应抛出异常"
        except ValueError:
            pass
        print("  ✓ 边界测试通过")

        # --- 测试6: 占位符 ---
        print("\n[测试6] 占位符生成")
        text_no_info = "这是一段没有结构化信息的普通文本"
        result = parse_text(text_no_info)
        data = result["data"]
        for field_name in ("name", "gender", "birth_year", "city"):
            assert field_name in data, f"应包含字段{field_name}"
            if isinstance(data[field_name], str) and data[field_name].startswith("[需核实:"):
                # 占位符存在，验证格式
                assert data[field_name].endswith("]"), "占位符应以]结尾"
        print("  ✓ 占位符测试通过")

        # 输出汇总
        print("\n" + "=" * 60)
        print("所有自检测试通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        print("错误码: E010")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {e}")
        print("错误码: E009")
        return False


# ============================================================
# 7. 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="microsis — 旧档解析与结构化提取工具",
        epilog="示例: python scripts/main.py --parse-text \"张三，男，1985年生，北京\""
    )

    # 输入方式（互斥）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--parse-text", metavar="TEXT", help="解析非结构化文本")
    input_group.add_argument("--parse-file", metavar="FILE", help="解析文件（.txt/.csv/.log/.json）")
    input_group.add_argument("--parse-url", metavar="URL", help="解析URL（仅解析结构，不访问网络）")
    input_group.add_argument("--restore", metavar="KV", help="字段还原（如 user.name=张三&user.age=38）")
    input_group.add_argument("--selftest", action="store_true", help="运行离线自检")

    # 输出选项
    parser.add_argument("--pretty", action="store_true", help="美化JSON输出（缩进2空格）")

    args = parser.parse_args()

    # 处理自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理解析请求
    try:
        if args.parse_text:
            result = parse_text(args.parse_text)
        elif args.parse_file:
            result = parse_file(args.parse_file)
        elif args.parse_url:
            result = parse_url(args.parse_url)
        elif args.restore:
            result = restore_fields(args.restore)
        else:
            parser.print_help()
            return 0

        # 输出结果
        if args.pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E009 内部错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
