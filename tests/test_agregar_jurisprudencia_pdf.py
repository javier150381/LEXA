import os
import shutil
import tempfile
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


class AgregarJurisprudenciaPdfTests(TestCase):
    def setUp(self):
        self.tmp_juris = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.patch_juris = mock.patch.object(dem, "JURIS_DIR", self.tmp_juris)
        self.patch_vector = mock.patch.object(dem, "VECTOR_DB_JURIS", self.tmp_vector)
        self.patch_juris.start()
        self.patch_vector.start()
        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.patch_juris.stop()
        self.patch_vector.stop()
        shutil.rmtree(self.tmp_juris, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)

    def _create_pdf(self, path):
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_agregar_jurisprudencia_pdf(self):
        src_dir = tempfile.mkdtemp()
        src_pdf = os.path.join(src_dir, "j.pdf")
        self._create_pdf(src_pdf)

        class DummyVS:
            def __init__(self):
                self.docstore = type("DS", (), {"_dict": {}})()

        with mock.patch.object(dem, "build_or_load_vectorstore", return_value=DummyVS()) as mock_build:
            msg = dem.agregar_jurisprudencia_pdf(src_pdf, self.ctx)

        self.assertIn("agregada", msg)
        self.assertTrue(os.path.exists(os.path.join(self.tmp_juris, "j.pdf")))
        mock_build.assert_called_once()
        args, kwargs = mock_build.call_args
        self.assertEqual(args[0], self.tmp_juris)
        self.assertEqual(args[1], self.tmp_vector)
        self.assertTrue(kwargs.get("force_rebuild"))
        shutil.rmtree(src_dir, ignore_errors=True)

