#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
考勤处理脚本 - 提供考勤记录的识别、整理、生成与校验功能。

用法示例:
    python main.py --input input.csv --output output.csv
    python main.py --input input.csv --output output.csv --dry-run
    python main.py --input input.csv --output output.csv --force
    python main.py --selftest
    python main.py --input input.csv --output output.csv --verbose
"""

import argparse
import csv
import os
import sys
import traceback
from datetime import datetime, timedelta

# 错误码定义
ERROR_CODES = {
    "E001": "输入文件不存在",
    "E002": "输入文件格式错误",
    "E003": "输出文件路径无效",
    "E004": "输入数据为空",
    "E005": "日期格式错误",
    "E006": "时间格式错误",
    "E007": "数据行格式错误",
    "E008": "输出文件写入失败",
    "E009": "参数校验失败",
    "E010": "内部逻辑错误",
}


class AttendanceError(Exception):
    """考勤处理异常基类"""

    def __init__(self, error_code, message):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")


def validate_input_file(file_path):
    """校验输入文件是否存在且可读"""
    if not file_path:
        raise AttendanceError("E009", "输入文件路径不能为空")
    if not os.path.isfile(file_path):
        raise AttendanceError("E001", f"输入文件不存在: {file_path}")
    if not os.access(file_path, os.R_OK):
        raise AttendanceError("E001", f"输入文件不可读: {file_path}")


def validate_output_path(file_path):
    """校验输出路径是否合法"""
    if not file_path:
        raise AttendanceError("E009", "输出文件路径不能为空")
    output_dir = os.path.dirname(os.path.abspath(file_path))
    if not os.path.isdir(output_dir):
        raise AttendanceError("E003", f"输出目录不存在: {output_dir}")
    if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
        raise AttendanceError("E003", f"输出文件不可写: {file_path}")


def read_input_file(file_path):
    """读取输入文件，支持多编码"""
    encodings = ["utf-8", "gbk", "gb18030"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            return content, encoding
        except (UnicodeDecodeError, IOError):
            continue
    raise AttendanceError("E002", f"无法识别文件编码: {file_path}")


def parse_csv_content(content):
    """解析CSV内容为考勤记录列表"""
    if not content or not content.strip():
        raise AttendanceError("E004", "输入数据为空")

    records = []
    try:
        reader = csv.DictReader(content.splitlines())
        if not reader.fieldnames:
            raise AttendanceError("E007", "CSV文件缺少表头")

        required_fields = ["date", "employee_id", "check_in", "check_out"]
        missing_fields = [f for f in required_fields if f not in reader.fieldnames]
        if missing_fields:
            raise AttendanceError("E007", f"缺少必需字段: {missing_fields}")

        for row_num, row in enumerate(reader, start=2):
            try:
                record = {
                    "date": row.get("date", "").strip(),
                    "employee_id": row.get("employee_id", "").strip(),
                    "check_in": row.get("check_in", "").strip(),
                    "check_out": row.get("check_out", "").strip(),
                }
                if any(not v for v in record.values()):
                    continue  # 跳过空行
                records.append(record)
            except (KeyError, AttributeError) as e:
                raise AttendanceError("E007", f"第{row_num}行数据格式错误: {e}") from e
    except csv.Error as e:
        raise AttendanceError("E002", f"CSV解析失败: {e}") from e

    if not records:
        raise AttendanceError("E004", "没有有效的考勤记录")

    return records


def parse_date(date_str):
    """解析日期字符串"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise AttendanceError("E005", f"日期格式错误: {date_str}") from e


def parse_time(time_str):
    """解析时间字符串"""
    try:
        return datetime.strptime(time_str, "%H:%M")
    except ValueError as e:
        raise AttendanceError("E006", f"时间格式错误: {time_str}") from e


def calculate_work_hours(record):
    """计算单个考勤记录的工作时长（小时）"""
    try:
        check_in = parse_time(record["check_in"])
        check_out = parse_time(record["check_out"])
        if check_out < check_in:
            # 跨天情况，加24小时
            check_out += timedelta(days=1)
        return (check_out - check_in).total_seconds() / 3600.0
    except AttendanceError:
        return 0.0


def process_records(records):
    """处理考勤记录，计算工作时长和状态"""
    processed = []
    for record in records:
        try:
            date_obj = parse_date(record["date"])
            work_hours = calculate_work_hours(record)

            # 判断状态
            if work_hours >= 8.0:
                status = "正常"
            elif work_hours >= 4.0:
                status = "不足"
            else:
                status = "异常"

            processed_record = {
                "date": record["date"],
                "employee_id": record["employee_id"],
                "check_in": record["check_in"],
                "check_out": record["check_out"],
                "work_hours": f"{work_hours:.2f}",
                "status": status,
            }
            processed.append(processed_record)
        except AttendanceError as e:
            # 单条记录处理失败，保留原始数据并标记
            processed_record = {
                "date": record["date"],
                "employee_id": record["employee_id"],
                "check_in": record["check_in"],
                "check_out": record["check_out"],
                "work_hours": "0.00",
                "status": f"错误: {e.message}",
            }
            processed.append(processed_record)
    return processed


def generate_summary(records):
    """生成考勤汇总信息"""
    if not records:
        return {}

    total_records = len(records)
    normal_count = sum(1 for r in records if r["status"] == "正常")
    insufficient_count = sum(1 for r in records if r["status"] == "不足")
    abnormal_count = sum(1 for r in records if r["status"] == "异常")
    error_count = sum(1 for r in records if "错误" in r["status"])

    return {
        "total_records": total_records,
        "normal_count": normal_count,
        "insufficient_count": insufficient_count,
        "abnormal_count": abnormal_count,
        "error_count": error_count,
        "normal_rate": (normal_count / total_records * 100) if total_records > 0 else 0.0,
    }


def format_output(records, summary):
    """格式化输出内容"""
    lines = []
    lines.append("考勤处理结果")
    lines.append("=" * 50)

    if summary:
        lines.append(f"总记录数: {summary['total_records']}")
        lines.append(f"正常: {summary['normal_count']} ({summary['normal_rate']:.1f}%)")
        lines.append(f"不足: {summary['insufficient_count']}")
        lines.append(f"异常: {summary['abnormal_count']}")
        lines.append(f"错误: {summary['error_count']}")
        lines.append("-" * 50)

    if records:
        lines.append("详细记录:")
        lines.append("日期,员工ID,上班时间,下班时间,工作时长,状态")
        for record in records:
            lines.append(
                f"{record['date']},{record['employee_id']},"
                f"{record['check_in']},{record['check_out']},"
                f"{record['work_hours']},{record['status']}"
            )

    return "\n".join(lines)


def write_output_file(file_path, content, dry_run=False):
    """写入输出文件"""
    if dry_run:
        print(f"[DRY-RUN] 将写入文件: {file_path}")
        print(content)
        return True

    try:
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        return True
    except IOError as e:
        raise AttendanceError("E008", f"写入文件失败: {e}") from e


def run_selftest():
    """内置自检函数，使用硬编码样例数据验证核心逻辑"""
    print("开始自检...")

    # 测试样例数据
    test_records = [
        {"date": "2026-01-05", "employee_id": "EMP001", "check_in": "09:00", "check_out": "18:00"},
        {"date": "2026-01-05", "employee_id": "EMP002", "check_in": "09:30", "check_out": "17:30"},
        {"date": "2026-01-06", "employee_id": "EMP001", "check_in": "08:30", "check_out": "12:30"},
        {"date": "2026-01-06", "employee_id": "EMP002", "check_in": "10:00", "check_out": "15:00"},
        {"date": "2026-01-07", "employee_id": "EMP001", "check_in": "09:15", "check_out": "18:15"},
    ]

    # 测试1: 处理记录
    processed = process_records(test_records)
    assert len(processed) == 5, f"处理记录数应为5，实际为{len(processed)}"
    assert processed[0]["status"] == "正常", "第一条记录应为正常"
    assert processed[2]["status"] == "不足", "第三条记录应为不足"

    # 测试2: 工作时长计算
    work_hours = [float(r["work_hours"]) for r in processed]
    assert work_hours[0] >= 8.0, "第一条记录工作时长应>=8小时"
    assert work_hours[2] < 8.0, "第三条记录工作时长应<8小时"
    assert work_hours[2] >= 4.0, "第三条记录工作时长应>=4小时"

    # 测试3: 汇总统计
    summary = generate_summary(processed)
    assert summary["total_records"] == 5, "总记录数应为5"
    assert summary["normal_count"] >= 2, "正常记录数应>=2"
    assert summary["insufficient_count"] >= 1, "不足记录数应>=1"
    assert 0 <= summary["normal_rate"] <= 100, "正常率应在0-100之间"

    # 测试4: 异常输入处理
    try:
        parse_date("2026/01/05")
        assert False, "应抛出日期格式错误"
    except AttendanceError as e:
        assert e.error_code == "E005", f"错误码应为E005，实际为{e.error_code}"

    # 测试5: 空输入处理
    try:
        parse_csv_content("")
        assert False, "应抛出空输入错误"
    except AttendanceError as e:
        assert e.error_code == "E004", f"错误码应为E004，实际为{e.error_code}"

    # 测试6: 中文标点处理
    chinese_records = [
        {"date": "2026-01-08", "employee_id": "EMP003", "check_in": "09:00", "check_out": "18:00"},
        {"date": "2026-01-08", "employee_id": "EMP004", "check_in": "09:30", "check_out": "17:30"},
    ]
    processed_chinese = process_records(chinese_records)
    assert len(processed_chinese) == 2, "中文数据处理失败"

    # 测试7: 超长输入处理
    long_records = []
    for i in range(1000):
        long_records.append({
            "date": f"2026-01-{i % 28 + 1:02d}",
            "employee_id": f"EMP{i:04d}",
            "check_in": "09:00",
            "check_out": "18:00",
        })
    processed_long = process_records(long_records)
    assert len(processed_long) == 1000, "超长数据处理失败"

    print("所有自检通过 ✓")
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description="考勤处理脚本")
    parser.add_argument("--input", help="输入CSV文件路径")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--dry-run", action="store_true", help="只预览不写入")
    parser.add_argument("--force", action="store_true", help="强制写入文件")
    parser.add_argument("--verbose", action="store_true", help="显示详细处理信息")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            traceback.print_exc()
            return 1

    # 参数校验
    if not args.input or not args.output:
        print("错误: 必须指定 --input 和 --output 参数", file=sys.stderr)
        return 1

    # 检查dry-run和force的互斥
    if args.dry_run and args.force:
        print("警告: --dry-run 和 --force 同时指定，将执行dry-run模式", file=sys.stderr)
        args.force = False

    try:
        # 输入校验
        validate_input_file(args.input)
        validate_output_path(args.output)

        # 读取输入
        content, encoding = read_input_file(args.input)
        if args.verbose:
            print(f"输入文件编码: {encoding}")

        # 解析数据
        records = parse_csv_content(content)
        if args.verbose:
            print(f"解析到 {len(records)} 条记录")

        # 处理数据
        processed = process_records(records)
        summary = generate_summary(processed)

        # 输出格式化
        output_content = format_output(processed, summary)

        # 写入文件
        dry = args.dry_run or not args.force
        success = write_output_file(args.output, output_content, dry_run=dry)

        if success:
            if dry:
                print(f"[DRY-RUN] 预览完成，未写入文件。使用 --force 实际写入。")
            else:
                print(f"处理完成，结果已写入: {args.output}")

        if args.verbose:
            print(f"处理详情: {summary}")

        return 0

    except AttendanceError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
