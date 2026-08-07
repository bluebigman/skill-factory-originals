#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anime-dl 爬虫采集工具 - 独立实现脚本
=====================================
本脚本依据功能规格独立开发，用于将用户提供的数据/文件/URL 转换为结构化结果。
支持批量处理、自定义格式、置信度标注和错误码体系。

用法:
    python main.py --selftest          # 运行内置自检
    python main.py --input "文本"       # 处理输入
    python main.py --batch file.txt    # 批量处理文件
    python main.py --format json       # 指定输出格式
"""

import sys
import os
import json
import argparse
import hashlib
from datetime import datetime
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
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "批量处理中断，存在未完成的任务",
    "E008": "输出格式不支持",
    "E009": "内部处理异常",
    "E010": "参数错误",
}


class AnimeDLError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

class DataProcessor:
    """数据处理核心类"""
    
    # 关键字段识别规则
    KEY_FIELDS = {
        "url": ["http", "https", "www", ".com", ".org", ".net"],
        "email": ["@", ".com", ".org"],
        "phone": ["+", "tel:", "phone"],
        "date": ["20", "19", "-", "/", "."],
        "name": ["name", "标题", "名称"],
        "id": ["id", "编号", "序号"],
    }
    
    def __init__(self):
        self.processed_count = 0
        self.confidence_threshold = 0.85
    
    def process_input(self, input_data: str, output_format: str = "json") -> Dict[str, Any]:
        """
        处理输入数据，转换为结构化结果
        
        参数:
            input_data: 用户提供的原始数据
            output_format: 输出格式 (json/text/csv)
            
        返回:
            结构化结果字典
        """
        # 输入校验
        if not input_data or not input_data.strip():
            raise AnimeDLError("E001")
        
        if output_format not in ["json", "text", "csv"]:
            raise AnimeDLError("E008")
        
        # 解析输入
        parsed_data = self._parse_input(input_data)
        
        # 识别关键信息
        key_info = self._extract_key_info(parsed_data)
        
        # 计算置信度
        confidence = self._calculate_confidence(key_info)
        
        # 构建输出
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "input_type": self._detect_input_type(input_data),
            "key_info": key_info,
            "confidence": round(confidence, 2),
            "confidence_label": self._get_confidence_label(confidence),
            "processed_count": self.processed_count,
        }
        
        self.processed_count += 1
        return result
    
    def batch_process(self, inputs: List[str], output_format: str = "json") -> List[Dict[str, Any]]:
        """
        批量处理多个输入
        
        参数:
            inputs: 输入数据列表
            output_format: 输出格式
            
        返回:
            处理结果列表
        """
        results = []
        failed = []
        
        for idx, input_data in enumerate(inputs):
            try:
                result = self.process_input(input_data, output_format)
                results.append(result)
            except AnimeDLError as e:
                failed.append({"index": idx, "error": e.code, "message": str(e)})
        
        if failed:
            results.append({
                "status": "partial_failure",
                "failed_items": failed,
                "error_code": "E007",
            })
        
        return results
    
    def _parse_input(self, input_data: str) -> Dict[str, Any]:
        """解析输入数据"""
        parsed = {
            "raw": input_data,
            "length": len(input_data),
            "lines": input_data.strip().split("\n"),
            "words": input_data.strip().split(),
        }
        
        # 尝试解析 JSON
        try:
            parsed["json"] = json.loads(input_data)
        except (json.JSONDecodeError, TypeError):
            parsed["json"] = None
        
        return parsed
    
    def _extract_key_info(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """识别并提取关键信息"""
        key_info = {}
        raw = parsed_data["raw"]
        
        # 提取 URL
        urls = self._find_urls(raw)
        if urls:
            key_info["urls"] = urls
        
        # 提取邮箱
        emails = self._find_emails(raw)
        if emails:
            key_info["emails"] = emails
        
        # 提取日期
        dates = self._find_dates(raw)
        if dates:
            key_info["dates"] = dates
        
        # 提取数字编号
        ids = self._find_ids(raw)
        if ids:
            key_info["ids"] = ids
        
        # 提取关键词
        keywords = self._find_keywords(raw)
        if keywords:
            key_info["keywords"] = keywords
        
        return key_info
    
    def _find_urls(self, text: str) -> List[str]:
        """查找 URL"""
        urls = []
        words = text.split()
        for word in words:
            if any(domain in word.lower() for domain in [".com", ".org", ".net", ".io"]):
                if word.startswith("http") or word.startswith("www"):
                    urls.append(word.strip(",.);:"))
        return urls
    
    def _find_emails(self, text: str) -> List[str]:
        """查找邮箱地址"""
        emails = []
        words = text.split()
        for word in words:
            if "@" in word and "." in word:
                clean_word = word.strip(",.);:")
                if clean_word.count("@") == 1:
                    emails.append(clean_word)
        return emails
    
    def _find_dates(self, text: str) -> List[str]:
        """查找日期格式"""
        import re
        date_patterns = [
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # 2024-01-01
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',  # 01-01-2024
            r'\d{4}年\d{1,2}月\d{1,2}日',     # 2024年1月1日
        ]
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        return list(set(dates))
    
    def _find_ids(self, text: str) -> List[str]:
        """查找编号/ID"""
        import re
        # 匹配常见 ID 格式
        patterns = [
            r'\b[A-Z]{2,5}\d{3,}\b',  # ABC1234
            r'\b\d{6,}\b',             # 123456
            r'ID[:\s]*\d+',            # ID:123
            r'编号[:\s]*\d+',          # 编号:123
        ]
        ids = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            ids.extend(matches)
        return list(set(ids))
    
    def _find_keywords(self, text: str) -> List[str]:
        """查找关键词"""
        common_keywords = [
            "anime", "动画", "动漫", "下载", "download",
            "视频", "video", "episode", "集", "season", "季",
        ]
        found = []
        text_lower = text.lower()
        for keyword in common_keywords:
            if keyword in text_lower:
                found.append(keyword)
        return found
    
    def _detect_input_type(self, input_data: str) -> str:
        """检测输入类型"""
        if input_data.startswith("http://") or input_data.startswith("https://"):
            return "URL"
        if input_data.lstrip().startswith("{"):
            return "JSON"
        if len(input_data.split("\n")) > 1:
            return "multiline_text"
        return "plain_text"
    
    def _calculate_confidence(self, key_info: Dict[str, Any]) -> float:
        """计算处理置信度"""
        if not key_info:
            return 0.5
        
        # 基于提取到的信息量计算
        base_score = 0.6
        info_count = len(key_info)
        
        # 每类信息增加置信度
        bonus = min(0.3, info_count * 0.1)
        
        # 有关键信息类型加分
        if "urls" in key_info:
            bonus += 0.1
        if "emails" in key_info:
            bonus += 0.1
        if "dates" in key_info:
            bonus += 0.05
        
        confidence = min(0.98, base_score + bonus)
        return confidence
    
    def _get_confidence_label(self, confidence: float) -> str:
        """获取置信度标签"""
        if confidence >= 0.9:
            return "高置信度"
        elif confidence >= 0.85:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 格式输出处理器
# ============================================================

class OutputFormatter:
    """输出格式处理器"""
    
    @staticmethod
    def format_result(result: Dict[str, Any], output_format: str = "json") -> str:
        """格式化输出结果"""
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif output_format == "text":
            return OutputFormatter._format_text(result)
        elif output_format == "csv":
            return OutputFormatter._format_csv(result)
        else:
            raise AnimeDLError("E008")
    
    @staticmethod
    def _format_text(result: Dict[str, Any]) -> str:
        """文本格式输出"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"处理时间: {result.get('timestamp', 'N/A')}")
        lines.append(f"输入类型: {result.get('input_type', 'N/A')}")
        lines.append(f"置信度: {result.get('confidence', 0):.0%} ({result.get('confidence_label', 'N/A')})")
        lines.append("-" * 50)
        
        key_info = result.get("key_info", {})
        if key_info:
            for field, value in key_info.items():
                lines.append(f"{field}: {', '.join(value) if isinstance(value, list) else value}")
        else:
            lines.append("未识别到关键信息")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    @staticmethod
    def _format_csv(result: Dict[str, Any]) -> str:
        """CSV 格式输出"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写表头
        writer.writerow(["字段", "值"])
        
        # 写基本信息
        writer.writerow(["timestamp", result.get("timestamp", "")])
        writer.writerow(["input_type", result.get("input_type", "")])
        writer.writerow(["confidence", result.get("confidence", "")])
        
        # 写关键信息
        key_info = result.get("key_info", {})
        for field, value in key_info.items():
            if isinstance(value, list):
                writer.writerow([field, ";".join(value)])
            else:
                writer.writerow([field, value])
        
        return output.getvalue()


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检程序
    
    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。
    使用宽松阈值进行断言，确保测试稳健。
    """
    print("=" * 60)
    print("anime-dl 自检程序")
    print("=" * 60)
    
    try:
        # 创建处理器实例
        processor = DataProcessor()
        formatter = OutputFormatter()
        
        # 测试样例 1: URL 输入
        print("\n[测试 1] URL 输入处理...")
        url_input = "https://www.example.com/anime/episode-01 2024-01-15"
        result1 = processor.process_input(url_input, "json")
        
        # 宽松断言
        assert result1["status"] == "success", "状态应为 success"
        assert result1["confidence"] > 0.7, f"置信度应大于 0.7，实际: {result1['confidence']}"
        assert len(result1["key_info"]) > 0, "应提取到关键信息"
        print(f"  ✓ 通过 (置信度: {result1['confidence']:.0%})")
        
        # 测试样例 2: 多行文本输入
        print("[测试 2] 多行文本处理...")
        multi_input = """动漫名称: 测试动漫
        集数: 第5集
        链接: https://example.org/watch/12345
        日期: 2024-03-20"""
        result2 = processor.process_input(multi_input, "json")
        
        assert result2["status"] == "success", "状态应为 success"
        assert result2["input_type"] == "multiline_text", "应识别为多行文本"
        assert result2["confidence"] > 0.6, f"置信度应大于 0.6，实际: {result2['confidence']}"
        print(f"  ✓ 通过 (置信度: {result2['confidence']:.0%})")
        
        # 测试样例 3: 错误处理
        print("[测试 3] 空输入错误处理...")
        try:
            processor.process_input("", "json")
            assert False, "空输入应抛出 E001 错误"
        except AnimeDLError as e:
            assert e.code == "E001", f"错误码应为 E001，实际: {e.code}"
        print("  ✓ 通过 (E001 错误码正确)")
        
        # 测试样例 4: 批量处理
        print("[测试 4] 批量处理...")
        batch_inputs = [
            "https://example.com/batch/1",
            "测试文本 with email@test.com",
            "2024-05-01 重要日期",
        ]
        batch_results = processor.batch_process(batch_inputs, "json")
        
        assert len(batch_results) >= 3, "批量处理应返回至少 3 个结果"
        success_count = sum(1 for r in batch_results if r["status"] == "success")
        assert success_count >= 2, f"至少应有 2 个成功结果，实际: {success_count}"
        print(f"  ✓ 通过 (成功: {success_count}/{len(batch_inputs)})")
        
        # 测试样例 5: 输出格式化
        print("[测试 5] 输出格式化...")
        text_output = formatter.format_result(result1, "text")
        assert len(text_output) > 10, "文本输出应包含内容"
        
        csv_output = formatter.format_result(result1, "csv")
        assert "字段" in csv_output, "CSV 输出应包含表头"
        print("  ✓ 通过 (text/csv 格式正常)")
        
        # 测试样例 6: 关键信息提取
        print("[测试 6] 关键信息提取...")
        info_text = "联系邮箱: support@anime.com 电话: +86-123-4567"
        info_result = processor.process_input(info_text, "json")
        
        key_info = info_result["key_info"]
        assert "emails" in key_info, "应提取到邮箱信息"
        assert len(key_info["emails"]) > 0, "邮箱列表不应为空"
        print(f"  ✓ 通过 (提取到 {len(key_info.get('emails', []))} 个邮箱)")
        
        # 测试样例 7: 无效格式处理
        print("[测试 7] 无效格式处理...")
        try:
            processor.process_input("测试内容", "xml")
            assert False, "无效格式应抛出 E008 错误"
        except AnimeDLError as e:
            assert e.code == "E008", f"错误码应为 E008，实际: {e.code}"
        print("  ✓ 通过 (E008 错误码正确)")
        
        # 测试样例 8: 完整流程
        print("[测试 8] 完整处理流程...")
        full_input = """
        anime-dl 测试数据
        动画名称: 测试动画 第一季
        下载链接: https://cdn.example.com/video/season1/ep1.mp4
        发布日期: 2024-01-01
        备注: 高清版本
        """
        full_result = processor.process_input(full_input, "json")
        
        assert full_result["status"] == "success"
        assert len(full_result["key_info"]) >= 2, "应提取到至少 2 类关键信息"
        assert full_result["confidence"] > 0.5, "置信度应大于 0.5"
        print(f"  ✓ 通过 (提取到 {len(full_result['key_info'])} 类信息)")
        
        # 汇总
        print("\n" + "=" * 60)
        print("✅ 所有自检测试通过!")
        print(f"   测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {e}")
        return False


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="anime-dl 爬虫采集工具 - 将数据/文件/URL 转换为结构化结果",
        epilog="示例: python main.py --input 'https://example.com' --format json"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序（离线，不依赖外部文件）"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（文本/URL/JSON 字符串）"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件（每行一个输入）"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="anime-dl 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 无参数时显示帮助
    if not args.input and not args.batch:
        parser.print_help()
        print("\n提示: 使用 --selftest 运行自检程序")
        return
    
    try:
        processor = DataProcessor()
        formatter = OutputFormatter()
        
        # 批量处理
        if args.batch:
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    inputs = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"[E006] 文件不存在: {args.batch}")
                sys.exit(1)
            except Exception as e:
                print(f"[E006] 文件读取失败: {e}")
                sys.exit(1)
            
            results = processor.batch_process(inputs, args.format)
            output = formatter.format_result(results, args.format)
            print(output)
        
        # 单条处理
        elif args.input:
            try:
                result = processor.process_input(args.input, args.format)
                output = formatter.format_result(result, args.format)
                print(output)
            except AnimeDLError as e:
                print(f"处理失败: [{e.code}] {e.message}")
                sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n[E010] 用户中断操作")
        sys.exit(130)
    except Exception as e:
        print(f"[E009] 未预期异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
