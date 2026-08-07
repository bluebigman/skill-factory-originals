#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
humanizer-de — 德文文本去AI味改写器（独立实现）

本脚本根据功能规格独立实现，不参考任何既有代码。
仅使用 Python 标准库，无第三方依赖。

功能：
- 德文AI痕迹检测（基于规则模式扫描）
- 文本自然化改写（逐句处理）
- 多段文本批量处理（使用 '---' 分隔）
- 置信度标注（高/中/低）
- 内置自检模式（--selftest）

错误码：
E001 - 输入为空
E002 - 非德文文本（德文字符占比过低）
E003 - 文件读取失败
E004 - URL 访问失败
E005 - 无效参数
E006 - 输出写入失败
E007 - 内部处理异常
E008 - 自检失败
E009 - 不支持的输入类型
E010 - 未知错误
"""

import argparse
import re
import sys
from typing import Dict, List, Tuple


# ============================================================
# 常量定义
# ============================================================

# 德文特征字符
GERMAN_CHARS = set("äöüßÄÖÜ")

# 德文 AI 写作模式（72种模式的代表性集合）
AI_PATTERNS = [
    # 过度正式/模板化表达
    (r"\bes ist wichtig zu beachten\b", "Es sollte beachtet werden"),
    (r"\bes ist zu erwähnen\b", "Erwähnenswert ist"),
    (r"\bes sei darauf hingewiesen\b", "Hinweis:"),
    (r"\bim Folgenden\b", "nachfolgend"),
    (r"\bzusammenfassend lässt sich sagen\b", "Kurz gesagt"),
    (r"\bdes Weiteren\b", "Außerdem"),
    (r"\bdarüber hinaus\b", "Zudem"),
    (r"\baufgrund der Tatsache\b", "weil"),
    (r"\bin Bezug auf\b", "zu"),
    (r"\bmit Bezug auf\b", "zu"),
    # 机器翻译常见痕迹
    (r"\bum zu\b", "damit"),
    (r"\bwie bereits erwähnt\b", "wie gesagt"),
    (r"\bwie oben erwähnt\b", "wie erwähnt"),
    (r"\bwie folgt\b", "so"),
    (r"\bin der Lage sein\b", "können"),
    (r"\bdie Möglichkeit haben\b", "können"),
    (r"\bim Rahmen von\b", "bei"),
    (r"\bim Hinblick auf\b", "hinsichtlich"),
    (r"\bmit Hilfe von\b", "mittels"),
    (r"\bunter Berücksichtigung von\b", "angesichts"),
    # 过度书面化表达
    (r"\bsomit\b", "also"),
    (r"\bdaher\b", "deshalb"),
    (r"\bdementsprechend\b", "entsprechend"),
    (r"\bfolglich\b", "also"),
    (r"\binsofern\b", "insofern"),
    (r"\bgleichwohl\b", "trotzdem"),
    (r"\bnichtsdestotrotz\b", "trotzdem"),
    (r"\bzweifelsohne\b", "sicherlich"),
    (r"\bzweifellos\b", "sicher"),
    (r"\bzweifelsohne\b", "sicherlich"),
    # 被动语态过度使用
    (r"\bwird durchgeführt\b", "führen wir durch"),
    (r"\bwird verwendet\b", "verwenden wir"),
    (r"\bwird benötigt\b", "brauchen wir"),
    (r"\bwird erwartet\b", "erwarten wir"),
    (r"\bwird betrachtet\b", "betrachten wir"),
    # 名词化过度
    (r"\bdie Durchführung\b", "das Durchführen"),
    (r"\bdie Verwendung\b", "das Verwenden"),
    (r"\bdie Erstellung\b", "das Erstellen"),
    (r"\bdie Bearbeitung\b", "das Bearbeiten"),
    (r"\bdie Berücksichtigung\b", "das Berücksichtigen"),
    # 连接词滥用
    (r"\bjedoch\b", "aber"),
    (r"\ballerdings\b", "aber"),
    (r"\bdennoch\b", "trotzdem"),
    (r"\bhingegen\b", "dagegen"),
    (r"\bwiederum\b", "andererseits"),
    # 其他常见AI痕迹
    (r"\bsehr geehrte\b", "Hallo"),
    (r"\bmit freundlichen Grüßen\b", "Viele Grüße"),
    (r"\bies ist klar\b", "klar"),
    (r"\bes ist offensichtlich\b", "offensichtlich"),
    (r"\bes ist ersichtlich\b", "ersichtlich"),
    (r"\bman kann sehen\b", "man sieht"),
    (r"\bman beachte\b", "beachten Sie"),
    (r"\bbitte beachten Sie\b", "beachten Sie"),
    (r"\bwir möchten\b", "wir wollen"),
    (r"\bwir würden\b", "wir würden"),
    (r"\bwürde gerne\b", "möchte"),
    (r"\bsollte beachtet werden\b", "sollte beachtet werden"),
    (r"\bmuss berücksichtigt werden\b", "muss berücksichtigt werden"),
    (r"\bkann festgestellt werden\b", "kann man feststellen"),
    (r"\bwird angenommen\b", "nimmt man an"),
    (r"\bwird argumentiert\b", "argumentiert man"),
    (r"\bes gibt\b", "gibt es"),
    (r"\bhandelt sich um\b", "ist"),
    (r"\bbezüglich\b", "wegen"),
    (r"\bbzgl\.\b", "wegen"),
    (r"\bet al\.\b", "und andere"),
    (r"\betc\.\b", "usw."),
]

# 自然化改写规则（基于模式替换）
REWRITE_RULES: List[Tuple[str, str]] = [
    # 正式表达 → 自然表达
    (r"\bes ist wichtig zu beachten, dass\b", "wichtig ist, dass"),
    (r"\bes ist wichtig zu beachten\b", "wichtig ist"),
    (r"\bes ist zu erwähnen, dass\b", "erwähnenswert ist, dass"),
    (r"\bes ist zu erwähnen\b", "erwähnenswert"),
    (r"\bes sei darauf hingewiesen, dass\b", "hinweisen möchte ich auf"),
    (r"\bes sei darauf hingewiesen\b", "hinweisen möchte ich"),
    (r"\bim Folgenden\b", "nachfolgend"),
    (r"\bzusammenfassend lässt sich sagen, dass\b", "kurz gesagt"),
    (r"\bzusammenfassend lässt sich sagen\b", "kurz gesagt"),
    (r"\bdes Weiteren\b", "außerdem"),
    (r"\bdarüber hinaus\b", "zudem"),
    (r"\baufgrund der Tatsache, dass\b", "weil"),
    (r"\baufgrund der Tatsache\b", "weil"),
    (r"\bin Bezug auf\b", "zu"),
    (r"\bmit Bezug auf\b", "zu"),
    # 机器翻译痕迹
    (r"\bum zu\b", "damit"),
    (r"\bwie bereits erwähnt\b", "wie gesagt"),
    (r"\bwie oben erwähnt\b", "wie erwähnt"),
    (r"\bwie folgt\b", "so"),
    (r"\bin der Lage sein\b", "können"),
    (r"\bdie Möglichkeit haben\b", "können"),
    (r"\bim Rahmen von\b", "bei"),
    (r"\bim Hinblick auf\b", "hinsichtlich"),
    (r"\bmit Hilfe von\b", "mittels"),
    (r"\bunter Berücksichtigung von\b", "angesichts"),
    # 书面化 → 口语化
    (r"\bsomit\b", "also"),
    (r"\bdaher\b", "deshalb"),
    (r"\bdementsprechend\b", "entsprechend"),
    (r"\bfolglich\b", "also"),
    (r"\bgleichwohl\b", "trotzdem"),
    (r"\bnichtsdestotrotz\b", "trotzdem"),
    (r"\bzweifelsohne\b", "sicherlich"),
    (r"\bzweifellos\b", "sicher"),
    # 被动 → 主动
    (r"\bwird durchgeführt\b", "führen wir durch"),
    (r"\bwird verwendet\b", "verwenden wir"),
    (r"\bwird benötigt\b", "brauchen wir"),
    (r"\bwird erwartet\b", "erwarten wir"),
    (r"\bwird betrachtet\b", "betrachten wir"),
    # 名词化 → 动词化
    (r"\bdie Durchführung\b", "das Durchführen"),
    (r"\bdie Verwendung\b", "das Verwenden"),
    (r"\bdie Erstellung\b", "das Erstellen"),
    (r"\bdie Bearbeitung\b", "das Bearbeiten"),
    (r"\bdie Berücksichtigung\b", "das Berücksichtigen"),
    # 连接词简化
    (r"\bjedoch\b", "aber"),
    (r"\ballerdings\b", "aber"),
    (r"\bdennoch\b", "trotzdem"),
    (r"\bhingegen\b", "dagegen"),
    (r"\bwiederum\b", "andererseits"),
    # 其他
    (r"\bsehr geehrte\b", "hallo"),
    (r"\bmit freundlichen Grüßen\b", "viele Grüße"),
    (r"\bies ist klar\b", "klar"),
    (r"\bes ist offensichtlich\b", "offensichtlich"),
    (r"\bes ist ersichtlich\b", "ersichtlich"),
    (r"\bman kann sehen\b", "man sieht"),
    (r"\bman beachte\b", "beachten Sie"),
    (r"\bbitte beachten Sie\b", "beachten Sie"),
    (r"\bwir möchten\b", "wir wollen"),
    (r"\bwir würden\b", "wir würden"),
    (r"\bwürde gerne\b", "möchte"),
    (r"\bsollte beachtet werden\b", "sollte man beachten"),
    (r"\bmuss berücksichtigt werden\b", "muss man berücksichtigen"),
    (r"\bkann festgestellt werden\b", "kann man feststellen"),
    (r"\bwird angenommen\b", "nimmt man an"),
    (r"\bwird argumentiert\b", "argumentiert man"),
    (r"\bes gibt\b", "gibt es"),
    (r"\bhandelt sich um\b", "ist"),
    (r"\bbezüglich\b", "wegen"),
    (r"\bbzgl\.\b", "wegen"),
    (r"\bet al\.\b", "und andere"),
    (r"\betc\.\b", "usw."),
]


# ============================================================
# 核心功能类
# ============================================================

class HumanizerDE:
    """德文文本去AI味改写器主类"""

    def __init__(self):
        """初始化检测器和改写规则"""
        # 编译正则表达式
        self.ai_patterns = [(re.compile(pattern, re.IGNORECASE), replacement)
                           for pattern, replacement in AI_PATTERNS]
        self.rewrite_rules = [(re.compile(pattern, re.IGNORECASE), replacement)
                             for pattern, replacement in REWRITE_RULES]

    def is_german_text(self, text: str) -> bool:
        """
        检测文本是否以德文为主。
        德文字符（äöüßÄÖÜ）或常见德文词占比超过阈值则判定为德文。
        """
        if not text or len(text.strip()) == 0:
            return False

        # 移除标点和空白
        cleaned = re.sub(r'[\s\W_]', '', text)
        if len(cleaned) == 0:
            return False

        # 德文字符占比
        german_char_count = sum(1 for c in cleaned if c in GERMAN_CHARS)
        char_ratio = german_char_count / len(cleaned)

        # 常见德文单词检测
        common_words = ["der", "die", "das", "und", "ist", "nicht", "ein", "eine",
                        "mit", "auf", "für", "von", "den", "dem", "des", "sich",
                        "auch", "noch", "nach", "aus", "bei", "oder", "wenn"]
        word_count = 0
        for word in cleaned.lower().split():
            if word in common_words:
                word_count += 1
        word_ratio = word_count / max(1, len(cleaned.split()))

        # 综合判断：德文字符占比 > 1% 或 常见词占比 > 20%
        return char_ratio > 0.01 or word_ratio > 0.2

    def detect_ai_patterns(self, text: str) -> List[Dict]:
        """
        检测文本中的AI写作模式。
        返回命中清单，每项包含模式、位置和替换建议。
        """
        hits = []
        for pattern, replacement in self.ai_patterns:
            for match in pattern.finditer(text):
                hits.append({
                    "pattern": match.group(0),
                    "position": match.start(),
                    "suggestion": replacement,
                    "confidence": self._estimate_confidence(match.group(0))
                })
        return hits

    def _estimate_confidence(self, matched_text: str) -> str:
        """根据匹配文本长度估算置信度"""
        length = len(matched_text)
        if length >= 15:
            return "高"
        elif length >= 8:
            return "中"
        else:
            return "低"

    def rewrite_text(self, text: str) -> str:
        """
        对文本进行自然化改写。
        应用所有改写规则，返回改写后的文本。
        """
        result = text
        for pattern, replacement in self.rewrite_rules:
            result = pattern.sub(replacement, result)
        return result

    def process_text(self, text: str) -> Dict:
        """
        处理单段文本：检测 + 改写 + 置信度标注。
        返回包含检测结果和改写结果的字典。
        """
        if not text or len(text.strip()) == 0:
            return {"error": "E001", "message": "输入文本为空"}

        if not self.is_german_text(text):
            return {"error": "E002", "message": "输入文本不是以德文为主"}

        try:
            # 检测AI痕迹
            detections = self.detect_ai_patterns(text)

            # 改写文本
            rewritten = self.rewrite_text(text)

            # 计算置信度
            if len(detections) == 0:
                confidence = "高"
            elif len(detections) <= 3:
                confidence = "中"
            else:
                confidence = "低"

            return {
                "original": text,
                "rewritten": rewritten,
                "detections": detections,
                "detection_count": len(detections),
                "confidence": confidence
            }
        except Exception as e:
            return {"error": "E007", "message": f"处理异常: {str(e)}"}

    def process_batch(self, text: str) -> List[Dict]:
        """
        批量处理多段文本（用 '---' 分隔）。
        返回每段文本的处理结果列表。
        """
        segments = [seg.strip() for seg in text.split('---') if seg.strip()]
        results = []
        for seg in segments:
            result = self.process_text(seg)
            results.append(result)
        return results

    def process_file(self, filepath: str) -> Dict:
        """处理文件（.txt / .md）"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.process_text(content)
        except FileNotFoundError:
            return {"error": "E003", "message": f"文件不存在: {filepath}"}
        except Exception as e:
            return {"error": "E003", "message": f"文件读取失败: {str(e)}"}

    def format_output(self, result: Dict) -> str:
        """格式化输出结果"""
        if "error" in result:
            return f"[错误 {result['error']}] {result['message']}"

        lines = []
        lines.append("=" * 60)
        lines.append("【原文】")
        lines.append(result["original"])
        lines.append("")
        lines.append("【改写后】")
        lines.append(result["rewritten"])
        lines.append("")

        if result["detections"]:
            lines.append(f"【检测到 {result['detection_count']} 处AI痕迹】")
            for i, det in enumerate(result["detections"], 1):
                lines.append(f"  {i}. '{det['pattern']}' → 建议: '{det['suggestion']}' "
                           f"(置信度: {det['confidence']})")
        else:
            lines.append("【未检测到明显AI痕迹】")

        lines.append(f"【整体置信度: {result['confidence']}】")
        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================
# 自测模块
# ============================================================

def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("开始自检...")
    humanizer = HumanizerDE()

    # 测试样例1：典型AI风格德文文本
    sample1 = (
        "Es ist wichtig zu beachten, dass die Durchführung des Projekts "
        "im Rahmen der festgelegten Zeitvorgaben erfolgen muss. "
        "Des Weiteren sollte die Verwendung von modernen Technologien "
        "in Betracht gezogen werden. Zusammenfassend lässt sich sagen, "
        "dass das Projekt erfolgreich sein wird."
    )

    # 测试样例2：自然德文文本
    sample2 = (
        "Wir haben das Projekt pünktlich fertiggestellt. "
        "Die neuen Technologien haben uns dabei sehr geholfen. "
        "Kurz gesagt, das Projekt war ein Erfolg."
    )

    # 测试样例3：非德文文本
    sample3 = (
        "This is an English text that should be rejected "
        "because it is not primarily in German."
    )

    # 测试1：德文检测
    print("测试1: 德文检测...")
    assert humanizer.is_german_text(sample1), "E008: 德文文本检测失败 (样例1)"
    assert humanizer.is_german_text(sample2), "E008: 德文文本检测失败 (样例2)"
    assert not humanizer.is_german_text(sample3), "E008: 非德文文本误判"
    print("  通过 ✓")

    # 测试2：AI痕迹检测
    print("测试2: AI痕迹检测...")
    detections1 = humanizer.detect_ai_patterns(sample1)
    assert len(detections1) > 0, "E008: AI痕迹检测失败 (样例1应有检测结果)"
    detections2 = humanizer.detect_ai_patterns(sample2)
    print(f"  样例1命中 {len(detections1)} 处, 样例2命中 {len(detections2)} 处")
    print("  通过 ✓")

    # 测试3：改写功能
    print("测试3: 改写功能...")
    result1 = humanizer.process_text(sample1)
    assert "error" not in result1, f"E008: 处理样例1失败: {result1}"
    assert result1["rewritten"] != sample1, "E008: 改写结果与原文相同"
    assert len(result1["rewritten"]) > 0, "E008: 改写结果为空"
    print(f"  改写后长度: {len(result1['rewritten'])} (原文: {len(sample1)})")
    print("  通过 ✓")

    # 测试4：非德文拒绝
    print("测试4: 非德文拒绝...")
    result3 = humanizer.process_text(sample3)
    assert "error" in result3, "E008: 非德文文本未被拒绝"
    assert result3["error"] == "E002", f"E008: 错误码错误: {result3['error']}"
    print("  通过 ✓")

    # 测试5：批量处理
    print("测试5: 批量处理...")
    batch_text = sample1 + "\n---\n" + sample2
    batch_results = humanizer.process_batch(batch_text)
    assert len(batch_results) == 2, f"E008: 批量处理结果数量错误: {len(batch_results)}"
    print(f"  批量处理 {len(batch_results)} 段")
    print("  通过 ✓")

    # 测试6：置信度评估
    print("测试6: 置信度评估...")
    assert result1["confidence"] in ["高", "中", "低"], "E008: 置信度值无效"
    assert detections1[0]["confidence"] in ["高", "中", "低"], "E008: 置信度值无效"
    print(f"  整体置信度: {result1['confidence']}")
    print("  通过 ✓")

    # 测试7：空输入处理
    print("测试7: 空输入处理...")
    empty_result = humanizer.process_text("")
    assert "error" in empty_result, "E008: 空输入未被拒绝"
    assert empty_result["error"] == "E001", f"E008: 错误码错误: {empty_result['error']}"
    print("  通过 ✓")

    # 测试8：改写质量（宽松验证）
    print("测试8: 改写质量验证...")
    # 检查改写结果是否包含更自然的表达
    rewritten_lower = result1["rewritten"].lower()
    assert "wichtig ist" in rewritten_lower or "außerdem" in rewritten_lower or \
           "zudem" in rewritten_lower or "kurz gesagt" in rewritten_lower, \
           "E008: 改写结果缺少自然化表达"
    print("  通过 ✓")

    print("\n所有自检通过! ✓")
    return True


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="humanizer-de — 德文文本去AI味改写器",
        epilog="示例: python main.py --text '输入德文文本' 或 python main.py --file input.txt"
    )

    # 输入方式
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", type=str, help="直接输入德文文本")
    input_group.add_argument("--file", type=str, help="输入文件路径 (.txt / .md)")
    input_group.add_argument("--selftest", action="store_true", help="运行内置自检")

    # 批量模式
    parser.add_argument("--batch", action="store_true", help="批量模式 (用 '---' 分隔多段文本)")

    # 输出选项
    parser.add_argument("--output", type=str, help="输出文件路径")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"自检失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"自检异常: {str(e)}")
            sys.exit(1)

    # 检查输入
    if not args.text and not args.file:
        parser.error("E005: 请提供 --text、--file 或 --selftest 参数")

    # 初始化处理器
    humanizer = HumanizerDE()

    # 处理输入
    try:
        if args.text:
            if args.batch:
                results = humanizer.process_batch(args.text)
            else:
                results = [humanizer.process_text(args.text)]
        elif args.file:
            file_result = humanizer.process_file(args.file)
            if "error" in file_result:
                print(f"文件处理错误: {file_result['message']}")
                sys.exit(1)
            results = [file_result]
        else:
            parser.error("E005: 无效参数组合")
            return

        # 格式化输出
        output_lines = []
        for result in results:
            output_lines.append(humanizer.format_output(result))

        output_text = "\n".join(output_lines)

        # 输出
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"结果已写入: {args.output}")
            except Exception as e:
                print(f"E006: 输出写入失败: {str(e)}")
                sys.exit(1)
        else:
            print(output_text)

    except Exception as e:
        print(f"E010: 未知错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
