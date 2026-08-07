#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rack-mirror: 数据镜像/结构化转换/信息提取
========================================
将输入文本、文件或URL转换为结构化结果，保留关键信息并标注置信度。

仅依赖 Python 标准库，支持 --selftest 离线自检。
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
# E001: 参数错误
# E002: 文件不存在或不可读
# E003: URL 访问失败
# E004: 输入内容为空
# E005: 输出序列化失败
# E006: 不支持的输入类型
# E007: 自检断言失败
# E008: 正则表达式编译错误
# E009: 数据格式错误
# E010: 未知异常


# ---------------------------------------------------------------------------
# 核心提取器：负责从文本中抽取结构化字段
# ---------------------------------------------------------------------------
class FieldExtractor:
    """基于正则表达式的字段提取器，附带置信度评估。"""

    # 字段模式定义（名称 -> (正则, 置信度基准)）
    PATTERNS: Dict[str, Tuple[str, float]] = {
        "姓名": (r"(?:姓名|名字|称呼)[:：\s]*([\u4e00-\u9fa5]{2,4})", 0.90),
        "电话": (r"(?:电话|手机|联系方式|tel|phone)[:：\s]*(\+?\d[\d\- ]{6,14}\d)", 0.95),
        "邮箱": (r"(?:邮箱|电子邮件|email|e-mail)[:：\s]*([\w.+-]+@[\w-]+\.[\w.]+)", 0.95),
        "地址": (r"(?:地址|住址|location|address)[:：\s]*([\u4e00-\u9fa50-9A-Za-z\-号栋单元室楼层]+)", 0.85),
        "日期": (r"(?:日期|时间|date|time)[:：\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)", 0.90),
        "金额": (r"(?:金额|价格|价格|amount|price)[:：\s]*([¥￥]?\d+(?:\.\d{1,2})?(?:元|块|RMB)?)", 0.85),
        "编号": (r"(?:编号|单号|ID|No\.?)[:：\s]*([A-Za-z0-9\-]{4,20})", 0.80),
    }

    def __init__(self) -> None:
        """初始化并预编译所有正则表达式。"""
        self._compiled: Dict[str, Tuple[re.Pattern, float]] = {}
        for field, (pattern, confidence) in self.PATTERNS.items():
            try:
                self._compiled[field] = (re.compile(pattern, re.IGNORECASE), confidence)
            except re.error as exc:
                # 正则编译失败属于内部错误，直接抛出并携带错误码
                raise RuntimeError(f"E008: 正则表达式编译失败 - {pattern}: {exc}")

    def extract(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取所有已知字段。

        参数:
            text: 输入文本

        返回:
            包含字段值和置信度的字典，格式:
            {"字段名": "值", "_confidence": {"字段名": 0.95}}
        """
        if not text or not text.strip():
            return {"_confidence": {}, "_warning": "输入内容为空"}

        result: Dict[str, Any] = {}
        confidence_map: Dict[str, float] = {}

        for field, (pattern, base_conf) in self._compiled.items():
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                if value:
                    result[field] = value
                    # 置信度 = 基础置信度，若值长度较长可微调
                    conf = base_conf
                    if len(value) > 8:
                        conf = min(1.0, conf + 0.05)
                    confidence_map[field] = round(conf, 2)

        result["_confidence"] = confidence_map

        # 补充缺失字段占位
        for field in self.PATTERNS:
            if field not in result:
                result[field] = f"[需核实:{field}]"

        return result


# ---------------------------------------------------------------------------
# 输入处理器：支持文本、文件、URL
# ---------------------------------------------------------------------------
class InputHandler:
    """处理不同类型的输入来源，统一返回文本内容。"""

    @staticmethod
    def from_text(text: str) -> str:
        """直接使用传入的文本。"""
        if not text or not text.strip():
            raise ValueError("E004: 输入内容为空")
        return text.strip()

    @staticmethod
    def from_file(path: str) -> str:
        """从纯文本文件中读取内容。"""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"E002: 文件不存在 - {path}")
        if not file_path.is_file():
            raise IsADirectoryError(f"E002: 路径不是文件 - {path}")
        try:
            return file_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError as exc:
            raise OSError(f"E002: 文件读取失败 - {exc}") from exc

    @staticmethod
    def from_url(url: str) -> str:
        """从公开URL获取文本内容。"""
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                # 仅处理文本类型响应
                content_type = response.headers.get("Content-Type", "")
                if "text" not in content_type and "html" not in content_type:
                    raise ValueError(f"E003: 非文本内容类型 - {content_type}")
                data = response.read()
                # 尝试常见编码
                for encoding in ("utf-8", "gbk", "latin-1"):
                    try:
                        return data.decode(encoding).strip()
                    except UnicodeDecodeError:
                        continue
                return data.decode("utf-8", errors="replace").strip()
        except Exception as exc:
            raise ConnectionError(f"E003: URL访问失败 - {url}: {exc}") from exc


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def process_batch(text: str, extractor: FieldExtractor) -> List[Dict[str, Any]]:
    """
    将多行文本按行拆分，逐行结构化提取。

    参数:
        text: 多行文本
        extractor: 字段提取器实例

    返回:
        每行提取结果的列表
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    results = []
    for line in lines:
        # 跳过可能的标题行
        if re.match(r"^(序号|姓名|电话|邮箱|字段|#|//)", line, re.IGNORECASE):
            continue
        extracted = extractor.extract(line)
        extracted["_source_line"] = line
        results.append(extracted)

    return results


# ---------------------------------------------------------------------------
# 主处理函数：统一入口
# ---------------------------------------------------------------------------
def process_input(
    text: Optional[str] = None,
    file_path: Optional[str] = None,
    url: Optional[str] = None,
    batch: bool = False,
) -> Dict[str, Any]:
    """
    处理输入并返回结构化结果。

    参数:
        text: 直接文本输入
        file_path: 文件路径
        url: URL地址
        batch: 是否按行批量处理

    返回:
        结构化结果字典
    """
    extractor = FieldExtractor()

    # 获取输入内容
    try:
        if text is not None:
            content = InputHandler.from_text(text)
        elif file_path is not None:
            content = InputHandler.from_file(file_path)
        elif url is not None:
            content = InputHandler.from_url(url)
        else:
            raise ValueError("E001: 必须提供text、file或url之一")
    except (ValueError, FileNotFoundError, IsADirectoryError, OSError, ConnectionError) as exc:
        return {"error": str(exc), "status": "failed"}

    # 执行提取
    try:
        if batch:
            results = process_batch(content, extractor)
            return {"status": "success", "count": len(results), "results": results}
        else:
            result = extractor.extract(content)
            return {"status": "success", "data": result}
    except Exception as exc:
        return {"error": f"E010: 处理失败 - {exc}", "status": "failed"}


# ---------------------------------------------------------------------------
# 自检模块：硬编码样例数据，离线验证核心逻辑
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    运行内置自检用例，验证核心提取逻辑。

    返回:
        True 表示所有断言通过，否则抛出异常
    """
    print("[selftest] 开始运行 rack-mirror 自检...")

    # 创建提取器实例
    extractor = FieldExtractor()

    # 测试用例1：标准文本提取
    sample1 = "张三，电话13800138000，邮箱zhang@example.com"
    result1 = extractor.extract(sample1)

    # 宽松断言：字段存在且格式合理
    assert result1["姓名"] == "张三", "E007: 姓名提取失败"
    assert result1["电话"] != "[需核实:电话]", "E007: 电话提取失败"
    assert result1["邮箱"] != "[需核实:邮箱]", "E007: 邮箱提取失败"
    assert "138" in result1["电话"], "E007: 电话格式异常"
    assert "@" in result1["邮箱"], "E007: 邮箱格式异常"
    # 置信度在合理区间
    conf1 = result1["_confidence"]
    assert all(0.0 <= v <= 1.0 for v in conf1.values()), "E007: 置信度超出范围"
    assert conf1.get("电话", 0) > 0.8, "E007: 电话置信度偏低"

    # 测试用例2：缺失字段占位
    sample2 = "仅有一个日期：2024年5月20日"
    result2 = extractor.extract(sample2)
    assert result2["日期"] != "[需核实:日期]", "E007: 日期提取失败"
    assert "2024" in result2["日期"], "E007: 日期年份错误"
    assert result2["姓名"] == "[需核实:姓名]", "E007: 缺失字段占位失败"

    # 测试用例3：批量处理
    sample3 = "张三,13800138000,zhang@example.com\n李四,13900139000,li@example.com"
    batch_results = process_batch(sample3, extractor)
    assert len(batch_results) == 2, "E007: 批量处理行数错误"
    assert batch_results[0]["姓名"] == "张三", "E007: 批量第一行姓名错误"
    assert batch_results[1]["姓名"] == "李四", "E007: 批量第二行姓名错误"

    # 测试用例4：完整流程（process_input）
    full_result = process_input(text=sample1)
    assert full_result["status"] == "success", "E007: 完整流程失败"
    assert full_result["data"]["姓名"] == "张三", "E007: 完整流程姓名错误"

    # 测试用例5：空输入处理（不应崩溃，返回错误信息）
    try:
        process_input(text="   ")
        # 如果走到这里说明没有抛出异常，但应返回错误
        empty_check = process_input(text="   ")
        assert empty_check["status"] == "failed", "E007: 空输入未返回失败状态"
    except Exception:
        # 抛出异常也视为失败
        raise AssertionError("E007: 空输入处理异常")

    # 测试用例6：文件不存在
    try:
        process_input(file_path="/nonexistent/path/file.txt")
        raise AssertionError("E007: 不存在的文件应返回失败")
    except Exception as exc:
        # 应返回错误字典而不是抛出
        assert "E002" in str(exc) or "failed" in str(exc), "E007: 文件错误处理异常"

    print("[selftest] 所有自检断言通过 ✅")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="rack-mirror - 数据镜像/结构化转换/信息提取",
        epilog="示例: python main.py --text '张三,电话13800138000' --batch",
    )
    parser.add_argument("--text", type=str, help="直接输入文本")
    parser.add_argument("--file", type=str, help="输入文件路径")
    parser.add_argument("--url", type=str, help="输入URL地址")
    parser.add_argument("--batch", action="store_true", help="按行批量处理")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--output", type=str, help="输出结果到文件(JSON)")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as exc:
            print(f"[selftest] 失败: {exc}", file=sys.stderr)
            return 1

    # 参数校验
    if not args.text and not args.file and not args.url:
        parser.error("E001: 必须提供 --text、--file 或 --url 之一")

    # 处理输入
    result = process_input(
        text=args.text,
        file_path=args.file,
        url=args.url,
        batch=args.batch,
    )

    # 输出结果
    try:
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        print(f"E005: 输出序列化失败 - {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            Path(args.output).write_text(output_json, encoding="utf-8")
            print(f"结果已写入: {args.output}")
        except OSError as exc:
            print(f"E002: 输出文件写入失败 - {exc}", file=sys.stderr)
            return 1
    else:
        print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
