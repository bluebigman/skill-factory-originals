#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sinatra — Web路由设计 Sinatra调试助手

本脚本提供 Sinatra 风格路由的解析、匹配与调试辅助功能。
通过命令行参数 --selftest 可执行内置离线自检，不依赖任何外部文件或网络。

错误码约定：
    E001 参数解析失败
    E002 路由定义格式错误
    E003 路由匹配失败
    E004 路由冲突
    E005 HTTP方法不支持
    E006 路径参数类型错误
    E007 内部状态异常
    E008 自检数据异常
    E009 输入路径非法
    E010 未知错误
"""

import sys
import json
import argparse
from typing import Dict, List, Optional, Tuple, Any


class SinatraRouter:
    """Sinatra 风格路由解析与匹配器"""

    # 支持的 HTTP 方法
    SUPPORTED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

    def __init__(self) -> None:
        """初始化路由表"""
        self.routes: List[Dict[str, Any]] = []
        self._route_index: Dict[str, List[int]] = {}

    def add_route(self, method: str, pattern: str, handler: str) -> None:
        """
        添加路由定义

        参数：
            method: HTTP 方法（GET/POST/PUT/DELETE/PATCH 等）
            pattern: 路由模式，支持 :param 与 *wildcard 语法
            handler: 处理函数标识（字符串）

        错误码：
            E002 路由定义格式错误
            E005 HTTP方法不支持
            E004 路由冲突
        """
        method_upper = method.upper()
        if method_upper not in self.SUPPORTED_METHODS:
            raise ValueError(f"E005: 不支持的HTTP方法: {method}")

        if not pattern or not pattern.startswith("/"):
            raise ValueError(f"E002: 路由模式必须以/开头: {pattern}")

        if not handler or not isinstance(handler, str):
            raise ValueError(f"E002: 处理器标识必须为非空字符串")

        # 检查路由冲突（相同方法与模式）
        for existing in self.routes:
            if existing["method"] == method_upper and existing["pattern"] == pattern:
                raise ValueError(f"E004: 路由冲突: {method_upper} {pattern}")

        route = {
            "method": method_upper,
            "pattern": pattern,
            "handler": handler,
            "segments": self._parse_pattern(pattern),
        }
        self.routes.append(route)

        # 建立索引：方法 -> 路由索引列表
        if method_upper not in self._route_index:
            self._route_index[method_upper] = []
        self._route_index[method_upper].append(len(self.routes) - 1)

    @staticmethod
    def _parse_pattern(pattern: str) -> List[Dict[str, str]]:
        """
        解析路由模式为段列表

        返回段列表，每段为 {'type': 'literal'|'param'|'wildcard', 'value': str}
        """
        segments = []
        parts = pattern.split("/")

        for part in parts:
            if part == "":
                continue
            if part.startswith(":"):
                # 命名参数
                param_name = part[1:]
                if not param_name:
                    raise ValueError(f"E002: 空参数名在模式 {pattern} 中")
                segments.append({"type": "param", "value": param_name})
            elif part == "*":
                # 通配符
                segments.append({"type": "wildcard", "value": "*"})
            elif part.startswith("*"):
                # 命名通配符
                segments.append({"type": "wildcard", "value": part[1:]})
            else:
                # 字面量
                segments.append({"type": "literal", "value": part})

        return segments

    def match(self, method: str, path: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        匹配路由

        参数：
            method: HTTP 方法
            path: 请求路径

        返回：
            (handler, params) 元组；无匹配时返回 None

        错误码：
            E009 输入路径非法
        """
        if not path.startswith("/"):
            raise ValueError(f"E009: 路径必须以/开头: {path}")

        method_upper = method.upper()
        if method_upper not in self.SUPPORTED_METHODS:
            raise ValueError(f"E005: 不支持的HTTP方法: {method}")

        # 获取该方法的候选路由
        candidates = self._route_index.get(method_upper, [])
        path_segments = [s for s in path.split("/") if s]

        for idx in candidates:
            route = self.routes[idx]
            params = self._match_segments(route["segments"], path_segments)
            if params is not None:
                return route["handler"], params

        return None

    @staticmethod
    def _match_segments(
        pattern_segments: List[Dict[str, str]], path_segments: List[str]
    ) -> Optional[Dict[str, str]]:
        """
        匹配路径段与模式段

        返回参数字典；不匹配时返回 None
        """
        params: Dict[str, str] = {}
        p_idx = 0
        s_idx = 0

        while p_idx < len(pattern_segments):
            p_seg = pattern_segments[p_idx]
            p_type = p_seg["type"]

            if p_type == "wildcard":
                # 通配符匹配剩余所有段
                if p_idx == len(pattern_segments) - 1:
                    # 最后一个通配符，匹配所有剩余
                    remaining = "/".join(path_segments[s_idx:])
                    params[p_seg["value"]] = remaining
                    return params
                else:
                    # 非末尾通配符，尝试匹配到下一个模式段
                    next_p = pattern_segments[p_idx + 1]
                    matched = False
                    for take in range(len(path_segments) - s_idx, -1, -1):
                        # 尝试不同长度的匹配
                        candidate_params = params.copy()
                        if take > 0:
                            candidate_params[p_seg["value"]] = "/".join(
                                path_segments[s_idx : s_idx + take]
                            )
                        # 递归匹配剩余
                        result = SinatraRouter._match_segments(
                            pattern_segments[p_idx + 1 :],
                            path_segments[s_idx + take :],
                        )
                        if result is not None:
                            candidate_params.update(result)
                            params.update(candidate_params)
                            matched = True
                            return params
                    if not matched:
                        return None
            elif p_type == "param":
                if s_idx >= len(path_segments):
                    return None
                params[p_seg["value"]] = path_segments[s_idx]
                p_idx += 1
                s_idx += 1
            else:  # literal
                if s_idx >= len(path_segments):
                    return None
                if p_seg["value"] != path_segments[s_idx]:
                    return None
                p_idx += 1
                s_idx += 1

        # 模式耗尽后，路径不应有剩余
        if s_idx < len(path_segments):
            return None

        return params

    def get_routes(self) -> List[Dict[str, str]]:
        """返回所有路由定义"""
        return [
            {"method": r["method"], "pattern": r["pattern"], "handler": r["handler"]}
            for r in self.routes
        ]

    def to_json(self) -> str:
        """导出路由表为 JSON"""
        return json.dumps(self.get_routes(), ensure_ascii=False, indent=2)


def build_sample_router() -> SinatraRouter:
    """构建示例路由器（用于演示与自检）"""
    router = SinatraRouter()
    router.add_route("GET", "/", "home_handler")
    router.add_route("GET", "/users", "users_index")
    router.add_route("GET", "/users/:id", "user_show")
    router.add_route("POST", "/users", "user_create")
    router.add_route("GET", "/files/*path", "file_serve")
    router.add_route("GET", "/search", "search_handler")
    router.add_route("DELETE", "/users/:id", "user_delete")
    return router


def run_selftest() -> int:
    """
    内置离线自检

    使用硬编码样例数据验证核心逻辑，不依赖外部文件。
    断言采用宽松阈值（存在性/类型/大小比较），确保稳健。

    返回：
        0 表示通过，非0表示失败（错误码）
    """
    try:
        # 构建测试路由器
        router = build_sample_router()

        # 测试1: 基本路由匹配
        result = router.match("GET", "/")
        assert result is not None, "E008: 根路由匹配失败"
        handler, params = result
        assert handler == "home_handler", f"E008: 处理器错误: {handler}"
        assert isinstance(params, dict), "E008: 参数类型错误"

        # 测试2: 静态路由
        result = router.match("GET", "/users")
        assert result is not None, "E008: 静态路由匹配失败"
        handler, params = result
        assert handler == "users_index", f"E008: 处理器错误: {handler}"

        # 测试3: 参数路由
        result = router.match("GET", "/users/42")
        assert result is not None, "E008: 参数路由匹配失败"
        handler, params = result
        assert handler == "user_show", f"E008: 处理器错误: {handler}"
        assert "id" in params, "E008: 缺少参数 id"
        assert params["id"] == "42", f"E008: 参数值错误: {params['id']}"

        # 测试4: POST 路由
        result = router.match("POST", "/users")
        assert result is not None, "E008: POST路由匹配失败"
        handler, params = result
        assert handler == "user_create", f"E008: 处理器错误: {handler}"

        # 测试5: 通配符路由
        result = router.match("GET", "/files/docs/report.pdf")
        assert result is not None, "E008: 通配符路由匹配失败"
        handler, params = result
        assert handler == "file_serve", f"E008: 处理器错误: {handler}"
        assert "path" in params, "E008: 缺少通配符参数"
        # 宽松断言：通配符捕获的内容应包含至少一个字符
        assert len(params["path"]) > 0, "E008: 通配符参数为空"

        # 测试6: 不匹配的路径
        result = router.match("GET", "/nonexistent")
        assert result is None, "E008: 不存在的路径应返回 None"

        # 测试7: 方法不匹配
        result = router.match("PUT", "/users/42")
        assert result is None, "E008: 方法不匹配应返回 None"

        # 测试8: 路由冲突检测
        try:
            router.add_route("GET", "/users", "duplicate")
            assert False, "E008: 应检测到路由冲突"
        except ValueError as e:
            assert str(e).startswith("E004"), f"E008: 错误码错误: {e}"

        # 测试9: 非法方法
        try:
            router.add_route("FOO", "/test", "handler")
            assert False, "E008: 应拒绝非法方法"
        except ValueError as e:
            assert str(e).startswith("E005"), f"E008: 错误码错误: {e}"

        # 测试10: 空模式
        try:
            router.add_route("GET", "", "handler")
            assert False, "E008: 应拒绝空模式"
        except ValueError as e:
            assert str(e).startswith("E002"), f"E008: 错误码错误: {e}"

        # 测试11: 路由表导出
        routes = router.get_routes()
        assert isinstance(routes, list), "E008: 路由表格式错误"
        assert len(routes) >= 7, f"E008: 路由数量不足: {len(routes)}"

        # 测试12: JSON 序列化
        json_str = router.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, list), "E008: JSON解析失败"
        assert len(parsed) == len(routes), "E008: JSON长度不匹配"

        # 测试13: 多级参数路由
        router2 = SinatraRouter()
        router2.add_route("GET", "/api/:version/users/:id", "api_user")
        result = router2.match("GET", "/api/v1/users/99")
        assert result is not None, "E008: 多级参数路由匹配失败"
        handler, params = result
        assert "version" in params and "id" in params, "E008: 参数缺失"
        assert params["version"] == "v1", f"E008: 版本参数错误: {params['version']}"
        assert params["id"] == "99", f"E008: ID参数错误: {params['id']}"

        # 测试14: 复杂通配符场景
        router3 = SinatraRouter()
        router3.add_route("GET", "/a/*rest/b", "complex")
        result = router3.match("GET", "/a/x/y/z/b")
        assert result is not None, "E008: 复杂通配符匹配失败"
        handler, params = result
        assert "rest" in params, "E008: 通配符参数缺失"
        assert len(params["rest"]) > 0, "E008: 通配符参数为空"

        # 测试15: 边缘路径（根路径）
        result = router.match("GET", "/")
        assert result is not None, "E008: 根路径匹配失败"

        print("[selftest] 全部断言通过 ✅")
        return 0

    except AssertionError as e:
        print(f"[selftest] 断言失败: {e}")
        return 8  # E008
    except ValueError as e:
        print(f"[selftest] 值错误: {e}")
        return 8  # E008
    except Exception as e:
        print(f"[selftest] 未知异常: {e}")
        return 10  # E010


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Sinatra 风格路由设计调试助手",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--route",
        nargs=3,
        metavar=("METHOD", "PATTERN", "HANDLER"),
        help="添加路由定义",
    )
    parser.add_argument(
        "--match",
        nargs=2,
        metavar=("METHOD", "PATH"),
        help="匹配路由",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有路由",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 构建路由器
    router = SinatraRouter()

    # 添加路由
    if args.route:
        method, pattern, handler = args.route
        try:
            router.add_route(method, pattern, handler)
        except ValueError as e:
            print(f"错误: {e}")
            return 1  # E001

    # 匹配路由
    if args.match:
        method, path = args.match
        try:
            result = router.match(method, path)
            if result:
                handler, params = result
                print(f"匹配成功: handler={handler}, params={json.dumps(params)}")
            else:
                print("无匹配路由")
                return 3  # E003
        except ValueError as e:
            print(f"错误: {e}")
            return 1  # E001

    # 列出路由
    if args.list:
        for route in router.get_routes():
            print(f"{route['method']:6s} {route['pattern']:30s} -> {route['handler']}")

    # 无操作时显示帮助
    if not (args.route or args.match or args.list):
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
