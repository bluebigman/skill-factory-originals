#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 安全分析·威胁建模·框架映射工具（独立实现）

本脚本依据"anthropic-cybersecurity-skills"功能规格，采用 clean-room 方式全新编写。
仅依赖 Python 标准库，不访问网络，不读取外部文件（除用户显式传入参数外）。

功能概览：
  1. 解析输入文本/日志，提取安全实体（IP、域名、哈希、CVE、攻击技术关键词等）。
  2. 将提取结果映射至六大权威框架（MITRE ATT&CK、NIST CSF 2.0、MITRE ATLAS、
     D3FEND、OWASP ASVS、ISO 27001 控制项）。
  3. 对每条映射给出置信度（高/中/低）与依据片段。
  4. 支持单条文本分析、批量文件分析、JSON/CSV/Markdown 三种输出格式。
  5. 提供 --selftest 离线自检模式（内置硬编码样例，不依赖任何外部资源）。

错误码约定：
  E001: 参数解析错误（未知参数、缺少必要参数等）
  E002: 输入文件不存在或不可读
  E003: 输入文本为空或无法解析
  E004: 输出格式不支持
  E005: 写入输出文件失败
  E006: 内部逻辑错误（不应发生）
  E007: 批量输入格式错误（非 UTF-8、非文本）
  E008: 映射结果为空（无任何可映射实体）
  E009: 自检失败（逻辑与内置样例不匹配）
  E010: 未知异常（兜底）

用法示例：
  python scripts/main.py --text "检测到勒索软件利用 CVE-2021-44228 进行横向移动，涉及 IP 1.2.3.4"
  python scripts/main.py --file report.txt --format json --output result.json
  python scripts/main.py --selftest
"""

import argparse
import csv
import hashlib
import ipaddress
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
VERSION = "1.0.2"
ERROR_CODES = {
    "E001": "参数解析错误",
    "E002": "输入文件不存在或不可读",
    "E003": "输入文本为空或无法解析",
    "E004": "输出格式不支持",
    "E005": "写入输出文件失败",
    "E006": "内部逻辑错误",
    "E007": "批量输入格式错误",
    "E008": "映射结果为空",
    "E009": "自检失败",
    "E010": "未知异常",
}

# 六大框架标识（用于输出标记）
FRAMEWORKS = [
    "MITRE_ATTACK",
    "NIST_CSF_2.0",
    "MITRE_ATLAS",
    "D3FEND",
    "OWASP_ASVS",
    "ISO_27001",
]

# 常见攻击技术关键词 → 框架编号映射（内置轻量知识库，用于演示与离线自检）
TECHNIQUE_KEYWORDS: Dict[str, Dict[str, str]] = {
    "钓鱼": {
        "MITRE_ATTACK": "T1566",
        "NIST_CSF_2.0": "PR.PT-4",
        "MITRE_ATLAS": "AML.T0001",
        "D3FEND": "D3-PH",
        "OWASP_ASVS": "V2.1",
        "ISO_27001": "A.8.7",
    },
    "勒索软件": {
        "MITRE_ATTACK": "T1486",
        "NIST_CSF_2.0": "PR.DS-1",
        "MITRE_ATLAS": "AML.T0029",
        "D3FEND": "D3-DA",
        "OWASP_ASVS": "V6.4",
        "ISO_27001": "A.12.6",
    },
    "横向移动": {
        "MITRE_ATTACK": "T1021",
        "NIST_CSF_2.0": "DE.AE-2",
        "MITRE_ATLAS": "AML.T0025",
        "D3FEND": "D3-NT",
        "OWASP_ASVS": "V11.1",
        "ISO_27001": "A.13.1",
    },
    "权限提升": {
        "MITRE_ATTACK": "T1068",
        "NIST_CSF_2.0": "PR.AC-4",
        "MITRE_ATLAS": "AML.T0020",
        "D3FEND": "D3-PE",
        "OWASP_ASVS": "V4.2",
        "ISO_27001": "A.9.2",
    },
    "数据泄露": {
        "MITRE_ATTACK": "T1041",
        "NIST_CSF_2.0": "PR.DS-2",
        "MITRE_ATLAS": "AML.T0023",
        "D3FEND": "D3-DE",
        "OWASP_ASVS": "V8.3",
        "ISO_27001": "A.8.2",
    },
    "SQL注入": {
        "MITRE_ATTACK": "T1190",
        "NIST_CSF_2.0": "PR.AC-5",
        "MITRE_ATLAS": "AML.T0010",
        "D3FEND": "D3-SI",
        "OWASP_ASVS": "V5.1",
        "ISO_27001": "A.14.2",
    },
    "DDoS": {
        "MITRE_ATTACK": "T1498",
        "NIST_CSF_2.0": "PR.DS-4",
        "MITRE_ATLAS": "AML.T0028",
        "D3FEND": "D3-DD",
        "OWASP_ASVS": "V6.2",
        "ISO_27001": "A.12.2",
    },
    "暴力破解": {
        "MITRE_ATTACK": "T1110",
        "NIST_CSF_2.0": "PR.AC-7",
        "MITRE_ATLAS": "AML.T0011",
        "D3FEND": "D3-BF",
        "OWASP_ASVS": "V2.2",
        "ISO_27001": "A.9.4",
    },
}

# 正则模式（仅用于实体提取）
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DOMAIN_RE = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b")
HASH_RE = re.compile(r"\b(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\b")
CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# 实体提取与数据解析
# ---------------------------------------------------------------------------
def extract_entities(text: str) -> Dict[str, List[str]]:
    """从原始文本中提取安全相关实体。

    返回格式:
        {
            "ipv4": ["1.2.3.4", ...],
            "domain": ["example.com", ...],
            "hash": ["a"*32, ...],
            "cve": ["CVE-2021-44228", ...],
            "technique_keywords": ["勒索软件", "横向移动", ...]
        }
    """
    if not text or not text.strip():
        return {"ipv4": [], "domain": [], "hash": [], "cve": [], "technique_keywords": []}

    entities: Dict[str, List[str]] = {
        "ipv4": [],
        "domain": [],
        "hash": [],
        "cve": [],
        "technique_keywords": [],
    }

    # IP 提取（过滤明显非法值，如 999.999.999.999）
    for match in IPV4_RE.findall(text):
        try:
            ip = ipaddress.ip_address(match)
            if ip.version == 4:
                entities["ipv4"].append(match)
        except ValueError:
            pass  # 非法 IP 忽略

    # 域名提取（排除纯数字、排除 IP 误匹配）
    for match in DOMAIN_RE.findall(text):
        if not match.replace(".", "").isdigit():
            entities["domain"].append(match.lower())

    # Hash 提取（MD5/SHA1/SHA256，统一小写）
    for match in HASH_RE.findall(text):
        entities["hash"].append(match.lower())

    # CVE 提取（统一大写）
    for match in CVE_RE.findall(text):
        entities["cve"].append(match.upper())

    # 技术关键词匹配（中文关键词，简单包含匹配）
    # 注意：不要使用 .lower() 处理中文，直接匹配即可
    for keyword in TECHNIQUE_KEYWORDS:
        if keyword in text:
            entities["technique_keywords"].append(keyword)

    # 去重（保持顺序）
    for key in entities:
        entities[key] = list(dict.fromkeys(entities[key]))

    return entities


# ---------------------------------------------------------------------------
# 框架映射与置信度计算
# ---------------------------------------------------------------------------
def map_to_framework(entity_type: str, entity_value: str) -> List[Dict[str, str]]:
    """将单个实体映射至六大框架。

    参数:
        entity_type: 实体类型（ipv4/domain/hash/cve/technique_keyword）
        entity_value: 实体值

    返回:
        映射结果列表，每项包含 framework, id, confidence, evidence
    """
    results: List[Dict[str, str]] = []

    # 技术关键词：直接查内置知识库
    if entity_type == "technique_keyword":
        if entity_value in TECHNIQUE_KEYWORDS:
            mapping = TECHNIQUE_KEYWORDS[entity_value]
            for framework in FRAMEWORKS:
                results.append({
                    "framework": framework,
                    "id": mapping.get(framework, "N/A"),
                    "confidence": "高",  # 明确关键词匹配 → 高置信度
                    "evidence": f"命中技术关键词: {entity_value}",
                })
        return results

    # 其他实体（IP/域名/Hash/CVE）：通用映射，置信度依据实体类型
    if entity_type == "cve":
        # CVE 通常对应 ATT&CK 的 T1190（利用漏洞）等，此处做通用映射
        base_id = "T1190"
        confidence = "高"  # CVE 是明确指标
        evidence = f"检测到漏洞编号: {entity_value}"
    elif entity_type == "ipv4":
        base_id = "T1071"
        confidence = "中"  # IP 可能为误报
        evidence = f"检测到可疑 IP: {entity_value}"
    elif entity_type == "domain":
        base_id = "T1583"
        confidence = "中"
        evidence = f"检测到可疑域名: {entity_value}"
    elif entity_type == "hash":
        base_id = "T1204"
        confidence = "高"  # Hash 是明确 IOC
        evidence = f"检测到文件哈希: {entity_value}"
    else:
        return results

    for framework in FRAMEWORKS:
        results.append({
            "framework": framework,
            "id": base_id,  # 简化处理：同一实体在各框架使用相同基础编号
            "confidence": confidence,
            "evidence": evidence,
        })
    return results


def analyze_text(text: str) -> Dict[str, Any]:
    """综合分析文本，返回结构化映射结果。

    返回:
        {
            "timestamp": "...",
            "input_preview": "...",
            "entities": {...},
            "mappings": [...],
            "summary": {...}
        }
    """
    if not text or not text.strip():
        raise ValueError("E003")  # 空输入

    entities = extract_entities(text)

    # 汇总所有实体，生成映射
    mappings: List[Dict[str, str]] = []
    entity_items: List[Tuple[str, str]] = []

    for etype, values in entities.items():
        for val in values:
            entity_items.append((etype, val))
            mappings.extend(map_to_framework(etype, val))

    # 若没有任何实体，但文本非空，尝试按技术关键词匹配（已在 extract 中处理）
    if not mappings:
        # 尝试直接匹配关键词（可能 extract 未命中，但文本确实包含）
        for keyword in TECHNIQUE_KEYWORDS:
            if keyword in text:
                mappings.extend(map_to_framework("technique_keyword", keyword))
                entity_items.append(("technique_keyword", keyword))

    if not mappings:
        raise ValueError("E008")  # 无任何可映射实体

    # 统计摘要
    summary = {
        "total_entities": len(entity_items),
        "total_mappings": len(mappings),
        "high_confidence": sum(1 for m in mappings if m["confidence"] == "高"),
        "medium_confidence": sum(1 for m in mappings if m["confidence"] == "中"),
        "low_confidence": sum(1 for m in mappings if m["confidence"] == "低"),
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_preview": text[:200] + ("..." if len(text) > 200 else ""),
        "entities": entities,
        "mappings": mappings,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_json(result: Dict[str, Any]) -> str:
    """JSON 输出（UTF-8，缩进 2）"""
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_csv(result: Dict[str, Any]) -> str:
    """CSV 输出（UTF-8 BOM 以兼容 Excel）"""
    output = tempfile.SpooledTemporaryFile(mode="w+", encoding="utf-8-sig", newline="")
    try:
        writer = csv.writer(output)
        writer.writerow(["框架", "编号", "置信度", "依据", "实体类型", "实体值"])

        # 需要将实体与映射关联，简化处理：直接遍历映射
        for m in result["mappings"]:
            # 从 evidence 中提取实体值（简化）
            evidence = m.get("evidence", "")
            writer.writerow([
                m.get("framework", ""),
                m.get("id", ""),
                m.get("confidence", ""),
                evidence,
                "",  # 实体类型（简化不单独列出）
                "",  # 实体值
            ])
        output.seek(0)
        return output.read()
    finally:
        output.close()


def format_markdown(result: Dict[str, Any]) -> str:
    """Markdown 表格输出"""
    lines = [
        "# 安全分析·框架映射结果",
        "",
        f"- **时间戳**: {result.get('timestamp', '')}",
        f"- **输入预览**: `{result.get('input_preview', '')}`",
        "",
        "## 映射结果",
        "",
        "| 框架 | 编号 | 置信度 | 依据 |",
        "|------|------|--------|------|",
    ]
    for m in result.get("mappings", []):
        lines.append(
            f"| {m.get('framework', '')} | {m.get('id', '')} | "
            f"{m.get('confidence', '')} | {m.get('evidence', '')} |"
        )
    lines.append("")
    lines.append("## 摘要")
    lines.append("")
    lines.append(f"- 总实体数: {result.get('summary', {}).get('total_entities', 0)}")
    lines.append(f"- 总映射数: {result.get('summary', {}).get('total_mappings', 0)}")
    lines.append(f"- 高置信度: {result.get('summary', {}).get('high_confidence', 0)}")
    lines.append(f"- 中置信度: {result.get('summary', {}).get('medium_confidence', 0)}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 文件处理与命令行入口
# ---------------------------------------------------------------------------
def analyze_file(filepath: str) -> Dict[str, Any]:
    """读取文本文件并分析"""
    if not os.path.isfile(filepath):
        raise FileNotFoundError("E002")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, OSError) as e:
        raise ValueError("E007") from e
    return analyze_text(content)


def write_output(content: str, output_path: Optional[str]) -> None:
    """写入输出文件或打印到 stdout"""
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            raise IOError("E005") from e
    else:
        print(content)


def run_selftest() -> int:
    """离线自检：使用内置硬编码样例验证核心逻辑。"""
    try:
        # 样例 1：勒索软件 + CVE + IP 的综合文本
        sample1 = (
            "检测到勒索软件攻击，利用 CVE-2021-44228 漏洞进行横向移动，"
            "攻击源 IP 为 192.168.1.100，域名 evil.example.com，文件哈希 a" * 64
        )
        result1 = analyze_text(sample1)

        # 断言 1：应包含 CVE 实体
        assert len(result1["entities"]["cve"]) >= 1, "E009: CVE 提取失败"
        # 断言 2：应包含 IP 实体
        assert len(result1["entities"]["ipv4"]) >= 1, "E009: IP 提取失败"
        # 断言 3：应包含技术关键词（勒索软件/横向移动至少一个）
        assert len(result1["entities"]["technique_keywords"]) >= 1, "E009: 关键词提取失败"
        # 断言 4：映射结果应覆盖六大框架
        frameworks_in_result = {m["framework"] for m in result1["mappings"]}
        assert len(frameworks_in_result) >= 6, "E009: 框架覆盖不足"
        # 断言 5：高置信度映射应存在
        assert result1["summary"]["high_confidence"] >= 1, "E009: 高置信度映射缺失"
        # 断言 6：总映射数应大于等于实体数（每个实体至少映射到 6 个框架）
        assert result1["summary"]["total_mappings"] >= result1["summary"]["total_entities"], "E009: 映射数异常"

        # 样例 2：SQL 注入（单一技术）
        sample2 = "应用程序存在 SQL 注入漏洞，可被用于数据泄露。"
        result2 = analyze_text(sample2)
        # 断言：应包含 SQL注入 关键词
        assert "SQL注入" in result2["entities"]["technique_keywords"], "E009: SQL注入关键词缺失"
        # 断言：映射结果非空
        assert len(result2["mappings"]) >= 6, "E009: SQL注入映射不足"

        # 样例 3：空文本应抛错
        try:
            analyze_text("   ")
            raise AssertionError("E009: 空文本未抛错")
        except ValueError as e:
            assert str(e) == "E003", "E009: 空文本错误码不正确"

        # 样例 4：纯 IP 文本
        result4 = analyze_text("可疑流量来自 10.0.0.5")
        assert len(result4["entities"]["ipv4"]) == 1, "E009: 纯IP提取失败"

        # 输出自检成功信息
        print("[SELFTEST] 全部断言通过，核心逻辑正常。")
        print(f"[SELFTEST] 样例1 实体数: {result1['summary']['total_entities']}, 映射数: {result1['summary']['total_mappings']}")
        print(f"[SELFTEST] 样例2 映射数: {len(result2['mappings'])}")
        return 0
    except AssertionError as e:
        print(f"[SELFTEST] 失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # 兜底
        print(f"[SELFTEST] 未知异常: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="安全分析·威胁建模·框架映射工具（独立实现）",
        epilog="错误码: " + ", ".join(f"{k}={v}" for k, v in ERROR_CODES.items()),
    )
    parser.add_argument("--text", type=str, help="直接输入待分析文本")
    parser.add_argument("--file", type=str, help="输入文件路径（UTF-8 文本）")
    parser.add_argument("--format", choices=["json", "csv", "markdown"], default="json", help="输出格式")
    parser.add_argument("--output", type=str, help="输出文件路径（默认 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if args.text and args.file:
        print("E001: 不能同时指定 --text 和 --file", file=sys.stderr)
        return 1
    if not args.text and not args.file:
        print("E001: 必须指定 --text 或 --file", file=sys.stderr)
        return 1

    try:
        # 输入获取
        if args.text:
            result = analyze_text(args.text)
        else:
            result = analyze_file(args.file)

        # 输出格式化
        if args.format == "json":
            output = format_json(result)
        elif args.format == "csv":
            output = format_csv(result)
        elif args.format == "markdown":
            output = format_markdown(result)
        else:
            raise ValueError("E004")

        # 写入输出
        write_output(output, args.output)
        return 0

    except FileNotFoundError as e:
        print(f"E002: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        code = str(e)
        if code in ERROR_CODES:
            print(f"{code}: {ERROR_CODES[code]}", file=sys.stderr)
        else:
            print(f"E006: {e}", file=sys.stderr)
        return 1
    except IOError as e:
        print(f"E005: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # 兜底
        print(f"E010: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
