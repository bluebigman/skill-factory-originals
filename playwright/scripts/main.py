#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
playwright 技能工具 - 独立实现

本脚本根据功能规格实现一个通用的数据处理工具，支持：
- 从用户提供的数据/文件/URL 中提取关键信息并结构化输出
- 批量处理与自定义格式
- 置信度评估与标注
- 完善的错误码体系和自检功能

仅使用 Python 标准库，无第三方依赖。

用法:
    python main.py --selftest          # 运行内置自检
    python main.py --help              # 显示帮助
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


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
    "E007": "URL 格式无效，请输入合法的 URL 地址",
    "E008": "输出格式不支持，支持格式：json, text, csv",
    "E009": "内部处理错误，请重试或检查输入",
    "E010": "自检失败，核心逻辑存在缺陷",
}


class SkillError(Exception):
    """技能处理异常，携带错误码"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.message = ERROR_CODES.get(code, "未知错误")
        self.detail = detail
        super().__init__(f"[{code}] {self.message} {detail}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ProcessedItem:
    """处理结果项"""
    source: str                    # 输入来源
    content: str                   # 原始内容
    key_fields: Dict[str, Any]     # 提取的关键字段
    confidence: float              # 置信度 0-1
    flags: List[str] = field(default_factory=list)  # 标记列表


@dataclass
class ProcessResult:
    """批量处理结果"""
    items: List[ProcessedItem]
    total: int = 0
    avg_confidence: float = 0.0


# ============================================================
# 核心处理逻辑
# ============================================================
def extract_key_fields(content: str) -> Tuple[Dict[str, Any], float]:
    """
    从输入内容中提取关键字段并计算置信度
    
    规则：
    - 识别常见字段模式（邮箱、电话、日期、URL、金额等）
    - 根据识别到的字段数量和完整性计算置信度
    
    返回: (关键字段字典, 置信度)
    """
    if not content or not content.strip():
        return {}, 0.0
    
    fields: Dict[str, Any] = {}
    found_count = 0
    total_patterns = 6  # 总模式数
    
    # 邮箱识别
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', content)
    if email_match:
        fields['email'] = email_match.group(0)
        found_count += 1
    
    # 电话号码识别（简单模式）
    phone_match = re.search(r'(?<!\d)(1[3-9]\d{9}|0\d{2,3}-?\d{7,8})(?!\d)', content)
    if phone_match:
        fields['phone'] = phone_match.group(0)
        found_count += 1
    
    # 日期识别（支持多种格式）
    date_match = re.search(
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        content
    )
    if date_match:
        fields['date'] = date_match.group(0)
        found_count += 1
    
    # URL 识别
    url_match = re.search(r'https?://[^\s]+', content)
    if url_match:
        fields['url'] = url_match.group(0)
        found_count += 1
    
    # 金额识别
    amount_match = re.search(r'[¥￥]\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*元', content)
    if amount_match:
        fields['amount'] = amount_match.group(0)
        found_count += 1
    
    # 身份证号识别
    id_match = re.search(r'\d{17}[\dXx]', content)
    if id_match:
        fields['id_card'] = id_match.group(0)
        found_count += 1
    
    # 计算置信度：基础值 + 识别率加权
    base_confidence = 0.7
    recognition_rate = found_count / total_patterns
    confidence = min(0.95, base_confidence + recognition_rate * 0.25)
    
    # 内容长度影响置信度
    content_len = len(content.strip())
    if content_len < 10:
        confidence *= 0.8
    elif content_len > 200:
        confidence = min(0.95, confidence + 0.05)
    
    return fields, round(confidence, 2)


def process_content(source: str, content: str) -> ProcessedItem:
    """处理单条内容"""
    if not content or not content.strip():
        raise SkillError("E001")
    
    key_fields, confidence = extract_key_fields(content)
    
    # 生成标记
    flags = []
    if confidence >= 0.9:
        pass  # 高置信度，无标记
    elif confidence >= 0.85:
        flags.append("建议复核")
    else:
        flags.append("[需核实]")
    
    if not key_fields:
        flags.append("未识别到关键字段")
    
    return ProcessedItem(
        source=source,
        content=content.strip(),
        key_fields=key_fields,
        confidence=confidence,
        flags=flags
    )


def process_batch(inputs: List[Tuple[str, str]]) -> ProcessResult:
    """批量处理输入列表 [(来源, 内容), ...]"""
    if not inputs:
        raise SkillError("E001")
    
    items = []
    for source, content in inputs:
        try:
            item = process_content(source, content)
            items.append(item)
        except SkillError:
            # 单条失败不影响其他，标记后继续
            items.append(ProcessedItem(
                source=source,
                content=content,
                key_fields={},
                confidence=0.0,
                flags=["处理失败"]
            ))
    
    total = len(items)
    avg_conf = sum(i.confidence for i in items) / total if total > 0 else 0.0
    
    return ProcessResult(items=items, total=total, avg_confidence=round(avg_conf, 2))


# ============================================================
# 输出格式化
# ============================================================
def format_output(result: ProcessResult, fmt: str = "json") -> str:
    """格式化输出结果"""
    if fmt == "json":
        data = {
            "total": result.total,
            "avg_confidence": result.avg_confidence,
            "items": [
                {
                    "source": item.source,
                    "content_preview": item.content[:100] + ("..." if len(item.content) > 100 else ""),
                    "key_fields": item.key_fields,
                    "confidence": item.confidence,
                    "flags": item.flags
                }
                for item in result.items
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    elif fmt == "text":
        lines = [f"处理结果 (共{result.total}条，平均置信度 {result.avg_confidence}):"]
        for i, item in enumerate(result.items, 1):
            lines.append(f"\n--- 第{i}条 ---")
            lines.append(f"来源: {item.source}")
            lines.append(f"置信度: {item.confidence}")
            if item.flags:
                lines.append(f"标记: {', '.join(item.flags)}")
            if item.key_fields:
                lines.append("关键字段:")
                for k, v in item.key_fields.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append("未提取到关键字段")
        return "\n".join(lines)
    
    elif fmt == "csv":
        lines = ["source,confidence,flags,key_fields"]
        for item in result.items:
            flags_str = ";".join(item.flags)
            fields_str = ";".join(f"{k}={v}" for k, v in item.key_fields.items())
            # 简单 CSV 转义
            source = item.source.replace('"', '""')
            lines.append(f'"{source}",{item.confidence},"{flags_str}","{fields_str}"')
        return "\n".join(lines)
    
    else:
        raise SkillError("E008")


# ============================================================
# 输入处理
# ============================================================
def read_input_from_file(filepath: str) -> str:
    """从文件读取内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise SkillError("E006", f"文件不存在: {filepath}")
    except PermissionError:
        raise SkillError("E006", f"无权限读取: {filepath}")
    except Exception as e:
        raise SkillError("E006", str(e))


def validate_url(url: str) -> bool:
    """验证 URL 格式（仅格式验证，不访问网络）"""
    pattern = re.compile(
        r'^https?://'  # http:// 或 https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
        r'localhost|'  # 本地
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # 端口
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))


def parse_inputs(raw_inputs: List[str]) -> List[Tuple[str, str]]:
    """
    解析输入列表，支持直接内容、文件路径、URL
    
    返回: [(来源, 内容), ...]
    """
    if not raw_inputs:
        raise SkillError("E001")
    
    parsed = []
    for raw in raw_inputs:
        # 尝试作为文件读取
        if os.path.isfile(raw):
            content = read_input_from_file(raw)
            parsed.append((f"file:{raw}", content))
        # 尝试作为 URL
        elif validate_url(raw):
            # 注意：按规格要求不访问网络，仅标记
            parsed.append((f"url:{raw}", raw))
        # 否则作为直接内容
        else:
            parsed.append(("direct", raw))
    
    return parsed


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    内置自检函数，使用硬编码样例数据验证核心逻辑
    
    不读外部文件、不依赖工作目录、不访问网络
    """
    print("=" * 60)
    print("开始自检...")
    
    # 测试样例（硬编码）
    test_cases = [
        # (来源, 内容, 期望至少有一个关键字段, 最低置信度)
        (
            "test1",
            "联系人：张三，邮箱：zhangsan@example.com，电话：13812345678，日期：2024-01-15",
            True, 0.7
        ),
        (
            "test2",
            "项目预算：¥50,000元，负责人：李四，截止日期：2024年6月30日",
            True, 0.7
        ),
        (
            "test3",
            "这是一段普通文本，没有明显的关键信息，只有简单描述。",
            False, 0.5
        ),
        (
            "test4",
            "访问 https://example.com/api/v1 获取数据，金额 299元",
            True, 0.7
        ),
        (
            "test5",
            "身份证号 110101199001011234，联系电话 010-12345678",
            True, 0.7
        ),
    ]
    
    all_passed = True
    
    # 测试1: 基本处理
    print("\n[测试1] 核心处理逻辑")
    for idx, (source, content, expect_fields, min_conf) in enumerate(test_cases, 1):
        try:
            item = process_content(source, content)
            has_fields = bool(item.key_fields)
            conf_ok = item.confidence >= min_conf
            
            status = "通过" if (has_fields == expect_fields and conf_ok) else "失败"
            if status == "失败":
                all_passed = False
            
            print(f"  样例{idx}: {status} (字段: {has_fields}, 置信度: {item.confidence:.2f})")
            
            # 宽松断言
            assert has_fields == expect_fields, f"样例{idx}字段提取不符合预期"
            assert item.confidence >= min_conf, f"样例{idx}置信度低于阈值"
            
        except Exception as e:
            all_passed = False
            print(f"  样例{idx}: 失败 ({e})")
    
    # 测试2: 批量处理
    print("\n[测试2] 批量处理")
    try:
        batch_inputs = [(src, content) for src, content, _, _ in test_cases]
        result = process_batch(batch_inputs)
        assert result.total == len(test_cases), "批量处理数量不符"
        assert result.avg_confidence > 0.5, "平均置信度过低"
        print(f"  通过 (共{result.total}条，平均置信度: {result.avg_confidence:.2f})")
    except Exception as e:
        all_passed = False
        print(f"  失败 ({e})")
    
    # 测试3: 输出格式
    print("\n[测试3] 输出格式")
    try:
        result = process_batch([(src, content) for src, content, _, _ in test_cases[:3]])
        
        json_out = format_output(result, "json")
        assert json.loads(json_out)["total"] == 3, "JSON输出异常"
        
        text_out = format_output(result, "text")
        assert "处理结果" in text_out, "文本输出异常"
        
        csv_out = format_output(result, "csv")
        assert csv_out.startswith("source"), "CSV输出异常"
        
        print("  通过 (JSON/Text/CSV 格式均正常)")
    except Exception as e:
        all_passed = False
        print(f"  失败 ({e})")
    
    # 测试4: 错误处理
    print("\n[测试4] 错误处理")
    try:
        # 空输入
        try:
            process_content("test", "")
            all_passed = False
            print("  失败: 空输入未抛出E001")
        except SkillError as e:
            assert e.code == "E001", f"错误码应为E001，实际{e.code}"
            print("  通过: 空输入正确抛出E001")
        
        # 不支持的输出格式
        try:
            result = process_batch([("test", "内容")])
            format_output(result, "xml")
            all_passed = False
            print("  失败: 不支持格式未抛出E008")
        except SkillError as e:
            assert e.code == "E008", f"错误码应为E008，实际{e.code}"
            print("  通过: 不支持格式正确抛出E008")
        
        # 不存在的文件
        try:
            read_input_from_file("/nonexistent/path/file.txt")
            all_passed = False
            print("  失败: 文件不存在未抛出E006")
        except SkillError as e:
            assert e.code == "E006", f"错误码应为E006，实际{e.code}"
            print("  通过: 文件不存在正确抛出E006")
            
    except Exception as e:
        all_passed = False
        print(f"  失败 ({e})")
    
    # 测试5: 边界情况
    print("\n[测试5] 边界情况")
    try:
        # 超长输入
        long_content = "测试" * 1000
        item = process_content("long", long_content)
        assert item.confidence > 0, "长文本处理异常"
        
        # 特殊字符
        special = "邮箱 test@test.com 日期 2024/01/01 金额 ¥100"
        item = process_content("special", special)
        assert len(item.key_fields) >= 3, "特殊字符提取异常"
        
        print("  通过 (长文本和特殊字符处理正常)")
    except Exception as e:
        all_passed = False
        print(f"  失败 ({e})")
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
        return True
    else:
        print("自检存在失败项 ✗")
        return False


# ============================================================
# 主程序
# ============================================================
def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="playwright 技能工具 - 通用数据处理",
        epilog="示例: python main.py --input '文本内容' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        action="append",
        help="输入内容，可多次指定（支持文件路径/URL/直接文本）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="playwright 技能工具 v1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 正常处理模式
    try:
        if not args.input:
            raise SkillError("E001")
        
        # 解析输入
        parsed_inputs = parse_inputs(args.input)
        
        # 处理
        result = process_batch(parsed_inputs)
        
        # 输出
        output = format_output(result, args.format)
        print(output)
        
        # 置信度提示
        if result.avg_confidence < 0.85:
            print(f"\n[提示] 平均置信度 {result.avg_confidence:.2f}，建议复核关键结果",
                  file=sys.stderr)
        
    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 [E009]: 内部错误 - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
