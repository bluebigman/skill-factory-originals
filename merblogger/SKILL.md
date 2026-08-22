---
slug: merblogger
name: merblogger
displayName: 博客发布 内容管理 批量推送
description: 基于Merb框架的博客发布与内容管理工具，支持结构化输出与批量处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["merblogger", "博客发布", "内容管理", "文章推送", "站点维护", "批量发文", "博客维护"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# merblogger 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 博客发布 | 将本地 Markdown/HTML 文件推送至 Merb 博客站点 | 单篇或批量发布文章 |
| 内容管理 | 对已发布文章进行状态查询、列表导出、字段核对 | 日常维护、内容审计 |
| 文章推送 | 支持按目录批量推送，自动识别文件名与标题映射 | 多篇文章一次性上线 |
| 站点维护 | 提供基础站点连通性检查与配置校验 | 部署后自检、排障 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持自定义主题开发 | 主题样式需在 Merb 框架内另行处理 |
| 不支持评论系统管理 | 评论数据需通过 Merb 后台或 API 操作 |
| 不支持图片自动上传 | 图片需预先上传至可达 URL 或站点媒体库 |
| 不提供 SEO 优化建议 | 关键词与元描述需人工撰写 |

### 1.3 适用对象

- 使用 Merb 框架搭建博客的开发者或运维人员
- 需要批量导入历史文章的内容迁移团队
- 日常维护多个博客站点的内容运营者

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`merblogger`、`博客发布`、`内容管理`、`文章推送`、`站点维护`
- 补充触发词：`批量发文`、`博客维护`、`文章导入`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 | 对应能力 |
|------------------|--------------|----------|
| "帮我把这几篇文章发到博客上" | 执行批量发布 | 文章推送 |
| "看看博客现在有哪些文章" | 查询文章列表 | 内容管理 |
| "我改了一篇文章，帮我更新一下" | 单篇更新 | 博客发布 |
| "博客好像打不开了，帮我看看" | 站点连通性检查 | 站点维护 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 文件格式 | `.md` 或 `.html`，UTF-8 编码 | 文件头检查 |
| 命名规范 | 文件名格式：`YYYY-MM-DD-slug.md` | 正则匹配 |
| 目录结构 | 所有待处理文件位于同一目录 | `ls` 确认 |
| 站点配置 | `config.yml` 中站点地址与认证信息完整 | 读取配置文件 |
| 备份 | 原始文件保留副本，命名加 `.bak` 后缀 | 文件系统确认 |

### 3.2 执行步骤（分步编号）

1. **环境确认**：检查当前目录下是否存在 `config.yml`，若不存在则提示用户提供站点地址与认证方式。
2. **文件清单生成**：扫描目录下所有符合命名规范的文件，生成待处理清单，输出文件数量与文件名列表。
3. **单样本试运行**：取清单中第一个文件，执行单篇发布，核对返回结果中的 `status`、`post_id`、`url` 字段。
4. **字段核对**：将试运行输出与源文件 frontmatter 中的 `title`、`date`、`tags` 进行比对，确认一致。
5. **批量执行**：确认无误后，对剩余文件按顺序执行发布，每篇间隔 1 秒，避免请求过载。
6. **结果汇总**：生成执行报告，包含成功数、失败数、失败原因与对应文件名。
7. **备份留存**：将原始文件目录打包为 `backup-YYYYMMDD-HHMMSS.tar.gz`，保留在上级目录。

### 3.3 输出规范

每次执行后输出结构化结果：

```json
{
  "operation": "publish",
  "total": 12,
  "success": 11,
  "failed": 1,
  "results": [
    {
      "file": "2024-01-15-hello-world.md",
      "status": "success",
      "post_id": 1024,
      "url": "https://example.com/posts/hello-world"
    },
    {
      "file": "2024-01-16-broken-post.md",
      "status": "failed",
      "error_code": "E4002",
      "error_message": "frontmatter missing title"
    }
  ]
}
```

---

## 四、置信度门控

当遇到以下情况时，输出 `[需核实:字段名]` 占位符，不进行推测或编造：

| 场景 | 占位符示例 |
|------|------------|
| 文件缺少 `title` 字段 | `[需核实:title]` |
| 站点地址无法确认 | `[需核实:site_url]` |
| 认证信息不完整 | `[需核实:auth_token]` |
| 日期格式无法解析 | `[需核实:date]` |

**原则**：信息不足时，宁可中断流程并提示用户补充，也不使用默认值或猜测值。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E4001 | 文件不存在 | "未找到指定文件，请检查路径" | 确认路径后重试 |
| E4002 | frontmatter 缺少必填字段 | "文章缺少 title 或 date 字段" | 补全字段后重试 |
| E4003 | 站点连接失败 | "无法连接目标站点，请检查网络或地址" | 检查网络与站点状态 |
| E4004 | 认证失败 | "认证信息无效，请检查 token 或用户名密码" | 更新配置后重试 |
| E4005 | 文件命名不规范 | "文件名不符合 YYYY-MM-DD-slug.md 格式" | 重命名文件后重试 |
| E4006 | 批量执行中断 | "批量执行过程中出现异常，已停止" | 查看日志，修复后从失败点继续 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 跳过试运行直接批量 | 直接对 100 个文件执行发布，结果全部失败 | 先跑 1 个样本，确认输出格式正确后再批量 |
| 覆盖原始文件 | 发布成功后删除本地 `.md` 文件 | 保留原始文件，另存备份 |
| 忽略失败条目 | 只看成功数，不检查失败原因 | 逐条查看失败原因，修复后重试 |
| 手动修改输出结果 | 手工编辑 JSON 报告中的字段 | 重新执行命令生成新报告 |
| 依赖默认配置 | 不检查 `config.yml` 直接执行 | 每次执行前确认配置项完整 |

---

## 七、渐进式披露阅读路径

### 7.1 速查卡（新手必读）

- 使用前：确认文件命名规范、站点配置、备份文件
- 执行时：先试运行 → 核对字段 → 批量执行
- 执行后：查看报告 → 处理失败项 → 保留备份

### 7.2 进阶阅读（有经验用户）

- 深入理解错误码体系，建立自动化重试机制
- 结合 CI/CD 流程，将发布集成到部署管线
- 自定义输出格式，对接内部监控系统

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于内容合规性、数据准确性及操作后果。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行逆向分析、反编译或试图提取源代码。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 独立技能工坊

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

<!-- professional-license-embedded -->
