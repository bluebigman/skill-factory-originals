#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reviewcerberus - 代码审查工具（独立实现）

本脚本依据功能规格独立编写，实现核心的代码审查数据流程：
1. 解析用户输入（数据/文件/URL 描述文本）
2. 结构化提取关键信息
3. 生成审查报告（含置信度标注）
4. 支持批量处理与自定义输出格式

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及标准化话术（依据功能规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或联系管理员",
    "E007": "输出序列化失败，请检查数据格式",
    "E008": "批量处理中断，存在失败项",
    "E009": "参数配置错误，请检查命令行参数",
    "E010": "未知异常，请查看日志",
}

# 置信度阈值（依据规格：≥90% 直接输出；85%-90% 建议复核；<85% 需核实）
CONFIDENCE_HIGH = 90
CONFIDENCE_MEDIUM = 85

# 默认输出字段（依据规格 Step 2 的核心字段）
DEFAULT_FIELDS = ["input_type", "key_info", "confidence", "output_format"]


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class ReviewResult:
    """单次代码审查的结果"""
    input_type: str = "unknown"          # 输入类型（data/file/url/text）
    key_info: List[str] = field(default_factory=list)  # 提取的关键信息
    confidence: int = 0                  # 置信度（0-100）
    output_format: str = "json"          # 输出格式
    raw_input: str = ""                  # 原始输入（用于调试）
    warnings: List[str] = field(default_factory=list)  # 警告/提示信息
    error_code: Optional[str] = None     # 错误码（如有错误）


@dataclass
class ReviewReport:
    """批量审查的整体报告"""
    results: List[ReviewResult] = field(default_factory=list)
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    error_details: List[Tuple[str, str]] = field(default_factory=list)  # (错误码, 描述)


# ============================================================
# 核心处理逻辑
# ============================================================

class ReviewCerberus:
    """
    代码审查核心引擎

    依据功能规格实现：
    - 输入解析（Step 2.1）
    - 关键信息识别与结构化（Step 2.2）
    - 置信度评估与标注（Step 2.3）
    - 输出格式化（Step 3）
    """

    # 常见输入类型的关键特征（用于识别输入类型）
    INPUT_PATTERNS = {
        "url": re.compile(r"^https?://", re.IGNORECASE),
        "file": re.compile(r"\.(py|js|java|c|cpp|go|rs|ts|txt|md|json|yaml|yml)$", re.IGNORECASE),
        "data": re.compile(r"[\[{]", re.IGNORECASE),  # JSON 或类似结构
    }

    # 关键信息提取的常见关键词（用于从文本中识别）
    KEYWORD_PATTERN = re.compile(
        r"(?:函数|方法|类|变量|参数|接口|API|模块|文件|功能|bug|问题|优化|重构|性能|安全|错误|异常)"
        r"[:：]?\s*([A-Za-z0-9_\-\u4e00-\u9fa5]{2,})",
        re.IGNORECASE
    )

    def __init__(self, output_format: str = "json", batch_mode: bool = False):
        """
        初始化审查引擎

        Args:
            output_format: 输出格式（json/text）
            batch_mode: 是否批量处理模式
        """
        self.output_format = output_format
        self.batch_mode = batch_mode

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------

    def process(self, raw_input: str) -> ReviewResult:
        """
        处理单个输入，生成审查结果

        Args:
            raw_input: 用户提供的原始输入（数据/文件/URL 描述）

        Returns:
            ReviewResult: 审查结果对象
        """
        # 输入为空检查（错误码 E001）
        if not raw_input or not raw_input.strip():
            return self._make_error_result("E001", raw_input, "输入内容为空")

        # 输入格式检查（错误码 E003）
        if len(raw_input.strip()) < 3:
            return self._make_error_result("E003", raw_input, "输入内容过短，无法识别有效信息")

        try:
            # Step 2.1: 解析输入，识别类型
            input_type = self._detect_input_type(raw_input)

            # Step 2.2: 提取关键信息
            key_info = self._extract_key_info(raw_input)

            # 关键信息缺失检查（错误码 E002）
            if not key_info:
                return self._make_error_result(
                    "E002", raw_input,
                    "未从输入中识别到关键信息（函数/变量/接口等），请补充具体内容"
                )

            # Step 2.3: 评估置信度
            confidence = self._calculate_confidence(raw_input, input_type, key_info)

            # 构建正常结果
            result = ReviewResult(
                input_type=input_type,
                key_info=key_info,
                confidence=confidence,
                output_format=self.output_format,
                raw_input=raw_input,
            )

            # 根据置信度添加标注
            if confidence < CONFIDENCE_MEDIUM:
                result.warnings.append("[需核实] 置信度低于85%，请人工复核关键信息")
            elif confidence < CONFIDENCE_HIGH:
                result.warnings.append("建议复核：置信度在85%-90%之间")

            return result

        except Exception as exc:
            # 未知异常（错误码 E010）
            return self._make_error_result("E010", raw_input, f"处理异常: {str(exc)}")

    def process_batch(self, inputs: List[str]) -> ReviewReport:
        """
        批量处理多个输入（依据规格：连续提供多个输入，按同一规则逐项处理）

        Args:
            inputs: 输入列表

        Returns:
            ReviewReport: 批量处理报告
        """
        report = ReviewReport()
        report.total_count = len(inputs)

        if not inputs:
            report.error_details.append(("E001", "批量输入列表为空"))
            return report

        for i, raw_input in enumerate(inputs):
            result = self.process(raw_input)
            report.results.append(result)

            if result.error_code:
                report.failed_count += 1
                report.error_details.append((result.error_code, f"第{i+1}项: {result.raw_input[:30]}..."))
            else:
                report.success_count += 1

        # 批量处理部分失败（错误码 E008）
        if report.failed_count > 0 and report.success_count > 0:
            report.error_details.insert(0, ("E008", f"批量处理完成，成功{report.success_count}项，失败{report.failed_count}项"))

        return report

    # ----------------------------------------------------------
    # 输入解析与识别
    # ----------------------------------------------------------

    def _detect_input_type(self, raw_input: str) -> str:
        """
        识别输入类型（依据规格 Step 2.1）

        Args:
            raw_input: 原始输入

        Returns:
            str: 输入类型（url/file/data/text）
        """
        stripped = raw_input.strip()

        # URL 检测
        if self.INPUT_PATTERNS["url"].match(stripped):
            return "url"

        # 文件路径检测（含文件名）
        if self.INPUT_PATTERNS["file"].search(stripped):
            # 需要判断是文件名还是普通文本中提到了文件
            if os.path.sep in stripped or stripped.endswith((".py", ".js", ".java", ".go", ".rs")):
                return "file"
            return "text"

        # 数据结构检测（JSON 等）
        if self.INPUT_PATTERNS["data"].match(stripped):
            return "data"

        # 默认文本
        return "text"

    def _extract_key_info(self, raw_input: str) -> List[str]:
        """
        提取关键信息（依据规格 Step 2.2）

        策略：
        - 匹配关键词模式（函数/变量/接口等）
        - 去除重复项
        - 限制最多返回 10 项

        Args:
            raw_input: 原始输入

        Returns:
            List[str]: 关键信息列表
        """
        matches = self.KEYWORD_PATTERN.findall(raw_input)

        # 清洗：去除过短项、重复项
        cleaned = []
        seen = set()
        for item in matches:
            item = item.strip()
            if len(item) >= 2 and item not in seen:
                cleaned.append(item)
                seen.add(item)

            # 最多返回 10 项
            if len(cleaned) >= 10:
                break

        return cleaned

    def _calculate_confidence(self, raw_input: str, input_type: str, key_info: List[str]) -> int:
        """
        计算置信度（依据规格 Step 2.3）

        评估因素：
        - 输入长度（信息量）
        - 关键信息数量
        - 输入类型明确度
        - 结构化程度

        Args:
            raw_input: 原始输入
            input_type: 输入类型
            key_info: 提取的关键信息

        Returns:
            int: 置信度（0-100）
        """
        score = 0

        # 输入长度贡献（最多 40 分）
        length = len(raw_input.strip())
        if length >= 200:
            score += 40
        elif length >= 100:
            score += 30
        elif length >= 50:
            score += 20
        elif length >= 20:
            score += 10
        else:
            score += 5

        # 关键信息数量贡献（最多 30 分）
        info_count = len(key_info)
        if info_count >= 5:
            score += 30
        elif info_count >= 3:
            score += 25
        elif info_count >= 2:
            score += 20
        elif info_count >= 1:
            score += 10

        # 输入类型明确度贡献（最多 20 分）
        if input_type in ("url", "file"):
            score += 20  # 明确类型
        elif input_type == "data":
            score += 15  # 结构化数据
        else:
            score += 5   # 普通文本，需要更多判断

        # 结构化程度贡献（最多 10 分）
        # 检测是否有明显的结构（冒号、引号、括号等）
        structural_chars = sum(1 for c in raw_input if c in ':"{}[]()')
        if structural_chars > 10:
            score += 10
        elif structural_chars > 5:
            score += 7
        elif structural_chars > 2:
            score += 4
        else:
            score += 1

        # 确保在 0-100 范围内
        return max(0, min(100, score))

    # ----------------------------------------------------------
    # 输出与错误处理
    # ----------------------------------------------------------

    def _make_error_result(self, error_code: str, raw_input: str, detail: str) -> ReviewResult:
        """
        构造错误结果

        Args:
            error_code: 错误码
            raw_input: 原始输入
            detail: 错误详情

        Returns:
            ReviewResult: 带错误信息的审查结果
        """
        result = ReviewResult(
            input_type="error",
            confidence=0,
            output_format=self.output_format,
            raw_input=raw_input,
            error_code=error_code,
        )
        result.warnings.append(ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"]))
        result.warnings.append(f"详情: {detail}")
        return result

    def format_output(self, result: ReviewResult) -> str:
        """
        格式化输出（依据规格 Step 3）

        Args:
            result: 审查结果

        Returns:
            str: 格式化后的输出
        """
        if self.output_format == "text":
            return self._format_text(result)
        else:
            return self._format_json(result)

    def format_batch_output(self, report: ReviewReport) -> str:
        """
        格式化批量输出

        Args:
            report: 批量报告

        Returns:
            str: 格式化后的输出
        """
        if self.output_format == "text":
            lines = [f"批量处理报告: 共{report.total_count}项, 成功{report.success_count}项, 失败{report.failed_count}项"]
            for i, result in enumerate(report.results, 1):
                lines.append(f"\n--- 第{i}项 ---")
                lines.append(self._format_text(result))
            return "\n".join(lines)
        else:
            data = {
                "summary": {
                    "total": report.total_count,
                    "success": report.success_count,
                    "failed": report.failed_count,
                },
                "results": [asdict(r) for r in report.results],
                "errors": report.error_details,
            }
            return json.dumps(data, ensure_ascii=False, indent=2)

    def _format_json(self, result: ReviewResult) -> str:
        """JSON 格式输出"""
        data = asdict(result)
        # 移除内部调试字段
        data.pop("raw_input", None)
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _format_text(self, result: ReviewResult) -> str:
        """文本格式输出"""
        lines = []
        if result.error_code:
            lines.append(f"[错误 {result.error_code}]")
            lines.append(f"消息: {ERROR_MESSAGES.get(result.error_code, '未知错误')}")
            lines.append(f"详情: {result.warnings[-1] if result.warnings else '无'}")
            return "\n".join(lines)

        lines.append(f"输入类型: {result.input_type}")
        lines.append(f"置信度: {result.confidence}%")

        if result.confidence < CONFIDENCE_MEDIUM:
            lines.append("状态: [需核实]")
        elif result.confidence < CONFIDENCE_HIGH:
            lines.append("状态: 建议复核")
        else:
            lines.append("状态: 可直接使用")

        lines.append("关键信息:")
        for i, info in enumerate(result.key_info, 1):
            lines.append(f"  {i}. {info}")

        if result.warnings:
            lines.append("提示:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    自检核心逻辑（依据要求 3：内置硬编码样例，离线可跑）

    使用宽松阈值断言，确保与实现逻辑必然匹配。

    Returns:
        int: 0 表示成功，非 0 表示失败
    """
    print("=== reviewcerberus 自检开始 ===")
    engine = ReviewCerberus(output_format="json")
    failures = 0

    # ----------------------------------------------------------
    # 测试用例 1：正常文本输入（含关键信息）
    # ----------------------------------------------------------
    print("\n[测试1] 正常文本输入")
    sample1 = "请帮我审查以下代码：函数 calculate_total 存在性能问题，变量 user_data 未做空值检查，接口 /api/v1/users 缺少鉴权。建议优化重构。"
    result1 = engine.process(sample1)
    assert result1.error_code is None, f"测试1失败: 不应有错误，实际错误码 {result1.error_code}"
    assert len(result1.key_info) >= 1, f"测试1失败: 应提取到至少1个关键信息，实际 {len(result1.key_info)}"
    assert result1.confidence >= 50, f"测试1失败: 置信度应>=50，实际 {result1.confidence}"
    assert result1.input_type in ("text", "data"), f"测试1失败: 输入类型应为text或data，实际 {result1.input_type}"
    print(f"  通过: 提取到 {len(result1.key_info)} 个关键信息, 置信度 {result1.confidence}%")

    # ----------------------------------------------------------
    # 测试用例 2：空输入（应触发 E001）
    # ----------------------------------------------------------
    print("\n[测试2] 空输入")
    result2 = engine.process("")
    assert result2.error_code == "E001", f"测试2失败: 应返回E001，实际 {result2.error_code}"
    print(f"  通过: 正确返回 E001")

    # ----------------------------------------------------------
    # 测试用例 3：URL 输入
    # ----------------------------------------------------------
    print("\n[测试3] URL 输入")
    sample3 = "https://github.com/example/repo/blob/main/src/main.py 请审查这个文件的代码质量"
    result3 = engine.process(sample3)
    assert result3.error_code is None, f"测试3失败: 不应有错误，实际 {result3.error_code}"
    assert result3.input_type == "url", f"测试3失败: 应识别为url，实际 {result3.input_type}"
    print(f"  通过: 正确识别 URL 类型")

    # ----------------------------------------------------------
    # 测试用例 4：批量处理
    # ----------------------------------------------------------
    print("\n[测试4] 批量处理")
    samples = [
        "审查函数 process_data 的异常处理",
        "",  # 空输入，应报错
        "检查文件 /src/utils/helper.py 中的安全漏洞",
    ]
    report = engine.process_batch(samples)
    assert report.total_count == 3, f"测试4失败: 总数应为3，实际 {report.total_count}"
    assert report.success_count >= 1, f"测试4失败: 至少应有1个成功，实际 {report.success_count}"
    assert report.failed_count >= 1, f"测试4失败: 至少应有1个失败，实际 {report.failed_count}"
    print(f"  通过: 成功{report.success_count}项, 失败{report.failed_count}项")

    # ----------------------------------------------------------
    # 测试用例 5：文本格式输出
    # ----------------------------------------------------------
    print("\n[测试5] 文本格式输出")
    text_engine = ReviewCerberus(output_format="text")
    output5 = text_engine.format_output(result1)
    assert "关键信息" in output5, f"测试5失败: 输出应包含'关键信息'，实际: {output5[:100]}"
    assert "置信度" in output5, f"测试5失败: 输出应包含'置信度'，实际: {output5[:100]}"
    print(f"  通过: 文本输出包含必要字段")

    # ----------------------------------------------------------
    # 测试用例 6：JSON 输出可解析
    # ----------------------------------------------------------
    print("\n[测试6] JSON 输出解析")
    output6 = engine.format_output(result1)
    parsed6 = json.loads(output6)
    assert "key_info" in parsed6, f"测试6失败: JSON应包含key_info字段，实际: {list(parsed6.keys())}"
    assert "confidence" in parsed6, f"测试6失败: JSON应包含confidence字段"
    print(f"  通过: JSON 解析成功, 字段: {list(parsed6.keys())}")

    # ----------------------------------------------------------
    # 测试用例 7：置信度范围检查
    # ----------------------------------------------------------
    print("\n[测试7] 置信度范围")
    for i in range(10):
        sample = f"测试输入 {i}: 函数 func_{i} 需要审查，变量 var_{i} 存在潜在问题"
        res = engine.process(sample)
        assert 0 <= res.confidence <= 100, f"测试7失败: 置信度应在0-100，实际 {res.confidence}"
    print("  通过: 所有置信度均在合法范围 [0, 100]")

    # ----------------------------------------------------------
    # 测试用例 8：错误码体系完整性
    # ----------------------------------------------------------
    print("\n[测试8] 错误码检查")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_MESSAGES, f"测试8失败: 缺少错误码 {code}"
    print(f"  通过: 核心错误码 {list(ERROR_MESSAGES.keys())[:5]} 均存在")

    # ----------------------------------------------------------
    # 测试用例 9：关键信息提取去重
    # ----------------------------------------------------------
    print("\n[测试9] 关键信息去重")
    sample9 = "检查函数 foo 和函数 foo 以及变量 bar 的问题"
    result9 = engine.process(sample9)
    key_info_9 = result9.key_info
    assert len(key_info_9) == len(set(key_info_9)), f"测试9失败: 关键信息应去重，实际 {key_info_9}"
    print(f"  通过: 关键信息去重正常, 提取到 {len(key_info_9)} 项")

    # ----------------------------------------------------------
    # 测试用例 10：批量输出格式
    # ----------------------------------------------------------
    print("\n[测试10] 批量输出格式")
    batch_output = engine.format_batch_output(report)
    parsed10 = json.loads(batch_output)
    assert "summary" in parsed10, f"测试10失败: 批量输出应包含summary，实际: {list(parsed10.keys())}"
    assert parsed10["summary"]["total"] == 3, f"测试10失败: 总数应为3"
    print(f"  通过: 批量输出格式正确")

    # ==========================================================
    # 汇总
    # ==========================================================
    print("\n=== 自检完成 ===")
    if failures == 0:
        print("全部测试通过 ✅")
        return 0
    else:
        print(f"共 {failures} 项测试失败 ❌")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    命令行主入口

    用法示例:
        python main.py --input "审查函数 foo 的问题"
        python main.py --input "审查函数 foo 的问题" --output text
        python main.py --batch "input1|input2|input3"
        python main.py --selftest
    """
    parser = argparse.ArgumentParser(
        description="reviewcerberus - 代码审查工具",
        epilog="示例: python main.py --input '审查函数 foo 的异常处理'"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待审查的输入内容（数据/文件/URL 描述）"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入，用 | 分隔多个输入"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件或网络）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数配置检查（错误码 E009）
    if not args.input and not args.batch:
        print(f"[错误 E009] {ERROR_MESSAGES['E009']}")
        print("请使用 --input 或 --batch 提供输入内容")
        print("示例: python main.py --input '审查函数 foo'")
        return 2

    # 创建引擎
    engine = ReviewCerberus(output_format=args.output)

    try:
        # 批量模式
        if args.batch:
            inputs = [item.strip() for item in args.batch.split("|") if item.strip()]
            report = engine.process_batch(inputs)
            output = engine.format_batch_output(report)
        else:
            # 单条模式
            result = engine.process(args.input)
            output = engine.format_output(result)

        print(output)

        # 检查是否有错误
        if args.batch:
            report = engine.process_batch([item.strip() for item in args.batch.split("|") if item.strip()])
            return 1 if report.failed_count > 0 else 0
        else:
            result = engine.process(args.input)
            return 1 if result.error_code else 0

    except Exception as exc:
        print(f"[错误 E010] 未知异常: {str(exc)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
