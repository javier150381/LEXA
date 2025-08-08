import os
import tempfile
from unittest import mock

from pypdf import PdfWriter

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


class DummyRetriever:
    def __init__(self, docs):
        self.docs = docs

    def get_relevant_documents(self, query):
        return self.docs


class DummyVS:
    def __init__(self, docs):
        self.docs = docs

    @classmethod
    def from_documents(cls, docs, embeddings):
        return cls(docs)

    @classmethod
    def load_local(cls, *a, **k):
        return cls([])

    def save_local(self, path):
        pass

    def as_retriever(self, search_kwargs=None):
        return DummyRetriever(self.docs)

    def add_documents(self, docs):
        self.docs.extend(docs)


class DummyChain:
    def __init__(self, retriever):
        self.retriever = retriever

    def invoke(self, inputs, config=None):
        docs = self.retriever.get_relevant_documents(inputs["question"])
        answer = docs[0].page_content if docs else ""
        return {"answer": answer}


class DummyCRC:
    @classmethod
    def from_llm(cls, llm, retriever, combine_docs_chain_kwargs=None):
        return DummyChain(retriever)


def _blank_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as fh:
        writer.write(fh)


def test_scanned_pdf_text_in_vectorstore():
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "scan.pdf")
        _blank_pdf(pdf_path)
        vector_dir = os.path.join(tmp, "vec")

        class DummyLoader:
            def __init__(self, *a, **k):
                pass

            def load(self):
                raise Exception("no text")

        with mock.patch("lib.demandas.PyPDFLoader", DummyLoader), \
             mock.patch("lib.demandas.read_pdf_text", return_value="hola ocr") as m_read, \
             mock.patch("lib.demandas.FAISS", DummyVS), \
             mock.patch("lib.demandas.HuggingFaceEmbeddings", new=lambda *a, **k: None), \
             mock.patch("lib.demandas.ConversationalRetrievalChain", DummyCRC), \
             mock.patch("lib.demandas.RunnableWithMessageHistory", lambda chain, *a, **k: chain), \
             mock.patch("lib.demandas.get_llm", return_value=None):

            vs = dem.build_or_load_vectorstore(tmp, vector_dir)
            ctx = dem.DemandasContext()
            ctx.juris_vectorstore = vs
            answer = dem.chat_fn("pregunta", None, ctx=ctx, usar_jurisprudencia=True)

        assert answer == "hola ocr"
        m_read.assert_called_once_with(pdf_path)
