---
slug: karpathy-llm-wiki
name: karpathy-llm-wiki
displayName: 资料整理 知识库构建 结构化解析
description: 将原始资料自动解析为结构化知识库，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知识工坊
agent_created: true
trigger_words: ["知识库构建", "结构化解析", "wiki生成", "资料整理", "文档转换", "批量处理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# karpathy-llm-wiki — 资料整理与知识库构建工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单文件解析 | 将单个 Markdown 文件转换为结构化 JSON | `--input note.md --output note.json` |
| 批量处理 | 处理整个目录下的所有 .md 文件 | `--batch --input ./docs/ --output ./output/` |
| 置信度标注 | 对解析结果中的每个字段标注可信程度 | `"content": {"value": "...", "confidence": 0.92}` |
| 标签生成 | 自动提取关键词作为文档标签 | 输入文章自动生成 3-5 个标签 |
| 结果校验 | 检查输出 JSON 的完整性与格式合规性 | `--verify --input output.json` |
| 阈值门控 | 过滤低置信度的解析结果 | `--threshold 0.8` 仅保留置信度 ≥0.8 的字段 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持 PDF/Word | 仅接受纯文本 Markdown（.md）格式输入 |
| 不做语义理解 | 仅做结构化提取，不进行内容摘要或语义分析 |
| 不保证标签准确 | 自动标签基于词频统计，可能偏离主题 |
| 不处理图片 | 图片链接保留原样，不进行 OCR 或图像识别 |
| 不联网 | 所有处理均在本地完成，不调用外部 API |

### 1.3 适用对象

- 需要将零散笔记整理为知识库的个人用户
- 需要批量转换文档格式的团队协作场景
- 希望建立可检索、可追溯的资料管理体系的内容创作者

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 将被激活：

| 触发词 | 场景示例 |
|--------|----------|
| 知识库构建 | "帮我把这些笔记整理成知识库" |
| 结构化解析 | "把这个文档转成 JSON 格式" |
| wiki生成 | "生成一个 wiki 页面" |
| 资料整理 | "整理一下我的学习资料" |
| 文档转换 | "把 Markdown 转成结构化数据" |
| 批量处理 | "处理这个文件夹里的所有文件" |

### 2.2 场景映射表

| 用户需求（大白话） | 对应操作 |
|-------------------|----------|
| "我有一堆笔记想整理" | 使用 `--batch` 批量处理目录 |
| "这个文档帮我转成 JSON" | 使用 `--input` 单文件解析 |
| "帮我检查一下转换结果" | 使用 `--verify` 校验输出 |
| "有些内容我不确定准不准" | 查看置信度字段，使用 `--threshold` 过滤 |
| "标签不太对，我想自己定" | 使用 `--tags` 手动指定标签 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|----------|
| 输入文件格式 | 必须是 .md 文件 | 文件扩展名检查 |
| 文件编码 | UTF-8 无 BOM | 文本编辑器查看 |
| 目录权限 | 输入目录可读，输出目录可写 | 操作系统权限检查 |
| 磁盘空间 | 至少 2 倍于输入文件大小 | `df -h` 查看 |

### 3.2 执行步骤

#### 步骤 1：单样本试运行

```bash
# 创建测试文件
echo "# 测试标题" > test.md
echo "这是一段测试内容。" >> test.md

# 执行单文件解析
karpathy llm wiki --input test.md --output test.json
```

#### 步骤 2：检查输出结构

```bash
# 查看输出文件
cat test.json
```

预期输出结构：

```json
{
  "title": "测试标题",
  "tags": ["测试", "内容"],
  "content": "这是一段测试内容。",
  "source": "test.md",
  "confidence": {
    "title": 0.95,
    "tags": 0.78,
    "content": 0.99
  }
}
```

#### 步骤 3：处理真实文件

```bash
# 处理单个真实文件
karpathy llm wiki --input real-note.md --output real-note.json

# 批量处理整个目录
karpathy llm wiki --batch --input ./notes/ --output ./output/

# 指定置信度阈值
karpathy llm wiki --batch --input ./notes/ --output ./output/ --threshold 0.8

# 手动指定标签
karpathy llm wiki --input note.md --output note.json --tags "AI,编程,教程"
```

#### 步骤 4：校验结果

```bash
# 校验单个输出文件
karpathy llm wiki --verify --input output.json

# 校验整个输出目录
karpathy llm wiki --verify --batch --input ./output/
```

### 3.3 输出规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 文档标题，取自第一个一级标题 |
| `tags` | array | 是 | 自动提取的标签，3-5 个 |
| `content` | string | 是 | 文档正文内容（去除标题） |
| `source` | string | 是 | 原始文件名 |
| `confidence` | object | 是 | 各字段的置信度评分（0-1） |

---

## 四、置信度门控

### 4.1 置信度评分标准

| 置信度区间 | 含义 | 处理方式 |
|-----------|------|----------|
| 0.9 - 1.0 | 高置信度，字段提取准确 | 直接使用 |
| 0.7 - 0.9 | 中置信度，可能存在偏差 | 建议人工复核 |
| 0.5 - 0.7 | 低置信度，提取结果不可靠 | 需要人工修正 |
| < 0.5 | 极低置信度，提取失败 | 输出 `[需核实:字段名]` 占位 |

### 4.2 占位符规则

当信息不足或提取失败时，使用以下格式输出占位符：

```
[需核实:title]
[需核实:tags]
[需核实:content]
```

占位符不会被计入最终统计，但会在校验报告中标记为"待处理"。

### 4.3 阈值调节

```bash
# 设置阈值为 0.85，低于此值的字段将被替换为占位符
karpathy llm wiki --input note.md --output note.json --threshold 0.85

# 关闭阈值过滤（默认行为）
karpathy llm wiki --input note.md --output note.json --threshold 0
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文件不存在 | "错误：找不到指定的输入文件" | 检查文件路径是否正确 |
| E002 | 输入文件不是 .md 格式 | "错误：仅支持 Markdown 文件" | 转换文件格式后重试 |
| E003 | 输出目录不可写 | "错误：无法写入输出目录" | 检查目录权限或更换路径 |
| E004 | 文件编码不支持 | "错误：文件编码必须为 UTF-8" | 使用文本编辑器转换编码 |
| E005 | 批量处理时目录为空 | "错误：输入目录中没有 .md 文件" | 确认目录内容后重试 |
| E006 | 校验失败 | "错误：输出文件缺少必要字段" | 重新执行解析操作 |
| E007 | 阈值设置无效 | "错误：阈值必须在 0 到 1 之间" | 检查阈值参数 |
| E008 | 标签参数格式错误 | "错误：标签需用逗号分隔" | 检查 `--tags` 参数格式 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|-----------|----------|
| 忽略置信度 | 直接使用所有解析结果，不检查置信度 | 设置阈值，过滤低置信度字段 |
| 批量处理前不备份 | 直接对原始目录执行 `--batch` | 先复制原始资料到备份目录 |
| 标签完全依赖自动生成 | 不检查自动标签的准确性 | 对重要文档使用 `--tags` 手动指定 |
| 不校验输出 | 解析完成后直接使用 JSON | 执行 `--verify` 确认结构完整 |
| 处理超大文件 | 单个文件超过 10MB 直接解析 | 先拆分文件，再逐个处理 |

### 6.2 反模式自查清单

- [ ] 是否检查了输出文件的置信度？
- [ ] 是否在批量处理前备份了原始资料？
- [ ] 是否对关键文档手动指定了标签？
- [ ] 是否执行了 `--verify` 校验？
- [ ] 是否确认输入文件编码为 UTF-8？

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```bash
# 最常用命令
karpathy llm wiki --input 文件.md --output 输出.json
karpathy llm wiki --batch --input ./目录/ --output ./输出/
karpathy llm wiki --verify --input 输出.json
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）

1. 阅读「能力边界」了解工具限制
2. 创建测试文件，执行单样本试运行
3. 对照「输出规范」检查结果
4. 处理 1-2 个真实文件，熟悉置信度标注
5. 批量处理前，先备份原始资料

#### 进阶路径（深度使用）

1. 使用 `--threshold` 调节置信度门控
2. 使用 `--tags` 手动指定标签，替代自动生成
3. 结合外部工具（如 Obsidian）实现知识库可视化
4. 编写脚本调用 CLI 接口，实现定时自动整理
5. 自定义校验规则，扩展 `--verify` 的检查项

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、解析错误、输出内容不准确等风险。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **合规使用**：使用者应确保输入数据来源合法，不得使用本 Skill 处理违法违规内容。

4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

5. **免责**：因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 知识工坊

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
