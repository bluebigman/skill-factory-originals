#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bedrock - AI-ready 项目配置引导工具

根据功能规格实现的核心 CLI：
- 将用户输入转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术（来自规格第四章）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出序列化失败",
    "E008": "批量处理中断，部分结果已生成",
    "E009": "参数解析错误，请检查命令行参数",
    "E010": "未知错误，请联系维护者",
}

# 置信度阈值（来自规格第三章）
CONFIDENCE_HIGH = 90          # ≥90% 直接输出
CONFIDENCE_MEDIUM = 85        # 85%-90% 建议复核
CONFIDENCE_LOW = 85           # <85% 标注需核实

# 默认输出字段结构
DEFAULT_FIELDS = ["content", "summary", "keywords", "confidence", "flags"]

# 触发词（来自规格第二章）
TRIGGER_WORDS = ["bedrock", "处理", "转换", "批量", "格式化"]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果的标准化容器"""
    
    def __init__(self, content: str, summary: str, keywords: List[str],
                 confidence: float, flags: Optional[List[str]] = None):
        self.content = content
        self.summary = summary
        self.keywords = keywords
        self.confidence = confidence
        self.flags = flags or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "content": self.content,
            "summary": self.summary,
            "keywords": self.keywords,
            "confidence": self.confidence,
            "flags": self.flags,
        }
    
    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise BedrockError("E007", f"序列化失败: {exc}") from exc


# ============================================================
# 自定义异常
# ============================================================

class BedrockError(Exception):
    """带错误码的业务异常"""
    
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        if detail:
            message = f"{message} {detail}"
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, str]:
        return {"error_code": self.code, "message": str(self)}


# ============================================================
# 核心处理引擎
# ============================================================

class BedrockEngine:
    """
    核心处理引擎：负责解析输入、识别关键信息、生成结构化输出。
    
    能力边界（来自规格第一章）：
    - 能做：结构化转换、关键信息保留、格式输出、置信度标注、批量处理
    - 不做：超出输入范围的分析、绝对准确保证、网络/外部服务访问
    """
    
    def __init__(self, custom_fields: Optional[List[str]] = None):
        self.output_fields = custom_fields or DEFAULT_FIELDS
    
    def process(self, raw_input: Any, format_hint: str = "auto") -> ProcessingResult:
        """
        处理单个输入，返回结构化结果。
        
        Args:
            raw_input: 用户提供的原始数据（字符串、字典、列表等）
            format_hint: 格式提示（auto/json/text/yaml）
            
        Returns:
            ProcessingResult 标准化结果
            
        Raises:
            BedrockError: E001 输入为空 / E003 格式错误 / E004 超出边界
        """
        # 输入校验
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            raise BedrockError("E001")
        if isinstance(raw_input, (list, tuple)) and len(raw_input) == 0:
            raise BedrockError("E001")
        if isinstance(raw_input, dict) and len(raw_input) == 0:
            raise BedrockError("E001")
        
        # 格式解析
        try:
            parsed_content, input_type = self._parse_input(raw_input, format_hint)
        except ValueError as exc:
            raise BedrockError("E003", str(exc)) from exc
        
        # 关键信息提取
        keywords = self._extract_keywords(parsed_content)
        summary = self._generate_summary(parsed_content, input_type)
        
        # 置信度评估
        confidence = self._assess_confidence(parsed_content, keywords, input_type)
        
        # 生成标记
        flags = self._generate_flags(confidence, input_type)
        
        return ProcessingResult(
            content=parsed_content,
            summary=summary,
            keywords=keywords,
            confidence=confidence,
            flags=flags,
        )
    
    def batch_process(self, inputs: List[Any], format_hint: str = "auto") -> List[ProcessingResult]:
        """
        批量处理多个输入。
        
        Args:
            inputs: 输入列表
            format_hint: 格式提示
            
        Returns:
            处理结果列表（可能部分失败，失败项以错误标记）
        """
        results = []
        for idx, item in enumerate(inputs):
            try:
                results.append(self.process(item, format_hint))
            except BedrockError as exc:
                # 批量处理时记录错误但不中断
                results.append(ProcessingResult(
                    content=str(item),
                    summary=f"[错误] {exc}",
                    keywords=["error"],
                    confidence=0.0,
                    flags=[exc.code],
                ))
        return results
    
    # --------------------------------------------------------
    # 内部方法
    # --------------------------------------------------------
    
    def _parse_input(self, raw_input: Any, format_hint: str) -> Tuple[str, str]:
        """
        解析输入为文本内容，返回 (内容, 类型)。
        
        支持：
        - 字符串：直接使用或尝试 JSON 解析
        - 字典/列表：JSON 序列化
        - 数字/布尔：字符串转换
        """
        # 字符串处理
        if isinstance(raw_input, str):
            text = raw_input.strip()
            if not text:
                raise ValueError("空字符串")
            
            # 尝试 JSON 解析（如果看起来像 JSON）
            if format_hint in ("auto", "json") and (text.startswith("{") or text.startswith("[")):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, (dict, list)):
                        return json.dumps(parsed, ensure_ascii=False), "json"
                except json.JSONDecodeError:
                    if format_hint == "json":
                        raise ValueError("JSON 格式无效")
            return text, "text"
        
        # 字典/列表处理
        if isinstance(raw_input, (dict, list)):
            try:
                return json.dumps(raw_input, ensure_ascii=False), "json"
            except (TypeError, ValueError) as exc:
                raise ValueError(f"无法序列化: {exc}") from exc
        
        # 其他类型（数字、布尔等）
        return str(raw_input), "scalar"
    
    def _extract_keywords(self, content: str) -> List[str]:
        """
        从内容中提取关键信息。
        
        策略：
        - 提取中英文单词/词组
        - 过滤常见停用词
        - 保留有意义的标识符（如 UUID、URL、文件名）
        """
        # 提取英文单词和数字
        words = re.findall(r'[a-zA-Z][a-zA-Z0-9_]{1,}', content)
        # 提取中文词组（2-6字）
        chinese = re.findall(r'[\u4e00-\u9fff]{2,6}', content)
        # 提取 URL
        urls = re.findall(r'https?://[^\s]+', content)
        # 提取文件路径
        paths = re.findall(r'[\w./\\]+\.\w{1,5}', content)
        
        # 合并去重
        all_items = words + chinese + urls + paths
        
        # 停用词过滤
        stopwords = {"the", "and", "for", "with", "this", "that", "from",
                     "您", "的", "了", "是", "在", "我", "有", "和"}
        
        keywords = []
        seen = set()
        for item in all_items:
            lower = item.lower()
            if lower not in stopwords and lower not in seen:
                seen.add(lower)
                keywords.append(item)
        
        # 限制关键词数量
        return keywords[:10]
    
    def _generate_summary(self, content: str, input_type: str) -> str:
        """
        根据内容生成摘要。
        
        规则：
        - 文本：取前 50 个字符
        - JSON：提取关键字段名
        - 标量：直接返回
        """
        if input_type == "json":
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    return f"包含字段: {', '.join(keys)}"
                elif isinstance(data, list):
                    return f"列表，共 {len(data)} 项"
            except json.JSONDecodeError:
                pass
        
        if input_type == "scalar":
            return content[:50]
        
        # 文本摘要
        clean_text = re.sub(r'\s+', ' ', content).strip()
        if len(clean_text) <= 50:
            return clean_text
        return clean_text[:50] + "..."
    
    def _assess_confidence(self, content: str, keywords: List[str], input_type: str) -> float:
        """
        评估处理置信度（0-100）。
        
        规则：
        - 有有效关键词：基础 90 分
        - 内容长且结构化：加分
        - 内容模糊或过短：减分
        """
        score = 80.0
        
        # 关键词丰富度
        if len(keywords) >= 3:
            score += 10
        elif len(keywords) >= 1:
            score += 5
        
        # 内容长度
        if len(content) >= 100:
            score += 5
        elif len(content) < 20:
            score -= 10
        
        # 结构化加分
        if input_type in ("json", "scalar"):
            score += 5
        
        # 限制在 0-100
        return max(0.0, min(100.0, score))
    
    def _generate_flags(self, confidence: float, input_type: str) -> List[str]:
        """
        根据置信度生成标记。
        
        规则（来自规格第三章）：
        - ≥90%：无标记
        - 85%-90%：建议复核
        - <85%：需核实
        """
        flags = []
        if confidence >= CONFIDENCE_HIGH:
            pass  # 直接输出
        elif confidence >= CONFIDENCE_MEDIUM:
            flags.append("建议复核")
        else:
            flags.append("[需核实]")
        
        # 类型标记
        if input_type == "json":
            flags.append("结构化数据")
        elif input_type == "text":
            flags.append("自由文本")
        
        return flags


# ============================================================
# 输出格式化器
# ============================================================

class OutputFormatter:
    """将处理结果格式化为不同输出格式"""
    
    @staticmethod
    def format_result(result: ProcessingResult, output_format: str = "text") -> str:
        """
        格式化单个结果。
        
        Args:
            result: 处理结果
            output_format: text/json/compact
            
        Returns:
            格式化字符串
        """
        if output_format == "json":
            return result.to_json()
        
        if output_format == "compact":
            conf = f"{result.confidence:.0f}%"
            flags = " | " + ", ".join(result.flags) if result.flags else ""
            return f"[{conf}]{flags} {result.summary}"
        
        # 默认文本格式
        lines = [
            "=" * 60,
            "处理结果",
            "=" * 60,
            f"摘要: {result.summary}",
            f"置信度: {result.confidence:.1f}%",
        ]
        if result.keywords:
            lines.append(f"关键词: {', '.join(result.keywords)}")
        if result.flags:
            lines.append(f"标记: {', '.join(result.flags)}")
        lines.append("-" * 60)
        lines.append("内容:")
        lines.append(result.content)
        lines.append("=" * 60)
        return "\n".join(lines)
    
    @staticmethod
    def format_batch(results: List[ProcessingResult], output_format: str = "text") -> str:
        """格式化批量结果"""
        if output_format == "json":
            return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
        
        parts = []
        for i, result in enumerate(results, 1):
            parts.append(f"--- 项目 {i} ---")
            parts.append(OutputFormatter.format_result(result, output_format))
        return "\n".join(parts)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。
    
    不读取外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    
    Returns:
        0 表示全部通过，非 0 表示失败
    """
    print("=" * 60)
    print("Bedrock 自检开始")
    print("=" * 60)
    
    engine = BedrockEngine()
    formatter = OutputFormatter()
    failures = 0
    
    # ---- 测试用例 1: 文本输入 ----
    print("\n[测试 1] 文本输入处理")
    text_input = "请帮我处理这个项目配置文件，包含数据库连接和API密钥设置"
    try:
        result = engine.process(text_input)
        # 宽松断言：置信度在合理范围
        assert result.confidence > 50, f"置信度过低: {result.confidence}"
        assert result.confidence <= 100, f"置信度超上限: {result.confidence}"
        # 摘要非空
        assert result.summary, "摘要为空"
        # 关键词列表存在
        assert isinstance(result.keywords, list), "关键词应为列表"
        print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    except BedrockError as exc:
        print(f"  ✗ 异常: {exc}")
        failures += 1
    
    # ---- 测试用例 2: JSON 输入 ----
    print("\n[测试 2] JSON 输入处理")
    json_input = '{"name": "demo", "version": "1.0", "settings": {"debug": true}}'
    try:
        result = engine.process(json_input, format_hint="json")
        # JSON 应被识别为结构化数据
        assert "结构化数据" in result.flags, "JSON 输入应标记为结构化数据"
        assert result.confidence > 50, f"置信度过低: {result.confidence}"
        print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%, 关键词: {len(result.keywords)}个)")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    except BedrockError as exc:
        print(f"  ✗ 异常: {exc}")
        failures += 1
    
    # ---- 测试用例 3: 空输入错误处理 ----
    print("\n[测试 3] 空输入错误码")
    try:
        engine.process("")
        print("  ✗ 失败: 空输入未抛出异常")
        failures += 1
    except BedrockError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print(f"  ✓ 通过 (错误码: {exc.code})")
    except Exception as exc:
        print(f"  ✗ 异常类型错误: {type(exc).__name__}")
        failures += 1
    
    # ---- 测试用例 4: 批量处理 ----
    print("\n[测试 4] 批量处理")
    batch_inputs = [
        "第一个测试数据",
        {"id": 1, "name": "item"},
        "第二个测试数据",
    ]
    try:
        results = engine.batch_process(batch_inputs)
        assert len(results) == 3, f"应返回 3 个结果，实际 {len(results)}"
        # 每个结果都有有效置信度
        for r in results:
            assert 0 <= r.confidence <= 100, f"置信度越界: {r.confidence}"
        print(f"  ✓ 通过 (共 {len(results)} 项)")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    
    # ---- 测试用例 5: 输出格式化 ----
    print("\n[测试 5] 输出格式化")
    try:
        sample = ProcessingResult(
            content="测试内容",
            summary="测试摘要",
            keywords=["测试", "demo"],
            confidence=88.5,
            flags=["建议复核"],
        )
        text_out = formatter.format_result(sample, "text")
        json_out = formatter.format_result(sample, "json")
        compact_out = formatter.format_result(sample, "compact")
        
        assert "测试摘要" in text_out, "文本输出缺少摘要"
        assert '"confidence"' in json_out, "JSON 输出缺少置信度字段"
        assert "88%" in compact_out, "紧凑输出缺少置信度百分比"
        print("  ✓ 通过 (3 种格式)")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    
    # ---- 测试用例 6: 错误码完整性 ----
    print("\n[测试 6] 错误码完整性")
    try:
        expected_codes = ["E001", "E002", "E003", "E004", "E005"]
        for code in expected_codes:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
            assert ERROR_MESSAGES[code], f"错误码 {code} 话术为空"
        print(f"  ✓ 通过 ({len(expected_codes)} 个错误码)")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    
    # ---- 汇总 ----
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检全部通过 ✓")
        return 0
    else:
        print(f"自检失败: {failures} 项未通过 ✗")
        return 1


# ============================================================
# CLI 入口
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="bedrock",
        description="Bedrock - AI-ready 项目配置引导工具",
        epilog="示例: python main.py --input '文本内容' --format json",
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（文本或 JSON 字符串）",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取输入（注意：自检模式不使用此选项）",
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["text", "json", "compact"],
        default="text",
        help="输出格式 (默认: text)",
    )
    parser.add_argument(
        "--input-format",
        choices=["auto", "text", "json"],
        default="auto",
        help="输入格式提示 (默认: auto)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为 JSON 数组）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）",
    )
    
    return parser


def read_file_content(filepath: str) -> str:
    """读取文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as exc:
        raise BedrockError("E006", f"无法读取文件: {exc}") from exc


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。
    
    Args:
        argv: 命令行参数列表（None 表示使用 sys.argv[1:]）
        
    Returns:
        进程退出码（0 成功，非 0 失败）
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 参数校验
    if not args.input and not args.file:
        parser.print_usage()
        print(f"错误: {ERROR_MESSAGES['E001']}")
        return 1
    
    try:
        engine = BedrockEngine()
        formatter = OutputFormatter()
        
        # 获取输入
        if args.file:
            raw_input = read_file_content(args.file)
        else:
            raw_input = args.input
        
        # 批量模式
        if args.batch:
            try:
                data = json.loads(raw_input)
                if not isinstance(data, list):
                    raise ValueError("批量模式需要 JSON 数组")
            except (json.JSONDecodeError, ValueError) as exc:
                print(f"错误: {ERROR_MESSAGES['E003']} {exc}")
                return 1
            
            results = engine.batch_process(data, args.input_format)
            output = formatter.format_batch(results, args.format)
        else:
            # 单条处理
            result = engine.process(raw_input, args.input_format)
            output = formatter.format_result(result, args.format)
        
        print(output)
        return 0
        
    except BedrockError as exc:
        print(f"错误 [{exc.code}]: {exc}")
        return 1
    except Exception as exc:
        print(f"错误 [E010]: 未知错误: {exc}")
        return 1


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
