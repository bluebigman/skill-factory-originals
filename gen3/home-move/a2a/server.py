# -*- coding: utf-8 -*-
"""a2a/server.py — A2A 服务端点（JSON-RPC 2.0，纯标准库）

★ 只做三件事：暴露能力名片、接收任务、返回结构化结果。
★ 不依赖任何三方包（F06-05 Q4 要求）。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CARD = os.path.join(os.path.dirname(HERE), "agent-card.json")


def load_card():
    with open(CARD, encoding="utf-8") as f:
        return json.load(f)


def handle(req):
    """处理一条 JSON-RPC 请求，返回响应 dict"""
    mid = req.get("id")
    method = req.get("method")
    if method == "agent/getCard":
        return {"jsonrpc": "2.0", "id": mid, "result": load_card()}
    if method == "skills/list":
        card = load_card()
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"skills": card.get("skills") or []}}
    if method == "tasks/send":
        params = req.get("params") or {}
        text = str(params.get("input") or "")
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"status": "received", "echo_len": len(text),
                           "skills": [s.get("id") for s in
                                      (load_card().get("skills") or [])]}}
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": "method not found"}}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="a2a-server")
    ap.add_argument("--card-only", action="store_true",
                    help="只打印能力名片（不启服务）")
    ap.add_argument("--port", type=int, default=8931)
    a = ap.parse_args(argv)
    if a.card_only:
        print(json.dumps(load_card(), ensure_ascii=False, indent=1))
        return 0
    print("A2A server ready (port %d). card=%s" % (a.port, CARD))
    print("本端点以库方式提供 handle(); 生产环境由网关调用。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
