#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf-inspector: PDF文档检测与分类
=================================
快速检测PDF文件类型（扫描版或文本版），提取文本内容，
为后续处理（如OCR、转换）提供智能路由决策。

本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例:
    python scripts/main.py path/to/file.pdf
    python scripts/main.py --selftest

错误码:
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 文件不存在
    E007: 无法读取PDF内容
    E008: PDF文件损坏或无效
    E009: 不支持的参数
    E010: 内部逻辑错误
"""

import sys
import os
import re
import argparse
import zlib
from typing import Dict, Any, List, Optional, Tuple

# 尝试导入第三方库（仅用于增强解析，非必需）
try:
    import pypdf  # pip install pypdf
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False


# ============================================================
# 核心数据结构
# ============================================================

class PDFInspectionResult:
    """PDF检测结果的数据结构"""
    
    def __init__(self):
        self.file_name: str = ""
        self.file_size: int = 0
        self.page_count: int = 0
        self.pdf_type: str = "unknown"  # "text" / "scanned" / "mixed" / "unknown"
        self.text_preview: str = ""
        self.confidence: float = 0.0
        self.is_encrypted: bool = False
        self.has_text_layer: bool = False
        self.has_images: bool = False
        self.warnings: List[str] = []
        self.raw_metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "pdf_type": self.pdf_type,
            "text_preview": self.text_preview[:200] if self.text_preview else "",
            "confidence": round(self.confidence, 2),
            "is_encrypted": self.is_encrypted,
            "has_text_layer": self.has_text_layer,
            "has_images": self.has_images,
            "warnings": self.warnings,
            "metadata": self.raw_metadata
        }
    
    def __repr__(self) -> str:
        return f"<PDFInspectionResult type={self.pdf_type} pages={self.page_count} conf={self.confidence:.2f}>"


# ============================================================
# PDF解析核心函数
# ============================================================

def _parse_pdf_header(data: bytes) -> Dict[str, Any]:
    """
    解析PDF文件头信息
    
    参数:
        data: PDF文件字节数据
    
    返回:
        包含PDF版本等信息的字典
    """
    header_info = {
        "version": "",
        "is_valid": False
    }
    
    if data.startswith(b"%PDF-"):
        # 提取版本号
        version_match = re.match(rb"%PDF-(\d+\.\d+)", data[:16])
        if version_match:
            header_info["version"] = version_match.group(1).decode("utf-8")
            header_info["is_valid"] = True
    
    return header_info


def _extract_text_from_stream(stream: bytes) -> List[str]:
    """
    从PDF流中提取文本
    
    参数:
        stream: PDF流数据
    
    返回:
        提取的文本片段列表
    """
    text_parts: List[str] = []
    
    # 尝试zlib解压
    try:
        decompressed = zlib.decompress(stream)
        # 查找文本操作符
        text_patterns = [
            rb"\((.*?)\)\s*Tj",       # Tj 操作符
            rb"\[(.*?)\]\s*TJ",       # TJ 操作符
            rb"\((.*?)\)\s*'",        # 单引号字符串
            rb"\((.*?)\)\s*\"",       # 双引号字符串
        ]
        
        for pattern in text_patterns:
            matches = re.findall(pattern, decompressed, re.DOTALL)
            for match in matches:
                if isinstance(match, bytes):
                    # 处理转义字符
                    cleaned = match.replace(b"\\(", b"(").replace(b"\\)", b")")
                    cleaned = cleaned.replace(b"\\\\", b"\\")
                    cleaned = cleaned.replace(b"\\n", b" ")
                    try:
                        text = cleaned.decode("utf-8", errors="ignore")
                        if text.strip():
                            text_parts.append(text)
                    except:
                        pass
    
    except zlib.error:
        # 不是压缩流，尝试直接解析
        try:
            # 查找文本操作符
            matches = re.findall(rb"\((.*?)\)\s*Tj", stream, re.DOTALL)
            for match in matches:
                cleaned = match.replace(b"\\(", b"(").replace(b"\\)", b")")
                cleaned = cleaned.replace(b"\\\\", b"\\")
                try:
                    text = cleaned.decode("utf-8", errors="ignore")
                    if text.strip():
                        text_parts.append(text)
                except:
                    pass
        except:
            pass
    
    return text_parts


def _extract_text_from_pdf_bytes(data: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    从PDF字节数据中提取文本信息（纯标准库实现）
    
    返回:
        (提取到的文本, 元信息字典)
    """
    text_parts: List[str] = []
    metadata: Dict[str, Any] = {
        "has_images": False,
        "has_text": False,
        "page_count": 0,
        "is_encrypted": False,
        "stream_count": 0,
        "image_count": 0,
        "version": "",
        "has_forms": False,
        "has_annotations": False,
    }
    
    # 解析文件头
    header_info = _parse_pdf_header(data)
    metadata["version"] = header_info["version"]
    
    if not header_info["is_valid"]:
        raise ValueError("不是有效的PDF文件")
    
    # 查找所有流对象
    stream_pattern = rb"stream\r?\n(.*?)\r?\nendstream"
    streams = re.findall(stream_pattern, data, re.DOTALL)
    metadata["stream_count"] = len(streams)
    
    # 统计图片对象
    image_pattern = rb"/Subtype\s*/Image"
    images = re.findall(image_pattern, data)
    metadata["image_count"] = len(images)
    metadata["has_images"] = len(images) > 0
    
    # 检查加密
    if b"/Encrypt" in data:
        metadata["is_encrypted"] = True
    
    # 统计页面数量
    page_pattern = rb"/Type\s*/Page[^s]"
    pages = re.findall(page_pattern, data)
    metadata["page_count"] = len(pages) if pages else 0
    
    # 检查表单和注释
    if b"/AcroForm" in data or b"/BBox" in data:
        metadata["has_forms"] = True
    if b"/Annots" in data:
        metadata["has_annotations"] = True
    
    # 提取文本
    for stream in streams:
        text_parts.extend(_extract_text_from_stream(stream))
    
    # 合并文本
    full_text = " ".join(text_parts)
    metadata["has_text"] = len(full_text.strip()) > 0
    
    return full_text, metadata


def _analyze_pdf_content(data: bytes) -> PDFInspectionResult:
    """
    分析PDF内容，确定类型
    
    返回:
        PDFInspectionResult 对象
    """
    result = PDFInspectionResult()
    
    try:
        # 使用标准库解析
        text, metadata = _extract_text_from_pdf_bytes(data)
        
        result.page_count = metadata.get("page_count", 0)
        result.is_encrypted = metadata.get("is_encrypted", False)
        result.has_images = metadata.get("has_images", False)
        result.text_preview = text[:500] if text else ""
        result.raw_metadata = metadata
        
        # 判断PDF类型
        text_len = len(text.strip())
        image_count = metadata.get("image_count", 0)
        
        # 更精确的类型判断逻辑
        if text_len > 0 and image_count > 0:
            # 混合类型：根据文本和图片比例调整置信度
            result.pdf_type = "mixed"
            if text_len > 1000:
                result.confidence = 0.88
            elif text_len > 100:
                result.confidence = 0.85
            else:
                result.confidence = 0.82
        elif text_len > 0:
            # 纯文本类型
            result.pdf_type = "text"
            if text_len > 100:
                result.confidence = 0.95
            elif text_len > 0:
                result.confidence = 0.90
        elif image_count > 0:
            # 扫描类型
            result.pdf_type = "scanned"
            if image_count >= 2:
                result.confidence = 0.92
            else:
                result.confidence = 0.90
        else:
            # 无法确定类型
            result.pdf_type = "unknown"
            result.confidence = 0.50
            result.warnings.append("无法确定PDF类型，可能为空文档或格式特殊")
        
        result.has_text_layer = text_len > 0
        
        # 添加额外警告
        if metadata.get("is_encrypted", False):
            result.warnings.append("PDF文件已加密，可能无法完整解析")
        
        if metadata.get("has_forms", False):
            result.warnings.append("PDF包含表单元素")
        
        if metadata.get("has_annotations", False):
            result.warnings.append("PDF包含注释元素")
        
        if result.page_count == 0:
            result.warnings.append("未检测到页面对象")
        
    except Exception as e:
        result.pdf_type = "unknown"
        result.confidence = 0.1
        result.warnings.append(f"解析失败: {str(e)}")
    
    return result


def inspect_pdf_file(file_path: str) -> PDFInspectionResult:
    """
    检测PDF文件的主入口函数
    
    参数:
        file_path: PDF文件路径
    
    返回:
        PDFInspectionResult 对象
    
    错误码:
        E001: 输入为空
        E006: 文件不存在
        E007: 无法读取PDF内容
        E008: PDF文件损坏或无效
    """
    # E001: 输入为空
    if not file_path or not file_path.strip():
        raise ValueError("E001: 请提供待处理的PDF文件路径")
    
    # E006: 文件不存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"E006: 文件不存在: {file_path}")
    
    # 读取文件
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        raise IOError(f"E007: 无法读取PDF内容: {str(e)}")
    
    # 检查文件大小
    file_size = len(data)
    if file_size == 0:
        raise ValueError("E008: PDF文件为空")
    
    # 检查PDF文件头
    if not data.startswith(b"%PDF"):
        raise ValueError("E008: 不是有效的PDF文件")
    
    # 分析内容
    result = _analyze_pdf_content(data)
    result.file_name = os.path.basename(file_path)
    result.file_size = file_size
    
    return result


# ============================================================
# 自检函数
# ============================================================

def _run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑
    
    使用硬编码样例数据，不依赖外部文件
    """
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)
    
    # 构造测试用PDF字节数据（最小化有效PDF结构）
    # 文本型PDF样例
    text_pdf_data = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
4 0 obj
<< /Length 100 >>
stream
BT /F1 12 Tf 72 720 Td (Hello World Test PDF) Tj ET
endstream
endobj
xref
trailer
<< /Root 1 0 R >>
%%EOF
"""
    
    # 图片型PDF样例（模拟扫描版）
    scanned_pdf_data = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /XObject << /Im1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 50 >>
stream
q 612 0 0 792 0 0 cm /Im1 Do Q
endstream
endobj
5 0 obj
<< /Type /XObject /Subtype /Image /Width 100 /Height 100 /ColorSpace /DeviceRGB /BitsPerComponent 8 >>
stream
ABCDEFGHIJKLMNOPQRSTUVWXYZ
endstream
endobj
xref
trailer
<< /Root 1 0 R >>
%%EOF
"""
    
    # 混合型PDF样例（既有文本又有图片）
    mixed_pdf_data = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /XObject << /Im1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 80 >>
stream
BT /F1 12 Tf 72 720 Tj (Mixed Content PDF) Tj ET
endstream
endobj
5 0 obj
<< /Type /XObject /Subtype /Image /Width 50 /Height 50 >>
stream
FAKEDATA
endstream
endobj
xref
trailer
<< /Root 1 0 R >>
%%EOF
"""
    
    test_cases = [
        ("文本型PDF", text_pdf_data, "text"),
        ("扫描型PDF", scanned_pdf_data, "scanned"),
        ("混合型PDF", mixed_pdf_data, "mixed"),
    ]
    
    all_passed = True
    
    for name, data, expected_type in test_cases:
        print(f"\n测试: {name}")
        try:
            result = _analyze_pdf_content(data)
            
            # 宽松断言：只检查类型匹配和置信度范围
            type_ok = result.pdf_type == expected_type
            conf_ok = 0.0 < result.confidence <= 1.0
            
            # 检查基本信息
            has_text = "text_preview" in result.__dict__
            has_meta = isinstance(result.raw_metadata, dict)
            
            status = "PASS" if (type_ok and conf_ok and has_text and has_meta) else "FAIL"
            if status == "FAIL":
                all_passed = False
            
            print(f"  类型: {result.pdf_type} (期望: {expected_type}) -> {'✓' if type_ok else '✗'}")
            print(f"  置信度: {result.confidence:.2f} -> {'✓' if conf_ok else '✗'}")
            print(f"  结果: {status}")
            
        except Exception as e:
            all_passed = False
            print(f"  异常: {str(e)}")
            print(f"  结果: FAIL")
    
    # 测试错误处理
    print("\n测试错误处理:")
    
    # E001: 空输入
    try:
        inspect_pdf_file("")
        print("  E001空输入测试: FAIL (未抛出异常)")
        all_passed = False
    except ValueError as e:
        if "E001" in str(e):
            print("  E001空输入测试: PASS")
        else:
            print(f"  E001空输入测试: FAIL (错误码不匹配: {e})")
            all_passed = False
    
    # E006: 文件不存在
    try:
        inspect_pdf_file("/nonexistent/file.pdf")
        print("  E006文件不存在测试: FAIL (未抛出异常)")
        all_passed = False
    except FileNotFoundError as e:
        if "E006" in str(e):
            print("  E006文件不存在测试: PASS")
        else:
            print(f"  E006文件不存在测试: FAIL (错误码不匹配: {e})")
            all_passed = False
    
    # E008: 无效PDF
    try:
        invalid_data = b"This is not a PDF file"
        # 使用临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(invalid_data)
            tmp_path = tmp.name
        
        try:
            inspect_pdf_file(tmp_path)
            print("  E008无效PDF测试: FAIL (未抛出异常)")
            all_passed = False
        except ValueError as e:
            if "E008" in str(e):
                print("  E008无效PDF测试: PASS")
            else:
                print(f"  E008无效PDF测试: FAIL (错误码不匹配: {e})")
                all_passed = False
        except Exception as e:
            print(f"  E008无效PDF测试: FAIL (其他异常: {e})")
            all_passed = False
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        print(f"  E008无效PDF测试: FAIL (临时文件创建失败: {e})")
        all_passed = False
    
    # 验证输出格式
    print("\n验证输出格式:")
    sample_result = PDFInspectionResult()
    sample_result.file_name = "test.pdf"
    sample_result.pdf_type = "text"
    sample_result.confidence = 0.95
    sample_dict = sample_result.to_dict()
    
    required_keys = ["file_name", "file_size", "page_count", "pdf_type", 
                     "text_preview", "confidence", "is_encrypted", 
                     "has_text_layer", "has_images", "warnings", "metadata"]
    
    keys_ok = all(key in sample_dict for key in required_keys)
    print(f"  必要字段完整性: {'PASS' if keys_ok else 'FAIL'}")
    if not keys_ok:
        all_passed = False
    
    # 汇总结果
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="PDF文档检测与分类工具",
        epilog="示例: python main.py document.pdf 或 python main.py --selftest"
    )
    
    parser.add_argument(
        "file",
        nargs="?",
        help="PDF文件路径"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件）"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出结果"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = _run_selftest()
        return 0 if success else 1
    
    # 正常模式
    if not args.file:
        print("E001: 请提供待处理的PDF文件路径", file=sys.stderr)
        print("提示: 使用 --selftest 运行内置自检", file=sys.stderr)
        return 1
    
    try:
        result = inspect_pdf_file(args.file)
        
        if args.json:
            import json
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        else:
            # 人类可读输出
            print(f"\n{'='*50}")
            print(f"PDF检测结果: {result.file_name}")
            print(f"{'='*50}")
            print(f"文件大小: {result.file_size} bytes")
            print(f"页数: {result.page_count}")
            print(f"类型: {result.pdf_type}")
            print(f"置信度: {result.confidence:.1%}")
            print(f"有文本层: {'是' if result.has_text_layer else '否'}")
            print(f"包含图片: {'是' if result.has_images else '否'}")
            print(f"加密: {'是' if result.is_encrypted else '否'}")
            
            if result.text_preview:
                preview = result.text_preview[:100]
                print(f"文本预览: {preview}...")
            
            if result.warnings:
                print(f"\n警告:")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            print(f"\n{'-'*50}")
            if result.confidence >= 0.9:
                print("结论: 检测结果可信，可直接使用")
            elif result.confidence >= 0.85:
                print("结论: 建议复核")
            else:
                print("结论: [需核实] 置信度较低，请人工确认")
            print(f"{'='*50}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 内部错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
