import os
import shutil
import tempfile
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem

class EliminarCasoTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.patch_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.patch_vector = mock.patch.object(dem, "VECTOR_DB_CASOS", self.tmp_vector)
        self.patch_mem = mock.patch.object(dem, "ChatMessageHistory", lambda *a, **k: object())
        self.patch_root.start()
        self.patch_vector.start()
        self.patch_mem.start()

        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.patch_root.stop()
        self.patch_vector.stop()
        self.patch_mem.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)
        self.ctx.vectorstores_por_caso.clear()
        self.ctx.memories_por_caso.clear()
        self.ctx.datos_basicos_casos.clear()

    def _create_case(self, name):
        folder = os.path.join(self.tmp_root, name)
        os.makedirs(folder, exist_ok=True)
        index = os.path.join(self.tmp_vector, name)
        os.makedirs(index, exist_ok=True)
        self.ctx.vectorstores_por_caso[name] = "VS"
        self.ctx.memories_por_caso[name] = "MEM"
        self.ctx.datos_basicos_casos[name] = {"NOMBRE": "X"}

    def test_eliminar_caso_removes_all(self):
        self._create_case("case1")
        msg = dem.eliminar_caso("case1", self.ctx)
        self.assertFalse(os.path.exists(os.path.join(self.tmp_root, "case1")))
        self.assertFalse(os.path.exists(os.path.join(self.tmp_vector, "case1")))
        self.assertNotIn("case1", self.ctx.vectorstores_por_caso)
        self.assertNotIn("case1", self.ctx.memories_por_caso)
        self.assertNotIn("case1", self.ctx.datos_basicos_casos)
        self.assertIn("✅", msg)

    def test_eliminar_caso_inexistente(self):
        msg = dem.eliminar_caso("nope", self.ctx)
        self.assertIn("no existe", msg)
