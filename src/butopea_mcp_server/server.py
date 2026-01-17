"""
Butopea MCP Server - Main Entry Point
Simplified MCP server with generic Odoo tools.
"""
import asyncio
import logging
import os
import json
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .odoo_client import OdooClient

# Load environment variables
load_dotenv()

# Configure logging to file (stderr can interfere with MCP stdio protocol)
log_file = '/tmp/butopea-mcp-server.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file)]
)
_logger = logging.getLogger(__name__)
_logger.info("Starting butopea-mcp-server")

# Initialize MCP server
server = Server("butopea-odoo")

# Global Odoo client
odoo_client: OdooClient | None = None


def get_odoo_config() -> dict[str, str]:
    """Get Odoo configuration from environment."""
    return {
        'url': os.getenv('ODOO_URL', 'http://localhost:8069'),
        'database': os.getenv('ODOO_DB', 'odoo'),
        'username': os.getenv('ODOO_USERNAME', ''),
        'password': os.getenv('ODOO_PASSWORD', ''),
        'api_key': os.getenv('ODOO_API_KEY', ''),
        'preferred_lang': os.getenv('PREFERRED_LANG', 'en_US'),
    }


async def initialize_odoo():
    """Initialize Odoo client (graceful - no exceptions)."""
    global odoo_client
    
    config = get_odoo_config()
    odoo_client = OdooClient(
        url=config['url'],
        database=config['database'],
        username=config['username'],
        password=config['password'],
        api_key=config['api_key'],
        preferred_lang=config['preferred_lang'],
    )
    
    try:
        if not await odoo_client.authenticate():
            _logger.warning("Could not authenticate with Odoo - use odoo_reconnect")
            return False
        _logger.info("Connected to Odoo as uid=%s", odoo_client.uid)
        return True
    except Exception as e:
        _logger.warning("Odoo not available: %s", e)
        return False


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    Generic Odoo tools - simplified, model as parameter.
    Only 8 tools instead of per-model tools.
    """
    return [
        # Connection management
        Tool(
            name="odoo_reconnect",
            description="Reconnect to Odoo server. Use this if Odoo was started after the MCP server, or if connection was lost.",
            inputSchema={"type": "object", "properties": {}},
        ),
        
        # Discovery
        Tool(
            name="odoo_capabilities",
            description="Get list of accessible menus and models for the current user. Use this first to understand what you can access.",
            inputSchema={"type": "object", "properties": {}},
        ),
        
        # 🔍 Search records
        Tool(
            name="odoo_search",
            description="Search for records in any Odoo model. Supports filtering, field selection, pagination, and sorting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name (e.g., 'res.partner', 'sale.order')"},
                    "domain": {"type": "array", "description": "Odoo domain filter, e.g. [['state', '=', 'draft']]", "items": {"type": "array"}},
                    "fields": {"type": "array", "description": "Field names to return. Omit for smart defaults.", "items": {"type": "string"}},
                    "limit": {"type": "integer", "description": "Max records (default 20, max 100)", "default": 20},
                    "offset": {"type": "integer", "description": "Pagination offset", "default": 0},
                    "order": {"type": "string", "description": "Sort order, e.g. 'name asc' or 'create_date desc'"},
                },
                "required": ["model"],
            },
        ),
        
        # 📊 Read single record
        Tool(
            name="odoo_read",
            description="Read a specific record by ID with detailed field values.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name"},
                    "id": {"type": "integer", "description": "Record ID"},
                    "fields": {"type": "array", "description": "Field names to return", "items": {"type": "string"}},
                },
                "required": ["model", "id"],
            },
        ),
        
        # 🔢 Count records
        Tool(
            name="odoo_count",
            description="Count records matching a domain filter. Use for statistics without fetching data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name"},
                    "domain": {"type": "array", "description": "Odoo domain filter", "items": {"type": "array"}},
                },
                "required": ["model"],
            },
        ),
        
        # ✨ Create record
        Tool(
            name="odoo_create",
            description="Create a new record in any Odoo model. Respects field validation and permissions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name"},
                    "values": {"type": "object", "description": "Field values for the new record"},
                },
                "required": ["model", "values"],
            },
        ),
        
        # ✏️ Update record
        Tool(
            name="odoo_update",
            description="Update an existing record. Respects field validation and permissions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name"},
                    "id": {"type": "integer", "description": "Record ID to update"},
                    "values": {"type": "object", "description": "Field values to update"},
                },
                "required": ["model", "id", "values"],
            },
        ),
        
        # 🗑️ Delete record
        Tool(
            name="odoo_delete",
            description="Delete a record. Respects model-level permissions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name"},
                    "id": {"type": "integer", "description": "Record ID to delete"},
                },
                "required": ["model", "id"],
            },
        ),
        
        # 📋 Schema/fields
        Tool(
            name="odoo_schema",
            description="Get field definitions for a model. Use to understand data structure before creating/updating.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name"},
                    "view_type": {"type": "string", "enum": ["form", "tree", "search"], "default": "form"},
                },
                "required": ["model"],
            },
        ),
        
        # 🎯 Execute method
        Tool(
            name="odoo_execute",
            description="Execute a method/button action on an Odoo model. Use for actions like 'action_confirm', 'action_cancel', etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name (e.g., 'sale.order')"},
                    "method": {"type": "string", "description": "Method name to call (e.g., 'action_confirm')"},
                    "ids": {"type": "array", "description": "Record IDs to execute on", "items": {"type": "integer"}},
                    "args": {"type": "array", "description": "Positional arguments"},
                    "kwargs": {"type": "object", "description": "Keyword arguments"},
                },
                "required": ["model", "method"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    global odoo_client
    
    try:
        # Reconnect (always available)
        if name == "odoo_reconnect":
            success = await initialize_odoo()
            if success:
                return [TextContent(type="text", text=f"✅ Connected to Odoo as uid={odoo_client.uid}")]
            else:
                return [TextContent(type="text", text="❌ Failed to connect. Check if Odoo is running.")]
        
        # Check connection
        if odoo_client is None or odoo_client.uid is None:
            return [TextContent(type="text", text="❌ Not connected to Odoo. Use odoo_reconnect first.")]
        
        # Capabilities
        if name == "odoo_capabilities":
            result = await odoo_client.get_capabilities()
            return [TextContent(type="text", text=format_result(result))]
        
        # Search
        if name == "odoo_search":
            result = await odoo_client.search(
                model=arguments['model'],
                domain=arguments.get('domain', []),
                fields=arguments.get('fields'),
                limit=min(arguments.get('limit', 20), 100),  # Cap at 100
                offset=arguments.get('offset', 0),
                order=arguments.get('order'),
            )
            return [TextContent(type="text", text=format_result(result))]
        
        # Read single record
        if name == "odoo_read":
            result = await odoo_client.search(
                model=arguments['model'],
                domain=[['id', '=', arguments['id']]],
                fields=arguments.get('fields'),
                limit=1,
            )
            if result.get('records'):
                return [TextContent(type="text", text=format_result(result['records'][0]))]
            return [TextContent(type="text", text=f"❌ Record not found: {arguments['model']} ID {arguments['id']}")]
        
        # Count
        if name == "odoo_count":
            result = await odoo_client.execute(
                model=arguments['model'],
                method='search_count',
                args=[arguments.get('domain', [])],
            )
            return [TextContent(type="text", text=f"Count: {result.get('result', 0)}")]
        
        # Create
        if name == "odoo_create":
            result = await odoo_client.execute(
                model=arguments['model'],
                method='create',
                values=arguments['values'],
            )
            return [TextContent(type="text", text=format_result(result))]
        
        # Update
        if name == "odoo_update":
            result = await odoo_client.execute(
                model=arguments['model'],
                method='write',
                ids=[arguments['id']],
                values=arguments['values'],
            )
            return [TextContent(type="text", text=format_result(result))]
        
        # Delete
        if name == "odoo_delete":
            result = await odoo_client.execute(
                model=arguments['model'],
                method='unlink',
                ids=[arguments['id']],
            )
            return [TextContent(type="text", text=format_result(result))]
        
        # Schema
        if name == "odoo_schema":
            result = await odoo_client.get_model_schema(
                model=arguments['model'],
                view_type=arguments.get('view_type', 'form'),
            )
            return [TextContent(type="text", text=format_result(result))]
        
        # Execute method
        if name == "odoo_execute":
            result = await odoo_client.execute(
                model=arguments['model'],
                method=arguments['method'],
                ids=arguments.get('ids'),
                args=arguments.get('args'),
                kwargs=arguments.get('kwargs'),
            )
            return [TextContent(type="text", text=format_result(result))]
        
        return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]
    
    except Exception as e:
        _logger.exception("Error calling tool %s", name)
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


def format_result(result: dict | list | Any) -> str:
    """Format result for LLM-friendly output."""
    return json.dumps(result, indent=2, default=str, ensure_ascii=False)


async def run():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        # Try to connect to Odoo at startup
        try:
            await initialize_odoo()
        except Exception as e:
            _logger.warning("Failed to initialize Odoo at startup: %s", e)
        
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Entry point."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
