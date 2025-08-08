import unittest
from unittest import mock
import lib.demandas as dem

class ResumirCasoTests(unittest.TestCase):
    def test_invoca_chain(self):
        class DummyVS:
            def as_retriever(self, **k):
                return "RET"
        ctx = dem.DemandasContext()
        ctx.vectorstores_por_caso["CASE"] = DummyVS()
        fake_chain = mock.MagicMock()
        fake_chain.invoke.return_value = {"answer": "OK"}
        with mock.patch.object(dem, "ConversationalRetrievalChain") as m_chain, \
             mock.patch.object(dem, "RunnableWithMessageHistory", return_value=fake_chain) as m_wrap, \
             mock.patch.object(dem, "get_llm", return_value="LLM"), \
             mock.patch.object(dem, "ChatMessageHistory", lambda *a, **k: object()):
            m_chain.from_llm.return_value = "RAW"
            resp = dem.resumir_caso("CASE", ctx)
        self.assertEqual(resp, "OK")
        m_chain.from_llm.assert_called()
        m_wrap.assert_called()

    def test_usa_cache_si_existe(self):
        class DummyVS:
            def as_retriever(self, **k):
                return "RET"

        ctx = dem.DemandasContext()
        ctx.vectorstores_por_caso["CASE"] = DummyVS()
        ctx.datos_basicos_casos["CASE"] = {"RESUMEN": "CACHED"}

        with mock.patch.object(dem, "ConversationalRetrievalChain") as m_chain:
            resp = dem.resumir_caso("CASE", ctx)

        self.assertEqual(resp, "CACHED")
        m_chain.from_llm.assert_not_called()

if __name__ == "__main__":
    unittest.main()
