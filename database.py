import os
import sqlite3
from typing import List, Optional, Tuple
from langchain.schema import Document

# Default path for the SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")


def connect() -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create database tables if they do not exist and run migrations."""
    conn = connect()
    cur = conn.cursor()
    # Create base tables
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cedula TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS casos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            nombre TEXT,
            descripcion TEXT,
            FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE SET NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audiencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caso_id INTEGER,
            fecha TEXT,
            descripcion TEXT,
            FOREIGN KEY(caso_id) REFERENCES casos(id) ON DELETE CASCADE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caso_id INTEGER,
            nombre TEXT,
            remite TEXT,
            asunto TEXT,
            fecha TEXT,
            cuerpo TEXT,
            FOREIGN KEY(caso_id) REFERENCES casos(id) ON DELETE CASCADE
        )
        """
    )
    # Migration: ensure "nombre" column exists in emails
    cur.execute("PRAGMA table_info(emails)")
    cols = [r[1] for r in cur.fetchall()]
    if "nombre" not in cols:
        cur.execute("ALTER TABLE emails ADD COLUMN nombre TEXT")
    conn.commit()
    conn.close()


def add_cliente(nombre: str, cedula: str) -> int:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clientes (nombre, cedula) VALUES (?, ?)", (nombre, cedula)
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def get_clientes() -> List[Tuple[int, str, str]]:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, cedula FROM clientes")
    rows = cur.fetchall()
    conn.close()
    return rows


def update_cliente(cliente_id: int, nombre: str, cedula: str) -> None:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE clientes SET nombre = ?, cedula = ? WHERE id = ?",
        (nombre, cedula, cliente_id),
    )
    conn.commit()
    conn.close()


def add_caso(cliente_id: Optional[int], nombre: str, descripcion: str) -> int:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO casos (cliente_id, nombre, descripcion) VALUES (?, ?, ?)",
        (cliente_id, nombre, descripcion),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def update_caso(caso_id: int, cliente_id: Optional[int], nombre: str, descripcion: str) -> None:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE casos SET cliente_id = ?, nombre = ?, descripcion = ? WHERE id = ?",
        (cliente_id, nombre, descripcion, caso_id),
    )
    conn.commit()
    conn.close()


def get_casos() -> List[Tuple[int, Optional[int], str, str]]:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, cliente_id, nombre, descripcion FROM casos")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_caso_id_by_nombre(nombre: str) -> Optional[int]:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM casos WHERE nombre = ?", (nombre,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def add_audiencia(caso_id: Optional[int], fecha: str, descripcion: str) -> int:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audiencias (caso_id, fecha, descripcion) VALUES (?, ?, ?)",
        (caso_id, fecha, descripcion),
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def update_audiencia(audiencia_id: int, caso_id: Optional[int], fecha: str, descripcion: str) -> None:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE audiencias SET caso_id = ?, fecha = ?, descripcion = ? WHERE id = ?",
        (caso_id, fecha, descripcion, audiencia_id),
    )
    conn.commit()
    conn.close()


def get_audiencias() -> List[Tuple[int, Optional[int], str, str]]:
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, caso_id, fecha, descripcion FROM audiencias")
    rows = cur.fetchall()
    conn.close()
    return rows


def add_caso_if_missing(nombre: str) -> int:
    """Add a case if it does not exist and return its ID."""
    cid = get_caso_id_by_nombre(nombre)
    if cid is not None:
        return cid
    return add_caso(None, nombre, "")


def add_email(
    caso_id: int,
    remite: str,
    asunto: str,
    fecha: str,
    cuerpo: str,
    nombre: str,
) -> int:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO emails (caso_id, nombre, remite, asunto, fecha, cuerpo)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (caso_id, nombre, remite, asunto, fecha, cuerpo),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def get_emails_by_caso(caso_id: int) -> List[Tuple[int, str, str, str, str, str]]:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nombre, remite, asunto, fecha, cuerpo FROM emails WHERE caso_id = ?",
        (caso_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_email_documents(caso_id: int) -> List[Document]:
    docs = []
    for row in get_emails_by_caso(caso_id):
        eid, nombre, remite, asunto, fecha, cuerpo = row
        metadata = {
            "id": eid,
            "nombre": nombre,
            "remite": remite,
            "asunto": asunto,
            "fecha": fecha,
        }
        docs.append(Document(page_content=cuerpo, metadata=metadata))
    return docs


def sync_casos_from_fs() -> None:
    """Sync cases from filesystem directories into the database."""
    from lib import demandas as dem  # Local import to avoid circular dependency

    casos_root = dem.CASOS_DIR_ROOT
    if not os.path.isdir(casos_root):
        return
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM casos")
    existentes = {row[0] for row in cur.fetchall()}
    for nombre in os.listdir(casos_root):
        path = os.path.join(casos_root, nombre)
        if os.path.isdir(path) and nombre not in existentes:
            cur.execute(
                "INSERT INTO casos (cliente_id, nombre, descripcion) VALUES (?, ?, ?)",
                (None, nombre, ""),
            )
    conn.commit()
    conn.close()

