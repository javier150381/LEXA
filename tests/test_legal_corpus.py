import os
import tempfile
from unittest import TestCase, mock

import lib.demandas as dem


class LegalCorpusTests(TestCase):
    def test_indexar_corpus_legal_invoca_build(self):
        tmp_docs = tempfile.mkdtemp()
        tmp_vec = tempfile.mkdtemp()
        ctx = dem.DemandasContext()
        ctx.ruta_legal_corpus = tmp_docs
        with mock.patch.object(dem, "LEGAL_CORPUS_DIR", tmp_docs), \
             mock.patch.object(dem, "VECTOR_DB_LEGAL", tmp_vec), \
             mock.patch.object(dem, "build_or_load_vectorstore", return_value="VS") as mock_build:
            msg = dem.indexar_corpus_legal(ctx)
        self.assertIn("indexado", msg)
        self.assertEqual(ctx.legal_vectorstore, "VS")
        mock_build.assert_called_once_with(tmp_docs, tmp_vec, force_rebuild=True)

    def test_generar_redaccion_incluye_referencias(self):
        class DummyVS:
            def as_retriever(self, search_kwargs=None):
                class R:
                    def get_relevant_documents(self, q):
                        from langchain.schema import Document
                        return [Document(page_content="t", metadata={"source": "norma.txt"})]
                return R()

        ctx = dem.DemandasContext()
        ctx.legal_vectorstore = DummyVS()
        datos = {
            "DESIGNACION_JUZGADOR": "Juez",
            "ACTOR_NOMBRES_APELLIDOS": "Pedro Perez",
            "DEMANDADO_NOMBRES_APELLIDOS": "Juan Lopez",
            "FUNDAMENTOS_DERECHO": "contrato",
        }
        texto = dem.generar_redaccion_demanda_llm(datos, ctx=ctx)
        self.assertIn("Referencias", texto)
        self.assertIn("norma.txt", texto)
