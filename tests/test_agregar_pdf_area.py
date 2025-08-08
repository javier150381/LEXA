import os
import shutil
import tempfile
from unittest import TestCase, mock

from pypdf import PdfWriter

import lib.demandas as dem

class AgregarPdfAreaTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "AREAS_DIR_ROOT", self.tmp_root)
        self.p_ctx = mock.patch.object(dem.default_context, "ruta_areas_root", self.tmp_root)
        self.p_root.start()
        self.p_ctx.start()

    def tearDown(self):
        self.p_root.stop()
        self.p_ctx.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _create_pdf(self, path):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_agregar_pdf_area(self):
        src_dir = tempfile.mkdtemp()
        src_pdf = os.path.join(src_dir, "file.pdf")
        self._create_pdf(src_pdf)

        msg = dem.agregar_pdf_a_area(src_pdf, "a")
        dest = os.path.join(self.tmp_root, "a", "file.pdf")
        self.assertTrue(os.path.exists(dest))
        self.assertIn("agregado", msg)
        shutil.rmtree(src_dir, ignore_errors=True)
