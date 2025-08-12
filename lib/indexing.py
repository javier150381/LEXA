"""Utilidades para crear índices vectoriales.

La función :func:`crear_indice` admite dos backends de almacenamiento:
`FAISS` (por defecto) y `Pinecone`.  Para usar Pinecone se debe pasar el
parámetro ``usar_pinecone=True`` y proporcionar los parámetros de
autenticación ``api_key``, ``environment`` e ``index_name``.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from langchain_community.vectorstores import FAISS

try:  # pragma: no cover - imports opcionales
    from langchain_pinecone import Pinecone as PineconeVS
    import pinecone
except Exception:  # noqa: BLE001 - dependencia opcional
    PineconeVS = None  # type: ignore[assignment]
    pinecone = None  # type: ignore[assignment]


def crear_indice(
    docs: Iterable[Any],
    embeddings: Any,
    usar_pinecone: bool = False,
    *,
    api_key: Optional[str] = None,
    environment: Optional[str] = None,
    index_name: Optional[str] = None,
) -> Any:
    """Crear un índice vectorial a partir de ``docs``.

    Parameters
    ----------
    docs:
        Documentos a indexar.
    embeddings:
        Modelo de embeddings utilizado para transformar los documentos.
    usar_pinecone:
        Si es ``True`` se usa Pinecone como backend; en caso contrario se
        utiliza ``FAISS``.
    api_key, environment, index_name:
        Parámetros de autenticación requeridos por Pinecone.  Son
        ignorados cuando ``usar_pinecone`` es ``False``.

    Returns
    -------
    VectorStore
        Instancia del vector store creado.
    """

    if usar_pinecone:
        if PineconeVS is None or pinecone is None:
            raise ImportError(
                "Pinecone no está instalado. Instala 'pinecone-client' y 'langchain-pinecone'."
            )
        if not api_key or not environment or not index_name:
            raise ValueError(
                "api_key, environment e index_name son obligatorios para Pinecone."
            )
        pinecone.init(api_key=api_key, environment=environment)
        return PineconeVS.from_documents(
            list(docs), embeddings, index_name=index_name
        )

    return FAISS.from_documents(list(docs), embeddings)
