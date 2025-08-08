import os
import shutil
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem

class GuardarEmailTxtTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.patch = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_guardar_email_txt(self):
        path = dem.guardar_email_en_txt(
            "Caso1", "Mi Correo", "yo@example.com", "Asunto", "2024-01-01", "Cuerpo"
        )
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("Remite: yo@example.com", content)
        self.assertIn("Asunto: Asunto", content)
        self.assertIn("Cuerpo", content)
        # file should be inside case folder
        self.assertTrue(path.startswith(os.path.join(self.tmp_root, "Caso1")))
