# SkillForge Originals — 原创资产池

本仓库为 **SkillForge Lab** 原创能力资产的公开落证仓库，用于证明资产的原创性与时间归属。

## 同步说明

- 同步时间：2026-10-18T21:12:06+08:00
- 资产数量：847
- 生成方式：规格驱动 clean-room 原创（非代码抓取）
- 版权归属：SkillForge Lab（唯一法定主体）
- 许可：MIT

## 目录结构

```
<slug>/
  SKILL.md                      能力说明（含合规 frontmatter）
  config.json                   规则表（when/then）
  capability.json               能力契约
  agent-card.json               A2A 名片
  .well-known/agent-card.json   A2A 标准发现路径
  a2a/server.py                 A2A 服务端点
  skills/<name>/SKILL.md        分层技能文档
  skills/<name>/references/     知识分层（四分区）
  skills/<name>/scripts/main.py 实现
  skills/<name>/.phoenix/       原创证据链（merkle）
  avatars/                      头像资产
```

## 原创性说明

每个资产含 `.phoenix/provenance.json`（来源与生成方式）与
`.phoenix/evidence.json`（全文件 merkle 根，可验证内容未被篡改）。

---

© 2026 SkillForge Lab. 本仓库内容采用 MIT 许可。
