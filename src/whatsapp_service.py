"""Send WhatsApp messages using Twilio.

This module provides helper functions to deliver different kinds of
feedback (grammar, reading, etc.) through Twilio's WhatsApp API.

Environment variables
---------------------
TWILIO_ACCOUNT_SID
    Account identifier from the Twilio console.
TWILIO_AUTH_TOKEN
    Authentication token from the Twilio console.
TWILIO_WHATSAPP_NUMBER
    Twilio phone number enabled for WhatsApp (e.g., ``whatsapp:+14155238886``).
"""

from __future__ import annotations

import os
from typing import Optional

from twilio.rest import Client


_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
_from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

_client: Optional[Client] = None
if _account_sid and _auth_token:
    _client = Client(_account_sid, _auth_token)


def _send_message(body: str, to: str) -> None:
    """Send *body* to the ``to`` phone number via WhatsApp.

    The ``to`` number should be in international format, without the
    ``whatsapp:`` prefix.
    """

    if not _client:
        raise RuntimeError("Twilio client is not configured")
    if not _from_number:
        raise RuntimeError("TWILIO_WHATSAPP_NUMBER is not set")

    _client.messages.create(body=body, from_=_from_number, to=f"whatsapp:{to}")


def send_grammar(text: str, to: str) -> None:
    """Send grammar feedback *text* to the recipient ``to``."""

    _send_message(text, to)


def send_reading(text: str, to: str) -> None:
    """Send reading exercise feedback."""

    _send_message(text, to)


def send_listening(text: str, to: str) -> None:
    """Send listening exercise feedback."""

    _send_message(text, to)


def send_speaking(text: str, to: str) -> None:
    """Send speaking exercise feedback."""

    _send_message(text, to)


def send_writing(text: str, to: str) -> None:
    """Send writing exercise feedback."""

    _send_message(text, to)
