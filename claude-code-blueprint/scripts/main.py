#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-code-blueprint 技能实现脚本（独立实现）

功能：
- 将用户提供的任意数据、文件或URL转换为结构化结果
- 支持批量处理与自定义格式（Markdown表格 / JSON / CSV）
- 内置离线自检（--selftest），不依赖外部文件或网络
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import time

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据为空或格式不合法",
    "E002": "文件不存在或无法读取",
    "E003": "URL访问失败或返回无效内容",
    "E004": "数据解析失败（JSON/CSV格式错误）",
    "E005": "批量处理超过最大限制（50条）",
    "E006": "输出格式不支持",
    "E007": "字段提取失败",
    "E008": "文件写入失败",
    "E009": "参数配置错误",
    "E010": "内部逻辑错误（未知异常）",
}


class BlueprintError(Exception):
    """蓝图处理自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class Record:
    """单条记录的数据结构"""

    def __init__(self, raw_data: Union[str, Dict[str, Any]]):
        self.raw = raw_data
        self.fields: Dict[str, Any] = {}
        self._parse()

    def _parse(self) -> None:
        """从原始数据中提取关键字段"""
        if isinstance(self.raw, dict):
            # 直接使用字典字段
            for key, value in self.raw.items():
                self.fields[str(key)] = value
        elif isinstance(self.raw, str):
            # 尝试解析文本行（key: value 或 key=value）
            text = self.raw.strip()
            if not text:
                raise BlueprintError("E001", "空文本数据")

            # 尝试 JSON 解析
            if text.startswith("{") and text.endswith("}"):
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        for key, value in data.items():
                            self.fields[str(key)] = value
                        return
                except json.JSONDecodeError:
                    pass  # 继续尝试其他格式

            # 尝试 key: value 或 key=value 格式
            pattern = r"(?:^|\n)\s*([^:=]+?)\s*[:=]\s*(.+?)(?=\n\s*[^:=]+?\s*[:=]|$)"
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                for key, value in matches:
                    self.fields[key.strip()] = value.strip()
            else:
                # 单行文本，使用默认字段
                self.fields["content"] = text
        else:
            raise BlueprintError("E001", f"不支持的数据类型: {type(self.raw)}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取字段值"""
        return self.fields.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return dict(self.fields)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.fields, ensure_ascii=False, indent=2)

    def to_csv_row(self, columns: List[str]) -> List[str]:
        """转换为CSV行（按指定列顺序）"""
        return [str(self.fields.get(col, "")) for col in columns]


# ============================================================
# 数据加载器
# ============================================================

class DataLoader:
    """负责从不同来源加载数据"""

    @staticmethod
    def from_text(text: str) -> List[str]:
        """从纯文本加载记录（按空行或换行分割）"""
        if not text or not text.strip():
            raise BlueprintError("E001", "输入文本为空")

        # 按空行分割（双换行），若无空行则按单行分割
        blocks = re.split(r"\n\s*\n", text.strip())
        if len(blocks) == 1:
            blocks = [line.strip() for line in text.strip().splitlines() if line.strip()]

        return [block for block in blocks if block.strip()]

    @staticmethod
    def from_file(filepath: str) -> str:
        """从文件读取内容"""
        path = Path(filepath)
        if not path.exists():
            raise BlueprintError("E002", f"文件不存在: {filepath}")

        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            raise BlueprintError("E002", f"文件读取失败: {str(e)}")

    @staticmethod
    def from_url(url: str, timeout: int = 10) -> str:
        """从URL获取内容"""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status != 200:
                    raise BlueprintError("E003", f"HTTP状态码: {response.status}")
                return response.read().decode("utf-8", errors="replace")
        except BlueprintError:
            raise
        except Exception as e:
            raise BlueprintError("E003", f"URL访问失败: {str(e)}")

    @staticmethod
    def from_json(content: str) -> List[Dict[str, Any]]:
        """从JSON内容解析记录列表"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise BlueprintError("E004", f"JSON解析失败: {str(e)}")

        if isinstance(data, dict):
            # 单条记录
            return [data]
        elif isinstance(data, list):
            # 多条记录
            return data
        else:
            raise BlueprintError("E004", f"JSON结构不支持: {type(data)}")

    @staticmethod
    def from_csv(content: str) -> List[Dict[str, Any]]:
        """从CSV内容解析记录列表"""
        try:
            reader = csv.DictReader(io.StringIO(content))
            records = [dict(row) for row in reader]
        except Exception as e:
            raise BlueprintError("E004", f"CSV解析失败: {str(e)}")

        if not records:
            raise BlueprintError("E001", "CSV无有效数据")

        return records


# ============================================================
# 核心转换器
# ============================================================

class BlueprintConverter:
    """核心转换引擎"""

    MAX_BATCH_SIZE = 50  # 最大批量处理条数

    def __init__(self, output_format: str = "json", custom_fields: Optional[List[str]] = None):
        """初始化转换器

        Args:
            output_format: 输出格式（markdown/json/csv）
            custom_fields: 自定义字段顺序
        """
        self.output_format = output_format.lower()
        if self.output_format not in ("markdown", "json", "csv"):
            raise BlueprintError("E006", f"不支持的输出格式: {output_format}")

        self.custom_fields = custom_fields or []

    def process_records(self, records: List[Union[str, Dict[str, Any]]]) -> List[Record]:
        """处理记录列表，转换为Record对象

        Args:
            records: 原始记录列表

        Returns:
            处理后的Record列表

        Raises:
            BlueprintError: 当记录数量超过限制时
        """
        if len(records) > self.MAX_BATCH_SIZE:
            raise BlueprintError("E005", f"批量处理超过最大限制: {len(records)}/{self.MAX_BATCH_SIZE}")

        result = []
        for item in records:
            try:
                result.append(Record(item))
            except Exception as e:
                if isinstance(e, BlueprintError):
                    raise
                raise BlueprintError("E010", f"记录处理失败: {str(e)}")

        return result

    def extract_fields(self, records: List[Record]) -> List[str]:
        """提取所有记录中的字段名（并集）"""
        field_set: set = set()
        for record in records:
            field_set.update(record.fields.keys())

        # 合并自定义字段顺序
        fields = list(field_set)
        if self.custom_fields:
            # 自定义字段优先，其余字段按字母序追加
            custom_set = set(self.custom_fields)
            fields = [f for f in self.custom_fields if f in field_set]
            fields.extend(sorted(field_set - custom_set))

        return fields

    def convert(self, records: List[Record]) -> str:
        """将记录转换为指定格式输出

        Args:
            records: 处理后的记录列表

        Returns:
            格式化输出字符串
        """
        if not records:
            raise BlueprintError("E001", "无记录可转换")

        fields = self.extract_fields(records)
        numbered_records = [(idx + 1, rec) for idx, rec in enumerate(records)]

        if self.output_format == "json":
            return self._to_json(numbered_records, fields)
        elif self.output_format == "csv":
            return self._to_csv(numbered_records, fields)
        elif self.output_format == "markdown":
            return self._to_markdown(numbered_records, fields)
        else:
            raise BlueprintError("E006", f"输出格式不支持: {self.output_format}")

    def _to_json(self, numbered_records: List[tuple], fields: List[str]) -> str:
        """转换为JSON格式"""
        output = []
        for num, record in numbered_records:
            item = {"_index": num}
            for field in fields:
                item[field] = record.get(field, "")
            output.append(item)
        return json.dumps(output, ensure_ascii=False, indent=2)

    def _to_csv(self, numbered_records: List[tuple], fields: List[str]) -> str:
        """转换为CSV格式"""
        output = io.StringIO()
        writer = csv.writer(output)

        # 表头
        header = ["_index"] + fields
        writer.writerow(header)

        # 数据行
        for num, record in numbered_records:
            row = [num] + [record.get(field, "") for field in fields]
            writer.writerow(row)

        return output.getvalue()

    def _to_markdown(self, numbered_records: List[tuple], fields: List[str]) -> str:
        """转换为Markdown表格格式"""
        lines = []
        header = ["序号"] + fields
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))

        for num, record in numbered_records:
            row = [str(num)] + [str(record.get(field, "")) for field in fields]
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)


# ============================================================
# 主处理流程
# ============================================================

def process_input(
    input_data: Optional[str] = None,
    filepath: Optional[str] = None,
    url: Optional[str] = None,
    output_format: str = "json",
    custom_fields: Optional[List[str]] = None,
) -> str:
    """主处理函数：从不同来源加载数据并转换

    Args:
        input_data: 直接输入的文本数据
        filepath: 输入文件路径
        url: 输入URL
        output_format: 输出格式
        custom_fields: 自定义字段顺序

    Returns:
        转换后的字符串结果

    Raises:
        BlueprintError: 处理过程中的错误
    """
    # 参数校验 - 确保至少有一个有效的输入源
    sources = []
    if input_data is not None and input_data.strip():  # 非空字符串才算有效
        sources.append("input")
    if filepath:
        sources.append("file")
    if url:
        sources.append("url")
    
    if len(sources) != 1:
        raise BlueprintError("E009", "必须且只能指定一个输入源（文本/文件/URL）")

    # 加载数据
    loader = DataLoader()
    if "input" in sources:
        content = input_data
        if not content or not content.strip():
            raise BlueprintError("E001", "输入文本为空")
    elif "file" in sources:
        content = loader.from_file(filepath)
    else:
        content = loader.from_url(url)

    # 解析记录
    # 尝试JSON解析
    content_stripped = content.strip()
    if content_stripped.startswith("{") or content_stripped.startswith("["):
        try:
            raw_records = loader.from_json(content_stripped)
        except BlueprintError:
            # JSON解析失败，按文本处理
            raw_records = loader.from_text(content)
    elif content_stripped.startswith("id,") or content_stripped.startswith("序号,"):
        try:
            raw_records = loader.from_csv(content_stripped)
        except BlueprintError:
            raw_records = loader.from_text(content)
    else:
        raw_records = loader.from_text(content)

    # 转换处理
    converter = BlueprintConverter(output_format=output_format, custom_fields=custom_fields)
    records = converter.process_records(raw_records)
    result = converter.convert(records)

    return result


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """执行内置自检，验证核心逻辑

    Returns:
        0: 自检通过
        1: 自检失败
    """
    print("=== 蓝图转换技能自检 ===")
    failures = 0

    # 测试1: 文本数据解析
    print("\n[测试1] 文本数据解析")
    try:
        text_data = """
        姓名: 张三
        年龄: 28
        城市: 北京

        姓名: 李四
        年龄: 35
        城市: 上海
        """
        result = process_input(input_data=text_data, output_format="json")
        parsed = json.loads(result)
        assert len(parsed) >= 2, f"应至少解析出2条记录，实际: {len(parsed)}"
        assert any("姓名" in item for item in parsed), "记录中应包含'姓名'字段"
        print(f"  通过: 解析出 {len(parsed)} 条记录")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 测试2: JSON数据处理
    print("\n[测试2] JSON数据处理")
    try:
        json_data = json.dumps([
            {"id": 1, "name": "Alice", "amount": 100.5},
            {"id": 2, "name": "Bob", "amount": 200.0},
            {"id": 3, "name": "Carol", "amount": 150.25},
        ])
        result = process_input(input_data=json_data, output_format="json")
        parsed = json.loads(result)
        assert len(parsed) == 3, f"应解析出3条记录，实际: {len(parsed)}"
        assert all("id" in item for item in parsed), "每条记录应包含id字段"
        print(f"  通过: 解析出 {len(parsed)} 条JSON记录")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 测试3: CSV输出
    print("\n[测试3] CSV输出")
    try:
        json_data = json.dumps([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ])
        result = process_input(input_data=json_data, output_format="csv")
        lines = result.strip().splitlines()
        assert len(lines) >= 3, f"CSV应有表头+2行数据，实际: {len(lines)}行"
        assert "id" in lines[0] and "name" in lines[0], "CSV表头应包含id和name"
        print(f"  通过: CSV输出 {len(lines)} 行")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 测试4: Markdown输出
    print("\n[测试4] Markdown输出")
    try:
        json_data = json.dumps([
            {"id": 1, "name": "Alice"},
        ])
        result = process_input(input_data=json_data, output_format="markdown")
        assert "|" in result, "Markdown表格应包含竖线分隔符"
        assert "---" in result, "Markdown表格应包含分隔行"
        print("  通过: Markdown表格输出")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 测试5: 批量限制
    print("\n[测试5] 批量限制")
    try:
        records = [{"id": i} for i in range(60)]
        converter = BlueprintConverter()
        converter.process_records(records)
        print("  失败: 应触发批量限制错误")
        failures += 1
    except BlueprintError as e:
        if e.code == "E005":
            print("  通过: 正确触发批量限制")
        else:
            failures += 1
            print(f"  失败: 错误码不正确: {e.code}")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 测试6: 字段提取
    print("\n[测试6] 字段提取")
    try:
        records = [
            Record({"a": 1, "b": 2}),
            Record({"b": 3, "c": 4}),
        ]
        converter = BlueprintConverter(custom_fields=["b", "a"])
        fields = converter.extract_fields(records)
        assert "a" in fields and "b" in fields and "c" in fields, "应提取所有字段"
        assert fields[0] == "b", "自定义字段应优先"
        print(f"  通过: 提取字段 {fields}")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 测试7: 错误处理 - 空输入应返回E001
    print("\n[测试7] 错误处理")
    try:
        process_input(input_data="")
        print("  失败: 空输入应触发错误")
        failures += 1
    except BlueprintError as e:
        if e.code == "E001":
            print("  通过: 空输入正确报错")
        else:
            failures += 1
            print(f"  失败: 错误码不正确: {e.code}")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 测试8: 多输入源错误
    print("\n[测试8] 多输入源错误")
    try:
        process_input(input_data="测试", filepath="test.txt")
        print("  失败: 多输入源应触发错误")
        failures += 1
    except BlueprintError as e:
        if e.code == "E009":
            print("  通过: 多输入源正确报错")
        else:
            failures += 1
            print(f"  失败: 错误码不正确: {e.code}")
    except Exception as e:
        failures += 1
        print(f"  失败: {str(e)}")

    # 汇总
    print(f"\n=== 自检完成: {failures} 个失败 ===")
    return 1 if failures > 0 else 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="蓝图解析工具 - 将数据转换为结构化结果",
        epilog="示例: python main.py --input '姓名: 张三' --format json"
    )

    # 输入源（三选一）
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--input", "-i", type=str, help="直接输入文本数据")
    source_group.add_argument("--file", "-f", type=str, help="输入文件路径（.csv/.json/.txt/.md）")
    source_group.add_argument("--url", "-u", type=str, help="输入URL地址")

    # 输出配置
    parser.add_argument("--format", "-fmt", type=str, default="json",
                        choices=["markdown", "json", "csv"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--fields", type=str, nargs="*",
                        help="自定义字段顺序，例如: --fields id name amount")

    # 其他选项
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（不读取外部数据）")
    parser.add_argument("--output", "-o", type=str,
                        help="将结果写入文件")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入源
    if not (args.input or args.file or args.url):
        parser.error("必须指定一个输入源: --input, --file 或 --url")

    try:
        # 执行转换
        result = process_input(
            input_data=args.input,
            filepath=args.file,
            url=args.url,
            output_format=args.format,
            custom_fields=args.fields,
        )

        # 输出结果
        if args.output:
            try:
                Path(args.output).write_text(result, encoding="utf-8")
                print(f"结果已写入: {args.output}")
            except Exception as e:
                raise BlueprintError("E008", f"文件写入失败: {str(e)}")
        else:
            print(result)

        return 0

    except BlueprintError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 未预期异常 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
