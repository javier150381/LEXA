import ui.forms.schema_form as sf


def test_infer_lines():
    assert sf._infer_lines("Redaccion De Antecedentes……") == 3
    assert sf._infer_lines("Mayor/Menor Demandado") == 1


def test_validate_data_ignores_required_and_checks_pattern():
    schema = {"fields": [{"name": "FIELD1", "label": "Field1", "required": True}]}
    assert sf.validate_data(schema, {}) == []
    schema2 = {"fields": [{"name": "EMAIL", "label": "Correo", "validations": {"pattern": r"^\S+@\S+$"}}]}
    assert sf.validate_data(schema2, {"EMAIL": "bad"}) == ["EMAIL"]
    assert sf.validate_data(schema2, {"EMAIL": "good@example.com"}) == []
