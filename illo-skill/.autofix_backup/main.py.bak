#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
illo-skill 编辑插画方案生成器 - 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不复制任何既有代码。
提供核心逻辑：主题提炼、构图设计、色彩规划、元素清单、风格定位。
支持 --selftest 参数进行离线自检。
"""

import argparse
import json
import re
import sys
import os

# 错误码定义
ERROR_CODES = {
    "E001": "输入文本为空",
    "E002": "输入文本过短（少于50字）",
    "E003": "输入文本格式不正确（非字符串）",
    "E004": "输出目录不可写",
    "E005": "JSON序列化失败",
    "E006": "色彩规划计算异常",
    "E007": "元素清单生成异常",
    "E008": "构图设计异常",
    "E009": "风格定位异常",
    "E010": "未知错误",
}


class IlloSkillError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def validate_input(text: str) -> None:
    """
    校验输入文本
    - 必须是字符串
    - 非空
    - 长度不少于50字
    """
    if not isinstance(text, str):
        raise IlloSkillError("E003")
    if not text.strip():
        raise IlloSkillError("E001")
    if len(text.strip()) < 50:
        raise IlloSkillError("E002")


def extract_theme(text: str) -> dict:
    """
    主题提炼：从文本中提取核心视觉概念
    返回包含画面核心描述、关键词列表的字典
    """
    # 去除常见停用词和标点
    cleaned = re.sub(r'[，。！？、；：""''（）\s]+', ' ', text)
    # 按空格分割，过滤过短的词
    words = [w for w in cleaned.split() if len(w) > 1]
    # 提取高频词作为关键词（简单实现：取前5个）
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    keywords = [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]]
    
    # 生成一句话画面核心描述
    if keywords:
        core_desc = f"画面核心：以{'、'.join(keywords[:3])}为主要视觉意象，营造与主题呼应的氛围。"
    else:
        core_desc = "画面核心：以抽象几何元素与柔和光影表现主题内涵。"
    
    return {
        "core_description": core_desc,
        "keywords": keywords,
        "visual_concept": "、".join(keywords[:3]) if keywords else "抽象光影"
    }


def design_composition(text: str, theme: dict) -> dict:
    """
    构图设计：规划画面元素的空间关系
    返回文字说明和ASCII示意图
    """
    try:
        # 基于关键词数量决定构图类型
        kw_count = len(theme.get("keywords", []))
        if kw_count >= 4:
            comp_type = "三分法构图"
            ascii_art = (
                "┌─────────┬─────────┐\n"
                "│  主体    │  辅助    │\n"
                "│  (核心)  │  (元素)  │\n"
                "├─────────┼─────────┤\n"
                "│  背景    │  点缀    │\n"
                "│  (氛围)  │  (细节)  │\n"
                "└─────────┴─────────┘"
            )
        elif kw_count >= 2:
            comp_type = "中心对称构图"
            ascii_art = (
                "┌───────────────┐\n"
                "│     辅助元素    │\n"
                "│    ┌─────┐    │\n"
                "│    │ 主体 │    │\n"
                "│    └─────┘    │\n"
                "│     背景氛围    │\n"
                "└───────────────┘"
            )
        else:
            comp_type = "留白式构图"
            ascii_art = (
                "┌───────────────┐\n"
                "│               │\n"
                "│    主体      │\n"
                "│    (居中)    │\n"
                "│               │\n"
                "│   大量留白    │\n"
                "└───────────────┘"
            )
        
        return {
            "composition_type": comp_type,
            "description": f"采用{comp_type}，主体置于视觉焦点位置，辅助元素环绕呼应，背景提供氛围衬托。",
            "ascii_diagram": ascii_art
        }
    except Exception as e:
        raise IlloSkillError("E008", str(e))


def plan_colors(text: str) -> dict:
    """
    色彩规划：建立符合内容基调的配色体系
    返回色值（HEX）和比例分配
    """
    try:
        # 根据文本长度和内容特征选择色系
        text_len = len(text)
        # 简单哈希决定色系偏移
        hash_val = sum(ord(c) for c in text) % 3
        
        if hash_val == 0:
            # 暖色系
            colors = [
                {"hex": "#D4A574", "name": "暖沙色", "ratio": 0.4},
                {"hex": "#C0392B", "name": "砖红色", "ratio": 0.3},
                {"hex": "#F5DEB3", "name": "小麦色", "ratio": 0.2},
                {"hex": "#8B4513", "name": "深棕色", "ratio": 0.1},
            ]
            tone = "温暖、亲和、自然"
        elif hash_val == 1:
            # 冷色系
            colors = [
                {"hex": "#5DADE2", "name": "天蓝色", "ratio": 0.4},
                {"hex": "#2E86C1", "name": "湖蓝色", "ratio": 0.3},
                {"hex": "#AED6F1", "name": "淡蓝色", "ratio": 0.2},
                {"hex": "#1B4F72", "name": "深蓝色", "ratio": 0.1},
            ]
            tone = "冷静、理性、专业"
        else:
            # 中性色系
            colors = [
                {"hex": "#808B96", "name": "灰蓝色", "ratio": 0.35},
                {"hex": "#F2F3F4", "name": "云雾白", "ratio": 0.3},
                {"hex": "#566573", "name": "石墨灰", "ratio": 0.2},
                {"hex": "#D5D8DC", "name": "银灰色", "ratio": 0.15},
            ]
            tone = "简约、现代、高级"
        
        # 根据文本长度调整主色比例（宽松调整）
        if text_len > 200:
            colors[0]["ratio"] = min(0.5, colors[0]["ratio"] + 0.05)
            colors[-1]["ratio"] = max(0.05, colors[-1]["ratio"] - 0.05)
        
        return {
            "tone": tone,
            "palette": colors,
            "description": f"整体色调偏向{tone}风格，主色占比约{int(colors[0]['ratio']*100)}%，辅助色与点缀色协调搭配。"
        }
    except Exception as e:
        raise IlloSkillError("E006", str(e))


def list_elements(theme: dict) -> dict:
    """
    元素清单：拆解画面所需视觉元素
    返回主/辅/背景三层清单
    """
    try:
        keywords = theme.get("keywords", ["抽象图形"])
        main_kw = keywords[0] if keywords else "主体物"
        sub_kws = keywords[1:3] if len(keywords) > 1 else ["辅助图形"]
        bg_kws = keywords[3:5] if len(keywords) > 3 else ["背景纹理"]
        
        return {
            "main_elements": [
                f"主体{main_kw}（视觉焦点）",
                f"核心{main_kw}的简化轮廓",
                f"{main_kw}的光影层次",
            ],
            "auxiliary_elements": [
                f"辅助元素：{'、'.join(sub_kws)}",
                "几何装饰图形",
                "线条引导元素",
            ],
            "background_elements": [
                f"背景氛围：{'、'.join(bg_kws)}",
                "渐变底色",
                "纹理细节",
            ]
        }
    except Exception as e:
        raise IlloSkillError("E007", str(e))


def define_style(text: str, theme: dict) -> dict:
    """
    风格定位：描述性风格建议
    返回文字描述和参考方向
    """
    try:
        # 基于文本特征选择风格方向
        text_len = len(text)
        has_digit = bool(re.search(r'\d', text))
        
        if has_digit:
            style_name = "现代简约风"
            style_desc = "以简洁的几何形态和明快的色彩对比，突出信息层级，适合数据或科技类内容。"
            direction = "参考方向：扁平化设计、几何抽象、大面积色块"
        elif text_len > 150:
            style_name = "叙事插画风"
            style_desc = "通过丰富的场景细节和叙事性画面，营造沉浸式阅读体验，适合故事性内容。"
            direction = "参考方向：绘本风格、场景化插画、多元素组合"
        else:
            style_name = "意境留白风"
            style_desc = "以简约构图和大量留白传递意境，强调氛围营造，适合散文或抒情内容。"
            direction = "参考方向：水墨意境、极简主义、负空间运用"
        
        return {
            "style_name": style_name,
            "description": style_desc,
            "reference_direction": direction
        }
    except Exception as e:
        raise IlloSkillError("E009", str(e))


def generate_plan(text: str) -> dict:
    """
    生成完整插画方案
    """
    # 校验输入
    validate_input(text)
    
    # 依次执行各模块
    theme = extract_theme(text)
    composition = design_composition(text, theme)
    colors = plan_colors(text)
    elements = list_elements(theme)
    style = define_style(text, theme)
    
    # 组装完整方案
    plan = {
        "title": "编辑插画视觉方案",
        "theme": theme,
        "composition": composition,
        "colors": colors,
        "elements": elements,
        "style": style,
        "metadata": {
            "version": "1.0.2",
            "generator": "illo-skill"
        }
    }
    return plan


def save_plan(plan: dict, output_path: str) -> None:
    """
    保存方案为JSON文件
    """
    try:
        # 检查输出目录是否可写
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        if output_dir and not os.access(output_dir, os.W_OK):
            raise IlloSkillError("E004")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
    except IlloSkillError:
        raise
    except Exception as e:
        raise IlloSkillError("E005", str(e))


def run_selftest() -> bool:
    """
    自检函数：使用内置硬编码样例数据，离线验证核心逻辑
    使用宽松阈值，不依赖精确值
    """
    print("=== illo-skill 自检开始 ===")
    
    # 硬编码测试样例（不少于50字）
    test_text = (
        "在数字化浪潮席卷全球的今天，人工智能技术正在深刻改变着内容创作的方式。"
        "编辑们需要快速将抽象的文章概念转化为直观的视觉语言，以满足读者的阅读期待。"
        "插画作为一种重要的视觉表达形式，能够在瞬间传递情感与信息，增强文章的感染力。"
        "通过系统化的视觉方案设计，我们可以让每一篇文章都拥有独特的视觉身份。"
    )
    
    try:
        # 1. 输入校验测试
        print("[1/5] 测试输入校验...")
        validate_input(test_text)  # 应通过
        print("  ✓ 合法输入通过")
        
        # 2. 主题提炼测试
        print("[2/5] 测试主题提炼...")
        theme = extract_theme(test_text)
        assert len(theme["keywords"]) > 0, "关键词列表不应为空"
        assert len(theme["core_description"]) > 5, "核心描述应有一定长度"
        print(f"  ✓ 主题提炼通过，关键词数: {len(theme['keywords'])}")
        
        # 3. 构图与色彩测试
        print("[3/5] 测试构图与色彩...")
        comp = design_composition(test_text, theme)
        assert comp["composition_type"], "构图类型不应为空"
        assert "┌" in comp["ascii_diagram"], "ASCII示意图应包含边框"
        
        colors = plan_colors(test_text)
        assert len(colors["palette"]) == 4, "配色应包含4个颜色"
        total_ratio = sum(c["ratio"] for c in colors["palette"])
        assert abs(total_ratio - 1.0) < 0.2, f"配色比例总和应接近1，实际: {total_ratio}"
        print(f"  ✓ 构图({comp['composition_type']})与色彩({colors['tone']})通过")
        
        # 4. 元素清单与风格测试
        print("[4/5] 测试元素清单与风格...")
        elements = list_elements(theme)
        assert len(elements["main_elements"]) >= 1, "应有主体元素"
        assert len(elements["auxiliary_elements"]) >= 1, "应有辅助元素"
        assert len(elements["background_elements"]) >= 1, "应有背景元素"
        
        style = define_style(test_text, theme)
        assert style["style_name"], "风格名称不应为空"
        assert len(style["description"]) > 10, "风格描述应有一定长度"
        print(f"  ✓ 元素清单与风格({style['style_name']})通过")
        
        # 5. 完整方案生成测试
        print("[5/5] 测试完整方案生成...")
        plan = generate_plan(test_text)
        assert "theme" in plan
        assert "composition" in plan
        assert "colors" in plan
        assert "elements" in plan
        assert "style" in plan
        print("  ✓ 完整方案生成通过")
        
        print("\n=== 自检全部通过 ===")
        return True
        
    except AssertionError as e:
        print(f"\n[自检失败] 断言错误: {e}")
        return False
    except IlloSkillError as e:
        print(f"\n[自检失败] 业务错误: {e.code} {e.message}")
        return False
    except Exception as e:
        print(f"\n[自检失败] 未知错误: {e}")
        return False


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="illo-skill 编辑插画方案生成器",
        epilog="示例: python main.py --input article.txt --output plan.json"
    )
    parser.add_argument("--input", "-i", help="输入文章文件路径")
    parser.add_argument("--output", "-o", default="illo_plan.json", help="输出方案文件路径（默认: illo_plan.json）")
    parser.add_argument("--text", "-t", help="直接输入文章文本（用于测试）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 正常模式：需要输入
    try:
        if args.text:
            # 直接使用命令行文本
            text = args.text
        elif args.input:
            # 从文件读取
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    text = f.read()
            except FileNotFoundError:
                print(f"[E010] 输入文件不存在: {args.input}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"[E010] 读取文件失败: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # 交互模式
            print("请输入文章内容（不少于50字，输入完成后按 Ctrl+D 结束）：")
            try:
                lines = []
                for line in sys.stdin:
                    lines.append(line)
                text = "\n".join(lines)
            except KeyboardInterrupt:
                print("\n[E010] 输入已取消", file=sys.stderr)
                sys.exit(1)
        
        # 生成方案
        plan = generate_plan(text)
        
        # 保存方案
        save_plan(plan, args.output)
        
        # 输出摘要
        print(f"✓ 插画方案已生成并保存至: {args.output}")
        print(f"  主题: {plan['theme']['core_description']}")
        print(f"  构图: {plan['composition']['composition_type']}")
        print(f"  风格: {plan['style']['style_name']}")
        
    except IlloSkillError as e:
        print(f"错误: {e.code} - {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
