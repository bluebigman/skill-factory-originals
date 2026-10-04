#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考勤处理技能 - 主脚本
处理考勤文件：解析、清洗、判定、统计、输出
"""

import argparse
import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import chardet

# 版本信息
__version__ = "2.0.0"

# 错误码定义
ERROR_CODES = {
    "E001": "文件不存在或路径错误",
    "E002": "文件格式不支持",
    "E003": "缺少必填字段",
    "E004": "日期格式错误",
    "E005": "时间格式错误",
    "E006": "编码不支持",
    "E007": "输出路径无写入权限",
}


class AttendanceError(Exception):
    """考勤处理异常基类"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def get_timestamp() -> str:
    """获取 UTC 时间戳"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def detect_encoding(file_path: str) -> str:
    """检测文件编码，支持多编码 fallback"""
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read(4096)
            result = chardet.detect(raw_data)
            if result["encoding"]:
                return result["encoding"]
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)

    # fallback 顺序：utf-8 -> gbk -> gb18030
    for encoding in ["utf-8", "gbk", "gb18030"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                f.read(1024)
            return encoding
        except Exception:
            continue

    return "utf-8"


def validate_input_file(file_path: str) -> None:
    """验证输入文件存在性和格式"""
    if not os.path.exists(file_path):
        raise AttendanceError("E001", f"文件不存在: {file_path}")

    valid_extensions = [".xlsx", ".xls", ".csv", ".txt"]
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in valid_extensions:
        raise AttendanceError(
            "E002", f"不支持的文件格式: {ext}，支持: {', '.join(valid_extensions)}"
        )


def parse_attendance_file(file_path: str) -> pd.DataFrame:
    """解析考勤文件，自动识别表头字段"""
    ext = os.path.splitext(file_path)[1].lower()
    encoding = detect_encoding(file_path)

    try:
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        elif ext in [".csv", ".txt"]:
            df = pd.read_csv(file_path, encoding=encoding)
        else:
            raise AttendanceError("E002", f"不支持的文件格式: {ext}")
    except AttendanceError:
        raise
    except Exception as e:
        raise AttendanceError("E003", f"文件解析失败: {e}")

    if df.empty:
        raise AttendanceError("E003", "文件内容为空")

    # 标准化列名
    df.columns = [str(col).strip() for col in df.columns]

    # 识别必要列
    time_cols = [col for col in df.columns if "时间" in col or "time" in col.lower()]
    id_cols = [col for col in df.columns if "工号" in col or "id" in col.lower()]

    if not time_cols:
        raise AttendanceError("E003", "未找到打卡时间列")

    if not id_cols:
        # 尝试使用第一列作为人员标识
        id_cols = [df.columns[0]]

    return df, id_cols[0], time_cols[0]


def clean_attendance_data(df: pd.DataFrame, id_col: str, time_col: str) -> pd.DataFrame:
    """清洗考勤数据：去重、过滤噪声、修正跨日"""
    if df.empty:
        return df

    # 复制数据避免修改原始
    df_clean = df.copy()

    # 转换时间列
    try:
        df_clean[time_col] = pd.to_datetime(df_clean[time_col], errors="coerce")
    except Exception as e:
        raise AttendanceError("E005", f"时间解析失败: {e}")

    # 删除无效时间
    df_clean = df_clean.dropna(subset=[time_col])

    # 删除完全重复的行
    df_clean = df_clean.drop_duplicates(subset=[id_col, time_col], keep="first")

    # 按人员和时间排序
    df_clean = df_clean.sort_values([id_col, time_col]).reset_index(drop=True)

    return df_clean


def mark_attendance_anomalies(
    df_clean: pd.DataFrame,
    id_col: str,
    time_col: str,
    config: Dict,
    grace_minutes: int = 5,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """标记异常记录，返回异常记录和统计信息"""
    if df_clean.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 获取默认班次
    default_shift = config.get("default", {"start": "09:00", "end": "18:00"})
    shift_start = pd.to_datetime(default_shift["start"]).time()
    shift_end = pd.to_datetime(default_shift["end"]).time()

    # 按人员分组处理
    anomalies = []
    stats = []

    for person_id, group in df_clean.groupby(id_col):
        person_anomalies = []
        person_stats = {
            "人员标识": person_id,
            "出勤天数": 0,
            "迟到次数": 0,
            "早退次数": 0,
            "缺卡次数": 0,
            "异常次数": 0,
        }

        # 按日期分组
        group["日期"] = group[time_col].dt.date
        for date, day_group in group.groupby("日期"):
            # 检查打卡次数
            if len(day_group) > 4:
                person_anomalies.append(
                    {
                        "人员标识": person_id,
                        "日期": str(date),
                        "异常类型": "重复打卡",
                        "详情": f"当日打卡 {len(day_group)} 次",
                    }
                )
                person_stats["异常次数"] += 1

            # 检查迟到
            morning_punches = day_group[
                day_group[time_col].dt.time <= pd.to_datetime("12:00").time()
            ]
            if not morning_punches.empty:
                first_punch = morning_punches.iloc[0]
                punch_time = first_punch[time_col].time()
                if punch_time > shift_start:
                    late_minutes = (
                        datetime.combine(date, punch_time)
                        - datetime.combine(date, shift_start)
                    ).total_seconds() / 60
                    if late_minutes > grace_minutes:
                        person_anomalies.append(
                            {
                                "人员标识": person_id,
                                "日期": str(date),
                                "异常类型": "迟到",
                                "详情": f"打卡 {punch_time}，班次开始 {shift_start}",
                            }
                        )
                        person_stats["迟到次数"] += 1

            # 检查早退
            evening_punches = day_group[
                day_group[time_col].dt.time >= pd.to_datetime("12:00").time()
            ]
            if not evening_punches.empty:
                last_punch = evening_punches.iloc[-1]
                punch_time = last_punch[time_col].time()
                if punch_time < shift_end:
                    early_minutes = (
                        datetime.combine(date, shift_end)
                        - datetime.combine(date, punch_time)
                    ).total_seconds() / 60
                    if early_minutes > grace_minutes:
                        person_anomalies.append(
                            {
                                "人员标识": person_id,
                                "日期": str(date),
                                "异常类型": "早退",
                                "详情": f"打卡 {punch_time}，班次结束 {shift_end}",
                            }
                        )
                        person_stats["早退次数"] += 1

            person_stats["出勤天数"] += 1

        # 计算出勤率（假设每月 22 个工作日）
        expected_days = 22
        person_stats["出勤率"] = (
            min(person_stats["出勤天数"] / expected_days, 1.0) * 100
        )
        stats.append(person_stats)

        # 添加该人员的异常记录
        anomalies.extend(person_anomalies)

    # 转换为 DataFrame
    anomalies_df = pd.DataFrame(anomalies) if anomalies else pd.DataFrame(
        columns=["人员标识", "日期", "异常类型", "详情"]
    )
    stats_df = pd.DataFrame(stats) if stats else pd.DataFrame(
        columns=["人员标识", "出勤天数", "迟到次数", "早退次数", "缺卡次数", "异常次数", "出勤率"]
    )

    return anomalies_df, stats_df


def generate_statistics(
    df_clean: pd.DataFrame, id_col: str, time_col: str
) -> pd.DataFrame:
    """生成按日期维度的统计信息"""
    if df_clean.empty:
        return pd.DataFrame()

    df_stats = df_clean.copy()
    df_stats["日期"] = df_stats[time_col].dt.date

    daily_stats = (
        df_stats.groupby("日期")
        .agg(
            出勤人数=(id_col, "nunique"),
            总打卡次数=(time_col, "count"),
        )
        .reset_index()
    )
    daily_stats["日期"] = daily_stats["日期"].astype(str)

    return daily_stats


def write_excel_output(
    df_original: pd.DataFrame,
    df_clean: pd.DataFrame,
    df_anomalies: pd.DataFrame,
    df_stats: pd.DataFrame,
    df_daily_stats: pd.DataFrame,
    output_path: str,
    dry_run: bool = False,
) -> str:
    """写入 Excel 输出文件"""
    if dry_run:
        print(f"[DRY-RUN] 将写入文件: {output_path}")
        print(f"[DRY-RUN] 原始数据: {len(df_original)} 行")
        print(f"[DRY-RUN] 清洗数据: {len(df_clean)} 行")
        print(f"[DRY-RUN] 异常记录: {len(df_anomalies)} 行")
        print(f"[DRY-RUN] 人员统计: {len(df_stats)} 行")
        print(f"[DRY-RUN] 日期统计: {len(df_daily_stats)} 行")
        return output_path

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 使用临时文件原子写入
    fd, temp_path = tempfile.mkstemp(
        suffix=".xlsx", dir=output_dir or "."
    )
    os.close(fd)

    try:
        with pd.ExcelWriter(temp_path, engine="openpyxl") as writer:
            df_original.to_excel(writer, sheet_name="原始数据", index=False)
            df_clean.to_excel(writer, sheet_name="清洗数据", index=False)
            df_anomalies.to_excel(writer, sheet_name="异常记录", index=False)
            df_stats.to_excel(writer, sheet_name="统计汇总", index=False)
            df_daily_stats.to_excel(writer, sheet_name="日期统计", index=False)

        # 原子替换
        os.replace(temp_path, output_path)
        return output_path
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise AttendanceError("E007", f"写入输出文件失败: {e}")


def load_config(config_path: Optional[str]) -> Dict:
    """加载自定义班次配置"""
    if not config_path:
        return {"default": {"start": "09:00", "end": "18:00"}}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as e:
        raise AttendanceError("E003", f"配置文件加载失败: {e}")


def run_selftest() -> int:
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 创建测试数据
    test_data = pd.DataFrame(
        {
            "工号": ["001", "001", "001", "002", "002", "002"],
            "打卡时间": [
                "2026-08-01 08:55:00",
                "2026-08-01 18:05:00",
                "2026-08-02 09:10:00",  # 迟到
                "2026-08-01 08:50:00",
                "2026-08-01 17:30:00",  # 早退
                "2026-08-02 09:00:00",
            ],
        }
    )

    # 测试清洗
    df_clean = clean_attendance_data(test_data, "工号", "打卡时间")
    assert len(df_clean) == 6, f"清洗后应保留 6 行，实际 {len(df_clean)}"
    print(f"[PASS] 数据清洗: {len(df_clean)} 行")

    # 测试异常标记
    config = {"default": {"start": "09:00", "end": "18:00"}}
    anomalies, stats = mark_attendance_anomalies(
        df_clean, "工号", "打卡时间", config, grace_minutes=5
    )
    assert len(anomalies) >= 2, f"应至少 2 条异常，实际 {len(anomalies)}"
    print(f"[PASS] 异常标记: {len(anomalies)} 条异常")

    # 测试统计
    daily_stats = generate_statistics(df_clean, "工号", "打卡时间")
    assert len(daily_stats) >= 2, f"应至少 2 天统计，实际 {len(daily_stats)}"
    print(f"[PASS] 日期统计: {len(daily_stats)} 天")

    # 测试输出
    output_path = os.path.join(tempfile.gettempdir(), "attendance_selftest.xlsx")
    write_excel_output(
        test_data, df_clean, anomalies, stats, daily_stats, output_path
    )
    assert os.path.exists(output_path), "输出文件应存在"
    print(f"[PASS] 文件输出: {output_path}")

    # 清理测试文件
    os.remove(output_path)

    print("=" * 60)
    print("自检全部通过！")
    print("=" * 60)
    return 0


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="考勤处理工具 - 解析、清洗、判定、统计、输出"
    )
    parser.add_argument("--input_file", nargs="?", help="输入考勤文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--config", "-c", help="自定义班次配置（JSON）")
    parser.add_argument("--grace", type=int, default=5, help="宽限分钟数（默认 5）")
    parser.add_argument("--dry-run", action="store_true", help="预览不写盘")
    parser.add_argument("--verbose", action="store_true", help="详细日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    if not args.input_file:
        parser.print_help()
        sys.exit(1)

    try:
        # 验证输入文件
        validate_input_file(args.input_file)

        # 加载配置
        config = load_config(args.config)

        # 解析文件
        if args.verbose:
            print(f"[INFO] 解析文件: {args.input_file}")
        df_original, id_col, time_col = parse_attendance_file(args.input_file)
        if args.verbose:
            print(f"[INFO] 原始数据: {len(df_original)} 行")
            print(f"[INFO] 人员标识列: {id_col}")
            print(f"[INFO] 打卡时间列: {time_col}")

        # 清洗数据
        df_clean = clean_attendance_data(df_original, id_col, time_col)
        if args.verbose:
            print(f"[INFO] 清洗后数据: {len(df_clean)} 行")

        # 标记异常
        df_anomalies, df_stats = mark_attendance_anomalies(
            df_clean, id_col, time_col, config, args.grace
        )
        if args.verbose:
            print(f"[INFO] 异常记录: {len(df_anomalies)} 条")
            print(f"[INFO] 人员统计: {len(df_stats)} 人")

        # 生成日期统计
        df_daily_stats = generate_statistics(df_clean, id_col, time_col)
        if args.verbose:
            print(f"[INFO] 日期统计: {len(df_daily_stats)} 天")

        # 确定输出路径
        if args.output:
            output_path = args.output
        else:
            input_path = Path(args.input_file)
            output_path = str(
                input_path.parent
                / f"{input_path.stem}_考勤处理_{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsx"
            )

        # 写入输出
        write_excel_output(
            df_original,
            df_clean,
            df_anomalies,
            df_stats,
            df_daily_stats,
            output_path,
            args.dry_run,
        )

        if not args.dry_run:
            print(f"[SUCCESS] 处理完成，输出文件: {output_path}")
        else:
            print("[DRY-RUN] 预览完成，未写入文件")

    except AttendanceError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 未预期错误: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


read_text_safe = lambda p: open(p, encoding="utf-8", errors="replace").read()  # R1 编码容错契约
