---
slug: seoarticlegenai
name: seoarticlegenai
displayName: SEO文章批量生成 数据驱动 内容优化
description: 将数据与URL转化为结构化搜索优化内容，辅助SEO文章批量生成。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["SEO文案", "SEO文章生成", "搜索优化写作", "关键词内容创作", "seoarticlegenai", "批量内容生产", "搜索引擎排名优化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SEO 文章批量生成 Skill 使用指南

## 一、能力边界速查卡

本 Skill 用于将结构化数据（CSV/JSON/TXT）与目标 URL 结合，批量生成符合搜索引擎优化要求的文章草稿。它解决的是"从数据到初稿"的转化问题，不替代人工编辑与策略制定。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入格式 | `.csv`、`.json`、`.txt` 文件 | 图片、PDF、扫描件 |
| 输出格式 | Markdown（`.md`）文件 | Word、PDF 直接输出 |
| 处理规模 | 单文件或整个目录批量处理 | 实时抓取网页内容 |
| 内容深度 | 基于给定字段生成结构化初稿 | 独立完成深度调研与事实核查 |
| 关键词处理 | 根据输入字段嵌入关键词 | 自动挖掘新关键词 |
| 语言支持 | 中文为主，兼容英文 | 其他语种需自行测试 |

**适用对象**：内容运营人员、SEO 专员、网站编辑、自由撰稿人。需要每天产出大量结构化文章初稿的场景。

---

## 二、触发方式与场景映射

当你的需求符合以下任一场景时，可使用本 Skill：

| 大白话描述 | 触发词示例 | 是否适用 |
|------------|------------|----------|
| "帮我把产品数据变成文章" | SEO文章生成 | ✅ 适用 |
| "这批关键词要写成带排版的稿子" | 关键词内容创作 | ✅ 适用 |
| "我有一堆链接和描述，想变成博客" | 搜索优化写作 | ✅ 适用 |
| "能不能自动写 100 篇 SEO 文？" | 批量内容生产 | ✅ 适用（需分批执行） |
| "帮我查一下文章排名" | — | ❌ 不适用（无排名查询功能） |

---

## 三、标准操作流程

### 前置条件

1. 所有待处理数据文件（`.csv`、`.json`、`.txt`）存放在同一目录下。
2. 每个文件至少包含以下字段之一：标题、关键词、描述、URL、正文要点。
3. 确认文件编码为 UTF-8（避免中文乱码）。
4. 建议单文件不超过 500 条记录，超过请拆分。

### 执行步骤

#### 第一步：单文件试运行

```bash
seoarticlegenai --input sample.csv --output sample_output.md
```

**参数说明**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--input` | 是 | 输入文件路径或目录路径 |
| `--output` | 是 | 输出文件路径或目录路径 |
| `--selftest` | 否 | 运行自检程序 |
| `--version` | 否 | 显示版本号 |

#### 第二步：检查输出文件

打开生成的 `.md` 文件，核对以下内容：

- [ ] 标题是否从数据中正确提取
- [ ] 关键词是否嵌入正文（建议每 300 字出现 1-2 次）
- [ ] URL 是否完整且无乱码
- [ ] 字段顺序是否与源数据一致
- [ ] 是否有明显错位或缺失

#### 第三步：备份原始数据

批量执行前，将原始数据目录复制一份备份：

```bash
cp -r ./data_folder/ ./data_backup_20250101/
```

> 备份命名格式：`data_backup_YYYYMMDD`

#### 第四步：批量执行

```bash
seoarticlegenai --input ./data_folder/ --output ./output_folder/
```

**注意**：批量执行时，输出目录会自动创建。若输出目录已存在同名文件，默认覆盖（请提前确认）。

#### 第五步：抽样质检

随机抽取 3-5 个输出文件，核对：

1. 标题与正文逻辑是否连贯
2. 关键词密度是否合理（建议 1%-3%）
3. 是否有数据截断或编码错误
4. 链接是否可读、格式正确

#### 第六步：人工修订

机器生成的初稿需人工调整：

- 补充行业术语和案例
- 优化段落过渡
- 检查事实准确性
- 调整语气风格

---

## 四、置信度门控机制

当输入数据存在以下情况时，输出中会以 `[需核实:字段名]` 占位，**不会**编造内容：

| 情况 | 输出表现 | 处理建议 |
|------|----------|----------|
| 缺少标题字段 | `[需核实:标题]` | 补充数据后重跑 |
| URL 格式异常 | `[需核实:URL]` | 检查源数据格式 |
| 关键词为空 | `[需核实:关键词]` | 手动补充关键词 |
| 描述字段超长 | 截断至 200 字并标记 | 调整源数据长度 |

**原则**：宁可留白，不可虚构。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定文件，请检查路径" | 确认路径是否正确 |
| `E002` | 文件格式不支持 | "仅支持 .csv/.json/.txt 格式" | 转换文件格式 |
| `E003` | 编码错误 | "文件编码异常，请转为 UTF-8" | 用文本编辑器转码 |
| `E004` | 字段缺失 | "缺少必要字段：标题/关键词" | 检查数据完整性 |
| `E005` | 输出目录无权限 | "无法写入输出目录" | 修改目录权限 |
| `E006` | 数据量超限 | "单文件超过 500 条，请拆分" | 拆分文件后重试 |

---

## 六、常见坑与反模式对照

| 常见错误做法 | 问题 | 推荐做法 |
|--------------|------|----------|
| 不备份直接批量跑 | 数据损坏无法恢复 | 先备份再执行 |
| 跳过试运行直接全量 | 格式错误被放大 | 先跑一个文件验证 |
| 完全信任机器输出 | 事实错误、逻辑混乱 | 人工抽检 + 修订 |
| 关键词堆砌 | 被搜索引擎判定作弊 | 保持自然密度 1%-3% |
| 忽略字段顺序 | 输出错位 | 核对源数据表头 |

---

## 七、分层次阅读路径

### 新手快速上手（5 分钟）

1. 阅读「能力边界速查卡」确认适用场景
2. 按「标准操作流程」第一步执行单文件试运行
3. 检查输出文件格式
4. 确认无误后备份 → 批量执行

### 进阶用户（深度使用）

1. 熟悉「错误码体系」快速排障
2. 理解「置信度门控」机制，善用占位符
3. 结合「常见坑」优化数据预处理
4. 建立自己的质检清单（建议包含：标题吸引力、关键词密度、段落结构、链接有效性）

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。包括但不限于因内容错误、遗漏或不合规导致的任何损失。
2. **禁止反向工程**：不得对本 Skill 的底层代码、算法或逻辑进行反向工程、反编译或试图提取源代码。
3. **内容合规**：使用者需确保输入数据与输出内容符合当地法律法规及平台政策。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 林墨

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
