#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec-kit 规格驱动开发工具 - 独立实现脚本

功能：将需求数据/文件/URL转化为结构化规格结果，支持批量与自定义格式。
本脚本为 clean-room 实现，仅依据功能规格文档重新编写。
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入参数无效或缺失",
    "E002": "文件不存在或无法读取",
    "E003": "URL 无法访问或下载失败",
    "E004": "输入数据格式无法解析",
    "E005": "批量条目超过限制",
    "E006": "输出格式不支持",
    "E007": "字段映射配置错误",
    "E008": "排序规则配置错误",
    "E009": "内部处理逻辑错误",
    "E010": "未知错误",
}

# 版本信息
VERSION = "1.0.1"
MAX_BATCH_SIZE = 50  # 最大批量条目数


class SpecKitError(Exception):
    """规格工具自定义异常"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


class InputParser:
    """输入解析器 - 处理文本、文件、URL 三种输入来源"""
    
    @staticmethod
    def parse_text(text: str) -> List[Dict[str, Any]]:
        """解析纯文本数据，识别关键字段"""
        if not text or not text.strip():
            raise SpecKitError("E001", "输入文本为空")
        
        items = []
        # 按空行或换行分割为条目
        raw_entries = [e.strip() for e in re.split(r'\n\s*\n|\n(?=\d+[.、)])', text) if e.strip()]
        
        for entry in raw_entries:
            item = InputParser._extract_fields(entry)
            if item:
                items.append(item)
        
        if not items:
            raise SpecKitError("E004", "无法从文本中提取有效字段")
        return items
    
    @staticmethod
    def _extract_fields(text: str) -> Dict[str, Any]:
        """从单条文本中提取结构化字段"""
        item: Dict[str, Any] = {}
        
        # 提取标题（通常是第一行或包含冒号的键值对中的键）
        lines = text.split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # 尝试识别键值对格式
        kv_pattern = re.compile(r'^([^:：]{1,30})[：:]\s*(.+)$')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = kv_pattern.match(line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                item[key] = value
        
        # 如果没有键值对，则整段作为描述
        if not item:
            item["描述"] = first_line or text[:100]
        
        # 提取日期（常见格式）
        date_pattern = re.compile(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)')
        date_match = date_pattern.search(text)
        if date_match and "日期" not in item:
            item["日期"] = date_match.group(1)
        
        # 提取数字/金额
        num_pattern = re.compile(r'(\d+(?:\.\d+)?)')
        nums = num_pattern.findall(text)
        if nums and "数量" not in item and len(nums) <= 3:
            item["数值"] = float(nums[0]) if '.' in nums[0] else int(nums[0])
        
        return item
    
    @staticmethod
    def parse_file(filepath: str) -> List[Dict[str, Any]]:
        """解析本地文件"""
        if not os.path.isfile(filepath):
            raise SpecKitError("E002", f"文件不存在: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return InputParser.parse_text(content)
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    content = f.read()
                return InputParser.parse_text(content)
            except Exception as e:
                raise SpecKitError("E002", f"文件读取失败: {e}")
        except Exception as e:
            raise SpecKitError("E002", f"文件读取失败: {e}")
    
    @staticmethod
    def parse_url(url: str) -> List[Dict[str, Any]]:
        """从 URL 获取内容并解析"""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')
            return InputParser.parse_text(content)
        except Exception as e:
            raise SpecKitError("E003", f"URL 访问失败: {e}")


class FieldMapper:
    """字段映射器 - 支持自定义字段结构"""
    
    DEFAULT_FIELDS = ["描述", "日期", "数值"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.field_map = self.config.get("field_map", {})
        self.aliases = self.config.get("aliases", {})
    
    def apply(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用字段映射配置"""
        if not self.field_map:
            return items
        
        mapped_items = []
        for item in items:
            new_item = {}
            for target_field, source_field in self.field_map.items():
                # 支持别名映射
                source = self.aliases.get(source_field, source_field)
                if source in item:
                    new_item[target_field] = item[source]
                else:
                    # 尝试模糊匹配
                    matched = self._fuzzy_match(item, source)
                    if matched is not None:
                        new_item[target_field] = matched
            mapped_items.append(new_item)
        
        return mapped_items if mapped_items else items
    
    @staticmethod
    def _fuzzy_match(item: Dict[str, Any], keyword: str) -> Any:
        """模糊匹配字段名"""
        keyword_lower = keyword.lower()
        for key, value in item.items():
            if keyword_lower in key.lower() or key.lower() in keyword_lower:
                return value
        return None


class OutputFormatter:
    """输出格式化器 - 支持 JSON、YAML、Markdown、CSV"""
    
    @staticmethod
    def format(items: List[Dict[str, Any]], fmt: str, sort_rules: Optional[List[str]] = None) -> str:
        """格式化输出"""
        if sort_rules:
            items = OutputFormatter._apply_sort(items, sort_rules)
        
        fmt = fmt.lower()
        if fmt == "json":
            return OutputFormatter._to_json(items)
        elif fmt == "yaml":
            return OutputFormatter._to_yaml(items)
        elif fmt == "md" or fmt == "markdown":
            return OutputFormatter._to_markdown(items)
        elif fmt == "csv":
            return OutputFormatter._to_csv(items)
        else:
            raise SpecKitError("E006", f"不支持的输出格式: {fmt}")
    
    @staticmethod
    def _apply_sort(items: List[Dict[str, Any]], rules: List[str]) -> List[Dict[str, Any]]:
        """应用排序规则"""
        try:
            sort_key = rules[0] if rules else "描述"
            reverse = len(rules) > 1 and rules[1].lower() in ("desc", "descend", "降序")
            
            def sort_func(item: Dict[str, Any]) -> Any:
                value = item.get(sort_key, "")
                # 尝试数值排序
                if isinstance(value, (int, float)):
                    return value
                return str(value)
            
            return sorted(items, key=sort_func, reverse=reverse)
        except Exception as e:
            raise SpecKitError("E008", f"排序失败: {e}")
    
    @staticmethod
    def _to_json(items: List[Dict[str, Any]]) -> str:
        """转换为 JSON"""
        try:
            return json.dumps(items, ensure_ascii=False, indent=2)
        except Exception as e:
            raise SpecKitError("E009", f"JSON 序列化失败: {e}")
    
    @staticmethod
    def _to_yaml(items: List[Dict[str, Any]]) -> str:
        """转换为 YAML（简单实现）"""
        lines = []
        for idx, item in enumerate(items, 1):
            lines.append(f"- id: {idx}")
            for key, value in item.items():
                if isinstance(value, str):
                    lines.append(f"  {key}: \"{value}\"")
                else:
                    lines.append(f"  {key}: {value}")
        return "\n".join(lines)
    
    @staticmethod
    def _to_markdown(items: List[Dict[str, Any]]) -> str:
        """转换为 Markdown 表格"""
        if not items:
            return "**无数据**"
        
        # 收集所有字段
        all_keys = []
        for item in items:
            for key in item.keys():
                if key not in all_keys:
                    all_keys.append(key)
        
        # 生成表头
        header = "| " + " | ".join(all_keys) + " |"
        separator = "| " + " | ".join(["---"] * len(all_keys)) + " |"
        
        # 生成数据行
        rows = []
        for item in items:
            row = []
            for key in all_keys:
                value = item.get(key, "")
                row.append(str(value))
            rows.append("| " + " | ".join(row) + " |")
        
        return "\n".join([header, separator] + rows)
    
    @staticmethod
    def _to_csv(items: List[Dict[str, Any]]) -> str:
        """转换为 CSV"""
        if not items:
            return ""
        
        all_keys = []
        for item in items:
            for key in item.keys():
                if key not in all_keys:
                    all_keys.append(key)
        
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(items)
        return output.getvalue()


class SpecKitProcessor:
    """核心处理器 - 协调各组件完成规格化处理"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.parser = InputParser()
        self.mapper = FieldMapper(self.config)
        self.formatter = OutputFormatter()
    
    def process(self, source: str, source_type: str = "text", 
                output_format: str = "json", 
                sort_rules: Optional[List[str]] = None) -> str:
        """处理入口"""
        try:
            # 1. 解析输入
            if source_type == "text":
                items = self.parser.parse_text(source)
            elif source_type == "file":
                items = self.parser.parse_file(source)
            elif source_type == "url":
                items = self.parser.parse_url(source)
            else:
                raise SpecKitError("E001", f"未知输入类型: {source_type}")
            
            # 2. 批量限制检查
            if len(items) > MAX_BATCH_SIZE:
                raise SpecKitError("E005", f"批量条目 {len(items)} 超过上限 {MAX_BATCH_SIZE}")
            
            # 3. 字段映射
            items = self.mapper.apply(items)
            
            # 4. 格式化输出
            result = self.formatter.format(items, output_format, sort_rules)
            return result
            
        except SpecKitError:
            raise
        except Exception as e:
            raise SpecKitError("E010", f"处理失败: {e}")


def run_selftest() -> bool:
    """内置自检函数 - 使用硬编码样例数据验证核心逻辑"""
    print("=" * 60)
    print("spec-kit 自检程序 v" + VERSION)
    print("=" * 60)
    
    # 测试数据 - 硬编码，不依赖外部文件
    test_text = """
    需求1：用户登录功能
    描述: 实现用户登录验证
    日期: 2026-03-15
    优先级: 高

    需求2：数据导出
    描述: 支持导出为 CSV 格式
    日期: 2026-04-01
    优先级: 中

    需求3：报表生成
    描述: 自动生成月度报表
    日期: 2026-05-20
    优先级: 低
    """
    
    tests_passed = 0
    total_tests = 5
    
    try:
        # 测试1: 文本解析
        print("\n[测试1] 文本解析...")
        parser = InputParser()
        items = parser.parse_text(test_text)
        assert len(items) >= 3, f"期望至少3个条目，实际 {len(items)}"
        assert any("描述" in item for item in items), "未提取到描述字段"
        print(f"  ✓ 解析成功，共 {len(items)} 个条目")
        tests_passed += 1
        
        # 测试2: 字段映射
        print("\n[测试2] 字段映射...")
        config = {
            "field_map": {
                "title": "描述",
                "date": "日期"
            }
        }
        mapper = FieldMapper(config)
        mapped_items = mapper.apply(items)
        assert len(mapped_items) >= 1, "映射结果为空"
        assert any("title" in item for item in mapped_items), "映射字段 title 缺失"
        print("  ✓ 字段映射成功")
        tests_passed += 1
        
        # 测试3: JSON 输出
        print("\n[测试3] JSON 输出...")
        formatter = OutputFormatter()
        json_output = formatter.format(items, "json")
        parsed = json.loads(json_output)
        assert isinstance(parsed, list), "JSON 输出不是列表"
        assert len(parsed) >= 3, f"JSON 条目数不足: {len(parsed)}"
        print(f"  ✓ JSON 输出有效，{len(parsed)} 条记录")
        tests_passed += 1
        
        # 测试4: Markdown 输出
        print("\n[测试4] Markdown 输出...")
        md_output = formatter.format(items, "md")
        assert "|" in md_output, "Markdown 表格格式错误"
        assert "---" in md_output, "Markdown 分隔线缺失"
        print("  ✓ Markdown 表格生成成功")
        tests_passed += 1
        
        # 测试5: 完整处理流程
        print("\n[测试5] 完整处理流程...")
        processor = SpecKitProcessor()
        result = processor.process(test_text, "text", "json", ["描述"])
        assert result, "处理结果为空"
        assert json.loads(result), "处理结果不是有效 JSON"
        print("  ✓ 完整流程执行成功")
        tests_passed += 1
        
        # 汇总结果
        print("\n" + "=" * 60)
        print(f"自检完成: {tests_passed}/{total_tests} 项测试通过")
        print("=" * 60)
        return tests_passed == total_tests
        
    except AssertionError as e:
        print(f"\n✗ 自检失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 自检异常: {e}")
        return False


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="spec-kit 规格驱动开发工具 v" + VERSION,
        epilog="示例: python main.py --text '需求描述' --format json"
    )
    
    parser.add_argument("--text", type=str, help="直接输入文本数据")
    parser.add_argument("--file", type=str, help="输入文件路径")
    parser.add_argument("--url", type=str, help="输入 URL 链接")
    parser.add_argument("--format", type=str, default="json", 
                        choices=["json", "yaml", "md", "markdown", "csv"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--sort", type=str, nargs="*", 
                        help="排序规则，如: --sort 描述 desc")
    parser.add_argument("--field-map", type=str,
                        help="字段映射配置 (JSON格式)，如: '{\"title\":\"描述\"}'")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检程序")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 检查输入源
    input_sources = sum([
        1 if args.text else 0,
        1 if args.file else 0,
        1 if args.url else 0
    ])
    
    if input_sources == 0:
        parser.error("必须指定输入源: --text, --file 或 --url")
        return 1
    if input_sources > 1:
        parser.error("只能指定一种输入源")
        return 1
    
    # 构建配置
    config = {}
    if args.field_map:
        try:
            config["field_map"] = json.loads(args.field_map)
        except json.JSONDecodeError:
            print("错误: 字段映射配置不是有效的 JSON")
            return 1
    
    try:
        processor = SpecKitProcessor(config)
        
        # 确定输入源
        if args.text:
            result = processor.process(args.text, "text", args.format, args.sort)
        elif args.file:
            result = processor.process(args.file, "file", args.format, args.sort)
        else:
            result = processor.process(args.url, "url", args.format, args.sort)
        
        # 输出结果
        print(result)
        return 0
        
    except SpecKitError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
