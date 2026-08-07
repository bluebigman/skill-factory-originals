#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章处理工具 - 独立实现脚本

功能：将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理与自定义格式。
本脚本为 clean-room 实现，仅依据功能规格编写，不包含任何既有代码。

运行方式：
    python scripts/main.py --selftest     # 离线自检核心逻辑
    python scripts/main.py --input "数据内容"   # 处理输入数据
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出格式不支持，请选择支持的格式",
    "E008": "批量处理中断，请检查输入项",
    "E009": "文件读取失败，请检查文件路径",
    "E010": "参数错误，请检查命令行参数",
}


class AppError(Exception):
    """应用自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class ArticleInfo:
    """文章信息结构化对象"""

    def __init__(
        self,
        title: str = "",
        author: str = "",
        content: str = "",
        source: str = "",
        url: str = "",
        publish_time: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.title = title
        self.author = author
        self.content = content
        self.source = source
        self.url = url
        self.publish_time = publish_time
        self.extra = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "content": self.content,
            "source": self.source,
            "url": self.url,
            "publish_time": self.publish_time,
            "extra": self.extra,
        }


class ProcessResult:
    """处理结果对象，包含置信度标注"""

    def __init__(self, data: Any, confidence: float, warnings: Optional[List[str]] = None):
        self.data = data
        self.confidence = confidence  # 0-100
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "confidence_level": self._get_confidence_level(),
            "warnings": self.warnings,
            "processed_at": datetime.now().isoformat(),
        }

    def _get_confidence_level(self) -> str:
        """根据置信度返回标注等级"""
        if self.confidence >= 90:
            return "直接输出"
        elif self.confidence >= 80:
            return "建议复核"
        else:
            return "[需核实]"


# ============================================================
# 核心处理逻辑
# ============================================================
class ArticleProcessor:
    """文章处理核心类"""

    # 可识别的关键字段名
    KEY_FIELDS = ["title", "author", "content", "source", "url", "publish_time"]

    def __init__(self):
        self.stats = {"processed": 0, "warnings": 0, "errors": []}

    def process_input(self, raw_input: str, output_format: str = "json") -> ProcessResult:
        """
        处理输入内容，转换为结构化结果

        Args:
            raw_input: 用户提供的原始输入（文本/JSON/URL等）
            output_format: 输出格式（json/dict）

        Returns:
            ProcessResult: 处理结果

        Raises:
            AppError: 处理错误（E001-E010）
        """
        # 空输入检查
        if not raw_input or not raw_input.strip():
            raise AppError("E001")

        # 尝试解析输入
        parsed_data = self._parse_input(raw_input)

        # 提取关键信息
        article = self._extract_article_info(parsed_data)

        # 检查关键信息完整性
        missing_fields = self._get_missing_fields(article)
        if missing_fields:
            missing_str = ", ".join(missing_fields)
            raise AppError("E002", f"还缺少以下信息，请补充：{missing_str}")

        # 计算置信度
        confidence = self._calculate_confidence(article)

        # 生成输出
        if output_format == "json":
            output_data = json.dumps(article.to_dict(), ensure_ascii=False, indent=2)
        elif output_format == "dict":
            output_data = article.to_dict()
        else:
            raise AppError("E007")

        # 更新统计
        self.stats["processed"] += 1
        if confidence < 90:
            self.stats["warnings"] += 1

        # 构建结果
        warnings = []
        if confidence < 80:
            warnings.append("置信度过低，部分字段可能不准确")
        elif confidence < 90:
            warnings.append("部分字段置信度一般，建议复核")

        return ProcessResult(data=output_data, confidence=confidence, warnings=warnings)

    def _parse_input(self, raw_input: str) -> Any:
        """
        解析输入内容

        支持：
        - JSON 字符串
        - 纯文本（尝试提取关键信息）
        - URL（识别链接）
        """
        raw_input = raw_input.strip()

        # 尝试解析 JSON
        if raw_input.startswith("{") and raw_input.endswith("}"):
            try:
                return json.loads(raw_input)
            except json.JSONDecodeError:
                raise AppError("E003", "JSON格式错误")

        # URL 识别
        if raw_input.startswith(("http://", "https://")):
            return {"url": raw_input}

        # 纯文本，按行解析
        lines = [line.strip() for line in raw_input.split("\n") if line.strip()]
        if not lines:
            raise AppError("E001")

        # 尝试从文本中识别字段
        result = {}
        for line in lines:
            for field in self.KEY_FIELDS:
                if line.lower().startswith(f"{field}:"):
                    result[field] = line.split(":", 1)[1].strip()
                    break
            else:
                # 非字段行，作为内容
                if "content" in result:
                    result["content"] += "\n" + line
                else:
                    result["content"] = line

        return result

    def _extract_article_info(self, parsed_data: Any) -> ArticleInfo:
        """从解析后的数据中提取文章信息"""
        if isinstance(parsed_data, dict):
            article = ArticleInfo(
                title=str(parsed_data.get("title", "")),
                author=str(parsed_data.get("author", "")),
                content=str(parsed_data.get("content", "")),
                source=str(parsed_data.get("source", "")),
                url=str(parsed_data.get("url", "")),
                publish_time=str(parsed_data.get("publish_time", "")),
                extra={
                    k: v for k, v in parsed_data.items()
                    if k not in self.KEY_FIELDS and not isinstance(v, (dict, list))
                },
            )
        else:
            # 非字典输入，视为纯文本内容
            article = ArticleInfo(content=str(parsed_data))

        return article

    def _get_missing_fields(self, article: ArticleInfo) -> List[str]:
        """获取缺失的关键字段列表"""
        missing_fields = []
        if not article.title:
            missing_fields.append("标题(title)")
        if not article.content:
            missing_fields.append("内容(content)")
        return missing_fields

    def _check_required_fields(self, article: ArticleInfo) -> None:
        """检查关键字段完整性（向后兼容）"""
        missing_fields = self._get_missing_fields(article)
        if missing_fields:
            raise AppError("E002", "还缺少以下信息，请补充：" + ", ".join(missing_fields))

    def _calculate_confidence(self, article: ArticleInfo) -> float:
        """
        计算置信度（0-100）

        规则：
        - 基础分 60
        - 有标题 +15
        - 有内容 +15
        - 有作者 +5
        - 有来源 +5
        - 有 URL +5
        - 有发布时间 +5
        """
        confidence = 60

        if article.title:
            confidence += 15
        if article.content:
            confidence += 15
        if article.author:
            confidence += 5
        if article.source:
            confidence += 5
        if article.url:
            confidence += 5
        if article.publish_time:
            confidence += 5

        return min(confidence, 100)

    def batch_process(self, inputs: List[str], output_format: str = "json") -> List[ProcessResult]:
        """
        批量处理多个输入

        Args:
            inputs: 输入列表
            output_format: 输出格式

        Returns:
            List[ProcessResult]: 处理结果列表
        """
        results = []
        for i, raw_input in enumerate(inputs):
            try:
                result = self.process_input(raw_input, output_format)
                results.append(result)
            except AppError as e:
                self.stats["errors"].append({"index": i, "code": e.code, "message": e.message})
                # 单个失败不中断整体
                results.append(ProcessResult(data=None, confidence=0, warnings=[f"处理失败: {e.message}"]))
            except Exception as e:
                self.stats["errors"].append({"index": i, "code": "E006", "message": str(e)})
                results.append(ProcessResult(data=None, confidence=0, warnings=["内部处理错误"]))

        return results


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑

    使用内置硬编码样例数据，不读取外部文件、不访问网络。
    所有断言使用宽松阈值（大小比较/区间判断），确保稳健。
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    all_passed = True

    # 测试用例 1: 完整 JSON 输入
    print("\n[测试 1] 完整 JSON 输入")
    try:
        processor = ArticleProcessor()
        json_input = json.dumps({
            "title": "测试文章标题",
            "author": "测试作者",
            "content": "这是测试内容，包含足够长的文本用于验证处理逻辑。",
            "source": "测试公众号",
            "url": "https://example.com/article/12345",
            "publish_time": "2025-01-01",
        })
        result = processor.process_input(json_input, "dict")
        assert result is not None, "结果不应为空"
        assert result.confidence > 0, "置信度应大于0"
        assert result.confidence >= 90, f"完整输入置信度应≥90，实际: {result.confidence}"
        assert result.data is not None, "数据不应为空"
        assert isinstance(result.data, dict), "数据应为字典类型"
        assert result.data.get("title") == "测试文章标题", "标题提取错误"
        assert result.data.get("author") == "测试作者", "作者提取错误"
        assert len(result.data.get("content", "")) > 10, "内容长度应大于10"
        print(f"  ✓ 通过 (置信度: {result.confidence})")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    except AppError as e:
        all_passed = False
        print(f"  ✗ 失败: {e.code} {e.message}")

    # 测试用例 2: 纯文本输入
    print("\n[测试 2] 纯文本输入")
    try:
        processor = ArticleProcessor()
        text_input = """title: 文本标题
author: 文本作者
content: 这是从纯文本中提取的内容，包含足够的信息用于测试。
"""
        result = processor.process_input(text_input, "dict")
        assert result is not None, "结果不应为空"
        assert result.confidence > 0, "置信度应大于0"
        assert result.confidence >= 80, f"文本输入置信度应≥80，实际: {result.confidence}"
        assert result.data.get("title") == "文本标题", "标题提取错误"
        assert result.data.get("author") == "文本作者", "作者提取错误"
        print(f"  ✓ 通过 (置信度: {result.confidence})")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    except AppError as e:
        all_passed = False
        print(f"  ✗ 失败: {e.code} {e.message}")

    # 测试用例 3: URL 输入
    print("\n[测试 3] URL 输入")
    try:
        processor = ArticleProcessor()
        url_input = "https://mp.weixin.qq.com/s/test_article_123"
        try:
            processor.process_input(url_input, "dict")
            all_passed = False
            print("  ✗ 失败: URL输入应抛出 E002 错误（缺少标题和内容）")
        except AppError as e:
            assert e.code == "E002", f"错误码应为E002，实际: {e.code}"
            assert "标题(title)" in e.message, "错误信息应包含标题"
            assert "内容(content)" in e.message, "错误信息应包含内容"
            print(f"  ✓ 通过 (错误码: {e.code}, 提示: {e.message})")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试用例 4: 空输入错误处理
    print("\n[测试 4] 空输入错误处理")
    try:
        processor = ArticleProcessor()
        processor.process_input("", "dict")
        all_passed = False
        print("  ✗ 失败: 应抛出 E001 错误")
    except AppError as e:
        assert e.code == "E001", f"错误码应为E001，实际: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")

    # 测试用例 5: 缺失关键字段错误处理
    print("\n[测试 5] 缺失关键字段错误处理")
    try:
        processor = ArticleProcessor()
        processor.process_input('{"author": "无标题作者"}', "dict")
        all_passed = False
        print("  ✗ 失败: 应抛出 E002 错误")
    except AppError as e:
        assert e.code == "E002", f"错误码应为E002，实际: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")

    # 测试用例 6: 批量处理
    print("\n[测试 6] 批量处理")
    try:
        processor = ArticleProcessor()
        batch_inputs = [
            '{"title": "批量1", "content": "内容1的内容部分"}',
            '{"title": "批量2", "content": "内容2的内容部分"}',
            "invalid json {",
        ]
        results = processor.batch_process(batch_inputs, "dict")
        assert len(results) == 3, f"应返回3个结果，实际: {len(results)}"
        assert results[0].confidence > 0, "第一个结果置信度应大于0"
        assert results[1].confidence > 0, "第二个结果置信度应大于0"
        assert results[2].confidence == 0, "第三个结果置信度应为0（失败）"
        assert len(processor.stats["errors"]) >= 1, "应记录至少1个错误"
        print(f"  ✓ 通过 (处理: {len(results)}, 错误: {len(processor.stats['errors'])})")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试用例 7: 置信度阈值逻辑
    print("\n[测试 7] 置信度阈值逻辑")
    try:
        processor = ArticleProcessor()
        # 完整信息 - 高置信度
        full_result = processor.process_input(
            json.dumps({
                "title": "完整标题",
                "content": "完整内容部分，足够长以通过验证。",
                "author": "作者",
                "source": "来源",
                "url": "https://example.com",
                "publish_time": "2025-01-01",
            }),
            "dict"
        )
        assert full_result.confidence >= 90, f"完整信息置信度应≥90，实际: {full_result.confidence}"
        assert full_result._get_confidence_level() == "直接输出", "置信度等级应为直接输出"

        # 部分信息 - 中等置信度
        partial_result = processor.process_input(
            json.dumps({"title": "只有标题", "content": "只有内容"}),
            "dict"
        )
        assert 80 <= partial_result.confidence < 90, f"部分信息置信度应在80-90之间，实际: {partial_result.confidence}"
        assert partial_result._get_confidence_level() == "建议复核", "置信度等级应标注为建议复核"

        # 低置信度 - 只有标题
        low_result = processor.process_input(
            json.dumps({"title": "只有标题", "content": "短"}),
            "dict"
        )
        assert low_result.confidence < 80, f"低置信度应<80，实际: {low_result.confidence}"
        assert low_result._get_confidence_level() == "[需核实]", "置信度等级应为需核实"

        print(f"  ✓ 通过 (完整: {full_result.confidence}, 部分: {partial_result.confidence}, 低: {low_result.confidence})")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    except AppError as e:
        all_passed = False
        print(f"  ✗ 失败: {e.code} {e.message}")

    # 测试用例 8: 输出格式
    print("\n[测试 8] 输出格式")
    try:
        processor = ArticleProcessor()
        json_output = processor.process_input(
            '{"title": "格式测试", "content": "内容"}',
            "json"
        )
        assert isinstance(json_output.data, str), "JSON输出应为字符串"
        parsed = json.loads(json_output.data)
        assert parsed.get("title") == "格式测试", "JSON解析后标题错误"

        dict_output = processor.process_input(
            '{"title": "格式测试", "content": "内容"}',
            "dict"
        )
        assert isinstance(dict_output.data, dict), "字典输出应为字典类型"
        print("  ✓ 通过 (JSON和字典格式均正常)")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    except AppError as e:
        all_passed = False
        print(f"  ✗ 失败: {e.code} {e.message}")

    # 测试用例 9: 错误码完整性
    print("\n[测试 9] 错误码完整性")
    try:
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert ERROR_CODES[code], f"错误码 {code} 描述为空"
        print(f"  ✓ 通过 (共 {len(ERROR_CODES)} 个错误码)")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")

    # 测试用例 10: 统计信息
    print("\n[测试 10] 统计信息")
    try:
        processor = ArticleProcessor()
        processor.process_input('{"title": "统计1", "content": "内容"}', "dict")
        processor.process_input('{"title": "统计2", "content": "内容"}', "dict")
        assert processor.stats["processed"] == 2, f"应处理2条，实际: {processor.stats['processed']}"
        assert processor.stats["warnings"] >= 0, "警告数应≥0"
        print(f"  ✓ 通过 (processed: {processor.stats['processed']})")
    except AssertionError as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    except AppError as e:
        all_passed = False
        print(f"  ✗ 失败: {e.code} {e.message}")

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="公众号文章处理工具 - 本地优先的微信内容情报库",
        epilog="示例: python main.py --input '{\"title\": \"标题\", \"content\": \"内容\"}' --format json"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（JSON/文本/URL）"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "dict"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理，多个输入用 | 分隔"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )

    args = parser.parse_args()

    # 版本信息
    if args.version:
        print("moore-wechat-article-downloader v1.0.0")
        print("本地优先的微信内容情报库")
        return 0

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理模式
    try:
        processor = ArticleProcessor()

        # 批量处理
        if args.batch:
            inputs = [item.strip() for item in args.batch.split("|") if item.strip()]
            if not inputs:
                raise AppError("E001")
            results = processor.batch_process(inputs, args.format)
            for i, result in enumerate(results):
                print(f"\n--- 结果 {i + 1} ---")
                if result.data is not None:
                    if isinstance(result.data, str):
                        print(result.data)
                    else:
                        print(json.dumps(result.data, ensure_ascii=False, indent=2))
                if result.warnings:
                    for warning in result.warnings:
                        print(f"警告: {warning}")
            return 0

        # 单个处理
        if args.input:
            result = processor.process_input(args.input, args.format)
            if isinstance(result.data, str):
                print(result.data)
            else:
                print(json.dumps(result.data, ensure_ascii=False, indent=2))
            if result.warnings:
                for warning in result.warnings:
                    print(f"警告: {warning}")
            return 0

        # 无输入，显示帮助
        parser.print_help()
        return 0

    except AppError as e:
        print(f"错误: {e.code} - {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E006 - 内部处理错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
