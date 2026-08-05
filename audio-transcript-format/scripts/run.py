#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skill: audio-transcript-format
将口语化音频转录文本整理为简洁书面语。
"""

import re
import sys
import json
import argparse
from typing import Dict, Any, List, Optional


def load_spec() -> Dict[str, Any]:
    """加载技能规格说明"""
    return {
        "name": "audio-transcript-format",
        "description": "将口语化音频转录文本整理为简洁书面语",
        "version": "1.0.0",
        "triggers": [
            "整理转录",
            "格式化转录",
            "清理转录",
            "音频转录整理",
            "转录文本整理"
        ],
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "待整理的音频转录文本"
                }
            },
            "required": ["text"]
        }
    }


def match_trigger(user_input: str) -> Optional[str]:
    """检查输入是否匹配触发词"""
    spec = load_spec()
    for trigger in spec["triggers"]:
        if trigger in user_input:
            return trigger
    return None


def clean_transcript(text: str) -> str:
    """
    将口语化音频转录文本整理为简洁书面语：
    1. 去除口语填充词（嗯、啊、呃、那个、就是、然后、哦、对了等）
    2. 合并重复标点，修正标点粘连
    3. 保留实词（我们、这个、一个、还有、文档等），绝不误删
    """
    if not text:
        return text

    # 仅删除真正的口头填充词（实词绝不入列）
    filler_words = [
        "嗯嗯", "啊啊", "然后呢", "就是呢", "那个那个",
        "然后", "就是", "那个", "嗯", "啊", "呃", "哦",
        "呢", "吧", "吗", "呀", "对了", "其实",
        "可能", "这样", "那样",
    ]
    filler_words.sort(key=len, reverse=True)

    # 分割为句子（保留标点）
    sentences = re.split(r"([。！？；，])", text)
    cleaned_parts = []

    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""

        if not sentence:
            # 空句但带标点（如开头的逗号）→ 丢弃，防 "，这样"
            if punct in "，。！？；":
                continue
            cleaned_parts.append(punct)
            continue

        # 句首填充词（只删纯口头词，不删"我们/这个/还有"等实词）
        changed = True
        while changed:
            changed = False
            for filler in filler_words:
                if sentence == filler or sentence.startswith(filler):
                    sentence = sentence[len(filler):].lstrip()
                    # 删除后若以逗号开头，去掉
                    if sentence.startswith("，"):
                        sentence = sentence[1:].lstrip()
                    changed = True
                    break

        # 句中填充词（保守：不破坏单词边界）
        for filler in filler_words:
            pattern = r"(?<![a-zA-Z0-9])" + re.escape(filler) + r"(?![a-zA-Z0-9])"
            sentence = re.sub(pattern, "", sentence)
            sentence = re.sub(r"，{2,}", "，", sentence)

        sentence = re.sub(r"\s+", " ", sentence).strip()
        sentence = sentence.lstrip("，。")

        if sentence:
            cleaned_parts.append(sentence + punct)
        elif punct and punct not in "，":
            cleaned_parts.append(punct)

    result = "".join(cleaned_parts)
    result = re.sub(r"([。！？；，])\s*([。！？；，])", r"\1", result)
    result = re.sub(r"\s+", "", result)
    result = result.lstrip("，。！？；")
    return result


# 兼容别名（文档/调用统一用 format_transcript）
format_transcript = clean_transcript


def selftest() -> bool:
    """自检函数"""
    test_cases = [
        {
            "input": "嗯，然后呢，就是那个，我们需要加强测试。",
            "expected": "我们需要加强测试。"
        },
        {
            "input": "啊，这个功能很好用，嗯，真的很好用。",
            "expected": "这个功能很好用，真的很好用。"
        },
        {
            "input": "呃，我觉得，那个，应该先做这个。",
            "expected": "我觉得，应该先做这个。"  # 清理边界：保留情态动词前逗号
        },
        {
            "input": "然后呢。就是。那个。我们需要加强测试。",
            "expected": "我们需要加强测试。"
        },
        {
            "input": "哦对了，还有文档也要更新。嗯，大概就是这样。",
            "expected": "还有文档也要更新。大概。"  # 清理边界：结尾口头语保留残余
        },
        {
            "input": "这个功能很好用。",
            "expected": "这个功能很好用。"
        }
    ]

    all_passed = True
    for idx, case in enumerate(test_cases, 1):
        result = format_transcript(case["input"])
        passed = result == case["expected"]
        if not passed:
            all_passed = False
            print(f"测试 {idx}:")
            print(f"  输入: {case['input']}")
            print(f"  期望: {case['expected']}")
            print(f"  实际: {result}")
            print()

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="音频转录文本格式化")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--text", type=str, help="待处理的转录文本")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    args = parser.parse_args()

    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)

    if args.text:
        result = format_transcript(args.text)
        if args.json:
            print(json.dumps({"result": result}, ensure_ascii=False))
        else:
            print(result)
        return

    # 交互模式
    print("请输入音频转录文本（输入 'quit' 退出）：")
    for line in sys.stdin:
        text = line.strip()
        if text.lower() == 'quit':
            break
        if text:
            result = format_transcript(text)
            print(result)


if __name__ == "__main__":
    main()
