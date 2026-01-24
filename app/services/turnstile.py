import requests
from django.conf import settings

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

def verify_turnstile(token: str, remoteip: str | None = None) -> tuple[bool, str]:
    if not token:
        return False, "Thiếu Turnstile token"

    secret = getattr(settings, "TURNSTILE_SECRET_KEY", "")
    if not secret:
        return False, "Server chưa cấu hình TURNSTILE_SECRET_KEY"

    data = {"secret": secret, "response": token}
    if remoteip:
        data["remoteip"] = remoteip

    try:
        r = requests.post(VERIFY_URL, data=data, timeout=8)
        r.raise_for_status()
        js = r.json()
    except Exception as e:
        return False, f"Không verify được Turnstile: {e}"

    if js.get("success") is True:
        return True, ""

    codes = js.get("error-codes") or []
    return False, "Turnstile không hợp lệ: " + (", ".join(codes) if codes else "unknown")
