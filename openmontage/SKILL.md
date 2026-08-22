---
slug: openmontage
name: openmontage
displayName: 视频生产 管线编排 自动化制作
description: 编排多管线与工具链，自动化完成视频制作全流程。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流媒体工坊
agent_created: true
trigger_words: ["openmontage", "视频生产", "视频编排", "自动化管线", "视频制作", "批量渲染", "剪辑流水线"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# openmontage — 开源智能视频生产系统

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 多管线编排 | 将多个处理管线按依赖关系串联，支持并行/串行混合 | 先转码 → 再合成字幕 → 最后封装输出 |
| 工具链集成 | 调用外部命令行工具（ffmpeg、ImageMagick 等） | 调用 ffmpeg 做滤镜处理 |
| 批量生产 | 对同一目录下多个素材执行相同流程 | 批量给 100 个片段加片头片尾 |
| 参数化配置 | 通过 YAML/JSON 文件定义流程参数 | 不同分辨率、码率的输出配置 |
| 试运行模式 | 单样本验证流程正确性后再全量执行 | 先跑 1 个文件确认输出格式 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非实时渲染 | 不提供实时预览或流式输出，所有处理均为离线批处理 |
| 无 GUI 编辑 | 不包含时间线拖拽、关键帧动画等交互式编辑能力 |
| 不生成创意内容 | 不负责脚本撰写、分镜设计、配音合成等创意环节 |
| 不处理版权素材 | 不校验输入素材的版权合法性，使用者自行负责 |
| 不支持分布式计算 | 单机多进程并行，不跨节点调度 |

### 1.3 适用对象

- 视频制作团队：需要批量处理标准化视频素材
- 自动化工程师：希望将视频处理嵌入 CI/CD 流水线
- 内容运营人员：需要定期生成固定格式的短视频/宣传片

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 说明 |
|--------|------|
| openmontage | 主命令，直接调用 |
| 视频生产 / 视频制作 | 描述用途时触发 |
| 视频编排 / 自动化管线 | 强调流程编排时触发 |
| 批量渲染 / 剪辑流水线 | 补充场景词，用于批量处理场景 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行 |
|------------------|----------|
| "帮我把这几个视频统一加上片头" | 定义单管线：片头合成 → 输出到指定目录 |
| "每天自动生成 50 个产品宣传视频" | 配置批量任务 + 定时触发 |
| "先跑一个看看效果" | 使用 `--selftest` 或单样本试运行 |
| "这个流程能复用吗？" | 导出管线配置为 YAML 文件，下次直接加载 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 检查项 | 验证方式 |
|------|--------|----------|
| 环境就绪 | Python ≥ 3.9，ffmpeg ≥ 4.4 | `openmontage --version` |
| 输入素材 | 所有待处理文件位于同一目录 | `ls <input_dir>` |
| 命名规范 | 文件名前缀一致，扩展名统一 | 如 `product_001.mp4`、`product_002.mp4` |
| 输出目录 | 目标目录存在且有写权限 | `mkdir -p <output_dir>` |

### 3.2 执行步骤

1. **准备输入目录**
   ```bash
   mkdir -p ./input ./output ./backup
   cp /path/to/source/*.mp4 ./input/
   ```

2. **编写管线配置**（`pipeline.yaml` 示例）
   ```yaml
   name: product_intro
   steps:
     - tool: ffmpeg
       args: ["-i", "{input}", "-vf", "scale=1280:720", "{output}_720p.mp4"]
     - tool: ffmpeg
       args: ["-i", "{output}_720p.mp4", "-i", "intro.mp4", "-filter_complex", "concat", "{output}_final.mp4"]
   ```

3. **试运行单样本**
   ```bash
   openmontage --config pipeline.yaml --input ./input/product_001.mp4 --output ./output/ --selftest
   ```
   核对输出文件是否存在、字段是否完整。

4. **批量执行**
   ```bash
   openmontage --config pipeline.yaml --input ./input/ --output ./output/
   ```
   执行前自动备份原始文件至 `./backup/`。

5. **校验结果**
   ```bash
   openmontage --verify --output ./output/ --expect "*.mp4"
   ```
   抽查 3-5 个输出文件，核对分辨率、时长、文件大小。

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 视频文件 | `.mp4` / `.mov` | 按配置生成，命名规则 `{原文件名}_{步骤标识}.{ext}` |
| 日志 | `openmontage_YYYYMMDD_HHMMSS.log` | 记录每步执行时间、退出码、输出路径 |
| 校验报告 | `verify_report.json` | 包含文件列表、大小、时长、校验状态 |

---

## 四、置信度门控

当遇到以下情况时，**不猜测、不编造**，输出 `[需核实:字段]` 占位符：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 输入文件缺失 | `[需核实:输入文件路径]` | 停止执行，提示用户检查路径 |
| 参数值超出范围 | `[需核实:分辨率参数]` | 提示用户确认分辨率是否合法 |
| 工具版本不兼容 | `[需核实:ffmpeg版本]` | 提示用户升级或降级工具 |
| 输出格式不确定 | `[需核实:输出编码格式]` | 提示用户明确编码规格 |

**规则**：任何不确定的信息必须显式标注，不得用默认值替代。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入目录为空 | "未找到任何可处理的文件，请检查输入路径。" | 确认文件已复制到输入目录 |
| `E002` | 配置文件解析失败 | "管线配置 YAML 格式错误，请检查缩进和引号。" | 用 `yaml lint` 校验配置 |
| `E003` | 外部工具调用失败 | "ffmpeg 执行返回非零退出码，请查看日志详情。" | 检查 ffmpeg 参数是否正确 |
| `E004` | 输出目录不可写 | "无法写入输出目录，请检查权限。" | `chmod +w <output_dir>` |
| `E005` | 命名冲突 | "输出文件已存在，为避免覆盖已跳过。" | 清理输出目录或启用 `--force` |
| `E006` | 资源不足 | "内存/磁盘空间不足，任务已暂停。" | 释放磁盘空间或增加内存 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 直接全量执行 | 跳过试运行，直接跑全部数据 | 先单样本验证，再批量执行 |
| 覆盖原始文件 | 输出路径与输入路径相同 | 输出到独立目录，保留备份 |
| 忽略日志 | 出错后不查看日志直接重试 | 先查 `openmontage_*.log` 定位错误码 |
| 参数硬编码 | 在命令行写死参数，不可复用 | 使用 YAML 配置，参数化定义 |
| 不校验结果 | 执行完不检查输出文件 | 用 `--verify` 抽查输出质量 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
openmontage --config pipeline.yaml --input ./input/ --output ./output/ --selftest
openmontage --config pipeline.yaml --input ./input/ --output ./output/
openmontage --verify --output ./output/ --expect "*.mp4"
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」确认适用场景
2. 按「标准流程」步骤 1-3 完成单样本验证
3. 确认输出符合预期后，再执行批量任务
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（深度使用）

1. 学习 YAML 配置中的多管线编排语法
2. 自定义外部工具链（非 ffmpeg 工具）
3. 编写校验脚本，集成到 CI/CD 流程
4. 使用 `--dry-run` 模式预演全流程

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用 openmontage Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于素材版权、输出内容合规性、操作失误导致的损失。
2. **禁止反向工程**：不得对本 Skill 的配置模板、管线逻辑进行反向工程、反编译或提取核心算法用于商业竞争。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
4. **合规使用**：使用者须确保输入素材和输出内容不违反任何法律法规及第三方权益。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 流媒体工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*
