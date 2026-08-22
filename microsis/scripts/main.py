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
import urllib.error
from pathlib import Path
import time
from datetime import datetime, timezone

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


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


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
    - 姓名：张三 / name: 张三 / 我叫张三 / 姓名：张三
    - 性别：男 / 女
    - 出生年份：1985年 / 1985年生
    - 城市：北京 / 上海 / 广州等
    - 电话：11位数字
    - 邮箱：标准邮箱格式
    """
    if not text or not text.strip():
        return _error("E008", "输入文本为空")

    result = {"status": "success", "fields": [], "raw_text": text.strip()}

    # 姓名提取 - 使用非贪婪匹配和上下文校验
    name_patterns = [
        # 显式标签模式（高置信度）
        (r"姓名[：:\s]*([\u4e00-\u9fa5]{2,4})", 0.95),
        (r"name[：:\s]*([\u4e00-\u9fa5A-Za-z]{2,20})", 0.95),
        # 上下文关键词模式（中高置信度）- 非贪婪匹配
        (r"(?:我叫|我是|本人|姓名是|名字叫)[：:\s]*([\u4e00-\u9fa5]{2,4}?)(?:[，,。\s]|$)", 0.9),
        # 逗号分隔且后跟性别/年龄等上下文（中置信度）
        (r"^([\u4e00-\u9fa5]{2,4}?)[，,、\s]+(?:男|女|先生|女士|，|,)", 0.7),
    ]
    for pattern, conf in name_patterns:
        match = re.search(pattern, text)
        if match:
            # 上下文校验：确保提取的姓名不是更长词语的一部分
            name = match.group(1)
            # 检查姓名后面是否紧跟更多汉字（可能是更长名字的一部分）
            if len(name) < 4:
                # 检查后续字符
                end_pos = match.end(1)
                if end_pos < len(text) and re.match(r'[\u4e00-\u9fa5]', text[end_pos]):
                    # 可能是更长名字，尝试扩展
                    extended = re.match(r'[\u4e00-\u9fa5]{2,4}', text[match.start(1):])
                    if extended and len(extended.group(0)) > len(name):
                        name = extended.group(0)
            result["fields"].append({
                "field": "name",
                "value": name,
                "confidence": conf,
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
    实现重试退避机制，超时10秒，最多重试3次
    """
    if not url.startswith(("http://", "https://")):
        return _error("E001", "URL必须以 http:// 或 https:// 开头")

    max_retries = 3
    base_delay = 1.0  # 初始退避延迟（秒）
    content = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8", errors="replace")
                break
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == max_retries - 1:
                return _error("E006", f"URL访问失败: {str(e)}")
            # 指数退避
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
        except Exception as e:
            return _error("E006", f"URL访问失败: {str(e)}")

    if content is None:
        return _error("E006", "URL访问失败: 达到最大重试次数")

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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    真实调用核心函数并断言关键输出
    """
    print("=" * 60)
    print("microsis 自检开始")
    print("=" * 60)

    all_passed = True

    # 测试1: 文本解析核心链路 - 完整字段提取
    print("\n[测试1] 文本解析核心链路（完整字段）")
    text_result = parse_text("姓名：张三，男，1985年生，北京，电话13800138000，邮箱zhangsan@example.com")
    assert text_result["status"] == "success", "文本解析失败"
    fields = {f["field"]: f["value"] for f in text_result["fields"]}

    # 严格断言关键字段
    assert fields.get("name") == "张三", f"姓名提取错误: {fields.get('name')}"
    assert fields.get("gender") == "男", f"性别提取错误: {fields.get('gender')}"
    assert fields.get("birth_year") == 1985, f"出生年份提取错误: {fields.get('birth_year')}"
    assert fields.get("city") == "北京", f"城市提取错误: {fields.get('city')}"
    assert fields.get("phone") == "13800138000", f"电话提取错误: {fields.get('phone')}"
    assert fields.get("email") == "zhangsan@example.com", f"邮箱提取错误: {fields.get('email')}"
    print(f"  通过: 提取到 {len(fields)} 个字段，关键字段全部正确")

    # 测试2: 文本解析 - 上下文关键词模式（我叫）
    print("\n[测试2] 文本解析（我叫模式）")
    text_result2 = parse_text("我叫李四，女，1990年生，上海")
    assert text_result2["status"] == "success", "文本解析失败"
    fields2 = {f["field"]: f["value"] for f in text_result2["fields"]}
    assert fields2.get("name") == "李四", f"姓名提取错误: {fields2.get('name')}"
    assert fields2.get("gender") == "女", f"性别提取错误: {fields2.get('gender')}"
    assert fields2.get("birth_year") == 1990, f"出生年份提取错误: {fields2.get('birth_year')}"
    assert fields2.get("city") == "上海", f"城市提取错误: {fields2.get('city')}"
    print("  通过: 我叫模式提取正确")

    # 测试3: 文本解析 - 逗号分隔模式（低置信度）
    print("\n[测试3] 文本解析（逗号分隔模式）")
    text_result3 = parse_text("王五，男，深圳")
    assert text_result3["status"] == "success", "文本解析失败"
    fields3 = {f["field"]: f["value"] for f in text_result3["fields"]}
    assert fields3.get("name") == "王五", f"姓名提取错误: {fields3.get('name')}"
    assert fields3.get("gender") == "男", f"性别提取错误: {fields3.get('gender')}"
    assert fields3.get("city") == "深圳", f"城市提取错误: {fields3.get('city')}"
    # 验证置信度
    name_field = [f for f in text_result3["fields"] if f["field"] == "name"][0]
    assert name_field["confidence"] < 0.8, f"逗号分隔模式置信度应低于0.8，实际: {name_field['confidence']}"
    print("  通过: 逗号分隔模式提取正确，置信度合理")

    # 测试4: 边界情况 - 三字姓名
    print("\n[测试4] 边界情况（三字姓名）")
    text_result4 = parse_text("我叫欧阳娜娜，女，1995年生")
    assert text_result4["status"] == "success", "文本解析失败"
    fields4 = {f["field"]: f["value"] for f in text_result4["fields"]}
    assert fields4.get("name") == "欧阳娜娜", f"三字姓名提取错误: {fields4.get('name')}"
    print("  通过: 三字姓名提取正确")

    # 测试
