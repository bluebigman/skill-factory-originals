#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patent_pro - 专利价值评估与风险预警系统
离线自检工具，用于验证核心功能
"""

import sys
import os
import json
import math
import random
from datetime import datetime, timedelta
from collections import defaultdict

# ============================================================
# 核心数据结构
# ============================================================

class Patent:
    """专利类"""
    def __init__(self, patent_id, title, abstract, claims, applicants, inventors, 
                 filing_date, grant_date, expiration_date, status, tech_field, 
                 citations, cited_by, maintenance_fees_paid, family_size, 
                 claims_count, description_length, has_drawings, has_claims, 
                 has_abstract, has_description, is_independent, is_dependent, 
                 priority_count, pct_applications, foreign_filings):
        self.patent_id = patent_id
        self.title = title
        self.abstract = abstract
        self.claims = claims
        self.applicants = applicants
        self.inventors = inventors
        self.filing_date = filing_date
        self.grant_date = grant_date
        self.expiration_date = expiration_date
        self.status = status
        self.tech_field = tech_field
        self.citations = citations
        self.cited_by = cited_by
        self.maintenance_fees_paid = maintenance_fees_paid
        self.family_size = family_size
        self.claims_count = claims_count
        self.description_length = description_length
        self.has_drawings = has_drawings
        self.has_claims = has_claims
        self.has_abstract = has_abstract
        self.has_description = has_description
        self.is_independent = is_independent
        self.is_dependent = is_dependent
        self.priority_count = priority_count
        self.pct_applications = pct_applications
        self.foreign_filings = foreign_filings

    def age_years(self, current_date=None):
        """计算专利年龄（年）"""
        if current_date is None:
            current_date = datetime.now().date()
        if self.filing_date:
            return (current_date - self.filing_date).days / 365.25
        return 0

    def remaining_life_years(self, current_date=None):
        """计算剩余寿命（年）"""
        if current_date is None:
            current_date = datetime.now().date()
        if self.expiration_date:
            return max(0, (self.expiration_date - current_date).days / 365.25)
        return 0


# ============================================================
# 数据生成与加载
# ============================================================

def generate_sample_data():
    """生成样例专利数据"""
    patents = []
    
    # 创建一些样例专利
    sample_data = [
        {
            "patent_id": "US10000001B2",
            "title": "Method and system for blockchain-based secure data storage",
            "abstract": "A method and system for storing data securely using blockchain technology. The system includes a distributed ledger, cryptographic hash functions, and consensus mechanisms.",
            "claims": "1. A method for secure data storage comprising: receiving data; hashing the data; storing the hash in a blockchain; and verifying the data integrity.",
            "applicants": ["Blockchain Innovations Inc."],
            "inventors": ["John Smith", "Jane Doe"],
            "filing_date": datetime(2018, 5, 15).date(),
            "grant_date": datetime(2020, 3, 10).date(),
            "expiration_date": datetime(2038, 5, 15).date(),
            "status": "active",
            "tech_field": "blockchain",
            "citations": [5, 8, 12],
            "cited_by": [45, 32, 28, 15],
            "maintenance_fees_paid": True,
            "family_size": 5,
            "claims_count": 15,
            "description_length": 12000,
            "has_drawings": True,
            "has_claims": True,
            "has_abstract": True,
            "has_description": True,
            "is_independent": True,
            "is_dependent": False,
            "priority_count": 2,
            "pct_applications": 1,
            "foreign_filings": 3
        },
        {
            "patent_id": "US10000002B2",
            "title": "Artificial intelligence-based medical diagnosis system",
            "abstract": "An AI system for medical diagnosis using deep learning algorithms. The system analyzes medical images and patient data to provide diagnostic recommendations.",
            "claims": "1. A medical diagnosis system comprising: a neural network; an image processing module; and a diagnostic output interface.",
            "applicants": ["MedTech Solutions LLC"],
            "inventors": ["Alice Johnson", "Bob Wilson"],
            "filing_date": datetime(2019, 8, 20).date(),
            "grant_date": datetime(2021, 6, 15).date(),
            "expiration_date": datetime(2039, 8, 20).date(),
            "status": "active",
            "tech_field": "ai_healthcare",
            "citations": [3, 6, 10],
            "cited_by": [25, 18, 12],
            "maintenance_fees_paid": True,
            "family_size": 3,
            "claims_count": 12,
            "description_length": 15000,
            "has_drawings": True,
            "has_claims": True,
            "has_abstract": True,
            "has_description": True,
            "is_independent": True,
            "is_dependent": False,
            "priority_count": 1,
            "pct_applications": 0,
            "foreign_filings": 2
        },
        {
            "patent_id": "US10000003B2",
            "title": "Renewable energy storage system using advanced battery technology",
            "abstract": "A system for storing renewable energy using advanced battery technology. The system optimizes charging cycles and extends battery life.",
            "claims": "1. An energy storage system comprising: a battery array; a charge controller; and an optimization module.",
            "applicants": ["GreenEnergy Corp"],
            "inventors": ["David Brown"],
            "filing_date": datetime(2020, 2, 10).date(),
            "grant_date": datetime(2022, 1, 20).date(),
            "expiration_date": datetime(2040, 2, 10).date(),
            "status": "active",
            "tech_field": "renewable_energy",
            "citations": [2, 4, 7],
            "cited_by": [15, 10, 8],
            "maintenance_fees_paid": True,
            "family_size": 4,
            "claims_count": 10,
            "description_length": 10000,
            "has_drawings": True,
            "has_claims": True,
            "has_abstract": True,
            "has_description": True,
            "is_independent": True,
            "is_dependent": False,
            "priority_count": 1,
            "pct_applications": 1,
            "foreign_filings": 2
        },
        {
            "patent_id": "US10000004B2",
            "title": "Autonomous vehicle navigation system",
            "abstract": "A navigation system for autonomous vehicles using sensor fusion and real-time mapping. The system enables safe navigation in complex environments.",
            "claims": "1. A navigation system comprising: sensors; a mapping module; and a decision-making module.",
            "applicants": ["AutoDrive Technologies"],
            "inventors": ["Sarah Lee", "Michael Chen"],
            "filing_date": datetime(2017, 11, 5).date(),
            "grant_date": datetime(2019, 9, 30).date(),
            "expiration_date": datetime(2037, 11, 5).date(),
            "status": "active",
            "tech_field": "autonomous_vehicles",
            "citations": [8, 15, 20],
            "cited_by": [50, 35, 22, 18],
            "maintenance_fees_paid": True,
            "family_size": 6,
            "claims_count": 18,
            "description_length": 18000,
            "has_drawings": True,
            "has_claims": True,
            "has_abstract": True,
            "has_description": True,
            "is_independent": True,
            "is_dependent": False,
            "priority_count": 3,
            "pct_applications": 2,
            "foreign_filings": 4
        },
        {
            "patent_id": "US10000005B2",
            "title": "Quantum computing error correction method",
            "abstract": "A method for error correction in quantum computing systems. The method uses surface codes and topological protection to reduce error rates.",
            "claims": "1. A quantum error correction method comprising: encoding qubits; applying error detection; and performing correction operations.",
            "applicants": ["QuantumTech Labs"],
            "inventors": ["Emma Davis", "James Wilson"],
            "filing_date": datetime(2021, 3, 15).date(),
            "grant_date": datetime(2023, 5, 10).date(),
            "expiration_date": datetime(2041, 3, 15).date(),
            "status": "active",
            "tech_field": "quantum_computing",
            "citations": [4, 6, 9],
            "cited_by": [12, 8, 5],
            "maintenance_fees_paid": True,
            "family_size": 2,
            "claims_count": 8,
            "description_length": 9000,
            "has_drawings": True,
            "has_claims": True,
            "has_abstract": True,
            "has_description": True,
            "is_independent": True,
            "is_dependent": False,
            "priority_count": 1,
            "pct_applications": 0,
            "foreign_filings": 1
        }
    ]
    
    for data in sample_data:
        patent = Patent(**data)
        patents.append(patent)
    
    return patents


def load_patents():
    """加载专利数据（使用样例数据）"""
    return generate_sample_data()


# ============================================================
# 核心功能模块
# ============================================================

def calculate_patent_score(patent):
    """计算专利综合评分（0-100）"""
    score = 0.0
    weights = {
        'citations': 0.20,
        'family_size': 0.15,
        'claims': 0.15,
        'remaining_life': 0.15,
        'tech_field': 0.10,
        'maintenance': 0.10,
        'international': 0.15
    }
    
    # 引用评分（0-100）
    citation_score = min(100, len(patent.cited_by) * 10)
    
    # 家族规模评分
    family_score = min(100, patent.family_size * 20)
    
    # 权利要求评分
    claims_score = min(100, patent.claims_count * 5)
    
    # 剩余寿命评分
    remaining_life = patent.remaining_life_years()
    life_score = min(100, remaining_life * 5)
    
    # 技术领域评分（热门领域加分）
    hot_fields = ['blockchain', 'ai_healthcare', 'quantum_computing']
    tech_score = 70 if patent.tech_field in hot_fields else 50
    
    # 维护费评分
    maintenance_score = 100 if patent.maintenance_fees_paid else 30
    
    # 国际化评分
    international_score = min(100, (patent.priority_count + patent.pct_applications + patent.foreign_filings) * 15)
    
    # 加权计算
    score = (citation_score * weights['citations'] +
             family_score * weights['family_size'] +
             claims_score * weights['claims'] +
             life_score * weights['remaining_life'] +
             tech_score * weights['tech_field'] +
             maintenance_score * weights['maintenance'] +
             international_score * weights['international'])
    
    return max(0, min(100, score))


def identify_high_value_patents(patents, threshold=70):
    """识别高价值专利"""
    high_value = []
    for patent in patents:
        score = calculate_patent_score(patent)
        if score >= threshold:
            high_value.append((patent, score))
    return high_value


def identify_low_value_patents(patents, threshold=40):
    """识别低价值专利"""
    low_value = []
    for patent in patents:
        score = calculate_patent_score(patent)
        if score < threshold:
            low_value.append((patent, score))
    return low_value


def identify_at_risk_patents(patents, months_threshold=6):
    """识别有风险专利（即将到期或维护费未缴）"""
    at_risk = []
    current_date = datetime.now().date()
    
    for patent in patents:
        risk_reasons = []
        
        # 检查剩余寿命
        remaining_life = patent.remaining_life_years()
        if remaining_life < months_threshold / 12:
            risk_reasons.append(f"剩余寿命不足{months_threshold}个月")
        
        # 检查维护费
        if not patent.maintenance_fees_paid:
            risk_reasons.append("维护费未缴纳")
        
        # 检查状态
        if patent.status != "active":
            risk_reasons.append(f"状态异常: {patent.status}")
        
        if risk_reasons:
            at_risk.append((patent, risk_reasons))
    
    return at_risk


def analyze_patent_portfolio(patents):
    """分析专利组合"""
    if not patents:
        return {
            'total_patents': 0,
            'avg_score': 0,
            'high_value_count': 0,
            'low_value_count': 0,
            'at_risk_count': 0,
            'tech_distribution': {},
            'status_distribution': {}
        }
    
    scores = [calculate_patent_score(p) for p in patents]
    high_value = identify_high_value_patents(patents)
    low_value = identify_low_value_patents(patents)
    at_risk = identify_at_risk_patents(patents)
    
    # 技术领域分布
    tech_dist = defaultdict(int)
    for p in patents:
        tech_dist[p.tech_field] += 1
    
    # 状态分布
    status_dist = defaultdict(int)
    for p in patents:
        status_dist[p.status] += 1
    
    return {
        'total_patents': len(patents),
        'avg_score': sum(scores) / len(scores),
        'high_value_count': len(high_value),
        'low_value_count': len(low_value),
        'at_risk_count': len(at_risk),
        'tech_distribution': dict(tech_dist),
        'status_distribution': dict(status_dist)
    }


def generate_patent_report(patents):
    """生成专利报告"""
    analysis = analyze_patent_portfolio(patents)
    high_value = identify_high_value_patents(patents)
    at_risk = identify_at_risk_patents(patents)
    
    report = []
    report.append("=" * 60)
    report.append("专利价值评估与风险预警报告")
    report.append("=" * 60)
    report.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"专利总数: {analysis['total_patents']}")
    report.append(f"平均评分: {analysis['avg_score']:.2f}")
    report.append(f"高价值专利数: {analysis['high_value_count']}")
    report.append(f"低价值专利数: {analysis['low_value_count']}")
    report.append(f"风险专利数: {analysis['at_risk_count']}")
    report.append("")
    
    report.append("技术领域分布:")
    for field, count in analysis['tech_distribution'].items():
        report.append(f"  - {field}: {count}件")
    report.append("")
    
    report.append("高价值专利:")
    for patent, score in high_value:
        report.append(f"  - {patent.patent_id}: {score:.2f}分")
    report.append("")
    
    report.append("风险专利:")
    for patent, reasons in at_risk:
        report.append(f"  - {patent.patent_id}: {', '.join(reasons)}")
    report.append("")
    
    report.append("=" * 60)
    return "\n".join(report)


# ============================================================
# 自检模块
# ============================================================

def selftest():
    """自检函数"""
    print("=" * 60)
    print("patent_pro 自检开始")
    print("=" * 60)
    
    # 加载数据
    patents = load_patents()
    assert len(patents) > 0, "契约1失败：应识别为专利"
    print(f"[PASS] 加载专利数据: {len(patents)}件")
    
    # 测试评分功能
    scores = [calculate_patent_score(p) for p in patents]
    for i, score in enumerate(scores):
        assert 0 <= score <= 100, f"契约2失败：评分应在0-100之间，实际{score}"
        print(f"[PASS] 专利{patents[i].patent_id}评分: {score:.2f}")
    
    # 测试高价值识别
    high_value = identify_high_value_patents(patents)
    assert len(high_value) > 0, "契约3失败：应识别出高价值专利"
    for patent, score in high_value:
        assert score >= 70, f"契约4失败：高价值专利评分应>=70，实际{score}"
    print(f"[PASS] 高价值专利识别: {len(high_value)}件")
    
    # 测试低价值识别
    low_value = identify_low_value_patents(patents)
    for patent, score in low_value:
        assert score < 40, f"契约5失败：低价值专利评分应<40，实际{score}"
    print(f"[PASS] 低价值专利识别: {len(low_value)}件")
    
    # 测试风险识别
    at_risk = identify_at_risk_patents(patents)
    print(f"[PASS] 风险专利识别: {len(at_risk)}件")
    
    # 测试组合分析
    analysis = analyze_patent_portfolio(patents)
    assert analysis['total_patents'] == len(patents), "契约6失败：专利总数不匹配"
    assert analysis['avg_score'] > 0, "契约7失败：平均评分应大于0"
    print(f"[PASS] 组合分析: 平均评分{analysis['avg_score']:.2f}")
    
    # 测试报告生成
    report = generate_patent_report(patents)
    assert len(report) > 100, "契约8失败：报告内容应足够详细"
    print("[PASS] 报告生成成功")
    
    # 测试边界情况
    empty_patents = []
    empty_analysis = analyze_patent_portfolio(empty_patents)
    assert empty_analysis['total_patents'] == 0, "契约9失败：空列表应返回0"
    assert empty_analysis['avg_score'] == 0, "契约10失败：空列表平均评分应为0"
    print("[PASS] 边界情况测试通过")
    
    print("=" * 60)
    print("patent_pro 自检完成 - 全部通过")
    print("=" * 60)
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        try:
            result = selftest()
            sys.exit(0 if result else 1)
        except AssertionError as e:
            print(f"\n[FAIL] {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] {e}")
            sys.exit(1)
    
    # 正常运行模式
    print("patent_pro - 专利价值评估与风险预警系统")
    print("使用 --selftest 参数运行自检")
    
    # 加载数据并生成报告
    patents = load_patents()
    report = generate_patent_report(patents)
    print(report)


if __name__ == "__main__":
    main()
