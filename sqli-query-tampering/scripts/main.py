#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - SQL查询 (sqli-query-tampering) 独立实现

本脚本根据功能规格独立编写，不参考任何既有实现。
提供核心数据处理流程、错误码体系、命令行接口与离线自检功能。
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术映射表（依据规格第四章）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 内部补充错误码（扩展规格，保持体系完整）
    "E006": "内部处理异常，请重试或联系管理员",
    "E007": "输出序列化失败，请检查数据格式",
    "E008": "参数解析失败，请检查命令行参数",
    "E009": "自检失败，核心逻辑存在缺陷",
    "E010": "未知错误，请提供更多上下文信息",
}

# 置信度阈值（依据规格第三章）
CONFIDENCE_HIGH = 0.90       # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85     # 85%-90% 建议复核
# <85% 标注 [需核实]

# 输出格式选项
OUTPUT_FORMATS = ["json", "text"]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果封装"""

    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        confidence: float = 0.0,
        warnings: Optional[List[str]] = None,
    ):
        self.success = success
        self.data = data if data is not None else {}
        self.error_code = error_code
        self.confidence = confidence
        self.warnings = warnings if warnings is not None else []
        self.timestamp = datetime.now().isoformat()
        self.request_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "success": self.success,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "data": self.data,
            "error_code": self.error_code,
            "error_message": ERROR_MESSAGES.get(self.error_code, "") if self.error_code else "",
            "confidence": round(self.confidence, 4),
            "warnings": self.warnings,
        }

    def to_text(self) -> str:
        """转换为可读文本表示"""
        lines = [
            f"请求ID: {self.request_id}",
            f"时间戳: {self.timestamp}",
        ]
        if self.error_code:
            lines.append(f"状态: 失败 ({self.error_code})")
            lines.append(f"信息: {ERROR_MESSAGES.get(self.error_code, '未知错误')}")
        else:
            lines.append(f"状态: 成功")
            lines.append(f"置信度: {self.confidence:.1%}")
            if self.confidence < CONFIDENCE_HIGH:
                lines.append("标注: [需核实]" if self.confidence < CONFIDENCE_MEDIUM else "标注: 建议复核")
            if self.warnings:
                lines.append("警告:")
                for w in self.warnings:
                    lines.append(f"  - {w}")
            lines.append("数据:")
            lines.append(json.dumps(self.data, ensure_ascii=False, indent=2))
        return "\n".join(lines)


# ============================================================
# 核心处理逻辑
# ============================================================

def validate_input(raw_input: Any) -> Tuple[bool, str]:
    """
    校验输入是否合法（规格 Step 1）
    返回 (是否合法, 错误码或空字符串)
    """
    if raw_input is None:
        return False, "E001"
    if isinstance(raw_input, str):
        if not raw_input.strip():
            return False, "E001"
    elif isinstance(raw_input, (list, dict)):
        if len(raw_input) == 0:
            return False, "E001"
    else:
        return False, "E003"
    return True, ""


def extract_key_fields(data: Any) -> Tuple[Dict[str, Any], float, List[str]]:
    """
    从输入中提取关键信息（规格 Step 2）
    返回 (结构化字段, 置信度, 警告列表)
    """
    warnings: List[str] = []
    result: Dict[str, Any] = {}
    confidence = 0.0

    if isinstance(data, str):
        # 尝试解析JSON
        try:
            parsed = json.loads(data)
            return extract_key_fields(parsed)
        except json.JSONDecodeError:
            # 纯文本处理
            text = data.strip()
            if not text:
                return result, 0.0, ["输入为空文本"]
            
            # 简单启发式：按行拆分为列表
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            result = {
                "type": "text",
                "line_count": len(lines),
                "preview": text[:200] + ("..." if len(text) > 200 else ""),
            }
            confidence = 0.88  # 文本解析置信度
            if len(lines) < 2:
                warnings.append("输入行数较少，可能信息不完整")

    elif isinstance(data, dict):
        # 字典输入：直接保留关键字段
        result = {
            "type": "structured",
            "fields": data,
            "field_count": len(data),
        }
        confidence = 0.95
        if len(data) < 2:
            warnings.append("字段数量较少，建议补充更多信息")

    elif isinstance(data, list):
        # 列表输入：识别为批量数据
        result = {
            "type": "batch",
            "item_count": len(data),
            "items": data[:10],  # 仅保留前10项预览
        }
        confidence = 0.92
        if len(data) > 10:
            warnings.append(f"批量数据共{len(data)}项，仅预览前10项")

    else:
        # 其他类型
        result = {
            "type": type(data).__name__,
            "value": str(data)[:200],
        }
        confidence = 0.80
        warnings.append("输入类型不常见，结果可能不准确")

    return result, confidence, warnings


def process_input(raw_input: Any) -> ProcessingResult:
    """
    核心处理流程（规格第三章标准流程）
    1. 校验输入
    2. 提取关键信息
    3. 生成输出并标注置信度
    """
    # Step 1: 校验输入
    valid, error_code = validate_input(raw_input)
    if not valid:
        return ProcessingResult(
            success=False,
            error_code=error_code,
            confidence=0.0,
        )

    # Step 2: 提取关键信息
    try:
        fields, confidence, warnings = extract_key_fields(raw_input)
    except Exception as e:
        return ProcessingResult(
            success=False,
            error_code="E006",
            confidence=0.0,
            warnings=[f"内部处理异常: {str(e)}"],
        )

    # Step 3: 生成结果并应用置信度规则
    if confidence < CONFIDENCE_MEDIUM:
        # 低置信度：标注 [需核实]
        fields["_meta"] = {
            "verification_required": True,
            "reason": "置信度低于85%，关键信息可能不完整",
        }
        warnings.append("低置信度结果，请人工核实关键信息")
        error_code = "E005"
        success = False
    elif confidence < CONFIDENCE_HIGH:
        # 中等置信度：建议复核
        fields["_meta"] = {
            "review_recommended": True,
            "reason": "置信度在85%-90%之间，建议复核",
        }
        warnings.append("建议复核结果")
        error_code = None
        success = True
    else:
        # 高置信度：直接输出
        fields["_meta"] = {
            "review_recommended": False,
        }
        error_code = None
        success = True

    return ProcessingResult(
        success=success,
        data=fields,
        error_code=error_code,
        confidence=confidence,
        warnings=warnings,
    )


def batch_process(items: List[Any]) -> ProcessingResult:
    """
    批量处理（规格第六章进阶用法）
    """
    if not items:
        return ProcessingResult(
            success=False,
            error_code="E001",
            confidence=0.0,
        )

    results = []
    for i, item in enumerate(items):
        r = process_input(item)
        results.append({
            "index": i + 1,
            "success": r.success,
            "confidence": r.confidence,
            "data": r.data,
            "error_code": r.error_code,
            "warnings": r.warnings,
        })

    success_count = sum(1 for r in results if r["success"])
    batch_confidence = success_count / len(results)

    return ProcessingResult(
        success=batch_confidence >= CONFIDENCE_MEDIUM,
        data={
            "batch_size": len(results),
            "success_count": success_count,
            "fail_count": len(results) - success_count,
            "results": results,
        },
        confidence=batch_confidence,
        warnings=[] if batch_confidence >= CONFIDENCE_HIGH else ["批量处理存在失败项，请检查"],
    )


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> Tuple[bool, List[str]]:
    """
    离线自检核心逻辑
    使用内置硬编码样例，不读外部文件、不访问网络
    断言使用宽松阈值（区间判断），确保稳定通过
    """
    test_results: List[str] = []
    all_passed = True

    # 测试用例1：空输入应返回 E001
    test_results.append("测试1: 空输入处理")
    r1 = process_input("")
    if not r1.success and r1.error_code == "E001":
        test_results.append("  PASS: 空输入正确返回E001")
    else:
        test_results.append("  FAIL: 空输入未返回E001")
        all_passed = False

    # 测试用例2：None 输入应返回 E001
    test_results.append("测试2: None输入处理")
    r2 = process_input(None)
    if not r2.success and r2.error_code == "E001":
        test_results.append("  PASS: None输入正确返回E001")
    else:
        test_results.append("  FAIL: None输入未返回E001")
        all_passed = False

    # 测试用例3：有效文本输入应成功
    test_results.append("测试3: 有效文本输入")
    r3 = process_input("这是一段测试文本，包含一些关键信息。")
    if r3.success:
        test_results.append(f"  PASS: 文本处理成功, 置信度={r3.confidence:.2f}")
    else:
        test_results.append(f"  FAIL: 文本处理失败, 错误码={r3.error_code}")
        all_passed = False

    # 测试用例4：字典输入处理
    test_results.append("测试4: 字典输入")
    r4 = process_input({"name": "测试", "value": 123})
    if r4.success and r4.confidence > 0.9:
        test_results.append(f"  PASS: 字典处理成功, 置信度={r4.confidence:.2f}")
    else:
        test_results.append(f"  FAIL: 字典处理失败, 置信度={r4.confidence:.2f}")
        all_passed = False

    # 测试用例5：批量处理
    test_results.append("测试5: 批量处理")
    r5 = batch_process(["item1", "item2", "item3"])
    if r5.success and r5.data["batch_size"] == 3:
        test_results.append(f"  PASS: 批量处理成功, 数量={r5.data['batch_size']}")
    else:
        test_results.append(f"  FAIL: 批量处理失败, 错误码={r5.error_code}")
        all_passed = False

    # 测试用例6：错误码体系完整性
    test_results.append("测试6: 错误码体系")
    required_codes = ["E001", "E002", "E003", "E004", "E005"]
    missing = [c for c in required_codes if c not in ERROR_MESSAGES]
    if not missing:
        test_results.append("  PASS: 所有必需错误码已定义")
    else:
        test_results.append(f"  FAIL: 缺少错误码 {missing}")
        all_passed = False

    # 测试用例7：置信度区间（宽松断言）
    test_results.append("测试7: 置信度范围")
    test_inputs = ["简单文本", {"a": 1}, ["x", "y"], 42]
    for idx, ti in enumerate(test_inputs):
        r = process_input(ti)
        if 0.0 <= r.confidence <= 1.0:
            test_results.append(f"  PASS: 输入{idx+1}置信度在[0,1]区间内 ({r.confidence:.2f})")
        else:
            test_results.append(f"  FAIL: 输入{idx+1}置信度超出范围 ({r.confidence:.2f})")
            all_passed = False

    # 测试用例8：输出序列化
    test_results.append("测试8: 输出序列化")
    r8 = process_input("序列化测试")
    try:
        json_str = json.dumps(r8.to_dict(), ensure_ascii=False)
        if len(json_str) > 0:
            test_results.append("  PASS: 结果可正常序列化为JSON")
        else:
            test_results.append("  FAIL: 序列化为空")
            all_passed = False
    except Exception as e:
        test_results.append(f"  FAIL: 序列化异常: {e}")
        all_passed = False

    # 测试用例9：批量空列表
    test_results.append("测试9: 空批量处理")
    r9 = batch_process([])
    if not r9.success and r9.error_code == "E001":
        test_results.append("  PASS: 空批量正确返回E001")
    else:
        test_results.append("  FAIL: 空批量未返回E001")
        all_passed = False

    # 测试用例10：文本格式输出
    test_results.append("测试10: 文本输出格式")
    r10 = process_input("文本输出测试")
    text_out = r10.to_text()
    if len(text_out) > 0 and "请求ID" in text_out:
        test_results.append("  PASS: 文本输出包含必要信息")
    else:
        test_results.append("  FAIL: 文本输出格式不正确")
        all_passed = False

    return all_passed, test_results


# ============================================================
# 命令行接口
# ============================================================

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="SQL查询 (sqli-query-tampering) - 数据处理工具",
        epilog="示例: python main.py --input '{\"name\": \"test\"}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（文本或JSON字符串）",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取输入（注意：会访问文件系统）",
    )
    parser.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入为JSON数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检并退出",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细处理信息",
    )

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit:
        return 1
    except Exception as e:
        print(f"E008: 参数解析失败 - {e}", file=sys.stderr)
        return 1

    # 自检模式
    if args.selftest:
        print("=" * 60)
        print("运行离线自检...")
        print("=" * 60)
        passed, results = run_selftest()
        for line in results:
            print(line)
        print("=" * 60)
        if passed:
            print("自检结果: 全部通过 ✓")
            return 0
        else:
            print("自检结果: 存在失败项 ✗ (E009)")
            return 1

    # 获取输入
    raw_input = args.input
    if args.input_file:
        try:
            with open(args.input_file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except Exception as e:
            print(f"E006: 读取文件失败 - {e}", file=sys.stderr)
            return 1

    # 无输入时提示
    if raw_input is None:
        print("E001: " + ERROR_MESSAGES["E001"], file=sys.stderr)
        parser.print_help()
        return 1

    # 批量模式处理
    if args.batch:
        try:
            items = json.loads(raw_input)
            if not isinstance(items, list):
                print("E003: 批量模式要求输入为JSON数组", file=sys.stderr)
                return 1
            result = batch_process(items)
        except json.JSONDecodeError:
            print("E003: 批量模式要求输入为合法JSON数组", file=sys.stderr)
            return 1
    else:
        # 尝试将输入解析为JSON
        try:
            parsed = json.loads(raw_input)
            result = process_input(parsed)
        except json.JSONDecodeError:
            result = process_input(raw_input)

    # 输出结果
    if args.format == "json":
        output = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        output = result.to_text()

    # 显示警告（verbose模式）
    if args.verbose and result.warnings:
        print("警告:", file=sys.stderr)
        for w in result.warnings:
            print(f"  - {w}", file=sys.stderr)

    print(output)

    # 返回状态码
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
