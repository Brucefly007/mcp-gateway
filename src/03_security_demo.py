"""步骤 3：故意踩边界——这些请求应该被拒绝（面试高频）。"""
from __future__ import annotations

import json

from mcp_core import handle_jsonrpc


ATTACKS = [
    ("写库", {"name": "mysql_query", "arguments": {"sql": "UPDATE orders SET status='hacked'"}}),
    ("内网 SSRF", {"name": "http_get", "arguments": {"url": "http://127.0.0.1:8080/admin"}}),
    ("非白名单域名", {"name": "http_get", "arguments": {"url": "https://evil.example.net/x"}}),
    ("路径穿越", {"name": "search_files", "arguments": {"query": "secret", "root": "../../Windows"}}),
]


def main() -> None:
    print("下面四次调用都应当失败，并写入 演示/audit.log\n")
    for title, params in ATTACKS:
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
        resp = handle_jsonrpc(req)
        text = resp["result"]["content"][0]["text"]
        err = resp["result"].get("isError")
        print(f"[{title}] isError={err}")
        print(f"  → {text}\n")
    print("口述提示：MCP 不管权限；SELECT-only、白名单、目录沙箱、审计日志是我自己加的。")


if __name__ == "__main__":
    main()
