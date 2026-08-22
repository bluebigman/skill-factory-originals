---
slug: tldr-pro
name: tldr
displayName: 命令行速查手册 示例速览 多语言查询
description: 获取常用命令的简洁示例与参数速查，替代冗长手册。
version: 1.0.0
license: MIT
source_project: original
source_url: ""
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinCLI
agent_created: true
trigger_words: ["tldr", "cheat", "速查", "命令示例", "怎么用", "如何用", "命令行速查"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# tldr 技能文档

## 一、能力边界（一页纸速查卡）

本技能面向**命令行使用者**（含新手与进阶用户），提供命令速查与批量操作辅助。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 精确返回命令的常用参数与示例；支持反向搜索（按中文描述找命令）；支持批量命令生成与预览 |
| ❌ 不能做 | 不执行任何系统修改操作；不解析 man 手册全文；不提供 GUI 操作指导；不保证所有命令均有收录 |
| 适用对象 | 需要快速回忆命令参数、学习新命令、批量处理文件/目录的开发者与运维人员 |

**边界示例**：
- 输入 `tldr tar` → 返回 tar 的 3-5 个常用参数及示例
- 输入 `tldr --search "列出文件"` → 返回 `ls`、`find` 等候选命令
- 输入 `tldr 删除文件` → 返回 `rm` 的速查表，但**不会**直接执行删除

---

## 二、触发方式与场景映射

| 触发词/场景 | 响应模式 | 示例 |
|-------------|----------|------|
| `tldr <命令>` | 立即返回速查表 | `tldr grep` |
| `cheat <命令>` | 立即返回速查表 | `cheat docker` |
| `<命令> 怎么用/如何用/什么参数` | 延迟 1 轮确认后返回 | `git log 怎么用` |
| 仅提及命令名（无速查意图） | 不触发，进入普通对话 | "我今天学了 git" |
| `tldr --search <中文描述>` | 返回候选命令列表 | `tldr --search "查看磁盘占用"` |

**补充触发词**：`命令手册`、`快速参考`、`示例查询`

---

## 三、标准流程

### 前置条件
- 用户输入需包含命令名或明确的查询意图
- 若输入含特殊字符（如管道符、重定向），需用引号包裹

### 执行步骤

1. **读取输入**：解析用户消息，提取命令名、参数、查询意图
2. **匹配模式**：按优先级判断触发类型（精确匹配 > 长度优先 > 上下文优先）
3. **检索数据**：从内置速查库中查找对应条目
4. **组装输出**：按速查表格式返回（参数表 + 示例 + 注意事项）
5. **批量操作确认**：若涉及批量命令，先展示预览，等待用户确认

### 输出规范

```text
命令：<命令名>
用途：<一句话说明>

常用参数：
  -a, --all     <参数说明>
  -b, --batch   <参数说明>

示例：
  <命令> <示例1>
  <命令> <示例2>

注意：<特殊提示>
```

---

## 四、置信度门控

当出现以下情况时，输出 `[需核实:字段]` 占位符，**不编造**内容：

| 场景 | 处理方式 |
|------|----------|
| 命令未收录 | 返回 `[需核实:命令是否存在]` + 建议使用 `man <命令>` |
| 参数含义不确定 | 返回 `[需核实:参数说明]` + 提示查阅官方文档 |
| 多语言版本差异 | 返回 `[需核实:平台差异]` + 标注当前平台 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "请输入要查询的命令名" | 重新输入含命令名的内容 |
| E002 | 命令未找到 | "未找到该命令的速查记录" | 尝试 `tldr --search <关键词>` |
| E003 | 参数格式错误 | "参数格式不正确，请检查拼写" | 确认命令名拼写，或使用引号 |
| E004 | 批量操作未确认 | "已生成预览，请确认后执行" | 输入 `确认` 或 `取消` |
| E005 | 输出乱码 | "检测到编码问题，请设置 LANG=en_US.UTF-8" | 在 shell 中执行 `export LANG=en_US.UTF-8` |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 误执行批量操作 | 直接运行生成的批量命令 | 先预览，确认无误后再执行 |
| 查询不存在的命令 | 反复尝试不同拼写 | 使用 `--search` 按功能描述查找 |
| 忽略上下文关联 | 每次查询都当作独立请求 | 同一会话内，后续查询自动关联前一命令 |
| 依赖完整手册 | 期望返回 man 级别的全部信息 | 速查表仅覆盖 3-5 个最常用参数 |
| 多语言混淆 | 混用中英文参数 | 明确指定语言偏好，或使用 `LANG` 环境变量 |

---

## 七、渐进式披露

### 速查卡（新手路径）

1. 输入 `tldr <命令>` 获取速查表
2. 复制示例命令，在终端中测试
3. 遇到不认识的参数，使用 `man <命令>` 查阅详情

### 进阶路径

1. 使用 `tldr --search "<中文描述>"` 反向查找命令
2. 组合多个速查表，构建批量操作脚本
3. 利用上下文关联，连续查询相关命令（如 `tar` → `gzip` → `scp`）

### 深度路径

1. 对比不同平台的命令差异（Linux/macOS/Windows）
2. 自定义速查表扩展（需手动编辑数据文件）
3. 结合 shell 别名，将常用速查结果固化为快捷命令

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的代码、结构、算法进行反向工程、反编译或破解。
3. **合规使用**：不得将本 Skill 用于任何违反法律法规或道德伦理的用途。
4. **内容变更**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 LinCLI

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
