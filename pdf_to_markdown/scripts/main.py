#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_to_markdown - 将PDF批量转为带表格结构的Markdown文档，保留原始布局。

本脚本为 Clean-Room 独立实现，仅依据功能规格编写，不包含任何既有代码。
版本: 2.0.4 | 许可证: MIT
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入路径不存在或无法访问",
    "E002": "输入路径不是目录且不是PDF文件",
    "E003": "PDF文件无法读取或已损坏",
    "E004": "PDF文件为加密文件，无法处理",
    "E005": "PDF文件为纯图片型（无文字层），需先OCR预处理",
    "E006": "输出目录无法创建或不可写",
    "E007": "文件写入失败",
    "E008": "PDF解析过程中发生未知错误",
    "E009": "命令行参数不合法",
    "E010": "内部逻辑错误（自检失败）",
}


class PDFConverterError(Exception):
    """PDF转换过程中的自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据模型：PDF文本行与表格单元
# ============================================================

class TextLine:
    """表示PDF中的一行文本，包含位置信息。"""

    def __init__(self, text: str, x0: float = 0.0, y0: float = 0.0,
                 x1: float = 0.0, y1: float = 0.0):
        self.text = text.strip()
        self.x0 = x0  # 左下角x
        self.y0 = y0  # 左下角y
        self.x1 = x1  # 右上角x
        self.y1 = y1  # 右上角y

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2.0


class TableCell:
    """表格中的一个单元格。"""

    def __init__(self, text: str, col_start: int, col_end: int,
                 row_start: int, row_end: int):
        self.text = text.strip()
        self.col_start = col_start
        self.col_end = col_end
        self.row_start = row_start
        self.row_end = row_end

    def __repr__(self):
        return f"TableCell(text='{self.text}', cols=[{self.col_start}-{self.col_end}], rows=[{self.row_start}-{self.row_end}])"


# ============================================================
# 表格识别与还原（核心逻辑）
# ============================================================

class TableDetector:
    """基于文本行位置信息识别表格结构。"""

    # 列对齐容差（像素）
    COL_TOLERANCE = 5.0
    # 行合并容差
    ROW_TOLERANCE = 3.0

    def __init__(self, lines: List[TextLine]):
        self.lines = [line for line in lines if line.text]
        self.columns: List[float] = []  # 每列的x中心位置
        self.rows: List[float] = []     # 每行的y中心位置
        self.cells: List[TableCell] = []
        self._detect()

    def _detect(self):
        """检测表格结构。"""
        if not self.lines:
            return

        # 1. 按x坐标聚类，识别列边界
        x_centers = sorted([line.center_x for line in self.lines])
        self.columns = self._cluster_centers(x_centers, self.COL_TOLERANCE)

        # 2. 按y坐标聚类，识别行边界
        y_centers = sorted([line.center_y for line in self.lines], reverse=True)
        self.rows = self._cluster_centers(y_centers, self.ROW_TOLERANCE)

        # 3. 将文本行分配到单元格
        self._assign_cells()

    def _cluster_centers(self, values: List[float], tolerance: float) -> List[float]:
        """一维聚类：将相近的值聚合为簇，返回簇中心。"""
        if not values:
            return []

        clusters: List[List[float]] = [[values[0]]]
        for val in values[1:]:
            if abs(val - clusters[-1][-1]) <= tolerance:
                clusters[-1].append(val)
            else:
                clusters.append([val])

        # 返回每个簇的平均值
        return [sum(cluster) / len(cluster) for cluster in clusters]

    def _find_column_index(self, x: float) -> int:
        """找到最接近x的列索引。"""
        if not self.columns:
            return 0
        distances = [abs(x - col) for col in self.columns]
        return distances.index(min(distances))

    def _find_row_index(self, y: float) -> int:
        """找到最接近y的行索引。"""
        if not self.rows:
            return 0
        distances = [abs(y - row) for row in self.rows]
        return distances.index(min(distances))

    def _assign_cells(self):
        """将文本行分配到单元格。"""
        if not self.columns or not self.rows:
            # 无法识别行列，将所有文本作为一个单元格
            all_text = "\n".join(line.text for line in self.lines)
            if all_text:
                self.cells.append(TableCell(all_text, 0, 0, 0, 0))
            return

        # 创建二维单元格映射
        grid: Dict[Tuple[int, int], List[str]] = {}
        for line in self.lines:
            col_idx = self._find_column_index(line.center_x)
            row_idx = self._find_row_index(line.center_y)
            key = (col_idx, row_idx)
            if key not in grid:
                grid[key] = []
            grid[key].append(line.text)

        # 转换为TableCell对象
        for (col_idx, row_idx), texts in grid.items():
            cell_text = "\n".join(texts)
            self.cells.append(TableCell(cell_text, col_idx, col_idx, row_idx, row_idx))

    def to_markdown_table(self) -> Optional[str]:
        """生成Markdown表格语法。"""
        if not self.cells or not self.columns or not self.rows:
            return None

        # 构建二维数组
        n_cols = len(self.columns)
        n_rows = len(self.rows)
        table = [["" for _ in range(n_cols)] for _ in range(n_rows)]

        for cell in self.cells:
            row = cell.row_start
            col = cell.col_start
            if 0 <= row < n_rows and 0 <= col < n_cols:
                table[row][col] = cell.text

        # 过滤空行
        non_empty_rows = [r for r in table if any(cell.strip() for cell in r)]
        if not non_empty_rows:
            return None

        # 生成Markdown
        lines = []
        header = non_empty_rows[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * n_cols) + " |")
        for row in non_empty_rows[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)


# ============================================================
# PDF解析（简化实现，实际项目可替换为pypdf/pdfplumber）
# ============================================================

def parse_pdf_simple(pdf_path: Path) -> List[TextLine]:
    """
    从PDF中提取文本行。

    注意：此实现为简化版，仅处理纯文本PDF。
    实际使用时可替换为 pdfplumber（pip install pdfplumber）等库。
    """
    try:
        data = pdf_path.read_bytes()
    except Exception as exc:
        raise PDFConverterError("E003", f"无法读取PDF文件: {exc}") from exc

    # 检查是否为PDF文件
    if not data.startswith(b"%PDF"):
        raise PDFConverterError("E003", "文件不是有效的PDF格式")

    # 检查是否加密（简单检测）
    if b"/Encrypt" in data[:2000]:
        raise PDFConverterError("E004", "PDF文件已加密，请先解密后再处理")

    # 尝试提取文本（简化：从流中提取可打印ASCII/Unicode字符）
    text_content = []
    try:
        # 提取所有文本流中的可读内容
        content = data.decode("latin-1", errors="ignore")
        # 查找文本流对象
        text_pattern = re.findall(r"\((.*?)\)", content)
        for match in text_pattern:
            clean = match.encode("latin-1").decode("utf-8", errors="ignore")
            clean = clean.replace("\\n", "\n").replace("\\r", "\n")
            if clean.strip():
                text_content.append(clean)
    except Exception:
        # 如果解码失败，可能为纯图片PDF
        raise PDFConverterError("E005", "PDF中未检测到文本层，可能为纯图片型PDF")

    if not text_content:
        raise PDFConverterError("E005", "PDF中未检测到文本内容")

    # 转换为TextLine对象（简化：无位置信息时使用估算位置）
    lines = []
    y_pos = 100.0
    for text in text_content:
        for line in text.split("\n"):
            if line.strip():
                # 估算位置（实际项目应从PDF中读取精确坐标）
                lines.append(TextLine(line, x0=0, y0=y_pos, x1=len(line) * 5, y1=y_pos + 10))
                y_pos -= 12.0

    return lines


# ============================================================
# Markdown生成与文件处理
# ============================================================

def generate_markdown(lines: List[TextLine]) -> str:
    """从文本行生成Markdown文档。"""
    # 检测表格
    detector = TableDetector(lines)
    table_md = detector.to_markdown_table()

    if table_md:
        return table_md

    # 无表格时，按段落生成
    paragraphs = []
    current = []
    for line in lines:
        if line.text.strip():
            current.append(line.text.strip())
        else:
            if current:
                paragraphs.append(" ".join(current))
                current = []
    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def process_pdf_file(pdf_path: Path, output_dir: Path) -> Dict:
    """处理单个PDF文件，返回结果记录。"""
    result = {
        "file": pdf_path.name,
        "status": "success",
        "output": "",
        "error": None,
    }

    try:
        # 解析PDF
        lines = parse_pdf_simple(pdf_path)

        # 生成Markdown
        markdown_content = generate_markdown(lines)

        # 写入输出文件
        output_file = output_dir / (pdf_path.stem + ".md")
        try:
            if not dry_run or getattr(args, "force", False):
                output_file.write_text(markdown_content, encoding="utf-8")
            result["output"] = str(output_file)
        except Exception as exc:
            raise PDFConverterError("E007", f"写入文件失败: {exc}") from exc

    except PDFConverterError as exc:
        result["status"] = "failed"
        result["error"] = exc.code
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = "E008"

    return result


def process_directory(input_dir: Path, output_dir: Path) -> List[Dict]:
    """批量处理目录中的所有PDF文件。"""
    results = []
    pdf_files = list(input_dir.glob("*.pdf")) + list(input_dir.glob("*.PDF"))

    if not pdf_files:
        raise PDFConverterError("E002", "目录中未找到PDF文件")

    for pdf_file in pdf_files:
        result = process_pdf_file(pdf_file, output_dir)
        results.append(result)

    # 生成错误日志
    error_log = [r for r in results if r["status"] == "failed"]
    if error_log:
        log_file = output_dir / "error_log.json"
        try:
            if not dry_run or getattr(args, "force", False):
                log_file.write_text(json.dumps(error_log, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出  # 日志写入失败不阻塞主流程

    return results


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> bool:
    """内置硬编码样例数据进行离线自检，不依赖外部文件。"""
    test_cases = [
        # 测试用例1：表格数据
        {
            "name": "表格还原测试",
            "lines": [
                TextLine("日期", x0=0, y0=100, x1=50, y1=110),
                TextLine("金额", x0=60, y0=100, x1=110, y1=110),
                TextLine("备注", x0=120, y0=100, x1=170, y1=110),
                TextLine("2024-01-01", x0=0, y0=88, x1=50, y1=98),
                TextLine("100.00", x0=60, y0=88, x1=110, y1=98),
                TextLine("收入", x0=120, y0=88, x1=170, y1=98),
                TextLine("2024-01-02", x0=0, y0=76, x1=50, y1=86),
                TextLine("50.00", x0=60, y0=76, x1=110, y1=86),
                TextLine("支出", x0=120, y0=76, x1=170, y1=86),
            ],
            "check": lambda md: "|" in md and "---" in md and "日期" in md,
        },
        # 测试用例2：段落文本
        {
            "name": "段落文本测试",
            "lines": [
                TextLine("这是第一段文本。", x0=0, y0=100, x1=200, y1=110),
                TextLine("", x0=0, y0=98, x1=0, y1=98),
                TextLine("这是第二段文本，包含一些内容。", x0=0, y0=86, x1=250, y1=96),
            ],
            "check": lambda md: "第一段" in md and "第二段" in md,
        },
        # 测试用例3：空输入
        {
            "name": "空输入测试",
            "lines": [],
            "check": lambda md: md == "",
        },
    ]

    all_passed = True
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    for idx, case in enumerate(test_cases, 1):
        try:
            md_content = generate_markdown(case["lines"])
            passed = case["check"](md_content)
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] 用例{idx}: {case['name']}")
            if not passed:
                print(f"        生成的Markdown: {repr(md_content)}")
                all_passed = False
        except Exception as exc:
            print(f"  [FAIL] 用例{idx}: {case['name']} - 异常: {exc}")
            all_passed = False

    # 测试错误处理
    print("-" * 60)
    print("测试错误处理...")

    # 测试不存在的文件
    try:
        parse_pdf_simple(Path("/nonexistent/file.pdf"))
        print("  [FAIL] 错误处理: 未抛出异常")
        all_passed = False
    except PDFConverterError as exc:
        print(f"  [PASS] 错误处理: 正确抛出 {exc.code}")

    # 测试非PDF文件
    try:
        temp_file = Path("test_not_pdf.txt")
        if not dry_run or getattr(args, "force", False):
            temp_file.write_text("This is not a PDF", encoding="utf-8")
        try:
            parse_pdf_simple(temp_file)
            print("  [FAIL] 错误处理: 非PDF文件未抛出异常")
            all_passed = False
        except PDFConverterError as exc:
            print(f"  [PASS] 错误处理: 非PDF文件正确抛出 {exc.code}")
        finally:
            temp_file.unlink()
    except Exception:
        print("  [WARN] 错误处理: 临时文件测试失败，跳过")

    print("=" * 60)
    if all_passed:
        print("自检全部通过！")
    else:
        print("自检存在失败项！")
    print("=" * 60)

    return all_passed


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="将PDF批量转为带表格结构的Markdown文档",
        epilog="示例: python main.py input_dir output_dir --selftest"
    )
    parser.add_argument(
        "--input", nargs="?", default=None,
        help="输入路径（目录或PDF文件）"
    )
    parser.add_argument(
        "--output", nargs="?", default="output",
        help="输出目录（默认: ./output）"
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行内置自检（不处理实际文件）"
    )
    parser.add_argument(
        "--version", action="version", version="pdf_to_markdown 2.0.4"
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 校验参数
    if not args.input:
        print("错误: 必须指定输入路径", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)

    # 处理输入路径
    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        # 检查输入路径
        if not input_path.exists():
            raise PDFConverterError("E001")

        # 创建输出目录
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise PDFConverterError("E006", f"无法创建输出目录: {exc}") from exc

        # 处理文件或目录
        if input_path.is_dir():
            print(f"批量处理目录: {input_path}")
            results = process_directory(input_path, output_path)
        elif input_path.is_file() and input_path.suffix.lower() == ".pdf":
            print(f"处理单个PDF: {input_path}")
            result = process_pdf_file(input_path, output_path)
            results = [result]
        else:
            raise PDFConverterError("E002")

        # 输出结果摘要
        success_count = sum(1 for r in results if r["status"] == "success")
        fail_count = len(results) - success_count

        print(f"\n处理完成: 成功 {success_count} 个, 失败 {fail_count} 个")
        for r in results:
            if r["status"] == "success":
                print(f"  ✓ {r['file']} → {r['output']}")
            else:
                print(f"  ✗ {r['file']} → 错误码 {r['error']}")

        if fail_count > 0:
            print(f"\n失败详情已记录到 {output_path / 'error_log.json'}")

    except PDFConverterError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
