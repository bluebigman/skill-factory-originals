#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruview — 无线信号空间感知与存在检测分析（Clean-room 实现）

本脚本完全依据功能规格独立实现，不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

核心能力：
    1. 信号强度解析：解析 RSSI 序列，输出均值、方差、峰值频次
    2. 空间状态推断：基于多源信号波动，判定存在/不存在/不确定
    3. 区域划分建议：基于衰减模型，给出监测区域划分建议
    4. 异常信号报告：识别信号突变事件（时间戳+类型+置信度）

命令行用法：
    python main.py [--selftest]
"""

import argparse
import math
import statistics
import sys
from collections import deque
from datetime import datetime, timedelta


# ============================================================
# 错误码定义 (E001-E010)
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或格式错误",
    "E002": "采样数据不足（至少需要 30 个数据点）",
    "E003": "采样率过低（至少需要 1Hz）",
    "E004": "发射源数量不足（至少需要 2 个）",
    "E005": "房间尺寸参数无效",
    "E006": "数据中包含非数值类型",
    "E007": "时间戳格式错误",
    "E008": "时间跨度不足（至少需要 5 分钟）",
    "E009": "参数类型错误",
    "E010": "内部计算异常",
}


class RUViewError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 信号强度解析模块
# ============================================================
class SignalAnalyzer:
    """信号强度解析器：处理 RSSI 数值序列，输出波动特征"""

    @staticmethod
    def validate_rssi_sequence(rssi_values: list) -> None:
        """校验 RSSI 序列有效性"""
        if not rssi_values:
            raise RUViewError("E001")
        if len(rssi_values) < 30:
            raise RUViewError("E002")
        for val in rssi_values:
            if not isinstance(val, (int, float)):
                raise RUViewError("E006")
            if math.isnan(val) or math.isinf(val):
                raise RUViewError("E006")

    @staticmethod
    def calculate_features(rssi_values: list) -> dict:
        """计算波动特征：均值、方差、峰值频次"""
        SignalAnalyzer.validate_rssi_sequence(rssi_values)

        try:
            mean_val = statistics.mean(rssi_values)
            var_val = statistics.variance(rssi_values) if len(rssi_values) > 1 else 0.0

            # 峰值检测：局部极大值（比前后邻居都大）
            peak_count = 0
            for i in range(1, len(rssi_values) - 1):
                if rssi_values[i] > rssi_values[i-1] and rssi_values[i] > rssi_values[i+1]:
                    peak_count += 1

            # 峰值频次 = 峰值数 / 总时长（假设 1Hz 采样率，点数即秒数）
            duration_seconds = len(rssi_values)
            peak_freq = peak_count / duration_seconds if duration_seconds > 0 else 0.0

            return {
                "mean": mean_val,                # 均值
                "variance": var_val,             # 方差
                "peak_count": peak_count,        # 峰值次数
                "peak_frequency": peak_freq,     # 峰值频次（次/秒）
                "sample_count": len(rssi_values), # 样本数
            }
        except Exception as exc:
            raise RUViewError("E010", str(exc)) from exc


# ============================================================
# 空间状态推断模块
# ============================================================
class SpaceStateDetector:
    """空间状态推断器：根据多源信号波动判定存在状态"""

    # 判定阈值（宽松设计，避免边界依赖）
    VARIANCE_THRESHOLD = 0.5      # 方差低于此值视为"无明显波动"
    PEAK_FREQ_THRESHOLD = 0.01    # 峰值频次低于此值视为"不活跃"

    @staticmethod
    def validate_sources(sources: dict) -> None:
        """校验发射源数据：至少 2 个有效信号源"""
        if not isinstance(sources, dict):
            raise RUViewError("E009")
        if len(sources) < 2:
            raise RUViewError("E004")
        for src_name, rssi_list in sources.items():
            if not isinstance(rssi_list, list) or not rssi_list:
                raise RUViewError("E001")
            SignalAnalyzer.validate_rssi_sequence(rssi_list)

    @classmethod
    def infer_state(cls, sources: dict) -> dict:
        """
        推断空间存在状态：
        - "present"：存在移动物体（多个源波动明显）
        - "absent"：不存在移动物体（所有源波动微弱）
        - "uncertain"：不确定（部分源波动，部分不波动）
        """
        cls.validate_sources(sources)

        try:
            per_source_features = {}
            for src_name, rssi_list in sources.items():
                features = SignalAnalyzer.calculate_features(rssi_list)
                per_source_features[src_name] = features

            # 统计活跃源数量（方差或峰值频次超过阈值）
            active_sources = 0
            for features in per_source_features.values():
                if (features["variance"] > cls.VARIANCE_THRESHOLD or
                        features["peak_frequency"] > cls.PEAK_FREQ_THRESHOLD):
                    active_sources += 1

            total_sources = len(sources)

            # 判定逻辑（宽松比例判断）
            if active_sources == 0:
                state = "absent"
                confidence = 0.8  # 高置信度：完全安静
            elif active_sources >= total_sources * 0.6:
                state = "present"
                confidence = 0.7 + 0.2 * (active_sources / total_sources)
            else:
                state = "uncertain"
                confidence = 0.5

            return {
                "state": state,                      # present / absent / uncertain
                "confidence": min(confidence, 0.95), # 置信度 0~1
                "active_source_count": active_sources,
                "total_source_count": total_sources,
                "per_source_features": per_source_features,
            }
        except RUViewError:
            raise
        except Exception as exc:
            raise RUViewError("E010", str(exc)) from exc


# ============================================================
# 区域划分建议模块
# ============================================================
class ZonePlanner:
    """区域划分建议器：基于信号衰减模型给出监测区域建议"""

    # 2.4GHz 信号自由空间衰减模型（简化版）
    # 路径损耗 = 20*log10(d) + 20*log10(f) - 147.55，f 单位 MHz
    FREQ_MHZ = 2400.0

    @staticmethod
    def validate_room_params(room_width: float, room_height: float,
                             router_pos: tuple, wall_material: str) -> None:
        """校验房间参数"""
        if not isinstance(room_width, (int, float)) or room_width <= 0:
            raise RUViewError("E005")
        if not isinstance(room_height, (int, float)) or room_height <= 0:
            raise RUViewError("E005")
        if not isinstance(router_pos, (tuple, list)) or len(router_pos) != 2:
            raise RUViewError("E009")
        if not all(isinstance(v, (int, float)) for v in router_pos):
            raise RUViewError("E009")
        if not isinstance(wall_material, str) or not wall_material:
            raise RUViewError("E009")

    @staticmethod
    def _wall_attenuation(material: str) -> float:
        """墙体材质衰减系数（dB）"""
        material_map = {
            "木质": 3.0,
            "石膏板": 2.5,
            "砖墙": 8.0,
            "混凝土": 15.0,
            "玻璃": 2.0,
        }
        return material_map.get(material, 5.0)  # 默认中等衰减

    @classmethod
    def suggest_zones(cls, room_width: float, room_height: float,
                      router_pos: tuple, wall_material: str) -> dict:
        """生成区域划分建议"""
        cls.validate_room_params(room_width, room_height, router_pos, wall_material)

        try:
            rx, ry = router_pos
            attenuation = cls._wall_attenuation(wall_material)

            # 计算各区域信号强度参考值
            # 将房间划分为 3 个区域：近场、中场、远场（基于距离）
            max_dist = math.sqrt(room_width**2 + room_height**2)
            rx_dist = math.sqrt((room_width - rx)**2 + (room_height - ry)**2)

            def path_loss(distance_m):
                """简化路径损耗计算"""
                if distance_m <= 0:
                    distance_m = 0.1
                return 20 * math.log10(distance_m) + 20 * math.log10(cls.FREQ_MHZ) - 147.55

            # 参考信号强度（假设发射功率 20dBm）
            tx_power = 20.0
            ref_rssi = tx_power - path_loss(rx_dist / 3)

            zones = []
            for i, (dist_ratio, name) in enumerate([
                (0.3, "近场区"),
                (0.6, "中场区"),
                (1.0, "远场区"),
            ]):
                dist = dist_ratio * rx_dist
                rssi_est = tx_power - path_loss(dist) - attenuation
                zones.append({
                    "zone_name": name,
                    "distance_ratio": dist_ratio,
                    "estimated_rssi": rssi_est,
                    "recommendation": (
                        f"{name}：建议部署监测点，预计信号强度约 {rssi_est:.1f} dBm"
                    ),
                })

            return {
                "room_size": (room_width, room_height),
                "router_position": router_pos,
                "wall_material": wall_material,
                "wall_attenuation_db": attenuation,
                "zones": zones,
                "summary": (
                    f"房间 {room_width}x{room_height}m，路由器在 ({rx},{ry})，"
                    f"墙体衰减 {attenuation}dB。建议分为 {len(zones)} 个监测区域。"
                ),
            }
        except RUViewError:
            raise
        except Exception as exc:
            raise RUViewError("E010", str(exc)) from exc


# ============================================================
# 异常信号报告模块
# ============================================================
class AnomalyDetector:
    """异常信号检测器：识别信号突变事件"""

    # 突变判定阈值（宽松）
    JUMP_THRESHOLD_DB = 8.0      # 相邻采样变化超过此值视为突变
    MIN_DURATION_SECONDS = 300   # 至少 5 分钟数据

    @staticmethod
    def validate_timeseries(timestamps: list, rssi_values: list) -> None:
        """校验时间序列数据"""
        if not timestamps or not rssi_values:
            raise RUViewError("E001")
        if len(timestamps) != len(rssi_values):
            raise RUViewError("E001")

        # 时间跨度检查
        try:
            first_ts = timestamps[0]
            last_ts = timestamps[-1]
            if isinstance(first_ts, (int, float)) and isinstance(last_ts, (int, float)):
                duration = last_ts - first_ts
            else:
                # 尝试解析为 datetime
                first_dt = datetime.fromisoformat(str(first_ts))
                last_dt = datetime.fromisoformat(str(last_ts))
                duration = (last_dt - first_dt).total_seconds()

            if duration < AnomalyDetector.MIN_DURATION_SECONDS:
                raise RUViewError("E008")
        except (ValueError, TypeError) as exc:
            raise RUViewError("E007", str(exc)) from exc

        # RSSI 校验
        SignalAnalyzer.validate_rssi_sequence(rssi_values)

    @classmethod
    def detect_anomalies(cls, timestamps: list, rssi_values: list) -> dict:
        """检测异常事件列表"""
        cls.validate_timeseries(timestamps, rssi_values)

        try:
            anomalies = []
            for i in range(1, len(rssi_values)):
                diff = abs(rssi_values[i] - rssi_values[i-1])
                if diff > cls.JUMP_THRESHOLD_DB:
                    # 判断突变类型
                    if rssi_values[i] > rssi_values[i-1]:
                        anomaly_type = "signal_increase"
                        desc = "信号强度突增"
                    else:
                        anomaly_type = "signal_decrease"
                        desc = "信号强度突降"

                    # 置信度计算（基于突变幅度）
                    confidence = min(0.9, 0.5 + diff / 30.0)

                    anomalies.append({
                        "timestamp": timestamps[i],
                        "type": anomaly_type,
                        "description": desc,
                        "delta_db": diff,
                        "confidence": confidence,
                    })

            return {
                "total_events": len(anomalies),
                "events": anomalies,
                "summary": f"检测到 {len(anomalies)} 个异常事件",
            }
        except RUViewError:
            raise
        except Exception as exc:
            raise RUViewError("E010", str(exc)) from exc


# ============================================================
# 综合分析入口
# ============================================================
class RUViewAnalyzer:
    """ruview 综合分析器：整合所有能力"""

    def __init__(self):
        self.signal_analyzer = SignalAnalyzer()
        self.state_detector = SpaceStateDetector()
        self.zone_planner = ZonePlanner()
        self.anomaly_detector = AnomalyDetector()

    def full_analysis(self, rssi_sequences: dict, room_params: dict) -> dict:
        """
        执行完整分析流程
        rssi_sequences: {"source1": [rssi...], "source2": [rssi...]}
        room_params: {"width": float, "height": float, "router_pos": (x,y), "wall_material": str}
        """
        # 1. 空间状态推断
        state_result = self.state_detector.infer_state(rssi_sequences)

        # 2. 区域划分建议
        zone_result = self.zone_planner.suggest_zones(
            room_params["width"],
            room_params["height"],
            room_params["router_pos"],
            room_params["wall_material"],
        )

        # 3. 信号特征分析（取第一个源作为代表）
        first_source = list(rssi_sequences.keys())[0]
        signal_features = self.signal_analyzer.calculate_features(rssi_sequences[first_source])

        return {
            "space_state": state_result,
            "zones": zone_result,
            "signal_features": signal_features,
            "analysis_time": datetime.now().isoformat(),
        }


# ============================================================
# 自检模块（--selftest）
# ============================================================
class SelfTest:
    """内置自检：使用硬编码样例数据验证核心逻辑"""

    @staticmethod
    def _generate_test_data():
        """生成测试数据（确定性数据，非随机）"""
        # 模拟 60 秒采样，1Hz
        # 源1：有明显波动（模拟有人移动）
        source1 = []
        base = -45.0
        for i in range(60):
            # 使用确定性正弦波 + 固定偏移，产生波动
            val = base + 5 * math.sin(i / 5.0) + (3 if i % 7 == 0 else 0)
            source1.append(round(val, 2))

        # 源2：波动较小（模拟较远或遮挡）
        source2 = []
        base2 = -60.0
        for i in range(60):
            val = base2 + 2 * math.sin(i / 8.0)
            source2.append(round(val, 2))

        # 源3：几乎无波动（模拟静止环境）
        source3 = [-70.0 + (0.1 if i % 10 == 0 else 0) for i in range(60)]

        return {
            "sources": {
                "source_1": source1,
                "source_2": source2,
                "source_3": source3,
            },
            "room": {
                "width": 6.0,
                "height": 4.0,
                "router_pos": (1.0, 2.0),
                "wall_material": "砖墙",
            },
        }

    @classmethod
    def run(cls) -> bool:
        """执行自检，返回是否通过"""
        print("=" * 60)
        print("ruview 自检开始（离线模式，无外部依赖）")
        print("=" * 60)

        try:
            test_data = cls._generate_test_data()

            # ---- 测试1：信号特征分析 ----
            print("\n[测试1] 信号特征分析")
            analyzer = SignalAnalyzer()
            features = analyzer.calculate_features(test_data["sources"]["source_1"])
            assert features["sample_count"] >= 30, "样本数应 >= 30"
            assert features["variance"] > 0, "波动数据方差应 > 0"
            assert features["peak_count"] > 0, "波动数据应有峰值"
            assert 0 <= features["peak_frequency"] <= 1, "峰值频次应在合理范围"
            print(f"  ✓ 通过: 均值={features['mean']:.2f}, 方差={features['variance']:.2f}, "
                  f"峰值次数={features['peak_count']}")

            # ---- 测试2：空间状态推断 ----
            print("\n[测试2] 空间状态推断")
            detector = SpaceStateDetector()
            state_result = detector.infer_state(test_data["sources"])
            assert state_result["state"] in ("present", "absent", "uncertain"), \
                "状态必须是三态之一"
            assert 0 <= state_result["confidence"] <= 1, "置信度应在 0~1 之间"
            assert state_result["active_source_count"] >= 1, "应有至少一个活跃源"
            print(f"  ✓ 通过: 状态={state_result['state']}, 置信度={state_result['confidence']:.2f}, "
                  f"活跃源={state_result['active_source_count']}/{state_result['total_source_count']}")

            # ---- 测试3：区域划分建议 ----
            print("\n[测试3] 区域划分建议")
            planner = ZonePlanner()
            zone_result = planner.suggest_zones(
                test_data["room"]["width"],
                test_data["room"]["height"],
                test_data["room"]["router_pos"],
                test_data["room"]["wall_material"],
            )
            assert len(zone_result["zones"]) == 3, "应输出 3 个区域"
            assert zone_result["wall_attenuation_db"] > 0, "墙体衰减应为正数"
            print(f"  ✓ 通过: 区域数={len(zone_result['zones'])}, "
                  f"墙体衰减={zone_result['wall_attenuation_db']}dB")

            # ---- 测试4：异常检测 ----
            print("\n[测试4] 异常信号检测")
            # 构造 6 分钟数据（360 点），包含突变
            timestamps = list(range(360))  # 0~359 秒
            rssi = [-50.0] * 180 + [-65.0] * 180  # 中间有 15dB 突变
            anomaly_detector = AnomalyDetector()
            anomaly_result = anomaly_detector.detect_anomalies(timestamps, rssi)
            assert anomaly_result["total_events"] >= 1, "应检测到至少 1 个异常"
            first_event = anomaly_result["events"][0]
            assert first_event["type"] in ("signal_increase", "signal_decrease"), \
                "异常类型必须正确"
            print(f"  ✓ 通过: 检测到 {anomaly_result['total_events']} 个异常事件")

            # ---- 测试5：综合流程 ----
            print("\n[测试5] 综合分析流程")
            full_analyzer = RUViewAnalyzer()
            full_result = full_analyzer.full_analysis(test_data["sources"], test_data["room"])
            assert "space_state" in full_result, "应包含空间状态"
            assert "zones" in full_result, "应包含区域建议"
            assert "signal_features" in full_result, "应包含信号特征"
            print(f"  ✓ 通过: 综合状态={full_result['space_state']['state']}")

            # ---- 测试6：错误处理 ----
            print("\n[测试6] 错误处理")
            try:
                SignalAnalyzer.calculate_features([])
                assert False, "空数据应抛出 E001"
            except RUViewError as e:
                assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
            print("  ✓ 通过: 空数据正确抛出 E001")

            try:
                SignalAnalyzer.calculate_features([-50] * 10)  # 不足 30 个
                assert False, "数据不足应抛出 E002"
            except RUViewError as e:
                assert e.code == "E002", f"错误码应为 E002，实际 {e.code}"
            print("  ✓ 通过: 数据不足正确抛出 E002")

            print("\n" + "=" * 60)
            print("✅ 全部自检通过！")
            print("=" * 60)
            return True

        except AssertionError as exc:
            print(f"\n❌ 自检失败: {exc}")
            return False
        except RUViewError as exc:
            print(f"\n❌ 自检异常: [{exc.code}] {exc.message}")
            return False
        except Exception as exc:
            print(f"\n❌ 自检未预期异常: {exc}")
            return False


# ============================================================
# 命令行入口
# ============================================================
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="ruview — 无线信号空间感知与存在检测分析",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部数据）",
    )
    args = parser.parse_args()

    if args.selftest:
        success = SelfTest.run()
        sys.exit(0 if success else 1)

    # 未指定参数时，显示帮助信息
    parser.print_help()
    print("\n提示: 使用 --selftest 运行内置自检")


if __name__ == "__main__":
    main()
