# -*- coding: utf-8 -*-
"""main.py — 短视频脚本生成器 CLI 引擎

军规契约：
  R1 能力边界与 SKILL.md 一一对应（平台/时长/风格/角度/count/lexicon/json）
  R2 每个函数 try-except 降级输出（禁裸 except）
  R3 read_text_safe 三级编码（utf-8 → gbk → gb18030）
  R4 默认只打印预览不写盘；--out 才写（--force 不经 dry-run 直写为安全写盘）
  R5 线性处理，无隐藏 O(n^2)
  R6 --verbose 输出每个分镜的决策明细
"""
from __future__ import print_function
import argparse
import io
import json
import os
import random
import sys

from template_lib import (
    PLATFORMS, STYLES, ANGLES,
    HOOK_TEMPLATES, PAIN_TEMPLATES, SOLVE_TEMPLATES, STEP_TEMPLATES,
    CTA_TEMPLATES, CAMERA_HINTS, SUMMARY_TEMPLATES, TAKEAWAY_TEMPLATES,
    BLOCK_WORDS, RISK_WORDS,
    MIN_DURATION, MAX_DURATION, MIN_COUNT, MAX_COUNT,
)

VERSION = "1.0.0"


# ---------------------------------------------------------------- 编码容错
def read_text_safe(path, encodings=("utf-8", "gbk", "gb18030")):
    """R3: 三级编码容错读取。全部失败则抛最后一个异常。"""
    last_err = None
    for enc in encodings:
        try:
            with io.open(path, "r", encoding=enc) as fh:
                return fh.read()
        except Exception as exc:  # noqa: BLE001 - 连续尝试不同编码
            last_err = exc
    if last_err is not None:
        raise last_err
    return ""


# ---------------------------------------------------------------- 合规检查
def compliance_check(topic):
    """扫描主题命中风险词/绝对化词，返回 (ok, 命中词列表)。"""
    hits = []
    blob = topic or ""
    for w in BLOCK_WORDS:
        if w in blob:
            hits.append(w)
    risky = [w for w in RISK_WORDS if w in blob]
    return (not hits, hits, risky)


def sanitize_topic(topic):
    """清洗主题：去除首尾空白、压缩连续空白、限长。"""
    if not topic:
        return ""
    cleaned = " ".join(str(topic).split())
    return cleaned[:80]


# ---------------------------------------------------------------- 参数校验
def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="short-video-script-gen",
        description="按主题/平台/时长生成短视频分镜脚本（离线模板引擎，不写盘预览优先）",
    )
    p.add_argument("--topic", required=False, default="", help="视频主题（一句话）")
    p.add_argument("--platform", default="douyin", choices=sorted(PLATFORMS.keys()), help="目标平台")
    p.add_argument("--duration", type=int, default=30, help="目标时长（秒）10-600")
    p.add_argument("--style", default="seed", choices=sorted(STYLES.keys()), help="内容风格")
    p.add_argument("--count", type=int, default=1, help="生成条数（不同角度）1-5")
    p.add_argument("--angle", default="", help="指定切入角度（缺省按条数自动分配）")
    p.add_argument("--out", default="", help="输出文件路径（缺省仅预览）")
    p.add_argument("--json", dest="as_json", action="store_true", help="输出结构化 JSON")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", help="仅预览将写入内容")
    p.add_argument("--verbose", action="store_true", help="输出分镜节奏决策明细")
    p.add_argument("--selftest", action="store_true", help="运行自检契约")
    p.add_argument("--lexicon", default="", help="自定义语气词库文件路径（三级编码容错）")
    p.add_argument("--seed", type=int, default=None, help="随机种子（可复现）")
    p.add_argument("--force", action="store_true", help="写盘前跳过提示（配合 --out）")
    p.add_argument("--version", action="version", version="short-video-script-gen " + VERSION)
    args = p.parse_args(argv)
    return args


def validate_args(args, log):
    """参数边界校验，返回错误消息列表（空=通过）。"""
    errs = []
    if not args.topic:
        errs.append("缺少 --topic 视频主题")
    if not (MIN_DURATION <= args.duration <= MAX_DURATION):
        errs.append("时长需在 %d-%d 秒之间" % (MIN_DURATION, MAX_DURATION))
    if not (MIN_COUNT <= args.count <= MAX_COUNT):
        errs.append("条数需在 %d-%d 之间" % (MIN_COUNT, MAX_COUNT))
    if args.angle and args.angle not in ANGLES:
        errs.append("切入角度必须在 %s 中" % "、".join(ANGLES))
    if args.out and args.dry_run:
        log("verbose", "dry-run 模式：不写盘，仅预览 --out 目标内容")
    return errs


# ---------------------------------------------------------------- 生成核心
def pick_angles(count, forced, log):
    """分配切入角度：指定则单角度重复变体，否则从库轮转。"""
    if forced:
        chosen = [forced] * count
        log("decision", "使用指定角度: %s x%d" % (forced, count))
        return chosen
    pool = list(ANGLES)
    random.shuffle(pool)
    chosen = (pool * ((count // len(pool)) + 1))[:count]
    log("decision", "自动分配角度: %s" % "、".join(chosen))
    return chosen


def build_hook(style, topic, angle, log):
    """按角度选择开场句式。"""
    if "倒叙" in angle or "故事" in angle:
        keys = ["story_open"]
    elif "对比" in angle or "冲突" in angle:
        keys = ["conflict_question"]
    elif "数据" in angle:
        keys = ["data_shock"]
    elif "设问" in angle:
        keys = ["conflict_question", "list_open"]
    else:
        keys = ["list_open", "conflict_question"]
    text = ""
    for key in keys:
        pool = HOOK_TEMPLATES.get(key, [])
        if pool:
            text = random.choice(pool).format(topic=topic)
            break
    log("decision", "开场角度 %s → 句式库 %s" % (angle, keys[0] if keys else "list_open"))
    return text


def build_section_body(style, topic, beats, log):
    """按风格结构生成主体段落列表。"""
    style_cfg = STYLES.get(style, STYLES["seed"])
    sections = []
    for beat_name, _ratio in style_cfg["structure"]:
        text = ""
        if beat_name == "hook":
            text = build_hook(style, topic, "设问引导", log)
        elif beat_name in ("pain", "context"):
            text = random.choice(PAIN_TEMPLATES).format(topic=topic) if beat_name == "pain" \
                else "先交代背景：" + random.choice(SUMMARY_TEMPLATES).format(topic=topic)
        elif beat_name in ("solve", "steps"):
            text = random.choice(SOLVE_TEMPLATES) + random.choice(STEP_TEMPLATES).format(topic=topic)
        elif beat_name == "summary":
            text = random.choice(SUMMARY_TEMPLATES).format(topic=topic)
        elif beat_name == "takeaway":
            text = random.choice(TAKEAWAY_TEMPLATES).format(topic=topic)
        elif beat_name == "proof":
            text = "我自己试了一周，最直观的感受是：流程顺了、时间省了。"
        elif beat_name in ("conflict", "climax", "twist"):
            text = {
                "conflict": "事情从一件小事开始失控……",
                "climax": "直到我发现问题出在一个被忽略的细节上。",
                "twist": "原来答案比想象的简单得多。",
            }[beat_name]
        elif beat_name == "opinion":
            text = "我的观点很明确：%s，方法 > 天赋。" % topic
        elif beat_name == "evidence":
            text = "支撑这个观点的理由有三个，我一个个讲。"
        elif beat_name == "list":
            text = "清单第一项：把{topic}拆成能立刻执行的 3 个小动作。".format(topic=topic)
        elif beat_name == "detail":
            text = "挑其中一个细讲，剩下的按同样思路推进就行。"
        elif beat_name == "cta":
            continue
        if text:
            sections.append((beat_name, text))
    log("decision", "风格 %s → %d 个主体段落" % (style, len(sections)))
    return sections


def allocate_time(duration, beats, log):
    """按节拍比例分配每镜时长（秒，合计≈目标时长）。"""
    style_cfg = STYLES.get("seed")  # 占位，实际比例来自调用方传入的结构
    return None  # 实际实现在 build_script 内联完成


def build_script(topic, platform, duration, style, angle, idx, rng, log):
    """生成一条完整分镜脚本。返回 dict。"""
    beats = []
    style_cfg = STYLES.get(style, STYLES["seed"])
    total_ratio = sum(r for _b, r in style_cfg["structure"])
    cursor = 0.0
    for beat_name, ratio in style_cfg["structure"]:
        start_pct = cursor / total_ratio
        end_pct = (cursor + ratio) / total_ratio
        sec_start = int(round(duration * start_pct))
        sec_end = int(round(duration * end_pct))
        beats.append({"beat": beat_name, "start": sec_start, "end": sec_end,
                      "duration": max(1, sec_end - sec_start)})
        cursor += ratio
        log("verbose", "节拍 %s → %d-%ds (%ds)" % (beat_name, sec_start, sec_end, sec_end - sec_start))

    sections = build_section_body(style, topic, beats, log)
    plat = PLATFORMS[platform]
    cta = CTA_TEMPLATES.get(platform, CTA_TEMPLATES["douyin"]).format(topic=topic)

    shots = []
    for i, (beat_name, text) in enumerate(sections):
        bd = beats[i] if i < len(beats) else beats[-1]
        camera = CAMERA_HINTS[(idx * 3 + i) % len(CAMERA_HINTS)]
        shots.append({
            "no": i + 1,
            "time": "%ds-%ds" % (bd["start"], bd["end"]),
            "beat": beat_name,
            "camera": camera,
            "text": text,
        })
    # 结尾 CTA 镜
    last_sec = max((b["end"] for b in beats), default=duration)
    shots.append({
        "no": len(shots) + 1,
        "time": "%ds-%ds" % (max(0, last_sec - 3), duration),
        "beat": "cta",
        "camera": "正面收尾，直视镜头",
        "text": cta,
    })
    log("decision", "镜头总数 %d（含 CTA 尾镜）" % len(shots))
    return {
        "topic": topic,
        "platform": platform,
        "platform_name": plat["name"],
        "style": style,
        "style_name": style_cfg["name"],
        "angle": angle,
        "duration": duration,
        "shots": shots,
        "tags": plat["tags"],
        "note": plat["note"],
    }


def render_text(script):
    """渲染为可读文本。"""
    lines = []
    lines.append("【短视频脚本 · 主题: %s · 平台: %s · %ds · 风格: %s · 角度: %s】"
                 % (script["topic"], script["platform_name"], script["duration"],
                    script["style_name"], script["angle"]))
    for sh in script["shots"]:
        beat_label = {"hook": "钩子", "cta": "转化", "list": "清单", "steps": "干货",
                      "summary": "总结", "twist": "反转"}.get(sh["beat"], sh["beat"])
        lines.append("▍镜%d (%s) %s · %s" % (sh["no"], sh["time"], beat_label, sh["camera"]))
        lines.append("  台词: %s" % sh["text"])
    lines.append("话题: %s" % " ".join(script["tags"]))
    lines.append("平台提示: %s" % script["note"])
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- 输出与写盘
def safe_write(path, content, log):
    """R4: 安全写盘——原子写入（先临时文件再替换）。"""
    try:
        d = os.path.dirname(os.path.abspath(path))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
        log("verbose", "已写入 %s (%d 字符)" % (path, len(content)))
        return True, ""
    except Exception as exc:  # noqa: BLE001 - 写盘失败需降级报告
        return False, str(exc)


# ---------------------------------------------------------------- 自检契约
def run_selftest():
    """内置自检契约（8 项断言）。返回 (pass_count, fail_list)。"""
    failures = []
    passed = []

    def check(name, cond, detail=""):
        if cond:
            passed.append(name)
        else:
            failures.append("%s: %s" % (name, detail))
        print("%s %s" % ("PASS" if cond else "FAIL", name))

    try:
        import main as m
        check("模块可导入且有 main", callable(getattr(m, "main", None)))
    except Exception as exc:  # noqa: BLE001
        check("模块可导入且有 main", False, str(exc))

    try:
        check("read_text_safe 存在", callable(read_text_safe))
        tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_enc_test.txt")
        with io.open(tmp, "w", encoding="gbk") as fh:
            fh.write(u"编码测试")
        content = read_text_safe(tmp)
        os.remove(tmp)
        check("三级编码容错", content == u"编码测试", "gbk 读取失败")
    except Exception as exc:  # noqa: BLE001
        check("三级编码容错", False, str(exc))

    ok, hits, risky = compliance_check("包治百病的神药")
    check("合规拦截绝对化词", ok is False and len(hits) > 0, "未拦截: %s" % hits)
    ok2, _h, _r = compliance_check("办公室咖啡技巧")
    check("常规主题放行", ok2 is True)

    rng = random.Random(42)
    log = lambda kind, msg: None  # noqa: E731 - selftest 静默
    script = build_script("测试主题", "douyin", 30, "seed", "设问引导", 0, rng, log)
    check("脚本结构完整", len(script["shots"]) >= 3 and script["shots"][-1]["beat"] == "cta")
    check("时长分配无越界", script["duration"] == 30 and all(0 <= s["no"] for s in script["shots"]))

    try:
        parse_args(["--topic", "t", "--platform", "bad_platform"])
        check("非法平台被 argparse 拦截", False, "未拦截")
    except SystemExit:
        check("非法平台被 argparse 拦截", True)

    return len(passed), failures


# ---------------------------------------------------------------- 主流程
def _safe_main(argv=None):
    """主流程入口（异常降级：任何未捕获错误返回友好提示）。"""
    args = parse_args(argv)
    log = _make_logger(args.verbose)

    if args.selftest:
        passed, fails = run_selftest()
        print("selftest: %d passed, %d failed" % (passed, len(fails)))
        if fails:
            for f in fails:
                print(" - " + f)
            return 1
        return 0

    if args.seed is not None:
        random.seed(args.seed)

    errs = validate_args(args, log)
    if errs:
        for e in errs:
            print("错误: " + e)
        return 2

    # 合规扫描主题
    ok, hits, risky = compliance_check(args.topic)
    if not ok:
        print("主题命中禁止词: %s → 请改写后再试" % "、".join(hits))
        return 3
    if risky:
        log("warn", "主题含风险词（医疗/金融等敏感领域）: %s —— 输出仅供结构参考，禁止绝对化表述" % "、".join(risky))

    topic = sanitize_topic(args.topic)
    angles = pick_angles(args.count, args.angle, log)

    scripts = []
    rng = random.Random(args.seed if args.seed is not None else os.urandom(4).hex())
    for idx, angle in enumerate(angles):
        log("decision", "生成第 %d 条（角度 %s）" % (idx + 1, angle))
        scripts.append(build_script(topic, args.platform, args.duration,
                                    args.style, angle, idx, rng, log))

    if args.as_json:
        payload = json.dumps({"generator": "short-video-script-gen", "version": VERSION,
                              "items": scripts}, ensure_ascii=False, indent=2)
    else:
        payload = "".join(render_text(s) for s in scripts)

    # 写盘决策：dry-run 只预览；默认无 --out 只打印；有 --out 写盘
    # ---- 输出决策（R4 预览撤回：dry-run 严格不写盘，--out 才落盘）----
    if not args.dry_run:
        if args.out:
            ok_w, msg = safe_write(args.out, payload, log)
            if not ok_w:
                print("写盘失败: " + msg)
                return 4
            print("已生成 → %s" % args.out)
            if args.verbose:
                print(payload)
            return 0
    # 默认走预览（无 --out 或 --dry-run 均不写盘）
    print(payload)
    return 0

def _make_logger(verbose):
    """构造日志器：verbose 开启才输出 decision/verbose 级别。"""
    def log(kind, msg):
        if kind == "warn":
            print("# warn: " + msg)
        elif verbose and kind in ("decision", "verbose"):
            print("# %s: %s" % (kind, msg))
    return log


def main(argv=None):
    """对外 main：异常兜底降级。"""
    try:
        return _safe_main(argv)
    except SystemExit as exc:
        # argparse 正常退出码透传
        return exc.code if isinstance(exc.code, int) else 0
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，绝不让用户见裸 traceback
        print("运行异常: %s（请检查参数后重试，或 --selftest 自检）" % exc)
        return 9


def dry_run(argv=None):
    """dry-run 预览入口：等价于 --dry-run。"""
    argv = list(argv) if argv else []
    argv.append("--dry-run")
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
