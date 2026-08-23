---
slug: oad
name: oad
displayName: 显微成像 自动化脚本 工作流编排
description: 面向ZEN Blue显微工作流的Python脚本工具集，助您高效编排自动化任务。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["oad", "Open Application Development", "ZEN Blue自动化", "显微脚本", "显微镜工作流", "显微成像编排", "自动化采集流程"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# oad — 显微成像自动化脚本工具集

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 脚本编排 | 将 ZEN Blue 中的重复性操作封装为可复用 Python 脚本 | 多批次样本采集、定时成像任务 |
| 参数批处理 | 支持对多组参数（如曝光时间、Z轴层数）进行循环控制 | 条件筛选实验、参数扫描 |
| 数据整理 | 自动规整输出文件命名与存放路径 | 大批量数据归档、后续分析前预处理 |
| 流程串联 | 将采集、保存、初步质检串联为一条自动化链路 | 无人值守的连续成像 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代 ZEN Blue 核心功能 | 本工具集仅做流程编排，不提供图像分析算法、重建算法等 ZEN 原生能力 |
| 不跨设备控制 | 仅面向 ZEN Blue 软件环境，不直接驱动显微镜硬件（需通过 ZEN 接口） |
| 不处理非标准输入 | 输入文件命名、目录结构需符合约定，否则脚本可能中断 |
| 不保证兼容所有版本 | 不同 ZEN Blue 版本接口可能有差异，使用前需验证 |

### 1.3 适用对象

- 使用 ZEN Blue 进行显微成像的科研人员
- 需要批量处理成像任务的实验助理
- 希望减少手动重复操作的实验室管理者

---

## 二、触发方式：场景映射表

| 触发词/短语 | 用户意图 | 建议动作 |
|-------------|----------|----------|
| "oad" / "Open Application Development" | 直接调用工具集 | 查看版本与自检：`oad --selftest` |
| "ZEN Blue自动化" | 希望自动化 ZEN 操作 | 提供脚本模板与参数说明 |
| "显微脚本" | 需要编写/修改脚本 | 给出脚本结构示例与调试建议 |
| "显微镜工作流" | 优化整体流程 | 推荐标准流程（见第四节） |
| "批量成像" / "自动采集" | 处理多组样本 | 引导至批量执行流程 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 软件环境 | ZEN Blue 已安装并激活 | 打开 ZEN Blue 主界面确认 |
| Python 环境 | Python 3.7+ 且已安装 oad 工具包 | 终端执行 `oad --version` |
| 输入文件 | 所有待处理文件位于同一目录 | 使用 `ls` 或资源管理器确认 |
| 命名规范 | 文件名遵循统一格式（如 `sample_001.tif`） | 目视检查或脚本校验 |

### 3.2 执行步骤（分步编号）

1. **准备输入目录**
   - 创建文件夹 `input/`，将全部待处理文件移入
   - 确认命名规范一致（建议格式：`[实验名]_[编号].[扩展名]`）

2. **单样本试运行**
   - 选取一个代表性文件，执行：
     ```bash
     oad run --input input/sample_001.tif --output output_test/
     ```
   - 检查输出目录中的文件字段与格式是否符合预期

3. **核对输出规范**
   - 输出文件命名规则：`[原文件名]_processed.[扩展名]`
   - 输出元数据（如时间戳、参数记录）写入 `output_test/metadata.json`
   - 若字段缺失或格式错误，检查脚本参数设置

4. **全量批量执行**
   - 确认试运行无误后，执行：
     ```bash
     oad run --input input/ --output output/ --batch
     ```
   - 执行前备份原始文件：`cp -r input/ backup_input/`

5. **结果校验**
   - 随机抽取 5-10% 输出文件，核对关键字段（如文件名、时间戳、处理参数）与源数据一致
   - 使用 `oad verify --input input/ --output output/` 自动比对

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 处理后的图像文件 | `.tif` / `.czi` | 保持原始格式，不转换 |
| 元数据文件 | `metadata.json` | 记录处理时间、参数、文件列表 |
| 日志文件 | `run_log.txt` | 记录每步执行状态与错误信息 |

---

## 四、置信度门控：不编造，不猜测

当遇到以下情况时，输出占位符 `[需核实:字段]`，并停止后续处理：

| 场景 | 处理方式 |
|------|----------|
| 输入文件命名不符合规范 | 输出 `[需核实:文件名格式]`，提示用户检查命名 |
| ZEN Blue 版本未知 | 输出 `[需核实:ZEN版本兼容性]`，建议先运行 `oad --selftest` |
| 参数值超出合理范围（如曝光时间 > 10s） | 输出 `[需核实:参数值]`，要求用户确认 |
| 输出路径无写入权限 | 输出 `[需核实:目录权限]`，提示检查文件系统权限 |

**原则**：宁可中断，不输出可能误导的结果。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入目录不存在 | "输入路径无效，请检查目录是否存在" | 创建目录或修正路径 |
| `E002` | 文件命名不规范 | "检测到文件名包含非法字符或格式不一致" | 统一重命名后重试 |
| `E003` | ZEN Blue 未运行 | "无法连接 ZEN Blue 实例，请确认软件已启动" | 启动 ZEN Blue 后重试 |
| `E004` | 参数越界 | "参数值超出允许范围（详见文档）" | 修改参数后重试 |
| `E005` | 输出目录不可写 | "输出目录无写入权限" | 修改目录权限或更换路径 |
| `E006` | 脚本执行超时 | "处理超时（默认 300s），可能文件过大" | 增大超时阈值或拆分文件 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 跳过试运行直接批量 | 直接对全量数据执行，发现格式错误后返工 | 始终先单样本试运行，确认输出后再批量 |
| 忽略备份 | 批量执行后原始文件被覆盖，无法恢复 | 执行前强制备份，保留原始数据 |
| 命名随意 | 文件名包含空格、中文、特殊符号，导致脚本中断 | 统一使用 `[a-z0-9_]` 命名 |
| 不校验输出 | 输出文件存在但内容为空或字段缺失，未被发现 | 批量后抽查 5-10% 输出，核对关键字段 |
| 版本不匹配 | 在旧版 ZEN Blue 上使用新接口，报错后不知所措 | 先运行 `oad --selftest` 验证兼容性 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（新手必读）

- **核心命令**：`oad --selftest`（自检）、`oad run --input [路径] --output [路径]`（执行）
- **铁律**：先试运行 → 再批量 → 最后校验
- **遇到问题**：查看错误码表（第五节），按提示修正

### 7.2 进阶路径（有经验用户）

- 阅读完整标准流程（第三节），理解每个步骤的意图
- 学习参数调优：通过修改脚本中的参数定义，适配不同实验需求
- 自定义输出格式：修改 `metadata.json` 的生成逻辑，对接下游分析工具

### 7.3 专家路径（开发者）

- 扩展脚本模板：在 `oad` 包内新增处理函数，支持更多 ZEN Blue 接口
- 集成 CI/CD：将批量执行嵌入自动化流水线，配合定时任务
- 贡献代码：遵循 MIT 许可证，提交改进至项目仓库

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用须知**：

1. 本 Skill 提供的所有脚本、代码示例及流程建议，使用者应自行评估其适用性并承担全部使用责任。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。
2. 使用者不得对本 Skill 进行反向工程、反编译或试图提取底层源代码（除非适用法律允许）。
3. 使用者应遵守所在机构关于实验数据管理和软件使用的相关规定。
4. 本 Skill 中的示例参数（如曝光时间、Z轴层数）仅为演示用途，实际实验请依据具体需求设置。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 SkillForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 ZEN Blue 官方文档及本 Skill 全部章节。*
