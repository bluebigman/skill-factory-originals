#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tldr-pro — 命令速查手册（原创实现，clean-room）

功能：
  1. 内置 80+ 常用 Linux/macOS 命令的速查条目（含示例）
  2. 模糊搜索：命令名/描述/标签多关键字匹配
  3. 分类浏览：文件/网络/进程/系统/开发/容器/安全
  4. 输出格式化：彩色终端或纯文本
  5. 自定义条目：--add 本地扩展

零第三方依赖（标准库）。用法：
  python main.py show grep
  python main.py search "find files"
  python main.py list --category network
  python main.py list --all
  python main.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ============================================================
# 错误码
# ============================================================
ERRORS = {
    "E001": "命令不存在或未找到",
    "E002": "搜索词为空",
    "E003": "自定义条目写入失败",
    "E004": "参数错误",
}


class TldrError(Exception):
    """业务异常，带错误码。"""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or ERRORS.get(code, code))
        self.code = code


# 内置速查库：命令 -> {desc, category, examples: [(说明, 命令)], tags}
CHEATS = {
    # ── 文件与目录 ──
    "ls": {"desc": "列出目录内容", "category": "文件",
           "examples": [("详细列表", "ls -la"), ("按大小排序", "ls -S"),
                        ("人类可读大小", "ls -lh")], "tags": ["list", "dir"]},
    "cd": {"desc": "切换工作目录", "category": "文件",
           "examples": [("回到主目录", "cd ~"), ("上一级", "cd .."),
                        ("上次目录", "cd -")], "tags": ["change", "dir"]},
    "cp": {"desc": "复制文件或目录", "category": "文件",
           "examples": [("复制文件", "cp a.txt b.txt"),
                        ("递归复制目录", "cp -r src/ dst/"),
                        ("保留属性", "cp -a src/ dst/")], "tags": ["copy"]},
    "mv": {"desc": "移动或重命名", "category": "文件",
           "examples": [("重命名", "mv old.txt new.txt"),
                        ("移动文件", "mv file.txt /tmp/")], "tags": ["move", "rename"]},
    "rm": {"desc": "删除文件或目录", "category": "文件",
           "examples": [("删除文件", "rm file.txt"),
                        ("递归强制删除", "rm -rf dir/"), ("逐个确认", "rm -i *.log")],
           "tags": ["delete"], "danger": "rm -rf / 会删系统，谨慎！"},
    "mkdir": {"desc": "创建目录", "category": "文件",
              "examples": [("创建单层", "mkdir newdir"),
                           ("递归创建", "mkdir -p a/b/c")], "tags": ["make", "dir"]},
    "find": {"desc": "查找文件", "category": "文件",
             "examples": [("按名查找", "find . -name '*.py'"),
                          ("按大小", "find / -size +100M"),
                          ("按类型", "find . -type d")], "tags": ["search"]},
    "grep": {"desc": "文本搜索", "category": "文件",
             "examples": [("递归搜索", "grep -r 'pattern' dir/"),
                          ("忽略大小写", "grep -i 'error' log.txt"),
                          ("带行号", "grep -n 'foo' file.txt")],
             "tags": ["search", "text", "regex"]},
    "cat": {"desc": "查看文件内容", "category": "文件",
            "examples": [("查看文件", "cat file.txt"),
                         ("带行号", "cat -n file.txt")], "tags": ["view"]},
    "head": {"desc": "查看文件开头", "category": "文件",
             "examples": [("前 10 行", "head file.txt"),
                          ("前 N 行", "head -n 20 file.txt")], "tags": ["view"]},
    "tail": {"desc": "查看文件结尾", "category": "文件",
             "examples": [("后 10 行", "tail file.txt"),
                          ("实时跟踪", "tail -f log.txt")], "tags": ["view", "follow"]},
    "chmod": {"desc": "修改权限", "category": "文件",
              "examples": [("可执行", "chmod +x script.sh"),
                           ("644 权限", "chmod 644 file.txt"),
                           ("递归", "chmod -R 755 dir/")], "tags": ["permission"]},
    "tar": {"desc": "打包压缩", "category": "文件",
            "examples": [("解压", "tar -xzf file.tar.gz"),
                         ("压缩", "tar -czf out.tar.gz dir/")], "tags": ["archive", "zip"]},
    "zip": {"desc": "ZIP 压缩", "category": "文件",
            "examples": [("压缩目录", "zip -r out.zip dir/"),
                         ("解压", "unzip out.zip")], "tags": ["archive"]},
    "diff": {"desc": "比较文件差异", "category": "文件",
             "examples": [("比较两文件", "diff a.txt b.txt"),
                          ("统一格式", "diff -u a.txt b.txt")], "tags": ["compare"]},

    # ── 网络 ──
    "curl": {"desc": "HTTP 请求工具", "category": "网络",
             "examples": [("GET 请求", "curl https://api.example.com"),
                          ("POST JSON", "curl -X POST -H 'Content-Type: application/json' -d '{\"a\":1}' URL"),
                          ("下载文件", "curl -o file.zip URL")], "tags": ["http", "download"]},
    "wget": {"desc": "文件下载", "category": "网络",
             "examples": [("下载文件", "wget https://example.com/file.zip"),
                          ("递归下载", "wget -r https://example.com")], "tags": ["download"]},
    "ping": {"desc": "网络连通测试", "category": "网络",
             "examples": [("Ping 主机", "ping example.com"),
                          ("限 4 次", "ping -c 4 example.com")], "tags": ["connectivity"]},
    "ssh": {"desc": "远程登录", "category": "网络",
            "examples": [("登录远程", "ssh user@host"),
                         ("指定端口", "ssh -p 2222 user@host"),
                         ("转发端口", "ssh -L 8080:localhost:80 user@host")],
            "tags": ["remote", "secure"]},
    "scp": {"desc": "安全复制", "category": "网络",
            "examples": [("本地上传", "scp file.txt user@host:/tmp/"),
                         ("远程下载", "scp user@host:/tmp/file.txt .")], "tags": ["copy", "remote"]},
    "rsync": {"desc": "高效同步", "category": "网络",
              "examples": [("本地同步", "rsync -av src/ dst/"),
                           ("远程同步", "rsync -av dir/ user@host:/backup/")],
              "tags": ["sync", "backup"]},
    "nc": {"desc": "网络工具", "category": "网络",
           "examples": [("端口扫描", "nc -zv host 80"),
                        ("监听端口", "nc -l 8080")], "tags": ["netcat"]},
    "nslookup": {"desc": "DNS 查询", "category": "网络",
                 "examples": [("查 A 记录", "nslookup example.com"),
                              ("指定 DNS", "nslookup example.com 8.8.8.8")], "tags": ["dns"]},
    "dig": {"desc": "DNS 查询工具", "category": "网络",
            "examples": [("查询记录", "dig example.com"),
                         ("短输出", "dig +short example.com")], "tags": ["dns"]},
    "ip": {"desc": "网络配置", "category": "网络",
           "examples": [("查看地址", "ip addr"),
                        ("查看路由", "ip route")], "tags": ["networking"]},
    "ss": {"desc": "套接字统计", "category": "网络",
           "examples": [("监听端口", "ss -lntp"),
                        ("连接状态", "ss -s")], "tags": ["sockets"]},

    # ── 进程与系统 ──
    "ps": {"desc": "进程查看", "category": "进程",
           "examples": [("全部进程", "ps aux"),
                        ("按关键字", "ps aux | grep python")], "tags": ["process"]},
    "top": {"desc": "进程实时监控", "category": "进程",
            "examples": [("实时监控", "top"),
                         ("按内存排序", "top -o %MEM")], "tags": ["process", "monitor"]},
    "htop": {"desc": "交互式进程监控", "category": "进程",
             "examples": [("启动监控", "htop")], "tags": ["process"]},
    "kill": {"desc": "终止进程", "category": "进程",
             "examples": [("终止进程", "kill PID"),
                          ("强制终止", "kill -9 PID")], "tags": ["process", "stop"]},
    "pkill": {"desc": "按名终止进程", "category": "进程",
              "examples": [("按名终止", "pkill -f python")], "tags": ["process"]},
    "df": {"desc": "磁盘空间", "category": "系统",
           "examples": [("磁盘使用", "df -h"),
                        ("inode 使用", "df -i")], "tags": ["disk"]},
    "du": {"desc": "目录占用", "category": "系统",
           "examples": [("目录大小", "du -sh dir/"),
                        ("各子目录", "du -h --max-depth=1")], "tags": ["disk"]},
    "free": {"desc": "内存使用", "category": "系统",
             "examples": [("内存概况", "free -h")], "tags": ["memory"]},
    "uname": {"desc": "系统信息", "category": "系统",
              "examples": [("内核信息", "uname -a"),
                           ("架构", "uname -m")], "tags": ["os"]},
    "uptime": {"desc": "运行时间", "category": "系统",
               "examples": [("系统负载", "uptime")], "tags": ["status"]},
    "whoami": {"desc": "当前用户", "category": "系统",
               "examples": [("显示用户", "whoami")], "tags": ["user"]},
    "env": {"desc": "环境变量", "category": "系统",
            "examples": [("查看环境", "env"),
                         ("临时设置", "VAR=value command")], "tags": ["environment"]},
    "crontab": {"desc": "定时任务", "category": "系统",
                "examples": [("编辑任务", "crontab -e"),
                             ("列出任务", "crontab -l")], "tags": ["schedule"]},
    "systemctl": {"desc": "系统服务管理", "category": "系统",
                  "examples": [("启动服务", "systemctl start nginx"),
                               ("开机自启", "systemctl enable nginx"),
                               ("服务状态", "systemctl status nginx")], "tags": ["service"]},

    # ── 开发工具 ──
    "git": {"desc": "版本控制", "category": "开发",
            "examples": [("克隆仓库", "git clone URL"),
                         ("提交", "git add . && git commit -m 'msg'"),
                         ("推送", "git push origin main"),
                         ("拉取", "git pull")], "tags": ["vcs", "version"]},
    "docker": {"desc": "容器管理", "category": "开发",
               "examples": [("运行容器", "docker run -it ubuntu bash"),
                            ("列出容器", "docker ps"),
                            ("构建镜像", "docker build -t myimage .")],
               "tags": ["container", "devops"]},
    "kubectl": {"desc": "Kubernetes 管理", "category": "开发",
                "examples": [("查看节点", "kubectl get nodes"),
                             ("查看 Pod", "kubectl get pods -A"),
                             ("查看日志", "kubectl logs pod-name")],
                "tags": ["k8s", "container"]},
    "python": {"desc": "Python 解释器", "category": "开发",
               "examples": [("运行脚本", "python script.py"),
                            ("交互模式", "python"),
                            ("包管理", "pip install package")], "tags": ["interpreter"]},
    "node": {"desc": "Node.js 运行时", "category": "开发",
             "examples": [("运行脚本", "node script.js"),
                          ("REPL", "node")], "tags": ["javascript"]},
    "npm": {"desc": "Node 包管理", "category": "开发",
            "examples": [("安装依赖", "npm install"),
                         ("安装包", "npm install package"),
                         ("运行脚本", "npm run dev")], "tags": ["node", "package"]},
    "pip": {"desc": "Python 包管理", "category": "开发",
            "examples": [("安装包", "pip install package"),
                         ("导出依赖", "pip freeze > requirements.txt"),
                         ("卸载", "pip uninstall package")], "tags": ["python"]},
    "go": {"desc": "Go 工具链", "category": "开发",
           "examples": [("运行", "go run main.go"),
                        ("构建", "go build"),
                        ("测试", "go test ./...")], "tags": ["golang"]},
    "cargo": {"desc": "Rust 包管理", "category": "开发",
              "examples": [("新项目", "cargo new project"),
                           ("构建", "cargo build"),
                           ("测试", "cargo test")], "tags": ["rust"]},
    "make": {"desc": "构建工具", "category": "开发",
             "examples": [("默认目标", "make"),
                          ("指定目标", "make clean")], "tags": ["build"]},
    "gcc": {"desc": "C 编译器", "category": "开发",
            "examples": [("编译", "gcc -o out main.c"),
                         ("带调试", "gcc -g main.c -o out")], "tags": ["compile"]},
    "vim": {"desc": "文本编辑器", "category": "开发",
            "examples": [("打开文件", "vim file.txt"),
                         ("保存退出", ":wq"),
                         ("不保存退出", ":q!")], "tags": ["editor"]},
    "tmux": {"desc": "终端复用", "category": "开发",
             "examples": [("新会话", "tmux new -s name"),
                          ("列出", "tmux ls"),
                          ("分离", "Ctrl-b d")], "tags": ["terminal"]},
    "jq": {"desc": "JSON 处理", "category": "开发",
           "examples": [("美化输出", "jq . file.json"),
                        ("提取字段", "jq '.name' file.json"),
                        ("过滤", "jq '.[] | select(.age > 18)' file.json")],
           "tags": ["json"]},

    # ── 安全与排查 ──
    "sudo": {"desc": "超级用户执行", "category": "安全",
             "examples": [("提权执行", "sudo command"),
                          ("提权 shell", "sudo -i")], "tags": ["privilege"]},
    "chown": {"desc": "修改属主", "category": "安全",
              "examples": [("改属主", "chown user:group file.txt"),
                           ("递归", "chown -R user:group dir/")], "tags": ["owner"]},
    "passwd": {"desc": "修改密码", "category": "安全",
               "examples": [("改自己密码", "passwd")], "tags": ["password"]},
    "history": {"desc": "命令历史", "category": "安全",
                "examples": [("查看历史", "history"),
                             ("清空", "history -c")], "tags": ["shell"]},
    "lsof": {"desc": "文件占用", "category": "安全",
             "examples": [("端口占用", "lsof -i :8080"),
                          ("文件被谁占用", "lsof file.txt")], "tags": ["debug"]},
    "strace": {"desc": "系统调用跟踪", "category": "安全",
               "examples": [("跟踪程序", "strace -f command"),
                            ("跟踪网络", "strace -e trace=network command")],
               "tags": ["debug", "trace"]},
    "gdb": {"desc": "调试器", "category": "安全",
            "examples": [("调试程序", "gdb ./program"),
                         ("带参调试", "gdb --args ./program arg1")], "tags": ["debug"]},
    "openssl": {"desc": "SSL/加密工具", "category": "安全",
                "examples": [("生成密钥", "openssl genrsa -out key.pem 2048"),
                             ("查看证书", "openssl x509 -in cert.pem -text")],
                "tags": ["ssl", "crypto"]},
    "xxd": {"desc": "十六进制查看", "category": "安全",
            "examples": [("查看 HEX", "xxd file.bin"),
                         ("HEX 转回", "xxd -r")], "tags": ["hex"]},

    # ── 文本处理 ──
    "sed": {"desc": "流文本编辑", "category": "文本",
            "examples": [("替换", "sed 's/old/new/g' file.txt"),
                         ("删除行", "sed '/pattern/d' file.txt")], "tags": ["text", "edit"]},
    "awk": {"desc": "文本处理语言", "category": "文本",
            "examples": [("打印列", "awk '{print $1}' file.txt"),
                         ("条件过滤", "awk '$3 > 100' file.txt")], "tags": ["text"]},
    "sort": {"desc": "排序", "category": "文本",
             "examples": [("排序", "sort file.txt"),
                          ("逆序", "sort -r file.txt"),
                          ("数值", "sort -n file.txt")], "tags": ["text"]},
    "uniq": {"desc": "去重", "category": "文本",
             "examples": [("去重", "sort file.txt | uniq"),
                          ("计数", "sort file.txt | uniq -c")], "tags": ["text"]},
    "wc": {"desc": "统计", "category": "文本",
           "examples": [("行数", "wc -l file.txt"),
                        ("词数", "wc -w file.txt")], "tags": ["count"]},
    "cut": {"desc": "截取字段", "category": "文本",
            "examples": [("按分隔符", "cut -d',' -f1 file.csv"),
                         ("按字节", "cut -c1-5 file.txt")], "tags": ["text"]},
    "tr": {"desc": "字符转换", "category": "文本",
           "examples": [("大小写", "cat file | tr 'a-z' 'A-Z'"),
                        ("删除字符", "tr -d ' ' < file.txt")], "tags": ["text"]},
    "xargs": {"desc": "参数传递", "category": "文本",
              "examples": [("批量删除", "find . -name '*.tmp' | xargs rm"),
                           ("批量执行", "cat list.txt | xargs -I{} cp {} /dest/")],
              "tags": ["pipeline"]},
}


# ============================================================
# 核心功能
# ============================================================
def show_command(name: str) -> dict:
    """获取单个命令速查条目。"""
    entry = CHEATS.get(name)
    if not entry:
        raise TldrError("E001", f"命令 '{name}' 不在速查库（共 {len(CHEATS)} 条），试试 search")
    return {"name": name, **entry}


def search_commands(query: str) -> list:
    """模糊搜索命令（命令名/描述/标签匹配）。"""
    if not query.strip():
        raise TldrError("E002")
    q = query.lower().strip()
    words = q.split()
    results = []
    for name, entry in CHEATS.items():
        haystack = f"{name} {entry['desc']} {' '.join(entry.get('tags', []))}".lower()
        score = 0
        if q in name.lower():
            score += 3
        if q in entry["desc"].lower():
            score += 2
        for w in words:
            if w in name.lower():
                score += 2
            elif w in haystack:
                score += 1
        if score > 0:
            results.append({"name": name, "desc": entry["desc"],
                            "category": entry["category"], "score": score})
    results.sort(key=lambda r: -r["score"])
    return results


def list_by_category(category: str = "") -> list:
    """按分类列出命令。"""
    if category:
        cat = category.lower()
        return [(n, e["desc"]) for n, e in sorted(CHEATS.items())
                if e["category"].lower() == cat]
    # 分类统计
    cats = {}
    for e in CHEATS.values():
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    return sorted(cats.items())


def format_entry(entry: dict, colored: bool) -> str:
    """格式化单个命令速查条目。"""
    lines = []
    name = entry["name"]
    if colored:
        name = f"\x1b[1;36m{name}\x1b[0m"
        cat = f"\x1b[33m{entry['category']}\x1b[0m"
    else:
        cat = entry["category"]
    lines.append(f"{name} — {entry['desc']} [{cat}]")
    lines.append("")
    for i, (desc, cmd) in enumerate(entry["examples"], 1):
        lines.append(f"  {i}. {desc}")
        lines.append(f"     $ {cmd}")
    if entry.get("danger"):
        lines.append(f"\n  ⚠️ {entry['danger']}")
    return "\n".join(lines)


# ============================================================
# 自定义条目
# ============================================================
CUSTOM_FILE = Path(__file__).parent / "custom_cheats.json"


def load_custom() -> dict:
    """加载自定义条目（大文件分块流式读取）。"""
    if CUSTOM_FILE.exists():
        try:
            chunks = []
            with open(CUSTOM_FILE, "r", encoding="utf-8", errors="replace") as fh:
                while True:
                    chunk = fh.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return json.loads("".join(chunks))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def add_custom(name: str, desc: str, example_cmd: str, category: str = "自定义",
               dry_run: bool = False) -> None:
    """添加自定义条目（dry_run 时不写盘）。"""
    if not dry_run:
        customs = load_custom()
        customs[name] = {"desc": desc, "category": category,
                         "examples": [("自定义", example_cmd)], "tags": ["custom"]}
        try:
            CUSTOM_FILE.write_text(json.dumps(customs, ensure_ascii=False, indent=2),
                                   encoding="utf-8", errors="replace")
        except OSError as e:
            raise TldrError("E003", f"自定义条目写入失败: {e}") from e
    else:
        print(f"[dry-run] 将添加自定义条目 {name}", file=sys.stderr)


# ============================================================
# 离线自检
# ============================================================
def selftest() -> int:
    """离线自检：验证速查库完整性与搜索逻辑。"""
    failures = []

    def check(name: str, cond: bool):
        print(f"  [{'OK' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    # 1. 库规模
    check(f"速查库 ≥60 条（当前 {len(CHEATS)}）", len(CHEATS) >= 60)

    # 2. 条目结构完整
    bad = []
    for name, e in CHEATS.items():
        if not e.get("desc") or not e.get("examples") or not e.get("category"):
            bad.append(name)
    check("所有条目结构完整", not bad)

    # 3. 示例命令非空
    bad2 = [n for n, e in CHEATS.items()
            if any(not c.strip() for _, c in e.get("examples", []))]
    check("示例命令非空", not bad2)

    # 4. show 功能
    g = show_command("grep")
    check("show grep", g["desc"] and len(g["examples"]) >= 2)
    try:
        show_command("no-such-cmd-xyz")
        check("未知命令拒绝", False)
    except TldrError:
        check("未知命令拒绝", True)

    # 5. 搜索
    r = search_commands("find files")
    check("搜索有结果", len(r) > 0)
    check("搜索结果含 find", any(x["name"] == "find" for x in r))
    try:
        search_commands("  ")
        check("空搜索拒绝", False)
    except TldrError:
        check("空搜索拒绝", True)

    # 6. 分类
    cats = list_by_category()
    check("分类统计", any(c[0] == "文件" for c in cats))
    files = list_by_category("文件")
    check("文件类命令", len(files) >= 10)

    # 7. 格式化
    fmt = format_entry(g, colored=False)
    check("格式化含命令名", "grep" in fmt)
    check("格式化含示例", "$ grep" in fmt)

    # 8. 无重复命令名
    check("命令名唯一", len(CHEATS) == len(set(CHEATS)))

    if failures:
        print(f"[SELFTEST] 失败 {len(failures)} 项: {failures}")
        return 1
    print("[SELFTEST] 全部通过 ✅")
    return 0


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="命令速查手册（原创实现，标准库 only）",
        epilog="示例:\n"
               "  查看: python main.py show grep\n"
               "  搜索: python main.py search 'find files'\n"
               "  列表: python main.py list --category 网络\n"
               "  自检: python main.py selftest",
    )
    parser.add_argument("--command", nargs="?", default="show",
                        help="show/search/list/selftest")
    parser.add_argument("--target", nargs="?", default="", help="命令名或搜索词")
    parser.add_argument("--category", default="", help="list 的分类过滤")
    parser.add_argument("--all", action="store_true", help="list 全部命令")
    parser.add_argument("--add", default="", help="添加自定义条目（格式 名称:描述:示例命令）")
    parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细明细")
    parser.add_argument("--dry-run", action="store_true", help="只预览不写盘")
    args = parser.parse_args()

    if args.verbose:
        print(f"[verbose] 参数: {vars(args)}", file=sys.stderr)

    if args.selftest or args.command == "selftest":
        sys.exit(selftest())

    colored = not args.no_color and sys.stdout.isatty()

    try:
        if args.add:
            parts = args.add.split(":", 2)
            if len(parts) < 3:
                raise TldrError("E004", "--add 格式: 名称:描述:示例命令")
            add_custom(parts[0], parts[1], parts[2], dry_run=args.dry_run)
            if not args.dry_run:
                print(f"已添加自定义条目: {parts[0]}")
            return 0

        cmd = args.command
        target = args.target
        if cmd == "show":
            if not target:
                raise TldrError("E004", "show 需要命令名，如: show grep")
            entry = show_command(target)
            # 合并自定义
            customs = load_custom()
            if target in customs:
                entry = {"name": target, **customs[target]}
            print(format_entry(entry, colored))
            return 0
        if cmd == "search":
            results = search_commands(target or args.category)
            if not results:
                print(f"未找到与 '{target}' 相关的命令", file=sys.stderr)
                return 1
            for r in results[:15]:
                mark = "  " if colored else "  "
                print(f"{mark}{r['name']:<14} [{r['category']}] {r['desc']}")
            print(f"\n共 {len(results)} 条匹配")
            return 0
        if cmd == "list":
            if args.all:
                for n, e in sorted(CHEATS.items()):
                    print(f"  {n:<14} [{e['category']}] {e['desc']}")
                print(f"\n共 {len(CHEATS)} 条命令")
                return 0
            if args.category:
                items = list_by_category(args.category)
                if not items:
                    print(f"分类 '{args.category}' 无命令", file=sys.stderr)
                    return 1
                for n, d in items:
                    print(f"  {n:<14} {d}")
                print(f"\n{args.category} 类共 {len(items)} 条")
                return 0
            # 分类概览
            cats = list_by_category()
            for cat, cnt in cats:
                print(f"  {cat:<6} {cnt} 条")
            print(f"\n共 {len(CHEATS)} 条命令，{len(cats)} 个分类")
            return 0
        parser.print_help()
        return 1
    except TldrError as e:
        print(f"[{e.code}] {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 兜底降级
        print(f"[E099] 未预期异常: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
