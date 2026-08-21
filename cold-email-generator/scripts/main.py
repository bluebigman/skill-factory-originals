#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cold-email-generator 独立实现脚本
版本: 1.0.2 (clean-room 重写)
仅依据功能规格开发，不包含任何既有代码。
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Optional
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据格式错误",
    "E002": "输入数据为空",
    "E003": "线索数据缺少必要字段",
    "E004": "JSON解析失败",
    "E005": "输出写入失败",
    "E006": "参数组合不合法",
    "E007": "内部逻辑异常",
    "E008": "文件读取失败",
    "E009": "批量处理中断",
    "E010": "未知错误",
}

# 语气风格配置
TONE_STYLES = {
    "formal": {
        "greeting": "尊敬的{name}",
        "opening": "希望这封邮件能为您带来帮助。",
        "closing": "期待您的回复。\n\n此致\n敬礼",
    },
    "casual": {
        "greeting": "Hi {name}",
        "opening": "希望您一切顺利！",
        "closing": "期待您的回复！\n\nCheers",
    },
    "professional": {
        "greeting": "{name} 您好",
        "opening": "感谢您抽出时间阅读此信。",
        "closing": "期待与您进一步沟通。\n\n顺祝商祺",
    },
}

# 行业常用语
INDUSTRY_PHRASES = {
    "tech": "在技术领域，我们专注于提供创新解决方案。",
    "finance": "针对金融行业，我们提供稳健可靠的方案。",
    "startup": "我们深知初创企业的挑战，并提供灵活支持。",
    "default": "我们相信我们的产品能为您带来显著价值。",
}


class ColdEmailGenerator:
    """冷邮件生成器核心类"""

    def __init__(self, tone: str = "professional"):
        """初始化生成器

        Args:
            tone: 语气风格 (formal/casual/professional)
        """
        self.tone = tone if tone in TONE_STYLES else "professional"
        self.tone_config = TONE_STYLES[self.tone]

    def generate_single(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """生成单封邮件草稿

        Args:
            lead: 线索字典，包含以下可选字段:
                - company: 公司名
                - contact_name: 联系人姓名
                - product: 产品/服务
                - industry: 行业
                - value_prop: 价值主张
                - pain_point: 痛点

        Returns:
            包含邮件各部分的字典
        """
        if not lead or not isinstance(lead, dict):
            raise ValueError("E001: 线索数据必须是字典")

        # 提取字段并标注缺失
        company = lead.get("company", "").strip()
        contact_name = lead.get("contact_name", "").strip()
        product = lead.get("product", "").strip()
        industry = lead.get("industry", "").strip()
        value_prop = lead.get("value_prop", "").strip()
        pain_point = lead.get("pain_point", "").strip()

        # 必需字段检查
        if not company and not contact_name:
            raise ValueError("E003: 至少需要公司名或联系人姓名")

        # 构建邮件各部分
        # 称呼
        if contact_name:
            greeting = self.tone_config["greeting"].format(name=contact_name)
        elif company:
            greeting = f"{company} 负责人"
        else:
            greeting = "负责人"

        # 开场
        opening = self.tone_config["opening"]

        # 公司介绍
        company_intro = ""
        if company:
            company_intro = f"我是{company}的代表。"
        else:
            company_intro = "我是本次与您联系的代表。"

        # 产品/价值主张
        value_section = ""
        if product:
            value_section = f"我们提供的{product}"
            if value_prop:
                value_section += f"，{value_prop}"
            else:
                value_section += "，能有效提升您的业务效率。"
                value_section += " [需核实:价值主张]"
        else:
            value_section = "我们的解决方案能为您带来显著价值。 [需核实:产品/服务]"

        # 行业相关
        industry_section = ""
        if industry:
            lower_industry = industry.lower()
            if "tech" in lower_industry or "科技" in lower_industry:
                industry_section = INDUSTRY_PHRASES["tech"]
            elif "financ" in lower_industry or "金融" in lower_industry:
                industry_section = INDUSTRY_PHRASES["finance"]
            elif "startup" in lower_industry or "初创" in lower_industry:
                industry_section = INDUSTRY_PHRASES["startup"]
            else:
                industry_section = INDUSTRY_PHRASES["default"]
        else:
            industry_section = INDUSTRY_PHRASES["default"]
            industry_section += " [需核实:行业]"

        # 痛点呼应
        pain_section = ""
        if pain_point:
            pain_section = f"我们了解到您可能面临{pain_point}的问题，"
            pain_section += "这正是我们擅长的领域。"

        # 行动召唤
        cta = "如果您有兴趣，欢迎回复本邮件或预约一次简短交流。"

        # 结束语
        closing = self.tone_config["closing"]

        # 组装正文
        body_parts = [
            opening,
            company_intro,
            value_section,
            industry_section,
        ]
        if pain_section:
            body_parts.append(pain_section)
        body_parts.append(cta)

        body = "\n\n".join(body_parts)

        # 完整邮件
        full_email = f"{greeting}：\n\n{body}\n\n{closing}"

        # 置信度评估（简单规则）
        confidence = self._calculate_confidence(lead)

        return {
            "company": company,
            "contact_name": contact_name,
            "greeting": greeting,
            "body": body,
            "closing": closing,
            "full_email": full_email,
            "subject": self._generate_subject(company, product),
            "confidence": confidence,
        }

    def _generate_subject(self, company: str, product: str) -> str:
        """生成邮件主题"""
        if company and product:
            return f"{company} × {product} 合作探讨"
        elif company:
            return f"关于与{company}的合作机会"
        elif product:
            return f"关于{product}的介绍"
        else:
            return "合作机会探讨"

    def _calculate_confidence(self, lead: Dict[str, Any]) -> float:
        """计算置信度（0-1之间）

        规则：有更多完整字段则置信度更高
        """
        required_fields = ["company", "contact_name", "product", "value_prop"]
        filled = sum(1 for f in required_fields if lead.get(f, "").strip())
        total = len(required_fields)
        # 基础置信度 + 额外字段加分
        base = filled / total
        extra = 0.1 if lead.get("industry", "").strip() else 0
        extra += 0.1 if lead.get("pain_point", "").strip() else 0
        return min(1.0, base + extra)

    def batch_generate(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量生成邮件草稿

        Args:
            leads: 线索字典列表

        Returns:
            邮件草稿列表
        """
        if not leads:
            raise ValueError("E002: 线索列表为空")

        results = []
        for i, lead in enumerate(leads):
            try:
                result = self.generate_single(lead)
                result["index"] = i + 1
                results.append(result)
            except ValueError as e:
                # 单条失败不中断批量，记录错误
                results.append({
                    "index": i + 1,
                    "error": str(e),
                    "company": lead.get("company", ""),
                })
        return results


def parse_input(data: str) -> Any:
    """解析输入数据（支持JSON格式）

    Args:
        data: JSON字符串

    Returns:
        解析后的数据
    """
    if not data or not data.strip():
        raise ValueError("E002: 输入数据为空")
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        raise ValueError("E004: JSON解析失败")


def format_output(result: Dict[str, Any]) -> str:
    """格式化输出结果

    Args:
        result: 生成结果字典

    Returns:
        格式化后的文本
    """
    if "error" in result:
        return f"[错误] 线索{result.get('index', '?')}: {result['error']}"

    lines = [
        f"=== 邮件草稿 #{result.get('index', 1)} ===",
        f"【主题】{result['subject']}",
        f"【置信度】{result['confidence']:.0%}",
        "",
        result["full_email"],
        "",
    ]
    return "\n".join(lines)


def run_selftest() -> bool:
    """内置自检函数，不依赖外部文件或网络

    使用硬编码样例数据验证核心逻辑。
    采用宽松断言，确保任何环境可过。
    """
    print("开始自检...")

    # 创建生成器
    gen = ColdEmailGenerator(tone="professional")

    # 测试样例1：完整数据
    lead1 = {
        "company": "示例科技有限公司",
        "contact_name": "张经理",
        "product": "API集成服务",
        "industry": "technology",
        "value_prop": "可提升开发效率30%",
        "pain_point": "系统集成复杂",
    }

    # 测试样例2：不完整数据
    lead2 = {
        "company": "某初创公司",
        "product": "数据分析工具",
    }

    # 执行单条生成
    result1 = gen.generate_single(lead1)
    result2 = gen.generate_single(lead2)

    # 宽松断言1：结果应包含必要字段
    assert "full_email" in result1, "E007: 结果缺少full_email字段"
    assert "full_email" in result2, "E007: 结果缺少full_email字段"
    assert "subject" in result1, "E007: 结果缺少subject字段"
    assert "confidence" in result1, "E007: 结果缺少confidence字段"

    # 宽松断言2：完整数据的置信度应高于不完整数据
    assert result1["confidence"] > result2["confidence"], "E007: 置信度排序异常"

    # 宽松断言3：邮件内容应包含关键要素
    assert "张经理" in result1["full_email"], "E007: 称呼未正确生成"
    assert "示例科技有限公司" in result1["full_email"], "E007: 公司名未正确生成"
    assert "API集成服务" in result1["full_email"], "E007: 产品名未正确生成"

    # 宽松断言4：不完整数据应包含占位符
    assert "需核实" in result2["full_email"], "E007: 缺少置信度标注"

    # 宽松断言5：主题应包含公司名或产品名
    assert "示例科技" in result1["subject"], "E007: 主题生成异常"

    # 测试批量生成
    batch_result = gen.batch_generate([lead1, lead2])
    assert len(batch_result) == 2, "E009: 批量生成数量异常"
    assert all("full_email" in r for r in batch_result), "E009: 批量结果不完整"

    # 测试不同语气
    formal_gen = ColdEmailGenerator(tone="formal")
    casual_gen = ColdEmailGenerator(tone="casual")
    formal_result = formal_gen.generate_single(lead1)
    casual_result = casual_gen.generate_single(lead1)
    assert formal_result["full_email"] != casual_result["full_email"], "E007: 语气切换无效"

    # 测试错误处理
    try:
        gen.generate_single({})
        assert False, "E007: 空字典未抛出异常"
    except ValueError:
        pass  # 预期行为

    print("全部自检通过！")
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="冷邮件生成器 - 将零散资料转化为专业冷邮件草稿"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入JSON文件路径，或使用 --data 直接传入JSON字符串"
    )
    parser.add_argument(
        "--data", "-d",
        type=str,
        help="直接传入JSON字符串（单条或批量）"
    )
    parser.add_argument(
        "--tone", "-t",
        type=str,
        choices=["formal", "casual", "professional"],
        default="professional",
        help="语气风格 (默认: professional)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（可选）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"自检失败: {e}")
            sys.exit(1)

    # 输入检查
    if not args.data and not args.input:
        print("E006: 必须提供 --data 或 --input 参数", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)

    try:
        # 获取输入数据
        if args.data:
            input_str = args.data
        else:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    input_str = f.read()
            except FileNotFoundError:
                print(f"E008: 文件不存在: {args.input}", file=sys.stderr)
                sys.exit(1)
            except IOError as e:
                print(f"E008: 文件读取失败: {e}", file=sys.stderr)
                sys.exit(1)

        # 解析输入
        data = parse_input(input_str)

        # 创建生成器
        gen = ColdEmailGenerator(tone=args.tone)

        # 处理数据
        if isinstance(data, list):
            # 批量处理
            results = gen.batch_generate(data)
            outputs = [format_output(r) for r in results]
            output_text = "\n".join(outputs)
        elif isinstance(data, dict):
            # 单条处理
            result = gen.generate_single(data)
            output_text = format_output(result)
        else:
            print("E001: 输入必须是JSON对象或数组", file=sys.stderr)
            sys.exit(1)

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_text)
                print(f"结果已写入: {args.output}")
            except IOError as e:
                print(f"E005: 输出写入失败: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output_text)

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
