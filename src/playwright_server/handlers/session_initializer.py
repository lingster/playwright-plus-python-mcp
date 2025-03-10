from typing import Any

class SessionInitializer:
    """Helper class to manage browser session initialization and listeners."""
    
    @staticmethod
    async def initialize_session(session_id: str, page: Any, handlers: dict[str, Any]) -> None:
        """Initialize a new browser session with all required listeners."""
        # Extract console log and network handlers
        console_handler = handlers.get("playwright_get_console_logs")
        network_handler = handlers.get("playwright_get_network_activity")
        
        # Set up the console log listener if available
        if console_handler:
            await console_handler._setup_console_log_listener(page, session_id)
            
        # Set up the network listener if available
        if network_handler:
            await network_handler._setup_network_listener(page, session_id)
            
        # This could be extended to initialize other listeners in the future
