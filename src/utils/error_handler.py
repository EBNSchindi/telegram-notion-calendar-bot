"""Centralized error handling utilities for the Telegram bot."""

import logging
from typing import Optional, Any, Dict, Union
from enum import Enum
from telegram import Update
from telegram.ext import ContextTypes

from src.constants import StatusEmojis

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can occur in the bot."""
    NETWORK = "network"
    NOTION_API = "notion_api"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    AI_SERVICE = "ai_service"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"        # User can continue normally
    MEDIUM = "medium"  # Feature unavailable but bot works
    HIGH = "high"      # Critical error, bot may not work properly
    CRITICAL = "critical"  # System failure


class BotError(Exception):
    """Custom exception class for bot errors."""
    
    def __init__(
        self, 
        message: str, 
        error_type: ErrorType, 
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.user_message = user_message or self._generate_user_message()
        self.context = context or {}
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly message based on error type."""
        user_messages = {
            ErrorType.NETWORK: "🌐 Verbindungsproblem aufgetreten. Bitte versuche es in einem Moment erneut.",
            ErrorType.NOTION_API: "📝 Problem mit der Notion-Verbindung. Bitte überprüfe deine Konfiguration.",
            ErrorType.VALIDATION: "❌ Eingabe ungültig. Bitte überprüfe deine Angaben.",
            ErrorType.AUTHENTICATION: "🔒 Authentifizierungsproblem. Bitte kontaktiere den Administrator.",
            ErrorType.RATE_LIMIT: "⏰ Zu viele Anfragen. Bitte warte einen Moment und versuche es erneut.",
            ErrorType.USER_INPUT: "📝 Eingabe konnte nicht verarbeitet werden. Bitte verwende ein anderes Format.",
            ErrorType.AI_SERVICE: "🤖 KI-Service ist vorübergehend nicht verfügbar. Versuche es ohne KI-Unterstützung.",
            ErrorType.SYSTEM: "❌ Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut."
        }
        return user_messages.get(self.error_type, user_messages[ErrorType.SYSTEM])


class ErrorHandler:
    """Centralized error handler for the bot."""
    
    def __init__(self):
        self.error_stats = {}
    
    async def handle_error(
        self, 
        error: Union[Exception, BotError], 
        update: Optional[Update] = None,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle an error with appropriate logging and user notification."""
        
        # Convert to BotError if necessary
        if not isinstance(error, BotError):
            bot_error = self._convert_to_bot_error(error)
        else:
            bot_error = error
        
        # Log the error
        self._log_error(bot_error, update, additional_context)
        
        # Update statistics
        self._update_error_stats(bot_error)
        
        # Notify user if possible
        if update:
            await self._notify_user(bot_error, update)
    
    def _convert_to_bot_error(self, error: Exception) -> BotError:
        """Convert generic exception to BotError."""
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Determine error type based on error message and type
        if "network" in error_str or "timeout" in error_str or "connection" in error_str:
            error_type = ErrorType.NETWORK
        elif "notion" in error_str or "api" in error_str:
            error_type = ErrorType.NOTION_API
        elif "validation" in error_str or "invalid" in error_str:
            error_type = ErrorType.VALIDATION
        elif "auth" in error_str or "permission" in error_str:
            error_type = ErrorType.AUTHENTICATION
        elif "rate" in error_str or "limit" in error_str:
            error_type = ErrorType.RATE_LIMIT
        elif "openai" in error_str or "ai" in error_str:
            error_type = ErrorType.AI_SERVICE
        else:
            error_type = ErrorType.SYSTEM
        
        # Determine severity
        if error_type in [ErrorType.CRITICAL, ErrorType.AUTHENTICATION]:
            severity = ErrorSeverity.CRITICAL
        elif error_type in [ErrorType.NETWORK, ErrorType.NOTION_API]:
            severity = ErrorSeverity.HIGH
        elif error_type in [ErrorType.AI_SERVICE, ErrorType.RATE_LIMIT]:
            severity = ErrorSeverity.MEDIUM
        else:
            severity = ErrorSeverity.LOW
        
        return BotError(
            message=str(error),
            error_type=error_type,
            severity=severity,
            context={"original_error_type": error_type_name}
        )
    
    def _log_error(
        self, 
        error: BotError, 
        update: Optional[Update], 
        additional_context: Optional[Dict[str, Any]]
    ) -> None:
        """Log error with appropriate level based on severity."""
        
        # Get user information safely
        user_info = "Unknown User"
        if update and update.effective_user:
            user_info = f"{update.effective_user.first_name or 'User'} ({update.effective_user.id})"
        
        # Prepare context
        log_context = {
            "error_type": error.error_type.value,
            "severity": error.severity.value,
            "user": user_info,
            **error.context
        }
        
        if additional_context:
            log_context.update(additional_context)
        
        # Format log message
        log_message = f"Bot error for user {user_info}: {error.error_type.value} - {str(error)[:200]}..."
        
        # Log with appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=log_context, exc_info=error)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=log_context, exc_info=error)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=log_context)
        else:
            logger.info(log_message, extra=log_context)
    
    def _update_error_stats(self, error: BotError) -> None:
        """Update error statistics for monitoring."""
        error_key = f"{error.error_type.value}_{error.severity.value}"
        self.error_stats[error_key] = self.error_stats.get(error_key, 0) + 1
    
    async def _notify_user(self, error: BotError, update: Update) -> None:
        """Notify user about the error if possible."""
        try:
            if update.effective_message:
                await update.effective_message.reply_text(
                    error.user_message,
                    parse_mode=None  # Safe fallback
                )
        except Exception as notification_error:
            logger.error(f"Failed to notify user about error: {notification_error}")
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics for monitoring."""
        return self.error_stats.copy()
    
    def reset_error_stats(self) -> None:
        """Reset error statistics."""
        self.error_stats.clear()


# Global error handler instance
global_error_handler = ErrorHandler()


def handle_bot_error(
    error_type: ErrorType,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    user_message: Optional[str] = None
):
    """Decorator for handling bot errors in functions."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Find update object in arguments
                update = None
                for arg in args:
                    if isinstance(arg, Update):
                        update = arg
                        break
                
                bot_error = BotError(
                    message=str(e),
                    error_type=error_type,
                    severity=severity,
                    user_message=user_message,
                    context={"function": func.__name__}
                )
                
                await global_error_handler.handle_error(bot_error, update)
                
                # Re-raise for critical errors
                if severity == ErrorSeverity.CRITICAL:
                    raise
                
        return wrapper
    return decorator


class SafeOperationContext:
    """Context manager for safe operations with automatic error handling."""
    
    def __init__(
        self,
        operation_name: str,
        error_type: ErrorType = ErrorType.SYSTEM,
        update: Optional[Update] = None,
        silent_errors: bool = False
    ):
        self.operation_name = operation_name
        self.error_type = error_type
        self.update = update
        self.silent_errors = silent_errors
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            bot_error = BotError(
                message=f"Error in {self.operation_name}: {str(exc_val)}",
                error_type=self.error_type,
                context={"operation": self.operation_name}
            )
            
            if not self.silent_errors:
                await global_error_handler.handle_error(bot_error, self.update)
            
            return True  # Suppress the exception
        
        return False