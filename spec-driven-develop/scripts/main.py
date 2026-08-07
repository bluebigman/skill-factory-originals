#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec-driven-develop 技能实现脚本

功能：将需求规格转化为结构化开发计划与任务清单。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input "需求文本" [--output json|text]
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或格式无效",
    "E002": "输入超过处理上限（5000字 或 100个需求点）",
    "E003": "无法解析输入内容",
    "E004": "输出格式不支持",
    "E005": "内部处理异常",
    "E006": "参数缺失",
    "E007": "文件读取失败",
    "E008": "URL 访问失败",
    "E009": "数据序列化失败",
    "E010": "未知错误",
}


class SpecDrivenError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


class RequirementItem:
    """单个需求点"""

    def __init__(self, text: str, confidence: str = "高"):
        self.text = text.strip()
        self.confidence = confidence  # 高/中/低
        self.functional_points: List[str] = []
        self.constraints: List[str] = []
        self.acceptance_criteria: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "functional_points": self.functional_points,
            "constraints": self.constraints,
            "acceptance_criteria": self.acceptance_criteria,
        }


class TaskItem:
    """单个开发任务"""

    def __init__(self, title: str, description: str = ""):
        self.id = str(uuid.uuid4())[:8]
        self.title = title
        self.description = description
        self.inputs: List[str] = []
        self.outputs: List[str] = []
        self.acceptance_criteria: List[str] = []
        self.dependencies: List[str] = []
        self.estimated_hours: Tuple[int, int] = (1, 4)  # 预估耗时范围（小时）
        self.module: str = "未分配"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "acceptance_criteria": self.acceptance_criteria,
            "dependencies": self.dependencies,
            "estimated_hours": {
                "min": self.estimated_hours[0],
                "max": self.estimated_hours[1],
            },
            "module": self.module,
        }


class SpecDrivenProcessor:
    """核心处理器：将需求规格转化为开发计划"""

    # 处理上限
    MAX_CHARS = 5000
    MAX_POINTS = 100

    # 置信度关键词
    CONFIDENCE_HIGH = ["明确", "必须", "需要", "要求", "应"]
    CONFIDENCE_MEDIUM = ["建议", "应当", "可以", "可能"]
    CONFIDENCE_LOW = ["或许", "也许", "可选", "考虑"]

    # 模块划分关键词
    MODULE_KEYWORDS = {
        "前端": ["界面", "页面", "UI", "前端", "交互", "样式"],
        "后端": ["接口", "服务", "后端", "API", "数据处理"],
        "数据库": ["数据表", "存储", "数据库", "schema", "模型"],
        "测试": ["测试", "验证", "用例", "质量"],
        "部署": ["部署", "发布", "上线", "运维", "配置"],
    }

    def __init__(self, max_chars: int = MAX_CHARS, max_points: int = MAX_POINTS):
        self.max_chars = max_chars
        self.max_points = max_points

    def process(self, input_text: str) -> Dict[str, Any]:
        """主处理流程"""
        # 1. 输入校验
        if not input_text or not input_text.strip():
            raise SpecDrivenError("E001")

        # 2. 长度检查
        if len(input_text) > self.max_chars:
            raise SpecDrivenError("E002", f"输入超过 {self.max_chars} 字限制")

        # 3. 解析需求
        requirements = self._parse_requirements(input_text)
        if not requirements:
            raise SpecDrivenError("E003")

        # 4. 需求点数量检查
        if len(requirements) > self.max_points:
            raise SpecDrivenError("E002", f"需求点超过 {self.max_points} 个限制")

        # 5. 架构规划
        architecture = self._plan_architecture(requirements)

        # 6. 任务拆解
        tasks = self._breakdown_tasks(requirements, architecture)

        # 7. 生成 ADR 摘要
        adr_summary = self._generate_adr(architecture, tasks)

        # 8. 生成 GitHub 产物
        github_artifacts = self._generate_github_artifacts(tasks)

        # 9. 组装结果
        result = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "spec_version": "1.0.1",
                "total_requirements": len(requirements),
                "total_tasks": len(tasks),
                "total_modules": len(architecture),
            },
            "requirements": [r.to_dict() for r in requirements],
            "architecture": architecture,
            "tasks": [t.to_dict() for t in tasks],
            "adr_summary": adr_summary,
            "github": github_artifacts,
        }

        return result

    def _parse_requirements(self, text: str) -> List[RequirementItem]:
        """解析需求文本，提取需求点"""
        requirements: List[RequirementItem] = []

        # 按段落或换行拆分
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 提取需求点（以数字、点号、中划线开头的内容）
        for line in lines:
            # 跳过明显非需求的行
            if line.startswith(("#", "!", "//", "<!--")):
                continue

            # 去除常见前缀
            cleaned = re.sub(r"^[\d\.\-\*•\s]+", "", line)

            if len(cleaned) < 2:
                continue

            # 创建需求项
            req = RequirementItem(cleaned)
            req.confidence = self._estimate_confidence(cleaned)

            # 提取功能点、约束、验收标准
            self._extract_details(req, cleaned)

            requirements.append(req)

        # 如果没有明确的行式需求，尝试整段解析
        if not requirements and len(text.strip()) > 10:
            cleaned = re.sub(r"\s+", " ", text.strip())
            if len(cleaned) >= 10:
                req = RequirementItem(cleaned[:200])  # 截取前200字符
                req.confidence = self._estimate_confidence(cleaned)
                self._extract_details(req, cleaned)
                requirements.append(req)

        return requirements

    def _extract_details(self, req: RequirementItem, text: str) -> None:
        """提取需求中的功能点、约束、验收标准"""
        # 功能点：包含动作性动词的句子
        func_patterns = [
            r"(?:实现|开发|创建|构建|提供|支持|完成)[^。；;]*",
            r"(?:能够|可以|需要)[^。；;]*",
        ]
        for pattern in func_patterns:
            matches = re.findall(pattern, text)
            for m in matches[:3]:  # 每个需求最多提取3个功能点
                if m not in req.functional_points:
                    req.functional_points.append(m.strip())

        # 约束：包含限制性词汇
        constraint_patterns = [
            r"(?:必须|不得|禁止|限制|仅)[^。；;]*",
            r"(?:性能|安全|兼容|稳定)[^。；;]*",
        ]
        for pattern in constraint_patterns:
            matches = re.findall(pattern, text)
            for m in matches[:2]:
                if m not in req.constraints:
                    req.constraints.append(m.strip())

        # 验收标准：包含验收、标准、通过条件等
        accept_patterns = [
            r"(?:验收|标准|通过条件|完成标准)[：:][^。；;]*",
            r"(?:应满足|需满足)[^。；;]*",
        ]
        for pattern in accept_patterns:
            matches = re.findall(pattern, text)
            for m in matches[:2]:
                if m not in req.acceptance_criteria:
                    req.acceptance_criteria.append(m.strip())

        # 如果没有提取到功能点，使用需求文本本身
        if not req.functional_points:
            req.functional_points = [req.text[:100]]

    def _estimate_confidence(self, text: str) -> str:
        """根据关键词估计置信度"""
        if any(kw in text for kw in self.CONFIDENCE_HIGH):
            return "高"
        elif any(kw in text for kw in self.CONFIDENCE_MEDIUM):
            return "中"
        elif any(kw in text for kw in self.CONFIDENCE_LOW):
            return "低"
        else:
            return "中"  # 默认中等置信度

    def _plan_architecture(self, requirements: List[RequirementItem]) -> Dict[str, Any]:
        """规划模块架构"""
        modules: Dict[str, Dict[str, Any]] = {}

        # 初始化模块
        for module_name in self.MODULE_KEYWORDS:
            modules[module_name] = {
                "name": module_name,
                "description": f"{module_name}相关功能模块",
                "dependencies": [],
                "requirements": [],
            }

        # 分配需求到模块
        for req in requirements:
            assigned = False
            for module_name, keywords in self.MODULE_KEYWORDS.items():
                if any(kw in req.text for kw in keywords):
                    modules[module_name]["requirements"].append(req.text[:50])
                    assigned = True
                    break

            # 未匹配则归入后端（默认）
            if not assigned:
                modules["后端"]["requirements"].append(req.text[:50])

        # 清理空模块，建立依赖关系
        active_modules = {}
        module_names = list(modules.keys())
        for i, (name, data) in enumerate(modules.items()):
            if data["requirements"]:
                # 建立简单依赖：后一个模块依赖前一个
                if i > 0 and module_names[i - 1] in active_modules:
                    data["dependencies"].append(module_names[i - 1])
                active_modules[name] = data

        # 如果没有活跃模块，创建默认模块
        if not active_modules:
            active_modules["核心"] = {
                "name": "核心",
                "description": "核心功能模块",
                "dependencies": [],
                "requirements": [r.text[:50] for r in requirements],
            }

        return active_modules

    def _breakdown_tasks(
        self, requirements: List[RequirementItem], architecture: Dict[str, Any]
    ) -> List[TaskItem]:
        """将需求拆解为开发任务"""
        tasks: List[TaskItem] = []
        task_id_counter = 0

        # 为每个模块创建任务
        for module_name, module_data in architecture.items():
            module_reqs = module_data["requirements"]

            # 每个模块创建1-2个任务
            task_count = min(2, len(module_reqs)) if module_reqs else 1

            for i in range(task_count):
                task_id_counter += 1
                req_indices = range(
                    i * (len(module_reqs) // task_count),
                    (i + 1) * (len(module_reqs) // task_count) if task_count > 1 else len(module_reqs),
                )

                task_title = f"{module_name}模块-任务{task_id_counter}"
                task_desc = f"实现{module_name}模块的{len(list(req_indices))}个需求点"

                task = TaskItem(task_title, task_desc)
                task.module = module_name

                # 设置输入输出
                task.inputs = [f"需求规格-{module_name}"]
                task.outputs = [f"{module_name}模块实现"]

                # 设置验收标准
                task.acceptance_criteria = [
                    f"{module_name}模块功能完整实现",
                    "代码通过测试",
                    "文档完善",
                ]

                # 设置依赖
                for dep in module_data.get("dependencies", []):
                    task.dependencies.append(dep)

                # 预估耗时（根据需求数量估算）
                req_count = len(list(req_indices))
                if req_count <= 2:
                    task.estimated_hours = (2, 6)
                elif req_count <= 5:
                    task.estimated_hours = (4, 12)
                else:
                    task.estimated_hours = (8, 24)

                tasks.append(task)

        # 如果没有生成任务，创建默认任务
        if not tasks:
            task = TaskItem("基础功能实现", "实现核心基础功能")
            task.module = "核心"
            task.inputs = ["需求规格"]
            task.outputs = ["基础功能"]
            task.acceptance_criteria = ["核心功能可用"]
            tasks.append(task)

        return tasks

    def _generate_adr(self, architecture: Dict[str, Any], tasks: List[TaskItem]) -> Dict[str, Any]:
        """生成架构决策记录摘要"""
        return {
            "title": "架构决策记录摘要",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "modules": list(architecture.keys()),
            "total_tasks": len(tasks),
            "decisions": [
                {
                    "id": f"ADR-{i+1}",
                    "title": f"采用{name}模块化架构",
                    "context": f"根据需求分析，系统需要{name}模块",
                    "decision": f"使用独立{name}模块，通过接口与其他模块交互",
                    "status": "提议",
                }
                for i, name in enumerate(architecture.keys())
            ],
        }

    def _generate_github_artifacts(self, tasks: List[TaskItem]) -> Dict[str, Any]:
        """生成 GitHub Issue 和 PR 模板"""
        issues = []
        for task in tasks:
            issue = {
                "title": f"[{task.module}] {task.title}",
                "labels": [task.module, "enhancement"],
                "body": f"## 任务描述\n{task.description}\n\n"
                f"### 输入\n{chr(10).join(task.inputs)}\n\n"
                f"### 输出\n{chr(10).join(task.outputs)}\n\n"
                f"### 验收标准\n{chr(10).join(task.acceptance_criteria)}\n\n"
                f"### 预估耗时\n{task.estimated_hours[0]}-{task.estimated_hours[1]}小时",
            }
            issues.append(issue)

        pr_template = {
            "title": "PR: 功能实现",
            "body": "## 变更描述\n\n"
            "## 变更类型\n- [ ] 新功能\n- [ ] Bug修复\n- [ ] 重构\n\n"
            "## 测试计划\n- [ ] 单元测试\n- [ ] 集成测试\n\n"
            "## 关联Issue\n",
        }

        return {"issues": issues, "pr_template": pr_template}


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """格式化输出结果"""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif output_format == "text":
        # 生成可读的文本格式
        lines = []
        lines.append("=" * 60)
        lines.append("规格驱动开发计划")
        lines.append("=" * 60)
        lines.append(f"生成时间: {result['meta']['generated_at']}")
        lines.append(f"需求点数: {result['meta']['total_requirements']}")
        lines.append(f"任务数: {result['meta']['total_tasks']}")
        lines.append(f"模块数: {result['meta']['total_modules']}")
        lines.append("")

        lines.append("【架构规划】")
        for module_name, module_data in result["architecture"].items():
            lines.append(f"  - {module_name}: {module_data['description']}")

        lines.append("")
        lines.append("【任务清单】")
        for task in result["tasks"]:
            lines.append(f"  [{task['id']}] {task['title']} (模块: {task['module']})")
            lines.append(f"      预估: {task['estimated_hours']['min']}-{task['estimated_hours']['max']}小时")
            if task["dependencies"]:
                lines.append(f"      依赖: {', '.join(task['dependencies'])}")

        return "\n".join(lines)
    else:
        raise SpecDrivenError("E004", f"不支持的输出格式: {output_format}")


def run_selftest() -> None:
    """内置自检逻辑，使用硬编码样例数据验证核心功能"""
    print("开始自检...")

    # 硬编码测试数据
    test_input = """
    1. 实现用户登录功能，必须支持邮箱和密码验证
    2. 创建用户数据表，需要存储用户基本信息
    3. 提供用户注册接口，应支持邮箱验证
    4. 开发前端登录页面，建议使用响应式设计
    5. 系统应具备基础安全防护，防止SQL注入
    """

    # 创建处理器
    processor = SpecDrivenProcessor()

    try:
        # 执行处理
        result = processor.process(test_input)

        # 宽松断言：检查关键字段存在性和基本合理性
        assert result is not None, "处理结果不应为空"
        assert "meta" in result, "结果应包含元数据"
        assert "requirements" in result, "结果应包含需求列表"
        assert "architecture" in result, "结果应包含架构规划"
        assert "tasks" in result, "结果应包含任务列表"
        assert "adr_summary" in result, "结果应包含ADR摘要"
        assert "github" in result, "结果应包含GitHub产物"

        # 检查数量范围（宽松判断）
        assert 0 < len(result["requirements"]) <= 10, "需求数量应在合理范围"
        assert 0 < len(result["tasks"]) <= 10, "任务数量应在合理范围"
        assert len(result["architecture"]) >= 1, "至少应有一个模块"

        # 检查任务字段完整性
        for task in result["tasks"]:
            assert "id" in task, "任务应有ID"
            assert "title" in task, "任务应有标题"
            assert "module" in task, "任务应有所属模块"
            assert "estimated_hours" in task, "任务应有预估时间"
            # 宽松时间检查
            est = task["estimated_hours"]
            assert est["min"] > 0, "最小预估时间应大于0"
            assert est["max"] >= est["min"], "最大预估时间应不小于最小预估时间"

        # 检查ADR
        assert len(result["adr_summary"]["decisions"]) >= 1, "ADR摘要应包含决策"

        # 检查GitHub产物
        assert len(result["github"]["issues"]) >= 1, "应生成至少一个Issue"
        assert "pr_template" in result["github"], "应包含PR模板"

        # 检查置信度标注
        for req in result["requirements"]:
            assert req["confidence"] in ["高", "中", "低"], "置信度应为高/中/低"

        # 测试输出格式化
        json_output = format_output(result, "json")
        assert json_output is not None and len(json_output) > 0, "JSON输出不应为空"

        text_output = format_output(result, "text")
        assert text_output is not None and len(text_output) > 0, "文本输出不应为空"

        # 测试错误处理
        try:
            processor.process("")  # 空输入
            assert False, "空输入应抛出异常"
        except SpecDrivenError as e:
            assert e.error_code == "E001", "空输入应返回E001错误码"

        try:
            processor.process("x" * 6000)  # 超长输入
            assert False, "超长输入应抛出异常"
        except SpecDrivenError as e:
            assert e.error_code == "E002", "超长输入应返回E002错误码"

        print("自检通过！所有核心功能验证成功。")
        print(f"  需求点数: {result['meta']['total_requirements']}")
        print(f"  任务数: {result['meta']['total_tasks']}")
        print(f"  模块数: {result['meta']['total_modules']}")

    except AssertionError as e:
        print(f"自检失败: {str(e)}")
        sys.exit(1)
    except SpecDrivenError as e:
        print(f"自检失败: [{e.error_code}] {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"自检失败: 未知错误 {str(e)}")
        sys.exit(1)


def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="规格驱动开发工具：将需求规格转化为开发计划与任务清单",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python main.py --selftest
  python main.py --input "实现用户登录功能"
  python main.py --file requirements.md --output text
        """,
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心功能",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="需求规格文本（直接输入）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="需求规格文件路径（.md/.txt/.json）",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 获取输入
    input_text = ""
    if args.input:
        input_text = args.input
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_text = f.read()
        except FileNotFoundError:
            print("错误: 文件不存在")
            sys.exit(1)
        except Exception as e:
            print(f"错误: 读取文件失败 - {str(e)}")
            sys.exit(1)
    else:
        # 从标准输入读取
        print("请输入需求规格（Ctrl+D 结束输入）:")
        try:
            input_text = sys.stdin.read().strip()
        except KeyboardInterrupt:
            print("\n输入已取消")
            sys.exit(1)

    if not input_text:
        print("错误: 未提供输入内容")
        parser.print_help()
        sys.exit(1)

    # 处理
    try:
        processor = SpecDrivenProcessor()
        result = processor.process(input_text)
        output = format_output(result, args.output)
        print(output)
    except SpecDrivenError as e:
        print(f"错误: [{e.error_code}] {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: [E010] 未知错误 - {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
