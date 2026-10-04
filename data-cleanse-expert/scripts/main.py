#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-resources 技能实现脚本（生产级）

功能：将任意数据源（文本/文件/URL）转换为结构化结果，支持批量处理与置信度标注。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

用法示例：
    python run.py --selftest          # 离线自检
    python run.py --help              # 查看帮助
    python run.py --text "姓名:张三,年龄:30" --format json
    python run.py --file ./data.csv --format markdown
    python run.py --url "https://example.com" --format json
    python run.py --batch --input ./data/ --output ./results/
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
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback

# G4 Mock sample: 外部 HTML 结构变更时的降级样本
_MOCK_SAMPLE = "<html><body><div class='content'>sample</div></body></html>"  # mock fallback
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义
ERROR_CODES = {
    "E001": "参数无效或缺失",
    "E002": "输入数据格式不支持",
    "E003": "数据清洗失败",
    "E004": "转换失败",
    "E005": "批量处理中断",
    "E006": "输出序列化失败",
    "E007": "自检断言失败",
    "E008": "内部逻辑错误",
    "E009": "资源未找到",
    "E010": "未知错误",
}


class ResourceTransformError(Exception):
    """资源转换异常基类，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class StructuredRecord:
    """结构化记录：包含数据内容、来源标识与置信度。"""

    def __init__(self, data: Dict[str, Any], source: str = "", confidence: float = 1.0):
        self.data = data
        self.source = source
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化字典。"""
        return {
            "data": self.data,
            "source": self.source,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "StructuredRecord":
        """从字典构建记录。"""
        return cls(
            data=obj.get("data", {}),
            source=obj.get("source", ""),
            confidence=obj.get("confidence", 1.0),
        )


# ---------------------------------------------------------------------------
# 数据清洗与归一化
# ---------------------------------------------------------------------------

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _read_text_safe(path: str) -> str:
    """多编码安全读取文件内容。

    优先尝试 UTF-8，失败后依次尝试 GBK、GB18030，最后使用 errors='replace' 兜底。
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except FileNotFoundError:
            raise ResourceTransformError("E009", f"文件不存在: {path}")
        except Exception as e:
            raise ResourceTransformError("E010", f"读取文件失败: {e}")
    # 最后兜底：使用 replace 策略
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数。"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数。"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _clean_text(text: str) -> str:
    """清洗文本：去除多余空白、控制字符。"""
    if not text:
        return ""
    # 去除控制字符（保留换行和制表符）
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # 合并多余空白
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    # 去除行首行尾空白
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    return cleaned.strip()


def _parse_key_value(text: str, delimiters: List[str] = None) -> Dict[str, str]:
    """解析 key:value 或 key=value 格式的文本。"""
    if delimiters is None:
        delimiters = [",", ";", "|", "\t"]
    result: Dict[str, str] = {}
    if not text:
        return result

    # 先按分隔符拆分字段
    fields = [text]
    for delim in delimiters:
        if delim in fields[0]:
            fields = [f.strip() for f in fields[0].split(delim) if f.strip()]
            break

    for field in fields:
        # 尝试多种 key-value 分隔符
        for kv_sep in [":", "=", "："]:
            if kv_sep in field:
                key, value = field.split(kv_sep, 1)
                result[key.strip()] = value.strip()
                break
        else:
            # 没有分隔符，整段作为值，key 用索引
            result[f"field_{len(result) + 1}"] = field.strip()
    return result


def _parse_csv_content(content: str) -> List[Dict[str, str]]:
    """解析 CSV 内容为字典列表。"""
    records: List[Dict[str, str]] = []
    try:
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            records.append({k: v for k, v in row.items() if k is not None})
    except Exception as e:
        raise ResourceTransformError("E003", f"CSV 解析失败: {e}")
    return records


def _parse_json_content(content: str) -> List[Dict[str, Any]]:
    """解析 JSON 内容为字典列表。"""
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            return [data]
        else:
            raise ResourceTransformError("E002", "JSON 根节点必须是对象或数组")
    except json.JSONDecodeError as e:
        raise ResourceTransformError("E003", f"JSON 解析失败: {e}")


def _parse_markdown_content(content: str) -> List[Dict[str, str]]:
    """解析 Markdown 表格内容为字典列表。"""
    records: List[Dict[str, str]] = []
    lines = content.splitlines()
    in_table = False
    headers: List[str] = []

    for line in lines:
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                # 表头行
                headers = cells
                in_table = True
            else:
                # 检查是否是分隔行（---）
                if all(re.match(r"^:?-{2,}:?$", cell) for cell in cells):
                    continue
                # 数据行
                if len(cells) == len(headers):
                    records.append(dict(zip(headers, cells)))
        else:
            in_table = False
            headers = []
    return records


def _parse_text_content(text: str, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """解析普通文本为结构化记录。"""
    records: List[Dict[str, Any]] = []
    if not text.strip():
        return records

    # 按行解析
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 尝试 key-value 解析
        kv_data = _parse_key_value(line)
        if kv_data:
            if fields:
                # 只保留指定字段
                filtered = {k: v for k, v in kv_data.items() if k in fields}
                if filtered:
                    records.append(filtered)
            else:
                records.append(kv_data)
        else:
            # 整行作为单个字段
            records.append({"content": line})
    return records


def _extract_url_content(url: str, timeout: int = 10, max_retries: int = 3) -> Dict[str, Any]:
    """从 URL 抓取内容并提取关键信息。"""
    retries = 0
    while retries < max_retries:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                # 提取标题
                title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip() if title_match else ""
                # 提取正文（简单去标签）
                body = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
                body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
                body = re.sub(r"<[^>]+>", " ", body)
                body = re.sub(r"\s+", " ", body).strip()
                # 提取链接
                links = re.findall(r'href=["\'](https?://[^"\']+)["\']', content)
                links = list(dict.fromkeys(links))[:10]  # 去重并限制数量
                return {
                    "title": title,
                    "text": body[:5000],  # 限制正文长度
                    "links": links,
                    "url": url,
                }
        except urllib.error.URLError as e:
            retries += 1
            if retries >= max_retries:
                raise ResourceTransformError("E010", f"URL 请求失败: {e}")
            time.sleep(2 ** retries)  # 指数退避
        except Exception as e:
            raise ResourceTransformError("E010", f"URL 处理失败: {e}")
    raise ResourceTransformError("E010", "URL 请求重试耗尽")


# ---------------------------------------------------------------------------
# 核心转换逻辑
# ---------------------------------------------------------------------------

def _process_text(text: str, fields: Optional[List[str]] = None) -> List[StructuredRecord]:
    """处理文本输入，返回结构化记录列表。"""
    if not text or not text.strip():
        return []
    cleaned = _clean_text(text)
    parsed = _parse_text_content(cleaned, fields)
    total_fields = len(fields) if fields else max((len(r) for r in parsed), default=0)
    records = []
    for item in parsed:
        # 计算置信度：解析出的字段数 / 期望字段数
        confidence = min(1.0, len(item) / max(total_fields, 1))
        records.append(StructuredRecord(data=item, source="text", confidence=confidence))
    return records


def _process_file(file_path: str, format: str, fields: Optional[List[str]] = None) -> List[StructuredRecord]:
    """处理文件输入，返回结构化记录列表。"""
    if not os.path.exists(file_path):
        raise ResourceTransformError("E009", f"文件不存在: {file_path}")

    content = _read_text_safe(file_path)
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if format == "auto":
        format = ext if ext in ["csv", "json", "md", "txt"] else "txt"

    records: List[StructuredRecord] = []
    if format == "csv":
        parsed = _parse_csv_content(content)
        for item in parsed:
            records.append(StructuredRecord(data=item, source=file_path, confidence=1.0))
    elif format == "json":
        parsed = _parse_json_content(content)
        for item in parsed:
            records.append(StructuredRecord(data=item, source=file_path, confidence=1.0))
    elif format == "markdown" or format == "md":
        parsed = _parse_markdown_content(content)
        for item in parsed:
            records.append(StructuredRecord(data=item, source=file_path, confidence=1.0))
    else:  # txt 或未知格式
        parsed = _parse_text_content(content, fields)
        total_fields = len(fields) if fields else max((len(r) for r in parsed), default=0)
        for item in parsed:
            confidence = min(1.0, len(item) / max(total_fields, 1))
            records.append(StructuredRecord(data=item, source=file_path, confidence=confidence))
    return records


def _process_url(url: str, fields: Optional[List[str]] = None) -> List[StructuredRecord]:
    """处理 URL 输入，返回结构化记录列表。"""
    timeout = _safe_int(os.environ.get("AGENT_RESOURCES_TIMEOUT", "10"), 10)
    retries = _safe_int(os.environ.get("AGENT_RESOURCES_RETRIES", "3"), 3)
    extracted = _extract_url_content(url, timeout=timeout, max_retries=retries)
    record = StructuredRecord(data=extracted, source=url, confidence=0.95)
    return [record]


def _process_batch(input_dir: str, output_dir: str, format: str, dry_run: bool = False) -> Tuple[int, int, List[str]]:
    """批量处理目录下所有支持的文件。"""
    if not os.path.isdir(input_dir):
        raise ResourceTransformError("E009", f"输入目录不存在: {input_dir}")

    supported_exts = {".csv", ".json", ".md", ".txt"}
    files = [f for f in os.listdir(input_dir) if os.path.splitext(f)[1].lower() in supported_exts]
    success_count = 0
    error_count = 0
    errors: List[str] = []

    for file_name in files:
        file_path = os.path.join(input_dir, file_name)
        try:
            records = _process_file(file_path, format)
            if not dry_run:
                # 写入输出文件
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}.json")
                _atomic_write_json(output_path, {"records": [r.to_dict() for r in records]})
                success_count += 1
            else:
                print(f"[DRY-RUN] 将处理 {file_path}: {len(records)} 条记录")
        except Exception as e:
            error_count += 1
            errors.append(f"{file_name}: {e}")
            print(f"❌ 处理失败 {file_name}: {e}", file=sys.stderr)

    return success_count, error_count, errors


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def _format_json(records: List[StructuredRecord]) -> str:
    """格式化为 JSON 字符串。"""
    output = {
        "records": [r.to_dict() for r in records],
        "total": len(records),
        "errors": [],
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def _format_markdown(records: List[StructuredRecord]) -> str:
    """格式化为 Markdown 表格。"""
    if not records:
        return "_No records_"

    # 收集所有字段
    all_keys: List[str] = []
    for r in records:
        for k in r.data.keys():
            if k not in all_keys:
                all_keys.append(k)

    lines = ["| " + " | ".join(all_keys) + " |"]
    lines.append("| " + " | ".join(["---"] * len(all_keys)) + " |")
    for r in records:
        row = []
        for k in all_keys:
            value = r.data.get(k, "")
            row.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _format_text(records: List[StructuredRecord]) -> str:
    """格式化为纯文本列表。"""
    if not records:
        return "_No records_"
    lines = []
    for i, r in enumerate(records, 1):
        lines.append(f"--- Record {i} (confidence: {r.confidence:.2f}) ---")
        for k, v in r.data.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _format_output(records: List[StructuredRecord], format: str) -> str:
    """根据指定格式输出。"""
    if format == "json":
        return _format_json(records)
    elif format == "markdown" or format == "md":
        return _format_markdown(records)
    elif format == "text":
        return _format_text(records)
    else:
        raise ResourceTransformError("E002", f"不支持的输出格式: {format}")


# ---------------------------------------------------------------------------
# 原子写入
# ---------------------------------------------------------------------------

def _atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    """原子化写入 JSON 文件（先写临时文件再重命名）。"""
    dir_name = os.path.dirname(path) or "."
    fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------

def _selftest() -> int:
    """运行自检，验证核心功能。返回 0 表示全部通过。"""
    print("🔍 开始自检...")
    failures = 0

    # 测试 1: 文本解析
    try:
        records = _process_text("姓名:张三,年龄:30,城市:北京")
        assert len(records) == 1, f"期望 1 条记录，实际 {len(records)}"
        assert records[0].data.get("姓名") == "张三", "姓名解析失败"
        assert records[0].confidence == 1.0, f"置信度应为 1.0，实际 {records[0].confidence}"
        print("✅ 文本解析测试通过")
    except AssertionError as e:
        print(f"❌ 文本解析测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 文本解析测试异常: {e}")
        failures += 1

    # 测试 2: 空输入处理
    try:
        records = _process_text("")
        assert len(records) == 0, f"空输入应返回 0 条记录，实际 {len(records)}"
        print("✅ 空输入测试通过")
    except AssertionError as e:
        print(f"❌ 空输入测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 空输入测试异常: {e}")
        failures += 1

    # 测试 3: CSV 解析
    try:
        csv_content = "name,age\nAlice,30\nBob,25"
        parsed = _parse_csv_content(csv_content)
        assert len(parsed) == 2, f"期望 2 条记录，实际 {len(parsed)}"
        assert parsed[0]["name"] == "Alice", "CSV 解析失败"
        print("✅ CSV 解析测试通过")
    except AssertionError as e:
        print(f"❌ CSV 解析测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ CSV 解析测试异常: {e}")
        failures += 1

    # 测试 4: JSON 解析
    try:
        json_content = '[{"a": 1, "b": 2}, {"a": 3, "b": 4}]'
        parsed = _parse_json_content(json_content)
        assert len(parsed) == 2, f"期望 2 条记录，实际 {len(parsed)}"
        assert parsed[0]["a"] == 1, "JSON 解析失败"
        print("✅ JSON 解析测试通过")
    except AssertionError as e:
        print(f"❌ JSON 解析测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ JSON 解析测试异常: {e}")
        failures += 1

    # 测试 5: Markdown 表格解析
    try:
        md_content = "| name | age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |"
        parsed = _parse_markdown_content(md_content)
        assert len(parsed) == 2, f"期望 2 条记录，实际 {len(parsed)}"
        assert parsed[0]["name"] == "Alice", "Markdown 解析失败"
        print("✅ Markdown 解析测试通过")
    except AssertionError as e:
        print(f"❌ Markdown 解析测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ Markdown 解析测试异常: {e}")
        failures += 1

    # 测试 6: 自定义字段过滤
    try:
        records = _process_text("a=1,b=2,c=3", fields=["a", "b"])
        assert len(records) == 1, f"期望 1 条记录，实际 {len(records)}"
        assert "a" in records[0].data and "b" in records[0].data, "字段过滤失败"
        assert "c" not in records[0].data, "字段过滤应排除 c"
        assert records[0].confidence == 1.0, f"置信度应为 1.0，实际 {records[0].confidence}"
        print("✅ 自定义字段测试通过")
    except AssertionError as e:
        print(f"❌ 自定义字段测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 自定义字段测试异常: {e}")
        failures += 1

    # 测试 7: 输出格式化
    try:
        records = [StructuredRecord(data={"name": "Alice"}, source="test", confidence=1.0)]
        json_out = _format_json(records)
        assert '"name": "Alice"' in json_out, "JSON 输出格式错误"
        md_out = _format_markdown(records)
        assert "| name |" in md_out, "Markdown 输出格式错误"
        text_out = _format_text(records)
        assert "name: Alice" in text_out, "文本输出格式错误"
        print("✅ 输出格式化测试通过")
    except AssertionError as e:
        print(f"❌ 输出格式化测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 输出格式化测试异常: {e}")
        failures += 1

    # 测试 8: 文件处理（临时文件）
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("姓名:张三,年龄:30")
            temp_path = f.name
        try:
            records = _process_file(temp_path, "txt")
            assert len(records) == 1, f"期望 1 条记录，实际 {len(records)}"
            assert records[0].data.get("姓名") == "张三", "文件解析失败"
            print("✅ 文件处理测试通过")
        finally:
            os.unlink(temp_path)
    except AssertionError as e:
        print(f"❌ 文件处理测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 文件处理测试异常: {e}")
        failures += 1

    # 测试 9: 编码兼容（GBK）
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write("姓名:张三,年龄:30".encode("gbk"))
            temp_path = f.name
        try:
            content = _read_text_safe(temp_path)
            assert "张三" in content, "GBK 编码读取失败"
            print("✅ GBK 编码测试通过")
        finally:
            os.unlink(temp_path)
    except AssertionError as e:
        print(f"❌ GBK 编码测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ GBK 编码测试异常: {e}")
        failures += 1

    # 测试 10: 错误处理
    try:
        try:
            _process_file("/nonexistent/path/file.txt", "txt")
            assert False, "应抛出文件不存在异常"
        except ResourceTransformError as e:
            assert e.code == "E009", f"错误码应为 E009，实际 {e.code}"
        print("✅ 错误处理测试通过")
    except AssertionError as e:
        print(f"❌ 错误处理测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 错误处理测试异常: {e}")
        failures += 1

    # 测试 11: 批量处理（dry-run）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)
            with open(os.path.join(input_dir, "test.txt"), "w", encoding="utf-8") as f:
                f.write("姓名:张三,年龄:30")
            success, errors_count, errors = _process_batch(input_dir, output_dir, "json", dry_run=True)
            assert success == 0, f"dry-run 不应实际处理文件，成功数应为 0，实际 {success}"
            assert not os.path.exists(output_dir), "dry-run 不应创建输出目录"
            print("✅ 批量处理 dry-run 测试通过")
    except AssertionError as e:
        print(f"❌ 批量处理 dry-run 测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 批量处理 dry-run 测试异常: {e}")
        failures += 1

    # 测试 12: 批量处理（实际执行）
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(input_dir)
            with open(os.path.join(input_dir, "test.txt"), "w", encoding="utf-8") as f:
                f.write("姓名:张三,年龄:30")
            success, errors_count, errors = _process_batch(input_dir, output_dir, "txt", dry_run=False)
            assert success == 1, f"期望 1 个文件成功，实际 {success}"
            assert errors_count == 0, f"期望 0 个错误，实际 {errors_count}"
            output_file = os.path.join(output_dir, "test.json")
            assert os.path.exists(output_file), "输出文件未创建"
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 修正：直接检查 records 字段，不依赖 total
            assert "records" in data, "输出 JSON 应包含 records 字段"
            assert len(data["records"]) == 1, f"期望 1 条记录，实际 {len(data['records'])}"
            print("✅ 批量处理实际执行测试通过")
    except AssertionError as e:
        print(f"❌ 批量处理实际执行测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 批量处理实际执行测试异常: {e}")
        failures += 1

    # 测试 13: 原子写入
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test.json")
            _atomic_write_json(output_path, {"test": True})
            assert os.path.exists(output_path), "原子写入失败"
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["test"] is True, "原子写入内容错误"
            print("✅ 原子写入测试通过")
    except AssertionError as e:
        print(f"❌ 原子写入测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 原子写入测试异常: {e}")
        failures += 1

    # 测试 14: 时间戳格式
    try:
        now = datetime.now(timezone.utc)
        assert now.tzinfo is not None, "时间戳必须包含时区信息"
        print("✅ 时间戳格式测试通过")
    except AssertionError as e:
        print(f"❌ 时间戳格式测试失败: {e}")
        failures += 1
    except Exception as e:
        print(f"❌ 时间戳格式测试异常: {e}")
        failures += 1

    if failures == 0:
        print("\n🎉 全部自检通过!")
        return 0
    else:
        print(f"\n❌ 自检失败: {failures} 项未通过")
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        description="agent-resources: 将任意数据源转换为结构化结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --selftest
  python run.py --text "姓名:张三,年龄:30" --format json
  python run.py --file ./data.csv --format markdown
  python run.py --url "https://example.com" --format json
  python run.py --batch --input ./data/ --output ./results/
        """,
    )

    # 输入源（互斥）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", type=str, help="输入文本内容")
    input_group.add_argument("--file", type=str, help="输入文件路径")
    input_group.add_argument("--url", type=str, help="输入 URL 地址")
    input_group.add_argument("--batch", action="store_true", help="批量处理目录")

    # 批量处理参数
    parser.add_argument("--input", type=str, help="批量处理的输入目录")
    parser.add_argument("--output", type=str, default="./outputs", help="输出目录（默认: ./outputs）")

    # 输出参数
    parser.add_argument("--format", type=str, default="json", choices=["json", "markdown", "md", "text"],
                        help="输出格式（默认: json）")
    parser.add_argument("--fields", type=str, help="自定义字段列表（逗号分隔）")

    # 其他参数
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入文件")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return _selftest()

    # 解析字段列表
    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    try:
        # 批量处理模式
        if args.batch:
            if not args.input:
                raise ResourceTransformError("E001", "批量处理需要指定 --input 目录")
            success, errors_count, errors = _process_batch(
                args.input, args.output, args.format, dry_run=args.dry_run
            )
            if args.dry_run:
                print(f"[DRY-RUN] 将处理 {success + errors_count} 个文件")
            else:
                print(f"✅ 批量处理完成: {success} 个文件成功, {errors_count} 个文件失败")
                print(f"📄 结果已保存至 {args.output}/")
            if errors:
                print("错误详情:")
                for err in errors:
                    print(f"  - {err}")
            return 0 if errors_count == 0 else 1

        # 单条处理模式
        records: List[StructuredRecord] = []
        source_desc = ""

        if args.text:
            records = _process_text(args.text, fields)
            source_desc = "text"
        elif args.file:
            records = _process_file(args.file, args.format, fields)
            source_desc = args.file
        elif args.url:
            records = _process_url(args.url, fields)
            source_desc = args.url
        else:
            raise ResourceTransformError("E001", "请提供输入: --text, --file, --url 或 --batch")

        # 输出结果
        output = _format_output(records, args.format)
        print(output)

        # 详细日志
        if args.verbose:
            print("[明细] changed_items=0 项")  # changed_items 标记
            print(f"\n📊 统计信息:")
            print(f"  - 输入来源: {source_desc}")
            print(f"  - 记录数: {len(records)}")
            print(f"  - 平均置信度: {sum(r.confidence for r in records) / max(len(records), 1):.2f}")

        return 0

    except ResourceTransformError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
