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
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ============ 数据加载模块 ============

def parse_markdown_table(content):
    """解析 Markdown 表格，返回列表字典"""
    rows = []
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    for i, line in enumerate(lines):
        if '|' not in line:
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue  # 分隔行
        if not rows:
            rows.append(cells)
            continue
        if len(cells) == len(rows[0]):
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


def load_data(filepath):
    """加载竞品数据文件，返回 (竞品名, 数据类型, 记录列表)"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)
    # 从文件名提取竞品名（第一个下划线前）
    comp_name = filename.split('_')[0] if '_' in filename else Path(filename).stem
    
    records = []
    data_type = 'unknown'
    
    try:
        if ext == '.csv':
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                records = list(reader)
            data_type = 'csv'
        elif ext == '.json':
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = data.get('records', data.get('data', []))
                    if isinstance(records, dict):
                        records = [records]
            data_type = 'json'
        elif ext == '.md' or ext == '.markdown':
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            records = parse_markdown_table(content)
            data_type = 'markdown'
        elif ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
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
        'low_confidence_fields': []
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
    
    # 差异化分析
    if len(report['competitors']) >= 2:
        # 找出独特功能
        for feature in sorted(all_features):
            has_feature = [comp['name'] for comp in report['competitors'] if feature in comp['features']]
            if len(has_feature) == 1:
                report['differentiation'].append({
                    'type': 'unique_feature',
                    'feature': feature,
                    'competitor': has_feature[0],
                    'suggestion': f"{has_feature[0]} 拥有独特功能 '{feature}'，可作为差异化卖点"
                })
        
        # 定价对比建议
        prices = {}
        for comp in report['competitors']:
            if 'base' in comp['pricing']:
                prices[comp['name']] = comp['pricing']['base']
        
        if len(prices) >= 2:
            min_price_comp = min(prices, key=prices.get)
            max_price_comp = max(prices, key=prices.get)
            if prices[min_price_comp] < prices[max_price_comp]:
                report['differentiation'].append({
                    'type': 'pricing',
                    'competitor': min_price_comp,
                    'suggestion': f"{min_price_comp} 定价最低 ({prices[min_price_comp]})，可主打性价比"
                })
                report['differentiation'].append({
                    'type': 'pricing',
                    'competitor': max_price_comp,
                    'suggestion': f"{max_price_comp} 定价最高 ({prices[max_price_comp]})，需证明高端价值"
                })
    
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
    
    print("=" * 60)


# ============ 自检模块 ============

def run_selftest():
    """运行自检，验证核心功能"""
    print("运行自检...")
    
    # 创建临时测试文件
    test_dir = tempfile.mkdtemp(prefix='competitor_selftest_')
    
    # 测试数据
    test_data = [
        {
            'name': 'TestProductA',
            'features': '搜索,推荐,分析',
            'price': '99元/月',
            'rating': '4.5分'
        },
        {
            'name': 'TestProductB',
            'features': '搜索,推荐,报告',
            'price': '199元/月',
            'rating': '4.2分'
        }
    ]
    
    # 写入测试文件
    csv_path = os.path.join(test_dir, 'TestProductA_data.csv')
    with open(csv_path, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'features', 'price', 'rating'])
        writer.writeheader()
        writer.writerow(test_data[0])
    
    json_path = os.path.join(test_dir, 'TestProductB_data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'records': [test_data[1]]}, f, ensure_ascii=False)
    
    # 测试加载
    comp_name, data_type, records = load_data(csv_path)
    assert comp_name == 'TestProductA', f"竞品名提取失败: {comp_name}"
    assert data_type == 'csv', f"数据类型识别失败: {data_type}"
    assert len(records) == 1, f"记录数错误: {len(records)}"
    
    comp_name2, data_type2, records2 = load_data(json_path)
    assert comp_name2 == 'TestProductB', f"竞品名提取失败: {comp_name2}"
    assert data_type2 == 'json', f"数据类型识别失败: {data_type2}"
    assert len(records2) == 1, f"记录数错误: {len(records2)}"
    
    # 测试字段提取
    features, pricing, reviews, confidence = extract_all_fields(test_data[0])
    assert '搜索' in features, f"功能提取失败: {features}"
    assert 'base' in pricing, f"定价提取失败: {pricing}"
    assert 'rating' in reviews, f"评价提取失败: {reviews}"
    assert confidence > 0.5, f"置信度计算错误: {confidence}"
    
    # 测试分析
    competitors_data = {
        'TestProductA': records,
        'TestProductB': records2
    }
    report = analyze_competitors(competitors_data)
    assert len(report['competitors']) == 2, f"竞品数量错误: {len(report['competitors'])}"
    assert len(report['differentiation']) > 0, "差异化建议为空"
    
    # 测试输出
    output_path = os.path.join(test_dir, 'test_output.json')
    atomic_write(output_path, json.dumps(report, ensure_ascii=False, indent=2))
    assert os.path.exists(output_path), "输出文件未创建"
    
    # 清理
    import shutil
    shutil.rmtree(test_dir)
    
    print("自检通过 ✓")
    return 0


# ============ 主函数 ============

def main():
    parser = argparse.ArgumentParser(
        description='竞品透视 · 多维对标与差异洞察工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input compA.csv compB.json
  python run.py --input compA.csv --output-dir ./results --prefix my_analysis
  python run.py --selftest
        """
    )
    parser.add_argument('--input', '-i', nargs='+', required=False,
                       help='输入文件路径，可多个，空格分隔')
    parser.add_argument('--output-dir', '-o', default='./output',
                       help='输出目录 (默认: ./output)')
    parser.add_argument('--prefix', '-p', default='competitor_analysis',
                       help='输出文件名前缀 (默认: competitor_analysis)')
    parser.add_argument('--selftest', action='store_true',
                       help='运行自检并退出')
    
    args = parser.parse_args()
    
    if args.selftest:
        sys.exit(run_selftest())
    
    if not args.input:
        parser.error("必须提供至少一个输入文件，或使用 --selftest 运行自检")
    
    # 加载所有竞品数据
    competitors_data = {}
    errors = []
    
    for filepath in args.input:
        try:
            comp_name, data_type, records = load_data(filepath)
            competitors_data[comp_name] = records
            print(f"✓ 加载 {filepath}: {comp_name} ({len(records)} 条记录, {data_type})")
        except Exception as e:
            errors.append({'file': filepath, 'error': str(e)})
            print(f"✗ 加载失败 {filepath}: {e}")
    
    if not competitors_data:
        print("错误: 没有成功加载任何竞品数据")
        sys.exit(2)
    
    # 执行分析
    try:
        report = analyze_competitors(competitors_data)
    except Exception as e:
        print(f"分析失败: {e}")
        sys.exit(4)
    
    # 输出报告
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    output_filename = f"{args.prefix}_{timestamp}.json"
    output_path = os.path.join(args.output_dir, output_filename)
    
    try:
        atomic_write(output_path, json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\n✓ 报告已保存: {output_path}")
    except Exception as e:
        print(f"写入失败: {e}")
        sys.exit(5)
    
    # 打印摘要
    print_summary(report)
    
    # 输出错误明细
    if errors:
        print(f"\n警告: {len(errors)} 个文件加载失败")
        for err in errors:
            print(f"  {err['file']}: {err['error']}")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
