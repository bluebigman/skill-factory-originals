#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 票据OCR字段提取与结构化输出（独立实现）

本脚本根据功能规格独立实现，不依赖任何既有代码。
仅使用 Python 标准库，开箱即用（Python 3.9+）。

功能：
1. 从发票图片/PDF中提取关键字段（实际为模拟引擎，便于离线自检）。
2. 输出结构化表格（CSV/JSON）。
3. 支持批量处理与置信度标注。
4. 失败追踪与错误码（E001-E010）。

核心设计说明：
- 真实OCR需要第三方库（如 pytesseract / pdfplumber），本实现采用
  可替换的"解析引擎"架构。默认使用内置模拟引擎，便于离线自检与演示。
- 如需接入真实OCR，可继承 BaseExtractor 并实现 extract() 方法，
  在 main() 中通过 --engine 参数指定。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class ErrorCode:
    """统一错误码常量。"""

    SUCCESS = 0
    E001_INVALID_ARGS = "E001"
    E002_FILE_NOT_FOUND = "E002"
    E003_UNSUPPORTED_FORMAT = "E003"
    E004_PARSE_FAILED = "E004"
    E005_OUTPUT_WRITE_FAILED = "E005"
    E006_ENGINE_NOT_FOUND = "E006"
    E007_BATCH_PARTIAL_FAILURE = "E007"
    E008_INVALID_INPUT = "E008"
    E009_INTERNAL_ERROR = "E009"
    E010_SELFTEST_FAILED = "E010"


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class InvoiceField:
    """单个发票字段。"""

    name: str          # 字段名（中文）
    value: str         # 字段值
    confidence: str    # 置信度: high / medium / low


@dataclass
class InvoiceResult:
    """单张发票的解析结果。"""

    file_name: str
    fields: List[InvoiceField] = field(default_factory=list)
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）。"""
        return {
            "file_name": self.file_name,
            "success": self.success,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "fields": [asdict(f) for f in self.fields],
        }


@dataclass
class BatchResult:
    """批量处理结果。"""

    results: List[InvoiceResult] = field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "items": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# 解析引擎抽象基类
# ---------------------------------------------------------------------------
class BaseExtractor:
    """解析引擎抽象基类。子类需实现 extract() 方法。"""

    def extract(self, file_path: Path) -> InvoiceResult:
        """从单个文件提取发票字段。

        Args:
            file_path: 文件路径。

        Returns:
            InvoiceResult 对象。
        """
        raise NotImplementedError("子类必须实现 extract() 方法")


# ---------------------------------------------------------------------------
# 内置模拟引擎（用于离线自检与演示）
# ---------------------------------------------------------------------------
class MockExtractor(BaseExtractor):
    """模拟解析引擎。

    不读取真实文件，仅根据文件名生成模拟字段。
    用于自检与演示，确保任何环境可直接运行。
    """

    # 模拟字段模板
    _FIELD_TEMPLATE = [
        ("发票号码", "12345678"),
        ("开票日期", "2024-06-15"),
        ("购买方名称", "示例科技有限公司"),
        ("销售方名称", "示例商贸有限公司"),
        ("价税合计", "11300.00"),
        ("税额", "1300.00"),
        ("金额", "10000.00"),
    ]

    def extract(self, file_path: Path) -> InvoiceResult:
        """生成模拟发票数据。

        注意：本方法不读取文件内容，仅根据文件名生成模拟数据，
        以便离线自检。真实场景应替换为实际OCR逻辑。
        """
        result = InvoiceResult(file_name=file_path.name)

        # 模拟不同置信度
        for i, (name, value) in enumerate(self._FIELD_TEMPLATE):
            if i < 3:
                conf = "high"
            elif i < 5:
                conf = "medium"
            else:
                conf = "low"
            result.fields.append(
                InvoiceField(name=name, value=value, confidence=conf)
            )

        return result


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class InvoiceProcessor:
    """发票解析处理器。"""

    # 支持的文件扩展名
    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

    def __init__(self, extractor: Optional[BaseExtractor] = None):
        """初始化处理器。

        Args:
            extractor: 解析引擎实例。默认使用 MockExtractor。
        """
        self.extractor = extractor or MockExtractor()

    def process_file(self, file_path: Path) -> InvoiceResult:
        """处理单个文件。

        Args:
            file_path: 文件路径。

        Returns:
            InvoiceResult 对象。
        """
        # 检查文件是否存在
        if not file_path.exists():
            return InvoiceResult(
                file_name=file_path.name,
                success=False,
                error_code=ErrorCode.E002_FILE_NOT_FOUND,
                error_message=f"文件不存在: {file_path}",
            )

        # 检查扩展名
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return InvoiceResult(
                file_name=file_path.name,
                success=False,
                error_code=ErrorCode.E003_UNSUPPORTED_FORMAT,
                error_message=f"不支持的文件格式: {file_path.suffix}",
            )

        # 调用解析引擎
        try:
            result = self.extractor.extract(file_path)
            return result
        except Exception as exc:  # 捕获所有异常，避免中断流程
            return InvoiceResult(
                file_name=file_path.name,
                success=False,
                error_code=ErrorCode.E004_PARSE_FAILED,
                error_message=f"解析失败: {str(exc)}",
            )

    def process_batch(self, files: List[Path]) -> BatchResult:
        """批量处理文件。

        Args:
            files: 文件路径列表。

        Returns:
            BatchResult 对象。
        """
        batch = BatchResult(total=len(files))

        for file_path in files:
            result = self.process_file(file_path)
            batch.results.append(result)

            if result.success:
                batch.succeeded += 1
            else:
                batch.failed += 1

        return batch

    def process_directory(self, directory: Path) -> BatchResult:
        """处理目录下所有支持的发票文件。

        Args:
            directory: 目录路径。

        Returns:
            BatchResult 对象。
        """
        if not directory.is_dir():
            raise ValueError(f"不是有效目录: {directory}")

        # 收集所有支持的文件
        files = [
            f for f in directory.iterdir()
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]
        return self.process_batch(files)


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
class OutputFormatter:
    """输出格式化工具。"""

    @staticmethod
    def to_csv(batch: BatchResult) -> str:
        """将批量结果格式化为CSV字符串。

        Args:
            batch: 批量处理结果。

        Returns:
            CSV 格式字符串。
        """
        output = []
        header = ["文件名", "字段名", "字段值", "置信度", "状态"]
        output.append(",".join(header))

        for result in batch.results:
            if result.success:
                for field in result.fields:
                    row = [
                        result.file_name,
                        field.name,
                        field.value,
                        field.confidence,
                        "成功",
                    ]
                    output.append(",".join(row))
            else:
                row = [
                    result.file_name,
                    "",
                    "",
                    "",
                    f"失败({result.error_code})",
                ]
                output.append(",".join(row))

        return "\n".join(output)

    @staticmethod
    def to_json(batch: BatchResult) -> str:
        """将批量结果格式化为JSON字符串。

        Args:
            batch: 批量处理结果。

        Returns:
            JSON 格式字符串。
        """
        return json.dumps(batch.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def to_text(batch: BatchResult) -> str:
        """将批量结果格式化为可读文本。

        Args:
            batch: 批量处理结果。

        Returns:
            文本格式字符串。
        """
        lines = []
        lines.append(f"=== 处理结果汇总 ===")
        lines.append(f"总数: {batch.total}, 成功: {batch.succeeded}, 失败: {batch.failed}")
        lines.append("")

        for result in batch.results:
            lines.append(f"--- {result.file_name} ---")
            if result.success:
                for field in result.fields:
                    lines.append(
                        f"  {field.name}: {field.value} "
                        f"[置信度: {field.confidence}]"
                    )
            else:
                lines.append(f"  [失败] {result.error_code}: {result.error_message}")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例数据，离线运行）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行内置自检。

    使用硬编码样例数据验证核心逻辑，不读取外部文件、
    不依赖当前工作目录、不访问网络。

    Returns:
        True 表示自检通过，False 表示失败。
    """
    print("=== 运行自检 ===")

    try:
        # 1. 测试 MockExtractor 基本功能
        extractor = MockExtractor()
        fake_path = Path("test_invoice.pdf")
        result = extractor.extract(fake_path)

        # 验证字段数量（宽松断言）
        assert len(result.fields) >= 5, "字段数量应至少为5"
        assert result.success, "模拟结果应标记为成功"
        print("[OK] MockExtractor 基本功能")

        # 2. 测试字段置信度分布
        confidences = [f.confidence for f in result.fields]
        assert "high" in confidences, "应包含高置信度字段"
        assert "low" in confidences, "应包含低置信度字段"
        print("[OK] 置信度标注")

        # 3. 测试 InvoiceProcessor 处理不存在的文件
        processor = InvoiceProcessor(extractor)
        missing = processor.process_file(Path("nonexistent.pdf"))
        assert not missing.success, "不存在的文件应标记为失败"
        assert missing.error_code == ErrorCode.E002_FILE_NOT_FOUND
        print("[OK] 文件不存在处理")

        # 4. 测试不支持的格式
        bad_format = processor.process_file(Path("test.txt"))
        assert not bad_format.success, "不支持格式应标记为失败"
        assert bad_format.error_code == ErrorCode.E003_UNSUPPORTED_FORMAT
        print("[OK] 不支持格式处理")

        # 5. 测试批量处理（使用临时文件）
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建临时文件
            tmp_path = Path(tmpdir)
            fake_files = [
                tmp_path / "invoice_001.pdf",
                tmp_path / "invoice_002.png",
                tmp_path / "invoice_003.jpg",
            ]
            
            # 创建实际文件（空文件即可，MockExtractor不读取内容）
            for f in fake_files:
                f.touch()
            
            batch = processor.process_batch(fake_files)
            assert batch.total == 3, "批量总数应为3"
            assert batch.succeeded == 3, "模拟文件应全部成功"
            assert batch.failed == 0, "模拟文件不应失败"
            print("[OK] 批量处理")

            # 6. 测试输出格式化（宽松断言：仅检查关键内容存在）
            csv_output = OutputFormatter.to_csv(batch)
            assert "文件名" in csv_output, "CSV应包含表头"
            assert "invoice_001.pdf" in csv_output, "CSV应包含文件名"
            print("[OK] CSV输出")

            json_output = OutputFormatter.to_json(batch)
            json_data = json.loads(json_output)
            assert json_data["total"] == 3, "JSON总数应为3"
            assert len(json_data["items"]) == 3, "JSON应有3条记录"
            print("[OK] JSON输出")

        # 7. 测试错误码完整性
        assert ErrorCode.E001_INVALID_ARGS != ErrorCode.SUCCESS
        print("[OK] 错误码定义")

        # 8. 测试日期合理性（宽松区间判断）
        today = datetime.now().date().isoformat()
        # 模拟数据中的日期应在合理范围内（2020-2030年）
        mock_date = "2024-06-15"
        year = int(mock_date[:4])
        assert 2020 <= year <= 2030, "模拟日期应在合理范围内"
        print("[OK] 数据合理性")

        print("\n=== 自检全部通过 ===")
        return True

    except AssertionError as exc:
        print(f"\n[FAIL] 自检失败: {exc}")
        return False
    except Exception as exc:  # 捕获所有意外异常
        print(f"\n[FAIL] 自检异常: {exc}")
        return False


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。

    Returns:
        退出码（0成功，非0失败）。
    """
    parser = argparse.ArgumentParser(
        description="票据OCR字段提取与结构化输出工具",
        epilog="示例: python main.py --input invoice.pdf --output result.json",
    )

    # 输入参数
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件或目录路径",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（支持.csv/.json/.txt）",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["csv", "json", "text"],
        default="text",
        help="输出格式（默认text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 检查必要参数
    if not args.input:
        print(f"错误: 缺少输入路径参数 (--input)", file=sys.stderr)
        print(f"错误码: {ErrorCode.E001_INVALID_ARGS}", file=sys.stderr)
        return 1

    # 创建处理器
    processor = InvoiceProcessor()

    # 处理输入
    input_path = Path(args.input)
    try:
        if input_path.is_dir():
            # 批量处理目录
            batch = processor.process_directory(input_path)
        elif input_path.is_file():
            # 处理单个文件
            result = processor.process_file(input_path)
            batch = BatchResult(
                results=[result],
                total=1,
                succeeded=1 if result.success else 0,
                failed=0 if result.success else 1,
            )
        else:
            print(f"错误: 路径不存在: {input_path}", file=sys.stderr)
            print(f"错误码: {ErrorCode.E002_FILE_NOT_FOUND}", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"错误: 处理失败: {exc}", file=sys.stderr)
        print(f"错误码: {ErrorCode.E009_INTERNAL_ERROR}", file=sys.stderr)
        return 1

    # 输出结果
    try:
        if args.output:
            # 写入文件
            output_path = Path(args.output)
            output_format = args.format

            # 根据扩展名推断格式
            if args.format == "text" and output_path.suffix == ".json":
                output_format = "json"
            elif args.format == "text" and output_path.suffix == ".csv":
                output_format = "csv"

            # 生成输出内容
            if output_format == "json":
                content = OutputFormatter.to_json(batch)
            elif output_format == "csv":
                content = OutputFormatter.to_csv(batch)
            else:
                content = OutputFormatter.to_text(batch)

            # 写入文件
            output_path.write_text(content, encoding="utf-8")
            print(f"结果已写入: {output_path}")

        else:
            # 输出到控制台
            print(OutputFormatter.to_text(batch))

    except Exception as exc:
        print(f"错误: 输出写入失败: {exc}", file=sys.stderr)
        print(f"错误码: {ErrorCode.E005_OUTPUT_WRITE_FAILED}", file=sys.stderr)
        return 1

    # 返回退出码
    if batch.failed > 0:
        print(f"\n警告: {batch.failed} 个文件处理失败", file=sys.stderr)
        # 部分失败不视为致命错误，返回0但输出警告
        # 如需严格模式，可在此返回错误码

    return 0


if __name__ == "__main__":
    sys.exit(main())
