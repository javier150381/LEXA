from src import schema_utils


def test_cache_and_load_form_data(tmp_path, monkeypatch):
    monkeypatch.setattr(schema_utils, "FORM_DATA_CACHE_DIR", tmp_path)
    data = {"actor": "Juan", "demandado": "Ana"}
    schema_utils.cache_form_data("civil", data)
    loaded = schema_utils.load_form_data("civil")
    assert loaded == data
