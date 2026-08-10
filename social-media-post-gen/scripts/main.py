#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 小红书种草笔记生成器（clean-room 独立实现）

依据功能规格独立编写，不参考任何既有实现。
仅使用 Python 标准库，无第三方依赖。

功能：
- 根据产品信息生成小红书风格种草笔记（标题、正文、标签、配图建议）
- 支持命令行直接调用 / 交互式输入 / 自检模式

用法示例：
    python scripts/main.py --product "保湿面霜" --scene "秋冬干燥" --audience "干皮女生" --feature "含玻尿酸"
    python scripts/main.py --selftest
"""

import argparse
import json
import random
import re
import sys
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 常量定义（错误码、合规词、模板库）
# ---------------------------------------------------------------------------

# 错误码约定：E001~E010
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入参数类型错误",
    "E003": "产品名称过长（超过50字符）",
    "E004": "正文生成失败（模板匹配异常）",
    "E005": "标签数量超出允许范围",
    "E006": "配图建议生成失败",
    "E007": "JSON 解析失败（内部数据损坏）",
    "E008": "自检断言失败",
    "E009": "命令行参数冲突",
    "E010": "未知内部错误",
}

# 合规过滤：绝对化用语 / 医疗功效 / 金融收益 关键词（命中则替换或删除）
BANNED_WORDS = [
    "根治", "彻底治愈", "百分百有效", "绝对", "最有效", "第一名",
    "包治", "药到病除", "无副作用", "永不复发", "稳赚", "保本",
    "零风险", "必涨", "翻倍收益", "神效", "奇效", "立竿见影",
]

# 情绪化口语词库（用于正文润色）
EMOTION_WORDS = ["真的", "太", "绝了", "忍不住", "疯狂", "超", "巨", "无敌", "惊艳", "上头"]

# 标题模板（按产品类型粗略分类）
TITLE_TEMPLATES = [
    "{name}测评｜{emotion}好用，{scene}必备！",
    "被问爆了！{name}也太{emotion}了吧",
    "{name}使用一个月，{scene}再也不怕了",
    "挖到宝了！{name}让我{emotion}到词穷",
    "姐妹们冲！{name}对{audience}太友好了",
    "{name}真实体验：{emotion}到想回购十次",
]

# 正文段落模板（可组合）
BODY_TEMPLATES = [
    "最近入手了{name}，{scene}环境下用了一段时间，{emotion}想分享给你们！",
    "作为一个{audience}，真的{emotion}需要这种好东西，{name}完全戳中我。",
    "先说结论：{name}的{feature}表现，让我{emotion}意外，比预期好太多。",
    "使用感受：{scene}时候拿出来用，{feature}确实有感觉，{emotion}推荐。",
    "细节方面，{name}的包装和质感都不错，{emotion}适合日常携带。",
    "如果你也是{audience}，{name}可以考虑一下，{feature}对场景很友好。",
    "当然，效果因人而异，但{name}整体给我的感觉是{emotion}值得的。",
    "最后提醒：理性种草，{name}适合特定需求，按需入手就好。",
]

# 标签前缀模板
TAG_TEMPLATES = [
    "好物分享", "种草", "{name}", "{scene}", "{audience}",
    "真实体验", "日常必备", "{feature}", "回购清单", "自用推荐",
]

# 配图建议模板
IMAGE_TEMPLATES = [
    "产品正面图（光线充足，背景简洁）",
    "使用场景图（{scene}环境实拍）",
    "质地/细节特写（突出{feature}）",
    "上手/上脸效果图（自然光）",
    "与相似产品对比图（横排）",
    "包装+配件全家福（俯拍）",
]


# ---------------------------------------------------------------------------
# 核心数据类
# ---------------------------------------------------------------------------

class ProductInfo:
    """产品信息数据类，负责校验与清洗。"""

    def __init__(self, name: str, scene: str, audience: str, feature: str):
        if not all(isinstance(x, str) for x in [name, scene, audience, feature]):
            raise ValueError(ERROR_CODES["E002"])
        if not name.strip():
            raise ValueError(ERROR_CODES["E001"])
        if len(name) > 50:
            raise ValueError(ERROR_CODES["E003"])

        self.name = name.strip()
        self.scene = scene.strip() or "日常"
        self.audience = audience.strip() or "所有人"
        self.feature = feature.strip() or "品质"

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "scene": self.scene,
            "audience": self.audience,
            "feature": self.feature,
        }


# ---------------------------------------------------------------------------
# 核心生成逻辑
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """合规过滤：将违禁词替换为安全表达。"""
    for word in BANNED_WORDS:
        text = text.replace(word, "**（已合规处理）**")
    return text


def _pick_emotion() -> str:
    """随机选择一个情绪词（保证多样性）。"""
    return random.choice(EMOTION_WORDS)


def _generate_title(info: ProductInfo) -> str:
    """根据产品信息生成标题（最多20字）。"""
    template = random.choice(TITLE_TEMPLATES)
    title = template.format(
        name=info.name,
        scene=info.scene,
        audience=info.audience,
        feature=info.feature,
        emotion=_pick_emotion(),
    )
    # 截断到20字（中文字符计数）
    title = title[:20]
    return _clean_text(title)


def _generate_body(info: ProductInfo) -> str:
    """生成正文（300-800字），由多个模板段落拼接。"""
    try:
        # 基础段落数：5~8段，每段约60~100字
        num_paragraphs = random.randint(5, 8)
        paragraphs = []
        for i in range(num_paragraphs):
            template = random.choice(BODY_TEMPLATES)
            paragraph = template.format(
                name=info.name,
                scene=info.scene,
                audience=info.audience,
                feature=info.feature,
                emotion=_pick_emotion(),
            )
            paragraphs.append(paragraph)

        # 补充过渡句，确保字数充足
        while sum(len(p) for p in paragraphs) < 300:
            extra = random.choice(BODY_TEMPLATES).format(
                name=info.name,
                scene=info.scene,
                audience=info.audience,
                feature=info.feature,
                emotion=_pick_emotion(),
            )
            paragraphs.append(extra)

        body = "\n\n".join(paragraphs)
        # 控制上限800字（截断到段落边界）
        if len(body) > 800:
            cut = 800
            while cut > 0 and body[cut] != "\n":
                cut -= 1
            body = body[:cut]

        return _clean_text(body)
    except (KeyError, IndexError) as exc:
        raise RuntimeError(ERROR_CODES["E004"]) from exc


def _generate_tags(info: ProductInfo) -> List[str]:
    """生成5-10个标签。"""
    try:
        tags = set()
        for template in TAG_TEMPLATES:
            tag = template.format(
                name=info.name,
                scene=info.scene,
                audience=info.audience,
                feature=info.feature,
            )
            # 清洗标签：去空格、限制长度
            tag = tag.strip().replace(" ", "")
            if tag and len(tag) <= 15:
                tags.add(tag)
            if len(tags) >= 10:
                break

        # 确保至少5个标签
        while len(tags) < 5:
            tags.add(f"{info.name}推荐")
            if len(tags) >= 5:
                break

        result = list(tags)[:10]
        if not 5 <= len(result) <= 10:
            raise ValueError(ERROR_CODES["E005"])
        return result
    except (KeyError, ValueError) as exc:
        raise RuntimeError(ERROR_CODES["E005"]) from exc


def _generate_image_advice(info: ProductInfo) -> List[str]:
    """生成3-6条配图建议。"""
    try:
        count = random.randint(3, 6)
        advice = []
        for i in range(count):
            template = random.choice(IMAGE_TEMPLATES)
            item = template.format(
                name=info.name,
                scene=info.scene,
                audience=info.audience,
                feature=info.feature,
            )
            advice.append(item)
        if not 3 <= len(advice) <= 6:
            raise ValueError(ERROR_CODES["E006"])
        return advice
    except (KeyError, ValueError) as exc:
        raise RuntimeError(ERROR_CODES["E006"]) from exc


def generate_post(info: ProductInfo) -> Dict[str, object]:
    """完整生成一篇种草笔记（核心入口）。"""
    try:
        post = {
            "title": _generate_title(info),
            "body": _generate_body(info),
            "tags": _generate_tags(info),
            "image_advice": _generate_image_advice(info),
        }
        # 最终完整性校验
        if not post["title"] or len(post["body"]) < 300:
            raise RuntimeError(ERROR_CODES["E004"])
        return post
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(ERROR_CODES["E010"]) from exc


def format_markdown(post: Dict[str, object]) -> str:
    """将生成结果格式化为 Markdown 文本。"""
    lines = [
        f"# {post['title']}",
        "",
        post["body"],
        "",
        "---",
        "## 标签",
        " ".join(f"#{tag}" for tag in post["tags"]),
        "",
        "## 配图建议",
    ]
    for i, advice in enumerate(post["image_advice"], 1):
        lines.append(f"{i}. {advice}")
    lines.append("")
    lines.append("> 本内容由 AI 生成，仅供学习参考，请理性种草。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，离线运行）
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """内置样例自检，返回 0 表示通过，非 0 表示失败。"""
    print("[selftest] 开始自检...")

    # 内置样例数据（硬编码，不依赖外部文件）
    samples = [
        ProductInfo(
            name="保湿面霜",
            scene="秋冬干燥",
            audience="干皮女生",
            feature="含玻尿酸",
        ),
        ProductInfo(
            name="便携榨汁杯",
            scene="办公室下午茶",
            audience="上班族",
            feature="无线充电",
        ),
        ProductInfo(
            name="护眼台灯",
            scene="学生党熬夜",
            audience="学生",
            feature="无频闪",
        ),
    ]

    try:
        for idx, info in enumerate(samples, 1):
            print(f"[selftest] 样例 {idx}: {info.name}")

            post = generate_post(info)

            # 宽松断言（区间/大小判断，不依赖精确值）
            assert post["title"], ERROR_CODES["E008"]
            assert len(post["title"]) <= 20, ERROR_CODES["E008"]

            body_len = len(post["body"])
            assert body_len >= 300, ERROR_CODES["E008"]
            assert body_len <= 800, ERROR_CODES["E008"]

            assert 5 <= len(post["tags"]) <= 10, ERROR_CODES["E008"]
            assert 3 <= len(post["image_advice"]) <= 6, ERROR_CODES["E008"]

            # 合规性检查：不应包含违禁词
            combined = post["title"] + post["body"]
            for banned in BANNED_WORDS:
                assert banned not in combined, ERROR_CODES["E008"]

            # 产品名必须出现在标题或正文中（宽松判断）
            assert info.name in post["title"] or info.name in post["body"], ERROR_CODES["E008"]

            # Markdown 格式化验证
            md = format_markdown(post)
            assert md.startswith("# "), ERROR_CODES["E008"]
            assert len(md) > 300, ERROR_CODES["E008"]

        print("[selftest] 全部样例通过 ✅")
        return 0

    except AssertionError as exc:
        print(f"[selftest] 失败: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[selftest] 异常: {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def _parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="小红书种草笔记生成器（clean-room 实现）",
        epilog="示例: python scripts/main.py --product '面霜' --scene '秋冬' --audience '干皮' --feature '保湿'",
    )
    parser.add_argument("--product", dest="product", help="产品名称（必填）")
    parser.add_argument("--scene", dest="scene", default="日常", help="使用场景")
    parser.add_argument("--audience", dest="audience", default="所有人", help="目标人群")
    parser.add_argument("--feature", dest="feature", default="品质", help="核心卖点")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--json", dest="as_json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口。"""
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    # 自检模式优先
    if args.selftest:
        # 检查是否有其他参数被设置（使用默认值判断）
        if (args.product or 
            args.scene != "日常" or 
            args.audience != "所有人" or 
            args.feature != "品质" or 
            args.as_json):
            print(f"[错误] {ERROR_CODES['E009']}: --selftest 不能与其他参数同时使用", file=sys.stderr)
            return 1
        return _run_selftest()

    # 正常生成模式
    try:
        info = ProductInfo(
            name=args.product or "",
            scene=args.scene,
            audience=args.audience,
            feature=args.feature,
        )
        post = generate_post(info)

        if args.as_json:
            print(json.dumps(post, ensure_ascii=False, indent=2))
        else:
            print(format_markdown(post))
        return 0

    except ValueError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[错误] {ERROR_CODES['E010']}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
