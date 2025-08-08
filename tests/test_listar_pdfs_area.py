import os
import shutil
import tempfile
from unittest import TestCase, mock

from pypdf import PdfWriter

import lib.demandas as dem

class ListarPdfsAreaTests(TestCase):
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

    def test_listar_area(self):
        area = os.path.join(self.tmp_root, "area1")
        os.makedirs(os.path.join(area, "sub"), exist_ok=True)
        self._create_pdf(os.path.join(area, "a.pdf"))
        self._create_pdf(os.path.join(area, "sub", "b.pdf"))
        with open(os.path.join(area, "nota.txt"), "w") as fh:
            fh.write("x")
        archivos = dem.listar_pdfs_de_area("area1")
        self.assertEqual(
            sorted(archivos),
            ["a.pdf", "nota.txt", os.path.join("sub", "b.pdf")],
        )
