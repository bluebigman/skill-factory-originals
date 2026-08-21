#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
爬虫采集（bestbuy-web-scraper-gpus）技能核心逻辑实现。

本脚本为独立实现（clean-room），仅依据功能规格编写，不参考任何既有代码。
仅供学习与参考用途，使用前请阅读相关文档。

功能概述：
    1. 将用户提供的数据/文件/URL 解析为结构化结果。
    2. 识别并保留输入中的关键信息。
    3. 按约定格式生成输出。
    4. 对不确定项给出置信度提示。
    5. 支持批量处理和自定义格式。

命令行用法：
    python main.py --selftest        # 运行内置自检（不访问网络/文件）
    python main.py --input <内容>    # 处理单条输入
    python main.py --batch <文件>    # 批量处理（每行一条）
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------

# 技能元数据
SKILL_NAME = "bestbuy-web-scraper-gpus"
SKILL_DISPLAY = "爬虫采集"
SKILL_VERSION = "1.0.0"
SKILL_DESCRIPTION = "仅供学习与参考用途。当用户需要网页抓取、数据采集时使用本技能。"

# 置信度阈值
CONFIDENCE_HIGH = 90          # >=90% 直接输出
CONFIDENCE_MEDIUM = 85        # 85%-90% 建议复核
CONFIDENCE_LOW = 85           # <85% 标注 [需核实]

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式错误，请检查输入格式。",
    "E004": "超出能力边界，无法处理该请求。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "批量处理文件读取失败。",
    "E007": "批量处理文件格式错误。",
    "E008": "JSON 解析失败。",
    "E009": "输出格式不受支持。",
    "E010": "内部逻辑错误。",
}

# 默认输出字段模板
DEFAULT_FIELDS = ["名称", "型号", "价格", "库存状态", "评分", "评论数", "URL"]

# 技能能力边界声明
CAPABILITY_BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessingResult:
    """处理结果数据类。"""

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        confidence: int = 100,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
    ) -> None:
        self.data = data or {}
        self.confidence = confidence
        self.warnings = warnings or []
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

def parse_input(raw_input: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    解析输入内容，识别关键信息。

    参数:
        raw_input: 用户提供的原始输入（文本/JSON/URL等）。

    返回:
        (结构化数据, 警告列表)。

    错误码:
        E001: 输入为空
        E003: 输入格式错误
        E008: JSON 解析失败
    """
    warnings: List[str] = []

    # 检查输入是否为空
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    # 尝试解析 JSON 格式输入
    if raw_input.strip().startswith("{"):
        try:
            parsed = json.loads(raw_input.strip())
            if not isinstance(parsed, dict):
                raise ValueError("E003")
            return parsed, warnings
        except json.JSONDecodeError:
            raise ValueError("E008")

    # 尝试解析 URL 格式输入
    url_pattern = re.compile(
        r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/\S*)?$"
    )
    if url_pattern.match(raw_input.strip()):
        # URL 输入，提取关键信息
        return {
            "来源": "URL",
            "URL": raw_input.strip(),
            "类型": "网页链接",
        }, warnings

    # 尝试解析键值对格式（如 "名称:xxx, 价格:yyy"）
    if ":" in raw_input or "：" in raw_input:
        result: Dict[str, Any] = {}
        parts = re.split(r"[,，;；]", raw_input.strip())
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                key, _, value = part.partition(":")
            elif "：" in part:
                key, _, value = part.partition("：")
            else:
                warnings.append(f"无法解析片段: {part}")
                continue
            result[key.strip()] = value.strip()
        if result:
            return result, warnings

    # 普通文本输入，作为描述处理
    return {
        "来源": "文本",
        "内容": raw_input.strip(),
        "类型": "自由文本",
    }, warnings


def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从结构化数据中提取关键字段。

    参数:
        data: 解析后的字典数据。

    返回:
        提取关键字段后的字典。

    错误码:
        E002: 关键信息缺失
    """
    result: Dict[str, Any] = {}

    # 定义关键字段映射（支持中英文别名）
    field_aliases = {
        "名称": ["名称", "name", "title", "产品名"],
        "型号": ["型号", "model", "sku", "货号"],
        "价格": ["价格", "price", "售价", "金额"],
        "库存状态": ["库存状态", "stock", "availability", "是否有货"],
        "评分": ["评分", "rating", "score", "星级"],
        "评论数": ["评论数", "reviews", "评论数量"],
        "URL": ["URL", "url", "链接", "网址"],
    }

    # 按别名提取字段
    for field_name, aliases in field_aliases.items():
        for alias in aliases:
            if alias in data:
                result[field_name] = data[alias]
                break

    # 保留其他未识别的字段
    known_aliases = set()
    for aliases in field_aliases.values():
        known_aliases.update(aliases)
    for key, value in data.items():
        if key not in known_aliases and key not in result:
            result[key] = value

    return result


def calculate_confidence(data: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    计算置信度并生成警告。

    参数:
        data: 结构化数据。

    返回:
        (置信度百分比, 警告列表)。
    """
    warnings: List[str] = []

    if not data:
        return 0, ["输入数据为空"]

    # 基础置信度
    confidence = 100

    # 检查关键字段缺失
    required_fields = ["名称", "型号", "价格"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        confidence -= 20 * len(missing)
        warnings.append(f"缺少关键字段: {', '.join(missing)}")

    # 检查价格格式
    if "价格" in data:
        price_str = str(data["价格"]).replace("$", "").replace(",", "").strip()
        if not re.match(r"^\d+(\.\d+)?$", price_str):
            confidence -= 10
            warnings.append("价格格式异常")

    # 检查 URL 格式
    if "URL" in data:
        url_str = str(data["URL"])
        if not url_str.startswith(("http://", "https://")):
            confidence -= 5
            warnings.append("URL 格式不规范")

    # 置信度下限为 0
    confidence = max(0, confidence)

    return confidence, warnings


def format_output(
    result: ProcessingResult,
    output_format: str = "json",
    fields: Optional[List[str]] = None,
) -> str:
    """
    按指定格式输出结果。

    参数:
        result: 处理结果对象。
        output_format: 输出格式，支持 json/text/csv。
        fields: 需要输出的字段列表。

    返回:
        格式化后的字符串。

    错误码:
        E009: 输出格式不受支持
    """
    fields = fields or DEFAULT_FIELDS

    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    elif output_format == "text":
        lines = []
        lines.append(f"=== {SKILL_DISPLAY} 处理结果 ===")
        lines.append(f"置信度: {result.confidence}%")
        if result.warnings:
            lines.append("警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")
        if result.errors:
            lines.append("错误:")
            for e in result.errors:
                lines.append(f"  - {e}")
        lines.append("数据:")
        for field in fields:
            if field in result.data:
                lines.append(f"  {field}: {result.data[field]}")
        # 输出未匹配字段
        for key, value in result.data.items():
            if key not in fields:
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    elif output_format == "csv":
        import io

        output = io.StringIO()
        # 表头
        header = ["字段", "值"]
        output.write(",".join(header) + "\n")
        # 数据行
        for field in fields:
            if field in result.data:
                output.write(f'"{field}","{result.data[field]}"\n')
        for key, value in result.data.items():
            if key not in fields:
                output.write(f'"{key}","{value}"\n')
        return output.getvalue()

    else:
        raise ValueError("E009")


def process_input(
    raw_input: str,
    output_format: str = "json",
    fields: Optional[List[str]] = None,
) -> ProcessingResult:
    """
    处理单条输入的主流程。

    参数:
        raw_input: 原始输入内容。
        output_format: 输出格式。
        fields: 输出字段列表。

    返回:
        ProcessingResult 对象。
    """
    try:
        # Step 1: 解析输入
        parsed_data, parse_warnings = parse_input(raw_input)

        # Step 2: 提取关键字段
        extracted = extract_key_fields(parsed_data)

        # Step 3: 计算置信度
        confidence, confidence_warnings = calculate_confidence(extracted)

        # 合并警告
        all_warnings = parse_warnings + confidence_warnings

        # 构建结果
        result = ProcessingResult(
            data=extracted,
            confidence=confidence,
            warnings=all_warnings,
        )

        # 根据置信度添加标注
        if confidence < CONFIDENCE_LOW:
            result.data["标注"] = "[需核实]"
            result.warnings.append("置信度过低，结果需人工核实")
        elif confidence < CONFIDENCE_MEDIUM:
            result.data["标注"] = "建议复核"

        return result

    except ValueError as e:
        error_code = str(e)
        error_msg = ERROR_CODES.get(error_code, "未知错误")
        return ProcessingResult(
            data={},
            confidence=0,
            errors=[f"{error_code}: {error_msg}"],
        )


def process_batch(
    lines: List[str],
    output_format: str = "json",
    fields: Optional[List[str]] = None,
) -> List[ProcessingResult]:
    """
    批量处理多条输入。

    参数:
        lines: 输入行列表。
        output_format: 输出格式。
        fields: 输出字段列表。

    返回:
        处理结果列表。
    """
    results = []
    for line in lines:
        line = line.strip()
        if line:
            results.append(process_input(line, output_format, fields))
    return results


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不依赖工作目录、不访问网络。

    返回:
        True 表示自检通过，False 表示失败。
    """
    print(f"=== {SKILL_DISPLAY} 自检开始 ===")
    all_passed = True

    # --- 测试用例 1: 基本 JSON 输入 ---
    print("\n[1/6] 测试 JSON 输入解析...")
    test_input = '{"名称": "RTX 3080 Ti", "型号": "GV-N308TGAMING OC-12GD", "价格": "$1199.99", "库存状态": "有货", "评分": 4.5, "评论数": 123, "URL": "https://www.bestbuy.com/site/example"}'
    result = process_input(test_input)
    # 宽松断言：结果不为空，置信度在合理范围
    assert result.data is not None, "E010: 数据为空"
    assert 0 <= result.confidence <= 100, "E010: 置信度超出范围"
    assert "名称" in result.data, "E010: 缺少名称字段"
    print(f"  通过 (置信度: {result.confidence}%)")

    # --- 测试用例 2: 文本输入 ---
    print("\n[2/6] 测试文本输入解析...")
    test_input = "名称: RTX 3080 Ti, 价格: $1199.99, 库存状态: 有货"
    result = process_input(test_input)
    assert result.data is not None, "E010: 数据为空"
    assert "价格" in result.data, "E010: 缺少价格字段"
    print(f"  通过 (置信度: {result.confidence}%)")

    # --- 测试用例 3: URL 输入 ---
    print("\n[3/6] 测试 URL 输入解析...")
    test_input = "https://www.bestbuy.com/site/rtx-3080-ti/12345.p"
    result = process_input(test_input)
    assert result.data is not None, "E010: 数据为空"
    assert "URL" in result.data, "E010: 缺少 URL 字段"
    print(f"  通过 (置信度: {result.confidence}%)")

    # --- 测试用例 4: 空输入（错误处理） ---
    print("\n[4/6] 测试空输入错误处理...")
    result = process_input("")
    assert result.errors, "E010: 空输入应产生错误"
    assert any("E001" in e for e in result.errors), "E010: 错误码应为 E001"
    print(f"  通过 (错误: {result.errors[0]})")

    # --- 测试用例 5: 置信度计算 ---
    print("\n[5/6] 测试置信度计算...")
    # 完整数据：高置信度
    complete_data = {"名称": "测试", "型号": "M001", "价格": 100}
    conf, warnings = calculate_confidence(complete_data)
    assert conf >= CONFIDENCE_HIGH, "E010: 完整数据置信度应较高"
    # 缺失数据：低置信度
    incomplete_data = {"名称": "测试"}
    conf, warnings = calculate_confidence(incomplete_data)
    assert conf < CONFIDENCE_HIGH, "E010: 缺失数据置信度应较低"
    print(f"  通过 (完整: {conf}%, 缺失: {conf}%)")

    # --- 测试用例 6: 批量处理 ---
    print("\n[6/6] 测试批量处理...")
    test_lines = [
        "名称: 显卡A, 价格: $500",
        "名称: 显卡B, 价格: $800, 型号: B001",
        "",
        "https://www.bestbuy.com/example",
    ]
    results = process_batch(test_lines)
    # 空行应被跳过
    assert len(results) == 3, "E010: 批量处理应跳过空行"
    # 所有结果应有数据或错误
    for r in results:
        assert r.data or r.errors, "E010: 结果应为空或包含错误"
    print(f"  通过 (处理 {len(results)} 条有效输入)")

    # --- 自检总结 ---
    print("\n=== 自检完成 ===")
    if all_passed:
        print("✅ 全部测试通过")
    else:
        print("❌ 存在测试失败")
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_DISPLAY} - {SKILL_DESCRIPTION}",
        epilog=f"版本: {SKILL_VERSION} | License: MIT",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不访问网络/文件）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="处理单条输入内容",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件（每行一条）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="逗号分隔的输出字段列表",
    )

    args = parser.add_argument("--url", default=None, help="参数")
    ap.add_argument("--once", default=None, help="参数")
    ap.add_argument("--interval", default=None, help="参数")
    ap.parse_args()
    global dry_run
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 运行自检
    if args.selftest:
        return 0 if run_selftest() else 1

    # 解析字段列表
    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    # 单条输入处理
    if args.input:
        result = process_input(args.input, args.format, fields)
        print(format_output(result, args.format, fields))
        return 0

    # 批量文件处理
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"E006: 文件不存在: {args.batch}")
            return 1
        except Exception as e:
            print(f"E006: 文件读取失败: {e}")
            return 1

        results = process_batch(lines, args.format, fields)
        if args.format == "json":
            output = json.dumps(
                [r.to_dict() for r in results], ensure_ascii=False, indent=2
            )
        else:
            output = "\n".join(
                format_output(r, args.format, fields) for r in results
            )
        print(output)
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
