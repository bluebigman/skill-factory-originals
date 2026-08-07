#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
remnawave-scripts 工具集 - 独立实现脚本
版本: 1.0.1 (clean-room 重写)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class ErrorCode:
    """统一错误码常量"""
    E001 = "E001"  # 参数无效
    E002 = "E002"  # 文件不存在
    E003 = "E003"  # JSON 解析失败
    E004 = "E004"  # 配置校验失败
    E005 = "E005"  # 目录创建失败
    E006 = "E006"  # 文件写入失败
    E007 = "E007"  # 数据转换失败
    E008 = "E008"  # 模板渲染失败
    E009 = "E009"  # 自检失败
    E010 = "E010"  # 未知错误


class ScriptError(Exception):
    """带错误码的异常"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ============================================================
# 核心工具函数
# ============================================================

def safe_read_json(file_path: str) -> Dict[str, Any]:
    """安全读取 JSON 文件（E002/E003）"""
    if not os.path.isfile(file_path):
        raise ScriptError(ErrorCode.E002, f"文件不存在: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ScriptError(ErrorCode.E003, f"JSON 解析失败: {e}") from e
    except OSError as e:
        raise ScriptError(ErrorCode.E003, f"读取文件失败: {e}") from e


def safe_write_json(file_path: str, data: Any) -> None:
    """安全写入 JSON 文件（E006）"""
    try:
        parent = os.path.dirname(os.path.abspath(file_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise ScriptError(ErrorCode.E006, f"写入文件失败: {e}") from e


def generate_node_id(prefix: str = "node") -> str:
    """生成节点 ID（基于时间戳+随机数）"""
    import random
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = random.randint(1000, 9999)
    return f"{prefix}-{ts}-{rand}"


def parse_duration(duration_str: str) -> int:
    """解析时长字符串为秒（支持 s/m/h/d）"""
    if not isinstance(duration_str, str):
        raise ScriptError(ErrorCode.E001, "时长必须是字符串")
    match = re.match(r"^(\d+)([smhd])$", duration_str.strip().lower())
    if not match:
        raise ScriptError(ErrorCode.E001, f"无效时长格式: {duration_str}")
    value = int(match.group(1))
    unit = match.group(2)
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return value * multiplier[unit]


def validate_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    """验证配置结构（E004）"""
    required_keys = ["name", "version", "nodes"]
    for key in required_keys:
        if key not in config:
            return False, f"缺少必需键: {key}"
    if not isinstance(config["name"], str) or not config["name"].strip():
        return False, "name 必须是非空字符串"
    if not isinstance(config["version"], str):
        return False, "version 必须是字符串"
    if not isinstance(config["nodes"], list) or len(config["nodes"]) == 0:
        return False, "nodes 必须是非空列表"
    return True, "OK"


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """规范化配置，填充默认值"""
    normalized = dict(config)
    normalized.setdefault("description", "")
    normalized.setdefault("enabled", True)
    normalized.setdefault("created_at", datetime.now().isoformat())
    normalized.setdefault("settings", {})
    
    # 规范化节点
    new_nodes = []
    for idx, node in enumerate(config.get("nodes", [])):
        new_node = dict(node)
        new_node.setdefault("id", generate_node_id(f"node{idx}"))
        new_node.setdefault("enabled", True)
        new_node.setdefault("weight", 1)
        new_node.setdefault("tags", [])
        new_nodes.append(new_node)
    normalized["nodes"] = new_nodes
    return normalized


def convert_format(data: Any, target_format: str) -> str:
    """数据格式转换（E007）"""
    target = target_format.lower().strip()
    if target == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif target == "yaml":
        # 简易 YAML 生成（仅支持 dict/list/基本类型）
        return _to_yaml(data, 0)
    elif target == "env":
        if not isinstance(data, dict):
            raise ScriptError(ErrorCode.E007, "env 格式仅支持字典数据")
        lines = []
        for key, value in data.items():
            lines.append(f"{key}={value}")
        return "\n".join(lines)
    else:
        raise ScriptError(ErrorCode.E007, f"不支持的目标格式: {target_format}")


def _to_yaml(data: Any, indent: int = 0) -> str:
    """递归生成简易 YAML"""
    prefix = " " * indent
    lines = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_to_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_format_scalar(value)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_to_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
    else:
        lines.append(f"{prefix}{_format_scalar(data)}")
    return "\n".join(lines)


def _format_scalar(value: Any) -> str:
    """格式化标量值"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    if isinstance(value, str):
        # 简单判断是否需要引号
        if any(c in value for c in ":#{}[],&*!|>'\"%@`"):
            return f'"{value}"'
        return value
    return str(value)


def render_template(template_str: str, context: Dict[str, Any]) -> str:
    """简易模板渲染，支持 {{ variable }} 语法（E008）"""
    def replace_match(match):
        var_name = match.group(1).strip()
        if var_name not in context:
            raise ScriptError(ErrorCode.E008, f"模板变量未定义: {var_name}")
        return str(context[var_name])
    
    try:
        pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
        return re.sub(pattern, replace_match, template_str)
    except re.error as e:
        raise ScriptError(ErrorCode.E008, f"模板正则错误: {e}") from e


def deploy_plan(config: Dict[str, Any]) -> Dict[str, Any]:
    """生成部署计划（核心业务逻辑）"""
    valid, msg = validate_config(config)
    if not valid:
        raise ScriptError(ErrorCode.E004, msg)
    
    normalized = normalize_config(config)
    plan = {
        "plan_id": generate_node_id("plan"),
        "name": normalized["name"],
        "version": normalized["version"],
        "generated_at": datetime.now().isoformat(),
        "total_nodes": len(normalized["nodes"]),
        "enabled_nodes": sum(1 for n in normalized["nodes"] if n.get("enabled", True)),
        "estimated_minutes": 0,
        "steps": [],
    }
    
    # 计算预估时间（宽松估算）
    base_time = 5  # 基础 5 分钟
    per_node_time = 3  # 每节点 3 分钟
    plan["estimated_minutes"] = base_time + per_node_time * plan["total_nodes"]
    
    # 生成步骤
    for idx, node in enumerate(normalized["nodes"]):
        step = {
            "step": idx + 1,
            "node_id": node["id"],
            "action": "deploy" if node.get("enabled", True) else "skip",
            "description": f"部署节点 {node.get('name', node['id'])}",
        }
        plan["steps"].append(step)
    
    return plan


def export_summary(data: Dict[str, Any], output_dir: str = ".") -> str:
    """导出摘要文件（E005/E006）"""
    try:
        out_path = os.path.join(output_dir, f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        safe_write_json(out_path, data)
        return out_path
    except ScriptError:
        raise
    except Exception as e:
        raise ScriptError(ErrorCode.E010, f"导出摘要失败: {e}") from e


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """内置自检，不依赖外部文件/网络"""
    print("=" * 60)
    print("开始自检 (selftest)...")
    failures = []
    
    # --- 测试 1: 配置校验 ---
    print("[TEST 1] 配置校验")
    try:
        valid_config = {
            "name": "test-cluster",
            "version": "1.0.0",
            "nodes": [
                {"id": "n1", "name": "node-a", "enabled": True},
                {"id": "n2", "name": "node-b", "enabled": False},
            ]
        }
        ok, msg = validate_config(valid_config)
        assert ok, f"有效配置被拒绝: {msg}"
        
        bad_config = {"name": "x", "version": "1.0"}  # 缺少 nodes
        ok, _ = validate_config(bad_config)
        assert not ok, "无效配置未被拒绝"
        print("  PASS")
    except AssertionError as e:
        failures.append(f"TEST 1: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 2: 时长解析 ---
    print("[TEST 2] 时长解析")
    try:
        assert parse_duration("30s") == 30
        assert parse_duration("5m") == 300
        assert parse_duration("2h") == 7200
        assert parse_duration("1d") == 86400
        # 宽松验证：所有解析结果都应大于 0
        for s in ["10s", "1m", "1h", "1d"]:
            assert parse_duration(s) > 0, f"解析结果应为正数: {s}"
        print("  PASS")
    except (AssertionError, ScriptError) as e:
        failures.append(f"TEST 2: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 3: 配置规范化 ---
    print("[TEST 3] 配置规范化")
    try:
        raw_config = {
            "name": "cluster",
            "version": "2.0",
            "nodes": [{"name": "n1"}],  # 缺 id/enabled/weight
        }
        normalized = normalize_config(raw_config)
        assert len(normalized["nodes"]) == 1, "节点数量应保持"
        node = normalized["nodes"][0]
        assert node["id"], "应自动生成 id"
        assert node["enabled"] is True, "默认 enabled 应为 True"
        assert node["weight"] == 1, "默认 weight 应为 1"
        assert isinstance(node["tags"], list), "tags 应为列表"
        print("  PASS")
    except AssertionError as e:
        failures.append(f"TEST 3: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 4: 数据转换 ---
    print("[TEST 4] 数据转换")
    try:
        sample = {"host": "example.com", "port": 8080, "ssl": True}
        json_out = convert_format(sample, "json")
        assert '"host"' in json_out, "JSON 应包含 host"
        
        env_out = convert_format(sample, "env")
        assert "host=example.com" in env_out, "ENV 格式错误"
        
        yaml_out = convert_format(sample, "yaml")
        assert "host: example.com" in yaml_out, "YAML 格式错误"
        print("  PASS")
    except (AssertionError, ScriptError) as e:
        failures.append(f"TEST 4: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 5: 模板渲染 ---
    print("[TEST 5] 模板渲染")
    try:
        template = "服务 {{ service }} 运行在 {{ host }}:{{ port }}"
        context = {"service": "web", "host": "localhost", "port": 3000}
        result = render_template(template, context)
        assert "web" in result and "localhost" in result and "3000" in result, "渲染结果不完整"
        
        # 缺失变量应报错
        try:
            render_template("{{ missing_var }}", {})
            assert False, "缺失变量应抛出异常"
        except ScriptError:
            pass  # 预期行为
        print("  PASS")
    except AssertionError as e:
        failures.append(f"TEST 5: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 6: 部署计划生成 ---
    print("[TEST 6] 部署计划")
    try:
        config = {
            "name": "prod",
            "version": "3.1.0",
            "nodes": [
                {"id": "n1", "name": "api", "enabled": True},
                {"id": "n2", "name": "worker", "enabled": True},
                {"id": "n3", "name": "db", "enabled": False},
            ]
        }
        plan = deploy_plan(config)
        assert plan["total_nodes"] == 3, "节点总数应为 3"
        assert plan["enabled_nodes"] == 2, "启用节点应为 2"
        assert len(plan["steps"]) == 3, "步骤数应为 3"
        assert plan["estimated_minutes"] > 0, "预估时间应为正数"
        # 宽松断言：步骤中至少有一个 deploy 和一个 skip
        actions = [s["action"] for s in plan["steps"]]
        assert "deploy" in actions and "skip" in actions, "应同时包含 deploy 和 skip"
        print("  PASS")
    except (AssertionError, ScriptError) as e:
        failures.append(f"TEST 6: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 7: 错误处理 ---
    print("[TEST 7] 错误处理")
    try:
        # 不存在的文件
        try:
            safe_read_json("/nonexistent/path/file.json")
            assert False, "应抛出 E002"
        except ScriptError as e:
            assert e.code == ErrorCode.E002, f"错误码应为 E002，实际 {e.code}"
        
        # 无效 JSON
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            tmp_path = f.name
        try:
            safe_read_json(tmp_path)
            assert False, "应抛出 E003"
        except ScriptError as e:
            assert e.code == ErrorCode.E003, f"错误码应为 E003，实际 {e.code}"
        finally:
            os.unlink(tmp_path)
        print("  PASS")
    except (AssertionError, ScriptError) as e:
        failures.append(f"TEST 7: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 8: 节点 ID 生成 ---
    print("[TEST 8] 节点 ID 生成")
    try:
        id1 = generate_node_id("test")
        id2 = generate_node_id("test")
        assert id1 != id2, "两次生成的 ID 不应相同"
        assert id1.startswith("test-"), "ID 应有正确前缀"
        print("  PASS")
    except AssertionError as e:
        failures.append(f"TEST 8: {e}")
        print(f"  FAIL: {e}")
    
    # --- 测试 9: 导出功能 ---
    print("[TEST 9] 导出功能")
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"result": "ok", "count": 42}
            out = export_summary(data, tmpdir)
            assert os.path.isfile(out), "导出文件应存在"
            # 验证内容
            with open(out, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["count"] == 42, "导出内容应正确"
        print("  PASS")
    except (AssertionError, ScriptError) as e:
        failures.append(f"TEST 9: {e}")
        print(f"  FAIL: {e}")
    
    # --- 结果汇总 ---
    print("=" * 60)
    if failures:
        print(f"自检失败: {len(failures)} 项未通过")
        for fail in failures:
            print(f"  - {fail}")
        return 1
    else:
        print("所有自检通过 (9/9)")
        return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="RemnaWave 脚本工具集 (clean-room 实现)",
        epilog="示例: python main.py --selftest"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）"
    )
    parser.add_argument(
        "--validate",
        metavar="CONFIG.json",
        help="验证配置文件"
    )
    parser.add_argument(
        "--plan",
        metavar="CONFIG.json",
        help="生成部署计划"
    )
    parser.add_argument(
        "--convert",
        metavar="INPUT.json",
        help="转换数据格式（需配合 --to 参数）"
    )
    parser.add_argument(
        "--to",
        choices=["json", "yaml", "env"],
        default="json",
        help="转换目标格式"
    )
    parser.add_argument(
        "--render",
        metavar="TEMPLATE",
        help="渲染模板（需配合 --context 参数）"
    )
    parser.add_argument(
        "--context",
        metavar='{"key":"value"}',
        help="模板上下文 JSON"
    )
    parser.add_argument(
        "--export",
        metavar="OUTPUT_DIR",
        help="导出摘要到目录"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细信息"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 无参数时显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    try:
        # 验证配置
        if args.validate:
            config = safe_read_json(args.validate)
            ok, msg = validate_config(config)
            if ok:
                print(f"配置有效: {config['name']} v{config['version']}")
            else:
                print(f"配置无效: {msg}", file=sys.stderr)
                return 1
        
        # 生成部署计划
        if args.plan:
            config = safe_read_json(args.plan)
            plan = deploy_plan(config)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            if args.export:
                out_path = export_summary(plan, args.export)
                print(f"\n摘要已导出: {out_path}", file=sys.stderr)
        
        # 数据转换
        if args.convert:
            data = safe_read_json(args.convert)
            result = convert_format(data, args.to)
            print(result)
        
        # 模板渲染
        if args.render:
            if not args.context:
                raise ScriptError(ErrorCode.E001, "--render 需要 --context 参数")
            try:
                context = json.loads(args.context)
            except json.JSONDecodeError as e:
                raise ScriptError(ErrorCode.E003, f"context JSON 解析失败: {e}") from e
            result = render_template(args.render, context)
            print(result)
        
        return 0
        
    except ScriptError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误 [{ErrorCode.E010}]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
