---
slug: codexassistant
name: codexassistant
displayName: CDP协议驱动 数据注入提取
description: 通过CDP协议驱动Codex，实现外部数据注入与结果结构化提取。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 协议工坊
agent_created: true
trigger_words: ["codexassistant", "codex助手", "CDP调试", "协议注入", "外部增强", "CDP连接", "数据桥接", "结果抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# codexassistant — CDP 协议驱动的 Codex 外部数据桥接工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 环境自检 | 运行 `--selftest` 验证运行环境是否就绪 | 首次安装后确认依赖完整 |
| 连接管理 | 通过 CDP 协议连接/断开 Codex 调试端口 | 需要向运行中的 Codex 实例注入数据 |
| 数据注入 | 将外部 JSON 文件注入 Codex 会话上下文 | 把业务数据、测试用例、配置参数喂给 Codex |
| 结果提取 | 按 JSON Schema 从 Codex 输出中提取结构化结果 | 将 Codex 的回复转为可程序化处理的 JSON |
| 输出落盘 | 将提取结果写入指定文件 | 供下游流水线消费 |

### 1.2 不能做什么（明确边界）

- 不能修改 Codex 核心逻辑或绕过其安全机制
- 不能保证注入数据后 Codex 必然产生预期输出（模型行为不可完全预测）
- 不能处理未按 Schema 定义的结构化提取请求
- 不能跨网络连接非本机调试端口（默认仅支持 localhost）
- 不能自动重试失败的连接（需手动重新执行命令）

### 1.3 适用对象

- 需要将外部数据批量喂给 Codex 的自动化脚本开发者
- 需要从 Codex 回复中稳定抽取字段的集成工程师
- 在 CI/CD 流水线中编排 Codex 任务的运维人员

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 场景描述 |
|--------|----------|
| `codexassistant` | 直接调用工具主命令 |
| `codex助手` | 中文场景下的自然语言唤起 |
| `CDP调试` | 需要调试 Codex 调试端口时 |
| `协议注入` | 需要向 Codex 注入外部数据时 |
| `外部增强` | 需要增强 Codex 上下文时 |
| `CDP连接` | 建立/断开调试连接时 |
| `数据桥接` | 在 Codex 与外部系统间搬运数据时 |
| `结果抽取` | 需要从 Codex 输出中提取结构化字段时 |

### 2.2 大白话场景映射表

| 用户说（口语化） | 实际执行动作 |
|------------------|--------------|
| "帮我检查一下环境能不能用" | 运行 `codexassistant --selftest` |
| "把这份数据喂给 Codex" | 运行 `codexassistant --connect -p 9222` 后执行 `-i ./data.json -f json` |
| "把 Codex 的回答存成 JSON" | 运行 `codexassistant -e -s ./schema.json -o ./result.json` |
| "断开连接" | 运行 `codexassistant --disconnect` |
| "看看版本" | 运行 `codexassistant --version` |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| 操作系统 | Windows / macOS / Linux | `uname -a` 或 `ver` |
| Node.js | ≥ 16.0.0 | `node -v` |
| Codex 应用 | 已安装且支持 CDP 调试端口 | 应用设置中确认开启调试模式 |
| 网络 | 本机回环地址可访问 | `ping 127.0.0.1` |

### 3.2 执行步骤（分步编号）

**Step 1：环境自检**

```bash
codexassistant --selftest
```

预期输出：

```
[OK] Node.js 版本检查通过
[OK] CDP 依赖库可用
[OK] 文件系统写入权限正常
[OK] 网络回环可用
```

**Step 2：启动 Codex 并开启调试端口**

在 Codex 应用设置中开启「远程调试」选项，记下端口号（默认 9222）。

**Step 3：建立连接**

```bash
codexassistant --connect -p 9222
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--connect` | 是 | - | 建立连接 |
| `-p` | 否 | 9222 | 调试端口号 |

**Step 4：注入数据**

```bash
codexassistant -i ./data.json -f json
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `-i` | 是 | - | 数据文件路径 |
| `-f` | 否 | json | 数据格式（当前仅支持 json） |

数据文件示例（`data.json`）：

```json
{
  "context": "请分析以下销售数据",
  "records": [
    { "region": "华东", "amount": 12000 },
    { "region": "华北", "amount": 9800 }
  ]
}
```

**Step 5：提取结果**

```bash
codexassistant -e -s ./schema.json -o ./result.json
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `-e` | 是 | - | 执行提取 |
| `-s` | 是 | - | Schema 文件路径 |
| `-o` | 否 | ./result.json | 输出文件路径 |

Schema 文件示例（`schema.json`）：

```json
{
  "type": "object",
  "properties": {
    "summary": { "type": "string" },
    "totalAmount": { "type": "number" },
    "topRegion": { "type": "string" }
  },
  "required": ["summary", "totalAmount"]
}
```

**Step 6：断开连接**

```bash
codexassistant --disconnect
```

### 3.3 输出规范

- 所有命令执行后均输出 `[OK]` 或 `[ERROR]` 前缀的状态行
- 提取结果默认写入 `./result.json`，文件编码为 UTF-8
- 输出文件结构严格遵循 Schema 定义，未定义字段不写入

---

## 四、置信度门控

当遇到以下情况时，工具会输出 `[需核实:字段]` 占位符，而非编造数据：

| 场景 | 处理方式 |
|------|----------|
| Schema 中标记为 `required` 但 Codex 输出中缺失 | 输出 `[需核实:字段名]` |
| 提取结果类型与 Schema 定义不符 | 输出 `[需核实:字段名]` 并附类型冲突说明 |
| 注入数据文件格式非法 | 终止操作，输出错误码 `E1001` |
| Codex 输出为空或超时 | 输出 `[需核实:全部字段]` 并提示重试 |

示例输出：

```json
{
  "summary": "销售数据整体呈上升趋势",
  "totalAmount": 21800,
  "topRegion": "[需核实:topRegion]"
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 数据文件格式非法 | "数据文件不是合法的 JSON 格式" | 检查文件内容，确保 JSON 语法正确 |
| `E1002` | Schema 文件缺失 | "未找到指定的 Schema 文件" | 确认 `-s` 参数路径正确 |
| `E2001` | 连接失败 | "无法连接到 Codex 调试端口" | 确认 Codex 已启动且调试端口已开启 |
| `E2002` | 连接超时 | "连接超时，请检查网络配置" | 确认端口号正确，尝试重新连接 |
| `E3001` | 提取结果不符合 Schema | "提取结果缺少必填字段" | 检查 Schema 定义，或调整提取逻辑 |
| `E3002` | 输出文件写入失败 | "无法写入输出文件" | 检查目录权限，确认路径可写 |
| `E4001` | 未建立连接即执行操作 | "请先执行 --connect 建立连接" | 按流程先连接再操作 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 跳过自检直接连接 | 不运行 `--selftest` 就执行 `--connect` | 每次新环境先跑自检，确认依赖完整 |
| 端口号写错 | 默认 9222 但实际端口是 9333，未指定 `-p` | 确认 Codex 实际监听端口，显式传入 `-p` |
| Schema 定义过严 | 所有字段都设为 `required`，导致频繁报错 | 仅将核心字段设为必填，其余设为可选 |
| 注入数据体积过大 | 一次性注入 10MB 以上数据 | 分批注入，每批不超过 1MB |
| 忽略错误码直接重试 | 报 `E2001` 后盲目重试连接 | 先检查 Codex 进程是否存活，再重试 |

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```bash
# 1. 自检
codexassistant --selftest

# 2. 连接（Codex 需已开启调试端口）
codexassistant --connect -p 9222

# 3. 注入数据
codexassistant -i ./data.json -f json

# 4. 提取结果
codexassistant -e -s ./schema.json -o ./result.json

# 5. 断开
codexassistant --disconnect
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」确认工具适用场景
2. 按「标准操作流程」逐步执行，每步观察输出状态
3. 遇到错误对照「错误码体系」定位问题
4. 参考「FAQ 反模式」避免常见失误

### 7.3 进阶路径（深度集成）

1. 将 `codexassistant` 命令嵌入 Shell 脚本或 CI 流水线
2. 设计符合业务需求的 Schema，确保提取结果可直接消费
3. 结合错误码编写自动化重试逻辑（注意：工具本身不自动重试）
4. 对注入数据做预处理，控制单次注入体积

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因数据注入错误、结果提取偏差、连接中断等造成的直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图获取源代码逻辑。

3. **合规使用**：使用者需确保使用场景符合当地法律法规及 Codex 应用的服务条款。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
