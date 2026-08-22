---
slug: gpt-engineer
name: AI生成代码工程
displayName: 代码工程 需求落地 质量审查
description: 从需求到工程代码，四步把关，让AI生成可落地、可审查、敢使用。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeForge Studio
agent_created: true
trigger_words: ["gpt-engineer", "AI生成代码", "代码工程", "需求生成项目", "AI编程", "代码脚手架", "工程化生成"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI生成代码工程 Skill 文档

## 一、能力边界速查卡

本 Skill 的核心价值在于：**把模糊的需求描述，转化为结构清晰、可审查、可落地的工程代码骨架**。它不是一个代码补全工具，而是一个**工程化需求翻译器**。

### 1.1 能做什么（能力清单）

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 环境体检 | 检测当前开发环境（Node/Python/Java等版本、包管理器、Git状态） | 环境体检报告 |
| 需求评分 | 对需求描述的完整性、明确性、可测试性进行量化评分 | 需求质量评分表 |
| 脚手架生成 | 根据需求生成项目目录结构、核心文件、配置模板 | 完整工程目录 |
| 完整性审查 | 检查生成代码中是否存在 TODO、占位符、未实现函数 | 完整性审查报告 |
| 凭据扫描 | 检测代码中是否硬编码了 API Key、密码、Token 等敏感信息 | 凭据扫描报告 |

### 1.2 不能做什么（明确边界）

| 禁止事项 | 说明 |
|----------|------|
| 不猜测信息 | 任何无法确认的信息（如数据库连接串、第三方 API 地址）必须使用占位符 `[需核实:字段名]`，不得编造 |
| 不保证运行 | 生成的代码骨架不保证直接可运行，需用户补充环境变量、依赖版本等关键信息 |
| 不替代测试 | 不生成完整的单元测试套件，只生成基础测试骨架 |
| 不处理已有代码 | 不负责重构或修改用户已有的工程代码，只处理从零开始的新项目 |

### 1.3 适用对象

- **适用**：需要快速搭建项目原型的开发者、需要将需求文档转化为代码结构的技术负责人、需要规范化 AI 生成代码流程的团队。
- **不适用**：需要处理遗留代码、需要深度业务逻辑实现、需要与特定云平台深度集成的场景。

---

## 二、触发方式与场景映射

### 2.1 触发词

当用户输入包含以下关键词时，本 Skill 自动激活：

- 主触发词：`gpt-engineer`、`AI生成代码`、`代码工程`、`需求生成项目`、`AI编程`
- 补充触发词：`代码脚手架`、`工程化生成`、`需求转代码`

### 2.2 场景映射表

| 用户说（大白话） | Skill 实际执行 |
|------------------|----------------|
| "帮我生成一个用户登录模块" | 执行标准流程：环境体检 → 需求评分 → 脚手架生成 → 完整性审查 |
| "把这个需求文档变成代码" | 解析需求文档 → 提取功能点 → 生成项目结构 |
| "AI 帮我写个爬虫项目" | 环境体检（检查 Python 版本）→ 生成爬虫工程骨架 |
| "给我搭个前后端分离的项目" | 生成前端（React/Vue）+ 后端（Node/Python）双目录结构 |

---

## 三、标准流程（四步把关）

### 3.1 前置条件

执行本 Skill 前，需确认以下条件：

| 条件 | 检查项 | 不满足时的处理 |
|------|--------|----------------|
| 输入格式 | 需求描述是否为文本（支持 JSON、CSV、命令行参数） | 提示用户转换为文本格式 |
| 环境信息 | 是否已提供目标语言/框架版本 | 使用 `[需核实:目标语言版本]` 占位 |
| 输出要求 | 是否指定输出格式（JSON/HTML/文件） | 默认输出为 Markdown 报告 + 工程目录 |

### 3.2 执行步骤

#### 步骤 1：环境体检

检测当前环境的运行时版本和工具链，输出体检报告。

```bash
# 示例：检测 Node 环境
node --version   # 输出：v18.17.0
npm --version    # 输出：9.6.7
```

**输出规范**：

```json
{
  "environment": {
    "node": "v18.17.0",
    "npm": "9.6.7",
    "git": "2.40.1"
  },
  "status": "ready" | "missing_dependency",
  "missing": ["python3", "java"]
}
```

#### 步骤 2：需求评分

对需求描述进行多维度量化评分，满分 100 分。

| 评分维度 | 权重 | 评分标准 |
|----------|------|----------|
| 完整性 | 30% | 是否包含输入/输出/异常处理描述 |
| 明确性 | 25% | 是否使用精确术语而非模糊表述 |
| 可测试性 | 20% | 是否包含验收标准或测试用例 |
| 技术栈匹配 | 15% | 是否指定语言/框架/版本 |
| 边界条件 | 10% | 是否描述空值、超时、并发等边界情况 |

**评分示例**：

- 需求："写一个登录功能" → 评分 35 分（缺输入输出、缺异常处理、缺技术栈）
- 需求："用 Python 3.10 + FastAPI 实现一个登录接口，接收 JSON 格式的 username 和 password，返回 JWT token，密码错误时返回 401" → 评分 88 分

#### 步骤 3：脚手架生成

根据需求评分结果，生成工程目录结构。

**标准目录模板**：

```
project-name/
├── src/                  # 源代码目录
│   ├── main.py           # 入口文件
│   └── modules/          # 功能模块
├── config/               # 配置文件
│   └── settings.py       # 环境变量配置
├── tests/                # 测试目录
│   └── test_main.py      # 基础测试
├── requirements.txt      # 依赖清单
├── README.md             # 项目说明
└── .env.example          # 环境变量模板
```

**生成规则**：

- 所有外部依赖（数据库连接、API 地址、密钥）一律使用 `[需核实:xxx]` 占位
- 每个文件头部自动添加文件用途注释
- 入口文件必须包含 `if __name__ == "__main__":` 或等效入口

#### 步骤 4：完整性审查与凭据扫描

对生成的代码进行自动化检查。

**完整性检查项**：

| 检查项 | 通过标准 |
|--------|----------|
| TODO 标记 | 不允许存在未处理的 TODO/FIXME |
| 占位符 | 占位符必须带有 `[需核实:]` 前缀 |
| 未实现函数 | 函数体不得为空或仅含 `pass` |
| 导入完整性 | 所有 import 的模块必须在依赖清单中 |

**凭据扫描规则**：

| 模式 | 示例 | 处理方式 |
|------|------|----------|
| API Key | `sk-xxxxxxxx` | 替换为 `[需核实:API_KEY]` |
| 密码 | `password = "123456"` | 替换为 `[需核实:DB_PASSWORD]` |
| Token | `token = "eyJhbGci..."` | 替换为 `[需核实:AUTH_TOKEN]` |

---

## 四、置信度门控

### 4.1 占位符规则

当信息不足时，必须使用 `[需核实:字段名]` 格式的占位符，**严禁猜测**。

| 场景 | 占位符示例 | 说明 |
|------|------------|------|
| 数据库连接串 | `[需核实:DATABASE_URL]` | 无法确认数据库类型和地址 |
| 第三方 API | `[需核实:PAYMENT_API_ENDPOINT]` | 无法确认支付服务商 |
| 端口号 | `[需核实:SERVER_PORT]` | 未指定监听端口 |
| 依赖版本 | `[需核实:FASTAPI_VERSION]` | 未指定框架版本 |

### 4.2 报告降级机制

- 当报告中出现占位符时，结论自动降级为「警告」级别
- 用户补充信息后，重新生成报告，升级为「通过」级别
- 降级规则：`通过` → `警告` → `不通过`

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 需求描述为空 | "请提供至少包含一个功能点的需求描述" | 引导用户补充需求 |
| E002 | 环境检测失败 | "无法检测到 Node.js 环境，请确认已安装" | 指导安装 Node.js 或切换语言 |
| E003 | 需求评分低于 40 分 | "需求描述过于模糊，建议补充输入输出和异常处理" | 展示评分明细，逐项指导补充 |
| E004 | 生成目录已存在 | "目标目录 project-name 已存在，是否覆盖？" | 询问用户选择覆盖或重命名 |
| E005 | 凭据扫描发现硬编码密钥 | "检测到疑似硬编码的 API Key，已自动替换为占位符" | 提示用户使用环境变量管理密钥 |
| E006 | 完整性审查未通过 | "存在 3 个未实现函数，请补充逻辑或标记为待办" | 列出具体函数位置，逐项修复 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 正确做法（正模式） |
|------------------|-------------------|
| ❌ 直接生成包含真实密码的代码 | ✅ 使用 `[需核实:DB_PASSWORD]` 占位，提示用户配置环境变量 |
| ❌ 需求描述只有一句话就生成 | ✅ 先执行需求评分，低于 60 分时引导用户补充细节 |
| ❌ 生成代码后不检查直接交付 | ✅ 必须执行完整性审查和凭据扫描，输出审查报告 |
| ❌ 忽略环境差异直接写死路径 | ✅ 使用相对路径或配置文件管理路径，保留环境变量接口 |
| ❌ 生成代码中包含 `pass` 空函数 | ✅ 空函数必须标注 `[需核实:待实现逻辑]` 并列入审查报告 |

---

## 七、渐进式披露阅读路径

### 7.1 速查卡（30 秒上手）

1. 输入需求描述（一句话即可）
2. 等待环境体检结果
3. 查看需求评分（低于 60 分先补充需求）
4. 生成工程目录
5. 检查完整性报告和凭据扫描结果
6. 补充 `[需核实:]` 占位符对应的真实信息

### 7.2 新手路径（首次使用）

- 阅读「能力边界速查卡」→ 了解能做什么、不能做什么
- 按「标准流程」步骤 1-4 执行 → 完成一次完整生成
- 遇到问题查「错误码体系」→ 定位并修复

### 7.3 进阶路径（熟练使用）

- 深入理解「需求描述质量评分」各维度权重 → 优化需求描述策略
- 自定义「明文凭据识别」匹配模式 → 扩展扫描范围
- 结合 CI/CD 流程 → 将环境体检、完整性审查、凭据扫描接入自动化流水线
- 建立团队级「需求描述规范」→ 基于 PROMPT.md 模板定制团队标准

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 生成代码所产生的一切后果，包括但不限于代码质量、安全性、合规性及法律风险。本 Skill 仅提供辅助生成功能，不构成任何形式的专业建议或担保。

2. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑、评分算法进行反向工程、破解、提取或二次分发。

3. **合规使用**：使用者应确保其使用场景符合所在地法律法规及 gpt-engineer 官方条款。

4. **无担保声明**：本 Skill 按「现状」提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证输出结果。*
