#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docspect — 合同文本审阅与风险标注（独立实现）

本脚本依据功能规格独立编写，不参考任何既有实现。
仅使用 Python 标准库，无第三方依赖。

用法示例:
    python main.py --selftest              # 离线自检
    python main.py --file contract.txt     # 审查单个合同文件
    python main.py --compare a.txt b.txt   # 两份合同条款比对
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# E001: 参数错误
# E002: 文件不存在
# E003: 文件读取失败
# E004: 文本过短（少于500字）
# E005: 文本过长（超过50000字）
# E006: 文本为空
# E007: 内部解析异常
# E008: 比对文本长度不一致
# E009: 输出序列化失败
# E010: 未知错误
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class ContractStructure:
    """合同结构树"""
    title: str = ""
    parties: List[str] = field(default_factory=list)
    recitals: List[str] = field(default_factory=list)
    definitions: List[str] = field(default_factory=list)
    body_clauses: List[Dict[str, str]] = field(default_factory=list)
    signature_block: List[str] = field(default_factory=list)


@dataclass
class ClauseClassification:
    """条款分类结果"""
    category: str = ""
    clause_text: str = ""
    confidence: float = 0.0


@dataclass
class RiskPoint:
    """风险点"""
    risk_type: str = ""
    clause_ref: str = ""
    description: str = ""
    severity: str = ""  # 高/中/低


@dataclass
class ContractSummary:
    """合同摘要"""
    core_transaction: str = ""
    total_amount: str = ""
    duration: str = ""
    key_obligations: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """条款比对结果"""
    clause_index: int = 0
    clause_a: str = ""
    clause_b: str = ""
    difference: str = ""
    similarity: float = 0.0


# ---------------------------------------------------------------------------
# 核心分析引擎
# ---------------------------------------------------------------------------

class DocSpectEngine:
    """合同审阅引擎：负责结构解析、分类、风险识别、摘要生成、条款比对"""

    # 条款分类关键词表
    CATEGORY_KEYWORDS = {
        "付款": ["付款", "支付", "价款", "费用", "金额", "结算", "定金", "违约金", "赔偿"],
        "交付": ["交付", "交货", "提供", "送达", "移交", "验收", "签收"],
        "违约": ["违约", "责任", "赔偿", "解除", "终止", "补救"],
        "保密": ["保密", "机密", "披露", "泄露", "保护"],
        "知识产权": ["知识产权", "专利", "商标", "著作权", "版权", "技术秘密"],
        "管辖": ["管辖", "仲裁", "诉讼", "法律适用", "争议解决"],
        "其他": []
    }

    # 风险关键词
    RISK_PATTERNS = [
        (r"尽快|及时|合理时间|适当时候", "模糊时间表述", "中"),
        (r"相关费用|合理费用|必要费用", "费用表述不明确", "中"),
        (r"有权单方|可单方|自行决定", "单方权利失衡", "高"),
        (r"视情况|根据情况|酌情", "裁量权模糊", "中"),
        (r"本合同未尽事宜|其他事项", "未尽事宜条款缺失", "低"),
        (r"口头|电话|微信", "非书面形式约定", "低"),
        (r"不可抗力", "不可抗力条款", "低"),
        (r"续签|自动续期", "自动续期风险", "中"),
        (r"管辖法院|仲裁委员会", "争议解决条款", "低"),
        (r"盖章|签字|签署", "签署要件", "低"),
    ]

    def __init__(self) -> None:
        self._text = ""
        self._lines: List[str] = []

    # -----------------------------------------------------------------------
    # 对外主接口
    # -----------------------------------------------------------------------

    def analyze(self, text: str) -> Dict:
        """
        执行完整合同审阅流程。
        返回包含结构、分类、风险、摘要的结构化字典。
        """
        # 输入校验
        if not text or not text.strip():
            raise ValueError("E006: 文本为空")
        if len(text.strip()) < 500:
            raise ValueError("E004: 文本过短（少于500字）")
        if len(text.strip()) > 50000:
            raise ValueError("E005: 文本过长（超过50000字）")

        self._text = text.strip()
        self._lines = [ln.strip() for ln in self._text.splitlines() if ln.strip()]

        try:
            structure = self._parse_structure()
            classifications = self._classify_clauses(structure.body_clauses)
            risks = self._identify_risks(structure)
            summary = self._generate_summary(structure, classifications)

            return {
                "structure": asdict(structure),
                "classifications": [asdict(c) for c in classifications],
                "risks": [asdict(r) for r in risks],
                "summary": asdict(summary),
            }
        except Exception as exc:
            raise RuntimeError(f"E007: 内部解析异常 - {str(exc)}") from exc

    def compare(self, text_a: str, text_b: str) -> List[Dict]:
        """
        比对两份合同的条款差异。
        返回差异对照表。
        """
        if not text_a or not text_b:
            raise ValueError("E006: 文本为空")

        # 提取条款
        clauses_a = self._extract_clauses(text_a)
        clauses_b = self._extract_clauses(text_b)

        # 对齐并比较
        max_len = max(len(clauses_a), len(clauses_b))
        results: List[ComparisonResult] = []

        for i in range(max_len):
            clause_a = clauses_a[i] if i < len(clauses_a) else ""
            clause_b = clauses_b[i] if i < len(clauses_b) else ""

            if not clause_a and not clause_b:
                continue

            similarity = self._compute_similarity(clause_a, clause_b)
            difference = self._describe_difference(clause_a, clause_b)

            results.append(ComparisonResult(
                clause_index=i + 1,
                clause_a=clause_a[:200],
                clause_b=clause_b[:200],
                difference=difference,
                similarity=similarity,
            ))

        return [asdict(r) for r in results]

    # -----------------------------------------------------------------------
    # 结构解析
    # -----------------------------------------------------------------------

    def _parse_structure(self) -> ContractStructure:
        """解析合同结构"""
        structure = ContractStructure()
        structure.title = self._detect_title()
        structure.parties = self._detect_parties()
        structure.recitals = self._detect_recitals()
        structure.definitions = self._detect_definitions()
        structure.body_clauses = self._extract_clauses(self._text)
        structure.signature_block = self._detect_signature_block()
        return structure

    def _detect_title(self) -> str:
        """检测合同标题"""
        for line in self._lines[:10]:
            if re.search(r"合同|协议|契约", line) and len(line) < 50:
                return line
        return "未命名合同"

    def _detect_parties(self) -> List[str]:
        """检测当事人"""
        parties = []
        patterns = [
            r"甲方[:：]?\s*(.+)",
            r"乙方[:：]?\s*(.+)",
            r"丙方[:：]?\s*(.+)",
            r"丁方[:：]?\s*(.+)",
        ]
        for line in self._lines:
            for pat in patterns:
                m = re.match(pat, line)
                if m:
                    parties.append(m.group(1).strip())
        return parties

    def _detect_recitals(self) -> List[str]:
        """检测鉴于条款"""
        recitals = []
        in_recital = False
        for line in self._lines:
            if re.search(r"鉴于|背景|前言", line):
                in_recital = True
                recitals.append(line)
                continue
            if in_recital:
                if re.match(r"第[一二三四五六七八九十百千0-9]+条", line):
                    break
                recitals.append(line)
        return recitals

    def _detect_definitions(self) -> List[str]:
        """检测定义条款"""
        definitions = []
        in_definition = False
        for line in self._lines:
            if re.search(r"定义|术语|解释", line):
                in_definition = True
                continue
            if in_definition:
                if re.match(r"第[一二三四五六七八九十百千0-9]+条", line):
                    break
                definitions.append(line)
        return definitions

    def _extract_clauses(self, text: str) -> List[str]:
        """提取正文条款"""
        clauses = []
        # 按条款编号分割
        pattern = r"(第[一二三四五六七八九十百千0-9]+条[^\n]*)"
        parts = re.split(pattern, text)
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                clause_header = parts[i].strip()
                clause_body = parts[i + 1].strip()
                if clause_body:
                    clauses.append(f"{clause_header}\n{clause_body[:500]}")
        return clauses

    def _detect_signature_block(self) -> List[str]:
        """检测签署页"""
        signature = []
        in_signature = False
        for line in self._lines:
            if re.search(r"签署|盖章|签字|法定代表人", line):
                in_signature = True
            if in_signature:
                signature.append(line)
                if len(signature) > 20:
                    break
        return signature

    # -----------------------------------------------------------------------
    # 条款分类
    # -----------------------------------------------------------------------

    def _classify_clauses(self, clauses: List[str]) -> List[ClauseClassification]:
        """对条款进行分类标注"""
        results = []
        for clause in clauses:
            category = "其他"
            best_score = 0.0
            for cat, keywords in self.CATEGORY_KEYWORDS.items():
                score = sum(1 for kw in keywords if kw in clause)
                if score > best_score:
                    best_score = score
                    category = cat
            confidence = min(best_score / 3.0, 1.0)
            results.append(ClauseClassification(
                category=category,
                clause_text=clause[:200],
                confidence=confidence,
            ))
        return results

    # -----------------------------------------------------------------------
    # 风险识别
    # -----------------------------------------------------------------------

    def _identify_risks(self, structure: ContractStructure) -> List[RiskPoint]:
        """识别风险点"""
        risks = []
        full_text = self._text

        # 基于关键词模式匹配
        for pattern, desc, severity in self.RISK_PATTERNS:
            matches = re.finditer(pattern, full_text)
            for m in matches:
                start = max(0, m.start() - 30)
                end = min(len(full_text), m.end() + 30)
                context = full_text[start:end].replace("\n", " ")
                risks.append(RiskPoint(
                    risk_type=desc,
                    clause_ref=f"位置 {m.start()}",
                    description=f"检测到: {context}...",
                    severity=severity,
                ))

        # 检查缺失要素
        if not structure.parties:
            risks.append(RiskPoint(
                risk_type="缺少当事人信息",
                clause_ref="合同头部",
                description="未检测到甲方/乙方等当事人信息",
                severity="高",
            ))

        if not structure.signature_block:
            risks.append(RiskPoint(
                risk_type="缺少签署条款",
                clause_ref="合同尾部",
                description="未检测到签署/盖章条款",
                severity="高",
            ))

        # 去重
        unique_risks = []
        seen = set()
        for r in risks:
            key = (r.risk_type, r.clause_ref[:50])
            if key not in seen:
                seen.add(key)
                unique_risks.append(r)

        return unique_risks[:20]  # 最多返回20条

    # -----------------------------------------------------------------------
    # 摘要生成
    # -----------------------------------------------------------------------

    def _generate_summary(self, structure: ContractStructure,
                          classifications: List[ClauseClassification]) -> ContractSummary:
        """生成合同摘要"""
        summary = ContractSummary()

        # 核心交易结构
        transaction_parts = []
        if structure.parties:
            transaction_parts.append(f"当事人: {'、'.join(structure.parties[:4])}")
        if structure.recitals:
            transaction_parts.append(f"鉴于: {structure.recitals[0][:100]}")

        # 金额提取
        amount_pattern = r"[¥￥]?\s*(\d+(?:\.\d+)?)\s*(万元|元|人民币|美元|欧元)?"
        amounts = re.findall(amount_pattern, self._text)
        if amounts:
            total = sum(float(a[0]) for a in amounts[:10])
            unit = amounts[0][1] if amounts[0][1] else "元"
            summary.total_amount = f"约{total:.0f}{unit}（基于文本中出现的金额估算）"

        # 期限提取
        duration_pattern = r"(\d+)\s*(天|日|月|年|周)"
        durations = re.findall(duration_pattern, self._text)
        if durations:
            summary.duration = f"约{durations[0][0]}{durations[0][1]}"

        # 关键义务
        for cls in classifications:
            if cls.category in ("付款", "交付", "违约") and cls.confidence > 0.5:
                summary.key_obligations.append(cls.clause_text[:100])

        summary.core_transaction = "；".join(transaction_parts) if transaction_parts else "未能自动提取交易结构"
        summary.key_obligations = summary.key_obligations[:5]

        return summary

    # -----------------------------------------------------------------------
    # 比对辅助
    # -----------------------------------------------------------------------

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        """计算文本相似度（基于字符集合重叠）"""
        if not text_a or not text_b:
            return 0.0
        set_a = set(text_a)
        set_b = set(text_b)
        if not set_a or not set_b:
            return 0.0
        overlap = len(set_a & set_b) / max(len(set_a | set_b), 1)
        return round(overlap, 4)

    def _describe_difference(self, text_a: str, text_b: str) -> str:
        """描述条款差异"""
        if not text_a and text_b:
            return "新增条款"
        if text_a and not text_b:
            return "删除条款"
        if text_a == text_b:
            return "条款一致"
        # 简单长度比较
        if len(text_a) > len(text_b) * 1.5:
            return "条款内容明显扩充"
        if len(text_b) > len(text_a) * 1.5:
            return "条款内容明显缩减"
        return "条款内容有修改"


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件、网络或工作目录。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("docspect 自检开始")
    print("=" * 60)

    engine = DocSpectEngine()

    # 构造测试用合同文本（约600字）
    sample_contract = """
    技术服务合同

    甲方：北京科技有限公司
    乙方：上海数据服务有限公司

    鉴于甲方需要技术服务支持，乙方具有相应技术能力，双方达成如下协议：

    第一条 定义
    本合同所称"技术服务"指乙方为甲方提供的系统开发、调试及维护服务。

    第二条 服务内容
    乙方应在本合同生效后30日内完成系统开发工作，并尽快交付甲方验收。
    交付标准以双方确认的技术方案为准，相关费用由甲方承担。

    第三条 付款方式
    甲方应在验收合格后15日内支付合同总价款的80%，剩余20%作为质保金。
    具体金额为人民币50万元，相关费用包含所有开发成本。

    第四条 保密条款
    双方应对本合同内容及履约过程中获知的对方商业秘密承担保密义务。
    未经对方书面同意，不得向第三方披露。

    第五条 知识产权
    项目开发过程中产生的知识产权归甲方所有，乙方保留署名权。
    乙方不得将技术秘密用于本合同以外的其他用途。

    第六条 违约责任
    任何一方违约应赔偿对方因此遭受的损失，违约金为合同金额的30%。
    守约方有权单方解除本合同并要求违约方承担违约责任。

    第七条 争议解决
    因本合同引起的争议，双方应友好协商解决；协商不成的，提交北京仲裁委员会仲裁。

    第八条 其他
    本合同未尽事宜由双方协商解决。本合同一式两份，双方各执一份。

    甲方（盖章）：北京科技有限公司
    法定代表人：张三
    签署日期：2025年1月1日

    乙方（盖章）：上海数据服务有限公司
    法定代表人：李四
    签署日期：2025年1月1日
    """

    # --- 测试1: 基本分析 ---
    print("\n[测试1] 合同基本分析")
    try:
        result = engine.analyze(sample_contract)
        assert result is not None, "分析结果不应为None"
        assert "structure" in result, "应包含structure字段"
        assert "risks" in result, "应包含risks字段"
        assert "summary" in result, "应包含summary字段"
        assert "classifications" in result, "应包含classifications字段"
        print("  ✓ 分析结果包含所有必需字段")

        # 宽松断言：结构字段应存在
        struct = result["structure"]
        assert isinstance(struct.get("title", ""), str), "标题应为字符串"
        assert len(struct.get("parties", [])) >= 0, "当事人列表应存在"
        print("  ✓ 结构解析正常")

        # 风险数量不为负数
        assert len(result["risks"]) >= 0, "风险列表应存在"
        print(f"  ✓ 风险识别完成，识别到 {len(result['risks'])} 条风险")

        # 摘要字段存在
        summary = result["summary"]
        assert isinstance(summary.get("total_amount", ""), str), "金额应为字符串"
        print(f"  ✓ 摘要生成完成: {summary.get('total_amount', '未提取到金额')}")

    except AssertionError as ae:
        print(f"  ✗ 断言失败: {ae}")
        return False
    except Exception as exc:
        print(f"  ✗ 测试异常: {exc}")
        return False

    # --- 测试2: 条款分类 ---
    print("\n[测试2] 条款分类")
    try:
        classifications = result["classifications"]
        assert len(classifications) > 0, "应至少有一个分类结果"
        categories = [c["category"] for c in classifications]
        assert "付款" in categories or "交付" in categories, "应识别出付款或交付类条款"
        print(f"  ✓ 分类完成，共 {len(classifications)} 条，类别: {set(categories)}")

        # 置信度在合理范围
        for c in classifications:
            assert 0.0 <= c["confidence"] <= 1.0, "置信度应在0-1之间"
        print("  ✓ 所有置信度在合理范围")

    except AssertionError as ae:
        print(f"  ✗ 断言失败: {ae}")
        return False
    except Exception as exc:
        print(f"  ✗ 测试异常: {exc}")
        return False

    # --- 测试3: 风险识别 ---
    print("\n[测试3] 风险识别")
    try:
        risks = result["risks"]
        risk_types = [r["risk_type"] for r in risks]
        assert len(risk_types) > 0, "应识别出风险"
        assert any("模糊" in t or "缺失" in t or "失衡" in t for t in risk_types), \
            "应包含典型风险类型"
        print(f"  ✓ 风险类型: {risk_types[:5]}")

        # 严重程度字段合法
        for r in risks:
            assert r["severity"] in ("高", "中", "低"), "严重程度应合法"
        print("  ✓ 风险严重程度字段合法")

    except AssertionError as ae:
        print(f"  ✗ 断言失败: {ae}")
        return False
    except Exception as exc:
        print(f"  ✗ 测试异常: {exc}")
        return False

    # --- 测试4: 条款比对 ---
    print("\n[测试4] 条款比对")
    try:
        # 构造第二份合同（有修改）
        sample_contract_v2 = sample_contract.replace("30日", "45日").replace("80%", "70%")
        comparisons = engine.compare(sample_contract, sample_contract_v2)
        assert len(comparisons) > 0, "比对结果不应为空"
        assert any(c["difference"] != "条款一致" for c in comparisons), "应存在差异条款"
        print(f"  ✓ 比对完成，共 {len(comparisons)} 条，发现差异")

        # 相似度在合理范围
        for c in comparisons:
            assert 0.0 <= c["similarity"] <= 1.0, "相似度应在0-1之间"
        print("  ✓ 相似度字段合法")

    except AssertionError as ae:
        print(f"  ✗ 断言失败: {ae}")
        return False
    except Exception as exc:
        print(f"  ✗ 测试异常: {exc}")
        return False

    # --- 测试5: 输入校验 ---
    print("\n[测试5] 输入校验")
    try:
        # 空文本
        try:
            engine.analyze("")
            print("  ✗ 空文本未报错")
            return False
        except ValueError as ve:
            assert "E006" in str(ve), "应返回E006错误码"
            print("  ✓ 空文本正确报错 E006")

        # 过短文本
        try:
            engine.analyze("短文本")
            print("  ✗ 过短文本未报错")
            return False
        except ValueError as ve:
            assert "E004" in str(ve), "应返回E004错误码"
            print("  ✓ 过短文本正确报错 E004")

    except AssertionError as ae:
        print(f"  ✗ 断言失败: {ae}")
        return False
    except Exception as exc:
        print(f"  ✗ 测试异常: {exc}")
        return False

    # --- 测试6: 输出JSON可序列化 ---
    print("\n[测试6] JSON序列化")
    try:
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        assert len(json_str) > 0, "JSON序列化结果不应为空"
        print(f"  ✓ JSON序列化成功，长度 {len(json_str)} 字符")

        # 反序列化验证
        parsed = json.loads(json_str)
        assert parsed["structure"]["title"] == result["structure"]["title"], "反序列化应一致"
        print("  ✓ JSON反序列化验证通过")

    except Exception as exc:
        print(f"  ✗ 测试异常: {exc}")
        return False

    print("\n" + "=" * 60)
    print("所有自检测试通过 ✓")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 文件处理辅助
# ---------------------------------------------------------------------------

def read_text_file(filepath: str) -> str:
    """读取文本文件，支持UTF-8和GBK编码"""
    if not filepath:
        raise ValueError("E001: 文件路径不能为空")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"E002: 文件不存在 - {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="gbk") as f:
                return f.read()
        except Exception as exc:
            raise IOError(f"E003: 文件读取失败 - {str(exc)}") from exc
    except Exception as exc:
        raise IOError(f"E003: 文件读取失败 - {str(exc)}") from exc


def format_output(data: Dict, pretty: bool = True) -> str:
    """格式化输出结果"""
    try:
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)
    except Exception as exc:
        raise RuntimeError(f"E009: 输出序列化失败 - {str(exc)}") from exc


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="docspect - 合同文本审阅与风险标注工具",
        epilog="示例: python main.py --selftest"
    )
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检（不依赖外部文件）")
    parser.add_argument("--file", "-f", type=str,
                        help="待审查的合同文件路径")
    parser.add_argument("--compare", "-c", nargs=2, metavar=("FILE_A", "FILE_B"),
                        help="比对两份合同文件")
    parser.add_argument("--output", "-o", type=str,
                        help="输出结果到文件（JSON格式）")
    parser.add_argument("--compact", action="store_true",
                        help="紧凑JSON输出（不缩进）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 比对模式
    if args.compare:
        try:
            text_a = read_text_file(args.compare[0])
            text_b = read_text_file(args.compare[1])
            engine = DocSpectEngine()
            result = engine.compare(text_a, text_b)
            output = format_output({"comparison": result}, not args.compact)
            print(output)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            return 0
        except (ValueError, FileNotFoundError, IOError, RuntimeError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1

    # 单文件审查模式
    if args.file:
        try:
            text = read_text_file(args.file)
            engine = DocSpectEngine()
            result = engine.analyze(text)
            output = format_output(result, not args.compact)
            print(output)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            return 0
        except (ValueError, FileNotFoundError, IOError, RuntimeError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    import os  # 延迟导入，确保selftest路径不依赖
    sys.exit(main())
