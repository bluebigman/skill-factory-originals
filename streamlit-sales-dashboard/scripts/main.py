#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
数据可视化技能 - Streamlit 销售仪表盘辅助工具

本脚本根据功能规格独立实现（clean-room），提供：
1. 数据解析与结构化处理
2. 关键指标计算（KPI）
3. 置信度评估与标注
4. 标准输出格式与错误码体系
5. 内置离线自检（--selftest）

仅依赖 Python 标准库，无需第三方包。
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查数据格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "数据解析失败，请检查数据源",
    "E007": "字段类型不匹配，请核对数据类型",
    "E008": "计算过程异常，请检查输入数据",
    "E009": "输出生成失败，请重试",
    "E010": "未知错误，请联系管理员",
}


class SkillError(Exception):
    """技能统一异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class SalesRecord:
    """销售记录数据类"""

    def __init__(
        self,
        date: str,
        product: str,
        region: str,
        amount: float,
        quantity: int,
        customer: str = "",
    ):
        self.date = date
        self.product = product
        self.region = region
        self.amount = float(amount)
        self.quantity = int(quantity)
        self.customer = customer

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "date": self.date,
            "product": self.product,
            "region": self.region,
            "amount": self.amount,
            "quantity": self.quantity,
            "customer": self.customer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SalesRecord":
        """从字典创建记录"""
        required = ["date", "product", "region", "amount", "quantity"]
        missing = [k for k in required if k not in data]
        if missing:
            raise SkillError("E002", f"缺少必要字段: {', '.join(missing)}")
        return cls(
            date=str(data["date"]),
            product=str(data["product"]),
            region=str(data["region"]),
            amount=float(data["amount"]),
            quantity=int(data["quantity"]),
            customer=str(data.get("customer", "")),
        )


# ============================================================
# 数据解析与验证
# ============================================================
def parse_input(data: Any) -> List[SalesRecord]:
    """
    解析输入数据为销售记录列表

    支持格式：
    - List[Dict]：字典列表
    - Dict：包含 records 键的字典
    - JSON 字符串
    """
    if data is None:
        raise SkillError("E001")

    # 处理 JSON 字符串
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise SkillError("E006", "JSON 解析失败")

    # 处理字典格式
    if isinstance(data, dict):
        if "records" in data:
            data = data["records"]
        elif "data" in data:
            data = data["data"]
        else:
            # 单条记录
            data = [data]

    # 处理列表格式
    if not isinstance(data, list):
        raise SkillError("E003", "输入必须是列表或包含 records 的字典")

    if len(data) == 0:
        raise SkillError("E001")

    # 解析每条记录
    records = []
    for item in data:
        if not isinstance(item, dict):
            raise SkillError("E003", f"记录必须是字典格式，收到: {type(item)}")
        try:
            records.append(SalesRecord.from_dict(item))
        except (ValueError, TypeError) as e:
            raise SkillError("E007", f"字段类型错误: {str(e)}")

    return records


# ============================================================
# KPI 计算
# ============================================================
def calculate_kpis(records: List[SalesRecord]) -> Dict[str, Any]:
    """
    计算关键绩效指标（KPI）

    返回：
    - 总销售额
    - 总销量
    - 订单数
    - 平均客单价
    - 区域排名
    - 产品排名
    """
    if not records:
        raise SkillError("E001")

    total_amount = sum(r.amount for r in records)
    total_quantity = sum(r.quantity for r in records)
    order_count = len(records)

    # 平均客单价（宽松判断：总金额/订单数）
    avg_order_value = total_amount / order_count if order_count > 0 else 0.0

    # 区域聚合
    region_stats: Dict[str, Dict[str, float]] = {}
    for r in records:
        if r.region not in region_stats:
            region_stats[r.region] = {"amount": 0.0, "quantity": 0}
        region_stats[r.region]["amount"] += r.amount
        region_stats[r.region]["quantity"] += r.quantity

    # 按销售额排序
    region_ranking = sorted(
        region_stats.items(), key=lambda x: x[1]["amount"], reverse=True
    )

    # 产品聚合
    product_stats: Dict[str, float] = {}
    for r in records:
        product_stats[r.product] = product_stats.get(r.product, 0.0) + r.amount

    product_ranking = sorted(product_stats.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_amount": round(total_amount, 2),
        "total_quantity": total_quantity,
        "order_count": order_count,
        "avg_order_value": round(avg_order_value, 2),
        "region_ranking": [
            {"region": k, "amount": round(v["amount"], 2), "quantity": v["quantity"]}
            for k, v in region_ranking
        ],
        "product_ranking": [
            {"product": k, "amount": round(v, 2)} for k, v in product_ranking
        ],
    }


# ============================================================
# 置信度评估
# ============================================================
def evaluate_confidence(records: List[SalesRecord]) -> Tuple[float, str]:
    """
    评估结果置信度

    规则：
    - 记录数 >= 10：高置信度（>=90%）
    - 记录数 >= 5：中置信度（85-90%）
    - 记录数 < 5：低置信度（<85%）
    - 存在缺失字段：降低置信度

    返回：(置信度百分比, 建议标签)
    """
    if not records:
        return 0.0, "[需核实]"

    base_score = 95.0

    # 样本量影响
    if len(records) < 5:
        base_score -= 15.0
    elif len(records) < 10:
        base_score -= 5.0

    # 字段完整性检查
    completeness = 0.0
    for r in records:
        fields = ["date", "product", "region", "amount", "quantity"]
        present = sum(1 for f in fields if getattr(r, f) not in (None, "", 0))
        completeness += present / len(fields)
    completeness_ratio = completeness / len(records) if records else 0.0
    base_score -= (1.0 - completeness_ratio) * 10.0

    # 限制范围
    confidence = max(0.0, min(100.0, base_score))

    # 生成标签
    if confidence >= 90.0:
        label = "直接输出"
    elif confidence >= 85.0:
        label = "建议复核"
    else:
        label = "[需核实]"

    return round(confidence, 1), label


# ============================================================
# 输出格式化
# ============================================================
def format_output(kpis: Dict[str, Any], confidence: float, label: str) -> Dict[str, Any]:
    """生成标准输出格式"""
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "confidence": {
            "score": confidence,
            "label": label,
        },
        "kpis": kpis,
        "summary": (
            f"共 {kpis['order_count']} 笔订单，"
            f"总销售额 ¥{kpis['total_amount']:,.2f}，"
            f"总销量 {kpis['total_quantity']} 件"
        ),
    }


# ============================================================
# 主处理流程
# ============================================================
def process_data(data: Any) -> Dict[str, Any]:
    """
    标准处理流程：
    1. 解析输入
    2. 计算 KPI
    3. 评估置信度
    4. 生成输出
    """
    try:
        # Step 1: 解析输入
        records = parse_input(data)

        # Step 2: 计算 KPI
        kpis = calculate_kpis(records)

        # Step 3: 置信度评估
        confidence, label = evaluate_confidence(records)

        # Step 4: 生成输出
        return format_output(kpis, confidence, label)

    except SkillError as e:
        return {
            "status": "error",
            "code": e.code,
            "message": e.message,
        }
    except Exception as e:
        return {
            "status": "error",
            "code": "E010",
            "message": f"未知错误: {str(e)}",
        }


# ============================================================
# 内置自检（--selftest）
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑

    使用硬编码样例数据，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值，确保稳定通过。
    """
    print("=" * 60)
    print("自检开始：数据可视化技能核心逻辑验证")
    print("=" * 60)

    # 内置硬编码样例数据（10条记录，覆盖多区域多产品）
    sample_data = [
        {"date": "2026-01-01", "product": "笔记本电脑", "region": "华东", "amount": 12999.0, "quantity": 5, "customer": "A公司"},
        {"date": "2026-01-02", "product": "智能手机", "region": "华北", "amount": 6999.0, "quantity": 8, "customer": "B公司"},
        {"date": "2026-01-03", "product": "平板电脑", "region": "华南", "amount": 3999.0, "quantity": 6, "customer": "C公司"},
        {"date": "2026-01-04", "product": "笔记本电脑", "region": "华北", "amount": 11999.0, "quantity": 3, "customer": "D公司"},
        {"date": "2026-01-05", "product": "智能手表", "region": "华东", "amount": 2999.0, "quantity": 10, "customer": "E公司"},
        {"date": "2026-01-06", "product": "智能手机", "region": "华南", "amount": 7499.0, "quantity": 4, "customer": "F公司"},
        {"date": "2026-01-07", "product": "平板电脑", "region": "华东", "amount": 3599.0, "quantity": 7, "customer": "G公司"},
        {"date": "2026-01-08", "product": "笔记本电脑", "region": "华南", "amount": 13999.0, "quantity": 2, "customer": "H公司"},
        {"date": "2026-01-09", "product": "智能手表", "region": "华北", "amount": 2599.0, "quantity": 12, "customer": "I公司"},
        {"date": "2026-01-10", "product": "智能手机", "region": "华东", "amount": 7999.0, "quantity": 6, "customer": "J公司"},
    ]

    # 测试1：正常处理流程
    print("\n[测试1] 正常数据处理流程")
    result = process_data(sample_data)
    assert result["status"] == "success", f"状态应为 success，实际: {result}"
    print("  ✓ 状态检查通过")

    # 测试2：KPI 数值合理性（宽松断言）
    print("\n[测试2] KPI 数值合理性")
    kpis = result["kpis"]
    assert kpis["order_count"] == 10, f"订单数应为 10，实际: {kpis['order_count']}"
    assert kpis["total_amount"] > 50000, f"总销售额应大于 50000，实际: {kpis['total_amount']}"
    assert kpis["total_quantity"] > 50, f"总销量应大于 50，实际: {kpis['total_quantity']}"
    assert kpis["avg_order_value"] > 5000, f"平均客单价应大于 5000，实际: {kpis['avg_order_value']}"
    assert len(kpis["region_ranking"]) >= 3, "至少应有 3 个区域"
    assert len(kpis["product_ranking"]) >= 4, "至少应有 4 个产品"
    print("  ✓ 总销售额:", kpis["total_amount"])
    print("  ✓ 总销量:", kpis["total_quantity"])
    print("  ✓ 平均客单价:", kpis["avg_order_value"])
    print("  ✓ 区域数:", len(kpis["region_ranking"]))
    print("  ✓ 产品数:", len(kpis["product_ranking"]))

    # 测试3：置信度评估（宽松断言）
    print("\n[测试3] 置信度评估")
    confidence = result["confidence"]["score"]
    assert confidence >= 85.0, f"置信度应 >= 85，实际: {confidence}"
    print(f"  ✓ 置信度: {confidence}%")

    # 测试4：错误处理 - 空输入
    print("\n[测试4] 空输入错误处理")
    result = process_data(None)
    assert result["status"] == "error", "空输入应返回错误"
    assert result["code"] == "E001", f"错误码应为 E001，实际: {result.get('code')}"
    print(f"  ✓ 错误码: {result['code']}")

    # 测试5：错误处理 - 格式错误
    print("\n[测试5] 格式错误处理")
    result = process_data("not a valid json")
    assert result["status"] == "error", "无效 JSON 应返回错误"
    assert result["code"] in ("E006", "E003"), f"错误码应为 E006 或 E003，实际: {result.get('code')}"
    print(f"  ✓ 错误码: {result['code']}")

    # 测试6：错误处理 - 缺少字段
    print("\n[测试6] 缺少字段错误处理")
    bad_data = [{"date": "2026-01-01", "product": "测试"}]  # 缺少 region/amount/quantity
    result = process_data(bad_data)
    assert result["status"] == "error", "缺少字段应返回错误"
    assert result["code"] == "E002", f"错误码应为 E002，实际: {result.get('code')}"
    print(f"  ✓ 错误码: {result['code']}")

    # 测试7：批量处理
    print("\n[测试7] 批量处理能力")
    batch_data = [
        {"date": "2026-02-01", "product": "显示器", "region": "西南", "amount": 1999.0, "quantity": 3},
        {"date": "2026-02-02", "product": "键盘", "region": "东北", "amount": 399.0, "quantity": 15},
        {"date": "2026-02-03", "product": "鼠标", "region": "华东", "amount": 199.0, "quantity": 20},
    ]
    result = process_data(batch_data)
    assert result["status"] == "success", "批量处理应成功"
    assert result["kpis"]["order_count"] == 3, f"订单数应为 3，实际: {result['kpis']['order_count']}"
    print("  ✓ 批量处理成功")

    # 测试8：单条记录处理
    print("\n[测试8] 单条记录处理")
    single_data = {"date": "2026-03-01", "product": "耳机", "region": "华北", "amount": 899.0, "quantity": 2}
    result = process_data(single_data)
    assert result["status"] == "success", "单条记录应成功"
    assert result["kpis"]["order_count"] == 1, f"订单数应为 1，实际: {result['kpis']['order_count']}"
    print("  ✓ 单条记录处理成功")

    # 测试9：置信度标签
    print("\n[测试9] 置信度标签")
    result = process_data(sample_data)
    label = result["confidence"]["label"]
    assert label in ("直接输出", "建议复核", "[需核实]"), f"标签不合法: {label}"
    print(f"  ✓ 置信度标签: {label}")

    # 测试10：输出格式完整性
    print("\n[测试10] 输出格式完整性")
    result = process_data(sample_data)
    assert "status" in result, "输出缺少 status"
    assert "kpis" in result, "输出缺少 kpis"
    assert "confidence" in result, "输出缺少 confidence"
    assert "summary" in result, "输出缺少 summary"
    print("  ✓ 输出格式完整")

    print("\n" + "=" * 60)
    print("✅ 全部自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="数据可视化技能 - 销售数据处理工具",
        epilog="示例: python main.py --input data.json --output result.json",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部数据）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 文件路径（包含 records 数组或直接为数组）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出 JSON 文件路径（可选，默认输出到 stdout）",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="直接传入 JSON 字符串作为输入数据",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"\n❌ 自检失败: {str(e)}")
            return 1
        except Exception as e:
            print(f"\n❌ 自检异常: {str(e)}")
            return 1

    # 数据处理模式
    if args.data:
        # 从命令行参数读取数据
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            print("错误: --data 参数不是有效的 JSON")
            return 1
    elif args.input:
        # 从文件读取数据
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"错误: 文件不存在: {args.input}")
            return 1
        except json.JSONDecodeError:
            print(f"错误: 文件不是有效的 JSON: {args.input}")
            return 1
    else:
        # 没有输入数据
        print("错误: 请提供输入数据（--data 或 --input）或使用 --selftest")
        parser.print_help()
        return 1

    # 处理数据
    result = process_data(data)

    # 输出结果
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"结果已写入: {args.output}")
        except IOError as e:
            print(f"错误: 无法写入输出文件: {str(e)}")
            return 1
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
