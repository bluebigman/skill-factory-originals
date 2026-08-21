#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能包：问诊全流程 文本处理 术语规范
提供问诊对话文本的一站式处理：识别、整理、术语规范化与结果校验输出。
"""
import sys
import re
import argparse
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
dry_run = False  # v3.274 模块级 dry-run 标志


class MedicalTermNormalizer:
    """术语规范化：口语表述 -> 规范医学术语"""
    
    def __init__(self):
        # 口语表述 -> 规范术语映射表
        self.term_map = {
            '胸口疼': '胸痛',
            '胸口痛': '胸痛',
            '拉肚子': '腹泻',
            '脑袋晕': '头晕',
            '头晕': '头晕',
            '喘不上气': '呼吸困难',
            '喘不过气': '呼吸困难',
            '胃里反酸': '反酸',
            '反酸': '反酸',
            '身上没劲': '乏力',
            '没劲': '乏力',
            '睡不着': '失眠',
            '恶心干呕': '恶心',
            '干呕': '恶心',
            '恶心': '恶心',
            '头疼': '头痛',
            '头痛': '头痛',
            '肚子疼': '腹痛',
            '肚子痛': '腹痛',
            '发烧': '发热',
            '发高烧': '高热',
            '咳嗽': '咳嗽',
            '嗓子疼': '咽痛',
            '嗓子痛': '咽痛',
            '后背疼': '背痛',
            '后背痛': '背痛',
            '腰疼': '腰痛',
            '腰酸': '腰痛',
            '关节疼': '关节痛',
            '浑身疼': '全身疼痛',
            '心慌': '心悸',
            '心跳快': '心悸',
            '胸闷': '胸闷',
            '气短': '气促',
            '没胃口': '食欲不振',
            '不想吃饭': '食欲不振',
            '呕吐': '呕吐',
            '吐了': '呕吐',
            '便秘': '便秘',
            '便血': '便血',
            '尿频': '尿频',
            '尿急': '尿急',
            '尿痛': '尿痛',
            '浮肿': '水肿',
            '肿了': '水肿',
            '皮疹': '皮疹',
            '起疹子': '皮疹',
            '痒': '瘙痒',
            '发痒': '瘙痒',
            '麻木': '麻木',
            '麻了': '麻木',
            '无力': '乏力',
            '没力气': '乏力',
            '疲劳': '乏力',
            '疲倦': '乏力',
            '犯困': '嗜睡',
            '嗜睡': '嗜睡',
            '出汗': '出汗',
            '盗汗': '盗汗',
            '怕冷': '畏寒',
            '发冷': '畏寒',
            '寒战': '寒战',
            '打冷战': '寒战',
        }
    
    def normalize(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        将文本中的口语表述规范化为医学术语
        
        Returns:
            (规范化后的文本, [(原始表述, 规范术语), ...])
        """
        normalized_text = text
        mappings = []
        
        # 按长度降序排列，优先匹配长词
        for slang, term in sorted(self.term_map.items(), key=lambda x: len(x[0]), reverse=True):
            if slang in normalized_text:
                normalized_text = normalized_text.replace(slang, term)
                mappings.append((slang, term))
        
        return normalized_text, mappings


class ConsultationProcessor:
    """问诊文本处理器：识别、整理、术语规范化与结果校验"""
    
    def __init__(self):
        self.normalizer = MedicalTermNormalizer()
        
        # 说话人标记模式
        self.speaker_patterns = [
            re.compile(r'^(医生|医师|大夫|医者|Dr\.?|医生：|医师：|大夫：)\s*[:：]?\s*'),
            re.compile(r'^(患者|病人|病人：|患者：)\s*[:：]?\s*'),
        ]
        
        # 症状关键词（用于主诉抽取）
        self.symptom_keywords = [
            '痛', '疼', '晕', '眩', '吐', '泻', '咳', '喘', '闷', '慌',
            '热', '烧', '肿', '胀', '麻', '痒', '酸', '乏力', '失眠',
            '食欲', '恶心', '心悸', '气短', '出汗', '畏寒', '寒战',
            '皮疹', '水肿', '便秘', '便血', '尿频', '尿急', '尿痛',
        ]
        
        # 时间关键词
        self.time_keywords = [
            '天', '周', '月', '年', '小时', '分钟', '日', '夜',
            '早上', '中午', '晚上', '昨天', '今天', '明天', '前天',
            '刚刚', '最近', '一直', '反复', '间断', '持续',
        ]
    
    def preprocess(self, text: str) -> List[Dict[str, str]]:
        """
        输入预处理：去除冗余信息，按说话人分组对话轮次
        
        Returns:
            对话轮次列表: [{'speaker': '医生'|'患者', 'text': str}, ...]
        """
        if not text or not text.strip():
            raise ValueError("E1001: 未检测到有效文本，请提供问诊对话内容")
        
        if len(text) > 10000:
            raise ValueError("E1002: 输入文本超过10000字限制，请分段处理")
        
        # 按行分割
        lines = text.strip().split('\n')
        turns = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 去除时间戳 [12:30:45] 或 (12:30)
            line = re.sub(r'[\[\(]\d{1,2}:\d{2}(:\d{2})?[\]\)]', '', line)
            line = line.strip()
            if not line:
                continue
            
            # 识别说话人
            speaker = None
            content = line
            
            # 尝试匹配说话人标记
            for pattern in self.speaker_patterns:
                match = pattern.match(line)
                if match:
                    prefix = match.group(0)
                    if '医生' in prefix or '医师' in prefix or '大夫' in prefix or 'Dr' in prefix:
                        speaker = '医生'
                    else:
                        speaker = '患者'
                    content = line[match.end():].strip()
                    break
            
            # 如果没有明确标记，尝试根据内容判断
            if speaker is None:
                # 简单启发式：包含较多症状描述词则认为是患者
                symptom_count = sum(1 for kw in self.symptom_keywords if kw in line)
                if symptom_count >= 2:
                    speaker = '患者'
                else:
                    speaker = '医生'
            
            if content:
                turns.append({'speaker': speaker, 'text': content})
        
        if not turns:
            raise ValueError("E1001: 未检测到有效文本，请提供问诊对话内容")
        
        return turns
    
    def extract_chief_complaint(self, turns: List[Dict[str, str]]) -> str:
        """
        抽取主诉：患者最主要的症状/体征+持续时间
        """
        # 收集患者的所有表述
        patient_texts = [t['text'] for t in turns if t['speaker'] == '患者']
        if not patient_texts:
            return "[需核实:主诉]"
        
        full_text = ' '.join(patient_texts)
        
        # 查找症状关键词
        symptoms = []
        for kw in self.symptom_keywords:
            if kw in full_text:
                symptoms.append(kw)
        
        if not symptoms:
            return "[需核实:主诉]"
        
        # 查找时间信息
        duration = None
        for time_kw in self.time_keywords:
            # 匹配 "数字+时间单位" 或 "时间词"
            pattern = re.compile(r'(\d+)\s*' + time_kw)
            match = pattern.search(full_text)
            if match:
                duration = match.group(0)
                break
        
        # 构建主诉
        if duration:
            chief = f"{'、'.join(symptoms[:3])}{duration}"
        else:
            chief = '、'.join(symptoms[:3])
            if len(symptoms) > 0:
                chief += "[需核实:时间]"
        
        return chief
    
    def extract_present_illness(self, turns: List[Dict[str, str]]) -> str:
        """
        抽取现病史：症状发生、发展、诊疗经过
        """
        patient_texts = [t['text'] for t in turns if t['speaker'] == '患者']
        doctor_texts = [t['text'] for t in turns if t['speaker'] == '医生']
        
        if not patient_texts:
            return "[需核实:现病史]"
        
        # 合并患者表述，去除重复
        seen = set()
        unique_texts = []
        for text in patient_texts:
            if text not in seen:
                seen.add(text)
                unique_texts.append(text)
        
        # 简单拼接
        present = '；'.join(unique_texts)
        
        # 规范化术语
        normalized, _ = self.normalizer.normalize(present)
        
        # 检查是否包含起病时间
        has_time = any(kw in normalized for kw in ['天前', '周前', '月前', '年前', '小时前', '昨天', '今天', '最近'])
        if not has_time:
            normalized += "[需核实:时间]"
        
        return normalized
    
    def extract_past_history(self, turns: List[Dict[str, str]]) -> str:
        """
        抽取既往史：既往疾病、手术、过敏史
        """
        patient_texts = [t['text'] for t in turns if t['speaker'] == '患者']
        full_text = ' '.join(patient_texts)
        
        # 关键词匹配
        history_keywords = ['既往', '以前', '曾经', '有过', '病史', '过敏', '手术', '住院', '高血压', '糖尿病', '心脏病']
        found = []
        
        for kw in history_keywords:
            if kw in full_text:
                # 提取相关句子
                idx = full_text.find(kw)
                start = max(0, idx - 20)
                end = min(len(full_text), idx + 30)
                snippet = full_text[start:end].strip()
                found.append(snippet)
        
        if found:
            return '；'.join(found[:3])
        else:
            return "[需核实:既往史]"
    
    def extract_physical_exam(self, turns: List[Dict[str, str]]) -> str:
        """
        抽取体格检查：生命体征、阳性体征
        """
        doctor_texts = [t['text'] for t in turns if t['speaker'] == '医生']
        full_text = ' '.join(doctor_texts)
        
        # 生命体征模式
        vital_signs = []
        
        # 体温
        temp_match = re.search(r'T[:：]?\s*(\d+\.?\d*)\s*℃', full_text)
        if temp_match:
            vital_signs.append(f"T:{temp_match.group(1)}℃")
        
        # 脉搏
        pulse_match = re.search(r'P[:：]?\s*(\d+)\s*次/分', full_text)
        if pulse_match:
            vital_signs.append(f"P:{pulse_match.group(1)}次/分")
        
        # 呼吸
        resp_match = re.search(r'R[:：]?\s*(\d+)\s*次/分', full_text)
        if resp_match:
            vital_signs.append(f"R:{resp_match.group(1)}次/分")
        
        # 血压
        bp_match = re.search(r'BP[:：]?\s*(\d+)/(\d+)\s*mmHg', full_text)
        if bp_match:
            vital_signs.append(f"BP:{bp_match.group(1)}/{bp_match.group(2)}mmHg")
        
        # 阳性体征关键词
        positive_signs = []
        sign_keywords = ['充血', '红肿', '压痛', '反跳痛', '啰音', '杂音', '肿大', '畸形', '活动受限']
        for kw in sign_keywords:
            if kw in full_text:
                idx = full_text.find(kw)
                start = max(0, idx - 10)
                end = min(len(full_text), idx + 15)
                snippet = full_text[start:end].strip()
                positive_signs.append(snippet)
        
        if vital_signs or positive_signs:
            parts = vital_signs + positive_signs
            return '；'.join(parts)
        else:
            return "[需核实:体格检查]"
    
    def generate_preliminary_impression(self, chief_complaint: str) -> List[str]:
        """
        生成初步印象（仅供医生参考）
        """
        impressions = []
        
        if '胸痛' in chief_complaint or '胸' in chief_complaint:
            impressions.append("胸痛待查（需排除心源性胸痛）")
        if '腹痛' in chief_complaint or '腹' in chief_complaint:
            impressions.append("腹痛待查（需排除急腹症）")
        if '头痛' in chief_complaint or '头' in chief_complaint:
            impressions.append("头痛待查")
        if '发热' in chief_complaint or '热' in chief_complaint:
            impressions.append("发热待查")
        if '咳嗽' in chief_complaint or '咳' in chief_complaint:
            impressions.append("咳嗽待查（需排除呼吸道感染）")
        if '腹泻' in chief_complaint or '泻' in chief_complaint:
            impressions.append("腹泻待查（需排除肠道感染）")
        
        if not impressions:
            impressions.append("症状待查")
        
        impressions.append("建议进一步检查")
        return impressions
    
    def check_completeness(self, data: Dict[str, str]) -> List[str]:
        """
        完整性校验
        """
        issues = []
        
        # 主诉完整性
        if '主诉' in data and data['主诉']:
            if '[需核实' in data['主诉']:
                issues.append("主诉信息不完整，缺少症状或持续时间")
        else:
            issues.append("主诉缺失")
        
        # 现病史完整性
        if '现病史' in data and data['现病史']:
            if '[需核实' in data['现病史']:
                issues.append("现病史信息不完整，缺少起病时间或症状演变")
        else:
            issues.append("现病史缺失")
        
        # 字段齐全性
        required_fields = ['主诉', '现病史']
        for field in required_fields:
            if field not in data or not data[field]:
                issues.append(f"必填字段缺失: {field}")
        
        return issues
    
    def process(self, text: str) -> str:
        """
        处理问诊文本，输出结构化问诊记录草稿
        """
        # Step 1: 输入预处理
        turns = self.preprocess(text)
        
        # Step 2: 信息抽取与分类
        chief_complaint = self.extract_chief_complaint(turns)
        present_illness = self.extract_present_illness(turns)
        past_history = self.extract_past_history(turns)
        physical_exam = self.extract_physical_exam(turns)
        impressions = self.generate_preliminary_impression(chief_complaint)
        
        # Step 3: 术语规范化（对现病史进行规范化）
        normalized_present, term_mappings = self.normalizer.normalize(present_illness)
        
        # Step 4: 结构化输出
        data = {
            '主诉': chief_complaint,
            '现病史': normalized_present,
            '既往史': past_history,
            '体格检查': physical_exam,
            '初步印象': impressions,
        }
        
        # Step 5: 完整性校验
        issues = self.check_completeness(data)
        
        # 生成输出
        output = []
        output.append("# 问诊记录草稿")
        output.append("")
        output.append("## 主诉")
        output.append(chief_complaint)
        output.append("")
        output.append("## 现病史")
        output.append(normalized_present)
        output.append("")
        output.append("## 既往史")
        output.append(past_history)
        output.append("")
        output.append("## 体格检查")
        output.append(physical_exam)
        output.append("")
        output.append("## 初步印象")
        for imp in impressions:
            output.append(f"- {imp}")
        output.append("")
        
        # 术语规范化记录
        if term_mappings:
            output.append("## 术语规范化记录")
            for original, normalized in term_mappings:
                output.append(f"原始表述：{original} → 规范术语：{normalized}")
            output.append("")
        
        # 待核实清单
        pending_items = []
        for field, value in data.items():
            if isinstance(value, str) and '[需核实' in value:
                pending_items.append(field)
            elif isinstance(value, list):
                for item in value:
                    if '[需核实' in str(item):
                        pending_items.append(field)
                        break
        
        if pending_items:
            output.append("## 待核实清单")
            for item in pending_items:
                output.append(f"- {item}")
            output.append("")
        
        # 校验问题
        if issues:
            output.append("## 校验提示")
            for issue in issues:
                output.append(f"- {issue}")
            output.append("")
        
        output.append("---")
        output.append("*本记录由AI辅助生成，仅供医疗专业人员参考，不构成医疗建议。*")
        
        return '\n'.join(output)
    
    def process_batch(self, texts: List[str]) -> List[str]:
        """
        批量处理多个问诊文本
        """
        results = []
        for text in texts:
            try:
                result = self.process(text)
                results.append(result)
            except ValueError as e:
                results.append(f"处理失败: {str(e)}")
        return results


def run_selftest() -> bool:
    """
    运行自检程序
    """
    print("=== 开始自检 ===")
    
    processor = ConsultationProcessor()
    
    # 样例1：完整问诊对话
    test1 = """医生：您好，请问哪里不舒服？
患者：我这两天胸口疼，就是这儿，一按就疼。
医生：疼多久了？
患者：大概三天了吧，昨天开始后背也疼。
医生：有没有恶心、呕吐？
患者：没有，就是疼。
医生：以前有什么病史吗？
患者：没有。
医生：好的，我检查一下。T:36.5℃ P:88次/分 咽部充血"""
    
    try:
        result = processor.process(test1)
        assert '主诉' in result
        assert '现病史' in result
        assert '胸痛' in result or '胸' in result
        print("样例1（完整问诊对话）通过 ✓")
    except Exception as e:
        print(f"样例1（完整问诊对话）失败 ✗: {str(e)}")
        return False
    
    # 样例2：口语化表述规范化
    test2 = "患者：我这两天拉肚子，脑袋晕，身上没劲，睡不着。"
    
    try:
        result = processor.process(test2)
        assert '腹泻' in result
        assert '头晕' in result
        assert '乏力' in result
        assert '失眠' in result
        print("样例2（口语化表述规范化）通过 ✓")
    except Exception as e:
        print(f"样例2（口语化表述规范化）失败 ✗: {str(e)}")
        return False
    
    # 样例3：信息缺失占位符
    test3 = "医生：你好，请问哪里不舒服？患者：就是有点疼。"
    
    try:
        result = processor.process(test3)
        assert '[需核实' in result
        print("样例3（信息缺失占位符）通过 ✓")
    except Exception as e:
        print(f"样例3（信息缺失占位符）失败 ✗: {str(e)}")
        return False
    
    # 样例4：空输入错误处理
    try:
        processor.process("   ")
        print("样例4（空输入）失败 ✗: 应该抛出异常但未抛出")
        return False
    except ValueError as e:
        assert "E1001" in str(e), f"样例4：错误码应为E1001，实际{str(e)}"
        print("样例4（空输入错误处理）通过 ✓")
    except Exception as e:
        print(f"样例4（空输入）失败 ✗: {str(e)}")
        return False
    
    # 样例5：超长输入错误处理
    long_text = "患者：" + "我头疼。" * 3000
    try:
        processor.process(long_text)
        print("样例5（超长输入）失败 ✗: 应该抛出异常但未抛出")
        return False
    except ValueError as e:
        assert "E1002" in str(e), f"样例5：错误码应为E1002，实际{str(e)}"
        print("样例5（超长输入错误处理）通过 ✓")
    except Exception as e:
        print(f"样例5（超长输入）失败 ✗: {str(e)}")
        return False
    
    # 样例6：非问诊文本检测
    test6 = "手术记录：患者在全麻下行腹腔镜胆囊切除术，术中出血少，术后恢复良好。"
    try:
        result = processor.process(test6)
        # 应该能处理但可能输出占位符
        assert result is not None
        print("样例6（非问诊文本处理）通过 ✓")
    except Exception as e:
        print(f"样例6（非问诊文本处理）失败 ✗: {str(e)}")
        return False
    
    # 样例7：批量处理
    try:
        texts = [
            "医生：哪里不舒服？患者：我头疼。",
            "医生：你好。患者：我拉肚子两天了。",
        ]
        results = processor.process_batch(texts)
        assert len(results) == 2
        print("样例7（批量处理）通过 ✓")
    except Exception as e:
        print(f"样例7（批量处理）失败 ✗: {str(e)}")
        return False
    
    # 样例8：术语规范化映射
    try:
        normalizer = MedicalTermNormalizer()
        normalized, mappings = normalizer.normalize("我胸口疼，拉肚子")
        assert '胸痛' in normalized
        assert '腹泻' in normalized
        assert len(mappings) >= 2
        print("样例8（术语规范化映射）通过 ✓")
    except Exception as e:
        print(f"样例8（术语规范化映射）失败 ✗: {str(e)}")
        return False
    
    print("=== 自检完成 ===")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='问诊全流程 文本处理 术语规范')
    parser.add_argument('--selftest', action='store_true', help='运行自检程序')
    parser.add_argument('--input', type=str, help='输入问诊文本')
    parser.add_argument('--file', type=str, help='从文件读取问诊文本')
    parser.add_argument('--output', type=str, help='输出文件路径')
    parser.add_argument('--interactive', action='store_true', help='交互模式')
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 运行自检
    if args.selftest:
        ok = run_selftest()
        sys.exit(0 if ok else 1)
    
    # 创建处理器
    processor = ConsultationProcessor()
    
    # 交互模式
    if args.interactive:
        print("问诊文本处理器已启动（输入'退出'结束）")
        print("请输入问诊对话文本：")
        lines = []
        while True:
            try:
                line = input()
                if line in ['退出', 'quit', 'exit']:
                    break
                lines.append(line)
            except EOFError:
                break
        
        if lines:
            text = '\n'.join(lines)
            try:
                result = processor.process(text)
                print("\n" + "="*50)
                print(result)
            except Exception as e:
                print(f"错误: {str(e)}")
        return
    
    # 从文件读取
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            result = processor.process(text)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"结果已保存到: {args.output}")
            else:
                print(result)
        except Exception as e:
            print(f"错误: {str(e)}")
            sys.exit(1)
        return
    
    # 单次输入模式
    if args.input:
        try:
            result = processor.process(args.input)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"结果已保存到: {args.output}")
            else:
                print(result)
        except Exception as e:
            print(f"错误: {str(e)}")
            sys.exit(1)
        return
    
    # 默认模式：演示
    print("问诊全流程 文本处理 术语规范")
    print("示例输入：")
    print("  医生：您好，请问哪里不舒服？")
    print("  患者：我这两天胸口疼，拉肚子。")
    print("输入'退出'结束程序")
    print()
    
    lines = []
    while True:
        try:
            line = input()
            if line in ['退出', 'quit', 'exit']:
                break
            lines.append(line)
        except EOFError:
            break
    
    if lines:
        text = '\n'.join(lines)
        try:
            result = processor.process(text)
            print("\n" + "="*50)
            print(result)
        except Exception as e:
            print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()
