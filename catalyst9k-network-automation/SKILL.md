---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: catalyst9k-network-automation
name: catalyst9k-network-automation
displayName: 网络设备自动化 配置生成 脚本编排
description: 将网络配置需求转化为可执行脚本，辅助Catalyst交换机的自动化工作流设计。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/catalyst9k-network-automation
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: NetForge Studio
agent_created: true
trigger_words: ["catalyst9k network automation", "网络自动化", "交换机脚本", "Catalyst配置生成", "网络脚本编排"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# Catalyst9K 网络自动化脚本设计助手

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 网络配置需求解析 | 从自然语言或半结构化文本中提取配置意图 | "为接口Gi1/0/1配置VLAN 100，端口模式为access" | `{"interface": "Gi1/0/1", "vlan": 100, "mode": "access"}` |
| C2 | Python脚本骨架生成 | 基于解析结果生成可运行的Python脚本框架 | 上述结构化数据 | 包含`connect()`、`configure()`、`disconnect()`的脚本模板 |
| C3 | YANG模型字段映射 | 将配置项映射到Open YANG模型中的对应叶子节点 | `{"vlan": 100}` | `Cisco-IOS-XE-vlan:VLAN/vlan-id = 100` |
| C4 | 批量配置展开 | 将单条配置模板展开为多设备/多接口的批量配置 | 模板+设备列表 | 逐设备展开的配置清单 |
| C5 | 配置合规性预检 | 检查生成的配置是否符合常见网络规范（如VLAN范围、端口安全） | 生成的配置 | 合规报告，含警告项 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行真实设备操作 | 本Skill仅生成脚本和配置文本，不直接连接设备下发配置 |
| L2 | 不保证脚本零错误 | 生成的脚本需在测试环境验证后方可部署 |
| L3 | 不覆盖所有IOS-XE版本差异 | 不同版本YANG模型可能存在差异，需自行核对 |
| L4 | 不处理非Catalyst设备 | 仅面向Catalyst 9000系列交换机 |
| L5 | 不提供图形化界面 | 所有交互通过命令行或API完成 |

### 1.3 适用对象

- 网络工程师：需要快速生成自动化脚本原型
- DevOps工程师：需要将网络配置纳入CI/CD流水线
- 网络架构师：需要评估自动化方案的可行性
- 学习网络自动化的学生：需要参考示例脚本


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。
