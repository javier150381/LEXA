import os
from email.message import EmailMessage
import lib.demandas as dem

def test_get_pdf_attachments():
    msg = EmailMessage()
    msg.set_content("hola")
    msg.add_attachment(b"%PDF-1.4\n", maintype="application", subtype="pdf", filename="doc.pdf")
    atts = dem.get_pdf_attachments(msg)
    assert len(atts) == 1
    name, data = atts[0]
    assert name == "doc.pdf"
    assert data.startswith(b"%PDF")
