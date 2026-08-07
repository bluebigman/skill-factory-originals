#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hec-commander 工具主脚本
功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理和自定义格式。
本实现为 clean-room 独立编写，仅依据功能规格实现。
"""

import sys
import argparse
import json
import re
from typing import Any, Dict, List, Optional, Union


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "批量处理中断，请检查各项输入",
    "E008": "输出格式不支持，请选择支持的格式",
    "E009": "置信度计算异常，请重新输入",
    "E010": "未知错误，请查看日志或联系管理员",
}


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果数据类"""
    def __init__(self, status: str = "success", data: Any = None,
                 confidence: float = 1.0, warnings: List[str] = None,
                 error_code: str = None):
        self.status = status  # success / warning / error
        self.data = data
        self.confidence = confidence  # 0.0 - 1.0
        self.warnings = warnings or []
        self.error_code = error_code

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status,
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "error_code": self.error_code,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
class DataProcessor:
    """数据处理核心类"""

    # 可识别的关键字段模式（用于结构化提取）
    FIELD_PATTERNS = {
        "id": r"(?:ID|编号)[:：\s]*([A-Za-z0-9_-]+)",
        "name": r"(?:名称|名字)[:：\s]*([\u4e00-\u9fa5A-Za-z0-9_\- ]+)",
        "type": r"(?:类型)[:：\s]*([\u4e00-\u9fa5A-Za-z0-9_\- ]+)",
        "value": r"(?:数值|值)[:：\s]*([0-9]+\.?[0-9]*)",
        "unit": r"(?:单位)[:：\s]*([\u4e00-\u9fa5A-Za-z]+)",
        "description": r"(?:描述|说明)[:：\s]*(.+)",
        "url": r"https?://[^\s]+",
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
        "phone": r"1[3-9]\d{9}",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
    }

    def __init__(self):
        self.batch_mode = False
        self.custom_format = None

    def process(self, input_data: Union[str, List[str]], 
                output_format: str = "json") -> ProcessingResult:
        """
        主处理入口
        Args:
            input_data: 输入数据（字符串或字符串列表）
            output_format: 输出格式（json/text/dict）
        Returns:
            ProcessingResult 对象
        """
        # 输入校验
        if not input_data:
            return ProcessingResult("error", error_code="E001")

        # 批量处理判断
        if isinstance(input_data, list):
            self.batch_mode = True
            return self._process_batch(input_data, output_format)
        else:
            self.batch_mode = False
            return self._process_single(input_data, output_format)

    def _process_single(self, text: str, output_format: str) -> ProcessingResult:
        """处理单个输入"""
        if not text or not text.strip():
            return ProcessingResult("error", error_code="E001")

        try:
            # 1. 识别关键信息
            extracted = self._extract_fields(text)
            if not extracted:
                return ProcessingResult("error", error_code="E003")

            # 2. 计算置信度
            confidence = self._calculate_confidence(text, extracted)
            if confidence < 0.85:
                extracted["_warning"] = "[需核实] 低置信度结果，请人工复核"
            elif confidence < 0.9:
                extracted["_warning"] = "建议复核"

            # 3. 格式化输出
            result = self._format_output(extracted, output_format)

            # 4. 构建返回结果
            status = "success"
            if confidence < 0.9:
                status = "warning"
            return ProcessingResult(status, result, confidence)

        except Exception as e:
            return ProcessingResult("error", error_code="E006", 
                                   warnings=[str(e)])

    def _process_batch(self, items: List[str], output_format: str) -> ProcessingResult:
        """批量处理多个输入"""
        if not items:
            return ProcessingResult("error", error_code="E001")

        results = []
        success_count = 0
        warnings = []

        for idx, item in enumerate(items):
            if not item or not item.strip():
                warnings.append(f"第 {idx+1} 项为空，已跳过")
                continue

            try:
                result = self._process_single(item, output_format)
                if result.status == "error":
                    warnings.append(f"第 {idx+1} 项处理失败: {result.error_code}")
                else:
                    success_count += 1
                    results.append(result.data)
            except Exception:
                warnings.append(f"第 {idx+1} 项处理异常")

        # 计算整体置信度（按成功率）
        total = len(items)
        if total > 0:
            confidence = success_count / total
        else:
            confidence = 0.0

        if success_count == 0:
            return ProcessingResult("error", error_code="E007", 
                                   confidence=confidence, warnings=warnings)

        status = "success" if confidence >= 0.9 else "warning"
        return ProcessingResult(status, results, confidence, warnings)

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """从文本中提取关键字段"""
        fields = {}

        # 识别 URL
        urls = re.findall(self.FIELD_PATTERNS["url"], text)
        if urls:
            fields["url"] = urls[0] if len(urls) == 1 else urls

        # 识别邮箱
        emails = re.findall(self.FIELD_PATTERNS["email"], text)
        if emails:
            fields["email"] = emails[0] if len(emails) == 1 else emails

        # 识别手机号
        phones = re.findall(self.FIELD_PATTERNS["phone"], text)
        if phones:
            fields["phone"] = phones[0] if len(phones) == 1 else phones

        # 识别日期
        dates = re.findall(self.FIELD_PATTERNS["date"], text)
        if dates:
            fields["date"] = dates[0] if len(dates) == 1 else dates

        # 识别结构化字段（ID、名称、类型、值等）
        for field_name, pattern in self.FIELD_PATTERNS.items():
            if field_name in ["url", "email", "phone", "date"]:
                continue  # 已在上面处理
            match = re.search(pattern, text)
            if match:
                fields[field_name] = match.group(1).strip()

        # 如果没有任何识别结果，尝试整段作为内容
        if not fields:
            # 至少保留原文
            fields["_raw_text"] = text.strip()

        return fields

    def _calculate_confidence(self, text: str, extracted: Dict[str, Any]) -> float:
        """计算置信度（0.0 - 1.0）"""
        if not text or not extracted:
            return 0.0

        score = 0.0
        total_checks = 4

        # 检查1: 文本长度（太短置信度低）
        if len(text) >= 10:
            score += 1.0
        elif len(text) >= 5:
            score += 0.6
        else:
            score += 0.2

        # 检查2: 字段识别数量（越多越可信）
        field_count = len(extracted)
        if field_count >= 3:
            score += 1.0
        elif field_count == 2:
            score += 0.7
        else:
            score += 0.4

        # 检查3: 是否包含关键标识符
        has_identifier = any(k in extracted for k in ["id", "name", "url", "email"])
        score += 1.0 if has_identifier else 0.3

        # 检查4: 文本结构（是否包含多种类型信息）
        structure_indicators = 0
        if re.search(r"[:：]", text):
            structure_indicators += 1
        if re.search(r"[,，;；]", text):
            structure_indicators += 1
        if re.search(r"\d", text):
            structure_indicators += 1
        score += structure_indicators / 3.0

        # 归一化到 0-1
        confidence = score / total_checks
        # 确保在合理范围内
        return max(0.0, min(1.0, confidence))

    def _format_output(self, data: Dict[str, Any], output_format: str) -> Any:
        """按指定格式输出"""
        if output_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == "dict":
            return data
        elif output_format == "text":
            # 生成文本格式
            lines = []
            for key, value in data.items():
                if not key.startswith("_"):
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")


# ============================================================
# 命令行接口
# ============================================================
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="hec-commander - 数据处理与结构化工具",
        epilog="示例: python main.py --input '名称: 测试项目; 类型: 水文; 值: 123.45' --format json"
    )
    parser.add_argument("--input", "-i", 
                       help="输入数据（字符串）或文件路径")
    parser.add_argument("--batch", "-b",
                       help="批量输入，多个值用分号(;)分隔")
    parser.add_argument("--format", "-f", default="json",
                       choices=["json", "text", "dict"],
                       help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true",
                       help="运行内置自检程序")
    parser.add_argument("--output", "-o",
                       help="输出文件路径（可选）")
    return parser.parse_args()


def run_selftest() -> int:
    """
    内置自检程序
    使用硬编码样例数据，不依赖外部文件或网络
    """
    print("=" * 60)
    print("hec-commander 自检程序")
    print("=" * 60)

    processor = DataProcessor()
    test_cases = [
        {
            "name": "基本文本处理",
            "input": "名称: 水文模型; 类型: HEC-RAS; 值: 123.45; 单位: m",
            "expect_success": True,
            "check": lambda r: r.status == "success" and r.confidence >= 0.5
        },
        {
            "name": "URL 识别",
            "input": "请处理这个链接: https://www.hec.usace.army.mil/ 包含模型数据",
            "expect_success": True,
            "check": lambda r: r.status == "success" and r.confidence >= 0.5
        },
        {
            "name": "空输入处理",
            "input": "",
            "expect_success": False,
            "check": lambda r: r.error_code == "E001"
        },
        {
            "name": "批量处理",
            "input": ["项目A: 类型: 水文; 值: 100", "项目B: 类型: 水力学; 值: 200"],
            "expect_success": True,
            "check": lambda r: r.status == "success" and r.confidence >= 0.5
        },
        {
            "name": "复杂混合输入",
            "input": "ID: HEC-001; 名称: 洪水模拟; 类型: 分析; 值: 999.99; 单位: m3/s; 描述: 城市防洪评估; 日期: 2026-01-15",
            "expect_success": True,
            "check": lambda r: r.status == "success" and r.confidence >= 0.5
        }
    ]

    passed = 0
    failed = 0

    for idx, case in enumerate(test_cases, 1):
        print(f"\n测试 {idx}: {case['name']}")
        try:
            if isinstance(case["input"], list):
                result = processor.process(case["input"], "dict")
            else:
                result = processor.process(case["input"], "dict")
            
            # 宽松断言：只验证状态和基本条件
            check_result = case["check"](result)
            
            if result.error_code:
                print(f"  -> 错误码: {result.error_code}")
                
            if case["expect_success"]:
                if result.status == "error":
                    print(f"  [FAIL] 期望成功但得到错误: {result.error_code}")
                    failed += 1
                elif check_result:
                    print(f"  [PASS] 状态={result.status}, 置信度={result.confidence:.2f}")
                    passed += 1
                else:
                    print(f"  [FAIL] 断言条件未满足")
                    failed += 1
            else:
                if result.status == "error" and result.error_code == "E001":
                    print(f"  [PASS] 正确拒绝了空输入")
                    passed += 1
                else:
                    print(f"  [FAIL] 期望错误但得到: {result.status}")
                    failed += 1

        except Exception as e:
            print(f"  [FAIL] 异常: {str(e)}")
            failed += 1

    # 输出汇总
    print("\n" + "=" * 60)
    print(f"自检结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed > 0:
        print("存在失败用例，请检查实现")
        return 1
    else:
        print("所有用例通过，实现正常")
        return 0


def main() -> int:
    """主函数"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    processor = DataProcessor()

    try:
        # 收集输入
        if args.batch:
            # 批量模式：分号分隔
            items = [item.strip() for item in args.batch.split(";") if item.strip()]
            if not items:
                print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
                return 1
            result = processor.process(items, args.format)
        elif args.input:
            # 单条输入
            result = processor.process(args.input, args.format)
        else:
            # 无输入：提示
            print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
            return 1

        # 处理结果
        if result.status == "error":
            error_msg = ERROR_CODES.get(result.error_code, "未知错误")
            print(f"错误 {result.error_code}: {error_msg}", file=sys.stderr)
            if result.warnings:
                for w in result.warnings:
                    print(f"  警告: {w}", file=sys.stderr)
            return 1

        # 输出结果
        output_text = ""
        if isinstance(result.data, str):
            output_text = result.data
        elif isinstance(result.data, (dict, list)):
            output_text = json.dumps(result.data, ensure_ascii=False, indent=2)
        else:
            output_text = str(result.data)

        # 输出到文件或控制台
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"结果已写入: {args.output}")
        else:
            print(output_text)

        # 打印状态信息
        if result.warnings:
            for w in result.warnings:
                print(f"提示: {w}", file=sys.stderr)
        print(f"置信度: {result.confidence:.1%}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"错误 E010: {ERROR_CODES['E010']}: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
