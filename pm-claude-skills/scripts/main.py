#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm-claude-skills 技能编排工具箱 - 独立实现脚本
================================================
本脚本依据功能规格独立实现，提供技能导航、文档生成辅助、
数据分析与流程自动化的核心逻辑。

仅使用 Python 标准库，无第三方依赖。
运行方式:
    python main.py --selftest   # 离线自检
    python main.py --help       # 查看帮助
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义
# E001: 输入参数错误
# E002: 输入数据处理失败
# E003: 输出格式错误
# E004: 数据解析失败
# E005: 置信度标注失败
# E006: 批量处理失败
# E007: 数据验证失败
# E008: 文件读写错误
# E009: 内部逻辑错误
# E010: 未知错误


class SkillError(Exception):
    """技能执行异常基类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心数据结构
# ============================================================

class ProductData:
    """产品数据容器"""
    def __init__(self, raw_text: str = "", source_type: str = "text"):
        self.raw_text = raw_text
        self.source_type = source_type
        self.fields: Dict[str, Any] = {}
        self.confidence: Dict[str, float] = {}
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0.1"
        }

    def set_field(self, name: str, value: Any, confidence: float = 1.0) -> None:
        """设置字段值及置信度"""
        self.fields[name] = value
        self.confidence[name] = max(0.0, min(1.0, confidence))

    def get_field(self, name: str, default: Any = None) -> Any:
        """获取字段值"""
        return self.fields.get(name, default)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.fields,
            "confidence": self.confidence,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = ["# 产品数据报告", ""]
        for key, value in self.fields.items():
            conf = self.confidence.get(key, 1.0)
            marker = "" if conf >= 0.8 else f" [需核实:{key}]"
            lines.append(f"## {key}{marker}")
            lines.append(str(value))
            lines.append("")
        return "\n".join(lines)

    def to_csv(self) -> str:
        """转换为 CSV 格式"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["字段", "值", "置信度"])
        for key, value in self.fields.items():
            writer.writerow([key, str(value), f"{self.confidence.get(key, 1.0):.2f}"])
        return output.getvalue()


# ============================================================
# 核心功能模块
# ============================================================

class TextParser:
    """文本解析器 - 从原始文本中提取结构化信息"""
    
    # 常见字段的正则模式
    PATTERNS = {
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
        "phone": r"(?:\+?86[- ]?)?1[3-9]\d{9}",
        "url": r"https?://[^\s]+",
        "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        "price": r"(?:￥|¥|RMB|CNY)?\s*\d+(?:\.\d{1,2})?\s*(?:元|块)?",
        "id_card": r"\d{17}[\dXx]",
        "ip_address": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    }

    def __init__(self, text: str):
        """初始化解析器"""
        if not isinstance(text, str):
            raise SkillError("E001", "输入文本必须是字符串类型")
        self.text = text.strip()

    def extract_fields(self) -> Dict[str, List[str]]:
        """提取所有匹配的字段"""
        results = {}
        for field_name, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, self.text)
            if matches:
                results[field_name] = list(set(matches))  # 去重
        return results

    def extract_keywords(self, top_n: int = 10) -> List[str]:
        """提取关键词（简单词频统计）"""
        # 分词（简单按空格和常见标点分割）
        words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+', self.text.lower())
        # 过滤停用词
        stopwords = {
            "的", "了", "和", "是", "在", "有", "我", "你", "他", "她",
            "它", "们", "这", "那", "个", "之", "与", "及", "或", "等",
            "the", "a", "an", "is", "are", "was", "were", "be", "to", "of"
        }
        filtered = [w for w in words if w not in stopwords and len(w) > 1]
        # 统计词频
        freq = {}
        for word in filtered:
            freq[word] = freq.get(word, 0) + 1
        # 排序取前 N 个
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:top_n]]

    def detect_language(self) -> str:
        """检测文本语言"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', self.text))
        english_chars = len(re.findall(r'[a-zA-Z]', self.text))
        if chinese_chars > english_chars:
            return "zh-CN"
        elif english_chars > 0:
            return "en-US"
        return "unknown"

    def summarize(self, max_length: int = 200) -> str:
        """生成摘要"""
        if len(self.text) <= max_length:
            return self.text
        # 取前 max_length 个字符，并在句子边界截断
        truncated = self.text[:max_length]
        # 尝试在句号、感叹号、问号处截断
        for punct in ["。", "！", "？", ".", "!", "?"]:
            idx = truncated.rfind(punct)
            if idx > max_length * 0.5:
                return truncated[:idx + 1] + "..."
        return truncated + "..."


class DocumentGenerator:
    """文档生成器 - 生成 PRD、报告等结构化文档"""
    
    def __init__(self, data: ProductData):
        """初始化生成器"""
        self.data = data

    def generate_prd(self) -> str:
        """生成 PRD 文档"""
        lines = [
            "# 产品需求文档 (PRD)",
            "",
            f"> 生成时间: {self.data.metadata.get('created_at', '未知')}",
            f"> 版本: {self.data.metadata.get('version', '1.0.0')}",
            "",
            "## 1. 需求背景",
            "",
            self.data.get_field("background", "[需核实:背景描述]"),
            "",
            "## 2. 目标用户",
            "",
            self.data.get_field("target_users", "[需核实:目标用户]"),
            "",
            "## 3. 功能需求",
            "",
        ]
        
        features = self.data.get_field("features", [])
        if isinstance(features, list):
            for i, feature in enumerate(features, 1):
                lines.append(f"### 3.{i} {feature.get('name', f'功能{i}')}")
                lines.append("")
                lines.append(f"- 描述: {feature.get('description', '[需核实:功能描述]')}")
                lines.append(f"- 优先级: {feature.get('priority', 'P2')}")
                lines.append("")
        else:
            lines.append("[需核实:功能列表]")
        
        lines.extend([
            "## 4. 验收标准",
            "",
            self.data.get_field("acceptance_criteria", "[需核实:验收标准]"),
            "",
            "## 5. 风险与依赖",
            "",
            self.data.get_field("risks", "[需核实:风险管理]"),
        ])
        return "\n".join(lines)

    def generate_retrospective(self) -> str:
        """生成复盘报告"""
        lines = [
            "# 项目复盘报告",
            "",
            f"> 生成时间: {self.data.metadata.get('created_at', '未知')}",
            "",
            "## 1. 项目概述",
            "",
            self.data.get_field("overview", "[需核实:项目概述]"),
            "",
            "## 2. 完成情况",
            "",
            self.data.get_field("completion", "[需核实:完成情况]"),
            "",
            "## 3. 经验总结",
            "",
            "- 做得好的:",
        ]
        
        good_points = self.data.get_field("good_points", [])
        if isinstance(good_points, list):
            for point in good_points:
                lines.append(f"  - {point}")
        else:
            lines.append("  [需核实:做得好的方面]")
        
        lines.extend([
            "",
            "- 待改进的:",
        ])
        
        improvements = self.data.get_field("improvements", [])
        if isinstance(improvements, list):
            for point in improvements:
                lines.append(f"  - {point}")
        else:
            lines.append("  [需核实:待改进方面]")
        
        lines.extend([
            "",
            "## 4. 行动计划",
            "",
            self.data.get_field("action_plan", "[需核实:行动计划]"),
        ])
        return "\n".join(lines)

    def generate_meeting_minutes(self) -> str:
        """生成会议纪要"""
        lines = [
            "# 会议纪要",
            "",
            f"> 生成时间: {self.data.metadata.get('created_at', '未知')}",
            "",
            "## 会议信息",
            "",
            f"- 主题: {self.data.get_field('topic', '[需核实:会议主题]')}",
            f"- 时间: {self.data.get_field('meeting_time', '[需核实:会议时间]')}",
            f"- 地点: {self.data.get_field('location', '[需核实:会议地点]')}",
            "",
            "## 参会人员",
            "",
        ]
        
        attendees = self.data.get_field("attendees", [])
        if isinstance(attendees, list):
            for person in attendees:
                lines.append(f"- {person}")
        else:
            lines.append("- [需核实:参会人员]")
        
        lines.extend([
            "",
            "## 讨论要点",
            "",
        ])
        
        topics = self.data.get_field("discussion_topics", [])
        if isinstance(topics, list):
            for i, topic in enumerate(topics, 1):
                lines.append(f"### {i}. {topic.get('title', f'议题{i}')}")
                lines.append("")
                lines.append(topic.get("content", "[需核实:讨论内容]"))
                lines.append("")
        else:
            lines.append("[需核实:讨论要点]")
        
        lines.extend([
            "## 行动项",
            "",
        ])
        
        actions = self.data.get_field("action_items", [])
        if isinstance(actions, list):
            for i, action in enumerate(actions, 1):
                owner = action.get("owner", "[需核实:负责人]")
                deadline = action.get("deadline", "[需核实:截止日期]")
                lines.append(f"{i}. {action.get('task', '[需核实:任务]')} - 负责人: {owner}, 截止: {deadline}")
        else:
            lines.append("- [需核实:行动项]")
        
        return "\n".join(lines)


class DataAnalyzer:
    """数据分析器 - 执行统计分析"""
    
    def __init__(self, data: List[Dict[str, Any]]):
        """初始化分析器"""
        if not isinstance(data, list):
            raise SkillError("E001", "数据必须是列表类型")
        self.data = data
        self.rows = len(data)

    def get_numeric_fields(self) -> List[str]:
        """获取所有数值型字段名"""
        if not self.data:
            return []
        numeric_fields = []
        for field in self.data[0].keys():
            try:
                float(self.data[0][field])
                numeric_fields.append(field)
            except (ValueError, TypeError):
                continue
        return numeric_fields

    def compute_stats(self, field: str) -> Dict[str, float]:
        """计算字段的统计指标"""
        values = []
        for row in self.data:
            try:
                values.append(float(row.get(field, 0)))
            except (ValueError, TypeError):
                continue
        
        if not values:
            raise SkillError("E007", f"字段 '{field}' 没有有效的数值数据")
        
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = variance ** 0.5
        
        return {
            "count": n,
            "mean": mean,
            "median": sorted(values)[n // 2] if n % 2 == 1 else (sorted(values)[n//2 - 1] + sorted(values)[n//2]) / 2,
            "min": min(values),
            "max": max(values),
            "std_dev": std_dev,
            "variance": variance,
            "sum": sum(values)
        }

    def group_by(self, field: str) -> Dict[str, List[Dict[str, Any]]]:
        """按字段分组"""
        groups = {}
        for row in self.data:
            key = str(row.get(field, "未知"))
            if key not in groups:
                groups[key] = []
            groups[key].append(row)
        return groups

    def detect_outliers(self, field: str, threshold: float = 1.5) -> List[Dict[str, Any]]:
        """检测离群值（IQR 方法）"""
        values = []
        for row in self.data:
            try:
                values.append(float(row.get(field, 0)))
            except (ValueError, TypeError):
                continue
        
        if len(values) < 4:
            return []
        
        sorted_vals = sorted(values)
        q1 = sorted_vals[len(sorted_vals) // 4]
        q3 = sorted_vals[3 * len(sorted_vals) // 4]
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        outliers = []
        for row in self.data:
            try:
                val = float(row.get(field, 0))
                if val < lower_bound or val > upper_bound:
                    outliers.append(row)
            except (ValueError, TypeError):
                continue
        return outliers


class WorkflowManager:
    """流程管理器 - 编排多步骤任务"""
    
    def __init__(self):
        """初始化流程管理器"""
        self.steps: List[Dict[str, Any]] = []
        self.results: List[Any] = []
        self.status = "idle"

    def add_step(self, name: str, func: callable, *args, **kwargs) -> None:
        """添加执行步骤"""
        self.steps.append({
            "name": name,
            "func": func,
            "args": args,
            "kwargs": kwargs
        })

    def execute(self) -> bool:
        """依次执行所有步骤"""
        self.status = "running"
        self.results = []
        
        for i, step in enumerate(self.steps):
            try:
                print(f"  执行步骤 {i+1}/{len(self.steps)}: {step['name']}")
                result = step["func"](*step["args"], **step["kwargs"])
                self.results.append({
                    "step": step["name"],
                    "success": True,
                    "result": result
                })
            except Exception as e:
                self.results.append({
                    "step": step["name"],
                    "success": False,
                    "error": str(e)
                })
                self.status = "failed"
                return False
        
        self.status = "completed"
        return True

    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        success_count = sum(1 for r in self.results if r.get("success"))
        return {
            "total_steps": len(self.steps),
            "success_count": success_count,
            "failed_count": len(self.steps) - success_count,
            "status": self.status
        }


class SkillToolkit:
    """技能工具箱主类"""
    
    def __init__(self):
        """初始化工具箱"""
        self.version = "1.0.1"
        self.name = "pm-claude-skills"
        self.display_name = "产品研发 技能编排 全栈工具箱"
        self.capabilities = {
            "core_uses": ["PRD生成", "复盘报告", "需求拆解", "数据分析"],
            "input_sources": ["文本", "文件", "URL"],
            "output_formats": ["Markdown", "JSON", "CSV"],
            "processing": ["单条处理", "批量处理"],
            "confidence_marking": True
        }

    def process_text(self, text: str, output_format: str = "json") -> str:
        """处理文本并输出结构化结果"""
        try:
            # 解析文本
            parser = TextParser(text)
            extracted = parser.extract_fields()
            
            # 创建产品数据对象
            data = ProductData(text)
            for field, values in extracted.items():
                conf = 0.7 if len(values) > 0 else 0.3
                data.set_field(field, values, conf)
            
            # 添加额外信息
            data.set_field("language", parser.detect_language(), 0.9)
            data.set_field("summary", parser.summarize(), 0.8)
            data.set_field("keywords", parser.extract_keywords(), 0.6)
            
            # 输出
            if output_format == "json":
                return data.to_json()
            elif output_format == "markdown":
                return data.to_markdown()
            elif output_format == "csv":
                return data.to_csv()
            else:
                raise SkillError("E003", f"不支持的输出格式: {output_format}")
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E002", f"文本处理失败: {str(e)}") from e

    def analyze_data(self, data: List[Dict[str, Any]], fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """分析数据集"""
        try:
            analyzer = DataAnalyzer(data)
            analysis = {
                "row_count": analyzer.rows,
                "fields": list(data[0].keys()) if data else [],
                "stats": {}
            }
            
            fields_to_analyze = fields or analyzer.get_numeric_fields()
            for field in fields_to_analyze:
                try:
                    analysis["stats"][field] = analyzer.compute_stats(field)
                except SkillError:
                    continue
            
            return analysis
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E006", f"数据分析失败: {str(e)}") from e

    def batch_process(self, items: List[str], output_format: str = "json") -> List[str]:
        """批量处理文本项"""
        results = []
        for i, item in enumerate(items):
            try:
                result = self.process_text(item, output_format)
                results.append(result)
            except SkillError as e:
                results.append(json.dumps({
                    "error": e.code,
                    "message": e.message,
                    "item_index": i
                }, ensure_ascii=False))
        return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """运行内置自检"""
    print("=" * 60)
    print("pm-claude-skills 自检程序")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    def run_test(name: str, func: callable) -> None:
        nonlocal tests_passed, tests_failed
        try:
            func()
            print(f"  [PASS] {name}")
            tests_passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            tests_failed += 1
    
    # 测试1: 文本解析
    def test_text_parser():
        sample_text = """
        产品需求文档 2024年6月15日
        联系人: zhangsan@example.com, 电话: 13812345678
        项目网站: https://example.com/prd
        预算: ¥50000元
        """
        parser = TextParser(sample_text)
        fields = parser.extract_fields()
        assert "email" in fields, "应提取邮箱"
        assert "phone" in fields, "应提取电话"
        assert "url" in fields, "应提取URL"
        assert "date" in fields, "应提取日期"
        assert "price" in fields, "应提取价格"
        
        # 语言检测
        lang = parser.detect_language()
        assert lang == "zh-CN", f"语言检测应为 zh-CN, 实际: {lang}"
        
        # 摘要
        summary = parser.summarize(50)
        assert len(summary) <= 53, f"摘要长度应有限制, 实际: {len(summary)}"
        
        # 关键词
        keywords = parser.extract_keywords(5)
        assert len(keywords) > 0, "应提取到关键词"
    
    # 测试2: 产品数据
    def test_product_data():
        data = ProductData("测试数据")
        data.set_field("name", "测试产品", 0.9)
        data.set_field("price", 100)
        
        # JSON 输出
        json_str = data.to_json()
        parsed = json.loads(json_str)
        assert parsed["data"]["name"] == "测试产品"
        assert parsed["confidence"]["name"] >= 0.8
        
        # Markdown 输出
        md = data.to_markdown()
        assert "# 产品数据报告" in md
        assert "测试产品" in md
        
        # CSV 输出
        csv_str = data.to_csv()
        assert "字段" in csv_str
        assert "测试产品" in csv_str
    
    # 测试3: 文档生成
    def test_document_generator():
        data = ProductData()
        data.set_field("background", "用户反馈系统响应慢")
        data.set_field("target_users", "内部员工")
        data.set_field("features", [
            {"name": "性能优化", "description": "优化系统响应", "priority": "P0"},
            {"name": "界面改进", "description": "改进用户界面", "priority": "P1"}
        ])
        
        gen = DocumentGenerator(data)
        prd = gen.generate_prd()
        assert "# 产品需求文档" in prd
        assert "性能优化" in prd
        assert "P0" in prd
        
        # 复盘报告
        data2 = ProductData()
        data2.set_field("overview", "Q2 项目")
        data2.set_field("completion", "完成 80%")
        data2.set_field("good_points", ["按时交付", "质量良好"])
        data2.set_field("improvements", ["沟通需改进"])
        
        gen2 = DocumentGenerator(data2)
        retro = gen2.generate_retrospective()
        assert "# 项目复盘报告" in retro
        assert "按时交付" in retro
    
    # 测试4: 数据分析
    def test_data_analyzer():
        sample_data = [
            {"name": "A", "value": 10, "group": "X"},
            {"name": "B", "value": 20, "group": "X"},
            {"name": "C", "value": 30, "group": "Y"},
            {"name": "D", "value": 40, "group": "Y"},
            {"name": "E", "value": 50, "group": "X"},
        ]
        
        analyzer = DataAnalyzer(sample_data)
        assert analyzer.rows == 5
        
        stats = analyzer.compute_stats("value")
        assert stats["count"] == 5
        assert stats["mean"] == 30
        assert stats["min"] == 10
        assert stats["max"] == 50
        
        groups = analyzer.group_by("group")
        assert "X" in groups
        assert "Y" in groups
        assert len(groups["X"]) == 3
        
        outliers = analyzer.detect_outliers("value")
        assert len(outliers) == 0  # 无离群值
    
    # 测试5: 流程管理
    def test_workflow():
        wf = WorkflowManager()
        
        def step1():
            return "第一步完成"
        
        def step2():
            return "第二步完成"
        
        wf.add_step("初始化", step1)
        wf.add_step("处理", step2)
        
        success = wf.execute()
        assert success, "流程应执行成功"
        assert len(wf.results) == 2
        assert wf.get_summary()["status"] == "completed"
    
    # 测试6: 主工具箱
    def test_toolkit():
        toolkit = SkillToolkit()
        
        # 文本处理
        result = toolkit.process_text("测试邮箱: test@example.com", "json")
        parsed = json.loads(result)
        assert "email" in parsed["data"]
        
        # 数据分析
        sample = [{"x": 1}, {"x": 2}, {"x": 3}]
        analysis = toolkit.analyze_data(sample)
        assert analysis["row_count"] == 3
        assert analysis["stats"]["x"]["mean"] == 2
        
        # 批量处理
        batch = toolkit.batch_process(["文本1", "文本2"], "json")
        assert len(batch) == 2
    
    # 运行所有测试
    run_test("文本解析器", test_text_parser)
    run_test("产品数据容器", test_product_data)
    run_test("文档生成器", test_document_generator)
    run_test("数据分析器", test_data_analyzer)
    run_test("流程管理器", test_workflow)
    run_test("工具箱主类", test_toolkit)
    
    # 输出结果
    print("-" * 60)
    print(f"自检完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)
    
    return tests_failed == 0


# ============================================================
# 主程序入口
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="pm-claude-skills 产品研发技能编排工具箱",
        epilog="示例: python main.py --selftest"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件）"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"pm-claude-skills v1.0.1"
    )
    
    parser.add_argument(
        "--process",
        type=str,
        metavar="TEXT",
        help="处理文本并输出结构化结果"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown", "csv"],
        default="json",
        help="输出格式（默认: json）"
    )
    
    parser.add_argument(
        "--analyze",
        type=str,
        metavar="DATA_JSON",
        help="分析 JSON 格式的数据集"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 文本处理模式
    if args.process:
        try:
            toolkit = SkillToolkit()
            result = toolkit.process_text(args.process, args.format)
            print(result)
            sys.exit(0)
        except SkillError as e:
            print(f"错误 {e.code}: {e.message}", file=sys.stderr)
            sys.exit(1)
    
    # 数据分析模式
    if args.analyze:
        try:
            data = json.loads(args.analyze)
            if not isinstance(data, list):
                raise SkillError("E001", "数据分析输入必须是 JSON 数组")
            toolkit = SkillToolkit()
            result = toolkit.analyze_data(data)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0)
        except json.JSONDecodeError:
            print("错误 E004: JSON 解析失败", file=sys.stderr)
            sys.exit(1)
        except SkillError as e:
            print(f"错误 {e.code}: {e.message}", file=sys.stderr)
            sys.exit(1)
    
    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
