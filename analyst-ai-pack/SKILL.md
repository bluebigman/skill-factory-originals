---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: analyst-ai-pack
name: analyst-ai-pack
displayName: 恶意样本分析 威胁狩猎 逆向工程
description: 面向恶意软件分析、逆向工程与威胁狩猎的开源技能库，提供118个可运行技能。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/analyst-ai-pack
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForgeLab
agent_created: true
trigger_words: ["恶意软件分析", "逆向工程", "威胁狩猎", "样本分析", "病毒分析", "malware analysis", "reverse engineering", "threat hunting"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# analyst-ai-pack 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 样本文件解析 | 对PE/ELF/Mach-O等格式进行静态结构解析 | `sample.exe` | 文件头信息、节区表、导入导出表 |
| 2 | 威胁指标提取 | 从样本中提取IOC（IP、域名、哈希、互斥量） | 恶意文档 | 结构化IOC列表（JSON/CSV） |
| 3 | 行为特征分析 | 解析沙箱报告或动态跟踪日志 | `report.json` | 行为摘要、ATT&CK技术映射 |
| 4 | 逆向辅助 | 反汇编/反编译结果的关键函数定位 | `idb`/`asm`文件 | 可疑函数清单及调用关系 |
| 5 | 批量威胁狩猎 | 对多个样本或日志进行批量匹配与聚类 | 样本目录/日志文件 | 聚类结果、相似度评分 |

### 1.2 能力边界声明

**能做：**
- 处理用户提供的本地文件、目录路径、URL链接
- 识别并保留输入中的关键上下文信息（文件名、哈希、时间戳等）
- 按用户指定的格式（JSON/YAML/CSV/纯文本）输出结构化结果
- 对分析结果中的不确定项标注置信度
- 支持批量输入与自定义输出模板

**不能做：**
- 无法执行动态沙箱运行（需外部沙箱环境配合）
- 不提供样本修复或清除服务
- 不保证检测率或查杀效果（检测率受规则库和引擎限制）
- 不替代人工研判，最终结论需分析师确认
- 不处理加密样本（需用户先解密）

### 1.3 适用对象

| 角色 | 适用场景 | 使用方式 |
|------|----------|----------|
| 安全分析师 | 日常样本初筛、IOC提取 | CLI命令或API调用 |
| 逆向工程师 | 恶意代码逻辑梳理 | 辅助反汇编分析 |
| 威胁情报研究员 | 批量样本聚类、家族识别 | 批量模式 |
| 蓝队/应急响应 | 入侵指标匹配、日志狩猎 | 日志导入分析 |


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->
