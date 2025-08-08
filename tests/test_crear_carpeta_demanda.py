import os
import shutil
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem

class CrearCarpetaDemandaTests(TestCase):
    def setUp(self):
        self.tmp_dem = tempfile.mkdtemp()
        self.p_dem = mock.patch.object(dem, "DEMANDAS_DIR", self.tmp_dem)
        self.p_dem.start()

    def tearDown(self):
        self.p_dem.stop()
        shutil.rmtree(self.tmp_dem, ignore_errors=True)

    def test_crear_carpeta_demanda(self):
        msg = dem.crear_carpeta_demanda("Nueva")
        self.assertTrue(os.path.isdir(os.path.join(self.tmp_dem, "Nueva")))
        self.assertIn("creada", msg)
