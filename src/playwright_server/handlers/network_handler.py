from typing import Any
import json
import mcp.types as types
from .base_handler import BaseToolHandler

class NetworkHandler(BaseToolHandler):
    """Handler for retrieving browser network requests and responses."""
    
    _network_events: dict[str, list[dict[str, Any]]] = {}
    
    async def _setup_network_listener(self, page: Any, session_id: str) -> None:
        """Set up listeners for network events on the given page."""
        if session_id not in self._network_events:
            self._network_events[session_id] = []
            
        async def handle_request(request):
            """Handle request events."""
            try:
                headers = await request.all_headers()
                post_data = None
                
                try:
                    post_data = await request.post_data()
                except:
                    # Post data might not be available for all requests
                    pass
                
                request_data = {
                    "id": id(request),
                    "type": "request",
                    "url": request.url,
                    "method": request.method,
                    "headers": headers,
                    "post_data": post_data,
                    "resource_type": request.resource_type,
                    "timestamp": await page.evaluate("new Date().toISOString()"),
                    "status": None,
                    "status_text": None,
                    "response_headers": None,
                    "response_size": None,
                    "response_body": None,
                }
                
                self._network_events[session_id].append(request_data)
            except Exception as e:
                # Silently handle errors to prevent crashing the listener
                pass
        
        async def handle_response(response):
            """Handle response events."""
            try:
                request = response.request
                request_id = id(request)
                
                # Find the corresponding request
                for event in self._network_events[session_id]:
                    if event["id"] == request_id:
                        # Update with response data
                        headers = await response.all_headers()
                        event.update({
                            "status": response.status,
                            "status_text": response.status_text,
                            "response_headers": headers,
                        })
                        
                        # Try to get response size
                        try:
                            body = await response.body()
                            event["response_size"] = len(body)
                            
                            # For small text responses, include the body (limit to avoid large binary data)
                            content_type = headers.get("content-type", "")
                            if (len(body) < 10240 and 
                                ("json" in content_type or 
                                 "text" in content_type or 
                                 "javascript" in content_type or 
                                 "css" in content_type)):
                                try:
                                    event["response_body"] = body.decode('utf-8')
                                except:
                                    pass
                        except:
                            # Some responses might not have a body
                            pass
                            
                        break
            except Exception as e:
                # Silently handle errors to prevent crashing the listener
                pass
        
        # Only add listeners if not already added
        if not hasattr(page, "_network_listener_added"):
            page.on("request", handle_request)
            page.on("response", handle_response)
            setattr(page, "_network_listener_added", True)
    
    async def handle(self, name: str, arguments: dict | None) -> list[types.TextContent]:
        """Retrieve browser network activity for the current session."""
        try:
            session_id, session = self._get_active_session()
            page = session["page"]
            
            # Make sure the network listener is set up
            await self._setup_network_listener(page, session_id)
            
            # Get network events for this session
            events = self._network_events.get(session_id, [])
            
            # Apply filters if provided
            if arguments:
                # Filter by URL
                url_filter = arguments.get("url")
                if url_filter:
                    events = [e for e in events if url_filter in e["url"]]
                
                # Filter by method
                method_filter = arguments.get("method")
                if method_filter:
                    events = [e for e in events if e["method"] == method_filter]
                
                # Filter by status code range
                status_min = arguments.get("status_min")
                if status_min is not None:
                    events = [e for e in events if e["status"] is not None and e["status"] >= status_min]
                
                status_max = arguments.get("status_max")
                if status_max is not None:
                    events = [e for e in events if e["status"] is not None and e["status"] <= status_max]
                
                # Filter by resource type
                resource_type = arguments.get("resource_type")
                if resource_type:
                    events = [e for e in events if e["resource_type"] == resource_type]
            
            # Apply limit
            limit = arguments.get("limit", 50) if arguments else 50
            events = events[-limit:]
            
            # Format the events for display
            result = []
            for event in events:
                entry = f"[{event['timestamp']}] {event['method']} {event['url']} ({event['resource_type']})"
                if event["status"] is not None:
                    entry += f" - Status: {event['status']} {event['status_text']}"
                    
                if event["response_size"] is not None:
                    entry += f", Size: {event['response_size']} bytes"
                
                result.append(entry)
                
                # Add headers if requested
                if arguments and arguments.get("show_headers", False):
                    if event["headers"]:
                        result.append("  Request Headers:")
                        for key, value in event["headers"].items():
                            result.append(f"    {key}: {value}")
                    
                    if event["response_headers"]:
                        result.append("  Response Headers:")
                        for key, value in event["response_headers"].items():
                            result.append(f"    {key}: {value}")
                
                # Add response body if available and requested
                if arguments and arguments.get("show_body", False) and event.get("response_body"):
                    result.append("  Response Body:")
                    
                    # Try to pretty print JSON
                    body = event["response_body"]
                    try:
                        if "json" in event.get("response_headers", {}).get("content-type", ""):
                            body_obj = json.loads(body)
                            body = json.dumps(body_obj, indent=2)
                    except:
                        pass
                        
                    # Limit body size for display
                    if len(body) > 1000:
                        body = body[:1000] + "... [truncated]"
                        
                    # Add body with indentation
                    for line in body.split("\n"):
                        result.append(f"    {line}")
            
            formatted_result = "\n".join(result) if result else "No network activity recorded."
            return [types.TextContent(type="text", text=formatted_result)]
            
        except ValueError as e:
            return [types.TextContent(type="text", text=str(e))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error retrieving network activity: {str(e)}")]
