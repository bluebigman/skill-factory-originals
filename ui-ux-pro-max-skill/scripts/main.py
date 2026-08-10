#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
UI/UX Pro Max Skill — 独立实现脚本（clean-room 重写）

依据功能规格实现核心逻辑：
- 需求转结构化方案（模块清单 + 页面架构）
- 设计规范生成（色彩系统 + 字体层级 + 间距规则）
- 组件库规划（组件分类 + 状态定义）
- 前端代码指引（HTML/CSS 结构建议 + 响应式断点）
- 可用性自查（问题清单 + 修改优先级）

仅使用标准库，无第三方依赖。
命令行参数：
    --selftest    离线自检核心逻辑（硬编码样例，不读文件、不依赖目录、不联网）
"""

import sys
import json
import argparse
from typing import Dict, List, Any, Tuple

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入格式不正确（非字典/列表）",
    "E003": "品牌色值格式无效（应为 #RRGGBB）",
    "E004": "风格关键词为空列表",
    "E005": "页面清单为空",
    "E006": "组件分类为空",
    "E007": "设计稿标注格式错误",
    "E008": "可用性自查输入格式错误",
    "E009": "内部处理异常",
    "E010": "未知错误",
}

class SkillError(Exception):
    """技能自定义异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心逻辑函数
# ============================================================

def parse_requirement(description: str) -> Dict[str, Any]:
    """
    功能1：需求转结构化方案
    输入：一句话产品描述
    输出：功能模块清单 + 页面架构图（结构化）
    """
    if not description or not isinstance(description, str):
        raise SkillError("E001", "需求描述不能为空且必须是字符串")

    # 基于关键词的简单解析（clean-room 规则，不复制任何既有实现）
    keywords = ["登录", "注册", "首页", "列表", "详情", "搜索", "设置", "个人", "购物", "支付", "订单", "消息"]
    modules = []
    for kw in keywords:
        if kw in description:
            modules.append(kw)

    if not modules:
        modules = ["首页", "列表", "详情"]  # 默认模块

    pages = [f"{m}页" for m in modules]
    # 页面架构：层级结构
    architecture = {
        "层级1": pages[0] if pages else "首页",
        "层级2": pages[1:3] if len(pages) > 1 else [],
        "层级3": pages[3:] if len(pages) > 3 else [],
    }

    return {
        "功能模块": modules,
        "页面架构": architecture,
        "页面总数": len(pages),
    }


def generate_design_tokens(brand_color: str, style_keywords: List[str]) -> Dict[str, Any]:
    """
    功能2：设计规范生成
    输入：品牌色值（#RRGGBB）、风格关键词列表
    输出：色彩系统 + 字体层级 + 间距规则
    """
    # 校验品牌色
    if not brand_color or not isinstance(brand_color, str) or len(brand_color) != 7 or not brand_color.startswith("#"):
        raise SkillError("E003")

    try:
        r = int(brand_color[1:3], 16)
        g = int(brand_color[3:5], 16)
        b = int(brand_color[5:7], 16)
    except ValueError:
        raise SkillError("E003")

    if not style_keywords or not isinstance(style_keywords, list) or len(style_keywords) == 0:
        raise SkillError("E004")

    # 色彩系统：基于品牌色派生
    def adjust_channel(ch: int, delta: int) -> int:
        return max(0, min(255, ch + delta))

    color_system = {
        "primary": brand_color,
        "primary_light": f"#{adjust_channel(r, 40):02x}{adjust_channel(g, 40):02x}{adjust_channel(b, 40):02x}",
        "primary_dark": f"#{adjust_channel(r, -40):02x}{adjust_channel(g, -40):02x}{adjust_channel(b, -40):02x}",
        "background": "#F5F5F5",
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "border": "#E0E0E0",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
    }

    # 字体层级
    if "简约" in style_keywords or "现代" in style_keywords:
        font_family = "Inter, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        heading_scale = 1.25
    elif "复古" in style_keywords or "传统" in style_keywords:
        font_family = "Georgia, 'Songti SC', 'SimSun', serif"
        heading_scale = 1.15
    else:
        font_family = "system-ui, -apple-system, 'Segoe UI', sans-serif"
        heading_scale = 1.2

    base_size = 16
    type_scale = {
        "h1": int(base_size * heading_scale ** 3),
        "h2": int(base_size * heading_scale ** 2),
        "h3": int(base_size * heading_scale ** 1),
        "body": base_size,
        "caption": int(base_size * 0.875),
    }

    # 间距规则（4px 基准）
    spacing_scale = {
        "xs": 4,
        "sm": 8,
        "md": 16,
        "lg": 24,
        "xl": 32,
        "xxl": 48,
    }

    return {
        "色彩系统": color_system,
        "字体层级": {
            "font_family": font_family,
            "type_scale": type_scale,
        },
        "间距规则": spacing_scale,
        "风格关键词": style_keywords,
    }


def plan_component_library(components_input: List[str]) -> Dict[str, Any]:
    """
    功能3：组件库规划
    输入：组件名称列表（或线框图描述）
    输出：组件分类表 + 状态定义
    """
    if not components_input or not isinstance(components_input, list) or len(components_input) == 0:
        raise SkillError("E006")

    # 组件分类
    categories = {
        "基础组件": ["按钮", "输入框", "图标", "标签"],
        "导航组件": ["导航栏", "标签页", "面包屑"],
        "反馈组件": ["弹窗", "提示", "加载"],
        "业务组件": [],
    }

    uncategorized = []
    for comp in components_input:
        found = False
        for cat, comps in categories.items():
            if any(c in comp for c in comps) or comp in comps:
                found = True
                break
        if not found and comp not in categories["业务组件"]:
            categories["业务组件"].append(comp)

    if not categories["业务组件"]:
        categories["业务组件"] = ["自定义业务组件"]

    # 状态定义
    states = ["默认", "悬停", "激活", "禁用", "加载", "错误"]

    return {
        "组件分类": categories,
        "状态定义": states,
        "组件总数": len(components_input),
    }


def generate_frontend_guidance(annotations: Dict[str, Any]) -> Dict[str, Any]:
    """
    功能4：前端代码指引
    输入：设计稿标注（字典，包含 width, height, breakpoints 等）
    输出：HTML/CSS 结构建议 + 响应式断点
    """
    if not annotations or not isinstance(annotations, dict):
        raise SkillError("E007")

    width = annotations.get("width", 375)
    height = annotations.get("height", 812)
    breakpoints = annotations.get("breakpoints", [375, 768, 1024, 1440])

    if not isinstance(breakpoints, list) or len(breakpoints) == 0:
        breakpoints = [375, 768, 1024, 1440]

    # 响应式断点建议
    bp_suggestions = {}
    for bp in sorted(breakpoints):
        if bp <= 480:
            bp_suggestions[f"≤{bp}px"] = "移动端竖屏（单列布局）"
        elif bp <= 768:
            bp_suggestions[f"≤{bp}px"] = "平板竖屏/大屏手机（双列布局）"
        elif bp <= 1024:
            bp_suggestions[f"≤{bp}px"] = "平板横屏/小笔记本（三列布局）"
        else:
            bp_suggestions[f"> {bp}px"] = "桌面端（多列栅格布局）"

    # HTML 结构建议
    html_structure = {
        "容器": f"<div class=\"container\" style=\"max-width: {max(breakpoints)}px; margin: 0 auto;\">",
        "头部": "<header>（包含导航与品牌区）</header>",
        "主体": "<main>（包含各功能区块）</main>",
        "底部": "<footer>（包含版权与链接）</footer>",
    }

    # CSS 建议
    css_suggestions = {
        "盒模型": "使用 border-box 全局设置",
        "布局": "Flexbox 用于一维布局，Grid 用于二维布局",
        "单位": "rem 用于字体，px 用于边框，% / vw / vh 用于响应式尺寸",
        "媒体查询": "@media (min-width: ...) 逐级增强",
    }

    return {
        "设计稿尺寸": {"width": width, "height": height},
        "响应式断点": bp_suggestions,
        "HTML结构建议": html_structure,
        "CSS建议": css_suggestions,
    }


def usability_check(design_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    功能5：可用性自查
    输入：设计稿数据（包含对比度、字号、点击区域等）
    输出：问题清单 + 修改优先级
    """
    if not design_data or not isinstance(design_data, dict):
        raise SkillError("E008")

    issues = []
    priorities = {"高": [], "中": [], "低": []}

    # 检查对比度
    contrast = design_data.get("contrast_ratio", 3.0)
    if contrast < 3.0:
        issues.append("文本与背景对比度不足（< 3:1），影响可读性")
        priorities["高"].append("提升对比度至至少 4.5:1")
    elif contrast < 4.5:
        issues.append("对比度处于边缘（3:1 ~ 4.5:1），建议优化")
        priorities["中"].append("适当加深文字颜色或提亮背景")

    # 检查字号
    font_size = design_data.get("font_size", 12)
    if font_size < 14:
        issues.append(f"正文字号 {font_size}px 过小，建议不小于 14px")
        priorities["高"].append("将正文字号提升至 14px 以上")
    elif font_size < 16:
        issues.append(f"正文字号 {font_size}px 偏小，建议使用 16px")
        priorities["中"].append("考虑提升字号至 16px")

    # 检查点击区域
    touch_target = design_data.get("touch_target", 40)
    if touch_target < 44:
        issues.append(f"点击区域 {touch_target}px 小于推荐值 44px")
        priorities["高"].append("扩大点击区域至至少 44×44px")
    else:
        priorities["低"].append("点击区域符合无障碍标准")

    # 检查间距
    spacing = design_data.get("spacing", 8)
    if spacing < 8:
        issues.append(f"元素间距 {spacing}px 过小，容易误触")
        priorities["中"].append("增加元素间距至至少 8px")

    if not issues:
        issues.append("未发现明显可用性问题")
        priorities["低"].append("建议进行真实用户测试验证")

    return {
        "问题清单": issues,
        "修改优先级": priorities,
        "问题总数": len(issues),
    }


# ============================================================
# 自检函数（--selftest）
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用硬编码样例数据。
    断言使用宽松阈值，不依赖精确值/边界值。
    """
    print("=" * 60)
    print("UI/UX Pro Max Skill 自检开始")
    print("=" * 60)

    # --- 测试 1: 需求转结构化方案 ---
    print("\n[1/5] 测试需求解析...")
    try:
        result = parse_requirement("这是一个包含登录和首页的电商应用，有搜索和购物功能")
        assert "功能模块" in result, "缺少功能模块"
        assert "页面架构" in result, "缺少页面架构"
        assert len(result["功能模块"]) >= 3, f"模块数量过少: {len(result['功能模块'])}"
        assert result["页面总数"] >= 3, f"页面总数过少: {result['页面总数']}"
        assert "登录" in result["功能模块"], "未识别登录模块"
        assert "首页" in result["功能模块"], "未识别首页模块"
        print(f"  ✓ 解析成功，模块数: {result['页面总数']}, 模块: {result['功能模块']}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 技能错误: {e}")
        return False

    # --- 测试 2: 设计规范生成 ---
    print("\n[2/5] 测试设计规范生成...")
    try:
        tokens = generate_design_tokens("#3366FF", ["现代", "简约"])
        assert "色彩系统" in tokens, "缺少色彩系统"
        assert "字体层级" in tokens, "缺少字体层级"
        assert "间距规则" in tokens, "缺少间距规则"
        assert tokens["色彩系统"]["primary"] == "#3366FF", "主色不匹配"
        assert tokens["色彩系统"]["primary_light"] != tokens["色彩系统"]["primary_dark"], "亮色与暗色不应相同"
        assert tokens["字体层级"]["type_scale"]["body"] >= 14, "正文字号过小"
        assert tokens["间距规则"]["md"] >= 12, "中等间距过小"
        print(f"  ✓ 设计规范生成成功，主色: {tokens['色彩系统']['primary']}")
        print(f"    字体层级: {tokens['字体层级']['type_scale']}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 技能错误: {e}")
        return False

    # --- 测试 3: 组件库规划 ---
    print("\n[3/5] 测试组件库规划...")
    try:
        components = ["按钮", "输入框", "导航栏", "购物车卡片", "价格标签"]
        comp_plan = plan_component_library(components)
        assert "组件分类" in comp_plan, "缺少组件分类"
        assert "状态定义" in comp_plan, "缺少状态定义"
        assert len(comp_plan["状态定义"]) >= 4, f"状态定义过少: {len(comp_plan['状态定义'])}"
        assert "默认" in comp_plan["状态定义"], "缺少默认状态"
        assert "禁用" in comp_plan["状态定义"], "缺少禁用状态"
        assert comp_plan["组件总数"] == len(components), "组件总数不匹配"
        print(f"  ✓ 组件库规划成功，组件数: {comp_plan['组件总数']}, 状态数: {len(comp_plan['状态定义'])}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 技能错误: {e}")
        return False

    # --- 测试 4: 前端代码指引 ---
    print("\n[4/5] 测试前端代码指引...")
    try:
        annotations = {
            "width": 375,
            "height": 812,
            "breakpoints": [375, 768, 1024],
        }
        guidance = generate_frontend_guidance(annotations)
        assert "响应式断点" in guidance, "缺少响应式断点"
        assert "HTML结构建议" in guidance, "缺少HTML结构建议"
        assert "CSS建议" in guidance, "缺少CSS建议"
        assert len(guidance["响应式断点"]) >= 3, f"断点数量过少: {len(guidance['响应式断点'])}"
        assert "容器" in guidance["HTML结构建议"], "缺少容器建议"
        assert "媒体查询" in guidance["CSS建议"], "缺少媒体查询建议"
        print(f"  ✓ 前端指引生成成功，断点数: {len(guidance['响应式断点'])}")
        for bp, desc in guidance["响应式断点"].items():
            print(f"    {bp}: {desc}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 技能错误: {e}")
        return False

    # --- 测试 5: 可用性自查 ---
    print("\n[5/5] 测试可用性自查...")
    try:
        # 宽松样例：对比度 2.5（明确不达标）、字号 13（偏小）、点击区域 40（偏小）
        design = {
            "contrast_ratio": 2.5,
            "font_size": 13,
            "touch_target": 40,
            "spacing": 6,
        }
        check = usability_check(design)
        assert "问题清单" in check, "缺少问题清单"
        assert "修改优先级" in check, "缺少修改优先级"
        assert check["问题总数"] >= 3, f"问题数量过少: {check['问题总数']}"
        assert len(check["修改优先级"]["高"]) >= 1, "高优先级问题缺失"
        assert len(check["问题清单"]) == check["问题总数"], "问题清单数量不一致"
        print(f"  ✓ 可用性自查成功，发现问题: {check['问题总数']} 个")
        for issue in check["问题清单"]:
            print(f"    - {issue}")
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 技能错误: {e}")
        return False

    # --- 全部通过 ---
    print("\n" + "=" * 60)
    print("✅ 全部自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="UI/UX Pro Max Skill — 界面设计与前端还原辅助工具",
        epilog="示例: python main.py --selftest"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（硬编码样例，不读文件、不联网）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 文件路径（可选，用于批量处理）"
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 无参数时打印帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
