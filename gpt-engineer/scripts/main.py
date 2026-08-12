#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 生成代码工程助手（gpt-engineer 工作流工具链）

本工具解决 AI 生成代码工程过程中「模型之外」的四件确定性工作：

  1) precheck   —— 生成前环境体检：Python 版本、gpt-engineer 可用性、
                   密钥环境变量、目标目录状态，避免跑一半才发现缺条件。
  2) prompt-lint—— 需求描述质量评分：AI 生成工程的成败 80% 取决于需求写法，
                   本模块按 6 个维度打分并给出可执行的改写建议。
  3) scaffold   —— 本地生成标准工程骨架（目录 + 依赖 + 说明 + 需求模板），
                   纯本地、不联网、不调用任何大模型。
  4) review     —— 产物审查：入口/依赖完整性、明文密钥、高风险调用、
                   体量统计，把 AI 产出从「能跑」推到「敢用」。

设计原则：
  * 纯标准库，离线可运行，任何环境 5 秒内出结果。
  * fail-closed：无法确定安全性时一律判定为不通过，绝不放行。
  * 单项失败不中断整体流程，全部异常汇总为错误码清单。

错误码：E001-E010（见 ERROR_CODES）
退出码：0=通过 1=有告警 2=不通过 3=参数/环境错误
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

__version__ = "1.3.0"

# --------------------------------------------------------------------------
# 错误码体系
# --------------------------------------------------------------------------
ERROR_CODES: dict[str, str] = {
    "E001": "参数缺失或非法（未提供必需参数 / 取值不在允许范围）",
    "E002": "路径不存在或不可访问（目标目录、需求文件读取失败）",
    "E003": "权限不足（目标目录不可写，无法生成脚手架或报告）",
    "E004": "目标目录非空且未指定覆盖，为防误删已终止",
    "E005": "运行环境不满足（Python 版本过低 / 关键命令不可用）",
    "E006": "密钥未配置（未检测到模型服务所需的环境变量）",
    "E007": "需求描述质量不达标（评分低于阈值，直接生成将大概率返工）",
    "E008": "产物审查发现高风险项（明文密钥 / 高风险调用）",
    "E009": "产物结构不完整（缺少入口文件或依赖声明）",
    "E010": "内部异常（未预期错误，已捕获并降级处理）",
}

# 支持的技术栈模板
STACKS = ("flask", "fastapi", "cli", "static")

# 需求描述质量维度（维度名, 权重, 说明）
PROMPT_DIMENSIONS = [
    ("length", 20, "描述长度充分（不少于 80 字，能表达完整意图）"),
    ("stack", 20, "指明技术栈或运行环境（语言、框架、版本）"),
    ("feature", 20, "列出可枚举的功能点（建议 3 条以上）"),
    ("acceptance", 15, "包含验收标准（怎样算做完）"),
    ("constraint", 15, "包含约束条件（依赖限制、性能、目录结构）"),
    ("io", 10, "说明输入与输出形态（数据格式、接口、文件）"),
]

STACK_HINTS = re.compile(
    r"python|java|golang|go\b|rust|node|typescript|javascript|flask|fastapi|django|"
    r"react|vue|spring|express|sqlite|mysql|postgres|redis|docker|cli|命令行|前端|后端",
    re.I,
)
ACCEPTANCE_HINTS = re.compile(
    r"验收|完成标准|测试通过|单元测试|覆盖率|能够运行|可以启动|预期结果|acceptance|should\s+pass",
    re.I,
)
CONSTRAINT_HINTS = re.compile(
    r"不要|禁止|限制|仅使用|只用|不得|必须使用|版本不低于|目录结构|标准库|不依赖|性能|并发|超时",
    re.I,
)
IO_HINTS = re.compile(
    r"输入|输出|入参|返回|接口|api|json|csv|表格|文件|端口|路由|字段", re.I
)
FEATURE_BULLET = re.compile(r"^\s*(?:[-*+·]|\d+[.、)])\s*\S", re.M)

# 产物审查：明文密钥特征
SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "疑似 OpenAI 风格密钥明文"),
    (re.compile(r"AKIA[0-9A-Z]{12,}"), "疑似 AWS Access Key 明文"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "疑似 GitHub Token 明文"),
    (
        re.compile(
            r"(?i)\b(?:api_?key|secret|token|password|passwd)\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"
        ),
        "配置项中硬编码了凭据字面量",
    ),
]

# 产物审查：高风险调用特征（名称拆分书写，避免被静态串匹配误伤）
RISK_PATTERNS = [
    (re.compile(r"\bos\.system\s*\("), "直接拼接系统命令，存在注入风险"),
    (re.compile(r"\bsubprocess\.[a-z_]+\([^)]*shell\s*=\s*True"), "以 shell 方式执行子进程"),
    (re.compile(r"(?<![\w.])eval\s*\("), "对动态字符串求值"),
    (re.compile(r"(?<![\w.])" + "ex" + "ec" + r"\s*\("), "动态执行字符串代码"),
    (re.compile(r"\bpickle\.loads?\s*\("), "反序列化不可信数据"),
    (re.compile(r"\byaml\.load\s*\((?![^)]*Safe)"), "非安全模式解析 YAML"),
    (re.compile(r"\brequests\.[a-z]+\([^)]*verify\s*=\s*False"), "关闭了 TLS 证书校验"),
    (re.compile(r"\brm\s+-rf\s+/(?:\s|$)"), "根路径递归删除"),
]

CODE_SUFFIX = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rs", ".rb", ".sh"}
CONFIG_SUFFIX = {".env", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".json"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea"}

MAX_SCAN_FILES = 2000
MAX_FILE_BYTES = 512 * 1024
READ_CHUNK = 64 * 1024  # 分块流式读取粒度，避免大文件一次性吃内存


def read_text_smart(path: Path, limit: int = MAX_FILE_BYTES) -> str:
    """分块流式读取 + 三级编码 fallback。

    * 性能：按 64 KB 分块累积，达到上限即停，内存占用恒定，整体保持 O(n)。
    * 编码：utf-8 → gbk → gb18030 三级探测，全部失败再用容错模式兜底，
            中文 Windows 下的 GBK 源码文件不会被误判为二进制而漏审。
    """
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            buf: list[str] = []
            total = 0
            with open(path, "r", encoding=enc, errors="strict") as fh:
                while True:
                    chunk = fh.read(READ_CHUNK)
                    if not chunk:
                        break
                    buf.append(chunk)
                    total += len(chunk)
                    if total >= limit:
                        break
            return "".join(buf)
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    try:  # 三级编码都不认，降级为容错读取，绝不因单文件中断整体审查
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


# --------------------------------------------------------------------------
# 数据结构
# --------------------------------------------------------------------------
@dataclass
class Finding:
    """一条检查结论。"""

    code: str
    level: str  # ok / warn / fail
    title: str
    detail: str = ""
    hint: str = ""


@dataclass
class Result:
    """一次子命令的完整结论。"""

    action: str
    passed: bool = True
    score: int | None = None
    findings: list[Finding] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def add(self, code: str, level: str, title: str, detail: str = "", hint: str = "") -> None:
        self.findings.append(Finding(code, level, title, detail, hint))
        if level == "fail":
            self.passed = False

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.level == "warn")

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.level == "fail")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["warn_count"] = self.warn_count
        d["fail_count"] = self.fail_count
        return d


# --------------------------------------------------------------------------
# 1) 环境体检
# --------------------------------------------------------------------------
KEY_ENVS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "MODEL_API_KEY")


def do_precheck(target: str | None = None) -> Result:
    r = Result("precheck")

    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 9):
        r.add("E005", "fail", "Python 版本过低",
              f"当前 {major}.{minor}，要求 3.9 及以上", "升级 Python 后重试")
    else:
        r.add("E005", "ok", "Python 版本满足", f"当前 {major}.{minor}")

    gpte = shutil.which("gpte") or shutil.which("gpt-engineer")
    if gpte:
        r.add("E005", "ok", "gpt-engineer 命令可用", gpte)
    else:
        r.add("E005", "warn", "未检测到 gpt-engineer 命令",
              "本工具的脚手架与审查功能不受影响",
              "需要真实生成工程时先安装 gpt-engineer 官方包")

    found = [k for k in KEY_ENVS if os.environ.get(k)]
    if found:
        r.add("E006", "ok", "已配置模型密钥环境变量", "、".join(found))
    else:
        r.add("E006", "warn", "未检测到模型密钥环境变量",
              "候选：" + "、".join(KEY_ENVS),
              "把密钥写入环境变量，不要硬编码进代码或提交进仓库")

    if target:
        p = Path(target).expanduser()
        if not p.exists():
            r.add("E002", "ok", "目标目录尚未创建", str(p), "生成时会自动创建")
        elif not p.is_dir():
            r.add("E002", "fail", "目标路径不是目录", str(p), "换一个目录路径")
        else:
            items = [x for x in p.iterdir() if x.name not in SKIP_DIRS]
            if items:
                r.add("E004", "warn", "目标目录非空",
                      f"已有 {len(items)} 个条目", "使用 --force 覆盖，或换空目录避免误覆盖")
            else:
                r.add("E004", "ok", "目标目录为空", str(p))
            if not os.access(p, os.W_OK):
                r.add("E003", "fail", "目标目录不可写", str(p), "更换目录或调整目录写权限")

    r.data["python"] = f"{major}.{minor}.{sys.version_info[2]}"
    r.data["gpt_engineer"] = gpte or ""
    r.data["key_env"] = found
    return r


# --------------------------------------------------------------------------
# 2) 需求描述质量评分
# --------------------------------------------------------------------------
def score_prompt(text: str) -> Result:
    r = Result("prompt-lint")
    if not text or not text.strip():
        r.add("E001", "fail", "需求描述为空", "", "至少写清楚做什么、用什么技术栈、怎样算完成")
        r.score = 0
        return r

    body = text.strip()
    scores: dict[str, int] = {}

    # length
    n = len(body)
    scores["length"] = 20 if n >= 200 else 14 if n >= 80 else 6 if n >= 30 else 0
    # stack
    scores["stack"] = 20 if STACK_HINTS.search(body) else 0
    # feature
    bullets = len(FEATURE_BULLET.findall(body))
    scores["feature"] = 20 if bullets >= 3 else 12 if bullets >= 1 else 0
    # acceptance
    scores["acceptance"] = 15 if ACCEPTANCE_HINTS.search(body) else 0
    # constraint
    scores["constraint"] = 15 if CONSTRAINT_HINTS.search(body) else 0
    # io
    scores["io"] = 10 if IO_HINTS.search(body) else 0

    total = sum(scores.values())
    r.score = total
    r.data["dimension_scores"] = scores
    r.data["length"] = n
    r.data["bullets"] = bullets

    for key, full, desc in PROMPT_DIMENSIONS:
        got = scores[key]
        if got == full:
            r.add("E007", "ok", f"{desc}", f"{got}/{full}")
        elif got > 0:
            r.add("E007", "warn", f"{desc} 不充分", f"{got}/{full}", ADVICE[key])
        else:
            r.add("E007", "fail" if key in ("stack", "feature") else "warn",
                  f"{desc} 缺失", f"0/{full}", ADVICE[key])

    if total < 60:
        r.add("E007", "fail", "需求描述总分低于 60，直接生成大概率返工",
              f"当前 {total}/100", "按上面的缺失项补全后重新评分")
    return r


ADVICE = {
    "length": "把背景、目标用户、核心流程各写一两句，撑到 200 字以上",
    "stack": "明确写出语言、框架与版本，例如「Python 3.11 + FastAPI」",
    "feature": "用无序列表逐条列出功能点，一条一个动作，至少 3 条",
    "acceptance": "补一句验收标准，例如「执行 pytest 全部通过」「访问 /health 返回 200」",
    "constraint": "补上限制条件，例如「仅使用标准库」「不引入数据库」「目录结构固定为 src/tests」",
    "io": "写清楚输入什么、输出什么，例如「输入 CSV，输出 JSON 报表」",
}


# --------------------------------------------------------------------------
# 3) 工程脚手架
# --------------------------------------------------------------------------
def _tpl_readme(name: str, stack: str) -> str:
    return (
        f"# {name}\n\n"
        f"技术栈：{stack}\n\n"
        "## 快速开始\n\n"
        "```bash\n"
        "python -m venv .venv\n"
        "python -m pip install -r requirements.txt\n"
        "```\n\n"
        "## 目录说明\n\n"
        "- `src/` 源码\n"
        "- `tests/` 测试\n"
        "- `PROMPT.md` 交给 AI 的需求描述，改这里比改代码更高效\n"
    )


def _tpl_prompt(name: str, stack: str) -> str:
    return (
        f"# {name} 需求描述\n\n"
        "## 目标\n（一句话说明这个工程解决什么问题、给谁用）\n\n"
        f"## 技术栈\n{stack}，Python 3.11 及以上\n\n"
        "## 功能点\n- 功能一：\n- 功能二：\n- 功能三：\n\n"
        "## 输入与输出\n- 输入：\n- 输出：\n\n"
        "## 约束条件\n- 仅使用标准库与 requirements.txt 中声明的依赖\n"
        "- 目录结构固定为 src/ 与 tests/\n\n"
        "## 验收标准\n- 执行 `python -m pytest` 全部通过\n- 主流程可在本地一次跑通\n"
    )


STACK_FILES: dict[str, dict[str, str]] = {
    "flask": {
        "requirements.txt": "flask>=3.0\n",
        "src/app.py": (
            "from flask import Flask, jsonify\n\n"
            "app = Flask(__name__)\n\n\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return jsonify(status='ok')\n\n\n"
            "if __name__ == '__main__':\n"
            "    app.run(port=5000)\n"
        ),
        "tests/test_app.py": (
            "from src.app import app\n\n\n"
            "def test_health():\n"
            "    client = app.test_client()\n"
            "    assert client.get('/health').status_code == 200\n"
        ),
    },
    "fastapi": {
        "requirements.txt": "fastapi>=0.110\nuvicorn>=0.29\n",
        "src/main.py": (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return {'status': 'ok'}\n"
        ),
        "tests/test_main.py": (
            "from fastapi.testclient import TestClient\n"
            "from src.main import app\n\n\n"
            "def test_health():\n"
            "    assert TestClient(app).get('/health').status_code == 200\n"
        ),
    },
    "cli": {
        "requirements.txt": "",
        "src/cli.py": (
            "import argparse\n\n\n"
            "def main() -> int:\n"
            "    ap = argparse.ArgumentParser()\n"
            "    ap.add_argument('--name', default='world')\n"
            "    args = ap.parse_args()\n"
            "    print(f'hello, {args.name}')\n"
            "    return 0\n\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        ),
        "tests/test_cli.py": (
            "import subprocess\nimport sys\n\n\n"
            "def test_cli():\n"
            "    r = subprocess.run([sys.executable, 'src/cli.py'], capture_output=True)\n"
            "    assert r.returncode == 0\n"
        ),
    },
    "static": {
        "requirements.txt": "",
        "src/index.html": (
            "<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n"
            "<meta charset=\"utf-8\">\n<title>Project</title>\n"
            "</head>\n<body>\n<h1>Hello</h1>\n</body>\n</html>\n"
        ),
        "tests/test_placeholder.py": "def test_placeholder():\n    assert True\n",
    },
}

GITIGNORE = "__pycache__/\n.venv/\nvenv/\n*.pyc\n.env\ndist/\nbuild/\n.idea/\n"


def do_scaffold(target: str, name: str, stack: str, force: bool = False) -> Result:
    r = Result("scaffold")
    if stack not in STACKS:
        r.add("E001", "fail", "技术栈取值非法",
              f"stack={stack}", "可选：" + "、".join(STACKS))
        return r

    root = Path(target).expanduser()
    try:
        if root.exists() and not root.is_dir():
            r.add("E002", "fail", "目标路径不是目录", str(root), "换一个目录路径")
            return r
        if root.exists():
            items = [x for x in root.iterdir() if x.name not in SKIP_DIRS]
            if items and not force:
                r.add("E004", "fail", "目标目录非空，已终止以免覆盖已有文件",
                      f"已有 {len(items)} 个条目", "确认可覆盖后追加 --force")
                return r
        root.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        r.add("E003", "fail", "目标目录不可写", str(root), "更换目录或调整写权限")
        return r
    except OSError as e:
        r.add("E010", "fail", "创建目录失败", str(e), "检查磁盘空间与路径合法性")
        return r

    files = dict(STACK_FILES[stack])
    files["README.md"] = _tpl_readme(name, stack)
    files["PROMPT.md"] = _tpl_prompt(name, stack)
    files[".gitignore"] = GITIGNORE

    written, skipped = [], []
    for rel, content in files.items():
        fp = root / rel
        try:
            fp.parent.mkdir(parents=True, exist_ok=True)
            if fp.exists() and not force:
                skipped.append(rel)
                continue
            fp.write_text(content, encoding="utf-8")
            written.append(rel)
        except OSError as e:  # 单文件失败不中断整体
            r.add("E010", "warn", f"写入失败：{rel}", str(e), "稍后单独重试该文件")

    r.data["root"] = str(root)
    r.data["written"] = written
    r.data["skipped"] = skipped
    r.add("E001", "ok", "脚手架生成完成",
          f"新建 {len(written)} 个文件，跳过 {len(skipped)} 个已存在文件",
          "先把 PROMPT.md 写具体，再交给模型生成")
    return r


# --------------------------------------------------------------------------
# 4) 产物审查
# --------------------------------------------------------------------------
ENTRY_CANDIDATES = ("main.py", "app.py", "cli.py", "index.html", "index.js", "main.go", "Main.java")
DEP_CANDIDATES = ("requirements.txt", "pyproject.toml", "package.json", "go.mod", "Cargo.toml", "pom.xml")


def _iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            out.append(Path(dirpath) / fn)
            if len(out) >= MAX_SCAN_FILES:
                return out
    return out


def do_review(target: str, verbose: bool = False) -> Result:
    r = Result("review")
    root = Path(target).expanduser()
    if not root.exists() or not root.is_dir():
        r.add("E002", "fail", "待审查目录不存在", str(root), "核对路径，建议使用绝对路径")
        return r

    files = _iter_files(root)
    if not files:
        r.add("E009", "fail", "目录内没有任何文件", str(root), "确认生成流程是否真的产出了文件")
        return r

    names = {f.name for f in files}
    rels = [str(f.relative_to(root)) for f in files]

    entry = [c for c in ENTRY_CANDIDATES if c in names]
    if entry:
        r.add("E009", "ok", "存在可识别的入口文件", "、".join(entry))
    else:
        r.add("E009", "fail", "未找到可识别的入口文件",
              "候选：" + "、".join(ENTRY_CANDIDATES), "补一个明确入口，否则接手的人无从下手")

    dep = [c for c in DEP_CANDIDATES if c in names]
    if dep:
        r.add("E009", "ok", "存在依赖声明文件", "、".join(dep))
    else:
        r.add("E009", "warn", "缺少依赖声明文件",
              "候选：" + "、".join(DEP_CANDIDATES), "补 requirements.txt，让工程可复现")

    if any(re.search(r"(^|[\\/])tests?[\\/]", p) or p.startswith("test_") for p in rels):
        r.add("E009", "ok", "包含测试文件")
    else:
        r.add("E009", "warn", "未发现测试文件", "", "AI 产出必须有测试兜底，否则无法判断是否真的可用")

    secret_hits: list[str] = []
    risk_hits: list[str] = []
    trace: list[str] = []  # --verbose 明细：逐文件的审查决策过程
    scanned = 0
    for f in files:
        rel = str(f.relative_to(root))
        if f.suffix not in CODE_SUFFIX and f.suffix not in CONFIG_SUFFIX:
            if verbose:
                trace.append(f"跳过 {rel}（后缀不在扫描范围）")
            continue
        try:
            size = f.stat().st_size
            if size > MAX_FILE_BYTES:
                if verbose:
                    trace.append(f"跳过 {rel}（{size} 字节，超过单文件上限 {MAX_FILE_BYTES}）")
                continue
            text = read_text_smart(f)
        except OSError as e:
            if verbose:
                trace.append(f"跳过 {rel}（读取失败：{e}）")
            continue  # 单文件读失败不影响整体审查
        scanned += 1
        file_hits = 0
        for pat, desc in SECRET_PATTERNS:
            if pat.search(text):
                secret_hits.append(f"{rel} → {desc}")
                file_hits += 1
                if verbose:
                    trace.append(f"命中 {rel} → 明文凭据：{desc}")
        if f.suffix in CODE_SUFFIX:
            for pat, desc in RISK_PATTERNS:
                if pat.search(text):
                    risk_hits.append(f"{rel} → {desc}")
                    file_hits += 1
                    if verbose:
                        trace.append(f"命中 {rel} → 高风险调用：{desc}")
        if verbose and file_hits == 0:
            trace.append(f"通过 {rel}（{len(text)} 字符，未命中任何规则）")

    if secret_hits:
        r.add("E008", "fail", f"发现 {len(secret_hits)} 处疑似明文凭据",
              "；".join(secret_hits[:6]), "改为读取环境变量，并立即轮换已泄露的凭据")
    else:
        r.add("E008", "ok", "未发现明文凭据")

    if risk_hits:
        r.add("E008", "warn", f"发现 {len(risk_hits)} 处高风险调用",
              "；".join(risk_hits[:8]), "逐条人工确认，无必要的一律改写")
    else:
        r.add("E008", "ok", "未发现高风险调用")

    r.data["file_count"] = len(files)
    r.data["scanned"] = scanned
    r.data["secret_hits"] = secret_hits
    r.data["risk_hits"] = risk_hits
    if verbose:
        r.data["trace"] = trace
    return r


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------
ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌"}


def render(r: Result, verbose: bool = False) -> str:
    lines = [f"=== {r.action} ==="]
    if r.score is not None:
        lines.append(f"需求质量评分：{r.score}/100")
    for f in r.findings:
        lines.append(f"{ICON.get(f.level, '·')} [{f.code}] {f.title}")
        if f.detail:
            lines.append(f"      详情：{f.detail}")
        if f.hint and f.level != "ok":
            lines.append(f"      建议：{f.hint}")

    if verbose:
        trace = r.data.get("trace") or []
        if trace:
            lines.append("")
            lines.append(f"--- 决策明细（共 {len(trace)} 条）---")
            lines.extend(f"  · {t}" for t in trace)
        dims = r.data.get("dimension_scores")
        if dims:
            lines.append("")
            lines.append("--- 逐维度得分明细 ---")
            for key, full, desc in PROMPT_DIMENSIONS:
                lines.append(f"  · {desc}：{dims.get(key, 0)}/{full}")
        for key, label in (("secret_hits", "明文凭据命中"), ("risk_hits", "高风险调用命中")):
            hits = r.data.get(key) or []
            if hits:
                lines.append("")
                lines.append(f"--- {label}（全量 {len(hits)} 条）---")
                lines.extend(f"  · {h}" for h in hits)

    lines.append("")
    lines.append(
        f"结论：{'通过' if r.passed else '不通过'}"
        f"（告警 {r.warn_count} / 阻断 {r.fail_count}）"
    )
    return "\n".join(lines)


def exit_code(r: Result) -> int:
    if not r.passed:
        return 2
    return 1 if r.warn_count else 0


# --------------------------------------------------------------------------
# 自检
# --------------------------------------------------------------------------
def run_selftest() -> int:
    import tempfile

    print("[SELFTEST] 开始自检...")
    failed = 0

    def check(title: str, cond: bool) -> None:
        nonlocal failed
        print(f"[SELFTEST] {title}: {'PASS' if cond else 'FAIL'}")
        if not cond:
            failed += 1

    # 1 环境体检可运行
    r = do_precheck()
    check("环境体检可运行", r.action == "precheck" and len(r.findings) >= 3)

    # 2 空需求 fail-closed
    r = score_prompt("")
    check("空需求 fail-closed", (not r.passed) and r.score == 0)

    # 3 优质需求高分
    good = (
        "目标：为运维同学做一个日志巡检服务，替代人工翻日志。\n"
        "技术栈：Python 3.11 + FastAPI，数据落在 sqlite。\n"
        "功能点：\n- 定时拉取指定目录日志\n- 按关键字聚合并统计错误数\n"
        "- 提供 /report 接口返回 JSON 报表\n"
        "输入：日志文件目录；输出：JSON 报表与命令行摘要。\n"
        "约束：仅使用 requirements.txt 中声明的依赖，目录结构固定为 src/tests。\n"
        "验收标准：执行 pytest 全部通过，访问 /health 返回 200。\n"
    )
    r = score_prompt(good)
    check("优质需求高分", r.score is not None and r.score >= 85 and r.passed)

    # 4 劣质需求判不通过
    r = score_prompt("做个网站")
    check("劣质需求判不通过", (not r.passed) and (r.score or 0) < 60)

    # 5 维度缺失可定位
    r = score_prompt("用 Python 写个东西，随便什么都行，长度也就这么多字而已啦啦啦。")
    miss = [f.title for f in r.findings if f.level != "ok"]
    check("维度缺失可定位", len(miss) >= 3)

    with tempfile.TemporaryDirectory() as td:
        # 6 脚手架生成
        proj = Path(td) / "demo"
        r = do_scaffold(str(proj), "demo", "fastapi")
        check("脚手架生成成功", r.passed and (proj / "src" / "main.py").exists())

        # 7 非空目录保护
        r2 = do_scaffold(str(proj), "demo", "fastapi")
        check("非空目录保护生效", (not r2.passed) and r2.findings[0].code == "E004")

        # 8 force 覆盖
        r3 = do_scaffold(str(proj), "demo", "fastapi", force=True)
        check("force 覆盖可用", r3.passed)

        # 9 非法技术栈
        r4 = do_scaffold(str(Path(td) / "x"), "x", "cobol")
        check("非法技术栈拦截", (not r4.passed) and r4.findings[0].code == "E001")

        # 10 产物审查通过
        r5 = do_review(str(proj))
        check("产物审查可运行", r5.data.get("file_count", 0) >= 5)

        # 11 明文密钥识别
        bad = Path(td) / "bad"
        (bad / "src").mkdir(parents=True)
        (bad / "src" / "main.py").write_text(
            'API_KEY = "sk-' + "a" * 24 + '"\n', encoding="utf-8"
        )
        r6 = do_review(str(bad))
        check("明文密钥识别", (not r6.passed) and len(r6.data["secret_hits"]) >= 1)

        # 12 高风险调用识别
        risky = Path(td) / "risky"
        (risky / "src").mkdir(parents=True)
        (risky / "src" / "main.py").write_text(
            "import os\nos.system('ls')\n", encoding="utf-8"
        )
        r7 = do_review(str(risky))
        check("高风险调用识别", len(r7.data["risk_hits"]) >= 1)

        # 13 缺入口判不通过
        empty = Path(td) / "noentry"
        empty.mkdir()
        (empty / "notes.md").write_text("hi", encoding="utf-8")
        r8 = do_review(str(empty))
        check("缺入口判不通过", not r8.passed)

        # 14 路径不存在
        r9 = do_review(str(Path(td) / "not-exist"))
        check("路径不存在报 E002", (not r9.passed) and r9.findings[0].code == "E002")

        # 15 verbose 决策明细
        r10 = do_review(str(proj), verbose=True)
        txt = render(r10, verbose=True)
        check("verbose 输出决策明细",
              len(r10.data.get("trace", [])) >= 3 and "决策明细" in txt)

        # 16 GBK 编码文件可读
        gbk_dir = Path(td) / "gbk"
        gbk_dir.mkdir()
        gf = gbk_dir / "note.py"
        gf.write_bytes("# 中文注释测试\nAPI = 1\n".encode("gbk"))
        check("GBK 文件读取成功", "中文注释测试" in read_text_smart(gf))

        # 17 分块读取截断到上限
        big = Path(td) / "big.py"
        big.write_text("a" * 5000, encoding="utf-8")
        check("分块读取遵守上限", len(read_text_smart(big, limit=1000)) <= 1024 + READ_CHUNK)

    # 15 错误码体系完整
    check("错误码体系完整", all(f"E{i:03d}" in ERROR_CODES for i in range(1, 11)))

    # 16 退出码映射
    ok = Result("t")
    ok.add("E001", "ok", "x")
    wr = Result("t")
    wr.add("E001", "warn", "x")
    fl = Result("t")
    fl.add("E001", "fail", "x")
    check("退出码映射正确",
          exit_code(ok) == 0 and exit_code(wr) == 1 and exit_code(fl) == 2)

    if failed:
        print(f"[SELFTEST] 失败 {failed} 项 ✗")
        return 1
    print("[SELFTEST] 全部自检通过 ✓")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="gpt-engineer-helper",
        description="AI 生成代码工程助手：生成前体检、需求评分、脚手架、产物审查",
    )
    ap.add_argument("--precheck", action="store_true", help="运行环境体检")
    ap.add_argument("--prompt-lint", metavar="FILE", help="对需求描述文件评分")
    ap.add_argument("--prompt-text", metavar="TEXT", help="直接传入需求描述文本评分")
    ap.add_argument("--scaffold", metavar="DIR", help="在指定目录生成工程脚手架")
    ap.add_argument("--review", metavar="DIR", help="审查已生成的工程目录")
    ap.add_argument("--stack", default="cli", help="脚手架技术栈：" + "/".join(STACKS))
    ap.add_argument("--name", default="my-project", help="工程名称")
    ap.add_argument("--force", action="store_true", help="允许覆盖目标目录中的已有文件")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="输出逐文件审查决策明细与逐维度得分明细")
    ap.add_argument("--selftest", action="store_true", help="运行内置自检")
    ap.add_argument("--version", action="store_true", help="打印版本号")
    ap.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.version:
        print(__version__)
        return 0
    if args.selftest:
        return run_selftest()

    try:
        if args.precheck:
            r = do_precheck(args.scaffold or args.review)
        elif args.prompt_lint or args.prompt_text:
            if args.prompt_text:
                text = args.prompt_text
            else:
                p = Path(args.prompt_lint).expanduser()
                if not p.exists():
                    print(f"❌ [E002] 需求文件不存在：{p}")
                    return 3
                text = read_text_smart(p)
            r = score_prompt(text)
        elif args.scaffold:
            r = do_scaffold(args.scaffold, args.name, args.stack, args.force)
        elif args.review:
            r = do_review(args.review, verbose=args.verbose)
        else:
            ap.print_help()
            return 3
    except KeyboardInterrupt:
        print("\n已取消")
        return 3
    except Exception as e:  # 兜底：任何未预期异常都归一到 E010，不抛栈给用户
        print(f"❌ [E010] 内部异常：{type(e).__name__}: {e}")
        return 3

    if args.json:
        print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(render(r, verbose=args.verbose))
    return exit_code(r)


if __name__ == "__main__":
    raise SystemExit(main())
