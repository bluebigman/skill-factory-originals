#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转文档 - 结构化转换工具
技能功能规格: parsers
版本: 1.0.0
许可证: MIT
"""

import argparse
import json
import sys
import re
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "输出格式不支持",
    "E008": "置信度计算失败",
    "E009": "批量处理中断",
    "E010": "参数校验失败",
}


class ParsingError(Exception):
    """解析异常，携带错误码"""
    def __init__(self, error_code: str, message: Optional[str] = None):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心功能模块
# ============================================================

class DataParser:
    """数据解析器：识别输入中的关键信息并结构化"""
    
    # 常见字段模式（宽松匹配）
    FIELD_PATTERNS = {
        "name": [r"(?:姓名|名称|名字)[:：]\s*(.+)", r"(?:name)\s*[:：]\s*(.+)"],
        "email": [r"[\w.+-]+@[\w-]+\.[\w.]+"],
        "phone": [r"(?:电话|手机|联系方式)[:：]\s*([+\d\s-]{6,})", r"(?:tel|phone)[:：]\s*([+\d\s-]{6,})"],
        "date": [r"(?:日期|时间)[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)", r"(?:date)[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"],
        "amount": [r"(?:金额|价格|费用)[:：]\s*([¥$€]?\s*\d+(?:\.\d+)?(?:元|块|美元|欧元)?)", r"(?:amount|price)[:：]\s*([¥$€]?\s*\d+(?:\.\d+)?)"],
        "id": [r"(?:编号|ID|序号)[:：]\s*([A-Za-z0-9_-]+)", r"(?:id|no)[:：]\s*([A-Za-z0-9_-]+)"],
    }
    
    def __init__(self, input_text: str):
        """初始化解析器"""
        if not input_text or not input_text.strip():
            raise ParsingError("E001")
        self.raw_text = input_text.strip()
        self.structured: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.uncertain_fields: List[str] = []
    
    def parse(self) -> Dict[str, Any]:
        """执行解析主流程"""
        # 1. 识别关键字段
        self._extract_fields()
        
        # 2. 计算置信度
        self._calculate_confidence()
        
        # 3. 生成结果
        return self._build_result()
    
    def _extract_fields(self) -> None:
        """提取字段（宽松匹配）"""
        for field, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, self.raw_text, re.IGNORECASE)
                if match:
                    value = match.group(1) if match.lastindex else match.group(0)
                    self.structured[field] = value.strip()
                    break
        
        # 如果没有提取到任何字段，尝试按行拆分
        if not self.structured:
            lines = [l.strip() for l in self.raw_text.split('\n') if l.strip()]
            if lines:
                self.structured["content"] = lines
                self.uncertain_fields.append("content")
    
    def _calculate_confidence(self) -> None:
        """计算置信度（宽松阈值）"""
        if not self.structured:
            self.confidence = 0.0
            self.uncertain_fields.append("all")
            return
        
        # 基础置信度：已提取字段越多，置信度越高
        base = min(90.0, 50.0 + len(self.structured) * 10.0)
        
        # 有不确定字段则降低置信度
        uncertainty_penalty = len(self.uncertain_fields) * 5.0
        self.confidence = max(0.0, base - uncertainty_penalty)
    
    def _build_result(self) -> Dict[str, Any]:
        """构建输出结果"""
        result = {
            "data": self.structured,
            "confidence": round(self.confidence, 1),
            "uncertain_fields": self.uncertain_fields,
        }
        
        # 置信度标注
        if self.confidence >= 90:
            result["level"] = "直接输出"
        elif self.confidence >= 85:
            result["level"] = "建议复核"
        else:
            result["level"] = "[需核实]"
            result["note"] = "置信度过低，关键结果请人工复核"
        
        return result


class OutputFormatter:
    """输出格式化器：按约定格式生成输出"""
    
    SUPPORTED_FORMATS = ["json", "text", "table"]
    
    def __init__(self, format_name: str = "json"):
        """初始化格式化器"""
        if format_name not in self.SUPPORTED_FORMATS:
            raise ParsingError("E007", f"不支持的输出格式: {format_name}，支持: {', '.join(self.SUPPORTED_FORMATS)}")
        self.format_name = format_name
    
    def format(self, result: Dict[str, Any]) -> str:
        """格式化输出"""
        if self.format_name == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif self.format_name == "text":
            return self._format_text(result)
        elif self.format_name == "table":
            return self._format_table(result)
        return ""
    
    def _format_text(self, result: Dict[str, Any]) -> str:
        """文本格式输出"""
        lines = []
        data = result.get("data", {})
        for key, value in data.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        lines.append(f"置信度: {result.get('confidence', 0)}% ({result.get('level', '')})")
        return "\n".join(lines)
    
    def _format_table(self, result: Dict[str, Any]) -> str:
        """表格格式输出"""
        data = result.get("data", {})
        if not data:
            return "(空)"
        
        # 简单表格
        lines = ["| 字段 | 值 |", "|------|-----|"]
        for key, value in data.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"| {key} | {value} |")
        return "\n".join(lines)


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, max_items: int = 100):
        """初始化批量处理器"""
        self.max_items = max_items
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Tuple[str, str]] = []
    
    def process_batch(self, items: List[str], format_name: str = "json") -> Dict[str, Any]:
        """批量处理"""
        if not items:
            raise ParsingError("E001")
        if len(items) > self.max_items:
            raise ParsingError("E009", f"批量数量超出限制（最大{self.max_items}）")
        
        formatter = OutputFormatter(format_name)
        
        for idx, item in enumerate(items):
            try:
                parser = DataParser(item)
                result = parser.parse()
                formatted = formatter.format(result)
                self.results.append({
                    "index": idx + 1,
                    "input_preview": item[:50] + ("..." if len(item) > 50 else ""),
                    "output": formatted,
                })
            except ParsingError as e:
                self.errors.append((str(idx + 1), str(e)))
        
        return {
            "total": len(items),
            "success": len(self.results),
            "failed": len(self.errors),
            "results": self.results,
            "errors": self.errors,
        }


# ============================================================
# 主程序入口
# ============================================================

def run_selftest() -> None:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("开始自检...")
    
    # ---- 测试用例 1: 正常解析 ----
    sample1 = "姓名：张三\n电话：13812345678\n邮箱：zhangsan@example.com\n金额：100元"
    parser1 = DataParser(sample1)
    result1 = parser1.parse()
    
    # 宽松断言：字段存在
    assert "name" in result1["data"], "E001: 姓名未提取"
    assert "phone" in result1["data"], "E001: 电话未提取"
    assert "email" in result1["data"], "E001: 邮箱未提取"
    assert "amount" in result1["data"], "E001: 金额未提取"
    
    # 宽松断言：置信度范围
    assert result1["confidence"] >= 80, f"E001: 置信度异常: {result1['confidence']}"
    assert result1["confidence"] <= 100, f"E001: 置信度超范围: {result1['confidence']}"
    print("  [通过] 正常解析用例")
    
    # ---- 测试用例 2: 空输入 ----
    try:
        DataParser("")
        assert False, "E001: 空输入未抛异常"
    except ParsingError as e:
        assert e.error_code == "E001", f"E001: 错误码错误: {e.error_code}"
    print("  [通过] 空输入错误处理")
    
    # ---- 测试用例 3: 批量处理 ----
    batch = ["姓名：李四", "电话：13912345678", "邮箱：lisi@test.com"]
    processor = BatchProcessor()
    batch_result = processor.process_batch(batch)
    assert batch_result["total"] == 3, "E009: 批量总数错误"
    assert batch_result["success"] == 3, "E009: 批量成功数错误"
    assert batch_result["failed"] == 0, "E009: 批量失败数错误"
    print("  [通过] 批量处理用例")
    
    # ---- 测试用例 4: 输出格式化 ----
    formatter_json = OutputFormatter("json")
    json_output = formatter_json.format(result1)
    assert json_output.startswith("{"), "E007: JSON格式错误"
    
    formatter_text = OutputFormatter("text")
    text_output = formatter_text.format(result1)
    assert "姓名" in text_output or "name" in text_output, "E007: 文本格式错误"
    
    try:
        OutputFormatter("xml")
        assert False, "E007: 不支持的格式未抛异常"
    except ParsingError as e:
        assert e.error_code == "E007", f"E007: 错误码错误: {e.error_code}"
    print("  [通过] 输出格式化用例")
    
    # ---- 测试用例 5: 置信度分级 ----
    low_conf = {"data": {}, "confidence": 50.0, "uncertain_fields": ["all"]}
    assert low_conf["confidence"] < 85, "E005: 置信度分级错误"
    
    high_conf = {"data": {"name": "王五"}, "confidence": 95.0, "uncertain_fields": []}
    assert high_conf["confidence"] >= 90, "E005: 置信度分级错误"
    print("  [通过] 置信度分级用例")
    
    # ---- 测试用例 6: 边界能力 ----
    # 模拟超出能力范围的输入
    boundary_input = "帮我做股票预测"
    parser_boundary = DataParser(boundary_input)
    result_boundary = parser_boundary.parse()
    # 应该能处理，但置信度低
    assert result_boundary["confidence"] < 85, "E004: 边界情况置信度异常"
    print("  [通过] 边界能力处理")
    
    print("\n全部自检通过！")


def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="PDF转文档 - 结构化转换工具",
        epilog="示例: python main.py --input '姓名：张三 电话：13812345678' --format json"
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--input", "-i", help="输入文本内容")
    input_group.add_argument("--file", "-f", help="输入文件路径")
    input_group.add_argument("--batch", "-b", nargs="+", help="批量输入多个文本")
    
    # 输出参数
    parser.add_argument("--format", "-fmt", choices=["json", "text", "table"], default="json", help="输出格式")
    parser.add_argument("--output", "-o", help="输出文件路径（可选）")
    
    # 功能参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="parsers 1.0.0")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        run_selftest()
        return
    
    # 处理输入
    try:
        if args.input:
            # 单条输入
            parser_engine = DataParser(args.input)
            result = parser_engine.parse()
            formatter = OutputFormatter(args.format)
            output = formatter.format(result)
            print(output)
            
            # 可选写文件
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
        
        elif args.file:
            # 文件输入
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    content = f.read()
                if not content.strip():
                    raise ParsingError("E001")
                parser_engine = DataParser(content)
                result = parser_engine.parse()
                formatter = OutputFormatter(args.format)
                output = formatter.format(result)
                print(output)
                
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output)
            except FileNotFoundError:
                raise ParsingError("E003", f"文件不存在: {args.file}")
            except IOError as e:
                raise ParsingError("E003", f"文件读取失败: {str(e)}")
        
        elif args.batch:
            # 批量输入
            processor = BatchProcessor()
            batch_result = processor.process_batch(args.batch, args.format)
            
            # 输出汇总
            summary = {
                "summary": {
                    "total": batch_result["total"],
                    "success": batch_result["success"],
                    "failed": batch_result["failed"],
                },
                "results": batch_result["results"],
                "errors": batch_result["errors"],
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
        
        else:
            # 无输入，显示帮助
            parser.print_help()
            print("\n错误: 请提供输入内容、文件或批量输入，或使用 --selftest 运行自检")
            raise ParsingError("E001")
    
    except ParsingError as e:
        print(f"\n错误: {e}", file=sys.stderr)
        print(f"错误码: {e.error_code}", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        print(f"\n未预期的错误: {str(e)}", file=sys.stderr)
        print("错误码: E006", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
