#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sop-packager 独立实现脚本
功能：将重复性操作整理为标准作业程序（SOP），供AI自动执行。
本脚本为 clean-room 实现，仅依据功能规格独立编写。
"""

import sys
import json
import argparse
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "输入内容为空",
    "E002": "输入格式不支持",
    "E003": "无法解析输入内容",
    "E004": "输出格式不支持",
    "E005": "批量处理失败",
    "E006": "自定义字段配置错误",
    "E007": "文件读取失败",
    "E008": "URL访问失败",
    "E009": "内部处理异常",
    "E010": "参数配置错误",
}


class SOPError(Exception):
    """SOP处理异常类"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


class SOPExtractor:
    """
    SOP信息提取器
    从非结构化文本中提取动作、条件、责任人、时限等要素
    """
    
    # 动作关键词（宽松匹配）
    ACTION_PATTERNS = [
        r"(?:请|需要|必须|应当|应)?(?:执行|进行|完成|操作|设置|配置|检查|确认|验证|提交|发送|接收|创建|删除|更新|修改|启动|停止|重启|安装|卸载|备份|恢复|导出|导入)",
        r"(?:点击|打开|关闭|输入|选择|勾选|取消|保存|加载|上传|下载|连接|断开|授权|审批|通知|报告|记录|登记|整理|归档|清理|扫描|检测|测试)",
    ]
    
    # 条件关键词
    CONDITION_PATTERNS = [
        r"如果|若|当|如遇|一旦|除非|只有|必须满足|前提|条件",
        r"在.{0,20}情况下|当.{0,20}时",
    ]
    
    # 责任人关键词
    OWNER_PATTERNS = [
        r"(?:由|交给|指定|通知)\s*([\u4e00-\u9fa5A-Za-z0-9_]+)",
        r"责任人[:：]\s*([\u4e00-\u9fa5A-Za-z0-9_]+)",
        r"负责人[:：]\s*([\u4e00-\u9fa5A-Za-z0-9_]+)",
    ]
    
    # 时限关键词
    DEADLINE_PATTERNS = [
        r"(?:在|于)?\s*(\d+\s*(?:分钟|小时|天|周|月|年))\s*(?:内|之内|以内|前|之前)",
        r"(?:截止|最晚|不迟于)\s*([\d年月日:：\s]+)",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ]
    
    def __init__(self, min_confidence: float = 0.3):
        """初始化提取器
        
        Args:
            min_confidence: 最小置信度阈值，低于此值的字段标注为低置信度
        """
        self.min_confidence = min_confidence
    
    def extract(self, text: str) -> Dict[str, Any]:
        """从文本中提取SOP要素
        
        Args:
            text: 输入的非结构化文本
            
        Returns:
            结构化SOP数据字典
        """
        if not text or not text.strip():
            raise SOPError("E001")
        
        steps = self._extract_steps(text)
        if not steps:
            # 尝试将整个文本作为一个步骤
            steps = [self._parse_step(text)]
        
        # 提取全局信息
        title = self._extract_title(text)
        owner = self._extract_owner(text)
        deadline = self._extract_deadline(text)
        
        # 计算整体置信度
        confidence = self._calculate_confidence(steps)
        
        return {
            "title": title,
            "owner": owner,
            "deadline": deadline,
            "steps": steps,
            "confidence": confidence,
            "metadata": {
                "extracted_at": datetime.now().isoformat(),
                "source_type": "text",
                "step_count": len(steps),
            },
            "warnings": self._generate_warnings(steps, confidence),
        }
    
    def _extract_steps(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取步骤列表"""
        # 按常见步骤标记分割
        lines = text.split('\n')
        steps = []
        current_step = []
        step_pattern = re.compile(r'^\s*(?:步骤|第[一二三四五六七八九十\d]+步|Step\s*\d+|\d+[\.、)])')
        
        for line in lines:
            if step_pattern.match(line) and current_step:
                # 完成当前步骤
                step_text = '\n'.join(current_step).strip()
                if step_text:
                    steps.append(self._parse_step(step_text))
                current_step = [line]
            else:
                current_step.append(line)
        
        # 处理最后一个步骤
        if current_step:
            step_text = '\n'.join(current_step).strip()
            if step_text:
                steps.append(self._parse_step(step_text))
        
        return steps
    
    def _parse_step(self, text: str) -> Dict[str, Any]:
        """解析单个步骤"""
        step = {
            "description": text.strip(),
            "action": None,
            "condition": None,
            "owner": None,
            "deadline": None,
            "confidence": 0.5,  # 默认中等置信度
        }
        
        # 提取动作
        for pattern in self.ACTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                step["action"] = match.group(0)
                step["confidence"] = min(0.9, step["confidence"] + 0.2)
                break
        
        # 提取条件
        for pattern in self.CONDITION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                step["condition"] = match.group(0)
                step["confidence"] = min(0.9, step["confidence"] + 0.1)
                break
        
        # 提取责任人
        owner = self._extract_owner(text)
        if owner:
            step["owner"] = owner
            step["confidence"] = min(0.9, step["confidence"] + 0.1)
        
        # 提取时限
        deadline = self._extract_deadline(text)
        if deadline:
            step["deadline"] = deadline
            step["confidence"] = min(0.9, step["confidence"] + 0.1)
        
        return step
    
    def _extract_title(self, text: str) -> Optional[str]:
        """提取标题"""
        # 查找标题模式
        patterns = [
            r'^#+\s*(.+)$',  # Markdown标题
            r'^(?:标题|名称|主题)[:：]\s*(.+)$',
            r'^《(.+)》$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # 默认使用第一行作为标题
        first_line = text.strip().split('\n')[0]
        if len(first_line) <= 50:
            return first_line
        return None
    
    def _extract_owner(self, text: str) -> Optional[str]:
        """提取责任人"""
        for pattern in self.OWNER_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """提取时限"""
        for pattern in self.DEADLINE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None
    
    def _calculate_confidence(self, steps: List[Dict[str, Any]]) -> float:
        """计算整体置信度"""
        if not steps:
            return 0.0
        
        # 平均各步骤置信度
        step_confidences = [step.get("confidence", 0.5) for step in steps]
        avg_confidence = sum(step_confidences) / len(step_confidences)
        
        # 根据步骤信息完整度调整
        complete_steps = 0
        for step in steps:
            if step.get("action") and step.get("condition"):
                complete_steps += 1
        
        completeness_factor = complete_steps / len(steps) if steps else 0
        
        return round(min(0.95, avg_confidence * 0.7 + completeness_factor * 0.3), 2)
    
    def _generate_warnings(self, steps: List[Dict[str, Any]], confidence: float) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        if confidence < self.min_confidence:
            warnings.append("整体置信度较低，建议人工复核提取结果")
        
        for i, step in enumerate(steps, 1):
            if not step.get("action"):
                warnings.append(f"步骤{i}可能缺少明确的动作描述")
            if not step.get("condition"):
                warnings.append(f"步骤{i}可能缺少条件说明")
        
        return warnings


class SOPFormatter:
    """SOP格式化输出器"""
    
    SUPPORTED_FORMATS = ["json", "markdown", "md", "text", "txt"]
    
    def __init__(self):
        """初始化格式化器"""
        pass
    
    def format(self, data: Dict[str, Any], output_format: str = "json") -> str:
        """格式化输出
        
        Args:
            data: SOP数据字典
            output_format: 输出格式（json/markdown/text）
            
        Returns:
            格式化后的字符串
        """
        fmt = output_format.lower().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            raise SOPError("E004", f"不支持的输出格式: {output_format}")
        
        if fmt == "json":
            return self._format_json(data)
        elif fmt in ("markdown", "md"):
            return self._format_markdown(data)
        else:
            return self._format_text(data)
    
    def _format_json(self, data: Dict[str, Any]) -> str:
        """JSON格式输出"""
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def _format_markdown(self, data: Dict[str, Any]) -> str:
        """Markdown格式输出"""
        lines = []
        
        # 标题
        title = data.get("title") or "标准作业程序"
        lines.append(f"# {title}")
        lines.append("")
        
        # 元信息
        lines.append("## 基本信息")
        lines.append("")
        lines.append(f"- **责任人**: {data.get('owner') or '未指定'}")
        lines.append(f"- **完成时限**: {data.get('deadline') or '未指定'}")
        lines.append(f"- **置信度**: {data.get('confidence', 0):.0%}")
        lines.append(f"- **步骤数**: {len(data.get('steps', []))}")
        lines.append("")
        
        # 步骤
        lines.append("## 操作步骤")
        lines.append("")
        for i, step in enumerate(data.get("steps", []), 1):
            lines.append(f"### 步骤 {i}")
            lines.append("")
            lines.append(f"**描述**: {step.get('description', '')}")
            if step.get("action"):
                lines.append(f"- 动作: {step['action']}")
            if step.get("condition"):
                lines.append(f"- 条件: {step['condition']}")
            if step.get("owner"):
                lines.append(f"- 责任人: {step['owner']}")
            if step.get("deadline"):
                lines.append(f"- 时限: {step['deadline']}")
            lines.append(f"- 置信度: {step.get('confidence', 0):.0%}")
            lines.append("")
        
        # 警告
        if data.get("warnings"):
            lines.append("## 注意事项")
            lines.append("")
            for warning in data["warnings"]:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_text(self, data: Dict[str, Any]) -> str:
        """纯文本格式输出"""
        lines = []
        
        title = data.get("title") or "标准作业程序"
        lines.append(f"标题: {title}")
        lines.append(f"责任人: {data.get('owner') or '未指定'}")
        lines.append(f"完成时限: {data.get('deadline') or '未指定'}")
        lines.append(f"置信度: {data.get('confidence', 0):.0%}")
        lines.append("")
        
        lines.append("操作步骤:")
        for i, step in enumerate(data.get("steps", []), 1):
            lines.append(f"  {i}. {step.get('description', '')}")
            if step.get("action"):
                lines.append(f"     动作: {step['action']}")
            if step.get("condition"):
                lines.append(f"     条件: {step['condition']}")
            if step.get("owner"):
                lines.append(f"     责任人: {step['owner']}")
            if step.get("deadline"):
                lines.append(f"     时限: {step['deadline']}")
        
        if data.get("warnings"):
            lines.append("")
            lines.append("注意事项:")
            for warning in data["warnings"]:
                lines.append(f"  ⚠️ {warning}")
        
        return "\n".join(lines)


class SOPProcessor:
    """SOP主处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.extractor = SOPExtractor()
        self.formatter = SOPFormatter()
    
    def process(self, content: str, output_format: str = "json") -> str:
        """处理文本内容生成SOP
        
        Args:
            content: 输入文本内容
            output_format: 输出格式
            
        Returns:
            格式化后的SOP字符串
        """
        try:
            # 提取SOP数据
            data = self.extractor.extract(content)
            # 格式化输出
            return self.formatter.format(data, output_format)
        except SOPError:
            raise
        except Exception as e:
            raise SOPError("E009", f"处理失败: {str(e)}")
    
    def process_batch(self, contents: List[str], output_format: str = "json") -> List[str]:
        """批量处理多个文本内容
        
        Args:
            contents: 文本内容列表
            output_format: 输出格式
            
        Returns:
            格式化后的SOP字符串列表
        """
        if not contents:
            raise SOPError("E001")
        
        results = []
        for i, content in enumerate(contents):
            try:
                results.append(self.process(content, output_format))
            except SOPError as e:
                results.append(json.dumps({
                    "error": e.code,
                    "message": str(e),
                    "index": i,
                }, ensure_ascii=False))
        
        return results
    
    def process_file(self, file_path: str, output_format: str = "json") -> str:
        """处理文件内容生成SOP
        
        Args:
            file_path: 文件路径
            output_format: 输出格式
            
        Returns:
            格式化后的SOP字符串
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.process(content, output_format)
        except FileNotFoundError:
            raise SOPError("E007", f"文件不存在: {file_path}")
        except PermissionError:
            raise SOPError("E007", f"无权读取文件: {file_path}")
        except UnicodeDecodeError:
            raise SOPError("E007", f"文件编码不支持: {file_path}")
        except SOPError:
            raise
        except Exception as e:
            raise SOPError("E009", f"文件处理失败: {str(e)}")


def run_selftest() -> bool:
    """
    内置自检函数
    使用硬编码样例数据离线测试核心逻辑，不依赖外部文件或网络。
    
    Returns:
        True 表示自检通过
    """
    print("=" * 60)
    print("SOP Packager 自检程序")
    print("=" * 60)
    
    # 创建处理器
    processor = SOPProcessor()
    
    # 测试用例1：基本文本处理
    print("\n[测试1] 基本文本处理...")
    sample_text = """
    # 服务器部署流程
    
    步骤1: 检查服务器硬件配置，确保满足最低要求。
    步骤2: 如果系统未安装Linux，请安装Ubuntu 20.04操作系统。
    步骤3: 由运维人员配置网络，在1小时内完成。
    步骤4: 安装必要的软件依赖包。
    步骤5: 部署应用程序并验证服务正常运行。
    """
    
    try:
        result = processor.process(sample_text, "json")
        data = json.loads(result)
        assert data.get("title") is not None, "标题不应为空"
        assert len(data.get("steps", [])) >= 3, "步骤数应至少为3"
        assert data.get("confidence", 0) >= 0.3, "置信度应不低于0.3"
        print("  ✓ JSON格式处理通过")
    except Exception as e:
        print(f"  ✗ JSON格式处理失败: {e}")
        return False
    
    # 测试用例2：Markdown格式输出
    print("\n[测试2] Markdown格式输出...")
    try:
        result = processor.process(sample_text, "markdown")
        assert "#" in result, "Markdown输出应包含标题标记"
        assert "步骤" in result, "Markdown输出应包含步骤"
        print("  ✓ Markdown格式输出通过")
    except Exception as e:
        print(f"  ✗ Markdown格式输出失败: {e}")
        return False
    
    # 测试用例3：批量处理
    print("\n[测试3] 批量处理...")
    try:
        contents = [
            "步骤1: 登录系统\n步骤2: 修改配置文件",
            "步骤1: 备份数据库\n步骤2: 如果备份成功，执行更新",
        ]
        results = processor.process_batch(contents, "text")
        assert len(results) == 2, "应返回2个结果"
        assert all(r for r in results), "所有结果不应为空"
        print("  ✓ 批量处理通过")
    except Exception as e:
        print(f"  ✗ 批量处理失败: {e}")
        return False
    
    # 测试用例4：边界情况
    print("\n[测试4] 边界情况处理...")
    try:
        # 空输入
        try:
            processor.process("", "json")
            print("  ✗ 空输入应抛出异常")
            return False
        except SOPError as e:
            assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
            print("  ✓ 空输入错误处理通过")
        
        # 无效输出格式
        try:
            processor.process(sample_text, "xml")
            print("  ✗ 无效格式应抛出异常")
            return False
        except SOPError as e:
            assert e.code == "E004", f"错误码应为E004，实际为{e.code}"
            print("  ✓ 无效格式错误处理通过")
    except Exception as e:
        print(f"  ✗ 边界情况处理失败: {e}")
        return False
    
    # 测试用例5：要素提取验证
    print("\n[测试5] 要素提取验证...")
    try:
        extractor = SOPExtractor()
        data = extractor.extract(sample_text)
        
        # 验证动作提取
        actions = [step.get("action") for step in data["steps"] if step.get("action")]
        assert len(actions) >= 2, f"应提取至少2个动作，实际{len(actions)}个"
        print(f"  ✓ 动作提取通过（{len(actions)}个动作）")
        
        # 验证条件提取
        conditions = [step.get("condition") for step in data["steps"] if step.get("condition")]
        assert len(conditions) >= 1, "应提取至少1个条件"
        print(f"  ✓ 条件提取通过（{len(conditions)}个条件）")
        
        # 验证责任人提取
        owners = [step.get("owner") for step in data["steps"] if step.get("owner")]
        assert len(owners) >= 1, "应提取至少1个责任人"
        print(f"  ✓ 责任人提取通过（{len(owners)}个责任人）")
        
        # 验证时限提取
        deadlines = [step.get("deadline") for step in data["steps"] if step.get("deadline")]
        assert len(deadlines) >= 1, "应提取至少1个时限"
        print(f"  ✓ 时限提取通过（{len(deadlines)}个时限）")
    except Exception as e:
        print(f"  ✗ 要素提取验证失败: {e}")
        return False
    
    # 测试用例6：置信度标注
    print("\n[测试6] 置信度标注验证...")
    try:
        extractor = SOPExtractor(min_confidence=0.5)
        data = extractor.extract(sample_text)
        
        # 验证置信度范围
        assert 0 <= data["confidence"] <= 1, "置信度应在0-1之间"
        
        # 验证低置信度警告
        low_conf_text = "做一些操作"
        low_conf_data = extractor.extract(low_conf_text)
        assert len(low_conf_data["warnings"]) >= 1, "低置信度应产生警告"
        print("  ✓ 置信度标注验证通过")
    except Exception as e:
        print(f"  ✗ 置信度标注验证失败: {e}")
        return False
    
    # 测试用例7：幂等性验证
    print("\n[测试7] 幂等性验证...")
    try:
        result1 = processor.process(sample_text, "json")
        result2 = processor.process(sample_text, "json")
        assert result1 == result2, "重复处理结果应一致"
        print("  ✓ 幂等性验证通过")
    except Exception as e:
        print(f"  ✗ 幂等性验证失败: {e}")
        return False
    
    # 测试用例8：超时与重试策略验证（模拟）
    print("\n[测试8] 稳定性策略验证...")
    try:
        # 验证单条失败不中断整批
        contents = [
            "正常步骤1\n步骤2: 执行操作",
            "",  # 空内容应失败
            "步骤1: 备份数据",
        ]
        results = processor.process_batch(contents, "json")
        assert len(results) == 3, "应返回3个结果"
        assert "error" in results[1], "空内容应产生错误结果"
        assert "error" not in results[0], "正常内容不应产生错误"
        assert "error" not in results[2], "正常内容不应产生错误"
        print("  ✓ 单条失败不中断整批验证通过")
    except Exception as e:
        print(f"  ✗ 稳定性策略验证失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ 所有自检测试通过！")
    print("=" * 60)
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SOP Packager - 流程封装与标准作业程序生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --text "步骤1: 检查配置" --format json
  %(prog)s --file input.txt --format markdown
  %(prog)s --selftest
        """
    )
    
    # 输入参数（互斥）
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--text", type=str, help="输入文本内容")
    input_group.add_argument("--file", type=str, help="输入文件路径")
    input_group.add_argument("--selftest", action="store_true", help="运行内置自检程序")
    
    # 输出参数
    parser.add_argument("--format", type=str, default="json", 
                       choices=["json", "markdown", "md", "text", "txt"],
                       help="输出格式（默认: json）")
    parser.add_argument("--output", type=str, help="输出文件路径（不指定则输出到控制台）")
    
    # 批量处理参数
    parser.add_argument("--batch", action="store_true", help="批量处理模式（从标准输入读取JSON数组）")
    
    args = parser.parse_args()
    
    try:
        # 自检模式
        if args.selftest:
            success = run_selftest()
            sys.exit(0 if success else 1)
        
        # 批量处理模式
        if args.batch:
            try:
                contents = json.load(sys.stdin)
                if not isinstance(contents, list):
                    raise SOPError("E006", "批量模式需要JSON数组输入")
            except json.JSONDecodeError:
                raise SOPError("E006", "批量模式需要有效的JSON数组输入")
            
            processor = SOPProcessor()
            results = processor.process_batch(contents, args.format)
            
            output_text = json.dumps(results, ensure_ascii=False, indent=2)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"处理完成，结果已保存到: {args.output}")
            else:
                print(output_text)
            return
        
        # 单次处理模式
        if not args.text and not args.file:
            parser.print_help()
            sys.exit(0)
        
        processor = SOPProcessor()
        
        if args.text:
            result = processor.process(args.text, args.format)
        elif args.file:
            result = processor.process_file(args.file, args.format)
        else:
            raise SOPError("E010", "必须指定 --text 或 --file 参数")
        
        # 输出结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"处理完成，结果已保存到: {args.output}")
        else:
            print(result)
            
    except SOPError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
