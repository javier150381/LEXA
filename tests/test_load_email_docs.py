import os
import sys
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import lib.demandas as dem


def test_load_email_docs_metadata():
    with mock.patch.object(dem.db, "get_caso_id_by_nombre", return_value=1), \
         mock.patch.object(dem.db, "get_emails_by_caso", return_value=[(10, "n", "a", "b", "c", "body")]):
        docs = dem.load_email_docs("Caso")
    assert len(docs) == 1
    doc = docs[0]
    assert doc.page_content == "body"
    assert doc.metadata["doc_type"] == "email"
    assert doc.metadata["nombre"] == "n"
    assert doc.metadata["id"] == 10
