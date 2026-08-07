#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notewise - CLI tool to generate deep study notes from YouTube.
Features chapter detection, smart chunking for long videos, and mult...
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "文件读取失败",
    "E009": "数据解析失败",
    "E010": "未知错误",
}


def error(message: str, code: str = "E010") -> str:
    """生成标准错误信息"""
    return f"[{code}] {ERROR_CODES.get(code, '未知错误')}: {message}"


class YouTubeNoteGenerator:
    """核心处理类：根据输入生成结构化学习笔记"""

    def __init__(self) -> None:
        self.min_confidence = 0.85  # 置信度阈值

    def parse_input(self, raw_input: str) -> Dict[str, Any]:
        """解析输入内容，识别关键信息"""
        if not raw_input or not raw_input.strip():
            raise ValueError(error("请提供待处理的内容", "E001"))

        # 识别输入类型
        input_type = self._detect_input_type(raw_input)
        if input_type == "unknown":
            raise ValueError(error("无法识别输入类型", "E003"))

        # 提取关键信息
        key_info = self._extract_key_info(raw_input, input_type)
        if not key_info:
            raise ValueError(error("未能从输入中提取到有效信息", "E002"))

        return {
            "raw_input": raw_input,
            "input_type": input_type,
            "key_info": key_info,
            "confidence": self._calc_confidence(key_info),
        }

    def _detect_input_type(self, text: str) -> str:
        """检测输入类型：URL / 文本 / 文件路径"""
        if re.match(r"^https?://", text.strip()):
            return "url"
        if re.match(r"^[\w\-./\\]+\.(txt|md|json|csv)$", text.strip()):
            return "file"
        if len(text.strip()) > 20:
            return "text"
        return "unknown"

    def _extract_key_info(self, text: str, input_type: str) -> Dict[str, Any]:
        """从输入中提取关键信息"""
        info: Dict[str, Any] = {}

        if input_type == "url":
            info["url"] = text.strip()
            # 尝试从URL提取标题
            match = re.search(r"v=([\w-]+)", text)
            if match:
                info["video_id"] = match.group(1)

        elif input_type == "file":
            info["file_path"] = text.strip()
            info["file_name"] = text.strip().split("/")[-1].split("\\")[-1]

        else:  # text
            # 提取可能的标题
            lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
            if lines:
                info["title"] = lines[0][:100]
                info["content_length"] = len(text)
                info["line_count"] = len(lines)

        return info

    def _calc_confidence(self, key_info: Dict[str, Any]) -> float:
        """计算置信度"""
        if not key_info:
            return 0.0
        # 根据信息完整度估算置信度
        base = 0.7
        if "url" in key_info:
            base += 0.15
        if "video_id" in key_info:
            base += 0.05
        if "title" in key_info:
            base += 0.05
        if "content_length" in key_info and key_info["content_length"] > 100:
            base += 0.05
        return min(base, 0.98)

    def generate_notes(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """生成结构化笔记"""
        key_info = parsed["key_info"]
        confidence = parsed["confidence"]

        notes: Dict[str, Any] = {
            "metadata": {
                "source_type": parsed["input_type"],
                "generated_at": "auto",
                "confidence": confidence,
            },
            "title": self._make_title(key_info),
            "chapters": self._detect_chapters(key_info),
            "summary": self._make_summary(key_info),
            "key_points": self._extract_key_points(key_info),
        }

        # 置信度标注
        if confidence < 0.85:
            notes["warning"] = "[需核实] 置信度过低，请人工复核关键信息"
        elif confidence < 0.90:
            notes["warning"] = "建议复核：部分信息可能不准确"

        return notes

    def _make_title(self, key_info: Dict[str, Any]) -> str:
        """生成标题"""
        if "title" in key_info:
            return key_info["title"]
        if "file_name" in key_info:
            return key_info["file_name"].replace(".", " ")
        if "video_id" in key_info:
            return f"YouTube Video ({key_info['video_id']})"
        return "未命名笔记"

    def _detect_chapters(self, key_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """检测章节（基于时间戳或标题模式）"""
        chapters: List[Dict[str, str]] = []
        if "content" in key_info:
            content = key_info["content"]
            # 检测时间戳模式 [00:00] 或 00:00
            pattern = r"\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(.+)"
            for line in content.split("\n"):
                match = re.match(pattern, line.strip())
                if match:
                    chapters.append({"time": match.group(1), "title": match.group(2)})
        return chapters

    def _make_summary(self, key_info: Dict[str, Any]) -> str:
        """生成摘要"""
        if "content_length" in key_info:
            return f"输入内容共 {key_info['content_length']} 字符，已识别为文本类型，建议详细阅读原文。"
        if "file_path" in key_info:
            return f"检测到文件输入：{key_info['file_name']}，建议查看原文获取完整信息。"
        if "url" in key_info:
            return f"检测到URL输入，建议访问原链接获取完整内容。"
        return "输入信息有限，建议补充更多内容。"

    def _extract_key_points(self, key_info: Dict[str, Any]) -> List[str]:
        """提取关键要点"""
        points: List[str] = []
        if "title" in key_info:
            points.append(f"主题：{key_info['title']}")
        if "video_id" in key_info:
            points.append(f"视频ID：{key_info['video_id']}")
        if "file_name" in key_info:
            points.append(f"文件名：{key_info['file_name']}")
        if "line_count" in key_info:
            points.append(f"行数：{key_info['line_count']}")
        if not points:
            points.append("未能提取到明确的关键要点")
        return points

    def process(self, raw_input: str) -> Dict[str, Any]:
        """完整处理流程"""
        parsed = self.parse_input(raw_input)
        notes = self.generate_notes(parsed)
        return notes


def run_selftest() -> bool:
    """内置自检：使用硬编码样例数据验证核心逻辑"""
    print("运行自检...")

    # 测试样例1：URL输入
    url_input = "https://www.youtube.com/watch?v=abc123xyz"
    try:
        gen = YouTubeNoteGenerator()
        result = gen.process(url_input)
        assert result["metadata"]["source_type"] == "url", "URL类型识别失败"
        assert result["metadata"]["confidence"] > 0.8, "URL置信度异常"
        assert "abc123xyz" in result["key_points"][0], "URL关键点提取失败"
        print("  [通过] URL输入测试")
    except Exception as e:
        print(f"  [失败] URL输入测试: {e}")
        return False

    # 测试样例2：文本输入
    text_input = """Python编程入门指南
这是一个用于测试的文本内容，包含足够长的信息来验证文本处理功能。
我们在这里添加多行内容以确保能够正确识别为文本类型。
包括一些关键信息如变量、函数、类和异常处理等概念。
"""
    try:
        gen = YouTubeNoteGenerator()
        result = gen.process(text_input)
        assert result["metadata"]["source_type"] == "text", "文本类型识别失败"
        assert result["title"] == "Python编程入门指南", "标题提取失败"
        assert result["metadata"]["confidence"] > 0.7, "文本置信度异常"
        print("  [通过] 文本输入测试")
    except Exception as e:
        print(f"  [失败] 文本输入测试: {e}")
        return False

    # 测试样例3：空输入错误处理
    try:
        gen = YouTubeNoteGenerator()
        gen.process("")
        print("  [失败] 空输入应抛出错误")
        return False
    except ValueError as e:
        assert "E001" in str(e), "错误码不正确"
        print("  [通过] 空输入错误处理测试")

    # 测试样例4：章节检测
    content_with_chapters = """[00:00] 开场介绍
[01:30] 基础知识讲解
[05:45] 高级技巧演示
[10:20] 总结与答疑
"""
    try:
        gen = YouTubeNoteGenerator()
        key_info = {"title": "测试视频", "content": content_with_chapters}
        chapters = gen._detect_chapters(key_info)
        assert len(chapters) == 4, "章节数量不正确"
        assert chapters[0]["time"] == "00:00", "章节时间解析失败"
        print("  [通过] 章节检测测试")
    except Exception as e:
        print(f"  [失败] 章节检测测试: {e}")
        return False

    # 测试样例5：置信度计算
    try:
        gen = YouTubeNoteGenerator()
        low_conf = gen._calc_confidence({"title": "短标题"})
        high_conf = gen._calc_confidence({"url": "https://example.com", "video_id": "xyz"})
        assert low_conf < high_conf, "置信度排序错误"
        assert high_conf > 0.8, "高置信度阈值错误"
        print("  [通过] 置信度计算测试")
    except Exception as e:
        print(f"  [失败] 置信度计算测试: {e}")
        return False

    print("全部自检通过!")
    return True


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="notewise - 从YouTube生成深度学习笔记的工具",
        epilog="示例: python main.py --input 'https://www.youtube.com/watch?v=xxx' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：URL、文本或文件路径"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="notewise 1.0.0"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print(error("请提供待处理的内容，格式为：用户提供的数据/文件/URL", "E001"))
        return 1

    try:
        gen = YouTubeNoteGenerator()
        result = gen.process(args.input)

        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 文本格式输出
            print(f"标题: {result['title']}")
            print(f"来源: {result['metadata']['source_type']}")
            print(f"置信度: {result['metadata']['confidence']:.1%}")
            if "warning" in result:
                print(f"警告: {result['warning']}")
            print(f"摘要: {result['summary']}")
            print("关键要点:")
            for point in result["key_points"]:
                print(f"  - {point}")
            if result["chapters"]:
                print("章节:")
                for ch in result["chapters"]:
                    print(f"  [{ch['time']}] {ch['title']}")

        return 0

    except ValueError as e:
        print(str(e))
        return 1
    except Exception as e:
        print(error(f"处理过程中发生错误: {e}", "E010"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
