#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: scripts/main.py
功能: 安全分析、威胁建模、框架映射（clean-room 实现）
说明: 依据功能规格独立实现，不复制既有代码。
      将安全数据映射至 MITRE ATT&CK、NIST CSF 2.0、MITRE ATLAS、D3F 等框架。
"""

import argparse
import json
import sys
import os
from typing import Dict, List, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入数据格式错误",
    "E003": "输入文件不存在或不可读",
    "E004": "JSON 解析失败",
    "E005": "缺少必填字段",
    "E006": "映射引擎内部错误",
    "E007": "输出格式不支持",
    "E008": "置信度计算失败",
    "E009": "批量处理失败",
    "E010": "未知错误",
}


def fail(error_code: str, message: str = "") -> None:
    """输出错误信息并以错误码退出。"""
    err_text = ERROR_CODES.get(error_code, ERROR_CODES["E010"])
    if message:
        print(f"[{error_code}] {err_text}: {message}", file=sys.stderr)
    else:
        print(f"[{error_code}] {err_text}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 框架定义（内置知识库，仅用于演示映射逻辑）
# ---------------------------------------------------------------------------
# 注意：真实场景中这些映射关系应来自权威数据源。
# 此处仅内置少量示例，用于自检和演示。

FRAMEWORK_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "MITRE ATT&CK": {
        "T1059": ["command", "shell", "exec", "powershell", "cmd"],
        "T1566": ["phishing", "email", "link", "attachment"],
        "T1027": ["obfuscat", "encode", "pack", "encrypt"],
        "T1078": ["credential", "login", "account", "valid"],
        "T1041": ["exfil", "c2", "command control", "beacon"],
    },
    "NIST CSF 2.0": {
        "DE.CM": ["detect", "monitor", "alert", "log"],
        "PR.AC": ["access", "auth", "identity", "permission"],
        "PR.DS": ["encrypt", "data protection", "backup"],
        "RS.MI": ["contain", "mitigate", "isolate", "block"],
        "ID.AM": ["inventory", "asset", "hardware", "software"],
    },
    "MITRE ATLAS": {
        "AML.T0020": ["model", "dataset", "poison", "training"],
        "AML.T0010": ["adversarial", "perturb", "evasion"],
        "AML.T0030": ["extract", "steal", "model", "infer"],
    },
    "D3FEND": {
        "D3-IA": ["authentication", "identity", "verify"],
        "D3-NI": ["network", "isolation", "segment"],
        "D3-PA": ["process", "allowlist", "execution"],
    },
    "CIS Controls": {
        "CIS-01": ["inventory", "asset", "hardware"],
        "CIS-06": ["access", "control", "privilege"],
        "CIS-13": ["monitor", "log", "audit"],
    },
    "ISO 27001": {
        "A.9.1.1": ["access", "policy", "user"],
        "A.12.4.1": ["log", "event", "record"],
        "A.13.1.1": ["network", "control", "segment"],
    },
}


# 置信度计算：基于关键词命中数量与文本长度
def compute_confidence(text: str, matched_keywords: List[str]) -> str:
    """根据匹配关键词数量与文本长度计算置信度（高/中/低）。"""
    try:
        if not text or not matched_keywords:
            return "低"
        text_len = len(text)
        hit_count = len(matched_keywords)
        # 宽松阈值：命中数 >= 3 且文本长度 >= 20 -> 高；命中数 >= 1 -> 中；否则低
        if hit_count >= 3 and text_len >= 20:
            return "高"
        elif hit_count >= 1:
            return "中"
        else:
            return "低"
    except Exception:
        return "低"


# ---------------------------------------------------------------------------
# 核心映射引擎
# ---------------------------------------------------------------------------
class ThreatMapper:
    """将安全文本映射到多个框架。"""

    def __init__(self) -> None:
        self.frameworks = FRAMEWORK_KEYWORDS

    def map_text(self, text: str) -> List[Dict[str, Any]]:
        """将一段文本映射到所有框架，返回结构化结果列表。"""
        if not text or not isinstance(text, str):
            raise ValueError("输入文本为空或类型错误")

        results: List[Dict[str, Any]] = []
        text_lower = text.lower()

        for framework, tech_map in self.frameworks.items():
            for tech_id, keywords in tech_map.items():
                matched = [kw for kw in keywords if kw in text_lower]
                if matched:
                    confidence = compute_confidence(text, matched)
                    results.append({
                        "framework": framework,
                        "technique_id": tech_id,
                        "matched_keywords": matched,
                        "confidence": confidence,
                    })

        # 若没有任何匹配，返回一条占位记录（符合 L3 边界）
        if not results:
            results.append({
                "framework": "未知",
                "technique_id": "N/A",
                "matched_keywords": [],
                "confidence": "低",
                "note": "未匹配到已知框架条目，输入信息可能不完整",
            })

        return results

    def batch_map(self, items: List[str]) -> List[Dict[str, Any]]:
        """批量处理多条文本。"""
        if not items:
            return []
        batch_results = []
        for idx, item in enumerate(items):
            try:
                mapped = self.map_text(item)
                batch_results.append({
                    "index": idx,
                    "input_preview": item[:50] + ("..." if len(item) > 50 else ""),
                    "mappings": mapped,
                })
            except Exception as e:
                batch_results.append({
                    "index": idx,
                    "input_preview": str(item)[:50],
                    "error": f"处理失败: {str(e)}",
                    "mappings": [],
                })
        return batch_results


# ---------------------------------------------------------------------------
# 数据解析与输出
# ---------------------------------------------------------------------------
def parse_input(data: Any) -> List[str]:
    """将输入数据解析为文本列表。

    支持:
    - 字符串: 按换行分割
    - 列表: 每个元素作为一条文本
    - 字典: 检查 'texts' 或 'items' 字段
    """
    if isinstance(data, str):
        # 按换行分割，过滤空行
        return [line.strip() for line in data.splitlines() if line.strip()]

    if isinstance(data, list):
        # 每个元素转为字符串
        return [str(item) for item in data if str(item).strip()]

    if isinstance(data, dict):
        # 支持 'texts' 或 'items' 键
        for key in ("texts", "items", "data"):
            if key in data and isinstance(data[key], list):
                return [str(item) for item in data[key] if str(item).strip()]
        # 若 dict 中有 'text' 字段
        if "text" in data and isinstance(data["text"], str):
            return [data["text"]]

    raise ValueError("无法解析输入数据格式")


def format_output(results: List[Dict[str, Any]], output_format: str) -> str:
    """将结果格式化为指定格式（json/csv/markdown）。"""
    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)

    if output_format == "csv":
        # 简单 CSV 输出
        lines = ["framework,technique_id,confidence,matched_keywords"]
        for item in results:
            if "mappings" in item:
                # 批量结果
                for m in item.get("mappings", []):
                    fw = m.get("framework", "")
                    tid = m.get("technique_id", "")
                    conf = m.get("confidence", "")
                    kws = ";".join(m.get("matched_keywords", []))
                    lines.append(f"{fw},{tid},{conf},{kws}")
            else:
                fw = item.get("framework", "")
                tid = item.get("technique_id", "")
                conf = item.get("confidence", "")
                kws = ";".join(item.get("matched_keywords", []))
                lines.append(f"{fw},{tid},{conf},{kws}")
        return "\n".join(lines)

    if output_format == "markdown":
        lines = ["| 框架 | 技术ID | 置信度 | 关键词 |", "|------|--------|--------|--------|"]
        for item in results:
            if "mappings" in item:
                for m in item.get("mappings", []):
                    fw = m.get("framework", "")
                    tid = m.get("technique_id", "")
                    conf = m.get("confidence", "")
                    kws = ",".join(m.get("matched_keywords", []))
                    lines.append(f"| {fw} | {tid} | {conf} | {kws} |")
            else:
                fw = item.get("framework", "")
                tid = item.get("technique_id", "")
                conf = item.get("confidence", "")
                kws = ",".join(item.get("matched_keywords", []))
                lines.append(f"| {fw} | {tid} | {conf} | {kws} |")
        return "\n".join(lines)

    # 默认 json
    return json.dumps(results, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自检模块（硬编码样例数据，离线可运行）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """内置硬编码样例数据，自检核心逻辑。不依赖外部文件。"""
    print("开始自检...")

    # 硬编码测试样例
    test_samples = [
        "攻击者通过钓鱼邮件发送恶意链接，诱导用户点击执行 PowerShell 命令",
        "检测到异常登录行为，使用有效凭证进行未授权访问",
        "网络流量中发现 C2 通信特征，疑似数据外传",
        "模型训练数据被投毒，导致 AI 系统行为异常",
        "普通文本，不包含任何安全相关信息",
    ]

    # 创建映射引擎
    mapper = ThreatMapper()

    # 测试单条映射
    try:
        for sample in test_samples:
            result = mapper.map_text(sample)
            assert isinstance(result, list), "映射结果应为列表"
            assert len(result) > 0, "映射结果不应为空"
            assert "framework" in result[0], "结果缺少 framework 字段"
            assert "technique_id" in result[0], "结果缺少 technique_id 字段"
            assert "confidence" in result[0], "结果缺少 confidence 字段"
            # 置信度必须是 高/中/低 之一
            assert result[0]["confidence"] in ("高", "中", "低"), "置信度取值非法"
        print("  单条映射测试: 通过")
    except AssertionError as e:
        print(f"  单条映射测试: 失败 - {e}")
        return 1

    # 测试批量映射
    try:
        batch_result = mapper.batch_map(test_samples)
        assert isinstance(batch_result, list), "批量结果应为列表"
        assert len(batch_result) == len(test_samples), "批量结果数量不匹配"
        for item in batch_result:
            assert "index" in item, "批量结果缺少 index"
            assert "mappings" in item, "批量结果缺少 mappings"
            assert len(item["mappings"]) > 0, "批量映射结果不应为空"
        print("  批量映射测试: 通过")
    except AssertionError as e:
        print(f"  批量映射测试: 失败 - {e}")
        return 1

    # 测试输入解析
    try:
        parsed = parse_input("第一行\n第二行\n")
        assert len(parsed) == 2, "字符串解析应得到两行"
        parsed_list = parse_input(["a", "b", "c"])
        assert len(parsed_list) == 3, "列表解析应得到三个元素"
        parsed_dict = parse_input({"texts": ["x", "y"]})
        assert len(parsed_dict) == 2, "字典解析应得到两个元素"
        print("  输入解析测试: 通过")
    except AssertionError as e:
        print(f"  输入解析测试: 失败 - {e}")
        return 1

    # 测试输出格式化
    try:
        sample_result = mapper.map_text("钓鱼邮件攻击")
        json_out = format_output(sample_result, "json")
        assert json.loads(json_out), "JSON 输出无效"
        csv_out = format_output(sample_result, "csv")
        assert "framework" in csv_out, "CSV 输出缺少表头"
        md_out = format_output(sample_result, "markdown")
        assert "|" in md_out, "Markdown 输出缺少表格"
        print("  输出格式化测试: 通过")
    except AssertionError as e:
        print(f"  输出格式化测试: 失败 - {e}")
        return 1

    # 测试边界情况
    try:
        # 空输入
        empty_result = mapper.map_text("")
        assert len(empty_result) > 0, "空输入应有占位结果"
        # 纯噪声输入
        noise_result = mapper.map_text("asdfghjklqwerty")
        assert len(noise_result) > 0, "噪声输入应有占位结果"
        print("  边界情况测试: 通过")
    except AssertionError as e:
        print(f"  边界情况测试: 失败 - {e}")
        return 1

    print("所有自检项通过 ✅")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="安全分析威胁建模框架映射工具",
        epilog="示例: python main.py -i input.json -o output.json --format json",
    )
    parser.add_argument(
        "-i", "--input",
        help="输入文件路径（JSON 或文本文件），或使用 -d 直接传入数据",
    )
    parser.add_argument(
        "-d", "--data",
        help="直接传入文本数据（字符串或 JSON 字符串）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "csv", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式
    try:
        # 获取输入数据
        if args.data:
            # 尝试解析为 JSON，失败则作为纯文本
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError:
                data = args.data
        elif args.input:
            if not os.path.isfile(args.input):
                fail("E003", f"文件不存在: {args.input}")
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    content = f.read()
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = content
            except Exception as e:
                fail("E003", f"读取文件失败: {e}")
        else:
            fail("E002", "请提供 -i 或 -d 参数")

        # 解析输入为文本列表
        try:
            texts = parse_input(data)
        except ValueError as e:
            fail("E002", str(e))

        if not texts:
            fail("E002", "输入数据为空")

        # 执行映射
        mapper = ThreatMapper()
        try:
            results = mapper.batch_map(texts)
        except Exception as e:
            fail("E006", str(e))

        # 格式化输出
        try:
            output = format_output(results, args.format)
        except Exception as e:
            fail("E007", str(e))

        # 输出
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"结果已写入: {args.output}")
            except Exception as e:
                fail("E003", f"写入文件失败: {e}")
        else:
            print(output)

        return 0

    except SystemExit:
        raise
    except Exception as e:
        fail("E010", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
