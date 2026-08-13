#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentpack — 本地上下文路由引擎
版本: 2.0.0 (生产级重写)
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
    """本地上下文路由引擎核心类"""

    # 关键词 → 模块映射
    KEYWORD_MODULES = {
        "清理": "cache_cleaner",
        "缓存": "cache_cleaner",
        "分析": "analyzer",
        "重新分析": "analyzer",
        "批量": "batch_ops",
        "重命名": "batch_ops",
        "报告": "reporter",
        "生成": "reporter",
        "预览": "preview",
        "路由": "router",
        "分发": "router",
    }

    # 模块名称映射
    MODULE_NAMES = {
        "cache_cleaner": "缓存管理模块",
        "analyzer": "分析模块",
        "batch_ops": "批量操作模块",
        "reporter": "报告生成模块",
        "preview": "预览模块",
        "router": "路由模块",
    }

    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.cache_dir = self.project_dir / ".cache" / "agentpack"
        self._validate_project()

    def _validate_project(self) -> None:
        """校验项目目录（R7 输入校验）"""
        if not self.project_dir.exists():
            raise AgentPackError("E1001", f"项目目录不存在: {self.project_dir}")
        if not self.project_dir.is_dir():
            raise AgentPackError("E1001", f"路径不是目录: {self.project_dir}")
        if not os.access(self.project_dir, os.R_OK):
            raise AgentPackError("E1013", f"项目目录不可读: {self.project_dir}")

    def _validate_cache_writable(self) -> None:
        """校验缓存目录可写（R7 输入校验）"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.cache_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
        except OSError as e:
            raise AgentPackError("E1002", f"缓存目录不可写: {self.cache_dir} ({e})")

    def extract_keywords(self, description: str) -> List[str]:
        """从任务描述中提取关键词（R1 契约）"""
        if not description or not description.strip():
            raise AgentPackError("E1003", "任务描述为空")
        keywords = []
        for kw in self.KEYWORD_MODULES:
            if kw in description:
                keywords.append(kw)
        return keywords

    def route(self, description: str) -> Tuple[List[str], float]:
        """路由任务到模块，返回 (模块列表, 置信度)（R1 契约）"""
        keywords = self.extract_keywords(description)
        if not keywords:
            return [], 0.0

        modules = []
        for kw in keywords:
            module = self.KEYWORD_MODULES[kw]
            if module not in modules:
                modules.append(module)

        # 置信度 = 匹配关键词数 / 描述总词数 * 0.8 基础系数
        total_words = len(re.findall(r"[\u4e00-\u9fff\w]+", description))
        confidence = min(1.0, (len(keywords) / max(total_words, 1)) * 0.8 + 0.2)
        return modules, confidence

    def clean_cache(self, dry_run: bool = False) -> Dict[str, Any]:
        """清理缓存目录（R4 预览/撤回）"""
        self._validate_cache_writable()
        result = {"module": "cache_cleaner", "action": "清理缓存", "files": [], "dry_run": dry_run}

        if not self.cache_dir.exists():
            result["message"] = "缓存目录不存在，无需清理"
            return result

        for item in self.cache_dir.iterdir():
            if item.is_file():
                result["files"].append(str(item))
                if not dry_run:
                    item.unlink()
            elif item.is_dir():
                for sub in item.rglob("*"):
                    if sub.is_file():
                        result["files"].append(str(sub))
                        if not dry_run:
                            sub.unlink()
                if not dry_run:
                    item.rmdir()

        result["count"] = len(result["files"])
        return result

    def analyze(self, dry_run: bool = False) -> Dict[str, Any]:
        """分析项目结构（R1 契约）"""
        result = {"module": "analyzer", "action": "分析项目", "files": [], "dry_run": dry_run}

        code_exts = {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp"}
        for root, dirs, files in os.walk(self.project_dir):
            # 跳过缓存目录
            dirs[:] = [d for d in dirs if d not in {".cache", ".git", "__pycache__", "node_modules"}]
            for fname in files:
                ext = Path(fname).suffix
                if ext in code_exts:
                    fpath = Path(root) / fname
                    result["files"].append(str(fpath))

        result["count"] = len(result["files"])
        return result

    def batch_ops(self, dry_run: bool = False) -> Dict[str, Any]:
        """批量操作预览（R4 预览/撤回）"""
        result = {"module": "batch_ops", "action": "批量操作", "files": [], "dry_run": dry_run}

        # 扫描项目中的文件，模拟批量重命名预览
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if d not in {".cache", ".git", "__pycache__", "node_modules"}]
            for fname in files:
                fpath = Path(root) / fname
                result["files"].append(str(fpath))

        result["count"] = len(result["files"])
        return result

    def reporter(self, dry_run: bool = False) -> Dict[str, Any]:
        """生成报告（R1 契约）"""
        result = {"module": "reporter", "action": "生成报告", "files": [], "dry_run": dry_run}

        report_path = self.project_dir / "agentpack_report.json"
        result["report_path"] = str(report_path)

        if not dry_run:
            report_data = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "project_dir": str(self.project_dir),
                "modules": ["cache_cleaner", "analyzer", "batch_ops", "reporter"],
            }
            _atomic_write(str(report_path), json.dumps(report_data, ensure_ascii=False, indent=2))

        return result

    def preview(self, dry_run: bool = False) -> Dict[str, Any]:
        """预览操作（R4 预览/撤回）"""
        result = {"module": "preview", "action": "预览操作", "files": [], "dry_run": dry_run}
        result["message"] = "预览模式：以下操作将被执行"
        return result

    def router(self, dry_run: bool = False) -> Dict[str, Any]:
        """路由模块（R1 契约）"""
        result = {"module": "router", "action": "路由任务", "files": [], "dry_run": dry_run}
        result["message"] = "路由模块：任务分发完成"
        return result

    def execute(self, modules: List[str], dry_run: bool = False) -> List[Dict[str, Any]]:
        """按顺序执行模块（R1 契约）"""
        results = []
        module_map = {
            "cache_cleaner": self.clean_cache,
            "analyzer": self.analyze,
            "batch_ops": self.batch_ops,
            "reporter": self.reporter,
            "preview": self.preview,
            "router": self.router,
        }

        for module in modules:
            if module not in module_map:
                raise AgentPackError("E1009", f"路由目标不存在: {module}")
            try:
                result = module_map[module](dry_run=dry_run)
                results.append(result)
            except AgentPackError:
                raise
            except Exception as e:
                raise AgentPackError("E1010", f"执行模块 {module} 失败: {e}")

        return results

    def run_selftest(self) -> bool:
        """运行自检（R1 契约）"""
        print("[AgentPack] 开始自检...")
        all_passed = True

        # 测试 1: 关键词提取
        try:
            keywords = self.extract_keywords("清理缓存并重新分析项目")
            assert "清理" in keywords, "关键词提取失败: 缺少'清理'"
            assert "缓存" in keywords, "关键词提取失败: 缺少'缓存'"
            print("[PASS] 关键词提取")
        except Exception as e:
            print(f"[FAIL] 关键词提取: {e}")
            all_passed = False

        # 测试 2: 路由
        try:
            modules, confidence = self.route("清理缓存并重新分析项目")
            assert "cache_cleaner" in modules, "路由失败: 缺少 cache_cleaner"
            assert "analyzer" in modules, "路由失败: 缺少 analyzer"
            assert confidence > 0.5, f"置信度异常: {confidence}"
            print(f"[PASS] 路由 (置信度: {confidence:.2f})")
        except Exception as e:
            print(f"[FAIL] 路由: {e}")
            all_passed = False

        # 测试 3: 空输入
        try:
            self.extract_keywords("")
            print("[FAIL] 空输入未报错")
            all_passed = False
        except AgentPackError as e:
            assert e.code == "E1003", f"错误码异常: {e.code}"
            print("[PASS] 空输入校验")
        except Exception as e:
            print(f"[FAIL] 空输入校验: {e}")
            all_passed = False

        # 测试 4: 模糊输入
        try:
            modules, confidence = self.route("处理一下那个东西")
            assert confidence == 0.0, f"模糊输入置信度异常: {confidence}"
            assert len(modules) == 0, f"模糊输入路由异常: {modules}"
            print("[PASS] 模糊输入处理")
        except Exception as e:
            print(f"[FAIL] 模糊输入处理: {e}")
            all_passed = False

        # 测试 5: 缓存清理 dry-run
        try:
            result = self.clean_cache(dry_run=True)
            assert result["dry_run"] is True, "dry-run 标志异常"
            print("[PASS] 缓存清理 dry-run")
        except Exception as e:
            print(f"[FAIL] 缓存清理 dry-run: {e}")
            all_passed = False

        # 测试 6: 分析
        try:
            result = self.analyze(dry_run=True)
            assert "files" in result, "分析结果缺少 files"
            print(f"[PASS] 项目分析 (发现 {result['count']} 个文件)")
        except Exception as e:
            print(f"[FAIL] 项目分析: {e}")
            all_passed = False

        # 测试 7: 串联任务
        try:
            modules, confidence = self.route("清理缓存; 重新分析")
            assert "cache_cleaner" in modules, "串联任务路由失败"
            assert "analyzer" in modules, "串联任务路由失败"
            print("[PASS] 串联任务路由")
        except Exception as e:
            print(f"[FAIL] 串联任务路由: {e}")
            all_passed = False

        # 测试 8: 原子写入
        try:
            test_path = self.cache_dir / "test_atomic.txt"
            _atomic_write(str(test_path), "test content")
            assert test_path.exists(), "原子写入失败"
            test_path.unlink()
            print("[PASS] 原子写入")
        except Exception as e:
            print(f"[FAIL] 原子写入: {e}")
            all_passed = False

        print(f"[AgentPack] 自检完成: {'全部通过' if all_passed else '存在失败'}")
        return all_passed


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数（R7 输入校验）"""
    parser = argparse.ArgumentParser(
        prog="agentpack",
        description="AgentPack 智能体路由与任务调度工具",
        epilog="示例: agentpack '清理缓存; 重新分析' --dry-run",
    )
    parser.add_argument("--task", nargs="?", help="任务描述，用分号分隔多个子任务")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="store_true", help="输出版本号")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际执行")
    parser.add_argument("--project-dir", default=".", help="项目目录（默认: 当前目录）")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--output", help="输出结果到指定文件")
    return parser.parse_args(argv)


def format_output(results: List[Dict[str, Any]], confidence: float, elapsed: float) -> str:
    """格式化输出结果（R6 可解释输出）"""
    lines = ["[AgentPack] 任务执行完成"]
    lines.append(f"- 路由模块: {len(results)} 个")
    total_ops = sum(r.get("count", 0) for r in results)
    lines.append(f"- 执行操作: {total_ops} 项")
    lines.append(f"- 置信度: {confidence:.2f}")
    lines.append(f"- 耗时: {elapsed:.2f}s")

    for r in results:
        module_name = r.get("module", "unknown")
        action = r.get("action", "")
        count = r.get("count", 0)
        dry = r.get("dry_run", False)
        mode = "预览" if dry else "执行"
        lines.append(f"  - [{module_name}] {action}: {count} 项 ({mode})")
        if r.get("message"):
            lines.append(f"    {r['message']}")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口（R8 函数短小单一）"""
    args = parse_args(argv)

    if args.version:
        print("agentpack 2.0.0")
        return 0

    if args.selftest:
        router = ContextRouter(args.project_dir)
        return 0 if router.run_selftest() else 1

    if not args.task:
        print("[AgentPack] 错误: 未提供任务描述", file=sys.stderr)
        print("用法: agentpack '任务描述' [--dry-run] [--project-dir DIR]", file=sys.stderr)
        return 1

    try:
        router = ContextRouter(args.project_dir)
        modules, confidence = router.route(args.task)

        if confidence < 0.5:
            print(f"[AgentPack] 置信度过低 ({confidence:.2f})，拒绝执行")
            print("[需核实:关键词] 对应的任务无法路由。")
            print("请补充具体操作关键词，如'清理'、'分析'、'批量重命名'等。")
            return 1

        if confidence < 0.8:
            print(f"[AgentPack] 置信度中等 ({confidence:.2f})，需要确认")
            print(f"将执行模块: {', '.join(router.MODULE_NAMES.get(m, m) for m in modules)}")
            print("请确认是否继续 (y/N): ", end="")
            confirm = input().strip().lower()
            if confirm not in ("y", "yes"):
                print("[AgentPack] 已取消执行")
                return 0

        start_time = time.time()
        results = router.execute(modules, dry_run=args.dry_run)
        elapsed = time.time() - start_time

        output = format_output(results, confidence, elapsed)
        print(output)

        if args.output:
            output_data = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "confidence": confidence,
                "dry_run": args.dry_run,
                "results": results,
            }
            _atomic_write(args.output, json.dumps(output_data, ensure_ascii=False, indent=2))
            print(f"[AgentPack] 结果已写入: {args.output}")

        return 0

    except AgentPackError as e:
        print(f"[AgentPack] 错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("[AgentPack] 已中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[AgentPack] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
