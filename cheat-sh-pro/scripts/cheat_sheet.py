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
import sys
import tempfile
from datetime import datetime, timezone
dry_run = False  # v3.274 模块级 dry-run 标志

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


def search_cheats(keyword, domain=None):
    """按关键词模糊搜索命令，返回 (匹配列表, 匹配数量)
    使用 difflib.SequenceMatcher 计算相似度，结合子串匹配和正则表达式
    """
    if domain:
        items = get_domain_cheats(domain)
        if items is None:
            return None, 0
    else:
        items = get_all_cheats()

    keyword_lower = keyword.lower()
    # 构建正则模式（转义特殊字符）
    try:
        pattern = re.compile(re.escape(keyword_lower))
    except re.error:
        pattern = None

    scored_matches = []
    for item in items:
        # 收集所有可搜索字段
        searchable_text = f"{item['cmd']} {item['desc']} {item['scene']}".lower()
        
        # 1. 精确子串匹配（最高优先级）
        if keyword_lower in searchable_text:
            score = 1.0
        else:
            # 2. 正则匹配
            regex_score = 0.0
            if pattern and pattern.search(searchable_text):
                regex_score = 0.8
            
            # 3. difflib 模糊匹配（对每个字段计算相似度）
            diff_scores = []
            for field in [item["cmd"], item["desc"], item["scene"]]:
                field_lower = field.lower()
                # 使用 SequenceMatcher 计算相似度
                similarity = difflib.SequenceMatcher(None, keyword_lower, field_lower).ratio()
                diff_scores.append(similarity)
            
            # 取最高相似度
            max_diff_score = max(diff_scores) if diff_scores else 0.0
            
            # 综合评分：正则匹配优先于纯模糊匹配
            score = max(regex_score, max_diff_score * 0.6)
        
        # 只保留相似度超过阈值的匹配
        if score > 0.3:
            scored_matches.append((score, item))
    
    # 按相似度降序排序
    scored_matches.sort(key=lambda x: x[0], reverse=True)
    matches = [item for _, item in scored_matches]
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

    # 6. 随机（测试 seed 可复现性）
    rand_item1 = get_random_cheat("docker", seed=42)
    rand_item2 = get_random_cheat("docker", seed=42)
    assert rand_item1 is not None, "docker 随机应返回一条"
    assert rand_item1 in CHEATS["docker"], "随机结果应来自 docker 领域"
    assert rand_item1 == rand_item2, "相同 seed 应产生相同随机结果"

    # 7. 导出
    tmp_export = os.path.join(tempfile.gettempdir(), f"cheats_test_{os.getpid()}.md")
    try:
        export_markdown(tmp_export)
        with open(tmp_export, "r", encoding="utf-8") as f:
            content = f.read()
        assert "命令行速查手册" in content, "导出文件应包含标题"
        assert "git" in content and "docker" in content and "linux" in content, "导出文件应包含所有领域"
        assert "导出时间" in content, "导出文件应包含时间戳"
    finally:
        if os.path.exists(tmp_export):
            os.unlink(tmp_export)

    # 8. 表格格式
    table = format_table(git_items[:2])
    assert "| 序号 | 命令 | 描述 | 场景 |" in table, "表格应包含表头"
    assert "git log" in table, "表格应包含命令内容"

    # 9. 主流程集成测试（通过 subprocess 调用 main）
    import subprocess
    test_cases = [
        (["--domain", "git"], 0),
        (["--search", "提交"], 0),
        (["--search", "log"], 0),  # 模糊搜索
        (["--random", "--domain", "linux"], 0),
        (["--random", "--domain", "linux", "--seed", "42"], 0),  # 带 seed 的随机
        (["--list-domains"], 0),
        (["--export", os.path.join(tempfile.gettempdir(), f"cheats_export_{os.getpid()}.md")], 0),
        (["--domain", "nonexist"], 3),
    ]
    for args, expected_code in test_cases:
        result = subprocess.run(
            [sys.executable, __file__] + args,
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == expected_code, f"参数 {args} 应退出码 {expected_code}，实际 {result.returncode}"
        # 验证输出内容
        if expected_code == 0:
            assert len(result.stdout.strip()) > 0, f"参数 {args} 应有输出内容"

    # 10. 验证导出文件内容
    export_path = os.path.join(tempfile.gettempdir(), f"cheats_export_{os.getpid()}.md")
    if os.path.exists(export_path):
        with open(export_path, "r", encoding="utf-8") as f:
            export_content = f.read()
        assert "命令行速查手册" in export_content, "导出文件应包含标题"
        os.unlink(export_path)

    # 11. 验证 seed 可复现性（通过 subprocess）
    result1 = subprocess.run(
        [sys.executable, __file__, "--random", "--domain", "docker", "--seed", "123"],
        capture_output=True,
        text=True,
        timeout=10
    )
    result2 = subprocess.run(
        [sys.executable, __file__, "--random", "--domain", "docker", "--seed", "123"],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert result1.stdout == result2.stdout, "相同 seed 的随机输出应一致"

    print("自检通过：所有核心功能验证成功")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="命令行速查手册（cheat-sh-pro）— 本地多领域命令速查工具",
        epilog="示例：python cheat_sheet.py --domain git | --search 提交 | --random | --export cheats.md | --list-domains | --selftest"
    )
    parser.add_argument("--domain", type=str, help="领域名称（git/docker/linux）")
    parser.add_argument("--search", type=str, help="搜索关键词（支持模糊匹配）")
    parser.add_argument("--random", action="store_true", help="随机返回一条命令")
    parser.add_argument("--seed", type=int, help="随机种子（用于可复现性）")
    parser.add_argument("--export", type=str, metavar="FILE", help="导出全部速查到 Markdown 文件")
    parser.add_argument("--list-domains", action="store_true", help="列出所有可用领域")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    args = parser.parse_args()
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检
    if args.selftest:
        return run_selftest()

    # 列出领域
    if args.list_domains:
        print("可用领域：")
        for domain in CHEATS:
            print(f"  - {domain}")
        return 0

    # 导出
    if args.export:
        try:
            filepath = export_markdown(args.export)
            print(f"已导出到：{filepath}")
            return 0
        except Exception as e:
            print(f"导出失败：{e}", file=sys.stderr)
            return 4

    # 随机
    if args.random:
        item = get_random_cheat(args.domain, seed=args.seed)
        if item is None:
            print(f"领域不存在：{args.domain}", file=sys.stderr)
            return 3
        print(format_table([item]))
        return 0

    # 搜索
    if args.search:
        matches, count = search_cheats(args.search, args.domain)
        if matches is None:
            print(f"领域不存在：{args.domain}", file=sys.stderr)
            return 3
        print(f"找到 {count} 条匹配结果：")
        print()
        print(format_table(matches))
        return 0

    # 领域查询
    if args.domain:
        items = get_domain_cheats(args.domain)
        if items is None:
            print(f"领域不存在：{args.domain}", file=sys.stderr)
            return 3
        print(f"领域 [{args.domain}] 的命令速查：")
        print()
        print(format_table(items))
        return 0

    # 默认：全部领域
    all_items = get_all_cheats()
    print(f"全部领域命令速查（共 {len(all_items)} 条）：")
    print()
    print(format_table(all_items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
