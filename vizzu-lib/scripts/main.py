#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — vizzu-lib 技能核心逻辑（clean-room 独立实现）

本脚本仅依据功能规格独立编写，不复制任何既有代码。
提供：
  - 数据校验与清洗（缺失值、类型异常标注）
  - 图表类型与动画配置生成（面向 Vizzu 库的配置片段）
  - 内置硬编码样例数据的离线自检（--selftest）

错误码约定：
  E001 参数错误
  E002 数据为空
  E003 数据格式不支持
  E004 缺少必需列
  E005 数据类型异常
  E006 缺失值过多
  E007 图表类型不支持
  E008 配置生成失败
  E009 自检失败
  E010 未知错误
"""

import argparse
import csv
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
SUPPORTED_CHART_TYPES = ("bar", "line", "area", "scatter", "pie")
SUPPORTED_INPUT_FORMATS = ("csv", "json")
REQUIRED_COLUMNS = ("category", "value")
MISSING_VALUE_THRESHOLD = 0.3  # 缺失值占比超过 30% 视为异常


# ---------------------------------------------------------------------------
# 错误处理辅助
# ---------------------------------------------------------------------------
class VizzuError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _raise(code: str, message: str) -> None:
    """统一抛错入口。"""
    raise VizzuError(code, message)


# ---------------------------------------------------------------------------
# 数据读取与解析
# ---------------------------------------------------------------------------
def read_data(source: str, fmt: str = "auto") -> List[Dict[str, Any]]:
    """
    从文件或 URL 读取数据（仅支持 CSV / JSON）。
    实际实现中不访问网络，仅做本地文件解析；URL 场景由上层调用方处理。
    """
    if fmt not in ("auto", "csv", "json"):
        _raise("E003", f"不支持的数据格式: {fmt}")

    try:
        if fmt == "csv" or (fmt == "auto" and source.lower().endswith(".csv")):
            return _read_csv(source)
        if fmt == "json" or (fmt == "auto" and source.lower().endswith(".json")):
            return _read_json(source)
        _raise("E003", f"无法自动识别数据格式: {source}")
    except VizzuError:
        raise
    except Exception as exc:
        _raise("E001", f"读取文件失败: {exc}")


def _read_csv(path: str) -> List[Dict[str, Any]]:
    """解析 CSV 文件为字典列表。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = [dict(row) for row in reader]
    except FileNotFoundError:
        _raise("E001", f"文件不存在: {path}")
    except Exception as exc:
        _raise("E001", f"CSV 解析失败: {exc}")
    if not rows:
        _raise("E002", "CSV 文件为空")
    return rows


def _read_json(path: str) -> List[Dict[str, Any]]:
    """解析 JSON 文件为字典列表。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        _raise("E001", f"文件不存在: {path}")
    except Exception as exc:
        _raise("E001", f"JSON 解析失败: {exc}")

    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and "data" in data:
        rows = data["data"]
    else:
        _raise("E003", "JSON 结构必须是数组或包含 data 字段的对象")

    if not rows:
        _raise("E002", "JSON 数据为空")
    return rows


# ---------------------------------------------------------------------------
# 数据清洗与校验
# ---------------------------------------------------------------------------
def clean_data(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    清洗数据：
      - 检查必需列
      - 识别缺失值
      - 检查类型异常
    返回 (清洗后数据, 警告信息列表)。
    """
    if not rows:
        _raise("E002", "输入数据为空")

    # 检查必需列
    if not all(col in rows[0] for col in REQUIRED_COLUMNS):
        missing = [col for col in REQUIRED_COLUMNS if col not in rows[0]]
        _raise("E004", f"缺少必需列: {missing}")

    warnings: List[str] = []
    cleaned: List[Dict[str, Any]] = []
    missing_count = 0

    for idx, row in enumerate(rows):
        new_row = dict(row)
        # 缺失值检测
        for col in REQUIRED_COLUMNS:
            val = new_row.get(col)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                missing_count += 1
                new_row[col] = None
                warnings.append(f"第 {idx + 1} 行: 列 '{col}' 缺失值")

        # 类型检查：value 列应可转为数值
        if new_row.get("value") is not None:
            try:
                new_row["value"] = float(new_row["value"])
            except (TypeError, ValueError):
                warnings.append(f"第 {idx + 1} 行: 列 'value' 类型异常，已置为 None")
                new_row["value"] = None
                missing_count += 1

        cleaned.append(new_row)

    # 缺失值过多检查
    total_cells = len(cleaned) * len(REQUIRED_COLUMNS)
    if total_cells > 0 and missing_count / total_cells > MISSING_VALUE_THRESHOLD:
        _raise("E006", f"缺失值占比过高: {missing_count / total_cells:.1%}")

    return cleaned, warnings


# ---------------------------------------------------------------------------
# 图表配置生成（面向 Vizzu 库）
# ---------------------------------------------------------------------------
def generate_chart_config(
    data: List[Dict[str, Any]],
    chart_type: str = "bar",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成 Vizzu 库可用的图表配置片段。
    支持柱状图、折线图、面积图、散点图、饼图。
    """
    if chart_type not in SUPPORTED_CHART_TYPES:
        _raise("E007", f"不支持的图表类型: {chart_type}，可选: {SUPPORTED_CHART_TYPES}")

    if not data:
        _raise("E002", "无数据可配置")

    # 基本配置骨架
    config: Dict[str, Any] = {
        "data": data,
        "chartType": chart_type,
        "x": "category",
        "y": "value",
    }

    if title:
        config["title"] = title

    # 按图表类型补充特定配置
    try:
        if chart_type == "pie":
            config["angle"] = "value"
            config["label"] = "category"
        elif chart_type == "scatter":
            config["x"] = "category"
            config["y"] = "value"
            config["size"] = "value"
        # bar/line/area 使用通用配置即可
    except Exception as exc:
        _raise("E008", f"图表配置生成失败: {exc}")

    # 为动画添加默认状态切换（时间轴叙事基础）
    config["animation"] = {
        "duration": 800,
        "easing": "easeInOut",
        "sort": "byValue",
    }

    return config


# ---------------------------------------------------------------------------
# 核心流程编排
# ---------------------------------------------------------------------------
def process_data(
    source: str,
    fmt: str = "auto",
    chart_type: str = "bar",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    完整数据处理流程：
      读取 -> 清洗 -> 生成配置。
    """
    rows = read_data(source, fmt)
    cleaned, warnings = clean_data(rows)
    config = generate_chart_config(cleaned, chart_type, title)
    return {"config": config, "warnings": warnings}


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，离线可运行）
# ---------------------------------------------------------------------------
def _selftest() -> None:
    """内置样例数据的离线自检，不依赖外部文件或网络。"""
    print("开始自检...")

    # 内置样例数据（硬编码，不读外部文件）
    sample_data = [
        {"category": "A", "value": 10},
        {"category": "B", "value": 25},
        {"category": "C", "value": 15},
        {"category": "D", "value": 30},
    ]

    # 测试 1: 数据清洗
    try:
        cleaned, warnings = clean_data(sample_data)
        assert len(cleaned) == 4, "清洗后数据行数应为 4"
        assert all(row["value"] is not None for row in cleaned), "所有 value 不应为 None"
        assert isinstance(cleaned[0]["value"], float), "value 应转为 float"
        print("  [PASS] 数据清洗")
    except AssertionError as exc:
        _raise("E009", f"自检失败 - 数据清洗: {exc}")

    # 测试 2: 缺失值识别
    try:
        dirty_data = [
            {"category": "A", "value": 10},
            {"category": "B", "value": None},
            {"category": "C", "value": "abc"},  # 类型异常
        ]
        cleaned_dirty, warnings_dirty = clean_data(dirty_data)
        assert len(cleaned_dirty) == 3, "脏数据清洗后行数应为 3"
        assert any(w for w in warnings_dirty if "缺失" in w), "应包含缺失值警告"
        assert any(w for w in warnings_dirty if "类型异常" in w), "应包含类型异常警告"
        print("  [PASS] 缺失值/类型异常识别")
    except AssertionError as exc:
        _raise("E009", f"自检失败 - 异常识别: {exc}")

    # 测试 3: 图表配置生成（所有支持类型）
    try:
        for ctype in SUPPORTED_CHART_TYPES:
            cfg = generate_chart_config(sample_data, ctype)
            assert cfg["chartType"] == ctype, f"图表类型应为 {ctype}"
            assert cfg["x"] == "category", "x 轴应为 category"
            assert cfg["y"] == "value", "y 轴应为 value"
            assert "animation" in cfg, "应包含动画配置"
            # 宽松验证：动画时长在合理区间
            duration = cfg["animation"]["duration"]
            assert 0 < duration < 5000, "动画时长应在合理范围"
        print("  [PASS] 图表配置生成（全部类型）")
    except AssertionError as exc:
        _raise("E009", f"自检失败 - 配置生成: {exc}")

    # 测试 4: 缺失值过多检测（应抛错）
    try:
        too_many_missing = [
            {"category": "A", "value": None},
            {"category": "B", "value": None},
            {"category": "C", "value": None},
        ]
        try:
            clean_data(too_many_missing)
            raise AssertionError("缺失值过多时应抛出 E006 错误")
        except VizzuError as exc:
            assert exc.code == "E006", f"错误码应为 E006，实际为 {exc.code}"
        print("  [PASS] 缺失值过多检测")
    except AssertionError as exc:
        _raise("E009", f"自检失败 - 缺失值过多: {exc}")

    # 测试 5: 不支持的图表类型（应抛错）
    try:
        try:
            generate_chart_config(sample_data, "3d")
            raise AssertionError("不支持的图表类型应抛出 E007 错误")
        except VizzuError as exc:
            assert exc.code == "E007", f"错误码应为 E007，实际为 {exc.code}"
        print("  [PASS] 不支持图表类型检测")
    except AssertionError as exc:
        _raise("E009", f"自检失败 - 图表类型: {exc}")

    # 测试 6: 完整流程（使用临时 JSON 文件，但不依赖外部数据）
    try:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(sample_data, tmp)
            tmp_path = tmp.name

        try:
            result = process_data(tmp_path, "json", "bar", "自检图表")
            assert "config" in result, "应返回 config"
            assert result["config"]["title"] == "自检图表", "标题应正确"
            assert result["config"]["chartType"] == "bar", "图表类型应为 bar"
        finally:
            os.unlink(tmp_path)  # 清理临时文件
        print("  [PASS] 完整流程")
    except AssertionError as exc:
        _raise("E009", f"自检失败 - 完整流程: {exc}")
    except Exception as exc:
        _raise("E009", f"自检失败 - 完整流程异常: {exc}")

    print("自检全部通过 ✅")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="vizzu-lib 技能核心逻辑：数据清洗与图表配置生成"
    )
    parser.add_argument("--input", "-i", help="输入数据文件路径（CSV/JSON）")
    parser.add_argument("--format", "-f", choices=["auto", "csv", "json"], default="auto",
                        help="输入数据格式（默认 auto 自动识别）")
    parser.add_argument("--chart-type", "-t", choices=SUPPORTED_CHART_TYPES, default="bar",
                        help="图表类型（默认 bar）")
    parser.add_argument("--title", help="图表标题（可选）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（不依赖外部文件）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            _selftest()
            return 0
        except VizzuError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        parser.error("必须提供 --input 或使用 --selftest")

    try:
        result = process_data(args.input, args.format, args.chart_type, args.title)
    except VizzuError as exc:
        print(f"处理失败: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] 未知错误: {exc}", file=sys.stderr)
        return 1

    # 输出结果（JSON）
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
