import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest import TestCase, mock
from pypdf import PdfWriter

import lib.demandas as dem

class LeerTextoPdfCacheTests(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.pdf_path = os.path.join(self.tmp_dir, "doc.pdf")
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(self.pdf_path, "wb") as f:
            writer.write(f)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _loader(self, *a, **k):
        return SimpleNamespace(load=lambda: [SimpleNamespace(page_content="TXT")])

    def test_uses_cache_file(self):
        with mock.patch.object(dem, "_es_pdf_escaneado", return_value=False), \
             mock.patch.object(dem, "PyPDFLoader", self._loader), \
             mock.patch.object(dem, "_ocr_pdf", return_value=""):
            texto = dem.leer_texto_pdf("doc.pdf", carpeta=self.tmp_dir)
        self.assertEqual(texto, "TXT")
        cache = os.path.join(self.tmp_dir, "doc.txt")
        self.assertTrue(os.path.exists(cache))
        with mock.patch.object(dem, "PyPDFLoader") as m_loader, \
             mock.patch.object(dem, "_ocr_pdf") as m_ocr, \
             mock.patch.object(dem, "_es_pdf_escaneado") as m_scan:
            texto2 = dem.leer_texto_pdf("doc.pdf", carpeta=self.tmp_dir)
        self.assertEqual(texto2, "TXT")
        m_loader.assert_not_called()
        m_ocr.assert_not_called()
        m_scan.assert_not_called()
