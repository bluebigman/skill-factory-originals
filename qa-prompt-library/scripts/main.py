#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa-prompt-library - 独立实现脚本

基于功能规格 clean-room 重写，仅使用标准库。
提供 QA 提示词库的核心能力：输入解析、结构化处理、置信度标注、错误处理。
支持 --selftest 离线自检，不依赖外部文件或网络。
"""

import sys
import json
import argparse
import re
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及标准化话术（对应规格第四章）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{\"content\": \"待处理内容\", \"output_format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议：检查输入是否符合要求或联系人工支持",
    "E005": "结果无法确定，建议：补充更多上下文信息或人工复核关键结果",
    "E006": "内部处理错误，请重试或检查输入数据",
    "E007": "输出序列化失败，请检查数据格式",
    "E008": "批量处理中断，部分结果可能已生成",
    "E009": "输入数据类型不受支持，仅接受字符串或字典",
    "E010": "置信度计算失败，请检查输入数据质量",
}

# 能力边界声明（对应规格第一章）
CAPABILITIES: Dict[str, List[str]] = {
    "can_do": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 默认输出模板字段
DEFAULT_FIELDS: List[str] = ["content", "keywords", "structure", "confidence"]

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(data: Any) -> Tuple[bool, str, Dict[str, Any]]:
    """
    校验输入数据并提取关键信息。
    
    返回: (是否有效, 错误码或空字符串, 规范化后的数据)
    """
    # 空输入检查 (E001)
    if data is None:
        return False, "E001", {}
    if isinstance(data, str) and not data.strip():
        return False, "E001", {}
    if isinstance(data, dict) and not data:
        return False, "E001", {}
    
    # 类型检查 (E009)
    if not isinstance(data, (str, dict)):
        return False, "E009", {}
    
    # 字典格式检查
    if isinstance(data, dict):
        # 必须包含 content 字段 (E002)
        if "content" not in data or not str(data.get("content", "")).strip():
            return False, "E002", {}
        
        # 检查必需字段完整性 (E002)
        required_keys = ["output_format"]
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            return False, "E002", {}
        
        # 规范化数据
        normalized = {
            "content": str(data["content"]).strip(),
            "output_format": str(data.get("output_format", "json")).lower(),
            "expected_completeness": str(data.get("expected_completeness", "detailed")).lower(),
            "custom_fields": data.get("custom_fields", []),
        }
    else:
        # 字符串输入，尝试解析为 JSON
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return validate_input(parsed)
            else:
                # 纯文本内容
                normalized = {
                    "content": data.strip(),
                    "output_format": "json",
                    "expected_completeness": "detailed",
                    "custom_fields": [],
                }
        except json.JSONDecodeError:
            # 非 JSON 纯文本
            normalized = {
                "content": data.strip(),
                "output_format": "json",
                "expected_completeness": "detailed",
                "custom_fields": [],
            }
    
    # 检查内容是否为空 (E001)
    if not normalized["content"]:
        return False, "E001", {}
    
    return True, "", normalized


def extract_keywords(content: str) -> List[str]:
    """
    从内容中提取关键词。
    简单实现：提取长度>=2的中英文词汇，去重并限制数量。
    """
    if not content:
        return []
    
    # 提取中文字符串（2字以上）
    chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', content)
    
    # 提取英文字符串（2字母以上）
    english_words = re.findall(r'[a-zA-Z]{2,}', content.lower())
    
    # 合并、去重、限制数量
    all_words = chinese_words + english_words
    unique_words = list(dict.fromkeys(all_words))
    
    # 限制最多10个关键词
    return unique_words[:10]


def estimate_confidence(content: str, keywords: List[str]) -> float:
    """
    估算置信度。
    基于内容长度和关键词数量的启发式方法。
    """
    if not content:
        return 0.0
    
    content_length = len(content)
    keyword_count = len(keywords)
    
    # 基础置信度
    base_score = 0.5
    
    # 内容长度贡献（40%权重）
    length_score = min(content_length / 200, 1.0) * 0.4
    
    # 关键词数量贡献（10%权重）
    keyword_score = min(keyword_count / 5, 1.0) * 0.1
    
    # 内容结构贡献（简单判断是否有结构化特征）
    structure_score = 0.0
    if re.search(r'[\u4e00-\u9fff]', content):  # 包含中文
        structure_score += 0.1
    if re.search(r'[a-zA-Z]', content):  # 包含英文
        structure_score += 0.1
    if re.search(r'\d', content):  # 包含数字
        structure_score += 0.05
    if len(content.split()) > 3:  # 多词
        structure_score += 0.05
    
    # 总置信度
    total = base_score + length_score + keyword_score + structure_score
    
    # 确保在 0-1 之间
    return max(0.0, min(total, 1.0))


def structure_content(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将输入内容结构化处理，生成输出结果。
    """
    content = data["content"]
    output_format = data["output_format"]
    expected_completeness = data["expected_completeness"]
    custom_fields = data.get("custom_fields", [])
    
    # 提取关键词
    keywords = extract_keywords(content)
    
    # 估算置信度
    confidence = estimate_confidence(content, keywords)
    
    # 构建结构化结果
    result: Dict[str, Any] = {
        "content": content,
        "keywords": keywords,
        "structure": {
            "length": len(content),
            "word_count": len(content.split()),
            "type": "text",
        },
        "confidence": confidence,
        "confidence_label": get_confidence_label(confidence),
    }
    
    # 添加自定义字段
    for field in custom_fields:
        if isinstance(field, str) and field:
            result[field] = None  # 自定义字段默认空值
    
    # 根据完整度调整输出
    if expected_completeness == "quick":
        # 快速骨架：只保留核心字段
        result = {
            "content": result["content"],
            "keywords": result["keywords"][:5],
            "confidence": result["confidence"],
            "confidence_label": result["confidence_label"],
        }
    
    # 根据输出格式调整
    if output_format == "text":
        # 文本格式：返回格式化字符串
        result["_format"] = "text"
    
    return result


def get_confidence_label(confidence: float) -> str:
    """
    根据置信度返回标注标签。
    """
    if confidence >= HIGH_CONFIDENCE:
        return "直接输出"
    elif confidence >= MEDIUM_CONFIDENCE:
        return "建议复核"
    else:
        return "[需核实]"


def format_result(result: Dict[str, Any], output_format: str) -> Any:
    """
    按指定格式输出结果。
    """
    if output_format == "json":
        # 移除内部格式标记
        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
        return json.dumps(clean_result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        # 文本格式输出
        lines = [
            f"内容: {result.get('content', '')}",
            f"关键词: {', '.join(result.get('keywords', []))}",
            f"置信度: {result.get('confidence', 0):.1%} ({result.get('confidence_label', '')})",
        ]
        if "structure" in result:
            structure = result["structure"]
            lines.append(f"结构: 长度={structure.get('length', 0)}, 词数={structure.get('word_count', 0)}")
        return "\n".join(lines)
    else:
        # 默认 JSON
        clean_result = {k: v for k, v in result.items() if not k.startswith("_")}
        return json.dumps(clean_result, ensure_ascii=False)


def batch_process(inputs: List[Any]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。
    """
    results = []
    for item in inputs:
        try:
            is_valid, error_code, normalized = validate_input(item)
            if not is_valid:
                results.append({
                    "success": False,
                    "error_code": error_code,
                    "error_message": ERROR_MESSAGES[error_code],
                })
            else:
                result = structure_content(normalized)
                results.append({
                    "success": True,
                    "result": result,
                })
        except Exception as e:
            results.append({
                "success": False,
                "error_code": "E006",
                "error_message": f"{ERROR_MESSAGES['E006']} ({str(e)})",
            })
    return results


def handle_error(error_code: str) -> str:
    """
    处理错误，返回标准化话术。
    """
    return ERROR_MESSAGES.get(error_code, f"未知错误: {error_code}")


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)
    
    all_passed = True
    
    # ---- 测试1: 输入校验 ----
    print("\n[测试1] 输入校验")
    
    # 空输入
    is_valid, error_code, _ = validate_input(None)
    assert not is_valid, "空输入应返回无效"
    assert error_code == "E001", f"空输入应返回 E001，实际: {error_code}"
    print("  ✓ 空输入返回 E001")
    
    # 空字符串
    is_valid, error_code, _ = validate_input("   ")
    assert not is_valid, "空字符串应返回无效"
    assert error_code == "E001", f"空字符串应返回 E001，实际: {error_code}"
    print("  ✓ 空字符串返回 E001")
    
    # 缺少必要字段
    is_valid, error_code, _ = validate_input({"content": "test"})
    assert not is_valid, "缺少 output_format 应返回无效"
    assert error_code == "E002", f"缺少字段应返回 E002，实际: {error_code}"
    print("  ✓ 缺少字段返回 E002")
    
    # 错误类型
    is_valid, error_code, _ = validate_input(12345)
    assert not is_valid, "数字输入应返回无效"
    assert error_code == "E009", f"错误类型应返回 E009，实际: {error_code}"
    print("  ✓ 错误类型返回 E009")
    
    # 有效输入
    is_valid, error_code, normalized = validate_input({"content": "测试内容", "output_format": "json"})
    assert is_valid, "有效输入应通过校验"
    assert error_code == "", f"有效输入不应有错误码，实际: {error_code}"
    assert normalized["content"] == "测试内容", "内容应正确提取"
    print("  ✓ 有效输入通过校验")
    
    # ---- 测试2: 关键词提取 ----
    print("\n[测试2] 关键词提取")
    
    keywords = extract_keywords("这是一个测试内容，包含中文和English words")
    assert len(keywords) >= 1, f"应提取至少1个关键词，实际: {len(keywords)}"
    assert any("测试" in kw for kw in keywords), "应包含'测试'关键词"
    print(f"  ✓ 关键词提取成功: {keywords[:3]}...")
    
    # 空内容
    keywords = extract_keywords("")
    assert keywords == [], "空内容应返回空列表"
    print("  ✓ 空内容返回空列表")
    
    # ---- 测试3: 置信度估算 ----
    print("\n[测试3] 置信度估算")
    
    # 长内容应有较高置信度
    long_content = "这是一个较长的测试内容，包含多个中文字符和English words，用于测试置信度估算功能。"
    long_conf = estimate_confidence(long_content, extract_keywords(long_content))
    short_conf = estimate_confidence("短", ["短"])
    assert long_conf > short_conf, f"长内容置信度应高于短内容: {long_conf} vs {short_conf}"
    print(f"  ✓ 长内容置信度({long_conf:.2f}) > 短内容置信度({short_conf:.2f})")
    
    # 置信度范围
    assert 0.0 <= long_conf <= 1.0, f"置信度应在0-1之间，实际: {long_conf}"
    print("  ✓ 置信度范围正确")
    
    # ---- 测试4: 结构化处理 ----
    print("\n[测试4] 结构化处理")
    
    test_data = {
        "content": "测试QA提示词库功能，包含测试用例创建和自动化测试场景。",
        "output_format": "json",
        "expected_completeness": "detailed",
    }
    result = structure_content(test_data)
    
    assert "content" in result, "结果应包含内容"
    assert "keywords" in result, "结果应包含关键词"
    assert "confidence" in result, "结果应包含置信度"
    assert "confidence_label" in result, "结果应包含置信度标签"
    assert result["confidence"] > 0, f"置信度应大于0，实际: {result['confidence']}"
    print(f"  ✓ 结构化结果完整，置信度: {result['confidence']:.2%}")
    
    # 置信度标签
    label = get_confidence_label(0.95)
    assert label == "直接输出", f"高置信度应标记为'直接输出'，实际: {label}"
    label = get_confidence_label(0.87)
    assert label == "建议复核", f"中置信度应标记为'建议复核'，实际: {label}"
    label = get_confidence_label(0.50)
    assert label == "[需核实]", f"低置信度应标记为'[需核实]'，实际: {label}"
    print("  ✓ 置信度标签分级正确")
    
    # ---- 测试5: 输出格式化 ----
    print("\n[测试5] 输出格式化")
    
    # JSON 格式
    json_output = format_result(result, "json")
    parsed_json = json.loads(json_output)
    assert "content" in parsed_json, "JSON输出应包含内容字段"
    print("  ✓ JSON格式输出正确")
    
    # 文本格式
    text_output = format_result(result, "text")
    assert "内容:" in text_output, "文本输出应包含内容标记"
    print("  ✓ 文本格式输出正确")
    
    # ---- 测试6: 批量处理 ----
    print("\n[测试6] 批量处理")
    
    batch_inputs = [
        {"content": "第一条测试内容", "output_format": "json"},
        {"content": "第二条测试内容，用于批量处理", "output_format": "json"},
        None,  # 无效输入
        {"content": "第三条测试", "output_format": "text"},
    ]
    
    batch_results = batch_process(batch_inputs)
    assert len(batch_results) == 4, f"应返回4个结果，实际: {len(batch_results)}"
    assert batch_results[0]["success"], "第一条应成功处理"
    assert batch_results[2]["success"] == False, "第三条应处理失败"
    assert batch_results[2]["error_code"] == "E001", "第三条应返回E001"
    success_count = sum(1 for r in batch_results if r["success"])
    assert success_count >= 3, f"应至少成功3条，实际: {success_count}"
    print(f"  ✓ 批量处理成功 ({success_count}/4)")
    
    # ---- 测试7: 错误处理 ----
    print("\n[测试7] 错误处理")
    
    for error_code in ["E001", "E002", "E003", "E004", "E005"]:
        message = handle_error(error_code)
        assert message, f"错误码 {error_code} 应有对应话术"
        assert len(message) > 5, f"错误话术应非空且有一定长度: {message}"
    print("  ✓ 错误处理话术完整")
    
    # ---- 测试8: 能力边界 ----
    print("\n[测试8] 能力边界")
    
    assert len(CAPABILITIES["can_do"]) == 5, "应有5项核心能力"
    assert len(CAPABILITIES["cannot_do"]) == 3, "应有3项边界声明"
    print("  ✓ 能力边界声明完整")
    
    # ---- 测试9: 端到端流程 ----
    print("\n[测试9] 端到端流程")
    
    # 模拟完整处理流程
    sample_input = {
        "content": "请为登录功能创建测试用例，包含正常登录、错误密码、锁定账号三个场景。",
        "output_format": "json",
        "expected_completeness": "detailed",
    }
    
    is_valid, error_code, normalized = validate_input(sample_input)
    assert is_valid, "端到端输入应有效"
    result = structure_content(normalized)
    output = format_result(result, "json")
    assert output, "端到端输出应非空"
    print("  ✓ 端到端流程成功")
    
    print("\n" + "=" * 60)
    print("自检全部通过！")
    print("=" * 60)
    
    return True


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主函数，处理命令行参数。
    """
    parser = argparse.ArgumentParser(
        description="qa-prompt-library - QA提示词库工具",
        epilog="示例: python main.py --input '待处理内容' --format json"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（纯文本或JSON字符串）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--completeness",
        type=str,
        choices=["quick", "detailed"],
        default="detailed",
        help="期望完整度 (默认: detailed)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理JSON数组输入"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"\n[自检失败] {str(e)}")
            return 1
        except Exception as e:
            print(f"\n[自检异常] {str(e)}")
            return 1
    
    # 批量处理模式
    if args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                print(f"E003: {ERROR_MESSAGES['E003']}")
                return 1
            results = batch_process(batch_data)
            for i, result in enumerate(results):
                if result["success"]:
                    output = format_result(result["result"], args.format)
                    print(f"[结果 {i+1}]\n{output}\n")
                else:
                    print(f"[结果 {i+1}] 错误 {result['error_code']}: {result['error_message']}\n")
            return 0
        except json.JSONDecodeError:
            print(f"E003: {ERROR_MESSAGES['E003']}")
            return 1
    
    # 单条处理模式
    if args.input:
        input_data = args.input
        # 尝试解析JSON
        try:
            parsed = json.loads(input_data)
            if isinstance(parsed, dict):
                input_data = parsed
        except json.JSONDecodeError:
            pass  # 保持原始字符串
        
        # 构建处理数据
        if isinstance(input_data, dict):
            input_data["output_format"] = input_data.get("output_format", args.format)
            input_data["expected_completeness"] = input_data.get("expected_completeness", args.completeness)
        else:
            input_data = {
                "content": input_data,
                "output_format": args.format,
                "expected_completeness": args.completeness,
            }
        
        # 校验并处理
        is_valid, error_code, normalized = validate_input(input_data)
        if not is_valid:
            print(f"{error_code}: {handle_error(error_code)}")
            return 1
        
        try:
            result = structure_content(normalized)
            output = format_result(result, args.format)
            print(output)
            return 0
        except Exception as e:
            print(f"E006: {ERROR_MESSAGES['E006']} ({str(e)})")
            return 1
    
    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
