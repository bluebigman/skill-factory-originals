#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 超高速代码搜索（clean-room 独立实现）

本脚本依据功能规格独立实现，不参考任何既有代码。
仅使用 Python 标准库，无需第三方依赖。

功能概述：
- 递归搜索目录中的正则模式
- 自动忽略 .gitignore / .ignore / .rgignore 规则
- 支持文件类型过滤（-t/-T）
- 支持上下文输出（-C/-A/-B）
- 支持统计计数（-c/--count-matches）
- 支持文件列表输出（-l/-L）
- 支持多目录搜索
- 支持替换预览（--replace + --passthru）
- 支持编码指定（-E）
- 支持 JSON 结构化输出（--json）
- 内置自检模式（--selftest）

错误码说明：
E001 - 参数解析错误
E002 - 正则表达式编译失败
E003 - 搜索路径不存在或不可访问
E004 - 文件读取失败
E005 - 编码不支持
E006 - 文件类型过滤规则无效
E007 - 输出写入失败
E008 - 自检失败
E009 - 内部逻辑错误
E010 - 不支持的参数组合
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SearchOptions:
    """搜索选项集合"""
    pattern: str = ""
    paths: List[str] = field(default_factory=lambda: ["."])
    type_include: List[str] = field(default_factory=list)   # -t
    type_exclude: List[str] = field(default_factory=list)   # -T
    glob_exclude: List[str] = field(default_factory=list)   # -g '!...'
    glob_include: List[str] = field(default_factory=list)   # -g '...'
    context_before: int = 0
    context_after: int = 0
    context: int = 0
    files_with_matches: bool = False        # -l
    files_without_matches: bool = False     # -L
    count: bool = False                     # -c
    count_matches: bool = False             # --count-matches
    ignore_case: bool = False               # -i
    encoding: str = "utf-8"                 # -E
    json_output: bool = False               # --json
    replace: Optional[str] = None           # --replace
    passthru: bool = False                  # --passthru
    no_ignore: bool = False                 # --no-ignore
    hidden: bool = False                    # --hidden
    follow_links: bool = False              # -L
    binary: bool = False                    # -a
    line_number: bool = True                # -n / -N
    max_depth: Optional[int] = None         # --max-depth
    smart_case: bool = False                # -S


# ============================================================
# 忽略规则解析
# ============================================================

class IgnoreRules:
    """解析并应用 .gitignore / .ignore / .rgignore 规则"""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self.rules: List[Tuple[str, bool]] = []  # (pattern, is_negation)
        self._load_ignore_files()

    def _load_ignore_files(self) -> None:
        """从根目录加载各类忽略文件"""
        for filename in [".gitignore", ".ignore", ".rgignore"]:
            ignore_path = self.root_dir / filename
            if ignore_path.is_file():
                self._parse_ignore_file(ignore_path)

    def _parse_ignore_file(self, path: Path) -> None:
        """解析单个忽略文件"""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # 处理取反规则
                    is_negation = False
                    if line.startswith("!"):
                        is_negation = True
                        line = line[1:]
                    # 去除结尾的转义斜杠
                    if line.endswith("\\"):
                        line = line[:-1]
                    self.rules.append((line, is_negation))
        except (OSError, IOError):
            pass  # 忽略文件读取失败

    def is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """
        判断相对路径是否被忽略
        rel_path: 相对于根目录的路径，使用 / 分隔
        """
        # 默认忽略隐藏文件和常见目录
        parts = rel_path.split("/")
        for part in parts:
            if part.startswith(".") and part not in (".", ".."):
                return True

        # 应用规则（最后一个匹配的规则生效）
        ignored = False
        for pattern, is_negation in self.rules:
            if self._match_pattern(pattern, rel_path, is_dir):
                ignored = not is_negation
        return ignored

    def _match_pattern(self, pattern: str, rel_path: str, is_dir: bool) -> bool:
        """匹配单个忽略模式"""
        # 处理目录模式（结尾带 /）
        dir_only = pattern.endswith("/")
        if dir_only:
            pattern = pattern.rstrip("/")
            # 目录模式匹配路径前缀
            if rel_path == pattern or rel_path.startswith(pattern + "/"):
                return True
            return False

        # 处理锚定模式（开头带 /）
        anchored = pattern.startswith("/")
        if anchored:
            pattern = pattern.lstrip("/")
            # 锚定模式匹配根目录下的路径
            return rel_path == pattern or rel_path.startswith(pattern + "/")

        # 处理包含 / 的模式（相对路径）
        if "/" in pattern:
            # 匹配完整路径或任意父目录下的路径
            return fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, f"**/{pattern}")

        # 简单文件名模式（匹配任意层级）
        # 检查路径的每一部分
        for part in rel_path.split("/"):
            if fnmatch.fnmatch(part, pattern):
                return True
        # 也检查整个路径
        return fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, f"**/{pattern}")


# ============================================================
# 文件类型映射
# ============================================================

# 常见文件类型扩展名映射
FILE_TYPE_MAP: Dict[str, Set[str]] = {
    "py": {".py", ".pyi", ".pyw"},
    "js": {".js", ".jsx", ".mjs", ".cjs"},
    "ts": {".ts", ".tsx"},
    "java": {".java"},
    "c": {".c", ".h"},
    "cpp": {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"},
    "cs": {".cs"},
    "go": {".go"},
    "rs": {".rs"},
    "rb": {".rb"},
    "php": {".php"},
    "swift": {".swift"},
    "kt": {".kt", ".kts"},
    "scala": {".scala"},
    "sh": {".sh", ".bash", ".zsh"},
    "html": {".html", ".htm"},
    "css": {".css"},
    "scss": {".scss", ".sass"},
    "less": {".less"},
    "json": {".json"},
    "xml": {".xml"},
    "yaml": {".yaml", ".yml"},
    "toml": {".toml"},
    "ini": {".ini", ".cfg", ".conf"},
    "md": {".md", ".markdown"},
    "txt": {".txt"},
    "sql": {".sql"},
    "dockerfile": {"dockerfile", "dockerfile.*"},
    "makefile": {"makefile", "makefile.*"},
}


def get_extension_set(type_name: str) -> Optional[Set[str]]:
    """获取文件类型对应的扩展名集合"""
    type_name = type_name.lower()
    if type_name in FILE_TYPE_MAP:
        return FILE_TYPE_MAP[type_name]
    # 支持直接传扩展名，如 -t .py
    if type_name.startswith("."):
        return {type_name}
    return None


# ============================================================
# 核心搜索逻辑
# ============================================================

class SearchEngine:
    """核心搜索引擎"""

    def __init__(self, options: SearchOptions):
        self.options = options
        self.regex = None
        self.ignore_rules: List[IgnoreRules] = []
        self.error_code = "E000"
        self.error_message = ""

    def compile_regex(self) -> bool:
        """编译正则表达式"""
        try:
            flags = 0
            if self.options.ignore_case or self.options.smart_case:
                flags |= re.IGNORECASE
            self.regex = re.compile(self.options.pattern, flags)
            return True
        except re.error as e:
            self.error_code = "E002"
            self.error_message = f"正则表达式编译失败: {e}"
            return False

    def _should_process_file(self, file_path: Path, rel_path: str) -> bool:
        """判断文件是否应被处理"""
        # 检查文件类型过滤
        if self.options.type_include:
            ext = file_path.suffix.lower()
            file_name = file_path.name.lower()
            matched = False
            for t in self.options.type_include:
                ext_set = get_extension_set(t)
                if ext_set:
                    for e in ext_set:
                        if e.startswith(".") and ext == e:
                            matched = True
                            break
                        elif not e.startswith(".") and fnmatch.fnmatch(file_name, e):
                            matched = True
                            break
                if matched:
                    break
            if not matched:
                return False

        if self.options.type_exclude:
            ext = file_path.suffix.lower()
            file_name = file_path.name.lower()
            for t in self.options.type_exclude:
                ext_set = get_extension_set(t)
                if ext_set:
                    for e in ext_set:
                        if e.startswith(".") and ext == e:
                            return False
                        elif not e.startswith(".") and fnmatch.fnmatch(file_name, e):
                            return False

        # 检查 glob 排除规则
        for pattern in self.options.glob_exclude:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                return False

        # 检查 glob 包含规则（如果有）
        if self.options.glob_include:
            matched = False
            for pattern in self.options.glob_include:
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    matched = True
                    break
            if not matched:
                return False

        # 检查忽略规则
        if not self.options.no_ignore:
            for ignore in self.ignore_rules:
                if ignore.is_ignored(rel_path):
                    return False

        return True

    def _read_file(self, file_path: Path) -> Optional[List[str]]:
        """读取文件内容，返回行列表"""
        try:
            with open(file_path, "r", encoding=self.options.encoding, errors="replace") as f:
                return f.readlines()
        except UnicodeDecodeError:
            # 尝试 UTF-8 作为后备
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.readlines()
            except (OSError, IOError):
                self.error_code = "E004"
                self.error_message = f"文件读取失败: {file_path}"
                return None
        except (OSError, IOError):
            self.error_code = "E004"
            self.error_message = f"文件读取失败: {file_path}"
            return None

    def _is_binary(self, file_path: Path) -> bool:
        """检测文件是否为二进制文件"""
        if self.options.binary:
            return False
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return True
        except (OSError, IOError):
            pass
        return False

    def search_file(self, file_path: Path, root_dir: Path) -> Optional[Dict]:
        """
        在单个文件中搜索
        返回结果字典或 None
        """
        if self._is_binary(file_path):
            return None

        rel_path = file_path.relative_to(root_dir).as_posix()
        if not self._should_process_file(file_path, rel_path):
            return None

        lines = self._read_file(file_path)
        if lines is None:
            return None

        matches = []
        match_count = 0

        for i, line in enumerate(lines):
            line_content = line.rstrip("\n")
            if self.regex.search(line_content):
                match_count += 1
                matches.append({
                    "line_number": i + 1,
                    "line": line_content,
                    "match_start": self.regex.search(line_content).start(),
                    "match_end": self.regex.search(line_content).end(),
                })

        if self.options.files_without_matches:
            # -L 模式：只输出不包含匹配的文件
            if match_count == 0:
                return {"path": str(file_path), "matches": []}
            else:
                return None

        if self.options.files_with_matches:
            # -l 模式：只输出包含匹配的文件
            if match_count > 0:
                return {"path": str(file_path), "matches": []}
            else:
                return None

        if self.options.count:
            # -c 模式：输出每个文件的匹配行数
            return {"path": str(file_path), "count": match_count, "matches": []}

        if self.options.count_matches:
            # --count-matches 模式：输出总匹配次数
            total_matches = sum(self.regex.findall(line) for line in lines if self.regex.search(line))
            return {"path": str(file_path), "count": len(total_matches), "matches": []}

        # 默认模式：输出匹配行
        if match_count > 0:
            return {
                "path": str(file_path),
                "matches": matches,
                "context_before": self.options.context_before,
                "context_after": self.options.context_after,
                "lines": lines,
            }

        return None

    def search_directory(self, dir_path: Path) -> List[Dict]:
        """递归搜索目录"""
        results = []
        root_dir = dir_path.resolve()
        ignore = IgnoreRules(str(root_dir))
        self.ignore_rules.append(ignore)

        for current_root, dirs, files in os.walk(root_dir):
            # 应用忽略规则过滤目录
            filtered_dirs = []
            for d in dirs:
                rel_d = os.path.relpath(os.path.join(current_root, d), root_dir).replace(os.sep, "/")
                if self.options.hidden or not d.startswith("."):
                    if self.options.no_ignore or not ignore.is_ignored(rel_d, is_dir=True):
                        filtered_dirs.append(d)
            dirs[:] = filtered_dirs

            # 处理文件
            for file_name in files:
                file_path = Path(current_root) / file_name
                rel_f = os.path.relpath(file_path, root_dir).replace(os.sep, "/")
                if self.options.hidden or not file_name.startswith("."):
                    result = self.search_file(file_path, root_dir)
                    if result:
                        results.append(result)

        return results

    def run(self) -> List[Dict]:
        """执行搜索，返回结果列表"""
        if not self.compile_regex():
            return []

        all_results = []
        for path_str in self.options.paths:
            path = Path(path_str)
            if not path.exists():
                self.error_code = "E003"
                self.error_message = f"搜索路径不存在: {path_str}"
                continue

            if path.is_file():
                result = self.search_file(path, path.parent)
                if result:
                    all_results.append(result)
            elif path.is_dir():
                results = self.search_directory(path)
                all_results.extend(results)

        return all_results


# ============================================================
# 输出格式化
# ============================================================

class OutputFormatter:
    """结果输出格式化"""

    @staticmethod
    def format_plain(results: List[Dict], options: SearchOptions) -> str:
        """普通文本输出格式"""
        output_lines = []

        for result in results:
            path = result["path"]

            if options.files_with_matches or options.files_without_matches:
                output_lines.append(path)
                continue

            if options.count or options.count_matches:
                count = result.get("count", 0)
                output_lines.append(f"{path}:{count}")
                continue

            matches = result.get("matches", [])
            lines = result.get("lines", [])
            ctx_before = result.get("context_before", 0)
            ctx_after = result.get("context_after", 0)

            for match in matches:
                line_num = match["line_number"]
                line_content = match["line"]

                # 应用替换预览
                if options.replace:
                    line_content = options.regex.sub(options.replace, line_content)

                if options.line_number:
                    output_lines.append(f"{path}:{line_num}:{line_content}")
                else:
                    output_lines.append(f"{path}:{line_content}")

                # 上下文输出
                if ctx_before > 0 or ctx_after > 0:
                    start = max(0, line_num - 1 - ctx_before)
                    end = min(len(lines), line_num + ctx_after)
                    for i in range(start, line_num - 1):
                        output_lines.append(f"{path}-{i+1}-{lines[i].rstrip()}")
                    for i in range(line_num, end):
                        output_lines.append(f"{path}-{i+1}-{lines[i].rstrip()}")

        return "\n".join(output_lines)

    @staticmethod
    def format_json(results: List[Dict], options: SearchOptions) -> str:
        """JSON 输出格式"""
        json_results = []
        for result in results:
            item = {"path": result["path"]}
            if options.count or options.count_matches:
                item["count"] = result.get("count", 0)
            elif options.files_with_matches or options.files_without_matches:
                item["has_matches"] = len(result.get("matches", [])) > 0
            else:
                item["matches"] = result.get("matches", [])
            json_results.append(item)
        return json.dumps(json_results, ensure_ascii=False, indent=2)

    @staticmethod
    def format_passthru(results: List[Dict], options: SearchOptions) -> str:
        """替换预览输出格式"""
        output_lines = []
        for result in results:
            path = result["path"]
            lines = result.get("lines", [])
            matches = result.get("matches", [])

            # 收集匹配行号
            match_lines = set(m["line_number"] for m in matches)

            for i, line in enumerate(lines, 1):
                content = line.rstrip("\n")
                if i in match_lines and options.replace:
                    content = options.regex.sub(options.replace, content)
                output_lines.append(content)

        return "\n".join(output_lines)


# ============================================================
# 命令行解析
# ============================================================

def parse_args(argv: List[str]) -> Optional[SearchOptions]:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="超高速代码搜索 - 递归搜索目录中的正则模式",
        epilog="示例: python main.py 'def \\w+' -t py -C 2 ./src"
    )

    # 位置参数
    parser.add_argument("pattern", nargs="?", help="搜索的正则模式")
    parser.add_argument("paths", nargs="*", default=["."], help="搜索路径（默认为当前目录）")

    # 文件类型
    parser.add_argument("-t", "--type", action="append", dest="type_include", help="只搜索指定文件类型（如 py, js）")
    parser.add_argument("-T", "--type-not", action="append", dest="type_exclude", help="排除指定文件类型")

    # 忽略规则
    parser.add_argument("-g", "--glob", action="append", help="全局规则（!前缀表示排除）")
    parser.add_argument("--no-ignore", action="store_true", help="不读取忽略文件")
    parser.add_argument("--hidden", action="store_true", help="搜索隐藏文件")

    # 上下文
    parser.add_argument("-C", "--context", type=int, default=0, help="显示前后N行上下文")
    parser.add_argument("-A", "--after-context", type=int, default=0, help="显示后N行")
    parser.add_argument("-B", "--before-context", type=int, default=0, help="显示前N行")

    # 输出模式
    parser.add_argument("-l", "--files-with-matches", action="store_true", help="只输出包含匹配的文件名")
    parser.add_argument("-L", "--files-without-match", action="store_true", help="只输出不包含匹配的文件名")
    parser.add_argument("-c", "--count", action="store_true", help="输出每个文件的匹配行数")
    parser.add_argument("--count-matches", action="store_true", help="输出每个文件的总匹配次数")
    parser.add_argument("--json", action="store_true", help="JSON 结构化输出")
    parser.add_argument("-n", "--line-number", action="store_true", default=True, help="显示行号")
    parser.add_argument("-N", "--no-line-number", action="store_false", dest="line_number", help="不显示行号")

    # 编码
    parser.add_argument("-E", "--encoding", default="utf-8", help="文件编码（默认 utf-8）")

    # 大小写
    parser.add_argument("-i", "--ignore-case", action="store_true", help="忽略大小写")
    parser.add_argument("-S", "--smart-case", action="store_true", help="智能大小写（模式含大写则区分）")

    # 替换预览
    parser.add_argument("--replace", help="替换预览（不写盘）")
    parser.add_argument("--passthru", action="store_true", help="输出所有行（配合 --replace）")

    # 其他
    parser.add_argument("-a", "--text", action="store_true", help="搜索二进制文件")
    parser.add_argument("--max-depth", type=int, help="最大搜索深度")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return None

    # 验证必要参数
    if not args.pattern:
        print("错误: 必须提供搜索模式", file=sys.stderr)
        return None

    # 构建选项
    options = SearchOptions()
    options.pattern = args.pattern
    options.paths = args.paths if args.paths else ["."]
    options.type_include = args.type_include or []
    options.type_exclude = args.type_exclude or []
    options.ignore_case = args.ignore_case
    options.smart_case = args.smart_case
    options.encoding = args.encoding
    options.json_output = args.json
    options.files_with_matches = args.files_with_matches
    options.files_without_matches = args.files_without_match
    options.count = args.count
    options.count_matches = args.count_matches
    options.line_number = args.line_number
    options.no_ignore = args.no_ignore
    options.hidden = args.hidden
    options.binary = args.text
    options.max_depth = args.max_depth
    options.replace = args.replace
    options.passthru = args.passthru

    # 上下文
    if args.context > 0:
        options.context = args.context
        options.context_before = args.context
        options.context_after = args.context
    else:
        options.context_before = args.before_context
        options.context_after = args.after_context

    # 解析 glob 规则
    if args.glob:
        for g in args.glob:
            if g.startswith("!"):
                options.glob_exclude.append(g[1:])
            else:
                options.glob_include.append(g)

    # 验证文件类型
    for t in options.type_include + options.type_exclude:
        if get_extension_set(t) is None:
            print(f"错误: 未知文件类型 '{t}' (E006)", file=sys.stderr)
            return None

    return options


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> int:
    """运行内置自检，验证核心逻辑"""
    print("=== ripgrep 自检开始 ===")
    failures = 0

    # 测试 1: 正则编译
    print("\n[测试1] 正则编译...")
    opts = SearchOptions()
    opts.pattern = r"def\s+\w+"
    engine = SearchEngine(opts)
    if engine.compile_regex():
        print("  ✓ 正则编译成功")
    else:
        print(f"  ✗ 正则编译失败: {engine.error_message}")
        failures += 1

    # 测试 2: 忽略规则
    print("\n[测试2] 忽略规则...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_dir = Path(tmpdir)
        (test_dir / ".gitignore").write_text("node_modules/\n*.log\n")
        (test_dir / "test.py").write_text("def hello():\n    pass\n")
        (test_dir / "test.log").write_text("ERROR: something\n")
        (test_dir / "node_modules").mkdir()
        (test_dir / "node_modules" / "module.js").write_text("console.log('test')\n")

        ignore = IgnoreRules(str(test_dir))
        if ignore.is_ignored("node_modules/module.js"):
            print("  ✓ 忽略 node_modules 成功")
        else:
            print("  ✗ 忽略 node_modules 失败")
            failures += 1
        if ignore.is_ignored("test.log"):
            print("  ✓ 忽略 *.log 成功")
        else:
            print("  ✗ 忽略 *.log 失败")
            failures += 1
        if not ignore.is_ignored("test.py"):
            print("  ✓ test.py 未被忽略")
        else:
            print("  ✗ test.py 被错误忽略")
            failures += 1

    # 测试 3: 搜索功能
    print("\n[测试3] 搜索功能...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "code.py").write_text(
            "import os\n"
            "def main():\n"
            "    print('hello')\n"
            "    return 0\n"
            "\n"
            "def helper():\n"
            "    pass\n"
        )

        opts = SearchOptions()
        opts.pattern = r"def\s+\w+"
        opts.paths = [str(test_dir)]
        engine = SearchEngine(opts)
        results = engine.run()

        if len(results) == 1:
            matches = results[0]["matches"]
            if len(matches) == 2:
                print(f"  ✓ 找到 {len(matches)} 个匹配")
                if matches[0]["line_number"] == 2:
                    print("  ✓ 行号正确")
                else:
                    print(f"  ✗ 行号错误: {matches[0]['line_number']}")
                    failures += 1
            else:
                print(f"  ✗ 匹配数量错误: {len(matches)}")
                failures += 1
        else:
            print(f"  ✗ 搜索结果错误: {len(results)} 个文件")
            failures += 1

    # 测试 4: 文件类型过滤
    print("\n[测试4] 文件类型过滤...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.py").write_text("def test():\n    pass\n")
        (test_dir / "test.js").write_text("function test() {}\n")

        opts = SearchOptions()
        opts.pattern = "test"
        opts.paths = [str(test_dir)]
        opts.type_include = ["py"]
        engine = SearchEngine(opts)
        results = engine.run()

        if len(results) == 1 and results[0]["path"].endswith(".py"):
            print("  ✓ 类型过滤正确")
        else:
            print(f"  ✗ 类型过滤错误: {len(results)} 个结果")
            failures += 1

    # 测试 5: 上下文输出
    print("\n[测试5] 上下文输出...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.txt").write_text(
            "line1\n"
            "line2\n"
            "MATCH\n"
            "line4\n"
            "line5\n"
        )

        opts = SearchOptions()
        opts.pattern = "MATCH"
        opts.paths = [str(test_dir)]
        opts.context_before = 1
        opts.context_after = 1
        engine = SearchEngine(opts)
        results = engine.run()

        if len(results) == 1:
            matches = results[0]["matches"]
            if len(matches) == 1 and matches[0]["line_number"] == 3:
                print("  ✓ 上下文设置正确")
            else:
                print(f"  ✗ 上下文匹配错误")
                failures += 1
        else:
            print(f"  ✗ 上下文搜索结果错误")
            failures += 1

    # 测试 6: 计数功能
    print("\n[测试6] 计数功能...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.txt").write_text("apple\nbanana\napple\n")

        opts = SearchOptions()
        opts.pattern = "apple"
        opts.paths = [str(test_dir)]
        opts.count = True
        engine = SearchEngine(opts)
        results = engine.run()

        if len(results) == 1 and results[0].get("count") == 2:
            print("  ✓ 计数功能正确")
        else:
            print(f"  ✗ 计数功能错误: {results}")
            failures += 1

    # 测试 7: JSON 输出
    print("\n[测试7] JSON 输出...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.txt").write_text("hello world\n")

        opts = SearchOptions()
        opts.pattern = "hello"
        opts.paths = [str(test_dir)]
        opts.json_output = True
        engine = SearchEngine(opts)
        results = engine.run()
        formatter = OutputFormatter()
        json_str = formatter.format_json(results, opts)
        try:
            json.loads(json_str)
            print("  ✓ JSON 输出有效")
        except json.JSONDecodeError:
            print("  ✗ JSON 输出无效")
            failures += 1

    # 测试 8: 替换预览
    print("\n[测试8] 替换预览...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        (test_dir / "test.txt").write_text("foo bar foo\n")

        opts = SearchOptions()
        opts.pattern = "foo"
        opts.paths = [str(test_dir)]
        opts.replace = "baz"
        engine = SearchEngine(opts)
        results = engine.run()
        formatter = OutputFormatter()
        output = formatter.format_plain(results, opts)
        if "baz bar baz" in output:
            print("  ✓ 替换预览正确")
        else:
            print(f"  ✗ 替换预览错误: {output}")
            failures += 1

    # 测试 9: 错误处理
    print("\n[测试9] 错误处理...")
    opts = SearchOptions()
    opts.pattern = "[invalid"
    engine = SearchEngine(opts)
    if not engine.compile_regex():
        print(f"  ✓ 正则错误处理正确 (E002)")
    else:
        print("  ✗ 正则错误处理失败")
        failures += 1

    # 测试 10: 多目录搜索
    print("\n[测试10] 多目录搜索...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir1 = Path(tmpdir) / "dir1"
        test_dir2 = Path(tmpdir) / "dir2"
        test_dir1.mkdir()
        test_dir2.mkdir()
        (test_dir1 / "a.txt").write_text("match\n")
        (test_dir2 / "b.txt").write_text("match\n")

        opts = SearchOptions()
        opts.pattern = "match"
        opts.paths = [str(test_dir1), str(test_dir2)]
        engine = SearchEngine(opts)
        results = engine.run()

        if len(results) == 2:
            print("  ✓ 多目录搜索正确")
        else:
            print(f"  ✗ 多目录搜索错误: {len(results)} 个结果")
            failures += 1

    print(f"\n=== 自检完成: {'通过' if failures == 0 else f'{failures} 项失败'} ===")
    return 0 if failures == 0 else 1


# ============================================================
# 主入口
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    """主函数"""
    if argv is None:
        argv = sys.argv[1:]

    # 自检模式
    if "--selftest" in argv:
        return run_selftest()

    # 解析参数
    options = parse_args(argv)
    if options is None:
        return 1

    # 执行搜索
    engine = SearchEngine(options)
    results = engine.run()

    # 错误处理
    if engine.error_code != "E000":
        print(f"错误 ({engine.error_code}): {engine.error_message}", file=sys.stderr)
        return 1

    # 输出结果
    formatter = OutputFormatter()
    try:
        if options.passthru and options.replace:
            output = formatter.format_passthru(results, options)
        elif options.json_output:
            output = formatter.format_json(results, options)
        else:
            output = formatter.format_plain(results, options)

        if output:
            print(output)
    except (OSError, IOError) as e:
        print(f"错误 (E007): 输出写入失败: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
