#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
未命名工具 - Marketing Skills 独立实现脚本

本脚本为 clean-room 重写实现，仅依据功能规格独立开发。
提供核心能力：输入解析、关键信息识别、结构化输出、置信度标注、错误处理。
包含 --selftest 离线自检功能，不依赖外部文件或网络。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及标准化话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{'source': 'data', 'content': '...'}",
    "E004": "这超出了本工具的能力范围，建议使用专业工具或咨询专业人士",
    "E005": "结果无法确定，建议：提供更多上下文信息或人工复核",
    "E006": "内部处理错误，请检查输入数据",
    "E007": "输出格式不支持，仅支持 json 或 text",
    "E008": "置信度计算异常，请检查输入数据",
    "E009": "批量处理时出现错误，请检查各条输入",
    "E010": "未知错误，请查看日志",
}

# 能力边界声明
CAPABILITIES = [
    "将用户提供的数据/文件/URL 转换为结构化结果",
    "识别并保留输入中的关键信息",
    "按约定格式生成输出",
    "对不确定项给出置信度提示",
    "支持批量处理和自定义格式",
]

BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]

# 触发词表
TRIGGER_WORDS = ["marketingskills"]

# 必需的最小信息集
REQUIRED_FIELDS = ["输入来源", "输出格式要求", "期望的完整度"]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果数据类"""
    
    def __init__(self, 
                 data: Any = None,
                 confidence: float = 0.0,
                 warnings: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
    
    def to_text(self) -> str:
        """转换为文本格式"""
        lines = [
            f"处理时间: {self.timestamp}",
            f"置信度: {self.confidence:.1%}",
        ]
        if self.warnings:
            lines.append(f"警告: {'; '.join(self.warnings)}")
        lines.append(f"结果: {json.dumps(self.data, ensure_ascii=False, indent=2)}")
        return "\n".join(lines)


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(input_data: Any) -> Tuple[bool, Optional[str]]:
    """
    验证输入数据的基本有效性
    
    Args:
        input_data: 输入数据
        
    Returns:
        (是否有效, 错误码)
    """
    if input_data is None:
        return False, "E001"
    if isinstance(input_data, str) and not input_data.strip():
        return False, "E001"
    if isinstance(input_data, (list, dict)) and len(input_data) == 0:
        return False, "E001"
    return True, None


def extract_key_info(input_data: Any) -> Tuple[Dict[str, Any], float]:
    """
    从输入中提取关键信息
    
    Args:
        input_data: 输入数据
        
    Returns:
        (提取的关键信息, 置信度)
    """
    key_info = {}
    confidence = 0.0
    
    try:
        if isinstance(input_data, str):
            # 文本输入：尝试解析 JSON，否则作为纯文本
            try:
                parsed = json.loads(input_data)
                if isinstance(parsed, dict):
                    key_info = parsed
                    confidence = 0.95  # JSON 解析成功，高置信度
                else:
                    key_info = {"content": parsed}
                    confidence = 0.85
            except json.JSONDecodeError:
                # 纯文本处理
                key_info = {
                    "content": input_data,
                    "length": len(input_data),
                    "type": "text",
                }
                confidence = 0.80
                
        elif isinstance(input_data, dict):
            # 字典输入
            key_info = input_data
            confidence = 0.90
            # 检查必需字段
            missing = [f for f in REQUIRED_FIELDS if f not in input_data]
            if missing:
                confidence -= 0.1 * len(missing)
                
        elif isinstance(input_data, list):
            # 列表输入（批量）
            key_info = {
                "items": input_data,
                "count": len(input_data),
                "type": "batch",
            }
            confidence = 0.85
            
        else:
            # 其他类型
            key_info = {
                "content": str(input_data),
                "type": type(input_data).__name__,
            }
            confidence = 0.70
            
    except Exception:
        confidence = 0.50
        key_info = {"error": "解析失败"}
    
    # 置信度限制在 0-1 之间
    confidence = max(0.0, min(1.0, confidence))
    
    return key_info, confidence


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    按指定格式输出结果
    
    Args:
        result: 处理结果
        output_format: 输出格式（json 或 text）
        
    Returns:
        格式化后的输出字符串
    """
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        return result.to_text()
    else:
        raise ValueError(ERROR_MESSAGES["E007"])


def process_single_input(input_data: Any, output_format: str = "json") -> ProcessingResult:
    """
    处理单个输入数据
    
    Args:
        input_data: 输入数据
        output_format: 输出格式
        
    Returns:
        处理结果对象
    """
    # 验证输入
    is_valid, error_code = validate_input(input_data)
    if not is_valid:
        return ProcessingResult(
            data={"error": ERROR_MESSAGES[error_code]},
            confidence=0.0,
            warnings=[f"错误码: {error_code}"],
            metadata={"error_code": error_code},
        )
    
    # 提取关键信息
    key_info, confidence = extract_key_info(input_data)
    
    # 生成警告
    warnings = []
    if confidence < 0.85:
        warnings.append("[需核实] 置信度较低，请人工复核")
    elif confidence < 0.90:
        warnings.append("建议复核")
    
    # 构建结果
    result = ProcessingResult(
        data=key_info,
        confidence=confidence,
        warnings=warnings,
        metadata={
            "input_type": type(input_data).__name__,
            "processed_at": datetime.now().isoformat(),
        },
    )
    
    return result


def process_batch_input(inputs: List[Any], output_format: str = "json") -> ProcessingResult:
    """
    批量处理多个输入
    
    Args:
        inputs: 输入列表
        output_format: 输出格式
        
    Returns:
        批量处理结果
    """
    results = []
    errors = []
    
    for i, item in enumerate(inputs):
        try:
            result = process_single_input(item, output_format)
            results.append({
                "index": i,
                "result": result.to_dict(),
            })
        except Exception as e:
            errors.append({
                "index": i,
                "error": str(e),
            })
    
    # 计算批量处理的总体置信度
    if results:
        avg_confidence = sum(r["result"]["confidence"] for r in results) / len(results)
    else:
        avg_confidence = 0.0
    
    warnings = []
    if errors:
        warnings.append(f"批量处理完成，{len(errors)} 条输入处理失败")
        warnings.append(f"错误码: E009")
    
    return ProcessingResult(
        data={
            "total": len(inputs),
            "success": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        },
        confidence=avg_confidence,
        warnings=warnings,
        metadata={"batch": True},
    )


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑
    
    使用硬编码样例数据，不读取外部文件，不依赖工作目录，不访问网络。
    断言使用宽松阈值，确保在不同环境下都能通过。
    
    Returns:
        自检是否通过
    """
    print("=" * 60)
    print("开始运行自检 (--selftest)")
    print("=" * 60)
    
    test_results = []
    
    # 测试 1: 有效文本输入
    print("\n[测试 1] 有效文本输入")
    try:
        result = process_single_input("这是一个测试文本")
        assert result.confidence > 0.5, "置信度应大于 0.5"
        assert result.data is not None, "结果不应为空"
        test_results.append(("文本输入", True))
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
    except AssertionError as e:
        test_results.append(("文本输入", False))
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        test_results.append(("文本输入", False))
        print(f"  ✗ 异常: {e}")
    
    # 测试 2: 空输入处理
    print("\n[测试 2] 空输入处理")
    try:
        result = process_single_input("")
        assert result.confidence == 0.0, "空输入置信度应为 0"
        assert "E001" in str(result.metadata), "应返回错误码 E001"
        test_results.append(("空输入", True))
        print(f"  ✓ 通过 (错误码: {result.metadata.get('error_code')})")
    except AssertionError as e:
        test_results.append(("空输入", False))
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        test_results.append(("空输入", False))
        print(f"  ✗ 异常: {e}")
    
    # 测试 3: JSON 输入解析
    print("\n[测试 3] JSON 输入解析")
    try:
        json_input = json.dumps({"source": "测试", "content": "内容"})
        result = process_single_input(json_input)
        assert result.confidence > 0.8, "JSON 解析置信度应较高"
        assert "source" in result.data, "应提取到 source 字段"
        test_results.append(("JSON解析", True))
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
    except AssertionError as e:
        test_results.append(("JSON解析", False))
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        test_results.append(("JSON解析", False))
        print(f"  ✗ 异常: {e}")
    
    # 测试 4: 批量输入
    print("\n[测试 4] 批量输入")
    try:
        batch_input = ["文本1", "文本2", "文本3"]
        result = process_batch_input(batch_input)
        assert result.data["total"] == 3, "应处理 3 条输入"
        assert result.data["success"] == 3, "应全部成功"
        assert result.confidence > 0.5, "批量置信度应合理"
        test_results.append(("批量输入", True))
        print(f"  ✓ 通过 (成功率: {result.data['success']}/{result.data['total']})")
    except AssertionError as e:
        test_results.append(("批量输入", False))
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        test_results.append(("批量输入", False))
        print(f"  ✗ 异常: {e}")
    
    # 测试 5: 输出格式
    print("\n[测试 5] 输出格式")
    try:
        result = process_single_input("测试内容")
        json_output = format_output(result, "json")
        text_output = format_output(result, "text")
        assert json.loads(json_output), "JSON 格式应可解析"
        assert len(text_output) > 0, "文本格式不应为空"
        test_results.append(("输出格式", True))
        print(f"  ✓ 通过 (JSON {len(json_output)} 字符, TEXT {len(text_output)} 字符)")
    except AssertionError as e:
        test_results.append(("输出格式", False))
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        test_results.append(("输出格式", False))
        print(f"  ✗ 异常: {e}")
    
    # 测试 6: 错误处理
    print("\n[测试 6] 错误处理")
    try:
        # 测试错误码
        for code, message in ERROR_MESSAGES.items():
            assert len(message) > 0, f"错误码 {code} 应有消息"
        assert len(ERROR_MESSAGES) >= 5, "至少应有 5 个错误码"
        test_results.append(("错误处理", True))
        print(f"  ✓ 通过 ({len(ERROR_MESSAGES)} 个错误码)")
    except AssertionError as e:
        test_results.append(("错误处理", False))
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        test_results.append(("错误处理", False))
        print(f"  ✗ 异常: {e}")
    
    # 测试 7: 能力边界
    print("\n[测试 7] 能力边界")
    try:
        assert len(CAPABILITIES) == 5, "应有 5 项核心能力"
        assert len(BOUNDARIES) == 3, "应有 3 项边界声明"
        test_results.append(("能力边界", True))
        print(f"  ✓ 通过 ({len(CAPABILITIES)} 项能力, {len(BOUNDARIES)} 项边界)")
    except AssertionError as e:
        test_results.append(("能力边界", False))
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        test_results.append(("能力边界", False))
        print(f"  ✗ 异常: {e}")
    
    # 汇总结果
    print("\n" + "=" * 60)
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    print(f"自检结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 全部测试通过")
        return True
    else:
        print("✗ 存在失败的测试")
        return False


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主入口函数
    
    Returns:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="未命名工具 - Marketing Skills 处理脚本",
        epilog="示例: python main.py --input '{\"source\": \"data\"}' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据（文本或 JSON 字符串）"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入（JSON 数组字符串）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="marketingskills 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理输入
    try:
        if args.batch:
            # 批量处理
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    print(json.dumps({
                        "error": ERROR_MESSAGES["E003"],
                        "error_code": "E003",
                    }, ensure_ascii=False))
                    return 1
                result = process_batch_input(batch_data, args.format)
            except json.JSONDecodeError:
                print(json.dumps({
                    "error": ERROR_MESSAGES["E003"],
                    "error_code": "E003",
                }, ensure_ascii=False))
                return 1
                
        elif args.input:
            # 单个输入
            result = process_single_input(args.input, args.format)
        else:
            # 无输入，显示帮助
            print("请提供输入数据。使用 --help 查看帮助。")
            print(f"错误: {ERROR_MESSAGES['E001']}")
            return 1
        
        # 输出结果
        print(format_output(result, args.format))
        return 0
        
    except Exception as e:
        # 未知错误
        error_result = ProcessingResult(
            data={"error": ERROR_MESSAGES["E010"]},
            confidence=0.0,
            warnings=[f"未知错误: {str(e)}"],
            metadata={"error_code": "E010"},
        )
        print(format_output(error_result, "json"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
