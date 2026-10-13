"""
教学用 MCP 核心：JSON-RPC 形状对齐官方 tools/list、tools/call。
零第三方依赖。数据源是内存假库 + 本地文件，边界逻辑与简历一致。
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
AUDIT_LOG = ROOT / "演示" / "audit.log"

# 简历同款：假 MySQL（仅演示 SELECT + LIMIT）
FAKE_DB = {
    "orders": [
        {"id": 1001, "sku": "BAG-A01", "status": "已发货", "city": "保定"},
        {"id": 1002, "sku": "BAG-B12", "status": "待发货", "city": "石家庄"},
        {"id": 1003, "sku": "BAG-A01", "status": "已签收", "city": "北京"},
    ],
    "products": [
        {"sku": "BAG-A01", "name": "头层牛皮托特包", "stock": 42},
        {"sku": "BAG-B12", "name": "牛津布双肩包", "stock": 18},
    ],
}

HTTP_ALLOWLIST = {"example.com", "httpbin.org", "api.github.com"}


@dataclass
class ToolResult:
    ok: bool
    content: str
    meta: dict[str, Any] = field(default_factory=dict)


def _audit(event: str, detail: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **detail,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def tool_mysql_query(sql: str) -> ToolResult:
    """仅允许 SELECT；自动补 LIMIT 50。"""
    cleaned = " ".join(sql.strip().split())
    if not re.match(r"(?i)^select\b", cleaned):
        _audit("mysql_denied", {"sql": cleaned, "reason": "not_select"})
        return ToolResult(False, "拒绝：只允许 SELECT 只读查询。")
    if re.search(r"(?i)\b(insert|update|delete|drop|alter|truncate|attach)\b", cleaned):
        _audit("mysql_denied", {"sql": cleaned, "reason": "dangerous_keyword"})
        return ToolResult(False, "拒绝：检测到写/DDL 关键字。")
    if not re.search(r"(?i)\blimit\b", cleaned):
        cleaned = cleaned.rstrip(";") + " LIMIT 50"
        auto_limit = True
    else:
        auto_limit = False

    # 极简解析：FROM <table>
    m = re.search(r"(?i)\bfrom\s+([a-zA-Z_][\w]*)", cleaned)
    if not m:
        return ToolResult(False, "无法解析表名。示例：SELECT * FROM orders")
    table = m.group(1).lower()
    if table not in FAKE_DB:
        return ToolResult(False, f"表不存在：{table}。可用：{', '.join(FAKE_DB)}")
    rows = FAKE_DB[table]
    lim = 50
    lm = re.search(r"(?i)\blimit\s+(\d+)", cleaned)
    if lm:
        lim = min(int(lm.group(1)), 50)
    rows = rows[:lim]
    _audit("mysql_ok", {"sql": cleaned, "rows": len(rows), "auto_limit": auto_limit})
    return ToolResult(True, json.dumps(rows, ensure_ascii=False, indent=2), {"auto_limit": auto_limit})


def tool_http_get(url: str) -> ToolResult:
    """域名白名单，防 SSRF。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return ToolResult(False, "URL 无法解析。")
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"}:
        _audit("http_denied", {"url": url, "reason": "scheme"})
        return ToolResult(False, "拒绝：仅允许 http/https。")
    if host in {"localhost", "127.0.0.1", "0.0.0.0"} or host.startswith("10.") or host.startswith("192.168."):
        _audit("http_denied", {"url": url, "reason": "private_host"})
        return ToolResult(False, "拒绝：禁止访问内网/本机（SSRF 防护）。")
    if host not in HTTP_ALLOWLIST:
        _audit("http_denied", {"url": url, "reason": "not_allowlisted", "host": host})
        return ToolResult(False, f"拒绝：域名不在白名单。允许：{sorted(HTTP_ALLOWLIST)}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mcp-demo/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read(2000).decode("utf-8", errors="replace")
        _audit("http_ok", {"url": url, "bytes": len(body)})
        return ToolResult(True, body[:1500] + ("…" if len(body) > 1500 else ""))
    except urllib.error.HTTPError as e:
        _audit("http_error", {"url": url, "code": e.code})
        return ToolResult(False, f"HTTP {e.code}")
    except Exception as e:
        _audit("http_error", {"url": url, "error": str(e)})
        return ToolResult(False, f"请求失败：{e}")


def tool_search_files(query: str, root: str | None = None) -> ToolResult:
    """检索限定在 DATA_DIR（或显式子路径且不得越出）。"""
    base = DATA_DIR.resolve()
    target = base
    if root:
        normalized = root.replace("\\", "/")
        parts = Path(normalized).parts
        if normalized.startswith("/") or ".." in parts:
            _audit("search_denied", {"root": root, "reason": "path_escape"})
            return ToolResult(False, "拒绝：路径越出允许目录。")
        candidate = (base / normalized).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            _audit("search_denied", {"root": root, "reason": "path_escape"})
            return ToolResult(False, "拒绝：路径越出允许目录。")
        target = candidate
    q = query.strip().lower()
    if not q:
        return ToolResult(False, "query 不能为空。")
    hits: list[str] = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if q in text.lower() or q in path.name.lower():
            # 取含关键词的一行
            line = next((ln.strip() for ln in text.splitlines() if q in ln.lower()), path.name)
            hits.append(f"{path.relative_to(base)}: {line[:120]}")
        if len(hits) >= 10:
            break
    _audit("search_ok", {"query": query, "hits": len(hits)})
    if not hits:
        return ToolResult(True, "无命中。")
    return ToolResult(True, "\n".join(hits))


TOOLS: dict[str, dict[str, Any]] = {
    "mysql_query": {
        "name": "mysql_query",
        "description": "只读查询假库 orders/products。仅 SELECT，自动 LIMIT。",
        "inputSchema": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "SQL，例如 SELECT * FROM orders"}},
            "required": ["sql"],
        },
        "handler": tool_mysql_query,
        "arg": "sql",
    },
    "http_get": {
        "name": "http_get",
        "description": "对白名单域名发起 GET（防 SSRF）。",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        "handler": tool_http_get,
        "arg": "url",
    },
    "search_files": {
        "name": "search_files",
        "description": "在 data/ 目录内按关键词检索文件，禁止路径穿越。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "root": {"type": "string", "description": "可选，data 下相对子路径"},
            },
            "required": ["query"],
        },
        "handler": tool_search_files,
        "arg": None,
    },
}


def list_tools_payload() -> dict[str, Any]:
    tools = []
    for t in TOOLS.values():
        tools.append(
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
        )
    return {"tools": tools}


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    arguments = arguments or {}
    if name not in TOOLS:
        return {
            "content": [{"type": "text", "text": f"未知工具：{name}"}],
            "isError": True,
        }
    spec = TOOLS[name]
    handler: Callable[..., ToolResult] = spec["handler"]
    try:
        if name == "search_files":
            result = handler(arguments.get("query", ""), arguments.get("root"))
        else:
            key = spec["arg"]
            result = handler(arguments.get(key, ""))
    except Exception as e:
        _audit("tool_exception", {"name": name, "error": str(e)})
        return {"content": [{"type": "text", "text": f"工具异常：{e}"}], "isError": True}
    return {
        "content": [{"type": "text", "text": result.content}],
        "isError": not result.ok,
        "_meta": result.meta,
    }


def handle_jsonrpc(msg: dict[str, Any]) -> dict[str, Any] | None:
    """处理单条 JSON-RPC 请求，返回响应；通知则返回 None。"""
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "bag-mcp-demo", "version": "0.1.0"},
        }
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        result = list_tools_payload()
    elif method == "tools/call":
        result = call_tool(params.get("name", ""), params.get("arguments"))
    elif method == "ping":
        result = {}
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    if req_id is None:
        return None
    return {"jsonrpc": "2.0", "id": req_id, "result": result}
