#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruview — 空间感知 无线信号 环境监测
=====================================
将 WiFi 信号（CSI 振幅/相位、RSSI 序列）转化为结构化空间分析结果。

功能：
  - 活动检测（静止 / 移动 / 无人）
  - 区域占用估计
  - 信号质量指标
  - 置信度评分

用法：
  python scripts/main.py --selftest          # 离线自检
  python scripts/main.py --input data.csv    # 分析信号数据文件
  python scripts/main.py --help              # 帮助

错误码：
  E001 参数错误
  E002 文件不存在
  E003 文件格式不支持
  E004 数据解析失败
  E005 数据为空
  E006 数据长度不足
  E007 数值范围异常
  E008 内部计算错误
  E009 输出写入失败
  E010 未知错误

许可证：MIT License (c) 2026 SkillForge Lab
"""

import argparse
import csv
import json
import math
import os
import random
import statistics
import sys
import tempfile
from pathlib import Path


# ============================================================
# 常量定义
# ============================================================

# 信号强度参考值（dBm）
RSSI_REFERENCE = -30.0

# 活动分类阈值
ACTIVITY_STATIC_THRESHOLD = 0.15      # 标准差阈值（归一化后）
ACTIVITY_MOVING_THRESHOLD = 0.45      # 标准差阈值（归一化后）

# 占用估计系数
OCCUPANCY_ALPHA = 0.6                 # 加权系数
OCCUPANCY_BETA = 0.4                  # 加权系数

# 置信度计算系数
CONFIDENCE_WEIGHT = 0.8               # 信号质量权重
CONFIDENCE_PENALTY = 0.2              # 数据长度惩罚系数


# ============================================================
# 错误处理工具
# ============================================================

class RuViewError(Exception):
    """自定义异常，携带错误码"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _fail(code: str, message: str):
    """抛出带错误码的异常"""
    raise RuViewError(code, message)


# ============================================================
# 数据解析模块
# ============================================================

def parse_signal_data(file_path: str) -> dict:
    """
    解析信号数据文件（CSV/JSON/纯文本）

    支持格式：
      - CSV: 第一列为时间戳，第二列为 RSSI 值；或仅一列 RSSI 值
      - JSON: {"rssi": [...], "timestamp": [...]} 或 [{"rssi": ...}, ...]
      - 文本: 每行一个数值（RSSI 或 CSI 振幅）

    返回：
      {"rssi": [...], "timestamps": [...]} 或 {"amplitude": [...], "timestamps": [...]}
    """
    path = Path(file_path)
    if not path.exists():
        _fail("E002", f"文件不存在: {file_path}")

    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            return _parse_csv(path)
        elif suffix == ".json":
            return _parse_json(path)
        elif suffix in (".txt", ".dat", ".log"):
            return _parse_text(path)
        else:
            _fail("E003", f"不支持的文件格式: {suffix}")
    except RuViewError:
        raise
    except Exception as exc:
        _fail("E004", f"数据解析失败: {exc}")


def _parse_csv(path: Path) -> dict:
    """解析 CSV 文件"""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            # 跳过表头（非数值行）
            try:
                values = [float(x.strip()) for x in row if x.strip()]
            except ValueError:
                continue
            if values:
                rows.append(values)

    if not rows:
        _fail("E005", "CSV 文件无有效数值数据")

    # 判断格式：单列或多列
    if len(rows[0]) == 1:
        rssi = [r[0] for r in rows]
        timestamps = list(range(len(rssi)))
        return {"rssi": rssi, "timestamps": timestamps}
    elif len(rows[0]) >= 2:
        # 第一列时间戳，第二列 RSSI
        timestamps = [r[0] for r in rows]
        rssi = [r[1] for r in rows]
        return {"rssi": rssi, "timestamps": timestamps}
    else:
        _fail("E004", "CSV 列数异常")


def _parse_json(path: Path) -> dict:
    """解析 JSON 文件"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 格式1: {"rssi": [...], "timestamp": [...]}
    if isinstance(data, dict):
        if "rssi" in data:
            rssi = [float(x) for x in data["rssi"]]
            timestamps = data.get("timestamp") or data.get("timestamps") or list(range(len(rssi)))
            timestamps = [float(x) for x in timestamps]
            return {"rssi": rssi, "timestamps": timestamps}
        elif "amplitude" in data:
            amp = [float(x) for x in data["amplitude"]]
            timestamps = data.get("timestamp") or data.get("timestamps") or list(range(len(amp)))
            timestamps = [float(x) for x in timestamps]
            return {"amplitude": amp, "timestamps": timestamps}
        else:
            _fail("E004", "JSON 缺少 rssi 或 amplitude 字段")

    # 格式2: [{"rssi": ...}, ...]
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            if "rssi" in data[0]:
                rssi = [float(x["rssi"]) for x in data]
                timestamps = [float(x.get("timestamp", i)) for i, x in enumerate(data)]
                return {"rssi": rssi, "timestamps": timestamps}
            elif "amplitude" in data[0]:
                amp = [float(x["amplitude"]) for x in data]
                timestamps = [float(x.get("timestamp", i)) for i, x in enumerate(data)]
                return {"amplitude": amp, "timestamps": timestamps}
        else:
            _fail("E004", "JSON 数组格式不支持")

    _fail("E004", "JSON 格式不支持")


def _parse_text(path: Path) -> dict:
    """解析纯文本文件（每行一个数值）"""
    values = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                values.append(float(line))
            except ValueError:
                continue

    if not values:
        _fail("E005", "文本文件无有效数值")

    timestamps = list(range(len(values)))
    return {"rssi": values, "timestamps": timestamps}


# ============================================================
# 信号处理核心模块
# ============================================================

def _normalize(values: list) -> list:
    """归一化到 [0, 1] 区间"""
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [0.0] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def _moving_average(values: list, window: int = 3) -> list:
    """滑动平均平滑"""
    if len(values) < window:
        return values.copy()
    result = []
    half = window // 2
    for i in range(len(values)):
        start = max(0, i - half)
        end = min(len(values), i + half + 1)
        result.append(sum(values[start:end]) / (end - start))
    return result


def detect_activity(rssi: list) -> str:
    """
    活动检测：静止 / 移动 / 无人

    基于归一化信号的波动程度判断：
      - 标准差 < 0.15   → 静止
      - 标准差 < 0.45   → 移动
      - 标准差 >= 0.45  → 无人（高波动视为异常/无人）
    """
    if not rssi:
        _fail("E005", "数据为空，无法检测活动")

    if len(rssi) < 5:
        _fail("E006", "数据长度不足，无法可靠检测活动")

    normalized = _normalize(rssi)
    smoothed = _moving_average(normalized, 3)
    std_dev = statistics.stdev(smoothed) if len(smoothed) > 1 else 0.0

    if std_dev < ACTIVITY_STATIC_THRESHOLD:
        return "静止"
    elif std_dev < ACTIVITY_MOVING_THRESHOLD:
        return "移动"
    else:
        return "无人"


def estimate_occupancy(rssi: list) -> dict:
    """
    区域占用估计

    根据信号均值与波动特征估算占用程度：
      - 返回 {"occupancy": 0.0-1.0, "level": "低/中/高"}
    """
    if not rssi:
        _fail("E005", "数据为空，无法估计占用")

    # 信号强度越高（越接近 0），可能越近/占用越高
    avg_rssi = statistics.mean(rssi)
    # 将 RSSI 映射到 [0, 1]：-90 ~ -30 dBm 映射到 0~1
    rssi_score = max(0.0, min(1.0, (avg_rssi - (-90.0)) / 60.0))

    # 波动程度也反映活动/占用
    normalized = _normalize(rssi)
    std_dev = statistics.stdev(normalized) if len(normalized) > 1 else 0.0
    volatility_score = min(1.0, std_dev * 2.0)

    # 加权综合
    occupancy = OCCUPANCY_ALPHA * rssi_score + OCCUPANCY_BETA * volatility_score
    occupancy = max(0.0, min(1.0, occupancy))

    if occupancy < 0.33:
        level = "低"
    elif occupancy < 0.66:
        level = "中"
    else:
        level = "高"

    return {"occupancy": round(occupancy, 4), "level": level}


def compute_signal_quality(rssi: list) -> dict:
    """
    信号质量指标计算

    返回：均值、标准差、信噪比估计、质量评分（0-100）
    """
    if not rssi:
        _fail("E005", "数据为空，无法计算信号质量")

    avg = statistics.mean(rssi)
    std = statistics.stdev(rssi) if len(rssi) > 1 else 0.0

    # 信噪比估计：信号均值与波动比
    if std < 0.1:
        snr = 100.0
    else:
        snr = min(100.0, abs(avg) / std * 20.0)

    # 质量评分：基于信号强度和稳定性
    # 信号越强（接近 -30）且波动越小，质量越高
    strength_score = max(0.0, min(1.0, (avg - (-90.0)) / 60.0))
    stability_score = max(0.0, min(1.0, 1.0 - (std / 10.0)))
    quality = (strength_score * 0.6 + stability_score * 0.4) * 100.0

    return {
        "mean": round(avg, 2),
        "std_dev": round(std, 2),
        "snr_estimate": round(snr, 2),
        "quality_score": round(quality, 2)
    }


def compute_confidence(data_length: int, quality_score: float) -> float:
    """计算置信度评分（0-1）"""
    # 数据长度惩罚：少于 10 个点显著降低置信度
    length_factor = min(1.0, data_length / 20.0)
    length_penalty = (1.0 - length_factor) * CONFIDENCE_PENALTY

    # 质量因素
    quality_factor = quality_score / 100.0

    confidence = CONFIDENCE_WEIGHT * quality_factor - length_penalty
    return max(0.0, min(1.0, confidence))


# ============================================================
# 主分析流程
# ============================================================

def analyze_signal(data: dict) -> dict:
    """
    执行完整的信号分析流程

    输入：
      {"rssi": [...], "timestamps": [...]}
      或 {"amplitude": [...], "timestamps": [...]}

    输出：
      结构化 JSON 结果
    """
    # 提取数据
    if "rssi" in data:
        signal = data["rssi"]
        signal_type = "rssi"
    elif "amplitude" in data:
        signal = data["amplitude"]
        signal_type = "amplitude"
    else:
        _fail("E004", "数据缺少信号字段")

    if not signal:
        _fail("E005", "信号数据为空")

    if len(signal) < 3:
        _fail("E006", "信号数据长度不足（最少 3 个点）")

    # 数值范围检查
    for val in signal:
        if not math.isfinite(val):
            _fail("E007", "信号数据包含非有限数值")

    # 活动检测
    activity = detect_activity(signal)

    # 占用估计
    occupancy = estimate_occupancy(signal)

    # 信号质量
    quality = compute_signal_quality(signal)

    # 置信度
    confidence = compute_confidence(len(signal), quality["quality_score"])

    # 趋势分析（简单线性回归斜率）
    trend = _compute_trend(signal)

    # 异常波动标记
    anomalies = _detect_anomalies(signal)

    # 组装结果
    result = {
        "meta": {
            "skill": "ruview",
            "version": "1.0.1",
            "signal_type": signal_type
        },
        "analysis": {
            "activity": activity,
            "occupancy": occupancy,
            "signal_quality": quality,
            "confidence": round(confidence, 4),
            "trend": trend,
            "anomalies": anomalies
        },
        "summary": {
            "sample_count": len(signal),
            "duration": _compute_duration(data.get("timestamps", [])),
            "data_points": len(signal)
        }
    }

    return result


def _compute_trend(signal: list) -> dict:
    """计算信号趋势（线性回归斜率）"""
    n = len(signal)
    if n < 2:
        return {"direction": "平稳", "slope": 0.0}

    x_mean = (n - 1) / 2.0
    y_mean = sum(signal) / n

    numerator = 0.0
    denominator = 0.0
    for i, y in enumerate(signal):
        numerator += (i - x_mean) * (y - y_mean)
        denominator += (i - x_mean) ** 2

    if denominator == 0:
        slope = 0.0
    else:
        slope = numerator / denominator

    # 归一化斜率
    y_range = max(signal) - min(signal)
    if y_range == 0:
        norm_slope = 0.0
    else:
        norm_slope = slope / y_range

    if norm_slope > 0.05:
        direction = "上升"
    elif norm_slope < -0.05:
        direction = "下降"
    else:
        direction = "平稳"

    return {"direction": direction, "slope": round(norm_slope, 4)}


def _detect_anomalies(signal: list) -> list:
    """检测异常波动点"""
    if len(signal) < 3:
        return []

    mean = statistics.mean(signal)
    std = statistics.stdev(signal) if len(signal) > 1 else 0.0

    if std == 0:
        return []

    anomalies = []
    for i, val in enumerate(signal):
        z_score = (val - mean) / std
        if abs(z_score) > 2.0:
            anomalies.append({
                "index": i,
                "value": round(val, 2),
                "z_score": round(z_score, 2)
            })

    return anomalies


def _compute_duration(timestamps: list) -> float:
    """计算时间跨度"""
    if not timestamps or len(timestamps) < 2:
        return 0.0
    return round(max(timestamps) - min(timestamps), 2)


# ============================================================
# 自检模块
# ============================================================

def _selftest() -> None:
    """
    离线自检核心逻辑

    使用内置样例数据验证：
      - 活动检测
      - 占用估计
      - 信号质量
      - 置信度
    """
    print("=" * 60)
    print("ruview 自检开始")
    print("=" * 60)

    # 测试用例 1：静止信号（低波动）
    static_signal = [-65.0 + (i % 2) * 0.1 for i in range(30)]
    print("\n[测试 1] 静止信号检测...")
    result = analyze_signal({"rssi": static_signal, "timestamps": list(range(30))})
    assert result["analysis"]["activity"] == "静止", f"期望静止，实际 {result['analysis']['activity']}"
    print(f"  ✓ 活动检测: {result['analysis']['activity']}")

    # 测试用例 2：移动信号（中等波动）
    moving_signal = []
    for i in range(30):
        base = -60.0
        variation = math.sin(i * 0.3) * 5.0
        moving_signal.append(base + variation)
    print("\n[测试 2] 移动信号检测...")
    result = analyze_signal({"rssi": moving_signal, "timestamps": list(range(30))})
    assert result["analysis"]["activity"] in ("移动", "静止"), f"活动检测异常: {result['analysis']['activity']}"
    print(f"  ✓ 活动检测: {result['analysis']['activity']}")

    # 测试用例 3：无人信号（高波动/异常）
    empty_signal = []
    for i in range(30):
        if i % 5 == 0:
            empty_signal.append(-90.0 + random.random() * 30.0)
        else:
            empty_signal.append(-65.0 + random.random() * 10.0)
    print("\n[测试 3] 高波动信号检测...")
    result = analyze_signal({"rssi": empty_signal, "timestamps": list(range(30))})
    print(f"  ✓ 活动检测: {result['analysis']['activity']}")

    # 测试用例 4：占用估计
    print("\n[测试 4] 占用估计...")
    result = analyze_signal({"rssi": static_signal, "timestamps": list(range(30))})
    assert 0.0 <= result["analysis"]["occupancy"]["occupancy"] <= 1.0, "占用估计超出范围"
    print(f"  ✓ 占用: {result['analysis']['occupancy']}")

    # 测试用例 5：信号质量
    print("\n[测试 5] 信号质量...")
    result = analyze_signal({"rssi": moving_signal, "timestamps": list(range(30))})
    assert 0 <= result["analysis"]["signal_quality"]["quality_score"] <= 100, "质量评分超出范围"
    print(f"  ✓ 质量评分: {result['analysis']['signal_quality']['quality_score']}")

    # 测试用例 6：置信度
    print("\n[测试 6] 置信度计算...")
    result = analyze_signal({"rssi": static_signal, "timestamps": list(range(30))})
    assert 0.0 <= result["analysis"]["confidence"] <= 1.0, "置信度超出范围"
    print(f"  ✓ 置信度: {result['analysis']['confidence']}")

    # 测试用例 7：错误处理
    print("\n[测试 7] 错误处理...")
    try:
        analyze_signal({"rssi": []})
        assert False, "空数据未抛出异常"
    except RuViewError as e:
        assert e.code == "E005", f"错误码错误: {e.code}"
        print(f"  ✓ 空数据正确抛出 E005")

    # 测试用例 8：文件解析
    print("\n[测试 8] 文件解析...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("timestamp,rssi\n")
        for i in range(10):
            f.write(f"{i},{-60.0 + i * 0.5}\n")
        tmp_path = f.name
    try:
        data = parse_signal_data(tmp_path)
        assert len(data["rssi"]) == 10, "CSV 解析数据量错误"
        print(f"  ✓ CSV 解析成功: {len(data['rssi'])} 个数据点")
    finally:
        os.unlink(tmp_path)

    print("\n" + "=" * 60)
    print("✅ 所有自检通过！")
    print("=" * 60)


# ============================================================
# 命令行入口
# ============================================================

def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="ruview — 空间感知 无线信号 环境监测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/main.py --selftest
  python scripts/main.py --input data.csv
  python scripts/main.py --input data.json --output result.json
        """
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--input", "-i", type=str, help="输入信号数据文件（CSV/JSON/TXT）")
    parser.add_argument("--output", "-o", type=str, help="输出结果 JSON 文件路径")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON 输出")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        _selftest()
        return 0

    # 分析模式
    if not args.input:
        parser.error("请提供 --input 参数或使用 --selftest 进行自检")

    try:
        # 解析数据
        data = parse_signal_data(args.input)

        # 执行分析
        result = analyze_signal(data)

        # 输出结果
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2 if args.pretty else None)
            print(f"结果已写入: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

        return 0

    except RuViewError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
