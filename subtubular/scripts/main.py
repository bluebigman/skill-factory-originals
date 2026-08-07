#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subtubular - 视频字幕检索与元数据处理工具

本脚本依据功能规格独立实现（clean-room），提供：
- 字幕/元数据文本的结构化解析与全文检索
- 置信度评估与标注
- 批量处理能力
- 内置离线自检（--selftest）

错误码说明：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 文件读取失败
    E007: 文件写入失败
    E008: 参数错误
    E009: 内部逻辑错误
    E010: 自检失败

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SubtitleItem:
    """单条字幕或元数据条目"""
    text: str
    start_time: Optional[float] = None   # 秒
    end_time: Optional[float] = None     # 秒
    speaker: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessResult:
    """处理结果"""
    items: List[SubtitleItem] = field(default_factory=list)
    query: str = ""
    matches: List[Tuple[int, float]] = field(default_factory=list)  # (index, score)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理引擎
# ============================================================

class SubtitleProcessor:
    """字幕处理核心类"""

    # 置信度阈值
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.85

    def __init__(self) -> None:
        self._items: List[SubtitleItem] = []

    def load_data(self, raw_data: Any) -> None:
        """
        加载并解析输入数据。
        支持格式：
            - 字符串：按行解析，支持 "时间戳: 文本" 或纯文本
            - 列表/元组：元素为字符串或 dict
            - dict：包含 'items' 或 'subtitles' 键
        """
        if raw_data is None:
            raise ValueError("E001: 输入为空，请提供待处理的内容")

        self._items = []
        parsed = self._parse_raw(raw_data)

        if not parsed:
            raise ValueError("E002: 关键信息缺失，未能从输入中提取有效内容")

        for entry in parsed:
            if isinstance(entry, dict):
                item = self._parse_dict_entry(entry)
            elif isinstance(entry, str):
                item = self._parse_string_entry(entry)
            else:
                raise ValueError(f"E003: 输入格式错误，不支持的条目类型: {type(entry)}")
            self._items.append(item)

    def _parse_raw(self, raw: Any) -> List[Any]:
        """将原始输入转换为条目列表"""
        if isinstance(raw, str):
            # 按行分割，过滤空行
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            return lines
        elif isinstance(raw, (list, tuple)):
            return list(raw)
        elif isinstance(raw, dict):
            for key in ("items", "subtitles", "data"):
                if key in raw:
                    val = raw[key]
                    if isinstance(val, list):
                        return val
                    elif isinstance(val, str):
                        return [ln.strip() for ln in val.splitlines() if ln.strip()]
            # 没有找到有效键，尝试将整个 dict 作为单条
            return [raw]
        else:
            raise ValueError(f"E003: 输入格式错误，不支持的数据类型: {type(raw)}")

    def _parse_dict_entry(self, entry: Dict[str, Any]) -> SubtitleItem:
        """从 dict 解析条目"""
        text = entry.get("text") or entry.get("content") or entry.get("subtitle")
        if not text:
            raise ValueError("E002: 关键信息缺失，条目中缺少文本内容")

        item = SubtitleItem(text=str(text))
        # 时间字段
        for key in ("start_time", "start", "begin"):
            if key in entry:
                item.start_time = self._to_float(entry[key])
                break
        for key in ("end_time", "end", "finish"):
            if key in entry:
                item.end_time = self._to_float(entry[key])
                break
        # 说话人
        if "speaker" in entry:
            item.speaker = str(entry["speaker"])
        # 其他元数据
        for key in ("metadata", "meta", "extra"):
            if key in entry and isinstance(entry[key], dict):
                item.metadata = dict(entry[key])
                break
        return item

    def _parse_string_entry(self, entry: str) -> SubtitleItem:
        """从字符串解析条目，支持格式：
        1. [00:12.34] 文本内容
        2. 00:12.34 --> 00:15.67 文本内容
        3. 纯文本
        """
        entry = entry.strip()
        if not entry:
            raise ValueError("E002: 关键信息缺失，空字符串无法解析")

        # 尝试匹配 [mm:ss.xx] 格式
        m = re.match(r"^\[(\d+):(\d+(?:\.\d+)?)\]\s*(.+)$", entry)
        if m:
            minutes, seconds, text = m.groups()
            start = int(minutes) * 60 + float(seconds)
            return SubtitleItem(text=text.strip(), start_time=start)

        # 尝试匹配 mm:ss.xx --> mm:ss.xx 格式
        m = re.match(
            r"^(\d+):(\d+(?:\.\d+)?)\s*-->\s*(\d+):(\d+(?:\.\d+)?)\s*(.*)$",
            entry
        )
        if m:
            m1, s1, m2, s2, text = m.groups()
            start = int(m1) * 60 + float(s1)
            end = int(m2) * 60 + float(s2)
            return SubtitleItem(text=text.strip(), start_time=start, end_time=end)

        # 纯文本
        return SubtitleItem(text=entry)

    @staticmethod
    def _to_float(val: Any) -> Optional[float]:
        """安全转换为 float"""
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    # ============================================================
    # 全文检索
    # ============================================================

    def search(self, query: str, threshold: float = 0.3) -> ProcessResult:
        """
        在已加载的字幕中执行全文检索。
        返回匹配项按相关度降序排列。
        """
        if not query or not query.strip():
            raise ValueError("E001: 搜索关键词不能为空")

        if not self._items:
            raise ValueError("E002: 尚未加载任何数据，请先调用 load_data")

        result = ProcessResult(query=query.strip())
        query_terms = self._tokenize(query)

        if not query_terms:
            raise ValueError("E003: 搜索关键词格式错误，无法分词")

        # 逐条计算匹配分数
        for idx, item in enumerate(self._items):
            score = self._score_item(item, query_terms)
            if score >= threshold:
                result.matches.append((idx, score))

        # 按分数降序排列
        result.matches.sort(key=lambda x: x[1], reverse=True)

        # 计算整体置信度
        if result.matches:
            result.confidence = min(1.0, result.matches[0][1])
            if result.confidence < self.MEDIUM_CONFIDENCE:
                result.warnings.append(
                    f"E005: 检索结果置信度较低（{result.confidence:.0%}），建议人工复核"
                )
        else:
            result.confidence = 0.0
            result.warnings.append("未找到匹配项，请尝试更换关键词")

        return result

    def _tokenize(self, text: str) -> List[str]:
        """分词：提取中文/英文单词/数字"""
        # 中文按字切分，英文按单词切分
        tokens = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+", text.lower())
        return tokens

    def _score_item(self, item: SubtitleItem, query_terms: List[str]) -> float:
        """计算单条字幕与查询的匹配分数（0~1）"""
        text = item.text.lower()
        text_terms = self._tokenize(text)

        if not text_terms:
            return 0.0

        # 计算命中率
        hit_count = sum(1 for t in query_terms if t in text_terms)
        hit_ratio = hit_count / len(query_terms)

        # 精确短语加分（完整查询在文本中出现）
        phrase_bonus = 0.1 if query_terms and "".join(query_terms) in text.replace(" ", "") else 0.0

        # 长度惩罚：非常短的文本匹配度降低
        length_factor = min(1.0, len(text_terms) / 5.0)

        score = hit_ratio * 0.8 + phrase_bonus + length_factor * 0.1
        return min(1.0, score)

    # ============================================================
    # 输出生成
    # ============================================================

    def format_result(self, result: ProcessResult, fmt: str = "text") -> str:
        """将检索结果格式化为指定格式输出"""
        if fmt == "json":
            return self._format_json(result)
        elif fmt == "text":
            return self._format_text(result)
        elif fmt == "markdown":
            return self._format_markdown(result)
        else:
            raise ValueError(f"E008: 不支持的输出格式: {fmt}")

    def _format_json(self, result: ProcessResult) -> str:
        """JSON 格式输出"""
        output: Dict[str, Any] = {
            "query": result.query,
            "confidence": round(result.confidence, 4),
            "warnings": result.warnings,
            "matches": []
        }
        for idx, score in result.matches:
            item = self._items[idx]
            output["matches"].append({
                "index": idx,
                "score": round(score, 4),
                "text": item.text,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "speaker": item.speaker,
                "metadata": item.metadata
            })
        return json.dumps(output, ensure_ascii=False, indent=2)

    def _format_text(self, result: ProcessResult) -> str:
        """纯文本格式输出"""
        lines = [f"搜索: {result.query}", f"置信度: {result.confidence:.0%}"]
        if result.warnings:
            lines.append("警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")
        lines.append("匹配结果:")
        for idx, score in result.matches:
            item = self._items[idx]
            time_str = ""
            if item.start_time is not None:
                time_str = f"[{self._format_time(item.start_time)}"
                if item.end_time is not None:
                    time_str += f" - {self._format_time(item.end_time)}"
                time_str += "] "
            speaker_str = f"({item.speaker}) " if item.speaker else ""
            lines.append(f"  {idx}: {time_str}{speaker_str}{item.text} (匹配度: {score:.0%})")
        return "\n".join(lines)

    def _format_markdown(self, result: ProcessResult) -> str:
        """Markdown 格式输出"""
        lines = [
            f"## 搜索结果: {result.query}",
            "",
            f"**置信度:** {result.confidence:.0%}",
            ""
        ]
        if result.warnings:
            lines.append("**警告:**")
            for w in result.warnings:
                lines.append(f"- {w}")
            lines.append("")
        lines.append("### 匹配项")
        lines.append("")
        for idx, score in result.matches:
            item = self._items[idx]
            time_str = ""
            if item.start_time is not None:
                time_str = f" ({self._format_time(item.start_time)}"
                if item.end_time is not None:
                    time_str += f" - {self._format_time(item.end_time)}"
                time_str += ")"
            speaker_str = f" **{item.speaker}**" if item.speaker else ""
            lines.append(f"{idx}.{speaker_str} {item.text}{time_str} — 匹配度 {score:.0%}")
        return "\n".join(lines)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """将秒数格式化为 mm:ss.xx"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:05.2f}"

    # ============================================================
    # 批量处理
    # ============================================================

    def batch_search(self, queries: List[str], threshold: float = 0.3) -> List[ProcessResult]:
        """批量执行搜索"""
        results = []
        for q in queries:
            try:
                result = self.search(q, threshold)
                results.append(result)
            except ValueError as e:
                # 单条失败不影响其他
                result = ProcessResult(query=q)
                result.warnings.append(str(e))
                results.append(result)
        return results


# ============================================================
# 文件处理辅助
# ============================================================

def read_file(path: str) -> str:
    """读取文件内容，支持 UTF-8 和常见编码"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"E006: 文件不存在: {path}")
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"E006: 无法解码文件（尝试了 UTF-8/GBK/Latin-1）: {path}")


def write_file(path: str, content: str) -> None:
    """写入文件"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise IOError(f"E007: 文件写入失败: {path} - {e}")


# ============================================================
# 内置自检（离线硬编码样例）
# ============================================================

def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读取外部文件，不依赖工作目录，不访问网络。
    使用宽松断言（区间/比较），确保任何环境可过。
    """
    print("=" * 50)
    print("subtubular 自检开始")
    print("=" * 50)

    # 测试数据：内置硬编码样例
    sample_data = [
        {"text": "大家好，欢迎观看本视频", "start_time": 0.0, "end_time": 3.5},
        {"text": "今天我们讨论人工智能的发展", "start_time": 3.5, "end_time": 10.2},
        {"text": "机器学习是AI的重要分支", "start_time": 10.2, "end_time": 18.7},
        {"text": "深度学习在图像识别中表现优异", "start_time": 18.7, "end_time": 30.1},
        {"text": "自然语言处理也取得重大突破", "start_time": 30.1, "end_time": 42.5},
        {"text": "感谢观看，我们下期再见", "start_time": 42.5, "end_time": 50.0},
    ]

    processor = SubtitleProcessor()

    # --- 测试1: 数据加载 ---
    try:
        processor.load_data(sample_data)
        assert len(processor._items) == 6, "数据加载数量不正确"
        print("[PASS] 数据加载")
    except Exception as e:
        print(f"[FAIL] 数据加载: {e}")
        return 1

    # --- 测试2: 文本字符串加载 ---
    try:
        text_data = "第一行字幕\n第二行字幕\n[00:10.00] 带时间戳的字幕"
        processor2 = SubtitleProcessor()
        processor2.load_data(text_data)
        assert len(processor2._items) == 3, "文本加载数量不正确"
        assert processor2._items[2].start_time is not None, "时间戳解析失败"
        print("[PASS] 文本字符串加载")
    except Exception as e:
        print(f"[FAIL] 文本字符串加载: {e}")
        return 1

    # --- 测试3: 全文检索（宽松断言） ---
    try:
        result = processor.search("人工智能")
        # 至少应该有匹配项
        assert len(result.matches) > 0, "搜索应有匹配结果"
        # 置信度应该在合理范围
        assert 0.0 <= result.confidence <= 1.0, "置信度超出范围"
        # 匹配分数也应在合理范围
        for _, score in result.matches:
            assert 0.0 <= score <= 1.0, "匹配分数超出范围"
        print(f"[PASS] 全文检索（匹配 {len(result.matches)} 条，置信度 {result.confidence:.0%}）")
    except Exception as e:
        print(f"[FAIL] 全文检索: {e}")
        return 1

    # --- 测试4: 无匹配情况 ---
    try:
        result = processor.search("不存在的关键词xyz")
        assert len(result.matches) == 0, "不应有匹配结果"
        assert result.confidence == 0.0, "置信度应为0"
        print("[PASS] 无匹配处理")
    except Exception as e:
        print(f"[FAIL] 无匹配处理: {e}")
        return 1

    # --- 测试5: 批量搜索 ---
    try:
        queries = ["人工智能", "机器学习", "深度学习", "不存在的词"]
        results = processor.batch_search(queries)
        assert len(results) == 4, "批量结果数量不正确"
        print("[PASS] 批量搜索")
    except Exception as e:
        print(f"[FAIL] 批量搜索: {e}")
        return 1

    # --- 测试6: 输出格式 ---
    try:
        result = processor.search("人工智能")
        # 文本格式
        text_out = processor.format_result(result, "text")
        assert len(text_out) > 0, "文本输出不应为空"
        # JSON 格式
        json_out = processor.format_result(result, "json")
        parsed = json.loads(json_out)
        assert "query" in parsed, "JSON 缺少 query 字段"
        assert "matches" in parsed, "JSON 缺少 matches 字段"
        # Markdown 格式
        md_out = processor.format_result(result, "markdown")
        assert len(md_out) > 0, "Markdown 输出不应为空"
        print("[PASS] 输出格式（text/json/markdown）")
    except Exception as e:
        print(f"[FAIL] 输出格式: {e}")
        return 1

    # --- 测试7: 错误处理 ---
    try:
        # 空输入
        try:
            processor.load_data(None)
            print("[FAIL] 空输入未抛出异常")
            return 1
        except ValueError:
            pass

        # 空搜索词
        try:
            processor.search("")
            print("[FAIL] 空搜索词未抛出异常")
            return 1
        except ValueError:
            pass

        # 未加载数据搜索
        empty_proc = SubtitleProcessor()
        try:
            empty_proc.search("test")
            print("[FAIL] 未加载数据搜索未抛出异常")
            return 1
        except ValueError:
            pass

        print("[PASS] 错误处理")
    except Exception as e:
        print(f"[FAIL] 错误处理: {e}")
        return 1

    # --- 测试8: 时间戳解析 ---
    try:
        # 测试 [mm:ss.xx] 格式
        item = processor._parse_string_entry("[01:30.50] 测试字幕")
        assert item.start_time is not None, "时间戳解析失败"
        assert abs(item.start_time - 90.5) < 0.01, "时间戳数值错误"
        # 测试 mm:ss --> mm:ss 格式
        item2 = processor._parse_string_entry("00:10.00 --> 00:15.50 测试")
        assert item2.start_time is not None and item2.end_time is not None, "时间段解析失败"
        assert abs(item2.start_time - 10.0) < 0.01, "开始时间错误"
        assert abs(item2.end_time - 15.5) < 0.01, "结束时间错误"
        print("[PASS] 时间戳解析")
    except Exception as e:
        print(f"[FAIL] 时间戳解析: {e}")
        return 1

    # --- 测试9: 置信度标注逻辑 ---
    try:
        # 低置信度应该产生警告
        result = processor.search("不存在的词")
        assert len(result.warnings) > 0, "低置信度应有警告"
        # 高置信度不应有 E005 警告
        result2 = processor.search("人工智能")
        has_low_conf_warning = any("E005" in w for w in result2.warnings)
        assert not has_low_conf_warning, "高置信度不应有 E005 警告"
        print("[PASS] 置信度标注")
    except Exception as e:
        print(f"[FAIL] 置信度标注: {e}")
        return 1

    # --- 测试10: 元数据处理 ---
    try:
        sample_with_meta = [
            {
                "text": "带元数据的字幕",
                "start_time": 1.0,
                "speaker": "张三",
                "metadata": {"language": "zh", "source": "测试"}
            }
        ]
        proc = SubtitleProcessor()
        proc.load_data(sample_with_meta)
        item = proc._items[0]
        assert item.speaker == "张三", "说话人解析失败"
        assert item.metadata["language"] == "zh", "元数据解析失败"
        print("[PASS] 元数据处理")
    except Exception as e:
        print(f"[FAIL] 元数据处理: {e}")
        return 1

    # --- 测试11: 文件读写（使用临时目录） ---
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写文件
            test_content = "测试文件内容\n第二行"
            test_path = os.path.join(tmpdir, "test.txt")
            write_file(test_path, test_content)
            # 读文件
            content = read_file(test_path)
            assert content == test_content, "文件读写不一致"
            # 不存在文件应该报错
            try:
                read_file(os.path.join(tmpdir, "nonexist.txt"))
                print("[FAIL] 不存在文件未抛异常")
                return 1
            except FileNotFoundError:
                pass
        print("[PASS] 文件读写")
    except Exception as e:
        print(f"[FAIL] 文件读写: {e}")
        return 1

    # --- 测试12: 空数据处理 ---
    try:
        # 空列表应该报错
        empty_proc = SubtitleProcessor()
        try:
            empty_proc.load_data([])
            print("[FAIL] 空数据未抛出异常")
            return 1
        except ValueError as e:
            assert "E002" in str(e), "错误码不正确"
        
        # 空字符串应该报错
        try:
            empty_proc.load_data("")
            print("[FAIL] 空字符串未抛出异常")
            return 1
        except ValueError as e:
            assert "E002" in str(e), "错误码不正确"
        
        # 只包含空字符串的列表应该报错
        try:
            empty_proc.load_data(["", "  "])
            print("[FAIL] 空内容列表未抛出异常")
            return 1
        except ValueError as e:
            assert "E002" in str(e), "错误码不正确"
        
        # 空数据搜索应报错
        try:
            empty_proc.search("test")
            print("[FAIL] 空数据搜索未抛异常")
            return 1
        except ValueError:
            pass
        
        print("[PASS] 空数据处理")
    except Exception as e:
        print(f"[FAIL] 空数据处理: {e}")
        return 1

    print("=" * 50)
    print("所有自检通过！")
    print("=" * 50)
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="subtubular - 视频字幕全文检索与元数据处理工具",
        epilog="示例: python main.py -i input.txt -q '关键词' -o result.json"
    )

    # 输入参数
    parser.add_argument("-i", "--input", help="输入文件路径（支持 txt/json）")
    parser.add_argument("-d", "--data", help="直接提供数据字符串（多行用 \\n 分隔）")

    # 搜索参数
    parser.add_argument("-q", "--query", help="搜索关键词（可用逗号分隔多个关键词）")
    parser.add_argument("-t", "--threshold", type=float, default=0.3,
                        help="匹配阈值（0~1，默认 0.3）")

    # 输出参数
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("-f", "--format", choices=["text", "json", "markdown"],
                        default="text", help="输出格式（默认 text）")

    # 其他
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version="subtubular 1.0.0")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input and not args.data:
        parser.error("E001: 请提供输入数据（-i 文件路径 或 -d 数据字符串）")

    if not args.query:
        parser.error("E001: 请提供搜索关键词（-q）")

    # 加载数据
    try:
        processor = SubtitleProcessor()
        if args.input:
            content = read_file(args.input)
            # 尝试解析 JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = content
            processor.load_data(data)
        else:
            # 将 \\n 转换为换行
            data_str = args.data.replace("\\n", "\n")
            processor.load_data(data_str)
    except (ValueError, FileNotFoundError, IOError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # 执行搜索
    try:
        queries = [q.strip() for q in args.query.split(",") if q.strip()]
        if len(queries) == 1:
            result = processor.search(queries[0], args.threshold)
            output = processor.format_result(result, args.format)
        else:
            # 批量搜索
            results = processor.batch_search(queries, args.threshold)
            combined = []
            for r in results:
                combined.extend(r.matches)
            combined.sort(key=lambda x: x[1], reverse=True)
            # 简单合并输出
            if args.format == "json":
                output = json.dumps({
                    "queries": queries,
                    "total_matches": len(combined),
                    "matches": [
                        {"index": idx, "score": round(score, 4),
                         "text": processor._items[idx].text}
                        for idx, score in combined
                    ]
                }, ensure_ascii=False, indent=2)
            else:
                lines = [f"批量搜索: {', '.join(queries)}", f"共找到 {len(combined)} 条匹配", ""]
                for idx, score in combined:
                    item = processor._items[idx]
                    lines.append(f"  {idx}: {item.text} (匹配度: {score:.0%})")
                output = "\n".join(lines)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    # 输出结果
    try:
        if args.output:
            write_file(args.output, output)
            print(f"结果已写入: {args.output}")
        else:
            print(output)
    except IOError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
