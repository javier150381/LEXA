import os
import shutil
import tempfile
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


class GuardarPdfEnCasoTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.p_root.start()

    def tearDown(self):
        self.p_root.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _create_pdf(self, path):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_guardar_pdf_en_caso(self):
        src_dir = tempfile.mkdtemp()
        src_pdf = os.path.join(src_dir, "doc.pdf")
        self._create_pdf(src_pdf)

        with mock.patch.object(dem, "build_or_load_vectorstore") as mock_build:
            msg = dem.guardar_pdf_en_caso(src_pdf, "Caso1")

        self.assertIn("guardado", msg)
        dest = os.path.join(self.tmp_root, "Caso1", "doc.pdf")
        self.assertTrue(os.path.exists(dest))
        mock_build.assert_not_called()
        shutil.rmtree(src_dir, ignore_errors=True)
