#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章下载器 - 本地优先的微信内容情报库同步工具

本脚本是一个独立、干净的实现，仅依据功能规格编写。
核心能力：
  1. 将用户提供的数据/文件/URL 转换为结构化结果
  2. 识别并保留输入中的关键信息
  3. 按约定格式生成输出
  4. 对不确定项给出置信度提示
  5. 支持批量处理和自定义格式

错误码体系：
  E001 - 输入为空
  E002 - 关键信息缺失
  E003 - 输入格式错误
  E004 - 超出能力边界
  E005 - 置信度过低
  E006 - 输出格式不支持
  E007 - 数据解析失败
  E008 - 文件读取失败
  E009 - 参数错误
  E010 - 内部逻辑错误

用法示例：
  python main.py --selftest                       # 运行离线自检
  python main.py --input "文章标题|作者|2026-01-01"  # 处理一条输入
  python main.py --input "标题1|作者1|日期1" --input "标题2|作者2|日期2"  # 批量处理
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：标题|作者|日期",
    "E004": "这超出了本工具的能力范围，建议使用专门工具处理",
    "E005": "结果无法确定，建议人工复核关键信息",
    "E006": "不支持的输出格式，可选：json、text、csv",
    "E007": "数据解析失败，请检查输入内容",
    "E008": "文件读取失败，请检查文件路径和权限",
    "E009": "参数错误，请检查命令行参数",
    "E010": "内部逻辑错误，请报告此问题",
}

# 置信度阈值
HIGH_CONFIDENCE = 90   # ≥90% 直接输出
MEDIUM_CONFIDENCE = 85 # 85%-90% 标注"建议复核"
LOW_CONFIDENCE = 85    # <85% 标注"[需核实]"

# 输出格式支持列表
SUPPORTED_FORMATS = ["json", "text", "csv"]

# 必需字段列表
REQUIRED_FIELDS = ["title", "author", "date"]


# ============================================================
# 数据模型与解析
# ============================================================

class Article:
    """文章数据模型"""
    
    def __init__(self, title: str, author: str, date: str, 
                 content: str = "", url: str = "", 
                 comments: Optional[List[Dict[str, Any]]] = None,
                 extra: Optional[Dict[str, Any]] = None):
        self.title = title
        self.author = author
        self.date = date
        self.content = content
        self.url = url
        self.comments = comments or []
        self.extra = extra or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "content": self.content,
            "url": self.url,
            "comments": self.comments,
            "extra": self.extra,
            "confidence": self._calculate_confidence(),
            "needs_review": self._needs_review(),
        }
    
    def _calculate_confidence(self) -> int:
        """
        计算置信度（0-100）
        
        基于字段完整性和数据合理性：
        - 基础分 70
        - 每个必需字段存在 +5
        - 日期格式正确 +5
        - 有内容 +5
        - 有URL +5
        - 有评论 +5
        """
        score = 70
        
        # 必需字段检查
        for field in REQUIRED_FIELDS:
            if getattr(self, field, ""):
                score += 5
        
        # 日期格式检查
        if self._is_valid_date(self.date):
            score += 5
        
        # 可选字段加分
        if self.content:
            score += 5
        if self.url:
            score += 5
        if self.comments:
            score += 5
        
        return min(score, 100)
    
    def _needs_review(self) -> bool:
        """判断是否需要复核"""
        confidence = self._calculate_confidence()
        if confidence >= HIGH_CONFIDENCE:
            return False
        if confidence >= MEDIUM_CONFIDENCE:
            return True  # 建议复核
        return True  # 需要核实
    
    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """检查日期格式是否合理"""
        if not date_str:
            return False
        # 尝试多种常见日期格式
        formats = [
            "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
            "%Y年%m月%d日", "%m-%d", "%m/%d",
        ]
        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        return False


class InputParser:
    """输入解析器"""
    
    @staticmethod
    def parse_line(line: str) -> Tuple[Optional[Article], Optional[str]]:
        """
        解析单条输入
        
        支持格式：
        - "标题|作者|日期"
        - "标题|作者|日期|内容"
        - "标题|作者|日期|内容|URL"
        
        返回：(文章对象, 错误码或None)
        """
        if not line or not line.strip():
            return None, "E001"
        
        parts = [p.strip() for p in line.split("|")]
        
        # 检查必需字段
        if len(parts) < 3:
            # 如果不足3个字段，检查是否是因为字段为空
            # 例如 "只有标题|" 应该返回E002（缺失字段）
            if len(parts) == 2 and parts[1] == "":
                return None, "E002"
            return None, "E003"
        
        title, author, date = parts[0], parts[1], parts[2]
        
        # 检查字段是否为空
        missing = []
        if not title:
            missing.append("标题")
        if not author:
            missing.append("作者")
        if not date:
            missing.append("日期")
        
        if missing:
            return None, "E002"
        
        # 可选字段
        content = parts[3] if len(parts) > 3 else ""
        url = parts[4] if len(parts) > 4 else ""
        
        return Article(title=title, author=author, date=date,
                      content=content, url=url), None
    
    @staticmethod
    def parse_file(file_path: str) -> Tuple[List[Article], List[str]]:
        """
        解析文件输入
        
        支持格式：每行一条记录，用|分隔字段
        
        返回：(文章列表, 错误列表)
        """
        articles = []
        errors = []
        
        try:
            path = Path(file_path)
            if not path.exists():
                return [], ["E008"]
            
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):  # 跳过空行和注释
                        continue
                    
                    article, error = InputParser.parse_line(line)
                    if error:
                        errors.append(f"第{line_num}行: {ERROR_MESSAGES.get(error, '未知错误')}")
                    else:
                        articles.append(article)
            
            return articles, errors
            
        except Exception as e:
            return [], [f"E008: {str(e)}"]


# ============================================================
# 输出格式化
# ============================================================

class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format_json(articles: List[Article]) -> str:
        """JSON格式输出"""
        return json.dumps(
            [a.to_dict() for a in articles],
            ensure_ascii=False,
            indent=2
        )
    
    @staticmethod
    def format_text(articles: List[Article]) -> str:
        """纯文本格式输出"""
        lines = []
        for i, article in enumerate(articles, 1):
            data = article.to_dict()
            lines.append(f"=== 文章 {i} ===")
            lines.append(f"标题: {data['title']}")
            lines.append(f"作者: {data['author']}")
            lines.append(f"日期: {data['date']}")
            if data.get('content'):
                lines.append(f"内容: {data['content'][:100]}...")
            if data.get('url'):
                lines.append(f"URL: {data['url']}")
            lines.append(f"置信度: {data['confidence']}%")
            if data['needs_review']:
                if data['confidence'] >= MEDIUM_CONFIDENCE:
                    lines.append("状态: 建议复核")
                else:
                    lines.append("状态: [需核实]")
            lines.append("")
        return "\n".join(lines)
    
    @staticmethod
    def format_csv(articles: List[Article]) -> str:
        """CSV格式输出"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 表头
        writer.writerow(["标题", "作者", "日期", "内容", "URL", "置信度", "状态"])
        
        for article in articles:
            data = article.to_dict()
            status = ""
            if data['needs_review']:
                status = "需核实" if data['confidence'] < MEDIUM_CONFIDENCE else "建议复核"
            writer.writerow([
                data['title'],
                data['author'],
                data['date'],
                data.get('content', ''),
                data.get('url', ''),
                f"{data['confidence']}%",
                status,
            ])
        
        return output.getvalue()


# ============================================================
# 核心处理逻辑
# ============================================================

class ArticleProcessor:
    """文章处理器"""
    
    def __init__(self):
        self.parser = InputParser()
        self.formatter = OutputFormatter()
    
    def process_input(self, input_str: str) -> Tuple[Optional[Article], Optional[str]]:
        """
        处理单条输入
        
        返回：(结果字典, 错误码)
        """
        if not input_str or not input_str.strip():
            return None, "E001"
        
        # 检查是否是文件路径
        if input_str.startswith("file:"):
            file_path = input_str[5:]
            articles, errors = self.parser.parse_file(file_path)
            if errors:
                return None, errors[0].split(":")[0] if ":" in errors[0] else "E008"
            if not articles:
                return None, "E001"
            return articles[0], None
        
        # 解析单条输入
        article, error = self.parser.parse_line(input_str)
        if error:
            return None, error
        
        return article, None
    
    def process_batch(self, inputs: List[str]) -> Tuple[List[Article], List[str]]:
        """
        批量处理输入
        
        返回：(文章列表, 错误列表)
        """
        articles = []
        errors = []
        
        for i, input_str in enumerate(inputs, 1):
            article, error = self.process_input(input_str)
            if error:
                errors.append(f"第{i}条: {ERROR_MESSAGES.get(error, '未知错误')}")
            else:
                articles.append(article)
        
        return articles, errors
    
    def format_output(self, articles: List[Article], fmt: str = "json") -> Tuple[Optional[str], Optional[str]]:
        """
        格式化输出
        
        返回：(输出字符串, 错误码)
        """
        if fmt not in SUPPORTED_FORMATS:
            return None, "E006"
        
        if fmt == "json":
            return self.formatter.format_json(articles), None
        elif fmt == "text":
            return self.formatter.format_text(articles), None
        elif fmt == "csv":
            return self.formatter.format_csv(articles), None
        else:
            return None, "E006"


# ============================================================
# 自检功能
# ============================================================

class SelfTest:
    """自检模块 - 使用硬编码样例数据离线验证核心逻辑"""
    
    @staticmethod
    def run() -> bool:
        """
        运行自检
        
        使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、
        不访问网络，任何环境直接可过。
        
        返回：True 表示所有测试通过
        """
        print("=" * 60)
        print("开始自检...")
        print("=" * 60)
        
        all_passed = True
        
        # 测试1: 解析单条输入
        print("\n[测试1] 解析单条输入")
        parser = InputParser()
        test_line = "测试文章标题|测试作者|2026-01-15"
        article, error = parser.parse_line(test_line)
        assert error is None, f"解析失败: {error}"
        assert article is not None, "文章对象为空"
        assert article.title == "测试文章标题", "标题解析错误"
        assert article.author == "测试作者", "作者解析错误"
        assert article.date == "2026-01-15", "日期解析错误"
        print("  ✓ 单条输入解析成功")
        
        # 测试2: 解析完整输入
        print("\n[测试2] 解析完整输入（含内容和URL）")
        test_line_full = "完整文章|作者甲|2026-02-20|这是文章内容摘要|https://mp.weixin.qq.com/s/test123"
        article_full, error = parser.parse_line(test_line_full)
        assert error is None, f"解析失败: {error}"
        assert article_full.content == "这是文章内容摘要", "内容解析错误"
        assert article_full.url == "https://mp.weixin.qq.com/s/test123", "URL解析错误"
        print("  ✓ 完整输入解析成功")
        
        # 测试3: 空输入处理
        print("\n[测试3] 空输入处理")
        _, error = parser.parse_line("")
        assert error == "E001", f"预期E001，实际: {error}"
        print("  ✓ 空输入正确返回E001")
        
        # 测试4: 缺失字段处理
        print("\n[测试4] 缺失字段处理")
        # 测试各种缺失字段情况
        test_cases = [
            ("只有标题|", "E002", "作者和日期缺失"),
            ("标题|作者|", "E002", "日期缺失"),
            ("|作者|日期", "E002", "标题缺失"),
            ("标题||日期", "E002", "作者缺失"),
        ]
        for test_input, expected_error, desc in test_cases:
            _, error = parser.parse_line(test_input)
            assert error == expected_error, f"测试'{test_input}'预期{expected_error}，实际: {error}"
            print(f"  ✓ '{test_input}' 正确返回 {expected_error} ({desc})")
        
        # 测试5: 格式错误处理
        print("\n[测试5] 格式错误处理")
        _, error = parser.parse_line("只有一个字段")
        assert error == "E003", f"预期E003，实际: {error}"
        print("  ✓ 格式错误正确返回E003")
        
        # 测试6: 置信度计算
        print("\n[测试6] 置信度计算")
        # 完整数据的置信度应该较高
        high_conf = article_full._calculate_confidence()
        assert high_conf >= 85, f"完整数据置信度应≥85，实际: {high_conf}"
        print(f"  ✓ 完整数据置信度: {high_conf}%")
        
        # 测试7: 输出格式化
        print("\n[测试7] 输出格式化")
        processor = ArticleProcessor()
        articles = [article, article_full]
        
        # JSON格式
        json_out, error = processor.format_output(articles, "json")
        assert error is None, f"JSON格式化失败: {error}"
        json_data = json.loads(json_out)
        assert len(json_data) == 2, "JSON输出文章数量错误"
        print("  ✓ JSON格式输出成功")
        
        # 文本格式
        text_out, error = processor.format_output(articles, "text")
        assert error is None, f"文本格式化失败: {error}"
        assert "测试文章标题" in text_out, "文本输出缺少标题"
        print("  ✓ 文本格式输出成功")
        
        # CSV格式
        csv_out, error = processor.format_output(articles, "csv")
        assert error is None, f"CSV格式化失败: {error}"
        assert "测试文章标题" in csv_out, "CSV输出缺少标题"
        print("  ✓ CSV格式输出成功")
        
        # 测试8: 不支持的格式
        print("\n[测试8] 不支持的输出格式")
        _, error = processor.format_output(articles, "xml")
        assert error == "E006", f"预期E006，实际: {error}"
        print("  ✓ 不支持格式正确返回E006")
        
        # 测试9: 批量处理
        print("\n[测试9] 批量处理")
        batch_inputs = [
            "批量文章1|作者1|2026-03-01",
            "批量文章2|作者2|2026-03-02",
            "批量文章3|作者3|2026-03-03",
        ]
        batch_articles, errors = processor.process_batch(batch_inputs)
        assert len(batch_articles) == 3, f"批量处理应返回3篇文章，实际: {len(batch_articles)}"
        assert len(errors) == 0, f"批量处理不应有错误，实际: {errors}"
        print(f"  ✓ 批量处理成功，处理{len(batch_articles)}篇文章")
        
        # 测试10: 边界条件
        print("\n[测试10] 边界条件")
        # 最小合法输入
        min_article, error = parser.parse_line("标题|作者|2026-01-01")
        assert error is None, f"最小合法输入解析失败: {error}"
        assert min_article._calculate_confidence() >= 85, "最小合法输入置信度应≥85"
        print("  ✓ 最小合法输入处理成功")
        
        # 日期格式变体
        date_variants = ["2026-01-01", "2026/01/01", "2026.01.01", "2026年1月1日"]
        for date_str in date_variants:
            variant_article, error = parser.parse_line(f"标题|作者|{date_str}")
            assert error is None, f"日期格式{date_str}解析失败: {error}"
        print("  ✓ 多种日期格式处理成功")
        
        # 测试11: 完整流程
        print("\n[测试11] 完整流程测试")
        processor = ArticleProcessor()
        test_input = "端到端测试|测试作者|2026-04-15|这是测试内容|https://example.com/article"
        result, error = processor.process_input(test_input)
        assert error is None, f"端到端处理失败: {error}"
        assert result is not None, "端到端处理结果为空"
        
        output, fmt_error = processor.format_output([result], "json")
        assert fmt_error is None, f"端到端输出失败: {fmt_error}"
        result_data = json.loads(output)
        assert result_data[0]["title"] == "端到端测试", "端到端输出标题错误"
        print("  ✓ 端到端流程测试成功")
        
        # 测试12: 错误消息完整性
        print("\n[测试12] 错误消息完整性")
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code} 的消息"
        print("  ✓ 所有错误码消息完整")
        
        # 测试13: 文件处理（使用临时文件）
        print("\n[测试13] 文件处理")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# 测试文件\n")
            f.write("文件文章1|作者A|2026-05-01\n")
            f.write("文件文章2|作者B|2026-05-02\n")
            f.write("\n")
            f.write("文件文章3|作者C|2026-05-03\n")
            temp_file = f.name
        
        try:
            file_articles, file_errors = parser.parse_file(temp_file)
            assert len(file_articles) == 3, f"文件解析应返回3篇文章，实际: {len(file_articles)}"
            assert len(file_errors) == 0, f"文件解析不应有错误，实际: {file_errors}"
            print("  ✓ 文件解析成功")
        finally:
            # 清理临时文件
            os.unlink(temp_file)
        
        # 测试14: 不存在的文件
        print("\n[测试14] 不存在的文件处理")
        _, file_errors = parser.parse_file("/nonexistent/path/file.txt")
        assert len(file_errors) > 0, "不存在的文件应返回错误"
        print("  ✓ 不存在的文件正确返回错误")
        
        # 总结
        print("\n" + "=" * 60)
        if all_passed:
            print("自检完成：全部测试通过 ✓")
        else:
            print("自检完成：存在失败测试 ✗")
        print("=" * 60)
        
        return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """
    主函数
    
    返回：退出码（0成功，非0失败）
    """
    parser = argparse.ArgumentParser(
        description="公众号文章下载器 - 本地优先的微信内容情报库同步工具",
        epilog="示例: python main.py --input '标题|作者|日期' --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        action="append",
        help="输入内容，格式: 标题|作者|日期[|内容|URL]，可多次使用"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="输入文件路径，每行一条记录"
    )
    
    parser.add_argument(
        "--format", "-fmt",
        choices=SUPPORTED_FORMATS,
        default="json",
        help=f"输出格式，可选: {', '.join(SUPPORTED_FORMATS)}"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件、不依赖工作目录、不访问网络）"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（可选，默认输出到stdout）"
    )
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 运行自检
    if args.selftest:
        success = SelfTest.run()
        return 0 if success else 1
    
    # 检查是否有输入
    if not args.input and not args.file:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        print("使用 --help 查看用法", file=sys.stderr)
        return 1
    
    # 收集输入
    inputs = list(args.input) if args.input else []
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        inputs.append(line)
        except FileNotFoundError:
            print(f"错误 E008: {ERROR_MESSAGES['E008']}: {args.file}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 E008: {ERROR_MESSAGES['E008']}: {str(e)}", file=sys.stderr)
            return 1
    
    # 处理输入
    processor = ArticleProcessor()
    articles, errors = processor.process_batch(inputs)
    
    # 输出错误信息
    if errors:
        for err in errors:
            print(f"警告: {err}", file=sys.stderr)
    
    if not articles:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        return 1
    
    # 格式化输出
    output, fmt_error = processor.format_output(articles, args.format)
    if fmt_error:
        print(f"错误 {fmt_error}: {ERROR_MESSAGES.get(fmt_error, '未知错误')}", file=sys.stderr)
        return 1
    
    # 输出结果
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"结果已保存到: {args.output}")
        except Exception as e:
            print(f"错误 E008: 无法写入文件: {str(e)}", file=sys.stderr)
            return 1
    else:
        print(output)
    
    # 输出统计信息
    print(f"\n处理完成: {len(articles)} 篇文章", file=sys.stderr)
    needs_review = sum(1 for a in articles if a._needs_review())
    if needs_review > 0:
        print(f"注意: {needs_review} 篇文章建议人工复核", file=sys.stderr)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
