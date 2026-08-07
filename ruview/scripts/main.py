#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruview — 无线信号空间感知与存在检测分析（独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
提供信号强度解析、空间状态推断、区域划分建议、异常信号报告四大核心能力。
"""

import argparse
import math
import statistics
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：输入数据格式不正确",
    "E002": "数据不足：采样点数少于最小要求",
    "E003": "采样率过低：无法满足时间分辨率要求",
    "E004": "发射源不足：需要至少2个发射源信号",
    "E005": "时间跨度不足：需要至少5分钟数据",
    "E006": "房间尺寸参数无效",
    "E007": "信号数据包含无效值（非数值或超出合理范围）",
    "E008": "内部计算错误",
    "E009": "输入数据为空",
    "E010": "未知错误",
}


class RuviewError(Exception):
    """ruview 自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class SignalSample:
    """单条信号采样记录。"""

    def __init__(self, timestamp: datetime, source_id: str, rssi: float):
        self.timestamp = timestamp
        self.source_id = source_id
        self.rssi = rssi


class SignalSeries:
    """某个发射源的信号时间序列。"""

    def __init__(self, source_id: str, samples: List[SignalSample]):
        self.source_id = source_id
        self.samples = samples

    def rssi_values(self) -> List[float]:
        return [s.rssi for s in self.samples]

    def timestamps(self) -> List[datetime]:
        return [s.timestamp for s in self.samples]


# ============================================================
# 数据校验与预处理
# ============================================================

def validate_signal_data(samples: List[SignalSample]) -> None:
    """校验信号数据的基本合法性。"""
    if not samples:
        raise RuviewError("E009")

    # 检查采样点数
    if len(samples) < 30:
        raise RuviewError("E002", f"采样点数 {len(samples)} < 30，至少需要30个点")

    # 检查发射源数量（按 source_id 去重）
    source_ids = set(s.source_id for s in samples)
    if len(source_ids) < 2:
        raise RuviewError("E004", f"发射源数量 {len(source_ids)} < 2")

    # 检查时间跨度
    timestamps = [s.timestamp for s in samples]
    time_span = (max(timestamps) - min(timestamps)).total_seconds()
    if time_span < 300:  # 5分钟
        raise RuviewError("E005", f"时间跨度 {time_span:.1f}秒 < 300秒")

    # 检查采样率（至少 1Hz）
    if len(samples) > 1:
        intervals = [
            (timestamps[i + 1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
            if (timestamps[i + 1] - timestamps[i]).total_seconds() > 0
        ]
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            if avg_interval > 1.0:
                raise RuviewError("E003", f"平均采样间隔 {avg_interval:.2f}秒 > 1秒")

    # 检查 RSSI 值范围（-120 ~ 0 dBm 为合理范围）
    for s in samples:
        if not isinstance(s.rssi, (int, float)) or math.isnan(s.rssi):
            raise RuviewError("E007", f"非数值 RSSI: {s.rssi}")
        if s.rssi < -120 or s.rssi > 0:
            raise RuviewError("E007", f"RSSI 超出合理范围: {s.rssi}")


def group_by_source(samples: List[SignalSample]) -> Dict[str, SignalSeries]:
    """按发射源分组，返回序列字典。"""
    grouped: Dict[str, List[SignalSample]] = {}
    for s in samples:
        grouped.setdefault(s.source_id, []).append(s)

    # 每个源内部按时间排序
    result = {}
    for sid, slist in grouped.items():
        slist.sort(key=lambda x: x.timestamp)
        result[sid] = SignalSeries(sid, slist)
    return result


# ============================================================
# 核心算法：信号特征提取
# ============================================================

def compute_series_features(series: SignalSeries) -> Dict[str, float]:
    """计算单个信号序列的统计特征。"""
    values = series.rssi_values()
    if len(values) < 2:
        raise RuviewError("E002")

    mean_val = statistics.mean(values)
    variance_val = statistics.variance(values) if len(values) > 1 else 0.0
    std_val = math.sqrt(variance_val)

    # 计算峰值频次：信号强度变化超过阈值（3dB）的次数
    peak_count = 0
    threshold = 3.0
    for i in range(1, len(values)):
        if abs(values[i] - values[i - 1]) > threshold:
            peak_count += 1
    # 归一化为每分钟峰值次数
    timestamps = series.timestamps()
    span_seconds = (timestamps[-1] - timestamps[0]).total_seconds()
    peaks_per_min = (peak_count / span_seconds * 60.0) if span_seconds > 0 else 0.0

    # 最大波动幅度
    max_fluctuation = max(values) - min(values) if values else 0.0

    return {
        "mean": mean_val,
        "variance": variance_val,
        "std": std_val,
        "peaks_per_min": peaks_per_min,
        "max_fluctuation": max_fluctuation,
    }


# ============================================================
# 空间状态推断
# ============================================================

def infer_spatial_state(features_list: List[Dict[str, float]]) -> str:
    """
    根据多个发射源的特征推断空间状态。
    返回 'present'（有人）、'absent'（无人）、'uncertain'（不确定）。
    """
    if not features_list:
        return "uncertain"

    # 综合所有源的平均方差和峰值频次
    avg_variance = statistics.mean([f["variance"] for f in features_list])
    avg_peaks = statistics.mean([f["peaks_per_min"] for f in features_list])
    avg_fluctuation = statistics.mean([f["max_fluctuation"] for f in features_list])

    # 宽松判定阈值（基于经验值，留有充分余量）
    # 有人活动时：方差 > 1.0，峰值 > 1次/分钟，波动 > 5dB
    if avg_variance > 1.0 and avg_peaks > 1.0:
        return "present"
    # 无人时：方差很小，峰值很少
    if avg_variance < 0.5 and avg_peaks < 0.5 and avg_fluctuation < 5.0:
        return "absent"
    return "uncertain"


# ============================================================
# 区域划分建议
# ============================================================

def suggest_zones(room_length: float, room_width: float,
                  router_x: float, router_y: float,
                  wall_material: str = "drywall") -> List[Dict]:
    """
    基于信号衰减模型给出区域划分建议。
    返回区域列表，每个区域包含中心坐标和半径。
    """
    if room_length <= 0 or room_width <= 0:
        raise RuviewError("E006", "房间尺寸必须为正数")

    # 墙体材质对应的衰减系数（dB/m）
    material_attenuation = {
        "drywall": 1.5,
        "concrete": 3.0,
        "wood": 1.0,
        "glass": 0.8,
    }
    attenuation = material_attenuation.get(wall_material.lower(), 1.5)

    # 将房间划分为网格，计算每个格点到路由器的距离
    grid_size = 1.0  # 1米网格
    x_steps = max(1, int(room_length / grid_size))
    y_steps = max(1, int(room_width / grid_size))

    # 计算每个格点的信号衰减（简化模型：自由空间 + 墙体衰减）
    zones = []
    for i in range(x_steps):
        for j in range(y_steps):
            cx = (i + 0.5) * grid_size
            cy = (j + 0.5) * grid_size
            distance = math.sqrt((cx - router_x) ** 2 + (cy - router_y) ** 2)
            # 简化衰减模型：L = 20log10(d) + 墙体衰减
            if distance < 0.1:
                distance = 0.1
            free_space_loss = 20 * math.log10(distance) + 40  # 粗略参考
            wall_loss = attenuation * 0.5  # 假设半面墙
            total_loss = free_space_loss + wall_loss

            zones.append({
                "center": (cx, cy),
                "loss": total_loss,
                "distance": distance,
            })

    # 按信号质量分为近、中、远三个区域
    if not zones:
        return []

    losses = [z["loss"] for z in zones]
    min_loss = min(losses)
    max_loss = max(losses)
    loss_range = max_loss - min_loss

    if loss_range < 1.0:
        loss_range = 1.0  # 避免除零

    near_threshold = min_loss + loss_range * 0.3
    mid_threshold = min_loss + loss_range * 0.7

    result_zones = []
    for z in zones:
        if z["loss"] <= near_threshold:
            zone_type = "near"
        elif z["loss"] <= mid_threshold:
            zone_type = "mid"
        else:
            zone_type = "far"
        result_zones.append({
            "type": zone_type,
            "center": z["center"],
            "loss": z["loss"],
        })

    return result_zones


# ============================================================
# 异常信号报告
# ============================================================

def detect_anomalies(series_list: List[SignalSeries],
                     window_seconds: int = 60) -> List[Dict]:
    """
    检测信号异常事件（突变）。
    返回事件列表，每项含时间戳、类型、置信度。
    """
    anomalies = []
    if not series_list:
        return anomalies

    # 对每个源分别检测
    for series in series_list:
        values = series.rssi_values()
        timestamps = series.timestamps()
        if len(values) < 2:
            continue

        # 计算平均采样间隔
        total_span = (timestamps[-1] - timestamps[0]).total_seconds()
        avg_interval = total_span / (len(values) - 1) if len(values) > 1 else 1.0
        
        # 滑动窗口大小（基于秒数转换）
        window_size = max(2, int(window_seconds / max(avg_interval, 0.1)))
        window_size = min(window_size, len(values) // 3) if len(values) > 3 else 1
        if window_size < 1:
            window_size = 1

        # 使用固定窗口大小检测突变
        for i in range(window_size, len(values) - window_size):
            # 计算前后窗口的均值
            before_vals = values[max(0, i - window_size):i]
            after_vals = values[i + 1:min(len(values), i + window_size + 1)]
            
            if len(before_vals) < 1 or len(after_vals) < 1:
                continue
                
            before_mean = statistics.mean(before_vals)
            after_mean = statistics.mean(after_vals)
            current = values[i]
            
            # 检测突变：当前值偏离前后均值
            diff_before = abs(current - before_mean)
            diff_after = abs(current - after_mean)
            diff = max(diff_before, diff_after)

            # 突变阈值：超过 8dB
            if diff > 8.0:
                # 置信度基于突变幅度
                confidence = min(1.0, diff / 15.0)
                anomalies.append({
                    "timestamp": timestamps[i],
                    "source_id": series.source_id,
                    "type": "sudden_change",
                    "magnitude": diff,
                    "confidence": confidence,
                })

    # 按时间排序
    anomalies.sort(key=lambda x: x["timestamp"])
    
    # 合并相近事件（同一时间多个源同时突变可能是同一事件）
    merged = []
    for a in anomalies:
        if merged and (a["timestamp"] - merged[-1]["timestamp"]).total_seconds() < 5:
            # 合并相近事件
            if "sources" not in merged[-1]:
                merged[-1]["sources"] = [merged[-1]["source_id"]]
            merged[-1]["sources"].append(a["source_id"])
            merged[-1]["confidence"] = max(merged[-1]["confidence"], a["confidence"])
            merged[-1]["magnitude"] = max(merged[-1]["magnitude"], a["magnitude"])
        else:
            merged.append(a)

    # 输出格式整理
    result = []
    for m in merged:
        result.append({
            "timestamp": m["timestamp"].isoformat(),
            "type": m["type"],
            "sources": m.get("sources", [m["source_id"]]),
            "magnitude_db": round(m["magnitude"], 1),
            "confidence": round(m["confidence"], 2),
        })
    return result


# ============================================================
# 主分析入口
# ============================================================

def analyze(samples: List[SignalSample]) -> Dict:
    """
    综合分析入口。
    输入信号采样列表，输出完整的分析结果。
    """
    # 数据校验
    validate_signal_data(samples)

    # 按源分组
    series_map = group_by_source(samples)

    # 计算特征
    features_map = {}
    for sid, series in series_map.items():
        features_map[sid] = compute_series_features(series)

    # 空间状态推断
    all_features = list(features_map.values())
    state = infer_spatial_state(all_features)

    # 异常检测
    anomalies = detect_anomalies(list(series_map.values()))

    # 汇总结果
    result = {
        "source_count": len(series_map),
        "total_samples": len(samples),
        "time_span_seconds": round(
            (max(s.timestamp for s in samples) - min(s.timestamp for s in samples)).total_seconds(),
            1
        ),
        "source_features": {
            sid: {
                "mean_rssi": round(f["mean"], 1),
                "variance": round(f["variance"], 2),
                "std": round(f["std"], 2),
                "peaks_per_min": round(f["peaks_per_min"], 2),
                "max_fluctuation": round(f["max_fluctuation"], 1),
            }
            for sid, f in features_map.items()
        },
        "spatial_state": state,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }
    return result


# ============================================================
# 自检模块（内置硬编码数据，离线可跑）
# ============================================================

def _build_selftest_data() -> List[SignalSample]:
    """
    构造自检用内置数据。
    生成 10 分钟、2 个源、采样率约 1Hz 的信号数据。
    源A：稳定信号（模拟无人）；源B：含明显波动（模拟有人活动）。
    """
    start_time = datetime(2026, 1, 1, 0, 0, 0)
    samples = []
    base_time = start_time

    # 源A：稳定信号，均值 -55dBm，方差很小
    for i in range(600):  # 10分钟 * 1Hz
        ts = base_time + timedelta(seconds=i)
        # 轻微噪声，波动 < 1dB
        rssi = -55.0 + math.sin(i * 0.1) * 0.3
        samples.append(SignalSample(ts, "source_A", rssi))

    # 源B：前半段稳定，后半段有明显波动（模拟有人进入）
    for i in range(600):
        ts = base_time + timedelta(seconds=i)
        if i < 300:  # 前5分钟稳定
            rssi = -60.0 + math.cos(i * 0.05) * 0.2
        else:  # 后5分钟波动大
            rssi = -60.0 + math.sin(i * 0.3) * 5.0 + (i % 7) * 0.5
        samples.append(SignalSample(ts, "source_B", rssi))

    return samples


def run_selftest() -> int:
    """运行内置自检，返回退出码（0=通过，非0=失败）。"""
    print("=== ruview 自检开始 ===")

    # ========== 测试1：数据构造与校验 ==========
    print("[1/5] 数据构造与校验...")
    samples = _build_selftest_data()
    assert len(samples) >= 600, "自检数据量不足"
    validate_signal_data(samples)
    print("      通过（数据量 %d 条）" % len(samples))

    # ========== 测试2：特征提取 ==========
    print("[2/5] 特征提取...")
    series_map = group_by_source(samples)
    assert len(series_map) == 2, "应有两个发射源"
    features_a = compute_series_features(series_map["source_A"])
    features_b = compute_series_features(series_map["source_B"])
    # 源A方差应明显小于源B（宽松比较）
    assert features_a["variance"] < features_b["variance"], "源A方差应小于源B"
    assert features_a["peaks_per_min"] < features_b["peaks_per_min"], "源A峰值频次应低于源B"
    print("      通过（源A方差 %.3f，源B方差 %.3f）" % (features_a["variance"], features_b["variance"]))

    # ========== 测试3：空间状态推断 ==========
    print("[3/5] 空间状态推断...")
    state = infer_spatial_state([features_a, features_b])
    assert state in ("present", "absent", "uncertain"), "状态必须是三态之一"
    # 由于源B有明显波动，整体应判定为"有人"或"不确定"（不能是"无人"）
    assert state != "absent", "不应判定为无人"
    print("      通过（判定结果：%s）" % state)

    # ========== 测试4：区域划分 ==========
    print("[4/5] 区域划分建议...")
    zones = suggest_zones(room_length=8.0, room_width=6.0,
                          router_x=2.0, router_y=3.0, wall_material="drywall")
    assert len(zones) > 0, "区域划分结果不能为空"
    zone_types = set(z["type"] for z in zones)
    assert "near" in zone_types and "far" in zone_types, "应包含近区和远区"
    print("      通过（共 %d 个格点，区域类型：%s）" % (len(zones), sorted(zone_types)))

    # ========== 测试5：异常检测 ==========
    print("[5/5] 异常检测...")
    anomalies = detect_anomalies(list(series_map.values()))
    # 源B在后半段有明显波动，应检测到至少1个异常
    assert len(anomalies) >= 1, "应检测到至少1个异常事件"
    for a in anomalies:
        assert "timestamp" in a and "type" in a and "confidence" in a, "异常事件字段不完整"
    print("      通过（检测到 %d 个异常事件）" % len(anomalies))

    print("\n=== 自检全部通过 ===")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="ruview — 无线信号空间感知与存在检测分析",
        epilog="示例：python main.py --selftest"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码数据，无需外部输入）"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据文件路径（预留接口，当前版本仅支持自检）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出结果文件路径（预留接口）"
    )

    args = parser.parse_args()

    try:
        if args.selftest:
            return run_selftest()
        else:
            # 无参数时显示帮助
            parser.print_help()
            return 0
    except RuviewError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except AssertionError as e:
        print(f"自检断言失败: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
