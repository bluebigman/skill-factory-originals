#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份核查工具 - 完整性校验与风险预警

功能：
1. 解析备份清单（支持纯文本/JSON/CSV格式）
2. 核对必填字段完整性
3. 版本差异对比（新增/删除/修改）
4. 恢复演练评分
5. 风险分级预警
6. 多格式输出（Markdown/JSON/自定义分隔符）

用法示例：
  python run.py --input backup_list.txt --output report.md
  python run.py --input backup_list.json --output report.json --format json
  python run.py --input backup_list.csv --output report.txt --format text --separator "|"
  python run.py --compare old.json new.json --output diff.md
  python run.py --selftest
"""

import argparse
import json
import os
import sys
import csv
import tempfile
from datetime import datetime, timezone
from collections import defaultdict

# 尝试导入 openpyxl（可选，用于 Excel 支持）
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


class BackupRecord:
    """备份记录类"""

    REQUIRED_FIELDS = ['filename', 'timestamp', 'size']

    def __init__(self, filename, timestamp, size, checksum='', backup_type='', status=''):
        self.filename = filename
        self.timestamp = timestamp
        self.size = int(size) if size else 0
        self.checksum = checksum
        self.backup_type = backup_type
        self.status = status

    def to_dict(self):
        return {
            'filename': self.filename,
            'timestamp': self.timestamp,
            'size': self.size,
            'checksum': self.checksum,
            'backup_type': self.backup_type,
            'status': self.status
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建记录"""
        return cls(
            filename=data.get('filename', ''),
            timestamp=data.get('timestamp', ''),
            size=data.get('size', 0),
            checksum=data.get('checksum', ''),
            backup_type=data.get('backup_type', ''),
            status=data.get('status', '')
        )

    def is_complete(self):
        """检查必填字段是否完整"""
        return all([
            self.filename,
            self.timestamp,
            self.size is not None and self.size >= 0
        ])


def parse_text(filepath):
    """解析纯文本文件（每行一条记录，字段用逗号或制表符分隔）"""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # 尝试逗号分隔，再尝试制表符
            parts = line.split(',') if ',' in line else line.split('\t')
            if len(parts) < 3:
                print(f"警告: 第 {line_num} 行字段不足，跳过: {line}")
                continue
            records.append(BackupRecord(
                filename=parts[0].strip(),
                timestamp=parts[1].strip(),
                size=parts[2].strip(),
                checksum=parts[3].strip() if len(parts) > 3 else '',
                backup_type=parts[4].strip() if len(parts) > 4 else '',
                status=parts[5].strip() if len(parts) > 5 else ''
            ))
    return records


def parse_json(filepath):
    """解析 JSON 文件（支持数组或对象）"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return [BackupRecord.from_dict(item) for item in data]
    elif isinstance(data, dict):
        # 支持 { "records": [...] } 或 { "1": {...} } 格式
        if 'records' in data:
            return [BackupRecord.from_dict(item) for item in data['records']]
        else:
            return [BackupRecord.from_dict(item) for item in data.values()]
    else:
        raise ValueError("JSON 格式不支持，应为数组或对象")


def parse_csv(filepath):
    """解析 CSV 文件"""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(BackupRecord(
                filename=row.get('filename', ''),
                timestamp=row.get('timestamp', ''),
                size=row.get('size', 0),
                checksum=row.get('checksum', ''),
                backup_type=row.get('backup_type', ''),
                status=row.get('status', '')
            ))
    return records


def parse_input(filepath, format_hint=None):
    """解析输入文件，根据扩展名或提示选择解析器"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"输入文件不存在: {filepath}")

    ext = format_hint.lower() if format_hint else os.path.splitext(filepath)[1].lower().lstrip('.')
    if ext == 'json':
        return parse_json(filepath)
    elif ext == 'csv':
        return parse_csv(filepath)
    elif ext in ('txt', 'text', 'log', ''):
        return parse_text(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def validate_records(records):
    """校验记录完整性，返回 (完整列表, 不完整列表)"""
    complete = []
    incomplete = []
    for rec in records:
        if rec.is_complete():
            complete.append(rec)
        else:
            incomplete.append(rec)
    return complete, incomplete


def calculate_score(records):
    """计算恢复演练评分（0-100）"""
    if not records:
        return 0
    total = 0
    now = datetime.now(timezone.utc)
    for rec in records:
        score = 0
        # 完整性（40分）
        if rec.is_complete():
            score += 40
        # 时间新鲜度（30分）
        try:
            ts = datetime.fromisoformat(rec.timestamp.replace('Z', '+00:00'))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = (now - ts).days
            if age_days <= 7:
                score += 30
            elif age_days <= 30:
                score += 15
        except (ValueError, TypeError):
            pass  # 时间格式错误，不加分
        # 大小合理性（30分）
        if rec.size > 0:
            score += 30
        total += score
    return round(total / len(records))


def risk_level(score):
    """根据评分返回风险等级"""
    if score >= 90:
        return "低风险"
    elif score >= 70:
        return "中风险"
    elif score >= 50:
        return "高风险"
    else:
        return "严重风险"


def compare_records(old_records, new_records):
    """对比新旧记录，返回差异字典"""
    old_map = {rec.filename: rec for rec in old_records}
    new_map = {rec.filename: rec for rec in new_records}

    added = [rec for name, rec in new_map.items() if name not in old_map]
    removed = [rec for name, rec in old_map.items() if name not in new_map]
    modified = []
    for name, new_rec in new_map.items():
        if name in old_map:
            old_rec = old_map[name]
            if (old_rec.timestamp != new_rec.timestamp or
                old_rec.size != new_rec.size or
                old_rec.checksum != new_rec.checksum):
                modified.append({
                    'filename': name,
                    'old': old_rec.to_dict(),
                    'new': new_rec.to_dict()
                })
    return {'added': added, 'removed': removed, 'modified': modified}


def generate_markdown(records, score, level, diff=None):
    """生成 Markdown 格式报告"""
    lines = []
    lines.append("# 备份核查报告")
    lines.append(f"\n**生成时间**: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**记录总数**: {len(records)}")
    lines.append(f"**完整记录**: {sum(1 for r in records if r.is_complete())}")
    lines.append(f"**不完整记录**: {sum(1 for r in records if not r.is_complete())}")
    lines.append(f"**恢复演练评分**: {score}/100")
    lines.append(f"**风险等级**: {level}")
    lines.append("\n## 记录明细")
    if records:
        lines.append("| 文件名 | 时间戳 | 大小 | 校验和 | 类型 | 状态 |")
        lines.append("|--------|--------|------|--------|------|------|")
        for rec in records:
            lines.append(f"| {rec.filename} | {rec.timestamp} | {rec.size} | {rec.checksum} | {rec.backup_type} | {rec.status} |")
    else:
        lines.append("无记录")
    if diff:
        lines.append("\n## 版本差异")
        if diff['added']:
            lines.append("\n### 新增")
            for rec in diff['added']:
                lines.append(f"- {rec.filename} ({rec.timestamp})")
        if diff['removed']:
            lines.append("\n### 删除")
            for rec in diff['removed']:
                lines.append(f"- {rec.filename} ({rec.timestamp})")
        if diff['modified']:
            lines.append("\n### 修改")
            for item in diff['modified']:
                lines.append(f"- {item['filename']}: {item['old']['timestamp']} -> {item['new']['timestamp']}")
    return "\n".join(lines)


def generate_json(records, score, level, diff=None):
    """生成 JSON 格式报告"""
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_records': len(records),
        'complete_records': sum(1 for r in records if r.is_complete()),
        'incomplete_records': sum(1 for r in records if not r.is_complete()),
        'score': score,
        'risk_level': level,
        'records': [rec.to_dict() for rec in records]
    }
    if diff:
        report['diff'] = {
            'added': [rec.to_dict() for rec in diff['added']],
            'removed': [rec.to_dict() for rec in diff['removed']],
            'modified': diff['modified']
        }
    return json.dumps(report, indent=2, ensure_ascii=False)


def generate_text(records, score, level, separator="|", diff=None):
    """生成纯文本格式报告"""
    lines = []
    lines.append(f"备份核查报告 - {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"记录总数: {len(records)}")
    lines.append(f"完整记录: {sum(1 for r in records if r.is_complete())}")
    lines.append(f"不完整记录: {sum(1 for r in records if not r.is_complete())}")
    lines.append(f"恢复演练评分: {score}/100")
    lines.append(f"风险等级: {level}")
    lines.append("\n记录明细:")
    for rec in records:
        lines.append(separator.join([
            rec.filename, rec.timestamp, str(rec.size),
            rec.checksum, rec.backup_type, rec.status
        ]))
    if diff:
        lines.append("\n版本差异:")
        if diff['added']:
            lines.append("新增:")
            for rec in diff['added']:
                lines.append(f"  + {rec.filename} ({rec.timestamp})")
        if diff['removed']:
            lines.append("删除:")
            for rec in diff['removed']:
                lines.append(f"  - {rec.filename} ({rec.timestamp})")
        if diff['modified']:
            lines.append("修改:")
            for item in diff['modified']:
                lines.append(f"  ~ {item['filename']}: {item['old']['timestamp']} -> {item['new']['timestamp']}")
    return "\n".join(lines)


def atomic_write(filepath, content):
    """原子化写入文件（先写临时文件再替换）"""
    dirname = os.path.dirname(filepath) or '.'
    fd, temp_path = tempfile.mkstemp(dir=dirname, prefix='.backup_check_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, filepath)
    except Exception:
        os.unlink(temp_path)
        raise


def run_selftest():
    """自检函数：真实调用主流程和核心函数"""
    print("开始自检...")

    # 创建临时测试文件
    test_dir = tempfile.mkdtemp(prefix='backup_selftest_')
    txt_file = os.path.join(test_dir, 'test.txt')
    json_file = os.path.join(test_dir, 'test.json')
    csv_file = os.path.join(test_dir, 'test.csv')
    output_file = os.path.join(test_dir, 'output.md')

    # 测试数据
    test_records = [
        BackupRecord('file1.txt', '2024-01-01T00:00:00+00:00', 100, 'abc123', 'full', 'ok'),
        BackupRecord('file2.txt', '2024-01-02T00:00:00+00:00', 200, 'def456', 'inc', 'ok'),
        BackupRecord('', '2024-01-03T00:00:00+00:00', 0, '', '', '')  # 不完整
    ]

    # 写入测试文件
    with open(txt_file, 'w', encoding='utf-8') as f:
        for rec in test_records:
            f.write(f"{rec.filename},{rec.timestamp},{rec.size},{rec.checksum},{rec.backup_type},{rec.status}\n")

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump([rec.to_dict() for rec in test_records], f)

    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'timestamp', 'size', 'checksum', 'backup_type', 'status'])
        writer.writeheader()
        for rec in test_records:
            writer.writerow(rec.to_dict())

    # 测试1: 解析文本
    records = parse_input(txt_file)
    assert len(records) == 3, f"文本解析失败: 预期3条，实际{len(records)}"
    print("✓ 文本解析通过")

    # 测试2: 解析 JSON
    records = parse_input(json_file)
    assert len(records) == 3, f"JSON解析失败: 预期3条，实际{len(records)}"
    print("✓ JSON解析通过")

    # 测试3: 解析 CSV
    records = parse_input(csv_file)
    assert len(records) == 3, f"CSV解析失败: 预期3条，实际{len(records)}"
    print("✓ CSV解析通过")

    # 测试4: 完整性校验
    complete, incomplete = validate_records(records)
    assert len(complete) == 2, f"完整性校验失败: 预期2条完整，实际{len(complete)}"
    assert len(incomplete) == 1, f"完整性校验失败: 预期1条不完整，实际{len(incomplete)}"
    print("✓ 完整性校验通过")

    # 测试5: 评分
    score = calculate_score(records)
    assert 0 <= score <= 100, f"评分超出范围: {score}"
    print(f"✓ 评分通过: {score}")

    # 测试6: 风险分级
    level = risk_level(score)
    assert level in ["低风险", "中风险", "高风险", "严重风险"], f"风险等级无效: {level}"
    print(f"✓ 风险分级通过: {level}")

    # 测试7: 差异对比
    old_records = [test_records[0], test_records[1]]
    new_records = [test_records[1], test_records[2]]
    diff = compare_records(old_records, new_records)
    assert len(diff['added']) == 1, "差异对比失败: 应新增1条"
    assert len(diff['removed']) == 1, "差异对比失败: 应删除1条"
    print("✓ 差异对比通过")

    # 测试8: 报告生成（Markdown）
    md_content = generate_markdown(records, score, level, diff)
    assert '# 备份核查报告' in md_content, "Markdown报告生成失败"
    print("✓ Markdown报告生成通过")

    # 测试9: 报告生成（JSON）
    json_content = generate_json(records, score, level, diff)
    parsed_json = json.loads(json_content)
    assert parsed_json['total_records'] == 3, "JSON报告生成失败"
    print("✓ JSON报告生成通过")

    # 测试10: 报告生成（文本）
    text_content = generate_text(records, score, level, separator="|")
    assert '备份核查报告' in text_content, "文本报告生成失败"
    print("✓ 文本报告生成通过")

    # 测试11: 原子写入
    atomic_write(output_file, md_content)
    assert os.path.exists(output_file), "原子写入失败"
    print("✓ 原子写入通过")

    # 测试12: 主流程（通过 argparse 调用）
    sys.argv = ['run.py', '--input', txt_file, '--output', output_file, '--format', 'markdown']
    main()
    assert os.path.exists(output_file), "主流程执行失败"
    print("✓ 主流程执行通过")

    # 清理临时文件
    import shutil
    shutil.rmtree(test_dir)

    print("\n所有自检通过！")
    return 0


def main():
    parser = argparse.ArgumentParser(description='备份核查工具 - 完整性校验与风险预警')
    parser.add_argument('--input', help='输入备份清单文件（文本/JSON/CSV）')
    parser.add_argument('--output', default='report.md', help='输出报告文件（默认: report.md）')
    parser.add_argument('--format', choices=['markdown', 'json', 'text'], default='markdown',
                        help='输出格式（默认: markdown）')
    parser.add_argument('--separator', default='|', help='文本格式分隔符（默认: |）')
    parser.add_argument('--compare', nargs=2, metavar=('OLD', 'NEW'),
                        help='对比两份备份清单')
    parser.add_argument('--selftest', action='store_true', help='运行自检')

    args = parser.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    if not args.input and not args.compare:
        parser.error("必须提供 --input 或 --compare 参数")

    try:
        if args.compare:
            # 对比模式
            old_records = parse_input(args.compare[0])
            new_records = parse_input(args.compare[1])
            diff = compare_records(old_records, new_records)
            # 使用新记录生成报告
            records = new_records
            score = calculate_score(records)
            level = risk_level(score)
        else:
            # 单文件模式
            records = parse_input(args.input)
            score = calculate_score(records)
            level = risk_level(score)
            diff = None

        # 生成报告
        if args.format == 'markdown':
            content = generate_markdown(records, score, level, diff)
        elif args.format == 'json':
            content = generate_json(records, score, level, diff)
        else:  # text
            content = generate_text(records, score, level, args.separator, diff)

        # 原子写入
        atomic_write(args.output, content)
        print(f"报告已生成: {args.output}")
        print(f"评分: {score}/100, 风险等级: {level}")

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"运行时错误: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
