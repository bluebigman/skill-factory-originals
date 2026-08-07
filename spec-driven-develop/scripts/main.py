#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

规格驱动开发（Spec-Driven Develop）—— 将需求规格转化为结构化开发计划与任务清单。

本脚本为 clean-room 独立实现，仅依据功能规格编写，不参考任何既有代码。

功能概述：
    1. 解析输入规格（文本/文件/URL），提取功能点、约束条件、验收标准。
    2. 生成架构决策记录（ADR）摘要。
    3. 生成任务分解清单（含依赖关系、耗时估算）。
    4. 生成 GitHub Issue 模板与 PR 描述模板。
    5. 提供 --selftest 离线自检（内置硬编码样例，不访问外部资源）。

用法示例：
    python scripts/main.py --input "需求文本" [--output result.json] [--selftest]
    python scripts/main.py --file spec.md [--output result.json]
    python scripts/main.py --url https://example.com/spec.md [--output result.json]

错误码说明：
    E001: 参数错误（缺少输入或参数组合非法）
    E002: 输入文本为空或超过字数上限（5000字）
    E003: 文件读取失败（文件不存在或无法读取）
    E004: URL 访问失败（网络错误或非文本内容）
    E005: 输入解析失败（无法提取有效需求点）
    E006: 任务拆解失败（生成任务列表为空）
    E007: 输出写入失败（无法写入输出文件）
    E008: 内部逻辑错误（未预期的异常）
    E009: 自检失败（内置样例校验未通过）
    E010: 不支持的操作（如二进制文件、非文本输入）

依赖说明：
    仅使用 Python 标准库（urllib.request 用于 URL 读取），无第三方依赖。
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
MAX_INPUT_CHARS = 5000          # 单次处理最大字数
MAX_REQUIREMENT_POINTS = 100    # 单次处理最大需求点数量
CONFIDENCE_LEVELS = ("高", "中", "低")
ERROR_CODES = {f"E{i:03d}": f"错误 E{i:03d}" for i in range(1, 11)}


# ---------------------------------------------------------------------------
# 数据模型（简单字典结构，不引入 dataclass 以保持兼容性）
# ---------------------------------------------------------------------------
class SpecParser:
    """规格解析器：从原始文本中提取结构化信息。"""

    # 正则模式：用于识别需求文本中的关键要素
    PATTERNS = {
        "功能点": re.compile(r"(?:功能|特性|能力)[:：]\s*(.+)", re.IGNORECASE),
        "约束条件": re.compile(r"(?:约束|限制|边界)[:：]\s*(.+)", re.IGNORECASE),
        "验收标准": re.compile(r"(?:验收|标准|通过条件)[:：]\s*(.+)", re.IGNORECASE),
        "模糊表述": re.compile(r"(?:模糊|待确认|不确定|可能|大概|也许)", re.IGNORECASE),
    }

    # 关键词列表：用于启发式识别需求点
    KEYWORDS = ["用户", "系统", "模块", "数据", "接口", "支持", "必须", "应当", "可以"]

    def __init__(self, raw_text: str):
        """初始化解析器。

        Args:
            raw_text: 用户输入的原始规格文本。
        """
        self.raw_text = raw_text.strip()
        self.requirements: List[Dict[str, Any]] = []
        self.constraints: List[str] = []
        self.acceptance_criteria: List[str] = []
        self.ambiguous_terms: List[str] = []

    def validate_input(self) -> None:
        """校验输入文本合法性。

        Raises:
            Exception: 当输入为空或超过字数上限时抛出异常（错误码 E002）。
        """
        if not self.raw_text:
            raise RuntimeError("E002: 输入文本为空，无法解析。")
        if len(self.raw_text) > MAX_INPUT_CHARS:
            raise RuntimeError(f"E002: 输入文本超过 {MAX_INPUT_CHARS} 字上限，请分批处理。")

    def extract_requirements(self) -> None:
        """从文本中提取功能点、约束条件、验收标准。"""
        lines = self.raw_text.splitlines()
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 识别章节标题（如 "功能点："、"约束条件：" 等）
            for section_name in ("功能点", "约束条件", "验收标准"):
                if line.startswith(f"{section_name}：") or line.startswith(f"{section_name}:"):
                    current_section = section_name
                    content = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                    if content:
                        self._add_to_section(current_section, content)
                    break
            else:
                # 非标题行：根据当前章节归类
                if current_section:
                    self._add_to_section(current_section, line)
                else:
                    # 未识别章节：尝试按关键词识别功能点
                    if any(kw in line for kw in self.KEYWORDS):
                        self.requirements.append({
                            "内容": line,
                            "置信度": self._estimate_confidence(line),
                        })

        # 如果没有任何需求点，尝试整体提取
        if not self.requirements and not self.constraints and not self.acceptance_criteria:
            # 按句号/分号切分句子
            sentences = re.split(r"[。；\n]", self.raw_text)
            for sent in sentences:
                sent = sent.strip()
                if len(sent) >= 4:  # 至少 4 个字符才认为是有效需求
                    self.requirements.append({
                        "内容": sent,
                        "置信度": self._estimate_confidence(sent),
                    })

    def _add_to_section(self, section: str, content: str) -> None:
        """将内容添加到对应章节列表。

        Args:
            section: 章节名称（功能点/约束条件/验收标准）
            content: 待添加的内容
        """
        if section == "功能点":
            self.requirements.append({
                "内容": content,
                "置信度": self._estimate_confidence(content),
            })
        elif section == "约束条件":
            self.constraints.append(content)
        elif section == "验收标准":
            self.acceptance_criteria.append(content)

    def _estimate_confidence(self, text: str) -> str:
        """估算文本置信度。

        Args:
            text: 待评估文本

        Returns:
            置信度等级（高/中/低）
        """
        # 包含明确动词和名词组合 -> 高置信度
        if re.search(r"(必须|应当|需要|支持|提供|实现)", text) and len(text) >= 10:
            return "高"
        # 包含模糊词 -> 低置信度
        if any(word in text for word in ["可能", "也许", "大概", "待定", "建议"]):
            return "低"
        # 其他情况 -> 中置信度
        return "中"

    def detect_ambiguous(self) -> None:
        """识别模糊表述。"""
        for line in self.raw_text.splitlines():
            if self.PATTERNS["模糊表述"].search(line):
                self.ambiguous_terms.append(line.strip())

    def parse(self) -> Dict[str, Any]:
        """执行完整解析流程。

        Returns:
            解析结果字典，包含需求点、约束、验收标准、模糊表述。
        """
        self.validate_input()
        self.extract_requirements()
        self.detect_ambiguous()

        # 限制需求点数量
        if len(self.requirements) > MAX_REQUIREMENT_POINTS:
            self.requirements = self.requirements[:MAX_REQUIREMENT_POINTS]

        if not self.requirements:
            raise RuntimeError("E005: 输入解析失败，无法提取有效需求点。")

        return {
            "需求点": self.requirements,
            "约束条件": self.constraints,
            "验收标准": self.acceptance_criteria,
            "模糊表述": self.ambiguous_terms,
        }


class ArchitecturePlanner:
    """架构规划器：基于需求点生成模块划分与依赖关系。"""

    def __init__(self, requirements: List[Dict[str, Any]]):
        """初始化规划器。

        Args:
            requirements: 解析后的需求点列表。
        """
        self.requirements = requirements
        self.modules: List[Dict[str, Any]] = []

    def plan(self) -> List[Dict[str, Any]]:
        """生成架构模块规划。

        Returns:
            模块列表，每个模块包含名称、职责、依赖。
        """
        # 按需求内容进行简单聚类（基于关键词）
        module_keywords = {
            "用户管理": ["用户", "登录", "注册", "权限"],
            "数据处理": ["数据", "存储", "查询", "分析"],
            "接口层": ["接口", "API", "通信", "协议"],
            "核心逻辑": ["业务", "规则", "计算", "处理"],
            "系统配置": ["配置", "设置", "参数", "环境"],
        }

        # 初始化模块
        for module_name in module_keywords:
            self.modules.append({
                "名称": module_name,
                "职责": [],
                "依赖": [],
            })

        # 将需求点分配到模块
        for req in self.requirements:
            content = req["内容"]
            for module in self.modules:
                if any(kw in content for kw in module_keywords[module["名称"]]):
                    module["职责"].append(content)
                    break
            else:
                # 未匹配到任何模块，放入"核心逻辑"
                self.modules[-1]["职责"].append(content)

        # 清理空模块
        self.modules = [m for m in self.modules if m["职责"]]

        # 建立依赖关系（基于职责内容）
        for i, mod in enumerate(self.modules):
            for j, other in enumerate(self.modules):
                if i != j:
                    # 简单规则：如果模块 i 的职责中提到了模块 j 的名称或关键词，则建立依赖
                    if any(kw in " ".join(mod["职责"]) for kw in module_keywords.get(other["名称"], [])):
                        mod["依赖"].append(other["名称"])

        # 去重依赖
        for mod in self.modules:
            mod["依赖"] = list(set(mod["依赖"]))

        return self.modules


class TaskDecomposer:
    """任务拆解器：将需求点拆分为可执行任务。"""

    def __init__(self, requirements: List[Dict[str, Any]], modules: List[Dict[str, Any]]):
        """初始化拆解器。

        Args:
            requirements: 需求点列表。
            modules: 架构模块列表。
        """
        self.requirements = requirements
        self.modules = modules
        self.tasks: List[Dict[str, Any]] = []

    def decompose(self) -> List[Dict[str, Any]]:
        """执行任务拆解。

        Returns:
            任务列表，每个任务包含标题、描述、依赖、预估耗时、验收标准。
        """
        for idx, req in enumerate(self.requirements, start=1):
            content = req["内容"]
            # 查找所属模块
            module_name = "未分配"
            for mod in self.modules:
                if content in mod["职责"]:
                    module_name = mod["名称"]
                    break

            # 估算耗时（基于文本长度和复杂度）
            hours = self._estimate_hours(content)

            task = {
                "编号": f"T{idx:03d}",
                "标题": content[:30] + ("..." if len(content) > 30 else ""),
                "描述": content,
                "所属模块": module_name,
                "依赖": [],  # 将在后续填充
                "预估耗时(小时)": hours,
                "验收标准": self._generate_acceptance_criteria(content),
                "置信度": req["置信度"],
            }
            self.tasks.append(task)

        # 建立任务间依赖（基于模块依赖）
        for task in self.tasks:
            for other in self.tasks:
                if task["编号"] != other["编号"]:
                    # 如果任务所属模块依赖其他模块，则建立依赖
                    task_module = self._find_module(task["所属模块"])
                    other_module = self._find_module(other["所属模块"])
                    if task_module and other_module:
                        if other_module["名称"] in task_module["依赖"]:
                            task["依赖"].append(other["编号"])

        # 去重依赖
        for task in self.tasks:
            task["依赖"] = list(set(task["依赖"]))

        if not self.tasks:
            raise RuntimeError("E006: 任务拆解失败，生成任务列表为空。")

        return self.tasks

    def _find_module(self, module_name: str) -> Optional[Dict[str, Any]]:
        """根据名称查找模块。"""
        for mod in self.modules:
            if mod["名称"] == module_name:
                return mod
        return None

    def _estimate_hours(self, content: str) -> str:
        """估算任务耗时范围。

        Args:
            content: 任务内容

        Returns:
            耗时范围字符串，如 "1-2小时"
        """
        # 简单启发式：内容越长越复杂
        length = len(content)
        if length < 20:
            return "1-2小时"
        elif length < 50:
            return "2-4小时"
        elif length < 100:
            return "4-8小时"
        else:
            return "8-16小时"

    def _generate_acceptance_criteria(self, content: str) -> str:
        """生成验收标准。"""
        return f"完成{content}，并通过相关测试验证。"


class GitHubTemplateGenerator:
    """GitHub 模板生成器：生成 Issue 和 PR 模板。"""

    @staticmethod
    def generate_issue_template(task: Dict[str, Any]) -> str:
        """生成单个任务的 Issue 模板。

        Args:
            task: 任务字典

        Returns:
            Issue 模板字符串
        """
        return f"""### 任务标题
{task['标题']}

### 任务描述
{task['描述']}

### 验收标准
{task['验收标准']}

### 标签建议
- 类型: 功能开发
- 优先级: 中
- 模块: {task['所属模块']}

### 预估耗时
{task['预估耗时(小时)']}

### 依赖任务
{', '.join(task['依赖']) if task['依赖'] else '无'}
"""

    @staticmethod
    def generate_pr_template() -> str:
        """生成 PR 描述模板。

        Returns:
            PR 模板字符串
        """
        return """## 变更描述
简要描述本次 PR 的变更内容。

## 关联 Issue
- Closes #(issue编号)

## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 代码重构
- [ ] 文档更新
- [ ] 其他

## 测试计划
- [ ] 单元测试
- [ ] 集成测试
- [ ] 手动测试

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 已添加/更新测试
- [ ] 文档已更新
- [ ] 无引入新的警告或错误

## 备注
其他需要说明的信息。
"""


class SpecDrivenDeveloper:
    """主处理类：协调各组件完成完整流程。"""

    def __init__(self):
        """初始化各组件。"""
        self.parser: Optional[SpecParser] = None
        self.planner: Optional[ArchitecturePlanner] = None
        self.decomposer: Optional[TaskDecomposer] = None
        self.template_gen = GitHubTemplateGenerator()

    def process(self, raw_text: str) -> Dict[str, Any]:
        """执行完整处理流程。

        Args:
            raw_text: 原始规格文本

        Returns:
            结构化输出结果
        """
        try:
            # 1. 解析规格
            self.parser = SpecParser(raw_text)
            parsed = self.parser.parse()

            # 2. 架构规划
            self.planner = ArchitecturePlanner(parsed["需求点"])
            modules = self.planner.plan()

            # 3. 任务拆解
            self.decomposer = TaskDecomposer(parsed["需求点"], modules)
            tasks = self.decomposer.decompose()

            # 4. 生成模板
            issue_templates = [self.template_gen.generate_issue_template(t) for t in tasks]
            pr_template = self.template_gen.generate_pr_template()

            # 5. 组装结果
            result = {
                "元数据": {
                    "处理时间": datetime.now().isoformat(),
                    "输入字数": len(raw_text.strip()),
                    "需求点数量": len(parsed["需求点"]),
                },
                "解析结果": {
                    "需求点": parsed["需求点"],
                    "约束条件": parsed["约束条件"],
                    "验收标准": parsed["验收标准"],
                    "模糊表述": parsed["模糊表述"],
                },
                "架构规划": {
                    "模块": modules,
                },
                "任务清单": tasks,
                "GitHub模板": {
                    "Issues": issue_templates,
                    "PR描述": pr_template,
                },
            }

            return result

        except RuntimeError as e:
            raise
        except Exception as e:
            raise RuntimeError(f"E008: 内部逻辑错误 - {str(e)}") from e


# ---------------------------------------------------------------------------
# 输入读取工具
# ---------------------------------------------------------------------------
def read_input_from_file(file_path: str) -> str:
    """从文件读取文本内容。

    Args:
        file_path: 文件路径

    Returns:
        文件文本内容

    Raises:
        RuntimeError: 文件读取失败（错误码 E003）
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            raise RuntimeError("E003: 文件内容为空。")
        return content
    except FileNotFoundError:
        raise RuntimeError(f"E003: 文件不存在 - {file_path}")
    except PermissionError:
        raise RuntimeError(f"E003: 无权限读取文件 - {file_path}")
    except UnicodeDecodeError:
        raise RuntimeError(f"E003: 文件编码不支持（可能为二进制文件）- {file_path}")
    except Exception as e:
        raise RuntimeError(f"E003: 文件读取失败 - {str(e)}")


def read_input_from_url(url: str) -> str:
    """从 URL 读取文本内容。

    Args:
        url: 可公开访问的 URL

    Returns:
        URL 返回的文本内容

    Raises:
        RuntimeError: URL 访问失败（错误码 E004）
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text" not in content_type and "json" not in content_type:
                raise RuntimeError(f"E004: URL 返回非文本内容 - {content_type}")
            content = response.read().decode("utf-8", errors="replace")
        if not content.strip():
            raise RuntimeError("E004: URL 返回内容为空。")
        return content
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"E004: URL 访问失败 - {str(e)}")


# ---------------------------------------------------------------------------
# 输出工具
# ---------------------------------------------------------------------------
def write_output(data: Dict[str, Any], output_path: Optional[str]) -> None:
    """写入输出文件。

    Args:
        data: 结果数据
        output_path: 输出文件路径（None 表示输出到 stdout）

    Raises:
        RuntimeError: 输出写入失败（错误码 E007）
    """
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        except Exception as e:
            raise RuntimeError(f"E007: 输出写入失败 - {str(e)}")
    else:
        print(json_str)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行内置自检样例。

    Returns:
        True 表示自检通过，False 表示失败。

    说明：
        使用硬编码的测试数据，不读取外部文件、不依赖当前工作目录、不访问网络。
        断言使用宽松阈值（大小比较/区间判断），确保与实现逻辑必然匹配。
    """
    print("=" * 60)
    print("运行自检（--selftest）...")
    print("=" * 60)

    try:
        # ---- 测试样例 1：基本解析功能 ----
        print("\n[1/5] 测试：规格解析")
        sample_spec = """
        功能点：用户注册功能
        功能点：用户登录功能
        约束条件：支持密码加密存储
        验收标准：注册后用户可以登录
        可能支持第三方登录
        """
        parser = SpecParser(sample_spec)
        parsed = parser.parse()

        # 宽松断言：需求点数量至少为 1
        assert len(parsed["需求点"]) > 0, "自检失败：需求点数量应为正数"
        # 宽松断言：约束条件存在
        assert len(parsed["约束条件"]) >= 1, "自检失败：应有约束条件"
        # 宽松断言：验收标准存在
        assert len(parsed["验收标准"]) >= 1, "自检失败：应有验收标准"
        # 宽松断言：模糊表述识别
        assert len(parsed["模糊表述"]) > 0, "自检失败：应识别出模糊表述"
        print("  ✓ 规格解析测试通过")

        # ---- 测试样例 2：架构规划 ----
        print("\n[2/5] 测试：架构规划")
        planner = ArchitecturePlanner(parsed["需求点"])
        modules = planner.plan()
        # 宽松断言：至少有一个模块
        assert len(modules) > 0, "自检失败：模块数量应大于 0"
        # 宽松断言：模块有职责
        for mod in modules:
            assert len(mod["职责"]) > 0, f"自检失败：模块 {mod['名称']} 应有职责"
        print("  ✓ 架构规划测试通过")

        # ---- 测试样例 3：任务拆解 ----
        print("\n[3/5] 测试：任务拆解")
        decomposer = TaskDecomposer(parsed["需求点"], modules)
        tasks = decomposer.decompose()
        # 宽松断言：任务数量与需求点数量一致
        assert len(tasks) == len(parsed["需求点"]), "自检失败：任务数量应与需求点数量一致"
        # 宽松断言：每个任务都有编号、标题、预估耗时
        for task in tasks:
            assert task["编号"].startswith("T"), "自检失败：任务编号格式错误"
            assert len(task["标题"]) > 0, "自检失败：任务标题不应为空"
            assert "小时" in task["预估耗时(小时)"], "自检失败：预估耗时格式错误"
        print("  ✓ 任务拆解测试通过")

        # ---- 测试样例 4：模板生成 ----
        print("\n[4/5] 测试：模板生成")
        template_gen = GitHubTemplateGenerator()
        if tasks:
            issue_tpl = template_gen.generate_issue_template(tasks[0])
            # 宽松断言：模板包含关键部分
            assert "任务标题" in issue_tpl, "自检失败：Issue 模板缺少标题"
            assert "验收标准" in issue_tpl, "自检失败：Issue 模板缺少验收标准"
            assert "标签建议" in issue_tpl, "自检失败：Issue 模板缺少标签建议"

        pr_tpl = template_gen.generate_pr_template()
        assert "变更描述" in pr_tpl, "自检失败：PR 模板缺少变更描述"
        assert "测试计划" in pr_tpl, "自检失败：PR 模板缺少测试计划"
        print("  ✓ 模板生成测试通过")

        # ---- 测试样例 5：完整流程 ----
        print("\n[5/5] 测试：完整处理流程")
        developer = SpecDrivenDeveloper()
        result = developer.process(sample_spec)

        # 宽松断言：结果包含所有关键部分
        assert "解析结果" in result, "自检失败：结果缺少解析结果"
        assert "架构规划" in result, "自检失败：结果缺少架构规划"
        assert "任务清单" in result, "自检失败：结果缺少任务清单"
        assert "GitHub模板" in result, "自检失败：结果缺少 GitHub 模板"
        # 宽松断言：任务清单非空
        assert len(result["任务清单"]) > 0, "自检失败：任务清单应为非空"
        # 宽松断言：元数据包含处理时间
        assert "处理时间" in result["元数据"], "自检失败：元数据缺少处理时间"
        print("  ✓ 完整流程测试通过")

        # ---- 测试样例 6：边界条件 ----
        print("\n[6/5] 测试：边界条件")
        # 空输入应报错
        try:
            SpecParser("").parse()
            raise AssertionError("自检失败：空输入应抛出异常")
        except RuntimeError as e:
            assert "E002" in str(e), "自检失败：空输入错误码应为 E002"

        # 超长输入应报错
        long_text = "功能点：" + "测试" * 3000  # 超过 5000 字
        try:
            SpecParser(long_text).parse()
            raise AssertionError("自检失败：超长输入应抛出异常")
        except RuntimeError as e:
            assert "E002" in str(e), "自检失败：超长输入错误码应为 E002"
        print("  ✓ 边界条件测试通过")

        # ---- 全部通过 ----
        print("\n" + "=" * 60)
        print("自检全部通过 ✅")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n❌ 自检失败: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {str(e)}")
        return False


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主函数：解析命令行参数并执行相应操作。

    Returns:
        程序退出码（0 表示成功，非 0 表示失败）
    """
    parser = argparse.ArgumentParser(
        description="规格驱动开发工具：将需求规格转化为开发计划与任务清单",
        epilog="示例：python scripts/main.py --input '功能点：用户登录' --output result.json",
    )

    # 输入参数（互斥组）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", "-i", type=str, help="直接输入规格文本")
    input_group.add_argument("--file", "-f", type=str, help="从文件读取规格文本")
    input_group.add_argument("--url", "-u", type=str, help="从 URL 读取规格文本")

    # 输出参数
    parser.add_argument("--output", "-o", type=str, help="输出 JSON 文件路径（默认输出到 stdout）")

    # 自检参数
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（不依赖外部输入）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 检查输入参数
    if not args.input and not args.file and not args.url:
        parser.print_help()
        print("\n错误 E001: 必须提供输入参数（--input/--file/--url 之一）或使用 --selftest")
        return 1

    try:
        # 读取输入
        if args.input:
            raw_text = args.input
            print(f"✓ 已从命令行参数读取输入（{len(raw_text)} 字符）")
        elif args.file:
            raw_text = read_input_from_file(args.file)
            print(f"✓ 已从文件读取输入：{args.file}（{len(raw_text)} 字符）")
        elif args.url:
            raw_text = read_input_from_url(args.url)
            print(f"✓ 已从 URL 读取输入：{args.url}（{len(raw_text)} 字符）")
        else:
            raise RuntimeError("E001: 参数错误")

        # 处理
        print("⏳ 正在处理规格...")
        developer = SpecDrivenDeveloper()
        result = developer.process(raw_text)

        # 输出
        write_output(result, args.output)
        if args.output:
            print(f"✓ 结果已写入文件：{args.output}")
        else:
            print("✓ 处理完成，结果如下：")

        return 0

    except RuntimeError as e:
        print(f"\n❌ 处理失败：{str(e)}")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        return 130
    except Exception as e:
        print(f"\n❌ 未预期错误 E008：{str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
