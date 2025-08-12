import pytest

from lib.corrector import corregir

language_tool_python = pytest.importorskip("language_tool_python")


def test_corregir_sugiere_went():
    resultados = corregir("I goed to the store yesterday.")
    assert any("went" in sugerencia["sugerencias"] for sugerencia in resultados)
