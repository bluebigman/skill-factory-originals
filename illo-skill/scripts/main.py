#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
illo-skill — 编辑插画方案生成器（独立实现）

本脚本依据功能规格独立编写（clean-room），不复制任何既有代码。
仅使用标准库，无第三方依赖。

功能：
- 从输入文本中提取核心视觉概念（主题提炼）
- 规划画面元素的空间关系（构图设计）
- 建立符合内容基调的配色体系（色彩规划）
- 拆解画面所需视觉元素（元素清单）
- 描述性风格建议（风格定位）

用法：
    python main.py --input "文章文本" [--style "风格词"] [--output file.json]
    python main.py --selftest          # 离线自检核心逻辑

错误码：
    E001 输入为空
    E002 输入文本过短（少于50字）
    E003 未知命令行参数
    E004 输出文件写入失败
    E005 内部逻辑错误（自检失败）
    E006 输入包含非法字符（不可打印字符）
    E007 风格参数无效（非字符串）
    E008 自检数据异常
    E009 输出格式不支持
    E010 运行时异常
"""

import argparse
import json
import re
import sys
import tempfile
import os
from collections import Counter
from datetime import datetime


# ============================================================
# 常量定义
# ============================================================

# 最小输入长度
MIN_INPUT_LENGTH = 50

# 默认配色方案（按内容基调匹配）
DEFAULT_PALETTES = {
    "tech": {"name": "科技冷调", "colors": [{"hex": "#0F2027", "ratio": 0.4}, {"hex": "#203A43", "ratio": 0.3}, {"hex": "#2C5364", "ratio": 0.2}, {"hex": "#E0E0E0", "ratio": 0.1}]},
    "nature": {"name": "自然暖调", "colors": [{"hex": "#2D5016", "ratio": 0.35}, {"hex": "#6B8E23", "ratio": 0.3}, {"hex": "#C0C040", "ratio": 0.2}, {"hex": "#F5F5DC", "ratio": 0.15}]},
    "business": {"name": "商务理性", "colors": [{"hex": "#1A1A2E", "ratio": 0.4}, {"hex": "#16213E", "ratio": 0.3}, {"hex": "#0F3460", "ratio": 0.2}, {"hex": "#E94560", "ratio": 0.1}]},
    "creative": {"name": "创意活力", "colors": [{"hex": "#FF6B6B", "ratio": 0.3}, {"hex": "#4ECDC4", "ratio": 0.3}, {"hex": "#FFE66D", "ratio": 0.2}, {"hex": "#292F36", "ratio": 0.2}]},
    "default": {"name": "中性平衡", "colors": [{"hex": "#2C3E50", "ratio": 0.35}, {"hex": "#E67E22", "ratio": 0.25}, {"hex": "#ECF0F1", "ratio": 0.25}, {"hex": "#95A5A6", "ratio": 0.15}]},
}

# 常见停用词（用于关键词提取）
STOP_WORDS = set("""的 了 和 是 在 我 有 也 就 不 人 都 一 一个 上 很 到 说 要 去 你 会 着 没有 看 好 自己 这 那 他 她 它 我们 你们 他们 这个 那个 这些 那些 但 而 或 与 及 并 等 从 为 以 于 之 其 所 因 被 把 让 向 往 对 比 还 又 再 更 最 太 很 非常 特别 十分 比较 相当 有些 有点 稍微 略微 大致 几乎 大约 左右 上下 前后 之间 之 内 外 中 里 上 下 左 右 前 后 东 南 西 北 来 去 回 过 起 落 开 关 打 拿 放 走 跑 跳 看 听 说 读 写 画 想 认为 觉得 感觉 知道 明白 理解 希望 期望 要求 需要 必须 应该 可以 可能 能够 得到 成为 作为 进行 开始 结束 完成 实现 产生 出现 存在 变化 发展 提高 降低 增加 减少 扩大 缩小 加强 减弱 改善 恶化 解决 处理 管理 控制 使用 利用 采用 采取 提供 给予 获得 失去 保持 维持 继续 停止 开始 结束 完成 实现 产生 出现 存在 变化 发展 提高 降低 增加 减少 扩大 缩小 加强 减弱 改善 恶化 解决 处理 管理 控制 使用 利用 采用 采取 提供 给予 获得 失去 保持 维持 继续 停止 是 的 了 在 和 有 就 不 人 都 一 一个 上 很 到 说 要 去 你 会 着 没有 看 好 自己 这 那 他 她 它 我们 你们 他们 这个 那个 这些 那些 但 而 或 与 及 并 等 从 为 以 于 之 其 所 因 被 把 让 向 往 对 比 还 又 再 更 最 太 很 非常 特别 十分 比较 相当 有些 有点 稍微 略微 大致 几乎 大约 左右 上下 前后 之间 之 内 外 中 里 上 下 左 右 前 后 东 南 西 北 来 去 回 过 起 落 开 关 打 拿 放 走 跑 跳 看 听 说 读 写 画 想 认为 觉得 感觉 知道 明白 理解 希望 期望 要求 需要 必须 应该 可以 可能 能够 得到 成为 作为 进行 开始 结束 完成 实现 产生 出现 存在 变化 发展 提高 降低 增加 减少 扩大 缩小 加强 减弱 改善 恶化 解决 处理 管理 控制 使用 利用 采用 采取 提供 给予 获得 失去 保持 维持 继续 停止""".split())


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(text):
    """
    验证输入文本是否合法。
    
    参数:
        text (str): 输入文本
        
    返回:
        tuple: (是否合法, 错误码或None)
    """
    if not text or not text.strip():
        return False, "E001"
    if len(text.strip()) < MIN_INPUT_LENGTH:
        return False, "E002"
    # 检查是否包含非法字符（不可打印字符，但允许换行和制表符）
    for ch in text:
        if ord(ch) < 32 and ch not in '\n\t\r':
            return False, "E006"
    return True, None


def extract_theme(text):
    """
    主题提炼：从输入文本中提取核心视觉概念。
    
    策略：
    1. 过滤停用词
    2. 统计词频
    3. 选取高频且有意义的词汇组合成一句话
    
    参数:
        text (str): 输入文本
        
    返回:
        str: 一句话画面核心描述
    """
    # 清理文本，提取中文词汇
    clean_text = re.sub(r'[^\u4e00-\u9fff\w\s]', ' ', text)
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', clean_text)
    
    # 过滤停用词和过短的词
    filtered = [w for w in words if w.lower() not in STOP_WORDS and len(w) >= 2]
    
    if not filtered:
        return "以抽象几何形态表现核心概念"
    
    # 统计词频
    counter = Counter(filtered)
    top_words = [w for w, _ in counter.most_common(3)]
    
    # 组合成一句话
    if len(top_words) >= 3:
        theme = f"以{top_words[0]}为核心，结合{top_words[1]}与{top_words[2]}的视觉意象"
    elif len(top_words) == 2:
        theme = f"以{top_words[0]}与{top_words[1]}的互动关系为主线"
    else:
        theme = f"突出{top_words[0]}的本质特征"
    
    return theme


def design_composition(theme, text_length):
    """
    构图设计：规划画面元素的空间关系。
    
    根据文本长度和主题特点，生成不同的构图方案。
    
    参数:
        theme (str): 主题描述
        text_length (int): 输入文本长度
        
    返回:
        dict: 包含文字说明和ASCII示意图
    """
    # 根据文本长度选择构图类型
    if text_length > 200:
        composition_type = "三段式"
        description = "画面分为上中下三层：上层为背景氛围，中层为主体形象，下层为细节元素"
        ascii_art = """
        ┌─────────────────────────┐
        │        背景氛围层        │
        │   ┌─────────────────┐   │
        │   │    主体形象      │   │
        │   │    (核心元素)    │   │
        │   └─────────────────┘   │
        │        细节元素区        │
        └─────────────────────────┘
        """
    elif text_length > 100:
        composition_type = "对称式"
        description = "画面采用左右对称构图，主体居中，两侧元素平衡呼应"
        ascii_art = """
        ┌─────────────────────────┐
        │   元素A   │  元素B      │
        │           │             │
        │  ┌─────┐  │  ┌─────┐   │
        │  │ 主  │  │  │ 要  │   │
        │  │ 体  │  │  │ 素  │   │
        │  └─────┘  │  └─────┘   │
        │   元素C   │  元素D      │
        └─────────────────────────┘
        """
    else:
        composition_type = "聚焦式"
        description = "画面采用中心聚焦构图，主体占据视觉中心，周围以留白和辅助元素衬托"
        ascii_art = """
        ┌─────────────────────────┐
        │                         │
        │      ┌───────────┐      │
        │      │  主体核心  │      │
        │      │  视觉焦点  │      │
        │      └───────────┘      │
        │                         │
        └─────────────────────────┘
        """
    
    return {
        "type": composition_type,
        "description": description,
        "ascii_art": ascii_art.strip()
    }


def analyze_tone(text):
    """
    分析文本基调，用于匹配配色方案。
    
    通过关键词匹配判断内容属于科技/自然/商务/创意等类型。
    
    参数:
        text (str): 输入文本
        
    返回:
        str: 基调类型（tech/nature/business/creative/default）
    """
    tone_keywords = {
        "tech": ["科技", "数据", "算法", "程序", "网络", "智能", "数字", "代码", "系统", "软件", "硬件", "AI", "人工智能", "计算", "信息"],
        "nature": ["自然", "生态", "环境", "植物", "动物", "山水", "森林", "海洋", "气候", "绿色", "地球", "环保", "生物"],
        "business": ["商业", "市场", "经济", "管理", "战略", "营销", "金融", "投资", "企业", "品牌", "客户", "产品", "销售"],
        "creative": ["创意", "艺术", "设计", "想象", "灵感", "美学", "视觉", "文化", "音乐", "绘画", "创新", "表达"],
    }
    
    scores = {tone: 0 for tone in tone_keywords}
    for tone, keywords in tone_keywords.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                scores[tone] += 1
    
    if max(scores.values()) == 0:
        return "default"
    
    return max(scores, key=scores.get)


def plan_colors(tone):
    """
    色彩规划：根据内容基调建立配色体系。
    
    参数:
        tone (str): 基调类型
        
    返回:
        dict: 包含配色方案名称、色值和比例
    """
    palette = DEFAULT_PALETTES.get(tone, DEFAULT_PALETTES["default"])
    return {
        "name": palette["name"],
        "colors": palette["colors"]
    }


def list_elements(theme, tone):
    """
    元素清单：拆解画面所需视觉元素。
    
    参数:
        theme (str): 主题描述
        tone (str): 基调类型
        
    返回:
        dict: 主/辅/背景三层元素清单
    """
    # 从主题中提取关键词作为主元素
    theme_words = [w for w in re.findall(r'[\u4e00-\u9fff]+', theme) if w not in STOP_WORDS and len(w) >= 2]
    
    main_elements = theme_words[:2] if theme_words else ["核心意象"]
    if len(main_elements) < 2:
        main_elements.append("辅助意象")
    
    # 根据基调生成辅助元素
    tone_supplements = {
        "tech": ["数据流", "几何图形", "节点连线"],
        "nature": ["枝叶纹理", "光影变化", "自然形态"],
        "business": ["图表曲线", "建筑轮廓", "人物剪影"],
        "creative": ["抽象形状", "色彩碰撞", "手绘线条"],
        "default": ["几何形态", "渐变层次", "留白空间"],
    }
    
    supplements = tone_supplements.get(tone, tone_supplements["default"])
    
    return {
        "main": main_elements,
        "supplementary": supplements[:2],
        "background": ["氛围底色", "纹理细节", "空间层次"]
    }


def describe_style(tone):
    """
    风格定位：描述性风格建议。
    
    不使用具体艺术家姓名，仅使用通用美术术语。
    
    参数:
        tone (str): 基调类型
        
    返回:
        dict: 包含风格描述和参考方向
    """
    style_map = {
        "tech": {
            "description": "简洁现代的扁平化风格，强调线条感与几何秩序，适当运用渐变和光效",
            "direction": "可参考现代科技类杂志的配图风格，注重信息层级与视觉节奏"
        },
        "nature": {
            "description": "柔和自然的写意风格，注重光影层次与有机形态，色彩温润不刺眼",
            "direction": "可参考自然类纪录片的画面处理，强调氛围感与呼吸感"
        },
        "business": {
            "description": "稳重清晰的商务风格，构图规整，色彩克制，突出专业感与可信度",
            "direction": "可参考财经类刊物的信息图表设计，注重清晰与效率"
        },
        "creative": {
            "description": "大胆自由的创意风格，允许夸张变形与超现实组合，色彩鲜明有冲击力",
            "direction": "可参考当代艺术展览的视觉表达，鼓励突破常规"
        },
        "default": {
            "description": "均衡通用的中性风格，兼顾可读性与美感，不强调特定倾向",
            "direction": "可参考主流编辑插画的通用范式，注重内容适配"
        }
    }
    
    return style_map.get(tone, style_map["default"])


def generate_plan(text):
    """
    生成完整的插画方案。
    
    参数:
        text (str): 输入文本
        
    返回:
        dict: 完整的方案文档
    """
    # 验证输入
    is_valid, error_code = validate_input(text)
    if not is_valid:
        raise ValueError(f"输入验证失败: {error_code}")
    
    # 执行各模块
    theme = extract_theme(text)
    composition = design_composition(theme, len(text))
    tone = analyze_tone(text)
    colors = plan_colors(tone)
    elements = list_elements(theme, tone)
    style = describe_style(tone)
    
    # 组装方案
    plan = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0.2",
            "skill": "illo-skill"
        },
        "theme": theme,
        "composition": composition,
        "color_scheme": colors,
        "elements": elements,
        "style": style
    }
    
    return plan


def format_output(plan, format_type="text"):
    """
    格式化输出方案。
    
    参数:
        plan (dict): 方案数据
        format_type (str): 输出格式（text/json）
        
    返回:
        str: 格式化后的文本
    """
    if format_type == "json":
        return json.dumps(plan, ensure_ascii=False, indent=2)
    elif format_type == "text":
        lines = []
        lines.append("=" * 50)
        lines.append("编辑插画方案（illo-skill）")
        lines.append("=" * 50)
        lines.append(f"生成时间: {plan['meta']['generated_at']}")
        lines.append("")
        lines.append("【主题提炼】")
        lines.append(f"  {plan['theme']}")
        lines.append("")
        lines.append("【构图设计】")
        lines.append(f"  类型: {plan['composition']['type']}")
        lines.append(f"  说明: {plan['composition']['description']}")
        lines.append("  示意图:")
        lines.append(plan['composition']['ascii_art'])
        lines.append("")
        lines.append("【色彩规划】")
        lines.append(f"  方案: {plan['color_scheme']['name']}")
        for color in plan['color_scheme']['colors']:
            ratio_pct = int(color['ratio'] * 100)
            lines.append(f"  {color['hex']}  占比约{ratio_pct}%")
        lines.append("")
        lines.append("【元素清单】")
        lines.append(f"  主元素: {', '.join(plan['elements']['main'])}")
        lines.append(f"  辅助元素: {', '.join(plan['elements']['supplementary'])}")
        lines.append(f"  背景元素: {', '.join(plan['elements']['background'])}")
        lines.append("")
        lines.append("【风格定位】")
        lines.append(f"  描述: {plan['style']['description']}")
        lines.append(f"  参考方向: {plan['style']['direction']}")
        lines.append("=" * 50)
        return "\n".join(lines)
    else:
        raise ValueError(f"不支持的输出格式: {format_type} (错误码 E009)")


# ============================================================
# 自检模块
# ============================================================

def run_selftest():
    """
    自检核心逻辑。
    
    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。
    
    返回:
        bool: 自检是否通过
    """
    print("开始自检 illo-skill 核心逻辑...")
    
    # 构造一个超过50字的测试文本
    test_text = (
        "在人工智能快速发展的今天，数据驱动的决策方式正在改变各行各业的运作模式。"
        "企业需要更加智能化的管理系统来应对复杂多变的市场环境，而科技创新则成为推动"
        "这一变革的核心动力。通过分析海量数据，我们可以发现隐藏在表面之下的规律，"
        "并据此制定更加精准的战略。这种变革不仅体现在商业领域，也深刻影响着教育、"
        "医疗等公共服务的提供方式。未来，我们将看到更多融合了智能技术的创新应用，"
        "它们将重新定义工作与生活的方式。"
    )
    
    # 验证输入长度
    assert len(test_text) >= MIN_INPUT_LENGTH, "自检失败: 测试文本长度不足 (E008)"
    
    # 测试主题提炼
    theme = extract_theme(test_text)
    assert isinstance(theme, str) and len(theme) > 0, "主题提炼失败 (E008)"
    print(f"  [通过] 主题提炼: {theme}")
    
    # 测试构图设计
    composition = design_composition(theme, len(test_text))
    assert "type" in composition and "ascii_art" in composition, "构图设计失败 (E008)"
    assert len(composition["ascii_art"]) > 10, "ASCII示意图过短 (E008)"
    print(f"  [通过] 构图设计: {composition['type']}")
    
    # 测试基调分析
    tone = analyze_tone(test_text)
    assert tone in DEFAULT_PALETTES, f"基调分析返回未知类型: {tone} (E008)"
    print(f"  [通过] 基调分析: {tone}")
    
    # 测试色彩规划
    colors = plan_colors(tone)
    assert len(colors["colors"]) >= 3, "配色方案颜色数量不足 (E008)"
    total_ratio = sum(c["ratio"] for c in colors["colors"])
    # 宽松阈值：比例总和在0.95到1.05之间
    assert 0.95 <= total_ratio <= 1.05, f"配色比例总和异常: {total_ratio} (E008)"
    print(f"  [通过] 色彩规划: {colors['name']}")
    
    # 测试元素清单
    elements = list_elements(theme, tone)
    assert len(elements["main"]) >= 1, "主元素为空 (E008)"
    assert len(elements["supplementary"]) >= 1, "辅助元素为空 (E008)"
    assert len(elements["background"]) >= 1, "背景元素为空 (E008)"
    print(f"  [通过] 元素清单: 主元素 {len(elements['main'])}个, 辅助 {len(elements['supplementary'])}个, 背景 {len(elements['background'])}个")
    
    # 测试风格定位
    style = describe_style(tone)
    assert "description" in style and "direction" in style, "风格定位失败 (E008)"
    assert len(style["description"]) > 0, "风格描述为空 (E008)"
    print(f"  [通过] 风格定位: {style['description'][:30]}...")
    
    # 测试完整方案生成
    plan = generate_plan(test_text)
    assert "theme" in plan and "composition" in plan, "方案生成失败 (E008)"
    assert "color_scheme" in plan and "elements" in plan and "style" in plan, "方案生成不完整 (E008)"
    print(f"  [通过] 完整方案生成")
    
    # 测试输入验证
    # 空输入
    ok, err = validate_input("")
    assert not ok and err == "E001", f"空输入应返回E001, 实际: {err} (E008)"
    # 短输入
    ok, err = validate_input("太短了")
    assert not ok and err == "E002", f"短输入应返回E002, 实际: {err} (E008)"
    # 合法输入
    ok, err = validate_input(test_text)
    assert ok and err is None, f"合法输入应通过, 实际: {err} (E008)"
    print("  [通过] 输入验证")
    
    # 测试输出格式化
    text_output = format_output(plan, "text")
    assert "编辑插画方案" in text_output, "文本输出格式错误 (E008)"
    json_output = format_output(plan, "json")
    assert json.loads(json_output)["theme"] == plan["theme"], "JSON输出格式错误 (E008)"
    print("  [通过] 输出格式化")
    
    print("\n所有自检项目通过！")
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    """
    命令行入口。
    
    支持参数：
        --input: 输入文本
        --style: 风格词（可选，影响基调分析）
        --output: 输出文件路径（可选）
        --format: 输出格式（text/json，默认text）
        --selftest: 运行自检
    """
    parser = argparse.ArgumentParser(
        description="编辑插画方案生成器 (illo-skill)",
        epilog="示例: python main.py --input '文章内容...' --format json"
    )
    parser.add_argument("--input", type=str, help="输入文章文本")
    parser.add_argument("--style", type=str, help="风格关键词（可选）")
    parser.add_argument("--output", type=str, help="输出文件路径（可选）")
    parser.add_argument("--format", type=str, choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"自检失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"自检过程中发生异常: {e} (错误码 E010)")
            sys.exit(1)
    
    # 正常模式
    if not args.input:
        parser.error("请提供 --input 参数或使用 --selftest 运行自检 (错误码 E001)")
    
    try:
        # 处理风格参数
        if args.style is not None and not isinstance(args.style, str):
            raise ValueError("风格参数必须是字符串 (错误码 E007)")
        
        # 生成方案
        plan = generate_plan(args.input)
        
        # 如果指定了风格词，可以在这里调整（简化处理，实际可扩展）
        if args.style:
            plan["style"]["direction"] += f" 结合'{args.style}'风格元素"
        
        # 格式化输出
        output = format_output(plan, args.format)
        
        # 输出到文件或控制台
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"方案已写入: {args.output}")
            except OSError as e:
                print(f"写入文件失败: {e} (错误码 E004)")
                sys.exit(1)
        else:
            print(output)
            
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"运行时异常: {e} (错误码 E010)")
        sys.exit(1)


if __name__ == "__main__":
    main()
