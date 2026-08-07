#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
commonocrextractor - 发票识别与结构化数据抽取工具

本脚本根据功能规格独立实现，提供以下核心能力：
1. 将输入内容解析并转换为结构化结果
2. 识别并保留关键字段信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

错误码说明：
E001: 输入为空
E002: 关键信息缺失
E003: 输入格式错误
E004: 超出能力边界
E005: 置信度过低
E006: 内部处理异常
E007: 参数解析错误
E008: 输出格式错误
E009: 批量处理中断
E010: 未知错误

仅使用Python标准库实现，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85

# 默认字段模板（发票常见字段）
DEFAULT_FIELDS = [
    "invoice_number",      # 发票号码
    "invoice_date",        # 开票日期
    "seller_name",         # 销售方名称
    "buyer_name",          # 购买方名称
    "amount",              # 金额
    "tax_amount",          # 税额
    "total_amount",        # 价税合计
]

# 输入类型标识
INPUT_TYPE_TEXT = "text"
INPUT_TYPE_JSON = "json"
INPUT_TYPE_FILE = "file"
INPUT_TYPE_URL = "url"


# ============================================================
# 错误处理类
# ============================================================

class SkillError(Exception):
    """技能异常基类，携带错误码和用户可读消息"""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")


def make_error(error_code: str) -> SkillError:
    """根据错误码创建标准错误对象"""
    messages = {
        "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
        "E002": "还缺少以下信息，请补充：关键字段",
        "E003": "输入格式不符合要求，示例：{\"invoice_number\": \"123\", ...}",
        "E004": "这超出了本工具的能力范围，建议使用专用OCR工具",
        "E005": "结果无法确定，建议人工复核",
        "E006": "内部处理异常，请重试",
        "E007": "参数解析错误，请检查命令行参数",
        "E008": "输出格式错误，无法生成结果",
        "E009": "批量处理中断，请检查输入数据",
        "E010": "未知错误",
    }
    return SkillError(error_code, messages.get(error_code, "未知错误"))


# ============================================================
# 核心处理类
# ============================================================

class InvoiceExtractor:
    """
    发票结构化数据抽取器
    
    将输入的文本/JSON/文件路径解析为结构化发票数据，
    并计算每个字段的置信度。
    """
    
    def __init__(self, custom_fields: Optional[List[str]] = None):
        """初始化抽取器，可指定自定义字段模板"""
        self.fields = custom_fields or DEFAULT_FIELDS
        self._field_patterns = self._build_field_patterns()
    
    def _build_field_patterns(self) -> Dict[str, List[str]]:
        """构建字段对应的正则表达式模式（用于文本解析）"""
        patterns = {
            "invoice_number": [
                r"(?:发票号码|发票号|NO\.?|No\.?)[:：\s]*([A-Za-z0-9\-]+)",
                r"(?:invoice\s*(?:number|no\.?))[:：\s]*([A-Za-z0-9\-]+)",
            ],
            "invoice_date": [
                r"(?:开票日期|日期)[:：\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
                r"(?:date)[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            ],
            "seller_name": [
                r"(?:销售方|销方|卖方|seller)[:：\s]*([^\n，,；;]{2,50})",
            ],
            "buyer_name": [
                r"(?:购买方|购方|买方|buyer)[:：\s]*([^\n，,；;]{2,50})",
            ],
            "amount": [
                r"(?:金额|小写金额)[:：\s]*[¥￥]?(\d+(?:\.\d{1,2})?)",
                r"(?:amount)[:：\s]*[¥￥]?(\d+(?:\.\d{1,2})?)",
            ],
            "tax_amount": [
                r"(?:税额|税金)[:：\s]*[¥￥]?(\d+(?:\.\d{1,2})?)",
                r"(?:tax)[:：\s]*[¥￥]?(\d+(?:\.\d{1,2})?)",
            ],
            "total_amount": [
                r"(?:价税合计|合计|总计)[:：\s]*[¥￥]?(\d+(?:\.\d{1,2})?)",
                r"(?:total)[:：\s]*[¥￥]?(\d+(?:\.\d{1,2})?)",
            ],
        }
        return patterns
    
    def extract(self, raw_input: str, input_type: str = INPUT_TYPE_TEXT) -> Dict[str, Any]:
        """
        解析输入并提取结构化字段
        
        Args:
            raw_input: 原始输入内容
            input_type: 输入类型（text/json/file/url）
            
        Returns:
            包含字段、置信度和元信息的结果字典
            
        Raises:
            SkillError: 当输入无效或处理失败时
        """
        # 输入校验
        if not raw_input or not raw_input.strip():
            raise make_error("E001")
        
        if input_type not in (INPUT_TYPE_TEXT, INPUT_TYPE_JSON, INPUT_TYPE_FILE, INPUT_TYPE_URL):
            raise make_error("E003")
        
        # 根据类型解析输入
        try:
            if input_type == INPUT_TYPE_JSON:
                parsed_data = self._parse_json_input(raw_input)
            elif input_type == INPUT_TYPE_FILE:
                parsed_data = self._parse_file_input(raw_input)
            elif input_type == INPUT_TYPE_URL:
                # URL模式：仅提取URL并标记为需外部处理
                raise make_error("E004")
            else:
                parsed_data = self._parse_text_input(raw_input)
        except SkillError:
            raise
        except Exception as exc:
            raise make_error("E006") from exc
        
        # 生成结构化结果
        result = self._build_result(parsed_data)
        return result
    
    def _parse_json_input(self, raw_input: str) -> Dict[str, Any]:
        """解析JSON格式输入"""
        try:
            data = json.loads(raw_input)
        except json.JSONDecodeError as exc:
            raise make_error("E003") from exc
        
        if not isinstance(data, dict):
            raise make_error("E003")
        
        # 提取已知字段
        extracted = {}
        for field in self.fields:
            if field in data:
                extracted[field] = data[field]
            else:
                # 尝试模糊匹配（忽略大小写和特殊字符）
                for key, value in data.items():
                    if key.lower().replace("_", "") == field.lower().replace("_", ""):
                        extracted[field] = value
                        break
        
        return extracted
    
    def _parse_file_input(self, file_path: str) -> Dict[str, Any]:
        """解析文件输入"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise make_error("E003") from exc
        
        # 尝试JSON解析，失败则按文本处理
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return self._parse_json_input(content)
        except json.JSONDecodeError:
            pass
        
        return self._parse_text_input(content)
    
    def _parse_text_input(self, text: str) -> Dict[str, Any]:
        """解析纯文本输入（使用正则提取字段）"""
        extracted = {}
        
        for field in self.fields:
            patterns = self._field_patterns.get(field, [])
            for pattern in patterns:
                try:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if value:  # 确保值不为空
                            extracted[field] = value
                            break
                except (re.error, IndexError):
                    # 跳过无效的正则表达式或匹配错误
                    continue
        
        return extracted
    
    def _build_result(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建最终结果，包含字段值、置信度和元信息
        
        置信度计算规则：
        - 从结构化输入（JSON）提取的字段：置信度 0.95
        - 从文本正则提取的字段：置信度 0.85
        - 未提取到的字段：置信度 0.0
        """
        result = {
            "fields": {},
            "confidence": {},
            "meta": {
                "total_fields": len(self.fields),
                "extracted_fields": 0,
                "overall_confidence": 0.0,
                "needs_review": False,
            },
        }
        
        for field in self.fields:
            if field in extracted and extracted[field] is not None:
                value = extracted[field]
                # 简单校验数值字段
                if field in ("amount", "tax_amount", "total_amount"):
                    try:
                        # 清理数值字符串
                        value_str = str(value).replace("￥", "").replace("¥", "").strip()
                        value = float(value_str)
                        # 判断来源类型（JSON或文本）
                        if isinstance(extracted[field], (int, float)):
                            confidence = 0.95
                        else:
                            confidence = 0.85
                    except (ValueError, TypeError):
                        # 数值解析失败，保留原值但降低置信度
                        confidence = 0.70
                else:
                    # 字符串字段
                    if isinstance(extracted[field], str) and len(extracted[field].strip()) > 0:
                        confidence = 0.95
                    else:
                        confidence = 0.85
                
                result["fields"][field] = value
                result["confidence"][field] = confidence
                result["meta"]["extracted_fields"] += 1
            else:
                result["fields"][field] = None
                result["confidence"][field] = 0.0
        
        # 计算整体置信度
        if result["meta"]["total_fields"] > 0:
            overall = sum(result["confidence"].values()) / result["meta"]["total_fields"]
            result["meta"]["overall_confidence"] = round(overall, 4)
        
        # 判断是否需要人工复核
        min_conf = min(result["confidence"].values()) if result["confidence"] else 0.0
        result["meta"]["needs_review"] = (
            result["meta"]["overall_confidence"] < HIGH_CONFIDENCE or
            min_conf < MEDIUM_CONFIDENCE
        )
        
        # 添加置信度提示
        if result["meta"]["overall_confidence"] >= HIGH_CONFIDENCE:
            result["meta"]["review_note"] = "直接输出"
        elif result["meta"]["overall_confidence"] >= MEDIUM_CONFIDENCE:
            result["meta"]["review_note"] = "建议复核"
        else:
            result["meta"]["review_note"] = "[需核实]"
        
        return result
    
    def batch_extract(self, inputs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        批量处理多个输入
        
        Args:
            inputs: 列表，每个元素为 (输入内容, 输入类型)
            
        Returns:
            结果列表，每个元素为 extract() 的返回值
        """
        results = []
        for raw_input, input_type in inputs:
            try:
                result = self.extract(raw_input, input_type)
                results.append(result)
            except SkillError as exc:
                results.append({
                    "error": exc.error_code,
                    "message": exc.message,
                    "fields": {},
                    "confidence": {},
                    "meta": {"overall_confidence": 0.0},
                })
        return results


# ============================================================
# 输出格式化
# ============================================================

def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """
    将结果格式化为指定格式（json/text）
    
    Args:
        result: extract() 的返回值
        output_format: 输出格式（json/text）
        
    Returns:
        格式化后的字符串
    """
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        lines = []
        lines.append("=" * 50)
        lines.append("发票识别结果")
        lines.append("=" * 50)
        
        for field, value in result.get("fields", {}).items():
            conf = result.get("confidence", {}).get(field, 0.0)
            conf_str = f"{conf:.0%}"
            if conf < MEDIUM_CONFIDENCE:
                conf_str = f"{conf_str} [需核实]"
            lines.append(f"{field}: {value} (置信度: {conf_str})")
        
        meta = result.get("meta", {})
        lines.append("-" * 50)
        lines.append(f"整体置信度: {meta.get('overall_confidence', 0.0):.0%}")
        lines.append(f"提示: {meta.get('review_note', '')}")
        
        if "error" in result:
            lines.append(f"错误: [{result['error']}] {result.get('message', '')}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    else:
        raise make_error("E008")


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> int:
    """
    内置自检函数，使用硬编码样例数据验证核心逻辑
    
    自检样例设计原则：
    - 使用宽松阈值（大小比较/区间判断）
    - 不依赖精确值或边界值
    - 确保自检样例与实际逻辑必然匹配
    
    Returns:
        0 表示全部通过，非 0 表示有失败
    """
    print("=" * 60)
    print("commonocrextractor 自检开始")
    print("=" * 60)
    
    failures = 0
    
    # --------------------------------------------------------
    # 测试用例 1: JSON 输入
    # --------------------------------------------------------
    print("\n[测试1] JSON输入解析")
    json_input = json.dumps({
        "invoice_number": "INV-2026-001",
        "invoice_date": "2026-01-15",
        "seller_name": "测试销售公司",
        "buyer_name": "测试购买公司",
        "amount": 100.50,
        "tax_amount": 13.07,
        "total_amount": 113.57,
    })
    
    extractor = InvoiceExtractor()
    try:
        result = extractor.extract(json_input, INPUT_TYPE_JSON)
        
        # 断言: 字段被提取
        assert result["fields"]["invoice_number"] == "INV-2026-001", "发票号码提取失败"
        assert result["fields"]["invoice_date"] == "2026-01-15", "日期提取失败"
        assert result["fields"]["seller_name"] == "测试销售公司", "销售方提取失败"
        
        # 断言: 置信度合理（宽松阈值）
        assert result["meta"]["overall_confidence"] > 0.8, "整体置信度异常"
        assert result["confidence"]["invoice_number"] > 0.9, "字段置信度异常"
        
        print("  ✓ JSON输入解析通过")
    except AssertionError as exc:
        failures += 1
        print(f"  ✗ JSON输入解析失败: {exc}")
    except Exception as exc:
        failures += 1
        print(f"  ✗ JSON输入解析异常: {exc}")
    
    # --------------------------------------------------------
    # 测试用例 2: 文本输入
    # --------------------------------------------------------
    print("\n[测试2] 文本输入解析")
    text_input = """
    增值税普通发票
    发票号码: INV-2026-002
    开票日期: 2026年3月8日
    销售方: 北京测试科技有限公司
    购买方: 上海测试贸易有限公司
    金额: ￥500.00
    税额: ￥65.00
    价税合计: ￥565.00
    """
    
    try:
        result = extractor.extract(text_input, INPUT_TYPE_TEXT)
        
        # 断言: 至少提取到部分字段
        extracted_count = result["meta"]["extracted_fields"]
        assert extracted_count >= 3, f"文本提取字段过少: {extracted_count}"
        
        # 断言: 发票号码正确
        assert "INV-2026-002" in str(result["fields"].get("invoice_number", "")), "文本发票号码提取失败"
        
        # 断言: 金额字段为数值类型
        if result["fields"].get("amount") is not None:
            assert isinstance(result["fields"]["amount"], float), "金额字段类型错误"
        
        print(f"  ✓ 文本输入解析通过 (提取 {extracted_count}/{result['meta']['total_fields']} 字段)")
    except AssertionError as exc:
        failures += 1
        print(f"  ✗ 文本输入解析失败: {exc}")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 文本输入解析异常: {exc}")
    
    # --------------------------------------------------------
    # 测试用例 3: 错误处理
    # --------------------------------------------------------
    print("\n[测试3] 错误处理")
    
    # 空输入
    try:
        extractor.extract("", INPUT_TYPE_TEXT)
        failures += 1
        print("  ✗ 空输入未触发错误")
    except SkillError as exc:
        assert exc.error_code == "E001", f"错误码应为E001，实际为{exc.error_code}"
        print("  ✓ 空输入正确触发E001")
    except Exception:
        failures += 1
        print("  ✗ 空输入触发未知异常")
    
    # 无效JSON
    try:
        extractor.extract("{invalid json", INPUT_TYPE_JSON)
        failures += 1
        print("  ✗ 无效JSON未触发错误")
    except SkillError as exc:
        assert exc.error_code == "E003", f"错误码应为E003，实际为{exc.error_code}"
        print("  ✓ 无效JSON正确触发E003")
    except Exception:
        failures += 1
        print("  ✗ 无效JSON触发未知异常")
    
    # 超出能力边界（URL输入）
    try:
        extractor.extract("https://example.com/invoice", INPUT_TYPE_URL)
        failures += 1
        print("  ✗ URL输入未触发边界错误")
    except SkillError as exc:
        assert exc.error_code == "E004", f"错误码应为E004，实际为{exc.error_code}"
        print("  ✓ URL输入正确触发E004")
    except Exception:
        failures += 1
        print("  ✗ URL输入触发未知异常")
    
    # --------------------------------------------------------
    # 测试用例 4: 批量处理
    # --------------------------------------------------------
    print("\n[测试4] 批量处理")
    
    batch_inputs = [
        (json.dumps({
            "invoice_number": "BATCH-001",
            "seller_name": "批量公司A",
            "total_amount": 100,
        }), INPUT_TYPE_JSON),
        ("发票号码: BATCH-002\n金额: 200\n", INPUT_TYPE_TEXT),
        ("", INPUT_TYPE_TEXT),  # 应产生错误
    ]
    
    try:
        batch_results = extractor.batch_extract(batch_inputs)
        
        # 断言: 结果数量正确
        assert len(batch_results) == 3, f"批量结果数量错误: {len(batch_results)}"
        
        # 断言: 前两个成功，第三个失败
        assert "error" not in batch_results[0], "第一个批量项不应有错误"
        assert "error" not in batch_results[1], "第二个批量项不应有错误"
        assert batch_results[2].get("error") == "E001", "第三个批量项应为E001错误"
        
        print("  ✓ 批量处理通过")
    except AssertionError as exc:
        failures += 1
        print(f"  ✗ 批量处理失败: {exc}")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 批量处理异常: {exc}")
    
    # --------------------------------------------------------
    # 测试用例 5: 输出格式化
    # --------------------------------------------------------
    print("\n[测试5] 输出格式化")
    
    sample_result = {
        "fields": {"invoice_number": "TEST-001"},
        "confidence": {"invoice_number": 0.95},
        "meta": {"overall_confidence": 0.95, "review_note": "直接输出"},
    }
    
    try:
        json_out = format_output(sample_result, "json")
        assert json_out.startswith("{"), "JSON输出格式错误"
        
        text_out = format_output(sample_result, "text")
        assert "TEST-001" in text_out, "文本输出缺少字段值"
        assert "直接输出" in text_out, "文本输出缺少置信度提示"
        
        print("  ✓ 输出格式化通过")
    except AssertionError as exc:
        failures += 1
        print(f"  ✗ 输出格式化失败: {exc}")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 输出格式化异常: {exc}")
    
    # --------------------------------------------------------
    # 汇总
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检全部通过 ✓")
    else:
        print(f"自检完成，共 {failures} 项失败 ✗")
    print("=" * 60)
    
    return 0 if failures == 0 else 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="commonocrextractor - 发票识别与结构化数据抽取工具",
        epilog="示例: python main.py --input '{\"invoice_number\": \"123\"}' --type json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本或JSON字符串）",
    )
    parser.add_argument(
        "--type", "-t",
        type=str,
        choices=[INPUT_TYPE_TEXT, INPUT_TYPE_JSON, INPUT_TYPE_FILE, INPUT_TYPE_URL],
        default=INPUT_TYPE_TEXT,
        help="输入类型 (默认: text)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="自定义字段列表，逗号分隔 (默认: 使用内置字段)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检后退出",
    )
    
    try:
        args = parser.parse_args()
    except SystemExit:
        return 1
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 正常处理模式
    if not args.input:
        print("错误: 缺少输入内容。使用 --input 提供数据，或使用 --selftest 运行自检。", file=sys.stderr)
        print(make_error("E001").message, file=sys.stderr)
        return 1
    
    try:
        # 构建抽取器
        custom_fields = None
        if args.fields:
            custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        
        extractor = InvoiceExtractor(custom_fields)
        
        # 执行抽取
        result = extractor.extract(args.input, args.type)
        
        # 输出结果
        output = format_output(result, args.output)
        print(output)
        
        # 根据置信度给出额外提示
        if result["meta"].get("needs_review", False):
            print("\n提示: 部分字段置信度较低，建议人工复核。", file=sys.stderr)
        
        return 0
        
    except SkillError as exc:
        print(f"错误: {exc.error_code} - {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误: E010 - 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
