#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cold-email-generator 技能实现脚本
版本: 1.0.1
功能: 将零散资料转化为专业冷邮件草稿，支持批量处理与置信度标注。
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或格式无效",
    "E002": "无法解析输入内容",
    "E003": "缺少必要的收件人信息",
    "E004": "批量处理超过50条限制",
    "E005": "URL访问失败或内容为空",
    "E006": "文件读取失败或格式不支持",
    "E007": "JSON解析失败",
    "E008": "CSV解析失败",
    "E009": "内部处理逻辑错误",
    "E010": "参数配置错误",
}


@dataclass
class ContactInfo:
    """联系人信息数据类"""
    name: str = ""
    company: str = ""
    industry: str = ""
    product_service: str = ""
    intent_keywords: List[str] = field(default_factory=list)
    source_text: str = ""
    confidence_issues: List[str] = field(default_factory=list)


@dataclass
class EmailDraft:
    """邮件草稿数据类"""
    subject: str = ""
    greeting: str = ""
    body: str = ""
    signature_placeholder: str = ""
    confidence_notes: List[str] = field(default_factory=list)
    raw_input: str = ""


class InputParser:
    """输入解析器：处理文本、文件、URL等输入源"""
    
    @staticmethod
    def parse_text(text: str) -> Dict[str, Any]:
        """解析纯文本输入，提取联系人相关信息"""
        if not text or not text.strip():
            raise ValueError("E001: 输入为空或格式无效")
        
        info = ContactInfo(source_text=text.strip())
        
        # 提取姓名（常见模式：姓名：XXX 或 Name: XXX）
        name_match = re.search(r'(?:姓名|名字|Name)[：:\s]+([\u4e00-\u9fa5A-Za-z\s]{2,20})', text)
        if name_match:
            info.name = name_match.group(1).strip()
        
        # 提取公司
        company_match = re.search(r'(?:公司|企业|Company)[：:\s]+([\u4e00-\u9fa5A-Za-z0-9&\s]{2,50})', text)
        if company_match:
            info.company = company_match.group(1).strip()
        
        # 提取行业
        industry_match = re.search(r'(?:行业|Industry)[：:\s]+([\u4e00-\u9fa5A-Za-z\s]{2,30})', text)
        if industry_match:
            info.industry = industry_match.group(1).strip()
        
        # 提取产品/服务
        product_match = re.search(r'(?:产品|服务|Product|Service)[：:\s]+([\u4e00-\u9fa5A-Za-z0-9\s]{2,100})', text)
        if product_match:
            info.product_service = product_match.group(1).strip()
        
        # 提取合作意向关键词
        intent_patterns = [
            r'(?:合作|意向|需求)[：:\s]+([\u4e00-\u9fa5A-Za-z\s]{2,50})',
            r'(?:关键词|Keyword)[：:\s]+([\u4e00-\u9fa5A-Za-z\s,，]{2,100})'
        ]
        for pattern in intent_patterns:
            intent_match = re.search(pattern, text)
            if intent_match:
                keywords = [k.strip() for k in re.split(r'[,，\s]+', intent_match.group(1)) if k.strip()]
                info.intent_keywords.extend(keywords[:5])
        
        # 检查缺失信息并添加置信度标注
        if not info.name:
            info.confidence_issues.append("[需核实:收件人姓名]")
        if not info.company:
            info.confidence_issues.append("[需核实:公司名称]")
        if not info.industry:
            info.confidence_issues.append("[需核实:行业]")
        
        return {"contacts": [info], "source_type": "text"}
    
    @staticmethod
    def parse_csv(content: str) -> Dict[str, Any]:
        """解析CSV格式的批量数据"""
        try:
            reader = csv.DictReader(content.splitlines())
            contacts = []
            for row in reader:
                contact = ContactInfo(
                    name=row.get('姓名', row.get('name', '')),
                    company=row.get('公司', row.get('company', '')),
                    industry=row.get('行业', row.get('industry', '')),
                    product_service=row.get('产品', row.get('product', '')),
                    source_text=json.dumps(row, ensure_ascii=False)
                )
                # 检查缺失信息
                if not contact.name:
                    contact.confidence_issues.append("[需核实:收件人姓名]")
                if not contact.company:
                    contact.confidence_issues.append("[需核实:公司名称]")
                contacts.append(contact)
            
            if not contacts:
                raise ValueError("E008: CSV解析失败")
            if len(contacts) > 50:
                raise ValueError("E004: 批量处理超过50条限制")
            
            return {"contacts": contacts, "source_type": "csv"}
        except csv.Error as e:
            raise ValueError(f"E008: CSV解析失败 - {str(e)}")
    
    @staticmethod
    def parse_json(content: str) -> Dict[str, Any]:
        """解析JSON格式的批量数据"""
        try:
            data = json.loads(content)
            contacts = []
            
            # 支持单个对象或对象数组
            if isinstance(data, dict):
                data = [data]
            
            for item in data:
                contact = ContactInfo(
                    name=item.get('name', item.get('姓名', '')),
                    company=item.get('company', item.get('公司', '')),
                    industry=item.get('industry', item.get('行业', '')),
                    product_service=item.get('product', item.get('产品', '')),
                    source_text=json.dumps(item, ensure_ascii=False)
                )
                if not contact.name:
                    contact.confidence_issues.append("[需核实:收件人姓名]")
                if not contact.company:
                    contact.confidence_issues.append("[需核实:公司名称]")
                contacts.append(contact)
            
            if not contacts:
                raise ValueError("E007: JSON解析失败")
            if len(contacts) > 50:
                raise ValueError("E004: 批量处理超过50条限制")
            
            return {"contacts": contacts, "source_type": "json"}
        except json.JSONDecodeError as e:
            raise ValueError(f"E007: JSON解析失败 - {str(e)}")
    
    @staticmethod
    def parse_file(filepath: str) -> Dict[str, Any]:
        """解析文件内容"""
        if not os.path.exists(filepath):
            raise ValueError(f"E006: 文件读取失败 - 文件不存在: {filepath}")
        
        ext = os.path.splitext(filepath)[1].lower()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"E006: 文件读取失败 - {str(e)}")
        
        if ext == '.csv':
            return InputParser.parse_csv(content)
        elif ext == '.json':
            return InputParser.parse_json(content)
        elif ext in ['.txt', '.md']:
            return InputParser.parse_text(content)
        else:
            raise ValueError(f"E006: 文件读取失败 - 不支持的格式: {ext}")
    
    @staticmethod
    def parse_url(url: str) -> Dict[str, Any]:
        """解析URL内容"""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            raise ValueError(f"E005: URL访问失败或内容为空 - {str(e)}")
        
        if not content.strip():
            raise ValueError("E005: URL访问失败或内容为空")
        
        return InputParser.parse_text(content)


class EmailGenerator:
    """冷邮件生成器"""
    
    def __init__(self, style: str = "semi_formal", max_length: int = 200):
        """初始化生成器
        
        Args:
            style: 语气风格 (formal/semi_formal/casual)
            max_length: 邮件正文最大长度
        """
        if style not in ["formal", "semi_formal", "casual"]:
            raise ValueError(f"E010: 参数配置错误 - 无效的语气风格: {style}")
        if max_length < 50 or max_length > 500:
            raise ValueError("E010: 参数配置错误 - 邮件长度需在50-500字之间")
        
        self.style = style
        self.max_length = max_length
    
    def _generate_subject(self, contact: ContactInfo) -> str:
        """生成邮件主题行"""
        if contact.company:
            subject = f"关于与{contact.company}的商务合作机会"
        elif contact.industry:
            subject = f"{contact.industry}领域的合作建议"
        else:
            subject = "商务合作机会探讨"
        
        if contact.intent_keywords:
            subject += f" - {contact.intent_keywords[0]}"
        
        return subject[:50]  # 控制主题长度
    
    def _generate_greeting(self, contact: ContactInfo) -> str:
        """生成称呼"""
        if contact.name:
            if self.style == "formal":
                return f"尊敬的{contact.name}先生/女士："
            elif self.style == "casual":
                return f"你好，{contact.name}："
            else:
                return f"尊敬的{contact.name}："
        else:
            return "尊敬的客户："
    
    def _generate_body(self, contact: ContactInfo) -> str:
        """生成邮件正文"""
        paragraphs = []
        
        # 开头：自我介绍和目的
        if contact.company:
            opening = f"我是[您的姓名]，来自[您的公司]。我们注意到{contact.company}"
            if contact.industry:
                opening += f"在{contact.industry}领域的卓越表现"
            opening += "，希望探讨双方合作的可能性。"
        else:
            opening = "我是[您的姓名]，来自[您的公司]。希望与贵方探讨合作机会。"
        paragraphs.append(opening)
        
        # 中间：产品/服务介绍
        if contact.product_service:
            middle = f"我们提供的{contact.product_service}，"
            if contact.intent_keywords:
                middle += f"特别针对您关注的{contact.intent_keywords[0]}方面，"
            middle += "能够为贵方带来显著价值。"
        else:
            middle = "我们的产品/服务在同行业中具有显著优势，期待能为贵方创造价值。"
        paragraphs.append(middle)
        
        # 结尾：行动号召
        ending = "如您方便，期待与您进一步交流。您可以通过[您的邮箱]或[您的电话]联系我。"
        paragraphs.append(ending)
        
        body = "\n\n".join(paragraphs)
        
        # 控制长度
        if len(body) > self.max_length:
            body = body[:self.max_length] + "..."
        
        return body
    
    def _generate_signature(self) -> str:
        """生成签名占位符"""
        return "[您的姓名]\n[您的职位]\n[您的公司]\n[您的联系方式]"
    
    def generate(self, contact: ContactInfo) -> EmailDraft:
        """生成单个联系人的邮件草稿"""
        draft = EmailDraft(
            subject=self._generate_subject(contact),
            greeting=self._generate_greeting(contact),
            body=self._generate_body(contact),
            signature_placeholder=self._generate_signature(),
            confidence_notes=contact.confidence_issues,
            raw_input=contact.source_text
        )
        return draft
    
    def generate_batch(self, contacts: List[ContactInfo]) -> List[EmailDraft]:
        """批量生成邮件草稿"""
        return [self.generate(contact) for contact in contacts]


def format_email_output(draft: EmailDraft) -> str:
    """格式化邮件输出为Markdown格式"""
    lines = [f"# 邮件草稿", f"", f"**主题：** {draft.subject}", f""]
    
    # 置信度标注
    if draft.confidence_notes:
        lines.append("**注意：**")
        for note in draft.confidence_notes:
            lines.append(f"- {note}")
        lines.append("")
    
    lines.extend([
        draft.greeting,
        "",
        draft.body,
        "",
        draft.signature_placeholder,
        "",
        "---",
        "*本邮件由 cold-email-generator 自动生成*"
    ])
    
    return "\n".join(lines)


def process_input(input_source: str, input_type: str = "text") -> Dict[str, Any]:
    """处理输入源，返回解析结果"""
    parser = InputParser()
    
    if input_type == "text":
        return parser.parse_text(input_source)
    elif input_type == "file":
        return parser.parse_file(input_source)
    elif input_type == "url":
        return parser.parse_url(input_source)
    else:
        raise ValueError(f"E010: 参数配置错误 - 无效的输入类型: {input_type}")


def run_selftest() -> bool:
    """内置自检函数，使用硬编码样例数据验证核心逻辑"""
    print("开始自检...")
    
    # 测试数据
    test_text = """
    姓名：张三
    公司：ABC科技有限公司
    行业：企业服务
    产品：CRM客户管理系统
    合作意向：提高销售效率，数字化转型
    关键词：销售管理，客户关系
    """
    
    test_csv = """姓名,公司,行业,产品
    李四,XYZ制造集团,智能制造,工业自动化设备
    王五,EFG咨询,管理咨询,战略规划服务
    """
    
    test_json = json.dumps([
        {"name": "赵六", "company": "QWE科技", "industry": "人工智能", "product": "AI解决方案"},
        {"name": "孙七", "company": "RTY金融", "industry": "金融科技", "product": "智能风控系统"}
    ], ensure_ascii=False)
    
    try:
        # 测试1: 文本解析
        print("[1/6] 测试文本解析...")
        result = process_input(test_text, "text")
        assert len(result["contacts"]) == 1, "文本解析应返回1个联系人"
        contact = result["contacts"][0]
        assert contact.name == "张三", "姓名提取失败"
        assert contact.company == "ABC科技有限公司", "公司提取失败"
        assert contact.industry == "企业服务", "行业提取失败"
        assert len(contact.intent_keywords) > 0, "关键词提取失败"
        print("  ✓ 文本解析通过")
        
        # 测试2: CSV解析
        print("[2/6] 测试CSV解析...")
        result = process_input(test_csv, "text")
        assert len(result["contacts"]) == 2, "CSV解析应返回2个联系人"
        assert result["contacts"][0].name == "李四", "CSV第一行姓名解析失败"
        assert result["contacts"][1].company == "EFG咨询", "CSV第二行公司解析失败"
        print("  ✓ CSV解析通过")
        
        # 测试3: JSON解析
        print("[3/6] 测试JSON解析...")
        result = process_input(test_json, "text")
        assert len(result["contacts"]) == 2, "JSON解析应返回2个联系人"
        assert result["contacts"][0].name == "赵六", "JSON第一项姓名解析失败"
        assert result["contacts"][1].industry == "金融科技", "JSON第二项行业解析失败"
        print("  ✓ JSON解析通过")
        
        # 测试4: 邮件生成
        print("[4/6] 测试邮件生成...")
        generator = EmailGenerator(style="semi_formal", max_length=300)
        contacts = process_input(test_text, "text")["contacts"]
        draft = generator.generate(contacts[0])
        assert draft.subject, "主题不能为空"
        assert draft.greeting, "称呼不能为空"
        assert draft.body, "正文不能为空"
        assert draft.signature_placeholder, "签名不能为空"
        assert len(draft.body) <= 310, "正文长度超出限制"
        print("  ✓ 邮件生成通过")
        
        # 测试5: 批量处理
        print("[5/6] 测试批量处理...")
        contacts = process_input(test_csv, "text")["contacts"]
        drafts = generator.generate_batch(contacts)
        assert len(drafts) == 2, "批量生成数量错误"
        assert all(d.subject for d in drafts), "批量生成的主题不能为空"
        print("  ✓ 批量处理通过")
        
        # 测试6: 置信度标注
        print("[6/6] 测试置信度标注...")
        incomplete_text = "公司：测试公司\n行业：IT"
        contacts = process_input(incomplete_text, "text")["contacts"]
        assert contacts[0].confidence_issues, "缺失信息应产生置信度标注"
        assert any("[需核实" in issue for issue in contacts[0].confidence_issues), "置信度标注格式错误"
        print("  ✓ 置信度标注通过")
        
        print("\n所有自检测试通过！")
        return True
        
    except AssertionError as e:
        print(f"✗ 自检失败: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ 自检异常: {str(e)}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="冷邮件撰写工具 - 将零散资料转化为专业冷邮件草稿",
        epilog="示例: python main.py --input '姓名：张三\n公司：ABC公司' --style formal"
    )
    
    parser.add_argument("--input", "-i", type=str, help="输入内容（文本/文件路径/URL）")
    parser.add_argument("--type", "-t", type=str, choices=["text", "file", "url"], 
                        default="text", help="输入类型，默认text")
    parser.add_argument("--style", "-s", type=str, choices=["formal", "semi_formal", "casual"],
                        default="semi_formal", help="语气风格，默认semi_formal")
    parser.add_argument("--max-length", "-m", type=int, default=200,
                        help="邮件正文最大长度，默认200字")
    parser.add_argument("--format", "-f", type=str, choices=["markdown", "json"],
                        default="markdown", help="输出格式，默认markdown")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查必要参数
    if not args.input:
        print("错误: E001 - 请提供输入内容，使用 --input 参数", file=sys.stderr)
        sys.exit(1)
    
    try:
        # 处理输入
        parsed_data = process_input(args.input, args.type)
        contacts = parsed_data["contacts"]
        
        # 生成邮件
        generator = EmailGenerator(style=args.style, max_length=args.max_length)
        drafts = generator.generate_batch(contacts)
        
        # 输出结果
        if args.format == "json":
            output = []
            for draft in drafts:
                output.append({
                    "subject": draft.subject,
                    "greeting": draft.greeting,
                    "body": draft.body,
                    "signature": draft.signature_placeholder,
                    "confidence_notes": draft.confidence_notes
                })
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            for i, draft in enumerate(drafts, 1):
                if len(drafts) > 1:
                    print(f"\n{'='*50}\n[邮件 {i}/{len(drafts)}]\n{'='*50}")
                print(format_email_output(draft))
                if i < len(drafts):
                    print("\n" + "-"*50)
        
    except ValueError as e:
        error_msg = str(e)
        error_code = error_msg.split(":")[0] if ":" in error_msg else "E009"
        print(f"错误: {error_msg}", file=sys.stderr)
        print(f"错误码: {error_code}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: E009 - 内部处理逻辑错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
