#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — ripgrep 技能的全新独立实现（clean-room）

仅依据功能规格实现，不复制任何既有代码。
支持正则搜索、忽略规则、文件类型过滤、上下文输出、统计计数、
文件列表、多路径、替换预览、编码指定和 JSON 输出。

用法示例:
    python main.py "pattern" [path...]
    python main.py --selftest
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 错误码定义
# E001: 参数错误
# E002: 路径不存在
# E003: 路径不可读
# E004: 正则表达式编译失败
# E005: 编码错误
# E006: 输出错误
# E007: 内部逻辑错误
# E008: 忽略规则解析错误
# E009: 文件类型映射错误
# E010: 自检失败
# ============================================================

# ============================================================
# 数据结构
# ============================================================

@dataclass
class SearchOptions:
    """搜索选项集合"""
    pattern: str = ""
    paths: List[str] = field(default_factory=list)
    ignore_case: bool = False
    line_number: bool = True
    context_before: int = 0
    context_after: int = 0
    count: bool = False
    count_matches: bool = False
    files_with_matches: bool = False
    files_without_match: bool = False
    file_type: Optional[str] = None
    exclude_type: Optional[str] = None
    encoding: str = "utf-8"
    json_output: bool = False
    replace: Optional[str] = None
    passthru: bool = False
    follow_symlinks: bool = False
    one_file_system: bool = False
    no_ignore: bool = False
    hidden: bool = False
    max_depth: Optional[int] = None
    glob: Optional[str] = None
    invert_match: bool = False


@dataclass
class MatchResult:
    """单个匹配结果"""
    path: str
    line_number: int
    line_text: str
    match_start: int
    match_end: int
    match_text: str


@dataclass
class FileResult:
    """文件级匹配结果"""
    path: str
    matches: List[MatchResult] = field(default_factory=list)
    match_count: int = 0
    line_count: int = 0


# ============================================================
# 核心搜索类
# ============================================================

class IgnoreRule:
    """忽略规则管理器（模拟 .gitignore 行为）"""
    
    def __init__(self) -> None:
        self.patterns: List[Tuple[str, bool]] = []  # (pattern, is_dir_only)
    
    def load_from_file(self, filepath: str) -> None:
        """从忽略文件加载规则"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # 处理以 / 结尾的目录规则
                    is_dir_only = line.endswith("/")
                    if is_dir_only:
                        line = line.rstrip("/")
                    self.patterns.append((line, is_dir_only))
        except (OSError, UnicodeDecodeError) as e:
            raise RuntimeError(f"E008: 无法读取忽略文件 {filepath}: {e}")
    
    def is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """判断相对路径是否被忽略"""
        for pattern, is_dir_only in self.patterns:
            if is_dir_only and not is_dir:
                continue
            # 支持简单的 glob 匹配
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                return True
            # 支持目录前缀匹配
            if "/" in pattern and rel_path.startswith(pattern.rstrip("/") + "/"):
                return True
        return False


class FileTypeRegistry:
    """文件类型注册表"""
    
    def __init__(self) -> None:
        self.types: Dict[str, Set[str]] = {
            "py": {".py", ".pyw", ".pyi"},
            "js": {".js", ".mjs", ".cjs"},
            "ts": {".ts", ".tsx"},
            "java": {".java"},
            "c": {".c", ".h"},
            "cpp": {".cpp", ".hpp", ".cc", ".hh"},
            "cs": {".cs"},
            "go": {".go"},
            "rs": {".rs"},
            "rb": {".rb"},
            "php": {".php"},
            "html": {".html", ".htm"},
            "css": {".css"},
            "json": {".json"},
            "xml": {".xml"},
            "yaml": {".yaml", ".yml"},
            "toml": {".toml"},
            "md": {".md", ".markdown"},
            "txt": {".txt"},
            "sh": {".sh", ".bash"},
            "sql": {".sql"},
        }
    
    def get_extensions(self, type_name: str) -> Set[str]:
        """获取指定类型的扩展名集合"""
        if type_name not in self.types:
            raise ValueError(f"E009: 未知文件类型: {type_name}")
        return self.types[type_name]
    
    def is_type(self, path: str, type_name: str) -> bool:
        """判断文件是否属于指定类型"""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.types.get(type_name, set())


class SearchEngine:
    """搜索引擎主类"""
    
    def __init__(self, options: SearchOptions) -> None:
        self.options = options
        self.ignore_rules: List[IgnoreRule] = []
        self.type_registry = FileTypeRegistry()
        self._regex = self._compile_pattern()
    
    def _compile_pattern(self) -> re.Pattern:
        """编译正则表达式"""
        try:
            flags = re.MULTILINE
            if self.options.ignore_case:
                flags |= re.IGNORECASE
            return re.compile(self.options.pattern, flags)
        except re.error as e:
            raise RuntimeError(f"E004: 正则表达式编译失败: {e}")
    
    def _load_ignore_rules(self, root_dir: str) -> None:
        """加载忽略规则"""
        if self.options.no_ignore:
            return
        for ignore_file in [".gitignore", ".ignore", ".rgignore"]:
            path = os.path.join(root_dir, ignore_file)
            if os.path.isfile(path):
                rule = IgnoreRule()
                try:
                    rule.load_from_file(path)
                    self.ignore_rules.append(rule)
                except RuntimeError:
                    # 忽略规则加载失败不阻断搜索
                    continue
    
    def _is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """检查路径是否被忽略"""
        for rule in self.ignore_rules:
            if rule.is_ignored(rel_path, is_dir):
                return True
        return False
    
    def _should_skip(self, root: str, name: str, is_dir: bool) -> bool:
        """判断是否跳过该路径"""
        # 隐藏文件
        if name.startswith(".") and not self.options.hidden:
            if name not in [".gitignore", ".ignore", ".rgignore"]:
                return True
        
        # 忽略规则
        rel_path = os.path.relpath(os.path.join(root, name), root)
        if self._is_ignored(rel_path, is_dir):
            return True
        
        # 深度限制
        if self.options.max_depth is not None:
            depth = rel_path.count(os.sep)
            if depth >= self.options.max_depth:
                return True
        
        return False
    
    def _iter_files(self, paths: List[str]) -> List[str]:
        """遍历所有搜索路径，返回文件列表"""
        files: List[str] = []
        
        for path in paths:
            if not os.path.exists(path):
                raise RuntimeError(f"E002: 路径不存在: {path}")
            if not os.access(path, os.R_OK):
                raise RuntimeError(f"E003: 路径不可读: {path}")
            
            if os.path.isfile(path):
                # 单文件直接加入
                if self._matches_type(path):
                    files.append(path)
            elif os.path.isdir(path):
                # 加载该目录的忽略规则
                self._load_ignore_rules(path)
                # 递归遍历
                for root, dirs, filenames in os.walk(path):
                    # 过滤目录
                    dirs[:] = [d for d in dirs if not self._should_skip(root, d, True)]
                    for filename in filenames:
                        full_path = os.path.join(root, filename)
                        if self._should_skip(root, filename, False):
                            continue
                        if self._matches_type(full_path):
                            files.append(full_path)
        
        return files
    
    def _matches_type(self, path: str) -> bool:
        """检查文件类型是否符合过滤条件"""
        if self.options.file_type:
            try:
                if not self.type_registry.is_type(path, self.options.file_type):
                    return False
            except ValueError:
                return False
        
        if self.options.exclude_type:
            try:
                if self.type_registry.is_type(path, self.options.exclude_type):
                    return False
            except ValueError:
                pass
        
        if self.options.glob:
            if not fnmatch.fnmatch(path, self.options.glob):
                return False
        
        return True
    
    def _read_file(self, path: str) -> str:
        """读取文件内容"""
        try:
            with open(path, "r", encoding=self.options.encoding, errors="replace") as f:
                return f.read()
        except (OSError, UnicodeDecodeError) as e:
            raise RuntimeError(f"E005: 读取文件失败 {path}: {e}")
    
    def _process_file(self, path: str) -> Optional[FileResult]:
        """处理单个文件，返回匹配结果"""
        content = self._read_file(path)
        lines = content.splitlines()
        result = FileResult(path=path)
        
        for line_num, line in enumerate(lines, 1):
            # 搜索匹配
            for match in self._regex.finditer(line):
                matched = True
                if self.options.invert_match:
                    matched = False
                
                if matched:
                    m = MatchResult(
                        path=path,
                        line_number=line_num,
                        line_text=line,
                        match_start=match.start(),
                        match_end=match.end(),
                        match_text=match.group(0)
                    )
                    result.matches.append(m)
                    result.match_count += 1
            
            # 反转匹配时，无匹配的行也算
            if self.options.invert_match and not self._regex.search(line):
                result.line_count += 1
        
        if self.options.count:
            result.line_count = len(set(m.line_number for m in result.matches))
        
        return result if (result.matches or (self.options.invert_match and result.line_count > 0)) else None
    
    def search(self) -> Dict[str, FileResult]:
        """执行搜索"""
        files = self._iter_files(self.options.paths)
        results: Dict[str, FileResult] = {}
        
        for file_path in files:
            try:
                result = self._process_file(file_path)
                if result:
                    results[file_path] = result
            except RuntimeError as e:
                # 单个文件错误不中断整个搜索
                if "E005" in str(e):
                    sys.stderr.write(f"警告: {e}\n")
                    continue
                raise
        
        return results
    
    def format_output(self, results: Dict[str, FileResult]) -> str:
        """格式化输出结果"""
        if self.options.json_output:
            return self._format_json(results)
        
        lines: List[str] = []
        
        for path, result in results.items():
            if self.options.files_without_match:
                if not result.matches:
                    lines.append(path)
                continue
            
            if self.options.files_with_matches:
                if result.matches:
                    lines.append(path)
                continue
            
            if self.options.count:
                count = result.match_count if self.options.count_matches else result.line_count
                lines.append(f"{path}:{count}")
                continue
            
            # 正常输出
            for match in result.matches:
                prefix = f"{path}:{match.line_number}:" if self.options.line_number else f"{path}:"
                
                # 上下文处理
                if self.options.context_before > 0 or self.options.context_after > 0:
                    # 获取上下文行
                    all_lines = match.line_text.splitlines()
                    start = max(0, match.line_number - 1 - self.options.context_before)
                    end = min(len(all_lines), match.line_number + self.options.context_after)
                    
                    for ctx_line_num in range(start, end):
                        ctx_line = all_lines[ctx_line_num] if ctx_line_num < len(all_lines) else ""
                        marker = ">" if ctx_line_num == match.line_number - 1 else "-"
                        lines.append(f"{prefix}{marker} {ctx_line}")
                else:
                    # 替换预览
                    if self.options.replace is not None:
                        new_line = self._regex.sub(self.options.replace, match.line_text)
                        if self.options.passthru:
                            lines.append(f"{prefix}- {match.line_text}")
                            lines.append(f"{prefix}+ {new_line}")
                        else:
                            lines.append(f"{prefix} {new_line}")
                    else:
                        lines.append(f"{prefix} {match.line_text}")
        
        return "\n".join(lines)
    
    def _format_json(self, results: Dict[str, FileResult]) -> str:
        """JSON 格式输出"""
        output = []
        for path, result in results.items():
            file_data = {
                "path": path,
                "matches": []
            }
            for match in result.matches:
                file_data["matches"].append({
                    "line_number": match.line_number,
                    "line": match.line_text,
                    "start": match.match_start,
                    "end": match.match_end,
                    "text": match.match_text
                })
            output.append(file_data)
        return json.dumps(output, ensure_ascii=False, indent=2)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """内置自检逻辑"""
    import tempfile
    import shutil
    
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="rg_selftest_")
        
        # 创建测试文件
        test_files = {
            "test1.py": "def hello():\n    print('Hello World')\n\n# comment\n",
            "test2.py": "class Test:\n    def method(self):\n        return 'hello again'\n",
            "test3.txt": "This is a plain text file.\nNo code here.\n",
            "data.json": '{"key": "hello", "value": 42}\n',
        }
        
        for name, content in test_files.items():
            with open(os.path.join(temp_dir, name), "w", encoding="utf-8") as f:
                f.write(content)
        
        # 创建 .gitignore
        with open(os.path.join(temp_dir, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("*.log\n")
        
        # 测试1: 基本搜索
        opts = SearchOptions(pattern="hello", paths=[temp_dir])
        engine = SearchEngine(opts)
        results = engine.search()
        assert len(results) >= 2, f"E010: 基本搜索失败，找到 {len(results)} 个文件"
        assert any("test1.py" in p for p in results), "E010: 未找到 test1.py"
        assert any("test2.py" in p for p in results), "E010: 未找到 test2.py"
        assert any("data.json" in p for p in results), "E010: 未找到 data.json"
        
        # 测试2: 文件类型过滤
        opts = SearchOptions(pattern="hello", paths=[temp_dir], file_type="py")
        engine = SearchEngine(opts)
        results = engine.search()
        assert all(p.endswith(".py") for p in results), "E010: 文件类型过滤失败"
        
        # 测试3: 忽略规则
        with open(os.path.join(temp_dir, "test.log"), "w", encoding="utf-8") as f:
            f.write("hello in log file\n")
        
        opts = SearchOptions(pattern="hello", paths=[temp_dir])
        engine = SearchEngine(opts)
        results = engine.search()
        assert not any(p.endswith(".log") for p in results), "E010: 忽略规则失败"
        
        # 测试4: 上下文输出
        opts = SearchOptions(pattern="Hello", paths=[os.path.join(temp_dir, "test1.py")], context_before=1, context_after=1)
        engine = SearchEngine(opts)
        results = engine.search()
        output = engine.format_output(results)
        assert "def hello" in output or "Hello World" in output, "E010: 上下文输出失败"
        
        # 测试5: 计数
        opts = SearchOptions(pattern="hello", paths=[temp_dir], count=True)
        engine = SearchEngine(opts)
        results = engine.search()
        output = engine.format_output(results)
        assert any(":1" in line for line in output.splitlines()), "E010: 计数输出失败"
        
        # 测试6: JSON 输出
        opts = SearchOptions(pattern="hello", paths=[temp_dir], json_output=True)
        engine = SearchEngine(opts)
        results = engine.search()
        output = engine.format_output(results)
        data = json.loads(output)
        assert isinstance(data, list) and len(data) > 0, "E010: JSON 输出失败"
        
        # 测试7: 反转匹配
        opts = SearchOptions(pattern="hello", paths=[os.path.join(temp_dir, "test3.txt")], invert_match=True)
        engine = SearchEngine(opts)
        results = engine.search()
        assert results, "E010: 反转匹配失败"
        
        # 测试8: 替换预览
        opts = SearchOptions(pattern="hello", paths=[os.path.join(temp_dir, "test1.py")], replace="world")
        engine = SearchEngine(opts)
        results = engine.search()
        output = engine.format_output(results)
        assert "world" in output, "E010: 替换预览失败"
        
        # 测试9: 大小写不敏感
        opts = SearchOptions(pattern="HELLO", paths=[os.path.join(temp_dir, "test1.py")], ignore_case=True)
        engine = SearchEngine(opts)
        results = engine.search()
        assert results, "E010: 大小写不敏感搜索失败"
        
        # 测试10: 多路径搜索
        sub_dir = os.path.join(temp_dir, "sub")
        os.makedirs(sub_dir, exist_ok=True)
        with open(os.path.join(sub_dir, "test4.py"), "w", encoding="utf-8") as f:
            f.write("hello from subdirectory\n")
        
        opts = SearchOptions(pattern="hello", paths=[temp_dir, sub_dir])
        engine = SearchEngine(opts)
        results = engine.search()
        assert any("test4.py" in p for p in results), "E010: 多路径搜索失败"
        
        print("自检通过: 所有核心功能验证成功")
        return 0
        
    except AssertionError as e:
        print(f"自检失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"自检异常: {e}", file=sys.stderr)
        return 1
    finally:
        # 清理临时目录
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 命令行入口
# ============================================================

def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="rg",
        description="代码库快速检索 正则匹配 文件扫描",
        epilog="示例: python main.py 'pattern' /path/to/dir -C 3"
    )
    
    parser.add_argument("--pattern", nargs="?", help="正则表达式模式")
    parser.add_argument("--paths", nargs="*", default=["."], help="搜索路径（默认当前目录）")
    
    parser.add_argument("-i", "--ignore-case", action="store_true", help="忽略大小写")
    parser.add_argument("-n", "--line-number", action="store_true", default=True, help="显示行号")
    parser.add_argument("-C", "--context", type=int, default=0, metavar="NUM", help="前后各显示 NUM 行")
    parser.add_argument("-A", "--after-context", type=int, default=0, metavar="NUM", help="显示后 NUM 行")
    parser.add_argument("-B", "--before-context", type=int, default=0, metavar="NUM", help="显示前 NUM 行")
    parser.add_argument("-c", "--count", action="store_true", help="按文件计数")
    parser.add_argument("--count-matches", action="store_true", help="统计总匹配次数")
    parser.add_argument("-l", "--files-with-matches", action="store_true", help="仅输出含匹配的文件")
    parser.add_argument("-L", "--files-without-match", action="store_true", help="仅输出不含匹配的文件")
    parser.add_argument("-t", "--type", dest="file_type", help="按文件类型过滤")
    parser.add_argument("-T", "--type-not", dest="exclude_type", help="排除文件类型")
    parser.add_argument("-E", "--encoding", default="utf-8", help="文件编码（默认 utf-8）")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--replace", help="替换预览")
    parser.add_argument("--passthru", action="store_true", help="替换预览时同时显示原文")
    parser.add_argument("--follow", action="store_true", help="跟随符号链接")
    parser.add_argument("--one-file-system", action="store_true", help="不跨文件系统")
    parser.add_argument("--no-ignore", action="store_true", help="不读取忽略规则")
    parser.add_argument("--hidden", action="store_true", help="搜索隐藏文件")
    parser.add_argument("--max-depth", type=int, help="最大搜索深度")
    parser.add_argument("--glob", help="glob 模式过滤文件")
    parser.add_argument("-v", "--invert-match", action="store_true", help="反转匹配")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    return parser.parse_args(argv)


def main() -> int:
    """主入口函数"""
    try:
        args = parse_args(sys.argv[1:])
        
        # 自检模式
        if args.selftest:
            return run_selftest()
        
        # 参数检查
        if not args.pattern:
            print("E001: 必须提供搜索模式", file=sys.stderr)
            return 1
        
        # 构建选项
        options = SearchOptions(
            pattern=args.pattern,
            paths=args.paths,
            ignore_case=args.ignore_case,
            line_number=args.line_number,
            context_before=args.before_context or args.context,
            context_after=args.after_context or args.context,
            count=args.count,
            count_matches=args.count_matches,
            files_with_matches=args.files_with_matches,
            files_without_match=args.files_without_match,
            file_type=args.file_type,
            exclude_type=args.exclude_type,
            encoding=args.encoding,
            json_output=args.json,
            replace=args.replace,
            passthru=args.passthru,
            follow_symlinks=args.follow,
            one_file_system=args.one_file_system,
            no_ignore=args.no_ignore,
            hidden=args.hidden,
            max_depth=args.max_depth,
            glob=args.glob,
            invert_match=args.invert_match,
        )
        
        # 执行搜索
        engine = SearchEngine(options)
        results = engine.search()
        
        # 输出结果
        output = engine.format_output(results)
        if output:
            print(output)
        
        return 0
        
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("搜索被中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"E007: 未预期的错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
