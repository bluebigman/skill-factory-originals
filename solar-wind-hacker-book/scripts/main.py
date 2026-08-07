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
            "
