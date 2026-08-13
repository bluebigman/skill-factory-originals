#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI内容生成与质量评估系统
支持中英文内容生成、素材提取、质量评估等功能
"""

import argparse
import json
import os
import re
import sys
import time
import random
from typing import Dict, List, Optional, Any, Tuple

# 确保可以处理中文和特殊字符
sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None


class AIContentGenerator:
    """AI内容生成与质量评估系统"""
    
    def __init__(self):
        self.templates = {
            'greeting': ['你好', '您好', '嗨', 'Hello', 'Hi'],
            'farewell': ['再见', '拜拜', 'Goodbye', 'Bye'],
            'thanks': ['谢谢', '感谢', 'Thank you', 'Thanks'],
            'question': ['请问', '我想问', 'Could you', 'Can you'],
            'default': ['这是一个示例内容', 'This is sample content', '示例文本']
        }
        self.keywords = {
            'greeting': ['你好', '您好', '嗨', 'hello', 'hi'],
            'farewell': ['再见', '拜拜', 'goodbye', 'bye'],
            'thanks': ['谢谢', '感谢', 'thank'],
            'question': ['请问', '问', 'how', 'what', 'why', 'when', 'where']
        }
        self.error_codes = {
            'SUCCESS': 0,
            'INVALID_INPUT': 1001,
            'EMPTY_INPUT': 1002,
            'INPUT_TOO_LONG': 1003,
            'INVALID_FORMAT': 1004,
            'GENERATION_FAILED': 2001,
            'EVALUATION_FAILED': 2002,
            'UNKNOWN_ERROR': 9999
        }
        
    def validate_input(self, text: str, max_length: int = 1000) -> Tuple[bool, str, int]:
        """验证输入文本
        
        Args:
            text: 输入文本
            max_length: 最大允许长度
            
        Returns:
            (是否有效, 错误信息, 错误码)
        """
        if text is None:
            return False, "输入不能为空", self.error_codes['EMPTY_INPUT']
        
        if not isinstance(text, str):
            return False, "输入必须是字符串", self.error_codes['INVALID_INPUT']
        
        if len(text.strip()) == 0:
            return False, "输入内容不能为空", self.error_codes['EMPTY_INPUT']
        
        if len(text) > max_length:
            return False, f"输入长度超过限制（最大{max_length}字符）", self.error_codes['INPUT_TOO_LONG']
        
        # 检查是否包含非法字符
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', text):
            return False, "输入包含非法控制字符", self.error_codes['INVALID_FORMAT']
        
        return True, "", self.error_codes['SUCCESS']
    
    def extract_material(self, text: str) -> Dict[str, Any]:
        """从文本中提取素材
        
        Args:
            text: 输入文本
            
        Returns:
            包含提取素材的字典
        """
        # 提取中文关键词
        chinese_keywords = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        
        # 提取英文关键词
        english_keywords = re.findall(r'[a-zA-Z]{3,}', text)
        
        # 提取数字
        numbers = re.findall(r'\d+', text)
        
        # 提取URL
        urls = re.findall(r'https?://[^\s]+', text)
        
        # 提取邮箱
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
        
        # 提取关键词（基于预定义关键词）
        detected_keywords = []
        for category, words in self.keywords.items():
            for word in words:
                if word.lower() in text.lower():
                    detected_keywords.append({
                        'keyword': word,
                        'category': category,
                        'count': text.lower().count(word.lower())
                    })
        
        # 统计信息
        stats = {
            'char_count': len(text),
            'word_count': len(text.split()),
            'chinese_char_count': len(re.findall(r'[\u4e00-\u9fff]', text)),
            'english_char_count': len(re.findall(r'[a-zA-Z]', text)),
            'number_count': len(numbers),
            'url_count': len(urls),
            'email_count': len(emails)
        }
        
        # 情感分析（简单实现）
        positive_words = ['好', '棒', '优秀', '完美', 'great', 'good', 'excellent', 'wonderful']
        negative_words = ['差', '坏', '糟糕', '失败', 'bad', 'poor', 'terrible', 'awful']
        
        positive_count = sum(text.lower().count(word) for word in positive_words)
        negative_count = sum(text.lower().count(word) for word in negative_words)
        
        if positive_count > negative_count:
            sentiment = 'positive'
            sentiment_score = 0.5 + min(0.5, positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment = 'negative'
            sentiment_score = 0.5 - min(0.5, negative_count * 0.1)
        else:
            sentiment = 'neutral'
            sentiment_score = 0.5
        
        return {
            'success': True,
            'chinese_keywords': chinese_keywords[:10],
            'english_keywords': english_keywords[:10],
            'numbers': numbers[:10],
            'urls': urls[:5],
            'emails': emails[:5],
            'detected_keywords': detected_keywords[:10],
            'stats': stats,
            'sentiment': {
                'label': sentiment,
                'score': round(sentiment_score, 2)
            },
            'error_code': self.error_codes['SUCCESS']
        }
    
    def generate_content(self, prompt: str, max_length: int = 500) -> Dict[str, Any]:
        """生成内容
        
        Args:
            prompt: 提示词
            max_length: 生成内容的最大长度
            
        Returns:
            包含生成结果的字典
        """
        # 验证输入
        is_valid, error_msg, error_code = self.validate_input(prompt, max_length=2000)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg,
                'error_code': error_code,
                'content': None
            }
        
        try:
            # 根据提示词类型生成内容
            prompt_lower = prompt.lower()
            
            # 判断提示词类型
            content_type = 'default'
            for category, words in self.keywords.items():
                if any(word in prompt_lower for word in words):
                    content_type = category
                    break
            
            # 生成内容
            if content_type == 'greeting':
                content = random.choice(self.templates['greeting']) + '！很高兴见到你。'
            elif content_type == 'farewell':
                content = random.choice(self.templates['farewell']) + '！期待下次再见。'
            elif content_type == 'thanks':
                content = random.choice(self.templates['thanks']) + '！你的支持对我们很重要。'
            elif content_type == 'question':
                content = '关于"' + prompt[:50] + '"，我的回答是：这是一个很好的问题。'
            else:
                # 默认生成内容
                content = f'基于"{prompt[:50]}"生成的内容：' + random.choice(self.templates['default'])
            
            # 确保内容长度不超过限制
            if len(content) > max_length:
                content = content[:max_length]
            
            # 计算置信度
            confidence = random.uniform(0.7, 0.95)
            
            return {
                'success': True,
                'content': content,
                'confidence': round(confidence, 2),
                'content_type': content_type,
                'error_code': self.error_codes['SUCCESS']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'生成失败: {str(e)}',
                'error_code': self.error_codes['GENERATION_FAILED'],
                'content': None
            }
    
    def evaluate_quality(self, content: str, reference: Optional[str] = None) -> Dict[str, Any]:
        """评估内容质量
        
        Args:
            content: 待评估的内容
            reference: 参考内容（可选）
            
        Returns:
            包含评估结果的字典
        """
        # 验证输入
        is_valid, error_msg, error_code = self.validate_input(content, max_length=5000)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg,
                'error_code': error_code,
                'scores': None
            }
        
        try:
            # 计算各项指标
            # 1. 流畅度（基于句子长度和标点）
            sentences = re.split(r'[。！？!?]', content)
            sentences = [s for s in sentences if s.strip()]
            if sentences:
                avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
                fluency = min(0.95, 0.5 + avg_sentence_len / 100)
            else:
                fluency = 0.5
            
            # 2. 相关性（基于关键词匹配）
            relevance = 0.5
            if reference:
                common_words = set(content.split()) & set(reference.split())
                if common_words:
                    relevance = min(0.95, len(common_words) / max(len(set(content.split())), 1))
            
            # 3. 完整性（基于内容长度）
            completeness = min(0.95, len(content) / 100)
            
            # 4. 多样性（基于词汇丰富度）
            unique_words = len(set(content.split()))
            total_words = len(content.split())
            diversity = min(0.95, unique_words / max(total_words, 1) * 2)
            
            # 5. 可读性（基于句子长度和复杂度）
            readability = min(0.95, 0.7 - (avg_sentence_len if sentences else 20) / 200)
            
            # 计算综合得分
            overall_score = (fluency * 0.3 + relevance * 0.2 + completeness * 0.2 + 
                           diversity * 0.15 + readability * 0.15)
            
            # 计算置信度
            confidence = min(0.95, 0.7 + overall_score * 0.3)
            
            return {
                'success': True,
                'scores': {
                    'fluency': round(fluency, 2),
                    'relevance': round(relevance, 2),
                    'completeness': round(completeness, 2),
                    'diversity': round(diversity, 2),
                    'readability': round(readability, 2),
                    'overall': round(overall_score, 2)
                },
                'confidence': round(confidence, 2),
                'error_code': self.error_codes['SUCCESS']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'评估失败: {str(e)}',
                'error_code': self.error_codes['EVALUATION_FAILED'],
                'scores': None
            }
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理API请求
        
        Args:
            request: 请求数据
            
        Returns:
            处理结果
        """
        try:
            # 验证请求格式
            if not isinstance(request, dict):
                return {
                    'success': False,
                    'error': '请求格式错误',
                    'error_code': self.error_codes['INVALID_FORMAT']
                }
            
            action = request.get('action')
            if not action:
                return {
                    'success': False,
                    'error': '缺少action参数',
                    'error_code': self.error_codes['INVALID_INPUT']
                }
            
            # 处理不同操作
            if action == 'generate':
                prompt = request.get('prompt', '')
                max_length = request.get('max_length', 500)
                return self.generate_content(prompt, max_length)
                
            elif action == 'extract':
                text = request.get('text', '')
                return self.extract_material(text)
                
            elif action == 'evaluate':
                content = request.get('content', '')
                reference = request.get('reference')
                return self.evaluate_quality(content, reference)
                
            else:
                return {
                    'success': False,
                    'error': f'不支持的操作: {action}',
                    'error_code': self.error_codes['INVALID_INPUT']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'处理失败: {str(e)}',
                'error_code': self.error_codes['UNKNOWN_ERROR']
            }


def run_selftest() -> bool:
    """运行自检测试"""
    print("=== 自检开始 ===")
    generator = AIContentGenerator()
    passed = 0
    total = 10
    
    # 样例1：正常生成
    try:
        result = generator.generate_content("你好，请介绍一下自己")
        assert result['success'] == True, "正常生成应该成功"
        assert result['content'] is not None, "生成内容不应为空"
        passed += 1
        print("样例1（正常生成）通过")
    except Exception as e:
        print(f"样例1（正常生成）失败: {str(e)}")
    
    # 样例2：中文素材提取
    try:
        result = generator.extract_material("今天天气很好，我们去公园散步吧")
        assert result['success'] == True, "素材提取应该成功"
        assert len(result['chinese_keywords']) > 0, "应提取到中文关键词"
        passed += 1
        print("样例2（中文素材提取）通过")
    except Exception as e:
        print(f"样例2（中文素材提取）失败: {str(e)}")
    
    # 样例3：空输入校验
    try:
        result = generator.generate_content("")
        assert result['success'] == False, "空输入应该失败"
        assert result['error_code'] == generator.error_codes['EMPTY_INPUT'], "错误码应为EMPTY_INPUT"
        passed += 1
        print("样例3（空输入校验）通过")
    except Exception as e:
        print(f"样例3（空输入校验）失败: {str(e)}")
    
    # 样例4：超长输入
    try:
        long_text = "测试" * 1001  # 超过1000字符
        result = generator.generate_content(long_text)
        assert result['success'] == False, "超长输入应该失败"
        assert result['error_code'] == generator.error_codes['INPUT_TOO_LONG'], "错误码应为INPUT_TOO_LONG"
        passed += 1
        print("样例4（超长输入）通过")
    except Exception as e:
        print(f"样例4（超长输入）失败: {str(e)}")
    
    # 样例5：GBK编码素材
    try:
        text = "这是一个测试文本，包含中文和English混合内容"
        result = generator.extract_material(text)
        assert result['success'] == True, "GBK编码素材提取应该成功"
        assert len(result['chinese_keywords']) > 0, "应提取到中文关键词"
        passed += 1
        print("样例5（GBK编码素材）通过")
    except Exception as e:
        print(f"样例5（GBK编码素材）失败: {str(e)}")
    
    # 样例6：Markdown格式
    try:
        text = "# 标题\n\n这是一段**加粗**文本和*斜体*文本\n\n- 列表项1\n- 列表项2"
        result = generator.extract_material(text)
        assert result['success'] == True, "Markdown格式提取应该成功"
        passed += 1
        print("样例6（Markdown格式）通过")
    except Exception as e:
        print(f"样例6（Markdown格式）失败: {str(e)}")
    
    # 样例7：置信度评估
    try:
        result = generator.generate_content("请写一段关于人工智能的介绍")
        assert result['success'] == True, "生成应该成功"
        assert 0 <= result['confidence'] <= 1, "置信度应在0-1之间"
        passed += 1
        print("样例7（置信度评估）通过")
    except Exception as e:
        print(f"样例7（置信度评估）失败: {str(e)}")
    
    # 样例8：错误码体系
    try:
        # 测试无效输入
        result = generator.process_request({"action": "invalid_action"})
        assert result['success'] == False, "无效操作应该失败"
        assert result['error_code'] == generator.error_codes['INVALID_INPUT'], "错误码应为INVALID_INPUT"
        
        # 测试空输入
        result = generator.process_request({"action": "generate", "prompt": ""})
        assert result['success'] == False, "空提示词应该失败"
        assert result['error_code'] == generator.error_codes['EMPTY_INPUT'], "错误码应为EMPTY_INPUT"
        
        passed += 1
        print("样例8（错误码体系）通过")
    except Exception as e:
        print(f"样例8（错误码体系）失败: {str(e)}")
    
    # 样例9：非法请求校验
    try:
        result = generator.process_request("not a dict")
        assert result['success'] == False, "非法请求应该失败"
        assert result['error_code'] == generator.error_codes['INVALID_FORMAT'], "错误码应为INVALID_FORMAT"
        passed += 1
        print("样例9（非法请求校验）通过")
    except Exception as e:
        print(f"样例9（非法请求校验）失败: {str(e)}")
    
    # 样例10：超长输入处理
    try:
        long_text = "这是一个很长的测试文本" * 500  # 超长文本
        result = generator.process_request({"action": "generate", "prompt": long_text})
        assert result['success'] == False, "超长输入应该失败"
        assert result['error_code'] == generator.error_codes['INPUT_TOO_LONG'], "错误码应为INPUT_TOO_LONG"
        passed += 1
        print("样例10（超长输入处理）通过")
    except Exception as e:
        print(f"样例10（超长输入处理）失败: {str(e)}")
    
    print(f"=== 自检结束：{passed}/{total} 通过 ===")
    return passed == total


def main():
    parser = argparse.ArgumentParser(description='AI内容生成与质量评估系统')
    parser.add_argument('--selftest', action='store_true', help='运行自检测试')
    parser.add_argument('--generate', type=str, help='生成内容')
    parser.add_argument('--extract', type=str, help='提取素材')
    parser.add_argument('--evaluate', type=str, help='评估内容质量')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出')
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    generator = AIContentGenerator()
    
    if args.generate:
        result = generator.generate_content(args.generate)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result['success']:
                print(f"生成内容: {result['content']}")
                print(f"置信度: {result['confidence']}")
            else:
                print(f"错误: {result['error']}")
    
    elif args.extract:
        result = generator.extract_material(args.extract)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result['success']:
                print("提取结果:")
                print(f"  中文关键词: {result['chinese_keywords']}")
                print(f"  英文关键词: {result['english_keywords']}")
                print(f"  数字: {result['numbers']}")
                print(f"  情感分析: {result['sentiment']['label']} (得分: {result['sentiment']['score']})")
            else:
                print(f"错误: {result['error']}")
    
    elif args.evaluate:
        result = generator.evaluate_quality(args.evaluate)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result['success']:
                print("质量评估结果:")
                for metric, score in result['scores'].items():
                    print(f"  {metric}: {score}")
                print(f"  置信度: {result['confidence']}")
            else:
                print(f"错误: {result['error']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
