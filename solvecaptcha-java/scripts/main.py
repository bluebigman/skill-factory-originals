#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
solvecaptcha-java 技能辅助脚本
================================
提供验证码识别 Java 客户端的辅助功能：
  - 解析验证码识别请求参数
  - 模拟验证码识别结果（离线、无网络）
  - 提供 Java 代码片段生成
  - 内置 --selftest 自检模式

本脚本仅依据功能规格独立实现（clean-room），不包含任何既有代码。
错误码约定：E001~E010
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
VERSION = "1.0.5"
SLUG = "solvecaptcha-java"
DISPLAY_NAME = "验证码识别 Java 自动化辅助"

# 支持的行为验证类型
SUPPORTED_TYPES = [
    "image",          # 图形验证码
    "recaptcha",      # Google reCAPTCHA
    "hcaptcha",       # hCaptcha
    "funcaptcha",     # FunCaptcha
    "geetest",        # 极验
    "turnstile",      # Cloudflare Turnstile
]

# 错误码与消息映射
ERROR_MESSAGES = {
    "E001": "参数缺失或为空",
    "E002": "验证码类型不支持",
    "E003": "图片数据格式无效（仅支持 base64 或 URL）",
    "E004": "配置项非法（sitekey / pageurl 缺失）",
    "E005": "超时时间超出允许范围",
    "E006": "代理配置格式错误",
    "E007": "内部处理失败",
    "E008": "自检断言失败",
    "E009": "输入 JSON 解析失败",
    "E010": "未知错误",
}


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------
def error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误返回结构。"""
    msg = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
    result = {"success": False, "error_code": code, "error_message": msg}
    if detail:
        result["detail"] = detail
    return result


def success(data: Any = None) -> Dict[str, Any]:
    """构造标准成功返回结构。"""
    return {"success": True, "data": data}


def normalize_type(captcha_type: str) -> Optional[str]:
    """规范化验证码类型（支持别名）。"""
    if not captcha_type:
        return None
    t = captcha_type.strip().lower()
    # 别名映射
    alias_map = {
        "img": "image",
        "图片": "image",
        "图形": "image",
        "recaptchav2": "recaptcha",
        "recaptchav3": "recaptcha",
        "rc": "recaptcha",
        "hc": "hcaptcha",
        "fc": "funcaptcha",
        "gt": "geetest",
        "极验": "geetest",
        "ts": "turnstile",
        "cf": "turnstile",
    }
    if t in alias_map:
        t = alias_map[t]
    if t in SUPPORTED_TYPES:
        return t
    return None


def validate_timeout(timeout: Any) -> Tuple[bool, int]:
    """校验超时时间，返回 (是否有效, 规范化值)。"""
    try:
        val = int(timeout)
    except (TypeError, ValueError):
        return False, 0
    if val < 5 or val > 300:
        return False, val
    return True, val


def parse_proxy(proxy: Any) -> Tuple[bool, str]:
    """解析代理配置，返回 (是否有效, 规范化代理串)。"""
    if proxy is None or proxy == "":
        return True, ""
    if not isinstance(proxy, str):
        return False, ""
    # 支持格式: http://user:pass@host:port 或 host:port
    pattern = re.compile(
        r"^(https?://)?([^:@/]+)(:([^@/]+))?@([^:/]+):(\d+)$"
    )
    pattern2 = re.compile(r"^([^:/]+):(\d+)$")
    if pattern.match(proxy) or pattern2.match(proxy):
        return True, proxy
    return False, proxy


def validate_image_input(image_data: str) -> Tuple[bool, str]:
    """校验图片输入（base64 或 URL）。"""
    if not image_data or not isinstance(image_data, str):
        return False, ""
    s = image_data.strip()
    # base64 常见特征
    if re.match(r"^[A-Za-z0-9+/=\s]+$", s) and len(s) > 50:
        return True, "base64"
    # URL 特征
    if s.startswith(("http://", "https://", "data:image/")):
        return True, "url"
    return False, ""


# ---------------------------------------------------------------------------
# 核心逻辑函数
# ---------------------------------------------------------------------------
def parse_request(raw_input: str) -> Dict[str, Any]:
    """
    解析验证码识别请求参数。
    支持 JSON 字符串或 key=value&key=value 格式。
    """
    if not raw_input:
        return error("E001")

    # 尝试 JSON 解析
    if raw_input.strip().startswith("{"):
        try:
            data = json.loads(raw_input)
            if not isinstance(data, dict):
                return error("E001", "JSON 根节点必须是对象")
            return {"success": True, "params": data}
        except json.JSONDecodeError as e:
            return error("E009", f"JSON 解析失败: {e}")

    # 尝试 key=value 格式
    params: Dict[str, str] = {}
    for pair in raw_input.split("&"):
        if "=" not in pair:
            continue
        k, _, v = pair.partition("=")
        params[k.strip()] = v.strip()
    if not params:
        return error("E001", "无法解析请求参数")
    return {"success": True, "params": params}


def build_solve_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    构建标准验证码识别请求。
    返回结构包含 task 与 options 两部分。
    """
    if not params or not isinstance(params, dict):
        return error("E001")

    # 提取并校验验证码类型
    captcha_type = params.get("type") or params.get("captcha_type") or params.get("method")
    norm_type = normalize_type(captcha_type)
    if not norm_type:
        return error("E002", f"不支持的验证码类型: {captcha_type}")

    # 构建基础 task
    task: Dict[str, Any] = {
        "type": norm_type,
        "client_key": params.get("client_key") or params.get("api_key") or "",
    }

    # 根据类型添加必要字段
    if norm_type == "image":
        img = params.get("image") or params.get("image_base64") or params.get("image_url") or ""
        valid, kind = validate_image_input(img)
        if not valid:
            return error("E003", "图片数据格式无效")
        task["image"] = img
        task["image_type"] = kind
        # 可选参数
        if "phrase" in params:
            task["phrase"] = bool(params["phrase"])
        if "case_sensitive" in params:
            task["case_sensitive"] = bool(params["case_sensitive"])
        if "numeric" in params:
            task["numeric"] = int(params["numeric"])
        if "min_length" in params:
            task["min_length"] = int(params["min_length"])
        if "max_length" in params:
            task["max_length"] = int(params["max_length"])
    else:
        # 行为验证类需要 sitekey 和 pageurl
        sitekey = params.get("sitekey") or params.get("site_key") or ""
        pageurl = params.get("pageurl") or params.get("page_url") or params.get("url") or ""
        if not sitekey or not pageurl:
            return error("E004", "sitekey 与 pageurl 为必填项")
        task["sitekey"] = sitekey
        task["pageurl"] = pageurl
        # 可选参数
        if "data_s" in params:
            task["data_s"] = params["data_s"]
        if "invisible" in params:
            task["invisible"] = bool(params["invisible"])
        if "domain" in params:
            task["domain"] = params["domain"]
        if "user_agent" in params:
            task["user_agent"] = params["user_agent"]

    # 构建 options
    options: Dict[str, Any] = {}

    # 超时时间
    timeout = params.get("timeout", 60)
    valid_t, norm_t = validate_timeout(timeout)
    if not valid_t:
        return error("E005", f"超时时间 {timeout} 超出范围 [5, 300]")
    options["timeout"] = norm_t

    # 代理
    proxy = params.get("proxy", "")
    valid_p, norm_p = parse_proxy(proxy)
    if not valid_p:
        return error("E006", f"代理格式错误: {proxy}")
    if norm_p:
        options["proxy"] = norm_p

    # 其他可选配置
    if "lang" in params:
        options["lang"] = str(params["lang"])
    if "soft_id" in params:
        options["soft_id"] = str(params["soft_id"])
    if "callback" in params:
        options["callback"] = str(params["callback"])

    return success({"task": task, "options": options})


def simulate_solve(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    模拟验证码识别过程（离线）。
    返回与真实服务一致的伪随机结果，用于测试与演示。
    """
    if not request.get("success"):
        return request

    task = request["data"]["task"]
    options = request["data"]["options"]
    captcha_type = task.get("type", "image")

    # 生成伪识别文本
    seed_str = f"{captcha_type}:{task.get('sitekey', '')}:{task.get('image', '')}"
    seed = hashlib.sha256(seed_str.encode("utf-8")).hexdigest()

    # 根据类型生成结果
    if captcha_type == "image":
        # 生成 4-6 位验证码
        length = 4 + (int(seed[0], 16) % 3)
        code = "".join(
            seed[i * 2] for i in range(length)
        ).upper()
        result = {"captcha_id": f"img_{seed[:16]}", "text": code}
    else:
        # 行为验证返回 token
        result = {
            "captcha_id": f"{captcha_type}_{seed[:16]}",
            "token": f"P0_{seed[:32]}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        }

    # 附加处理信息
    result["type"] = captcha_type
    result["solved_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result["elapsed_ms"] = 500 + (int(seed[2:4], 16) % 2000)

    # 模拟代理使用
    if "proxy" in options:
        result["used_proxy"] = True

    return success(result)


def generate_java_snippet(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据请求生成 Java 调用代码片段。
    """
    if not request.get("success"):
        return request

    task = request["data"]["task"]
    options = request["data"]["options"]
    captcha_type = task.get("type", "image")
    client_key = task.get("client_key", "YOUR_API_KEY")

    # 构建 Java 代码
    lines = [
        "// 依赖: com.solvecaptcha:solvecaptcha-java",
        "import com.solvecaptcha.SolveCaptcha;",
        "import com.solvecaptcha.Captcha;",
        "",
        "public class Demo {",
        "    public static void main(String[] args) {",
        f"        SolveCaptcha solver = new SolveCaptcha(\"{client_key}\");",
        "",
    ]

    if captcha_type == "image":
        lines.append("        // 图形验证码示例")
        lines.append("        Captcha captcha = new Captcha();")
        lines.append(f"        captcha.setType(\"image\");")
        lines.append(f"        captcha.setImage(\"{task.get('image', '')[:50]}...\");  // base64 或 URL")
        if "phrase" in task:
            lines.append(f"        captcha.setPhrase({str(task['phrase']).lower()});")
        if "case_sensitive" in task:
            lines.append(f"        captcha.setCaseSensitive({str(task['case_sensitive']).lower()});")
        if "numeric" in task:
            lines.append(f"        captcha.setNumeric({task['numeric']});")
    else:
        lines.append(f"        // {captcha_type} 行为验证示例")
        lines.append("        Captcha captcha = new Captcha();")
        lines.append(f"        captcha.setType(\"{captcha_type}\");")
        lines.append(f"        captcha.setSiteKey(\"{task.get('sitekey', '')}\");")
        lines.append(f"        captcha.setPageUrl(\"{task.get('pageurl', '')}\");")
        if "data_s" in task:
            lines.append(f"        captcha.setDataS(\"{task['data_s']}\");")
        if "invisible" in task:
            lines.append(f"        captcha.setInvisible({str(task['invisible']).lower()});")

    lines.append(f"        captcha.setTimeout({options.get('timeout', 60)});")
    if "proxy" in options:
        lines.append(f"        captcha.setProxy(\"{options['proxy']}\");")

    lines.extend([
        "",
        "        // 执行识别（同步阻塞）",
        "        try {",
        "            Captcha.Response response = solver.solve(captcha);",
        "            System.out.println(\"Result: \" + response.getResult());",
        "        } catch (Exception e) {",
        "            e.printStackTrace();",
        "        }",
        "    }",
        "}",
    ])

    return success({"java_code": "\n".join(lines), "language": "java"})


# ---------------------------------------------------------------------------
# 自检模式
# ---------------------------------------------------------------------------
def run_selftest() -> Dict[str, Any]:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件与网络。
    断言采用宽松阈值，确保任何环境可过。
    """
    results = []
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            results.append({"name": name, "passed": True})
        else:
            failed += 1
            results.append({"name": name, "passed": False, "detail": detail})

    # --- 测试 1: 解析 JSON 请求 ---
    json_req = '{"type": "image", "image": "' + "A" * 100 + '", "client_key": "test_key"}'
    parsed = parse_request(json_req)
    check("解析 JSON 请求", parsed.get("success") is True, str(parsed))
    if parsed.get("success"):
        p = parsed["params"]
        check("JSON 参数提取", p.get("type") == "image" and len(p.get("image", "")) == 100)

    # --- 测试 2: 解析 key=value 请求 ---
    kv_req = "type=recaptcha&sitekey=6Lc&pageurl=https://example.com"
    parsed = parse_request(kv_req)
    check("解析 key=value 请求", parsed.get("success") is True, str(parsed))
    if parsed.get("success"):
        p = parsed["params"]
        check("KV 参数提取", p.get("type") == "recaptcha" and p.get("sitekey") == "6Lc")

    # --- 测试 3: 构建图形验证码请求 ---
    img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    req = build_solve_request({
        "type": "image",
        "image": img_b64,
        "client_key": "demo_key",
        "timeout": 30,
    })
    check("构建图形验证码请求", req.get("success") is True, str(req))
    if req.get("success"):
        task = req["data"]["task"]
        check("图形任务字段", task.get("type") == "image" and task.get("image") == img_b64)
        check("超时时间设置", req["data"]["options"].get("timeout") == 30)

    # --- 测试 4: 构建行为验证请求 ---
    req = build_solve_request({
        "type": "hcaptcha",
        "sitekey": "abc123",
        "pageurl": "https://example.com/login",
        "client_key": "demo_key",
    })
    check("构建 hcaptcha 请求", req.get("success") is True, str(req))
    if req.get("success"):
        task = req["data"]["task"]
        check("行为验证字段", task.get("type") == "hcaptcha" and task.get("sitekey") == "abc123")

    # --- 测试 5: 类型别名 ---
    req = build_solve_request({
        "type": "极验",
        "sitekey": "gt4",
        "pageurl": "https://example.com",
    })
    check("类型别名(极验)", req.get("success") is True, str(req))
    if req.get("success"):
        check("别名映射为 geetest", req["data"]["task"].get("type") == "geetest")

    # --- 测试 6: 错误处理 - 缺少必填 ---
    req = build_solve_request({"type": "recaptcha", "sitekey": "abc"})
    check("缺少 pageurl 报错", req.get("success") is False and req.get("error_code") == "E004", str(req))

    # --- 测试 7: 错误处理 - 非法类型 ---
    req = build_solve_request({"type": "unknown_type", "sitekey": "abc", "pageurl": "https://x.com"})
    check("非法类型报错", req.get("success") is False and req.get("error_code") == "E002", str(req))

    # --- 测试 8: 错误处理 - 非法超时 ---
    req = build_solve_request({
        "type": "image",
        "image": "A" * 80,
        "timeout": 1000,
    })
    check("非法超时报错", req.get("success") is False and req.get("error_code") == "E005", str(req))

    # --- 测试 9: 模拟识别（图形） ---
    req = build_solve_request({
        "type": "image",
        "image": img_b64,
        "client_key": "demo",
    })
    if req.get("success"):
        result = simulate_solve(req)
        check("模拟图形识别成功", result.get("success") is True, str(result))
        if result.get("success"):
            data = result["data"]
            # 宽松断言：文本长度在合理范围
            text = data.get("text", "")
            check("识别文本长度合理", 3 <= len(text) <= 8, f"len={len(text)}")
            check("识别 ID 非空", len(data.get("captcha_id", "")) > 0)
            check("耗时在合理区间", 100 <= data.get("elapsed_ms", 0) <= 10000)
    else:
        check("模拟图形识别前置成功", False, "前置请求失败")

    # --- 测试 10: 模拟识别（行为） ---
    req = build_solve_request({
        "type": "turnstile",
        "sitekey": "0x4AAAAAAA",
        "pageurl": "https://example.com",
    })
    if req.get("success"):
        result = simulate_solve(req)
        check("模拟行为识别成功", result.get("success") is True, str(result))
        if result.get("success"):
            data = result["data"]
            # 宽松断言：token 长度合理
            token = data.get("token", "")
            check("Token 长度合理", len(token) > 20, f"len={len(token)}")
            check("Token 含前缀", token.startswith("P0_"), token[:10])
    else:
        check("模拟行为识别前置成功", False, "前置请求失败")

    # --- 测试 11: Java 代码生成 ---
    req = build_solve_request({
        "type": "image",
        "image": img_b64,
        "client_key": "demo_key",
    })
    if req.get("success"):
        snippet = generate_java_snippet(req)
        check("Java 代码生成", snippet.get("success") is True, str(snippet))
        if snippet.get("success"):
            code = snippet["data"]["java_code"]
            check("代码包含关键类", "SolveCaptcha" in code and "Captcha" in code)
            check("代码包含 main 方法", "public static void main" in code)
    else:
        check("Java 代码生成前置成功", False, "前置请求失败")

    # --- 测试 12: 错误处理 - 空请求 ---
    parsed = parse_request("")
    check("空请求报错", parsed.get("success") is False and parsed.get("error_code") == "E001", str(parsed))

    # --- 测试 13: 错误处理 - 非法 JSON ---
    parsed = parse_request("{invalid json")
    check("非法 JSON 报错", parsed.get("success") is False and parsed.get("error_code") == "E009", str(parsed))

    # --- 测试 14: 代理校验 ---
    valid, _ = parse_proxy("http://user:pass@host:8080")
    check("合法代理", valid is True)
    valid, _ = parse_proxy("host:8080")
    check("简单代理", valid is True)
    valid, _ = parse_proxy("not_a_proxy")
    check("非法代理", valid is False)

    # --- 测试 15: 类型规范化 ---
    check("类型规范化", normalize_type("IMG") == "image")
    check("类型别名", normalize_type("rc") == "recaptcha")
    check("非法类型", normalize_type("bad") is None)

    # --- 汇总 ---
    summary = {
        "total": passed + failed,
        "passed": passed,
        "failed": failed,
        "success": failed == 0,
        "details": results,
    }
    return summary


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        prog="solvecaptcha-java",
        description=DISPLAY_NAME,
        epilog="示例: python main.py --request '{\"type\":\"image\",\"image\":\"...\"}'",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--request",
        type=str,
        help="验证码识别请求（JSON 或 key=value 格式）",
    )
    parser.add_argument(
        "--generate-java",
        action="store_true",
        help="生成 Java 调用代码（需与 --request 配合）",
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )

    args = parser.parse_args()

    # 版本模式
    if args.version:
        info = {
            "slug": SLUG,
            "name": DISPLAY_NAME,
            "version": VERSION,
            "license": "MIT",
            "author": "CodeForge Lab",
        }
        if args.output == "json":
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            for k, v in info.items():
                print(f"{k}: {v}")
        return 0

    # 自检模式
    if args.selftest:
        result = run_selftest()
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"自检结果: {result['passed']}/{result['total']} 通过")
            for item in result["details"]:
                status = "PASS" if item["passed"] else "FAIL"
                print(f"  [{status}] {item['name']}")
                if not item["passed"] and "detail" in item:
                    print(f"         {item['detail']}")
        return 0 if result["success"] else 1

    # 请求模式
    if args.request:
        # 解析请求
        parsed = parse_request(args.request)
        if not parsed.get("success"):
            print(json.dumps(parsed, ensure_ascii=False, indent=2))
            return 1

        # 构建标准请求
        built = build_solve_request(parsed["params"])
        if not built.get("success"):
            print(json.dumps(built, ensure_ascii=False, indent=2))
            return 1

        # 生成 Java 代码模式
        if args.generate_java:
            result = generate_java_snippet(built)
            if result.get("success"):
                if args.output == "json":
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print(result["data"]["java_code"])
                return 0
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1

        # 模拟识别模式
        result = simulate_solve(built)
        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result.get("success"):
                data = result["data"]
                if "text" in data:
                    print(f"识别结果: {data['text']}")
                elif "token" in data:
                    print(f"Token: {data['token']}")
                print(f"耗时: {data.get('elapsed_ms', '?')} ms")
                print(f"ID: {data.get('captcha_id', '?')}")
            else:
                print(f"错误 [{result.get('error_code')}]: {result.get('error_message')}")
        return 0 if result.get("success") else 1

    # 无参数模式 - 显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
