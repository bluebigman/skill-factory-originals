#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会议纪要解析与行动项提取工具"""

import re
import sys
from datetime import datetime
from typing import Dict, List, Optional


class MeetingParser:
    """会议纪要解析器"""

    def __init__(self):
        self.actions = []
        self.participants = []
        self.summary = ""
        self.meeting_date = None

    def parse(self, text: str) -> Dict:
        """解析会议纪要文本"""
        if not text or not text.strip():
            raise ValueError("会议纪要文本不能为空")

        # 解析日期
        self._parse_date(text)

        # 解析参与人
        self._parse_participants(text)

        # 解析行动项
        self._parse_actions(text)

        # 生成摘要
        self._generate_summary(text)

        return {
            "date": self.meeting_date,
            "participants": self.participants,
            "actions": self.actions,
            "summary": self.summary
        }

    def _parse_date(self, text: str):
        """解析会议日期"""
        date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    if '年' in date_str:
                        parts = re.findall(r'\d+', date_str)
                        self.meeting_date = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                    else:
                        self.meeting_date = datetime.strptime(date_str, '%Y-%m-%d' if '-' in date_str else '%Y/%m/%d')
                    return
                except (ValueError, IndexError):
                    continue
        self.meeting_date = datetime.now()

    def _parse_participants(self, text: str):
        """解析参与人"""
        # 查找参与人相关行
        participant_patterns = [
            r'[参出]席[人者][：:]\s*(.+)',
            r'参与[人者][：:]\s*(.+)',
            r'参会[人者][：:]\s*(.+)'
        ]
        for pattern in participant_patterns:
            match = re.search(pattern, text)
            if match:
                names = re.split(r'[,，、\s]+', match.group(1).strip())
                self.participants = [name for name in names if name]
                return
        self.participants = []

    def _parse_actions(self, text: str):
        """解析行动项"""
        self.actions = []
        lines = text.split('\n')
        current_action = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配行动项开始（支持中英文标点）
            action_match = re.match(
                r'^[（(]?\s*行动项\s*[)）]?\s*[：:]\s*(.+)$',
                line
            ) or re.match(
                r'^[-*•]\s*(?:行动项|任务|待办)[：:]\s*(.+)$',
                line
            ) or re.match(
                r'^(\d+)[、.．]\s*(?:行动项|任务|待办)[：:]\s*(.+)$',
                line
            )

            if action_match:
                # 保存前一个行动项
                if current_action:
                    self.actions.append(current_action)

                # 开始新的行动项
                content = action_match.group(1) if action_match.lastindex == 1 else action_match.group(action_match.lastindex)
                current_action = {
                    'content': content.strip(),
                    'owner': None,
                    'deadline': None
                }
                continue

            # 如果当前在行动项中，尝试提取负责人和截止日期
            if current_action:
                # 提取负责人
                owner_match = re.search(r'[负责]责人[：:]\s*([^\s,，;；]+)', line)
                if owner_match:
                    current_action['owner'] = owner_match.group(1).strip()

                # 提取截止日期
                deadline_match = re.search(r'(?:截止|完成)[日期时间][：:]\s*([^\s,，;；]+)', line)
                if deadline_match:
                    current_action['deadline'] = deadline_match.group(1).strip()
                elif re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?', line):
                    date_match = re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?', line)
                    if date_match:
                        current_action['deadline'] = date_match.group(0)

        # 添加最后一个行动项
        if current_action:
            self.actions.append(current_action)

    def _generate_summary(self, text: str):
        """生成会议摘要"""
        # 提取关键信息
        sentences = re.split(r'[。！？!?]', text)
        key_points = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # 保留包含关键词的句子
            if any(keyword in sentence for keyword in ['决定', '确认', '同意', '通过', '安排', '计划', '目标', '重点']):
                key_points.append(sentence)

        if key_points:
            self.summary = '；'.join(key_points[:3])
        else:
            # 如果没有关键词句子，取前几个非空句子
            non_empty = [s for s in sentences if s.strip()]
            self.summary = '；'.join(non_empty[:3]) if non_empty else text[:100]


def run_selftest():
    """运行自检"""
    parser = MeetingParser()

    # 测试1：正常文本解析
    test_text = """
    2024年1月15日 项目周会

    参会人：张三、李四、王五

    会议内容：
    1. 项目进度确认，整体进展顺利
    2. 讨论技术方案，决定采用微服务架构
    3. 确认下阶段重点任务

    行动项：
    1. 行动项：完成接口文档编写
       负责人：张三
       截止日期：2024年1月20日

    2. 行动项：搭建测试环境
       负责人：李四
       截止日期：2024年1月18日

    3. 行动项：准备项目汇报材料
       负责人：王五
       截止日期：2024年1月22日
    """
    result = parser.parse(test_text)
    assert result['date'] is not None, "日期解析失败"
    assert len(result['participants']) >= 3, "参与人解析失败"
    assert len(result['actions']) >= 3, "行动项解析失败"
    assert len(result['summary']) > 0, "摘要生成失败"

    # 测试2：中文标点文本
    chinese_text = """
    2024年2月1日 产品评审会

    参会人：赵六、钱七、孙八

    会议内容：
    讨论了新功能需求，确认了产品方向，安排了开发计划。

    行动项：
    1. 行动项：完成需求文档
       负责人：赵六
       截止日期：2024年2月5日

    2. 行动项：设计原型图
       负责人：钱七
       截止日期：2024年2月8日
    """
    result2 = parser.parse(chinese_text)
    assert len(result2['actions']) >= 2, "中文标点文本行动项解析失败"

    # 测试3：空输入
    try:
        parser.parse("")
        assert False, "空输入应该抛出异常"
    except ValueError:
        pass

    print("[通过] 正常文本解析")
    print("[通过] 中文标点文本解析")
    print("[通过] 空输入正确抛出异常")
    return True


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常模式：从stdin读取文本
    text = sys.stdin.read() if not sys.stdin.isatty() else None
    if not text:
        print("请通过stdin输入会议纪要文本", file=sys.stderr)
        sys.exit(1)

    parser = MeetingParser()
    try:
        result = parser.parse(text)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except ValueError as e:
        print(f"解析错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
