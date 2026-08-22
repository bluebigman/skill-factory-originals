#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sop-packager 独立实现脚本
功能：将重复性操作整理为标准作业程序（SOP），供AI自动执行。
本脚本为 clean-room 实现，仅依据功能规格独立编写。
"""

import sys
import json
import argparse
import re
import time
import urllib.request
import urllib.error
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "输入内容为空",
    "E002": "输入格式不支持",
    "E003": "无法解析输入内容",
    "E004": "输出格式不支持",
    "E005": "批量处理失败",
    "E006": "自定义字段配置错误",
    "E007": "文件读取失败",
    "E008": "URL访问失败",
    "E009": "内部处理异常",
    "E010": "参数配置错误",
}


class SOPError(Exception):
    """SOP处理异常类"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


class SOPExtractor:
    """
    SOP信息提取器
    从非结构化文本中提取动作、条件、责任人、时限等要素
    """
    
    # 动作关键词（精简，避免重复和误匹配）
    # 使用前后边界约束，避免匹配"应该"等非动作场景
    # 修复：将'完成'从负向前瞻中移除，避免误排除合法动作
    ACTION_PATTERNS = [
        r"(?:请|需要|必须|应当)?\s*(?:执行|进行|完成|操作|设置|配置|检查|确认|验证|提交|发送|接收|创建|删除|更新|修改|启动|停止|重启|安装|卸载|备份|恢复|导出|导入|点击|打开|关闭|输入|选择|勾选|取消|保存|加载|上传|下载|连接|断开|授权|审批|通知|报告|记录|登记|整理|归档|清理|扫描|检测|测试)(?!了|过|一下|完毕)(?=\s|$|[，。；：])",
    ]
    
    # 条件关键词
    CONDITION_PATTERNS = [
        r"如果|若|当|如遇|一旦|除非|只有|必须满足|前提|条件",
        r"在.{0,20}情况下|当.{0,20}时",
    ]
    
    # 责任人关键词
    OWNER_PATTERNS = [
        r"(?:由|交给|指定|通知)\s*([\u4e00-\u9fa5A-Za-z0-9_]+)",
        r"责任人[:：]\s*([\u4e00-\u9fa5A-Za-z0-9_]+)",
        r"负责人[:：]\s*([\u4e00-\u9fa5A-Za-z0-9_]+)",
    ]
    
    # 时限关键词
    DEADLINE_PATTERNS = [
        r"(?:在|于)?\s*(\d+\s*(?:分钟|小时|天|周|月|年))\s*(?:内|之内|以内|前|之前)",
        r"(?:截止|最晚|不迟于)\s*([\d年月日:：\s]+)",
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ]
    
    def __init__(self, min_confidence: float = 0.3):
        """初始化提取器
        
        Args:
            min_confidence: 最小置信度阈值，低于此值的字段标注为低置信度
        """
        self.min_confidence = min_confidence
    
    def extract(self, text: str) -> Dict[str, Any]:
        """从文本中提取SOP要素
        
        Args:
            text: 输入的非结构化文本
            
        Returns:
            结构化SOP数据字典
        """
        if not text or not text.strip():
            raise SOPError("E001")
        
        # 检测编码（简单检测是否包含常见乱码字符）
        if self._detect_encoding_issue(text):
            raise SOPError("E003", "输入文本编码异常，请检查编码格式")
        
        steps = self._extract_steps(text)
        if not steps:
            # 尝试将整个文本作为一个步骤
            steps = [self._parse_step(text)]
        
        # 提取全局信息
        title = self._extract_title(text)
        owner = self._extract_owner(text)
        deadline = self._extract_deadline(text)
        
        # 计算整体置信度
        confidence = self._calculate_confidence(steps)
        
        # 生成SOP结构化数据
        sop_data = self._build_sop_structure(steps, title, owner, deadline, confidence)
        
        return sop_data
    
    def _build_sop_structure(self, steps: List[Dict[str, Any]], title: Optional[str], 
                            owner: Optional[str], deadline: Optional[str], 
                            confidence: float) -> Dict[str, Any]:
        """构建完整的SOP结构化数据
        
        实现完整的SOP生成逻辑：
        - 步骤排序
        - 条件分支
        - 责任人分配
        - 时限校验
        """
        # 步骤排序：按置信度降序，确保高置信度步骤在前
        sorted_steps = sorted(steps, key=lambda x: x.get("confidence", 0), reverse=True)
        
        # 重新编号步骤
        numbered_steps = []
        for idx, step in enumerate(sorted_steps, 1):
            step["step_number"] = idx
            step["id"] = f"step_{idx}"
            
            # 条件分支处理
            if step.get("condition"):
                step["branch"] = {
                    "type": "conditional",
                    "condition": step["condition"],
                    "true_action": step.get("action", ""),
                    "false_action": None
                }
            else:
                step["branch"] = {
                    "type": "sequential",
                    "condition": None,
                    "true_action": step.get("action", ""),
                    "false_action": None
                }
            
            # 责任人分配
            if not step.get("owner") and owner:
                step["owner"] = owner
                step["owner_source"] = "inherited"
            else:
                step["owner_source"] = "explicit" if step.get("owner") else "unassigned"
            
            # 时限校验
            if step.get("deadline"):
                step["deadline_valid"] = self._validate_deadline(step["deadline"])
            else:
                step["deadline_valid"] = True
                step["deadline"] = deadline if deadline else None
            
            numbered_steps.append(step)
        
        return {
            "title": title or "未命名SOP",
            "owner": owner,
            "deadline": deadline,
            "steps": numbered_steps,
            "confidence": confidence,
            "metadata": {
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "source_type": "text",
                "step_count": len(numbered_steps),
                "sop_version": "1.0",
                "generator": "sop-packager",
                "generation_time": datetime.now(timezone.utc).isoformat(),
            },
            "warnings": self._generate_warnings(numbered_steps, confidence),
            "execution_plan": self._generate_execution_plan(numbered_steps),
        }
    
    def _validate_deadline(self, deadline_str: str) -> bool:
        """校验时限格式是否有效"""
        # 检查是否包含有效的时间单位
        time_units = ["分钟", "小时", "天", "周", "月", "年"]
        if any(unit in deadline_str for unit in time_units):
            # 提取数字部分
            numbers = re.findall(r'\d+', deadline_str)
            if numbers:
                return int(numbers[0]) > 0
        return False
    
    def _generate_execution_plan(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成可执行的执行计划"""
        plan = []
        for step in steps:
            plan_item = {
                "step_id": step["id"],
                "action": step.get("action") or step.get("description", ""),
                "condition": step.get("condition"),
                "owner": step.get("owner"),
                "deadline": step.get("deadline"),
                "dependencies": [],
                "estimated_duration": None,
                "status": "pending",
                "priority": "normal"
            }
            
            # 如果有条件，添加依赖关系
            if step.get("condition"):
                plan_item["dependencies"].append("condition_check")
            
            plan.append(plan_item)
        
        return plan
    
    def _detect_encoding_issue(self, text: str) -> bool:
        """检测文本编码问题"""
        # 检查是否包含常见的乱码字符
        garbled_patterns = [
            r'[\ufffd]',  # Unicode替换字符
            r'[\x00-\x08\x0b\x0c\x0e-\x1f]',  # 控制字符
            r'Ã[\x80-\xbf]',  # UTF-8被误读为Latin-1
        ]
        for pattern in garbled_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _extract_steps(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取步骤列表"""
        # 按常见步骤标记分割
        lines = text.split('\n')
        steps = []
        current_step = []
        step_pattern = re.compile(r'^\s*(?:步骤|第[一二三四五六七八九十\d]+步|Step\s*\d+|\d+[\.、)])')
        
        for line in lines:
            if step_pattern.match(line) and current_step:
                # 完成当前步骤
                step_text = '\n'.join(current_step).strip()
                if step_text:
                    steps.append(self._parse_step(step_text))
                current_step = [line]
            else:
                current_step.append(line)
        
        # 处理最后一个步骤
        if current_step:
            step_text = '\n'.join(current_step).strip()
            if step_text:
                steps.append(self._parse_step(step_text))
        
        # 如果按行分割没有找到步骤，尝试按段落分割
        if not steps:
            paragraphs = re.split(r'\n\s*\n', text.strip())
            for para in paragraphs:
                if para.strip():
                    steps.append(self._parse_step(para.strip()))
        
        # 去重：按描述文本内容去重，保留首次出现的位置
        seen_descriptions = set()
        unique_steps = []
        for step in steps:
            desc = step.get("description", "").strip()
            if desc and desc not in seen_descriptions:
                seen_descriptions.add(desc)
                unique_steps.append(step)
        
        return unique_steps
    
    def _parse_step(self, text: str) -> Dict[str, Any]:
        """解析单个步骤"""
        step = {
            "description": text.strip(),
            "action": None,
            "condition": None,
            "owner": None,
            "deadline": None,
            "confidence": 0.5,  # 默认中等置信度
        }
        
        # 提取动作（使用合并后的单一正则）
        action_found = False
        for pattern in self.ACTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                action_text = match.group(0).strip()
                # 验证是否包含实际动词（排除只有"请"等无动词的情况）
                verb_pattern = r"(?:执行|进行|完成|操作|设置|配置|检查|确认|验证|提交|发送|接收|创建|删除|更新|修改|启动|停止|重启|安装|卸载|备份|恢复|导出|导入|点击|打开|关闭|输入|选择|勾选|取消|保存|加载|上传|下载|连接|断开|授权|审批|通知|报告|记录|登记|整理|归档|清理|扫描|检测|测试)"
                if re.search(verb_pattern, action_text):
                    step["action"] = action_text
                    step["confidence"] = min(0.9, step["confidence"] + 0.2)
                    action_found = True
                    break
        
        # 提取条件
        for pattern in self.CONDITION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                step["condition"] = match.group(0)
                step["confidence"] = min(0.9, step["confidence"] + 0.1)
                break
        
        # 提取责任人
        owner = self._extract_owner(text)
        if owner:
            step["owner"] = owner
            step["confidence"] = min(0.9, step["confidence"] + 0.1)
        
        # 提取时限
        deadline = self._extract_deadline(text)
        if deadline:
            step["deadline"] = deadline
            step["confidence"] = min(0.9, step["confidence"] + 0.1)
        
        return step
    
    def _extract_title(self, text: str) -> Optional[str]:
        """提取标题"""
        # 查找标题模式
        patterns = [
            r'^#+\s*(.+)$',  # Markdown标题
            r'^(?:标题|名称|主题)[:：]\s*(.+)$',
            r'^《(.+)》$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # 默认使用第一行作为标题
        first_line = text.strip().split('\n')[0]
        if len(first_line) <= 50:
            return first_line
        return None
    
    def _extract_owner(self, text: str) -> Optional[str]:
        """提取责任人"""
        for pattern in self.OWNER_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """提取时限"""
        for pattern in self.DEADLINE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        return None
    
    def _calculate_confidence(self, steps: List[Dict[str, Any]]) -> float:
        """计算整体置信度"""
        if not steps:
            return 0.0
        
        # 平均各步骤置信度
        step_confidences = [step.get("confidence", 0.5) for step in steps]
        avg_confidence = sum(step_confidences) / len(step_confidences)
        
        # 根据步骤信息完整度调整
        complete_steps = 0
        for step in steps:
            if step.get("action") and step.get("condition"):
                complete_steps += 1
        
        completeness_factor = complete_steps / len(steps) if steps else 0
        
        return round(min(0.95, avg_confidence * 0.7 + completeness_factor * 0.3), 2)
    
    def _generate_warnings(self, steps: List[Dict[str, Any]], confidence: float) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        if confidence < self.min_confidence:
            warnings.append("整体置信度较低，建议人工复核提取结果")
        
        for i, step in enumerate(steps, 1):
            if not step.get("action"):
                warnings.append(f"步骤{i}可能缺少明确的动作描述")
            if not step.get("condition"):
                warnings.append(f"步骤{i}可能缺少条件说明")
            if not step.get("owner"):
                warnings.append(f"步骤{i}未分配责任人")
            if step.get("deadline") and not step.get("deadline_valid"):
                warnings.append(f"步骤{i}的时限格式可能无效")
        
        return warnings


class SOPFormatter:
    """SOP格式化输出器"""
    
    SUPPORTED_FORMATS = ["json", "markdown", "md", "text", "txt"]
    
    def __init__(self):
        """初始化格式化器"""
        pass
    
    def format(self, data: Dict[str, Any], output_format: str = "json") -> str:
        """格式化输出
        
        Args:
            data: SOP数据字典
            output_format: 输出格式（json/markdown/text）
            
        Returns:
            格式化后的字符串
        """
        fmt = output_format.lower().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            raise SOPError("E004", f"不支持的输出格式: {output_format}")
        
        if fmt == "json":
            return self._format_json(data)
        elif fmt in ("markdown", "md"):
            return self._format_markdown(data)
        else:
            return self._format_text(data)
    
    def _format_json(self, data: Dict[str, Any]) -> str:
        """JSON格式输出"""
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def _format_markdown(self, data: Dict[str, Any]) -> str:
        """Markdown格式输出"""
        lines = []
        
        # 标题
        title = data.get("title") or "标准作业程序"
        lines.append(f"# {title}")
        lines.append("")
        
        # 元信息
        lines.append("## 基本信息")
        lines.append("")
        lines.append(f"- **责任人**: {data.get('owner') or '未指定'}")
        lines.append(f"- **完成时限**: {data.get('deadline') or '未指定'}")
        lines.append(f"- **置信度**: {data.get('confidence', 0):.0%}")
        lines.append(f"- **步骤数**: {len(data.get('steps', []))}")
        lines.append("")
        
        # 步骤
        lines.append("## 操作步骤")
        lines.append("")
        for i, step in enumerate(data.get("steps", []), 1):
            lines.append(f"### 步骤 {i}")
