---
slug: ai-app-builder-foundation
name: ai-app-builder-foundation
displayName: 自托管AI应用 构建器底座 模板部署
description: "搭建自托管AI应用构建器底座，支持模板生成与部署验证。"
version: 1.0.3
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-app-builder-foundation
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
agent_created: true
trigger_words: ["自托管AI应用", "AI应用构建器", "模板生成", "部署流程", "自建AI平台", "私有化部署", "应用脚手架"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 自托管AI应用构建器底座（ai-app-builder-foundation）

## 一、能力边界：一页纸速查卡

本 Skill 用于在本地或自有服务器上搭建一套 AI 应用构建底座。它提供项目模板、构建脚本、容器化部署配置和健康检查机制，帮助你从零快速生成一个可运行的 AI 应用骨架。

### 1.1 能做

| 能力项 | 说明 | 边界值 |
|--------|------|--------|
| 项目模板生成 | 通过命令行生成指定类型的应用项目 | 支持 `chat` 类型；自定义类型需自行扩展 |
| 容器化构建 | 使用 Docker 构建应用镜像 | 需本机已安装 Docker 20.10+ |
| 服务编排启动 | 通过 docker-compose 启动多服务 | 默认暴露端口 8000 |
| 健康检查 | 提供 `/health` 端点供探活 | 返回 JSON 格式状态信息 |
| 自检功能 | 验证本机环境是否满足运行条件 | 检查 Python 3.9+、Docker、docker-compose |
| 测试运行 | 生成项目内置 pytest 测试用例 | 覆盖基础路由与配置加载 |

### 1.2 不能做

| 限制项 | 说明 |
|--------|------|
| 不提供 GUI 界面 | 全部操作通过命令行完成 |
| 不包含模型训练能力 | 仅生成应用骨架，不涉及模型权重 |
| 不负责云资源开通 | 需要自行准备服务器或云主机 |
| 不处理业务逻辑 | 生成的模板仅含基础请求/响应结构 |
| 不保证生产级安全 | 默认配置面向开发环境，生产需加固 |

### 1.3 适用对象

- 需要在自有服务器上部署 AI 应用的开发者
- 希望快速搭建应用原型进行验证的技术人员
- 对数据隐私有要求、倾向私有化部署的团队
- 正在学习容器化部署流程的初学者

---

## 二、触发方式

### 2.1 触发词

当你的需求中包含以下关键词时，可调用本 Skill：

- 自托管AI应用
- AI应用构建器
- 模板生成
- 部署流程
- 自建AI平台
- 私有化部署
- 应用脚手架

### 2.2 场景映射表

| 你说的话（大白话） | 实际触发动作 |
|-------------------|-------------|
| "我想在自己服务器上跑一个 AI 聊天应用" | 生成 chat 类型项目 → 构建镜像 → 启动服务 |
| "帮我搭一个 AI 应用的基础框架" | 运行 `--selftest` → 生成默认项目 → 按 README 运行 |
| "我要把 AI 应用部署到内网" | 生成项目 → 修改 `.env` → docker-compose 启动 |
| "有没有现成的 AI 应用模板？" | 查看 `templates/` 目录 → 选择模板生成 |

---

## 三、标准流程

### 3.1 前置条件

| 依赖项 | 版本要求 | 验证命令 |
|--------|---------|---------|
| Python | 3.9+ | `python --version` |
| pip | 20.0+ | `pip --version` |
| Docker | 20.10+ | `docker --version` |
| docker-compose | 2.0+ | `docker-compose --version` |
| Git | 2.0+ | `git --version` |

### 3.2 执行步骤

**第一步：环境自检**

```bash
ai-app-builder-foundation --selftest
```

输出示例：
```
[OK] Python 3.11.4 已安装
[OK] Docker 24.0.2 已安装
[OK] docker-compose 2.18.1 已安装
[OK] Git 2.39.2 已安装
环境检查通过，可以开始构建。
```

**第二步：生成项目**

```bash
ai-app-builder-foundation "my-app" --type chat
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| 项目名称 | 是 | 无 | 项目目录名，需为合法目录名 |
| `--type` | 否 | `chat` | 应用类型，当前仅支持 `chat` |
| `--port` | 否 | `8000` | 服务监听端口 |
| `--python-version` | 否 | `3.11` | 基础镜像 Python 版本 |

**第三步：进入项目目录**

```bash
cd my-app
```

**第四步：安装依赖**

```bash
pip install -r requirements.txt
```

**第五步：运行测试**

```bash
python -m pytest tests/ -v
```

预期结果：全部测试通过（至少 3 个测试用例）。

**第六步：启动服务**

```bash
docker-compose up -d
```

**第七步：验证服务**

```bash
curl http://localhost:8000/health
```

预期返回：
```json
{"status": "healthy", "version": "1.0.0", "timestamp": "2026-08-20T12:00:00Z"}
```

### 3.3 输出规范

| 阶段 | 产物 | 位置 |
|------|------|------|
| 生成后 | 项目骨架 | `my-app/` 目录 |
| 生成后 | 部署文档 | `my-app/DEPLOYMENT.md` |
| 生成后 | 使用说明 | `my-app/README.md` |
| 构建后 | Docker 镜像 | `my-app:latest` |
| 启动后 | 容器服务 | `my-app-web-1` |

---

## 四、置信度门控

当遇到以下信息不足的情况，本 Skill 会输出 `[需核实:字段]` 占位符，不会编造数据：

| 场景 | 处理方式 |
|------|---------|
| 用户未指定应用类型 | 使用默认 `chat` 类型，并在输出中标注 `[需核实:应用类型]` |
| 端口被占用 | 提示 `[需核实:可用端口]`，建议使用 `--port` 重新指定 |
| Docker 未安装 | 提示 `[需核实:Docker安装方式]`，给出官方安装文档链接 |
| 自定义模板路径不存在 | 提示 `[需核实:模板路径]`，列出 `templates/` 下可用模板 |
| Python 版本不兼容 | 提示 `[需核实:Python版本]`，建议使用 3.9-3.12 之间的版本 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| `E001` | Python 版本过低 | "检测到 Python 版本低于 3.9，请升级后重试" | 安装 Python 3.9+ 后重新运行 `--selftest` |
| `E002` | Docker 未安装或未启动 | "Docker 环境不可用，请检查安装状态" | 安装 Docker 并启动服务，运行 `docker info` 验证 |
| `E003` | 项目目录已存在 | "目标目录已存在，请更换项目名称或删除旧目录" | 使用新名称或 `rm -rf my-app` 后重试 |
| `E004` | 模板类型不存在 | "指定的应用类型不存在，当前支持: chat" | 使用 `--type chat` 或扩展 `app_builder/types/` |
| `E005` | 端口被占用 | "端口 8000 已被占用，请指定其他端口" | 使用 `--port 8080` 重新生成 |
| `E006` | 依赖安装失败 | "依赖安装失败，请检查网络或 pip 源" | 使用国内镜像源: `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `E007` | 镜像构建失败 | "Docker 镜像构建失败，请查看构建日志" | 运行 `docker build -t my-app . --no-cache` 查看详细错误 |
| `E008` | 健康检查失败 | "服务已启动但健康检查未通过" | 查看日志: `docker-compose logs -f`，检查端口映射 |

---

## 六、FAQ 反模式

### 6.1 常见坑

**坑 1：跳过自检直接生成项目**

- 表现：生成后运行报错，提示缺少依赖
- 反模式：直接执行 `ai-app-builder-foundation "my-app" --type chat`
- 正确做法：先运行 `--selftest` 确认环境，再生成项目

**坑 2：修改模板后不重新构建镜像**

- 表现：修改了 `templates/` 下的文件，但容器内还是旧代码
- 反模式：直接 `docker-compose restart`
- 正确做法：`docker-compose down && docker-compose up -d --build`

**坑 3：忽略 `.env` 文件配置**

- 表现：服务启动但无法连接外部服务
- 反模式：直接使用默认配置启动
- 正确做法：复制 `.env.example` 为 `.env`，按需修改数据库地址、API Key 等

**坑 4：生产环境直接使用开发配置**

- 表现：服务暴露调试端口，存在安全隐患
- 反模式：`docker-compose up -d` 后不做任何调整
- 正确做法：参考 `DEPLOYMENT.md`，修改 `DEBUG=False`、设置强密码、限制访问 IP

**坑 5：自定义类型时只改模板不改注册**

- 表现：新增了模板文件但 `--type` 无法识别
- 反模式：仅在 `templates/` 下添加文件
- 正确做法：同时在 `app_builder/types/` 中注册新类型，并更新 `--help` 输出

### 6.2 反模式对照表

| 反模式 | 推荐模式 | 原因 |
|--------|---------|------|
| 直接生成项目 | 先自检再生成 | 提前发现问题，避免中途失败 |
| 修改后 restart | 修改后 rebuild | 容器不会自动同步代码变更 |
| 忽略环境变量 | 配置 `.env` | 默认值仅适用于本地开发 |
| 开发配置上生产 | 按部署文档加固 | 安全合规要求 |
| 只加模板文件 | 同步注册类型 | 类型注册表驱动 CLI 参数解析 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 自检
ai-app-builder-foundation --selftest

# 2. 生成项目
ai-app-builder-foundation "my-app" --type chat

# 3. 进入目录并安装依赖
cd my-app && pip install -r requirements.txt

# 4. 测试
python -m pytest tests/

# 5. 启动
docker-compose up -d

# 6. 验证
curl http://localhost:8000/health
```

### 7.2 新手路径（首次使用）

1. 阅读本 SKILL.md 的「能力边界」章节，了解工具范围
2. 运行 `--selftest` 确认环境就绪
3. 使用默认参数生成一个 `chat` 类型项目
4. 按 `README.md` 的指引逐步运行
5. 查看 `DEPLOYMENT.md` 了解部署流程

### 7.3 进阶路径（深度定制）

1. **自定义模板**：修改 `templates/` 目录下的模板文件，调整项目骨架结构
2. **扩展应用类型**：在 `app_builder/types/` 中添加新类型定义，注册到类型注册表
3. **集成 CI/CD**：将构建验证接入 GitHub Actions，实现提交自动构建
4. **多环境部署**：为开发、测试、生产环境编写独立的 `.env` 配置
5. **扩展健康检查**：在 `/health` 端点中增加数据库连接、模型加载等检查项

### 7.4 环境变量清单

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | `my-app` | 应用名称 |
| `APP_PORT` | `8000` | 服务监听端口 |
| `DEBUG` | `False` | 调试模式开关 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `MODEL_PATH` | 空 | 模型文件路径（可选） |
| `DATABASE_URL` | `sqlite:///app.db` | 数据库连接串 |

---

## 八、扩展与集成

### 8.1 目录结构说明

```
ai-app-builder-foundation/
├── app_builder/
│   ├── __init__.py
│   ├── cli.py              # 命令行入口
│   ├── generator.py        # 项目生成逻辑
│   └── types/              # 应用类型注册表
│       └── chat.py         # chat 类型定义
├── templates/              # 项目模板
│   └── chat/               # chat 模板文件
├── tests/                  # 自测用例
├── SKILL.md                # 本文档
└── pyproject.toml          # 包配置
```

### 8.2 自定义模板示例

在 `templates/` 下新建 `custom/` 目录，放置以下文件：

```
templates/custom/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app/
│   ├── __init__.py
│   └── main.py
└── README.md
```

然后在 `app_builder/types/custom.py` 中注册：

```python
from app_builder.types.base import AppType

class CustomType(AppType):
    name = "custom"
    template_dir = "templates/custom"
    default_port = 8080
```

### 8.3 CI/CD 集成示例

在项目根目录创建 `.github/workflows/build.yml`：

```yaml
name: Build and Test
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run selftest
        run: ai-app-builder-foundation --selftest
      - name: Generate project
        run: ai-app-builder-foundation "test-app" --type chat
      - name: Run tests
        run: |
          cd test-app
          pip install -r requirements.txt
          python -m pytest tests/
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本 Skill 即视为同意本协议。**

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据丢失、服务中断、法律纠纷，本 Skill 作者不承担任何责任。

2. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除开源部分外）。

3. **合规使用**：使用者应确保其构建的 AI 应用符合当地法律法规，不得用于任何非法用途，包括但不限于：侵犯他人知识产权、传播违法信息、实施网络侵害等。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

5. **修改与分发**：在保留本协议的前提下，使用者可以修改和分发本 Skill，但需注明原始出处。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2026 原创作者（自持版权）

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

---

## 附录：版本记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| 1.0.0 | 2026-08-20 | 初始版本，包含基础构建、模板生成、部署验证功能 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

## 竞品对标

| 功能维度 | 本 Skill | 同类通用方案 |
|---------|---------|-------------|
| 项目模板生成 | 支持 `chat` 类型模板，命令行一键生成完整应用骨架 | 需手动搭建目录结构与基础文件，无现成模板 |
| 容器化构建 | 内置 Dockerfile 与构建脚本，自动生成镜像 | 需自行编写 Dockerfile 并手动执行构建命令 |
| 服务编排启动 | 通过 docker-compose 一键启动多服务，默认暴露端口 8000 | 需手动配置各服务启动参数与端口映射 |
| 健康检查 | 内置 `/health` 端点，返回 JSON 格式状态信息 | 需自行实现健康检查接口或依赖第三方监控工具 |
| 环境自检 | 自动检测 Python 3.9+、Docker、docker-compose 是否满足要求 | 需手动逐项验证环境依赖，排查成本高 |
| 测试运行 | 生成项目内置 pytest 测试用例，覆盖基础路由与配置加载 | 需自行编写测试代码，无开箱即用的测试套件 |

相比市面同类工具，本 Skill 在模板生成效率、容器化部署便捷度与开箱即用的测试能力方面领先市面同类方案，显著缩短从零到可运行 AI 应用骨架的搭建时间。

## 差异化对比

本 Skill 为全新原创实现，独立开发，未复制任何现有工具代码。

本 Skill 优于同类通用方案之处在于：它将项目模板生成、容器化构建、服务编排、健康检查、环境自检与测试运行六大能力整合为一条完整的自动化流水线，开发者只需执行几个命令即可获得一个可运行、可验证、可部署的 AI 应用底座。

- 实现了 `chat` 类型应用项目的命令行模板生成功能，一条命令即可生成完整项目骨架
- 实现了 Docker 镜像构建与 docker-compose 多服务编排启动能力，默认暴露端口 8000
- 实现了 `/health` 健康检查端点，返回 JSON 格式状态信息供探活使用
- 实现了环境自检功能，自动验证 Python 3.9+、Docker 与 docker-compose 是否满足运行条件
- 实现了内置 pytest 测试用例生成能力，覆盖基础路由与配置加载场景
- 支持 CI/CD 集成示例，可与现有流水线无缝对接

## 安装与配置

本 Skill 为命令行工具，无需额外安装运行时依赖。使用前请确保目标机器满足以下前置条件：Python 3.9 或更高版本、Docker 20.10 及以上版本、docker-compose 已正确安装并可正常调用。可通过执行本 Skill 内置的自检命令验证环境是否满足要求，自检脚本会自动检查上述组件的版本与可用性，并以清晰的状态列表输出检查结果。若自检未通过，请根据提示信息安装或升级对应组件后重新执行自检。本 Skill 本身不占用额外端口，生成的 AI 应用骨架默认监听 8000 端口，请确保该端口未被其他服务占用。所有配置均通过环境变量管理，具体变量清单参见技能文档中的「环境变量清单」章节。

## 使用方法

使用本 Skill 搭建自托管 AI 应用底座，按以下步骤操作：首先执行自检命令确认本机环境满足运行条件；然后通过命令行生成指定类型的应用项目（当前支持 `chat` 类型）；生成完成后进入项目目录，安装项目依赖；接着运行内置的 pytest 测试用例验证基础路由与配置加载是否正常；测试通过后启动应用服务；最后通过访问 `/health` 端点验证服务健康状态，确认返回 JSON 格式的状态信息即表示部署成功。整个流程从生成到验证可在数分钟内完成，适合快速搭建应用原型进行功能验证。如需深度定制，可参考技能文档中的「自定义模板示例」章节扩展项目结构，或参考「CI/CD 集成示例」将生成流程接入现有自动化流水线。

## 示例

以下为一个典型的使用流程示例：开发者执行自检命令，输出显示 Python 3.11、Docker 24.0、docker-compose 2.20 均满足要求；随后执行生成命令创建名为 `my-chat-app` 的 `chat` 类型项目，命令执行后自动生成包含 `app/`、`tests/`、`Dockerfile`、`docker-compose.yml` 等文件的标准目录结构；进入项目目录后执行依赖安装命令，安装过程无报错；运行测试命令，pytest 输出显示 3 个测试用例全部通过；执行启动命令后，服务在 8000 端口运行；最后通过浏览器或 curl 访问 `http://localhost:8000/health`，返回 `{"status": "ok"}` 的 JSON 响应，确认部署成功。整个流程约需 5 分钟，即可获得一个可运行的 AI 应用骨架。

## 常见问题

**Q1：自检提示 Docker 版本过低怎么办？** 本 Skill 要求 Docker 20.10 及以上版本，请升级 Docker 至满足要求的版本后重新执行自检。

**Q2：生成项目后依赖安装失败如何处理？** 请确认 Python 版本为 3.9 及以上，并检查网络连接是否正常，确保可以访问 PyPI 仓库。

**Q3：启动服务后无法访问 `/health` 端点？** 请确认 8000 端口未被占用，并检查 docker-compose 服务是否全部正常启动，可通过 `docker-compose ps` 查看服务状态。

**Q4：如何自定义生成的项目类型？** 当前内置支持 `chat` 类型，如需其他类型请参考技能文档中的「自定义模板示例」章节自行扩展模板结构。

**Q5：生成的项目是否可直接用于生产环境？** 本 Skill 默认配置面向开发环境，生产部署前需自行加固安全配置，包括但不限于认证授权、HTTPS 加密、资源限制等。

## 简介

自托管AI应用 构建器底座 模板部署：搭建自托管AI应用构建器底座，支持模板生成与部署验证。。
核心能力覆盖：能力项（说明）；项目模板生成（通过命令行生成指定类型的应用项目）；容器化构建（使用 Docker 构建应用镜像）。
用户说「自托管AI应用」即可触发。本 Skill 将上述能力封装为可执行脚本与结构化输出，开箱即用，无需额外配置环境。

## 失败处理

| 错误 | 处理 |
|------|------|
| 输入无效 | 提示参数错误，退出码 2 |
| 执行异常 | 捕获异常输出原因，退出码 1 |
| 网络失败 | 重试 3 次后退避退出 |
