#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 数据可视化技能独立实现

本脚本根据功能规格独立编写，不依赖任何既有代码。
提供核心数据解析、结构化、置信度评估与命令行自检功能。
"""

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请稍后重试",
    "E007": "文件读取失败，请检查文件路径",
    "E008": "数据解析失败，请检查数据格式",
    "E009": "输出生成失败，请检查配置",
    "E010": "参数错误，请检查命令行参数",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ProcessingResult:
    """处理结果数据类"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理逻辑
# ============================================================
class DataProcessor:
    """数据处理器：负责解析、结构化、置信度评估"""

    # 可识别的关键字段（销售数据场景）
    KEY_FIELDS = [
        "日期", "月份", "季度",
        "产品", "品类", "类别",
        "销售额", "销售金额", "金额",
        "数量", "销量",
        "地区", "区域", "城市",
        "客户", "渠道",
    ]

    # 字段别名映射（中英文）
    FIELD_ALIASES = {
        # 日期相关
        "date": "日期",
        "day": "日期",
        "datetime": "日期",
        "time": "日期",
        "month": "月份",
        "quarter": "季度",
        # 产品相关
        "product": "产品",
        "product_name": "产品",
        "item": "产品",
        "goods": "产品",
        "category": "品类",
        "type": "品类",
        # 销售额相关
        "sales": "销售额",
        "sales_amount": "销售额",
        "revenue": "销售额",
        "amount": "销售额",
        "total": "销售额",
        "price": "销售额",
        "money": "销售额",
        # 数量相关
        "quantity": "数量",
        "qty": "数量",
        "count": "数量",
        "num": "数量",
        # 地区相关
        "region": "地区",
        "area": "区域",
        "city": "城市",
        "location": "地区",
        "province": "地区",
        # 客户相关
        "customer": "客户",
        "client": "客户",
        "buyer": "客户",
        # 渠道相关
        "channel": "渠道",
        "source": "渠道",
        # 中文别名
        "日期": "日期",
        "时间": "日期",
        "月份": "月份",
        "季度": "季度",
        "产品": "产品",
        "产品名": "产品",
        "商品": "产品",
        "品类": "品类",
        "类别": "品类",
        "销售额": "销售额",
        "销售金额": "销售额",
        "金额": "销售额",
        "收入": "销售额",
        "数量": "数量",
        "销量": "数量",
        "地区": "地区",
        "区域": "区域",
        "城市": "城市",
        "客户": "客户",
        "渠道": "渠道",
    }

    def __init__(self):
        self.required_fields = ["日期", "产品", "销售额"]

    def parse_input(self, raw_input: Any) -> ProcessingResult:
        """
        解析输入内容，识别关键信息。

        支持：
        - 字符串（JSON/CSV/纯文本）
        - 字典/列表（Python对象）
        - 文件路径（自动读取）
        """
        # 输入为空检查
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            return ProcessingResult(
                success=False,
                error_code="E001",
                error_message=ERROR_CODES["E001"],
            )

        # 处理文件路径
        if isinstance(raw_input, str) and self._is_file_path(raw_input):
            result = self._read_file(raw_input)
            if not result.success:
                return result
            raw_input = result.data

        # 尝试解析JSON
        if isinstance(raw_input, str):
            try:
                parsed = json.loads(raw_input)
                return self._parse_structured(parsed)
            except json.JSONDecodeError:
                # 尝试CSV解析
                try:
                    parsed = self._parse_csv_string(raw_input)
                    return self._parse_structured(parsed)
                except Exception:
                    return ProcessingResult(
                        success=False,
                        error_code="E003",
                        error_message=ERROR_CODES["E003"],
                    )

        # 处理Python对象
        if isinstance(raw_input, (dict, list)):
            return self._parse_structured(raw_input)

        return ProcessingResult(
            success=False,
            error_code="E003",
            error_message=ERROR_CODES["E003"],
        )

    def _is_file_path(self, path: str) -> bool:
        """判断是否为文件路径"""
        # 检查常见文件扩展名
        common_extensions = [".csv", ".json", ".txt", ".xlsx", ".xls"]
        has_extension = any(path.lower().endswith(ext) for ext in common_extensions)
        # 检查路径是否存在
        exists = os.path.exists(path)
        return has_extension or exists

    def _read_file(self, file_path: str) -> ProcessingResult:
        """读取文件内容"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ProcessingResult(success=True, data=content)
        except FileNotFoundError:
            return ProcessingResult(
                success=False,
                error_code="E007",
                error_message=ERROR_CODES["E007"],
            )
        except Exception:
            return ProcessingResult(
                success=False,
                error_code="E008",
                error_message=ERROR_CODES["E008"],
            )

    def _parse_csv_string(self, csv_str: str) -> List[Dict[str, str]]:
        """解析CSV字符串为字典列表"""
        csv_file = io.StringIO(csv_str)
        reader = csv.DictReader(csv_file)
        rows = []
        for row in reader:
            if row:  # 跳过空行
                rows.append(dict(row))
        return rows

    def _parse_structured(self, data: Any) -> ProcessingResult:
        """解析结构化数据"""
        # 统一为字典列表
        rows = []
        if isinstance(data, dict):
            # 单条记录
            if "数据" in data or "records" in data or "data" in data:
                # 嵌套记录
                records = data.get("数据") or data.get("records") or data.get("data", [])
                if isinstance(records, list):
                    rows = records
                else:
                    rows = [records]
            else:
                # 单条记录
                rows = [data]
        elif isinstance(data, list):
            rows = data

        if not rows:
            return ProcessingResult(
                success=False,
                error_code="E002",
                error_message=ERROR_CODES["E002"] + "未找到有效数据记录",
            )

        # 规范化字段名
        normalized_rows = []
        for row in rows:
            if isinstance(row, dict):
                normalized = self._normalize_fields(row)
                normalized_rows.append(normalized)

        if not normalized_rows:
            return ProcessingResult(
                success=False,
                error_code="E003",
                error_message=ERROR_CODES["E003"],
            )

        # 检查关键信息
        missing = self._check_required_fields(normalized_rows)
        if missing:
            return ProcessingResult(
                success=False,
                error_code="E002",
                error_message=ERROR_CODES["E002"] + f"缺少字段: {', '.join(missing)}",
            )

        # 评估置信度
        confidence = self._evaluate_confidence(normalized_rows)

        # 生成结构化结果
        result_data = {
            "records": normalized_rows,
            "total_records": len(normalized_rows),
            "fields": self._extract_fields(normalized_rows),
            "summary": self._generate_summary(normalized_rows),
        }

        return ProcessingResult(
            success=True,
            data=result_data,
            confidence=confidence,
        )

    def _normalize_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """规范化字段名"""
        normalized = {}
        for key, value in row.items():
            if not key:
                continue
            # 转换字段名
            new_key = self._normalize_field_name(key)
            # 如果新key已存在，保留原有值（避免覆盖）
            if new_key not in normalized:
                normalized[new_key] = value
            else:
                # 如果字段已存在，尝试合并或保留第一个
                normalized[new_key] = normalized[new_key] if normalized[new_key] else value
        return normalized

    def _normalize_field_name(self, field_name: str) -> str:
        """规范化单个字段名"""
        # 去除空白并转为小写
        name = str(field_name).strip().lower()
        
        # 检查别名映射（优先使用小写匹配）
        if name in self.FIELD_ALIASES:
            return self.FIELD_ALIASES[name]
        
        # 检查原始格式（保留大小写）
        original = str(field_name).strip()
        if original in self.FIELD_ALIASES:
            return self.FIELD_ALIASES[original]
        
        # 尝试部分匹配（如果字段名包含关键信息）
        for alias, standard in self.FIELD_ALIASES.items():
            if alias in name:
                return standard
        
        # 直接返回原名（保留原始格式）
        return original

    def _check_required_fields(self, rows: List[Dict[str, Any]]) -> List[str]:
        """检查必需字段是否存在"""
        if not rows:
            return self.required_fields

        # 检查所有记录，确保所有必需字段都存在
        missing = set()
        for row in rows:
            for field in self.required_fields:
                if field not in row:
                    missing.add(field)
        
        return list(missing)

    def _evaluate_confidence(self, rows: List[Dict[str, Any]]) -> float:
        """评估数据置信度"""
        score = 0.0
        total_fields = len(rows[0]) if rows else 0

        # 字段完整性得分（40%）
        if rows:
            field_coverage = total_fields / max(len(self.required_fields), 1)
            score += min(field_coverage, 1.0) * 0.4

        # 数据一致性得分（30%）
        if rows:
            has_date = "日期" in rows[0]
            has_product = "产品" in rows[0]
            has_sales = "销售额" in rows[0]
            consistency = sum([has_date, has_product, has_sales]) / 3
            score += consistency * 0.3

        # 数据量得分（30%）
        if rows:
            # 10条以上数据视为充分
            volume_score = min(len(rows) / 10, 1.0)
            score += volume_score * 0.3

        return round(score, 2)

    def _extract_fields(self, rows: List[Dict[str, Any]]) -> List[str]:
        """提取所有字段名"""
        fields = set()
        for row in rows:
            fields.update(row.keys())
        return sorted(fields)

    def _generate_summary(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成数据摘要"""
        summary = {
            "record_count": len(rows),
            "unique_products": set(),
            "total_sales": 0.0,
            "date_range": [None, None],
        }

        for row in rows:
            # 统计产品
            if "产品" in row:
                summary["unique_products"].add(row["产品"])

            # 统计销售额
            if "销售额" in row:
                try:
                    sales = float(row["销售额"])
                    summary["total_sales"] += sales
                except (ValueError, TypeError):
                    pass

            # 统计日期范围
            if "日期" in row:
                date_val = row["日期"]
                if summary["date_range"][0] is None or date_val < summary["date_range"][0]:
                    summary["date_range"][0] = date_val
                if summary["date_range"][1] is None or date_val > summary["date_range"][1]:
                    summary["date_range"][1] = date_val

        # 转换set为list
        summary["unique_products"] = list(summary["unique_products"])
        return summary

    def format_output(self, result: ProcessingResult, output_format: str = "text") -> ProcessingResult:
        """格式化输出"""
        if not result.success:
            return result

        try:
            if output_format == "json":
                output = json.dumps(result.data, ensure_ascii=False, indent=2)
            elif output_format == "text":
                output = self._format_as_text(result.data)
            else:
                return ProcessingResult(
                    success=False,
                    error_code="E009",
                    error_message=ERROR_CODES["E009"],
                )

            result.data["formatted_output"] = output
            return result

        except Exception:
            return ProcessingResult(
                success=False,
                error_code="E009",
                error_message=ERROR_CODES["E009"],
            )

    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """格式化为文本输出"""
        lines = []
        lines.append("=" * 60)
        lines.append("数据可视化结果")
        lines.append("=" * 60)

        # 摘要信息
        summary = data.get("summary", {})
        lines.append(f"记录数: {summary.get('record_count', 0)}")
        lines.append(f"产品数: {len(summary.get('unique_products', []))}")
        lines.append(f"总销售额: {summary.get('total_sales', 0):.2f}")

        date_range = summary.get("date_range", [None, None])
        if date_range[0] and date_range[1]:
            lines.append(f"日期范围: {date_range[0]} ~ {date_range[1]}")

        # 字段信息
        fields = data.get("fields", [])
        if fields:
            lines.append(f"字段: {', '.join(fields)}")

        # 数据预览
        records = data.get("records", [])
        if records:
            lines.append("\n数据预览:")
            preview_count = min(5, len(records))
            for i, record in enumerate(records[:preview_count]):
                lines.append(f"  [{i+1}] {record}")

        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    内置自检功能：使用硬编码样例数据验证核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    """
    print("开始自检...")

    # 创建处理器
    processor = DataProcessor()

    # 测试用例1: 正常数据（JSON格式）
    print("\n[测试1] JSON格式数据处理")
    test_data_json = json.dumps({
        "records": [
            {"日期": "2024-01-01", "产品": "手机", "销售额": "5000", "地区": "北京"},
            {"日期": "2024-01-02", "产品": "电脑", "销售额": "8000", "地区": "上海"},
            {"日期": "2024-01-03", "产品": "手机", "销售额": "4500", "地区": "广州"},
            {"日期": "2024-01-04", "产品": "平板", "销售额": "3000", "地区": "深圳"},
            {"日期": "2024-01-05", "产品": "电脑", "销售额": "7500", "地区": "北京"},
        ]
    })
    result = processor.parse_input(test_data_json)
    assert result.success, f"JSON解析失败: {result.error_message}"
    assert result.confidence > 0.5, f"置信度异常: {result.confidence}"
    assert result.data["total_records"] == 5, f"记录数错误: {result.data['total_records']}"
    assert result.data["summary"]["total_sales"] > 25000, "销售额汇总异常"
    assert len(result.data["summary"]["unique_products"]) >= 3, "产品数异常"
    print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")

    # 测试用例2: CSV格式处理
    print("\n[测试2] CSV格式数据处理")
    test_csv = """日期,产品,销售额,地区
2024-02-01,手机,6000,北京
2024-02-02,电脑,9000,上海
2024-02-03,手机,5500,广州
2024-02-04,平板,3500,深圳
"""
    result = processor.parse_input(test_csv)
    assert result.success, f"CSV解析失败: {result.error_message}"
    assert result.data["total_records"] == 4, f"记录数错误: {result.data['total_records']}"
    assert result.data["summary"]["total_sales"] > 20000, "销售额汇总异常"
    print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")

    # 测试用例3: 字段别名处理
    print("\n[测试3] 字段别名处理")
    test_alias = json.dumps([
        {"date": "2024-03-01", "product": "手机", "amount": "7000"},
        {"date": "2024-03-02", "product": "电脑", "amount": "8500"},
    ])
    result = processor.parse_input(test_alias)
    assert result.success, f"别名解析失败: {result.error_message}"
    assert "日期" in result.data["fields"], "日期字段未正确映射"
    assert "产品" in result.data["fields"], "产品字段未正确映射"
    assert "销售额" in result.data["fields"], "销售额字段未正确映射"
    print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")

    # 测试用例4: 空输入处理
    print("\n[测试4] 空输入处理")
    result = processor.parse_input("")
    assert not result.success, "空输入应该失败"
    assert result.error_code == "E001", f"错误码错误: {result.error_code}"
    print(f"  ✓ 通过 (错误码: {result.error_code})")

    # 测试用例5: 缺少必需字段
    print("\n[测试5] 缺少必需字段")
    test_missing = json.dumps([
        {"产品": "手机", "销售额": "1000"},
        {"产品": "电脑", "销售额": "2000"},
    ])
    result = processor.parse_input(test_missing)
    assert not result.success, "缺少字段应该失败"
    assert result.error_code == "E002", f"错误码错误: {result.error_code}"
    print(f"  ✓ 通过 (错误码: {result.error_code})")

    # 测试用例6: 输出格式化
    print("\n[测试6] 输出格式化")
    result = processor.parse_input(test_data_json)
    assert result.success, "解析失败"
    result = processor.format_output(result, "json")
    assert result.success, "JSON格式化失败"
    assert "formatted_output" in result.data, "缺少格式化输出"
    result = processor.format_output(result, "text")
    assert result.success, "文本格式化失败"
    print("  ✓ 通过")

    # 测试用例7: 错误输入
    print("\n[测试7] 错误输入处理")
    result = processor.parse_input("这不是有效的JSON或CSV格式")
    assert not result.success, "无效输入应该失败"
    assert result.error_code in ["E003", "E008"], f"错误码错误: {result.error_code}"
    print(f"  ✓ 通过 (错误码: {result.error_code})")

    # 测试用例8: 边界情况 - 大量数据
    print("\n[测试8] 大量数据处理")
    large_data = []
    for i in range(50):
        large_data.append({
            "日期": f"2024-06-{i+1:02d}",
            "产品": f"产品{i % 5}",
            "销售额": str((i + 1) * 100),
        })
    result = processor.parse_input(json.dumps(large_data))
    assert result.success, "大量数据处理失败"
    assert result.data["total_records"] == 50, f"记录数错误: {result.data['total_records']}"
    assert result.confidence > 0.8, f"置信度应较高: {result.confidence}"
    print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")

    print("\n" + "=" * 60)
    print("所有自检测试通过!")
    print("=" * 60)
    return True


# ============================================================
# 主程序
# ============================================================
def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="数据可视化技能 - 独立实现",
        epilog="示例: python main.py --input '{\"records\": [{\"日期\": \"2024-01-01\", \"产品\": \"手机\", \"销售额\": \"5000\"}]}'"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入数据（JSON/CSV字符串或文件路径）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"\n自检失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n自检异常: {e}")
            sys.exit(1)

    # 正常处理模式
    if not args.input:
        print(f"错误 (E010): {ERROR_CODES['E010']}", file=sys.stderr)
        print("请使用 --input 提供数据，或使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)

    # 创建处理器并处理
    processor = DataProcessor()

    # 解析输入
    result = processor.parse_input(args.input)
    if not result.success:
        print(f"错误 ({result.error_code}): {result.error_message}", file=sys.stderr)
        sys.exit(1)

    # 格式化输出
    result = processor.format_output(result, args.format)
    if not result.success:
        print(f"错误 ({result.error_code}): {result.error_message}", file=sys.stderr)
        sys.exit(1)

    # 输出结果
    if args.format == "json":
        print(json.dumps(result.data, ensure_ascii=False, indent=2))
    else:
        print(result.data["formatted_output"])

    # 输出置信度提示
    confidence = result.confidence
    if confidence >= 0.9:
        print(f"\n置信度: {confidence:.0%} - 可直接使用")
    elif confidence >= 0.85:
        print(f"\n置信度: {confidence:.0%} - 建议复核")
    else:
        print(f"\n置信度: {confidence:.0%} - [需核实] 结果可能不准确")

    sys.exit(0)


if __name__ == "__main__":
    main()
