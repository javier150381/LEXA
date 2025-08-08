import os
import shutil
import tempfile
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


class EliminarDemandasTests(TestCase):
    def setUp(self):
        self.tmp_dem = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.tmp_cfg_dir = tempfile.mkdtemp()
        self.tmp_cfg = os.path.join(self.tmp_cfg_dir, "config.json")

        self.p_dem = mock.patch.object(dem, "DEMANDAS_DIR", self.tmp_dem)
        self.p_vector = mock.patch.object(dem, "VECTOR_DB_DEMANDAS", self.tmp_vector)
        self.p_cfg = mock.patch.object(dem, "CONFIG_PATH", self.tmp_cfg)
        self.p_dem.start()
        self.p_vector.start()
        self.p_cfg.start()

        os.makedirs(self.tmp_dem, exist_ok=True)
        with open(os.path.join(self.tmp_dem, "d.pdf"), "w") as fh:
            fh.write("x")
        os.makedirs(self.tmp_vector, exist_ok=True)
        with open(os.path.join(self.tmp_vector, "index.faiss"), "w") as fh:
            fh.write("x")

        self.ctx = dem.DemandasContext()
        self.ctx.config_global = {"demandas_path": self.tmp_dem}
        self.ctx.ruta_demandas = self.tmp_dem
        self.ctx.demandas_vectorstore = "dummy"
        self.ctx.demandas_textos = {"d.pdf": "X"}
        self.ctx.datos_basicos_demandas = {"d.pdf": {"NOMBRE": "Juan"}}

    def tearDown(self):
        self.p_dem.stop()
        self.p_vector.stop()
        self.p_cfg.stop()
        shutil.rmtree(self.tmp_dem, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)
        shutil.rmtree(self.tmp_cfg_dir, ignore_errors=True)
        self.ctx.demandas_vectorstore = None
        self.ctx.demandas_textos.clear()
        self.ctx.datos_basicos_demandas.clear()
        self.ctx.ruta_demandas = ""
        self.ctx.config_global = {}

    def test_eliminar_demandas(self):
        msg = dem.eliminar_demandas(self.ctx)
        self.assertIn("elimin", msg)
        self.assertEqual(self.ctx.demandas_vectorstore, None)
        self.assertEqual(self.ctx.ruta_demandas, "")
        self.assertEqual(self.ctx.demandas_textos, {})
        self.assertEqual(self.ctx.datos_basicos_demandas, {})
        self.assertEqual(self.ctx.config_global.get("demandas_path"), "")
        self.assertEqual(os.listdir(self.tmp_dem), [])
        self.assertEqual(os.listdir(self.tmp_vector), [])
