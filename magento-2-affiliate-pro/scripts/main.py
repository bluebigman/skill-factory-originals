#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
magento-2-affiliate-pro — Magento2 联盟营销配置审查工具

本脚本仅依据功能规格独立实现（clean-room），不参考任何既有代码。
功能：对 Magento2 联盟营销扩展的配置数据进行结构化审查，
      输出检查报告（合规/告警/错误）。

用法：
    python scripts/main.py <配置文件路径>
    python scripts/main.py --selftest

错误码：
    E001 参数缺失或非法
    E002 文件不存在或不可读
    E003 文件格式不支持
    E004 配置内容为空
    E005 配置解析失败
    E006 缺少必需字段
    E007 字段类型错误
    E008 配置值超出允许范围
    E009 内部逻辑错误
    E010 未预期的异常
"""

import argparse
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {".json", ".yaml", ".yml"}

# 必需字段（顶级）
REQUIRED_TOP_LEVEL_FIELDS = ["extension_name", "version", "settings"]

# 设置项中必需字段
REQUIRED_SETTING_FIELDS = ["cookie_name", "commission_rate", "enabled"]

# 允许的 commission_rate 范围
COMMISSION_RATE_MIN = 0.0
COMMISSION_RATE_MAX = 100.0

# 审查结果级别
LEVEL_PASS = "PASS"
LEVEL_WARN = "WARN"
LEVEL_ERROR = "ERROR"


# ---------------------------------------------------------------------------
# 数据模型（轻量校验类）
# ---------------------------------------------------------------------------

class ConfigReport:
    """配置审查报告对象，收集所有检查结果。"""

    def __init__(self, source_name=""):
        self.source_name = source_name
        self.items = []          # 每条检查结果
        self.error_code = None   # 致命错误码（如有）

    def add(self, level, code, message):
        """添加一条检查结果。"""
        self.items.append({
            "level": level,
            "code": code,
            "message": message,
        })

    def add_error(self, code, message):
        """添加致命错误并记录错误码。"""
        self.error_code = code
        self.add(LEVEL_ERROR, code, message)

    def summary(self):
        """生成摘要统计。"""
        counts = {LEVEL_PASS: 0, LEVEL_WARN: 0, LEVEL_ERROR: 0}
        for item in self.items:
            counts[item["level"]] = counts.get(item["level"], 0) + 1
        return counts

    def to_dict(self):
        """转换为字典结构（便于序列化）。"""
        return {
            "source": self.source_name,
            "summary": self.summary(),
            "checks": self.items,
            "fatal_error": self.error_code,
        }


# ---------------------------------------------------------------------------
# 核心审查逻辑
# ---------------------------------------------------------------------------

def validate_structure(config, report):
    """
    校验配置的顶层结构完整性。

    参数:
        config: 已解析的配置对象（dict）
        report: ConfigReport 实例

    返回:
        bool: 结构是否基本可用（若为 False 则后续检查无意义）
    """
    if not isinstance(config, dict):
        report.add_error("E006", "配置根节点必须是 JSON 对象/字典结构")
        return False

    # 检查必需字段是否存在
    missing = [f for f in REQUIRED_TOP_LEVEL_FIELDS if f not in config]
    if missing:
        report.add_error(
            "E006",
            f"缺少必需顶级字段: {', '.join(missing)}"
        )
        return False

    # 检查字段类型
    if not isinstance(config["extension_name"], str):
        report.add_error("E007", "extension_name 必须是字符串")
        return False

    if not isinstance(config["version"], str):
        report.add_error("E007", "version 必须是字符串")
        return False

    if not isinstance(config["settings"], dict):
        report.add_error("E007", "settings 必须是对象/字典")
        return False

    # 检查 settings 中的必需字段
    settings = config["settings"]
    missing_settings = [f for f in REQUIRED_SETTING_FIELDS if f not in settings]
    if missing_settings:
        report.add_error(
            "E006",
            f"settings 中缺少必需字段: {', '.join(missing_settings)}"
        )
        return False

    return True


def validate_setting_values(config, report):
    """
    校验 settings 中各字段的值是否合理。

    参数:
        config: 已解析的配置对象
        report: ConfigReport 实例
    """
    settings = config["settings"]

    # ---- cookie_name ----
    cookie_name = settings["cookie_name"]
    if not isinstance(cookie_name, str):
        report.add(LEVEL_ERROR, "E007", "cookie_name 必须是字符串")
    elif len(cookie_name.strip()) == 0:
        report.add(LEVEL_WARN, "E008", "cookie_name 为空字符串，可能导致追踪失效")
    elif len(cookie_name) > 64:
        report.add(LEVEL_WARN, "E008", "cookie_name 长度超过 64 字符，可能被浏览器拒绝")
    else:
        report.add(LEVEL_PASS, "OK", f"cookie_name 格式合规: '{cookie_name}'")

    # ---- commission_rate ----
    rate = settings["commission_rate"]
    if not isinstance(rate, (int, float)):
        report.add(LEVEL_ERROR, "E007", "commission_rate 必须是数字")
    elif isinstance(rate, bool):
        report.add(LEVEL_ERROR, "E007", "commission_rate 不能是布尔值")
    else:
        if rate < COMMISSION_RATE_MIN:
            report.add(LEVEL_WARN, "E008",
                       f"commission_rate 低于下限 {COMMISSION_RATE_MIN}（当前: {rate}）")
        elif rate > COMMISSION_RATE_MAX:
            report.add(LEVEL_WARN, "E008",
                       f"commission_rate 高于上限 {COMMISSION_RATE_MAX}（当前: {rate}）")
        else:
            report.add(LEVEL_PASS, "OK", f"commission_rate 在合理范围内: {rate}%")

    # ---- enabled ----
    enabled = settings["enabled"]
    if not isinstance(enabled, bool):
        report.add(LEVEL_ERROR, "E007", "enabled 必须是布尔值")
    else:
        report.add(LEVEL_PASS, "OK", f"enabled 类型正确: {enabled}")

    # ---- 可选字段的宽松检查（仅告警不致命） ----
    if "tracking_duration" in settings:
        dur = settings["tracking_duration"]
        if not isinstance(dur, (int, float)) or isinstance(dur, bool):
            report.add(LEVEL_WARN, "E007", "tracking_duration 应为数字（天数）")
        elif dur <= 0:
            report.add(LEVEL_WARN, "E008", "tracking_duration 应大于 0")

    if "payout_threshold" in settings:
        th = settings["payout_threshold"]
        if not isinstance(th, (int, float)) or isinstance(th, bool):
            report.add(LEVEL_WARN, "E007", "payout_threshold 应为数字")
        elif th < 0:
            report.add(LEVEL_WARN, "E008", "payout_threshold 不应为负数")


def run_review(config_data, source_name=""):
    """
    对配置数据执行完整审查流程。

    参数:
        config_data: 解析后的配置对象
        source_name: 来源名称（文件名或标识）

    返回:
        ConfigReport 实例
    """
    report = ConfigReport(source_name=source_name)

    # 空内容检查
    if config_data is None:
        report.add_error("E004", "配置内容为空")
        return report

    # 结构校验
    if not validate_structure(config_data, report):
        # 结构致命错误，不再继续
        return report

    # 值校验
    validate_setting_values(config_data, report)

    return report


# ---------------------------------------------------------------------------
# 文件读取与解析
# ---------------------------------------------------------------------------

def load_config_file(filepath):
    """
    根据文件扩展名读取并解析配置文件。

    参数:
        filepath: 文件路径字符串

    返回:
        (config_data, error_code, error_message)

    说明:
        优先使用标准库。YAML 解析尝试使用 PyYAML，若未安装则报错提示。
    """
    path = Path(filepath)

    # 文件存在性检查
    if not path.exists():
        return None, "E002", f"文件不存在: {filepath}"
    if not path.is_file():
        return None, "E002", f"路径不是文件: {filepath}"
    if not os.access(path, os.R_OK):
        return None, "E002", f"文件不可读: {filepath}"

    # 扩展名检查
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None, "E003", f"不支持的文件格式: {ext}（仅支持 {', '.join(SUPPORTED_EXTENSIONS)}）"

    # 读取内容
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None, "E005", "文件编码不是 UTF-8，解析失败"
    except OSError as exc:
        return None, "E002", f"读取文件失败: {exc}"

    # 空文件检查
    if not content.strip():
        return None, "E004", "配置文件为空"

    # 按格式解析
    try:
        if ext == ".json":
            data = json.loads(content)
        else:  # YAML
            try:
                import yaml  # pip install pyyaml
            except ImportError:
                return None, "E003", "解析 YAML 需要 PyYAML，请先安装: pip install pyyaml"
            data = yaml.safe_load(content)
    except json.JSONDecodeError as exc:
        return None, "E005", f"JSON 解析失败: {exc}"
    except Exception as exc:  # YAML 解析异常
        return None, "E005", f"YAML 解析失败: {exc}"

    return data, None, None


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_report(report, verbose=True):
    """
    将报告格式化为可读文本。

    参数:
        report: ConfigReport 实例
        verbose: 是否输出每条检查详情

    返回:
        格式化字符串
    """
    lines = []
    lines.append("=" * 60)
    lines.append(f"配置审查报告 — 来源: {report.source_name or '(未命名)'}")
    lines.append("=" * 60)

    summary = report.summary()
    lines.append(f"汇总: PASS={summary[LEVEL_PASS]}, "
                 f"WARN={summary[LEVEL_WARN]}, "
                 f"ERROR={summary[LEVEL_ERROR]}")

    if report.error_code:
        lines.append(f"致命错误: [{report.error_code}]")

    if verbose:
        lines.append("-" * 60)
        for item in report.items:
            lines.append(f"[{item['level']}] {item['code']}: {item['message']}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------

def run_selftest():
    """
    内置硬编码样例数据，离线自检核心逻辑。

    不使用任何外部文件、不访问网络、不依赖工作目录。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("开始自检...")

    # ---- 样例 1: 合规配置 ----
    good_config = {
        "extension_name": "Affiliate Pro",
        "version": "2.1.0",
        "settings": {
            "cookie_name": "affiliate_track",
            "commission_rate": 15.0,
            "enabled": True,
            "tracking_duration": 30,
            "payout_threshold": 50.0,
        }
    }

    report = run_review(good_config, source_name="selftest-good")
    summary = report.summary()

    # 宽松断言：不应有致命错误，ERROR 数应为 0
    assert report.error_code is None, f"合规配置不应产生致命错误，实际: {report.error_code}"
    assert summary[LEVEL_ERROR] == 0, f"合规配置不应有 ERROR，实际: {summary[LEVEL_ERROR]}"
    # 至少应该有 3 条 PASS（cookie_name, commission_rate, enabled）
    assert summary[LEVEL_PASS] >= 3, f"合规配置至少应有 3 条 PASS，实际: {summary[LEVEL_PASS]}"

    # ---- 样例 2: 问题配置（缺字段、类型错误、值越界） ----
    bad_config = {
        "extension_name": 123,           # 类型错误
        "version": "1.0",
        "settings": {
            "cookie_name": "",            # 空字符串（告警）
            "commission_rate": 150,       # 超出上限（告警）
            "enabled": "yes",             # 类型错误（ERROR）
        }
    }

    report2 = run_review(bad_config, source_name="selftest-bad")
    summary2 = report2.summary()

    # 宽松断言：该配置必然有 ERROR（类型错误导致）
    assert summary2[LEVEL_ERROR] >= 1, f"问题配置应至少有 1 个 ERROR，实际: {summary2[LEVEL_ERROR]}"
    # 致命错误码应为 E007（类型错误）或 E006（缺字段）
    assert report2.error_code in ("E006", "E007"), \
        f"致命错误码应为 E006/E007，实际: {report2.error_code}"

    # ---- 样例 3: 空配置 ----
    report3 = run_review(None, source_name="selftest-empty")
    assert report3.error_code == "E004", f"空配置应产生 E004，实际: {report3.error_code}"

    # ---- 样例 4: 缺少必需字段 ----
    incomplete = {"extension_name": "X"}  # 缺少 version 和 settings
    report4 = run_review(incomplete, source_name="selftest-incomplete")
    assert report4.error_code == "E006", f"缺字段应产生 E006，实际: {report4.error_code}"

    # ---- 样例 5: 文件加载逻辑（使用临时文件，不依赖外部） ----
    import tempfile
    import json as _json

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        _json.dump(good_config, f)
        tmp_path = f.name

    try:
        data, err_code, err_msg = load_config_file(tmp_path)
        assert err_code is None, f"临时文件加载不应出错，实际: {err_code} {err_msg}"
        assert data is not None, "加载结果不应为 None"
        assert data["extension_name"] == "Affiliate Pro", "加载内容与预期不符"
    finally:
        os.unlink(tmp_path)

    # ---- 样例 6: 不存在的文件 ----
    data, err_code, _ = load_config_file("/nonexistent/path/config.json")
    assert err_code == "E002", f"不存在文件应产生 E002，实际: {err_code}"

    # ---- 样例 7: 不支持的文件格式 ----
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write("<config/>")
        tmp_xml = f.name
    try:
        _, err_code, _ = load_config_file(tmp_xml)
        assert err_code == "E003", f"不支持格式应产生 E003，实际: {err_code}"
    finally:
        os.unlink(tmp_xml)

    print("自检通过: 所有核心逻辑验证成功 ✓")
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main(argv=None):
    """
    命令行入口函数。

    参数:
        argv: 命令行参数列表（默认使用 sys.argv[1:]）

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="Magento2 联盟营销配置审查工具 (magento-2-affiliate-pro)"
    )
    parser.add_argument(
        "config_path",
        nargs="?",
        help="配置文件路径（支持 .json / .yaml / .yml）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="仅输出汇总信息，不输出每条检查详情"
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"自检失败: {exc}")
            return 1
        except Exception as exc:  # 未预期异常
            print(f"自检异常 [E010]: {exc}")
            return 1

    # 正常模式：需要配置文件路径
    if not args.config_path:
        parser.error("需要指定配置文件路径，或使用 --selftest 运行自检")
        return 1

    # 加载配置文件
    config_data, err_code, err_msg = load_config_file(args.config_path)
    if err_code:
        print(f"错误 [{err_code}]: {err_msg}")
        return 1

    # 执行审查
    report = run_review(config_data, source_name=args.config_path)

    # 输出报告
    print(format_report(report, verbose=not args.quiet))

    # 返回退出码：有 ERROR 则返回非零
    summary = report.summary()
    if summary[LEVEL_ERROR] > 0:
        return 2
    return 0


# ---------------------------------------------------------------------------
# 程序入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(130)
    except Exception as exc:  # 全局兜底
        print(f"未预期异常 [E010]: {exc}")
        sys.exit(1)
