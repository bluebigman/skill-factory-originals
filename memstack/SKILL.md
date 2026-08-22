---
slug: memstack
name: memstack
displayName: 学习参考 数据转换 结构化处理
description: 将用户提供的文件或URL转换为结构化结果，供学习与参考使用。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["memstack", "学习参考", "数据转换", "结构化处理", "信息提取", "资料整理", "内容归档"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# memstack Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文件转结构化 | 将文本类文件（txt/md/csv/json）解析为字段化条目 | `data.csv` | 按行拆分的 JSON 数组 |
| URL 内容提取 | 抓取公开网页正文，剔除导航/广告噪音 | `https://example.com/article` | 标题+正文+发布时间 |
| 批量目录处理 | 对同一目录下多个文件逐一执行转换 | `./docs/*.md` | 每个文件对应一个输出文件 |
| 字段映射校验 | 检查输出字段是否与源数据一致 | 源文件含 `id,name` 字段 | 输出条目含 `id,name` 且值一致 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制文件 | 图片、PDF 扫描件、音视频等需先转文本 |
| 不访问付费墙内容 | 需要登录或付费的 URL 无法抓取 |
| 不进行语义理解 | 仅做结构转换，不判断内容对错 |
| 不自动修改源文件 | 所有操作均在副本上进行 |

### 1.3 适用对象

- 需要将散乱资料整理为统一格式的学习者
- 需要批量提取网页信息做调研的从业者
- 需要将旧格式数据迁移到新系统的开发者

---

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 适用场景 |
|--------|----------|
| `memstack` | 通用触发，进入默认处理流程 |
| `学习参考` | 明确表达整理资料用于学习目的 |
| `数据转换` | 强调格式转换需求 |
| `结构化处理` | 强调输出字段化结果 |
| `信息提取` | 强调从非结构化内容中抽取关键字段 |
| `资料整理` / `内容归档` | 批量整理场景 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我把这几个网页存成表格" | 抓取 URL → 提取标题/正文/日期 → 输出 CSV |
| "这个文件夹里的笔记太乱了，整理一下" | 扫描目录 → 逐文件解析 → 输出统一格式 |
| "把这个 CSV 转成我能看的格式" | 读取 CSV → 按列映射 → 输出 JSON/Markdown 表格 |
| "提取这篇文章里的所有日期和数字" | 解析文本 → 正则匹配日期/数字 → 输出字段列表 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 文本格式（txt/md/csv/json/html） | 文件扩展名确认 |
| 文件位置 | 与执行目录一致，或提供绝对路径 | `ls` 命令确认 |
| 命名规范 | 文件名不含空格和特殊字符 | 正则 `^[a-zA-Z0-9_\-\.]+$` |
| URL 可达性 | 目标网页可公开访问 | `curl -I` 返回 200 |
| 输出目录 | 存在且可写 | `test -w` 确认 |

### 3.2 执行步骤

#### 步骤 1：准备输入

```bash
# 将待处理文件放入同一目录
mkdir -p ./input ./output
cp /path/to/source/*.md ./input/
# 确认命名规范
ls ./input/
```

#### 步骤 2：单样本试运行

```bash
# 对单个文件执行转换
memstack process ./input/sample.md --output ./output/sample.json
# 检查输出字段
cat ./output/sample.json | jq '.[0]'
```

**试运行检查清单：**

- [ ] 输出是否为合法 JSON
- [ ] 字段名是否与预期一致
- [ ] 字段值是否与源文件对应
- [ ] 空值/缺失字段是否标记为 `[需核实:字段名]`

#### 步骤 3：批量执行

```bash
# 确认无误后，对全量数据执行
memstack batch ./input/ --output ./output/
# 保留原始文件备份
cp -r ./input ./backup_$(date +%Y%m%d)
```

**批量执行参数表：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` | `./input/` | 输入目录 |
| `--output` | `./output/` | 输出目录 |
| `--format` | `json` | 输出格式（json/csv/md） |
| `--recursive` | `false` | 是否递归子目录 |
| `--overwrite` | `false` | 是否覆盖同名输出文件 |
| `--verbose` | `false` | 是否输出详细日志 |

#### 步骤 4：结果校验

```bash
# 抽查输出条目
memstack verify ./output/sample.json --source ./input/sample.md
```

**校验规则：**

| 校验项 | 方法 | 通过标准 |
|--------|------|----------|
| 字段完整性 | 对比源文件与输出的字段集合 | 无遗漏字段 |
| 值一致性 | 随机抽取 5 条对比 | 关键字段值完全一致 |
| 格式合法性 | JSON 解析 / CSV 列数检查 | 无解析错误 |
| 编码正确性 | 检查中文字符 | 无乱码 |

### 3.3 输出规范

**JSON 输出示例：**

```json
[
  {
    "id": "001",
    "title": "示例文档",
    "content": "正文内容...",
    "source": "./input/sample.md",
    "processed_at": "2025-01-15T10:30:00Z",
    "confidence": 0.95
  }
]
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 条目唯一标识 |
| `title` | string | 是 | 文档标题 |
| `content` | string | 是 | 提取的正文内容 |
| `source` | string | 是 | 源文件路径或 URL |
| `processed_at` | datetime | 是 | 处理时间戳 |
| `confidence` | float | 否 | 提取置信度（0-1） |

---

## 四、置信度门控

### 4.1 占位符规则

当信息不足时，**禁止编造**，使用以下占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 字段缺失 | `[需核实:字段名]` | `"author": "[需核实:author]"` |
| 值不确定 | `[需核实:原值]` | `"date": "[需核实:2023-xx-xx]"` |
| 内容截断 | `[需核实:内容不完整]` | `"content": "前半部分...[需核实:内容不完整]"` |

### 4.2 置信度分级

| 置信度 | 含义 | 处理方式 |
|--------|------|----------|
| 0.9-1.0 | 高置信，字段完整且匹配 | 直接输出 |
| 0.7-0.9 | 中置信，部分字段需人工确认 | 输出并标注 `confidence` 值 |
| 0.4-0.7 | 低置信，存在较多不确定 | 输出占位符并提示人工复核 |
| <0.4 | 不可用 | 拒绝输出，提示重新提供输入 |

### 4.3 门控触发条件

```text
IF 输入文件为空 OR 文件格式不支持 THEN
    输出错误码 E1001，不执行转换
IF URL 返回 404/403 THEN
    输出错误码 E2001，不执行抓取
IF 提取字段缺失超过 30% THEN
    输出占位符，标记低置信度
IF 源文件编码非 UTF-8 THEN
    尝试转码，失败则输出错误码 E3001
```

---

## 五、错误码体系

### 5.1 错误码速查表

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E1001 | 输入文件为空 | "未检测到有效输入，请检查文件是否为空" | 1. 确认文件大小 >0；2. 检查文件权限 |
| E1002 | 文件格式不支持 | "仅支持 txt/md/csv/json/html 格式" | 1. 转换文件格式；2. 提供支持的格式 |
| E1003 | 文件命名不规范 | "文件名含空格或特殊字符，请重命名" | 1. 重命名为 `^[a-zA-Z0-9_\-\.]+$` 格式 |
| E2001 | URL 不可访问 | "目标 URL 返回 404/403，无法抓取" | 1. 检查 URL 拼写；2. 确认公开可访问 |
| E2002 | URL 内容为空 | "页面无正文内容，可能为 JS 渲染页面" | 1. 尝试静态版本；2. 手动复制内容 |
| E3001 | 编码错误 | "文件编码非 UTF-8，转码失败" | 1. 用 `iconv` 转码；2. 重新导出为 UTF-8 |
| E4001 | 输出目录不可写 | "输出目录无写入权限" | 1. 修改目录权限；2. 指定其他输出路径 |
| E5001 | 批量执行中断 | "批量处理中途失败，已停止" | 1. 查看日志定位失败文件；2. 单独处理该文件 |

### 5.2 错误处理流程

```text
遇到错误 → 记录错误码和上下文 → 输出提示话术 → 给出修正步骤
         ↓
    错误可自动修复？ → 是 → 自动修复并继续
         ↓ 否
    终止当前任务，保留已处理结果
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 跳过试运行直接批量 | 直接对 100 个文件执行批量，发现格式全错 | 先用 1 个样本验证，确认后再批量 |
| 覆盖原始文件 | 输出直接写入源文件路径 | 输出到独立目录，保留源文件备份 |
| 忽略置信度标记 | 直接使用含 `[需核实]` 的输出 | 人工复核所有占位符字段 |
| 不校验编码 | 中文乱码仍继续处理 | 先确认 UTF-8 编码，乱码先转码 |
| 一次处理超大文件 | 对 1GB 文件直接解析导致内存溢出 | 分块处理或先截取样本 |

### 6.2 反模式示例

**反模式：** 用户提供 50 个文件，直接执行 `memstack batch ./input/`，未先试运行。

**后果：** 50 个文件全部输出，但字段映射错误，需全部重新处理。

**正确做法：**

```bash
# 先处理 1 个文件
memstack process ./input/file01.md --output ./output/file01.json
# 检查字段
cat ./output/file01.json
# 确认无误后批量
memstack batch ./input/ --output ./output/
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```text
1. 放文件 → 2. 试运行 → 3. 批量 → 4. 校验
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「能力边界」了解能做什么
2. 按「标准流程」步骤 1-2 完成单文件处理
3. 查看「输出规范」确认结果格式
4. 遇到问题查「错误码体系」

#### 进阶路径（熟练用户）

1. 自定义字段映射（修改配置）
2. 批量处理 + 定时任务
3. 集成到 CI/CD 流程
4. 扩展支持自定义格式

### 7.3 配置参数详解

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_file_size` | int | 10MB | 单文件大小上限 |
| `timeout` | int | 30s | URL 抓取超时时间 |
| `retry_count` | int | 3 | 失败重试次数 |
| `encoding` | string | `utf-8` | 默认编码 |
| `field_mapping` | object | `{}` | 自定义字段映射规则 |

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. **合法使用**：使用者须确保输入内容合法合规，不得使用本 Skill 处理违法信息或侵犯第三方权益的内容。
3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **内容准确性**：本 Skill 的输出结果仅供学习参考，使用者须自行核实关键信息。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

MIT License

Copyright (c) 2025 林默

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
