#!/usr/bin/env python3
"""冒烟测试修复版 - 网络数据包分析工具"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime


def parse_pcap_line(line):
    """解析单行数据包记录"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    parts = line.split(',')
    if len(parts) < 5:
        return None
    
    try:
        timestamp = float(parts[0])
        src_ip = parts[1].strip()
        dst_ip = parts[2].strip()
        protocol = parts[3].strip().upper()
        size = int(parts[4].strip())
        
        return {
            'timestamp': timestamp,
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'protocol': protocol,
            'size': size
        }
    except (ValueError, IndexError):
        return None


def analyze_packets(packets):
    """分析数据包统计信息"""
    stats = {
        'total_packets': len(packets),
        'total_bytes': sum(p['size'] for p in packets),
        'protocols': defaultdict(int),
        'src_ips': defaultdict(int),
        'dst_ips': defaultdict(int),
        'connections': defaultdict(int),
        'time_range': None
    }
    
    if packets:
        times = [p['timestamp'] for p in packets]
        stats['time_range'] = {
            'start': min(times),
            'end': max(times),
            'duration': max(times) - min(times)
        }
    
    for p in packets:
        stats['protocols'][p['protocol']] += 1
        stats['src_ips'][p['src_ip']] += 1
        stats['dst_ips'][p['dst_ip']] += 1
        conn_key = f"{p['src_ip']}->{p['dst_ip']}"
        stats['connections'][conn_key] += 1
    
    return stats


def format_stats(stats):
    """格式化统计结果"""
    lines = []
    lines.append(f"总数据包数: {stats['total_packets']}")
    lines.append(f"总字节数: {stats['total_bytes']}")
    
    if stats['time_range']:
        tr = stats['time_range']
        lines.append(f"时间范围: {tr['start']:.3f} - {tr['end']:.3f} (时长 {tr['duration']:.3f}s)")
    
    lines.append("\n协议分布:")
    for proto, count in sorted(stats['protocols'].items()):
        lines.append(f"  {proto}: {count}")
    
    lines.append("\n源IP Top 5:")
    for ip, count in sorted(stats['src_ips'].items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  {ip}: {count}")
    
    lines.append("\n目的IP Top 5:")
    for ip, count in sorted(stats['dst_ips'].items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  {ip}: {count}")
    
    lines.append("\n连接 Top 5:")
    for conn, count in sorted(stats['connections'].items(), key=lambda x: -x[1])[:5]:
        lines.append(f"  {conn}: {count}")
    
    return '\n'.join(lines)


def read_pcap_file(filepath):
    """读取pcap文件"""
    packets = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                packet = parse_pcap_line(line)
                if packet:
                    packets.append(packet)
    except FileNotFoundError:
        print(f"错误: 文件 {filepath} 不存在", file=sys.stderr)
        return None
    except Exception as e:
        print(f"错误: 读取文件失败 - {e}", file=sys.stderr)
        return None
    
    return packets


def run_selftest():
    """自测试函数"""
    print("运行自测试...")
    
    # 测试数据
    test_data = [
        "1634567890.123,192.168.1.1,192.168.1.100,TCP,1200",
        "1634567890.456,192.168.1.2,192.168.1.100,UDP,800",
        "1634567890.789,192.168.1.1,192.168.1.100,TCP,1500",
        "1634567891.123,192.168.1.3,192.168.1.100,ICMP,64",
        "1634567891.456,192.168.1.1,192.168.1.200,TCP,900",
        "1634567891.789,192.168.1.2,192.168.1.100,UDP,1200",
        "1634567892.123,192.168.1.4,192.168.1.100,TCP,2048",
        "1634567892.456,192.168.1.1,192.168.1.100,TCP,512",
    ]
    
    # 解析测试
    packets = []
    for line in test_data:
        p = parse_pcap_line(line)
        assert p is not None, "解析数据包失败"
        packets.append(p)
    
    assert len(packets) == 8, f"数据包数量错误: {len(packets)}"
    
    # 统计测试
    stats = analyze_packets(packets)
    assert stats['total_packets'] == 8, "总数据包数错误"
    assert stats['total_bytes'] > 0, "总字节数应为正数"
    assert len(stats['protocols']) >= 3, "应有至少3种协议"
    assert stats['protocols']['TCP'] > 0, "TCP数据包数应为正数"
    assert stats['protocols']['UDP'] > 0, "UDP数据包数应为正数"
    
    # 时间范围测试
    assert stats['time_range'] is not None, "时间范围不应为空"
    assert stats['time_range']['duration'] > 0, "时长应为正数"
    
    # 格式化测试
    output = format_stats(stats)
    assert "总数据包数" in output, "输出应包含总数据包数"
    assert "协议分布" in output, "输出应包含协议分布"
    
    print("✓ 自测试通过!")
    return True


def main():
    parser = argparse.ArgumentParser(description='网络数据包分析工具')
    parser.add_argument('file', nargs='?', help='数据包文件路径')
    parser.add_argument('--selftest', action='store_true', help='运行自测试')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出')
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    if not args.file:
        print("错误: 请提供文件路径或使用 --selftest", file=sys.stderr)
        sys.exit(1)
    
    packets = read_pcap_file(args.file)
    if packets is None:
        sys.exit(1)
    
    if not packets:
        print("警告: 文件中没有有效的数据包记录", file=sys.stderr)
        sys.exit(0)
    
    stats = analyze_packets(packets)
    
    if args.json:
        # JSON输出
        json_stats = {
            'total_packets': stats['total_packets'],
            'total_bytes': stats['total_bytes'],
            'protocols': dict(stats['protocols']),
            'src_ips': dict(stats['src_ips']),
            'dst_ips': dict(stats['dst_ips']),
            'connections': dict(stats['connections']),
            'time_range': stats['time_range']
        }
        print(json.dumps(json_stats, indent=2))
    else:
        # 文本输出
        print(format_stats(stats))


if __name__ == '__main__':
    main()
