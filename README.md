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
| ✨ **Create** | Create new records with field validation (requires confirmation) |
| ✏️ **Update** | Update existing records (requires confirmation) |
| 🗑️ **Delete** | Delete records respecting permissions (requires confirmation) |
| 🔢 **Count** | Count records matching criteria |
| 📋 **Schema** | Inspect model fields to understand data structure |
| 🎯 **Execute** | Trigger button actions (requires confirmation for state-changing methods) |
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

## 🛡️ Confirmation Flow

To prevent accidental data modifications, **all write operations require explicit user confirmation**:

### AI-Driven Confirmation Workflow

The MCP server uses **tool descriptions** to instruct AI agents to request user approval before executing destructive operations. This ensures a human-in-the-loop for all database modifications.

### How It Works

1. **User makes a request** (e.g., "Confirm order S156460")
2. **AI identifies the operation** and finds the relevant record
3. **AI asks for confirmation** showing exactly what will happen
4. **User approves** with a simple "yes" or similar response
5. **AI executes** the operation only after approval

### Example: Confirming a Sale Order

```
User: "Confirm order S156460"

AI: I found order S156460 - it's in draft state, which means it can be confirmed.
    Here are the details:
    • Order: S156460
    • Customer: Zoltán Mészáros
    • Amount: €46,990.00
    • State: Draft (ready to confirm)
    
    Should I proceed with confirming this order? This will:
    - Change the state from "draft" to "sale"
    - Generate delivery orders if applicable
    - Reserve inventory
    - Lock the order for editing

User: "yes"

AI: [Executes odoo_execute(model="sale.order", method="action_confirm", ids=[226959])]
    ✅ Order S156460 has been successfully confirmed!
```

### Operations Requiring Confirmation

| Operation | Confirmation Required | What AI Shows Before Executing |
|-----------|----------------------|-------------------------------|
| `odoo_create` | ✅ Always | Model, all field values being set |
| `odoo_update` | ✅ Always | Model, record ID, field changes |
| `odoo_delete` | ✅ Always | Model, record ID, record details, permanence warning |
| `odoo_execute` | ✅ Always | Model, method name, record IDs, what the method does |
| `odoo_search` | ❌ Never | Read-only operation |
| `odoo_read` | ❌ Never | Read-only operation |
| `odoo_count` | ❌ Never | Read-only operation |


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
