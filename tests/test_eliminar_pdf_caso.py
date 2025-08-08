import os
import shutil
import tempfile
from unittest import TestCase, mock

from pypdf import PdfWriter

import lib.demandas as dem


class EliminarPdfCasoTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.p_vector = mock.patch.object(dem, "VECTOR_DB_CASOS", self.tmp_vector)
        self.p_mem = mock.patch.object(dem, "ChatMessageHistory", lambda *a, **k: object())
        self.p_root.start()
        self.p_vector.start()
        self.p_mem.start()

    def tearDown(self):
        self.p_root.stop()
        self.p_vector.stop()
        self.p_mem.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)

    def _create_pdf(self, path):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_eliminar_pdf_sin_restantes(self):
        case_folder = os.path.join(self.tmp_root, "case")
        os.makedirs(case_folder)
        pdf_path = os.path.join(case_folder, "a.pdf")
        self._create_pdf(pdf_path)
        os.makedirs(os.path.join(self.tmp_vector, "case"))
        ctx = dem.DemandasContext()
        ctx.vectorstores_por_caso["case"] = "VS"
        ctx.memories_por_caso["case"] = "MEM"
        ctx.datos_basicos_casos["case"] = {"NOMBRE": "X"}

        msg = dem.eliminar_pdf_de_caso("a.pdf", "case", ctx)
        self.assertIn("eliminado", msg)
        self.assertFalse(os.path.exists(pdf_path))
        self.assertNotIn("case", ctx.vectorstores_por_caso)
        self.assertFalse(os.path.isdir(os.path.join(self.tmp_vector, "case")))

    def test_eliminar_pdf_con_restantes(self):
        case_folder = os.path.join(self.tmp_root, "case")
        os.makedirs(case_folder)
        pdf_a = os.path.join(case_folder, "a.pdf")
        pdf_b = os.path.join(case_folder, "b.pdf")
        self._create_pdf(pdf_a)
        self._create_pdf(pdf_b)
        ctx = dem.DemandasContext()
        with mock.patch.object(dem, "load_email_docs", return_value=[]), \
             mock.patch.object(dem, "build_or_load_vectorstore", return_value="VS2") as mock_build:
            msg = dem.eliminar_pdf_de_caso("a.pdf", "case", ctx)
        self.assertTrue(os.path.exists(pdf_b))
        self.assertIn("eliminado", msg)
        mock_build.assert_called_once()
        self.assertEqual(ctx.vectorstores_por_caso["case"], "VS2")
