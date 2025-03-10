import json
import time
from typing import Any
from loguru import logger
import mcp.types as types
from .base_handler import BaseToolHandler

class ConsoleLogHandler(BaseToolHandler):
    """Handler for retrieving browser console logs."""
    
    _console_logs: dict[str, list[dict[str, Any]]] = {}
    
    async def _setup_console_log_listener(self, page: Any, session_id: str) -> None:
        """Set up a listener for console messages on the given page."""
        if session_id not in self._console_logs:
            self._console_logs[session_id] = []
            
        async def handle_console(msg):
            log_entry = {
                "type": msg.type,
                "text": msg.text,
                "location": {
                    "url": msg.page.url,
                    "lineNumber": getattr(msg.location, "lineNumber", None),
                    "columnNumber": getattr(msg.location, "columnNumber", None),
                },
                "timestamp": await page.evaluate("new Date().toISOString()"),
            }
            self._console_logs[session_id].append(log_entry)
            
        # Only add listener if not already added
        if not hasattr(page, "_console_listener_added"):
            page.on("console", handle_console)
            setattr(page, "_console_listener_added", True)
    
    async def handle(self, name: str, arguments: dict | None) -> list[types.TextContent]:
        """Retrieve browser console logs for the current session."""
        try:
            session_id, session = self._get_active_session()
            page = session["page"]
            
            # Make sure the console listener is set up
            await self._setup_console_log_listener(page, session_id)

            logger.info(f"waiting 5 seconds for logs to accumulate")
            time.sleep(5)  # Sleep for 10 seconds to allow logs to accumulate
            logger.info(f"done waiting 5 seconds for logs to accumulate")
            
            # Get logs for this session
            logs = self._console_logs.get(session_id, [])
            
            # Optional filtering by log type
            log_type = arguments.get("type") if arguments else None
            if log_type:
                logs = [log for log in logs if log["type"] == log_type]
                
            # Optional limit
            limit = arguments.get("limit", 100) if arguments else 100
            logs = logs[-limit:]
            
            # Format logs for display
            formatted_logs = []
            for log in logs:
                log_entry = f"[{log['timestamp']}] [{log['type']}] {log['text']}"
                if log['location']['lineNumber'] is not None:
                    log_entry += f" (at {log['location']['url']}:{log['location']['lineNumber']}:{log['location']['columnNumber']})"
                formatted_logs.append(log_entry)
            
            result = "\n".join(formatted_logs) if formatted_logs else "No console logs available."
            return [types.TextContent(type="text", text=result)]
            
        except ValueError as e:
            return [types.TextContent(type="text", text=str(e))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error retrieving console logs: {str(e)}")]
