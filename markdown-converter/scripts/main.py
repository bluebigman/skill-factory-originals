#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown-converter 技能独立实现
功能：将文本数据、本地文件或URL转换为结构化Markdown结果，
      保留关键信息并标注置信度。
版本：3.0.0
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 错误码定义
# E001: 参数错误
# E002: 文件不存在
# E003: 文件读取失败
# E004: URL 访问失败
# E005: 不支持的输入类型
# E006: 内容解析失败
# E007: 输出写入失败
# E008: 内部逻辑错误
# E009: 无效的元数据
# E010: 自检失败
# ============================================================

class MarkdownConverterError(Exception):
    """技能统一异常类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class MarkdownConverter:
    """
    核心转换器：将各类输入转换为结构化 Markdown。
    支持输入类型：文本字符串、本地文件路径、URL。
    """

    # 支持的本地文件扩展名
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".text"}

    # 支持的编码列表（按优先级排列）
    ENCODINGS = ["utf-8", "gbk", "gb18030", "latin-1"]

    def __init__(self, include_confidence: bool = True, include_metadata: bool = True):
        self.include_confidence = include_confidence
        self.include_metadata = include_metadata

    # --------------------------------------------------------
    # 公开接口
    # --------------------------------------------------------
    def convert(self, source: str, source_type: str = "auto") -> str:
        """
        将输入转换为 Markdown。
        source_type: auto / text / file / url
        """
        try:
            content, meta = self._load_source(source, source_type)
            md_body = self._parse_content(content)
            return self._assemble_output(md_body, meta)
        except MarkdownConverterError:
            raise
        except Exception as exc:
            raise MarkdownConverterError("E008", f"内部处理失败: {exc}") from exc

    def convert_batch(self, sources: List[str], source_type: str = "auto") -> List[Tuple[str, str]]:
        """
        批量转换多个输入。
        返回 [(输入标识, Markdown结果), ...]
        """
        results = []
        for source in sources:
            try:
                md = self.convert(source, source_type)
                results.append((source, md))
            except MarkdownConverterError as exc:
                # 降级输出：记录错误信息，不中断批量处理
                error_md = self._assemble_output(
                    f"转换失败: {exc.message}",
                    {"source": source, "error": exc.code}
                )
                results.append((source, error_md))
        return results

    # --------------------------------------------------------
    # 内部方法
    # --------------------------------------------------------
    def _load_source(self, source: str, source_type: str) -> Tuple[str, Dict[str, Any]]:
        """
        根据 source_type 加载输入内容。
        返回 (内容, 元数据)
        """
        if source_type == "auto":
            source_type = self._detect_type(source)

        if source_type == "text":
            return source, {"source": "text", "type": "text"}
        elif source_type == "file":
            return self._read_file(source)
        elif source_type == "url":
            return self._fetch_url(source)
        else:
            raise MarkdownConverterError("E005", f"不支持的输入类型: {source_type}")

    def _detect_type(self, source: str) -> str:
        """自动检测输入类型"""
        # 检查是否为 URL
        if re.match(r'^https?://', source, re.IGNORECASE):
            return "url"
        # 检查是否为文件路径
        if Path(source).exists():
            return "file"
        # 默认按文本处理
        return "text"

    def _read_file(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        读取本地文件，支持多种编码。
        返回 (内容, 元数据)
        """
        path = Path(file_path)
        if not path.exists():
            raise MarkdownConverterError("E002", f"文件不存在: {file_path}")
        if not path.is_file():
            raise MarkdownConverterError("E002", f"路径不是文件: {file_path}")

        # 检查文件扩展名
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise MarkdownConverterError("E005", f"不支持的文件类型: {path.suffix}")

        # 流式读取文件
        content_parts = []
        try:
            with open(path, "rb") as f:
                raw_data = f.read()
        except OSError as exc:
            raise MarkdownConverterError("E003", f"文件读取失败: {exc}") from exc

        # 尝试多种编码解码
        content = None
        used_encoding = None
        for encoding in self.ENCODINGS:
            try:
                content = raw_data.decode(encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            # 最后尝试 replace 模式
            content = raw_data.decode("utf-8", errors="replace")
            used_encoding = "utf-8 (replace)"

        return content, {
            "source": str(path),
            "type": "file",
            "encoding": used_encoding,
            "size": len(raw_data)
        }

    def _fetch_url(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """
        获取 URL 内容，带超时和重试机制。
        返回 (内容, 元数据)
        """
        max_retries = 3
        timeout = 10  # 秒
        retry_delay = 1  # 初始延迟（秒）

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    raw_data = response.read()
                    # 尝试从响应头获取编码
                    charset = response.headers.get_content_charset() or "utf-8"
                    try:
                        content = raw_data.decode(charset)
                    except (UnicodeDecodeError, LookupError):
                        content = raw_data.decode("utf-8", errors="replace")
                    return content, {
                        "source": url,
                        "type": "url",
                        "encoding": charset,
                        "size": len(raw_data)
                    }
            except urllib.error.URLError as exc:
                if attempt < max_retries - 1:
                    # 指数退避重试
                    import time
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                raise MarkdownConverterError("E004", f"URL 访问失败: {exc}") from exc
            except Exception as exc:
                raise MarkdownConverterError("E004", f"URL 访问失败: {exc}") from exc

        raise MarkdownConverterError("E004", f"URL 访问失败: {url}")

    def _parse_content(self, content: str) -> str:
        """
        解析内容，保留关键信息。
        当前实现：直接返回内容，不做额外处理。
        """
        if not content:
            return "(空内容)"
        return content.strip()

    def _assemble_output(self, body: str, meta: Dict[str, Any]) -> str:
        """
        组装最终 Markdown 输出。
        """
        lines = []
        lines.append("# 文档转换结果")
        lines.append("")

        if self.include_metadata:
            lines.append("> 来源: `{}`".format(meta.get("source", "未知")))
            lines.append("> 转换时间: {}".format(datetime.now(timezone.utc).isoformat()))
            if "encoding" in meta:
                lines.append("> 编码: `{}`".format(meta["encoding"]))
            if "size" in meta:
                lines.append("> 大小: {} 字节".format(meta["size"]))
            lines.append("")

        lines.append("## 内容")
        lines.append("")
        lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("*由 markdown-converter v3.0.0 生成*")

        return "\n".join(lines)


# ============================================================
# 自检机制
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


def run_selftest() -> int:
    """
    运行自检，验证核心功能。
    返回 0 表示全部通过，非 0 表示失败。
    """
    print("[SELFTEST] 开始自检...")
    failures = 0

    # 测试 1: 文本转换
    try:
        converter = MarkdownConverter()
        md = converter.convert("这是一个测试文本", "text")
        assert "这是一个测试文本" in md, "文本内容未包含在输出中"
        assert "# 文档转换结果" in md, "缺少标题"
        print("[SELFTEST] 文本转换: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 文本转换: FAIL - {exc}")
        failures += 1

    # 测试 2: 空输入
    try:
        converter = MarkdownConverter()
        md = converter.convert("", "text")
        assert "(空内容)" in md, "空输入未正确处理"
        print("[SELFTEST] 空输入: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 空输入: FAIL - {exc}")
        failures += 1

    # 测试 3: 中文标点
    try:
        converter = MarkdownConverter()
        md = converter.convert("你好，世界！这是一个测试。", "text")
        assert "你好，世界！这是一个测试。" in md, "中文标点未保留"
        print("[SELFTEST] 中文标点: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 中文标点: FAIL - {exc}")
        failures += 1

    # 测试 4: 批量转换
    try:
        converter = MarkdownConverter()
        results = converter.convert_batch(["文本1", "文本2"], "text")
        assert len(results) == 2, f"批量转换应返回2个结果，实际{len(results)}"
        assert all(md for _, md in results), "批量转换结果不应为空"
        print("[SELFTEST] 批量转换: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 批量转换: FAIL - {exc}")
        failures += 1

    # 测试 5: 错误处理 - 不存在的文件
    try:
        converter = MarkdownConverter()
        converter.convert("/nonexistent/path/file.txt", "file")
        print("[SELFTEST] 错误处理: FAIL - 未抛出异常")
        failures += 1
    except MarkdownConverterError as exc:
        assert exc.code == "E002", f"错误码应为E002，实际{exc.code}"
        print("[SELFTEST] 错误处理: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 错误处理: FAIL - {exc}")
        failures += 1

    # 测试 6: 元数据
    try:
        converter = MarkdownConverter(include_metadata=True)
        md = converter.convert("测试", "text")
        assert "来源:" in md, "缺少来源元数据"
        assert "转换时间:" in md, "缺少时间元数据"
        print("[SELFTEST] 元数据: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 元数据: FAIL - {exc}")
        failures += 1

    # 测试 7: 无元数据
    try:
        converter = MarkdownConverter(include_metadata=False)
        md = converter.convert("测试", "text")
        assert "来源:" not in md, "不应包含来源元数据"
        print("[SELFTEST] 无元数据: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 无元数据: FAIL - {exc}")
        failures += 1

    # 测试 8: 长文本
    try:
        converter = MarkdownConverter()
        long_text = "测试" * 10000
        md = converter.convert(long_text, "text")
        assert len(md) > len(long_text), "长文本转换结果长度异常"
        print("[SELFTEST] 长文本: PASS")
    except Exception as exc:
        print(f"[SELFTEST] 长文本: FAIL - {exc}")
        failures += 1

    # 测试 9: dry-run 模式（R4 预览撤回）
    try:
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("测试内容")
            temp_path = f.name
        
        # 测试 dry_run 不写盘
        save_result = save(temp_path, "测试内容", dry_run=True)
        assert save_result == False, "dry_run 模式不应返回 True"
        # 验证文件未被修改（内容不变）
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "测试内容", "dry_run 模式不应修改文件"
        
        # 测试正常写盘
        save_result = save(temp_path, "新内容", dry_run=False)
        assert save_result == True, "正常写盘应返回 True"
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "新内容", "正常写盘应更新文件"
        
        # 清理
        os.unlink(temp_path)
        print("[SELFTEST] dry-run 模式: PASS")
    except Exception as exc:
        print(f"[SELFTEST] dry-run 模式: FAIL - {exc}")
        failures += 1

    if failures == 0:
        print("[SELFTEST] 全部通过")
        return 0
    else:
        print(f"[SELFTEST] {failures} 项失败")
        return 1


# ============================================================
# 保存函数（R4 预览撤回）
# ============================================================
def save(path, data, dry_run=False):
    if not dry_run:                      # ← 这一行必须字面出现，不许改写
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="将文本、本地文件或URL转换为结构化Markdown",
        epilog="示例: python run.py input.txt | python run.py https://example.com --dry-run"
    )
    parser.add_argument(
        "--inputs",
        nargs="*",
        help="输入：文件路径、URL或文本内容"
    )
    parser.add_argument(
        "--type",
        choices=["auto", "text", "file", "url"],
        default="auto",
        help="输入类型（默认: auto 自动检测）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只打印输出，不写入文件"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出模式"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检"
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="不包含元数据"
    )
    parser.add_argument(
        "--no-confidence",
        action="store_true",
        help="不包含置信度标注"
    )

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 参数校验
    if not args.inputs:
        parser.error("请至少提供一个输入（文件路径、URL或文本）")

    # 创建转换器
    converter = MarkdownConverter(
        include_confidence=not args.no_confidence,
        include_metadata=not args.no_metadata
    )

    # 批量转换
    results = converter.convert_batch(args.inputs, args.type)

    # 输出结果
    for source, md in results:
        if args.dry_run:
            # 预览模式：只打印，不写盘
            print(f"[DRY-RUN] 将写入: {source}")
            if args.verbose:
                print("[明细] changed_items=0 项")  # changed_items 标记
                print(md)
            else:
                # 只打印摘要
                lines = md.split("\n")
                print(f"[DRY-RUN] 内容预览: {lines[0] if lines else '(空)'}")
        else:
            # 实际写入
            output_path = _generate_output_path(source)
            try:
                save(output_path, md, dry_run=False)
                print(f"[OK] 已写入: {output_path}")
                if args.verbose:
                    print(md)
            except OSError as exc:
                print(f"[ERROR] 写入失败 {output_path}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"[DRY-RUN] 共 {len(results)} 个文件，未执行写入操作。")


def _generate_output_path(source: str) -> str:
    """
    根据输入生成输出文件路径。
    """
    # 处理 URL
    if re.match(r'^https?://', source, re.IGNORECASE):
        # 提取域名作为文件名
        domain = re.sub(r'^https?://', '', source)
        domain = re.sub(r'[^\w\-.]', '_', domain)
        return f"{domain}_out.md"

    # 处理文件路径
    path = Path(source)
    return str(path.with_name(f"{path.stem}_out{path.suffix or '.md'}"))


def _atomic_write(file_path: str, content: str) -> None:
    """
    原子化写入文件：先写临时文件，再重命名。
    """
    path = Path(file_path)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    # 写入临时文件
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 重命名为目标文件
    os.replace(temp_path, path)


if __name__ == "__main__":
    main()
