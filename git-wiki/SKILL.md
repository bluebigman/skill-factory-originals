---
slug: git-wiki
name: git-wiki
displayName: 文档速建 Git 知识库
description: 将零散 Markdown 文档快速转化为 Git 版本控制的轻量 Wiki 站点。
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
trigger_words: ["git-wiki", "wiki", "git wiki", "文档站点", "知识库搭建", "文档建站", "知识管理", "wiki生成"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# git-wiki Skill 文档

本 Skill 由 AI 辅助生成，仅供参考，不构成任何形式的保证或承诺。

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 目录扫描 | 递归读取指定文件夹内所有 `.md` 文件 | `git-wiki wiki ./docs` |
| 索引生成 | 自动生成 `_index.md` 汇总页面 | 输出到目标目录根路径 |
| 双链解析 | 识别 `[[页面名]]` 语法并建立关联 | `[[安装指南]]` 自动链接到对应页面 |
| 模板覆盖 | 支持自定义 `_template.md` 覆盖默认索引模板 | 在输出目录放置模板文件 |
| Git 集成 | 生成的文件可直接纳入 Git 版本管理 | 配合 `post-commit` 钩子自动部署 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持非 Markdown 格式 | 仅处理 `.md` 文件，忽略 `.docx`、`.pdf` 等 |
| 不处理图片资源 | 图片需自行管理，工具不复制或转换图片 |
| 不提供 Web 服务器 | 生成的是静态文件，需自行托管（如 GitHub Pages） |
| 不解析复杂 HTML 嵌入 | 页面内嵌的 HTML 代码保持原样，不做渲染处理 |
| 不自动推送 Git | 仅生成文件，提交和推送需手动或通过钩子完成 |

### 适用对象

- 个人知识库维护者：需要快速将零散笔记整理为可浏览的站点结构
- 小型团队文档管理员：希望用 Git 跟踪文档变更历史
- 技术写作者：习惯用 Markdown 写作，需要轻量发布方案

---

## 二、触发方式与场景映射

| 触发词 | 典型使用场景 | 用户意图 |
|--------|-------------|----------|
| `git-wiki` | 命令行直接调用 | 执行工具主程序 |
| `wiki` | 口语化指令 | 快速生成 Wiki 站点 |
| `git wiki` | 强调 Git 版本控制 | 需要版本管理能力的文档站点 |
| `文档站点` | 中文场景 | 将文档转为站点形式 |
| `知识库搭建` | 从零开始 | 初始化一个知识库结构 |
| `文档建站` | 已有文档 | 将现有文档整理为站点 |
| `知识管理` | 长期维护 | 持续更新知识体系 |

---

## 三、标准流程

### 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 源文件夹 | 存在且包含至少 1 个 `.md` 文件 | `ls /path/to/folder/*.md` |
| 输出目录 | 可写权限 | `touch /path/to/output/.write_test` |
| Git 环境 | 如需版本控制，需已安装 Git | `git --version` |
| 磁盘空间 | 至少 10MB 可用空间 | `df -h` |

### 执行步骤

1. **准备源文件**
   - 创建文件夹，放入 2-3 个 `.md` 文件
   - 建议在文件头部添加 YAML frontmatter：
     ```yaml
     ---
     title: 页面标题
     tags: [标签1, 标签2]
     date: 2024-01-01
     ---
     ```
   - 在正文中使用 `[[双链]]` 语法建立页面关联

2. **执行生成命令**
   ```bash
   git-wiki wiki /path/to/source_folder
   ```
   可选参数：
   | 参数 | 作用 | 默认值 |
   |------|------|--------|
   | `--output` | 指定输出目录 | 源文件夹下的 `_wiki_output` |
   | `--template` | 指定模板文件路径 | 输出目录下的 `_template.md` |
   | `--verbose` | 显示详细日志 | 关闭 |

3. **检查生成结果**
   - 确认输出目录下存在 `_index.md`
   - 确认每个源文件对应生成一个页面文件
   - 检查双链是否被正确解析为链接

4. **验证与预览**
   - 用任意 Markdown 编辑器打开 `_index.md`
   - 检查页面间跳转是否正常
   - 确认 frontmatter 中的元数据被正确展示

5. **纳入版本控制（可选）**
   ```bash
   cd /path/to/output
   git init
   git add .
   git commit -m "初始化 Wiki 站点"
   ```

### 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| `_index.md` | Markdown | 站点首页，包含所有页面链接 |
| 页面文件 | Markdown | 每个源文件对应一个 `.md` 文件 |
| `_template.md` | Markdown | 自定义模板（如存在） |
| 日志 | 文本 | 生成过程的错误和警告信息 |

---

## 四、置信度门控

当遇到以下情况时，工具会输出 `[需核实:字段]` 占位符，而非编造内容：

| 场景 | 占位符示例 | 处理方式 |
|------|-----------|----------|
| 页面标题缺失 | `[需核实:页面标题]` | 检查源文件 frontmatter |
| 双链目标不存在 | `[需核实:链接目标]` | 确认目标文件是否存在 |
| 日期格式异常 | `[需核实:日期]` | 检查 frontmatter 中 date 字段 |
| 标签格式错误 | `[需核实:标签]` | 确认 tags 是否为数组格式 |

**原则**：信息不足时明确标注，不猜测、不虚构。

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 源文件夹不存在 | "指定的源文件夹不存在，请检查路径" | 确认路径正确，或先创建文件夹 |
| `E002` | 无 Markdown 文件 | "源文件夹中未找到 .md 文件" | 添加至少一个 `.md` 文件 |
| `E003` | 输出目录不可写 | "输出目录没有写入权限" | 修改目录权限或更换输出路径 |
| `E004` | 模板文件格式错误 | "模板文件解析失败，请检查 YAML 格式" | 检查 `_template.md` 的 frontmatter |
| `E005` | 双链循环引用 | "检测到页面间循环引用" | 检查并调整 `[[双链]]` 指向 |
| `E006` | 文件名冲突 | "存在同名文件，可能导致覆盖" | 重命名冲突文件 |
| `E007` | Git 操作失败 | "Git 命令执行失败，请检查 Git 环境" | 确认 Git 已安装且仓库状态正常 |

---

## 六、FAQ 反模式

### 常见坑 1：忽略 frontmatter

**反模式**：直接在正文写标题，不添加 YAML frontmatter。

**后果**：页面标题显示为文件名，元数据丢失。

**正确做法**：
```yaml
---
title: 安装指南
tags: [入门, 配置]
---
```

### 常见坑 2：双链指向不存在的页面

**反模式**：随意使用 `[[任意名称]]`，不确认目标是否存在。

**后果**：生成死链接，影响浏览体验。

**正确做法**：先创建目标文件，再添加双链。

### 常见坑 3：模板覆盖位置错误

**反模式**：将 `_template.md` 放在源文件夹而非输出目录。

**后果**：模板不生效，使用默认样式。

**正确做法**：将模板放在输出目录根路径下。

### 常见坑 4：文件名包含特殊字符

**反模式**：使用空格、中文标点等作为文件名。

**后果**：链接生成异常，Git 操作报错。

**正确做法**：使用短横线或下划线命名，如 `install-guide.md`。

### 常见坑 5：忘记 Git 钩子配置

**反模式**：生成站点后手动提交，忘记配置自动部署。

**后果**：每次更新都需要手动操作，容易遗漏。

**正确做法**：配置 `post-commit` 钩子：
```bash
#!/bin/sh
git-wiki wiki ./docs --output ./public
cd ./public && git add . && git commit -m "auto deploy"
```

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 1. 准备文件
mkdir my-wiki && cd my-wiki
echo "# Hello" > intro.md

# 2. 生成站点
git-wiki wiki .

# 3. 查看结果
ls _wiki_output/
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解工具范围
2. 按「标准流程」完成一次基础生成
3. 查看「FAQ 反模式」避免常见错误
4. 尝试添加 frontmatter 和双链

### 进阶路径（深度使用）

1. 自定义 `_template.md` 实现个性化样式
2. 配置 Git 钩子实现自动部署
3. 结合 CI/CD 流程实现持续集成
4. 扩展双链语法，建立知识图谱

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用即视为同意全部内容：**

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **合规使用**：使用者需确保使用场景符合当地法律法规及平台规定。

4. **内容责任**：生成的内容由使用者负责审核，作者不对生成内容的准确性、完整性作任何保证。

5. **修改与分发**：允许修改和再分发，但需保留原始版权声明。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 林墨

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

*文档版本：1.0.0 | 最后更新：2024年*
