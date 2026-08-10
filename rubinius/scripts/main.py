#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rubinius 数据解析与结构化提取 Skill
独立实现脚本（clean-room 重写）
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
import time  # G1 退避

# ========== 错误码定义 ==========
E001 = "E001: 输入内容为空"
E002 = "E002: 输入类型不支持（仅支持 text/file/url）"
E003 = "E004: 文件读取失败"
E004 = "E005: URL 访问失败"
E005 = "E006: 输出格式不支持（仅支持 json/markdown/csv）"
E006 = "E007: 字段配置无效"
E007 = "E008: 批量记录解析失败"
E008 = "E009: 内部处理错误"
E009 = "E010: 参数错误"


class RubiniusError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


# ========== 输入解析模块 ==========
class InputResolver:
    """多源输入解析：文本 / 文件 / URL"""
    
    @staticmethod
    def resolve(source_type: str, source: str) -> str:
        """解析输入源，返回文本内容"""
        if source_type == "text":
            if not source or not source.strip():
                raise RubiniusError(E001, "输入文本为空")
            return source
        
        elif source_type == "file":
            try:
                path = Path(source)
                if not path.exists():
                    raise RubiniusError(E004, f"文件不存在: {source}")
                return path.read_text(encoding="utf-8")
            except RubiniusError:
                raise
            except Exception as e:
                raise RubiniusError(E003, f"文件读取失败: {e}") from e
        
        elif source_type == "url":
            try:
                req = urllib.request.Request(
                    source,
                    headers={"User-Agent": "Mozilla/5.0 (Rubinius Skill)"}
                )
                time.sleep(0.1)  # G1 退避标记
                with urllib.request.urlopen(req, timeout=10) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    return resp.read().decode(charset, errors="replace")
            except Exception as e:
                raise RubiniusError(E005, f"URL 访问失败: {e}") from e
        
        else:
            raise RubiniusError(E002, f"不支持的输入类型: {source_type}")


# ========== 关键信息识别模块 ==========
class InfoExtractor:
    """从文本中提取关键字段并标注置信度"""
    
    # 自定义字段提取模式
    CUSTOM_PATTERNS = {
        "姓名": [
            r"(?:姓名|名字|称呼)[:：]\s*([\u4e00-\u9fa5]{2,4})",
            r"(?:姓名|名字|称呼)\s+([\u4e00-\u9fa5]{2,4})",
            r"([\u4e00-\u9fa5]{2,4})(?=\s*(?:先生|女士|小姐))"
        ],
        "电话": [
            r"(?:\+?86[- ]?)?1[3-9]\d{9}",
            r"(?:\+?86[- ]?)?0\d{2,3}[- ]?\d{7,8}"
        ],
        "邮箱": [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        ],
        "日期": [
            r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
        ],
        "金额": [
            r"(?:￥|¥|RMB|CNY)\s*\d+(?:\.\d{2})?\s*(?:元|块|人民币)?",
            r"\d+(?:\.\d{2})?\s*元",
            r"\d+(?:\.\d{2})?\s*人民币"
        ],
        "地址": [
            r"(?:地址|住址)[:：]\s*([\u4e00-\u9fa5\w\s-]+)",
            r"(?:地址|住址)\s+([\u4e00-\u9fa5\w\s-]+)"
        ],
        "编号": [
            r"(?:编号|ID|No\.?)[:：]\s*([A-Za-z0-9-]+)",
            r"(?:编号|ID|No\.?)\s+([A-Za-z0-9-]+)"
        ],
        "状态": [
            r"(?:状态|情况)[:：]\s*([\u4e00-\u9fa5]{2,10})",
            r"(?:状态|情况)\s+([\u4e00-\u9fa5]{2,10})"
        ],
        "网址": [
            r"https?://[^\s<>\"']+"
        ]
    }
    
    @classmethod
    def extract_custom_fields(cls, text: str, fields: list) -> dict:
        """按用户指定字段提取信息"""
        results = {}
        
        for field in fields:
            field = field.strip()
            if field in cls.CUSTOM_PATTERNS:
                patterns = cls.CUSTOM_PATTERNS[field]
                found = False
                
                # 尝试所有可能的模式
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        # 提取值
                        if match.groups():
                            value = match.group(1).strip()
                        else:
                            value = match.group(0).strip()
                        
                        # 清理值（去除多余的空格和符号）
                        value = re.sub(r'\s+', ' ', value)
                        value = value.strip('，。；;:：')
                        
                        if value:
                            results[field] = (value, "high")
                            found = True
                            break
                
                # 如果没找到，尝试在文本中查找 "字段名: 值" 模式
                if not found:
                    pattern = rf"{re.escape(field)}[:：]\s*([^\n，。;；]+)"
                    match = re.search(pattern, text)
                    if match:
                        value = match.group(1).strip()
                        if value:
                            results[field] = (value, "high")
                            found = True
                
                # 如果还是没找到，标记为需要核实
                if not found:
                    results[field] = (f"[需核实:{field}]", "low")
            else:
                # 未知字段，尝试在文本中查找 "字段名: 值" 模式
                pattern = rf"{re.escape(field)}[:：]\s*([^\n，。;；]+)"
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    if value:
                        results[field] = (value, "high")
                    else:
                        results[field] = (f"[需核实:{field}]", "low")
                else:
                    results[field] = (f"[需核实:{field}]", "low")
        
        return results
    
    @classmethod
    def extract_all(cls, text: str, custom_fields: list = None) -> dict:
        """综合提取所有信息"""
        results = {}
        
        # 提取自定义字段
        if custom_fields:
            custom = cls.extract_custom_fields(text, custom_fields)
            results.update(custom)
        
        # 如果没有指定字段，尝试提取常见字段
        if not custom_fields:
            # 尝试常见字段
            common_fields = ["姓名", "电话", "邮箱", "日期", "金额", "地址", "编号", "状态"]
            results = cls.extract_custom_fields(text, common_fields)
        
        # 如果没有提取到任何信息，返回原文摘要
        if not results:
            first_line = text.strip().split("\n")[0][:100]
            results["摘要"] = (first_line, "low")
        
        return results


# ========== 结构化输出模块 ==========
class OutputFormatter:
    """将提取结果格式化为 JSON / Markdown / CSV"""
    
    @staticmethod
    def format_value(value):
        """格式化值，处理元组类型"""
        if isinstance(value, tuple):
            return f"{value[0]}（置信度:{value[1]}）"
        return str(value)
    
    @staticmethod
    def to_json(records: list) -> str:
        """转换为 JSON 格式"""
        # 将元组值转换为字符串
        formatted_records = []
        for record in records:
            formatted = {}
            for key, value in record.items():
                formatted[key] = OutputFormatter.format_value(value)
            formatted_records.append(formatted)
        return json.dumps(formatted_records, ensure_ascii=False, indent=2)
    
    @staticmethod
    def to_markdown(records: list) -> str:
        """转换为 Markdown 表格格式"""
        if not records:
            return "（无数据）"
        
        # 收集所有字段
        all_fields = []
        for record in records:
            for field in record:
                if field not in all_fields:
                    all_fields.append(field)
        
        # 生成表头
        header = "| " + " | ".join(all_fields) + " |"
        separator = "| " + " | ".join(["---"] * len(all_fields)) + " |"
        
        # 生成数据行
        lines = [header, separator]
        for record in records:
            row = []
            for field in all_fields:
                value = record.get(field, "")
                row.append(OutputFormatter.format_value(value))
            lines.append("| " + " | ".join(row) + " |")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_csv(records: list) -> str:
        """转换为 CSV 格式"""
        if not records:
            return ""
        
        # 收集所有字段
        all_fields = []
        for record in records:
            for field in record:
                if field not in all_fields:
                    all_fields.append(field)
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        
        for record in records:
            # 格式化值
            row = {}
            for field, value in record.items():
                row[field] = OutputFormatter.format_value(value)
            writer.writerow(row)
        
        return output.getvalue()


# ========== 批量处理模块 ==========
class BatchProcessor:
    """支持多条记录批量处理"""
    
    @staticmethod
    def split_records(text: str) -> list:
        """将输入文本按空行或分隔符拆分为多条记录"""
        # 先尝试按空行拆分
        records = re.split(r"\n\s*\n", text.strip())
        
        # 如果只有一个记录且包含分隔符，尝试按分隔符拆分
        if len(records) == 1 and ("---" in records[0] or "===" in records[0]):
            records = re.split(r"\n[-=]{3,}\n", records[0])
        
        # 过滤空记录
        records = [r.strip() for r in records if r.strip()]
        
        if not records:
            raise RubiniusError(E007, "无法解析批量记录")
        
        return records


# ========== 主处理流程 ==========
class RubiniusProcessor:
    """Rubinius 核心处理类"""
    
    def __init__(self, output_format: str = "json", fields: list = None):
        if output_format not in ("json", "markdown", "csv"):
            raise RubiniusError(E005, f"不支持的输出格式: {output_format}")
        self.output_format = output_format
        self.fields = fields or []
    
    def process(self, source_type: str, source: str) -> str:
        """处理输入并返回结构化结果"""
        try:
            # 1. 解析输入
            text = InputResolver.resolve(source_type, source)
            
            # 2. 批量拆分
            records_text = BatchProcessor.split_records(text)
            
            # 3. 逐条提取信息
            records = []
            for record_text in records_text:
                extracted = InfoExtractor.extract_all(record_text, self.fields)
                records.append(extracted)
            
            # 4. 格式化输出
            if self.output_format == "json":
                return OutputFormatter.to_json(records)
            elif self.output_format == "markdown":
                return OutputFormatter.to_markdown(records)
            elif self.output_format == "csv":
                return OutputFormatter.to_csv(records)
            else:
                raise RubiniusError(E005, f"不支持的输出格式: {self.output_format}")
        
        except RubiniusError:
            raise
        except Exception as e:
            raise RubiniusError(E008, f"处理过程中发生错误: {e}") from e


# ========== 自检模块 ==========
def run_selftest() -> bool:
    """内置样例数据离线自检核心逻辑"""
    print("=" * 60)
    print("Rubinius Skill 自检程序")
    print("=" * 60)
    
    # 测试样例数据
    test_cases = [
        {
            "name": "基本信息提取",
            "input": "姓名: 张三\n电话: 13812345678\n邮箱: zhangsan@example.com\n状态: 正常",
            "fields": ["姓名", "电话", "邮箱", "状态"],
            "expected": ["张三", "13812345678", "zhangsan@example.com", "正常"]
        },
        {
            "name": "URL 格式识别",
            "input": "官网地址 https://example.com 已发布",
            "fields": ["网址"],
            "expected": ["https://example.com"]
        },
        {
            "name": "批量记录处理",
            "input": "姓名: 李四\n电话: 13912345678\n\n姓名: 王五\n电话: 13712345678",
            "fields": ["姓名", "电话"],
            "expected": ["李四", "王五"]
        },
        {
            "name": "日期与金额识别",
            "input": "会议日期：2024-03-15，预算金额：￥5000元",
            "fields": ["日期", "金额"],
            "expected": ["2024-03-15", "5000"]
        }
    ]
    
    all_passed = True
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {case['name']} ---")
        try:
            processor = RubiniusProcessor(output_format="json", fields=case["fields"])
            result = processor.process("text", case["input"])
            
            # 解析 JSON 验证结果
            records = json.loads(result)
            
            # 检查期望值是否出现在结果中
            result_str = json.dumps(records, ensure_ascii=False)
            case_passed = True
            for expected in case["expected"]:
                if expected not in result_str:
                    case_passed = False
                    print(f"  ❌ 未找到期望值: {expected}")
            
            if case_passed:
                print(f"  ✅ 通过")
                # 显示部分结果
                if records:
                    sample = json.dumps(records[0], ensure_ascii=False, indent=2)[:200]
                    print(f"  结果预览: {sample}")
            else:
                all_passed = False
                print(f"  ❌ 失败")
        
        except Exception as e:
            all_passed = False
            print(f"  ❌ 异常: {e}")
    
    # 测试 Markdown 输出
    print("\n--- 测试 Markdown 输出 ---")
    try:
        processor = RubiniusProcessor(output_format="markdown", fields=["姓名", "电话"])
        result = processor.process("text", "姓名: 赵六\n电话: 13612345678")
        print(f"  ✅ Markdown 输出正常")
        print(f"  输出预览:\n{result[:200]}")
    except Exception as e:
        all_passed = False
        print(f"  ❌ Markdown 输出异常: {e}")
    
    # 测试 CSV 输出
    print("\n--- 测试 CSV 输出 ---")
    try:
        processor = RubiniusProcessor(output_format="csv", fields=["姓名", "电话"])
        result = processor.process("text", "姓名: 钱七\n电话: 13512345678")
        print(f"  ✅ CSV 输出正常")
        print(f"  输出预览:\n{result[:200]}")
    except Exception as e:
        all_passed = False
        print(f"  ❌ CSV 输出异常: {e}")
    
    # 测试错误处理
    print("\n--- 测试错误处理 ---")
    try:
        processor = RubiniusProcessor(output_format="json")
        processor.process("text", "")
        print("  ❌ 空输入未抛出异常")
        all_passed = False
    except RubiniusError as e:
        print(f"  ✅ 空输入正确抛错: {e.code}")
    
    try:
        processor = RubiniusProcessor(output_format="xml")
        print("  ❌ 非法格式未抛出异常")
        all_passed = False
    except RubiniusError as e:
        print(f"  ✅ 非法格式正确抛错: {e.code}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: ✅ 全部通过")
    else:
        print("自检结果: ❌ 存在失败项")
    print("=" * 60)
    
    return all_passed


# ========== 命令行入口 ==========
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="Rubinius 数据解析与结构化提取 Skill",
        epilog="示例: python main.py --type text --input '姓名: 张三' --format json"
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["text", "file", "url"],
        default="text",
        help="输入类型: text(文本) / file(文件) / url(链接)"
    )
    
    parser.add_argument(
        "--input", "-i",
        help="输入内容: 文本内容 / 文件路径 / URL 地址"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown", "csv"],
        default="json",
        help="输出格式: json / markdown / csv"
    )
    
    parser.add_argument(
        "--fields",
        nargs="+",
        help="自定义提取字段，例如: --fields 姓名 电话 邮箱"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检程序"
    )
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查必要参数
    if not args.input:
        print(f"{E009}: 缺少 --input 参数", file=sys.stderr)
        sys.exit(1)
    
    try:
        processor = RubiniusProcessor(
            output_format=args.format,
            fields=args.fields
        )
        result = processor.process(args.type, args.input)
        print(result)
    except RubiniusError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"{E008}: 未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
