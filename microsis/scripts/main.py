#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
microsis — 旧档解析与结构化提取工具

功能：
- 从非结构化文本中提取关键字段
- 解析常见文本文件（.txt/.csv/.log/.json）
- 将扁平键值对还原为嵌套结构
- 对提取字段进行置信度标注

用法：
    python main.py --selftest          # 离线自检
    python main.py --parse-text "文本"  # 解析文本
    python main.py --parse-file 路径    # 解析文件
    python main.py --parse-url URL     # 解析URL（需网络）
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "文件读取失败",
    "E004": "文件格式不支持",
    "E005": "JSON解析失败",
    "E006": "URL访问失败",
    "E007": "URL内容为空",
    "E008": "输入为空",
    "E009": "内部处理错误",
    "E010": "自检失败",
}


def _error(code: str, message: str = "") -> dict:
    """构造标准错误响应"""
    return {
        "status": "error",
        "error_code": code,
        "error_message": message or ERROR_CODES.get(code, "未知错误"),
    }


def parse_text(text: str) -> dict:
    """
    从非结构化文本中提取关键字段

    支持的模式：
    - 姓名：张三 / name: 张三
    - 性别：男 / 女
    - 出生年份：1985年 / 1985年生
    - 城市：北京 / 上海 / 广州等
    - 电话：11位数字
    - 邮箱：标准邮箱格式
    """
    if not text or not text.strip():
        return _error("E008", "输入文本为空")

    result = {"status": "success", "fields": [], "raw_text": text.strip()}

    # 姓名提取
    name_patterns = [
        r"姓名[：:\s]*([\u4e00-\u9fa5]{2,4})",
        r"name[：:\s]*([\u4e00-\u9fa5A-Za-z]{2,20})",
        r"^([\u4e00-\u9fa5]{2,4})[，,、\s]",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            result["fields"].append({
                "field": "name",
                "value": match.group(1),
                "confidence": 0.9,
            })
            break

    # 性别提取
    gender_match = re.search(r"[性别]?[：:\s]*([男女])", text)
    if gender_match:
        result["fields"].append({
            "field": "gender",
            "value": gender_match.group(1),
            "confidence": 0.95,
        })

    # 出生年份提取
    year_match = re.search(r"(\d{4})\s*年|(\d{4})\s*生", text)
    if year_match:
        year = year_match.group(1) or year_match.group(2)
        result["fields"].append({
            "field": "birth_year",
            "value": int(year),
            "confidence": 0.9,
        })

    # 城市提取
    cities = ["北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "重庆"]
    for city in cities:
        if city in text:
            result["fields"].append({
                "field": "city",
                "value": city,
                "confidence": 0.8,
            })
            break

    # 电话提取
    phone_match = re.search(r"1[3-9]\d{9}", text)
    if phone_match:
        result["fields"].append({
            "field": "phone",
            "value": phone_match.group(0),
            "confidence": 0.85,
        })

    # 邮箱提取
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    if email_match:
        result["fields"].append({
            "field": "email",
            "value": email_match.group(0),
            "confidence": 0.9,
        })

    return result


def parse_file(filepath: str) -> dict:
    """
    解析常见文本文件

    支持：.txt, .csv, .log, .json
    """
    path = Path(filepath)

    if not path.exists():
        return _error("E002", f"文件不存在: {filepath}")

    if path.suffix.lower() not in [".txt", ".csv", ".log", ".json"]:
        return _error("E004", f"不支持的文件格式: {path.suffix}")

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return _error("E003", f"文件读取失败: {str(e)}")

    # 根据文件类型处理
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(content)
            return {
                "status": "success",
                "format": "json",
                "data": data,
                "record_count": len(data) if isinstance(data, list) else 1,
            }
        except json.JSONDecodeError as e:
            return _error("E005", f"JSON解析失败: {str(e)}")

    elif path.suffix.lower() == ".csv":
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return _error("E008", "文件内容为空")

        header = [h.strip() for h in lines[0].split(",")]
        records = []
        for line in lines[1:]:
            values = [v.strip() for v in line.split(",")]
            record = {}
            for i, h in enumerate(header):
                record[h] = values[i] if i < len(values) else "[需核实:" + h + "]"
            records.append(record)

        return {
            "status": "success",
            "format": "csv",
            "data": records,
            "record_count": len(records),
        }

    else:  # .txt 或 .log
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return _error("E008", "文件内容为空")

        # 尝试解析每行，如果一行包含结构化信息则提取，否则作为原始行
        parsed_lines = []
        for line in lines:
            parsed = parse_text(line)
            if parsed["status"] == "success" and parsed["fields"]:
                parsed_lines.append(parsed["fields"])
            else:
                parsed_lines.append({"raw": line, "confidence": 0.5})

        return {
            "status": "success",
            "format": path.suffix[1:] if path.suffix else "txt",
            "data": parsed_lines,
            "record_count": len(parsed_lines),
        }


def parse_url(url: str) -> dict:
    """
    解析URL内容并提取元信息

    注意：此功能需要网络访问
    """
    if not url.startswith(("http://", "https://")):
        return _error("E001", "URL必须以 http:// 或 https:// 开头")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        return _error("E006", f"URL访问失败: {str(e)}")

    if not content or len(content.strip()) == 0:
        return _error("E007", "URL内容为空")

    # 提取标题
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "[需核实:title]"

    # 提取meta描述
    desc_match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
        content, re.IGNORECASE
    )
    description = desc_match.group(1).strip() if desc_match else ""

    # 提取正文前500字符
    text_content = re.sub(r"<[^>]+>", " ", content)
    text_content = re.sub(r"\s+", " ", text_content).strip()
    snippet = text_content[:500] if text_content else "[需核实:content]"

    return {
        "status": "success",
        "url": url,
        "title": title,
        "meta": {"description": description} if description else {},
        "content_snippet": snippet,
        "content_length": len(text_content),
    }


def flatten_to_nested(data: dict) -> dict:
    """
    将扁平键值对还原为嵌套结构

    例如：{"user.name": "张三", "user.age": 38} -> {"user": {"name": "张三", "age": 38}}
    """
    result = {}

    for key, value in data.items():
        parts = key.split(".")
        current = result

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    return result


def parse_key_value(text: str) -> dict:
    """
    解析键值对文本（支持点号嵌套）

    输入格式：key1=value1&key2=value2 或 key1=value1,key2=value2
    """
    if not text or not text.strip():
        return _error("E008", "输入为空")

    # 支持 & 或 , 或 ; 分隔
    pairs = re.split(r"[&,;]", text)
    flat_dict = {}

    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue

        if "=" not in pair:
            continue

        key, value = pair.split("=", 1)
        flat_dict[key.strip()] = value.strip()

    if not flat_dict:
        return _error("E001", "未找到有效的键值对")

    nested = flatten_to_nested(flat_dict)

    return {
        "status": "success",
        "data": nested,
        "fields": [
            {"field": k, "value": v, "confidence": 0.7}
            for k, v in flat_dict.items()
        ],
    }


def _selftest() -> bool:
    """
    内置自检函数，使用硬编码样例数据离线验证核心逻辑
    """
    print("=" * 60)
    print("microsis 自检开始")
    print("=" * 60)

    all_passed = True

    # 测试1: 文本解析
    print("\n[测试1] 文本解析")
    text_result = parse_text("张三，男，1985年生，北京，电话13800138000，邮箱zhangsan@example.com")
    assert text_result["status"] == "success", "文本解析失败"
    fields = {f["field"]: f["value"] for f in text_result["fields"]}

    # 宽松断言：只检查关键字段是否存在，不依赖精确值
    assert "name" in fields, "缺少姓名字段"
    assert "gender" in fields, "缺少性别字段"
    assert "birth_year" in fields, "缺少出生年份字段"
    assert "city" in fields, "缺少城市字段"
    print(f"  通过: 提取到 {len(fields)} 个字段")

    # 测试2: 空输入处理
    print("\n[测试2] 空输入处理")
    empty_result = parse_text("")
    assert empty_result["status"] == "error", "空输入应返回错误"
    assert empty_result["error_code"] == "E008", "错误码应为E008"
    print("  通过: 空输入正确返回错误")

    # 测试3: 键值对解析与嵌套还原
    print("\n[测试3] 键值对解析与嵌套还原")
    kv_result = parse_key_value("user.name=张三&user.age=38&user.address.city=北京")
    assert kv_result["status"] == "success", "键值对解析失败"
    assert "user" in kv_result["data"], "嵌套结构缺少user"
    assert "name" in kv_result["data"]["user"], "嵌套结构缺少name"
    assert "address" in kv_result["data"]["user"], "嵌套结构缺少address"
    assert kv_result["data"]["user"]["address"]["city"] == "北京", "嵌套城市错误"
    print("  通过: 嵌套结构还原正确")

    # 测试4: 文件解析（使用内存中的临时文件）
    print("\n[测试4] 文件解析")
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("姓名,年龄,城市\n张三,38,北京\n李四,25,上海\n")
        temp_path = f.name

    try:
        file_result = parse_file(temp_path)
        assert file_result["status"] == "success", "CSV解析失败"
        assert file_result["record_count"] == 2, "CSV记录数应为2"
        assert len(file_result["data"]) == 2, "CSV数据应包含2条记录"
        print("  通过: CSV解析正确")

        # 测试不存在的文件
        missing_result = parse_file("/nonexistent/file.txt")
        assert missing_result["status"] == "error", "不存在文件应返回错误"
        assert missing_result["error_code"] == "E002", "错误码应为E002"
        print("  通过: 不存在文件正确返回错误")
    finally:
        os.unlink(temp_path)

    # 测试5: JSON文件解析
    print("\n[测试5] JSON文件解析")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"key": "value", "nested": {"a": 1}}, f)
        temp_json_path = f.name

    try:
        json_result = parse_file(temp_json_path)
        assert json_result["status"] == "success", "JSON解析失败"
        assert json_result["format"] == "json", "格式应为json"
        assert "key" in json_result["data"], "JSON数据缺少key"
        assert json_result["data"]["nested"]["a"] == 1, "JSON嵌套数据错误"
        print("  通过: JSON解析正确")
    finally:
        os.unlink(temp_json_path)

    # 测试6: 不支持的文件格式
    print("\n[测试6] 不支持的文件格式")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".exe", delete=False) as f:
        f.write("binary content")
        temp_exe_path = f.name

    try:
        exe_result = parse_file(temp_exe_path)
        assert exe_result["status"] == "error", "不支持格式应返回错误"
        assert exe_result["error_code"] == "E004", "错误码应为E004"
        print("  通过: 不支持格式正确返回错误")
    finally:
        os.unlink(temp_exe_path)

    # 测试7: 扁平化嵌套还原
    print("\n[测试7] 扁平化嵌套还原")
    flat = {"a.b.c": 1, "a.b.d": 2, "a.e": 3, "f": 4}
    nested = flatten_to_nested(flat)
    assert nested["a"]["b"]["c"] == 1, "嵌套还原错误"
    assert nested["a"]["b"]["d"] == 2, "嵌套还原错误"
    assert nested["a"]["e"] == 3, "嵌套还原错误"
    assert nested["f"] == 4, "嵌套还原错误"
    print("  通过: 嵌套还原正确")

    # 测试8: 错误码完整性
    print("\n[测试8] 错误码完整性")
    required_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    for code in required_codes:
        assert code in ERROR_CODES, f"缺少错误码 {code}"
    print(f"  通过: 全部 {len(required_codes)} 个错误码已定义")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有自检通过")
    else:
        print("❌ 存在失败项")
    print("=" * 60)

    return all_passed


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="microsis — 旧档解析与结构化提取工具",
        epilog="示例: python main.py --parse-text \"张三，男，1985年生，北京\""
    )
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--parse-text", type=str, help="解析非结构化文本")
    parser.add_argument("--parse-file", type=str, help="解析文件路径")
    parser.add_argument("--parse-url", type=str, help="解析URL")
    parser.add_argument("--parse-key-value", type=str, help="解析键值对（支持点号嵌套）")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = _selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"E010: 自检失败 - {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"E009: 自检异常 - {str(e)}")
            sys.exit(1)

    # 各功能模式
    result = None

    if args.parse_text:
        result = parse_text(args.parse_text)
    elif args.parse_file:
        result = parse_file(args.parse_file)
    elif args.parse_url:
        result = parse_url(args.parse_url)
    elif args.parse_key_value:
        result = parse_key_value(args.parse_key_value)
    else:
        parser.print_help()
        return

    # 输出结果
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["status"] == "success":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"错误 [{result['error_code']}]: {result['error_message']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
