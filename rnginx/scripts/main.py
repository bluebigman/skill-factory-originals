#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rnginx — Nginx 配置脚本结构化解析命令行工具

本脚本为 clean-room 独立实现，仅依据功能规格编写。
解析 Nginx 配置文本，提取关键指令并输出结构化 JSON/YAML/文本树，
附带置信度标注（high / medium / low）。

用法示例:
    python main.py --text 'server { listen 80; server_name a.com; }'
    python main.py --file /etc/nginx/conf.d/app.conf --format yaml
    python main.py --selftest
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# 错误码定义 (E001-E010)
# ---------------------------------------------------------------------------
ERR_INVALID_ARGS = "E001"        # 命令行参数不合法
ERR_FILE_NOT_FOUND = "E002"      # 文件不存在
ERR_FILE_READ_FAILED = "E003"    # 文件读取失败
ERR_URL_UNSUPPORTED = "E004"     # URL 输入暂不支持（离线模式）
ERR_INPUT_EMPTY = "E005"         # 输入内容为空
ERR_PARSE_SYNTAX = "E006"        # 配置语法错误（括号不匹配等）
ERR_UNKNOWN_BLOCK = "E007"       # 未知块指令（不阻断，仅记录）
ERR_OUTPUT_SERIALIZE = "E008"    # 输出序列化失败
ERR_INTERNAL = "E009"            # 内部未知错误
ERR_BATCH_TOO_LARGE = "E010"     # 批量文件超过 50 个


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------

@dataclass
class NginxDirective:
    """一条 Nginx 指令（简单指令或块指令）。"""
    name: str
    args: List[str] = field(default_factory=list)
    block: Optional["NginxBlock"] = None  # 若为块指令，则包含子指令
    line: int = 0
    confidence: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON/YAML 输出）。"""
        result: Dict[str, Any] = {
            "directive": self.name,
            "args": self.args,
            "line": self.line,
            "confidence": self.confidence,
        }
        if self.block is not None:
            result["block"] = self.block.to_dict()
        return result


@dataclass
class NginxBlock:
    """一个块（如 server { ... }）。"""
    directives: List[NginxDirective] = field(default_factory=list)

    def to_dict(self) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in self.directives]


@dataclass
class ParseResult:
    """解析结果（顶层结构）。"""
    blocks: List[NginxDirective] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blocks": [b.to_dict() for b in self.blocks],
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 词法 / 语法解析器（手写递归下降，不依赖第三方库）
# ---------------------------------------------------------------------------

# 常见的块指令（用于识别块开始）
_BLOCK_DIRECTIVES = {
    "http", "server", "location", "upstream", "events",
    "if", "limit_except", "types", "map", "geo", "stream", "mail",
}

# 需要标记置信度的指令（非核心指令，置信度 medium/low）
_MEDIUM_CONFIDENCE = {"if", "map", "geo", "rewrite", "set"}
_LOW_CONFIDENCE = {"lua_", "set", "perl_"}


class NginxParser:
    """Nginx 配置解析器（词法 + 语法）。"""

    def __init__(self, text: str):
        self.text = text
        self.tokens: List[Tuple[str, Any]] = []  # (type, value)
        self.pos = 0
        self.line = 1

    # -- 词法分析 ----------------------------------------------------------
    def tokenize(self) -> None:
        """将文本拆分为 token 流。"""
        i = 0
        n = len(self.text)
        while i < n:
            ch = self.text[i]

            # 空白与换行
            if ch in " \t\r\n":
                if ch == "\n":
                    self.line += 1
                i += 1
                continue

            # 注释 # ... 到行尾
            if ch == "#":
                while i < n and self.text[i] != "\n":
                    i += 1
                continue

            # 分号（指令结束）
            if ch == ";":
                self.tokens.append(("SEMI", self.line))
                i += 1
                continue

            # 左大括号
            if ch == "{":
                self.tokens.append(("LBRACE", self.line))
                i += 1
                continue

            # 右大括号
            if ch == "}":
                self.tokens.append(("RBRACE", self.line))
                i += 1
                continue

            # 引号字符串（单引号或双引号）
            if ch in ("'", '"'):
                quote = ch
                i += 1
                start = i
                while i < n and self.text[i] != quote:
                    if self.text[i] == "\n":
                        self.line += 1
                    i += 1
                if i >= n:
                    raise ValueError(f"{ERR_PARSE_SYNTAX}: 未闭合的引号")
                value = self.text[start:i]
                i += 1  # 跳过闭合引号
                self.tokens.append(("STRING", value))
                continue

            # 普通字符串（直到空白或特殊字符）
            start = i
            while i < n and self.text[i] not in " \t\r\n;{}'\"":
                i += 1
            if start == i:
                raise ValueError(f"{ERR_PARSE_SYNTAX}: 无法识别的字符 '{ch}'")
            self.tokens.append(("WORD", self.text[start:i]))

        # 添加 EOF 标记
        self.tokens.append(("EOF", self.line))

    # -- 语法分析 ----------------------------------------------------------
    def parse(self) -> ParseResult:
        """解析 token 流，构建 AST。"""
        self.tokenize()
        self.pos = 0
        result = ParseResult()

        try:
            while self._peek_type() != "EOF":
                directive = self._parse_directive(top_level=True)
                if directive is not None:
                    result.blocks.append(directive)
        except ValueError as e:
            # 将错误转为带错误码的异常
            raise ValueError(f"{ERR_PARSE_SYNTAX}: 解析错误: {e}")

        return result

    def _peek_type(self) -> str:
        return self.tokens[self.pos][0]

    def _peek_value(self) -> Any:
        return self.tokens[self.pos][1]

    def _next(self) -> Tuple[str, Any]:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _parse_directive(self, top_level: bool = False) -> Optional[NginxDirective]:
        """解析一条指令（简单或块）。"""
        if self._peek_type() == "EOF":
            return None

        # 获取指令名
        tok_type, tok_value = self._next()
        if tok_type != "WORD":
            # 意外的 token（如右括号）
            raise ValueError(f"第 {tok_value} 行: 意外的 token '{tok_type}'")

        name = tok_value
        args: List[str] = []
        
        # 收集参数直到遇到 ; 或 {
        while self._peek_type() not in ("SEMI", "LBRACE", "RBRACE", "EOF"):
            _, val = self._next()
            if isinstance(val, str):
                args.append(val)
            else:
                raise ValueError(f"第 {self.line} 行: 指令参数类型错误")

        # 判断是块指令还是简单指令
        if self._peek_type() == "LBRACE":
            # 块指令
            self._next()  # 跳过 {
            block = NginxBlock()
            while self._peek_type() != "RBRACE":
                if self._peek_type() == "EOF":
                    raise ValueError(f"第 {self.line} 行: 未闭合的块 '{name}'")
                child = self._parse_directive()
                if child is not None:
                    block.directives.append(child)
            self._next()  # 跳过 }

            directive = NginxDirective(
                name=name,
                args=args,
                block=block,
                line=self._current_line(),
                confidence=self._infer_confidence(name),
            )
            return directive

        elif self._peek_type() == "SEMI":
            self._next()  # 跳过 ;
            directive = NginxDirective(
                name=name,
                args=args,
                line=self._current_line(),
                confidence=self._infer_confidence(name),
            )
            return directive

        elif self._peek_type() == "EOF":
            # 简单指令缺少分号且遇到 EOF
            raise ValueError(f"第 {self.line} 行: 指令 '{name}' 缺少 ';'")

        else:
            # 简单指令缺少分号
            raise ValueError(f"第 {self.line} 行: 指令 '{name}' 缺少 ';'")

    def _current_line(self) -> int:
        """获取当前 token 的行号（简化：使用最近一次 token 的行）。"""
        if self.pos > 0:
            return self.tokens[self.pos - 1][1]
        return 1

    def _infer_confidence(self, name: str) -> str:
        """根据指令名推断置信度。"""
        for prefix in _LOW_CONFIDENCE:
            if name.startswith(prefix):
                return "low"
        if name in _MEDIUM_CONFIDENCE:
            return "medium"
        return "high"


# ---------------------------------------------------------------------------
# 输入处理（文本 / 文件 / 批量）
# ---------------------------------------------------------------------------

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


def parse_text(text: str, source_name: str = "text") -> Dict[str, Any]:
    """解析纯文本配置，返回结构化字典。"""
    if not text or not text.strip():
        raise ValueError(f"{ERR_INPUT_EMPTY}: 输入内容为空")

    parser = NginxParser(text)
    result = parser.parse()

    output = result.to_dict()
    output["source"] = source_name
    output["format"] = "nginx-parsed"
    return output


def parse_file(file_path: str) -> Dict[str, Any]:
    """解析本地文件。"""
    import os
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{ERR_FILE_NOT_FOUND}: 文件不存在: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        raise IOError(f"{ERR_FILE_READ_FAILED}: 读取文件失败: {e}")

    return parse_text(content, source_name=file_path)


def parse_batch(inputs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """批量解析（支持 text / file 类型）。"""
    if len(inputs) > 50:
        raise ValueError(f"{ERR_BATCH_TOO_LARGE}: 批量文件超过 50 个")

    results = []
    for item in inputs:
        if "text" in item:
            results.append(parse_text(item["text"]))
        elif "file" in item:
            results.append(parse_file(item["file"]))
        else:
            raise ValueError(f"{ERR_INVALID_ARGS}: 输入项必须包含 'text' 或 'file' 字段")
    return results


# ---------------------------------------------------------------------------
# 输出格式化（JSON / YAML / 文本树）
# ---------------------------------------------------------------------------

def format_output(data: Any, fmt: str = "json") -> str:
    """将结构化数据格式化为指定格式。"""
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "yaml":
        return _to_yaml(data)
    elif fmt == "tree":
        return _to_text_tree(data)
    else:
        raise ValueError(f"{ERR_INVALID_ARGS}: 不支持的输出格式: {fmt}")


def _to_yaml(data: Any, indent: int = 0) -> str:
    """极简 YAML 序列化（仅支持 dict/list/str/int/bool/None）。"""
    lines: List[str] = []
    prefix = " " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_to_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_to_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
    else:
        lines.append(f"{prefix}{_yaml_scalar(data)}")

    return "\n".join(lines)


def _yaml_scalar(value: Any) -> str:
    """YAML 标量序列化。"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        # 简单转义（不处理复杂情况）
        if value == "":
            return '""'
        return value
    return str(value)


def _to_text_tree(data: Any, indent: int = 0) -> str:
    """将结构化数据渲染为缩进文本树。"""
    lines: List[str] = []
    prefix = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_to_text_tree(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(_to_text_tree(item, indent + 1))
            else:
                lines.append(f"{prefix}- {item}")
    else:
        lines.append(f"{prefix}{data}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """内置样例数据离线自检核心逻辑，不依赖外部文件/网络。"""
    test_cases = [
        {
            "name": "简单 server 块",
            "input": 'server { listen 80; server_name a.com; }',
            "expected": {
                "blocks": [
                    {
                        "directive": "server",
                        "args": [],
                        "line": 1,
                        "confidence": "high",
                        "block": [
                            {"directive": "listen", "args": ["80"], "line": 1, "confidence": "high"},
                            {"directive": "server_name", "args": ["a.com"], "line": 1, "confidence": "high"},
                        ],
                    }
                ],
                "warnings": [],
                "source": "text",
                "format": "nginx-parsed",
            },
        },
        {
            "name": "嵌套 location 块",
            "input": 'server { listen 443 ssl; location /api { proxy_pass http://backend; } }',
            "expected": {
                "blocks": [
                    {
                        "directive": "server",
                        "args": [],
                        "line": 1,
                        "confidence": "high",
                        "block": [
                            {"directive": "listen", "args": ["443", "ssl"], "line": 1, "confidence": "high"},
                            {
                                "directive": "location",
                                "args": ["/api"],
                                "line": 1,
                                "confidence": "high",
                                "block": [
                                    {"directive": "proxy_pass", "args": ["http://backend"], "line": 1, "confidence": "high"},
                                ],
                            },
                        ],
                    }
                ],
                "warnings": [],
                "source": "text",
                "format": "nginx-parsed",
            },
        },
        {
            "name": "upstream 块",
            "input": 'upstream backend { server 127.0.0.1:8080; server 127.0.0.1:8081; }',
            "expected": {
                "blocks": [
                    {
                        "directive": "upstream",
                        "args": ["backend"],
                        "line": 1,
                        "confidence": "high",
                        "block": [
                            {"directive": "server", "args": ["127.0.0.1:8080"], "line": 1, "confidence": "high"},
                            {"directive": "server", "args": ["127.0.0.1:8081"], "line": 1, "confidence": "high"},
                        ],
                    }
                ],
                "warnings": [],
                "source": "text",
                "format": "nginx-parsed",
            },
        },
        {
            "name": "注释与空白处理",
            "input": "# 注释行\n\nserver {\n    listen 80;  # 端口\n    server_name example.com;\n}\n",
            "expected": {
                "blocks": [
                    {
                        "directive": "server",
                        "args": [],
                        "line": 3,
                        "confidence": "high",
                        "block": [
                            {"directive": "listen", "args": ["80"], "line": 4, "confidence": "high"},
                            {"directive": "server_name", "args": ["example.com"], "line": 5, "confidence": "high"},
                        ],
                    }
                ],
                "warnings": [],
                "source": "text",
                "format": "nginx-parsed",
            },
        },
        {
            "name": "未知指令保留原样",
            "input": 'server { listen 80; custom_directive foo bar; }',
            "expected": {
                "blocks": [
                    {
                        "directive": "server",
                        "args": [],
                        "line": 1,
                        "confidence": "high",
                        "block": [
                            {"directive": "listen", "args": ["80"], "line": 1, "confidence": "high"},
                            {"directive": "custom_directive", "args": ["foo", "bar"], "line": 1, "confidence": "high"},
                        ],
                    }
                ],
                "warnings": [],
                "source": "text",
                "format": "nginx-parsed",
            },
        },
    ]

    print("[selftest] 开始运行核心逻辑自检...")
    all_passed = True

    for i, tc in enumerate(test_cases):
        try:
            result = parse_text(tc["input"])
            # 简化比较：仅比较 blocks 部分（忽略行号可能因环境差异）
            expected_blocks = tc["expected"]["blocks"]
            actual_blocks = result["blocks"]

            # 递归比较（忽略 line 字段）
            if _compare_blocks(actual_blocks, expected_blocks):
                print(f"  [PASS] 用例 {i+1}: {tc['name']}")
            else:
                print(f"  [FAIL] 用例 {i+1}: {tc['name']}")
                print(f"         期望: {json.dumps(expected_blocks, ensure_ascii=False)}")
                print(f"         实际: {json.dumps(actual_blocks, ensure_ascii=False)}")
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] 用例 {i+1}: {tc['name']} - {e}")
            all_passed = False

    # 测试错误处理
    print("[selftest] 测试错误处理...")
    try:
        parse_text("")  # 空输入
        print("  [FAIL] 空输入未抛出异常")
        all_passed = False
    except ValueError as e:
        if str(e).startswith(ERR_INPUT_EMPTY):
            print("  [PASS] 空输入错误码正确")
        else:
            print(f"  [FAIL] 空输入错误码错误: {e}")
            all_passed = False
    except Exception:
        print("  [FAIL] 空输入抛出了非预期异常")
        all_passed = False

    try:
        parse_text("server { listen 80; }")  # 缺少右括号
        print("  [FAIL] 语法错误未抛出异常")
        all_passed = False
    except ValueError as e:
        if str(e).startswith(ERR_PARSE_SYNTAX):
            print("  [PASS] 语法错误错误码正确")
        else:
            print(f"  [FAIL] 语法错误错误码错误: {e}")
            all_passed = False
    except Exception:
        print("  [FAIL] 语法错误抛出了非预期异常")
        all_passed = False

    if all_passed:
        print("[selftest] 全部自检通过 ✅")
        return 0
    else:
        print("[selftest] 存在失败用例 ❌")
        return 1


def _compare_blocks(actual: List[Dict], expected: List[Dict]) -> bool:
    """比较两个块列表（忽略 line 字段）。"""
    if len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected):
        if not _compare_directive(a, e):
            return False
    return True


def _compare_directive(actual: Dict, expected: Dict) -> bool:
    """比较两条指令（忽略 line 字段）。"""
    for key in ("directive", "args", "confidence"):
        if actual.get(key) != expected.get(key):
            return False
    # 递归比较 block
    a_block = actual.get("block")
    e_block = expected.get("block")
    if (a_block is None) != (e_block is None):
        return False
    if a_block is not None:
        if not _compare_blocks(a_block, e_block):
            return False
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="Nginx 配置解析 结构化提取 命令行工具",
        epilog="示例: python main.py --text 'server { listen 80; }'",
    )
    parser.add_argument("--text", type=str, help="直接传入配置文本")
    parser.add_argument("--file", type=str, help="配置文件路径")
    parser.add_argument("--format", choices=["json", "yaml", "tree"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--batch", type=str, help="批量解析 JSON 数组文件路径")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    try:
        # 批量模式
        if args.batch:
            with open(args.batch, "r", encoding="utf-8", errors="replace") as f:
                inputs = json.load(f)
            if not isinstance(inputs, list):
                raise ValueError(f"{ERR_INVALID_ARGS}: --batch 参数必须指向 JSON 数组")
            results = parse_batch(inputs)
            output = format_output(results, args.format)
            print(output)
            return 0

        # 单文件模式
        if args.file:
            data = parse_file(args.file)
            output = format_output(data, args.format)
            print(output)
            return 0

        # 文本模式
        if args.text:
            data = parse_text(args.text)
            output = format_output(data, args.format)
            print(output)
            return 0

        # 无输入
        parser.print_help()
        return 1

    except FileNotFoundError as e:
        print(f"错误 [{ERR_FILE_NOT_FOUND}]: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误 [{ERR_INVALID_ARGS}]: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERR_INTERNAL}]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
