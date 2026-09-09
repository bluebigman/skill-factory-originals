#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wb-publish-guide: 诊断 WorkBuddy 开放平台上传/驳回问题, 输出修复建议"""
import argparse
import os
import re
import sys

REF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'references', 'publish_guide.md')

def load_guide():
    """读知识库, 按章节拆分"""
    if not os.path.isfile(REF_FILE):
        return {}
    txt = open(REF_FILE, encoding='utf-8', errors='ignore').read()
    sections = {}
    cur = 'HEAD'
    for line in txt.split('\n'):
        m = re.match(r'^#{2,3}\s+(.+)$', line)
        if m:
            cur = m.group(1).strip()
            sections.setdefault(cur, [])
        else:
            sections.setdefault(cur, []).append(line)
    return {k: '\n'.join(v).strip() for k, v in sections.items() if '\n'.join(v).strip()}

def diagnose(text):
    """按症状关键词分诊, 返回匹配的修复段"""
    text_l = text.lower()
    results = []
    # A 解析类
    if any(k in text_l for k in ['parse_fail', '解析失败', '上传失败', '无法解析']):
        results.append(('A_解析类', '常见根因: zip 结构不符契约/缺 selftest.py/name 与目录不一致/JSON 错误。修复: 对照 15 项清单检查 zip 内部结构; 技能必含 SKILL.md+config.json+run.py+selftest.py+scripts/main.py; frontmatter name==目录名; 确认 UTF-8 无 BOM 问题。'))
    # B 审核类
    if any(k in text_l for k in ['归属', '无明确归属', '主体']):
        results.append(('B_归属驳回', '根因: author 字段≠发布账号 ID(用了虚构名/团队名)。修复: plugin.json/SKILL.md 的 author 填你的平台账号 ID=真实归属。'))
    if any(k in text_l for k in ['类目', 'category']):
        results.append(('B_类目驳回', '根因: 类目与功能不匹配。修复: 按功能对位(计算器选 工具>计算器); 不确定时选最贴近的大类。'))
    if any(k in text_l for k in ['质量', '沙箱', '评测', '低质量', 'not pass']):
        results.append(('B_质量驳回', '根因: 沙箱评测未达标(功能不可用/空转/报错)。修复: 本地充分测试含无素材场景(无素材时给演示样例不反问); 修完重提。'))
    # C 限流类
    if any(k in text_l for k in ['次数过多', 'rate', 'limit', '限流', '频繁']):
        results.append(('C_限流', '根因: 24h 滚动提交限流。修复: 当天停手不再试(硬试延长窗口); 次日再提交; 提交间隔 ≥15s 串行。'))
    # D 展示类
    if any(k in text_l for k in ['搜不到', 'displayname', '中文名', '名称']):
        results.append(('D_搜索', '根因: displayName 非功能词。修复: 用 6-12 字中文功能名含搜索场景词(如"XX生成器/XX工具"); README 写真实描述禁 TODO 占位。'))
    return results

def checklist():
    """输出 15 项自检清单"""
    return [
        '1. zip 顶层目录名 == slug (英文 kebab-case)',
        '2. 技能含 SKILL.md/config.json/run.py/selftest.py/scripts/main.py',
        '3. SKILL.md frontmatter 完整 (name/display_name/description/version/author)',
        '4. 无重复文件/.bak/.DS_Store',
        '5. author == 你的平台账号 ID (非虚构品牌名)',
        '6. plugin/agent 层 description = 英文',
        '7. displayDescription.zh 40-60 字',
        '8. displayName = 6-12 字中文功能名 (含搜索词)',
        '9. 类目与功能对位',
        '10. README 无 [TODO:] 占位',
        '11. 涉专业领域含免责声明',
        '12. 含 AI 生成标识',
        '13. 无黑名单敏感词',
        '14. selftest.py 可运行全绿 (8/8)',
        '15. agent 提示词含鲁棒性规则 (无素材自驱/多轮纪律/输入分类/数字纪律)',
    ]

def main():
    p = argparse.ArgumentParser(description='WB 上架避坑: 诊断上传/驳回问题')
    p.add_argument('--diagnose', '-d', help='粘贴报错文案/现象进行分诊')
    p.add_argument('--checklist', '-c', action='store_true', help='输出提交前 15 项自检清单')
    p.add_argument('--guide', '-g', action='store_true', help='输出完整知识库')
    args = p.parse_args()
    if args.checklist:
        for item in checklist():
            print(item)
        return 0
    if args.diagnose:
        hits = diagnose(args.diagnose)
        if hits:
            for cat, fix in hits:
                print(f'[{cat}] {fix}')
        else:
            print('未匹配到已知症状, 请提供: 1)完整报错文案 2)资产类型(技能/专家/连接器) 3)zip 结构')
        return 0
    if args.guide:
        secs = load_guide()
        for k, v in secs.items():
            print(f'## {k}\n{v[:500]}')
        return 0
    p.print_help()
    return 0

if __name__ == '__main__':
    sys.exit(main())
