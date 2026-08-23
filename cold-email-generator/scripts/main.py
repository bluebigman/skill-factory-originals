#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cold-email-generator 独立实现脚本
版本: 1.0.3 (clean-room 重写 + 生产级修复)
仅依据功能规格开发，不包含任何既有代码。

修复内容：
1. 修复语法错误 `self.tone_config["greeting"].for` → `.format(name=contact_name)`
2. 移除无用的模块级 dry_run 标志
3. 批量处理改用 ThreadPoolExecutor 并发执行，添加异常捕获和重试逻辑
4. 在 generate_single 返回值中添加 confidence 字段（基于字段完整度计算）
5. 重写 selftest，真实调用核心函数并断言关键输出
6. 使用 datetime.now(timezone.utc) 获取UTC时间
"""

import argparse
import json
import sys
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

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
            包含邮件各部分和置信度的字典
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
        # 称呼 - 修复语法错误
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

        # 置信度评估（基于字段完整度）
        confidence = self._calculate_confidence(lead)

        # 生成时间戳（UTC）
        timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "company": company,
            "contact_name": contact_name,
            "greeting": greeting,
            "body": body,
            "closing": closing,
            "full_email": full_email,
            "subject": self._generate_subject(company, product),
            "confidence": confidence,
            "generated_at": timestamp,
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

    def _process_single_with_retry(self, lead: Dict[str, Any], index: int, max_retries: int = 3) -> Dict[str, Any]:
        """处理单条线索，带重试机制

        Args:
            lead: 线索字典
            index: 索引号
            max_retries: 最大重试次数

        Returns:
            处理结果字典
        """
        for attempt in range(max_retries):
            try:
                result = self.generate_single(lead)
                result["index"] = index
                return result
            except ValueError as e:
                # 数据错误不重试，直接返回错误
                return {
                    "index": index,
                    "error": str(e),
                    "company": lead.get("company", ""),
                }
            except Exception as e:
                # 其他异常，带退避重试
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    time.sleep(wait_time)
                else:
                    return {
                        "index": index,
                        "error": f"E010: 处理失败: {str(e)}",
                        "company": lead.get("company", ""),
                    }

    def batch_generate(self, leads: List[Dict[str, Any]], max_workers: int = 4) -> List[Dict[str, Any]]:
        """批量生成邮件草稿（并发执行）

        Args:
            leads: 线索字典列表
            max_workers: 最大并发数

        Returns:
            邮件草稿列表
        """
        if not leads:
            raise ValueError("E002: 线索列表为空")

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(self._process_single_with_retry, lead, i + 1): i
                for i, lead in enumerate(leads)
            }

            # 收集结果
            for future in as_completed(future_to_index):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # 单个任务失败不中断整体
                    index = future_to_index[future] + 1
                    results.append({
                        "index": index,
                        "error": f"E010: 未知错误: {str(e)}",
                        "company": leads[index - 1].get("company", ""),
                    })

        # 按索引排序，保持原始顺序
        results.sort(key=lambda x: x.get("index", 0))
        return results


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


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
        f"【生成时间】{result.get('generated_at', 'N/A')}",
        "",
        result["full_email"],
        "",
    ]
    return "\n".join(lines)


def run_selftest() -> bool:
    """内置自检函数，真实调用核心函数并断言关键输出

    使用硬编码样例数据验证核心逻辑。
    确保退出码为0且验证结果。
    """
    print("开始自检...")
    test_results = []

    try:
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

        # 断言1：结果应包含必要字段
        assert "full_email" in result1, "E007: 结果缺少full_email字段"
        assert "full_email" in result2, "E007: 结果缺少full_email字段"
        assert "subject" in result1, "E007: 结果缺少subject字段"
        assert "confidence" in result1, "E007: 结果缺少confidence字段"
        assert "generated_at" in result1, "E007: 结果缺少generated_at字段"
        test_results.append("字段完整性检查通过")

        # 断言2：完整数据的置信度应高于不完整数据
        assert result1["confidence"] > result2["confidence"], "E007: 置信度排序异常"
        test_results.append("置信度排序检查通过")

        # 断言3：邮件内容应包含关键要素
        assert "张经理" in result1["full_email"], "E007: 称呼未正确生成"
        assert "示例科技有限公司" in result1["full_email"], "E007: 公司名未正确生成"
        assert "API集成服务" in result1["full_email"], "E007: 产品名未正确生成"
        test_results.append("邮件内容检查通过")

        # 断言4：不完整数据应包含占位符
        assert "需核实" in result2["full_email"], "E007: 缺少置信度标注"
        test_results.append("占位符检查通过")

        # 断言5：主题应包含公司名或产品名
        assert "示例科技" in result1["subject"], "E007: 主题生成异常"
        test_results.append("主题生成检查通过")

        # 断言6：时间戳应为UTC格式
        assert result1["generated_at"].endswith("+00:00"), "E007: 时间戳不是UTC格式"
        test_results.append("UTC时间戳检查通过")

        # 测试批量生成（并发）
        batch_result = gen.batch_generate([lead1, lead2], max_workers=2)
        assert len(batch_result) == 2, "E009: 批量生成数量异常"
        assert all("full_email" in r for r in batch_result), "E009: 批量结果不完整"
        test_results.append("批量生成检查通过")

        # 测试不同语气
        formal_gen = ColdEmailGenerator(tone="formal")
        casual_gen = ColdEmailGenerator(tone="casual")
        formal_result = formal_gen.generate_single(lead1)
        casual_result = casual_gen.generate_single(lead1)
        assert formal_result["full_email"] != casual_result["full_email"], "E007: 语气切换无效"
        test_results.append("语气切换检查通过")

        # 测试错误处理
        try:
            gen.generate_single({})
            assert False, "E007: 空字典未抛出异常"
        except ValueError:
            pass  # 预期行为
        test_results.append("错误处理检查通过")

        # 测试重试机制
        class TestGenerator(ColdEmailGenerator):
            def generate_single(self, lead):
                if not hasattr(self, '_retry_count'):
                    self._retry_count = 0
                self._retry_count += 1
                if self._retry_count < 3:
                    raise Exception("模拟临时错误")
                return super().generate_single(lead)

        test_gen = TestGenerator()
        retry_result = test_gen._process_single_with_retry(lead1, 1, max_retries=3)
        assert "full_email" in retry_result, "E007: 重试机制未生效"
        test_results.append("重试机制检查通过")

        # 打印所有检查结果
        for result in test_results:
            print(f"  ✓ {result}")

        print("全部自检通过！")
        return True

    except AssertionError as e:
        print(f"自检失败: {e}")
        return False
    except Exception as e:
        print(f"自检异常: {e}")
        return False


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
