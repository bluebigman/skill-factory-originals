#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel表格处理 - 图片提取工具

功能：从 Excel 单元格中提取嵌入的图片，并保存到指定目录。
本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import os
import sys
import zipfile
import re
import shutil
from pathlib import Path


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的 Excel 文件路径",
    "E002": "关键信息缺失，请提供输出目录",
    "E003": "输入格式错误，文件不是有效的 Excel 文件",
    "E004": "超出能力边界，无法处理该类型文件",
    "E005": "置信度过低，结果可能不准确",
    "E006": "文件不存在或无法访问",
    "E007": "输出目录创建失败",
    "E008": "Excel 文件中未找到图片",
    "E009": "图片提取过程中发生错误",
    "E010": "参数错误，请检查命令行参数",
}


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出程序"""
    message = ERROR_CODES.get(code, "未知错误")
    if detail:
        message = f"{message}：{detail}"
    print(f"[错误 {code}] {message}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 核心功能：从 Excel 中提取图片
# ============================================================
def extract_images_from_excel(excel_path: str, output_dir: str) -> list:
    """
    从 Excel 文件中提取所有嵌入的图片

    Excel 文件本质上是 ZIP 压缩包，图片通常存储在
    xl/media/ 目录下。

    参数:
        excel_path: Excel 文件路径
        output_dir: 图片输出目录

    返回:
        提取的图片文件路径列表

    错误码:
        E001: 输入为空
        E006: 文件不存在
        E003: 不是有效的 Excel 文件
        E008: 未找到图片
        E009: 提取过程错误
    """
    # 检查输入
    if not excel_path:
        error_exit("E001")
    if not os.path.exists(excel_path):
        error_exit("E006", f"文件不存在: {excel_path}")

    # 检查是否为有效的 Excel 文件（ZIP 格式）
    if not zipfile.is_zipfile(excel_path):
        error_exit("E003", f"不是有效的 Excel 文件: {excel_path}")

    # 创建输出目录
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        error_exit("E007", f"无法创建输出目录: {str(e)}")

    extracted_files = []

    try:
        with zipfile.ZipFile(excel_path, "r") as zip_ref:
            # 查找所有图片文件
            media_files = [
                name for name in zip_ref.namelist()
                if name.startswith("xl/media/") and not name.endswith("/")
            ]

            if not media_files:
                error_exit("E008", "Excel 文件中未找到图片")

            # 提取每个图片文件
            for media_file in media_files:
                # 构造输出文件名
                filename = os.path.basename(media_file)
                # 处理重名文件
                base_name, ext = os.path.splitext(filename)
                output_path = os.path.join(output_dir, filename)
                counter = 1
                while os.path.exists(output_path):
                    output_path = os.path.join(
                        output_dir, f"{base_name}_{counter}{ext}"
                    )
                    counter += 1

                # 提取文件
                with zip_ref.open(media_file) as source, open(output_path, "wb") as target:
                    shutil.copyfileobj(source, target)

                extracted_files.append(output_path)

    except zipfile.BadZipFile:
        error_exit("E003", "ZIP 文件损坏")
    except Exception as e:
        error_exit("E009", f"提取过程出错: {str(e)}")

    return extracted_files


# ============================================================
# 辅助函数：获取 Excel 基本信息
# ============================================================
def get_excel_info(excel_path: str) -> dict:
    """
    获取 Excel 文件的基本信息（不读取图片）

    参数:
        excel_path: Excel 文件路径

    返回:
        包含文件信息的字典
    """
    if not excel_path or not os.path.exists(excel_path):
        return {}

    info = {
        "filename": os.path.basename(excel_path),
        "size_bytes": os.path.getsize(excel_path),
        "is_excel": zipfile.is_zipfile(excel_path),
    }

    # 如果是有效的 Excel，尝试读取更多信息
    if info["is_excel"]:
        try:
            with zipfile.ZipFile(excel_path, "r") as zip_ref:
                # 统计图片数量
                media_files = [
                    name for name in zip_ref.namelist()
                    if name.startswith("xl/media/") and not name.endswith("/")
                ]
                info["image_count"] = len(media_files)

                # 检查是否有工作簿结构
                info["has_workbook"] = any(
                    name.endswith("workbook.xml") for name in zip_ref.namelist()
                )
        except Exception:
            pass

    return info


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑

    使用硬编码的样例数据，不依赖外部文件。
    通过构造一个内存中的 Excel 结构来测试提取逻辑。

    返回:
        True 表示自检通过
    """
    print("=" * 60)
    print("开始自检...")
    print("=" * 60)

    # 构建一个模拟的 Excel 文件结构（内存中）
    # 使用 zipfile 在内存中创建一个简单的 Excel 结构
    import io

    test_cases = []

    # 测试用例 1：正常的 Excel 文件结构
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w") as zip_ref:
            # 添加工作簿结构
            zip_ref.writestr(
                "xl/workbook.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main"></workbook>'
            )
            # 添加两个模拟图片（使用简单的 PNG 头）
            png_header = bytes.fromhex(
                "89504E470D0A1A0A0000000D49484452"
                "000000010000000108000000003C6C"
                "0F3A0000000A49444154789C6360"
                "0000000200010000002E000000"
            )
            zip_ref.writestr("xl/media/image1.png", png_header)
            zip_ref.writestr("xl/media/image2.png", png_header)

        memory_file.seek(0)

        # 保存到临时文件进行测试
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(memory_file.getvalue())
            tmp_path = tmp.name

        # 创建临时输出目录
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 测试图片提取
            extracted = extract_images_from_excel(tmp_path, tmp_dir)

            # 宽松断言：至少提取到 1 张图片
            assert len(extracted) >= 1, "应至少提取到 1 张图片"
            print(f"✅ 测试用例 1 通过：成功提取 {len(extracted)} 张图片")

        # 清理临时文件
        os.unlink(tmp_path)

    except AssertionError as e:
        print(f"❌ 测试用例 1 失败：{str(e)}")
        return False
    except Exception as e:
        print(f"❌ 测试用例 1 异常：{str(e)}")
        return False

    # 测试用例 2：空 Excel（无图片）
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w") as zip_ref:
            zip_ref.writestr(
                "xl/workbook.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main"></workbook>'
            )

        memory_file.seek(0)

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(memory_file.getvalue())
            tmp_path = tmp.name

        with tempfile.TemporaryDirectory() as tmp_dir:
            # 测试信息获取
            info = get_excel_info(tmp_path)
            assert "image_count" in info, "信息中应包含 image_count 字段"
            assert info["image_count"] == 0, "无图片时 image_count 应为 0"
            print("✅ 测试用例 2 通过：正确识别空 Excel（无图片）")

        os.unlink(tmp_path)

    except AssertionError as e:
        print(f"❌ 测试用例 2 失败：{str(e)}")
        return False
    except Exception as e:
        print(f"❌ 测试用例 2 异常：{str(e)}")
        return False

    # 测试用例 3：文件信息获取
    try:
        info = get_excel_info("nonexistent_file.xlsx")
        assert info == {}, "不存在的文件应返回空字典"
        print("✅ 测试用例 3 通过：正确处理不存在的文件")

    except AssertionError as e:
        print(f"❌ 测试用例 3 失败：{str(e)}")
        return False
    except Exception as e:
        print(f"❌ 测试用例 3 异常：{str(e)}")
        return False

    # 测试用例 4：错误码检查
    try:
        assert "E001" in ERROR_CODES, "E001 应存在于错误码表中"
        assert "E010" in ERROR_CODES, "E010 应存在于错误码表中"
        assert len(ERROR_CODES) >= 5, "错误码数量应不少于 5 个"
        print("✅ 测试用例 4 通过：错误码定义完整")

    except AssertionError as e:
        print(f"❌ 测试用例 4 失败：{str(e)}")
        return False
    except Exception as e:
        print(f"❌ 测试用例 4 异常：{str(e)}")
        return False

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return True


# ============================================================
# 主程序
# ============================================================
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="从 Excel 文件中提取嵌入的图片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 Excel 提取图片到指定目录
  python main.py input.xlsx -o ./output

  # 查看 Excel 文件信息（不提取）
  python main.py input.xlsx --info

  # 运行自检
  python main.py --selftest
        """,
    )

    parser.add_argument(
        "excel_file",
        nargs="?",
        help="Excel 文件路径（.xlsx 或 .xlsm 格式）",
    )
    parser.add_argument(
        "-o", "--output",
        default="./extracted_images",
        help="图片输出目录（默认: ./extracted_images）",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="仅显示 Excel 文件信息，不提取图片",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 检查参数
    if not args.excel_file:
        error_exit("E001")

    # 信息模式
    if args.info:
        info = get_excel_info(args.excel_file)
        if not info:
            error_exit("E006", f"无法读取文件: {args.excel_file}")

        print("=" * 50)
        print("Excel 文件信息")
        print("=" * 50)
        for key, value in info.items():
            print(f"  {key}: {value}")
        print("=" * 50)
        return

    # 提取模式
    print(f"正在从 {args.excel_file} 提取图片...")
    print(f"输出目录: {args.output}")

    extracted_files = extract_images_from_excel(args.excel_file, args.output)

    if extracted_files:
        print(f"✅ 成功提取 {len(extracted_files)} 张图片:")
        for file_path in extracted_files:
            print(f"  - {file_path}")
        print(f"\n图片已保存到: {os.path.abspath(args.output)}")
    else:
        print("未提取到任何图片")


if __name__ == "__main__":
    main()
