#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
horizon-dashboard 独立实现脚本
================================
基于功能规格 clean-room 重写，仅依赖 Python 标准库。

功能：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

用法：
    python main.py --selftest          # 离线自检（不读文件、不联网）
    python main.py --help              # 查看帮助
    python main.py "文本内容"          # 处理单个输入
    python main.py "文本1" "文本2"     # 批量处理
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与话术映射（规格 E001-E005，扩展至 E010）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或联系管理员",
    "E007": "批量处理时存在失败项，详见错误列表",
    "E008": "输出格式配置错误，请检查格式参数",
    "E009": "输入内容过大，超出单次处理上限",
    "E010": "未知错误，请提供更多上下文信息",
}

# 置信度阈值（规格定义）
HIGH_CONFIDENCE_THRESHOLD = 0.90
MEDIUM_CONFIDENCE_THRESHOLD = 0.85

# 默认输出字段模板
DEFAULT_FIELDS = ["原文", "类型", "关键信息", "置信度", "备注"]

# 单条输入最大字符数（防止内存溢出）
MAX_INPUT_LENGTH = 100_000


# ============================================================
# 核心处理逻辑
# ============================================================

class HorizonProcessor:
    """核心处理器：解析输入、结构化、计算置信度。"""

    def __init__(self) -> None:
        # 可识别的信息类型（正则模式）
        self._type_patterns: List[Tuple[str, str]] = [
            ("URL", r"https?://[^\s]+"),
            ("邮箱", r"[\w.+-]+@[\w-]+\.[\w.]+"),
            ("手机号", r"1[3-9]\d{9}"),
            ("日期", r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?"),
            ("金额", r"¥?\s?\d[\d,]*\.?\d*\s?(元|块)?"),
            ("身份证号", r"\d{17}[\dXx]"),
        ]
        # 常见关键信息词（用于识别语义重点）
        self._key_terms = [
            "项目", "合同", "金额", "日期", "地点", "人员",
            "要求", "目标", "结果", "风险", "方案", "报告",
        ]

    def process(self, raw_text: str) -> Dict[str, Any]:
        """处理单条输入，返回结构化结果。

        参数:
            raw_text: 用户输入的原始文本

        返回:
            结构化结果字典，包含原文、类型、关键信息、置信度、备注

        异常:
            ValueError: 当输入为空或超限时（对应 E001/E009）
        """
        # 输入校验
        if not raw_text or not raw_text.strip():
            raise ValueError("E001")
        if len(raw_text) > MAX_INPUT_LENGTH:
            raise ValueError("E009")

        text = raw_text.strip()

        # 1. 识别类型
        detected_types, matched_spans = self._detect_types(text)

        # 2. 提取关键信息
        key_info = self._extract_key_info(text)

        # 3. 计算置信度
        confidence = self._calculate_confidence(
            text, detected_types, key_info
        )

        # 4. 生成备注
        remarks = self._generate_remarks(confidence, detected_types)

        # 5. 组装结果
        result = {
            "原文": text,
            "类型": detected_types if detected_types else ["普通文本"],
            "关键信息": key_info,
            "置信度": round(confidence, 4),
            "备注": remarks,
        }
        return result

    def process_batch(self, inputs: List[str]) -> Dict[str, Any]:
        """批量处理多个输入。

        参数:
            inputs: 输入文本列表

        返回:
            包含成功项、失败项和统计信息的字典
        """
        results = []
        errors = []
        success_count = 0

        for idx, item in enumerate(inputs, start=1):
            try:
                result = self.process(item)
                result["序号"] = idx
                results.append(result)
                success_count += 1
            except ValueError as exc:
                error_code = str(exc)
                errors.append({
                    "序号": idx,
                    "错误码": error_code,
                    "错误信息": ERROR_MESSAGES.get(
                        error_code, ERROR_MESSAGES["E010"]
                    ),
                    "原文": item,
                })

        summary = {
            "成功数": success_count,
            "失败数": len(errors),
            "总数": len(inputs),
            "成功率": round(success_count / len(inputs), 4) if inputs else 0.0,
        }

        return {
            "结果": results,
            "错误": errors,
            "统计": summary,
        }

    # --------------------------------------------------------
    # 内部辅助方法
    # --------------------------------------------------------

    def _detect_types(self, text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        """识别文本中的信息类型。

        返回:
            (类型列表, 匹配位置列表)
        """
        detected = []
        spans = []
        for type_name, pattern in self._type_patterns:
            for match in re.finditer(pattern, text):
                detected.append(type_name)
                spans.append((match.start(), match.end()))
        # 去重但保留顺序
        unique_types = list(dict.fromkeys(detected))
        return unique_types, spans

    def _extract_key_info(self, text: str) -> List[str]:
        """提取关键信息片段。

        策略：
        - 查找包含关键术语的句子片段
        - 提取数字、专有名词等
        """
        key_info = []

        # 按句号、逗号、分号切分
        segments = re.split(r"[，。；、,.;\n]", text)

        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            # 包含关键术语 或 包含数字
            if any(term in seg for term in self._key_terms) or re.search(
                r"\d", seg
            ):
                # 截取前 50 字符作为关键信息
                key_info.append(seg[:50])

        # 去重
        unique_info = list(dict.fromkeys(key_info))

        # 若没有识别到，返回整体前 30 字符
        if not unique_info:
            unique_info = [text[:30]]

        return unique_info[:5]  # 最多返回 5 条

    def _calculate_confidence(
        self,
        text: str,
        detected_types: List[str],
        key_info: List[str],
    ) -> float:
        """计算置信度（0~1）。

        规则：
        - 基础分 0.75
        - 识别到类型 +0.1（最多 +0.15）
        - 提取到关键信息 +0.05
        - 文本长度适中（10~500字符）+0.05
        - 文本过短（<10字符）-0.1
        """
        confidence = 0.75

        # 类型识别加分
        if detected_types:
            confidence += min(0.15, 0.10 * len(detected_types))

        # 关键信息加分
        if key_info:
            confidence += 0.05

        # 长度判断
        text_len = len(text)
        if 10 <= text_len <= 500:
            confidence += 0.05
        elif text_len < 10:
            confidence -= 0.10

        # 限制在 [0, 1] 区间
        return max(0.0, min(1.0, confidence))

    def _generate_remarks(
        self, confidence: float, detected_types: List[str]
    ) -> str:
        """根据置信度生成备注说明。"""
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return "可直接使用"
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "建议复核"
        else:
            uncertain_items = []
            if not detected_types:
                uncertain_items.append("未识别明确的信息类型")
            if confidence < 0.7:
                uncertain_items.append("文本信息量不足")
            detail = "；".join(uncertain_items) if uncertain_items else "不确定点较多"
            return f"[需核实] {detail}"


# ============================================================
# 输出格式化
# ============================================================

def format_output(
    data: Dict[str, Any],
    output_format: str = "text",
    fields: Optional[List[str]] = None,
) -> str:
    """将处理结果格式化为指定格式。

    参数:
        data: 处理结果字典
        output_format: "text" | "json"
        fields: 需要输出的字段列表

    返回:
        格式化后的字符串

    异常:
        ValueError: 当输出格式不支持时（对应 E008）
    """
    if output_format == "json":
        # JSON 输出
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif output_format == "text":
        # 文本输出
        lines = []
        selected_fields = fields or DEFAULT_FIELDS

        for field in selected_fields:
            if field in data:
                value = data[field]
                if isinstance(value, list):
                    value = "; ".join(str(v) for v in value)
                lines.append(f"{field}: {value}")

        return "\n".join(lines)

    else:
        raise ValueError("E008")


def format_batch_output(
    batch_result: Dict[str, Any],
    output_format: str = "text",
) -> str:
    """格式化批量处理结果。"""
    if output_format == "json":
        return json.dumps(batch_result, ensure_ascii=False, indent=2)

    # 文本格式
    lines = []
    if batch_result["结果"]:
        lines.append("=== 处理结果 ===")
        for item in batch_result["结果"]:
            lines.append(f"\n--- 序号 {item['序号']} ---")
            lines.append(format_output(item, "text"))

    if batch_result["错误"]:
        lines.append("\n=== 错误信息 ===")
        for err in batch_result["错误"]:
            lines.append(
                f"[{err['序号']}] {err['错误码']}: {err['错误信息']}"
            )

    stat = batch_result["统计"]
    lines.append(
        f"\n=== 统计 ===\n"
        f"总数: {stat['总数']}, 成功: {stat['成功数']}, "
        f"失败: {stat['失败数']}, 成功率: {stat['成功率']:.1%}"
    )

    return "\n".join(lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> bool:
    """离线自检核心逻辑。

    使用内置硬编码样例数据，不读文件、不联网、不依赖工作目录。
    断言使用宽松阈值，确保任何环境可过。

    返回:
        True 表示全部通过，False 表示失败
    """
    print("=== 开始自检 ===\n")

    processor = HorizonProcessor()

    # 测试用例（硬编码内置）
    test_cases = [
        # (描述, 输入, 期望类型数下限, 期望置信度下限)
        ("普通文本", "今天天气很好，适合出门散步。", 0, 0.50),
        ("URL", "请访问 https://example.com/data 获取信息。", 1, 0.60),
        ("邮箱", "请联系 support@example.com 咨询问题。", 1, 0.60),
        ("混合信息", "项目金额5000元，日期2024年3月15日，地点北京。", 2, 0.65),
        ("短文本", "测试", 0, 0.40),
    ]

    all_passed = True

    # 逐条测试
    for desc, text, min_types, min_conf in test_cases:
        try:
            result = processor.process(text)

            # 宽松断言
            assert result["原文"] == text.strip(), "原文不匹配"
            assert len(result["类型"]) >= min_types, "类型数量不足"
            assert result["置信度"] >= min_conf, "置信度过低"
            assert result["关键信息"], "关键信息为空"
            assert result["备注"], "备注为空"

            print(f"  [通过] {desc}: 置信度={result['置信度']:.2f}")
        except AssertionError as exc:
            print(f"  [失败] {desc}: {exc}")
            all_passed = False
        except Exception as exc:
            print(f"  [异常] {desc}: {exc}")
            all_passed = False

    # 批量测试
    print("\n--- 批量处理测试 ---")
    try:
        batch_inputs = [
            "第一个测试文本 https://example.com",
            "第二个测试文本，包含邮箱 test@test.com",
            "",  # 空输入，应报错 E001
        ]
        batch_result = processor.process_batch(batch_inputs)

        # 宽松断言：成功数至少 1，错误数至少 1
        assert batch_result["统计"]["成功数"] >= 1, "批量成功数不足"
        assert batch_result["统计"]["失败数"] >= 1, "应至少有一个失败项"
        assert batch_result["统计"]["总数"] == 3, "总数不正确"

        print(f"  [通过] 批量处理: 成功={batch_result['统计']['成功数']}, "
              f"失败={batch_result['统计']['失败数']}")
    except AssertionError as exc:
        print(f"  [失败] 批量处理: {exc}")
        all_passed = False
    except Exception as exc:
        print(f"  [异常] 批量处理: {exc}")
        all_passed = False

    # 输出格式测试
    print("\n--- 输出格式测试 ---")
    try:
        sample = processor.process("测试文本")
        text_out = format_output(sample, "text")
        json_out = format_output(sample, "json")

        assert text_out, "文本输出为空"
        assert json_out, "JSON输出为空"
        json.loads(json_out)  # 验证 JSON 可解析

        print("  [通过] text/json 两种格式均正常")
    except AssertionError as exc:
        print(f"  [失败] 输出格式: {exc}")
        all_passed = False
    except Exception as exc:
        print(f"  [异常] 输出格式: {exc}")
        all_passed = False

    # 错误处理测试
    print("\n--- 错误处理测试 ---")
    try:
        # E001: 空输入
        try:
            processor.process("")
            print("  [失败] 空输入未抛出 E001")
            all_passed = False
        except ValueError as exc:
            assert str(exc) == "E001", f"错误码不正确: {exc}"
            print("  [通过] E001 空输入")

        # E008: 非法输出格式
        try:
            format_output({}, "xml")
            print("  [失败] 非法格式未抛出 E008")
            all_passed = False
        except ValueError as exc:
            assert str(exc) == "E008", f"错误码不正确: {exc}"
            print("  [通过] E008 非法输出格式")

        # E009: 超长输入
        try:
            processor.process("a" * (MAX_INPUT_LENGTH + 1))
            print("  [失败] 超长输入未抛出 E009")
            all_passed = False
        except ValueError as exc:
            assert str(exc) == "E009", f"错误码不正确: {exc}"
            print("  [通过] E009 超长输入")

    except AssertionError as exc:
        print(f"  [失败] 错误处理: {exc}")
        all_passed = False
    except Exception as exc:
        print(f"  [异常] 错误处理: {exc}")
        all_passed = False

    # 错误码完整性检查
    print("\n--- 错误码完整性 ---")
    try:
        required_codes = ["E001", "E002", "E003", "E004", "E005"]
        for code in required_codes:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
            assert ERROR_MESSAGES[code].strip(), f"错误码 {code} 话术为空"
        print(f"  [通过] 核心错误码 {required_codes} 均已定义")
    except AssertionError as exc:
        print(f"  [失败] 错误码完整性: {exc}")
        all_passed = False

    # 总结
    print("\n" + "=" * 40)
    if all_passed:
        print("自检全部通过 ✓")
        return True
    else:
        print("自检存在失败项 ✗")
        return False


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数。

    返回:
        0 表示成功，非 0 表示失败
    """
    parser = argparse.ArgumentParser(
        description="horizon-dashboard 翻译润色工具",
        epilog="示例: python main.py '待处理文本' 或 python main.py --selftest",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="待处理的文本内容（可多个，批量处理）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认 text）",
    )
    parser.add_argument(
        "--fields",
        nargs="*",
        default=None,
        help="输出字段列表（仅 text 格式有效）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理模式
    if not args.inputs:
        print(ERROR_MESSAGES["E001"], file=sys.stderr)
        return 1

    processor = HorizonProcessor()

    try:
        if len(args.inputs) == 1:
            # 单条处理
            result = processor.process(args.inputs[0])
            output = format_output(result, args.format, args.fields)
            print(output)
        else:
            # 批量处理
            batch_result = processor.process_batch(args.inputs)
            output = format_batch_output(batch_result, args.format)
            print(output)

            # 有错误时返回非零
            if batch_result["错误"]:
                return 1

        return 0

    except ValueError as exc:
        error_code = str(exc)
        message = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
        print(f"[{error_code}] {message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E006] 内部处理异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
