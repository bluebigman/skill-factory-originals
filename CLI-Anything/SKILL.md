---
slug: CLI-Anything
name: 自然语言转命令工具
displayName: 终端指令 中文转译 命令行速查
description: 将中文操作意图精准翻译为可执行命令行，提升终端效率。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨言
agent_created: true
trigger_words: ["自然语言转命令", "CLI生成", "命令翻译", "终端指令转换", "命令行助手", "中文转shell", "命令查询"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 自然语言转命令工具（CLI-Anything）

## 一、能力边界速查卡

### 1.1 能做什么

| 场景类别 | 具体说明 | 示例输入 → 输出 |
|---------|---------|----------------|
| 文件操作 | 创建、复制、移动、删除、重命名、查找 | "把当前目录所有 .log 文件打包成 tar.gz" → `tar -czf logs.tar.gz *.log` |
| 目录管理 | 切换、列出、统计大小、递归遍历 | "按修改时间倒序显示当前目录文件" → `ls -lt` |
| 进程管理 | 查看、终止、后台运行、资源占用 | "杀掉所有 python 进程" → `pkill -f python` |
| 系统服务 | 启动、停止、重启、查看状态 | "重启 nginx 服务" → `sudo systemctl restart nginx` |
| 网络操作 | 连通性测试、端口监听、下载文件 | "测试 192.168.1.1 的 80 端口是否开放" → `nc -zv 192.168.1.1 80` |
| 文本处理 | 提取、替换、排序、去重、统计 | "统计 access.log 中每个 IP 的出现次数" → `awk '{print $1}' access.log \| sort \| uniq -c` |
| 磁盘管理 | 查看占用、挂载、格式化 | "查看根分区剩余空间" → `df -h /` |
| 容器操作 | 查看、启动、停止、日志 | "查看所有运行中的容器" → `docker ps` |
| 权限管理 | 修改权限、属主、特殊位 | "给 script.sh 添加执行权限" → `chmod +x script.sh` |
| 包管理 | 安装、卸载、更新、搜索 | "用 apt 安装 htop" → `sudo apt install htop` |

### 1.2 不能做什么

| 限制类别 | 说明 | 替代建议 |
|---------|------|---------|
| 图形界面操作 | 无法生成点击、拖拽、窗口管理命令 | 建议使用 `xdotool` 或 GUI 自动化工具 |
| 硬件控制 | 无法直接控制物理设备（如风扇转速） | 建议查阅硬件厂商提供的 CLI 工具 |
| 交互式程序 | 无法处理需要 TUI 交互的复杂程序 | 建议使用 `expect` 或 `script` 命令模拟 |
| 非命令行范畴 | 无法完成需要图形渲染、音频播放等操作 | 建议使用对应 GUI 应用 |
| 跨平台兼容 | 无法保证命令在所有 OS 上一致 | 建议明确操作系统类型后重试 |

### 1.3 适用对象

- **目标用户**：日常使用终端的开发者、运维人员、数据分析师
- **前置条件**：用户具备基础命令行认知（知道什么是参数、路径）
- **不适用**：完全零基础用户（需先学习基本概念）


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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
