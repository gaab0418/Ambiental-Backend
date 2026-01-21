from contextvars import ContextVar
import uuid

# Context variable to store correlation ID for the current request context
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default=None)

def get_correlation_id() -> str:
    """Get the current correlation ID or generate a new one if not set"""
    val = correlation_id_ctx.get()
    if not val:
        val = str(uuid.uuid4())
        correlation_id_ctx.set(val)
    return val

def set_correlation_id(val: str):
    """Set the correlation ID for the current context"""
    correlation_id_ctx.set(val)
