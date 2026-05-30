"""
Veritas AI Error Handler
========================
Centralized error handling for API calls, async operations, and data processing.
Provides graceful fallbacks and detailed logging for debugging.
"""

import logging
import json
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error classification for structured handling."""
    API_ERROR = "api_error"
    AUTH_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    CONFIG_ERROR = "config_error"
    ASYNC_ERROR = "async_error"
    UNKNOWN_ERROR = "unknown_error"


class VeritasError(Exception):
    """Base exception for Veritas AI errors."""
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN_ERROR, details: Optional[Dict] = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/response."""
        return {
            "message": self.message,
            "error_type": self.error_type.value,
            "details": self.details
        }


class APIError(VeritasError):
    """Raised when an API call fails."""
    def __init__(self, message: str, provider: str = "unknown", status_code: Optional[int] = None, details: Optional[Dict] = None):
        self.provider = provider
        self.status_code = status_code
        details = details or {}
        details["provider"] = provider
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, ErrorType.API_ERROR, details)


class AuthError(VeritasError):
    """Raised when authentication fails (invalid API key, etc)."""
    def __init__(self, message: str, provider: str = "unknown"):
        details = {"provider": provider}
        super().__init__(message, ErrorType.AUTH_ERROR, details)


class NetworkError(VeritasError):
    """Raised when network/connection issues occur."""
    def __init__(self, message: str, url: Optional[str] = None):
        details = {"url": url} if url else {}
        super().__init__(message, ErrorType.NETWORK_ERROR, details)


class ParseError(VeritasError):
    """Raised when JSON/data parsing fails."""
    def __init__(self, message: str, raw_content: Optional[str] = None):
        details = {"raw_content": raw_content[:200] if raw_content else None}
        super().__init__(message, ErrorType.PARSE_ERROR, details)


class ConfigError(VeritasError):
    """Raised when configuration is missing or invalid."""
    def __init__(self, message: str, missing_keys: Optional[list] = None):
        details = {"missing_keys": missing_keys or []}
        super().__init__(message, ErrorType.CONFIG_ERROR, details)


def handle_errors(error_type: ErrorType = ErrorType.UNKNOWN_ERROR, fallback_return: Any = None):
    """
    Decorator for handling errors in async and sync functions.
    
    Args:
        error_type: Classification of errors this function may raise
        fallback_return: Value to return if error occurs
    
    Usage:
        @handle_errors(ErrorType.API_ERROR, fallback_return={})
        async def my_api_call():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except VeritasError as e:
                logger.error(f"Veritas error in {func.__name__}: {e.message}", extra=e.to_dict())
                return fallback_return
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in {func.__name__}: {str(e)}")
                return fallback_return
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                return fallback_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except VeritasError as e:
                logger.error(f"Veritas error in {func.__name__}: {e.message}", extra=e.to_dict())
                return fallback_return
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in {func.__name__}: {str(e)}")
                return fallback_return
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                return fallback_return

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def validate_config(required_keys: list, env_dict: Dict[str, str]) -> None:
    """
    Validate that all required config keys are present.
    
    Args:
        required_keys: List of required env variable names
        env_dict: Dictionary of environment variables
        
    Raises:
        ConfigError: If any required keys are missing
    """
    missing = [key for key in required_keys if not env_dict.get(key)]
    if missing:
        raise ConfigError(
            f"Missing required configuration keys: {', '.join(missing)}",
            missing_keys=missing
        )


def safe_json_parse(content: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Safely parse JSON with fallback.
    
    Args:
        content: JSON string to parse
        default: Value to return on parse failure
        
    Returns:
        Parsed JSON dict or default value
    """
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        logger.debug(f"Content preview: {content[:500]}")
        if default is None:
            default = {}
        return default


def get_fallback_response(agent_name: str) -> Dict[str, Any]:
    """
    Return a safe fallback response for an agent when API calls fail.
    
    Args:
        agent_name: Name of the agent (e.g., "Agent 1", "Agent 2")
        
    Returns:
        Dictionary with safe default values
    """
    return {
        "agent_name": agent_name,
        "status": "error",
        "logs": [
            f"[ERROR] {agent_name} encountered an API error.",
            "[INFO] Using fallback safe response.",
            "[WARNING] Results may be incomplete or delayed."
        ],
        "data": f"[{agent_name} data unavailable due to API error]",
        "proxy_utilized": "N/A",
        "duration_seconds": 0,
        "target_url": None,
    }


# Error message templates for common issues
ERROR_MESSAGES = {
    "groq_auth": "Groq API authentication failed. Check GROQ_API_KEY in .env file.",
    "groq_rate_limit": "Groq API rate limit exceeded. Please wait before retrying.",
    "bright_data_auth": "Bright Data authentication failed. Check BRIGHT_DATA_API_TOKEN in .env file.",
    "network_timeout": "Network request timed out. Check internet connection or URL.",
    "json_parse": "Failed to parse API response as JSON. Response may be invalid.",
    "config_missing": "Configuration file (.env) missing required keys. Check setup instructions.",
}


class ErrorResponse:
    """Structured error response for frontend display."""
    def __init__(self, title: str, message: str, error_type: ErrorType, details: Optional[Dict] = None):
        self.title = title
        self.message = message
        self.error_type = error_type
        self.details = details or {}

    def to_streamlit_alert(self) -> str:
        """Format error for Streamlit alert box."""
        return f"**{self.title}**\n\n{self.message}\n\n*Error Type: {self.error_type.value}*"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "message": self.message,
            "error_type": self.error_type.value,
            "details": self.details
        }
