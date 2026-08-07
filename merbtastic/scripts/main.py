#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merbtastic - 站点构建与路由配置助手

本脚本基于功能规格独立实现（clean-room），提供：
1. 内容源解析（C1）
2. 动态路由设计（C2）
3. Nginx 配置生成（C3）
4. 静态站点生成（C4）
5. 批量处理与格式转换（C5）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：输入文件不存在或无法访问",
    "E003": "文件写入失败：输出目录不可写或路径无效",
    "E004": "内容解析失败：输入内容格式不支持或数据损坏",
    "E005": "路由生成失败：路由规则与内容类型不匹配",
    "E006": "Nginx 配置生成失败：配置参数不完整",
    "E007": "静态站点生成失败：模板处理或文件生成出错",
    "E008": "批量处理失败：批量转换过程中出现异常",
    "E009": "自检失败：核心逻辑验证未通过",
    "E010": "未知错误：未预期的异常情况",
}


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出程序"""
    err_msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if message:
        print(f"错误 {code}: {err_msg} - {message}", file=sys.stderr)
    else:
        print(f"错误 {code}: {err_msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ContentItem:
    """内容条目"""
    title: str = ""
    slug: str = ""
    content_type: str = "page"
    year: str = ""
    month: str = ""
    tags: List[str] = field(default_factory=list)
    body: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteRule:
    """动态路由规则"""
    pattern: str = ""
    content_type: str = ""
    template: str = ""


@dataclass
class SiteConfig:
    """站点配置"""
    title: str = "My Merb Site"
    base_url: str = "http://localhost:4000"
    output_dir: str = "./public"
    routes: List[RouteRule] = field(default_factory=list)


# ============================================================
# 内容源解析（C1）
# ============================================================
class ContentParser:
    """内容源解析器：从文件或数据中提取页面结构"""

    @staticmethod
    def parse_json(data: str) -> List[ContentItem]:
        """解析 JSON 格式的内容源"""
        try:
            raw_items = json.loads(data)
            if not isinstance(raw_items, list):
                raw_items = [raw_items]
            items = []
            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                item = ContentItem(
                    title=str(raw.get("title", "")),
                    slug=str(raw.get("slug", "")),
                    content_type=str(raw.get("type", "page")),
                    year=str(raw.get("year", "")),
                    month=str(raw.get("month", "")),
                    tags=[str(t) for t in raw.get("tags", [])],
                    body=str(raw.get("body", "")),
                    metadata=raw.get("metadata", {})
                )
                if not item.slug and item.title:
                    item.slug = ContentParser._slugify(item.title)
                items.append(item)
            return items
        except (json.JSONDecodeError, AttributeError) as e:
            error_exit("E004", f"JSON 解析失败: {e}")

    @staticmethod
    def parse_csv(data: str) -> List[ContentItem]:
        """解析 CSV 格式的内容源"""
        try:
            reader = csv.DictReader(data.splitlines())
            items = []
            for row in reader:
                item = ContentItem(
                    title=row.get("title", ""),
                    slug=row.get("slug", ""),
                    content_type=row.get("type", "page"),
                    year=row.get("year", ""),
                    month=row.get("month", ""),
                    tags=[t.strip() for t in row.get("tags", "").split(",") if t.strip()],
                    body=row.get("body", "")
                )
                if not item.slug and item.title:
                    item.slug = ContentParser._slugify(item.title)
                items.append(item)
            return items
        except Exception as e:
            error_exit("E004", f"CSV 解析失败: {e}")

    @staticmethod
    def parse_yaml(data: str) -> List[ContentItem]:
        """解析简单 YAML 风格的内容（无第三方库的简化实现）"""
        try:
            items = []
            current_item = None
            in_body = False
            body_lines = []
            item_started = False

            for line in data.splitlines():
                stripped = line.strip()
                
                # 检查是否是新条目的开始
                if stripped == "---":
                    # 如果已经在处理一个条目，先保存它
                    if current_item is not None and item_started:
                        if in_body:
                            current_item.body = "\n".join(body_lines).strip()
                        if not current_item.slug and current_item.title:
                            current_item.slug = ContentParser._slugify(current_item.title)
                        if current_item.title or current_item.slug:  # 只保存有内容的条目
                            items.append(current_item)
                    
                    # 开始新条目
                    current_item = ContentItem()
                    in_body = False
                    body_lines = []
                    item_started = True
                    continue
                
                # 如果还没开始任何条目，跳过
                if current_item is None:
                    continue
                
                # 处理 body 内容
                if in_body:
                    # 检查是否遇到新的字段（非 body 内容）
                    if stripped and not line.startswith(" ") and ":" in stripped:
                        current_item.body = "\n".join(body_lines).strip()
                        in_body = False
                        body_lines = []
                        # 继续处理当前行作为新字段
                    else:
                        body_lines.append(line)
                        continue
                
                # 解析字段
                if stripped.startswith("title:"):
                    current_item.title = stripped[6:].strip().strip('"\'')
                elif stripped.startswith("slug:"):
                    current_item.slug = stripped[5:].strip().strip('"\'')
                elif stripped.startswith("type:"):
                    current_item.content_type = stripped[5:].strip().strip('"\'')
                elif stripped.startswith("year:"):
                    current_item.year = stripped[5:].strip().strip('"\'')
                elif stripped.startswith("month:"):
                    current_item.month = stripped[6:].strip().strip('"\'')
                elif stripped.startswith("tags:"):
                    tag_str = stripped[5:].strip()
                    if tag_str.startswith("["):
                        tag_str = tag_str.strip("[]")
                        current_item.tags = [t.strip().strip('"\'') for t in tag_str.split(",") if t.strip()]
                    else:
                        current_item.tags = [tag_str]
                elif stripped.startswith("body:"):
                    in_body = True
                    body_lines = []

            # 处理最后一个条目
            if current_item is not None and item_started:
                if in_body:
                    current_item.body = "\n".join(body_lines).strip()
                if not current_item.slug and current_item.title:
                    current_item.slug = ContentParser._slugify(current_item.title)
                if current_item.title or current_item.slug:  # 只保存有内容的条目
                    items.append(current_item)

            return items
        except Exception as e:
            error_exit("E004", f"YAML 解析失败: {e}")

    @staticmethod
    def _slugify(text: str) -> str:
        """将标题转换为 URL slug"""
        # 只保留字母、数字、空格和连字符
        cleaned = re.sub(r'[^\w\s-]', '', text.lower())
        # 空格转连字符
        cleaned = re.sub(r'[\s_]+', '-', cleaned)
        # 去除多余连字符
        cleaned = re.sub(r'-+', '-', cleaned).strip('-')
        return cleaned

    @staticmethod
    def parse_file(file_path: str) -> List[ContentItem]:
        """根据文件扩展名自动选择解析方式"""
        try:
            path = Path(file_path)
            if not path.exists():
                error_exit("E002", f"文件不存在: {file_path}")
            content = path.read_text(encoding="utf-8")
            suffix = path.suffix.lower()
            if suffix == ".json":
                return ContentParser.parse_json(content)
            elif suffix == ".csv":
                return ContentParser.parse_csv(content)
            elif suffix in (".yaml", ".yml"):
                return ContentParser.parse_yaml(content)
            else:
                error_exit("E004", f"不支持的文件格式: {suffix}")
        except OSError as e:
            error_exit("E002", str(e))


# ============================================================
# 动态路由设计（C2）
# ============================================================
class RouteGenerator:
    """动态路由生成器"""

    def __init__(self, base_url: str = "http://localhost:4000"):
        self.base_url = base_url.rstrip("/")

    def generate_routes(self, items: List[ContentItem]) -> List[RouteRule]:
        """根据内容条目生成动态路由规则"""
        routes = []
        for item in items:
            # 根据内容类型生成不同的路由模式
            if item.content_type == "blog" or item.content_type == "post":
                if item.year and item.slug:
                    pattern = f"/blog/{item.year}/{item.slug}"
                elif item.slug:
                    pattern = f"/blog/{item.slug}"
                else:
                    pattern = f"/blog/{ContentParser._slugify(item.title)}"
                routes.append(RouteRule(
                    pattern=pattern,
                    content_type=item.content_type,
                    template="blog_post.html"
                ))
            elif item.content_type == "page":
                pattern = f"/{item.slug}" if item.slug else f"/{ContentParser._slugify(item.title)}"
                routes.append(RouteRule(
                    pattern=pattern,
                    content_type="page",
                    template="page.html"
                ))
            elif item.content_type == "tag":
                for tag in item.tags:
                    pattern = f"/tag/{ContentParser._slugify(tag)}"
                    routes.append(RouteRule(
                        pattern=pattern,
                        content_type="tag",
                        template="tag_listing.html"
                    ))
            else:
                # 默认路由
                pattern = f"/{item.slug}" if item.slug else f"/{ContentParser._slugify(item.title)}"
                routes.append(RouteRule(
                    pattern=pattern,
                    content_type=item.content_type,
                    template="default.html"
                ))
        return routes

    def generate_route_map(self, routes: List[RouteRule]) -> Dict[str, str]:
        """生成路由到模板的映射表"""
        route_map = {}
        for route in routes:
            full_url = f"{self.base_url}{route.pattern}"
            route_map[full_url] = route.template
        return route_map


# ============================================================
# Nginx 配置生成（C3）
# ============================================================
class NginxConfigGenerator:
    """Nginx 配置生成器"""

    @staticmethod
    def generate_server_block(server_name: str, root_dir: str, 
                              ssl_enabled: bool = False,
                              cache_enabled: bool = True) -> str:
        """生成 Nginx server 配置块"""
        if not server_name or not root_dir:
            error_exit("E006", "server_name 和 root_dir 不能为空")

        config_lines = []
        config_lines.append("server {")
        config_lines.append(f"    listen 80;")
        config_lines.append(f"    server_name {server_name};")

        if ssl_enabled:
            config_lines.append("    # HTTPS 跳转配置")
            config_lines.append("    return 301 https://$host$request_uri;")
            config_lines.append("}")
            config_lines.append("")
            config_lines.append("server {")
            config_lines.append("    listen 443 ssl;")
            config_lines.append(f"    server_name {server_name};")
            config_lines.append("    ssl_certificate     /etc/nginx/ssl/server.crt;")
            config_lines.append("    ssl_certificate_key /etc/nginx/ssl/server.key;")

        config_lines.append(f"    root {root_dir};")
        config_lines.append("    index index.html;")

        # 静态资源缓存配置
        if cache_enabled:
            config_lines.append("")
            config_lines.append("    # 静态资源缓存")
            config_lines.append("    location ~* \\.(css|js|jpg|jpeg|png|gif|ico|svg|woff2?)$ {")
            config_lines.append("        expires 30d;")
            config_lines.append("        add_header Cache-Control \"public, max-age=2592000\";")
            config_lines.append("    }")

        # gzip 压缩
        config_lines.append("")
        config_lines.append("    # gzip 压缩")
        config_lines.append("    gzip on;")
        config_lines.append("    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;")
        config_lines.append("}")

        return "\n".join(config_lines)

    @staticmethod
    def generate_reverse_proxy(proxy_pass: str, location: str = "/") -> str:
        """生成反向代理配置"""
        if not proxy_pass:
            error_exit("E006", "proxy_pass 不能为空")
        config_lines = []
        config_lines.append(f"location {location} {{")
        config_lines.append(f"    proxy_pass {proxy_pass};")
        config_lines.append("    proxy_set_header Host $host;")
        config_lines.append("    proxy_set_header X-Real-IP $remote_addr;")
        config_lines.append("    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;")
        config_lines.append("    proxy_set_header X-Forwarded-Proto $scheme;")
        config_lines.append("}")
        return "\n".join(config_lines)


# ============================================================
# 静态站点生成（C4）
# ============================================================
class StaticSiteGenerator:
    """静态站点生成器"""

    def __init__(self, output_dir: str = "./public"):
        self.output_dir = output_dir

    def generate_html(self, item: ContentItem, template: str = "default.html") -> str:
        """根据内容条目生成 HTML 页面"""
        # 简易模板渲染（无第三方库）
        title = item.title or "Untitled"
        slug = item.slug or ContentParser._slugify(title)
        body = item.body or f"<p>内容占位符 - {title}</p>"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="generator" content="merbtastic">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        header {{ border-bottom: 2px solid #eee; margin-bottom: 20px; }}
        .tags {{ margin: 10px 0; }}
        .tag {{ display: inline-block; background: #f0f0f0; padding: 2px 8px; border-radius: 3px; font-size: 0.9em; margin-right: 5px; }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
        <p>类型: {item.content_type}</p>
        {f'<p>日期: {item.year}-{item.month}</p>' if item.year and item.month else ''}
    </header>
    <main>
        {body}
    </main>
    <div class="tags">
        {''.join(f'<span class="tag">{tag}</span>' for tag in item.tags)}
    </div>
    <footer>
        <p>由 merbtastic 生成 | 模板: {template}</p>
    </footer>
</body>
</html>"""
        return html

    def generate_site(self, items: List[ContentItem], routes: List[RouteRule]) -> Dict[str, str]:
        """生成完整站点，返回文件路径到内容的映射"""
        try:
            site_files = {}
            if not items:
                return site_files

            # 生成首页
            index_html = self.generate_html(
                ContentItem(title="首页", slug="index", body="<h2>欢迎来到我的站点</h2><ul>" + 
                           "".join(f'<li><a href="{r.pattern}">{r.pattern}</a></li>' for r in routes[:10]) + "</ul>"),
                template="index.html"
            )
            site_files["index.html"] = index_html

            # 生成各内容页面
            for item in items:
                if item.content_type == "tag":
                    continue  # 标签页由路由生成器处理
                html = self.generate_html(item)
                file_path = f"{item.content_type}/{item.slug}.html"
                if item.content_type == "page":
                    file_path = f"{item.slug}.html"
                elif item.content_type in ("blog", "post"):
                    if item.year:
                        file_path = f"blog/{item.year}/{item.slug}.html"
                    else:
                        file_path = f"blog/{item.slug}.html"
                site_files[file_path] = html

            return site_files
        except Exception as e:
            error_exit("E007", str(e))

    def write_site(self, site_files: Dict[str, str]) -> List[str]:
        """将站点文件写入磁盘，返回生成的文件列表"""
        try:
            written_files = []
            for file_path, content in site_files.items():
                full_path = Path(self.output_dir) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                written_files.append(str(full_path))
            return written_files
        except OSError as e:
            error_exit("E003", str(e))


# ============================================================
# 批量处理与格式转换（C5）
# ============================================================
class BatchProcessor:
    """批量处理与格式转换器"""

    @staticmethod
    def convert_items_to_json(items: List[ContentItem]) -> str:
        """将内容条目转换为 JSON 格式"""
        data = []
        for item in items:
            data.append({
                "title": item.title,
                "slug": item.slug,
                "type": item.content_type,
                "year": item.year,
                "month": item.month,
                "tags": item.tags,
                "body": item.body[:200] + "..." if len(item.body) > 200 else item.body,
            })
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def generate_sitemap(routes: List[RouteRule], base_url: str) -> str:
        """生成 sitemap.xml"""
        sitemap_lines = []
        sitemap_lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        sitemap_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for route in routes:
            url = f"{base_url.rstrip('/')}{route.pattern}"
            sitemap_lines.append(f"  <url><loc>{url}</loc></url>")
        sitemap_lines.append("</urlset>")
        return "\n".join(sitemap_lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================
class SelfTest:
    """内置自检模块：使用硬编码样例数据验证核心逻辑"""

    @staticmethod
    def run() -> bool:
        """执行自检，返回是否通过"""
        print("=" * 60)
        print("merbtastic 自检开始")
        print("=" * 60)

        # ========== 测试 1: 内容解析 ==========
        print("\n[测试 1] 内容解析...")
        sample_json = """
        [
            {"title": "Hello World", "slug": "hello-world", "type": "page", "body": "Test content"},
            {"title": "My First Blog", "slug": "my-first-blog", "type": "blog", "year": "2026", "month": "03", "tags": ["tech", "intro"]}
        ]
        """
        items = ContentParser.parse_json(sample_json)
        assert len(items) == 2, f"JSON 解析应返回 2 条，实际 {len(items)}"
        assert items[0].title == "Hello World"
        assert items[0].content_type == "page"
        assert items[1].content_type == "blog"
        assert items[1].year == "2026"
        assert len(items[1].tags) == 2
        print(f"  通过: 解析到 {len(items)} 条内容")

        # ========== 测试 2: slug 生成 ==========
        print("\n[测试 2] slug 生成...")
        slug = ContentParser._slugify("Hello World Test!")
        assert slug == "hello-world-test", f"slug 生成错误: {slug}"
        slug2 = ContentParser._slugify("  Multiple   Spaces & Special Characters  ")
        assert "  " not in slug2, "slug 不应包含连续空格"
        print(f"  通过: '{slug}'")

        # ========== 测试 3: 路由生成 ==========
        print("\n[测试 3] 动态路由生成...")
        route_gen = RouteGenerator("http://example.com")
        routes = route_gen.generate_routes(items)
        assert len(routes) >= 2, f"应生成至少 2 条路由，实际 {len(routes)}"
        blog_routes = [r for r in routes if r.content_type == "blog"]
        assert len(blog_routes) >= 1, "应包含 blog 类型路由"
        # 检查 blog 路由包含年份
        assert any("/2026/" in r.pattern for r in blog_routes), "blog 路由应包含年份"
        print(f"  通过: 生成 {len(routes)} 条路由")

        # ========== 测试 4: Nginx 配置生成 ==========
        print("\n[测试 4] Nginx 配置生成...")
        nginx_conf = NginxConfigGenerator.generate_server_block(
            server_name="example.com",
            root_dir="/var/www/example",
            ssl_enabled=True
        )
        assert "server_name example.com" in nginx_conf
        assert "listen 80" in nginx_conf
        assert "listen 443 ssl" in nginx_conf
        assert "root /var/www/example" in nginx_conf
        print("  通过: Nginx 配置生成成功")

        # ========== 测试 5: 静态站点生成 ==========
        print("\n[测试 5] 静态站点生成...")
        site_gen = StaticSiteGenerator(output_dir="/tmp/merbtastic_selftest")
        site_files = site_gen.generate_site(items, routes)
        assert len(site_files) >= 3, f"应生成至少 3 个文件（首页+2内容页），实际 {len(site_files)}"
        assert "index.html" in site_files, "应包含首页"
        # 检查内容页面
        page_files = [f for f in site_files if f.endswith(".html") and f != "index.html"]
        assert len(page_files) >= 2, f"应至少 2 个内容页面，实际 {len(page_files)}"
        # 检查 HTML 内容结构
        sample_html = site_files.get("hello-world.html", "")
        assert "<html" in sample_html, "HTML 应包含 <html> 标签"
        assert "Hello World" in sample_html, "HTML 应包含标题"
        print(f"  通过: 生成 {len(site_files)} 个文件")

        # ========== 测试 6: 批量转换 ==========
        print("\n[测试 6] 批量格式转换...")
        json_output = BatchProcessor.convert_items_to_json(items)
        parsed_back = json.loads(json_output)
        assert len(parsed_back) == 2, "JSON 转换往返应保持一致"
        print("  通过: JSON 转换成功")

        # ========== 测试 7: sitemap 生成 ==========
        print("\n[测试 7] sitemap 生成...")
        sitemap = BatchProcessor.generate_sitemap(routes, "http://example.com")
        assert "<urlset" in sitemap, "sitemap 应包含 urlset 标签"
        assert "http://example.com" in sitemap, "sitemap 应包含站点 URL"
        print(f"  通过: sitemap 包含 {sitemap.count('<url>')} 个 URL")

        # ========== 测试 8: CSV 解析 ==========
        print("\n[测试 8] CSV 解析...")
        sample_csv = "title,slug,type,year,month,tags,body\nCSV Post,csv-post,blog,2026,04,test,csv body content\n"
        csv_items = ContentParser.parse_csv(sample_csv)
        assert len(csv_items) == 1, f"CSV 应解析 1 条，实际 {len(csv_items)}"
        assert csv_items[0].title == "CSV Post"
        assert csv_items[0].content_type == "blog"
        print("  通过: CSV 解析成功")

        # ========== 测试 9: YAML 解析 ==========
        print("\n[测试 9] YAML 解析...")
        sample_yaml = """
---
title: YAML Page
slug: yaml-page
type: page
tags: [test, yaml]
body: This is a YAML test page.
---
"""
        yaml_items = ContentParser.parse_yaml(sample_yaml)
        assert len(yaml_items) == 1, f"YAML 应解析 1 条，实际 {len(yaml_items)}"
        assert yaml_items[0].title == "YAML Page"
        assert yaml_items[0].slug == "yaml-page"
        assert yaml_items[0].content_type == "page"
        assert "yaml" in yaml_items[0].tags
        assert "test" in yaml_items[0].tags
        assert "This is a YAML test page." in yaml_items[0].body
        print(f"  通过: YAML 解析成功，body 内容: '{yaml_items[0].body[:30]}...'")

        # ========== 测试 10: 反向代理配置 ==========
        print("\n[测试 10] 反向代理配置...")
        proxy_conf = NginxConfigGenerator.generate_reverse_proxy("http://backend:8080")
        assert "proxy_pass http://backend:8080;" in proxy_conf
        assert "proxy_set_header Host $host;" in proxy_conf
        print("  通过: 反向代理配置生成成功")

        # ========== 汇总 ==========
        print("\n" + "=" * 60)
        print("✅ 所有自检测试通过！")
        print("=" * 60)
        return True


# ============================================================
# 主程序
# ============================================================
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        prog="merbtastic",
        description="站点构建与路由配置助手 - 将内容源转换为 Merb+Webgen 站点",
        epilog="示例: python main.py --input content.json --output ./public"
    )
    parser.add_argument("--input", "-i", help="输入内容文件（JSON/CSV/YAML）")
    parser.add_argument("--output", "-o", default="./public", help="输出目录（默认: ./public）")
    parser.add_argument("--base-url", default="http://localhost:4000", help="站点基础 URL")
    parser.add_argument("--server-name", help="Nginx server_name")
    parser.add_argument("--ssl", action="store_true", help="生成 HTTPS 配置")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--json-index", action="store_true", help="同时生成 JSON 索引")
    parser.add_argument("--sitemap", action="store_true", help="生成 sitemap.xml")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            SelfTest.run()
            sys.exit(0)
        except AssertionError as e:
            error_exit("E009", str(e))
        except Exception as e:
            error_exit("E009", f"自检异常: {e}")

    # 正常模式
    if not args.input:
        error_exit("E001", "请指定输入文件（--input）或使用 --selftest 运行自检")

    print("=" * 60)
    print("merbtastic - 站点构建工具")
    print("=" * 60)

    # 步骤 1: 解析内容
    print(f"\n[1/5] 解析内容源: {args.input}")
    items = ContentParser.parse_file(args.input)
    print(f"  解析到 {len(items)} 条内容")

    # 步骤 2: 生成路由
    print("\n[2/5] 生成动态路由...")
    route_gen = RouteGenerator(base_url=args.base_url)
    routes = route_gen.generate_routes(items)
    print(f"  生成 {len(routes)} 条路由规则")
    for route in routes[:5]:
        print(f"    {route.pattern} -> {route.template}")

    # 步骤 3: 生成站点
    print(f"\n[3/5] 生成静态站点 (输出: {args.output})...")
    site_gen = StaticSiteGenerator(output_dir=args.output)
    site_files = site_gen.generate_site(items, routes)
    written_files = site_gen.write_site(site_files)
    print(f"  生成 {len(written_files)} 个文件")

    # 步骤 4: 生成辅助文件
    print("\n[4/5] 生成辅助文件...")
    extra_files = []

    if args.json_index:
        json_index = BatchProcessor.convert_items_to_json(items)
        json_path = Path(args.output) / "index.json"
        json_path.write_text(json_index, encoding="utf-8")
        extra_files.append(str(json_path))
        print(f"  生成 JSON 索引: {json_path}")

    if args.sitemap:
        sitemap = BatchProcessor.generate_sitemap(routes, args.base_url)
        sitemap_path = Path(args.output) / "sitemap.xml"
        sitemap_path.write_text(sitemap, encoding="utf-8")
        extra_files.append(str(sitemap_path))
        print(f"  生成 sitemap: {sitemap_path}")

    # 步骤 5: 生成 Nginx 配置（如果指定了 server-name）
    if args.server_name:
        print("\n[5/5] 生成 Nginx 配置...")
        nginx_conf = NginxConfigGenerator.generate_server_block(
            server_name=args.server_name,
            root_dir=str(Path(args.output).resolve()),
            ssl_enabled=args.ssl
        )
        nginx_path = Path(args.output) / "nginx.conf"
        nginx_path.write_text(nginx_conf, encoding="utf-8")
        extra_files.append(str(nginx_path))
        print(f"  生成 Nginx 配置: {nginx_path}")
    else:
        print("\n[5/5] 跳过 Nginx 配置（未指定 --server-name）")

    # 完成
    print("\n" + "=" * 60)
    print("✅ 站点生成完成！")
    print(f"  输出目录: {args.output}")
    print(f"  生成文件: {len(written_files) + len(extra_files)} 个")
    print("=" * 60)


if __name__ == "__main__":
    main()
