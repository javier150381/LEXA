"""Herramientas para construir cadenas RAG."""

from __future__ import annotations

from typing import Iterable, Sequence

from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def construir_rag(
    textos: Sequence[str],
    *,
    embeddings: Embeddings | None = None,
    llm: ChatOpenAI | None = None,
):
    """Construye una cadena RAG sencilla a partir de *textos*.

    Parameters
    ----------
    textos:
        Lista de textos que se indexarán para la recuperación.
    embeddings:
        Implementación opcional de :class:`~langchain_core.embeddings.Embeddings`.
        Si no se proporciona se usan `OpenAIEmbeddings`.
    llm:
        Modelo de lenguaje opcional. Por defecto se usa ``ChatOpenAI``.

    Returns
    -------
    tuple
        Pareja ``(cadena, retriever)`` donde ``cadena`` es una instancia de
        :class:`~langchain.chains.RetrievalQA` lista para invocarse y
        ``retriever`` permite realizar consultas de manera independiente.
    """

    embeddings = embeddings or OpenAIEmbeddings()
    vectorstore = FAISS.from_texts(list(textos), embeddings)
    retriever = vectorstore.as_retriever()
    llm = llm or ChatOpenAI(temperature=0)
    cadena = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    return cadena, retriever
