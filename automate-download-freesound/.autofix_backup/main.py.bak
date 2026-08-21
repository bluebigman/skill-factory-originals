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
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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


@dataclass
class TaskConfig:
    """任务配置"""
    output_format: str = "json"  # json / csv / markdown
    output_dir: str = "."
    max_items: int = 100
    include_metadata: bool = True
    naming_prefix: str = "sound_"


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


class ReportGenerator:
    """生成结构化输出报告"""

    @staticmethod
    def to_json(items: List[DownloadItem], include_metadata: bool = True) -> str:
        """生成 JSON 格式报告"""
        data = {
            "generated_at": "generated_by_skill",
            "item_count": len(items),
            "items": [asdict(item) for item in items],
        }
        if not include_metadata:
            # 精简模式，只保留关键字段
            for item in data["items"]:
                for key in list(item.keys()):
                    if key not in ("source_url", "file_name", "category"):
                        del item[key]
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(items: List[DownloadItem]) -> str:
        """生成 CSV 格式报告"""
        if not items:
            return "source_url,file_name,category,tags,description,license_type\n"

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
        lines.append("| # | 文件名 | 来源 URL | 分类 | 标签 |")
        lines.append("|---|--------|----------|------|------|")

        for idx, item in enumerate(items, 1):
            tags_str = ", ".join(item.tags[:3]) if item.tags else "-"
            lines.append(
                f"| {idx} | {item.file_name} | {item.source_url} | "
                f"{item.category} | {tags_str} |"
            )

        lines.extend(["", "## 操作指引", ""])
        lines.append("1. 使用浏览器打开上述 URL 验证资源可用性。")
        lines.append("2. 下载后请检查许可证类型，遵守使用规范。")
        lines.append("3. 建议使用 `wget` 或 `curl` 配合用户代理下载。")
        lines.append("4. 本清单由自动化工具生成，仅供学习研究使用。")

        return "\n".join(lines)


class BatchProcessor:
    """批量任务处理器"""

    def __init__(self, config: TaskConfig):
        self.config = config
        self.generator = DownloadListGenerator(config)

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

        # 写入文件
        try:
            os.makedirs(self.config.output_dir, exist_ok=True)
            file_name = f"download_manifest_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = os.path.join(self.config.output_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return file_path
        except OSError as e:
            raise SkillError("E006", f"文件写入失败: {e}")

    def print_summary(self, items: List[DownloadItem]) -> None:
        """打印任务摘要"""
        print("\n===== 任务摘要 =====")
        print(f"生成条目数: {len(items)}")
        if items:
            print(f"输出格式: {self.config.output_format}")
            print(f"输出目录: {self.config.output_dir}")
            print("\n前 5 个条目预览:")
            for i, item in enumerate(items[:5], 1):
                print(f"  {i}. {item.file_name} <- {item.source_url}")
        print("===================\n")


# ---------- 自检模块 ----------

class SelfTest:
    """内置自检逻辑，使用硬编码样例数据验证核心功能"""

    SAMPLE_URLS = [
        "https://freesound.org/people/user1/sounds/123456/",
        "https://freesound.org/s/654321",
        "https://freesound.org/browse/samples/",
        "https://invalid-url-no-scheme.com/test",  # 应被跳过
    ]

    SAMPLE_KEYWORDS = ["rain", "thunder", "wind", "rain"]  # 含重复项

    @staticmethod
    def run() -> bool:
        """执行所有自检断言"""
        print("开始自检...")

        # 1. URL 解析测试
        parser = FreesoundRequestParser()
        info = parser.parse_url(SelfTest.SAMPLE_URLS[0])
        assert info["sound_id"] == "123456", "URL 解析失败: sound_id 不匹配"
        assert info["url_type"] == "sound", "URL 解析失败: url_type 错误"
        print("  ✓ URL 解析功能正常")

        # 2. 关键词解析测试
        keywords = parser.parse_keywords(SelfTest.SAMPLE_KEYWORDS)
        assert len(keywords) == 3, "关键词去重失败"
        assert "rain" in keywords, "关键词缺失"
        print("  ✓ 关键词解析功能正常")

        # 3. 生成器测试
        config = TaskConfig(output_format="json", max_items=10)
        generator = DownloadListGenerator(config)

        # 从 URL 生成（只使用有效的 URL）
        valid_urls = [u for u in SelfTest.SAMPLE_URLS[:3]]
        url_items = generator.generate_from_urls(valid_urls)
        assert len(url_items) > 0, "URL 生成失败"
        assert len(url_items) == 3, f"URL 条目生成数量错误: {len(url_items)}"
        assert all(item.source_url for item in url_items), "URL 条目缺少 source_url"
        print(f"  ✓ URL 条目生成正常（{len(url_items)} 条）")

        # 从关键词生成
        kw_items = generator.generate_from_keywords(SelfTest.SAMPLE_KEYWORDS)
        assert len(kw_items) == 3, f"关键词条目生成数量错误: {len(kw_items)}"
        assert all(item.tags for item in kw_items), "关键词条目缺少标签"
        print(f"  ✓ 关键词条目生成正常（{len(kw_items)} 条）")

        # 合并测试
        merged = generator.merge_items(url_items, kw_items)
        assert len(merged) == 6, f"合并后数量错误: {len(merged)}"
        print(f"  ✓ 条目合并功能正常（{len(merged)} 条）")

        # 4. 报告生成测试
        report_gen = ReportGenerator()

        # JSON
        json_report = report_gen.to_json(url_items)
        json_data = json.loads(json_report)
        assert json_data["item_count"] == len(url_items), "JSON 条目计数错误"
        assert "items" in json_data, "JSON 缺少 items 字段"
        print("  ✓ JSON 报告生成正常")

        # CSV
        csv_report = report_gen.to_csv(url_items)
        assert "source_url" in csv_report, "CSV 缺少表头"
        assert len(csv_report.splitlines()) >= 2, "CSV 内容不足"
        print("  ✓ CSV 报告生成正常")

        # Markdown
        md_report = report_gen.to_markdown(url_items)
        assert "# 声音素材下载清单" in md_report, "Markdown 缺少标题"
        assert "|" in md_report, "Markdown 缺少表格"
        print("  ✓ Markdown 报告生成正常")

        # 5. 批量处理测试
        processor = BatchProcessor(config)
        processed = processor.process_input(
            urls=valid_urls,
            keywords=SelfTest.SAMPLE_KEYWORDS[:2],
        )
        assert len(processed) == 5, f"批量处理数量错误: {len(processed)}"
        print(f"  ✓ 批量处理功能正常（{len(processed)} 条）")

        # 6. 文件写入测试（使用临时目录）
        with tempfile.TemporaryDirectory() as tmpdir:
            test_config = TaskConfig(output_format="json", output_dir=tmpdir)
            test_processor = BatchProcessor(test_config)
            file_path = test_processor.write_report(url_items)
            assert os.path.exists(file_path), "文件写入失败"
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert len(content) > 0, "文件内容为空"
            print(f"  ✓ 文件写入功能正常（{file_path}）")

        # 7. 错误处理测试
        try:
            parser.parse_url("")
            raise AssertionError("空 URL 未抛出异常")
        except SkillError as e:
            assert e.code == "E003", f"错误码不匹配: {e.code}"
        print("  ✓ 错误处理功能正常")

        print("自检全部通过 ✓")
        return True


# ---------- 命令行入口 ----------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="声音素材采集与下载处理工具（clean-room 实现）",
        epilog="示例: python main.py --urls https://freesound.org/s/123 --keywords rain --format json",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        help="Freesound 资源 URL 列表",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        help="搜索关键词列表",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="输出目录（默认: 当前目录）",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=100,
        help="最大条目数（默认: 100）",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="精简输出，不包含完整元数据",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )

    args = parser.add_argument("--version", default=None, help="参数")
    ap.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = SelfTest.run()
            return 0 if success else 1
        except AssertionError as e:
            print(f"[E007] 自检断言失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[E010] 自检异常: {e}", file=sys.stderr)
            return 1

    # 正常处理模式
    try:
        # 校验输入
        if not args.urls and not args.keywords:
            print("错误: 请提供 --urls 或 --keywords 参数", file=sys.stderr)
            parser.print_help()
            return 1

        # 构建配置
        config = TaskConfig(
            output_format=args.format,
            output_dir=args.output_dir,
            max_items=args.max_items,
            include_metadata=not args.no_metadata,
        )

        # 处理任务
        processor = BatchProcessor(config)
        items = processor.process_input(urls=args.urls, keywords=args.keywords)

        # 生成报告
        file_path = processor.write_report(items)
        processor.print_summary(items)

        print(f"报告已生成: {file_path}")
        print("提示: 本工具不执行实际网络请求，请使用浏览器或下载工具获取资源。")

        return 0

    except SkillError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
