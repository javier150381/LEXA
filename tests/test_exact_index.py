import unittest
from langchain.schema import Document
from lib.exact_index import build_exact_index


class DummyVS:
    def __init__(self, docs):
        self.docstore = type("DS", (), {"_dict": {str(i): d for i, d in enumerate(docs)}})()


class BuildExactIndexTests(unittest.TestCase):
    def test_uses_existing_metadata(self):
        doc = Document(
            page_content="Contenido 5",
            metadata={"documento": "Ley", "articulo": "5"},
        )
        vs = DummyVS([doc])
        index = build_exact_index(vs)
        self.assertEqual(len(index), 1)
        self.assertEqual(index[0]["metadata"], {"documento": "Ley", "articulo": 5})
        self.assertEqual(index[0]["text"], "Contenido 5")

    def test_mixed_docs(self):
        doc1 = Document(
            page_content="Contenido 5",
            metadata={"documento": "Ley", "articulo": 5},
        )
        doc2 = Document(
            page_content="Artículo 7 Texto",
            metadata={"source": "Norma.pdf"},
        )
        vs = DummyVS([doc1, doc2])
        index = build_exact_index(vs)
        metas = { (e["metadata"]["documento"], e["metadata"]["articulo"]) for e in index }
        self.assertIn(("Ley", 5), metas)
        self.assertIn(("Norma", 7), metas)


if __name__ == "__main__":
    unittest.main()
