"""步骤 2：模拟 Agent 连续调用三个工具。"""
from __future__ import annotations

import json

from mcp_core import handle_jsonrpc


CASES = [
    {
        "name": "mysql_query",
        "arguments": {"sql": "SELECT * FROM orders"},
    },
    {
        "name": "search_files",
        "arguments": {"query": "七天无理由"},
    },
    {
        "name": "http_get",
        "arguments": {"url": "https://example.com"},
    },
]


def main() -> None:
    for i, args in enumerate(CASES, start=1):
        req = {
            "jsonrpc": "2.0",
            "id": i,
            "method": "tools/call",
            "params": args,
        }
        resp = handle_jsonrpc(req)
        print(f"\n===== 调用 {i}: {args['name']} =====")
        print(json.dumps(req, ensure_ascii=False, indent=2))
        print("--- 结果 ---")
        print(json.dumps(resp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
