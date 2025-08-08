import os
import shutil
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem

class EliminarAreaTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "AREAS_DIR_ROOT", self.tmp_root)
        self.p_ctx = mock.patch.object(dem.default_context, "ruta_areas_root", self.tmp_root)
        self.p_root.start()
        self.p_ctx.start()
        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.p_root.stop()
        self.p_ctx.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _create_area(self, name):
        os.makedirs(os.path.join(self.tmp_root, name), exist_ok=True)

    def test_eliminar_area(self):
        self._create_area("a")
        msg = dem.eliminar_area("a")
        self.assertFalse(os.path.exists(os.path.join(self.tmp_root, "a")))
        self.assertIn("eliminada", msg)

    def test_eliminar_area_inexistente(self):
        msg = dem.eliminar_area("nope")
        self.assertIn("no existe", msg)
