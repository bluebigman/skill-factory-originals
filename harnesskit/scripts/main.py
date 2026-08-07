#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harnesskit — 跨环境工作台装配技能（独立实现）

本脚本依据功能规格独立编写，不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能概览：
  - 技能管理：列出、安装、卸载、更新技能包
  - 工具链装配：按依赖关系组合工具为可执行链路
  - MCP 配置：读取、校验、写入 MCP 配置
  - 环境编排：跨环境同步配置，生成差异报告

命令行用法：
  python main.py --selftest          # 离线自检核心逻辑
  python main.py skill list          # 列出技能
  python main.py skill install <名称>
  python main.py skill uninstall <名称>
  python main.py skill update <名称>
  python main.py toolchain build <工具清单JSON>
  python main.py mcp validate <配置JSON>
  python main.py mcp write <配置JSON> <目标路径>
  python main.py env diff <环境A> <环境B>
  python main.py env plan <环境A> <环境B>

错误码：
  E001: 参数错误
  E002: 技能不存在
  E003: 技能安装失败
  E004: 技能卸载失败
  E005: 技能更新失败
  E006: 工具链装配失败
  E007: MCP 配置校验失败
  E008: MCP 配置写入失败
  E009: 环境差异分析失败
  E010: 内部未知错误
"""

import json
import os
import sys
import tempfile
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------

class HarnessKitError(Exception):
    """基类异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _fail(code: str, message: str) -> None:
    """抛出带错误码的异常。"""
    raise HarnessKitError(code, message)


# ---------------------------------------------------------------------------
# 数据模型与内部存储
# ---------------------------------------------------------------------------

class Skill:
    """技能包对象。"""

    def __init__(self, name: str, version: str, description: str = "", dependencies: Optional[List[str]] = None):
        self.name = name
        self.version = version
        self.description = description
        self.dependencies = dependencies or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "dependencies": list(self.dependencies),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
        )


class SkillRegistry:
    """技能注册表（内存实现）。"""

    def __init__(self, initial_skills: Optional[List[Skill]] = None):
        self._skills: Dict[str, Skill] = {}
        if initial_skills:
            for skill in initial_skills:
                self._skills[skill.name] = skill

    def list(self) -> List[Skill]:
        """返回全部技能（按名称排序）。"""
        return [self._skills[name] for name in sorted(self._skills.keys())]

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def install(self, skill: Skill) -> bool:
        """安装技能。若已存在则视为更新。"""
        self._skills[skill.name] = skill
        return True

    def uninstall(self, name: str) -> bool:
        """卸载技能。若不存在返回 False。"""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def update(self, skill: Skill) -> bool:
        """更新技能。若不存在返回 False。"""
        if skill.name in self._skills:
            self._skills[skill.name] = skill
            return True
        return False


# ---------------------------------------------------------------------------
# 工具链装配
# ---------------------------------------------------------------------------

class ToolchainAssembler:
    """工具链装配器：按依赖关系将工具组合为执行链路。"""

    @staticmethod
    def build(tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        输入工具清单，输出装配拓扑图与执行顺序。

        工具格式: {"name": str, "dependencies": [str, ...]}
        """
        if not tools:
            _fail("E006", "工具清单为空，无法装配")

        # 构建依赖图
        graph: Dict[str, List[str]] = {}
        all_names: set = set()

        for tool in tools:
            name = tool.get("name")
            if not name:
                _fail("E006", "工具缺少 name 字段")
            deps = tool.get("dependencies", [])
            graph[name] = list(deps)
            all_names.add(name)
            for dep in deps:
                all_names.add(dep)

        # 检查依赖是否存在（允许外部依赖，但记录警告）
        missing = set()
        for name, deps in graph.items():
            for dep in deps:
                if dep not in graph:
                    missing.add(dep)

        # 拓扑排序（Kahn 算法）
        in_degree: Dict[str, int] = {n: 0 for n in graph}
        for deps in graph.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        exec_order: List[str] = []

        while queue:
            node = queue.pop(0)
            exec_order.append(node)
            for dep in graph.get(node, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

        # 检测环
        if len(exec_order) != len(graph):
            _fail("E006", "依赖关系存在环，无法完成拓扑排序")

        return {
            "topology": graph,
            "execution_order": exec_order,
            "missing_external_deps": sorted(missing),
        }


# ---------------------------------------------------------------------------
# MCP 配置管理
# ---------------------------------------------------------------------------

class MCPConfigManager:
    """MCP 配置管理器：校验与写入。"""

    # 必填字段
    REQUIRED_FIELDS = ["server", "endpoint"]
    # 可选字段
    OPTIONAL_FIELDS = ["auth_type", "timeout", "headers"]

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """校验 MCP 配置，返回校验报告。"""
        report: Dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        # 检查必填字段
        for field in cls.REQUIRED_FIELDS:
            if field not in config or not config[field]:
                report["valid"] = False
                report["errors"].append(f"缺少必填字段: {field}")

        # 检查类型
        if "timeout" in config and config["timeout"] is not None:
            if not isinstance(config["timeout"], (int, float)) or config["timeout"] <= 0:
                report["valid"] = False
                report["errors"].append("timeout 必须为正数")

        if "headers" in config and config["headers"] is not None:
            if not isinstance(config["headers"], dict):
                report["valid"] = False
                report["errors"].append("headers 必须为对象")

        # 检查未知字段（警告）
        known = set(cls.REQUIRED_FIELDS + cls.OPTIONAL_FIELDS)
        for key in config:
            if key not in known:
                report["warnings"].append(f"未知字段: {key}")

        return report

    @classmethod
    def write(cls, config: Dict[str, Any], target_path: str) -> Dict[str, Any]:
        """写入 MCP 配置到目标文件，返回写入结果。"""
        # 先校验
        report = cls.validate(config)
        if not report["valid"]:
            _fail("E007", f"MCP 配置校验失败: {report['errors']}")

        try:
            # 确保目录存在
            parent = os.path.dirname(os.path.abspath(target_path))
            os.makedirs(parent, exist_ok=True)

            # 写入 JSON
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            return {
                "written": True,
                "path": os.path.abspath(target_path),
                "size": os.path.getsize(target_path),
            }
        except OSError as e:
            _fail("E008", f"MCP 配置写入失败: {str(e)}")
        except Exception as e:
            _fail("E008", f"MCP 配置写入失败: {str(e)}")

        # 不可达（_fail 会抛出异常）
        return {"written": False}  # pragma: no cover


# ---------------------------------------------------------------------------
# 环境编排
# ---------------------------------------------------------------------------

class EnvironmentOrchestrator:
    """环境编排器：跨环境同步配置，生成差异报告。"""

    @staticmethod
    def diff(env_a: Dict[str, Any], env_b: Dict[str, Any]) -> Dict[str, Any]:
        """比较两个环境配置，返回差异报告。"""
        report: Dict[str, Any] = {
            "same": True,
            "added": [],
            "removed": [],
            "modified": [],
        }

        keys_a = set(env_a.keys())
        keys_b = set(env_b.keys())

        # 新增的键
        for key in sorted(keys_b - keys_a):
            report["added"].append(key)
            report["same"] = False

        # 删除的键
        for key in sorted(keys_a - keys_b):
            report["removed"].append(key)
            report["same"] = False

        # 修改的键
        for key in sorted(keys_a & keys_b):
            if env_a[key] != env_b[key]:
                report["modified"].append(key)
                report["same"] = False

        return report

    @classmethod
    def plan(cls, env_a: Dict[str, Any], env_b: Dict[str, Any]) -> Dict[str, Any]:
        """生成从环境 A 同步到环境 B 的计划。"""
        diff_report = cls.diff(env_a, env_b)

        plan = {
            "target": "env_b",
            "steps": [],
        }

        # 删除多余键
        for key in diff_report["removed"]:
            plan["steps"].append({"action": "remove", "key": key})

        # 修改差异键
        for key in diff_report["modified"]:
            plan["steps"].append({
                "action": "set",
                "key": key,
                "value": env_b[key],
            })

        # 新增缺失键
        for key in diff_report["added"]:
            plan["steps"].append({
                "action": "set",
                "key": key,
                "value": env_b[key],
            })

        if not diff_report["same"]:
            plan["steps"].append({"action": "apply", "message": "应用配置变更"})

        return plan


# ---------------------------------------------------------------------------
# 内置样例数据（用于自检）
# ---------------------------------------------------------------------------

def _builtin_sample_skills() -> List[Skill]:
    """返回内置样例技能列表。"""
    return [
        Skill(
            name="text-tools",
            version="1.2.0",
            description="文本处理工具集",
            dependencies=[],
        ),
        Skill(
            name="data-parse",
            version="0.9.1",
            description="数据解析器",
            dependencies=["text-tools"],
        ),
        Skill(
            name="report-gen",
            version="2.0.0",
            description="报告生成器",
            dependencies=["data-parse"],
        ),
    ]


def _builtin_sample_tools() -> List[Dict[str, Any]]:
    """返回内置样例工具清单。"""
    return [
        {"name": "fetch", "dependencies": []},
        {"name": "parse", "dependencies": ["fetch"]},
        {"name": "analyze", "dependencies": ["parse"]},
        {"name": "report", "dependencies": ["analyze"]},
    ]


def _builtin_sample_mcp_config() -> Dict[str, Any]:
    """返回内置样例 MCP 配置。"""
    return {
        "server": "local-ai",
        "endpoint": "http://127.0.0.1:8080/mcp",
        "auth_type": "env",
        "timeout": 30,
        "headers": {"Content-Type": "application/json"},
    }


def _builtin_sample_env_a() -> Dict[str, Any]:
    """返回内置样例环境 A 配置。"""
    return {
        "model": "claude-3",
        "temperature": 0.7,
        "max_tokens": 4096,
    }


def _builtin_sample_env_b() -> Dict[str, Any]:
    """返回内置样例环境 B 配置。"""
    return {
        "model": "gpt-4",
        "temperature": 0.5,
        "max_tokens": 8192,
        "top_p": 0.9,
    }


# ---------------------------------------------------------------------------
# 自检逻辑
# ---------------------------------------------------------------------------

def _selftest() -> bool:
    """离线自检核心逻辑，使用内置硬编码样例数据。"""
    print("=== harnesskit 自检开始 ===")

    # 1. 技能管理自检
    print("[1/4] 技能管理...")
    registry = SkillRegistry(initial_skills=_builtin_sample_skills())
    skills = registry.list()
    assert len(skills) == 3, f"技能数量应为 3，实际 {len(skills)}"
    assert skills[0].name == "data-parse", "技能应按名称排序"

    # 安装新技能
    new_skill = Skill("visualizer", "0.1.0", "可视化工具", ["data-parse"])
    registry.install(new_skill)
    assert registry.get("visualizer") is not None, "安装后应能查询到"

    # 更新技能
    updated = Skill("text-tools", "1.3.0", "升级版文本工具")
    assert registry.update(updated), "更新已有技能应返回 True"
    assert registry.get("text-tools").version == "1.3.0", "版本应更新为 1.3.0"

    # 卸载技能
    assert registry.uninstall("visualizer"), "卸载技能应返回 True"
    assert registry.get("visualizer") is None, "卸载后应查询不到"
    assert not registry.uninstall("nonexistent"), "卸载不存在的技能应返回 False"

    print("      技能管理: 通过")

    # 2. 工具链装配自检
    print("[2/4] 工具链装配...")
    assembler = ToolchainAssembler()
    result = assembler.build(_builtin_sample_tools())

    # 执行顺序应包含全部工具
    assert len(result["execution_order"]) == 4, "应有 4 个工具"
    # 第一个应是无依赖的 fetch
    assert result["execution_order"][0] == "fetch", "第一个执行的应为 fetch"
    # 最后一个应为 report
    assert result["execution_order"][-1] == "report", "最后一个执行的应为 report"
    # 依赖关系应正确
    assert result["topology"]["report"] == ["analyze"], "report 依赖 analyze"

    # 环检测
    cyclic_tools = [
        {"name": "a", "dependencies": ["b"]},
        {"name": "b", "dependencies": ["a"]},
    ]
    try:
        assembler.build(cyclic_tools)
        assert False, "环依赖应抛出异常"
    except HarnessKitError as e:
        assert e.code == "E006", f"环依赖错误码应为 E006，实际 {e.code}"

    print("      工具链装配: 通过")

    # 3. MCP 配置自检
    print("[3/4] MCP 配置...")
    mcp_mgr = MCPConfigManager()

    # 有效配置
    valid_report = mcp_mgr.validate(_builtin_sample_mcp_config())
    assert valid_report["valid"], "有效配置应通过校验"

    # 无效配置
    invalid_config = {"server": "test"}  # 缺少 endpoint
    invalid_report = mcp_mgr.validate(invalid_config)
    assert not invalid_report["valid"], "缺少 endpoint 应校验失败"
    assert len(invalid_report["errors"]) > 0, "应有错误信息"

    # 写入测试（使用临时目录）
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "mcp", "config.json")
        write_result = mcp_mgr.write(_builtin_sample_mcp_config(), target)
        assert write_result["written"], "写入应成功"
        assert os.path.exists(target), "文件应存在"

        # 验证写入内容
        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["server"] == "local-ai", "写入内容应正确"

    print("      MCP 配置: 通过")

    # 4. 环境编排自检
    print("[4/4] 环境编排...")
    orch = EnvironmentOrchestrator()
    env_a = _builtin_sample_env_a()
    env_b = _builtin_sample_env_b()

    diff_report = orch.diff(env_a, env_b)
    assert not diff_report["same"], "两个环境应不同"
    assert "top_p" in diff_report["added"], "top_p 应标记为新增"
    assert "max_tokens" in diff_report["modified"], "max_tokens 应标记为修改"

    plan = orch.plan(env_a, env_b)
    assert len(plan["steps"]) >= 3, "计划步骤应不少于 3 步"
    assert plan["steps"][-1]["action"] == "apply", "最后一步应为应用变更"

    # 相同环境
    same_report = orch.diff(env_a, dict(env_a))
    assert same_report["same"], "相同环境应无差异"

    print("      环境编排: 通过")

    print("=== 全部自检通过 ===")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def _cmd_skill_list(registry: SkillRegistry) -> int:
    """列出所有技能。"""
    skills = registry.list()
    if not skills:
        print("（无已安装技能）")
        return 0

    print(f"{'名称':<20} {'版本':<10} 描述")
    print("-" * 60)
    for skill in skills:
        print(f"{skill.name:<20} {skill.version:<10} {skill.description}")
    return 0


def _cmd_skill_install(registry: SkillRegistry, name: str) -> int:
    """安装技能（模拟）。"""
    if not name:
        _fail("E001", "缺少技能名称")

    # 模拟安装：创建新技能对象
    skill = Skill(name=name, version="1.0.0", description=f"手动安装的技能 {name}")
    registry.install(skill)
    print(f"技能已安装: {name} (v1.0.0)")
    return 0


def _cmd_skill_uninstall(registry: SkillRegistry, name: str) -> int:
    """卸载技能。"""
    if not name:
        _fail("E001", "缺少技能名称")

    if registry.uninstall(name):
        print(f"技能已卸载: {name}")
        return 0
    _fail("E002", f"技能不存在: {name}")
    return 1  # 不可达


def _cmd_skill_update(registry: SkillRegistry, name: str) -> int:
    """更新技能（模拟）。"""
    if not name:
        _fail("E001", "缺少技能名称")

    existing = registry.get(name)
    if not existing:
        _fail("E002", f"技能不存在: {name}")

    updated = Skill(name=name, version="2.0.0", description=existing.description)
    registry.update(updated)
    print(f"技能已更新: {name} (v2.0.0)")
    return 0


def _cmd_toolchain_build(tools_json: str) -> int:
    """构建工具链。"""
    try:
        tools = json.loads(tools_json)
    except json.JSONDecodeError:
        _fail("E001", "工具清单 JSON 解析失败")

    assembler = ToolchainAssembler()
    result = assembler.build(tools)

    print("=== 装配拓扑图 ===")
    for node, deps in result["topology"].items():
        dep_str = ", ".join(deps) if deps else "（无）"
        print(f"  {node} -> {dep_str}")

    print("\n=== 执行顺序 ===")
    for i, step in enumerate(result["execution_order"], 1):
        print(f"  {i}. {step}")

    if result["missing_external_deps"]:
        print(f"\n⚠ 外部依赖（不在清单中）: {', '.join(result['missing_external_deps'])}")

    return 0


def _cmd_mcp_validate(config_json: str) -> int:
    """校验 MCP 配置。"""
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError:
        _fail("E001", "配置 JSON 解析失败")

    report = MCPConfigManager.validate(config)
    if report["valid"]:
        print("✅ MCP 配置有效")
    else:
        print("❌ MCP 配置无效:")
        for err in report["errors"]:
            print(f"  - {err}")

    if report["warnings"]:
        print("⚠ 警告:")
        for warn in report["warnings"]:
            print(f"  - {warn}")

    return 0 if report["valid"] else 1


def _cmd_mcp_write(config_json: str, target_path: str) -> int:
    """写入 MCP 配置。"""
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError:
        _fail("E001", "配置 JSON 解析失败")

    result = MCPConfigManager.write(config, target_path)
    print(f"✅ 配置已写入: {result['path']} ({result['size']} 字节)")
    return 0


def _cmd_env_diff(env_a_json: str, env_b_json: str) -> int:
    """比较两个环境配置。"""
    try:
        env_a = json.loads(env_a_json)
        env_b = json.loads(env_b_json)
    except json.JSONDecodeError:
        _fail("E001", "环境配置 JSON 解析失败")

    report = EnvironmentOrchestrator.diff(env_a, env_b)

    if report["same"]:
        print("✅ 两个环境配置相同")
        return 0

    print("环境配置差异:")
    if report["added"]:
        print(f"  新增: {', '.join(report['added'])}")
    if report["removed"]:
        print(f"  删除: {', '.join(report['removed'])}")
    if report["modified"]:
        print(f"  修改: {', '.join(report['modified'])}")

    return 0


def _cmd_env_plan(env_a_json: str, env_b_json: str) -> int:
    """生成环境同步计划。"""
    try:
        env_a = json.loads(env_a_json)
        env_b = json.loads(env_b_json)
    except json.JSONDecodeError:
        _fail("E001", "环境配置 JSON 解析失败")

    plan = EnvironmentOrchestrator.plan(env_a, env_b)

    print(f"同步计划（目标: {plan['target']}）:")
    for i, step in enumerate(plan["steps"], 1):
        if step["action"] == "set":
            print(f"  {i}. 设置 {step['key']} = {json.dumps(step['value'], ensure_ascii=False)}")
        elif step["action"] == "remove":
            print(f"  {i}. 删除 {step['key']}")
        else:
            print(f"  {i}. {step.get('message', step['action'])}")

    return 0


def main() -> int:
    """主入口函数。"""
    args = sys.argv[1:]

    # 自检模式
    if args and args[0] == "--selftest":
        try:
            _selftest()
            return 0
        except AssertionError as e:
            print(f"❌ 自检失败: {e}")
            return 1
        except HarnessKitError as e:
            print(f"❌ 自检失败: [{e.code}] {e.message}")
            return 1

    # 无参数时显示帮助
    if not args:
        print(__doc__)
        return 0

    # 初始化技能注册表（含内置样例）
    registry = SkillRegistry(initial_skills=_builtin_sample_skills())

    try:
        cmd = args[0]

        # 技能管理
        if cmd == "skill" and len(args) >= 2:
            action = args[1]
            if action == "list":
                return _cmd_skill_list(registry)
            elif action == "install" and len(args) >= 3:
                return _cmd_skill_install(registry, args[2])
            elif action == "uninstall" and len(args) >= 3:
                return _cmd_skill_uninstall(registry, args[2])
            elif action == "update" and len(args) >= 3:
                return _cmd_skill_update(registry, args[2])
            else:
                _fail("E001", f"未知技能操作: {action}")

        # 工具链装配
        elif cmd == "toolchain" and len(args) >= 3 and args[1] == "build":
            return _cmd_toolchain_build(args[2])

        # MCP 配置
        elif cmd == "mcp" and len(args) >= 3:
            action = args[1]
            if action == "validate":
                return _cmd_mcp_validate(args[2])
            elif action == "write" and len(args) >= 4:
                return _cmd_mcp_write(args[2], args[3])
            else:
                _fail("E001", f"未知 MCP 操作: {action}")

        # 环境编排
        elif cmd == "env" and len(args) >= 4:
            action = args[1]
            if action == "diff":
                return _cmd_env_diff(args[2], args[3])
            elif action == "plan":
                return _cmd_env_plan(args[2], args[3])
            else:
                _fail("E001", f"未知环境操作: {action}")

        else:
            _fail("E001", f"未知命令或参数不足: {' '.join(args)}")

    except HarnessKitError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E010]: 内部未知错误: {str(e)}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
