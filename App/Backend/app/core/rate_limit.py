"""
Rate limiting configuration module.

Strategy: IP-based rate limiting using the Slowapi library.
Each endpoint decorated with @limiter.limit("N/period") tracks requests
by the client's remote IP address via get_remote_address.

Limits are applied at the endpoint level in router files.
Configured limits:
- Login: 5 requests per 15 minutes per IP (brute-force protection).
- Other endpoints can be individually decorated as needed.

Slowapi is initialized by creating a global Limiter instance with the
key function that identifies clients (IP address in this case).
The limiter is attached to app.state in main.py to integrate with FastAPI.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance using the client's IP address as the key.
# get_remote_address extracts the client IP from the request object,
# considering proxy headers when behind a reverse proxy.
limiter = Limiter(key_func=get_remote_address)
