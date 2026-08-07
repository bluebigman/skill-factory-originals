#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data-visual-report — 配套执行器（原创实现，clean-room）
技能「data-visual-report」的轻量辅助脚本：解析同目录 SKILL.md，提供 CLI 入口、触发词匹配、能力速览。
零第三方依赖。
"""
from __future__ import annotations
import argparse, re, sys, json, csv, os, tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

HERE = Path(__file__).resolve().parent
TRIGGERS = ["data-visual-report"]


def load_spec() -> str:
    # 资产池/发布目录均为 SKILL.md 在技能根目录、scripts/ 为其子目录，故读父目录
    p = HERE.parent / "SKILL.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def match_trigger(text: str):
    low = text.lower()
    return [t for t in TRIGGERS if t.lower() in low]


def read_table_data(file_path: str, max_rows: int = 10000) -> List[Dict[str, Any]]:
    """读取表格数据（支持 CSV/JSON），返回字典列表
    
    处理：
    - CSV 使用 utf-8-sig 编码，自动处理 BOM
    - 捕获 UnicodeDecodeError 并尝试其他编码
    - 超大文件限制读取行数，避免内存溢出
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"输入文件不存在: {file_path}")
    
    if path.suffix.lower() == '.csv':
        # 尝试多种编码
        encodings = ['utf-8-sig', 'utf-8', 'gbk', 'latin-1']
        last_error = None
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding, newline='') as f:
                    reader = csv.DictReader(f)
                    data = []
                    for i, row in enumerate(reader):
                        if i >= max_rows:
                            print(f"警告: 文件超过 {max_rows} 行，仅读取前 {max_rows} 行", file=sys.stderr)
                            break
                        # 清理 BOM 和空字段
                        clean_row = {}
                        for k, v in row.items():
                            if k is None:
                                continue
                            k = k.strip().lstrip('\ufeff')
                            if v is not None:
                                v = v.strip()
                            clean_row[k] = v
                        data.append(clean_row)
                    return data
            except UnicodeDecodeError as e:
                last_error = e
                continue
        raise ValueError(f"无法解码 CSV 文件，尝试了 {encodings} 编码: {last_error}")
    
    elif path.suffix.lower() == '.json':
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                if isinstance(data, list):
                    if len(data) > max_rows:
                        print(f"警告: 文件超过 {max_rows} 行，仅读取前 {max_rows} 行", file=sys.stderr)
                        return data[:max_rows]
                    return data
                elif isinstance(data, dict) and 'data' in data:
                    if isinstance(data['data'], list):
                        if len(data['data']) > max_rows:
                            print(f"警告: 文件超过 {max_rows} 行，仅读取前 {max_rows} 行", file=sys.stderr)
                            return data['data'][:max_rows]
                        return data['data']
                raise ValueError("JSON 格式需为数组或包含 data 字段的对象")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")
    else:
        raise ValueError(f"不支持的文件格式: {path.suffix}，仅支持 CSV/JSON")


def _generate_ascii_chart(values: List[float], title: str, width: int = 50) -> str:
    """生成 ASCII 柱状图"""
    if not values:
        return f"{title}: 无数据"
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        # 所有值相同的情况
        lines = [f"{title} (所有值均为 {max_val:.2f}):"]
        lines.append("█" * width)
        return "\n".join(lines)
    
    lines = [f"{title} (范围: {min_val:.2f} - {max_val:.2f}):"]
    
    # 分 5 个区间显示分布
    bins = [0] * 5
    bin_width = (max_val - min_val) / 5
    for v in values:
        idx = min(4, int((v - min_val) / bin_width) if bin_width > 0 else 0)
        bins[idx] += 1
    
    max_count = max(bins) if max(bins) > 0 else 1
    labels = ["极低", "较低", "中等", "较高", "极高"]
    
    for i, (label, count) in enumerate(zip(labels, bins)):
        bar_len = int((count / max_count) * width)
        percentage = (count / len(values)) * 100
        lines.append(f"{label:>4} |{'█' * bar_len} {count} ({percentage:.1f}%)")
    
    return "\n".join(lines)


def generate_report(data: List[Dict[str, Any]]) -> str:
    """生成包含图表和结论的分析报告"""
    if not data:
        raise ValueError("输入数据为空")
    
    # 数据验证和统计
    headers = list(data[0].keys())
    row_count = len(data)
    
    # 数值列统计
    numeric_cols = []
    for col in headers:
        try:
            values = [float(row[col]) for row in data if row.get(col) not in (None, '')]
            if values:
                numeric_cols.append({
                    'name': col,
                    'values': values,
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values),
                    'std': (sum((v - sum(values)/len(values))**2 for v in values) / len(values)) ** 0.5
                })
        except (ValueError, TypeError):
            continue
    
    # 生成报告
    report_lines = []
    report_lines.append("# 数据可视化分析报告")
    report_lines.append(f"\n> 生成时间: {datetime.now(timezone.utc).isoformat()}")
    report_lines.append(f"> 数据规模: {row_count} 行 × {len(headers)} 列")
    
    # 图表部分（ASCII 柱状图）
    if numeric_cols:
        report_lines.append("\n## 图表分析")
        for col in numeric_cols[:3]:  # 最多展示3个数值列
            report_lines.append(f"\n### {col['name']} 分布")
            report_lines.append(_generate_ascii_chart(col['values'], col['name']))
            report_lines.append(f"\n统计: 最小值={col['min']:.2f} | 最大值={col['max']:.2f} | 平均值={col['avg']:.2f} | 标准差={col['std']:.2f}")
    
    # 结论部分
    report_lines.append("\n## 分析结论")
    
    if numeric_cols:
        # 找出最大/最小列
        max_col = max(numeric_cols, key=lambda x: x['avg'])
        min_col = min(numeric_cols, key=lambda x: x['avg'])
        
        report_lines.append(f"1. 数据共 {row_count} 条记录，包含 {len(headers)} 个字段")
        report_lines.append(f"2. 数值字段中，'{max_col['name']}' 平均值最高（{max_col['avg']:.2f}），'{min_col['name']}' 平均值最低（{min_col['avg']:.2f}）")
        
        # 基于标准差的分析
        for col in numeric_cols[:3]:
            cv = col['std'] / col['avg'] if col['avg'] != 0 else float('inf')
            if cv < 0.1:
                variability = "非常稳定"
            elif cv < 0.3:
                variability = "较为稳定"
            elif cv < 0.5:
                variability = "波动适中"
            else:
                variability = "波动较大"
            report_lines.append(f"3. '{col['name']}' 变异系数为 {cv:.2f}，数据{ variability }")
        
        # 数据完整性检查
        total_cells = row_count * len(headers)
        non_empty = sum(1 for row in data for v in row.values() if v not in (None, ''))
        completeness = non_empty / total_cells * 100 if total_cells > 0 else 0
        report_lines.append(f"4. 数据完整性: {completeness:.1f}%（{non_empty}/{total_cells} 个单元格有值）")
        
        if completeness < 80:
            report_lines.append("5. ⚠️ 数据完整性较低，建议检查缺失值")
        elif completeness < 95:
            report_lines.append("5. 数据完整性良好，存在少量缺失值")
        else:
            report_lines.append("5. 数据完整性优秀，无明显缺失")
    else:
        report_lines.append(f"1. 数据共 {row_count} 条记录，包含 {len(headers)} 个字段")
        report_lines.append("2. 未检测到数值型字段，无法进行数值统计分析")
        report_lines.append("3. 建议检查数据格式，确保包含数值型字段")
    
    report_lines.append("\n---")
    report_lines.append("*本报告由 data-visual-report 自动生成*")
    
    return "\n".join(report_lines)


def selftest() -> int:
    """自检：验证核心数据转换链路"""
    try:
        # 1. 基础检查
        assert TRIGGERS, "触发器列表为空"
        assert load_spec().strip(), "SKILL.md 为空"
        print("  [OK] 基础配置检查通过")
        
        # 2. 触发词匹配测试
        sample = " ".join(TRIGGERS[:1])
        got = match_trigger(sample)
        assert got, "触发匹配失败"
        print("  [OK] 触发匹配:", got)
        
        # 3. 核心链路测试：创建最小测试数据
        test_data = [
            {"name": "A", "value": 10},
            {"name": "B", "value": 20},
            {"name": "C", "value": 30},
            {"name": "D", "value": 25},
            {"name": "E", "value": 15}
        ]
        
        # 4. 测试报告生成
        report = generate_report(test_data)
        assert "图表分析" in report, "报告缺少图表部分"
        assert "分析结论" in report, "报告缺少结论部分"
        assert "data-visual-report" in report, "报告缺少技能标识"
        assert "█" in report, "报告缺少 ASCII 图表"
        assert "变异系数" in report, "报告缺少统计分析"
        print("  [OK] 报告生成成功，包含图表和结论")
        
        # 5. 测试文件读取（临时文件）- 测试 BOM 处理
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
            f.write(b'\xef\xbb\xbfname,value\r\nA,10\r\nB,20\r\nC,30\r\n')  # 带 BOM 的 UTF-8
            temp_path = f.name
        
        try:
            data = read_table_data(temp_path)
            assert len(data) == 3, "CSV 读取失败"
            assert data[0]['name'] == 'A', "BOM 处理失败"
            print("  [OK] CSV 文件读取成功（含 BOM 处理）")
        finally:
            os.unlink(temp_path)
        
        # 6. 测试 JSON 读取
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump({"data": [{"x": 1, "y": 2}, {"x": 3, "y": 4}]}, f)
            temp_json = f.name
        
        try:
            data = read_table_data(temp_json)
            assert len(data) == 2, "JSON 读取失败"
            print("  [OK] JSON 文件读取成功")
        finally:
            os.unlink(temp_json)
        
        # 7. 测试错误处理
        try:
            read_table_data("/nonexistent/file.csv")
            assert False, "应该抛出文件不存在异常"
        except FileNotFoundError:
            print("  [OK] 文件不存在异常处理正确")
        
        # 8. 测试空数据
        try:
            generate_report([])
            assert False, "应该抛出空数据异常"
        except ValueError:
            print("  [OK] 空数据异常处理正确")
        
        # 9. 测试超大文件限制
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("value\n")
            for i in range(15000):
                f.write(f"{i}\n")
            temp_large = f.name
        
        try:
            data = read_table_data(temp_large, max_rows=10000)
            assert len(data) == 10000, "超大文件行数限制失败"
            print("  [OK] 超大文件行数限制正确")
        finally:
            os.unlink(temp_large)
        
        print("== data-visual-report 自检通过 ✅ ==")
        return 0
        
    except Exception as e:
        print(f"  [FAIL] 自检失败: {e}")
        print("== data-visual-report 自检失败 ❌ ==")
        return 1


def main():
    ap = argparse.ArgumentParser(description="data-visual-report 配套执行器")
    ap.add_argument("--guide", action="store_true", help="打印能力速览")
    ap.add_argument("--match", default="", help="输入文本，匹配触发词")
    ap.add_argument("--selftest", action="store_true", help="离线自检")
    ap.add_argument("--input", default="", help="输入表格文件路径（CSV/JSON），生成分析报告")
    ap.add_argument("--max-rows", type=int, default=10000, help="最大读取行数（默认10000）")
    args = ap.parse_args()
    
    if args.selftest:
        return selftest()
    
    if args.input:
        try:
            data = read_table_data(args.input, max_rows=args.max_rows)
            report = generate_report(data)
            print(report)
            return 0
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    
    if args.match:
        print("命中触发词:", match_trigger(args.match))
        return 0
    
    if args.guide:
        md = load_spec()
        print("\n".join(l for l in md.splitlines() if l.strip())[:40])
        return 0
    
    print("用法: python run.py --guide | --match 文本 | --selftest | --input 文件.csv [--max-rows N]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
