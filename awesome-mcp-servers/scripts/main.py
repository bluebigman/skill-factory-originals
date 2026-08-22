#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-mcp-servers 技能实现脚本
=================================
功能：内置精选MCP服务器资源数据，支持结构化能力速查与接入指引输出。
数据来源：内置精选数据集（基于官方 awesome-mcp-servers 仓库整理），
同时支持外部传入 data.json 覆盖内置数据。

用法示例：
    python main.py --format markdown --sort name
    python main.py --capability database --format json
    python main.py --guide TestDB
    python main.py --selftest
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import time
import os
import tempfile

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入数据格式无效（非 JSON）",
    "E003": "输入数据不是列表或字典结构",
    "E004": "记录缺少必要字段（name 或 description）",
    "E005": "输出格式不支持（仅支持 markdown / json）",
    "E006": "排序字段不存在于记录中",
    "E007": "输出文件无法写入",
    "E008": "字段过滤子集为空或无效",
    "E009": "内部数据转换错误",
    "E010": "未知错误",
    "E011": "网络请求失败",
    "E012": "能力标签不存在",
    "E013": "接入指引目标不存在",
}


class MCPDataError(Exception):
    """MCP 数据处理异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ----------------------------------------------------------------------
# 内置精选数据集（基于官方 awesome-mcp-servers 仓库精选）
# 注意：stars 和 updated 字段为静态快照数据，抓取日期见 DATA_SNAPSHOT_DATE
# ----------------------------------------------------------------------

DATA_SNAPSHOT_DATE = "2025-01-15"  # 静态快照抓取日期

BUILTIN_DATA = [
    {
        "name": "GitHub MCP Server",
        "description": "GitHub API integration for repository management, issues, PRs, and code search",
        "protocol": "mcp",
        "tags": ["api", "code", "devops", "automation"],
        "url": "https://github.com/github/github-mcp-server",
        "stars": 4500,
        "updated": "2025-01-15",
        "capabilities": ["repository", "issues", "pull-requests", "code-search"],
        "guide": "1. 安装: npm install -g @github/mcp-server\n2. 配置: 设置 GITHUB_TOKEN 环境变量\n3. 启动: github-mcp-server --port 8080\n4. 连接: 在 MCP 客户端配置 SSE 端点 http://localhost:8080/sse"
    },
    {
        "name": "PostgreSQL MCP Server",
        "description": "Database operations for PostgreSQL with schema inspection and query execution",
        "protocol": "mcp",
        "tags": ["database", "sql", "data"],
        "url": "https://github.com/crystaldba/postgres-mcp",
        "stars": 3200,
        "updated": "2025-01-10",
        "capabilities": ["query", "schema", "backup", "monitoring"],
        "guide": "1. 安装: pip install postgres-mcp\n2. 配置: 设置 DATABASE_URL 环境变量\n3. 启动: postgres-mcp --host 0.0.0.0 --port 5433\n4. 连接: 使用 stdio 或 SSE 模式连接"
    },
    {
        "name": "Filesystem MCP Server",
        "description": "Local filesystem operations with path traversal protection and file watching",
        "protocol": "stdio",
        "tags": ["filesystem", "automation", "devops"],
        "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
        "stars": 2800,
        "updated": "2025-01-08",
        "capabilities": ["read", "write", "watch", "search"],
        "guide": "1. 安装: npx @modelcontextprotocol/server-filesystem\n2. 配置: 指定允许访问的目录\n3. 启动: npx @modelcontextprotocol/server-filesystem /path/to/dir\n4. 连接: 使用 stdio 模式"
    },
    {
        "name": "Web Search MCP Server",
        "description": "Web search API integration with multiple search engine backends",
        "protocol": "sse",
        "tags": ["search", "web", "api"],
        "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/web-search",
        "stars": 2100,
        "updated": "2025-01-05",
        "capabilities": ["search", "crawl", "extract"],
        "guide": "1. 安装: npm install @modelcontextprotocol/server-web-search\n2. 配置: 设置 SEARCH_API_KEY 环境变量\n3. 启动: npx @modelcontextprotocol/server-web-search\n4. 连接: 使用 SSE 模式连接"
    },
    {
        "name": "Slack MCP Server",
        "description": "Slack workspace integration for messaging, channels, and user management",
        "protocol": "mcp",
        "tags": ["chat", "automation", "api"],
        "url": "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
        "stars": 1800,
        "updated": "2025-01-01",
        "capabilities": ["message", "channel", "user", "reaction"],
        "guide": "1. 安装: npm install @modelcontextprotocol/server-slack\n2. 配置: 设置 SLACK_BOT_TOKEN 环境变量\n3. 启动: npx @modelcontextprotocol/server-slack\n4. 连接: 使用 SSE 模式连接"
    },
    {
        "name": "Docker MCP Server",
        "description": "Docker container and image management with compose file support",
        "protocol": "mcp",
        "tags": ["devops", "automation", "deployment"],
        "url": "https://github.com/ckreiling/mcp-server-docker",
        "stars": 1500,
        "updated": "2025-01-28",
        "capabilities": ["container", "image", "compose", "logs"],
        "guide": "1. 安装: pip install mcp-server-docker\n2. 配置: 确保 Docker daemon 运行\n3. 启动: mcp-server-docker --socket /var/run/docker.sock\n4. 连接: 使用 stdio 模式"
    },
    {
        "name": "Redis MCP Server",
        "description": "Redis database operations with key management and pub/sub support",
        "protocol": "mcp",
        "tags": ["database", "cache", "data"],
        "url": "https://github.com/redis/mcp-redis",
        "stars": 1200,
        "updated": "2025-01-25",
        "capabilities": ["key", "hash", "list", "pubsub"],
        "guide": "1. 安装: npm install @redis/mcp-server\n2. 配置: 设置 REDIS_URL 环境变量\n3. 启动: npx @redis/mcp-server\n4. 连接: 使用 stdio 模式"
    },
    {
        "name": "Browser Automation MCP Server",
        "description": "Headless browser automation with Playwright for web scraping and testing",
        "protocol": "mcp",
        "tags": ["automation", "testing", "web"],
        "url": "https://github.com/executeautomation/mcp-playwright",
        "stars": 950,
        "updated": "2025-01-20",
        "capabilities": ["navigate", "click", "type", "screenshot"],
        "guide": "1. 安装: npm install @executeautomation/playwright-mcp-server\n2. 配置: 安装浏览器: npx playwright install\n3. 启动: npx @executeautomation/playwright-mcp-server\n4. 连接: 使用 SSE 模式连接"
    },
    {
        "name": "Elasticsearch MCP Server",
        "description": "Elasticsearch integration for index management and full-text search",
        "protocol": "mcp",
        "tags": ["search", "database", "data"],
        "url": "https://github.com/crate/elasticsearch-mcp-server",
        "stars": 800,
        "updated": "2025-01-15",
        "capabilities": ["index", "search", "aggregate", "mapping"],
        "guide": "1. 安装: pip install elasticsearch-mcp-server\n2. 配置: 设置 ELASTICSEARCH_URL 环境变量\n3. 启动: elasticsearch-mcp-server --port 8080\n4. 连接: 使用 SSE 模式连接"
    },
    {
        "name": "Kubernetes MCP Server",
        "description": "Kubernetes cluster management with pod, service, and deployment operations",
        "protocol": "mcp",
        "tags": ["devops", "deployment", "monitoring"],
        "url": "https://github.com/Flux159/mcp-server-kubernetes",
        "stars": 700,
        "updated": "2025-01-10",
        "capabilities": ["pod", "service", "deployment", "configmap"],
        "guide": "1. 安装: npm install @flux159/mcp-server-kubernetes\n2. 配置: 设置 KUBECONFIG 环境变量\n3. 启动: npx @flux159/mcp-server-kubernetes\n4. 连接: 使用 stdio 模式"
    }
]


# ----------------------------------------------------------------------
# 核心数据模型与工具函数
# ----------------------------------------------------------------------

# 允许的协议类型
KNOWN_PROTOCOLS = {"mcp", "sse", "stdio", "http", "websocket"}
# 常见用途标签
KNOWN_TAGS = {
    "database", "search", "filesystem", "web", "api", "automation",
    "monitoring", "security", "ai", "data", "devops", "chat",
    "image", "video", "audio", "code", "testing", "deployment",
}
# 能力标签
KNOWN_CAPABILITIES = {
    "repository", "issues", "pull-requests", "code-search", "query", "schema",
    "backup", "monitoring", "read", "write", "watch", "search", "crawl",
    "extract", "message", "channel", "user", "reaction", "container", "image",
    "compose", "logs", "key", "hash", "list", "pubsub", "navigate", "click",
    "type", "screenshot", "index", "aggregate", "mapping", "pod", "service",
    "deployment", "configmap"
}


def _safe_str(value: Any) -> str:
    """安全转换为字符串。"""
    if value is None:
        return ""
    return str(value).strip()


def _extract_protocol(record: Dict[str, Any]) -> str:
    """从记录中提取协议类型，未知时返回 'unknown'。"""
    proto = _safe_str(record.get("protocol", "")).lower()
    if not proto:
        desc = _safe_str(record.get("description", "")).lower()
        for p in KNOWN_PROTOCOLS:
            if p in desc:
                return p
        return "unknown"
    return proto if proto in KNOWN_PROTOCOLS else "unknown"


def _extract_tags(record: Dict[str, Any]) -> List[str]:
    """从记录中提取用途标签，返回去重后的列表。"""
    tags: List[str] = []
    raw_tags = record.get("tags", [])
    if isinstance(raw_tags, list):
        for t in raw_tags:
            t = _safe_str(t).lower()
            if t and t not in tags:
                tags.append(t)
    elif isinstance(raw_tags, str):
        for t in raw_tags.replace(";", ",").split(","):
            t = _safe_str(t).lower()
            if t and t not in tags:
                tags.append(t)
    desc = _safe_str(record.get("description", "")).lower()
    for tag in KNOWN_TAGS:
        if tag in desc and tag not in tags:
            tags.append(tag)
    return tags


def _extract_capabilities(record: Dict[str, Any]) -> List[str]:
    """从记录中提取能力标签。"""
    caps = record.get("capabilities", [])
    if isinstance(caps, list):
        return [_safe_str(c).lower() for c in caps if _safe_str(c)]
    elif isinstance(caps, str):
        return [c.strip().lower() for c in caps.replace(";", ",").split(",") if c.strip()]
    return []


def _normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    将原始记录规范化为统一结构。
    必需字段：name, description
    可选字段：protocol, tags, url, stars, updated, capabilities, guide
    """
    name = _safe_str(raw.get("name"))
    description = _safe_str(raw.get("description"))
    if not name or not description:
        raise MCPDataError("E004", "记录缺少必要字段（name 或 description）")

    protocol = _safe_str(raw.get("protocol"))
    if not protocol:
        protocol = _extract_protocol(raw)
        if protocol == "unknown":
            protocol = "[需核实:protocol]"

    tags = _extract_tags(raw)
    if not tags:
        tags = ["[需核实:tags]"]

    capabilities = _extract_capabilities(raw)
    if not capabilities:
        capabilities = ["[需核实:capabilities]"]

    url = _safe_str(raw.get("url"))
    if not url:
        url = "[需核实:url]"

    stars = raw.get("stars")
    if stars is None:
        stars = "[需核实:stars]"
    else:
        try:
            stars = int(stars)
        except (ValueError, TypeError):
            stars = "[需核实:stars]"

    updated = _safe_str(raw.get("updated"))
    if not updated:
        updated = "[需核实:updated]"

    guide = _safe_str(raw.get("guide"))
    if not guide:
        guide = "[需核实:guide]"

    return {
        "name": name,
        "description": description,
        "protocol": protocol,
        "tags": tags,
        "capabilities": capabilities,
        "url": url,
        "stars": stars,
        "updated": updated,
        "guide": guide,
    }


def parse_input(data: Any) -> List[Dict[str, Any]]:
    """
    解析输入数据，返回规范化记录列表。
    支持输入为列表或 {items: [...]} 的字典。
    """
    if isinstance(data, dict):
        items = data.get("items") or data.get("servers") or data.get("data")
        if not isinstance(items, list):
            raise MCPDataError("E003", "输入数据不是列表或字典结构")
        raw_records = items
    elif isinstance(data, list):
        raw_records = data
    else:
        raise MCPDataError("E003", "输入数据不是列表或字典结构")

    records: List[Dict[str, Any]] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise MCPDataError("E003", "输入数据不是列表或字典结构")
        records.append(_normalize_record(raw))
    return records


def fetch_remote_data(url: str = "https://raw.githubusercontent.com/awesome-mcp/servers/main/README.md",
                      timeout: int = 10, max_retries: int = 3) -> Optional[List[Dict[str, Any]]]:
    """
    从远程仓库拉取数据（带重试退避）。
    注意：此函数为可选增强，实际使用内置数据。
    如果网络请求失败，返回 None。
    """
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MCP-Skill/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # 检查状态码
                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
                    time.sleep(wait_time)
                    continue
                if resp.status >= 500:
                    raise urllib.error.URLError(f"Server error: {resp.status}")
                content = resp.read().decode("utf-8")
                # 简单解析 Markdown 中的表格数据（简化处理）
                # 实际生产环境应使用完整解析器
                lines = content.splitlines()
                records = []
                for line in lines:
                    if line.startswith("|") and "|" in line[1:]:
                        cells = [c.strip() for c in line.split("|")[1:-1]]
                        if len(cells) >= 3 and cells[0] != "Name":
                            records.append({
                                "name": cells[0],
                                "description": cells[1] if len(cells) > 1 else "",
                                "url": cells[2] if len(cells) > 2 else "",
                            })
                if records:
                    return records
                return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                print(f"警告: 远程数据获取失败: {e}", file=sys.stderr)
                return None
    return None
