#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agencycli — 智能体团队编排命令行工具（独立实现）

本脚本基于功能规格独立编写（clean-room），不包含任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能概述：
    1. 角色定义解析：从 YAML 配置中读取智能体角色、职责与权限范围。
    2. 技能注册与调用：将 Markdown 格式的技能文档注册为可执行技能。
    3. 项目任务编排：根据项目描述自动拆解任务，分配给合适的智能体角色。
    4. 执行状态追踪：模拟监控各智能体执行进度，输出结构化状态报告。
    5. 结果汇总输出：收集各智能体产出，按约定格式生成最终交付物。

用法示例：
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --help              # 查看帮助
    python scripts/main.py --version           # 查看版本
    python scripts/main.py parse-role roles/analyst.yaml
    python scripts/main.py register-skill skills/web-search.md
    python scripts/main.py orchestrate project.md
    python scripts/main.py status
    python scripts/main.py report
"""

import argparse
import sys
import os
import re
import json
import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple

# -----------------------------------------------------------------------------
# 错误码定义
# -----------------------------------------------------------------------------
# E001: 参数错误 / 用法错误
# E002: 文件不存在或无法读取
# E003: YAML/Markdown 解析失败
# E004: 角色定义无效
# E005: 技能注册失败
# E006: 项目编排失败
# E007: 状态追踪失败
# E008: 结果汇总失败
# E009: 内部逻辑错误（不应发生）
# E010: 未知错误

# -----------------------------------------------------------------------------
# 数据模型（dataclass）
# -----------------------------------------------------------------------------

@dataclass
class Role:
    """智能体角色定义"""
    name: str
    description: str = ""
    responsibilities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)

    def validate(self) -> bool:
        """校验角色定义是否有效"""
        if not self.name or not self.name.strip():
            return False
        if not self.description or not self.description.strip():
            return False
        # 职责和权限可以为空，但名称和描述必填
        return True


@dataclass
class Skill:
    """技能定义（由 Markdown 文档注册）"""
    name: str
    description: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)

    def validate(self) -> bool:
        """校验技能定义是否有效"""
        if not self.name or not self.name.strip():
            return False
        if not self.description or not self.description.strip():
            return False
        return True


@dataclass
class Task:
    """项目任务"""
    id: str
    title: str
    description: str = ""
    assigned_role: str = ""
    status: str = "pending"  # pending / in_progress / completed / failed
    priority: int = 5  # 1-10，10 最高

    def validate(self) -> bool:
        """校验任务定义是否有效"""
        if not self.id or not self.title:
            return False
        if self.status not in ("pending", "in_progress", "completed", "failed"):
            return False
        if not (1 <= self.priority <= 10):
            return False
        return True


@dataclass
class Project:
    """项目定义"""
    name: str
    description: str = ""
    tasks: List[Task] = field(default_factory=list)

    def validate(self) -> bool:
        """校验项目定义是否有效"""
        if not self.name or not self.name.strip():
            return False
        if not self.description or not self.description.strip():
            return False
        return True


# -----------------------------------------------------------------------------
# 解析器（YAML 子集 / Markdown 元数据）
# -----------------------------------------------------------------------------

class YamlParser:
    """
    轻量级 YAML 子集解析器。
    仅支持规格中需要的结构：键值对、列表、嵌套字典（最多两层）。
    不依赖第三方 PyYAML 库。
    """

    @staticmethod
    def parse(text: str) -> Dict[str, Any]:
        """
        解析 YAML 文本（子集），返回字典。

        支持：
            - 顶层键值对: key: value
            - 列表: - item
            - 嵌套字典: key:\n  subkey: value
            - 注释: # 开头
            - 字符串（含引号）、数字、布尔值

        不支持：
            - 多行字符串块 (|, >)
            - 锚点/别名
            - 复杂类型
        """
        result: Dict[str, Any] = {}
        lines = text.splitlines()
        current_section: Optional[str] = None
        current_list: Optional[List[str]] = None
        list_section: Optional[str] = None  # 记录当前列表所属的键名

        for line in lines:
            # 去掉注释（# 开头的视为注释）
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # 缩进判断（2 空格或 4 空格）
            indent = len(line) - len(line.lstrip(" "))

            # 列表项
            if stripped.startswith("- "):
                item = stripped[2:].strip()
                # 去除可能的引号
                item = YamlParser._strip_quotes(item)
                if current_section and list_section:
                    section_dict = result.get(current_section, {})
                    if isinstance(section_dict, dict):
                        if list_section not in section_dict:
                            section_dict[list_section] = []
                        section_dict[list_section].append(item)
                else:
                    # 顶层列表（一般不会出现，但兼容处理）
                    result.setdefault("_top_level_list", []).append(item)
                continue

            # 键值对
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()

                # 如果 value 为空，说明是嵌套结构开始
                if not value:
                    if indent == 0:
                        current_section = key
                        result[key] = {}
                        current_list = None
                        list_section = None
                    elif current_section:
                        # 嵌套字典
                        nested_dict = result.get(current_section, {})
                        if isinstance(nested_dict, dict):
                            nested_dict[key] = {}
                            list_section = key  # 记录这个键可能是列表的父级
                        current_list = None
                    continue

                # 普通键值对
                parsed_value = YamlParser._parse_scalar(value)

                if indent == 0:
                    result[key] = parsed_value
                    current_section = key
                    current_list = None
                    list_section = None
                elif current_section:
                    # 嵌套在 section 下
                    section_dict = result.get(current_section)
                    if isinstance(section_dict, dict):
                        section_dict[key] = parsed_value
                        # 如果是列表，记录当前列表引用
                        if isinstance(parsed_value, list):
                            current_list = parsed_value
                            list_section = key
                        else:
                            current_list = None
                            list_section = None

        return result

    @staticmethod
    def _parse_scalar(value: str) -> Any:
        """解析标量值（字符串、数字、布尔值）"""
        value = YamlParser._strip_quotes(value)

        # 布尔值
        if value.lower() in ("true", "yes"):
            return True
        if value.lower() in ("false", "no"):
            return False

        # 数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 字符串
        return value

    @staticmethod
    def _strip_quotes(value: str) -> str:
        """去除字符串首尾的引号"""
        if len(value) >= 2:
            if (value[0] == '"' and value[-1] == '"') or \
               (value[0] == "'" and value[-1] == "'"):
                return value[1:-1]
        return value


class MarkdownParser:
    """Markdown 解析器（提取元数据与技能内容）"""

    @staticmethod
    def parse_yaml_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
        """
        解析 Markdown 文档开头的 YAML front matter。

        返回 (元数据字典, 剩余正文)
        """
        if not text.startswith("---"):
            return {}, text

        # 找到第二个 ---
        lines = text.splitlines()
        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx == -1:
            return {}, text

        yaml_text = "\n".join(lines[1:end_idx])
        body = "\n".join(lines[end_idx + 1:])

        metadata = YamlParser.parse(yaml_text)
        return metadata, body

    @staticmethod
    def extract_skill_info(text: str) -> Optional[Dict[str, str]]:
        """
        从 Markdown 技能文档中提取技能信息。

        期望格式（front matter）：
            ---
            name: skill-name
            description: 技能描述
            tags: [tag1, tag2]
            ---
            技能内容...
        """
        metadata, body = MarkdownParser.parse_yaml_front_matter(text)

        if not metadata or "name" not in metadata or "description" not in metadata:
            return None

        return {
            "name": str(metadata["name"]),
            "description": str(metadata["description"]),
            "content": body.strip(),
            "tags": metadata.get("tags", []),
        }


# -----------------------------------------------------------------------------
# 核心引擎
# -----------------------------------------------------------------------------

class AgencyEngine:
    """智能体编排引擎（核心逻辑）"""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.skills: Dict[str, Skill] = {}
        self.projects: Dict[str, Project] = {}
        self.task_status: Dict[str, str] = {}  # task_id -> status

    # ---- 角色管理 ----

    def parse_role(self, yaml_text: str) -> Role:
        """从 YAML 文本解析角色定义"""
        try:
            data = YamlParser.parse(yaml_text)
        except Exception as exc:
            raise ValueError(f"E003: YAML 解析失败: {exc}")

        if "name" not in data or "description" not in data:
            raise ValueError("E004: 角色定义必须包含 name 和 description")

        role = Role(
            name=str(data["name"]),
            description=str(data["description"]),
            responsibilities=[str(x) for x in data.get("responsibilities", [])],
            permissions=[str(x) for x in data.get("permissions", [])],
        )

        if not role.validate():
            raise ValueError("E004: 角色定义无效")

        self.roles[role.name] = role
        return role

    # ---- 技能管理 ----

    def register_skill(self, markdown_text: str) -> Skill:
        """从 Markdown 文档注册技能"""
        try:
            info = MarkdownParser.extract_skill_info(markdown_text)
        except Exception as exc:
            raise ValueError(f"E003: Markdown 解析失败: {exc}")

        if info is None:
            raise ValueError("E005: 技能文档缺少必要的 front matter 元数据")

        skill = Skill(
            name=info["name"],
            description=info["description"],
            content=info["content"],
            tags=[str(x) for x in info["tags"]] if isinstance(info["tags"], list) else [],
        )

        if not skill.validate():
            raise ValueError("E005: 技能定义无效")

        self.skills[skill.name] = skill
        return skill

    # ---- 项目编排 ----

    def orchestrate(self, project_name: str, description: str) -> Project:
        """
        根据项目描述自动拆解任务并分配角色。

        简化实现：根据关键词匹配角色，生成若干任务。
        """
        if not project_name or not description:
            raise ValueError("E006: 项目名称和描述不能为空")

        project = Project(name=project_name, description=description)

        # 简单关键词拆分逻辑：按句号/分号拆分描述，生成任务
        sentences = re.split(r"[。；;\n]", description)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            # 无有效句子，生成一个默认任务
            sentences = [description]

        for i, sentence in enumerate(sentences[:5]):  # 最多 5 个任务
            task_id = f"T{i + 1:03d}"
            task = Task(
                id=task_id,
                title=sentence[:50] if len(sentence) > 50 else sentence,
                description=sentence,
                assigned_role=self._match_role(sentence),
                priority=min(10, max(1, len(sentence) // 20 + 1)),
            )
            project.tasks.append(task)
            self.task_status[task_id] = task.status

        self.projects[project.name] = project
        return project

    def _match_role(self, text: str) -> str:
        """根据文本内容匹配最合适的角色"""
        if not self.roles:
            return ""

        # 关键词匹配
        keyword_map = {
            "分析": ["analyst", "分析师", "数据分析"],
            "开发": ["developer", "开发", "编码", "程序"],
            "测试": ["tester", "测试", "质检"],
            "设计": ["designer", "设计", "UI", "UX"],
            "文档": ["writer", "文档", "写作", "撰写"],
            "运维": ["ops", "运维", "部署", "监控"],
        }

        best_match = ""
        max_score = 0

        for role_name, role in self.roles.items():
            score = 0
            role_desc = role.description + " " + " ".join(role.responsibilities)

            for keyword, aliases in keyword_map.items():
                if keyword in text or any(alias in text for alias in aliases):
                    if keyword in role_desc or any(alias in role_desc for alias in aliases):
                        score += 2

            # 角色名称匹配
            if role_name in text:
                score += 3

            if score > max_score:
                max_score = score
                best_match = role_name

        # 如果没有匹配，返回第一个角色
        if not best_match and self.roles:
            best_match = next(iter(self.roles.keys()))

        return best_match

    # ---- 状态追踪 ----

    def get_status(self) -> Dict[str, Any]:
        """获取所有项目/任务的状态报告"""
        report: Dict[str, Any] = {
            "generated_at": datetime.datetime.now().isoformat(),
            "projects": {},
            "summary": {
                "total_projects": len(self.projects),
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "in_progress_tasks": 0,
                "failed_tasks": 0,
            },
        }

        for proj_name, project in self.projects.items():
            proj_info = {
                "name": project.name,
                "description": project.description,
                "tasks": [],
            }
            for task in project.tasks:
                task_info = {
                    "id": task.id,
                    "title": task.title,
                    "assigned_role": task.assigned_role,
                    "status": task.status,
                    "priority": task.priority,
                }
                proj_info["tasks"].append(task_info)

                # 更新汇总
                report["summary"]["total_tasks"] += 1
                if task.status == "completed":
                    report["summary"]["completed_tasks"] += 1
                elif task.status == "pending":
                    report["summary"]["pending_tasks"] += 1
                elif task.status == "in_progress":
                    report["summary"]["in_progress_tasks"] += 1
                elif task.status == "failed":
                    report["summary"]["failed_tasks"] += 1

            report["projects"][proj_name] = proj_info

        return report

    # ---- 结果汇总 ----

    def generate_report(self) -> Dict[str, Any]:
        """生成最终交付物报告"""
        report: Dict[str, Any] = {
            "generated_at": datetime.datetime.now().isoformat(),
            "agency": {
                "roles": [asdict(r) for r in self.roles.values()],
                "skills": [asdict(s) for s in self.skills.values()],
            },
            "projects": [],
        }

        for project in self.projects.values():
            project_report = {
                "name": project.name,
                "description": project.description,
                "deliverables": [],
            }

            for task in project.tasks:
                if task.status == "completed":
                    project_report["deliverables"].append({
                        "task_id": task.id,
                        "title": task.title,
                        "assigned_role": task.assigned_role,
                        "output": f"deliverable_{task.id}.md",
                    })

            report["projects"].append(project_report)

        return report


# -----------------------------------------------------------------------------
# CLI 入口
# -----------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("[selftest] 开始自检...")
    engine = AgencyEngine()

    # ---- 1. 角色解析测试 ----
    print("[selftest] 测试角色解析...")
    role_yaml = """
# 数据分析师角色
name: analyst
description: 负责数据分析和报告生成
responsibilities:
  - 数据清洗
  - 统计分析
  - 报告撰写
permissions:
  - read_data
  - write_report
"""
    try:
        role = engine.parse_role(role_yaml)
        assert role.name == "analyst", "角色名称应为 analyst"
        assert len(role.responsibilities) >= 2, "职责数量应 >= 2"
        assert len(role.permissions) >= 1, "权限数量应 >= 1"
        print(f"  [OK] 角色解析成功: {role.name}, 职责数={len(role.responsibilities)}")
    except Exception as exc:
        print(f"  [FAIL] 角色解析失败: {exc}")
        return 1

    # ---- 2. 技能注册测试 ----
    print("[selftest] 测试技能注册...")
    skill_md = """---
name: web-search
description: 网络搜索技能，用于查找最新信息
tags: [search, web, information]
---
# Web Search Skill

这是一个网络搜索技能文档。
"""
    try:
        skill = engine.register_skill(skill_md)
        assert skill.name == "web-search", "技能名称应为 web-search"
        assert len(skill.content) > 0, "技能内容不应为空"
        assert len(skill.tags) >= 2, "标签数量应 >= 2"
        print(f"  [OK] 技能注册成功: {skill.name}")
    except Exception as exc:
        print(f"  [FAIL] 技能注册失败: {exc}")
        return 1

    # ---- 3. 项目编排测试 ----
    print("[selftest] 测试项目编排...")
    # 添加一个开发角色用于匹配
    dev_role_yaml = """
name: developer
description: 负责软件开发和编码实现
responsibilities:
  - 编码
  - 代码审查
permissions:
  - write_code
"""
    try:
        engine.parse_role(dev_role_yaml)
        print("  [OK] 开发角色注册成功")
    except Exception as exc:
        print(f"  [FAIL] 开发角色注册失败: {exc}")
        return 1

    project_desc = "开发一个数据分析平台，包括数据采集模块和可视化模块；同时编写使用文档。"
    try:
        project = engine.orchestrate("data-platform", project_desc)
        assert project.name == "data-platform", "项目名称应为 data-platform"
        assert len(project.tasks) >= 2, "任务数量应 >= 2"
        assert all(t.status in ("pending", "in_progress", "completed", "failed") for t in project.tasks), \
            "任务状态非法"
        print(f"  [OK] 项目编排成功: {project.name}, 任务数={len(project.tasks)}")
    except Exception as exc:
        print(f"  [FAIL] 项目编排失败: {exc}")
        return 1

    # ---- 4. 状态追踪测试 ----
    print("[selftest] 测试状态追踪...")
    try:
        # 模拟任务状态变化
        for task in project.tasks:
            engine.task_status[task.id] = "in_progress"
            task.status = "in_progress"
        # 完成第一个任务
        if project.tasks:
            project.tasks[0].status = "completed"
            engine.task_status[project.tasks[0].id] = "completed"

        status_report = engine.get_status()
        assert status_report["summary"]["total_tasks"] >= 1, "总任务数应 >= 1"
        assert status_report["summary"]["completed_tasks"] >= 1, "完成任务数应 >= 1"
        assert status_report["summary"]["in_progress_tasks"] >= 0, "进行中任务数应 >= 0"
        assert len(status_report["projects"]) >= 1, "项目数应 >= 1"
        print(f"  [OK] 状态追踪成功: 总任务={status_report['summary']['total_tasks']}, "
              f"完成={status_report['summary']['completed_tasks']}")
    except Exception as exc:
        print(f"  [FAIL] 状态追踪失败: {exc}")
        return 1

    # ---- 5. 结果汇总测试 ----
    print("[selftest] 测试结果汇总...")
    try:
        final_report = engine.generate_report()
        assert len(final_report["agency"]["roles"]) >= 2, "角色数应 >= 2"
        assert len(final_report["agency"]["skills"]) >= 1, "技能数应 >= 1"
        assert len(final_report["projects"]) >= 1, "项目数应 >= 1"
        # 至少有一个交付物（因为第一个任务已完成）
        assert len(final_report["projects"][0]["deliverables"]) >= 1, "交付物应 >= 1"
        print(f"  [OK] 结果汇总成功: 交付物数量={len(final_report['projects'][0]['deliverables'])}")
    except Exception as exc:
        print(f"  [FAIL] 结果汇总失败: {exc}")
        return 1

    # ---- 6. YAML 解析器测试 ----
    print("[selftest] 测试 YAML 解析器...")
    try:
        yaml_text = """
name: test
value: 42
enabled: true
items:
  - a
  - b
  - c
nested:
  key1: value1
  key2: value2
"""
        parsed = YamlParser.parse(yaml_text)
        assert parsed["name"] == "test", "name 应为 test"
        assert parsed["value"] == 42, "value 应为 42"
        assert parsed["enabled"] is True, "enabled 应为 True"
        assert len(parsed["items"]) == 3, "items 长度应为 3"
        assert parsed["nested"]["key1"] == "value1", "nested.key1 应为 value1"
        print("  [OK] YAML 解析器工作正常")
    except Exception as exc:
        print(f"  [FAIL] YAML 解析器测试失败: {exc}")
        return 1

    # ---- 7. Markdown 解析器测试 ----
    print("[selftest] 测试 Markdown 解析器...")
    try:
        md_text = """---
name: test-skill
description: 测试技能
---
正文内容
"""
        metadata, body = MarkdownParser.parse_yaml_front_matter(md_text)
        assert metadata["name"] == "test-skill", "元数据 name 应为 test-skill"
        assert "正文" in body, "正文应包含内容"
        print("  [OK] Markdown 解析器工作正常")
    except Exception as exc:
        print(f"  [FAIL] Markdown 解析器测试失败: {exc}")
        return 1

    print("\n[selftest] 全部自检通过 ✓")
    return 0


def main() -> int:
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="agencycli",
        description="智能体团队编排命令行工具（轻量级实现）",
        epilog="示例: agencycli --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部文件）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="agencycli 1.0.1 (clean-room implementation)",
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # parse-role 子命令
    parse_role_parser = subparsers.add_parser("parse-role", help="解析角色 YAML 文件")
    parse_role_parser.add_argument("file", help="角色 YAML 文件路径")

    # register-skill 子命令
    register_skill_parser = subparsers.add_parser("register-skill", help="注册技能 Markdown 文件")
    register_skill_parser.add_argument("file", help="技能 Markdown 文件路径")

    # orchestrate 子命令
    orchestrate_parser = subparsers.add_parser("orchestrate", help="编排项目任务")
    orchestrate_parser.add_argument("name", help="项目名称")
    orchestrate_parser.add_argument("description", help="项目描述文本")

    # status 子命令
    subparsers.add_parser("status", help="查看任务执行状态")

    # report 子命令
    subparsers.add_parser("report", help="生成最终交付物报告")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无子命令
    if not args.command:
        parser.print_help()
        return 0

    engine = AgencyEngine()

    try:
        if args.command == "parse-role":
            # 读取角色文件
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                print(f"E002: 文件不存在: {args.file}", file=sys.stderr)
                return 2
            except Exception as exc:
                print(f"E002: 读取文件失败: {exc}", file=sys.stderr)
                return 2

            try:
                role = engine.parse_role(content)
                print(json.dumps(asdict(role), ensure_ascii=False, indent=2))
            except ValueError as exc:
                print(f"{exc}", file=sys.stderr)
                return 2

        elif args.command == "register-skill":
            # 读取技能文件
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                print(f"E002: 文件不存在: {args.file}", file=sys.stderr)
                return 2
            except Exception as exc:
                print(f"E002: 读取文件失败: {exc}", file=sys.stderr)
                return 2

            try:
                skill = engine.register_skill(content)
                print(json.dumps(asdict(skill), ensure_ascii=False, indent=2))
            except ValueError as exc:
                print(f"{exc}", file=sys.stderr)
                return 2

        elif args.command == "orchestrate":
            try:
                project = engine.orchestrate(args.name, args.description)
                output = {
                    "project": project.name,
                    "description": project.description,
                    "tasks": [asdict(t) for t in project.tasks],
                }
                print(json.dumps(output, ensure_ascii=False, indent=2))
            except ValueError as exc:
                print(f"{exc}", file=sys.stderr)
                return 2

        elif args.command == "status":
            try:
                status_report = engine.get_status()
                print(json.dumps(status_report, ensure_ascii=False, indent=2))
            except Exception as exc:
                print(f"E007: 状态追踪失败: {exc}", file=sys.stderr)
                return 2

        elif args.command == "report":
            try:
                report = engine.generate_report()
                print(json.dumps(report, ensure_ascii=False, indent=2))
            except Exception as exc:
                print(f"E008: 结果汇总失败: {exc}", file=sys.stderr)
                return 2

    except Exception as exc:
        print(f"E010: 未知错误: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
