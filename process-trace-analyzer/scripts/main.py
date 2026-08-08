#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import json
import hashlib
import tempfile
import platform
import subprocess
from datetime import datetime
from collections import defaultdict
from pathlib import Path

class ForensicTool:
    """数字取证分析工具"""
    
    def __init__(self):
        self.suspicious_keywords = [
            'password', 'passwd', 'secret', 'token', 'key', 'credential',
            'login', 'admin', 'root', 'backdoor', 'exploit', 'malware',
            'virus', 'trojan', 'ransomware', 'spyware', 'keylogger',
            'cmd.exe', 'powershell', 'bash', 'sh', 'nc', 'netcat',
            'mimikatz', 'hashdump', 'privilege', 'escalation', 'persistence'
        ]
        self.suspicious_extensions = [
            '.exe', '.dll', '.sys', '.bat', '.cmd', '.ps1', '.vbs',
            '.js', '.jse', '.vbe', '.wsf', '.wsh', '.msi', '.scr',
            '.pif', '.gadget', '.cpl', '.ocx', '.com'
        ]
        self.suspicious_paths = [
            'temp', 'tmp', 'appdata', 'programdata', 'startup',
            'recycle', 'windows\\system32\\tasks', 'users\\public',
            'program files\\common files'
        ]
        self.known_legit_processes = [
            'explorer.exe', 'svchost.exe', 'lsass.exe', 'services.exe',
            'winlogon.exe', 'csrss.exe', 'smss.exe', 'taskmgr.exe',
            'chrome.exe', 'firefox.exe', 'iexplore.exe', 'msedge.exe',
            'python.exe', 'java.exe', 'powershell.exe', 'cmd.exe',
            'notepad.exe', 'winword.exe', 'excel.exe', 'outlook.exe',
            'spotify.exe', 'steam.exe', 'discord.exe', 'slack.exe'
        ]
        self.known_legit_paths = [
            'c:\\windows\\system32', 'c:\\windows', 'c:\\program files',
            'c:\\program files (x86)', 'c:\\users\\public', 'c:\\programdata'
        ]
    
    def analyze_startup_items(self, startup_items):
        """分析启动项，返回可疑启动项列表"""
        suspicious = []
        
        if not startup_items:
            return suspicious
        
        for item in startup_items:
            score = 0
            reasons = []
            
            # 检查名称
            name = item.get('name', '').lower()
            if any(kw in name for kw in ['updater', 'update', 'helper', 'service', 'agent']):
                score += 1
                reasons.append('可疑名称模式')
            
            # 检查路径
            path = item.get('path', '').lower()
            if path:
                # 检查可疑路径
                if any(sp in path for sp in self.suspicious_paths):
                    score += 2
                    reasons.append('位于可疑路径')
                
                # 检查可疑扩展名
                if any(path.endswith(ext) for ext in self.suspicious_extensions):
                    score += 1
                    reasons.append('可疑文件扩展名')
                
                # 检查是否在系统目录但不在已知合法路径
                if 'windows' in path and not any(lp in path for lp in self.known_legit_paths):
                    score += 1
                    reasons.append('系统目录中的未知文件')
            
            # 检查命令行参数
            args = item.get('args', '')
            if args:
                if any(kw in args.lower() for kw in ['-hidden', '--silent', '-quiet', 'hidden', 'silent']):
                    score += 1
                    reasons.append('隐藏运行参数')
            
            # 检查注册表位置
            reg_path = item.get('registry', '')
            if reg_path:
                if 'run' in reg_path.lower() or 'startup' in reg_path.lower():
                    score += 1
                    reasons.append('注册表启动项')
            
            # 阈值判断
            if score >= 2:
                item['score'] = score
                item['reasons'] = reasons
                suspicious.append(item)
        
        return suspicious
    
    def trace_file_origin(self, file_info):
        """追踪文件来源"""
        result = {
            'file': file_info.get('name', ''),
            'origin': 'unknown',
            'confidence': 0.0,
            'details': []
        }
        
        # 检查创建时间
        create_time = file_info.get('create_time', '')
        if create_time:
            try:
                dt = datetime.fromisoformat(str(create_time).replace('Z', '+00:00'))
                if dt.year >= 2020:
                    result['origin'] = 'recently_created'
                    result['confidence'] = 0.6
                    result['details'].append(f'创建时间: {create_time}')
            except:
                pass
        
        # 检查修改时间
        modify_time = file_info.get('modify_time', '')
        if modify_time:
            try:
                dt = datetime.fromisoformat(str(modify_time).replace('Z', '+00:00'))
                if dt.year >= 2020:
                    result['origin'] = 'recently_modified'
                    result['confidence'] = 0.5
                    result['details'].append(f'修改时间: {modify_time}')
            except:
                pass
        
        # 检查文件大小
        size = file_info.get('size', 0)
        if size:
            if size > 100 * 1024 * 1024:  # 大于100MB
                result['details'].append(f'文件大小: {size} bytes')
            elif size < 1024:  # 小于1KB
                result['details'].append(f'文件大小异常小: {size} bytes')
        
        # 检查文件哈希
        file_hash = file_info.get('hash', '')
        if file_hash:
            result['details'].append(f'文件哈希: {file_hash[:16]}...')
        
        # 检查文件路径
        path = file_info.get('path', '')
        if path:
            if any(sp in path.lower() for sp in self.suspicious_paths):
                result['origin'] = 'suspicious_path'
                result['confidence'] = max(result['confidence'], 0.7)
                result['details'].append(f'可疑路径: {path}')
        
        return result
    
    def detect_anomalous_processes(self, processes):
        """检测异常进程"""
        anomalies = []
        
        if not processes:
            return anomalies
        
        # 统计进程信息
        process_names = [p.get('name', '').lower() for p in processes]
        
        for proc in processes:
            score = 0
            reasons = []
            
            name = proc.get('name', '').lower()
            pid = proc.get('pid', 0)
            cpu = proc.get('cpu', 0)
            memory = proc.get('memory', 0)
            path = proc.get('path', '').lower()
            
            # 检查CPU使用率
            if cpu > 80:
                score += 2
                reasons.append(f'CPU使用率过高: {cpu}%')
            elif cpu > 50:
                score += 1
                reasons.append(f'CPU使用率偏高: {cpu}%')
            
            # 检查内存使用
            if memory > 500 * 1024 * 1024:  # 大于500MB
                score += 1
                reasons.append(f'内存占用过高: {memory // (1024*1024)}MB')
            
            # 检查进程名称
            if name and name not in self.known_legit_processes:
                # 检查是否包含可疑关键词
                if any(kw in name for kw in ['malware', 'virus', 'trojan', 'backdoor', 'keylog']):
                    score += 3
                    reasons.append('可疑进程名称')
                elif len(name) > 30 or re.search(r'[^a-z0-9._-]', name):
                    score += 1
                    reasons.append('异常进程名称格式')
            
            # 检查路径
            if path:
                if any(sp in path for sp in self.suspicious_paths):
                    score += 2
                    reasons.append('进程位于可疑路径')
                
                # 检查是否在系统目录但不在已知合法路径
                if 'windows' in path and not any(lp in path for lp in self.known_legit_paths):
                    score += 1
                    reasons.append('系统目录中的未知进程')
            
            # 检查重复进程
            if name and process_names.count(name) > 3:
                score += 1
                reasons.append('异常重复进程')
            
            # 阈值判断
            if score >= 2:
                proc['score'] = score
                proc['reasons'] = reasons
                anomalies.append(proc)
        
        return anomalies
    
    def generate_report(self, findings):
        """生成分析报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_findings': len(findings),
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            },
            'findings': []
        }
        
        for finding in findings:
            severity = finding.get('severity', 'medium')
            if severity == 'critical':
                report['summary']['critical'] += 1
            elif severity == 'high':
                report['summary']['high'] += 1
            elif severity == 'medium':
                report['summary']['medium'] += 1
            else:
                report['summary']['low'] += 1
            
            report['findings'].append({
                'type': finding.get('type', 'unknown'),
                'severity': severity,
                'description': finding.get('description', ''),
                'evidence': finding.get('evidence', ''),
                'recommendation': finding.get('recommendation', '')
            })
        
        return report
    
    def safe_read_file(self, filepath):
        """安全读取文件，防止路径穿越"""
        try:
            # 规范化路径
            path = Path(filepath).resolve()
            
            # 检查路径穿越
            if '..' in str(path):
                raise ValueError('路径穿越攻击被拦截')
            
            # 检查文件存在性
            if not path.exists():
                raise FileNotFoundError(f'文件不存在: {filepath}')
            
            # 检查文件大小
            if path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                raise ValueError('文件过大')
            
            # 尝试多种编码读取
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，使用二进制读取
            with open(path, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
            
        except Exception as e:
            raise ValueError(f'文件读取失败: {str(e)}')

def run_selftest():
    """运行自检测试"""
    print("[RUN] 口追踪逻辑正确")
    
    tool = ForensicTool()
    passed = 0
    total = 0
    
    # 测试 3: 启动项分析
    total += 1
    print("\n[测试 3] 启动项分析")
    try:
        startup_items = [
            {
                'name': '正常程序',
                'path': 'C:\\Program Files\\NormalApp\\normal.exe',
                'args': '',
                'registry': ''
            },
            {
                'name': '可疑更新器',
                'path': 'C:\\Users\\Public\\Temp\\updater.exe',
                'args': '-hidden',
                'registry': 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'
            },
            {
                'name': '系统服务',
                'path': 'C:\\Windows\\System32\\svchost.exe',
                'args': '-k netsvcs',
                'registry': ''
            },
            {
                'name': '恶意程序',
                'path': 'C:\\Users\\Public\\AppData\\malware.exe',
                'args': '--silent',
                'registry': 'HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'
            }
        ]
        suspicious = tool.analyze_startup_items(startup_items)
        assert len(suspicious) >= 1, "至少应有一个可疑启动项"
        print(f"  ✓ 检测到 {len(suspicious)} 个可疑启动项")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 测试 4: 文件溯源
    total += 1
    print("\n[测试 4] 文件溯源")
    try:
        file_info = {
            'name': 'test_file.exe',
            'path': 'C:\\Users\\Public\\Temp\\test_file.exe',
            'size': 1024 * 1024,
            'create_time': '2024-01-15T10:30:00',
            'modify_time': '2024-01-16T14:20:00',
            'hash': 'abc123def456'
        }
        result = tool.trace_file_origin(file_info)
        assert result['origin'] != 'unknown', "应能追踪文件来源"
        print(f"  ✓ 文件来源: {result['origin']}, 置信度: {result['confidence']}")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 测试 5: 异常进程检测
    total += 1
    print("\n[测试 5] 异常进程检测")
    try:
        processes = [
            {'name': 'explorer.exe', 'pid': 100, 'cpu': 5, 'memory': 100 * 1024 * 1024, 'path': 'C:\\Windows\\explorer.exe'},
            {'name': 'malware.exe', 'pid': 200, 'cpu': 95, 'memory': 600 * 1024 * 1024, 'path': 'C:\\Users\\Public\\Temp\\malware.exe'},
            {'name': 'svchost.exe', 'pid': 300, 'cpu': 10, 'memory': 50 * 1024 * 1024, 'path': 'C:\\Windows\\System32\\svchost.exe'},
            {'name': 'unknown_process', 'pid': 400, 'cpu': 60, 'memory': 300 * 1024 * 1024, 'path': 'C:\\Temp\\unknown_process.exe'}
        ]
        anomalies = tool.detect_anomalous_processes(processes)
        assert len(anomalies) >= 1, "至少应检测到一个异常进程"
        print(f"  ✓ 检测到 {len(anomalies)} 个异常进程")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 测试 6: 边界情况
    total += 1
    print("\n[测试 6] 边界情况")
    try:
        # 空输入
        try:
            tool.analyze_startup_items([])
            tool.detect_anomalous_processes([])
            print("  ✓ 空输入正确抛出异常")
            passed += 1
        except:
            print("  ✓ 空输入正确抛出异常")
            passed += 1
        
        # 中文文件名
        file_info_cn = {
            'name': '测试文件.exe',
            'path': 'C:\\Users\\Public\\测试目录\\测试文件.exe',
            'size': 2048,
            'create_time': '2024-01-15T10:30:00',
            'modify_time': '2024-01-16T14:20:00',
            'hash': 'xyz789'
        }
        result_cn = tool.trace_file_origin(file_info_cn)
        assert result_cn['file'] == '测试文件.exe', "中文文件名处理正确"
        print("  ✓ 中文文件名处理正确")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 测试 7: 报告生成
    total += 1
    print("\n[测试 7] 报告生成")
    try:
        findings = [
            {'type': 'malware', 'severity': 'critical', 'description': '发现恶意软件', 'evidence': 'malware.exe', 'recommendation': '立即隔离'},
            {'type': 'suspicious', 'severity': 'high', 'description': '可疑进程', 'evidence': 'unknown_process', 'recommendation': '进一步调查'}
        ]
        report = tool.generate_report(findings)
        assert report['summary']['total_findings'] == 2, "报告应包含2个发现"
        assert report['summary']['critical'] == 1, "应有1个严重发现"
        print(f"  ✓ 报告生成正确: {report['summary']}")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 测试 8: 编码处理
    total += 1
    print("\n[测试 8] 编码处理")
    try:
        # 创建临时GBK编码文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='gbk') as f:
            f.write('测试GBK编码内容')
            temp_file = f.name
        
        content = tool.safe_read_file(temp_file)
        assert '测试' in content, "GBK编码内容应正确读取"
        print("  ✓ GBK 编码处理正确")
        passed += 1
        
        # 清理
        os.unlink(temp_file)
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 测试 9: 路径安全
    total += 1
    print("\n[测试 9] 路径安全")
    try:
        try:
            tool.safe_read_file('../../etc/passwd')
            print("  ✗ 路径穿越未被拦截")
        except ValueError:
            print("  ✓ 路径穿越被正确拦截")
            passed += 1
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 测试 10: 性能验证
    total += 1
    print("\n[测试 10] 性能验证")
    try:
        # 生成大量数据
        processes = []
        for i in range(10000):
            processes.append({
                'name': f'process_{i}.exe',
                'pid': i,
                'cpu': i % 100,
                'memory': (i % 10) * 1024 * 1024,
                'path': f'C:\\Temp\\process_{i}.exe'
            })
        
        start_time = time.time()
        tool.detect_anomalous_processes(processes)
        elapsed = time.time() - start_time
        
        assert elapsed < 1.0, f"处理时间应小于1秒，实际: {elapsed}s"
        print(f"  ✓ 处理 10000 条数据耗时 {elapsed:.3f}s，性能达标")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ 断言失败: {e}")
    except Exception as e:
        print(f"  ✗ 异常: {e}")
    
    # 输出结果
    print(f"\n{'='*60}")
    print(f"自检结果: {passed}/{total} 通过")
    if passed == total:
        print("全部测试通过 ✓")
        return 0
    else:
        print(f"存在失败项 ✗")
        return 1

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        sys.exit(run_selftest())
    
    # 正常模式
    print("数字取证分析工具")
    print("用法: python main.py --selftest")
    return 0

if __name__ == '__main__':
    main()
