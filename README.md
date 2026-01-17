# Butopea MCP Server for Odoo

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

An MCP (Model Context Protocol) server that enables AI assistants like Claude to interact with Odoo ERP. The AI operates with the exact same permissions and visibility as the authenticated user.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔐 **User POV** | AI sees exactly what the user can see (menus, records, fields) |
| 🔍 **Search** | Search and retrieve any Odoo record with smart pagination |
| 📊 **Read** | Get detailed record information |
| ✨ **Create** | Create new records with field validation |
| ✏️ **Update** | Update existing records |
| 🗑️ **Delete** | Delete records respecting permissions |
| 🔢 **Count** | Count records matching criteria |
| 📋 **Schema** | Inspect model fields to understand data structure |
| 🎯 **Execute** | Trigger button actions (confirm, cancel, etc.) |
| 🔄 **Reconnect** | Reconnect to Odoo without restarting |

## 🚀 Quick Start

### For AI Assistants (Claude, Antigravity, etc.)

Add to your MCP config file (`mcp_config.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "butopea-odoo": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/whynotkimhari/butopea-mcp-server.git", "butopea-mcp-server"],
      "env": {
        "ODOO_URL": "https://your-odoo-instance.com",
        "ODOO_DB": "your_database",
        "ODOO_USERNAME": "your_username",
        "ODOO_PASSWORD": "your_password"
      }
    }
  }
}
```

That's it! No manual installation required. `uvx` handles everything.

### For Development

```bash
# Clone the repository
git clone https://github.com/whynotkimhari/butopea-mcp-server.git
cd butopea-mcp-server

# Install with uv
uv sync

# Run
uv run butopea-mcp-server
```

## ⚙️ Configuration

All configuration is via environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `ODOO_URL` | Yes | Odoo instance URL (e.g., `https://odoo.company.com`) |
| `ODOO_DB` | Yes | Database name |
| `ODOO_USERNAME` | Yes* | Login username |
| `ODOO_PASSWORD` | Yes* | Login password |
| `ODOO_API_KEY` | Yes* | API key (alternative to username/password) |
| `PREFERRED_LANG` | No | Prefer language (Odoo-format: en_US, hu_HU, ...) |

*Either username/password OR api_key is required.

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `odoo_reconnect` | Reconnect to Odoo server |
| `odoo_capabilities` | Get accessible menus and models |
| `odoo_search` | Search records with filters |
| `odoo_read` | Read a single record by ID |
| `odoo_count` | Count records matching domain |
| `odoo_create` | Create a new record |
| `odoo_update` | Update an existing record |
| `odoo_delete` | Delete a record |
| `odoo_schema` | Get model field definitions |
| `odoo_execute` | Execute a method/action on records |

### Example Usage

```
User: "Find all draft sale orders"
AI uses: odoo_search(model="sale.order", domain=[["state", "=", "draft"]])

User: "Confirm order SO123"
AI uses: odoo_execute(model="sale.order", method="action_confirm", ids=[123])

User: "How many customers do we have?"
AI uses: odoo_count(model="res.partner", domain=[["customer_rank", ">", 0]])
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Assistant                             │
│                 (Claude, Antigravity, etc.)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ MCP Protocol (stdio)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Butopea MCP Server                           │
│                    (this project)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 10 Generic  │  │   Odoo      │  │   Session Management    │  │
│  │   Tools     │  │   Client    │  │   & Error Handling      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/JSON-RPC
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Odoo Instance                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              butopea_mcp Module                             ││
│  │  • /mcp/capabilities  - User's accessible menus/models      ││
│  │  • /mcp/search        - Search records                      ││
│  │  • /mcp/execute       - CRUD & method execution             ││
│  │  • /mcp/model/schema  - Field definitions                   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Odoo Module

The `butopea_mcp` Odoo module must be installed on your Odoo instance. Copy it to your addons path and install via Apps menu.

The module exposes secure JSON-RPC endpoints that respect user permissions.

## 🔒 Security

- All operations run under the authenticated user's permissions
- No elevated access or sudo operations
- Session-based authentication with automatic reconnection
- Passwords are passed via environment variables (not stored in files)

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please open an issue or pull request.
