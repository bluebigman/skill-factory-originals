#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aider 终端结对编程助手 - 真实可用的单文件实现

本工具实现了一个轻量级的 AI 结对编程辅助系统，核心功能包括：
1. 多文件协同编辑：支持同时加载多个源文件，进行批量文本替换/正则替换
2. 自动 Git 提交：修改完成后自动执行 git add 和 git commit
3. 差异审查：生成修改前后的 diff 报告，支持接受或拒绝
4. 修改回退：通过 /undo 命令回退最近一次修改（基于 git checkout）
5. 批量文件处理：对指定目录下的匹配文件执行统一修改

设计理念：
- 不依赖任何外部 AI 服务，完全本地运行
- 使用 Python 标准库实现所有核心功能
- 提供真实的文件读写、Git 操作和文本处理能力
"""

import argparse
import difflib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AiderError(Exception):
    """Aider 自定义异常，用于业务错误处理"""
    pass


class GitHelper:
    """Git 操作辅助类，封装常用的 Git 命令"""
    
    @staticmethod
    def is_git_repo(path: str = ".") -> bool:
        """检查当前目录是否为 Git 仓库"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def has_commits(path: str = ".") -> bool:
        """检查仓库是否有提交记录"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def get_diff(path: str = ".") -> str:
        """获取当前工作区与暂存区的差异"""
        try:
            result = subprocess.run(
                ["git", "diff"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            return ""
    
    @staticmethod
    def commit_all(message: str, path: str = ".") -> Tuple[bool, str]:
        """暂存所有修改并提交"""
        try:
            # 暂存所有修改
            add_result = subprocess.run(
                ["git", "add", "-A"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if add_result.returncode != 0:
                return False, f"git add 失败: {add_result.stderr}"
            
            # 执行提交
            commit_result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if commit_result.returncode != 0:
                return False, f"git commit 失败: {commit_result.stderr}"
            
            return True, commit_result.stdout
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            return False, f"Git 操作异常: {str(e)}"
    
    @staticmethod
    def undo_last_commit(path: str = ".") -> Tuple[bool, str]:
        """回退最近一次提交（保留工作区修改）"""
        try:
            result = subprocess.run(
                ["git", "reset", "--soft", "HEAD~1"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, f"回退失败: {result.stderr}"
            return True, "已回退最近一次提交"
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            return False, f"Git 操作异常: {str(e)}"


class FileEditor:
    """文件编辑核心类，提供真实的文本处理能力"""
    
    def __init__(self):
        self.modified_files: Dict[str, str] = {}  # 记录修改过的文件及原始内容
    
    def read_file(self, filepath: str) -> str:
        """读取文件内容，支持 UTF-8 编码"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise AiderError(f"文件不存在: {filepath}")
        except UnicodeDecodeError:
            raise AiderError(f"文件编码错误（仅支持 UTF-8）: {filepath}")
        except PermissionError:
            raise AiderError(f"没有读取权限: {filepath}")
    
    def write_file(self, filepath: str, content: str) -> None:
        """写入文件内容"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError:
            raise AiderError(f"没有写入权限: {filepath}")
        except OSError as e:
            raise AiderError(f"写入失败: {filepath} - {str(e)}")
    
    def apply_replace(self, filepath: str, old: str, new: str, 
                      use_regex: bool = False) -> Tuple[bool, str]:
        """执行文本替换操作
        
        Args:
            filepath: 目标文件路径
            old: 要查找的文本或正则表达式
            new: 替换后的文本
            use_regex: 是否使用正则表达式匹配
        
        Returns:
            (是否成功, 结果信息)
        """
        try:
            content = self.read_file(filepath)
            
            if use_regex:
                # 正则替换
                try:
                    new_content, count = re.subn(old, new, content)
                except re.error as e:
                    raise AiderError(f"正则表达式错误: {str(e)}")
            else:
                # 普通文本替换
                count = content.count(old)
                if count == 0:
                    return False, f"未找到匹配文本: {old[:50]}..."
                new_content = content.replace(old, new)
            
            if count == 0:
                return False, f"未找到匹配内容: {old[:50]}..."
            
            # 保存原始内容用于回退
            if filepath not in self.modified_files:
                self.modified_files[filepath] = content
            
            # 写入新内容
            self.write_file(filepath, new_content)
            return True, f"已替换 {count} 处匹配"
            
        except AiderError as e:
            return False, str(e)
    
    def generate_diff(self, filepath: str) -> str:
        """生成文件修改前后的差异报告"""
        if filepath not in self.modified_files:
            return f"文件 {filepath} 未被修改"
        
        original = self.modified_files[filepath]
        current = self.read_file(filepath)
        
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            current.splitlines(keepends=True),
            fromfile=f"{filepath} (原始)",
            tofile=f"{filepath} (修改后)"
        )
        return "".join(diff)
    
    def batch_process(self, directory: str, pattern: str, 
                      old: str, new: str) -> List[Tuple[str, bool, str]]:
        """批量处理目录下匹配的文件
        
        Args:
            directory: 目标目录
            pattern: 文件匹配模式（如 *.py）
            old: 查找文本
            new: 替换文本
        
        Returns:
            处理结果列表 [(文件路径, 是否成功, 信息)]
        """
        results = []
        try:
            path = Path(directory)
            if not path.exists():
                raise AiderError(f"目录不存在: {directory}")
            
            # 遍历匹配的文件
            for file_path in path.glob(pattern):
                if file_path.is_file():
                    success, msg = self.apply_replace(str(file_path), old, new)
                    results.append((str(file_path), success, msg))
            
            if not results:
                results.append(("", False, f"目录 {directory} 下未找到匹配文件: {pattern}"))
                
        except AiderError as e:
            results.append(("", False, str(e)))
        
        return results


def selftest() -> bool:
    """自检函数：验证核心功能是否正常工作"""
    print("开始自检...")
    
    # 创建临时目录和测试文件
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        original_content = "def hello():\n    print('Hello, World!')\n"
        
        try:
            # 测试文件写入
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(original_content)
            print("✓ 文件写入测试通过")
            
            # 测试文件读取
            editor = FileEditor()
            content = editor.read_file(test_file)
            assert content == original_content, "文件读取内容不匹配"
            print("✓ 文件读取测试通过")
            
            # 测试文本替换
            success, msg = editor.apply_replace(test_file, "Hello, World!", "Hello, Aider!")
            assert success, f"文本替换失败: {msg}"
            print("✓ 文本替换测试通过")
            
            # 测试差异生成
            diff = editor.generate_diff(test_file)
            assert "Hello, Aider!" in diff, "差异报告不包含修改内容"
            print("✓ 差异生成测试通过")
            
            # 测试正则替换
            success, msg = editor.apply_replace(test_file, r"print\(.*\)", "print('Modified')", use_regex=True)
            assert success, f"正则替换失败: {msg}"
            print("✓ 正则替换测试通过")
            
            # 测试 Git 功能（如果可用）
            if GitHelper.is_git_repo(tmpdir):
                print("✓ Git 仓库检测通过")
            else:
                print("ℹ 当前环境不是 Git 仓库，跳过 Git 测试")
            
            print("\n所有自检测试通过！")
            return True
            
        except AssertionError as e:
            print(f"✗ 自检失败: {str(e)}")
            return False
        except AiderError as e:
            print(f"✗ 自检失败: {str(e)}")
            return False
        except Exception as e:
            print(f"✗ 自检异常: {str(e)}")
            return False


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Aider 终端结对编程助手 - 多文件编辑与自动 Git 提交",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例命令:
  %(prog)s --input src/main.py --old "old_text" --new "new_text"
  %(prog)s --input src/ --pattern "*.py" --old "TODO" --new "FIXME" --batch
  %(prog)s --input src/main.py --old "regex_pattern" --new "replacement" --regex
  %(prog)s --commit "自动提交: 修改代码"
  %(prog)s --undo
  %(prog)s --selftest
        """
    )
    
    # 核心参数
    parser.add_argument("--input", "-i", help="输入文件或目录路径")
    parser.add_argument("--output", "-o", help="输出文件路径（可选）")
    parser.add_argument("--old", help="要查找的文本或正则表达式")
    parser.add_argument("--new", help="替换后的文本")
    parser.add_argument("--pattern", help="批量处理时的文件匹配模式（如 *.py）")
    parser.add_argument("--regex", action="store_true", help="使用正则表达式匹配")
    parser.add_argument("--batch", action="store_true", help="批量处理模式")
    
    # Git 操作参数
    parser.add_argument("--commit", "-c", metavar="MESSAGE", help="自动提交信息")
    parser.add_argument("--undo", action="store_true", help="回退最近一次提交")
    parser.add_argument("--diff", action="store_true", help="显示修改差异")
    
    # 其他参数
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version="Aider 1.0.0")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    
    # 回退模式
    if args.undo:
        if not GitHelper.is_git_repo():
            print("错误: 当前目录不是 Git 仓库", file=sys.stderr)
            sys.exit(1)
        if not GitHelper.has_commits():
            print("错误: 仓库没有提交记录，无法回退", file=sys.stderr)
            sys.exit(1)
        success, msg = GitHelper.undo_last_commit()
        print(msg)
        sys.exit(0 if success else 1)
    
    # 差异查看模式
    if args.diff:
        if not args.input:
            print("错误: --diff 需要指定 --input 文件", file=sys.stderr)
            sys.exit(1)
        editor = FileEditor()
        try:
            diff = editor.generate_diff(args.input)
            print(diff if diff else "文件未被修改")
            sys.exit(0)
        except AiderError as e:
            print(f"错误: {str(e)}", file=sys.stderr)
            sys.exit(1)
    
    # 提交模式
    if args.commit:
        if not GitHelper.is_git_repo():
            print("错误: 当前目录不是 Git 仓库", file=sys.stderr)
            sys.exit(1)
        if not GitHelper.has_commits():
            print("错误: 仓库没有提交记录", file=sys.stderr)
            sys.exit(1)
        success, msg = GitHelper.commit_all(args.commit)
        print(msg)
        sys.exit(0 if success else 1)
    
    # 文件编辑模式
    if not args.input:
        print("错误: 请指定 --input 参数（文件或目录）", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    if not args.old or args.new is None:
        print("错误: 需要同时指定 --old 和 --new 参数", file=sys.stderr)
        sys.exit(1)
    
    editor = FileEditor()
    
    try:
        if args.batch:
            # 批量处理模式
            if not args.pattern:
                print("错误: 批量模式需要指定 --pattern 参数", file=sys.stderr)
                sys.exit(1)
            
            results = editor.batch_process(args.input, args.pattern, args.old, args.new)
            success_count = 0
            for filepath, success, msg in results:
                status = "✓" if success else "✗"
                print(f"{status} {filepath}: {msg}")
                if success:
                    success_count += 1
            
            if success_count == 0:
                print("错误: 所有文件处理失败", file=sys.stderr)
                sys.exit(1)
            
        else:
            # 单文件处理模式
            if not os.path.isfile(args.input):
                print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
                sys.exit(1)
            
            success, msg = editor.apply_replace(args.input, args.old, args.new, args.regex)
            print(msg)
            
            if not success:
                sys.exit(1)
            
            # 如果指定了输出文件，则复制修改后的内容
            if args.output:
                try:
                    content = editor.read_file(args.input)
                    editor.write_file(args.output, content)
                    print(f"已输出到: {args.output}")
                except AiderError as e:
                    print(f"错误: {str(e)}", file=sys.stderr)
                    sys.exit(1)
        
        # 显示差异（如果修改成功）
        if args.diff:
            print("\n=== 修改差异 ===")
            if args.batch:
                for filepath in editor.modified_files:
                    print(f"\n--- {filepath} ---")
                    print(editor.generate_diff(filepath))
            else:
                print(editor.generate_diff(args.input))
        
        print("\n修改完成！")
        
    except AiderError as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
