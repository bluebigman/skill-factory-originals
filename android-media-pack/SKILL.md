---
slug: android-media-pack
name: android-media-pack
displayName: 媒体播放 迁移集成 流媒体DRM
description: AndroidX Media3 媒体播放技能，覆盖迁移、UI、流媒体、DRM 与广告集成。
version: 1.0.0
license: MIT
source_project: original
source_url: ""
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: media-craft-studio
agent_created: true
trigger_words: ["android-media-pack", "Media3", "ExoPlayer迁移", "Compose播放器", "流媒体播放", "媒体播放器集成", "DRM配置", "视频广告接入"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Android Media3 媒体播放技能包

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合官方文档与项目实际环境进行验证。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C-01 | ExoPlayer 迁移 | 从旧版 ExoPlayer 2.x 迁移至 AndroidX Media3 1.x |
| C-02 | 播放器 UI 搭建 | 基于 View 系统的 `PlayerView` 与 Compose 的 `AndroidView` 封装 |
| C-03 | 流媒体播放 | HLS、DASH、SmoothStreaming 协议的媒体加载与播放 |
| C-04 | DRM 集成 | Widevine 等 DRM 方案的 License 请求与媒体加密播放 |
| C-05 | 广告集成 | IMA（Interactive Media Ads）SDK 与 Media3 的对接 |
| C-06 | 生命周期管理 | 播放器实例的创建、暂停、释放等生命周期操作 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L-01 | 编解码器扩展 | 不提供自定义编解码器实现，依赖设备硬件能力 |
| L-02 | 离线下载管理 | 不包含媒体离线缓存与下载任务调度 |
| L-03 | 服务端 License 签发 | 不涉及 DRM License 服务器的搭建与授权逻辑 |
| L-04 | 广告素材制作 | 不提供广告创意内容生成，仅负责播放侧集成 |
| L-05 | 跨平台支持 | 仅适用于 Android 平台，不涵盖 iOS/Web |

### 1.3 适用对象

- 已有 Android 项目且使用 Gradle 构建的开发者
- 需要从 ExoPlayer 2.x 升级到 Media3 的维护团队
- 正在开发视频/音频类应用并需要流媒体、DRM 或广告能力的工程师

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`android-media-pack`、`Media3`、`ExoPlayer迁移`、`Compose播放器`、`流媒体播放`
- 补充触发词：`媒体播放器集成`、`DRM配置`、`视频广告接入`

### 2.2 场景映射表

| 用户说（大白话） | 触发能力 | 对应章节 |
|------------------|----------|----------|
| "我想把项目里的 ExoPlayer 升级到新版本" | 迁移能力 | 第四章 4.1 |
| "用 Compose 怎么写视频播放界面？" | UI 搭建 | 第四章 4.2 |
| "要播放 m3u8 格式的视频流" | 流媒体播放 | 第四章 4.3 |
| "视频需要加密播放，有 License 服务器" | DRM 集成 | 第四章 4.4 |
| "想在视频里插广告" | 广告集成 | 第四章 4.5 |
| "播放器用完了怎么释放？" | 生命周期 | 第四章 4.6 |

---

## 三、标准流程

### 3.1 前置条件

| 条件编号 | 检查项 | 验证方式 | 通过标准 |
|----------|--------|----------|----------|
| P-01 | Android Gradle Plugin 版本 | 查看 `build.gradle` | ≥ 7.4 |
| P-02 | minSdkVersion | 查看 `build.gradle` | ≥ 21 |
| P-03 | 设备编解码器支持 | 使用 `MediaCodecList` 查询 | H.264/HEVC 可用 |
| P-04 | DRM 凭证（如涉及） | 确认 License URL 与认证信息 | 可访问且有效 |

### 3.2 执行步骤

#### 步骤 1：添加依赖

在 `app/build.gradle` 的 `dependencies` 块中添加：

```groovy
implementation "androidx.media3:media3-exoplayer:1.4.1"
implementation "androidx.media3:media3-ui:1.4.1"        // 如需 PlayerView
implementation "androidx.media3:media3-exoplayer-hls:1.4.1"  // 如需 HLS
implementation "androidx.media3:media3-exoplayer-dash:1.4.1" // 如需 DASH
```

#### 步骤 2：创建播放器实例

```kotlin
val exoPlayer = ExoPlayer.Builder(context).build()
```

#### 步骤 3：构建媒体项并播放

```kotlin
val mediaItem = MediaItem.fromUri("https://example.com/video.mp4")
exoPlayer.setMediaItem(mediaItem)
exoPlayer.prepare()
exoPlayer.playWhenReady = true
```

#### 步骤 4：绑定 UI

- **View 系统**：在布局中放置 `PlayerView`，然后调用 `playerView.player = exoPlayer`
- **Compose**：使用 `AndroidView` 工厂包装 `PlayerView`

#### 步骤 5：释放资源

在 `onDestroy` 或 `DisposableEffect` 的 `onDispose` 中调用：

```kotlin
exoPlayer.release()
```

### 3.3 输出规范

| 输出物 | 格式 | 说明 |
|--------|------|------|
| 依赖配置 | Gradle 代码片段 | 可直接粘贴至构建文件 |
| 播放器代码 | Kotlin 代码 | 包含创建、播放、释放全流程 |
| UI 绑定 | XML 或 Compose 代码 | 根据项目技术栈选择 |
| 配置清单 | Markdown 表格 | 列出所有需要修改的文件与位置 |

---

## 四、置信度门控

当以下信息缺失时，输出中必须使用 `[需核实:字段]` 占位，不得编造：

| 场景 | 占位示例 |
|------|----------|
| 用户未提供包名 | `[需核实:应用包名]` |
| 用户未指定媒体 URL | `[需核实:媒体资源地址]` |
| 用户未提供 DRM License URL | `[需核实:License服务器URL]` |
| 用户未说明设备型号 | `[需核实:目标设备型号]` |
| 用户未指定广告单元 ID | `[需核实:广告单元ID]` |

---

## 五、错误码体系

| 错误码 | 常见错误 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E-1001 | 依赖冲突（旧版 ExoPlayer 残留） | "检测到旧版 ExoPlayer 依赖，请先移除" | 1. 删除 `com.google.android.exoplayer:*` 依赖；2. 全局搜索替换 import 路径 |
| E-1002 | 播放器未释放导致内存泄漏 | "播放器实例未释放，存在泄漏风险" | 1. 在生命周期回调中调用 `release()`；2. 使用 `LeakCanary` 验证 |
| E-1003 | 流媒体协议不支持 | "当前协议不在支持范围内" | 1. 确认添加对应模块依赖（如 `media3-exoplayer-hls`）；2. 检查 URL 协议头 |
| E-1004 | DRM License 请求失败 | "License 获取失败，请检查凭证" | 1. 验证 License URL 可达性；2. 检查认证头信息；3. 确认设备支持 Widevine L1/L3 |
| E-1005 | 广告 SDK 初始化失败 | "IMA SDK 初始化异常" | 1. 确认网络权限；2. 检查广告单元 ID 格式；3. 查看 Logcat 详细堆栈 |

---

## 六、FAQ 反模式

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 反模式 1：全局单例播放器 | 将播放器设为静态实例，导致 Context 泄漏 | 每个页面或业务模块独立创建播放器，随页面销毁 |
| 反模式 2：忽略 `playWhenReady` 状态 | 直接调用 `play()` 而不处理音频焦点变化 | 使用 `playWhenReady` 配合音频焦点监听 |
| 反模式 3：UI 线程操作播放器 | 在子线程调用播放器方法 | 所有播放器操作必须在主线程执行 |
| 反模式 4：不处理网络切换 | 播放中断后无重试机制 | 监听 `ConnectivityManager`，断网时暂停，恢复时重试 |
| 反模式 5：硬编码媒体 URL | 将测试地址直接用于生产 | 使用 BuildConfig 区分环境，生产地址走配置中心 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 加依赖：media3-exoplayer:1.4.1
2. 建实例：ExoPlayer.Builder(context).build()
3. 设媒体：setMediaItem(MediaItem.fromUri(url))
4. 准备播：prepare() + playWhenReady = true
5. 绑 UI：playerView.player = exoPlayer
6. 释放：release()
```

### 7.2 新手路径（首次使用）

1. 阅读第三章「标准流程」的完整步骤
2. 从最简单的本地视频播放开始（步骤 2-3）
3. 逐步添加 UI 绑定（步骤 4）
4. 最后处理生命周期释放（步骤 5）
5. 遇到问题对照第五章「错误码体系」

### 7.3 进阶路径（深度集成）

1. 掌握流媒体协议选择（HLS vs DASH 的适用场景）
2. 理解 DRM 工作流程（License 请求 → 解密 → 渲染）
3. 学习广告插播策略（前贴片/中贴片/后贴片）
4. 优化播放体验（缓冲策略、码率自适应、音视频同步）
5. 结合 `media3-session` 实现后台播放与媒体通知

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的代码示例与配置建议仅供参考，使用者需根据实际项目情况自行验证与调整。
2. **禁止反向工程**：使用者不得对本 Skill 的提示词结构、生成逻辑进行反向工程、反编译或试图提取底层设计。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。
4. **合规使用**：使用者应确保其应用符合 Google Play 政策及相关法律法规，特别是涉及 DRM 与广告内容时。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 原创作者（自持版权）

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

*文档版本：1.0.0 | 最后更新：2025 年 | 适用 Media3 版本：1.4.1*
