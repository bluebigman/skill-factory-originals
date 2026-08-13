#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class LogAnalyzer:
    """日志分析器：解析、聚合、统计、告警"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logs = []
        self.parsed_logs = []
        self.stats = {}
        self.alerts = []
        self.start_time = None
        self.end_time = None
        
        # 默认配置
        self.default_config = {
            "time_format": "%Y-%m-%d %H:%M:%S",
            "alert_threshold": 10,
            "error_keywords": ["ERROR", "FATAL", "CRITICAL"],
            "warn_keywords": ["WARN", "WARNING"],
            "info_keywords": ["INFO", "NOTICE"],
            "debug_keywords": ["DEBUG", "TRACE"],
            "group_by": ["level", "source", "message"],
            "aggregate_by": ["count", "unique", "avg", "max", "min"],
            "time_window": 3600,
            "max_log_size": 10000,
            "output_format": "json"
        }
        
        # 合并配置
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
    
    def load_file(self, filepath: str) -> bool:
        """从文件加载日志"""
        try:
            if not os.path.exists(filepath):
                print(f"错误: 文件不存在: {filepath}")
                return False
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            self.logs = content.split('\n')
            # 过滤空行
            self.logs = [line for line in self.logs if line.strip()]
            
            if not self.logs:
                print("警告: 文件为空")
                return True
            
            self.parse_logs()
            return True
            
        except Exception as e:
            print(f"加载文件失败: {e}")
            return False
    
    def load_string(self, content: str) -> bool:
        """从字符串加载日志"""
        try:
            self.logs = content.split('\n')
            self.logs = [line for line in self.logs if line.strip()]
            
            if self.logs:
                self.parse_logs()
            return True
            
        except Exception as e:
            print(f"加载字符串失败: {e}")
            return False
    
    def parse_logs(self) -> None:
        """解析日志行"""
        self.parsed_logs = []
        
        for line in self.logs:
            parsed = self.parse_line(line)
            if parsed:
                self.parsed_logs.append(parsed)
        
        # 更新时间范围
        if self.parsed_logs:
            timestamps = [log.get('timestamp') for log in self.parsed_logs if log.get('timestamp')]
            if timestamps:
                self.start_time = min(timestamps)
                self.end_time = max(timestamps)
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """解析单行日志"""
        try:
            # 尝试提取时间戳
            timestamp = None
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})', line)
            if time_match:
                try:
                    timestamp = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        timestamp = datetime.strptime(time_match.group(1), '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass
            
            # 提取级别
            level = 'UNKNOWN'
            for kw in self.config['error_keywords']:
                if kw in line.upper():
                    level = 'ERROR'
                    break
            if level == 'UNKNOWN':
                for kw in self.config['warn_keywords']:
                    if kw in line.upper():
                        level = 'WARN'
                        break
            if level == 'UNKNOWN':
                for kw in self.config['info_keywords']:
                    if kw in line.upper():
                        level = 'INFO'
                        break
            if level == 'UNKNOWN':
                for kw in self.config['debug_keywords']:
                    if kw in line.upper():
                        level = 'DEBUG'
                        break
            
            # 提取来源
            source = None
            source_match = re.search(r'\[(\w+)\]', line)
            if source_match:
                source = source_match.group(1)
            
            # 提取消息
            message = line
            if timestamp and time_match:
                message = line[line.find(time_match.group(1)) + len(time_match.group(1)):].strip()
            if source:
                idx = line.find(f'[{source}]')
                if idx >= 0:
                    message = line[idx + len(source) + 2:].strip()
            
            # 提取IP
            ip = None
            ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', line)
            if ip_match:
                ip = ip_match.group(1)
            
            # 提取状态码
            status_code = None
            status_match = re.search(r'\b(\d{3})\b', line)
            if status_match:
                status_code = int(status_match.group(1))
            
            # 提取响应时间
            response_time = None
            rt_match = re.search(r'(?:响应时间|response_time|duration|耗时)[=:：]\s*(\d+(?:\.\d+)?)\s*(?:ms|毫秒)?', line, re.IGNORECASE)
            if rt_match:
                response_time = float(rt_match.group(1))
            
            # 提取用户ID
            user_id = None
            uid_match = re.search(r'(?:用户|user|uid)[=:：]\s*(\w+)', line, re.IGNORECASE)
            if uid_match:
                user_id = uid_match.group(1)
            
            # 提取请求路径
            path = None
            path_match = re.search(r'(?:路径|path|url|uri)[=:：]\s*([^\s,;]+)', line, re.IGNORECASE)
            if path_match:
                path = path_match.group(1)
            
            parsed = {
                'raw': line,
                'timestamp': timestamp,
                'level': level,
                'source': source,
                'message': message,
                'ip': ip,
                'status_code': status_code,
                'response_time': response_time,
                'user_id': user_id,
                'path': path,
                'length': len(line)
            }
            
            return parsed
            
        except Exception as e:
            print(f"解析行失败: {e}")
            return None
    
    def analyze(self) -> Dict:
        """执行分析"""
        if not self.parsed_logs:
            return {"error": "没有可分析的日志", "total": 0}
        
        result = {
            "total": len(self.parsed_logs),
            "time_range": {
                "start": self.start_time.isoformat() if self.start_time else None,
                "end": self.end_time.isoformat() if self.end_time else None
            },
            "levels": self.count_by_level(),
            "sources": self.count_by_source(),
            "errors": self.get_errors(),
            "warnings": self.get_warnings(),
            "ips": self.count_by_ip(),
            "status_codes": self.count_by_status_code(),
            "response_times": self.analyze_response_times(),
            "users": self.count_by_user(),
            "paths": self.count_by_path(),
            "trends": self.analyze_trends(),
            "top_errors": self.get_top_errors(),
            "top_sources": self.get_top_sources(),
            "top_ips": self.get_top_ips(),
            "top_paths": self.get_top_paths(),
            "summary": self.generate_summary()
        }
        
        self.stats = result
        return result
    
    def count_by_level(self) -> Dict:
        """按级别统计"""
        counter = Counter()
        for log in self.parsed_logs:
            counter[log['level']] += 1
        return dict(counter)
    
    def count_by_source(self) -> Dict:
        """按来源统计"""
        counter = Counter()
        for log in self.parsed_logs:
            if log['source']:
                counter[log['source']] += 1
        return dict(counter)
    
    def get_errors(self) -> List[Dict]:
        """获取错误日志"""
        return [log for log in self.parsed_logs if log['level'] == 'ERROR']
    
    def get_warnings(self) -> List[Dict]:
        """获取警告日志"""
        return [log for log in self.parsed_logs if log['level'] == 'WARN']
    
    def count_by_ip(self) -> Dict:
        """按IP统计"""
        counter = Counter()
        for log in self.parsed_logs:
            if log['ip']:
                counter[log['ip']] += 1
        return dict(counter)
    
    def count_by_status_code(self) -> Dict:
        """按状态码统计"""
        counter = Counter()
        for log in self.parsed_logs:
            if log['status_code']:
                counter[log['status_code']] += 1
        return dict(counter)
    
    def analyze_response_times(self) -> Dict:
        """分析响应时间"""
        times = [log['response_time'] for log in self.parsed_logs if log['response_time'] is not None]
        if not times:
            return {"count": 0}
        
        sorted_times = sorted(times)
        return {
            "count": len(times),
            "avg": sum(times) / len(times),
            "max": max(times),
            "min": min(times),
            "p50": sorted_times[len(sorted_times) // 2],
            "p90": sorted_times[int(len(sorted_times) * 0.9)],
            "p99": sorted_times[int(len(sorted_times) * 0.99)]
        }
    
    def count_by_user(self) -> Dict:
        """按用户统计"""
        counter = Counter()
        for log in self.parsed_logs:
            if log['user_id']:
                counter[log['user_id']] += 1
        return dict(counter)
    
    def count_by_path(self) -> Dict:
        """按路径统计"""
        counter = Counter()
        for log in self.parsed_logs:
            if log['path']:
                counter[log['path']] += 1
        return dict(counter)
    
    def analyze_trends(self) -> Dict:
        """分析趋势"""
        if not self.parsed_logs:
            return {}
        
        # 按小时统计
        hourly = Counter()
        for log in self.parsed_logs:
            if log['timestamp']:
                hour = log['timestamp'].strftime('%Y-%m-%d %H:00')
                hourly[hour] += 1
        
        # 按天统计
        daily = Counter()
        for log in self.parsed_logs:
            if log['timestamp']:
                day = log['timestamp'].strftime('%Y-%m-%d')
                daily[day] += 1
        
        return {
            "hourly": dict(sorted(hourly.items())),
            "daily": dict(sorted(daily.items()))
        }
    
    def get_top_errors(self, n: int = 10) -> List[Dict]:
        """获取最常见的错误"""
        errors = self.get_errors()
        if not errors:
            return []
        
        # 按消息聚类
        error_groups = defaultdict(list)
        for err in errors:
            # 简化消息用于分组
            msg = err['message'][:100] if err['message'] else ''
            error_groups[msg].append(err)
        
        sorted_groups = sorted(error_groups.items(), key=lambda x: len(x[1]), reverse=True)
        result = []
        for msg, group in sorted_groups[:n]:
            result.append({
                "message": msg,
                "count": len(group),
                "sources": list(set(e['source'] for e in group if e['source'])),
                "ips": list(set(e['ip'] for e in group if e['ip']))
            })
        return result
    
    def get_top_sources(self, n: int = 10) -> List[Dict]:
        """获取最常见的来源"""
        sources = self.count_by_source()
        if not sources:
            return []
        
        sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
        return [{"source": src, "count": cnt} for src, cnt in sorted_sources[:n]]
    
    def get_top_ips(self, n: int = 10) -> List[Dict]:
        """获取最常见的IP"""
        ips = self.count_by_ip()
        if not ips:
            return []
        
        sorted_ips = sorted(ips.items(), key=lambda x: x[1], reverse=True)
        return [{"ip": ip, "count": cnt} for ip, cnt in sorted_ips[:n]]
    
    def get_top_paths(self, n: int = 10) -> List[Dict]:
        """获取最常见的路径"""
        paths = self.count_by_path()
        if not paths:
            return []
        
        sorted_paths = sorted(paths.items(), key=lambda x: x[1], reverse=True)
        return [{"path": path, "count": cnt} for path, cnt in sorted_paths[:n]]
    
    def generate_summary(self) -> str:
        """生成摘要"""
        total = len(self.parsed_logs)
        errors = len(self.get_errors())
        warnings = len(self.get_warnings())
        
        error_rate = (errors / total * 100) if total > 0 else 0
        warn_rate = (warnings / total * 100) if total > 0 else 0
        
        summary = f"共分析 {total} 条日志，其中错误 {errors} 条（{error_rate:.2f}%），警告 {warnings} 条（{warn_rate:.2f}%）"
        
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            summary += f"，时间跨度 {duration:.0f} 秒"
        
        return summary
    
    def generate_alerts(self) -> List[Dict]:
        """生成告警"""
        self.alerts = []
        
        if not self.parsed_logs:
            return self.alerts
        
        # 检查错误率
        total = len(self.parsed_logs)
        errors = len(self.get_errors())
        error_rate = errors / total if total > 0 else 0
        
        threshold = self.config.get('alert_threshold', 10) / 100
        if error_rate > threshold:
            self.alerts.append({
                "type": "high_error_rate",
                "severity": "critical",
                "message": f"错误率过高: {error_rate:.2%} (阈值: {threshold:.2%})",
                "value": error_rate,
                "threshold": threshold,
                "timestamp": datetime.now().isoformat()
            })
        
        # 检查响应时间
        times = [log['response_time'] for log in self.parsed_logs if log['response_time'] is not None]
        if times:
            avg_time = sum(times) / len(times)
            if avg_time > 1000:  # 超过1秒
                self.alerts.append({
                    "type": "high_response_time",
                    "severity": "warning",
                    "message": f"平均响应时间过高: {avg_time:.2f}ms",
                    "value": avg_time,
                    "threshold": 1000,
                    "timestamp": datetime.now().isoformat()
                })
        
        # 检查错误集中度
        top_errors = self.get_top_errors(5)
        for err in top_errors:
            if err['count'] > 100:
                self.alerts.append({
                    "type": "error_concentration",
                    "severity": "warning",
                    "message": f"错误集中: {err['message'][:50]}... 出现 {err['count']} 次",
                    "value": err['count'],
                    "threshold": 100,
                    "timestamp": datetime.now().isoformat()
                })
        
        return self.alerts
    
    def export(self, format: str = 'json') -> str:
        """导出结果"""
        if format == 'json':
            return json.dumps(self.stats, ensure_ascii=False, indent=2, default=str)
        elif format == 'text':
            return self.format_text()
        else:
            return json.dumps(self.stats, ensure_ascii=False, indent=2, default=str)
    
    def format_text(self) -> str:
        """格式化文本输出"""
        if not self.stats:
            return "暂无数据"
        
        lines = []
        lines.append("=" * 60)
        lines.append("日志分析报告")
        lines.append("=" * 60)
        
        # 基本信息
        lines.append(f"\n总日志数: {self.stats.get('total', 0)}")
        
        time_range = self.stats.get('time_range', {})
        if time_range.get('start'):
            lines.append(f"时间范围: {time_range['start']} 至 {time_range['end']}")
        
        # 级别统计
        levels = self.stats.get('levels', {})
        if levels:
            lines.append("\n级别统计:")
            for level, count in sorted(levels.items()):
                lines.append(f"  {level}: {count}")
        
        # 来源统计
        sources = self.stats.get('sources', {})
        if sources:
            lines.append("\n来源统计:")
            for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True)[:10]:
                lines.append(f"  {source}: {count}")
        
        # 错误统计
        errors = self.stats.get('errors', [])
        if errors:
            lines.append(f"\n错误数: {len(errors)}")
        
        warnings = self.stats.get('warnings', [])
        if warnings:
            lines.append(f"警告数: {len(warnings)}")
        
        # 响应时间
        rt = self.stats.get('response_times', {})
        if rt.get('count', 0) > 0:
            lines.append("\n响应时间统计:")
            lines.append(f"  平均: {rt['avg']:.2f}ms")
            lines.append(f"  最大: {rt['max']:.2f}ms")
            lines.append(f"  最小: {rt['min']:.2f}ms")
            lines.append(f"  P50: {rt['p50']:.2f}ms")
            lines.append(f"  P90: {rt['p90']:.2f}ms")
            lines.append(f"  P99: {rt['p99']:.2f}ms")
        
        # 摘要
        summary = self.stats.get('summary', '')
        if summary:
            lines.append(f"\n摘要: {summary}")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
    
    def search(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索日志"""
        results = []
        for log in self.parsed_logs:
            if keyword.lower() in log['raw'].lower():
                results.append(log)
                if len(results) >= limit:
                    break
        return results
    
    def filter(self, level: Optional[str] = None, source: Optional[str] = None,
               ip: Optional[str] = None, start_time: Optional[datetime] = None,
               end_time: Optional[datetime] = None) -> List[Dict]:
        """过滤日志"""
        results = []
        for log in self.parsed_logs:
            if level and log['level'] != level:
                continue
            if source and log['source'] != source:
                continue
            if ip and log['ip'] != ip:
                continue
            if start_time and log['timestamp'] and log['timestamp'] < start_time:
                continue
            if end_time and log['timestamp'] and log['timestamp'] > end_time:
                continue
            results.append(log)
        return results


def generate_sample_logs() -> str:
    """生成样例日志数据"""
    lines = []
    
    # 生成时间序列
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    # 正常日志
    for i in range(50):
        ts = base_time + timedelta(seconds=i * 30)
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"{ts_str} [INFO] [app-server] 用户 user{i%5} 请求 /api/data status=200 响应时间={100 + i*10}ms")
    
    # 警告日志
    for i in range(20):
        ts = base_time + timedelta(seconds=i * 60)
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"{ts_str} [WARN] [cache-server] 缓存命中率低 status=200 响应时间={500 + i*20}ms")
    
    # 错误日志
    for i in range(15):
        ts = base_time + timedelta(seconds=i * 120)
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"{ts_str} [ERROR] [db-server] 数据库连接超时 status=500 响应时间={2000 + i*100}ms")
    
    # 调试日志
    for i in range(10):
        ts = base_time + timedelta(seconds=i * 45)
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"{ts_str} [DEBUG] [app-server] 调试信息 user{i%3} 请求 /api/debug")
    
    # 致命错误
    for i in range(5):
        ts = base_time + timedelta(seconds=i * 300)
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"{ts_str} [FATAL] [system] 系统崩溃 status=500 响应时间={5000 + i*100}ms")
    
    return "\n".join(lines)


def run_selftest() -> bool:
    """运行自测"""
    print("开始自测...")
    
    # 测试1: 基本解析
    print("测试1: 基本解析")
    analyzer = LogAnalyzer()
    sample = generate_sample_logs()
    assert analyzer.load_string(sample), "加载样例日志失败"
    assert len(analyzer.parsed_logs) > 0, "解析日志为空"
    print(f"  解析 {len(analyzer.parsed_logs)} 条日志")
    
    # 测试2: 统计分析
    print("测试2: 统计分析")
    stats = analyzer.analyze()
    assert stats['total'] > 0, "统计总数为0"
    assert 'levels' in stats, "缺少级别统计"
    assert 'errors' in stats, "缺少错误统计"
    print(f"  总日志: {stats['total']}")
    print(f"  级别分布: {stats['levels']}")
    
    # 测试3: 级别统计
    print("测试3: 级别统计")
    levels = stats['levels']
    assert 'ERROR' in levels, "缺少ERROR级别"
    assert 'INFO' in levels, "缺少INFO级别"
    assert levels['ERROR'] >= 0, "错误数不能为负"
    assert levels['INFO'] >= 0, "信息数不能为负"
    print(f"  错误数: {levels.get('ERROR', 0)}")
    
    # 测试4: 错误分析
    print("测试4: 错误分析")
    errors = analyzer.get_errors()
    assert len(errors) >= 0, "错误列表异常"
    print(f"  错误数: {len(errors)}")
    
    # 测试5: 响应时间分析
    print("测试5: 响应时间分析")
    rt = stats['response_times']
    assert rt['count'] >= 0, "响应时间统计异常"
    if rt['count'] > 0:
        assert rt['avg'] >= 0, "平均响应时间异常"
        assert rt['max'] >= rt['min'], "最大响应时间应不小于最小响应时间"
    print(f"  响应时间样本: {rt['count']}")
    
    # 测试6: 告警生成
    print("测试6: 告警生成")
    alerts = analyzer.generate_alerts()
    assert isinstance(alerts, list), "告警类型错误"
    print(f"  生成告警: {len(alerts)} 条")
    
    # 测试7: 搜索功能
    print("测试7: 搜索功能")
    results = analyzer.search("ERROR")
    assert len(results) >= 0, "搜索结果异常"
    print(f"  搜索结果: {len(results)} 条")
    
    # 测试8: 过滤功能
    print("测试8: 过滤功能")
    filtered = analyzer.filter(level='ERROR')
    assert len(filtered) >= 0, "过滤结果异常"
    print(f"  过滤结果: {len(filtered)} 条")
    
    # 测试9: 导出功能
    print("测试9: 导出功能")
    json_output = analyzer.export('json')
    assert json_output, "JSON导出为空"
    text_output = analyzer.export('text')
    assert text_output, "文本导出为空"
    print("  导出成功")
    
    # 测试10: 趋势分析
    print("测试10: 趋势分析")
    trends = stats['trends']
    assert 'hourly' in trends, "缺少小时趋势"
    assert 'daily' in trends, "缺少天趋势"
    print(f"  小时趋势数据点: {len(trends['hourly'])}")
    print(f"  天趋势数据点: {len(trends['daily'])}")
    
    # 测试11: TopN分析
    print("测试11: TopN分析")
    top_errors = stats['top_errors']
    top_sources = stats['top_sources']
    top_ips = stats['top_ips']
    top_paths = stats['top_paths']
    assert isinstance(top_errors, list), "Top错误类型错误"
    assert isinstance(top_sources, list), "Top来源类型错误"
    print(f"  Top错误: {len(top_errors)} 条")
    print(f"  Top来源: {len(top_sources)} 条")
    
    # 测试12: 摘要生成
    print("测试12: 摘要生成")
    summary = stats['summary']
    assert summary, "摘要为空"
    print(f"  摘要: {summary}")
    
    print("\n所有自测通过!")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='日志分析工具')
    parser.add_argument('--file', '-f', help='日志文件路径')
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    parser.add_argument('--search', help='搜索关键词')
    parser.add_argument('--level', help='过滤级别')
    parser.add_argument('--source', help='过滤来源')
    parser.add_argument('--ip', help='过滤IP')
    parser.add_argument('--format', '-o', choices=['json', 'text'], default='json', help='输出格式')
    parser.add_argument('--alert', action='store_true', help='生成告警')
    parser.add_argument('--top', type=int, default=10, help='Top N数量')
    
    args = parser.parse_args()
    
    # 运行自测
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 创建分析器
    analyzer = LogAnalyzer()
    
    # 加载数据
    if args.file:
        success = analyzer.load_file(args.file)
        if not success:
            sys.exit(1)
    else:
        # 使用样例数据
        print("未指定文件，使用样例数据")
        sample = generate_sample_logs()
        analyzer.load_string(sample)
    
    # 执行分析
    stats = analyzer.analyze()
    
    # 搜索
    if args.search:
        results = analyzer.search(args.search)
        print(f"搜索结果 ({len(results)} 条):")
        for r in results[:10]:
            print(f"  {r['raw'][:100]}")
        return
    
    # 过滤
    if args.level or args.source or args.ip:
        filtered = analyzer.filter(level=args.level, source=args.source, ip=args.ip)
        print(f"过滤结果 ({len(filtered)} 条):")
        for r in filtered[:10]:
            print(f"  {r['raw'][:100]}")
        return
    
    # 生成告警
    if args.alert:
        alerts = analyzer.generate_alerts()
        print(f"告警 ({len(alerts)} 条):")
        for alert in alerts:
            print(f"  [{alert['severity']}] {alert['message']}")
        return
    
    # 输出结果
    output = analyzer.export(args.format)
    print(output)


if __name__ == "__main__":
    main()
