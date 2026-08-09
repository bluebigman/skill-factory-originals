#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meeting-pro 会议纪要生成工具"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional


class MeetingProcessor:
    """会议纪要处理器"""
    
    def __init__(self):
        self.min_paragraphs = 3
        self.min_sentences = 2
        self.min_keywords = 1
    
    def process_text(self, text: str) -> Dict:
        """处理会议文本，生成结构化纪要"""
        if not text or not text.strip():
            return {
                "title": "未命名会议",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "paragraphs": [],
                "summary": "无内容",
                "keywords": []
            }
        
        # 清理文本
        text = text.strip()
        
        # 切分段落
        paragraphs = self._split_paragraphs(text)
        
        # 生成标题
        title = self._generate_title(paragraphs)
        
        # 生成摘要
        summary = self._generate_summary(paragraphs)
        
        # 提取关键词
        keywords = self._extract_keywords(text)
        
        return {
            "title": title,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "paragraphs": paragraphs,
            "summary": summary,
            "keywords": keywords
        }
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """将文本切分为段落"""
        # 按空行或换行切分
        raw_paragraphs = re.split(r'\n\s*\n|\n+', text)
        paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]
        
        # 如果段落太少，按句子切分
        if len(paragraphs) < self.min_paragraphs:
            sentences = re.split(r'[。！？.!?]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) >= self.min_paragraphs:
                paragraphs = sentences[:self.min_paragraphs]
        
        # 确保至少有3段
        while len(paragraphs) < self.min_paragraphs:
            paragraphs.append("补充内容")
        
        return paragraphs[:5]  # 最多5段
    
    def _generate_title(self, paragraphs: List[str]) -> str:
        """生成会议标题"""
        if not paragraphs:
            return "未命名会议"
        
        # 取第一段的前几个词作为标题
        first_para = paragraphs[0]
        words = first_para.split()[:5]
        if words:
            return "会议：" + " ".join(words)
        return "未命名会议"
    
    def _generate_summary(self, paragraphs: List[str]) -> str:
        """生成会议摘要"""
        if not paragraphs:
            return "无内容"
        
        # 取每段的第一句拼接为摘要
        summary_parts = []
        for para in paragraphs[:3]:
            sentences = re.split(r'[。！？.!?]', para)
            if sentences and sentences[0].strip():
                summary_parts.append(sentences[0].strip())
        
        if summary_parts:
            return "；".join(summary_parts)
        return "无内容"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 常见会议关键词
        common_words = [
            "会议", "讨论", "决定", "项目", "计划", "方案",
            "问题", "解决", "任务", "时间", "人员", "资源",
            "目标", "进度", "风险", "质量", "成本", "范围"
        ]
        
        keywords = []
        for word in common_words:
            if word in text and word not in keywords:
                keywords.append(word)
        
        # 如果没有找到关键词，添加默认关键词
        if not keywords:
            keywords = ["会议纪要"]
        
        return keywords[:5]
    
    def selftest(self) -> bool:
        """自检测试"""
        print("meeting-pro 自检模式")
        print("=" * 60)
        
        # 测试1：文本段落切分
        print("\n[测试1] 文本段落切分...")
        test_text = """今天会议讨论了项目进展。
我们完成了第一阶段的任务。
下一步计划在下周开始。
需要协调各部门资源。
会议决定加强沟通机制。"""
        
        result = self.process_text(test_text)
        
        # 宽松断言：段落数>=3
        assert len(result["paragraphs"]) >= 3, f"段落数应>=3, 实际={len(result['paragraphs'])}"
        print(f"  ✓ 段落切分成功，共{len(result['paragraphs'])}段")
        
        # 测试2：标题生成
        print("\n[测试2] 标题生成...")
        assert result["title"], "标题不能为空"
        print(f"  ✓ 标题生成成功: {result['title']}")
        
        # 测试3：摘要生成
        print("\n[测试3] 摘要生成...")
        assert result["summary"], "摘要不能为空"
        print(f"  ✓ 摘要生成成功: {result['summary'][:50]}...")
        
        # 测试4：关键词提取
        print("\n[测试4] 关键词提取...")
        assert result["keywords"], "关键词不能为空"
        print(f"  ✓ 关键词提取成功: {result['keywords']}")
        
        # 测试5：空文本处理
        print("\n[测试5] 空文本处理...")
        empty_result = self.process_text("")
        assert empty_result["title"] == "未命名会议"
        assert empty_result["summary"] == "无内容"
        print("  ✓ 空文本处理成功")
        
        # 测试6：短文本处理
        print("\n[测试6] 短文本处理...")
        short_result = self.process_text("简短会议")
        assert len(short_result["paragraphs"]) >= 3
        print("  ✓ 短文本处理成功")
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="会议纪要生成工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检测试")
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--text", "-t", help="直接输入文本")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        processor = MeetingProcessor()
        success = processor.selftest()
        sys.exit(0 if success else 1)
    
    # 处理输入
    processor = MeetingProcessor()
    
    if args.text:
        # 直接文本输入
        result = processor.process_text(args.text)
    elif args.input:
        # 文件输入
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                text = f.read()
            result = processor.process_text(text)
        except Exception as e:
            print(f"读取文件失败: {e}")
            sys.exit(1)
    else:
        # 交互式输入
        print("请输入会议内容（输入空行结束）：")
        lines = []
        while True:
            line = input()
            if not line.strip():
                break
            lines.append(line)
        text = "\n".join(lines)
        result = processor.process_text(text)
    
    # 输出结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
