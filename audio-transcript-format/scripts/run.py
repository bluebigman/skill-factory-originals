#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Skill: audio-transcript-format
将口语化音频转录文本整理为结构化书面语。
支持段落划分、主题句提取、列表化等结构化能力。
"""

import re
import sys
import json
import argparse
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple


def load_spec() -> Dict[str, Any]:
    """加载技能规格说明"""
    return {
        "name": "audio-transcript-format",
        "description": "将口语化音频转录文本整理为结构化书面语，支持段落划分、主题句提取、列表化",
        "version": "2.0.0",
        "triggers": [
            "整理转录",
            "格式化转录",
            "清理转录",
            "音频转录整理",
            "转录文本整理",
            "结构化转录"
        ],
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "待整理的音频转录文本"
                },
                "terms": {
                    "type": "object",
                    "description": "术语规范化映射表，如 {'tensorflow': 'TensorFlow'}",
                    "default": {}
                },
                "add_headings": {
                    "type": "boolean",
                    "description": "是否自动添加小标题",
                    "default": False
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


def clean_transcript(text: str, terms: Optional[Dict[str, str]] = None) -> str:
    """
    将口语化音频转录文本整理为结构化书面语：
    1. 去除口语填充词（仅删除纯口头词，保留实词）
    2. 合并重复标点，修正标点粘连
    3. 段落划分：按语义主题分组
    4. 主题句提取：识别每段核心句
    5. 列表化：识别并列项并转为列表
    """
    if not text or not text.strip():
        return text

    terms = terms or {}

    # 1. 去除口语填充词（仅删除纯口头词，实词绝不入列）
    filler_words = [
        "嗯嗯", "啊啊", "然后呢", "就是呢", "那个那个",
        "然后", "就是", "那个", "嗯", "啊", "呃", "哦",
        "呢", "吧", "吗", "呀", "对了", "其实"
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
        for filler in filler_words:
            if sentence.startswith(filler):
                sentence = sentence[len(filler):].strip()
                break

        # 句尾填充词（只删纯口头词）
        for filler in filler_words:
            if sentence.endswith(filler):
                sentence = sentence[:-len(filler)].strip()
                break

        # 删除句子中间的填充词（只删纯口头词）
        for filler in filler_words:
            # 使用正则确保只删除独立的填充词，不删除实词中的子串
            pattern = r'(?<![a-zA-Z0-9\u4e00-\u9fff])' + re.escape(filler) + r'(?![a-zA-Z0-9\u4e00-\u9fff])'
            sentence = re.sub(pattern, '', sentence)

        # 清理多余空格
        sentence = re.sub(r'\s+', ' ', sentence).strip()

        if sentence:
            cleaned_parts.append(sentence + punct)
        elif punct and punct not in "，。！？；":
            cleaned_parts.append(punct)

    # 2. 合并重复标点，修正标点粘连
    text = ''.join(cleaned_parts)
    text = re.sub(r'([。！？；，])\1+', r'\1', text)  # 合并重复标点
    text = re.sub(r'\s+([。！？；，])', r'\1', text)  # 标点前不留空格
    text = re.sub(r'([。！？；，])(?=[a-zA-Z0-9\u4e00-\u9fff])', r'\1 ', text)  # 标点后加空格

    # 3. 术语规范化
    for old, new in terms.items():
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)

    # 4. 段落划分（按语义主题分组）
    paragraphs = split_paragraphs(text)

    # 5. 列表化（识别并列项）
    paragraphs = convert_to_lists(paragraphs)

    return '\n\n'.join(paragraphs)


def split_paragraphs(text: str) -> List[str]:
    """按语义主题将文本划分为逻辑段落"""
    if not text:
        return []

    # 按句号、问号、感叹号分割为句子
    sentences = re.split(r'(?<=[。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 3:
        return [text]

    paragraphs = []
    current_para = []
    current_topic = None

    for sentence in sentences:
        # 提取句子关键词作为主题判断
        keywords = extract_keywords(sentence)

        if current_topic is None:
            current_topic = keywords
            current_para.append(sentence)
        elif keywords and set(keywords) & set(current_topic):
            # 与当前主题相关，加入当前段落
            current_para.append(sentence)
        else:
            # 主题变化，开始新段落
            if current_para:
                paragraphs.append(''.join(current_para))
            current_para = [sentence]
            current_topic = keywords

    if current_para:
        paragraphs.append(''.join(current_para))

    return paragraphs


def extract_keywords(sentence: str) -> List[str]:
    """提取句子关键词（简单实现：提取名词性词汇）"""
    # 简单实现：提取长度>=2的中文词或英文单词
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', sentence)
    return [w.lower() for w in words[:5]]


def convert_to_lists(paragraphs: List[str]) -> List[str]:
    """识别并列项并转为列表格式"""
    result = []
    for para in paragraphs:
        # 识别"第一...第二...第三..."或"首先...其次...最后..."模式
        items = re.split(r'(?:第一|第二|第三|第四|第五|首先|其次|再次|最后)[，,、]?', para)
        if len(items) > 2:
            # 有多个并列项，转为列表
            items = [item.strip() for item in items if item.strip()]
            if len(items) >= 2:
                list_items = []
                for idx, item in enumerate(items, 1):
                    list_items.append(f"{idx}. {item}")
                result.append('\n'.join(list_items))
                continue

        # 识别"1. ... 2. ... 3. ..."模式
        numbered_items = re.findall(r'(?:^|\n)\s*(\d+)[.、]\s*(.+)', para)
        if len(numbered_items) >= 2:
            list_items = [f"{num}. {content.strip()}" for num, content in numbered_items]
            result.append('\n'.join(list_items))
            continue

        result.append(para)

    return result


def add_headings(paragraphs: List[str]) -> List[str]:
    """为段落添加小标题（基于主题句提取）"""
    result = []
    for idx, para in enumerate(paragraphs, 1):
        # 提取主题句（段首句）
        first_sentence = para.split('。')[0] if '。' in para else para[:30]
        # 生成小标题
        heading = f"### 段落 {idx}: {first_sentence[:20]}..."
        result.append(f"{heading}\n\n{para}")
    return result


def process_transcript(text: str, terms: Optional[Dict[str, str]] = None,
                       add_headings_flag: bool = False) -> Dict[str, Any]:
    """
    处理转录文本的主流程
    """
    start_time = datetime.now(timezone.utc)

    # 输入验证
    if not text or not text.strip():
        return {
            "success": False,
            "error_code": 1,
            "error_message": "输入文本为空",
            "output": "",
            "stats": {
                "input_chars": 0,
                "output_chars": 0,
                "processing_time_ms": 0
            }
        }

    # 长度检查
    if len(text) > 10000:
        return {
            "success": False,
            "error_code": 2,
            "error_message": "输入文本过长（>10000字符），请分段处理",
            "output": "",
            "stats": {
                "input_chars": len(text),
                "output_chars": 0,
                "processing_time_ms": 0
            }
        }

    # 清洗处理
    cleaned = clean_transcript(text, terms)

    # 段落划分
    paragraphs = split_paragraphs(cleaned)

    # 列表化
    paragraphs = convert_to_lists(paragraphs)

    # 添加小标题（可选）
    if add_headings_flag:
        paragraphs = add_headings(paragraphs)

    output = '\n\n'.join(paragraphs)

    end_time = datetime.now(timezone.utc)
    processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

    return {
        "success": True,
        "error_code": 0,
        "error_message": "",
        "output": output,
        "stats": {
            "input_chars": len(text),
            "output_chars": len(output),
            "processing_time_ms": processing_time_ms
        }
    }


def atomic_write_file(filepath: str, content: str) -> bool:
    """原子化写入文件"""
    try:
        dirname = os.path.dirname(filepath) or '.'
        os.makedirs(dirname, exist_ok=True)

        # 写入临时文件
        fd, temp_path = tempfile.mkstemp(dir=dirname, prefix='.tmp_', suffix='.md')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            # 原子替换
            os.replace(temp_path, filepath)
        except Exception:
            os.unlink(temp_path)
            raise
        return True
    except Exception as e:
        print(f"写入文件失败: {e}", file=sys.stderr)
        return False


def run_selftest() -> int:
    """自测函数：真实调用主流程并断言关键输出"""
    print("运行自测...")

    # 测试用例1：基本清洗
    test_text1 = "嗯，那个，我们其实已经完成了这个项目。然后呢，就是，呃，下一步我们要做什么？"
    result1 = process_transcript(test_text1)
    assert result1["success"] is True, f"测试1失败: {result1}"
    assert "嗯" not in result1["output"], f"测试1失败: 填充词未删除"
    assert "那个" not in result1["output"], f"测试1失败: 填充词未删除"
    assert "我们其实已经完成了这个项目" in result1["output"], f"测试1失败: 核心内容丢失"
    print("测试1通过: 基本清洗")

    # 测试用例2：术语规范化
    test_text2 = "我们使用tensorflow进行训练，TensorFlow是一个很好的框架。"
    result2 = process_transcript(test_text2, terms={"tensorflow": "TensorFlow"})
    assert result2["success"] is True, f"测试2失败: {result2}"
    assert result2["output"].count("TensorFlow") == 2, f"测试2失败: 术语未统一"
    print("测试2通过: 术语规范化")

    # 测试用例3：列表化
    test_text3 = "首先我们需要准备数据，其次我们要训练模型，最后我们要评估结果。"
    result3 = process_transcript(test_text3)
    assert result3["success"] is True, f"测试3失败: {result3}"
    assert "1." in result3["output"], f"测试3失败: 未生成列表"
    assert "2." in result3["output"], f"测试3失败: 未生成列表"
    print("测试3通过: 列表化")

    # 测试用例4：空输入
    result4 = process_transcript("")
    assert result4["success"] is False, f"测试4失败: 空输入应该失败"
    assert result4["error_code"] == 1, f"测试4失败: 错误码不正确"
    print("测试4通过: 空输入处理")

    # 测试用例5：长文本
    test_text5 = "这是一个测试。" * 2000  # 约12000字符
    result5 = process_transcript(test_text5)
    assert result5["success"] is False, f"测试5失败: 长文本应该失败"
    assert result5["error_code"] == 2, f"测试5失败: 错误码不正确"
    print("测试5通过: 长文本处理")

    # 测试用例6：标点修复
    test_text6 = "你好。。。这是一个测试！！真的吗？？"
    result6 = process_transcript(test_text6)
    assert result6["success"] is True, f"测试6失败: {result6}"
    assert "。。。" not in result6["output"], f"测试6失败: 重复标点未合并"
    assert "！！" not in result6["output"], f"测试6失败: 重复标点未合并"
    print("测试6通过: 标点修复")

    print("\n所有自测通过!")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="音频转写文本格式化整理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --text "嗯，那个，我们完成了项目。"
  python run.py --file input.txt --output output.md
  python run.py --selftest
        """
    )
    parser.add_argument("--text", type=str, help="待处理的转录文本")
    parser.add_argument("--file", type=str, help="输入文件路径（UTF-8编码）")
    parser.add_argument("--output", type=str, help="输出文件路径（可选）")
    parser.add_argument("--terms", type=str, help="术语映射JSON文件路径（可选）")
    parser.add_argument("--add-headings", action="store_true", help="自动添加小标题")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--version", action="version", version="audio-transcript-format 2.0.0")

    args = parser.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    # 获取输入文本
    text = args.text
    if not text and args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"读取文件失败: {e}", file=sys.stderr)
            sys.exit(1)

    if not text:
        # 尝试从标准输入读取
        try:
            text = sys.stdin.read()
        except KeyboardInterrupt:
            print("用户中断输入", file=sys.stderr)
            sys.exit(1)

    if not text or not text.strip():
        print("错误: 输入文本为空", file=sys.stderr)
        sys.exit(1)

    # 加载术语映射
    terms = {}
    if args.terms:
        try:
            with open(args.terms, 'r', encoding='utf-8') as f:
                terms = json.load(f)
        except Exception as e:
            print(f"加载术语映射失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 处理文本
    result = process_transcript(text, terms=terms, add_headings_flag=args.add_headings)

    if not result["success"]:
        print(f"错误: {result['error_message']}", file=sys.stderr)
        sys.exit(result["error_code"])

    # 输出结果
    output = result["output"]
    if args.output:
        if atomic_write_file(args.output, output):
            print(f"结果已写入: {args.output}")
        else:
            print("写入文件失败", file=sys.stderr)
            sys.exit(4)
    else:
        print(output)

    # 输出统计信息（到stderr，不影响stdout）
    stats = result["stats"]
    print(f"\n[统计] 输入: {stats['input_chars']}字符, 输出: {stats['output_chars']}字符, "
          f"耗时: {stats['processing_time_ms']}ms", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
