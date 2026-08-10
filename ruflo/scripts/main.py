#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ruflo - 数据管道多智能体编排批量转换工具

本脚本依据功能规格独立实现（clean-room），不包含任何既有代码。
功能：将 JSON/CSV/XML/纯文本等数据源解析为结构化结果，
      支持多智能体协同与批量处理。
"""

import argparse
import csv
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"      # 输入数据无效或无法解析
ERR_UNSUPPORTED_FORMAT = "E002" # 不支持的输入格式
ERR_FIELD_MAPPING = "E003"      # 字段映射错误
ERR_MISSING_REQUIRED = "E004"   # 缺少必填字段
ERR_AGENT_FAILURE = "E005"      # 智能体处理失败
ERR_BATCH_EMPTY = "E006"        # 批量数据为空
ERR_RESUME_FAILURE = "E007"     # 断点续跑失败
ERR_CONFIG_ERROR = "E008"       # 配置错误
ERR_INTERNAL = "E009"           # 内部错误
ERR_USAGE = "E010"              # 命令行参数错误


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class Record:
    """单条结构化记录"""
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    source: str = ""


@dataclass
class ParseResult:
    """解析结果"""
    records: List[Record] = field(default_factory=list)
    total: int = 0
    failed: int = 0
    error_code: str = ERR_SUCCESS
    error_message: str = ""


@dataclass
class AgentTask:
    """智能体任务定义"""
    name: str
    func: Callable[[Record], Record]
    description: str = ""


@dataclass
class PipelineConfig:
    """流水线配置"""
    input_format: str = "json"          # json/csv/xml/text
    required_fields: List[str] = field(default_factory=list)
    field_mapping: Dict[str, str] = field(default_factory=dict)  # 源字段->目标字段
    batch_size: int = 100
    resume_from: int = 0                # 断点续跑位置
    agents: List[AgentTask] = field(default_factory=list)


# ============================================================
# 数据解析器（多源接入）
# ============================================================
class DataParser:
    """多格式数据解析器"""
    
    @staticmethod
    def parse_json(content: str) -> List[Dict[str, Any]]:
        """解析 JSON 数据"""
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise ValueError("JSON 顶层必须是对象或数组")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")
    
    @staticmethod
    def parse_csv(content: str) -> List[Dict[str, Any]]:
        """解析 CSV 数据"""
        try:
            reader = csv.DictReader(io.StringIO(content))
            return [dict(row) for row in reader]
        except Exception as e:
            raise ValueError(f"CSV 解析失败: {e}")
    
    @staticmethod
    def parse_xml(content: str) -> List[Dict[str, Any]]:
        """解析 XML 数据，提取 item/record 元素"""
        try:
            root = ET.fromstring(content)
            records = []
            # 查找所有 item 或 record 元素
            for elem in root.iter():
                if elem.tag.lower() in ("item", "record", "row"):
                    rec = {}
                    for child in elem:
                        rec[child.tag] = child.text or ""
                    records.append(rec)
            if not records:
                # 如果没找到标准元素，将根元素的子元素作为记录
                for child in root:
                    if len(child) > 0:
                        rec = {}
                        for sub in child:
                            rec[sub.tag] = sub.text or ""
                        records.append(rec)
            return records
        except ET.ParseError as e:
            raise ValueError(f"XML 解析失败: {e}")
    
    @staticmethod
    def parse_text(content: str) -> List[Dict[str, Any]]:
        """解析纯文本，按行拆分，尝试 key=value 格式"""
        records = []
        current = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                if current:
                    records.append(current)
                    current = {}
                continue
            # 尝试 key=value 或 key: value 格式
            match = re.match(r"^([^=:]+)[=:]\s*(.+)$", line)
            if match:
                current[match.group(1).strip()] = match.group(2).strip()
            else:
                current["text"] = line
        if current:
            records.append(current)
        return records
    
    @classmethod
    def parse(cls, content: str, fmt: str) -> List[Dict[str, Any]]:
        """统一解析入口"""
        parsers = {
            "json": cls.parse_json,
            "csv": cls.parse_csv,
            "xml": cls.parse_xml,
            "text": cls.parse_text,
        }
        if fmt not in parsers:
            raise ValueError(f"不支持的格式: {fmt}")
        return parsers[fmt](content)


# ============================================================
# 字段映射与校验
# ============================================================
class FieldMapper:
    """字段映射与校验器"""
    
    @staticmethod
    def apply_mapping(records: List[Dict[str, Any]], mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """应用字段映射"""
        if not mapping:
            return records
        mapped_records = []
        for rec in records:
            new_rec = {}
            for src_field, dst_field in mapping.items():
                if src_field in rec:
                    new_rec[dst_field] = rec[src_field]
                else:
                    new_rec[dst_field] = None
            # 保留未映射的字段
            for key, value in rec.items():
                if key not in mapping:
                    new_rec[key] = value
            mapped_records.append(new_rec)
        return mapped_records
    
    @staticmethod
    def validate_required(records: List[Dict[str, Any]], required_fields: List[str]) -> tuple:
        """校验必填字段，返回 (有效记录, 缺失列表)"""
        valid_records = []
        invalid_records = []
        for rec in records:
            missing = [f for f in required_fields if f not in rec or rec[f] in (None, "")]
            if missing:
                invalid_records.append((rec, missing))
            else:
                valid_records.append(rec)
        return valid_records, invalid_records


# ============================================================
# 多智能体编排
# ============================================================
class AgentOrchestrator:
    """多智能体协同处理器"""
    
    def __init__(self, agents: List[AgentTask] = None):
        self.agents = agents or []
    
    def register_agent(self, agent: AgentTask):
        """注册智能体"""
        self.agents.append(agent)
    
    def process(self, record: Record) -> Record:
        """依次执行所有智能体"""
        for agent in self.agents:
            try:
                record = agent.func(record)
                if record is None:
                    record = Record(source=agent.name, errors=[f"智能体 {agent.name} 返回空"])
            except Exception as e:
                record.errors.append(f"智能体 {agent.name} 失败: {e}")
        return record
    
    def process_batch(self, records: List[Record]) -> List[Record]:
        """批量处理（模拟并行，实际串行执行）"""
        results = []
        for rec in records:
            results.append(self.process(rec))
        return results


# ============================================================
# 批量流水线
# ============================================================
class BatchPipeline:
    """批量处理流水线，支持断点续跑"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.parser = DataParser()
        self.mapper = FieldMapper()
        self.orchestrator = AgentOrchestrator(config.agents)
        self.processed_count = 0
    
    def load_data(self, content: str) -> List[Dict[str, Any]]:
        """加载并解析数据"""
        raw_records = self.parser.parse(content, self.config.input_format)
        if not raw_records:
            raise ValueError(ERR_BATCH_EMPTY)
        # 应用字段映射
        mapped = self.mapper.apply_mapping(raw_records, self.config.field_mapping)
        # 校验必填字段
        valid, invalid = self.mapper.validate_required(mapped, self.config.required_fields)
        return valid
    
    def run(self, content: str, resume: bool = False) -> ParseResult:
        """执行流水线"""
        try:
            records_data = self.load_data(content)
            if not records_data:
                return ParseResult(error_code=ERR_BATCH_EMPTY, error_message="没有有效记录")
            
            # 断点续跑
            start_idx = 0
            if resume:
                start_idx = self.config.resume_from
                if start_idx >= len(records_data):
                    return ParseResult(error_code=ERR_RESUME_FAILURE, 
                                      error_message="断点位置超出数据范围")
            
            # 构建 Record 对象
            records = [Record(data=d, source=f"batch_{i+1}") 
                      for i, d in enumerate(records_data[start_idx:], start=start_idx)]
            
            # 批量处理
            processed = self.orchestrator.process_batch(records)
            self.processed_count = len(processed)
            
            # 统计结果
            valid_records = [r for r in processed if not r.errors]
            failed_count = len(processed) - len(valid_records)
            
            return ParseResult(
                records=processed,
                total=len(processed),
                failed=failed_count,
                error_code=ERR_SUCCESS,
                error_message=""
            )
        except ValueError as e:
            return ParseResult(error_code=ERR_INVALID_INPUT, error_message=str(e))
        except Exception as e:
            return ParseResult(error_code=ERR_INTERNAL, error_message=f"内部错误: {e}")


# ============================================================
# 内置智能体示例
# ============================================================
def agent_strip_whitespace(record: Record) -> Record:
    """智能体：去除字符串字段首尾空白"""
    for key, value in record.data.items():
        if isinstance(value, str):
            record.data[key] = value.strip()
    return record


def agent_normalize_phone(record: Record) -> Record:
    """智能体：规范化手机号格式"""
    phone = record.data.get("phone") or record.data.get("mobile")
    if phone:
        digits = re.sub(r"\D", "", str(phone))
        if len(digits) == 11 and digits.startswith("1"):
            record.data["phone_normalized"] = digits
    return record


def agent_fill_default(record: Record) -> Record:
    """智能体：填充默认值"""
    defaults = {"status": "active", "source_type": "imported"}
    for key, value in defaults.items():
        if key not in record.data or record.data[key] in (None, ""):
            record.data[key] = value
    return record


# ============================================================
# 内置自检（selftest）
# ============================================================
def run_selftest() -> bool:
    """离线自检核心逻辑"""
    print("[SELFTEST] 开始自检...")
    
    # 测试1: JSON 解析
    print("[TEST 1] JSON 解析")
    json_data = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
    result = DataParser.parse(json_data, "json")
    assert len(result) == 2, "JSON 解析记录数错误"
    assert result[0]["name"] == "Alice", "JSON 字段值错误"
    print("  ✓ 通过")
    
    # 测试2: CSV 解析
    print("[TEST 2] CSV 解析")
    csv_data = "name,age,city\nAlice,30,Beijing\nBob,25,Shanghai"
    result = DataParser.parse(csv_data, "csv")
    assert len(result) == 2, "CSV 解析记录数错误"
    assert result[1]["city"] == "Shanghai", "CSV 字段值错误"
    print("  ✓ 通过")
    
    # 测试3: 字段映射
    print("[TEST 3] 字段映射")
    records = [{"full_name": "Alice", "years": 30}]
    mapping = {"full_name": "name", "years": "age"}
    mapped = FieldMapper.apply_mapping(records, mapping)
    assert mapped[0]["name"] == "Alice", "字段映射错误"
    assert mapped[0]["age"] == 30, "字段映射类型错误"
    print("  ✓ 通过")
    
    # 测试4: 必填字段校验
    print("[TEST 4] 必填字段校验")
    records = [{"name": "Alice", "email": "a@b.com"}, {"name": "", "email": "c@d.com"}]
    valid, invalid = FieldMapper.validate_required(records, ["name", "email"])
    assert len(valid) == 1, "有效记录数错误"
    assert len(invalid) == 1, "无效记录数错误"
    assert "name" in invalid[0][1], "缺失字段检测错误"
    print("  ✓ 通过")
    
    # 测试5: 智能体编排
    print("[TEST 5] 智能体编排")
    orchestrator = AgentOrchestrator([
        AgentTask("strip", agent_strip_whitespace, "去除空白"),
        AgentTask("default", agent_fill_default, "填充默认值"),
    ])
    rec = Record(data={"name": "  Alice  ", "phone": "138-0013-8000"})
    processed = orchestrator.process(rec)
    assert processed.data["name"] == "Alice", "智能体去空白失败"
    assert processed.data["status"] == "active", "智能体填充默认值失败"
    assert not processed.errors, "智能体处理不应有错误"
    print("  ✓ 通过")
    
    # 测试6: 完整流水线
    print("[TEST 6] 完整流水线")
    config = PipelineConfig(
        input_format="json",
        required_fields=["name", "email"],
        field_mapping={"full_name": "name"},
    )
    pipeline = BatchPipeline(config)
    content = '[{"full_name": "Alice", "email": "alice@test.com"}, {"full_name": "Bob", "email": "bob@test.com"}]'
    result = pipeline.run(content)
    assert result.error_code == ERR_SUCCESS, f"流水线错误: {result.error_message}"
    assert result.total == 2, "流水线记录数错误"
    assert result.failed == 0, "流水线失败数错误"
    print("  ✓ 通过")
    
    # 测试7: XML 解析
    print("[TEST 7] XML 解析")
    xml_data = '<root><item><name>Alice</name><age>30</age></item><item><name>Bob</name><age>25</age></item></root>'
    result = DataParser.parse(xml_data, "xml")
    assert len(result) == 2, "XML 解析记录数错误"
    assert result[0]["name"] == "Alice", "XML 字段值错误"
    print("  ✓ 通过")
    
    # 测试8: 错误处理
    print("[TEST 8] 错误处理")
    try:
        DataParser.parse("{invalid json", "json")
        assert False, "应抛出异常"
    except ValueError:
        pass
    print("  ✓ 通过")
    
    print("[SELFTEST] 全部测试通过！")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="ruflo - 数据管道多智能体编排批量转换工具",
        epilog="示例: python main.py --input data.json --format json --required name,email"
    )
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--content", "-c", help="直接输入数据内容")
    parser.add_argument("--format", "-f", choices=["json", "csv", "xml", "text"],
                       default="json", help="输入数据格式")
    parser.add_argument("--required", "-r", help="必填字段，逗号分隔")
    parser.add_argument("--mapping", "-m", help="字段映射，格式: src1:dst1,src2:dst2")
    parser.add_argument("--batch-size", type=int, default=100, help="批处理大小")
    parser.add_argument("--resume", action="store_true", help="启用断点续跑")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"[SELFTEST] 失败: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 参数校验
    if not args.input and not args.content:
        parser.error("必须提供 --input 或 --content 参数")
        sys.exit(ERR_USAGE)
    
    # 读取数据
    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = args.content
    except Exception as e:
        print(f"读取数据失败: {e}", file=sys.stderr)
        sys.exit(ERR_INVALID_INPUT)
    
    # 解析配置
    required_fields = args.required.split(",") if args.required else []
    field_mapping = {}
    if args.mapping:
        for pair in args.mapping.split(","):
            src, dst = pair.split(":")
            field_mapping[src.strip()] = dst.strip()
    
    # 构建配置
    config = PipelineConfig(
        input_format=args.format,
        required_fields=required_fields,
        field_mapping=field_mapping,
        batch_size=args.batch_size,
    )
    
    # 注册默认智能体
    config.agents = [
        AgentTask("strip", agent_strip_whitespace, "去除空白"),
        AgentTask("default", agent_fill_default, "填充默认值"),
    ]
    
    # 执行流水线
    pipeline = BatchPipeline(config)
    result = pipeline.run(content, resume=args.resume)
    
    # 输出结果
    if result.error_code != ERR_SUCCESS:
        print(f"处理失败 ({result.error_code}): {result.error_message}", file=sys.stderr)
        sys.exit(1)
    
    # 打印结果
    print(f"处理完成: 共 {result.total} 条，失败 {result.failed} 条")
    for i, rec in enumerate(result.records):
        status = "✓" if not rec.errors else f"✗ ({'; '.join(rec.errors)})"
        print(f"  [{i+1}] {rec.data} {status}")
    
    sys.exit(0 if result.failed == 0 else 2)


if __name__ == "__main__":
    main()
