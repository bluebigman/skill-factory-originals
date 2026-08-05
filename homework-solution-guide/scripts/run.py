#!/usr/bin/env python3
"""homework-solution-guide Skill - 作业解题指导"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# 题目类型定义
SUBJECTS = {
    "math": "数学",
    "physics": "物理",
    "chemistry": "化学"
}

GRADES = {
    "7年级": "七年级",
    "8年级": "八年级",
    "9年级": "九年级",
    "10": "高一"
}

# 解析模板
TEMPLATES = {
    "step": {
        "description": "分步解题",
        "output_lines": 8
    },
    "hint": {
        "description": "提示",
        "output_lines": 10
    },
    "review": {
        "description": "复习",
        "output_lines": 10
    },
    "analyze": {
        "description": "分析",
        "output_lines": 12
    },
    "next": {
        "description": "下一步",
        "output_lines": 11
    }
}

def load_spec(subject, grade, topic):
    """加载题目规格"""
    # 这里应该是从文件或数据库加载
    # 为了演示，返回一个模拟的规格
    return {
        "subject": subject,
        "grade": grade,
        "topic": topic,
        "type": "homework",
        "content": f"{SUBJECTS.get(subject, subject)} {GRADES.get(grade, grade)} {topic} 题目",
        "equation": None
    }

def match_trigger(text):
    """匹配触发词"""
    triggers = ["作业", "解题", "指导", "help", "solve"]
    return any(t in text.lower() for t in triggers)

def extract_equation(content, subject):
    """从题目内容中提取方程/公式"""
    if subject == "chemistry":
        # 化学方程式的常见模式
        patterns = [
            r'[A-Z][a-z]?\d*\s*\+\s*[A-Z][a-z]?\d*\s*→\s*[A-Z][a-z]?\d*',  # 简单反应
            r'[A-Z][a-z]?\d*\s*=\s*[A-Z][a-z]?\d*',  # 等式
            r'[A-Za-z0-9]+\s*\+\s*[A-Za-z0-9]+\s*→\s*[A-Za-z0-9]+',  # 一般反应
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)
        # 如果没有匹配到，尝试更宽松的模式
        match = re.search(r'[A-Za-z0-9]+(?:\s*\+\s*[A-Za-z0-9]+)*\s*[→=]\s*[A-Za-z0-9]+', content)
        if match:
            return match.group(0)
        return None
    elif subject == "math":
        # 数学公式
        match = re.search(r'[0-9xXyY]+\s*[+\-*/]\s*[0-9xXyY]+\s*=\s*[0-9xXyY]+', content)
        return match.group(0) if match else None
    elif subject == "physics":
        # 物理公式
        match = re.search(r'[A-Za-z]+\s*=\s*[A-Za-z0-9]+\s*[+\-*/]\s*[A-Za-z0-9]+', content)
        return match.group(0) if match else None
    return None

def generate_review(spec):
    """生成复习内容"""
    lines = []
    subject = spec.get("subject", "")
    content = spec.get("content", "")
    
    # 提取方程
    equation = extract_equation(content, subject)
    if equation:
        spec["equation"] = equation
    
    lines.append(f"【复习】{SUBJECTS.get(subject, subject)} {GRADES.get(spec.get('grade', ''), spec.get('grade', ''))} 复习指导")
    lines.append("")
    lines.append("一、核心知识点回顾")
    lines.append(f"  1. 题目类型：{spec.get('topic', '')}")
    lines.append(f"  2. 解题思路：分析题目条件，确定解题方向")
    
    if equation:
        lines.append(f"  3. 关键公式：{equation}")
    else:
        lines.append("  3. 关键公式：无特定公式")
    
    lines.append("")
    lines.append("二、常见错误提醒")
    lines.append("  1. 注意单位换算")
    lines.append("  2. 注意符号正负")
    lines.append("  3. 注意计算精度")
    
    return lines

def generate_step(spec):
    """生成分步解题"""
    lines = []
    subject = spec.get("subject", "")
    content = spec.get("content", "")
    
    lines.append(f"【分步解题】{SUBJECTS.get(subject, subject)} {GRADES.get(spec.get('grade', ''), spec.get('grade', ''))} 题目")
    lines.append("")
    lines.append("第一步：审题")
    lines.append(f"  题目内容：{content}")
    lines.append("  明确已知条件和求解目标")
    lines.append("")
    lines.append("第二步：分析")
    lines.append("  确定解题方法和步骤")
    lines.append("  列出相关公式")
    
    return lines

def generate_hint(spec):
    """生成提示"""
    lines = []
    subject = spec.get("subject", "")
    
    lines.append(f"【提示】{SUBJECTS.get(subject, subject)} {GRADES.get(spec.get('grade', ''), spec.get('grade', ''))} 题目提示")
    lines.append("")
    lines.append("提示1：仔细阅读题目，找出关键信息")
    lines.append("提示2：回忆相关知识点和公式")
    lines.append("提示3：尝试从已知条件推导")
    lines.append("提示4：注意题目中的隐含条件")
    lines.append("提示5：检查答案的合理性")
    lines.append("提示6：如果卡住，尝试换个角度思考")
    lines.append("提示7：可以画图辅助理解")
    lines.append("提示8：注意单位和精度")
    
    return lines

def generate_analyze(spec):
    """生成分析"""
    lines = []
    subject = spec.get("subject", "")
    content = spec.get("content", "")
    
    lines.append(f"【分析】{SUBJECTS.get(subject, subject)} {GRADES.get(spec.get('grade', ''), spec.get('grade', ''))} 题目分析")
    lines.append("")
    lines.append("一、题目分析")
    lines.append(f"  题目：{content}")
    lines.append("  难度：中等")
    lines.append("  考点：基本概念和计算")
    lines.append("")
    lines.append("二、解题思路")
    lines.append("  1. 理解题意")
    lines.append("  2. 提取关键信息")
    lines.append("  3. 选择合适方法")
    lines.append("  4. 逐步计算")
    lines.append("  5. 验证结果")
    
    return lines

def generate_next(spec):
    """生成下一步"""
    lines = []
    subject = spec.get("subject", "")
    
    lines.append(f"【下一步】{SUBJECTS.get(subject, subject)} {GRADES.get(spec.get('grade', ''), spec.get('grade', ''))} 下一步建议")
    lines.append("")
    lines.append("1. 完成当前题目后，尝试类似题目")
    lines.append("2. 总结解题方法和技巧")
    lines.append("3. 复习相关知识点")
    lines.append("4. 做错题本记录")
    lines.append("5. 与同学讨论解题思路")
    lines.append("6. 请教老师疑难问题")
    lines.append("7. 定期回顾已学内容")
    lines.append("8. 尝试挑战更高难度")
    lines.append("9. 保持练习频率")
    lines.append("10. 建立知识框架")
    
    return lines

def generate_content(spec, mode):
    """根据模式生成内容"""
    if mode == "step":
        return generate_step(spec)
    elif mode == "hint":
        return generate_hint(spec)
    elif mode == "review":
        return generate_review(spec)
    elif mode == "analyze":
        return generate_analyze(spec)
    elif mode == "next":
        return generate_next(spec)
    else:
        return [f"未知模式: {mode}"]

def selftest():
    """自检函数"""
    test_cases = [
        ("math", "7年级", "review"),
        ("math", "7年级", "analyze"),
        ("math", "7年级", "next"),
        ("physics", "9年级", "step"),
        ("physics", "9年级", "hint"),
        ("physics", "9年级", "review"),
        ("physics", "9年级", "analyze"),
        ("physics", "9年级", "next"),
        ("chemistry", "10", "step"),
        ("chemistry", "10", "hint"),
        ("chemistry", "10", "review"),
        ("chemistry", "10", "analyze"),
        ("chemistry", "10", "next"),
    ]
    
    all_passed = True
    for subject, grade, mode in test_cases:
        spec = load_spec(subject, grade, "测试题目")
        # 为化学题目添加一些内容以便提取方程
        if subject == "chemistry":
            spec["content"] = "2H2 + O2 → 2H2O 反应方程式"
        
        lines = generate_content(spec, mode)
        print(f"  {'✓' if len(lines) > 0 else '✗'} {subject}/{grade}/{mode}: {len(lines)} 行输出")
        
        # 检查 review 模式是否包含 equation
        if mode == "review" and subject == "chemistry":
            if "equation" not in spec or not spec["equation"]:
                print(f"  ✗ 测试失败: {subject}/{grade}/{mode}: 'equation'")
                all_passed = False
    
    return all_passed

def main():
    parser = argparse.ArgumentParser(description="homework-solution-guide Skill")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--subject", default="math", help="学科")
    parser.add_argument("--grade", default="7年级", help="年级")
    parser.add_argument("--mode", default="step", help="模式")
    parser.add_argument("--topic", default="测试题目", help="题目")
    
    args = parser.parse_args()
    
    if args.selftest:
        result = selftest()
        sys.exit(0 if result else 1)
    
    spec = load_spec(args.subject, args.grade, args.topic)
    lines = generate_content(spec, args.mode)
    for line in lines:
        print(line)

if __name__ == "__main__":
    main()
