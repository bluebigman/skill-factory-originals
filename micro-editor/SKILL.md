---
slug: micro-editor
name: micro-editor
displayName: 终端文本 轻量编辑 文件处理
description: 终端内编辑文本文件，支持预览、查找替换与多行插入操作。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 终端工具设计组
agent_created: true
trigger_words: ["micro-editor", "终端编辑", "文本修改", "文件编辑", "命令行编辑"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# micro-editor Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 功能项 | 说明 | 示例 |
|--------|------|------|
| 文件打开 | 读取指定路径的文本文件内容 | `micro-editor open ./notes.txt` |
| 内容预览 | 显示文件当前内容，不修改文件 | `micro-editor preview ./notes.txt` |
| 查找替换 | 在文件中定位并替换指定字符串 | `micro-editor replace "旧词" "新词" ./notes.txt` |
| 多行插入 | 在指定行号后插入多行文本 | `micro-editor insert 5 "行1\n行2" ./notes.txt` |
| 语法高亮 | 根据文件扩展名显示高亮内容 | 自动识别 `.py`、`.js`、`.md` 等 |
| 干跑模式 | 不实际修改文件，仅显示将执行的操作 | `micro-editor replace "a" "b" ./f.txt --dry-run` |
| 差异明细 | 显示修改前后的具体差异 | `micro-editor diff ./f.txt` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 二进制文件 | 不支持编辑非纯文本文件（如图片、压缩包） |
| 非 UTF-8/GBK 编码 | 其他编码（如 UTF-16、Latin-1）无法正确处理 |
| 目录操作 | 不支持创建、删除、移动目录 |
| 权限管理 | 不处理文件权限变更，仅按当前用户权限操作 |
| 远程文件 | 仅支持本地文件系统路径 |
| 大文件 | 超过 10MB 的文件可能响应缓慢，建议分段处理 |

### 1.3 适用对象

- 需要在终端中快速修改配置文件的开发者
- 需要批量替换文本内容的运维人员
- 偏好命令行操作、不依赖图形编辑器的用户

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`micro-editor`
- 同义场景词：`终端编辑`、`文本修改`、`文件编辑`、`命令行编辑`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发操作 |
|------------------|--------------|
| "帮我改一下这个配置文件里的端口号" | `micro-editor replace "8080" "9090" ./config.yml` |
| "看看这个日志文件里写了什么" | `micro-editor preview ./app.log` |
| "在这个文件第 10 行后面加几行配置" | `micro-editor insert 10 "新配置内容" ./settings.conf` |
| "把代码里所有的 TODO 都换成 FIXME" | `micro-editor replace "TODO" "FIXME" ./src/main.py` |
| "先别改，让我看看会改哪些地方" | `micro-editor replace "旧值" "新值" ./file.txt --dry-run` |

---

## 三、标准流程

### 3.1 前置条件

1. 确认目标文件路径存在，且为普通文件（非目录、非设备文件）。
2. 确认文件编码为 UTF-8 或 GBK（可通过 `file` 命令检查）。
3. 确认当前用户对文件有读写权限（`ls -l` 查看权限位）。
4. 确认文件大小不超过 10MB（`ls -lh` 查看）。

### 3.2 执行步骤

#### 步骤 1：收集输入并确认格式

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| 操作类型 | 是 | `open` / `preview` / `replace` / `insert` / `diff` | `replace` |
| 文件路径 | 是 | 目标文件的绝对或相对路径 | `./docs/readme.md` |
| 查找内容 | 条件必填 | `replace` 操作需要 | `"旧文本"` |
| 替换内容 | 条件必填 | `replace` 操作需要 | `"新文本"` |
| 插入行号 | 条件必填 | `insert` 操作需要 | `5` |
| 插入内容 | 条件必填 | `insert` 操作需要 | `"新增行内容"` |
| `--dry-run` | 否 | 干跑模式，不实际修改 | `--dry-run` |

#### 步骤 2：执行操作（去掉 `--dry-run` 参数）

```bash
# 示例：替换操作
micro-editor replace "旧值" "新值" ./target.txt

# 示例：插入操作
micro-editor insert 12 "新增配置项 = true" ./app.conf

# 示例：干跑模式预览
micro-editor replace "旧值" "新值" ./target.txt --dry-run
```

#### 步骤 3：校验结果

```bash
# 查看修改后的文件内容
micro-editor preview ./target.txt

# 查看修改前后的差异明细
micro-editor diff ./target.txt
```

#### 步骤 4：处理失败

若步骤 2-3 中任何一步报错，参照「五、错误码体系」中的指引修正输入或环境问题后重试。

### 3.3 输出规范

- 成功操作：输出 `操作成功` 及修改摘要（修改行数、位置）。
- 干跑模式：输出将执行的操作明细，不修改文件。
- 失败操作：输出错误码、错误描述及修正建议。

---

## 四、置信度门控

当输入信息不足或存在歧义时，使用 `[需核实:字段]` 占位符，不编造内容。

| 场景 | 处理方式 |
|------|----------|
| 文件路径不存在 | 输出 `[需核实:文件路径]`，提示用户确认路径 |
| 查找内容在文件中不存在 | 输出 `[需核实:查找内容]`，提示用户确认目标字符串 |
| 插入行号超出文件范围 | 输出 `[需核实:行号]`，提示用户确认行号范围 |
| 文件编码无法识别 | 输出 `[需核实:文件编码]`，提示用户确认编码格式 |
| 操作类型不明确 | 输出 `[需核实:操作类型]`，列出可选操作 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | 无法找到指定文件，请检查路径是否正确 | 使用 `ls` 确认路径，或提供正确的绝对路径 |
| E002 | 编码不支持 | 文件编码不是 UTF-8 或 GBK | 使用 `iconv` 转换编码后再操作 |
| E003 | 权限不足 | 当前用户无读写权限 | 使用 `chmod` 调整权限，或切换用户 |
| E004 | 查找内容为空 | `replace` 操作的查找内容不能为空 | 提供非空的查找字符串 |
| E005 | 插入行号越界 | 行号超出文件总行数范围 | 使用 `preview` 查看文件总行数，重新指定行号 |
| E006 | 文件过大 | 文件超过 10MB 限制 | 拆分文件或使用其他工具处理 |
| E007 | 参数缺失 | 缺少必填参数 | 参照「三、标准流程」中的参数表补齐参数 |
| E008 | 语法错误 | 命令格式不正确 | 使用 `micro-editor --help` 查看用法 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 路径含空格 | `micro-editor open /path/my file.txt` | 使用引号包裹路径：`micro-editor open "/path/my file.txt"` |
| 特殊字符未转义 | `micro-editor replace "a" "b" ./f.txt` 中内容含 `$` | 使用单引号包裹内容：`micro-editor replace '$old' '$new' ./f.txt` |
| 忘记干跑验证 | 直接执行修改，结果发现改错位置 | 先执行 `--dry-run` 预览，确认无误后再实际执行 |
| 编码混用 | 文件是 GBK 编码，但按 UTF-8 处理 | 先使用 `file` 命令确认编码，必要时转换 |
| 行号从 0 开始 | 用户认为第 1 行是行号 0 | 本工具行号从 1 开始计数，与常见编辑器一致 |

### 6.2 反模式对照

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 用 `replace` 做全局替换但未确认次数 | 可能替换了不该替换的位置 | 先 `--dry-run` 查看差异，确认替换范围 |
| 在文件末尾插入时使用超大行号 | 报 E005 错误 | 使用 `preview` 查看总行数，用 `总行数+1` 作为插入位置 |
| 连续多次修改同一文件 | 中间步骤出错难以定位 | 每次修改后立即 `diff` 校验，或使用版本控制工具 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
micro-editor 常用命令速查：

  preview <文件>              # 查看文件内容
  replace <旧> <新> <文件>    # 替换文本
  insert <行号> <内容> <文件> # 插入多行
  diff <文件>                 # 查看修改差异
  --dry-run                   # 干跑模式（不实际修改）
```

### 7.2 分层次阅读路径

#### 新手路径

1. 阅读「一、能力边界」了解工具能做什么。
2. 使用 `preview` 命令查看文件内容。
3. 使用 `replace` 配合 `--dry-run` 进行安全替换。
4. 使用 `diff` 确认修改结果。

#### 进阶路径

1. 掌握 `insert` 多行插入，配合行号精确定位。
2. 理解错误码体系，快速定位问题。
3. 结合 shell 脚本批量处理多个文件。
4. 使用 `--selftest` 验证工具自身状态，使用 `--version` 确认版本。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 micro-editor Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因操作不当（包括但不限于文件误修改、数据丢失、配置错误）造成的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保使用本 Skill 的行为符合所在组织及当地法律法规的要求。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 终端工具设计组

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
