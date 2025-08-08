import json

from src import schema_utils


def test_cache_placeholder_mapping(tmp_path, monkeypatch):
    monkeypatch.setattr(schema_utils, "PLACEHOLDER_CACHE_DIR", tmp_path)
    data = {"NOMBRE": "{{NOMBRE}}"}
    schema_utils.cache_placeholder_mapping("demo", data)
    path = tmp_path / "demo.json"
    assert json.load(open(path, "r", encoding="utf8")) == data

