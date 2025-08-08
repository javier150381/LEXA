import os
import shutil
import tempfile
from unittest import TestCase, mock

from pypdf import PdfWriter

import lib.demandas as dem


class MoverPdfCasoAreaTests(TestCase):
    def setUp(self):
        self.tmp_casos = tempfile.mkdtemp()
        self.tmp_vector = tempfile.mkdtemp()
        self.tmp_areas = tempfile.mkdtemp()
        self.p_casos = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_casos)
        self.p_vector = mock.patch.object(dem, "VECTOR_DB_CASOS", self.tmp_vector)
        self.p_areas = mock.patch.object(dem, "AREAS_DIR_ROOT", self.tmp_areas)
        self.p_ctx1 = mock.patch.object(dem.default_context, "ruta_areas_root", self.tmp_areas)
        self.p_config = mock.patch.object(
            dem, "cargar_config", return_value={"areas_path": self.tmp_areas}
        )
        self.p_casos.start()
        self.p_vector.start()
        self.p_areas.start()
        self.p_ctx1.start()
        self.p_config.start()
        self.ctx = dem.DemandasContext()

    def tearDown(self):
        self.p_casos.stop()
        self.p_vector.stop()
        self.p_areas.stop()
        self.p_ctx1.stop()
        self.p_config.stop()
        shutil.rmtree(self.tmp_casos, ignore_errors=True)
        shutil.rmtree(self.tmp_vector, ignore_errors=True)
        shutil.rmtree(self.tmp_areas, ignore_errors=True)

    def _create_pdf(self, path):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with open(path, "wb") as f:
            writer.write(f)

    def test_mover_pdf_de_caso_a_area(self):
        case_folder = os.path.join(self.tmp_casos, "case")
        os.makedirs(case_folder)
        pdf_path = os.path.join(case_folder, "a.pdf")
        self._create_pdf(pdf_path)

        os.makedirs(os.path.join(self.tmp_vector, "case"))
        self.ctx.vectorstores_por_caso["case"] = "VS"

        os.makedirs(os.path.join(self.tmp_areas, "area1"))

        with mock.patch.object(dem, "build_or_load_vectorstore", return_value="VS2"):
            msg = dem.mover_pdf_de_caso_a_area("a.pdf", "case", "area1", self.ctx)

        self.assertIn("movido", msg)
        self.assertFalse(os.path.exists(pdf_path))
        dest = os.path.join(self.tmp_areas, "area1", "a.pdf")
        self.assertTrue(os.path.exists(dest))
