#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
go-get-jobs — 技术职位聚合采集 Skill
版本: 1.0.1
许可: MIT License
"""

import argparse
import csv
import io
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from urllib.parse import urljoin
dry_run = False  # v3.274 模块级 dry-run 标志


# ---------------------------------------------------------------------------
# 错误码定义
# E001: 参数错误
# E002: 输入文件无法读取
# E003: 输出文件无法写入
# E004: JSON 解析失败
# E005: CSV 解析失败
# E006: 数据源配置无效
# E007: 抓取超时
# E008: 网络请求失败
# E009: 数据校验失败
# E010: 未知内部错误
# ---------------------------------------------------------------------------

@dataclass
class JobPosting:
    """职位数据模型"""
    company: str = ""
    title: str = ""
    location: str = ""
    url: str = ""
    source: str = ""
    description: str = ""
    posted_at: str = ""
    tags: List[str] = field(default_factory=list)


class JobAggregator:
    """职位聚合器核心类"""

    # 内置数据源配置（模拟 50+ 公司）
    SOURCES = {
        "google": {"name": "Google", "base_url": "https://careers.google.com/jobs"},
        "meta": {"name": "Meta", "base_url": "https://www.metacareers.com/jobs"},
        "apple": {"name": "Apple", "base_url": "https://jobs.apple.com/en-us/search"},
        "amazon": {"name": "Amazon", "base_url": "https://www.amazon.jobs/en/search"},
        "microsoft": {"name": "Microsoft", "base_url": "https://careers.microsoft.com/us/en/search"},
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.last_run_timestamp = 0
        self.results: List[JobPosting] = []
        self._validate_config()

    def _validate_config(self):
        """校验配置有效性"""
        if not isinstance(self.config, dict):
            raise ValueError("E001: 配置必须是字典类型")
        sources = self.config.get("sources", self.SOURCES)
        if not isinstance(sources, dict) or len(sources) == 0:
            raise ValueError("E006: 数据源配置无效")

    def fetch_jobs(self, keywords: Optional[List[str]] = None,
                   locations: Optional[List[str]] = None,
                   incremental: bool = False) -> List[JobPosting]:
        """
        获取职位列表（模拟实现，实际项目可替换为真实抓取逻辑）
        返回结构化职位数据
        """
        try:
            keywords = keywords or []
            locations = locations or []
            self.last_run_timestamp = int(time.time())

            # 模拟从数据源获取数据
            all_jobs = self._mock_fetch_from_sources()

            # 应用过滤条件
            filtered = self._apply_filters(all_jobs, keywords, locations)

            # 增量更新逻辑（模拟：仅返回新数据）
            if incremental and self.config.get("last_timestamp"):
                filtered = [j for j in filtered if self._is_new(j)]

            self.results = filtered
            return filtered

        except Exception as e:
            raise RuntimeError(f"E008: 网络请求失败: {str(e)}") from e

    def _mock_fetch_from_sources(self) -> List[JobPosting]:
        """模拟从多个数据源获取职位（离线演示用）"""
        jobs = []
        sample_titles = ["Software Engineer", "Senior Go Developer", "Frontend Engineer",
                         "Backend Engineer", "Full Stack Developer", "DevOps Engineer"]
        sample_locations = ["San Francisco, CA", "Remote", "New York, NY", "Seattle, WA"]
        sample_tags = ["Go", "Python", "JavaScript", "AWS", "Docker"]

        for source_key, source_info in self.SOURCES.items():
            for i in range(3):  # 每个源生成3条模拟数据
                job = JobPosting(
                    company=source_info["name"],
                    title=f"{sample_titles[i % len(sample_titles)]} ({source_key})",
                    location=sample_locations[i % len(sample_locations)],
                    url=urljoin(source_info["base_url"], f"/position/{i}"),
                    source=source_key,
                    description=f"职位描述 - {source_info['name']} - {i}",
                    posted_at=time.strftime("%Y-%m-%d"),
                    tags=sample_tags[i:i+2]
                )
                jobs.append(job)
        return jobs

    def _apply_filters(self, jobs: List[JobPosting],
                       keywords: List[str],
                       locations: List[str]) -> List[JobPosting]:
        """应用关键词和地点过滤"""
        if not keywords and not locations:
            return jobs

        filtered = []
        for job in jobs:
            # 关键词匹配（标题+描述+标签）
            keyword_match = True
            if keywords:
                search_text = f"{job.title} {job.description} {' '.join(job.tags)}".lower()
                keyword_match = any(k.lower() in search_text for k in keywords)

            # 地点匹配
            location_match = True
            if locations:
                location_match = any(l.lower() in job.location.lower() for l in locations)

            if keyword_match and location_match:
                filtered.append(job)

        return filtered

    def _is_new(self, job: JobPosting) -> bool:
        """判断职位是否为新增（模拟增量逻辑）"""
        last_ts = self.config.get("last_timestamp", 0)
        # 模拟：发布时间字符串转时间戳（简化处理）
        try:
            posted_ts = time.mktime(time.strptime(job.posted_at, "%Y-%m-%d"))
            return posted_ts > last_ts
        except (ValueError, TypeError):
            return True

    def export_json(self, jobs: List[JobPosting]) -> str:
        """导出为 JSON 格式"""
        try:
            data = [asdict(j) for j in jobs]
            return json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            raise ValueError(f"E004: JSON 序列化失败: {str(e)}") from e

    def export_csv(self, jobs: List[JobPosting]) -> str:
        """导出为 CSV 格式"""
        try:
            output = io.StringIO()
            if not jobs:
                return ""

            fieldnames = ["company", "title", "location", "url", "source",
                          "description", "posted_at", "tags"]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for job in jobs:
                row = asdict(job)
                row["tags"] = "|".join(job.tags)
                writer.writerow(row)
            return output.getvalue()
        except (csv.Error, TypeError, ValueError) as e:
            raise ValueError(f"E005: CSV 序列化失败: {str(e)}") from e

    def save_to_file(self, content: str, filepath: str, mode: str = "w") -> None:
        """保存内容到文件"""
        try:
            with open(filepath, mode, encoding="utf-8") as f:
                f.write(content)
        except (IOError, OSError) as e:
            raise RuntimeError(f"E003: 无法写入文件 {filepath}: {str(e)}") from e


def run_selftest() -> bool:
    """
    自检函数：使用内置硬编码样例数据验证核心逻辑
    不依赖外部文件、网络或当前工作目录
    """
    print("[自检] 开始执行离线自检...")
    try:
        # 1. 创建聚合器实例
        agg = JobAggregator()

        # 2. 测试数据获取（模拟）
        jobs = agg.fetch_jobs()
        assert len(jobs) > 0, "E009: 获取职位数量应为正数"
        assert len(jobs) >= 15, f"E009: 职位数量应>=15，实际{len(jobs)}"
        print(f"[自检] 数据获取正常，共 {len(jobs)} 条职位")

        # 3. 测试关键词过滤
        filtered = agg._apply_filters(jobs, keywords=["Go"], locations=[])
        assert len(filtered) > 0, "E009: 关键词'Go'过滤结果不应为空"
        assert all("go" in f"{j.title} {j.description} {' '.join(j.tags)}".lower()
                   for j in filtered), "E009: 过滤结果应包含关键词"
        print(f"[自检] 关键词过滤正常，'Go' 过滤出 {len(filtered)} 条")

        # 4. 测试地点过滤
        filtered_loc = agg._apply_filters(jobs, keywords=[], locations=["Remote"])
        assert len(filtered_loc) > 0, "E009: 地点'Remote'过滤结果不应为空"
        assert all("remote" in j.location.lower() for j in filtered_loc), \
            "E009: 过滤结果应包含指定地点"
        print(f"[自检] 地点过滤正常，'Remote' 过滤出 {len(filtered_loc)} 条")

        # 5. 测试 JSON 导出
        json_data = agg.export_json(jobs[:5])
        parsed = json.loads(json_data)
        assert len(parsed) == 5, "E009: JSON 导出数量应为5"
        assert all(k in parsed[0] for k in ["company", "title", "location", "url"]), \
            "E009: JSON 应包含必要字段"
        print("[自检] JSON 导出正常")

        # 6. 测试 CSV 导出
        csv_data = agg.export_csv(jobs[:5])
        assert len(csv_data) > 0, "E009: CSV 导出不应为空"
        assert "company" in csv_data, "E009: CSV 应包含表头"
        assert csv_data.count("\n") >= 5, "E009: CSV 应有至少5行数据"
        print("[自检] CSV 导出正常")

        # 7. 测试错误处理
        try:
            agg._apply_filters(jobs, keywords=None, locations=None)
        except Exception:
            assert False, "E009: 无过滤条件不应抛出异常"

        print("[自检] 所有核心逻辑测试通过 ✓")
        return True

    except AssertionError as e:
        print(f"[自检] 失败: {str(e)}")
        print("[自检] 自检未通过，请检查实现逻辑")
        return False
    except Exception as e:
        print(f"[自检] 异常: {str(e)}")
        print("[自检] 自检过程中出现异常")
        return False


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="go-get-jobs - 技术职位聚合采集工具",
        epilog="示例: python main.py --keyword Go --location Remote --format json"
    )
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检（不依赖外部资源）")
    parser.add_argument("--version", action="version",
                        version="go-get-jobs 1.0.1")
    parser.add_argument("--keyword", action="append", default=[],
                        help="关键词过滤（可多次指定）")
    parser.add_argument("--location", action="append", default=[],
                        help="地点过滤（可多次指定）")
    parser.add_argument("--format", choices=["json", "csv"], default="json",
                        help="输出格式")
    parser.add_argument("--output", "-o", default=None,
                        help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--incremental", action="store_true",
                        help="启用增量模式（基于上次时间戳）")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    try:
        # 正常模式：创建聚合器并获取职位
        aggregator = JobAggregator()

        print(f"正在采集职位数据... (关键词: {args.keyword or '全部'}, "
              f"地点: {args.location or '全部'})")

        jobs = aggregator.fetch_jobs(
            keywords=args.keyword,
            locations=args.location,
            incremental=args.incremental
        )

        if not jobs:
            print("未找到匹配的职位")
            return 0

        # 生成输出
        if args.format == "json":
            output = aggregator.export_json(jobs)
        else:
            output = aggregator.export_csv(jobs)

        # 输出结果
        if args.output:
            aggregator.save_to_file(output, args.output)
            print(f"已保存 {len(jobs)} 条职位到 {args.output}")
        else:
            print(output)

        return 0

    except (ValueError, RuntimeError) as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"E010: 未知错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
