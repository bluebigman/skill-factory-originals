#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同审查风险清单核查工具
功能：对合同文本进行风险点审查，输出违约、付款、保密、知产归属的核查意见清单
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from docx import Document
except ImportError:
    Document = None

# 风险规则定义：每个规则包含关键词、风险等级、风险描述、建议
RISK_RULES = {
    "违约": {
        "keywords": ["违约金", "违约责任", "赔偿", "损失"],
        "high_risk": ["违约金.*%", "赔偿.*全部损失", "承担.*一切责任"],
        "medium_risk": ["违约金", "赔偿损失"],
        "low_risk": ["违约责任"],
        "suggestions": {
            "high": "违约金比例过高或责任范围过大，建议协商调整至合理范围",
            "medium": "违约责任约定不够明确，建议明确违约金计算方式和赔偿范围",
            "low": "违约责任条款存在，建议补充具体违约情形和后果"
        }
    },
    "付款": {
        "keywords": ["付款", "支付", "价款", "费用", "定金", "预付款"],
        "high_risk": ["付款.*后.*交货", "先付款.*后.*验收", "一次性.*付款"],
        "medium_risk": ["付款期限", "付款条件"],
        "low_risk": ["付款方式"],
        "suggestions": {
            "high": "付款条件对己方不利，建议增加验收合格后再付款的条款",
            "medium": "付款条款不够明确，建议明确付款时间节点和条件",
            "low": "付款条款存在，建议补充逾期付款的违约责任"
        }
    },
    "保密": {
        "keywords": ["保密", "机密", "商业秘密", "保密义务"],
        "high_risk": ["保密.*无限期", "保密.*永久"],
        "medium_risk": ["保密期限", "保密范围"],
        "low_risk": ["保密协议"],
        "suggestions": {
            "high": "保密期限不合理，建议设定合理期限并明确保密信息范围",
            "medium": "保密条款不够完善，建议补充保密期限、范围和违约责任",
            "low": "保密条款存在，建议明确保密信息的定义和例外情形"
        }
    },
    "知识产权": {
        "keywords": ["知识产权", "著作权", "专利", "商标", "版权", "归属"],
        "high_risk": ["知识产权.*归.*甲方", "成果.*归.*甲方"],
        "medium_risk": ["知识产权归属", "许可使用"],
        "low_risk": ["知识产权"],
        "suggestions": {
            "high": "知识产权归属约定对己方不利，建议协商共同拥有或明确使用许可",
            "medium": "知识产权条款不够明确，建议明确成果归属和使用权限",
            "low": "知识产权条款存在，建议补充侵权责任承担和许可范围"
        }
    }
}

def extract_text_from_file(filepath):
    """从文件中提取文本内容"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    suffix = path.suffix.lower()
    
    if suffix in ['.txt', '.md']:
        try:
            return path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return path.read_text(encoding='gbk')
    
    elif suffix == '.docx':
        if Document is None:
            raise ImportError("处理 .docx 文件需要安装 python-docx，请执行: pip install python-docx")
        doc = Document(path)
        return '\n'.join([para.text for para in doc.paragraphs])
    
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，仅支持 .txt、.md、.docx")

def analyze_contract(text):
    """分析合同文本，返回风险清单"""
    risks = []
    
    for category, rules in RISK_RULES.items():
        # 检查是否包含该类别的关键词
        has_keywords = any(kw in text for kw in rules["keywords"])
        if not has_keywords:
            risks.append({
                "category": category,
                "level": "中",
                "title": f"{category}条款缺失",
                "detail": f"合同未包含{category}相关条款",
                "suggestion": f"建议补充{category}条款"
            })
            continue
        
        # 检查高风险模式
        high_matches = []
        for pattern in rules["high_risk"]:
            matches = re.findall(pattern, text)
            if matches:
                high_matches.extend(matches)
        
        if high_matches:
            risks.append({
                "category": category,
                "level": "高",
                "title": f"{category}条款存在高风险",
                "detail": f"发现高风险表述: {'; '.join(high_matches[:3])}",
                "suggestion": rules["suggestions"]["high"]
            })
            continue
        
        # 检查中风险模式
        medium_matches = []
        for pattern in rules["medium_risk"]:
            matches = re.findall(pattern, text)
            if matches:
                medium_matches.extend(matches)
        
        if medium_matches:
            risks.append({
                "category": category,
                "level": "中",
                "title": f"{category}条款需完善",
                "detail": f"发现需完善的表述: {'; '.join(medium_matches[:3])}",
                "suggestion": rules["suggestions"]["medium"]
            })
            continue
        
        # 低风险
        risks.append({
            "category": category,
            "level": "低",
            "title": f"{category}条款基本合规",
            "detail": "条款存在但需人工复核",
            "suggestion": rules["suggestions"]["low"]
        })
    
    return risks

def format_output(risks, format_type='text'):
    """格式化输出结果"""
    if format_type == 'json':
        return json.dumps(risks, ensure_ascii=False, indent=2)
    
    # 文本格式输出
    lines = []
    lines.append("=" * 60)
    lines.append("合同审查风险清单")
    lines.append("=" * 60)
    
    for risk in risks:
        lines.append(f"\n【{risk['category']}】风险等级: {risk['level']}")
        lines.append(f"风险点: {risk['title']}")
        lines.append(f"详情: {risk['detail']}")
        lines.append(f"建议: {risk['suggestion']}")
        lines.append("-" * 40)
    
    return '\n'.join(lines)

def selftest():
    """自检函数，验证核心功能"""
    print("运行自检...")
    
    # 测试文本
    test_text = """
    本合同约定，甲方应于合同签订后30日内支付乙方合同总价款的30%作为预付款。
    若甲方逾期付款，每逾期一日需支付合同总价款0.5%的违约金。
    乙方应保守甲方的商业秘密，保密期限为合同终止后3年。
    项目开发过程中产生的知识产权归甲方所有。
    """
    
    # 执行分析
    risks = analyze_contract(test_text)
    
    # 验证结果
    assert len(risks) == 4, f"预期4个风险项，实际{len(risks)}个"
    
    # 验证各类别都有结果
    categories = [r['category'] for r in risks]
    assert '违约' in categories, "缺少违约条款分析"
    assert '付款' in categories, "缺少付款条款分析"
    assert '保密' in categories, "缺少保密条款分析"
    assert '知识产权' in categories, "缺少知识产权条款分析"
    
    # 验证输出格式
    output = format_output(risks)
    assert '风险等级' in output, "输出格式错误"
    
    print("✓ 自检通过：所有功能正常")
    return True

def main():
    parser = argparse.ArgumentParser(
        description='合同审查风险清单核查工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s --input contract.txt --output result.txt
  %(prog)s --input contract.docx --format json
  %(prog)s --selftest
        '''
    )
    
    parser.add_argument('--input', '-i', help='输入合同文件路径（支持 .txt/.md/.docx）')
    parser.add_argument('--output', '-o', help='输出结果文件路径')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text', help='输出格式')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
    
    # 检查必要参数
    if not args.input:
        parser.error("必须指定 --input 参数")
    
    try:
        # 读取文件
        print(f"正在读取文件: {args.input}")
        text = extract_text_from_file(args.input)
        print(f"成功读取 {len(text)} 字符")
        
        # 分析合同
        print("正在分析合同风险...")
        risks = analyze_contract(text)
        
        # 生成输出
        output = format_output(risks, args.format)
        
        # 输出结果
        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f"结果已保存至: {args.output}")
        else:
            print(output)
        
        # 统计信息
        high_count = sum(1 for r in risks if r['level'] == '高')
        medium_count = sum(1 for r in risks if r['level'] == '中')
        low_count = sum(1 for r in risks if r['level'] == '低')
        print(f"\n统计: 高风险 {high_count} 项, 中风险 {medium_count} 项, 低风险 {low_count} 项")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期的错误: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
