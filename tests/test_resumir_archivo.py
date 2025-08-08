import os
import shutil
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem
from langchain_community.chat_models.fake import FakeListChatModel


class ResumirArchivoCasoTests(TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp()
        self.p_root = mock.patch.object(dem, "CASOS_DIR_ROOT", self.tmp_root)
        self.p_root.start()

    def tearDown(self):
        self.p_root.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_resumen_txt(self):
        case_dir = os.path.join(self.tmp_root, "C")
        os.makedirs(case_dir, exist_ok=True)
        path = os.path.join(case_dir, "doc.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("Contenido")
        fake = FakeListChatModel(responses=["RES"])
        with mock.patch.object(dem, "get_llm", return_value=fake):
            texto = dem.resumir_archivo_caso("C", "doc.txt")
        self.assertEqual(texto, "RES")

    def test_resumen_pdf(self):
        case_dir = os.path.join(self.tmp_root, "C")
        os.makedirs(case_dir, exist_ok=True)
        open(os.path.join(case_dir, "a.pdf"), "wb").close()
        fake = FakeListChatModel(responses=["SUM"])
        with mock.patch.object(dem, "leer_texto_pdf", return_value="PDF"), \
             mock.patch.object(dem, "get_llm", return_value=fake):
            texto = dem.resumir_archivo_caso("C", "a.pdf")
        self.assertEqual(texto, "SUM")
