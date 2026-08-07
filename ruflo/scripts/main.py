#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruflo — 数据流编排与多智能体协同批量转换工具

本脚本依据功能规格独立实现（clean-room），
提供多源数据解析、多智能体任务编排、批量处理与结果合并能力。

用法示例：
    python main.py --parse json --input data.json
    python main.py --pipeline agents.yaml --batch items.csv
    python main.py --selftest
"""

import argparse
import csv
import io
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输入格式不支持",
    "E003": "JSON 解析失败",
    "E004": "CSV 解析失败",
    "E005": "XML 解析失败",
    "E006": "管道配置格式错误",
    "E007": "智能体执行失败",
    "E008": "批量处理失败",
    "E009": "结果合并失败",
    "E010": "未知内部错误",
}


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并以非零状态码退出。"""
    message = ERROR_CODES.get(code, "未知错误")
    if detail:
        message = f"{message}: {detail}"
    print(f"[错误 {code}] {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据解析层：将不同格式的输入解析为统一的结构化数据（列表[Dict]）
# ---------------------------------------------------------------------------

def parse_json(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为结构化记录列表。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        error_exit("E003", str(exc))
    if isinstance(data, list):
        return [item if isinstance(item, dict) else {"value": item} for item in data]
    if isinstance(data, dict):
        return [data]
    return [{"value": data}]


def parse_csv(text: str) -> List[Dict[str, Any]]:
    """解析 CSV 文本为结构化记录列表（首行为表头）。"""
    try:
        reader = csv.DictReader(io.StringIO(text))
        records: List[Dict[str, Any]] = []
        for row in reader:
            if row is None:
                continue
            # 过滤空行
            if any(v.strip() for v in row.values()):
                records.append(dict(row))
        return records
    except Exception as exc:  # 捕获 CSV 解析中的各类异常
        error_exit("E004", str(exc))


def parse_xml(text: str) -> List[Dict[str, Any]]:
    """解析 XML 文本为结构化记录列表（每个子元素为一条记录）。"""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        error_exit("E005", str(exc))
    records: List[Dict[str, Any]] = []

    # 将每个直接子元素转换为字典
    for child in root:
        record: Dict[str, Any] = {}
        for sub in child:
            # 如果有多个同名字段，合并为列表
            if sub.tag in record:
                if not isinstance(record[sub.tag], list):
                    record[sub.tag] = [record[sub.tag]]
                record[sub.tag].append(sub.text or "")
            else:
                record[sub.tag] = sub.text or ""
        if record:
            records.append(record)
    return records


def parse_text(text: str) -> List[Dict[str, Any]]:
    """解析纯文本：按行拆分，每行作为一条记录。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [{"line": line} for line in lines]


# 格式注册表
PARSERS: Dict[str, Callable[[str], List[Dict[str, Any]]]] = {
    "json": parse_json,
    "csv": parse_csv,
    "xml": parse_xml,
    "txt": parse_text,
    "text": parse_text,
}


def parse_input(data: str, fmt: str) -> List[Dict[str, Any]]:
    """根据指定格式解析输入数据。"""
    parser = PARSERS.get(fmt.lower())
    if parser is None:
        error_exit("E002", f"不支持的格式: {fmt}")
    return parser(data)


# ---------------------------------------------------------------------------
# 多智能体编排层：定义智能体与管道
# ---------------------------------------------------------------------------

@dataclass
class Agent:
    """智能体定义。"""
    name: str
    func: Callable[[Dict[str, Any]], Dict[str, Any]]
    description: str = ""

    def execute(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """执行智能体逻辑，失败时抛出 E007。"""
        try:
            return self.func(record)
        except Exception as exc:
            error_exit("E007", f"智能体 {self.name} 执行失败: {exc}")


@dataclass
class Pipeline:
    """数据流管道：由多个智能体串行组成。"""
    name: str
    agents: List[Agent] = field(default_factory=list)

    def run(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """将记录依次通过所有智能体处理。"""
        result = record
        for agent in self.agents:
            result = agent.execute(result)
        return result


# ---------------------------------------------------------------------------
# 内置智能体示例
# ---------------------------------------------------------------------------

def agent_upper(record: Dict[str, Any]) -> Dict[str, Any]:
    """将字符串字段转换为大写。"""
    for key, value in record.items():
        if isinstance(value, str):
            record[key] = value.upper()
    return record


def agent_trim(record: Dict[str, Any]) -> Dict[str, Any]:
    """去除字符串字段首尾空格。"""
    for key, value in record.items():
        if isinstance(value, str):
            record[key] = value.strip()
    return record


def agent_add_timestamp(record: Dict[str, Any]) -> Dict[str, Any]:
    """添加处理时间戳字段。"""
    import time
    record["_processed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return record


def agent_extract_numbers(record: Dict[str, Any]) -> Dict[str, Any]:
    """提取字符串字段中的所有数字并求和。"""
    import re
    total = 0
    for value in record.values():
        if isinstance(value, str):
            nums = re.findall(r"\d+", value)
            total += sum(int(n) for n in nums)
    record["_number_sum"] = total
    return record


# 内置智能体注册表
BUILTIN_AGENTS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "upper": agent_upper,
    "trim": agent_trim,
    "timestamp": agent_add_timestamp,
    "extract_numbers": agent_extract_numbers,
}


# ---------------------------------------------------------------------------
# 批量处理与结果合并
# ---------------------------------------------------------------------------

def batch_process(
    records: List[Dict[str, Any]],
    pipeline: Pipeline,
    batch_size: int = 100,
) -> List[Dict[str, Any]]:
    """对记录列表进行批量处理，支持分批执行。"""
    results: List[Dict[str, Any]] = []
    try:
        # 分批处理
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            for record in batch:
                processed = pipeline.run(dict(record))  # 深拷贝避免污染原始数据
                results.append(processed)
    except Exception as exc:
        error_exit("E008", str(exc))
    return results


def merge_results(records: List[Dict[str, Any]], merge_key: str = "id") -> Dict[str, Any]:
    """将多条记录按指定键合并为分组结构。"""
    try:
        merged: Dict[str, Any] = {}
        for record in records:
            key = record.get(merge_key, "_default")
            if key not in merged:
                merged[key] = []
            merged[key].append(record)
        return {"merged": merged, "total": len(records), "groups": len(merged)}
    except Exception as exc:
        error_exit("E009", str(exc))


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="ruflo — 数据流编排与多智能体协同批量转换工具"
    )
    parser.add_argument(
        "--parse",
        choices=["json", "csv", "xml", "txt"],
        help="输入数据格式",
    )
    parser.add_argument(
        "--input",
        help="输入文件路径（与 --parse 配合使用）",
    )
    parser.add_argument(
        "--pipeline",
        help="管道配置文件路径（JSON格式，定义智能体序列）",
    )
    parser.add_argument(
        "--batch",
        help="批量处理输入文件（与 --pipeline 配合使用）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批量处理每批大小（默认100）",
    )
    parser.add_argument(
        "--merge-key",
        default="id",
        help="结果合并时使用的分组键（默认 'id'）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )
    return parser


def load_pipeline_config(path: str) -> Pipeline:
    """从 JSON 配置文件加载管道定义。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        error_exit("E001", path)
    except json.JSONDecodeError as exc:
        error_exit("E006", f"管道配置 JSON 解析失败: {exc}")

    if not isinstance(config, dict) or "name" not in config:
        error_exit("E006", "管道配置必须包含 'name' 字段")

    pipeline = Pipeline(name=config["name"])
    agents_config = config.get("agents", [])
    if not isinstance(agents_config, list):
        error_exit("E006", "'agents' 必须是列表")

    for agent_cfg in agents_config:
        if not isinstance(agent_cfg, dict) or "name" not in agent_cfg:
            error_exit("E006", "每个智能体配置必须包含 'name' 字段")
        agent_name = agent_cfg["name"]
        if agent_name in BUILTIN_AGENTS:
            pipeline.agents.append(
                Agent(name=agent_name, func=BUILTIN_AGENTS[agent_name])
            )
        else:
            error_exit("E006", f"未知智能体类型: {agent_name}")

    return pipeline


def run_selftest() -> None:
    """内置自检：不依赖外部文件，验证核心逻辑。"""
    print("=== ruflo 自检开始 ===")

    # 1. 测试 JSON 解析
    json_text = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
    records = parse_json(json_text)
    assert len(records) == 2, "JSON 解析失败"
    assert records[0]["name"] == "Alice", "JSON 解析内容错误"
    print("[通过] JSON 解析")

    # 2. 测试 CSV 解析
    csv_text = "name,age\nAlice,30\nBob,25\n"
    records = parse_csv(csv_text)
    assert len(records) == 2, "CSV 解析失败"
    assert records[1]["name"] == "Bob", "CSV 解析内容错误"
    print("[通过] CSV 解析")

    # 3. 测试 XML 解析
    xml_text = "<root><item><name>Alice</name><age>30</age></item></root>"
    records = parse_xml(xml_text)
    assert len(records) == 1, "XML 解析失败"
    assert records[0]["name"] == "Alice", "XML 解析内容错误"
    print("[通过] XML 解析")

    # 4. 测试文本解析
    text = "第一行\n第二行\n"
    records = parse_text(text)
    assert len(records) == 2, "文本解析失败"
    assert records[0]["line"] == "第一行", "文本解析内容错误"
    print("[通过] 文本解析")

    # 5. 测试管道编排
    pipeline = Pipeline(name="测试管道")
    pipeline.agents.append(Agent(name="trim", func=agent_trim))
    pipeline.agents.append(Agent(name="upper", func=agent_upper))
    test_record = {"name": "  hello  "}
    result = pipeline.run(test_record)
    assert result["name"] == "HELLO", "管道编排失败"
    print("[通过] 智能体管道编排")

    # 6. 测试批量处理
    records = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    results = batch_process(records, pipeline, batch_size=2)
    assert len(results) == 3, "批量处理失败"
    assert results[0]["name"] == "A", "批量处理内容错误"
    print("[通过] 批量处理")

    # 7. 测试结果合并
    records = [
        {"id": 1, "value": "x"},
        {"id": 1, "value": "y"},
        {"id": 2, "value": "z"},
    ]
    merged = merge_results(records, "id")
    assert merged["total"] == 3, "合并总数错误"
    assert merged["groups"] == 2, "合并分组数错误"
    assert len(merged["merged"][1]) == 2, "合并分组内容错误"
    print("[通过] 结果合并")

    # 8. 测试错误处理
    try:
        parse_json("{invalid json}")
        assert False, "应当抛出 E003 错误"
    except SystemExit as exc:
        assert exc.code == 1, "错误退出码不正确"
    print("[通过] 错误处理")

    print("=== 全部自检通过 ===")


def main() -> None:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 模式一：单次解析
    if args.parse and args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                data = f.read()
        except FileNotFoundError:
            error_exit("E001", args.input)
        except Exception as exc:
            error_exit("E001", str(exc))

        records = parse_input(data, args.parse)
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return

    # 模式二：管道批量处理
    if args.pipeline and args.batch:
        pipeline = load_pipeline_config(args.pipeline)
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                data = f.read()
        except FileNotFoundError:
            error_exit("E001", args.batch)
        except Exception as exc:
            error_exit("E001", str(exc))

        # 自动检测格式：根据扩展名
        ext = args.batch.rsplit(".", 1)[-1].lower() if "." in args.batch else "txt"
        records = parse_input(data, ext)
        results = batch_process(records, pipeline, args.batch_size)
        merged = merge_results(results, args.merge_key)
        print(json.dumps(merged, ensure_ascii=False, indent=2))
        return

    # 无有效参数
    parser.print_help()
    error_exit("E010", "请提供有效参数组合（--parse/--input 或 --pipeline/--batch）")


if __name__ == "__main__":
    main()
