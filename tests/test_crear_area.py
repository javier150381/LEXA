import os
import shutil
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem

class CrearAreaTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "AREAS_DIR_ROOT", self.tmp_root)
        self.p_ctx = mock.patch.object(dem.default_context, "ruta_areas_root", self.tmp_root)
        self.p_root.start()
        self.p_ctx.start()

    def tearDown(self):
        self.p_root.stop()
        self.p_ctx.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_crear_area(self):
        msg = dem.crear_area("Nueva")
        self.assertTrue(os.path.isdir(os.path.join(self.tmp_root, "Nueva")))
        self.assertIn("creada", msg)

    def test_crear_area_custom_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            custom_root = os.path.join(tmp, "custom_areas")
            with mock.patch.object(dem, "cargar_config", return_value={"areas_path": custom_root}):
                ctx = dem.DemandasContext()
            msg = dem.crear_area("Otra", ctx)
            self.assertTrue(os.path.isdir(os.path.join(custom_root, "Otra")))
            self.assertIn("creada", msg)
