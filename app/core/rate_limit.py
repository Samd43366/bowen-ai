from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_email_identifier(request: Request) -> str:
    """
    Custom key function that attempts to rate-limit based on the email provided in the JSON body.
    Fallbacks to IP if no email is found.
    """
    try:
        # Note: This requires the request body to be read, which can be tricky in middleware
        # For route-level decorators, it works if we access the parsed body
        # However, a simpler version for this specific app is just using IP for now 
        # as body-parsing in the key_func is complex with async FastAPI.
        return get_remote_address(request)
    except:
        return get_remote_address(request)

# Create a singleton limiter instance keyed by client IP address
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
