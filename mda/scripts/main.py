#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDA 文档编译智能转换工具 - 独立实现

功能：
- 将文本、CSV、JSON 等数据源编译为标准化 Markdown 文档
- 支持置信度标注与字段缺失占位
- 提供批量处理能力
- 内置自检模式

版本：1.0.1
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 常量定义
# ============================================================
VERSION = "1.0.1"
SUPPORTED_EXTENSIONS = {".txt", ".csv", ".json", ".md", ".html"}
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"


# ============================================================
# 错误码定义
# ============================================================
ERROR_MESSAGES = {
    "E001": "未检测到有效输入，请提供数据、文件或 URL",
    "E002": "指定文件路径无法访问，请确认路径正确",
    "E003": "目标 URL 返回错误状态码，无法获取内容",
    "E004": "当前输入格式不在支持范围内（支持: txt/csv/json/html/md）",
    "E005": "无法写入输出目录，请检查权限设置",
    "E006": "批量处理在第 {index} 个文件处中断，请检查该文件格式",
}


# ============================================================
# 数据模型与核心逻辑
# ============================================================
class MDADocument:
    """MDA 文档数据模型"""
    
    def __init__(self, title: str = "", source: str = "", content: str = ""):
        self.title = title
        self.source = source
        self.content = content
        self.fields: Dict[str, Tuple[str, str]] = {}  # 字段名 -> (值, 置信度)
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.overall_confidence = CONFIDENCE_MEDIUM
    
    def add_field(self, name: str, value: Any, confidence: str = CONFIDENCE_MEDIUM) -> None:
        """添加字段及其置信度"""
        # 值缺失时使用占位符
        if value is None or (isinstance(value, str) and not value.strip()):
            value = f"[需核实:{name}]"
            confidence = CONFIDENCE_LOW
        self.fields[name] = (str(value), confidence)
    
    def calculate_overall_confidence(self) -> str:
        """计算整体置信度"""
        if not self.fields:
            return CONFIDENCE_MEDIUM
        
        confidences = [c for _, c in self.fields.values()]
        if CONFIDENCE_LOW in confidences:
            return CONFIDENCE_LOW
        if CONFIDENCE_MEDIUM in confidences:
            return CONFIDENCE_MEDIUM
        return CONFIDENCE_HIGH
    
    def to_markdown(self) -> str:
        """生成标准 Markdown 文档"""
        lines = []
        
        # 标题
        lines.append(f"# {self.title}")
        lines.append("")
        
        # 元信息
        lines.append(f"> 来源: {self.source} | 编译时间: {self.timestamp} | 置信度: {self.calculate_overall_confidence()}")
        lines.append("")
        
        # 内容概览
        lines.append("## 内容概览")
        lines.append("")
        summary = self.content[:200] + ("..." if len(self.content) > 200 else "")
        lines.append(summary)
        lines.append("")
        
        # 详细内容
        lines.append("## 详细内容")
        lines.append("")
        lines.append(self.content)
        lines.append("")
        
        # 数据字段
        lines.append("## 数据字段")
        lines.append("")
        lines.append("| 字段名 | 值 | 置信度 |")
        lines.append("|--------|-----|--------|")
        for field_name, (value, confidence) in self.fields.items():
            lines.append(f"| {field_name} | {value} | {confidence} |")
        lines.append("")
        
        # 原始来源
        lines.append("## 原始来源")
        lines.append("")
        lines.append(self.source)
        lines.append("")
        
        return "\n".join(lines)


class MDAParser:
    """输入解析器"""
    
    @staticmethod
    def parse_text(text: str) -> str:
        """解析纯文本"""
        if not text or not text.strip():
            raise ValueError("E001")
        return text.strip()
    
    @staticmethod
    def parse_csv(content: str) -> Tuple[str, Dict[str, str]]:
        """解析 CSV 内容，返回 (摘要, 字段字典)"""
        reader = csv.DictReader(content.splitlines())
        rows = list(reader)
        if not rows:
            raise ValueError("E001")
        
        # 生成摘要
        summary = f"共 {len(rows)} 条记录，字段: {', '.join(reader.fieldnames or [])}"
        
        # 构建字段（取第一条记录）
        fields = {}
        if rows and reader.fieldnames:
            first_row = rows[0]
            for field in reader.fieldnames:
                fields[field] = first_row.get(field, "")
        
        return summary, fields
    
    @staticmethod
    def parse_json(content: str) -> Tuple[str, Dict[str, Any]]:
        """解析 JSON 内容，返回 (摘要, 字段字典)"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("E004")
        
        if isinstance(data, dict):
            summary = f"JSON 对象，包含 {len(data)} 个键"
            return summary, {k: v for k, v in data.items()}
        elif isinstance(data, list):
            summary = f"JSON 数组，包含 {len(data)} 个元素"
            if data and isinstance(data[0], dict):
                return summary, {k: v for k, v in data[0].items()}
            return summary, {}
        else:
            return f"JSON 标量值: {data}", {}


class MDACompiler:
    """MDA 文档编译器"""
    
    def __init__(self):
        self.parser = MDAParser()
    
    def compile_text(self, text: str, source: str = "直接输入", title: str = "文本文档") -> MDADocument:
        """编译纯文本"""
        content = self.parser.parse_text(text)
        doc = MDADocument(title=title, source=source, content=content)
        doc.add_field("内容长度", len(content), CONFIDENCE_HIGH)
        doc.add_field("来源类型", "文本", CONFIDENCE_HIGH)
        return doc
    
    def compile_csv(self, content: str, source: str = "CSV 数据", title: str = "表格文档") -> MDADocument:
        """编译 CSV 数据"""
        summary, fields = self.parser.parse_csv(content)
        doc = MDADocument(title=title, source=source, content=summary)
        for field_name, value in fields.items():
            confidence = CONFIDENCE_HIGH if value else CONFIDENCE_LOW
            doc.add_field(field_name, value, confidence)
        doc.add_field("记录数量", len(content.splitlines()) - 1, CONFIDENCE_HIGH)
        return doc
    
    def compile_json(self, content: str, source: str = "JSON 数据", title: str = "JSON 文档") -> MDADocument:
        """编译 JSON 数据"""
        summary, fields = self.parser.parse_json(content)
        doc = MDADocument(title=title, source=source, content=summary)
        for field_name, value in fields.items():
            confidence = CONFIDENCE_HIGH if value is not None else CONFIDENCE_LOW
            doc.add_field(field_name, value, confidence)
        return doc
    
    def compile_file(self, file_path: str) -> MDADocument:
        """编译文件"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError("E002")
        
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError("E004")
        
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            content = path.read_text(encoding="gbk")
        
        source = str(path)
        title = path.stem
        
        if ext == ".csv":
            return self.compile_csv(content, source, title)
        elif ext == ".json":
            return self.compile_json(content, source, title)
        else:
            return self.compile_text(content, source, title)
    
    def compile_batch(self, file_paths: List[str], output_dir: str) -> List[str]:
        """批量编译，返回生成的文件路径列表"""
        output_path = Path(output_dir)
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True)
            except PermissionError:
                raise PermissionError("E005")
        
        generated_files = []
        for i, file_path in enumerate(file_paths, 1):
            try:
                doc = self.compile_file(file_path)
                out_file = output_path / f"{Path(file_path).stem}_mda.md"
                out_file.write_text(doc.to_markdown(), encoding="utf-8")
                generated_files.append(str(out_file))
            except Exception as e:
                # 批量处理中断，记录错误并继续
                error_msg = ERROR_MESSAGES["E006"].format(index=i)
                print(f"警告: {error_msg} - {e}")
                continue
        
        return generated_files


# ============================================================
# 自检模块
# ============================================================
class SelfTest:
    """内置自检逻辑，使用硬编码样例数据"""
    
    @staticmethod
    def run() -> bool:
        """运行自检，返回是否全部通过"""
        print("MDA 文档编译器自检开始...")
        all_passed = True
        
        # 测试 1: 文本编译
        print("\n[测试 1] 文本编译")
        try:
            compiler = MDACompiler()
            sample_text = "这是一个测试文档，用于验证 MDA 编译器的基本文本处理功能。"
            doc = compiler.compile_text(sample_text, source="self-test", title="测试文档")
            
            markdown = doc.to_markdown()
            assert "# 测试文档" in markdown, "标题生成失败"
            assert "来源: self-test" in markdown, "来源信息缺失"
            assert "置信度:" in markdown, "置信度标注缺失"
            assert sample_text in markdown, "正文内容缺失"
            print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 2: CSV 编译
        print("\n[测试 2] CSV 编译")
        try:
            sample_csv = "姓名,年龄,城市\n张三,25,北京\n李四,30,上海"
            doc = compiler.compile_csv(sample_csv, source="self-test", title="人员表")
            
            markdown = doc.to_markdown()
            assert "| 姓名 |" in markdown, "CSV 字段表缺失"
            assert "张三" in markdown, "CSV 数据缺失"
            assert "置信度" in markdown, "置信度列缺失"
            assert "人员表" in markdown, "标题生成失败"
            print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 3: JSON 编译
        print("\n[测试 3] JSON 编译")
        try:
            sample_json = '{"name": "产品A", "price": 99.9, "stock": 100}'
            doc = compiler.compile_json(sample_json, source="self-test", title="产品信息")
            
            markdown = doc.to_markdown()
            assert "产品A" in markdown, "JSON 值缺失"
            assert "99.9" in markdown, "JSON 数值缺失"
            assert "产品信息" in markdown, "标题错误"
            print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 4: 字段缺失占位
        print("\n[测试 4] 字段缺失占位")
        try:
            doc = MDADocument(title="测试", source="test", content="内容")
            doc.add_field("缺失字段", None, CONFIDENCE_MEDIUM)
            markdown = doc.to_markdown()
            assert "[需核实:缺失字段]" in markdown, "缺失字段占位符未生成"
            print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 5: 文件编译
        print("\n[测试 5] 文件编译")
        try:
            # 使用临时文件测试
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write("临时文件内容测试")
                temp_path = f.name
            
            try:
                doc = compiler.compile_file(temp_path)
                assert "临时文件内容测试" in doc.content, "文件内容读取失败"
                print("  ✓ 通过")
            finally:
                os.unlink(temp_path)
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 6: 批量处理
        print("\n[测试 6] 批量处理")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 创建两个临时文件
                file1 = os.path.join(tmpdir, "a.txt")
                file2 = os.path.join(tmpdir, "b.txt")
                with open(file1, "w", encoding="utf-8") as f:
                    f.write("文件A内容")
                with open(file2, "w", encoding="utf-8") as f:
                    f.write("文件B内容")
                
                out_dir = os.path.join(tmpdir, "output")
                generated = compiler.compile_batch([file1, file2], out_dir)
                assert len(generated) == 2, f"预期生成 2 个文件，实际 {len(generated)}"
                for g in generated:
                    assert os.path.exists(g), f"文件未生成: {g}"
                    content = Path(g).read_text(encoding="utf-8")
                    assert "# " in content, "Markdown 标题缺失"
                print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 7: 置信度评估
        print("\n[测试 7] 置信度评估")
        try:
            doc = MDADocument(title="测试", source="test", content="内容")
            doc.add_field("完整字段", "值", CONFIDENCE_HIGH)
            doc.add_field("部分字段", "值", CONFIDENCE_MEDIUM)
            assert doc.calculate_overall_confidence() == CONFIDENCE_MEDIUM, "置信度计算错误"
            
            doc2 = MDADocument(title="测试", source="test", content="内容")
            doc2.add_field("字段1", "值", CONFIDENCE_HIGH)
            doc2.add_field("字段2", "值", CONFIDENCE_HIGH)
            assert doc2.calculate_overall_confidence() == CONFIDENCE_HIGH, "置信度计算错误"
            print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 8: 错误处理
        print("\n[测试 8] 错误处理")
        try:
            # 文件不存在
            try:
                compiler.compile_file("/nonexistent/path/file.txt")
                all_passed = False
                print("  ✗ 失败: 预期抛错但未抛出")
            except FileNotFoundError:
                print("  ✓ 通过")
            
            # 空输入
            try:
                compiler.compile_text("", source="test", title="test")
                all_passed = False
                print("  ✗ 失败: 预期抛错但未抛出")
            except ValueError:
                print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 9: Markdown 结构完整性
        print("\n[测试 9] Markdown 结构完整性")
        try:
            doc = compiler.compile_text("结构测试内容", source="test", title="结构测试")
            markdown = doc.to_markdown()
            
            # 检查必需段落
            required_sections = ["# ", "> 来源:", "## 内容概览", "## 详细内容", "## 数据字段", "## 原始来源"]
            for section in required_sections:
                assert section in markdown, f"缺少必需段落: {section}"
            
            # 检查表格格式
            assert "| 字段名 | 值 | 置信度 |" in markdown, "表格头部格式错误"
            assert "|--------|-----|--------|" in markdown, "表格分隔符格式错误"
            print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        # 测试 10: 批量处理错误恢复
        print("\n[测试 10] 批量处理错误恢复")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                good_file = os.path.join(tmpdir, "good.txt")
                with open(good_file, "w", encoding="utf-8") as f:
                    f.write("正常文件内容")
                
                # 一个不存在的文件 + 一个正常文件
                out_dir = os.path.join(tmpdir, "out")
                generated = compiler.compile_batch(["/nonexistent/file.txt", good_file], out_dir)
                assert len(generated) >= 1, "至少应生成一个文件"
                assert os.path.exists(generated[0]), "生成的文件不存在"
                print("  ✓ 通过")
        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {e}")
        
        print("\n" + ("=" * 40))
        if all_passed:
            print("自检完成: 全部通过 ✓")
        else:
            print("自检完成: 存在失败项 ✗")
        print("=" * 40)
        return all_passed


# ============================================================
# CLI 入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="MDA 文档编译智能转换工具",
        epilog="示例: mda input.csv -o output.md"
    )
    parser.add_argument("input", nargs="?", help="输入文件路径、URL 或直接文本")
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--batch", nargs="+", help="批量处理多个文件")
    parser.add_argument("--outdir", help="批量输出目录")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="store_true", help="显示版本号")
    
    args = parser.parse_args()
    
    # 版本显示
    if args.version:
        print(f"mda 版本 {VERSION}")
        return 0
    
    # 自检模式
    if args.selftest:
        success = SelfTest.run()
        return 0 if success else 1
    
    compiler = MDACompiler()
    
    # 批量处理
    if args.batch:
        if not args.outdir:
            print("错误: 批量处理需要指定 --outdir 参数", file=sys.stderr)
            return 1
        try:
            generated = compiler.compile_batch(args.batch, args.outdir)
            print(f"批量处理完成，生成 {len(generated)} 个文件:")
            for g in generated:
                print(f"  - {g}")
            return 0
        except Exception as e:
            error_code = str(e) if str(e).startswith("E") else "E006"
            print(f"错误 [{error_code}]: {ERROR_MESSAGES.get(error_code, str(e))}", file=sys.stderr)
            return 1
    
    # 单文件处理
    if args.input:
        try:
            # 判断是否为文件路径
            if os.path.exists(args.input):
                doc = compiler.compile_file(args.input)
            else:
                # 尝试作为文本处理
                doc = compiler.compile_text(args.input, source="命令行输入", title="命令行文档")
            
            markdown = doc.to_markdown()
            
            if args.output:
                try:
                    Path(args.output).write_text(markdown, encoding="utf-8")
                    print(f"文档已生成: {args.output}")
                except PermissionError:
                    print("错误 [E005]: 无法写入输出文件，请检查权限", file=sys.stderr)
                    return 1
            else:
                print(markdown)
            return 0
        except FileNotFoundError:
            print("错误 [E002]: 指定文件路径无法访问，请确认路径正确", file=sys.stderr)
            return 1
        except ValueError as e:
            error_code = str(e) if str(e).startswith("E") else "E001"
            print(f"错误 [{error_code}]: {ERROR_MESSAGES.get(error_code, str(e))}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    
    # 无输入参数
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
