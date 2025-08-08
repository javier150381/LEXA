import json
from fpdf import FPDF
from src.schema_utils import generate_schema_from_pdf


def test_generate_schema_from_pdf_placeholders(tmp_path):
    pdf_path = tmp_path / "ejemplo.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Demandante [ACTOR] contra [DEMANDADO]", ln=1)
    pdf.output(str(pdf_path))

    class FakeLLM:
        def invoke(self, prompt):
            return json.dumps(
                {
                    "plantilla": "Demandante {{ACTOR}} contra {{DEMANDADO}}. Hechos: {{HECHOS}}",
                    "campos": {"HECHOS": "detalle"},
                }
            )

    schema, data = generate_schema_from_pdf(str(pdf_path), llm_model=FakeLLM())
    names = {f["name"] for f in schema["fields"]}
    assert {"ACTOR", "DEMANDADO", "HECHOS"}.issubset(names)
    assert data.get("HECHOS") == "detalle"


def test_generate_schema_from_pdf_llm(tmp_path):
    pdf_path = tmp_path / "ejemplo.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Demanda sin marcadores", ln=1)
    pdf.output(str(pdf_path))

    class FakeLLM:
        def invoke(self, prompt):
            return json.dumps(
                {
                    "plantilla": "Yo, {{NOMBRE}}, con cédula {{CEDULA}}.",
                    "campos": {"NOMBRE": "Juan", "CEDULA": "123"},
                }
            )

    schema, data = generate_schema_from_pdf(str(pdf_path), llm_model=FakeLLM())
    names = {f["name"] for f in schema["fields"]}
    assert "NOMBRE" in names
    assert "CEDULA" in names
    assert data == {"NOMBRE": "Juan", "CEDULA": "123"}
