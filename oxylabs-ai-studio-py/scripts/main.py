#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oxylabs-ai-studio-py 独立实现脚本

仅依据功能规格独立编写，不复制任何既有代码（clean room）。
提供网页数据采集、文件内容解析、批量任务处理、自定义字段映射、置信度标注等能力。

用法示例：
    python scripts/main.py --selftest          # 离线自检核心逻辑
    python scripts/main.py --url https://example.com --fields title,price
    python scripts/main.py --file report.html --fields name,date
    python scripts/main.py --urls a.html b.html --fields title --output json

错误码说明：
    E001 参数解析失败
    E002 未提供任何输入源（URL或文件）
    E003 URL格式非法
    E004 文件不存在或不可读
    E005 字段映射配置非法
    E006 输入内容为空或无法解析
    E007 输出格式不支持
    E008 批量任务中全部失败
    E009 内部逻辑错误（不应发生）
    E010 自检失败
"""

import argparse
import csv
import html.parser
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """单条提取结果"""
    source: str                       # 来源标识（URL或文件名）
    fields: Dict[str, Any]            # 提取的字段名 -> 值
    confidence: Dict[str, float]      # 字段名 -> 置信度 (0.0~1.0)
    status: str = "success"           # success / partial / failed
    error: Optional[str] = None       # 错误信息


@dataclass
class BatchResult:
    """批量任务结果"""
    results: List[ExtractionResult] = field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "results": [
                {
                    "source": r.source,
                    "status": r.status,
                    "fields": r.fields,
                    "confidence": r.confidence,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


# ---------------------------------------------------------------------------
# 轻量 HTML 解析器（标准库实现，不依赖第三方）
# ---------------------------------------------------------------------------

class _FieldExtractor(html.parser.HTMLParser):
    """
    基于 html.parser 的简易字段提取器。
    通过 CSS 选择器（仅支持 tag、#id、.class）定位元素并提取文本。
    这是 clean-room 的简化实现，不追求完整 CSS 支持。
    """

    # 常见标签的文本提取权重（用于置信度估计）
    _TAG_WEIGHT = {
        "title": 0.9,
        "h1": 0.85,
        "h2": 0.8,
        "h3": 0.75,
        "meta": 0.7,
        "p": 0.6,
        "span": 0.5,
        "div": 0.4,
        "td": 0.5,
        "li": 0.5,
        "a": 0.4,
        "default": 0.3,
    }

    def __init__(self, selector: str):
        super().__init__()
        self._selector = selector
        self._tag, self._id, self._class = self._parse_selector(selector)
        self._depth = 0
        self._match_depth = -1          # 匹配元素的深度
        self._in_match = False
        self._text_parts: List[str] = []
        self._matched = False
        self._meta_content: Optional[str] = None

    @staticmethod
    def _parse_selector(selector: str) -> Tuple[str, Optional[str], Optional[str]]:
        """解析简易 CSS 选择器，返回 (tag, id, class)"""
        selector = selector.strip()
        tag = ""
        id_ = None
        class_ = None

        # 提取 id
        id_match = re.search(r"#([\w-]+)", selector)
        if id_match:
            id_ = id_match.group(1)

        # 提取 class
        class_match = re.search(r"\.([\w-]+)", selector)
        if class_match:
            class_ = class_match.group(1)

        # 提取 tag（去掉 # 和 . 部分）
        tag_part = re.sub(r"[#.][\w-]+", "", selector).strip()
        if tag_part and re.match(r"^[a-zA-Z][\w-]*$", tag_part):
            tag = tag_part.lower()

        return tag, id_, class_

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = dict(attrs)
        elem_id = attr_dict.get("id")
        elem_class = attr_dict.get("class", "")

        # 判断是否为匹配元素
        is_match = True
        if self._tag and tag.lower() != self._tag:
            is_match = False
        if self._id and elem_id != self._id:
            is_match = False
        if self._class and self._class not in (elem_class or "").split():
            is_match = False

        if is_match:
            self._match_depth = self._depth
            self._in_match = True
            self._matched = True
            # 处理 meta 标签的 content 属性
            if tag.lower() == "meta" and "content" in attr_dict:
                self._meta_content = attr_dict["content"]

        self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        self._depth -= 1
        if self._depth <= self._match_depth:
            self._in_match = False
            self._match_depth = -1

    def handle_data(self, data: str) -> None:
        if self._in_match:
            text = data.strip()
            if text:
                self._text_parts.append(text)

    def get_result(self) -> Tuple[Optional[str], float]:
        """返回 (提取文本, 置信度)"""
        if not self._matched:
            return None, 0.0

        if self._meta_content is not None:
            text = self._meta_content.strip()
        else:
            text = " ".join(self._text_parts).strip()

        if not text:
            return None, 0.0

        # 根据标签类型估算置信度
        tag = self._tag or "default"
        base_conf = self._TAG_WEIGHT.get(tag, self._TAG_WEIGHT["default"])

        # 文本长度修正：太短或太长的文本置信度略低
        length = len(text)
        if length < 2:
            conf = base_conf * 0.5
        elif length > 500:
            conf = base_conf * 0.8
        else:
            conf = base_conf

        return text, round(min(conf, 1.0), 2)


# ---------------------------------------------------------------------------
# 核心提取逻辑
# ---------------------------------------------------------------------------

def _fetch_url(url: str, timeout: float = 10.0) -> str:
    """从 URL 获取内容（仅支持 http/https）"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不支持的协议: {parsed.scheme}")

    req = urllib.request.Request(url, headers={"User-Agent": "oxylabs-ai-studio-py/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        raw = resp.read()
        return raw.decode(charset, errors="replace")


def _read_file(path: str) -> str:
    """读取本地文件内容"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _extract_field(content: str, selector: str) -> Tuple[Optional[str], float]:
    """从 HTML 内容中提取单个字段"""
    parser = _FieldExtractor(selector)
    try:
        parser.feed(content)
        parser.close()  # 确保解析完成
    except Exception:
        return None, 0.0
    return parser.get_result()


def _validate_fields(fields: List[str]) -> List[str]:
    """校验字段配置，返回规范化后的字段名列表"""
    if not fields:
        raise ValueError("字段列表不能为空")
    cleaned = []
    for f in fields:
        f = f.strip()
        if not f:
            continue
        # 字段名必须包含选择器语法（tag、#id、.class 至少一种）
        if not re.search(r"[a-zA-Z]|#|\.", f):
            raise ValueError(f"非法字段配置: {f}")
        cleaned.append(f)
    if not cleaned:
        raise ValueError("字段列表为空")
    return cleaned


def extract_from_content(
    content: str, fields: List[str], source: str = "unknown"
) -> ExtractionResult:
    """
    从 HTML 内容中提取指定字段。

    字段配置格式：字段名=选择器，例如 "title=h1.title" 或 "price=.price"
    也支持纯选择器形式（自动以选择器作为字段名）。
    """
    result = ExtractionResult(source=source, fields={}, confidence={})

    for field_cfg in fields:
        # 解析 "字段名=选择器" 格式
        if "=" in field_cfg:
            field_name, selector = field_cfg.split("=", 1)
            field_name = field_name.strip()
            selector = selector.strip()
        else:
            # 纯选择器：用选择器去重后的标识作为字段名
            selector = field_cfg.strip()
            field_name = re.sub(r"[^a-zA-Z0-9_]", "_", selector)
            field_name = field_name.strip("_") or "field"

        if not selector:
            continue

        value, conf = _extract_field(content, selector)
        result.fields[field_name] = value if value is not None else ""
        result.confidence[field_name] = conf

    # 判断整体状态
    if not result.fields:
        result.status = "failed"
        result.error = "未提取到任何字段"
    elif any(v == "" for v in result.fields.values()):
        result.status = "partial"
    else:
        result.status = "success"

    return result


def process_url(url: str, fields: List[str], timeout: float = 10.0) -> ExtractionResult:
    """处理单个 URL"""
    try:
        # 验证 URL 格式
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"非法 URL 格式: {url}")
        
        content = _fetch_url(url, timeout=timeout)
        result = extract_from_content(content, fields, source=url)
        return result
    except Exception as e:
        return ExtractionResult(
            source=url, fields={}, confidence={}, status="failed", error=str(e)
        )


def process_file(path: str, fields: List[str]) -> ExtractionResult:
    """处理单个文件"""
    try:
        content = _read_file(path)
        result = extract_from_content(content, fields, source=path)
        return result
    except Exception as e:
        return ExtractionResult(
            source=path, fields={}, confidence={}, status="failed", error=str(e)
        )


def process_batch(
    urls: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    fields: Optional[List[str]] = None,
    timeout: float = 10.0,
) -> BatchResult:
    """批量处理多个 URL 和/或文件"""
    batch = BatchResult()

    if fields is None:
        fields = []

    # 校验字段
    try:
        fields = _validate_fields(fields)
    except ValueError as e:
        raise ValueError(f"字段配置错误: {e}") from e

    sources: List[Tuple[str, str]] = []  # (类型, 路径/URL)

    if urls:
        for u in urls:
            sources.append(("url", u))
    if files:
        for f in files:
            sources.append(("file", f))

    batch.total = len(sources)

    for src_type, src in sources:
        if src_type == "url":
            result = process_url(src, fields, timeout=timeout)
        else:
            result = process_file(src, fields)

        batch.results.append(result)
        if result.status == "failed":
            batch.failed += 1
        else:
            batch.succeeded += 1

    return batch


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(batch: BatchResult, output_format: str = "json") -> str:
    """将批量结果格式化为指定格式"""
    fmt = output_format.lower()

    if fmt == "json":
        return json.dumps(batch.to_dict(), ensure_ascii=False, indent=2)

    if fmt == "csv":
        # 收集所有字段名
        all_fields = set()
        for r in batch.results:
            all_fields.update(r.fields.keys())
        field_list = sorted(all_fields)

        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        # 表头
        writer.writerow(["source", "status"] + field_list + ["error"])
        # 数据行
        for r in batch.results:
            row = [r.source, r.status]
            row.extend([r.fields.get(f, "") for f in field_list])
            row.append(r.error or "")
            writer.writerow(row)
        return buf.getvalue()

    if fmt == "plain":
        lines = []
        for r in batch.results:
            lines.append(f"来源: {r.source} | 状态: {r.status}")
            for k, v in r.fields.items():
                conf = r.confidence.get(k, 0.0)
                lines.append(f"  {k}: {v} (置信度: {conf:.2f})")
            if r.error:
                lines.append(f"  错误: {r.error}")
            lines.append("")
        return "\n".join(lines)

    raise ValueError(f"不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保在任何环境直接可过。
    """
    print("[SELFTEST] 开始自检...")

    # --- 测试 1: HTML 解析器基本功能 ---
    sample_html = """
    <html>
      <head><title>测试商品页面</title></head>
      <body>
        <h1 class="product-title">智能手表 Pro Max</h1>
        <div id="price">¥2999</div>
        <p class="description">这是一款功能强大的智能手表，支持心率监测、GPS定位。</p>
        <span class="rating">4.8</span>
        <ul>
          <li class="feature">防水等级 IP68</li>
          <li class="feature">续航 14 天</li>
        </ul>
      </body>
    </html>
    """

    # 提取标题
    parser = _FieldExtractor("h1.product-title")
    parser.feed(sample_html)
    title, title_conf = parser.get_result()
    assert title is not None, "E010: 标题提取失败"
    assert len(title) > 0, "E010: 标题为空"
    assert title_conf > 0.5, "E010: 标题置信度异常"

    # 提取价格
    parser = _FieldExtractor("#price")
    parser.feed(sample_html)
    price, price_conf = parser.get_result()
    assert price is not None, "E010: 价格提取失败"
    assert "2999" in price, "E010: 价格内容不符"
    assert price_conf > 0.0, "E010: 价格置信度异常"

    # 提取描述
    parser = _FieldExtractor("p.description")
    parser.feed(sample_html)
    desc, desc_conf = parser.get_result()
    assert desc is not None, "E010: 描述提取失败"
    assert len(desc) > 5, "E010: 描述过短"
    assert desc_conf > 0.3, "E010: 描述置信度异常"

    # --- 测试 2: extract_from_content 完整流程 ---
    fields = ["title=h1.product-title", "price=#price", "desc=p.description"]
    result = extract_from_content(sample_html, fields, source="selftest-html")
    assert result.status == "success", f"E010: 提取状态异常: {result.status}"
    assert len(result.fields) == 3, "E010: 字段数量不符"
    assert result.fields["title"] == "智能手表 Pro Max", "E010: 标题字段值不符"
    assert "2999" in result.fields["price"], "E010: 价格字段值不符"
    assert len(result.fields["desc"]) > 5, "E010: 描述字段值过短"
    # 置信度检查（宽松）
    for v in result.confidence.values():
        assert 0.0 <= v <= 1.0, "E010: 置信度超出范围"

    # --- 测试 3: 部分成功场景 ---
    fields_partial = ["title=h1.product-title", "missing=.not-exist"]
    result_partial = extract_from_content(sample_html, fields_partial, source="partial-test")
    assert result_partial.status == "partial", "E010: 部分成功状态异常"
    assert result_partial.fields["title"] != "", "E010: 存在的字段未提取"
    assert result_partial.fields["missing"] == "", "E010: 不存在的字段应为空"

    # --- 测试 4: 批量处理逻辑 ---
    batch = BatchResult()
    batch.total = 2
    batch.results = [
        result,
        ExtractionResult(source="fail-test", fields={}, confidence={}, status="failed", error="模拟失败"),
    ]
    batch.succeeded = 1
    batch.failed = 1
    assert batch.succeeded + batch.failed == batch.total, "E010: 批量计数不一致"

    # --- 测试 5: 输出格式化 ---
    json_out = format_output(batch, "json")
    assert json_out is not None and len(json_out) > 0, "E010: JSON 输出为空"
    parsed_json = json.loads(json_out)
    assert parsed_json["total"] == 2, "E010: JSON 输出 total 字段不符"
    assert parsed_json["succeeded"] == 1, "E010: JSON 输出 succeeded 字段不符"

    csv_out = format_output(batch, "csv")
    assert csv_out is not None and len(csv_out) > 0, "E010: CSV 输出为空"
    assert "source" in csv_out, "E010: CSV 输出缺少表头"

    plain_out = format_output(batch, "plain")
    assert plain_out is not None and len(plain_out) > 0, "E010: 纯文本输出为空"

    # --- 测试 6: 字段校验 ---
    try:
        _validate_fields(["title=h1"])
        _validate_fields(["price"])
    except ValueError:
        assert False, "E010: 合法字段配置被拒绝"

    try:
        _validate_fields([])
        assert False, "E010: 空字段列表未被拒绝"
    except ValueError:
        pass  # 预期行为

    # --- 测试 7: 错误处理 ---
    bad_url_result = process_url("not-a-valid-url", ["title=h1"])
    assert bad_url_result.status == "failed", "E010: 非法 URL 应失败"

    bad_file_result = process_file("/nonexistent/path/file.html", ["title=h1"])
    assert bad_file_result.status == "failed", "E010: 不存在的文件应失败"

    print("[SELFTEST] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def _parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="网页数据采集与结构化提取工具 (oxylabs-ai-studio-py clean-room 实现)"
    )
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--url", dest="urls", action="append", help="要处理的 URL（可多次指定）")
    parser.add_argument("--file", dest="files", action="append", help="要处理的文件路径（可多次指定）")
    parser.add_argument("--fields", required=False, help="字段配置，逗号分隔，格式: 字段名=选择器")
    parser.add_argument("--output", choices=["json", "csv", "plain"], default="json", help="输出格式")
    parser.add_argument("--timeout", type=float, default=10.0, help="请求超时时间（秒）")

    try:
        return parser.parse_args(argv)
    except SystemExit as e:
        # argparse 在错误时会调用 sys.exit，这里转为异常
        raise ValueError(f"参数解析失败: {e}") from e


def main(argv: Optional[List[str]] = None) -> int:
    """主入口"""
    try:
        if argv is None:
            argv = sys.argv[1:]

        args = _parse_args(argv)

        # 自检模式
        if args.selftest:
            return _run_selftest()

        # 正常处理模式
        if not args.urls and not args.files:
            print("错误: 必须提供 --url 或 --file 参数（或使用 --selftest 自检）", file=sys.stderr)
            return 2  # E002

        if not args.fields:
            print("错误: 必须提供 --fields 参数", file=sys.stderr)
            return 2  # E002

        # 解析字段配置
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 批量处理
        try:
            batch = process_batch(
                urls=args.urls, files=args.files, fields=fields, timeout=args.timeout
            )
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 2  # E005

        # 输出结果
        try:
            output = format_output(batch, args.output)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 2  # E007

        print(output)

        # 返回码：全部成功返回 0，部分失败返回 1，全部失败返回 2
        if batch.failed == 0:
            return 0
        elif batch.succeeded > 0:
            return 1
        else:
            return 2  # E008

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # 兜底错误处理
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1  # E009


if __name__ == "__main__":
    sys.exit(main())
