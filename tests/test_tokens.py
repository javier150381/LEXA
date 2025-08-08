import os
import sqlite3
import json
import pytest
import lib.tokens as tokens

def test_token_log(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    assert tokens.get_tokens() == 0
    tokens.add_tokens(5, "A")
    tokens.add_tokens(3, "B")
    assert tokens.get_tokens() == 8
    log = tokens.get_token_log()
    assert len(log) == 2
    ts, count, tokens_in, tokens_out, actividad, costo = log[-1]
    assert count == 3
    assert actividad == "B"
    assert tokens_in is None
    assert tokens_out is None
    assert costo > 0


def test_activity_context(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    with tokens.activity("X"):
        tokens.add_tokens(2)
    tokens.add_tokens(1)
    log = tokens.get_token_log()
    assert len(log) == 2
    assert log[0][4] == "X"
    assert log[1][4] is None


def test_update_token_activity(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    tokens.add_tokens(1, "A")
    row = tokens.get_token_log_with_id()[-1]
    row_id = row[0]
    tokens.update_token_activity(row_id, "B")
    log = tokens.get_token_log_with_id()
    assert log[-1][5] == "B"


def test_get_token_log_with_cost(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    tokens.add_tokens(1_000_000)
    row = tokens.get_token_log_with_id()[-1]
    ds_cost_expected = tokens.DS_COST_PER_MILLION
    client_cost_expected = tokens.calculate_client_price(ds_cost_expected)
    assert row[6] == pytest.approx(client_cost_expected, rel=1e-6)
    assert row[7] == pytest.approx(ds_cost_expected, rel=1e-6)


def test_calculate_ds_cost_and_client_price():
    costo = tokens.calculate_ds_cost(4064064, 1096710, 171240)
    assert costo == pytest.approx(0.50872068, rel=1e-6)
    precio = tokens.calculate_client_price(costo)
    assert precio == pytest.approx(2.03488272, rel=1e-6)


def test_calcular_costo():
    prov, cli = tokens.calcular_costo(4064064, 1096710, 171240, factor_cliente=3.0)
    costo = tokens.calculate_ds_cost(4064064, 1096710, 171240)
    assert prov == round(costo, 4)
    assert cli == round(costo * 3.0, 4)


def test_get_token_totals(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    tokens.add_tokens(10, tokens_in=6, tokens_out=4)
    tokens.add_tokens(5, tokens_in=3, tokens_out=2)
    total, t_in, t_out = tokens.get_token_totals()
    assert total == 15
    assert t_in == 9
    assert t_out == 6


def test_add_credit(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    assert tokens.get_credit() == 0
    tokens.add_credit(5.0)
    assert tokens.get_credit() == pytest.approx(5.0)


def test_credit_deduction(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    tokens.add_credit(10.0)
    tokens.add_tokens(1_000_000)
    expected = 10.0 - tokens.calculate_client_price(tokens.DS_COST_PER_MILLION)
    assert tokens.get_credit() == pytest.approx(expected, rel=1e-6)


def test_get_token_log_date_range(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()

    from datetime import datetime as real_datetime

    class DummyDateTime:
        queue = []

        @classmethod
        def now(cls):
            return cls.queue.pop(0)

    monkeypatch.setattr(tokens, "datetime", DummyDateTime)

    DummyDateTime.queue = [
        real_datetime(2023, 1, 1, 12, 0, 0),
        real_datetime(2023, 1, 2, 12, 0, 0),
        real_datetime(2023, 1, 3, 12, 0, 0),
    ]

    tokens.add_tokens(1, "A")
    tokens.add_tokens(1, "B")
    tokens.add_tokens(1, "C")

    log = tokens.get_token_log(start_date="2023-01-02", end_date="2023-01-03")
    assert len(log) == 2
    actividades = [row[4] for row in log]
    assert actividades == ["B", "C"]


def test_password(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    monkeypatch.setattr(tokens, "PASSWORD_FILE", tmp_path / "pwd")
    tokens.init_db()
    tokens.set_password("secret")
    with pytest.raises(ValueError):
        tokens.add_credit(1.0, password="bad")
    tokens.add_credit(1.0, password="secret")
    assert tokens.get_credit() == pytest.approx(1.0)


def test_credit_file(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    file_path = tmp_path / "cred.json"
    tokens.generate_credit_file(2.5, file_path, email="a@b.com", user_id="id1")
    tokens.add_credit_from_file(file_path, email="a@b.com")
    assert tokens.get_credit() == pytest.approx(2.5)


def test_credit_file_reuse(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    file_path = tmp_path / "cred.json"
    tokens.generate_credit_file(1.0, file_path, email="a@b.com", user_id="id1")
    tokens.add_credit_from_file(file_path, email="a@b.com")
    with pytest.raises(ValueError):
        tokens.add_credit_from_file(file_path, email="a@b.com")


def test_credit_file_wrong_user(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    file_path = tmp_path / "cred.json"
    tokens.generate_credit_file(2.5, file_path, email="a@b.com", user_id="id1")
    with pytest.raises(ValueError):
        tokens.add_credit_from_file(file_path, email="x@y.com")


def test_create_user_id():
    ts1 = "2024-05-05T12:00:00"
    ts2 = "2024-05-05T12:30:00"
    uid1 = tokens.create_user_id("test@example.com", ts1)
    uid2 = tokens.create_user_id("TEST@example.com", ts1)
    uid3 = tokens.create_user_id("test@example.com", ts2)
    assert uid1 == uid2
    assert uid1 != uid3
    import hashlib
    expected = hashlib.sha256(b"test@example.com:2024-05-05T12:00:00").hexdigest()
    assert uid1 == expected


def test_create_credit_id():
    id1 = tokens.create_credit_id("User@Example.com", 1.0)
    id2 = tokens.create_credit_id("user@example.com", 1.0)
    id3 = tokens.create_credit_id("user@example.com", 2.0)
    assert id1 == id2
    assert id1 != id3
    import hashlib
    expected = hashlib.sha256(b"user@example.com:1.00").hexdigest()
    assert id1 == expected


def test_reset_credit(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    monkeypatch.setattr(tokens, "PASSWORD_FILE", tmp_path / "pwd")
    tokens.init_db()
    tokens.set_password("secret")
    tokens.add_credit(5.0, password="secret")
    assert tokens.get_credit() == pytest.approx(5.0)
    tokens.reset_credit(password="secret")
    assert tokens.get_credit() == pytest.approx(0.0)


def test_reset_credit_wrong_password(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    monkeypatch.setattr(tokens, "PASSWORD_FILE", tmp_path / "pwd")
    tokens.init_db()
    tokens.set_password("secret")
    tokens.add_credit(5.0, password="secret")
    with pytest.raises(ValueError):
        tokens.reset_credit(password="bad")




def test_credit_file_expired(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    file_path = tmp_path / "cred.json"
    # create invalid credit file with zero balance
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"correo": "a@b.com", "saldo": 0}, f)
    with pytest.raises(ValueError):
        tokens.add_credit_from_file(file_path, email="a@b.com")



def test_add_credit_uses_config_email(monkeypatch, tmp_path):
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    file_path = tmp_path / "cred.json"
    tokens.generate_credit_file(1.0, file_path, email="a@b.com", user_id="id1")

    monkeypatch.setattr(tokens, "get_license_email", lambda: "a@b.com")

    tokens.add_credit_from_file(file_path)
    assert tokens.get_credit() == pytest.approx(1.0)
