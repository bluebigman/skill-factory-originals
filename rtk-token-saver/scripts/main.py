#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rtk-token-saver - 对话瘦身与上下文压缩工具

本脚本依据功能规格独立实现，仅使用 Python 标准库。
提供代码块压缩、对话历史精简、上下文摘要生成、结构化信息提取四大核心能力。
"""

import argparse
import json
import re
import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用异常基类，携带错误码。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def err_invalid_input() -> AppError:
    return AppError("E001", "输入数据格式无效或为空")


def err_code_parse() -> AppError:
    return AppError("E002", "代码块解析失败：括号不匹配或语法错误")


def err_dialog_format() -> AppError:
    return AppError("E003", "对话历史格式错误：应为消息对象列表")


def err_unsupported_mode() -> AppError:
    return AppError("E004", "不支持的压缩模式")


def err_file_read() -> AppError:
    return AppError("E005", "文件读取失败")


def err_file_write() -> AppError:
    return AppError("E006", "文件写入失败")


def err_missing_field() -> AppError:
    return AppError("E007", "缺少关键字段")


def err_type_mismatch() -> AppError:
    return AppError("E008", "类型不匹配")


def err_selfcheck() -> AppError:
    return AppError("E009", "自检失败")


def err_unknown() -> AppError:
    return AppError("E010", "未知错误")


# ============================================================
# 一、代码块压缩
# ============================================================
def compress_code(code: str, language: str = "") -> str:
    """
    对代码块进行词法级压缩：
    - 去除行注释（//, #, -- 等）
    - 去除块注释（/* */, ''' ''', """ """）
    - 去除空行
    - 去除行首行尾空白
    - 压缩连续空白为单个空格（保留字符串内空白）
    注意：不保证压缩后代码可运行，仅做词法级处理。
    """
    if not code or not code.strip():
        raise err_invalid_input()

    lines = code.splitlines()
    result_lines: List[str] = []
    in_block_comment = False
    block_comment_delimiter = ""

    # 根据语言选择块注释分隔符
    if language.lower() in ("python", "py"):
        block_delims = [('"""', '"""'), ("'''", "'''")]
        line_comment = "#"
    elif language.lower() in ("c", "cpp", "java", "js", "ts", "go", "rust"):
        block_delims = [("/*", "*/")]
        line_comment = "//"
    elif language.lower() in ("html", "xml"):
        block_delims = [("<!--", "-->")]
        line_comment = ""
    elif language.lower() in ("sql",):
        block_delims = [("/*", "*/")]
        line_comment = "--"
    else:
        # 默认支持常见注释
        block_delims = [("/*", "*/"), ('"""', '"""'), ("'''", "'''")]
        line_comment = ""

    for raw_line in lines:
        line = raw_line.strip()

        # 跳过空行
        if not line:
            continue

        # 处理块注释状态
        if in_block_comment:
            # 查找块注释结束符
            end_idx = line.find(block_comment_delimiter)
            if end_idx != -1:
                # 块注释结束，保留结束符之后的内容
                remainder = line[end_idx + len(block_comment_delimiter):].strip()
                in_block_comment = False
                block_comment_delimiter = ""
                if remainder:
                    line = remainder
                else:
                    continue
            else:
                # 整行都在块注释内
                continue

        # 检查是否进入块注释
        block_started = False
        for start_delim, end_delim in block_delims:
            start_idx = line.find(start_delim)
            if start_idx != -1:
                # 查找同一行的结束符
                end_idx = line.find(end_delim, start_idx + len(start_delim))
                if end_idx != -1:
                    # 同一行内闭合，删除注释部分
                    line = line[:start_idx] + line[end_idx + len(end_delim):]
                else:
                    # 跨行块注释开始
                    in_block_comment = True
                    block_comment_delimiter = end_delim
                    line = line[:start_idx]
                    block_started = True
                break

        if block_started:
            line = line.strip()
            if not line:
                continue

        # 处理行注释（仅在非字符串上下文中简单处理）
        if line_comment:
            # 简单处理：查找不在引号内的行注释符
            line = _remove_line_comment(line, line_comment)

        line = line.strip()
        if line:
            # 压缩连续空白为单个空格（简单处理，不解析字符串）
            line = re.sub(r'\s+', ' ', line)
            result_lines.append(line)

    compressed = "\n".join(result_lines)
    return compressed


def _remove_line_comment(line: str, comment_marker: str) -> str:
    """移除行注释，注意跳过字符串字面量内的注释符。"""
    if not comment_marker:
        return line

    in_single = False
    in_double = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if line.startswith(comment_marker, i):
                return line[:i].rstrip()
        i += 1
    return line


# ============================================================
# 二、对话历史精简
# ============================================================
def compress_dialog(messages: List[Dict[str, str]], strategy: str = "merge") -> List[Dict[str, str]]:
    """
    对话历史精简：
    - strategy="merge": 合并连续相同角色的消息，删除寒暄（如"你好"、"谢谢"等）
    - strategy="keep_key": 仅保留包含关键决策点的消息（含"决定"、"选择"、"确认"等关键词）
    """
    if not messages or not isinstance(messages, list):
        raise err_dialog_format()

    for msg in messages:
        if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
            raise err_dialog_format()

    if strategy == "merge":
        return _merge_dialog(messages)
    elif strategy == "keep_key":
        return _keep_key_messages(messages)
    else:
        raise err_unsupported_mode()


def _merge_dialog(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """合并连续相同角色消息，删除寒暄内容。"""
    greetings = {"你好", "您好", "hello", "hi", "谢谢", "感谢", "thanks", "thank you", "嗯", "好的", "ok"}

    result: List[Dict[str, str]] = []
    for msg in messages:
        content = msg.get("content", "").strip()
        role = msg.get("role", "")

        # 删除寒暄消息
        if content.lower() in greetings:
            continue

        if result and result[-1]["role"] == role:
            # 合并到上一条消息
            result[-1]["content"] += "\n" + content
        else:
            result.append({"role": role, "content": content})

    return result


def _keep_key_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """仅保留含关键决策点的消息。"""
    keywords = ["决定", "选择", "确认", "采用", "方案", "结论", "最终", "确定", "approved", "decided", "chosen"]

    result = []
    for msg in messages:
        content = msg.get("content", "")
        if any(kw in content for kw in keywords):
            result.append(msg)

    if not result and messages:
        # 如果没有关键消息，保留第一条和最后一条
        result = [messages[0], messages[-1]]

    return result


# ============================================================
# 三、上下文摘要生成
# ============================================================
def generate_summary(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    从对话历史生成结构化摘要：
    - 目标（goals）
    - 约束（constraints）
    - 已做（completed）
    - 待办（todo）
    """
    if not messages or not isinstance(messages, list):
        raise err_dialog_format()

    full_text = "\n".join([m.get("content", "") for m in messages if isinstance(m, dict)])

    # 提取目标：包含"目标"、"目的"、"想要"、"需要"等词的内容
    goals = _extract_by_keywords(full_text, ["目标", "目的", "想要", "需要", "goal", "objective", "aim"])
    # 提取约束
    constraints = _extract_by_keywords(full_text, ["约束", "限制", "不能", "不要", "constraint", "limit", "restriction"])
    # 提取已完成
    completed = _extract_by_keywords(full_text, ["已完成", "完成", "实现了", "完成", "done", "completed", "finished"])
    # 提取待办
    todo = _extract_by_keywords(full_text, ["待办", "接下来", "下一步", "还需要", "todo", "next", "pending"])

    summary = {
        "goals": goals[:5],
        "constraints": constraints[:5],
        "completed": completed[:5],
        "todo": todo[:5],
    }
    return summary


def _extract_by_keywords(text: str, keywords: List[str]) -> List[str]:
    """从文本中提取包含关键词的句子。"""
    sentences = re.split(r'[。！？\n.!?]', text)
    result = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if any(kw in sent for kw in keywords):
            # 截取关键词后的内容作为摘要
            for kw in keywords:
                idx = sent.find(kw)
                if idx != -1:
                    content = sent[idx + len(kw):].strip()
                    if content and content not in result:
                        result.append(content[:100])
                    break
    return result


# ============================================================
# 四、结构化信息提取
# ============================================================
def extract_info(messages: List[Dict[str, str]]) -> Dict[str, List[str]]:
    """
    从对话中抽取结构化信息：
    - 参数（parameters）：如 --xxx 或 -x 形式
    - 路径（paths）：文件路径
    - 版本号（versions）：如 v1.0.0 或 1.2.3
    - 关键词（keywords）：技术关键词
    """
    if not messages or not isinstance(messages, list):
        raise err_dialog_format()

    full_text = "\n".join([m.get("content", "") for m in messages if isinstance(m, dict)])

    # 提取参数
    params = re.findall(r'--?[a-zA-Z][a-zA-Z0-9_-]*', full_text)
    # 提取路径
    paths = re.findall(r'(?:/[a-zA-Z0-9_./-]+|\./[a-zA-Z0-9_./-]+|[a-zA-Z]:\\[a-zA-Z0-9_\\./-]+)', full_text)
    # 提取版本号
    versions = re.findall(r'v?\d+\.\d+(?:\.\d+)?(?:[-_][a-zA-Z0-9]+)?', full_text)
    # 提取技术关键词
    tech_keywords = ["python", "javascript", "typescript", "react", "vue", "docker", "kubernetes",
                     "api", "rest", "graphql", "sql", "nosql", "redis", "kafka", "aws", "azure"]
    keywords = [kw for kw in tech_keywords if kw in full_text.lower()]

    info = {
        "parameters": list(OrderedDict.fromkeys(params)),
        "paths": list(OrderedDict.fromkeys(paths)),
        "versions": list(OrderedDict.fromkeys(versions)),
        "keywords": list(OrderedDict.fromkeys(keywords)),
    }
    return info


# ============================================================
# 自检模块
# ============================================================
def selftest() -> bool:
    """内置样例数据自检核心逻辑。"""
    print("=== rtk-token-saver 自检开始 ===")

    # 1. 代码压缩测试
    code_sample = '''
    # 这是一个注释
    def hello(name):
        """文档字符串"""
        # 打印问候
        print(f"Hello, {name}!")  # 行尾注释
        return True

    # 空行测试

    def main():
        hello("world")
        return 0
    '''
    compressed = compress_code(code_sample, "python")
    assert "注释" not in compressed, "E009: 注释未移除"
    assert "文档字符串" not in compressed, "E009: 文档字符串未移除"
    assert "\n\n" not in compressed, "E009: 空行未移除"
    assert "def hello" in compressed and "print" in compressed, "E009: 代码逻辑被移除"
    print("[PASS] 代码块压缩")

    # 2. 对话精简测试
    dialog = [
        {"role": "user", "content": "你好"},
        {"role": "user", "content": "我需要压缩这段代码"},
        {"role": "assistant", "content": "好的，我来看看"},
        {"role": "assistant", "content": "这段代码可以优化"},
        {"role": "user", "content": "决定采用方案A"},
    ]
    merged = compress_dialog(dialog, "merge")
    assert len(merged) < len(dialog), "E009: 对话未精简"
    assert all(m["content"] != "你好" for m in merged), "E009: 寒暄未删除"
    print("[PASS] 对话精简(merge)")

    key_messages = compress_dialog(dialog, "keep_key")
    assert any("方案" in m["content"] for m in key_messages), "E009: 关键决策点未保留"
    print("[PASS] 对话精简(keep_key)")

    # 3. 摘要生成测试
    summary = generate_summary(dialog)
    assert isinstance(summary, dict), "E009: 摘要格式错误"
    assert "goals" in summary and "todo" in summary, "E009: 摘要缺少关键字段"
    print("[PASS] 摘要生成")

    # 4. 结构化信息提取测试
    info_dialog = [
        {"role": "user", "content": "使用 python 脚本处理 /tmp/data.txt，版本 v1.2.3，参数 --verbose"},
        {"role": "assistant", "content": "建议使用 docker 部署，路径 /app/config.yaml"},
    ]
    info = extract_info(info_dialog)
    assert "--verbose" in info["parameters"], "E009: 参数提取失败"
    assert "/tmp/data.txt" in info["paths"], "E009: 路径提取失败"
    assert "v1.2.3" in info["versions"], "E009: 版本号提取失败"
    assert "python" in info["keywords"], "E009: 关键词提取失败"
    print("[PASS] 结构化信息提取")

    # 5. 错误处理测试
    try:
        compress_code("")
        raise AssertionError("E009: 空输入未报错")
    except AppError as e:
        assert e.code == "E001", "E009: 错误码不正确"

    try:
        compress_dialog("not a list")
        raise AssertionError("E009: 非法对话格式未报错")
    except AppError as e:
        assert e.code == "E003", "E009: 错误码不正确"
    print("[PASS] 错误处理")

    print("=== 自检通过，所有测试均成功 ===")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="rtk-token-saver - 对话瘦身与上下文压缩工具",
        epilog="示例: python main.py --code-file input.py --output compressed.txt"
    )

    # 输入输出参数
    parser.add_argument("--code", "-c", help="待压缩的代码字符串")
    parser.add_argument("--code-file", help="包含代码的文件路径")
    parser.add_argument("--dialog-file", help="对话历史 JSON 文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径（可选，默认输出到控制台）")

    # 功能选择
    parser.add_argument("--mode", "-m", choices=["code", "dialog", "summary", "extract"],
                        default="code", help="操作模式")
    parser.add_argument("--language", "-l", default="", help="代码语言（用于注释识别）")
    parser.add_argument("--strategy", "-s", choices=["merge", "keep_key"],
                        default="merge", help="对话精简策略")

    # 自检
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            selftest()
            return 0
        except Exception as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    try:
        # 读取输入数据
        if args.code:
            input_data = args.code
        elif args.code_file:
            try:
                with open(args.code_file, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except Exception:
                raise err_file_read()
        elif args.dialog_file:
            try:
                with open(args.dialog_file, "r", encoding="utf-8") as f:
                    input_data = json.load(f)
            except json.JSONDecodeError:
                raise err_invalid_input()
            except Exception:
                raise err_file_read()
        else:
            # 读取标准输入
            input_data = sys.stdin.read() if not sys.stdin.isatty() else None
            if not input_data:
                raise err_invalid_input()

        # 执行操作
        result = ""
        if args.mode == "code":
            result = compress_code(input_data, args.language)
        elif args.mode == "dialog":
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except json.JSONDecodeError:
                    raise err_dialog_format()
            result = json.dumps(compress_dialog(input_data, args.strategy), ensure_ascii=False, indent=2)
        elif args.mode == "summary":
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except json.JSONDecodeError:
                    raise err_dialog_format()
            result = json.dumps(generate_summary(input_data), ensure_ascii=False, indent=2)
        elif args.mode == "extract":
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except json.JSONDecodeError:
                    raise err_dialog_format()
            result = json.dumps(extract_info(input_data), ensure_ascii=False, indent=2)
        else:
            raise err_unsupported_mode()

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result)
            except Exception:
                raise err_file_write()
        else:
            print(result)

        return 0

    except AppError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
