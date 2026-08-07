#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同智审 · 法律风险 · 条款比对 (ai-legal-claude)
=================================================
独立实现脚本，仅依据功能规格设计，不参考任何既有实现。

功能模块：
  1. 合同文本结构化解析（parse_contract）
  2. 关键风险点识别（identify_risks）
  3. NDA/保密协议生成（generate_nda）
  4. 合规缺口审计（compliance_audit）
  5. 条款比对与差异标注（compare_clauses）

命令行支持：
  python main.py --selftest    # 离线自检核心逻辑

错误码约定：
  E001 参数错误
  E002 文件读取失败
  E003 输入文本为空
  E004 解析失败
  E005 风险识别失败
  E006 文书生成失败
  E007 合规审计失败
  E008 条款比对失败
  E009 内部逻辑错误
  E010 未知错误

免责声明：
  本脚本输出仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。
  涉及专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 风险关键词库（严重度分级）
HIGH_RISK_KEYWORDS = [
    "违约金", "赔偿", "连带责任", "无限责任", "单方解除",
    "仲裁", "诉讼", "保密义务", "知识产权归属", "竞业限制",
]

MEDIUM_RISK_KEYWORDS = [
    "付款条件", "交付期限", "验收标准", "质保期", "维保",
    "不可抗力", "争议解决", "管辖", "通知", "变更",
]

LOW_RISK_KEYWORDS = [
    "附件", "补充协议", "签署日期", "生效条件", "份数",
    "语言", "传真", "电子邮件", "邮寄",
]

# 合规法规关键词库
REGULATORY_KEYWORDS = {
    "数据安全": ["数据", "个人信息", "隐私", "网络安全"],
    "劳动法": ["工资", "工时", "社保", "劳动合同"],
    "税法": ["发票", "税务", "税收", "代扣"],
    "消费者保护": ["消费者", "退款", "售后", "三包"],
    "反垄断": ["垄断", "不正当竞争", "排他"],
}

# 条款类型识别规则
CLAUSE_PATTERNS = {
    "定义": r"定义|解释",
    "保密": r"保密|confidential",
    "付款": r"付款|支付|费用",
    "交付": r"交付|交货|提供",
    "验收": r"验收|检验|测试",
    "违约": r"违约|责任|赔偿",
    "终止": r"终止|解除|期满",
    "争议": r"争议|仲裁|诉讼|管辖",
    "知识产权": r"知识产权|专利|商标|著作权|版权",
    "其他": r"其他|附则|一般",
}


# ============================================================
# 基础工具函数
# ============================================================

def _generate_id(text: str) -> str:
    """生成文本的短哈希标识符。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def _normalize_text(text: str) -> str:
    """规范化文本：去除多余空白、统一换行。"""
    if not text:
        return ""
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去除多余空白行
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _split_clauses(text: str) -> List[str]:
    """将合同文本按条款编号切分。"""
    if not text:
        return []
    # 匹配常见条款编号格式：第X条、X.、X.X、 (X)
    pattern = r"(?m)^\s*(?:第\s*[一二三四五六七八九十百千万0-9]+\s*条|[0-9]+(?:\.[0-9]+)*\s*[、.．]|[（(][0-9]+[）)])\s*"
    parts = re.split(pattern, text)
    # 过滤空字符串和纯标点
    clauses = []
    for part in parts:
        part = part.strip()
        if part and len(part) > 2:
            clauses.append(part)
    return clauses


def _extract_dates(text: str) -> List[str]:
    """提取文本中的日期。"""
    date_patterns = [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        r"\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}",
        r"[一二三四五六七八九十]+月[一二三四五六七八九十]+日",
    ]
    dates = []
    for pattern in date_patterns:
        dates.extend(re.findall(pattern, text))
    return list(set(dates))


# ============================================================
# 模块 1：合同文本结构化解析
# ============================================================

def parse_contract(text: str) -> Dict[str, Any]:
    """
    将合同全文解析为结构化条款清单。
    
    输入: 合同全文文本
    输出: 结构化字典，包含元信息、条款列表
    """
    if not text or not text.strip():
        raise ValueError("E003: 输入文本为空")
    
    try:
        normalized = _normalize_text(text)
        clauses = _split_clauses(normalized)
        
        if not clauses:
            # 无法切分时，将全文作为一个条款
            clauses = [normalized]
        
        parsed_clauses = []
        for idx, clause_text in enumerate(clauses, 1):
            # 识别条款类型
            clause_type = "通用"
            for ctype, pattern in CLAUSE_PATTERNS.items():
                if re.search(pattern, clause_text, re.IGNORECASE):
                    clause_type = ctype
                    break
            
            # 提取日期
            dates = _extract_dates(clause_text)
            
            parsed_clauses.append({
                "序号": idx,
                "类型": clause_type,
                "内容": clause_text[:200],  # 截断保存
                "全文": clause_text,
                "提及日期": dates,
                "字数": len(clause_text),
            })
        
        # 统计条款类型分布
        type_counter = Counter(c["类型"] for c in parsed_clauses)
        
        return {
            "解析状态": "成功",
            "文本哈希": _generate_id(normalized),
            "条款总数": len(parsed_clauses),
            "条款类型分布": dict(type_counter),
            "条款列表": parsed_clauses,
            "原始字数": len(normalized),
        }
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"E004: 解析失败 - {str(e)}")


# ============================================================
# 模块 2：关键风险点识别
# ============================================================

def identify_risks(contract_text: str, risk_preference: str = "balanced") -> Dict[str, Any]:
    """
    识别合同中的关键风险点，按严重度分级。
    
    输入: 合同全文，可选风险偏好（conservative/balanced/aggressive）
    输出: 风险清单（按严重度分级）
    """
    if not contract_text or not contract_text.strip():
        raise ValueError("E003: 输入文本为空")
    
    try:
        normalized = _normalize_text(contract_text)
        risks = []
        
        # 按风险等级扫描关键词
        risk_weights = {
            "high": 3,
            "medium": 2,
            "low": 1,
        }
        
        # 根据偏好调整权重
        if risk_preference == "conservative":
            risk_weights = {"high": 5, "medium": 3, "low": 2}
        elif risk_preference == "aggressive":
            risk_weights = {"high": 2, "medium": 1, "low": 1}
        
        all_keywords = [
            ("high", HIGH_RISK_KEYWORDS),
            ("medium", MEDIUM_RISK_KEYWORDS),
            ("low", LOW_RISK_KEYWORDS),
        ]
        
        for level, keywords in all_keywords:
            for keyword in keywords:
                count = normalized.count(keyword)
                if count > 0:
                    # 提取上下文
                    positions = [m.start() for m in re.finditer(re.escape(keyword), normalized)]
                    context = []
                    for pos in positions[:3]:  # 最多取前3处上下文
                        start = max(0, pos - 30)
                        end = min(len(normalized), pos + len(keyword) + 30)
                        context.append(normalized[start:end].replace("\n", " "))
                    
                    score = count * risk_weights[level]
                    risks.append({
                        "关键词": keyword,
                        "严重度": level,
                        "出现次数": count,
                        "风险评分": score,
                        "上下文": context,
                    })
        
        # 按评分排序
        risks.sort(key=lambda x: x["风险评分"], reverse=True)
        
        # 汇总统计
        high_count = sum(1 for r in risks if r["严重度"] == "high")
        medium_count = sum(1 for r in risks if r["严重度"] == "medium")
        low_count = sum(1 for r in risks if r["严重度"] == "low")
        
        # 总体风险等级
        total_score = sum(r["风险评分"] for r in risks)
        if total_score > 30:
            overall = "高风险"
        elif total_score > 15:
            overall = "中风险"
        else:
            overall = "低风险"
        
        return {
            "风险等级": overall,
            "风险总数": len(risks),
            "统计": {
                "高风险项": high_count,
                "中风险项": medium_count,
                "低风险项": low_count,
                "总评分": total_score,
            },
            "风险清单": risks,
        }
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"E005: 风险识别失败 - {str(e)}")


# ============================================================
# 模块 3：NDA/保密协议生成
# ============================================================

def generate_nda(
    party_a: str,
    party_b: str,
    confidentiality_period: int = 2,
    purpose: str = "商业合作",
) -> Dict[str, Any]:
    """
    生成保密协议（NDA）文本。
    
    输入: 双方主体信息、保密期限（年）、保密目的
    输出: 可编辑的 NDA 文本
    """
    if not party_a or not party_b:
        raise ValueError("E001: 双方主体信息不能为空")
    if confidentiality_period <= 0:
        raise ValueError("E001: 保密期限必须为正数")
    
    try:
        today = datetime.now()
        expiry = today + timedelta(days=confidentiality_period * 365)
        
        # 使用中文数字表示保密期限
        period_cn = {
            1: "一", 2: "两", 3: "三", 4: "四", 5: "五",
            6: "六", 7: "七", 8: "八", 9: "九", 10: "十"
        }
        period_text = period_cn.get(confidentiality_period, str(confidentiality_period))
        
        nda_text = f"""
保密协议（NDA）

本保密协议（以下简称"本协议"）由以下双方于 {today.strftime("%Y年%m月%d日")} 签订：

甲方：{party_a}
乙方：{party_b}

鉴于双方拟就 {purpose} 事宜进行合作，为保护双方商业秘密，经友好协商，达成如下协议：

第一条 定义
1.1 "保密信息"指一方（披露方）向另一方（接收方）披露的、与双方合作相关的全部技术、商业、财务信息，无论以何种形式或介质承载。

第二条 保密义务
2.1 接收方应对保密信息承担保密义务，未经披露方书面同意，不得向任何第三方披露。
2.2 接收方仅可在为履行合作目的所必需的范围内使用保密信息。

第三条 保密期限
3.1 本协议项下的保密义务自本协议签署之日起 {period_text}年内有效，即至 {expiry.strftime("%Y年%m月%d日")} 止。
3.2 保密期限届满后，接收方仍应对保密信息承担永久保密义务，但已进入公有领域的信息除外。

第四条 例外情形
4.1 以下信息不属于保密信息：
(a) 接收方在接收时已合法持有的信息；
(b) 非因接收方过错而进入公有领域的信息；
(c) 接收方从有权披露的第三方合法获取的信息；
(d) 接收方独立开发且未使用保密信息获得的信息。

第五条 违约责任
5.1 如接收方违反本协议约定，应向披露方赔偿由此造成的全部损失。

第六条 争议解决
6.1 因本协议引起的争议，双方应友好协商解决；协商不成的，任何一方均可向有管辖权的人民法院提起诉讼。

第七条 其他
7.1 本协议一式两份，甲乙双方各执一份，具有同等法律效力。
7.2 本协议自双方签字盖章之日起生效。

甲方（盖章）：____________    乙方（盖章）：____________
授权代表：____________        授权代表：____________
日期：____________            日期：____________
"""
        return {
            "协议类型": "NDA",
            "甲方": party_a,
            "乙方": party_b,
            "保密期限(年)": confidentiality_period,
            "生效日期": today.strftime("%Y-%m-%d"),
            "到期日期": expiry.strftime("%Y-%m-%d"),
            "协议全文": nda_text.strip(),
            "字数": len(nda_text),
        }
    except Exception as e:
        raise RuntimeError(f"E006: 文书生成失败 - {str(e)}")


# ============================================================
# 模块 4：合规缺口审计
# ============================================================

def compliance_audit(contract_text: str, applicable_regulations: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    审计合同文本的合规缺口。
    
    输入: 合同全文，可选适用法规清单
    输出: 合规差距报告
    """
    if not contract_text or not contract_text.strip():
        raise ValueError("E003: 输入文本为空")
    
    try:
        normalized = _normalize_text(contract_text)
        
        # 默认检查全部法规领域
        if applicable_regulations is None:
            applicable_regulations = list(REGULATORY_KEYWORDS.keys())
        
        audit_results = []
        total_gaps = 0
        
        for regulation in applicable_regulations:
            if regulation not in REGULATORY_KEYWORDS:
                continue
            
            keywords = REGULATORY_KEYWORDS[regulation]
            found_keywords = []
            missing_keywords = []
            
            for kw in keywords:
                if kw in normalized:
                    found_keywords.append(kw)
                else:
                    missing_keywords.append(kw)
            
            # 合规判断：找到至少一个关键词视为部分合规
            if len(found_keywords) >= 2:
                status = "合规"
                gap_count = 0
            elif len(found_keywords) == 1:
                status = "部分合规"
                gap_count = 1
            else:
                status = "不合规"
                gap_count = len(keywords)
            
            total_gaps += gap_count
            
            audit_results.append({
                "法规领域": regulation,
                "状态": status,
                "已覆盖关键词": found_keywords,
                "缺失关键词": missing_keywords,
                "缺口数": gap_count,
            })
        
        # 总体合规评分
        total_keywords = sum(len(REGULATORY_KEYWORDS[r]) for r in applicable_regulations if r in REGULATORY_KEYWORDS)
        coverage = 0
        if total_keywords > 0:
            covered = sum(len(r["已覆盖关键词"]) for r in audit_results)
            coverage = covered / total_keywords
        
        if coverage >= 0.7:
            overall = "良好"
        elif coverage >= 0.4:
            overall = "中等"
        else:
            overall = "较差"
        
        return {
            "总体合规评级": overall,
            "法规覆盖率": round(coverage * 100, 1),
            "总缺口数": total_gaps,
            "审计明细": audit_results,
        }
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"E007: 合规审计失败 - {str(e)}")


# ============================================================
# 模块 5：条款比对与差异标注
# ============================================================

def compare_clauses(contract_a: str, contract_b: str) -> Dict[str, Any]:
    """
    比对两份合同的条款差异。
    
    输入: 两份合同文本
    输出: 逐条差异对照表
    """
    if not contract_a or not contract_a.strip() or not contract_b or not contract_b.strip():
        raise ValueError("E003: 输入文本不能为空")
    
    try:
        # 解析两份合同
        parsed_a = parse_contract(contract_a)
        parsed_b = parse_contract(contract_b)
        
        clauses_a = parsed_a["条款列表"]
        clauses_b = parsed_b["条款列表"]
        
        # 按类型分组比对
        type_a = {}
        type_b = {}
        for c in clauses_a:
            type_a.setdefault(c["类型"], []).append(c)
        for c in clauses_b:
            type_b.setdefault(c["类型"], []).append(c)
        
        all_types = set(list(type_a.keys()) + list(type_b.keys()))
        
        diff_table = []
        for ctype in sorted(all_types):
            list_a = type_a.get(ctype, [])
            list_b = type_b.get(ctype, [])
            
            max_len = max(len(list_a), len(list_b))
            for i in range(max_len):
                clause_a = list_a[i] if i < len(list_a) else None
                clause_b = list_b[i] if i < len(list_b) else None
                
                if clause_a is None:
                    status = "仅乙方有"
                    diff = "乙方新增条款"
                elif clause_b is None:
                    status = "仅甲方有"
                    diff = "甲方独有条款"
                else:
                    # 比较内容相似度
                    text_a = clause_a["全文"]
                    text_b = clause_b["全文"]
                    
                    # 简单相似度：字符重合率
                    set_a = set(text_a)
                    set_b = set(text_b)
                    if len(set_a | set_b) > 0:
                        similarity = len(set_a & set_b) / len(set_a | set_b)
                    else:
                        similarity = 0
                    
                    if similarity > 0.8:
                        status = "基本一致"
                        diff = "内容高度相似"
                    elif similarity > 0.5:
                        status = "部分差异"
                        diff = f"相似度 {similarity:.0%}，存在措辞或内容修改"
                    else:
                        status = "明显不同"
                        diff = f"相似度 {similarity:.0%}，条款内容差异显著"
                
                diff_table.append({
                    "条款类型": ctype,
                    "序号": i + 1,
                    "状态": status,
                    "差异说明": diff,
                    "甲方内容摘要": (clause_a["内容"][:100] + "...") if clause_a else "（无）",
                    "乙方内容摘要": (clause_b["内容"][:100] + "...") if clause_b else "（无）",
                })
        
        # 统计
        status_counter = Counter(d["状态"] for d in diff_table)
        
        return {
            "比对结果": "完成",
            "甲方条款数": len(clauses_a),
            "乙方条款数": len(clauses_b),
            "差异总数": len(diff_table),
            "差异统计": dict(status_counter),
            "差异明细": diff_table,
        }
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"E008: 条款比对失败 - {str(e)}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。
    不读外部文件、不依赖当前工作目录、不访问网络。
    
    返回: True 表示全部通过
    """
    print("=" * 60)
    print("开始自检（ai-legal-claude 核心逻辑）")
    print("=" * 60)
    
    # 硬编码测试数据
    SAMPLE_CONTRACT_A = """
    技术服务合同
    
    第一条 定义
    本合同所述"技术资料"指甲方提供的全部技术文档。
    
    第二条 服务内容
    乙方应根据甲方要求提供软件开发服务，交付期限为合同签订后90日。
    
    第三条 付款条件
    甲方应在验收合格后30日内支付合同总价的90%，剩余10%作为质保金。
    
    第四条 保密义务
    双方应对合作期间获知的商业秘密承担保密义务，保密期限为3年。
    
    第五条 违约责任
    任何一方违约，应向守约方支付合同总价20%的违约金。如造成损失的，还应承担赔偿责任。
    
    第六条 知识产权
    乙方开发的软件知识产权归甲方所有。
    
    第七条 争议解决
    因本合同引起的争议，双方协商解决；协商不成的，提交北京仲裁委员会仲裁。
    
    第八条 其他
    本合同一式两份，双方各执一份。
    """
    
    SAMPLE_CONTRACT_B = """
    软件采购合同
    
    第一条 定义
    本合同所述"软件产品"指乙方提供的标准软件。
    
    第二条 交付与验收
    乙方应在合同签订后60日内交付软件，甲方应在收到软件后15日内完成验收。
    
    第三条 付款方式
    甲方应在合同签订后预付30%货款，验收合格后支付60%，质保期满后支付10%。
    
    第四条 保密条款
    双方应对合作中知悉的商业秘密予以保密，保密期限为2年。
    
    第五条 违约责任
    违约方应赔偿守约方直接经济损失，赔偿总额不超过合同总价。
    
    第六条 知识产权
    软件产品的知识产权归乙方所有，甲方仅获得使用权。
    
    第七条 争议解决
    因本合同发生的争议，由合同签订地人民法院管辖。
    """
    
    SAMPLE_RISK_TEXT = """
    本协议约定违约金为合同金额的50%，乙方承担无限连带责任。
    如发生争议，双方同意提交仲裁。甲方对技术资料承担保密义务。
    付款条件为验收合格后一次性付清。
    """
    
    results = []
    
    # ---- 测试 1: parse_contract ----
    print("\n[测试 1] 合同结构化解析")
    try:
        parsed = parse_contract(SAMPLE_CONTRACT_A)
        assert parsed["解析状态"] == "成功"
        assert parsed["条款总数"] >= 5, f"条款数应>=5，实际{parsed['条款总数']}"
        assert parsed["条款类型分布"].get("保密", 0) >= 1
        assert parsed["条款类型分布"].get("争议", 0) >= 1
        assert parsed["条款类型分布"].get("知识产权", 0) >= 1
        results.append(("parse_contract", True, f"解析出 {parsed['条款总数']} 个条款"))
    except Exception as e:
        results.append(("parse_contract", False, str(e)))
    
    # ---- 测试 2: identify_risks ----
    print("\n[测试 2] 风险识别")
    try:
        risks = identify_risks(SAMPLE_RISK_TEXT)
        assert risks["风险总数"] >= 3, f"风险数应>=3，实际{risks['风险总数']}"
        # 高风险项应存在（违约金、连带责任）
        high_items = risks["统计"]["高风险项"]
        assert high_items >= 2, f"高风险项应>=2，实际{high_items}"
        # 风险清单非空
        assert len(risks["风险清单"]) >= 3
        results.append(("identify_risks", True, f"识别 {risks['风险总数']} 项风险"))
    except Exception as e:
        results.append(("identify_risks", False, str(e)))
    
    # ---- 测试 3: generate_nda ----
    print("\n[测试 3] NDA 生成")
    try:
        nda = generate_nda("测试科技有限公司", "测试信息有限公司", 2, "项目合作")
        assert "保密协议" in nda["协议全文"]
        assert "测试科技有限公司" in nda["协议全文"]
        assert "测试信息有限公司" in nda["协议全文"]
        assert "两年" in nda["协议全文"] or "2年" in nda["协议全文"]
        assert nda["字数"] > 500, f"NDA 字数应>500，实际{nda['字数']}"
        results.append(("generate_nda", True, f"生成 {nda['字数']} 字 NDA"))
    except Exception as e:
        results.append(("generate_nda", False, str(e)))
    
    # ---- 测试 4: compliance_audit ----
    print("\n[测试 4] 合规审计")
    try:
        audit = compliance_audit(SAMPLE_CONTRACT_A, ["数据安全", "劳动法", "税法"])
        assert audit["审计明细"] is not None
        assert len(audit["审计明细"]) == 3
        # 覆盖率应在 0-100 之间
        assert 0 <= audit["法规覆盖率"] <= 100
        results.append(("compliance_audit", True, f"覆盖率 {audit['法规覆盖率']}%"))
    except Exception as e:
        results.append(("compliance_audit", False, str(e)))
    
    # ---- 测试 5: compare_clauses ----
    print("\n[测试 5] 条款比对")
    try:
        compared = compare_clauses(SAMPLE_CONTRACT_A, SAMPLE_CONTRACT_B)
        assert compared["差异总数"] >= 5, f"差异数应>=5，实际{compared['差异总数']}"
        # 应有明显不同的条款（知识产权归属不同）
        statuses = set(d["状态"] for d in compared["差异明细"])
        assert "明显不同" in statuses or "部分差异" in statuses
        results.append(("compare_clauses", True, f"比对 {compared['差异总数']} 项差异"))
    except Exception as e:
        results.append(("compare_clauses", False, str(e)))
    
    # ---- 测试 6: 错误处理 ----
    print("\n[测试 6] 错误处理")
    try:
        # 空文本应抛出 E003
        try:
            parse_contract("")
            results.append(("error_handling", False, "空文本未抛出异常"))
        except ValueError as e:
            assert "E003" in str(e)
            results.append(("error_handling", True, "空文本正确抛出 E003"))
    except Exception as e:
        results.append(("error_handling", False, str(e)))
    
    # ---- 输出结果 ----
    print("\n" + "=" * 60)
    print("自检结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed, detail in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} | {name}: {detail}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 全部自检通过！")
    else:
        print("⚠️  存在失败项，请检查实现。")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="合同智审 · 法律风险 · 条款比对工具",
        epilog="免责声明：本工具输出仅供一般信息参考，不构成法律建议。",
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部文件）",
    )
    
    parser.add_argument(
        "--parse",
        metavar="FILE",
        help="解析合同文件为结构化条款",
    )
    
    parser.add_argument(
        "--risks",
        metavar="FILE",
        help="识别合同文件中的风险点",
    )
    
    parser.add_argument(
        "--nda",
        nargs=3,
        metavar=("PARTY_A", "PARTY_B", "YEARS"),
        help="生成保密协议：甲方 乙方 保密期限(年)",
    )
    
    parser.add_argument(
        "--audit",
        metavar="FILE",
        help="对合同文件进行合规审计",
    )
    
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("FILE_A", "FILE_B"),
        help="比对两份合同文件的条款差异",
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 无参数时显示帮助
    if not (args.parse or args.risks or args.nda or args.audit or args.compare):
        parser.print_help()
        return 0
    
    # 各功能模式
    try:
        if args.parse:
            try:
                with open(args.parse, "r", encoding="utf-8") as f:
                    text = f.read()
            except FileNotFoundError:
                print(f"E002: 文件不存在 - {args.parse}", file=sys.stderr)
                return 2
            result = parse_contract(text)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        
        elif args.risks:
            try:
                with open(args.risks, "r", encoding="utf-8") as f:
                    text = f.read()
            except FileNotFoundError:
                print(f"E002: 文件不存在 - {args.risks}", file=sys.stderr)
                return 2
            result = identify_risks(text)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        
        elif args.nda:
            party_a, party_b, years_str = args.nda
            try:
                years = int(years_str)
            except ValueError:
                print(f"E001: 保密期限必须为整数 - {years_str}", file=sys.stderr)
                return 1
            result = generate_nda(party_a, party_b, years)
            print(result["协议全文"])
        
        elif args.audit:
            try:
                with open(args.audit, "r", encoding="utf-8") as f:
                    text = f.read()
            except FileNotFoundError:
                print(f"E002: 文件不存在 - {args.audit}", file=sys.stderr)
                return 2
            result = compliance_audit(text)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        
        elif args.compare:
            file_a, file_b = args.compare
            try:
                with open(file_a, "r", encoding="utf-8") as f:
                    text_a = f.read()
                with open(file_b, "r", encoding="utf-8") as f:
                    text_b = f.read()
            except FileNotFoundError as e:
                print(f"E002: 文件不存在 - {e.filename}", file=sys.stderr)
                return 2
            result = compare_clauses(text_a, text_b)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知错误 - {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
