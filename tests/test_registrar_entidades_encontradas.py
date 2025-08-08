import json
from lib import demandas


def test_registrar_entidades_encontradas(tmp_path, monkeypatch):
    destino = tmp_path / "encontradas.json"
    monkeypatch.setattr(demandas, "ENTIDADES_ENCONTRADAS", destino)
    texto = "El actor {{NOMBRE_DEMANDANTE}} representado por {{CORREO_ABOGADO}} presenta demanda."
    encontrados = demandas.registrar_entidades_encontradas(texto)
    assert set(encontrados) == {"NOMBRE_DEMANDANTE", "CORREO_ABOGADO"}
    data = json.load(open(destino, "r", encoding="utf8"))
    assert set(data) == {"NOMBRE_DEMANDANTE", "CORREO_ABOGADO"}
