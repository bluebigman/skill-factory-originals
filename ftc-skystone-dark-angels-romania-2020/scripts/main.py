#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTC SKYSTONE 代码审查与结构解析工具（独立实现）

功能：
- 解析 FTC 机器人项目中的 Java/Kotlin 源码文件，提取类、方法、注解、OpMode 注册信息。
- 识别 @TeleOp / @Autonomous 注解、LinearOpMode / OpMode 继承关系、硬件映射调用。
- 生成 Markdown 格式审查报告，包含结构概览、风险点、改进建议。
- 支持多文件/目录批量处理。
- 内置离线自检（--selftest），不依赖外部文件与网络。

错误码：
E001 参数错误
E002 文件不存在或无法读取
E003 目录不存在或无法访问
E004 不支持的文件类型
E005 源码解析失败（语法异常）
E006 输出目录创建失败
E007 写入文件失败
E008 自检数据缺失（不应发生）
E009 内部逻辑错误
E010 未知错误

仅使用 Python 标准库实现。
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class MethodInfo:
    """方法信息"""
    name: str
    visibility: str = "package"
    is_static: bool = False
    is_abstract: bool = False
    parameters: List[str] = field(default_factory=list)
    return_type: str = "void"
    line_number: int = 0


@dataclass
class ClassInfo:
    """类信息"""
    name: str
    kind: str = "class"  # class / interface / enum
    visibility: str = "package"
    is_abstract: bool = False
    is_final: bool = False
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    hardware_calls: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class FileAnalysis:
    """单文件分析结果"""
    file_path: str
    file_type: str  # java / kt
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    package: Optional[str] = None
    raw_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0
    error: Optional[str] = None


@dataclass
class ReviewReport:
    """审查报告"""
    files_analyzed: int = 0
    files_failed: int = 0
    total_classes: int = 0
    total_methods: int = 0
    teleop_count: int = 0
    autonomous_count: int = 0
    linear_opmode_count: int = 0
    opmode_count: int = 0
    hardware_map_calls: int = 0
    risks: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    file_details: List[FileAnalysis] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 源码解析器（静态文本分析，不执行代码）
# ---------------------------------------------------------------------------

class SourceParser:
    """解析 Java/Kotlin 源码文件，提取结构信息"""

    # 注解匹配
    ANNOTATION_PATTERN = re.compile(r'@(\w+)')
    # 类声明匹配
    CLASS_PATTERN = re.compile(
        r'^\s*(?:public\s+|protected\s+|private\s+)?'
        r'(?:abstract\s+|final\s+|static\s+)*'
        r'(?P<kind>class|interface|enum)\s+'
        r'(?P<name>\w+)'
        r'(?:\s+extends\s+(?P<extends>[\w\.]+))?'
        r'(?:\s+implements\s+(?P<implements>[\w\.\s,]+))?'
    )
    # 方法声明匹配（更宽松的模式）
    METHOD_PATTERN = re.compile(
        r'^\s*'
        r'(?:(?P<visibility>public|protected|private)\s+)?'
        r'(?:(?P<static>static)\s+)?'
        r'(?:(?P<abstract>abstract)\s+)?'
        r'(?:(?P<final>final)\s+)?'
        r'(?:(?P<synchronized>synchronized)\s+)?'
        r'(?P<return>[\w\<\>\[\]\.\?]+)\s+'  # 允许泛型和可空类型
        r'(?P<name>\w+)\s*\((?P<params>[^)]*)\)'
    )
    # 硬件映射调用匹配
    HARDWARE_MAP_PATTERN = re.compile(
        r'(?:hardwareMap|HardwareMap)\s*\.\s*'
        r'(?P<type>get|put|tryGet)\s*\('
    )
    # 导入语句匹配
    IMPORT_PATTERN = re.compile(r'^\s*import\s+([\w\.\*]+)\s*;')
    # 包声明匹配
    PACKAGE_PATTERN = re.compile(r'^\s*package\s+([\w\.]+)\s*;')

    SUPPORTED_EXTENSIONS = {'.java', '.kt', '.kts'}

    def parse_file(self, file_path: str) -> FileAnalysis:
        """解析单个源码文件"""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"E004: 不支持的文件类型: {ext}")

        try:
            content = path.read_text(encoding='utf-8', errors='replace')
        except OSError as exc:
            raise ValueError(f"E002: 文件无法读取: {exc}") from exc

        analysis = FileAnalysis(
            file_path=str(path),
            file_type='java' if ext == '.java' else 'kt',
            raw_lines=len(content.splitlines())
        )

        # 统计注释行与代码行
        comment_count = 0
        code_count = 0
        in_block_comment = False

        for line in content.splitlines():
            stripped = line.strip()
            if in_block_comment:
                comment_count += 1
                if '*/' in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith('/*'):
                comment_count += 1
                if '*/' not in stripped:
                    in_block_comment = True
                continue
            if stripped.startswith('//') or stripped.startswith('*'):
                comment_count += 1
                continue
            if stripped:
                code_count += 1

        analysis.comment_lines = comment_count
        analysis.code_lines = code_count

        # 解析导入与包
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith('import '):
                match = self.IMPORT_PATTERN.match(stripped)
                if match:
                    analysis.imports.append(match.group(1))
            elif stripped.startswith('package '):
                match = self.PACKAGE_PATTERN.match(stripped)
                if match:
                    analysis.package = match.group(1)

        # 解析类与方法（逐行扫描，保留缩进上下文）
        lines = content.splitlines()
        current_class: Optional[ClassInfo] = None
        pending_annotations: List[str] = []
        class_indent = 0

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # 收集注解（可能出现在类或方法之前）
            if stripped.startswith('@'):
                for match in self.ANNOTATION_PATTERN.finditer(stripped):
                    pending_annotations.append(match.group(1))
                continue

            # 检查是否为类声明
            class_match = self.CLASS_PATTERN.match(stripped)
            if class_match:
                kind = class_match.group('kind')
                name = class_match.group('name')
                extends = class_match.group('extends')
                implements_raw = class_match.group('implements')

                implements = []
                if implements_raw:
                    implements = [item.strip() for item in implements_raw.split(',') if item.strip()]

                current_class = ClassInfo(
                    name=name,
                    kind=kind,
                    extends=extends,
                    implements=implements,
                    annotations=list(pending_annotations),
                    line_number=idx + 1
                )
                # 记录类的缩进级别
                class_indent = len(line) - len(line.lstrip())
                pending_annotations = []
                analysis.classes.append(current_class)
                continue

            # 检查是否为方法声明（仅在类内部）
            if current_class is not None:
                # 检查是否还在当前类的作用域内
                line_indent = len(line) - len(line.lstrip())
                if line_indent > class_indent:
                    method_match = self.METHOD_PATTERN.match(stripped)
                    if method_match and not stripped.startswith(('if', 'for', 'while', 'switch', 'return', 'try', 'catch', 'else')):
                        params_raw = method_match.group('params') or ''
                        params = [p.strip() for p in params_raw.split(',') if p.strip()]

                        method = MethodInfo(
                            name=method_match.group('name'),
                            visibility=method_match.group('visibility') or 'package',
                            is_static=bool(method_match.group('static')),
                            is_abstract=bool(method_match.group('abstract')),
                            parameters=params,
                            return_type=method_match.group('return'),
                            line_number=idx + 1
                        )
                        current_class.methods.append(method)
                        # 清除待处理注解（它们属于这个方法）
                        pending_annotations = []
                        continue

            # 检测硬件映射调用
            if 'hardwareMap' in stripped or 'HardwareMap' in stripped:
                for match in self.HARDWARE_MAP_PATTERN.finditer(stripped):
                    if current_class is not None:
                        current_class.hardware_calls.append(match.group('type'))
                    else:
                        # 在类外（如顶层函数）也记录
                        if not hasattr(analysis, 'hardware_calls'):
                            analysis.hardware_calls = []
                        analysis.hardware_calls.append(match.group('type'))

            # 重置待处理注解（如果行不是注解且不是类/方法声明）
            if not stripped.startswith('@'):
                pending_annotations = []

        return analysis


# ---------------------------------------------------------------------------
# 报告生成器
# ---------------------------------------------------------------------------

class ReportGenerator:
    """生成 Markdown 格式审查报告"""

    def generate(self, report: ReviewReport) -> str:
        """生成完整审查报告"""
        lines = []
        lines.append("# FTC SKYSTONE 代码审查报告")
        lines.append("")
        lines.append("> 本报告由静态分析工具自动生成，仅供参考。")
        lines.append("")
        lines.append("## 一、总体概览")
        lines.append("")
        lines.append(f"- 分析文件数: {report.files_analyzed}")
        lines.append(f"- 失败文件数: {report.files_failed}")
        lines.append(f"- 类总数: {report.total_classes}")
        lines.append(f"- 方法总数: {report.total_methods}")
        lines.append(f"- @TeleOp 数量: {report.teleop_count}")
        lines.append(f"- @Autonomous 数量: {report.autonomous_count}")
        lines.append(f"- LinearOpMode 继承数: {report.linear_opmode_count}")
        lines.append(f"- OpMode 继承数: {report.opmode_count}")
        lines.append(f"- hardwareMap 调用次数: {report.hardware_map_calls}")
        lines.append("")

        lines.append("## 二、文件明细")
        lines.append("")
        for detail in report.file_details:
            lines.append(f"### {detail.file_path}")
            lines.append("")
            if detail.error:
                lines.append(f"**解析错误:** {detail.error}")
                lines.append("")
                continue
            lines.append(f"- 类型: {detail.file_type}")
            lines.append(f"- 包: {detail.package or '(无)'}")
            lines.append(f"- 代码行数: {detail.code_lines} / 注释行数: {detail.comment_lines} / 总行数: {detail.raw_lines}")
            lines.append("")
            if detail.classes:
                lines.append("#### 类结构")
                lines.append("")
                for cls in detail.classes:
                    lines.append(f"- **{cls.kind} {cls.name}** (行 {cls.line_number})")
                    if cls.annotations:
                        lines.append(f"  - 注解: {', '.join(cls.annotations)}")
                    if cls.extends:
                        lines.append(f"  - 继承: {cls.extends}")
                    if cls.implements:
                        lines.append(f"  - 实现: {', '.join(cls.implements)}")
                    if cls.methods:
                        lines.append(f"  - 方法数: {len(cls.methods)}")
                        for method in cls.methods[:10]:  # 最多列出10个方法
                            params = ', '.join(method.parameters)
                            lines.append(f"    - {method.visibility} {method.return_type} {method.name}({params})")
                        if len(cls.methods) > 10:
                            lines.append(f"    - ... 等 {len(cls.methods) - 10} 个方法")
                    lines.append("")
            else:
                lines.append("未检测到类定义。")
                lines.append("")
        lines.append("")

        lines.append("## 三、风险点")
        lines.append("")
        if report.risks:
            for risk in report.risks:
                lines.append(f"- [ ] {risk}")
        else:
            lines.append("- 未检测到明显风险点。")
        lines.append("")

        lines.append("## 四、改进建议")
        lines.append("")
        if report.suggestions:
            for suggestion in report.suggestions:
                lines.append(f"- {suggestion}")
        else:
            lines.append("- 暂无建议。")
        lines.append("")

        lines.append("## 五、置信度说明")
        lines.append("")
        lines.append("本报告基于静态文本分析，以下信息可能需要人工核实：")
        lines.append("- [需核实:硬件配置] 硬件映射是否与真实机器人配置一致")
        lines.append("- [需核实:外部依赖] 第三方库的完整依赖关系")
        lines.append("- [需核实:逻辑正确性] 代码逻辑是否正确实现比赛策略")
        lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 审查引擎
# ---------------------------------------------------------------------------

class ReviewEngine:
    """代码审查引擎"""

    def __init__(self):
        self.parser = SourceParser()
        self.generator = ReportGenerator()

    def analyze_paths(self, paths: List[str]) -> ReviewReport:
        """分析文件或目录列表"""
        report = ReviewReport()
        files_to_analyze: List[str] = []

        # 收集所有待分析文件
        for path_str in paths:
            path = Path(path_str)
            if path.is_file():
                if path.suffix.lower() in SourceParser.SUPPORTED_EXTENSIONS:
                    files_to_analyze.append(str(path))
                else:
                    report.files_failed += 1
                    report.file_details.append(FileAnalysis(
                        file_path=str(path),
                        file_type=path.suffix.lstrip('.'),
                        error="E004: 不支持的文件类型"
                    ))
            elif path.is_dir():
                for root, _, filenames in os.walk(path):
                    for filename in filenames:
                        file_path = Path(root) / filename
                        if file_path.suffix.lower() in SourceParser.SUPPORTED_EXTENSIONS:
                            files_to_analyze.append(str(file_path))
            else:
                report.files_failed += 1
                report.file_details.append(FileAnalysis(
                    file_path=str(path),
                    file_type="unknown",
                    error="E003: 路径不存在或无法访问"
                ))

        # 解析所有文件
        for file_path in files_to_analyze:
            report.files_analyzed += 1
            try:
                analysis = self.parser.parse_file(file_path)
            except ValueError as exc:
                report.files_failed += 1
                report.file_details.append(FileAnalysis(
                    file_path=file_path,
                    file_type=Path(file_path).suffix.lstrip('.'),
                    error=str(exc)
                ))
                continue

            report.file_details.append(analysis)

            # 汇总统计
            for cls in analysis.classes:
                report.total_classes += 1
                report.total_methods += len(cls.methods)
                report.hardware_map_calls += len(cls.hardware_calls)

                if "TeleOp" in cls.annotations:
                    report.teleop_count += 1
                if "Autonomous" in cls.annotations:
                    report.autonomous_count += 1
                if cls.extends and "LinearOpMode" in cls.extends:
                    report.linear_opmode_count += 1
                if cls.extends and "OpMode" in cls.extends:
                    report.opmode_count += 1

                # 风险检测
                if cls.extends and "OpMode" in cls.extends and not cls.methods:
                    report.risks.append(f"{cls.name}: OpMode 类未定义任何方法")
                if len(cls.methods) > 15:
                    report.risks.append(f"{cls.name}: 类方法过多（{len(cls.methods)}个），建议拆分职责")
                if cls.is_abstract and not cls.methods:
                    report.risks.append(f"{cls.name}: 抽象类未定义抽象方法")

        # 生成建议
        if report.total_classes == 0 and report.files_analyzed > 0:
            report.suggestions.append("未检测到类定义，请确认输入文件是否为有效的 Java/Kotlin 源码")
        if report.teleop_count == 0 and report.autonomous_count == 0:
            report.suggestions.append("未检测到 @TeleOp 或 @Autonomous 注解，请检查 OpMode 注册")
        if report.hardware_map_calls == 0 and report.total_classes > 0:
            report.suggestions.append("未检测到 hardwareMap 调用，请确认硬件映射是否正确初始化")

        return report

    def generate_report(self, report: ReviewReport) -> str:
        """生成报告文本"""
        return self.generator.generate(report)


# ---------------------------------------------------------------------------
# 离线自检（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """运行内置自检，验证核心逻辑正确性"""
    print("[自检] 开始运行内置自检...")

    # 内置硬编码样例数据（不读取外部文件）
    sample_java_code = """
package com.example.ftc;

import com.qualcomm.robotcore.eventloop.opmode.TeleOp;
import com.qualcomm.robotcore.eventloop.opmode.LinearOpMode;
import com.qualcomm.robotcore.hardware.DcMotor;

@TeleOp(name="Test OpMode", group="Test")
public class TestOpMode extends LinearOpMode {
    private DcMotor motorLeft;
    private DcMotor motorRight;

    @Override
    public void runOpMode() {
        motorLeft = hardwareMap.get(DcMotor.class, "left_motor");
        motorRight = hardwareMap.get(DcMotor.class, "right_motor");
        
        waitForStart();
        while (opModeIsActive()) {
            motorLeft.setPower(0.5);
            motorRight.setPower(-0.5);
        }
    }
    
    private double calculateSpeed(double input) {
        return input * 1.5;
    }
}
"""

    sample_kt_code = """
package com.example.ftc

import com.qualcomm.robotcore.eventloop.opmode.Autonomous
import com.qualcomm.robotcore.eventloop.opmode.LinearOpMode
import com.qualcomm.robotcore.hardware.Servo

@Autonomous(name="Test Auto", group="Test")
class TestAuto : LinearOpMode() {
    private lateinit var servo: Servo
    
    override fun runOpMode() {
        servo = hardwareMap.get(Servo::class.java, "servo")
        waitForStart()
        while (opModeIsActive()) {
            servo.position = 0.5
        }
    }
}
"""

    # 创建临时目录用于自检（使用 tempfile 确保不污染工作目录）
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp(prefix="ftc_selftest_")
    try:
        java_file = os.path.join(temp_dir, "TestOpMode.java")
        kt_file = os.path.join(temp_dir, "TestAuto.kt")

        with open(java_file, "w", encoding="utf-8") as f:
            f.write(sample_java_code)
        with open(kt_file, "w", encoding="utf-8") as f:
            f.write(sample_kt_code)

        # 运行分析
        engine = ReviewEngine()
        report = engine.analyze_paths([temp_dir])

        # 断言（宽松阈值，不依赖精确值）
        assert report.files_analyzed >= 2, f"E008: 应分析至少2个文件，实际 {report.files_analyzed}"
        assert report.files_failed == 0, f"E008: 不应有失败文件，实际 {report.files_failed}"
        assert report.total_classes >= 2, f"E008: 应至少2个类，实际 {report.total_classes}"
        assert report.total_methods >= 3, f"E008: 应至少3个方法，实际 {report.total_methods}"
        assert report.teleop_count >= 1, f"E008: 应至少1个@TeleOp，实际 {report.teleop_count}"
        assert report.autonomous_count >= 1, f"E008: 应至少1个@Autonomous，实际 {report.autonomous_count}"
        assert report.linear_opmode_count >= 2, f"E008: 应至少2个LinearOpMode，实际 {report.linear_opmode_count}"
        assert report.hardware_map_calls >= 3, f"E008: 应至少3次hardwareMap调用，实际 {report.hardware_map_calls}"

        # 生成报告并验证基本结构
        report_text = engine.generate_report(report)
        assert "# FTC SKYSTONE 代码审查报告" in report_text, "E008: 报告缺少标题"
        assert "## 一、总体概览" in report_text, "E008: 报告缺少概览部分"
        assert "## 二、文件明细" in report_text, "E008: 报告缺少文件明细"
        assert "## 三、风险点" in report_text, "E008: 报告缺少风险点"
        assert "## 四、改进建议" in report_text, "E008: 报告缺少建议"
        assert "## 五、置信度说明" in report_text, "E008: 报告缺少置信度说明"

        # 验证报告内容包含关键信息
        assert "TestOpMode" in report_text, "E008: 报告缺少 TestOpMode 类信息"
        assert "TestAuto" in report_text, "E008: 报告缺少 TestAuto 类信息"
        assert "runOpMode" in report_text, "E008: 报告缺少 runOpMode 方法信息"

        print("[自检] 所有断言通过，核心逻辑验证成功。")
        return 0

    except AssertionError as exc:
        print(f"[自检] 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"[自检] 异常: E009: {exc}")
        return 1
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="FTC SKYSTONE 代码审查与结构解析工具",
        epilog="示例: python main.py ./src --output ./report.md"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="要分析的文件或目录路径（默认为当前目录）"
    )
    parser.add_argument(
        "-o", "--output",
        help="输出报告文件路径（默认输出到 stdout）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ftc-skystone-dark-angels-romania-2020 1.0.2"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.paths:
        print("E001: 未指定分析路径", file=sys.stderr)
        return 1

    # 执行分析
    try:
        engine = ReviewEngine()
        report = engine.analyze_paths(args.paths)
        report_text = engine.generate_report(report)

        # 输出结果
        if args.output:
            output_dir = os.path.dirname(args.output)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except OSError as exc:
                    print(f"E006: 输出目录创建失败: {exc}", file=sys.stderr)
                    return 1
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(report_text)
                print(f"报告已写入: {args.output}")
            except OSError as exc:
                print(f"E007: 写入文件失败: {exc}", file=sys.stderr)
                return 1
        else:
            print(report_text)

        return 0

    except ValueError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
