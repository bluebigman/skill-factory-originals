---
slug: book-to-skill
name: book-to-skill
displayName: 技术书转技能 场景封装 边学边用
description: 将技术书籍PDF转化为可操作的Claude Code技能，边学边用。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["book-to-skill", "技术书转技能", "书籍转技能", "PDF转技能", "技能封装", "书本变技能", "教材转工作流"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 技术书转技能（book-to-skill）

## 一、能力边界（一页纸速查卡）

### 能做

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| PDF 文本提取 | 从文字型 PDF 中抽取章节、段落、代码块 | 有电子版技术书的读者 |
| 技能包骨架生成 | 按 Claude Code Skill 规范生成目录结构与 SKILL.md | 想将书本知识落地为可复用工具 |
| 场景化指令编排 | 将书中操作步骤改写为可执行的指令序列 | 运维手册、框架教程、算法导论 |
| 置信度标注 | 对不确定内容自动插入 `[需核实:字段]` 占位 | 扫描版 PDF、缺页、公式乱码 |
| 验证报告输出 | 生成 `verification-report.md` 记录提取质量 | 需要质检或团队评审时 |

### 不能做

| 限制项 | 说明 |
|--------|------|
| 扫描版/图片型 PDF | 无 OCR 能力，需先自行转成文字版 |
| 版权内容商用 | 提取内容仅限个人学习与研究，禁止商业传播 |
| 自动执行书内代码 | 不负责运行或调试书中的程序，仅做指令编排 |
| 跨书知识融合 | 单次只处理一本书，多书合并需手动干预 |

### 适用对象

- 正在读技术书、想边读边沉淀技能的开发者
- 需要将内部知识手册转为团队可用 Skill 的技术负责人
- 希望把教材内容封装为可重复调用工作流的个人用户

---

## 二、触发方式

### 触发词

`book-to-skill`、`技术书转技能`、`书籍转技能`、`PDF转技能`、`技能封装`、`书本变技能`、`教材转工作流`

### 大白话场景映射表

| 你说的话（口语） | 实际含义 | 本 Skill 会做什么 |
|------------------|----------|-------------------|
| "帮我把这本《Python 网络爬虫》变成能用的技能" | 提取书中爬虫章节，封装为可复用指令 | 解析 PDF → 抽取爬虫相关章节 → 生成技能包 |
| "这本 Docker 手册我想转成团队能用的操作指南" | 将手册步骤转为标准化操作流程 | 提取操作步骤 → 编排为指令序列 → 输出技能包 |
| "这本书内容太多，我只想要里面的算法部分" | 按主题筛选内容 | 按关键词/章节过滤 → 只封装指定部分 |
| "这本书扫描版，字看不清" | 无法直接提取文字 | 提示先做 OCR，给出替代方案 |

---

## 三、标准流程

### 前置条件

| 条件 | 检查方法 | 不满足时的处理 |
|------|----------|----------------|
| PDF 为文字型（非扫描） | 用阅读器打开，尝试选中文字 | 先运行 OCR 工具（如 Tesseract）转成文字版 |
| 已安装 Claude Code 环境 | 终端执行 `claude --version` | 先安装 Claude Code |
| 有明确的使用场景 | 想清楚"这本书解决什么问题" | 先写一句话场景描述，再开始 |

### 执行步骤

1. **准备 PDF 文件**
   - 将 PDF 放在工作目录下，路径中不要有空格或中文（避免解析异常）
   - 确认文件可读：`ls -lh <文件>`

2. **运行转换命令**
   ```bash
   book-to-skill --pdf <文件路径> --scene <场景描述>
   ```
   参数说明：

   | 参数 | 必填 | 说明 | 示例 |
   |------|------|------|------|
   | `--pdf` | 是 | PDF 文件路径 | `./books/python-crawler.pdf` |
   | `--scene` | 是 | 一句话描述使用场景 | `"爬取电商网站商品信息"` |
   | `--output` | 否 | 输出目录，默认 `./output/` | `--output ./my-skill/` |
   | `--lang` | 否 | 输出语言，默认 `zh-CN` | `--lang en-US` |
   | `--selftest` | 否 | 自检模式，检查环境依赖 | 无参数值 |
   | `--version` | 否 | 显示版本号 | 无参数值 |

3. **查看输出目录**
   ```bash
   tree output/
   ```
   预期结构：
   ```
   output/
   ├── SKILL.md          # 技能主文档
   ├── references/       # 书中提取的参考片段
   ├── scripts/          # 可执行脚本（如有）
   └── verification-report.md  # 提取质量报告
   ```

4. **复制到 skills 目录**
   ```bash
   cp -r output/ ~/.claude/skills/<技能名>/
   ```

5. **对话中激活**
   在 Claude Code 对话中直接说"技术书转技能"或使用你定义的触发词，即可调用该技能。

### 输出规范

- `SKILL.md` 必须包含：能力边界、触发方式、标准流程、置信度门控、错误码体系、FAQ 反模式
- `verification-report.md` 必须记录：提取章节数、置信度低于阈值的条目、缺失页码
- 所有代码片段保留原始语言，不擅自改写

---

## 四、置信度门控

### 规则说明

当提取内容存在以下情况时，**不得编造**，必须插入占位符：

| 情况 | 占位符格式 | 示例 |
|------|------------|------|
| 文字模糊/乱码 | `[需核实:原文]` | `[需核实:原文] 该函数的返回类型` |
| 图表无法解析 | `[需核实:图表]` | `[需核实:图表] 图3-2 架构流程图` |
| 公式识别失败 | `[需核实:公式]` | `[需核实:公式] 损失函数定义` |
| 章节缺失 | `[需核实:页码]` | `[需核实:页码] 第 87-89 页内容缺失` |
| 代码缩进丢失 | `[需核实:缩进]` | `[需核实:缩进] 第 4 行 for 循环体` |

### 门控阈值

- 单页置信度 < 60%：整页标记为 `[需核实:整页]`，不进入技能包
- 单段置信度 < 70%：段落标记占位符，保留但置于 `references/` 待人工确认
- 单句置信度 < 80%：句子标记占位符，技能包中保留但加注释

### 处理流程

1. 提取时自动计算置信度
2. 低于阈值的自动插入占位符
3. 生成 `verification-report.md` 列出所有占位符位置
4. 用户可手动替换占位符为正确内容，或删除该片段

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | PDF 文件不存在 | "未找到指定文件，请检查路径" | 1. 确认文件路径 2. 用 `ls` 验证 3. 重新运行 |
| `E002` | PDF 为扫描版 | "检测到无文字层，请先 OCR" | 1. 运行 OCR 工具 2. 生成文字版 PDF 3. 重新运行 |
| `E003` | 场景描述为空 | "请提供使用场景，一句话即可" | 1. 用 `--scene` 参数补充 2. 重新运行 |
| `E004` | 提取内容为空 | "未提取到有效内容，可能文件损坏" | 1. 用阅读器打开验证 2. 换其他 PDF 工具导出 3. 重新运行 |
| `E005` | 输出目录无权限 | "无法写入输出目录" | 1. 检查目录权限 2. 换 `--output` 指定可写目录 |
| `E006` | 置信度过低 | "提取质量低于阈值，建议人工处理" | 1. 查看 `verification-report.md` 2. 手动补充关键内容 3. 重新生成 |
| `E007` | 依赖缺失 | "缺少必要依赖，请先安装" | 1. 查看错误详情 2. 安装对应依赖 3. 运行 `--selftest` 验证 |

---

## 六、FAQ 反模式

### 常见坑 1：拿扫描版硬转

- **错误做法**：直接对扫描版 PDF 运行转换，得到大量乱码
- **正确姿势**：先 OCR 转文字版，再运行转换
- **反模式对照**：扫描版 → 乱码 → 浪费时间；扫描版 → OCR → 文字版 → 正常提取

### 常见坑 2：场景描述太模糊

- **错误做法**：`--scene "这本书"`，结果提取内容发散
- **正确姿势**：`--scene "用 Python 实现电商网站商品价格监控"`，提取内容聚焦
- **反模式对照**：模糊场景 → 技能包内容杂乱；明确场景 → 技能包精准可用

### 常见坑 3：忽略置信度报告

- **错误做法**：生成后不看 `verification-report.md` 直接使用
- **正确姿势**：先检查报告，确认所有占位符位置，决定保留或删除
- **反模式对照**：忽略报告 → 技能包含错误内容；检查报告 → 技能包质量可控

### 常见坑 4：一次处理整本书

- **错误做法**：把 500 页的书全部提取，生成超大技能包
- **正确姿势**：按章节或主题分批处理，每个技能包聚焦一个场景
- **反模式对照**：整本提取 → 技能包臃肿难用；分场景提取 → 技能包轻量高效

### 常见坑 5：不验证生成结果

- **错误做法**：生成后不测试，直接复制到 skills 目录
- **正确姿势**：先在对话中试运行一次，确认指令可执行
- **反模式对照**：不测试 → 上线后报错；先测试 → 使用顺畅

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 确认 PDF 是文字版
2. 运行：book-to-skill --pdf 文件.pdf --scene "场景描述"
3. 查看 output/ 目录
4. 复制到 skills 目录
5. 对话中触发词激活
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解工具限制
2. 按「标准流程」逐步操作
3. 遇到问题查「错误码体系」
4. 生成后查看 `verification-report.md`

### 进阶路径（熟练用户）

1. 掌握「置信度门控」规则，处理不确定内容
2. 尝试多本书合并为一个综合技能包
3. 自定义输出格式，适配团队规范
4. 将技能包分享给团队，收集反馈并迭代优化
5. 结合「错误码体系」，建立自动化校验流程

---

## 用户协议

**使用本 Skill 即视为同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的输出结果仅供参考，不构成任何形式的保证或承诺。因使用本 Skill 导致的任何直接或间接损失，Skill 作者不承担任何责任。

2. **使用限制**：本 Skill 生成的技能包仅限个人学习、研究或内部使用。未经版权方许可，不得将提取内容用于商业用途或公开传播。

3. **禁止反向工程**：使用者不得对本 Skill 的代码、算法、内部逻辑进行反向工程、反编译或破解，不得移除或篡改任何版权标识。

4. **内容合规**：使用者应确保输入的 PDF 文件来源合法，不侵犯他人知识产权。因输入内容引发的版权纠纷，由使用者自行承担。

5. **协议更新**：本协议可能随时更新，更新后的协议将在本 Skill 文档中发布。继续使用本 Skill 即视为接受更新后的协议。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

<!-- professional-license-embedded -->
