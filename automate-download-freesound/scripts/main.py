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


class DownloadListGenerator:
    """生成规范化下载清单"""

    def __init__(self, config: TaskConfig):
        self.config = config

    def generate_from_urls(self, urls: List[str]) -> List[DownloadItem]:
        """从 URL 列表生成下载条目"""
        items = []
        for url in urls:
            try:
                info = FreesoundRequestParser.parse_url(url)
                item = DownloadItem(
                    source_url=info["source_url"],
                    file_name=self._make_file_name(info),
                    category=self._guess_category(url),
                    tags=self._extract_tags(info),
                    description=f"从 Freesound 采集的声音资源 (ID: {info['sound_id'] or 'unknown'})",
                    license_type="cc0",  # 默认假设为 CC0，实际应以页面信息为准
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
        """从关键词集合生成下载条目（生成搜索建议）"""
        cleaned = FreesoundRequestParser.parse_keywords(keywords)

        items = []
        for kw in cleaned:
            # 为每个关键词生成一个搜索条目
            search_url = self._build_search_url(kw)
            item = DownloadItem(
                source_url=search_url,
                file_name=f"search_{kw.replace(' ', '_')}",
                category="search",
                tags=[kw],
                description=f"Freesound 搜索: {kw}",
                license_type="unknown",
                download_priority=3,  # 搜索条目优先级较高
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
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(items: List[DownloadItem]) -> str:
        """生成 CSV 格式报告"""
        if not items:
            return "source_url,file_name,category,tags,description,license_type,local_path\n"

        output = io.StringIO()
        fieldnames = [
            "source_url",
            "file_name",
            "category",
            "tags",
            "description",
            "license_type",
            "size_bytes",
            "duration_seconds",
            "download_priority",
            "download_url",
            "local_path",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            row = asdict(item)
            row["tags"] = ";".join(item.tags)
            writer.writerow(row)
        return output.getvalue()

    @staticmethod
    def to_markdown(items: List[DownloadItem]) -> str:
        """生成 Markdown 格式报告"""
        if not items:
            return "# 下载清单\n\n（空）\n"

        lines = ["# 声音素材下载清单", ""]
        lines.append(f"共 {len(items)} 个条目")
        lines.append("")
        lines.append("| # | 文件名 | 来源 URL | 分类 | 标签 | 本地路径 |")
        lines.append("|---|--------|----------|------|------|----------|")

        for idx, item in enumerate(items, 1):
            tags_str = ", ".join(item.tags[:3]) if item.tags else "-"
            local_path = item.local_path or "-"
            lines.append(
                f"| {idx} | {item.file_name} | {item.source_url} | "
                f"{item.category} | {tags_str} | {local_path} |"
            )

        lines.extend(["", "## 操作指引", ""])
        lines.append("1. 使用浏览器打开上述 URL 验证资源可用性。")
        lines.append("2. 下载后请检查许可证类型，遵守使用规范。")
        lines.append("3. 本清单由自动化工具生成，仅供学习研究使用。")

        return "\n".join(lines)


class BatchProcessor:
    """批量任务处理器"""

    def __init__(self, config: TaskConfig):
        self.config = config
        self.generator = DownloadListGenerator(config)
        self.downloader = Downloader(config)

    def process_input(
        self,
        urls: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
    ) -> List[DownloadItem]:
        """处理输入，生成合并的下载条目列表"""
        url_items = []
        kw_items = []

        if urls:
            url_items = self.generator.generate_from_urls(urls)

        if keywords:
            kw_items = self.generator.generate_from_keywords(keywords)

        if not url_items and not kw_items:
            raise SkillError("E002", "未提供有效的 URL 或关键词")

        return self.generator.merge_items(url_items, kw_items)

    def download_items(self, items: List[DownloadItem]) -> List[DownloadItem]:
        """执行实际下载"""
        if not self.config.download:
            return items

        print(f"\n开始下载 {len(items)} 个文件...")
        downloaded = self.downloader.download_batch(items)
        print(f"下载完成: {len(downloaded)}/{len(items)} 成功")
        return downloaded

    def write_report(self, items: List[DownloadItem]) -> str:
        """生成报告并写入文件，返回文件路径"""
        fmt = self.config.output_format.lower()
        if fmt not in ("json", "csv", "markdown"):
            raise SkillError("E005", f"不支持的输出格式: {fmt}")

        # 生成报告内容
        if fmt == "json":
            content = ReportGenerator.to_json(items, self.config.include_metadata)
            ext = "json"
        elif fmt == "csv":
            content = ReportGenerator.to_csv(items)
            ext = "csv"
        else:
            content = ReportGenerator.to_markdown(items)
            ext = "md"

        # 写入文件（原子操作）
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
            file_name = f"download_manifest_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = os.path.join(self.config.output_dir, file_name)

            # 先写临时文件，再原子替换
            fd, temp_path = tempfile.mkstemp(
                dir=self.config.output_dir,
                prefix=f".{file_name}_",
                suffix=".tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content)
                os.replace(temp_path, file_path)
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

            return file_path
        except OSError as e:
            raise SkillError("E006", f"文件写入失败: {e}")

    def print_summary(self, items: List[DownloadItem]) -> None:
        """打印任务摘要"""
        print("\n===== 任务摘要 =====")
        print(f"生成条目数: {len(items)}")
