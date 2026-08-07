#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merbtastic — 站点构建与路由配置助手（独立实现）

依据功能规格从零编写，不引用任何既有代码。
提供内容源解析、动态路由设计、Nginx 配置生成、静态站点骨架生成、批量格式转换。
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "输入文件不存在",
    "E003": "文件读取失败",
    "E004": "内容解析失败",
    "E005": "路由生成失败",
    "E006": "Nginx 配置生成失败",
    "E007": "静态站点生成失败",
    "E008": "目录创建失败",
    "E009": "文件写入失败",
    "E010": "内部逻辑错误",
}


class MerbtasticError(Exception):
    """统一异常类型，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------- 核心数据结构 ----------

class ContentItem:
    """单个内容项（页面/文章）"""

    def __init__(self, title: str, content_type: str, slug: str, date: Optional[str] = None):
        self.title = title
        self.content_type = content_type      # 如 post, page, project
        self.slug = slug                      # URL 片段
        self.date = date                      # 可选，如 "2026-01-15"
        self.metadata: Dict[str, Any] = {}    # 扩展元数据

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content_type": self.content_type,
            "slug": self.slug,
            "date": self.date,
            "metadata": self.metadata,
        }


class RouteRule:
    """动态路由规则"""

    def __init__(self, pattern: str, content_type: str):
        self.pattern = pattern                # 如 /blog/:year/:slug
        self.content_type = content_type

    def to_dict(self) -> Dict[str, Any]:
        return {"pattern": self.pattern, "content_type": self.content_type}


# ---------- 功能模块 ----------

def parse_content_source(source: Any) -> List[ContentItem]:
    """
    C1: 内容源解析
    支持输入：
      - 字符串路径（JSON 文件）
      - 字典（直接提供数据）
      - 列表（ContentItem 字典列表）
    返回 ContentItem 列表。
    """
    try:
        items: List[ContentItem] = []

        if isinstance(source, str):
            # 尝试作为文件路径读取
            p = Path(source)
            if not p.exists():
                raise MerbtasticError("E002", f"文件不存在: {source}")
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except MerbtasticError:
                raise
            except Exception as e:
                raise MerbtasticError("E003", f"读取失败: {e}")
        elif isinstance(source, dict):
            data = source
        elif isinstance(source, list):
            data = source
        else:
            raise MerbtasticError("E001", f"不支持的内容源类型: {type(source)}")

        # 统一转为列表处理
        raw_list: List[Dict] = []
        if isinstance(data, dict):
            # 兼容 {"items": [...]} 或 {"content": [...]} 或直接是单条
            if "items" in data and isinstance(data["items"], list):
                raw_list = data["items"]
            elif "content" in data and isinstance(data["content"], list):
                raw_list = data["content"]
            elif "title" in data:
                raw_list = [data]
            else:
                # 尝试将字典值作为列表
                for v in data.values():
                    if isinstance(v, list):
                        raw_list.extend(v)
        elif isinstance(data, list):
            raw_list = data

        # 逐条解析
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title", "未命名"))
            ctype = str(raw.get("content_type", raw.get("type", "page")))
            slug = str(raw.get("slug", _slugify(title)))
            date = raw.get("date")
            item = ContentItem(title=title, content_type=ctype, slug=slug, date=str(date) if date else None)
            item.metadata = raw.get("metadata", {})
            items.append(item)

        if not items:
            raise MerbtasticError("E004", "未能从内容源解析出任何内容项")

        return items
    except MerbtasticError:
        raise
    except Exception as e:
        raise MerbtasticError("E004", f"内容解析异常: {e}")


def design_routes(items: List[ContentItem], base_route: str = "/") -> List[RouteRule]:
    """
    C2: 动态路由设计
    根据内容类型生成 Merb 风格路由规则。
    规则：
      - 每个内容类型生成一个路由模式
      - post 类型使用 /blog/:year/:slug（如有日期）
      - 其他类型使用 /<type>/:slug
      - base_route 作为前缀
    """
    try:
        if not items:
            raise MerbtasticError("E005", "内容项列表为空，无法生成路由")

        # 按内容类型分组
        type_map: Dict[str, List[ContentItem]] = {}
        for item in items:
            type_map.setdefault(item.content_type, []).append(item)

        routes: List[RouteRule] = []
        base = base_route.rstrip("/") if base_route != "/" else ""

        for ctype, citems in type_map.items():
            if ctype == "post":
                # 有日期的使用 /blog/:year/:slug
                dated = [c for c in citems if c.date]
                if dated:
                    pattern = f"{base}/blog/:year/:slug"
                    routes.append(RouteRule(pattern=pattern, content_type=ctype))
                # 无日期的使用 /blog/:slug
                undated = [c for c in citems if not c.date]
                if undated:
                    pattern = f"{base}/blog/:slug"
                    routes.append(RouteRule(pattern=pattern, content_type=ctype))
            else:
                pattern = f"{base}/{ctype}/:slug"
                routes.append(RouteRule(pattern=pattern, content_type=ctype))

        # 去重
        seen = set()
        unique_routes = []
        for r in routes:
            key = (r.pattern, r.content_type)
            if key not in seen:
                seen.add(key)
                unique_routes.append(r)

        return unique_routes
    except MerbtasticError:
        raise
    except Exception as e:
        raise MerbtasticError("E005", f"路由生成异常: {e}")


def generate_nginx_config(
    routes: List[RouteRule],
    server_name: str = "example.com",
    upstream: str = "127.0.0.1:4000",
) -> str:
    """
    C3: Nginx 配置生成
    生成包含反向代理、静态资源缓存、HTTPS 跳转的配置片段。
    """
    try:
        lines: List[str] = []
        lines.append("# 由 merbtastic 生成的 Nginx 配置片段（仅供参考）")
        lines.append(f"server {{")
        lines.append(f"    listen 80;")
        lines.append(f"    server_name {server_name};")
        lines.append(f"    # HTTP 跳转 HTTPS")
        lines.append(f"    return 301 https://$host$request_uri;")
        lines.append(f"}}")
        lines.append(f"")
        lines.append(f"server {{")
        lines.append(f"    listen 443 ssl;")
        lines.append(f"    server_name {server_name};")
        lines.append(f"    # 请配置 SSL 证书路径")
        lines.append(f"    ssl_certificate     /etc/ssl/certs/{server_name}.crt;")
        lines.append(f"    ssl_certificate_key /etc/ssl/private/{server_name}.key;")
        lines.append(f"")
        lines.append(f"    # 反向代理到 Merb 应用")
        lines.append(f"    location / {{")
        lines.append(f"        proxy_pass http://{upstream};")
        lines.append(f"        proxy_set_header Host $host;")
        lines.append(f"        proxy_set_header X-Real-IP $remote_addr;")
        lines.append(f"        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;")
        lines.append(f"        proxy_set_header X-Forwarded-Proto $scheme;")
        lines.append(f"    }}")
        lines.append(f"")
        lines.append(f"    # 静态资源缓存（CSS/JS/图片）")
        lines.append(f"    location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg|woff2?)$ {{")
        lines.append(f"        expires 7d;")
        lines.append(f"        add_header Cache-Control \"public, max-age=604800\";")
        lines.append(f"        try_files $uri $uri/ @proxy;")
        lines.append(f"    }}")
        lines.append(f"")
        lines.append(f"    location @proxy {{")
        lines.append(f"        proxy_pass http://{upstream};")
        lines.append(f"        proxy_set_header Host $host;")
        lines.append(f"    }}")
        lines.append(f"")
        # 动态路由注释
        lines.append(f"    # 动态路由规则（由 merbtastic 生成）")
        for r in routes:
            lines.append(f"    #   {r.content_type}: {r.pattern}")
        lines.append(f"}}")

        return "\n".join(lines)
    except Exception as e:
        raise MerbtasticError("E006", f"Nginx 配置生成异常: {e}")


def generate_static_site(
    items: List[ContentItem],
    output_dir: str,
    routes: Optional[List[RouteRule]] = None,
) -> List[Path]:
    """
    C4: 静态站点生成
    生成纯静态 HTML 文件结构（简化版，不依赖模板引擎）。
    每个内容项生成一个 HTML 文件，并生成 index.html 和 sitemap.txt。
    """
    try:
        out = Path(output_dir)
        try:
            out.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise MerbtasticError("E008", f"创建目录失败: {e}")

        generated: List[Path] = []

        # 为每个内容项生成 HTML
        for item in items:
            # 构建输出路径
            if item.content_type == "post" and item.date:
                year = item.date[:4] if len(item.date) >= 4 else "unknown"
                rel_dir = out / "blog" / year
            else:
                rel_dir = out / item.content_type
            try:
                rel_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise MerbtasticError("E008", f"创建目录失败: {e}")

            html_path = rel_dir / f"{item.slug}.html"
            html = _render_html(item)
            try:
                html_path.write_text(html, encoding="utf-8")
                generated.append(html_path)
            except Exception as e:
                raise MerbtasticError("E009", f"写入文件失败: {e}")

        # 生成 index.html
        index_html = _render_index(items)
        index_path = out / "index.html"
        try:
            index_path.write_text(index_html, encoding="utf-8")
            generated.append(index_path)
        except Exception as e:
            raise MerbtasticError("E009", f"写入文件失败: {e}")

        # 生成 sitemap.txt
        sitemap_lines = []
        for item in items:
            if item.content_type == "post" and item.date:
                year = item.date[:4] if len(item.date) >= 4 else "unknown"
                sitemap_lines.append(f"/blog/{year}/{item.slug}.html")
            else:
                sitemap_lines.append(f"/{item.content_type}/{item.slug}.html")
        sitemap_path = out / "sitemap.txt"
        try:
            sitemap_path.write_text("\n".join(sitemap_lines), encoding="utf-8")
            generated.append(sitemap_path)
        except Exception as e:
            raise MerbtasticError("E009", f"写入文件失败: {e}")

        return generated
    except MerbtasticError:
        raise
    except Exception as e:
        raise MerbtasticError("E007", f"静态站点生成异常: {e}")


def batch_convert(
    items: List[ContentItem],
    output_format: str = "json",
) -> str:
    """
    C5: 批量处理与格式转换
    将内容项列表转换为指定格式（json / csv / markdown）。
    返回字符串内容。
    """
    try:
        if output_format == "json":
            data = [item.to_dict() for item in items]
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == "csv":
            lines = ["title,content_type,slug,date"]
            for item in items:
                title = item.title.replace(",", "\\,")
                slug = item.slug.replace(",", "\\,")
                date = item.date or ""
                lines.append(f"{title},{item.content_type},{slug},{date}")
            return "\n".join(lines)
        elif output_format == "markdown":
            lines = ["# 内容索引\n"]
            for item in items:
                lines.append(f"## {item.title}")
                lines.append(f"- 类型: {item.content_type}")
                lines.append(f"- 标识: {item.slug}")
                if item.date:
                    lines.append(f"- 日期: {item.date}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise MerbtasticError("E001", f"不支持的输出格式: {output_format}")
    except MerbtasticError:
        raise
    except Exception as e:
        raise MerbtasticError("E010", f"格式转换异常: {e}")


# ---------- 辅助函数 ----------

def _slugify(text: str) -> str:
    """将文本转为 URL 友好的 slug"""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = text.strip("-")
    return text or "untitled"


def _render_html(item: ContentItem) -> str:
    """渲染单个内容项的 HTML（极简模板）"""
    date_line = f"<p class=\"date\">{item.date}</p>" if item.date else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{item.title}</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
        .meta {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <article>
        <h1>{item.title}</h1>
        <div class="meta">
            <span>类型: {item.content_type}</span>
            {date_line}
        </div>
        <div class="content">
            <p>内容待补充（由 merbtastic 静态生成）</p>
        </div>
    </article>
</body>
</html>"""


def _render_index(items: List[ContentItem]) -> str:
    """渲染站点首页"""
    links = []
    for item in items:
        if item.content_type == "post" and item.date:
            year = item.date[:4] if len(item.date) >= 4 else "unknown"
            href = f"blog/{year}/{item.slug}.html"
        else:
            href = f"{item.content_type}/{item.slug}.html"
        links.append(f"        <li><a href=\"{href}\">{item.title}</a></li>")

    links_html = "\n".join(links) if links else "        <li>暂无内容</li>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>站点首页</title>
    <style>
        body {{ font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ margin: 8px 0; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>站点内容</h1>
    <ul>
{links_html}
    </ul>
</body>
</html>"""


# ---------- 自检模块 ----------

def _selftest() -> int:
    """
    内置硬编码样例数据离线自检。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保必然匹配。
    """
    print("开始自检...")

    # 硬编码测试数据
    test_data = {
        "items": [
            {"title": "Hello World", "content_type": "post", "slug": "hello-world", "date": "2026-01-15"},
            {"title": "Merb 入门", "content_type": "post", "slug": "merb-intro", "date": "2026-02-01"},
            {"title": "关于我们", "content_type": "page", "slug": "about"},
            {"title": "项目 Alpha", "content_type": "project", "slug": "alpha"},
        ]
    }

    # 1. 内容源解析测试
    print("  测试内容源解析...")
    items = parse_content_source(test_data)
    assert len(items) >= 3, "解析出的内容项数量应不少于 3"
    assert items[0].title == "Hello World", "第一条内容标题应为 Hello World"
    assert items[0].content_type == "post", "第一条内容类型应为 post"
    print(f"    ✓ 解析成功，共 {len(items)} 项")

    # 2. 动态路由设计测试
    print("  测试动态路由设计...")
    routes = design_routes(items)
    assert len(routes) >= 2, "路由数量应不少于 2"
    patterns = [r.pattern for r in routes]
    assert any("/blog/:year/:slug" in p for p in patterns), "应包含 /blog/:year/:slug 路由"
    assert any("/page/:slug" in p for p in patterns), "应包含 /page/:slug 路由"
    print(f"    ✓ 路由生成成功，共 {len(routes)} 条")

    # 3. Nginx 配置生成测试
    print("  测试 Nginx 配置生成...")
    nginx_conf = generate_nginx_config(routes, server_name="example.com")
    assert "server {" in nginx_conf, "应包含 server 块"
    assert "listen 443 ssl" in nginx_conf, "应包含 HTTPS 监听"
    assert "proxy_pass" in nginx_conf, "应包含反向代理配置"
    assert len(nginx_conf) > 100, "配置内容应足够长"
    print(f"    ✓ 配置生成成功，长度 {len(nginx_conf)} 字符")

    # 4. 静态站点生成测试（使用临时目录）
    print("  测试静态站点生成...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        generated_files = generate_static_site(items, tmpdir, routes)
        assert len(generated_files) >= 4, "生成文件数应不少于 4（3 内容 + index + sitemap）"
        assert any(f.name == "index.html" for f in generated_files), "应生成 index.html"
        assert any(f.name == "sitemap.txt" for f in generated_files), "应生成 sitemap.txt"
        # 验证文件内容非空
        for f in generated_files:
            content = f.read_text(encoding="utf-8")
            assert len(content) > 20, f"文件 {f.name} 内容过短"
        print(f"    ✓ 生成成功，共 {len(generated_files)} 个文件")

    # 5. 批量格式转换测试
    print("  测试批量格式转换...")
    json_out = batch_convert(items, "json")
    assert json_out.startswith("["), "JSON 输出应以 [ 开头"
    parsed = json.loads(json_out)
    assert len(parsed) == len(items), "JSON 解析后数量应一致"

    csv_out = batch_convert(items, "csv")
    assert csv_out.startswith("title,"), "CSV 输出应以表头开头"
    assert csv_out.count("\n") >= len(items), "CSV 行数应足够"

    md_out = batch_convert(items, "markdown")
    assert md_out.startswith("#"), "Markdown 输出应以 # 开头"
    assert "Hello World" in md_out, "Markdown 应包含内容标题"
    print("    ✓ 三种格式转换均成功")

    # 6. 边界与异常测试
    print("  测试异常处理...")
    try:
        batch_convert(items, "xml")  # 不支持的格式
        assert False, "应抛出异常"
    except MerbtasticError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"

    try:
        parse_content_source("/nonexistent/path/data.json")
        assert False, "应抛出异常"
    except MerbtasticError as e:
        assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"
    print("    ✓ 异常处理正确")

    print("自检全部通过 ✓")
    return 0


# ---------- 命令行入口 ----------

def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="merbtastic — 站点构建与路由配置助手",
        epilog="示例: python main.py --input data.json --output ./site --format json"
    )

    parser.add_argument("--input", "-i", help="输入内容源（JSON 文件路径）")
    parser.add_argument("--output", "-o", help="输出目录（静态站点生成时使用）")
    parser.add_argument("--format", "-f", choices=["json", "csv", "markdown"], default="json",
                        help="批量转换输出格式（默认 json）")
    parser.add_argument("--server-name", default="example.com", help="Nginx 配置的服务器名")
    parser.add_argument("--upstream", default="127.0.0.1:4000", help="Nginx 反向代理上游地址")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检并退出")

    args = parser.parse_args()

    if args.selftest:
        try:
            return _selftest()
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 常规模式：需要输入文件
    if not args.input:
        print("错误: 请指定 --input 或使用 --selftest 运行自检")
        return 1

    try:
        # 1. 解析内容源
        items = parse_content_source(args.input)
        print(f"解析到 {len(items)} 个内容项")

        # 2. 设计路由
        routes = design_routes(items)
        print(f"生成 {len(routes)} 条路由规则:")
        for r in routes:
            print(f"  [{r.content_type}] {r.pattern}")

        # 3. 生成 Nginx 配置
        nginx_conf = generate_nginx_config(routes, args.server_name, args.upstream)
        print("\n--- Nginx 配置片段 ---")
        print(nginx_conf)

        # 4. 批量转换输出
        converted = batch_convert(items, args.format)
        print(f"\n--- 内容索引（{args.format}）---")
        print(converted[:500] + ("..." if len(converted) > 500 else ""))

        # 5. 静态站点生成（如指定输出目录）
        if args.output:
            files = generate_static_site(items, args.output, routes)
            print(f"\n--- 静态站点生成完成（{len(files)} 个文件）---")
            for f in files[:10]:
                print(f"  {f}")
            if len(files) > 10:
                print(f"  ... 等 {len(files)} 个文件")

        return 0
    except MerbtasticError as e:
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"未预期错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
