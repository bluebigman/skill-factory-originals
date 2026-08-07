#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harnesskit — 工具链装配与技能管理助手（独立实现）

本脚本依据功能规格独立编写，用于：
  - 技能清单盘点
  - MCP 服务器配置管理
  - 插件与钩子管理
  - 配置文件编排
  - 记忆与规则同步

仅使用 Python 标准库，无第三方依赖。
支持 --selftest 离线自检。
"""

import argparse
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件错误：无法读取或写入指定文件",
    "E003": "配置错误：配置内容格式不正确或字段缺失",
    "E004": "技能错误：技能不存在或版本不匹配",
    "E005": "MCP错误：MCP服务器配置无效或连接参数缺失",
    "E006": "插件错误：插件不存在或状态操作无效",
    "E007": "钩子错误：钩子事件注册或移除失败",
    "E008": "回滚错误：配置回滚失败或备份不存在",
    "E009": "记忆错误：记忆或规则同步失败",
    "E010": "内部错误：未预期的异常",
}


def error_message(code: str) -> str:
    """返回错误码对应的中文说明。"""
    return f"[{code}] {ERROR_CODES.get(code, '未知错误')}"


# ---------------------------------------------------------------------------
# 数据模型（内存存储，不依赖外部文件）
# ---------------------------------------------------------------------------
class Skill:
    """技能条目。"""

    def __init__(self, name: str, version: str, description: str = ""):
        self.name = name
        self.version = version
        self.description = description

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version, "description": self.description}


class MCPServer:
    """MCP 服务器配置条目。"""

    def __init__(self, name: str, url: str, protocol: str = "http", auth_type: str = "none"):
        self.name = name
        self.url = url
        self.protocol = protocol
        self.auth_type = auth_type

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "protocol": self.protocol,
            "auth_type": self.auth_type,
        }


class Plugin:
    """插件条目。"""

    def __init__(self, name: str, enabled: bool = True, hooks: list = None):
        self.name = name
        self.enabled = enabled
        self.hooks = hooks if hooks is not None else []

    def to_dict(self) -> dict:
        return {"name": self.name, "enabled": self.enabled, "hooks": list(self.hooks)}


class ConfigEntry:
    """配置文件条目。"""

    def __init__(self, key: str, value, source: str = "default"):
        self.key = key
        self.value = value
        self.source = source

    def to_dict(self) -> dict:
        return {"key": self.key, "value": self.value, "source": self.source}


class MemoryItem:
    """记忆/规则条目。"""

    def __init__(self, content: str, category: str = "general", tags: list = None):
        self.content = content
        self.category = category
        self.tags = tags if tags is not None else []

    def to_dict(self) -> dict:
        return {"content": self.content, "category": self.category, "tags": list(self.tags)}


# ---------------------------------------------------------------------------
# 核心管理器
# ---------------------------------------------------------------------------
class HarnessKit:
    """工具链装配管理器（内存实现）。"""

    def __init__(self):
        self.skills = {}          # name -> Skill
        self.mcp_servers = {}     # name -> MCPServer
        self.plugins = {}         # name -> Plugin
        self.configs = {}         # key -> ConfigEntry
        self.memories = []        # list of MemoryItem
        self.config_backups = []  # list of (key, old_value) 用于回滚

    # ---- 技能管理 ------------------------------------------------------
    def add_skill(self, name: str, version: str, description: str = "") -> str:
        """添加或更新技能。返回技能名称。"""
        if not name or not version:
            raise ValueError(error_message("E001"))
        self.skills[name] = Skill(name, version, description)
        return name

    def remove_skill(self, name: str) -> bool:
        """移除技能。不存在时返回 False。"""
        if name in self.skills:
            del self.skills[name]
            return True
        return False

    def list_skills(self) -> list:
        """列出所有技能。"""
        return [s.to_dict() for s in self.skills.values()]

    def get_skill(self, name: str) -> dict:
        """获取单个技能。不存在时抛异常。"""
        if name not in self.skills:
            raise KeyError(error_message("E004"))
        return self.skills[name].to_dict()

    # ---- MCP 管理 ------------------------------------------------------
    def add_mcp(self, name: str, url: str, protocol: str = "http", auth_type: str = "none") -> str:
        """添加或更新 MCP 服务器。"""
        if not name or not url:
            raise ValueError(error_message("E001"))
        if protocol not in ("http", "https", "ws", "wss", "stdio"):
            raise ValueError(error_message("E005"))
        self.mcp_servers[name] = MCPServer(name, url, protocol, auth_type)
        return name

    def remove_mcp(self, name: str) -> bool:
        """移除 MCP 服务器。"""
        if name in self.mcp_servers:
            del self.mcp_servers[name]
            return True
        return False

    def list_mcp(self) -> list:
        """列出所有 MCP 服务器。"""
        return [s.to_dict() for s in self.mcp_servers.values()]

    # ---- 插件管理 ------------------------------------------------------
    def add_plugin(self, name: str, enabled: bool = True, hooks: list = None) -> str:
        """添加或更新插件。"""
        if not name:
            raise ValueError(error_message("E001"))
        self.plugins[name] = Plugin(name, enabled, hooks)
        return name

    def set_plugin_enabled(self, name: str, enabled: bool) -> bool:
        """启用/停用插件。"""
        if name not in self.plugins:
            raise KeyError(error_message("E006"))
        self.plugins[name].enabled = bool(enabled)
        return True

    def remove_plugin(self, name: str) -> bool:
        """移除插件。"""
        if name in self.plugins:
            del self.plugins[name]
            return True
        return False

    def list_plugins(self) -> list:
        """列出所有插件。"""
        return [p.to_dict() for p in self.plugins.values()]

    # ---- 钩子管理 ------------------------------------------------------
    def register_hook(self, plugin_name: str, event: str, callback: str = "") -> bool:
        """为插件注册钩子事件。"""
        if plugin_name not in self.plugins:
            raise KeyError(error_message("E007"))
        if not event:
            raise ValueError(error_message("E001"))
        hook_entry = {"event": event, "callback": callback}
        if hook_entry not in self.plugins[plugin_name].hooks:
            self.plugins[plugin_name].hooks.append(hook_entry)
        return True

    def remove_hook(self, plugin_name: str, event: str) -> bool:
        """移除插件的钩子事件。"""
        if plugin_name not in self.plugins:
            raise KeyError(error_message("E007"))
        before = len(self.plugins[plugin_name].hooks)
        self.plugins[plugin_name].hooks = [
            h for h in self.plugins[plugin_name].hooks if h.get("event") != event
        ]
        return len(self.plugins[plugin_name].hooks) < before

    # ---- 配置管理 ------------------------------------------------------
    def set_config(self, key: str, value, source: str = "manual") -> str:
        """设置配置项，并保存备份以便回滚。"""
        if not key:
            raise ValueError(error_message("E001"))
        # 记录旧值用于回滚
        old_value = self.configs[key].value if key in self.configs else None
        self.config_backups.append((key, old_value))
        self.configs[key] = ConfigEntry(key, value, source)
        return key

    def get_config(self, key: str):
        """获取配置值。不存在时返回 None。"""
        if key in self.configs:
            return self.configs[key].value
        return None

    def rollback_config(self) -> bool:
        """回滚最近一次配置变更。"""
        if not self.config_backups:
            return False
        key, old_value = self.config_backups.pop()
        if old_value is None:
            # 原来不存在则删除
            self.configs.pop(key, None)
        else:
            self.configs[key] = ConfigEntry(key, old_value, "rollback")
        return True

    def list_configs(self) -> list:
        """列出所有配置。"""
        return [c.to_dict() for c in self.configs.values()]

    # ---- 记忆管理 ------------------------------------------------------
    def add_memory(self, content: str, category: str = "general", tags: list = None) -> int:
        """添加记忆条目。返回条目索引。"""
        if not content:
            raise ValueError(error_message("E001"))
        self.memories.append(MemoryItem(content, category, tags))
        return len(self.memories) - 1

    def list_memories(self, category: str = None) -> list:
        """列出记忆条目，可按类别过滤。"""
        items = self.memories
        if category:
            items = [m for m in items if m.category == category]
        return [m.to_dict() for m in items]

    def remove_memory(self, index: int) -> bool:
        """移除指定索引的记忆条目。"""
        if 0 <= index < len(self.memories):
            del self.memories[index]
            return True
        return False

    # ---- 导入导出（JSON 序列化） --------------------------------------
    def export_json(self) -> str:
        """将全部状态导出为 JSON 字符串。"""
        data = {
            "skills": self.list_skills(),
            "mcp_servers": self.list_mcp(),
            "plugins": self.list_plugins(),
            "configs": self.list_configs(),
            "memories": self.list_memories(),
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def import_json(self, json_str: str) -> bool:
        """从 JSON 字符串导入状态。"""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError(error_message("E003"))

        # 清空现有状态
        self.skills = {}
        self.mcp_servers = {}
        self.plugins = {}
        self.configs = {}
        self.memories = []

        # 导入技能
        for s in data.get("skills", []):
            self.add_skill(s.get("name", ""), s.get("version", ""), s.get("description", ""))

        # 导入 MCP
        for m in data.get("mcp_servers", []):
            self.add_mcp(m.get("name", ""), m.get("url", ""), m.get("protocol", "http"), m.get("auth_type", "none"))

        # 导入插件
        for p in data.get("plugins", []):
            self.add_plugin(p.get("name", ""), p.get("enabled", True), p.get("hooks", []))

        # 导入配置
        for c in data.get("configs", []):
            self.set_config(c.get("key", ""), c.get("value"), c.get("source", "imported"))

        # 导入记忆
        for m in data.get("memories", []):
            self.add_memory(m.get("content", ""), m.get("category", "general"), m.get("tags", []))

        return True


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """离线自检核心逻辑。使用硬编码样例数据，不依赖外部环境。"""
    print("harnesskit 自检开始...", flush=True)

    try:
        # 创建管理器实例
        kit = HarnessKit()

        # ---- 技能管理自检 ----
        print("  测试技能管理...", flush=True)
        kit.add_skill("code-reviewer", "1.2.0", "代码审查技能")
        kit.add_skill("test-generator", "0.9.1", "测试用例生成")
        skills = kit.list_skills()
        assert len(skills) >= 2, "技能数量应至少为2"
        assert any(s["name"] == "code-reviewer" for s in skills), "应包含 code-reviewer"
        assert any(s["name"] == "test-generator" for s in skills), "应包含 test-generator"

        # 获取单个技能
        skill = kit.get_skill("code-reviewer")
        assert skill["version"] is not None, "版本号不应为空"

        # 移除技能
        assert kit.remove_skill("test-generator") is True, "移除技能应成功"
        assert kit.remove_skill("nonexistent") is False, "移除不存在的技能应返回False"
        print("  技能管理测试通过", flush=True)

        # ---- MCP 管理自检 ----
        print("  测试 MCP 管理...", flush=True)
        kit.add_mcp("github", "https://api.github.com", "https", "token")
        kit.add_mcp("local-db", "localhost:5432", "stdio", "none")
        mcp_list = kit.list_mcp()
        assert len(mcp_list) >= 2, "MCP服务器数量应至少为2"
        assert any(m["name"] == "github" for m in mcp_list), "应包含 github MCP"
        assert any(m["name"] == "local-db" for m in mcp_list), "应包含 local-db MCP"

        # 移除 MCP
        assert kit.remove_mcp("local-db") is True, "移除MCP应成功"
        print("  MCP 管理测试通过", flush=True)

        # ---- 插件与钩子管理自检 ----
        print("  测试插件与钩子管理...", flush=True)
        kit.add_plugin("formatter", True, [])
        kit.add_plugin("linter", False, [])
        kit.register_hook("formatter", "before_save", "format_file")
        kit.register_hook("formatter", "after_save", "validate")

        plugins = kit.list_plugins()
        assert len(plugins) >= 2, "插件数量应至少为2"
        formatter = [p for p in plugins if p["name"] == "formatter"][0]
        assert len(formatter["hooks"]) >= 2, "formatter 应有至少2个钩子"

        # 启用/停用
        assert kit.set_plugin_enabled("linter", True) is True, "启用插件应成功"
        linter = [p for p in kit.list_plugins() if p["name"] == "linter"][0]
        assert linter["enabled"] is True, "linter 应已启用"

        # 移除钩子
        assert kit.remove_hook("formatter", "after_save") is True, "移除钩子应成功"
        print("  插件与钩子管理测试通过", flush=True)

        # ---- 配置管理自检 ----
        print("  测试配置管理...", flush=True)
        kit.set_config("theme", "dark")
        kit.set_config("font_size", 14)
        kit.set_config("auto_save", True)

        configs = kit.list_configs()
        assert len(configs) >= 3, "配置项数量应至少为3"
        assert kit.get_config("theme") == "dark", "主题配置应为 dark"

        # 回滚
        assert kit.rollback_config() is True, "回滚应成功"
        assert kit.get_config("auto_save") is None, "回滚后 auto_save 应不存在"
        print("  配置管理测试通过", flush=True)

        # ---- 记忆管理自检 ----
        print("  测试记忆管理...", flush=True)
        kit.add_memory("用户偏好使用 Python", "preference", ["python", "language"])
        kit.add_memory("项目使用 FastAPI", "project", ["backend"])
        kit.add_memory("遵循 PEP8", "rule", ["style"])

        memories = kit.list_memories()
        assert len(memories) >= 3, "记忆条目应至少为3"

        pref = kit.list_memories(category="preference")
        assert len(pref) >= 1, "偏好类记忆应至少1条"

        # 移除记忆
        assert kit.remove_memory(0) is True, "移除记忆应成功"
        assert len(kit.list_memories()) >= 2, "移除后记忆应至少2条"
        print("  记忆管理测试通过", flush=True)

        # ---- 导入导出自检 ----
        print("  测试导入导出...", flush=True)
        kit.add_skill("export-test", "1.0.0", "导出测试")
        exported = kit.export_json()
        assert exported is not None and len(exported) > 0, "导出 JSON 不应为空"

        # 导入到新实例
        kit2 = HarnessKit()
        assert kit2.import_json(exported) is True, "导入应成功"
        assert len(kit2.list_skills()) >= 3, "导入后技能数量应至少为3"
        assert len(kit2.list_mcp()) >= 1, "导入后 MCP 数量应至少为1"
        assert len(kit2.list_plugins()) >= 2, "导入后插件数量应至少为2"
        print("  导入导出测试通过", flush=True)

        # ---- 错误处理自检 ----
        print("  测试错误处理...", flush=True)
        try:
            kit.add_skill("", "1.0.0")
            assert False, "空名称应抛出异常"
        except ValueError:
            pass  # 预期行为

        try:
            kit.get_skill("not-exist")
            assert False, "不存在的技能应抛出异常"
        except KeyError:
            pass  # 预期行为
        print("  错误处理测试通过", flush=True)

        print("harnesskit 自检通过 ✓", flush=True)
        return 0

    except Exception as e:
        print(f"\n自检失败: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return 1


def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="harnesskit — 工具链装配与技能管理助手",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不访问网络/文件）",
    )
    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="列出所有技能",
    )
    parser.add_argument(
        "--add-skill",
        nargs=2,
        metavar=("NAME", "VERSION"),
        help="添加技能",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="导出当前状态为 JSON",
    )
    parser.add_argument(
        "--import-file",
        metavar="FILE",
        help="从 JSON 文件导入状态",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式
    kit = HarnessKit()

    try:
        if args.add_skill:
            name, version = args.add_skill
            kit.add_skill(name, version)
            print(f"技能已添加: {name} v{version}")

        if args.list_skills or args.add_skill:
            skills = kit.list_skills()
            if not skills:
                print("暂无技能")
            for s in skills:
                print(f"  - {s['name']} v{s['version']}: {s['description']}")

        if args.export:
            print(kit.export_json())

        if args.import_file:
            path = Path(args.import_file)
            if not path.exists():
                print(error_message("E002"), file=sys.stderr)
                return 2
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            kit.import_json(content)
            print(f"已从 {args.import_file} 导入状态")

        # 无参数时显示帮助
        if len(sys.argv) == 1:
            parser.print_help()

    except (ValueError, KeyError, OSError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{error_message('E010')}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
