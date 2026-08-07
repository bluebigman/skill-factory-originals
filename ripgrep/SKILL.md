---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ripgrep
name: ripgrep
displayName: 代码库快速检索 正则匹配 文件扫描
description: 基于正则的极速代码搜索工具，自动遵循忽略规则，秒级定位目标内容。
version: 1.7.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ripgrep
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingSearch
agent_created: true
trigger_words: ["ripgrep", "rg", "代码搜索", "正则搜索", "文件内容查找", "快速检索", "文本定位"]
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

# ripgrep 技能手册

## 一、能力边界（速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 正则模式搜索 | 支持 PCRE2 语法，可匹配复杂文本结构 | `rg "fn\s+\w+"` 查找函数定义 |
| 智能忽略机制 | 自动读取 `.gitignore`、`.ignore`、`.rgignore`，跳过隐藏文件和二进制文件 | 无需额外参数，默认生效 |
| 文件类型过滤 | 按扩展名或类型名限定搜索范围 | `-t py` 仅搜 Python；`-T js` 排除 JS |
| 上下文输出 | 显示匹配行附近的代码，便于理解语境 | `-C 3` 前后各 3 行；`-A 2` 后 2 行 |
| 统计计数 | 统计每个文件的匹配行数或总匹配次数 | `-c` 按文件计数；`--count-matches` 总次数 |
| 文件列表输出 | 仅输出文件名，或反向输出不含匹配的文件 | `-l` 含匹配文件；`-L` 不含匹配文件 |
| 多路径搜索 | 同时指定多个目录进行搜索 | `rg pattern dir1 dir2` |
| 替换预览 | 预览替换效果但不实际写入文件 | `--replace` + `--passthru` |
| 编码指定 | 指定文件编码，解决乱码问题 | `-E gbk` 按 GBK 编码读取 |
| JSON 输出 | 结构化输出，便于程序解析 | `--json` |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不修改文件 | 仅搜索和预览，不执行写入操作 |
| 不支持模糊搜索 | 必须提供正则表达式或字面字符串 |
| 不索引内容 | 每次搜索实时扫描，非预建索引 |
| 不搜索压缩包 | 不自动解压 zip/tar 等归档文件 |
| 不跨文件系统 | 默认不跨越挂载点（可用 `--one-file-system` 控制） |

### 适用对象

- 开发者在大型代码库中定位函数、变量、日志输出
- 运维人员快速查找配置文件中的关键参数
- 数据分析师在文本数据集中提取符合模式的行
- 任何需要在文件系统中按内容找文件的场景


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
