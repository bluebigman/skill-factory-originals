---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: git-wiki
name: git-wiki
displayName: 文档建站 Git版本 知识库管理
description: 将零散文档快速转化为 Git 版本控制的轻量 Wiki 站点。
version: 1.0.2
rules_version: cpr-20260817-n526
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/git-wiki
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨轩
agent_created: true
trigger_words: ["git-wiki", "wiki", "git wiki", "文档站点", "知识库搭建", "文档建站", "知识库管理", "wiki生成"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# git-wiki 技能手册

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文档清洗 | 去除原始文本中的无关字符、重复空行、乱码 | 将带 BOM 头的 txt 转为干净 Markdown |
| 元数据生成 | 自动提取或生成 YAML frontmatter | 从文件名提取 `title`，从系统时间生成 `date` |
| 双链转换 | 将 `[[双链]]` 语法转换为可点击的相对链接 | `[[安装指南]]` → `[安装指南](./安装指南.md)` |
| 索引生成 | 自动生成 `_index.md` 目录页 | 按文件名排序，列出所有页面标题与摘要 |
| Git 集成 | 输出目录可直接 `git init` 使用 | 生成 `.gitignore` 建议文件 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行 Git 命令 | 只生成文件，不自动 commit/push |
| 不处理二进制文件 | 仅支持 `.md`、`.txt`、`.markdown` 文本格式 |
| 不进行语义理解 | 不总结、不翻译、不提炼正文内容 |
| 不修改源文件 | 所有操作在输出目录进行，源目录只读 |
| 不生成图片 | 图片需自行放置到输出目录的 `assets/` 文件夹 |

### 1.3 适用对象

- 需要快速搭建个人知识库的开发者
- 维护项目文档但不想引入重型 CMS 的团队
- 希望用 Git 管理文档版本的写作爱好者

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 场景说明 |
|--------|----------|
| `git-wiki` | 标准触发，后接文件夹路径 |
| `wiki` | 简写触发，适合快速输入 |
| `git wiki` | 强调 Git 版本控制场景 |
| `文档站点` | 中文场景，适合非技术用户 |
| `知识库搭建` | 面向知识管理需求 |
| `文档建站` | 强调站点生成属性 |
| `知识库管理` | 面向长期维护场景 |
| `wiki生成` | 强调自动化生成 |

### 2.2 场景映射表

| 用户说 | 实际需求 | 执行动作 |
|--------|----------|----------|
| "把这几篇笔记整理成 wiki" | 需要目录索引和页面关联 | 执行标准流程，生成 `_index.md` |
| "我的文档要能追溯版本" | 需要 Git 集成 | 输出目录附带 `.gitignore` 建议 |
| "文档里有很多 `[[链接]]` 没处理" | 需要双链转换 | 自动转换所有双链语法 |
| "帮我建个团队知识库" | 需要多人协作结构 | 生成 `_index.md` + 按目录分组 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|----------|
| 输入目录 | 存在且包含 2-3 个 `.md` 文件 | `ls /path/to/folder/*.md` |
| 文件编码 | UTF-8 无 BOM | `file -i 文件名.md` |
| 输出目录 | 不存在或为空 | `ls /path/to/output` |
| 磁盘空间 | 至少 10MB 可用 | `df -h` |

### 3.2 执行步骤

**步骤 1：读取源文件**

```bash
# 输入示例
git-wiki wiki /path/to/source_folder
```

读取 `/path/to/source_folder` 下所有 `.md`、`.txt`、`.markdown` 文件。

**步骤 2：清洗内容**

- 移除每行首尾多余空格（保留 Markdown 语法所需缩进）
- 合并连续 3 个以上的空行为 1 个
- 移除不可见 Unicode 字符（如零宽空格 `\u200B`）
- 保留 HTML 标签（如 `<br>`、`<div>`）

**步骤 3：提取或生成元数据**

| 字段 | 来源优先级 | 默认值 |
|------|------------|--------|
| `title` | 文件内 YAML frontmatter → 文件名（去扩展名） | 文件名 |
| `source` | 源文件相对路径 | 无 |
| `date` | 文件内 YAML frontmatter → 文件修改时间 | 当前时间 |

**步骤 4：转换双链**

```markdown
# 输入
[[安装指南]] 和 [[常见问题]] 请参考。

# 输出
[安装指南](./安装指南.md) 和 [常见问题](./常见问题.md) 请参考。
```

**步骤 5：生成输出文件**

输出目录结构：

```
output/
├── _index.md          # 自动生成的目录页
├── 安装指南.md         # 清洗后的内容 + 元数据
├── 常见问题.md
└── .gitignore         # 建议的 Git 忽略规则
```

### 3.3 输出规范

每个页面文件格式：

```markdown
---
title: 安装指南
source: docs/install.md
date: 2026-08-17T10:30:00+08:00
---

<!-- 正文内容 -->

<!-- generated-by: git-wiki -->
```

`_index.md` 格式：

```markdown
---
title: Wiki 首页
generated: 2026-08-17T10:30:00+08:00
---

# Wiki 首页

- [安装指南](./安装指南.md) — 安装步骤说明
- [常见问题](./常见问题.md) — 常见问题解答
```

---

## 四、置信度门控

### 4.1 信息不足处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不编造内容：

| 场景 | 占位符示例 |
|------|------------|
| 无法确定文件修改时间 | `[需核实:date]` |
| 文件名无法推断标题 | `[需核实:title]` |
| 双链指向不存在的文件 | `[需核实:链接目标]` |

### 4.2 示例

```markdown
---
title: [需核实:title]
source: unknown_file.txt
date: [需核实:date]
---

正文内容...

<!-- generated-by: git-wiki -->
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 输入目录不存在 | "指定的文件夹不存在，请检查路径" | 确认路径正确后重试 |
| `E002` | 输入目录无支持的文本文件 | "未找到 .md/.txt/.markdown 文件" | 添加文件后重试 |
| `E003` | 输出目录非空 | "输出目录已存在文件，为避免覆盖请更换目录" | 更换输出路径或清空目录 |
| `E004` | 文件编码不支持 | "文件编码不是 UTF-8，请转换后重试" | 使用 `iconv -f GBK -t UTF-8 文件` 转换 |
| `E005` | 文件读取权限不足 | "没有读取文件的权限" | 检查文件权限 `chmod +r 文件` |
| `E006` | 磁盘空间不足 | "磁盘空间不足，无法写入输出文件" | 清理磁盘或更换输出路径 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|------------|----------|
| 源文件被修改 | 直接在源目录生成输出文件 | 始终使用独立输出目录 |
| 双链失效 | 链接目标文件名含空格未处理 | 链接中使用 `%20` 或下划线替代空格 |
| 元数据丢失 | 手动编辑生成的文件后重新运行 | 在源文件中维护元数据，重新生成 |
| 目录混乱 | 所有文件平铺在根目录 | 按主题分子目录存放 |
| Git 冲突 | 多人同时编辑同一文件 | 使用分支管理，合并前先 pull |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 手动维护 `_index.md` | 内容更新后索引过期 | 每次生成时自动重建 |
| 在生成文件中写死日期 | 文件移动后日期错误 | 使用 `date` 字段记录处理时间 |
| 忽略 `.gitignore` | 临时文件被提交 | 始终包含 `*.tmp`、`.DS_Store` 忽略规则 |

---

## 七、渐进式披露

### 7.1 新手路径（5 分钟上手）

1. 准备一个文件夹，放入 2-3 个 `.md` 文件
2. 输入 `git-wiki wiki /path/to/folder`
3. 查看输出目录下的 `_index.md` 和生成的页面文件
4. 用任意 Markdown 编辑器打开查看效果

### 7.2 进阶路径（30 分钟精通）

1. 在源文件中添加 YAML frontmatter：

```markdown
---
title: 自定义标题
tags: [安装, 配置]
---

正文内容...
```

2. 使用 `[[双链]]` 语法在页面间建立关联
3. 结合 Git 钩子（如 `post-commit`）实现自动部署：

```bash
#!/bin/bash
# .git/hooks/post-commit
git-wiki wiki ./docs
cd ./wiki-output && git add . && git commit -m "auto-update"
```

4. 自定义 `_index.md` 模板（在输出目录放置 `_template.md` 覆盖默认模板）

### 7.3 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--selftest` | 布尔 | `false` | 运行自检，验证环境 |
| `--version` | 布尔 | `false` | 显示版本号 |
| `--output` | 路径 | `./wiki-output` | 指定输出目录 |
| `--template` | 路径 | 内置模板 | 自定义索引模板 |
| `--no-index` | 布尔 | `false` | 不生成 `_index.md` |

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者需确保使用场景符合当地法律法规及平台规定。
4. **内容责任**：生成的内容由使用者负责审核，作者不对生成内容的准确性、完整性作任何保证。
5. **修改与分发**：允许修改和再分发，但需保留原始版权声明。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

MIT License

Copyright (c) 2026 林墨轩

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

<!-- professional-license-embedded -->
