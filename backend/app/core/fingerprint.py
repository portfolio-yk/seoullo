import hashlib
import hmac

from fastapi import Request

from app.core.config import Settings


def request_fingerprint(request: Request, settings: Settings) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",", 1)[0].strip() if forwarded else ""
    if not client_ip and request.client:
        client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown-browser")[:512]
    message = f"{client_ip or 'unknown-ip'}|{user_agent}".encode("utf-8")
    return hmac.new(settings.fingerprint_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

