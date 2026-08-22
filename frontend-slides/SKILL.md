---
slug: frontend-slides
name: frontend-slides
displayName: 前端幻灯片 数据可视化 演示文稿
description: 将数据与内容转化为可交互的网页幻灯片，支持自定义样式与交互。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["frontend slides", "网页幻灯片", "前端演示", "slide deck", "HTML slides", "交互式演示", "数据展示"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 前端幻灯片（frontend-slides）技能文档

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据转幻灯片 | 将 CSV、JSON、Markdown 等数据文件转换为 HTML 幻灯片 | 销售数据 → 柱状图幻灯片 |
| 自定义样式 | 支持通过 CSS 变量、主题配置调整幻灯片外观 | 修改主色调、字体、背景 |
| 交互设计 | 支持点击、悬停、键盘导航等交互行为 | 点击切换图表维度 |
| 批量生成 | 对多份数据文件批量生成幻灯片组 | 10 份周报 → 10 组幻灯片 |
| 嵌入部署 | 输出纯 HTML 文件，可嵌入任意 Web 环境 | 内嵌到公司内网门户 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持动态数据源 | 幻灯片生成后为静态 HTML，不自动刷新数据 |
| 不包含演示遥控功能 | 需借助浏览器全屏或第三方工具实现遥控 |
| 不处理二进制大文件 | 超过 50MB 的数据文件建议预处理后再转换 |
| 不生成 PDF/PPT 格式 | 仅输出 HTML，如需其他格式需自行转换 |

### 适用对象

- 需要快速将数据转化为可视化演示的**数据分析师**
- 需要制作产品演示页面的**前端开发者**
- 需要定期制作汇报材料的**项目经理**
- 需要制作教学课件的**培训讲师**

---

## 二、触发方式

### 触发词

- 直接触发：`frontend slides`、`网页幻灯片`、`前端演示`、`slide deck`、`HTML slides`
- 补充触发：`交互式演示`、`数据展示`、`网页版PPT`

### 场景映射表

| 你说的话 | 实际需求 | 技能响应 |
|----------|----------|----------|
| "帮我把这份销售数据做成网页幻灯片" | 数据可视化演示 | 读取数据 → 生成图表幻灯片 |
| "我要做一个产品介绍的前端演示" | 产品展示页面 | 生成图文混排幻灯片 |
| "把这几份周报转成 HTML slides" | 批量文档转换 | 批量处理并输出幻灯片组 |
| "做一个带交互的 slide deck" | 交互式演示 | 添加点击/悬停交互效果 |

---

## 三、标准流程

### 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 数据文件格式 | CSV / JSON / Markdown | 文件扩展名确认 |
| 文件命名规范 | 统一前缀 + 序号，如 `data_01.csv` | 目录列表检查 |
| 环境要求 | Node.js ≥ 16 或纯浏览器环境 | `node -v` 命令 |
| 依赖安装 | 无需额外依赖（纯前端实现） | 直接运行 |

### 执行步骤

#### 步骤 1：准备输入

1. 将待处理的数据文件放入同一工作目录。
2. 确认文件命名符合规范（建议格式：`[前缀]_[序号].[扩展名]`）。
3. 检查文件编码为 UTF-8（避免中文乱码）。

```bash
# 示例：准备目录结构
mkdir slides_project
cd slides_project
cp /path/to/data/*.csv .
ls -la
```

#### 步骤 2：试运行（单样本验证）

1. 选取一个代表性文件作为测试样本。
2. 执行转换命令：

```bash
frontend slides --input data_01.csv --output preview.html
```

3. 打开 `preview.html`，核对以下字段：
   - 标题是否正确提取
   - 数据是否完整展示
   - 图表类型是否符合预期
   - 样式是否正常渲染

#### 步骤 3：批量执行

1. 确认试运行无误后，对全量数据执行：

```bash
frontend slides --input "data_*.csv" --output slides/
```

2. 保留原始文件备份（建议复制到 `backup/` 目录）。
3. 记录执行日志，便于排查问题。

#### 步骤 4：校验结果

1. 抽查 3-5 个输出文件，核对关键字段与源数据一致性。
2. 检查文件命名是否与输入对应。
3. 验证交互功能是否正常（点击、键盘导航等）。

### 输出规范

| 输出项 | 规范要求 |
|--------|----------|
| 文件格式 | 纯 HTML（内嵌 CSS/JS） |
| 文件命名 | `[前缀]_[序号].html` |
| 编码 | UTF-8 |
| 响应式 | 适配 1280px 以上屏幕 |
| 兼容性 | Chrome / Firefox / Safari 最新版 |

---

## 四、置信度门控

### 信息不足时的处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行编造：

| 场景 | 处理方式 |
|------|----------|
| 数据文件缺少标题字段 | 输出 `[需核实:标题]` 并提示用户补充 |
| 图表类型无法确定 | 输出 `[需核实:图表类型]` 并给出可选类型列表 |
| 样式参数缺失 | 使用默认样式，并在注释中标注 `[需核实:样式参数]` |
| 数据单位不明确 | 输出 `[需核实:单位]` 并提示用户确认 |

### 示例

```html
<!-- 数据缺失时的输出示例 -->
<div class="slide">
  <h1>[需核实:标题]</h1>
  <div class="chart" data-type="[需核实:图表类型]">
    <!-- 图表渲染区域 -->
  </div>
</div>
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | "未找到指定的输入文件，请检查路径" | 1. 确认文件路径正确；2. 检查文件权限 |
| E002 | 文件格式不支持 | "仅支持 CSV、JSON、Markdown 格式" | 1. 转换文件格式；2. 重新执行 |
| E003 | 数据解析失败 | "数据格式有误，无法解析" | 1. 检查数据完整性；2. 确认分隔符正确 |
| E004 | 输出目录不可写 | "无法写入输出目录，请检查权限" | 1. 修改目录权限；2. 更换输出路径 |
| E005 | 批量执行中断 | "批量处理在第 N 个文件处中断" | 1. 查看日志定位问题；2. 修复后从断点继续 |
| E006 | 样式编译错误 | "CSS 语法错误，请检查自定义样式" | 1. 定位错误行；2. 修正 CSS 语法 |

---

## 六、FAQ 反模式

### 常见坑与正确做法

| 常见错误（反模式） | 问题说明 | 正确做法 |
|-------------------|----------|----------|
| ❌ 直接批量处理所有文件 | 未验证单样本就全量执行，出错后返工成本高 | ✅ 先试运行单个样本，确认无误后再批量 |
| ❌ 覆盖原始数据文件 | 转换过程中修改了源数据，导致无法追溯 | ✅ 保留原始文件备份，输出到独立目录 |
| ❌ 忽略数据编码问题 | 中文乱码导致幻灯片内容不可读 | ✅ 统一使用 UTF-8 编码，转换前检查 |
| ❌ 过度自定义样式 | 样式过于复杂导致渲染性能下降 | ✅ 保持样式简洁，使用 CSS 变量统一管理 |
| ❌ 不校验输出结果 | 生成后不检查，直接交付使用 | ✅ 抽查关键字段，确保数据一致性 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. 放文件 → 2. 试运行 → 3. 批量执行 → 4. 校验结果
```

### 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围。
2. 按「标准流程」步骤 1-2 完成首次转换。
3. 遇到问题查阅「错误码体系」。
4. 参考「FAQ 反模式」避免常见错误。

#### 进阶路径（熟练用户）

1. 深入研究「自定义样式」配置（CSS 变量、主题）。
2. 探索「交互设计」高级用法（事件绑定、动画）。
3. 优化批量处理流程（并行处理、增量更新）。
4. 结合 CI/CD 实现自动化幻灯片生成。

---

## 八、自定义样式指南

### CSS 变量配置

```css
:root {
  --slide-width: 1280px;
  --slide-height: 720px;
  --primary-color: #2c3e50;
  --accent-color: #3498db;
  --font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
  --background: #ffffff;
  --text-color: #333333;
}
```

### 主题切换

```javascript
// 切换主题示例
const themes = {
  light: { background: '#fff', text: '#333' },
  dark: { background: '#1a1a2e', text: '#eee' }
};

function applyTheme(themeName) {
  const theme = themes[themeName];
  document.documentElement.style.setProperty('--background', theme.background);
  document.documentElement.style.setProperty('--text-color', theme.text);
}
```

---

## 九、交互设计规范

### 支持的交互类型

| 交互类型 | 触发方式 | 实现示例 |
|----------|----------|----------|
| 键盘导航 | ← → 方向键切换幻灯片 | `keydown` 事件监听 |
| 点击切换 | 点击按钮/区域切换 | `click` 事件绑定 |
| 悬停提示 | 鼠标悬停显示详情 | `mouseover` 事件 |
| 数据筛选 | 点击图例筛选数据 | 图表库内置功能 |

### 交互实现示例

```javascript
// 键盘导航示例
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight') {
    nextSlide();
  } else if (e.key === 'ArrowLeft') {
    prevSlide();
  }
});

// 点击切换示例
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.target;
    goToSlide(target);
  });
});
```

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因数据错误、样式问题、交互缺陷等导致的任何直接或间接损失。

2. **禁止反向工程**：未经授权，不得对本 Skill 的源代码、算法、逻辑进行反向工程、反编译或试图提取底层设计。

3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得用于制作违法、侵权或不当内容。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性等。

5. **修改与分发**：允许在保留本协议的前提下修改和再分发，但需注明原始出处。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

### MIT License

```
MIT License

Copyright (c) 2024 Lin Chen

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

---

## 十二、版本记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2024-01-15 | 初始版本发布 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*
