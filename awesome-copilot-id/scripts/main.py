#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-copilot-id 技能实现脚本
功能：将用户提供的任意数据、文件或URL解析为结构化结果，支持批量处理与置信度标注。
版本：1.0.2
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# -------------------------------
# 错误码定义
# -------------------------------
ERROR_CODES = {
    "E001": "输入数据为空或无效",
    "E002": "不支持的输入类型",
    "E003": "文件读取失败",
    "E004": "URL 访问失败",
    "E005": "JSON 解析失败",
    "E006": "CSV 解析失败",
    "E007": "字段提取失败",
    "E008": "批量处理失败",
    "E009": "置信度计算失败",
    "E010": "内部逻辑错误",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# -------------------------------
# 核心解析逻辑
# -------------------------------

def _detect_type(data: Any) -> str:
    """检测输入数据类型"""
    if data is None:
        raise SkillError("E001")
    if isinstance(data, str):
        # 去除首尾空白
        data = data.strip()
        # 尝试判断是否为文件路径或URL
        if data.startswith(("http://", "https://")):
            return "url"
        if os.path.exists(data):
            return "file"
        # 尝试解析为 JSON
        try:
            json.loads(data)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass
        # 尝试解析为 CSV
        if "," in data or ";" in data:
            return "csv"
        return "text"
    if isinstance(data, (dict, list)):
        return "json"
    if isinstance(data, (int, float, bool)):
        return "text"
    return "unknown"


def _parse_json(data: Union[str, Dict, List]) -> Dict[str, Any]:
    """解析 JSON 数据"""
    try:
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"items": parsed, "_type": "list"}
        raise SkillError("E005", "JSON 根节点必须是对象或数组")
    except json.JSONDecodeError as e:
        raise SkillError("E005", f"JSON 解析失败: {e}") from e


def _parse_csv(data: str) -> Dict[str, Any]:
    """解析 CSV 数据"""
    try:
        # 清理数据，确保第一行是表头
        lines = data.strip().split('\n')
        if len(lines) < 2:
            raise SkillError("E006", "CSV 数据至少需要表头和一行数据")
        
        # 尝试检测分隔符
        sample = data[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
            delimiter = dialect.delimiter
        except csv.Error:
            # 默认使用逗号
            delimiter = ','
        
        # 解析 CSV
        reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
        rows = list(reader)
        if not rows:
            raise SkillError("E006", "CSV 数据为空")
        
        # 获取表头
        headers = list(rows[0].keys())
        
        # 清理行数据中的空值
        cleaned_rows = []
        for row in rows:
            cleaned_row = {}
            for key, value in row.items():
                if value is not None:
                    cleaned_row[key] = value.strip() if isinstance(value, str) else value
                else:
                    cleaned_row[key] = ""
            cleaned_rows.append(cleaned_row)
        
        return {
            "headers": headers,
            "rows": cleaned_rows,
            "count": len(cleaned_rows),
            "delimiter": delimiter
        }
    except csv.Error as e:
        raise SkillError("E006", f"CSV 解析失败: {e}") from e
    except Exception as e:
        if isinstance(e, SkillError):
            raise
        raise SkillError("E006", f"CSV 解析失败: {e}") from e


def _read_file(path: str) -> str:
    """读取文件内容"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError) as e:
        raise SkillError("E003", f"文件读取失败: {e}") from e


def _fetch_url(url: str) -> str:
    """获取 URL 内容"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        raise SkillError("E004", f"URL 访问失败: {e}") from e


def _extract_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """从解析后的数据中提取结构化字段"""
    try:
        result = {"_meta": {}, "data": data}
        
        # 如果数据是列表类型（来自JSON数组），特殊处理
        if isinstance(data, dict) and "_type" in data and data["_type"] == "list":
            items = data.get("items", [])
            result["_meta"]["item_count"] = len(items)
            result["_meta"]["item_type"] = "list"
            return result
        
        # 提取通用字段
        if isinstance(data, dict):
            # 处理嵌套数据
            for key in ["id", "name", "title", "type", "status", "category"]:
                if key in data:
                    result["_meta"][key] = data[key]
            
            # 时间字段
            for key in ["created_at", "updated_at", "timestamp", "date", "time"]:
                if key in data:
                    try:
                        ts = data[key]
                        if isinstance(ts, (int, float)):
                            # 判断是秒还是毫秒
                            if ts > 10000000000:  # 毫秒
                                dt = datetime.fromtimestamp(ts / 1000)
                            else:  # 秒
                                dt = datetime.fromtimestamp(ts)
                            result["_meta"][key] = dt.isoformat()
                        else:
                            result["_meta"][key] = str(ts)
                    except (ValueError, TypeError, OSError):
                        result["_meta"][key] = str(data[key])
            
            # 其他常见字段
            for key in ["email", "phone", "address", "url", "website"]:
                if key in data and data[key]:
                    result["_meta"][key] = data[key]
        
        return result
    except Exception as e:
        raise SkillError("E007", f"字段提取失败: {e}") from e


def _calculate_confidence(data: Any) -> float:
    """计算数据解析的置信度（0-1）"""
    try:
        if data is None:
            return 0.0
        
        score = 0.4  # 基础分（降低基础分，使区分度更高）
        
        if isinstance(data, dict):
            # 字段数量影响
            score += min(len(data) * 0.05, 0.3)
            # 关键字段提升置信度
            if any(k in data for k in ["id", "name", "type", "title"]):
                score += 0.15
            # 嵌套结构
            if any(isinstance(v, (dict, list)) for v in data.values()):
                score += 0.1
        elif isinstance(data, list):
            # 列表长度影响
            score += min(len(data) * 0.03, 0.25)
            # 列表包含对象
            if data and all(isinstance(item, dict) for item in data):
                score += 0.15
        elif isinstance(data, str):
            # 字符串长度影响
            score += min(len(data) * 0.002, 0.2)
            # 包含结构化特征
            if any(char in data for char in ['{', '[', ',']):
                score += 0.1
        elif isinstance(data, (int, float)):
            score += 0.15
        elif isinstance(data, bool):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    except Exception as e:
        raise SkillError("E009", f"置信度计算失败: {e}") from e


def parse_single(data: Any) -> Dict[str, Any]:
    """解析单条数据"""
    # 空数据检查
    if data is None:
        raise SkillError("E001")
    if isinstance(data, str) and not data.strip():
        raise SkillError("E001")
    if isinstance(data, (list, dict)) and len(data) == 0:
        raise SkillError("E001")

    data_type = _detect_type(data)
    parsed = None

    if data_type == "url":
        content = _fetch_url(data)
        # 尝试解析为 JSON
        try:
            parsed = _parse_json(content)
        except SkillError:
            # 尝试解析为 CSV
            try:
                parsed = _parse_csv(content)
            except SkillError:
                parsed = {"content": content, "url": data}
    elif data_type == "file":
        content = _read_file(data)
        ext = Path(data).suffix.lower()
        try:
            if ext in [".json", ".jsonl"]:
                parsed = _parse_json(content)
            elif ext in [".csv", ".tsv"]:
                parsed = _parse_csv(content)
            else:
                # 尝试自动检测
                try:
                    parsed = _parse_json(content)
                except SkillError:
                    try:
                        parsed = _parse_csv(content)
                    except SkillError:
                        parsed = {"content": content, "filename": Path(data).name}
        except SkillError:
            parsed = {"content": content, "filename": Path(data).name}
    elif data_type == "json":
        parsed = _parse_json(data)
    elif data_type == "csv":
        parsed = _parse_csv(data)
    elif data_type == "text":
        if isinstance(data, (int, float, bool)):
            parsed = {"content": str(data)}
        else:
            parsed = {"content": data}
    else:
        raise SkillError("E002", f"不支持的数据类型: {type(data).__name__}")

    structured = _extract_fields(parsed)
    confidence = _calculate_confidence(parsed)

    return {
        "source_type": data_type,
        "structured": structured,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.2",
        "status": "success"
    }


def parse_batch(items: List[Any]) -> Dict[str, Any]:
    """批量解析多条数据"""
    if not items:
        raise SkillError("E001")
    
    results = []
    errors = []
    
    for i, item in enumerate(items):
        try:
            result = parse_single(item)
            results.append({
                "index": i,
                "result": result,
                "success": True
            })
        except SkillError as e:
            errors.append({
                "index": i,
                "code": e.code,
                "message": e.message,
                "success": False
            })
        except Exception as e:
            errors.append({
                "index": i,
                "code": "E008",
                "message": str(e),
                "success": False
            })

    # 计算统计信息
    total_items = len(items)
    success_count = len(results)
    fail_count = len(errors)
    
    # 计算平均置信度
    avg_confidence = 0.0
    if results:
        confidences = [r["result"]["confidence"] for r in results]
        avg_confidence = sum(confidences) / len(confidences)

    return {
        "total": total_items,
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": success_count / total_items if total_items > 0 else 0,
        "avg_confidence": avg_confidence,
        "results": results,
        "errors": errors,
        "batch_id": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.2",
        "status": "success" if fail_count == 0 else "partial"
    }


# -------------------------------
# 自测模块
# -------------------------------

def run_selftest() -> bool:
    """内置硬编码样例的自检测试，不依赖外部环境"""
    print("=" * 60)
    print("开始自检 (selftest)...")
    print("=" * 60)

    all_passed = True

    # 测试样例 1：JSON 字符串
    print("\n[测试 1] JSON 字符串解析")
    json_sample = '{"id": 1, "name": "测试项目", "status": "active", "created_at": 1700000000}'
    try:
        result = parse_single(json_sample)
        assert result["source_type"] == "json", f"JSON 类型检测失败: {result['source_type']}"
        assert result["confidence"] > 0.5, f"JSON 置信度异常: {result['confidence']}"
        assert result["structured"]["_meta"].get("name") == "测试项目", "字段提取失败"
        assert result["status"] == "success", "状态标记错误"
        print("[PASS] JSON 解析测试")
    except AssertionError as e:
        print(f"[FAIL] JSON 解析测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] JSON 解析测试: {e}")
        all_passed = False

    # 测试样例 2：CSV 字符串
    print("\n[测试 2] CSV 字符串解析")
    csv_sample = "name,age,city\n张三,28,北京\n李四,35,上海\n王五,42,广州"
    try:
        result = parse_single(csv_sample)
        assert result["source_type"] == "csv", f"CSV 类型检测失败: {result['source_type']}"
        assert result["structured"]["data"].get("count") == 3, f"CSV 行数解析错误: {result['structured']['data'].get('count')}"
        assert result["structured"]["data"].get("headers") == ["name", "age", "city"], "CSV 表头解析错误"
        assert result["confidence"] > 0.3, f"CSV 置信度异常: {result['confidence']}"
        print("[PASS] CSV 解析测试")
    except AssertionError as e:
        print(f"[FAIL] CSV 解析测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] CSV 解析测试: {e}")
        all_passed = False

    # 测试样例 3：Python 字典
    print("\n[测试 3] Python 字典解析")
    dict_sample = {"id": 42, "name": "示例数据", "tags": ["a", "b", "c"], "score": 87.5}
    try:
        result = parse_single(dict_sample)
        assert result["source_type"] == "json", f"字典类型检测失败: {result['source_type']}"
        assert result["confidence"] > 0.5, f"字典置信度异常: {result['confidence']}"
        assert result["structured"]["_meta"].get("id") == 42, "字典字段提取失败"
        print("[PASS] 字典解析测试")
    except AssertionError as e:
        print(f"[FAIL] 字典解析测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] 字典解析测试: {e}")
        all_passed = False

    # 测试样例 4：批量处理
    print("\n[测试 4] 批量处理")
    batch_sample = [
        '{"id": 1, "name": "项目A"}',
        "name,value\nx,100\ny,200",
        {"id": 3, "name": "项目C"},
        "简单文本数据"
    ]
    try:
        result = parse_batch(batch_sample)
        assert result["total"] == 4, f"批量总数错误: {result['total']}"
        assert result["success_count"] == 4, f"批量成功数错误: {result['success_count']}"
        assert result["fail_count"] == 0, f"批量失败数错误: {result['fail_count']}"
        assert result["success_rate"] == 1.0, "成功率错误"
        assert result["avg_confidence"] > 0.3, f"平均置信度异常: {result['avg_confidence']}"
        print("[PASS] 批量解析测试")
    except AssertionError as e:
        print(f"[FAIL] 批量解析测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] 批量解析测试: {e}")
        all_passed = False

    # 测试样例 5：错误处理
    print("\n[测试 5] 错误处理")
    try:
        parse_single("")
        print("[FAIL] 空数据错误处理测试")
        all_passed = False
    except SkillError as e:
        if e.code != "E001":
            print(f"[FAIL] 错误码错误: {e.code}")
            all_passed = False
        else:
            print("[PASS] 空数据错误处理测试")

    # 测试样例 6：置信度范围
    print("\n[测试 6] 置信度范围")
    try:
        test_samples = [123, "hello", [1, 2, 3], {"a": 1}, True, 3.14]
        for sample in test_samples:
            result = parse_single(sample)
            assert 0 <= result["confidence"] <= 1, f"置信度超出范围: {result['confidence']}"
        print("[PASS] 置信度范围测试")
    except AssertionError as e:
        print(f"[FAIL] 置信度范围测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] 置信度范围测试: {e}")
        all_passed = False

    # 测试样例 7：CSV 分号分隔符
    print("\n[测试 7] CSV 分号分隔符")
    csv_semicolon = "name;age;city\n张三;28;北京\n李四;35;上海"
    try:
        result = parse_single(csv_semicolon)
        assert result["source_type"] == "csv", f"CSV 类型检测失败: {result['source_type']}"
        assert result["structured"]["data"].get("count") == 2, "CSV 行数解析错误"
        assert result["structured"]["data"].get("delimiter") == ";", "分隔符检测错误"
        print("[PASS] CSV 分号分隔符测试")
    except AssertionError as e:
        print(f"[FAIL] CSV 分号分隔符测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] CSV 分号分隔符测试: {e}")
        all_passed = False

    # 测试样例 8：JSON 数组
    print("\n[测试 8] JSON 数组解析")
    json_array = '[{"id": 1, "name": "项目A"}, {"id": 2, "name": "项目B"}]'
    try:
        result = parse_single(json_array)
        assert result["source_type"] == "json", f"JSON 类型检测失败: {result['source_type']}"
        assert result["structured"]["data"].get("_type") == "list", "JSON 数组类型错误"
        assert len(result["structured"]["data"].get("items", [])) == 2, "JSON 数组长度错误"
        print("[PASS] JSON 数组解析测试")
    except AssertionError as e:
        print(f"[FAIL] JSON 数组解析测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] JSON 数组解析测试: {e}")
        all_passed = False

    # 测试样例 9：嵌套 JSON
    print("\n[测试 9] 嵌套 JSON 解析")
    nested_json = '{"user": {"name": "张三", "age": 30}, "items": [{"id": 1}, {"id": 2}]}'
    try:
        result = parse_single(nested_json)
        assert result["source_type"] == "json", f"JSON 类型检测失败: {result['source_type']}"
        assert result["confidence"] > 0.6, f"嵌套 JSON 置信度异常: {result['confidence']}"
        print("[PASS] 嵌套 JSON 解析测试")
    except AssertionError as e:
        print(f"[FAIL] 嵌套 JSON 解析测试: {e}")
        all_passed = False
    except SkillError as e:
        print(f"[FAIL] 嵌套 JSON 解析测试: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("所有自检项通过！")
    else:
        print("存在未通过的测试项！")
    print("=" * 60)
    
    return all_passed


# -------------------------------
# 命令行入口
# -------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="awesome-copilot-id: 数据解析与结构化转换工具",
        epilog="示例: python main.py --data '{\"name\": \"test\"}' --batch",
    )
    parser.add_argument("--data", type=str, help="待解析的数据（字符串、JSON、CSV）")
    parser.add_argument("--file", type=str, help="待解析的文件路径")
    parser.add_argument("--url", type=str, help="待解析的URL地址")
    parser.add_argument("--batch", action="store_true", help="批量处理模式（--data 为 JSON 数组）")
    parser.add_argument("--output", type=str, choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                data = f.read()
        elif args.url:
            data = args.url
        elif args.data:
            data = args.data
        else:
            # 交互模式：从标准输入读取
            print("请输入要解析的数据（Ctrl+D 结束）：")
            data = sys.stdin.read().strip()
            if not data:
                raise SkillError("E001")

        # 批量处理
        if args.batch:
            # 尝试将输入解析为列表
            if isinstance(data, str):
                try:
                    items = json.loads(data)
                    if not isinstance(items, list):
                        raise SkillError("E008", "批量模式需要 JSON 数组")
                except json.JSONDecodeError as e:
                    raise SkillError("E008", f"批量模式 JSON 解析失败: {e}") from e
            else:
                items = data
            result = parse_batch(items)
        else:
            result = parse_single(data)

        # 输出结果
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 文本输出
            if isinstance(result, dict) and "structured" in result:
                print(f"类型: {result['source_type']}")
                print(f"置信度: {result['confidence']:.2%}")
                print(f"时间: {result['timestamp']}")
                print("数据:")
                print(json.dumps(result["structured"], ensure_ascii=False, indent=2))
            elif isinstance(result, dict) and "results" in result:
                # 批量结果输出
                print(f"批量处理结果:")
                print(f"  总数: {result['total']}")
                print(f"  成功: {result['success_count']}")
                print(f"  失败: {result['fail_count']}")
                print(f"  成功率: {result['success_rate']:.2%}")
                print(f"  平均置信度: {result['avg_confidence']:.2%}")
                print("\n详细结果:")
                for item in result["results"]:
                    print(f"  [{item['index']}] 类型: {item['result']['source_type']}, 置信度: {item['result']['confidence']:.2%}")
                if result["errors"]:
                    print("\n错误信息:")
                    for error in result["errors"]:
                        print(f"  [{error['index']}] 错误码: {error['code']}, 信息: {error['message']}")
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
