import os
import json
from datetime import datetime, timedelta
import hashlib

from .tokens import normalize_identifier, BASE_DIR

ACTIVATION_STORE = os.path.join(BASE_DIR, "activation.json")


def create_activation_id(email: str, issued_at: str) -> str:
    """Return a deterministic id from email and timestamp."""
    clean = normalize_identifier(email)
    base = f"{clean}:{issued_at}"
    return hashlib.sha256(base.encode()).hexdigest()


def generate_activation_file(email: str, path: str) -> None:
    """Generate an activation JSON file for *email* valid for 30 minutes."""
    issued_at = datetime.utcnow().isoformat(timespec="seconds")
    expires_at = (datetime.utcnow() + timedelta(minutes=30)).isoformat(timespec="seconds")
    data = {
        "email": normalize_identifier(email),
        "id": create_activation_id(email, issued_at),
        "issued_at": issued_at,
        "expires_at": expires_at,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def verify_activation_data(data: dict, email: str) -> None:
    """Validate activation data for *email* or raise ValueError."""
    try:
        file_email = data["email"]
        issued_at = data["issued_at"]
        expires_at = data["expires_at"]
        act_id = data["id"]
    except KeyError:
        raise ValueError("Archivo de licencia inválido")

    if normalize_identifier(file_email) != normalize_identifier(email):
        raise ValueError("Correo no coincide")

    if datetime.utcnow() > datetime.fromisoformat(expires_at):
        raise ValueError("Licencia expirada")

    expected = create_activation_id(file_email, issued_at)
    if expected != act_id:
        raise ValueError("ID inválido")


def activate_from_file(path: str, email: str) -> dict:
    """Validate *path* for *email* and return activation data."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    verify_activation_data(data, email)
    with open(ACTIVATION_STORE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def load_activation() -> dict | None:
    """Return stored activation data if available."""
    if os.path.exists(ACTIVATION_STORE):
        with open(ACTIVATION_STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
