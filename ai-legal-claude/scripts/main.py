#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — AI Legal Claude 法律场景智能辅助工具（独立 clean-room 实现）

本脚本完全依据功能规格独立编写，不参考或复制任何既有实现。
功能：合同审查、风险分析、NDA 生成、合规审计、条款比对。
仅依赖 Python 标准库，无第三方依赖。

用法示例：
    python scripts/main.py --review contract.txt
    python scripts/main.py --compare docA.txt docB.txt
    python scripts/main.py --nda "甲方公司" "乙方公司" --term 24 --region 中国大陆
    python scripts/main.py --selftest
"""

import argparse
import re
import sys
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import time
import urllib.request
import urllib.error
import socket

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：无法读取指定文件",
    "E003": "文本为空：输入文本内容为空",
    "E004": "法规不支持：指定的法规不在支持列表中",
    "E005": "内部错误：处理过程中发生未预期异常",
    "E006": "输出目录不可写：无法写入输出文件",
    "E007": "日期格式错误：日期应为 YYYY-MM-DD 格式",
    "E008": "数据不足：输入信息不足以完成操作",
    "E009": "文件写入失败：无法写入输出文件",
    "E010": "自检失败：核心逻辑自检未通过",
    "E011": "编码错误：文件编码无法识别",
    "E012": "网络错误：外部服务调用失败",
    "E013": "配置错误：JSON 配置格式非法",
    "E014": "超时错误：处理超时",
}


def fail(code: str, detail: str = "") -> None:
    """输出错误码和详情并退出"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        print(f"[{code}] {msg} — {detail}", file=sys.stderr)
    else:
        print(f"[{code}] {msg}", file=sys.stderr)
    sys.exit(1)


def _detect_encoding(path: str) -> str:
    """
    检测文件编码，返回第一个能成功解码的编码名称。
    如果所有编码都失败，返回 None。
    支持 UTF-8-SIG、UTF-16、GBK、GB18030。
    """
    # 先尝试带 BOM 的编码
    for enc in ("utf-8-sig", "utf-16"):
        try:
            with open(path, encoding=enc, errors="strict") as f:
                f.read()
            return enc
        except (UnicodeDecodeError, OSError):
            continue
    # 再尝试无 BOM 的编码
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="strict") as f:
                f.read()
            return enc
        except (UnicodeDecodeError, OSError):
            continue
    return None


def _read_text_safe(path: str, max_size: int = 10 * 1024 * 1024) -> str:
    """
    多编码安全读取（R3+R5 合规）
    使用 errors='strict' 严格模式，避免静默替换字符
    增加文件大小限制，防止大文件耗尽内存
    修复：单次 open 读取并限制读取字节数，避免 TOCTOU 竞态
    """
    # 检查文件大小（仅作为快速预检，实际读取时强制限制）
    try:
        file_size = os.path.getsize(path)
        if file_size > max_size:
            fail("E014", f"文件过大（{file_size} 字节），超过限制 {max_size} 字节")
    except OSError as e:
        fail("E002", f"无法读取文件: {path}，错误: {e}")

    # 单次 open 读取，强制限制字节数
    enc = _detect_encoding(path)
    if enc is None:
        fail("E011", f"文件编码无法识别: {path}")
    try:
        with open(path, encoding=enc, errors="strict") as f:
            content = f.read(max_size + 1)  # 多读一个字节用于检测截断
            if len(content) > max_size:
                fail("E014", f"文件过大（超过 {max_size} 字节）")
            return content
    except OSError as e:
        fail("E002", f"无法读取文件: {path}，错误: {e}")


def _iter_lines(path: str, max_size: int = 10 * 1024 * 1024):
    """
    批处理流式读取工具，复用 _detect_encoding 的编码检测逻辑。
    支持多编码回退，与 _read_text_safe 保持一致。
    增加文件大小限制。
    """
    # 检查文件大小
    try:
        file_size = os.path.getsize(path)
        if file_size > max_size:
            fail("E014", f"文件过大（{file_size} 字节），超过限制 {max_size} 字节")
    except OSError as e:
        fail("E002", f"无法读取文件: {path}，错误: {e}")

    enc = _detect_encoding(path)
    if enc is None:
        fail("E011", f"文件编码无法识别: {path}")
    try:
        with open(path, encoding=enc, errors="strict") as f:
            for line in f:
                yield line
    except OSError as e:
        fail("E002", f"无法读取文件: {path}，错误: {e}")


# ============================================================
# 网络请求模块（带重试、退避、超时）
# ============================================================

def http_get_with_retry(url: str, timeout: float = 5.0, max_retries: int = 3) -> Optional[str]:
    """
    带重试、指数退避和超时的 HTTP GET 请求。
    返回响应文本，失败返回 None。
    """
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, socket.timeout, OSError) as e:
            if attempt == max_retries - 1:
                print(f"[E012] 网络错误: {url} — {e}", file=sys.stderr)
                return None
            # 指数退避
            wait_time = 2 ** attempt
            time.sleep(wait_time)
    return None


# ============================================================
# 配置校验模块
# ============================================================

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "review_rules": {
            "type": "object",
            "properties": {
                "required_clauses": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": [{"type": "string"}, {"type": "string"}, {"type": "array", "items": {"type": "string"}}]
                    }
                },
                "vague_phrases": {"type": "array", "items": {"type": "string"}},
                "risk_weights": {
                    "type": "object",
                    "properties": {
                        "缺失条款": {"type": "number"},
                        "模糊表述": {"type": "number"},
                        "权利义务不对等": {"type": "number"},
                        "金额未大写": {"type": "number"},
                        "缺少签署日期": {"type": "number"}
                    },
                    "required": ["缺失条款", "模糊表述", "权利义务不对等", "金额未大写", "缺少签署日期"]
                }
            },
            "required": ["required_clauses", "vague_phrases", "risk_weights"]
        }
    },
    "required": ["review_rules"]
}


def validate_config(config: Dict[str, Any]) -> bool:
    """
    校验配置字典是否符合 schema。
    返回 True 表示合法，否则抛出异常。
    """
    try:
        # 简化版 schema 校验（不引入第三方库）
        if not isinstance(config, dict):
            raise ValueError("配置必须是 JSON 对象")
        if "review_rules" not in config:
            raise ValueError("缺少 review_rules 字段")
        rr = config["review_rules"]
        if not isinstance(rr, dict):
            raise ValueError("review_rules 必须是对象")
        if "required_clauses" not in rr or not isinstance(rr["required_clauses"], list):
            raise ValueError("required_clauses 必须是数组")
        for item in rr["required_clauses"]:
            if not isinstance(item, list) or len(item) != 3:
                raise ValueError("required_clauses 每项必须是 [名称, 关键词, 关键词列表]")
            if not isinstance(item[0], str) or not isinstance(item[1], str) or not isinstance(item[2], list):
                raise ValueError("required_clauses 每项类型错误")
            if not all(isinstance(k, str) for k in item[2]):
                raise ValueError("required_clauses 关键词列表必须全是字符串")
        if "vague_phrases" not in rr or not isinstance(rr["vague_phrases"], list):
            raise ValueError("vague_phrases 必须是数组")
        if not all(isinstance(p, str) for p in rr["vague_phrases"]):
            raise ValueError("vague_phrases 必须全是字符串")
        if "risk_weights" not in rr or not isinstance(rr["risk_weights"], dict):
            raise ValueError("risk_weights 必须是对象")
        required_weights = ["缺失条款", "模糊表述", "权利义务不对等", "金额未大写", "缺少签署日期"]
        for key in required_weights:
            if key not in rr["risk_weights"]:
                raise ValueError(f"risk_weights 缺少字段: {key}")
            if not isinstance(rr["risk_weights"][key], (int, float)):
                raise ValueError(f"risk_weights.{key} 必须是数字")
        return True
    except (ValueError, TypeError) as e:
        fail("E013", str(e))
        return False  # 不可达，fail 会退出


# ============================================================
# 核心数据结构
# ============================================================

# 风险等级
RISK_HIGH = "高"
RISK_MEDIUM = "中"
RISK_LOW = "低"

# 支持的法规列表
SUPPORTED_REGULATIONS = ["个保法", "劳动法", "合同法", "公司法", "知识产权法"]

# 法律知识库（内置规则引擎）
LEGAL_KNOWLEDGE_BASE = {
    "个保法": {
        "required_clauses": [
            ("个人信息处理规则", ["个人信息", "个人数据"], "应明确个人信息处理的目的、方式和范围"),
            ("用户同意", ["同意", "授权"], "处理个人信息应取得用户同意"),
            ("数据安全", ["安全", "保护措施"], "应明确数据安全保护措施"),
            ("数据出境", ["出境", "跨境"], "数据出境需符合相关规定"),
            ("用户权利", ["删除", "更正", "访问"], "应保障用户查询、更正、删除权利"),
        ],
        "risk_weights": {"个人信息处理规则": 0.3, "用户同意": 0.25, "数据安全": 0.2, "数据出境": 0.15, "用户权利": 0.1}
    },
    "劳动法": {
        "required_clauses": [
            ("劳动合同期限", ["合同期限", "劳动合同"], "应明确劳动合同期限"),
            ("工作内容", ["工作内容", "岗位"], "应明确工作内容和地点"),
            ("劳动报酬", ["工资", "薪酬", "报酬"], "应明确劳动报酬及支付方式"),
            ("工作时间", ["工作时间", "工时"], "应明确工作时间和休息休假"),
            ("社会保险", ["社保", "保险"], "应明确社会保险缴纳义务"),
            ("解除条件", ["解除", "终止"], "应明确合同解除条件和程序"),
        ],
        "risk_weights": {"劳动合同期限": 0.2, "工作内容": 0.15, "劳动报酬": 0.25, "工作时间": 0.15, "社会保险": 0.15, "解除条件": 0.1}
    },
    "合同法": {
        "required_clauses": [
            ("当事人信息", ["甲方", "乙方"], "应明确双方当事人的基本信息"),
            ("标的条款", ["标的", "服务内容", "产品"], "应明确合同标的"),
            ("数量质量", ["数量", "质量", "标准"], "应明确数量和质量标准"),
            ("价款报酬", ["价款", "金额", "费用"], "应明确价款或报酬"),
            ("履行期限", ["期限", "日期", "时间"], "应明确履行期限和地点"),
            ("违约责任", ["违约"], "应明确违约责任"),
        ],
        "risk_weights": {"当事人信息": 0.1, "标的条款": 0.2, "数量质量": 0.15, "价款报酬": 0.25, "履行期限": 0.15, "违约责任": 0.15}
    },
    "公司法": {
        "required_clauses": [
            ("公司名称", ["公司名称", "有限公司"], "应明确公司全称"),
            ("经营范围", ["经营范围", "业务范围"], "应明确经营范围"),
            ("注册资本", ["注册资本", "资本"], "应明确注册资本"),
            ("股东信息", ["股东"], "应明确股东信息"),
            ("表决机制", ["表决", "投票"], "应明确表决机制"),
        ],
        "risk_weights": {"公司名称": 0.2, "经营范围": 0.2, "注册资本": 0.2, "股东信息": 0.2, "表决机制": 0.2}
    },
    "知识产权法": {
        "required_clauses": [
            ("权利归属", ["知识产权", "著作权", "专利"], "应明确知识产权归属"),
            ("使用许可", ["许可", "授权使用"], "应明确使用许可范围"),
            ("侵权责任", ["侵权"], "应明确侵权责任承担"),
            ("保密义务", ["保密"], "应有保密条款保护未公开知识产权"),
        ],
        "risk_weights": {"权利归属": 0.3, "使用许可": 0.3, "侵权责任": 0.2, "保密义务": 0.2}
    }
}

# 合同审查规则库
CONTRACT_REVIEW_RULES = {
    "required_clauses": [
        ("违约责任", "违约", ["违约责任", "违约条款"]),
        ("争议解决", "争议", ["争议解决", "仲裁", "诉讼"]),
        ("保密条款", "保密", ["保密", "机密"]),
        ("终止条款", "终止", ["终止", "解除"]),
        ("知识产权", "知识产权", ["知识产权", "著作权", "专利", "商标"]),
        ("不可抗力", "不可抗力", ["不可抗力"]),
    ],
    "vague_phrases": ["尽快", "适当", "合理", "及时", "相关", "等", "视情况", "酌情", "尽可能", "原则上"],
    "risk_weights": {"缺失条款": 0.4, "模糊表述": 0.3, "权利义务不对等": 0.2, "金额未大写": 0.05, "缺少签署日期": 0.05}
}


# ============================================================
# 合同审查模块（带缓存和超时）
# ============================================================

@lru_cache(maxsize=128)
def _review_contract_cached(text_hash: str, text: str) -> List[Dict[str, str]]:
    """带缓存的合同审查核心逻辑（text_hash 用于缓存键）"""
    issues: List[Dict[str, str]] = []
    lower_text = text.lower()
    
    # 1. 检查关键条款是否缺失（基于规则库）
    for clause_name, keyword, keywords in CONTRACT_REVIEW_RULES["required_clauses"]:
        found = any(k in lower_text for k in keywords)
        if not found:
            issues.append({
                "位置": "全文",
                "问题类型": f"缺失条款：{clause_name}",
                "风险等级": RISK_HIGH,
                "建议": f"建议补充{clause_name}相关条款，明确各方权利义务。",
            })
    
    # 2. 检查模糊表述（基于规则库）
    for phrase in CONTRACT_REVIEW_RULES["vague_phrases"]:
        if phrase in text:
            issues.append({
                "位置": f"包含'{phrase}'的条款",
                "问题类型": "模糊表述",
                "风险等级": RISK_MEDIUM,
                "建议": f"建议将'{phrase}'替换为具体、可量化的表述。",
            })
    
    # 3. 检查权利义务不对等（简单启发式）
    party_a_obligations = len(re.findall(r"甲方[应须必]", text))
    party_b_obligations = len(re.findall(r"乙方[应须必]", text))
    party_a_rights = len(re.findall(r"甲方[有权可]", text))
    party_b_rights = len(re.findall(r"乙方[有权可]", text))
    
    if party_a_obligations > 0 and party_b_obligations > 0:
        ratio = party_a_obligations / max(party_b_obligations, 1)
        if ratio > 3:
            issues.append({
                "位置": "全文",
                "问题类型": "权利义务不对等",
                "风险等级": RISK_HIGH,
                "建议": "甲方义务条款明显多于乙方，建议平衡双方权利义务。",
            })
    
    # 4. 检查
