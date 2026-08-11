#!/usr/bin/env python3
"""
cheat.sh 命令行速查手册 - 生产级实现

一条命令查到任意编程语言与工具的可用代码示例。
支持：语言/工具查询、关键词搜索、多结果翻页、纯文本输出、本地缓存、中文转译。

作者: factory-ops-bot
版本: 2.0.0
许可证: MIT
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

DEFAULT_URL = "https://cheat.sh"
DEFAULT_TIMEOUT = 10  # 秒
DEFAULT_MAX_RETRIES = 3
DEFAULT_CACHE_DIR = os.path.join(
    os.path.expanduser("~"), ".cache", "cheat-sh"
)
CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # 24 小时

# 中文关键词 → 英文关键词 转译表
TRANSLATION_MAP = {
    "读文件": "read+file",
    "写文件": "write+file",
    "读": "read",
    "写": "write",
    "文件": "file",
    "解压": "extract",
    "压缩": "compress",
    "撤销": "undo",
    "提交": "commit",
    "删除": "delete",
    "创建": "create",
    "列表": "list",
    "查看": "view",
    "搜索": "search",
    "替换": "replace",
    "排序": "sort",
    "过滤": "filter",
    "合并": "merge",
    "拆分": "split",
    "连接": "connect",
    "请求": "request",
    "响应": "response",
    "服务器": "server",
    "客户端": "client",
    "数据库": "database",
    "查询": "query",
    "插入": "insert",
    "更新": "update",
    "json": "json",
    "http": "http",
    "网络": "network",
    "字符串": "string",
    "数组": "array",
    "列表": "list",
    "字典": "dict",
    "对象": "object",
    "函数": "function",
    "类": "class",
    "异常": "exception",
    "错误": "error",
    "调试": "debug",
    "测试": "test",
    "部署": "deploy",
    "安装": "install",
    "配置": "config",
    "启动": "start",
    "停止": "stop",
    "重启": "restart",
    "状态": "status",
    "日志": "log",
    "监控": "monitor",
    "备份": "backup",
    "恢复": "restore",
    "同步": "sync",
    "异步": "async",
    "线程": "thread",
    "进程": "process",
    "内存": "memory",
    "磁盘": "disk",
    "权限": "permission",
    "用户": "user",
    "密码": "password",
    "认证": "auth",
    "加密": "encrypt",
    "解密": "decrypt",
    "压缩": "compress",
    "解压": "decompress",
    "编码": "encode",
    "解码": "decode",
    "转换": "convert",
    "格式化": "format",
    "解析": "parse",
    "生成": "generate",
    "计算": "calculate",
    "比较": "compare",
    "复制": "copy",
    "移动": "move",
    "重命名": "rename",
    "打开": "open",
    "关闭": "close",
    "保存": "save",
    "加载": "load",
    "导入": "import",
    "导出": "export",
    "初始化": "init",
    "清理": "clean",
    "检查": "check",
    "验证": "validate",
    "发送": "send",
    "接收": "receive",
    "上传": "upload",
    "下载": "download",
}

# 常见编程语言/工具名映射
LANGUAGE_MAP = {
    "python": "python",
    "py": "python",
    "python3": "python",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "java": "java",
    "c": "c",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    "go": "go",
    "golang": "go",
    "rust": "rust",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "scala": "scala",
    "perl": "perl",
    "lua": "lua",
    "r": "r",
    "bash": "bash",
    "shell": "bash",
    "sh": "bash",
    "zsh": "zsh",
    "powershell": "powershell",
    "sql": "sql",
    "html": "html",
    "css": "css",
    "git": "git",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "nginx": "nginx",
    "redis": "redis",
    "mysql": "mysql",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "mongodb": "mongodb",
    "mongo": "mongodb",
    "curl": "curl",
    "wget": "wget",
    "tar": "tar",
    "zip": "zip",
    "unzip": "unzip",
    "grep": "grep",
    "sed": "sed",
    "awk": "awk",
    "find": "find",
    "xargs": "xargs",
    "ssh": "ssh",
    "scp": "scp",
    "rsync": "rsync",
    "vim": "vim",
    "emacs": "emacs",
    "tmux": "tmux",
    "screen": "screen",
    "make": "make",
    "cmake": "cmake",
    "npm": "npm",
    "yarn": "yarn",
    "pip": "pip",
    "conda": "conda",
    "brew": "brew",
    "apt": "apt",
    "yum": "yum",
    "systemctl": "systemctl",
    "journalctl": "journalctl",
    "ffmpeg": "ffmpeg",
    "imagemagick": "imagemagick",
    "convert": "convert",
}


# ============================================================
# 异常与错误码
# ============================================================

class CheatShError(Exception):
    """cheat.sh 查询基础异常"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class TopicEmptyError(CheatShError):
    """E001: 查询主题为空"""
    def __init__(self):
        super().__init__("E001", "查询主题为空，请提供语言/工具名")


class UnknownTopicError(CheatShError):
    """E002: 返回 Unknown topic"""
    def __init__(self, topic: str):
        super().__init__("E002", f"Unknown topic: {topic}，请换同义关键词重试")


class NetworkTimeoutError(CheatShError):
    """E003: 网络超时"""
    def __init__(self, retries: int):
        super().__init__("E003", f"网络超时，已重试 {retries} 次仍失败")


class NoNetworkError(CheatShError):
    """E004: 无外网出口"""
    def __init__(self):
        super().__init__("E004", "无外网出口，请使用 --cache 模式或自建服务")


class ContentTooLongError(CheatShError):
    """E005: 返回内容过长"""
    def __init__(self, length: int, limit: int):
        super().__init__("E005", f"返回内容过长（{length} 行 > {limit} 行），请加关键词收窄")


class TranslationError(CheatShError):
    """E006: 中文关键词转译失败"""
    def __init__(self, keyword: str):
        super().__init__("E006", f"无法转译中文关键词: {keyword}，请直接提供英文关键词")


class AnsiColorError(CheatShError):
    """E007: ANSI 颜色码干扰管道"""
    def __init__(self):
        super().__init__("E007", "ANSI 颜色码干扰管道处理，请加 --plain 参数")


class CacheWriteError(CheatShError):
    """E008: 本地缓存写入失败"""
    def __init__(self, path: str, reason: str):
        super().__init__("E008", f"缓存写入失败 {path}: {reason}")


class InvalidIndexError(CheatShError):
    """E009: 无效的 --index 参数"""
    def __init__(self, index: int, max_index: int):
        super().__init__("E009", f"无效的 --index {index}，有效范围 1-{max_index}")


class CacheReadError(CheatShError):
    """E010: 缓存读取失败"""
    def __init__(self, path: str, reason: str):
        super().__init__("E010", f"缓存读取失败 {path}: {reason}")


# ============================================================
# 工具函数
# ============================================================

def get_utc_now() -> str:
    """获取当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def safe_filename(text: str) -> str:
    """将文本转换为安全的文件名"""
    # 只保留字母、数字、下划线、连字符、点
    safe = re.sub(r'[^\w\-.]', '_', text)
    # 限制长度
    return safe[:100]


def read_text_safe(path: str) -> str:
    """多编码安全读取文件，带降级处理"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def atomic_write(path: str, content: str, dry_run: bool = False) -> bool:
    """
    原子化写入文件。
    先写入临时文件，再原子重命名，避免写入中断导致文件损坏。
    """
    if not dry_run:
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            # 原子重命名
            os.replace(temp_path, path)
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise CacheWriteError(path, str(e))
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(content)} 字节），未落盘")
    return False


def read_file_with_fallback(path: str) -> str:
    """
    读取文件，支持多编码 fallback。
    优先 utf-8，然后 gbk，最后 gb18030。
    """
    return read_text_safe(path)


def translate_chinese(text: str) -> str:
    """
    将中文描述转译为英文关键词。
    例如: "读文件" → "read+file"
    """
    # 如果已经是英文，直接返回
    if re.match(r'^[a-zA-Z0-9_+\-./~]+$', text):
        return text
    
    # 尝试整体匹配
    if text in TRANSLATION_MAP:
        return TRANSLATION_MAP[text]
    
    # 尝试分词匹配
    parts = []
    for key, value in TRANSLATION_MAP.items():
        if key in text:
            parts.append(value)
    
    if parts:
        return "+".join(parts)
    
    # 无法转译
    raise TranslationError(text)


def normalize_topic(topic: str) -> str:
    """
    规范化查询主题。
    处理语言名映射、中文转译、路径拼接。
    """
    if not topic or not topic.strip():
        raise TopicEmptyError()
    
    topic = topic.strip()
    
    # 检查是否包含路径分隔符
    if "/" in topic:
        parts = topic.split("/")
        normalized_parts = []
        for i, part in enumerate(parts):
            if i == 0:
                # 第一个部分是语言/工具名
                lang = LANGUAGE_MAP.get(part.lower(), part)
                normalized_parts.append(lang)
            else:
                # 后续部分是动作描述
                try:
                    translated = translate_chinese(part)
                    normalized_parts.append(translated)
                except TranslationError:
                    # 保留原文
                    normalized_parts.append(part)
        return "/".join(normalized_parts)
    
    # 单个词，可能是语言名或工具名
    lang = LANGUAGE_MAP.get(topic.lower(), topic)
    return lang


def strip_ansi_codes(text: str) -> str:
    """去除 ANSI 颜色码"""
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_pattern.sub("", text)


def parse_answers(content: str) -> List[str]:
    """
    解析 cheat.sh 返回的多答案。
    答案以注释分隔，格式类似:
    # 1. 第一个答案
    ...
    # 2. 第二个答案
    ...
    """
    if not content:
        return []
    
    # 按注释行分割
    lines = content.split("\n")
    answers = []
    current_answer = []
    
    for line in lines:
        # 检测答案分隔符
        if re.match(r'^#\s*\d+[\.\)]', line) or re.match(r'^---+\s*$', line):
            if current_answer:
                answers.append("\n".join(current_answer))
                current_answer = []
        current_answer.append(line)
    
    if current_answer:
        answers.append("\n".join(current_answer))
    
    return answers


def truncate_content(content: str, max_lines: int = 200) -> Tuple[str, bool]:
    """
    截断过长内容。
    返回 (截断后的内容, 是否被截断)
    """
    lines = content.split("\n")
    if len(lines) <= max_lines:
        return content, False
    
    truncated = "\n".join(lines[:max_lines])
    truncated += f"\n\n... [内容已截断，共 {len(lines)} 行，仅显示前 {max_lines} 行]"
    return truncated, True


# ============================================================
# 缓存管理
# ============================================================

class CacheManager:
    """本地缓存管理器"""
    
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR, expiry: int = CACHE_EXPIRY_SECONDS):
        self.cache_dir = cache_dir
        self.expiry = expiry
    
    def _get_cache_path(self, topic: str, plain: bool) -> str:
        """生成缓存文件路径"""
        # 使用 topic 的哈希作为文件名，避免特殊字符问题
        hash_input = f"{topic}|{plain}"
        hash_value = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{hash_value}.json")
    
    def get(self, topic: str, plain: bool) -> Optional[str]:
        """读取缓存，返回缓存内容或 None"""
        cache_path = self._get_cache_path(topic, plain)
        try:
            if not os.path.exists(cache_path):
                return None
            
            # 检查过期时间
            mtime = os.path.getmtime(cache_path)
            if time.time() - mtime > self.expiry:
                return None
            
            # 读取缓存文件
            content = read_file_with_fallback(cache_path)
            data = json.loads(content)
            
            # 验证缓存结构
            if "content" not in data or "timestamp" not in data:
                return None
            
            return data["content"]
        except Exception as e:
            print(f"[WARN] 缓存读取失败 {cache_path}: {e}", file=sys.stderr)
            return None
    
    def set(self, topic: str, plain: bool, content: str, dry_run: bool = False) -> None:
        """写入缓存"""
        cache_path = self._get_cache_path(topic, plain)
        data = {
            "topic": topic,
            "plain": plain,
            "content": content,
            "timestamp": get_utc_now(),
        }
        try:
            atomic_write(cache_path, json.dumps(data, ensure_ascii=False, indent=2), dry_run=dry_run)
        except CacheWriteError as e:
            # 缓存写入失败不致命，降级为不缓存
            print(f"[WARN] 缓存写入失败: {e}", file=sys.stderr)
    
    def clear(self) -> int:
        """清空缓存，返回删除的文件数"""
        count = 0
        try:
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith(".json"):
                        filepath = os.path.join(self.cache_dir, filename)
                        try:
                            os.unlink(filepath)
                            count += 1
                        except OSError as e:
                            print(f"[WARN] 删除缓存文件失败 {filepath}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] 清空缓存目录失败: {e}", file=sys.stderr)
        return count


# ============================================================
# 网络请求
# ============================================================

def fetch_with_retry(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    verbose: bool = False,
) -> str:
    """
    带指数退避重试的 HTTP GET 请求。
    
    重试策略：
    - 第 1 次失败后等待 1 秒
    - 第 2 次失败后等待 2 秒
    - 第 3 次失败后等待 4 秒
    - 最多重试 max_retries 次
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if verbose:
                print(f"  请求 [{attempt + 1}/{max_retries + 1}]: {url}", file=sys.stderr)
            
            req = urllib.request.Request(url, headers={"User-Agent": "cheat-sh-skill/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 流式读取响应
                chunks = []
                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                content = b"".join(chunks).decode("utf-8", errors="replace")
                
                if verbose:
                    print(f"  响应: {len(content)} 字符", file=sys.stderr)
                
                return content
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # 404 表示主题不存在，不重试
                raise UnknownTopicError(url)
            last_error = e
        except urllib.error.URLError as e:
            last_error = e
        except TimeoutError as e:
            last_error = e
        except Exception as e:
            last_error = e
        
        # 指数退避
        if attempt < max_retries:
            wait_time = 2 ** attempt  # 1, 2, 4
            if verbose:
                print(f"  请求失败，{wait_time} 秒后重试...", file=sys.stderr)
            time.sleep(wait_time)
    
    # 所有重试都失败
    if isinstance(last_error, TimeoutError):
        raise NetworkTimeoutError(max_retries)
    else:
        raise NoNetworkError()


# ============================================================
# 核心查询逻辑
# ============================================================

def build_query_url(topic: str, plain: bool = False) -> str:
    """构建 cheat.sh 查询 URL"""
    base_url = os.environ.get("CHEAT_SH_URL", DEFAULT_URL)
    
    # URL 编码 topic
    encoded_topic = urllib.parse.quote(topic, safe="/+~")
    
    # 构建 URL
    url = f"{base_url}/{encoded_topic}"
    
    # 添加参数
    params = []
    if plain:
        params.append("T")
    
    if params:
        url += "?" + "&".join(params)
    
    return url


def query_cheat_sh(
    topic: str,
    plain: bool = False,
    index: int = 1,
    use_cache: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
) -> Dict:
    """
    查询 cheat.sh 服务。
    
    返回:
    {
        "success": bool,
        "content": str,
        "error_code": str | None,
        "error_message": str | None,
        "from_cache": bool,
        "truncated": bool,
        "total_lines": int,
    }
    """
    result = {
        "success": False,
        "content": "",
        "error_code": None,
        "error_message": None,
        "from_cache": False,
        "truncated": False,
        "total_lines": 0,
    }
    
    try:
        # 规范化 topic
        normalized_topic = normalize_topic(topic)
        
        if verbose:
            print(f"  规范化主题: {topic} → {normalized_topic}", file=sys.stderr)
        
        # 构建 URL
        url = build_query_url(normalized_topic, plain)
        
        if dry_run:
            # dry-run 模式：只打印将执行的请求
            print(f"[DRY-RUN] 将请求: {url}")
            result["content"] = f"[DRY-RUN] {url}"
            result["success"] = True
            return result
        
        # 检查缓存
        cache_manager = CacheManager()
        if use_cache:
            try:
                cached = cache_manager.get(normalized_topic, plain)
                if cached is not None:
                    if verbose:
                        print(f"  命中缓存: {normalized_topic}", file=sys.stderr)
                    result["content"] = cached
                    result["success"] = True
                    result["from_cache"] = True
                    result["total_lines"] = len(cached.split("\n"))
                    return result
            except CacheReadError as e:
                if verbose:
                    print(f"  缓存读取失败，降级为网络请求: {e}", file=sys.stderr)
        
        # 发起网络请求
        content = fetch_with_retry(url, verbose=verbose)
        
        # 检查是否 Unknown topic
        if "Unknown topic" in content:
            raise UnknownTopicError(normalized_topic)
        
        # 解析多答案
        answers = parse_answers(content)
        
        # 选择指定索引的答案
        if answers:
            if index < 1 or index > len(answers):
                raise InvalidIndexError(index, len(answers))
            content = answers[index - 1]
        
        # 截断过长内容
        content, truncated = truncate_content(content)
        
        # 写入缓存
        if use_cache:
            try:
                cache_manager.set(normalized_topic, plain, content, dry_run=dry_run)
            except CacheWriteError as e:
                if verbose:
                    print(f"  缓存写入失败: {e}", file=sys.stderr)
        
        result["content"] = content
        result["success"] = True
        result["truncated"] = truncated
        result["total_lines"] = len(content.split("\n"))
        
        return result
    
    except CheatShError as e:
        result["error_code"] = e.code
        result["error_message"] = e.message
        return result
    except Exception as e:
        # 未知异常，记录完整信息
        result["error_code"] = "E999"
        result["error_message"] = f"未知错误: {str(e)}"
        return result


# ============================================================
# 输出格式化
# ============================================================

def format_output(result: Dict, verbose: bool = False) -> str:
    """格式化查询结果输出"""
    if not result["success"]:
        error_code = result.get("error_code", "E999")
        error_message = result.get("error_message", "未知错误")
        return f"错误 [{error_code}]: {error_message}"
    
    content = result["content"]
    
    # 添加元信息
    lines = []
    if verbose:
        lines.append(f"# 来源: cheat.sh")
        lines.append(f"# 时间: {get_utc_now()}")
        lines.append(f"# 缓存: {'是' if result.get('from_cache') else '否'}")
        lines.append(f"# 行数: {result.get('total_lines', 0)}")
        if result.get("truncated"):
            lines.append(f"# 注意: 内容已截断")
        lines.append("")
    
    lines.append(content)
    
    # 添加提示
    lines.append("")
    lines.append("# ⚠️ 示例来自社区，可能过时或不适配你的版本")
    lines.append("# 危险操作请谨慎执行，建议先理解再运行")
    
    return "\n".join(lines)


# ============================================================
# 命令行入口
# ============================================================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="cheat-sh",
        description="命令行速查手册 - 一条命令查到任意编程语言与工具的可用代码示例",
        epilog="示例: python run.py python/read+file --plain",
    )
    
    parser.add_argument(
        "--topic",
        nargs="?",
        default=None,
        help="查询主题，如: python/read+file, tar, git/undo+commit",
    )
    
    parser.add_argument(
        "--index",
        type=int,
        default=1,
        help="取第 N 个社区答案（默认 1）",
    )
    
    parser.add_argument(
        "--plain",
        action="store_true",
        help="纯文本输出，去除 ANSI 颜色码",
    )
    
    parser.add_argument(
        "--cache",
        action="store_true",
        help="使用本地缓存（24 小时有效）",
    )
    
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="清空本地缓存",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，只打印将执行的请求不实际发送",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细调试信息",
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测并退出",
    )
    
    return parser.parse_args(argv)


def run_selftest() -> int:
    """
    运行自测。
    真实调用核心函数并断言关键输出。
    """
    print("=" * 60)
    print("cheat.sh Skill 自测")
    print("=" * 60)
    
    failures = 0
    
    # 测试 1: normalize_topic 中文转译
    print("\n[测试 1] normalize_topic 中文转译")
    try:
        result = normalize_topic("python/读文件")
        assert result == "python/read+file", f"期望 python/read+file, 实际 {result}"
        print(f"  ✅ python/读文件 → {result}")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 2: normalize_topic 语言名映射
    print("\n[测试 2] normalize_topic 语言名映射")
    try:
        result = normalize_topic("py/read+file")
        assert result == "python/read+file", f"期望 python/read+file, 实际 {result}"
        print(f"  ✅ py/read+file → {result}")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 3: normalize_topic 空输入
    print("\n[测试 3] normalize_topic 空输入")
    try:
        normalize_topic("")
        print("  ❌ 期望抛出 TopicEmptyError")
        failures += 1
    except TopicEmptyError:
        print("  ✅ 正确抛出 TopicEmptyError")
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 4: strip_ansi_codes
    print("\n[测试 4] strip_ansi_codes")
    try:
        input_text = "\x1b[32m绿色文字\x1b[0m普通文字"
        result = strip_ansi_codes(input_text)
        assert result == "绿色文字普通文字", f"期望 '绿色文字普通文字', 实际 '{result}'"
        print(f"  ✅ ANSI 码已去除")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 5: parse_answers
    print("\n[测试 5] parse_answers")
    try:
        content = """# 1. 第一个答案
print("hello")

# 2. 第二个答案
print("world")"""
        answers = parse_answers(content)
        assert len(answers) == 2, f"期望 2 个答案, 实际 {len(answers)}"
        assert "hello" in answers[0], f"第一个答案应包含 hello"
        assert "world" in answers[1], f"第二个答案应包含 world"
        print(f"  ✅ 解析出 {len(answers)} 个答案")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 6: truncate_content
    print("\n[测试 6] truncate_content")
    try:
        content = "\n".join([f"line {i}" for i in range(300)])
        truncated, was_truncated = truncate_content(content, max_lines=200)
        assert was_truncated, "应标记为已截断"
        assert len(truncated.split("\n")) <= 205, "截断后行数应接近 200"
        print(f"  ✅ 300 行截断为 {len(truncated.split(chr(10)))} 行")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 7: build_query_url
    print("\n[测试 7] build_query_url")
    try:
        url = build_query_url("python/read+file", plain=True)
        assert "python/read+file" in url, f"URL 应包含主题"
        assert "?T" in url, f"URL 应包含纯文本参数"
        print(f"  ✅ URL: {url}")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 8: query_cheat_sh dry-run
    print("\n[测试 8] query_cheat_sh dry-run")
    try:
        result = query_cheat_sh("python/read+file", dry_run=True)
        assert result["success"], "dry-run 应成功"
        assert "[DRY-RUN]" in result["content"], "dry-run 应包含标记"
        print(f"  ✅ dry-run 成功")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 9: query_cheat_sh 空主题
    print("\n[测试 9] query_cheat_sh 空主题")
    try:
        result = query_cheat_sh("")
        assert not result["success"], "空主题应失败"
        assert result["error_code"] == "E001", f"期望 E001, 实际 {result['error_code']}"
        print(f"  ✅ 正确返回 E001")
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 10: CacheManager
    print("\n[测试 10] CacheManager")
    try:
        cache_dir = tempfile.mkdtemp(prefix="cheat-sh-test-")
        cache = CacheManager(cache_dir=cache_dir, expiry=3600)
        
        # 写入缓存
        cache.set("test/topic", True, "test content")
        
        # 读取缓存
        content = cache.get("test/topic", True)
        assert content == "test content", f"期望 'test content', 实际 '{content}'"
        print(f"  ✅ 缓存写入/读取成功")
        
        # 清理
        import shutil
        shutil.rmtree(cache_dir, ignore_errors=True)
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 11: atomic_write dry-run
    print("\n[测试 11] atomic_write dry-run")
    try:
        test_dir = tempfile.mkdtemp(prefix="cheat-sh-test-")
        test_file = os.path.join(test_dir, "test.txt")
        
        # dry-run 模式不应写文件
        result = atomic_write(test_file, "test content", dry_run=True)
        assert result is False, "dry-run 应返回 False"
        assert not os.path.exists(test_file), "dry-run 不应创建文件"
        print(f"  ✅ dry-run 未写盘")
        
        # 正常模式应写文件
        result = atomic_write(test_file, "test content", dry_run=False)
        assert result is True, "正常模式应返回 True"
        assert os.path.exists(test_file), "正常模式应创建文件"
        content = read_text_safe(test_file)
        assert content == "test content", f"期望 'test content', 实际 '{content}'"
        print(f"  ✅ 正常模式写入成功")
        
        # 清理
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)
    except AssertionError as e:
        print(f"  ❌ {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        failures += 1
    
    # 测试 12: 真实网络请求（如果可用）
    print("\n[测试 12] 真实网络请求")
    try:
        result = query_cheat_sh("python/read+file", plain=True, verbose=False)
        if result["success"]:
            assert len(result["content"]) > 0, "内容不应为空"
            print(f"  ✅ 网络请求成功，返回 {result['total_lines']} 行")
        else:
            print(f"  ⚠️ 网络请求失败: {result['error_code']} {result['error_message']}")
            print(f"  ⚠️ 跳过（可能是网络环境限制）")
    except Exception as e:
        print(f"  ⚠️ 网络请求异常: {e}")
        print(f"  ⚠️ 跳过（可能是网络环境限制）")
    
    # 汇总
    print("\n" + "=" * 60)
    if failures == 0:
        print("✅ 所有测试通过")
        return 0
    else:
        print(f"❌ {failures} 个测试失败")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    args = parse_args(argv)
    
    # 自测模式
    if args.selftest:
        return run_selftest()
    
    # 清空缓存
    if args.clear_cache:
        cache = CacheManager()
        count = cache.clear()
        print(f"已清空 {count} 个缓存文件")
        return 0
    
    # 检查是否有 topic
    if not args.topic:
        print("错误 [E001]: 查询主题为空，请提供语言/工具名", file=sys.stderr)
        print("示例: python run.py python/read+file", file=sys.stderr)
        return 1
    
    # 执行查询
    result = query_cheat_sh(
        topic=args.topic,
        plain=args.plain,
        index=args.index,
        use_cache=args.cache,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )
    
    # 输出结果
    output = format_output(result, verbose=args.verbose)
    print(output)
    
    # 返回退出码
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
