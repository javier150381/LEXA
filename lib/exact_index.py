
import os
import re

import unicodedata
from typing import Any, Dict, List, Optional, Set


def _normalize_text(s: str) -> str:
    """Return ``s`` lowercased and stripped of accents."""
    return (
        unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8").lower()
    )


def build_exact_index(vectorstore: Any) -> List[Dict[str, Any]]:

    """Return a list of documents with their metadata from a vectorstore."""

    """Create a metadata-based index of all "Artículo" entries.

    Each entry of the returned list contains the exact text of one article and
    two metadata fields:

    * ``documento`` – the source filename without extension.
    * ``articulo`` – the article number as integer.

    ``vectorstore`` is only used as a convenient container of the loaded
    documents; no similarity search is performed.
    """


    if not vectorstore:
        return []

    index: List[Dict[str, Any]] = []
    pattern = re.compile(r"Art[ií]culo\s+(\d+)\b", re.IGNORECASE)
    seen: Set[tuple[str, str]] = set()

    for doc in vectorstore.docstore._dict.values():
        text = doc.page_content
        meta = getattr(doc, "metadata", {}) or {}

        # Allow callers to provide ``documento`` and ``articulo`` directly in
        # the metadata of each ``Document``. When present we add the entry to
        # the index without using the regular expression search above.
        if "documento" in meta and "articulo" in meta:
            doc_name = str(meta["documento"])
            num = str(meta["articulo"])
            key = (doc_name, num)
            if key in seen:
                continue
            index.append(
                {
                    "text": text.strip(),
                    "metadata": {"documento": doc_name, "articulo": int(num)},
                }
            )
            seen.add(key)
            continue

        source = meta.get("source", "")
        doc_name = os.path.splitext(source)[0]

        for match in pattern.finditer(text):
            num = match.group(1)
            key = (doc_name, num)
            if key in seen:
                continue

            start = match.start()
            after = text[start:]
            next_m = pattern.search(after[len(match.group(0)):])
            end = start + len(match.group(0)) + next_m.start() if next_m else len(text)
            article_text = text[start:end].strip()

            index.append(
                {
                    "text": article_text,
                    "metadata": {"documento": doc_name, "articulo": int(num)},
                }
            )
            seen.add(key)

    return index


def search_article(
    num: str,
    fuente: Optional[str] = None,
    index: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Return all matches for ``Artículo num`` filtered by ``fuente``.

    ``index`` must be the structure produced by :func:`build_exact_index`. The
    search is performed only over the metadata fields ``documento`` and
    ``articulo``.  ``fuente`` is compared in a case- and accent-insensitive
    manner and can be a partial name of the document.
    """

    if not index:
        return []

    fuente_norm = _normalize_text(fuente) if fuente else ""
    results: List[Dict[str, Any]] = []

    for entry in index:
        meta = entry["metadata"]
        art = str(meta.get("articulo"))
        if art != str(num):
            continue
        doc = str(meta.get("documento", ""))
        doc_norm = _normalize_text(doc)
        if fuente_norm and not (
            fuente_norm in doc_norm or doc_norm in fuente_norm
        ):
            continue
        results.append(entry)

    return results
