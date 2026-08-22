---
slug: automate-download-freesound
name: automate-download-freesound
displayName: 声音素材 批量抓取 归档整理
description: 自动化批量下载Freesound音频，支持筛选、重试与结构化归档。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SoundArchitect
agent_created: true
trigger_words: ["freesound", "download", "audio", "批量下载", "声音素材", "音效采集", "音频抓取", "素材归档"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Freesound 批量下载与归档 Skill 文档

## 一、能力边界（速查卡）

### 1.1 工具能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 批量下载 | 按关键词、标签、时长、格式等条件批量拉取音频文件 | 下载 200 个雨声白噪音，MP3 格式，时长 10-60 秒 |
| 条件筛选 | 支持 Freesound API 的查询参数组合 | 按 `tag:field_recording` + `duration:[10 TO 60]` 过滤 |
| 断点重试 | 下载失败自动重试，支持指数退避 | 网络抖动时自动重试 3 次，间隔 2s/4s/8s |
| 结构化归档 | 按日期/关键词/标签生成目录树，附带 JSON 元数据 | `output/2024-06-15/rain/` 内含音频 + `meta.json` |
| 配置自检 | 验证 API 凭据与网络连通性 | `--selftest` 返回配置检查报告 |

### 1.2 工具不能做什么

| 限制项 | 说明 |
|--------|------|
| 不绕过付费墙 | 仅下载 Freesound 允许免费下载的音频（CC0/CC-BY 等许可） |
| 不处理版权纠纷 | 使用者须自行确认音频的授权许可与使用范围 |
| 不提供流媒体服务 | 仅支持批量下载，不支持在线播放或实时转码 |
| 不保证下载成功率 | 受 Freesound 服务端限流、文件缺失、网络波动影响 |
| 不自动登录付费账户 | 仅使用 API 凭据，不支持模拟登录或绕过认证 |

### 1.3 适用对象

- 声音设计师：需要大量环境音、拟音素材用于影视/游戏制作
- 播客/视频创作者：需要背景音乐、转场音效
- 研究人员：需要特定声音数据集用于机器学习或声学分析
- 业余爱好者：想建立个人声音素材库

---

## 二、触发方式

### 2.1 触发词

用户对话中出现以下任一词汇即触发本 Skill：

- 直接触发：`freesound`、`download audio`、`批量下载`、`声音素材`
- 语义触发：`音效采集`、`音频抓取`、`素材归档`、`下载声音`

### 2.2 场景映射表

| 用户说（大白话） | 工具实际执行 |
|------------------|-------------|
| "帮我下载一些鸟叫的声音" | 执行 `freesound download audio --query "bird song" --limit 20` |
| "我要找 30 秒左右的电子游戏音效" | 执行 `freesound download audio --tag "videogame" --duration "[20 TO 40]" --limit 50` |
| "把下载的音频按类别放好" | 执行 `freesound download audio --query "rain" --organize-by tag` |
| "上次下载到一半断了，继续下" | 执行 `freesound download audio --resume --output ./output` |
| "检查一下我的配置对不对" | 执行 `freesound download audio --selftest` |

---

## 三、标准流程

### 3.1 前置条件

| 序号 | 条件 | 验证方式 |
|------|------|----------|
| 1 | 已注册 Freesound 账号 | 能登录 freesound.org |
| 2 | 已申请 API 凭据（Client ID + API Key） | 在 freesound.org/apiv2/app/ 创建应用 |
| 3 | 已安装 Python 3.8+ 与依赖包 | 运行 `python --version` 确认 |
| 4 | 已创建 `config.yaml` 配置文件 | 文件存在于当前目录或 `~/.freesound/` |

**config.yaml 模板：**

```yaml
api:
  client_id: "你的Client ID"
  api_key: "你的API Key"
  base_url: "https://freesound.org/apiv2"
download:
  output_dir: "./output"
  max_concurrency: 4
  retry_times: 3
  retry_backoff: [2, 4, 8]
  timeout: 30
filter:
  default_duration: "[0 TO 300]"
  default_format: "mp3"
  min_score: 3.0
```

### 3.2 执行步骤

**第一步：验证配置**

```bash
freesound download audio --selftest
```

预期输出：

```
[OK] API 凭据有效
[OK] 网络连通性正常
[OK] 输出目录可写
[OK] 配置项完整
```

**第二步：小批量试运行**

```bash
freesound download audio --query "rain" --limit 5 --output ./test_output
```

检查 `test_output/` 目录结构：

```
test_output/
├── 2024-06-15_rain/
│   ├── 12345_rain_on_window.mp3
│   ├── 12346_light_rain.mp3
│   └── meta.json
```

**第三步：正式批量下载**

```bash
freesound download audio \
  --query "rain" \
  --tag "field_recording" \
  --duration "[10 TO 120]" \
  --format "mp3" \
  --limit 200 \
  --organize-by tag \
  --output ./output
```

**第四步：检查输出**

```bash
find ./output -type f | wc -l   # 统计文件数
cat ./output/meta.json | jq '.download_summary'  # 查看下载摘要
```

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 音频文件 | `.mp3` / `.wav` / `.ogg` | 保持原始格式，文件名格式：`{id}_{slug}.{ext}` |
| 元数据文件 | `meta.json` | 包含下载时间、查询条件、文件列表、每个文件的 Freesound 元数据 |
| 目录结构 | `{日期}_{查询词}/` | 按 `--organize-by` 参数决定二级目录（tag/query/date） |
| 日志文件 | `download.log` | 记录每次请求的 URL、状态码、耗时、重试次数 |

**meta.json 结构示例：**

```json
{
  "download_time": "2024-06-15T10:30:00Z",
  "query": "rain",
  "total_requested": 200,
  "total_downloaded": 198,
  "failed": [
    {"id": 12345, "reason": "404 Not Found", "retried": 3}
  ],
  "files": [
    {
      "id": 12346,
      "name": "light_rain.mp3",
      "url": "https://freesound.org/data/previews/123/12346_1234-lq.mp3",
      "license": "CC0",
      "duration": 45.2,
      "tags": ["rain", "field_recording"]
    }
  ]
}
```

---

## 四、置信度门控

当遇到以下信息不完整的情况，工具会输出 `[需核实:字段]` 占位符，**不会编造数据**：

| 场景 | 输出示例 | 后续动作 |
|------|----------|----------|
| API 返回的音频时长缺失 | `"duration": [需核实:duration]` | 跳过该文件，记录到 `failed` 列表 |
| 许可证信息不明确 | `"license": [需核实:license]` | 默认不下载，提示用户手动确认 |
| 文件大小未知 | `"size_bytes": [需核实:size_bytes]` | 下载前无法预检，下载后补充 |
| 查询结果总数未知 | `"total_results": [需核实:total_results]` | 按实际下载数记录，不估算 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | API 凭据无效 | "API 认证失败，请检查 config.yaml 中的 client_id 和 api_key" | 1. 登录 Freesound 开发者后台 2. 重新生成 API Key 3. 更新配置文件 4. 重跑 `--selftest` |
| `E002` | 网络超时 | "请求超时（30s），请检查网络或调整 timeout 参数" | 1. 确认网络连通 2. 增大 `timeout` 至 60 3. 降低 `max_concurrency` 至 2 |
| `E003` | 触发限流 | "HTTP 429：请求过于频繁，已自动退避" | 1. 等待 60 秒 2. 将 `max_concurrency` 调低 3. 增加 `retry_backoff` 间隔 |
| `E004` | 文件不存在 | "音频文件 404，可能已被原作者删除" | 1. 跳过该文件 2. 记录到 `failed` 列表 3. 继续下载其余文件 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 1. 确认目录存在 2. 修改权限 `chmod 755 ./output` 3. 或更换 `--output` 路径 |
| `E006` | 配置缺失 | "未找到 config.yaml，请先创建配置文件" | 1. 复制模板 2. 填入凭据 3. 保存到当前目录或 `~/.freesound/` |

---

## 六、FAQ 反模式

### 反模式 1：一次性下载过多

**错误做法**：直接 `--limit 10000` 试图一次拉取全部结果。

**后果**：触发限流（429），大量请求失败，IP 可能被临时封禁。

**正确做法**：分批次下载，每批 200-500 条，间隔 10-15 秒。使用 `--offset` 参数翻页。

### 反模式 2：忽略许可证筛选

**错误做法**：不检查 `license` 字段，下载所有结果。

**后果**：可能下载到 "All Rights Reserved" 的音频，用于商业项目会侵权。

**正确做法**：在查询参数中增加 `--license "CC0,CC-BY"`，并在下载前二次确认。

### 反模式 3：并发数设置过高

**错误做法**：`max_concurrency: 16` 试图加速下载。

**后果**：Freesound API 限流阈值约为 10 req/s，过高并发导致大量 429 错误。

**正确做法**：从 4 开始，逐步调至 8，观察日志中 429 出现频率，维持在 5% 以下。

### 反模式 4：不保留元数据

**错误做法**：下载完成后删除 `meta.json`，只保留音频文件。

**后果**：后续无法追溯音频来源、许可证、作者信息，使用受限。

**正确做法**：始终保留 `meta.json`，建议与音频文件一同归档。

### 反模式 5：忽略重试机制

**错误做法**：下载失败后立即手动重跑整个命令。

**后果**：重复下载已成功的文件，浪费流量和时间。

**正确做法**：使用 `--resume` 参数，工具会跳过已存在的文件，只下载缺失部分。

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 配置
cp config.example.yaml config.yaml  # 填入你的 API 凭据

# 2. 自检
freesound download audio --selftest

# 3. 试下载 5 条
freesound download audio --query "rain" --limit 5

# 4. 正式下载 200 条
freesound download audio --query "rain" --limit 200 --organize-by tag
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」确认工具满足需求
2. 在 Freesound 开发者后台申请 API 凭据
3. 创建 `config.yaml` 填入凭据
4. 运行 `freesound download audio --selftest` 验证配置
5. 使用 `--limit 5` 小批量试运行
6. 检查输出目录结构与元数据文件

### 7.3 进阶路径（熟练使用）

1. **自定义筛选**：组合 `--tag`、`--duration`、`--format`、`--license` 参数实现精确筛选
2. **调整并发参数**：根据网络状况将 `max_concurrency` 从 4 调至 8，观察限流情况
3. **编写后处理脚本**：在下载完成后自动执行重命名、生成播放列表、提取音频特征
4. **集成 CI/CD**：通过命令行接口在定时任务中调用，实现每日增量同步

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--query` | string | 必填 | 搜索关键词，支持空格分隔的多词 |
| `--tag` | string | 空 | 按标签过滤，逗号分隔多个标签 |
| `--duration` | string | `[0 TO 300]` | 时长范围，格式 `[min TO max]` |
| `--format` | string | `mp3` | 音频格式：`mp3`/`wav`/`ogg` |
| `--license` | string | 空 | 许可证过滤：`CC0`/`CC-BY`/`CC-BY-NC` |
| `--limit` | int | 50 | 最大下载数量，范围 1-1000 |
| `--offset` | int | 0 | 结果偏移量，用于分页 |
| `--organize-by` | string | `query` | 归档方式：`query`/`tag`/`date` |
| `--output` | string | `./output` | 输出目录路径 |
| `--resume` | bool | false | 断点续传，跳过已存在文件 |
| `--selftest` | bool | false | 运行配置自检 |
| `--version` | bool | false | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于下载内容的合法性、版权合规性、使用后果等。作者不对因使用本 Skill 导致的任何直接或间接损失负责。

2. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

4. **服务变更**：Freesound 网站可能随时变更其服务条款、页面结构或 API，本 Skill 可能因此失效，作者不承担更新义务。

5. **合规使用**：使用者须遵守 Freesound 的服务条款、API 使用政策以及音频文件的原始许可证要求。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

版权所有 (c) 2024 SoundArchitect

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士使用本软件的权利，包括但不限于使用、复制、修改、合并、出版、分发、再许可和/或出售软件副本的权利，并允许向其提供软件的人士在遵守以下条件的前提下这样做：

上述版权声明和本许可声明应包含在软件的所有副本或重要部分中。

本软件按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他方面，由软件或软件的使用或其他交易引起、产生或与之相关。

---

*本文档由 AI 辅助生成，仅供参考。使用前请阅读 Freesound API 官方文档。*
