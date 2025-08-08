import os
import shutil
import tempfile
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


class AgregarPdfACasoTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.p_vector = mock.patch.object(dem, "VECTOR_DB_CASOS", self.tmp_vector)
        self.p_mem = mock.patch.object(dem, "ChatMessageHistory", lambda *a, **k: object())
        self.p_root.start()
        self.p_vector.start()
        self.p_mem.start()
        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.p_root.stop()
        self.p_vector.stop()
        self.p_mem.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)
        self.ctx.vectorstores_por_caso.clear()
        self.ctx.memories_por_caso.clear()

    def _create_pdf(self, path):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_agregar_pdf_a_caso(self):
        src_dir = tempfile.mkdtemp()
        src_pdf = os.path.join(src_dir, "file.pdf")
        self._create_pdf(src_pdf)

        with mock.patch.object(dem.db, "get_caso_id_by_nombre", return_value=1), \
             mock.patch.object(dem.db, "get_emails_by_caso", return_value=[(1, "n", "r", "a", "f", "body")]), \
             mock.patch.object(dem, "build_or_load_vectorstore", return_value="VS") as mock_build:
            msg = dem.agregar_pdf_a_caso(src_pdf, "Caso1", self.ctx)

        self.assertIn("agregado", msg)
        dest = os.path.join(self.tmp_root, "Caso1", "file.pdf")
        self.assertTrue(os.path.exists(dest))
        mock_build.assert_called_once()
        args, kwargs = mock_build.call_args
        self.assertEqual(args[0], os.path.join(self.tmp_root, "Caso1"))
        self.assertEqual(args[1], os.path.join(self.tmp_vector, "Caso1"))
        self.assertTrue(kwargs.get("force_rebuild"))
        self.assertIsNotNone(kwargs.get("extra_docs"))
        self.assertIn("Caso1", self.ctx.vectorstores_por_caso)
        shutil.rmtree(src_dir, ignore_errors=True)
