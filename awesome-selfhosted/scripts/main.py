#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
自托管服务资源导航信息整理工具（awesome-selfhosted）
仅依据功能规格独立实现（clean-room），不复制任何既有代码。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义（E001-E010）
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

    def process(self, content: str, input_format: str = "auto",
                output_format: str = "markdown", group_by: str = "none") -> str:
        """处理输入内容并返回格式化结果"""
        try:
            records = self.parser.parse(content, input_format)
            return self.formatter.format(records, output_format, group_by)
        except ValueError as e:
            error_code = str(e)
            if error_code in ERROR_CODES:
                raise ValueError(f"{error_code}: {ERROR_CODES[error_code]}")
            raise


def run_selftest() -> bool:
    """内置硬编码样例数据的离线自检"""
    print("开始自检 (self-test)...")

    # 硬编码测试数据（不依赖任何外部文件）
    test_text = """Nextcloud | https://github.com/nextcloud/server | 自托管云存储与文件同步 | Docker
Gitea | https://github.com/go-gitea/gitea | 轻量级Git代码托管 | Docker
Bitwarden | https://github.com/bitwarden/server | 密码管理器 | Docker"""

    test_json = json.dumps({
        "records": [
            {"name": "MinIO", "url": "https://github.com/minio/minio",
             "description": "高性能对象存储服务", "deploy": "Docker", "tags": ["存储", "对象存储"]},
            {"name": "Grafana", "url": "https://github.com/grafana/grafana",
             "description": "数据可视化与监控分析平台", "deploy": "Docker", "tags": ["监控", "可视化"]},
        ]
    })

    test_csv = "name,url,description,deploy,tags\n" \
               "Nginx,https://nginx.org,Web服务器与反向代理,Docker,web;代理\n" \
               "Postgres,https://www.postgresql.org,关系型数据库,裸机,数据库"

    processor = SelfHostedProcessor()

    # 测试文本解析
    try:
        records = processor.parser.parse(test_text, "text")
        assert len(records) == 3, f"文本解析失败: 期望3条记录，实际{len(records)}条"
        assert all(r.name for r in records), "记录缺少名称"
        assert all(r.url.startswith("http") for r in records), "记录URL格式错误"
        print(f"  [PASS] 文本解析: {len(records)}条记录")

        # 测试提取
        deploy = InfoExtractor.extract_deploy(records[0])
        assert deploy in ["Docker", "Kubernetes", "裸机", "未知"], f"部署方式提取异常: {deploy}"
        print(f"  [PASS] 部署方式提取: {deploy}")

        tags = InfoExtractor.extract_tags(records[0])
        assert isinstance(tags, list), "标签应为列表"
        print(f"  [PASS] 功能标签提取: {tags if tags else '无'}")

        # 测试输出
        md_output = OutputFormatter.format_markdown(records)
        assert "| 服务名称" in md_output, "Markdown表格头缺失"
        assert "Nextcloud" in md_output, "Markdown输出缺少记录内容"
        print("  [PASS] Markdown输出")

        json_output = OutputFormatter.format_json(records)
        json_data = json.loads(json_output)
        assert json_data["count"] == 3, "JSON输出条数错误"
        assert len(json_data["records"]) == 3, "JSON记录数错误"
        print("  [PASS] JSON输出")

        csv_output = OutputFormatter.format_csv(records)
        assert "name,url" in csv_output, "CSV表头错误"
        assert "Nextcloud" in csv_output, "CSV输出缺少记录内容"
        print("  [PASS] CSV输出")

    except AssertionError as e:
        print(f"  [FAIL] 自检失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 自检异常: {e}")
        return False

    # 测试JSON解析
    try:
        records = processor.parser.parse(test_json, "json")
        assert len(records) == 2, f"JSON解析失败: 期望2条记录，实际{len(records)}条"
        assert records[0].name == "MinIO", "JSON记录名称错误"
        assert records[0].tags, "JSON记录标签缺失"
        print(f"  [PASS] JSON解析: {len(records)}条记录")
    except AssertionError as e:
        print(f"  [FAIL] 自检失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 自检异常: {e}")
        return False

    # 测试CSV解析
    try:
        records = processor.parser.parse(test_csv, "csv")
        assert len(records) == 2, f"CSV解析失败: 期望2条记录，实际{len(records)}条"
        assert records[0].name == "Nginx", "CSV记录名称错误"
        print(f"  [PASS] CSV解析: {len(records)}条记录")
    except AssertionError as e:
        print(f"  [FAIL] 自检失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 自检异常: {e}")
        return False

    # 测试分组输出
    try:
        records = processor.parser.parse(test_text, "text")
        grouped = OutputFormatter.format_markdown(records, group_by="deploy")
        assert "## Docker" in grouped, "按部署方式分组失败"
        print("  [PASS] 按部署方式分组")

        grouped = OutputFormatter.format_markdown(records, group_by="tag")
        assert grouped.strip(), "按标签分组输出为空"
        print("  [PASS] 按标签分组")
    except AssertionError as e:
        print(f"  [FAIL] 自检失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] 自检异常: {e}")
        return False

    # 测试错误处理
    try:
        processor.parser.parse("", "text")
        print("  [FAIL] 空输入未抛出异常")
        return False
    except ValueError as e:
        assert "E001" in str(e), f"空输入错误码错误: {e}"
        print("  [PASS] 空输入错误处理")

    try:
        processor.parser.parse("item1 | https://example.com\n" * 101, "text")
        print("  [FAIL] 超量输入未抛出异常")
        return False
    except ValueError as e:
        assert "E003" in str(e), f"超量输入错误码错误: {e}"
        print("  [PASS] 超量输入错误处理")

    print("自检全部通过 ✅")
    return True


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="自托管服务资源导航信息整理工具",
        epilog="示例: python main.py -i input.txt -f markdown -g deploy"
    )
    parser.add_argument("-i", "--input", help="输入文件路径（.txt/.md/.csv/.json）")
    parser.add_argument("-c", "--content", help="直接输入内容字符串")
    parser.add_argument("-f", "--format", choices=["markdown", "json", "csv"],
                        default="markdown", help="输出格式")
    parser.add_argument("-g", "--group", choices=["none", "deploy", "tag"],
                        default="none", help="分组方式")
    parser.add_argument("--input-format", choices=["auto", "text", "json", "csv"],
                        default="auto", help="输入格式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("-o", "--output", help="输出文件路径")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 参数校验
    if not args.input and not args.content:
        parser.error("必须提供 --input 或 --content 参数")
        sys.exit(1)

    # 读取输入
    try:
        if args.content:
            content = args.content
        else:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()
    except FileNotFoundError:
        print(f"E010: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E010: 读取输入失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 处理
    try:
        processor = SelfHostedProcessor()
        result = processor.process(
            content,
            input_format=args.input_format,
            output_format=args.format,
            group_by=args.group,
        )
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 输出
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
        except Exception as e:
            print(f"E010: 写入输出文件失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(result)


if __name__ == "__main__":
    main()
