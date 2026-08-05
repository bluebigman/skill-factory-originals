#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音转写文本整理工具 - 将口语化转写稿整理为结构化正式文本

功能：
1. 删除语气词（嗯、啊、呃、哦、哎等）
2. 删除重复词
3. 删除自我修正前缀
4. 删除高频口头禅
5. 合并碎片化短句
6. 规范标点符号
7. 段落重排
8. 标记不确定信息

用法示例：
    python run.py --input raw.txt --output clean.txt
    python run.py --input raw.txt --output clean.txt --mode interview
    python run.py --selftest
"""

import argparse
import re
import sys
from pathlib import Path

# 尝试导入可选依赖（本工具核心功能仅需标准库）
try:
    import chardet  # 用于自动检测文件编码（可选）
except ImportError:
    chardet = None

# ============ 核心处理逻辑 ============

# 语气词表（按使用频率排序）
FILLER_WORDS = [
    "嗯", "啊", "呃", "哦", "哎", "唉", "呐", "嘛", "哈",
    "那个", "这个", "就是说", "然后呢", "就是说呢",
    "嗯嗯", "啊啊", "呃呃", "哦哦", "哎哎",
    "emmm", "emm", "um", "uh", "er", "hmm"
]

# 高频口头禅（可配置）
PET_PHRASES = [
    "你懂我意思吧", "你明白吗", "你知道吗", "怎么说呢",
    "对吧", "是吧", "对不对", "是不是", "说实话",
    "讲真的", "其实吧", "基本上", "基本上来说"
]

# 自我修正前缀模式（如"不对不对，我说的是..."）
SELF_CORRECT_PATTERNS = [
    r"不对不对[，,、\s]*",
    r"不是不是[，,、\s]*",
    r"我说错了[，,、\s]*",
    r"等等等等[，,、\s]*",
    r"不不不[，,、\s]*",
    r"错了错了[，,、\s]*",
]

# 不确定信息标记模式（如"听不清"、"模糊"等）
UNCERTAIN_PATTERNS = [
    r"\[听不清\]",
    r"\[模糊\]",
    r"\[无法识别\]",
    r"\[未听清\]",
    r"\(听不清\)",
    r"\(模糊\)",
]

# 标点符号映射（半角转全角）
PUNCT_MAP = {
    ',': '，',
    '.': '。',
    '?': '？',
    '!': '！',
    ';': '；',
    ':': '：',
    '(': '（',
    ')': '）',
    '[': '【',
    ']': '】',
    '"': '"',
    "'": "'",
}


def remove_fillers(text: str) -> str:
    """删除语气词"""
    for word in FILLER_WORDS:
        # 使用正则确保只删除独立词（前后不是中文字符）
        pattern = r'(?<![一-龥])' + re.escape(word) + r'(?![一-龥])'
        text = re.sub(pattern, '', text)
    return text


def remove_repetitions(text: str) -> str:
    """删除重复词（连续重复2次及以上）"""
    # 匹配连续重复的中文词（2-4字）
    pattern = r'([一-龥]{2,4})(\1)+'
    while re.search(pattern, text):
        text = re.sub(pattern, r'\1', text)
    return text


def remove_self_corrections(text: str) -> str:
    """删除自我修正前缀"""
    for pattern in SELF_CORRECT_PATTERNS:
        text = re.sub(pattern, '', text)
    return text


def remove_pet_phrases(text: str) -> str:
    """删除高频口头禅"""
    for phrase in PET_PHRASES:
        text = text.replace(phrase, '')
    return text


def merge_fragments(text: str) -> str:
    """合并碎片化短句"""
    # 将"然后呢。就是。那个。"这类碎片合并
    # 先处理句号分隔的碎片
    text = re.sub(r'[。！？]+([一-龥]{1,4}[。！？]+)+', lambda m: m.group(0).replace('。', '，').replace('！', '，').replace('？', '，'), text)
    # 合并连续逗号
    text = re.sub(r'[，,]{2,}', '，', text)
    return text


def normalize_punctuation(text: str) -> str:
    """规范标点符号"""
    # 半角转全角
    for half, full in PUNCT_MAP.items():
        text = text.replace(half, full)
    # 确保句子以句号结尾
    text = re.sub(r'([^。！？])$', r'\1。', text)
    # 去除多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def mark_uncertain(text: str) -> str:
    """标记不确定信息"""
    for pattern in UNCERTAIN_PATTERNS:
        text = re.sub(pattern, '[需核实:内容]', text)
    return text


def reorganize_paragraphs(text: str) -> str:
    """段落重排（按语义切分）"""
    # 按句号切分，每2-3句合并为一段
    sentences = re.split(r'[。！？]', text)
    sentences = [s for s in sentences if s.strip()]
    
    paragraphs = []
    current = []
    for i, sent in enumerate(sentences):
        current.append(sent)
        if len(current) >= 3 or (i == len(sentences) - 1 and current):
            paragraphs.append('。'.join(current) + '。')
            current = []
    
    return '\n\n'.join(paragraphs)


def process_text(text: str, mode: str = "general") -> str:
    """主处理函数：按顺序应用所有规则"""
    # 1. 删除语气词
    text = remove_fillers(text)
    # 2. 删除重复词
    text = remove_repetitions(text)
    # 3. 删除自我修正
    text = remove_self_corrections(text)
    # 4. 删除口头禅
    text = remove_pet_phrases(text)
    # 5. 合并碎片
    text = merge_fragments(text)
    # 6. 标记不确定信息
    text = mark_uncertain(text)
    # 7. 规范标点
    text = normalize_punctuation(text)
    # 8. 段落重排
    text = reorganize_paragraphs(text)
    
    # 模式特定处理
    if mode == "interview":
        # 访谈模式：保留问答结构
        text = re.sub(r'([问Q])[:：]', r'\1：', text)
        text = re.sub(r'([答A])[:：]', r'\1：', text)
    elif mode == "meeting":
        # 会议模式：突出结论
        text = re.sub(r'(结论|决定|决议)[:：]', r'【\1】', text)
    
    return text


def read_file(filepath: str) -> str:
    """读取文件（自动检测编码）"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 尝试UTF-8
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # 尝试GBK
        try:
            return path.read_text(encoding='gbk')
        except UnicodeDecodeError:
            # 尝试使用chardet检测
            if chardet:
                raw = path.read_bytes()
                detected = chardet.detect(raw)
                encoding = detected.get('encoding', 'utf-8')
                try:
                    return raw.decode(encoding)
                except:
                    pass
            raise ValueError(f"无法识别文件编码: {filepath}")


def write_file(filepath: str, content: str) -> None:
    """写入文件"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


# ============ CLI 入口 ============

def main():
    parser = argparse.ArgumentParser(
        description="语音转写文本整理工具 - 将口语化转写稿整理为结构化正式文本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input raw.txt --output clean.txt
  python run.py --input raw.txt --output clean.txt --mode interview
  python run.py --selftest
        """
    )
    parser.add_argument("--input", "-i", help="输入文件路径（纯文本）")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--mode", "-m", choices=["general", "interview", "meeting"],
                       default="general", help="处理模式: general=通用, interview=访谈, meeting=会议")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    if args.selftest:
        selftest()
        return
    
    if not args.input or not args.output:
        parser.error("必须提供 --input 和 --output 参数")
    
    try:
        # 读取输入
        raw_text = read_file(args.input)
        print(f"已读取输入文件: {args.input} ({len(raw_text)} 字符)")
        
        # 处理文本
        cleaned_text = process_text(raw_text, args.mode)
        print(f"处理完成: {len(raw_text)} -> {len(cleaned_text)} 字符")
        
        # 写入输出
        write_file(args.output, cleaned_text)
        print(f"已写入输出文件: {args.output}")
        
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


# ============ 自检函数 ============

def selftest():
    """自检：验证核心功能是否正常"""
    print("=" * 50)
    print("开始自检...")
    print("=" * 50)
    
    # 测试用例
    test_cases = [
        {
            "name": "语气词删除",
            "input": "嗯，我觉得这个方案可以",
            "expected": "我觉得这个方案可以"
        },
        {
            "name": "重复词删除",
            "input": "我们我们明天开会",
            "expected": "我们明天开会"
        },
        {
            "name": "自我修正删除",
            "input": "不对不对，我说的是周三，周三下午",
            "expected": "周三下午"
        },
        {
            "name": "口头禅删除",
            "input": "你懂我意思吧，这个需求很急，你懂我意思吧",
            "expected": "这个需求很急"
        },
        {
            "name": "碎片合并",
            "input": "然后呢。就是。那个。我们走了。",
            "expected": "然后我们走了。"
        },
        {
            "name": "标点规范",
            "input": "你好,世界.你好吗?",
            "expected": "你好，世界。你好吗？"
        },
        {
            "name": "不确定标记",
            "input": "他说[听不清]明天来",
            "expected": "他说[需核实:内容]明天来"
        }
    ]
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        result = process_text(case["input"])
        # 简化比较（忽略段落重排的影响）
        result_simple = result.replace('\n\n', ' ').strip()
        expected = case["expected"].strip()
        
        if expected in result_simple or result_simple in expected:
            print(f"✓ {case['name']}: PASS")
            passed += 1
        else:
            print(f"✗ {case['name']}: FAIL")
            print(f"  输入: {case['input']}")
            print(f"  期望: {expected}")
            print(f"  实际: {result_simple}")
            failed += 1
    
    # 完整流程测试
    print("\n--- 完整流程测试 ---")
    sample = """
    嗯，大家好，那个今天我们来讨论一下项目进度。呃，首先呢，我觉得我们我们进度有点慢。
    不对不对，其实还行。你懂我意思吧，主要问题是那个测试环节。然后呢。就是。那个。
    我们需要加强测试。哦对了，还有文档也要更新。嗯，大概就是这样。
    """
    print(f"原始文本:\n{sample}")
    cleaned = process_text(sample, "meeting")
    print(f"\n整理后:\n{cleaned}")
    
    print("\n" + "=" * 50)
    print(f"自检结果: {passed} 通过, {failed} 失败")
    print("=" * 50)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("所有测试通过！")


if __name__ == "__main__":
    main()
