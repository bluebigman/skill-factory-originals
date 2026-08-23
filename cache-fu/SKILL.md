---
slug: cache-fu
name: cache-fu
displayName: 缓存清理 磁盘释放 安全回滚
description: 智能扫描系统缓存，安全清理并支持回滚，释放磁盘空间。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinusTech
agent_created: true
trigger_words: ["cache", "缓存", "清理", "cleanup", "disk space", "磁盘空间", "释放空间", "垃圾文件"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# cache-fu Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 缓存扫描 | 扫描系统常见缓存目录，统计大小与最后访问时间 | `~/.cache/pip`、`~/.cache/thumbnails` |
| 安全清理 | 将待清理文件移入回收站而非直接删除 | 移动至 `~/.cache-fu/trash/` |
| 回滚恢复 | 从回收站恢复误删文件 | `cache-fu --restore <备份ID>` |
| 空间报告 | 输出清理前后磁盘空间对比 | 清理前 856MB → 清理后 0MB |
| 白名单保护 | 指定目录或应用缓存不被清理 | `--whitelist pip` |
| 自动清理 | 回收站超过 30 天的备份自动删除 | 定期执行 `--purge-trash` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不清理系统关键文件 | 不触碰 `/usr`、`/etc`、`/var` 等系统目录 |
| 不清理运行中进程的缓存 | 若文件被进程占用，会跳过并提示 |
| 不清理用户未授权的目录 | 仅处理 `~/.cache` 下已知缓存目录 |
| 不保证清理后空间一定增加 | 若缓存文件被占用或为硬链接，可能无法释放 |

### 1.3 适用对象

- 个人开发者：清理 pip、npm、yarn 等包管理器缓存
- 桌面用户：清理缩略图、浏览器缓存
- CI/CD 运维：定期清理构建缓存，释放磁盘空间

---

## 二、触发方式

### 2.1 触发词

`cache`、`缓存`、`清理`、`cleanup`、`disk space`、`磁盘空间`、`释放空间`、`垃圾文件`

### 2.2 场景映射表

| 用户说（大白话） | 触发动作 |
|------------------|----------|
| "我磁盘快满了，帮我看看" | 执行 `cache-fu --scan` 扫描缓存分布 |
| "清理一下缓存吧" | 执行 `cache-fu --preview` 预览后 `--clean` |
| "刚才误删了，能恢复吗" | 执行 `cache-fu --restore` 列出回收站并恢复 |
| "帮我定期清理" | 配置 cron 定期执行 `--scan` 并邮件通知 |
| "别动 pip 的缓存" | 添加 `--whitelist pip` 保护 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 检查方式 | 通过标准 |
|------|----------|----------|
| 工具已安装 | `which cache-fu` | 返回路径 |
| 环境自检通过 | `cache-fu --selftest` | 输出 `OK` |
| 磁盘空间充足 | `df -h ~` | 剩余空间 > 1GB |
| 回收站目录可写 | `test -w ~/.cache-fu/trash` | 返回 `true` |

### 3.2 执行步骤

1. **环境自检**：运行 `cache-fu --selftest`，确认依赖（`du`、`mv`、`date`）可用。
2. **扫描缓存**：运行 `cache-fu --scan`，输出缓存目录列表，包含大小与最后访问时间。
3. **预览清理**：运行 `cache-fu --preview`，显示将被清理的文件清单及预计释放空间。
4. **执行清理**：确认无误后运行 `cache-fu --clean`，文件移入回收站并生成日志。
5. **生成报告**：运行 `cache-fu --report`，输出清理前后空间对比，保存为记录。

### 3.3 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 扫描结果 | 表格 | `~/.cache/pip (856 MB) - 非活跃，最后访问 23 天前` |
| 清理日志 | 文本文件 | `~/.cache-fu/logs/cleanup_20260813_143000.log` |
| 空间报告 | 对比表 | `清理前: 2.3GB → 清理后: 1.4GB` |
| JSON 输出 | 结构化数据 | `{"cleaned": 856, "unit": "MB"}` |

---

## 四、置信度门控

当以下信息不足时，输出 `[需核实:字段]` 占位，不编造数据：

| 场景 | 占位示例 |
|------|----------|
| 缓存目录大小未知 | `[需核实:~/.cache/pip 大小]` |
| 最后访问时间未知 | `[需核实:最后访问时间]` |
| 回收站备份 ID 未知 | `[需核实:备份ID]` |
| 白名单规则冲突 | `[需核实:白名单规则]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 工具未安装 | `cache-fu 未找到，请先安装` | 运行 `pip install cache-fu` |
| `E002` | 自检失败 | `依赖缺失: du 命令不可用` | 安装 coreutils 包 |
| `E003` | 目录不可写 | `回收站目录不可写` | 运行 `chmod +w ~/.cache-fu/trash` |
| `E004` | 文件被占用 | `文件被进程占用，跳过: xxx` | 关闭相关进程后重试 |
| `E005` | 白名单冲突 | `目录在白名单中，跳过清理` | 移除白名单或调整规则 |
| `E006` | 恢复失败 | `备份不存在或已过期` | 检查回收站目录或备份 ID |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式 | 正确做法 |
|----|--------|----------|
| 直接删除缓存 | `rm -rf ~/.cache/pip` | 使用 `cache-fu --clean` 移入回收站 |
| 忽略预览 | 直接执行 `--clean` | 先执行 `--preview` 确认清单 |
| 清理后不检查 | 清理完就完事 | 执行 `--report` 确认空间释放 |
| 无白名单保护 | 清理所有缓存 | 为重要应用添加 `--whitelist` |
| 回收站无限膨胀 | 从不清理回收站 | 定期执行 `--purge-trash`（30 天自动删除） |

### 6.2 反模式对照

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 清理所有 `~/.cache` | 可能误删重要缓存 | 按目录逐个扫描，确认后清理 |
| 依赖 `du` 输出 | 大目录扫描慢 | 使用 `--json` 输出，配合监控系统 |
| 手动恢复文件 | 容易出错 | 使用 `--restore` 自动恢复 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```bash
# 1. 自检
cache-fu --selftest

# 2. 扫描
cache-fu --scan

# 3. 预览
cache-fu --preview

# 4. 清理
cache-fu --clean

# 5. 报告
cache-fu --report
```

### 7.2 进阶路径（有经验用户）

1. **定期清理**：配置 cron 每周执行 `--scan`，每月执行 `--clean`。
2. **监控告警**：配置 cron 定期执行 `--scan --json`，对接监控系统。
3. **自定义白名单**：编辑 `~/.cache-fu/config.yaml`，添加保护规则。
4. **回收站管理**：定期执行 `--purge-trash`，清理超过 30 天的备份。

---

## 八、参数速查表

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--scan` | 扫描缓存目录 | 无 |
| `--preview` | 预览清理清单 | 无 |
| `--clean` | 执行清理 | 无 |
| `--restore <ID>` | 恢复指定备份 | 无 |
| `--report` | 输出空间报告 | 无 |
| `--json` | 输出 JSON 格式 | `false` |
| `--whitelist <dir>` | 添加白名单目录 | 空 |
| `--purge-trash` | 清理过期回收站 | 30 天 |
| `--selftest` | 环境自检 | 无 |
| `--version` | 显示版本 | 无 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用须知**

1. 使用者自行承担全部责任。本 Skill 提供的所有操作指导仅供参考，使用者应自行评估风险并确认操作安全性。
2. 禁止反向工程。不得对本 Skill 的代码、逻辑、文档进行逆向分析、反编译或试图提取底层实现。
3. 本 Skill 不提供任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
4. 使用本 Skill 造成的任何直接或间接损失，作者不承担任何责任。
5. 使用本 Skill 即表示您已阅读、理解并同意本协议全部条款。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
