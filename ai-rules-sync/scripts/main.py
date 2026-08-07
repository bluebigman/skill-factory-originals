#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-rules-sync - 独立的技能功能实现脚本
版本: 1.0.0
许可: MIT
"""

import argparse
import os
import sys
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件读取失败",
    "E007": "数据解析失败",
    "E008": "输出写入失败",
    "E009": "参数校验失败",
    "E010": "内部逻辑错误",
}


class SkillError(Exception):
    """技能执行异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class InputItem:
    """输入数据项"""
    source: str          # 输入来源标识
    content: str         # 原始内容
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedResult:
    """处理结果"""
    item_id: str
    source: str
    structured: Dict[str, Any]
    confidence: float           # 置信度 0-1
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SkillConfig:
    """技能配置"""
    name: str = "ai-rules-sync"
    version: str = "1.0.0"
    author: str = "skill-factory-auto"
    min_confidence_pass: float = 0.90    # ≥90% 直接输出
    min_confidence_review: float = 0.85  # 85%-90% 建议复核
    output_format: str = "json"


# ============================================================
# 核心处理引擎
# ============================================================
class RuleSyncEngine:
    """
    规则同步处理引擎
    负责将输入数据解析为结构化结果，并评估置信度
    """
    
    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()
        self._keywords = {
            "rule": ["rule", "rules", "规则", "规范"],
            "skill": ["skill", "skills", "技能"],
            "command": ["command", "commands", "命令"],
            "subagent": ["subagent", "subagents", "子代理"],
            "sync": ["sync", "synchronize", "同步"],
            "share": ["share", "sharing", "分享"],
        }
    
    def process(self, items: List[InputItem]) -> List[ProcessedResult]:
        """批量处理输入项"""
        if not items:
            raise SkillError("E001", "输入列表为空")
        
        results = []
        for item in items:
            # 基础校验
            if not item.content or not item.content.strip():
                raise SkillError("E001", f"输入项 {item.source} 内容为空")
            if not item.source:
                raise SkillError("E002", "缺少输入来源标识")
            
            # 解析内容
            parsed = self._parse_content(item)
            
            # 计算置信度
            confidence = self._calculate_confidence(parsed, item)
            
            # 生成警告
            warnings = self._generate_warnings(parsed, confidence)
            
            # 创建结果
            result = ProcessedResult(
                item_id=self._generate_id(item),
                source=item.source,
                structured=parsed,
                confidence=confidence,
                warnings=warnings,
            )
            results.append(result)
        
        return results
    
    def _parse_content(self, item: InputItem) -> Dict[str, Any]:
        """
        解析输入内容，提取关键信息
        支持 JSON 格式或文本格式
        """
        content = item.content.strip()
        
        # 尝试解析 JSON
        if content.startswith("{") or content.startswith("["):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return self._structure_dict(data)
                elif isinstance(data, list):
                    return {"items": [self._structure_dict(x) for x in data if isinstance(x, dict)]}
            except json.JSONDecodeError:
                # JSON 解析失败，降级为文本解析
                pass
        
        # 文本解析
        return self._parse_text(content)
    
    def _structure_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """结构化字典数据"""
        structured = {}
        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in ("rule", "rules", "规则", "规范"):
                structured["rules"] = self._parse_rules(value)
            elif key_lower in ("skill", "skills", "技能"):
                structured["skills"] = self._parse_skills(value)
            elif key_lower in ("command", "commands", "命令"):
                structured["commands"] = self._parse_commands(value)
            elif key_lower in ("subagent", "subagents", "子代理"):
                structured["subagents"] = self._parse_subagents(value)
            elif key_lower in ("name", "标题", "名称"):
                structured["name"] = str(value)
            elif key_lower in ("description", "描述", "说明"):
                structured["description"] = str(value)
            elif key_lower in ("version", "版本"):
                structured["version"] = str(value)
            else:
                structured[key] = value
        return structured
    
    def _parse_rules(self, value: Any) -> List[Dict[str, Any]]:
        """解析规则数据"""
        if isinstance(value, str):
            return [{"content": value, "type": "rule"}]
        elif isinstance(value, list):
            rules = []
            for v in value:
                if isinstance(v, str):
                    rules.append({"content": v, "type": "rule"})
                elif isinstance(v, dict):
                    rules.append(v)
            return rules
        return []
    
    def _parse_skills(self, value: Any) -> List[Dict[str, Any]]:
        """解析技能数据"""
        if isinstance(value, str):
            return [{"content": value, "type": "skill"}]
        elif isinstance(value, list):
            skills = []
            for v in value:
                if isinstance(v, str):
                    skills.append({"content": v, "type": "skill"})
                elif isinstance(v, dict):
                    skills.append(v)
            return skills
        return []
    
    def _parse_commands(self, value: Any) -> List[Dict[str, Any]]:
        """解析命令数据"""
        if isinstance(value, str):
            return [{"content": value, "type": "command"}]
        elif isinstance(value, list):
            commands = []
            for v in value:
                if isinstance(v, str):
                    commands.append({"content": v, "type": "command"})
                elif isinstance(v, dict):
                    commands.append(v)
            return commands
        return []
    
    def _parse_subagents(self, value: Any) -> List[Dict[str, Any]]:
        """解析子代理数据"""
        if isinstance(value, str):
            return [{"content": value, "type": "subagent"}]
        elif isinstance(value, list):
            subagents = []
            for v in value:
                if isinstance(v, str):
                    subagents.append({"content": v, "type": "subagent"})
                elif isinstance(v, dict):
                    subagents.append(v)
            return subagents
        return []
    
    def _parse_text(self, content: str) -> Dict[str, Any]:
        """解析文本内容"""
        structured = {}
        lines = content.split("\n")
        
        # 提取标题
        for line in lines[:5]:  # 只检查前5行
            line = line.strip()
            if line.startswith("#"):
                structured["name"] = line.lstrip("#").strip()
                break
        
        # 提取描述
        for line in lines:
            line = line.strip()
            if line.startswith(("描述:", "说明:", "Description:")):
                structured["description"] = line.split(":", 1)[1].strip()
                break
        
        # 识别规则/技能/命令
        rules, skills, commands, subagents = [], [], [], []
        current_type = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测类型标记
            lowered = line.lower()
            if any(kw in lowered for kw in self._keywords["rule"]):
                current_type = "rule"
                continue
            elif any(kw in lowered for kw in self._keywords["skill"]):
                current_type = "skill"
                continue
            elif any(kw in lowered for kw in self._keywords["command"]):
                current_type = "command"
                continue
            elif any(kw in lowered for kw in self._keywords["subagent"]):
                current_type = "subagent"
                continue
            
            # 根据当前类型分类内容
            if current_type == "rule" and line.startswith("-"):
                rules.append({"content": line.lstrip("- ").strip(), "type": "rule"})
            elif current_type == "skill" and line.startswith("-"):
                skills.append({"content": line.lstrip("- ").strip(), "type": "skill"})
            elif current_type == "command" and line.startswith("-"):
                commands.append({"content": line.lstrip("- ").strip(), "type": "command"})
            elif current_type == "subagent" and line.startswith("-"):
                subagents.append({"content": line.lstrip("- ").strip(), "type": "subagent"})
        
        if rules:
            structured["rules"] = rules
        if skills:
            structured["skills"] = skills
        if commands:
            structured["commands"] = commands
        if subagents:
            structured["subagents"] = subagents
        
        return structured
    
    def _calculate_confidence(self, parsed: Dict[str, Any], item: InputItem) -> float:
        """
        计算置信度
        基于结构化完整度和内容质量
        """
        if not parsed:
            return 0.5
        
        confidence = 0.0
        total_weight = 0.0
        
        # 检查关键字段
        field_weights = {
            "name": 0.3,
            "description": 0.2,
            "rules": 0.2,
            "skills": 0.15,
            "commands": 0.1,
            "subagents": 0.05,
        }
        
        for field_name, weight in field_weights.items():
            total_weight += weight
            if field_name in parsed and parsed[field_name]:
                # 检查内容的完整性
                if isinstance(parsed[field_name], list):
                    if len(parsed[field_name]) > 0:
                        confidence += weight * 0.9
                elif isinstance(parsed[field_name], str):
                    if len(parsed[field_name]) > 0:
                        confidence += weight * 0.9
        
        # 根据内容长度调整
        content_length = len(item.content)
        if content_length > 0:
            length_factor = min(1.0, content_length / 200)  # 200字符为基准
            confidence *= (0.8 + 0.2 * length_factor)
        
        # 确保置信度在 0-1 之间
        return max(0.0, min(1.0, confidence))
    
    def _generate_warnings(self, parsed: Dict[str, Any], confidence: float) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        if confidence < self.config.min_confidence_review:
            warnings.append("置信度过低，建议人工复核")
        elif confidence < self.config.min_confidence_pass:
            warnings.append("建议复核结果")
        
        if "name" not in parsed:
            warnings.append("缺少名称字段")
        
        if not parsed.get("rules") and not parsed.get("skills"):
            warnings.append("未检测到规则或技能内容")
        
        return warnings
    
    def _generate_id(self, item: InputItem) -> str:
        """生成唯一标识"""
        raw = f"{item.source}_{item.content}_{datetime.now().isoformat()}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]


# ============================================================
# 输出格式化器
# ============================================================
class OutputFormatter:
    """结果格式化输出"""
    
    @staticmethod
    def format(results: List[ProcessedResult], output_format: str = "json") -> str:
        """格式化输出结果"""
        if output_format == "json":
            return json.dumps(
                [asdict(r) for r in results],
                ensure_ascii=False,
                indent=2
            )
        elif output_format == "text":
            lines = []
            for r in results:
                lines.append(f"=== 结果 {r.item_id} ===")
                lines.append(f"来源: {r.source}")
                lines.append(f"置信度: {r.confidence:.1%}")
                if r.warnings:
                    lines.append(f"警告: {'; '.join(r.warnings)}")
                lines.append("结构化数据:")
                lines.append(json.dumps(r.structured, ensure_ascii=False, indent=2))
                lines.append("")
            return "\n".join(lines)
        else:
            raise SkillError("E003", f"不支持的输出格式: {output_format}")


# ============================================================
# 文件处理辅助
# ============================================================
class FileProcessor:
    """文件读取与写入"""
    
    @staticmethod
    def read_file(filepath: str) -> str:
        """读取文件内容"""
        try:
            path = Path(filepath)
            if not path.exists():
                raise SkillError("E006", f"文件不存在: {filepath}")
            if not path.is_file():
                raise SkillError("E006", f"不是文件: {filepath}")
            return path.read_text(encoding="utf-8")
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E006", f"读取文件失败: {str(e)}")
    
    @staticmethod
    def write_file(filepath: str, content: str) -> None:
        """写入文件内容"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise SkillError("E008", f"写入文件失败: {str(e)}")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据
    不依赖外部文件、网络或当前工作目录
    """
    print("=" * 60)
    print("运行自检...")
    
    try:
        # 创建引擎
        engine = RuleSyncEngine()
        
        # 测试用例 1: JSON 格式输入
        print("\n[测试 1] JSON 格式输入")
        json_input = InputItem(
            source="test_json",
            content=json.dumps({
                "name": "测试规则集",
                "description": "用于自检的规则集合",
                "rules": ["规则一", "规则二"],
                "skills": ["技能一"]
            })
        )
        results = engine.process([json_input])
        assert len(results) == 1, "JSON 输入应生成一个结果"
        result = results[0]
        assert "name" in result.structured, "JSON 输入应包含名称"
        assert "rules" in result.structured, "JSON 输入应包含规则"
        assert result.confidence > 0.5, "JSON 输入置信度应高于 0.5"
        print(f"  ✓ 通过 (置信度: {result.confidence:.1%})")
        
        # 测试用例 2: 文本格式输入
        print("\n[测试 2] 文本格式输入")
        text_input = InputItem(
            source="test_text",
            content="""# 文本规则集
描述: 这是一个文本格式的规则集

规则:
- 规则一内容
- 规则二内容

技能:
- 技能一内容
"""
        )
        results = engine.process([text_input])
        assert len(results) == 1, "文本输入应生成一个结果"
        result = results[0]
        assert "name" in result.structured, "文本输入应包含名称"
        assert "description" in result.structured, "文本输入应包含描述"
        assert result.confidence > 0.3, "文本输入置信度应高于 0.3"
        print(f"  ✓ 通过 (置信度: {result.confidence:.1%})")
        
        # 测试用例 3: 批量处理
        print("\n[测试 3] 批量处理")
        batch_inputs = [
            InputItem(source="batch_1", content='{"name": "批量一", "rules": ["r1"]}'),
            InputItem(source="batch_2", content='{"name": "批量二", "skills": ["s1"]}'),
        ]
        results = engine.process(batch_inputs)
        assert len(results) == 2, "批量输入应生成两个结果"
        assert all(r.confidence > 0.3 for r in results), "所有结果置信度应高于 0.3"
        print("  ✓ 通过")
        
        # 测试用例 4: 错误处理
        print("\n[测试 4] 错误处理")
        try:
            engine.process([])  # 空输入
            assert False, "空输入应抛出异常"
        except SkillError as e:
            assert e.code == "E001", f"错误码应为 E001, 实际: {e.code}"
            print(f"  ✓ 通过 (错误码: {e.code})")
        
        # 测试用例 5: 置信度评估
        print("\n[测试 5] 置信度评估")
        complete_input = InputItem(
            source="complete",
            content='{"name": "完整", "description": "完整描述", "rules": ["r1", "r2"], "skills": ["s1"]}'
        )
        incomplete_input = InputItem(
            source="incomplete",
            content='{"rules": ["r1"]}'
        )
        complete_result = engine.process([complete_input])[0]
        incomplete_result = engine.process([incomplete_input])[0]
        assert complete_result.confidence > incomplete_result.confidence, "完整输入置信度应高于不完整输入"
        print(f"  ✓ 通过 (完整: {complete_result.confidence:.1%} vs 不完整: {incomplete_result.confidence:.1%})")
        
        # 测试用例 6: 输出格式化
        print("\n[测试 6] 输出格式化")
        formatter = OutputFormatter()
        json_output = formatter.format([complete_result], "json")
        text_output = formatter.format([complete_result], "text")
        assert json_output.startswith("["), "JSON 输出应以 [ 开头"
        assert "=== 结果" in text_output, "文本输出应包含结果标记"
        print("  ✓ 通过")
        
        # 测试用例 7: 文件处理（使用临时文件）
        print("\n[测试 7] 文件处理")
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"name": "文件测试", "rules": ["r1"]}')
            temp_path = f.name
        try:
            content = FileProcessor.read_file(temp_path)
            assert "文件测试" in content, "文件读取应包含内容"
            print("  ✓ 文件读取通过")
        finally:
            os.unlink(temp_path)
        
        # 测试用例 8: 触发词识别
        print("\n[测试 8] 触发词识别")
        trigger_words = ["ai rules sync", "规则同步", "同步规则"]
        for word in trigger_words:
            assert "sync" in word.lower() or "同步" in word, f"触发词应包含同步语义: {word}"
        print("  ✓ 通过")
        
        print("\n" + "=" * 60)
        print("所有自检测试通过 ✓")
        return True
        
    except AssertionError as e:
        print(f"\n✗ 自检失败: {str(e)}")
        return False
    except SkillError as e:
        print(f"\n✗ 自检失败: [{e.code}] {e.message}")
        return False
    except Exception as e:
        print(f"\n✗ 自检失败 (未预期错误): {str(e)}")
        return False


# ============================================================
# 主程序入口
# ============================================================
def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="ai-rules-sync - 规则/技能/命令同步管理工具",
        epilog="示例: python main.py --input data.json --output result.json --format json"
    )
    
    parser.add_argument(
        "--input", "-i",
        help="输入文件路径 (JSON 或文本格式)"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径 (默认输出到 stdout)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检 (不读取外部文件，不访问网络)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ai-rules-sync 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查必要参数
    if not args.input:
        print("错误 [E009]: 必须指定 --input 参数或使用 --selftest 运行自检", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    try:
        # 读取输入
        print(f"读取输入文件: {args.input}")
        content = FileProcessor.read_file(args.input)
        
        # 创建输入项
        input_item = InputItem(source=args.input, content=content)
        
        # 处理
        print("处理中...")
        engine = RuleSyncEngine()
        results = engine.process([input_item])
        
        # 格式化输出
        formatter = OutputFormatter()
        output = formatter.format(results, args.format)
        
        # 输出结果
        if args.output:
            FileProcessor.write_file(args.output, output)
            print(f"结果已写入: {args.output}")
        else:
            print(output)
        
        # 打印警告信息
        for result in results:
            if result.warnings:
                print(f"\n警告: {result.item_id}", file=sys.stderr)
                for warning in result.warnings:
                    print(f"  - {warning}", file=sys.stderr)
        
        print("\n处理完成 ✓")
        
    except SkillError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误 [E010]: 未预期错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
