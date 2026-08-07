#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-workspace-archive - 独立实现脚本
====================================
基于功能规格的 clean-room 实现，不包含任何外部依赖。
仅使用 Python 标准库。

功能概述：
    1. 将用户提供的输入（文本/文件/URL）转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

用法示例：
    python main.py --input "需要处理的文本内容"
    python main.py --file /path/to/file.txt
    python main.py --batch file1.txt file2.txt
    python main.py --selftest   # 离线自检
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要信息",
    "E003": "输入格式错误，请检查格式是否符合要求",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "批量处理中断，存在失败项",
    "E008": "参数冲突，请检查命令行参数",
    "E009": "输出写入失败，请检查输出路径",
    "E010": "内部处理异常，请重试或报告问题",
}

# ============================================================
# 数据模型
# ============================================================
@dataclass
class ProcessingResult:
    """处理结果数据模型"""
    status: str = "success"           # success / failed / partial
    confidence: float = 0.0            # 置信度 0-100
    data: Dict[str, Any] = field(default_factory=dict)  # 结构化数据
    warning: Optional[str] = None      # 警告信息
    error_code: Optional[str] = None   # 错误码
    error_message: Optional[str] = None # 错误信息
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# 核心处理引擎
# ============================================================
class ArchiveProcessor:
    """核心处理器：负责输入解析、结构化、置信度评估"""
    
    # 关键信息识别模式（用于从文本中提取结构化数据）
    KEY_PATTERNS = {
        "url": r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"(?:\+?86[- ]?)?1[3-9]\d{9}|(?:\+?\d{1,3}[- ]?)?\d{3,4}[- ]?\d{7,8}",
        "ip": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}",
        "name": r"(?:[\u4e00-\u9fa5]{2,4}|[A-Za-z]+(?: [A-Za-z]+){1,3})",
        "number": r"\d+(?:\.\d+)?",
    }
    
    def __init__(self):
        """初始化处理器"""
        self.supported_formats = ["json", "text", "table"]
        self.max_batch_size = 100  # 单次批量最大处理数量
    
    def process(self, content: str, output_format: str = "json", 
                completeness: str = "detailed") -> ProcessingResult:
        """
        核心处理流程：解析输入并生成结构化结果
        
        Args:
            content: 输入内容（文本）
            output_format: 输出格式（json/text/table）
            completeness: 完整度要求（quick/detailed）
            
        Returns:
            ProcessingResult: 处理结果
        """
        # ===== Step 1: 输入验证 =====
        if not content or not content.strip():
            return self._create_error("E001")
        
        # 检查输出格式是否支持
        if output_format not in self.supported_formats:
            return self._create_error("E003", 
                                     f"不支持的输出格式: {output_format}，"
                                     f"支持: {', '.join(self.supported_formats)}")
        
        # ===== Step 2: 解析输入内容 =====
        try:
            parsed = self._parse_input(content)
            
            # 检查是否提取到关键信息
            if not parsed["extracted_fields"]:
                return self._create_error("E002", 
                                         "未能从输入中识别出关键信息，"
                                         "请提供包含URL、邮箱、日期等可识别信息的文本")
            
            # ===== Step 3: 结构化处理 =====
            structured = self._structure_data(parsed)
            
            # ===== Step 4: 置信度评估 =====
            confidence = self._evaluate_confidence(parsed)
            
            # ===== Step 5: 生成结果 =====
            result = ProcessingResult(
                status="success",
                confidence=confidence,
                data=structured
            )
            
            # 添加置信度标注
            if confidence < 85:
                result.warning = "[需核实] 部分字段置信度较低，请人工复核"
            elif confidence < 90:
                result.warning = "建议复核：部分字段可能不够准确"
            
            # 按格式转换
            result.data["_formatted"] = self._format_output(structured, output_format)
            
            return result
            
        except Exception as e:
            return self._create_error("E010", str(e))
    
    def process_batch(self, items: List[str], output_format: str = "json") -> ProcessingResult:
        """
        批量处理多个输入
        
        Args:
            items: 输入列表
            output_format: 输出格式
            
        Returns:
            ProcessingResult: 批量处理结果
        """
        if not items:
            return self._create_error("E001", "批量输入列表为空")
        
        if len(items) > self.max_batch_size:
            return self._create_error("E008", 
                                     f"批量处理数量超过上限（{self.max_batch_size}），"
                                     f"请分批处理")
        
        results = []
        failed_count = 0
        
        for item in items:
            result = self.process(item, output_format)
            if result.status == "failed":
                failed_count += 1
            results.append(result)
        
        # 汇总结果
        summary = {
            "total": len(results),
            "success": len(results) - failed_count,
            "failed": failed_count,
            "items": [r.data if r.status == "success" else 
                     {"error": r.error_code, "message": r.error_message} 
                     for r in results]
        }
        
        status = "success" if failed_count == 0 else "partial"
        if failed_count == len(results):
            status = "failed"
            
        return ProcessingResult(
            status=status,
            confidence=sum(r.confidence for r in results) / max(len(results), 1),
            data=summary,
            error_code="E007" if failed_count > 0 else None,
            error_message="部分批次处理失败" if failed_count > 0 else None
        )
    
    def process_file(self, file_path: str, output_format: str = "json") -> ProcessingResult:
        """处理文件输入"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return self.process(content, output_format)
        except FileNotFoundError:
            return self._create_error("E006", f"文件不存在: {file_path}")
        except PermissionError:
            return self._create_error("E006", f"没有权限读取文件: {file_path}")
        except Exception as e:
            return self._create_error("E006", f"读取文件失败: {str(e)}")
    
    def _parse_input(self, content: str) -> Dict[str, Any]:
        """解析输入内容，提取关键信息"""
        extracted = {}
        
        # 对每种模式进行匹配
        for field_name, pattern in self.KEY_PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # 去重并保留顺序
                unique_matches = list(dict.fromkeys(matches))
                extracted[field_name] = unique_matches
        
        # 计算信息密度（非空白字符占比）
        non_blank_chars = len(re.sub(r'\s+', '', content))
        total_chars = len(content)
        info_density = (non_blank_chars / total_chars * 100) if total_chars > 0 else 0
        
        return {
            "raw_content": content,
            "content_length": len(content),
            "info_density": info_density,
            "extracted_fields": extracted,
            "field_count": len(extracted)
        }
    
    def _structure_data(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """将解析结果组织为结构化数据"""
        structure = {
            "summary": {
                "content_length": parsed["content_length"],
                "info_density": round(parsed["info_density"], 2),
                "identified_fields": parsed["field_count"]
            },
            "fields": {},
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "parser_version": "1.0.0"
            }
        }
        
        # 整理提取的字段
        for field_name, values in parsed["extracted_fields"].items():
            # 字段描述
            field_desc = {
                "count": len(values),
                "values": values[:10],  # 最多保留10个值
                "type": self._infer_field_type(field_name, values)
            }
            structure["fields"][field_name] = field_desc
        
        return structure
    
    def _infer_field_type(self, field_name: str, values: List[str]) -> str:
        """推断字段类型"""
        type_map = {
            "url": "string[url]",
            "email": "string[email]",
            "phone": "string[phone]",
            "ip": "string[ipv4]",
            "date": "string[date]",
            "name": "string[name]",
            "number": "number"
        }
        return type_map.get(field_name, "string")
    
    def _evaluate_confidence(self, parsed: Dict[str, Any]) -> float:
        """
        评估置信度（0-100）
        基于：字段数量、信息密度、内容长度
        """
        confidence = 0.0
        
        # 字段数量贡献（最多50分）
        field_count = parsed["field_count"]
        confidence += min(field_count * 10, 50)
        
        # 信息密度贡献（最多30分）
        info_density = parsed["info_density"]
        if info_density > 50:
            confidence += 30
        elif info_density > 30:
            confidence += 20
        elif info_density > 10:
            confidence += 10
        
        # 内容长度贡献（最多20分）
        content_length = parsed["content_length"]
        if content_length > 200:
            confidence += 20
        elif content_length > 100:
            confidence += 15
        elif content_length > 50:
            confidence += 10
        elif content_length > 10:
            confidence += 5
        
        # 确保在 0-100 范围内
        return max(0, min(100, confidence))
    
    def _format_output(self, data: Dict[str, Any], output_format: str) -> str:
        """按指定格式输出"""
        if output_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == "text":
            return self._format_as_text(data)
        elif output_format == "table":
            return self._format_as_table(data)
        else:
            return json.dumps(data, ensure_ascii=False)
    
    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """格式化为纯文本"""
        lines = []
        lines.append("=== 处理结果 ===")
        lines.append(f"内容长度: {data['summary']['content_length']}")
        lines.append(f"信息密度: {data['summary']['info_density']}%")
        lines.append(f"识别字段: {data['summary']['identified_fields']}")
        
        for field_name, field_data in data["fields"].items():
            lines.append(f"\n{field_name} ({field_data['type']}):")
            for value in field_data["values"][:5]:
                lines.append(f"  - {value}")
        
        return "\n".join(lines)
    
    def _format_as_table(self, data: Dict[str, Any]) -> str:
        """格式化为表格"""
        lines = []
        lines.append("| 字段 | 类型 | 数量 | 值预览 |")
        lines.append("|------|------|------|--------|")
        
        for field_name, field_data in data["fields"].items():
            values_preview = ", ".join(field_data["values"][:3])
            if len(field_data["values"]) > 3:
                values_preview += f"... (+{len(field_data['values']) - 3})"
            lines.append(f"| {field_name} | {field_data['type']} | "
                        f"{field_data['count']} | {values_preview} |")
        
        return "\n".join(lines)
    
    def _create_error(self, error_code: str, detail: Optional[str] = None) -> ProcessingResult:
        """创建错误结果"""
        message = ERROR_CODES.get(error_code, "未知错误")
        if detail:
            message = f"{message}。{detail}"
        
        return ProcessingResult(
            status="failed",
            confidence=0.0,
            error_code=error_code,
            error_message=message
        )


# ============================================================
# 自检模块
# ============================================================
class SelfTest:
    """内置自检功能：使用硬编码样例数据验证核心逻辑"""
    
    @staticmethod
    def run() -> bool:
        """运行自检，返回是否通过"""
        print("=" * 60)
        print("开始自检 (Self-Test)")
        print("=" * 60)
        
        processor = ArchiveProcessor()
        all_passed = True
        
        # ===== 测试用例 1: 标准输入处理 =====
        print("\n[测试 1] 标准输入处理")
        sample_text = """
        你好，我是张三，我的邮箱是zhangsan@example.com，
        个人网站是 https://www.zhangsan.com，电话是 13812345678。
        项目开始于 2024年3月15日，预计持续 90 天。
        服务器IP地址是 192.168.1.100。
        """
        
        result = processor.process(sample_text, "json")
        passed = result.status == "success"
        passed = passed and result.confidence > 50  # 宽松阈值
        passed = passed and len(result.data["fields"]) >= 3  # 至少识别3个字段
        print(f"  状态: {'通过' if passed else '失败'}")
        print(f"  置信度: {result.confidence:.1f}%")
        print(f"  识别字段: {list(result.data['fields'].keys())}")
        all_passed = all_passed and passed
        
        # ===== 测试用例 2: 空输入处理 =====
        print("\n[测试 2] 空输入处理")
        result = processor.process("", "json")
        passed = result.status == "failed" and result.error_code == "E001"
        print(f"  状态: {'通过' if passed else '失败'}")
        print(f"  错误码: {result.error_code}, 消息: {result.error_message}")
        all_passed = all_passed and passed
        
        # ===== 测试用例 3: 批量处理 =====
        print("\n[测试 3] 批量处理")
        batch_items = [
            "联系邮箱是 test@test.com, 网站是 https://test.com",
            "电话 13912345678, 日期 2024-01-01",
            "IP 10.0.0.1"
        ]
        result = processor.process_batch(batch_items, "json")
        passed = result.status == "success" and result.data["total"] == 3
        passed = passed and result.data["success"] == 3
        print(f"  状态: {'通过' if passed else '失败'}")
        print(f"  总数: {result.data['total']}, 成功: {result.data['success']}")
        all_passed = all_passed and passed
        
        # ===== 测试用例 4: 文件处理（使用临时文件） =====
        print("\n[测试 4] 文件处理")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', 
                                        delete=False, encoding='utf-8') as f:
            f.write("测试文件内容，邮箱 test@file.com，网站 https://file.example.com")
            temp_path = f.name
        
        try:
            result = processor.process_file(temp_path, "json")
            passed = result.status == "success" and result.confidence > 0
            print(f"  状态: {'通过' if passed else '失败'}")
            print(f"  置信度: {result.confidence:.1f}%")
            all_passed = all_passed and passed
        finally:
            os.unlink(temp_path)
        
        # ===== 测试用例 5: 输出格式 =====
        print("\n[测试 5] 输出格式")
        sample_short = "邮箱 test@format.com"
        formats_ok = True
        for fmt in ["json", "text", "table"]:
            result = processor.process(sample_short, fmt)
            fmt_passed = result.status == "success" and result.data["_formatted"]
            formats_ok = formats_ok and fmt_passed
            print(f"  格式 {fmt}: {'通过' if fmt_passed else '失败'}")
        all_passed = all_passed and formats_ok
        
        # ===== 测试用例 6: 错误处理 =====
        print("\n[测试 6] 错误处理")
        # 不支持的格式
        result = processor.process("test content", "xml")
        passed = result.status == "failed" and result.error_code == "E003"
        print(f"  不支持格式: {'通过' if passed else '失败'}")
        all_passed = all_passed and passed
        
        # 不存在的文件
        result = processor.process_file("/nonexistent/path/file.txt", "json")
        passed = result.status == "failed" and result.error_code == "E006"
        print(f"  不存在文件: {'通过' if passed else '失败'}")
        all_passed = all_passed and passed
        
        # ===== 汇总 =====
        print("\n" + "=" * 60)
        if all_passed:
            print("自检通过: 所有测试用例均通过 ✓")
        else:
            print("自检失败: 存在未通过的测试用例 ✗")
        print("=" * 60)
        
        return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="ai-workspace-archive - 结构化信息处理工具",
        epilog="示例: python main.py --input '需要处理的文本' --format json"
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", "-i", type=str, help="输入文本内容")
    input_group.add_argument("--file", "-f", type=str, help="输入文件路径")
    input_group.add_argument("--batch", "-b", nargs="+", type=str, 
                            help="批量输入多个文本")
    input_group.add_argument("--selftest", action="store_true",
                            help="运行内置自检（无需外部输入）")
    
    # 输出参数
    parser.add_argument("--format", "-fmt", type=str, default="json",
                       choices=["json", "text", "table"],
                       help="输出格式 (默认: json)")
    parser.add_argument("--completeness", "-c", type=str, default="detailed",
                       choices=["quick", "detailed"],
                       help="完整度要求 (默认: detailed)")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（可选）")
    
    args = parser.parse_args()
    
    # ===== 自检模式 =====
    if args.selftest:
        success = SelfTest.run()
        sys.exit(0 if success else 1)
    
    # ===== 验证输入参数 =====
    if not args.input and not args.file and not args.batch:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        print("请使用 --input, --file 或 --batch 提供输入内容", file=sys.stderr)
        print("或使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)
    
    # ===== 创建处理器 =====
    processor = ArchiveProcessor()
    
    # ===== 执行处理 =====
    try:
        if args.input:
            result = processor.process(args.input, args.format, args.completeness)
        elif args.file:
            result = processor.process_file(args.file, args.format)
        elif args.batch:
            result = processor.process_batch(args.batch, args.format)
        else:
            # 理论上不会到这里
            result = processor._create_error("E001")
        
        # ===== 输出结果 =====
        if result.status == "failed":
            print(f"处理失败 [{result.error_code}]: {result.error_message}", 
                  file=sys.stderr)
            sys.exit(1)
        
        # 输出结果
        output_text = result.data.get("_formatted", 
                                     json.dumps(result.data, ensure_ascii=False, indent=2))
        
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"结果已保存到: {args.output}")
            except Exception as e:
                print(f"错误 E009: {ERROR_CODES['E009']}: {str(e)}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output_text)
        
        # 输出置信度和警告
        print(f"\n--- 置信度: {result.confidence:.1f}% ---")
        if result.warning:
            print(f"⚠ {result.warning}")
        
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误 E010: {ERROR_CODES['E010']}: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
