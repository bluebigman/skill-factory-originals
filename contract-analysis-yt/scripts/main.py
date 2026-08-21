#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同审查与风险识别工具 (contract-analysis-yt)

独立实现版本，基于功能规格 clean-room 重写。
提供合同文本解析、风险点识别、合规性初检和结构化报告输出。
仅依赖标准库，支持离线自检。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 常量定义
# ============================================================

# 错误码定义
ERROR_CODES = {
    "E001": "输入文本为空或格式错误",
    "E002": "无法解析合同主体信息",
    "E003": "无法识别合同金额或期限",
    "E004": "风险分析过程异常",
    "E005": "报告生成失败",
    "E006": "输入类型不支持（仅支持字符串或文件路径）",
    "E007": "文件读取失败",
    "E008": "JSON 序列化失败",
    "E009": "自定义规则格式错误",
    "E010": "未预期的内部错误",
}

# 常见风险关键词及其风险等级（权重）
RISK_KEYWORDS = {
    "违约金": {"weight": 2, "level": "中", "suggestion": "建议核实违约金比例是否过高，是否与损失相当。"},
    "单方解除": {"weight": 3, "level": "高", "suggestion": "单方解除权可能导致权利义务不对等，建议明确行使条件和补偿机制。"},
    "免责": {"weight": 2, "level": "中", "suggestion": "免责条款需确保不违反法律强制性规定，建议明确免责范围。"},
    "保密": {"weight": 1, "level": "低", "suggestion": "保密条款建议明确保密期限、范围和违约责任。"},
    "知识产权": {"weight": 2, "level": "中", "suggestion": "建议明确知识产权归属、使用范围和收益分配。"},
    "付款": {"weight": 1, "level": "低", "suggestion": "建议核实付款条件、时间和方式是否合理。"},
    "解除": {"weight": 2, "level": "中", "suggestion": "解除条件需明确具体情形，避免歧义。"},
    "赔偿": {"weight": 2, "level": "中", "suggestion": "赔偿范围与标准建议量化，避免争议。"},
    "管辖": {"weight": 2, "level": "中", "suggestion": "管辖条款建议选择明确、便利的法院或仲裁机构。"},
    "不可抗力": {"weight": 1, "level": "低", "suggestion": "不可抗力定义与后果处理建议明确。"},
    "自动续约": {"weight": 2, "level": "中", "suggestion": "自动续约条款建议设置提醒机制或退出机制。"},
    "违约金过高": {"weight": 3, "level": "高", "suggestion": "违约金可能被认定为过高，建议参考实际损失调整。"},
    "权利义务不对等": {"weight": 3, "level": "高", "suggestion": "建议平衡双方权利义务，避免显失公平。"},
    "缺少社保": {"weight": 3, "level": "高", "suggestion": "劳动合同必须包含社保条款，否则违法。"},
    "试用期过长": {"weight": 2, "level": "中", "suggestion": "试用期长度需符合法律规定，建议核实。"},
}

# 合规性检查关键词（对应常见法规要求）
COMPLIANCE_KEYWORDS = {
    "民法典": ["合同", "诚实信用", "公平"],
    "劳动法": ["社保", "工资", "工时", "休假", "解除"],
    "数据安全法": ["数据", "隐私", "安全"],
    "消费者权益保护法": ["消费者", "退款", "质量"],
}

# 合同类型关键词
CONTRACT_TYPE_KEYWORDS = {
    "采购合同": ["采购", "供应", "货物"],
    "销售合同": ["销售", "出售", "买方"],
    "劳动合同": ["劳动", "聘用", "工资", "社保"],
    "租赁合同": ["租赁", "出租", "承租"],
    "服务合同": ["服务", "咨询", "委托"],
    "保密协议": ["保密", "机密", "NDA"],
    "技术合同": ["技术", "开发", "知识产权"],
}

# 默认自定义规则（可被用户覆盖）
DEFAULT_RULES = {
    "风险关键词": RISK_KEYWORDS,
    "合规关键词": COMPLIANCE_KEYWORDS,
}


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ContractElement:
    """合同要素"""
    contract_type: str = ""
    parties: List[str] = field(default_factory=list)
    amount: Optional[float] = None
    amount_text: str = ""
    duration: Optional[str] = None
    key_terms: List[str] = field(default_factory=list)


@dataclass
class RiskItem:
    """风险点"""
    keyword: str
    level: str
    context: str
    suggestion: str
    location: Optional[int] = None


@dataclass
class ComplianceItem:
    """合规性检查项"""
    law: str
    status: str  # "通过" / "需关注" / "未覆盖"
    detail: str


@dataclass
class ContractReport:
    """结构化审查报告"""
    meta: Dict[str, str] = field(default_factory=dict)
    elements: ContractElement = field(default_factory=ContractElement)
    risks: List[RiskItem] = field(default_factory=list)
    compliance: List[ComplianceItem] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)


# ============================================================
# 核心处理函数
# ============================================================

def validate_input(text: str) -> None:
    """校验输入文本"""
    if not text or not text.strip():
        raise ValueError(f"[{ERROR_CODES['E001']}] 输入文本为空")


def extract_contract_type(text: str) -> str:
    """识别合同类型"""
    for ctype, keywords in CONTRACT_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return ctype
    return "未识别"


def extract_parties(text: str) -> List[str]:
    """提取合同主体（甲方/乙方）"""
    parties = []
    # 匹配 "甲方：XXX" 或 "乙方：XXX"
    pattern = r"(?:甲方|乙方|买方|卖方|出租方|承租方|雇主|雇员|委托方|受托方)\s*[:：]\s*([^\n,，。;；]+)"
    matches = re.findall(pattern, text)
    for m in matches:
        name = m.strip()
        if name and name not in parties:
            parties.append(name)
    return parties


def extract_amount(text: str) -> Tuple[Optional[float], str]:
    """提取合同金额"""
    # 匹配 人民币/元 后的数字
    patterns = [
        r"(?:人民币|RMB|￥|¥)?\s*([0-9,]+\.?[0-9]*)\s*(?:万元|万|元)",
        r"(?:金额|总价|价款|费用)[^\d]*([0-9,]+\.?[0-9]*)\s*(?:万元|万|元)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 取第一个匹配
            raw = matches[0].replace(",", "")
            try:
                amount = float(raw)
                # 如果是"万元"需要转换
                if "万" in text[max(0, text.find(raw)-5):text.find(raw)+5]:
                    amount *= 10000
                return amount, f"{amount:,.2f}"
            except ValueError:
                continue
    return None, ""


def extract_duration(text: str) -> Optional[str]:
    """提取合同期限"""
    patterns = [
        r"(?:期限|有效期|合同期)[^\d]*(\d+)\s*(?:年|个月|日|天)",
        r"(?:自|从)\s*(\d{4}年\d{1,2}月\d{1,2}日)\s*(?:至|到)\s*(\d{4}年\d{1,2}月\d{1,2}日)",
    ]
    for pattern in patterns:
        matches = re.search(pattern, text)
        if matches:
            return matches.group(0)
    return None


def extract_key_terms(text: str) -> List[str]:
    """提取关键条款（包含风险关键词的句子）"""
    terms = []
    sentences = re.split(r"[。；\n]", text)
    for sent in sentences:
        for kw in RISK_KEYWORDS:
            if kw in sent and sent not in terms:
                terms.append(sent.strip())
                break
    return terms[:10]  # 最多返回10条


def parse_contract(text: str) -> ContractElement:
    """解析合同文本，提取关键要素"""
    try:
        validate_input(text)
        element = ContractElement()
        element.contract_type = extract_contract_type(text)
        element.parties = extract_parties(text)
        amount, amount_text = extract_amount(text)
        element.amount = amount
        element.amount_text = amount_text
        element.duration = extract_duration(text)
        element.key_terms = extract_key_terms(text)
        return element
    except ValueError as e:
        # 确保错误消息包含错误码
        error_msg = str(e)
        if not any(code in error_msg for code in ERROR_CODES):
            error_msg = f"[{ERROR_CODES['E002']}] {error_msg}"
        raise RuntimeError(error_msg)
    except Exception:
        raise RuntimeError(f"[{ERROR_CODES['E002']}] 合同解析失败")


def analyze_risks(text: str, rules: Dict = None) -> List[RiskItem]:
    """识别风险点"""
    risks = []
    if rules is None:
        rules = DEFAULT_RULES["风险关键词"]
    
    try:
        sentences = re.split(r"[。；\n]", text)
        for idx, sent in enumerate(sentences):
            for kw, config in rules.items():
                if kw in sent:
                    risk = RiskItem(
                        keyword=kw,
                        level=config.get("level", "中"),
                        context=sent.strip()[:100],
                        suggestion=config.get("suggestion", "建议人工复核该条款。"),
                        location=idx,
                    )
                    risks.append(risk)
        return risks
    except Exception:
        raise RuntimeError(f"[{ERROR_CODES['E004']}] 风险分析失败")


def check_compliance(text: str, rules: Dict = None) -> List[ComplianceItem]:
    """合规性初检"""
    items = []
    if rules is None:
        rules = DEFAULT_RULES["合规关键词"]
    
    try:
        for law, keywords in rules.items():
            found = [kw for kw in keywords if kw in text]
            if len(found) >= 2:
                status = "通过"
                detail = f"已覆盖关键词: {', '.join(found)}"
            elif len(found) == 1:
                status = "需关注"
                detail = f"仅覆盖: {found[0]}，建议补充相关条款"
            else:
                status = "未覆盖"
                detail = "未发现相关条款，建议核查是否符合该法规要求"
            items.append(ComplianceItem(law=law, status=status, detail=detail))
        return items
    except Exception:
        raise RuntimeError(f"[{ERROR_CODES['E004']}] 合规检查失败")


def generate_report(text: str, custom_rules: Dict = None) -> ContractReport:
    """生成完整审查报告"""
    try:
        # 解析合同要素
        elements = parse_contract(text)
        
        # 合并默认规则和自定义规则
        risk_rules = DEFAULT_RULES["风险关键词"]
        compliance_rules = DEFAULT_RULES["合规关键词"]
        if custom_rules:
            if "风险关键词" in custom_rules:
                risk_rules = custom_rules["风险关键词"]
            if "合规关键词" in custom_rules:
                compliance_rules = custom_rules["合规关键词"]
        
        # 风险分析
        risks = analyze_risks(text, risk_rules)
        
        # 合规检查
        compliance = check_compliance(text, compliance_rules)
        
        # 风险等级统计
        level_count = {"高": 0, "中": 0, "低": 0}
        for r in risks:
            level_count[r.level] = level_count.get(r.level, 0) + 1
        
        # 构建报告
        report = ContractReport(
            meta={
                "合同类型": elements.contract_type,
                "合同主体数": str(len(elements.parties)),
                "主体列表": ", ".join(elements.parties) if elements.parties else "未识别",
                "金额": elements.amount_text if elements.amount_text else "未识别",
                "期限": elements.duration if elements.duration else "未识别",
            },
            elements=elements,
            risks=risks,
            compliance=compliance,
            summary={
                "总风险数": len(risks),
                "高风险": level_count.get("高", 0),
                "中风险": level_count.get("中", 0),
                "低风险": level_count.get("低", 0),
                "合规通过": sum(1 for c in compliance if c.status == "通过"),
                "合规需关注": sum(1 for c in compliance if c.status == "需关注"),
                "合规未覆盖": sum(1 for c in compliance if c.status == "未覆盖"),
            },
        )
        return report
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"[{ERROR_CODES['E005']}] 报告生成失败: {str(e)}")


def report_to_json(report: ContractReport) -> str:
    """报告转 JSON 字符串"""
    try:
        return json.dumps(asdict(report), ensure_ascii=False, indent=2)
    except Exception:
        raise RuntimeError(f"[{ERROR_CODES['E008']}] JSON 序列化失败")


def report_to_markdown(report: ContractReport) -> str:
    """报告转 Markdown 格式"""
    try:
        lines = []
        lines.append("# 合同审查报告\n")
        
        # 元信息
        lines.append("## 基本信息")
        for k, v in report.meta.items():
            lines.append(f"- **{k}**: {v}")
        
        # 风险点
        lines.append("\n## 风险点识别")
        if report.risks:
            for i, risk in enumerate(report.risks, 1):
                lines.append(f"### 风险 {i} [{risk.level}]")
                lines.append(f"- **关键词**: {risk.keyword}")
                lines.append(f"- **上下文**: {risk.context}")
                lines.append(f"- **建议**: {risk.suggestion}")
        else:
            lines.append("未发现明显风险点。")
        
        # 合规性
        lines.append("\n## 合规性检查")
        for item in report.compliance:
            icon = {"通过": "✅", "需关注": "⚠️", "未覆盖": "❌"}.get(item.status, "❓")
            lines.append(f"- {icon} **{item.law}**: {item.status} - {item.detail}")
        
        # 总结
        lines.append("\n## 总结")
        lines.append(f"- 总风险数: {report.summary.get('总风险数', 0)}")
        lines.append(f"- 高风险: {report.summary.get('高风险', 0)}")
        lines.append(f"- 中风险: {report.summary.get('中风险', 0)}")
        lines.append(f"- 低风险: {report.summary.get('低风险', 0)}")
        
        return "\n".join(lines)
    except Exception:
        raise RuntimeError(f"[{ERROR_CODES['E005']}] Markdown 生成失败")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """内置硬编码样例数据，离线自检核心逻辑"""
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)
    
    # 硬编码测试数据
    sample_text = """
    采购合同
    
    甲方：北京某某科技有限公司
    乙方：上海某某供应链有限公司
    
    第一条 合同标的
    甲方向乙方采购一批办公设备，合同总金额为人民币50万元。
    
    第二条 付款方式
    甲方在收到货物后30日内支付全款，付款条件较为苛刻。
    
    第三条 违约责任
    若乙方延迟交货，需向甲方支付违约金，违约金比例为合同金额的30%。
    甲方拥有单方解除权，且不承担任何赔偿责任。
    
    第四条 保密条款
    双方应对本合同内容进行保密，保密期限为合同终止后3年。
    
    第五条 知识产权
    乙方开发的相关软件知识产权归甲方所有。
    
    第六条 合同期限
    本合同有效期为2年，自2026年1月1日起至2027年12月31日止。
    合同期满前30日，若双方未提出异议，合同自动续约。
    
    第七条 争议解决
    双方发生争议时，提交北京市仲裁委员会仲裁。
    
    第八条 不可抗力
    因不可抗力导致无法履行合同的，双方互不承担责任。
    """
    
    try:
        # 1. 测试合同解析
        print("\n[1/5] 测试合同解析...")
        element = parse_contract(sample_text)
        assert element.contract_type == "采购合同", f"合同类型识别错误: {element.contract_type}"
        assert len(element.parties) >= 2, f"应识别至少2个合同主体，实际: {len(element.parties)}"
        assert element.amount is not None, "未能识别合同金额"
        assert element.amount > 0, f"金额应为正数，实际: {element.amount}"
        assert element.duration is not None, "未能识别合同期限"
        print("  ✅ 合同解析通过")
        print(f"     - 类型: {element.contract_type}")
        print(f"     - 主体: {element.parties}")
        print(f"     - 金额: {element.amount_text}")
        print(f"     - 期限: {element.duration}")
        
        # 2. 测试风险识别
        print("\n[2/5] 测试风险识别...")
        risks = analyze_risks(sample_text)
        assert len(risks) > 0, "应识别出至少1个风险点"
        risk_keywords = [r.keyword for r in risks]
        assert "违约金" in risk_keywords, "未识别'违约金'风险"
        assert "单方解除" in risk_keywords, "未识别'单方解除'风险"
        print(f"  ✅ 风险识别通过，共识别 {len(risks)} 个风险点")
        print(f"     - 风险关键词: {risk_keywords[:5]}")
        
        # 3. 测试合规检查
        print("\n[3/5] 测试合规检查...")
        compliance = check_compliance(sample_text)
        assert len(compliance) > 0, "合规检查结果为空"
        laws = [c.law for c in compliance]
        assert "民法典" in laws, "缺少民法典检查项"
        print(f"  ✅ 合规检查通过，共 {len(compliance)} 项")
        for c in compliance:
            print(f"     - {c.law}: {c.status}")
        
        # 4. 测试完整报告生成
        print("\n[4/5] 测试完整报告生成...")
        report = generate_report(sample_text)
        assert report.summary["总风险数"] > 0, "报告风险数为0"
        assert report.summary["高风险"] > 0, "应存在高风险项"
        assert len(report.compliance) > 0, "合规检查为空"
        print("  ✅ 报告生成通过")
        print(f"     - 风险总数: {report.summary['总风险数']}")
        print(f"     - 高风险: {report.summary['高风险']}, 中风险: {report.summary['中风险']}, 低风险: {report.summary['低风险']}")
        
        # 5. 测试 JSON 和 Markdown 输出
        print("\n[5/5] 测试输出格式...")
        json_str = report_to_json(report)
        assert json_str and len(json_str) > 0, "JSON 输出为空"
        md_str = report_to_markdown(report)
        assert md_str and len(md_str) > 0, "Markdown 输出为空"
        print("  ✅ JSON 输出通过")
        print("  ✅ Markdown 输出通过")
        
        # 额外测试：异常处理
        print("\n[额外] 测试错误处理...")
        try:
            parse_contract("")
            raise AssertionError("空文本应抛出异常")
        except RuntimeError as e:
            assert "E001" in str(e), f"错误码错误: {e}"
        print("  ✅ 空文本错误码 E001 通过")
        
        try:
            generate_report("这是没有合同内容的普通文本")
            print("  ✅ 普通文本处理通过")
        except RuntimeError as e:
            print(f"  ⚠️ 普通文本处理警告: {e}")
        
        print("\n" + "=" * 60)
        print("所有自检通过 ✅")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {e}")
        return False


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="合同审查与风险识别工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --text "合同内容..."
  python main.py --file contract.txt
  python main.py --selftest
  python main.py --text "..." --format json --output report.json
  python main.py --text "..." --rules custom_rules.json
        """,
    )
    
    parser.add_argument("--text", type=str, help="直接传入合同文本")
    parser.add_argument("--file", type=str, help="从文件读取合同文本")
    parser.add_argument("--format", choices=["json", "markdown", "both"], default="markdown", help="输出格式")
    parser.add_argument("--output", type=str, help="输出文件路径（可选）")
    parser.add_argument("--rules", type=str, help="自定义规则 JSON 文件路径（可选）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 获取输入文本
    text = ""
    try:
        if args.text:
            text = args.text
        elif args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                print(f"[{ERROR_CODES['E007']}] 文件读取失败: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            parser.print_help()
            sys.exit(0)
        
        # 加载自定义规则
        custom_rules = None
        if args.rules:
            try:
                with open(args.rules, "r", encoding="utf-8") as f:
                    custom_rules = json.load(f)
            except Exception as e:
                print(f"[{ERROR_CODES['E009']}] 自定义规则加载失败: {e}", file=sys.stderr)
                sys.exit(1)
        
        # 生成报告
        report = generate_report(text, custom_rules)
        
        # 输出
        output = ""
        if args.format in ("json", "both"):
            output += report_to_json(report)
            if args.format == "both":
                output += "\n\n---\n\n"
        if args.format in ("markdown", "both"):
            output += report_to_markdown(report)
        
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"报告已保存到: {args.output}")
        else:
            print(output)
            
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[{ERROR_CODES['E010']}] 未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
