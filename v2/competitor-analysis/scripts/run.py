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
from collections import defaultdict
from datetime import datetime

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


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
        if i == 0 or not rows:
            if not rows:
                rows.append(cells)
                continue
        if len(cells) == len(rows[0]):
            rows.append(cells)
    if not rows:
        return []
    headers = rows[0]
    data = []
    for row in rows[1:]:
        data.append(dict(zip(headers, row)))
    return data


def load_data(filepath):
    """加载竞品数据文件，返回 (竞品名, 数据类型, 记录列表)"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    ext = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)
    # 从文件名提取竞品名（第一个下划线前）
    comp_name = filename.split('_')[0] if '_' in filename else '未命名竞品'
    
    records = []
    data_type = 'unknown'
    
    try:
        if ext == '.csv':
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                records = list(reader)
        elif ext == '.json':
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = data.get('records', [data])
        elif ext == '.md':
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                records = parse_markdown_table(content)
        elif ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # 尝试解析简单格式：每行 "字段: 值"
                for line in content.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        k, v = line.split(':', 1)
                        records.append({k.strip(): v.strip()})
        elif ext == '.xlsx' and HAS_OPENPYXL:
            wb = openpyxl.load_workbook(filepath, read_only=True)
            ws = wb.active
            headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
            for row in ws.iter_rows(min_row=2, values_only=True):
                records.append(dict(zip(headers, row)))
            wb.close()
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
    except Exception as e:
        raise RuntimeError(f"解析文件 {filepath} 失败: {e}")
    
    # 识别数据类型
    if records:
        all_keys = set().union(*[set(r.keys()) for r in records])
        if any(k in ['功能', 'feature', 'features'] for k in all_keys):
            data_type = 'feature'
        elif any(k in ['价格', '定价', 'price', 'pricing'] for k in all_keys):
            data_type = 'pricing'
        elif any(k in ['评价', '评论', 'review', 'rating'] for k in all_keys):
            data_type = 'review'
        else:
            data_type = 'general'
    
    return comp_name, data_type, records


def analyze_features(records):
    """功能对比分析"""
    features = defaultdict(list)
    for rec in records:
        for k, v in rec.items():
            if v and str(v).strip() not in ['', '无', 'N/A', 'NA']:
                features[k].append(str(v).strip())
    return dict(features)


def analyze_pricing(records):
    """定价分析"""
    prices = []
    for rec in records:
        for k, v in rec.items():
            if any(word in k.lower() for word in ['价格', '定价', 'price', 'pricing', '费用', 'cost']):
                try:
                    # 提取数字
                    nums = re.findall(r'[\d.]+', str(v))
                    if nums:
                        prices.append(float(nums[0]))
                except (ValueError, IndexError):
                    continue
    if not prices:
        return {'count': 0, 'min': 0, 'max': 0, 'avg': 0, 'tier': '未知'}
    
    avg = sum(prices) / len(prices)
    if avg < 50:
        tier = '低价位'
    elif avg < 200:
        tier = '中价位'
    else:
        tier = '高价位'
    
    return {
        'count': len(prices),
        'min': min(prices),
        'max': max(prices),
        'avg': round(avg, 2),
        'tier': tier
    }


def analyze_reviews(records):
    """评价情感分析（简单关键词法）"""
    positive_words = ['好', '优秀', '赞', '推荐', '满意', '好用', '强大', '稳定', '快', '方便']
    negative_words = ['差', '慢', '卡', '贵', '难用', '崩溃', 'bug', '问题', '失望', '糟糕']
    
    pos_count = 0
    neg_count = 0
    total = 0
    keywords = defaultdict(int)
    
    for rec in records:
        for k, v in rec.items():
            if any(word in k.lower() for word in ['评价', '评论', 'review', 'rating', 'feedback']):
                text = str(v).lower()
                total += 1
                for w in positive_words:
                    if w in text:
                        pos_count += 1
                        keywords[w] += 1
                for w in negative_words:
                    if w in text:
                        neg_count += 1
                        keywords[w] += 1
    
    if total == 0:
        return {'total': 0, 'positive': 0, 'negative': 0, 'sentiment': '无数据', 'keywords': {}}
    
    sentiment = '正面' if pos_count > neg_count else ('负面' if neg_count > pos_count else '中性')
    return {
        'total': total,
        'positive': pos_count,
        'negative': neg_count,
        'sentiment': sentiment,
        'keywords': dict(sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5])
    }


def generate_report(competitors):
    """生成对比报告"""
    lines = []
    lines.append("# 竞品对比分析报告\n")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"分析竞品数: {len(competitors)}\n")
    
    # 功能对比
    lines.append("\n## 功能对比矩阵\n")
    lines.append("| 竞品 | 功能维度 | 功能项数 |")
    lines.append("|------|----------|----------|")
    for comp in competitors:
        if comp['type'] == 'feature':
            feat = analyze_features(comp['records'])
            lines.append(f"| {comp['name']} | {', '.join(list(feat.keys())[:3])} | {sum(len(v) for v in feat.values())} |")
    
    # 定价对比
    lines.append("\n## 定价分析\n")
    lines.append("| 竞品 | 样本数 | 最低价 | 最高价 | 均价 | 档位 |")
    lines.append("|------|--------|--------|--------|------|------|")
    for comp in competitors:
        if comp['type'] == 'pricing':
            p = analyze_pricing(comp['records'])
            lines.append(f"| {comp['name']} | {p['count']} | {p['min']} | {p['max']} | {p['avg']} | {p['tier']} |")
    
    # 评价对比
    lines.append("\n## 用户评价分析\n")
    lines.append("| 竞品 | 样本数 | 正面 | 负面 | 情感倾向 | 高频词 |")
    lines.append("|------|--------|------|------|----------|--------|")
    for comp in competitors:
        if comp['type'] == 'review':
            r = analyze_reviews(comp['records'])
            kw = ', '.join(r['keywords'].keys()) if r['keywords'] else '无'
            lines.append(f"| {comp['name']} | {r['total']} | {r['positive']} | {r['negative']} | {r['sentiment']} | {kw} |")
    
    # 差异化建议
    lines.append("\n## 差异化建议\n")
    types = set(c['type'] for c in competitors)
    if 'feature' in types:
        lines.append("- 功能维度：建议对比各竞品功能覆盖度，找出缺失项作为机会点")
    if 'pricing' in types:
        lines.append("- 定价维度：分析价格区间分布，评估自身定价的竞争力")
    if 'review' in types:
        lines.append("- 评价维度：关注负面评价高频词，针对性改进产品体验")
    if not types:
        lines.append("- 数据不足：请提供包含功能、定价或评价字段的竞品数据")
    
    return '\n'.join(lines)


def process_directory(input_dir, output_file):
    """处理目录下所有竞品数据文件"""
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(f"目录不存在: {input_dir}")
    
    competitors = []
    for fname in os.listdir(input_dir):
        if fname.startswith('.'):
            continue
        fpath = os.path.join(input_dir, fname)
        if os.path.isfile(fpath):
            try:
                name, dtype, records = load_data(fpath)
                if records:
                    competitors.append({'name': name, 'type': dtype, 'records': records})
                    print(f"已加载: {name} ({dtype}) - {len(records)}条记录")
            except Exception as e:
                print(f"跳过 {fname}: {e}", file=sys.stderr)
    
    if not competitors:
        raise ValueError("未找到有效的竞品数据文件")
    
    report = generate_report(competitors)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存: {output_file}")
    else:
        print(report)
    
    return len(competitors)


def selftest():
    """自检函数：验证核心功能"""
    print("运行自检...")
    
    # 创建临时测试数据
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # 测试数据1：功能
        feat_data = [
            {'功能': '报表', '描述': '支持导出'},
            {'功能': '图表', '描述': '支持柱状图'},
            {'功能': '协作', '描述': '实时同步'}
        ]
        f1 = os.path.join(tmpdir, '产品A_功能.json')
        with open(f1, 'w') as f:
            json.dump(feat_data, f)
        
        # 测试数据2：定价
        price_data = [
            {'价格': '99元/月'},
            {'价格': '199元/月'},
            {'价格': '299元/月'}
        ]
        f2 = os.path.join(tmpdir, '产品B_定价.json')
        with open(f2, 'w') as f:
            json.dump(price_data, f)
        
        # 测试数据3：评价
        review_data = [
            {'评价': '很好用，推荐！'},
            {'评价': '价格有点贵，但功能强大'},
            {'评价': '界面卡顿，体验一般'}
        ]
        f3 = os.path.join(tmpdir, '产品C_评价.json')
        with open(f3, 'w') as f:
            json.dump(review_data, f)
        
        # 执行分析
        count = process_directory(tmpdir, os.path.join(tmpdir, 'report.md'))
        assert count == 3, f"预期3个竞品，实际{count}"
        
        # 验证报告内容
        report_path = os.path.join(tmpdir, 'report.md')
        with open(report_path, 'r') as f:
            content = f.read()
        assert '竞品对比分析报告' in content
        assert '产品A' in content
        assert '产品B' in content
        assert '产品C' in content
        
        print("自检通过！")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='竞品透视：多维对标与差异洞察工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--input', '-i', help='输入目录（包含竞品数据文件）')
    parser.add_argument('--output', '-o', help='输出报告文件路径（Markdown格式）')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    
    args = parser.parse_args()
    
    if args.selftest:
        try:
            selftest()
            sys.exit(0)
        except Exception as e:
            print(f"自检失败: {e}", file=sys.stderr)
            sys.exit(1)
    
    if not args.input:
        parser.error("请指定 --input 参数（竞品数据目录）")
    
    try:
        count = process_directory(args.input, args.output)
        print(f"分析完成，共处理 {count} 个竞品")
        sys.exit(0)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
