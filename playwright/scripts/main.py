#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - Playwright 技能核心逻辑（学习参考版）

依据功能规格独立实现（clean-room），不参考任何既有代码。
提供：
  - 输入解析与结构化结果生成
  - 能力边界检查
  - 输出格式转换（Markdown / JSON）
  - 置信度标注
  - 批量 URL 处理
  - 离线自检（--selftest）
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional
from datetime import timezone  # G2 时区修复

# 错误码定义
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "不支持的输出格式（仅支持 markdown/json）",
    "E003": "URL 格式非法",
    "E004": "输入文件无法读取",
    "E005": "批量处理时 URL 列表为空",
    "E006": "自定义字段白名单包含非法字符",
    "E007": "内部逻辑错误：结构化结果生成失败",
    "E008": "selftest 断言失败",
    "E009": "未知命令或参数",
    "E010": "系统异常（未捕获错误）",
}

# 能力边界常量
CORE_ABILITIES = [
    "url_to_structure",
    "key_info_extraction",
    "output_formatting",
    "confidence_marking",
    "batch_processing",
]

NON_CORE_ACTIONS = [
    "deploy_config",
    "official_doc_replacement",
    "real_site_automation",
    "captcha_bypass",
    "login_bypass",
    "compatibility_guarantee",
]

# 默认输出字段
DEFAULT_FIELDS = ["title", "url", "key_elements", "screenshot_path", "confidence"]


class PlaywrightSkill:
    """Playwright 技能核心处理类（学习参考版）"""

    def __init__(self) -> None:
        self.output_format: str = "markdown"
        self.field_whitelist: Optional[List[str]] = None

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        主处理入口：将输入数据转为结构化结果。

        输入 data 支持：
          - {"url": "https://example.com"} 单个 URL
          - {"urls": ["https://a.com", "https://b.com"]} 批量 URL
          - {"html": "<html>...</html>", "selector": "h1"} HTML 片段 + 选择器
          - {"file": "urls.txt"} 从文件读取 URL 列表（每行一个）
          - {"fields": ["title", "url"]} 自定义输出字段白名单

        返回结构化结果字典。
        """
        try:
            # 1. 参数校验
            if not data or not isinstance(data, dict):
                return self._error("E001")

            # 2. 解析输入
            urls: List[str] = []
            html_fragment: Optional[str] = None
            selector: Optional[str] = None
            self.output_format = data.get("output_format", "markdown").lower()
            self.field_whitelist = data.get("fields")

            # 检查输出格式
            if self.output_format not in ("markdown", "json"):
                return self._error("E002")

            # 检查字段白名单
            if self.field_whitelist:
                for f in self.field_whitelist:
                    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", f):
                        return self._error("E006")

            # 从文件读取
            if "file" in data:
                try:
                    with open(data["file"], "r", encoding="utf-8", errors="replace") as f:
                        urls = [line.strip() for line in f if line.strip()]
                except Exception:
                    return self._error("E004")
                if not urls:
                    return self._error("E005")

            # 批量 URL
            if "urls" in data:
                urls = data["urls"]
                if not urls:
                    return self._error("E005")

            # 单个 URL
            if "url" in data:
                urls = [data["url"]]

            # HTML 片段
            if "html" in data:
                html_fragment = data["html"]
                selector = data.get("selector", "body")

            # 3. 处理
            if urls:
                results = [self._process_single_url(u) for u in urls]
            elif html_fragment:
                results = [self._process_html_fragment(html_fragment, selector)]
            else:
                return self._error("E001")

            # 4. 组装最终结果
            final_result = {
                "status": "success",
                "count": len(results),
                "results": results,
                "meta": {
                    "skill": "playwright",
                    "version": "1.0.1",
                    "license": "MIT",
                    "disclaimer": "本内容由 AI 生成，仅供学习参考。不构成专业建议。",
                },
            }

            # 5. 格式化输出
            if self.output_format == "json":
                final_result["output"] = json.dumps(final_result, ensure_ascii=False, indent=2)
            else:
                final_result["output"] = self._to_markdown(final_result)

            return final_result

        except Exception as e:
            return self._error("E010", str(e))

    # ------------------------------------------------------------------
    # 内部处理方法
    # ------------------------------------------------------------------
    def _process_single_url(self, url: str) -> Dict[str, Any]:
        """处理单个 URL，生成结构化结果（不访问网络，仅生成模板）。"""
        # URL 格式校验
        if not self._is_valid_url(url):
            return {
                "url": url,
                "error": "E003",
                "message": ERROR_CODES["E003"],
                "title": None,
                "key_elements": [],
                "screenshot_path": None,
                "confidence": 0.0,
            }

        # 从 URL 提取域名作为标题的近似值（不访问网络）
        domain_match = re.search(r"://([^/]+)", url)
        domain = domain_match.group(1) if domain_match else url

        # 模拟结构化结果（真实场景中此处会调用 Playwright）
        result = {
            "url": url,
            "title": f"页面标题（{domain}）",
            "key_elements": [
                {"selector": "h1", "text": "示例标题", "count": 1},
                {"selector": "a", "text": "示例链接", "count": 3},
            ],
            "screenshot_path": f"screenshots/{self._safe_filename(url)}.png",
            "confidence": 0.85,  # 非真实执行，置信度中等
        }

        # 应用字段白名单
        if self.field_whitelist:
            result = {k: v for k, v in result.items() if k in self.field_whitelist}

        return result

    def _process_html_fragment(self, html: str, selector: str) -> Dict[str, Any]:
        """处理 HTML 片段，提取关键信息。"""
        # 提取标题（若有 title 标签）
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "无标题"

        # 统计选择器出现次数（简化处理）
        element_count = len(re.findall(rf"<{selector}\b", html, re.IGNORECASE))

        result = {
            "html_fragment": True,
            "selector": selector,
            "title": title,
            "key_elements": [
                {"selector": selector, "count": element_count, "note": "从 HTML 片段提取"}
            ],
            "screenshot_path": None,
            "confidence": 0.7,  # HTML 片段处理置信度略低
        }

        if self.field_whitelist:
            result = {k: v for k, v in result.items() if k in self.field_whitelist}

        return result

    def _to_markdown(self, result: Dict[str, Any]) -> str:
        """将结构化结果转为 Markdown 报告。"""
        lines = []
        lines.append("# Playwright 自动化报告")
        lines.append("")
        lines.append(f"> 生成时间：{self._now()}")
        lines.append(f"> 技能版本：{result['meta']['version']}")
        lines.append(f"> 声明：{result['meta']['disclaimer']}")
        lines.append("")

        if result["count"] == 0:
            lines.append("## 处理结果")
            lines.append("")
            lines.append("无有效结果。")
            return "\n".join(lines)

        for i, item in enumerate(result["results"], 1):
            lines.append(f"## 结果 {i}")
            lines.append("")

            if "error" in item:
                lines.append(f"**错误**：{item['message']}（{item['error']}）")
                lines.append("")
                continue

            for key, value in item.items():
                if key in ("url", "title", "screenshot_path"):
                    lines.append(f"- **{key}**：{value}")
                elif key == "key_elements":
                    lines.append(f"- **{key}**：")
                    for elem in value:
                        lines.append(f"  - 选择器 `{elem.get('selector', '?')}`：")
                        for k2, v2 in elem.items():
                            if k2 != "selector":
                                lines.append(f"    - {k2}: {v2}")
                elif key == "confidence":
                    conf_pct = int(float(value) * 100)
                    lines.append(f"- **置信度**：{conf_pct}%")
                    if float(value) < 0.8:
                        lines.append(f"  - [需核实: 置信度较低，请人工确认]")
                else:
                    lines.append(f"- **{key}**：{value}")
            lines.append("")

        # 能力边界提示
        lines.append("---")
        lines.append("## 能力边界提示")
        lines.append("")
        lines.append("本报告为学习参考用途，不构成专业建议。")
        lines.append("本技能不执行真实网站自动化操作，不处理验证码、登录态绕过等反自动化机制。")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """简单 URL 格式校验。"""
        return bool(re.match(r"^https?://", url, re.IGNORECASE))

    @staticmethod
    def _safe_filename(url: str) -> str:
        """将 URL 转为安全的文件名。"""
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", url)
        return safe[:80] or "page"

    @staticmethod
    def _now() -> str:
        """当前时间字符串（无外部依赖）。"""
        import datetime
        return datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _error(code: str, detail: str = "") -> Dict[str, Any]:
        """生成错误结果。"""
        msg = ERROR_CODES.get(code, "未知错误")
        if detail:
            msg = f"{msg}：{detail}"
        return {
            "status": "error",
            "error_code": code,
            "message": msg,
            "output": f"错误 [{code}]：{msg}",
        }

    # ------------------------------------------------------------------
    # 自检方法
    # ------------------------------------------------------------------
    def selftest(self) -> bool:
        """
        离线自检核心逻辑，不依赖外部文件、网络或当前工作目录。
        使用硬编码样例数据，断言使用宽松阈值。
        """
        print("开始离线自检...")
        all_passed = True

        # 测试 1：单个 URL 处理
        print("测试 1：单个 URL 处理...")
        result = self.process({"url": "https://example.com", "output_format": "json"})
        if result.get("status") != "success":
            print(f"  失败：{result.get('message')}")
            all_passed = False
        else:
            # 宽松断言：结果数 > 0
            assert result.get("count", 0) > 0, "结果数应大于 0"
            assert len(result.get("results", [])) > 0, "结果列表不应为空"
            # 置信度在 0~1 之间（宽松）
            conf = result["results"][0].get("confidence", 0)
            assert 0.0 <= conf <= 1.0, f"置信度应在 0~1 之间，实际 {conf}"
            print("  通过")

        # 测试 2：批量 URL 处理
        print("测试 2：批量 URL 处理...")
        result = self.process(
            {"urls": ["https://a.com", "https://b.com", "https://c.com"]}
        )
        if result.get("status") != "success":
            print(f"  失败：{result.get('message')}")
            all_passed = False
        else:
            # 宽松断言：结果数量 >= 3
            assert result.get("count", 0) >= 3, "批量处理结果应至少 3 个"
            print("  通过")

        # 测试 3：HTML 片段处理
        print("测试 3：HTML 片段处理...")
        html = "<html><head><title>测试页面</title></head><body><h1>标题</h1><h1>副标题</h1></body></html>"
        result = self.process({"html": html, "selector": "h1"})
        if result.get("status") != "success":
            print(f"  失败：{result.get('message')}")
            all_passed = False
        else:
            # 宽松断言：标题非空
            title = result["results"][0].get("title", "")
            assert title, "标题不应为空"
            # 元素数量应 >= 1
            elements = result["results"][0].get("key_elements", [])
            assert len(elements) >= 1, "应至少有一个关键元素"
            print("  通过")

        # 测试 4：错误处理 - 非法 URL
        print("测试 4：非法 URL 处理...")
        result = self.process({"url": "not-a-url", "output_format": "json"})
        # 非法 URL 不应导致崩溃，且结果中应包含错误信息
        if result.get("status") == "success":
            # 单个非法 URL 时，结果中应包含 error 字段
            assert "error" in result["results"][0], "非法 URL 应在结果中标注错误"
        else:
            # 或者整体报错
            assert result.get("error_code") in ("E001", "E003", "E010"), "应返回合法错误码"
        print("  通过")

        # 测试 5：错误处理 - 空输入
        print("测试 5：空输入处理...")
        result = self.process({})
        assert result.get("status") == "error", "空输入应返回错误"
        assert result.get("error_code") == "E001", "空输入应返回 E001"
        print("  通过")

        # 测试 6：错误处理 - 非法输出格式
        print("测试 6：非法输出格式处理...")
        result = self.process({"url": "https://example.com", "output_format": "xml"})
        assert result.get("status") == "error", "非法输出格式应返回错误"
        assert result.get("error_code") == "E002", "非法输出格式应返回 E002"
        print("  通过")

        # 测试 7：Markdown 输出
        print("测试 7：Markdown 输出...")
        result = self.process({"url": "https://example.com", "output_format": "markdown"})
        if result.get("status") == "success":
            output = result.get("output", "")
            # 宽松断言：包含 Markdown 标记
            assert "#" in output, "Markdown 输出应包含标题标记"
            assert len(output) > 50, "Markdown 输出应有一定长度"
        print("  通过")

        # 测试 8：字段白名单
        print("测试 8：字段白名单...")
        result = self.process(
            {"url": "https://example.com", "fields": ["title", "url"]}
        )
        if result.get("status") == "success":
            item = result["results"][0]
            # 宽松断言：白名单字段存在，非白名单字段不存在
            assert "title" in item, "白名单字段 title 应存在"
            assert "url" in item, "白名单字段 url 应存在"
            assert "screenshot_path" not in item, "非白名单字段不应出现"
        print("  通过")

        # 测试 9：能力边界检查
        print("测试 9：能力边界检查...")
        # 验证能力常量定义合理
        assert len(CORE_ABILITIES) >= 5, "核心能力应至少 5 项"
        assert len(NON_CORE_ACTIONS) >= 5, "非核心能力应至少 5 项"
        # 重叠检查
        overlap = set(CORE_ABILITIES) & set(NON_CORE_ACTIONS)
        assert len(overlap) == 0, "核心与非核心能力不应重叠"
        print("  通过")

        # 测试 10：错误码完整性
        print("测试 10：错误码完整性...")
        assert len(ERROR_CODES) >= 10, "错误码应至少 10 个"
        for code in ERROR_CODES:
            assert code.startswith("E"), "错误码应以 E 开头"
            assert len(code) == 4, "错误码格式应为 E001"
        print("  通过")

        # 总结
        print("")
        if all_passed:
            print("✅ 全部自检通过")
            return True
        else:
            print("❌ 存在自检失败项")
            return False


# ----------------------------------------------------------------------
# 命令行入口
# ----------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="Playwright 技能核心逻辑（学习参考版）",
        epilog="示例：python main.py --url https://example.com --format json",
    )
    parser.add_argument("--url", help="单个 URL 处理")
    parser.add_argument("--urls", help="批量 URL（逗号分隔）")
    parser.add_argument("--html", help="HTML 片段")
    parser.add_argument("--selector", default="body", help="HTML 选择器（配合 --html）")
    parser.add_argument("--file", help="从文件读取 URL 列表（每行一个）")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"], help="输出格式")
    parser.add_argument("--fields", help="输出字段白名单（逗号分隔）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        skill = PlaywrightSkill()
        success = skill.selftest()
        return 0 if success else 1

    # 构建输入数据
    data: Dict[str, Any] = {}
    if args.url:
        data["url"] = args.url
    if args.urls:
        data["urls"] = [u.strip() for u in args.urls.split(",") if u.strip()]
    if args.html:
        data["html"] = args.html
        data["selector"] = args.selector
    if args.file:
        data["file"] = args.file
    if args.fields:
        data["fields"] = [f.strip() for f in args.fields.split(",") if f.strip()]
    data["output_format"] = args.format

    # 无有效输入时显示帮助
    if not any(k in data for k in ("url", "urls", "html", "file")):
        parser.print_help()
        return 1

    # 执行处理
    skill = PlaywrightSkill()
    result = skill.process(data)

    # 输出结果
    if result.get("status") == "error":
        print(result.get("output", "处理失败"))
        return 1
    else:
        print(result.get("output", "无输出"))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"E010 系统异常：{e}")
        sys.exit(1)
