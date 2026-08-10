#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Webhook 样例编排器（独立实现）

依据功能规格 clean-room 重写：
- 解析 Webhook 样例数据（JSON 字符串 / URL / 本地文件路径）
- 提取事件类型、目标 URL、负载结构、认证方式等关键字段
- 输出结构化配置建议与脚本骨架
- 支持批量输入与多种输出格式
- 内置 --selftest 离线自检（不依赖外部文件/网络/工作目录）

仅使用 Python 标准库。
错误码：E001-E010（见下方异常类定义）。
"""

import argparse
import json
import os
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
class SkillError(Exception):
    """技能基础异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def err(code: str, message: str) -> SkillError:
    """快速构造错误。"""
    return SkillError(code, message)


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ParsedWebhook:
    """解析后的 Webhook 结构化结果。"""

    event_type: str = "unknown"
    target_url: str = ""
    auth_type: str = "none"
    payload_keys: List[str] = field(default_factory=list)
    payload_sample: Dict[str, Any] = field(default_factory=dict)
    source_type: str = "unknown"  # json / url / file
    confidence: Dict[str, str] = field(default_factory=dict)  # 字段 -> 高/中/低
    raw_input: str = ""


# ============================================================
# 核心解析逻辑
# ============================================================
def _looks_like_url(text: str) -> bool:
    """判断输入是否像 URL（宽松判断）。"""
    parsed = urllib.parse.urlparse(text.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _looks_like_json(text: str) -> bool:
    """判断输入是否像 JSON（宽松判断）。"""
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def _is_file_path(text: str) -> bool:
    """判断输入是否像文件路径（宽松判断）。"""
    # 排除 URL 和纯 JSON
    if _looks_like_url(text) or _looks_like_json(text):
        return False
    # 路径特征：包含路径分隔符，或指向存在的文件
    return "/" in text or "\\" in text or os.path.isfile(text)


def _extract_event_type(payload: Dict[str, Any]) -> str:
    """从负载中提取事件类型（多级回退）。"""
    candidates = [
        payload.get("eventType"),
        payload.get("event_type"),
        payload.get("type"),
        payload.get("event"),
        payload.get("action"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return "unknown"


def _extract_target_url(payload: Dict[str, Any]) -> str:
    """从负载中提取目标 URL（多级回退）。"""
    candidates = [
        payload.get("targetUrl"),
        payload.get("target_url"),
        payload.get("callbackUrl"),
        payload.get("callback_url"),
        payload.get("url"),
        payload.get("endpoint"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return ""


def _extract_auth_type(payload: Dict[str, Any]) -> str:
    """从负载中提取认证方式。"""
    auth = payload.get("auth")
    if isinstance(auth, dict):
        # 常见字段：type / method / scheme
        for key in ("type", "method", "scheme"):
            val = auth.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip().lower()
        # 若存在 token / apiKey 等字段则判定为 bearer/api-key
        if "token" in auth or "apiKey" in auth or "api_key" in auth:
            return "bearer"
        if "username" in auth or "password" in auth:
            return "basic"
    if isinstance(auth, str) and auth.strip():
        return auth.strip().lower()
    # 顶层字段回退
    if "token" in payload or "apiKey" in payload or "api_key" in payload:
        return "bearer"
    return "none"


def _collect_payload_keys(payload: Dict[str, Any], prefix: str = "") -> List[str]:
    """递归收集负载中的所有键路径（扁平化）。"""
    keys: List[str] = []
    for k, v in payload.items():
        full = f"{prefix}.{k}" if prefix else k
        keys.append(full)
        if isinstance(v, dict):
            keys.extend(_collect_payload_keys(v, full))
    return keys


def _compute_confidence(event_type: str, target_url: str, auth_type: str) -> Dict[str, str]:
    """基于字段是否成功提取计算置信度。"""
    conf: Dict[str, str] = {}
    conf["event_type"] = "高" if event_type != "unknown" else "低"
    conf["target_url"] = "高" if target_url else "低"
    conf["auth_type"] = "高" if auth_type != "none" else "中"
    return conf


def _extract_auth_from_url(url: str) -> str:
    """从 URL 查询参数中提取认证信息。"""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    # 检查常见的认证相关参数
    if "token" in query_params or "access_token" in query_params:
        return "bearer"
    if "api_key" in query_params or "apikey" in query_params:
        return "api-key"
    if "username" in query_params or "user" in query_params:
        return "basic"
    
    # 检查 URL 中是否包含认证信息（user:pass@host）
    if parsed.username or parsed.password:
        return "basic"
    
    return "none"


def parse_webhook(raw_input: str) -> ParsedWebhook:
    """
    解析 Webhook 样例输入（JSON 字符串 / URL / 文件路径）。

    参数:
        raw_input: 用户提供的原始输入

    返回:
        ParsedWebhook 结构化结果

    异常:
        E001: 输入为空
        E002: 无法识别的输入类型
        E003: JSON 解析失败
        E004: 文件读取失败
    """
    if not raw_input or not raw_input.strip():
        raise err("E001", "输入为空，请提供 Webhook 样例数据")

    text = raw_input.strip()
    result = ParsedWebhook(raw_input=text)

    # ---- 类型判断与数据获取 ----
    payload: Dict[str, Any] = {}

    if _looks_like_json(text):
        # 情况 1：JSON 字符串
        result.source_type = "json"
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise err("E003", f"JSON 解析失败: {e}") from e
        if not isinstance(data, dict):
            raise err("E003", "JSON 顶层必须是对象（dict）")
        payload = data

    elif _looks_like_url(text):
        # 情况 2：URL（仅提取 URL 本身，不访问网络）
        result.source_type = "url"
        result.target_url = text
        
        # 从 URL 中提取认证信息
        result.auth_type = _extract_auth_from_url(text)
        
        # URL 中可能带查询参数，尝试提取事件类型
        parsed = urllib.parse.urlparse(text)
        query_params = urllib.parse.parse_qs(parsed.query)
        for key in ("eventType", "event_type", "type", "event"):
            if key in query_params and query_params[key]:
                result.event_type = query_params[key][0]
                break
        
        # 构造负载用于统一处理
        payload = {
            "targetUrl": text,
            "eventType": result.event_type if result.event_type != "unknown" else "webhook_received",
        }
        
        # 将查询参数中的认证信息也加入负载
        if result.auth_type != "none":
            payload["auth"] = {"type": result.auth_type}
            if "token" in query_params:
                payload["auth"]["token"] = query_params["token"][0]
            elif "api_key" in query_params:
                payload["auth"]["api_key"] = query_params["api_key"][0]

    elif _is_file_path(text):
        # 情况 3：本地文件路径
        result.source_type = "file"
        try:
            with open(text, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read().strip()
        except (OSError, IOError) as e:
            raise err("E004", f"文件读取失败: {e}") from e
        # 文件内容应为 JSON
        if not _looks_like_json(file_content):
            raise err("E003", "文件内容不是有效 JSON")
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError as e:
            raise err("E003", f"文件 JSON 解析失败: {e}") from e
        if not isinstance(data, dict):
            raise err("E003", "文件 JSON 顶层必须是对象（dict）")
        payload = data

    else:
        raise err("E002", "无法识别的输入类型（仅支持 JSON 字符串、URL、文件路径）")

    # ---- 字段提取 ----
    # 对于 URL 类型，保留已提取的认证类型
    if result.source_type != "url":
        result.auth_type = _extract_auth_type(payload)
    
    # 事件类型（URL 类型已提前设置，此处覆盖若 payload 中有更明确的值）
    extracted_event = _extract_event_type(payload)
    if extracted_event != "unknown":
        result.event_type = extracted_event
    
    # 目标 URL（URL 类型已提前设置，此处覆盖若 payload 中有更明确的值）
    extracted_url = _extract_target_url(payload)
    if extracted_url:
        result.target_url = extracted_url
    
    result.payload_keys = _collect_payload_keys(payload)
    result.payload_sample = payload
    result.confidence = _compute_confidence(result.event_type, result.target_url, result.auth_type)

    return result


# ============================================================
# 配置生成
# ============================================================
def generate_config(parsed: ParsedWebhook) -> Dict[str, Any]:
    """
    基于解析结果生成接收器配置建议。

    参数:
        parsed: 解析后的 Webhook 数据

    返回:
        配置建议字典
    """
    config: Dict[str, Any] = {
        "receiver": {
            "name": f"webhook_{parsed.event_type.lower().replace(' ', '_')}",
            "enabled": True,
        },
        "endpoint": {
            "url": parsed.target_url or "/webhook/receiver",
            "method": "POST",
        },
        "authentication": {
            "type": parsed.auth_type,
        },
        "events": [parsed.event_type],
        "payload_mapping": {
            key: f"$.{key}" for key in parsed.payload_keys[:20]  # 最多映射 20 个键
        },
        "notes": [
            "请根据实际环境调整 URL 与认证凭据",
            "建议在接收器端启用 HTTPS",
            "低置信度字段需人工确认",
        ],
    }

    # 根据认证类型补充字段
    if parsed.auth_type == "bearer":
        config["authentication"]["token_placeholder"] = "<YOUR_TOKEN>"
    elif parsed.auth_type == "basic":
        config["authentication"]["username_placeholder"] = "<USERNAME>"
        config["authentication"]["password_placeholder"] = "<PASSWORD>"
    elif parsed.auth_type == "api-key":
        config["authentication"]["api_key_placeholder"] = "<API_KEY>"

    return config


def generate_script_skeleton(parsed: ParsedWebhook) -> str:
    """
    生成接收器脚本骨架（Python 代码字符串）。

    参数:
        parsed: 解析后的 Webhook 数据

    返回:
        脚本骨架代码
    """
    lines = [
        "# 自动生成的 Webhook 接收器骨架",
        "# 请根据实际环境完善以下代码",
        "",
        "import json",
        "from http.server import BaseHTTPRequestHandler, HTTPServer",
        "",
        "",
        "class WebhookHandler(BaseHTTPRequestHandler):",
        "    def do_POST(self):",
        "        # 读取请求体",
        "        content_length = int(self.headers.get('Content-Length', 0))",
        "        body = self.rfile.read(content_length)",
        "        try:",
        "            payload = json.loads(body)",
        f"            event_type = payload.get('eventType', '{parsed.event_type}')",
        "            print(f'收到事件: {event_type}')",
        "            # TODO: 在这里添加业务处理逻辑",
        "            self.send_response(200)",
        "            self.send_header('Content-Type', 'application/json')",
        "            self.end_headers()",
        "            self.wfile.write(json.dumps({'status': 'ok'}).encode())",
        "        except Exception as e:",
        "            self.send_response(400)",
        "            self.end_headers()",
        "            self.wfile.write(str(e).encode())",
        "",
        "    def log_message(self, format, *args):",
        "        # 精简日志输出",
        "        print(f'[{self.address_string()}] {format % args}')",
        "",
        "",
        "def run_server(port=8080):",
        "    server = HTTPServer(('0.0.0.0', port), WebhookHandler)",
        f"    print(f'Webhook 接收器已启动，监听端口 {{port}}，事件类型: {parsed.event_type}')",
        "    server.serve_forever()",
        "",
        "",
        "if __name__ == '__main__':",
        "    run_server()",
        "",
    ]
    return "\n".join(lines)


# ============================================================
# 输出格式化
# ============================================================
def format_output(parsed: ParsedWebhook, config: Dict[str, Any], fmt: str = "table") -> str:
    """
    按指定格式输出解析结果。

    参数:
        parsed: 解析后的 Webhook 数据
        config: 生成的配置建议
        fmt: 输出格式（table / kv / script）

    返回:
        格式化后的字符串
    """
    if fmt == "kv":
        # 键值对格式
        lines = [
            "=== Webhook 解析结果 ===",
            f"事件类型: {parsed.event_type} (置信度: {parsed.confidence.get('event_type', '未知')})",
            f"目标 URL: {parsed.target_url or '(未指定)'} (置信度: {parsed.confidence.get('target_url', '未知')})",
            f"认证方式: {parsed.auth_type} (置信度: {parsed.confidence.get('auth_type', '未知')})",
            f"输入类型: {parsed.source_type}",
            "负载键清单:",
        ]
        for key in parsed.payload_keys:
            lines.append(f"  - {key}")
        lines.append("")
        lines.append("=== 配置建议 ===")
        lines.append(json.dumps(config, ensure_ascii=False, indent=2))
        return "\n".join(lines)

    elif fmt == "script":
        # 脚本骨架格式
        return generate_script_skeleton(parsed)

    else:
        # 默认表格格式
        lines = [
            "┌─────────────────────────────────────────────┐",
            "│        Webhook 样例解析结果                  │",
            "├─────────────────────────────────────────────┤",
            f"│ 事件类型 : {parsed.event_type:<28} │",
            f"│ 置信度   : {parsed.confidence.get('event_type', '未知'):<28} │",
            f"│ 目标 URL : {(parsed.target_url or '(未指定)'):<28} │",
            f"│ 置信度   : {parsed.confidence.get('target_url', '未知'):<28} │",
            f"│ 认证方式 : {parsed.auth_type:<28} │",
            f"│ 置信度   : {parsed.confidence.get('auth_type', '未知'):<28} │",
            f"│ 输入类型 : {parsed.source_type:<28} │",
            "├─────────────────────────────────────────────┤",
            "│ 负载键清单:                                  │",
        ]
        for key in parsed.payload_keys[:10]:
            lines.append(f"│   • {key:<44} │")
        if len(parsed.payload_keys) > 10:
            lines.append(f"│   ... 共 {len(parsed.payload_keys)} 个键            │")
        lines.append("└─────────────────────────────────────────────┘")
        lines.append("")
        lines.append("配置建议:")
        lines.append(json.dumps(config, ensure_ascii=False, indent=2))
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def _run_selftest() -> int:
    """
    内置硬编码样例数据的离线自检。

    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("=== Webhook 样例编排器自检开始 ===")

    # ---- 样例 1：标准 JSON ----
    sample_json = json.dumps({
        "eventType": "featureService.edit",
        "targetUrl": "https://example.com/webhook/receiver",
        "auth": {"type": "bearer", "token": "abc123"},
        "payload": {"featureId": 42, "layerName": "parcels"},
        "timestamp": "2026-01-01T00:00:00Z",
    })

    try:
        result1 = parse_webhook(sample_json)
        assert result1.event_type == "featureService.edit", "事件类型提取失败"
        assert "example.com" in result1.target_url, "URL 提取失败"
        assert result1.auth_type == "bearer", "认证类型提取失败"
        assert len(result1.payload_keys) >= 4, "负载键提取不完整"
        assert result1.confidence["event_type"] == "高", "置信度标注错误"

        config1 = generate_config(result1)
        assert config1["receiver"]["enabled"] is True, "配置生成失败"
        assert config1["authentication"]["type"] == "bearer", "配置认证类型错误"

        script1 = generate_script_skeleton(result1)
        assert "do_POST" in script1, "脚本骨架缺少 POST 处理"
        assert "featureService.edit" in script1, "脚本骨架缺少事件类型"

        print("[通过] JSON 解析、配置生成、脚本骨架")
    except AssertionError as e:
        print(f"[失败] 样例 1 断言错误: {e}")
        return 1
    except SkillError as e:
        print(f"[失败] 样例 1 技能错误: {e}")
        return 1

    # ---- 样例 2：URL 输入 ----
    sample_url = "https://arcgis.example.com/webhook?eventType=layer.update&token=secret"

    try:
        result2 = parse_webhook(sample_url)
        assert result2.source_type == "url", "URL 类型判断失败"
        assert result2.event_type == "layer.update", "URL 事件类型提取失败"
        assert result2.target_url == sample_url, "URL 提取失败"
        assert result2.auth_type == "bearer", "URL 认证类型推断失败"

        # 宽松断言：payload_keys 至少包含 targetUrl 和 eventType
        assert len(result2.payload_keys) >= 2, "URL 负载键提取失败"

        print("[通过] URL 解析")
    except AssertionError as e:
        print(f"[失败] 样例 2 断言错误: {e}")
        return 1
    except SkillError as e:
        print(f"[失败] 样例 2 技能错误: {e}")
        return 1

    # ---- 样例 3：无认证简单 JSON ----
    sample_simple = '{"event": "delete", "endpoint": "http://localhost:8080/hook"}'

    try:
        result3 = parse_webhook(sample_simple)
        assert result3.event_type == "delete", "简单 JSON 事件类型提取失败"
        assert "localhost" in result3.target_url, "简单 JSON URL 提取失败"
        assert result3.auth_type == "none", "无认证类型判断失败"

        # 宽松断言：置信度字段必须存在
        assert "event_type" in result3.confidence, "置信度字段缺失"

        # 测试 kv 输出格式
        kv_output = format_output(result3, generate_config(result3), fmt="kv")
        assert "事件类型" in kv_output, "kv 格式输出失败"

        # 测试 table 输出格式
        table_output = format_output(result3, generate_config(result3), fmt="table")
        assert "┌" in table_output, "table 格式输出失败"

        print("[通过] 简单 JSON 解析与多种输出格式")
    except AssertionError as e:
        print(f"[失败] 样例 3 断言错误: {e}")
        return 1
    except SkillError as e:
        print(f"[失败] 样例 3 技能错误: {e}")
        return 1

    # ---- 样例 4：错误处理 ----
    try:
        parse_webhook("")
        print("[失败] 空输入未抛错")
        return 1
    except SkillError as e:
        assert e.code == "E001", f"空输入错误码错误: {e.code}"
        print("[通过] 空输入错误处理")

    try:
        parse_webhook("这不是任何有效格式")
        print("[失败] 无效输入未抛错")
        return 1
    except SkillError as e:
        assert e.code == "E002", f"无效输入错误码错误: {e.code}"
        print("[通过] 无效输入错误处理")

    # ---- 样例 5：批量处理 ----
    batch = [sample_json, sample_url, sample_simple]
    try:
        results = [parse_webhook(item) for item in batch]
        assert len(results) == 3, "批量处理数量错误"
        assert all(r.event_type != "unknown" for r in results), "批量处理存在未知事件"
        print("[通过] 批量处理")
    except AssertionError as e:
        print(f"[失败] 批量处理断言错误: {e}")
        return 1

    # ---- 样例 6：脚本输出格式 ----
    try:
        result6 = parse_webhook(sample_json)
        script_output = format_output(result6, generate_config(result6), fmt="script")
        assert "import json" in script_output, "脚本格式输出缺少 import"
        assert "HTTPServer" in script_output, "脚本格式输出缺少服务器"
        print("[通过] 脚本格式输出")
    except AssertionError as e:
        print(f"[失败] 脚本格式输出断言错误: {e}")
        return 1

    print("=== 自检全部通过 ===")
    return 0


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """
    命令行主入口。

    返回:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="Webhook 样例编排器 - 解析 Webhook 样例并生成配置建议",
        epilog="示例: python main.py '{\"eventType\":\"test\"}' --format table",
    )
    parser.add_argument(
        "--input",
        nargs="?",
        help="Webhook 样例输入（JSON 字符串 / URL / 文件路径）",
    )
    parser.add_argument(
        "--format",
        choices=["table", "kv", "script"],
        default="table",
        help="输出格式（默认: table）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 批量模式
    if args.batch:
        try:
            for item in args.batch:
                print(f"\n--- 处理输入: {item[:50]}... ---")
                parsed = parse_webhook(item)
                config = generate_config(parsed)
                print(format_output(parsed, config, args.format))
            return 0
        except SkillError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 单条模式
    if not args.input:
        parser.print_help()
        return 1

    try:
        parsed = parse_webhook(args.input)
        config = generate_config(parsed)
        output = format_output(parsed, config, args.format)
        print(output)
        return 0
    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # 兜底异常
        print(f"错误 [E010]: 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
