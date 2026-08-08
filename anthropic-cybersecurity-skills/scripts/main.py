#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

安全分析·威胁建模·框架映射 独立实现（clean-room）
----------------------------------------------------
仅依据功能规格独立编写，不复制任何既有代码。

支持能力：
  C1  数据解析与结构化（从文本/日志/URL/文件提取实体、行为、指标）
  C2  多框架映射（MITRE ATT&CK / NIST CSF 2.0 / MITRE ATLAS / D3F 等六大框架）
  C3  置信度标注（高/中/低）
  C4  批量处理（多条目输入，批量输出结构化结果）
  C5  自定义格式输出（JSON / CSV / Markdown 表格）

明确边界（不实现）：
  L1  不执行实时扫描（不连接外部系统）
  L2  不提供修复建议
  L3  不保证覆盖全部框架条目（缺失字段以占位符标注）
  L4  不替代专业判断（输出为辅助参考）

错误码约定：
  E001  未知命令或参数错误
  E002  输入文件无法读取
  E003  输入数据格式非法（非 JSON/CSV/TXT）
  E004  输出格式不支持
  E005  缺少必要字段
  E006  框架名称不支持
  E007  内部逻辑错误（不应发生）
  E008  批量输入为空
  E009  自定义字段名非法
  E010  运行时异常（兜底）

用法示例：
  python scripts/main.py --input data.json --output result.json --format json
  python scripts/main.py --selftest
  python scripts/main.py --help
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

SUPPORTED_FRAMEWORKS = [
    "mitre_attck",      # MITRE ATT&CK
    "nist_csf",         # NIST CSF 2.0
    "mitre_atlas",      # MITRE ATLAS
    "d3f",              # D3FEND (D3F)
    "iso_27001",        # ISO/IEC 27001 控制项（补充）
    "owasp",            # OWASP ASVS（补充）
]

# 占位符（用于缺失字段）
PLACEHOLDER = "N/A"

# 置信度级别
CONFIDENCE_LEVELS = ["high", "medium", "low"]

# 输出格式
OUTPUT_FORMATS = ["json", "csv", "markdown"]


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------


class SecurityEntity:
    """安全实体：从输入中提取的结构化信息单元。"""

    def __init__(
        self,
        entity_type: str,
        value: str,
        context: Optional[str] = None,
        source: Optional[str] = None,
    ):
        self.entity_type = entity_type          # 实体类型：ip/domain/hash/url/technique...
        self.value = value                      # 实体值
        self.context = context or ""            # 上下文描述
        self.source = source or ""              # 来源（如日志文件、报告段落）

    def to_dict(self) -> Dict[str, str]:
        return {
            "entity_type": self.entity_type,
            "value": self.value,
            "context": self.context,
            "source": self.source,
        }


class FrameworkMapping:
    """框架映射结果：一个实体到某个框架条目的映射。"""

    def __init__(
        self,
        framework: str,
        framework_id: str,
        framework_name: str,
        confidence: str,
        evidence: str,
    ):
        self.framework = framework
        self.framework_id = framework_id
        self.framework_name = framework_name
        self.confidence = confidence
        self.evidence = evidence

    def to_dict(self) -> Dict[str, str]:
        return {
            "framework": self.framework,
            "framework_id": self.framework_id,
            "framework_name": self.framework_name,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


class AnalysisResult:
    """单条输入数据的完整分析结果。"""

    def __init__(self, input_text: str):
        self.input_text = input_text
        self.entities: List[SecurityEntity] = []
        self.mappings: List[FrameworkMapping] = []
        self.notes: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_text": self.input_text,
            "entities": [e.to_dict() for e in self.entities],
            "mappings": [m.to_dict() for m in self.mappings],
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# 数据解析与结构化（C1）
# ---------------------------------------------------------------------------


def extract_entities(text: str) -> List[SecurityEntity]:
    """
    从文本中提取安全实体（IP、域名、URL、哈希、文件路径、攻击技术关键词等）。

    采用宽松、启发式的提取方式，不依赖外部库。
    """
    entities: List[SecurityEntity] = []
    if not text:
        return entities

    # 提取 IPv4 地址
    ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    for match in re.finditer(ip_pattern, text):
        ip = match.group()
        # 简单过滤非法八位组
        parts = ip.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            entities.append(SecurityEntity("ip", ip, context=text[max(0, match.start()-30):match.end()+30]))

    # 提取域名（简易）
    domain_pattern = r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
    for match in re.finditer(domain_pattern, text):
        domain = match.group()
        # 排除纯 IP 的情况
        if not domain.replace(".", "").isdigit():
            entities.append(SecurityEntity("domain", domain, context=text[max(0, match.start()-30):match.end()+30]))

    # 提取 URL
    url_pattern = r"https?://[^\s]+"
    for match in re.finditer(url_pattern, text):
        entities.append(SecurityEntity("url", match.group(), context=text[max(0, match.start()-30):match.end()+30]))

    # 提取文件哈希（MD5/SHA1/SHA256 等，32/40/64 位十六进制）
    hash_pattern = r"\b(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\b"
    for match in re.finditer(hash_pattern, text):
        entities.append(SecurityEntity("hash", match.group(), context=text[max(0, match.start()-30):match.end()+30]))

    # 提取常见攻击技术关键词（启发式）
    technique_keywords = [
        "phishing", "ransomware", "ddos", "sql injection", "xss",
        "privilege escalation", "lateral movement", "data exfiltration",
        "command and control", "c2", "malware", "trojan", "worm",
        "zero-day", "exploit", "backdoor", "keylogger", "spyware",
        "botnet", "social engineering", "brute force", "buffer overflow",
    ]
    text_lower = text.lower()
    for kw in technique_keywords:
        if kw in text_lower:
            entities.append(SecurityEntity("technique", kw, context=text))

    # 去重（按 entity_type + value）
    seen = set()
    unique_entities = []
    for e in entities:
        key = (e.entity_type, e.value)
        if key not in seen:
            seen.add(key)
            unique_entities.append(e)

    return unique_entities


# ---------------------------------------------------------------------------
# 多框架映射（C2 + C3）
# ---------------------------------------------------------------------------


def _map_technique_to_frameworks(technique: str) -> List[FrameworkMapping]:
    """
    将攻击技术名称映射到六大框架。

    返回映射列表，每个映射包含框架、ID、名称、置信度、证据。
    置信度判断规则（宽松）：
      - 技术名称在框架关键词表中明确匹配 -> high
      - 技术名称与框架关键词部分匹配   -> medium
      - 无匹配但技术名称有效           -> low
    """
    technique_lower = technique.lower()
    mappings: List[FrameworkMapping] = []

    # MITRE ATT&CK 映射表（部分常见技术）
    attck_map = {
        "phishing": ("T1566", "Phishing", "high"),
        "ransomware": ("T1486", "Data Encrypted for Impact", "high"),
        "ddos": ("T1498", "Network Denial of Service", "high"),
        "sql injection": ("T1190", "Exploit Public-Facing Application", "medium"),
        "xss": ("T1059", "Command and Scripting Interpreter", "low"),
        "privilege escalation": ("T1068", "Exploitation for Privilege Escalation", "high"),
        "lateral movement": ("T1021", "Remote Services", "high"),
        "data exfiltration": ("T1048", "Exfiltration Over Alternative Protocol", "high"),
        "command and control": ("T1071", "Application Layer Protocol", "high"),
        "c2": ("T1071", "Application Layer Protocol", "medium"),
        "malware": ("T1204", "User Execution", "low"),
        "trojan": ("T1204", "User Execution", "medium"),
        "worm": ("T1566", "Phishing", "low"),
        "zero-day": ("T1190", "Exploit Public-Facing Application", "medium"),
        "exploit": ("T1190", "Exploit Public-Facing Application", "medium"),
        "backdoor": ("T1505", "Server Software Component", "high"),
        "keylogger": ("T1056", "Input Capture", "high"),
        "spyware": ("T1056", "Input Capture", "medium"),
        "botnet": ("T1583", "Acquire Infrastructure", "medium"),
        "social engineering": ("T1566", "Phishing", "high"),
        "brute force": ("T1110", "Brute Force", "high"),
        "buffer overflow": ("T1200", "Hardware Additions", "low"),
    }

    if technique_lower in attck_map:
        fid, fname, conf = attck_map[technique_lower]
        mappings.append(FrameworkMapping(
            framework="mitre_attck",
            framework_id=fid,
            framework_name=fname,
            confidence=conf,
            evidence=f"技术关键词 '{technique}' 匹配 MITRE ATT&CK 条目 {fid}",
        ))
    else:
        # 未匹配到具体条目，给一个低置信度的泛化映射
        mappings.append(FrameworkMapping(
            framework="mitre_attck",
            framework_id="T0XXX",
            framework_name="Unclassified Technique",
            confidence="low",
            evidence=f"技术关键词 '{technique}' 未在本地 ATT&CK 表中找到精确匹配，给予泛化映射",
        ))

    # NIST CSF 2.0 映射（按功能域）
    nist_map = {
        "phishing": ("PR.PT", "Protective Technology", "high"),
        "ransomware": ("PR.DS", "Data Security", "high"),
        "ddos": ("PR.DS", "Data Security", "medium"),
        "sql injection": ("PR.PT", "Protective Technology", "medium"),
        "xss": ("PR.PT", "Protective Technology", "low"),
        "privilege escalation": ("PR.AC", "Access Control", "high"),
        "lateral movement": ("PR.AC", "Access Control", "high"),
        "data exfiltration": ("DE.CM", "Continuous Monitoring", "high"),
        "command and control": ("DE.CM", "Continuous Monitoring", "high"),
        "c2": ("DE.CM", "Continuous Monitoring", "medium"),
        "malware": ("PR.DS", "Data Security", "low"),
        "trojan": ("PR.DS", "Data Security", "medium"),
        "worm": ("PR.DS", "Data Security", "low"),
        "zero-day": ("DE.CM", "Continuous Monitoring", "medium"),
        "exploit": ("DE.CM", "Continuous Monitoring", "medium"),
        "backdoor": ("PR.PT", "Protective Technology", "high"),
        "keylogger": ("PR.PT", "Protective Technology", "high"),
        "spyware": ("PR.PT", "Protective Technology", "medium"),
        "botnet": ("DE.CM", "Continuous Monitoring", "medium"),
        "social engineering": ("PR.AT", "Awareness and Training", "high"),
        "brute force": ("PR.AC", "Access Control", "high"),
        "buffer overflow": ("PR.PT", "Protective Technology", "low"),
    }

    if technique_lower in nist_map:
        fid, fname, conf = nist_map[technique_lower]
        mappings.append(FrameworkMapping(
            framework="nist_csf",
            framework_id=fid,
            framework_name=fname,
            confidence=conf,
            evidence=f"技术关键词 '{technique}' 匹配 NIST CSF 2.0 功能域 {fid}",
        ))
    else:
        mappings.append(FrameworkMapping(
            framework="nist_csf",
            framework_id="PR.PT",
            framework_name="Protective Technology",
            confidence="low",
            evidence=f"技术关键词 '{technique}' 未在本地 NIST 表中匹配，给予默认映射",
        ))

    # MITRE ATLAS 映射（AI 领域攻击）
    atlas_map = {
        "phishing": ("AML.T0026", "Phishing", "high"),
        "ransomware": ("AML.T0028", "Ransomware", "medium"),
        "ddos": ("AML.T0029", "Denial of Service", "medium"),
        "sql injection": ("AML.T0010", "Injection", "low"),
        "xss": ("AML.T0010", "Injection", "low"),
        "privilege escalation": ("AML.T0012", "Privilege Escalation", "high"),
        "lateral movement": ("AML.T0013", "Lateral Movement", "high"),
        "data exfiltration": ("AML.T0022", "Exfiltration", "high"),
        "command and control": ("AML.T0024", "Command and Control", "high"),
        "c2": ("AML.T0024", "Command and Control", "medium"),
        "malware": ("AML.T0018", "Malware", "low"),
        "trojan": ("AML.T0018", "Malware", "medium"),
        "worm": ("AML.T0018", "Malware", "low"),
        "zero-day": ("AML.T0019", "Exploit", "medium"),
        "exploit": ("AML.T0019", "Exploit", "medium"),
        "backdoor": ("AML.T0020", "Backdoor", "high"),
        "keylogger": ("AML.T0021", "Input Capture", "high"),
        "spyware": ("AML.T0021", "Input Capture", "medium"),
        "botnet": ("AML.T0025", "Botnet", "medium"),
        "social engineering": ("AML.T0026", "Phishing", "high"),
        "brute force": ("AML.T0011", "Brute Force", "high"),
        "buffer overflow": ("AML.T0019", "Exploit", "low"),
    }

    if technique_lower in atlas_map:
        fid, fname, conf = atlas_map[technique_lower]
        mappings.append(FrameworkMapping(
            framework="mitre_atlas",
            framework_id=fid,
            framework_name=fname,
            confidence=conf,
            evidence=f"技术关键词 '{technique}' 匹配 MITRE ATLAS 条目 {fid}",
        ))
    else:
        mappings.append(FrameworkMapping(
            framework="mitre_atlas",
            framework_id="AML.T0000",
            framework_name="Unclassified",
            confidence="low",
            evidence=f"技术关键词 '{technique}' 未在本地 ATLAS 表中匹配",
        ))

    # D3FEND（D3F）映射
    d3f_map = {
        "phishing": ("D3-PHISH", "Phishing Detection", "high"),
        "ransomware": ("D3-RAN", "Ransomware Detection", "high"),
        "ddos": ("D3-DDOS", "DDoS Mitigation", "medium"),
        "sql injection": ("D3-SQLI", "SQL Injection Detection", "medium"),
        "xss": ("D3-XSS", "XSS Detection", "low"),
        "privilege escalation": ("D3-PE", "Privilege Escalation Detection", "high"),
        "lateral movement": ("D3-LM", "Lateral Movement Detection", "high"),
        "data exfiltration": ("D3-DE", "Data Exfiltration Detection", "high"),
        "command and control": ("D3-C2", "C2 Detection", "high"),
        "c2": ("D3-C2", "C2 Detection", "medium"),
        "malware": ("D3-MAL", "Malware Detection", "low"),
        "trojan": ("D3-MAL", "Malware Detection", "medium"),
        "worm": ("D3-MAL", "Malware Detection", "low"),
        "zero-day": ("D3-ZD", "Zero-Day Detection", "medium"),
        "exploit": ("D3-EXP", "Exploit Detection", "medium"),
        "backdoor": ("D3-BD", "Backdoor Detection", "high"),
        "keylogger": ("D3-KL", "Keylogger Detection", "high"),
        "spyware": ("D3-SPY", "Spyware Detection", "medium"),
        "botnet": ("D3-BOT", "Botnet Detection", "medium"),
        "social engineering": ("D3-SE", "Social Engineering Detection", "high"),
        "brute force": ("D3-BF", "Brute Force Detection", "high"),
        "buffer overflow": ("D3-BO", "Buffer Overflow Detection", "low"),
    }

    if technique_lower in d3f_map:
        fid, fname, conf = d3f_map[technique_lower]
        mappings.append(FrameworkMapping(
            framework="d3f",
            framework_id=fid,
            framework_name=fname,
            confidence=conf,
            evidence=f"技术关键词 '{technique}' 匹配 D3FEND 条目 {fid}",
        ))
    else:
        mappings.append(FrameworkMapping(
            framework="d3f",
            framework_id="D3-UNK",
            framework_name="Unknown",
            confidence="low",
            evidence=f"技术关键词 '{technique}' 未在本地 D3FEND 表中匹配",
        ))

    # ISO 27001 映射（补充）
    iso_map = {
        "phishing": ("A.7.2.2", "Security Awareness Training", "high"),
        "ransomware": ("A.8.12", "Data Leakage Prevention", "medium"),
        "ddos": ("A.8.20", "Networks Security", "medium"),
        "sql injection": ("A.8.26", "Application Security", "low"),
        "xss": ("A.8.26", "Application Security", "low"),
        "privilege escalation": ("A.8.2", "Access Control", "high"),
        "lateral movement": ("A.8.2", "Access Control", "high"),
        "data exfiltration": ("A.8.12", "Data Leakage Prevention", "high"),
        "command and control": ("A.8.20", "Networks Security", "high"),
        "c2": ("A.8.20", "Networks Security", "medium"),
        "malware": ("A.8.7", "Protection Against Malware", "low"),
        "trojan": ("A.8.7", "Protection Against Malware", "medium"),
        "worm": ("A.8.7", "Protection Against Malware", "low"),
        "zero-day": ("A.8.25", "Secure Development Life Cycle", "medium"),
        "exploit": ("A.8.25", "Secure Development Life Cycle", "medium"),
        "backdoor": ("A.8.20", "Networks Security", "high"),
        "keylogger": ("A.8.7", "Protection Against Malware", "high"),
        "spyware": ("A.8.7", "Protection Against Malware", "medium"),
        "botnet": ("A.8.20", "Networks Security", "medium"),
        "social engineering": ("A.7.2.2", "Security Awareness Training", "high"),
        "brute force": ("A.8.2", "Access Control", "high"),
        "buffer overflow": ("A.8.26", "Application Security", "low"),
    }

    if technique_lower in iso_map:
        fid, fname, conf = iso_map[technique_lower]
        mappings.append(FrameworkMapping(
            framework="iso_27001",
            framework_id=fid,
            framework_name=fname,
            confidence=conf,
            evidence=f"技术关键词 '{technique}' 匹配 ISO 27001 控制项 {fid}",
        ))
    else:
        mappings.append(FrameworkMapping(
            framework="iso_27001",
            framework_id="A.8.26",
            framework_name="Application Security",
            confidence="low",
            evidence=f"技术关键词 '{technique}' 未在本地 ISO 表中匹配",
        ))

    # OWASP ASVS 映射（补充）
    owasp_map = {
        "phishing": ("V1.1", "Authentication Verification", "medium"),
        "ransomware": ("V11.1", "Business Logic Verification", "low"),
        "ddos": ("V11.1", "Business Logic Verification", "low"),
        "sql injection": ("V5.3", "Injection Prevention", "high"),
        "xss": ("V5.1", "XSS Prevention", "high"),
        "privilege escalation": ("V4.1", "Access Control", "high"),
        "lateral movement": ("V4.1", "Access Control", "high"),
        "data exfiltration": ("V11.1", "Business Logic Verification", "medium"),
        "command and control": ("V11.1", "Business Logic Verification", "low"),
        "c2": ("V11.1", "Business Logic Verification", "low"),
        "malware": ("V11.1", "Business Logic Verification", "low"),
        "trojan": ("V11.1", "Business Logic Verification", "low"),
        "worm": ("V11.1", "Business Logic Verification", "low"),
        "zero-day": ("V11.1", "Business Logic Verification", "low"),
        "exploit": ("V11.1", "Business Logic Verification", "low"),
        "backdoor": ("V11.1", "Business Logic Verification", "low"),
        "keylogger": ("V11.1", "Business Logic Verification", "low"),
        "spyware": ("V11.1", "Business Logic Verification", "low"),
        "botnet": ("V11.1", "Business Logic Verification", "low"),
        "social engineering": ("V1.1", "Authentication Verification", "medium"),
        "brute force": ("V1.1", "Authentication Verification", "high"),
        "buffer overflow": ("V5.3", "Injection Prevention", "low"),
    }

    if technique_lower in owasp_map:
        fid, fname, conf = owasp_map[technique_lower]
        mappings.append(FrameworkMapping(
            framework="owasp",
            framework_id=fid,
            framework_name=fname,
            confidence=conf,
            evidence=f"技术关键词 '{technique}' 匹配 OWASP ASVS 条目 {fid}",
        ))
    else:
        mappings.append(FrameworkMapping(
            framework="owasp",
            framework_id="V11.1",
            framework_name="Business Logic Verification",
            confidence="low",
            evidence=f"技术关键词 '{technique}' 未在本地 OWASP 表中匹配",
        ))

    return mappings


def map_entity_to_frameworks(entity: SecurityEntity) -> List[FrameworkMapping]:
    """将单个实体映射到所有支持的框架。"""
    if entity.entity_type == "technique":
        return _map_technique_to_frameworks(entity.value)
    # 对于其他实体类型（IP、域名、URL、哈希），给出基于实体类型的通用映射
    # 置信度设为 low，因为没有具体技术上下文
    mappings = []
    for framework in SUPPORTED_FRAMEWORKS:
        mappings.append(FrameworkMapping(
            framework=framework,
            framework_id=PLACEHOLDER,
            framework_name=f"{entity.entity_type} indicator",
            confidence="low",
            evidence=f"实体 '{entity.value}' 为 {entity.entity_type} 类型，无具体技术上下文，置信度较低",
        ))
    return mappings


# ---------------------------------------------------------------------------
# 批量处理与结果组装（C4）
# ---------------------------------------------------------------------------


def analyze_text(text: str) -> AnalysisResult:
    """分析单条文本，返回完整分析结果。"""
    result = AnalysisResult(text)

    # 提取实体
    result.entities = extract_entities(text)

    # 对每个实体进行框架映射
    for entity in result.entities:
        mappings = map_entity_to_frameworks(entity)
        result.mappings.extend(mappings)

    # 如果没有提取到实体，添加一条说明
    if not result.entities:
        result.notes.append("未从输入中提取到任何安全实体")

    return result


def analyze_batch(inputs: List[str]) -> List[AnalysisResult]:
    """批量分析多条输入。"""
    if not inputs:
        raise ValueError("E008: 批量输入为空")
    return [analyze_text(text) for text in inputs]


# ---------------------------------------------------------------------------
# 输入解析（支持 JSON / CSV / TXT）
# ---------------------------------------------------------------------------


def parse_input(data: str, input_format: str) -> List[str]:
    """
    解析输入数据为文本列表。

    支持格式：
      - json: 数组或对象，对象时取 'text'/'input'/'data' 字段
      - csv: 取第一列作为文本
      - txt: 按行分割
    """
    if not data.strip():
        raise ValueError("E005: 输入数据为空")

    if input_format == "json":
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("E003: JSON 解析失败")

        if isinstance(parsed, list):
            texts = []
            for item in parsed:
                if isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, dict):
                    # 尝试常见字段名
                    for key in ["text", "input", "data", "content", "value"]:
                        if key in item and isinstance(item[key], str):
                            texts.append(item[key])
                            break
                    else:
                        texts.append(json.dumps(item, ensure_ascii=False))
                else:
                    texts.append(str(item))
            return texts
        elif isinstance(parsed, dict):
            # 尝试常见字段名
            for key in ["text", "input", "data", "content", "items", "list"]:
                if key in parsed:
                    val = parsed[key]
                    if isinstance(val, list):
                        return [str(x) if not isinstance(x, dict) else json.dumps(x, ensure_ascii=False) for x in val]
                    elif isinstance(val, str):
                        return [val]
            # 如果没有找到，将整个对象转成字符串
            return [json.dumps(parsed, ensure_ascii=False)]
        else:
            raise ValueError("E003: JSON 顶层必须是数组或对象")

    elif input_format == "csv":
        try:
            reader = csv.reader(io.StringIO(data))
            texts = []
            for row in reader:
                if row and row[0].strip():
                    texts.append(row[0].strip())
            return texts
        except Exception:
            raise ValueError("E003: CSV 解析失败")

    elif input_format == "txt":
        lines = [line.strip() for line in data.splitlines() if line.strip()]
        return lines

    else:
        raise ValueError(f"E003: 不支持的输入格式: {input_format}")


# ---------------------------------------------------------------------------
# 输出序列化（C5）
# ---------------------------------------------------------------------------


def serialize_output(results: List[AnalysisResult], output_format: str, custom_fields: Optional[List[str]] = None) -> str:
    """将分析结果序列化为指定格式。"""
    if output_format == "json":
        return json.dumps(
            {"results": [r.to_dict() for r in results]},
            ensure_ascii=False,
            indent=2,
        )

    elif output_format == "csv":
        # 展平为行
        rows = []
        for r in results:
            for m in r.mappings:
                row = {
                    "input_text": r.input_text,
                    "entity_type": m.framework,  # 简化
                    "value": m.framework_id,
                    "framework": m.framework,
                    "framework_id": m.framework_id,
                    "framework_name": m.framework_name,
                    "confidence": m.confidence,
                    "evidence": m.evidence,
                }
                # 应用自定义字段过滤
                if custom_fields:
                    row = {k: v for k, v in row.items() if k in custom_fields}
                rows.append(row)

        if not rows:
            return ""

        output = io.StringIO()
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    elif output_format == "markdown":
        lines = ["# 安全分析结果", ""]
        for i, r in enumerate(results, 1):
            lines.append(f"## 输入 #{i}")
            lines.append(f"**原始输入**: {r.input_text}")
            lines.append("")
            if r.entities:
                lines.append("### 提取实体")
                lines.append("")
                lines.append("| 类型 | 值 | 上下文 |")
                lines.append("|------|-----|--------|")
                for e in r.entities:
                    lines.append(f"| {e.entity_type} | {e.value} | {e.context} |")
                lines.append("")
            if r.mappings:
                lines.append("### 框架映射")
                lines.append("")
                lines.append("| 框架 | ID | 名称 | 置信度 | 证据 |")
                lines.append("|------|----|------|--------|------|")
                for m in r.mappings:
                    lines.append(f"| {m.framework} | {m.framework_id} | {m.framework_name} | {m.confidence} | {m.evidence} |")
                lines.append("")
            if r.notes:
                lines.append("### 备注")
                lines.append("")
                for note in r.notes:
                    lines.append(f"- {note}")
                lines.append("")
        return "\n".join(lines)

    else:
        raise ValueError(f"E004: 不支持的输出格式: {output_format}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def read_input_file(filepath: str) -> str:
    """读取输入文件内容。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError("E002: 输入文件无法读取")
    except Exception as e:
        raise ValueError(f"E002: 输入文件无法读取: {e}")


def run_selftest() -> bool:
    """运行自测，验证核心功能。"""
    try:
        # 测试实体提取
        text = "检测到来自 192.168.1.100 的钓鱼攻击，使用了恶意软件 ransomware，目标为 example.com"
        result = analyze_text(text)
        assert len(result.entities) > 0, "实体提取失败"
        assert any(e.entity_type == "ip" for e in result.entities), "IP 提取失败"
        assert any(e.entity_type == "technique" for e in result.entities), "技术关键词提取失败"

        # 测试框架映射
        assert len(result.mappings) > 0, "框架映射失败"
        assert all(m.framework in SUPPORTED_FRAMEWORKS for m in result.mappings), "框架名称不合法"
        assert all(m.confidence in CONFIDENCE_LEVELS for m in result.mappings), "置信度不合法"

        # 测试批量处理
        batch = analyze_batch(["测试1", "测试2"])
        assert len(batch) == 2, "批量处理失败"

        # 测试输入解析
        json_input = json.dumps(["测试1", "测试2"])
        parsed = parse_input(json_input, "json")
        assert len(parsed) == 2, "JSON 解析失败"

        # 测试输出序列化
        output = serialize_output(batch, "json")
        assert json.loads(output), "JSON 输出失败"
        output = serialize_output(batch, "csv")
        assert "input_text" in output, "CSV 输出失败"
        output = serialize_output(batch, "markdown")
        assert "# 安全分析结果" in output, "Markdown 输出失败"

        print("自测通过: 所有核心功能正常")
        return True
    except Exception as e:
        print(f"自测失败: {e}")
        return False


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="安全分析·威胁建模·框架映射工具",
        epilog="示例: python main.py --input data.json --output result.json --format json",
    )
    parser.add_argument("--input", "-i", help="输入文件路径（JSON/CSV/TXT）")
    parser.add_argument("--output", "-o", help="输出文件路径（可选，默认输出到 stdout）")
    parser.add_argument("--format", "-f", choices=OUTPUT_FORMATS, default="json", help="输出格式")
    parser.add_argument("--input-format", choices=["json", "csv", "txt"], help="输入格式（默认根据扩展名推断）")
    parser.add_argument("--fields", nargs="*", help="自定义输出字段（CSV 格式）")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    parser.add_argument("--version", action="version", version="1.0.0")

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 需要输入文件
    if not args.input:
        parser.error("E001: 缺少 --input 参数")
        return 1

    try:
        # 读取输入
        data = read_input_file(args.input)

        # 推断输入格式
        input_format = args.input_format
        if not input_format:
            if args.input.endswith(".json"):
                input_format = "json"
            elif args.input.endswith(".csv"):
                input_format = "csv"
            elif args.input.endswith(".txt"):
                input_format = "txt"
            else:
                input_format = "txt"

        # 解析输入
        texts = parse_input(data, input_format)

        # 批量分析
        results = analyze_batch(texts)

        # 序列化输出
        output = serialize_output(results, args.format, args.fields)

        # 输出
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010 运行时异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
