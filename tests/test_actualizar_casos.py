import os
import shutil
import glob
import tempfile
from unittest import TestCase, mock

import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem

class DummyVS(str):
    pass

class ActualizarCasosTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        # Patch paths
        self.patcher_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.patcher_vector = mock.patch.object(dem, "VECTOR_DB_CASOS", self.tmp_vector)
        self.patcher_root.start()
        self.patcher_vector.start()
        # Patch ChatMessageHistory to avoid warnings
        self.patcher_mem = mock.patch.object(dem, "ChatMessageHistory", lambda *a, **k: object())
        self.patcher_mem.start()

        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.patcher_root.stop()
        self.patcher_vector.stop()
        self.patcher_mem.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)
        self.ctx.vectorstores_por_caso.clear()
        self.ctx.memories_por_caso.clear()

    def _write_pdf(self, folder, name="doc.pdf"):
        from pypdf import PdfWriter
        os.makedirs(folder, exist_ok=True)
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(os.path.join(folder, name), "wb") as f:
            writer.write(f)

    def test_actualizar_casos_skips_empty_folders(self):
        valid = os.path.join(self.tmp_root, "valid")
        empty = os.path.join(self.tmp_root, "empty")
        os.makedirs(empty)
        self._write_pdf(valid)

        def fake_build(path_docs, path_vector, force_rebuild=False, extra_docs=None):
            pdfs = glob.glob(os.path.join(path_docs, "**", "*.pdf"), recursive=True)
            if not pdfs:
                raise ValueError("❌ No se encontraron documentos PDF en '{path_docs}'.")
            self.assertIsNotNone(extra_docs)
            return DummyVS(os.path.basename(path_docs))

        with mock.patch.object(dem.db, "get_caso_id_by_nombre", return_value=1), \
             mock.patch.object(dem.db, "get_emails_by_caso", return_value=[(1,"n","r","a","f","body")]), \
             mock.patch.object(dem, "build_or_load_vectorstore", side_effect=fake_build):
            msg = dem.actualizar_casos(self.ctx)

        self.assertIn("valid", self.ctx.vectorstores_por_caso)
        self.assertNotIn("empty", self.ctx.vectorstores_por_caso)
        self.assertIn("empty", msg)

    def test_actualizar_casos_only_valid(self):
        valid = os.path.join(self.tmp_root, "case1")
        self._write_pdf(valid)

        def fake_build(path_docs, path_vector, force_rebuild=False, extra_docs=None):
            pdfs = glob.glob(os.path.join(path_docs, "**", "*.pdf"), recursive=True)
            if not pdfs:
                raise ValueError("❌ No se encontraron documentos PDF en '{path_docs}'.")
            self.assertIsNotNone(extra_docs)
            return DummyVS(os.path.basename(path_docs))

        with mock.patch.object(dem.db, "get_caso_id_by_nombre", return_value=1), \
             mock.patch.object(dem.db, "get_emails_by_caso", return_value=[(1,"n","r","a","f","body")]), \
             mock.patch.object(dem, "build_or_load_vectorstore", side_effect=fake_build):
            msg = dem.actualizar_casos(self.ctx)

        self.assertIn("case1", self.ctx.vectorstores_por_caso)
        self.assertNotIn("omitidas", msg)
