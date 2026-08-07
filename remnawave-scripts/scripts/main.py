#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RemnaWave 部署配置与数据转换工具集

功能：
- 部署辅助：生成部署脚本骨架、校验部署前置条件
- 配置管理：读取/修改 RemnaWave 配置文件、参数校验
- 数据转换：将外部数据格式（JSON/CSV/YAML）转换为 RemnaWave 所需结构

仅依赖标准库，无第三方依赖。
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件不存在",
    "E003": "文件格式不支持",
    "E004": "JSON 解析失败",
    "E005": "CSV 解析失败",
    "E006": "YAML 解析失败（需安装 PyYAML）",
    "E007": "配置校验失败",
    "E008": "目录创建失败",
    "E009": "数据转换失败",
    "E010": "内部逻辑错误",
}


def error_exit(code: str, message: str = "") -> None:
    """输出错误信息并退出"""
    desc = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"错误 [{code}] {desc}: {message}", file=sys.stderr)
    else:
        print(f"错误 [{code}] {desc}", file=sys.stderr)
    sys.exit(1)


# ==================== 部署辅助模块 ====================

def generate_deploy_script(service_name: str, port: int, data_dir: str) -> str:
    """
    生成部署脚本骨架（Bash）

    参数：
        service_name: 服务名称
        port: 服务端口
        data_dir: 数据存储目录

    返回：
        部署脚本内容
    """
    if not service_name or not re.match(r"^[a-zA-Z0-9_-]+$", service_name):
        error_exit("E001", f"服务名称不合法: {service_name}")
    if not isinstance(port, int) or port < 1 or port > 65535:
        error_exit("E001", f"端口号不合法: {port}")

    script = f"""#!/bin/bash
# RemnaWave 服务部署脚本（自动生成）
# 服务名称: {service_name}
# 服务端口: {port}
# 数据目录: {data_dir}

set -euo pipefail

echo "=== 部署前置检查 ==="
# 检查必要工具
for cmd in docker curl; do
    if ! command -v $cmd &>/dev/null; then
        echo "错误: 缺少必要工具 $cmd"
        exit 1
    fi
done

# 检查端口占用
if ss -tlnp 2>/dev/null | grep -q ":{port} "; then
    echo "警告: 端口 {port} 已被占用"
fi

echo "=== 创建数据目录 ==="
mkdir -p "{data_dir}"

echo "=== 启动服务 ==="
# TODO: 在此处添加实际的服务启动命令
# 示例: docker run -d --name {service_name} -p {port}:{port} -v {data_dir}:/data remnawave/{service_name}

echo "=== 部署完成 ==="
echo "服务 {service_name} 已就绪，端口 {port}，数据目录 {data_dir}"
"""
    return script


def check_deploy_prerequisites(required_tools: list, required_dirs: list) -> dict:
    """
    校验部署前置条件

    参数：
        required_tools: 必需的命令行工具列表
        required_dirs: 必需的目录列表

    返回：
        校验结果字典
    """
    results = {
        "tools": {},
        "dirs": {},
        "all_passed": True,
    }

    # 检查工具 - 使用 shutil.which 进行检测
    for tool in required_tools:
        found = shutil.which(tool) is not None
        results["tools"][tool] = found
        if not found:
            results["all_passed"] = False

    # 检查目录
    for dir_path in required_dirs:
        exists = os.path.isdir(dir_path)
        writable = exists and os.access(dir_path, os.W_OK)
        results["dirs"][dir_path] = {"exists": exists, "writable": writable}
        if not (exists and writable):
            results["all_passed"] = False

    return results


# ==================== 配置管理模块 ====================

def validate_remnawave_config(config: dict) -> list:
    """
    校验 RemnaWave 配置参数

    参数：
        config: 配置字典

    返回：
        错误信息列表（空列表表示校验通过）
    """
    errors = []

    # 校验 server 配置
    server = config.get("server", {})
    if not isinstance(server, dict):
        errors.append("server 必须是对象")
    else:
        # 端口校验
        port = server.get("port", 8080)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append(f"端口不合法: {port}")

        # 日志级别校验
        log_level = server.get("log_level", "info")
        valid_levels = ["debug", "info", "warn", "error"]
        if log_level not in valid_levels:
            errors.append(f"日志级别不合法: {log_level}，可选值: {', '.join(valid_levels)}")

    # 校验 storage 配置
    storage = config.get("storage", {})
    if not isinstance(storage, dict):
        errors.append("storage 必须是对象")
    else:
        # 存储路径校验
        path = storage.get("path", "/data/remnawave")
        if not isinstance(path, str) or not path.strip():
            errors.append("存储路径不能为空")

        # 存储类型校验
        stype = storage.get("type", "local")
        valid_types = ["local", "nfs", "s3"]
        if stype not in valid_types:
            errors.append(f"存储类型不合法: {stype}")

    # 校验 features 配置
    features = config.get("features", {})
    if not isinstance(features, dict):
        errors.append("features 必须是对象")
    else:
        # 布尔值校验
        for key, value in features.items():
            if not isinstance(value, bool):
                errors.append(f"功能开关 {key} 必须是布尔值")

    return errors


def load_config_file(file_path: str) -> dict:
    """
    读取配置文件（支持 JSON/CSV/YAML）

    参数：
        file_path: 配置文件路径

    返回：
        配置字典
    """
    if not os.path.isfile(file_path):
        error_exit("E002", f"文件不存在: {file_path}")

    suffix = Path(file_path).suffix.lower()
    try:
        if suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                error_exit("E004", "JSON 根节点必须是对象")
            return data
        elif suffix == ".csv":
            # CSV 转配置：第一列为键，第二列为值
            config = {}
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        key = row[0].strip()
                        value = row[1].strip()
                        # 尝试转换类型
                        if value.lower() == "true":
                            config[key] = True
                        elif value.lower() == "false":
                            config[key] = False
                        elif value.isdigit():
                            config[key] = int(value)
                        else:
                            config[key] = value
            return config
        elif suffix in (".yaml", ".yml"):
            # 尝试导入 PyYAML
            try:
                import yaml  # pip install pyyaml
            except ImportError:
                error_exit("E006", "解析 YAML 需要安装 PyYAML: pip install pyyaml")
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                error_exit("E006", "YAML 根节点必须是对象")
            return data
        else:
            error_exit("E003", f"不支持的文件格式: {suffix}")
    except json.JSONDecodeError as e:
        error_exit("E004", f"JSON 解析错误: {e}")
    except csv.Error as e:
        error_exit("E005", f"CSV 解析错误: {e}")
    except Exception as e:
        error_exit("E010", f"读取文件异常: {e}")


def modify_config_value(config: dict, key_path: str, new_value) -> dict:
    """
    修改配置值（支持点号路径）

    参数：
        config: 配置字典（会被修改）
        key_path: 键路径，如 "server.port"
        new_value: 新值

    返回：
        修改后的配置字典
    """
    keys = key_path.split(".")
    current = config

    # 遍历到父节点
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    # 设置值
    current[keys[-1]] = new_value
    return config


# ==================== 数据转换模块 ====================

def convert_to_remnawave_format(data: list, source_type: str) -> dict:
    """
    将外部数据转换为 RemnaWave 所需结构

    参数：
        data: 源数据列表
        source_type: 源数据类型（"users", "configs", "nodes"）

    返回：
        RemnaWave 格式的数据字典
    """
    result = {"version": "1.0", "type": source_type, "items": []}

    try:
        if source_type == "users":
            # 用户数据转换
            for item in data:
                user = {
                    "id": item.get("id") or item.get("user_id") or item.get("uid", ""),
                    "username": item.get("username") or item.get("name") or item.get("user", ""),
                    "email": item.get("email", ""),
                    "status": item.get("status", "active"),
                    "created_at": item.get("created_at") or item.get("create_time", ""),
                    "metadata": item.get("metadata", {}),
                }
                if user["username"]:
                    result["items"].append(user)
        elif source_type == "configs":
            # 配置数据转换
            for item in data:
                config_item = {
                    "key": item.get("key") or item.get("name") or item.get("config_key", ""),
                    "value": item.get("value") or item.get("data", ""),
                    "type": item.get("type", "string"),
                    "description": item.get("description", ""),
                }
                if config_item["key"]:
                    result["items"].append(config_item)
        elif source_type == "nodes":
            # 节点数据转换
            for item in data:
                node = {
                    "hostname": item.get("hostname") or item.get("host") or item.get("name", ""),
                    "ip": item.get("ip") or item.get("ip_address", ""),
                    "port": int(item.get("port", 8080)),
                    "role": item.get("role", "worker"),
                    "tags": item.get("tags", []),
                }
                if node["hostname"]:
                    result["items"].append(node)
        else:
            error_exit("E001", f"不支持的数据类型: {source_type}")

        return result
    except (KeyError, TypeError, ValueError) as e:
        error_exit("E009", f"数据转换失败: {e}")
        return {}  # 不可达，仅为类型检查


def convert_file(input_path: str, output_path: str, source_type: str) -> dict:
    """
    转换文件数据

    参数：
        input_path: 输入文件路径
        output_path: 输出文件路径
        source_type: 数据类型

    返回：
        转换结果摘要
    """
    if not os.path.isfile(input_path):
        error_exit("E002", f"输入文件不存在: {input_path}")

    suffix = Path(input_path).suffix.lower()
    try:
        if suffix == ".json":
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # 如果是单个对象，包装为列表
                data = [data]
        elif suffix == ".csv":
            with open(input_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                data = [row for row in reader]
        else:
            error_exit("E003", f"不支持的文件格式: {suffix}")

        result = convert_to_remnawave_format(data, source_type)

        # 写入输出
        output_suffix = Path(output_path).suffix.lower()
        if output_suffix == ".json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        elif output_suffix == ".csv":
            # 将转换结果写为 CSV
            items = result.get("items", [])
            if items:
                # 获取所有键的并集
                all_keys = set()
                for item in items:
                    all_keys.update(item.keys())
                with open(output_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                    writer.writeheader()
                    writer.writerows(items)
        else:
            error_exit("E003", f"不支持的输出格式: {output_suffix}")

        return {"input": input_path, "output": output_path, "count": len(result["items"])}
    except json.JSONDecodeError as e:
        error_exit("E004", f"JSON 解析错误: {e}")
    except csv.Error as e:
        error_exit("E005", f"CSV 解析错误: {e}")
    except Exception as e:
        error_exit("E010", f"转换过程异常: {e}")
        return {}  # 不可达


# ==================== 自检模块 ====================

def selftest() -> bool:
    """
    内置自检函数：验证核心逻辑

    使用硬编码样例数据，不依赖外部文件、网络或当前目录。

    返回：
        自检是否通过
    """
    print("=== RemnaWave 脚本工具集自检开始 ===")
    all_passed = True

    # --- 测试 1: 部署脚本生成 ---
    print("\n[测试 1] 部署脚本生成")
    try:
        script = generate_deploy_script("test-service", 8080, "/tmp/remnawave-test")
        # 宽松断言：包含关键内容
        assert "test-service" in script, "脚本应包含服务名称"
        assert "8080" in script, "脚本应包含端口"
        assert "/tmp/remnawave-test" in script, "脚本应包含数据目录"
        assert "#!/bin/bash" in script, "脚本应为 Bash 脚本"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # --- 测试 2: 部署前置条件检查 ---
    print("\n[测试 2] 部署前置条件检查")
    try:
        # 使用当前环境中的工具
        available_tools = [t for t in ["python3", "sh", "ls"] if shutil.which(t)]
        unavailable_tools = ["definitely-not-exist-tool-xyz"]
        result = check_deploy_prerequisites(available_tools + unavailable_tools, [])
        # 宽松断言：存在的工具应被检测到，不存在的应被标记
        for tool in available_tools:
            assert result["tools"].get(tool) is True, f"工具 {tool} 应被检测到"
        assert result["tools"].get("definitely-not-exist-tool-xyz") is False, "不存在的工具应被标记"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # --- 测试 3: 配置校验 ---
    print("\n[测试 3] 配置校验")
    try:
        # 有效配置
        valid_config = {
            "server": {"port": 8080, "log_level": "info"},
            "storage": {"path": "/data", "type": "local"},
            "features": {"enable_api": True, "enable_ui": False},
        }
        errors = validate_remnawave_config(valid_config)
        assert len(errors) == 0, f"有效配置不应有错误: {errors}"

        # 无效配置
        invalid_config = {
            "server": {"port": 99999, "log_level": "invalid"},
            "storage": {"path": "", "type": "unknown"},
            "features": {"enable_api": "yes"},
        }
        errors = validate_remnawave_config(invalid_config)
        assert len(errors) >= 4, f"无效配置应至少 4 个错误，实际: {len(errors)}"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # --- 测试 4: 配置修改 ---
    print("\n[测试 4] 配置修改")
    try:
        config = {"server": {"port": 8080}}
        modify_config_value(config, "server.port", 9090)
        modify_config_value(config, "server.host", "0.0.0.0")
        modify_config_value(config, "new_section.enabled", True)
        assert config["server"]["port"] == 9090, "端口应被修改"
        assert config["server"]["host"] == "0.0.0.0", "host 应被添加"
        assert config["new_section"]["enabled"] is True, "新节点应被创建"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # --- 测试 5: 数据转换 ---
    print("\n[测试 5] 数据转换")
    try:
        # 用户数据转换
        users = [
            {"id": "u1", "name": "张三", "email": "zhangsan@example.com"},
            {"id": "u2", "name": "李四", "email": "lisi@example.com"},
        ]
        result = convert_to_remnawave_format(users, "users")
        assert len(result["items"]) == 2, "应转换 2 个用户"
        assert result["items"][0]["username"] == "张三", "用户名应为张三"
        assert result["type"] == "users", "类型应为 users"

        # 节点数据转换
        nodes = [
            {"hostname": "node1", "ip": "10.0.0.1", "port": "8080"},
            {"hostname": "node2", "ip": "10.0.0.2", "port": "9090"},
        ]
        result = convert_to_remnawave_format(nodes, "nodes")
        assert len(result["items"]) == 2, "应转换 2 个节点"
        assert result["items"][0]["port"] == 8080, "端口应为整数 8080"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # --- 测试 6: 文件转换（使用临时目录） ---
    print("\n[测试 6] 文件转换")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建临时 JSON 输入文件
            input_file = os.path.join(tmpdir, "input.json")
            output_file = os.path.join(tmpdir, "output.json")
            test_data = [
                {"id": "1", "name": "测试用户", "email": "test@example.com"},
                {"id": "2", "name": "测试用户2", "email": "test2@example.com"},
            ]
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            # 执行转换
            result = convert_file(input_file, output_file, "users")
            assert result["count"] == 2, f"应转换 2 条记录，实际: {result['count']}"
            assert os.path.isfile(output_file), "输出文件应存在"

            # 验证输出内容
            with open(output_file, "r", encoding="utf-8") as f:
                output_data = json.load(f)
            assert output_data["type"] == "users", "输出类型应为 users"
            assert len(output_data["items"]) == 2, "输出应包含 2 条记录"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # --- 测试 7: 错误处理 ---
    print("\n[测试 7] 错误处理")
    try:
        # 不存在的文件
        try:
            load_config_file("/path/to/nonexistent/file.json")
            assert False, "应抛出文件不存在错误"
        except SystemExit as e:
            assert e.code == 1, "退出码应为 1"

        # 无效配置
        invalid = {"server": {"port": -1}}
        errors = validate_remnawave_config(invalid)
        assert len(errors) > 0, "应返回错误"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # --- 总结 ---
    print("\n=== 自检结束 ===")
    if all_passed:
        print("✓ 全部测试通过")
        return True
    else:
        print("✗ 存在失败的测试")
        return False


# ==================== 主程序 ====================

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="RemnaWave 部署配置与数据转换工具集",
        epilog="示例: python main.py --generate-deploy-script --service myapp --port 8080 --data-dir /data"
    )

    # 子命令或功能选项
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--generate-deploy-script", action="store_true", help="生成部署脚本")
    parser.add_argument("--check-prerequisites", action="store_true", help="检查部署前置条件")
    parser.add_argument("--validate-config", action="store_true", help="校验配置文件")
    parser.add_argument("--modify-config", action="store_true", help="修改配置值")
    parser.add_argument("--convert-file", action="store_true", help="转换数据文件")

    # 参数
    parser.add_argument("--service", type=str, default="remnawave", help="服务名称")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("--data-dir", type=str, default="/data/remnawave", help="数据目录")
    parser.add_argument("--config-file", type=str, help="配置文件路径")
    parser.add_argument("--key", type=str, help="配置键路径（点号分隔）")
    parser.add_argument("--value", type=str, help="配置新值")
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--type", type=str, choices=["users", "configs", "nodes"], help="数据类型")
    parser.add_argument("--tools", type=str, help="必需工具列表（逗号分隔）")
    parser.add_argument("--dirs", type=str, help="必需目录列表（逗号分隔）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        sys.exit(0 if success else 1)

    # 功能分发
    if args.generate_deploy_script:
        script = generate_deploy_script(args.service, args.port, args.data_dir)
        print(script)

    elif args.check_prerequisites:
        tools = [t.strip() for t in args.tools.split(",") if t.strip()] if args.tools else []
        dirs = [d.strip() for d in args.dirs.split(",") if d.strip()] if args.dirs else []
        result = check_deploy_prerequisites(tools, dirs)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["all_passed"]:
            sys.exit(1)

    elif args.validate_config:
        if not args.config_file:
            error_exit("E001", "校验配置需要 --config-file 参数")
        config = load_config_file(args.config_file)
        errors = validate_remnawave_config(config)
        if errors:
            print("配置校验失败:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print("配置校验通过")

    elif args.modify_config:
        if not args.config_file or not args.key or args.value is None:
            error_exit("E001", "修改配置需要 --config-file、--key、--value 参数")
        config = load_config_file(args.config_file)
        # 尝试转换值类型
        value = args.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)
        modify_config_value(config, args.key, value)
        # 写回
        with open(args.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"已修改 {args.key} = {value}")

    elif args.convert_file:
        if not args.input or not args.output or not args.type:
            error_exit("E001", "转换文件需要 --input、--output、--type 参数")
        result = convert_file(args.input, args.output, args.type)
        print(f"转换完成: {result['count']} 条记录")

    else:
        # 无参数时显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()
