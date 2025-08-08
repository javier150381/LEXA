import os
import pytest
import lib.demandas as dem
from lib import tokens


def test_get_llm_fails_without_credit(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    monkeypatch.setattr(tokens, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tokens, "TOKENS_DB", tmp_path / "tokens.db")
    tokens.init_db()
    dem._llm = None
    with pytest.raises(ValueError):
        dem.get_llm()
