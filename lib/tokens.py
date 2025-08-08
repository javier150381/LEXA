import os
import sqlite3
import sys
from datetime import datetime
from contextlib import contextmanager

import json


def _get_base_dir():
    """Return a writable base directory for application data."""
    if getattr(sys, "frozen", False):
        user_dir = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(user_dir, "AbogadoVirtual")

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if not os.access(base, os.W_OK):
        user_dir = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
        return os.path.join(user_dir, "AbogadoVirtual")
    return base


BASE_DIR = _get_base_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")

TOKENS_DB = os.path.join(DATA_DIR, "tokens.db")
PASSWORD_FILE = os.path.join(DATA_DIR, "password.sha256")

# Costo base del proveedor por millón de tokens
DS_COST_PER_MILLION = 0.17

# Factor de incremento para obtener el precio al cliente
CLIENT_PRICE_FACTOR = 4.0


# Tarifas DeepSeek para cálculo rápido
DS_RATE_INPUT_HIT = 0.045
DS_RATE_INPUT_MISS = 0.18
DS_RATE_OUTPUT = 0.75

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_license_email() -> str | None:
    email = _load_config().get("license_email")
    return normalize_identifier(email) if email else None

def create_credit_id(email: str, amount: float) -> str:
    import hashlib

    clean = normalize_identifier(email)
    base = f"{clean}:{float(amount):.2f}"
    return hashlib.sha256(base.encode()).hexdigest()

def get_machine_id() -> str:
    """Return a unique identifier for the current machine."""
    env_id = os.getenv("AV_USER_ID")
    if env_id:
        return env_id

    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, "machine_id")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                stored = f.read().strip()
                if stored:
                    return stored
        except OSError:
            pass

    import uuid

    try:
        ident = hex(uuid.getnode())
    except Exception:
        ident = "unknown"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ident)
    except OSError:
        pass
    return ident

def normalize_identifier(value: str) -> str:
    """Return ``value`` normalized for comparisons."""
    import unicodedata

    normalized = unicodedata.normalize("NFC", (value or "").strip().lower())
    if normalized.endswith("@gmail.com"):
        local, domain = normalized.split("@", 1)
        if "+" in local:
            local = local.split("+", 1)[0]
        normalized = f"{local}@{domain}"
    return normalized


def create_user_id(email: str, issued_at: str) -> str:
    """Return a deterministic identifier from ``email`` and ``issued_at``."""
    import hashlib

    clean = normalize_identifier(email)
    base = f"{clean}:{issued_at}"
    return hashlib.sha256(base.encode()).hexdigest()

_current_activity: str | None = None


@contextmanager
def activity(name: str | None):
    """Context manager to temporarily label token usage with *name*.

    Any :func:`add_tokens` calls executed inside the ``with`` block will use
    ``name`` as the activity description.  The previous activity is restored
    afterwards.
    """
    prev = get_current_activity()
    set_current_activity(name)
    try:
        yield
    finally:
        set_current_activity(prev)


def set_current_activity(activity: str | None) -> None:
    """Set a description for the next token usage log."""
    global _current_activity
    _current_activity = activity


def get_current_activity() -> str | None:
    """Return the current activity description."""
    return _current_activity


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(TOKENS_DB) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS token_usage ("
            "id INTEGER PRIMARY KEY CHECK (id = 1),"
            "total INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS token_log ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "timestamp TEXT NOT NULL,"
            "tokens INTEGER NOT NULL,"
            "tokens_in INTEGER,"
            "tokens_out INTEGER,"
            "activity TEXT,"
            "cost REAL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS credit ("
            "id INTEGER PRIMARY KEY CHECK(id=1),"
            "balance REAL NOT NULL"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS used_credit_files ("
            "uid TEXT PRIMARY KEY"
            ")"
        )
        # Upgrade older DBs without the extra columns
        cols = [r[1] for r in conn.execute("PRAGMA table_info(token_log)")]
        if "activity" not in cols:
            conn.execute("ALTER TABLE token_log ADD COLUMN activity TEXT")
        if "cost" not in cols:
            conn.execute("ALTER TABLE token_log ADD COLUMN cost REAL")
        if "tokens_in" not in cols:
            conn.execute("ALTER TABLE token_log ADD COLUMN tokens_in INTEGER")
        if "tokens_out" not in cols:
            conn.execute("ALTER TABLE token_log ADD COLUMN tokens_out INTEGER")
        cur = conn.execute("SELECT id FROM token_usage WHERE id=1")
        if cur.fetchone() is None:
            conn.execute("INSERT INTO token_usage (id, total) VALUES (1, 0)")
        cur = conn.execute("SELECT id FROM credit WHERE id=1")
        if cur.fetchone() is None:
            conn.execute("INSERT INTO credit (id, balance) VALUES (1, 0)")
        conn.commit()


def add_tokens(
    count: int,
    activity: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> None:
    if count <= 0:
        return
    ts = datetime.now().isoformat(timespec="seconds")
    if activity is None:
        activity = _current_activity
    if tokens_in is not None or tokens_out is not None:
        provider_cost = calculate_ds_cost(0, tokens_in or 0, tokens_out or 0)
    else:
        provider_cost = count / 1_000_000 * DS_COST_PER_MILLION
    client_cost = calculate_client_price(provider_cost)
    with sqlite3.connect(TOKENS_DB) as conn:
        conn.execute(
            "UPDATE token_usage SET total = total + ? WHERE id=1",
            (count,),
        )
        conn.execute(
            "INSERT INTO token_log (timestamp, tokens, tokens_in, tokens_out, activity, cost) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, count, tokens_in, tokens_out, activity, client_cost),
        )
        conn.commit()
    deduct_credit(client_cost)


def get_tokens() -> int:
    with sqlite3.connect(TOKENS_DB) as conn:
        cur = conn.execute("SELECT total FROM token_usage WHERE id=1")
        row = cur.fetchone()
        return row[0] if row else 0


def reset_tokens() -> None:
    with sqlite3.connect(TOKENS_DB) as conn:
        conn.execute("UPDATE token_usage SET total = 0 WHERE id=1")
        conn.execute("DELETE FROM token_log")
        conn.commit()


def get_token_log(
    limit: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    query = "SELECT timestamp, tokens, tokens_in, tokens_out, activity, cost FROM token_log"
    conditions = []
    params: list[str | int] = []
    if start_date is not None:
        conditions.append("date(timestamp) >= date(?)")
        params.append(start_date)
    if end_date is not None:
        conditions.append("date(timestamp) <= date(?)")
        params.append(end_date)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    if isinstance(limit, int):
        query += " LIMIT ?"
        params.append(limit)
    with sqlite3.connect(TOKENS_DB) as conn:
        cur = conn.execute(query, tuple(params))
        return cur.fetchall()[::-1]


def get_token_log_with_id(
    limit: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Return token log entries including the row id."""
    query = "SELECT id, timestamp, tokens, tokens_in, tokens_out, activity, cost FROM token_log"
    conditions = []
    params: list[str | int] = []
    if start_date is not None:
        conditions.append("date(timestamp) >= date(?)")
        params.append(start_date)
    if end_date is not None:
        conditions.append("date(timestamp) <= date(?)")
        params.append(end_date)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    if isinstance(limit, int):
        query += " LIMIT ?"
        params.append(limit)
    with sqlite3.connect(TOKENS_DB) as conn:
        cur = conn.execute(query, tuple(params))
        rows = cur.fetchall()[::-1]

    result = []
    for (row_id, ts, tokens_total, tokens_in, tokens_out, actividad, cost) in rows:
        if tokens_in is not None or tokens_out is not None:
            ds_cost = calculate_ds_cost(0, tokens_in or 0, tokens_out or 0)
        else:
            ds_cost = tokens_total / 1_000_000 * DS_COST_PER_MILLION
        result.append(
            (
                row_id,
                ts,
                tokens_total,
                tokens_in,
                tokens_out,
                actividad,
                cost,
                ds_cost,
            )
        )
    return result


def update_token_activity(row_id: int, activity: str | None) -> None:
    """Update the activity description for a log entry."""
    with sqlite3.connect(TOKENS_DB) as conn:
        conn.execute(
            "UPDATE token_log SET activity=? WHERE id=?",
            (activity, row_id),
        )
        conn.commit()


def calculate_ds_cost(input_hit: int, input_miss: int, output: int) -> float:
    """Return DeepSeek cost in USD for the given token counts."""
    return (
        DS_RATE_INPUT_HIT * input_hit
        + DS_RATE_INPUT_MISS * input_miss
        + DS_RATE_OUTPUT * output
    ) / 1_000_000


def calculate_client_price(cost: float, factor: float | None = None) -> float:
    """Return price to charge the client in USD.

    ``cost`` should be the DeepSeek cost in USD (for example, as returned by
    :func:`calculate_ds_cost`). The price is obtained by multiplying this value
    by ``factor`` which defaults to :data:`CLIENT_PRICE_FACTOR`.
    """
    if factor is None:
        factor = CLIENT_PRICE_FACTOR
    return cost * factor


def calcular_costo(
    tokens_input_hit: int,
    tokens_input_miss: int,
    tokens_output: int,
    factor_cliente: float = 1.0,
) -> tuple[float, float]:
    """Calcular costo del proveedor y precio al cliente en USD.

    ``tokens_input_hit`` y ``tokens_input_miss`` corresponden a los tokens
    de entrada que coincidieron o no con el cache respectivamente, mientras
    ``tokens_output`` representa los tokens de salida. ``factor_cliente``
    es el multiplicador aplicado al costo del proveedor para obtener el
    precio final al cliente.
    """

    millon = 1_000_000
    costo_proveedor = (
        (tokens_input_hit / millon) * DS_RATE_INPUT_HIT
        + (tokens_input_miss / millon) * DS_RATE_INPUT_MISS
        + (tokens_output / millon) * DS_RATE_OUTPUT
    )
    costo_cliente = costo_proveedor * factor_cliente
    return round(costo_proveedor, 4), round(costo_cliente, 4)


def get_token_totals():
    """Return aggregated token counts (total, input, output)."""
    with sqlite3.connect(TOKENS_DB) as conn:
        cur = conn.execute(
            "SELECT SUM(tokens), SUM(tokens_in), SUM(tokens_out) FROM token_log"
        )
        total, t_in, t_out = cur.fetchone()
        return (
            int(total or 0),
            int(t_in or 0),
            int(t_out or 0),
        )


def get_credit() -> float:
    """Return available prepaid balance."""
    with sqlite3.connect(TOKENS_DB) as conn:
        cur = conn.execute("SELECT balance FROM credit WHERE id=1")
        row = cur.fetchone()
        return float(row[0]) if row else 0.0




def deduct_credit(amount: float) -> None:
    """Decrease prepaid balance, preventing negative values."""
    if amount <= 0:
        return
    with sqlite3.connect(TOKENS_DB) as conn:
        cur = conn.execute("SELECT balance FROM credit WHERE id=1")
        row = cur.fetchone()
        balance = float(row[0]) if row else 0.0
        new_balance = balance - float(amount)
        if new_balance < 0:
            new_balance = 0.0
        conn.execute("UPDATE credit SET balance = ? WHERE id=1", (new_balance,))
        conn.commit()


def _read_password_hash() -> str | None:
    if not os.path.exists(PASSWORD_FILE):
        return None
    with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() or None


def set_password(password: str) -> None:
    """Store a hashed password used to authorize credit changes."""
    os.makedirs(DATA_DIR, exist_ok=True)
    import hashlib

    hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        f.write(hashed)


def check_password(password: str) -> bool:
    """Return ``True`` if ``password`` matches the stored hash."""
    hashed = _read_password_hash()
    if hashed is None:
        return True
    import hashlib

    return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed


def add_credit(amount: float, *, password: str | None = None) -> None:
    """Increase prepaid balance by ``amount`` dollars.

    If a password has been configured, ``password`` must match it.
    """
    if amount <= 0:
        return
    hashed = _read_password_hash()
    if hashed is not None:
        if password is None or not check_password(password):
            raise ValueError("Contraseña incorrecta")
    with sqlite3.connect(TOKENS_DB) as conn:
        conn.execute(
            "UPDATE credit SET balance = balance + ? WHERE id=1",
            (float(amount),),
        )
        conn.commit()


def reset_credit(*, password: str | None = None) -> None:
    """Reset prepaid balance to zero."""
    hashed = _read_password_hash()
    if hashed is not None:
        if password is None or not check_password(password):
            raise ValueError("Contraseña incorrecta")
    with sqlite3.connect(TOKENS_DB) as conn:
        conn.execute("UPDATE credit SET balance = 0 WHERE id=1")
        conn.commit()


def generate_credit_file(
    amount: float,
    path: str,
    *,
    email: str | None = None,
    user_id: str | None = None,
) -> None:
    """Generate a simple credit file bound to ``email`` and ``user_id``."""

    if amount <= 0:
        raise ValueError("amount must be positive")
    if email is None:
        email = get_license_email() or ""
    if user_id is None:
        raise ValueError("user_id is required")

    import uuid

    data = {
        "correo": normalize_identifier(email),
        "saldo": float(amount),
        "id": user_id,
        "uid": uuid.uuid4().hex,
    }

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def add_credit_from_file(path: str, *, email: str | None = None) -> float:
    """Import a credit file and add the contained amount if valid for this user."""

    if email is None:
        email = get_license_email() or ""

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Simple credit file format
    if "saldo" in data and "correo" in data and "uid" in data:
        amount = float(data.get("saldo", 0))
        if amount <= 0:
            raise ValueError("Archivo de crédito inválido")
        if normalize_identifier(data.get("correo", "")) != normalize_identifier(email):
            raise ValueError("Archivo asignado a otro usuario")
        uid = str(data.get("uid"))
        with sqlite3.connect(TOKENS_DB) as conn:
            cur = conn.execute(
                "SELECT 1 FROM used_credit_files WHERE uid=?",
                (uid,),
            )
            if cur.fetchone() is not None:
                raise ValueError("Archivo de crédito ya utilizado")
            conn.execute(
                "INSERT INTO used_credit_files (uid) VALUES (?)",
                (uid,),
            )
            conn.execute(
                "UPDATE credit SET balance = balance + ? WHERE id=1",
                (amount,),
            )
            conn.commit()
        return amount

    raise ValueError("Archivo de crédito inválido")
