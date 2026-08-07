#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户跟进轨迹管理与商机停滞预警工具

功能：
1. 读取客户跟进记录（CSV/XLSX）
2. 按客户归并时间线，计算跟进频次、最近跟进时间、平均间隔
3. 基于沉默阈值识别停滞商机
4. 结合互动频次、情绪倾向、竞品动态计算流失风险评分
5. 输出结构化分析报告（JSON/CSV）与行动建议

用法示例：
    python run.py --file ./customer_data.csv --output ./report.json
    python run.py --file ./data.xlsx --threshold 14 --output ./report.csv
    python run.py --selftest
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

# 尝试导入可选依赖
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# 情绪关键词词典（用于流失评分，作为情感分析的补充）
POSITIVE_WORDS = {"满意", "认可", "积极", "推进", "签约", "合作", "愉快", "顺利", "好评", "推荐"}
NEGATIVE_WORDS = {"不满", "投诉", "推迟", "取消", "犹豫", "拒绝", "失望", "差评", "终止", "搁置"}
COMPETITOR_WORDS = {"竞品", "对比", "考虑其他", "别家", "替代方案", "比价", "竞标"}

# 默认沉默阈值（天）
DEFAULT_THRESHOLD = 14

# 错误码定义
ERROR_CODES = {
    "E001": "文件不存在",
    "E002": "缺少必填字段",
    "E003": "日期解析失败",
    "E004": "编码错误",
    "E005": "依赖缺失",
}


class CustomerTracker:
    """客户跟进轨迹分析引擎"""

    def __init__(self, threshold=DEFAULT_THRESHOLD):
        self.threshold = threshold
        self.records = []
        self.customers = defaultdict(list)
        self.invalid_records = []
        self.now = datetime.now(timezone.utc)

    def load_csv(self, filepath):
        """加载CSV文件"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{ERROR_CODES['E001']}: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                required = {"客户ID", "客户名称", "跟进日期", "跟进方式", "跟进内容摘要"}
                if not required.issubset(reader.fieldnames or []):
                    missing = required - set(reader.fieldnames or [])
                    raise ValueError(f"{ERROR_CODES['E002']}: {missing}")
                self.records = list(reader)
        except UnicodeDecodeError:
            raise ValueError(f"{ERROR_CODES['E004']}: 请使用UTF-8编码")

        self._process_records()

    def load_xlsx(self, filepath):
        """加载XLSX文件"""
        if not HAS_OPENPYXL:
            raise ImportError(
                f"{ERROR_CODES['E005']}: 需要安装openpyxl (pip install openpyxl)。"
                "或者将xlsx文件转换为CSV格式后使用 --file 参数加载。"
            )

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{ERROR_CODES['E001']}: {filepath}")

        try:
            wb = openpyxl.load_workbook(filepath, read_only=True)
            ws = wb.active
            headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            required = {"客户ID", "客户名称", "跟进日期", "跟进方式", "跟进内容摘要"}
            if not required.issubset(headers):
                missing = required - set(headers)
                raise ValueError(f"{ERROR_CODES['E002']}: {missing}")

            records = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                record = dict(zip(headers, row))
                if all(record.get(k) is not None for k in required):
                    records.append(record)
            wb.close()
            self.records = records
            self._process_records()
        except Exception as e:
            if isinstance(e, (ImportError, FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"读取xlsx文件失败: {str(e)}")

    def _process_records(self):
        """处理原始记录，解析日期并按客户归组"""
        self.customers = defaultdict(list)
        self.invalid_records = []

        for idx, record in enumerate(self.records):
            try:
                date_str = record.get("跟进日期", "").strip()
                parsed_date = self._parse_date(date_str)
                if parsed_date is None:
                    raise ValueError(f"无法解析日期: {date_str}")

                customer_id = record.get("客户ID", "").strip()
                if not customer_id:
                    raise ValueError("客户ID为空")

                processed = {
                    "客户ID": customer_id,
                    "客户名称": record.get("客户名称", "").strip(),
                    "跟进日期": parsed_date.isoformat(),
                    "跟进方式": record.get("跟进方式", "").strip(),
                    "跟进内容摘要": record.get("跟进内容摘要", "").strip(),
                    "原始记录索引": idx,
                }
                self.customers[customer_id].append(processed)
            except (ValueError, AttributeError) as e:
                self.invalid_records.append({"index": idx, "error": str(e), "record": record})

        # 按日期排序
        for cid in self.customers:
            self.customers[cid].sort(key=lambda x: x["跟进日期"])

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        解析多种日期格式，返回aware datetime对象或None
        统一转换为UTC时区，避免naive/aware比较错误
        """
        if not date_str:
            return None

        # 尝试多种格式
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # 统一添加UTC时区
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        # 尝试ISO格式（可能已带时区）
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

        return None

    def _get_sentiment_score(self, text: str) -> Tuple[float, float]:
        """
        获取情绪倾向分数
        使用关键词词典方法（移除transformers依赖，避免静默降级问题）
        返回: (正向分数, 负向分数) 范围0-1
        """
        positive_count = 0
        negative_count = 0
        for word in POSITIVE_WORDS:
            if word in text:
                positive_count += 1
        for word in NEGATIVE_WORDS:
            if word in text:
                negative_count += 1

        total = positive_count + negative_count
        if total == 0:
            return (0.5, 0.5)  # 中性
        return (positive_count / total, negative_count / total)

    def _calculate_customer_metrics(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """计算单个客户的指标"""
        records = self.customers[customer_id]
        if not records:
            return None

        dates = [datetime.fromisoformat(r["跟进日期"]) for r in records]
        dates.sort()

        # 基础指标
        first_date = dates[0]
        last_date = dates[-1]
        total_records = len(records)
        days_span = (last_date - first_date).days if total_records > 1 else 0
        avg_interval = days_span / (total_records - 1) if total_records > 1 else 0

        # 停滞天数（确保都是aware datetime）
        days_since_last = (self.now - last_date).days
        is_stalled = days_since_last > self.threshold

        # 情绪分析（使用关键词词典）
        positive_count = 0
        negative_count = 0
        competitor_count = 0
        sentiment_scores = []

        for r in records:
            content = r["跟进内容摘要"]
            # 情感分析
            pos_score, neg_score = self._get_sentiment_score(content)
            sentiment_scores.append((pos_score, neg_score))
            if pos_score > neg_score:
                positive_count += 1
            elif neg_score > pos_score:
                negative_count += 1

            # 竞品检测
            for word in COMPETITOR_WORDS:
                if word in content:
                    competitor_count += 1

        # 计算平均情绪分数
        avg_pos_score = sum(s[0] for s in sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5
        avg_neg_score = sum(s[1] for s in sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5

        # 流失评分 (0-100)
        # 权重: 频次(30%) + 情绪(40%) + 竞品(30%)
        freq_score = min(30, total_records * 5)  # 记录越多，风险越低
        freq_score = 30 - freq_score if freq_score < 30 else 0

        # 基于平均负向情绪分数计算情绪风险
        sentiment_score = avg_neg_score * 40

        competitor_score = min(30, competitor_count * 10)

        risk_score = min(100, freq_score + sentiment_score + competitor_score)

        # 风险等级
        if risk_score >= 70:
            risk_level = "高"
        elif risk_score >= 40:
            risk_level = "中"
        else:
            risk_level = "低"

        # 行动建议
        suggestions = []
        if is_stalled:
            if risk_level == "高":
                suggestions.append("紧急联系客户，了解需求变化，考虑移交资深销售")
            elif risk_level == "中":
                suggestions.append("发送关怀信息，安排一次深度沟通")
            else:
                suggestions.append("发送行业资讯或产品更新，保持互动")
        else:
            if risk_level == "高":
                suggestions.append("增加跟进频率，关注竞品动态")
            elif risk_level == "中":
                suggestions.append("保持现有节奏，准备价值提案")
            else:
                suggestions.append("维持良好关系，寻求转介绍机会")

        # 评分依据说明
        score_reason = (
            f"频次得分={freq_score:.1f}/30 (基于{total_records}次跟进), "
            f"情绪得分={sentiment_score:.1f}/40 (平均负向情绪分数={avg_neg_score:.2f}), "
            f"竞品得分={competitor_score:.1f}/30 (提及{competitor_count}次)"
        )

        return {
            "客户ID": customer_id,
            "客户名称": records[0]["客户名称"],
            "总跟进次数": total_records,
            "首次跟进日期": first_date.isoformat(),
            "最近跟进日期": last_date.isoformat(),
            "平均跟进间隔(天)": round(avg_interval, 1),
            "停滞天数": days_since_last,
            "是否停滞": is_stalled,
            "正向情绪次数": positive_count,
            "负向情绪次数": negative_count,
            "平均正向情绪分数": round(avg_pos_score, 3),
            "平均负向情绪分数": round(avg_neg_score, 3),
            "竞品提及次数": competitor_count,
            "流失风险评分": risk_score,
            "风险等级": risk_level,
            "评分依据": score_reason,
            "行动建议": suggestions,
        }

    def analyze(self) -> Dict[str, Any]:
        """执行全部分析，返回结果字典"""
        results = {
            "生成时间": self.now.isoformat(),
            "沉默阈值(天)": self.threshold,
            "客户总数": len(self.customers),
            "记录总数": len(self.records),
            "无效记录数": len(self.invalid_records),
            "无效记录详情": self.invalid_records[:10],  # 最多显示10条
            "客户分析": [],
            "统计摘要": {},
        }

        for cid in self.customers:
            metrics = self._calculate_customer_metrics(cid)
            if metrics:
                results["客户分析"].append(metrics)

        # 统计摘要
        stalled_count = sum(1 for c in results["客户分析"] if c["是否停滞"])
        risk_distribution = {"低": 0, "中": 0, "高": 0}
        for c in results["客户分析"]:
            risk_distribution[c["风险等级"]] += 1

        results["统计摘要"] = {
            "停滞商机数": stalled_count,
            "停滞率": round(stalled_count / len(results["客户分析"]) * 100, 1) if results["客户分析"] else 0,
            "风险分布": risk_distribution,
        }

        return results

    def export_json(self, results: Dict[str, Any], filepath: str):
        """导出JSON报告（原子写入）"""
        self._atomic_write(filepath, json.dumps(results, ensure_ascii=False, indent=2))

    def export_csv(self, results: Dict[str, Any], filepath: str):
        """导出CSV报告（原子写入）"""
        if not results["客户分析"]:
            self._atomic_write(filepath, "无数据\n")
            return

        fieldnames = [
            "客户ID", "客户名称", "总跟进次数", "首次跟进日期", "最近跟进日期",
            "平均跟进间隔(天)", "停滞天数", "是否停滞", "正向情绪次数",
            "负向情绪次数", "平均正向情绪分数", "平均负向情绪分数",
            "竞品提及次数", "流失风险评分", "风险等级", "评分依据", "行动建议"
        ]

        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filepath) or ".")
        try:
            with os.fdopen(temp_fd, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for customer in results["客户分析"]:
                    row = {k: customer.get(k, "") for k in fieldnames}
                    row["行动建议"] = "; ".join(customer["行动建议"])
                    writer.writerow(row)
            os.replace(temp_path, filepath)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _atomic_write(self, filepath: str, content: str):
        """原子写入文件"""
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filepath) or ".")
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, filepath)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise


def run_selftest() -> int:
    """自测试：验证核心功能"""
    print("开始自测试...")

    # 创建测试数据
    test_data = [
        {"客户ID": "C001", "客户名称": "测试客户A", "跟进日期": "2024-01-01", "跟进方式": "电话", "跟进内容摘要": "客户满意，推进签约"},
        {"客户ID": "C001", "客户名称": "测试客户A", "跟进日期": "2024-01-15", "跟进方式": "邮件", "跟进内容摘要": "客户认可方案"},
        {"客户ID": "C002", "客户名称": "测试客户B", "跟进日期": "2024-01-01", "跟进方式": "会议", "跟进内容摘要": "客户投诉，考虑竞品"},
        {"客户ID": "C002", "客户名称": "测试客户B", "跟进日期": "2024-01-02", "跟进方式": "电话", "跟进内容摘要": "客户不满，推迟决策"},
    ]

    # 写入临时CSV
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "test_data.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(test_data[0].keys()))
        writer.writeheader()
        writer.writerows(test_data)

    # 测试1: 加载CSV
    tracker = CustomerTracker(threshold=14)
    tracker.load_csv(csv_path)
    assert len(tracker.records) == 4, f"加载记录数错误: {len(tracker.records)}"
    assert len(tracker.customers) == 2, f"客户数错误: {len(tracker.customers)}"
    print("✓ CSV加载测试通过")

    # 测试2: 分析功能
    results = tracker.analyze()
    assert results["客户总数"] == 2, "客户总数错误"
    assert results["记录总数"] == 4, "记录总数错误"
    assert results["无效记录数"] == 0, "无效记录数错误"
    assert len(results["客户分析"]) == 2, "客户分析数量错误"
    print("✓ 分析功能测试通过")

    # 测试3:
