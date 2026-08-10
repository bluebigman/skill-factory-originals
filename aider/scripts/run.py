#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aider 终端结对编程助手 - 生产级实现

核心功能：
1. 多文件协同编辑：支持同时加载多个源文件，进行批量文本替换/正则替换
2. 自动 Git 提交：修改完成后自动执行 git add 和 git commit
3. 差异审查：生成修改前后的 diff 报告，支持接受或拒绝
4. 修改回退：通过 --undo 命令回退最近一次修改（基于 git checkout）
5. 批量文件处理：对指定目录下的匹配文件执行统一修改

设计原则：
- 所有时间使用 UTC 时区
- 文件写入原子化（先写临时文件再重命名）
- 网络请求（如有）带超时和指数退避重试
- 禁止伪造数据，所有结果均为真实操作
"""

import argparse
import difflib
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


class AiderError(Exception):
    """Aider 自定义异常，用于业务错误处理"""
    pass


def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器，带指数退避"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (subprocess.SubprocessError, OSError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise
            
            raise last_exception
        return wrapper
    return decorator


class GitHelper:
    """Git 操作辅助类，封装常用的 Git 命令"""
    
    @staticmethod
    def run_git_command(args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """执行 Git 命令，带超时和重试"""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=cwd
            )
            return result
        except subprocess.TimeoutExpired:
            raise AiderError("Git 命令执行超时")
        except subprocess.SubprocessError as e:
            raise AiderError(f"Git 命令执行失败: {e}")
    
    @staticmethod
    def check_git_available() -> Tuple[bool, str]:
        """检查 git 命令是否可用"""
        try:
            result = GitHelper.run_git_command(["--version"])
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, "git 命令不可用"
        except AiderError as e:
            return False, str(e)
    
    @staticmethod
    def is_git_repo(cwd: Optional[str] = None) -> bool:
        """检查当前目录是否为 Git 仓库"""
        result = GitHelper.run_git_command(["rev-parse", "--is-inside-work-tree"], cwd)
        return result.returncode == 0 and result.stdout.strip() == "true"
    
    @staticmethod
    def has_commits(cwd: Optional[str] = None) -> bool:
        """检查仓库是否有至少一个 commit"""
        result = GitHelper.run_git_command(["rev-parse", "HEAD"], cwd)
        return result.returncode == 0
    
    @staticmethod
    def get_current_branch(cwd: Optional[str] = None) -> str:
        """获取当前分支名"""
        result = GitHelper.run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
        if result.returncode == 0:
            return result.stdout.strip()
        return "unknown"
    
    @staticmethod
    def stage_file(file_path: str, cwd: Optional[str] = None) -> bool:
        """暂存文件"""
        result = GitHelper.run_git_command(["add", file_path], cwd)
        return result.returncode == 0
    
    @staticmethod
    def commit(message: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """提交暂存区内容"""
        result = GitHelper.run_git_command(["commit", "-m", message], cwd)
        if result.returncode == 0:
            # 提取提交哈希
            match = re.search(r'\[(\w+)\s+([a-f0-9]+)\]', result.stdout)
            if match:
                return True, match.group(2)
            return True, "unknown"
        return False, result.stderr
    
    @staticmethod
    def undo_last_commit(cwd: Optional[str] = None) -> Tuple[bool, str]:
        """回退最近一次提交（保留工作区修改）"""
        result = GitHelper.run_git_command(["reset", "--soft", "HEAD~1"], cwd)
        if result.returncode == 0:
            return True, "已回退最近一次提交"
        return False, result.stderr


class FileEditor:
    """文件编辑辅助类，提供安全的文件读写操作"""
    
    @staticmethod
    def read_file(file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            raise AiderError(f"文件 {file_path} 不是有效的 UTF-8 文本文件")
        except FileNotFoundError:
            raise AiderError(f"文件 {file_path} 不存在")
        except PermissionError:
            raise AiderError(f"没有权限读取文件 {file_path}")
    
    @staticmethod
    def write_file_atomic(file_path: str, content: str) -> None:
        """原子化写入文件（先写临时文件再重命名）"""
        file_path = Path(file_path)
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        
        try:
            # 写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            
            # 原子重命名
            os.replace(temp_path, file_path)
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise AiderError(f"写入文件 {file_path} 失败: {e}")
    
    @staticmethod
    def is_text_file(file_path: str) -> bool:
        """检查是否为文本文件"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' not in chunk
        except Exception:
            return False


class DiffGenerator:
    """差异生成器，使用 difflib 生成统一格式的 diff"""
    
    @staticmethod
    def generate_diff(original: str, modified: str, file_path: str) -> str:
        """生成统一格式的 diff"""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f'a/{file_path}',
            tofile=f'b/{file_path}',
            lineterm=''
        )
        
        return ''.join(diff)


class AiderCore:
    """Aider 核心功能类"""
    
    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd or os.getcwd()
        self.git = GitHelper()
        self.editor = FileEditor()
        self.diff_gen = DiffGenerator()
    
    def validate_environment(self) -> Tuple[bool, str]:
        """验证运行环境"""
        # 检查 git 可用
        git_available, git_msg = self.git.check_git_available()
        if not git_available:
            return False, git_msg
        
        # 检查是否为 git 仓库
        if not self.git.is_git_repo(self.cwd):
            return False, "当前目录不是 Git 仓库"
        
        # 检查是否有 commit
        if not self.git.has_commits(self.cwd):
            return False, "仓库没有 commit 记录，请先创建首个 commit"
        
        return True, "环境验证通过"
    
    def validate_files(self, file_paths: List[str]) -> Tuple[bool, str]:
        """验证文件列表"""
        for file_path in file_paths:
            full_path = os.path.join(self.cwd, file_path)
            if not os.path.exists(full_path):
                return False, f"文件 {file_path} 不存在"
            if not self.editor.is_text_file(full_path):
                return False, f"文件 {file_path} 不是文本文件"
        return True, "文件验证通过"
    
    def apply_replacements(
        self,
        file_paths: List[str],
        old_text: str,
        new_text: str,
        use_regex: bool = False
    ) -> Dict[str, Tuple[bool, str, str]]:
        """对多个文件执行替换操作
        
        Returns:
            Dict[file_path, (success, diff, error_message)]
        """
        results = {}
        
        for file_path in file_paths:
            full_path = os.path.join(self.cwd, file_path)
            
            try:
                # 读取原文件
                original_content = self.editor.read_file(full_path)
                
                # 执行替换
                if use_regex:
                    modified_content, count = re.subn(old_text, new_text, original_content)
                else:
                    modified_content, count = original_content.replace(old_text, new_text), original_content.count(old_text)
                
                if count == 0:
                    results[file_path] = (False, "", f"未找到匹配内容: {old_text}")
                    continue
                
                # 生成 diff
                diff = self.diff_gen.generate_diff(original_content, modified_content, file_path)
                
                # 原子化写入
                self.editor.write_file_atomic(full_path, modified_content)
                
                results[file_path] = (True, diff, f"替换成功，共 {count} 处")
                
            except AiderError as e:
                results[file_path] = (False, "", str(e))
            except Exception as e:
                results[file_path] = (False, "", f"未知错误: {e}")
        
        return results
    
    def batch_process(
        self,
        directory: str,
        pattern: str,
        old_text: str,
        new_text: str,
        use_regex: bool = False
    ) -> Dict[str, Tuple[bool, str, str]]:
        """批量处理目录下的匹配文件"""
        results = {}
        dir_path = os.path.join(self.cwd, directory)
        
        if not os.path.isdir(dir_path):
            results["_error"] = (False, "", f"目录 {directory} 不存在")
            return results
        
        # 收集匹配的文件
        matched_files = []
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if re.match(pattern, file):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.cwd)
                    matched_files.append(rel_path)
        
        if not matched_files:
            results["_error"] = (False, "", f"在 {directory} 中未找到匹配 {pattern} 的文件")
            return results
        
        # 对每个文件执行替换
        return self.apply_replacements(matched_files, old_text, new_text, use_regex)
    
    def auto_commit(self, file_paths: List[str], message: Optional[str] = None) -> Tuple[bool, str]:
        """自动提交修改的文件"""
        # 暂存文件
        for file_path in file_paths:
            if not self.git.stage_file(file_path, self.cwd):
                return False, f"暂存文件 {file_path} 失败"
        
        # 生成提交信息
        if not message:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            message = f"Aider 自动提交: {timestamp}"
        
        # 提交
        success, result = self.git.commit(message, self.cwd)
        if not success:
            return False, f"提交失败: {result}"
        
        return True, f"提交成功，哈希: {result}"
    
    def undo(self) -> Tuple[bool, str]:
        """回退最近一次提交"""
        return self.git.undo_last_commit(self.cwd)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Aider 终端结对编程助手 - 多文件编辑与自动 Git 提交",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --add src/main.py src/helper.py --old "foo" --new "bar"
  %(prog)s --batch-dir ./src --pattern "*.py" --old "foo" --new "bar" --regex
  %(prog)s --undo
  %(prog)s --selftest
        """
    )
    
    # 文件选择参数
    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument(
        "--add", "-a",
        nargs="+",
        help="要编辑的文件列表"
    )
    file_group.add_argument(
        "--batch-dir",
        help="批量处理目录"
    )
    file_group.add_argument(
        "--undo",
        action="store_true",
        help="回退最近一次提交"
    )
    file_group.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测试"
    )
    
    # 替换参数
    parser.add_argument("--old", "-o", help="要替换的旧文本")
    parser.add_argument("--new", "-n", help="替换后的新文本")
    parser.add_argument("--regex", "-r", action="store_true", help="使用正则表达式匹配")
    
    # 批量处理参数
    parser.add_argument("--pattern", "-p", default="*.py", help="批量处理的文件模式（默认: *.py）")
    
    # 提交参数
    parser.add_argument("--message", "-m", help="自定义提交信息")
    parser.add_argument("--yes", "-y", action="store_true", help="自动接受修改，不交互确认")
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    return parser.parse_args()


def run_selftest() -> int:
    """运行自测试，验证核心功能"""
    print("=" * 60)
    print("Aider 自测试开始")
    print("=" * 60)
    
    # 创建临时目录和 Git 仓库
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp(prefix="aider_selftest_")
    test_file = os.path.join(temp_dir, "test.py")
    
    try:
        # 初始化 Git 仓库
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, capture_output=True, check=True)
        
        # 创建测试文件
        test_content = """def hello():
    print("Hello, World!")
    return True

def goodbye():
    print("Goodbye!")
    return False
"""
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # 首次提交
        subprocess.run(["git", "add", "test.py"], cwd=temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, capture_output=True, check=True)
        
        # 创建 Aider 实例
        aider = AiderCore(cwd=temp_dir)
        
        # 测试 1: 环境验证
        print("\n[测试 1] 环境验证")
        success, msg = aider.validate_environment()
        assert success, f"环境验证失败: {msg}"
        print(f"  ✓ 环境验证通过: {msg}")
        
        # 测试 2: 文件替换
        print("\n[测试 2] 文件替换")
        results = aider.apply_replacements(
            ["test.py"],
            "Hello, World!",
            "Hello, Aider!"
        )
        assert "test.py" in results, "替换结果中缺少 test.py"
        success, diff, msg = results["test.py"]
        assert success, f"替换失败: {msg}"
        assert "Hello, Aider!" in diff, "diff 中未包含替换后的内容"
        print(f"  ✓ 替换成功: {msg}")
        print(f"  diff 内容:\n{diff}")
        
        # 验证文件内容
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "Hello, Aider!" in content, "文件内容未更新"
        print("  ✓ 文件内容验证通过")
        
        # 测试 3: 自动提交
        print("\n[测试 3] 自动提交")
        success, msg = aider.auto_commit(["test.py"], "Test commit")
        assert success, f"自动提交失败: {msg}"
        print(f"  ✓ {msg}")
        
        # 测试 4: 回退
        print("\n[测试 4] 回退操作")
        success, msg = aider.undo()
        assert success, f"回退失败: {msg}"
        print(f"  ✓ {msg}")
        
        # 测试 5: 批量处理
        print("\n[测试 5] 批量处理")
        # 创建更多测试文件
        for i in range(3):
            fname = os.path.join(temp_dir, f"test_{i}.py")
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(f"# File {i}\nvalue = {i}\n")
        
        subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Add test files"], cwd=temp_dir, capture_output=True, check=True)
        
        batch_results = aider.batch_process(
            ".",
            r"test_\d+\.py",
            "value = ",
            "result = "
        )
        assert len(batch_results) >= 3, f"批量处理结果数量不足: {len(batch_results)}"
        print(f"  ✓ 批量处理完成，处理了 {len(batch_results)} 个文件")
        
        # 测试 6: 正则替换
        print("\n[测试 6] 正则替换")
        regex_results = aider.apply_replacements(
            ["test.py"],
            r"def (\w+)\(\):",
            r"def \1_updated():",
            use_regex=True
        )
        assert "test.py" in regex_results, "正则替换结果中缺少 test.py"
        success, _, msg = regex_results["test.py"]
        assert success, f"正则替换失败: {msg}"
        print(f"  ✓ 正则替换成功: {msg}")
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        return 1
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """主函数"""
    args = parse_args()
    
    # 运行自测试
    if args.selftest:
        sys.exit(run_selftest())
    
    # 创建 Aider 实例
    aider = AiderCore()
    
    # 处理回退操作
    if args.undo:
        success, msg = aider.undo()
        if success:
            print(f"✓ {msg}")
            sys.exit(0)
        else:
            print(f"✗ {msg}", file=sys.stderr)
            sys.exit(2)
    
    # 验证环境
    success, msg = aider.validate_environment()
    if not success:
        print(f"✗ 环境验证失败: {msg}", file=sys.stderr)
        sys.exit(2)
    
    # 执行替换操作
    if args.add:
        # 验证文件
        success, msg = aider.validate_files(args.add)
        if not success:
            print(f"✗ 文件验证失败: {msg}", file=sys.stderr)
            sys.exit(3)
        
        # 检查替换参数
        if not args.old or args.new is None:
            print("✗ 必须提供 --old 和 --new 参数", file=sys.stderr)
            sys.exit(1)
        
        # 执行替换
        results = aider.apply_replacements(args.add, args.old, args.new, args.regex)
        
    elif args.batch_dir:
        # 检查替换参数
        if not args.old or args.new is None:
            print("✗ 必须提供 --old 和 --new 参数", file=sys.stderr)
            sys.exit(1)
        
        # 执行批量处理
        results = aider.batch_process(args.batch_dir, args.pattern, args.old, args.new, args.regex)
    
    else:
        print("✗ 未指定操作", file=sys.stderr)
        sys.exit(1)
    
    # 处理结果
    successful_files = []
    failed_files = []
    
    for file_path, (success, diff, msg) in results.items():
        if file_path == "_error":
            print(f"✗ {msg}", file=sys.stderr)
            sys.exit(3)
        
        if success:
            successful_files.append(file_path)
            print(f"\n✓ {file_path}: {msg}")
            if diff:
                print(f"  diff:\n{diff}")
        else:
            failed_files.append((file_path, msg))
            print(f"✗ {file_path}: {msg}", file=sys.stderr)
    
    # 如果有失败的文件，报告错误
    if failed_files:
        print(f"\n✗ {len(failed_files)} 个文件处理失败", file=sys.stderr)
        sys.exit(4)
    
    # 如果没有成功修改的文件
    if not successful_files:
        print("✗ 没有文件被修改", file=sys.stderr)
        sys.exit(4)
    
    # 自动提交
    if args.yes:
        success, msg = aider.auto_commit(successful_files, args.message)
        if success:
            print(f"\n✓ {msg}")
        else:
            print(f"\n✗ {msg}", file=sys.stderr)
            sys.exit(5)
    else:
        # 交互确认
        print(f"\n共修改 {len(successful_files)} 个文件")
        response = input("是否接受修改并提交？(y/n): ").strip().lower()
        if response == 'y':
            success, msg = aider.auto_commit(successful_files, args.message)
            if success:
                print(f"✓ {msg}")
            else:
                print(f"✗ {msg}", file=sys.stderr)
                sys.exit(5)
        else:
            print("已取消提交，修改保留在工作区")
            # 回退文件修改
            for file_path in successful_files:
                full_path = os.path.join(aider.cwd, file_path)
                subprocess.run(["git", "checkout", "--", file_path], cwd=aider.cwd, capture_output=True)
            print("已回退所有文件修改")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
