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
import hashlib
from datetime import datetime
from collections import defaultdict

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


def parse_input(filepath):
    """解析输入文件，支持文本/JSON/CSV格式"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"输入文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        raise ValueError("输入文件为空")
    
    records = []
    
    # 尝试JSON解析
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    records.append(BackupRecord.from_dict(item))
                else:
                    print(f"警告: 跳过非字典记录: {item}")
        elif isinstance(data, dict):
            if 'records' in data:
                for item in data['records']:
                    records.append(BackupRecord.from_dict(item))
            else:
                records.append(BackupRecord.from_dict(data))
        return records
    except json.JSONDecodeError:
        pass
    
    # 尝试CSV解析
    try:
        import io
        csv_reader = csv.DictReader(io.StringIO(content))
        for row in csv_reader:
            records.append(BackupRecord.from_dict(row))
        if records:
            return records
    except Exception:
        pass
    
    # 纯文本解析（每行: 文件名,时间戳,大小[,校验值,类型,状态]）
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 3:
            print(f"警告: 跳过无法解析的行: {line}")
            continue
        
        record = BackupRecord(
            filename=parts[0],
            timestamp=parts[1],
            size=parts[2],
            checksum=parts[3] if len(parts) > 3 else '',
            backup_type=parts[4] if len(parts) > 4 else '',
            status=parts[5] if len(parts) > 5 else ''
        )
        records.append(record)
    
    if not records:
        raise ValueError("未识别为备份记录，请检查输入格式")
    
    return records


def check_completeness(records):
    """核对备份清单完整性"""
    issues = []
    for i, record in enumerate(records):
        missing = []
        for field in BackupRecord.REQUIRED_FIELDS:
            if not getattr(record, field):
                missing.append(field)
        if missing:
            issues.append({
                'record_index': i,
                'filename': record.filename or '未知',
                'missing_fields': missing,
                'severity': 'high' if 'filename' in missing else 'medium'
            })
    
    return issues


def compare_versions(old_records, new_records):
    """对比两个版本的备份差异"""
    old_map = {r.filename: r for r in old_records}
    new_map = {r.filename: r for r in new_records}
    
    added = [r for name, r in new_map.items() if name not in old_map]
    deleted = [r for name, r in old_map.items() if name not in new_map]
    modified = []
    
    for name, new_r in new_map.items():
        if name in old_map:
            old_r = old_map[name]
            if (old_r.size != new_r.size or 
                old_r.timestamp != new_r.timestamp or
                old_r.checksum != new_r.checksum):
                modified.append({
                    'filename': name,
                    'old': old_r.to_dict(),
                    'new': new_r.to_dict()
                })
    
    return {
        'added': added,
        'deleted': deleted,
        'modified': modified,
        'stats': {
            'added_count': len(added),
            'deleted_count': len(deleted),
            'modified_count': len(modified),
            'total_old': len(old_records),
            'total_new': len(new_records)
        }
    }


def evaluate_recovery(records):
    """评估恢复演练结果"""
    if not records:
        return {'score': 0, 'level': '较差', 'details': []}
    
    score = 100
    details = []
    
    for record in records:
        # 检查状态
        if record.status and record.status.lower() in ['failed', '失败']:
            score -= 20
            details.append(f"{record.filename}: 恢复失败")
        elif record.status and record.status.lower() in ['partial', '部分']:
            score -= 10
            details.append(f"{record.filename}: 部分恢复")
        
        # 检查校验值
        if not record.checksum:
            score -= 5
            details.append(f"{record.filename}: 缺少校验值")
        
        # 检查大小
        if record.size <= 0:
            score -= 5
            details.append(f"{record.filename}: 文件大小为0")
    
    score = max(0, min(100, score))
    
    if score >= 80:
        level = '良好'
    elif score >= 50:
        level = '一般'
    else:
        level = '较差'
    
    return {'score': score, 'level': level, 'details': details}


def generate_risks(records, completeness_issues):
    """生成风险预警"""
    risks = []
    
    # 高优先级风险
    for issue in completeness_issues:
        if issue['severity'] == 'high':
            risks.append({
                'level': '高',
                'message': f"记录 {issue['record_index']} ({issue['filename']}) 缺少必填字段: {', '.join(issue['missing_fields'])}"
            })
    
    # 中优先级风险
    for record in records:
        if record.status and record.status.lower() in ['failed', '失败']:
            risks.append({
                'level': '高',
                'message': f"备份失败: {record.filename}"
            })
        elif record.size == 0:
            risks.append({
                'level': '中',
                'message': f"文件大小为0: {record.filename}"
            })
        elif not record.checksum:
            risks.append({
                'level': '低',
                'message': f"缺少校验值: {record.filename}"
            })
    
    # 按级别排序
    level_order = {'高': 0, '中': 1, '低': 2}
    risks.sort(key=lambda x: level_order.get(x['level'], 3))
    
    return risks


def format_output(data, format_type='markdown', separator='|'):
    """格式化输出"""
    if format_type == 'json':
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    elif format_type == 'text':
        lines = []
        if 'records' in data:
            for record in data['records']:
                lines.append(separator.join([
                    record.get('filename', ''),
                    record.get('timestamp', ''),
                    str(record.get('size', 0)),
                    record.get('status', '')
                ]))
        elif 'risks' in data:
            for risk in data['risks']:
                lines.append(f"{risk['level']}{separator}{risk['message']}")
        return '\n'.join(lines)
    
    else:  # markdown
        lines = []
        if 'records' in data:
            lines.append("| 文件名 | 时间戳 | 大小 | 状态 |")
            lines.append("|--------|--------|------|------|")
            for record in data['records']:
                lines.append(f"| {record.get('filename', '')} | {record.get('timestamp', '')} | {record.get('size', 0)} | {record.get('status', '')} |")
        elif 'risks' in data:
            lines.append("| 级别 | 风险描述 |")
            lines.append("|------|----------|")
            for risk in data['risks']:
                lines.append(f"| {risk['level']} | {risk['message']} |")
        elif 'diff' in data:
            diff = data['diff']
            lines.append("## 版本差异报告")
            lines.append(f"- 新增: {diff['stats']['added_count']} 个文件")
            lines.append(f"- 删除: {diff['stats']['deleted_count']} 个文件")
            lines.append(f"- 修改: {diff['stats']['modified_count']} 个文件")
            if diff['added']:
                lines.append("\n### 新增文件")
                for r in diff['added']:
                    lines.append(f"- {r.filename}")
            if diff['deleted']:
                lines.append("\n### 删除文件")
                for r in diff['deleted']:
                    lines.append(f"- {r.filename}")
            if diff['modified']:
                lines.append("\n### 修改文件")
                for m in diff['modified']:
                    lines.append(f"- {m['filename']}")
        return '\n'.join(lines)


def selftest():
    """自检函数"""
    print("运行自检...")
    
    # 创建测试数据
    test_records = [
        BackupRecord("backup_20240101.tar.gz", "2024-01-01 00:00:00", 1024, "abc123", "full", "success"),
        BackupRecord("backup_20240102.tar.gz", "2024-01-02 00:00:00", 2048, "def456", "full", "success"),
        BackupRecord("backup_20240103.tar.gz", "2024-01-03 00:00:00", 0, "", "full", "failed"),
    ]
    
    # 测试完整性检查
    issues = check_completeness(test_records)
    assert len(issues) == 1, "完整性检查应该发现1个问题"
    print("✓ 完整性检查通过")
    
    # 测试版本对比
    old_records = test_records[:2]
    new_records = test_records[1:]
    diff = compare_versions(old_records, new_records)
    assert diff['stats']['added_count'] == 1, "应新增1个文件"
    assert diff['stats']['deleted_count'] == 1, "应删除1个文件"
    print("✓ 版本对比通过")
    
    # 测试恢复评估
    eval_result = evaluate_recovery(test_records)
    assert eval_result['score'] < 80, "评分应低于80"
    print("✓ 恢复评估通过")
    
    # 测试风险生成
    risks = generate_risks(test_records, issues)
    assert len(risks) > 0, "应生成风险预警"
    print("✓ 风险预警通过")
    
    # 测试输出格式
    output = format_output({'records': [r.to_dict() for r in test_records]}, 'markdown')
    assert '|' in output, "Markdown输出应包含表格"
    output = format_output({'records': [r.to_dict() for r in test_records]}, 'json')
    assert json.loads(output), "JSON输出应可解析"
    print("✓ 输出格式通过")
    
    print("\n所有自检通过！")
    return 0


def main():
    parser = argparse.ArgumentParser(description='备份核查工具 - 完整性校验与风险预警')
    parser.add_argument('--input', '-i', help='输入备份清单文件（支持文本/JSON/CSV）')
    parser.add_argument('--output', '-o', help='输出报告文件')
    parser.add_argument('--compare', '-c', nargs=2, metavar=('OLD', 'NEW'), help='对比两个版本的备份')
    parser.add_argument('--format', '-f', choices=['markdown', 'json', 'text'], default='markdown', help='输出格式')
    parser.add_argument('--separator', '-s', default='|', help='文本格式的分隔符')
    parser.add_argument('--selftest', action='store_true', help='运行自检')
    
    args = parser.parse_args()
    
    if args.selftest:
        return selftest()
    
    if not args.input and not args.compare:
        parser.error("必须提供 --input 或 --compare 参数")
    
    try:
        result = {}
        
        if args.compare:
            # 版本对比模式
            old_records = parse_input(args.compare[0])
            new_records = parse_input(args.compare[1])
            diff = compare_versions(old_records, new_records)
            result = {
                'diff': diff,
                'risks': generate_risks(new_records, check_completeness(new_records))
            }
        else:
            # 标准分析模式
            records = parse_input(args.input)
            completeness_issues = check_completeness(records)
            eval_result = evaluate_recovery(records)
            risks = generate_risks(records, completeness_issues)
            
            result = {
                'records': [r.to_dict() for r in records],
                'completeness_issues': completeness_issues,
                'recovery_evaluation': eval_result,
                'risks': risks,
                'summary': {
                    'total_records': len(records),
                    'issue_count': len(completeness_issues),
                    'risk_count': len(risks),
                    'recovery_score': eval_result['score'],
                    'recovery_level': eval_result['level']
                }
            }
        
        # 输出结果
        output_text = format_output(result, args.format, args.separator)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"报告已保存到: {args.output}")
        else:
            print(output_text)
        
        # 如果有高风险，返回非零退出码
        if result.get('risks'):
            high_risks = [r for r in result['risks'] if r['level'] == '高']
            if high_risks:
                print(f"\n警告: 发现 {len(high_risks)} 个高风险问题", file=sys.stderr)
                return 1
        
        return 0
        
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
