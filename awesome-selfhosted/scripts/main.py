#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
自托管服务资源导航信息整理工具（awesome-selfhosted）
仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.request
import urllib.error
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义（E001-E013）
ERROR_CODES = {
    "E001": "输入为空或格式无效",
    "E002": "输入数据超过支持条数（1-20条）",
    "E003": "输入数据超过最大批量限制（100条）",
    "E004": "无法识别的输入格式（仅支持文本/JSON/CSV）",
    "E005": "字段提取失败：缺少服务名称",
    "E006": "字段提取失败：缺少官方链接",
    "E007": "输出格式不支持（仅支持 markdown/json/csv）",
    "E008": "URL格式校验失败",
    "E009": "内部逻辑错误：未知分组方式",
    "E010": "参数错误或命令行使用不当",
    "E011": "网络请求失败",
    "E012": "远程数据获取超时",
    "E013": "远程数据格式无效",
}

# 支持的部署方式关键词（用于信息提取）
DEPLOY_KEYWORDS = {
    "docker": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "bare": "裸机",
    "baremetal": "裸机",
    "裸机": "裸机",
    "容器": "Docker",
    "虚拟机": "虚拟机",
    "vm": "虚拟机",
}

# 常见功能标签关键词（用于信息提取）
FEATURE_KEYWORDS = [
    "笔记", "wiki", "博客", "网盘", "文件", "同步",
    "密码", "密码管理", "监控", "分析", "数据库",
    "git", "代码", "代码托管", "邮件", "聊天",
    "crm", "项目管理", "任务", "任务管理",
    "书签", "rss", "阅读", "相册", "音乐",
    "视频", "地图", "日历", "联系人",
    "表单", "api", "api网关", "代理",
]

# 远程数据源配置（用于在线筛选）
REMOTE_SOURCES = {
    "awesome-selfhosted": {
        "url": "https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md",
        "type": "markdown",
        "timeout": 10,
        "max_retries": 3,
        "backoff_factor": 2.0,
    }
}

# 本地缓存（基于URL哈希）
_cache: Dict[str, Tuple[str, float]] = {}


class SelfHostedRecord:
    """单条自托管服务记录的数据结构"""

    def __init__(self, name: str, url: str, description: str = "",
                 deploy: str = "", tags: List[str] = None):
        self.name = name.strip()
        self.url = url.strip()
        self.description = description.strip()
        self.deploy = deploy.strip()
        self.tags = tags if tags else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "deploy": self.deploy,
            "tags": self.tags,
        }


class NetworkClient:
    """网络请求客户端，支持重试退避、超时和本地缓存"""

    @staticmethod
    def _get_cache_key(url: str) -> str:
        """生成URL的缓存键（哈希）"""
        return hashlib.sha256(url.encode()).hexdigest()

    @staticmethod
    def _get_cached(url: str) -> Optional[str]:
        """从缓存获取内容（5分钟有效期）"""
        cache_key = NetworkClient._get_cache_key(url)
        if cache_key in _cache:
            content, timestamp = _cache[cache_key]
            # 5分钟缓存有效期
            if datetime.now(timezone.utc).timestamp() - timestamp < 300:
                return content
            else:
                del _cache[cache_key]
        return None

    @staticmethod
    def _set_cached(url: str, content: str) -> None:
        """写入缓存"""
        cache_key = NetworkClient._get_cache_key(url)
        _cache[cache_key] = (content, datetime.now(timezone.utc).timestamp())

    @staticmethod
    def fetch_url(url: str, timeout: int = 10, max_retries: int = 3,
                  backoff_factor: float = 2.0) -> str:
        """获取URL内容，带重试退避机制和本地缓存"""
        # 先检查缓存
        cached = NetworkClient._get_cached(url)
        if cached is not None:
            return cached

        last_error = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "awesome-selfhosted-tool/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    if response.status != 200:
                        raise urllib.error.HTTPError(url, response.status, "HTTP Error", response.headers, None)
                    content = response.read().decode("utf-8", errors="replace")
                    # 写入缓存
                    NetworkClient._set_cached(url, content)
                    return content
            except (urllib.error.URLError, socket.timeout, OSError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor ** attempt)
                continue
        # 所有重试失败后，尝试返回缓存数据（即使过期）
        cached = NetworkClient._get_cached(url)
        if cached is not None:
            return cached
        raise ValueError(f"E011: 网络请求失败: {last_error}")

    @staticmethod
    def fetch_remote_data(source_name: str = "awesome-selfhosted") -> str:
        """从远程数据源获取数据"""
        if source_name not in REMOTE_SOURCES:
            raise ValueError(f"E010: 未知数据源: {source_name}")

        source = REMOTE_SOURCES[source_name]
        try:
            content = NetworkClient.fetch_url(
                source["url"],
                timeout=source["timeout"],
                max_retries=source["max_retries"],
                backoff_factor=source["backoff_factor"],
            )
            return content
        except ValueError as e:
            raise ValueError(f"E012: 远程数据获取失败: {e}")


class SelfHostedParser:
    """输入解析器：从文本/JSON/CSV中提取服务记录"""

    @staticmethod
    def parse_text(content: str) -> List[SelfHostedRecord]:
        """从纯文本中解析记录（支持行格式或简单列表）"""
        records = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        for line in lines:
            # 跳过可能的标题行或分隔线
            if line.startswith("#") or line.startswith("-") or line.startswith("="):
                continue

            # 尝试多种分隔符拆分名称和URL
            record = SelfHostedParser._parse_line(line)
            if record:
                records.append(record)

        return records

    @staticmethod
    def _parse_line(line: str) -> Optional[SelfHostedRecord]:
        """解析单行文本为记录"""
        # 支持格式: 名称 | URL | 描述 | 部署方式
        parts = re.split(r"\s*[|,;]\s*", line)
        if len(parts) >= 2:
            name, url = parts[0], parts[1]
            description = parts[2] if len(parts) > 2 else ""
            deploy = parts[3] if len(parts) > 3 else ""
        else:
            # 尝试匹配 "名称 (URL)" 或 "名称 URL" 格式
            match = re.match(r"(.+?)\s*[\(\[（【]\s*(https?://[^\s\)\]]+)\s*[\)\]）】]", line)
            if match:
                name, url = match.group(1), match.group(2)
                description, deploy = "", ""
            else:
                # 尝试 "名称 - URL" 格式
                match = re.match(r"(.+?)\s*[-–—]\s*(https?://\S+)", line)
                if match:
                    name, url = match.group(1), match.group(2)
                    description, deploy = "", ""
                else:
                    return None

        # 校验URL格式
        if not SelfHostedParser._is_valid_url(url):
            return None

        return SelfHostedRecord(name=name, url=url, description=description, deploy=deploy)

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """简单URL格式校验"""
        return bool(re.match(r"^https?://", url)) and len(url) > 10

    @staticmethod
    def parse_json(content: str) -> List[SelfHostedRecord]:
        """从JSON中解析记录"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("E004")

        records = []
        # 支持直接数组或{"records": [...]}格式
        if isinstance(data, dict) and "records" in data:
            data = data["records"]

        if not isinstance(data, list):
            raise ValueError("E004")

        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("title") or item.get("服务名称")
            url = item.get("url") or item.get("link") or item.get("官方链接")
            if not name or not url:
                raise ValueError("E005" if not name else "E006")
            record = SelfHostedRecord(
                name=str(name),
                url=str(url),
                description=str(item.get("description") or item.get("描述") or ""),
                deploy=str(item.get("deploy") or item.get("部署方式") or ""),
                tags=item.get("tags") or item.get("功能标签") or [],
            )
            records.append(record)

        return records

    @staticmethod
    def parse_csv(content: str) -> List[SelfHostedRecord]:
        """从CSV中解析记录"""
        records = []
        try:
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                name = row.get("name") or row.get("服务名称") or row.get("名称")
                url = row.get("url") or row.get("官方链接") or row.get("链接")
                if not name or not url:
                    raise ValueError("E005" if not name else "E006")
                record = SelfHostedRecord(
                    name=name.strip(),
                    url=url.strip(),
                    description=(row.get("description") or row.get("描述") or "").strip(),
                    deploy=(row.get("deploy") or row.get("部署方式") or "").strip(),
                    tags=[t.strip() for t in (row.get("tags") or row.get("功能标签") or "").split(";") if t.strip()],
                )
                records.append(record)
        except csv.Error:
            raise ValueError("E004")

        return records

    @staticmethod
    def parse(content: str, input_format: str = "auto") -> List[SelfHostedRecord]:
        """统一解析入口"""
        if not content or not content.strip():
            raise ValueError("E001")

        # 自动检测格式
        if input_format == "auto":
            stripped = content.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                input_format = "json"
            elif "," in stripped.splitlines()[0] and ("name" in stripped.splitlines()[0] or "服务名称" in stripped.splitlines()[0]):
                input_format = "csv"
            else:
                input_format = "text"

        if input_format == "json":
            records = SelfHostedParser.parse_json(content)
        elif input_format == "csv":
            records = SelfHostedParser.parse_csv(content)
        elif input_format == "text":
            records = SelfHostedParser.parse_text(content)
        else:
            raise ValueError("E004")

        # 条数校验
        if not records:
            raise ValueError("E001")
        if len(records) > 100:
            raise ValueError("E003")
        if len(records) > 20:
            # 超出20条时提示分批（但不失败，仅记录提示）
            print("提示: 输入超过20条，建议分批处理以获得最佳效果。", file=sys.stderr)

        return records


class InfoExtractor:
    """信息提取器：从描述中提取部署方式和功能标签"""

    @staticmethod
    def extract_deploy(record: SelfHostedRecord) -> str:
        """从描述或已有部署字段中提取部署方式"""
        if record.deploy:
            # 校验已有部署方式
            for key, value in DEPLOY_KEYWORDS.items():
                if key.lower() in record.deploy.lower():
                    return value
            return record.deploy

        # 从描述中提取
        text = f"{record.name} {record.description}".lower()
        for key, value in DEPLOY_KEYWORDS.items():
            if key in text:
                return value
        return "未知"

    @staticmethod
    def extract_tags(record: SelfHostedRecord) -> List[str]:
        """从名称和描述中提取功能标签"""
        if record.tags:
            return list(record.tags)

        text = f"{record.name} {record.description}".lower()
        found_tags = []
        for keyword in FEATURE_KEYWORDS:
            if keyword.lower() in text:
                canonical = keyword
                if canonical not in found_tags:
                    found_tags.append(canonical)

        # 限制最多5个标签
        return found_tags[:5]


class OutputFormatter:
    """输出格式化器：生成Markdown/JSON/CSV格式"""

    @staticmethod
    def format_markdown(records: List[SelfHostedRecord], group_by: str = "none") -> str:
        """生成Markdown表格输出"""
        lines = ["# 自托管服务资源清单", ""]

        if group_by == "deploy":
            # 按部署方式分组
            groups: Dict[str, List[SelfHostedRecord]] = {}
            for record in records:
                deploy = InfoExtractor.extract_deploy(record)
                groups.setdefault(deploy, []).append(record)

            for deploy, group_records in groups.items():
                lines.append(f"## {deploy}")
                lines.append("")
                lines.extend(OutputFormatter._markdown_table(group_records))
                lines.append("")
        elif group_by == "tag":
            # 按第一个标签分组
            groups: Dict[str, List[SelfHostedRecord]] = {}
            for record in records:
                tags = InfoExtractor.extract_tags(record)
                tag = tags[0] if tags else "未分类"
                groups.setdefault(tag, []).append(record)

            for tag, group_records in groups.items():
                lines.append(f"## {tag}")
                lines.append("")
                lines.extend(OutputFormatter._markdown_table(group_records))
                lines.append("")
        else:
            lines.extend(OutputFormatter._markdown_table(records))

        return "\n".join(lines)

    @staticmethod
    def _markdown_table(records: List[SelfHostedRecord]) -> List[str]:
        """生成Markdown表格内容"""
        lines = ["| 服务名称 | 官方链接 | 功能描述 | 部署方式 | 功能标签 |",
                 "|---------|---------|---------|---------|---------|"]
        for record in records:
            deploy = InfoExtractor.extract_deploy(record)
            tags = ", ".join(InfoExtractor.extract_tags(record)) or "—"
            desc = record.description[:50] + "..." if len(record.description) > 50 else record.description
            lines.append(f"| {record.name} | [{record.url}]({record.url}) | {desc} | {deploy} | {tags} |")
        return lines

    @staticmethod
    def format_json(records: List[SelfHostedRecord]) -> str:
        """生成JSON输出"""
        data = {
            "count": len(records),
            "records": [record.to_dict() for record in records],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def format_csv(records: List[SelfHostedRecord]) -> str:
        """生成CSV输出"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["name", "url", "description", "deploy", "tags"])
        for record in records:
            writer.writerow([
                record.name,
                record.url,
                record.description,
                InfoExtractor.extract_deploy(record),
                ";".join(InfoExtractor.extract_tags(record)),
            ])
        return output.getvalue().strip()

    @staticmethod
    def format(records: List[SelfHostedRecord], output_format: str = "markdown",
               group_by: str = "none") -> str:
        """统一格式化入口"""
        if output_format == "markdown":
            return OutputFormatter.format_markdown(records, group_by)
        elif output_format == "json":
            return OutputFormatter.format_json(records)
        elif output_format == "csv":
            return OutputFormatter.format_csv(records)
        else:
            raise ValueError("E007")


class SelfHostedProcessor:
    """核心处理器：编排解析、提取、格式化流程"""

    def __init__(self):
        self.parser = SelfHostedParser()
        self.extractor = InfoExtractor()
        self.formatter = OutputFormatter()
        self.network = NetworkClient()

    def filter_by_keywords(self, records: List[SelfHostedRecord], keywords: List[str]) -> List[SelfHostedRecord]:
        """根据关键词对记录进行匹配和评分筛选"""
        if not keywords:
            return records

        scored_records = []
        for record in records:
            score = 0
            # 构建搜索文本
            search_text
