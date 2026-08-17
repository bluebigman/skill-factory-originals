---
slug: ai-website-cloner-template
name: ai-website-cloner-template
displayName: 网页结构还原 模板生成 页面解析
description: 输入网址或HTML文件，自动解析页面结构并生成可复用的结构化模板。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["网站克隆","页面抓取","结构还原","网页转模板","站点复制","页面结构解析","HTML模板提取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 网页结构还原与模板生成 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 |
|--------|------|----------|
| 在线页面解析 | 输入完整 URL（含协议头），抓取并解析页面结构 | `https://example.com/news` |
| 本地文件解析 | 读取本地 HTML 文件，提取结构骨架 | `/path/to/page.html` |
| 结构模板生成 | 输出 Markdown 格式的结构化模板，标注组件区域 | 自动生成 `template_<时间戳>.md` |
| 组件复用建议 | 识别可抽离的公共区块（如 header、footer、侧边栏） | 自动标注 `[可复用组件]` 标记 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行 JavaScript | 仅解析静态 HTML，动态渲染内容无法捕获 |
| 不处理登录态 | 需要认证的页面无法访问 |
| 不生成完整前端代码 | 输出为结构模板，非可直接运行的网页源码 |
| 不处理超大文件 | 超过 5MB 的 HTML 文件可能解析超时 |
| 不绕过访问限制 | 遵守 robots.txt 及目标站点服务条款 |

### 1.3 适用对象

- 前端开发者：快速理解陌生页面布局，提取可复用结构
- 技术文档撰写者：将现有页面结构转化为文档模板
- 自动化测试工程师：生成页面结构基线用于比对
- 产品经理：梳理竞品页面信息架构（仅限合法公开页面）

---

## 二、触发方式与场景映射

### 2.1 触发词

- 直接触发：`网站克隆`、`页面抓取`、`结构还原`、`网页转模板`、`站点复制`
- 补充触发：`页面结构解析`、`HTML模板提取`、`布局拆解`

### 2.2 大白话场景映射表

| 你说的话（口语化） | 实际执行动作 |
|-------------------|-------------|
| "帮我把这个网页变成模板" | 解析 URL 或 HTML 文件，生成结构化 Markdown 模板 |
| "看看这个页面是怎么布局的" | 提取页面骨架，标注各区块功能 |
| "我想复用这个网站的头部导航" | 识别 header 区域，标注为可复用组件 |
| "把这个页面的卡片列表结构整理出来" | 提取重复性列表结构，标注循环模式 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| Python 版本 | ≥ 3.8 | `python3 --version` |
| 网络连通性 | 可访问目标站点（解析 URL 时） | `curl -I <url>` |
| 文件读取权限 | 本地 HTML 文件可读 | `ls -l <file>` |
| 工作目录写入权限 | 当前目录可生成输出文件 | `touch .write_test && rm .write_test` |

### 3.2 执行步骤

1. **保存脚本**：将 `run.py` 下载到当前工作目录。
   ```bash
   curl -O https://example.com/run.py  # 实际路径以发布渠道为准
   ```

2. **（可选）添加执行权限**（Linux/macOS）：
   ```bash
   chmod +x run.py
   ```

3. **自检安装**：
   ```bash
   python3 run.py --selftest
   ```
   预期输出：`[OK] 环境检查通过`（或列出缺失依赖项）。

4. **执行解析**，三选一：
   ```bash
   # 方式一：解析在线 URL
   python3 run.py "https://example.com/news"

   # 方式二：解析本地 HTML 文件
   python3 run.py /path/to/page.html

   # 方式三：查看版本
   python3 run.py --version
   ```

5. **查看输出**：脚本会在当前目录生成 `template_<时间戳>.md` 文件。

### 3.3 输出规范

生成的模板文件遵循以下结构：

```markdown
# 页面结构模板

## 页面元信息
- 来源: <URL 或文件路径>
- 解析时间: <ISO 时间戳>
- 页面标题: <title 标签内容>

## 结构骨架
### 1. Header 区域
- 类型: 固定/滚动
- 包含元素: logo, 导航菜单, 搜索框
- [可复用组件] 建议抽离为独立 header 组件

### 2. 主内容区
- 布局类型: 单栏/双栏/三栏
- 内容块: 文章卡片（重复结构，可循环渲染）
- 卡片字段: 标题, 摘要, 缩略图, 发布时间

### 3. Sidebar 区域
- 类型: 左侧/右侧
- 包含 widget: 标签云, 热门文章, 广告位
- [动态加载位] 预留异步加载区域

### 4. Footer 区域
- 包含元素: 版权信息, 友情链接, 联系方式
- [可复用组件] 建议抽离为独立 footer 组件

## 组件复用建议
1. header 区域可抽为独立组件，适配多页面复用
2. 文章卡片结构可扩展为列表循环
3. 侧边栏 widget 区域预留了动态加载位
```

---

## 四、置信度门控

### 4.1 占位符规则

当解析过程中遇到以下情况，输出 `[需核实:字段]` 占位符，不进行猜测：

| 场景 | 占位符示例 |
|------|-----------|
| 元素属性缺失 | `[需核实:链接地址]` |
| 结构嵌套层级过深（>5层） | `[需核实:深层嵌套结构]` |
| 疑似动态加载内容 | `[需核实:动态内容来源]` |
| 编码异常导致乱码 | `[需核实:原始编码格式]` |

### 4.2 禁止行为

- 不推断缺失的 CSS 类名含义
- 不猜测未渲染的 JavaScript 数据
- 不虚构页面中不存在的元素

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | URL 格式错误 | `[错误] URL 需包含协议头（http:// 或 https://）` | 重新输入完整 URL |
| E002 | 网络不可达 | `[错误] 无法连接目标站点，请检查网络或 URL 有效性` | 1. 检查网络；2. 用 `curl -I` 验证可达性 |
| E003 | 文件不存在 | `[错误] 指定的 HTML 文件路径不存在` | 确认文件路径是否正确 |
| E004 | 文件过大 | `[错误] 文件超过 5MB 限制，请拆分后重试` | 拆分 HTML 文件或截取关键片段 |
| E005 | 解析超时 | `[错误] 解析超过 30 秒，页面结构可能过于复杂` | 尝试简化页面或分段解析 |
| E006 | 编码异常 | `[错误] 无法识别文件编码，请转换为 UTF-8` | 用文本编辑器转换编码格式 |
| E007 | 权限不足 | `[错误] 当前用户无读取权限` | 修改文件权限或更换用户 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确姿势

| 常见坑（反模式） | 问题说明 | 正确姿势 |
|-----------------|----------|----------|
| 输入不带协议头的 URL | `example.com` 会被误判为本地路径 | 始终使用 `https://example.com` 格式 |
| 解析后直接复制页面内容 | 可能涉及版权问题 | 仅提取结构骨架，不复制正文内容 |
| 忽略动态内容提示 | 误以为模板完整，实际缺少 JS 渲染部分 | 关注 `[需核实:动态内容来源]` 标记 |
| 在未授权站点上使用 | 违反 robots.txt 或服务条款 | 仅解析有权访问的页面 |
| 期望输出完整前端代码 | 本工具输出结构模板，非可运行源码 | 将模板作为开发参考，自行编写实现 |

### 6.2 反模式对照表

| 反模式描述 | 后果 | 替代方案 |
|-----------|------|----------|
| 用本工具绕过登录墙抓取内容 | 违反服务条款，可能承担法律责任 | 使用官方 API 或申请授权 |
| 将模板直接用于商业产品 | 可能侵犯原站设计版权 | 仅作学习参考，重新设计 UI |
| 解析超大单页应用（SPA） | 只能拿到空壳结构，无实际内容 | 结合浏览器开发者工具手动分析 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 保存 run.py 到工作目录
2. 运行：python3 run.py --selftest
3. 解析：python3 run.py "https://目标网址" 或 python3 run.py 本地文件.html
4. 查看生成的 template_<时间戳>.md 文件
```

### 7.2 新手路径（首次使用）

1. 阅读本 Skill 文档的「能力边界」和「标准执行流程」
2. 用 `--selftest` 确认环境就绪
3. 找一个简单的公开网页（如博客首页）进行首次解析
4. 查看输出模板，对照原页面理解结构标注含义
5. 遇到问题查阅「错误码体系」章节

### 7.3 进阶路径（熟练使用）

1. 深入理解「组件复用建议」部分，规划多页面模板体系
2. 结合输出模板中的 `[需核实]` 标记，手动补充动态内容结构
3. 将多个页面的模板合并，构建站点级结构文档
4. 根据「FAQ 反模式」规避常见陷阱，提升解析效率

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于：解析内容的合法性、目标网站的访问权限、输出模板的合规使用。
2. **禁止反向工程**：不得对本 Skill 的脚本进行反向工程、反编译、破解或试图提取源代码逻辑（除正常调用接口外）。
3. **合规使用**：请遵守目标网站的 `robots.txt` 及服务条款。本工具仅用于技术学习与合法开发场景。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 林墨研

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

**文档版本**: 1.0.0  
**最后更新**: 2024 年  
**适用 Skill 版本**: 1.0.0
