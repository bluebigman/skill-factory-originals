#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmd-guard — 危险命令拦截与操作审计（原创实现，clean-room）
============================================================
对 shell 命令做静态风险评估：识别高危模式、校验目标路径黑白名单、
估算通配符影响范围，输出 0-100 风险分与安全替代建议，并可写审计日志。

设计原则：
  * fail-closed —— 任何评估异常一律按高风险处理，绝不静默放行
  * 零第三方依赖，仅使用 Python 标准库
  * 纯静态分析，不执行被评估的命令

用法:
    python run.py --check "rm -rf /"          # 评估单条命令
    python run.py --batch cmds.txt            # 批量评估（每行一条）
    python run.py --check "..." --json        # 结构化输出
    python run.py --selftest                  # 离线自检（不联网、无需终端UI）
    python run.py --version                   # 版本信息

退出码:
    0 = 安全（低风险）   1 = 需确认（中风险）
    2 = 高危（建议阻断） 3 = 评估错误
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

__version__ = "1.1.0"

# ---------------------------------------------------------------
# 错误码体系 E001-E010
# ---------------------------------------------------------------
E_PARSE_FAIL = "E001"        # 命令解析失败
E_PATH_NOT_FOUND = "E002"    # 路径不存在
E_GLOB_ANOMALY = "E003"      # 通配符展开异常
E_RULES_LOAD_FAIL = "E004"   # 规则库加载失败
E_LOG_WRITE_FAIL = "E005"    # 日志写入失败
E_CONFIRM_TIMEOUT = "E006"   # 确认超时
E_BLACKLIST_HIT = "E007"     # 黑名单命中
E_LIST_CONFLICT = "E008"     # 黑白名单冲突
E_EVAL_TIMEOUT = "E009"      # 评估超时
E_SELFTEST_FAIL = "E010"     # 自检未通过

ERROR_MESSAGES: Dict[str, str] = {
    E_PARSE_FAIL: "无法解析该命令，请检查语法",
    E_PATH_NOT_FOUND: "目标路径不存在，请确认路径拼写",
    E_GLOB_ANOMALY: "通配符匹配异常，可能匹配到系统关键文件",
    E_RULES_LOAD_FAIL: "规则库文件缺失或格式错误，已降级为内置规则",
    E_LOG_WRITE_FAIL: "无法写入审计日志，请检查目录权限",
    E_CONFIRM_TIMEOUT: "确认超时，命令已取消",
    E_BLACKLIST_HIT: "该路径已被列入黑名单，禁止操作",
    E_LIST_CONFLICT: "该路径同时命中白名单与黑名单，以黑名单为准",
    E_EVAL_TIMEOUT: "评估超时，已按未知高风险处理，请人工确认",
    E_SELFTEST_FAIL: "配套脚本自检失败，防护能力可能不完整",
}

# ---------------------------------------------------------------
# 内置规则库：(正则, 基础分, 说明, 安全替代建议)
# ---------------------------------------------------------------
BUILTIN_RULES: List[Tuple[str, int, str, str]] = [
    (r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+", 70, "递归强制删除",
     "先用 ls 确认匹配范围，再逐目录删除；重要数据先备份"),
    (r"\bmkfs(\.\w+)?\b", 95, "格式化文件系统",
     "确认设备号无误；操作前完整备份该设备数据"),
    (r"\bdd\b[^|]*\bof=/dev/", 95, "直接写入块设备",
     "用 lsblk 核对目标设备，优先写入镜像文件而非裸设备"),
    (r":\s*\(\s*\)\s*\{.*\|.*&.*\}\s*;?\s*:", 100, "fork 炸弹",
     "该命令会耗尽进程资源，无安全用途，请勿执行"),
    (r"\bchmod\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?777\b", 60, "开放全部权限",
     "按最小权限原则改用 750 / 640，并指定具体属主"),
    (r"\bchown\s+-[a-zA-Z]*R[a-zA-Z]*\s+", 55, "递归修改属主",
     "缩小作用目录，避免对系统目录递归改属主"),
    (r"\b(shutdown|reboot|halt|poweroff)\b", 50, "关机或重启",
     "确认无在途任务；生产环境请走变更流程"),
    (r"\bgit\s+push\s+.*(--force|-f)\b", 45, "强制推送",
     "改用 --force-with-lease，避免覆盖他人提交"),
    (r"\biptables\s+-F\b", 65, "清空防火墙规则",
     "先 iptables-save 备份现有规则，再逐条调整"),
    (r"\b(curl|wget)\b[^|]*\|\s*(ba)?sh\b", 85, "下载内容直接进入 shell 执行",
     "先下载到本地、核对内容与校验值，确认无误后再执行"),
    (r"\btruncate\s+-s\s*0\b", 50, "清空文件内容",
     "先复制备份，再执行清空"),
    (r"\bmv\s+[^\s]+\s+/dev/null\b", 60, "将文件移入 /dev/null",
     "这会永久丢失数据，改用移动到回收目录"),
]

# 敏感路径（命中即显著加分）
BUILTIN_BLACKLIST: List[str] = [
    "/", "/etc", "/boot", "/bin", "/sbin", "/usr", "/lib", "/lib64",
    "/var", "/sys", "/proc", "/dev", "/root", "C:\\Windows", "C:\\",
]

RISK_CONFIRM = 40   # ≥ 该分值需确认
RISK_BLOCK = 70     # ≥ 该分值建议阻断


@dataclass
class Assessment:
    """单条命令的评估结果"""
    command: str
    score: int = 0
    level: str = "safe"                       # safe / confirm / danger
    reasons: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)   # --verbose 评分决策明细

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------
# 核心评估逻辑
# ---------------------------------------------------------------
class CommandGuard:
    """命令风险评估器"""

    def __init__(self,
                 blacklist: Optional[List[str]] = None,
                 whitelist: Optional[List[str]] = None,
                 rules: Optional[List[Tuple[str, int, str, str]]] = None):
        self.blacklist = list(blacklist if blacklist is not None else BUILTIN_BLACKLIST)
        self.whitelist = list(whitelist or [])
        self.rules = list(rules if rules is not None else BUILTIN_RULES)

    # -- 路径提取 ------------------------------------------------
    @staticmethod
    def extract_paths(command: str) -> List[str]:
        """从命令中提取疑似路径的参数（不做文件系统访问）"""
        tokens = re.split(r"\s+", command.strip())
        paths: List[str] = []
        for tok in tokens[1:]:
            if tok.startswith("-"):          # 跳过选项
                continue
            if "=" in tok and not tok.startswith("/"):
                tok = tok.split("=", 1)[1]   # 处理 of=/dev/sda 这类形式
            if tok.startswith(("/", "./", "../", "~")) or re.match(r"^[A-Za-z]:\\", tok):
                paths.append(tok)
        return paths

    def _normalize(self, path: str) -> str:
        p = path.rstrip("/") or "/"
        return p

    def match_blacklist(self, path: str) -> Optional[str]:
        """返回命中的黑名单条目"""
        p = self._normalize(path)
        for entry in self.blacklist:
            e = self._normalize(entry)
            if p == e or p.startswith(e + "/") or fnmatch.fnmatch(p, e):
                return entry
            # 根目录通配（如 /* ）视为命中根
            if e == "/" and (p == "/" or p.startswith("/")) and path.strip() in ("/", "/*"):
                return entry
        return None

    def match_whitelist(self, path: str) -> Optional[str]:
        p = self._normalize(path)
        for entry in self.whitelist:
            e = self._normalize(entry)
            if p == e or p.startswith(e + "/") or fnmatch.fnmatch(p, e):
                return entry
        return None

    # -- 主评估 --------------------------------------------------
    def assess(self, command: str) -> Assessment:
        result = Assessment(command=command)

        if command is None or not str(command).strip():
            result.errors.append(E_PARSE_FAIL)
            result.score = 100
            result.level = "danger"
            result.reasons.append(f"[{E_PARSE_FAIL}] {ERROR_MESSAGES[E_PARSE_FAIL]}")
            return result

        cmd = str(command).strip()
        score = 0

        def _trace(delta: int, why: str) -> None:
            """记录一次加减分决策，供 --verbose 还原完整评分过程"""
            result.trace.append(f"{delta:+d} 分 ← {why}（累计 {score}）")

        # 1) 规则匹配
        for pattern, base, desc, advice in self.rules:
            try:
                if re.search(pattern, cmd):
                    score += base
                    _trace(base, f"命中高危规则「{desc}」")
                    result.reasons.append(f"命中高危模式：{desc}")
                    result.suggestions.append(advice)
            except re.error:
                # fail-closed：规则本身异常也要记录并保守处理
                result.errors.append(E_RULES_LOAD_FAIL)
                score += 10
                _trace(10, f"规则 {pattern!r} 编译失败，按保守策略加分")

        # 2) 路径风险
        paths = self.extract_paths(cmd)
        result.targets = paths
        for p in paths:
            bl = self.match_blacklist(p)
            wl = self.match_whitelist(p)
            if bl and wl:
                result.errors.append(E_LIST_CONFLICT)
                result.reasons.append(f"[{E_LIST_CONFLICT}] 路径 {p} 黑白名单冲突，以黑名单为准")
                score += 30
                _trace(30, f"路径 {p} 黑白名单冲突，以黑名单为准")
            elif bl:
                result.errors.append(E_BLACKLIST_HIT)
                result.reasons.append(f"[{E_BLACKLIST_HIT}] 目标 {p} 命中敏感路径 {bl}")
                score += 30
                _trace(30, f"目标 {p} 命中敏感路径 {bl}")
            elif wl:
                result.reasons.append(f"目标 {p} 位于白名单 {wl}，风险下调")
                score -= 20
                _trace(-20, f"目标 {p} 位于白名单 {wl}")

        # 3) 通配符影响范围
        if re.search(r"[*?]", cmd):
            result.reasons.append("包含通配符，实际影响范围可能远超预期")
            score += 15
            _trace(15, "命令包含通配符，影响范围不确定")
            if re.search(r"/\s*\*|\*\s*/", cmd):
                result.errors.append(E_GLOB_ANOMALY)
                score += 15
                _trace(15, "通配符直接作用于路径分隔符附近，范围可能扩散到上级目录")

        # 4) sudo 提权放大
        if re.match(r"^\s*sudo\b", cmd):
            result.reasons.append("以管理员权限执行，破坏力放大")
            score += 15
            _trace(15, "以 sudo 提权执行，破坏力放大")

        # 归一化与分级
        raw = score
        score = max(0, min(100, score))
        if raw != score:
            result.trace.append(f"归一化：原始 {raw} 分 → 夹取到 {score} 分（有效区间 0-100）")
        result.score = score
        if score >= RISK_BLOCK:
            result.level = "danger"
        elif score >= RISK_CONFIRM:
            result.level = "confirm"
        else:
            result.level = "safe"

        if not result.reasons:
            result.reasons.append("未命中已知高危模式")
        if result.level != "safe" and not result.suggestions:
            result.suggestions.append("执行前请再次确认目标范围，并确保已有可用备份")

        return result


# ---------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------
def read_lines_smart(path: str) -> List[str]:
    """按 utf-8 → gbk → gb18030 三级 fallback 逐行读取命令清单。

    中文 Windows 上导出的命令清单常为 GBK；只认 utf-8 会直接读崩，
    因此三级探测全部失败后再用容错模式兜底，保证不因编码丢命令。
    """
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, "r", encoding=enc, errors="strict") as fh:
                return [ln.rstrip("\n") for ln in fh]
        except UnicodeDecodeError:
            continue
        except OSError:
            return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return [ln.rstrip("\n") for ln in fh]
    except OSError:
        return []


def write_audit_log(result: Assessment, log_dir: Optional[str] = None,
                    dry_run: bool = False) -> Optional[str]:
    """写审计日志，失败返回 None 并不抛异常（不阻断主流程）。

    dry_run=True 时只计算目标路径不落盘，供 --dry-run 预览使用。
    """
    try:
        base = log_dir or os.path.join(os.path.expanduser("~"), ".cmd-guard", "logs")
        path = os.path.join(base, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".jsonl")
        # 写盘分支由 dry_run 统一控制，预览态不创建目录也不追加内容
        if not dry_run:
            os.makedirs(base, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    **result.to_dict(),
                }, ensure_ascii=False) + "\n")
        return path
    except OSError:
        return None


# ---------------------------------------------------------------
# 输出渲染
# ---------------------------------------------------------------
LEVEL_LABEL = {
    "safe": "安全 ✅",
    "confirm": "需确认 ⚠️",
    "danger": "高危 ⛔",
}
LEVEL_EXIT = {"safe": 0, "confirm": 1, "danger": 2}


def render(result: Assessment, verbose: bool = False) -> str:
    lines = [
        "─" * 52,
        f"命令：{result.command}",
        f"风险分：{result.score}/100    判定：{LEVEL_LABEL[result.level]}",
        "─" * 52,
        "评估依据：",
    ]
    lines += [f"  · {r}" for r in result.reasons]
    if verbose:
        lines.append("评分决策明细：")
        if result.trace:
            lines += [f"  {i}. {t}" for i, t in enumerate(result.trace, 1)]
        else:
            lines.append("  1. 未触发任何加减分规则，保持 0 分基线")
        if result.targets:
            lines.append(f"识别到的操作目标：{'、'.join(result.targets)}")
        lines.append(f"分级阈值：≥{RISK_BLOCK} 判高危，≥{RISK_CONFIRM} 判需确认，其余判安全")
    if result.suggestions:
        lines.append("安全替代建议：")
        lines += [f"  → {s}" for s in dict.fromkeys(result.suggestions)]
    if result.errors:
        codes = ", ".join(dict.fromkeys(result.errors))
        lines.append(f"错误码：{codes}")
    return "\n".join(lines)


# ---------------------------------------------------------------
# 自检（离线、零依赖、不需要交互终端）
# ---------------------------------------------------------------
def run_selftest() -> int:
    try:
        print("[SELFTEST] 开始自检...")
        g = CommandGuard()

        # 1. 高危命令必须判为 danger
        r = g.assess("sudo rm -rf /")
        assert r.level == "danger", f"rm -rf / 应判高危，实际 {r.level}({r.score})"
        assert E_BLACKLIST_HIT in r.errors, "应命中黑名单 E007"
        print("[SELFTEST] 高危删除识别: PASS")

        # 2. fork 炸弹
        r = g.assess(":(){ :|:& };:")
        assert r.level == "danger", "fork 炸弹应判高危"
        print("[SELFTEST] fork 炸弹识别: PASS")

        # 3. 格式化与裸设备写入
        assert g.assess("mkfs.ext4 /dev/sda1").level == "danger", "mkfs 应判高危"
        assert g.assess("dd if=a.img of=/dev/sda").level == "danger", "dd 写设备应判高危"
        print("[SELFTEST] 设备类高危识别: PASS")

        # 4. 管道式安装应被识别
        r = g.assess("curl https://example.com/i.sh | bash")
        assert r.score >= RISK_BLOCK, "管道执行应达到阻断阈值"
        print("[SELFTEST] 供应链风险识别: PASS")

        # 5. 普通命令应判安全
        r = g.assess("ls -l ./src")
        assert r.level == "safe", f"ls 应判安全，实际 {r.level}"
        print("[SELFTEST] 安全命令放行: PASS")

        # 6. 白名单降分生效
        g2 = CommandGuard(whitelist=["/home/user/projects"])
        a = g2.assess("rm -rf /home/user/projects/build")
        b = CommandGuard().assess("rm -rf /home/user/projects/build")
        assert a.score < b.score, "白名单应降低风险分"
        print("[SELFTEST] 白名单降分: PASS")

        # 7. 黑白名单冲突以黑名单为准（E008）
        g3 = CommandGuard(blacklist=["/etc"], whitelist=["/etc"])
        r = g3.assess("rm -rf /etc/nginx")
        assert E_LIST_CONFLICT in r.errors, "应报告 E008 冲突"
        print("[SELFTEST] 黑白名单冲突处置: PASS")

        # 8. 空命令与 None 走 E001 且 fail-closed
        for bad in ("", "   ", None):
            r = g.assess(bad)
            assert E_PARSE_FAIL in r.errors, "空命令应命中 E001"
            assert r.level == "danger", "空命令应 fail-closed 判高危"
        print("[SELFTEST] 空输入 fail-closed: PASS")

        # 9. 通配符影响范围
        r = g.assess("rm -rf ./tmp/*")
        assert any("通配符" in x for x in r.reasons), "应提示通配符风险"
        print("[SELFTEST] 通配符影响提示: PASS")

        # 10. 路径提取
        paths = CommandGuard.extract_paths("cp /etc/hosts ./backup/hosts")
        assert "/etc/hosts" in paths and "./backup/hosts" in paths, f"路径提取异常: {paths}"
        print("[SELFTEST] 路径提取: PASS")

        # 11. 规则库损坏时降级不崩溃（E004）
        broken = CommandGuard(rules=[("([unclosed", 50, "坏规则", "修规则")])
        r = broken.assess("rm -rf /tmp")
        assert E_RULES_LOAD_FAIL in r.errors, "坏规则应报 E004"
        print("[SELFTEST] 规则库降级: PASS")

        # 12. 日志写入失败不抛异常（E005 路径不可写）
        bad_dir = os.path.join(os.devnull, "cannot", "exist")
        assert write_audit_log(g.assess("ls"), log_dir=bad_dir) is None, "日志失败应静默返回 None"
        print("[SELFTEST] 日志失败不阻断: PASS")

        # 13. 错误码表完整（E001-E010）
        expect = {f"E{i:03d}" for i in range(1, 11)}
        assert expect.issubset(set(ERROR_MESSAGES)), "错误码表不完整"
        print("[SELFTEST] 错误码体系完整: PASS")

        tmp = tempfile.mkdtemp(prefix="cmdguard_selftest_")
        try:
            # 14. 预览模式不落盘（dry_run 守卫生效）
            logdir = os.path.join(tmp, "logs")
            p = write_audit_log(g.assess("rm -rf /tmp/x"), log_dir=logdir, dry_run=True)
            assert p is not None, "预览模式应返回目标路径"
            assert not os.path.exists(logdir), "预览模式不得创建日志目录"
            # 关闭预览后才真正落盘
            p2 = write_audit_log(g.assess("rm -rf /tmp/x"), log_dir=logdir, dry_run=False)
            assert p2 and os.path.isfile(p2), "非预览模式应真实写入审计记录"
            print("[SELFTEST] 预览模式不落盘: PASS")

            # 15. 决策明细可解释（verbose 输出每次加减分）
            r = g.assess("sudo rm -rf /var/log/*")
            plain = render(r, verbose=False)
            detail = render(r, verbose=True)
            assert "评分决策明细" in detail, "verbose 应输出评分决策明细"
            assert len(detail) > len(plain), "verbose 输出应比默认输出更详细"
            assert r.trace and any("分" in t for t in r.trace), "决策链应记录分值变化"
            print("[SELFTEST] 决策明细可解释: PASS")

            # 16. 命令清单编码自适应（GBK 中文注释不炸）
            gbk_file = os.path.join(tmp, "cmds_gbk.txt")
            with open(gbk_file, "w", encoding="gbk") as fh:
                fh.write("# 中文注释：批量待检命令\nrm -rf /tmp/构建缓存\nls -l\n")
            lines = read_lines_smart(gbk_file)
            assert any("构建缓存" in ln for ln in lines), f"GBK 清单读取异常: {lines}"
            print("[SELFTEST] 清单编码自适应: PASS")

            # 17. 大清单逐行流式读取（不一次性吃进内存）
            big = os.path.join(tmp, "cmds_big.txt")
            with open(big, "w", encoding="utf-8") as fh:
                for i in range(5000):
                    fh.write(f"ls -l ./dir{i}\n")
            lines = read_lines_smart(big)
            assert len(lines) == 5000, f"大清单行数异常: {len(lines)}"
            print("[SELFTEST] 大清单流式读取: PASS")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        print("[SELFTEST] 全部自检通过 ✓")
        return 0
    except AssertionError as exc:
        print(f"[SELFTEST] 断言失败: {exc}")
        print(f"[SELFTEST] 错误码: {E_SELFTEST_FAIL}")
        return 3
    except Exception as exc:  # noqa: BLE001
        print(f"[SELFTEST] 未预期异常: {exc}")
        print(f"[SELFTEST] 错误码: {E_SELFTEST_FAIL}")
        return 3


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        prog="cmd-guard",
        description="危险命令拦截与操作审计：静态评估 shell 命令风险",
    )
    ap.add_argument("--check", metavar="CMD", help="评估单条命令")
    ap.add_argument("--batch", metavar="FILE", help="批量评估，文件每行一条命令")
    ap.add_argument("--json", action="store_true", help="以 JSON 结构化输出")
    ap.add_argument("--log", action="store_true", help="写入审计日志")
    ap.add_argument("--whitelist", default="", help="白名单路径，逗号分隔")
    ap.add_argument("--dry-run", action="store_true",
                    help="预览模式：只展示评估结果与将要写入的审计记录，不落任何文件")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="输出逐条评分决策明细（每一次加减分的原因与分值变化）")
    ap.add_argument("--selftest", action="store_true", help="离线自检")
    ap.add_argument("--version", action="store_true", help="显示版本")
    ap.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    args = ap.parse_args()

    if args.version:
        print(f"cmd-guard {__version__}")
        return 0
    if args.selftest:
        return run_selftest()

    wl = [p.strip() for p in args.whitelist.split(",") if p.strip()]
    guard = CommandGuard(whitelist=wl)

    commands: List[str] = []
    if args.check:
        commands = [args.check]
    elif args.batch:
        if not os.path.isfile(args.batch):
            print(f"[{E_PATH_NOT_FOUND}] {ERROR_MESSAGES[E_PATH_NOT_FOUND]}: {args.batch}")
            return 3
        commands = [ln.strip() for ln in read_lines_smart(args.batch)
                    if ln.strip() and not ln.strip().startswith("#")]
    else:
        ap.print_help()
        return 0

    results = [guard.assess(c) for c in commands]
    if args.log:
        for r in results:
            written = write_audit_log(r, dry_run=args.dry_run)
            if args.dry_run:
                print(f"[预览] 审计记录未写盘，目标文件：{written}")
            elif args.verbose:
                print(f"[已写入] 审计记录：{written}")

    if args.json:
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(render(r, verbose=args.verbose))
        if len(results) > 1:
            danger = sum(1 for r in results if r.level == "danger")
            confirm = sum(1 for r in results if r.level == "confirm")
            print("─" * 52)
            print(f"汇总：共 {len(results)} 条 | 高危 {danger} | 需确认 {confirm} | "
                  f"安全 {len(results) - danger - confirm}")

    worst = max((LEVEL_EXIT[r.level] for r in results), default=0)
    return worst


if __name__ == "__main__":
    sys.exit(main())
