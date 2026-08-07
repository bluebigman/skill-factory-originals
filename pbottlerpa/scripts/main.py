#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pbottlerpa — 网页自动化与数据提取流程编排工具（独立实现）

本脚本基于功能规格独立编写，不依赖任何既有实现。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数类型不正确",
    "E002": "流程定义错误：流程为空或格式不正确",
    "E003": "步骤类型错误：不支持的步骤类型",
    "E004": "选择器错误：元素选择器缺失或无效",
    "E005": "执行错误：步骤执行过程中发生异常",
    "E006": "数据提取错误：无法从响应中提取数据",
    "E007": "流程中断：用户请求终止或超时",
    "E008": "网络错误：请求失败或连接超时",
    "E009": "数据校验错误：提取的数据未通过验证",
    "E010": "内部错误：未预期的异常",
}


class PbottlerpaError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class StepResult:
    """单个步骤的执行结果。"""

    step_id: str
    step_type: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class FlowResult:
    """整个流程的执行结果。"""

    flow_name: str
    success: bool
    steps: List[StepResult] = field(default_factory=list)
    final_data: Any = None
    error: Optional[str] = None
    total_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。"""
        return {
            "flow_name": self.flow_name,
            "success": self.success,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_type": s.step_type,
                    "success": s.success,
                    "data": s.data,
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
            "final_data": self.final_data,
            "error": self.error,
            "total_duration_ms": self.total_duration_ms,
        }


# ============================================================
# 工具函数
# ============================================================
def _now_ms() -> float:
    """返回当前毫秒时间戳。"""
    return time.time() * 1000.0


def _safe_json_dumps(obj: Any) -> str:
    """安全 JSON 序列化。"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(obj)


def _is_valid_url(url: str) -> bool:
    """简单 URL 合法性检查。"""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _extract_by_selector(data: Any, selector: str) -> Any:
    """
    从数据中按选择器提取内容。

    支持的选择器格式：
      - JSONPath 简化版：$.key1.key2[0].key3
      - 正则表达式：regex:/pattern/
      - 直接键名：key1.key2
    """
    if selector.startswith("regex:"):
        # 正则表达式提取
        pattern = selector[6:]
        if isinstance(data, str):
            match = re.search(pattern, data)
            return match.group(0) if match else None
        return None

    # 清理 JSONPath 前缀
    path = selector
    if path.startswith("$."):
        path = path[2:]
    elif path.startswith("$"):
        path = path[1:]

    # 按点号分割路径
    parts = re.split(r"\.", path)
    current = data

    for part in parts:
        if current is None:
            return None

        # 处理数组索引
        array_match = re.match(r"^(\w+)\[(\d+)\]$", part)
        if array_match:
            key, index = array_match.group(1), int(array_match.group(2))
            if isinstance(current, dict) and key in current:
                current = current[key]
                if isinstance(current, list) and index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
        elif isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None

    return current


# ============================================================
# 内置流程执行引擎
# ============================================================
class FlowEngine:
    """流程执行引擎，支持多种步骤类型。"""

    def __init__(self, http_client: Optional[Callable] = None):
        """
        初始化引擎。

        :param http_client: 可选的 HTTP 请求函数（用于替换默认实现）
        """
        self._http_client = http_client or self._default_http_client
        self._variables: Dict[str, Any] = {}

    @staticmethod
    def _default_http_client(method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        默认 HTTP 客户端（模拟实现）。

        实际项目中可替换为 requests 等库。
        """
        # 注意：此处仅作演示，真实环境请使用 requests 或 httpx
        # pip install requests
        raise PbottlerpaError("E008", "默认 HTTP 客户端未配置，请注入自定义客户端")

    def execute(self, flow: Dict[str, Any]) -> FlowResult:
        """执行整个流程定义。"""
        flow_name = flow.get("name", "未命名流程")
        steps = flow.get("steps", [])

        if not steps:
            raise PbottlerpaError("E002", "流程定义中不包含任何步骤")

        result = FlowResult(flow_name=flow_name, success=True)
        start_total = _now_ms()

        try:
            for step in steps:
                step_result = self._execute_step(step)
                result.steps.append(step_result)

                if not step_result.success:
                    result.success = False
                    result.error = step_result.error
                    break

                # 将步骤输出保存到变量
                if step_result.data is not None:
                    self._variables[step.get("output", f"step_{step_result.step_id}")] = step_result.data

            result.final_data = self._variables.get("final_output", self._variables)
            result.total_duration_ms = _now_ms() - start_total
            return result

        except PbottlerpaError as e:
            result.success = False
            result.error = str(e)
            result.total_duration_ms = _now_ms() - start_total
            return result
        except Exception as e:
            result.success = False
            result.error = f"[E010] 内部错误: {str(e)}"
            result.total_duration_ms = _now_ms() - start_total
            return result

    def _execute_step(self, step: Dict[str, Any]) -> StepResult:
        """执行单个步骤。"""
        step_id = step.get("id", "unknown")
        step_type = step.get("type", "")
        start = _now_ms()

        try:
            handler = self._get_handler(step_type)
            data = handler(step)
            return StepResult(
                step_id=step_id,
                step_type=step_type,
                success=True,
                data=data,
                duration_ms=_now_ms() - start,
            )
        except PbottlerpaError as e:
            return StepResult(
                step_id=step_id,
                step_type=step_type,
                success=False,
                error=str(e),
                duration_ms=_now_ms() - start,
            )
        except Exception as e:
            return StepResult(
                step_id=step_id,
                step_type=step_type,
                success=False,
                error=f"[E010] 内部错误: {str(e)}",
                duration_ms=_now_ms() - start,
            )

    def _get_handler(self, step_type: str) -> Callable:
        """根据步骤类型获取处理函数。"""
        handlers = {
            "http_request": self._handle_http_request,
            "extract": self._handle_extract,
            "transform": self._handle_transform,
            "condition": self._handle_condition,
            "loop": self._handle_loop,
            "delay": self._handle_delay,
            "log": self._handle_log,
            "set_variable": self._handle_set_variable,
        }

        handler = handlers.get(step_type)
        if not handler:
            raise PbottlerpaError("E003", f"不支持的步骤类型: {step_type}")
        return handler

    # ---- 各步骤处理函数 ----

    def _handle_http_request(self, step: Dict[str, Any]) -> Any:
        """HTTP 请求步骤。"""
        url = step.get("url", "")
        method = step.get("method", "GET").upper()

        if not url:
            raise PbottlerpaError("E001", "HTTP 请求步骤缺少 URL")

        # 变量替换
        url = self._replace_variables(url)

        if not _is_valid_url(url):
            raise PbottlerpaError("E008", f"无效的 URL: {url}")

        headers = step.get("headers", {})
        params = step.get("params", {})
        body = step.get("body")

        # 调用 HTTP 客户端
        response = self._http_client(method, url, headers=headers, params=params, body=body)

        # 检查响应
        if not response.get("ok", False):
            raise PbottlerpaError("E008", f"请求失败: {response.get('status', 'unknown')}")

        return response.get("data")

    def _handle_extract(self, step: Dict[str, Any]) -> Any:
        """数据提取步骤。"""
        source = step.get("source")
        selector = step.get("selector", "")

        if not selector:
            raise PbottlerpaError("E004", "提取步骤缺少选择器")

        # 如果 source 是变量名，从变量中获取
        if isinstance(source, str) and source.startswith("$"):
            source_var = source[1:]
            source = self._variables.get(source_var)

        if source is None:
            raise PbottlerpaError("E006", "提取源数据为空")

        result = _extract_by_selector(source, selector)

        # 提取后校验
        expected_type = step.get("expected_type")
        if expected_type and result is not None:
            try:
                if expected_type == "int":
                    result = int(result)
                elif expected_type == "float":
                    result = float(result)
                elif expected_type == "str":
                    result = str(result)
                elif expected_type == "list" and not isinstance(result, list):
                    raise PbottlerpaError("E009", "提取结果不是列表类型")
            except (ValueError, TypeError):
                raise PbottlerpaError("E009", f"提取结果无法转换为 {expected_type}")

        return result

    def _handle_transform(self, step: Dict[str, Any]) -> Any:
        """数据转换步骤。"""
        source = step.get("source")
        transform_type = step.get("transform", "")

        # 变量替换
        if isinstance(source, str) and source.startswith("$"):
            source = self._variables.get(source[1:])

        if transform_type == "json_stringify":
            return _safe_json_dumps(source)
        elif transform_type == "json_parse":
            if isinstance(source, str):
                try:
                    return json.loads(source)
                except json.JSONDecodeError:
                    raise PbottlerpaError("E006", "JSON 解析失败")
            return source
        elif transform_type == "upper":
            return str(source).upper() if source else source
        elif transform_type == "lower":
            return str(source).lower() if source else source
        elif transform_type == "strip":
            return str(source).strip() if source else source
        elif transform_type == "concat":
            parts = step.get("parts", [])
            separator = step.get("separator", "")
            resolved = []
            for p in parts:
                if isinstance(p, str) and p.startswith("$"):
                    resolved.append(str(self._variables.get(p[1:], "")))
                else:
                    resolved.append(str(p))
            return separator.join(resolved)
        else:
            raise PbottlerpaError("E003", f"不支持的转换类型: {transform_type}")

    def _handle_condition(self, step: Dict[str, Any]) -> Any:
        """条件判断步骤。"""
        variable = step.get("variable", "")
        operator = step.get("operator", "==")
        expected = step.get("value")

        # 获取变量值
        if variable.startswith("$"):
            variable = variable[1:]
        actual = self._variables.get(variable)

        # 执行比较
        if operator == "==":
            result = actual == expected
        elif operator == "!=":
            result = actual != expected
        elif operator == ">":
            result = float(actual) > float(expected)
        elif operator == "<":
            result = float(actual) < float(expected)
        elif operator == ">=":
            result = float(actual) >= float(expected)
        elif operator == "<=":
            result = float(actual) <= float(expected)
        elif operator == "contains":
            result = expected in str(actual)
        elif operator == "not_contains":
            result = expected not in str(actual)
        else:
            raise PbottlerpaError("E001", f"不支持的操作符: {operator}")

        # 根据结果执行分支
        if result:
            branch = step.get("then", [])
        else:
            branch = step.get("else", [])

        # 执行分支子流程
        branch_result = None
        for sub_step in branch:
            sub_result = self._execute_step(sub_step)
            if not sub_result.success:
                raise PbottlerpaError("E005", f"条件分支步骤失败: {sub_result.error}")
            branch_result = sub_result.data

        return branch_result

    def _handle_loop(self, step: Dict[str, Any]) -> Any:
        """循环步骤。"""
        items = step.get("items", [])
        item_var = step.get("item_var", "item")
        body = step.get("body", [])

        # 如果 items 是变量引用
        if isinstance(items, str) and items.startswith("$"):
            items = self._variables.get(items[1:], [])

        if not isinstance(items, list):
            raise PbottlerpaError("E001", "循环项必须是列表")

        results = []
        for item in items:
            # 设置循环变量
            self._variables[item_var] = item

            # 执行循环体
            for sub_step in body:
                sub_result = self._execute_step(sub_step)
                if not sub_result.success:
                    raise PbottlerpaError("E005", f"循环体步骤失败: {sub_result.error}")
                results.append(sub_result.data)

        return results

    def _handle_delay(self, step: Dict[str, Any]) -> Any:
        """延迟步骤。"""
        seconds = step.get("seconds", 0)
        if seconds < 0:
            raise PbottlerpaError("E001", "延迟秒数不能为负数")
        time.sleep(seconds)
        return f"delayed_{seconds}s"

    def _handle_log(self, step: Dict[str, Any]) -> Any:
        """日志步骤。"""
        message = step.get("message", "")
        # 变量替换
        message = self._replace_variables(message)
        print(f"[LOG] {message}")
        return message

    def _handle_set_variable(self, step: Dict[str, Any]) -> Any:
        """设置变量步骤。"""
        name = step.get("name", "")
        value = step.get("value")

        if not name:
            raise PbottlerpaError("E001", "设置变量步骤缺少变量名")

        # 变量引用解析
        if isinstance(value, str) and value.startswith("$"):
            value = self._variables.get(value[1:])

        self._variables[name] = value
        return value

    # ---- 辅助方法 ----

    def _replace_variables(self, text: str) -> str:
        """替换文本中的变量引用（$var 或 ${var}）。"""
        if not isinstance(text, str):
            return str(text)

        def replace_match(match):
            var_name = match.group(1) or match.group(2)
            if var_name in self._variables:
                return str(self._variables[var_name])
            return match.group(0)

        pattern = r"\$(\w+)|\$\{(\w+)\}"
        return re.sub(pattern, replace_match, text)


# ============================================================
# 流程定义校验器
# ============================================================
def validate_flow(flow: Dict[str, Any]) -> None:
    """校验流程定义是否合法。"""
    if not isinstance(flow, dict):
        raise PbottlerpaError("E002", "流程定义必须是字典类型")

    if "steps" not in flow or not isinstance(flow["steps"], list):
        raise PbottlerpaError("E002", "流程必须包含 steps 列表")

    if len(flow["steps"]) == 0:
        raise PbottlerpaError("E002", "流程步骤不能为空")

    for i, step in enumerate(flow["steps"]):
        if not isinstance(step, dict):
            raise PbottlerpaError("E002", f"第 {i + 1} 个步骤必须是字典类型")

        if "type" not in step:
            raise PbottlerpaError("E003", f"第 {i + 1} 个步骤缺少 type 字段")

        step_type = step["type"]
        if step_type not in ("http_request", "extract", "transform", "condition", "loop", "delay", "log", "set_variable"):
            raise PbottlerpaError("E003", f"不支持的步骤类型: {step_type}")


# ============================================================
# 自测模块（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    内置自测逻辑，使用硬编码样例数据离线验证核心功能。

    返回 0 表示通过，非 0 表示失败。
    """
    print("=" * 60)
    print("pbottlerpa 自测开始")
    print("=" * 60)

    # ---- 测试 1: 数据提取函数 ----
    print("\n[测试 1] 数据提取函数")
    test_data = {
        "user": {
            "name": "张三",
            "age": 30,
            "contacts": [
                {"type": "email", "value": "zhangsan@example.com"},
                {"type": "phone", "value": "13800138000"},
            ],
        },
        "orders": [{"id": 1001, "total": 299.5}, {"id": 1002, "total": 159.0}],
    }

    # 提取用户名
    name = _extract_by_selector(test_data, "$.user.name")
    assert name == "张三", f"提取用户名失败: {name}"

    # 提取第一个联系人邮箱
    email = _extract_by_selector(test_data, "$.user.contacts[0].value")
    assert email == "zhangsan@example.com", f"提取邮箱失败: {email}"

    # 正则提取
    text = "订单号: ABC-12345, 金额: 299.5"
    order_id = _extract_by_selector(text, "regex:ABC-\\d+")
    assert order_id == "ABC-12345", f"正则提取失败: {order_id}"

    # 提取不存在的键
    missing = _extract_by_selector(test_data, "$.user.nonexistent")
    assert missing is None, "提取不存在的键应返回 None"

    print("  ✓ 数据提取测试通过")

    # ---- 测试 2: URL 校验 ----
    print("\n[测试 2] URL 校验")
    assert _is_valid_url("https://example.com/path") is True
    assert _is_valid_url("http://example.com") is True
    assert _is_valid_url("ftp://example.com") is False
    assert _is_valid_url("not a url") is False
    print("  ✓ URL 校验测试通过")

    # ---- 测试 3: 流程执行引擎 ----
    print("\n[测试 3] 流程执行引擎")

    # 创建模拟 HTTP 客户端
    def mock_http_client(method, url, **kwargs):
        """模拟 HTTP 响应。"""
        if "api.example.com" in url:
            return {
                "ok": True,
                "status": 200,
                "data": {
                    "code": 0,
                    "data": {
                        "items": [
                            {"id": 1, "name": "商品A", "price": 99.9},
                            {"id": 2, "name": "商品B", "price": 199.9},
                            {"id": 3, "name": "商品C", "price": 299.9},
                        ],
                        "total": 3,
                    },
                    "message": "success",
                },
            }
        return {"ok": False, "status": 404, "data": None}

    engine = FlowEngine(http_client=mock_http_client)

    # 定义测试流程
    test_flow = {
        "name": "自测流程",
        "steps": [
            {
                "id": "step1",
                "type": "http_request",
                "method": "GET",
                "url": "https://api.example.com/products",
                "output": "api_response",
            },
            {
                "id": "step2",
                "type": "extract",
                "source": "$api_response",
                "selector": "$.data.items",
                "output": "items",
            },
            {
                "id": "step3",
                "type": "transform",
                "source": "$items",
                "transform": "json_stringify",
                "output": "items_json",
            },
            {
                "id": "step4",
                "type": "set_variable",
                "name": "item_count",
                "value": 3,
            },
            {
                "id": "step5",
                "type": "condition",
                "variable": "$item_count",
                "operator": ">=",
                "value": 2,
                "then": [
                    {
                        "id": "step5a",
                        "type": "log",
                        "message": "商品数量满足要求: $item_count",
                    }
                ],
            },
        ],
    }

    # 执行流程
    result = engine.execute(test_flow)

    # 验证结果
    assert result.success is True, f"流程执行失败: {result.error}"
    assert len(result.steps) == 5, f"步骤数量不正确: {len(result.steps)}"

    # 验证提取的数据
    items = result.steps[1].data
    assert isinstance(items, list), "提取结果应为列表"
    assert len(items) == 3, f"商品数量应为 3，实际: {len(items)}"

    # 验证转换后的 JSON
    items_json = result.steps[2].data
    parsed = json.loads(items_json)
    assert len(parsed) == 3, "JSON 转换后数据不正确"

    # 验证条件判断
    assert result.steps[4].success is True, "条件判断步骤失败"

    print("  ✓ 流程执行引擎测试通过")

    # ---- 测试 4: 错误处理 ----
    print("\n[测试 4] 错误处理")

    # 无效流程
    try:
        validate_flow({"name": "test", "steps": []})
        assert False, "空步骤流程应抛出 E002 错误"
    except PbottlerpaError as e:
        assert e.code == "E002", f"错误码应为 E002，实际: {e.code}"

    # 不支持的步骤类型
    try:
        validate_flow({"steps": [{"type": "unknown_type"}]})
        assert False, "未知步骤类型应抛出 E003 错误"
    except PbottlerpaError as e:
        assert e.code == "E003", f"错误码应为 E003，实际: {e.code}"

    # 缺少选择器
    try:
        engine._handle_extract({"source": {"a": 1}})
        assert False, "缺少选择器应抛出 E004 错误"
    except PbottlerpaError as e:
        assert e.code == "E004", f"错误码应为 E004，实际: {e.code}"

    print("  ✓ 错误处理测试通过")

    # ---- 测试 5: 宽松阈值验证 ----
    print("\n[测试 5] 宽松阈值验证")

    # 验证步骤执行时间（只做粗略检查）
    for step in result.steps:
        assert step.duration_ms >= 0, "步骤执行时间不应为负数"
        assert step.duration_ms < 10000, "步骤执行时间不应超过 10 秒"

    # 总执行时间
    assert result.total_duration_ms > 0, "总执行时间应大于 0"
    assert result.total_duration_ms < 30000, "总执行时间不应超过 30 秒"

    # 数据数量宽松验证
    assert len(items) >= 1, "至少应有 1 个商品"
    assert len(items) <= 10, "商品数量不应超过 10"

    print("  ✓ 宽松阈值验证通过")

    # ---- 测试 6: 序列化 ----
    print("\n[测试 6] 结果序列化")
    result_dict = result.to_dict()
    assert result_dict["success"] is True
    assert "steps" in result_dict
    assert len(result_dict["steps"]) == 5

    json_str = json.dumps(result_dict, ensure_ascii=False)
    assert len(json_str) > 0, "JSON 序列化不应为空"

    print("  ✓ 序列化测试通过")

    # ---- 测试完成 ----
    print("\n" + "=" * 60)
    print("所有自测用例通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="pbottlerpa - 网页自动化与数据提取流程编排工具",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自测（使用硬编码数据，离线执行）",
    )
    parser.add_argument(
        "--flow",
        type=str,
        help="流程定义 JSON 文件路径",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="仅校验流程定义，不执行",
    )

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        return run_selftest()

    # 流程文件模式
    if args.flow:
        try:
            with open(args.flow, "r", encoding="utf-8") as f:
                flow = json.load(f)

            validate_flow(flow)

            if args.validate:
                print("流程定义校验通过 ✓")
                return 0

            engine = FlowEngine()
            result = engine.execute(flow)
            print(_safe_json_dumps(result.to_dict()))

            if not result.success:
                return 1
            return 0

        except FileNotFoundError:
            print(f"[E001] 找不到流程文件: {args.flow}", file=sys.stderr)
            return 1
        except json.JSONDecodeError as e:
            print(f"[E001] 流程文件 JSON 解析失败: {e}", file=sys.stderr)
            return 1
        except PbottlerpaError as e:
            print(str(e), file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
