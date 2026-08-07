#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
合同审查助手 - Ally Legal Assistant 独立实现
基于功能规格 clean-room 重写，不依赖任何既有代码。
仅使用标准库，支持离线自检。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码常量（规格 E001-E005，扩展至 E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：请提供文本、JSON 或 URL",
    "E004": "这超出了本工具的能力范围，建议咨询专业人士或使用其他工具",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "置信度计算失败，请检查输入数据",
    "E008": "输出格式不支持，请选择：text / json",
    "E009": "批量处理时某个条目失败，已跳过该条目",
    "E010": "未知错误，请联系维护人员",
}


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class ContractItem:
    """合同关键信息条目"""
    field_name: str          # 字段名称
    value: str               # 提取的值
    confidence: float        # 置信度 0-100
    source: str = "input"    # 来源标记
    note: str = ""           # 备注（如"建议复核"）


@dataclass
class ParseResult:
    """解析结果"""
    items: List[ContractItem] = field(default_factory=list)
    raw_text: str = ""
    status: str = "ok"       # ok / warning / error
    error_code: str = ""
    message: str = ""


@dataclass
class OutputResult:
    """最终输出"""
    status: str = "ok"
    error_code: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    confidence_avg: float = 0.0


# ============================================================
# 核心逻辑类
# ============================================================
class ContractAnalyzer:
    """
    合同分析器 - 核心逻辑
    根据规格实现：解析输入、识别关键信息、计算置信度、生成输出
    """

    # 常见合同关键字段（用于识别）
    KEY_FIELDS = [
        "合同编号", "合同名称", "甲方", "乙方", "签订日期",
        "生效日期", "终止日期", "金额", "币种", "付款方式",
        "违约责任", "争议解决", "保密条款", "知识产权",
    ]

    # 字段别名映射（用于更鲁棒的识别）
    FIELD_ALIASES = {
        "合同编号": ["编号", "合同号", "NO", "NO."],
        "合同名称": ["名称", "标题", "合同标题"],
        "甲方": ["委托方", "买方", "采购方", "客户"],
        "乙方": ["受托方", "卖方", "供应商", "服务方"],
        "签订日期": ["签署日期", "签订时间", "日期"],
        "生效日期": ["生效时间", "开始日期"],
        "终止日期": ["结束日期", "到期日", "失效日期"],
        "金额": ["总金额", "合同金额", "价款", "费用", "价格"],
        "币种": ["货币", "货币单位"],
        "付款方式": ["支付方式", "结算方式"],
        "违约责任": ["违约条款", "赔偿条款"],
        "争议解决": ["争议处理", "仲裁", "诉讼管辖"],
        "保密条款": ["保密义务", "保密协议"],
        "知识产权": ["IP", "版权", "专利"],
    }

    # 需要数值验证的字段
    NUMERIC_FIELDS = ["金额"]

    def __init__(self) -> None:
        """初始化分析器"""
        self.debug_mode = False

    # ---------- 输入处理 ----------
    def parse_input(self, raw_input: str) -> ParseResult:
        """
        解析输入内容，识别关键信息
        支持：纯文本、JSON 字符串、简单键值对
        """
        result = ParseResult(raw_text=raw_input)

        # 空输入检查
        if not raw_input or not raw_input.strip():
            result.status = "error"
            result.error_code = "E001"
            result.message = ERROR_CODES["E001"]
            return result

        # 尝试 JSON 解析
        json_data = self._try_parse_json(raw_input)
        if json_data is not None:
            self._parse_json_data(json_data, result)
        else:
            # 尝试键值对解析
            kv_items = self._try_parse_key_value(raw_input)
            if kv_items:
                for k, v in kv_items:
                    self._add_item(result, k, v)
            else:
                # 纯文本解析
                self._parse_plain_text(raw_input, result)

        # 检查关键信息是否足够
        if result.status != "error":
            self._check_completeness(result)

        return result

    def _try_parse_json(self, text: str) -> Optional[Any]:
        """尝试解析 JSON 输入"""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None

    def _parse_json_data(self, data: Any, result: ParseResult) -> None:
        """解析 JSON 数据"""
        try:
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, (str, int, float)):
                        self._add_item(result, str(key), str(value))
                    elif isinstance(value, dict):
                        # 嵌套对象展平
                        for sub_key, sub_val in value.items():
                            if isinstance(sub_val, (str, int, float)):
                                self._add_item(result, f"{key}.{sub_key}", str(sub_val))
            elif isinstance(data, list):
                for idx, item in enumerate(data):
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if isinstance(value, (str, int, float)):
                                self._add_item(result, f"[{idx}].{key}", str(value))
            else:
                # 普通值
                self._add_item(result, "value", str(data))
        except Exception:
            result.status = "error"
            result.error_code = "E006"
            result.message = ERROR_CODES["E006"]

    def _try_parse_key_value(self, text: str) -> List[Tuple[str, str]]:
        """尝试解析键值对格式（如 'key: value' 或 'key=value'）"""
        items = []
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 支持冒号和等号
            for sep in [":", "：", "="]:
                if sep in line:
                    parts = line.split(sep, 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        items.append((key, value))
                    break
        return items

    def _parse_plain_text(self, text: str, result: ParseResult) -> None:
        """解析纯文本，尝试识别关键字段"""
        # 按行处理
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试匹配 "字段名：值" 模式
            for field_name in self.KEY_FIELDS:
                pattern = re.compile(
                    rf"{re.escape(field_name)}\s*[:：]\s*(.+)"
                )
                match = pattern.search(line)
                if match:
                    self._add_item(result, field_name, match.group(1).strip())
                    break

            # 尝试匹配别名
            if not any(item.field_name == field_name for item in result.items):
                for std_name, aliases in self.FIELD_ALIASES.items():
                    for alias in aliases:
                        pattern = re.compile(
                            rf"{re.escape(alias)}\s*[:：]\s*(.+)"
                        )
                        match = pattern.search(line)
                        if match:
                            self._add_item(result, std_name, match.group(1).strip())
                            break
                    else:
                        continue
                    break

        # 如果没有任何识别结果，将整段作为描述
        if not result.items:
            self._add_item(result, "描述", text[:200], confidence=50.0,
                          note="[需核实] 未识别到结构化字段")

    # ---------- 信息处理 ----------
    def _add_item(self, result: ParseResult, field_name: str, value: str,
                 confidence: Optional[float] = None, note: str = "") -> None:
        """添加一个识别项，自动计算置信度"""
        if confidence is None:
            confidence = self._calc_confidence(field_name, value)

        # 根据置信度添加备注
        if not note:
            if confidence >= 90:
                note = ""
            elif confidence >= 85:
                note = "建议复核"
            else:
                note = "[需核实]"

        item = ContractItem(
            field_name=field_name,
            value=value,
            confidence=round(confidence, 1),
            note=note
        )
        result.items.append(item)

    def _calc_confidence(self, field_name: str, value: str) -> float:
        """
        计算置信度（0-100）
        规则：
        - 字段名完全匹配 KEY_FIELDS：基础 85
        - 值非空且长度合理：+5~10
        - 数值字段能解析为数字：+5
        - 日期字段格式正确：+5
        - 否则降低
        """
        confidence = 50.0

        # 字段名匹配加分
        if field_name in self.KEY_FIELDS:
            confidence += 35
        else:
            # 检查是否匹配别名
            for std_name, aliases in self.FIELD_ALIASES.items():
                if field_name in aliases or field_name == std_name:
                    confidence += 30
                    break

        # 值非空加分
        if value and value.strip():
            confidence += 10
            # 长度合理加分（2-100字符）
            if 2 <= len(value.strip()) <= 100:
                confidence += 5

        # 数值字段验证
        if field_name in self.NUMERIC_FIELDS:
            numeric_str = re.sub(r"[^\d.]", "", value)
            try:
                float(numeric_str)
                confidence += 5
            except ValueError:
                confidence -= 10

        # 日期格式验证
        if "日期" in field_name or "时间" in field_name:
            date_pattern = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
            if re.search(date_pattern, value):
                confidence += 5

        # 限制范围
        return max(0.0, min(100.0, confidence))

    def _check_completeness(self, result: ParseResult) -> None:
        """检查关键信息完整性"""
        if not result.items:
            result.status = "error"
            result.error_code = "E002"
            result.message = ERROR_CODES["E002"]
            return

        # 检查是否有甲方和乙方（合同必备）
        field_names = [item.field_name for item in result.items]
        has_party_a = any("甲方" in f or "委托方" in f for f in field_names)
        has_party_b = any("乙方" in f or "受托方" in f for f in field_names)

        if not (has_party_a and has_party_b):
            result.status = "warning"
            result.message = "缺少甲方或乙方信息，结果可能不完整"

    # ---------- 输出生成 ----------
    def generate_output(self, parse_result: ParseResult, output_format: str = "text") -> OutputResult:
        """根据解析结果生成输出"""
        output = OutputResult()

        # 检查解析状态
        if parse_result.status == "error":
            output.status = "error"
            output.error_code = parse_result.error_code
            output.message = parse_result.message
            return output

        # 计算平均置信度
        if parse_result.items:
            output.confidence_avg = round(
                sum(item.confidence for item in parse_result.items) / len(parse_result.items),
                1
            )
        else:
            output.confidence_avg = 0.0

        # 构建数据
        output.data = {
            "items": [asdict(item) for item in parse_result.items],
            "avg_confidence": output.confidence_avg,
            "status": parse_result.status,
            "warning": parse_result.message if parse_result.status == "warning" else "",
        }

        # 根据格式生成
        if output_format == "json":
            output.message = json.dumps(output.data, ensure_ascii=False, indent=2)
        elif output_format == "text":
            output.message = self._format_text_output(output.data)
        else:
            output.status = "error"
            output.error_code = "E008"
            output.message = ERROR_CODES["E008"]
            return output

        # 检查置信度
        if output.confidence_avg < 85:
            output.status = "warning"
            output.error_code = "E005"
            if not output.message:
                output.message = ERROR_CODES["E005"]

        return output

    def _format_text_output(self, data: Dict[str, Any]) -> str:
        """格式化文本输出"""
        lines = []
        lines.append("=" * 50)
        lines.append("合同审查结果")
        lines.append("=" * 50)

        for item in data.get("items", []):
            field_name = item.get("field_name", "")
            value = item.get("value", "")
            confidence = item.get("confidence", 0)
            note = item.get("note", "")

            line = f"  {field_name}: {value}"
            if note:
                line += f" ({note})"
            line += f" [置信度: {confidence}%]"
            lines.append(line)

        lines.append("-" * 50)
        lines.append(f"平均置信度: {data.get('avg_confidence', 0)}%")

        if data.get("warning"):
            lines.append(f"警告: {data['warning']}")

        if data.get("status") == "warning":
            lines.append("提示: 部分字段置信度较低，建议人工复核")

        lines.append("=" * 50)
        return "\n".join(lines)

    # ---------- 批量处理 ----------
    def batch_process(self, inputs: List[str], output_format: str = "text") -> List[OutputResult]:
        """批量处理多个输入"""
        results = []
        for idx, input_text in enumerate(inputs):
            try:
                parse_result = self.parse_input(input_text)
                output = self.generate_output(parse_result, output_format)
                results.append(output)
            except Exception as e:
                # 单个失败不影响其他
                results.append(OutputResult(
                    status="error",
                    error_code="E009",
                    message=f"{ERROR_CODES['E009']} 错误详情: {str(e)}"
                ))
        return results


# ============================================================
# 内置自检数据（硬编码，不依赖外部文件）
# ============================================================
SELFTEST_SAMPLES = [
    # 完整合同文本
    {
        "input": """合同编号：HT-2024-001
合同名称：软件开发服务合同
甲方：北京科技有限公司
乙方：上海信息科技有限公司
签订日期：2024-01-15
生效日期：2024-02-01
终止日期：2025-01-31
金额：500,000元
币种：人民币
付款方式：分三期支付
违约责任：违约方需支付合同总额10%的违约金
争议解决：提交北京仲裁委员会仲裁
保密条款：双方对合同内容负有保密义务
知识产权：软件著作权归甲方所有""",
        "expected_fields": ["合同编号", "合同名称", "甲方", "乙方", "金额"]
    },
    # 部分信息合同
    {
        "input": """甲方：测试公司
乙方：合作公司
金额：10000元""",
        "expected_fields": ["甲方", "乙方", "金额"]
    },
    # JSON 格式输入
    {
        "input": json.dumps({
            "合同编号": "J-2024-002",
            "合同名称": "采购合同",
            "甲方": "采购方A",
            "乙方": "供应商B",
            "金额": 200000,
            "币种": "CNY"
        }, ensure_ascii=False),
        "expected_fields": ["合同编号", "合同名称", "甲方", "乙方", "金额"]
    },
    # 空输入（测试错误处理）
    {
        "input": "",
        "expected_error": "E001"
    },
    # 无结构化信息
    {
        "input": "这是一段普通的合同描述文本，没有明显的结构化字段信息。",
        "expected_fields": ["描述"]
    },
]


# ============================================================
# 自检函数
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检
    使用宽松阈值验证核心逻辑，不依赖精确值
    """
    print("开始自检...")
    analyzer = ContractAnalyzer()
    all_passed = True

    # 测试 1: 完整合同解析
    sample = SELFTEST_SAMPLES[0]
    result = analyzer.parse_input(sample["input"])
    print(f"\n测试 1 - 完整合同解析:")
    print(f"  状态: {result.status}")
    
    # 宽松断言：至少识别出 5 个字段
    assert len(result.items) >= 5, f"字段数量不足: {len(result.items)}"
    print(f"  识别字段数: {len(result.items)} ✓")

    # 检查关键字段存在
    field_names = [item.field_name for item in result.items]
    for expected in sample["expected_fields"]:
        assert expected in field_names, f"缺少字段: {expected}"
    print(f"  关键字段存在: {sample['expected_fields']} ✓")

    # 测试 2: 部分信息合同
    sample = SELFTEST_SAMPLES[1]
    result = analyzer.parse_input(sample["input"])
    print(f"\n测试 2 - 部分信息合同:")
    print(f"  状态: {result.status}")

    field_names = [item.field_name for item in result.items]
    for expected in sample["expected_fields"]:
        assert expected in field_names, f"缺少字段: {expected}"
    print(f"  关键字段存在: {sample['expected_fields']} ✓")

    # 测试 3: JSON 输入
    sample = SELFTEST_SAMPLES[2]
    result = analyzer.parse_input(sample["input"])
    print(f"\n测试 3 - JSON 输入:")
    print(f"  状态: {result.status}")

    field_names = [item.field_name for item in result.items]
    for expected in sample["expected_fields"]:
        assert expected in field_names, f"缺少字段: {expected}"
    print(f"  关键字段存在: {sample['expected_fields']} ✓")

    # 测试 4: 空输入错误处理
    sample = SELFTEST_SAMPLES[3]
    result = analyzer.parse_input(sample["input"])
    print(f"\n测试 4 - 空输入错误处理:")
    print(f"  状态: {result.status}, 错误码: {result.error_code}")
    assert result.status == "error", f"空输入应该报错，实际: {result.status}"
    assert result.error_code == sample["expected_error"], f"错误码不匹配: {result.error_code}"
    print(f"  错误码正确: {result.error_code} ✓")

    # 测试 5: 无结构化信息
    sample = SELFTEST_SAMPLES[4]
    result = analyzer.parse_input(sample["input"])
    print(f"\n测试 5 - 无结构化信息:")
    print(f"  状态: {result.status}")

    field_names = [item.field_name for item in result.items]
    for expected in sample["expected_fields"]:
        assert expected in field_names, f"缺少字段: {expected}"
    print(f"  描述字段存在: ✓")

    # 测试 6: 输出生成
    sample = SELFTEST_SAMPLES[0]
    parse_result = analyzer.parse_input(sample["input"])
    output = analyzer.generate_output(parse_result, "text")
    print(f"\n测试 6 - 文本输出生成:")
    print(f"  状态: {output.status}")
    assert output.message, "输出内容为空"
    assert len(output.message) > 50, f"输出内容过短: {len(output.message)}"
    print(f"  输出长度: {len(output.message)} 字符 ✓")

    # 测试 7: JSON 输出生成
    output = analyzer.generate_output(parse_result, "json")
    print(f"\n测试 7 - JSON 输出生成:")
    print(f"  状态: {output.status}")
    assert output.message, "JSON 输出为空"
    json_data = json.loads(output.message)
    assert "items" in json_data, "JSON 缺少 items 字段"
    print(f"  JSON 格式正确 ✓")

    # 测试 8: 批量处理
    inputs = [s["input"] for s in SELFTEST_SAMPLES[:3]]
    outputs = analyzer.batch_process(inputs)
    print(f"\n测试 8 - 批量处理:")
    print(f"  处理数量: {len(outputs)}")
    assert len(outputs) == 3, f"批量处理数量不对: {len(outputs)}"
    assert all(o.status != "error" or o.error_code == "E001" for o in outputs), "批量处理有意外错误"
    print(f"  批量处理成功 ✓")

    # 测试 9: 置信度计算
    sample = SELFTEST_SAMPLES[0]
    parse_result = analyzer.parse_input(sample["input"])
    print(f"\n测试 9 - 置信度计算:")
    confidences = [item.confidence for item in parse_result.items]
    avg_conf = sum(confidences) / len(confidences)
    print(f"  平均置信度: {avg_conf:.1f}%")
    # 宽松断言：置信度在合理范围
    assert avg_conf >= 50, f"平均置信度过低: {avg_conf}"
    assert avg_conf <= 100, f"置信度超过100: {avg_conf}"
    print(f"  置信度范围正常 ✓")

    # 测试 10: 错误码体系完整性
    print(f"\n测试 10 - 错误码体系:")
    for code, message in ERROR_CODES.items():
        assert code.startswith("E"), f"错误码格式错误: {code}"
        assert message, f"错误码 {code} 缺少消息"
    print(f"  错误码完整性: {len(ERROR_CODES)} 个 ✓")

    print("\n" + "=" * 50)
    print("所有自检测试通过！✓")
    print("=" * 50)
    return True


# ============================================================
# 主函数
# ============================================================
def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="合同审查助手 - Ally Legal Assistant",
        epilog="示例: python main.py --input '合同编号: ABC-001' --format text"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待分析的合同文本或 JSON 字符串"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例，无需外部文件）"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON 数组字符串，每个元素为一条输入"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式，输出详细日志"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"\n自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"\n自检异常: {e}", file=sys.stderr)
            return 1

    # 创建分析器
    analyzer = ContractAnalyzer()
    analyzer.debug_mode = args.debug

    # 批量处理模式
    if args.batch:
        try:
            inputs = json.loads(args.batch)
            if not isinstance(inputs, list):
                print("批量输入必须是 JSON 数组", file=sys.stderr)
                return 1
            outputs = analyzer.batch_process(inputs, args.format)
            for i, output in enumerate(outputs):
                print(f"\n--- 结果 {i+1} ---")
                print(output.message)
                if output.status == "error":
                    print(f"错误码: {output.error_code}", file=sys.stderr)
            return 0
        except json.JSONDecodeError:
            print("批量输入 JSON 格式错误", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"批量处理异常: {e}", file=sys.stderr)
            return 1

    # 单条处理模式
    if args.input:
        try:
            parse_result = analyzer.parse_input(args.input)
            output = analyzer.generate_output(parse_result, args.format)

            if output.status == "error":
                print(f"错误 [{output.error_code}]: {output.message}", file=sys.stderr)
                # 输出错误码提示
                if output.error_code in ERROR_CODES:
                    print(f"提示: {ERROR_CODES[output.error_code]}", file=sys.stderr)
                return 1

            print(output.message)

            # 警告信息输出到 stderr
            if output.status == "warning":
                print(f"\n警告 [{output.error_code}]: {output.message}", file=sys.stderr)

            return 0
        except Exception as e:
            print(f"处理异常 [{ERROR_CODES['E010']}]: {e}", file=sys.stderr)
            return 1

    # 无输入参数，显示帮助
    parser.print_help()
    print("\n提示: 使用 --selftest 运行内置自检")
    return 0


# ============================================================
# 程序入口
# ============================================================
if __name__ == "__main__":
    sys.exit(main())
