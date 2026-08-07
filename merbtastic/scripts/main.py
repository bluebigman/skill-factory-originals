#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merbtastic — 站点构建与路由配置助手

依据功能规格独立实现（clean-room），不参考任何既有代码。
提供内容源解析、动态路由设计、Nginx 配置生成、静态站点生成等核心能力。
"""

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
E001 = "E001: 输入参数无效"
E002 = "E002: 内容源解析失败"
E003 = "E003: 路由规则生成失败"
E004 = "E004: Nginx 配置生成失败"
E005 = "E005: 静态页面生成失败"
E006 = "E006: 模板渲染失败"
E007 = "E007: 输出目录创建失败"
E008 = "E008: 文件写入失败"
E009 = "E009: 数据格式不支持"
E010 = "E010: 内部逻辑错误"


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ContentItem:
    """内容条目，代表一个页面或资源"""
    title: str
    slug: str
    content_type: str  # post / page / asset
    body: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: str = ""
    url_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "slug": self.slug,
            "content_type": self.content_type,
            "body": self.body,
            "metadata": self.metadata,
            "source_path": self.source_path,
            "url_path": self.url_path,
        }


@dataclass
class RouteRule:
    """动态路由规则"""
    pattern: str          # 如 /blog/:year/:slug
    controller: str       # 控制器名称
    action: str = "show"  # 动作名称
    constraints: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            "pattern": self.pattern,
            "controller": self.controller,
            "action": self.action,
            "constraints": self.constraints,
        }


@dataclass
class SiteConfig:
    """站点配置"""
    title: str
    base_url: str
    language: str = "zh-CN"
    author: str = ""
    theme: str = "default"
    output_dir: str = "public"
    routes: List[RouteRule] = field(default_factory=list)
    content_items: List[ContentItem] = field(default_factory=list)


# ============================================================
# 内容源解析模块
# ============================================================

class ContentParser:
    """内容源解析器：从多种格式提取内容结构"""

    @staticmethod
    def parse_yaml_text(text: str) -> Dict[str, Any]:
        """解析简单 YAML 文本（仅支持键值对和列表）"""
        result: Dict[str, Any] = {}
        try:
            current_list_key: Optional[str] = None
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("- "):
                    # 列表项
                    if current_list_key:
                        item = line[2:].strip()
                        result[current_list_key].append(item)
                    continue
                if ": " in line:
                    key, value = line.split(": ", 1)
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key not in result or not isinstance(result.get(key), list):
                        result[key] = []
                        current_list_key = key
                    result[key].append(value)
                    current_list_key = None
            # 处理单值情况
            for key, value in result.items():
                if len(value) == 1 and not isinstance(value[0], list):
                    result[key] = value[0]
        except Exception as exc:
            raise ValueError(f"{E002} YAML 解析失败: {exc}")
        return result

    @staticmethod
    def parse_json_text(text: str) -> Dict[str, Any]:
        """解析 JSON 文本"""
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("JSON 根节点必须是对象")
            return data
        except json.JSONDecodeError as exc:
            raise ValueError(f"{E002} JSON 解析失败: {exc}")

    @staticmethod
    def parse_csv_text(text: str) -> List[Dict[str, str]]:
        """解析 CSV 文本，返回字典列表"""
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not lines:
            return []
        headers = [h.strip() for h in lines[0].split(",")]
        records = []
        for line in lines[1:]:
            values = [v.strip() for v in line.split(",")]
            record = dict(zip(headers, values))
            records.append(record)
        return records

    @classmethod
    def parse_content(cls, data: str, fmt: str = "auto") -> Dict[str, Any]:
        """解析内容源数据"""
        try:
            if fmt == "auto":
                stripped = data.lstrip()
                if stripped.startswith("{"):
                    return cls.parse_json_text(data)
                elif ":" in data.splitlines()[0] if data.splitlines() else False:
                    return cls.parse_yaml_text(data)
                else:
                    raise ValueError(f"{E009} 无法自动识别格式")
            elif fmt == "json":
                return cls.parse_json_text(data)
            elif fmt == "yaml":
                return cls.parse_yaml_text(data)
            else:
                raise ValueError(f"{E009} 不支持的格式: {fmt}")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"{E002} 内容解析失败: {exc}")

    @classmethod
    def extract_content_items(cls, data: Dict[str, Any]) -> List[ContentItem]:
        """从解析后的数据中提取内容条目"""
        items = []
        try:
            raw_items = data.get("content", data.get("items", []))
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
            if not isinstance(raw_items, list):
                raise ValueError("内容数据必须是列表或对象")

            for idx, raw in enumerate(raw_items):
                if isinstance(raw, str):
                    raw = {"title": raw, "slug": f"item-{idx}"}
                if not isinstance(raw, dict):
                    continue
                title = str(raw.get("title", f"未命名 {idx}"))
                slug = str(raw.get("slug", re.sub(r'\W+', '-', title.lower())))
                content_type = str(raw.get("type", raw.get("content_type", "page")))
                body = str(raw.get("body", raw.get("content", "")))
                metadata = raw.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                source = str(raw.get("source", ""))
                item = ContentItem(
                    title=title,
                    slug=slug,
                    content_type=content_type,
                    body=body,
                    metadata=metadata,
                    source_path=source,
                )
                items.append(item)
        except Exception as exc:
            raise ValueError(f"{E002} 内容条目提取失败: {exc}")
        return items


# ============================================================
# 动态路由设计模块
# ============================================================

class RouteGenerator:
    """动态路由生成器"""

    # 支持的路由参数模式
    PARAM_PATTERN = re.compile(r':([a-zA-Z_][a-zA-Z0-9_]*)')

    @classmethod
    def validate_pattern(cls, pattern: str) -> bool:
        """验证路由模式是否合法"""
        if not pattern or not pattern.startswith("/"):
            return False
        # 不允许连续冒号或空参数
        if "::" in pattern or ": " in pattern:
            return False
        return True

    @classmethod
    def generate_route(cls, content_type: str, base_path: str = "") -> str:
        """根据内容类型生成路由模式"""
        base = base_path.rstrip("/") if base_path else ""
        base = f"/{base}" if base and not base.startswith("/") else base

        if content_type == "post":
            return f"{base}/blog/:year/:month/:slug"
        elif content_type == "page":
            return f"{base}/page/:slug"
        elif content_type == "asset":
            return f"{base}/assets/:filename"
        else:
            return f"{base}/content/:slug"

    @classmethod
    def build_routes(cls, content_items: List[ContentItem], base_path: str = "") -> List[RouteRule]:
        """从内容条目构建路由规则"""
        routes = []
        seen = set()
        try:
            for item in content_items:
                pattern = cls.generate_route(item.content_type, base_path)
                if pattern in seen:
                    continue
                seen.add(pattern)
                controller = f"{item.content_type}_controller"
                constraints = {}
                if item.content_type == "post":
                    constraints = {"year": r"\d{4}", "month": r"\d{2}"}
                route = RouteRule(
                    pattern=pattern,
                    controller=controller,
                    constraints=constraints,
                )
                routes.append(route)
        except Exception as exc:
            raise ValueError(f"{E003} 路由生成失败: {exc}")
        return routes


# ============================================================
# Nginx 配置生成模块
# ============================================================

class NginxConfigGenerator:
    """Nginx 配置生成器"""

    @staticmethod
    def _generate_server_block(domain: str, port: int, root: str) -> str:
        """生成 server 块"""
        return f"""
server {{
    listen {port};
    server_name {domain};

    root {root};
    index index.html;

    # 静态资源缓存
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {{
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}

    # 反向代理到动态服务
    location /api/ {{
        proxy_pass http://127.0.0.1:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    # 前端路由回退
    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""

    @staticmethod
    def _generate_https_redirect(domain: str) -> str:
        """生成 HTTP 到 HTTPS 的跳转配置"""
        return f"""
server {{
    listen 80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}
"""

    @classmethod
    def generate_config(cls, config: SiteConfig, domain: str, https: bool = True) -> str:
        """生成完整 Nginx 配置"""
        try:
            parts = []
            if https:
                parts.append(cls._generate_https_redirect(domain))
                parts.append(cls._generate_server_block(domain, 443, config.output_dir))
            else:
                parts.append(cls._generate_server_block(domain, 80, config.output_dir))
            return "\n".join(parts)
        except Exception as exc:
            raise ValueError(f"{E004} Nginx 配置生成失败: {exc}")


# ============================================================
# 静态站点生成模块
# ============================================================

class StaticSiteGenerator:
    """静态站点生成器"""

    # 简单模板引擎（支持 {{ var }} 和 {% for %} 基本语法）
    @staticmethod
    def render_template(template: str, context: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            result = template
            # 变量替换
            for key, value in context.items():
                result = result.replace("{{ " + key + " }}", str(value))
                result = result.replace("{{" + key + "}}", str(value))
            # 列表循环
            for_match = re.finditer(r'{% for (\w+) in (\w+) %}(.*?){% endfor %}', result, re.DOTALL)
            for match in for_match:
                item_var, list_var, body = match.groups()
                items = context.get(list_var, [])
                rendered = ""
                for item in items:
                    item_ctx = dict(context)
                    if isinstance(item, dict):
                        for k, v in item.items():
                            item_ctx[k] = v
                    else:
                        item_ctx[item_var] = item
                    rendered += body
                    for k, v in item_ctx.items():
                        if isinstance(v, (str, int, float)):
                            rendered = rendered.replace("{{ " + k + " }}", str(v))
                            rendered = rendered.replace("{{" + k + "}}", str(v))
                result = result.replace(match.group(0), rendered)
            return result
        except Exception as exc:
            raise ValueError(f"{E006} 模板渲染失败: {exc}")

    @classmethod
    def generate_html(cls, item: ContentItem, site_title: str) -> str:
        """生成单个 HTML 页面"""
        template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - {{ site_title }}</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .meta { color: #777; font-size: 0.9em; }
        .content { line-height: 1.6; }
    </style>
</head>
<body>
    <header>
        <h1>{{ title }}</h1>
        <div class="meta">类型: {{ content_type }} | 路径: {{ url_path }}</div>
    </header>
    <main class="content">
        {{ body }}
    </main>
    <footer>
        <p>&copy; {{ year }} {{ site_title }}</p>
    </footer>
</body>
</html>"""
        context = {
            "title": item.title,
            "site_title": site_title,
            "content_type": item.content_type,
            "url_path": item.url_path,
            "body": item.body,
            "year": datetime.now().year,
        }
        return cls.render_template(template, context)

    @classmethod
    def generate_site(cls, config: SiteConfig) -> List[Path]:
        """生成整个静态站点"""
        generated_files = []
        try:
            output_dir = Path(config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成页面
            for item in config.content_items:
                html = cls.generate_html(item, config.title)
                file_path = output_dir / f"{item.slug}.html"
                file_path.write_text(html, encoding="utf-8")
                generated_files.append(file_path)

            # 生成索引页
            index_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{{ site_title }}</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .item { margin: 10px 0; padding: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>{{ site_title }}</h1>
    <h2>内容列表</h2>
    {% for item in items %}
    <div class="item">
        <a href="{{ slug }}.html">{{ title }}</a>
        <span>({{ content_type }})</span>
    </div>
    {% endfor %}
</body>
</html>"""
            items_data = [item.to_dict() for item in config.content_items]
            index_html = cls.render_template(index_template, {
                "site_title": config.title,
                "items": items_data,
            })
            index_path = output_dir / "index.html"
            index_path.write_text(index_html, encoding="utf-8")
            generated_files.append(index_path)

        except OSError as exc:
            raise ValueError(f"{E007} 输出目录创建失败: {exc}")
        except Exception as exc:
            raise ValueError(f"{E005} 静态站点生成失败: {exc}")
        return generated_files


# ============================================================
# 主应用类
# ============================================================

class MerbtasticApp:
    """merbtastic 应用主类"""

    def __init__(self) -> None:
        self.config = SiteConfig(
            title="Merbtastic 站点",
            base_url="http://localhost:4000",
            output_dir="public",
        )

    def run(self, args: argparse.Namespace) -> int:
        """运行应用"""
        try:
            if args.selftest:
                return self._run_selftest()

            if args.command == "parse":
                return self._cmd_parse(args)
            elif args.command == "routes":
                return self._cmd_routes(args)
            elif args.command == "nginx":
                return self._cmd_nginx(args)
            elif args.command == "build":
                return self._cmd_build(args)
            else:
                print(E001)
                return 1
        except ValueError as exc:
            print(f"错误: {exc}")
            return 1
        except Exception as exc:
            print(f"{E010} 未预期错误: {exc}")
            return 1

    # ---------- 命令处理 ----------

    def _load_input(self, args: argparse.Namespace) -> Dict[str, Any]:
        """加载输入数据"""
        if args.input:
            path = Path(args.input)
            if not path.exists():
                raise ValueError(f"{E001} 输入文件不存在: {args.input}")
            data = path.read_text(encoding="utf-8")
            fmt = args.format if args.format != "auto" else "auto"
            return ContentParser.parse_content(data, fmt)
        elif args.json_input:
            return json.loads(args.json_input)
        else:
            raise ValueError(f"{E001} 需要提供输入数据")

    def _cmd_parse(self, args: argparse.Namespace) -> int:
        """解析内容源"""
        data = self._load_input(args)
        items = ContentParser.extract_content_items(data)
        print(f"解析到 {len(items)} 条内容:")
        for item in items:
            print(f"  - {item.title} [{item.content_type}] slug={item.slug}")
        return 0

    def _cmd_routes(self, args: argparse.Namespace) -> int:
        """生成路由规则"""
        data = self._load_input(args)
        items = ContentParser.extract_content_items(data)
        routes = RouteGenerator.build_routes(items, args.base_path or "")
        print(f"生成 {len(routes)} 条路由规则:")
        for route in routes:
            print(f"  {route.pattern} -> {route.controller}#{route.action}")
            if route.constraints:
                print(f"    约束: {json.dumps(route.constraints, ensure_ascii=False)}")
        return 0

    def _cmd_nginx(self, args: argparse.Namespace) -> int:
        """生成 Nginx 配置"""
        data = self._load_input(args)
        items = ContentParser.extract_content_items(data)
        config = SiteConfig(
            title=data.get("title", "Merbtastic 站点"),
            base_url=data.get("base_url", "http://localhost"),
            output_dir=data.get("output_dir", "public"),
            content_items=items,
        )
        domain = args.domain or "example.com"
        nginx_conf = NginxConfigGenerator.generate_config(config, domain, https=not args.no_https)
        print(nginx_conf)
        return 0

    def _cmd_build(self, args: argparse.Namespace) -> int:
        """构建静态站点"""
        data = self._load_input(args)
        items = ContentParser.extract_content_items(data)
        output_dir = args.output_dir or data.get("output_dir", "public")

        # 为内容条目生成 URL 路径
        for item in items:
            if item.content_type == "post" and "date" in item.metadata:
                date_str = str(item.metadata["date"])
                year = date_str[:4] if len(date_str) >= 4 else "2026"
                month = date_str[5:7] if len(date_str) >= 7 else "01"
                item.url_path = f"/blog/{year}/{month}/{item.slug}"
            else:
                item.url_path = f"/{item.slug}"

        config = SiteConfig(
            title=data.get("title", "Merbtastic 站点"),
            base_url=data.get("base_url", "http://localhost:4000"),
            output_dir=output_dir,
            content_items=items,
        )
        files = StaticSiteGenerator.generate_site(config)
        print(f"站点构建完成，生成 {len(files)} 个文件:")
        for file_path in files:
            print(f"  - {file_path}")
        return 0

    # ---------- 自检 ----------

    def _run_selftest(self) -> int:
        """运行内置自检"""
        print("=== merbtastic 自检开始 ===")
        failures = 0

        # 1. 内容解析测试
        print("\n[1/4] 内容源解析测试...")
        try:
            sample_data = {
                "title": "测试站点",
                "content": [
                    {"title": "第一篇文章", "slug": "first-post", "type": "post",
                     "metadata": {"date": "2026-01-15"}},
                    {"title": "关于页面", "slug": "about", "type": "page"},
                    {"title": "Logo 资源", "slug": "logo", "type": "asset"},
                ]
            }
            items = ContentParser.extract_content_items(sample_data)
            assert len(items) == 3, f"期望 3 条内容，实际 {len(items)}"
            assert items[0].content_type == "post"
            assert items[1].content_type == "page"
            print(f"  ✓ 解析 {len(items)} 条内容成功")
        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            failures += 1
        except Exception as exc:
            print(f"  ✗ 异常: {exc}")
            failures += 1

        # 2. 路由生成测试
        print("\n[2/4] 动态路由生成测试...")
        try:
            sample_items = [
                ContentItem(title="文章", slug="post-1", content_type="post"),
                ContentItem(title="页面", slug="page-1", content_type="page"),
            ]
            routes = RouteGenerator.build_routes(sample_items)
            assert len(routes) >= 2, f"期望至少 2 条路由，实际 {len(routes)}"
            post_routes = [r for r in routes if "blog" in r.pattern]
            assert len(post_routes) >= 1, "缺少博客路由"
            print(f"  ✓ 生成 {len(routes)} 条路由规则")
            for route in routes:
                print(f"    - {route.pattern}")
        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            failures += 1
        except Exception as exc:
            print(f"  ✗ 异常: {exc}")
            failures += 1

        # 3. Nginx 配置生成测试
        print("\n[3/4] Nginx 配置生成测试...")
        try:
            config = SiteConfig(title="测试", base_url="http://test.com", output_dir="public")
            nginx_conf = NginxConfigGenerator.generate_config(config, "test.com", https=True)
            assert "server {" in nginx_conf, "缺少 server 块"
            assert "listen 443" in nginx_conf, "缺少 HTTPS 监听"
            assert "listen 80" in nginx_conf, "缺少 HTTP 监听"
            assert "return 301" in nginx_conf, "缺少 HTTPS 跳转"
            print(f"  ✓ 配置生成成功，长度 {len(nginx_conf)} 字符")
        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            failures += 1
        except Exception as exc:
            print(f"  ✗ 异常: {exc}")
            failures += 1

        # 4. 静态页面生成测试
        print("\n[4/4] 静态页面生成测试...")
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                sample_items = [
                    ContentItem(title="测试文章", slug="test-post", content_type="post",
                                body="<p>测试内容</p>", metadata={"date": "2026-01-15"}),
                ]
                config = SiteConfig(
                    title="测试站点",
                    base_url="http://localhost",
                    output_dir=tmpdir,
                    content_items=sample_items,
                )
                # 设置 URL 路径
                for item in config.content_items:
                    item.url_path = f"/blog/2026/01/{item.slug}"
                files = StaticSiteGenerator.generate_site(config)
                assert len(files) >= 2, f"期望至少 2 个文件，实际 {len(files)}"
                html_content = files[0].read_text(encoding="utf-8")
                assert "测试文章" in html_content, "HTML 内容缺少标题"
                assert "<html" in html_content, "缺少 HTML 标签"
                print(f"  ✓ 生成 {len(files)} 个文件成功")
        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            failures += 1
        except Exception as exc:
            print(f"  ✗ 异常: {exc}")
            failures += 1

        # 汇总
        print(f"\n=== 自检完成: {'全部通过' if failures == 0 else f'{failures} 项失败'} ===")
        return 0 if failures == 0 else 1


# ============================================================
# 命令行入口
# ============================================================

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="merbtastic",
        description="Merb+Webgen 站点构建与路由配置助手",
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse 子命令
    parse_parser = subparsers.add_parser("parse", help="解析内容源")
    parse_parser.add_argument("--input", help="输入文件路径 (JSON/YAML)")
    parse_parser.add_argument("--json-input", help="直接传入 JSON 字符串")
    parse_parser.add_argument("--format", default="auto", choices=["auto", "json", "yaml"],
                              help="输入格式")

    # routes 子命令
    routes_parser = subparsers.add_parser("routes", help="生成动态路由")
    routes_parser.add_argument("--input", help="输入文件路径")
    routes_parser.add_argument("--json-input", help="直接传入 JSON 字符串")
    routes_parser.add_argument("--format", default="auto", choices=["auto", "json", "yaml"])
    routes_parser.add_argument("--base-path", help="路由基础路径")

    # nginx 子命令
    nginx_parser = subparsers.add_parser("nginx", help="生成 Nginx 配置")
    nginx_parser.add_argument("--input", help="输入文件路径")
    nginx_parser.add_argument("--json-input", help="直接传入 JSON 字符串")
    nginx_parser.add_argument("--format", default="auto", choices=["auto", "json", "yaml"])
    nginx_parser.add_argument("--domain", help="域名")
    nginx_parser.add_argument("--no-https", action="store_true", help="禁用 HTTPS 跳转")

    # build 子命令
    build_parser = subparsers.add_parser("build", help="构建静态站点")
    build_parser.add_argument("--input", help="输入文件路径")
    build_parser.add_argument("--json-input", help="直接传入 JSON 字符串")
    build_parser.add_argument("--format", default="auto", choices=["auto", "json", "yaml"])
    build_parser.add_argument("--output-dir", help="输出目录")

    return parser


def main() -> int:
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    app = MerbtasticApp()
    return app.run(args)


if __name__ == "__main__":
    sys.exit(main())
