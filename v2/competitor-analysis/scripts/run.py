#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞品透视 · 多维对标与差异洞察 Skill
真实可用的竞品分析工具：读取竞品数据文件，输出多维对比报告
支持 CSV / JSON / Markdown / TXT / Excel 格式输入
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
dry_run = False  # v3.274 模块级 dry-run 标志

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

# 错误码定义
EXIT_SUCCESS = 0
EXIT_PARAM_ERROR = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_FORMAT_UNSUPPORTED = 3
EXIT_FILE_TOO_LARGE = 4
EXIT_PARSE_ERROR = 5
EXIT_WRITE_ERROR = 6
EXIT_SELFTEST_FAILED = 7


def read_text_safe(path):
    """安全读取文本文件，支持多编码回退。"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_markdown_table(content):
    """解析 Markdown 表格，返回列表字典。
    支持无表头（默认 col1, col2...）和列数不一致（保留行，缺失列填空字符串）。
    增强表头检测：检查是否包含常见列名关键词，避免数字/空行误判。
    """
    rows = []
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    header_count = None
    for i, line in enumerate(lines):
        if '|' not in line:
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        # 跳过分隔行
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        if not rows:
            # 第一行作为表头，如果没有表头（全是数据），则生成默认列名
            rows.append(cells)
            header_count = len(cells)
            continue
        # 列数不一致时，补齐或截断
        if len(cells) != header_count:
            logger.warning(f"Markdown表格第{i+1}行列数({len(cells)})与表头({header_count})不一致，补齐空列")
            if len(cells) < header_count:
                cells.extend([''] * (header_count - len(cells)))
            else:
                cells = cells[:header_count]
        rows.append(cells)

    if len(rows) < 2:
        # 只有一行，视为无表头数据
        if len(rows) == 1:
            headers = [f"col{j+1}" for j in range(len(rows[0]))]
            return [dict(zip(headers, rows[0]))]
        return []

    headers = rows[0]
    # 检测表头是否包含常见列名关键词
    header_keywords = ['名称', 'name', '功能', 'feature', '价格', 'price', '评价', 'review', '竞品', 'competitor']
    is_header = any(any(kw in h.lower() for kw in header_keywords) for h in headers)
    if not is_header:
        # 第一行不是表头，生成默认列名
        headers = [f"col{j+1}" for j in range(len(headers))]
        data_rows = rows
    else:
        data_rows = rows[1:]

    result = []
    for row in data_rows:
        if len(row) != len(headers):
            logger.warning(f"行数据长度({len(row)})与表头({len(headers)})不一致，跳过")
            continue
        result.append(dict(zip(headers, row)))
    return result


def parse_csv_file(file_path):
    """解析 CSV 文件，返回列表字典。支持多编码回退。"""
    encodings = ['utf-8', 'gbk', 'gb18030']
    if HAS_CHARDET:
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(1024 * 1024)  # 读取前 1MB 用于检测
                detected = chardet.detect(raw)
                if detected['encoding']:
                    encodings.insert(0, detected['encoding'])
        except Exception as e:
            logger.warning(f"编码检测失败: {e}")

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='replace') as f:
                reader = csv.DictReader(f)
                rows = []
                for row in reader:
                    # 清理键名中的空白字符
                    clean_row = {k.strip() if k else f"col{i}": v for i, (k, v) in enumerate(row.items())}
                    rows.append(clean_row)
                if rows:
                    logger.info(f"CSV 解析成功，编码: {enc}，共 {len(rows)} 行")
                    return rows
        except Exception as e:
            logger.warning(f"CSV 解析失败 (编码 {enc}): {e}")
            continue
    raise ValueError(f"无法解析 CSV 文件: {file_path}")


def parse_json_file(file_path):
    """解析 JSON 文件，返回列表字典。支持多编码回退。"""
    encodings = ['utf-8', 'gbk', 'gb18030']
    if HAS_CHARDET:
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(1024 * 1024)
                detected = chardet.detect(raw)
                if detected['encoding']:
                    encodings.insert(0, detected['encoding'])
        except Exception as e:
            logger.warning(f"编码检测失败: {e}")

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='replace') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # 尝试提取列表
                    for key in ['competitors', 'items', 'data', 'products']:
                        if key in data and isinstance(data[key], list):
                            data = data[key]
                            break
                    else:
                        data = [data]
                if not isinstance(data, list):
                    raise ValueError("JSON 根节点必须是数组或包含数组的对象")
                logger.info(f"JSON 解析成功，编码: {enc}，共 {len(data)} 条记录")
                return data
        except Exception as e:
            logger.warning(f"JSON 解析失败 (编码 {enc}): {e}")
            continue
    raise ValueError(f"无法解析 JSON 文件: {file_path}")


def parse_markdown_file(file_path):
    """解析 Markdown 文件，返回列表字典。支持多编码回退。"""
    encodings = ['utf-8', 'gbk', 'gb18030']
    if HAS_CHARDET:
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(1024 * 1024)
                detected = chardet.detect(raw)
                if detected['encoding']:
                    encodings.insert(0, detected['encoding'])
        except Exception as e:
            logger.warning(f"编码检测失败: {e}")

    for enc in encodings:
        try:
            content = read_text_safe(file_path)
            if content:
                rows = parse_markdown_table(content)
                if rows:
                    logger.info(f"Markdown 解析成功，编码: {enc}，共 {len(rows)} 条记录")
                    return rows
        except Exception as e:
            logger.warning(f"Markdown 解析失败 (编码 {enc}): {e}")
            continue
    raise ValueError(f"无法解析 Markdown 文件: {file_path}")


def parse_txt_file(file_path):
    """解析纯文本文件，每行一条记录，用 | 分隔字段。支持多编码回退。"""
    encodings = ['utf-8', 'gbk', 'gb18030']
    if HAS_CHARDET:
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(1024 * 1024)
                detected = chardet.detect(raw)
                if detected['encoding']:
                    encodings.insert(0, detected['encoding'])
        except Exception as e:
            logger.warning(f"编码检测失败: {e}")

    for enc in encodings:
        try:
            rows = []
            content = read_text_safe(file_path)
            if content:
                for line in content.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        row = {'名称': parts[0]}
                        if len(parts) > 1:
                            row['功能'] = parts[1]
                        if len(parts) > 2:
                            row['价格'] = parts[2]
                        if len(parts) > 3:
                            row['评价'] = parts[3]
                        rows.append(row)
            if rows:
                logger.info(f"TXT 解析成功，编码: {enc}，共 {len(rows)} 条记录")
                return rows
        except Exception as e:
            logger.warning(f"TXT 解析失败 (编码 {enc}): {e}")
            continue
    raise ValueError(f"无法解析 TXT 文件: {file_path}")


def parse_excel_file(file_path):
    """解析 Excel 文件，返回列表字典。需要 openpyxl。"""
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl 未安装，请执行 pip install openpyxl")
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows = []
        headers = None
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                headers = [str(c).strip() if c else f"col{j}" for j, c in enumerate(row)]
                continue
            if headers and row:
                clean_row = {}
                for j, val in enumerate(row):
                    if j < len(headers):
                        clean_row[headers[j]] = str(val) if val is not None else ''
                rows.append(clean_row)
        wb.close()
        logger.info(f"Excel 解析成功，共 {len(rows)} 条记录")
        return rows
    except Exception as e:
        raise ValueError(f"无法解析 Excel 文件: {e}")


def load_data(file_path, format_type):
    """根据格式加载数据，返回列表字典。"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小超过限制 ({MAX_FILE_SIZE} bytes)")

    format_map = {
        'csv': parse_csv_file,
        'json': parse_json_file,
        'md': parse_markdown_file,
        'markdown': parse_markdown_file,
        'txt': parse_txt_file,
        'xlsx': parse_excel_file,
        'excel': parse_excel_file,
    }

    if format_type not in format_map:
        raise ValueError(f"不支持的格式: {format_type}")

    return format_map[format_type](file_path)


def extract_features(rows):
    """从数据中提取功能清单。"""
    features = set()
    for row in rows:
        for key in ['功能', 'features', 'feature', 'Features']:
            if key in row and row[key]:
                parts = re.split(r'[;；,，|]', str(row[key]))
                for part in parts:
                    part = part.strip()
                    if part and part not in ('无', '暂无', 'N/A', 'n/a'):
                        features.add(part)
                break
    return sorted(features)


def extract_prices(rows):
    """从数据中提取价格档位。"""
    prices = []
    for row in rows:
        price_info = {}
        for key in ['价格', 'price', 'Price']:
            if key in row and row[key]:
                price_info['raw'] = str(row[key])
                # 尝试提取价格档位
                tiers = re.split(r'[;；,，|]', price_info['raw'])
                price_info['tiers'] = [t.strip() for t in tiers if t.strip()]
                break
        if price_info:
            prices.append(price_info)
    return prices


def analyze_sentiment(text):
    """分析文本情感倾向（正面/负面/中性）。"""
    if not text:
        return '中性'
    positive_words = ['好', '赞', '优秀', '强大', '友好', '方便', '高效', '稳定', '推荐', '喜欢', '满意', '不错', '好用', '流畅', '专业', '全面', '支持好', '积极']
    negative_words = ['差', '烂', '糟糕', '难用', '卡顿', '崩溃', '贵', '慢', '复杂', '失望', '后悔', '问题', 'bug', '缺陷', '不足', '缺少', '无法', '不能', '失败', '错误', '垃圾', '坑']

    text_lower = text.lower()
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)

    if pos_count > neg_count:
        return '正面'
    elif neg_count > pos_count:
        return '负面'
    else:
        return '中性'


def analyze_reviews(rows):
    """分析用户评价情感倾向。"""
    reviews_data = []
    for row in rows:
        review_info = {'name': row.get('名称', row.get('name', '未知'))}
        for key in ['评价', 'review', 'reviews', 'Review']:
            if key in row and row[key]:
                raw_reviews = re.split(r'[;；,，|]', str(row[key]))
                review_info['reviews'] = [r.strip() for r in raw_reviews if r.strip()]
                sentiments = [analyze_sentiment(r) for r in review_info['reviews']]
                review_info['sentiments'] = sentiments
                review_info['positive'] = sentiments.count('正面')
                review_info['negative'] = sentiments.count('负面')
                review_info['neutral'] = sentiments.count('中性')
                break
        if 'reviews' in review_info:
            reviews_data.append(review_info)
    return reviews_data


def generate_comparison_matrix(rows, features):
    """生成功能对比矩阵。"""
    matrix = []
    for row in rows:
        name = row.get('名称', row.get('name', '未知'))
        entry = {'名称': name}
        row_features = set()
        for key in ['功能', 'features', 'feature', 'Features']:
            if key in row and row[key]:
                parts = re.split(r'[;；,，|]', str(row[key]))
                row_features = {p.strip() for p in parts if p.strip()}
                break
        for feature in features:
            entry[feature] = '✓' if feature in row_features else '✗'
        matrix.append(entry)
    return matrix


def generate_diff_suggestions(rows, features, matrix):
    """生成差异化建议。"""
    suggestions = []
    if not rows or not features:
        return ["输入数据不足，无法生成差异化建议。"]

    # 计算每个功能的支持率
    feature_support = {}
    for feature in features:
        count = sum(1 for row in matrix if row.get(feature) == '✓')
        feature_support[feature] = count

    # 找出差异化机会
    all_support = [f for f, c in feature_support.items() if c == len(rows)]
    partial_support = [f for f, c in feature_support.items() if 0 < c < len(rows)]
    no_support = [f for f, c in feature_support.items() if c == 0]

    if all_support:
        suggestions.append(f"行业标配功能（所有竞品均支持）: {', '.join(all_support)}。这些功能是入场券，需保证基础体验。")
    if partial_support:
        suggestions.append(f"差异化机会功能（部分竞品支持）: {', '.join(partial_support)}。可考虑在这些功能上做深做透，形成差异化优势。")
    if no_support:
        suggestions.append(f"市场空白功能（暂无竞品支持）: {', '.join(no_support)}。这些是潜在创新点，可评估投入产出比。")

    # 价格策略建议
    prices = extract_prices(rows)
    if prices:
        free_count = sum(1 for p in prices if '免费' in p.get('raw', ''))
        if free_count == len(prices):
            suggestions.append("所有竞品均提供免费版本，免费策略是获客基础。")
        elif free_count > 0:
            suggestions.append(f"{free_count}/{len(prices)} 家竞品提供免费版本，免费+增值模式是主流。")

    return suggestions


def generate_report(rows, features, matrix, reviews_data, prices, suggestions, output_format='md'):
    """生成分析报告。"""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    if output_format == 'json':
        report = {
            'generated_at': timestamp,
            'competitor_count': len(rows),
            'features': features,
            'comparison_matrix': matrix,
            'reviews': reviews_data,
            'prices': prices,
            'suggestions': suggestions
        }
        return json.dumps(report, ensure_ascii=False, indent=2)

    # Markdown 格式
    lines = []
    lines.append("# 竞品分析报告\n")
    lines.append(f"**生成时间**: {timestamp}\n")
    lines.append(f"**竞品数量**: {len(rows)}\n")
    lines.append(f"**功能点数量**: {len(features)}\n\n")

    # 功能对比矩阵
    lines.append("## 功能对比矩阵\n")
    if matrix:
        headers = list(matrix[0].keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        for row in matrix:
            lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    else:
        lines.append("无数据\n")
    lines.append("\n")

    # 价格对比
    lines.append("## 价格对比\n")
    if prices:
        for p in prices:
            name = p.get('name', '未知')
            raw = p.get('raw', 'N/A')
            lines.append(f"- **{name}**: {raw}")
    else:
        lines.append("无价格数据\n")
    lines.append("\n")

    # 用户评价情感分析
    lines.append("## 用户评价情感分析\n")
    if reviews_data:
        for r in reviews_data:
            name = r.get('name', '未知')
            pos = r.get('positive', 0)
            neg = r.get('negative', 0)
            neu = r.get('neutral', 0)
            lines.append(f"- **{name}**: 正面 {pos} 条, 负面 {neg} 条, 中性 {neu} 条")
    else:
        lines.append("无评价数据\n")
    lines.append("\n")

    # 差异化建议
    lines.append("## 差异化建议\n")
    for i, s in enumerate(suggestions, 1):
        lines.append(f"{i}. {s}")
    lines.append("\n")

    return "\n".join(lines)


def write_file_atomic(file_path, content, dry_run=False):
    """原子化写入文件。"""
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        directory = os.path.dirname(os.path.abspath(file_path))
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=directory, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
            os.replace(temp_path, file_path)
            logger.info(f"已写入文件: {file_path}")
            return True
        except Exception as e:
            os.unlink(temp_path)
            raise IOError(f"写入文件失败: {e}")
    print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")
    return False


def run_selftest():
    """自检函数：验证核心功能。"""
    print("[SELFTEST] 开始自检...")
    failures = []

    # 测试 1: Markdown 表格解析
    print("[SELFTEST] 测试 Markdown 表格解析...")
    md_content = """
| 名称 | 功能 | 价格 | 评价 |
|------|------|------|------|
| 竞品A | 实时协作;文件分享 | 免费 | 用户反馈积极;界面友好 |
| 竞品B | 实时协作 | 99元/月 | 功能强大但学习曲线陡峭 |
"""
    try:
        rows = parse_markdown_table(md_content)
        assert len(rows) == 2, f"期望 2 行，实际 {len(rows)} 行"
        assert rows[0]['名称'] == '竞品A', f"期望 '竞品A'，实际 {rows[0]['名称']}"
        assert rows[1]['价格'] == '99元/月', f"期望 '99元/月'，实际 {rows[1]['价格']}"
        print("[SELFTEST] PASS - Markdown 表格解析")
    except Exception as e:
        failures.append(f"Markdown 表格解析失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 2: 功能提取
    print("[SELFTEST] 测试功能提取...")
    try:
        features = extract_features(rows)
        assert '实时协作' in features, f"期望包含 '实时协作'，实际 {features}"
        assert '文件分享' in features, f"期望包含 '文件分享'，实际 {features}"
        print(f"[SELFTEST] PASS - 功能提取: {features}")
    except Exception as e:
        failures.append(f"功能提取失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 3: 情感分析
    print("[SELFTEST] 测试情感分析...")
    try:
        assert analyze_sentiment('很好用，界面友好') == '正面', "期望 '正面'"
        assert analyze_sentiment('功能少，价格贵') == '负面', "期望 '负面'"
        assert analyze_sentiment('普通') == '中性', "期望 '中性'"
        print("[SELFTEST] PASS - 情感分析")
    except Exception as e:
        failures.append(f"情感分析失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 4: 对比矩阵生成
    print("[SELFTEST] 测试对比矩阵生成...")
    try:
        matrix = generate_comparison_matrix(rows, features)
        assert len(matrix) == 2, f"期望 2 行，实际 {len(matrix)} 行"
        assert matrix[0]['实时协作'] == '✓', f"期望 '✓'，实际 {matrix[0]['实时协作']}"
        print("[SELFTEST] PASS - 对比矩阵生成")
    except Exception as e:
        failures.append(f"对比矩阵生成失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 5: 差异化建议生成
    print("[SELFTEST] 测试差异化建议生成...")
    try:
        suggestions = generate_diff_suggestions(rows, features, matrix)
        assert len(suggestions) > 0, "期望至少 1 条建议"
        print(f"[SELFTEST] PASS - 差异化建议生成 ({len(suggestions)} 条)")
    except Exception as e:
        failures.append(f"差异化建议生成失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 6: 报告生成
    print("[SELFTEST] 测试报告生成...")
    try:
        reviews_data = analyze_reviews(rows)
        prices = extract_prices(rows)
        report = generate_report(rows, features, matrix, reviews_data, prices, suggestions, 'md')
        assert '竞品分析报告' in report, "报告缺少标题"
        assert '功能对比矩阵' in report, "报告缺少功能对比矩阵"
        assert '差异化建议' in report, "报告缺少差异化建议"
        print("[SELFTEST] PASS - 报告生成")
    except Exception as e:
        failures.append(f"报告生成失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 7: JSON 报告生成
    print("[SELFTEST] 测试 JSON 报告生成...")
    try:
        report_json = generate_report(rows, features, matrix, reviews_data, prices, suggestions, 'json')
        data = json.loads(report_json)
        assert data['competitor_count'] == 2, f"期望 2，实际 {data['competitor_count']}"
        print("[SELFTEST] PASS - JSON 报告生成")
    except Exception as e:
        failures.append(f"JSON 报告生成失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 8: 空输入处理
    print("[SELFTEST] 测试空输入处理...")
    try:
        empty_rows = []
        features_empty = extract_features(empty_rows)
        assert features_empty == [], f"期望空列表，实际 {features_empty}"
        suggestions_empty = generate_diff_suggestions(empty_rows, features_empty, [])
        assert len(suggestions_empty) == 1, f"期望 1 条建议，实际 {len(suggestions_empty)}"
        print("[SELFTEST] PASS - 空输入处理")
    except Exception as e:
        failures.append(f"空输入处理失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 9: 中文标点分隔
    print("[SELFTEST] 测试中文标点分隔...")
    try:
        test_row = {'名称': '测试', '功能': '功能A；功能B，功能C'}
        test_rows = [test_row]
        test_features = extract_features(test_rows)
        assert '功能A' in test_features, f"期望包含 '功能A'，实际 {test_features}"
        assert '功能B' in test_features, f"期望包含 '功能B'，实际 {test_features}"
        assert '功能C' in test_features, f"期望包含 '功能C'，实际 {test_features}"
        print("[SELFTEST] PASS - 中文标点分隔")
    except Exception as e:
        failures.append(f"中文标点分隔失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 10: 编码回退
    print("[SELFTEST] 测试编码回退...")
    try:
        # 创建 GBK 编码的临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='gbk') as f:
            f.write("名称,功能\n竞品A,实时协作\n")
            temp_path = f.name
        try:
            rows_gbk = parse_csv_file(temp_path)
            assert len(rows_gbk) == 1, f"期望 1 行，实际 {len(rows_gbk)}"
            assert rows_gbk[0]['名称'] == '竞品A', f"期望 '竞品A'，实际 {rows_gbk[0]['名称']}"
            print("[SELFTEST] PASS - 编码回退")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        failures.append(f"编码回退失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 11: dry-run 模式
    print("[SELFTEST] 测试 dry-run 模式...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            result = write_file_atomic(test_file, "test content", dry_run=True)
            assert result == False, f"期望返回 False，实际 {result}"
            assert not os.path.exists(test_file), "dry-run 模式不应写入文件"
            print("[SELFTEST] PASS - dry-run 模式")
    except Exception as e:
        failures.append(f"dry-run 模式失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    # 测试 12: 实际写入
    print("[SELFTEST] 测试实际写入...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            result = write_file_atomic(test_file, "test content", dry_run=False)
            assert result == True, f"期望返回 True，实际 {result}"
            assert os.path.exists(test_file), "实际写入模式应写入文件"
            with open(test_file, 'r', encoding='utf-8') as f:
                assert f.read() == "test content", "文件内容不匹配"
            print("[SELFTEST] PASS - 实际写入")
    except Exception as e:
        failures.append(f"实际写入失败: {e}")
        print(f"[SELFTEST] FAIL - {e}")

    if failures:
        print(f"\n[SELFTEST] FAILED - {len(failures)} 项失败")
        for f in failures:
            print(f"  - {f}")
        return EXIT_SELFTEST_FAILED

    print("\n[SELFTEST] PASS - 全部测试通过")
    return EXIT_SUCCESS


def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description='竞品透视 · 多维对标与差异洞察 - 竞品分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input data.csv --format csv
  python run.py --input data.json --format json --dry-run
  python run.py --input table.md --format md --verbose
  python run.py --selftest
        """
    )
    parser.add_argument('--input', '-i', type=str, help='输入文件路径')
    parser.add_argument('--format', '-f', type=str, choices=['csv', 'json', 'md', 'markdown', 'txt', 'xlsx', 'excel'],
                        help='输入文件格式')
    parser.add_argument('--output-dir', '-o', type=str, default='.',
                        help='输出目录（默认: 当前目录）')
    parser.add_argument('--output-format', type=str, choices=['md', 'json'], default='md',
                        help='输出格式（默认: md）')
    parser.add_argument('--dry-run', action='store_true',
                        help='预览模式：只打印将写入的文件，不实际写入')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='输出详细处理日志')
    parser.add_argument('--selftest', action='store_true',
                        help='运行自检')

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式 - 必须在所有必填校验之前
    if args.selftest:
        return run_selftest()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("详细日志模式已开启")

    # 参数校验
    if not args.input:
        logger.error("错误: 必须提供 --input 参数")
        parser.print_help()
        return EXIT_PARAM_ERROR

    if not args.format:
        # 根据扩展名推断格式
        ext = Path(args.input).suffix.lower().lstrip('.')
        format_map = {'csv': 'csv', 'json': 'json', 'md': 'md', 'markdown': 'md', 'txt': 'txt', 'xlsx': 'xlsx'}
        if ext in format_map:
            args.format = format_map[ext]
            logger.info(f"根据扩展名推断格式: {args.format}")
        else:
            logger.error(f"错误: 无法推断格式，请使用 --format 指定")
            return EXIT_PARAM_ERROR

    try:
        # 加载数据
        logger.info(f"加载数据: {args.input} (格式: {args.format})")
        rows = load_data(args.input, args.format)
        if not rows:
            logger.warning("警告: 输入数据为空")
            rows = []

        # 分析
        logger.info(f"提取功能清单...")
        features = extract_features(rows)
        logger.info(f"提取到 {len(features)} 个功能点")

        logger.info(f"生成对比矩阵...")
        matrix = generate_comparison_matrix(rows, features)

        logger.info(f"分析用户评价...")
        reviews_data = analyze_reviews(rows)

        logger.info(f"提取价格信息...")
        prices = extract_prices(rows)

        logger.info(f"生成差异化建议...")
        suggestions = generate_diff_suggestions(rows, features, matrix)

        # 生成报告
        logger.info(f"生成报告 (格式: {args.output_format})...")
        report = generate_report(rows, features, matrix, reviews_data, prices, suggestions, args.output_format)

        # 输出
        if args.dry_run:
            # 预览模式：只打印不写盘
            report_path = os.path.join(args.output_dir, f"report.{args.output_format}")
            matrix_path = os.path.join(args.output_dir, "comparison_matrix.csv")
            print(f"[DRY-RUN] 将写入: {report_path}")
            print(f"[DRY-RUN] 将写入: {matrix_path}")
            print("\n" + "=" * 60)
            print("报告预览（前 2000 字符）:")
            print("=" * 60)
            print(report[:2000])
            if len(report) > 2000:
                print(f"\n... (报告共 {len(report)} 字符，已截断预览)")
            return EXIT_SUCCESS

        # 实际写入
        os.makedirs(args.output_dir, exist_ok=True)

        # 写入报告
        report_path = os.path.join(args.output_dir, f"report.{args.output_format}")
        write_file_atomic(report_path, report, dry_run=False)
        logger.info(f"报告已保存: {report_path}")

        # 写入对比矩阵 CSV
        if matrix:
            matrix_path = os.path.join(args.output_dir, "comparison_matrix.csv")
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(matrix[0].keys()))
            writer.writeheader()
            writer.writerows(matrix)
            write_file_atomic(matrix_path, output.getvalue(), dry_run=False)
            logger.info(f"对比矩阵已保存: {matrix_path}")

        # 控制台摘要
        print(f"\n分析完成:")
        print(f"  - 竞品数量: {len(rows)}")
        print(f"  - 功能点数量: {len(features)}")
        print(f"  - 价格档位: {len(prices)}")
        print(f"  - 差异化建议: {len(suggestions)} 条")
        print(f"  - 报告文件: {report_path}")
        if matrix:
            print(f"  - 对比矩阵: {matrix_path}")

        return EXIT_SUCCESS

    except FileNotFoundError as e:
        logger.error(f"错误: {e}")
        return EXIT_FILE_NOT_FOUND
    except ValueError as e:
        logger.error(f"错误: {e}")
        return EXIT_PARSE_ERROR
    except ImportError as e:
        logger.error(f"错误: {e}")
        return EXIT_FORMAT_UNSUPPORTED
    except IOError as e:
        logger.error(f"错误: {e}")
        return EXIT_WRITE_ERROR
    except Exception as e:
        logger.error(f"未预期的错误: {e}", exc_info=True)
        return EXIT_PARSE_ERROR


if __name__ == '__main__':
    sys.exit(main())
