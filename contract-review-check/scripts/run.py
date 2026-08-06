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
import time
import zipfile
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    from docx import Document
except ImportError:
    Document = None

# 风险规则定义：基于条款语义的规则引擎
RISK_RULES = {
    "违约": {
        "keywords": ["违约金", "违约责任", "赔偿", "损失"],
        "high_risk": [
            {
                "pattern": r"违约金[^。；]*?(\d+(?:\.\d+)?)\s*%",
                "description": "违约金比例过高",
                "check": lambda m: float(m.group(1)) > 30,
                "suggestion": "违约金比例超过30%，建议协商调整至合理范围（通常不超过30%）"
            },
            {
                "pattern": r"赔偿[^。；]*?全部损失",
                "description": "赔偿范围过大",
                "check": lambda m: True,
                "suggestion": "赔偿范围约定为全部损失，建议明确赔偿范围和上限"
            },
            {
                "pattern": r"承担[^。；]*?一切责任",
                "description": "责任范围过大",
                "check": lambda m: True,
                "suggestion": "责任范围约定为一切责任，建议明确责任边界和例外情形"
            }
        ],
        "medium_risk": [
            {
                "pattern": r"违约金[^。；]*?(\d+(?:\.\d+)?)\s*%",
                "description": "违约金比例需关注",
                "check": lambda m: 10 <= float(m.group(1)) <= 30,
                "suggestion": "违约金比例在10%-30%之间，建议根据实际损失评估合理性"
            },
            {
                "pattern": r"赔偿损失",
                "description": "赔偿约定不明确",
                "check": lambda m: True,
                "suggestion": "赔偿损失约定不够明确，建议明确赔偿计算方式和范围"
            }
        ],
        "low_risk": [
            {
                "pattern": r"违约责任",
                "description": "违约责任条款存在",
                "check": lambda m: True,
                "suggestion": "违约责任条款存在，建议补充具体违约情形和后果"
            }
        ]
    },
    "付款": {
        "keywords": ["付款", "支付", "价款", "费用", "定金", "预付款"],
        "high_risk": [
            {
                "pattern": r"付款[^。；]*?后[^。；]*?交货",
                "description": "付款后交货风险",
                "check": lambda m: True,
                "suggestion": "付款后交货存在风险，建议增加交货验收后再付款的条款"
            },
            {
                "pattern": r"先付款[^。；]*?后[^。；]*?验收",
                "description": "先付款后验收风险",
                "check": lambda m: True,
                "suggestion": "先付款后验收对己方不利，建议增加验收合格后再付款的条款"
            },
            {
                "pattern": r"一次性[^。；]*?付款",
                "description": "一次性付款风险",
                "check": lambda m: True,
                "suggestion": "一次性付款风险较高，建议分期付款并设置付款条件"
            }
        ],
        "medium_risk": [
            {
                "pattern": r"付款期限",
                "description": "付款期限约定",
                "check": lambda m: True,
                "suggestion": "付款期限约定不够明确，建议明确具体付款时间节点"
            },
            {
                "pattern": r"付款条件",
                "description": "付款条件约定",
                "check": lambda m: True,
                "suggestion": "付款条件约定不够明确，建议明确付款条件和验收标准"
            }
        ],
        "low_risk": [
            {
                "pattern": r"付款方式",
                "description": "付款方式约定",
                "check": lambda m: True,
                "suggestion": "付款方式条款存在，建议补充逾期付款的违约责任"
            }
        ]
    },
    "保密": {
        "keywords": ["保密", "机密", "商业秘密", "保密义务"],
        "high_risk": [
            {
                "pattern": r"保密[^。；]*?无限期",
                "description": "保密期限无限期",
                "check": lambda m: True,
                "suggestion": "保密期限约定为无限期不合理，建议设定合理期限（通常3-5年）"
            },
            {
                "pattern": r"保密[^。；]*?永久",
                "description": "保密期限永久",
                "check": lambda m: True,
                "suggestion": "保密期限约定为永久不合理，建议设定合理期限并明确保密信息范围"
            }
        ],
        "medium_risk": [
            {
                "pattern": r"保密期限",
                "description": "保密期限约定",
                "check": lambda m: True,
                "suggestion": "保密期限约定不够明确，建议明确具体保密期限"
            },
            {
                "pattern": r"保密范围",
                "description": "保密范围约定",
                "check": lambda m: True,
                "suggestion": "保密范围约定不够明确，建议明确保密信息的定义和范围"
            }
        ],
        "low_risk": [
            {
                "pattern": r"保密协议",
                "description": "保密协议存在",
                "check": lambda m: True,
                "suggestion": "保密条款存在，建议明确保密信息的定义和例外情形"
            }
        ]
    },
    "知识产权": {
        "keywords": ["知识产权", "著作权", "专利", "商标", "版权", "归属"],
        "high_risk": [
            {
                "pattern": r"知识产权[^。；]*?归[^。；]*?甲方",
                "description": "知识产权归甲方",
                "check": lambda m: True,
                "suggestion": "知识产权归属约定对己方不利，建议协商共同拥有或明确使用许可"
            },
            {
                "pattern": r"成果[^。；]*?归[^。；]*?甲方",
                "description": "成果归甲方",
                "check": lambda m: True,
                "suggestion": "成果归属约定对己方不利，建议协商共同拥有或明确使用许可"
            }
        ],
        "medium_risk": [
            {
                "pattern": r"知识产权归属",
                "description": "知识产权归属约定",
                "check": lambda m: True,
                "suggestion": "知识产权归属约定不够明确，建议明确成果归属和使用权限"
            },
            {
                "pattern": r"许可使用",
                "description": "许可使用约定",
                "check": lambda m: True,
                "suggestion": "许可使用条款不够明确，建议明确许可范围、期限和费用"
            }
        ],
        "low_risk": [
            {
                "pattern": r"知识产权",
                "description": "知识产权条款存在",
                "check": lambda m: True,
                "suggestion": "知识产权条款存在，建议补充侵权责任承担和许可范围"
            }
        ]
    }
}

def _compile_rules() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """预编译所有正则表达式"""
    compiled = {}
    for category, rules in RISK_RULES.items():
        compiled[category] = {
            'high': [{
                'pattern': re.compile(r['pattern']),
                'description': r['description'],
                'check': r['check'],
                'suggestion': r['suggestion']
            } for r in rules['high_risk']],
            'medium': [{
                'pattern': re.compile(r['pattern']),
                'description': r['description'],
                'check': r['check'],
                'suggestion': r['suggestion']
            } for r in rules['medium_risk']],
            'low': [{
                'pattern': re.compile(r['pattern']),
                'description': r['description'],
                'check': r['check'],
                'suggestion': r['suggestion']
            } for r in rules['low_risk']]
        }
    return compiled

_COMPILED_RULES = _compile_rules()

def extract_text_from_file(filepath: str) -> str:
    """从文件中提取文本内容，支持txt/md/docx格式，含异常处理和降级策略"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 检查文件大小（限制为50MB）
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"文件过大（{file_size/1024/1024:.1f}MB），超过50MB限制")
    
    suffix = path.suffix.lower()
    
    if suffix in ['.txt', '.md']:
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError(f"文件编码无法识别，请转换为UTF-8或GBK编码")
    
    elif suffix == '.docx':
        # 优先使用python-docx
        if Document is not None:
            try:
                doc = Document(path)
                texts = [para.text for para in doc.paragraphs if para.text.strip()]
                
                # 提取表格文本
                for table in doc.tables:
                    for row in table.rows:
                        row_texts = []
                        for cell in row.cells:
                            if cell.text.strip():
                                row_texts.append(cell.text.strip())
                        if row_texts:
                            texts.append(' | '.join(row_texts))
                
                return '\n'.join(texts)
            except Exception as e:
                # 降级到zipfile提取
                print(f"python-docx解析失败，尝试降级方案: {e}")
                try:
                    return _extract_docx_zipfile(path)
                except Exception as e2:
                    raise ValueError(f"docx文件解析失败: {e2}")
        else:
            # 直接使用zipfile降级方案
            try:
                return _extract_docx_zipfile(path)
            except Exception as e:
                raise ValueError(f"docx文件解析失败: {e}")
    
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，仅支持 .txt、.md、.docx")

def _extract_docx_zipfile(path: Path) -> str:
    """使用zipfile提取docx中的document.xml文本"""
    try:
        with zipfile.ZipFile(path, 'r') as z:
            # 检查文件是否损坏
            if z.testzip() is not None:
                raise ValueError("docx文件损坏")
            
            # 提取document.xml
            if 'word/document.xml' not in z.namelist():
                raise ValueError("docx文件缺少document.xml")
            
            with z.open('word/document.xml') as f:
                content = f.read().decode('utf-8')
            
            # 提取文本内容
            # 移除XML标签，保留文本
            text = re.sub(r'<[^>]+>', ' ', content)
            # 清理多余空白
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 按段落分割
            paragraphs = re.findall(r'<w:p[^>]*>(.*?)</w:p>', content, re.DOTALL)
            texts = []
            for para in paragraphs:
                # 提取每个段落中的文本
                para_text = re.sub(r'<[^>]+>', '', para)
                para_text = re.sub(r'\s+', ' ', para_text).strip()
                if para_text:
                    texts.append(para_text)
            
            return '\n'.join(texts) if texts else text
    except zipfile.BadZipFile:
        raise ValueError("docx文件格式错误")
    except Exception as e:
        raise ValueError(f"docx文件解析失败: {e}")

def analyze_contract(text: str) -> List[Dict[str, str]]:
    """分析合同文本，返回风险清单（基于语义规则引擎）"""
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
        
        # 检查高风险模式（语义判断）
        high_found = False
        high_details = []
        for rule in _COMPILED_RULES[category]['high']:
            for match in rule['pattern'].finditer(text):
                if rule['check'](match):
                    high_found = True
                    high_details.append(f"{rule['description']}: {match.group(0)[:50]}")
                    break
        
        if high_found:
            risks.append({
                "category": category,
                "level": "高",
                "title": f"{category}条款存在高风险",
                "detail": f"发现高风险表述: {'; '.join(high_details[:3])}",
                "suggestion": rules["high_risk"][0]["suggestion"]
            })
            continue
        
        # 检查中风险模式（语义判断）
        medium_found = False
        medium_details = []
        for rule in _COMPILED_RULES[category]['medium']:
            for match in rule['pattern'].finditer(text):
                if rule['check'](match):
                    medium_found = True
                    medium_details.append(f"{rule['description']}: {match.group(0)[:50]}")
                    break
        
        if medium_found:
            risks.append({
                "category": category,
                "level": "中",
                "title": f"{category}条款需完善",
                "detail": f"发现需完善的表述: {'; '.join(medium_details[:3])}",
                "suggestion": rules["medium_risk"][0]["suggestion"]
            })
            continue
        
        # 低风险
        risks.append({
            "category": category,
            "level": "低",
            "title": f"{category}条款基本合规",
            "detail": "条款存在但需人工复核",
            "suggestion": rules["low_risk"][0]["suggestion"]
        })
    
    return risks

def format_output(risks: List[Dict[str, str]], format_type: str = 'text') -> str:
    """格式化输出结果"""
    if format_type == 'json':
        return json.dumps(risks, ensure_ascii=False, indent=2)
    
    # 文本格式输出
    lines = []
    lines.append("=" * 60)
    lines.append("合同审查风险清单")
    lines.append(f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("=" * 60)
    
    for risk in risks:
        lines.append(f"\n【{risk['category']}】风险等级: {risk['level']}")
        lines.append(f"风险点: {risk['title']}")
        lines.append(f"详情: {risk['detail']}")
        lines.append(f"建议: {risk['suggestion']}")
        lines.append("-" * 40)
    
    return '\n'.join(lines)

def selftest() -> bool:
    """自检函数，真实调用核心功能并验证输出"""
    print("运行自检...")
    
    # 测试用例1：包含所有风险类别的文本（含高风险）
    test_text = """
    本合同约定，甲方应于合同签订后30日内支付乙方合同总价款的30%作为预付款。
    若甲方逾期付款，每逾期一日需支付合同总价款35%的违约金。
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
    
    # 验证高风险识别（违约金35% > 30%阈值）
    breach_risk = [r for r in risks if r['category'] == '违约'][0]
    assert breach_risk['level'] == '高', f"违约金35%应识别为高风险，实际为{breach_risk['level']}"
    
    # 验证输出格式
    output = format_output(risks)
    assert '风险等级' in output, "输出格式错误"
    assert '生成时间' in output, "输出缺少时间戳"
    
    # 测试用例2：中风险场景（违约金20%）
    test_text2 = """
    本合同约定，若乙方违约，需支付合同总金额20%的违约金。
    付款方式为分期付款，每期付款前需验收合格。
    保密期限为合同终止后5年。
    知识产权归属双方协商确定。
    """
    risks2 = analyze_contract(test_text2)
    breach_risk2 = [r for r in risks2 if r['category'] == '违约'][0]
    assert breach_risk2['level'] == '中', f"违约金20%应识别为中风险，实际为{breach_risk2['level']}"
    
    # 测试用例3：缺失条款的文本
    test_text3 = "这是一份简单的采购合同，仅包含基本的货物描述和价格。"
    risks3
