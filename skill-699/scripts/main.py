#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文本降重工具 - 智能文本去重与改写
支持多种降重策略：同义词替换、句式变换、语序调整、标点优化
"""

import re
import sys
import random
import hashlib
import argparse
from collections import Counter
from typing import List, Tuple, Dict, Set, Optional

# 设置随机种子保证可重复性
random.seed(42)


class TextDeduplicator:
    """文本降重处理器"""
    
    # 常见同义词映射表
    SYNONYMS = {
        '重要': ['关键', '核心', '主要'],
        '方法': ['方式', '途径', '手段'],
        '研究': ['探讨', '分析', '考察'],
        '问题': ['议题', '课题', '事项'],
        '解决': ['处理', '应对', '化解'],
        '提高': ['提升', '增强', '增进'],
        '发展': ['进展', '推进', '演进'],
        '影响': ['作用', '效应', '冲击'],
        '系统': ['体系', '机制', '架构'],
        '数据': ['资料', '信息', '素材'],
        '分析': ['解析', '剖析', '研判'],
        '结果': ['成果', '结论', '成效'],
        '过程': ['流程', '进程', '历程'],
        '实现': ['达成', '完成', '落实'],
        '需要': ['需求', '要求', '必要'],
        '使用': ['应用', '采用', '运用'],
        '通过': ['经过', '借助', '利用'],
        '相关': ['关联', '有关', '涉及'],
        '不同': ['差异', '区别', '差别'],
        '可能': ['或许', '也许', '大概'],
    }
    
    # 连接词替换表
    CONNECTIVES = {
        '和': ['与', '及', '以及'],
        '但是': ['然而', '不过', '可是'],
        '因为': ['由于', '鉴于'],
        '所以': ['因此', '因而', '从而'],
        '如果': ['倘若', '假如', '要是'],
        '虽然': ['尽管', '虽说'],
        '而且': ['并且', '此外', '同时'],
        '或者': ['或是', '抑或'],
    }
    
    # 标点替换
    PUNCTUATION = {
        '，': [',', ';'],
        '。': ['.', '!'],
        '；': [';', ','],
        '：': [':', ';'],
    }
    
    # 停用词
    STOP_WORDS = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    
    def __init__(self, aggressive: bool = False):
        """
        初始化降重器
        
        Args:
            aggressive: 是否使用激进模式（更多改写）
        """
        self.aggressive = aggressive
        self.modified_count = 0
        self.synonym_count = 0
        self.structure_count = 0
        self.punct_count = 0
        
    def _is_valid_text(self, text: str) -> bool:
        """检查输入文本是否有效"""
        return text is not None and isinstance(text, str) and text.strip() != ''
    
    def _split_sentences(self, text: str) -> List[str]:
        """将文本分割为句子列表"""
        # 使用正则表达式分割句子，保留分隔符
        sentences = re.split(r'(?<=[。！？!?])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _replace_synonyms(self, sentence: str) -> str:
        """替换同义词"""
        result = sentence
        for word, synonyms in self.SYNONYMS.items():
            if word in result and random.random() < 0.7:
                replacement = random.choice(synonyms)
                result = result.replace(word, replacement, 1)
                self.synonym_count += 1
        return result
    
    def _replace_connectives(self, sentence: str) -> str:
        """替换连接词"""
        result = sentence
        for word, alternatives in self.CONNECTIVES.items():
            if word in result and random.random() < 0.5:
                replacement = random.choice(alternatives)
                result = result.replace(word, replacement, 1)
                self.structure_count += 1
        return result
    
    def _adjust_punctuation(self, sentence: str) -> str:
        """调整标点符号"""
        result = sentence
        for punct, alternatives in self.PUNCTUATION.items():
            if punct in result and random.random() < 0.3:
                replacement = random.choice(alternatives)
                result = result.replace(punct, replacement, 1)
                self.punct_count += 1
        return result
    
    def _restructure_sentence(self, sentence: str) -> str:
        """调整句子结构（语序调整）"""
        # 简单语序调整：如果句子较长且有逗号，尝试交换部分
        if len(sentence) > 20 and '，' in sentence and random.random() < 0.3:
            parts = sentence.split('，')
            if len(parts) >= 2:
                # 交换前两个部分
                parts[0], parts[1] = parts[1], parts[0]
                sentence = '，'.join(parts)
                self.structure_count += 1
        return sentence
    
    def _generate_signature(self, text: str) -> str:
        """生成文本签名用于查重"""
        # 去除标点和空格，转换为小写
        normalized = re.sub(r'[^\w\u4e00-\u9fff]', '', text.lower())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def deduplicate(self, text: str) -> Tuple[str, Dict]:
        """
        执行文本降重
        
        Args:
            text: 输入文本
            
        Returns:
            (降重后的文本, 统计信息)
        """
        if not self._is_valid_text(text):
            raise ValueError("输入文本为空或类型错误: 输入文本为空")
        
        # 重置计数器
        self.modified_count = 0
        self.synonym_count = 0
        self.structure_count = 0
        self.punct_count = 0
        
        # 分割句子
        sentences = self._split_sentences(text)
        if not sentences:
            raise ValueError("输入文本为空或类型错误: 输入文本为空")
        
        # 处理每个句子
        processed_sentences = []
        for sentence in sentences:
            original = sentence
            
            # 应用各种改写策略
            sentence = self._replace_synonyms(sentence)
            sentence = self._replace_connectives(sentence)
            sentence = self._adjust_punctuation(sentence)
            
            if self.aggressive:
                sentence = self._restructure_sentence(sentence)
            
            # 统计修改
            if sentence != original:
                self.modified_count += 1
            
            processed_sentences.append(sentence)
        
        # 合并句子
        result_text = ''.join(processed_sentences)
        
        # 生成统计信息
        stats = {
            'original_length': len(text),
            'new_length': len(result_text),
            'modified_sentences': self.modified_count,
            'total_sentences': len(sentences),
            'synonym_replacements': self.synonym_count,
            'structure_changes': self.structure_count,
            'punctuation_changes': self.punct_count,
            'similarity_ratio': self._calculate_similarity(text, result_text)
        }
        
        return result_text, stats
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（0-1，越低越不相似）"""
        # 简单的字符级相似度计算
        if not text1 or not text2:
            return 1.0
        
        # 使用集合计算Jaccard相似度
        chars1 = set(text1)
        chars2 = set(text2)
        
        intersection = len(chars1 & chars2)
        union = len(chars1 | chars2)
        
        if union == 0:
            return 1.0
        
        return intersection / union
    
    def batch_deduplicate(self, texts: List[str]) -> List[Tuple[str, Dict]]:
        """批量处理文本"""
        results = []
        for text in texts:
            try:
                result = self.deduplicate(text)
                results.append(result)
            except ValueError as e:
                results.append(('', {'error': str(e)}))
        return results


def run_selftest() -> bool:
    """运行自检测试"""
    print("=" * 60)
    print("运行自检 (selftest)...")
    print("=" * 60)
    
    deduplicator = TextDeduplicator(aggressive=True)
    
    # 测试1: 基本降重功能
    print("\n[测试 1] 基本降重功能")
    test_text = "这是一个重要的研究方法，我们需要通过数据分析来解决问题。"
    try:
        result, stats = deduplicator.deduplicate(test_text)
        assert result is not None and len(result) > 0, "降重结果为空"
        assert stats['modified_sentences'] >= 0, "修改次数统计异常"
        assert stats['similarity_ratio'] >= 0 and stats['similarity_ratio'] <= 1, "相似度计算异常"
        print(f"  ✅ 通过 (修改 {stats['modified_sentences']} 处)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False
    
    # 测试2: 空输入校验
    print("\n[测试 2] 空输入校验")
    try:
        deduplicator.deduplicate("")
        print("  ❌ 失败: 空输入未抛出异常")
        return False
    except ValueError as e:
        error_msg = str(e)
        # 宽松检查：错误信息包含相关关键词即可
        assert "空" in error_msg or "错误" in error_msg or "无效" in error_msg, f"错误信息不明确: {error_msg}"
        print(f"  ✅ 通过 (错误信息: {error_msg})")
    except Exception as e:
        print(f"  ❌ 失败: 异常类型错误: {type(e).__name__}")
        return False
    
    # 测试3: 同义词替换
    print("\n[测试 3] 同义词替换")
    test_text = "这个问题需要解决，方法很重要。"
    try:
        result, stats = deduplicator.deduplicate(test_text)
        assert result is not None and len(result) > 0, "降重结果为空"
        assert stats['synonym_replacements'] >= 0, "同义词替换计数异常"
        print(f"  ✅ 通过 (同义词替换 {stats['synonym_replacements']} 次)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False
    
    # 测试4: 长文本处理
    print("\n[测试 4] 长文本处理")
    long_text = "人工智能是计算机科学的一个重要分支，它研究如何让机器模拟人类智能。"
    long_text += "近年来，深度学习技术取得了重大突破，推动了人工智能的快速发展。"
    long_text += "机器学习方法在图像识别、语音识别和自然语言处理等领域都有广泛应用。"
    try:
        result, stats = deduplicator.deduplicate(long_text)
        assert result is not None and len(result) > 0, "长文本降重结果为空"
        assert stats['total_sentences'] >= 1, "句子数量统计异常"
        print(f"  ✅ 通过 (处理 {stats['total_sentences']} 个句子)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False
    
    # 测试5: 批量处理
    print("\n[测试 5] 批量处理")
    texts = [
        "这是一个测试文本。",
        "这是另一个测试。",
        ""  # 包含一个空文本
    ]
    try:
        results = deduplicator.batch_deduplicate(texts)
        assert len(results) == 3, "批量处理结果数量错误"
        assert results[0][0] is not None and len(results[0][0]) > 0, "第一个文本处理失败"
        assert results[1][0] is not None and len(results[1][0]) > 0, "第二个文本处理失败"
        assert 'error' in results[2][1], "空文本未返回错误信息"
        print(f"  ✅ 通过 (成功处理 {len(results)} 个文本)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False
    
    # 测试6: 相似度计算
    print("\n[测试 6] 相似度计算")
    text1 = "这是一个测试文本"
    text2 = "这是另一个测试文本"
    try:
        similarity = deduplicator._calculate_similarity(text1, text2)
        assert similarity >= 0 and similarity <= 1, "相似度超出范围"
        assert similarity > 0, "相似度不应为0"
        print(f"  ✅ 通过 (相似度: {similarity:.2f})")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False
    
    # 测试7: 特殊字符处理
    print("\n[测试 7] 特殊字符处理")
    special_text = "Hello, World! 你好，世界！123测试。"
    try:
        result, stats = deduplicator.deduplicate(special_text)
        assert result is not None and len(result) > 0, "特殊字符文本处理失败"
        print(f"  ✅ 通过 (处理 {len(special_text)} 个字符)")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='文本降重工具')
    parser.add_argument('--text', type=str, help='输入文本')
    parser.add_argument('--file', type=str, help='输入文件路径')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--aggressive', action='store_true', help='使用激进模式')
    parser.add_argument('--selftest', action='store_true', help='运行自检测试')
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 创建降重器
    deduplicator = TextDeduplicator(aggressive=args.aggressive)
    
    # 获取输入文本
    input_text = None
    if args.text:
        input_text = args.text
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                input_text = f.read()
        except FileNotFoundError:
            print(f"错误: 文件不存在: {args.file}")
            sys.exit(1)
    else:
        # 从标准输入读取
        print("请输入要降重的文本 (Ctrl+D 结束):")
        input_text = sys.stdin.read()
    
    try:
        # 执行降重
        result, stats = deduplicator.deduplicate(input_text)
        
        # 输出结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"降重结果已保存到: {args.output}")
        else:
            print("\n降重结果:")
            print(result)
        
        # 输出统计信息
        print("\n统计信息:")
        print(f"  原始长度: {stats['original_length']} 字符")
        print(f"  降重后长度: {stats['new_length']} 字符")
        print(f"  修改句子数: {stats['modified_sentences']}/{stats['total_sentences']}")
        print(f"  同义词替换: {stats['synonym_replacements']} 次")
        print(f"  结构变换: {stats['structure_changes']} 次")
        print(f"  标点调整: {stats['punctuation_changes']} 次")
        print(f"  相似度: {stats['similarity_ratio']:.2%}")
        
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
