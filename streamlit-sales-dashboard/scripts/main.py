#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
数据可视化技能 - 独立实现脚本

本脚本根据功能规格独立编写，用于处理数据可视化相关任务。
仅依赖 Python 标准库，离线可用。
"""

import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件读取失败",
    "E007": "数据解析失败",
    "E008": "输出写入失败",
    "E009": "参数校验失败",
    "E010": "内部错误",
}


class SkillError(Exception):
    """技能异常基类"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class SalesRecord:
    """销售记录数据模型"""
    date: str
    region: str
    product: str
    quantity: int
    unit_price: float
    revenue: float = field(init=False)

    def __post_init__(self):
        """计算营收"""
        self.revenue = self.quantity * self.unit_price


@dataclass
class DashboardData:
    """仪表盘数据模型"""
    records: List[SalesRecord]
    filters: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 核心处理类
# ============================================================
class DataProcessor:
    """数据处理核心类"""

    # 支持的输入格式
    SUPPORTED_FORMATS = ["json", "csv"]

    def __init__(self):
        self.data: Optional[DashboardData] = None

    def process_input(self, raw_input: Any, input_format: str = "auto") -> DashboardData:
        """处理输入数据，返回结构化结果

        Args:
            raw_input: 原始输入数据
            input_format: 输入格式 (json/csv/auto)

        Returns:
            DashboardData: 处理后的数据

        Raises:
            SkillError: 处理失败时抛出对应错误码
        """
        # E001: 输入为空
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            raise SkillError("E001")

        # 自动检测格式
        if input_format == "auto":
            input_format = self._detect_format(raw_input)

        # E003: 不支持的格式
        if input_format not in self.SUPPORTED_FORMATS:
            raise SkillError("E003", f"不支持的输入格式: {input_format}")

        try:
            if input_format == "json":
                records = self._parse_json(raw_input)
            elif input_format == "csv":
                records = self._parse_csv(raw_input)
            else:
                raise SkillError("E003", "未知格式")
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E007", f"数据解析失败: {str(e)}")

        # E001: 解析后无数据
        if not records:
            raise SkillError("E001")

        # 构建仪表盘数据
        self.data = DashboardData(records=records)
        return self.data

    def _detect_format(self, raw_input: Any) -> str:
        """检测输入格式"""
        if isinstance(raw_input, str):
            stripped = raw_input.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                return "json"
            elif "," in stripped and "\n" in stripped:
                return "csv"
        elif isinstance(raw_input, (list, dict)):
            return "json"
        return "json"  # 默认按 JSON 处理

    def _parse_json(self, raw_input: Any) -> List[SalesRecord]:
        """解析 JSON 数据"""
        if isinstance(raw_input, str):
            data = json.loads(raw_input)
        else:
            data = raw_input

        records = []
        items = data if isinstance(data, list) else data.get("records", [])
        for item in items:
            record = self._create_record(item)
            if record:
                records.append(record)
        return records

    def _parse_csv(self, raw_input: Any) -> List[SalesRecord]:
        """解析 CSV 数据"""
        if isinstance(raw_input, str):
            csv_data = raw_input
        else:
            raise SkillError("E003", "CSV 数据必须为字符串")

        records = []
        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            record = self._create_record(row)
            if record:
                records.append(record)
        return records

    def _create_record(self, item: Dict[str, Any]) -> Optional[SalesRecord]:
        """从字典创建销售记录"""
        try:
            # 查找必填字段（支持不同字段名）
            date = self._find_field(item, ["date", "日期", "时间"])
            region = self._find_field(item, ["region", "地区", "区域"])
            product = self._find_field(item, ["product", "产品", "商品"])
            quantity = self._find_field(item, ["quantity", "数量", "销量"])
            unit_price = self._find_field(item, ["unit_price", "单价", "价格"])

            # E002: 关键信息缺失
            if not all([date, region, product, quantity is not None, unit_price is not None]):
                return None

            return SalesRecord(
                date=str(date),
                region=str(region),
                product=str(product),
                quantity=int(quantity),
                unit_price=float(unit_price),
            )
        except (ValueError, TypeError):
            return None

    def _find_field(self, data: Dict[str, Any], candidates: List[str]) -> Any:
        """在数据中查找字段"""
        for key in candidates:
            if key in data:
                return data[key]
        return None


class DashboardAnalyzer:
    """仪表盘分析类"""

    def __init__(self, data: DashboardData):
        self.data = data

    def get_kpis(self) -> Dict[str, float]:
        """计算核心 KPI 指标"""
        records = self.data.records
        if not records:
            return {
                "total_revenue": 0.0,
                "total_quantity": 0,
                "avg_unit_price": 0.0,
                "order_count": 0,
            }

        total_revenue = sum(r.revenue for r in records)
        total_quantity = sum(r.quantity for r in records)
        avg_unit_price = total_revenue / total_quantity if total_quantity else 0.0

        return {
            "total_revenue": total_revenue,
            "total_quantity": total_quantity,
            "avg_unit_price": avg_unit_price,
            "order_count": len(records),
        }

    def get_region_stats(self) -> Dict[str, Dict[str, float]]:
        """按地区统计"""
        stats = {}
        for record in self.data.records:
            region = record.region
            if region not in stats:
                stats[region] = {
                    "revenue": 0.0,
                    "quantity": 0,
                    "orders": 0,
                }
            stats[region]["revenue"] += record.revenue
            stats[region]["quantity"] += record.quantity
            stats[region]["orders"] += 1
        return stats

    def get_product_stats(self) -> Dict[str, Dict[str, float]]:
        """按产品统计"""
        stats = {}
        for record in self.data.records:
            product = record.product
            if product not in stats:
                stats[product] = {
                    "revenue": 0.0,
                    "quantity": 0,
                    "orders": 0,
                }
            stats[product]["revenue"] += record.revenue
            stats[product]["quantity"] += record.quantity
            stats[product]["orders"] += 1
        return stats

    def get_trend(self) -> Dict[str, Dict[str, float]]:
        """按日期趋势"""
        trend = {}
        for record in self.data.records:
            date = record.date
            if date not in trend:
                trend[date] = {
                    "revenue": 0.0,
                    "quantity": 0,
                    "orders": 0,
                }
            trend[date]["revenue"] += record.revenue
            trend[date]["quantity"] += record.quantity
            trend[date]["orders"] += 1
        return trend

    def get_confidence(self) -> float:
        """计算置信度"""
        if not self.data.records:
            return 0.0

        # 基于数据完整度计算置信度
        complete_records = 0
        for record in self.data.records:
            if all([record.date, record.region, record.product, record.quantity > 0, record.unit_price > 0]):
                complete_records += 1

        confidence = complete_records / len(self.data.records) * 100.0
        return min(confidence, 100.0)


class OutputGenerator:
    """输出生成类"""

    @staticmethod
    def generate_report(data: DashboardData) -> Dict[str, Any]:
        """生成分析报告"""
        analyzer = DashboardAnalyzer(data)

        # 计算置信度
        confidence = analyzer.get_confidence()

        # 生成报告
        report = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "record_count": len(data.records),
                "confidence": confidence,
                "confidence_label": OutputGenerator._get_confidence_label(confidence),
            },
            "kpis": analyzer.get_kpis(),
            "regions": analyzer.get_region_stats(),
            "products": analyzer.get_product_stats(),
            "trends": analyzer.get_trend(),
        }
        return report

    @staticmethod
    def _get_confidence_label(confidence: float) -> str:
        """获取置信度标签"""
        if confidence >= 90.0:
            return "高置信度"
        elif confidence >= 85.0:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 自测模块
# ============================================================
class SelfTest:
    """自测类 - 使用内置硬编码数据验证核心逻辑"""

    # 内置测试数据
    TEST_JSON_DATA = [
        {
            "date": "2024-01-01",
            "region": "华东",
            "product": "笔记本电脑",
            "quantity": 10,
            "unit_price": 5000.0,
        },
        {
            "date": "2024-01-01",
            "region": "华南",
            "product": "智能手机",
            "quantity": 20,
            "unit_price": 3000.0,
        },
        {
            "date": "2024-01-02",
            "region": "华东",
            "product": "平板电脑",
            "quantity": 15,
            "unit_price": 2000.0,
        },
        {
            "date": "2024-01-02",
            "region": "华北",
            "product": "笔记本电脑",
            "quantity": 8,
            "unit_price": 5200.0,
        },
        {
            "date": "2024-01-03",
            "region": "华南",
            "product": "智能手表",
            "quantity": 30,
            "unit_price": 1500.0,
        },
    ]

    @classmethod
    def run(cls) -> bool:
        """运行全部自测"""
        print("开始自测...")
        try:
            cls._test_processor()
            cls._test_analyzer()
            cls._test_output()
            print("自测通过 ✅")
            return True
        except AssertionError as e:
            print(f"自测失败 ❌: {str(e)}")
            return False

    @classmethod
    def _test_processor(cls):
        """测试数据处理"""
        processor = DataProcessor()

        # 测试 JSON 解析
        data = processor.process_input(json.dumps(cls.TEST_JSON_DATA), "json")
        assert len(data.records) == 5, "JSON 解析记录数应为 5"

        # 测试 CSV 解析
        csv_data = "date,region,product,quantity,unit_price\n"
        csv_data += "2024-01-01,华东,测试产品,10,100.0\n"
        data = processor.process_input(csv_data, "csv")
        assert len(data.records) == 1, "CSV 解析记录数应为 1"
        assert data.records[0].revenue == 1000.0, "营收计算错误"

        # 测试空输入
        try:
            processor.process_input("", "json")
            assert False, "空输入应该抛出 E001"
        except SkillError as e:
            assert e.code == "E001", "错误码应为 E001"

        print("  ✓ 数据处理测试通过")

    @classmethod
    def _test_analyzer(cls):
        """测试分析功能"""
        processor = DataProcessor()
        data = processor.process_input(json.dumps(cls.TEST_JSON_DATA), "json")
        analyzer = DashboardAnalyzer(data)

        # 测试 KPI
        kpis = analyzer.get_kpis()
        assert kpis["total_revenue"] > 0, "总营收应大于 0"
        assert kpis["total_quantity"] > 0, "总数量应大于 0"
        assert kpis["order_count"] == 5, "订单数应为 5"
        assert kpis["avg_unit_price"] > 0, "平均单价应大于 0"

        # 测试地区统计
        regions = analyzer.get_region_stats()
        assert len(regions) >= 3, "至少应有 3 个地区"
        assert "华东" in regions, "应包含华东地区"
        assert regions["华东"]["revenue"] > 0, "华东营收应大于 0"

        # 测试产品统计
        products = analyzer.get_product_stats()
        assert len(products) >= 4, "至少应有 4 个产品"

        # 测试趋势
        trends = analyzer.get_trend()
        assert len(trends) >= 3, "至少应有 3 个日期"

        # 测试置信度
        confidence = analyzer.get_confidence()
        assert confidence > 0, "置信度应大于 0"
        assert confidence <= 100, "置信度不应超过 100"

        print("  ✓ 分析功能测试通过")

    @classmethod
    def _test_output(cls):
        """测试输出生成"""
        processor = DataProcessor()
        data = processor.process_input(json.dumps(cls.TEST_JSON_DATA), "json")
        report = OutputGenerator.generate_report(data)

        # 检查报告结构
        assert "meta" in report, "报告应包含 meta"
        assert "kpis" in report, "报告应包含 kpis"
        assert "regions" in report, "报告应包含 regions"
        assert "products" in report, "报告应包含 products"
        assert "trends" in report, "报告应包含 trends"

        # 检查置信度标签
        assert report["meta"]["confidence_label"] in ["高置信度", "建议复核", "[需核实]"]

        print("  ✓ 输出生成测试通过")


# ============================================================
# 主入口
# ============================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据可视化技能 - 处理销售数据并生成仪表盘报告"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON 或 CSV 字符串）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "csv", "auto"],
        default="auto",
        help="输入格式（默认自动检测）",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        help="输入文件路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（JSON 格式）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测",
    )

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        success = SelfTest.run()
        sys.exit(0 if success else 1)

    # 正常处理模式
    try:
        # 获取输入数据
        raw_input = args.input
        if args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except Exception as e:
                raise SkillError("E006", f"文件读取失败: {str(e)}")

        # E001: 输入为空
        if not raw_input:
            raise SkillError("E001")

        # 处理数据
        processor = DataProcessor()
        data = processor.process_input(raw_input, args.format)

        # 生成报告
        report = OutputGenerator.generate_report(data)

        # 输出结果
        output_json = json.dumps(report, ensure_ascii=False, indent=2)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"报告已保存到: {args.output}")
            except Exception as e:
                raise SkillError("E008", f"输出写入失败: {str(e)}")
        else:
            print(output_json)

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[E010] 内部错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
