#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opencrow 爬虫采集 - 独立实现脚本

功能概述：
    根据用户提供的数据/文件/URL，识别关键信息并结构化输出。
    支持批量处理、自定义格式、置信度标注。

仅依据功能规格独立实现（clean-room），不包含任何第三方代码。
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
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "批量处理中断，请检查输入",
    "E008": "输出格式不支持",
    "E009": "字段映射失败",
    "E010": "未知错误",
}


def make_error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误响应"""
    return {
        "ok": False,
        "error_code": code,
        "error_message": ERROR_CODES.get(code, ERROR_CODES["E010"]),
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class OpenCrowProcessor:
    """爬虫采集核心处理器"""

    # 关键字段识别正则（宽松匹配）
    FIELD_PATTERNS = {
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "phone": r"1[3-9]\d{9}|0\d{2,3}-?\d{7,8}",
        "url": r"https?://[^\s]+",
        "id_card": r"\d{17}[\dXx]",
        "ip": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
    }

    def __init__(self) -> None:
        self.results: List[Dict[str, Any]] = []

    def parse_input(self, raw_input: str) -> Tuple[bool, Dict[str, Any]]:
        """解析输入内容，识别关键信息"""
        if not raw_input or not raw_input.strip():
            return False, make_error("E001")

        # 尝试解析 JSON
        try:
            data = json.loads(raw_input)
            if isinstance(data, dict):
                return True, {"type": "dict", "data": data}
            if isinstance(data, list):
                return True, {"type": "list", "data": data}
        except json.JSONDecodeError:
            pass

        # 尝试解析 URL
        if re.match(r"^https?://", raw_input.strip()):
            return True, {"type": "url", "data": raw_input.strip()}

        # 尝试解析文件路径（宽松判断）
        if re.match(r"^[\w\-. /\\]+\.\w+$", raw_input.strip()):
            return True, {"type": "file", "data": raw_input.strip()}

        # 默认按文本处理
        return True, {"type": "text", "data": raw_input.strip()}

    def extract_fields(self, text: str) -> Dict[str, List[str]]:
        """从文本中提取关键字段"""
        extracted: Dict[str, List[str]] = {}
        for field, pattern in self.FIELD_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                extracted[field] = list(set(matches))  # 去重
        return extracted

    def compute_confidence(self, extracted: Dict[str, List[str]], input_type: str) -> float:
        """计算置信度（宽松区间判断）"""
        if not extracted:
            return 0.0
        # 基础置信度：根据提取到的字段数量
        base = min(len(extracted) * 20, 80)
        # 不同类型输入的基础加成
        type_bonus = {"dict": 10, "list": 5, "url": 5, "file": 5, "text": 0}
        bonus = type_bonus.get(input_type, 0)
        return min(base + bonus, 100)

    def process_single(self, raw_input: str) -> Dict[str, Any]:
        """处理单条输入"""
        ok, parsed = self.parse_input(raw_input)
        if not ok:
            return parsed

        input_type = parsed["type"]
        data = parsed["data"]

        # 提取关键信息
        if input_type == "dict":
            # 字典类型：直接结构化
            extracted = {}
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    extracted[key] = [str(value)]
                elif isinstance(value, list):
                    extracted[key] = [str(v) for v in value]
                elif isinstance(value, dict):
                    extracted[key] = [json.dumps(value, ensure_ascii=False)]
            text_repr = json.dumps(data, ensure_ascii=False)
        elif input_type == "list":
            # 列表类型：逐项提取
            extracted = {}
            text_repr = json.dumps(data, ensure_ascii=False)
            for item in data:
                if isinstance(item, str):
                    item_fields = self.extract_fields(item)
                    for k, v in item_fields.items():
                        if k in extracted:
                            extracted[k].extend(v)
                        else:
                            extracted[k] = list(v)
                elif isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, (str, int, float, bool)):
                            if k in extracted:
                                extracted[k].append(str(v))
                            else:
                                extracted[k] = [str(v)]
        else:
            # 文本/URL/文件：正则提取
            text_repr = str(data)
            extracted = self.extract_fields(text_repr)

        # 计算置信度
        confidence = self.compute_confidence(extracted, input_type)

        # 构造输出
        result = {
            "ok": True,
            "input_type": input_type,
            "source": text_repr[:200],  # 截断长文本
            "extracted": extracted,
            "confidence": confidence,
            "confidence_label": self._confidence_label(confidence),
        }

        # 置信度标注
        if confidence < 85:
            result["warning"] = "[需核实] 部分内容无法确定，请人工复核"
        elif confidence < 90:
            result["warning"] = "建议复核"

        return result

    def _confidence_label(self, confidence: float) -> str:
        """置信度标签"""
        if confidence >= 90:
            return "高"
        if confidence >= 85:
            return "中高"
        if confidence >= 70:
            return "中"
        return "低"

    def batch_process(self, inputs: List[str]) -> Dict[str, Any]:
        """批量处理多条输入"""
        if not inputs:
            return make_error("E001")

        results = []
        for i, item in enumerate(inputs):
            try:
                result = self.process_single(item)
                result["index"] = i + 1
                results.append(result)
            except Exception as e:
                results.append({
                    "ok": False,
                    "index": i + 1,
                    "error_code": "E007",
                    "error_message": f"第 {i+1} 条处理失败: {str(e)}",
                })

        return {"ok": True, "total": len(results), "results": results}

    def format_output(self, result: Dict[str, Any], fmt: str = "json") -> str:
        """格式化输出"""
        if fmt == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif fmt == "text":
            if not result.get("ok"):
                return f"错误 {result.get('error_code', 'E010')}: {result.get('error_message', '')}"
            lines = []
            lines.append(f"输入类型: {result.get('input_type', 'unknown')}")
            lines.append(f"置信度: {result.get('confidence', 0)}% ({result.get('confidence_label', '')})")
            if result.get("warning"):
                lines.append(f"警告: {result['warning']}")
            lines.append("提取字段:")
            for field, values in result.get("extracted", {}).items():
                lines.append(f"  {field}: {', '.join(values)}")
            return "\n".join(lines)
        else:
            return make_error("E008", f"不支持的输出格式: {fmt}")

    def run(self, raw_input: str, output_format: str = "json") -> Dict[str, Any]:
        """标准流程入口"""
        # Step 1: 检查输入
        if not raw_input or not raw_input.strip():
            return make_error("E001")

        # Step 2: 核心处理
        result = self.process_single(raw_input)

        # Step 3: 输出校验
        if not result.get("ok"):
            return result

        # 格式检查
        if output_format not in ["json", "text"]:
            return make_error("E008", f"不支持的输出格式: {output_format}")

        return result


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """内置硬编码样例自检，不依赖外部文件/网络/工作目录"""
    print("=" * 60)
    print("opencrow 自检开始")
    print("=" * 60)

    try:
        processor = OpenCrowProcessor()

        # 测试样例 1: 文本输入，包含邮箱和手机号
        print("测试1: 文本提取...")
        test1 = "联系邮箱: test@example.com, 电话: 13812345678"
        r1 = processor.process_single(test1)
        assert r1["ok"], "测试1失败：处理失败"
        assert "email" in r1["extracted"], "测试1失败：未提取邮箱"
        assert "phone" in r1["extracted"], "测试1失败：未提取手机号"
        assert r1["confidence"] > 50, "测试1失败：置信度异常"
        print(f"[通过] 文本提取: 邮箱={r1['extracted']['email']}, 手机号={r1['extracted']['phone']}")

        # 测试样例 2: JSON 字典输入
        print("测试2: 字典结构化...")
        test2 = '{"name": "张三", "age": 30, "email": "zhangsan@test.com"}'
        r2 = processor.process_single(test2)
        assert r2["ok"], "测试2失败：处理失败"
        assert r2["input_type"] == "dict", "测试2失败：类型识别错误"
        assert "name" in r2["extracted"], "测试2失败：未提取name字段"
        print(f"[通过] 字典结构化: 字段数={len(r2['extracted'])}")

        # 测试样例 3: URL 输入
        print("测试3: URL识别...")
        test3 = "https://example.com/page?id=123"
        r3 = processor.process_single(test3)
        assert r3["ok"], "测试3失败：处理失败"
        assert r3["input_type"] == "url", "测试3失败：URL识别错误"
        print(f"[通过] URL识别: {r3['source']}")

        # 测试样例 4: 空输入（错误码 E001）
        print("测试4: 空输入错误处理...")
        r4 = processor.process_single("")
        assert not r4["ok"], "测试4失败：空输入应报错"
        assert r4["error_code"] == "E001", "测试4失败：错误码应为E001"
        print(f"[通过] 空输入错误处理: {r4['error_code']}")

        # 测试样例 5: 批量处理
        print("测试5: 批量处理...")
        test5 = ["测试文本", '{"key": "value"}', "https://test.com"]
        r5 = processor.batch_process(test5)
        assert r5["ok"], "测试5失败：批量处理失败"
        assert r5["total"] == 3, "测试5失败：批量数量错误"
        print(f"[通过] 批量处理: 共{r5['total']}条")

        # 测试样例 6: 置信度标注（低置信度）
        print("测试6: 低置信度标注...")
        test6 = "这是一段没有任何关键信息的普通文本"
        r6 = processor.process_single(test6)
        assert r6["ok"], "测试6失败：处理失败"
        assert r6["confidence"] < 50, "测试6失败：置信度应较低"
        print(f"[通过] 低置信度标注: {r6['confidence']}%")

        # 测试样例 7: 输出格式化
        print("测试7: 输出格式化...")
        test7 = "测试格式化输出 email@test.com"
        r7 = processor.process_single(test7)
        json_out = processor.format_output(r7, "json")
        assert isinstance(json_out, str), "测试7失败：JSON输出类型错误"
        text_out = processor.format_output(r7, "text")
        assert isinstance(text_out, str), "测试7失败：文本输出类型错误"
        print("[通过] 输出格式化: JSON和文本均正常")

        # 测试样例 8: 错误码体系完整性
        print("测试8: 错误码体系...")
        assert "E001" in ERROR_CODES and "E010" in ERROR_CODES, "测试8失败：错误码不完整"
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_CODES, f"测试8失败：缺少错误码 {code}"
        print("[通过] 错误码体系: E001-E005 完整")

        # 测试样例 9: 多字段提取
        print("测试9: 多字段提取...")
        test9 = "IP: 192.168.1.1, 日期: 2024-01-15, URL: https://test.com/path"
        r9 = processor.process_single(test9)
        assert r9["ok"], "测试9失败：处理失败"
        assert "ip" in r9["extracted"], "测试9失败：未提取IP"
        assert "date" in r9["extracted"], "测试9失败：未提取日期"
        assert "url" in r9["extracted"], "测试9失败：未提取URL"
        print(f"[通过] 多字段提取: {list(r9['extracted'].keys())}")

        # 测试样例 10: 批量处理错误隔离
        print("测试10: 批量错误隔离...")
        test10 = ["正常文本", "", "另一段正常文本"]
        r10 = processor.batch_process(test10)
        assert r10["ok"], "测试10失败：批量处理应继续"
        assert r10["results"][1]["error_code"] == "E001", "测试10失败：空输入错误码错误"
        assert r10["results"][0]["ok"] and r10["results"][2]["ok"], "测试10失败：正常项应成功"
        print("[通过] 批量错误隔离: 空输入不影响其他项")

        print("=" * 60)
        print("全部自检通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n自检失败: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n自检异常: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="opencrow 爬虫采集 - 结构化数据提取工具",
        epilog="示例: python main.py '联系邮箱: test@example.com' --format text"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="待处理的内容（文本/JSON/URL/文件路径），缺省时从stdin读取"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：每行作为一条独立输入"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        if run_selftest():
            return 0
        else:
            return 1

    # 创建处理器
    processor = OpenCrowProcessor()

    # 获取输入
    raw_input = args.input
    if raw_input is None:
        # 从 stdin 读取
        try:
            raw_input = sys.stdin.read().strip()
        except Exception as e:
            print(json.dumps(make_error("E006", str(e)), ensure_ascii=False))
            return 1

    # 批量模式
    if args.batch:
        lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
        result = processor.batch_process(lines)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        print(output)
        return 0 if result.get("ok") else 1

    # 单条模式
    result = processor.run(raw_input, args.format)

    # 输出
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(processor.format_output(result, "text"))

    # 返回码
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
