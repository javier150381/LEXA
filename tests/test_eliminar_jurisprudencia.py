import os
import tempfile
import shutil
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem

class EliminarJurisprudenciaTests(TestCase):
    def setUp(self):
        self.tmp_juris = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.tmp_cfg_dir = tempfile.mkdtemp()
        self.tmp_cfg = os.path.join(self.tmp_cfg_dir, "config.json")

        self.p_juris = mock.patch.object(dem, "JURIS_DIR", self.tmp_juris)
        self.p_vector = mock.patch.object(dem, "VECTOR_DB_JURIS", self.tmp_vector)
        self.p_config = mock.patch.object(dem, "CONFIG_PATH", self.tmp_cfg)
        self.p_juris.start()
        self.p_vector.start()
        self.p_config.start()

        # prepare dummy files
        os.makedirs(self.tmp_juris, exist_ok=True)
        with open(os.path.join(self.tmp_juris, "file.pdf"), "w") as fh:
            fh.write("x")
        os.makedirs(self.tmp_vector, exist_ok=True)
        with open(os.path.join(self.tmp_vector, "index.faiss"), "w") as fh:
            fh.write("x")

        self.ctx = dem.DemandasContext()
        self.ctx.config_global = {"juris_path": self.tmp_juris}
        self.ctx.ruta_juris = self.tmp_juris
        self.ctx.juris_vectorstore = "dummy"

    def tearDown(self):
        self.p_juris.stop()
        self.p_vector.stop()
        self.p_config.stop()
        shutil.rmtree(self.tmp_juris, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)
        shutil.rmtree(self.tmp_cfg_dir, ignore_errors=True)
        self.ctx.juris_vectorstore = None
        self.ctx.ruta_juris = ""
        self.ctx.config_global = {}

    def test_eliminar_jurisprudencia(self):
        msg = dem.eliminar_jurisprudencia(self.ctx)
        self.assertIn("eliminada", msg)
        self.assertEqual(self.ctx.juris_vectorstore, None)
        self.assertEqual(self.ctx.ruta_juris, "")
        self.assertEqual(self.ctx.config_global.get("juris_path"), "")
        self.assertEqual(os.listdir(self.tmp_juris), [])
        self.assertEqual(os.listdir(self.tmp_vector), [])

