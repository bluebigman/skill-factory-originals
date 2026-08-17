#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — ai-rules-sync 技能独立实现

本脚本根据功能规格 clean-room 独立编写，仅使用标准库。
功能：将 CSV/JSON 数据源转换为结构化 CSV/JSON 输出，支持批量与自定义格式。
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import hashlib
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

dry_run = False  # v3.268 模块级 dry-run 标志

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入文件不存在或无法读取",
    "E002": "参数错误：输出格式不支持（仅支持 csv/json）",
    "E003": "数据错误：输入内容为空或缺少有效数据行",
    "E004": "数据错误：CSV 解析失败，内容格式不正确",
    "E005": "数据错误：JSON 解析失败，内容格式不正确",
    "E006": "处理错误：无法将数据行转换为目标格式",
    "E007": "处理错误：批量模式需要至少两个输入文件",
    "E008": "IO错误：无法写入输出文件",
    "E009": "逻辑错误：内部状态异常（自检失败）",
    "E010": "未知错误：未预期的异常发生",
    "E011": "参数错误：自定义格式模板无效",
    "E012": "缓存错误：缓存读写失败",
}


class RuleSyncError(Exception):
    """带错误码的业务异常基类"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ==================== 缓存策略 ====================

class CacheManager:
    """线程安全的磁盘缓存管理器，使用文件哈希作为键"""
    
    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录，默认使用系统临时目录下的 ai-rules-sync-cache
            ttl: 缓存有效期（秒），默认1小时
        """
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "ai-rules-sync-cache")
        self.cache_dir = cache_dir
        self.ttl = ttl
        self._lock = threading.RLock()  # 线程锁保护缓存操作
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{key}.cache")
    
    def get(self, key: str) -> Optional[str]:
        """获取缓存内容（线程安全）"""
        with self._lock:
            try:
                cache_path = self._get_cache_path(key)
                if not os.path.exists(cache_path):
                    return None
                
                # 检查TTL（原子操作：先检查再删除）
                mtime = os.path.getmtime(cache_path)
                if time.time() - mtime > self.ttl:
                    # 原子删除：先重命名再删除，避免竞态
                    temp_path = cache_path + f".expired.{threading.get_ident()}"
                    try:
                        os.replace(cache_path, temp_path)
                        os.remove(temp_path)
                    except OSError:
                        # 降级：直接删除或忽略
                        try:
                            os.remove(cache_path)
                        except OSError:
                            pass
                    return None
                
                with open(cache_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except (IOError, OSError) as exc:
                # 降级：缓存读取失败时返回None，不阻断主流程
                return None
    
    def set(self, key: str, content: str) -> None:
        """设置缓存内容（线程安全+原子写入）"""
        with self._lock:
            try:
                cache_path = self._get_cache_path(key)
                # 使用临时文件 + os.replace 实现原子写入
                fd, temp_path = tempfile.mkstemp(dir=self.cache_dir, suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
                        f.write(content)
                    os.replace(temp_path, cache_path)
                except Exception:
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    raise
            except (IOError, OSError) as exc:
                # 降级：缓存写入失败时静默忽略
                pass
    
    def clear(self) -> None:
        """清空缓存（线程安全）"""
        with self._lock:
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith(".cache"):
                        os.remove(os.path.join(self.cache_dir, filename))
            except (IOError, OSError) as exc:
                # 降级：清空失败时静默忽略
                pass


def _compute_cache_key(input_path: str, output_format: str, template: Optional[str] = None) -> str:
    """计算缓存键"""
    try:
        with open(input_path, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        template_part = template or ""
        return hashlib.md5(f"{file_hash}:{output_format}:{template_part}".encode()).hexdigest()
    except (IOError, OSError) as exc:
        raise RuleSyncError("E001", f"{ERROR_CODES['E001']} 路径: {input_path} 详情: {exc}") from exc


# ==================== 核心转换函数 ====================

def _strip_headers(raw_lines: List[str]) -> List[str]:
    """去除常见文件头（如注释、版本声明等）"""
    result = []
    for line in raw_lines:
        stripped = line.strip()
        # 跳过空行和注释行（# 或 // 开头）
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        result.append(line)
    return result


def _detect_format(text: str) -> str:
    """检测数据格式（json/csv），默认 csv"""
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    return "csv"


def _parse_csv_text(text: str) -> List[Dict[str, str]]:
    """解析 CSV 文本为字典列表（首行为表头）"""
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(row) for row in reader if any(v.strip() for v in row.values())]
        if not rows:
            raise RuleSyncError("E003", ERROR_CODES["E003"])
        return rows
    except csv.Error as exc:
        raise RuleSyncError("E004", f"{ERROR_CODES['E004']} 详情: {exc}") from exc


def _parse_json_text(text: str) -> List[Dict[str, Any]]:
    """解析 JSON 文本为字典列表"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuleSyncError("E005", f"{ERROR_CODES['E005']} 详情: {exc}") from exc

    # 统一为列表形式
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise RuleSyncError("E005", ERROR_CODES["E005"])

    # 过滤空字典
    rows = [item for item in data if isinstance(item, dict) and item]
    if not rows:
        raise RuleSyncError("E003", ERROR_CODES["E003"])
    return rows


def _rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    """将字典列表转换为 CSV 字符串"""
    if not rows:
        raise RuleSyncError("E006", ERROR_CODES["E006"])
    # 合并所有键作为表头，保持原始顺序
    headers: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in headers:
                headers.append(key)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in headers})
    return output.getvalue().strip()


def _rows_to_json(rows: List[Dict[str, Any]]) -> str:
    """将字典列表转换为 JSON 字符串"""
    try:
        return json.dumps(rows, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise RuleSyncError("E006", f"{ERROR_CODES['E006']} 详情: {exc}") from exc


def _apply_custom_template(rows: List[Dict[str, Any]], template: str) -> str:
    """
    应用自定义格式模板
    
    支持模板变量：
    - {rows} 或 {data}: 完整数据（JSON格式）
    - {count}: 记录数
    - {timestamp}: 当前UTC时间戳
    - {field_name}: 第一条记录的字段值（如果存在）
    
    示例模板：
    - "共 {count} 条记录，第一条的name是 {name}"
    - "数据: {rows}"
    """
    if not template:
        raise RuleSyncError("E011", ERROR_CODES["E011"])
    
    try:
        # 替换基本变量
        result = template
        result = result.replace("{rows}", json.dumps(rows, ensure_ascii=False))
        result = result.replace("{data}", json.dumps(rows, ensure_ascii=False))
        result = result.replace("{count}", str(len(rows)))
        result = result.replace("{timestamp}", datetime.now(timezone.utc).isoformat())
        
        # 替换字段变量（取第一条记录）
        if rows:
            first_row = rows[0]
            for key, value in first_row.items():
                result = result.replace("{" + key + "}", str(value))
        
        return result
    except (KeyError, ValueError, TypeError) as exc:
        raise RuleSyncError("E011", f"{ERROR_CODES['E011']} 详情: {exc}") from exc


def _normalize_values(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """数据规范化：去除首尾空白，空字符串转为 None"""
    normalized = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            if isinstance(v, str):
                v = v.strip()
                if v == "":
                    v = None
            new_row[k.strip()] = v
        normalized.append(new_row)
    return normalized


def transform_data(
    input_text: str, 
    output_format: str = "csv", 
    template: Optional[str] = None
) -> str:
    """
    核心转换函数：将输入文本（CSV/JSON）转换为指定格式输出。

    参数:
        input_text: 原始输入文本
        output_format: 目标格式 ("csv" 或 "json")
        template: 自定义格式模板（可选）

    返回:
        转换后的文本

    异常:
        RuleSyncError: 处理失败时抛出带错误码的异常
    """
    if not input_text or not input_text.strip():
        raise RuleSyncError("E003", ERROR_CODES["E003"])

    if output_format not in ("csv", "json"):
        raise RuleSyncError("E002", ERROR_CODES["E002"])

    # 去除文件头注释
    lines = _strip_headers(input_text.splitlines())
    clean_text = "\n".join(lines).strip()
    if not clean_text:
        raise RuleSyncError("E003", ERROR_CODES["E003"])

    # 解析输入
    source_format = _detect_format(clean_text)
    if source_format == "json":
        rows = _parse_json_text(clean_text)
    else:
        rows = _parse_csv_text(clean_text)

    # 规范化
    rows = _normalize_values(rows)

    # 转换输出
    if template:
        return _apply_custom_template(rows, template)
    elif output_format == "csv":
        return _rows_to_csv(rows)
    else:
        return _rows_to_json(rows)


def process_file(
    input_path: str, 
    output_format: str = "csv", 
    template: Optional[str] = None,
    cache: Optional[CacheManager] = None
) -> str:
    """处理单个文件，返回转换结果（带缓存支持）"""
    # 尝试从缓存读取
    if cache:
        cache_key = _compute_cache_key(input_path, output_format, template)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
    
    # 读取文件
    try:
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (IOError, OSError) as exc:
        raise RuleSyncError("E001", f"{ERROR_CODES['E001']} 路径: {input_path} 详情: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise RuleSyncError("E001", f"{ERROR_CODES['E001']} 编码错误: {exc}") from exc

    # 转换
    result = transform_data(content, output_format, template)
    
    # 写入缓存
    if cache:
        try:
            cache.set(cache_key, result)
        except RuleSyncError:
            # 缓存失败不影响主流程
            pass
    
    return result


def process_batch(
    input_paths: List[str], 
    output_format: str = "csv", 
    template: Optional[str] = None,
    max_workers: int = 4,
    use_cache: bool = True
) -> List[str]:
    """批量处理多个文件（并行处理）"""
    if len(input_paths) < 2:
        raise RuleSyncError("E007", ERROR_CODES["E007"])

    # 限制最大并发数
    max_workers = min(max_workers, 8)  # 上限8个并发
    if max_workers < 1:
        max_workers = 1

    # 初始化缓存
    cache = CacheManager() if use_cache else None

    results: List[str] = []
    errors: List[Tuple[str, RuleSyncError]] = []
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(process_file, path, output_format, template, cache): path
            for path in input_paths
        }
        
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                result = future.result()
                results.append(result)
            except RuleSyncError as exc:
                errors.append((path, exc))
                print(f"  处理 {path} 失败: {exc.code} {exc.message}", file=sys.stderr)
    
    # 如果有错误，汇总抛出
    if errors:
        error_msgs = "; ".join(f"{path}: {exc.code} {exc.message}" for path, exc in errors)
        raise RuleSyncError("E010", f"批量处理部分失败: {error_msgs}")
    
    return results


def write_output(content: str, output_path: Optional[str] = None) -> None:
    """写入输出文件或打印到 stdout"""
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
        except (IOError, OSError) as exc:
            raise RuleSyncError("E008", f"{ERROR_CODES['E008']} 路径: {output_path} 详情: {exc}") from exc
    else:
        print(content)


# ==================== 自检程序 ====================

def run_selftest() -> int:
    """
    内置自检程序：验证核心转换链路。
    真实调用主流程/核心函数并断言关键输出。
    """
    print("[SELFTEST] 开始自检...")
    
    # ========== 测试1: CSV转JSON ==========
    print("  [测试] CSV转JSON...")
    try:
        csv_text = "name,age\nAlice,30\nBob,25\n"
        result = transform_data(csv_text, "json")
        parsed = json.loads(result)
        assert len(parsed) == 2, f"JSON行数错误: {len(parsed)}"
        assert parsed[0]["name"] == "Alice", f"字段错误: {parsed[0]}"
        assert parsed[1]["age"] == "25", f"字段错误: {parsed[1]}"
        print("    [OK] CSV转JSON成功")
    except Exception as exc:
        print(f"    [FAIL] CSV转JSON失败: {exc}")
        return 1
    
    # ========== 测试2: JSON转CSV ==========
    print("  [测试] JSON转CSV...")
    try:
        json_text = '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
        result = transform_data(json_text, "csv")
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 2, f"CSV行数错误: {len(rows)}"
        assert rows[0]["name"] == "Alice", f"字段错误: {rows[0]}"
        assert rows[1]["age"] == "25", f"字段错误: {rows[1]}"
        print("    [OK] JSON转CSV成功")
    except Exception as exc:
        print(f"    [FAIL] JSON转CSV失败: {exc}")
        return 1
    
    # ========== 测试3: 自定义模板 ==========
