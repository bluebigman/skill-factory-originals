#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞品透视 · 多维对标与差异洞察 Skill
真实可用的竞品分析工具：读取竞品数据文件，输出多维对比报告
支持 CSV / JSON / Markdown / TXT 格式输入
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024

# ============ 数据加载模块 ============

def parse_markdown_table(content):
    """解析 Markdown 表格，返回列表字典"""
    rows = []
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    header_count = None
    for i, line in enumerate(lines):
        if '|' not in line:
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue  # 分隔行
        if not rows:
            rows.append(cells)
            header_count = len(cells)
            continue
        if len(cells) != header_count:
            logger.warning(f"Markdown表格第{i+1}行列数({len(cells)})与表头({header_count})不一致，跳过该行")
            continue
        rows.append(cells)
    if len(rows) < 2:
        return []
    headers = rows[0]
    data = []
    for row in rows[1:]:
        data.append(dict(zip(headers, row)))
    return data


def parse_txt_content(content):
    """解析 TXT 内容，支持 key: value 格式或简单表格"""
    records = []
    current_record = {}
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            if current_record:
                records.append(current_record)
                current_record = {}
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            current_record[key.strip()] = value.strip()
        elif '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                current_record[parts[0].strip()] = parts[1].strip()
    if current_record:
        records.append(current_record)
    return records


def detect_encoding(filepath):
    """检测文件编码"""
    if HAS_CHARDET:
        with open(filepath, 'rb') as f:
            raw_data = f.read(10000)
        result = chardet.detect(raw_data)
        return result['encoding'] or 'utf-8'
    return 'utf-8'


def check_file_size(filepath):
    """检查文件大小"""
    size = os.path.getsize(filepath)
    if size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小({size}字节)超过限制({MAX_FILE_SIZE}字节)，请使用流式处理或分割文件")
    return size


def load_data(filepath):
    """加载竞品数据文件，返回 (竞品名, 数据类型, 记录列表)"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 检查文件大小
    check_file_size(filepath)
    
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)
    # 从文件名提取竞品名（第一个下划线前）
    comp_name = filename.split('_')[0] if '_' in filename else Path(filename).stem
    
    records = []
    data_type = 'unknown'
    
    try:
        if ext == '.csv':
            encoding = detect_encoding(filepath)
            with open(filepath, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                records = list(reader)
            data_type = 'csv'
        elif ext == '.json':
            encoding = detect_encoding(filepath)
            with open(filepath, 'r', encoding=encoding) as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = data.get('records', data.get('data', []))
                    if isinstance(records, dict):
                        records = [records]
            data_type = 'json'
        elif ext == '.md' or ext == '.markdown':
            encoding = detect_encoding(filepath)
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            records = parse_markdown_table(content)
            data_type = 'markdown'
        elif ext == '.txt':
            encoding = detect_encoding(filepath)
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            records = parse_txt_content(content)
            data_type = 'txt'
        elif ext == '.xlsx' and HAS_OPENPYXL:
            wb = openpyxl.load_workbook(filepath, read_only=True)
            ws = wb.active
            headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            for row in ws.iter_rows(min_row=2, values_only=True):
                records.append(dict(zip(headers, row)))
            wb.close()
            data_type = 'xlsx'
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
    except Exception as e:
        raise ValueError(f"解析文件失败: {e}")
    
    if not records:
        raise ValueError("文件中没有有效数据")
    
    return comp_name, data_type, records


# ============ 字段提取模块 ============

def extract_features(record):
    """从记录中提取功能列表"""
    features = []
    for key in ['features', '功能', 'feature', 'capabilities', '能力']:
        if key in record:
            value = record[key]
            if isinstance(value, list):
                features.extend([str(v).strip() for v in value if str(v).strip()])
            elif isinstance(value, str):
                # 支持逗号、分号、换行分隔
                parts = re.split(r'[,;，；\n]', value)
                features.extend([p.strip() for p in parts if p.strip()])
            break
    return features


def extract_pricing(record):
    """从记录中提取定价信息"""
    pricing = {}
    for key in ['price', 'pricing', '价格', '定价', 'cost', '费用']:
        if key in record:
            value = record[key]
            if isinstance(value, dict):
                pricing = value
            elif isinstance(value, (int, float)):
                pricing = {'base': value}
            elif isinstance(value, str):
                # 尝试解析价格字符串
                price_match = re.search(r'[\d.]+', value)
                if price_match:
                    pricing = {'base': float(price_match.group())}
                else:
                    pricing = {'description': value}
            break
    return pricing


def extract_reviews(record):
    """从记录中提取评价信息"""
    reviews = {}
    for key in ['reviews', 'rating', '评价', '评分', 'score', 'rating_score']:
        if key in record:
            value = record[key]
            if isinstance(value, (int, float)):
                reviews = {'rating': float(value)}
            elif isinstance(value, str):
                rating_match = re.search(r'(\d+(?:\.\d+)?)\s*[/分]', value)
                if rating_match:
                    reviews = {'rating': float(rating_match.group(1))}
                else:
                    reviews = {'description': value}
            elif isinstance(value, dict):
                reviews = value
            break
    return reviews


def extract_all_fields(record):
    """提取所有关键字段，返回 (features, pricing, reviews, confidence)"""
    features = extract_features(record)
    pricing = extract_pricing(record)
    reviews = extract_reviews(record)
    
    # 计算置信度
    confidence = 0.5
    if features:
        confidence += 0.2
    if pricing:
        confidence += 0.2
    if reviews:
        confidence += 0.1
    
    return features, pricing, reviews, min(confidence, 1.0)


# ============ 分析模块 ============

def generate_differentiation_suggestions(report):
    """生成差异化建议"""
    suggestions = []
    competitors = report['competitors']
    
    if len(competitors) < 2:
        return suggestions
    
    # 功能差异化建议
    all_features = set()
    for comp in competitors:
        all_features.update(comp['features'])
    
    for feature in sorted(all_features):
        has_feature = [comp['name'] for comp in competitors if feature in comp['features']]
        if len(has_feature) == 1:
            suggestions.append({
                'type': 'unique_feature',
                'feature': feature,
                'competitor': has_feature[0],
                'suggestion': f"{has_feature[0]} 拥有独特功能 '{feature}'，可作为差异化卖点"
            })
        elif len(has_feature) == len(competitors):
            suggestions.append({
                'type': 'common_feature',
                'feature': feature,
                'competitor': None,
                'suggestion': f"所有竞品都支持 '{feature}'，属于基础功能，需考虑差异化升级"
            })
    
    # 定价差异化建议
    prices = {}
    for comp in competitors:
        if 'base' in comp['pricing']:
            prices[comp['name']] = comp['pricing']['base']
    
    if len(prices) >= 2:
        min_price_comp = min(prices, key=prices.get)
        max_price_comp = max(prices, key=prices.get)
        if prices[min_price_comp] < prices[max_price_comp]:
            suggestions.append({
                'type': 'pricing',
                'competitor': min_price_comp,
                'suggestion': f"{min_price_comp} 定价最低 ({prices[min_price_comp]})，可主打性价比"
            })
            suggestions.append({
                'type': 'pricing',
                'competitor': max_price_comp,
                'suggestion': f"{max_price_comp} 定价最高 ({prices[max_price_comp]})，需证明高端价值"
            })
    
    # 评价差异化建议
    ratings = {}
    for comp in competitors:
        if 'avg_rating' in comp['reviews']:
            ratings[comp['name']] = comp['reviews']['avg_rating']
    
    if len(ratings) >= 2:
        max_rating_comp = max(ratings, key=ratings.get)
        min_rating_comp = min(ratings, key=ratings.get)
        if ratings[max_rating_comp] > ratings[min_rating_comp]:
            suggestions.append({
                'type': 'rating',
                'competitor': max_rating_comp,
                'suggestion': f"{max_rating_comp} 评分最高 ({ratings[max_rating_comp]})，可强调用户口碑"
            })
            suggestions.append({
                'type': 'rating',
                'competitor': min_rating_comp,
                'suggestion': f"{min_rating_comp} 评分较低 ({ratings[min_rating_comp]})，需关注用户体验改进"
            })
    
    # 综合建议
    if len(competitors) >= 2:
        # 找出功能最全的竞品
        max_features_comp = max(competitors, key=lambda c: len(c['features']))
        suggestions.append({
            'type': 'comprehensive',
            'competitor': max_features_comp['name'],
            'suggestion': f"{max_features_comp['name']} 功能最全面 ({len(max_features_comp['features'])}项)，可作为功能对标基准"
        })
    
    return suggestions


def analyze_competitors(competitors_data):
    """分析竞品数据，返回对比报告"""
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'competitors': [],
        'comparison': {
            'features': {},
            'pricing': {},
            'reviews': {}
        },
        'differentiation': [],
        'low_confidence_fields': [],
        'data_completeness': {}
    }
    
    all_features = set()
    
    for comp_name, records in competitors_data.items():
        comp_info = {
            'name': comp_name,
            'record_count': len(records),
            'features': [],
            'pricing': {},
            'reviews': {},
            'confidence': 0.0
        }
        
        # 聚合所有记录
        all_comp_features = set()
        all_pricing = {}
        all_reviews = []
        confidences = []
        
        for record in records:
            features, pricing, reviews, confidence = extract_all_fields(record)
            all_comp_features.update(features)
            if pricing:
                all_pricing.update(pricing)
            if reviews:
                all_reviews.append(reviews)
            confidences.append(confidence)
        
        comp_info['features'] = sorted(list(all_comp_features))
        comp_info['pricing'] = all_pricing
        if all_reviews:
            # 计算平均评分
            ratings = [r.get('rating', 0) for r in all_reviews if 'rating' in r]
            if ratings:
                comp_info['reviews'] = {'avg_rating': sum(ratings) / len(ratings), 'count': len(ratings)}
            else:
                comp_info['reviews'] = all_reviews[0]
        
        comp_info['confidence'] = sum(confidences) / len(confidences) if confidences else 0.0
        
        if comp_info['confidence'] < 0.6:
            report['low_confidence_fields'].append({
                'competitor': comp_name,
                'confidence': comp_info['confidence'],
                'reason': '字段提取置信度低于阈值'
            })
        
        all_features.update(comp_info['features'])
        report['competitors'].append(comp_info)
    
    # 功能对比矩阵
    for feature in sorted(all_features):
        report['comparison']['features'][feature] = {
            comp['name']: (feature in comp['features']) for comp in report['competitors']
        }
    
    # 定价对比
    for comp in report['competitors']:
        report['comparison']['pricing'][comp['name']] = comp['pricing']
    
    # 评价对比
    for comp in report['competitors']:
        report['comparison']['reviews'][comp['name']] = comp['reviews']
    
    # 数据完整性检查
    for comp in report['competitors']:
        completeness = {
            'features': len(comp['features']) > 0,
            'pricing': len(comp['pricing']) > 0,
            'reviews': len(comp['reviews']) > 0
        }
        report['data_completeness'][comp['name']] = completeness
        if not all(completeness.values()):
            logger.warning(f"竞品 {comp['name']} 数据不完整: {completeness}")
    
    # 生成差异化建议
    report['differentiation'] = generate_differentiation_suggestions(report)
    
    return report


# ============ 输出模块 ============

def atomic_write(filepath, content):
    """原子化写入文件"""
    dirpath = os.path.dirname(filepath)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(dir=dirpath or '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, filepath)
    except Exception:
        os.unlink(temp_path)
        raise


def print_summary(report):
    """打印控制台摘要"""
    print("\n" + "=" * 60)
    print("竞品分析报告摘要")
    print("=" * 60)
    print(f"生成时间: {report['generated_at']}")
    print(f"竞品数量: {len(report['competitors'])}")
    print(f"差异化建议: {len(report['differentiation'])} 条")
    print(f"低置信度字段: {len(report['low_confidence_fields'])} 个")
    print("\n--- 竞品概览 ---")
    for comp in report['competitors']:
        print(f"  {comp['name']}: {comp['record_count']} 条记录, 置信度 {comp['confidence']:.2f}")
        if comp['features']:
            print(f"    功能 ({len(comp['features'])}): {', '.join(comp['features'][:5])}{'...' if len(comp['features']) > 5 else ''}")
        if comp['pricing']:
            print(f"    定价: {comp['pricing']}")
        if comp['reviews']:
            print(f"    评价: {comp['reviews']}")
    
    if report['differentiation']:
        print("\n--- 差异化建议 ---")
        for diff in report['differentiation']:
            print(f"  [{diff['type']}] {diff['suggestion']}")
    
    if report['low_confidence_fields']:
        print("\n--- 低置信度警告 ---")
        for low in report['low_confidence_fields']:
            print(f"  {low['competitor']}: {low['reason']}")
    
    print("\n--- 数据完整性 ---")
    for comp_name, completeness in report['data_completeness'].items():
        status = "完整" if all(completeness.values()) else "不完整"
        print(f"  {comp_name}: {status}")
    
    print("=" * 60)


# ============ 自检
