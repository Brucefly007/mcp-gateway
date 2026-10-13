# MCP 工具网关 · 教学可跑版

MCP 工具网关的 **教学可跑版**：用与官方一致的 JSON-RPC 形状（`tools/list` / `tools/call`）暴露只读 SQL、HTTP GET、文件检索三类工具，并演示自建安全边界（SELECT-only、域名白名单防 SSRF、目录沙箱、审计日志）。

> **重要说明（请先读）**  
> 这是「**教学可跑版**」，不是完整生产栈。  
> - **本仓库**：内存假库 + 本地 `data/` 文件 + 标准库 HTTP；零第三方依赖即可跑通协议与边界。  
> - **生产环境**：真 **MySQL**、真实 HTTP 业务接口、可扩展为更多工具、stdio / SSE 接入 Cursor、Claude Desktop 与自研 Agent。  
> - **不变的部分**：MCP 消息形状、工具封装方式、**安全边界逻辑**——协议与边界和线上一致，换数据源即可。

## 环境

- Python **3.10+**
- **零第三方依赖**（系统自带标准库即可）
- 接入真实 Cursor / Claude Desktop 时可再使用官方 MCP SDK；本仓库已对齐协议形状

## 快速跑通

```bash
git clone https://github.com/Brucefly007/mcp-gateway.git
cd mcp-gateway

python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt   # 教学版可为空依赖

python src/01_list_tools.py
python src/02_call_tools_demo.py
python src/03_security_demo.py
```

想看真正的 **stdio Server** 进程（从 stdin 读 JSON-RPC）：

```bash
python src/mcp_server.py
```

日常演示用前面三个脚本即可。

### 脚本说明

1. **`01_list_tools.py`** — 打印 Agent 启动时会拿到的工具清单。  
2. **`02_call_tools_demo.py`** — 连续调用 mysql_query / search_files / http_get。  
3. **`03_security_demo.py`** — 故意写库、内网 SSRF、非白名单域名、路径穿越——均应被拒绝并记审计。  

## 目录结构

```
mcp-gateway/
├── README.md
├── LICENSE
├── requirements.txt
├── data/notes.md           # 文件检索样例
├── src/
│   ├── mcp_core.py         # 工具实现 + JSON-RPC 处理 + 安全边界
│   ├── mcp_server.py       # stdio 传输
│   ├── 01_list_tools.py
│   ├── 02_call_tools_demo.py
│   └── 03_security_demo.py
└── 演示/                   # 可选截图；audit.log 运行时生成（已 gitignore）
```

## 安全边界一览

| 工具 | 边界 |
|------|------|
| `mysql_query` | 仅 `SELECT`；拦截写/DDL 关键字；无 `LIMIT` 时自动补 `LIMIT 50` |
| `http_get` | 仅 http/https；拒绝 localhost / 私网；域名必须在白名单 |
| `search_files` | 根目录锁死在 `data/`；拒绝 `..` 与绝对路径穿越 |

审计事件追加写入 `演示/audit.log`。

## License

MIT © Brucefly007
