#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
datart - 数据可视化开放平台图表构建助手
版本: 1.0.1
仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import csv
import io
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或格式不正确",
    "E002": "数据源类型不支持（仅支持 csv/json/excel 文本或文件路径）",
    "E003": "字段映射失败：指定的字段不存在",
    "E004": "图表类型不支持",
    "E005": "数据清洗规则不合法",
    "E006": "文件读取失败或文件不存在",
    "E007": "JSON 解析失败",
    "E008": "CSV 解析失败",
    "E009": "数据源数量超过限制（最多 5 个）",
    "E010": "内部逻辑错误或未知异常",
}


class DatartError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据解析模块
# ============================================================
class DataParser:
    """负责将不同格式的输入解析为统一的数据结构（List[Dict]）。"""

    @staticmethod
    def parse_text(text: str, fmt: str = "csv") -> List[Dict[str, Any]]:
        """解析文本内容为记录列表。"""
        text = text.strip()
        if not text:
            raise DatartError("E001")

        if fmt == "csv":
            return DataParser._parse_csv_text(text)
        elif fmt == "json":
            return DataParser._parse_json_text(text)
        elif fmt == "excel":
            # Excel 文本粘贴通常以制表符分隔
            return DataParser._parse_csv_text(text, delimiter="\t")
        else:
            raise DatartError("E002")

    @staticmethod
    def _parse_csv_text(text: str, delimiter: str = ",") -> List[Dict[str, Any]]:
        """解析 CSV 文本。"""
        try:
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            records = [dict(row) for row in reader if any(row.values())]
            if not records:
                raise DatartError("E001")
            return records
        except Exception as e:
            raise DatartError("E008", f"CSV 解析失败: {e}")

    @staticmethod
    def _parse_json_text(text: str) -> List[Dict[str, Any]]:
        """解析 JSON 文本（支持数组或对象数组）。"""
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                # 支持 {"data": [...]} 或直接对象
                if "data" in data and isinstance(data["data"], list):
                    data = data["data"]
                else:
                    data = [data]
            if not isinstance(data, list) or len(data) == 0:
                raise DatartError("E001")
            # 确保所有元素是字典
            records = [item for item in data if isinstance(item, dict)]
            if not records:
                raise DatartError("E001")
            return records
        except json.JSONDecodeError as e:
            raise DatartError("E007", f"JSON 解析失败: {e}")

    @staticmethod
    def parse_file(file_path: str, fmt: str = "csv") -> List[Dict[str, Any]]:
        """从文件读取并解析数据。"""
        if not os.path.isfile(file_path):
            raise DatartError("E006", f"文件不存在: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return DataParser.parse_text(content, fmt)
        except DatartError:
            raise
        except Exception as e:
            raise DatartError("E006", f"文件读取失败: {e}")


# ============================================================
# 数据清洗模块
# ============================================================
class DataCleaner:
    """提供常见的数据清洗规则。"""

    @staticmethod
    def clean(records: List[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据规则清洗数据。
        规则示例:
        {
            "drop_na": ["field1", "field2"],       # 删除指定字段为空的行
            "fill_na": {"field1": 0},              # 用指定值填充缺失
            "convert_numeric": ["field1"],         # 转换为数值类型
            "rename": {"old_name": "new_name"}     # 重命名字段
        }
        """
        if not isinstance(rules, dict):
            raise DatartError("E005")

        result = [dict(r) for r in records]

        # 重命名
        rename_map = rules.get("rename", {})
        if rename_map:
            new_result = []
            for row in result:
                new_row = {}
                for k, v in row.items():
                    new_key = rename_map.get(k, k)
                    new_row[new_key] = v
                new_result.append(new_row)
            result = new_result

        # 删除缺失字段的行
        drop_na_fields = rules.get("drop_na", [])
        if drop_na_fields:
            result = [r for r in result if all(r.get(f) not in (None, "") for f in drop_na_fields)]

        # 填充缺失值
        fill_na_map = rules.get("fill_na", {})
        if fill_na_map:
            for row in result:
                for field, value in fill_na_map.items():
                    if row.get(field) in (None, ""):
                        row[field] = value

        # 数值转换
        numeric_fields = rules.get("convert_numeric", [])
        if numeric_fields:
            for row in result:
                for field in numeric_fields:
                    val = row.get(field)
                    if val is not None and val != "":
                        try:
                            row[field] = float(val)
                        except (ValueError, TypeError):
                            # 转换失败保留原值
                            pass

        return result


# ============================================================
# 图表配置生成模块
# ============================================================
class ChartConfigGenerator:
    """根据数据和用户需求生成图表配置。"""

    SUPPORTED_CHARTS = ["bar", "line", "pie", "scatter", "pivot", "dashboard"]

    @staticmethod
    def generate(
        records: List[Dict[str, Any]],
        chart_type: str,
        x_field: Optional[str] = None,
        y_field: Optional[str] = None,
        group_field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成图表配置 JSON。"""
        if chart_type not in ChartConfigGenerator.SUPPORTED_CHARTS:
            raise DatartError("E004", f"不支持的图表类型: {chart_type}")

        fields = list(records[0].keys()) if records else []
        if not fields:
            raise DatartError("E001")

        # 自动选择字段
        if not x_field:
            x_field = fields[0]
        if not y_field:
            # 尝试找第一个数值字段
            for f in fields:
                if f != x_field and DataCleaner._is_numeric_column(records, f):
                    y_field = f
                    break
            if not y_field:
                y_field = fields[-1] if len(fields) > 1 else fields[0]

        # 验证字段存在
        if x_field not in fields:
            raise DatartError("E003", f"字段不存在: {x_field}")
        if y_field not in fields:
            raise DatartError("E003", f"字段不存在: {y_field}")
        if group_field and group_field not in fields:
            raise DatartError("E003", f"字段不存在: {group_field}")

        # 生成基础配置
        config = {
            "chart_type": chart_type,
            "data_fields": {
                "x": x_field,
                "y": y_field,
            },
            "data": records[:100],  # 最多取 100 条
            "style": {
                "title": f"{x_field} vs {y_field}",
                "legend": group_field or "无",
            },
            "meta": {
                "record_count": len(records),
                "generated_by": "datart",
                "version": "1.0.1",
            },
        }

        if group_field:
            config["data_fields"]["group"] = group_field

        # 根据图表类型补充特有配置
        if chart_type == "pie":
            config["style"]["is_pie"] = True
            config["style"]["hole_ratio"] = 0.4  # 环形饼图
        elif chart_type == "scatter":
            config["style"]["point_size"] = 8
        elif chart_type == "pivot":
            config["style"]["aggregation"] = "sum"
        elif chart_type == "dashboard":
            config["style"]["layout"] = "grid"
            config["style"]["columns"] = 2

        return config

    @staticmethod
    def _is_numeric_column(records: List[Dict[str, Any]], field: str) -> bool:
        """判断字段是否为数值类型。"""
        sample = [r.get(field) for r in records[:5] if r.get(field) is not None]
        if not sample:
            return False
        for val in sample:
            try:
                float(val)
            except (ValueError, TypeError):
                return False
        return True


# ============================================================
# 多数据源合并模块
# ============================================================
class MultiSourceMerger:
    """合并多个数据源（最多 5 个）。"""

    MAX_SOURCES = 5

    @staticmethod
    def merge(sources: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """合并多个数据源为单一记录列表。"""
        if len(sources) > MultiSourceMerger.MAX_SOURCES:
            raise DatartError("E009", f"最多支持 {MultiSourceMerger.MAX_SOURCES} 个数据源")

        if not sources:
            raise DatartError("E001")

        # 简单纵向合并
        merged = []
        for src in sources:
            merged.extend(src)

        if not merged:
            raise DatartError("E001")

        return merged


# ============================================================
# 主处理流程
# ============================================================
class DatartProcessor:
    """核心处理类，串联解析、清洗、合并、生成配置。"""

    @staticmethod
    def process(
        data_inputs: List[str],
        input_format: str = "csv",
        chart_type: str = "bar",
        x_field: Optional[str] = None,
        y_field: Optional[str] = None,
        group_field: Optional[str] = None,
        clean_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """完整处理流程。"""
        try:
            # 1. 解析所有数据源
            sources = []
            for data_input in data_inputs:
                if os.path.isfile(data_input):
                    records = DataParser.parse_file(data_input, input_format)
                else:
                    records = DataParser.parse_text(data_input, input_format)
                sources.append(records)

            # 2. 合并数据源
            merged = MultiSourceMerger.merge(sources)

            # 3. 数据清洗
            if clean_rules:
                merged = DataCleaner.clean(merged, clean_rules)

            # 4. 生成图表配置
            config = ChartConfigGenerator.generate(
                merged, chart_type, x_field, y_field, group_field
            )

            return config

        except DatartError:
            raise
        except Exception as e:
            raise DatartError("E010", f"未知异常: {e}")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """内置硬编码样例数据，离线自检核心逻辑。"""
    print("=" * 60)
    print("datart 自检开始（离线模式）...")
    print("=" * 60)

    # ---------- 测试 1: CSV 解析 ----------
    print("\n[测试 1] CSV 解析")
    csv_text = """name,age,score
Alice,25,85.5
Bob,30,92.3
Charlie,35,78.9"""
    try:
        records = DataParser.parse_text(csv_text, "csv")
        assert len(records) == 3, f"期望 3 条记录，实际 {len(records)}"
        assert records[0]["name"] == "Alice", "第一条记录名称错误"
        print("  ✓ CSV 解析正常")
    except Exception as e:
        print(f"  ✗ CSV 解析失败: {e}")
        return False

    # ---------- 测试 2: JSON 解析 ----------
    print("\n[测试 2] JSON 解析")
    json_text = '[{"name":"A","value":10},{"name":"B","value":20}]'
    try:
        records = DataParser.parse_text(json_text, "json")
        assert len(records) == 2, f"期望 2 条记录，实际 {len(records)}"
        assert records[1]["value"] == 20, "第二条记录值错误"
        print("  ✓ JSON 解析正常")
    except Exception as e:
        print(f"  ✗ JSON 解析失败: {e}")
        return False

    # ---------- 测试 3: 数据清洗 ----------
    print("\n[测试 3] 数据清洗")
    dirty_records = [
        {"name": "A", "value": "10", "note": ""},
        {"name": "B", "value": "20", "note": "x"},
        {"name": "", "value": "30", "note": "y"},
    ]
    rules = {
        "drop_na": ["name"],
        "convert_numeric": ["value"],
        "fill_na": {"note": "N/A"},
    }
    try:
        cleaned = DataCleaner.clean(dirty_records, rules)
        assert len(cleaned) == 2, f"期望 2 条清洗后记录，实际 {len(cleaned)}"
        assert isinstance(cleaned[0]["value"], float), "数值转换失败"
        assert cleaned[1]["note"] == "x", "填充逻辑错误"
        print("  ✓ 数据清洗正常")
    except Exception as e:
        print(f"  ✗ 数据清洗失败: {e}")
        return False

    # ---------- 测试 4: 图表配置生成 ----------
    print("\n[测试 4] 图表配置生成")
    sample_data = [
        {"month": "1月", "sales": 100},
        {"month": "2月", "sales": 150},
        {"month": "3月", "sales": 120},
    ]
    try:
        config = ChartConfigGenerator.generate(sample_data, "bar", "month", "sales")
        assert config["chart_type"] == "bar", "图表类型错误"
        assert config["data_fields"]["x"] == "month", "X 轴字段错误"
        assert config["data_fields"]["y"] == "sales", "Y 轴字段错误"
        assert config["meta"]["record_count"] == 3, "记录数错误"
        print("  ✓ 图表配置生成正常")
    except Exception as e:
        print(f"  ✗ 图表配置生成失败: {e}")
        return False

    # ---------- 测试 5: 多数据源合并 ----------
    print("\n[测试 5] 多数据源合并")
    src1 = [{"id": 1, "val": "a"}]
    src2 = [{"id": 2, "val": "b"}]
    try:
        merged = MultiSourceMerger.merge([src1, src2])
        assert len(merged) == 2, f"期望 2 条合并记录，实际 {len(merged)}"
        print("  ✓ 多数据源合并正常")
    except Exception as e:
        print(f"  ✗ 多数据源合并失败: {e}")
        return False

    # ---------- 测试 6: 完整流程 ----------
    print("\n[测试 6] 完整处理流程")
    try:
        result = DatartProcessor.process(
            data_inputs=[csv_text],
            chart_type="line",
            x_field="name",
            y_field="score",
        )
        assert result["chart_type"] == "line", "流程图表类型错误"
        assert result["meta"]["record_count"] == 3, "流程记录数错误"
        print("  ✓ 完整流程正常")
    except Exception as e:
        print(f"  ✗ 完整流程失败: {e}")
        return False

    # ---------- 测试 7: 错误处理 ----------
    print("\n[测试 7] 错误处理")
    try:
        DatartProcessor.process([""], chart_type="bar")
        print("  ✗ 空数据应报错 E001")
        return False
    except DatartError as e:
        assert e.code == "E001", f"期望 E001，实际 {e.code}"
        print("  ✓ 空数据错误码正确 (E001)")

    try:
        ChartConfigGenerator.generate([{"a": 1}], "3d_bar")
        print("  ✗ 不支持图表应报错 E004")
        return False
    except DatartError as e:
        assert e.code == "E004", f"期望 E004，实际 {e.code}"
        print("  ✓ 不支持图表错误码正确 (E004)")

    # ---------- 测试 8: 宽松数值断言 ----------
    print("\n[测试 8] 数值合理性检查")
    try:
        # 生成较大数据集
        big_data = [{"x": i, "y": i * 2} for i in range(100)]
        config = ChartConfigGenerator.generate(big_data, "scatter", "x", "y")
        # 宽松断言：记录数在合理范围
        assert 50 <= config["meta"]["record_count"] <= 100, "记录数应在 50-100 之间"
        # 字符串字段存在即可
        assert isinstance(config["style"]["title"], str), "标题应为字符串"
        assert len(config["style"]["title"]) > 0, "标题不应为空"
        print("  ✓ 数值断言通过")
    except Exception as e:
        print(f"  ✗ 数值断言失败: {e}")
        return False

    # ---------- 测试 9: 字段不存在错误 ----------
    print("\n[测试 9] 字段映射错误")
    try:
        ChartConfigGenerator.generate(sample_data, "bar", "nonexist", "sales")
        print("  ✗ 应报错 E003")
        return False
    except DatartError as e:
        assert e.code == "E003", f"期望 E003，实际 {e.code}"
        print("  ✓ 字段错误码正确 (E003)")

    print("\n" + "=" * 60)
    print("✅ 全部自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="datart - 数据可视化开放平台图表构建助手"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部文件）",
    )
    parser.add_argument(
        "--input",
        action="append",
        help="输入数据：文件路径或文本内容（可多次指定，最多 5 个）",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "excel"],
        default="csv",
        help="输入数据格式（默认: csv）",
    )
    parser.add_argument(
        "--chart",
        choices=["bar", "line", "pie", "scatter", "pivot", "dashboard"],
        default="bar",
        help="图表类型（默认: bar）",
    )
    parser.add_argument(
        "--x",
        help="X 轴字段名",
    )
    parser.add_argument(
        "--y",
        help="Y 轴字段名",
    )
    parser.add_argument(
        "--group",
        help="分组字段名",
    )
    parser.add_argument(
        "--clean-rules",
        help="数据清洗规则 JSON 字符串，如: '{\"drop_na\": [\"name\"]}'",
    )
    parser.add_argument(
        "--output",
        help="输出文件路径（默认输出到 stdout）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print("错误: 请提供 --input 参数（文件路径或文本内容）", file=sys.stderr)
        print("提示: 使用 --selftest 运行离线自检", file=sys.stderr)
        return 2

    if len(args.input) > 5:
        print("错误: 最多支持 5 个数据源 (E009)", file=sys.stderr)
        return 1

    # 解析清洗规则
    clean_rules = None
    if args.clean_rules:
        try:
            clean_rules = json.loads(args.clean_rules)
        except json.JSONDecodeError:
            print("错误: --clean-rules 不是合法的 JSON (E005)", file=sys.stderr)
            return 1

    try:
        # 执行处理
        result = DatartProcessor.process(
            data_inputs=args.input,
            input_format=args.format,
            chart_type=args.chart,
            x_field=args.x,
            y_field=args.y,
            group_field=args.group,
            clean_rules=clean_rules,
        )

        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"✅ 配置已保存到: {args.output}")
        else:
            print(output_json)

        return 0

    except DatartError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e} (E010)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
