---
name: deploy-config-linter
slug: deploy-config-linter
displayName: 部署配置规范校验
description: 按内置规则集校验部署配置，输出违规项分级、合规分与可执行修正建议，覆盖副本、镜像、端口、资源与探针。
license: MIT License
version: 1.0.0
author: user_2fd890c9
source_project: original
---

# 部署配置规范校验

## 简介

把部署配置贴进来，直接得到**合规分 + 违规项清单 + 每条对应的修正动作**，在发布前把低级问题挡掉。

本技能属于**运维/配置解析/部署（平台 TOP20 占 11 席）**需求方向，解决"配置写错了要等上线才发现"：
副本数为 0、镜像用了 `:latest`、端口写成 70000、内存写成 `512` 没单位、没声明探针——都可提前拦截。

核心能力：

| 能力 | 说明 |
|---|---|
| 解析 | 缩进型 YAML 子集（含 `- ` 列表项，路径带 `[i]`）与 `KEY=VALUE` 平铺，自动选择 |
| 单键规则 | 副本数下限与单点、镜像版本标签、端口范围与特权端口、CPU 与内存写法及配额上限 |
| 结构规则 | 存活探针、就绪探针、资源限额是否同时声明、挂载点与存储声明是否配套 |
| 命名规则 | 环境变量键名要求大写字母 + 数字 + 下划线 |
| 打分 | 满分 100，ERROR 扣 12、WARN 扣 4，下限 0 |
| 交付物 | 校验报告 Markdown + 结构化 JSON + 合规分 + 修正建议清单 |

本实现完全离线：不发起网络调用、不采集用户数据、不读写隐私文件。

## 安装

无需第三方依赖，仅使用 Python 标准库（Python 3.8+）。

```bash
python run.py --version
```

## 使用

```bash
python run.py --input <部署配置> --out out/result.json
python run.py --input <部署配置> --dry-run
cat <部署配置> | python run.py --out out/result.json
```

参数说明：

| 参数 | 简写 | 说明 |
|---|---|---|
| `--input` | `-i` | 输入文件路径（部署配置文本）；省略则从标准输入读取 |
| `--out` | `-o` | 结果输出路径（JSON），默认 `out/result.json` |
| `--dry-run` | | 预览模式，只打印计划不写盘 |
| `--version` | | 打印版本号 |

## 示例

**示例 1：一份有问题的负载配置**

```bash
printf 'app:\n  replicas: 0\n  image: demo:latest\n  port: 70000\n  resources:\n    cpu: 4\n    memory: 512Mi\n' > deploy.yaml
python run.py --input deploy.yaml --out out/result.json
```

**示例 2：只看合规分与结论**

```bash
python -c "import json;d=json.load(open('out/result.json',encoding='utf-8'));print(d['conclusion']);print(d['score'])"
```

**示例 3：管道输入 + 预览模式**

```bash
cat deploy.yaml | python run.py --out out/result.json
python run.py --input deploy.yaml --dry-run
```

**示例 4：作为库调用（接进发布流水线，有 ERROR 就拦）**

```python
import sys
sys.path.insert(0, "scripts")
import main

r = main.process(open("deploy.yaml", encoding="utf-8").read())
for f in r["suggested_fixes"]:
    print(f["level"], f["path"], "->", f["fix"])
if r["error_count"]:
    raise SystemExit("存在 ERROR 级配置问题，禁止发布")
```

## 常见问题

**Q1：我的配置是多层的，路径怎么表示？**
A：缩进两级算一层，路径点号连接。例如 `resources:` 下的 `cpu` 解析为 `app.resources.cpu`；列表项带下标，如 `containers[0].image`。

**Q2：`replicas: "2"`（带引号）会误判吗？**
A：不会。解析时先剥掉成对引号，判整型用全串匹配，`"2"` 与 `2` 结果一致。

**Q3：CPU 用 `500m` 这类毫核写法支持吗？**
A：支持。`500m` 换算为 0.5；超过 8 核会报 WARN 提示单机可调度风险。

**Q4：内存单位怎么判？**
A：支持 `Ki/Mi/Gi/K/M/G`，统一换算成 MiB。无法识别（例如只写 `512` 不带单位）报 ERROR；小于 64Mi 报 WARN。

**Q5：为什么有时会出现"（整个负载）"作为路径的违规项？**
A：那是结构规则，针对整份配置而不是单个键，例如未声明探针、未同时声明 CPU 与内存限额。

**Q6：解析不出任何配置项？**
A：返回 `{"ok": false, "error": "未解析到任何配置项"}` 并提示确认输入格式，退出码仍为 0。

## 输出说明

```json
{
  "ok": true,
  "conclusion": "合规分 64/100；ERROR 3 项、WARN 3 项，必须修复 ERROR 后才可发布",
  "score": 64,
  "error_count": 3,
  "warn_count": 3,
  "parsed_keys": 6,
  "parsed": {"app.replicas": "0", "app.image": "demo:latest"},
  "violations": [{"rule": "replicas-floor", "level": "ERROR", "path": "app.replicas",
                  "value": "0", "message": "副本数必须为 ≥1 的整数",
                  "fix": "把 replicas 调整为至少 1"}],
  "suggested_fixes": [{"level": "ERROR", "path": "app.replicas", "fix": "把 replicas 调整为至少 1"}],
  "report_md": "**合规分：64/100** ...",
  "next_action": "按建议清单逐条修正 ERROR 项后重跑校验",
  "content_id": "9a2f31c07e55"
}
```

失败时：

```json
{"ok": false, "error": "未解析到任何配置项"}
```

## 许可证

MIT License。可自由用于商业与非商业场景，保留版权声明即可。
