#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fb2cng - PDF转文档 统一转换器（独立实现）

本脚本根据功能规格独立编写，实现 FB2 文件到多种格式的转换逻辑。
仅使用标准库，支持 --selftest 离线自检。

用法:
    python scripts/main.py --selftest
    python scripts/main.py <input.fb2> --output <output.ext> [--format <fmt>]
"""

import sys
import os
import re
import json
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要参数",
    "E003": "输入格式错误，无法解析",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读写失败",
    "E007": "不支持的输出格式",
    "E008": "内部处理错误",
    "E009": "参数冲突或无效",
    "E010": "自检失败",
}


class FB2ConverterError(Exception):
    """转换器自定义异常"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class BookInfo:
    """书籍元数据"""
    def __init__(self):
        self.title: str = ""
        self.author: str = ""
        self.lang: str = "ru"
        self.genre: List[str] = []
        self.annotation: str = ""
        self.cover: Optional[bytes] = None
        self.confidence: float = 0.0


class Chapter:
    """章节数据"""
    def __init__(self, title: str = "", content: str = ""):
        self.title = title
        self.content = content
        self.confidence: float = 1.0


class FB2Document:
    """解析后的 FB2 文档"""
    def __init__(self):
        self.info = BookInfo()
        self.chapters: List[Chapter] = []
        self.raw_xml: str = ""
        self.parsed_ok: bool = False
        self.source_format: str = "fb2"


# ============================================================
# FB2 解析器（纯标准库实现）
# ============================================================
class FB2Parser:
    """FB2 XML 解析器"""
    
    NS = {
        'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0',
        'xlink': 'http://www.w3.org/1999/xlink',
    }
    
    def __init__(self):
        self.doc = FB2Document()
    
    def parse(self, xml_content: str) -> FB2Document:
        """解析 FB2 XML 内容"""
        if not xml_content or not xml_content.strip():
            raise FB2ConverterError("E001", "FB2内容为空")
        
        self.doc.raw_xml = xml_content
        self.doc.parsed_ok = False
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise FB2ConverterError("E003", f"XML解析失败: {str(e)}")
        
        # 识别根元素
        tag = self._local_name(root.tag)
        if tag != 'FictionBook':
            raise FB2ConverterError("E003", f"不是有效的FB2文档，根元素: {tag}")
        
        # 提取元数据
        self._parse_metadata(root)
        
        # 提取正文
        self._parse_body(root)
        
        self.doc.parsed_ok = True
        self.doc.info.confidence = self._calc_confidence()
        
        return self.doc
    
    def _parse_metadata(self, root: ET.Element) -> None:
        """解析书籍元数据"""
        desc = root.find('.//fb:description', self.NS)
        if desc is None:
            # 尝试无命名空间
            desc = root.find('.//description')
        
        if desc is None:
            self.doc.info.confidence = 0.3
            return
        
        # 标题
        title_info = desc.find('fb:title-info', self.NS)
        if title_info is None:
            title_info = desc.find('title-info')
        
        if title_info is not None:
            # 书名
            book_title = title_info.find('fb:book-title', self.NS)
            if book_title is None:
                book_title = title_info.find('book-title')
            if book_title is not None and book_title.text:
                self.doc.info.title = book_title.text.strip()
            
            # 作者 - 修复解析逻辑
            author = title_info.find('fb:author', self.NS)
            if author is None:
                author = title_info.find('author')
            if author is not None:
                # 直接查找子元素，不依赖命名空间
                first_name = ""
                last_name = ""
                middle_name = ""
                
                # 尝试带命名空间
                first = author.find('fb:first-name', self.NS)
                if first is None:
                    first = author.find('first-name')
                if first is not None and first.text:
                    first_name = first.text.strip()
                
                last = author.find('fb:last-name', self.NS)
                if last is None:
                    last = author.find('last-name')
                if last is not None and last.text:
                    last_name = last.text.strip()
                
                middle = author.find('fb:middle-name', self.NS)
                if middle is None:
                    middle = author.find('middle-name')
                if middle is not None and middle.text:
                    middle_name = middle.text.strip()
                
                # 组合作者名
                parts = [p for p in [first_name, middle_name, last_name] if p]
                self.doc.info.author = ' '.join(parts)
            
            # 语言
            lang = self._find_text(title_info, 'fb:lang', 'lang')
            if lang:
                self.doc.info.lang = lang
            
            # 体裁
            for genre in title_info.findall('fb:genre', self.NS):
                if genre.text:
                    self.doc.info.genre.append(genre.text.strip())
            if not self.doc.info.genre:
                for genre in title_info.findall('genre'):
                    if genre.text:
                        self.doc.info.genre.append(genre.text.strip())
            
            # 注释
            annotation = title_info.find('fb:annotation', self.NS)
            if annotation is None:
                annotation = title_info.find('annotation')
            if annotation is not None:
                self.doc.info.annotation = self._extract_text(annotation)
    
    def _parse_body(self, root: ET.Element) -> None:
        """解析正文内容"""
        body = root.find('fb:body', self.NS)
        if body is None:
            body = root.find('body')
        
        if body is None:
            raise FB2ConverterError("E003", "FB2文档缺少body元素")
        
        # 提取所有章节（section）
        sections = body.findall('.//fb:section', self.NS)
        if not sections:
            sections = body.findall('.//section')
        
        if not sections:
            # 没有section，把整个body作为一章
            content = self._extract_text(body)
            if content.strip():
                self.doc.chapters.append(Chapter(title="", content=content))
        else:
            for section in sections:
                self._parse_section(section)
    
    def _parse_section(self, section: ET.Element) -> None:
        """解析单个章节"""
        # 章节标题
        title = ""
        title_elem = section.find('fb:title', self.NS)
        if title_elem is None:
            title_elem = section.find('title')
        if title_elem is not None:
            title = self._extract_text(title_elem).strip()
        
        # 提取段落
        paragraphs = []
        for p in section.findall('.//fb:p', self.NS):
            if p.text:
                paragraphs.append(p.text.strip())
        if not paragraphs:
            for p in section.findall('.//p'):
                if p.text:
                    paragraphs.append(p.text.strip())
        
        content = '\n\n'.join(paragraphs)
        if title or content:
            self.doc.chapters.append(Chapter(title=title, content=content))
    
    def _extract_text(self, elem: ET.Element) -> str:
        """递归提取元素内所有文本"""
        if elem is None:
            return ""
        parts = []
        for child in elem.iter():
            if child.text:
                parts.append(child.text)
        return ' '.join(parts)
    
    def _find_text(self, elem: ET.Element, *names) -> str:
        """在元素中查找文本"""
        for name in names:
            found = elem.find(name)
            if found is not None and found.text:
                return found.text.strip()
        return ""
    
    def _local_name(self, tag: str) -> str:
        """获取XML标签的本地名称"""
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag
    
    def _calc_confidence(self) -> float:
        """计算解析置信度"""
        score = 0.0
        total = 4
        
        if self.doc.info.title:
            score += 1
        if self.doc.info.author:
            score += 1
        if self.doc.info.lang:
            score += 1
        if self.doc.chapters:
            score += 1
        
        return score / total


# ============================================================
# 输出格式转换器
# ============================================================
class OutputConverter:
    """将 FB2Document 转换为目标格式"""
    
    SUPPORTED_FORMATS = ['epub2', 'epub3', 'kepub', 'azw8', 'kfx', 'pdf', 'txt', 'md']
    
    def __init__(self, doc: FB2Document):
        self.doc = doc
    
    def convert(self, fmt: str) -> Tuple[bytes, str]:
        """转换为指定格式，返回 (内容, MIME类型)"""
        fmt = fmt.lower().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            raise FB2ConverterError("E007", f"不支持的格式: {fmt}")
        
        if fmt == 'txt':
            content, mime = self._to_txt(), "text/plain"
        elif fmt == 'md':
            content, mime = self._to_md(), "text/markdown"
        elif fmt in ('epub2', 'epub3', 'kepub'):
            content, mime = self._to_epub(fmt), "application/epub+zip"
        elif fmt in ('azw8', 'kfx', 'pdf'):
            # 这些格式需要复杂二进制处理，这里生成简化版本
            content, mime = self._to_simple_binary(fmt), "application/octet-stream"
        else:
            raise FB2ConverterError("E007", f"不支持的格式: {fmt}")
        
        return content, mime
    
    def _to_txt(self) -> bytes:
        """转换为纯文本"""
        lines = []
        if self.doc.info.title:
            lines.append(self.doc.info.title)
            lines.append("=" * len(self.doc.info.title))
            lines.append("")
        
        if self.doc.info.author:
            lines.append(f"作者: {self.doc.info.author}")
            lines.append("")
        
        for chapter in self.doc.chapters:
            if chapter.title:
                lines.append(chapter.title)
                lines.append("-" * len(chapter.title))
            lines.append(chapter.content)
            lines.append("")
        
        return "\n".join(lines).encode('utf-8')
    
    def _to_md(self) -> bytes:
        """转换为 Markdown"""
        lines = []
        
        if self.doc.info.title:
            lines.append(f"# {self.doc.info.title}")
            lines.append("")
        
        if self.doc.info.author:
            lines.append(f"**作者**: {self.doc.info.author}")
            lines.append("")
        
        if self.doc.info.annotation:
            lines.append("## 简介")
            lines.append(self.doc.info.annotation)
            lines.append("")
        
        for i, chapter in enumerate(self.doc.chapters, 1):
            if chapter.title:
                lines.append(f"## {chapter.title}")
            else:
                lines.append(f"## 章节 {i}")
            lines.append("")
            for para in chapter.content.split('\n\n'):
                lines.append(para)
                lines.append("")
        
        return "\n".join(lines).encode('utf-8')
    
    def _to_epub(self, fmt: str) -> bytes:
        """生成 EPUB 格式（简化版，使用 zip 打包）"""
        import zipfile
        import io
        
        buf = io.BytesIO()
        
        # 生成基础 EPUB 内容
        container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
        
        # 生成 OPF
        opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{self.doc.info.title}</dc:title>
    <dc:creator>{self.doc.info.author}</dc:creator>
    <dc:language>{self.doc.info.lang}</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="content"/>
  </spine>
</package>"""
        
        # 生成 XHTML 内容
        xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{self.doc.info.title}</title></head>
<body>
<h1>{self.doc.info.title}</h1>
<p><strong>{self.doc.info.author}</strong></p>
"""
        for chapter in self.doc.chapters:
            if chapter.title:
                xhtml += f"<h2>{chapter.title}</h2>\n"
            for para in chapter.content.split('\n\n'):
                xhtml += f"<p>{para}</p>\n"
        xhtml += "</body></html>"
        
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('mimetype', 'application/epub+zip')
            zf.writestr('META-INF/container.xml', container)
            zf.writestr('OEBPS/content.opf', opf)
            zf.writestr('OEBPS/content.xhtml', xhtml)
        
        return buf.getvalue()
    
    def _to_simple_binary(self, fmt: str) -> bytes:
        """生成简单二进制格式（占位实现）"""
        # 对于 AZW8/KFX/PDF，生成包含基本信息的简单二进制
        header = f"FB2CNG-{fmt.upper()}".encode('ascii')
        info = f"{self.doc.info.title}|{self.doc.info.author}".encode('utf-8')
        return header + b'\x00' + info


# ============================================================
# 主处理流程
# ============================================================
class FB2Converter:
    """FB2 转换器主类"""
    
    def __init__(self):
        self.parser = FB2Parser()
    
    def process_file(self, input_path: str, output_path: str, fmt: str) -> Dict[str, Any]:
        """处理文件转换"""
        try:
            # 读取输入文件
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            raise FB2ConverterError("E006", f"输入文件不存在: {input_path}")
        except Exception as e:
            raise FB2ConverterError("E006", f"读取文件失败: {str(e)}")
        
        # 解析
        doc = self.parser.parse(content)
        
        # 转换
        converter = OutputConverter(doc)
        output_data, mime = converter.convert(fmt)
        
        # 写入输出
        try:
            with open(output_path, 'wb') as f:
                f.write(output_data)
        except Exception as e:
            raise FB2ConverterError("E006", f"写入文件失败: {str(e)}")
        
        return {
            "status": "ok",
            "title": doc.info.title,
            "author": doc.info.author,
            "chapters": len(doc.chapters),
            "confidence": doc.info.confidence,
            "output_format": fmt,
            "output_path": output_path,
        }
    
    def process_string(self, content: str, fmt: str = 'txt') -> Tuple[bytes, Dict[str, Any]]:
        """处理字符串输入"""
        doc = self.parser.parse(content)
        converter = OutputConverter(doc)
        output_data, _ = converter.convert(fmt)
        
        result = {
            "status": "ok",
            "title": doc.info.title,
            "author": doc.info.author,
            "chapters": len(doc.chapters),
            "confidence": doc.info.confidence,
            "output_format": fmt,
        }
        return output_data, result


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """内置自检，使用硬编码样例数据"""
    print("=" * 60)
    print("fb2cng 自检开始")
    print("=" * 60)
    
    # 硬编码测试数据
    test_fb2 = """<?xml version="1.0" encoding="UTF-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <genre>science_fiction</genre>
      <author>
        <first-name>测试</first-name>
        <last-name>作者</last-name>
      </author>
      <book-title>自检测试书籍</book-title>
      <lang>zh</lang>
      <annotation><p>这是一本用于自检的测试书籍。</p></annotation>
    </title-info>
  </description>
  <body>
    <section>
      <title><p>第一章</p></title>
      <p>这是第一章的内容。</p>
      <p>包含多个段落。</p>
    </section>
    <section>
      <title><p>第二章</p></title>
      <p>这是第二章的内容。</p>
    </section>
  </body>
</FictionBook>"""
    
    try:
        # 测试1: 解析功能
        print("\n[测试1] FB2解析...")
        parser = FB2Parser()
        doc = parser.parse(test_fb2)
        
        assert doc.parsed_ok, "解析失败"
        assert doc.info.title, "标题为空"
        assert doc.info.author, f"作者为空 (实际: '{doc.info.author}')"
        assert len(doc.chapters) >= 2, f"章节数不足: {len(doc.chapters)}"
        assert doc.info.confidence >= 0.5, f"置信度过低: {doc.info.confidence}"
        print(f"  ✓ 解析成功: '{doc.info.title}' by {doc.info.author}")
        print(f"  ✓ 章节数: {len(doc.chapters)}, 置信度: {doc.info.confidence:.2f}")
        
        # 测试2: TXT 转换
        print("\n[测试2] TXT转换...")
        converter = OutputConverter(doc)
        txt_data, mime = converter.convert('txt')
        txt_str = txt_data.decode('utf-8')
        assert "自检测试书籍" in txt_str, "TXT缺少书名"
        assert "第一章" in txt_str, "TXT缺少章节标题"
        assert "这是第一章的内容" in txt_str, "TXT缺少正文内容"
        assert mime == "text/plain"
        print(f"  ✓ TXT转换成功, 大小: {len(txt_data)} bytes")
        
        # 测试3: MD 转换
        print("\n[测试3] MD转换...")
        md_data, mime = converter.convert('md')
        md_str = md_data.decode('utf-8')
        assert "# 自检测试书籍" in md_str, "MD缺少标题"
        assert "## 第一章" in md_str, "MD缺少章节"
        assert mime == "text/markdown"
        print(f"  ✓ MD转换成功, 大小: {len(md_data)} bytes")
        
        # 测试4: EPUB 转换
        print("\n[测试4] EPUB转换...")
        epub_data, mime = converter.convert('epub3')
        assert len(epub_data) > 100, "EPUB数据过小"
        assert mime == "application/epub+zip"
        print(f"  ✓ EPUB3转换成功, 大小: {len(epub_data)} bytes")
        
        # 测试5: 错误处理
        print("\n[测试5] 错误处理...")
        try:
            parser.parse("")
            assert False, "空输入应该报错"
        except FB2ConverterError as e:
            assert e.error_code == "E001", f"错误码错误: {e.error_code}"
            print(f"  ✓ 空输入正确报错: {e.message}")
        
        try:
            converter.convert('unknown')
            assert False, "未知格式应该报错"
        except FB2ConverterError as e:
            assert e.error_code == "E007", f"错误码错误: {e.error_code}"
            print(f"  ✓ 未知格式正确报错: {e.message}")
        
        # 测试6: 完整流程
        print("\n[测试6] 完整转换流程...")
        fb2cng = FB2Converter()
        output_data, result = fb2cng.process_string(test_fb2, 'md')
        assert result['status'] == 'ok'
        assert result['chapters'] >= 2
        assert result['confidence'] >= 0.5
        print(f"  ✓ 完整流程成功: {result}")
        
        print("\n" + "=" * 60)
        print("✅ 所有自检通过!")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ 自检失败: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {str(e)}")
        return False


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="fb2cng - FB2 文件格式转换器",
        epilog="示例: python main.py input.fb2 -o output.md -f md"
    )
    
    parser.add_argument(
        'input',
        nargs='?',
        help='输入 FB2 文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出文件路径'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['epub2', 'epub3', 'kepub', 'azw8', 'kfx', 'pdf', 'txt', 'md'],
        default='txt',
        help='输出格式 (默认: txt)'
    )
    parser.add_argument(
        '--selftest',
        action='store_true',
        help='运行内置自检'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='fb2cng 1.0.0'
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 正常转换模式
    if not args.input:
        print("错误: 需要指定输入文件 (或使用 --selftest 运行自检)")
        print("用法: python main.py <input.fb2> -o <output> -f <format>")
        return 1
    
    if not args.output:
        # 自动生成输出文件名
        input_path = Path(args.input)
        args.output = str(input_path.with_suffix(f".{args.format}"))
    
    try:
        converter = FB2Converter()
        result = converter.process_file(args.input, args.output, args.format)
        
        print(f"✅ 转换成功!")
        print(f"   标题: {result['title']}")
        print(f"   作者: {result['author']}")
        print(f"   章节: {result['chapters']}")
        print(f"   置信度: {result['confidence']:.1%}")
        print(f"   输出: {result['output_path']}")
        return 0
        
    except FB2ConverterError as e:
        print(f"❌ 转换失败: {e}")
        return 1
    except Exception as e:
        print(f"❌ 未预期错误: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
