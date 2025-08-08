import os
import shutil
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem


class CrearCasoTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.p_root.start()

    def tearDown(self):
        self.p_root.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_crear_caso(self):
        msg = dem.crear_caso("CasoX")
        self.assertTrue(os.path.isdir(os.path.join(self.tmp_root, "CasoX")))
        self.assertIn("creado", msg)
