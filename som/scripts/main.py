#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - SQL查询 (som) 技能实现

本脚本根据功能规格独立实现（clean-room），提供以下能力：
1. 解析输入内容，识别关键信息并结构化
2. 按默认模板组织输出
3. 对不确定项标注置信度
4. 支持批量处理和自定义格式
5. 内置离线自检（--selftest）
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：文本内容、JSON数据、文件路径或URL",
    "E004": "这超出了本工具的能力范围，建议使用专业工具处理",
    "E005": "结果无法确定，建议：请提供更多上下文信息或人工复核",
    "E006": "内部处理错误：数据解析失败，请检查输入格式",
    "E007": "内部处理错误：输出生成失败，请重试",
    "E008": "参数错误：请检查命令行参数",
    "E009": "批量处理错误：部分输入项处理失败",
    "E010": "未知错误：请查看日志或联系管理员",
}


class SkillError(Exception):
    """技能处理异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class StructuredItem:
    """结构化输出项"""

    def __init__(self, key: str, value: Any, confidence: float = 1.0):
        self.key = key
        self.value = value
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
        }


class ProcessingResult:
    """处理结果"""

    def __init__(self, items: List[StructuredItem], confidence: float):
        self.items = items
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "confidence": self.confidence,
            "confidence_label": get_confidence_label(self.confidence),
        }


# ============================================================
# 能力边界检测
# ============================================================

# 超出能力范围的关键词模式
OUT_OF_SCOPE_PATTERNS = [
    r'法律\s*合同',
    r'合同\s*起草',
    r'法律\s*建议',
    r'法律\s*咨询',
    r'医疗\s*诊断',
    r'药物\s*处方',
    r'投资\s*建议',
    r'税务\s*筹划',
    r'心理咨询',
    r'情感\s*咨询',
]

# 需要专业领域知识的场景模式
PROFESSIONAL_DOMAIN_PATTERNS = {
    '法律': r'合同|诉讼|法律|律师|起诉|判决',
    '医疗': r'诊断|治疗|手术|药物|病症|处方',
    '金融': r'投资|股票|基金|理财|股市',
    '心理咨询': r'抑郁|焦虑|心理|情绪|压力',
}


def detect_out_of_scope(text: str) -> Tuple[bool, str, float]:
    """
    检测输入是否超出能力范围
    
    返回: (是否超出范围, 检测到的领域, 置信度降低系数)
    """
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, "专业领域", 0.3
    
    # 检测专业领域关键词
    for domain, pattern in PROFESSIONAL_DOMAIN_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return True, domain, 0.35
    
    return False, "", 1.0


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: Any) -> str:
    """校验输入，返回字符串形式的输入内容"""
    if raw_input is None:
        raise SkillError("E001")

    if isinstance(raw_input, str):
        text = raw_input.strip()
    elif isinstance(raw_input, (dict, list)):
        text = json.dumps(raw_input, ensure_ascii=False)
    else:
        text = str(raw_input).strip()

    if not text:
        raise SkillError("E001")

    return text


def parse_input(text: str) -> Dict[str, Any]:
    """解析输入内容，识别关键信息"""
    parsed: Dict[str, Any] = {
        "raw_text": text,
        "content_type": "text",
        "key_fields": {},
        "has_url": False,
        "has_file_path": False,
        "out_of_scope": False,
        "out_of_scope_domain": "",
    }

    # 检测是否超出能力范围
    out_of_scope, domain, _ = detect_out_of_scope(text)
    if out_of_scope:
        parsed["out_of_scope"] = True
        parsed["out_of_scope_domain"] = domain

    # 检测URL
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(text)
    if urls:
        parsed["has_url"] = True
        parsed["key_fields"]["url"] = urls[0]

    # 检测文件路径（简单判断）
    file_pattern = re.compile(r'[\w\-/\\]+\.\w{1,10}')
    files = file_pattern.findall(text)
    if files:
        parsed["has_file_path"] = True
        parsed["key_fields"]["file_path"] = files[0]

    # 尝试解析JSON
    try:
        json_data = json.loads(text)
        parsed["content_type"] = "json"
        parsed["key_fields"]["json_data"] = json_data
    except (json.JSONDecodeError, ValueError):
        pass

    # 提取关键字段（通用模式）- 支持中英文
    key_patterns = {
        "名称": r'(?:名称|姓名|name)\s*[=:：]\s*([^\s,，。；;]+)',
        "编号": r'(?:编号|ID|id)\s*[=:：]\s*([^\s,，。；;]+)',
        "类型": r'(?:类型|type)\s*[=:：]\s*([^\s,，。；;]+)',
        "状态": r'(?:状态|status)\s*[=:：]\s*([^\s,，。；;]+)',
        "时间": r'(?:时间|日期|date)\s*[=:：]\s*([^\s,，。；;]+)',
        "地点": r'(?:地点|位置|location)\s*[=:：]\s*([^\s,，。；;]+)',
        "数量": r'(?:数量|金额|数量)\s*[=:：]\s*([^\s,，。；;]+)',
    }
    for key, pattern in key_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed["key_fields"][key] = match.group(1)

    return parsed


def extract_key_info(parsed: Dict[str, Any]) -> List[StructuredItem]:
    """从解析结果中提取关键信息，生成结构化条目"""
    items: List[StructuredItem] = []
    key_fields = parsed.get("key_fields", {})

    # 如果超出能力范围，返回低置信度的提示条目
    if parsed.get("out_of_scope"):
        domain = parsed.get("out_of_scope_domain", "专业领域")
        items.append(StructuredItem(
            "能力边界提示",
            f"该请求涉及{domain}专业领域，超出本工具处理范围，建议咨询专业人士",
            0.2
        ))
        return items

    if not key_fields:
        # 无关键字段时，提取文本片段
        text = parsed.get("raw_text", "")
        if len(text) > 50:
            snippet = text[:50] + "..."
        else:
            snippet = text
        items.append(StructuredItem("content", snippet, 0.8))
        return items

    # 为每个关键字段生成条目
    for key, value in key_fields.items():
        confidence = 0.9 if key in ("url", "file_path") else 0.85
        items.append(StructuredItem(key, value, confidence))

    return items


def calculate_confidence(items: List[StructuredItem], parsed: Dict[str, Any]) -> float:
    """计算整体置信度"""
    if not items:
        return 0.0

    # 如果超出能力范围，直接返回低置信度
    if parsed.get("out_of_scope"):
        return 0.2

    # 基础置信度
    base = 0.85

    # 有URL或文件路径时提高置信度
    if parsed.get("has_url") or parsed.get("has_file_path"):
        base += 0.05

    # 有JSON数据时提高置信度
    if parsed.get("content_type") == "json":
        base += 0.05

    # 关键字段多时提高置信度
    if len(parsed.get("key_fields", {})) >= 3:
        base += 0.05

    # 限制在0-1之间
    return max(0.0, min(1.0, base))


def get_confidence_label(confidence: float) -> str:
    """根据置信度生成标签"""
    if confidence >= 0.90:
        return "直接输出"
    elif confidence >= 0.85:
        return "建议复核"
    else:
        return "[需核实]"


def generate_output(result: ProcessingResult, output_format: str = "json") -> Any:
    """生成输出结果"""
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        for item in result.items:
            lines.append(f"{item.key}: {item.value} (置信度: {item.confidence:.0%})")
        lines.append(f"整体置信度: {result.confidence:.0%} ({get_confidence_label(result.confidence)})")
        return "\n".join(lines)
    else:
        raise SkillError("E003", f"不支持的输出格式: {output_format}")


def process_single(input_data: Any, output_format: str = "json") -> str:
    """处理单个输入，返回格式化结果"""
    try:
        # 校验输入
        text = validate_input(input_data)

        # 解析输入
        parsed = parse_input(text)

        # 提取关键信息
        items = extract_key_info(parsed)

        # 计算置信度
        confidence = calculate_confidence(items, parsed)

        # 生成结果
        result = ProcessingResult(items, confidence)
        return generate_output(result, output_format)

    except SkillError:
        raise
    except Exception as e:
        raise SkillError("E006", f"数据解析失败: {str(e)}")


def process_batch(input_list: List[Any], output_format: str = "json") -> List[str]:
    """批量处理多个输入"""
    results = []
    errors = []

    for i, item in enumerate(input_list):
        try:
            result = process_single(item, output_format)
            results.append({"index": i, "success": True, "result": result})
        except SkillError as e:
            errors.append({"index": i, "code": e.code, "message": e.message})
            results.append({"index": i, "success": False, "error": e.code})

    if errors and len(errors) == len(input_list):
        raise SkillError("E009", f"批量处理失败: {len(errors)}/{len(input_list)} 项失败")

    return results


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """内置自检逻辑，使用硬编码样例数据，不依赖外部文件"""
    print("=" * 60)
    print("自检开始 (离线模式，使用内置样例数据)")
    print("=" * 60)

    all_passed = True

    # 测试用例1: 基本文本输入
    print("\n[测试1] 基本文本输入...")
    try:
        result = process_single("名称：测试项目，类型：数据分析，状态：进行中", "json")
        assert result is not None, "结果不应为None"
        parsed_result = json.loads(result)
        assert "items" in parsed_result, "应包含items字段"
        assert len(parsed_result["items"]) >= 1, "应至少有一个条目"
        assert parsed_result["confidence"] > 0.5, "置信度应大于0.5"
        print("  PASS - 基本文本处理正常")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 测试用例2: JSON输入
    print("\n[测试2] JSON输入...")
    try:
        json_input = {"name": "项目A", "id": "001", "type": "测试"}
        result = process_single(json_input, "json")
        parsed_result = json.loads(result)
        assert parsed_result["confidence"] > 0.5, "JSON输入置信度应较高"
        print("  PASS - JSON处理正常")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 测试用例3: 空输入错误处理
    print("\n[测试3] 空输入错误处理...")
    try:
        process_single("")
        all_passed = False
        print("  FAIL - 空输入应抛出E001错误")
    except SkillError as e:
        assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
        print("  PASS - 空输入正确返回E001")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 测试用例4: 批量处理
    print("\n[测试4] 批量处理...")
    try:
        batch_input = ["名称：A", "名称：B", "名称：C"]
        results = process_batch(batch_input, "json")
        assert len(results) == 3, "批量处理应返回3个结果"
        assert all(r["success"] for r in results), "所有批量项应成功"
        print("  PASS - 批量处理正常")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 测试用例5: 文本格式输出
    print("\n[测试5] 文本格式输出...")
    try:
        result = process_single("名称：测试项目", "text")
        assert isinstance(result, str), "文本输出应为字符串"
        assert "名称" in result, f"文本输出应包含'名称'字段，实际输出: {result}"
        print("  PASS - 文本格式输出正常")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 测试用例6: URL识别
    print("\n[测试6] URL识别...")
    try:
        result = process_single("请处理这个链接 https://example.com/data", "json")
        parsed_result = json.loads(result)
        url_items = [item for item in parsed_result["items"] if item["key"] == "url"]
        assert len(url_items) > 0, "应识别出URL"
        assert "example.com" in url_items[0]["value"], "URL值应正确"
        print("  PASS - URL识别正常")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 测试用例7: 置信度标签
    print("\n[测试7] 置信度标签...")
    try:
        assert get_confidence_label(0.95) == "直接输出"
        assert get_confidence_label(0.87) == "建议复核"
        assert get_confidence_label(0.80) == "[需核实]"
        print("  PASS - 置信度标签正确")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")

    # 测试用例8: 错误码完整性
    print("\n[测试8] 错误码完整性...")
    try:
        assert len(ERROR_CODES) >= 5, "应至少5个错误码"
        assert "E001" in ERROR_CODES and "E005" in ERROR_CODES
        print("  PASS - 错误码定义完整")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")

    # 测试用例9: 能力边界检查
    print("\n[测试9] 能力边界检查...")
    try:
        # 测试超出能力范围的输入
        result = process_single("帮我写一份法律合同", "json")
        parsed_result = json.loads(result)
        assert parsed_result["confidence"] < 0.5, f"法律合同应低置信度，实际置信度: {parsed_result['confidence']}"
        assert parsed_result["confidence_label"] == "[需核实]", "应标记为需核实"
        print("  PASS - 能力边界正确处理")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 测试用例10: 批量错误处理
    print("\n[测试10] 批量错误处理...")
    try:
        batch_input = ["有效输入", ""]  # 第二个为空
        results = process_batch(batch_input, "json")
        assert results[0]["success"], "第一个应成功"
        assert not results[1]["success"], "第二个应失败"
        print("  PASS - 批量错误处理正常")
    except AssertionError as e:
        all_passed = False
        print(f"  FAIL - {str(e)}")
    except SkillError as e:
        # 全失败时抛出E009
        assert e.code == "E009", f"错误码应为E009，实际为{e.code}"
        print("  PASS - 批量错误处理正常（E009）")
    except Exception as e:
        all_passed = False
        print(f"  FAIL - 异常: {str(e)}")

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SQL查询 (som) - 数据解析与结构化工具",
        epilog="示例: python main.py --input '名称：测试项目' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容（文本、JSON、文件路径或URL）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--batch", "-b", action="store_true",
                        help="批量处理模式（输入为JSON数组）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（离线，不依赖外部文件）")
    parser.add_argument("--version", action="version", version="som 1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print(f"错误: {ERROR_CODES['E001']}", file=sys.stderr)
        print("使用 --help 查看帮助，或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    try:
        if args.batch:
            # 批量模式：输入应为JSON数组
            try:
                batch_data = json.loads(args.input)
                if not isinstance(batch_data, list):
                    raise ValueError("批量模式输入应为JSON数组")
            except (json.JSONDecodeError, ValueError) as e:
                raise SkillError("E003", f"批量模式输入应为JSON数组: {str(e)}")

            results = process_batch(batch_data, args.format)
            # 输出批量结果
            output = json.dumps(results, ensure_ascii=False, indent=2)
            print(output)
        else:
            # 单条模式
            result = process_single(args.input, args.format)
            print(result)

        return 0

    except SkillError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未知错误 [E010]: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
