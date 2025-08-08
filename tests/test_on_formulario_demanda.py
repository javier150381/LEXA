import types

import ui.app as app_module
import src.schema_utils as schema_utils
import ui.forms.schema_form as schema_form


class DummyVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


def test_preserve_cached_data(monkeypatch, tmp_path):
    # Prepare directories and default context
    monkeypatch.setattr(app_module, "DEMANDAS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "AREAS_DIR_ROOT", tmp_path)
    dummy_context = types.SimpleNamespace(demandas_textos={}, last_generated_document="")
    monkeypatch.setattr(app_module, "default_context", dummy_context)

    pdf_file = tmp_path / "example.pdf"
    pdf_file.write_text("dummy")

    schema = {"fields": [{"name": "NOMBRE"}]}
    pdf_data = {"NOMBRE": "pdf"}

    cache_storage = {}
    cache_calls = {"count": 0}

    def fake_cache_form_data(tipo, data):
        cache_calls["count"] += 1
        cache_storage[tipo] = data.copy()

    def fake_load_form_data(tipo):
        return cache_storage.get(tipo, {}).copy()

    monkeypatch.setattr(schema_form, "SchemaForm", lambda *a, **k: None)
    monkeypatch.setattr(app_module.messagebox, "askyesno", lambda *a, **k: False)
    monkeypatch.setattr(schema_utils, "_slugify", lambda s: s)
    monkeypatch.setattr(schema_utils, "generate_schema_from_pdf", lambda p: (schema, pdf_data))
    monkeypatch.setattr(schema_utils, "hash_for_pdf", lambda p: "hash")
    monkeypatch.setattr(schema_utils, "update_schema_index", lambda *a, **k: None)
    monkeypatch.setattr(schema_utils, "cache_form_data", fake_cache_form_data)
    monkeypatch.setattr(schema_utils, "load_form_data", fake_load_form_data)
    monkeypatch.setattr(schema_utils, "cache_placeholder_mapping", lambda *a, **k: None)
    monkeypatch.setattr(schema_utils, "SCHEMAS_DIR", tmp_path)

    app = types.SimpleNamespace(
        var_demanda=DummyVar("example.pdf"),
        var_area=DummyVar(""),
        root=None,
        chat_demanda_area=None,
        btn_export_word=None,
        btn_export_pdf=None,
        _format_text=lambda x: x,
    )

    # First call caches PDF data
    app_module.AbogadoVirtualApp.on_formulario_demanda(app)
    assert cache_calls["count"] == 1
    assert cache_storage["example"] == pdf_data

    # Simulate user modifications saved in cache
    cache_storage["example"] = {"NOMBRE": "user"}

    # Second call should not overwrite cached data (askyesno returns False)
    app_module.AbogadoVirtualApp.on_formulario_demanda(app)
    assert cache_calls["count"] == 1
    assert cache_storage["example"] == {"NOMBRE": "user"}
