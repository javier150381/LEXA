import unittest
import unittest
from unittest import mock

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem
from langchain.schema import Document
from lib.exact_index import build_exact_index


class BuscarPalabrasClaveTests(unittest.TestCase):
    def test_requires_jurisprudencia(self):
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = None
        msg = dem.buscar_palabras_clave_fn("algo", ctx)
        self.assertIn("jurisprudencia", msg.lower())

    def test_invokes_chain(self):
        class DummyVS:
            def as_retriever(self, **k):
                return "RET"
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = DummyVS()
        fake_chain = mock.MagicMock()
        fake_chain.invoke.return_value = {"answer": "RESP"}
        with mock.patch.object(dem, "ConversationalRetrievalChain") as mock_chain, \
             mock.patch.object(dem, "RunnableWithMessageHistory", return_value=fake_chain) as mock_wrap, \
             mock.patch.object(dem, "get_llm", return_value="LLM"), \
             mock.patch.object(dem, "ChatMessageHistory", lambda *a, **k: object()):
            mock_chain.from_llm.return_value = "RAW"
            resp = dem.buscar_palabras_clave_fn("hola", ctx)
        self.assertEqual(resp, "RESP")
        mock_chain.from_llm.assert_called()
        mock_wrap.assert_called()

    def test_general_fn_uses_exact_index(self):
        doc = Document(
            page_content="Artículo 5 Contenido del art 5.",
            metadata={"source": "Ley"},
        )

        class DummyVS:
            def __init__(self, docs):
                self.docstore = type("DS", (), {"_dict": {str(i): d for i, d in enumerate(docs)}})()

            def as_retriever(self, **k):
                raise AssertionError("no debería llamarse")

        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = DummyVS([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_fn("¿Qué dice el artículo 5 de la Ley?", ctx)
        self.assertIn("Artículo 5", resp)

    def test_semantic_includes_links(self):
        class DummyVS:
            def as_retriever(self, **k):
                return "RET"

        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = DummyVS()
        fake_doc = Document(page_content="x", metadata={"source": "Ley.pdf"})
        fake_chain = mock.MagicMock()
        fake_chain.invoke.return_value = {
            "answer": "RESP",
            "source_documents": [fake_doc],
        }
        with mock.patch.object(dem, "ConversationalRetrievalChain") as mock_chain, \
             mock.patch.object(dem, "RunnableWithMessageHistory", return_value=fake_chain), \
             mock.patch.object(dem, "get_llm", return_value="LLM"), \
             mock.patch.object(dem, "ChatMessageHistory", lambda *a, **k: object()):
            mock_chain.from_llm.return_value = "RAW"
            resp = dem.buscar_palabras_clave_fn("hola", ctx)
        expected = os.path.join(ctx.ruta_juris, "Ley.pdf")
        self.assertIn(expected, resp)


class BuscarPalabrasClaveExactaTests(unittest.TestCase):
    def _dummy_vs(self, docs):
        class DummyVS:
            def __init__(self, docs):
                self.docstore = type(
                    "DS", (), {"_dict": {str(i): d for i, d in enumerate(docs)}}
                )()

            def similarity_search(self, query, k=20):
                q = query.lower()
                return [
                    d for d in self.docstore._dict.values() if q.split()[0] in d.page_content.lower()
                ]

        return DummyVS(docs)

    def test_requires_jurisprudencia_exacta(self):
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = None
        msg = dem.buscar_palabras_clave_exacta_fn("artículo 1 de la Ley", ctx)
        self.assertIn("jurisprudencia", msg.lower())

    def test_busqueda_sin_documento_devuelve_articulo(self):
        doc = Document(page_content="Artículo 1 Uno", metadata={"source": "Ley"})
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn("artículo 1", ctx)
        self.assertIn("Artículo 1 Uno".lower(), resp.lower())
        self.assertIn("Ley".lower(), resp.lower())

    def test_exacta_includes_link(self):
        doc = Document(page_content="Artículo 1 Uno", metadata={"source": "Ley.pdf"})
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn("artículo 1 de la Ley", ctx)
        expected = os.path.join(ctx.ruta_juris, "Ley.pdf")
        self.assertIn(expected, resp)

    def test_busqueda_varios_documentos(self):
        docs = [
            Document(page_content="Artículo 1 A", metadata={"source": "LeyA"}),
            Document(page_content="Artículo 1 B", metadata={"source": "LeyB"}),
        ]
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs(docs)
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn("artículo 1", ctx)
        self.assertIn("Artículo 1 de LeyA".lower(), resp.lower())
        self.assertIn("Artículo 1 de LeyB".lower(), resp.lower())
        self.assertNotIn("Coincidencias".lower(), resp.lower())

    def test_encontrar_articulo(self):
        doc = Document(
            page_content="Texto del artículo 127",
            metadata={"documento": "Constitución", "articulo": "127"},
        )

        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn(
            "¿Qué dice el artículo 127 de la Constitución?", ctx
        )
        self.assertIn("Texto del artículo 127", resp)
        self.assertIn("Constitución".lower(), resp.lower())

    def test_encontrar_articulo_abreviado_general(self):
        doc = Document(
            page_content="Contenido 5",
            metadata={"documento": "Ley", "articulo": "5"},
        )
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_fn("art. 5 de la Ley", ctx)
        self.assertIn("Contenido 5", resp)
        self.assertIn("Ley".lower(), resp.lower())

    def test_encontrar_articulo_abreviado(self):
        doc = Document(
            page_content="Artículo 127 Texto del artículo 127.\nArtículo 128 Otro.",
            metadata={"source": "Constitucion"},
        )

        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn(
            "¿Qué dice el art. 127 de la Constitución?", ctx
        )
        self.assertIn("Artículo 127", resp)
        self.assertNotIn("Artículo 128", resp)
        self.assertIn("Constitucion".lower(), resp.lower())

    def test_encontrar_articulo_sin_espacio(self):
        doc = Document(
            page_content="Contenido 7",
            metadata={"documento": "Ley", "articulo": "7"},
        )
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn("¿Qué dice el art.7 de la Ley?", ctx)
        self.assertIn("Contenido 7", resp)
        self.assertIn("Ley".lower(), resp.lower())

    def test_busqueda_sin_numero_devuelve_articulo(self):
        doc = Document(
            page_content="Artículo 1 El abuso sexual será sancionado.",
            metadata={"source": "CodigoPenal"},
        )
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn("abuso sexual", ctx)
        self.assertIn("Artículo 1", resp)
        self.assertIn("CodigoPenal".lower(), resp.lower())

    def test_busqueda_con_sinonimos(self):
        doc = Document(
            page_content="Artículo 3 La agresión sexual será sancionada.",
            metadata={"source": "CodigoPenal"},
        )
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn("abuso sexual", ctx)
        self.assertIn("Artículo 3", resp)
        self.assertIn("codigopenal", resp.lower())

    def test_busqueda_sin_resultados(self):
        doc = Document(
            page_content="Artículo 2 Otro tema", metadata={"source": "Ley"}
        )
        ctx = dem.DemandasContext()
        ctx.juris_vectorstore = self._dummy_vs([doc])
        ctx.juris_index = build_exact_index(ctx.juris_vectorstore)
        resp = dem.buscar_palabras_clave_exacta_fn("consulta inexistente", ctx)
        self.assertIn("no se encontraron", resp.lower())



if __name__ == "__main__":
    unittest.main()
