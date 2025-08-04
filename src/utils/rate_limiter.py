"""Rate limiting utilities for bot commands."""
import time
import logging
from typing import Dict, List, Callable, Any
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter for bot commands."""
    
    def __init__(self, max_requests: int = 30, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests: Dict[int, List[float]] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make a request."""
        now = time.time()
        
        # Get user's request history
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        user_request_times = self.user_requests[user_id]
        
        # Remove old requests outside the time window
        user_request_times[:] = [
            req_time for req_time in user_request_times 
            if now - req_time < self.time_window
        ]
        
        # Check if user has exceeded the limit
        if len(user_request_times) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        # Add current request
        user_request_times.append(now)
        return True
    
    def get_remaining_requests(self, user_id: int) -> int:
        """Get number of remaining requests for user."""
        if user_id not in self.user_requests:
            return self.max_requests
        
        now = time.time()
        user_request_times = self.user_requests[user_id]
        
        # Count requests within time window
        recent_requests = [
            req_time for req_time in user_request_times 
            if now - req_time < self.time_window
        ]
        
        return max(0, self.max_requests - len(recent_requests))
    
    def get_reset_time(self, user_id: int) -> float:
        """Get time when rate limit will reset for user."""
        if user_id not in self.user_requests or not self.user_requests[user_id]:
            return 0
        
        oldest_request = min(self.user_requests[user_id])
        return oldest_request + self.time_window


# Global rate limiter instance
_rate_limiter = RateLimiter(max_requests=30, time_window=60)  # 30 requests per minute


def rate_limit(max_requests: int = None, time_window: int = None) -> Callable[[Callable], Callable]:
    """
    Decorator to add rate limiting to bot command handlers.
    
    Args:
        max_requests: Override default max requests (default: 30)
        time_window: Override default time window in seconds (default: 60)
        
    Returns:
        Decorator function that applies rate limiting to the wrapped handler
        
    Example:
        @rate_limit(max_requests=10, time_window=60)  # 10 requests per minute
        async def my_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Handler code here
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(self: Any, update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
            user_id = update.effective_user.id
            
            # Use custom rate limiter if parameters are provided
            if max_requests is not None or time_window is not None:
                limiter = RateLimiter(
                    max_requests=max_requests or _rate_limiter.max_requests,
                    time_window=time_window or _rate_limiter.time_window
                )
            else:
                limiter = _rate_limiter
            
            if not limiter.is_allowed(user_id):
                reset_time = limiter.get_reset_time(user_id)
                wait_time = max(0, reset_time - time.time())
                
                await update.message.reply_text(
                    f"⏰ Rate Limit erreicht!\n"
                    f"Bitte warte {int(wait_time)} Sekunden bevor du den nächsten Befehl sendest."
                )
                return
            
            return await func(self, update, context, *args, **kwargs)
        return wrapper
    return decorator


def get_global_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter