import os
import shutil
import tempfile
from unittest import TestCase, mock

from pypdf import PdfWriter

import lib.demandas as dem


class ListarPdfsCasoTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.p_root.start()

    def tearDown(self):
        self.p_root.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _create_pdf(self, path):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_listar(self):
        case = os.path.join(self.tmp_root, "c")
        os.makedirs(os.path.join(case, "sub"), exist_ok=True)
        self._create_pdf(os.path.join(case, "a.pdf"))
        self._create_pdf(os.path.join(case, "sub", "b.pdf"))
        with open(os.path.join(case, "nota.txt"), "w") as fh:
            fh.write("hola")
        archivos = dem.listar_pdfs_de_caso("c")
        self.assertEqual(
            sorted(archivos),
            ["a.pdf", "nota.txt", os.path.join("sub", "b.pdf")],
        )
