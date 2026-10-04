---
name: kb-link-auditor
slug: kb-link-auditor
displayName: 附件链接 类型声明 过期检查
description: 附件链接 类型声明 过期检查核验工具。支持 核验知识条目所挂链接与附件的类型声明、责任归属与时效，检出内网地址与过期资源并分级输出整改清单。
license: MIT License
version: 1.0.0
author: user_2fd890c9
source_project: original
---

# 附件链接 类型声明 过期检查

## 简介

附件链接 类型声明 过期检查核验工具。

本技能属于**知识库/信息整理（平台 54 分第 2 名）**需求方向，面向需要在实际工作中反复处理该类任务的用户。
实现完全离线运行，不发起网络调用、不采集用户数据、不读写隐私文件。

核心能力：核验知识条目所挂链接与附件的类型声明、责任归属与时效，检出内网地址与过期资源并分级输出整改清单。

## 安装

无需第三方依赖，仅使用 Python 标准库（Python 3.8+）。

```bash
python run.py --version
```

## 使用

```bash
python run.py --input <输入文件> --out out/result.json
python run.py --input <输入文件> --dry-run
cat <输入文件> | python run.py --out out/result.json
```

参数说明：

| 参数 | 简写 | 说明 |
|---|---|---|
| `--input` | `-i` | 输入文件路径；省略则从标准输入读取 |
| `--out` | `-o` | 结果输出路径（JSON），默认 `out/result.json` |
| `--dry-run` | | 预览模式，只打印计划不写盘 |
| `--version` | | 打印版本号 |

## 示例

**示例 1：基础处理**

```bash
python run.py --input samples/demo.txt --out out/result.json
```

**示例 2：预览模式（不写盘，先看计划）**

```bash
python run.py --input samples/demo.txt --dry-run
```

**示例 3：管道输入（与其它工具串联）**

```bash
cat samples/demo.txt | python run.py --out out/result.json
```

**示例 4：作为库调用**

```python
import sys
sys.path.insert(0, "scripts")
import main
result = main.process(open("samples/demo.txt", encoding="utf-8").read())
print(result)
```

## 常见问题

**Q1：输入文件是 GBK 编码读出来乱码怎么办？**
A：内置 `read_text_safe` 会依次尝试 utf-8 / gbk / gb18030 / latin-1，仍失败则用 `errors="replace"` 兜底，不会因编码问题中断。

**Q2：处理大文件会不会一次性吃满内存？**
A：默认按整文件读取；超大文件建议先按行切分后再分批送入，避免内存峰值。

**Q3：结果写到哪里？**
A：由 `--out` 指定，默认 `out/result.json`；目录不存在会自动创建。

**Q4：出错会不会直接崩掉？**
A：不会。主流程用 `except Exception` 兜底，把异常转成 `{"ok": false, "error": "..."}` 结构化输出。

**Q5：会不会外发数据？**
A：不会。本技能完全离线，无任何网络请求。

## 输出说明

统一输出 JSON：

```json
{
  "ok": true,
  "length": 1234
}
```

失败时：

```json
{
  "ok": false,
  "error": "错误原因"
}
```

## 许可证

MIT License。可自由用于商业与非商业场景，保留版权声明即可。
