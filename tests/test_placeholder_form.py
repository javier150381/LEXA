from src.schema_utils import placeholders_from_text, form_from_text, fill_placeholders


def test_form_and_fill_from_text():
    template = "[NOMBRE COMPLETO], [nacionalidad], cédula [cedula]"
    placeholders = placeholders_from_text(template)
    assert placeholders == ["NOMBRE COMPLETO", "NACIONALIDAD", "CEDULA"]

    form = form_from_text(template, title="Datos")
    names = {f["name"] for f in form["fields"]}
    assert names == {"NOMBRE_COMPLETO", "NACIONALIDAD", "CEDULA"}

    data = {
        "NOMBRE COMPLETO": "Juan Pérez",
        "NACIONALIDAD": "colombiana",
        "CEDULA": "12345",
    }
    filled = fill_placeholders(template, data)
    assert filled == "Juan Pérez, colombiana, cédula 12345"
