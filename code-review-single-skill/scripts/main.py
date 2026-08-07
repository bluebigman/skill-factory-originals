#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码审查技能 - 独立实现脚本
================================
依据功能规格 clean-room 重写，仅使用标准库。
提供命令行接口与离线自检功能。

用法:
    python main.py --selftest          # 运行内置自检
    python main.py --help              # 查看帮助
"""

import argparse
import sys
from typing import Dict, List, Any


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "内部处理错误",
    "E007": "参数解析错误",
    "E008": "文件读取失败",
    "E009": "数据校验失败",
    "E010": "未知错误",
}

# 置信度阈值
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 85


# ============================================================
# 核心数据结构
# ============================================================
class ReviewResult:
    """代码审查结果对象"""
    def __init__(self):
        self.fields: Dict[str, Any] = {}
        self.confidence: int = 0
        self.warnings: List[str] = []
        self.raw_output: str = ""


# ============================================================
# 核心处理函数
# ============================================================
def validate_input(data: Any) -> None:
    """
    校验输入数据有效性
    错误码: E001, E002, E003
    """
    if data is None:
        raise ValueError("E001")
    
    if isinstance(data, str):
        if not data.strip():
            raise ValueError("E001")
    elif isinstance(data, (list, dict, tuple)):
        if len(data) == 0:
            raise ValueError("E001")
    else:
        raise ValueError("E003")


def extract_key_fields(data: Any) -> Dict[str, Any]:
    """
    从输入中提取关键字段并结构化
    错误码: E002, E003
    """
    result = {}
    
    try:
        if isinstance(data, dict):
            # 字典输入：直接提取已知字段
            for key in ["title", "content", "type", "source"]:
                if key in data:
                    result[key] = data[key]
            
            # 检查是否缺少必要字段
            if "content" not in result and "title" not in result:
                raise ValueError("E002")
                
        elif isinstance(data, str):
            # 字符串输入：按行解析
            lines = [line.strip() for line in data.split('\n') if line.strip()]
            if lines:
                result["content"] = lines
                result["line_count"] = len(lines)
            else:
                raise ValueError("E002")
                
        elif isinstance(data, (list, tuple)):
            # 列表输入：视为内容行
            result["content"] = list(data)
            result["line_count"] = len(data)
            
        else:
            raise ValueError("E003")
            
    except ValueError:
        raise
    except Exception:
        raise ValueError("E006")
    
    return result


def calculate_confidence(fields: Dict[str, Any]) -> int:
    """
    计算处理结果的置信度
    规则：
    - 字段完整度越高，置信度越高
    - 有警告信息时降低置信度
    """
    base_score = 70  # 基础分
    
    # 根据字段完整度加分
    field_count = len(fields)
    if field_count >= 5:
        base_score += 20
    elif field_count >= 3:
        base_score += 15
    elif field_count >= 1:
        base_score += 10
    
    # 根据内容长度加分
    content = fields.get("content", "")
    if isinstance(content, (list, str)):
        length = len(content) if isinstance(content, list) else len(content)
        if length > 100:
            base_score += 5
        elif length > 10:
            base_score += 3
    
    # 限制在 0-100 范围
    return max(0, min(100, base_score))


def format_output(result: ReviewResult, output_format: str = "text") -> str:
    """
    按指定格式生成输出
    支持: text, json, summary
    """
    if output_format == "json":
        # 简易 JSON 输出
        import json
        return json.dumps({
            "fields": result.fields,
            "confidence": result.confidence,
            "warnings": result.warnings
        }, ensure_ascii=False, indent=2)
    
    elif output_format == "summary":
        # 摘要格式
        lines = []
        lines.append("=== 处理摘要 ===")
        lines.append(f"置信度: {result.confidence}%")
        
        if result.confidence >= HIGH_CONFIDENCE:
            lines.append("状态: 可直接使用")
        elif result.confidence >= MEDIUM_CONFIDENCE:
            lines.append("状态: 建议复核")
        else:
            lines.append("状态: [需核实]")
        
        if result.warnings:
            lines.append("\n警告信息:")
            for w in result.warnings:
                lines.append(f"  - {w}")
        
        return "\n".join(lines)
    
    else:
        # 默认文本格式
        lines = []
        lines.append("=== 处理结果 ===")
        
        for key, value in result.fields.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value[:5]:  # 只显示前5行
                    lines.append(f"  - {item}")
                if len(value) > 5:
                    lines.append(f"  ... 共 {len(value)} 条")
            else:
                lines.append(f"{key}: {value}")
        
        lines.append(f"\n置信度: {result.confidence}%")
        
        if result.confidence < HIGH_CONFIDENCE:
            lines.append("提示: 结果建议人工复核")
        
        if result.warnings:
            lines.append("\n警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")
        
        return "\n".join(lines)


def process_data(data: Any, output_format: str = "text") -> ReviewResult:
    """
    核心处理流程
    1. 校验输入
    2. 提取字段
    3. 计算置信度
    4. 生成输出
    """
    result = ReviewResult()
    
    try:
        # Step 1: 输入校验
        validate_input(data)
        
        # Step 2: 提取关键字段
        result.fields = extract_key_fields(data)
        
        # Step 3: 计算置信度
        result.confidence = calculate_confidence(result.fields)
        
        # Step 4: 生成警告
        if result.confidence < HIGH_CONFIDENCE:
            result.warnings.append("部分字段可能不完整，请核实")
        
        # Step 5: 格式化输出
        result.raw_output = format_output(result, output_format)
        
    except ValueError as e:
        error_code = str(e)
        if error_code in ERROR_CODES:
            result.warnings.append(f"错误 {error_code}: {ERROR_CODES[error_code]}")
            result.confidence = 0
        else:
            result.warnings.append(f"错误 E010: {ERROR_CODES['E010']}")
            result.confidence = 0
    
    return result


# ============================================================
# 自检函数
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检
    使用硬编码样例数据，不访问外部资源
    """
    print("开始自检...")
    all_passed = True
    
    # 测试用例 1: 字典输入
    print("\n[测试 1] 字典输入")
    test_data = {
        "title": "示例文档",
        "content": "这是一段测试内容\n包含多行文本\n用于验证处理逻辑",
        "type": "text"
    }
    try:
        result = process_data(test_data)
        assert result.confidence > 50, "置信度应大于50"
        assert "title" in result.fields, "应包含title字段"
        assert "content" in result.fields, "应包含content字段"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 2: 字符串输入
    print("\n[测试 2] 字符串输入")
    test_text = "第一行内容\n第二行内容\n第三行内容"
    try:
        result = process_data(test_text)
        assert result.confidence > 0, "置信度应大于0"
        assert "content" in result.fields, "应包含content字段"
        assert result.fields.get("line_count", 0) >= 3, "应至少有3行"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 3: 空输入
    print("\n[测试 3] 空输入")
    try:
        result = process_data("")
        assert result.confidence == 0, "空输入置信度应为0"
        assert any("E001" in w for w in result.warnings), "应包含E001错误"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 4: 批量处理
    print("\n[测试 4] 批量处理")
    test_batch = ["项目A", "项目B", "项目C"]
    try:
        results = [process_data(item) for item in test_batch]
        assert len(results) == 3, "应处理3个项目"
        assert all(r.confidence > 0 for r in results), "所有项目置信度应大于0"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 5: 输出格式
    print("\n[测试 5] 输出格式")
    try:
        result = process_data(test_data, output_format="json")
        assert "confidence" in result.raw_output, "JSON输出应包含置信度"
        
        result = process_data(test_data, output_format="summary")
        assert "置信度" in result.raw_output, "摘要输出应包含置信度"
        
        result = process_data(test_data, output_format="text")
        assert "处理结果" in result.raw_output, "文本输出应包含处理结果"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 6: 错误码验证
    print("\n[测试 6] 错误码验证")
    try:
        # 验证所有错误码都存在
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 7: 边界输入
    print("\n[测试 7] 边界输入")
    try:
        # 超长输入
        long_text = "x" * 10000
        result = process_data(long_text)
        assert result.confidence >= 70, "长文本置信度应较高"
        
        # 特殊字符
        special_text = "特殊字符: !@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`"
        result = process_data(special_text)
        assert result.confidence > 0, "特殊字符输入应能处理"
        
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 8: 列表输入
    print("\n[测试 8] 列表输入")
    try:
        test_list = ["第一项", "第二项", "第三项", "第四项"]
        result = process_data(test_list)
        assert result.fields.get("line_count", 0) == 4, "应识别4项"
        assert result.confidence > 0, "置信度应大于0"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 汇总
    print("\n" + "=" * 40)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("存在失败项 ✗")
    print("=" * 40)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="代码审查技能 - 独立实现",
        epilog="示例: python main.py --selftest"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        help="输入文本或JSON字符串"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "summary"],
        default="text",
        help="输出格式 (默认: text)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 处理输入
    if args.input:
        try:
            # 尝试解析为JSON
            import json
            try:
                data = json.loads(args.input)
            except json.JSONDecodeError:
                # 不是JSON，按普通文本处理
                data = args.input
            
            result = process_data(data, args.format)
            print(result.raw_output)
            
            if args.verbose:
                print("\n=== 调试信息 ===")
                print(f"字段数: {len(result.fields)}")
                print(f"警告数: {len(result.warnings)}")
            
            return 0
            
        except Exception as e:
            print(f"错误 E010: {ERROR_CODES['E010']}: {e}", file=sys.stderr)
            return 1
    
    # 无参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
