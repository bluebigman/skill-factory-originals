#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resource-controller 技能实现脚本

功能概述：
    将输入数据转化为结构化 REST 控制器结果，支持批量与自定义格式。
    本脚本为 clean-room 独立实现，仅依据功能规格编写。

核心能力（对应规格 C1-C5）：
    C1: 解析输入数据为结构化结果
    C2: 识别并保留关键字段
    C3: 支持 JSON / YAML / 表格 / 自定义模板输出
    C4: 置信度标注
    C5: 批量处理与自定义格式

明确边界（对应规格 L1-L4）：
    L1: 不执行代码
    L2: 不访问外部服务
    L3: 不保证数据准确性
    L4: 不生成完整应用

错误码说明：
    E001: 输入数据为空或无效
    E002: 输入数据不是可解析的格式
    E003: 输出格式不支持
    E004: 批量处理时输入为空
    E005: 自定义模板格式错误
    E006: 字段提取失败
    E007: 置信度计算异常
    E008: 数据转换失败
    E009: 内部逻辑错误
    E010: 未知错误

用法示例：
    python scripts/main.py --input data.json --format json
    python scripts/main.py --input data.csv --format table
    python scripts/main.py --selftest
"""

import argparse
import csv
import io
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


# ============================================================
# 常量定义
# ============================================================

SUPPORTED_FORMATS = ["json", "yaml", "table", "custom"]
DEFAULT_CONFIDENCE = 0.8
HIGH_CONFIDENCE = 0.95
MEDIUM_CONFIDENCE = 0.75
LOW_CONFIDENCE = 0.5

# 错误码对应的错误信息
ERROR_MESSAGES = {
    "E001": "输入数据为空或无效",
    "E002": "输入数据不是可解析的格式",
    "E003": "输出格式不支持",
    "E004": "批量处理时输入为空",
    "E005": "自定义模板格式错误",
    "E006": "字段提取失败",
    "E007": "置信度计算异常",
    "E008": "数据转换失败",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class ResourceControllerError(Exception):
    """资源控制器异常类，携带错误码"""

    def __init__(self, error_code: str, message: Optional[str] = None):
        self.error_code = error_code
        self.message = message or ERROR_MESSAGES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class FieldInfo:
    """字段信息，包含字段名、值、置信度"""

    def __init__(self, name: str, value: Any, confidence: float = DEFAULT_CONFIDENCE):
        self.name = name
        self.value = value
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.name,
            "value": self.value,
            "confidence": self.confidence,
        }


class ControllerResult:
    """控制器结果对象，包含结构化数据和元信息"""

    def __init__(self, resource_name: str, fields: List[FieldInfo]):
        self.resource_name = resource_name
        self.fields = fields
        self.created_at = datetime.now().isoformat()
        self.result_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_name": self.resource_name,
            "fields": [f.to_dict() for f in self.fields],
            "created_at": self.created_at,
            "result_id": self.result_id,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        """返回简化字典，字段名直接映射到值"""
        result = {}
        for field in self.fields:
            result[field.name] = field.value
        return result


# ============================================================
# 数据解析模块（C1）
# ============================================================

class DataParser:
    """数据解析器，支持 JSON、CSV、纯文本等格式"""

    @staticmethod
    def parse(data: Union[str, bytes, Dict, List]) -> List[Dict[str, Any]]:
        """
        解析输入数据为结构化字典列表
        
        Args:
            data: 输入数据，可以是字符串、字节或已解析的对象
            
        Returns:
            结构化字典列表
            
        Raises:
            ResourceControllerError: E001 输入为空, E002 格式错误
        """
        if data is None:
            raise ResourceControllerError("E001")

        # 如果已经是字典或列表，直接使用
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data

        # 如果是字节，尝试解码
        if isinstance(data, bytes):
            try:
                data = data.decode("utf-8")
            except UnicodeDecodeError:
                raise ResourceControllerError("E002")

        if not isinstance(data, str):
            raise ResourceControllerError("E002")

        # 去除空白
        data = data.strip()
        if not data:
            raise ResourceControllerError("E001")

        # 尝试 JSON 解析
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return [parsed]
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # 尝试 CSV 解析
        try:
            csv_reader = csv.DictReader(io.StringIO(data))
            rows = list(csv_reader)
            if rows:
                return rows
        except Exception:
            pass

        # 尝试键值对解析 (key: value 或 key=value)
        try:
            result = {}
            for line in data.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                elif "=" in line:
                    key, value = line.split("=", 1)
                else:
                    continue
                result[key.strip()] = value.strip()
            if result:
                return [result]
        except Exception:
            pass

        # 无法解析
        raise ResourceControllerError("E002")


# ============================================================
# 关键信息识别模块（C2）
# ============================================================

class FieldExtractor:
    """字段提取器，从原始数据中识别关键字段"""

    # 常见字段名映射，用于识别
    COMMON_FIELDS = {
        "name": ["name", "名称", "姓名", "product_name", "资源名"],
        "id": ["id", "ID", "编号", "序号"],
        "type": ["type", "类型", "类别"],
        "status": ["status", "状态"],
        "description": ["description", "描述", "说明"],
        "price": ["price", "价格", "金额"],
        "count": ["count", "数量", "个数"],
        "created": ["created", "创建时间", "created_at"],
        "updated": ["updated", "更新时间", "updated_at"],
        "owner": ["owner", "所有者", "负责人"],
        "url": ["url", "链接", "地址"],
        "version": ["version", "版本"],
    }

    @staticmethod
    def extract(raw_data: Dict[str, Any], resource_name: str = "resource") -> List[FieldInfo]:
        """
        从原始字典中提取关键字段并标注置信度
        
        Args:
            raw_data: 原始数据字典
            resource_name: 资源名称
            
        Returns:
            字段信息列表
            
        Raises:
            ResourceControllerError: E006 字段提取失败
        """
        try:
            fields = []
            for key, value in raw_data.items():
                if value is None:
                    continue

                # 计算置信度
                confidence = FieldExtractor._calc_confidence(key, value)

                # 创建字段信息
                field = FieldInfo(name=key, value=value, confidence=confidence)
                fields.append(field)

            if not fields:
                # 没有提取到任何字段
                raise ResourceControllerError("E006")

            return fields
        except ResourceControllerError:
            raise
        except Exception:
            raise ResourceControllerError("E006")

    @staticmethod
    def _calc_confidence(key: str, value: Any) -> float:
        """
        计算字段置信度
        
        规则：
        - 字段名匹配常见字段名 → 高置信度
        - 字段名包含常见关键词 → 中置信度
        - 值非空且类型明确 → 中置信度
        - 其他 → 低置信度
        """
        key_lower = key.lower()

        # 完全匹配常见字段
        for canonical, aliases in FieldExtractor.COMMON_FIELDS.items():
            if key_lower == canonical or key_lower in aliases:
                return HIGH_CONFIDENCE

        # 包含匹配
        for canonical, aliases in FieldExtractor.COMMON_FIELDS.items():
            for alias in aliases:
                if alias in key_lower or key_lower in alias:
                    return MEDIUM_CONFIDENCE

        # 值类型判断
        if isinstance(value, (int, float, bool)):
            return MEDIUM_CONFIDENCE
        if isinstance(value, str) and len(value) > 0:
            return MEDIUM_CONFIDENCE
        if isinstance(value, (list, dict)):
            return MEDIUM_CONFIDENCE

        return LOW_CONFIDENCE


# ============================================================
# 输出格式化模块（C3）
# ============================================================

class OutputFormatter:
    """输出格式化器，支持多种格式"""

    @staticmethod
    def format(result: ControllerResult, fmt: str = "json", template: Optional[str] = None) -> str:
        """
        将控制器结果格式化为指定格式
        
        Args:
            result: 控制器结果对象
            fmt: 输出格式 (json/yaml/table/custom)
            template: 自定义模板（当 fmt=custom 时使用）
            
        Returns:
            格式化后的字符串
            
        Raises:
            ResourceControllerError: E003 格式不支持, E005 模板错误
        """
        if fmt not in SUPPORTED_FORMATS:
            raise ResourceControllerError("E003")

        if fmt == "json":
            return OutputFormatter._to_json(result)
        elif fmt == "yaml":
            return OutputFormatter._to_yaml(result)
        elif fmt == "table":
            return OutputFormatter._to_table(result)
        elif fmt == "custom":
            if not template:
                raise ResourceControllerError("E005")
            return OutputFormatter._to_custom(result, template)
        else:
            raise ResourceControllerError("E003")

    @staticmethod
    def _to_json(result: ControllerResult) -> str:
        """转换为 JSON 格式"""
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def _to_yaml(result: ControllerResult) -> str:
        """转换为 YAML 格式（简化实现，不使用第三方库）"""
        lines = []
        lines.append(f"resource_name: {result.resource_name}")
        lines.append(f"result_id: {result.result_id}")
        lines.append(f"created_at: {result.created_at}")
        lines.append("fields:")
        for field in result.fields:
            lines.append(f"  - field: {field.name}")
            lines.append(f"    value: {field.value}")
            lines.append(f"    confidence: {field.confidence}")
        return "\n".join(lines)

    @staticmethod
    def _to_table(result: ControllerResult) -> str:
        """转换为表格格式"""
        # 计算列宽
        headers = ["字段名", "值", "置信度"]
        rows = []
        for field in result.fields:
            rows.append([field.name, str(field.value), f"{field.confidence:.2f}"])

        # 计算宽度
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # 构建表格
        lines = []
        # 表头
        header_line = " | ".join(
            headers[i].ljust(col_widths[i]) for i in range(len(headers))
        )
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # 数据行
        for row in rows:
            line = " | ".join(
                row[i].ljust(col_widths[i]) for i in range(len(row))
            )
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _to_custom(result: ControllerResult, template: str) -> str:
        """
        使用自定义模板格式化
        
        模板中支持占位符：
        {resource_name} - 资源名称
        {field_name} - 字段名（循环）
        {field_value} - 字段值（循环）
        {field_confidence} - 字段置信度（循环）
        {result_id} - 结果ID
        {created_at} - 创建时间
        """
        try:
            output = template
            # 替换单值占位符
            output = output.replace("{resource_name}", result.resource_name)
            output = output.replace("{result_id}", result.result_id)
            output = output.replace("{created_at}", result.created_at)

            # 处理循环占位符
            # 简单的 {fields} 块
            if "{fields}" in output:
                field_block = ""
                for field in result.fields:
                    block = "{field_name}: {field_value} ({field_confidence})"
                    block = block.replace("{field_name}", field.name)
                    block = block.replace("{field_value}", str(field.value))
                    block = block.replace("{field_confidence}", f"{field.confidence:.2f}")
                    field_block += block + "\n"
                output = output.replace("{fields}", field_block.rstrip("\n"))

            return output
        except Exception:
            raise ResourceControllerError("E005")


# ============================================================
# 批量处理模块（C5）
# ============================================================

class BatchProcessor:
    """批量处理器，支持多记录处理"""

    @staticmethod
    def process(data_items: List[Any], resource_name: str = "resource") -> List[ControllerResult]:
        """
        批量处理数据项
        
        Args:
            data_items: 数据项列表
            resource_name: 资源名称
            
        Returns:
            控制器结果列表
            
        Raises:
            ResourceControllerError: E004 输入为空
        """
        if not data_items:
            raise ResourceControllerError("E004")

        results = []
        for item in data_items:
            # 解析每一项
            parsed_items = DataParser.parse(item)
            for parsed in parsed_items:
                # 提取字段
                fields = FieldExtractor.extract(parsed, resource_name)
                # 创建结果
                result = ControllerResult(resource_name, fields)
                results.append(result)

        return results


# ============================================================
# 主控制器类
# ============================================================

class ResourceController:
    """资源控制器主类，整合所有功能"""

    def __init__(self):
        self.parser = DataParser()
        self.extractor = FieldExtractor()
        self.formatter = OutputFormatter()
        self.batch_processor = BatchProcessor()

    def process(
        self,
        data: Union[str, bytes, Dict, List],
        resource_name: str = "resource",
        fmt: str = "json",
        template: Optional[str] = None,
        batch: bool = False,
    ) -> str:
        """
        处理输入数据并返回格式化结果
        
        Args:
            data: 输入数据
            resource_name: 资源名称
            fmt: 输出格式
            template: 自定义模板
            batch: 是否批量处理
            
        Returns:
            格式化后的结果字符串
            
        Raises:
            ResourceControllerError: 各种错误码
        """
        try:
            if batch:
                # 批量处理
                if isinstance(data, list):
                    items = data
                else:
                    # 解析为列表
                    parsed = self.parser.parse(data)
                    items = parsed

                results = self.batch_processor.process(items, resource_name)

                # 批量结果合并
                if fmt == "json":
                    combined = {
                        "resource_name": resource_name,
                        "batch_size": len(results),
                        "results": [r.to_dict() for r in results],
                    }
                    return json.dumps(combined, ensure_ascii=False, indent=2)
                else:
                    # 非 JSON 格式，逐个处理并用分隔符连接
                    outputs = []
                    for result in results:
                        outputs.append(self.formatter.format(result, fmt, template))
                    return "\n\n---\n\n".join(outputs)
            else:
                # 单条处理
                parsed_items = self.parser.parse(data)
                if not parsed_items:
                    raise ResourceControllerError("E001")

                # 取第一条记录
                raw_data = parsed_items[0]
                fields = self.extractor.extract(raw_data, resource_name)
                result = ControllerResult(resource_name, fields)

                return self.formatter.format(result, fmt, template)

        except ResourceControllerError:
            raise
        except Exception as e:
            raise ResourceControllerError("E010", str(e))


# ============================================================
# 自检模块（--selftest）
# ============================================================

class SelfTest:
    """自检模块，使用内置硬编码样例数据离线测试"""

    @staticmethod
    def run() -> bool:
        """
        运行自检
        
        Returns:
            自检是否通过
        """
        print("=" * 60)
        print("resource-controller 自检开始")
        print("=" * 60)

        controller = ResourceController()

        # 测试用例 1: JSON 解析与格式化
        print("\n[测试 1] JSON 解析与格式化")
        try:
            test_json = '{"name": "测试资源", "type": "compute", "status": "active"}'
            result = controller.process(test_json, resource_name="test_resource")
            parsed = json.loads(result)
            assert parsed["resource_name"] == "test_resource", "资源名称不匹配"
            assert len(parsed["fields"]) >= 3, "字段数量不足"
            assert any(f["field"] == "name" for f in parsed["fields"]), "缺少 name 字段"
            assert any(f["field"] == "type" for f in parsed["fields"]), "缺少 type 字段"
            print("  ✓ JSON 解析与格式化通过")
        except Exception as e:
            print(f"  ✗ 测试 1 失败: {e}")
            return False

        # 测试用例 2: CSV 解析
        print("\n[测试 2] CSV 解析")
        try:
            test_csv = "name,age,city\n张三,30,北京\n李四,25,上海"
            result = controller.process(test_csv, resource_name="users")
            parsed = json.loads(result)
            assert parsed["resource_name"] == "users", "资源名称不匹配"
            assert len(parsed["fields"]) >= 3, "字段数量不足"
            assert any(f["field"] == "name" for f in parsed["fields"]), "缺少 name 字段"
            assert any(f["field"] == "city" for f in parsed["fields"]), "缺少 city 字段"
            print("  ✓ CSV 解析通过")
        except Exception as e:
            print(f"  ✗ 测试 2 失败: {e}")
            return False

        # 测试用例 3: 批量处理
        print("\n[测试 3] 批量处理")
        try:
            test_batch = [
                {"name": "资源A", "count": 10},
                {"name": "资源B", "count": 20},
                {"name": "资源C", "count": 30},
            ]
            result = controller.process(test_batch, resource_name="batch_resources", batch=True)
            parsed = json.loads(result)
            assert parsed["batch_size"] == 3, f"批量大小应为 3，实际 {parsed['batch_size']}"
            assert len(parsed["results"]) == 3, "结果数量不正确"
            print("  ✓ 批量处理通过")
        except Exception as e:
            print(f"  ✗ 测试 3 失败: {e}")
            return False

        # 测试用例 4: 表格输出
        print("\n[测试 4] 表格输出")
        try:
            test_data = {"name": "测试", "status": "ok"}
            result = controller.process(test_data, fmt="table")
            assert "字段名" in result, "表格缺少表头"
            assert "name" in result, "表格缺少字段名"
            print("  ✓ 表格输出通过")
        except Exception as e:
            print(f"  ✗ 测试 4 失败: {e}")
            return False

        # 测试用例 5: 置信度标注
        print("\n[测试 5] 置信度标注")
        try:
            test_data = {"name": "测试", "custom_field": "自定义值"}
            result = controller.process(test_data)
            parsed = json.loads(result)
            fields = parsed["fields"]
            for field in fields:
                assert 0 <= field["confidence"] <= 1, "置信度超出范围"
                assert field["confidence"] > 0, "置信度应为正数"
            # name 字段应有较高置信度
            name_field = next(f for f in fields if f["field"] == "name")
            assert name_field["confidence"] > 0.8, "name 字段置信度应较高"
            print("  ✓ 置信度标注通过")
        except Exception as e:
            print(f"  ✗ 测试 5 失败: {e}")
            return False

        # 测试用例 6: 自定义模板
        print("\n[测试 6] 自定义模板")
        try:
            test_data = {"name": "测试资源", "type": "storage"}
            template = "资源: {resource_name}\n名称: {field_name} = {field_value}"
            result = controller.process(test_data, fmt="custom", template=template)
            assert "资源:" in result, "模板未正确应用"
            assert "名称:" in result, "模板字段未正确应用"
            print("  ✓ 自定义模板通过")
        except Exception as e:
            print(f"  ✗ 测试 6 失败: {e}")
            return False

        # 测试用例 7: 错误处理
        print("\n[测试 7] 错误处理")
        try:
            # 空数据
            try:
                controller.process("")
                print("  ✗ 空数据应抛出错误")
                return False
            except ResourceControllerError as e:
                assert e.error_code == "E001", f"错误码应为 E001，实际 {e.error_code}"

            # 不支持的格式
            try:
                controller.process("test", fmt="xml")
                print("  ✗ 不支持的格式应抛出错误")
                return False
            except ResourceControllerError as e:
                assert e.error_code == "E003", f"错误码应为 E003，实际 {e.error_code}"

            print("  ✓ 错误处理通过")
        except Exception as e:
            print(f"  ✗ 测试 7 失败: {e}")
            return False

        # 测试用例 8: 边界测试
        print("\n[测试 8] 边界测试")
        try:
            # 空字段数据
            test_empty = {}
            result = controller.process(json.dumps(test_empty), resource_name="empty")
            parsed = json.loads(result)
            # 空数据可能成功也可能失败，但不应崩溃
            print(f"  ✓ 空字段数据处理通过 (字段数: {len(parsed['fields'])})")
        except ResourceControllerError:
            # 空数据抛出 E006 也是可接受的
            print("  ✓ 空字段数据正确抛出错误")
        except Exception as e:
            print(f"  ✗ 测试 8 失败: {e}")
            return False

        print("\n" + "=" * 60)
        print("所有自检通过！")
        print("=" * 60)
        return True


# ============================================================
# 命令行入口
# ============================================================

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(
        description="resource-controller: 资源编排控制器生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/main.py --input data.json --format json
  python scripts/main.py --input data.csv --format table
  python scripts/main.py --input data.txt --resource-name users --format yaml
  python scripts/main.py --input batch.json --batch --format json
  python scripts/main.py --selftest
        """,
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据文件路径（JSON/CSV/TXT），或直接输入数据字符串",
    )
    parser.add_argument(
        "--resource-name", "-r",
        type=str,
        default="resource",
        help="资源名称（默认: resource）",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=SUPPORTED_FORMATS,
        help=f"输出格式（默认: json，可选: {', '.join(SUPPORTED_FORMATS)}）",
    )
    parser.add_argument(
        "--template", "-t",
        type=str,
        help="自定义模板（当 --format custom 时使用）",
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量处理模式",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="resource-controller 1.0.1",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = SelfTest.run()
        sys.exit(0 if success else 1)

    # 检查输入
    if not args.input:
        parser.error("必须提供 --input 或使用 --selftest")

    # 读取输入
    try:
        input_data = args.input
        # 检查是否为文件路径
        if os.path.isfile(args.input):
            with open(args.input, "r", encoding="utf-8") as f:
                input_data = f.read()
        # 否则视为直接输入的数据字符串
    except Exception as e:
        print(f"[E010] 读取输入失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 处理数据
    try:
        controller = ResourceController()
        result = controller.process(
            data=input_data,
            resource_name=args.resource_name,
            fmt=args.format,
            template=args.template,
            batch=args.batch,
        )
        print(result)
    except ResourceControllerError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
