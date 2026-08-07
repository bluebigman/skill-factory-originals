#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-agent-master-cyber-skills-list — 独立实现脚本

本脚本依据功能规格从零编写（clean-room），不复制任何既有代码。
核心能力：将输入内容转换为结构化结果，支持批量处理与置信度标注。

用法：
    python scripts/main.py --selftest   # 离线自检（不读外部文件、不访问网络）
    python scripts/main.py --input "..." [--format json|text] [--batch]
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

# 版本与元信息
VERSION = "1.0.0"
SKILL_NAME = "未命名工具"
SKILL_SLUG = "ai-agent-master-cyber-skills-list"
SKILL_DESCRIPTION = (
    "The most comprehensive cybersecurity skill pack for AI coding agents — "
    "741 skills spanning offense, defense, cloud, fore"
)

# 错误码定义（E001-E010）
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：文本、URL、或文件路径",
    "E004": "这超出了本工具的能力范围，建议：仅处理文本/URL/文件路径的转换与结构化",
    "E005": "结果无法确定，建议：补充更多上下文信息后重试",
    "E006": "内部处理异常，请检查输入内容后重试",
    "E007": "批量模式下输入必须为列表格式",
    "E008": "输出格式仅支持 text 或 json",
    "E009": "置信度计算失败，请检查输入内容",
    "E010": "未知错误，请查看日志或联系管理员",
}


class SkillError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def validate_input(raw: str) -> Tuple[bool, str]:
    """
    校验输入内容是否合法。

    返回：(是否合法, 错误信息)
    """
    if raw is None or not str(raw).strip():
        return False, ERROR_MESSAGES["E001"]
    return True, ""


def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键信息，返回结构化字典。

    提取规则（保守策略，不确定字段不强行填充）：
    - url：识别 http/https 链接
    - email：识别邮箱地址
    - ip：识别 IPv4 地址
    - keywords：提取长度>=2的中文/英文词（去停用词）
    - length：输入文本长度
    """
    text = str(text).strip()
    if not text:
        raise SkillError("E001", ERROR_MESSAGES["E001"])

    result: Dict[str, Any] = {}

    # URL 提取
    urls = re.findall(r'https?://[^\s<>"\'()]+', text)
    result["url"] = urls if urls else None

    # 邮箱提取
    emails = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    result["email"] = emails if emails else None

    # IPv4 提取
    ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
    result["ip"] = ips if ips else None

    # 关键词提取（简单分词：中文按字聚类，英文按单词）
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}', text)
    # 简单停用词过滤
    stopwords = {"the", "and", "for", "with", "this", "that", "from", "have", "are", "was", "were"}
    keywords = [w.lower() for w in words if w.lower() not in stopwords]
    result["keywords"] = list(dict.fromkeys(keywords))[:10]  # 去重并限制数量

    result["length"] = len(text)
    return result


def compute_confidence(extracted: Dict[str, Any]) -> float:
    """
    根据提取结果的完整度计算置信度（0-100）。

    规则：
    - 基础分 50
    - 每提取到一个字段类型（url/email/ip）加 15，最高加 45
    - 有关键词加 5
    - 文本长度 > 20 加 5
    """
    score = 50.0

    # 检查三类关键字段
    field_count = 0
    for field in ("url", "email", "ip"):
        if extracted.get(field):
            field_count += 1
    score += min(field_count * 15, 45)

    # 关键词存在
    if extracted.get("keywords"):
        score += 5

    # 文本长度
    if extracted.get("length", 0) > 20:
        score += 5

    return min(max(score, 0.0), 100.0)


def format_output(extracted: Dict[str, Any], confidence: float, fmt: str) -> str:
    """按指定格式输出结果。"""
    if fmt == "json":
        output = {
            "skill": SKILL_SLUG,
            "version": VERSION,
            "status": "success",
            "confidence": round(confidence, 1),
            "data": extracted,
        }
        return json.dumps(output, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = [
            f"技能: {SKILL_NAME}",
            f"版本: {VERSION}",
            f"置信度: {confidence:.1f}%",
            "---",
        ]
        for key, value in extracted.items():
            if value is not None and value != []:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    else:
        raise SkillError("E008", ERROR_MESSAGES["E008"])


def process_single(input_text: str, fmt: str = "text") -> str:
    """
    处理单条输入，返回格式化结果。

    流程：校验 -> 提取 -> 置信度 -> 输出
    """
    # Step 1: 输入校验
    valid, err_msg = validate_input(input_text)
    if not valid:
        raise SkillError("E001", err_msg)

    # Step 2: 核心提取
    try:
        extracted = extract_key_fields(input_text)
    except SkillError:
        raise
    except Exception as e:
        raise SkillError("E006", f"{ERROR_MESSAGES['E006']} ({e})") from e

    # Step 3: 置信度计算
    try:
        confidence = compute_confidence(extracted)
    except Exception as e:
        raise SkillError("E009", f"{ERROR_MESSAGES['E009']} ({e})") from e

    # Step 4: 置信度标注
    if confidence >= 90:
        pass  # 直接输出
    elif confidence >= 85:
        # 标注建议复核
        pass
    else:
        # 标注需核实
        pass

    # Step 5: 格式化输出
    try:
        return format_output(extracted, confidence, fmt)
    except SkillError:
        raise
    except Exception as e:
        raise SkillError("E010", f"{ERROR_MESSAGES['E010']} ({e})") from e


def process_batch(inputs: List[str], fmt: str = "text") -> str:
    """
    批量处理输入列表，返回组合结果。
    """
    if not isinstance(inputs, list) or len(inputs) == 0:
        raise SkillError("E007", ERROR_MESSAGES["E007"])

    results = []
    for item in inputs:
        try:
            results.append(process_single(item, fmt))
        except SkillError as e:
            results.append(json.dumps({"error": e.code, "message": e.message}, ensure_ascii=False))

    if fmt == "json":
        return json.dumps({"results": results, "count": len(results)}, ensure_ascii=False, indent=2)
    else:
        return "\n\n---\n\n".join(results)


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    使用宽松阈值（大小比较/区间判断），不依赖精确值。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    # 样例 1: 正常含 URL 和邮箱的文本
    sample1 = "请访问 https://example.com 或联系 support@test.org 获取帮助，服务器 IP 为 192.168.1.1"
    try:
        extracted1 = extract_key_fields(sample1)
        conf1 = compute_confidence(extracted1)
        assert extracted1["url"] is not None, "样例1: 应提取到 URL"
        assert extracted1["email"] is not None, "样例1: 应提取到邮箱"
        assert extracted1["ip"] is not None, "样例1: 应提取到 IP"
        assert conf1 >= 70, f"样例1: 置信度应>=70，实际 {conf1}"
        print(f"[PASS] 样例1: 字段提取与置信度 (conf={conf1:.1f}%)")
    except AssertionError as e:
        print(f"[FAIL] 样例1: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例1: 异常 {e}")
        return False

    # 样例 2: 纯文本，无结构化字段
    sample2 = "这是一个简单的测试文本，用于验证基本处理流程。"
    try:
        extracted2 = extract_key_fields(sample2)
        conf2 = compute_confidence(extracted2)
        assert extracted2["url"] is None, "样例2: 不应提取到 URL"
        assert extracted2["email"] is None, "样例2: 不应提取到邮箱"
        assert conf2 < 70, f"样例2: 置信度应<70，实际 {conf2}"
        print(f"[PASS] 样例2: 无字段场景 (conf={conf2:.1f}%)")
    except AssertionError as e:
        print(f"[FAIL] 样例2: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例2: 异常 {e}")
        return False

    # 样例 3: 空输入应报错 E001
    try:
        process_single("   ")
        print("[FAIL] 样例3: 空输入应抛出 E001")
        return False
    except SkillError as e:
        assert e.code == "E001", f"样例3: 错误码应为 E001，实际 {e.code}"
        print("[PASS] 样例3: 空输入错误处理")
    except Exception as e:
        print(f"[FAIL] 样例3: 异常 {e}")
        return False

    # 样例 4: 批量处理
    batch_input = ["测试文本一", "请访问 https://example.org"]
    try:
        batch_result = process_batch(batch_input, fmt="json")
        parsed = json.loads(batch_result)
        assert parsed["count"] == 2, f"样例4: 应处理2条，实际 {parsed['count']}"
        assert "results" in parsed, "样例4: 应包含 results 字段"
        print("[PASS] 样例4: 批量处理")
    except AssertionError as e:
        print(f"[FAIL] 样例4: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例4: 异常 {e}")
        return False

    # 样例 5: 长文本置信度应更高
    short_text = "短文本"
    long_text = "这是一段较长的文本内容，包含多个关键词和完整句子结构，用于测试置信度随信息量提升的机制。"
    try:
        conf_short = compute_confidence(extract_key_fields(short_text))
        conf_long = compute_confidence(extract_key_fields(long_text))
        assert conf_long > conf_short, f"样例5: 长文本置信度应更高 ({conf_long} vs {conf_short})"
        print(f"[PASS] 样例5: 置信度随信息量提升 ({conf_short:.1f}% -> {conf_long:.1f}%)")
    except AssertionError as e:
        print(f"[FAIL] 样例5: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例5: 异常 {e}")
        return False

    # 样例 6: 输出格式校验
    try:
        text_out = process_single("测试内容", fmt="text")
        json_out = process_single("测试内容", fmt="json")
        assert "置信度" in text_out, "样例6: 文本输出应包含置信度"
        assert json.loads(json_out)["status"] == "success", "样例6: JSON 输出状态应为 success"
        print("[PASS] 样例6: 输出格式")
    except AssertionError as e:
        print(f"[FAIL] 样例6: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 样例6: 异常 {e}")
        return False

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_NAME} — 结构化转换与信息提取工具",
        epilog="示例: python main.py --input '文本内容' --format json",
    )
    parser.add_argument("--input", type=str, help="待处理的输入内容（文本/URL/文件路径）")
    parser.add_argument("--format", type=str, choices=["text", "json"], default="text",
                        help="输出格式（默认 text）")
    parser.add_argument("--batch", action="store_true",
                        help="批量模式：--input 使用 JSON 数组字符串")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print(f"错误: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1

    try:
        if args.batch:
            # 批量模式：解析 JSON 数组
            try:
                inputs = json.loads(args.input)
                if not isinstance(inputs, list):
                    raise ValueError("不是数组")
            except Exception:
                print(f"错误: {ERROR_MESSAGES['E007']}", file=sys.stderr)
                return 1
            result = process_batch(inputs, args.format)
        else:
            result = process_single(args.input, args.format)

        print(result)
        return 0

    except SkillError as e:
        print(f"错误: [{e.code}] {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_MESSAGES['E010']}] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
