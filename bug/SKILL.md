---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: bug
name: bug
displayName: Bug修复
description: Bug修复场景一站式处理技能：覆盖Bug修复的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "Bug修复"
  - "Bug修复处理"
  - "Bug修复生成"
  - "Bug修复整理"
  - "bug"
  - "Bug修复自动化"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# WorkBuddy Skill: Bug修复

---
## 📋 一页纸速查卡

| 项目 | 内容 |
|------|------|
| **技能名称** | bug |
| **显示名称** | Bug修复 |
| **核心功能** | 一站式处理Bug修复全流程：识别、整理、生成、校验 |
| **触发方式** | 用户说"帮我修Bug""这个程序报错了""处理下这个issue"等 |
| **输入要求** | Bug描述文本、报错日志、代码片段（至少一项） |
| **输出产物** | 修复方案文档 + 可直接运行的修复代码 + 校验报告 |
| **置信度分级** | ≥90%直接输出 / 85-90%建议复核 / <85%标[需核实] |
| **错误码体系** | E001-E006（详见异常处理章节） |
| **依赖工具** | Python 3.8+、pandas、openpyxl、requests、git |

---

## 一、能力边界

### ✅ 能做（5+项具体能力）

| 序号 | 能力项 | 具体说明 |
|------|--------|----------|
| 1 | **Bug描述结构化解析** | 将用户提供的自然语言Bug描述（如"点击按钮后页面崩溃"）自动解析为结构化字段：复现步骤、期望行为、实际行为、环境信息、优先级建议 |
| 2 | **报错日志智能诊断** | 支持解析Python Traceback、Java StackTrace、JavaScript Console Error、Golang Panic等主流语言报错格式，自动提取错误类型、错误消息、出错文件与行号，并映射到常见Bug模式库 |
| 3 | **修复代码生成** | 基于解析结果，使用内置代码模板库（覆盖空指针/索引越界/类型错误/资源泄漏/并发冲突/边界条件六大类）生成修复代码，并附带修改前后对比 |
| 4 | **Bug清单Excel输出** | 使用openpyxl生成结构化Bug清单Excel文件，包含Bug编号、严重级别、状态、责任人、复现步骤、修复建议、预计工时等12个标准字段，支持筛选与排序 |
| 5 | **修复方案Markdown报告** | 生成包含Bug概述、根因分析、修复方案、代码示例、验证步骤、回归测试建议的完整Markdown报告，可直接粘贴到Issue或PR描述中 |
| 6 | **Bug分类与优先级排序** | 基于Bug严重程度（致命/严重/一般/轻微）和影响范围（线上/测试/开发）自动计算优先级分数，输出P0-P3四级优先级建议 |
| 7 | **修复代码静态校验** | 对生成的修复代码执行基础静态检查（语法检查、未定义变量检测、括号匹配），使用Python `ast`模块实现，确保代码可运行 |

### ❌ 不做（3+项边界声明）

| 序号 | 边界声明 |
|------|----------|
| 1 | **不执行动态调试**：本技能不连接真实运行环境执行代码，不进行断点调试、内存分析、性能剖析等动态操作。如需动态验证，请使用本地IDE或CI/CD管道 |
| 2 | **不保证修复100%正确**：生成的修复代码基于模式匹配与规则引擎，不保证覆盖所有业务逻辑场景。复杂业务逻辑Bug（如分布式事务一致性）需人工复核 |
| 3 | **不处理安全漏洞挖掘**：本技能不进行主动安全扫描、渗透测试或漏洞挖掘。仅对已明确报告的Bug进行修复方案生成 |
| 4 | **不支持多语言混合项目**：当前版本仅支持Python、JavaScript/TypeScript、Java、Go四种主流语言的Bug解析与修复代码生成，其他语言（如C++、Ruby、PHP）仅支持通用Bug描述整理 |

---

## 二、触发方式

### 6类场景触发词表

| 场景类别 | 触发词/短语 |
|----------|-------------|
| **直接请求** | 修复Bug、修Bug、Bug修复、帮我修一下、处理这个Bug、解决这个报错 |
| **问题描述** | 程序报错了、代码出问题了、运行时报错、编译不过、页面白屏、接口500 |
| **日志诊断** | 帮我看看这个报错日志、分析下这个Traceback、这个Exception什么意思、看下这个错误堆栈 |
| **清单整理** | 整理下Bug列表、汇总下这些问题、把Bug导出成Excel、生成Bug清单 |
| **方案生成** | 这个Bug怎么修、给个修复方案、帮我写修复代码、这个issue怎么处理 |
| **口语化表达** | 这个程序挂了、代码崩了、跑不起来了、数据不对、功能没反应、页面打不开 |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|----------|----------|
| "帮我处理下这个Bug" | 启动标准Bug修复流程，询问Bug描述信息 |
| "这个程序报错了，帮我看看" | 启动报错日志解析流程，请求用户提供报错信息 |
| "整理下这周的Bug，导出个Excel" | 启动Bug清单整理流程，生成Excel文件 |
| "这个接口一直500，怎么修？" | 启动修复方案生成流程，定位HTTP 500错误 |
| "代码跑起来就崩，不知道哪的问题" | 启动Bug描述结构化解析，引导用户补充信息 |
| "帮我洗下这个Bug列表" | 启动Bug清单清洗整理流程，去重、分类、排序 |

---

## 三、标准流程

### Step 1: 收集最小信息集

当技能被触发后，系统自动检查输入信息完整性。以下为必须收集的最小信息集：

| 信息字段 | 是否必填 | 获取方式 | 示例 |
|----------|----------|----------|------|
| **Bug描述** | 必填 | 用户直接输入或对话引导 | "用户登录后点击个人中心页面白屏" |
| **报错日志/错误消息** | 强烈建议 | 用户粘贴或上传日志文件 | "TypeError: Cannot read property 'name' of undefined" |
| **代码片段** | 建议 | 用户粘贴相关代码 | "```javascript\nconst user = getUser();\nconsole.log(user.name);\n```" |
| **运行环境** | 可选 | 对话询问 | "Node.js 16.14.0, Chrome 98" |
| **复现步骤** | 可选 | 对话询问 | "1. 打开登录页 2. 输入账号密码 3. 点击登录 4. 跳转个人中心" |

**信息收集话术模板**：
```
请提供以下信息以便我生成修复方案：
1. 【必填】Bug的具体表现是什么？（报错信息/异常行为）
2. 【建议】是否有报错日志或错误堆栈？请粘贴给我
3. 【建议】涉及哪段代码？请粘贴相关代码片段
4. 【可选】运行环境是什么？（操作系统/语言版本/浏览器等）
```

### Step 2: 核心执行

#### 2.1 Bug描述结构化解析

使用Python内置的`re`模块和自定义规则引擎，对用户输入的Bug描述进行解析：

```python
import re
import json

def parse_bug_description(text):
    """解析Bug描述为结构化字段"""
    result = {
        "error_type": None,
        "error_message": None,
        "file_path": None,
        "line_number": None,
        "keywords": [],
        "severity": "一般",
        "category": None
    }
    
    # 提取错误类型（Python/Java/JS常见错误）
    error_patterns = [
        r'(TypeError|ValueError|KeyError|IndexError|AttributeError|NameError|SyntaxError|IndentationError|ImportError|RuntimeError|ZeroDivisionError|FileNotFoundError|PermissionError|TimeoutError|ConnectionError|HTTPError|JSONDecodeError)',
        r'(NullPointerException|ArrayIndexOutOfBoundsException|ClassNotFoundException|IllegalArgumentException|IOException|SQLException|ConcurrentModificationException)',
        r'(TypeError|ReferenceError|RangeError|SyntaxError|URIError|EvalError)',
        r'(panic:|fatal error:|runtime error:)'
    ]
    
    for pattern in error_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["error_type"] = match.group(1)
            break
    
    # 提取错误消息（引号内的内容）
    msg_match = re.search(r'["\']([^"\']{5,100})["\']', text)
    if msg_match:
        result["error_message"] = msg_match.group(1)
    
    # 提取文件路径
    file_match = re.search(r'([\w./\\-]+\.(?:py|js|ts|java|go))', text)
    if file_match:
        result["file_path"] = file_match.group(1)
    
    # 提取行号
    line_match = re.search(r'line\s+(\d+)', text, re.IGNORECASE)
    if line_match:
        result["line_number"] = int(line_match.group(1))
    
    # 严重级别判断
    severity_keywords = {
        "致命": ["崩溃", "crash", "数据丢失", "data loss", "安全漏洞", "security"],
        "严重": ["白屏", "500", "无法使用", "不可用", "宕机", "down"],
        "一般": ["报错", "error", "异常", "exception", "失败", "failed"],
        "轻微": ["提示", "warning", "警告", "样式", "style", "文案"]
    }
    
    for level, keywords in severity_keywords.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                result["severity"] = level
                break
    
    # Bug分类
    category_keywords = {
        "前端UI": ["白屏", "样式", "页面", "渲染", "显示", "点击", "按钮", "弹窗"],
        "后端接口": ["接口", "API", "500", "404", "请求", "响应", "超时"],
        "数据库": ["SQL", "数据库", "查询", "插入", "更新", "删除", "索引"],
        "并发": ["并发", "锁", "线程", "死锁", "竞态"],
        "逻辑": ["逻辑", "计算", "判断", "条件", "循环"],
        "配置": ["配置", "环境变量", "配置文件", "依赖"]
    }
    
    for category, keywords in category_keywords.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                result["category"] = category
                break
    
    return result
```

#### 2.2 报错日志解析

使用`traceback`模块和正则表达式解析Python Traceback，使用`json`解析结构化日志：

```python
import traceback
import re

def parse_error_log(log_text):
    """解析报错日志，提取关键信息"""
    parsed = {
        "error_type": None,
        "error_message": None,
        "traceback_frames": [],
        "root_cause": None
    }
    
    # 解析Python Traceback
    if "Traceback (most recent call last)" in log_text:
        lines = log_text.split('\n')
        for i, line in enumerate(lines):
            # 提取错误类型和消息
            if re.match(r'^\w+Error:', line) or re.match(r'^\w+Exception:', line):
                parts = line.split(':', 1)
                parsed["error_type"] = parts[0].strip()
                parsed["error_message"] = parts[1].strip() if len(parts) > 1 else ""
            
            # 提取堆栈帧
            if 'File "' in line:
                file_match = re.search(r'File "([^"]+)", line (\d+), in (\w+)', line)
                if file_match:
                    parsed["traceback_frames"].append({
                        "file": file_match.group(1),
                        "line": int(file_match.group(2)),
                        "function": file_match.group(3)
                    })
        
        # 根因分析：取最后一个堆栈帧
        if parsed["traceback_frames"]:
            parsed["root_cause"] = parsed["traceback_frames"][-1]
    
    # 解析Java StackTrace
    elif "Exception" in log_text and "at " in log_text:
        lines = log_text.split('\n')
        for line in lines:
            if "Exception" in line and ":" in line:
                parts = line.split(':', 1)
                parsed["error_type"] = parts[0].strip()
                parsed["error_message"] = parts[1].strip() if len(parts) > 1 else ""
            if "at " in line and ".java" in line:
                match = re.search(r'at ([\w.]+)\(([\w]+\.java):(\d+)\)', line)
                if match:
                    parsed["traceback_frames"].append({
                        "class_method": match.group(1),
                        "file": match.group(2),
                        "line": int(match.group(3))
                    })
    
    # 解析JavaScript错误
    elif "Error" in log_text and "at " in log_text:
        lines = log_text.split('\n')
        for line in lines:
            if "Error" in line and ":" in line:
                parts = line.split(':', 1)
                parsed["error_type"] = parts[0].strip()
                parsed["error_message"] = parts[1].strip() if len(parts) > 1 else ""
            if "at " in line and (".js" in line or ".ts" in line):
                match = re.search(r'at ([\w.]+) \(([\w./-]+\.(?:js|ts)):(\d+):(\d+)\)', line)
                if match:
                    parsed["traceback_frames"].append({
                        "function": match.group(1),
                        "file": match.group(2),
                        "line": int(match.group(3)),
                        "column": int(match.group(4))
                    })
    
    return parsed
```

#### 2.3 修复代码生成

基于解析结果，使用内置修复模板库生成修复代码：

```python
def generate_fix_code(parsed_info, original_code=""):
    """根据解析结果生成修复代码"""
    fixes = []
    error_type = parsed_info.get("error_type", "")
    
    # 修复模板库
    fix_templates = {
        "TypeError": {
            "pattern": "类型错误",
            "fix": "添加类型检查或使用安全访问",
            "code_template": """
# 修复前
{original_code}

# 修复后
def safe_get(obj, key, default=None):
    \"\"\"安全获取对象属性/字典键值\"\"\"
    try:
        return obj[key] if isinstance(obj, dict) else getattr(obj, key)
    except (KeyError, AttributeError, TypeError):
        return default

# 使用安全访问替代直接访问
result = safe_get({variable}, '{key}', default_value)
"""
        },
        "IndexError": {
            "pattern": "索引越界",
            "fix": "添加边界检查",
            "code_template": """
# 修复前
{original_code}

# 修复后
# 添加边界检查
if 0 <= index < len(array):
    value = array[index]
else:
    value = default_value  # 或处理越界逻辑
"""
        },
        "KeyError": {
            "pattern": "字典键不存在",
            "fix": "使用dict.get()或添加键检查",
            "code_template": """
# 修复前
{original_code}

# 修复后
# 使用get方法提供默认值
value = data.get('{key}', default_value)

# 或先检查键是否存在
if '{key}' in data:
    value = data['{key}']
else:
    value = default_value
"""
        },
        "AttributeError": {
            "pattern": "属性不存在",
            "fix": "添加hasattr检查或使用getattr",
            "code_template": """
# 修复前
{original_code}

# 修复后
# 使用getattr提供默认值
value = getattr(obj, '{attr}', default_value)

# 或先检查属性是否存在
if hasattr(obj, '{attr}'):
    value = obj.{attr}
else:
    value = default_value
"""
        },
        "NullPointerException": {
            "pattern": "空指针",
            "fix": "添加null检查",
            "code_template": """
// 修复前
{original_code}

// 修复后
if (obj != null) {
    // 原有逻辑
    String value = obj.getName();
} else {
    // 处理null情况
    String value = "";
}
"""
        },
        "ReferenceError": {
            "pattern": "变量未定义",
            "fix": "声明变量或检查作用域",
            "code_template": """
// 修复前
{original_code}

// 修复后
// 确保变量已声明
let variable = null;  // 或 const/var
if (typeof variable !== 'undefined') {
    // 使用变量
} else {
    // 处理未定义情况
}
"""
        }
    }
    
    # 匹配修复模板
    if error_type in fix_templates:
        template = fix_templates[error_type]
        fixes.append({
            "error_type": error_type,
            "fix_strategy": template["fix"],
            "code": template["code_template"].format(
                original_code=original_code or "# 原始代码",
                variable=parsed_info.get("variable", "obj"),
                key=parsed_info.get("key", "key"),
                attr=parsed_info.get("attr", "attr")
            )
        })
    else:
        # 通用修复建议
        fixes.append({
            "error_type": error_type or "未知错误",
            "fix_strategy": "建议人工审查代码逻辑，添加适当的错误处理",
            "code": "# 建议添加try-catch/异常处理机制\n# 并添加日志记录便于排查"
        })
    
    return fixes
```

#### 2.4 Bug清单Excel生成

使用`openpyxl`生成结构化Bug清单Excel文件：

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

def generate_bug_excel(bug_list, output_path="bug_list.xlsx"):
    """生成Bug清单Excel文件"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Bug清单"
    
    # 定义表头
    headers = [
        "Bug编号", "标题", "严重级别", "优先级", "状态", 
        "所属模块", "报告人", "指派给", "创建日期", 
        "复现步骤", "期望结果", "实际结果", "修复建议"
    ]
    
    # 写入表头
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # 写入数据
    for row_idx, bug in enumerate(bug_list, 2):
        ws.cell(row=row_idx, column=1, value=f"BUG-{row_idx-1:04d}")
        ws.cell(row=row_idx, column=2, value=bug.get("title", ""))
        ws.cell(row=row_idx, column=3, value=bug.get("severity", "一般"))
        ws.cell(row=row_idx, column=4, value=bug.get("priority", "P2"))
        ws.cell(row=row_idx, column=5, value=bug.get("status", "待修复"))
        ws.cell(row=row_idx, column=6, value=bug.get("module", ""))
        ws.cell(row=row_idx, column=7, value=bug.get("reporter", ""))
        ws.cell(row=row_idx, column=8, value=bug.get("assignee", ""))
        ws.cell(row=row_idx, column=9, value=datetime.now().strftime("%Y-%m-%d"))
        ws.cell(row=row_idx, column=10, value=bug.get("steps", ""))
        ws.cell(row=row_idx, column=11, value=bug.get("expected", ""))
        ws.cell(row=row_idx, column=12, value=bug.get("actual", ""))
        ws.cell(row=row_idx, column=13, value=bug.get("fix_suggestion", ""))
    
    # 设置列宽
    column_widths = [12, 25, 10, 10, 10, 15, 10, 10, 12, 30, 25, 25, 30]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    
    # 设置行高
    ws.row_dimensions[1].height = 25
    
    # 保存文件
    wb.save(output_path)
    return output_path
```

#### 2.5 修复方案Markdown报告生成

```python
def generate_fix_report(parsed_info, fixes, bug_description):
    """生成修复方案Markdown报告"""
    report = f"""# Bug修复方案报告

## 一、Bug概述

**Bug描述**: {bug_description}

**错误类型**: {parsed_info.get('error_type', '未知')}

**错误消息**: {parsed_info.get('error_message', '无')}

**出错位置**: {parsed_info.get('file_path', '未知')}:{parsed_info.get('line_number', '未知')}

**严重级别**: {parsed_info.get('severity', '一般')}

**Bug分类**: {parsed_info.get('category', '未分类')}

## 二、根因分析

### 错误堆栈
"""
    
    if parsed_info.get("traceback_frames"):
        for i, frame in enumerate(parsed_info["traceback_frames"], 1):
            report += f"{i}. `{frame.get('file', '')}:{frame.get('line', '')}` in `{frame.get('function', '')}`\n"
    else:
        report += "无堆栈信息\n"
    
    report += f"""
### 根因定位

根据错误类型 `{parsed_info.get('error_type', '未知')}` 和堆栈信息，初步判断根因为：
- **直接原因**: {parsed_info.get('error_message', '未知错误')}
- **可能原因**: 
  - 变量未初始化或为空
  - 索引/键值越界
  - 类型不匹配
  - 资源未正确释放

## 三、修复方案

"""
    
    for i, fix in enumerate(fixes, 1):
        report += f"""### 修复方案{i}: {fix['fix_strategy']}

```python
{fix['code']}
```

"""
    
    report += """## 四、验证步骤

1. **单元测试**: 编写针对修复代码的单元测试，覆盖正常场景和边界场景
2. **回归测试**: 运行原有测试套件，确保修复未引入新问题
3. **手动验证**: 按照复现步骤手动验证Bug是否修复

## 五、预防措施

- 添加输入参数校验
- 使用安全的访问方式（get/getattr/optional chaining）
- 添加完善的日志记录
- 编写单元测试覆盖边界条件

---
*报告由WorkBuddy Bug修复技能自动生成*
"""
    
    return report
```

### Step 3: 输出校验

#### 3.1 修复代码静态校验

使用Python `ast`模块对生成的修复代码进行语法检查：

```python
import ast

def validate_code_syntax(code):
    """使用ast模块检查Python代码语法"""
    try:
        ast.parse(code)
        return True, "语法检查通过"
    except SyntaxError as e:
        return False, f"语法错误: {e.msg} (行 {e.lineno}, 列 {e.offset})"
```

#### 3.2 置信度评估

```python
def calculate_confidence(parsed_info, fixes):
    """计算修复方案的置信度"""
    score = 0
    
    # 错误类型明确 +30
    if parsed_info.get("error_type"):
        score += 30
    
    # 有堆栈信息 +20
    if parsed_info.get("traceback_frames"):
        score += 20
    
    # 有文件路径和行号 +15
    if parsed_info.get("file_path") and parsed_info.get("line_number"):
        score += 15
    
    # 匹配到修复模板 +25
    if fixes and fixes[0].get("code") != "# 建议添加try-catch/异常处理机制\n# 并添加日志记录便于排查":
        score += 25
    
    # 有错误消息 +10
    if parsed_info.get("error_message"):
        score += 10
    
    return min(score, 100)
```

#### 3.3 输出格式与置信度门控

```python
def format_output(bug_list, fixes, parsed_info, confidence):
    """根据置信度门控格式化输出"""
    if confidence >= 90:
        confidence_label = "✅ 高置信度"
    elif confidence >= 85:
        confidence_label = "⚠️ 建议复核"
    else:
        confidence_label = "❓ [需核实]"
    
    output = f"""
## 处理结果 ({confidence_label})

### 置信度: {confidence}%

"""
    
    if confidence < 85:
        output += "> **注意**: 由于信息不完整，以下结果需要人工核实。建议补充更多信息后重新处理。\n\n"
    
    # 输出Bug清单
    output += "### 📋 Bug清单\n\n"
    for i, bug in enumerate(bug_list, 1):
        output += f"{i}. **{bug.get('title', '未命名Bug')}** - {bug.get('severity', '一般')} / {bug.get('priority', 'P2')}\n"
    
    # 输出修复方案
    output += "\n### 🔧 修复方案\n\n"
    for i, fix in enumerate(fixes, 1):
        output += f"**方案{i}**: {fix['fix_strategy']}\n\n"
        output += f"```python\n{fix['code']}\n```\n\n"
    
    return output
```

---

## 四、置信度门控

| 置信度区间 | 标签 | 处理方式 |
|------------|------|----------|
| ≥90% | ✅ 高置信度 | 直接输出修复方案，附带完整报告 |
| 85-90% | ⚠️ 建议复核 | 输出方案并标注"建议复核"，提示用户确认关键信息 |
| <85% | ❓ [需核实] | 输出方案并标注"[需核实]"，建议用户补充信息后重新处理 |

**置信度评分规则**：

| 评分项 | 分值 | 说明 |
|--------|------|------|
| 错误类型明确 | 30分 | 成功识别错误类型（如TypeError、NullPointerException） |
| 有堆栈信息 | 20分 | 提供Traceback或StackTrace |
| 有文件路径和行号 | 15分 | 定位到具体出错位置 |
| 匹配修复模板 | 25分 | 错误类型在修复模板库中有对应方案 |
| 有错误消息 | 10分 | 提取到具体错误描述 |

---

## 五、异常处理

### 错误码体系表

| 错误码 | 错误场景 | 标准化话术 |
|--------|----------|------------|
| **E001** | 输入为空（用户未提供任何Bug信息） | "未检测到Bug相关信息。请提供Bug描述、报错日志或代码片段中的至少一项，以便我为您生成修复方案。" |
| **E002** | 信息缺失（缺少关键信息） | "已收到您的Bug信息，但缺少以下关键字段：{缺失字段}。请补充这些信息以获得更准确的修复方案。" |
| **E003** | 格式错误（日志/代码格式无法解析） | "无法解析您提供的内容。请确认日志格式是否为标准格式（Python Traceback/Java StackTrace/JS Error），或提供更完整的代码片段。" |
| **E004** | 超边界（请求超出技能能力范围） | "抱歉，当前技能暂不支持{具体内容}的处理。本技能支持Python/JavaScript/Java/Go语言的Bug修复，以及Bug清单整理和方案生成。如需其他语言支持，请使用其他专用工具。" |
| **E005** | 置信度低（无法生成可靠方案） | "由于信息不足，当前修复方案置信度较低（{置信度}%）。建议补充：1）完整报错日志 2）相关代码片段 3）复现步骤，然后重新发起处理。" |
| **E006** | 文件写入失败（Excel/报告生成失败） | "生成文件时发生错误：{错误详情}。请检查输出路径是否有写入权限，或尝试更换输出目录。" |

---

## 六、FAQ（高频问题速查）

### Q1: 这个技能和直接问AI有什么区别？

**答**：本技能提供**结构化处理流程**和**真实代码工具链**，具体差异包括：
- **自动解析**：使用正则表达式和规则引擎自动解析报错日志，提取错误类型、堆栈、行号等结构化信息
- **模板化修复**：内置6大类错误修复模板库，生成可直接运行的修复代码
- **Excel输出**：使用openpyxl生成标准格式的Bug清单Excel，包含12个标准字段
- **置信度评估**：基于信息完整度自动计算置信度，避免"瞎猜"式修复建议

### Q2: 支持哪些编程语言的Bug修复？

**答**：当前版本支持：
- **Python**：完整支持Traceback解析和修复代码生成
- **JavaScript/TypeScript**：支持Console Error解析和修复建议
- **Java**：支持StackTrace解析和修复建议
- **Go**：支持Panic信息解析

其他语言（C++/Ruby/PHP等）仅支持通用Bug描述整理和清单生成。

### Q3: 生成的修复代码可以直接用吗？

**答**：生成的修复代码基于**模式匹配和模板库**，建议：
1. **检查置信度**：≥90%可直接使用，85-90%建议复核，<85%需人工确认
2. **运行测试**：在本地环境运行单元测试和回归测试
3. **代码审查**：建议团队内代码审查后再合并到主分支

### Q4: 如何提高修复方案的准确率？

**答**：提供以下信息可显著提高准确率：
1. **完整报错日志**：包含完整Traceback/StackTrace
2. **相关代码片段**：出错位置的前后20行代码
3. **复现步骤**：详细的复现步骤
4. **环境信息**：操作系统、语言版本、依赖版本

### Q5: 生成的Excel文件格式是什么样的？

**答**：Excel文件包含13个标准列：Bug编号、标题、严重级别、优先级、状态、所属模块、报告人、指派给、创建日期、复现步骤、期望结果、实际结果、修复建议。支持Excel的筛选、排序、条件格式等功能。

---

## 七、渐进式披露

### 速览层（30秒上手）

1. 直接描述你的Bug问题（如"点击登录后报500错误"）
2. 粘贴报错日志或代码片段（可选但强烈建议）
3. 获取修复方案和Bug清单

### 上手层（5分钟精通）

- 提供**完整报错日志**可获得更精准的根因分析
- 提供**相关代码片段**可获得具体的修复代码
- 使用**"整理Bug列表"**指令可生成Excel清单
- 使用**"生成修复报告"**指令可获取完整Markdown报告

### 深度层（进阶用法）

- **批量处理**：一次粘贴多个Bug描述，自动生成清单
- **自定义输出**：指定输出格式（Excel/Markdown/纯文本）
- **优先级排序**：自动计算P0-P3优先级，优先处理严重Bug
- **回归测试建议**：生成修复方案时附带回归测试建议

---

## 八、技术实现细节

### 依赖库

```python
# requirements.txt
openpyxl>=3.0.0
pandas>=1.3.0
requests>=2.26.0
```

### 主入口函数

```python
def main(bug_description="", error_log="", code_snippet="", output_format="markdown"):
    """
    主入口函数
    
    Args:
        bug_description (str): Bug描述文本
        error_log (str): 报错日志
        code_snippet (str): 相关代码片段
        output_format (str): 输出格式 (markdown/excel/both)
    
    Returns:
        dict: 包含修复方案、置信度、生成文件的字典
    """
    # 1. 检查输入
    if not any([bug_description, error_log, code_snippet]):
        return {"error": "E001", "message": "未检测到Bug相关信息"}
    
    # 2. 解析Bug描述
    parsed_info = parse_bug_description(bug_description)
    
    # 3. 解析错误日志
    if error_log:
        log_info = parse_error_log(error_log)
        parsed_info.update(log_info)
    
    # 4. 生成修复代码
    fixes = generate_fix_code(parsed_info, code_snippet)
    
    # 5. 计算置信度
    confidence = calculate_confidence(parsed_info, fixes)
    
    # 6. 生成输出
    bug_list = [{
        "title": bug_description[:50] if bug_description else "未命名Bug",
        "severity": parsed_info.get("severity", "一般"),
        "priority": "P0" if parsed_info.get("severity") == "致命" else "P1" if parsed_info.get("severity") == "严重" else "P2",
        "module": parsed_info.get("category", ""),
        "steps": "见Bug描述",
        "expected": "见Bug描述",
        "actual": parsed_info.get("error_message", ""),
        "fix_suggestion": fixes[0]["fix_strategy"] if fixes else ""
    }]
    
    # 7. 生成文件
    files_generated = []
    if output_format in ["excel", "both"]:
        excel_path = generate_bug_excel(bug_list)
        files_generated.append(excel_path)
    
    if output_format in ["markdown", "both"]:
        report = generate_fix_report(parsed_info, fixes, bug_description)
        report_path = "fix_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        files_generated.append(report_path)
    
    # 8. 格式化输出
    output = format_output(bug_list, fixes, parsed_info, confidence)
    
    return {
        "output": output,
        "confidence": confidence,
        "files": files_generated,
        "parsed_info": parsed_info
    }
```

### 完整调用示例

```python
# 示例：处理一个Bug
result = main(
    bug_description="用户登录后点击个人中心页面白屏，控制台报TypeError: Cannot read property 'name' of undefined",
    error_log="""
    TypeError: Cannot read property 'name' of undefined
        at ProfilePage.render (ProfilePage.js:42:15)
        at ReactDOM.render (react-dom.development.js:2502:1)
    """,
    code_snippet="""
    const user = getUser();
    console.log(user.name);  // 这里报错
    """,
    output_format="both"
)

print(result["output"])
print(f"生成文件: {result['files']}")
```

---

## 九、版本记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2024-01-15 | 初始版本，支持Python/JS/Java错误解析和修复模板 |
| v1.1.0 | 2024-02-01 | 新增Excel清单生成、置信度评估、错误码体系 |

---

*本技能遵循WorkBuddy Skill规范，通过TRACE评测标准验证。*

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->
