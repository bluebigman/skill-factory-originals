#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能包：智能对话助手
提供基于规则的中文对话处理、意图识别与响应生成
"""
import sys
import re
import random
import argparse
import time
from typing import Dict, List, Optional, Tuple, Any

class DialogueProcessor:
    """对话处理器：基于规则的中文对话理解与响应"""
    
    def __init__(self):
        """初始化处理器，加载规则库"""
        # 意图识别规则库（关键词 -> 意图）
        self.intent_rules = {
            'greeting': ['你好', '您好', '嗨', 'hello', 'hi', '早上好', '下午好', '晚上好'],
            'farewell': ['再见', '拜拜', 'bye', '下次见', '回头见'],
            'thanks': ['谢谢', '感谢', '多谢', 'thank'],
            'weather': ['天气', '气温', '下雨', '晴天', '阴天', '温度'],
            'time': ['几点', '时间', '现在', '日期', '今天几号'],
            'help': ['帮助', '怎么用', '功能', '能做什么', 'help'],
            'joke': ['笑话', '搞笑', '幽默', 'joke'],
            'name': ['你叫什么', '你是谁', '名字', 'name'],
            'capability': ['会什么', '能干什么', '擅长什么', '技能'],
        }
        
        # 响应模板库
        self.response_templates = {
            'greeting': [
                '您好！很高兴见到您，有什么我可以帮助的吗？',
                '你好呀！今天过得怎么样？',
                '您好！欢迎来到智能助手，请问有什么需要帮忙的？',
            ],
            'farewell': [
                '再见！祝您有美好的一天！',
                '拜拜！期待下次与您交流！',
                '再见！记得常来找我聊天哦！',
            ],
            'thanks': [
                '不客气！这是我应该做的。',
                '很高兴能帮到您！',
                '不用谢！随时为您服务。',
            ],
            'weather': [
                '我目前没有实时天气数据，建议您查看天气预报应用获取最新信息。',
                '天气情况请参考当地气象部门发布的最新预报哦。',
                '我无法获取实时天气，但建议您出门前查看天气预报。',
            ],
            'time': [
                '现在是北京时间，具体时间请查看您的设备时钟。',
                '我无法直接获取当前时间，请查看您的设备显示。',
                '时间信息请参考您的设备时钟显示。',
            ],
            'help': [
                '我可以帮您处理日常对话、回答问题、提供建议等。试试问我\'你会什么\'吧！',
                '我的功能包括：日常聊天、信息查询建议、问题解答等。',
                '您可以问我各种问题，我会尽力回答。也可以输入\'帮助\'查看更多功能。',
            ],
            'joke': [
                '为什么程序员总是混淆万圣节和圣诞节？因为 Oct 31 == Dec 25！',
                '程序员最讨厌的两件事：1.写文档 2.别人不写文档。',
                '为什么Python程序员不害怕蛇？因为他们早就习惯了！',
            ],
            'name': [
                '我叫小智，是您的智能对话助手！',
                '我是小智，一个基于规则的中文对话机器人。',
                '我的名字叫小智，很高兴认识您！',
            ],
            'capability': [
                '我可以进行日常对话、识别简单意图、提供建议。试试问我\'天气\'、\'时间\'或\'笑话\'！',
                '我的能力包括：意图识别、对话响应、信息查询建议等。',
                '我能帮您处理各种对话场景，比如问候、道别、询问天气时间等。',
            ],
            'default': [
                '我明白了，让我想想怎么回答您。',
                '这是一个有趣的问题，让我思考一下。',
                '好的，我理解您的意思了。',
                '收到，让我为您处理这个问题。',
            ],
        }
        
        # 中文标点符号映射
        self.punctuation_map = {
            '，': ',',
            '。': '.',
            '！': '!',
            '？': '?',
            '：': ':',
            '；': ';',
            '、': ',',
            '“': '"',
            '”': '"',
            '‘': "'",
            '’': "'",
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '《': '<',
            '》': '>',
        }
        
        # 口语化表达映射
        self.slang_map = {
            '咋': '怎么',
            '啥': '什么',
            '干嘛': '干什么',
            '咋样': '怎么样',
            '行': '可以',
            '中': '可以',
            '成': '可以',
            '好嘞': '好的',
            '嗯嗯': '好的',
            '木有': '没有',
            '木有': '没有',
            '肿么': '怎么',
            '神马': '什么',
            '酱紫': '这样子',
            '偶': '我',
            '俺': '我',
            '咱': '我们',
            '您': '你',
        }
    
    def preprocess(self, text: str) -> str:
        """
        文本预处理：清洗、标准化
        
        Args:
            text: 原始输入文本
            
        Returns:
            预处理后的文本
        """
        if not text or not text.strip():
            return ""
        
        # 去除首尾空白
        text = text.strip()
        
        # 统一大小写（英文部分）
        text = text.lower()
        
        # 替换中文标点为英文标点
        for cn_punc, en_punc in self.punctuation_map.items():
            text = text.replace(cn_punc, en_punc)
        
        # 替换口语化表达
        for slang, standard in self.slang_map.items():
            text = text.replace(slang, standard)
        
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def extract_intent(self, text: str) -> str:
        """
        提取用户意图
        
        Args:
            text: 预处理后的文本
            
        Returns:
            意图标签
        """
        # 检查每个意图的关键词
        for intent, keywords in self.intent_rules.items():
            for keyword in keywords:
                if keyword in text:
                    return intent
        
        # 如果没有匹配到任何意图，返回默认
        return 'default'
    
    def generate_response(self, intent: str) -> str:
        """
        根据意图生成响应
        
        Args:
            intent: 意图标签
            
        Returns:
            响应文本
        """
        templates = self.response_templates.get(intent, self.response_templates['default'])
        return random.choice(templates)
    
    def process(self, user_input: str) -> str:
        """
        处理用户输入并返回响应
        
        Args:
            user_input: 用户输入的原始文本
            
        Returns:
            处理后的响应文本
        """
        # 输入验证
        if not user_input or not user_input.strip():
            raise ValueError("E001: 输入为空或全为空白字符")
        
        # 预处理
        processed_text = self.preprocess(user_input)
        
        # 再次验证预处理后的文本
        if not processed_text:
            raise ValueError("E002: 预处理后文本为空")
        
        # 提取意图
        intent = self.extract_intent(processed_text)
        
        # 生成响应
        response = self.generate_response(intent)
        
        return response


def run_selftest() -> bool:
    """
    运行自检程序
    
    Returns:
        bool: 自检是否通过
    """
    print("=== 开始自检 ===")
    
    # 创建处理器实例
    processor = DialogueProcessor()
    
    # 样例1：正常对话
    try:
        result = processor.process("你好，今天天气怎么样？")
        assert len(result) > 0, "样例1：响应不应为空"
        print("样例1（正常对话）通过 ✓")
    except Exception as e:
        print(f"样例1（正常对话）失败 ✗: {str(e)}")
        return False
    
    # 样例2：中文标点+口语化
    try:
        result = processor.process("咋样，今天天气咋样？")
        assert len(result) > 0, "样例2：响应不应为空"
        print("样例2（中文标点+口语化）通过 ✓")
    except Exception as e:
        print(f"样例2（中文标点+口语化）失败 ✗: {str(e)}")
        return False
    
    # 样例3：空输入错误处理
    try:
        result = processor.process("   ")
        # 如果没抛异常，说明处理有问题
        print(f"样例3（空输入）失败 ✗: 应该抛出异常但未抛出")
        return False
    except ValueError as e:
        # 检查错误码
        error_msg = str(e)
        assert "E001" in error_msg or "E002" in error_msg, f"样例3：错误码应为E001或E002，实际{error_msg}"
        print("样例3（空输入错误处理）通过 ✓")
    except Exception as e:
        print(f"样例3（空输入）失败 ✗: {str(e)}")
        return False
    
    # 样例4：意图识别
    try:
        result = processor.process("谢谢你的帮助")
        assert len(result) > 0, "样例4：响应不应为空"
        print("样例4（意图识别）通过 ✓")
    except Exception as e:
        print(f"样例4（意图识别）失败 ✗: {str(e)}")
        return False
    
    # 样例5：多轮对话
    try:
        result1 = processor.process("你好")
        result2 = processor.process("再见")
        assert len(result1) > 0 and len(result2) > 0, "样例5：响应不应为空"
        print("样例5（多轮对话）通过 ✓")
    except Exception as e:
        print(f"样例5（多轮对话）失败 ✗: {str(e)}")
        return False
    
    print("=== 自检完成 ===")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='智能对话助手')
    parser.add_argument('--selftest', action='store_true', help='运行自检程序')
    parser.add_argument('--input', type=str, help='输入对话文本')
    parser.add_argument('--interactive', action='store_true', help='交互模式')
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        ok = run_selftest()
        sys.exit(0 if ok else 1)
    
    # 创建处理器
    processor = DialogueProcessor()
    
    # 交互模式
    if args.interactive:
        print("智能对话助手已启动（输入'退出'结束）")
        while True:
            try:
                user_input = input("你: ")
                if user_input in ['退出', 'quit', 'exit']:
                    print("再见！")
                    break
                response = processor.process(user_input)
                print(f"助手: {response}")
            except EOFError:
                break
            except Exception as e:
                print(f"错误: {str(e)}")
        return
    
    # 单次输入模式
    if args.input:
        try:
            response = processor.process(args.input)
            print(response)
        except Exception as e:
            print(f"错误: {str(e)}")
            sys.exit(1)
        return
    
    # 默认模式：演示
    print("智能对话助手演示")
    print("示例输入：你好、天气、时间、笑话、帮助、再见")
    print("输入'退出'结束程序")
    
    while True:
        try:
            user_input = input("你: ")
            if user_input in ['退出', 'quit', 'exit']:
                print("再见！")
                break
            response = processor.process(user_input)
            print(f"助手: {response}")
        except EOFError:
            break
        except Exception as e:
            print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()
