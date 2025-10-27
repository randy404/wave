# notify_whatsapp.py
# Helper to send WhatsApp via Twilio Sandbox/Business
# Reads credentials from Streamlit secrets or .env / environment variables.

import os
from typing import Optional, Iterable, Union, List

# Try loading from dotenv first
try:
    from dotenv import load_dotenv
    load_dotenv()  # load .env if present
except Exception:
    pass

# Try loading from Streamlit secrets (for Streamlit Cloud)
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        # Override environment variables with Streamlit secrets if available
        for key in st.secrets:
            if key not in os.environ or not os.environ[key]:
                os.environ[key] = st.secrets[key]
except Exception:
    pass

from twilio.rest import Client

# Required (see .env or Streamlit secrets)
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")

# Sender number (Twilio WhatsApp). Sandbox default: whatsapp:+14155238886
FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# Default recipient(s) (comma-separated allowed)
# Format: 'whatsapp:+62xxxxxxxxxx'
TO_DEFAULT = os.getenv("WHATSAPP_TO", "").strip()

if not ACCOUNT_SID or not AUTH_TOKEN:
    raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN are not set. Please configure in Streamlit secrets or .env file.")

_client = Client(ACCOUNT_SID, AUTH_TOKEN)

def _normalize_targets(to: Optional[Union[str, Iterable[str]]]) -> List[str]:
    if to is None or (isinstance(to, str) and not to.strip()):
        to = TO_DEFAULT
    if isinstance(to, str):
        to_list = [t.strip() for t in to.split(",") if t.strip()]
    else:
        to_list = list(to)
    if not to_list:
        raise ValueError("Empty destination. Set WHATSAPP_TO in .env or pass to=...")
    # Ensure 'whatsapp:+62...' format
    norm = []
    for t in to_list:
        if not t.startswith("whatsapp:"):
            t = "whatsapp:" + t
        norm.append(t)
    return norm

def send_whatsapp(message: str, to: Optional[Union[str, Iterable[str]]] = None, media_url: Optional[str] = None) -> List[str]:
    """
    Send WhatsApp message(s).
    - message: text content
    - to: single string, comma-separated, or list[str]
    - media_url: optional image/file URL
    return: list of message_sid
    """
    sids = []
    for dest in _normalize_targets(to):
        kwargs = {"from_": FROM, "to": dest, "body": message}
        if media_url:
            kwargs["media_url"] = [media_url]
        msg = _client.messages.create(**kwargs)
        sids.append(msg.sid)
    return sids

def send_tsunami_alert_whatsapp(extreme_count: int, peak_y: int, frame_idx: int, to: Optional[Union[str, Iterable[str]]] = None, location: Optional[str] = None) -> List[str]:
    """
    Send dedicated tsunami alert via WhatsApp.
    
    Args:
        extreme_count (int): Number of consecutive EXTREME detections
        peak_y (int): Wave peak Y position
        frame_idx (int): Frame number
        to (str, optional): Destination (+62... or whatsapp:+62...)
        location (str, optional): Camera location (env fallback)
    
    Returns:
        list[str]: List of message SIDs
    """
    
    from datetime import datetime
    
    # Determine location
    if location:
        location_text = location
    else:
        # Try from environment variable
        camera_location = os.getenv("CAMERA_LOCATION", "")
        if camera_location:
            location_text = camera_location
        else:
            location_text = "[YOUR CAMERA LOCATION]"
    
    alert_message = f"""🚨 *POTENTIAL TSUNAMI ALERT!* 🚨

The wave detection system has detected *{extreme_count} consecutive* EXTREME waves (> 4 meters).

*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Location:* {location_text}
*Status:* > 4 Meters (EXTREME)
*Wave Peak Y:* {peak_y}
*Frame:* {frame_idx}

⚠️ *EVACUATE TO HIGHER GROUND IMMEDIATELY!* ⚠️
Contact local authorities now!

_Automatic Wave Detection System - Tsunami Alert_"""
    
    return send_whatsapp(alert_message, to)