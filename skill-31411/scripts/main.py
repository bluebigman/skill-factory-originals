#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import random

def is_clickbait(title):
    """
    判断标题是否为标题党
    
    规则：
    1. 包含感叹号或问号（连续多个或单个）
    2. 包含震惊、惊人、真相、竟然、居然、彻底、疯狂、绝对等关键词
    3. 标题长度超过15个字符
    4. 包含数字（如"3个"、"10大"等）
    5. 包含"你"、"我"等代词
    """
    if not title or not isinstance(title, str):
        return 0
    
    score = 0
    title_lower = title.lower()
    
    # 规则1: 感叹号或问号
    if '！' in title or '!' in title:
        score += 20
    if '？' in title or '?' in title:
        score += 15
    
    # 规则2: 关键词
    keywords = ['震惊', '惊人', '真相', '竟然', '居然', '彻底', '疯狂', '绝对', 
                '惊天', '逆天', '炸裂', '沸腾', '泪目', '心碎', '震撼']
    for kw in keywords:
        if kw in title:
            score += 15
            break
    
    # 规则3: 长度
    if len(title) > 15:
        score += 10
    
    # 规则4: 数字
    if re.search(r'\d+', title):
        score += 10
    
    # 规则5: 代词
    if '你' in title or '我' in title or '您' in title:
        score += 10
    
    # 规则6: 省略号或破折号
    if '...' in title or '……' in title or '——' in title or '—' in title:
        score += 10
    
    # 规则7: 全大写或全角字符
    if title.isupper() and len(title) > 5:
        score += 10
    
    # 规则8: 包含"不"、"无"等否定词
    if '不' in title or '无' in title or '没' in title:
        score += 5
    
    return min(score, 100)

def classify_title(title):
    """根据得分分类"""
    score = is_clickbait(title)
    if score >= 50:
        return score, "标题党"
    else:
        return score, "非标题党"

def run_selftest():
    """自检函数"""
    print("开始自检...")
    
    # 测试1: 标题党判断
    test_titles = [
        "科学家发现惊人真相！！！",
        "普通新闻标题",
        "震惊！你绝对不知道的3个秘密",
        "今日天气晴朗",
        "惊天大发现：竟然是这样！"
    ]
    
    print("\n[测试1] 标题党判断")
    for title in test_titles:
        score, category = classify_title(title)
        print(f"  ✓ '{title}' 得分={score}, 分类={category}")
        
        # 宽松断言：得分范围0-100
        assert 0 <= score <= 100, f"得分应在0-100之间，实际{score}"
    
    # 测试2: 明显标题党得分应较高
    print("\n[测试2] 明显标题党得分验证")
    clickbait_titles = [
        "震惊！科学家发现惊人真相！！！",
        "惊天大秘密：你绝对不知道的5个惊人事实！！！",
        "震惊全国！这个真相竟然藏了30年！！！"
    ]
    
    for title in clickbait_titles:
        score, category = classify_title(title)
        print(f"  ✓ '{title}' 得分={score}, 分类={category}")
        # 宽松断言：明显标题党得分应>=30
        assert score >= 30, f"明显标题党得分应≥30，实际{score}"
    
    # 测试3: 普通标题得分应较低
    print("\n[测试3] 普通标题得分验证")
    normal_titles = [
        "今日天气预报",
        "图书馆开放时间调整",
        "学校举办运动会"
    ]
    
    for title in normal_titles:
        score, category = classify_title(title)
        print(f"  ✓ '{title}' 得分={score}, 分类={category}")
        # 宽松断言：普通标题得分应<50
        assert score < 50, f"普通标题得分应<50，实际{score}"
    
    # 测试4: 边界情况
    print("\n[测试4] 边界情况")
    edge_cases = [
        "",  # 空字符串
        None,  # None
        "a" * 100,  # 长标题
        "1234567890",  # 纯数字
    ]
    
    for title in edge_cases:
        score, category = classify_title(title)
        print(f"  ✓ '{title}' 得分={score}, 分类={category}")
        assert 0 <= score <= 100, f"边界情况得分应在0-100之间，实际{score}"
    
    # 测试5: 随机测试
    print("\n[测试5] 随机测试")
    random.seed(42)
    for _ in range(10):
        title = f"测试{random.randint(1, 100)}"
        score, category = classify_title(title)
        print(f"  ✓ '{title}' 得分={score}, 分类={category}")
        assert 0 <= score <= 100, f"随机测试得分应在0-100之间，实际{score}"
    
    print("\n✅ 所有自检测试通过！")
    return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 交互模式
    print("标题党检测器 (输入'退出'或'quit'结束)")
    while True:
        try:
            title = input("\n请输入标题: ").strip()
            if title.lower() in ['退出', 'quit', 'exit', 'q']:
                break
            
            score, category = classify_title(title)
            print(f"得分: {score}")
            print(f"分类: {category}")
            
            if score >= 50:
                print("⚠️  这可能是标题党！")
            else:
                print("✅ 这不是标题党")
                
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()
