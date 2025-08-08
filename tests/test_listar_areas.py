import os
import shutil
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem

class ListarAreasTests(TestCase):
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

    def test_listar_areas(self):
        os.makedirs(os.path.join(self.tmp_root, "Laboral"), exist_ok=True)
        os.makedirs(os.path.join(self.tmp_root, "Familiar"), exist_ok=True)
        os.makedirs(
            os.path.join(self.tmp_root, "Familiar", "Pension"), exist_ok=True
        )
        self.assertEqual(
            dem.listar_areas(),
            ["Familiar", os.path.join("Familiar", "Pension"), "Laboral"],
        )
