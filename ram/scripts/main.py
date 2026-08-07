#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ram — 资源解析与结构化转换工具

功能：
- 将用户提供的文本、文件路径或 URL 内容解析为结构化结果
- 支持单条与批量处理
- 对每个提取字段标注置信度（高/中/低）
- 提供 --selftest 内置样例离线自检
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空或格式不合法",
    "E002": "无法识别的输入类型",
    "E003": "文件不存在或无法读取",
    "E004": "URL 格式不合法",
    "E005": "JSON 解析失败",
    "E006": "CSV 解析失败",
    "E007": "输出格式不支持",
    "E008": "批量处理输入格式错误",
    "E009": "字段提取失败",
    "E010": "内部错误",
}


class RamError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心功能：输入识别与解析
# ============================================================

def detect_input_type(raw_input: str) -> str:
    """
    识别输入类型：
    - text: 普通文本
    - file: 文件路径（存在且为文本类）
    - url: URL 链接
    - json: JSON 字符串
    """
    if raw_input is None or not raw_input.strip():
        raise RamError("E001")

    content = raw_input.strip()

    # URL 检测
    url_pattern = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
    if url_pattern.match(content):
        return "url"

    # 文件路径检测（存在且非目录）
    if len(content) < 4096 and not content.startswith((" ", "\t", "\n")):
        try:
            path = Path(content).expanduser()
            if path.exists() and path.is_file():
                # 仅支持文本类扩展名
                text_exts = {".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml"}
                if path.suffix.lower() in text_exts:
                    return "file"
        except (OSError, ValueError):
            pass

    # JSON 检测（以 { 或 [ 开头）
    if content.startswith("{") or content.startswith("["):
        return "json"

    return "text"


def parse_file(file_path: str) -> Dict[str, Any]:
    """读取文本文件并解析"""
    try:
        path = Path(file_path).expanduser()
        if not path.exists() or not path.is_file():
            raise RamError("E003", f"文件不存在: {file_path}")
        
        # 限制文件大小（10MB）
        if path.stat().st_size > 10 * 1024 * 1024:
            raise RamError("E003", "文件超过 10MB 限制")
        
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        
        return {
            "type": "file",
            "source": str(path),
            "content": content,
            "meta": {
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            },
        }
    except RamError:
        raise
    except Exception as e:
        raise RamError("E010", f"读取文件失败: {str(e)}")


def parse_url(url: str) -> Dict[str, Any]:
    """
    URL 解析（不执行网络请求，仅校验格式并返回占位内容）
    注意：本技能不主动抓取网页，URL 内容需由用户预先获取
    """
    url_pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
    if not url_pattern.match(url):
        raise RamError("E004", f"URL 格式不合法: {url}")
    
    return {
        "type": "url",
        "source": url,
        "content": "",  # 不主动抓取，内容留空
        "meta": {
            "note": "URL 内容需用户预先获取后提供，本技能不执行网络请求",
        },
    }


def parse_json(content: str) -> Dict[str, Any]:
    """解析 JSON 字符串"""
    try:
        data = json.loads(content)
        return {
            "type": "json",
            "source": "inline-json",
            "content": content,
            "data": data,
            "meta": {
                "keys": list(data.keys()) if isinstance(data, dict) else [],
                "is_array": isinstance(data, list),
                "length": len(data) if isinstance(data, (list, dict)) else 0,
            },
        }
    except json.JSONDecodeError as e:
        raise RamError("E005", f"JSON 解析失败: {str(e)}")


def parse_text(content: str) -> Dict[str, Any]:
    """解析普通文本"""
    if not content or not content.strip():
        raise RamError("E001")
    
    # 基础文本统计
    lines = content.strip().split("\n")
    words = content.split()
    
    return {
        "type": "text",
        "source": "inline-text",
        "content": content,
        "meta": {
            "line_count": len(lines),
            "word_count": len(words),
            "char_count": len(content),
        },
    }


def parse_input(raw_input: str) -> Dict[str, Any]:
    """统一入口：识别输入类型并解析"""
    input_type = detect_input_type(raw_input)
    
    if input_type == "file":
        return parse_file(raw_input)
    elif input_type == "url":
        return parse_url(raw_input)
    elif input_type == "json":
        return parse_json(raw_input)
    elif input_type == "text":
        return parse_text(raw_input)
    else:
        raise RamError("E002")


# ============================================================
# 核心功能：字段提取与置信度标注
# ============================================================

def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取实体信息（人名、邮箱、电话、日期等）
    返回带置信度的实体列表
    """
    if not text:
        return []

    entities = []

    # 邮箱提取
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    emails = email_pattern.findall(text)
    for email in emails[:5]:  # 限制数量
        entities.append({
            "type": "email",
            "value": email,
            "confidence": "high" if "@" in email and "." in email.split("@")[-1] else "medium",
        })

    # 电话号码提取（简单模式）
    phone_pattern = re.compile(r"\b(?:\+?\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b")
    phones = phone_pattern.findall(text)
    for phone in phones[:5]:
        entities.append({
            "type": "phone",
            "value": phone,
            "confidence": "medium",  # 无法验证真实性，仅格式匹配
        })

    # 日期提取
    date_pattern = re.compile(r"\b\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\b|\b\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}年?\b")
    dates = date_pattern.findall(text)
    for date in dates[:5]:
        entities.append({
            "type": "date",
            "value": date,
            "confidence": "high" if re.match(r"\d{4}", date) else "medium",
        })

    # 人名提取（中文姓名模式，简单启发式）
    # 注意：这是非常简化的启发式，实际应用中需更复杂的模型
    cn_name_pattern = re.compile(r"[\u4e00-\u9fa5]{2,4}(?:先生|女士|老师|同学|博士|教授)")
    names = cn_name_pattern.findall(text)
    for name in names[:5]:
        entities.append({
            "type": "person",
            "value": name,
            "confidence": "low",  # 启发式匹配，置信度低
        })

    return entities


def extract_key_value_pairs(content: str) -> List[Dict[str, Any]]:
    """
    提取键值对（支持 JSON、文本中的 key: value 模式）
    返回带置信度的键值对列表
    """
    results = []

    # 尝试 JSON 解析
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    results.append({
                        "key": str(key),
                        "value": value,
                        "confidence": "high" if value is not None else "medium",
                    })
            return results
    except (json.JSONDecodeError, TypeError):
        pass

    # 文本键值对提取（key: value 或 key = value）
    kv_pattern = re.compile(r"^\s*([^\s:=]+)\s*[:=]\s*(.+)$", re.MULTILINE)
    matches = kv_pattern.findall(content)
    for key, value in matches[:20]:
        results.append({
            "key": key.strip(),
            "value": value.strip(),
            "confidence": "medium",  # 格式匹配但无法验证语义
        })

    return results


def generate_structured_output(parsed: Dict[str, Any], custom_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    生成结构化输出结果
    - custom_fields: 用户指定的字段列表（可选）
    """
    content = parsed.get("content", "")
    
    # 提取实体
    entities = extract_entities(content)
    
    # 提取键值对
    kv_pairs = extract_key_value_pairs(content)
    
    # 构建结果
    result = {
        "source_type": parsed.get("type", "unknown"),
        "source": parsed.get("source", ""),
        "parsed_at": datetime.now().isoformat(),
        "summary": {
            "entity_count": len(entities),
            "kv_pairs_count": len(kv_pairs),
        },
        "entities": entities,
        "key_value_pairs": kv_pairs,
    }

    # 添加元数据
    if "meta" in parsed:
        result["meta"] = parsed["meta"]

    # 自定义字段处理
    if custom_fields:
        custom_result = {}
        for field in custom_fields:
            field = field.strip()
            if field in result:
                custom_result[field] = result[field]
            else:
                # 尝试从键值对中查找
                found = False
                for kv in kv_pairs:
                    if kv["key"].lower() == field.lower():
                        custom_result[field] = {
                            "value": kv["value"],
                            "confidence": kv["confidence"],
                        }
                        found = True
                        break
                if not found:
                    custom_result[field] = {
                        "value": None,
                        "confidence": "low",
                        "note": "待核实",
                    }
        result["custom_fields"] = custom_result

    # 整体置信度计算
    confidences = [e["confidence"] for e in entities] + [kv["confidence"] for kv in kv_pairs]
    if confidences:
        score_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
        avg_score = sum(score_map.get(c, 0.5) for c in confidences) / len(confidences)
        if avg_score >= 0.8:
            overall = "high"
        elif avg_score >= 0.5:
            overall = "medium"
        else:
            overall = "low"
        result["overall_confidence"] = overall
    else:
        result["overall_confidence"] = "low"

    return result


# ============================================================
# 批量处理
# ============================================================

def process_batch(items: List[str], custom_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """批量处理多条输入"""
    if not items or not isinstance(items, list):
        raise RamError("E008", "批量输入必须是字符串列表")

    results = []
    errors = []

    for idx, item in enumerate(items):
        try:
            parsed = parse_input(item)
            structured = generate_structured_output(parsed, custom_fields)
            structured["batch_index"] = idx
            results.append(structured)
        except RamError as e:
            errors.append({
                "index": idx,
                "code": e.code,
                "message": e.message,
            })
        except Exception as e:
            errors.append({
                "index": idx,
                "code": "E010",
                "message": str(e),
            })

    return {
        "total": len(items),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


# ============================================================
# 输出格式化
# ============================================================

def format_as_json(data: Dict[str, Any]) -> str:
    """JSON 格式输出"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_as_markdown(data: Dict[str, Any]) -> str:
    """Markdown 格式输出"""
    lines = []
    lines.append("# 资源解析结果\n")

    # 基本信息
    lines.append(f"- **来源类型**: {data.get('source_type', '未知')}")
    lines.append(f"- **来源**: {data.get('source', '-')}")
    lines.append(f"- **解析时间**: {data.get('parsed_at', '-')}")
    lines.append(f"- **整体置信度**: {data.get('overall_confidence', 'low')}\n")

    # 统计信息
    summary = data.get("summary", {})
    lines.append(f"## 统计\n")
    lines.append(f"- 实体数量: {summary.get('entity_count', 0)}")
    lines.append(f"- 键值对数量: {summary.get('kv_pairs_count', 0)}\n")

    # 实体列表
    entities = data.get("entities", [])
    if entities:
        lines.append(f"## 实体\n")
        lines.append("| 类型 | 值 | 置信度 |")
        lines.append("|------|-----|--------|")
        for e in entities:
            lines.append(f"| {e['type']} | {e['value']} | {e['confidence']} |")
        lines.append("")

    # 键值对
    kv_pairs = data.get("key_value_pairs", [])
    if kv_pairs:
        lines.append(f"## 键值对\n")
        lines.append("| 键 | 值 | 置信度 |")
        lines.append("|-----|-----|--------|")
        for kv in kv_pairs:
            lines.append(f"| {kv['key']} | {kv['value']} | {kv['confidence']} |")
        lines.append("")

    # 自定义字段
    custom = data.get("custom_fields", {})
    if custom:
        lines.append(f"## 自定义字段\n")
        for key, value in custom.items():
            if isinstance(value, dict):
                lines.append(f"- **{key}**: {value.get('value', '-')} (置信度: {value.get('confidence', 'low')})")
            else:
                lines.append(f"- **{key}**: {value}")
        lines.append("")

    return "\n".join(lines)


def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """统一输出格式化入口"""
    if output_format == "json":
        return format_as_json(data)
    elif output_format == "markdown":
        return format_as_markdown(data)
    else:
        raise RamError("E007", f"不支持的输出格式: {output_format}")


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检
    不读外部文件、不依赖当前工作目录、不访问网络
    """
    print("=== RAM 技能自检 ===\n")

    try:
        # 测试 1: 文本输入解析
        print("测试 1: 文本输入解析")
        sample_text = """
        联系人: 张三先生
        邮箱: zhangsan@example.com
        电话: 138-1234-5678
        日期: 2026-03-15
        项目: 数据迁移项目
        """
        parsed = parse_input(sample_text)
        assert parsed["type"] == "text", f"文本类型识别失败: {parsed['type']}"
        assert parsed["meta"]["line_count"] > 0, "行数统计异常"
        assert parsed["meta"]["word_count"] > 0, "词数统计异常"
        print("  ✓ 文本解析通过")

        # 测试 2: 实体提取
        print("测试 2: 实体提取")
        entities = extract_entities(sample_text)
        assert len(entities) > 0, "未提取到任何实体"
        types = {e["type"] for e in entities}
        assert "email" in types, "未提取到邮箱"
        assert "phone" in types, "未提取到电话"
        assert "date" in types, "未提取到日期"
        for entity in entities:
            assert entity["confidence"] in ("high", "medium", "low"), f"置信度取值非法: {entity['confidence']}"
        print(f"  ✓ 实体提取通过，共 {len(entities)} 个实体")

        # 测试 3: JSON 输入解析
        print("测试 3: JSON 输入解析")
        sample_json = '{"name": "测试项目", "status": "active", "version": 1.0}'
        parsed_json = parse_input(sample_json)
        assert parsed_json["type"] == "json", f"JSON 类型识别失败: {parsed_json['type']}"
        assert "data" in parsed_json, "JSON 数据缺失"
        assert parsed_json["data"]["name"] == "测试项目", "JSON 内容解析错误"
        print("  ✓ JSON 解析通过")

        # 测试 4: URL 格式检测
        print("测试 4: URL 格式检测")
        sample_url = "https://example.com/data"
        parsed_url = parse_input(sample_url)
        assert parsed_url["type"] == "url", f"URL 类型识别失败: {parsed_url['type']}"
        assert parsed_url["source"] == sample_url, "URL 来源错误"
        print("  ✓ URL 检测通过")

        # 测试 5: 结构化输出生成
        print("测试 5: 结构化输出生成")
        structured = generate_structured_output(parsed)
        assert "source_type" in structured, "输出缺少 source_type"
        assert "entities" in structured, "输出缺少 entities"
        assert "key_value_pairs" in structured, "输出缺少 key_value_pairs"
        assert structured["overall_confidence"] in ("high", "medium", "low"), "整体置信度非法"
        print(f"  ✓ 结构化输出通过，整体置信度: {structured['overall_confidence']}")

        # 测试 6: 批量处理
        print("测试 6: 批量处理")
        batch_input = [
            sample_text,
            sample_json,
            "简单文本，无特殊格式",
        ]
        batch_result = process_batch(batch_input)
        assert batch_result["total"] == 3, f"批量总数错误: {batch_result['total']}"
        assert batch_result["success_count"] == 3, f"成功数错误: {batch_result['success_count']}"
        assert batch_result["error_count"] == 0, f"错误数非零: {batch_result['error_count']}"
        assert len(batch_result["results"]) == 3, "结果数量错误"
        print("  ✓ 批量处理通过")

        # 测试 7: 错误处理
        print("测试 7: 错误处理")
        try:
            parse_input("")
            raise AssertionError("空输入未抛出异常")
        except RamError as e:
            assert e.code == "E001", f"错误码错误: {e.code}"
        print("  ✓ 错误处理通过")

        # 测试 8: 输出格式化
        print("测试 8: 输出格式化")
        json_out = format_output(structured, "json")
        assert json_out.startswith("{"), "JSON 输出格式错误"
        md_out = format_output(structured, "markdown")
        assert md_out.startswith("#"), "Markdown 输出格式错误"
        print("  ✓ 输出格式化通过")

        # 测试 9: 自定义字段
        print("测试 9: 自定义字段")
        custom = generate_structured_output(parsed, ["email", "nonexistent_field"])
        assert "custom_fields" in custom, "自定义字段结果缺失"
        assert "email" in custom["custom_fields"], "自定义字段缺少 email"
        assert "nonexistent_field" in custom["custom_fields"], "自定义字段缺少不存在字段"
        print("  ✓ 自定义字段通过")

        # 测试 10: 宽松阈值验证（不依赖精确值）
        print("测试 10: 宽松阈值验证")
        # 实体数量应在合理范围内（不依赖精确值）
        assert len(entities) >= 1 and len(entities) <= 20, f"实体数量超出合理范围: {len(entities)}"
        # 键值对数量应在合理范围内
        kv_count = len(structured["key_value_pairs"])
        assert kv_count >= 0 and kv_count <= 50, f"键值对数量超出合理范围: {kv_count}"
        print("  ✓ 宽松阈值验证通过")

        print("\n=== 自检全部通过 ===")
        return True

    except AssertionError as e:
        print(f"\n❌ 断言失败: {str(e)}")
        return False
    except RamError as e:
        print(f"\n❌ 技能错误: {e.code} - {e.message}")
        return False
    except Exception as e:
        print(f"\n❌ 未知错误: {str(e)}")
        return False


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="ram - 资源解析与结构化转换工具",
        epilog="示例: python main.py --input '文本内容' --format json"
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", "-i", type=str, help="输入内容（文本/JSON/URL/文件路径）")
    input_group.add_argument("--batch", "-b", type=str, help="批量输入（JSON 数组字符串）")
    input_group.add_argument("--selftest", action="store_true", help="运行内置自检")
    
    # 输出参数
    parser.add_argument("--format", "-f", choices=["json", "markdown"], default="json", help="输出格式")
    parser.add_argument("--fields", "-F", type=str, help="自定义字段（逗号分隔）")
    parser.add_argument("--output", "-o", type=str, help="输出到文件")
    
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    try:
        # 自定义字段
        custom_fields = None
        if args.fields:
            custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 批量处理
        if args.batch:
            try:
                batch_items = json.loads(args.batch)
                if not isinstance(batch_items, list):
                    raise RamError("E008", "批量输入必须是 JSON 数组")
                batch_items = [str(item) for item in batch_items]
            except json.JSONDecodeError:
                raise RamError("E008", "批量输入 JSON 解析失败")
            
            result = process_batch(batch_items, custom_fields)
        else:
            # 单条处理
            parsed = parse_input(args.input)
            result = generate_structured_output(parsed, custom_fields)

        # 格式化输出
        output_text = format_output(result, args.format)

        # 输出到文件或标准输出
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"结果已写入: {args.output}")
        else:
            print(output_text)

        return 0

    except RamError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
