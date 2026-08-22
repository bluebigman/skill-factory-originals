---
slug: subtlety
name: subtlety
displayName: 数据源转换 格式迁移 批量处理
description: 将SVN、RSS、hAtom等数据源转换为Atom或结构化格式，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["subtlety", "SVN转RSS", "hAtom转Atom", "数据源转换", "格式迁移", "批量转换"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# subtlety — 数据源格式转换与结构化输出 Skill

## 一、能力边界：一页纸速查卡

本 Skill 用于将非 Atom 数据源（SVN 日志、RSS 2.0、hAtom 微格式等）转换为 Atom 1.0 或自定义结构化 JSON 格式。支持单文件试运行与批量处理，并对每条输出记录附加置信度标记。

| 能力维度 | 支持 | 不支持 |
|---------|------|--------|
| 输入格式 | SVN 命令行日志、RSS 2.0 XML、hAtom 嵌入 HTML | 二进制文件、加密数据流、数据库直连 |
| 输出格式 | Atom 1.0 XML、结构化 JSON（自定义 schema） | 非标准 XML、CSV 导出 |
| 处理模式 | 单文件试运行、目录批量处理 | 实时流式转换、分布式并行 |
| 附加功能 | 置信度标注、字段缺失占位、原始文件备份 | 自动纠错、语义推断、跨语言翻译 |
| 适用对象 | 版本库迁移、内容聚合、博客平台数据整理 | 实时数据管道、高吞吐日志处理 |

**适用对象**：需要将 SVN 提交历史发布为订阅源、将旧 RSS 升级为 Atom、或从 HTML 页面提取 hAtom 条目的开发者和内容运维人员。

---

## 二、触发方式：场景映射表

当你的任务涉及以下场景时，可使用本 Skill：

| 触发词/场景 | 大白话描述 | 使用建议 |
|------------|-----------|---------|
| SVN转RSS | 把 SVN 仓库的提交记录变成可订阅的 RSS 或 Atom 源 | 先导出 svn log --xml 格式 |
| hAtom转Atom | 从网页中提取 hAtom 微格式内容，输出标准 Atom | 确保 HTML 结构完整，hAtom class 命名正确 |
| 数据源转换 | 泛指各类非 Atom 数据转为 Atom 或结构化格式 | 先确认输入格式，再选择对应转换路径 |
| 格式迁移 | 旧系统数据迁移到新内容平台 | 建议先做小样本验证 |
| 批量处理 | 一次转换多个文件或整个目录 | 务必先跑单样本试运行 |

---

## 三、标准流程：从准备到校验

### 3.1 前置条件

- 输入文件已放置在统一目录下，命名遵循一致规则（如 `*.xml`、`*.html`、`svn_log_*.txt`）。
- 已确认输入数据的编码格式（UTF-8 无 BOM 优先）。
- 已安装 Python 3.8+ 或 Node.js 14+（根据实现方式选择）。
- 已备份原始文件（建议复制到 `./backup/` 目录）。

### 3.2 执行步骤

1. **环境检查**：运行 `subtlety --version` 确认工具可用；若未安装，先执行安装脚本。
2. **单样本试运行**：
   ```bash
   subtlety SVN转RSS --input ./sample/svn_log.xml --output ./output/sample_atom.xml
   ```
   检查输出文件中的 `entry` 数量、`title`、`updated` 字段是否与源数据一致。
3. **参数调整**（可选）：
   | 参数 | 默认值 | 说明 |
   |------|--------|------|
   | `--confidence-threshold` | 0.7 | 低于此值的条目将标记 `low-confidence` |
   | `--output-format` | atom | 可选 `atom` 或 `json` |
   | `--include-empty-fields` | false | 是否保留缺失字段的占位符 |
4. **批量执行**：
   ```bash
   subtlety 数据源转换 --input ./data/ --output ./converted/ --batch
   ```
   批量模式会自动遍历目录下所有匹配文件，并生成 `conversion_report.json` 汇总报告。
5. **结果校验**：
   - 抽查 3-5 个输出文件，核对关键字段（`id`、`published`、`content`）与源数据一致。
   - 检查 `conversion_report.json` 中的错误统计，确认无 `fatal` 级别错误。

### 3.3 输出规范

- **Atom 格式**：符合 RFC 4287 规范，包含 `feed`、`entry`、`id`、`title`、`updated` 等必需元素。
- **JSON 格式**：顶层为对象，包含 `meta`（转换时间、工具版本）和 `items`（条目数组）。
- **置信度标注**：每个条目包含 `confidence` 字段（0.0-1.0），低于阈值的条目在 `warnings` 中列出原因。

---

## 四、置信度门控：不编造，只标注

当输入数据存在以下情况时，输出对应占位符而非猜测值：

| 情况 | 输出行为 |
|------|---------|
| 缺少 `updated` 时间戳 | 输出 `[需核实:updated]`，置信度降至 0.3 |
| SVN 日志中无作者信息 | 输出 `[需核实:author]`，置信度降至 0.5 |
| hAtom 条目缺少 `entry-title` | 输出 `[需核实:title]`，置信度降至 0.2 |
| RSS 中 `link` 为相对路径 | 保留原值，添加 `warning: relative-url`，置信度 0.6 |

**原则**：任何无法从源数据直接确认的字段，一律使用占位符，绝不推测填充。

---

## 五、错误码体系：常见问题与修正

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 输入文件不存在 | "未找到指定文件，请检查路径" | 确认路径正确，文件是否已放入目录 |
| E002 | 输入格式无法识别 | "无法识别输入格式，支持 SVN/RSS/hAtom" | 检查文件扩展名和内容结构 |
| E003 | 输出目录无写入权限 | "输出目录不可写，请检查权限" | 修改目录权限或更换输出路径 |
| E004 | 批量处理中部分文件失败 | "批量处理完成，N 个文件失败，详见报告" | 查看 `conversion_report.json` 中的错误详情 |
| E005 | 置信度低于阈值 | "N 个条目置信度低于阈值，已标记" | 检查源数据质量，或调整 `--confidence-threshold` |
| E006 | 编码不兼容 | "文件编码非 UTF-8，转换可能失真" | 使用 `iconv` 或编辑器转换为 UTF-8 无 BOM |

---

## 六、FAQ 反模式：常见坑与正确姿势

| 常见坑（反模式） | 正确做法 |
|-----------------|---------|
| 直接批量处理全部文件，不做试运行 | 先跑单样本，确认字段映射正确后再批量 |
| 忽略置信度标注，直接使用全部输出 | 检查低置信度条目，手动核实后再发布 |
| 覆盖原始文件，不做备份 | 始终保留原始文件副本，批量处理前自动备份 |
| 依赖默认参数，不调整阈值 | 根据数据质量调整 `--confidence-threshold`（建议 0.6-0.8） |
| 混淆 RSS 2.0 与 Atom 1.0 的命名空间 | 确认输出格式，RSS 用 `<rss>` 根元素，Atom 用 `<feed>` |

---

## 七、渐进式披露：按需阅读路径

### 速查卡（30 秒上手）

1. 放文件 → 2. 跑单样本 → 3. 查输出 → 4. 批量跑 → 5. 看报告

### 新手路径（首次使用）

- 阅读「能力边界」了解适用范围。
- 按「标准流程」的步骤 1-3 完成一次试运行。
- 遇到问题查「错误码体系」对照修正。

### 进阶路径（深度使用）

- 研究「置信度门控」机制，自定义阈值与占位符规则。
- 阅读输出 JSON 的 schema，对接下游系统。
- 修改源码中的字段映射表，支持自定义输入格式。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 导致的任何数据丢失、格式错误或业务损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的源码进行反向工程、反编译或试图提取底层算法（除法律允许的范围外）。
3. **合规使用**：使用者需确保输入数据来源合法，输出内容不违反任何法律法规。
4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 格式工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证。*
