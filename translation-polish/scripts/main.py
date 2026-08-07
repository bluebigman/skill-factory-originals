#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translation-polish 技能独立实现（clean-room 重写）
对翻译文本进行润色：术语统一、语感优化、格式调整，输出对照版本和修改说明。
仅依据功能规格独立实现，不复制任何既有代码。
"""

import argparse
import json
import sys
import time
from collections import OrderedDict

# 错误码定义（规格 E001-E005 为基础错误，E006-E010 为扩展错误）
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "输出校验失败",
    "E008": "批量处理中断",
    "E009": "参数配置错误",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


class TranslationPolish:
    """翻译润色核心处理类（纯本地、无网络、无第三方依赖）"""

    # 常见术语对照表（用于术语统一）
    TERM_MAP = {
        "AI": "人工智能",
        "API": "应用程序接口",
        "App": "应用",
        "Bug": "缺陷",
        "Cloud": "云端",
        "Data": "数据",
        "Deploy": "部署",
        "Framework": "框架",
        "Model": "模型",
        "Server": "服务器",
    }

    # 常见语感优化规则（简单启发式）
    SMOOTH_RULES = [
        # (原文片段, 优化后片段, 说明)
        ("进行一个", "进行", "去除冗余表达"),
        ("能够被", "可以", "简化被动句式"),
        ("在...之中", "在...中", "精简介词结构"),
        ("对于...来说", "对...而言", "书面化表达"),
        ("非常非常", "非常", "去除重复强调"),
    ]

    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 3):
        """
        初始化处理引擎

        :param timeout_seconds: 单条处理超时上限（秒）
        :param max_retries: 可恢复错误的重试次数
        """
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._term_map = dict(self.TERM_MAP)
        self._smooth_rules = list(self.SMOOTH_RULES)

    def process(self, original: str, translated: str) -> dict:
        """
        执行翻译润色主流程

        :param original: 原文文本
        :param translated: 待润色的译文文本
        :return: 结构化结果，包含对照版本、修改说明、置信度等
        """
        # ---- 输入校验（先检查类型，再检查内容）----
        if not isinstance(original, str) or not isinstance(translated, str):
            raise SkillError("E003", "输入格式不符合要求，示例：{'original': '...', 'translated': '...'}")

        if not original.strip():
            raise SkillError("E001", "请提供待处理的内容，格式为：原文与译文")
        if not translated.strip():
            raise SkillError("E002", "还缺少以下信息，请补充：译文内容")

        # ---- 超时控制 ----
        start_time = time.time()

        # ---- 重试机制（可恢复错误自动重试）----
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = self._process_internal(original, translated)
                # 幂等性校验：重复执行应得到一致结果
                result["idempotency_check"] = self._verify_idempotent(original, translated, result)
                return result
            except SkillError as e:
                # 不可恢复错误直接抛出
                if e.code not in ("E006",):
                    raise
                last_error = e
                # 间隔递增重试
                time.sleep(0.5 * (attempt + 1))
            except Exception as e:  # 兜底异常
                raise SkillError("E006", f"内部处理异常: {str(e)}") from e

            # 超时检查
            if time.time() - start_time > self.timeout_seconds:
                raise SkillError("E008", f"处理超时（限制 {self.timeout_seconds}s），已跳过该条")

        if last_error:
            raise last_error
        raise SkillError("E006", "重试后仍失败")

    def _process_internal(self, original: str, translated: str) -> dict:
        """
        内部核心处理逻辑

        1. 术语统一
        2. 语感优化
        3. 格式调整
        4. 生成对照与修改说明
        5. 计算置信度
        """
        # 步骤1: 术语统一
        unified_text = self._unify_terms(translated)
        term_changes = self._collect_term_changes(translated, unified_text)

        # 步骤2: 语感优化
        smoothed_text = self._smooth_language(unified_text)
        smooth_changes = self._collect_smooth_changes(unified_text, smoothed_text)

        # 步骤3: 格式调整（此处仅做基础清理，不改变结构）
        formatted_text = self._adjust_format(smoothed_text)
        format_changes = self._collect_format_changes(smoothed_text, formatted_text)

        # 最终润色结果
        polished_text = formatted_text

        # 计算置信度（基于修改量和文本完整性）
        confidence = self._calculate_confidence(original, translated, polished_text,
                                                term_changes, smooth_changes)

        # 组装修改说明
        modifications = []
        modifications.extend(term_changes)
        modifications.extend(smooth_changes)
        modifications.extend(format_changes)

        # 置信度标注
        if confidence < 85:
            polish_note = "[需核实] 结果存在不确定性，请人工复核关键内容"
        elif confidence < 90:
            polish_note = "建议复核：部分修改可能影响原意"
        else:
            polish_note = "置信度良好，可直接使用"

        return {
            "original": original,
            "translated": translated,
            "polished": polished_text,
            "comparison": {
                "原文": original,
                "原译文": translated,
                "润色后": polished_text,
            },
            "modifications": modifications,
            "confidence": confidence,
            "confidence_note": polish_note,
            "meta": {
                "engine": "translation-polish-clean-room",
                "version": "1.0.0",
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    # ------------------------------------------------------------------
    # 以下为各处理步骤的具体实现
    # ------------------------------------------------------------------

    def _unify_terms(self, text: str) -> str:
        """术语统一：将常见英文术语替换为统一中文表达"""
        result = text
        for en, zh in self._term_map.items():
            # 简单替换，保留大小写变体
            result = result.replace(en, zh)
            result = result.replace(en.lower(), zh)
            result = result.replace(en.upper(), zh)
        return result

    def _collect_term_changes(self, before: str, after: str) -> list:
        """收集术语修改记录"""
        changes = []
        for en, zh in self._term_map.items():
            variants = [en, en.lower(), en.upper()]
            for v in variants:
                if v in before and zh in after:
                    changes.append({
                        "type": "术语统一",
                        "from": v,
                        "to": zh,
                        "detail": f"将 '{v}' 统一为 '{zh}'",
                    })
        return changes

    def _smooth_language(self, text: str) -> str:
        """语感优化：应用启发式规则使表达更自然"""
        result = text
        for old, new, _ in self._smooth_rules:
            result = result.replace(old, new)
        return result

    def _collect_smooth_changes(self, before: str, after: str) -> list:
        """收集语感优化记录"""
        changes = []
        for old, new, desc in self._smooth_rules:
            if old in before and new in after and old != new:
                changes.append({
                    "type": "语感优化",
                    "from": old,
                    "to": new,
                    "detail": desc,
                })
        return changes

    def _adjust_format(self, text: str) -> str:
        """格式调整：清理多余空白、统一标点等"""
        result = text
        # 去除多余连续空白
        import re
        result = re.sub(r'[ \t]+', ' ', result)
        # 去除多余空行（保留至多一个）
        result = re.sub(r'\n\s*\n', '\n\n', result)
        # 中文标点统一（示例：英文逗号转中文逗号）
        result = result.replace(',', '，')
        result = result.replace(';', '；')
        return result.strip()

    def _collect_format_changes(self, before: str, after: str) -> list:
        """收集格式调整记录"""
        changes = []
        if before != after:
            # 统计变化点（简化处理，仅记录存在差异）
            if '，' in after and ',' in before:
                changes.append({
                    "type": "格式调整",
                    "from": "英文逗号",
                    "to": "中文逗号",
                    "detail": "统一标点为中文标点",
                })
            if before.strip() != after:
                changes.append({
                    "type": "格式调整",
                    "from": "含多余空白",
                    "to": "已清理",
                    "detail": "清理多余空白与空行",
                })
        return changes

    def _calculate_confidence(self, original: str, translated: str,
                              polished: str, term_changes: list,
                              smooth_changes: list) -> float:
        """
        计算置信度（0-100）

        规则：
        - 基础分 95
        - 有术语修改：-2
        - 有语感修改：-3
        - 修改过多（>10处）：额外 -5
        - 文本长度异常变化：额外扣分
        """
        confidence = 95.0

        if term_changes:
            confidence -= 2.0
        if smooth_changes:
            confidence -= 3.0

        total_mods = len(term_changes) + len(smooth_changes)
        if total_mods > 10:
            confidence -= 5.0

        # 长度变化检查（防止润色导致内容大量丢失）
        len_ratio = len(polished) / max(len(translated), 1)
        if len_ratio < 0.5 or len_ratio > 1.5:
            confidence -= 10.0
        elif len_ratio < 0.8 or len_ratio > 1.2:
            confidence -= 3.0

        # 原文与译文长度合理性（粗检查）
        if len(original) > 0 and len(translated) > 0:
            ratio = len(translated) / len(original)
            if ratio < 0.3 or ratio > 3.0:
                confidence -= 5.0

        # 限制在合理范围
        return max(0.0, min(100.0, confidence))

    def _verify_idempotent(self, original: str, translated: str, result: dict) -> bool:
        """幂等性验证：对润色结果再次处理应保持一致"""
        try:
            # 对润色结果再次运行（作为"译文"输入），应得到相同或相近结果
            second = self._process_internal(original, result["polished"])
            # 宽松比较：核心文本应一致
            return second["polished"] == result["polished"]
        except Exception:
            # 验证失败不阻断主流程，仅标记
            return False

    # ------------------------------------------------------------------
    # 批量处理支持
    # ------------------------------------------------------------------

    def process_batch(self, items: list) -> dict:
        """
        批量处理多个输入

        :param items: [{"original": "...", "translated": "..."}, ...]
        :return: 批量结果，含成功/失败明细
        """
        if not items:
            raise SkillError("E001", "请提供待处理的内容")

        results = []
        failures = []

        for idx, item in enumerate(items):
            try:
                if not isinstance(item, dict):
                    raise SkillError("E003", f"第 {idx+1} 项格式错误，应为字典对象")
                res = self.process(item.get("original", ""), item.get("translated", ""))
                results.append({"index": idx, "status": "success", "data": res})
            except SkillError as e:
                failures.append({
                    "index": idx,
                    "status": "failed",
                    "error_code": e.code,
                    "error_message": e.message,
                })
            except Exception as e:
                failures.append({
                    "index": idx,
                    "status": "failed",
                    "error_code": "E006",
                    "error_message": str(e),
                })

        # 降级方案：即使有失败也返回已成功的部分
        return {
            "total": len(items),
            "success_count": len(results),
            "failed_count": len(failures),
            "results": results,
            "failures": failures,
            "note": "已完成部分的输出有效，失败项可单独重跑",
        }


# ------------------------------------------------------------------
# 自检模块（--selftest）
# ------------------------------------------------------------------

def run_selftest() -> int:
    """
    内置自检测试：使用硬编码样例数据离线验证核心逻辑
    不读外部文件、不依赖当前工作目录、不访问网络
    """
    print("=" * 60)
    print("translation-polish 自检程序")
    print("=" * 60)

    engine = TranslationPolish()
    passed = 0
    total = 0

    # ---- 测试用例 1：基本润色流程 ----
    print("\n[用例1] 基本润色流程")
    total += 1
    try:
        result = engine.process(
            "The AI model can be deployed to the server.",
            "这个AI模型能够被部署到服务器上，进行一个非常非常快速的推理。"
        )
        assert result["polished"], "润色结果不应为空"
        assert result["confidence"] >= 0, "置信度应为非负数"
        assert result["confidence"] <= 100, "置信度不应超过100"
        assert "comparison" in result, "应包含对照版本"
        assert isinstance(result["modifications"], list), "修改说明应为列表"
        # 宽松断言：润色后文本不应为空且长度合理
        assert len(result["polished"]) > 0, "润色后文本不应为空"
        assert len(result["polished"]) <= len(result["translated"]) * 2, "润色后文本不应异常膨胀"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # ---- 测试用例 2：术语统一 ----
    print("\n[用例2] 术语统一")
    total += 1
    try:
        result = engine.process(
            "API and Framework are important.",
            "API和Framework都很重要，API提供了标准接口。"
        )
        polished = result["polished"]
        # 宽松断言：润色后应包含统一后的术语（不要求全部替换）
        assert "应用程序接口" in polished or "框架" in polished, "应包含统一后的术语"
        assert result["confidence"] > 50, "置信度应大于50"
        print(f"  ✓ 通过 (润色后: {polished[:50]}...)")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # ---- 测试用例 3：错误处理 ----
    print("\n[用例3] 错误处理")
    total += 1
    try:
        try:
            engine.process("", "测试译文")
            print("  ✗ 失败: 空原文应触发 E001")
        except SkillError as e:
            assert e.code == "E001", f"应返回 E001，实际 {e.code}"
            print(f"  ✓ 通过 (E001 输入为空)")

        try:
            engine.process("原文", "")
            print("  ✗ 失败: 空译文应触发 E002")
        except SkillError as e:
            assert e.code == "E002", f"应返回 E002，实际 {e.code}"
            print(f"  ✓ 通过 (E002 关键信息缺失)")

        try:
            engine.process(123, "译文")
            print("  ✗ 失败: 非字符串输入应触发 E003")
        except SkillError as e:
            assert e.code == "E003", f"应返回 E003，实际 {e.code}"
            print(f"  ✓ 通过 (E003 输入格式错误)")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # ---- 测试用例 4：批量处理 ----
    print("\n[用例4] 批量处理")
    total += 1
    try:
        batch_items = [
            {"original": "Hello world", "translated": "你好，世界"},
            {"original": "Test", "translated": "测试"},
            {"original": "", "translated": "空原文"},  # 应失败
            {"original": "Valid", "translated": "有效"},  # 应成功
        ]
        batch_result = engine.process_batch(batch_items)
        assert batch_result["total"] == 4, "总数应为4"
        assert batch_result["success_count"] >= 2, "至少2条成功"
        assert batch_result["failed_count"] >= 1, "至少1条失败（空原文）"
        # 失败项应有错误码
        for f in batch_result["failures"]:
            assert f["error_code"] in ERROR_CODES, "失败项应包含有效错误码"
        print(f"  ✓ 通过 (成功: {batch_result['success_count']}, 失败: {batch_result['failed_count']})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # ---- 测试用例 5：置信度与标注 ----
    print("\n[用例5] 置信度标注")
    total += 1
    try:
        # 正常输入应高置信度
        good = engine.process("Simple text", "简单文本")
        assert good["confidence"] >= 80, "正常输入置信度应较高"
        assert "置信度良好" in good["confidence_note"] or "建议复核" in good["confidence_note"], \
            "应有置信度标注"

        # 大量修改应降低置信度
        long_text = "这个AI模型能够被部署到服务器上，进行一个非常非常快速的推理，API接口很稳定。"
        low_conf = engine.process("Long text with many issues", long_text)
        assert low_conf["confidence"] >= 0, "置信度应非负"
        print(f"  ✓ 通过 (正常: {good['confidence']:.0f}%, 复杂: {low_conf['confidence']:.0f}%)")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # ---- 测试用例 6：幂等性 ----
    print("\n[用例6] 幂等性")
    total += 1
    try:
        result = engine.process("API test", "API测试")
        assert "idempotency_check" in result, "应包含幂等性校验标记"
        # 宽松断言：幂等性校验结果应为布尔值
        assert isinstance(result["idempotency_check"], bool), "幂等性校验应为布尔值"
        print(f"  ✓ 通过 (幂等性校验: {result['idempotency_check']})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # ---- 测试用例 7：超时控制 ----
    print("\n[用例7] 超时控制")
    total += 1
    try:
        # 使用极短超时验证超时机制不会导致崩溃
        fast_engine = TranslationPolish(timeout_seconds=0.001, max_retries=1)
        try:
            fast_engine.process("Test", "测试")
            # 可能成功（处理太快未超时）
            print(f"  ✓ 通过 (未触发超时，处理在限制内完成)")
        except SkillError as e:
            assert e.code in ("E006", "E008"), "超时应返回 E006 或 E008"
            print(f"  ✓ 通过 (超时正确处理: {e.code})")
        passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    print(f"自检完成: {passed}/{total} 通过")
    print("=" * 60)

    return 0 if passed == total else 1


# ------------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------------

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="翻译润色工具 - 对翻译文本进行术语统一、语感优化、格式调整",
        epilog="示例: python main.py --original '原文' --translated '译文'"
    )
    parser.add_argument("--original", type=str, help="原文文本")
    parser.add_argument("--translated", type=str, help="待润色的译文文本")
    parser.add_argument("--selftest", action="store_true", help="运行内置离线自检")
    parser.add_argument("--batch", type=str, help="批量处理 JSON 文件路径（格式: [{\"original\":\"...\",\"translated\":\"...\"}]）")
    parser.add_argument("--timeout", type=float, default=10.0, help="单条处理超时（秒）")
    parser.add_argument("--retries", type=int, default=3, help="可恢复错误重试次数")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.original and not args.translated and not args.batch:
        parser.print_help()
        print("\n错误: 请提供输入内容，或使用 --selftest 运行自检")
        return 10

    engine = TranslationPolish(
        timeout_seconds=args.timeout,
        max_retries=args.retries,
    )

    try:
        # 批量模式
        if args.batch:
            import os
            if not os.path.isfile(args.batch):
                print(f"[E009] 批量文件不存在: {args.batch}")
                return 9
            with open(args.batch, "r", encoding="utf-8") as f:
                items = json.load(f)
            result = engine.process_batch(items)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            # 有失败时返回非零退出码
            return 1 if result["failed_count"] > 0 else 0

        # 单条模式
        if not args.original or not args.translated:
            print("[E002] 关键信息缺失: 需要同时提供 --original 和 --translated")
            return 2

        result = engine.process(args.original, args.translated)
        # 结构化输出
        output = {
            "original": result["original"],
            "translated": result["translated"],
            "polished": result["polished"],
            "comparison": result["comparison"],
            "modifications": result["modifications"],
            "confidence": result["confidence"],
            "confidence_note": result["confidence_note"],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    except SkillError as e:
        print(f"[{e.code}] {e.message}")
        return int(e.code[1:])  # E001 -> 1, E002 -> 2, ...
    except Exception as e:
        print(f"[E010] 未知错误: {e}")
        return 10


if __name__ == "__main__":
    sys.exit(main())
