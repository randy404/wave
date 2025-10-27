
# notify_sms.py
# Helper to send SMS via Twilio.
# - Prefer "TWILIO_MESSAGING_SERVICE_SID" if available.
# - Fallback to "TWILIO_SMS_FROM" (Twilio number in E.164 format, e.g., +12025550123).
# - Trial accounts: only verified numbers can receive SMS.
import os
from typing import Optional, Iterable, Union, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from twilio.rest import Client

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")

MSID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")  # disarankan untuk produksi
SMS_FROM = os.getenv("TWILIO_SMS_FROM")           # fallback: nomor Twilio (E.164, mis. +1415...)

if not ACCOUNT_SID or not AUTH_TOKEN:
    raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN belum di-set.")

_client = Client(ACCOUNT_SID, AUTH_TOKEN)

def _normalize_targets(to: Optional[Union[str, Iterable[str]]]) -> List[str]:
    if to is None:
        # try from env
        env_to = os.getenv("SMS_TO", "").strip()
        to = env_to
    if isinstance(to, str):
        to_list = [t.strip() for t in to.split(",") if t.strip()]
    else:
        to_list = list(to or [])
    if not to_list:
        raise ValueError("Empty destination. Set SMS_TO in .env or pass to=... (comma-separated/list).")
    # must be E.164: +62...
    return to_list

def send_sms(message: str, to: Optional[Union[str, Iterable[str]]] = None) -> List[str]:
    """
    Send SMS to one or more numbers (E.164, e.g., +62812xxxxxx).
    Return: list of message_sid
    """
    if not (MSID or SMS_FROM):
        raise RuntimeError("Either TWILIO_MESSAGING_SERVICE_SID or TWILIO_SMS_FROM must be set in .env")
    sids = []
    for dest in _normalize_targets(to):
        if MSID:
            msg = _client.messages.create(
                messaging_service_sid=MSID,
                to=dest,
                body=message
            )
        else:
            msg = _client.messages.create(
                from_=SMS_FROM,
                to=dest,
                body=message
            )
        sids.append(msg.sid)
    return sids
