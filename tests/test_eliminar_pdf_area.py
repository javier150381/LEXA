import os
import shutil
import tempfile
from unittest import TestCase, mock

from pypdf import PdfWriter

import lib.demandas as dem

class EliminarPdfAreaTests(TestCase):
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

    def test_eliminar_pdf_area(self):
        area = os.path.join(self.tmp_root, "a")
        os.makedirs(area)
        pdf = os.path.join(area, "doc.pdf")
        self._create_pdf(pdf)
        msg = dem.eliminar_pdf_de_area("doc.pdf", "a")
        self.assertFalse(os.path.exists(pdf))
        self.assertIn("eliminado", msg)
