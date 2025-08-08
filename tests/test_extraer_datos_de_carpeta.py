import os
import tempfile
from types import SimpleNamespace
from unittest import mock
from pypdf import PdfWriter

from lib.demandas import extraer_datos_de_carpeta


def test_extraer_datos_de_carpeta_recursive():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub = os.path.join(tmpdir, "sub")
        os.makedirs(sub, exist_ok=True)
        pdf_path = os.path.join(sub, "doc.pdf")
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(pdf_path, "wb") as fh:
            writer.write(fh)

        texto = (
            "JUAN PEREZ, de nacionalidad ecuatoriana con cédula 1234567890, "
            "de 30 años de edad."
        )

        def dummy_loader(*a, **k):
            def _load():
                return [SimpleNamespace(page_content=texto)]

            return SimpleNamespace(load=_load)

        with mock.patch("lib.demandas.PyPDFLoader", dummy_loader), \
             mock.patch("lib.demandas.extraer_datos_por_llm", return_value={}), \
             mock.patch("lib.demandas._es_pdf_escaneado", return_value=False):
            datos = extraer_datos_de_carpeta(tmpdir)

        assert datos == {"NOMBRE": "Juan Perez", "CEDULA": "1234567890", "EDAD": "30"}
