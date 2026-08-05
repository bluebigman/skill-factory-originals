---
slug: aider
name: AI结对编程助手
displayName: 终端结对 代码协同 自动提交
description: 终端内AI结对编程，自动提交Git，支持多文件编辑。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 代码工坊
agent_created: true
trigger_words: ["aider", "结对编程", "AI改代码", "终端编程助手", "AI写代码", "自动提交"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI 结对编程助手（Aider）技能文档

## 一、能力边界速查卡

### 能做什么
| 能力项 | 说明 | 示例 |
|--------|------|------|
| 多文件协同编辑 | 同时加载多个源文件，AI 可跨文件理解上下文并修改 | `/add src/main.py src/helper.py` |
| 自动 Git 提交 | 接受修改后自动执行 `git add` 与 `git commit` | 输入 `y` 即完成提交 |
| 差异审查 | 逐文件查看 diff，决定接受或拒绝 | 输入 `s` 进入逐文件审查模式 |
| 修改回退 | 通过 `/undo` 撤销最近一次 AI 修改 | `/undo` 回退到上一状态 |
| 批量文件处理 | 对同目录下多个文件执行统一格式的修改任务 | 批量添加字段提取逻辑 |

### 不能做什么
| 限制项 | 说明 |
|--------|------|
| 非 Git 目录 | 当前目录未初始化 Git 仓库时无法工作 |
| 无提交记录 | 仓库无任何 commit 时无法执行自动提交 |
| 跨会话记忆 | 每次启动为全新会话，不保留历史上下文 |
| 网络依赖 | 需要联网调用 AI 服务，离线不可用 |
| 非代码文件 | 仅针对代码文件进行编辑，不处理二进制或图片 |

### 适用对象
- 使用终端进行日常开发的程序员
- 需要快速原型验证的开发者
- 希望减少手动 Git 提交操作的团队

---

## 二、触发方式与场景映射

| 触发词 | 典型场景 | 用户意图 |
|--------|----------|----------|
| `aider` | 在终端输入 `aider` 启动工具 | 进入结对编程会话 |
| `结对编程` | 描述"帮我结对编程改一下这个函数" | 请求 AI 协助修改代码 |
| `AI改代码` | 说"用 AI 改一下这段逻辑" | 请求自动修改代码 |
| `终端编程助手` | 说"在终端里帮我写个脚本" | 请求终端内编程辅助 |
| `AI写代码` | 说"帮我写一个排序算法" | 请求生成新代码 |
| `自动提交` | 说"改完自动提交一下" | 期望修改后自动 Git 提交 |

---

## 三、标准操作流程

### 前置条件检查

| 检查项 | 验证命令 | 通过标准 |
|--------|----------|----------|
| Git 仓库 | `git rev-parse --is-inside-work-tree` | 输出 `true` |
| 提交记录 | `git log --oneline` | 至少有一行输出 |
| Python 版本 | `python3 --version` | 3.9 或更高 |
| Aider 安装 | `aider --version` | 正常输出版本号 |

### 执行步骤

1. **进入项目目录**
   ```bash
   cd your-project/
   ```

2. **启动 Aider**
   ```bash
   aider
   ```

3. **加载相关文件**
   ```
   /add src/main.py src/helper.py
   ```
   参数说明：
   - 支持绝对路径与相对路径
   - 一次可添加多个文件，空格分隔
   - 使用 `/add` 查看已加载文件列表

4. **描述修改需求**
   用自然语言描述期望的改动，例如：
   > "把 main.py 中的排序逻辑改为快速排序，并更新 helper.py 中的调用方式"

5. **查看修改建议**
   AI 返回修改后的代码与 diff，逐行审查变更内容。

6. **接受或拒绝修改**
   | 输入 | 行为 |
   |------|------|
   | `y` | 接受全部修改，自动执行 `git add` 与 `git commit` |
   | `n` | 拒绝修改，AI 还原文件到原始状态 |
   | `s` | 逐文件查看 diff，逐个决定接受或拒绝 |

7. **验证结果**
   ```bash
   python3 -m pytest tests/  # 运行测试
   git log --oneline -3      # 查看提交记录
   ```

8. **调整与回退**
   - 需要撤销：输入 `/undo` 回退最近一次修改
   - 继续修改：直接描述新的需求

### 输出规范

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 修改建议 | 展示 diff，标注新增/删除行 | `+ 新增代码` / `- 删除代码` |
| 提交信息 | 自动生成，格式为 `feat: 描述` | `feat: 优化排序算法` |
| 错误提示 | 明确说明错误原因与修正方法 | `错误：目录不是 Git 仓库` |

---

## 四、置信度门控

当 AI 对以下情况不确定时，必须输出 `[需核实:字段]` 占位符，不得编造：

| 场景 | 占位符示例 |
|------|------------|
| 文件路径不确定 | `[需核实:文件路径]` |
| 函数签名不明确 | `[需核实:函数参数列表]` |
| 依赖版本未知 | `[需核实:依赖版本号]` |
| 业务逻辑模糊 | `[需核实:业务规则]` |

**处理原则**：
1. 信息不足时，先输出占位符，再询问用户补充
2. 不猜测文件内容，不虚构 API 返回值
3. 对不确定的修改点，明确标注"建议人工确认"

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 非 Git 仓库 | "当前目录不是 Git 仓库，请先执行 `git init`" | 1. 执行 `git init` 2. 创建初始提交 `git commit -m "init"` |
| E002 | 无提交记录 | "仓库无提交记录，无法执行自动提交" | 1. 手动创建初始提交 2. 重新启动 aider |
| E003 | Python 版本过低 | "Python 版本需 3.9+，当前版本过低" | 1. 升级 Python 2. 重新安装 aider |
| E004 | Aider 未安装 | "未检测到 aider，请先安装" | 1. 执行 `pip install aider-chat` 2. 验证 `aider --version` |
| E005 | 文件加载失败 | "无法加载指定文件，请检查路径" | 1. 确认文件存在 2. 检查路径拼写 3. 使用绝对路径重试 |
| E006 | 修改冲突 | "文件已被外部修改，无法应用 AI 变更" | 1. 手动合并冲突 2. 重新加载文件 3. 重试修改 |

---

## 六、常见坑与反模式

### 坑 1：忽略 Git 状态
**反模式**：在未提交的脏工作区直接启动 aider，导致 AI 修改与本地未提交变更冲突。
**正确做法**：启动前先 `git status` 确认工作区干净，或先提交当前变更。

### 坑 2：一次性加载过多文件
**反模式**：一次 `/add` 加载 20+ 文件，导致上下文超限，AI 响应质量下降。
**正确做法**：只加载与当前任务相关的文件，控制在 5 个以内。

### 坑 3：盲目接受所有修改
**反模式**：不审查 diff 直接输入 `y`，可能引入错误逻辑。
**正确做法**：使用 `s` 逐文件审查，确认每个变更点。

### 坑 4：忽略测试验证
**反模式**：AI 修改后不运行测试，直接提交。
**正确做法**：修改后立即运行相关测试，确认无回归。

### 坑 5：依赖 AI 记忆
**反模式**：期望 AI 记住上次会话的上下文。
**正确做法**：每次会话重新描述需求，必要时重新加载文件。

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）
```
启动：cd project && aider
加载：/add file1.py file2.py
描述：用自然语言说明修改需求
接受：y（接受）/ n（拒绝）/ s（逐文件审查）
回退：/undo
退出：/exit
```

### 新手路径（首次使用）
1. 阅读「前置条件检查」确保环境就绪
2. 按「标准操作流程」完成一次完整操作
3. 遇到问题查阅「错误码体系」
4. 注意「常见坑」中的前 3 项

### 进阶路径（熟练用户）
1. 掌握「批量文件处理」技巧
2. 理解「置信度门控」的边界场景
3. 自定义提交信息模板
4. 结合 CI/CD 流程自动化验证

---

## 八、批量处理场景指南

### 适用场景
- 对多个文件执行相同模式的修改（如添加日志、统一错误处理）
- 批量提取字段并结构化输出
- 多文件间的关联修改

### 操作步骤
1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致
2. **试运行**：先用单个样本执行，核对输出字段与格式
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致

### 注意事项
- 批量操作前务必备份原始文件
- 每次修改后检查 Git 提交记录，确保可回退
- 对失败条目记录错误原因，便于后续修复

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用须知**：
1. 使用者自行承担全部责任：本 Skill 提供的所有功能与建议仅供参考，使用者应对使用结果负全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. 禁止反向工程：不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码。
3. 合规使用：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。
4. 无担保声明：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 代码工坊

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
