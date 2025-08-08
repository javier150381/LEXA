import os
from pathlib import Path
from getpass import getpass
import secrets

import keyring
from dotenv import load_dotenv, set_key
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SERVICE = "WNThinker"
ACCOUNT = "deepseek-master"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _get_master_key():
    """Retrieve or create the master key stored in the system keyring."""
    master_hex = keyring.get_password(SERVICE, ACCOUNT)
    if master_hex is None:
        master_key = secrets.token_bytes(32)
        keyring.set_password(SERVICE, ACCOUNT, master_key.hex())
    else:
        master_key = bytes.fromhex(master_hex)
    return master_key


def _encrypt_and_store(plain_key: str) -> None:
    """Encrypt the provided key and persist it to the .env file."""
    master = _get_master_key()
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(master), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padded = plain_key.encode()
    padded += b"\0" * (16 - len(padded) % 16)
    encrypted = encryptor.update(padded) + encryptor.finalize()

    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), "DEEP_SEEK_ENC", encrypted.hex())
    set_key(str(ENV_PATH), "DEEP_SEEK_IV", iv.hex())
    load_dotenv(ENV_PATH, override=True)


def _decrypt() -> str | None:
    """Return the decrypted DEEP_SEEK key if present, else None."""
    enc = os.getenv("DEEP_SEEK_ENC")
    iv = os.getenv("DEEP_SEEK_IV")
    if not enc or not iv:
        return None
    master = _get_master_key()
    cipher = Cipher(algorithms.AES(master), modes.CBC(bytes.fromhex(iv)))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(bytes.fromhex(enc)) + decryptor.finalize()
    return decrypted.rstrip(b"\0").decode()


def get_deepseek_api_key() -> str:
    """Return the DEEP_SEEK API key, prompting and storing it if needed."""
    plain = os.getenv("DEEPSEEK_API_KEY")
    if plain:
        return plain

    key = _decrypt()
    if key:
        return key

    plain = getpass("Introduce la clave DEEP_SEEK: ")
    _encrypt_and_store(plain)
    return plain
