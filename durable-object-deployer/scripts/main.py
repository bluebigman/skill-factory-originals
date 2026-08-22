#!/usr/bin/env python3
"""Durable Object Deployer - 持久对象部署配置生成、校验与状态监控

功能：
1. 解析 JSON/CSV/键值对格式的输入参数
2. 根据部署模式生成 YAML 配置文件
3. 校验配置语法、存储端点可达性、副本数合法性、CPU/内存配额范围
4. 拉取并解析监控端点指标，输出状态摘要
"""

import argparse
import csv
import json
import os
import re
import socket
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 错误码定义
ERROR_MISSING_FIELD = "E1001"
ERROR_INVALID_FORMAT = "E1002"
ERROR_ENDPOINT_UNREACHABLE = "E3001"
ERROR_CONFIG_NOT_FOUND = "E4001"
WARNING_OUT_OF_RANGE = "W2001"

# 必填字段
REQUIRED_FIELDS = ["instance_name", "region", "replica_count", "storage_endpoint"]

# 可选字段默认值
DEFAULT_VALUES = {
    "deployment_mode": "single",
    "cpu_limit": 1.0,
    "memory_limit": 512,
    "metrics_endpoint": None,
}

# 字段范围
FIELD_RANGES = {
    "replica_count": (1, 9),
    "cpu_limit": (0.1, 64.0),
    "memory_limit": (128, 524288),  # 128MB - 512GB (MB)
}

# 部署模式
DEPLOYMENT_MODES = ["single", "cluster", "edge"]

# 输出模板
TEMPLATE_SINGLE = """config_version: 1.0.0
generated_at: {timestamp}
deployment_mode: single
instance_name: {instance_name}
region: {region}
replica_count: {replica_count}
storage_endpoint: {storage_endpoint}
cpu_limit: {cpu_limit}
memory_limit: {memory_limit}
metrics_endpoint: {metrics_endpoint}
"""

TEMPLATE_CLUSTER = """config_version: 1.0.0
generated_at: {timestamp}
deployment_mode: cluster
instance_name: {instance_name}
region: {region}
replica_count: {replica_count}
storage_endpoint: {storage_endpoint}
cpu_limit: {cpu_limit}
memory_limit: {memory_limit}
metrics_endpoint: {metrics_endpoint}
cluster:
  min_replicas: 3
  max_replicas: 9
  failover_policy: auto
"""

TEMPLATE_EDGE = """config_version: 1.0.0
generated_at: {timestamp}
deployment_mode: edge
instance_name: {instance_name}
region: {region}
replica_count: {replica_count}
storage_endpoint: {storage_endpoint}
cpu_limit: {cpu_limit}
memory_limit: {memory_limit}
metrics_endpoint: {metrics_endpoint}
edge:
  pop_coverage: global
  cache_ttl: 300
"""


def _g1_backoff():
    """G1 退避标记，用于网络重试之间的短暂等待。"""
    time.sleep(0.1)


def parse_json_input(file_path: str) -> Dict[str, Any]:
    """解析 JSON 格式的输入文件。

    Args:
        file_path: 输入文件路径。

    Returns:
        解析后的字典。

    Raises:
        ValueError: 如果文件内容不是有效的 JSON。
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"{ERROR_INVALID_FORMAT}: JSON 解析失败: {e}") from e


def parse_csv_input(file_path: str) -> Dict[str, Any]:
    """解析 CSV 格式的输入文件。

    Args:
        file_path: 输入文件路径。

    Returns:
        解析后的字典。

    Raises:
        ValueError: 如果文件内容不是有效的 CSV。
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                return dict(row)
        return {}
    except Exception as e:
        raise ValueError(f"{ERROR_INVALID_FORMAT}: CSV 解析失败: {e}") from e


def parse_kv_input(file_path: str) -> Dict[str, Any]:
    """解析键值对格式的输入文件。

    Args:
        file_path: 输入文件路径。

    Returns:
        解析后的字典。

    Raises:
        ValueError: 如果文件内容不是有效的键值对。
    """
    result = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    result[key.strip()] = value.strip()
        return result
    except Exception as e:
        raise ValueError(f"{ERROR_INVALID_FORMAT}: 键值对解析失败: {e}") from e


def parse_input(file_path: str, format_hint: Optional[str] = None) -> Dict[str, Any]:
    """根据文件扩展名或格式提示解析输入文件。

    Args:
        file_path: 输入文件路径。
        format_hint: 可选的格式提示（json/csv/kv）。

    Returns:
        解析后的字典。

    Raises:
        ValueError: 如果无法识别文件格式或解析失败。
    """
    suffix = Path(file_path).suffix.lower()
    if format_hint:
        suffix = f".{format_hint.lower()}"

    if suffix == ".json":
        return parse_json_input(file_path)
    elif suffix == ".csv":
        return parse_csv_input(file_path)
    elif suffix in (".txt", ".kv", ".conf"):
        return parse_kv_input(file_path)
    else:
        # 尝试自动检测
        try:
            return parse_json_input(file_path)
        except ValueError:
            try:
                return parse_csv_input(file_path)
            except ValueError:
                return parse_kv_input(file_path)


def validate_required_fields(data: Dict[str, Any]) -> List[str]:
    """检查必填字段是否齐全。

    Args:
        data: 输入数据字典。

    Returns:
        缺失字段列表。
    """
    missing = []
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            missing.append(field)
    return missing


def validate_field_ranges(data: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """检查字段值是否在合法范围内。

    Args:
        data: 输入数据字典。

    Returns:
        警告列表，每个元素为 (字段名, 当前值, 合法范围)。
    """
    warnings = []
    for field, (min_val, max_val) in FIELD_RANGES.items():
        if field in data and data[field] is not None:
            try:
                value = float(data[field])
                if value < min_val or value > max_val:
                    warnings.append((field, str(data[field]), f"{min_val}-{max_val}"))
            except (ValueError, TypeError):
                warnings.append((field, str(data[field]), "数值"))
    return warnings


def validate_deployment_mode(data: Dict[str, Any]) -> Optional[str]:
    """检查部署模式是否合法。

    Args:
        data: 输入数据字典。

    Returns:
        错误信息，如果合法则返回 None。
    """
    mode = data.get("deployment_mode", "single")
    if mode not in DEPLOYMENT_MODES:
        return f"{ERROR_INVALID_FORMAT}: 部署模式 '{mode}' 不合法，可选值: {', '.join(DEPLOYMENT_MODES)}"
    return None


def check_endpoint_reachable(endpoint: str, timeout: float = 5.0) -> bool:
    """检查存储端点是否可达。

    Args:
        endpoint: 存储端点 URL。
        timeout: 超时时间（秒）。

    Returns:
        是否可达。
    """
    if not endpoint:
        return False
    try:
        # 解析 URL 获取主机名和端口
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # 尝试 TCP 连接
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.error, ValueError):
        return False


def generate_config(data: Dict[str, Any]) -> str:
    """根据输入数据生成 YAML 配置。

    Args:
        data: 输入数据字典。

    Returns:
        YAML 配置字符串。
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mode = data.get("deployment_mode", "single")

    # 合并默认值
    merged = {**DEFAULT_VALUES, **data}

    if mode == "cluster":
        return TEMPLATE_CLUSTER.format(
            timestamp=timestamp,
            instance_name=merged["instance_name"],
            region=merged["region"],
            replica_count=merged["replica_count"],
            storage_endpoint=merged["storage_endpoint"],
            cpu_limit=merged["cpu_limit"],
            memory_limit=merged["memory_limit"],
            metrics_endpoint=merged["metrics_endpoint"],
        )
    elif mode == "edge":
        return TEMPLATE_EDGE.format(
            timestamp=timestamp,
            instance_name=merged["instance_name"],
            region=merged["region"],
            replica_count=merged["replica_count"],
            storage_endpoint=merged["storage_endpoint"],
            cpu_limit=merged["cpu_limit"],
            memory_limit=merged["memory_limit"],
            metrics_endpoint=merged["metrics_endpoint"],
        )
    else:
        return TEMPLATE_SINGLE.format(
            timestamp=timestamp,
            instance_name=merged["instance_name"],
            region=merged["region"],
            replica_count=merged["replica_count"],
            storage_endpoint=merged["storage_endpoint"],
            cpu_limit=merged["cpu_limit"],
            memory_limit=merged["memory_limit"],
            metrics_endpoint=merged["metrics_endpoint"],
        )


def atomic_write(file_path: str, content: str) -> None:
    """原子化写入文件。

    Args:
        file_path: 目标文件路径。
        content: 要写入的内容。
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(directory, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception:
        os.unlink(temp_path)
        raise


def validate_config(config_path: str, verbose: bool = False) -> Tuple[bool, List[Tuple[str, str]]]:
    """校验配置文件。

    Args:
        config_path: 配置文件路径。
        verbose: 是否输出详细日志。

    Returns:
        (是否全部通过, 检查结果列表)。
    """
    results = []
    all_pass = True

    # 检查文件是否存在
    if not os.path.exists(config_path):
        return False, [("配置文件存在性", "FAIL")]

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, [("配置文件读取", f"FAIL: {e}")]

    # 检查语法完整性
    required_keys = ["config_version", "generated_at", "instance_name", "region", "replica_count", "storage_endpoint"]
    missing_keys = [key for key in required_keys if key not in content]
    if missing_keys:
        results.append(("语法完整性", f"FAIL: 缺少字段 {', '.join(missing_keys)}"))
        all_pass = False
    else:
        results.append(("语法完整性", "PASS"))

    # 检查存储端点可达性
    endpoint_match = re.search(r"storage_endpoint:\s*(\S+)", content)
    if endpoint_match:
        endpoint = endpoint_match.group(1)
        if check_endpoint_reachable(endpoint):
            results.append(("存储端点可达性", "PASS"))
        else:
            results.append(("存储端点可达性", "FAIL"))
            all_pass = False
    else:
        results.append(("存储端点可达性", "FAIL: 未找到存储端点"))
        all_pass = False

    # 检查副本数合法性
    replica_match = re.search(r"replica_count:\s*(\d+)", content)
    if replica_match:
        replica_count = int(replica_match.group(1))
        if 1 <= replica_count <= 9:
            results.append(("副本数合法性", "PASS"))
        else:
            results.append(("副本数合法性", f"FAIL: 副本数 {replica_count} 超出范围 1-9"))
            all_pass = False
    else:
        results.append(("副本数合法性", "FAIL: 未找到副本数"))
        all_pass = False

    # 检查 CPU 配额范围
    cpu_match = re.search(r"cpu_limit:\s*([\d.]+)", content)
    if cpu_match:
        cpu_limit = float(cpu_match.group(1))
        if 0.1 <= cpu_limit <= 64.0:
            results.append(("CPU 配额范围", "PASS"))
        else:
            results.append(("CPU 配额范围", f"FAIL: CPU 配额 {cpu_limit} 超出范围 0.1-64.0"))
            all_pass = False
    else:
        results.append(("CPU 配额范围", "FAIL: 未找到 CPU 配额"))
        all_pass = False

    # 检查内存配额范围
    memory_match = re.search(r"memory_limit:\s*(\d+)", content)
    if memory_match:
        memory_limit = int(memory_match.group(1))
        if 128 <= memory_limit <= 524288:
            results.append(("内存配额范围", "PASS"))
        else:
            results.append(("内存配额范围", f"FAIL: 内存配额 {memory_limit} 超出范围 128-524288"))
            all_pass = False
    else:
        results.append(("内存配额范围", "FAIL: 未找到内存配额"))
        all_pass = False

    if verbose:
        for name, status in results:
            print(f"验证项: {name:<20} 结果: {status}")

    return all_pass, results


def fetch_metrics(metrics_endpoint: str, timeout: float = 5.0, max_retries: int = 3) -> Optional[str]:
    """拉取监控指标。

    Args:
        metrics_endpoint: 监控端点 URL。
        timeout: 超时时间（秒）。
        max_retries: 最大重试次数。

    Returns:
        指标内容字符串，失败返回 None。
    """
    import urllib.request
    import urllib.error

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(metrics_endpoint, headers={"User-Agent": "durable-object-deployer/4.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, socket.timeout) as e:
            if attempt < max_retries - 1:
                _g1_backoff()
            else:
                print(f"警告: 无法拉取监控指标: {e}", file=sys.stderr)
                return None
    return None


def parse_metrics(metrics_content: str) -> Dict[str, float]:
    """解析 Prometheus 格式的监控指标。

    Args:
        metrics_content: 指标内容字符串。

    Returns:
        解析后的指标字典。
    """
    result = {}
    for line in metrics_content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 匹配 cpu_usage{...} 45.2 格式
        match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\{.*\}\s+([\d.]+)', line)
        if match:
            result[match.group(1)] = float(match.group(2))
        else:
            # 匹配 cpu_usage 45.2 格式
            match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s+([\d.]+)', line)
            if match:
                result[match.group(1)] = float(match.group(2))
    return result


def monitor_instances(config_path: str, metrics_endpoint: str, verbose: bool = False) -> int:
    """监控实例状态。

    Args:
        config_path: 配置文件路径。
        metrics_endpoint: 监控端点 URL。
        verbose: 是否输出详细日志。

    Returns:
        退出码（0 表示成功，非 0 表示失败）。
    """
    if not os.path.exists(config_path):
        print(f"{ERROR_CONFIG_NOT_FOUND}: 配置文件不存在: {config_path}", file=sys.stderr)
        return 1

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"错误: 无法读取配置文件: {e}", file=sys.stderr)
        return 1

    # 解析配置
    instance_name = re.search(r"instance_name:\s*(\S+)", content)
    region = re.search(r"region:\s*(\S+)", content)
    replica_count = re.search(r"replica_count:\s*(\d+)", content)

    if not instance_name or not region or not replica_count:
        print("错误: 配置文件中缺少必要字段", file=sys.stderr)
        return 1

    # 拉取指标
    metrics_content = fetch_metrics(metrics_endpoint)
    if metrics_content is None:
        print("错误: 无法拉取监控指标", file=sys.stderr)
        return 1

    metrics = parse_metrics(metrics_content)

    cpu_usage = metrics.get("cpu_usage", 0.0)
    memory_usage = metrics.get("memory_usage", 0.0)
    connections = metrics.get("connections", 0)

    # 判断状态
    status = "healthy"
    if cpu_usage > 90.0 or memory_usage > 90.0:
        status = "degraded"
    if cpu_usage > 98.0 or memory_usage > 98.0:
        status = "critical"

    print(f"实例: {instance_name.group(1)}  状态: {status}  副本数: {replica_count.group(1)}  区域: {region.group(1)}")
    print(f"CPU 使用率: {cpu_usage:.1f}%  内存使用率: {memory_usage:.1f}%  连接数: {int(connections)}")

    if verbose:
        print(f"\n详细指标:")
        for key, value in sorted(metrics.items()):
            print(f"  {key}: {value}")

    return 0


def run_selftest() -> int:
    """运行自检程序。

    Returns:
        退出码（0 表示全部通过，非 0 表示有失败）。
    """
    print("=== 自检开始 ===")
    failures = 0

    # 测试 1: JSON 解析
    print("\n[测试 1] JSON 解析...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write('{"instance_name":"test-obj","region":"cn-north-1","replica_count":3,"storage_endpoint":"s3://bucket"}')
        temp_path = f.name
    try:
        data = parse_json_input(temp_path)
        assert data["instance_name"] == "test-obj", "instance_name 解析错误"
        assert data["replica_count"] == 3, "replica_count 解析错误"
        print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1
    finally:
        os.unlink(temp_path)

    # 测试 2: CSV 解析
    print("\n[测试 2] CSV 解析...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("instance_name,region,replica_count,storage_endpoint\n")
        f.write("test-obj,cn-north-1,3,s3://bucket\n")
        temp_path = f.name
    try:
        data = parse_csv_input(temp_path)
        assert data["instance_name"] == "test-obj", "instance_name 解析错误"
        assert data["region"] == "cn-north-1", "region 解析错误"
        print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1
    finally:
        os.unlink(temp_path)

    # 测试 3: 键值对解析
    print("\n[测试 3] 键值对解析...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("instance_name=test-obj\n")
        f.write("region=cn-north-1\n")
        f.write("replica_count=3\n")
        f.write("storage_endpoint=s3://bucket\n")
        temp_path = f.name
    try:
        data = parse_kv_input(temp_path)
        assert data["instance_name"] == "test-obj", "instance_name 解析错误"
        assert data["replica_count"] == "3", "replica_count 解析错误"
        print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1
    finally:
        os.unlink(temp_path)

    # 测试 4: 必填字段校验
    print("\n[测试 4] 必填字段校验...")
    data = {"instance_name": "test-obj", "region": "cn-north-1"}
    missing = validate_required_fields(data)
    assert "replica_count" in missing, "应检测到缺失 replica_count"
    assert "storage_endpoint" in missing, "应检测到缺失 storage_endpoint"
    print("  PASS")

    # 测试 5: 字段范围校验
    print("\n[测试 5] 字段范围校验...")
    data = {"replica_count": 15, "cpu_limit": 100.0, "memory_limit": 50}
    warnings = validate_field_ranges(data)
    assert len(warnings) == 3, f"应产生 3 条警告，实际 {len(warnings)} 条"
    print("  PASS")

    # 测试 6: 配置生成
    print("\n[测试 6] 配置生成...")
    data = {
        "instance_name": "test-obj",
        "region": "cn-north-1",
        "replica_count": 3,
        "storage_endpoint": "s3://bucket",
        "deployment_mode": "cluster",
    }
    config = generate_config(data)
    assert "config_version: 1.0.0" in config, "配置中应包含版本号"
    assert "instance_name: test-obj" in config, "配置中应包含实例名"
    assert "cluster:" in config, "集群模式应包含 cluster 配置"
    print("  PASS")

    # 测试 7: 配置校验
    print("\n[测试 7] 配置校验...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(config)
        temp_path = f.name
    try:
        all_pass, results = validate_config(temp_path, verbose=False)
        assert len(results) == 5, f"应产生 5 项检查结果，实际 {len(results)} 项"
        print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1
    finally:
        os.unlink(temp_path)

    # 测试 8: 指标解析
    print("\n[测试 8] 指标解析...")
    metrics_content = """# HELP cpu_usage CPU usage percentage
# TYPE cpu_usage gauge
cpu_usage{instance="test-obj"} 45.2
memory_usage{instance="test-obj"} 62.1
connections{instance="test-obj"} 128
"""
    metrics = parse_metrics(metrics_content)
    assert "cpu_usage" in metrics, "应解析出 cpu_usage"
    assert abs(metrics["cpu_usage"] - 45.2) < 0.01, "cpu_usage 值解析错误"
    assert "connections" in metrics, "应解析出 connections"
    print("  PASS")

    # 测试 9: 原子写入
    print("\n[测试 9] 原子写入...")
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        temp_path = f.name
    try:
        atomic_write(temp_path, "test: content\n")
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "test: content\n", "文件内容写入错误"
        print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1
    finally:
        os.unlink(temp_path)

    # 测试 10: 空输入处理
    print("\n[测试 10] 空输入处理...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("{}")
        temp_path = f.name
    try:
        data = parse_json_input(temp_path)
        missing = validate_required_fields(data)
        assert len(missing) == 4, f"空输入应缺失 4 个必填字段，实际缺失 {len(missing)} 个"
        print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1
    finally:
        os.unlink(temp_path)

    print(f"\n=== 自检完成: {10 - failures}/10 通过 ===")
    return 0 if failures == 0 else 1


def main() -> int:
    """主入口函数。

    Returns:
        退出码。
    """
    parser = argparse.ArgumentParser(
        description="持久对象部署器 - 生成、校验与监控持久对象部署配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python run.py generate --input params.json --output config.yaml
  python run.py validate --config config.yaml
  python run.py monitor --config config.yaml --metrics-endpoint http://localhost:9090/metrics
  python run.py --selftest
"""
    )

    parser.add_argument("--selftest", action="store_true", help="运行自检程序")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate 子命令
    gen_parser = subparsers.add_parser("generate", help="生成配置文件")
    gen_parser.add_argument("--input", required=False, help="输入文件路径（JSON/CSV/键值对）")
    gen_parser.add_argument("--output", required=False, help="输出 YAML 文件路径")
    gen_parser.add_argument("--format", choices=["json", "csv", "kv"], help="输入文件格式")
    gen_parser.add_argument("--batch", action="store_true", help="批量处理模式")
    gen_parser.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    gen_parser.add_argument("--force", action="store_true", help="强制接受超出范围的字段值")

    # validate 子命令
    val_parser = subparsers.add_parser("validate", help="校验配置文件")
    val_parser.add_argument("--config", required=False, help="配置文件路径")
    val_parser.add_argument("--batch", action="store_true", help="批量处理模式")

    # monitor 子命令
    mon_parser = subparsers.add_parser("monitor", help="监控实例状态")
    mon_parser.add_argument("--config", required=False, help="配置文件路径")
    mon_parser.add_argument("--metrics-endpoint", required=False, help="监控端点 URL")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无子命令
    if not args.command:
        parser.print_help()
        return 0

    # generate 子命令
    if args.command == "generate":
        try:
            # 解析输入
            data = parse_input(args.input, args.format)

            # 校验必填字段
            missing = validate_required_fields(data)
            if missing:
                print(f"{ERROR_MISSING_FIELD}: 缺少必填字段: {', '.join(missing)}", file=sys.stderr)
                return 1

            # 校验部署模式
            mode_error = validate_deployment_mode(data)
            if mode_error:
                print(mode_error, file=sys.stderr)
                return 1

            # 校验字段范围
            warnings = validate_field_ranges(data)
            for field, value, valid_range in warnings:
                print(f"{WARNING_OUT_OF_RANGE}: 字段 '{field}' 的值 '{value}' 超出范围 {valid_range}", file=sys.stderr)
                if not args.force:
                    print("使用 --force 参数强制接受", file=sys.stderr)
                    return 1

            # 生成配置
            config = generate_config(data)

            # 输出或写盘
            if args.dry_run:
                print(f"[DRY-RUN] 将写入配置到: {args.output}")
                print("--- 配置预览 ---")
                print(config)
                print("--- 预览结束 ---")
            else:
                atomic_write(args.output, config)
                print(f"配置已生成: {args.output}")

            if args.verbose:
                print(f"\n生成详情:")
                print(f"  输入文件: {args.input}")
                print(f"  输出文件: {args.output}")
                print(f"  部署模式: {data.get('deployment_mode', 'single')}")
                print(f"  实例名称: {data['instance_name']}")
                print(f"  副本数量: {data['replica_count']}")

            return 0

        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误: 生成配置失败: {e}", file=sys.stderr)
            return 1

    # validate 子命令
    elif args.command == "validate":
        try:
            all_pass, results = validate_config(args.config, verbose=args.verbose)

            if not args.verbose:
                for name, status in results:
                    print(f"验证项: {name:<20} 结果: {status}")

            if all_pass:
                print("\n校验通过: 所有检查项均通过")
                return 0
            else:
                print("\n校验失败: 存在未通过的检查项", file=sys.stderr)
                return 1

        except Exception as e:
            print(f"错误: 校验配置失败: {e}", file=sys.stderr)
            return 1

    # monitor 子命令
    elif args.command == "monitor":
        try:
            return monitor_instances(args.config, args.metrics_endpoint, verbose=args.verbose)
        except Exception as e:
            print(f"错误: 监控失败: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
