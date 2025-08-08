import json
from lib import demandas
from langchain_community.chat_models.fake import FakeListChatModel


def test_registrar_entidades_por_llm(tmp_path, monkeypatch):
    destino = tmp_path / "encontradas.json"
    monkeypatch.setattr(demandas, "ENTIDADES_ENCONTRADAS", destino)
    monkeypatch.setattr(
        demandas,
        "ENTIDADES_PREDEFINIDAS",
        ["NOMBRE_DEMANDANTE", "CIUDAD", "OTRA"],
    )
    fake = FakeListChatModel(
        responses=[
            json.dumps(
                {
                    "fields": {
                        "NOMBRE_DEMANDANTE": "",
                        "CIUDAD": "",
                        "DESCONOCIDA": "",
                    }
                }
            )
        ]
    )
    texto = "Demanda presentada en la ciudad correspondiente"
    encontrados = demandas.registrar_entidades_por_llm(texto, fake)
    assert set(encontrados) == {"NOMBRE_DEMANDANTE", "CIUDAD"}
    data = json.load(open(destino, "r", encoding="utf8"))
    assert set(data) == {"NOMBRE_DEMANDANTE", "CIUDAD"}
