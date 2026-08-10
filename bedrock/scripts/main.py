#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bedrock 技能实现
数据解析 / 信息抽取 / 结构化输出，支持批量处理与置信度标注。
仅依赖标准库，独立实现（clean-room）。
"""

import json
import re
import sys
from datetime import timezone, datetime
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或不是有效文本",
    "E002": "输入数据格式不支持（仅支持文本/JSON/CSV）",
    "E003": "JSON 解析失败",
    "E004": "字段提取失败：未找到任何关键信息",
    "E005": "批量处理输入格式错误",
    "E006": "输出序列化失败",
    "E007": "置信度计算异常",
    "E008": "参数校验失败",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class BedrockError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class FieldResult:
    """单个字段的提取结果。"""

    def __init__(self, name: str, value: Any, confidence: str = "低"):
        self.name = name
        self.value = value
        self.confidence = confidence  # 高 / 中 / 低

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.name,
            "value": self.value,
            "confidence": self.confidence,
        }


class ParseResult:
    """一条数据解析的完整结果。"""

    def __init__(self, source: str = "", fields: Optional[List[FieldResult]] = None):
        self.source = source
        self.fields = fields or []
        self.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "timestamp": self.timestamp,
            "fields": [f.to_dict() for f in self.fields],
        }


# ============================================================
# 字段提取规则（硬编码，不依赖外部资源）
# ============================================================

# 字段名称 -> 正则表达式模式
FIELD_PATTERNS: Dict[str, str] = {
    "姓名": r"(?:姓名|名字|称呼)[:：\s]*([\u4e00-\u9fa5]{2,4})",
    "电话": r"(?:电话|手机|联系方式)[:：\s]*((?:1[3-9]\d{9})|(?:\d{3,4}[-]?\d{7,8})|(?:\d{5,}))",
    "邮箱": r"(?:邮箱|电子邮件|Email|E-mail)[:：\s]*([\w.\-]+@[\w\-]+\.[\w.\-]+)",
    "日期": r"(?:日期|时间|日期时间)[:：\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    "金额": r"(?:金额|价格|费用)[:：\s]*([0-9]+(?:\.[0-9]{1,2})?)\s*(元|人民币|CNY|￥)?",
    "编号": r"(?:编号|单号|订单号|ID|No\.?)[:：\s]*([A-Za-z0-9\-]{4,20})",
    "地址": r"(?:地址|位置|地点)[:：\s]*([\u4e00-\u9fa50-9A-Za-z\-\s]{5,50})",
    "备注": r"(?:备注|说明|描述)[:：\s]*(.{3,100})",
}

# 字段中文名 -> 标准输出键名
FIELD_KEYS = {
    "姓名": "name",
    "电话": "phone",
    "邮箱": "email",
    "日期": "date",
    "金额": "amount",
    "编号": "id",
    "地址": "address",
    "备注": "remark",
}


# ============================================================
# 核心逻辑
# ============================================================

def validate_input(data: Any) -> str:
    """校验输入数据，返回文本内容。"""
    if data is None:
        raise BedrockError("E001")

    if isinstance(data, str):
        text = data.strip()
        if not text:
            raise BedrockError("E001")
        return text

    if isinstance(data, dict) or isinstance(data, list):
        # 尝试将结构化数据转为 JSON 文本
        try:
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            raise BedrockError("E002")

    if isinstance(data, (int, float, bool)):
        return str(data)

    raise BedrockError("E002")


def extract_fields(text: str) -> List[FieldResult]:
    """从文本中提取关键字段。"""
    fields: List[FieldResult] = []

    for field_name, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            raw_value = match.group(1).strip()
            if not raw_value:
                continue

            # 计算置信度（宽松规则）
            confidence = _calc_confidence(field_name, raw_value, text)

            fields.append(FieldResult(
                name=FIELD_KEYS.get(field_name, field_name),
                value=raw_value,
                confidence=confidence,
            ))

    if not fields:
        # 如果没有匹配到任何字段，尝试将整个文本作为"内容"字段输出
        # 这样即使是非结构化文本也能得到结构化结果
        fields.append(FieldResult(
            name="content",
            value=text[:200],
            confidence="低",
        ))

    return fields


def _calc_confidence(field_name: str, value: str, full_text: str) -> str:
    """基于简单规则计算置信度（高/中/低）。"""
    try:
        # 基础得分：字段模式匹配成功即有一定置信度
        score = 0.5

        # 值长度增加置信度
        if len(value) >= 6:
            score += 0.2

        # 值中包含数字增加置信度（对电话、金额、编号等）
        if field_name in ("电话", "金额", "编号") and re.search(r"\d", value):
            score += 0.2

        # 值在原文中出现多次增加置信度
        if full_text.count(value) > 1:
            score += 0.1

        # 值包含特定格式特征增加置信度
        if field_name == "邮箱" and "@" in value:
            score += 0.2
        if field_name == "电话":
            if re.fullmatch(r"1[3-9]\d{9}", value):
                score += 0.1  # 完整手机号
            elif len(value) >= 7:
                score += 0.05  # 较长的电话号码
        if field_name == "日期" and re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", value):
            score += 0.1

        # 映射为高中低
        if score >= 0.8:
            return "高"
        elif score >= 0.6:
            return "中"
        else:
            return "低"
    except Exception:
        # 任何计算异常都返回低置信度，不阻断主流程
        return "低"


def process_single(data: Any) -> ParseResult:
    """处理单条数据。"""
    text = validate_input(data)
    fields = extract_fields(text)
    return ParseResult(source=text[:200], fields=fields)


def process_batch(data_list: List[Any]) -> List[ParseResult]:
    """批量处理多组数据。"""
    if not isinstance(data_list, list) or len(data_list) == 0:
        raise BedrockError("E005")

    results = []
    for item in data_list:
        try:
            result = process_single(item)
            results.append(result)
        except BedrockError:
            # 单条失败不阻断批量流程，跳过并继续
            continue

    if not results:
        raise BedrockError("E004")

    return results


def format_output(results: List[ParseResult], output_format: str = "json") -> str:
    """格式化输出结果。"""
    try:
        if output_format == "json":
            data = [r.to_dict() for r in results]
            if len(results) == 1:
                data = data[0]
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == "table":
            # 简单表格输出（CSV 风格）
            lines = []
            for r in results:
                for f in r.fields:
                    lines.append(f"{r.timestamp},{f.name},{f.value},{f.confidence}")
            return "\n".join(lines)
        else:
            raise BedrockError("E008", f"不支持的输出格式: {output_format}")
    except BedrockError:
        raise
    except Exception:
        raise BedrockError("E006")


# ============================================================
# 命令行入口
# ============================================================

def _run_selftest() -> int:
    """内置自检逻辑：使用硬编码样例数据离线验证核心功能。"""
    print("[selftest] 开始自检...")

    # --- 样例 1：单条文本解析 ---
    sample1 = "姓名: 张三, 电话: 13812345678, 邮箱: zhangsan@example.com, 日期: 2024-03-15"
    try:
        result1 = process_single(sample1)
        assert len(result1.fields) >= 3, "应至少提取 3 个字段"
        field_names = [f.name for f in result1.fields]
        assert "name" in field_names, "应包含姓名"
        assert "phone" in field_names, "应包含电话"
        assert "email" in field_names, "应包含邮箱"

        # 宽松断言：值非空即可
        for f in result1.fields:
            assert f.value, "字段值不应为空"
            assert f.confidence in ("高", "中", "低"), "置信度取值非法"

        print(f"  [通过] 单条文本解析: {len(result1.fields)} 个字段")
    except AssertionError as e:
        print(f"  [失败] 单条文本解析: {e}")
        return 1
    except BedrockError as e:
        print(f"  [失败] 单条文本解析: {e}")
        return 1

    # --- 样例 2：批量处理 ---
    sample_batch = [
        "姓名: 李四, 金额: 99.50元, 编号: ORD-2024-001",
        "姓名: 王五, 电话: 13912345678, 地址: 北京市朝阳区",
        "姓名: 赵六, 邮箱: zhaoliu@test.com, 日期: 2024/06/30",
    ]
    try:
        batch_results = process_batch(sample_batch)
        assert len(batch_results) >= 2, "批量处理应至少成功 2 条"
        for r in batch_results:
            assert len(r.fields) >= 1, "每条结果应至少 1 个字段"

        print(f"  [通过] 批量处理: {len(batch_results)} 条成功")
    except AssertionError as e:
        print(f"  [失败] 批量处理: {e}")
        return 1
    except BedrockError as e:
        print(f"  [失败] 批量处理: {e}")
        return 1

    # --- 样例 3：输出格式化 ---
    try:
        json_out = format_output(batch_results, "json")
        parsed = json.loads(json_out)
        assert parsed is not None, "JSON 输出应可解析"

        table_out = format_output(batch_results, "table")
        assert len(table_out) > 0, "表格输出不应为空"

        print("  [通过] 输出格式化 (json/table)")
    except AssertionError as e:
        print(f"  [失败] 输出格式化: {e}")
        return 1
    except BedrockError as e:
        print(f"  [失败] 输出格式化: {e}")
        return 1

    # --- 样例 4：错误处理 ---
    try:
        process_single("")
        print("  [失败] 错误处理: 空输入应抛异常")
        return 1
    except BedrockError as e:
        assert e.code == "E001", "空输入错误码应为 E001"
        print(f"  [通过] 错误处理: 空输入返回 {e.code}")

    # --- 样例 5：置信度标注 ---
    try:
        sample5 = "姓名: 张三, 电话: 13812345678"
        result5 = process_single(sample5)
        phone_field = [f for f in result5.fields if f.name == "phone"]
        assert len(phone_field) == 1, "应找到电话字段"
        assert phone_field[0].confidence in ("高", "中"), "完整手机号置信度应为中或高"

        sample5b = "姓名: 张三, 电话: 12345"
        result5b = process_single(sample5b)
        phone_field_b = [f for f in result5b.fields if f.name == "phone"]
        assert len(phone_field_b) == 1, "应找到电话字段"
        # 宽松断言：短号码置信度不应高于完整号码
        conf_map = {"高": 3, "中": 2, "低": 1}
        assert conf_map[phone_field_b[0].confidence] <= conf_map[phone_field[0].confidence], \
            "短号码置信度不应高于完整号码"

        print("  [通过] 置信度标注逻辑")
    except AssertionError as e:
        print(f"  [失败] 置信度标注: {e}")
        return 1
    except BedrockError as e:
        print(f"  [失败] 置信度标注: {e}")
        return 1

    # --- 样例 6：边界条件（数字输入） ---
    try:
        result_num = process_single(12345)
        assert result_num.source == "12345", "数字输入应转为字符串"
        assert len(result_num.fields) >= 1, "数字输入应至少产生一个字段"
        print("  [通过] 边界条件: 数字输入")
    except AssertionError as e:
        print(f"  [失败] 边界条件: {e}")
        return 1
    except BedrockError as e:
        print(f"  [失败] 边界条件: {e}")
        return 1

    # --- 样例 7：批量输入格式错误 ---
    try:
        process_batch([])
        print("  [失败] 批量输入格式: 空列表应抛异常")
        return 1
    except BedrockError as e:
        assert e.code == "E005", "空列表错误码应为 E005"
        print(f"  [通过] 批量输入格式: 空列表返回 {e.code}")

    # --- 样例 8：不支持的输出格式 ---
    try:
        format_output([ParseResult(source="test", fields=[FieldResult("name", "张三")])], "xml")
        print("  [失败] 输出格式: 不支持的格式应抛异常")
        return 1
    except BedrockError as e:
        assert e.code == "E008", "不支持的格式错误码应为 E008"
        print(f"  [通过] 输出格式: 不支持格式返回 {e.code}")

    print("[selftest] 全部自检通过 ✓")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    argv = argv if argv is not None else sys.argv[1:]

    # 自检模式
    if "--selftest" in argv:
        return _run_selftest()

    # 参数解析（极简命令行）
    try:
        # 支持 --input 或直接传入文本
        input_text = None
        output_format = "json"

        i = 0
        while i < len(argv):
            if argv[i] == "--input" and i + 1 < len(argv):
                input_text = argv[i + 1]
                i += 2
            elif argv[i] == "--format" and i + 1 < len(argv):
                output_format = argv[i + 1]
                i += 2
            elif argv[i] == "--help" or argv[i] == "-h":
                print("用法: python main.py [--input 文本] [--format json|table] [--selftest]")
                print("      直接传文本: python main.py \"姓名: 张三, 电话: 13812345678\"")
                return 0
            else:
                # 将非参数内容视为输入文本
                if input_text is None:
                    input_text = argv[i]
                else:
                    input_text += " " + argv[i]
                i += 1

        if input_text is None:
            print("错误: 未提供输入数据。使用 --input 指定文本，或使用 --selftest 自检。")
            return 1

        # 尝试解析为批量（JSON 数组）
        try:
            parsed_input = json.loads(input_text)
            if isinstance(parsed_input, list):
                results = process_batch(parsed_input)
            else:
                results = [process_single(parsed_input)]
        except json.JSONDecodeError:
            # 不是 JSON，按单条文本处理
            results = [process_single(input_text)]

        output = format_output(results, output_format)
        print(output)
        return 0

    except BedrockError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E010']}] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
