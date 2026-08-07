#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI-Anything: 自然语言转命令行工具
将中文操作意图转换为可执行命令行，内置命令速查库与匹配引擎。

注意：本工具使用启发式模板匹配，基于关键词和模式识别，可能无法理解复杂上下文。
所有生成的命令在执行前需用户确认，特别是涉及系统修改的操作。
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# ========== 内置命令知识库 ==========
COMMAND_DB = {
    "文件操作": {
        "keywords": ["创建", "新建", "touch", "复制", "拷贝", "移动", "剪切", "删除", "移除", "重命名", "查找", "搜索文件"],
        "commands": {
            "创建文件": "touch {filename}",
            "复制文件": "cp {source} {destination}",
            "移动文件": "mv {source} {destination}",
            "删除文件": "rm {file}",
            "重命名": "mv {old_name} {new_name}",
            "查找文件": "find {path} -name '{pattern}'",
            "打包压缩": "tar -czf {archive}.tar.gz {files}",
            "解压": "tar -xzf {archive}.tar.gz"
        }
    },
    "目录管理": {
        "keywords": ["切换目录", "进入目录", "列出", "显示", "统计大小", "递归", "目录大小"],
        "commands": {
            "切换目录": "cd {path}",
            "列出文件": "ls -l",
            "按时间排序": "ls -lt",
            "按大小排序": "ls -lS",
            "统计目录大小": "du -sh {path}",
            "递归遍历": "find {path} -type f"
        }
    },
    "进程管理": {
        "keywords": ["查看进程", "进程列表", "杀掉", "终止", "后台运行", "资源占用", "进程状态"],
        "commands": {
            "查看所有进程": "ps aux",
            "查看特定进程": "ps aux | grep {keyword}",
            "杀掉进程": "kill {pid}",
            "杀掉所有匹配进程": "pkill -f {keyword}",
            "后台运行": "nohup {command} &",
            "查看资源占用": "top"
        }
    },
    "系统服务": {
        "keywords": ["启动服务", "停止服务", "重启服务", "服务状态", "systemctl", "nginx", "docker服务"],
        "commands": {
            "启动服务": "sudo systemctl start {service}",
            "停止服务": "sudo systemctl stop {service}",
            "重启服务": "sudo systemctl restart {service}",
            "查看服务状态": "sudo systemctl status {service}",
            "开机自启": "sudo systemctl enable {service}"
        }
    },
    "网络操作": {
        "keywords": ["ping", "连通性", "端口", "监听", "下载", "网络测试", "curl", "wget"],
        "commands": {
            "测试连通性": "ping -c 4 {host}",
            "测试端口": "nc -zv {host} {port}",
            "查看端口监听": "ss -tlnp",
            "下载文件": "wget {url}",
            "HTTP请求": "curl {url}",
            "DNS查询": "nslookup {domain}"
        }
    },
    "文本处理": {
        "keywords": ["提取", "替换", "排序", "去重", "统计", "grep", "awk", "sed", "文本处理"],
        "commands": {
            "查找文本": "grep '{pattern}' {file}",
            "替换文本": "sed -i 's/{old}/{new}/g' {file}",
            "排序": "sort {file}",
            "去重": "uniq {file}",
            "统计行数": "wc -l {file}",
            "统计IP": "awk '{{print $1}}' {file} | sort | uniq -c"
        }
    },
    "磁盘管理": {
        "keywords": ["磁盘", "分区", "挂载", "格式化", "空间", "df", "du"],
        "commands": {
            "查看磁盘空间": "df -h",
            "查看目录占用": "du -sh *",
            "挂载分区": "mount {device} {mount_point}",
            "卸载分区": "umount {mount_point}",
            "查看分区表": "fdisk -l"
        }
    },
    "容器操作": {
        "keywords": ["docker", "容器", "镜像", "k8s", "kubernetes"],
        "commands": {
            "查看运行中容器": "docker ps",
            "查看所有容器": "docker ps -a",
            "启动容器": "docker start {container}",
            "停止容器": "docker stop {container}",
            "查看容器日志": "docker logs {container}",
            "构建镜像": "docker build -t {image_name} ."
        }
    },
    "权限管理": {
        "keywords": ["权限", "chmod", "chown", "属主", "执行权限"],
        "commands": {
            "修改权限": "chmod {mode} {file}",
            "修改属主": "chown {user}:{group} {file}",
            "添加执行权限": "chmod +x {file}",
            "递归修改权限": "chmod -R {mode} {directory}"
        }
    },
    "包管理": {
        "keywords": ["安装", "卸载", "更新", "搜索包", "apt", "yum", "pip", "npm"],
        "commands": {
            "apt安装": "sudo apt install {package}",
            "apt更新": "sudo apt update",
            "apt卸载": "sudo apt remove {package}",
            "pip安装": "pip install {package}",
            "npm安装": "npm install {package}",
            "搜索包": "apt search {keyword}"
        }
    }
}

# 同义词映射
SYNONYMS = {
    "查看": ["显示", "列出", "查询"],
    "杀掉": ["终止", "杀死", "结束"],
    "创建": ["新建", "生成", "建立"],
    "删除": ["移除", "清除", "干掉"],
    "复制": ["拷贝", "cp"],
    "移动": ["剪切", "mv"],
    "重启": ["重新启动", "restart"],
    "安装": ["装", "install"],
    "卸载": ["移除", "uninstall"]
}

# 高危命令模式
HIGH_RISK_PATTERNS = [
    r'\brm\s+-rf\b',
    r'\bmkfs\b',
    r'\bdd\s+if=',
    r'\b>:?\s*/dev/sd',
    r'\bshutdown\b',
    r'\breboot\b',
    r'\binit\s+0\b',
    r'\bkill\s+-9\s+0\b',
    r'\bchmod\s+-R\s+777\s+/',
]

def normalize_text(text: str) -> str:
    """文本标准化：去除多余空格，统一标点"""
    text = text.strip().lower()
    text = re.sub(r'[，。！？、；：""''（）]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_parameters(text: str) -> Dict[str, str]:
    """从自然语言中提取参数（文件路径、URL、端口等）"""
    params = {}
    
    # 提取文件路径
    path_match = re.search(r'[\w\-./\\]+\.(?:log|txt|py|sh|conf|json|xml|yaml|yml|tar|gz|zip)', text)
    if path_match:
        params['file'] = path_match.group()
        params['pattern'] = path_match.group().split('/')[-1].split('.')[0]
    
    # 提取URL
    url_match = re.search(r'https?://[\w\-./?&=#%]+', text)
    if url_match:
        params['url'] = url_match.group()
    
    # 提取IP地址
    ip_match = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text)
    if ip_match:
        params['host'] = ip_match.group()
    
    # 提取端口
    port_match = re.search(r'端口\s*(\d+)', text)
    if port_match:
        params['port'] = port_match.group(1)
    
    # 提取服务名
    service_match = re.search(r'(?:服务|nginx|apache|mysql|redis|docker)\s*[是为]?\s*(\w+)', text)
    if service_match:
        params['service'] = service_match.group(1)
    
    # 提取包名
    pkg_match = re.search(r'(?:安装|卸载|更新)\s+(\w+)', text)
    if pkg_match:
        params['package'] = pkg_match.group(1)
    
    # 提取替换文本参数
    replace_match = re.search(r'把\s*(\S+)\s*替换为\s*(\S+)', text)
    if replace_match:
        params['old'] = replace_match.group(1)
        params['new'] = replace_match.group(2)
    
    # 提取文件名（用于创建文件等）
    filename_match = re.search(r'(?:创建|新建|touch)\s+(\S+)', text)
    if filename_match:
        params['filename'] = filename_match.group(1)
    
    # 提取源和目标
    copy_match = re.search(r'(?:复制|拷贝)\s+(\S+)\s+(?:到|至)\s+(\S+)', text)
    if copy_match:
        params['source'] = copy_match.group(1)
        params['destination'] = copy_match.group(2)
    
    # 提取PID
    pid_match = re.search(r'pid\s*[=:]\s*(\d+)', text, re.IGNORECASE)
    if pid_match:
        params['pid'] = pid_match.group(1)
    
    return params

def match_command(text: str) -> Tuple[Optional[str], Optional[str], float]:
    """匹配命令，返回(类别, 命令模板, 匹配分数)"""
    normalized = normalize_text(text)
    best_match = None
    best_score = 0.0
    
    for category, data in COMMAND_DB.items():
        # 关键词匹配
        for keyword in data["keywords"]:
            if keyword in normalized:
                score = 0.6
                # 检查同义词
                for syn, syns in SYNONYMS.items():
                    if syn in normalized:
                        score += 0.2
                        break
                
                # 在命令模板中寻找最佳匹配
                for cmd_name, cmd_template in data["commands"].items():
                    cmd_score = score
                    # 检查命令名是否在文本中
                    if cmd_name in normalized:
                        cmd_score += 0.3
                    # 使用相似度匹配
                    similarity = SequenceMatcher(None, normalized, cmd_name).ratio()
                    cmd_score += similarity * 0.1
                    
                    if cmd_score > best_score:
                        best_score = cmd_score
                        best_match = (category, cmd_template)
    
    return best_match[0] if best_match else None, best_match[1] if best_match else None, best_score

def validate_command(command: str) -> Tuple[bool, str]:
    """验证命令安全性，返回(是否安全, 风险描述)"""
    # 检查高危命令模式
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, command):
            return False, f"检测到高危命令模式: {pattern}"
    
    # 检查shell元字符注入
    dangerous_chars = [';', '&&', '||', '`', '$(']
    for char in dangerous_chars:
        if char in command:
            # 排除合法的管道符和重定向
            if char == ';' and ';' in command:
                return False, f"检测到命令分隔符: {char}"
            if char == '&&':
                return False, f"检测到命令连接符: {char}"
            if char == '||':
                return False, f"检测到命令连接符: {char}"
            if char == '`':
                return False, f"检测到命令替换符: {char}"
            if char == '$(':
                return False, f"检测到命令替换符: {char}"
    
    return True, ""

def generate_command(text: str) -> Tuple[str, float]:
    """生成命令的主函数"""
    category, template, score = match_command(text)
    
    if not template:
        return f"# 无法匹配到合适的命令，请尝试更具体的描述\n# 例如：'查看当前目录文件'、'杀掉所有python进程'", 0.0
    
    # 提取参数
    params = extract_parameters(text)
    
    # 填充模板
    try:
        command = template.format(**params)
    except KeyError as e:
        missing = str(e).strip("'")
        command = template.replace(f"{{{missing}}}", f"<{missing}>")
    
    # 添加注释
    comment = f"# [{category}] {text}"
    return f"{comment}\n{command}", score

def execute_command(command: str, confirm_high_risk: bool = True) -> Tuple[int, str]:
    """安全执行命令，返回(退出码, 输出)"""
    # 提取实际命令（去掉注释行）
    cmd_lines = [line for line in command.split('\n') if not line.startswith('#')]
    if not cmd_lines:
        return 0, "无命令可执行"
    
    actual_cmd = ' '.join(cmd_lines).strip()
    
    # 验证命令安全性
    is_safe, risk_desc = validate_command(actual_cmd)
    if not is_safe:
        return 1, f"命令被拒绝: {risk_desc}"
    
    # 高危命令二次确认
    if confirm_high_risk and re.search(r'\brm\b|\bmv\b|\bdd\b|\bmkfs\b', actual_cmd):
        print(f"警告: 命令 '{actual_cmd}' 可能具有破坏性")
        response = input("确认执行? (y/N): ").strip().lower()
        if response != 'y':
            return 0, "命令已取消"
    
    # 使用列表参数形式执行，避免shell注入
    try:
        # 解析命令为参数列表
        args = shlex.split(actual_cmd)
        # 检查是否有管道
        if '|' in args:
            # 处理管道命令
            pipeline = actual_cmd.split('|')
            processes = []
            for i, cmd_part in enumerate(pipeline):
                cmd_args = shlex.split(cmd_part.strip())
                if i == 0:
                    proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    proc = subprocess.Popen(cmd_args, stdin=processes[-1].stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                processes.append(proc)
            
            # 等待最后一个进程完成，设置超时
            try:
                output, error = processes[-1].communicate(timeout=30)
                return processes[-1].returncode, output.decode() if output else error.decode()
            except subprocess.TimeoutExpired:
                # 终止所有进程
                for proc in processes:
                    proc.kill()
                return 1, "命令执行超时"
        else:
            # 简单命令，设置超时和输出限制
            try:
                result = subprocess.run(
                    args, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    check=False
                )
                # 限制输出大小
                output = result.stdout if result.returncode == 0 else result.stderr
                if len(output) > 10000:
                    output = output[:10000] + "\n... [输出已截断]"
                return result.returncode, output
            except subprocess.TimeoutExpired:
                return 1, "命令执行超时"
    except FileNotFoundError:
        return 1, f"命令不存在: {args[0] if args else 'unknown'}"
    except Exception as e:
        return 1, f"执行错误: {str(e)}"

def validate_commondb() -> Tuple[bool, str]:
    """验证COMMAND_DB完整性"""
    required_keys = ["keywords", "commands"]
    for category, data in COMMAND_DB.items():
        for key in required_keys:
            if key not in data:
                return False, f"分类 '{category}' 缺少 '{key}' 字段"
        if not isinstance(data["keywords"], list) or len(data["keywords"]) == 0:
            return False, f"分类 '{category}' 的 keywords 为空或不是列表"
        if not isinstance(data["commands"], dict) or len(data["commands"]) == 0:
            return False, f"分类 '{category}' 的 commands 为空或不是字典"
    return True, "COMMAND_DB 完整性验证通过"

def selftest() -> bool:
    """自检函数：验证核心功能"""
    test_cases = [
        ("查看当前目录文件", "ls -l"),
        ("杀掉所有python进程", "pkill -f python"),
        ("测试192.168.1.1的80端口", "nc -zv 192.168.1.1 80"),
        ("用apt安装htop", "sudo apt install htop"),
        ("查看所有运行中的容器", "docker ps"),
        ("给script.sh添加执行权限", "chmod +x script.sh"),
        ("把old替换为new在config.txt中", "sed -i 's/old/new/g' config.txt"),
    ]
    
    passed = 0
    total = len(test_cases) + 3  # 加上模板完整
