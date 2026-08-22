---
slug: foundationmodelsocr
name: foundationmodelsocr
displayName: 票据解析 字段抽取 置信标注
description: 将票据或PDF转为结构化字段，含置信度标注与批量处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规工作室
agent_created: true
trigger_words: ["识别", "PDF识别", "文字提取", "OCR", "票据解析", "发票识别", "文档结构化", "批量扫描"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 票据与PDF结构化字段抽取 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单文件识别 | 对一张票据或一个PDF文件执行字段抽取 | 增值税发票、出租车票、银行回单 |
| 批量处理 | 对同一目录下多个文件依次执行识别 | 一个文件夹内50张发票 |
| 字段结构化 | 输出JSON格式的键值对字段 | `{"发票号码": "12345678"}` |
| 置信度标注 | 每个字段附带0~1的置信度分数 | `{"confidence": 0.97}` |
| 自检模式 | 验证环境依赖与模型可用性 | `--selftest` 参数 |
| 版本查询 | 输出当前Skill版本号 | `--version` 参数 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持手写体识别 | 仅支持印刷体、机打字体 |
| 不支持旋转/倾斜矫正 | 输入文件需正向摆放，倾斜超过15度将报错 |
| 不支持多页PDF合并输出 | 多页PDF仅抽取第一页，后续页忽略 |
| 不保证100%字段完整 | 缺失字段以 `[需核实:字段名]` 占位 |
| 不执行任何财务计算 | 只抽取字段，不做金额汇总或校验 |

### 1.3 适用对象

- 财务人员：发票信息录入前的预抽取
- 行政人员：纸质单据电子化归档
- 开发人员：作为OCR预处理模块嵌入业务系统
- 不适用于：法律合同全文理解、复杂表格结构还原

---

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 场景描述 |
|--------|----------|
| 识别 / OCR | 用户说"帮我识别这张发票" |
| PDF识别 | 用户说"把这个PDF里的文字提出来" |
| 文字提取 | 用户说"提取这张单子上的所有文字" |
| 票据解析 | 用户说"解析一下这张出租车票" |
| 发票识别 | 用户说"识别这张增值税发票的号码和金额" |
| 文档结构化 | 用户说"把这几张回单变成结构化数据" |
| 批量扫描 | 用户说"把这个文件夹里的所有票据都处理了" |

### 2.2 大白话场景映射

| 用户原话 | Skill 实际动作 |
|----------|----------------|
| "帮我看看这张票上写了啥" | 执行单文件识别，输出全部字段 |
| "这堆PDF能转成表格吗" | 执行批量处理，输出JSON数组 |
| "这个号码是多少" | 执行识别，只返回指定字段 |
| "识别结果准不准" | 执行识别，附带置信度分数 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件格式 | `.jpg`, `.png`, `.pdf`（单页） |
| 文件大小 | 单文件 ≤ 10MB |
| 文件命名 | 建议统一前缀，如 `invoice_001.jpg` |
| 目录结构 | 所有待处理文件放在同一目录，无子目录 |
| 环境依赖 | Python 3.8+，已安装 `pytesseract` 与 `Pillow` |

### 3.2 执行步骤（分步编号）

1. **准备输入目录**
   - 创建文件夹 `input/`，将所有待识别文件放入其中
   - 确认文件命名无重复，无空格或特殊字符

2. **单样本试运行**
   - 执行命令：`python skill.py 识别 input/invoice_001.jpg`
   - 检查输出JSON中字段是否完整、格式是否正确
   - 若字段缺失严重，检查图片清晰度与倾斜角度

3. **批量执行**
   - 执行命令：`python skill.py 批量扫描 input/`
   - 输出结果保存至 `output/result.json`
   - 原始文件自动备份至 `backup/` 目录（时间戳命名）

4. **结果校验**
   - 随机抽取3~5条输出，与源文件人工比对
   - 核对关键字段：发票号码、金额、日期
   - 若置信度低于0.6的字段超过20%，建议重新扫描文件

### 3.3 输出规范

```json
{
  "file": "invoice_001.jpg",
  "timestamp": "2025-01-15T10:30:00Z",
  "fields": [
    {"name": "发票号码", "value": "12345678", "confidence": 0.98},
    {"name": "开票日期", "value": "2025-01-10", "confidence": 0.95},
    {"name": "价税合计", "value": "¥1,234.56", "confidence": 0.89}
  ],
  "warnings": ["字段'收款人'缺失，已置为[需核实:收款人]"]
}
```

---

## 四、置信度门控机制

### 4.1 置信度阈值

| 置信度区间 | 处理策略 |
|------------|----------|
| 0.90 ~ 1.00 | 直接输出，无需人工复核 |
| 0.70 ~ 0.89 | 输出字段，附带黄色警告标记 |
| 0.50 ~ 0.69 | 输出字段，附带橙色警告标记，建议人工核对 |
| < 0.50 | 不输出具体值，替换为 `[需核实:字段名]` |

### 4.2 缺失字段处理

- 当模型无法从图像中定位到某个字段时，输出 `[需核实:字段名]`
- 禁止使用空字符串或 `null` 代替
- 禁止根据上下文推测补全字段值

### 4.3 示例

```json
{"name": "开户行", "value": "[需核实:开户行]", "confidence": 0.0}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径与文件名 |
| `E002` | 格式不支持 | "仅支持jpg/png/pdf格式" | 转换文件格式后重试 |
| `E003` | 文件过大 | "文件超过10MB限制" | 压缩图片或拆分PDF |
| `E004` | 图像倾斜 | "图像倾斜超过15度，无法识别" | 手动旋转图片至正向 |
| `E005` | 无可用文本 | "未检测到可识别文本" | 检查图片清晰度或重拍 |
| `E006` | 批量目录为空 | "目录下无待处理文件" | 确认文件已放入目录 |
| `E007` | 依赖缺失 | "缺少OCR引擎，请运行--selftest" | 执行 `python skill.py --selftest` |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 批量处理前不试跑 | 直接对100个文件执行批量识别，结果全错 | 先用1个样本试跑，确认字段映射正确 |
| 忽略置信度 | 置信度0.4的字段直接入库 | 按阈值规则处理，低置信度字段标记待核 |
| 覆盖原始文件 | 批量处理后删除原始文件 | 保留 `backup/` 目录，至少保留7天 |
| 多页PDF当单页处理 | 直接识别多页PDF，只得到第一页结果 | 先拆分PDF为单页，再逐页识别 |
| 手写体票据强行识别 | 手写发票直接跑OCR，输出乱码 | 确认票据为印刷体，否则改用人工录入 |

---

## 七、渐进式披露阅读路径

### 7.1 速查卡（30秒上手）

```
1. 文件放 input/ 目录
2. 跑单样本：python skill.py 识别 input/test.jpg
3. 看输出JSON，确认字段
4. 跑批量：python skill.py 批量扫描 input/
5. 结果在 output/result.json
```

### 7.2 新手路径（首次使用）

- 阅读「一、能力边界」了解限制
- 阅读「三、标准执行流程」按步骤操作
- 遇到问题查「五、错误码体系」

### 7.3 进阶路径（深度集成）

- 阅读「四、置信度门控机制」设计业务规则
- 阅读「六、FAQ 反模式」规避常见错误
- 参考输出JSON结构，对接下游系统

---

## 八、参数速查表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--selftest` | 布尔 | 否 | `false` | 检查环境依赖 |
| `--version` | 布尔 | 否 | `false` | 输出版本号 |
| `--output` | 字符串 | 否 | `output/` | 结果输出目录 |
| `--confidence` | 浮点 | 否 | `0.5` | 最低置信度阈值 |
| `--backup` | 布尔 | 否 | `true` | 是否备份原始文件 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、业务决策后果及合规风险。
2. **禁止反向工程**：不得对本 Skill 的源代码、模型权重、输出逻辑进行反向工程、反编译或破解。
3. **数据安全**：使用者需自行确保输入文件不包含敏感个人信息，因上传文件导致的数据泄露由使用者自行负责。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

### MIT License

```
MIT License

Copyright (c) 2025 原创作者（自持版权）

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证效果。*
