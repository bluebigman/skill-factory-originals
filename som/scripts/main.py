#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - SQL查询技能实现

基于功能规格的独立实现（clean-room）。
提供核心处理流程、错误码体系、命令行接口与离线自检。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码体系（E001-E010）
ERROR_CODES: Dict[str, str] = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "输出格式不支持",
    "E009": "批量处理中断",
    "E010": "未知错误",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 触发词
TRIGGER_WORDS = ["SQL查询", "som"]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果对象"""
    def __init__(self, data: Any, confidence: float, warnings: List[str] = None):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(input_data: Any) -> Tuple[bool, str]:
    """
    校验输入数据的有效性。
    
    Args:
        input_data: 用户输入
        
    Returns:
        (是否有效, 错误码或空字符串)
    """
    if input_data is None:
        return False, "E001"
    if isinstance(input_data, str) and not input_data.strip():
        return False, "E001"
    if isinstance(input_data, (list, dict)) and len(input_data) == 0:
        return False, "E001"
    return True, ""


def extract_key_info(input_data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键信息（核心处理步骤）。
    
    Args:
        input_data: 原始输入
        
    Returns:
        结构化提取结果
    """
    result = {
        "type": type(input_data).__name__,
        "content": input_data,
        "fields_found": 0,
    }
    
    # 字符串输入：尝试解析
    if isinstance(input_data, str):
        lines = [line.strip() for line in input_data.split("\n") if line.strip()]
        result["lines"] = lines
        result["fields_found"] = len(lines)
    
    # 字典输入：直接提取键
    elif isinstance(input_data, dict):
        result["keys"] = list(input_data.keys())
        result["fields_found"] = len(input_data)
    
    # 列表输入：统计元素
    elif isinstance(input_data, list):
        result["items"] = len(input_data)
        result["fields_found"] = len(input_data)
    
    return result


def calculate_confidence(info: Dict[str, Any]) -> float:
    """
    根据提取结果计算置信度。
    
    Args:
        info: 提取的关键信息
        
    Returns:
        置信度值 (0.0 - 1.0)
    """
    fields = info.get("fields_found", 0)
    
    # 有字段则置信度较高
    if fields > 0:
        base = 0.85
        # 字段越多置信度越高，但不超过 0.98
        return min(0.98, base + fields * 0.01)
    
    # 无字段则置信度低
    return 0.50


def process_input(input_data: Any) -> ProcessingResult:
    """
    核心处理流程：解析 -> 提取 -> 置信度评估。
    
    Args:
        input_data: 用户输入
        
    Returns:
        处理结果对象
    """
    # Step 1: 校验输入
    valid, error_code = validate_input(input_data)
    if not valid:
        raise ValueError(error_code)
    
    # Step 2: 提取关键信息
    info = extract_key_info(input_data)
    
    # Step 3: 计算置信度
    confidence = calculate_confidence(info)
    
    # Step 4: 生成警告
    warnings = []
    if confidence < CONFIDENCE_MEDIUM:
        warnings.append("[需核实] 置信度较低，请人工复核")
    elif confidence < CONFIDENCE_HIGH:
        warnings.append("建议复核")
    
    return ProcessingResult(info, confidence, warnings)


def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """
    按指定格式输出结果。
    
    Args:
        result: 处理结果
        output_format: 输出格式（json/text）
        
    Returns:
        格式化后的字符串
    """
    if output_format == "json":
        import json
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = [
            f"类型: {result.data.get('type', 'unknown')}",
            f"字段数: {result.data.get('fields_found', 0)}",
            f"置信度: {result.confidence:.1%}",
        ]
        if result.warnings:
            lines.append("警告: " + "; ".join(result.warnings))
        return "\n".join(lines)
    else:
        raise ValueError("E008")


# ============================================================
# 批量处理
# ============================================================

def batch_process(inputs: List[Any]) -> List[ProcessingResult]:
    """
    批量处理多个输入。
    
    Args:
        inputs: 输入列表
        
    Returns:
        处理结果列表
    """
    if not inputs:
        raise ValueError("E001")
    
    results = []
    for item in inputs:
        try:
            results.append(process_input(item))
        except ValueError as e:
            # 单条失败不中断整体
            error_code = str(e)
            results.append(ProcessingResult(
                {"error": error_code},
                0.0,
                [ERROR_CODES.get(error_code, ERROR_CODES["E010"])]
            ))
    
    return results


# ============================================================
# 命令行接口
# ============================================================

def run_selftest() -> bool:
    """
    离线自检功能：使用内置硬编码样例数据验证核心逻辑。
    不依赖外部文件、网络或当前工作目录。
    
    Returns:
        自检是否通过
    """
    print("开始自检...")
    
    # 测试1: 正常字符串输入
    try:
        result = process_input("姓名:张三\n年龄:30\n城市:北京")
        assert result.confidence > 0.85, "正常输入置信度过低"
        assert result.data["fields_found"] >= 2, "字段提取数量不足"
        print("[PASS] 字符串输入处理")
    except Exception as e:
        print(f"[FAIL] 字符串输入处理: {e}")
        return False
    
    # 测试2: 字典输入
    try:
        result = process_input({"name": "test", "value": 42})
        assert result.confidence > 0.85, "字典输入置信度过低"
        assert "keys" in result.data, "字典键提取失败"
        print("[PASS] 字典输入处理")
    except Exception as e:
        print(f"[FAIL] 字典输入处理: {e}")
        return False
    
    # 测试3: 空输入应报错 E001
    try:
        process_input(None)
        print("[FAIL] 空输入未报错")
        return False
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为 E001，实际 {e}"
        print("[PASS] 空输入错误处理")
    except Exception as e:
        print(f"[FAIL] 空输入错误处理: {e}")
        return False
    
    # 测试4: 批量处理
    try:
        results = batch_process(["数据1", "数据2", None])
        assert len(results) == 3, "批量处理数量错误"
        assert results[2].data.get("error") == "E001", "批量处理错误处理失败"
        print("[PASS] 批量处理")
    except Exception as e:
        print(f"[FAIL] 批量处理: {e}")
        return False
    
    # 测试5: 输出格式
    try:
        result = process_input("测试数据")
        json_out = format_output(result, "json")
        assert "confidence" in json_out, "JSON输出缺少置信度"
        text_out = format_output(result, "text")
        assert "置信度" in text_out, "文本输出缺少置信度"
        print("[PASS] 输出格式")
    except Exception as e:
        print(f"[FAIL] 输出格式: {e}")
        return False
    
    # 测试6: 错误码体系完整性
    try:
        assert len(ERROR_CODES) >= 5, "错误码数量不足"
        assert "E001" in ERROR_CODES and "E005" in ERROR_CODES, "错误码缺失"
        print("[PASS] 错误码体系")
    except Exception as e:
        print(f"[FAIL] 错误码体系: {e}")
        return False
    
    print("全部自检通过！")
    return True


def interactive_mode() -> None:
    """交互模式：从标准输入读取数据并处理"""
    print("请输入数据（Ctrl+D 结束）：")
    try:
        lines = []
        for line in sys.stdin:
            lines.append(line.rstrip("\n"))
        
        if not lines:
            print(f"错误 E001: {ERROR_CODES['E001']}")
            return
        
        # 简单处理：合并为字符串或保持列表
        if len(lines) == 1:
            input_data = lines[0]
        else:
            input_data = lines
        
        result = process_input(input_data)
        print("\n处理结果：")
        print(format_output(result))
        
    except KeyboardInterrupt:
        print("\n已取消")
    except ValueError as e:
        error_code = str(e)
        print(f"错误 {error_code}: {ERROR_CODES.get(error_code, ERROR_CODES['E010'])}")


def main() -> int:
    """
    主入口函数。
    
    Returns:
        退出码（0成功，非0失败）
    """
    parser = argparse.ArgumentParser(
        description="SQL查询技能 - 数据处理工具",
        epilog="示例: python main.py --input '数据内容' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        help="待处理的数据（字符串或JSON）"
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
        help="运行离线自检"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="交互模式（从标准输入读取）"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 交互模式
    if args.interactive:
        interactive_mode()
        return 0
    
    # 命令行输入模式
    if args.input:
        try:
            # 尝试解析JSON
            import json
            try:
                input_data = json.loads(args.input)
            except json.JSONDecodeError:
                input_data = args.input
            
            result = process_input(input_data)
            print(format_output(result, args.format))
            return 0
            
        except ValueError as e:
            error_code = str(e)
            print(f"错误 {error_code}: {ERROR_CODES.get(error_code, ERROR_CODES['E010'])}")
            return 1
        except Exception as e:
            print(f"错误 E010: {ERROR_CODES['E010']}: {e}")
            return 1
    
    # 无参数时显示帮助
    parser.print_help()
    return 0


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
