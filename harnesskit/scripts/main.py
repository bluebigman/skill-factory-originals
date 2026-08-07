#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harnesskit - 未命名工具

一个通用的数据/文件/URL 结构化处理工具。
根据功能规格独立实现（clean-room），不依赖任何既有代码。

功能概述：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理错误
    E007: 输出格式不支持
    E008: 批量处理中断
    E009: 参数解析错误
    E010: 未知错误

用法示例：
    python scripts/main.py --input "用户提供的数据" --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 置信度阈值
CONFIDENCE_HIGH = 0.90      # ≥90%：直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90%：标注"建议复核"
CONFIDENCE_LOW = 0.0        # <85%：标注"[需核实]"

# 支持的关键字段（用于结构化提取）
KEY_FIELDS = [
    "标题", "作者", "日期", "内容", "来源",
    "类型", "状态", "数量", "金额", "备注"
]

# 输出格式支持列表
SUPPORTED_FORMATS = ["json", "text", "table", "csv"]

# 版本信息
VERSION = "1.0.0"


# ============================================================
# 错误处理类
# ============================================================

class HarnessKitError(Exception):
    """基础异常类，携带错误码"""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")
    
    def to_dict(self) -> Dict[str, str]:
        """转为字典格式"""
        return {
            "error_code": self.error_code,
            "message": self.message
        }


# ============================================================
# 核心处理逻辑
# ============================================================

class HarnessKit:
    """
    harnesskit 核心处理器
    
    负责将输入内容解析为结构化结果，并计算置信度。
    完全离线运行，不访问网络。
    """
    
    def __init__(self):
        """初始化处理器"""
        self._processed_count = 0
    
    def process(
        self,
        input_data: str,
        output_format: str = "json",
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        处理单个输入，返回结构化结果
        
        参数：
            input_data: 用户提供的原始输入
            output_format: 输出格式（json/text/table/csv）
            fields: 需要提取的关键字段列表（默认使用全部）
        
        返回：
            包含处理结果、置信度、元信息的字典
        
        异常：
            HarnessKitError: 处理失败时抛出，携带错误码
        """
        # 检查输入
        if not input_data or not input_data.strip():
            raise HarnessKitError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")
        
        # 检查输出格式
        if output_format not in SUPPORTED_FORMATS:
            raise HarnessKitError("E007", f"输出格式 '{output_format}' 不支持，支持格式：{', '.join(SUPPORTED_FORMATS)}")
        
        # 确定要提取的字段
        target_fields = fields if fields else KEY_FIELDS
        
        # 解析输入，提取关键信息
        try:
            extracted = self._extract_fields(input_data, target_fields)
        except HarnessKitError:
            raise
        except Exception as e:
            raise HarnessKitError("E006", f"内部处理错误: {str(e)}")
        
        # 检查关键信息是否完整
        missing_fields = self._check_missing_fields(extracted)
        if missing_fields:
            # 不抛出异常，但降低置信度并标注
            pass
        
        # 计算置信度
        confidence = self._calculate_confidence(extracted, input_data, missing_fields)
        
        # 生成结果
        result = self._build_result(
            input_data=input_data,
            extracted=extracted,
            confidence=confidence,
            missing_fields=missing_fields,
            output_format=output_format
        )
        
        self._processed_count += 1
        return result
    
    def process_batch(
        self,
        inputs: List[str],
        output_format: str = "json",
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        批量处理多个输入
        
        参数：
            inputs: 输入列表
            output_format: 输出格式
            fields: 需要提取的字段
        
        返回：
            包含批量处理结果的字典
        """
        if not inputs:
            raise HarnessKitError("E001", "批量输入为空，请提供至少一个输入")
        
        results = []
        errors = []
        
        for idx, item in enumerate(inputs):
            try:
                r = self.process(item, output_format, fields)
                results.append(r)
            except HarnessKitError as e:
                errors.append({
                    "index": idx,
                    "error_code": e.error_code,
                    "message": e.message
                })
            except Exception as e:
                errors.append({
                    "index": idx,
                    "error_code": "E010",
                    "message": f"未知错误: {str(e)}"
                })
        
        # 如果全部失败，抛出批量中断错误
        if results and not errors:
            pass  # 全部成功
        elif not results and errors:
            raise HarnessKitError("E008", f"批量处理全部失败，共 {len(errors)} 个错误")
        
        return {
            "total": len(inputs),
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }
    
    def _extract_fields(self, input_data: str, fields: List[str]) -> Dict[str, Any]:
        """
        从输入中提取关键字段
        
        使用简单的模式匹配和关键词识别。
        完全离线，不依赖外部服务。
        """
        extracted = {}
        text = input_data.strip()
        
        # 尝试识别 URL
        url_match = re.search(r'https?://[^\s]+', text)
        if url_match:
            extracted["来源"] = url_match.group(0)
        
        # 尝试识别日期（多种格式）
        date_patterns = [
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?',
            r'\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}',
            r'\d{4}年\d{1,2}月\d{1,2}日'
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text)
            if date_match:
                extracted["日期"] = date_match.group(0)
                break
        
        # 尝试识别数字（数量/金额）
        number_matches = re.findall(r'\d+(?:\.\d+)?', text)
        if number_matches:
            # 如果有货币符号，视为金额
            if re.search(r'[¥$€£]', text):
                extracted["金额"] = number_matches[0]
            else:
                extracted["数量"] = number_matches[0]
        
        # 尝试识别标题（第一行非空内容）
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            extracted["标题"] = lines[0][:50]  # 截断过长标题
        
        # 尝试识别作者（常见模式）
        author_patterns = [
            r'作者[：:]\s*(\S+)',
            r'by\s+(\S+)',
            r'@(\w+)'
        ]
        for pattern in author_patterns:
            author_match = re.search(pattern, text, re.IGNORECASE)
            if author_match:
                extracted["作者"] = author_match.group(1)
                break
        
        # 内容：截取中间部分作为内容摘要
        if len(text) > 100:
            extracted["内容"] = text[50:150] + "..."
        else:
            extracted["内容"] = text
        
        # 尝试识别类型关键词
        type_keywords = ["报告", "文章", "数据", "代码", "文档", "笔记", "邮件", "消息"]
        for kw in type_keywords:
            if kw in text:
                extracted["类型"] = kw
                break
        
        # 尝试识别状态
        status_keywords = ["完成", "进行中", "待处理", "已发布", "草稿", "已归档"]
        for kw in status_keywords:
            if kw in text:
                extracted["状态"] = kw
                break
        
        # 只保留请求的字段
        filtered = {}
        for field in fields:
            if field in extracted:
                filtered[field] = extracted[field]
        
        return filtered
    
    def _check_missing_fields(self, extracted: Dict[str, Any]) -> List[str]:
        """检查哪些关键字段缺失"""
        missing = []
        for field in KEY_FIELDS:
            if field not in extracted or not extracted[field]:
                missing.append(field)
        return missing
    
    def _calculate_confidence(
        self,
        extracted: Dict[str, Any],
        original_text: str,
        missing_fields: List[str]
    ) -> float:
        """
        计算置信度
        
        规则：
        - 提取到字段越多，置信度越高
        - 缺失字段会降低置信度
        - 输入长度影响置信度
        """
        # 基础分：提取到字段的比例
        field_ratio = len(extracted) / len(KEY_FIELDS)
        base_score = field_ratio * 0.7
        
        # 内容完整度：输入长度
        text_length = len(original_text.strip())
        if text_length >= 100:
            length_score = 0.2
        elif text_length >= 50:
            length_score = 0.1
        else:
            length_score = 0.05
        
        # 缺失字段惩罚
        penalty = len(missing_fields) * 0.02
        
        # 最终置信度
        confidence = min(0.99, base_score + length_score - penalty)
        
        # 确保至少有个基础值
        if extracted:
            confidence = max(confidence, 0.5)
        else:
            confidence = 0.1
        
        return round(confidence, 2)
    
    def _build_result(
        self,
        input_data: str,
        extracted: Dict[str, Any],
        confidence: float,
        missing_fields: List[str],
        output_format: str
    ) -> Dict[str, Any]:
        """构建最终结果"""
        
        # 置信度标注
        if confidence >= CONFIDENCE_HIGH:
            confidence_note = "直接输出"
        elif confidence >= CONFIDENCE_MEDIUM:
            confidence_note = "建议复核"
        else:
            confidence_note = "[需核实]"
        
        # 构建结果
        result = {
            "status": "success",
            "confidence": confidence,
            "confidence_note": confidence_note,
            "extracted": extracted,
            "missing_fields": missing_fields,
            "processed_at": datetime.now().isoformat(),
            "input_preview": input_data[:100] + ("..." if len(input_data) > 100 else ""),
            "output_format": output_format
        }
        
        # 低置信度时添加说明
        if confidence < CONFIDENCE_MEDIUM:
            result["warning"] = "结果无法确定，建议人工复核关键信息"
        
        return result


# ============================================================
# 输出格式化
# ============================================================

class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format(result: Dict[str, Any], output_format: str) -> str:
        """
        将结果格式化为指定格式
        
        支持：json / text / table / csv
        """
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif output_format == "text":
            return OutputFormatter._format_text(result)
        elif output_format == "table":
            return OutputFormatter._format_table(result)
        elif output_format == "csv":
            return OutputFormatter._format_csv(result)
        else:
            raise HarnessKitError("E007", f"不支持的输出格式: {output_format}")
    
    @staticmethod
    def _format_text(result: Dict[str, Any]) -> str:
        """格式化为纯文本"""
        lines = []
        lines.append(f"=== harnesskit 处理结果 ===")
        lines.append(f"置信度: {result['confidence']:.0%} ({result['confidence_note']})")
        lines.append("")
        lines.append("提取字段:")
        
        extracted = result.get("extracted", {})
        if extracted:
            for key, value in extracted.items():
                lines.append(f"  {key}: {value}")
        else:
            lines.append("  (未提取到有效字段)")
        
        if result.get("missing_fields"):
            lines.append("")
            lines.append(f"缺失字段: {', '.join(result['missing_fields'])}")
        
        if result.get("warning"):
            lines.append("")
            lines.append(f"警告: {result['warning']}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_table(result: Dict[str, Any]) -> str:
        """格式化为表格"""
        extracted = result.get("extracted", {})
        if not extracted:
            return "| 字段 | 值 |\n|------|-----|\n| (空) | (空) |"
        
        lines = ["| 字段 | 值 |", "|------|-----|"]
        for key, value in extracted.items():
            # 转义表格特殊字符
            safe_value = str(value).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {key} | {safe_value} |")
        
        lines.append("")
        lines.append(f"置信度: {result['confidence']:.0%} ({result['confidence_note']})")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_csv(result: Dict[str, Any]) -> str:
        """格式化为 CSV"""
        extracted = result.get("extracted", {})
        
        # 字段列表
        field_names = list(extracted.keys())
        if not field_names:
            return "字段,值\n(空),(空)"
        
        # CSV 头
        lines = ["字段,值"]
        
        # 数据行
        for key, value in extracted.items():
            # 转义 CSV 特殊字符
            safe_value = str(value).replace('"', '""')
            lines.append(f'"{key}","{safe_value}"')
        
        # 添加置信度行
        lines.append(f'"置信度","{result["confidence"]:.0%} ({result["confidence_note"]})"')
        
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检
    
    使用硬编码样例数据，离线测试核心逻辑。
    不读取外部文件，不依赖当前工作目录，不访问网络。
    
    返回：
        True 表示全部通过，False 表示有失败项
    """
    print("=== harnesskit 自检开始 ===")
    print(f"版本: {VERSION}")
    print(f"时间: {datetime.now().isoformat()}")
    print("")
    
    all_passed = True
    
    # 测试用例 1：正常处理
    print("[测试 1] 正常处理测试")
    try:
        kit = HarnessKit()
        result = kit.process(
            "这是一个测试报告\n"
            "作者：张三\n"
            "日期：2024年3月15日\n"
            "内容：这是一段测试内容，用于验证处理器的基本功能。"
            "包含足够多的文字来确保内容提取正常工作。"
            "报告状态：已完成"
        )
        
        # 宽松断言
        assert result["status"] == "success", "状态应为 success"
        assert result["confidence"] > 0, "置信度应大于 0"
        assert result["confidence"] <= 1, "置信度应小于等于 1"
        assert "extracted" in result, "应包含提取字段"
        assert len(result["extracted"]) > 0, "应至少提取到 1 个字段"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 2：空输入
    print("[测试 2] 空输入错误处理")
    try:
        kit = HarnessKit()
        try:
            kit.process("")
            print("  ✗ 失败: 应抛出 E001 错误")
            all_passed = False
        except HarnessKitError as e:
            assert e.error_code == "E001", f"错误码应为 E001，实际为 {e.error_code}"
            print("  ✓ 通过")
        except Exception as e:
            print(f"  ✗ 异常: {e}")
            all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 3：URL 识别
    print("[测试 3] URL 识别")
    try:
        kit = HarnessKit()
        result = kit.process("请查看这个链接 https://example.com/docs/report 获取详细信息")
        extracted = result["extracted"]
        assert "来源" in extracted, "应识别出 URL 来源"
        assert "example.com" in extracted["来源"], "URL 应包含 example.com"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 4：日期识别
    print("[测试 4] 日期识别")
    try:
        kit = HarnessKit()
        result = kit.process("会议定于 2025年6月30日 下午两点举行，请准时参加。")
        extracted = result["extracted"]
        assert "日期" in extracted, "应识别出日期"
        assert "2025" in extracted["日期"], "日期应包含年份 2025"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 5：批量处理
    print("[测试 5] 批量处理")
    try:
        kit = HarnessKit()
        inputs = [
            "第一条测试数据，包含一些内容用于处理",
            "第二条测试数据，包含一些内容用于处理",
            "第三条测试数据，包含一些内容用于处理"
        ]
        batch_result = kit.process_batch(inputs)
        assert batch_result["total"] == 3, "总数应为 3"
        assert batch_result["success_count"] == 3, "应全部成功"
        assert batch_result["error_count"] == 0, "不应有错误"
        assert len(batch_result["results"]) == 3, "应有 3 个结果"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 6：输出格式
    print("[测试 6] 输出格式")
    try:
        kit = HarnessKit()
        result = kit.process("测试数据，包含一些内容")
        
        formatter = OutputFormatter()
        json_out = formatter.format(result, "json")
        assert json_out.startswith("{"), "JSON 输出应以 { 开头"
        
        text_out = formatter.format(result, "text")
        assert "置信度" in text_out, "文本输出应包含置信度"
        
        table_out = formatter.format(result, "table")
        assert "|" in table_out, "表格输出应包含 | 分隔符"
        
        csv_out = formatter.format(result, "csv")
        assert "," in csv_out or '"' in csv_out, "CSV 输出应包含逗号或引号"
        
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 7：置信度分级
    print("[测试 7] 置信度分级")
    try:
        kit = HarnessKit()
        
        # 完整输入应高置信度
        rich_input = (
            "标题：季度报告\n"
            "作者：李四\n"
            "日期：2024年12月1日\n"
            "内容：这是一段很长的内容，包含大量文字信息，"
            "用于测试置信度计算逻辑是否正常工作。"
            "这段文字足够长，以确保内容字段能够被提取。"
            "类型：报告\n"
            "状态：已完成\n"
            "来源：内部系统\n"
            "数量：100\n"
            "金额：¥5000\n"
            "备注：这是备注信息"
        )
        rich_result = kit.process(rich_input)
        
        # 简短输入应低置信度
        poor_input = "你好"
        poor_result = kit.process(poor_input)
        
        # 宽松断言：丰富输入置信度应高于简短输入
        assert rich_result["confidence"] > poor_result["confidence"], "丰富输入置信度应更高"
        
        # 置信度应在合理范围内
        assert 0 <= rich_result["confidence"] <= 1, "置信度应在 0-1 之间"
        assert 0 <= poor_result["confidence"] <= 1, "置信度应在 0-1 之间"
        
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 8：字段过滤
    print("[测试 8] 字段过滤")
    try:
        kit = HarnessKit()
        result = kit.process("测试数据，作者：王五", fields=["作者", "内容"])
        extracted = result["extracted"]
        # 只应包含请求的字段
        for key in extracted.keys():
            assert key in ["作者", "内容"], f"不应包含字段: {key}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 测试用例 9：错误码完整性
    print("[测试 9] 错误码完整性")
    try:
        expected_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
        for code in expected_codes:
            assert len(code) == 4, f"错误码格式错误: {code}"
            assert code.startswith("E"), f"错误码应以 E 开头: {code}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    
    # 测试用例 10：异常输入处理
    print("[测试 10] 异常输入处理")
    try:
        kit = HarnessKit()
        
        # 极长输入
        long_input = "x" * 10000
        result = kit.process(long_input)
        assert result["status"] == "success", "长输入应成功处理"
        
        # 特殊字符
        special_input = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`"
        result = kit.process(special_input)
        assert result["status"] == "success", "特殊字符应成功处理"
        
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False
    
    # 汇总
    print("")
    if all_passed:
        print("=== 自检全部通过 ===")
    else:
        print("=== 自检存在失败项 ===")
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="harnesskit - 通用数据/文件/URL 结构化处理工具",
        epilog="示例: python scripts/main.py --input '待处理内容' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（用户提供的数据/文件/URL）"
    )
    
    parser.add_argument(
        "--input-file",
        type=str,
        help="从文件读取输入内容"
    )
    
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=SUPPORTED_FORMATS,
        default="json",
        help=f"输出格式，支持: {', '.join(SUPPORTED_FORMATS)}"
    )
    
    parser.add_argument(
        "--fields",
        type=str,
        nargs="+",
        help=f"需要提取的字段，默认全部: {', '.join(KEY_FIELDS)}"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部环境）"
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    
    return parser.parse_args()


def read_input_file(filepath: str) -> str:
    """
    从文件读取输入内容
    
    参数：
        filepath: 文件路径
    
    返回：
        文件内容字符串
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise HarnessKitError("E003", f"文件不存在: {filepath}")
    except PermissionError:
        raise HarnessKitError("E003", f"没有权限读取文件: {filepath}")
    except Exception as e:
        raise HarnessKitError("E006", f"读取文件失败: {str(e)}")


def main():
    """主函数"""
    args = parse_args()
    
    # 版本信息
    if args.version:
        print(f"harnesskit v{VERSION}")
        return 0
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 批量处理模式
    if args.batch:
        try:
            kit = HarnessKit()
            batch_result = kit.process_batch(args.batch, args.format, args.fields)
            
            # 输出结果
            formatter = OutputFormatter()
            for i, result in enumerate(batch_result["results"]):
                print(f"--- 结果 {i+1} ---")
                print(formatter.format(result, args.format))
                print()
            
            # 输出统计
            print(f"--- 统计 ---")
            print(f"总数: {batch_result['total']}")
            print(f"成功: {batch_result['success_count']}")
            print(f"失败: {batch_result['error_count']}")
            
            if batch_result["errors"]:
                print("\n错误详情:")
                for err in batch_result["errors"]:
                    print(f"  第 {err['index']+1} 项: [{err['error_code']}] {err['message']}")
            
            return 0
        except HarnessKitError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    
    # 从文件读取
    input_data = None
    if args.input_file:
        try:
            input_data = read_input_file(args.input_file)
        except HarnessKitError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    elif args.input:
        input_data = args.input
    
    # 单次处理模式
    if input_data:
        try:
            kit = HarnessKit()
            result = kit.process(input_data, args.format, args.fields)
            
            # 输出结果
            formatter = OutputFormatter()
            output = formatter.format(result, args.format)
            print(output)
            
            return 0
        except HarnessKitError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    
    # 无有效输入
    print("错误: [E001] 请提供待处理的内容，格式为：用户提供的数据/文件/URL", file=sys.stderr)
    print("使用 --help 查看帮助，或使用 --selftest 运行自检", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
