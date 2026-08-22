---
slug: motion-skills
name: motion-skills
displayName: 动效设计 数据转化 批量生成
description: 将数据、文件或URL转化为结构化动效设计结果，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["motion-skills", "动效设计", "动画生成", "视觉叙事", "动态图形", "动效转化", "动态设计"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# motion-skills 动效设计转化 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据转结构 | 将 CSV、JSON、Excel 等数据文件转换为动效设计所需的结构化字段 | 将用户行为数据转为动画时间轴参数 |
| 文件转设计 | 将图片、音频、视频等素材文件映射为动效设计中的元素属性 | 将背景图转为场景层，音频转为节奏参考 |
| URL 转素材 | 提取 URL 指向的资源（需可公开访问）并转化为设计输入 | 将公开的 JSON API 数据转为图表动画数据源 |
| 批量处理 | 对同一目录下多个文件执行统一转化流程 | 一次处理 50 个产品展示图，生成统一动效规格 |
| 置信度标注 | 对每个输出字段标注可信程度，低置信度字段明确提示 | 字段 `duration` 置信度 0.72，提示人工复核 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不生成最终视频 | 本 Skill 输出的是结构化设计规格，不是渲染好的动画文件 |
| 不处理私有/加密数据 | 无法访问需要登录、鉴权或加密的 URL 资源 |
| 不推断缺失语义 | 输入中未明确表达的意图，不会自动猜测补充 |
| 不执行设计决策 | 不代替设计师判断美学取向，只提供参数化建议 |

### 1.3 适用对象

- 需要将数据快速转化为动效原型的交互设计师
- 需要批量生成动效规格说明的动效团队
- 需要将素材文件系统化整理为动效资产库的开发者

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发：`motion-skills`、`动效设计`、`动画生成`、`视觉叙事`、`动态图形`
- 补充触发：`动效转化`、`动态设计`、`动效规格`

### 2.2 场景映射表

| 用户说（大白话） | 实际意图 | 触发动作 |
|------------------|----------|----------|
| "帮我把这个 Excel 变成动画参数" | 数据转动效结构 | 读取 Excel → 映射字段 → 输出 JSON 规格 |
| "这堆图片能做成动效吗？" | 文件批量转设计 | 扫描目录 → 识别文件类型 → 生成元素清单 |
| "这个链接里的数据能用来做动画吗？" | URL 转素材 | 请求 URL → 解析内容 → 转为设计输入 |
| "帮我检查一下这批动效参数对不对" | 校验已有输出 | 对比源数据 → 标注置信度 → 输出校验报告 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入文件 | 与 Skill 运行目录一致，命名规范统一（如 `data_01.csv`、`data_02.csv`） | 执行 `ls` 确认文件存在 |
| 文件格式 | 支持 CSV、JSON、XLSX、PNG、JPG、MP3、MP4、公开 URL | 执行 `file` 命令确认格式 |
| 网络权限 | 若使用 URL 输入，需确认网络可访问 | 执行 `curl -I <url>` 验证 |
| 输出目录 | 默认输出到 `./output/`，需提前创建或授权自动创建 | 检查目录权限 |

### 3.2 执行步骤

#### 步骤 1：准备输入

```bash
# 将待处理文件放入同一目录，例如 ./input/
mkdir -p input output
cp /path/to/your/files/* ./input/
ls -la ./input/
```

确认文件命名规范一致，例如统一使用 `data_序号.扩展名` 格式。

#### 步骤 2：单样本试运行

```bash
motion-skills --input ./input/data_01.csv --output ./output/result_01.json
```

检查输出文件 `result_01.json`，确认以下字段完整：

```json
{
  "source": "data_01.csv",
  "elements": [
    {
      "id": "el_001",
      "type": "bar_chart",
      "data_binding": "column:revenue",
      "animation": {
        "duration": 2.5,
        "easing": "easeInOut",
        "delay": 0.3
      },
      "confidence": 0.95
    }
  ],
  "metadata": {
    "processed_at": "2025-01-15T10:30:00Z",
    "total_elements": 1
  }
}
```

#### 步骤 3：批量执行

```bash
# 对全量数据执行
motion-skills --input ./input/ --output ./output/ --batch

# 保留原始文件备份
cp -r ./input/ ./backup_input_$(date +%Y%m%d)/
```

批量执行时，每个输入文件对应一个输出文件，命名规则为 `result_<原文件名>.json`。

#### 步骤 4：校验结果

```bash
# 抽查输出条目，核对关键字段
motion-skills --verify --input ./output/ --source ./input/
```

校验规则：

| 校验项 | 规则 | 通过标准 |
|--------|------|----------|
| 字段完整性 | 每个元素必须包含 `id`、`type`、`animation` | 100% 元素通过 |
| 数据一致性 | 输出中的 `data_binding` 必须能在源文件中找到对应列/键 | 抽查 10% 条目 |
| 置信度阈值 | 所有字段置信度 ≥ 0.6 | 低于阈值需人工复核 |

---

## 四、置信度门控机制

### 4.1 置信度分级

| 置信度区间 | 含义 | 处理方式 |
|------------|------|----------|
| 0.9 - 1.0 | 高置信度，源数据明确 | 直接使用 |
| 0.7 - 0.89 | 中置信度，存在部分推断 | 输出时标注建议复核字段 |
| 0.5 - 0.69 | 低置信度，源数据模糊 | 输出 `[需核实:字段名]` 占位 |
| < 0.5 | 无法判断 | 拒绝输出该字段，提示补充信息 |

### 4.2 占位符使用规范

当信息不足时，使用以下格式输出占位符：

```json
{
  "animation": {
    "duration": "[需核实:duration]",
    "easing": "easeInOut"
  }
}
```

**禁止**：编造不存在的数值、猜测用户意图、用默认值替代缺失信息。

### 4.3 置信度计算依据

| 因素 | 权重 | 说明 |
|------|------|------|
| 源数据明确性 | 40% | 字段是否有明确对应值 |
| 格式匹配度 | 30% | 输入格式与目标字段类型的匹配程度 |
| 上下文一致性 | 20% | 与同批次其他元素的逻辑一致性 |
| 历史模式 | 10% | 与过往处理模式的相似度 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定文件，请检查路径是否正确" | 1. 执行 `ls` 确认文件路径；2. 修正路径后重试 |
| `E002` | 文件格式不支持 | "当前文件格式不在支持列表中，请转换为 CSV/JSON/XLSX/PNG/JPG/MP3/MP4" | 1. 使用转换工具转换格式；2. 重新执行 |
| `E003` | URL 无法访问 | "无法访问该 URL，请确认链接公开可访问" | 1. 用浏览器打开验证；2. 检查网络；3. 更换可访问链接 |
| `E004` | 输出目录无权限 | "无法写入输出目录，请检查目录权限" | 1. 执行 `chmod +w ./output/`；2. 或更换输出目录 |
| `E005` | 批量处理中断 | "批量处理在第 N 个文件处中断，请检查该文件格式" | 1. 定位中断文件；2. 单独处理该文件；3. 跳过或修复后继续 |
| `E006` | 置信度过低 | "多个字段置信度低于 0.5，无法生成可靠输出" | 1. 检查源数据完整性；2. 补充缺失信息；3. 重新执行 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑位 | 错误做法 | 正确做法 |
|------|----------|----------|
| 跳过试运行 | 直接批量处理全部文件 | 先单样本试运行，确认输出格式后再批量 |
| 忽略置信度 | 直接使用低置信度输出 | 对置信度 < 0.7 的字段进行人工复核 |
| 覆盖原始文件 | 在原始文件上直接修改 | 保留备份，输出到独立目录 |
| 混合命名规范 | 文件名格式不统一导致解析错误 | 统一命名规范，如 `data_序号.扩展名` |
| 忽略错误码 | 遇到错误直接跳过继续执行 | 按错误码提示修正后继续 |

### 6.2 反模式对照表

| 反模式 | 表现 | 推荐替代 |
|--------|------|----------|
| 猜测补全 | 源数据缺失时自行编造数值 | 使用 `[需核实:字段]` 占位 |
| 一刀切 | 所有文件用同一套参数处理 | 根据文件类型和内容调整参数 |
| 无验证 | 输出后不检查直接使用 | 执行 `--verify` 校验步骤 |
| 忽略上下文 | 只看单个文件不看整体批次 | 批量执行后整体抽查一致性 |

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
1. 放入文件 → 2. 单样本试运行 → 3. 批量执行 → 4. 校验结果
```

### 7.2 新手路径（首次使用）

1. 阅读本文档「能力边界速查卡」了解能做什么
2. 按「标准执行流程」步骤 1-2 完成单样本试运行
3. 对照「输出规范」检查输出 JSON 结构
4. 确认无误后执行批量处理

### 7.3 进阶路径（熟练使用）

1. 深入理解「置信度门控机制」，学会处理低置信度场景
2. 掌握「错误码体系」，能快速定位和修复问题
3. 自定义输出模板，适配特定项目需求
4. 结合 CI/CD 流程，将批量处理集成到自动化管线

---

## 八、输出规范详解

### 8.1 输出文件结构

```json
{
  "schema_version": "1.0",
  "source_file": "data_01.csv",
  "generated_at": "2025-01-15T10:30:00Z",
  "elements": [
    {
      "id": "el_001",
      "type": "bar_chart",
      "data_binding": {
        "field": "revenue",
        "source_type": "column"
      },
      "animation": {
        "duration": 2.5,
        "easing": "easeInOut",
        "delay": 0.3,
        "loop": false
      },
      "style": {
        "color": "#4A90D9",
        "opacity": 0.9
      },
      "confidence": 0.95
    }
  ],
  "warnings": [
    {
      "code": "W001",
      "message": "字段 'revenue' 置信度 0.72，建议人工复核",
      "field": "revenue"
    }
  ]
}
```

### 8.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `schema_version` | string | 是 | 输出格式版本号 |
| `source_file` | string | 是 | 源文件名 |
| `generated_at` | string | 是 | 生成时间（ISO 8601） |
| `elements[].id` | string | 是 | 元素唯一标识 |
| `elements[].type` | string | 是 | 元素类型（bar_chart/line_chart/image/audio/video） |
| `elements[].data_binding` | object | 是 | 数据绑定关系 |
| `elements[].animation` | object | 是 | 动画参数 |
| `elements[].style` | object | 否 | 样式参数 |
| `elements[].confidence` | number | 是 | 置信度（0-1） |
| `warnings[]` | array | 否 | 警告信息列表 |

### 8.3 支持的元素类型

| 类型 | 适用场景 | 必填动画参数 |
|------|----------|--------------|
| `bar_chart` | 柱状图数据 | duration, easing |
| `line_chart` | 折线图数据 | duration, easing, delay |
| `image` | 图片素材 | duration, opacity |
| `audio` | 音频素材 | duration, volume |
| `video` | 视频素材 | duration, loop |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用条款**

1. 本 Skill 仅供学习参考，使用者应自行承担使用本 Skill 产生的全部责任。
2. 使用者不得对本 Skill 进行反向工程、反编译或试图提取源代码。
3. 使用者应确保输入数据的合法性和合规性，不得使用本 Skill 处理违法违规内容。
4. 本 Skill 的输出结果仅供参考，不构成任何形式的专业建议或保证。
5. 使用者应自行验证输出结果的准确性和适用性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 林墨研

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

*文档版本：1.0.0 | 最后更新：2025-01-15*
