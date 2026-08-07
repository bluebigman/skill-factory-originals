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
