#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
story-skills 功能实现脚本
=========================
将素材转化为结构化故事，支持批量处理与置信度标注。
仅依据功能规格独立实现（clean-room），不依赖任何既有代码。

依赖：仅标准库（Python 3.6+）。
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入格式非法（非字符串/非列表）",
    "E003": "素材内容过短，无法提取有效信息",
    "E004": "批量处理时输入列表为空",
    "E005": "JSON 序列化失败",
    "E006": "配置文件读取失败",
    "E007": "输出目录不可写",
    "E008": "置信度计算失败",
    "E009": "故事结构生成失败",
    "E010": "未知错误",
}


class StorySkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class StoryElement:
    """故事元素（人物/场景/情节/主题）。"""

    element_type: str          # person / scene / plot / theme
    content: str
    confidence: float = 0.0    # 置信度 0~1
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.element_type,
            "content": self.content,
            "confidence": round(self.confidence, 4),
            "meta": self.meta,
        }


@dataclass
class StoryResult:
    """单篇结构化故事结果。"""

    title: str
    summary: str
    elements: List[StoryElement]
    overall_confidence: float = 0.0
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "elements": [e.to_dict() for e in self.elements],
            "overall_confidence": round(self.overall_confidence, 4),
            "raw_text_length": len(self.raw_text),
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class StoryProcessor:
    """素材 -> 结构化故事 的核心处理器。"""

    # 简单关键词表（用于演示结构提取）
    PERSON_KEYWORDS = ["他", "她", "我", "你", "他们", "我们", "主角", "老人", "男孩", "女孩", "医生", "老师"]
    SCENE_KEYWORDS = ["在", "来到", "走进", "位于", "城市", "村庄", "森林", "海边", "房间", "街道", "学校"]
    PLOT_KEYWORDS = ["然后", "接着", "后来", "突然", "但是", "因为", "所以", "最终", "最后", "开始", "结束"]
    THEME_KEYWORDS = ["爱", "勇气", "友谊", "成长", "希望", "梦想", "自由", "责任", "牺牲", "救赎"]

    def __init__(self, min_content_length: int = 20):
        self.min_content_length = min_content_length

    # -- 对外主入口 ----------------------------------------------------------
    def process(self, raw_text: str) -> StoryResult:
        """将单段素材文本转化为结构化故事。"""
        if not raw_text or not isinstance(raw_text, str):
            raise StorySkillError("E001")
        if len(raw_text.strip()) < self.min_content_length:
            raise StorySkillError("E003")

        try:
            elements = self._extract_elements(raw_text)
            title = self._generate_title(raw_text, elements)
            summary = self._generate_summary(raw_text, elements)
            overall_conf = self._compute_overall_confidence(elements)

            return StoryResult(
                title=title,
                summary=summary,
                elements=elements,
                overall_confidence=overall_conf,
                raw_text=raw_text,
            )
        except StorySkillError:
            raise
        except Exception as exc:
            raise StorySkillError("E009", str(exc)) from exc

    def process_batch(self, texts: List[str]) -> List[StoryResult]:
        """批量处理多段素材。"""
        if not texts or not isinstance(texts, list):
            raise StorySkillError("E004")
        if len(texts) == 0:
            raise StorySkillError("E004")
        return [self.process(t) for t in texts]

    # -- 内部提取方法 --------------------------------------------------------
    def _extract_elements(self, text: str) -> List[StoryElement]:
        """从文本中提取故事元素。"""
        elements: List[StoryElement] = []

        # 句子切分（简单按中文标点）
        sentences = re.split(r"[。！？!?；;]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            raise StorySkillError("E003")

        # 提取人物
        person_texts = [s for s in sentences if any(k in s for k in self.PERSON_KEYWORDS)]
        if person_texts:
            elements.append(StoryElement(
                element_type="person",
                content="；".join(person_texts[:3]),
                confidence=self._calc_confidence(len(person_texts), len(sentences)),
                meta={"matched_sentences": len(person_texts)},
            ))

        # 提取场景
        scene_texts = [s for s in sentences if any(k in s for k in self.SCENE_KEYWORDS)]
        if scene_texts:
            elements.append(StoryElement(
                element_type="scene",
                content="；".join(scene_texts[:3]),
                confidence=self._calc_confidence(len(scene_texts), len(sentences)),
                meta={"matched_sentences": len(scene_texts)},
            ))

        # 提取情节
        plot_texts = [s for s in sentences if any(k in s for k in self.PLOT_KEYWORDS)]
        if plot_texts:
            elements.append(StoryElement(
                element_type="plot",
                content="；".join(plot_texts[:5]),
                confidence=self._calc_confidence(len(plot_texts), len(sentences)),
                meta={"matched_sentences": len(plot_texts)},
            ))

        # 提取主题
        theme_texts = [s for s in sentences if any(k in s for k in self.THEME_KEYWORDS)]
        if theme_texts:
            elements.append(StoryElement(
                element_type="theme",
                content="；".join(theme_texts[:2]),
                confidence=self._calc_confidence(len(theme_texts), len(sentences)),
                meta={"matched_sentences": len(theme_texts)},
            ))

        # 若完全无匹配，则至少生成一个"通用"元素
        if not elements:
            elements.append(StoryElement(
                element_type="plot",
                content=sentences[0][:50],
                confidence=0.3,
                meta={"fallback": True},
            ))

        return elements

    def _generate_title(self, text: str, elements: List[StoryElement]) -> str:
        """根据元素生成故事标题。"""
        # 优先使用主题元素内容
        for e in elements:
            if e.element_type == "theme":
                return f"关于{e.content[:10]}的故事"
        # 其次使用场景
        for e in elements:
            if e.element_type == "scene":
                return f"{e.content[:10]}的故事"
        # 兜底：原文前几个字
        return f"故事：{text[:8]}"

    def _generate_summary(self, text: str, elements: List[StoryElement]) -> str:
        """生成故事摘要。"""
        parts = []
        for e in elements:
            if e.element_type == "person":
                parts.append(f"人物：{e.content[:20]}")
            elif e.element_type == "scene":
                parts.append(f"场景：{e.content[:20]}")
            elif e.element_type == "plot":
                parts.append(f"情节：{e.content[:30]}")
            elif e.element_type == "theme":
                parts.append(f"主题：{e.content[:20]}")
        if not parts:
            parts.append(text[:30])
        return "；".join(parts)

    def _compute_overall_confidence(self, elements: List[StoryElement]) -> float:
        """计算整体置信度（加权平均）。"""
        if not elements:
            raise StorySkillError("E008")
        weights = {
            "person": 0.3,
            "scene": 0.2,
            "plot": 0.3,
            "theme": 0.2,
        }
        total_weight = 0.0
        weighted_sum = 0.0
        for e in elements:
            w = weights.get(e.element_type, 0.1)
            weighted_sum += e.confidence * w
            total_weight += w
        if total_weight <= 0:
            raise StorySkillError("E008")
        return weighted_sum / total_weight

    @staticmethod
    def _calc_confidence(matched: int, total: int) -> float:
        """计算置信度：匹配句子占比映射到 0.5~0.95 区间。"""
        if total <= 0:
            return 0.0
        ratio = matched / total
        # 宽松映射，避免极端值
        return min(0.95, max(0.5, 0.5 + ratio * 0.4))


# ---------------------------------------------------------------------------
# 序列化与辅助功能
# ---------------------------------------------------------------------------
def result_to_json(result: StoryResult) -> str:
    """将结果序列化为 JSON 字符串。"""
    try:
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    except Exception as exc:
        raise StorySkillError("E005", str(exc)) from exc


def batch_to_json(results: List[StoryResult]) -> str:
    """批量结果序列化。"""
    try:
        return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
    except Exception as exc:
        raise StorySkillError("E005", str(exc)) from exc


def generate_fingerprint(text: str) -> str:
    """生成素材指纹（用于缓存/去重）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 内置自检（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """离线自检核心逻辑，不读取外部文件、不依赖工作目录、不访问网络。"""
    print("开始自检 story-skills 核心逻辑...")

    # 硬编码样例素材（足够长，包含多种元素）
    sample_text = (
        "在一个宁静的小村庄里，住着一位善良的老人。"
        "他每天清晨都会去森林边散步，看着日出。"
        "有一天，他突然发现了一只受伤的小鸟，于是决定带回家照顾。"
        "后来，小鸟康复了，飞向蓝天，老人感到非常欣慰。"
        "这个故事告诉我们，爱与勇气可以创造奇迹，希望永远存在。"
    )

    # 简短素材（应触发 E003）
    short_text = "你好"

    # 非法输入（应触发 E001/E002）
    empty_text = ""

    processor = StoryProcessor()

    # --- 用例 1：正常处理 ---
    try:
        result = processor.process(sample_text)
        assert result.title, "标题不应为空"
        assert result.summary, "摘要不应为空"
        assert len(result.elements) >= 1, "至少有一个故事元素"
        assert 0.0 <= result.overall_confidence <= 1.0, "置信度应在 0~1 之间"
        # 宽松断言：置信度应大于 0.3（一般会更高）
        assert result.overall_confidence > 0.3, f"置信度应大于 0.3，实际为 {result.overall_confidence}"
        print(f"  [通过] 正常处理：标题='{result.title}', 元素数={len(result.elements)}, 置信度={result.overall_confidence:.2f}")
    except AssertionError as exc:
        print(f"  [失败] 正常处理断言失败: {exc}")
        return 1
    except StorySkillError as exc:
        print(f"  [失败] 正常处理抛出异常: {exc}")
        return 1

    # --- 用例 2：批量处理 ---
    try:
        batch_results = processor.process_batch([sample_text, sample_text + "第二段素材。"])
        assert len(batch_results) == 2, "批量结果数量应为 2"
        for r in batch_results:
            assert r.overall_confidence > 0.3, "批量结果置信度异常"
        print(f"  [通过] 批量处理：{len(batch_results)} 条结果")
    except AssertionError as exc:
        print(f"  [失败] 批量处理断言失败: {exc}")
        return 1
    except StorySkillError as exc:
        print(f"  [失败] 批量处理抛出异常: {exc}")
        return 1

    # --- 用例 3：错误处理 ---
    try:
        processor.process(empty_text)
        print("  [失败] 空文本未抛出异常")
        return 1
    except StorySkillError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"
        print(f"  [通过] 空文本正确抛出 E001")

    try:
        processor.process(short_text)
        print("  [失败] 短文本未抛出异常")
        return 1
    except StorySkillError as exc:
        assert exc.code == "E003", f"错误码应为 E003，实际为 {exc.code}"
        print(f"  [通过] 短文本正确抛出 E003")

    try:
        processor.process_batch([])
        print("  [失败] 空列表未抛出异常")
        return 1
    except StorySkillError as exc:
        assert exc.code == "E004", f"错误码应为 E004，实际为 {exc.code}"
        print(f"  [通过] 空列表正确抛出 E004")

    # --- 用例 4：JSON 序列化 ---
    try:
        result = processor.process(sample_text)
        json_str = result_to_json(result)
        data = json.loads(json_str)
        assert data["title"], "JSON 中标题为空"
        assert "elements" in data, "JSON 中缺少 elements"
        print(f"  [通过] JSON 序列化：输出 {len(json_str)} 字符")
    except AssertionError as exc:
        print(f"  [失败] JSON 序列化断言失败: {exc}")
        return 1
    except StorySkillError as exc:
        print(f"  [失败] JSON 序列化异常: {exc}")
        return 1

    # --- 用例 5：指纹生成 ---
    try:
        fp1 = generate_fingerprint(sample_text)
        fp2 = generate_fingerprint(sample_text)
        fp3 = generate_fingerprint(sample_text + "不同")
        assert fp1 == fp2, "相同输入指纹应一致"
        assert fp1 != fp3, "不同输入指纹应不同"
        assert len(fp1) == 16, "指纹长度应为 16"
        print(f"  [通过] 指纹生成：{fp1}")
    except AssertionError as exc:
        print(f"  [失败] 指纹生成断言失败: {exc}")
        return 1

    print("自检全部通过。")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="story-skills：将素材转化为结构化故事",
        epilog="示例：python main.py -t '素材文本' 或 python main.py --selftest",
    )
    parser.add_argument("-t", "--text", type=str, help="待处理的素材文本")
    parser.add_argument("-f", "--file", type=str, help="从文件读取素材（UTF-8）")
    parser.add_argument("-b", "--batch", type=str, nargs="*", help="批量处理多段素材")
    parser.add_argument("-j", "--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--min-len", type=int, default=20, help="最小素材长度（默认 20）")

    args = parser.parse_args()

    # 自检模式优先
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.text and not args.file and not args.batch:
        parser.print_usage()
        print("错误: 需要提供 -t/--text、-f/--file 或 -b/--batch 之一")
        return 2

    try:
        processor = StoryProcessor(min_content_length=args.min_len)

        # 单文本处理
        if args.text:
            result = processor.process(args.text)
            if args.json:
                print(result_to_json(result))
            else:
                print(f"标题: {result.title}")
                print(f"摘要: {result.summary}")
                print(f"置信度: {result.overall_confidence:.2f}")
                for e in result.elements:
                    print(f"  [{e.element_type}] {e.content} (置信度: {e.confidence:.2f})")
            return 0

        # 文件处理
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as exc:
                raise StorySkillError("E006", f"读取文件失败: {exc}") from exc
            result = processor.process(text)
            if args.json:
                print(result_to_json(result))
            else:
                print(f"标题: {result.title}")
                print(f"摘要: {result.summary}")
                print(f"置信度: {result.overall_confidence:.2f}")
            return 0

        # 批量处理
        if args.batch:
            results = processor.process_batch(list(args.batch))
            if args.json:
                print(batch_to_json(results))
            else:
                for i, r in enumerate(results, 1):
                    print(f"--- 第 {i} 篇 ---")
                    print(f"标题: {r.title}")
                    print(f"摘要: {r.summary}")
                    print(f"置信度: {r.overall_confidence:.2f}")
            return 0

    except StorySkillError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
