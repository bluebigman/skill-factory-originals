#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
技能: solar-wind-hacker-book (代码审查)

本脚本依据《solar-wind-hacker-book 功能规格》独立实现。
仅依赖 Python 标准库，无第三方依赖。

功能：
1. 将用户提供的数据/文件/URL 解析为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出（JSON）
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式
6. 提供 --selftest 离线自检（内置硬编码样例，不读外部文件/不访问网络）

用法示例：
    python scripts/main.py --input "用户提供的数据内容"
    python scripts/main.py --file path/to/file.txt
    python scripts/main.py --url https://example.com/data
    python scripts/main.py --batch --input "item1" --input "item2"
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义（依据规格第五节）
# ---------------------------------------------------------------------------
ERR_INPUT_EMPTY = "E001"        # 输入为空
ERR_KEY_MISSING = "E002"        # 关键信息缺失
ERR_FORMAT = "E003"             # 输入格式错误
ERR_OUT_OF_SCOPE = "E004"       # 超出能力边界
ERR_LOW_CONFIDENCE = "E005"     # 置信度过低
ERR_FILE_READ = "E006"          # 文件读取失败
ERR_URL_FETCH = "E007"          # URL 获取失败（本实现不访问网络，直接报错）
ERR_BATCH_EMPTY = "E008"        # 批量输入为空
ERR_OUTPUT_WRITE = "E009"       # 输出写入失败
ERR_INTERNAL = "E010"           # 内部未知错误

# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------
CONFIDENCE_HIGH = 0.90          # 置信度 >= 90%：直接输出
CONFIDENCE_MEDIUM = 0.85        # 85%-90%：标注"建议复核"
CONFIDENCE_THRESHOLD_LOW = 0.85 # < 85%：标注"[需核实]"

# 关键信息字段（依据规格 Step 2）
KEY_FIELDS = ["source", "content", "format", "timestamp"]

# 支持的输入类型标识
INPUT_TYPE_TEXT = "text"
INPUT_TYPE_FILE = "file"
INPUT_TYPE_URL = "url"


# ---------------------------------------------------------------------------
# 核心处理类
# ---------------------------------------------------------------------------
class CodeReviewProcessor:
    """代码审查技能核心处理器。

    依据功能规格实现：
    - Step 1: 收集最小信息集
    - Step 2: 执行核心流程
    - Step 3: 输出与校验
    """

    def __init__(self) -> None:
        # 内部状态
        self._batch_mode = False
        self._custom_format: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # 对外主入口
    # ------------------------------------------------------------------
    def process(
        self,
        input_data: Optional[str] = None,
        input_type: str = INPUT_TYPE_TEXT,
        batch: bool = False,
        output_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """处理用户输入，返回结构化结果。

        参数:
            input_data: 用户提供的数据内容（text 类型时必填）
            input_type: 输入类型（text/file/url）
            batch: 是否批量处理（批量时 input_data 为逗号分隔的多个条目）
            output_format: 自定义输出格式（JSON 字符串，可选）

        返回:
            符合规格的结构化结果字典。

        异常:
            根据错误场景抛出 RuntimeError，错误码见模块常量。
        """
        try:
            # ---- Step 1: 收集最小信息集 ----
            if batch:
                return self._process_batch(input_data, output_format)

            return self._process_single(input_data, input_type, output_format)

        except RuntimeError:
            # 已知业务错误，原样上抛（携带错误码）
            raise
        except Exception as exc:  # 兜底未知错误
            raise RuntimeError(f"{ERR_INTERNAL}: 内部错误: {exc}") from exc

    # ------------------------------------------------------------------
    # 单条处理
    # ------------------------------------------------------------------
    def _process_single(
        self,
        input_data: Optional[str],
        input_type: str,
        output_format: Optional[str],
    ) -> Dict[str, Any]:
        """处理单条输入。"""
        # 检查输入为空
        if not input_data or not input_data.strip():
            raise RuntimeError(f"{ERR_INPUT_EMPTY}: 请提供待处理的内容，格式为：用户提供的数据/文件/URL")

        # 根据输入类型读取内容
        content, source_desc = self._acquire_content(input_data, input_type)

        # 解析关键信息
        parsed = self._parse_content(content)

        # 生成结构化结果
        result = self._build_result(parsed, source_desc, input_type)

        # 应用自定义输出格式（如果提供）
        if output_format:
            result = self._apply_custom_format(result, output_format)

        return result

    # ------------------------------------------------------------------
    # 批量处理
    # ------------------------------------------------------------------
    def _process_batch(
        self,
        input_data: Optional[str],
        output_format: Optional[str],
    ) -> Dict[str, Any]:
        """批量处理多个输入（逗号分隔）。"""
        if not input_data or not input_data.strip():
            raise RuntimeError(f"{ERR_BATCH_EMPTY}: 批量输入为空，请提供至少一个待处理条目")

        # 分割批量条目（支持逗号或分号分隔）
        items = [item.strip() for item in input_data.replace(";", ",").split(",") if item.strip()]

        if not items:
            raise RuntimeError(f"{ERR_BATCH_EMPTY}: 批量输入为空，请提供至少一个待处理条目")

        results = []
        for idx, item in enumerate(items, start=1):
            try:
                single_result = self._process_single(item, INPUT_TYPE_TEXT, None)
                single_result["batch_index"] = idx
                results.append(single_result)
            except RuntimeError as exc:
                # 批量模式下单条失败不中断，记录错误
                results.append({
                    "batch_index": idx,
                    "error": str(exc),
                    "status": "failed",
                })

        batch_result = {
            "status": "success",
            "batch_count": len(results),
            "success_count": sum(1 for r in results if r.get("status") != "failed"),
            "failed_count": sum(1 for r in results if r.get("status") == "failed"),
            "results": results,
        }

        if output_format:
            batch_result = self._apply_custom_format(batch_result, output_format)

        return batch_result

    # ------------------------------------------------------------------
    # 内容获取
    # ------------------------------------------------------------------
    def _acquire_content(self, input_data: str, input_type: str) -> Tuple[str, str]:
        """根据输入类型获取内容。

        返回:
            (内容字符串, 来源描述字符串)

        注意:
            依据规格"不做：不访问网络或外部服务"，URL 类型直接返回错误。
            文件类型仅读取本地文件。
        """
        if input_type == INPUT_TYPE_TEXT:
            return input_data.strip(), "用户直接提供"

        if input_type == INPUT_TYPE_FILE:
            return self._read_file(input_data)

        if input_type == INPUT_TYPE_URL:
            # 规格明确不访问网络
            raise RuntimeError(
                f"{ERR_OUT_OF_SCOPE}: 本工具不访问网络或外部服务，无法处理 URL。"
                f"建议：请将 URL 内容复制后以文本方式提供。"
            )

        raise RuntimeError(f"{ERR_FORMAT}: 不支持的输入类型: {input_type}，仅支持 text/file/url")

    def _read_file(self, file_path: str) -> Tuple[str, str]:
        """读取本地文件内容。"""
        try:
            path = Path(file_path).expanduser().resolve()
            if not path.exists():
                raise RuntimeError(f"{ERR_FILE_READ}: 文件不存在: {file_path}")
            if not path.is_file():
                raise RuntimeError(f"{ERR_FILE_READ}: 路径不是文件: {file_path}")

            content = path.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                raise RuntimeError(f"{ERR_INPUT_EMPTY}: 文件内容为空: {file_path}")

            return content.strip(), f"文件: {path.name}"
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"{ERR_FILE_READ}: 读取文件失败: {exc}") from exc

    # ------------------------------------------------------------------
    # 内容解析（核心逻辑）
    # ------------------------------------------------------------------
    def _parse_content(self, content: str) -> Dict[str, Any]:
        """解析输入内容，识别关键信息。

        依据规格：
        - 识别输入中的关键字段并结构化
        - 对不确定项标注并请求确认

        实现说明：
        本实现采用轻量级启发式解析，不依赖外部 NLP 库。
        识别以下信息：
        - 内容长度、行数、单词数
        - 是否包含代码特征（大括号、关键字等）
        - 是否包含 URL
        - 是否包含数字/日期
        - 内容摘要（前 200 字符）
        """
        if not content:
            raise RuntimeError(f"{ERR_INPUT_EMPTY}: 输入内容为空")

        lines = content.splitlines()
        word_count = len(content.split())
        char_count = len(content)

        # 识别内容特征
        has_code = self._detect_code(content)
        has_url = "http://" in content or "https://" in content or "www." in content
        has_number = any(ch.isdigit() for ch in content)
        has_date = self._detect_date(content)

        # 生成摘要
        summary = content[:200] + ("..." if len(content) > 200 else "")

        # 计算置信度（启发式）
        confidence = self._calculate_confidence(content, has_code, has_url)

        # 组装解析结果
        parsed = {
            "content_length": char_count,
            "line_count": len(lines),
            "word_count": word_count,
            "has_code": has_code,
            "has_url": has_url,
            "has_number": has_number,
            "has_date": has_date,
            "summary": summary,
            "confidence": confidence,
            "confidence_label": self._confidence_label(confidence),
        }

        # 缺失关键信息检查（依据规格 Step 1）
        missing = self._check_missing_fields(parsed)
        if missing:
            parsed["missing_fields"] = missing
            # 关键信息缺失但仍有内容可处理，不报错，仅标注

        return parsed

    def _detect_code(self, content: str) -> bool:
        """检测内容是否包含代码特征。"""
        code_keywords = [
            "def ", "class ", "import ", "return ", "if ", "else:",
            "for ", "while ", "function", "var ", "const ", "let ",
            "<html", "<div", "SELECT ", "INSERT ", "CREATE ",
        ]
        # 检查常见代码关键字
        for keyword in code_keywords:
            if keyword in content:
                return True
        # 检查大括号或分号等代码特征
        if "{" in content or "}" in content or ";" in content:
            return True
        return False

    def _detect_date(self, content: str) -> bool:
        """检测内容是否包含日期特征。"""
        import re
        # 匹配常见日期格式：2024-01-01, 2024/01/01, 01/01/2024, Jan 1, 2024
        date_patterns = [
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
            r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
        ]
        for pattern in date_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _calculate_confidence(self, content: str, has_code: bool, has_url: bool) -> float:
        """计算置信度（启发式评分）。"""
        confidence = 0.80  # 基础置信度

        # 内容长度增加置信度
        if len(content) >= 100:
            confidence += 0.05
        if len(content) >= 500:
            confidence += 0.03

        # 代码特征增加置信度（说明是结构化内容）
        if has_code:
            confidence += 0.05

        # URL 存在降低置信度（可能需要人工确认）
        if has_url:
            confidence -= 0.02

        # 有数字和日期增加置信度
        if any(ch.isdigit() for ch in content):
            confidence += 0.02

        # 限制在 0.5-0.98 之间
        return max(0.5, min(0.98, confidence))

    def _confidence_label(self, confidence: float) -> str:
        """根据置信度生成标签。"""
        if confidence >= CONFIDENCE_HIGH:
            return "高置信度"
        elif confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"

    def _check_missing_fields(self, parsed: Dict[str, Any]) -> List[str]:
        """检查关键信息缺失情况。"""
        missing = []
        if not parsed.get("has_code") and not parsed.get("has_url"):
            missing.append("未检测到明确的代码或URL特征")
        if parsed.get("word_count", 0) < 3:
            missing.append("内容过短，可能信息不足")
        return missing

    # ------------------------------------------------------------------
    # 结果构建
    # ------------------------------------------------------------------
    def _build_result(
        self,
        parsed: Dict[str, Any],
        source_desc: str,
        input_type: str,
    ) -> Dict[str, Any]:
        """构建最终结构化结果。"""
        import datetime

        result = {
            "status": "success",
            "source": source_desc,
            "input_type": input_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "content": parsed,
            "format": "json",
        }

        # 添加置信度信息
        result["confidence"] = parsed["confidence"]
        result["confidence_label"] = parsed["confidence_label"]

        # 如果有关键信息缺失，添加提示
        if parsed.get("missing_fields"):
            result["warnings"] = parsed["missing_fields"]

        return result

    # ------------------------------------------------------------------
    # 自定义格式处理
    # ------------------------------------------------------------------
    def _apply_custom_format(
        self,
        result: Dict[str, Any],
        format_spec: str,
    ) -> Dict[str, Any]:
        """应用自定义输出格式。

        格式说明（JSON 字符串）：
        - {"fields": ["source", "content"], "style": "compact"}
        - {"fields": ["*"], "style": "detailed"}
        """
        try:
            spec = json.loads(format_spec)
            if not isinstance(spec, dict):
                raise ValueError("格式必须是 JSON 对象")

            fields = spec.get("fields", ["*"])
            style = spec.get("style", "detailed")

            if fields == ["*"]:
                fields = list(result.keys())

            filtered = {k: result.get(k) for k in fields if k in result}

            if style == "compact":
                # 紧凑格式：去除空值
                filtered = {k: v for k, v in filtered.items() if v is not None}

            return filtered
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{ERR_FORMAT}: 自定义格式 JSON 解析失败: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"{ERR_FORMAT}: 自定义格式处理失败: {exc}") from exc


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """运行离线自检，验证核心功能正常。

    返回:
        0 表示全部通过，非 0 表示有失败项。
    """
    print("=" * 60)
    print("solar-wind-hacker-book 技能自检")
    print("=" * 60)

    processor = CodeReviewProcessor()
    failures = 0

    # ---- 测试 1: 正常文本处理 ----
    print("\n[测试 1] 正常文本处理")
    try:
        result = processor.process(
            input_data="这是一个测试文本，包含一些内容用于验证功能。",
            input_type="text",
        )
        assert result["status"] == "success", "状态应为 success"
        assert "content" in result, "结果应包含 content 字段"
        assert result["confidence"] > 0, "置信度应大于 0"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 2: 代码内容识别 ----
    print("\n[测试 2] 代码内容识别")
    try:
        code_sample = """
def hello_world():
    print("Hello, World!")
    return 42
"""
        result = processor.process(input_data=code_sample, input_type="text")
        assert result["content"]["has_code"] is True, "应识别出代码特征"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 3: 空输入错误处理 ----
    print("\n[测试 3] 空输入错误处理")
    try:
        processor.process(input_data="", input_type="text")
        failures += 1
        print("  ✗ 失败: 空输入未抛出异常")
    except RuntimeError as exc:
        assert str(exc).startswith("E001"), "错误码应为 E001"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 4: URL 类型拒绝 ----
    print("\n[测试 4] URL 类型拒绝")
    try:
        processor.process(input_data="https://example.com", input_type="url")
        failures += 1
        print("  ✗ 失败: URL 未抛出异常")
    except RuntimeError as exc:
        assert str(exc).startswith("E004"), "错误码应为 E004"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 5: 批量处理 ----
    print("\n[测试 5] 批量处理")
    try:
        result = processor.process(
            input_data="第一条内容,第二条内容,第三条内容",
            batch=True,
        )
        assert result["batch_count"] == 3, "应有 3 条结果"
        assert result["success_count"] == 3, "应全部成功"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 6: 文件读取 ----
    print("\n[测试 6] 文件读取")
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".txt") as f:
            f.write("这是文件内容测试。")
            tmp_path = f.name
        try:
            result = processor.process(input_data=tmp_path, input_type="file")
            assert result["status"] == "success", "文件读取应成功"
            assert "文件" in result["source"], "来源描述应包含文件信息"
            print("  ✓ 通过")
        finally:
            os.unlink(tmp_path)
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 7: 自定义格式 ----
    print("\n[测试 7] 自定义格式")
    try:
        result = processor.process(
            input_data="自定义格式测试内容",
            input_type="text",
            output_format='{"fields": ["status", "source"], "style": "compact"}',
        )
        assert "status" in result, "应包含 status 字段"
        assert "source" in result, "应包含 source 字段"
        assert "content" not in result, "不应包含 content 字段"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 8: 日期识别 ----
    print("\n[测试 8] 日期识别")
    try:
        result = processor.process(
            input_data="会议定于 2024-03-15 举行，请准时参加。",
            input_type="text",
        )
        assert result["content"]["has_date"] is True, "应识别出日期"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 9: 低置信度标注 ----
    print("\n[测试 9] 低置信度标注")
    try:
        result = processor.process(input_data="短", input_type="text")
        assert result["confidence_label"] == "[需核实]", "短内容应标记为需核实"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 测试 10: 批量空输入 ----
    print("\n[测试 10] 批量空输入")
    try:
        processor.process(input_data="", batch=True)
        failures += 1
        print("  ✗ 失败: 空批量输入未抛出异常")
    except RuntimeError as exc:
        assert str(exc).startswith("E008"), "错误码应为 E008"
        print("  ✓ 通过")
    except Exception as exc:
        failures += 1
        print(f"  ✗ 失败: {exc}")

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    if failures == 0:
        print("自检结果: 全部通过 ✓")
        return 0
    else:
        print(f"自检结果: {failures} 项失败 ✗")
        return 1


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="solar-wind-hacker-book 技能 - 代码审查与信息提取",
        epilog="示例: python main.py --input '待处理内容'",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本）",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径",
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="输入 URL（本工具不支持网络访问，会直接报错）",
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量模式（输入用逗号或分号分隔）",
    )
    parser.add_argument(
        "--format",
        type=str,
        help='自定义输出格式 JSON，如: {"fields": ["source"], "style": "compact"}',
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（默认输出到 stdout）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入参数
    if not args.input and not args.file and not args.url:
        parser.error("请提供输入：--input、--file 或 --url（或使用 --selftest 运行自检）")

    # 确定输入类型和数据
    input_type = "text"
    input_data = args.input
    if args.file:
        input_type = "file"
        input_data = args.file
    elif args.url:
        input_type = "url"
        input_data = args.url

    # 处理
    try:
        processor = CodeReviewProcessor()
        result = processor.process(
            input_data=input_data,
            input_type=input_type,
            batch=args.batch,
            output_format=args.format,
        )

        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"结果已写入: {args.output}")
            except Exception as exc:
                print(f"错误: 写入文件失败 - {exc}", file=sys.stderr)
                return 1
        else:
            print(output_json)

        return 0

    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
