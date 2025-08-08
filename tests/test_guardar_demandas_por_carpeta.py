import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, mock
from langchain_community.chat_models.fake import FakeListChatModel

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


class GuardarDemandasPorCarpetaTests(TestCase):
    def setUp(self):
        self.tmp_dem = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.tmp_cfg_dir = tempfile.mkdtemp()
        self.tmp_cfg = os.path.join(self.tmp_cfg_dir, "config.json")
        self.tmp_schemas = tempfile.mkdtemp()

        self.p_dem = mock.patch.object(dem, "DEMANDAS_DIR", self.tmp_dem)
        self.p_vector = mock.patch.object(dem, "VECTOR_DB_DEMANDAS", self.tmp_vector)
        self.p_cfg = mock.patch.object(dem, "CONFIG_PATH", self.tmp_cfg)
        self.p_schemas = mock.patch.object(dem, "SCHEMAS_DIR", Path(self.tmp_schemas))
        self.p_dem.start()
        self.p_vector.start()
        self.p_cfg.start()
        self.p_schemas.start()

        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.p_dem.stop()
        self.p_vector.stop()
        self.p_cfg.stop()
        self.p_schemas.stop()
        shutil.rmtree(self.tmp_dem, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)
        shutil.rmtree(self.tmp_cfg_dir, ignore_errors=True)
        shutil.rmtree(self.tmp_schemas, ignore_errors=True)

    def _create_pdf(self, path):
        from pypdf import PdfWriter
        os.makedirs(os.path.dirname(path), exist_ok=True)
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_guardar_demandas_por_carpeta(self):
        src_root = tempfile.mkdtemp()
        self._create_pdf(os.path.join(src_root, "root.pdf"))
        sub = os.path.join(src_root, "sub")
        self._create_pdf(os.path.join(sub, "inner.pdf"))

        fake_llm = FakeListChatModel(responses=["{}"])
        with mock.patch.object(dem, "build_or_load_vectorstore", return_value="VS") as mock_build, \
             mock.patch.object(dem, "get_llm", return_value=fake_llm), \
             mock.patch.object(dem, "generate_schema_from_pdf", return_value=({"fields": []}, {})) as mock_gen, \
             mock.patch.object(dem, "update_schema_index") as mock_idx, \
             mock.patch.object(dem, "cache_form_data") as mock_cache:
            msg = dem.guardar_demandas_por_carpeta(src_root, self.ctx)

        self.assertIn("cargadas", msg)
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dem, "root.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dem, "sub", "inner.pdf")))
        # Two PDFs -> two schema generations
        self.assertEqual(mock_gen.call_count, 2)
        self.assertEqual(mock_idx.call_count, 2)
        self.assertEqual(mock_cache.call_count, 2)
        # Schemas written to temp directory
        self.assertTrue(any(Path(self.tmp_schemas).glob("demanda_*.json")))
        mock_build.assert_called_once()
        args, kwargs = mock_build.call_args
        self.assertEqual(args[0], self.tmp_dem)
        self.assertEqual(args[1], self.tmp_vector)
        self.assertTrue(kwargs.get("force_rebuild"))
        self.assertEqual(self.ctx.ruta_demandas, src_root)
        self.assertEqual(self.ctx.config_global.get("demandas_path"), src_root)
        shutil.rmtree(src_root, ignore_errors=True)
