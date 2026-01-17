"""
Odoo Client - HTTP/JSON-RPC wrapper for communicating with Odoo.
Handles authentication and session management.
"""
import httpx
import logging
from typing import Any, Optional

_logger = logging.getLogger(__name__)


class OdooClient:
    """
    HTTP client for communicating with Odoo via the butopea_mcp module endpoints.
    """

    def __init__(
        self,
        url: str,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        preferred_lang: str = 'en_US',
    ):
        self.url = url.rstrip('/')
        self.database = database
        self.username = username
        self.password = password
        self.api_key = api_key
        self.preferred_lang = preferred_lang
        self.session_id: Optional[str] = None
        self.uid: Optional[int] = None
        self._cookies: dict = {}

    async def authenticate(self) -> bool:
        """Authenticate with Odoo and get a session."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            if self.api_key:
                client.headers['Authorization'] = f'Bearer {self.api_key}'
                try:
                    result = await self._call_with_client(client, '/mcp/capabilities')
                    self.uid = result.get('user', {}).get('id')
                    return True
                except Exception as e:
                    _logger.error("API key authentication failed: %s", e)
                    return False
            else:
                try:
                    response = await client.post(
                        f'{self.url}/web/session/authenticate',
                        json={
                            'jsonrpc': '2.0',
                            'method': 'call',
                            'params': {
                                'db': self.database,
                                'login': self.username,
                                'password': self.password,
                            },
                            'id': 1,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'error' in data:
                        _logger.error("Auth error: %s", data['error'])
                        return False
                    
                    result = data.get('result', {})
                    self.uid = result.get('uid')
                    self.session_id = response.cookies.get('session_id')
                    self._cookies = dict(response.cookies)
                    
                    if self.uid:
                        _logger.info("Authenticated as user %s (uid=%s)", self.username, self.uid)
                        return True
                    return False
                except Exception as e:
                    _logger.error("Authentication failed: %s", e)
                    return False

    async def _call_with_client(self, client: httpx.AsyncClient, endpoint: str, **params) -> dict[str, Any]:
        """Call a butopea_mcp endpoint with provided client."""
        url = f'{self.url}{endpoint}'
        
        # Inject language context into params
        if 'context' not in params:
            params['context'] = {}
        params['context']['lang'] = self.preferred_lang
        
        response = await client.post(
            url,
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': params,
                'id': 1,
            },
            cookies=self._cookies,
        )
        response.raise_for_status()
        data = response.json()
        
        if 'error' in data:
            raise Exception(data['error'].get('message', str(data['error'])))
        
        return data.get('result', {})

    async def _call_mcp(self, endpoint: str, **params) -> dict[str, Any]:
        """Call a butopea_mcp endpoint."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            return await self._call_with_client(client, endpoint, **params)

    async def get_capabilities(self) -> dict[str, Any]:
        """Get accessible menus and models for the current user."""
        return await self._call_mcp('/mcp/capabilities')

    async def get_model_schema(self, model: str, view_type: str = 'form') -> dict[str, Any]:
        """Get field schema for a model."""
        return await self._call_mcp(f'/mcp/model/{model}/schema', view_type=view_type)

    async def search(
        self,
        model: str,
        domain: Optional[list] = None,
        fields: Optional[list[str]] = None,
        limit: int = 80,
        offset: int = 0,
        order: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search for records."""
        return await self._call_mcp(
            '/mcp/search',
            model=model,
            domain=domain or [],
            fields=fields,
            limit=limit,
            offset=offset,
            order=order,
        )

    async def execute(
        self,
        model: str,
        method: str,
        ids: Optional[list[int]] = None,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
        values: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Execute a method on a model."""
        return await self._call_mcp(
            '/mcp/execute',
            model=model,
            method=method,
            ids=ids,
            args=args,
            kwargs=kwargs,
            values=values,
        )
