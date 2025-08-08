import os
import shutil
import tempfile
from unittest import TestCase, mock
from langchain_community.chat_models.fake import FakeListChatModel

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


class AgregarDemandaPdfTests(TestCase):
    def setUp(self):
        self.tmp_dem = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.patch_dem = mock.patch.object(dem, "DEMANDAS_DIR", self.tmp_dem)
        self.patch_vector = mock.patch.object(dem, "VECTOR_DB_DEMANDAS", self.tmp_vector)
        self.patch_dem.start()
        self.patch_vector.start()
        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.patch_dem.stop()
        self.patch_vector.stop()
        shutil.rmtree(self.tmp_dem, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)

    def _create_pdf(self, path):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_agregar_demanda_pdf(self):
        src_dir = tempfile.mkdtemp()
        src_pdf = os.path.join(src_dir, "d.pdf")
        self._create_pdf(src_pdf)

        fake_llm = FakeListChatModel(responses=["{}"])
        with mock.patch.object(dem, "build_or_load_vectorstore", return_value="VS") as mock_build, \
             mock.patch.object(dem, "get_llm", return_value=fake_llm):
            msg = dem.agregar_demanda_pdf(src_pdf, self.ctx)

        self.assertIn("agregada", msg)
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dem, "d.pdf")))
        mock_build.assert_called_once()
        args, kwargs = mock_build.call_args
        self.assertEqual(args[0], self.tmp_dem)
        self.assertEqual(args[1], self.tmp_vector)
        self.assertTrue(kwargs.get("force_rebuild"))
        shutil.rmtree(src_dir, ignore_errors=True)
