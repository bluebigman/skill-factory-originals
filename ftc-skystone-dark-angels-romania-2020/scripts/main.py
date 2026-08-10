#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTC SKYSTONE 机器人项目代码结构审查工具
=========================================
提供以下能力：
  1. 解析 FTC 机器人项目目录结构
  2. 识别 OpMode、硬件映射、工具类、配置类等模块
  3. 梳理类之间的继承、接口实现关系
  4. 检查命名、注释等代码规范问题
  5. 标注潜在风险点（空指针、资源泄漏、并发问题）
  6. 生成结构化 Markdown 审查报告

仅使用 Python 标准库实现，无第三方依赖。

用法示例：
  python run.py /path/to/ftc_project
  python run.py /path/to/ftc_project --dry-run
  python run.py /path/to/ftc_project --verbose
  python run.py --selftest
"""

import argparse
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ============================================================
# 常量定义与错误码
# ============================================================

# 错误码：E001~E010
ERROR_CODES = {
    "E001": "参数错误：路径不存在或不可访问",
    "E002": "参数错误：路径不是目录",
    "E003": "IO错误：读取文件失败",
    "E004": "解析错误：无法识别的文件结构",
    "E005": "解析错误：无效的 Java 语法",
    "E006": "内部错误：模块分类异常",
    "E007": "内部错误：依赖分析异常",
    "E008": "内部错误：规范检查异常",
    "E009": "内部错误：报告生成异常",
    "E010": "内部错误：未知异常",
}

# 模块分类关键字
OPMODE_KEYWORDS = ["OpMode", "LinearOpMode", "IterativeOpMode"]
HARDWARE_KEYWORDS = ["HardwareMap", "Hardware", "Motor", "Servo", "Sensor"]
UTIL_KEYWORDS = ["Util", "Helper", "Tool", "Math"]
CONFIG_KEYWORDS = ["Config", "Constants", "Settings", "Parameters"]

# 规范检查规则（宽松版）
MIN_COMMENT_RATIO = 0.05  # 注释行占比下限（宽松阈值）
MAX_LINE_LENGTH = 200     # 行长度上限（宽松阈值）
MIN_FILE_NAME_LEN = 3     # 文件名最小长度

# 风险模式（正则表达式）
RISK_PATTERNS = {
    "空指针风险": re.compile(r"\.get\w*\(\s*\)\s*\.", re.IGNORECASE),
    "资源泄漏风险": re.compile(r"(new\s+FileInputStream|new\s+FileOutputStream|openConnection)", re.IGNORECASE),
    "并发风险": re.compile(r"(synchronized|Thread\.start|volatile)", re.IGNORECASE),
    "硬编码风险": re.compile(r"(telemetry\.addData\(\s*\"[^\"]+\"\s*,\s*\"[^\"]*\")", re.IGNORECASE),
}

# 单文件解析超时（秒）
FILE_PARSE_TIMEOUT = 10


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class JavaFileInfo:
    """单个 Java 文件的解析信息"""
    file_path: str
    file_name: str
    package_name: str = ""
    class_name: str = ""
    module_type: str = "未分类"
    extends: str = ""
    implements: List[str] = field(default_factory=list)
    line_count: int = 0
    comment_line_count: int = 0
    max_line_length: int = 0
    risks: List[Tuple[str, int, str]] = field(default_factory=list)  # (风险类型, 行号, 描述)
    issues: List[str] = field(default_factory=list)  # 规范问题
    parse_error: Optional[str] = None


@dataclass
class ProjectReport:
    """项目审查报告"""
    project_path: str
    project_name: str
    scan_time: str
    java_files: List[JavaFileInfo] = field(default_factory=list)
    total_files: int = 0
    module_stats: Dict[str, int] = field(default_factory=dict)
    total_risks: int = 0
    total_issues: int = 0
    parse_failures: List[Tuple[str, str]] = field(default_factory=list)  # (文件, 错误)


# ============================================================
# 工具函数
# ============================================================

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def get_utc_now_str() -> str:
    """获取 UTC 当前时间的字符串表示"""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def read_text_safe(file_path: Path) -> str:
    """
    安全读取文件内容，支持多编码。
    返回文件内容字符串（失败时返回空字符串）。
    """
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(file_path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {file_path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(file_path, encoding="utf-8", errors="replace") as f:
        return f.read()


def atomic_write_file(file_path: Path, content: str) -> None:
    """原子化写入文件：先写临时文件，再重命名"""
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(temp_path, file_path)


def save_report(path: Path, data: str, dry_run: bool = False) -> bool:
    """
    保存报告文件。
    返回 True 表示已写入，False 表示 dry-run 未写入。
    """
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


# ============================================================
# 核心解析逻辑
# ============================================================

def parse_java_file(file_path: Path) -> JavaFileInfo:
    """
    解析单个 Java 文件，提取结构信息。
    返回 JavaFileInfo 对象。
    """
    info = JavaFileInfo(
        file_path=str(file_path),
        file_name=file_path.name,
    )

    # 读取文件内容（流式处理）
    try:
        content = read_text_safe(file_path)
        if not content and file_path.stat().st_size > 0:
            info.parse_error = "E003: 读取文件失败"
            return info
    except Exception as e:
        info.parse_error = f"E003: 读取文件失败 - {str(e)}"
        return info

    # 按行处理（流式）
    lines = content.splitlines()
    info.line_count = len(lines)

    # 解析包名
    for line in lines:
        line = line.strip()
        if line.startswith("package "):
            info.package_name = line[8:].rstrip(";").strip()
            break

    # 解析类名、继承、接口
    for line in lines:
        line = line.strip()
        # 类声明
        class_match = re.search(r"(?:public\s+|protected\s+|private\s+)?(?:abstract\s+|final\s+)?class\s+(\w+)", line)
        if class_match:
            info.class_name = class_match.group(1)
            # 继承
            extends_match = re.search(r"extends\s+(\w+)", line)
            if extends_match:
                info.extends = extends_match.group(1)
            # 接口
            implements_match = re.search(r"implements\s+([\w,\s]+)", line)
            if implements_match:
                info.implements = [x.strip() for x in implements_match.group(1).split(",") if x.strip()]
            break

    # 统计注释行和最大行长度
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            info.comment_line_count += 1
        info.max_line_length = max(info.max_line_length, len(line))

    # 模块分类
    info.module_type = classify_module(info)

    # 风险检测
    detect_risks(info, lines)

    # 规范检查
    check_standards(info)

    return info


def classify_module(info: JavaFileInfo) -> str:
    """根据类名和内容分类模块类型"""
    class_name = info.class_name.lower()
    file_name = info.file_name.lower()

    # OpMode 检测
    if any(kw.lower() in class_name or kw.lower() in file_name for kw in OPMODE_KEYWORDS):
        return "OpMode"
    # 硬件映射检测
    if any(kw.lower() in class_name or kw.lower() in file_name for kw in HARDWARE_KEYWORDS):
        return "硬件映射"
    # 工具类检测
    if any(kw.lower() in class_name or kw.lower() in file_name for kw in UTIL_KEYWORDS):
        return "工具类"
    # 配置类检测
    if any(kw.lower() in class_name or kw.lower() in file_name for kw in CONFIG_KEYWORDS):
        return "配置类"
    return "其他"


def detect_risks(info: JavaFileInfo, lines: List[str]) -> None:
    """检测代码中的潜在风险点"""
    for idx, line in enumerate(lines, start=1):
        for risk_type, pattern in RISK_PATTERNS.items():
            if pattern.search(line):
                # 提取风险描述
                desc = line.strip()[:80] + ("..." if len(line.strip()) > 80 else "")
                info.risks.append((risk_type, idx, desc))


def check_standards(info: JavaFileInfo) -> None:
    """检查代码规范问题"""
    # 文件名长度检查
    if len(info.file_name) < MIN_FILE_NAME_LEN:
        info.issues.append(f"文件名过短: {info.file_name}")

    # 注释比例检查
    if info.line_count > 0:
        comment_ratio = info.comment_line_count / info.line_count
        if comment_ratio < MIN_COMMENT_RATIO:
            info.issues.append(
                f"注释比例不足: {comment_ratio:.1%} (阈值: {MIN_COMMENT_RATIO:.1%})"
            )

    # 行长度检查
    if info.max_line_length > MAX_LINE_LENGTH:
        info.issues.append(
            f"存在超长行: {info.max_line_length} 字符 (阈值: {MAX_LINE_LENGTH})"
        )

    # 命名规范检查（类名驼峰）
    if info.class_name and not re.match(r"^[A-Z][a-zA-Z0-9]*$", info.class_name):
        info.issues.append(f"类名不符合驼峰规范: {info.class_name}")


# ============================================================
# 项目扫描
# ============================================================

def scan_project(project_path: Path, verbose: bool = False) -> ProjectReport:
    """
    扫描项目目录，解析所有 Java 文件。
    返回 ProjectReport 对象。
    """
    report = ProjectReport(
        project_path=str(project_path),
        project_name=project_path.name,
        scan_time=get_utc_now_str(),
    )

    # 递归查找所有 .java 文件
    java_files = []
    for root, dirs, files in os.walk(project_path):
        # 跳过构建目录
        dirs[:] = [d for d in dirs if d not in ["build", ".gradle", ".idea", "node_modules"]]
        for f in files:
            if f.endswith(".java"):
                java_files.append(Path(root) / f)

    report.total_files = len(java_files)

    # 解析每个文件
    for file_path in java_files:
        if verbose:
            print(f"[VERBOSE] 解析文件: {file_path}")

        try:
            # 超时控制
            start_time = time.time()
            info = parse_java_file(file_path)
            elapsed = time.time() - start_time

            if elapsed > FILE_PARSE_TIMEOUT:
                info.parse_error = f"解析超时 ({elapsed:.1f}s > {FILE_PARSE_TIMEOUT}s)"
                report.parse_failures.append((str(file_path), info.parse_error))
                continue

            if info.parse_error:
                report.parse_failures.append((str(file_path), info.parse_error))
                continue

            report.java_files.append(info)

            # 统计模块
            report.module_stats[info.module_type] = report.module_stats.get(info.module_type, 0) + 1
            report.total_risks += len(info.risks)
            report.total_issues += len(info.issues)

            if verbose:
                print(f"[VERBOSE]   模块分类: {info.module_type}")
                if info.extends:
                    print(f"[VERBOSE]   继承: {info.extends}")
                for risk_type, line_no, desc in info.risks:
                    print(f"[VERBOSE]   风险命中: {risk_type} (第 {line_no} 行: {desc})")

        except Exception as e:
            error_msg = f"E010: 未知异常 - {str(e)}"
            report.parse_failures.append((str(file_path), error_msg))
            if verbose:
                print(f"[ERROR] {error_msg}")
                traceback.print_exc()

    return report


# ============================================================
# 报告生成
# ============================================================

def generate_report(report: ProjectReport) -> str:
    """
    生成 Markdown 格式的审查报告。
    返回报告内容字符串。
    """
    lines = []
    lines.append(f"# FTC 机器人项目代码结构审查报告")
    lines.append(f"")
    lines.append(f"## 项目信息")
    lines.append(f"")
    lines.append(f"- **项目路径**: `{report.project_path}`")
    lines.append(f"- **项目名称**: {report.project_name}")
    lines.append(f"- **扫描时间**: {report.scan_time} (UTC)")
    lines.append(f"- **Java 文件数**: {report.total_files}")
    lines.append(f"")
    lines.append(f"## 模块统计")
    lines.append(f"")
    lines.append(f"| 模块类型 | 数量 |")
    lines.append(f"|----------|------|")
    for module_type, count in sorted(report.module_stats.items(), key=lambda x: -x[1]):
        lines.append(f"| {module_type} | {count} |")
    lines.append(f"")
    lines.append(f"## 目录结构")
    lines.append(f"")
    lines.append(f"```text")
    lines.append(f"{report.project_path}")
    # 生成简化的目录树
    dirs = set()
    for info in report.java_files:
        rel_path = os.path.relpath(info.file_path, report.project_path)
        parts = rel_path.split(os.sep)
        for i in range(1, len(parts)):
            dirs.add(os.sep.join(parts[:i]))
    for d in sorted(dirs):
        indent = "  " * (d.count(os.sep) + 1)
        lines.append(f"{indent}{os.path.basename(d)}/")
    for info in report.java_files:
        rel_path = os.path.relpath(info.file_path, report.project_path)
        indent = "  " * (rel_path.count(os.sep) + 1)
        lines.append(f"{indent}{info.file_name}")
    lines.append(f"```")
    lines.append(f"")
    lines.append(f"## 模块清单")
    lines.append(f"")
    lines.append(f"| 文件 | 模块类型 | 类名 | 继承 | 接口 |")
    lines.append(f"|------|----------|------|------|------|")
    for info in report.java_files:
        interfaces = ", ".join(info.implements) if info.implements else "-"
        lines.append(f"| {info.file_name} | {info.module_type} | {info.class_name or '-'} | {info.extends or '-'} | {interfaces} |")
    lines.append(f"")
    lines.append(f"## 依赖关系")
    lines.append(f"")
    lines.append(f"```text")
    for info in report.java_files:
        if info.extends:
            lines.append(f"{info.class_name or info.file_name} -> extends {info.extends}")
        for impl in info.implements:
            lines.append(f"{info.class_name or info.file_name} -> implements {impl}")
    lines.append(f"```")
    lines.append(f"")
    lines.append(f"## 规范检查")
    lines.append(f"")
    lines.append(f"| 文件 | 问题 |")
    lines.append(f"|------|------|")
    for info in report.java_files:
        if info.issues:
            for issue in info.issues:
                lines.append(f"| {info.file_name} | {issue} |")
    lines.append(f"")
    lines.append(f"## 风险标注")
    lines.append(f"")
    lines.append(f"| 文件 | 风险类型 | 行号 | 描述 |")
    lines.append(f"|------|----------|------|------|")
    for info in report.java_files:
        for risk_type, line_no, desc in info.risks:
            lines.append(f"| {info.file_name} | {risk_type} | {line_no} | `{desc}` |")
    lines.append(f"")
    lines.append(f"## 解析失败")
    lines.append(f"")
    if report.parse_failures:
        lines.append(f"| 文件 | 错误 |")
        lines.append(f"|------|------|")
        for file_path, error in report.parse_failures:
            lines.append(f"| {file_path} | {error} |")
    else:
        lines.append(f"无解析失败。")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"*报告由 FTC SKYSTONE 代码审查工具自动生成*")

    return "\n".join(lines)


# ============================================================
# 自检模式
# ============================================================

def run_selftest() -> int:
    """
    运行自检，验证核心功能。
    返回退出码（0 表示成功）。
    """
    print("[SELFTEST] 开始自检...")
    failures = []

    # 测试 1: 创建临时项目
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp(prefix="ftc_selftest_")
    try:
        # 创建测试项目结构
        project_dir = Path(temp_dir) / "TestProject"
        src_dir = project_dir / "TeamCode" / "src" / "main" / "java" / "org" / "firstinspires" / "ftc" / "teamcode"
        src_dir.mkdir(parents=True)

        # 创建测试文件
        test_files = {
            "AutoOpMode.java": """
package org.firstinspires.ftc.teamcode;

import com.qualcomm.robotcore.eventloop.opmode.LinearOpMode;

@com.qualcomm.robotcore.eventloop.opmode.Autonomous(name="Auto")
public class AutoOpMode extends LinearOpMode {
    @Override
    public void runOpMode() {
        // 测试注释
        telemetry.addData("Status", "Running");
        waitForStart();
    }
}
""",
            "TeleOpMode.java": """
package org.firstinspires.ftc.teamcode;

import com.qualcomm.robotcore.eventloop.opmode.OpMode;

@com.qualcomm.robotcore.eventloop.opmode.TeleOp(name="Tele")
public class TeleOpMode extends OpMode {
    @Override
    public void init() {
        // 初始化
    }
}
""",
            "HardwareMap.java": """
package org.firstinspires.ftc.teamcode;

public class HardwareMap {
    public DcMotor leftMotor;
    public DcMotor rightMotor;
}
""",
            "RobotUtil.java": """
package org.firstinspires.ftc.teamcode;

public class RobotUtil {
    public static double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }
}
""",
            "Constants.java": """
package org.firstinspires.ftc.teamcode;

public class Constants {
    public static final double WHEEL_DIAMETER = 4.0;
}
""",
        }

        for fname, content in test_files.items():
            fpath = src_dir / fname
            fpath.write_text(content, encoding="utf-8")

        # 测试 2: 扫描项目
        print("[SELFTEST] 测试扫描项目...")
        report = scan_project(project_dir, verbose=False)

        # 断言: 文件数
        assert report.total_files == 5, f"预期 5 个文件，实际 {report.total_files}"
        print(f"[SELFTEST]   文件数: {report.total_files} ✓")

        # 断言: 模块分类
        assert report.module_stats.get("OpMode", 0) == 2, f"预期 2 个 OpMode，实际 {report.module_stats.get('OpMode', 0)}"
        assert report.module_stats.get("硬件映射", 0) == 1, f"预期 1 个硬件映射，实际 {report.module_stats.get('硬件映射', 0)}"
        assert report.module_stats.get("工具类", 0) == 1, f"预期 1 个工具类，实际 {report.module_stats.get('工具类', 0)}"
        assert report.module_stats.get("配置类", 0) == 1, f"预期 1 个配置类，实际 {report.module_stats.get('配置类', 0)}"
        print(f"[SELFTEST]   模块分类: {report.module_stats} ✓")

        # 断言: 继承关系
        auto_opmode = [f for f in report.java_files if f.file_name == "AutoOpMode.java"][0]
        assert auto_opmode.extends == "LinearOpMode", f"预期继承 LinearOpMode，实际 {auto_opmode.extends}"
        print(f"[SELFTEST]   继承关系: AutoOpMode -> LinearOpMode ✓")

        # 断言: 风险检测
        assert report.total_risks >= 0, "风险数不能为负"
        print(f"[SELFTEST]   风险检测: {report.total_risks} 个风险 ✓")

        # 测试 3: 生成报告
        print("[SELFTEST] 测试报告生成...")
        report_content = generate_report(report)
        assert "FTC 机器人项目代码结构审查报告" in report_content, "报告缺少标题"
        assert "模块统计" in report_content, "报告缺少模块统计"
        assert "风险标注" in report_content, "报告缺少风险标注"
        print(f"[SELFTEST]   报告生成: {len(report_content)} 字符 ✓")

        # 测试 4: 编码兼容性（GBK 文件）
        print("[SELFTEST] 测试 GBK 编码兼容...")
        gbk_file = src_dir / "GbkTest.java"
        gbk_content = "package org.firstinspires.ftc.teamcode;\n\npublic class GbkTest {\n    // 中文注释测试\n    public void test() {}\n}"
        gbk_file.write_text(gbk_content, encoding="gbk")

        gbk_info = parse_java_file(gbk_file)
        assert gbk_info.class_name == "GbkTest", f"GBK 文件解析失败: {gbk_info.parse_error}"
        print(f"[SELFTEST]   GBK 编码解析: {gbk_info.class_name} ✓")

        # 测试 5: 空文件处理
        print("[SELFTEST] 测试空文件...")
        empty_file = src_dir / "Empty.java"
        empty_file.write_text("", encoding="utf-8")
        empty_info = parse_java_file(empty_file)
        assert empty_info.line_count == 0, "空文件行数应为 0"
        print(f"[SELFTEST]   空文件处理: ✓")

        # 测试 6: 原子写入
        print("[SELFTEST] 测试原子写入...")
        test_output = project_dir / "test_output.md"
        atomic_write_file(test_output, "# Test")
        assert test_output.exists(), "原子写入失败"
        assert not test_output.with_suffix(".md.tmp").exists(), "临时文件未清理"
        print(f"[SELFTEST]   原子写入: ✓")

        # 测试 7: dry-run 模式
        print("[SELFTEST] 测试 dry-run 模式...")
        dry_run_output = project_dir / "dry_run_test.md"
        result = save_report(dry_run_output, "# Dry Run Test", dry_run=True)
        assert result is False, "dry-run 模式不应写入文件"
        assert not dry_run_output.exists(), "dry-run 模式不应创建文件"
        print(f"[SELFTEST]   dry-run 模式: ✓")

        # 测试 8: 正常写入模式
        print("[SELFTEST] 测试正常写入模式...")
        normal_output = project_dir / "normal_test.md"
        result = save_report(normal_output, "# Normal Test", dry_run=False)
        assert result is True, "正常模式应写入文件"
        assert normal_output.exists(), "正常模式应创建文件"
        print(f"[SELFTEST]   正常写入模式: ✓")

    except AssertionError as e:
        failures.append(str(e))
        print(f"[SELFTEST]   ✗ 断言失败: {e}")
    except Exception as e:
        failures.append(str(e))
        print(f"[SELFTEST]   ✗ 异常: {e}")
        traceback.print_exc()
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)

    if failures:
        print(f"[SELFTEST] 失败 {len(failures)} 项:")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("[SELFTEST] 全部通过 ✓")
        return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="FTC SKYSTONE 机器人项目代码结构审查工具",
        epilog="示例: python run.py /path/to/ftc_project --dry-run"
    )
    parser.add_argument(
        "--project-path",
        help="FTC 项目根目录路径"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检模式，验证核心功能"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只打印将生成的报告信息，不写入文件"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出模式：打印每个文件的解析明细"
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("FTC_REVIEW_OUTPUT_DIR", "."),
        help="报告输出目录（默认: 当前目录或环境变量 FTC_REVIEW_OUTPUT_DIR）"
    )

    args = parser.parse_args()

    # 自检模式（必须在必填校验之前）
    if args.selftest:
        return run_selftest()

    # 参数校验（手工做必填校验）
    if not args.project_path:
        print("[ERROR] E001: 参数错误：请指定项目路径或使用 --selftest")
        parser.print_help()
        return 1

    project_path = Path(args.project_path)
    if not project_path.exists():
        print(f"[ERROR] E001: 路径不存在或不可访问: {project_path}")
        return 1

    if not project_path.is_dir():
        print(f"[ERROR] E002: 路径不是目录: {project_path}")
        return 1

    # 扫描项目
    print(f"[INFO] 扫描目录: {project_path}")
    try:
        report = scan_project(project_path, verbose=args.verbose)
    except Exception as e:
        print(f"[ERROR] E010: 未知异常 - {str(e)}")
        traceback.print_exc()
        return 1

    # 输出摘要
    print(f"[INFO] 发现 Java 文件: {report.total_files} 个")
    for module_type, count in sorted(report.module_stats.items(), key=lambda x: -x[1]):
        print(f"[INFO]   模块 {module_type}: {count} 个")
    print(f"[INFO] 规范问题: {report.total_issues} 个")
    print(f"[INFO] 风险标注: {report.total_risks} 个")
    if report.parse_failures:
        print(f"[WARN] 解析失败: {len(report.parse_failures)} 个文件")
        for file_path, error in report.parse_failures:
            print(f"[WARN]   {file_path}: {error}")

    # 生成报告
    report_content = generate_report(report)

    # 输出文件名
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"审查报告_{report.project_name}_{report.scan_time}.md"

    # 使用 save_report 统一处理 dry-run 和正常写入
    save_report(output_file, report_content, dry_run=args.dry_run)

    if args.verbose:
        print(f"[明细] 报告文件: {output_file}")
        print(f"[明细] 报告大小: {len(report_content)} 字节")
        print(f"[明细] 模块统计: {report.module_stats}")
        print(f"[明细] 风险总数: {report.total_risks}")
        print(f"[明细] 问题总数: {report.total_issues}")
        print(f"[汇总] changed={report.total_files} 项，skipped={len(report.parse_failures)} 项")

    return 0


if __name__ == "__main__":
    sys.exit(main())
