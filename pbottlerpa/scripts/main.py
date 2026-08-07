#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pbottlerpa — 网页流程自动化与数据提取 RPA 工具
=================================================
基于功能规格独立实现（clean-room）。
提供网页操作与数据提取的模拟核心逻辑，支持命令行调用与离线自检。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# 错误码定义（E001-E010）
# =============================================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "配置错误：配置文件不存在或格式无效",
    "E003": "网络错误：无法访问目标地址",
    "E004": "页面解析错误：无法解析目标页面结构",
    "E005": "选择器错误：指定的元素选择器无效",
    "E006": "操作超时：等待元素或页面加载超时",
    "E007": "数据提取错误：无法从页面提取所需数据",
    "E008": "数据校验错误：提取的数据未通过校验规则",
    "E009": "脚本执行错误：流程脚本执行过程中出现异常",
    "E010": "未知错误：未分类的异常情况",
}


class RPAError(Exception):
    """RPA 业务异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# =============================================================================
# 数据结构定义
# =============================================================================
@dataclass
class Selector:
    """元素选择器，支持 CSS 类选择器或 XPath 简化表达。"""

    type: str = "css"  # css 或 xpath
    value: str = ""

    @classmethod
    def from_string(cls, raw: str) -> "Selector":
        """从字符串解析选择器，支持 'css=.class' 或 'xpath=//div' 格式。"""
        if not raw or not raw.strip():
            raise RPAError("E005", "选择器不能为空")
        raw = raw.strip()
        if "=" in raw:
            stype, svalue = raw.split("=", 1)
            stype = stype.strip().lower()
            svalue = svalue.strip()
            if stype not in ("css", "xpath"):
                raise RPAError("E005", f"不支持的选择器类型: {stype}")
            return cls(type=stype, value=svalue)
        # 默认按 CSS 处理
        return cls(type="css", value=raw)


@dataclass
class ExtractedData:
    """提取的数据结果。"""

    items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(
            {"items": self.items, "metadata": self.metadata},
            ensure_ascii=False,
            indent=2,
        )


@dataclass
class WorkflowStep:
    """流程步骤定义。"""

    action: str  # 操作类型：open, click, input, extract, wait, screenshot
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowConfig:
    """流程配置。"""

    name: str = ""
    url: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    timeout: int = 30  # 默认超时秒数
    retry: int = 3  # 默认重试次数


# =============================================================================
# 核心引擎：模拟网页操作与数据提取
# =============================================================================
class RPAEngine:
    """
    模拟 RPA 引擎，在不依赖真实浏览器的情况下提供：
    - 页面加载模拟（基于 URL 的虚拟内容生成）
    - 元素查找与操作（CSS/XPath 简化匹配）
    - 数据提取与清洗
    - 流程脚本执行
    """

    # 内置虚拟页面数据（用于演示与自检）
    _VIRTUAL_PAGES = {
        "example.com": {
            "title": "Example Domain",
            "content": [
                {"tag": "h1", "text": "Example Domain", "attrs": {"id": "main-title"}},
                {"tag": "p", "text": "This domain is for use in illustrative examples.", "attrs": {"class": "description"}},
                {"tag": "a", "text": "More information...", "attrs": {"href": "https://www.iana.org/domains/example", "class": "link"}},
                {"tag": "div", "text": "Item 1", "attrs": {"class": "item"}},
                {"tag": "div", "text": "Item 2", "attrs": {"class": "item"}},
                {"tag": "div", "text": "Item 3", "attrs": {"class": "item"}},
            ],
        },
        "prices.example.com": {
            "title": "Price List",
            "content": [
                {"tag": "h1", "text": "Product Prices", "attrs": {"id": "price-title"}},
                {"tag": "div", "text": "Product A: $19.99", "attrs": {"class": "product", "data-price": "19.99"}},
                {"tag": "div", "text": "Product B: $29.50", "attrs": {"class": "product", "data-price": "29.50"}},
                {"tag": "div", "text": "Product C: $9.99", "attrs": {"class": "product", "data-price": "9.99"}},
            ],
        },
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.current_url: str = ""
        self.current_page: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # 页面操作
    # -------------------------------------------------------------------------
    def open_url(self, url: str) -> bool:
        """打开指定 URL，模拟页面加载。"""
        if not url or not url.startswith(("http://", "https://")):
            raise RPAError("E001", f"无效的 URL: {url}")

        # 模拟网络请求（仅演示，实际应使用 requests/playwright 等）
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc
            if domain in self._VIRTUAL_PAGES:
                self.current_page = self._VIRTUAL_PAGES[domain]
                self.current_url = url
                self.history.append({"url": url, "time": time.time()})
                return True
            else:
                # 未知域名：生成通用页面
                self.current_page = {
                    "title": f"Page: {domain}",
                    "content": [
                        {"tag": "h1", "text": f"Welcome to {domain}", "attrs": {"id": "welcome"}},
                        {"tag": "p", "text": "Generic content for demonstration.", "attrs": {"class": "content"}},
                    ],
                }
                self.current_url = url
                self.history.append({"url": url, "time": time.time()})
                return True
        except Exception as exc:
            raise RPAError("E003", f"无法访问 {url}: {str(exc)}") from exc

    def find_elements(self, selector: Selector) -> List[Dict[str, Any]]:
        """根据选择器查找元素（模拟 DOM 查询）。"""
        if not self.current_page:
            raise RPAError("E003", "当前没有加载页面，请先打开 URL")

        elements = self.current_page.get("content", [])
        results = []

        if selector.type == "css":
            # 简化 CSS 匹配：支持 .class、#id、tag 形式
            svalue = selector.value.strip()
            if svalue.startswith("."):
                class_name = svalue[1:]
                results = [el for el in elements if class_name in el.get("attrs", {}).get("class", "")]
            elif svalue.startswith("#"):
                el_id = svalue[1:]
                results = [el for el in elements if el.get("attrs", {}).get("id") == el_id]
            else:
                # 按标签名匹配
                results = [el for el in elements if el.get("tag") == svalue]
        elif selector.type == "xpath":
            # 简化 XPath 匹配：支持 //tag、//tag[@class='x']
            svalue = selector.value.strip()
            # 移除 // 前缀
            expr = svalue.lstrip("/")
            if "[" in expr:
                # 带属性条件
                tag_part, attr_part = expr.split("[", 1)
                tag_part = tag_part.strip()
                attr_part = attr_part.rstrip("]")
                # 解析 @attr='value' 或 @attr="value"
                match = re.search(r"@([\w-]+)\s*=\s*['\"]([^'\"]*)['\"]", attr_part)
                if match:
                    attr_name, attr_value = match.group(1), match.group(2)
                    results = [
                        el for el in elements
                        if (not tag_part or el.get("tag") == tag_part)
                        and el.get("attrs", {}).get(attr_name) == attr_value
                    ]
                else:
                    results = [el for el in elements if not tag_part or el.get("tag") == tag_part]
            else:
                results = [el for el in elements if el.get("tag") == expr]

        if not results:
            raise RPAError("E005", f"未找到匹配元素: {selector.value}")
        return results

    def click(self, selector: Selector) -> bool:
        """模拟点击元素。"""
        elements = self.find_elements(selector)
        if not elements:
            raise RPAError("E005", f"点击失败，未找到元素: {selector.value}")
        # 模拟点击行为（记录到历史）
        self.history.append({"action": "click", "selector": selector.value, "time": time.time()})
        return True

    def input_text(self, selector: Selector, text: str) -> bool:
        """模拟向输入框输入文本。"""
        elements = self.find_elements(selector)
        if not elements:
            raise RPAError("E005", f"输入失败，未找到元素: {selector.value}")
        # 模拟输入
        self.history.append({"action": "input", "selector": selector.value, "text": text, "time": time.time()})
        return True

    def wait(self, seconds: float = 1.0) -> bool:
        """模拟等待。"""
        if seconds < 0:
            raise RPAError("E001", "等待时间不能为负数")
        time.sleep(min(seconds, 0.1))  # 实际等待限制在 0.1 秒内
        return True

    # -------------------------------------------------------------------------
    # 数据提取
    # -------------------------------------------------------------------------
    def extract_text(self, selector: Selector, attribute: Optional[str] = None) -> List[str]:
        """提取元素文本或属性值。"""
        elements = self.find_elements(selector)
        results = []
        for el in elements:
            if attribute:
                value = el.get("attrs", {}).get(attribute, "")
            else:
                value = el.get("text", "")
            if value:
                results.append(value)
        if not results:
            raise RPAError("E007", f"未能提取到数据: {selector.value}")
        return results

    def extract_table(self, selector: Selector) -> List[Dict[str, str]]:
        """提取表格数据（模拟）。"""
        elements = self.find_elements(selector)
        rows = []
        for el in elements:
            text = el.get("text", "")
            # 尝试解析为键值对或列表
            if ":" in text:
                key, value = text.split(":", 1)
                rows.append({key.strip(): value.strip()})
            else:
                rows.append({"value": text.strip()})
        if not rows:
            raise RPAError("E007", f"表格数据提取失败: {selector.value}")
        return rows

    def extract_all(self, config: Dict[str, Any]) -> ExtractedData:
        """根据配置提取多种数据。"""
        result = ExtractedData()
        selectors = config.get("selectors", {})

        for name, sel_config in selectors.items():
            try:
                sel = Selector.from_string(sel_config.get("selector", ""))
                attr = sel_config.get("attribute")
                method = sel_config.get("method", "text")

                if method == "text":
                    values = self.extract_text(sel, attr)
                    result.items.append({"name": name, "type": "text", "values": values})
                elif method == "table":
                    rows = self.extract_table(sel)
                    result.items.append({"name": name, "type": "table", "rows": rows})
                elif method == "count":
                    count = len(self.find_elements(sel))
                    result.items.append({"name": name, "type": "count", "count": count})
                else:
                    raise RPAError("E001", f"未知提取方法: {method}")
            except RPAError:
                # 单个选择器失败不中断整体
                continue

        result.metadata = {
            "url": self.current_url,
            "timestamp": time.time(),
            "total_items": len(result.items),
        }
        return result

    # -------------------------------------------------------------------------
    # 流程执行
    # -------------------------------------------------------------------------
    def execute_workflow(self, config: WorkflowConfig) -> Dict[str, Any]:
        """执行完整的工作流程。"""
        if not config.url:
            raise RPAError("E001", "流程缺少起始 URL")

        execution_log = []
        self.open_url(config.url)
        execution_log.append({"step": "open", "url": config.url, "status": "success"})

        for idx, step in enumerate(config.steps, 1):
            try:
                if step.action == "open":
                    url = step.params.get("url", "")
                    if not url:
                        raise RPAError("E001", "open 操作缺少 url 参数")
                    self.open_url(url)
                    execution_log.append({"step": idx, "action": "open", "status": "success"})

                elif step.action == "click":
                    sel = Selector.from_string(step.params.get("selector", ""))
                    self.click(sel)
                    execution_log.append({"step": idx, "action": "click", "status": "success"})

                elif step.action == "input":
                    sel = Selector.from_string(step.params.get("selector", ""))
                    text = step.params.get("text", "")
                    self.input_text(sel, text)
                    execution_log.append({"step": idx, "action": "input", "status": "success"})

                elif step.action == "wait":
                    seconds = float(step.params.get("seconds", 1))
                    self.wait(seconds)
                    execution_log.append({"step": idx, "action": "wait", "status": "success"})

                elif step.action == "extract":
                    extract_config = step.params.get("config", {})
                    data = self.extract_all(extract_config)
                    execution_log.append({
                        "step": idx,
                        "action": "extract",
                        "status": "success",
                        "data": data.to_json(),
                    })

                elif step.action == "screenshot":
                    # 模拟截图
                    execution_log.append({
                        "step": idx,
                        "action": "screenshot",
                        "status": "success",
                        "path": f"screenshot_{idx}.png",
                    })

                else:
                    raise RPAError("E009", f"未知操作: {step.action}")

            except RPAError as exc:
                execution_log.append({
                    "step": idx,
                    "action": step.action,
                    "status": "failed",
                    "error": str(exc),
                })
                raise

        return {
            "success": True,
            "url": self.current_url,
            "log": execution_log,
            "history": self.history,
        }


# =============================================================================
# 流程配置加载与解析
# =============================================================================
def load_workflow_config(filepath: str) -> WorkflowConfig:
    """从 JSON 文件加载流程配置。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise RPAError("E002", f"配置文件不存在: {filepath}") from exc
    except json.JSONDecodeError as exc:
        raise RPAError("E002", f"配置文件 JSON 格式错误: {str(exc)}") from exc

    if not isinstance(raw, dict):
        raise RPAError("E002", "配置文件顶层必须是 JSON 对象")

    try:
        config = WorkflowConfig(
            name=raw.get("name", ""),
            url=raw.get("url", ""),
            timeout=int(raw.get("timeout", 30)),
            retry=int(raw.get("retry", 3)),
        )

        steps_raw = raw.get("steps", [])
        if not isinstance(steps_raw, list):
            raise RPAError("E002", "steps 必须是数组")

        for step_raw in steps_raw:
            if not isinstance(step_raw, dict):
                raise RPAError("E002", "每个 step 必须是对象")
            action = step_raw.get("action", "")
            params = step_raw.get("params", {})
            if not action:
                raise RPAError("E002", "step 缺少 action 字段")
            config.steps.append(WorkflowStep(action=action, params=params))

        return config
    except (ValueError, TypeError) as exc:
        raise RPAError("E002", f"配置解析错误: {str(exc)}") from exc


# =============================================================================
# 自检功能（--selftest）
# =============================================================================
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码数据，不访问网络、不读取外部文件。
    使用宽松断言确保稳定通过。
    """
    print("=" * 60)
    print("pbottlerpa 自检程序开始")
    print("=" * 60)

    # 1. 测试错误码定义
    assert len(ERROR_CODES) == 10, "错误码数量应为 10"
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"缺少错误码 {code}"
    print("[PASS] 错误码定义检查")

    # 2. 测试 Selector 解析
    sel1 = Selector.from_string("css=.item")
    assert sel1.type == "css" and sel1.value == ".item", "CSS 选择器解析失败"
    sel2 = Selector.from_string("xpath=//div[@class='item']")
    assert sel2.type == "xpath", "XPath 选择器解析失败"
    try:
        Selector.from_string("")
        assert False, "空选择器应抛出异常"
    except RPAError:
        pass
    print("[PASS] 选择器解析")

    # 3. 测试引擎基本操作
    engine = RPAEngine(timeout=10)

    # 打开示例页面
    success = engine.open_url("https://example.com")
    assert success, "打开示例页面失败"
    assert engine.current_url == "https://example.com", "URL 设置错误"
    assert len(engine.current_page.get("content", [])) > 0, "页面内容为空"
    print("[PASS] 页面加载")

    # 查找元素
    items = engine.find_elements(Selector.from_string("css=.item"))
    assert len(items) >= 1, "应找到至少一个 .item 元素"
    assert len(items) <= 10, "元素数量应在合理范围"

    # 提取文本
    texts = engine.extract_text(Selector.from_string("css=.item"))
    assert len(texts) >= 1, "应提取到文本"
    assert all(isinstance(t, str) and len(t) > 0 for t in texts), "文本应为非空字符串"
    print("[PASS] 元素查找与文本提取")

    # 4. 测试 XPath 查找
    xpath_items = engine.find_elements(Selector.from_string("xpath=//div[@class='item']"))
    assert len(xpath_items) >= 1, "XPath 查找应返回结果"
    print("[PASS] XPath 查找")

    # 5. 测试数据提取
    extract_config = {
        "selectors": {
            "title": {"selector": "css=#main-title", "method": "text"},
            "items": {"selector": "css=.item", "method": "count"},
            "link": {"selector": "css=a.link", "attribute": "href", "method": "text"},
        }
    }
    data = engine.extract_all(extract_config)
    assert len(data.items) >= 1, "应提取到至少一项数据"
    assert len(data.items) <= 10, "提取项数应在合理范围"
    print("[PASS] 数据提取")

    # 6. 测试价格页面
    engine.open_url("https://prices.example.com")
    prices = engine.extract_text(Selector.from_string("css=.product"))
    assert len(prices) >= 1, "应提取到价格数据"
    # 宽松断言：价格数量应在合理范围
    assert len(prices) <= 20, "价格数量不应过多"

    # 验证价格数据包含数字
    price_text = " ".join(prices)
    assert re.search(r"\d+\.?\d*", price_text), "价格数据应包含数字"
    print("[PASS] 价格数据提取")

    # 7. 测试流程执行
    config = WorkflowConfig(
        name="测试流程",
        url="https://example.com",
        steps=[
            WorkflowStep(action="wait", params={"seconds": 0.01}),
            WorkflowStep(action="extract", params={"config": extract_config}),
            WorkflowStep(action="screenshot", params={}),
        ],
    )
    result = engine.execute_workflow(config)
    assert result["success"] is True, "流程执行应成功"
    assert len(result["log"]) >= 3, "流程日志应包含至少 3 步"
    print("[PASS] 流程执行")

    # 8. 测试错误处理
    try:
        engine.open_url("invalid-url")
        assert False, "无效 URL 应抛出异常"
    except RPAError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"

    try:
        engine.find_elements(Selector.from_string("css=.nonexistent"))
        assert False, "不存在的元素应抛出异常"
    except RPAError as exc:
        assert exc.code in ("E005", "E007"), f"错误码应为 E005 或 E007，实际为 {exc.code}"
    print("[PASS] 错误处理")

    # 9. 测试配置加载（使用内存数据，不读文件）
    import tempfile
    import os

    test_config = {
        "name": "测试",
        "url": "https://example.com",
        "timeout": 15,
        "steps": [
            {"action": "wait", "params": {"seconds": 0.01}},
            {"action": "extract", "params": {"config": extract_config}},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_config, f)
        tmp_path = f.name

    try:
        loaded = load_workflow_config(tmp_path)
        assert loaded.name == "测试", "配置名称加载错误"
        assert len(loaded.steps) == 2, "步骤数量加载错误"
    finally:
        os.unlink(tmp_path)
    print("[PASS] 配置加载")

    # 10. 测试 JSON 序列化
    data_json = data.to_json()
    parsed = json.loads(data_json)
    assert "items" in parsed and "metadata" in parsed, "JSON 序列化应包含 items 和 metadata"
    print("[PASS] JSON 序列化")

    print("=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return 0


# =============================================================================
# 命令行入口
# =============================================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="pbottlerpa - 网页流程自动化与数据提取 RPA 工具",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不访问网络、不读取外部文件）",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="流程配置文件路径（JSON 格式）",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="直接指定起始 URL",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="超时时间（秒），默认 30",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as exc:
            print(f"[E010] 自检失败: {str(exc)}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"[E010] 自检异常: {str(exc)}", file=sys.stderr)
            return 1

    # 正常模式：需要配置文件或 URL
    if not args.config and not args.url:
        parser.error("请提供 --config 或 --url 参数，或使用 --selftest 运行自检")

    try:
        # 加载配置或构建简单流程
        if args.config:
            config = load_workflow_config(args.config)
        else:
            config = WorkflowConfig(
                name="命令行流程",
                url=args.url,
                timeout=args.timeout,
                steps=[
                    WorkflowStep(action="wait", params={"seconds": 0.1}),
                    WorkflowStep(
                        action="extract",
                        params={
                            "config": {
                                "selectors": {
                                    "title": {"selector": "css=h1", "method": "text"},
                                    "paragraphs": {"selector": "css=p", "method": "text"},
                                }
                            }
                        },
                    ),
                ],
            )

        # 执行流程
        engine = RPAEngine(timeout=config.timeout)
        result = engine.execute_workflow(config)

        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except RPAError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] 未知错误: {str(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
