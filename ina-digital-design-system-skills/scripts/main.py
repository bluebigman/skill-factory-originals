#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ina-digital-design-system-skills 独立实现脚本

本脚本依据《政务界面 设计审计 规范落地》功能规格，从零独立编写。
主要能力：
    C1 输入结构化       —— 将设计文本描述解析为结构化组件数据
    C2 关键信息提取     —— 从描述中提取设计令牌（色彩、间距等）
    C3 规范格式输出     —— 生成合规性审计报告（通过/不通过/需核实）
    C4 置信度标注       —— 对不确定字段标注 [需核实:字段名]
    C5 批量与自定义     —— 支持多输入批量处理与自定义输出模板

仅使用 Python 标准库实现，无第三方依赖。
运行方式：
    python scripts/main.py --selftest     # 离线自检
    python scripts/main.py --help         # 查看帮助
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 未知错误
# E002: 输入参数缺失或为空
# E003: 输入格式无法解析
# E004: 设计令牌提取失败
# E005: 审计规则加载失败
# E006: 报告生成失败
# E007: 批量处理中断
# E008: 模板格式不支持
# E009: 输出写入失败
# E010: 自检断言失败


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def raise_error(code: str, message: str) -> None:
    """统一抛出带错误码的异常"""
    raise SkillError(code, message)


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class DesignToken:
    """设计令牌（色彩、间距、字体等）"""
    category: str            # 类别: color / spacing / typography / radius
    name: str                # 令牌名称
    value: str               # 令牌值
    confidence: float = 1.0  # 置信度 0.0-1.0
    note: str = ""           # 备注（如 [需核实]）


@dataclass
class ComponentItem:
    """结构化组件条目"""
    name: str                # 组件名称
    state: str = "default"   # 状态: default / hover / active / disabled
    variant: str = ""        # 变体
    properties: Dict[str, str] = field(default_factory=dict)
    tokens: List[DesignToken] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class AuditResult:
    """单条审计结果"""
    component: str
    rule_id: str
    status: str              # pass / fail / review
    message: str
    detail: str = ""


@dataclass
class AuditReport:
    """完整审计报告"""
    title: str
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    needs_review: int = 0
    results: List[AuditResult] = field(default_factory=list)

    def add_result(self, result: AuditResult) -> None:
        self.results.append(result)
        self.total_checks += 1
        if result.status == "pass":
            self.passed += 1
        elif result.status == "fail":
            self.failed += 1
        else:
            self.needs_review += 1


# ---------------------------------------------------------------------------
# 内置审计规则库（设计规范参考条目）
# ---------------------------------------------------------------------------
BUILTIN_RULES: List[Dict[str, str]] = [
    {
        "id": "R-COLOR-001",
        "category": "color",
        "description": "主色必须使用规范定义的标准蓝色系",
        "check": "primary_color",
    },
    {
        "id": "R-SPACING-001",
        "category": "spacing",
        "description": "组件间距必须是 4px 的整数倍",
        "check": "spacing_multiples",
    },
    {
        "id": "R-TYPO-001",
        "category": "typography",
        "description": "正文字号不得小于 14px",
        "check": "min_font_size",
    },
    {
        "id": "R-RADIUS-001",
        "category": "radius",
        "description": "卡片圆角建议使用 8px 或 12px",
        "check": "card_radius",
    },
    {
        "id": "R-ACCESS-001",
        "category": "accessibility",
        "description": "文字与背景对比度需满足 WCAG AA 标准",
        "check": "contrast_ratio",
    },
]


# ---------------------------------------------------------------------------
# 核心功能：输入结构化（C1）
# ---------------------------------------------------------------------------
def parse_design_input(text: str) -> List[ComponentItem]:
    """
    将设计文本描述解析为结构化组件数据。

    支持格式：
        - 组件名: 属性名=值, 属性名=值
        - 组件名 [状态] {变体}
        - 多行输入，每行一个组件
    """
    if not text or not text.strip():
        raise_error("E002", "输入文本为空，无法解析")

    components: List[ComponentItem] = []
    lines = text.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        try:
            # 提取组件名称（第一个冒号之前的部分）
            if ":" in line:
                name_part, props_part = line.split(":", 1)
            else:
                name_part, props_part = line, ""

            name = name_part.strip()
            if not name:
                continue

            # 提取状态和变体
            state = "default"
            variant = ""
            state_match = re.search(r"\[(.*?)\]", name)
            if state_match:
                state = state_match.group(1).strip() or "default"
                name = name.replace(state_match.group(0), "").strip()

            variant_match = re.search(r"\{(.*?)\}", name)
            if variant_match:
                variant = variant_match.group(1).strip()
                name = name.replace(variant_match.group(0), "").strip()

            # 解析属性
            properties: Dict[str, str] = {}
            if props_part:
                for prop in props_part.split(","):
                    prop = prop.strip()
                    if not prop:
                        continue
                    if "=" in prop:
                        key, value = prop.split("=", 1)
                        properties[key.strip()] = value.strip()
                    else:
                        properties[prop] = "true"

            components.append(
                ComponentItem(
                    name=name,
                    state=state,
                    variant=variant,
                    properties=properties,
                )
            )
        except Exception as e:
            raise_error("E003", f"解析行失败: {line}，错误: {str(e)}")

    if not components:
        raise_error("E003", "未能从输入中解析出任何组件")

    return components


# ---------------------------------------------------------------------------
# 核心功能：关键信息提取（C2）
# ---------------------------------------------------------------------------
TOKEN_PATTERNS = {
    "color": r"(?:#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|hsl\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*\))",
    "spacing": r"(?:\d+(?:\.\d+)?px|\d+(?:\.\d+)?rem|\d+(?:\.\d+)?em)",
    "typography": r"(?:\d+(?:\.\d+)?px|\d+(?:\.\d+)?pt|\d+(?:\.\d+)?rem)",
    "radius": r"(?:\d+(?:\.\d+)?px|\d+(?:\.\d+)?rem|\d+(?:\.\d+)?%)",
}


def extract_design_tokens(components: List[ComponentItem]) -> List[DesignToken]:
    """从组件属性中提取设计令牌"""
    if not components:
        raise_error("E002", "组件列表为空，无法提取令牌")

    tokens: List[DesignToken] = []
    token_names = set()

    for comp in components:
        for key, value in comp.properties.items():
            category = detect_token_category(key, value)
            if category is None:
                continue

            token_name = f"{comp.name}_{key}"
            if token_name in token_names:
                continue
            token_names.add(token_name)

            confidence = 1.0
            note = ""
            if "?" in value or "不确定" in value:
                confidence = 0.5
                note = f"[需核实:{key}]"

            tokens.append(
                DesignToken(
                    category=category,
                    name=token_name,
                    value=value,
                    confidence=confidence,
                    note=note,
                )
            )

    if not tokens:
        raise_error("E004", "未能从组件中提取到设计令牌")

    return tokens


def detect_token_category(key: str, value: str) -> Optional[str]:
    """根据键名和值内容推测令牌类别"""
    key_lower = key.lower()
    value_lower = value.lower()

    # 颜色相关
    if any(k in key_lower for k in ["color", "colour", "背景", "颜色", "bg", "text"]):
        if re.search(TOKEN_PATTERNS["color"], value, re.IGNORECASE):
            return "color"

    # 间距相关
    if any(k in key_lower for k in ["spacing", "margin", "padding", "gap", "间距"]):
        if re.search(TOKEN_PATTERNS["spacing"], value, re.IGNORECASE):
            return "spacing"

    # 字体相关
    if any(k in key_lower for k in ["font", "size", "text", "字号", "字体"]):
        if re.search(TOKEN_PATTERNS["typography"], value, re.IGNORECASE):
            return "typography"

    # 圆角相关
    if any(k in key_lower for k in ["radius", "round", "圆角"]):
        if re.search(TOKEN_PATTERNS["radius"], value, re.IGNORECASE):
            return "radius"

    return None


# ---------------------------------------------------------------------------
# 核心功能：规范格式输出/审计（C3）
# ---------------------------------------------------------------------------
def run_audit(components: List[ComponentItem]) -> AuditReport:
    """对组件列表执行合规性审计"""
    if not components:
        raise_error("E002", "组件列表为空，无法执行审计")

    report = AuditReport(title="政务界面设计规范审计报告")

    for comp in components:
        # 检查主色规范
        check_primary_color(comp, report)
        # 检查间距规范
        check_spacing_multiples(comp, report)
        # 检查字号规范
        check_min_font_size(comp, report)
        # 检查圆角规范
        check_card_radius(comp, report)
        # 检查对比度（若有颜色信息）
        check_contrast(comp, report)

    return report


def check_primary_color(comp: ComponentItem, report: AuditReport) -> None:
    """R-COLOR-001: 主色检查"""
    for key, value in comp.properties.items():
        if "color" in key.lower() and "primary" in key.lower():
            if re.search(r"#(?:0[0-9a-fA-F]{2}|1[0-9a-fA-F]{2}|2[0-9a-fA-F]{2})", value):
                report.add_result(AuditResult(
                    component=comp.name,
                    rule_id="R-COLOR-001",
                    status="pass",
                    message="主色值符合标准蓝色系范围",
                ))
            else:
                report.add_result(AuditResult(
                    component=comp.name,
                    rule_id="R-COLOR-001",
                    status="fail",
                    message="主色值可能不符合规范蓝色系",
                    detail=f"当前值: {value}",
                ))
            return

    # 未显式声明主色，标记为需核实
    report.add_result(AuditResult(
        component=comp.name,
        rule_id="R-COLOR-001",
        status="review",
        message="未检测到主色定义，需人工核实",
    ))


def check_spacing_multiples(comp: ComponentItem, report: AuditReport) -> None:
    """R-SPACING-001: 间距必须是 4px 整数倍"""
    for key, value in comp.properties.items():
        if any(k in key.lower() for k in ["margin", "padding", "gap", "spacing"]):
            match = re.search(r"(\d+(?:\.\d+)?)px", value)
            if match:
                px_value = float(match.group(1))
                if px_value > 0 and px_value % 4 < 0.01:
                    report.add_result(AuditResult(
                        component=comp.name,
                        rule_id="R-SPACING-001",
                        status="pass",
                        message=f"间距 {px_value}px 是 4px 的整数倍",
                    ))
                else:
                    report.add_result(AuditResult(
                        component=comp.name,
                        rule_id="R-SPACING-001",
                        status="fail",
                        message=f"间距 {px_value}px 不是 4px 的整数倍",
                    ))
                return

    # 未检测到间距属性，不判定
    report.add_result(AuditResult(
        component=comp.name,
        rule_id="R-SPACING-001",
        status="review",
        message="未检测到间距定义，跳过检查",
    ))


def check_min_font_size(comp: ComponentItem, report: AuditReport) -> None:
    """R-TYPO-001: 正文字号不小于 14px"""
    for key, value in comp.properties.items():
        if "font" in key.lower() and "size" in key.lower():
            match = re.search(r"(\d+(?:\.\d+)?)px", value)
            if match:
                size = float(match.group(1))
                if size >= 14:
                    report.add_result(AuditResult(
                        component=comp.name,
                        rule_id="R-TYPO-001",
                        status="pass",
                        message=f"字号 {size}px 不小于 14px",
                    ))
                else:
                    report.add_result(AuditResult(
                        component=comp.name,
                        rule_id="R-TYPO-001",
                        status="fail",
                        message=f"字号 {size}px 小于 14px 最小要求",
                    ))
                return

    report.add_result(AuditResult(
        component=comp.name,
        rule_id="R-TYPO-001",
        status="review",
        message="未检测到字号定义，跳过检查",
    ))


def check_card_radius(comp: ComponentItem, report: AuditReport) -> None:
    """R-RADIUS-001: 卡片圆角建议 8px 或 12px"""
    if "card" not in comp.name.lower():
        return

    for key, value in comp.properties.items():
        if "radius" in key.lower():
            match = re.search(r"(\d+(?:\.\d+)?)px", value)
            if match:
                radius = float(match.group(1))
                if radius in (8, 12):
                    report.add_result(AuditResult(
                        component=comp.name,
                        rule_id="R-RADIUS-001",
                        status="pass",
                        message=f"卡片圆角 {radius}px 符合建议值",
                    ))
                else:
                    report.add_result(AuditResult(
                        component=comp.name,
                        rule_id="R-RADIUS-001",
                        status="review",
                        message=f"卡片圆角 {radius}px 非建议值（8px 或 12px）",
                    ))
                return

    # 未指定圆角
    report.add_result(AuditResult(
        component=comp.name,
        rule_id="R-RADIUS-001",
        status="review",
        message="卡片未指定圆角，建议使用 8px 或 12px",
    ))


def check_contrast(comp: ComponentItem, report: AuditReport) -> None:
    """R-ACCESS-001: 对比度检查（简化版）"""
    text_color = None
    bg_color = None

    for key, value in comp.properties.items():
        if "text" in key.lower() and "color" in key.lower():
            text_color = value
        if "bg" in key.lower() and "color" in key.lower():
            bg_color = value

    if text_color and bg_color:
        # 简化对比度评估：亮色文字配深色背景，或反之
        text_is_light = is_light_color(text_color)
        bg_is_light = is_light_color(bg_color)

        if text_is_light != bg_is_light:
            report.add_result(AuditResult(
                component=comp.name,
                rule_id="R-ACCESS-001",
                status="pass",
                message="文字与背景色具备明暗对比",
            ))
        else:
            report.add_result(AuditResult(
                component=comp.name,
                rule_id="R-ACCESS-001",
                status="review",
                message="文字与背景色对比度可能不足，需人工核实",
            ))
    else:
        report.add_result(AuditResult(
            component=comp.name,
            rule_id="R-ACCESS-001",
            status="review",
            message="未检测到完整文字/背景色信息，跳过对比度检查",
        ))


def is_light_color(color_str: str) -> bool:
    """简化判断颜色是否为亮色"""
    match = re.search(r"#([0-9a-fA-F]{6})", color_str)
    if match:
        hex_val = match.group(1)
        r = int(hex_val[0:2], 16)
        g = int(hex_val[2:4], 16)
        b = int(hex_val[4:6], 16)
        # 相对亮度近似值
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return luminance > 128
    return False


# ---------------------------------------------------------------------------
# 核心功能：置信度标注（C4）
# ---------------------------------------------------------------------------
def annotate_confidence(components: List[ComponentItem]) -> List[ComponentItem]:
    """对不确定的字段添加置信度标注"""
    for comp in components:
        for key, value in comp.properties.items():
            # 常见不确定标记
            if any(mark in value.lower() for mark in ["?", "不确定", "unknown", "tbd", "待定"]):
                comp.confidence = min(comp.confidence, 0.5)
                comp.properties[key] = f"{value} [需核实:{key}]"
            elif "approx" in value.lower() or "约" in value:
                comp.confidence = min(comp.confidence, 0.7)
                comp.properties[key] = f"{value} [需核实:{key}]"
    return components


# ---------------------------------------------------------------------------
# 核心功能：批量与自定义（C5）
# ---------------------------------------------------------------------------
def process_batch(inputs: List[str]) -> List[AuditReport]:
    """批量处理多个输入"""
    if not inputs:
        raise_error("E002", "批量输入列表为空")

    reports = []
    try:
        for idx, text in enumerate(inputs):
            components = parse_design_input(text)
            components = annotate_confidence(components)
            report = run_audit(components)
            report.title = f"批量审计 #{idx + 1}"
            reports.append(report)
    except SkillError:
        raise
    except Exception as e:
        raise_error("E007", f"批量处理中断: {str(e)}")

    return reports


def generate_custom_report(report: AuditReport, template: str = "standard") -> str:
    """按模板生成报告"""
    if template == "standard":
        return format_report_text(report)
    elif template == "json":
        return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)
    elif template == "minimal":
        lines = []
        for result in report.results:
            lines.append(f"[{result.status.upper()}] {result.component}: {result.message}")
        return "\n".join(lines)
    else:
        raise_error("E008", f"不支持的模板类型: {template}")


def report_to_dict(report: AuditReport) -> Dict[str, Any]:
    """将审计报告转换为字典"""
    return {
        "title": report.title,
        "total_checks": report.total_checks,
        "passed": report.passed,
        "failed": report.failed,
        "needs_review": report.needs_review,
        "results": [
            {
                "component": r.component,
                "rule_id": r.rule_id,
                "status": r.status,
                "message": r.message,
                "detail": r.detail,
            }
            for r in report.results
        ],
    }


def format_report_text(report: AuditReport) -> str:
    """将报告格式化为易读文本"""
    lines = [
        "=" * 60,
        f"📋 {report.title}",
        "=" * 60,
        f"总计检查: {report.total_checks} 项",
        f"✅ 通过: {report.passed} 项",
        f"❌ 未通过: {report.failed} 项",
        f"⚠️ 需核实: {report.needs_review} 项",
        "-" * 60,
    ]

    for result in report.results:
        icon = {"pass": "✅", "fail": "❌", "review": "⚠️"}.get(result.status, "❓")
        lines.append(f"{icon} [{result.rule_id}] {result.component}")
        lines.append(f"   {result.message}")
        if result.detail:
            lines.append(f"   详情: {result.detail}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------
SELFTEST_INPUT = """\
# 政务门户首页组件描述
PrimaryButton: color=#0B5FFF, font_size=16px, padding=8px, radius=8px
Card [hover] {elevated}: bg_color=#FFFFFF, radius=12px, margin=4px, font_size=14px
TextField: color=#333333, font_size=13px, padding=4px
Badge: bg_color=#FF6B35, color=#FFFFFF, radius=4px
Footer: font_size=14px, margin=8px, color=#666666
"""


def run_selftest() -> int:
    """执行内置自检，返回退出码"""
    print("🔍 开始自检...")
    failures = []

    try:
        # 测试 C1: 输入结构化
        print("  [1/5] 测试输入结构化 (C1)...")
        components = parse_design_input(SELFTEST_INPUT)
        assert len(components) >= 3, f"组件数量应>=3，实际: {len(components)}"
        assert all(comp.name for comp in components), "组件名称不能为空"
        print(f"    ✅ 解析出 {len(components)} 个组件")

        # 测试 C2: 关键信息提取
        print("  [2/5] 测试关键信息提取 (C2)...")
        tokens = extract_design_tokens(components)
        assert len(tokens) >= 3, f"令牌数量应>=3，实际: {len(tokens)}"
        categories = {t.category for t in tokens}
        assert len(categories) >= 2, f"至少包含2种类别，实际: {categories}"
        print(f"    ✅ 提取出 {len(tokens)} 个令牌，类别: {categories}")

        # 测试 C3: 审计报告
        print("  [3/5] 测试审计报告 (C3)...")
        report = run_audit(components)
        assert report.total_checks > 0, "审计检查项应大于0"
        assert report.passed + report.failed + report.needs_review == report.total_checks, \
            "审计统计不一致"
        print(f"    ✅ 审计完成: 通过{report.passed} 失败{report.failed} 需核实{report.needs_review}")

        # 测试 C4: 置信度标注
        print("  [4/5] 测试置信度标注 (C4)...")
        annotated = annotate_confidence(components)
        assert all(0.0 <= c.confidence <= 1.0 for c in annotated), "置信度应在0-1之间"
        print(f"    ✅ 置信度标注完成")

        # 测试 C5: 批量处理
        print("  [5/5] 测试批量处理 (C5)...")
        reports = process_batch([SELFTEST_INPUT, "Button: color=#123456, font_size=15px"])
        assert len(reports) == 2, f"应生成2份报告，实际: {len(reports)}"
        json_report = generate_custom_report(reports[0], "json")
        parsed_json = json.loads(json_report)
        assert parsed_json["total_checks"] == reports[0].total_checks, "JSON报告不一致"
        print(f"    ✅ 批量处理生成 {len(reports)} 份报告")

        print("\n🎉 所有自检通过！")
        return 0

    except SkillError as e:
        failures.append(f"技能错误 [{e.code}]: {e.message}")
    except AssertionError as e:
        failures.append(f"断言失败: {str(e)}")
    except Exception as e:
        failures.append(f"未知异常: {str(e)}")

    print("\n❌ 自检失败:")
    for failure in failures:
        print(f"  - {failure}")
    return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="政务界面设计规范审计与实施辅助工具",
        epilog="示例: python main.py --input 'Button: color=#0B5FFF, font_size=16px'",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="设计描述文本，格式: '组件名: 属性=值, 属性=值'",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取设计描述",
    )
    parser.add_argument(
        "--template",
        choices=["standard", "json", "minimal"],
        default="standard",
        help="报告输出模板 (默认: standard)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（从文件逐行读取输入）",
    )
    return parser


def read_input_from_file(filepath: str) -> str:
    """从文件读取输入内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise_error("E009", f"文件不存在: {filepath}")
    except Exception as e:
        raise_error("E009", f"读取文件失败: {str(e)}")


def main() -> int:
    """主入口函数"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 获取输入
    try:
        if args.input:
            input_text = args.input
        elif args.file:
            input_text = read_input_from_file(args.file)
        else:
            parser.print_help()
            return 0

        # 执行处理流程
        if args.batch:
            # 批量模式：按行拆分输入
            lines = [line for line in input_text.splitlines() if line.strip()]
            reports = process_batch(lines)
            for report in reports:
                print(generate_custom_report(report, args.template))
                print()
        else:
            # 单次处理
            components = parse_design_input(input_text)
            components = annotate_confidence(components)
            tokens = extract_design_tokens(components)
            report = run_audit(components)

            # 输出令牌信息
            print(f"📐 提取到 {len(tokens)} 个设计令牌:")
            for token in tokens:
                note = f" {token.note}" if token.note else ""
                print(f"  - [{token.category}] {token.name} = {token.value}{note}")

            print()
            # 输出审计报告
            print(generate_custom_report(report, args.template))

        return 0

    except SkillError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 [E001]: 未知错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
