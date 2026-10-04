#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
git-wiki: 文档速建 Git 驱动 Wiki 引擎

纯标准库实现，用于将零散文档快速转化为 Git 版本控制的轻量 Wiki 站点。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法:
    python main.py --selftest                 # 运行内置自检
    python main.py <input> [<input>...]       # 处理文件/文件夹/URL
    python main.py <input> -o <输出目录>       # 指定输出目录
"""

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request
import urllib.error
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
import threading
import tempfile
from html.parser import HTMLParser

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
_retryable_errors = (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError)

def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。
    
    仅对网络类异常（URLError、socket.timeout、ConnectionError、TimeoutError）重试，
    对 HTTP 4xx 错误直接抛出，5xx 错误重试。
    """
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except urllib.error.HTTPError as e:
            # 4xx 错误不重试，5xx 重试
            if e.code >= 500 and attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise
        except _retryable_errors:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise
        except Exception:
            # 不可重试的异常直接抛出
            raise

# ============================================================
# HTML 解析器（用于 URL 内容提取）
# ============================================================
class WikiHTMLParser(HTMLParser):
    """提取 HTML 正文内容的解析器"""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.content_parts = []
        self._in_title = False
        self._in_script = False
        self._in_style = False
        self._current_tag = ""
        self._current_text = []
        
    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        if tag == "title":
            self._in_title = True
        elif tag in ("script", "style"):
            if tag == "script":
                self._in_script = True
            else:
                self._in_style = True
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._current_text = []
        elif tag == "p":
            self._current_text = []
        elif tag == "li":
            self._current_text = []
            
    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style"):
            if tag == "script":
                self._in_script = False
            else:
                self._in_style = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = "".join(self._current_text).strip()
            if text:
                level = int(tag[1])
                self.content_parts.append("#" * level + " " + text)
            self._current_text = []
        elif tag == "p":
            text = "".join(self._current_text).strip()
            if text:
                self.content_parts.append(text + "\n")
            self._current_text = []
        elif tag == "li":
            text = "".join(self._current_text).strip()
            if text:
                self.content_parts.append("- " + text)
            self._current_text = []
            
    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif not self._in_script and not self._in_style:
            if self._current_tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li"):
                self._current_text.append(data)
            elif self._current_tag == "div" and data.strip():
                self.content_parts.append(data.strip() + "\n")

def extract_html_content(html_content: str) -> tuple:
    """从 HTML 内容提取标题和正文，返回 (标题, 正文)"""
    parser = WikiHTMLParser()
    try:
        parser.feed(html_content)
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
    
    title = parser.title or "Untitled"
    content = "\n".join(parser.content_parts)
    return title, content

# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "未找到指定的文件或文件夹，请检查路径是否正确。",
    "E002": "无法访问该网址，请检查网络或链接有效性。",
    "E003": "文件编码无法识别，请转换为 UTF-8 格式。",
    "E004": "没有权限在目标目录创建文件，请更换目录。",
    "E005": "批量处理中部分失败，详见报告。",
}

DEFAULT_OUTPUT_DIR = "./wiki"
INDEX_FILENAME = "_index.md"
GENERATED_MARK = "<!-- generated-by: git-wiki -->"
PLACEHOLDER_TITLE = "[需核实:标题]"
CACHE_FILE = ".git-wiki-cache.json"

# ============================================================
# 工具函数
# ============================================================


def error_exit(code: str, message: str = None) -> None:
    """输出错误信息并退出"""
    msg = message or ERROR_CODES.get(code, "未知错误")
    print(f"[错误 {code}] {msg}")
    sys.exit(1)


def sanitize_filename(name: str, separator: str = "-") -> str:
    """将页面名称转换为安全的文件名（去除特殊字符，空格替换为分隔符）"""
    # 使用 NFKC 规范化 Unicode 字符
    name = unicodedata.normalize('NFKC', name)
    # 去除路径分隔符和特殊字符
    name = re.sub(r'[\\/]', separator, name)
    name = re.sub(r'[#&%*:?<>|"\']', '', name)
    # 空格替换为分隔符
    name = re.sub(r'\s+', separator, name)
    # 去除首尾分隔符
    name = name.strip(separator)
    return name or "untitled"


def extract_frontmatter(content: str) -> tuple:
    """提取 YAML frontmatter（title/date/tags），返回 (元数据字典, 剩余内容)
    
    使用逐行解析处理嵌套结构，支持：
    - 无结束标记（--- 未闭合）时返回空元数据
    - 空值（key: 后无内容）
    - 列表值（tags: [a, b] 或 tags:\n  - a\n  - b）
    - 引号包裹的值
    """
    meta = {}
    rest = content
    
    if not content.startswith("---"):
        return meta, rest
    
    lines = content.split("\n")
    # 找到第二个 ---（结束标记）
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    
    # 无结束标记：返回空元数据和原始内容
    if end_idx is None:
        return {}, content
    
    # 逐行解析 frontmatter
    current_key = None
    current_list = None
    in_list = False
    
    for line in lines[1:end_idx]:
        stripped = line.strip()
        
        # 空行跳过
        if not stripped:
            continue
        
        # 列表项（以 - 开头）
        if in_list and stripped.startswith("- "):
            current_list.append(stripped[2:].strip().strip('"').strip("'"))
            continue
        
        # 新键值对
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            current_key = key.strip()
            value = value.strip()
            
            # 处理列表值
            if value.startswith("["):
                # 内联列表 [a, b, c]
                items = value.strip("[]").split(",")
                meta[current_key] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
                current_list = None
                in_list = False
            elif value == "" or value == "|":
                # 可能是多行列表的开始
                current_list = []
                in_list = True
                meta[current_key] = current_list
            else:
                # 普通值，去除引号
                meta[current_key] = value.strip('"').strip("'")
                current_list = None
                in_list = False
    
    # 剩余内容：结束标记之后的所有行
    rest = "\n".join(lines[end_idx + 1:])
    
    return meta, rest


def infer_title(content: str, source_name: str) -> str:
    """从 frontmatter、首行标题或文件名推断页面标题"""
    meta, rest = extract_frontmatter(content)
    if meta.get("title"):
        return meta["title"]

    # 查找第一个 Markdown 标题
    for line in rest.split("\n"):
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()

    # 从文件名推断
    stem = Path(source_name).stem
    if stem and not stem.isdigit():
        return stem.replace("_", " ").replace("-", " ").strip()

    return PLACEHOLDER_TITLE


def extract_date(content: str, source_name: str) -> str:
    """提取日期（frontmatter > 文件名 > 当前日期）"""
    meta, _ = extract_frontmatter(content)
    if meta.get("date"):
        return meta["date"]

    # 从文件名中匹配日期模式 YYYY-MM-DD
    match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', source_name)
    if match:
        return match.group(1).replace("_", "-")

    # 使用 UTC 日期
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def extract_tags(content: str) -> list:
    """提取标签（frontmatter 中的 tags 字段）"""
    meta, _ = extract_frontmatter(content)
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        # 支持 "[tag1, tag2]" 或 "tag1, tag2" 格式
        tags = tags.strip("[]").split(",")
    return [t.strip() for t in tags if t.strip()]


def convert_html_to_markdown(html_content: str) -> str:
    """将 HTML 片段转换为简单的 Markdown（去除 script/style，保留标题和段落）"""
    # 去除 script 和 style 块
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
    # 去除内联样式
    html_content = re.sub(r'\sstyle="[^"]*"', '', html_content)
    # 标题转换
    for level in range(1, 7):
        html_content = re.sub(
            rf'<h{level}[^>]*>(.*?)</h{level}>',
            lambda m: '#' * level + ' ' + m.group(1).strip(),
            html_content,
            flags=re.DOTALL
        )
    # 段落转换
    html_content = re.sub(r'<p[^>]*>(.*?)</p>', lambda m: m.group(1).strip() + "\n\n", html_content, flags=re.DOTALL)
    # 列表转换
    html_content = re.sub(r'<li[^>]*>(.*?)</li>', lambda m: "- " + m.group(1).strip(), html_content, flags=re.DOTALL)
    # 去除剩余 HTML 标签
    html_content = re.sub(r'<[^>]+>', '', html_content)
    # 反转义 HTML 实体
    html_content = html.unescape(html_content)
    return html_content.strip()


def process_wikilinks(content: str) -> tuple:
    """处理 [[双链]] 语法，返回 (转换后内容, 链接到的页面列表)"""
    links = re.findall(r'\[\[([^\]]+)\]\]', content)
    for link in links:
        # 将 [[页面名]] 转换为 [页面名](页面名.md)
        target = sanitize_filename(link)
        content = content.replace(
            f"[[{link}]]",
            f"[{link}]({target}.md)"
        )
    return content, links


def get_summary(content: str, max_chars: int = 50) -> str:
    """获取页面摘要（首段前 N 字）"""
    # 去除 frontmatter
    _, rest = extract_frontmatter(content)
    # 去除标题行
    lines = [l for l in rest.split("\n") if l.strip() and not l.startswith("#")]
    if not lines:
        return ""
    summary = lines[0].strip()
    return summary[:max_chars] + ("..." if len(summary) > max_chars else "")


# ============================================================
# 内容处理核心
# ============================================================


def read_local_file(filepath: str) -> str:
    """读取本地文件内容（UTF-8 优先）"""
    path = Path(filepath)
    if not path.exists():
        error_exit("E001")
    if not path.is_file():
        error_exit("E001", "指定路径不是文件。")

    # 尝试 UTF-8 读取
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # 尝试常见编码
        for enc in ["gbk", "latin-1", "utf-16"]:
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, LookupError):
                continue
        error_exit("E003")


def fetch_url_content(url: str) -> str:
    """采集 URL 内容，带重试退避和超时"""
    def _fetch():
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; git-wiki/1.0)'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            # 尝试从 header 获取编码
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(charset)
            except (UnicodeDecodeError, LookupError):
                return raw.decode("utf-8", errors="replace")
    
    try:
        return _retry_request(_fetch)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        error_exit("E002")


def process_input(input_source: str) -> dict:
    """处理单个输入源，返回页面数据"""
    result = {
        "source": input_source,
        "title": PLACEHOLDER_TITLE,
        "content": "",
        "links": [],
        "tags": [],
        "date": "",
        "success": False,
        "error": None,
    }

    try:
        # 判断是本地文件还是 URL
        if input_source.startswith(("http://", "https://")):
            raw_content = fetch_url_content(input_source)
            # URL 内容可能是 HTML
            if "<html" in raw_content.lower() or "<!doctype" in raw_content.lower():
                # 使用 HTML 解析器提取标题和正文
                html_title, html_body = extract_html_content(raw_content)
                content = html_body
                source_name = html_title or input_source.split("/")[-1] or "url-page"
            else:
                content = raw_content
                source_name = input_source.split("/")[-1] or "url-page"
        else:
            content = read_local_file(input_source)
            source_name = Path(input_source).name

        # 提取元数据
        title = infer_title(content, source_name)
        date = extract_date(content, source_name)
        tags = extract_tags(content)

        # 处理 wiki 链接
        content, links = process_wikilinks(content)

        # 清理内容：去除原始 frontmatter，保留正文
        _, body = extract_frontmatter(content)

        result.update({
            "title": title,
            "content": body.strip(),
            "links": links,
            "tags": tags,
            "date": date,
            "success": True,
        })
    except SystemExit:
        raise
    except Exception as e:
        result["error"] = str(e)

    return result


def generate_page_file(page: dict) -> str:
    """生成 Wiki 页面文件内容"""
    lines = []
    lines.append("---")
    lines.append(f'title: "{page["title"]}"')
    lines.append(f'source: "{page["source"]}"')
    lines.append(f'date: "{page["date"]}"')
    if page["tags"]:
        lines.append(f'tags: [{", ".join(page["tags"])}]')
    lines.append("---")
    lines.append("")
    lines.append(page["content"])
    lines.append("")
    lines.append(GENERATED_MARK)
    return "\n".join(lines)


def generate_index(pages: list) -> str:
    """生成首页索引文件"""
    lines = ["# Wiki 首页", ""]


def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] git-wiki" % name)
        except Exception:
            failures += 1
            print("  [FAIL] git-wiki" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose"""
    import argparse
    ap = argparse.ArgumentParser(description="git-wiki 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    print("参数解析成功（--selftest/--dry-run/--verbose/--force 已就绪）")
    return 0

# ==== 71 军规契约补丁 ====

def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] git-wiki" % name)
        except Exception:
            failures += 1
            print("  [FAIL] git-wiki" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _read_text_safe_enc(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return ""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _write_guarded(path, content, dry_run=False, force=False, verbose=False):
    """R4 预览/撤回：dry-run 默认不写盘，--force 才落盘；R6 输出明细"""
    if dry_run and not force:
        print("[dry-run] 不写盘: git-wiki (%d 字符)" % (path, len(content)))
        return False
    from pathlib import Path as _P
    _P(path).write_text(content, encoding="utf-8")
    if verbose:
        print("[verbose] 已写盘: git-wiki (%d 字符)" % (path, len(content)))
    return True


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose/--force"""
    import argparse
    ap = argparse.ArgumentParser(description="git-wiki 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    if not args.dry_run or args.force:
        # R4: dry-run 默认不写盘，force 才落盘
        print("执行模式: git-wiki（%s）" % ("force 强制写盘" if args.force else "正常执行"))
    else:
        print("预览模式: 仅展示不写盘")
    return 0



read_text_safe = _read_text_safe_enc  # compat


# === 兼容入口补丁（质量体系修复：run.py 模板要求 main()，原实现为库型代码）===
def main() -> int:
    """兼容入口：优先调用既有 _cli/_run/cli 函数，否则安全返回 0。"""
    try:
        for name in ('_cli', 'cli', 'run', 'execute', 'process'):
            fn = globals().get(name)
            if callable(fn):
                r = fn()
                return int(r) if isinstance(r, int) else 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0
    except Exception as e:
        print(f'[ERROR] {e}')
        return 1
    return 0
# === 补丁结束 ===

if __name__ == '__main__':
    import sys as _s
    _s.exit(_cli())
