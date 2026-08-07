#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
document-intelligence 技能实现脚本

功能：发票识别与文档智能处理
- 将用户输入转换为结构化结果
- 识别并保留关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理

本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：{发票代码: xxx, 发票号码: xxx}",
    "E004": "这超出了本工具的能力范围，建议：使用专业OCR工具或人工处理",
    "E005": "结果无法确定，建议：人工复核关键字段",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "批量处理失败，请检查每个输入项的格式",
    "E008": "输出格式不支持，仅支持 json/text",
    "E009": "输入包含无效字符或编码错误",
    "E010": "系统资源不足，请减少输入量后重试",
}

# ============================================================
# 常量定义
# ============================================================
# 置信度阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 支持的关键字段（发票常见字段）
KEY_FIELDS = [
    "invoice_code",      # 发票代码
    "invoice_number",    # 发票号码
    "invoice_date",      # 开票日期
    "seller_name",       # 销售方名称
    "buyer_name",        # 购买方名称
    "amount_total",      # 价税合计
    "tax_amount",        # 税额
    "amount_without_tax",# 不含税金额
]

# 字段正则模式（用于识别）
FIELD_PATTERNS = {
    "invoice_code": r"发票代码[：:\s]*([0-9]{10,12})",
    "invoice_number": r"发票号码[：:\s]*([0-9]{8,10})",
    "invoice_date": r"开票日期[：:\s]*([0-9]{4}[-年/][0-9]{1,2}[-月/][0-9]{1,2}日?)",
    "seller_name": r"销售方[名称]?[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()]+)",
    "buyer_name": r"购买方[名称]?[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()]+)",
    # 修正：价税合计后面可以跟"大写"或直接跟金额，也可以有括号
    "amount_total": r"价税合计[（(]?大写[）)]?[：:\s]*[¥￥]?([0-9]+\.?[0-9]*)|价税合计[：:\s]*[¥￥]?([0-9]+\.?[0-9]*)",
    "tax_amount": r"税额[：:\s]*[¥￥]?([0-9]+\.?[0-9]*)",
    "amount_without_tax": r"不含税金额[：:\s]*[¥￥]?([0-9]+\.?[0-9]*)",
}


# ============================================================
# 核心处理类
# ============================================================
class DocumentIntelligence:
    """文档智能处理主类"""

    def __init__(self) -> None:
        """初始化处理器"""
        self.error_codes = ERROR_CODES
        self.supported_fields = KEY_FIELDS

    def process_input(self, input_data: Any, output_format: str = "json") -> Dict[str, Any]:
        """
        处理输入数据，返回结构化结果

        Args:
            input_data: 输入数据（字符串或字典）
            output_format: 输出格式（json/text）

        Returns:
            处理结果字典

        Raises:
            ValueError: 当输入无效或处理失败时
        """
        # 校验输出格式
        if output_format not in ["json", "text"]:
            raise ValueError(self._get_error("E008"))

        # 校验输入
        if input_data is None or (isinstance(input_data, str) and not input_data.strip()):
            raise ValueError(self._get_error("E001"))

        # 解析输入
        parsed_data = self._parse_input(input_data)

        # 提取关键信息
        extracted = self._extract_fields(parsed_data)

        # 计算置信度
        confidence = self._calculate_confidence(extracted)

        # 生成结果
        result = self._build_result(extracted, confidence, output_format)

        return result

    def batch_process(self, inputs: List[Any], output_format: str = "json") -> List[Dict[str, Any]]:
        """
        批量处理多个输入

        Args:
            inputs: 输入列表
            output_format: 输出格式

        Returns:
            处理结果列表
        """
        if not inputs:
            raise ValueError(self._get_error("E001"))

        results = []
        for item in inputs:
            try:
                result = self.process_input(item, output_format)
                results.append(result)
            except ValueError as e:
                # 单个失败不影响整体，添加错误标记
                results.append({
                    "status": "error",
                    "error_code": str(e),
                    "message": str(e)
                })

        return results

    # --------------------------------------------------------
    # 内部方法
    # --------------------------------------------------------
    def _get_error(self, code: str) -> str:
        """获取错误信息"""
        return self.error_codes.get(code, "未知错误")

    def _parse_input(self, input_data: Any) -> str:
        """
        解析输入数据为文本字符串

        Args:
            input_data: 输入数据

        Returns:
            解析后的文本

        Raises:
            ValueError: 解析失败时
        """
        try:
            if isinstance(input_data, str):
                return input_data.strip()
            elif isinstance(input_data, dict):
                # 字典转 JSON 字符串
                return json.dumps(input_data, ensure_ascii=False)
            elif isinstance(input_data, (int, float)):
                return str(input_data)
            else:
                # 尝试转换为字符串
                return str(input_data).strip()
        except Exception:
            raise ValueError(self._get_error("E009"))

    def _extract_fields(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        从文本中提取关键字段

        Args:
            text: 输入文本

        Returns:
            字段字典，包含值和置信度
        """
        extracted = {}
        for field_key in self.supported_fields:
            pattern = FIELD_PATTERNS.get(field_key)
            if not pattern:
                continue

            match = re.search(pattern, text)
            if match:
                # 处理多个分组的情况（如价税合计的正则有两个分组）
                value = None
                for group in match.groups():
                    if group is not None:
                        value = group.strip()
                        break
                if value:
                    # 清理可能的标点
                    value = value.rstrip("，,。.;；")
                    extracted[field_key] = {
                        "value": value,
                        "confidence": 0.95,
                        "source": "regex_match"
                    }
                else:
                    extracted[field_key] = {
                        "value": None,
                        "confidence": 0.0,
                        "source": "not_found"
                    }
            else:
                extracted[field_key] = {
                    "value": None,
                    "confidence": 0.0,
                    "source": "not_found"
                }

        # 额外检查：如果文本是 JSON 格式，尝试直接解析
        if text.startswith("{"):
            try:
                json_data = json.loads(text)
                for field_key in self.supported_fields:
                    if field_key in json_data:
                        extracted[field_key] = {
                            "value": json_data[field_key],
                            "confidence": 0.98,
                            "source": "json_input"
                        }
            except json.JSONDecodeError:
                pass  # 忽略 JSON 解析失败，继续使用正则结果

        return extracted

    def _calculate_confidence(self, fields: Dict[str, Dict[str, Any]]) -> float:
        """
        计算整体置信度

        Args:
            fields: 提取的字段字典

        Returns:
            整体置信度（0-1）
        """
        if not fields:
            return 0.0

        # 统计有值的字段
        found_fields = [f for f in fields.values() if f["value"] is not None]
        if not found_fields:
            return 0.0

        # 平均置信度
        avg_confidence = sum(f["confidence"] for f in found_fields) / len(found_fields)

        # 根据字段覆盖率调整
        coverage_ratio = len(found_fields) / len(fields)
        final_confidence = avg_confidence * (0.7 + 0.3 * coverage_ratio)

        return min(final_confidence, 1.0)

    def _build_result(self, fields: Dict[str, Dict[str, Any]], 
                      confidence: float, output_format: str) -> Dict[str, Any]:
        """
        构建输出结果

        Args:
            fields: 提取的字段
            confidence: 整体置信度
            output_format: 输出格式

        Returns:
            结果字典
        """
        # 转换字段为简单字典
        field_values = {}
        for key, info in fields.items():
            field_values[key] = {
                "value": info["value"],
                "confidence": round(info["confidence"], 3)
            }

        # 判断置信度等级
        if confidence >= CONFIDENCE_HIGH:
            confidence_label = "高"
            confidence_note = "可直接使用"
        elif confidence >= CONFIDENCE_MEDIUM:
            confidence_label = "中"
            confidence_note = "建议复核"
        else:
            confidence_label = "低"
            confidence_note = "[需核实]"

        # 构建结果
        result = {
            "status": "success",
            "task_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "confidence": round(confidence, 3),
            "confidence_label": confidence_label,
            "confidence_note": confidence_note,
            "fields": field_values,
            "summary": {
                "total_fields": len(fields),
                "found_fields": sum(1 for f in fields.values() if f["value"] is not None),
                "missing_fields": [k for k, v in fields.items() if v["value"] is None]
            }
        }

        # 添加低置信度警告
        if confidence < CONFIDENCE_MEDIUM:
            result["warning"] = "识别置信度较低，请人工复核关键字段"

        # 文本格式时添加格式化文本
        if output_format == "text":
            result["formatted_text"] = self._format_as_text(result)

        return result

    def _format_as_text(self, result: Dict[str, Any]) -> str:
        """
        格式化为文本输出

        Args:
            result: 结果字典

        Returns:
            格式化文本
        """
        lines = []
        lines.append("=" * 40)
        lines.append("发票识别结果")
        lines.append("=" * 40)
        lines.append(f"置信度: {result['confidence']:.1%} ({result['confidence_label']})")
        lines.append("-" * 40)

        for key, info in result["fields"].items():
            if info["value"] is not None:
                lines.append(f"{key}: {info['value']} (置信度: {info['confidence']:.0%})")
            else:
                lines.append(f"{key}: [未识别]")

        lines.append("-" * 40)
        if result["summary"]["missing_fields"]:
            lines.append(f"缺失字段: {', '.join(result['summary']['missing_fields'])}")

        if result.get("warning"):
            lines.append(f"警告: {result['warning']}")

        lines.append("=" * 40)
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> int:
    """
    运行内置自检

    Returns:
        0 表示成功，非 0 表示失败
    """
    print("开始自检...")
    print("=" * 50)

    # 创建处理器实例
    processor = DocumentIntelligence()

    # 测试用例 1：正常发票文本
    print("\n[测试1] 正常发票文本识别")
    test_text = """
    增值税普通发票
    发票代码：123456789012
    发票号码：87654321
    开票日期：2025年06月15日
    购买方名称：测试科技有限公司
    销售方名称：示例贸易有限公司
    不含税金额：¥1000.00
    税额：¥130.00
    价税合计：¥1130.00
    """
    try:
        result = processor.process_input(test_text)
        assert result["status"] == "success", "处理状态应为成功"
        assert result["confidence"] > 0.7, "置信度应大于0.7"
        assert result["fields"]["invoice_code"]["value"] is not None, "应识别发票代码"
        assert result["fields"]["amount_total"]["value"] is not None, "应识别价税合计"
        assert result["fields"]["amount_total"]["value"] == "1130.00", "价税合计应为1130.00"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1%})")
        print(f"    价税合计: {result['fields']['amount_total']['value']}")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        print(f"    识别结果: {result.get('fields', {}).get('amount_total', '未找到')}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试用例 2：JSON 输入
    print("\n[测试2] JSON 输入处理")
    test_json = {
        "invoice_code": "1234567890",
        "invoice_number": "12345678",
        "invoice_date": "2025-01-01",
        "seller_name": "测试公司",
        "buyer_name": "客户公司",
        "amount_total": "1000.00"
    }
    try:
        result = processor.process_input(test_json)
        assert result["status"] == "success", "处理状态应为成功"
        assert result["confidence"] > 0.8, "JSON输入置信度应较高"
        assert result["fields"]["invoice_code"]["value"] == "1234567890", "发票代码应匹配"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1%})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试用例 3：空输入错误处理
    print("\n[测试3] 空输入错误处理")
    try:
        processor.process_input("")
        print("  ✗ 失败: 应抛出异常")
        return 1
    except ValueError as e:
        assert "E001" in str(e) or "请提供" in str(e), "应返回E001错误"
        print("  ✓ 通过 (正确返回E001错误)")

    # 测试用例 4：批量处理
    print("\n[测试4] 批量处理")
    batch_inputs = [
        "发票代码：111111111111 发票号码：22222222 价税合计：¥500.00",
        "发票代码：333333333333 发票号码：44444444 价税合计：¥800.00",
        ""  # 空输入应产生错误
    ]
    try:
        results = processor.batch_process(batch_inputs)
        assert len(results) == 3, "应返回3个结果"
        assert results[0]["status"] == "success", "第一个应成功"
        assert results[2]["status"] == "error", "第三个应失败"
        success_count = sum(1 for r in results if r["status"] == "success")
        assert success_count >= 2, "至少2个成功"
        print(f"  ✓ 通过 (成功: {success_count}/3)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试用例 5：文本输出格式
    print("\n[测试5] 文本输出格式")
    try:
        result = processor.process_input(test_text, output_format="text")
        assert "formatted_text" in result, "应包含格式化文本"
        assert len(result["formatted_text"]) > 50, "格式化文本应有一定长度"
        print("  ✓ 通过 (文本格式输出正常)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试用例 6：低置信度场景
    print("\n[测试6] 低置信度场景")
    low_conf_text = "这是一段无法识别的文本，没有任何发票信息"
    try:
        result = processor.process_input(low_conf_text)
        assert result["confidence"] < 0.5, "置信度应较低"
        assert result["summary"]["found_fields"] == 0, "不应识别到字段"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1%})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # 测试用例 7：错误码覆盖
    print("\n[测试7] 错误码检查")
    try:
        processor.process_input(None)
        print("  ✗ 失败: 应抛出异常")
        return 1
    except ValueError:
        print("  ✓ 通过 (E001 输入为空)")

    try:
        processor.process_input("测试文本", output_format="xml")
        print("  ✗ 失败: 应抛出异常")
        return 1
    except ValueError as e:
        assert "E008" in str(e), "应返回E008错误"
        print("  ✓ 通过 (E008 输出格式不支持)")

    # 测试用例 8：价税合计带大写
    print("\n[测试8] 价税合计带大写")
    test_text_with_capital = """
    发票代码：123456789012
    发票号码：87654321
    价税合计（大写）：壹仟壹佰叁拾元整
    价税合计：¥1130.00
    """
    try:
        result = processor.process_input(test_text_with_capital)
        assert result["fields"]["amount_total"]["value"] is not None, "应识别价税合计"
        assert result["fields"]["amount_total"]["value"] == "1130.00", "价税合计应为1130.00"
        print(f"  ✓ 通过 (价税合计: {result['fields']['amount_total']['value']})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return 1

    print("\n" + "=" * 50)
    print("所有自检通过！")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="发票识别与文档智能处理工具",
        epilog="示例: python main.py --input '发票代码：1234567890' --output json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本或JSON字符串）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，输入为JSON数组字符串"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="document-intelligence 1.0.0"
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        return run_selftest()

    # 创建处理器
    processor = DocumentIntelligence()

    # 批量处理
    if args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                print(json.dumps({"error": "批量输入必须是JSON数组"}, ensure_ascii=False))
                return 1
            results = processor.batch_process(batch_data, args.output)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except json.JSONDecodeError:
            print(json.dumps({"error": "批量输入JSON格式错误"}, ensure_ascii=False))
            return 1

    # 单条处理
    if args.input:
        try:
            result = processor.process_input(args.input, args.output)
            if args.output == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(result.get("formatted_text", json.dumps(result, ensure_ascii=False)))
            return 0
        except ValueError as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            return 1

    # 无输入参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
