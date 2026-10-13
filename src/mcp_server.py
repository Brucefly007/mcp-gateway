"""
stdio MCP Server：从 stdin 读一行一条 JSON-RPC，写到 stdout。
日常演示用 01/02/03 脚本；本文件用于理解真实传输形态。
"""
from __future__ import annotations

import json
import sys

from mcp_core import handle_jsonrpc


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue
        resp = handle_jsonrpc(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
