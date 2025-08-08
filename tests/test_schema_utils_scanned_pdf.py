import os
import tempfile
from unittest import mock

from pypdf import PdfWriter
from langchain_community.chat_models.fake import FakeListChatModel

from src.schema_utils import list_placeholders, generate_schema_from_pdf


def _blank_pdf(path: str) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as fh:
        writer.write(fh)


def test_list_placeholders_scanned_pdf():
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "scan.pdf")
        _blank_pdf(pdf_path)
        with mock.patch("src.schema_utils.extract_text", return_value=""), \
             mock.patch("lib.pdf_utils.read_pdf_text", return_value="hola [NOMBRE]") as m_read:
            placeholders = list_placeholders(pdf_path)
        assert placeholders == ["NOMBRE"]
        m_read.assert_called_once_with(pdf_path)


def test_generate_schema_from_scanned_pdf():
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "scan.pdf")
        _blank_pdf(pdf_path)
        with mock.patch("src.schema_utils.extract_text", return_value=""), \
             mock.patch("lib.pdf_utils.read_pdf_text", return_value="hola [NOMBRE]") as m_read:
            fake_llm = FakeListChatModel(responses=["{\"plantilla\": \"\", \"campos\": {}}"]) 
            schema, datos = generate_schema_from_pdf(pdf_path, llm_model=fake_llm)
        assert datos == {}
        assert schema["fields"][0]["name"] == "NOMBRE"
        m_read.assert_called_once_with(pdf_path)
