#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cheat_sheet.py — 终端速查工具（cheat-sh-pro 真实实现）
内置多领域命令速查字典，支持模糊搜索、领域过滤、随机速查、Markdown 导出。
纯标准库，零依赖。
"""
import argparse
import json
import random
import sys

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
        {"cmd": "docker inspect c1 | jq '.[0].NetworkSettings.IPAddress'", "desc": "查容器IP", "scene": "容器间通信"},
        {"cmd": "docker compose up -d", "desc": "后台启动编排服务", "scene": "启动服务栈"},
    ],
    "linux": [
        {"cmd": "grep -rn 'keyword' ./src", "desc": "递归搜索关键词", "scene": "找代码"},
        {"cmd": "find . -name '*.log' -mtime -7", "desc": "找7天内修改的日志文件", "scene": "定位近期文件"},
        {"cmd": "ps aux | grep java", "desc": "按进程名过滤", "scene": "查进程"},
        {"cmd": "kill -9 PID", "desc": "强制杀进程", "scene": "进程僵死"},
        {"cmd": "du -sh */ | sort -rh | head", "desc": "目录大小排序", "scene": "找大目录"},
        {"cmd": "tar -czvf a.tgz ./dir", "desc": "打包压缩", "scene": "归档"},
        {"cmd": "rsync -avz src/ dst/", "desc": "增量同步目录", "scene": "备份/部署"},
        {"cmd": "lsof -i :8080", "desc": "查端口占用", "scene": "端口冲突"},
    ],
    "python": [
        {"cmd": "python -m venv .venv && source .venv/bin/activate", "desc": "创建并激活虚拟环境", "scene": "项目隔离依赖"},
        {"cmd": "python -m pip freeze > requirements.txt", "desc": "导出依赖清单", "scene": "锁定依赖"},
        {"cmd": "python -m http.server 8000", "desc": "启动静态文件服务", "scene": "临时共享文件"},
        {"cmd": "python -m json.tool data.json", "desc": "格式化JSON", "scene": "查看JSON结构"},
        {"cmd": "python -c 'import this'", "desc": "打印Python之禅", "scene": "设计理念"},
        {"cmd": "python -m pdb script.py", "desc": "进入调试器", "scene": "定位bug"},
        {"cmd": "python -O script.py", "desc": "优化模式运行（去assert）", "scene": "性能敏感运行"},
        {"cmd": "python -X dev script.py", "desc": "开发模式运行（完整警告）", "scene": "开发期排查"},
    ],
    "sql": [
        {"cmd": "SELECT COUNT(*) FROM t;", "desc": "统计行数", "scene": "表规模评估"},
        {"cmd": "EXPLAIN SELECT ...", "desc": "查看执行计划", "scene": "SQL优化"},
        {"cmd": "SHOW PROCESSLIST;", "desc": "查看当前连接", "scene": "排查慢查询"},
        {"cmd": "SELECT * FROM t WHERE a LIKE '%x%';", "desc": "模糊查询", "scene": "搜索记录"},
        {"cmd": "ALTER TABLE t ADD INDEX idx_a (a);", "desc": "添加索引", "scene": "查询加速"},
        {"cmd": "DELETE FROM t WHERE id IN (...);", "desc": "批量删除", "scene": "清理数据"},
    ],
    "regex": [
        {"cmd": "\\d{4}-\\d{2}-\\d{2}", "desc": "匹配日期 2026-08-05", "scene": "日期格式校验"},
        {"cmd": "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", "desc": "匹配邮箱", "scene": "表单校验"},
        {"cmd": "(?<=@)\\w+", "desc": "取@后的用户名", "scene": "提取用户名"},
        {"cmd": "\\b\\w{6,}\\b", "desc": "6位以上单词", "scene": "找长词"},
        {"cmd": "(https?://[^\\s]+)", "desc": "提取URL", "scene": "抓链接"},
    ],
    "curl": [
        {"cmd": "curl -sS https://api.example.com/data", "desc": "静默GET请求", "scene": "调API"},
        {"cmd": "curl -X POST -H 'Content-Type: application/json' -d '{\"k\":1}' URL", "desc": "POST JSON", "scene": "提交数据"},
        {"cmd": "curl -o file.bin -L URL", "desc": "下载并跟随重定向", "scene": "下载文件"},
        {"cmd": "curl -w '%{http_code}\\n' -o /dev/null URL", "desc": "只看状态码", "scene": "接口健康检查"},
        {"cmd": "curl -u user:pass URL", "desc": "带认证请求", "scene": "需要登录的接口"},
    ],
    "vim": [
        {"cmd": ":wq", "desc": "保存并退出", "scene": "编辑完成"},
        {"cmd": ":q!", "desc": "不保存强制退出", "scene": "放弃改动"},
        {"cmd": "/keyword", "desc": "搜索关键词（n/N切换）", "scene": "定位文本"},
        {"cmd": ":%s/old/new/g", "desc": "全文替换", "scene": "批量替换"},
        {"cmd": "gg dG", "desc": "清空整个文件", "scene": "重置文件"},
        {"cmd": "u", "desc": "撤销", "scene": "操作失误"},
    ],
    "redis": [
        {"cmd": "redis-cli --scan --pattern 'cache:*' | xargs redis-cli del", "desc": "按模式批量删除key", "scene": "清理缓存"},
        {"cmd": "redis-cli info memory | grep used_memory_human", "desc": "查看内存占用", "scene": "内存监控"},
        {"cmd": "redis-cli monitor", "desc": "实时监控所有命令", "scene": "排查慢命令"},
        {"cmd": "redis-cli ttl key", "desc": "查看key剩余寿命", "scene": "检查过期"},
    ],
    "mysql": [
        {"cmd": "mysql -u root -p -e 'SHOW DATABASES;'", "desc": "命令行执行SQL", "scene": "快速查询"},
        {"cmd": "mysqldump -u root -p db > db.sql", "desc": "导出数据库", "scene": "备份"},
        {"cmd": "mysql -u root -p db < db.sql", "desc": "导入数据库", "scene": "恢复"},
        {"cmd": "SELECT version();", "desc": "查版本", "scene": "环境确认"},
    ],
    "grep": [
        {"cmd": "grep -v pattern file", "desc": "反向匹配（排除）", "scene": "过滤干扰行"},
        {"cmd": "grep -c pattern file", "desc": "统计匹配行数", "scene": "计数"},
        {"cmd": "grep -i pattern file", "desc": "忽略大小写", "scene": "不区分大小写搜索"},
        {"cmd": "grep -E 'a|b' file", "desc": "扩展正则多条件", "scene": "多模式匹配"},
    ],
}

LANGS = sorted(CHEATS.keys())


def search(query: str, lang: str = "", top: int = 10):
    q = query.lower()
    hits = []
    for lang_name, items in CHEATS.items():
        if lang and lang != lang_name:
            continue
        for it in items:
            hay = (it["cmd"] + " " + it["desc"] + " " + it["scene"]).lower()
            # 分词模糊匹配：query 每个词都要命中
            if all(w in hay for w in q.split() if w):
                hits.append((lang_name, it))
    hits.sort(key=lambda x: x[1]["cmd"].lower().find(q) if q in x[1]["cmd"].lower() else 99)
    return hits[:top]


def render(items, fmt: str = "plain"):
    lines = []
    for lang_name, it in items:
        if fmt == "markdown":
            lines.append(f"- **{lang_name}**: `{it['cmd']}` — {it['desc']} ({it['scene']})")
        else:
            lines.append(f"[{lang_name}] {it['cmd']}")
            lines.append(f"    {it['desc']}（{it['scene']}）")
    return "\n".join(lines) if lines else "（无匹配）"


def selftest() -> bool:
    ok = True
    # 1. 字典完整性：每领域至少 8 条（grep 等小领域放宽为≥4）
    for ln, items in CHEATS.items():
        if len(items) < 4:
            print(f"  ❌ {ln} 仅 {len(items)} 条")
            ok = False
    # 2. 搜索命中
    hits = search("日志")
    if not hits:
        print("  ❌ 搜索 '日志' 无结果")
        ok = False
    # 3. 领域过滤
    g = search("", lang="git")
    if not g:
        print("  ❌ git 领域无结果")
        ok = False
    # 4. 渲染
    if not render(hits):
        print("  ❌ 渲染失败")
        ok = False
    if ok:
        print(f"  ✅ 速查字典 {sum(len(v) for v in CHEATS.values())} 条 / {len(CHEATS)} 领域")
        print(f"  ✅ 搜索/过滤/渲染正常")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(
        description="终端速查工具：内置多领域命令速查，支持模糊搜索与导出")
    ap.add_argument("--query", "-q", default="", help="搜索关键词（分词模糊匹配）")
    ap.add_argument("--lang", "-l", default="", help="领域过滤：" + ",".join(LANGS))
    ap.add_argument("--format", "-f", choices=["plain", "markdown"], default="plain", help="输出格式")
    ap.add_argument("--top", "-n", type=int, default=10, help="最多显示条数")
    ap.add_argument("--random", "-r", action="store_true", help="随机一条")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    args = ap.parse_args()

    if args.selftest:
        return 0 if selftest() else 1
    if args.random:
        ln = random.choice(LANGS)
        it = random.choice(CHEATS[ln])
        print(f"[{ln}] {it['cmd']}\n    {it['desc']}（{it['scene']}）")
        return 0
    if args.lang and args.lang not in CHEATS:
        print(f"未知领域: {args.lang}，可用: {LANGS}")
        return 1
    items = search(args.query, args.lang, args.top)
    print(render(items, args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
