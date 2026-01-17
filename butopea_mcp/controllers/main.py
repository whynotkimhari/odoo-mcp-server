"""
Butopea MCP - Main Controller
Exposes endpoints for the MCP Server to interact with Odoo
under the current user's session context ("Session Mirror").
"""
from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class MCPController(http.Controller):
    """
    Main controller for MCP Server communication.
    All endpoints use auth='user' to ensure requests are made
    in the context of the authenticated user ("User POV").
    """

    def _get_env(self):
        """Get environment with context from request params (e.g., lang)."""
        try:
            params = request.get_json_data().get('params', {})
            ctx = params.get('context', {})
            if ctx:
                return request.env.with_context(**ctx)
        except Exception:
            pass
        return request.env

    # =========================================================================
    # CAPABILITIES - What can the current user access?
    # =========================================================================
    @http.route('/mcp/capabilities', type='json', auth='user', methods=['POST'])
    def get_capabilities(self):
        """
        Returns the list of accessible menus and models for the current user.
        This is the first call the MCP server makes to understand what tools
        to expose to the AI agent.
        """
        user = request.env.user
        _logger.info("MCP: Fetching capabilities for user %s", user.login)

        # Get accessible menus
        menus = self._get_accessible_menus()

        # Get accessible models (from menu actions)
        models = self._get_accessible_models(menus)

        return {
            'user': {
                'id': user.id,
                'name': user.name,
                'login': user.login,
            },
            'menus': menus,
            'models': models,
        }

    def _get_accessible_menus(self):
        """Fetches menus visible to the current user."""
        Menu = request.env['ir.ui.menu']
        # search() already filters based on user groups
        menus = Menu.search([])
        result = []
        for menu in menus:
            result.append({
                'id': menu.id,
                'name': menu.name,
                'parent_id': menu.parent_id.id if menu.parent_id else False,
                'action': menu.action.type if menu.action else False,
                'model': self._extract_model_from_action(menu.action) if menu.action else False,
            })
        return result

    def _extract_model_from_action(self, action):
        """Extracts the target model from a menu action."""
        if action and action._name == 'ir.actions.act_window':
            return action.res_model
        return False

    def _get_accessible_models(self, menus):
        """
        Returns unique models referenced by accessible menus.
        Includes basic metadata for each model.
        """
        model_names = set()
        for menu in menus:
            if menu.get('model'):
                model_names.add(menu['model'])

        IrModel = request.env['ir.model']
        result = []
        for model_name in model_names:
            try:
                # Check if user can at least read the model
                request.env[model_name].check_access_rights('read', raise_exception=True)
                ir_model = IrModel.search([('model', '=', model_name)], limit=1)
                if ir_model:
                    result.append({
                        'model': model_name,
                        'name': ir_model.name,
                        'description': ir_model.info or '',
                    })
            except Exception:
                # User cannot access this model, skip it
                pass

        return result

    # =========================================================================
    # SCHEMA - Get field definitions for a model
    # =========================================================================
    @http.route('/mcp/model/<string:model_name>/schema', type='json', auth='user', methods=['POST'])
    def get_model_schema(self, model_name, view_type='form', **kwargs):
        """
        Returns the schema for a specific model, respecting field visibility.
        Uses fields_view_get to get the actual view and extracts visible fields.
        
        Args:
            model_name: Technical model name (e.g., 'res.partner')
            view_type: Type of view to introspect ('form', 'tree', 'search')
        """
        _logger.info("MCP: Fetching schema for %s (view: %s)", model_name, view_type)

        try:
            env = self._get_env()
            Model = env[model_name]
            Model.check_access_rights('read', raise_exception=True)
        except Exception as e:
            return {'error': str(e), 'model': model_name}

        # Get the view definition
        try:
            view = Model.get_view(view_type=view_type)
        except Exception:
            view = {'fields': Model.fields_get()}

        # Get all field definitions
        all_fields = Model.fields_get()

        # Filter to only fields present in the view
        view_fields = view.get('fields', {})
        schema = {}
        for field_name, field_def in view_fields.items():
            if field_name in all_fields:
                full_def = all_fields[field_name]
                schema[field_name] = {
                    'type': full_def.get('type'),
                    'string': full_def.get('string'),
                    'required': full_def.get('required', False),
                    'readonly': full_def.get('readonly', False),
                    'selection': full_def.get('selection') if full_def.get('type') == 'selection' else None,
                    'relation': full_def.get('relation'),
                    'help': full_def.get('help'),
                }

        return {
            'model': model_name,
            'view_type': view_type,
            'fields': schema,
        }

    # =========================================================================
    # SEARCH / READ - Query records
    # =========================================================================
    @http.route('/mcp/search', type='json', auth='user', methods=['POST'])
    def search_records(self, model, domain=None, fields=None, limit=80, offset=0, order=None, **kwargs):
        """
        Search for records in a model.
        Security is automatically applied by Odoo's ORM.
        
        Args:
            model: Model name
            domain: Odoo domain filter
            fields: List of fields to return (None = all readable)
            limit: Max records to return
            offset: Pagination offset
            order: Sort order
        """
        domain = domain or []
        _logger.info("MCP: Searching %s with domain %s", model, domain)

        try:
            env = self._get_env()
            Model = env[model]
            Model.check_access_rights('read', raise_exception=True)
        except Exception as e:
            return {'error': str(e)}

        records = Model.search_read(
            domain=domain,
            fields=fields,
            limit=limit,
            offset=offset,
            order=order,
        )

        return {
            'model': model,
            'count': len(records),
            'records': records,
        }

    # =========================================================================
    # EXECUTE - Create, Write, Unlink, Call Methods
    # =========================================================================
    @http.route('/mcp/execute', type='json', auth='user', methods=['POST'])
    def execute_action(self, model, method, ids=None, args=None, kwargs=None, values=None, **kw):
        """
        Execute a method on a model or recordset.
        
        Supported operations:
        - create: method='create', values={...}
        - write: method='write', ids=[...], values={...}
        - unlink: method='unlink', ids=[...]
        - custom: method='<method_name>', ids=[...], args=[...], kwargs={...}
        """
        ids = ids or []
        args = args or []
        kwargs = kwargs or {}
        _logger.info("MCP: Executing %s.%s on ids %s", model, method, ids)

        try:
            env = self._get_env()
            Model = env[model]
        except Exception as e:
            return {'error': f'Model not found: {model}', 'details': str(e)}

        # Handle standard CRUD operations
        if method == 'create':
            if not values:
                return {'error': 'create requires values'}
            try:
                Model.check_access_rights('create', raise_exception=True)
                record = Model.create(values)
                return {'success': True, 'id': record.id}
            except Exception as e:
                return {'error': str(e)}

        elif method == 'write':
            if not ids or not values:
                return {'error': 'write requires ids and values'}
            try:
                records = Model.browse(ids)
                records.check_access_rights('write', raise_exception=True)
                records.check_access_rule('write')
                records.write(values)
                return {'success': True, 'ids': ids}
            except Exception as e:
                return {'error': str(e)}

        elif method == 'unlink':
            if not ids:
                return {'error': 'unlink requires ids'}
            try:
                records = Model.browse(ids)
                records.check_access_rights('unlink', raise_exception=True)
                records.check_access_rule('unlink')
                records.unlink()
                return {'success': True, 'ids': ids}
            except Exception as e:
                return {'error': str(e)}

        # Handle custom method calls (e.g., button actions)
        else:
            try:
                if ids:
                    records = Model.browse(ids)
                    # Security check happens inside the method
                    func = getattr(records, method)
                else:
                    func = getattr(Model, method)

                result = func(*args, **kwargs)
                # Handle common return types
                if hasattr(result, 'id'):
                    return {'success': True, 'result': {'id': result.id}}
                elif isinstance(result, dict):
                    return {'success': True, 'result': result}
                else:
                    return {'success': True, 'result': str(result) if result else None}
            except Exception as e:
                _logger.exception("MCP: Error executing %s.%s", model, method)
                return {'error': str(e)}
