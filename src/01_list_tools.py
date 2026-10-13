"""步骤 1：看 Agent 启动时会拿到的 tools/list。"""
from __future__ import annotations

import json

from mcp_core import handle_jsonrpc


def main() -> None:
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    resp = handle_jsonrpc(req)
    print("=== 请求 ===")
    print(json.dumps(req, ensure_ascii=False, indent=2))
    print("\n=== 响应（Agent 看到的工具清单）===")
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    print("\n口述提示：MCP 把能力变成带 name / description / inputSchema 的标准工具。")


if __name__ == "__main__":
    main()
