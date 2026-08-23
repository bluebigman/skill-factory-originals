#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
datart - 数据可视化开放平台图表构建助手
版本: 1.0.2
仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import csv
import io
import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
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
            # 类型推断：尝试将数值字段转换为 float/int
            records = DataParser._infer_types(records)
            return records
        except DatartError:
            raise
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
            # 类型推断
            records = DataParser._infer_types(records)
            return records
        except json.JSONDecodeError as e:
            raise DatartError("E007", f"JSON 解析失败: {e}")

    @staticmethod
    def _infer_types(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """推断字段类型：尝试将字符串转换为数值或日期类型。"""
        if not records:
            return records

        # 获取所有字段
        fields = list(records[0].keys())
        for field in fields:
            # 检查该字段的所有值
            values = [r.get(field) for r in records if r.get(field) is not None]
            if not values:
                continue

            # 尝试转换为数值
            numeric_values = []
            all_numeric = True
            for v in values:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    all_numeric = False
                    break

            if all_numeric and numeric_values:
                # 判断是 int 还是 float
                all_int = all(float(v).is_integer() for v in numeric_values)
                for r in records:
                    if r.get(field) is not None:
                        if all_int:
                            r[field] = int(float(r[field]))
                        else:
                            r[field] = float(r[field])
                continue

            # 尝试转换为日期时间
            try:
                datetime_values = []
                for v in values:
                    dt = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
                    datetime_values.append(dt)
                if datetime_values:
                    for r in records:
                        if r.get(field) is not None:
                            r[field] = datetime.fromisoformat(str(r[field]).replace('Z', '+00:00'))
                    continue
            except (ValueError, TypeError):
                pass

        return records

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

    @staticmethod
    def parse_url(url: str, fmt: str = "csv", timeout: int = 10, max_retries: int = 3) -> List[Dict[str, Any]]:
        """从 URL 下载并解析数据。"""
        if not url.startswith(('http://', 'https://')):
            raise DatartError("E006", f"无效的 URL: {url}")

        last_error = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'datart/1.0.2'})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8')
                return DataParser.parse_text(content, fmt)
            except urllib.error.URLError as e:
                last_error = e
                if attempt < max_retries - 1:
                    # 指数退避
                    wait_time = 2 ** attempt
                    print(f"  ⚠️ URL 请求失败（第 {attempt + 1} 次），{wait_time} 秒后重试...")
                    time.sleep(wait_time)
            except Exception as e:
                raise DatartError("E006", f"URL 数据获取失败: {e}")

        raise DatartError("E006", f"URL 请求失败（已重试 {max_retries} 次）: {last_error}")


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
                if f != x_field and ChartConfigGenerator._is_numeric_column(records, f):
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
                "version": "1.0.2",
                "generated_at": datetime.now(timezone.utc).isoformat(),
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
            # 1. 检查数据源数量
            if len(data_inputs) > MultiSourceMerger.MAX_SOURCES:
                raise DatartError("E009", f"最多支持 {MultiSourceMerger.MAX_SOURCES} 个数据源")

            # 2. 解析所有数据源
            sources = []
            for data_input in data_inputs:
                if data_input.startswith(('http://', 'https://')):
                    # URL 数据源
                    records = DataParser.parse_url(data_input, input_format)
                elif os.path.isfile(data_input):
                    # 文件数据源
                    records = DataParser.parse_file(data_input, input_format)
                else:
                    # 文本数据源
                    records = DataParser.parse_text(data_input, input_format)
                sources.append(records)

            # 3. 合并数据源
            merged = MultiSourceMerger.merge(sources)

            # 4. 数据清洗
            if clean_rules:
                merged = DataCleaner.clean(merged, clean_rules)

            # 5. 生成图表配置
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

    # ---------- 测试 1: CSV 解析与类型推断 ----------
    print("\n[测试 1] CSV 解析与类型推断")
    csv_text = """name,age,score
Alice,25,85.5
Bob,30,92.3
Charlie,35,78.9"""
    try:
        records = DataParser.parse_text(csv_text, "csv")
        assert len(records) == 3, f"期望 3 条记录，实际 {len(records)}"
        assert records[0]["name"] == "Alice", "第一条记录名称错误"
        assert isinstance(records[0]["age"], int), "age 字段应为 int 类型"
        assert isinstance(records[0]["score"], float), "score 字段应为 float 类型"
        print("  ✓ CSV 解析与类型推断正常")
    except Exception as e:
        print(f"  ✗ CSV 解析与类型推断失败: {e}")
        return False

    # ---------- 测试 2: JSON 解析与类型推断 ----------
    print("\n[测试 2] JSON 解析与类型推断")
    json_text = '[{"name":"A","value":10},{"name":"B","value":20.5}]'
    try:
        records = DataParser.parse_text(json_text, "json")
        assert len(records) == 2, f"期望 2 条记录，实际 {len(records)}"
        assert isinstance(records[0]["value"], int), "value 字段应为 int 类型"
        assert isinstance(records[1]["value"], float), "value 字段应为 float 类型"
        print("  ✓ JSON 解析与类型推断正常")
    except Exception as e:
        print(f"  ✗ JSON 解析与类型推断失败: {e}")
        return False
