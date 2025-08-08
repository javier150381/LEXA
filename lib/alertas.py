import os
import sqlite3
from datetime import datetime

from .demandas import ALERTAS_DB, DATA_DIR


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(ALERTAS_DB) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS alertas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "fecha TEXT NOT NULL,"
            "descripcion TEXT NOT NULL"
            ")"
        )
        conn.commit()


def add_alerta(fecha: str, descripcion: str) -> None:
    with sqlite3.connect(ALERTAS_DB) as conn:
        conn.execute(
            "INSERT INTO alertas (fecha, descripcion) VALUES (?, ?)",
            (fecha, descripcion),
        )
        conn.commit()


def delete_alerta(alerta_id: int) -> None:
    with sqlite3.connect(ALERTAS_DB) as conn:
        conn.execute("DELETE FROM alertas WHERE id = ?", (alerta_id,))
        conn.commit()


def get_alertas_desde(fecha_inicio: datetime, limite: int = 10):
    with sqlite3.connect(ALERTAS_DB) as conn:
        cur = conn.execute(
            "SELECT id, fecha, descripcion FROM alertas "
            "WHERE fecha >= ? ORDER BY fecha LIMIT ?",
            (fecha_inicio.isoformat(), limite),
        )
        return cur.fetchall()


def get_alertas_entre(inicio: datetime, fin: datetime):
    with sqlite3.connect(ALERTAS_DB) as conn:
        cur = conn.execute(
            "SELECT id, fecha, descripcion FROM alertas "
            "WHERE fecha BETWEEN ? AND ? ORDER BY fecha",
            (inicio.isoformat(), fin.isoformat()),
        )
        return cur.fetchall()
