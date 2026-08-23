---
slug: cheat.sh
name: cheat-sh
displayName: 开发速查 代码示例 即时检索
description: 一条命令获取编程语言与工具的代码示例，无需安装，开发必备速查手册。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: dev-toolsmith
agent_created: true
trigger_words: ["cheat.sh", "命令行速查", "代码示例", "速查手册", "开发查询", "编程速查", "代码片段检索"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# cheat.sh 技能文档

## 一、能力边界（一页纸速查卡）

### 能做

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 主题查询 | 获取指定语言/工具的基础用法 | `cheat.sh python/list --plain` |
| 关键词组合 | 用 `+` 连接多个关键词缩小范围 | `cheat.sh python/list+sort --plain` |
| 多结果索引 | 用 `--index` 参数选取第 N 条结果 | `cheat.sh python/list --index 2 --plain` |
| 本地缓存 | 用 `--cache` 保存查询结果供离线使用 | `cheat.sh python/list --cache` |
| 批量脚本 | 支持 shell 循环批量查询多个主题 | 见「进阶用法」 |
| 自检与版本 | 验证安装与查看版本 | `cheat.sh --selftest` / `cheat.sh --version` |

### 不能做

- 不能执行代码，只返回示例文本
- 不能保证示例与你的项目环境完全兼容
- 不能替代官方文档的完整阅读
- 不能离线查询未缓存的内容

### 适用对象

- 日常开发中需要快速回忆 API 用法的程序员
- 学习新语言/框架时希望快速上手的学习者
- 需要在无 IDE 环境下（如 SSH 终端）查阅代码示例的运维人员

---

## 二、触发方式

### 触发词

- 直接使用 `cheat.sh` 命令
- 对话中提及「命令行速查」「代码示例」「速查手册」「开发查询」等场景词

### 场景映射表

| 用户说（大白话） | 实际执行 |
|------------------|----------|
| "我想查一下 Python 列表怎么用" | `cheat.sh python/list --plain` |
| "Python 里怎么给列表排序？" | `cheat.sh python/list+sort --plain` |
| "给我看第二条结果" | `cheat.sh python/list --index 2 --plain` |
| "帮我存下来以后离线看" | `cheat.sh python/list --cache` |
| "查一下这个工具能不能用" | `cheat.sh --selftest` |

---

## 三、标准流程

### 前置条件

- 已安装 cheat.sh 命令行工具（安装方式见官方仓库）
- 网络可连通（首次查询或更新缓存时需要）

### 执行步骤

1. **确定查询主题**：明确你要查的语言/工具名称，如 `python`、`go`、`git`、`docker`
2. **构造基础查询**：`cheat.sh <主题>/list --plain`
   - 例：`cheat.sh python/list --plain` 返回 Python 相关主题列表
3. **添加关键词过滤**：用 `+` 连接多个关键词
   - 例：`cheat.sh python/list+sort --plain` 只返回与排序相关的内容
4. **选择结果索引**：若返回多条结果，用 `--index N` 取第 N 条
   - 例：`cheat.sh python/list --index 2 --plain`
5. **缓存常用查询**：对高频查询执行 `--cache` 参数
   - 例：`cheat.sh python/list+sort --cache`
6. **验证与版本检查**：首次使用或遇到问题时执行 `--selftest` 和 `--version`

### 输出规范

- 默认输出为纯文本，`--plain` 参数去除 ANSI 颜色码
- 每条结果包含：主题名称、适用场景、代码示例、注意事项（如有）
- 缓存文件保存在本地 `~/.cheat.sh/` 目录下

---

## 四、置信度门控

当出现以下情况时，输出中必须包含 `[需核实:字段]` 占位符，不得编造：

| 场景 | 处理方式 |
|------|----------|
| 查询主题不存在 | 输出 `[需核实:主题是否存在]` 并建议检查拼写 |
| 关键词组合无结果 | 输出 `[需核实:关键词组合]` 并建议拆分查询 |
| 索引超出范围 | 输出 `[需核实:索引范围]` 并提示当前结果总数 |
| 缓存文件损坏 | 输出 `[需核实:缓存完整性]` 并建议删除后重新缓存 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 网络连接失败 | "无法连接到 cheat.sh 服务，请检查网络" | 1. 检查网络连通性；2. 重试；3. 若已有缓存可离线使用 |
| E002 | 主题不存在 | "未找到主题，请检查拼写或尝试相近主题" | 1. 确认拼写；2. 用 `cheat.sh <语言>/list` 查看可用主题 |
| E003 | 索引越界 | "索引超出结果范围，当前共 N 条结果" | 1. 用 `--index 1` 查看第一条；2. 调整关键词缩小范围 |
| E004 | 缓存写入失败 | "缓存写入失败，请检查磁盘空间或权限" | 1. 检查 `~/.cheat.sh/` 目录权限；2. 清理磁盘空间 |
| E005 | 参数格式错误 | "参数格式不正确，请参考 `cheat.sh --help`" | 1. 查看帮助文档；2. 按示例重新构造命令 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正解（推荐做法） |
|--------|-------------------|------------------|
| 忽略 `--plain` 参数 | 直接使用 `cheat.sh python/list`，输出带颜色码导致脚本解析失败 | 在脚本或管道中使用 `--plain` 去除颜色码 |
| 关键词过度堆叠 | `cheat.sh python/list+sort+reverse+filter+map` 导致无结果 | 每次最多 2-3 个关键词，分步查询 |
| 不检查索引范围 | 直接 `--index 5` 但实际只有 3 条结果 | 先不带 `--index` 查看结果总数，再选取索引 |
| 缓存后不更新 | 长期使用旧缓存，内容过时 | 定期（如每月）重新执行 `--cache` 更新 |
| 忽略自检 | 遇到异常直接放弃 | 先执行 `--selftest` 确认工具本身正常 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 基础查询
cheat.sh python/list --plain

# 关键词组合
cheat.sh python/list+sort --plain

# 多结果索引
cheat.sh python/list --index 2 --plain

# 本地缓存
cheat.sh python/list --cache

# 自检
cheat.sh --selftest
```

### 新手路径（首次使用）

1. 执行 `cheat.sh --selftest` 确认工具可用
2. 用 `cheat.sh <语言>/list --plain` 浏览可用主题
3. 选择一个主题，添加 1 个关键词过滤
4. 对常用查询执行 `--cache` 建立本地缓存

### 进阶路径（熟练用户）

1. **批量查询脚本**：编写 shell 脚本循环查询多个主题

   ```bash
   #!/bin/bash
   topics=("python/list" "go/slice" "git/merge" "docker/compose")
   for t in "${topics[@]}"; do
     echo "=== $t ==="
     cheat.sh "$t" --plain
   done
   ```

2. **缓存管理**：定期更新缓存，保持离线数据新鲜

   ```bash
   # 每周日更新所有缓存
   0 0 * * 0 find ~/.cheat.sh -name "*.cache" -exec cheat.sh --refresh {} \;
   ```

3. **自定义别名**：为高频查询设置 shell 别名

   ```bash
   alias py-sort='cheat.sh python/list+sort --plain'
   alias git-merge='cheat.sh git/merge --plain'
   ```

4. **集成工作流**：将 cheat.sh 集成到 CI/CD 或开发工具链中

   ```yaml
   # .gitlab-ci.yml 示例
   check-code-snippets:
     script:
       - cheat.sh python/list+sort --plain > /tmp/sort-snippet.txt
       - grep -q "sorted()" /tmp/sort-snippet.txt
   ```

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因代码示例不适用、信息不准确或操作失误导致的任何损失。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应遵守所在地区法律法规，不得将本 Skill 用于任何非法用途。
4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。

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
