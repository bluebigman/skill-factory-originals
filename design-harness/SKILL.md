---
slug: design-harness
name: design-harness
displayName: 设计稿转前端 原型验证 交互测试
description: 将设计稿或需求转化为可验证的前端原型，提供结构化输出与置信度提示。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["design harness", "UI设计", "前端原型", "交互验证", "设计稿转前端", "原型测试", "界面还原"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# design-harness Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 设计稿解析 | 读取 PNG/Sketch/Figma 导出图或需求文档，提取布局、组件、交互点 | 结构化设计描述 |
| 原型代码生成 | 生成 HTML/CSS/JS 单文件原型，或 React/Vue 组件代码 | 可运行的前端代码 |
| 交互逻辑标注 | 识别按钮、表单、跳转等交互元素，标注触发条件与反馈 | 交互清单 |
| 批量转换 | 对同一目录下多个设计稿批量生成原型 | 多文件输出 + 索引清单 |
| 自检与校验 | 运行 `--selftest` 检查输出完整性，比对源文件关键字段 | 校验报告 |

### 1.2 不能做什么

- 不能直接读取 Figma/Sketch 私有格式的二进制源文件（需先导出为图片或 JSON）。
- 不能生成后端接口或数据库逻辑，仅限前端表现层。
- 不能保证像素级还原（受源文件清晰度与标注完整度限制）。
- 不能处理超过 50 个页面的超大项目（建议分批执行）。

### 1.3 适用对象

- 前端开发工程师：快速将设计稿转为可交互原型，用于技术评审。
- UI/UX 设计师：验证设计稿在浏览器中的实际表现。
- 产品经理：将需求文档转化为可点击的演示原型。
- 测试工程师：生成原型用于交互流程验证。

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一短语即可激活本 Skill：

- `design harness`
- `UI设计` / `设计稿转前端`
- `前端原型` / `交互验证`
- `原型测试` / `界面还原`

### 2.2 场景映射表

| 你说的话（大白话） | Skill 实际执行内容 |
|-------------------|-------------------|
| "帮我把这张首页设计图变成能点的网页" | 解析设计稿 → 生成 HTML 原型 → 标注可点击区域 |
| "这个需求文档能做成原型吗？" | 提取需求中的页面描述 → 生成线框原型 |
| "我这有 20 张设计图，一起转了吧" | 批量模式：逐张转换并输出索引清单 |
| "检查一下上次生成的原型对不对" | 运行 `--selftest` 校验输出与源文件一致性 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件格式 | PNG/JPG/PDF（设计稿）或 MD/TXT（需求文档） | 文件扩展名 |
| 命名规范 | 文件名为 `页面名_版本号.扩展名`，如 `home_v2.png` | 目视检查 |
| 目录结构 | 所有待处理文件放在同一目录，无子文件夹 | `ls` 命令 |
| 文件数量 | 单批不超过 50 个 | 文件计数 |

### 3.2 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。若文件名不含版本号，自动补 `_v1`。

2. **试运行**：先用单个样本执行，核对输出字段与格式。命令示例：
   ```bash
   design-harness --input ./samples/home_v2.png --output ./output/
   ```
   检查输出目录中是否生成 `home_v2.html` 与 `home_v2_meta.json`。

3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。命令示例：
   ```bash
   design-harness --input ./all_designs/ --output ./output/ --batch
   ```
   批量模式下自动在 `./output/_backup/` 中保留源文件副本。

4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。运行：
   ```bash
   design-harness --selftest --input ./output/
   ```
   该命令会比对每个 HTML 中的页面标题、组件数量与源文件元数据。

### 3.3 输出规范

每个设计稿生成两个文件：

| 文件 | 内容 | 命名规则 |
|------|------|----------|
| `*.html` | 可运行的原型代码（含内联 CSS/JS） | 与源文件同名 |
| `*_meta.json` | 结构化元数据（页面名、组件清单、交互点、置信度） | 源文件名 + `_meta` |

`_meta.json` 格式示例：

```json
{
  "source_file": "home_v2.png",
  "page_name": "首页",
  "components": ["导航栏", "轮播图", "商品卡片", "底部按钮"],
  "interactions": [
    {"element": "nav-menu", "action": "click", "target": "#/products"}
  ],
  "confidence": 0.87,
  "warnings": ["轮播图指示器颜色不明确，已使用默认色"]
}
```

---

## 四、置信度门控

### 4.1 置信度评分规则

| 评分范围 | 含义 | 处理方式 |
|----------|------|----------|
| 0.9 - 1.0 | 高置信度，所有关键元素清晰可辨 | 直接输出 |
| 0.7 - 0.89 | 中等置信度，部分细节模糊 | 输出并在 `warnings` 中列出模糊项 |
| 0.5 - 0.69 | 低置信度，关键结构缺失 | 输出占位符 + 明确提示 |
| < 0.5 | 无法识别 | 拒绝生成，返回错误码 E401 |

### 4.2 占位符规则

当信息不足时，使用 `[需核实:字段名]` 格式占位，**绝不编造**。例如：

- 图片中按钮文字模糊 → `[需核实:按钮文字]`
- 设计稿未标注跳转地址 → `[需核实:跳转URL]`
- 颜色色值无法确定 → `[需核实:主色调色值]`

占位符会同时出现在 HTML 代码注释与 `_meta.json` 的 `warnings` 字段中。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E101 | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径与文件名 |
| E102 | 格式不支持 | "仅支持 PNG/JPG/PDF/MD/TXT 格式" | 转换文件格式后重试 |
| E201 | 命名不规范 | "文件名需包含页面名与版本号" | 重命名为 `页面名_v版本号.扩展名` |
| E301 | 批量模式目录为空 | "目录中未找到可处理的文件" | 确认文件已放入指定目录 |
| E401 | 置信度过低 | "设计稿质量过低，无法生成原型" | 更换高清设计稿或补充需求文档 |
| E501 | 输出目录无写入权限 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |
| E601 | 批量执行中断 | "批量执行在第 N 个文件处中断" | 查看日志，修复后从第 N+1 个继续 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 像素级还原执念 | 花大量时间手动调整 CSS 追求 1:1 还原 | 接受 90% 还原度，剩余用占位符标注 |
| 忽略交互标注 | 只生成静态页面，不标注可点击区域 | 在 HTML 中为每个交互元素添加 `data-action` 属性 |
| 批量执行不试跑 | 直接对 50 个文件批量执行，结果全错 | 先跑 1 个样本，确认格式后再批量 |
| 覆盖原始文件 | 输出直接写入源文件目录 | 使用独立输出目录，保留源文件备份 |
| 置信度不足仍硬编 | 模糊区域随意猜测填充内容 | 使用 `[需核实:字段]` 占位，交由人工确认 |

### 6.2 反模式示例

**错误做法**：
```
用户：帮我把这张图转成网页
AI：好的，按钮文字看不清，我猜是"立即购买"
```

**正确做法**：
```
用户：帮我把这张图转成网页
AI：按钮文字区域模糊，已使用 [需核实:按钮文字] 占位，请确认实际文案
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 同一目录，命名规范
2. 试运行 → 单文件测试
3. 批量跑 → 全量执行
4. 查结果 → 抽查 meta 文件
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围。
2. 准备 1 个测试文件，按「标准流程」步骤 1-2 执行。
3. 查看生成的 HTML 与 `_meta.json`，理解输出结构。
4. 遇到问题查「错误码体系」。

### 7.3 进阶路径（熟练用户）

1. 直接进入批量模式，配合 `--selftest` 做全量校验。
2. 自定义输出模板：在配置文件中修改 HTML 骨架。
3. 集成 CI/CD：将 `design-harness` 命令接入自动化流水线。
4. 处理复杂交互：在需求文档中使用特定标记（如 `[交互:点击跳转]`）增强识别精度。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. 本 Skill 提供的所有输出结果（包括但不限于代码、文档、设计描述）仅供学习、研究和内部评估使用。
2. 使用者应自行承担因使用本 Skill 产生的全部责任。对于因输出结果不准确、不完整或存在缺陷而导致的任何直接或间接损失，Skill 作者不承担任何责任。
3. 使用者不得对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码（除非适用法律允许）。
4. 使用者不得将本 Skill 用于任何违反法律法规、侵犯第三方权益或破坏系统安全的活动。
5. 本 Skill 的输出结果不构成任何形式的专业建议或保证，使用者应结合自身判断进行决策。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 Lin Chen

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

*文档版本：1.0.0 | 最后更新：2024 年 12 月*
