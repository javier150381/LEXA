import os
from unittest import mock
from pypdf import PdfReader

import lib.demandas as dem


def test_exportar_a_pdf_strips_control_chars(tmp_path):
    texto = "Hola\x0cMundo\x85\nSegunda linea"
    dest = tmp_path / "out.pdf"
    dummy_mb = mock.Mock()
    with mock.patch.object(dem, "messagebox", dummy_mb):
        dem.exportar_a_pdf(texto, str(dest))
    assert dest.exists()
    reader = PdfReader(str(dest))
    contenido = reader.pages[0].extract_text()
    assert "HolaMundo" in contenido
    assert "Segunda linea" in contenido
