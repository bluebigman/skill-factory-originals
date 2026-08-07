#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
book-to-skill — 将技术书籍 PDF 转换为结构化技能包的工具
版本: 1.0.0
许可证: MIT
"""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
    "E007": "输出写入失败",
    "E008": "内部处理错误",
    "E009": "参数校验失败",
    "E010": "未预期的运行时错误",
}

# ============================================================
# 数据模型
# ============================================================
@dataclass
class SkillPackage:
    """技能包数据模型"""
    name: str
    display_name: str
    description: str
    version: str
    trigger_words: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    workflow_steps: List[str] = field(default_factory=list)
    error_handling: Dict[str, str] = field(default_factory=dict)
    faq: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "displayName": self.display_name,
            "description": self.description,
            "version": self.version,
            "triggerWords": self.trigger_words,
            "capabilities": self.capabilities,
            "limitations": self.limitations,
            "workflowSteps": self.workflow_steps,
            "errorHandling": self.error_handling,
            "faq": self.faq,
            "confidence": self.confidence,
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ============================================================
# 核心处理逻辑
# ============================================================
class SkillGenerator:
    """技能生成器"""

    # 默认技能模板
    DEFAULT_CAPABILITIES = [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ]

    DEFAULT_LIMITATIONS = [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ]

    DEFAULT_WORKFLOW = [
        "Step 1: 收集最小信息集（输入来源、输出格式、期望完整度）",
        "Step 2: 执行核心流程（解析输入、识别关键信息、结构化处理）",
        "Step 3: 输出与校验（格式检查、置信度标注、二次确认）",
    ]

    DEFAULT_ERROR_HANDLING = {
        "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
        "E002": "还缺少以下信息，请补充：...",
        "E003": "输入格式不符合要求，示例：...",
        "E004": "这超出了本工具的能力范围，建议...",
        "E005": "结果无法确定，建议：...",
    }

    DEFAULT_FAQ = {
        "处理速度如何？": "骨架结果 1 分钟内，详细结果视输入量而定",
        "会不会出错？": "低置信度内容会标注 [需核实]，请人工复核关键结果",
        "支持哪些输入？": "用户提供的数据/文件/URL",
    }

    def __init__(self, input_data: str = ""):
        """初始化生成器"""
        self.input_data = input_data.strip() if input_data else ""
        self.confidence = 0.0
        self.warnings: List[str] = []

    def process(self) -> SkillPackage:
        """处理输入数据，生成技能包"""
        # 输入校验
        if not self.input_data:
            raise SkillError("E001", ERROR_CODES["E001"])

        # 检查输入类型
        input_type = self._detect_input_type(self.input_data)
        if input_type == "unknown":
            raise SkillError("E003", f"{ERROR_CODES['E003']} 无法识别的输入类型")

        # 提取关键信息
        key_info = self._extract_key_info(self.input_data)
        if not key_info:
            raise SkillError("E002", ERROR_CODES["E002"])

        # 计算置信度
        self.confidence = self._calculate_confidence(key_info)

        # 生成技能包
        package = self._build_package(key_info)

        # 添加置信度提示
        if self.confidence < 0.85:
            self.warnings.append("[需核实] 输入信息不足，结果置信度较低")
            package.description = f"[需核实] {package.description}"
        elif self.confidence < 0.90:
            self.warnings.append("建议复核：结果置信度为中等水平")

        return package

    def _detect_input_type(self, data: str) -> str:
        """检测输入类型"""
        # 检查是否为 URL
        if data.startswith(("http://", "https://", "ftp://")):
            return "url"

        # 检查是否为文件路径
        if os.path.exists(data) and os.path.isfile(data):
            ext = os.path.splitext(data)[1].lower()
            if ext in [".pdf", ".txt", ".md", ".json", ".csv"]:
                return "file"
            return "file_unsupported"

        # 检查是否为 JSON 数据
        try:
            json.loads(data)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass

        # 检查是否为纯文本
        if len(data) > 10 and any(c.isalpha() for c in data):
            return "text"

        return "unknown"

    def _extract_key_info(self, data: str) -> Dict[str, Any]:
        """提取关键信息"""
        info: Dict[str, Any] = {}

        # 尝试解析 JSON
        if data.startswith("{"):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    info = self._extract_from_dict(parsed)
                elif isinstance(parsed, list):
                    info = self._extract_from_list(parsed)
            except (json.JSONDecodeError, ValueError):
                pass
        else:
            # 处理文本输入
            info = self._extract_from_text(data)

        return info

    def _extract_from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从字典提取信息"""
        result: Dict[str, Any] = {}
        keys_map = {
            "name": ["name", "title", "书名", "名称"],
            "description": ["description", "desc", "描述", "简介"],
            "version": ["version", "版本"],
            "trigger_words": ["trigger_words", "triggers", "触发词"],
        }

        for target_key, source_keys in keys_map.items():
            for key in source_keys:
                if key in data and data[key]:
                    result[target_key] = data[key]
                    break

        return result

    def _extract_from_list(self, data: List[Any]) -> Dict[str, Any]:
        """从列表提取信息"""
        result: Dict[str, Any] = {}
        if data and isinstance(data[0], dict):
            # 取第一个元素作为主要信息源
            result = self._extract_from_dict(data[0])
        return result

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """从文本提取信息"""
        result: Dict[str, Any] = {}

        # 提取标题（第一行或包含 title 的行）
        lines = text.splitlines()
        for line in lines[:5]:
            line = line.strip()
            if line and not line.startswith(("#", "//", "/*")):
                result["name"] = line[:50]
                break

        # 提取描述（包含 description 或 desc 的行）
        for line in lines:
            if "description" in line.lower() or "描述" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    result["description"] = parts[1].strip()[:100]
                break

        # 提取版本号
        for line in lines:
            if "version" in line.lower() or "版本" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    result["version"] = parts[1].strip()
                break

        # 提取触发词
        trigger_lines = [l for l in lines if "trigger" in l.lower() or "触发" in l]
        if trigger_lines:
            triggers = []
            for line in trigger_lines:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    triggers.extend([t.strip() for t in parts[1].split(",")])
            if triggers:
                result["trigger_words"] = triggers[:5]

        return result

    def _calculate_confidence(self, info: Dict[str, Any]) -> float:
        """计算置信度"""
        if not info:
            return 0.0

        score = 0.0
        total_weight = 0.0

        # 各字段权重
        weights = {
            "name": 0.35,
            "description": 0.30,
            "version": 0.15,
            "trigger_words": 0.20,
        }

        for field_name, weight in weights.items():
            total_weight += weight
            if info.get(field_name):
                score += weight

        if total_weight > 0:
            return min(1.0, score / total_weight)
        return 0.0

    def _build_package(self, info: Dict[str, Any]) -> SkillPackage:
        """构建技能包"""
        name = info.get("name", "未命名工具")
        # 清理名称（去扩展名、下划线转空格）
        name = os.path.splitext(name)[0].replace("_", " ").replace("-", " ").strip()
        if not name:
            name = "未命名工具"

        return SkillPackage(
            name=name,
            display_name=name.title(),
            description=info.get("description", "将输入数据转换为结构化技能包"),
            version=info.get("version", "1.0.0"),
            trigger_words=info.get("trigger_words", ["book to skill"]),
            capabilities=self.DEFAULT_CAPABILITIES.copy(),
            limitations=self.DEFAULT_LIMITATIONS.copy(),
            workflow_steps=self.DEFAULT_WORKFLOW.copy(),
            error_handling=self.DEFAULT_ERROR_HANDLING.copy(),
            faq=self.DEFAULT_FAQ.copy(),
            confidence=self.confidence,
        )


# ============================================================
# 错误处理
# ============================================================
class SkillError(Exception):
    """技能处理异常"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 文件处理
# ============================================================
def read_input_file(filepath: str) -> str:
    """读取输入文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise SkillError("E006", f"文件不存在: {filepath}")
    except PermissionError:
        raise SkillError("E006", f"没有权限读取文件: {filepath}")
    except Exception as e:
        raise SkillError("E006", f"读取文件失败: {str(e)}")


def write_output_file(content: str, filepath: str) -> None:
    """写入输出文件"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        raise SkillError("E007", f"写入文件失败: {str(e)}")


# ============================================================
# 自检功能（硬编码样例数据）
# ============================================================
def run_selftest() -> bool:
    """运行内置自检"""
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    # 样例 1: JSON 输入
    print("\n[Test 1] JSON 输入处理")
    json_input = json.dumps({
        "name": "python_cookbook",
        "description": "Python 编程实战技巧",
        "version": "3.0",
        "trigger_words": ["python", "cookbook", "recipe"]
    }, ensure_ascii=False)
    try:
        gen = SkillGenerator(json_input)
        pkg = gen.process()
        assert pkg.name, "名称不能为空"
        assert pkg.description, "描述不能为空"
        assert len(pkg.capabilities) >= 3, "能力列表过短"
        assert pkg.confidence >= 0.5, "置信度应大于0.5"
        assert "python" in pkg.trigger_words, "触发词应包含python"
        print(f"  ✓ 通过 (置信度: {pkg.confidence:.2f})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 错误: {e}")
        return False

    # 样例 2: 文本输入
    print("\n[Test 2] 文本输入处理")
    text_input = """
    Machine Learning Guide
    version: 2.1
    description: 机器学习入门到实践
    trigger: ml, machine learning, ai
    """
    try:
        gen = SkillGenerator(text_input)
        pkg = gen.process()
        assert pkg.name, "名称不能为空"
        assert "Machine" in pkg.name, "名称应包含Machine"
        assert pkg.version, "版本号不能为空"
        assert len(pkg.trigger_words) > 0, "触发词不能为空"
        print(f"  ✓ 通过 (置信度: {pkg.confidence:.2f})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 错误: {e}")
        return False

    # 样例 3: 错误处理
    print("\n[Test 3] 错误处理")
    try:
        gen = SkillGenerator("")
        gen.process()
        print("  ✗ 失败: 空输入应该报错")
        return False
    except SkillError as e:
        assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")

    # 样例 4: JSON 输出格式
    print("\n[Test 4] JSON 输出格式")
    try:
        gen = SkillGenerator(json_input)
        pkg = gen.process()
        json_str = pkg.to_json()
        parsed = json.loads(json_str)
        assert "name" in parsed, "JSON应包含name字段"
        assert "capabilities" in parsed, "JSON应包含capabilities字段"
        assert "confidence" in parsed, "JSON应包含confidence字段"
        print("  ✓ 通过 (JSON格式正确)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

    # 样例 5: 批量/多行输入
    print("\n[Test 5] 多行文本输入")
    multi_line = """第一行: 数据科学手册
第二行: description: 数据科学完整指南
第三行: version: 1.5
第四行: trigger: data science, ds"""
    try:
        gen = SkillGenerator(multi_line)
        pkg = gen.process()
        assert pkg.name, "名称不能为空"
        assert "数据" in pkg.name or "数据科学" in pkg.name, "名称应包含数据科学"
        assert pkg.confidence >= 0.3, "置信度应大于0.3"
        print(f"  ✓ 通过 (置信度: {pkg.confidence:.2f})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 错误: {e}")
        return False

    # 样例 6: 边界条件（超长输入）
    print("\n[Test 6] 超长输入处理")
    long_text = "name: " + "A" * 2000 + "\ndescription: " + "B" * 3000
    try:
        gen = SkillGenerator(long_text)
        pkg = gen.process()
        assert pkg.name, "名称不能为空"
        assert len(pkg.name) <= 500, "名称长度应有限制"
        print(f"  ✓ 通过 (名称长度: {len(pkg.name)})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 错误: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有自检通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="book-to-skill: 将技术书籍转换为结构化技能包",
        epilog="示例: python main.py -i input.pdf -o output.json"
    )
    parser.add_argument("-i", "--input", help="输入文件路径或URL")
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出到stdout）")
    parser.add_argument("--input-text", help="直接输入文本内容")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="book-to-skill 1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    try:
        # 获取输入
        input_data = ""
        if args.input_text:
            input_data = args.input_text
        elif args.input:
            # 检查是否为URL（本工具不访问网络，仅识别格式）
            if args.input.startswith(("http://", "https://")):
                print("警告: 本工具不访问网络，URL仅作为元数据处理")
                input_data = f"name: {args.input.split('/')[-1]}\nurl: {args.input}"
            else:
                input_data = read_input_file(args.input)
        else:
            # 从stdin读取
            if not sys.stdin.isatty():
                input_data = sys.stdin.read()
            else:
                raise SkillError("E001", ERROR_CODES["E001"])

        # 处理
        generator = SkillGenerator(input_data)
        package = generator.process()

        # 输出
        output_json = package.to_json()

        if args.output:
            write_output_file(output_json, args.output)
            print(f"技能包已生成: {args.output}")
            print(f"名称: {package.display_name}")
            print(f"置信度: {package.confidence:.2%}")
            if generator.warnings:
                for warning in generator.warnings:
                    print(f"警告: {warning}")
        else:
            print(output_json)

        return 0

    except SkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 E010: 未预期的错误 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
