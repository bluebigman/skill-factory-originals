---
slug: javascript-bits
name: javascript-bits
displayName: 前端开发 JS 实用片段速查
description: 精选 JavaScript 实用片段，覆盖新旧语法，助力日常开发。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeCraft Studio
agent_created: true
trigger_words: ["javascript bits", "js 片段", "javascript 代码片段", "js 工具函数", "javascript 实用代码", "js 常用方法", "前端工具函数"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# JavaScript Bits — 实用片段速查手册

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 语法速查 | 提供 ES5~ES2024 常用语法片段 | 数组操作、对象解构、可选链 |
| 工具函数 | 提供可直接复用的纯函数片段 | 防抖、节流、深拷贝、格式化 |
| 新旧对比 | 展示旧写法与新写法对照 | var→let/const、回调→Promise |
| 代码审查辅助 | 指出常见反模式及改进建议 | 隐式类型转换、全局污染 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供完整项目脚手架 | 仅提供片段，不生成项目结构 |
| 不替代官方文档 | 复杂 API 请查阅 MDN 或 ECMA 规范 |
| 不保证代码零缺陷 | 片段需结合具体运行环境验证 |
| 不处理框架特定逻辑 | React/Vue 等框架 API 不在覆盖范围 |

### 1.3 适用对象

- 前端开发工程师（初级~高级）
- 全栈开发者在编写前端逻辑时的参考
- 需要快速查阅 JS 语法或工具函数的场景

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 说明 |
|--------|------|
| `javascript bits` | 主触发词 |
| `js 片段` | 中文触发词 |
| `javascript 代码片段` | 完整描述 |
| `js 工具函数` | 功能导向触发 |
| `javascript 实用代码` | 同义触发 |
| `js 常用方法` | 补充触发词 |
| `前端工具函数` | 场景触发词 |

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|----------------|
| "给我一个防抖函数" | 需要防抖工具函数 | 输出防抖函数片段 + 使用说明 |
| "数组去重怎么写" | 需要数组去重方法 | 输出多种去重方案对比 |
| "Promise 和回调有什么区别" | 需要新旧写法对比 | 输出对照示例 |
| "这段代码有什么问题" | 需要代码审查建议 | 输出反模式分析 + 改进方案 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 运行环境 | Node.js ≥ 14 或现代浏览器（Chrome 90+） |
| 输入文件 | 待处理的 `.js` 或 `.mjs` 文件，编码为 UTF-8 |
| 命名规范 | 文件名为小写字母+连字符（如 `utils-helper.js`） |
| 备份要求 | 批量处理前必须保留原始文件副本 |

### 3.2 执行步骤

#### 步骤 1：准备输入

1. 将待处理文件放入当前工作目录
2. 确认文件名符合命名规范（小写+连字符）
3. 检查文件编码为 UTF-8（非 UTF-8 需先转换）

#### 步骤 2：试运行（单样本验证）

1. 选取 1 个代表性文件执行
2. 核对输出字段是否完整（函数名、参数、返回值）
3. 验证输出格式是否符合预期（代码块 + 说明）

**试运行检查表：**

| 检查项 | 通过标准 |
|--------|----------|
| 函数名 | 与源文件一致 |
| 参数列表 | 完整且顺序正确 |
| 返回值 | 类型与注释一致 |
| 格式 | 代码块可复制直接运行 |

#### 步骤 3：批量执行

1. 确认试运行无误后，对全量文件执行
2. 保留原始文件备份（建议 `backup/` 目录）
3. 输出结果按输入文件一一对应命名

#### 步骤 4：校验结果

1. 抽查 20% 输出条目（至少 5 条）
2. 核对关键字段与源数据一致性
3. 验证代码片段可独立运行（无外部依赖缺失）

**校验记录表：**

| 文件 | 函数数 | 抽查数 | 一致率 | 备注 |
|------|--------|--------|--------|------|
| 示例 | 10 | 2 | 100% | — |

### 3.3 输出规范

输出格式统一为：

```markdown
## [函数名]

**功能说明**：一句话描述

**参数表**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ... | ... | ... | ... |

**返回值**：类型 + 说明

**代码片段**：

```javascript
// 代码
```

**使用示例**：

```javascript
// 示例代码
```

**注意事项**：边界条件、性能提示等
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况，输出 `[需核实:字段]` 占位符，不编造内容：

| 场景 | 处理方式 |
|------|----------|
| 函数参数类型不确定 | 输出 `[需核实:参数类型]` |
| 返回值格式不明确 | 输出 `[需核实:返回值]` |
| 浏览器兼容性未知 | 输出 `[需核实:兼容性]` |
| 依赖的外部 API 版本未知 | 输出 `[需核实:API版本]` |

### 4.2 禁止行为

- 不猜测 API 行为
- 不虚构不存在的函数
- 不假设环境特性（如 Node 版本特有 API）

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 1. 确认文件路径 2. 检查文件名拼写 |
| `E002` | 编码不支持 | "文件编码非 UTF-8，请转换后重试" | 1. 使用 `iconv` 转换编码 2. 重新执行 |
| `E003` | 语法错误 | "文件包含语法错误，无法解析" | 1. 使用 `node --check` 检查 2. 修复语法错误 |
| `E004` | 输出目录不可写 | "输出目录无写入权限" | 1. 检查目录权限 2. 更换输出目录 |
| `E005` | 批量执行中断 | "批量执行中断，请检查日志" | 1. 查看错误日志 2. 定位失败文件 3. 单独重试 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 全局变量污染 | 在片段中直接定义全局变量 | 使用 IIFE 或模块封装 |
| 隐式类型转换 | 使用 `==` 而非 `===` | 始终使用严格相等 `===` |
| 回调地狱 | 多层嵌套回调 | 使用 Promise 或 async/await |
| 忽略错误处理 | 不捕获异常 | 添加 try-catch 或 .catch() |
| 硬编码魔法数 | 代码中出现无解释的数字 | 定义常量并添加注释 |

### 6.2 反模式示例

**反模式：**

```javascript
// 反模式：全局变量 + 隐式转换
result = 0;
function calc(a, b) {
  if (a == "10") {  // 隐式转换
    result = a + b;  // 全局变量
  }
}
```

**正确做法：**

```javascript
// 正确：模块化 + 严格比较
const DEFAULT_THRESHOLD = 10;

function calc(a, b) {
  if (a === DEFAULT_THRESHOLD) {
    return a + b;
  }
  return null;
}
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```markdown
1. 触发：输入 "js 片段" 或 "javascript bits"
2. 需求：描述你需要的功能（如 "数组去重"）
3. 获取：得到代码片段 + 使用说明
4. 验证：复制到本地运行测试
```

### 7.2 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围
2. 使用「触发方式」中的场景映射表定位需求
3. 按「标准流程」执行一次完整操作
4. 遇到问题查阅「错误码体系」

### 7.3 进阶路径（15 分钟）

1. 深入研究「FAQ 反模式对照」中的案例
2. 结合「置信度门控」理解信息处理边界
3. 使用「标准流程」中的校验方法验证输出质量
4. 将常用片段整理为个人工具库

---

## 八、实用片段示例

### 8.1 数组去重

```javascript
/**
 * 数组去重（支持基本类型）
 * @param {Array} arr 输入数组
 * @returns {Array} 去重后的新数组
 */
function uniqueArray(arr) {
  return [...new Set(arr)];
}

// 使用示例
const nums = [1, 2, 2, 3, 3, 4];
console.log(uniqueArray(nums)); // [1, 2, 3, 4]
```

### 8.2 防抖函数

```javascript
/**
 * 防抖函数
 * @param {Function} fn 目标函数
 * @param {number} delay 延迟时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
function debounce(fn, delay = 300) {
  let timer = null;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

// 使用示例
const handleResize = debounce(() => {
  console.log('窗口大小已调整');
}, 500);
window.addEventListener('resize', handleResize);
```

### 8.3 深拷贝（简易版）

```javascript
/**
 * 深拷贝（支持对象、数组、基本类型）
 * @param {*} obj 输入值
 * @returns {*} 深拷贝后的值
 */
function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(item => deepClone(item));
  }
  const result = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      result[key] = deepClone(obj[key]);
    }
  }
  return result;
}

// 使用示例
const original = { a: 1, b: { c: 2 } };
const cloned = deepClone(original);
cloned.b.c = 99;
console.log(original.b.c); // 2（原对象不受影响）
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的代码片段仅供参考，使用者应在实际环境中充分测试后再用于生产环境。

2. **禁止反向工程**：不得对本 Skill 的元数据、结构、生成逻辑进行反向工程、反编译或试图提取底层算法。

3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

4. **合规使用**：使用者应确保使用方式符合当地法律法规及所在组织的安全规范。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 CodeCraft Studio

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
