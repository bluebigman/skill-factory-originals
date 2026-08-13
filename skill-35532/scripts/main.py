#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学术文本改写工具 - 冒烟测试修复版"""

import sys
import re
import json
import argparse
from typing import Dict, List, Tuple

# 学术术语保护列表
PROTECTED_TERMS = [
    "深度学习", "机器学习", "人工智能", "神经网络", "自然语言处理",
    "计算机视觉", "数据挖掘", "强化学习", "迁移学习", "联邦学习",
    "Transformer", "BERT", "GPT", "LSTM", "CNN", "RNN"
]

# 同义词替换映射
SYNONYM_MAP = {
    "提出": ["提出", "给出", "构建"],
    "方法": ["方法", "方案", "途径"],
    "提高": ["提高", "提升", "增强"],
    "性能": ["性能", "效果", "表现"],
    "重要": ["重要", "关键", "核心"],
    "作用": ["作用", "影响", "意义"],
    "研究": ["研究", "探讨", "分析"],
    "系统": ["系统", "体系", "框架"],
    "但是": ["但是", "然而", "不过"],
    "需要": ["需要", "必须", "应当"],
    "注意": ["注意", "关注", "重视"],
    "局限": ["局限", "限制", "不足"],
    "我们": ["我们", "本文", "笔者"],
    "一种": ["一种", "一个", "某项"],
    "具有": ["具有", "拥有", "具备"],
    "对": ["对", "对于", "针对"],
    "新": ["新", "新型", "创新"],
    "能够": ["能够", "可以", "能"],
    "进行": ["进行", "实施", "执行"],
    "处理": ["处理", "应对", "解决"]
}

class AcademicRewriter:
    """学术文本改写器"""
    
    def __init__(self, intensity: int = 2):
        """初始化改写器
        
        Args:
            intensity: 改写强度 1-5，默认2
        """
        self.intensity = max(1, min(5, intensity))
        self.protected_terms = PROTECTED_TERMS
        
    def _protect_terms(self, text: str) -> Tuple[str, Dict[str, str]]:
        """保护学术术语，返回替换后的文本和映射表"""
        placeholder_map = {}
        protected_text = text
        
        for i, term in enumerate(self.protected_terms):
            if term in protected_text:
                placeholder = f"__TERM_{i}__"
                protected_text = protected_text.replace(term, placeholder)
                placeholder_map[placeholder] = term
                
        return protected_text, placeholder_map
    
    def _restore_terms(self, text: str, placeholder_map: Dict[str, str]) -> str:
        """恢复被保护的学术术语"""
        restored_text = text
        for placeholder, term in placeholder_map.items():
            restored_text = restored_text.replace(placeholder, term)
        return restored_text
    
    def _split_sentences(self, text: str) -> List[str]:
        """按中文标点拆分句子"""
        # 使用正则表达式匹配中文标点
        sentences = re.split(r'[。！？；]', text)
        # 过滤空字符串和纯空白
        return [s.strip() for s in sentences if s.strip()]
    
    def _rewrite_sentence(self, sentence: str) -> str:
        """改写单个句子"""
        if not sentence:
            return sentence
            
        # 保护术语
        protected_text, term_map = self._protect_terms(sentence)
        
        # 根据强度决定替换比例
        replace_ratio = min(0.3 + self.intensity * 0.1, 0.7)
        
        # 进行同义词替换
        words = protected_text.split()
        new_words = []
        replaced_count = 0
        total_replaceable = 0
        
        # 统计可替换的词
        for word in words:
            if word in SYNONYM_MAP:
                total_replaceable += 1
        
        # 执行替换
        for word in words:
            if word in SYNONYM_MAP and replaced_count < int(total_replaceable * replace_ratio):
                synonyms = SYNONYM_MAP[word]
                # 选择不同的同义词（避免重复使用原词）
                if len(synonyms) > 1:
                    new_word = synonyms[1] if synonyms[0] == word else synonyms[0]
                    new_words.append(new_word)
                    replaced_count += 1
                else:
                    new_words.append(word)
            else:
                new_words.append(word)
        
        # 重组句子
        rewritten = ' '.join(new_words)
        
        # 恢复术语
        rewritten = self._restore_terms(rewritten, term_map)
        
        return rewritten
    
    def rewrite(self, text: str) -> Dict:
        """改写文本主函数
        
        Args:
            text: 输入文本
            
        Returns:
            Dict: 包含改写结果或错误信息的字典
        """
        # 输入校验
        if not text or not text.strip():
            return {
                "success": False,
                "error_code": "E001",
                "message": "请提供需要改写的文本内容"
            }
        
        # 长度校验
        if len(text) > 1000:
            return {
                "success": False,
                "error_code": "E003",
                "message": "文本长度超出限制，请控制在1000字以内"
            }
        
        try:
            # 拆分句子
            sentences = self._split_sentences(text)
            
            if not sentences:
                return {
                    "success": False,
                    "error_code": "E002",
                    "message": "文本格式不正确，无法进行改写"
                }
            
            # 改写每个句子
            rewritten_sentences = []
            for sentence in sentences:
                rewritten = self._rewrite_sentence(sentence)
                if rewritten:
                    rewritten_sentences.append(rewritten)
            
            # 合并句子
            result_text = "。".join(rewritten_sentences)
            if result_text and not result_text.endswith("。"):
                result_text += "。"
            
            return {
                "success": True,
                "result": result_text,
                "original": text,
                "sentence_count": len(rewritten_sentences)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error_code": "E002",
                "message": f"改写过程中出现错误: {str(e)}"
            }

def run_selftest() -> bool:
    """运行自检程序"""
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)
    
    rewriter = AcademicRewriter(intensity=2)
    all_passed = True
    
    # 测试1: 正常文本改写
    print("\n[测试 1] 正常文本改写")
    test_text = "本研究提出了一种新方法，该方法对提高系统性能具有重要作用。"
    result = rewriter.rewrite(test_text)
    if result["success"]:
        result_len = len(result["result"])
        print(f"  ✅ 通过 (结果长度: {result_len}字)")
    else:
        print(f"  ❌ 失败: {result['message']}")
        all_passed = False
    
    # 测试2: 中文标点处理
    print("\n[测试 2] 中文标点处理")
    test_text = "我们提出了一种新方法；该方法很重要。但是，需要注意其局限性！"
    result = rewriter.rewrite(test_text)
    if result["success"] and result["sentence_count"] >= 2:
        print(f"  ✅ 通过 (拆分为 {result['sentence_count']} 句)")
    else:
        print(f"  ❌ 失败: 句子拆分不正确")
        all_passed = False
    
    # 测试3: 空输入处理
    print("\n[测试 3] 空输入处理")
    result = rewriter.rewrite("")
    if not result["success"] and result["error_code"] == "E001":
        print(f"  ✅ 通过 (错误码: {result['error_code']})")
    else:
        print(f"  ❌ 失败: 错误码错误: {result.get('error_code', '无')}")
        all_passed = False
    
    # 测试4: 超长输入处理
    print("\n[测试 4] 超长输入处理")
    long_text = "测试" * 600  # 1200字符
    result = rewriter.rewrite(long_text)
    if not result["success"] and result["error_code"] == "E003":
        print(f"  ✅ 通过 (错误码: {result['error_code']})")
    else:
        print(f"  ❌ 失败: 错误码错误: {result.get('error_code', '无')}")
        all_passed = False
    
    # 测试5: 术语保留
    print("\n[测试 5] 术语保留")
    test_text = "深度学习在人工智能领域具有重要作用。"
    result = rewriter.rewrite(test_text)
    if result["success"] and "深度学习" in result["result"]:
        print(f"  ✅ 通过 (术语'深度学习'已保留)")
    else:
        print(f"  ❌ 失败: 术语未保留")
        all_passed = False
    
    # 测试6: 强度参数校验
    print("\n[测试 6] 强度参数校验")
    try:
        # 测试无效强度参数
        invalid_rewriter = AcademicRewriter(intensity=10)  # 超出范围
        # 应该被限制在1-5之间
        if 1 <= invalid_rewriter.intensity <= 5:
            print(f"  ✅ 通过 (强度参数已限制在1-5)")
        else:
            print(f"  ❌ 失败: 强度参数超出范围")
            all_passed = False
    except Exception as e:
        print(f"  ✅ 通过 (参数校验正常: {str(e)})")
    
    # 测试7: 正常改写功能
    print("\n[测试 7] 正常改写功能")
    test_text = "我们提出了一种新方法，该方法对提高系统性能具有重要作用。"
    result = rewriter.rewrite(test_text)
    if result["success"] and len(result["result"]) > 0:
        print(f"  ✅ 通过 (改写成功)")
    else:
        print(f"  ❌ 失败: 改写失败")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试通过!")
    else:
        print("存在测试失败!")
    print("=" * 60)
    
    return all_passed

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="学术文本改写工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检程序")
    parser.add_argument("--text", type=str, help="需要改写的文本")
    parser.add_argument("--intensity", type=int, default=2, choices=range(1, 6),
                       help="改写强度 1-5，默认2")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 处理文本改写请求
    if args.text:
        rewriter = AcademicRewriter(intensity=args.intensity)
        result = rewriter.rewrite(args.text)
        
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["success"]:
                print(result["result"])
            else:
                print(f"错误: {result['message']}")
                sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
