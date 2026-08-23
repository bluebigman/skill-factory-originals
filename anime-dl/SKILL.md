---
slug: anime-dl
name: anime-dl
displayName: 番剧抓取 批量下载 任务队列
description: 命令行多站点解析与批量下载动漫资源，支持任务队列管理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge
agent_created: true
trigger_words: ["anime-dl", "动漫下载", "番剧下载", "crunchyroll下载", "funimation下载", "批量抓取番剧", "剧集队列下载"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# anime-dl 技能手册

本 Skill 由 AI 辅助生成，仅供参考。使用前请自行判断适用性，并遵守当地法律法规。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 |
|--------|------|
| 多站点解析 | 内置 Crunchyroll、Funimation 等站点的搜索与剧集列表解析逻辑 |
| 批量下载 | 支持整部番剧全量下载，或通过参数限定集数范围 |
| 任务队列 | 支持从文件读取多部番剧，依次排队下载 |
| 结构化输出 | 每集下载完成后输出 JSON 格式报告，含状态、路径、大小、耗时 |
| 环境自检 | 通过 `--selftest` 验证运行环境与依赖完整性 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不绕过付费墙 | 仅解析公开可访问的元数据与资源链接，不破解 DRM 或付费内容 |
| 不保证下载速度 | 实际速度取决于网络环境与目标站点响应 |
| 不处理播放列表 | 仅支持单集文件下载，不支持 m3u8 流媒体切片合并 |
| 不提供图形界面 | 纯命令行工具，无 GUI 封装 |

### 1.3 适用对象

- 需要批量整理番剧资源的个人用户
- 希望将下载流程脚本化的技术爱好者
- 需要定时自动更新剧集库的媒体管理场景

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一短语即可唤起本技能：

- `anime-dl`
- `动漫下载`
- `番剧下载`
- `crunchyroll下载`
- `funimation下载`
- `批量抓取番剧`
- `剧集队列下载`

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我把这部番全下了" | 解析番剧名 → 获取全部剧集 → 构建全量下载队列 |
| "只要前六集" | 解析番剧名 → 用 `--episodes 1-6` 限定范围 |
| "我有十部番要下" | 用 `--batch file.txt` 从文件读取多部番剧名 |
| "先检查一下环境能不能用" | 运行 `--selftest` 验证依赖完整性 |
| "下完了给我个清单" | 自动生成 JSON 报告，列出每集状态与文件信息 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 检查方式 |
|------|----------|
| Python 3.8+ | `python3 --version` |
| 网络连通性 | `curl -I https://www.crunchyroll.com` 返回 200 |
| 磁盘空间 | `df -h` 确认剩余空间 ≥ 预估下载体积 × 1.2 |
| 依赖完整性 | 运行 `anime-dl --selftest`，输出 `OK` 即通过 |

### 3.2 执行步骤

#### 步骤 1：初始化检查

```bash
anime-dl --selftest
```

输出 `OK` 表示环境就绪。若输出错误码，参照「错误码体系」章节排查。

#### 步骤 2：输入解析

支持两种输入方式：

| 方式 | 示例 | 说明 |
|------|------|------|
| 直接传番剧名 | `anime-dl "葬送的芙莉莲"` | 适用于单部番剧 |
| 从文件读取 | `anime-dl --batch list.txt` | 每行一部番剧名，适用于批量任务 |

#### 步骤 3：搜索与解析

工具将番剧名发送至目标站点搜索接口，解析返回的剧集列表。此阶段输出：

```
[解析] 正在搜索「葬送的芙莉莲」...
[解析] 找到 28 集，来自 crunchyroll
[解析] 剧集列表构建完成，共 28 个任务
```

#### 步骤 4：任务队列构建

默认下载全部集数。可用参数控制范围：

| 参数 | 示例 | 说明 |
|------|------|------|
| `--episodes` | `--episodes 1-6` | 限定下载第 1 至 6 集 |
| `--batch` | `--batch file.txt` | 从文件读取多部番剧 |
| `--source` | `--source funimation` | 指定解析站点（默认自动选择） |
| `--output` | `--output /media/anime` | 指定下载目录（默认当前目录） |

#### 步骤 5：执行下载

逐集下载，每集完成后校验文件大小非零。进度条显示当前集数与总进度：

```
[下载] 第 3/28 集 | 葬送的芙莉莲 - 第03集.mp4 | ████████░░ 78% | 1.2 GB / 1.5 GB
```

#### 步骤 6：输出结构化结果

完成后生成 JSON 报告，示例：

```json
{
  "task": "葬送的芙莉莲",
  "source": "crunchyroll",
  "total_episodes": 28,
  "completed": 28,
  "failed": 0,
  "results": [
    {
      "episode": 1,
      "status": "success",
      "file_path": "/media/anime/葬送的芙莉莲/第01集.mp4",
      "size_bytes": 1572864000,
      "duration_seconds": 342
    }
  ]
}
```

#### 步骤 7：下一步建议

输出完成后提示：

- 阅读速查卡，运行 `--selftest` 确认环境
- 用一部短番（12 集以内）试运行
- 查看生成的 JSON 报告，理解输出结构
- 尝试 `--episodes` 参数控制下载范围

进阶用法：

- 编写脚本调用 `anime-dl` 并解析 JSON 输出，集成到媒体管理流程
- 使用 `--batch` 配合定时任务（cron）实现夜间自动更新
- 研究 `--source` 参数，为新增站点编写解析器插件
- 结合 `--output` 与日志系统，构建完整的下载监控面板

### 3.3 输出规范

| 输出类型 | 格式 | 去向 |
|----------|------|------|
| 进度信息 | 文本 + 进度条 | stdout |
| 错误信息 | 错误码 + 提示话术 | stderr |
| 最终报告 | JSON | 当前目录 `anime-dl-report.json` |

---

## 四、置信度门控

当遇到以下情况时，工具会输出 `[需核实:字段]` 占位符，而非编造数据：

| 场景 | 输出示例 |
|------|----------|
| 剧集标题无法解析 | `[需核实:episode_title]` |
| 文件大小校验失败 | `[需核实:size_bytes]` |
| 站点返回异常响应 | `[需核实:source_status]` |
| 剧集总数不确定 | `[需核实:total_episodes]` |

用户应依据占位符提示，手动核实对应字段后决定是否继续。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 依赖缺失 | "缺少必要依赖，请运行 --selftest 查看详情" | 按提示安装缺失包 |
| `E002` | 网络超时 | "目标站点响应超时，请检查网络" | 确认网络连通后重试 |
| `E003` | 番剧未找到 | "未找到匹配的番剧，请检查名称拼写" | 尝试使用日文原名或英文名 |
| `E004` | 剧集解析失败 | "剧集列表解析失败，站点结构可能已变更" | 更新解析器或更换 --source |
| `E005` | 下载中断 | "下载中断，文件不完整" | 重新运行并指定缺失集数 |
| `E006` | 磁盘空间不足 | "磁盘空间不足，无法继续下载" | 清理空间或更换 --output 路径 |
| `E007` | 批量文件格式错误 | "批量文件每行应为一个番剧名" | 检查文件格式后重试 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|---------------------|----------|
| 依赖不全 | 直接运行下载命令，报错后不知所措 | 先运行 `--selftest` 确认环境 |
| 集数范围写错 | `--episodes 6-1` 导致空队列 | 使用升序范围，如 `--episodes 1-6` |
| 批量文件含空行 | 空行被当作番剧名，报 E003 | 确保每行非空，且无首尾空格 |
| 磁盘空间预估不足 | 下载到一半报 E006 | 提前用 `df -h` 检查空间 |
| 忽略 JSON 报告 | 下载完成后不检查报告，遗漏失败集 | 每次完成后查看 `anime-dl-report.json` |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 同时运行多个实例 | 任务队列冲突，文件覆盖 | 使用 `--batch` 串行处理 |
| 用 `sudo` 运行 | 权限过大，文件归属混乱 | 使用普通用户 + 可写目录 |
| 下载后立即删除源文件 | 无法回溯校验 | 保留至少一周后再清理 |
| 忽略 `--source` 参数 | 自动选择可能非最优站点 | 明确指定目标站点 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
anime-dl --selftest                    # 环境检查
anime-dl "番剧名"                       # 全量下载
anime-dl "番剧名" --episodes 1-6       # 限定集数
anime-dl --batch list.txt              # 批量下载
anime-dl --output /path/to/dir         # 指定目录
```

### 7.2 分层次阅读路径

**新手路径**：能力边界 → 触发方式 → 标准流程（步骤 1-3）→ 错误码 E001-E003

**进阶路径**：标准流程（步骤 4-7）→ 置信度门控 → 错误码全表 → FAQ 反模式

**专家路径**：研究 `--source` 参数 → 编写自定义解析器插件 → 结合 cron 与 JSON 报告构建自动化流水线

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本工具仅用于技术学习与个人合法用途，不得用于侵犯他人版权或违反任何法律法规的行为。
2. **禁止反向工程**：不得对本 Skill 的代码、文档进行反向工程、反编译或试图提取底层算法（法律允许的除外）。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
4. **内容合法性**：使用者需自行确认下载内容的合法性，并遵守所在地区的版权法规。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

MIT License

Copyright (c) 2024 FlowForge

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

<!-- professional-license-embedded -->
