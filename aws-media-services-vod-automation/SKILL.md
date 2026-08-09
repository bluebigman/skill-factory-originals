---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: aws-media-services-vod-automation
name: aws-media-services-vod-automation
displayName: 视频点播 云端转码 管道编排
description: 自动化AWS媒体服务VOD工作流，实现上传转码分发全链路编排。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/aws-media-services-vod-automation
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: MediaFlow Studio
agent_created: true
trigger_words: ["aws-media-services-vod-automation", "VOD自动化", "视频点播工作流", "媒体转码管道", "CloudFormation媒体编排"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AWS Media Services VOD Automation 技能文档

## 一、能力边界速查卡

本技能面向需要快速搭建视频点播（VOD）自动化管道的开发者和架构师，提供基于 AWS 媒体服务族（MediaConvert、MediaPackage、S3、CloudFront 等）的编排方案与基础设施即代码（IaC）模板。

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 输入解析与结构化 | 将用户提供的媒体文件路径、S3 URI、HTTP 直播流 URL 解析为结构化任务描述 |
| C2 | 关键信息识别 | 从输入中提取分辨率、编码格式、码率、封装格式、目标终端类型等关键参数 |
| C3 | 管道模板生成 | 根据输入参数生成对应的 CloudFormation 模板片段或完整堆栈定义 |
| C4 | 输出规范校验 | 按约定 schema 校验生成的模板与参数文件，确保字段完整、类型正确 |
| C5 | 批量任务编排 | 支持多文件、多目标格式的批量转码任务规划，生成可执行的批处理清单 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行实际部署 | 本技能只生成模板与编排脚本，不调用 AWS API 进行真实资源创建 |
| L2 | 不处理 DRM 授权 | 不涉及数字版权管理系统的密钥管理与许可证颁发逻辑 |
| L3 | 不优化转码参数 | 不针对特定编解码器（如 H.264/H.265/AV1）提供画质调优建议 |
| L4 | 不监控运行状态 | 不包含 CloudWatch 告警规则或管道健康检查的配置生成 |
| L5 | 不处理计费分析 | 不提供成本估算或费用优化方案 |

### 1.3 适用对象

- 需要快速原型验证的媒体解决方案架构师
- 负责视频平台基础设施的 DevOps 工程师
- 需要标准化 VOD 管道的技术团队负责人

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一触发词即可激活本技能：

- `aws-media-services-vod-automation`（主触发词）
- `VOD自动化`（中文同义）
- `视频点播工作流`（场景扩展）
- `媒体转码管道`（功能扩展）
- `CloudFormation媒体编排`（技术栈扩展）

### 2.2 场景映射表

| 用户实际诉求（大白话） | 技能响应行为 |
|----------------------|-------------|
| "我想把上传到 S3 的视频自动转成多码率" | 生成 MediaConvert 任务编排模板 + S3 事件触发配置 |
| "帮我写一套点播管道的 CloudFormation" | 输出完整堆栈模板，含 MediaPackage、CloudFront 资源配置 |
| "我有几个视频 URL 要批量处理" | 解析 URL 列表，生成批量转码任务清单 |
| "视频要适配手机和电视" | 识别终端类型，生成多分辨率输出预设组合 |
| "给我一个最小可用的管道配置" | 输出精简版模板，仅含核心转码与分发链路 |

---

## 三、标准执行流程

### 3.1 前置条件

执行本技能前，用户需确认以下信息：

| 前置项 | 必需 | 示例值 |
|--------|------|--------|
| 输入媒体位置 | 是 | `s3://my-bucket/input/video.mp4` 或 `https://example.com/live/stream.m3u8` |
| 目标输出格式 | 是 | `HLS` / `DASH` / `CMAF` |
| 目标终端类型 | 否（默认多终端） | `mobile` / `tv` / `web` |
| 分辨率范围 | 否（默认 480p-1080p） | `720p` / `1080p` |
| 部署区域 | 否（默认 us-east-1） | `ap-northeast-1` |

### 3.2 执行步骤

**步骤 1：收集与确认输入**

接收用户提供的媒体位置、格式要求、终端类型。若信息不完整，按置信度门控规则处理（见第四节）。

**步骤 2：解析关键参数**

从输入中提取以下参数表：

| 参数名 | 类型 | 提取规则 |
|--------|------|----------|
| `input_uri` | string | 识别 `s3://` 或 `https://` 前缀 |
| `output_format` | string | 匹配 `HLS`/`DASH`/`CMAF` 关键字 |
| `resolution` | string | 匹配 `\d+p` 模式 |
| `codec` | string | 匹配 `H.264`/`H.265`/`AV1` |
| `target_devices` | array | 匹配 `mobile`/`tv`/`web` 关键字 |

**步骤 3：生成管道模板**

根据解析结果，生成 CloudFormation 模板。模板结构如下：

```yaml
# 模板骨架示例（节选）
Resources:
  InputBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub "${AWS::StackName}-input"
  
  MediaConvertRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: mediaconvert.amazonaws.com
            Action: sts:AssumeRole
  
  ConvertJob:
    Type: Custom::MediaConvertJob
    Properties:
      ServiceToken: !GetAtt MediaConvertFunction.Arn
      InputUri: !Ref InputUri
      OutputFormat: !Ref OutputFormat
      Resolution: !Ref Resolution
```

**步骤 4：校验输出完整性**

检查生成的模板是否包含：

- [ ] 至少一个 S3 存储桶资源
- [ ] IAM 角色与策略（含 MediaConvert 服务信任策略）
- [ ] 转码任务定义（含输入/输出路径映射）
- [ ] 分发资源（MediaPackage 或 CloudFront，按需）
- [ ] 参数默认值（区域、码率、分辨率）

**步骤 5：输出结果**

按以下格式输出：

```json
{
  "template": "<CloudFormation YAML 内容>",
  "parameters": {
    "input_uri": "s3://bucket/input.mp4",
    "output_format": "HLS",
    "resolution": "1080p"
  },
  "confidence": {
    "input_uri": 1.0,
    "output_format": 0.95,
    "resolution": 0.8
  }
}
```

### 3.3 输出规范

| 输出项 | 格式要求 | 说明 |
|--------|----------|------|
| 模板文件 | YAML 或 JSON | 符合 CloudFormation 规范 |
| 参数文件 | JSON | 键值对形式，键名与模板 Parameters 一致 |
| 任务清单 | Markdown 表格 | 含任务编号、输入、输出、状态 |
| 置信度标注 | 0.0-1.0 浮点数 | 每个关键字段独立标注 |

---

## 四、置信度门控机制

当输入信息不足以生成完整模板时，遵循以下规则：

### 4.1 信息缺失处理

| 缺失字段 | 处理方式 | 输出占位符 |
|----------|----------|------------|
| 输出格式 | 默认 `HLS`，置信度 0.6 | `[需核实:output_format]` |
| 分辨率 | 默认 `1080p`，置信度 0.5 | `[需核实:resolution]` |
| 输入位置 | 无法默认，必须询问 | `[需核实:input_uri]` |
| 部署区域 | 默认 `us-east-1`，置信度 0.7 | `[需核实:region]` |

### 4.2 禁止行为

- 不编造不存在的 S3 路径或 URL
- 不假设用户未提及的编解码器
- 不生成包含未确认参数的 IAM 策略

### 4.3 二次确认流程

当出现以下情况时，主动向用户确认：

1. 输入 URI 格式无法识别（非 `s3://` 或 `https://`）
2. 输出格式与终端类型明显矛盾（如 `tv` 终端配 `480p` 分辨率）
3. 批量任务超过 10 个文件且未指定优先级

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 输入 URI 格式无效 | "无法识别输入位置，请提供 s3:// 或 https:// 开头的有效地址" | 检查 URI 前缀，重新输入 |
| `E1002` | 输出格式不支持 | "当前仅支持 HLS、DASH、CMAF 三种封装格式" | 从支持列表中选择 |
| `E1003` | 分辨率参数异常 | "分辨率格式应为数字+p，如 720p、1080p" | 修正分辨率写法 |
| `E1004` | 模板生成失败 | "模板生成过程中出现内部错误，请检查输入参数后重试" | 核对参数表，重新执行 |
| `E1005` | 批量任务冲突 | "检测到重复的输出路径，请确认是否覆盖或跳过" | 指定冲突处理策略 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑位

| 坑位描述 | 反模式（错误做法） | 正模式（正确做法） |
|----------|-------------------|-------------------|
| 忽略 IAM 权限 | 直接生成不含角色的模板 | 始终包含最小权限 IAM 角色定义 |
| 硬编码区域 | 模板中写死 `us-east-1` | 使用 `AWS::Region` 伪参数 |
| 忽略事件触发 | 只生成转码任务，无 S3 事件通知 | 添加 `S3:BucketNotification` 配置 |
| 输出路径冲突 | 多任务写同一输出前缀 | 使用 `${JobId}` 或时间戳隔离路径 |
| 缺少清理策略 | 不设置生命周期规则 | 添加 `LifecycleConfiguration` 自动清理 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 复制粘贴完整堆栈模板 | 无法适配不同输入场景 | 使用参数化模板 + 条件渲染 |
| 手动拼接 JSON 参数 | 易出错且难以维护 | 使用 YAML 模板 + 参数文件分离 |
| 忽略 MediaConvert 端点 | 不同区域端点不同 | 使用 `AWS::MediaConvert::Endpoint` 查询 |
| 将所有文件转成相同规格 | 浪费存储与转码成本 | 按终端类型差异化输出 |

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
输入：s3://bucket/input.mp4 → HLS → 1080p
输出：CloudFormation YAML + 参数 JSON + 置信度标注
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解适用范围
2. 准备一个简单的 S3 视频路径
3. 执行标准流程步骤 1-3
4. 检查输出模板的 Resources 部分
5. 使用 AWS CLI 手动部署验证

### 7.3 进阶路径（深度使用）

1. 熟悉「错误码体系」快速定位问题
2. 阅读「FAQ 与反模式对照」避免常见错误
3. 自定义模板中的 MediaConvert 作业设置
4. 集成 Lambda 函数实现自定义后处理
5. 结合 CI/CD 管道实现自动化部署

---

## 八、用户协议

使用本技能生成的任何模板、脚本或配置，使用者自行承担全部责任。本技能提供的示例代码和模板仅作为参考，不构成任何形式的保证或担保。使用者应自行验证生成的资源符合其业务需求和安全标准。

禁止对本技能生成的代码或文档进行反向工程、反编译或试图提取底层算法。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本技能采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2026 MediaFlow Studio

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

---

*文档版本：1.0.0 | 最后更新：2026-08-09*
