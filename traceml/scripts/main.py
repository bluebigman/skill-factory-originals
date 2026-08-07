#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
traceml — 模型追踪与漂移预警引擎（独立实现）

本脚本依据功能规格 clean-room 重写，仅使用标准库。
支持实验追踪、漂移检测、仪表盘生成等核心能力。

用法:
    python main.py --selftest          # 离线自检核心逻辑
    python main.py --help              # 查看帮助
"""

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数校验失败",
    "E002": "数据格式错误",
    "E003": "计算过程异常",
    "E004": "结果生成失败",
    "E005": "输入维度不匹配",
    "E006": "空数据集",
    "E007": "不支持的操作",
    "E008": "哈希计算失败",
    "E009": "JSON序列化失败",
    "E010": "未知错误",
}


class TraceMLError(Exception):
    """traceml 基础异常类"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class Experiment:
    """实验记录"""
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    model_hash: str = ""
    dataset_version: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)


@dataclass
class DriftReport:
    """漂移检测报告"""
    feature_name: str
    psi: float = 0.0
    kl_divergence: float = 0.0
    ks_statistic: float = 0.0
    is_drift: bool = False
    threshold: float = 0.2
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    """仪表盘配置"""
    title: str
    experiments: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    refresh_interval: int = 60
    theme: str = "light"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# 核心工具函数
# ============================================================
def safe_div(numerator: float, denominator: float) -> float:
    """安全除法，避免除零"""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_hash(data: Any) -> str:
    """计算数据的 SHA-256 哈希指纹"""
    try:
        serialized = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()
    except Exception as exc:
        raise TraceMLError("E008", f"哈希计算失败: {exc}") from exc


def validate_experiment(exp: Experiment) -> None:
    """校验实验数据有效性"""
    if not exp.name or not isinstance(exp.name, str):
        raise TraceMLError("E001", "实验名称必须为非空字符串")
    if not isinstance(exp.params, dict):
        raise TraceMLError("E002", "超参数必须为字典类型")
    if not isinstance(exp.metrics, dict):
        raise TraceMLError("E002", "指标必须为字典类型")


# ============================================================
# 实验追踪模块
# ============================================================
class ExperimentTracker:
    """实验追踪器：记录和管理实验"""
    
    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
    
    def add_experiment(self, exp: Experiment) -> str:
        """添加实验，返回实验ID"""
        validate_experiment(exp)
        exp_id = compute_hash({"name": exp.name, "timestamp": exp.timestamp})
        self._experiments[exp_id] = exp
        return exp_id
    
    def get_experiment(self, exp_id: str) -> Optional[Experiment]:
        """获取实验详情"""
        return self._experiments.get(exp_id)
    
    def list_experiments(self) -> List[Dict[str, Any]]:
        """列出所有实验摘要"""
        return [
            {
                "id": eid,
                "name": exp.name,
                "timestamp": exp.timestamp,
                "metrics": exp.metrics,
            }
            for eid, exp in self._experiments.items()
        ]
    
    def compare_experiments(self, exp_ids: List[str]) -> Dict[str, Any]:
        """对比多个实验"""
        if not exp_ids:
            raise TraceMLError("E006", "至少需要一个实验ID")
        
        exps = []
        for eid in exp_ids:
            exp = self.get_experiment(eid)
            if exp is None:
                raise TraceMLError("E001", f"实验不存在: {eid}")
            exps.append(exp)
        
        # 提取所有指标名称
        all_metrics = set()
        for exp in exps:
            all_metrics.update(exp.metrics.keys())
        
        # 构建对比表
        comparison = {
            "experiments": [exp.name for exp in exps],
            "metrics": {},
        }
        for metric in sorted(all_metrics):
            values = [exp.metrics.get(metric) for exp in exps]
            comparison["metrics"][metric] = values
        
        return comparison


# ============================================================
# 漂移检测模块
# ============================================================
class DriftDetector:
    """漂移检测器：PSI / KL / KS 统计量"""
    
    def __init__(self, threshold: float = 0.2) -> None:
        self.threshold = threshold
    
    @staticmethod
    def _validate_input(reference: Sequence[float], current: Sequence[float]) -> None:
        """校验输入数据"""
        if len(reference) == 0 or len(current) == 0:
            raise TraceMLError("E006", "数据集不能为空")
        if len(reference) != len(current):
            raise TraceMLError("E005", "参考集和当前集长度不一致")
        if not all(isinstance(x, (int, float)) for x in reference + current):
            raise TraceMLError("E002", "数据必须为数值类型")
    
    @staticmethod
    def _compute_psi(reference: Sequence[float], current: Sequence[float], bins: int = 10) -> float:
        """计算 PSI（Population Stability Index）"""
        # 构建分箱边界
        min_val = min(min(reference), min(current))
        max_val = max(max(reference), max(current))
        if min_val == max_val:
            return 0.0
        
        # 使用固定边界来确保稳定性
        bin_edges = [min_val + (max_val - min_val) * i / bins for i in range(bins + 1)]
        bin_edges[-1] = max_val + 1e-9  # 确保最大值包含在最后一个箱
        
        # 统计频率
        ref_counts = [0] * bins
        cur_counts = [0] * bins
        for val in reference:
            idx = min(int((val - min_val) / ((max_val - min_val) / bins)), bins - 1)
            ref_counts[idx] += 1
        for val in current:
            idx = min(int((val - min_val) / ((max_val - min_val) / bins)), bins - 1)
            cur_counts[idx] += 1
        
        # 计算 PSI
        psi = 0.0
        for i in range(bins):
            ref_pct = safe_div(ref_counts[i], len(reference))
            cur_pct = safe_div(cur_counts[i], len(current))
            if ref_pct == 0 and cur_pct == 0:
                continue
            # 添加微小偏移避免 log(0)
            ref_pct = max(ref_pct, 1e-6)
            cur_pct = max(cur_pct, 1e-6)
            psi += (cur_pct - ref_pct) * math.log(cur_pct / ref_pct)
        
        return psi
    
    @staticmethod
    def _compute_kl(reference: Sequence[float], current: Sequence[float], bins: int = 10) -> float:
        """计算 KL 散度（对称化）"""
        # 复用 PSI 的分箱逻辑
        min_val = min(min(reference), min(current))
        max_val = max(max(reference), max(current))
        if min_val == max_val:
            return 0.0
        
        bin_edges = [min_val + (max_val - min_val) * i / bins for i in range(bins + 1)]
        bin_edges[-1] = max_val + 1e-9
        
        ref_counts = [0] * bins
        cur_counts = [0] * bins
        for val in reference:
            idx = min(int((val - min_val) / ((max_val - min_val) / bins)), bins - 1)
            ref_counts[idx] += 1
        for val in current:
            idx = min(int((val - min_val) / ((max_val - min_val) / bins)), bins - 1)
            cur_counts[idx] += 1
        
        # 计算对称 KL 散度
        kl = 0.0
        for i in range(bins):
            p = safe_div(ref_counts[i], len(reference))
            q = safe_div(cur_counts[i], len(current))
            if p == 0 or q == 0:
                continue
            p = max(p, 1e-6)
            q = max(q, 1e-6)
            kl += p * math.log(p / q) + q * math.log(q / p)
        
        return kl / 2.0  # 对称化
    
    @staticmethod
    def _compute_ks(reference: Sequence[float], current: Sequence[float]) -> float:
        """计算 KS 统计量（最大累积分布差异）"""
        # 合并并排序所有值
        combined = sorted(reference + current)
        
        # 计算经验 CDF
        ref_cdf = []
        cur_cdf = []
        for val in combined:
            ref_cdf.append(safe_div(sum(1 for x in reference if x <= val), len(reference)))
            cur_cdf.append(safe_div(sum(1 for x in current if x <= val), len(current)))
        
        # 最大差异
        ks = max(abs(r - c) for r, c in zip(ref_cdf, cur_cdf))
        return ks
    
    def detect_drift(self, feature_name: str, reference: Sequence[float], current: Sequence[float]) -> DriftReport:
        """检测单个特征的漂移"""
        self._validate_input(reference, current)
        
        # 计算各项指标
        psi_val = self._compute_psi(reference, current)
        kl_val = self._compute_kl(reference, current)
        ks_val = self._compute_ks(reference, current)
        
        # 综合判断：任一指标超过阈值则判定漂移
        is_drift = psi_val > self.threshold or kl_val > self.threshold or ks_val > 0.3
        
        return DriftReport(
            feature_name=feature_name,
            psi=psi_val,
            kl_divergence=kl_val,
            ks_statistic=ks_val,
            is_drift=is_drift,
            threshold=self.threshold,
            details={
                "reference_size": len(reference),
                "current_size": len(current),
                "reference_mean": sum(reference) / len(reference),
                "current_mean": sum(current) / len(current),
            }
        )
    
    def detect_concept_drift(self, historical_acc: Sequence[float], current_acc: float) -> Dict[str, Any]:
        """检测概念漂移（准确率衰减）"""
        if not historical_acc:
            raise TraceMLError("E006", "历史准确率序列不能为空")
        
        avg_acc = sum(historical_acc) / len(historical_acc)
        drop_ratio = safe_div(avg_acc - current_acc, avg_acc)
        
        return {
            "historical_avg": avg_acc,
            "current_accuracy": current_acc,
            "drop_ratio": drop_ratio,
            "is_drift": drop_ratio > 0.1,  # 下降超过10%视为漂移
            "severity": "high" if drop_ratio > 0.2 else ("medium" if drop_ratio > 0.1 else "low"),
        }


# ============================================================
# 仪表盘引擎
# ============================================================
class DashboardEngine:
    """仪表盘引擎：聚合实验和漂移状态"""
    
    def __init__(self) -> None:
        self._configs: Dict[str, DashboardConfig] = {}
    
    def create_dashboard(self, title: str, experiments: List[str] = None, features: List[str] = None) -> str:
        """创建仪表盘，返回配置ID"""
        config = DashboardConfig(
            title=title,
            experiments=experiments or [],
            features=features or [],
        )
        config_id = compute_hash({"title": title, "created_at": config.created_at})
        self._configs[config_id] = config
        return config_id
    
    def get_dashboard(self, config_id: str) -> Optional[DashboardConfig]:
        """获取仪表盘配置"""
        return self._configs.get(config_id)
    
    def generate_snapshot(self, config_id: str, tracker: ExperimentTracker, detector: DriftDetector) -> Dict[str, Any]:
        """生成仪表盘快照"""
        config = self.get_dashboard(config_id)
        if config is None:
            raise TraceMLError("E001", f"仪表盘不存在: {config_id}")
        
        snapshot = {
            "config_id": config_id,
            "title": config.title,
            "generated_at": datetime.now().isoformat(),
            "experiments": [],
            "drift_reports": [],
        }
        
        # 聚合实验数据
        for exp_id in config.experiments:
            exp = tracker.get_experiment(exp_id)
            if exp:
                snapshot["experiments"].append({
                    "id": exp_id,
                    "name": exp.name,
                    "metrics": exp.metrics,
                    "model_hash": exp.model_hash[:8] + "..." if exp.model_hash else "",
                })
        
        # 聚合漂移报告（示例：需要外部提供数据）
        # 实际使用时，应由外部传入 reference/current 数据
        snapshot["drift_reports"] = config.features
        
        return snapshot
    
    def export_json(self, config_id: str) -> str:
        """导出仪表盘为 JSON 字符串"""
        config = self.get_dashboard(config_id)
        if config is None:
            raise TraceMLError("E001", f"仪表盘不存在: {config_id}")
        try:
            return json.dumps(asdict(config), ensure_ascii=False, indent=2)
        except Exception as exc:
            raise TraceMLError("E009", f"JSON序列化失败: {exc}") from exc


# ============================================================
# 可视化辅助（静态图表描述）
# ============================================================
class Visualizer:
    """可视化辅助：生成图表描述（不依赖第三方库）"""
    
    @staticmethod
    def loss_curve(epochs: Sequence[int], losses: Sequence[float], title: str = "Loss Curve") -> str:
        """生成损失曲线的 ASCII 描述"""
        if len(epochs) != len(losses) or len(epochs) == 0:
            raise TraceMLError("E005", "epochs 和 losses 长度不一致或为空")
        
        lines = [f"=== {title} ==="]
        lines.append("Epoch | Loss")
        lines.append("------+------")
        for ep, loss in zip(epochs, losses):
            bar = "#" * int(loss * 20)  # 简单可视化
            lines.append(f"{ep:5d} | {loss:.4f} {bar}")
        
        return "\n".join(lines)
    
    @staticmethod
    def feature_distribution(values: Sequence[float], feature_name: str = "Feature", bins: int = 10) -> str:
        """生成特征分布的 ASCII 直方图"""
        if not values:
            raise TraceMLError("E006", "数据集为空")
        
        min_val = min(values)
        max_val = max(values)
        if min_val == max_val:
            return f"{feature_name}: 所有值均为 {min_val}"
        
        bin_width = (max_val - min_val) / bins
        counts = [0] * bins
        for val in values:
            idx = min(int((val - min_val) / bin_width), bins - 1)
            counts[idx] += 1
        
        max_count = max(counts)
        lines = [f"=== {feature_name} 分布 ==="]
        for i, count in enumerate(counts):
            start = min_val + i * bin_width
            end = start + bin_width
            bar = "#" * int(count * 50 / max_count) if max_count > 0 else ""
            lines.append(f"[{start:8.3f}-{end:8.3f}] | {count:5d} {bar}")
        
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """离线自检核心逻辑（不依赖外部文件/网络）"""
    print("=" * 60)
    print("traceml 自检开始")
    print("=" * 60)
    
    # ---------- 1. 实验追踪模块 ----------
    print("\n[1/4] 测试实验追踪...")
    tracker = ExperimentTracker()
    
    # 创建测试实验
    exp1 = Experiment(
        name="exp_baseline",
        params={"lr": 0.01, "batch_size": 32},
        metrics={"acc": 0.85, "loss": 0.35},
        model_hash=compute_hash({"model": "v1"}),
        dataset_version="data_v1",
        tags=["baseline"],
    )
    exp2 = Experiment(
        name="exp_tuned",
        params={"lr": 0.001, "batch_size": 64},
        metrics={"acc": 0.91, "loss": 0.22},
        model_hash=compute_hash({"model": "v2"}),
        dataset_version="data_v1",
        tags=["tuned"],
    )
    
    exp1_id = tracker.add_experiment(exp1)
    exp2_id = tracker.add_experiment(exp2)
    
    # 断言实验被正确添加
    assert tracker.get_experiment(exp1_id) is not None, "实验1添加失败"
    assert tracker.get_experiment(exp2_id) is not None, "实验2添加失败"
    assert len(tracker.list_experiments()) == 2, "实验列表数量错误"
    
    # 测试实验对比
    comparison = tracker.compare_experiments([exp1_id, exp2_id])
    assert "acc" in comparison["metrics"], "对比结果缺少 acc 指标"
    assert len(comparison["metrics"]["acc"]) == 2, "对比结果指标数量错误"
    print("  实验追踪模块: OK")
    
    # ---------- 2. 漂移检测模块 ----------
    print("\n[2/4] 测试漂移检测...")
    detector = DriftDetector(threshold=0.2)
    
    # 构造测试数据：参考集和轻微漂移的当前集
    reference = [1.0, 1.2, 1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2]
    current_similar = [1.1, 1.3, 1.4, 1.7, 2.1, 2.3, 2.4, 2.7, 3.1, 3.3]
    current_drifted = [5.0, 5.2, 5.5, 5.8, 6.0, 6.2, 6.5, 6.8, 7.0, 7.2]
    
    # 相似数据不应漂移（宽松断言：PSI 应该较小）
    report_similar = detector.detect_drift("feature_a", reference, current_similar)
    assert report_similar.psi < 0.5, f"相似数据的 PSI 应较小，实际: {report_similar.psi}"
    assert report_similar.kl_divergence >= 0, "KL 散度不应为负"
    assert 0 <= report_similar.ks_statistic <= 1, "KS 统计量应在 [0,1] 区间"
    
    # 漂移数据应检测出漂移
    report_drifted = detector.detect_drift("feature_b", reference, current_drifted)
    assert report_drifted.psi > report_similar.psi, "漂移数据的 PSI 应更大"
    assert report_drifted.is_drift, f"应检测到明显漂移，PSI: {report_drifted.psi}, KL: {report_drifted.kl_divergence}, KS: {report_drifted.ks_statistic}"
    
    # 测试概念漂移
    concept_report = detector.detect_concept_drift([0.90, 0.88, 0.89, 0.87], 0.75)
    assert concept_report["is_drift"], "准确率下降超过10%应判定为漂移"
    assert concept_report["severity"] in ("high", "medium", "low"), "严重程度等级无效"
    print("  漂移检测模块: OK")
    
    # ---------- 3. 仪表盘引擎 ----------
    print("\n[3/4] 测试仪表盘引擎...")
    engine = DashboardEngine()
    
    dash_id = engine.create_dashboard(
        title="测试看板",
        experiments=[exp1_id, exp2_id],
        features=["feature_a", "feature_b"],
    )
    assert engine.get_dashboard(dash_id) is not None, "仪表盘创建失败"
    
    # 测试 JSON 导出
    json_str = engine.export_json(dash_id)
    assert json_str is not None and len(json_str) > 0, "JSON 导出失败"
    parsed = json.loads(json_str)
    assert parsed["title"] == "测试看板", "JSON 内容错误"
    
    # 测试快照生成
    snapshot = engine.generate_snapshot(dash_id, tracker, detector)
    assert len(snapshot["experiments"]) == 2, "快照实验数量错误"
    print("  仪表盘引擎: OK")
    
    # ---------- 4. 可视化辅助 ----------
    print("\n[4/4] 测试可视化辅助...")
    viz = Visualizer()
    
    # 损失曲线
    loss_curve_str = viz.loss_curve([1, 2, 3, 4, 5], [0.8, 0.6, 0.4, 0.3, 0.2])
    assert "Loss Curve" in loss_curve_str, "损失曲线标题错误"
    
    # 特征分布
    dist_str = viz.feature_distribution([1, 2, 2, 3, 3, 3, 4, 4, 5], "test_feature")
    assert "test_feature" in dist_str, "特征分布标题错误"
    print("  可视化辅助: OK")
    
    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="traceml — 模型追踪与漂移预警引擎",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="traceml 1.0.2",
    )
    
    args = parser.parse_args()
    
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"[E003] 自检失败: {exc}", file=sys.stderr)
            return 1
        except TraceMLError as exc:
            print(f"{exc}", file=sys.stderr)
            return 1
    
    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
