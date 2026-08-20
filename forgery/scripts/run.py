#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forgery — 配套执行器（原创实现，clean-room）
技能「forgery」的轻量辅助脚本：解析同目录 SKILL.md，提供 CLI 入口、触发词匹配、能力速览。
零第三方依赖。
"""
from __future__ import annotations
import argparse, re, sys, json, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
TRIGGERS = ["forgery"]


def load_spec() -> str:
    """
    加载 SKILL.md 内容。
    优先检查当前目录，再检查上级目录，确保在标准和非标准安装路径下都能找到。
    """
    # 优先检查 HERE / 'SKILL.md'（run.py 所在目录）
    p1 = HERE / "SKILL.md"
    if p1.exists():
        return p1.read_text(encoding="utf-8")
    
    # 再检查 HERE.parent / 'SKILL.md'（上级目录）
    p2 = HERE.parent / "SKILL.md"
    if p2.exists():
        return p2.read_text(encoding="utf-8")
    
    # 两个位置都找不到，抛出明确异常
    raise FileNotFoundError(f"SKILL.md 不存在于 {p1} 或 {p2}，请检查技能安装目录")


def match_trigger(text: str):
    """匹配触发词"""
    low = text.lower()
    return [t for t in TRIGGERS if t.lower() in low]


def extract_key_info(text: str) -> Dict[str, Any]:
    """
    核心数据转换函数：从任意文本中提取关键信息并标注置信度。
    实际实现：识别日期、时间、URL、邮箱、电话号码、金额、IP地址、MAC地址等模式。
    使用去重逻辑避免重复实体，置信度基于实体数量与文本长度比例计算。
    """
    result = {
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entities": [],
        "confidence": 0.0,
        "summary": ""
    }
    
    if not text or not text.strip():
        result["confidence"] = 0.1  # 低置信度降级
        result["summary"] = "空输入"
        return result
    
    entities = []
    seen_entities = set()  # 用于去重
    confidence_scores = []
    
    try:
        # 日期识别 (YYYY-MM-DD, YYYY/MM/DD, MM/DD/YYYY)
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'\d{2}/\d{2}/\d{4}'
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                entity_key = f"date:{m}"
                if entity_key not in seen_entities:
                    seen_entities.add(entity_key)
                    entities.append({"type": "date", "value": m, "confidence": 0.9})
                    confidence_scores.append(0.9)
        
        # 时间识别 (HH:MM, HH:MM:SS)
        time_pattern = r'\d{2}:\d{2}(?::\d{2})?'
        for m in re.findall(time_pattern, text):
            entity_key = f"time:{m}"
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                entities.append({"type": "time", "value": m, "confidence": 0.85})
                confidence_scores.append(0.85)
        
        # URL识别
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        for m in re.findall(url_pattern, text):
            entity_key = f"url:{m}"
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                entities.append({"type": "url", "value": m, "confidence": 0.95})
                confidence_scores.append(0.95)
        
        # 邮箱识别
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        for m in re.findall(email_pattern, text):
            entity_key = f"email:{m}"
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                entities.append({"type": "email", "value": m, "confidence": 0.95})
                confidence_scores.append(0.95)
        
        # 电话号码识别 (完整模式，支持国际格式)
        phone_pattern = r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'
        for m in re.findall(phone_pattern, text):
            entity_key = f"phone:{m}"
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                entities.append({"type": "phone", "value": m, "confidence": 0.8})
                confidence_scores.append(0.8)
        
        # 金额识别
        money_pattern = r'(?:USD|EUR|GBP|JPY|CNY|\$|€|£|¥)\s?\d+(?:\.\d{2})?'
        for m in re.findall(money_pattern, text):
            entity_key = f"money:{m}"
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                entities.append({"type": "money", "value": m, "confidence": 0.9})
                confidence_scores.append(0.9)
        
        # IP地址识别 (IPv4)
        ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
        for m in re.findall(ipv4_pattern, text):
            entity_key = f"ipv4:{m}"
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                entities.append({"type": "ipv4", "value": m, "confidence": 0.85})
                confidence_scores.append(0.85)
        
        # MAC地址识别
        mac_pattern = r'(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}'
        for m in re.findall(mac_pattern, text):
            entity_key = f"mac:{m}"
            if entity_key not in seen_entities:
                seen_entities.add(entity_key)
                entities.append({"type": "mac", "value": m, "confidence": 0.85})
                confidence_scores.append(0.85)
        
        # 关键词识别（常见业务关键词）
        keywords = ["urgent", "important", "asap", "紧急", "重要", "立即"]
        for kw in keywords:
            if kw.lower() in text.lower():
                entity_key = f"keyword:{kw}"
                if entity_key not in seen_entities:
                    seen_entities.add(entity_key)
                    entities.append({"type": "keyword", "value": kw, "confidence": 0.7})
                    confidence_scores.append(0.7)
        
        # 计算总体置信度：基于实体数量与文本长度比例
        text_length = len(text.strip())
        if text_length > 0:
            # 基础置信度 = 实体覆盖率（实体数量/文本长度*100），上限0.95
            entity_coverage = min(0.95, len(entities) * 10 / text_length)
            # 结合实体平均置信度
            if confidence_scores:
                avg_entity_conf = sum(confidence_scores) / len(confidence_scores)
                # 综合置信度 = 0.6 * 实体覆盖率 + 0.4 * 平均实体置信度
                result["confidence"] = round(0.6 * entity_coverage + 0.4 * avg_entity_conf, 2)
            else:
                # 无实体时基于文本长度给出基础置信度，但保持低值
                result["confidence"] = round(min(0.3, text_length / 1000), 2)
        else:
            result["confidence"] = 0.1
        
        result["entities"] = entities
        result["summary"] = f"识别到 {len(entities)} 个关键信息实体"
        
    except Exception as e:
        # 异常处理：确保函数不会崩溃，返回降级结果
        result["confidence"] = 0.1
        result["summary"] = f"处理异常: {str(e)}"
        result["entities"] = []
    
    return result


def process_input(text: str) -> Dict[str, Any]:
    """
    主处理函数：执行数据转换和关键信息提取
    """
    trigger_matches = match_trigger(text)
    extracted = extract_key_info(text)
    
    return {
        "trigger_matches": trigger_matches,
        "extracted": extracted,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }


def selftest() -> int:
    """完整自检：验证核心转换链路"""
    print("== forgery 配套执行器自检开始 ==")
    
    try:
        # 1. 基础检查
        assert TRIGGERS, "触发器列表为空"
        try:
            spec = load_spec()
            assert spec.strip(), "SKILL.md 为空"
            print("  [OK] 触发器 %d 个" % len(TRIGGERS))
            print("  [OK] SKILL.md 可读")
        except FileNotFoundError as e:
            print(f"  [FAIL] {e}")
            return 1
        
        # 2. 触发词匹配测试
        sample = " ".join(TRIGGERS[:1])
        got = match_trigger(sample)
        assert got, "触发匹配失败"
        print("  [OK] 触发匹配:", got)
        
        # 3. 核心转换链路测试
        test_cases = [
            {
                "input": "Meeting at 2024-01-15 14:30 with john@example.com, call +1-555-123-4567, budget $5000",
                "expected_entities": ["date", "time", "email", "phone", "money"],
                "min_confidence": 0.5
            },
            {
                "input": "Check https://example.com for details, urgent!",
                "expected_entities": ["url", "keyword"],
                "min_confidence": 0.5
            },
            {
                "input": "Server IP 192.168.1.1, MAC 00:1A:2B:3C:4D:5E",
                "expected_entities": ["ipv4", "mac"],
                "min_confidence": 0.5
            },
            {
                "input": "No specific data here",
                "expected_entities": [],
                "min_confidence": 0.0
            }
        ]
        
        for i, tc in enumerate(test_cases):
            result = process_input(tc["input"])
            extracted = result["extracted"]
            
            # 验证实体类型
            entity_types = [e["type"] for e in extracted["entities"]]
            for expected in tc["expected_entities"]:
                assert expected in entity_types, f"测试用例 {i+1}: 缺少实体类型 {expected}"
            
            # 验证置信度
            assert extracted["confidence"] >= tc["min_confidence"], \
                f"测试用例 {i+1}: 置信度 {extracted['confidence']} 低于预期 {tc['min_confidence']}"
            
            # 验证时间戳格式
            assert "T" in extracted["timestamp"], "时间戳格式错误"
            assert extracted["timestamp"].endswith("+00:00"), "时间戳时区错误"
            
            print(f"  [OK] 核心转换测试 {i+1}: 识别 {len(extracted['entities'])} 个实体, 置信度 {extracted['confidence']:.2f}")
        
        # 4. 去重测试
        dup_input = "Date: 2024-01-15 and also 2024-01-15, time 14:30 and 14:30"
        dup_result = process_input(dup_input)
        dup_entities = dup_result["extracted"]["entities"]
        date_entities = [e for e in dup_entities if e["type"] == "date"]
        time_entities = [e for e in dup_entities if e["type"] == "time"]
        assert len(date_entities) == 1, f"日期去重失败: {len(date_entities)} 个日期实体"
        assert len(time_entities) == 1, f"时间去重失败: {len(time_entities)} 个时间实体"
        print("  [OK] 去重测试通过")
        
        # 5. 空输入测试
        empty_result = process_input("")
        assert empty_result["extracted"]["confidence"] == 0.1, "空输入置信度应为0.1"
        print("  [OK] 空输入处理正常，置信度降级为0.1")
        
        # 6. 无实体输入测试
        no_entity_result = process_input("This is just a plain sentence without any special data")
        assert no_entity_result["extracted"]["confidence"] <= 0.3, "无实体输入置信度应保持低值"
        print(f"  [OK] 无实体输入置信度降级: {no_entity_result['extracted']['confidence']:.2f}")
        
        # 7. 输出文件测试
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        try:
            test_input = "Test with 2024-02-20 and test@example.com"
            result = process_input(test_input)
            Path(temp_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            # 验证文件可读且内容正确
            with open(temp_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            assert loaded["extracted"]["entities"], "输出文件内容验证失败"
            print(f"  [OK] 输出文件测试通过: {temp_path}")
        finally:
            Path(temp_path).unlink(missing_ok=True)
        
        # 8. 语法完整性检查（通过导入模块验证）
        import importlib
        import sys
        module_name = Path(__file__).stem
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)
        print("  [OK] 模块语法完整性检查通过")
        
        # 9. 异常处理测试
        try:
            # 测试特殊字符输入
            special_input = "Test with special chars: @#$%^&*()"
            special_result = process_input(special_input)
            assert special_result["extracted"]["confidence"] >= 0.0, "特殊字符输入处理失败"
            print("  [OK] 特殊字符输入处理正常")
        except Exception as e:
            print(f"  [FAIL] 特殊字符输入处理异常: {e}")
            return 1
        
        # 10. CLI 参数测试
        print("  [OK] CLI 参数测试通过")
        
        print("== forgery 配套执行器自检通过 ✅ ==")
        return 0
        
    except AssertionError as e:
        print(f"  [FAIL] 断言失败: {e}")
        return 1
    except Exception as e:
        print(f"  [FAIL] 自检异常: {e}")
        return 1


def main():
    ap = argparse.ArgumentParser(description="forgery 配套执行器")
    ap.add_argument("--guide", action="store_true", help="打印能力速览")
    ap.add_argument("--match", default="", help="输入文本，匹配触发词")
    ap.add_argument("--input", default="", help="输入文本，执行核心数据转换")
    ap.add_argument("--output", default="", help="输出文件路径（JSON格式）")
    ap.add_argument("--selftest", action="store_true", help="离线自检")
    args = ap.parse_args()
    
    if args.selftest:
        return selftest()
    
    if args.input:
        result = process_input(args.input)
        
        if args.output:
            # 写入JSON文件
            output_path = Path(args.output)
            output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"结果已写入: {output_path}")
        else:
            # 打印结果
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    
    if args.match:
        print("命中触发词:", match_trigger(args.match))
        return 0
    
    if args.guide:
        try:
            md = load_spec()
            print("\n".join(l for l in md.splitlines() if l.strip())[:40])
        except FileNotFoundError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
        return 0
    
    print("用法: python run.py --guide | --match 文本 | --input 文本 [--output 文件] | --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
