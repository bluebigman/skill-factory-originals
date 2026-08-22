#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harnesskit — 跨环境工作台装配器

功能：
  - 技能管理：列出、安装、卸载、更新技能包
  - 工具链装配：按依赖关系组合工具为可执行链路
  - MCP 配置：读取、校验、写入 MCP 配置
  - 环境编排：跨环境同步配置，生成差异报告

用法：
  python run.py --selftest
  python run.py skill list
  python run.py skill install <名称> [--dry-run]
  python run.py skill uninstall <名称> [--force]
  python run.py skill update <名称> [--dry-run]
  python run.py toolchain build <工具清单JSON>
  python run.py mcp validate <配置JSON>
  python run.py mcp write <配置JSON> <目标路径> [--dry-run]
  python run.py env diff <环境A> <环境B>
  python run.py env plan <环境A> <环境B>

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

import argparse
import json
import os
import sys
import tempfile
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

DEFAULT_HOME = Path.home() / ".harnesskit"
SKILLS_DIR = "skills"
CONFIG_FILE = "config.json"
ENCODINGS = ["utf-8", "gbk", "gb18030"]
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5  # 秒

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


def _now_utc() -> str:
    """返回 UTC 时间戳字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class Skill:
    """技能包对象。"""

    def __init__(self, name: str, version: str, description: str = "",
                 dependencies: Optional[List[str]] = None):
        self.name = name
        self.version = version
        self.description = description
        self.dependencies = dependencies or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """从字典创建 Skill 对象。"""
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
        )


class Toolchain:
    """工具链对象。"""

    def __init__(self, name: str, tools: List[str]):
        self.name = name
        self.tools = tools

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "tools": self.tools}


# ---------------------------------------------------------------------------
# 存储管理
# ---------------------------------------------------------------------------

class Storage:
    """管理技能存储目录。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(os.environ.get("HARNESSKIT_HOME", DEFAULT_HOME))
        self.skills_dir = self.base_dir / SKILLS_DIR
        self.config_path = self.base_dir / CONFIG_FILE
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """确保目录结构存在。"""
        try:
            self.skills_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            _fail("E010", f"无法创建存储目录: {e}")

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """读取 JSON 文件，支持多编码。"""
        if not path.exists():
            return {}
        for encoding in ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as f:
                    return json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        _fail("E010", f"无法读取文件（编码不支持）: {path}")

    def _write_json_atomic(self, path: Path, data: Dict[str, Any]) -> None:
        """原子化写入 JSON 文件。"""
        try:
            fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, str(path))
            except Exception:
                os.unlink(tmp_path)
                raise
        except OSError as e:
            _fail("E010", f"写入文件失败: {e}")

    def list_skills(self) -> List[Skill]:
        """列出所有已安装技能。"""
        skills = []
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                data = self._read_json(skill_file)
                if data:
                    skills.append(Skill.from_dict(data))
            except HarnessKitError:
                continue
        return sorted(skills, key=lambda s: s.name)

    def get_skill(self, name: str) -> Optional[Skill]:
        """获取指定技能。"""
        skill_path = self.skills_dir / f"{name}.json"
        if not skill_path.exists():
            return None
        data = self._read_json(skill_path)
        return Skill.from_dict(data) if data else None

    def install_skill(self, skill: Skill, dry_run: bool = False) -> bool:
        """安装技能包。"""
        if dry_run:
            print(f"[DRY-RUN] 将安装技能: {skill.name}@{skill.version}")
            return True
        skill_path = self.skills_dir / f"{skill.name}.json"
        self._write_json_atomic(skill_path, skill.to_dict())
        return True

    def uninstall_skill(self, name: str, dry_run: bool = False) -> bool:
        """卸载技能包。"""
        skill_path = self.skills_dir / f"{name}.json"
        if not skill_path.exists():
            _fail("E002", f"技能不存在: {name}")
        if dry_run:
            print(f"[DRY-RUN] 将卸载技能: {name}")
            return True
        try:
            skill_path.unlink()
            return True
        except OSError as e:
            _fail("E004", f"技能卸载失败: {e}")

    def update_skill(self, skill: Skill, dry_run: bool = False) -> bool:
        """更新技能包。"""
        existing = self.get_skill(skill.name)
        if not existing:
            _fail("E002", f"技能不存在: {skill.name}")
        if dry_run:
            print(f"[DRY-RUN] 将更新技能: {skill.name} {existing.version} -> {skill.version}")
            return True
        return self.install_skill(skill, dry_run=False)


# ---------------------------------------------------------------------------
# 工具链装配
# ---------------------------------------------------------------------------

def build_toolchain(tools: List[str], dependencies: Dict[str, List[str]]) -> List[str]:
    """按依赖关系构建工具链（拓扑排序）。

    Args:
        tools: 工具列表
        dependencies: 工具依赖关系 {工具名: [依赖工具列表]}

    Returns:
        排序后的工具链列表

    Raises:
        HarnessKitError: 存在循环依赖或未知工具
    """
    # 构建依赖图
    graph: Dict[str, List[str]] = {tool: [] for tool in tools}
    in_degree: Dict[str, int] = {tool: 0 for tool in tools}

    for tool in tools:
        for dep in dependencies.get(tool, []):
            if dep not in tools:
                _fail("E006", f"未知依赖工具: {dep} (依赖方: {tool})")
            graph[dep].append(tool)
            in_degree[tool] += 1

    # Kahn 算法拓扑排序
    queue = deque([t for t in tools if in_degree[t] == 0])
    result = []

    while queue:
        tool = queue.popleft()
        result.append(tool)
        for dependent in graph[tool]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) != len(tools):
        _fail("E006", "存在循环依赖，无法构建工具链")

    return result


# ---------------------------------------------------------------------------
# MCP 配置管理
# ---------------------------------------------------------------------------

def validate_mcp_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """校验 MCP 配置。

    Args:
        config: MCP 配置字典

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []
    servers = config.get("servers", {})
    if not isinstance(servers, dict):
        errors.append("servers 必须是对象")
        return False, errors

    for name, server in servers.items():
        if not isinstance(server, dict):
            errors.append(f"服务器 '{name}' 必须是对象")
            continue
        if "command" not in server:
            errors.append(f"服务器 '{name}' 缺少 command 字段")
        if "args" in server and not isinstance(server["args"], list):
            errors.append(f"服务器 '{name}' 的 args 必须是数组")
        if "env" in server and not isinstance(server["env"], dict):
            errors.append(f"服务器 '{name}' 的 env 必须是对象")

    return len(errors) == 0, errors


def write_mcp_config(config: Dict[str, Any], target_path: Path, dry_run: bool = False) -> bool:
    """写入 MCP 配置（原子化）。

    Args:
        config: MCP 配置字典
        target_path: 目标文件路径
        dry_run: 是否仅预览

    Returns:
        是否成功
    """
    valid, errors = validate_mcp_config(config)
    if not valid:
        _fail("E007", f"MCP 配置校验失败: {'; '.join(errors)}")

    if dry_run:
        server_count = len(config.get("servers", {}))
        print(f"[DRY-RUN] 将写入配置到: {target_path} ({server_count} 个服务器)")
        return True

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(target_path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(target_path))
        except Exception:
            os.unlink(tmp_path)
            raise
        return True
    except OSError as e:
        _fail("E008", f"MCP 配置写入失败: {e}")


# ---------------------------------------------------------------------------
# 环境差异分析
# ---------------------------------------------------------------------------

def _load_env_config(path: Path) -> Dict[str, Any]:
    """加载环境配置文件。"""
    if not path.exists():
        _fail("E009", f"环境配置文件不存在: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        # 尝试其他编码
        for encoding in ENCODINGS[1:]:
            try:
                with open(path, "r", encoding=encoding) as f:
                    return json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        _fail("E009", f"无法解析环境配置文件: {path} ({e})")


def env_diff(env_a: Dict[str, Any], env_b: Dict[str, Any]) -> List[Dict[str, str]]:
    """对比两个环境配置，返回差异列表。

    Args:
        env_a: 环境 A 配置
        env_b: 环境 B 配置

    Returns:
        差异项列表，每项包含 type/name/old/new 字段
    """
    diffs = []

    # 对比技能
    skills_a = {s["name"]: s.get("version", "0.0.0") for s in env_a.get("skills", [])}
    skills_b = {s["name"]: s.get("version", "0.0.0") for s in env_b.get("skills", [])}

    for name in skills_b:
        if name not in skills_a:
            diffs.append({"type": "新增", "name": f"skill:{name}", "old": "-", "new": skills_b[name]})
        elif skills_a[name] != skills_b[name]:
            diffs.append({"type": "变更", "name": f"skill:{name}", "old": skills_a[name], "new": skills_b[name]})

    for name in skills_a:
        if name not in skills_b:
            diffs.append({"type": "删除", "name": f"skill:{name}", "old": skills_a[name], "new": "-"})

    # 对比工具
    tools_a = set(env_a.get("tools", []))
    tools_b = set(env_b.get("tools", []))

    for tool in tools_b - tools_a:
        diffs.append({"type": "新增", "name": f"tool:{tool}", "old": "-", "new": "present"})
    for tool in tools_a - tools_b:
        diffs.append({"type": "删除", "name": f"tool:{tool}", "old": "present", "new": "-"})

    # 对比 MCP 服务器
    mcp_a = set(env_a.get("mcp_servers", []))
    mcp_b = set(env_b.get("mcp_servers", []))

    for server in mcp_b - mcp_a:
        diffs.append({"type": "新增", "name": f"mcp:{server}", "old": "-", "new": "present"})
    for server in mcp_a - mcp_b:
        diffs.append({"type": "删除", "name": f"mcp:{server}", "old": "present", "new": "-"})

    return diffs


def generate_env_plan(env_a: Dict[str, Any], env_b: Dict[str, Any]) -> List[str]:
    """生成环境迁移计划。

    Args:
        env_a: 源环境配置
        env_b: 目标环境配置

    Returns:
        迁移步骤列表
    """
    diffs = env_diff(env_a, env_b)
    plan = []

    for diff in diffs:
        if diff["type"] == "新增":
            plan.append(f"安装 {diff['name']} (版本: {diff['new']})")
        elif diff["type"] == "删除":
            plan.append(f"卸载 {diff['name']} (原版本: {diff['old']})")
        elif diff["type"] == "变更":
            plan.append(f"更新 {diff['name']}: {diff['old']} -> {diff['new']}")

    return plan


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def cmd_skill_list(args: argparse.Namespace, storage: Storage) -> int:
    """处理 skill list 命令。"""
    skills = storage.list_skills()
    if not skills:
        print("未安装任何技能")
        return 0
    print(f"已安装技能 ({len(skills)}):")
    for skill in skills:
        deps = f" (依赖: {', '.join(skill.dependencies)})" if skill.dependencies else ""
        print(f"  - {skill.name}@{skill.version}{deps}")
    return 0


def cmd_skill_install(args: argparse.Namespace, storage: Storage) -> int:
    """处理 skill install 命令。"""
    try:
        # 构造技能对象
        skill = Skill(
            name=args.name,
            version=args.version or "1.0.0",
            description=args.description or "",
            dependencies=args.dependencies or [],
        )
        storage.install_skill(skill, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"技能 {skill.name}@{skill.version} 安装成功")
        return 0
    except HarnessKitError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_skill_uninstall(args: argparse.Namespace, storage: Storage) -> int:
    """处理 skill uninstall 命令。"""
    try:
        if not args.force and not args.dry_run:
            print(f"警告: 将卸载技能 {args.name}。使用 --force 确认执行。", file=sys.stderr)
            return 1
        storage.uninstall_skill(args.name, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"技能 {args.name} 卸载成功")
        return 0
    except HarnessKitError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_skill_update(args: argparse.Namespace, storage: Storage) -> int:
    """处理 skill update 命令。"""
    try:
        existing = storage.get_skill(args.name)
        if not existing:
            _fail("E002", f"技能不存在: {args.name}")
        new_skill = Skill(
            name=args.name,
            version=args.version or "2.0.0",
            description=existing.description,
            dependencies=existing.dependencies,
        )
        storage.update_skill(new_skill, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"技能 {args.name} 更新到 {new_skill.version} 成功")
        return 0
    except HarnessKitError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_toolchain_build(args: argparse.Namespace) -> int:
    """处理 toolchain build 命令。"""
    try:
        data = json.loads(args.spec)
        tools = data.get("tools", [])
        dependencies = data.get("dependencies", {})
        if not tools:
            _fail("E006", "工具列表不能为空")
        result = build_toolchain(tools, dependencies)
        print(f"工具链构建成功 ({len(result)} 个工具):")
        for i, tool in enumerate(result, 1):
            print(f"  {i}. {tool}")
        return 0
    except (json.JSONDecodeError, HarnessKitError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_mcp_validate(args: argparse.Namespace) -> int:
    """处理 mcp validate 命令。"""
    try:
        config = json.loads(args.config)
        valid, errors = validate_mcp_config(config)
        if valid:
            server_count = len(config.get("servers", {}))
            print(f"MCP 配置校验通过: {server_count} 个服务器")
            return 0
        else:
            print(f"MCP 配置校验失败 ({len(errors)} 个错误):", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败: {e}", file=sys.stderr)
        return 1


def cmd_mcp_write(args: argparse.Namespace) -> int:
    """处理 mcp write 命令。"""
    try:
        config = json.loads(args.config)
        target = Path(args.target)
        write_mcp_config(config, target, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"配置已写入: {target}")
        return 0
    except (json.JSONDecodeError, HarnessKitError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_env_diff(args: argparse.Namespace) -> int:
    """处理 env diff 命令。"""
    try:
        env_a = _load_env_config(Path(args.env_a))
        env_b = _load_env_config(Path(args.env_b))
        diffs = env_diff(env_a, env_b)
        if not diffs:
            print("两个环境配置完全一致")
            return 0
        print(f"差异项: {len(diffs)}")
        for diff in diffs:
            print(f"  - [{diff['type']}] {diff['name']}: {diff['old']} -> {diff['new']}")
        return 0
    except HarnessKitError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_env_plan(args: argparse.Namespace) -> int:
    """处理 env plan 命令。"""
    try:
        env_a = _load_env_config(Path(args.env_a))
        env_b = _load_env_config(Path(args.env_b))
        plan = generate_env_plan(env_a, env_b)
        if not plan:
            print("无需迁移，两个环境配置一致")
            return 0
        print(f"迁移计划 ({len(plan)} 步):")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step}")
        return 0
    except HarnessKitError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """运行自检，验证核心功能。"""
    print("=" * 60)
    print("HarnessKit 自检开始")
    print(f"时间: {_now_utc()}")
    print("=" * 60)

    failures = 0

    # 1. 测试工具链构建
    print("\n[1/5] 测试工具链构建...")
    try:
        tools = ["a", "b", "c", "d"]
        deps = {"b": ["a"], "c": ["b"], "d": ["a", "c"]}
        result = build_toolchain(tools, deps)
        assert len(result) == 4, f"工具链长度应为 4，实际 {len(result)}"
        assert result[0] == "a", f"第一个工具应为 a，实际 {result[0]}"
        assert result[-1] == "d", f"最后一个工具应为 d，实际 {result[-1]}"
        print(f"  ✓ 工具链构建成功: {result}")
    except Exception as e:
        print(f"  ✗ 工具链构建失败: {e}")
        failures += 1

    # 2. 测试循环依赖检测
    print("\n[2/5] 测试循环依赖检测...")
    try:
        tools = ["a", "b"]
        deps = {"a": ["b"], "b": ["a"]}
        try:
            build_toolchain(tools, deps)
            print("  ✗ 应检测到循环依赖但未检测到")
            failures += 1
        except HarnessKitError as e:
            assert e.code == "E006", f"错误码应为 E006，实际 {e.code}"
            print(f"  ✓ 循环依赖检测成功: {e.message}")
    except Exception as e:
        print(f"  ✗ 循环依赖测试异常: {e}")
        failures += 1

    # 3. 测试 MCP 配置校验
    print("\n[3/5] 测试 MCP 配置校验...")
    try:
        # 有效配置
        valid_config = {
            "servers": {
                "github": {"command": "node", "args": ["server.js"]},
                "filesystem": {"command": "python", "args": ["fs_server.py"]},
            }
        }
        valid, errors = validate_mcp_config(valid_config)
        assert valid, f"有效配置应通过校验: {errors}"
        assert len(errors) == 0, f"有效配置不应有错误: {errors}"

        # 无效配置
        invalid_config = {
            "servers": {
                "bad": {"args": ["missing_command"]},
            }
        }
        valid, errors = validate_mcp_config(invalid_config)
        assert not valid, "无效配置应校验失败"
        assert len(errors) == 1, f"应有 1 个错误，实际 {len(errors)}"
        print(f"  ✓ MCP 配置校验正常 (有效: {len(valid_config['servers'])} 服务器, 无效: {len(errors)} 错误)")
    except Exception as e:
        print(f"  ✗ MCP 配置校验测试失败: {e}")
        failures += 1

    # 4. 测试环境差异分析
    print("\n[4/5] 测试环境差异分析...")
    try:
        env_a = {
            "skills": [
                {"name": "skill1", "version": "1.0.0"},
                {"name": "skill2", "version": "2.0.0"},
            ],
            "tools": ["tool1", "tool2"],
            "mcp_servers": ["server1"],
        }
        env_b = {
            "skills": [
                {"name": "skill1", "version": "1.5.0"},
                {"name": "skill3", "version": "1.0.0"},
            ],
            "tools": ["tool1", "tool3"],
            "mcp_servers": ["server1", "server2"],
        }
        diffs = env_diff(env_a, env_b)
        assert len(diffs) == 6, f"应有 6 个差异，实际 {len(diffs)}: {diffs}"

        # 验证差异类型
        types = [d["type"] for d in diffs]
        assert "变更" in types, f"应有变更类型差异: {types}"
        assert "新增" in types, f"应有新增类型差异: {types}"
        assert "删除" in types, f"应有删除类型差异: {types}"

        # 验证具体差异
        skill1_diff = [d for d in diffs if d["name"] == "skill:skill1"]
        assert len(skill1_diff) == 1, f"skill1 应有 1 个差异: {skill1_diff}"
        assert skill1_diff[0]["old"] == "1.0.0", f"skill1 旧版本应为 1.0.0: {skill1_diff}"
        assert skill1_diff[0]["new"] == "1.5.0", f"skill1 新版本应为 1.5.0: {skill1_diff}"

        print(f"  ✓ 环境差异分析正常 ({len(diffs)} 个差异)")
    except Exception as e:
        print(f"  ✗ 环境差异分析测试失败: {e}")
        failures += 1

    # 5. 测试存储管理
    print("\n[5/5] 测试存储管理...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(Path(tmpdir))
            # 安装技能
            skill = Skill("test_skill", "1.0.0", "测试技能", ["dep1"])
            storage.install_skill(skill)
            # 列出技能
            skills = storage.list_skills()
            assert len(skills) == 1, f"应有 1 个技能，实际 {len(skills)}"
            assert skills[0].name == "test_skill", f"技能名应为 test_skill: {skills[0].name}"
            assert skills[0].version == "1.0.0", f"版本应为 1.0.0: {skills[0].version}"
            # 获取技能
            fetched = storage.get_skill("test_skill")
            assert fetched is not None, "应能获取技能"
            assert fetched.dependencies == ["dep1"], f"依赖应为 ['dep1']: {fetched.dependencies}"
            # 卸载技能
            storage.uninstall_skill("test_skill")
            skills = storage.list_skills()
            assert len(skills) == 0, f"卸载后应为 0 个技能，实际 {len(skills)}"
            print("  ✓ 存储管理正常")
    except Exception as e:
        print(f"  ✗ 存储管理测试失败: {e}")
        failures += 1

    # 汇总
    print("\n" + "=" * 60)
    if failures == 0:
        print(f"自检通过: 全部测试成功 ({_now_utc()})")
        print("=" * 60)
        return 0
    else:
        print(f"自检失败: {failures} 个测试未通过 ({_now_utc()})")
        print("=" * 60)
        return 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI 主入口。"""
    parser = argparse.ArgumentParser(
        prog="harnesskit",
        description="跨环境工作台装配器 - 管理技能、工具链、MCP 配置与环境同步",
    )
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--dry-run", action="store_true", help="预览操作，不实际写入")
    parser.add_argument("--force", action="store_true", help="强制执行（跳过确认）")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # skill 子命令
    skill_parser = subparsers.add_parser("skill", help="技能管理")
    skill_sub = skill_parser.add_subparsers(dest="skill_command", help="技能操作")

    # skill list
    list_parser = skill_sub.add_parser("list", help="列出技能")
    list_parser.set_defaults(func=cmd_skill_list)

    # skill install
    install_parser = skill_sub.add_parser("install", help="安装技能")
    install_parser.add_argument("--name", help="技能名称")
    install_parser.add_argument("--version", help="技能版本")
    install_parser.add_argument("--description", help="技能描述")
    install_parser.add_argument("--dependencies", nargs="*", default=[], help="依赖技能列表")
    install_parser.set_defaults(func=cmd_skill_install)

    # skill uninstall
    uninstall_parser = skill_sub.add_parser("uninstall", help="卸载技能")
    uninstall_parser.add_argument("--name", help="技能名称")
    uninstall_parser.set_defaults(func=cmd_skill_uninstall)

    # skill update
    update_parser = skill_sub.add_parser("update", help="更新技能")
    update_parser.add_argument("--name", help="技能名称")
    update_parser.add_argument("--version", help="新版本号")
    update_parser.set_defaults(func=cmd_skill_update)

    # toolchain 子命令
    toolchain_parser = subparsers.add_parser("toolchain", help="工具链管理")
    toolchain_sub = toolchain_parser.add_subparsers(dest="toolchain_command", help="工具链操作")

    # toolchain build
    build_parser = toolchain_sub.add_parser("build", help="构建工具链")
    build_parser.add_argument("--spec", help="工具链规格 JSON")
    build_parser.set_defaults(func=cmd_toolchain_build)

    # mcp 子命令
    mcp_parser = subparsers.add_parser("mcp", help="MCP 配置管理")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_command", help="MCP 操作")

    # mcp validate
    validate_parser = mcp_sub.add_parser("validate", help="校验 MCP 配置")
    validate_parser.add_argument("--config", help="MCP 配置 JSON")
    validate_parser.set_defaults(func=cmd_mcp_validate)

    # mcp write
    write_parser = mcp_sub.add_parser("write", help="写入 MCP 配置")
    write_parser.add_argument("--config", help="MCP 配置 JSON")
    write_parser.add_argument("--target", help="目标文件路径")
    write_parser.set_defaults(func=cmd_mcp_write)

    # env 子命令
    env_parser = subparsers.add_parser("env", help="环境管理")
    env_sub = env_parser.add_subparsers(dest="env_command", help="环境操作")

    # env diff
    diff_parser = env_sub.add_parser("diff", help="对比环境差异")
    diff_parser.add_argument("--env_a", help="环境 A 配置")
    diff_parser.add_argument("--env_b", help="环境 B 配置")
    diff_parser.set_defaults(func=cmd_env_diff)

    # env plan
    plan_parser = env_sub.add_parser("plan", help="生成迁移计划")
    plan_parser.add_argument("--env_a", help="环境 A 配置")
    plan_parser.add_argument("--env_b", help="环境 B 配置")
    plan_parser.set_defaults(func=cmd_env_plan)

    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # 创建存储实例
    storage = Storage()

    # 执行子命令
    try:
        if hasattr(args, "func"):
            return args.func(args, storage)
        else:
            parser.print_help()
            return 0
    except HarnessKitError as e:
        print(f"错误: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
