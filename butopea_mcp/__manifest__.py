{
    'name': 'Butopea MCP Connector',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'API for Butopea MCP Server to interact with Odoo',
    'description': """
        Exposes endpoints for the MCP Server to:
        - Introspect user context (menus, allowed models)
        - Fetch model schemas (redacting invisible fields)
        - Execute actions on behalf of the user
    """,
    'author': 'Butopea',
    'website': 'https://www.butopea.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
