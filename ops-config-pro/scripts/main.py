#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy-config-linter — 部署配置规范校验

按内置规则集校验部署配置（缩进型 YAML 子集或键值对），输出违规项、等级、合规分与可执行修正建议。

规则分两类：
  1) 单键规则：副本数下限、单副本风险、镜像标签、端口范围与特权端口、CPU 与内存写法及配额
  2) 结构规则：探针声明、资源限额声明、挂载与存储声明配套、环境变量命名

领域：运维/配置解析/部署（平台 TOP20 占 11 席）
本实现完全离线：不发起网络调用、不读写用户隐私数据、不依赖第三方库。
"""
import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"


def is_int(v):
    return re.fullmatch(r"-?\d+", str(v).strip()) is not None


def as_num(v):
    """取数值（支持 500m 这类毫核写法），取不到返回 None"""
    s = str(v).strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)m?", s)
    if not m:
        return None
    val = float(m.group(1))
    return val / 1000.0 if s.endswith("m") else val


def mem_mib(v):
    """把内存写法换算成 MiB，无法识别返回 None"""
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(Ki|Mi|Gi|K|M|G)?", str(v).strip())
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2) or "Mi"
    factor = {"Ki": 1 / 1024.0, "Mi": 1.0, "Gi": 1024.0,
              "K": 1000.0 / 1048576.0, "M": 1000000.0 / 1048576.0,
              "G": 1000000000.0 / 1048576.0}
    return n * factor[unit]


# ---------------------------------------------------------- 单键规则
# (规则名, 路径正则, 判定函数(返回值→是否违规), 等级, 问题说明, 修正建议)
KEY_RULES = [
    ("replicas-floor", r"(^|\.)replicas$",
     lambda v: (not is_int(v)) or int(v) < 1, "ERROR",
     "副本数必须为 ≥1 的整数", "把 replicas 调整为至少 1"),
    ("replicas-spof", r"(^|\.)replicas$",
     lambda v: is_int(v) and int(v) == 1, "WARN",
     "单副本存在单点故障风险", "生产环境建议 replicas ≥2"),
    ("image-no-latest", r"(^|\.)image$",
     lambda v: str(v).strip().endswith(":latest") or ":" not in str(v).strip(), "ERROR",
     "镜像必须使用明确版本标签", "把 :latest 换成固定版本号或内容摘要"),
    ("port-range", r"(^|\.)port$",
     lambda v: (not is_int(v)) or not (1 <= int(v) <= 65535), "ERROR",
     "端口必须在 1-65535 之间", "把端口改为 1-65535 范围内的整数"),
    ("port-privileged", r"(^|\.)port$",
     lambda v: is_int(v) and int(v) < 1024, "WARN",
     "使用特权端口需要额外权限", "改用 ≥1024 端口，或显式声明所需权限"),
    ("cpu-format", r"(^|\.)cpu$",
     lambda v: as_num(v) is None, "ERROR",
     "CPU 限额写法无法识别", "写成 0.5 / 2 / 500m 这类写法"),
    ("cpu-overcommit", r"(^|\.)cpu$",
     lambda v: as_num(v) is not None and as_num(v) > 8, "WARN",
     "CPU 限额超过 8 核，单机可调度风险高", "拆分实例或下调到实际所需"),
    ("memory-format", r"(^|\.)memory$",
     lambda v: mem_mib(v) is None, "ERROR",
     "内存写法不规范", "使用 512Mi / 1Gi 这类带单位写法"),
    ("memory-too-small", r"(^|\.)memory$",
     lambda v: mem_mib(v) is not None and mem_mib(v) < 64, "WARN",
     "内存限额小于 64Mi，容器极易被终止", "上调到实际所需，建议 ≥128Mi"),
    ("env-name-upper", r"(^|\.)env\.[^.]+$",
     lambda v: False, "INFO",
     "环境变量键名规范检查", "统一为大写字母 + 数字 + 下划线"),
]


def env_name_violation(key):
    """环境变量键名是否不规范（小写 / 含空格 / 以数字开头）"""
    leaf = key.split(".")[-1]
    return re.fullmatch(r"[A-Z][A-Z0-9_]*", leaf) is None


def is_workload(flat):
    """判断这份配置是否在描述一个可运行负载（有镜像或副本数）"""
    return any(re.search(r"(^|\.)(image|replicas)$", k) for k in flat)


def run_key_rules(flat):
    """执行单键规则"""
    viol = []
    for key, val in sorted(flat.items()):
        for name, path_re, check, level, msg, fix in KEY_RULES:
            if not re.search(path_re, key):
                continue
            if name == "env-name-upper":
                if env_name_violation(key):
                    viol.append({"rule": name, "level": "WARN", "path": key, "value": val,
                                 "message": "环境变量键名不符合大写加下划线规范",
                                 "fix": "改写为大写字母 + 数字 + 下划线"})
                continue
            try:
                bad = check(val)
            except Exception:
                bad = False
            if bad:
                viol.append({"rule": name, "level": level, "path": key, "value": val,
                             "message": msg, "fix": fix})
    return viol


def has_path(flat, leaf_re):
    """是否存在以 leaf_re 结尾的路径"""
    return any(re.search(leaf_re, k) for k in flat)


def run_structural_rules(flat):
    """执行结构规则：探针、资源限额、挂载与存储配套"""
    viol = []
    if not is_workload(flat):
        return viol
    if not has_path(flat, r"(^|\.)livenessProbe$"):
        viol.append({"rule": "probe-missing", "level": "WARN", "path": "(整个负载)",
                     "value": "-", "message": "未声明存活探针，实例假死无法被自动拉起",
                     "fix": "补充 livenessProbe，并核对探针路径与端口"})
    if not has_path(flat, r"(^|\.)readinessProbe$"):
        viol.append({"rule": "readiness-missing", "level": "WARN", "path": "(整个负载)",
                     "value": "-", "message": "未声明就绪探针，流量可能在实例未就绪时进入",
                     "fix": "补充 readinessProbe，避免就绪前接流量"})
    if not (has_path(flat, r"(^|\.)cpu$") and has_path(flat, r"(^|\.)memory$")):
        viol.append({"rule": "resource-limit-missing", "level": "WARN", "path": "(整个负载)",
                     "value": "-", "message": "未同时声明 CPU 与内存限额，易引发资源争抢",
                     "fix": "同时补充 cpu 与 memory 限额"})
    if has_path(flat, r"(^|\.)volumeMounts(\.|$|\[)") and not has_path(flat, r"(^|\.)volumes$"):
        viol.append({"rule": "volume-dangling", "level": "ERROR", "path": "(整个负载)",
                     "value": "-", "message": "声明了挂载点但未声明对应存储卷",
                     "fix": "补齐 volumes / persistentVolumeClaim 声明"})
    return viol


def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030", "latin-1")):
    """多编码容错读取（utf-8 → gbk → gb18030 → latin-1 → replace 兜底）"""
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except Exception:
            break
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_json(path, obj):
    """写结构化结果（目录不存在则创建）"""
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def stable_id(text, length=12):
    """内容稳定短标识（用于去重与引用，非加密用途）"""
    import hashlib
    return hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def rate(numerator, denominator, digits=2):
    """百分比（分母为 0 时返回 0.0，不抛异常）"""
    if not denominator:
        return 0.0
    return round(numerator * 100.0 / denominator, digits)


def parse_indented(text, indent=2):
    """解析缩进型 YAML 子集 → 扁平路径表

    支持「键: 值」、「键:」+ 更深缩进子块、以及 `- ` 列表项（路径带 [i]）。
    不引入第三方依赖，仅覆盖部署配置常用子集。
    """
    flat, stack, list_index = {}, [], {}
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        stripped = raw.lstrip(" ")
        depth = (len(raw) - len(stripped)) // max(1, indent)
        m_list = re.match(r"^-\s*(?P<val>.*)$", stripped)
        if m_list:
            parent = ".".join(k for d, k in stack if d < depth)
            idx = list_index.get(parent, 0)
            list_index[parent] = idx + 1
            path = f"{parent}[{idx}]" if parent else f"[{idx}]"
            val = m_list.group("val").strip().strip("\"'")
            if val:
                flat[path] = val
            stack = [(d, k) for d, k in stack if d < depth]
            continue
        m = re.match(r"^(?P<key>[^:]+):\s*(?P<val>.*)$", stripped)
        if not m:
            continue
        key = m.group("key").strip().strip("\"'")
        val = m.group("val").strip()
        stack = [(d, k) for d, k in stack if d < depth]
        path = ".".join([k for _d, k in stack] + [key])
        stack.append((depth, key))
        if val:
            flat[path] = val.strip().strip("\"'")
    return flat


def parse_kv(text):
    """解析 KEY=VALUE / KEY: VALUE 平铺形式"""
    flat = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(?P<key>[A-Za-z_][\w.\-]*)\s*[=:]\s*(?P<val>.+)$", line)
        if m:
            flat[m.group("key")] = m.group("val").strip().strip("\"'")
    return flat


def parse_deploy_text(text):
    """自动选择解析器：能解析出缩进层级就走 YAML 子集，否则走平铺键值"""
    flat = parse_indented(text)
    return flat if flat else parse_kv(text)


def score_report(violations):
    """合规分：满分 100，ERROR 扣 12、WARN 扣 4、INFO 不扣，下限 0"""
    penalty = sum({"ERROR": 12, "WARN": 4}.get(v["level"], 0) for v in violations)
    return max(0, 100 - penalty)


def suggest_fixes(violations):
    """汇总可执行修正建议（去重保序）"""
    fixes, seen = [], set()
    for v in violations:
        if v["fix"] not in seen:
            seen.add(v["fix"])
            fixes.append({"level": v["level"], "path": v["path"], "fix": v["fix"]})
    return fixes


def render_lint_md(violations, score):
    """校验报告 Markdown"""
    lines = [f"**合规分：{score}/100**", "",
             "| 等级 | 路径 | 当前值 | 问题 | 修正建议 |", "|---|---|---|---|---|"]
    if not violations:
        lines.append("| - | - | - | 未发现违规项 | - |")
    for v in violations[:50]:
        lines.append(f"| {v['level']} | {v['path']} | {v['value']} | {v['message']} | {v['fix']} |")
    if len(violations) > 50:
        lines.append(f"| … | 其余 {len(violations) - 50} 项已省略 | | | |")
    return "\n".join(lines)


def process(text):
    """主流程：解析 → 单键规则 + 结构规则 → 打分 → 出修正建议"""
    if not text or not text.strip():
        return {"ok": False, "error": "输入为空，无法校验部署配置",
                "next_action": "把部署配置文件内容贴进来（支持缩进型 YAML 子集或键值对）"}
    flat = parse_deploy_text(text)
    if not flat:
        return {"ok": False, "error": "未解析到任何配置项",
                "next_action": "确认输入为「键: 值」缩进结构或 KEY=VALUE 平铺结构"}
    violations = run_key_rules(flat) + run_structural_rules(flat)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    violations.sort(key=lambda v: (order.get(v["level"], 3), v["path"]))
    score = score_report(violations)
    errors = sum(1 for v in violations if v["level"] == "ERROR")
    warns = sum(1 for v in violations if v["level"] == "WARN")
    return {
        "ok": True,
        "conclusion": (f"合规分 {score}/100；ERROR {errors} 项、WARN {warns} 项"
                       + ("，必须修复 ERROR 后才可发布" if errors else "，可直接发布")),
        "score": score,
        "error_count": errors,
        "warn_count": warns,
        "parsed_keys": len(flat),
        "parsed": flat,
        "violations": violations,
        "suggested_fixes": suggest_fixes(violations),
        "report_md": render_lint_md(violations, score),
        "next_action": ("按建议清单逐条修正 ERROR 项后重跑校验" if errors
                        else "无 ERROR 项，可进入发布流程"),
        "content_id": stable_id(text),
    }


def build_parser():
    p = argparse.ArgumentParser(
        prog="deploy-config-linter",
        description="按部署规范校验配置结构，输出违规项、合规分与修正建议")
    p.add_argument("--input", "-i", required=False, help="输入文件路径（部署配置文本）")
    p.add_argument("--out", "-o", default="out/result.json", help="结果输出路径（JSON）")
    p.add_argument("--dry-run", action="store_true", help="预览模式：只打印计划，不写盘")
    p.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.dry_run:
        print("[dry-run] 将读取:", args.input or "(stdin)")
        print("[dry-run] 将输出:", args.out)
        return 0
    if args.input and os.path.isfile(args.input):
        text = read_text_safe(args.input)
    else:
        text = sys.stdin.read()
    try:
        result = process(text)
    except Exception as exc:            # 异常降级：不抛出，转结构化错误
        result = {"ok": False, "error": str(exc)}
    write_json(args.out, result)
    print(json.dumps({"ok": result.get("ok", True), "out": args.out}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
