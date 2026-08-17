#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentpack — 智能体任务调度与缓存清理工具
版本: 2.0.4
"""

import argparse
import json
import os
import re
import sys
import time
import tempfile
from collections import OrderedDict
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any

# 错误码定义
ERROR_CODES = {
    "E1001": "项目目录不存在",
    "E1002": "缓存目录不可写",
    "E1003": "任务描述为空",
    "E1004": "关键词提取失败",
    "E1005": "JSON 输出序列化失败",
    "E1006": "缓存目录创建失败",
    "E1007": "缓存读取失败",
    "E1008": "缓存写入失败",
    "E1009": "路由目标不存在",
    "E1010": "内部逻辑错误",
    "E1011": "未知错误",
    "E1012": "参数错误",
    "E1013": "项目目录不可读",
}


class AgentPackError(Exception):
    """带错误码的异常"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def _read_text_safe(path: str) -> str:
    """多编码安全读取（R3 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _iter_lines(path: str):
    """流式读取文件行（R5 合规）"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def _atomic_write(path: str, content: str) -> None:
    """原子化写入文件（R9 合规）"""
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class ContextRouter:
    """上下文路由引擎"""

    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.tmp_dir = self.project_dir / "tmp"
        self.cache_file = self.project_dir / ".agentpack_cache.json"
        self._validate_project_dir()

    def _validate_project_dir(self) -> None:
        """校验项目目录"""
        if not self.project_dir.exists():
            raise AgentPackError("E1001", f"项目目录不存在: {self.project_dir}")
        if not self.project_dir.is_dir():
            raise AgentPackError("E1012", f"项目路径不是目录: {self.project_dir}")
        if not os.access(self.project_dir, os.R_OK):
            raise AgentPackError("E1013", f"项目目录不可读: {self.project_dir}")

    def _ensure_tmp_dir(self) -> None:
        """确保临时目录存在"""
        try:
            self.tmp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise AgentPackError("E1006", f"缓存目录创建失败: {e}")

    def _get_tmp_files(self) -> List[Path]:
        """获取临时目录下的所有文件"""
        if not self.tmp_dir.exists():
            return []
        return [f for f in self.tmp_dir.iterdir() if f.is_file()]

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def _parse_tasks(self, task_str: str) -> List[str]:
        """解析任务字符串，支持分号分隔"""
        if not task_str or not task_str.strip():
            raise AgentPackError("E1003", "任务描述为空")
        tasks = [t.strip() for t in task_str.split(";") if t.strip()]
        if not tasks:
            raise AgentPackError("E1003", "任务描述为空")
        return tasks

    def _route_task(self, task: str) -> str:
        """路由单个任务到对应操作"""
        task_lower = task.lower()
        if "清理" in task_lower or "clean" in task_lower:
            return "clean"
        elif "分析" in task_lower or "analyze" in task_lower:
            return "analyze"
        else:
            raise AgentPackError("E1009", f"路由目标不存在: {task}")

    def clean_tmp(self, dry_run: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """清理临时文件"""
        self._ensure_tmp_dir()
        files = self._get_tmp_files()
        result = {
            "operation": "clean",
            "dry_run": dry_run,
            "files_deleted": [],
            "total_size": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for file_path in files:
            try:
                file_size = file_path.stat().st_size
                result["total_size"] += file_size
                if verbose:
                    print(f"[{'待删除' if dry_run else '已删除'}] {file_path} ({self._format_size(file_size)})")
                if not dry_run:
                    file_path.unlink()
                result["files_deleted"].append(str(file_path))
            except OSError as e:
                print(f"[警告] 删除文件失败: {file_path} - {e}", file=sys.stderr)

        if verbose:
            action = "预演" if dry_run else "执行"
            print(f"[{action}] 共 {len(result['files_deleted'])} 个文件将被删除，总大小 {self._format_size(result['total_size'])}")
        return result

    def analyze_tmp(self, verbose: bool = False) -> Dict[str, Any]:
        """分析临时目录"""
        self._ensure_tmp_dir()
        files = self._get_tmp_files()
        result = {
            "operation": "analyze",
            "file_count": len(files),
            "total_size": 0,
            "files": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for file_path in files:
            try:
                file_size = file_path.stat().st_size
                result["total_size"] += file_size
                result["files"].append({
                    "path": str(file_path),
                    "size": file_size,
                    "size_formatted": self._format_size(file_size),
                })
                if verbose:
                    print(f"[分析] {file_path} ({self._format_size(file_size)})")
            except OSError as e:
                print(f"[警告] 读取文件信息失败: {file_path} - {e}", file=sys.stderr)

        if verbose:
            print(f"[分析] {self.tmp_dir}/ 目录下共 {result['file_count']} 个文件，总大小 {self._format_size(result['total_size'])}")
        return result

    def execute_tasks(self, task_str: str, dry_run: bool = False, verbose: bool = False) -> List[Dict[str, Any]]:
        """执行任务序列"""
        tasks = self._parse_tasks(task_str)
        results = []
        for task in tasks:
            try:
                route = self._route_task(task)
                if route == "clean":
                    result = self.clean_tmp(dry_run=dry_run, verbose=verbose)
                elif route == "analyze":
                    result = self.analyze_tmp(verbose=verbose)
                else:
                    raise AgentPackError("E1009", f"路由目标不存在: {task}")
                results.append(result)
            except AgentPackError as e:
                print(f"[错误] {e}", file=sys.stderr)
                results.append({"operation": "error", "error": str(e)})
        return results

    def save_cache(self, data: Dict[str, Any]) -> None:
        """保存缓存数据"""
        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            _atomic_write(str(self.cache_file), content)
        except (OSError, TypeError) as e:
            raise AgentPackError("E1008", f"缓存写入失败: {e}")

    def load_cache(self) -> Dict[str, Any]:
        """加载缓存数据"""
        if not self.cache_file.exists():
            return {}
        try:
            content = _read_text_safe(str(self.cache_file))
            return json.loads(content)
        except (OSError, json.JSONDecodeError) as e:
            raise AgentPackError("E1007", f"缓存读取失败: {e}")


def run_selftest() -> bool:
    """运行自检测试，验证核心功能"""
    print("[自检] 开始运行核心功能测试...")
    test_dir = tempfile.mkdtemp(prefix="agentpack_selftest_")
    try:
        # 创建测试环境
        test_project = Path(test_dir) / "project"
        test_project.mkdir()
        tmp_dir = test_project / "tmp"
        tmp_dir.mkdir()

        # 创建测试文件
        test_file = tmp_dir / "test_cache.bin"
        test_file.write_bytes(b"x" * 1024)  # 1KB 文件

        # 测试 1: 关键词路由
        router = ContextRouter(str(test_project))
        route = router._route_task("清理")
        assert route == "clean", f"关键词路由失败: 期望 'clean', 得到 '{route}'"
        print("[自检] 关键词路由测试: 通过")

        # 测试 2: 批量任务调度
        tasks = router._parse_tasks("清理;分析")
        assert len(tasks) == 2, f"批量任务解析失败: 期望 2 个任务, 得到 {len(tasks)}"
        print("[自检] 批量任务调度测试: 通过")

        # 测试 3: 缓存清理（预演模式）
        dry_result = router.clean_tmp(dry_run=True)
        assert dry_result["dry_run"] == True, "预演模式标志错误"
        assert len(dry_result["files_deleted"]) == 1, f"预演模式应发现 1 个文件, 得到 {len(dry_result['files_deleted'])}"
        assert test_file.exists(), "预演模式不应实际删除文件"
        print("[自检] 预演模式测试: 通过")

        # 测试 4: 缓存清理（实际执行）
        clean_result = router.clean_tmp(dry_run=False)
        assert len(clean_result["files_deleted"]) == 1, f"清理应删除 1 个文件, 得到 {len(clean_result['files_deleted'])}"
        assert not test_file.exists(), "清理后文件应不存在"
        print("[自检] 缓存清理测试: 通过")

        # 测试 5: 分析功能
        # 重新创建文件用于分析
        test_file2 = tmp_dir / "test_analyze.txt"
        test_file2.write_text("hello world", encoding="utf-8")
        analyze_result = router.analyze_tmp()
        assert analyze_result["file_count"] == 1, f"分析应发现 1 个文件, 得到 {analyze_result['file_count']}"
        assert analyze_result["total_size"] > 0, "分析应检测到文件大小"
        print("[自检] 分析功能测试: 通过")

        # 测试 6: 缓存读写
        cache_data = {"test": "data", "timestamp": datetime.now(timezone.utc).isoformat()}
        router.save_cache(cache_data)
        loaded = router.load_cache()
        assert loaded.get("test") == "data", "缓存读写失败"
        print("[自检] 缓存读写测试: 通过")

        # 测试 7: 错误处理
        try:
            router._parse_tasks("")
            assert False, "空任务应抛出异常"
        except AgentPackError as e:
            assert e.code == "E1003", f"错误码错误: 期望 E1003, 得到 {e.code}"
        print("[自检] 错误处理测试: 通过")

        print("[自检] 全部测试通过: OK")
        return True

    except AssertionError as e:
        print(f"[自检] 断言失败: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[自检] 未预期异常: {e}", file=sys.stderr)
        return False
    finally:
        # 清理测试目录
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="agentpack — 智能体任务调度与缓存清理工具",
        epilog="示例: python run.py 清理;分析 --dry-run"
    )
    parser.add_argument(
        "--tasks",
        nargs="?",
        default=None,
        help="要执行的任务，支持分号分隔多个任务（如: 清理;分析）"
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=".",
        help="项目目录（默认: 当前目录）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预演模式，只显示将要执行的操作，不实际执行"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出模式"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检测试"
    )

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print("agentpack v2.0.4")
        return 0

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 检查任务参数
    if not args.tasks:
        print("[需核实:操作类型] 请指定要执行的操作，如\"清理\"或\"分析\"", file=sys.stderr)
        return 1

    try:
        # 创建路由器
        router = ContextRouter(args.project_dir)

        # 执行任务
        results = router.execute_tasks(
            args.tasks,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        # 检查是否有错误
        has_error = any(r.get("operation") == "error" for r in results)
        return 1 if has_error else 0

    except AgentPackError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[中断] 用户取消操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[未知错误] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
