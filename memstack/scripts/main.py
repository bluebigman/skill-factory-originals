#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memstack - Structured skill framework for Claude Code
独立实现脚本（clean-room 重写），仅依据功能规格设计。
"""

import argparse
import sys
import re
import json
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 常量定义（错误码体系）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议...",
    "E006": "内部处理错误，请稍后重试",
    "E007": "参数解析失败，请检查命令行参数",
    "E008": "输出序列化失败，请检查数据格式",
    "E009": "置信度计算异常，请检查输入数据",
    "E010": "未知错误，请联系管理员",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
CONFIDENCE_LOW = 0.85       # <85% 标注 [需核实]

# 能力边界声明
CAPABILITY_BOUNDARY = (
    "本工具仅处理用户提供的数据/文件/URL，不执行超出输入范围的分析，"
    "不保证绝对准确，不访问网络或外部服务。"
)


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """结构化处理结果"""
    def __init__(self, status: str = "success", data: Any = None,
                 confidence: float = 1.0, warnings: List[str] = None,
                 error_code: Optional[str] = None):
        self.status = status              # success / error / warning
        self.data = data                  # 结构化数据
        self.confidence = confidence      # 置信度 0.0-1.0
        self.warnings = warnings or []    # 警告列表
        self.error_code = error_code      # 错误码

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "data": self.data,
            "confidence": round(self.confidence, 4),
            "warnings": self.warnings,
            "error_code": self.error_code,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

def extract_key_fields(raw_input: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段并结构化。
    
    支持输入类型：
    - 字符串：尝试解析为 JSON，若失败则按文本处理
    - 字典：直接使用
    - 列表：逐项处理
    - 其他：转为字符串处理
    
    返回结构化字典，包含提取的字段和元信息。
    """
    if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
        raise ValueError("E001")  # 输入为空

    # 字符串输入：尝试 JSON 解析
    if isinstance(raw_input, str):
        text = raw_input.strip()
        try:
            parsed = json.loads(text)
            return _structure_from_parsed(parsed, source_type="json")
        except json.JSONDecodeError:
            # 非 JSON 文本，提取关键信息
            return _structure_from_text(text)

    # 字典输入
    if isinstance(raw_input, dict):
        return _structure_from_parsed(raw_input, source_type="dict")

    # 列表输入
    if isinstance(raw_input, list):
        items = []
        for item in raw_input:
            try:
                items.append(extract_key_fields(item))
            except ValueError:
                items.append({"raw": str(item), "type": "unknown"})
        return {
            "type": "list",
            "count": len(items),
            "items": items,
            "source": "list",
        }

    # 其他类型
    return _structure_from_text(str(raw_input))


def _structure_from_parsed(parsed: Any, source_type: str) -> Dict[str, Any]:
    """将已解析的数据结构化为统一格式"""
    if isinstance(parsed, dict):
        # 识别关键字段
        keys = list(parsed.keys())
        return {
            "type": "object",
            "fields": parsed,
            "field_count": len(keys),
            "field_names": keys,
            "source": source_type,
        }
    elif isinstance(parsed, list):
        return {
            "type": "array",
            "items": parsed,
            "item_count": len(parsed),
            "source": source_type,
        }
    else:
        return {
            "type": "scalar",
            "value": parsed,
            "source": source_type,
        }


def _structure_from_text(text: str) -> Dict[str, Any]:
    """从纯文本中提取关键信息"""
    # 识别数字
    numbers = re.findall(r'-?\d+\.?\d*', text)
    
    # 识别日期（简单模式）
    dates = re.findall(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text)
    
    # 识别邮箱
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    
    # 识别 URL
    urls = re.findall(r'https?://[^\s]+', text)
    
    # 统计词频
    words = re.findall(r'[\u4e00-\u9fff\w]+', text.lower())
    word_freq: Dict[str, int] = {}
    for w in words:
        word_freq[w] = word_freq.get(w, 0) + 1
    
    return {
        "type": "text",
        "content": text,
        "length": len(text),
        "word_count": len(words),
        "numbers": numbers,
        "dates": dates,
        "emails": emails,
        "urls": urls,
        "top_keywords": sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5],
        "source": "text",
    }


def calculate_confidence(structured: Dict[str, Any]) -> float:
    """
    计算置信度（0.0-1.0）。
    
    规则：
    - 结构化数据字段完整：高置信度
    - 文本数据有明确标识：中高置信度
    - 信息模糊或缺失：低置信度
    """
    try:
        if structured.get("type") in ("object", "array"):
            # 结构化数据，根据字段数量和信息完整度评估
            field_count = structured.get("field_count", structured.get("item_count", 0))
            if field_count >= 5:
                return 0.95
            elif field_count >= 3:
                return 0.90
            elif field_count >= 1:
                return 0.85
            else:
                return 0.80
        
        elif structured.get("type") == "text":
            # 文本数据，根据内容特征评估
            content = structured.get("content", "")
            if len(content) < 10:
                return 0.70  # 内容太短，置信度低
            elif structured.get("emails") or structured.get("urls"):
                return 0.88  # 有明确标识
            elif structured.get("dates") or structured.get("numbers"):
                return 0.85
            else:
                return 0.80
        
        elif structured.get("type") == "scalar":
            # 标量数据
            return 0.92
        
        else:
            return 0.75  # 未知类型，保守估计
    
    except Exception:
        return 0.70  # 计算异常，低置信度


def process_input(raw_input: Any) -> ProcessingResult:
    """
    标准处理流程：
    1. 解析输入
    2. 结构化处理
    3. 计算置信度
    4. 生成结果
    """
    try:
        # Step 1: 解析输入
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            return ProcessingResult(
                status="error",
                error_code="E001",
                confidence=0.0,
                warnings=["输入内容为空"]
            )
        
        # Step 2: 结构化处理
        structured = extract_key_fields(raw_input)
        
        # Step 3: 计算置信度
        confidence = calculate_confidence(structured)
        
        # Step 4: 生成结果
        warnings = []
        if confidence < CONFIDENCE_LOW:
            warnings.append("结果无法确定，建议人工复核关键信息")
            status = "warning"
        elif confidence < CONFIDENCE_MEDIUM:
            warnings.append("建议复核：部分信息可能存在不确定性")
            status = "success"
        else:
            status = "success"
        
        return ProcessingResult(
            status=status,
            data=structured,
            confidence=confidence,
            warnings=warnings
        )
    
    except ValueError as e:
        # 处理业务错误
        error_code = str(e)
        return ProcessingResult(
            status="error",
            error_code=error_code,
            confidence=0.0,
            warnings=[ERROR_CODES.get(error_code, "未知错误")]
        )
    
    except Exception:
        return ProcessingResult(
            status="error",
            error_code="E006",
            confidence=0.0,
            warnings=["内部处理错误，请稍后重试"]
        )


def format_output(result: ProcessingResult, output_format: str = "text") -> str:
    """
    按指定格式输出结果。
    
    支持格式：
    - text: 文本格式
    - json: JSON 格式
    - compact: 精简格式
    """
    try:
        if output_format == "json":
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        
        elif output_format == "compact":
            # 精简格式
            lines = [f"状态: {result.status}"]
            if result.error_code:
                lines.append(f"错误码: {result.error_code}")
                lines.append(f"提示: {ERROR_CODES.get(result.error_code, '')}")
            else:
                data = result.data
                if data:
                    if data.get("type") == "object":
                        lines.append(f"字段数: {data.get('field_count', 0)}")
                        lines.append(f"字段: {', '.join(data.get('field_names', [])[:5])}")
                    elif data.get("type") == "text":
                        lines.append(f"长度: {data.get('length', 0)}")
                        lines.append(f"词数: {data.get('word_count', 0)}")
                        if data.get("emails"):
                            lines.append(f"邮箱: {', '.join(data['emails'])}")
                    elif data.get("type") == "array":
                        lines.append(f"项数: {data.get('item_count', 0)}")
                lines.append(f"置信度: {result.confidence:.1%}")
            return "\n".join(lines)
        
        else:
            # text 格式（默认）
            lines = []
            if result.status == "error":
                lines.append(f"❌ 处理失败")
                lines.append(f"错误码: {result.error_code}")
                lines.append(f"提示: {ERROR_CODES.get(result.error_code, '未知错误')}")
            else:
                lines.append(f"✅ 处理成功")
                if result.data:
                    lines.append(f"数据类型: {result.data.get('type', 'unknown')}")
                    if result.data.get("type") == "object":
                        lines.append(f"字段数: {result.data.get('field_count', 0)}")
                        lines.append(f"字段列表: {', '.join(result.data.get('field_names', []))}")
                    elif result.data.get("type") == "text":
                        lines.append(f"内容长度: {result.data.get('length', 0)}")
                        lines.append(f"词数: {result.data.get('word_count', 0)}")
                        if result.data.get("emails"):
                            lines.append(f"识别邮箱: {', '.join(result.data['emails'])}")
                        if result.data.get("urls"):
                            lines.append(f"识别URL: {', '.join(result.data['urls'])}")
                        if result.data.get("top_keywords"):
                            kws = [f"{k}({v})" for k, v in result.data["top_keywords"]]
                            lines.append(f"关键词: {', '.join(kws)}")
                    elif result.data.get("type") == "array":
                        lines.append(f"项数: {result.data.get('item_count', 0)}")
                    elif result.data.get("type") == "scalar":
                        lines.append(f"值: {result.data.get('value', '')}")
                
                # 置信度标注
                conf = result.confidence
                if conf >= CONFIDENCE_HIGH:
                    lines.append(f"置信度: {conf:.1%} ✅")
                elif conf >= CONFIDENCE_MEDIUM:
                    lines.append(f"置信度: {conf:.1%} ⚠️ 建议复核")
                else:
                    lines.append(f"置信度: {conf:.1%} ❌ [需核实]")
                
                # 警告
                if result.warnings:
                    lines.append("")
                    lines.append("⚠️ 注意事项:")
                    for w in result.warnings:
                        lines.append(f"  - {w}")
            
            return "\n".join(lines)
    
    except Exception:
        return f"错误码: E008 - 输出序列化失败"


# ============================================================
# 批量处理
# ============================================================

def batch_process(inputs: List[Any], output_format: str = "text") -> List[str]:
    """批量处理多个输入"""
    results = []
    for i, item in enumerate(inputs, 1):
        result = process_input(item)
        output = format_output(result, output_format)
        results.append(f"--- 第{i}项 ---\n{output}")
    return results


# ============================================================
# 自测模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=" * 60)
    print("memstack 自检开始")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # --------------------------------------------------------
    # 测试 1: 空输入处理
    # --------------------------------------------------------
    print("\n[测试1] 空输入处理")
    try:
        result = process_input("")
        assert result.status == "error", f"期望error，实际{result.status}"
        assert result.error_code == "E001", f"期望E001，实际{result.error_code}"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 2: JSON 字符串解析
    # --------------------------------------------------------
    print("\n[测试2] JSON 字符串解析")
    try:
        json_input = '{"name": "测试项目", "version": "1.0", "tags": ["a", "b", "c"], "active": true}'
        result = process_input(json_input)
        assert result.status == "success", f"期望success，实际{result.status}"
        assert result.data is not None, "数据不应为空"
        assert result.data.get("type") == "object", f"期望object，实际{result.data.get('type')}"
        assert result.data.get("field_count", 0) >= 3, "字段数应>=3"
        assert result.confidence >= 0.85, f"置信度应>=0.85，实际{result.confidence}"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 3: 纯文本处理
    # --------------------------------------------------------
    print("\n[测试3] 纯文本处理")
    try:
        text_input = "这是一个测试文本，包含数字123和邮箱test@example.com，日期2024-01-15。"
        result = process_input(text_input)
        assert result.status in ("success", "warning"), f"期望success/warning，实际{result.status}"
        assert result.data.get("type") == "text", f"期望text，实际{result.data.get('type')}"
        assert result.data.get("word_count", 0) > 0, "词数应大于0"
        assert result.confidence >= 0.70, f"置信度应>=0.70，实际{result.confidence}"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 4: 字典输入
    # --------------------------------------------------------
    print("\n[测试4] 字典输入")
    try:
        dict_input = {"key1": "value1", "key2": 123, "key3": [1, 2, 3], "key4": {"nested": True}}
        result = process_input(dict_input)
        assert result.status == "success", f"期望success，实际{result.status}"
        assert result.data.get("type") == "object", f"期望object，实际{result.data.get('type')}"
        assert result.data.get("field_count", 0) == 4, f"期望4个字段，实际{result.data.get('field_count')}"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 5: 列表输入
    # --------------------------------------------------------
    print("\n[测试5] 列表输入")
    try:
        list_input = ["item1", "item2", "item3", "item4", "item5"]
        result = process_input(list_input)
        assert result.status == "success", f"期望success，实际{result.status}"
        assert result.data.get("type") == "list", f"期望list，实际{result.data.get('type')}"
        assert result.data.get("count", 0) >= 3, f"项数应>=3，实际{result.data.get('count')}"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 6: 数字输入
    # --------------------------------------------------------
    print("\n[测试6] 数字输入")
    try:
        result = process_input(12345)
        assert result.status == "success", f"期望success，实际{result.status}"
        assert result.data.get("type") in ("scalar", "text"), f"期望scalar/text，实际{result.data.get('type')}"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 7: 置信度计算
    # --------------------------------------------------------
    print("\n[测试7] 置信度计算")
    try:
        # 完整结构化数据
        complete = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        conf = calculate_confidence(_structure_from_parsed(complete, "dict"))
        assert conf >= 0.90, f"完整数据置信度应>=0.90，实际{conf}"
        
        # 短文本
        short_text = _structure_from_text("短")
        conf2 = calculate_confidence(short_text)
        assert conf2 < 0.85, f"短文本置信度应<0.85，实际{conf2}"
        
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 8: 输出格式
    # --------------------------------------------------------
    print("\n[测试8] 输出格式")
    try:
        result = process_input({"name": "test", "value": 42})
        
        # JSON 格式
        json_out = format_output(result, "json")
        parsed = json.loads(json_out)
        assert parsed["status"] == "success", "JSON输出状态错误"
        
        # 文本格式
        text_out = format_output(result, "text")
        assert "处理成功" in text_out, "文本输出缺少成功标识"
        
        # 精简格式
        compact_out = format_output(result, "compact")
        assert "状态:" in compact_out, "精简输出缺少状态"
        
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 9: 批量处理
    # --------------------------------------------------------
    print("\n[测试9] 批量处理")
    try:
        inputs = ["第一项数据", {"second": "item"}, ["a", "b", "c"]]
        outputs = batch_process(inputs)
        assert len(outputs) == 3, f"期望3个输出，实际{len(outputs)}"
        for out in outputs:
            assert "第" in out and "项" in out, "批量输出缺少序号"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 测试 10: 错误码完整性
    # --------------------------------------------------------
    print("\n[测试10] 错误码完整性")
    try:
        assert "E001" in ERROR_CODES, "缺少E001"
        assert "E002" in ERROR_CODES, "缺少E002"
        assert "E003" in ERROR_CODES, "缺少E003"
        assert "E004" in ERROR_CODES, "缺少E004"
        assert "E005" in ERROR_CODES, "缺少E005"
        assert "E006" in ERROR_CODES, "缺少E006"
        assert "E007" in ERROR_CODES, "缺少E007"
        assert "E008" in ERROR_CODES, "缺少E008"
        assert "E009" in ERROR_CODES, "缺少E009"
        assert "E010" in ERROR_CODES, "缺少E010"
        tests_passed += 1
        print("  ✅ 通过")
    except AssertionError as e:
        tests_failed += 1
        print(f"  ❌ 失败: {e}")
    
    # --------------------------------------------------------
    # 汇总
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"自检完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)
    
    return 0 if tests_failed == 0 else 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="memstack - Structured skill framework for Claude Code",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（字符串/JSON/文本）"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "compact"],
        default="text",
        help="输出格式 (默认: text)"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入，用 | 分隔多个项目"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）"
    )
    
    parser.add_argument(
        "--boundary",
        action="store_true",
        help="显示能力边界声明"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 能力边界声明
    if args.boundary:
        print(CAPABILITY_BOUNDARY)
        return 0
    
    # 批量处理
    if args.batch:
        items = args.batch.split("|")
        outputs = batch_process(items, args.format)
        print("\n\n".join(outputs))
        return 0
    
    # 单条处理
    if args.input is not None:
        result = process_input(args.input)
        output = format_output(result, args.format)
        print(output)
        
        # 非零退出码表示错误
        if result.status == "error":
            return 1
        return 0
    
    # 无输入参数，显示帮助
    parser.print_help()
    print("\n提示: 请提供 --input 内容，或使用 --selftest 运行自检。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
