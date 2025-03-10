from typing import Any
import mcp.types as types
from loguru import logger

class BaseToolHandler:
    """Base class for all tool handlers to standardize behavior and provide common utilities."""
    
    _sessions: dict[str, Any] = {}
    _playwright: Any = None


    def add_session(session_id: str, session_info):
        self._sessions[session_id] = session_info

    def get_session(session_id:str):
        return self._sessions.get(session_id)
    
    async def handle(self, name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Base handle method to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _get_active_session(self) -> tuple[str, Any]:
        """Helper method to get the active session or raise an error if no session exists."""
        logger.info(f"{self._sessions=}")
        if not self._sessions:
            raise ValueError(f"No active browser session({self._sessions=}). Please create a new session first.")
        
        session_id = list(self._sessions.keys())[-1]
        return session_id, self._sessions[session_id]
    
    def _get_active_page(self) -> Any:
        """Helper method to get the active page from the active session."""
        _, session = self._get_active_session()
        return session["page"]
