---
slug: textual
name: Textual TUI 脚手架
displayName: 终端界面 快速搭建 组件装配
description: 依据组件清单与主题，一键生成可运行的 Textual 终端应用骨架。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 终端工坊
agent_created: true
trigger_words: ["textual", "tui", "终端界面", "脚手架", "cli应用", "终端应用", "命令行界面", "文本界面"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Textual TUI 脚手架 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 适用范围

| 维度 | 说明 |
|------|------|
| 目标用户 | 需要快速搭建终端交互界面的 Python 开发者 |
| 输入要求 | 组件清单（如：Header、DataTable、Button）+ 主题偏好（如：暗色、简约） |
| 输出产物 | 可运行的 Textual 应用骨架（单文件或多文件结构） |
| 运行环境 | Python 3.8+（推荐 3.10+），支持 ANSI 转义序列的终端 |

### 1.2 能力清单

**可以做到：**

- 根据组件清单生成 `compose()` 方法中的组件装配代码
- 根据主题偏好生成对应的 CSS 样式文件（或内联样式）
- 生成基础的事件处理方法（如 `on_button_pressed`、`on_mount`）
- 提供多文件项目结构建议（`app.py`、`widgets.py`、`styles.css`）
- 生成 `run_worker` 异步任务处理示例

**不能做到：**

- 无法生成完整的业务逻辑（如数据库操作、API 调用）
- 无法替代 Textual 官方文档的学习
- 无法保证生成的代码在特定终端环境下 100% 兼容
- 无法处理 Textual 版本更新带来的 API 变更

### 1.3 适用对象

- 刚接触 Textual 的初学者，需要一个可运行的起点
- 需要快速原型验证的开发者
- 希望了解 Textual 项目结构的开发者

---

## 二、触发方式

### 2.1 触发词

当用户输入以下关键词时，本 Skill 将被激活：

- `textual`、`tui`、`终端界面`、`脚手架`、`cli应用`
- 补充触发词：`终端应用`、`命令行界面`、`文本界面`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我搭一个终端界面" | 需要一个 Textual 应用骨架 | 生成基础应用代码 |
| "要一个带表格和按钮的界面" | 需要 DataTable + Button 组件 | 生成对应组件装配代码 |
| "界面要好看一点" | 需要自定义样式 | 生成 CSS 样式文件 |
| "要能处理耗时任务" | 需要异步处理 | 生成 `run_worker` 示例 |

---

## 三、标准流程

### 3.1 前置条件

| 检查项 | 要求 | 验证方法 |
|--------|------|----------|
| Python 版本 | 3.8+（推荐 3.10+） | `python --version` |
| Textual 库 | 已安装 | `pip show textual` |
| 终端环境 | 支持 ANSI 转义 | 运行 `echo -e "\033[31mred\033[0m"` 查看是否显示红色 |
| 网络连接 | 可用（如需安装依赖） | `ping pypi.org` |

### 3.2 执行步骤

**Step 1：收集需求**

向用户确认以下信息：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 组件清单 | 需要的组件类型（逗号分隔） | Header, Footer |
| 主题偏好 | 暗色/亮色/自定义 | 暗色 |
| 项目名称 | 应用名称 | my_app |
| 文件结构 | 单文件/多文件 | 单文件 |

**Step 2：生成骨架代码**

根据收集的参数，生成以下内容：

1. 主应用文件（`app.py` 或单文件）
2. 组件装配代码（`compose()` 方法）
3. 基础样式（CSS）
4. 事件处理示例

**Step 3：输出规范**

生成的代码必须包含：

- 完整的 `App` 子类定义
- `compose()` 方法返回组件列表
- 至少一个事件处理方法
- 应用入口（`if __name__ == "__main__":` 块）

### 3.3 输出示例

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, DataTable

class MyApp(App):
    CSS = """
    Screen {
        background: #1e1e1e;
    }
    Button {
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Button("点击我", id="main_button")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "名称")
        table.add_row("1", "示例数据")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.notify("按钮被点击了！")

if __name__ == "__main__":
    MyApp().run()
```

---

## 四、置信度门控

### 4.1 信息不足处理

当用户提供的信息不足以生成完整代码时，使用以下占位符：

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `[需核实:组件类型]` | 组件类型不明确 | `yield [需核实:组件类型]()` |
| `[需核实:事件名称]` | 事件名称不确定 | `def on_[需核实:事件名称](self):` |
| `[需核实:样式属性]` | 样式属性不明确 | `[需核实:样式属性]: value;` |

### 4.2 不编造原则

- 不猜测 Textual API 的具体行为
- 不虚构不存在的组件或方法
- 不假设用户的终端环境配置

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | Python 版本过低 | "检测到 Python 版本低于 3.8，请升级" | 升级 Python 至 3.8+ |
| E002 | Textual 未安装 | "未检测到 Textual 库，请先安装" | 运行 `pip install textual` |
| E003 | 组件名称无效 | "组件 'XXX' 不是有效的 Textual 组件" | 检查组件名称拼写，参考官方文档 |
| E004 | CSS 语法错误 | "生成的 CSS 存在语法问题" | 检查 CSS 缩进和属性名 |
| E005 | 事件绑定失败 | "事件处理方法未正确绑定" | 确认方法命名符合 `on_` 前缀规范 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 组件顺序混乱 | 随意排列组件，不关注布局 | 按逻辑顺序排列，Header 在上，Footer 在下 |
| 忽略异步处理 | 在 `on_mount` 中直接执行耗时操作 | 使用 `run_worker` 处理耗时任务 |
| CSS 过度设计 | 添加大量复杂样式导致性能下降 | 保持样式简洁，优先使用内置主题 |
| 不处理异常 | 没有 try-except 块 | 在关键操作中添加异常处理 |
| 忽略版本兼容 | 使用最新 API 不考虑兼容性 | 查阅文档确认 API 在当前版本可用 |

### 6.2 反模式示例

```python
# 反模式：在 on_mount 中直接执行耗时操作
def on_mount(self):
    data = self.fetch_data_from_api()  # 阻塞主线程
    self.update_table(data)

# 正确做法：使用 run_worker
def on_mount(self):
    self.run_worker(self.fetch_data())

async def fetch_data(self):
    data = await self.fetch_data_from_api()
    self.update_table(data)
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 安装依赖：`pip install textual`
2. 创建应用：继承 `App` 类，实现 `compose()` 方法
3. 运行应用：`MyApp().run()`
4. 添加组件：在 `compose()` 中 `yield` 组件实例
5. 样式定制：通过 `CSS` 类属性或外部 CSS 文件

### 7.2 分层次阅读路径

**新手路径（30 分钟上手）：**

1. 阅读「一、能力边界」了解适用范围
2. 使用默认参数生成第一个骨架，运行查看效果
3. 尝试修改 `compose()` 中的组件顺序，观察布局变化
4. 参考「六、FAQ 反模式」避免常见错误

**进阶路径（深入掌握）：**

1. 阅读 Textual 官方文档，了解 `Widget` 生命周期和消息传递机制
2. 在生成的 CSS 基础上，添加自定义样式（如渐变背景、动画效果）
3. 实现 `on_mount` 方法，在应用启动时加载数据
4. 使用 `run_worker` 处理耗时任务（如网络请求、文件读取）
5. 将单文件拆分为多文件项目：`app.py`、`widgets.py`、`styles.css`

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应确保生成内容的使用符合当地法律法规及所在组织的政策要求。不得将生成代码用于任何非法目的。使用者自行承担因使用本 Skill 产生的全部责任。

2. **合规使用**：使用者应确保生成内容的使用符合当地法律法规及所在组织的政策要求。不得将生成代码用于任何非法目的。

3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。

4. **禁止反向工程**：使用者不得对本 Skill 的提示词、内部逻辑、评分机制进行反向工程、破解或提取。

5. **内容修改**：使用者有权对生成内容进行修改、分发或商用，但需保留原始版权声明。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 终端工坊

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

*本 Skill 文档由 AI 辅助生成，仅供参考。使用前请阅读 Textual 官方文档获取最新信息。*
