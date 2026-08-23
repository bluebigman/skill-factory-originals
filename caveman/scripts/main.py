#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
caveman - 原始人指令压缩工具
将复杂指令压缩为精简表达，减少令牌消耗。
仅依据功能规格独立实现（clean-room）。
"""

import argparse
import re
import sys
import time
from typing import List, Tuple, Optional
from datetime import datetime, timezone

# 尝试导入tiktoken用于真实令牌计数（可选依赖）
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "输入不是字符串",
    "E003": "输入超过2000字限制",
    "E004": "压缩结果为空",
    "E005": "内部处理异常",
    "E006": "参数解析失败",
    "E007": "自检失败",
    "E008": "文件读写失败",
    "E009": "未知错误",
    "E010": "非法字符",
}


class CavemanError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _validate_input(text: str) -> None:
    """校验输入文本合法性"""
    if text is None:
        raise CavemanError("E001")
    if not isinstance(text, str):
        raise CavemanError("E002")
    if len(text) > 2000:
        raise CavemanError("E003")
    if not text.strip():
        raise CavemanError("E001")
    # 检查非法字符（控制字符等）
    if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in text):
        raise CavemanError("E010")


def _extract_keywords(text: str, custom_stopwords: Optional[List[str]] = None) -> List[str]:
    """提取文本中的关键词（动词、名词、关键限定词）"""
    # 去除标点符号和特殊字符，保留中英文、数字
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\s]", " ", text)
    
    # 分词：中文按字/词拆分，英文按空格拆分
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]+", cleaned)
    
    # 如果中文部分太少，尝试更细粒度切分
    if len(parts) < 2:
        parts = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", cleaned)
    
    # 停用词表（精简，避免过度过滤）
    stopwords = {
        "的", "了", "是", "在", "和", "与", "或", "把", "被", "让",
        "请", "帮我", "一下", "这个", "那个", "这些", "那些", "一个",
        "the", "a", "an", "is", "are", "was", "were", "be", "to", "of",
        "in", "on", "at", "for", "with", "by", "and", "or", "not", "no",
    }
    
    # 合并自定义停用词
    if custom_stopwords:
        stopwords.update([w.lower() for w in custom_stopwords])
    
    keywords = []
    for part in parts:
        if part.lower() not in stopwords and len(part) > 0:
            keywords.append(part)
    
    # 如果没有提取到关键词，返回原文中的有效部分
    if not keywords:
        chars = re.findall(r"[\u4e00-\u9fff]", text)
        keywords = [c for c in chars if c not in stopwords]
    
    return keywords


def _build_compressed(keywords: List[str], level: int = 1) -> str:
    """根据关键词构建压缩表达，支持压缩级别调整"""
    if not keywords:
        raise CavemanError("E004")
    
    # 原始人风格：短词 + 空格分隔，保留核心语义
    action_words = {
        "看", "做", "写", "说", "给", "去", "来", "用", "找", "分析",
        "计算", "生成", "创建", "删除", "修改", "查询", "导出", "添加",
        "测试", "阅读", "制作", "设计", "开发", "优化", "提升",
        "read", "write", "run", "make", "get", "set", "find",
        "create", "delete", "update", "query", "analyze", "calculate"
    }
    
    actions = []
    objects = []
    modifiers = []
    
    for kw in keywords:
        if kw in action_words or kw.lower() in action_words:
            actions.append(kw)
        elif len(kw) <= 2 and not kw.isdigit():
            modifiers.append(kw)
        else:
            objects.append(kw)
    
    # 根据压缩级别调整保留数量
    if level == 1:  # 标准压缩
        action_limit = 2
        object_limit = 4
        modifier_limit = 2
    elif level == 2:  # 深度压缩
        action_limit = 1
        object_limit = 2
        modifier_limit = 1
    elif level == 3:  # 极限压缩
        action_limit = 1
        object_limit = 1
        modifier_limit = 0
    else:  # 默认标准
        action_limit = 2
        object_limit = 4
        modifier_limit = 2
    
    # 组合：动作 + 对象 + 限定
    result_parts = actions[:action_limit] + objects[:object_limit] + modifiers[:modifier_limit]
    
    if not result_parts:
        # 兜底：取前几个关键词
        result_parts = keywords[:max(1, action_limit + object_limit)]
    
    # 确保结果非空
    if not result_parts:
        result_parts = [keywords[0]]
    
    return " ".join(result_parts)


def _count_tokens(text: str) -> int:
    """使用tiktoken或估算方式计算令牌数"""
    if HAS_TIKTOKEN:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            pass
    # 估算：中文字符算1个令牌，英文单词算1个令牌
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    numbers = len(re.findall(r'\d+', text))
    return chinese_chars + english_words + numbers


def compress(text: str, level: int = 1, custom_stopwords: Optional[List[str]] = None) -> Tuple[str, float]:
    """
    将复杂指令压缩为原始人式精简表达
    
    Args:
        text: 原始指令文本
        level: 压缩级别（1-3）
        custom_stopwords: 自定义停用词列表
        
    Returns:
        (压缩后的精简表达, 实际令牌节省比例)
        
    Raises:
        CavemanError: 处理失败时抛出，包含错误码
    """
    try:
        _validate_input(text)
        keywords = _extract_keywords(text, custom_stopwords)
        result = _build_compressed(keywords, level)
        
        # 确保结果不为空且合理
        if not result or len(result) > len(text):
            result = text[:min(len(text), 100)]
        
        # 计算实际令牌节省比例
        original_tokens = _count_tokens(text)
        compressed_tokens = _count_tokens(result)
        savings = 1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0.0
        
        return result, savings
    except CavemanError:
        raise
    except Exception as e:
        raise CavemanError("E005", str(e)) from e


def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检
    
    Returns:
        True 表示自检通过，False 表示失败
    """
    print("=" * 60)
    print("caveman 自检开始 (selftest)")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    # 硬编码测试样例（不依赖外部文件）
    test_cases = [
        {
            "input": "请帮我分析这份合同中的违约责任条款",
            "min_keywords": 2,
            "max_len_ratio": 0.8,
            "level": 1,
        },
        {
            "input": "写一篇关于人工智能发展趋势的文章，要求500字以上",
            "min_keywords": 3,
            "max_len_ratio": 0.8,
            "level": 1,
        },
        {
            "input": "计算这段代码的时间复杂度",
            "min_keywords": 2,
            "max_len_ratio": 0.8,
            "level": 2,
        },
        {
            "input": "给这个项目添加单元测试",
            "min_keywords": 2,
            "max_len_ratio": 0.8,
            "level": 1,
        },
        {
            "input": "查询数据库中的用户信息并导出为CSV文件",
            "min_keywords": 3,
            "max_len_ratio": 0.8,
            "level": 3,
        },
    ]
    
    all_passed = True
    
    # 核心链路测试
    print("核心链路测试:")
    for i, case in enumerate(test_cases, 1):
        try:
            original = case["input"]
            level = case.get("level", 1)
            compressed, savings = compress(original, level=level)
            
            # 断言：压缩结果非空
            assert compressed, f"压缩结果为空"
            
            # 断言：压缩结果包含至少一个原文字符
            assert any(ch in compressed for ch in original if ch.strip()), \
                "压缩结果与原文无关联"
            
            # 断言：压缩后长度不超过原文（允许少量溢出）
            assert len(compressed) <= len(original) * 1.2, \
                f"压缩结果过长: {len(compressed)} > {len(original) * 1.2}"
            
            # 断言：节省比例为正
            assert savings >= 0, f"节省比例为负: {savings}"
            
            # 断言：关键词数量
            keywords = _extract_keywords(original)
            assert len(keywords) >= case["min_keywords"], \
                f"关键词提取不足: {len(keywords)} < {case['min_keywords']}"
            
            print(f"  ✓ 用例{i}: '{original}' → '{compressed}' (节省{savings:.0%})")
            
        except AssertionError as e:
            print(f"  ✗ 用例{i}失败: {e}")
            all_passed = False
        except CavemanError as e:
            print(f"  ✗ 用例{i}异常: {e}")
            all_passed = False
    
    # 压缩级别测试
    print("\n压缩级别测试:")
    test_text = "请帮我分析这份合同中的违约责任条款并给出修改建议"
    for level in [1, 2, 3]:
        try:
            compressed, savings = compress(test_text, level=level)
            assert compressed, f"级别{level}压缩结果为空"
            assert len(compressed) <= len(test_text), f"级别{level}压缩结果过长"
            print(f"  ✓ 级别{level}: '{compressed}' (节省{savings:.0%})")
        except Exception as e:
            print(f"  ✗ 级别{level}失败: {e}")
            all_passed = False
    
    # 自定义停用词测试
    print("\n自定义停用词测试:")
    try:
        compressed, savings = compress(
            "请帮我分析这份合同中的违约责任条款",
            custom_stopwords=["合同", "条款"]
        )
        assert compressed, "自定义停用词压缩结果为空"
        assert "合同" not in compressed and "条款" not in compressed, \
            "自定义停用词未生效"
        print(f"  ✓ 自定义停用词: '{compressed}' (节省{savings:.0%})")
    except Exception as e:
        print(f"  ✗ 自定义停用词测试失败: {e}")
        all_passed = False
    
    # 错误处理测试
    print("\n错误处理测试:")
    error_tests = [
        ("", "E001"),  # 空输入
        (None, "E001"),  # None
        (12345, "E002"),  # 非字符串
        ("a" * 3000, "E003"),  # 超长
    ]
    
    for input_data, expected_code in error_tests:
        try:
            if isinstance(input_data, str) or input_data is None:
                compress(input_data)
            else:
                _validate_input(input_data)
            print(f"  ✗ 应抛出{expected_code}但未抛出")
            all_passed = False
        except CavemanError as e:
            if e.code == expected_code:
                print(f"  ✓ 正确抛出{e.code}")
            else:
                print(f"  ✗ 期望{expected_code}，实际{e.code}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ 异常类型错误: {type(e).__name__}")
            all_passed = False
    
    # 令牌计数测试
    print("\n令牌计数测试:")
    test_pairs = [
        ("这是一个很长的测试输入文本", "测试 输入"),
        ("请帮我写一份关于人工智能的详细报告", "写 报告"),
    ]
    for original, compressed in test_pairs:
        orig_tokens = _count_tokens(original)
        comp_tokens = _count_tokens(compressed)
        assert orig_tokens > 0 and comp_tokens > 0, "令牌计数异常"
        savings = 1.0 - (comp_tokens / orig_tokens)
        assert 0 <= savings <= 1, f"节省比例超出范围: {savings}"
        print(f"  ✓ 原文{orig_tokens}令牌 → 压缩{comp_tokens}令牌 (节省{savings:.0%})")
    
    print("=" * 60)
    if all_passed:
        print("自检通过 ✓")
    else:
        print("自检失败 ✗")
    print("=" * 60)
    
    return all_passed


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="caveman - 原始人指令压缩工具",
        epilog="示例: python main.py --text '请帮我分析这份合同' --level 2"
    )
    parser.add_argument(
        "--text", "-t",
        type=str,
        help="待压缩的指令文本"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    parser.add_argument(
        "--save",
        type=str,
        help="将压缩结果保存到文件"
    )
    parser.add_argument(
        "--level", "-l",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="压缩级别: 1=标准, 2=深度, 3=极限 (默认: 1)"
    )
    parser.add_argument(
        "--custom-stopwords",
        type=str,
        nargs="+",
        help="自定义停用词列表（空格分隔）"
    )
    
    try:
        args = parser.parse_args()
    except SystemExit:
        return 1
    
    # 自检模式
    if args.selftest:
        try:
            passed = run_selftest()
            return 0 if passed else 1
        except Exception as e:
            print(f"[E007] 自检异常: {e}")
            return 1
    
    # 压缩模式
    if not args.text:
        parser.print_help()
        return 0
    
    try:
        result, savings = compress(
            args.text,
            level=args.level,
            custom_stopwords=args.custom_stopwords
        )
        
        print(f"原始指令: {args.text}")
        print(f"压缩表达: {result}")
        print(f"令牌节省: {savings:.0%}")
        print(f"压缩级别: {args.level}")
        
        # 保存到文件
        if args.save:
            try:
                with open(args.save, "w", encoding="utf-8") as f:
                    f.write(result)
                print(f"已保存到: {args.save}")
            except IOError as e:
                print(f"[E008] 文件写入失败: {e}")
                return 1
        
        return 0
        
    except CavemanError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"[E009] 未知错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
