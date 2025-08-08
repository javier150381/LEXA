import os
from unittest import mock
from docx import Document

import lib.demandas as dem


def test_exportar_a_word_strips_control_chars(tmp_path):
    # incluye caracteres de control de los rangos C0 (\x0c) y C1 (\x85)
    texto = "Hola\x0cMundo\x85\nSegunda linea"
    dest = tmp_path / "out.docx"
    dummy_mb = mock.Mock()
    with mock.patch.object(dem, "messagebox", dummy_mb):
        dem.exportar_a_word(texto, str(dest))
    assert dest.exists()
    doc = Document(str(dest))
    contenido = [p.text for p in doc.paragraphs]
    assert contenido == ["HolaMundo", "Segunda linea"]
