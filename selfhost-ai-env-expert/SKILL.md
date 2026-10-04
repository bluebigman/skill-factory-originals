---
name: backup-exposure-auditor
slug: backup-exposure-auditor
displayName: 备份与暴露面 核验
description: "核验自托管环境的备份策略与对外暴露声明。检出保留期为 0、未验证恢复、无异地副本、暴露公网与缺少鉴权并分级输出。"
license: MIT License
version: 1.0.0
author: user_2fd890c9
source_project: original
---

# 备份与暴露面 核验

## 简介

核验自托管环境的备份策略与对外暴露声明。检出保留期为 0、未验证恢复、无异地副本、暴露公网与缺少鉴权并分级输出。

本技能属于**自托管 / AI 环境部署（雷达标的 AgentVerse-OS 732 star）**需求方向，面向需要在实际工作中反复处理该类任务的用户。
实现完全离线运行，不发起网络调用、不采集用户数据、不读写隐私文件。

核心能力：按声明逐条判级，输出高危项清单与可追溯报告，缺项按约定基线补判。

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

## 声明写法

每行一条声明，`#` 起始为注释；`policy` 行用于覆盖阈值。

```
backup name=backup-demo
expose name=expose-demo
policy min_retention_days=14
```

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
print(result["report"])
```

## 常见问题

**Q1：输入文件是 GBK 编码读出来乱码怎么办？**
A：内置 `read_text_safe` 会依次尝试 utf-8 / gbk / gb18030 / latin-1，仍失败则用 `errors="replace"` 兜底，不会因编码问题中断。

**Q2：声明行写错了会怎样？**
A：无法识别的行会被跳过而不是报错；字段缺失按规则逐条判级，命中哪条报哪条。

**Q3：阈值能不能改？**
A：可以。在输入里加一行 `policy` 覆盖默认值，例如 `policy min_mem_gb=16`。

**Q4：出错会不会直接崩掉？**
A：不会。主流程用 `except Exception` 兜底，把异常转成 `{"ok": false, "error": "..."}` 结构化输出。

**Q5：会不会外发数据？**
A：不会。本技能完全离线，无任何网络请求。

**Q6：判级标准是什么？**
A：HIGH 表示必须先修正再交付；MEDIUM 表示须给出理由或限期整改；LOW 表示建议补齐。结论以高危项数量为准。

## 输出说明

统一输出 JSON：

```json
{
  "ok": true,
  "decl_count": 3,
  "issue_total": 4,
  "high_risk_count": 1,
  "conclusion": "发现 1 处高危，须先修正再交付",
  "report": "== ... =="
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
