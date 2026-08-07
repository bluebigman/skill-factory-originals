#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同智审 (ailaw1) - 多维度智能合同审查工具

功能：
- 关键信息抽取（合同主体、标的额、期限、违约责任、争议解决等）
- 四维度风险扫描（合规性、商业合理性、文本严谨性、程序完备性）
- 结构化结果输出（Markdown / JSON）
- 置信度标注（高/中/低）

本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入文本为空",
    "E002": "输入文本过短（少于10个字符）",
    "E003": "输出格式不支持（仅支持 markdown/json）",
    "E004": "JSON序列化失败",
    "E005": "文件读取失败",
    "E006": "URL格式无效",
    "E007": "文件类型不支持（仅支持 .txt/.docx/.pdf）",
    "E008": "内部逻辑错误",
    "E009": "参数解析错误",
    "E010": "未知错误",
}


@dataclass
class ContractInfo:
    """合同关键信息"""
    parties: List[str] = field(default_factory=list)      # 合同主体
    subject_amount: Optional[float] = None                 # 标的额
    contract_term: Optional[str] = None                    # 合同期限
    breach_liability: List[str] = field(default_factory=list)  # 违约责任
    dispute_resolution: Optional[str] = None               # 争议解决
    payment_terms: List[str] = field(default_factory=list) # 付款条款


@dataclass
class RiskItem:
    """风险项"""
    dimension: str          # 维度：合规性/商业合理性/文本严谨性/程序完备性
    risk_level: str         # 风险等级：高/中/低
    description: str        # 风险描述
    clause_text: str        # 条款原文（可能为空）
    suggestion: str         # 修改建议
    confidence: str         # 置信度：高/中/低


@dataclass
class ReviewReport:
    """审查报告"""
    contract_info: ContractInfo = field(default_factory=ContractInfo)
    risks: List[RiskItem] = field(default_factory=list)
    summary: str = ""
    overall_risk_level: str = "低"


class ContractReviewer:
    """合同审查核心引擎"""

    # 常见风险关键词库
    RISK_PATTERNS = {
        "合规性": {
            "high": [
                (r"违约金.{0,10}(?:30|百分之三十|百分之三十以上|畸高)", "违约金比例可能畸高"),
                (r"(?:违反|违背).{0,10}(?:法律|法规|强制性规定)", "可能存在违法条款"),
                (r"(?:无限责任|全部责任|一切责任)", "责任范围可能过宽"),
            ],
            "medium": [
                (r"(?:免责|豁免).{0,10}(?:全部|一切|任何)", "免责条款可能过于宽泛"),
                (r"(?:管辖|诉讼).{0,10}(?:异地|外地)", "管辖法院可能不利于本方"),
            ],
        },
        "商业合理性": {
            "high": [
                (r"付款.{0,10}(?:100%|全部|全额).{0,10}(?:预付|提前)", "付款条件可能过于苛刻"),
                (r"(?:价格|费用|金额).{0,10}(?:不明确|待定|另行协商)", "价格条款不明确"),
            ],
            "medium": [
                (r"(?:交付|履行).{0,10}(?:期限|时间).{0,10}(?:不明确|未约定)", "履行期限不明确"),
                (r"(?:数量|质量).{0,10}(?:标准|要求).{0,10}(?:未约定|不明确)", "质量标准缺失"),
            ],
        },
        "文本严谨性": {
            "high": [
                (r"(?:约|大概|左右|大约)", "存在模糊表述"),
                (r"(?:等|等等|其他)", "列举不完整"),
            ],
            "medium": [
                (r"(?:尽快|及时|合理时间)", "时间表述模糊"),
                (r"(?:相关|适当|合理)", "程度表述模糊"),
            ],
        },
        "程序完备性": {
            "high": [
                (r"(?:缺少|缺失|没有).{0,10}(?:保密|confidential)", "可能缺少保密条款"),
                (r"(?:缺少|缺失|没有).{0,10}(?:争议|纠纷).{0,10}(?:解决|处理)", "可能缺少争议解决条款"),
            ],
            "medium": [
                (r"(?:缺少|缺失|没有).{0,10}(?:通知|送达)", "可能缺少通知条款"),
                (r"(?:缺少|缺失|没有).{0,10}(?:变更|修改|补充)", "可能缺少变更条款"),
            ],
        },
    }

    # 必备条款检查
    REQUIRED_CLAUSES = [
        ("保密条款", r"(?:保密|confidential)", "程序完备性", "低"),
        ("争议解决条款", r"(?:争议|纠纷|仲裁|诉讼)", "程序完备性", "高"),
        ("违约责任条款", r"(?:违约|赔偿|责任)", "程序完备性", "高"),
        ("合同期限条款", r"(?:期限|有效期|生效|终止)", "程序完备性", "中"),
        ("付款条款", r"(?:付款|支付|价款|费用)", "商业合理性", "中"),
    ]

    def __init__(self, text: str):
        """初始化审查器

        Args:
            text: 合同文本内容

        Raises:
            ValueError: 当输入文本为空或过短时抛出
        """
        if not text or not text.strip():
            raise ValueError(ERROR_CODES["E001"])
        self.text = text.strip()
        if len(self.text) < 10:
            raise ValueError(ERROR_CODES["E002"])
        self.report = ReviewReport()

    def extract_info(self) -> ContractInfo:
        """提取合同关键信息

        Returns:
            ContractInfo: 提取的合同信息
        """
        info = ContractInfo()

        # 提取合同主体（甲方/乙方）- 更宽松的匹配模式
        party_patterns = [
            # 标准格式：甲方（买方）：公司名
            r"(?:甲方|买方|采购方|委托方)\s*[（(]\s*(?:买方|采购方|委托方)?\s*[）)]?\s*[：:]\s*([^\n，,；;]+)",
            r"(?:乙方|卖方|供应方|受托方)\s*[（(]\s*(?:卖方|供应方|受托方)?\s*[）)]?\s*[：:]\s*([^\n，,；;]+)",
            # 简化格式：甲方：公司名
            r"(?:甲方|买方|采购方|委托方)\s*[：:]\s*([^\n，,；;]+)",
            r"(?:乙方|卖方|供应方|受托方)\s*[：:]\s*([^\n，,；;]+)",
            # 带编号格式：1.甲方：公司名
            r"\d+[\.、]\s*(?:甲方|买方|采购方|委托方)\s*[：:]\s*([^\n，,；;]+)",
            r"\d+[\.、]\s*(?:乙方|卖方|供应方|受托方)\s*[：:]\s*([^\n，,；;]+)",
            # 丙方
            r"(?:丙方|第三方)\s*[：:]\s*([^\n，,；;]+)",
        ]
        
        for pattern in party_patterns:
            matches = re.findall(pattern, self.text)
            for match in matches:
                party = match.strip()
                # 清理可能的括号内容
                party = re.sub(r'[（(].*?[）)]', '', party).strip()
                if party and party not in info.parties:
                    info.parties.append(party)

        # 如果还没提取到，尝试更宽松的匹配
        if len(info.parties) < 2:
            # 匹配 "甲方：XXX" 或 "甲方 XXX" 格式
            alt_patterns = [
                r"甲方\s*(?:[:：]|\s+)\s*([^\n，,；;]{2,30})",
                r"乙方\s*(?:[:：]|\s+)\s*([^\n，,；;]{2,30})",
            ]
            for pattern in alt_patterns:
                matches = re.findall(pattern, self.text)
                for match in matches:
                    party = match.strip()
                    if party and party not in info.parties:
                        info.parties.append(party)

        # 提取标的额
        amount_patterns = [
            r"(?:标的额|合同金额|总金额|价款)[：:为]?\s*(?:人民币|RMB)?\s*([\d,，.]+)\s*(?:万元|元|万)",
            r"(?:金额|价款)[：:为]?\s*([\d,，.]+)\s*(?:万元|元)",
            r"合同金额为人民币\s*([\d,，.]+)\s*万元",
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, self.text)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "").replace("，", "")
                    amount = float(amount_str)
                    # 如果是"万元"则转换为元
                    if "万" in match.group(0):
                        amount *= 10000
                    info.subject_amount = amount
                    break
                except (ValueError, IndexError):
                    continue

        # 提取合同期限
        term_patterns = [
            r"(?:合同期限|有效期|合同期)[：:为]?\s*([^\n，,；;]+)",
            r"(?:自|从)\s*([^\n，,；;]+?)\s*(?:起|开始).{0,20}(?:至|到)\s*([^\n，,；;]+?)(?:\s*止|为止)?",
        ]
        for pattern in term_patterns:
            match = re.search(pattern, self.text)
            if match:
                if pattern == term_patterns[0]:
                    info.contract_term = match.group(1).strip()
                else:
                    info.contract_term = f"{match.group(1).strip()}至{match.group(2).strip()}"
                break

        # 提取违约责任相关条款
        breach_pattern = r"(?:违约责任|违约条款)[：:]?\s*([^\n]+(?:\n[^\n]+){0,2})"
        match = re.search(breach_pattern, self.text)
        if match:
            info.breach_liability.append(match.group(1).strip())

        # 提取争议解决条款
        dispute_patterns = [
            r"(?:争议解决|纠纷解决)[：:]?\s*([^\n]+)",
            r"(?:仲裁|诉讼)[：:]?\s*([^\n]+)",
        ]
        for pattern in dispute_patterns:
            match = re.search(pattern, self.text)
            if match:
                info.dispute_resolution = match.group(1).strip()
                break

        # 提取付款条款
        payment_pattern = r"(?:付款|支付)[：:]?\s*([^\n]+(?:\n[^\n]+){0,2})"
        match = re.search(payment_pattern, self.text)
        if match:
            info.payment_terms.append(match.group(1).strip())

        self.report.contract_info = info
        return info

    def scan_risks(self) -> List[RiskItem]:
        """扫描风险点

        Returns:
            List[RiskItem]: 风险项列表
        """
        risks = []
        text_lower = self.text.lower()

        # 按维度扫描风险模式
        for dimension, levels in self.RISK_PATTERNS.items():
            for risk_level, patterns in levels.items():
                for pattern, description in patterns:
                    if re.search(pattern, self.text, re.IGNORECASE):
                        # 提取匹配的条款原文
                        match = re.search(pattern, self.text, re.IGNORECASE)
                        clause_text = ""
                        if match:
                            start = max(0, match.start() - 20)
                            end = min(len(self.text), match.end() + 20)
                            clause_text = self.text[start:end].replace("\n", " ")

                        risks.append(RiskItem(
                            dimension=dimension,
                            risk_level=risk_level,
                            description=description,
                            clause_text=clause_text,
                            suggestion=self._generate_suggestion(dimension, description),
                            confidence="高" if risk_level == "high" else "中",
                        ))

        # 检查必备条款
        for clause_name, pattern, dimension, importance in self.REQUIRED_CLAUSES:
            if not re.search(pattern, text_lower):
                risks.append(RiskItem(
                    dimension=dimension,
                    risk_level=importance,
                    description=f"缺少{clause_name}",
                    clause_text="",
                    suggestion=f"建议补充{clause_name}相关约定",
                    confidence="中",
                ))

        self.report.risks = risks
        self._calculate_overall_risk()
        return risks

    def _generate_suggestion(self, dimension: str, description: str) -> str:
        """根据风险描述生成修改建议

        Args:
            dimension: 风险维度
            description: 风险描述

        Returns:
            str: 修改建议
        """
        suggestions = {
            "违约金比例可能畸高": "建议将违约金比例调整至合理范围（一般为合同金额的20%-30%），并参考实际损失确定",
            "可能存在违法条款": "建议删除或修改违反法律法规强制性规定的条款，确保合同合法性",
            "责任范围可能过宽": "建议明确责任范围，避免无限责任，可设置责任上限",
            "免责条款可能过于宽泛": "建议限定免责条款的适用范围和条件",
            "管辖法院可能不利于本方": "建议协商约定对己方有利的管辖法院或仲裁机构",
            "付款条件可能过于苛刻": "建议调整付款比例和节点，增加验收环节后再付款",
            "价格条款不明确": "建议明确价格、费用金额及计算方式",
            "履行期限不明确": "建议明确约定履行期限和交付时间节点",
            "质量标准缺失": "建议明确约定质量标准、验收标准和验收方式",
            "存在模糊表述": "建议将模糊表述改为具体明确的数字或标准",
            "列举不完整": "建议使用'包括但不限于'或完整列举相关事项",
            "时间表述模糊": "建议明确具体时间或期限，避免使用模糊时间词",
            "程度表述模糊": "建议明确具体标准或量化指标",
            "可能缺少保密条款": "建议增加保密条款，明确保密范围和期限",
            "可能缺少争议解决条款": "建议增加争议解决条款，明确管辖法院或仲裁机构",
            "可能缺少通知条款": "建议增加通知条款，明确通知方式和送达地址",
            "可能缺少变更条款": "建议增加合同变更条款，明确变更程序和条件",
        }
        return suggestions.get(description, f"建议审查并优化：{description}")

    def _calculate_overall_risk(self) -> str:
        """计算整体风险等级

        Returns:
            str: 整体风险等级
        """
        if not self.report.risks:
            self.report.overall_risk_level = "低"
            return "低"

        high_count = sum(1 for r in self.report.risks if r.risk_level == "高")
        medium_count = sum(1 for r in self.report.risks if r.risk_level == "中")

        if high_count > 0:
            self.report.overall_risk_level = "高"
        elif medium_count >= 3:
            self.report.overall_risk_level = "中"
        else:
            self.report.overall_risk_level = "低"

        # 生成摘要
        self.report.summary = (
            f"共发现{len(self.report.risks)}个风险点，"
            f"其中高风险{high_count}个，中风险{medium_count}个，"
            f"整体风险等级：{self.report.overall_risk_level}"
        )
        return self.report.overall_risk_level

    def generate_report(self, output_format: str = "markdown") -> str:
        """生成审查报告

        Args:
            output_format: 输出格式，支持 markdown/json

        Returns:
            str: 格式化后的报告

        Raises:
            ValueError: 当输出格式不支持时抛出
        """
        if output_format not in ("markdown", "json"):
            raise ValueError(ERROR_CODES["E003"])

        if output_format == "json":
            return self._generate_json_report()
        return self._generate_markdown_report()

    def _generate_markdown_report(self) -> str:
        """生成 Markdown 格式报告"""
        lines = []
        lines.append("# 合同审查报告")
        lines.append("")
        lines.append(f"## 整体风险等级：{self.report.overall_risk_level}")
        lines.append("")
        lines.append(f"> {self.report.summary}")
        lines.append("")

        # 关键信息
        info = self.report.contract_info
        lines.append("## 关键信息")
        lines.append("")
        if info.parties:
            lines.append(f"- **合同主体**：{', '.join(info.parties)}")
        if info.subject_amount is not None:
            lines.append(f"- **标的额**：{info.subject_amount:,.2f} 元")
        if info.contract_term:
            lines.append(f"- **合同期限**：{info.contract_term}")
        if info.dispute_resolution:
            lines.append(f"- **争议解决**：{info.dispute_resolution}")
        if info.payment_terms:
            lines.append(f"- **付款条款**：{'；'.join(info.payment_terms[:3])}")
        lines.append("")

        # 风险列表
        if self.report.risks:
            lines.append("## 风险清单")
            lines.append("")
            for i, risk in enumerate(self.report.risks, 1):
                lines.append(f"### 风险 {i}：{risk.description}")
                lines.append("")
                lines.append(f"- **维度**：{risk.dimension}")
                lines.append(f"- **风险等级**：{risk.risk_level}")
                lines.append(f"- **置信度**：{risk.confidence}")
                if risk.clause_text:
                    lines.append(f"- **条款原文**：> {risk.clause_text}")
                lines.append(f"- **修改建议**：{risk.suggestion}")
                lines.append("")

        lines.append("---")
        lines.append("*本报告由 AI 辅助生成，仅供学习参考，不构成正式法律意见。*")
        return "\n".join(lines)

    def _generate_json_report(self) -> str:
        """生成 JSON 格式报告"""
        try:
            report_dict = {
                "overall_risk_level": self.report.overall_risk_level,
                "summary": self.report.summary,
                "contract_info": asdict(self.report.contract_info),
                "risks": [asdict(risk) for risk in self.report.risks],
                "disclaimer": "本报告由 AI 辅助生成，仅供学习参考，不构成正式法律意见。",
            }
            return json.dumps(report_dict, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            raise ValueError(ERROR_CODES["E004"]) from e


def run_selftest() -> bool:
    """内置自检函数，使用硬编码样例数据验证核心逻辑

    Returns:
        bool: 自检是否通过
    """
    print("开始自检...")

    # 硬编码测试样例1：正常合同
    sample_text_1 = """
    采购合同

    甲方（买方）：北京科技有限公司
    乙方（卖方）：上海信息技术有限公司

    第一条 合同标的
    乙方同意向甲方提供企业管理系统软件一套，合同金额为人民币100万元。

    第二条 合同期限
    本合同自2026年1月1日起至2026年12月31日止。

    第三条 付款方式
    合同签订后7日内，甲方向乙方支付合同金额的30%作为预付款。
    系统验收合格后15日内，甲方向乙方支付剩余70%款项。

    第四条 违约责任
    任何一方违反本合同约定，应向守约方支付违约金，违约金金额为合同金额的20%。

    第五条 保密条款
    双方应对本合同内容及履行过程中知悉的对方商业秘密负有保密义务。

    第六条 争议解决
    因本合同引起的争议，双方应友好协商解决；协商不成的，提交北京仲裁委员会仲裁。

    第七条 其他
    本合同一式两份，双方各执一份，具有同等法律效力。
    """

    # 硬编码测试样例2：有风险合同
    sample_text_2 = """
    合作协议

    甲方：某公司
    乙方：某个人

    双方就合作事宜达成如下协议：
    1. 合作期限约为一年。
    2. 甲方尽快向乙方支付相关费用。
    3. 乙方对合作内容承担一切责任。
    4. 违约金比例大约为百分之五十。
    5. 本协议未尽事宜，双方另行协商。

    本协议自双方签字之日起生效。
    """

    try:
        # 测试1：正常合同
        reviewer1 = ContractReviewer(sample_text_1)
        info1 = reviewer1.extract_info()
        risks1 = reviewer1.scan_risks()

        # 宽松断言：正常合同应该能提取到主体
        assert len(info1.parties) >= 2, f"应提取到至少两个合同主体，实际提取到{len(info1.parties)}个: {info1.parties}"
        # 宽松断言：应该能提取到金额
        assert info1.subject_amount is not None, "应提取到标的额"
        assert info1.subject_amount > 0, "标的额应为正数"
        # 宽松断言：正常合同风险数应较少（小于有风险合同）
        assert len(risks1) < 5, f"正常合同风险数应较少，实际{len(risks1)}个"

        # 测试2：有风险合同
        reviewer2 = ContractReviewer(sample_text_2)
        info2 = reviewer2.extract_info()
        risks2 = reviewer2.scan_risks()

        # 宽松断言：有风险合同应发现更多风险
        assert len(risks2) > len(risks1), f"有风险合同应发现更多风险点，实际{len(risks2)} vs {len(risks1)}"
        # 宽松断言：应识别出高风险项
        high_risks = [r for r in risks2 if r.risk_level == "高"]
        assert len(high_risks) > 0, "应识别出高风险项"

        # 测试3：报告生成
        md_report = reviewer1.generate_report("markdown")
        json_report = reviewer1.generate_report("json")

        # 宽松断言：报告应包含关键内容
        assert "合同审查报告" in md_report, "Markdown报告应包含标题"
        assert len(md_report) > 100, "Markdown报告应有足够内容"
        assert len(json_report) > 50, "JSON报告应有足够内容"

        # 测试4：异常处理
        try:
            ContractReviewer("")
            assert False, "空文本应抛出异常"
        except ValueError:
            pass

        try:
            reviewer1.generate_report("xml")
            assert False, "不支持格式应抛出异常"
        except ValueError:
            pass

        print("自检通过：所有断言均成功")
        return True

    except AssertionError as e:
        print(f"自检失败：{e}")
        return False
    except Exception as e:
        print(f"自检异常：{e}")
        return False


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="合同智审 - 多维度智能合同审查工具",
        epilog="示例：python main.py --file contract.txt --format markdown"
    )
    parser.add_argument(
        "--file", "-f",
        help="合同文件路径（支持 .txt）"
    )
    parser.add_argument(
        "--text", "-t",
        help="直接输入合同文本"
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认：markdown）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 检查输入
    if not args.file and not args.text:
        parser.error("请提供合同文本（--text）或文件路径（--file）")

    try:
        # 获取文本
        if args.text:
            text = args.text
        else:
            if not args.file.endswith(".txt"):
                raise ValueError(ERROR_CODES["E007"])
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text = f.read()
            except (IOError, OSError) as e:
                raise ValueError(ERROR_CODES["E005"]) from e

        # 执行审查
        reviewer = ContractReviewer(text)
        reviewer.extract_info()
        reviewer.scan_risks()

        # 输出报告
        report = reviewer.generate_report(args.format)
        print(report)

    except ValueError as e:
        # 将错误消息映射到错误码
        error_code = "E010"
        for code, message in ERROR_CODES.items():
            if message == str(e):
                error_code = code
                break
        print(f"错误[{error_code}]：{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误[E010]：未知错误 - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
