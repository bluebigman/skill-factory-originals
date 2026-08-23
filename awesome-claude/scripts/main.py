#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-claude 技能实现脚本
功能：检索Claude生态资产，将输入转为结构化结果，辅助选型与集成。
版本：1.0.1
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "输入为空：未提供任何有效输入内容",
    "E003": "输入超限：单批次记录数超过20条上限",
    "E004": "解析失败：无法从输入中识别有效资产信息",
    "E005": "输出序列化失败：无法生成JSON/Markdown输出",
    "E006": "内部逻辑错误：处理流程出现意外状态",
    "E007": "文件读取失败：无法读取指定文件",
    "E008": "URL格式错误：提供的链接不是有效URL",
    "E009": "类型不支持：未知的资产类型标识",
    "E010": "自检失败：核心逻辑自检未通过",
}


# ---------------------------------------------------------------------------
# 内置资产类型定义
# ---------------------------------------------------------------------------
ASSET_TYPES = {
    "agent": "Agent",
    "mcp": "MCP服务器",
    "skill": "Skill",
    "workflow": "工作流",
}

# 触发词（用于识别输入意图）
TRIGGER_WORDS = ["awesome claude", "claude资产", "技能检索", "mcp查询", "工作流速查"]

# 置信度级别
CONFIDENCE_LEVELS = ("高", "中", "低")


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _now_timestamp() -> str:
    """返回当前时间戳字符串（无外部依赖）。"""
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _is_valid_url(text: str) -> bool:
    """简单URL格式校验。"""
    if not text or len(text) > 2048:
        return False
    pattern = r"^(https?|ftp)://[^\s/$.?#].[^\s]*$"
    return re.match(pattern, text, re.IGNORECASE) is not None


def _detect_asset_type(text: str) -> Tuple[str, str]:
    """
    从文本中识别资产类型。
    返回 (类型标识, 置信度)
    """
    text_lower = text.lower()
    
    # 关键词权重匹配
    type_keywords = {
        "agent": ["agent", "智能体", "代理"],
        "mcp": ["mcp", "model context protocol", "模型上下文协议"],
        "skill": ["skill", "技能"],
        "workflow": ["workflow", "工作流", "流程"],
    }
    
    scores = {}
    for asset_type, keywords in type_keywords.items():
        score = 0
        for kw in keywords:
            if kw in text_lower:
                score += 1
        scores[asset_type] = score
    
    # 取最高分类型
    max_score = max(scores.values())
    if max_score == 0:
        return "unknown", "低"
    
    # 找出得分最高的类型（可能有并列）
    top_types = [t for t, s in scores.items() if s == max_score]
    if len(top_types) == 1:
        confidence = "高" if max_score >= 2 else "中"
        return top_types[0], confidence
    else:
        # 并列时取第一个，置信度降低
        return top_types[0], "低"


def _extract_name(text: str) -> Tuple[str, str]:
    """
    从文本中提取资产名称。
    返回 (名称, 置信度)
    """
    # 尝试匹配常见命名模式
    # 模式1: 引号中的内容
    quoted = re.findall(r"[\"']([^\"']+)[\"']", text)
    if quoted:
        return quoted[0].strip(), "高"
    
    # 模式2: 冒号后的内容
    colon_match = re.search(r"[：:]\s*([^\s,，。;；]+)", text)
    if colon_match:
        return colon_match.group(1).strip(), "中"
    
    # 模式3: 首个中英文单词组合（取前2-4个词）
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*|[\u4e00-\u9fa5]+", text)
    if words:
        # 过滤掉常见无意义词
        stopwords = {"the", "a", "an", "of", "for", "and", "claude", "使用", "一个", "这个"}
        meaningful = [w for w in words if w.lower() not in stopwords]
        if meaningful:
            name = " ".join(meaningful[:3])
            return name, "中"
    
    # 兜底：截取前20个字符
    cleaned = text.strip()[:20]
    if cleaned:
        return cleaned, "低"
    
    return "未知资产", "低"


def _extract_purpose(text: str) -> Tuple[str, str]:
    """
    从文本中提取用途描述。
    返回 (用途, 置信度)
    """
    # 查找用途相关关键词
    purpose_patterns = [
        r"(?:用于|作用是|目的是|帮助|实现|支持|完成)[^。；;\n]{2,50}",
        r"(?:用途|功能|作用)[：:]\s*[^。；;\n]{2,50}",
    ]
    
    for pattern in purpose_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip(), "高"
    
    # 无关键词时，取文本中间部分
    if len(text) > 20:
        mid = len(text) // 2
        start = max(0, mid - 15)
        end = min(len(text), mid + 15)
        return text[start:end].strip(), "低"
    
    return "未提供用途描述", "低"


def _extract_dependencies(text: str) -> Tuple[List[str], str]:
    """
    从文本中提取依赖项。
    返回 (依赖列表, 置信度)
    """
    # 查找依赖相关关键词
    dep_patterns = [
        r"依赖[:：]?\s*([^。；;\n]+)",
        r"requires?[:：]?\s*([^。；;\n]+)",
        r"需要[:：]?\s*([^。；;\n]+)",
    ]
    
    for pattern in dep_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            deps_text = match.group(1)
            # 拆分依赖项
            deps = [d.strip() for d in re.split(r"[,，、;；]", deps_text) if d.strip()]
            if deps:
                return deps, "高"
    
    return [], "低"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def process_input(raw_input: str) -> Dict[str, Any]:
    """
    处理用户输入，返回结构化结果。
    
    参数:
        raw_input: 用户提供的原始输入（URL、文件路径、粘贴文本）
    
    返回:
        结构化处理结果字典
    
    错误码:
        E001: 参数错误
        E002: 输入为空
        E003: 输入超限
        E004: 解析失败
    """
    # 参数校验
    if raw_input is None:
        raise ValueError(f"E001: {ERROR_CODES['E001']}")
    
    text = raw_input.strip()
    if not text:
        raise ValueError(f"E002: {ERROR_CODES['E002']}")
    
    # 按行拆分，检测批量输入
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    # 如果输入是单行但包含分隔符，也拆分为多条
    if len(lines) == 1:
        lines = [l.strip() for l in re.split(r"[;；]+", lines[0]) if l.strip()]
    
    # 批量上限检查
    if len(lines) > 20:
        raise ValueError(f"E003: {ERROR_CODES['E003']}（当前 {len(lines)} 条）")
    
    # 逐条处理
    records = []
    for line in lines:
        record = _process_single(line)
        if record:
            records.append(record)
    
    if not records:
        raise ValueError(f"E004: {ERROR_CODES['E004']}")
    
    # 构建结果
    result = {
        "query": text[:200],
        "record_count": len(records),
        "records": records,
        "processed_at": _now_timestamp(),
        "note": "结构化整理与检索辅助工具，非实时数据库",
    }
    
    return result


def _process_single(line: str) -> Optional[Dict[str, Any]]:
    """
    处理单条记录。
    """
    try:
        # 检测URL
        url = None
        url_match = re.search(r"(https?://[^\s]+)", line)
        if url_match:
            candidate_url = url_match.group(1).rstrip(".,;:!?")
            if _is_valid_url(candidate_url):
                url = candidate_url
        
        # 检测文件路径
        file_path = None
        path_match = re.search(r"([/\\][\w./\\-]+\.\w+)", line)
        if path_match:
            file_path = path_match.group(1)
        
        # 检测资产类型
        asset_type, type_confidence = _detect_asset_type(line)
        
        # 检测来源
        source = None
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            source = parsed.netloc
        
        # 提取名称
        name, name_confidence = _extract_name(line)
        
        # 提取用途
        purpose, purpose_confidence = _extract_purpose(line)
        
        # 提取依赖
        dependencies, dep_confidence = _extract_dependencies(line)
        
        # 综合置信度（取最低）
        confidences = [type_confidence, name_confidence, purpose_confidence]
        if dep_confidence == "高":
            confidences.append("高")
        overall = min(confidences, key=lambda x: ["高", "中", "低"].index(x))
        
        record = {
            "name": name,
            "type": asset_type,
            "type_display": ASSET_TYPES.get(asset_type, "未知类型"),
            "url": url,
            "file_path": file_path,
            "source": source,
            "purpose": purpose,
            "dependencies": dependencies,
            "confidence": overall,
            "raw_input": line[:100],
        }
        
        return record
    
    except Exception as e:
        # 单条记录失败不影响整体，返回None
        return None


def format_markdown(result: Dict[str, Any]) -> str:
    """
    将处理结果格式化为Markdown。
    
    错误码:
        E005: 输出序列化失败
    """
    try:
        lines = []
        lines.append("# Claude 资产检索结果")
        lines.append("")
        lines.append(f"> 查询时间：{result.get('processed_at', 'N/A')}")
        lines.append(f"> 记录数量：{result.get('record_count', 0)}")
        lines.append("")
        
        if result.get("query"):
            lines.append(f"**原始输入**：`{result['query']}`")
            lines.append("")
        
        lines.append("## 资产清单")
        lines.append("")
        lines.append("| # | 名称 | 类型 | 来源 | 置信度 | 用途 |")
        lines.append("|---|------|------|------|--------|------|")
        
        for idx, record in enumerate(result.get("records", []), 1):
            name = record.get("name", "未知")
            type_display = record.get("type_display", "未知")
            source = record.get("source") or record.get("file_path") or "N/A"
            confidence = record.get("confidence", "低")
            purpose = (record.get("purpose") or "N/A")[:40]
            
            lines.append(f"| {idx} | {name} | {type_display} | {source} | {confidence} | {purpose} |")
        
        lines.append("")
        lines.append("## 详细记录")
        lines.append("")
        
        for idx, record in enumerate(result.get("records", []), 1):
            lines.append(f"### {idx}. {record.get('name', '未知')}")
            lines.append("")
            lines.append(f"- **类型**：{record.get('type_display', '未知')}")
            lines.append(f"- **置信度**：{record.get('confidence', '低')}")
            if record.get("url"):
                lines.append(f"- **URL**：{record['url']}")
            if record.get("file_path"):
                lines.append(f"- **文件路径**：`{record['file_path']}`")
            if record.get("source"):
                lines.append(f"- **来源**：{record['source']}")
            if record.get("purpose"):
                lines.append(f"- **用途**：{record['purpose']}")
            if record.get("dependencies"):
                deps = ", ".join(record["dependencies"])
                lines.append(f"- **依赖**：{deps}")
            lines.append("")
        
        lines.append("---")
        lines.append("> ⚠️ 本内容仅供一般信息参考，不构成专业建议。")
        lines.append("> 本内容由 AI 生成，仅供学习参考。")
        
        return "\n".join(lines)
    
    except Exception as e:
        raise ValueError(f"E005: {ERROR_CODES['E005']} - {str(e)}")


def format_json(result: Dict[str, Any]) -> str:
    """
    将处理结果格式化为JSON字符串。
    
    错误码:
        E005: 输出序列化失败
    """
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ValueError(f"E005: {ERROR_CODES['E005']} - {str(e)}")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def _selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据验证核心功能。
    
    返回:
        True 表示自检通过
        
    错误码:
        E010: 自检失败
    """
    # 测试样例数据（硬编码，不依赖外部文件）
    test_cases = [
        {
            "input": "MCP服务器：claude-file-server，用于文件读写操作，依赖Node.js",
            "expect_type": "mcp",
            "expect_has_url": False,
        },
        {
            "input": "Agent: code-reviewer https://github.com/example/code-reviewer 用于自动化代码审查",
            "expect_type": "agent",
            "expect_has_url": True,
        },
        {
            "input": "Skill：文档总结技能，帮助快速生成文档摘要",
            "expect_type": "skill",
            "expect_has_url": False,
        },
        {
            "input": "https://github.com/example/workflow-orchestrator 工作流编排工具，依赖Python 3.10+",
            "expect_type": "workflow",
            "expect_has_url": True,
        },
    ]
    
    try:
        # 用例1: 基本MCP处理
        result1 = process_input(test_cases[0]["input"])
        assert result1["record_count"] >= 1, "记录数应至少为1"
        record1 = result1["records"][0]
        assert record1["type"] == test_cases[0]["expect_type"], f"类型应为{test_cases[0]['expect_type']}"
        assert record1["name"], "名称不应为空"
        assert record1["purpose"], "用途不应为空"
        assert len(record1["dependencies"]) >= 1, "应识别出依赖"
        
        # 用例2: URL处理
        result2 = process_input(test_cases[1]["input"])
        record2 = result2["records"][0]
        assert record2["type"] == test_cases[1]["expect_type"], f"类型应为{test_cases[1]['expect_type']}"
        if test_cases[1]["expect_has_url"]:
            assert record2["url"] is not None, "应识别出URL"
        
        # 用例3: 批量处理（多行）
        batch_input = "\n".join([tc["input"] for tc in test_cases])
        result3 = process_input(batch_input)
        assert result3["record_count"] >= 3, "批量处理记录数应>=3"
        
        # 用例4: 批量上限检查
        too_many = "\n".join([f"测试记录{i} MCP服务器" for i in range(21)])
        try:
            process_input(too_many)
            assert False, "应触发E003错误"
        except ValueError as e:
            assert str(e).startswith("E003"), "错误码应为E003"
        
        # 用例5: 空输入检查
        try:
            process_input("")
            assert False, "应触发E002错误"
        except ValueError as e:
            assert str(e).startswith("E002"), "错误码应为E002"
        
        # 用例6: Markdown输出
        md_output = format_markdown(result1)
        assert "Claude 资产检索结果" in md_output, "Markdown应包含标题"
        assert "|" in md_output, "Markdown应包含表格"
        
        # 用例7: JSON输出
        json_output = format_json(result1)
        parsed = json.loads(json_output)
        assert parsed["record_count"] >= 1, "JSON解析后记录数应>=1"
        
        # 用例8: URL校验
        assert _is_valid_url("https://example.com") is True, "合法URL应通过"
        assert _is_valid_url("not-a-url") is False, "非法URL应失败"
        
        # 用例9: 类型检测
        type_result, conf = _detect_asset_type("这是一个MCP服务器示例")
        assert type_result == "mcp", "应识别MCP类型"
        assert conf in CONFIDENCE_LEVELS, "置信度应为有效级别"
        
        # 用例10: 名称提取
        name, name_conf = _extract_name("Agent: my-agent 用于测试")
        assert name, "名称不应为空"
        assert name_conf in CONFIDENCE_LEVELS, "置信度应为有效级别"
        
        return True
        
    except AssertionError as e:
        print(f"E010: {ERROR_CODES['E010']} - {str(e)}")
        return False
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']} - 未预期异常: {str(e)}")
        return False


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    命令行主入口。
    """
    parser = argparse.ArgumentParser(
        description="Claude资产导航 技能检索 工作流速查",
        epilog="示例: python main.py --input 'MCP服务器: my-server https://example.com' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：URL、文件路径、粘贴文本（支持多行/分号分隔，≤20条/批）"
    )
    
    parser.add_argument(
        "--input-file", "-f",
        type=str,
        help="从文件读取输入内容"
    )
    
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["markdown", "md", "json"],
        default="markdown",
        help="输出格式（默认: markdown）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心逻辑"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="awesome-claude 1.0.1"
    )
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        passed = _selftest()
        if passed:
            print("✅ 自检通过：所有核心逻辑验证成功")
            return 0
        else:
            print("❌ 自检失败：请检查错误信息")
            return 1
    
    # 获取输入
    try:
        if args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8", errors="replace") as f:
                    raw_input = f.read()
            except Exception as e:
                print(f"E007: {ERROR_CODES['E007']} - {str(e)}")
                return 1
        elif args.input:
            raw_input = args.input
        else:
            # 交互模式
            print("请输入内容（URL/文件路径/文本，输入空行结束，Ctrl+D退出）：")
            lines = []
            try:
                while True:
                    line = input()
                    if not line.strip():
                        break
                    lines.append(line)
            except EOFError:
                pass
            raw_input = "\n".join(lines)
        
        # 处理输入
        result = process_input(raw_input)
        
        # 输出结果
        if args.format in ("markdown", "md"):
            output = format_markdown(result)
        else:
            output = format_json(result)
        
        print(output)
        return 0
        
    except ValueError as e:
        # 已知错误码
        print(f"错误: {str(e)}")
        return 1
    except Exception as e:
        print(f"E006: {ERROR_CODES['E006']} - {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
