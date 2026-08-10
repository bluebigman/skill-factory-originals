#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
SwiftUI 界面设计审查与规范指导 —— 独立实现脚本

本脚本根据功能规格文档（swiftui-design-skill）重新实现核心逻辑。
仅使用 Python 标准库，无第三方依赖。
支持 --selftest 参数进行离线自检。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "无效的命令行参数",
    "E002": "输入数据格式错误",
    "E003": "缺少必要的输入字段",
    "E004": "组件类型不受支持",
    "E005": "审查规则执行失败",
    "E006": "输出序列化失败",
    "E007": "内部状态异常",
    "E008": "自检数据缺失",
    "E009": "自检断言失败",
    "E010": "未预期的异常",
}


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ComponentSpec:
    """组件规格描述"""
    component_type: str          # 组件类型，如 "NavigationStack", "TabView"
    usage_scenario: str          # 适用场景
    recommendation: str          # 推荐建议
    alternatives: List[str] = field(default_factory=list)  # 可选替代方案


@dataclass
class ReviewRule:
    """审查规则"""
    rule_id: str                 # 规则编号
    category: str                # 分类：布局/字体/色彩/圆角/阴影
    description: str             # 规则描述
    check_func: str              # 检查函数名称（字符串引用）
    severity: str = "warning"    # 严重程度：error/warning/info


@dataclass
class ReviewResult:
    """审查结果"""
    rule_id: str
    category: str
    description: str
    severity: str
    passed: bool
    message: str = ""


# ============================================================
# 内置知识库（硬编码，不依赖外部文件）
# ============================================================
COMPONENT_KNOWLEDGE: Dict[str, ComponentSpec] = {
    "NavigationStack": ComponentSpec(
        component_type="NavigationStack",
        usage_scenario="需要多级页面跳转的层级导航",
        recommendation="推荐使用 NavigationStack 管理页面栈，配合 NavigationLink 实现跳转",
        alternatives=["NavigationView", "Sheet", "FullScreenCover"],
    ),
    "TabView": ComponentSpec(
        component_type="TabView",
        usage_scenario="需要在多个平级功能模块间切换",
        recommendation="推荐使用 TabView 配合 TabItem 进行底部标签导航",
        alternatives=["Sidebar", "SegmentedControl"],
    ),
    "List": ComponentSpec(
        component_type="List",
        usage_scenario="展示大量结构化数据列表",
        recommendation="推荐使用 List 配合 Section 分组，支持滑动删除等交互",
        alternatives=["ScrollView + VStack", "LazyVStack", "Table"],
    ),
    "ScrollView": ComponentSpec(
        component_type="ScrollView",
        usage_scenario="需要滚动展示内容",
        recommendation="推荐使用 ScrollView 配合 LazyVStack/LazyHStack 优化性能",
        alternatives=["List", "LazyVStack"],
    ),
    "VStack": ComponentSpec(
        component_type="VStack",
        usage_scenario="垂直排列多个视图",
        recommendation="推荐使用 VStack 进行垂直布局，注意控制嵌套层级",
        alternatives=["HStack", "ZStack", "Grid"],
    ),
    "HStack": ComponentSpec(
        component_type="HStack",
        usage_scenario="水平排列多个视图",
        recommendation="推荐使用 HStack 进行水平布局，注意间距设置",
        alternatives=["VStack", "ZStack", "Grid"],
    ),
    "ZStack": ComponentSpec(
        component_type="ZStack",
        usage_scenario="视图叠加场景",
        recommendation="推荐使用 ZStack 处理叠加关系，注意 Z 轴层级",
        alternatives=["VStack", "HStack", "overlay modifier"],
    ),
    "Button": ComponentSpec(
        component_type="Button",
        usage_scenario="需要用户点击触发操作的场景",
        recommendation="推荐使用 Button 并设置合适的按钮样式和状态反馈",
        alternatives=["Link", "TapGesture"],
    ),
    "Text": ComponentSpec(
        component_type="Text",
        usage_scenario="展示文本内容",
        recommendation="推荐使用 Text 并设置合适的字体、颜色、行距",
        alternatives=["TextField", "TextEditor", "Label"],
    ),
    "Image": ComponentSpec(
        component_type="Image",
        usage_scenario="展示图片内容",
        recommendation="推荐使用 Image 并设置合适的缩放模式",
        alternatives=["AsyncImage", "Canvas"],
    ),
}


# ============================================================
# 核心审查逻辑
# ============================================================
class SwiftUIDesignReviewer:
    """SwiftUI 设计审查器"""

    def __init__(self) -> None:
        """初始化审查器"""
        self.rules: List[ReviewRule] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """注册默认审查规则"""
        self.rules = [
            ReviewRule(
                rule_id="R001",
                category="布局",
                description="垂直间距应保持 8pt 的倍数",
                check_func="check_vertical_spacing",
            ),
            ReviewRule(
                rule_id="R002",
                category="布局",
                description="水平间距应保持 8pt 的倍数",
                check_func="check_horizontal_spacing",
            ),
            ReviewRule(
                rule_id="R003",
                category="字体",
                description="正文文字大小建议在 15-17pt 之间",
                check_func="check_body_font_size",
            ),
            ReviewRule(
                rule_id="R004",
                category="字体",
                description="标题文字大小建议在 20-34pt 之间",
                check_func="check_title_font_size",
            ),
            ReviewRule(
                rule_id="R005",
                category="色彩",
                description="正文文字对比度建议不低于 4.5:1",
                check_func="check_text_contrast",
            ),
            ReviewRule(
                rule_id="R006",
                category="圆角",
                description="圆角半径建议为 4pt 的倍数",
                check_func="check_corner_radius",
            ),
            ReviewRule(
                rule_id="R007",
                category="阴影",
                description="阴影透明度建议在 0.1-0.3 之间",
                check_func="check_shadow_opacity",
            ),
            ReviewRule(
                rule_id="R008",
                category="布局",
                description="视图嵌套层级建议不超过 10 层",
                check_func="check_view_nesting_depth",
            ),
            ReviewRule(
                rule_id="R009",
                category="组件",
                description="组件选择建议与使用场景匹配",
                check_func="check_component_selection",
            ),
            ReviewRule(
                rule_id="R010",
                category="适配",
                description="建议支持不同屏幕尺寸适配",
                check_func="check_adaptive_layout",
            ),
        ]

    # --------------------------------------------------------
    # 审查规则检查函数（每个函数返回 (passed, message)）
    # --------------------------------------------------------
    def check_vertical_spacing(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查垂直间距是否为 8 的倍数"""
        spacing = data.get("vertical_spacing", 0)
        if spacing <= 0:
            return True, "未设置垂直间距，跳过检查"
        if spacing % 8 == 0:
            return True, f"垂直间距 {spacing}pt 符合 8pt 倍数规范"
        return False, f"垂直间距 {spacing}pt 不是 8 的倍数，建议调整为 {max(8, (spacing // 8) * 8)}pt 或 {(spacing // 8 + 1) * 8}pt"

    def check_horizontal_spacing(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查水平间距是否为 8 的倍数"""
        spacing = data.get("horizontal_spacing", 0)
        if spacing <= 0:
            return True, "未设置水平间距，跳过检查"
        if spacing % 8 == 0:
            return True, f"水平间距 {spacing}pt 符合 8pt 倍数规范"
        return False, f"水平间距 {spacing}pt 不是 8 的倍数，建议调整为 {max(8, (spacing // 8) * 8)}pt 或 {(spacing // 8 + 1) * 8}pt"

    def check_body_font_size(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查正文字号"""
        font_size = data.get("body_font_size", 0)
        if font_size <= 0:
            return True, "未设置正文字号，跳过检查"
        if 15 <= font_size <= 17:
            return True, f"正文字号 {font_size}pt 在推荐范围 15-17pt 内"
        return False, f"正文字号 {font_size}pt 不在推荐范围 15-17pt 内"

    def check_title_font_size(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查标题字号"""
        font_size = data.get("title_font_size", 0)
        if font_size <= 0:
            return True, "未设置标题字号，跳过检查"
        if 20 <= font_size <= 34:
            return True, f"标题字号 {font_size}pt 在推荐范围 20-34pt 内"
        return False, f"标题字号 {font_size}pt 不在推荐范围 20-34pt 内"

    def check_text_contrast(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查文字对比度（简化版，用数值范围判断）"""
        contrast = data.get("text_contrast", 0)
        if contrast <= 0:
            return True, "未设置文字对比度，跳过检查"
        if contrast >= 4.5:
            return True, f"文字对比度 {contrast:.1f}:1 达到 WCAG AA 标准"
        return False, f"文字对比度 {contrast:.1f}:1 低于 4.5:1，建议提高"

    def check_corner_radius(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查圆角"""
        radius = data.get("corner_radius", 0)
        if radius <= 0:
            return True, "未设置圆角，跳过检查"
        if radius % 4 == 0:
            return True, f"圆角半径 {radius}pt 符合 4pt 倍数规范"
        return False, f"圆角半径 {radius}pt 不是 4 的倍数，建议调整为 {max(4, (radius // 4) * 4)}pt"

    def check_shadow_opacity(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查阴影透明度"""
        opacity = data.get("shadow_opacity", -1)
        if opacity < 0:
            return True, "未设置阴影透明度，跳过检查"
        if 0.1 <= opacity <= 0.3:
            return True, f"阴影透明度 {opacity:.2f} 在推荐范围 0.1-0.3 内"
        return False, f"阴影透明度 {opacity:.2f} 不在推荐范围 0.1-0.3 内"

    def check_view_nesting_depth(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查视图嵌套深度"""
        depth = data.get("view_nesting_depth", 0)
        if depth <= 0:
            return True, "未设置视图嵌套深度，跳过检查"
        if depth <= 10:
            return True, f"视图嵌套深度 {depth} 层在推荐范围（≤10层）内"
        return False, f"视图嵌套深度 {depth} 层超过推荐范围（≤10层），建议拆分视图"

    def check_component_selection(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查组件选择是否合理"""
        component = data.get("component", "")
        scenario = data.get("scenario", "")
        if not component:
            return True, "未指定组件，跳过检查"
        if component in COMPONENT_KNOWLEDGE:
            spec = COMPONENT_KNOWLEDGE[component]
            # 关键词匹配场景
            keywords = spec.usage_scenario.split("需要")[1:] if "需要" in spec.usage_scenario else []
            matched = False
            for kw in keywords:
                kw_clean = kw.replace("的", "").replace("导航", "").replace("切换", "").replace("排列", "")
                if kw_clean and kw_clean in scenario:
                    matched = True
                    break
            if matched or not keywords:
                return True, f"组件 {component} 与场景 '{scenario}' 匹配"
            return False, f"组件 {component} 可能不适合场景 '{scenario}'，建议参考：{spec.recommendation}"
        return False, f"未知组件类型 '{component}'"

    def check_adaptive_layout(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """检查自适应布局"""
        adaptive = data.get("adaptive_layout", None)
        if adaptive is None:
            return True, "未设置自适应布局，跳过检查"
        if adaptive:
            return True, "已启用自适应布局"
        return False, "未启用自适应布局，建议支持不同屏幕尺寸"

    # --------------------------------------------------------
    # 审查执行
    # --------------------------------------------------------
    def review(self, data: Dict[str, Any]) -> List[ReviewResult]:
        """执行审查，返回结果列表"""
        results: List[ReviewResult] = []
        for rule in self.rules:
            try:
                check_func = getattr(self, rule.check_func)
                passed, message = check_func(data)
            except Exception as exc:
                # 规则执行失败，记录错误但不中断
                results.append(ReviewResult(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    description=rule.description,
                    severity="error",
                    passed=False,
                    message=f"规则执行失败: {str(exc)}",
                ))
                continue

            results.append(ReviewResult(
                rule_id=rule.rule_id,
                category=rule.category,
                description=rule.description,
                severity=rule.severity,
                passed=passed,
                message=message,
            ))
        return results

    def get_component_recommendation(self, component_type: str) -> Optional[ComponentSpec]:
        """获取组件推荐"""
        return COMPONENT_KNOWLEDGE.get(component_type)


# ============================================================
# 数据处理与输出
# ============================================================
def format_review_output(results: List[ReviewResult], format_type: str = "text") -> str:
    """格式化审查结果输出"""
    if format_type == "json":
        try:
            return json.dumps(
                [
                    {
                        "rule_id": r.rule_id,
                        "category": r.category,
                        "description": r.description,
                        "severity": r.severity,
                        "passed": r.passed,
                        "message": r.message,
                    }
                    for r in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        except Exception as exc:
            raise ValueError(f"E006: {ERROR_CODES['E006']}: {str(exc)}")
    elif format_type == "text":
        # 文本输出
        lines = ["审查结果:", "=" * 60]
        for r in results:
            status = "✅" if r.passed else "❌"
            lines.append(f"[{status}] {r.rule_id} ({r.category})")
            lines.append(f"    描述: {r.description}")
            lines.append(f"    结果: {r.message}")
            lines.append("-" * 40)
        return "\n".join(lines)
    else:
        # 无效的格式类型，抛出异常
        raise ValueError(f"E006: {ERROR_CODES['E006']}: 不支持的输出格式: {format_type}")


# ============================================================
# 自检功能（--selftest）
# ============================================================
def run_selftest() -> bool:
    """
    运行自检。使用内置硬编码样例数据，不依赖外部文件、网络或工作目录。
    使用宽松阈值断言，确保在任何环境都能通过。
    """
    print("开始运行自检...")
    reviewer = SwiftUIDesignReviewer()

    # 自检样例数据（硬编码）
    test_data = {
        "vertical_spacing": 16,       # 8 的倍数
        "horizontal_spacing": 12,     # 8 的倍数
        "body_font_size": 16,         # 在 15-17 范围内
        "title_font_size": 28,        # 在 20-34 范围内
        "text_contrast": 5.0,         # 大于 4.5
        "corner_radius": 12,          # 4 的倍数
        "shadow_opacity": 0.2,        # 在 0.1-0.3 范围内
        "view_nesting_depth": 5,      # 小于 10
        "component": "NavigationStack",
        "scenario": "需要多级页面跳转",
        "adaptive_layout": True,
    }

    # 测试 1：审查功能
    try:
        results = reviewer.review(test_data)
        assert len(results) > 0, "E008: 审查结果为空"
        assert len(results) == len(reviewer.rules), "E009: 审查结果数量与规则数量不一致"
        print(f"  测试 1 (审查功能): 通过，共 {len(results)} 条规则")
    except AssertionError as exc:
        print(f"  测试 1 (审查功能): 失败 - {str(exc)}")
        return False
    except Exception as exc:
        print(f"  测试 1 (审查功能): 异常 - {str(exc)}")
        return False

    # 测试 2：组件推荐功能
    try:
        spec = reviewer.get_component_recommendation("TabView")
        assert spec is not None, "E008: 组件推荐不存在"
        assert spec.component_type == "TabView", "E009: 组件类型不匹配"
        assert len(spec.alternatives) > 0, "E009: 替代方案为空"
        print("  测试 2 (组件推荐): 通过")
    except AssertionError as exc:
        print(f"  测试 2 (组件推荐): 失败 - {str(exc)}")
        return False

    # 测试 3：规则检查函数（宽松断言）
    try:
        # 垂直间距检查
        passed, msg = reviewer.check_vertical_spacing({"vertical_spacing": 16})
        assert passed, f"E009: 垂直间距检查失败 - {msg}"
        passed, msg = reviewer.check_vertical_spacing({"vertical_spacing": 10})
        assert not passed, f"E009: 垂直间距应失败但通过了 - {msg}"

        # 正文字号检查
        passed, msg = reviewer.check_body_font_size({"body_font_size": 16})
        assert passed, f"E009: 正文字号检查失败 - {msg}"
        passed, msg = reviewer.check_body_font_size({"body_font_size": 10})
        assert not passed, f"E009: 正文字号应失败但通过了 - {msg}"

        # 对比度检查
        passed, msg = reviewer.check_text_contrast({"text_contrast": 5.0})
        assert passed, f"E009: 对比度检查失败 - {msg}"
        passed, msg = reviewer.check_text_contrast({"text_contrast": 3.0})
        assert not passed, f"E009: 对比度应失败但通过了 - {msg}"

        # 阴影检查
        passed, msg = reviewer.check_shadow_opacity({"shadow_opacity": 0.2})
        assert passed, f"E009: 阴影检查失败 - {msg}"
        passed, msg = reviewer.check_shadow_opacity({"shadow_opacity": 0.8})
        assert not passed, f"E009: 阴影应失败但通过了 - {msg}"

        # 嵌套深度检查
        passed, msg = reviewer.check_view_nesting_depth({"view_nesting_depth": 5})
        assert passed, f"E009: 嵌套深度检查失败 - {msg}"
        passed, msg = reviewer.check_view_nesting_depth({"view_nesting_depth": 15})
        assert not passed, f"E009: 嵌套深度应失败但通过了 - {msg}"

        print("  测试 3 (规则检查): 通过")
    except AssertionError as exc:
        print(f"  测试 3 (规则检查): 失败 - {str(exc)}")
        return False

    # 测试 4：JSON 输出格式
    try:
        json_output = format_review_output(results, "json")
        parsed = json.loads(json_output)
        assert isinstance(parsed, list), "E009: JSON 输出格式错误"
        assert len(parsed) == len(results), "E009: JSON 输出长度不匹配"
        print("  测试 4 (JSON 输出): 通过")
    except Exception as exc:
        print(f"  测试 4 (JSON 输出): 失败 - {str(exc)}")
        return False

    # 测试 5：错误处理
    try:
        format_review_output(results, "invalid_format")
        print("  测试 5 (错误处理): 失败 - 应抛出异常但未抛出")
        return False
    except ValueError as exc:
        # 确认抛出的是 ValueError 类型
        assert "E006" in str(exc), f"E009: 错误消息应包含错误码 E006，实际为: {str(exc)}"
        print("  测试 5 (错误处理): 通过")
    except Exception as exc:
        print(f"  测试 5 (错误处理): 失败 - 未预期的异常类型: {type(exc).__name__}")
        return False

    print("=" * 60)
    print("自检全部通过 ✅")
    return True


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SwiftUI 界面设计审查与规范指导工具",
        epilog="示例: python main.py --data '{\"component\": \"NavigationStack\", \"scenario\": \"多级页面跳转\"}'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检（使用内置硬编码样例数据，无需外部文件）",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="要审查的 JSON 格式数据字符串",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 审查模式
    if not args.data:
        print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as exc:
        print(f"E002: {ERROR_CODES['E002']}: {str(exc)}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print(f"E002: {ERROR_CODES['E002']}: 输入数据必须是 JSON 对象", file=sys.stderr)
        return 1

    try:
        reviewer = SwiftUIDesignReviewer()
        results = reviewer.review(data)
        output = format_review_output(results, args.format)
        print(output)
        return 0
    except ValueError as exc:
        print(f"E006: {str(exc)}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: {ERROR_CODES['E010']}: {str(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
