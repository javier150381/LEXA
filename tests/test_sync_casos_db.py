import os
import tempfile
import shutil
from unittest import TestCase, mock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database as db
import lib.demandas as dem


class SyncCasosDbTests(TestCase):
    def setUp(self):
        self.tmp_db_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_db_dir, "db.sqlite")
        self.patch_db = mock.patch.object(db, "DB_PATH", self.db_path)
        self.patch_db.start()
        db.init_db()

        self.tmp_casos_root = tempfile.mkdtemp()
        self.patch_casos = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_casos_root)
        self.patch_casos.start()

    def tearDown(self):
        self.patch_db.stop()
        self.patch_casos.stop()
        shutil.rmtree(self.tmp_db_dir, ignore_errors=True)
        shutil.rmtree(self.tmp_casos_root, ignore_errors=True)

    def _create_case(self, name):
        os.makedirs(os.path.join(self.tmp_casos_root, name), exist_ok=True)

    def test_sync_adds_missing_cases(self):
        self._create_case("Caso1")
        self._create_case("Caso2")

        db.sync_casos_from_fs()
        nombres = [row[2] for row in db.get_casos()]
        self.assertIn("Caso1", nombres)
        self.assertIn("Caso2", nombres)

        # ensure calling again does not duplicate
        db.sync_casos_from_fs()
        self.assertEqual(len(nombres), len(db.get_casos()))
