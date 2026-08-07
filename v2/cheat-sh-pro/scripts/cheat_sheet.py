#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cheat_sheet.py — 终端速查工具（cheat-sh-pro 真实实现）
内置多领域命令速查字典，支持模糊搜索、领域过滤、随机速查、Markdown 导出。
纯标准库，零依赖。
"""
import argparse
import difflib
import os
import random
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

CHEATS = {
    "git": [
        {"cmd": "git log --oneline -10", "desc": "查看最近10条提交（简洁）", "scene": "快速回顾提交历史"},
        {"cmd": "git status -sb", "desc": "查看工作区状态（短格式+分支）", "scene": "提交前检查"},
        {"cmd": "git diff --stat", "desc": "查看未暂存改动统计", "scene": "提交前概览改动量"},
        {"cmd": "git stash push -m 'wip'", "desc": "暂存当前改动", "scene": "临时切换分支"},
        {"cmd": "git branch -a", "desc": "查看全部分支（含远程）", "scene": "确认分支存在性"},
        {"cmd": "git checkout -b feat/xx", "desc": "新建并切换分支", "scene": "开始新功能"},
        {"cmd": "git commit --amend -m 'new msg'", "desc": "修改最近一次提交信息", "scene": "提交信息写错"},
        {"cmd": "git log --graph --oneline --all", "desc": "图形化查看全部分支提交", "scene": "梳理分支结构"},
        {"cmd": "git reset --soft HEAD~1", "desc": "撤销提交但保留改动", "scene": "提交错了要重来"},
        {"cmd": "git blame -L 10,20 file.py", "desc": "查看指定行历史归属", "scene": "排查代码来源"},
    ],
    "docker": [
        {"cmd": "docker ps -a", "desc": "查看所有容器（含停止）", "scene": "找容器"},
        {"cmd": "docker images", "desc": "查看本地镜像列表", "scene": "确认镜像"},
        {"cmd": "docker exec -it c1 bash", "desc": "进入容器终端", "scene": "容器内调试"},
        {"cmd": "docker logs -f c1", "desc": "跟踪容器日志", "scene": "排查应用报错"},
        {"cmd": "docker system df", "desc": "查看磁盘占用", "scene": "清理前评估"},
        {"cmd": "docker rmi $(docker images -q -f dangling=true)", "desc": "清理悬空镜像", "scene": "释放磁盘"},
        {"cmd": "docker inspect c1 --format '{{.NetworkSettings.IPAddress}}'", "desc": "查容器IP（纯docker命令）", "scene": "容器间通信"},
        {"cmd": "docker compose up -d", "desc": "后台启动编排服务", "scene": "启动服务栈"},
        {"cmd": "docker stop $(docker ps -q)", "desc": "停止所有容器", "scene": "批量停止"},
        {"cmd": "docker rm $(docker ps -aq --filter status=exited)", "desc": "删除所有已退出容器", "scene": "清理容器"},
    ],
    "linux": [
        {"cmd": "grep -rn 'pattern' /path", "desc": "递归搜索文件内容", "scene": "查找代码中的关键词"},
        {"cmd": "find /path -name '*.log' -mtime +7", "desc": "查找7天前的日志文件", "scene": "清理旧日志"},
        {"cmd": "ps aux | grep python", "desc": "查看python进程", "scene": "排查进程状态"},
        {"cmd": "netstat -tlnp", "desc": "查看监听端口及进程", "scene": "确认端口占用"},
        {"cmd": "df -h", "desc": "查看磁盘空间使用", "scene": "磁盘容量检查"},
        {"cmd": "du -sh * | sort -rh | head -10", "desc": "查看当前目录各子项大小并排序", "scene": "定位大文件"},
        {"cmd": "tar czf backup.tar.gz /path", "desc": "压缩备份目录", "scene": "数据备份"},
        {"cmd": "rsync -avz /src/ user@host:/dst/", "desc": "同步目录到远程", "scene": "部署文件"},
        {"cmd": "chmod +x script.sh", "desc": "添加执行权限", "scene": "运行脚本前"},
        {"cmd": "systemctl status nginx", "desc": "查看服务状态", "scene": "服务异常排查"},
    ],
    "python": [
        {"cmd": "python -m venv .venv", "desc": "创建虚拟环境", "scene": "项目隔离依赖"},
        {"cmd": "pip install -r requirements.txt", "desc": "安装项目依赖", "scene": "部署环境"},
        {"cmd": "python -m pip list --outdated", "desc": "查看过期包", "scene": "依赖升级"},
        {"cmd": "python -c \"import json; print(json.dumps({'a': 1}))\"", "desc": "快速JSON序列化", "scene": "调试数据"},
        {"cmd": "python -m http.server 8000", "desc": "启动HTTP文件服务器", "scene": "局域网共享文件"},
        {"cmd": "python -m pdb script.py", "desc": "调试模式运行脚本", "scene": "排查代码问题"},
        {"cmd": "python -m cProfile script.py", "desc": "性能分析", "scene": "定位性能瓶颈"},
        {"cmd": "python -m unittest discover", "desc": "运行单元测试", "scene": "测试验证"},
        {"cmd": "python -m pip freeze > requirements.txt", "desc": "导出依赖清单", "scene": "项目部署"},
        {"cmd": "python -m compileall .", "desc": "编译所有py文件", "scene": "语法检查"},
    ],
    "javascript": [
        {"cmd": "npm init -y", "desc": "快速初始化项目", "scene": "新项目启动"},
        {"cmd": "npm install express", "desc": "安装express框架", "scene": "Web开发"},
        {"cmd": "npm run dev", "desc": "启动开发服务器", "scene": "本地开发"},
        {"cmd": "npx create-react-app my-app", "desc": "创建React应用", "scene": "React项目初始化"},
        {"cmd": "node -e \"console.log('hello')\"", "desc": "运行单行JS代码", "scene": "快速测试"},
        {"cmd": "npm audit fix", "desc": "修复依赖漏洞", "scene": "安全加固"},
        {"cmd": "npm test", "desc": "运行测试", "scene": "测试验证"},
        {"cmd": "npm run build", "desc": "构建生产版本", "scene": "部署准备"},
        {"cmd": "npm list --depth=0", "desc": "查看顶层依赖", "scene": "依赖管理"},
        {"cmd": "node --inspect app.js", "desc": "调试模式运行", "scene": "代码调试"},
    ],
    "kubernetes": [
        {"cmd": "kubectl get pods -A", "desc": "查看所有命名空间的Pod", "scene": "集群状态检查"},
        {"cmd": "kubectl logs -f pod-name", "desc": "跟踪Pod日志", "scene": "应用调试"},
        {"cmd": "kubectl exec -it pod-name -- bash", "desc": "进入Pod终端", "scene": "容器内调试"},
        {"cmd": "kubectl get svc -A", "desc": "查看所有服务", "scene": "服务发现"},
        {"cmd": "kubectl apply -f deployment.yaml", "desc": "应用配置", "scene": "部署更新"},
        {"cmd": "kubectl rollout status deployment/name", "desc": "查看部署状态", "scene": "发布监控"},
        {"cmd": "kubectl scale deployment/name --replicas=3", "desc": "扩缩容", "scene": "弹性伸缩"},
        {"cmd": "kubectl get nodes", "desc": "查看集群节点", "scene": "集群健康检查"},
        {"cmd": "kubectl describe pod pod-name", "desc": "查看Pod详情", "scene": "问题排查"},
        {"cmd": "kubectl port-forward svc/service-name 8080:80", "desc": "端口转发", "scene": "本地访问服务"},
    ],
}


def get_all_cheats():
    """返回所有领域的命令列表（扁平化）"""
    all_items = []
    for domain_items in CHEATS.values():
        all_items.extend(domain_items)
    return all_items


def get_domain_cheats(domain):
    """返回指定领域的命令列表，领域不存在时返回 None"""
    if domain not in CHEATS:
        return None
    return CHEATS[domain]


def fuzzy_search(keyword, items):
    """使用 difflib 进行模糊搜索，返回匹配列表（按相似度降序）"""
    keyword_lower = keyword.lower()
    scored_matches = []
    
    for item in items:
        # 收集所有可搜索字段
        searchable_text = f"{item['cmd']} {item['desc']} {item['scene']}".lower()
        
        # 1. 精确子串匹配（最高优先级）
        if keyword_lower in searchable_text:
            score = 1.0
        else:
            # 2. 使用 get_close_matches 进行模糊匹配
            close_matches = difflib.get_close_matches(
                keyword_lower,
                [item["cmd"].lower(), item["desc"].lower(), item["scene"].lower()],
                n=1,
                cutoff=0.3
            )
            if close_matches:
                # 计算相似度
                similarity = difflib.SequenceMatcher(
                    None, keyword_lower, close_matches[0]
                ).ratio()
                score = max(0.3, similarity)
            else:
                # 3. 使用 SequenceMatcher 计算整体相似度
                similarity = difflib.SequenceMatcher(
                    None, keyword_lower, searchable_text
                ).ratio()
                score = similarity * 0.6
        
        if score > 0.3:
            scored_matches.append((score, item))
    
    # 按相似度降序排序
    scored_matches.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored_matches]


def search_cheats(keyword, domain=None):
    """按关键词模糊搜索命令，返回 (匹配列表, 匹配数量)"""
    if domain:
        items = get_domain_cheats(domain)
        if items is None:
            return None, 0
    else:
        items = get_all_cheats()

    # 使用 fuzzy_search 进行搜索
    matches = fuzzy_search(keyword, items)
    return matches, len(matches)


def get_random_cheat(domain=None, seed=None):
    """随机返回一条命令，领域不存在时返回 None
    支持 seed 参数用于可复现性
    """
    if seed is not None:
        random.seed(seed)
    if domain:
        items = get_domain_cheats(domain)
        if items is None:
            return None
    else:
        items = get_all_cheats()
    if not items:
        return None
    return random.choice(items)


def format_table(items, start_index=1):
    """将命令列表格式化为表格文本"""
    if not items:
        return "（无匹配结果）"
    lines = []
    lines.append("| 序号 | 命令 | 描述 | 场景 |")
    lines.append("|------|------|------|------|")
    for i, item in enumerate(items, start=start_index):
        cmd = item["cmd"].replace("|", "\\|")
        desc = item["desc"].replace("|", "\\|")
        scene = item["scene"].replace("|", "\\|")
        lines.append(f"| {i} | `{cmd}` | {desc} | {scene} |")
    return "\n".join(lines)


def validate_shell_command(cmd):
    """验证 shell 命令安全性，防止注入风险"""
    # 使用 shlex.split 检查命令是否可安全解析
    try:
        parts = shlex.split(cmd)
        # 检查是否有危险字符
        dangerous_patterns = [
            r';\s*(rm|sudo|shutdown|reboot|mkfs|dd)',
            r'&&\s*(rm|sudo|shutdown|reboot|mkfs|dd)',
            r'\|\s*(rm|sudo|shutdown|reboot|mkfs|dd)',
            r'>\s*/dev/sd',
            r'2>\s*/dev/sd',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, cmd, re.IGNORECASE):
                return False
        return True
    except (ValueError, TypeError):
        return False


def export_markdown(filepath):
    """导出全部速查到 Markdown 文件（原子写入）"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = []
    lines.append("# 命令行速查手册（cheat-sh-pro）")
    lines.append("")
    lines.append(f"> 导出时间：{timestamp}")
    lines.append("")
    lines.append("## 全部命令速查")
    lines.append("")
    for domain, items in CHEATS.items():
        lines.append(f"### {domain}")
        lines.append("")
        lines.append(format_table(items))
        lines.append("")
    content = "\n".join(lines) + "\n"

    # 原子写入：先写临时文件，再 os.replace
    dir_path = os.path.dirname(os.path.abspath(filepath))
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".cheats_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, filepath)
    except Exception:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return filepath


def run_selftest():
    """自检：真实调用核心函数并断言关键输出"""
    # 1. 领域查询
    git_items = get_domain_cheats("git")
    assert git_items is not None, "git 领域应存在"
    assert len(git_items) == 10, f"git 领域应有 10 条，实际 {len(git_items)}"

    # 2. 不存在的领域
    assert get_domain_cheats("nonexist") is None, "不存在的领域应返回 None"

    # 3. 精确搜索
    matches, count = search_cheats("提交")
    assert count > 0, "搜索'提交'应有结果"
    assert all("提交" in item["desc"] or "提交" in item["scene"] or "提交" in item["cmd"] for item in matches), "搜索结果应包含关键词"

    # 4. 模糊搜索（测试 difflib 匹配）
    fuzzy_matches, fuzzy_count = search_cheats("log")
    assert fuzzy_count > 0, "模糊搜索'log'应有结果"
    assert any("log" in item["cmd"].lower() for item in fuzzy_matches), "模糊搜索结果应包含 log 相关命令"

    # 5. 模糊搜索（测试拼写变体）
    fuzzy_matches2, fuzzy_count2 = search_cheats("git log")
    assert fuzzy_count2 > 0, "模糊搜索'git log'应有结果"

    # 6. 模糊搜索（测试近似匹配）
    fuzzy_matches3, fuzzy_count3 = search_cheats("gti")  # 拼写错误
    assert fuzzy_count3 > 0, "模糊搜索'gti'（拼写错误）应有结果"

    # 7. 随机（测试 seed 可复现性）
    rand_item1 = get_random_cheat("docker", seed=42)
    rand_item2 = get_random_cheat("docker", seed=42)
    assert rand_item1 is not None, "docker 随机应返回一条"
    assert rand_item1 in CHEATS["docker"], "随机结果应来自 docker 领域"
    assert rand_item1 == rand_item2, "相同 seed 应产生相同随机结果"

    # 8. 导出
    tmp_export = os.path.join(tempfile.gettempdir(), f"cheats_test_{os.getpid()}.md")
    try:
        export_markdown(tmp_export)
        with open(tmp_export, "r", encoding="utf-8") as f:
            content = f.read()
        assert "命令行速查手册" in content, "导出文件应包含标题"
        assert "git" in content and "docker" in content and "linux" in content, "导出文件应包含所有领域"
        assert "python" in content and "javascript" in content and "kubernetes" in content, "导出文件应包含新增领域"
        assert "导出时间" in content, "导出文件应包含时间戳"
    finally:
        if os.path.exists(tmp_export):
            os.unlink(tmp_export)

    # 9. 表格格式
    table = format_table(git_items[:2])
    assert "| 序号 | 命令 | 描述 | 场景 |" in table, "表格应包含表头"
    assert "git log" in table, "表格应包含命令内容"

    # 10. 命令安全性验证
    assert validate_shell_command("du -sh * | sort -rh | head -10"), "管道命令应通过验证"
    assert not validate_shell_command("rm -rf /; sudo reboot"), "危险命令应被拒绝"
    assert not validate_shell_command("echo test && rm -rf /"), "危险命令应被拒绝"

    #
