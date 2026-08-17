---
slug: ai-app-builder-foundation
name: ai-app-builder-foundation
displayName: 自托管AI应用构建器
description: 搭建自托管AI应用构建底座，支持模板生成、构建验证与部署流程。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 云筑工坊
agent_created: true
trigger_words: ["自托管AI应用", "AI应用构建器", "模板生成", "部署流程", "自建AI平台", "AI应用脚手架", "本地AI部署"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 自托管AI应用构建器 — 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 产出物 |
|--------|------|--------|
| 项目脚手架生成 | 基于模板生成可运行的 AI 应用项目结构 | 完整项目目录（含源码、配置、文档） |
| 构建验证 | 对生成的项目执行 Docker 镜像构建与测试 | 构建日志、测试报告 |
| 部署流程编排 | 提供 docker-compose 部署方案与环境变量模板 | docker-compose.yml、.env.example |
| 健康检查 | 内置 `/health` 端点用于服务状态探测 | HTTP 200 响应（含 JSON 状态体） |
| 模板自定义 | 支持修改 `templates/` 目录下的模板文件 | 自定义模板集 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供托管服务 | 本工具只生成与验证项目，不负责运行你的线上服务 |
| 不包含模型权重 | 生成的模板不附带任何预训练模型文件，需自行配置模型来源 |
| 不处理业务逻辑 | 生成的代码仅包含基础框架，业务逻辑需自行编写 |
| 不支持 GUI 操作 | 全部功能通过命令行接口（CLI）完成 |
| 不保证生产可用 | 生成的项目需经过自行测试与加固后方可上线 |

### 1.3 适用对象

- 需要快速搭建 AI 应用原型的开发者
- 希望将 AI 服务部署到自有服务器的团队
- 需要标准化 AI 项目结构的工程管理人员
- 对数据隐私有要求、倾向自托管方案的机构

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本技能将被激活：

- 自托管AI应用
- AI应用构建器
- 模板生成
- 部署流程
- 自建AI平台
- AI应用脚手架
- 本地AI部署

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 技能响应 |
|------------------|----------|----------|
| "我想自己搭一个 AI 聊天机器人" | 生成 chat 类型项目 | 执行 `ai-app-builder-foundation "my-app" --type chat` |
| "帮我搞个 AI 应用的项目结构" | 生成标准项目骨架 | 执行默认参数生成命令 |
| "怎么把 AI 服务部署到我的服务器上" | 获取部署方案 | 展示 DEPLOYMENT.md 与 docker-compose 配置 |
| "检查一下我的环境能不能跑" | 环境自检 | 执行 `--selftest` 并解读结果 |
| "我想改一下生成的模板" | 自定义模板 | 引导修改 `templates/` 目录 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| Python | ≥ 3.9 | `python --version` |
| Docker | ≥ 20.10 | `docker --version` |
| Docker Compose | ≥ 2.0 | `docker-compose --version` |
| 网络 | 可访问 PyPI 与 Docker Hub | `pip download --no-deps requests` |

### 3.2 执行步骤

#### 步骤 1：环境自检

```bash
ai-app-builder-foundation --selftest
```

预期输出：

```
[OK] Python 3.10.12
[OK] Docker 24.0.5
[OK] Docker Compose 2.20.2
[OK] 模板目录可写
[OK] 依赖包可安装
环境检查通过，可以开始构建。
```

#### 步骤 2：生成项目

```bash
ai-app-builder-foundation "my-app" --type chat
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | 无 | 项目名称（目录名） |
| `--type` | 否 | `chat` | 项目类型：`chat` / `rag` / `agent` |
| `--template` | 否 | `default` | 使用的模板名称 |
| `--output` | 否 | 当前目录 | 输出路径 |

#### 步骤 3：进入项目目录

```bash
cd my-app
```

#### 步骤 4：安装依赖

```bash
pip install -r requirements.txt
```

#### 步骤 5：运行测试

```bash
python -m pytest tests/
```

预期输出：

```
============================= test session starts =============================
collected 12 items

tests/test_app.py .........                                             [ 75%]
tests/test_health.py ...                                                [100%]

============================== 12 passed in 2.31s =============================
```

#### 步骤 6：启动服务

```bash
docker-compose up -d
```

#### 步骤 7：验证服务状态

```bash
curl http://localhost:8000/health
```

预期响应：

```json
{"status": "ok", "version": "1.0.0", "timestamp": "2025-01-15T08:30:00Z"}
```

### 3.3 输出规范

| 输出物 | 位置 | 格式 |
|--------|------|------|
| 项目源码 | `my-app/src/` | Python 文件 |
| 依赖清单 | `my-app/requirements.txt` | pip 格式 |
| 容器编排 | `my-app/docker-compose.yml` | YAML |
| 环境变量模板 | `my-app/.env.example` | KEY=VALUE |
| 项目说明 | `my-app/README.md` | Markdown |
| 部署指南 | `my-app/DEPLOYMENT.md` | Markdown |

---

## 四、环境变量清单

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_PORT` | `8000` | 服务监听端口 |
| `APP_HOST` | `0.0.0.0` | 服务绑定地址 |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `MODEL_PATH` | `/models` | 模型文件存放路径 |
| `MAX_REQUESTS` | `100` | 每分钟最大请求数 |
| `CORS_ORIGINS` | `*` | 允许的跨域来源（逗号分隔） |
| `DB_CONNECTION` | `sqlite:///app.db` | 数据库连接字符串 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 环境不满足要求 | "检测到 Python 版本低于 3.9，请升级后重试" | 安装 Python 3.9+ 并重新执行 `--selftest` |
| `E002` | 项目名称非法 | "项目名称只能包含字母、数字、下划线和连字符" | 修改名称后重新执行生成命令 |
| `E003` | 模板不存在 | "模板 `xxx` 不存在，可用模板：default, minimal, full" | 使用 `--template` 指定可用模板 |
| `E004` | 依赖安装失败 | "依赖安装失败，请检查网络连接或镜像源" | 配置 PyPI 镜像后重试 `pip install` |
| `E005` | 测试未通过 | "测试失败，请查看 tests/ 目录下的测试报告" | 检查代码修改，修复后重新运行 pytest |
| `E006` | Docker 构建失败 | "Docker 镜像构建失败，请检查 Dockerfile 与依赖" | 查看构建日志，修正 Dockerfile 后重试 |
| `E007` | 端口被占用 | "端口 8000 已被占用，请更换端口或释放占用" | 修改 `APP_PORT` 环境变量或停止占用进程 |

---

## 六、FAQ 反模式

### 6.1 常见坑位

| 坑位 | 反模式（错误做法） | 正模式（推荐做法） |
|------|-------------------|-------------------|
| 跳过自检 | 直接生成项目，忽略 `--selftest` | 先运行自检，确认环境就绪再生成 |
| 忽略环境变量 | 直接使用默认配置启动服务 | 根据部署环境修改 `.env` 文件 |
| 修改模板不测试 | 改完模板直接生成项目 | 修改后先运行模板测试再生成 |
| 依赖锁定不完整 | 只写包名不写版本号 | 使用 `pip freeze > requirements.txt` 锁定版本 |
| 忽略健康检查 | 部署后不验证服务状态 | 启动后立即执行 `curl /health` 确认服务正常 |

### 6.2 反模式对照表

| 场景 | 反模式 | 正模式 |
|------|--------|--------|
| 多环境部署 | 所有环境共用同一 `.env` | 为 dev/staging/prod 分别编写 `.env` |
| CI/CD 集成 | 手动执行构建验证 | 将构建验证接入 GitHub Actions |
| 新增应用类型 | 复制现有类型修改 | 在 `app_builder/types/` 中添加新类型定义 |
| 模板定制 | 直接修改生成后的项目 | 修改 `templates/` 目录下的模板文件 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 自检环境
ai-app-builder-foundation --selftest

# 2. 生成项目
ai-app-builder-foundation "my-app" --type chat

# 3. 进入目录并安装依赖
cd my-app && pip install -r requirements.txt

# 4. 运行测试
python -m pytest tests/

# 5. 启动服务
docker-compose up -d

# 6. 验证健康状态
curl http://localhost:8000/health
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解工具能做什么、不能做什么
2. 运行 `--selftest` 确认环境就绪
3. 使用默认参数生成一个 chat 类型项目
4. 按 README.md 的指引运行项目
5. 查看 DEPLOYMENT.md 了解部署流程

### 7.3 进阶路径（熟练使用）

1. 自定义模板：修改 `templates/` 目录下的模板文件
2. 扩展应用类型：在 `app_builder/types/` 中添加新类型定义
3. 集成 CI/CD：将构建验证接入 GitHub Actions
4. 多环境部署：为不同环境编写独立的 `.env` 配置
5. 性能调优：调整 `MAX_REQUESTS` 与 `LOG_LEVEL` 等参数

---

## 八、置信度门控

当信息不足或无法确认时，本技能将使用以下占位符，不会编造数据：

| 占位符 | 使用场景 | 示例 |
|--------|----------|------|
| `[需核实:字段]` | 需要用户提供但未提供的信息 | `[需核实:模型路径]` |
| `[需核实:版本号]` | 依赖版本不确定时 | `[需核实:torch版本]` |
| `[需核实:端口]` | 端口被占用需用户确认时 | `[需核实:可用端口]` |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 及其生成项目的全部责任。因使用本 Skill 或其产出物导致的任何直接或间接损失，技能作者不承担任何责任。

2. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除开源部分外）。

3. **合规使用**：使用者应确保其构建的 AI 应用符合当地法律法规，不得用于任何非法用途。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 云筑工坊

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
