#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rack-mirror 数据镜像结构化转换工具

功能：将用户输入的数据（文本/文件路径/URL）转换为结构化 JSON 结果，
      保留关键信息并标注置信度。
版本：1.0.1
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 配置常量
# ============================================================
MAX_INPUT_LENGTH = 5000          # 单次输入最大字符数
MAX_BATCH_SIZE = 20              # 批量处理最大条数
ERROR_CODES = {
    "E001": "输入为空或无效",
    "E002": "输入超过长度限制",
    "E003": "批量处理超过条数限制",
    "E004": "文件不存在或不可读",
    "E005": "URL 访问失败",
    "E006": "JSON 解析失败",
    "E007": "HTML 解析失败",
    "E008": "模板格式错误",
    "E009": "内部处理错误",
    "E010": "不支持的输入类型",
}


# ============================================================
# 核心工具函数
# ============================================================

def make_error(code: str, message: str = "") -> Dict[str, Any]:
    """构造标准错误结构"""
    return {
        "error": {
            "code": code,
            "message": message or ERROR_CODES.get(code, "未知错误")
        }
    }


def truncate_text(text: str, max_len: int = MAX_INPUT_LENGTH) -> Tuple[str, bool]:
    """截断文本，返回 (截断后文本, 是否被截断)"""
    if len(text) <= max_len:
        return text, False
    return text[:max_len], True


def confidence_label(score: float) -> str:
    """将 0-1 分数映射为 高/中/低 标签"""
    if score >= 0.8:
        return "高"
    elif score >= 0.5:
        return "中"
    return "低"


# ============================================================
# 实体提取模块
# ============================================================

def extract_entities(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    从纯文本中提取关键实体（人名、日期、金额、地址、编号）
    返回格式: {"entity_type": [{"value": ..., "confidence": ...}]}
    """
    entities: Dict[str, List[Dict[str, Any]]] = {
        "人名": [], "日期": [], "金额": [], "地址": [], "编号": []
    }
    if not text:
        return entities

    # 人名提取（简单模式：中文姓名 2-4 字，或英文姓名）
    name_patterns = [
        r'[\u4e00-\u9fa5]{2,4}(?=[，。,.\s]|$)',
        r'[A-Z][a-z]+\s[A-Z][a-z]+',
    ]
    for pattern in name_patterns:
        for match in re.finditer(pattern, text):
            value = match.group().strip()
            if value and value not in [e["value"] for e in entities["人名"]]:
                entities["人名"].append({
                    "value": value,
                    "confidence": 0.7 if len(value) >= 2 else 0.5
                })

    # 日期提取（支持多种格式）
    date_patterns = [
        r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?',
        r'\d{4}年\d{1,2}月\d{1,2}日',
        r'\d{1,2}月\d{1,2}日',
    ]
    for pattern in date_patterns:
        for match in re.finditer(pattern, text):
            value = match.group()
            entities["日期"].append({"value": value, "confidence": 0.8})

    # 金额提取
    money_pattern = r'[¥￥]\s?\d+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?\s*(?:元|人民币|RMB)'
    for match in re.finditer(money_pattern, text):
        value = match.group()
        entities["金额"].append({"value": value, "confidence": 0.85})

    # 地址提取（简单模式：包含省市或路/街）
    addr_pattern = r'[\u4e00-\u9fa5]{2,}(?:省|市|区|县)[\u4e00-\u9fa5]*(?:路|街|大道|巷|号)'
    for match in re.finditer(addr_pattern, text):
        value = match.group()
        entities["地址"].append({"value": value, "confidence": 0.6})

    # 编号提取（订单号、编号等）
    id_pattern = r'(?:编号|订单号|No\.?|ID)[:：\s]*([A-Za-z0-9\-_]{4,20})'
    for match in re.finditer(id_pattern, text, re.IGNORECASE):
        value = match.group(1)
        entities["编号"].append({"value": value, "confidence": 0.75})

    # 去重
    for key in entities:
        seen = set()
        unique = []
        for item in entities[key]:
            if item["value"] not in seen:
                seen.add(item["value"])
                unique.append(item)
        entities[key] = unique

    return entities


def extract_titles(text: str, is_markdown: bool = False, is_html: bool = False) -> List[Dict[str, Any]]:
    """提取标题层级结构"""
    titles = []
    if is_html:
        # HTML 标题提取
        pattern = r'<h([1-6])[^>]*>(.*?)</h\1>'
        for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            level = int(match.group(1))
            title_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            if title_text:
                titles.append({
                    "level": level,
                    "text": title_text,
                    "confidence": 0.9
                })
    elif is_markdown:
        # Markdown 标题提取
        pattern = r'^(#{1,6})\s+(.+)$'
        for line in text.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                level = len(match.group(1))
                title_text = match.group(2).strip()
                titles.append({
                    "level": level,
                    "text": title_text,
                    "confidence": 0.85
                })
    return titles


def extract_description(text: str) -> str:
    """从文本中提取描述（取前 200 字符）"""
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned[:200]


def extract_keywords(text: str) -> List[Dict[str, str]]:
    """提取关键词（基于词频统计的简单实现）"""
    # 中文分词简化版：按标点/空格切分，统计高频词
    words = re.findall(r'[\u4e00-\u9fa5]{2,}|[A-Za-z]{3,}', text.lower())
    word_count: Dict[str, int] = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1

    # 排序取前 10
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
    keywords = []
    for word, count in sorted_words:
        if count >= 2:  # 至少出现 2 次才认为关键词
            keywords.append({
                "keyword": word,
                "frequency": count,
                "confidence": min(0.5 + count * 0.1, 0.95)
            })
    return keywords


# ============================================================
# 输入解析模块
# ============================================================

def parse_input(raw_input: str) -> Tuple[str, Dict[str, Any]]:
    """
    解析输入，返回 (解析后的文本, 元信息)
    支持：纯文本、Markdown、HTML、JSON
    """
    meta = {
        "input_type": "text",
        "truncated": False,
        "length": 0
    }

    if not raw_input or not raw_input.strip():
        return "", meta

    # 检查长度
    if len(raw_input) > MAX_INPUT_LENGTH:
        raw_input, truncated = truncate_text(raw_input)
        meta["truncated"] = True

    stripped = raw_input.strip()
    meta["length"] = len(stripped)

    # 检测 HTML
    if re.search(r'<html[\s>]|<body[\s>]|<div[\s>]', stripped, re.IGNORECASE):
        meta["input_type"] = "html"
        # 提取纯文本
        text = re.sub(r'<script[^>]*>.*?</script>', '', stripped, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text, meta

    # 检测 Markdown
    if re.search(r'^#{1,6}\s', stripped, re.MULTILINE) or re.search(r'\*\*.*?\*\*', stripped):
        meta["input_type"] = "markdown"
        # 去除 Markdown 标记
        text = re.sub(r'[#>*_`~\-]', ' ', stripped)
        text = re.sub(r'\s+', ' ', text).strip()
        return text, meta

    # 检测 JSON
    if stripped.startswith('{') or stripped.startswith('['):
        try:
            json.loads(stripped)
            meta["input_type"] = "json"
        except json.JSONDecodeError:
            pass  # 不是有效 JSON，按普通文本处理

    return stripped, meta


# ============================================================
# 文件与 URL 处理模块
# ============================================================

def read_file(filepath: str) -> Tuple[str, Dict[str, Any]]:
    """读取本地文件"""
    if not os.path.exists(filepath):
        return "", make_error("E004", f"文件不存在: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, {"source": "file", "path": filepath}
    except Exception as e:
        return "", make_error("E004", f"文件读取失败: {str(e)}")


def fetch_url(url: str) -> Tuple[str, Dict[str, Any]]:
    """抓取 URL 内容"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
        return content, {"source": "url", "url": url}
    except Exception as e:
        return "", make_error("E005", f"URL 访问失败: {str(e)}")


# ============================================================
# 核心处理函数
# ============================================================

def process_single(raw_input: str, template: Optional[Dict] = None) -> Dict[str, Any]:
    """处理单条输入"""
    try:
        # 解析输入
        text, meta = parse_input(raw_input)
        if not text and meta["input_type"] == "text":
            return make_error("E001", "输入内容为空")

        # 提取实体
        entities = extract_entities(text)

        # 提取标题
        titles = extract_titles(
            raw_input,
            is_markdown=(meta["input_type"] == "markdown"),
            is_html=(meta["input_type"] == "html")
        )

        # 提取描述和关键词
        description = extract_description(text)
        keywords = extract_keywords(text)

        # 计算整体置信度
        entity_count = sum(len(v) for v in entities.values())
        confidence_score = min(0.3 + entity_count * 0.1 + len(keywords) * 0.05, 0.95)
        confidence = confidence_label(confidence_score)

        # 构造结果
        result = {
            "content": {
                "text": text,
                "length": len(text),
                "entities": entities,
                "titles": titles,
                "description": description,
                "keywords": keywords,
            },
            "meta": {
                "input_type": meta["input_type"],
                "truncated": meta["truncated"],
                "processed_at": datetime.now().isoformat(),
                "version": "1.0.1",
                **{k: v for k, v in meta.items() if k not in ["input_type", "truncated"]}
            },
            "confidence": {
                "score": round(confidence_score, 2),
                "label": confidence
            }
        }

        # 应用模板（如果提供）
        if template:
            result = apply_template(result, template)

        return result

    except Exception as e:
        return make_error("E009", f"处理失败: {str(e)}")


def apply_template(data: Dict[str, Any], template: Dict) -> Dict[str, Any]:
    """根据模板重组输出结构"""
    try:
        if not isinstance(template, dict) or "fields" not in template:
            return make_error("E008", "模板格式错误：缺少 fields 字段")

        result = {}
        for field_name, field_spec in template["fields"].items():
            if isinstance(field_spec, str):
                # 简单字段路径映射
                keys = field_spec.split(".")
                value = data
                try:
                    for key in keys:
                        if isinstance(value, dict):
                            value = value.get(key, "")
                        elif isinstance(value, list) and key.isdigit():
                            value = value[int(key)]
                        else:
                            value = ""
                            break
                except (KeyError, IndexError, TypeError):
                    value = ""
                result[field_name] = value
            elif isinstance(field_spec, dict) and "source" in field_spec:
                # 带默认值的字段
                keys = field_spec["source"].split(".")
                value = data
                try:
                    for key in keys:
                        if isinstance(value, dict):
                            value = value.get(key, "")
                        else:
                            value = ""
                            break
                except (KeyError, TypeError):
                    value = ""
                result[field_name] = value or field_spec.get("default", "")
            else:
                result[field_name] = None

        return result
    except Exception as e:
        return make_error("E008", f"模板应用失败: {str(e)}")


def process_batch(inputs: List[str], template: Optional[Dict] = None) -> Dict[str, Any]:
    """批量处理"""
    if len(inputs) > MAX_BATCH_SIZE:
        return make_error("E003", f"批量处理超过 {MAX_BATCH_SIZE} 条限制")

    results = []
    for item in inputs:
        result = process_single(item, template)
        results.append(result)

    return {
        "content": {
            "count": len(results),
            "items": results
        },
        "meta": {
            "batch": True,
            "total": len(results),
            "processed_at": datetime.now().isoformat()
        },
        "confidence": {
            "score": round(sum(r.get("confidence", {}).get("score", 0) for r in results) / len(results), 2) if results else 0,
            "label": confidence_label(sum(r.get("confidence", {}).get("score", 0) for r in results) / len(results)) if results else "低"
        }
    }


# ============================================================
# 自检模块（selftest）
# ============================================================

def run_selftest() -> int:
    """内置硬编码样例自检核心逻辑"""
    print("=== rack-mirror 自检开始 ===")
    errors = []

    # 测试 1: 基本文本处理
    test_text = "张三于2024年3月15日向北京市朝阳区幸福路88号支付了￥12,500元，订单号:ORD-20240315-001。"
    result = process_single(test_text)
    assert result.get("content"), "基本文本处理失败：缺少 content"
    assert result["content"]["length"] > 0, "基本文本处理失败：文本为空"
    assert result["meta"]["input_type"] == "text", "基本文本处理失败：输入类型错误"
    assert result["confidence"]["label"] in ["高", "中", "低"], "基本文本处理失败：置信度标签无效"
    print("  [PASS] 基本文本处理")

    # 测试 2: 实体提取
    entities = result["content"]["entities"]
    assert isinstance(entities, dict), "实体提取失败：格式错误"
    assert len(entities) > 0, "实体提取失败：无实体"
    print("  [PASS] 实体提取")

    # 测试 3: 输入长度限制
    long_text = "A" * (MAX_INPUT_LENGTH + 100)
    result_long = process_single(long_text)
    assert result_long["meta"]["truncated"] is True, "长度限制失败：未截断"
    assert len(result_long["content"]["text"]) <= MAX_INPUT_LENGTH, "长度限制失败：截断后仍超长"
    print("  [PASS] 输入长度限制")

    # 测试 4: 空输入
    result_empty = process_single("")
    assert "error" in result_empty, "空输入处理失败：未返回错误"
    assert result_empty["error"]["code"] == "E001", "空输入处理失败：错误码不正确"
    print("  [PASS] 空输入处理")

    # 测试 5: Markdown 处理
    md_text = "# 标题一\n## 标题二\n这是正文内容。"
    result_md = process_single(md_text)
    assert result_md["meta"]["input_type"] == "markdown", "Markdown 处理失败：类型识别错误"
    assert len(result_md["content"]["titles"]) >= 2, "Markdown 处理失败：标题提取不足"
    print("  [PASS] Markdown 处理")

    # 测试 6: HTML 处理
    html_text = "<html><body><h1>页面标题</h1><p>这是描述文字。</p></body></html>"
    result_html = process_single(html_text)
    assert result_html["meta"]["input_type"] == "html", "HTML 处理失败：类型识别错误"
    assert len(result_html["content"]["titles"]) >= 1, "HTML 处理失败：标题提取失败"
    print("  [PASS] HTML 处理")

    # 测试 7: 批量处理
    batch_inputs = ["第一条测试数据", "第二条测试数据", "第三条测试数据"]
    result_batch = process_batch(batch_inputs)
    assert result_batch["content"]["count"] == 3, "批量处理失败：条数不正确"
    assert result_batch["confidence"]["score"] > 0, "批量处理失败：置信度异常"
    print("  [PASS] 批量处理")

    # 测试 8: 批量限制
    too_many = [str(i) for i in range(MAX_BATCH_SIZE + 1)]
    result_limit = process_batch(too_many)
    assert "error" in result_limit, "批量限制失败：未返回错误"
    assert result_limit["error"]["code"] == "E003", "批量限制失败：错误码不正确"
    print("  [PASS] 批量限制")

    # 测试 9: 模板应用
    template = {
        "fields": {
            "提取文本": "content.text",
            "实体数量": {"source": "content.entities", "default": "0"},
            "处理时间": "meta.processed_at"
        }
    }
    result_template = process_single(test_text, template)
    assert "提取文本" in result_template, "模板应用失败：缺少字段"
    assert result_template["提取文本"], "模板应用失败：字段值为空"
    print("  [PASS] 模板应用")

    # 测试 10: 错误处理
    assert "E001" in ERROR_CODES, "错误码表不完整"
    assert "E010" in ERROR_CODES, "错误码表不完整"
    assert len(ERROR_CODES) == 10, "错误码表数量不正确"
    print("  [PASS] 错误码体系")

    if errors:
        print(f"\n自检失败: {len(errors)} 个错误")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\n=== 自检全部通过 ===")
    return 0


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="rack-mirror 数据镜像结构化转换工具 v1.0.1",
        epilog="示例: python main.py --text '张三 2024年3月15日 ￥5000'"
    )
    parser.add_argument("--text", type=str, help="要处理的文本内容")
    parser.add_argument("--file", type=str, help="要处理的文件路径")
    parser.add_argument("--url", type=str, help="要处理的 URL")
    parser.add_argument("--template", type=str, help="JSON 模板文件路径")
    parser.add_argument("--batch", type=str, help="批量处理，JSON 数组格式的输入")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--output", type=str, help="输出文件路径（可选）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 加载模板
    template = None
    if args.template:
        try:
            with open(args.template, 'r', encoding='utf-8') as f:
                template = json.load(f)
        except Exception as e:
            print(json.dumps(make_error("E008", f"模板加载失败: {str(e)}"), ensure_ascii=False, indent=2))
            sys.exit(1)

    # 处理输入
    result = None
    if args.text:
        result = process_single(args.text, template)
    elif args.file:
        content, meta = read_file(args.file)
        if "error" in meta:
            result = meta
        else:
            result = process_single(content, template)
            result["meta"].update(meta)
    elif args.url:
        content, meta = fetch_url(args.url)
        if "error" in meta:
            result = meta
        else:
            result = process_single(content, template)
            result["meta"].update(meta)
    elif args.batch:
        try:
            batch_inputs = json.loads(args.batch)
            if not isinstance(batch_inputs, list):
                result = make_error("E006", "批量输入必须是 JSON 数组")
            else:
                result = process_batch(batch_inputs, template)
        except json.JSONDecodeError:
            result = make_error("E006", "批量输入 JSON 解析失败")
    else:
        # 无参数时从标准输入读取
        print("请输入要处理的内容（Ctrl+D 结束）：", file=sys.stderr)
        content = sys.stdin.read().strip()
        if content:
            result = process_single(content, template)
        else:
            result = make_error("E001", "未提供输入内容")

    # 输出结果
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"结果已写入: {args.output}", file=sys.stderr)
        except Exception as e:
            print(json.dumps(make_error("E009", f"输出写入失败: {str(e)}"), ensure_ascii=False, indent=2))
            sys.exit(1)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
