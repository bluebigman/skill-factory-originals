---
slug: hec-commander
name: hec-commander
displayName: 水文建模 HEC 脚本自动化
description: 面向HEC系列软件的脚本生成与自动化操作辅助指南。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 河川工坊
agent_created: true
trigger_words: ["hec-commander", "HEC-RAS", "HEC-HMS", "水文建模", "脚本自动化", "水力计算", "水文模拟"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# HEC Commander — 水文建模脚本自动化辅助指南

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 脚本骨架生成 | 为 HEC-RAS / HEC-HMS 生成可编辑的自动化脚本框架 |
| 2 | 批量任务编排 | 设计多文件批量处理的执行顺序与参数映射 |
| 3 | 输入文件预检 | 检查文件命名、目录结构、格式一致性 |
| 4 | 输出校验方案 | 制定抽查规则与关键字段比对清单 |
| 5 | 错误排查指引 | 提供常见报错的分析路径与修正建议 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不替代专业软件 | 不执行实际的水文/水力计算，仅提供操作辅助 |
| 2 | 不生成完整业务代码 | 产出脚本框架，业务逻辑需使用者自行完善 |
| 3 | 不保证计算结果 | 不验证模型精度，不承担数据准确性责任 |
| 4 | 不处理非 HEC 系软件 | 仅覆盖 HEC-RAS 与 HEC-HMS 相关操作场景 |

### 1.3 适用对象

- 使用 HEC-RAS 进行河道水力分析的工程师
- 使用 HEC-HMS 进行流域水文模拟的技术人员
- 需要批量处理模型文件的研究人员
- 希望提升建模流程自动化水平的团队

---

## 二、触发方式

### 2.1 触发词

- 核心触发词：`hec-commander`、`HEC-RAS`、`HEC-HMS`、`水文建模`、`脚本自动化`
- 补充触发词：`水力计算`、`水文模拟`、`批量建模`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应方式 |
|------------------|----------|-------------------|
| "我有一堆 HEC-RAS 文件要跑" | 批量执行模型 | 提供批量处理脚本框架与流程指引 |
| "HEC-HMS 老报错，不知道哪错了" | 错误排查 | 给出错误码对照表与修正步骤 |
| "想写个脚本自动跑模型" | 脚本生成 | 输出脚本骨架与参数配置说明 |
| "跑完的结果怎么确认对不对" | 结果校验 | 提供抽查方案与字段比对清单 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 软件环境 | 已安装 HEC-RAS 或 HEC-HMS（版本不限） |
| 文件准备 | 待处理文件已放入同一工作目录 |
| 命名规范 | 文件名遵循统一规则（如 `project_01.ras`、`basin_02.hms`） |
| 备份 | 原始文件已做备份（建议复制到 `backup/` 子目录） |

### 3.2 执行步骤

**步骤 1：环境确认**

- 确认工作目录路径无中文与空格（避免脚本解析异常）
- 确认 HEC 软件可正常启动，版本号与脚本预期一致

**步骤 2：输入文件预检**

- 列出目录下所有待处理文件，核对命名规范
- 检查文件扩展名是否正确（`.ras` / `.hms` / `.prj` 等）
- 确认无重复文件或空文件

**步骤 3：单样本试运行**

- 选取 1 个代表性文件执行脚本
- 核对输出字段是否完整、格式是否符合预期
- 记录试运行耗时，评估批量执行时间

**步骤 4：批量执行**

- 确认试运行无误后，对全量文件执行脚本
- 执行过程中保留原始文件备份（不可覆盖）
- 建议分批执行（每批 10-20 个文件），便于中途检查

**步骤 5：结果校验**

- 按 10%-20% 比例随机抽查输出文件
- 核对关键字段（如流量、水位、峰值时间等）与源数据一致性
- 将校验结果记录到 `validation_log.csv`

### 3.3 输出规范

| 输出项 | 格式要求 | 示例 |
|--------|----------|------|
| 脚本文件 | `.py` 或 `.bat`，UTF-8 编码 | `hec_batch_runner.py` |
| 执行日志 | `.log`，含时间戳与每步状态 | `run_20250101_1430.log` |
| 校验记录 | `.csv`，含文件名、字段名、源值、输出值、状态 | `validation_log.csv` |
| 结果汇总 | `.md` 或 `.txt`，含执行摘要与异常清单 | `summary_report.md` |

---

## 四、置信度门控

### 4.1 信息不足时的处理规则

当脚本执行过程中遇到以下情况，**不得编造数据**，必须输出占位符：

| 场景 | 占位符 | 说明 |
|------|--------|------|
| 输入文件缺失 | `[需核实:输入文件路径]` | 需用户确认文件位置 |
| 参数值不确定 | `[需核实:参数名称]` | 需用户提供具体数值 |
| 输出字段不匹配 | `[需核实:字段映射]` | 需用户核对字段对应关系 |
| 版本兼容性未知 | `[需核实:软件版本]` | 需用户确认 HEC 版本 |

### 4.2 占位符使用示例

```
# 执行日志片段
[2025-01-01 14:35:02] 处理文件: project_01.ras
[2025-01-01 14:35:03] 警告: 输出字段 'peak_flow' 未找到
[2025-01-01 14:35:03] 提示: [需核实:字段映射] 请确认源数据中的峰值流量字段名称
```

---

## 五、错误码体系

### 5.1 常见错误对照表

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `ERR_001` | 文件未找到 | "未找到指定文件，请检查路径" | 1. 确认文件路径正确<br>2. 检查文件名大小写<br>3. 确认文件未被移动 |
| `ERR_002` | 文件格式不支持 | "文件扩展名不在支持范围内" | 1. 确认文件为 `.ras` / `.hms` 格式<br>2. 检查文件是否损坏 |
| `ERR_003` | 参数缺失 | "缺少必要参数，无法继续执行" | 1. 查看参数清单<br>2. 补充缺失参数<br>3. 重新执行 |
| `ERR_004` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 1. 确认目录存在<br>2. 检查写入权限<br>3. 更换输出路径 |
| `ERR_005` | 脚本语法错误 | "脚本存在语法错误，请检查第 X 行" | 1. 定位报错行<br>2. 核对括号/引号匹配<br>3. 参考示例修正 |
| `ERR_006` | 软件未启动 | "未检测到 HEC 软件进程" | 1. 手动启动 HEC 软件<br>2. 确认软件安装路径<br>3. 检查环境变量 |

### 5.2 错误处理流程

```
遇到错误 → 记录错误码 → 查看对照表 → 按修正步骤处理 → 重新执行
         ↓
   错误码不在表中 → 记录完整报错信息 → 查阅官方文档 → 或寻求社区支持
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 序号 | 常见坑 | 反模式（错误做法） | 正确做法 |
|------|--------|-------------------|----------|
| 1 | 文件命名混乱 | 直接批量执行，不做预检 | 先统一命名规范，再执行批量任务 |
| 2 | 覆盖原始文件 | 脚本直接写入原文件 | 保留备份，输出到独立目录 |
| 3 | 忽略试运行 | 跳过单样本测试直接全量跑 | 务必先试运行 1 个文件 |
| 4 | 不校验结果 | 跑完不检查直接使用 | 按比例抽查，核对关键字段 |
| 5 | 参数硬编码 | 在脚本中写死路径和参数 | 使用配置文件或命令行参数传入 |

### 6.2 反模式示例

**反模式：**
```python
# 错误：硬编码路径，无法复用
input_path = "C:/Users/xxx/Desktop/project_01.ras"
output_path = "C:/Users/xxx/Desktop/result_01.txt"
```

**正确做法：**
```python
# 正确：使用参数化配置
import sys
input_path = sys.argv[1]  # 从命令行获取
output_path = sys.argv[2]  # 从命令行获取
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

| 项目 | 内容 |
|------|------|
| 核心流程 | 预检 → 试运行 → 批量执行 → 校验 |
| 关键原则 | 先备份、先试跑、后批量 |
| 必查字段 | 文件名、扩展名、输出路径 |
| 常用命令 | `python hec_batch_runner.py --input ./data --output ./result` |

### 7.2 分层次阅读路径

**新手路径（首次使用）：**

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」逐步操作
3. 遇到问题查「错误码体系」

**进阶路径（熟练用户）：**

1. 参考「输出规范」自定义输出格式
2. 结合「置信度门控」设计容错机制
3. 扩展脚本框架，集成到现有工作流

**专家路径（深度定制）：**

1. 修改脚本骨架，增加并行处理能力
2. 自定义校验规则，对接业务系统
3. 建立错误知识库，持续优化提示话术

---

## 八、脚本框架参考

### 8.1 批量处理脚本骨架（Python）

```python
#!/usr/bin/env python3
"""
HEC Commander - 批量处理脚本框架
用法: python hec_batch_runner.py --input <dir> --output <dir>
"""

import os
import sys
import argparse
import logging
from datetime import datetime

def setup_logging(output_dir):
    """初始化日志配置"""
    log_file = os.path.join(output_dir, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_file

def precheck_files(input_dir):
    """预检输入文件"""
    files = [f for f in os.listdir(input_dir) if f.endswith(('.ras', '.hms'))]
    if not files:
        logging.error("ERR_001: 未找到支持的文件")
        return []
    logging.info(f"发现 {len(files)} 个待处理文件")
    return files

def process_single_file(filepath, output_dir):
    """处理单个文件（需根据实际需求实现）"""
    # TODO: 在此实现具体的 HEC 脚本调用逻辑
    logging.info(f"处理文件: {os.path.basename(filepath)}")
    return True

def main():
    parser = argparse.ArgumentParser(description='HEC Commander 批量处理工具')
    parser.add_argument('--input', required=True, help='输入目录')
    parser.add_argument('--output', required=True, help='输出目录')
    parser.add_argument('--test', action='store_true', help='试运行模式（仅处理第一个文件）')
    args = parser.parse_args()

    # 检查输出目录
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        logging.info(f"创建输出目录: {args.output}")

    # 初始化日志
    setup_logging(args.output)

    # 预检文件
    files = precheck_files(args.input)
    if not files:
        sys.exit(1)

    # 试运行或批量执行
    if args.test:
        files = files[:1]
        logging.info("试运行模式：仅处理第一个文件")

    # 执行处理
    success_count = 0
    for filename in files:
        filepath = os.path.join(args.input, filename)
        if process_single_file(filepath, args.output):
            success_count += 1

    # 输出汇总
    logging.info(f"处理完成: 成功 {success_count}/{len(files)}")
    logging.info(f"日志文件: {os.path.join(args.output, 'run_*.log')}")

if __name__ == '__main__':
    main()
```

### 8.2 参数配置示例（config.json）

```json
{
  "input_dir": "./data",
  "output_dir": "./result",
  "file_types": [".ras", ".hms"],
  "backup": true,
  "validation_ratio": 0.15,
  "key_fields": ["peak_flow", "water_level", "peak_time"]
}
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因脚本执行、数据处理、结果解读等环节造成的直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 文档及其生成内容进行反向工程、反编译、破解或任何形式的未授权修改。

3. **合规使用**：使用者应确保使用场景符合当地法律法规及行业规范，不得将本 Skill 用于任何非法用途。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及非侵权保证。

5. **更新与终止**：本 Skill 可能随时更新或终止，恕不另行通知。使用者应自行关注版本变化。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 河川工坊

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
