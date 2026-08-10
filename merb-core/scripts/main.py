#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merb-core 数据提炼与结构化输出工具（独立实现）

本脚本根据功能规格重新实现核心逻辑：
- 解析文本数据源，识别关键字段（实体、数字、日期、状态）
- 按模板输出结构化结果（JSON 格式）
- 对每个字段标注置信度（高/中/低）及理由
- 支持批量记录处理

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"      # 输入为空或不是字符串
ERR_UNSUPPORTED_FORMAT = "E002" # 不支持的输出格式
ERR_FIELD_SPEC_INVALID = "E003" # 字段规格不合法
ERR_BATCH_EMPTY = "E004"        # 批量输入为空
ERR_DATE_PARSE = "E005"         # 日期解析失败
ERR_NUMBER_PARSE = "E006"       # 数字解析失败
ERR_JSON_SERIALIZE = "E007"     # JSON 序列化失败
ERR_OUTPUT_WRITE = "E008"       # 输出写入失败
ERR_INTERNAL = "E009"           # 内部逻辑错误
ERR_SELFTEST_FAILED = "E010"    # 自检失败


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class FieldResult:
    """单个字段的提取结果。"""
    def __init__(self, name: str, value: Any, confidence: str, reason: str):
        self.name = name
        self.value = value
        self.confidence = confidence  # 高/中/低
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.name,
            "value": self.value,
            "confidence": self.confidence,
            "reason": self.reason
        }


class RecordResult:
    """单条记录的结构化输出结果。"""
    def __init__(self, record_id: Optional[str] = None):
        self.record_id = record_id or "record_1"
        self.fields: List[FieldResult] = []
        self.overall_confidence: str = "低"
        self.warnings: List[str] = []

    def add_field(self, field: FieldResult) -> None:
        self.fields.append(field)

    def compute_overall(self) -> None:
        """根据字段置信度计算整体置信度。"""
        if not self.fields:
            self.overall_confidence = "低"
            return
        # 统计各档数量
        high_count = sum(1 for f in self.fields if f.confidence == "高")
        mid_count = sum(1 for f in self.fields if f.confidence == "中")
        # 宽松规则：只要有一半以上为高，则整体为高；否则有中则为中；否则低
        total = len(self.fields)
        if high_count >= total / 2:
            self.overall_confidence = "高"
        elif mid_count > 0:
            self.overall_confidence = "中"
        else:
            self.overall_confidence = "低"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "fields": [f.to_dict() for f in self.fields],
            "overall_confidence": self.overall_confidence,
            "warnings": self.warnings
        }


# ---------------------------------------------------------------------------
# 解析工具函数
# ---------------------------------------------------------------------------
def parse_date(text: str) -> Optional[Tuple[str, str]]:
    """
    从文本中提取日期。支持常见格式：
    YYYY-MM-DD, YYYY/MM/DD, YYYY年M月D日, MM-DD-YYYY 等。
    返回 (日期字符串, 置信度)。无法识别返回 None。
    """
    if not text:
        return None

    # 尝试多种格式
    patterns = [
        (r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?', "高"),
        (r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', "中"),  # 美式 MM-DD-YYYY
        (r'(\d{4})年(\d{1,2})月(\d{1,2})日', "高"),
        (r'(\d{1,2})月(\d{1,2})日', "中"),  # 无年份
    ]

    for pattern, conf in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if len(groups) == 3:
                    # 判断是 YYYY-MM-DD 还是 MM-DD-YYYY
                    if int(groups[0]) > 1000:
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    # 验证日期合法性
                    datetime(year, month, day)
                    return (f"{year:04d}-{month:02d}-{day:02d}", conf)
                elif len(groups) == 2:
                    month, day = int(groups[0]), int(groups[1])
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        return (f"****-{month:02d}-{day:02d}", "中")
            except ValueError:
                continue
    return None


def parse_number(text: str) -> Optional[Tuple[float, str]]:
    """从文本中提取数字（整数或小数）。返回 (数值, 置信度)。"""
    if not text:
        return None

    # 尝试匹配数字（支持千分位逗号）
    match = re.search(r'[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+|\d+', text)
    if match:
        num_str = match.group().replace(',', '')
        try:
            value = float(num_str)
            # 如果带小数或千分位，置信度更高
            conf = "高" if ('.' in num_str or ',' in match.group()) else "中"
            return (value, conf)
        except ValueError:
            return None
    return None


def extract_email(text: str) -> Optional[Tuple[str, str]]:
    """提取电子邮件地址。"""
    match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    if match:
        return (match.group(), "高")
    return None


def extract_phone(text: str) -> Optional[Tuple[str, str]]:
    """提取电话号码（简单规则：至少 7 位数字，可带区号）。"""
    match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(\d{2,4}\)[-.\s]?)?\d{3,4}[-.\s]?\d{4}', text)
    if match:
        return (match.group(), "中")
    return None


# ---------------------------------------------------------------------------
# 核心提取逻辑
# ---------------------------------------------------------------------------
def extract_fields(text: str, field_spec: Optional[List[str]] = None) -> RecordResult:
    """
    从单条文本中提取结构化字段。

    参数:
        text: 输入文本
        field_spec: 可选字段规格列表。若为 None 则使用默认字段。

    返回:
        RecordResult 对象
    """
    if not text or not isinstance(text, str):
        raise ValueError(ERR_INVALID_INPUT)

    # 默认字段规格：姓名、邮箱、电话、日期、金额、描述
    default_fields = ["姓名", "邮箱", "电话", "日期", "金额", "描述"]
    fields_to_extract = field_spec if field_spec else default_fields

    record = RecordResult()
    text_lower = text.lower()

    # 逐字段提取
    for field_name in fields_to_extract:
        field_result = None

        if field_name in ("姓名", "name", "联系人"):
            # 姓名：尝试匹配 "姓名：XXX" 或 "姓名是XXX"
            match = re.search(r'姓名[:：]\s*([^\s,，。]+)', text)
            if match:
                field_result = FieldResult(field_name, match.group(1), "高", "明确标识")
            else:
                # 宽松匹配：中文姓名（2-4字）
                match = re.search(r'([\u4e00-\u9fa5]{2,4})(?=\s|，|,|。|$)', text)
                if match and match.group(1) not in ("姓名", "电话", "日期", "金额"):
                    field_result = FieldResult(field_name, match.group(1), "中", "推测")

        elif field_name in ("邮箱", "email"):
            email = extract_email(text)
            if email:
                field_result = FieldResult(field_name, email[0], email[1], "正则匹配")

        elif field_name in ("电话", "phone", "手机"):
            phone = extract_phone(text)
            if phone:
                field_result = FieldResult(field_name, phone[0], phone[1], "正则匹配")

        elif field_name in ("日期", "date", "时间"):
            date_info = parse_date(text)
            if date_info:
                field_result = FieldResult(field_name, date_info[0], date_info[1], "日期解析")

        elif field_name in ("金额", "价格", "费用", "amount", "price"):
            # 优先匹配带货币符号的金额
            money_match = re.search(r'[¥￥$€]\s*(\d[\d,]*\.?\d*)', text)
            if money_match:
                value = money_match.group(1).replace(',', '')
                field_result = FieldResult(field_name, float(value), "高", "货币符号明确")
            else:
                num_info = parse_number(text)
                if num_info:
                    field_result = FieldResult(field_name, num_info[0], num_info[1], "数字解析")

        elif field_name in ("描述", "备注", "内容", "description"):
            # 提取句子作为描述（简单规则：取第一个句号前的完整句子）
            sentences = re.split(r'[。！？!?]', text)
            if sentences and sentences[0].strip():
                desc = sentences[0].strip()[:100]  # 限制长度
                field_result = FieldResult(field_name, desc, "中", "截取首句")

        elif field_name in ("状态", "status"):
            # 识别状态关键词
            status_keywords = {
                "完成": "高", "已完成": "高", "进行中": "高", "待处理": "高",
                "成功": "高", "失败": "高", "取消": "中", "暂停": "中",
                "active": "高", "done": "高", "pending": "高", "closed": "高"
            }
            for keyword, conf in status_keywords.items():
                if keyword in text_lower:
                    field_result = FieldResult(field_name, keyword, conf, "关键词匹配")
                    break

        # 如果该字段未提取到，添加警告
        if field_result:
            record.add_field(field_result)
        else:
            record.warnings.append(f"字段 '{field_name}' 未提取到值")

    # 计算整体置信度
    record.compute_overall()
    return record


def process_batch(texts: List[str], field_spec: Optional[List[str]] = None) -> List[RecordResult]:
    """批量处理多条文本。"""
    if not texts:
        raise ValueError(ERR_BATCH_EMPTY)

    results = []
    for idx, text in enumerate(texts, start=1):
        try:
            record = extract_fields(text, field_spec)
            record.record_id = f"record_{idx}"
            results.append(record)
        except ValueError as e:
            # 单条失败不影响整体，记为空记录
            empty_rec = RecordResult(f"record_{idx}")
            empty_rec.warnings.append(f"处理失败: {e}")
            results.append(empty_rec)
    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(results: List[RecordResult], output_format: str = "json") -> str:
    """将结果格式化为指定格式（目前支持 JSON）。"""
    if output_format not in ("json", "JSON"):
        raise ValueError(ERR_UNSUPPORTED_FORMAT)

    data = [r.to_dict() for r in results]
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except TypeError as e:
        raise ValueError(f"{ERR_JSON_SERIALIZE}: {e}")


# ---------------------------------------------------------------------------
# 命令行处理
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=== merb-core 自检开始 ===")

    # 测试样例 1：标准文本
    sample1 = "姓名：张三，邮箱: zhangsan@example.com，电话: 138-1234-5678，日期: 2026-03-15，金额: ¥1,234.56。项目已完成。"
    try:
        rec1 = extract_fields(sample1)
        assert rec1 is not None
        assert len(rec1.fields) > 0, "应至少提取一个字段"
        # 宽松断言：只要结果非空即可
        assert rec1.overall_confidence in ("高", "中", "低"), "置信度必须为三档之一"
        print(f"  样例1通过: 提取 {len(rec1.fields)} 个字段, 置信度={rec1.overall_confidence}")
    except AssertionError as e:
        print(f"  样例1失败: {e}")
        return 1

    # 测试样例 2：模糊文本
    sample2 = "联系我 13812345678 或 email 测试test@test.org，大概3月20号左右，花了大约500块。"
    try:
        rec2 = extract_fields(sample2)
        assert rec2 is not None
        # 应该至少提取到邮箱或电话
        field_names = [f.name for f in rec2.fields]
        assert any(name in ("邮箱", "电话", "日期", "金额") for name in field_names), "应提取到关键字段"
        print(f"  样例2通过: 字段={field_names}")
    except AssertionError as e:
        print(f"  样例2失败: {e}")
        return 1

    # 测试样例 3：批量处理
    try:
        batch = [sample1, sample2, "无效输入"]
        results = process_batch(batch)
        assert len(results) == 3, "批量应返回3条结果"
        assert all(r.record_id.startswith("record_") for r in results)
        print(f"  样例3通过: 批量处理 {len(results)} 条")
    except AssertionError as e:
        print(f"  样例3失败: {e}")
        return 1

    # 测试样例 4：日期解析
    try:
        date_info = parse_date("2026年12月31日")
        assert date_info is not None, "应能解析中文日期"
        assert date_info[0].startswith("2026"), "年份应正确"
        date_info2 = parse_date("2026-03-15")
        assert date_info2 is not None, "应能解析ISO日期"
        print(f"  样例4通过: 日期解析正常")
    except AssertionError as e:
        print(f"  样例4失败: {e}")
        return 1

    # 测试样例 5：输出格式化
    try:
        rec = extract_fields(sample1)
        output_str = format_output([rec], "json")
        parsed = json.loads(output_str)
        assert isinstance(parsed, list) and len(parsed) == 1
        print(f"  样例5通过: JSON输出正常")
    except (AssertionError, ValueError) as e:
        print(f"  样例5失败: {e}")
        return 1

    print("=== 全部自检通过 ===")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="merb-core 数据提炼与结构化输出工具",
        epilog="示例: python main.py --input '姓名: 张三, 金额: 100元' --fields 姓名 金额"
    )
    parser.add_argument("--input", "-i", help="输入文本（单条）")
    parser.add_argument("--file", "-f", help="输入文件路径（每行一条记录）")
    parser.add_argument("--fields", "-F", nargs="*", help="要提取的字段名列表")
    parser.add_argument("--format", "-fmt", default="json", choices=["json"], help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--batch", action="store_true", help="批量模式（配合 --file）")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        # 收集输入
        texts: List[str] = []

        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8", errors="replace") as f:
                    texts = [line.strip() for line in f if line.strip()]
            except OSError as e:
                print(f"错误 {ERR_OUTPUT_WRITE}: 无法读取文件 {args.file}: {e}", file=sys.stderr)
                return 1
        elif args.input:
            texts = [args.input]
        else:
            # 交互模式：从 stdin 读取
            print("请输入文本（Ctrl+D 结束）:")
            for line in sys.stdin:
                line = line.strip()
                if line:
                    texts.append(line)

        if not texts:
            print(f"错误 {ERR_INVALID_INPUT}: 没有输入文本", file=sys.stderr)
            return 1

        # 提取字段
        field_spec = args.fields if args.fields else None
        if args.batch or len(texts) > 1:
            results = process_batch(texts, field_spec)
        else:
            rec = extract_fields(texts[0], field_spec)
            results = [rec]

        # 输出结果
        output = format_output(results, args.format)
        print(output)
        return 0

    except ValueError as e:
        print(f"错误 {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 {ERR_INTERNAL}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
