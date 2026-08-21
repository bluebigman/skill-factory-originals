#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标题工坊 - 智能标题生成与优化工具"""

import argparse
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

# ============ 核心功能 ============

def generate_titles(keyword, style=None, count=5):
    """生成标题列表"""
    if not keyword or not keyword.strip():
        raise ValueError("关键词不能为空")
    
    count = max(1, min(int(count), 20))
    keyword = keyword.strip()
    
    # 风格模板
    templates = {
        "default": [
            "{kw}：从入门到精通",
            "深入解析{kw}的奥秘",
            "{kw}实用指南",
            "掌握{kw}的5个关键技巧",
            "{kw}完全攻略",
            "揭秘{kw}背后的原理",
            "{kw}实战经验分享",
            "如何高效学习{kw}",
            "{kw}进阶之路",
            "{kw}常见问题解答",
        ],
        "科技": [
            "{kw}技术革新：未来已来",
            "人工智能时代的{kw}",
            "{kw}：科技改变生活",
            "前沿科技中的{kw}应用",
            "{kw}与数字化转型",
        ],
        "教育": [
            "{kw}学习指南：从基础到进阶",
            "如何快速掌握{kw}",
            "{kw}教学心得与体会",
            "{kw}学习路线图",
            "高效学习{kw}的方法论",
        ],
        "财经": [
            "{kw}投资分析：机遇与挑战",
            "{kw}市场趋势解读",
            "{kw}理财策略分享",
            "{kw}经济影响深度分析",
            "{kw}行业报告解读",
        ],
        "生活": [
            "{kw}生活小妙招",
            "{kw}实用技巧合集",
            "{kw}日常应用指南",
            "{kw}让生活更美好",
            "{kw}生活百科",
        ],
    }
    
    # 选择模板
    if style and style in templates:
        style_templates = templates[style]
    else:
        style_templates = templates["default"]
    
    # 生成标题
    titles = []
    for i in range(count):
        template = style_templates[i % len(style_templates)]
        title = template.format(kw=keyword)
        titles.append(title)
    
    return titles


def organize_titles(titles):
    """整理标题列表"""
    if not titles:
        return []
    
    # 去重并保持顺序
    seen = set()
    unique_titles = []
    for title in titles:
        if title and title not in seen:
            seen.add(title)
            unique_titles.append(title)
    
    # 按长度排序
    unique_titles.sort(key=len)
    return unique_titles


def validate_titles(titles):
    """校验标题列表"""
    if not titles:
        return False
    
    for title in titles:
        if not title or len(title.strip()) < 2:
            return False
        if len(title) > 100:
            return False
    
    return True


def check_duplicates(titles):
    """检查重复率"""
    if not titles:
        return 0.0
    
    total = len(titles)
    unique = len(set(titles))
    duplicate_rate = (total - unique) / total
    return duplicate_rate


def process_chinese_punctuation(text):
    """处理中文标点"""
    if not text:
        return text
    
    # 统一中文标点
    replacements = {
        ',': '，',
        '.': '。',
        '?': '？',
        '!': '！',
        ':': '：',
        ';': '；',
        '(': '（',
        ')': '）',
        '"': '"',
        "'": "'",
    }
    
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result


def read_titles_from_file(filepath):
    """从文件读取标题"""
    if not filepath or not filepath.strip():
        raise ValueError("文件路径不能为空")
    
    # 路径校验
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    if not path.is_file():
        raise ValueError("路径必须指向文件")
    
    # 读取内容
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = path.read_text(encoding='gbk')
    
    # 解析标题
    titles = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            # 去除可能的编号
            line = re.sub(r'^\d+[\.、]\s*', '', line)
            if line:
                titles.append(line)
    
    return titles


def validate_path(filepath):
    """校验文件路径"""
    if not filepath or not filepath.strip():
        raise ValueError("路径不能为空")
    
    path = Path(filepath)
    
    # 检查是否为绝对路径或相对路径
    if not path.is_absolute() and not path.exists():
        # 尝试在当前目录下查找
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")
    
    return True


# ============ 自检函数 ============

def run_selftest():
    """运行自检"""
    print("[RUN] === 标题工坊自检开始 ===")
    
    # 测试1: 标题生成
    try:
        titles = generate_titles("Python")
        assert len(titles) >= 1, "标题生成数量不足"
        assert all(isinstance(t, str) and len(t) > 0 for t in titles), "标题格式错误"
        print("✅ 测试1 标题生成：通过")
    except Exception as e:
        print(f"❌ 测试1 标题生成：失败 - {e}")
        return False
    
    # 测试2: 指定风格生成
    try:
        titles = generate_titles("Python", style="科技")
        assert len(titles) >= 1, "风格标题生成数量不足"
        assert all(isinstance(t, str) and len(t) > 0 for t in titles), "风格标题格式错误"
        print("✅ 测试2 指定风格生成：通过")
    except Exception as e:
        print(f"❌ 测试2 指定风格生成：失败 - {e}")
        return False
    
    # 测试3: 标题整理
    try:
        raw_titles = ["测试标题", "测试标题", "另一个标题", ""]
        organized = organize_titles(raw_titles)
        assert len(organized) >= 2, "整理后标题数量不足"
        assert len(organized) == len(set(organized)), "整理后仍有重复"
        print("✅ 测试3 标题整理：通过")
    except Exception as e:
        print(f"❌ 测试3 标题整理：失败 - {e}")
        return False
    
    # 测试4: 标题校验
    try:
        valid_titles = ["有效标题", "另一个有效标题"]
        assert validate_titles(valid_titles), "有效标题校验失败"
        print("✅ 测试4 标题校验：通过")
    except Exception as e:
        print(f"❌ 测试4 标题校验：失败 - {e}")
        return False
    
    # 测试5: 空标题列表应报错
    try:
        result = validate_titles([])
        assert result == False, "空列表应返回False"
        print("✅ 测试5 空标题列表应报错：通过")
    except Exception as e:
        print(f"❌ 测试5 空标题列表应报错：失败 - {e}")
        return False
    
    # 测试5b: 边界情况（空输入）
    try:
        result = generate_titles("")
        assert result is None or len(result) == 0, "空关键词应返回空列表"
        print("✅ 测试5 边界情况（空输入）：通过")
    except ValueError:
        print("✅ 测试5 边界情况（空输入）：通过")
    except Exception as e:
        print(f"❌ 测试5 边界情况（空输入）：失败 - {e}")
        return False
    
    # 测试6: 边界情况（超长输入）
    try:
        long_keyword = "长" * 200
        titles = generate_titles(long_keyword)
        assert len(titles) >= 1, "超长关键词应生成标题"
        print("✅ 测试6 边界情况（超长输入）：通过")
    except Exception as e:
        print(f"❌ 测试6 边界情况（超长输入）：失败 - {e}")
        return False
    
    # 测试7: 中文标点处理
    try:
        text = "测试,标点.处理?"
        processed = process_chinese_punctuation(text)
        assert "，" in processed, "逗号未转换"
        assert "。" in processed, "句号未转换"
        assert "？" in processed, "问号未转换"
        print("✅ 测试7 中文标点处理：通过")
    except Exception as e:
        print(f"❌ 测试7 中文标点处理：失败 - {e}")
        return False
    
    # 测试8: 数量边界
    try:
        titles = generate_titles("测试", count=0)
        assert len(titles) >= 1, "count=0时应至少生成1个"
        
        titles = generate_titles("测试", count=100)
        assert len(titles) <= 20, "count=100时应限制在20个以内"
        print("✅ 测试8 数量边界：通过")
    except Exception as e:
        print(f"❌ 测试8 数量边界：失败 - {e}")
        return False
    
    # 测试9: 重复率检查
    try:
        titles = ["相同标题", "相同标题", "不同标题"]
        rate = check_duplicates(titles)
        assert rate > 0, "重复率应大于0"
        assert rate <= 1.0, "重复率应小于等于1"
        print("✅ 测试9 重复率检查：通过")
    except Exception as e:
        print(f"❌ 测试9 重复率检查：失败 - {e}")
        return False
    
    # 测试10: 文件读取
    try:
        # 创建临时测试文件
        temp_file = Path("test_titles.txt")
        temp_file.write_text("标题一\n标题二\n标题三\n", encoding='utf-8')
        
        titles = read_titles_from_file("test_titles.txt")
        assert len(titles) >= 3, "文件读取标题数量不足"
        
        # 清理临时文件
        temp_file.unlink()
        print("✅ 测试10 文件读取：通过")
    except Exception as e:
        print(f"❌ 测试10 文件读取：失败 - {e}")
        return False
    
    # 测试11: 路径校验
    try:
        # 不存在的路径应该报错
        try:
            validate_path("nonexistent_file.txt")
            print("❌ 测试11 路径校验：失败 - 不存在的路径未报错")
            return False
        except FileNotFoundError:
            pass
        
        # 存在的路径应该通过
        temp_file = Path("test_path.txt")
        temp_file.write_text("test", encoding='utf-8')
        validate_path("test_path.txt")
        temp_file.unlink()
        
        print("✅ 测试11 路径校验：通过")
    except Exception as e:
        print(f"❌ 测试11 路径校验：失败 - {e}")
        return False
    
    print("[PASS] === 标题工坊自检全部通过 ===")
    return True


# ============ 命令行入口 ============

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="标题工坊 - 智能标题生成与优化工具")
    parser.add_argument("--generate", "-g", help="生成标题的关键词")
    parser.add_argument("--style", "-s", help="标题风格")
    parser.add_argument("--count", "-c", type=int, default=5, help="生成数量")
    parser.add_argument("--organize", "-o", help="整理标题（JSON数组）")
    parser.add_argument("--validate", "-v", help="校验标题（JSON数组）")
    parser.add_argument("--file", "-f", help="从文件读取标题")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    if args.generate:
        try:
            titles = generate_titles(args.generate, args.style, args.count)
            for i, title in enumerate(titles, 1):
                print(f"{i}. {title}")
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.organize:
        try:
            titles = json.loads(args.organize)
            organized = organize_titles(titles)
            print(json.dumps(organized, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.validate:
        try:
            titles = json.loads(args.validate)
            result = validate_titles(titles)
            print(f"校验结果: {'通过' if result else '失败'}")
            sys.exit(0 if result else 1)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.file:
        try:
            titles = read_titles_from_file(args.file)
            for i, title in enumerate(titles, 1):
                print(f"{i}. {title}")
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
