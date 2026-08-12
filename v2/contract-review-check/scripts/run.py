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
from functools import lru_cache
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

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
                "id": "breach_high_1",
                "pattern": r"违约金[^。；;]*?(\d+(?:\.\d+)?)\s*%",
                "description": "违约金比例过高",
                "check": lambda m: float(m.group(1)) > 30,
                "suggestion": "违约金比例超过30%，建议协商调整至合理范围（通常不超过30%）"
            },
            {
                "id": "breach_high_2",
                "pattern": r"赔偿[^。；;]*?全部损失",
                "description": "赔偿范围过大",
                "check": lambda m: True,
                "suggestion": "赔偿范围约定为全部损失，建议明确赔偿范围和上限"
            },
            {
                "id": "breach_high_3",
                "pattern": r"承担[^。；;]*?一切责任",
                "description": "责任范围过大",
                "check": lambda m: True,
                "suggestion": "责任范围约定为一切责任，建议明确责任边界和例外情形"
            }
        ],
        "medium_risk": [
            {
                "id": "breach_medium_1",
                "pattern": r"违约金[^。；;]*?(\d+(?:\.\d+)?)\s*%",
                "description": "违约金比例需关注",
                "check": lambda m: 10 <= float(m.group(1)) <= 30,
                "suggestion": "违约金比例在10%-30%之间，建议根据实际损失评估合理性"
            },
            {
                "id": "breach_medium_2",
                "pattern": r"赔偿损失",
                "description": "赔偿约定不明确",
                "check": lambda m: True,
                "suggestion": "赔偿损失约定不够明确，建议明确赔偿计算方式和范围"
            }
        ],
        "low_risk": [
            {
                "id": "breach_low_1",
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
                "id": "payment_high_1",
                "pattern": r"付款[^。；;]*?后[^。；;]*?交货",
                "description": "付款后交货风险",
                "check": lambda m: True,
                "suggestion": "付款后交货存在风险，建议增加交货验收后再付款的条款"
            },
            {
                "id": "payment_high_2",
                "pattern": r"先付款[^。；;]*?后[^。；;]*?验收",
                "description": "先付款后验收风险",
                "check": lambda m: True,
                "suggestion": "先付款后验收对己方不利，建议增加验收合格后再付款的条款"
            },
            {
                "id": "payment_high_3",
                "pattern": r"一次性[^。；;]*?付款",
                "description": "一次性付款风险",
                "check": lambda m: True,
                "suggestion": "一次性付款风险较高，建议分期付款并设置付款条件"
            }
        ],
        "medium_risk": [
            {
                "id": "payment_medium_1",
                "pattern": r"付款期限",
                "description": "付款期限约定",
                "check": lambda m: True,
                "suggestion": "付款期限约定不够明确，建议明确具体付款时间节点"
            },
            {
                "id": "payment_medium_2",
                "pattern": r"付款条件",
                "description": "付款条件约定",
                "check": lambda m: True,
                "suggestion": "付款条件约定不够明确，建议明确付款条件和验收标准"
            }
        ],
        "low_risk": [
            {
                "id": "payment_low_1",
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
                "id": "confidential_high_1",
                "pattern": r"保密[^。；;]*?无限期",
                "description": "保密期限无限期",
                "check": lambda m: True,
                "suggestion": "保密期限约定为无限期不合理，建议设定合理期限（通常3-5年）"
            },
            {
                "id": "confidential_high_2",
                "pattern": r"保密[^。；;]*?永久",
                "description": "保密期限永久",
                "check": lambda m: True,
                "suggestion": "保密期限约定为永久不合理，建议设定合理期限并明确保密信息范围"
            }
        ],
        "medium_risk": [
            {
                "id": "confidential_medium_1",
                "pattern": r"保密期限",
                "description": "保密期限约定",
                "check": lambda m: True,
                "suggestion": "保密期限约定不够明确，建议明确具体保密期限"
            },
            {
                "id": "confidential_medium_2",
                "pattern": r"保密范围",
                "description": "保密范围约定",
                "check": lambda m: True,
                "suggestion": "保密范围约定不够明确，建议明确保密信息的定义和范围"
            }
        ],
        "low_risk": [
            {
                "id": "confidential_low_1",
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
                "id": "ip_high_1",
                "pattern": r"知识产权[^。；;]*?归[^。；;]*?甲方",
                "description": "知识产权归甲方",
                "check": lambda m: True,
                "suggestion": "知识产权归属约定对己方不利，建议协商共同拥有或明确使用许可"
            },
            {
                "id": "ip_high_2",
                "pattern": r"成果[^。；;]*?归[^。；;]*?甲方",
                "description": "成果归甲方",
                "check": lambda m: True,
                "suggestion": "成果归属约定对己方不利，建议协商共同拥有或明确使用许可"
            }
        ],
        "medium_risk": [
            {
                "id": "ip_medium_1",
                "pattern": r"知识产权归属",
                "description": "知识产权归属约定",
                "check": lambda m: True,
                "suggestion": "知识产权归属约定不够明确，建议明确成果归属和使用权限"
            },
            {
                "id": "ip_medium_2",
                "pattern": r"许可使用",
                "description": "许可使用约定",
                "check": lambda m: True,
                "suggestion": "许可使用条款不够明确，建议明确许可范围、期限和费用"
            }
        ],
        "low_risk": [
            {
                "id": "ip_low_1",
                "pattern": r"知识产权",
                "description": "知识产权条款存在",
                "check": lambda m: True,
                "suggestion": "知识产权条款存在，建议补充侵权责任承担和许可范围"
            }
        ]
    }
}

def _normalize_text(text: str) -> str:
    """统一文本规范化：全角转半角、统一标点符号"""
    if not text:
        return text
    
    # 全角转半角映射表
    fullwidth_map = {
        '，': ',', '。': '.', '；': ';', '：': ':', '？': '?', '！': '!',
        '（': '(', '）': ')', '【': '[', '】': ']', '《': '<', '》': '>',
        '“': '"', '”': '"', '‘': "'", '’': "'", '、': ',', '％': '%',
        '　': ' ', '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }
    
    # 全角转半角
    normalized = text.translate(str.maketrans(fullwidth_map))
    
    # 统一中英文标点（将英文标点也统一为半角）
    # 确保所有标点都是半角形式
    normalized = normalized.replace('，', ',').replace('。', '.').replace('；', ';')
    normalized = normalized.replace('：', ':').replace('？', '?').replace('！', '!')
    normalized = normalized.replace('（', '(').replace('）', ')').replace('【', '[')
    normalized = normalized.replace('】', ']').replace('《', '<').replace('》', '>')
    normalized = normalized.replace('“', '"').replace('”', '"').replace('‘', "'")
    normalized = normalized.replace('’', "'").replace('、', ',').replace('％', '%')
    
    return normalized

def _compile_rules() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """预编译所有正则表达式"""
    compiled = {}
    for category, rules in RISK_RULES.items():
        compiled[category] = {
            'high': [{
                'id': r['id'],
                'pattern': re.compile(r['pattern']),
                'description': r['description'],
                'check': r['check'],
                'suggestion': r['suggestion']
            } for r in rules['high_risk']],
            'medium': [{
                'id': r['id'],
                'pattern': re.compile(r['pattern']),
                'description': r['description'],
                'check': r['check'],
                'suggestion': r['suggestion']
            } for r in rules['medium_risk']],
            'low': [{
                'id': r['id'],
                'pattern': re.compile(r['pattern']),
                'description': r['description'],
                'check': r['check'],
                'suggestion': r['suggestion']
            } for r in rules['low_risk']]
        }
    return compiled

_COMPILED_RULES = _compile_rules()

@lru_cache(maxsize=128)
def _cached_analyze(text: str) -> Tuple[tuple, tuple]:
    """带缓存的文本分析，返回可哈希的结果"""
    risks = analyze_contract_internal(text)
    # 转换为可哈希的元组
    risk_tuples = tuple(
        (r['category'], r['level'], r['title'], r['detail'], r['suggestion'])
        for r in risks
    )
    return risk_tuples, ()

def _analyze_category(category: str, normalized_text: str, matched_positions: set) -> Optional[Dict[str, str]]:
    """分析单个类别（用于并行化）"""
    rules = RISK_RULES[category]
    
    # 检查是否包含该类别的关键词
    has_keywords = any(kw in normalized_text for kw in rules["keywords"])
    if not has_keywords:
        return {
            "category": category,
            "level": "中",
            "title": f"{category}条款缺失",
            "detail": f"合同未包含{category}相关条款",
            "suggestion": f"建议补充{category}条款"
        }
    
    # 检查高风险模式（语义判断）
    high_found = False
    high_details = []
    for rule in _COMPILED_RULES[category]['high']:
        for match in rule['pattern'].finditer(normalized_text):
            # 检查是否已匹配过该位置
            pos_key = (category, 'high', rule['id'], match.start())
            if pos_key in matched_positions:
                continue
            # 安全调用check，捕获可能的异常
            try:
                if rule['check'](match):
                    high_found = True
                    high_details.append(f"{rule['description']}: {match.group(0)[:50]}")
                    matched_positions.add(pos_key)
                    break
            except (IndexError, ValueError) as e:
                # 正则匹配组不存在或转换失败，跳过该规则
                print(f"规则 {rule['id']} 匹配异常: {e}")
                continue
    
    if high_found:
        return {
            "category": category,
            "level": "高",
            "title": f"{category}条款存在高风险",
            "detail": f"发现高风险表述: {'; '.join(high_details[:3])}",
            "suggestion": rules["high_risk"][0]["suggestion"]
        }
    
    # 检查中风险模式（语义判断）
    medium_found = False
    medium_details = []
    for rule in _COMPILED_RULES[category]['medium']:
        for match in rule['pattern'].finditer(normalized_text):
            # 检查是否已匹配过该位置
            pos_key = (category, 'medium', rule['id'], match.start())
            if pos_key in matched_positions:
                continue
            # 安全调用check，捕获可能的异常
            try:
                if rule['check'](match):
                    medium_found = True
                    medium_details.append(f"{rule['description']}: {match.group(0)[:50]}")
                    matched_positions.add(pos_key)
                    break
            except (IndexError, ValueError) as e:
                # 正则匹配组不存在或转换失败，跳过该规则
                print(f"规则 {rule['id']} 匹配异常: {e}")
                continue
    
    if medium_found:
        return {
            "category": category,
            "level": "中",
            "title": f"{category}条款需完善",
            "detail": f"发现需完善的表述: {'; '.join(medium_details[:3])}",
            "suggestion": rules["medium_risk"][0]["suggestion"]
        }
    
    # 低风险
    return {
        "category": category,
        "level": "低",
        "title": f"{category}条款基本合规",
        "detail": "条款存在但需人工复核",
        "suggestion": rules["low_risk"][0]["suggestion"]
    }

def analyze_contract_internal(text: str) -> List[Dict[str, str]]:
    """分析合同文本，返回风险清单（内部实现，支持并行化）"""
    # 规范化文本
    normalized_text = _normalize_text(text)
    
    # 使用线程池并行分析各个类别
    matched_positions = set()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_analyze_category, category, normalized_text, matched_positions)
            for category in RISK_RULES.keys()
        ]
        risks = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # 按类别顺序排序结果
    category_order = list(RISK_RULES.keys())
    risks.sort(key=lambda r: category_order.index(r['category']))
    
    return risks

def analyze_contract(text: str) -> List[Dict[str, str]]:
    """分析合同文本，返回风险清单（带缓存）"""
    # 使用缓存
    risk_tuples, _ = _cached_analyze(text)
    return [
        {
            "category": r[0],
            "level": r[1],
            "title": r[2],
            "detail": r[3],
            "suggestion": r[4]
        }
        for r in risk_tuples
    ]

def _extract_docx_zipfile(path: Path) -> str:
    """使用zipfile降级提取docx文本"""
    try:
        with zipfile.ZipFile(path, 'r') as z:
            # 读取document.xml
            with z.open('word/document.xml') as f:
                content = f.read().decode('utf-8')
            
            # 提取段落文本
            import xml.etree.ElementTree as ET
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            root = ET.fromstring(content)
            
            texts = []
            for para in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                para_text = ''
                for run in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if run.text:
                        para_text += run.text
                if para_text.strip():
                    texts.append(para_text.strip())
            
            return '\n'.join(texts)
    except Exception as e:
        raise ValueError(f"docx文件解析失败: {e}")

def extract_text_from_file(filepath: str) -> str:
    """从文件中提取文本内容，支持txt/md/docx格式，含异常处理和降级策略"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
