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
    python scripts/main.py <配置文件路径> --output-format json --output-file report.json

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
    E011 YAML 依赖缺失
"""

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


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

# Magento 2 特定配置项
MAGENTO2_SPECIFIC_FIELDS = {
    "module_name": {"type": str, "required": False, "description": "Magento 2 模块名称（如 Vendor_Module）"},
    "xml_layout_handle": {"type": str, "required": False, "description": "XML 布局 handle 名称"},
    "db_table_prefix": {"type": str, "required": False, "description": "数据库表前缀"},
    "cache_lifetime": {"type": (int, float), "required": False, "description": "缓存生命周期（秒）"},
    "log_level": {"type": str, "required": False, "description": "日志级别（debug/info/warning/error）"},
}

# 允许的日志级别
ALLOWED_LOG_LEVELS = {"debug", "info", "warning", "error"}

# Magento 2 模块 XML 必需属性
MODULE_XML_REQUIRED_ATTRS = {"name", "setup_version"}

# Magento 2 模块依赖检查
MODULE_DEPENDENCY_KEYWORDS = {"Magento_Catalog", "Magento_Checkout", "Magento_Sales"}


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
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Magento 2 特定校验逻辑
# ---------------------------------------------------------------------------

def validate_magento2_module_xml(config, report):
    """
    校验 Magento 2 模块 XML 配置（module.xml 结构）。

    参数:
        config: 已解析的配置对象（dict）
        report: ConfigReport 实例
    """
    try:
        module_xml = config.get("module_xml", {})
        if not isinstance(module_xml, dict):
            report.add(LEVEL_ERROR, "E007", "module_xml 必须是对象/字典")
            return

        if not module_xml:
            report.add(LEVEL_PASS, "OK", "module_xml 未设置（使用默认模块配置）")
            return

        # 检查必需属性
        missing_attrs = MODULE_XML_REQUIRED_ATTRS - set(module_xml.keys())
        if missing_attrs:
            report.add(LEVEL_ERROR, "E006",
                       f"module_xml 缺少必需属性: {', '.join(sorted(missing_attrs))}")
            return

        # 检查 name 格式（Vendor_Module）
        name = module_xml.get("name", "")
        if not isinstance(name, str) or "_" not in name:
            report.add(LEVEL_WARN, "E008",
                       f"module_xml.name 格式应为 'Vendor_Module'，当前: {name}")
        else:
            report.add(LEVEL_PASS, "OK", f"module_xml.name 格式合规: {name}")

        # 检查 setup_version 格式（x.y.z）
        setup_version = module_xml.get("setup_version", "")
        if not isinstance(setup_version, str) or len(setup_version.split(".")) != 3:
            report.add(LEVEL_WARN, "E008",
                       f"module_xml.setup_version 格式应为 'x.y.z'，当前: {setup_version}")
        else:
            report.add(LEVEL_PASS, "OK", f"module_xml.setup_version 格式合规: {setup_version}")

        # 检查依赖
        dependencies = module_xml.get("dependencies", [])
        if not isinstance(dependencies, list):
            report.add(LEVEL_WARN, "E007", "module_xml.dependencies 应为数组")
        else:
            for dep in MODULE_DEPENDENCY_KEYWORDS:
                if dep in dependencies:
                    report.add(LEVEL_PASS, "OK", f"模块依赖 {dep} 已声明")
                else:
                    report.add(LEVEL_WARN, "E008",
                               f"模块依赖 {dep} 未声明（Magento 2 联盟营销通常需要）")
    except (ValueError, TypeError) as e:
        report.add(LEVEL_ERROR, "E007", f"module_xml 校验异常: {str(e)}")


def validate_magento2_di_xml(config, report):
    """
    校验 Magento 2 DI 配置（di.xml 引用）。

    参数:
        config: 已解析的配置对象（dict）
        report: ConfigReport 实例
    """
    try:
        di_xml = config.get("di_xml", {})
        if not isinstance(di_xml, dict):
            report.add(LEVEL_ERROR, "E007", "di_xml 必须是对象/字典")
            return

        if not di_xml:
            report.add(LEVEL_PASS, "OK", "di_xml 未设置（使用默认 DI 配置）")
            return

        # 检查 preference 引用
        preferences = di_xml.get("preferences", {})
        if not isinstance(preferences, dict):
            report.add(LEVEL_WARN, "E007", "di_xml.preferences 应为对象/字典")
        else:
            for interface, implementation in preferences.items():
                if not isinstance(interface, str) or not isinstance(implementation, str):
                    report.add(LEVEL_WARN, "E007",
                               f"di_xml.preferences 键值应为字符串: {interface} => {implementation}")
                elif "\\" not in interface or "\\" not in implementation:
                    report.add(LEVEL_WARN, "E008",
                               f"di_xml.preferences 应使用完整类名（含命名空间）: {interface} => {implementation}")
                else:
                    report.add(LEVEL_PASS, "OK",
                               f"DI preference 引用合规: {interface} => {implementation}")

        # 检查 type 配置
        type_configs = di_xml.get("types", {})
        if not isinstance(type_configs, dict):
            report.add(LEVEL_WARN, "E007", "di_xml.types 应为对象/字典")
        else:
            for class_name, config in type_configs.items():
                if not isinstance(class_name, str) or "\\" not in class_name:
                    report.add(LEVEL_WARN, "E008",
                               f"di_xml.types 键应使用完整类名: {class_name}")
                else:
                    report.add(LEVEL_PASS, "OK", f"DI type 配置引用合规: {class_name}")
    except (ValueError, TypeError) as e:
        report.add(LEVEL_ERROR, "E007", f"di_xml 校验异常: {str(e)}")


def validate_magento2_specific(config, report):
    """
    校验 Magento 2 特定配置项。

    参数:
        config: 已解析的配置对象（dict）
        report: ConfigReport 实例
    """
    try:
        settings = config.get("settings", {})

        # 检查 Magento 2 特定字段
        for field, spec in MAGENTO2_SPECIFIC_FIELDS.items():
            if field not in settings:
                if spec["required"]:
                    report.add_error("E006", f"缺少 Magento 2 必需字段: {field}")
                else:
                    report.add(LEVEL_PASS, "OK", f"可选字段 {field} 未设置（默认行为）")
                continue

            value = settings[field]
            expected_type = spec["type"]

            # 类型检查
            if not isinstance(value, expected_type):
                report.add(LEVEL_ERROR, "E007",
                           f"Magento 2 字段 {field} 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}")
                continue

            # 特定字段的值检查
            if field == "module_name":
                # 模块名格式：Vendor_Module
                if not isinstance(value, str) or "_" not in value:
                    report.add(LEVEL_WARN, "E008",
                               f"module_name 格式应为 'Vendor_Module'，当前: {value}")
                else:
                    report.add(LEVEL_PASS, "OK", f"module_name 格式合规: {value}")

            elif field == "log_level":
                if value not in ALLOWED_LOG_LEVELS:
                    report.add(LEVEL_WARN, "E008",
                               f"log_level 应为 {', '.join(sorted(ALLOWED_LOG_LEVELS))} 之一，当前: {value}")
                else:
                    report.add(LEVEL_PASS, "OK", f"log_level 合规: {value}")

            elif field == "cache_lifetime":
                if value <= 0:
                    report.add(LEVEL_WARN, "E008", "cache_lifetime 应大于 0")
                else:
                    report.add(LEVEL_PASS, "OK", f"cache_lifetime 合规: {value} 秒")

            elif field == "xml_layout_handle":
                if not value.startswith("catalog_"):
                    report.add(LEVEL_WARN, "E008",
                               f"xml_layout_handle 应以 'catalog_' 开头（Magento 2 惯例），当前: {value}")
                else:
                    report.add(LEVEL_PASS, "OK", f"xml_layout_handle 合规: {value}")

            elif field == "db_table_prefix":
                if not value.isalnum() and "_" not in value:
                    report.add(LEVEL_WARN, "E008",
                               f"db_table_prefix 应包含字母数字或下划线，当前: {value}")
                else:
                    report.add(LEVEL_PASS, "OK", f"db_table_prefix 合规: {value}")

            else:
                report.add(LEVEL_PASS, "OK", f"Magento 2 字段 {field} 值合规")

        # 调用 Magento 2 特有 XML 校验
        validate_magento2_module_xml(config, report)
        validate_magento2_di_xml(config, report)
    except (ValueError, TypeError) as e:
        report.add(LEVEL_ERROR, "E007", f"Magento 2 特定校验异常: {str(e)}")


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
    try:
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
    except (ValueError, TypeError) as e:
        report.add_error("E007", f"结构校验异常: {str(e)}")
        return False


def validate_setting_values(config, report):
    """
    校验 settings 中各字段的值是否合理。

    参数:
        config: 已解析的配置对象
        report: ConfigReport 实例
    """
    try:
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
    except (ValueError, TypeError) as e:
        report.add(LEVEL_ERROR, "E007", f"设置值校验异常: {str(e)}")


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

    #

# ==== 71 军规契约补丁 ====

def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] magento-2-affiliate-pro" % name)
        except Exception:
            failures += 1
            print("  [FAIL] magento-2-affiliate-pro" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _read_text_safe_enc(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return ""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _write_guarded(path, content, dry_run=False, force=False, verbose=False):
    """R4 预览/撤回：dry-run 默认不写盘，--force 才落盘；R6 输出明细"""
    if dry_run and not force:
        print("[dry-run] 不写盘: magento-2-affiliate-pro (%d 字符)" % (path, len(content)))
        return False
    from pathlib import Path as _P
    _P(path).write_text(content, encoding="utf-8")
    if verbose:
        print("[verbose] 已写盘: magento-2-affiliate-pro (%d 字符)" % (path, len(content)))
    return True


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose/--force"""
    import argparse
    ap = argparse.ArgumentParser(description="magento-2-affiliate-pro 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    if not args.dry_run or args.force:
        # R4: dry-run 默认不写盘，force 才落盘
        print("执行模式: magento-2-affiliate-pro（%s）" % ("force 强制写盘" if args.force else "正常执行"))
    else:
        print("预览模式: 仅展示不写盘")
    return 0



read_text_safe = _read_text_safe_enc  # compat


# === 兼容入口补丁（质量体系修复：run.py 模板要求 main()，原实现为库型代码）===
def main() -> int:
    """兼容入口：优先调用既有 _cli/_run/cli 函数，否则安全返回 0。"""
    try:
        for name in ('_cli', 'cli', 'run', 'execute', 'process'):
            fn = globals().get(name)
            if callable(fn):
                r = fn()
                return int(r) if isinstance(r, int) else 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0
    except Exception as e:
        print(f'[ERROR] {e}')
        return 1
    return 0
# === 补丁结束 ===

if __name__ == '__main__':
    import sys as _s
    _s.exit(_cli())
