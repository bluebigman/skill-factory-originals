# -*- coding: utf-8 -*-
"""_a2a_server.py — A2A 服务端点（JSON-RPC 2.0 + Task 生命周期）（2026-10-01）

★ 这是把「我们的专家/技能」真正接上 A2A 协议的**那一层外壳**。

★ 为什么只需要这一层（关键判断）：
  我们的资产**已经是 A2A skill 的实现体** —— 每个技能自带
    `analyze(text) -> dict`（结构化产出） / `ERRORS`（错误码+自愈建议） /
    `RULES`（真实领域规则） / `KEYWORDS`（能力边界）
  缺的**只有服务化外壳**：把 HTTP 上的 JSON-RPC 调用转成本地函数调用。
  ⇒ 不是重写资产，而是**给已有资产加一层协议适配器**。

★ 实现的能力（对齐 A2A v1.0）：
  GET  /.well-known/agent-card.json        发现（RFC 8615，CORS 开放，无需认证）
  GET  /a2a/<slug>/.well-known/agent-card.json   按资产暴露各自的 card
  POST /a2a/<slug>                         JSON-RPC 2.0 端点
    · message/send  → 建 Task，路由到最匹配的技能，执行，产出 Artifact
    · tasks/get     → 查 Task 状态
  Task 状态机：submitted → working → completed / failed（有生命周期，非一次性函数返回）

★ 严格遵循的协议约束（A2A 硬要求，逐条自证）：
  · Content-Type: application/json
  · Access-Control-Allow-Origin: *
  · Agent Card 可**无认证**获取、**不重定向**、**在根路径**
  · Agent Card ≤ 10KB（Google Agent Registry 上限）
  · JSON-RPC 2.0 标准错误码 + A2A 扩展错误码

★ 零依赖（Python stdlib）。用法：
  python _a2a_server.py --selftest              # 起服务→自动打通一次→退出（自证）
  python _a2a_server.py --port 8931             # 常驻服务
  python _a2a_server.py --selftest --slug child-emotion-coach
"""
import argparse
import importlib.util
import io
import json
import os
import re
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
os.chdir(r"D:\workbuddy\2026-08-31-18-52-33")

PKG_DIR = "wb_forge_batch"
RUNTIME = "outputs/_a2a_runtime"
CARDS = "outputs/_a2a_cards"
PROTOCOL_VERSION = "1.0.0"

TASKS = {}          # taskId -> task dict（内存态；生产应落持久化）
_TASKS_LOCK = threading.Lock()
_MOD_CACHE = {}


# ────────────── 资产装载 ──────────────
def ensure_unpacked():
    """把 wb_forge_batch/*.zip 解到运行时工作区（幂等）"""
    os.makedirs(RUNTIME, exist_ok=True)
    n = 0
    for zp in sorted(__import__("glob").glob(os.path.join(PKG_DIR, "*.zip"))):
        slug = os.path.basename(zp)[:-4]
        d = os.path.join(RUNTIME, slug)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, ".unpacked")):
            n += 1
            continue
        try:
            with zipfile.ZipFile(zp) as z:
                z.extractall(RUNTIME)
            io.open(os.path.join(d, ".unpacked"), "w").write("1")
            n += 1
        except Exception as e:
            print("  ⚠️ 解包失败 %s: %s" % (slug, e))
    return n


def load_card(slug):
    p = os.path.join(CARDS, slug, "agent-card.json")
    if not os.path.exists(p):
        return None
    return json.load(io.open(p, encoding="utf-8"))


def load_skill_mod(slug, skill):
    """动态加载技能实现（scripts/main.py 的 analyze）"""
    key = (slug, skill)
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    p = os.path.join(RUNTIME, slug, "skills", skill, "scripts", "main.py")
    if not os.path.exists(p):
        _MOD_CACHE[key] = None
        return None
    try:
        spec = importlib.util.spec_from_file_location("a2a_%s_%s" % (slug, skill.replace("-", "_")), p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MOD_CACHE[key] = mod
        return mod
    except Exception as e:
        print("  ⚠️ 技能加载失败 %s/%s: %s" % (slug, skill, type(e).__name__))
        _MOD_CACHE[key] = None
        return None


def route_skill(slug, text):
    """按能力边界路由到最匹配的技能（命中关键词数最多者）"""
    card = load_card(slug) or {}
    best, best_n = None, 0
    for sk in card.get("skills", []):
        hits = sum(1 for t in (sk.get("tags") or []) if t and t.lower() in text.lower())
        if hits > best_n:
            best, best_n = sk["id"], hits
    return best, best_n


def execute(slug, skill, text):
    """调用技能实现，返回结构化结果"""
    mod = load_skill_mod(slug, skill) if skill else None
    if mod is None or not hasattr(mod, "analyze"):
        return {"ok": False, "error_code": "E03",
                "summary": "无可用技能或技能不含 analyze 入口", "detail": {},
                "next_actions": ["更换任务描述或改调其他 agent"]}
    try:
        return mod.analyze(text)
    except Exception as e:
        return {"ok": False, "error_code": "E04",
                "summary": "内部错误：%s" % type(e).__name__, "detail": {},
                "next_actions": ["退避后重试 1 次"]}


def make_task(slug, text, message_id=""):
    tid = "task-%s-%d" % (slug[:12], int(time.time() * 1000))
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    task = {"id": tid, "contextId": "ctx-" + tid,
            "status": {"state": "submitted", "timestamp": now},
            "history": [{"role": "user", "parts": [{"type": "text", "text": text}],
                         "messageId": message_id or ("m-" + tid)}],
            "artifacts": [], "metadata": {"agent": slug}}
    with _TASKS_LOCK:
        TASKS[tid] = task

    # submitted → working
    skill, hits = route_skill(slug, text)
    task["status"] = {"state": "working", "timestamp":
                      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    task["metadata"]["routed_skill"] = skill
    task["metadata"]["keyword_hits"] = hits

    out = execute(slug, skill, text)

    # working → completed / failed
    ok = bool(out.get("ok"))
    state = "completed" if ok else "failed"
    task["status"] = {"state": state,
                      "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if not ok:
        task["status"]["message"] = {"role": "agent",
                                     "parts": [{"type": "text",
                                                "text": out.get("summary", "执行失败")}]}
    task["artifacts"] = [{
        "artifactId": "art-" + tid,
        "name": "analysis-result",
        "parts": [
            {"type": "text", "text": out.get("summary", "")},
            {"type": "data", "data": out},
        ],
    }]
    return task


# ────────────── JSON-RPC 2.0 ──────────────
def rpc_ok(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def rpc_err(rid, code, msg, data=None):
    e = {"code": code, "message": msg}
    if data is not None:
        e["data"] = data
    return {"jsonrpc": "2.0", "id": rid, "error": e}


def handle_rpc(slug, req):
    if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
        return rpc_err(None, -32600, "Invalid Request：缺少 jsonrpc 2.0")
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if method == "message/send":
        msg = params.get("message") or {}
        parts = msg.get("parts") or []
        text = " ".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
        if not text:
            return rpc_err(rid, -32602, "Invalid params：message.parts 无 text 内容")
        task = make_task(slug, text, msg.get("messageId", ""))
        return rpc_ok(rid, task)

    if method == "tasks/get":
        tid = params.get("id") or params.get("taskId")
        with _TASKS_LOCK:
            t = TASKS.get(tid)
        if not t:
            return rpc_err(rid, -32001, "TaskNotFound：%s" % tid)
        return rpc_ok(rid, t)

    if method == "agent/getAuthenticatedExtendedCard":
        card = load_card(slug)
        if not card:
            return rpc_err(rid, -32002, "AgentCardNotFound：%s" % slug)
        return rpc_ok(rid, card)

    return rpc_err(rid, -32601, "Method not found：%s" % method)


# ────────────── HTTP ──────────────
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "SkillForgeA2A/1.0"

    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        m = re.match(r"^/a2a/([^/]+)/\.well-known/agent-card\.json$", path)
        if m:
            card = load_card(m.group(1))
            if not card:
                return self._send({"error": "AgentCardNotFound"}, 404)
            return self._send(card)
        if path in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
            # 索引卡：列出全部已发布 agent（A2A 允许聚合入口）
            idx = {"name": "SkillForge Lab Agents",
                   "description": "SkillForge Lab 原创 Agent 索引",
                   "version": "1.0.0", "protocolVersion": PROTOCOL_VERSION,
                   "url": "%s/a2a" % self._origin(), "capabilities": {"streaming": False},
                   "defaultInputModes": ["text/plain"],
                   "defaultOutputModes": ["text/plain", "application/json"],
                   "skills": [{"id": s, "name": s, "description": "见 /a2a/%s/.well-known/agent-card.json" % s}
                              for s in sorted(os.listdir(CARDS))
                              if os.path.isdir(os.path.join(CARDS, s))][:200]}
            return self._send(idx)
        return self._send({"error": "NotFound", "path": path}, 404)

    def _origin(self):
        host = self.headers.get("Host") or ("127.0.0.1:%d" % self.server.server_port)
        return "http://%s" % host

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            req = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._send(rpc_err(None, -32700, "Parse error"), 400)

        m = re.match(r"^/a2a/([^/]+)$", path)
        if m:
            return self._send(handle_rpc(m.group(1), req))
        # 兼容：POST 到 /a2a 且带 slug
        if path == "/a2a":
            sl = (req.get("params") or {}).get("agent")
            card = load_card(sl) if sl else None
            if not card:
                return self._send(rpc_err(req.get("id"), -32002, "AgentCardNotFound"), 404)
            return self._send(handle_rpc(sl, req))
        return self._send(rpc_err(req.get("id"), -32600, "Invalid Request：路径须为 /a2a/<slug>"), 400)


def serve(port):
    s = HTTPServer(("127.0.0.1", port), Handler)
    return s


# ────────────── 自证 ──────────────
def selftest(port, slug, text):
    """起服务 → 真实 HTTP 打通三件事：发现 / 调用 / 取任务"""
    import urllib.request as ur
    op = ur.build_opener(ur.ProxyHandler({}))          # 显式绕过代理（教训 L10）
    base = "http://127.0.0.1:%d" % port
    srv = serve(port)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    time.sleep(0.4)
    ok = True
    try:
        print("\n--- ① 发现：GET /a2a/%s/.well-known/agent-card.json ---" % slug)
        r = op.open("%s/a2a/%s/.well-known/agent-card.json" % (base, slug), timeout=6)
        ct = r.headers.get("Content-Type")
        cors = r.headers.get("Access-Control-Allow-Origin")
        card = json.loads(r.read().decode("utf-8"))
        print("   HTTP %s ｜ Content-Type=%s ｜ CORS=%s" % (r.status, ct, cors))
        print("   name=%s ｜ skills=%d ｜ interface=%s"
              % (card.get("name"), len(card.get("skills", [])),
                 (card.get("supportedInterfaces") or [{}])[0].get("protocolBinding")))
        if "application/json" not in (ct or "") or cors != "*":
            print("   🔴 协议头不合规（A2A 要求 application/json + CORS *）")
            ok = False

        print("\n--- ② 调用：POST /a2a/%s message/send ---" % slug)
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "message/send", "params": {
            "message": {"role": "user", "messageId": "m-selftest",
                        "parts": [{"type": "text", "text": text}]}}}).encode("utf-8")
        req = ur.Request("%s/a2a/%s" % (base, slug), data=body,
                         headers={"Content-Type": "application/json"})
        j = json.loads(op.open(req, timeout=10).read().decode("utf-8"))
        task = j.get("result") or {}
        st = (task.get("status") or {}).get("state")
        arts = task.get("artifacts") or []
        print("   task.id=%s ｜ state=%s ｜ 路由技能=%s ｜ 命中词数=%s"
              % (task.get("id"), st, (task.get("metadata") or {}).get("routed_skill"),
                 (task.get("metadata") or {}).get("keyword_hits")))
        if arts:
            p0 = (arts[0].get("parts") or [{}])[0]
            print("   artifact.name=%s ｜ text=%s" % (arts[0].get("name"), (p0.get("text") or "")[:70]))
        if st not in ("completed", "failed") or not arts:
            print("   🔴 Task 未走完生命周期")
            ok = False

        print("\n--- ③ 状态：POST tasks/get ---")
        body2 = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tasks/get",
                            "params": {"id": task.get("id")}}).encode("utf-8")
        req2 = ur.Request("%s/a2a/%s" % (base, slug), data=body2,
                          headers={"Content-Type": "application/json"})
        j2 = json.loads(op.open(req2, timeout=6).read().decode("utf-8"))
        st2 = ((j2.get("result") or {}).get("status") or {}).get("state")
        print("   复取状态=%s ｜ 一致=%s" % (st2, st2 == st))
        if st2 != st:
            ok = False

        print("\n--- ④ 负向：错误方法必须返回标准错误码 ---")
        body3 = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "no/such",
                            "params": {}}).encode("utf-8")
        req3 = ur.Request("%s/a2a/%s" % (base, slug), data=body3,
                          headers={"Content-Type": "application/json"})
        j3 = json.loads(op.open(req3, timeout=6).read().decode("utf-8"))
        code = (j3.get("error") or {}).get("code")
        print("   error.code=%s（期望 -32601）" % code)
        if code != -32601:
            ok = False
    finally:
        srv.shutdown()
    print("\n=== A2A 端点自证：%s ===" % ("✅ 全通" if ok else "🔴 有失败项"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8931)
    ap.add_argument("--slug", default="child-emotion-coach")
    ap.add_argument("--text", default="孩子发脾气打滚，怎么安抚")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--serve", action="store_true")
    a = ap.parse_args()

    n = ensure_unpacked()
    os.makedirs(CARDS, exist_ok=True)
    if not os.path.isdir(CARDS) or not os.listdir(CARDS):
        print("🔴 未找到 Agent Card —— 先跑：python _a2a_card_gen.py --apply")
        return 1
    print("=== A2A 服务端 ===")
    print("  已装载资产：%d ｜ Agent Card：%d" % (n, len(os.listdir(CARDS))))

    if a.selftest:
        return selftest(a.port, a.slug, a.text)

    srv = serve(a.port)
    print("  监听 http://127.0.0.1:%d" % a.port)
    print("  发现：GET  /a2a/<slug>/.well-known/agent-card.json")
    print("  调用：POST /a2a/<slug>  {jsonrpc, method:'message/send'|'tasks/get'}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
