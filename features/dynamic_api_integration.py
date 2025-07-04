"""
Live External API Integration via Plugins
Allows the AI to dynamically learn and interact with external APIs using OpenAPI/Swagger specs.
"""

import json
import yaml
import requests
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import re
import urllib.parse
from pathlib import Path
import google.generativeai as genai
import asyncio
import aiohttp
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename

@dataclass
class APIEndpoint:
    path: str
    method: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)
    security: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

@dataclass
class APIClient:
    name: str
    base_url: str
    version: str
    description: str
    endpoints: Dict[str, APIEndpoint] = field(default_factory=dict)
    authentication: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

@dataclass
class APICall:
    client_name: str
    endpoint_id: str
    method: str
    url: str
    parameters: Dict[str, Any]
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0

class DynamicAPIManager:
    """Manages dynamic API integration and client generation"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro-exp-03-25"):
        self.model_name = model_name
        self.api_clients: Dict[str, APIClient] = {}
        self.call_history: List[APICall] = []
        self.auth_handlers: Dict[str, Callable] = {
            'bearer': self._handle_bearer_auth,
            'api_key': self._handle_api_key_auth,
            'basic': self._handle_basic_auth,
            'oauth2': self._handle_oauth2_auth
        }
        
    async def learn_api_from_spec(self, spec_source: Union[str, Dict], name: str = None) -> APIClient:
        """Learn an API from OpenAPI/Swagger specification"""
        
        # Load the spec
        if isinstance(spec_source, str):
            if spec_source.startswith(('http://', 'https://')):
                # URL to spec
                async with aiohttp.ClientSession() as session:
                    async with session.get(spec_source) as response:
                        if response.content_type == 'application/json':
                            spec = await response.json()
                        else:
                            spec_text = await response.text()
                            spec = yaml.safe_load(spec_text)
            else:
                # File path
                spec_path = Path(spec_source)
                if spec_path.suffix.lower() == '.json':
                    with open(spec_path, 'r') as f:
                        spec = json.load(f)
                else:
                    with open(spec_path, 'r') as f:
                        spec = yaml.safe_load(f)
        else:
            spec = spec_source
        
        # Validate the spec
        try:
            validate_spec(spec)
        except Exception as e:
            print(f"Warning: OpenAPI spec validation failed: {e}")
        
        # Extract API information
        api_info = spec.get('info', {})
        api_name = name or api_info.get('title', 'Unknown API')
        api_version = api_info.get('version', '1.0.0')
        api_description = api_info.get('description', '')
        
        # Determine base URL
        base_url = ""
        if 'servers' in spec and spec['servers']:
            base_url = spec['servers'][0]['url']
        elif 'host' in spec:
            scheme = spec.get('schemes', ['https'])[0]
            base_url = f"{scheme}://{spec['host']}"
            if 'basePath' in spec:
                base_url += spec['basePath']
        
        # Create API client
        client = APIClient(
            name=api_name,
            base_url=base_url,
            version=api_version,
            description=api_description
        )
        
        # Parse authentication
        if 'securityDefinitions' in spec:
            client.authentication = spec['securityDefinitions']
        elif 'components' in spec and 'securitySchemes' in spec['components']:
            client.authentication = spec['components']['securitySchemes']
        
        # Parse endpoints
        paths = spec.get('paths', {})
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint_id = f"{method.upper()}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
                    
                    endpoint = APIEndpoint(
                        path=path,
                        method=method.upper(),
                        summary=operation.get('summary', ''),
                        description=operation.get('description', ''),
                        parameters=operation.get('parameters', []),
                        request_body=operation.get('requestBody'),
                        responses=operation.get('responses', {}),
                        security=operation.get('security', []),
                        tags=operation.get('tags', [])
                    )
                    
                    client.endpoints[endpoint_id] = endpoint
        
        # Store the client
        self.api_clients[api_name] = client
        
        return client
    
    async def discover_api_capabilities(self, client_name: str) -> Dict[str, Any]:
        """Use AI to analyze and understand API capabilities"""
        
        if client_name not in self.api_clients:
            return {"error": "API client not found"}
        
        client = self.api_clients[client_name]
        
        # Prepare API summary for AI analysis
        api_summary = {
            "name": client.name,
            "description": client.description,
            "base_url": client.base_url,
            "endpoints": []
        }
        
        for endpoint_id, endpoint in client.endpoints.items():
            endpoint_summary = {
                "id": endpoint_id,
                "method": endpoint.method,
                "path": endpoint.path,
                "summary": endpoint.summary,
                "description": endpoint.description,
                "parameters": [
                    {
                        "name": param.get('name', ''),
                        "type": param.get('type', param.get('schema', {}).get('type', '')),
                        "required": param.get('required', False),
                        "description": param.get('description', '')
                    }
                    for param in endpoint.parameters
                ],
                "tags": endpoint.tags
            }
            api_summary["endpoints"].append(endpoint_summary)
        
        analysis_prompt = f"""
        Analyze the following API specification and provide insights about its capabilities:
        
        API: {json.dumps(api_summary, indent=2)}
        
        Please provide:
        1. A summary of what this API does
        2. Main categories of functionality
        3. Most useful endpoints for common tasks
        4. Suggested use cases
        5. Any patterns or conventions used
        6. Authentication requirements
        
        Format your response as JSON with the following structure:
        {{
            "summary": "Brief description of API purpose",
            "categories": ["category1", "category2"],
            "key_endpoints": [
                {{
                    "endpoint_id": "GET_/users",
                    "purpose": "Retrieve user information",
                    "use_case": "User management"
                }}
            ],
            "use_cases": ["use case 1", "use case 2"],
            "patterns": ["pattern 1", "pattern 2"],
            "auth_info": "Authentication details"
        }}
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(analysis_prompt)
            
            # Parse the JSON response
            analysis = json.loads(response.text.strip())
            return analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze API: {str(e)}"}
    
    async def generate_api_call(self, client_name: str, task_description: str, 
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate an appropriate API call based on task description"""
        
        if client_name not in self.api_clients:
            return {"error": "API client not found"}
        
        client = self.api_clients[client_name]
        context = context or {}
        
        # Get API capabilities
        capabilities = await self.discover_api_capabilities(client_name)
        
        generation_prompt = f"""
        Generate an API call for the following task using the {client_name} API:
        
        Task: {task_description}
        Context: {json.dumps(context)}
        
        Available API endpoints:
        {json.dumps([{
            "id": eid,
            "method": ep.method,
            "path": ep.path,
            "summary": ep.summary,
            "parameters": [p.get('name', '') for p in ep.parameters]
        } for eid, ep in client.endpoints.items()], indent=2)}
        
        API Capabilities: {json.dumps(capabilities)}
        
        Please generate the most appropriate API call and return a JSON response:
        {{
            "endpoint_id": "selected_endpoint_id",
            "parameters": {{"param1": "value1"}},
            "body": {{"key": "value"}},
            "reasoning": "Why this endpoint was chosen"
        }}
        
        If no suitable endpoint exists, return:
        {{
            "error": "No suitable endpoint found",
            "suggestion": "What functionality would be needed"
        }}
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(generation_prompt)
            
            call_spec = json.loads(response.text.strip())
            
            if "error" in call_spec:
                return call_spec
            
            # Execute the generated call
            result = await self.execute_api_call(
                client_name,
                call_spec["endpoint_id"],
                call_spec.get("parameters", {}),
                call_spec.get("body")
            )
            
            result["reasoning"] = call_spec.get("reasoning", "")
            return result
            
        except Exception as e:
            return {"error": f"Failed to generate API call: {str(e)}"}
    
    async def execute_api_call(self, client_name: str, endpoint_id: str, 
                              parameters: Dict[str, Any] = None, 
                              body: Dict[str, Any] = None,
                              auth_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute an API call"""
        
        if client_name not in self.api_clients:
            return {"error": "API client not found"}
        
        client = self.api_clients[client_name]
        
        if endpoint_id not in client.endpoints:
            return {"error": "Endpoint not found"}
        
        endpoint = client.endpoints[endpoint_id]
        parameters = parameters or {}
        
        # Build the URL
        url = client.base_url + endpoint.path
        
        # Replace path parameters
        path_params = re.findall(r'\{([^}]+)\}', endpoint.path)
        for param in path_params:
            if param in parameters:
                url = url.replace(f"{{{param}}}", str(parameters[param]))
                del parameters[param]
        
        # Prepare headers
        headers = dict(client.headers)
        headers['Content-Type'] = 'application/json'
        
        # Handle authentication
        if auth_config:
            auth_headers = await self._apply_authentication(client, auth_config)
            headers.update(auth_headers)
        
        # Create API call record
        api_call = APICall(
            client_name=client_name,
            endpoint_id=endpoint_id,
            method=endpoint.method,
            url=url,
            parameters=parameters,
            headers=headers,
            body=body
        )
        
        try:
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                if endpoint.method == 'GET':
                    async with session.get(url, params=parameters, headers=headers) as response:
                        api_call.status_code = response.status
                        api_call.response = await response.json() if response.content_type == 'application/json' else await response.text()
                
                elif endpoint.method == 'POST':
                    async with session.post(url, params=parameters, json=body, headers=headers) as response:
                        api_call.status_code = response.status
                        api_call.response = await response.json() if response.content_type == 'application/json' else await response.text()
                
                elif endpoint.method == 'PUT':
                    async with session.put(url, params=parameters, json=body, headers=headers) as response:
                        api_call.status_code = response.status
                        api_call.response = await response.json() if response.content_type == 'application/json' else await response.text()
                
                elif endpoint.method == 'DELETE':
                    async with session.delete(url, params=parameters, headers=headers) as response:
                        api_call.status_code = response.status
                        api_call.response = await response.json() if response.content_type == 'application/json' else await response.text()
                
                else:
                    api_call.error = f"Unsupported HTTP method: {endpoint.method}"
            
            api_call.execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update client usage
            client.last_used = datetime.now()
            client.usage_count += 1
            
        except Exception as e:
            api_call.error = str(e)
        
        # Store the call
        self.call_history.append(api_call)
        
        # Return result
        result = {
            "success": api_call.error is None,
            "status_code": api_call.status_code,
            "response": api_call.response,
            "execution_time": api_call.execution_time
        }
        
        if api_call.error:
            result["error"] = api_call.error
        
        return result
    
    async def _apply_authentication(self, client: APIClient, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Apply authentication to API call headers"""
        headers = {}
        
        auth_type = auth_config.get('type', '').lower()
        
        if auth_type in self.auth_handlers:
            auth_headers = await self.auth_handlers[auth_type](client, auth_config)
            headers.update(auth_headers)
        
        return headers
    
    async def _handle_bearer_auth(self, client: APIClient, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Handle Bearer token authentication"""
        token = auth_config.get('token', '')
        return {"Authorization": f"Bearer {token}"}
    
    async def _handle_api_key_auth(self, client: APIClient, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Handle API key authentication"""
        key = auth_config.get('key', '')
        header_name = auth_config.get('header', 'X-API-Key')
        return {header_name: key}
    
    async def _handle_basic_auth(self, client: APIClient, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Handle Basic authentication"""
        import base64
        
        username = auth_config.get('username', '')
        password = auth_config.get('password', '')
        
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
    
    async def _handle_oauth2_auth(self, client: APIClient, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Handle OAuth2 authentication"""
        # This would need to implement OAuth2 flow
        # For now, assume we have an access token
        token = auth_config.get('access_token', '')
        return {"Authorization": f"Bearer {token}"}
    
    def get_api_clients(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered API clients"""
        return {
            name: {
                "name": client.name,
                "base_url": client.base_url,
                "version": client.version,
                "description": client.description,
                "endpoint_count": len(client.endpoints),
                "usage_count": client.usage_count,
                "last_used": client.last_used.isoformat(),
                "created_at": client.created_at.isoformat()
            }
            for name, client in self.api_clients.items()
        }
    
    def get_client_endpoints(self, client_name: str) -> Dict[str, Dict[str, Any]]:
        """Get endpoints for a specific API client"""
        if client_name not in self.api_clients:
            return {}
        
        client = self.api_clients[client_name]
        return {
            endpoint_id: {
                "method": endpoint.method,
                "path": endpoint.path,
                "summary": endpoint.summary,
                "description": endpoint.description,
                "parameter_count": len(endpoint.parameters),
                "tags": endpoint.tags
            }
            for endpoint_id, endpoint in client.endpoints.items()
        }
    
    def get_call_history(self, client_name: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get API call history"""
        calls = self.call_history
        
        if client_name:
            calls = [call for call in calls if call.client_name == client_name]
        
        # Return most recent calls
        calls = calls[-limit:]
        
        return [
            {
                "client_name": call.client_name,
                "endpoint_id": call.endpoint_id,
                "method": call.method,
                "url": call.url,
                "status_code": call.status_code,
                "execution_time": call.execution_time,
                "timestamp": call.timestamp.isoformat(),
                "success": call.error is None,
                "error": call.error
            }
            for call in calls
        ]
    
    async def suggest_api_workflow(self, goal: str, available_apis: List[str] = None) -> Dict[str, Any]:
        """Suggest a workflow using available APIs to achieve a goal"""
        
        if available_apis is None:
            available_apis = list(self.api_clients.keys())
        
        # Get capabilities of available APIs
        api_capabilities = {}
        for api_name in available_apis:
            if api_name in self.api_clients:
                capabilities = await self.discover_api_capabilities(api_name)
                api_capabilities[api_name] = capabilities
        
        workflow_prompt = f"""
        Design a workflow to achieve the following goal using the available APIs:
        
        Goal: {goal}
        
        Available APIs and their capabilities:
        {json.dumps(api_capabilities, indent=2)}
        
        Create a step-by-step workflow that uses these APIs effectively. Return a JSON response:
        {{
            "workflow_name": "Descriptive workflow name",
            "description": "What this workflow accomplishes",
            "steps": [
                {{
                    "step": 1,
                    "description": "What this step does",
                    "api": "api_name",
                    "endpoint": "endpoint_id",
                    "purpose": "Why this call is needed",
                    "depends_on": [0]
                }}
            ],
            "expected_outcome": "What the workflow should achieve"
        }}
        
        If the goal cannot be achieved with available APIs, suggest what additional APIs would be needed.
        """
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(workflow_prompt)
            
            workflow = json.loads(response.text.strip())
            return workflow
            
        except Exception as e:
            return {"error": f"Failed to generate workflow: {str(e)}"}
    
    def remove_api_client(self, client_name: str) -> bool:
        """Remove an API client"""
        if client_name in self.api_clients:
            del self.api_clients[client_name]
            return True
        return False
    
    def export_api_client(self, client_name: str) -> Optional[Dict[str, Any]]:
        """Export an API client configuration"""
        if client_name not in self.api_clients:
            return None
        
        client = self.api_clients[client_name]
        
        return {
            "name": client.name,
            "base_url": client.base_url,
            "version": client.version,
            "description": client.description,
            "endpoints": {
                endpoint_id: {
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "summary": endpoint.summary,
                    "description": endpoint.description,
                    "parameters": endpoint.parameters,
                    "request_body": endpoint.request_body,
                    "responses": endpoint.responses,
                    "security": endpoint.security,
                    "tags": endpoint.tags
                }
                for endpoint_id, endpoint in client.endpoints.items()
            },
            "authentication": client.authentication,
            "headers": client.headers
        }

# Global dynamic API manager instance
dynamic_api_manager = DynamicAPIManager()
