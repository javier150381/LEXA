import os
import shutil
import tempfile
from unittest import TestCase, mock

from pypdf import PdfWriter

import lib.demandas as dem

class EliminarDemandaPdfTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "DEMANDAS_DIR", self.tmp_root)
        self.p_vector = mock.patch.object(dem, "VECTOR_DB_DEMANDAS", self.tmp_vector)
        self.p_root.start()
        self.p_vector.start()

    def tearDown(self):
        self.p_root.stop()
        self.p_vector.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)

    def _create_pdf(self, path):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_eliminar_demanda_pdf(self):
        sub = os.path.join(self.tmp_root, "sub")
        os.makedirs(sub)
        pdf = os.path.join(sub, "doc.pdf")
        self._create_pdf(pdf)
        os.makedirs(self.tmp_vector, exist_ok=True)
        ctx = dem.DemandasContext()
        ctx.demandas_vectorstore = "VS"
        ctx.demandas_textos = {"sub/doc.pdf": "X"}
        ctx.datos_basicos_demandas = {"sub/doc.pdf": {"N": "A"}}

        msg = dem.eliminar_demanda_pdf("sub/doc.pdf", ctx)
        self.assertFalse(os.path.exists(pdf))
        self.assertIn("eliminado", msg)
        self.assertIsNone(ctx.demandas_vectorstore)
        self.assertEqual(ctx.demandas_textos, {})
        self.assertEqual(ctx.datos_basicos_demandas, {})
        self.assertFalse(os.path.isdir(self.tmp_vector))
