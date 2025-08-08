import json
from lib.demandas import extraer_entidades_por_llm
from langchain_community.chat_models.fake import FakeListChatModel


def test_extraer_entidades_por_llm_basic():
    texto = (
        "Yo, ......................, presento demanda en la ciudad de "
        "...................... por incumplimiento."
    )
    fake = FakeListChatModel(
        responses=[
            json.dumps({"fields": {"NOMBRE_DEMANDANTE": "", "CIUDAD": ""}})
        ]
    )
    entidades = extraer_entidades_por_llm(texto, fake)
    assert sorted(entidades) == ["CIUDAD", "NOMBRE_DEMANDANTE"]

    texto = "Demanda presentada por JUAN contra PEDRO en Quito."
    fake = FakeListChatModel(
        responses=[
            json.dumps(
                {
                    "fields": {
                        "NOMBRE_ACTOR": "",
                        "NOMBRE_DEMANDADO": "",
                        "CIUDAD": "",
                    }
                }
            )
        ]
    )
    entidades = extraer_entidades_por_llm(texto, fake)
    assert sorted(entidades) == [
        "CIUDAD",
        "NOMBRE_ACTOR",
        "NOMBRE_DEMANDADO",
    ]


def test_extraer_entidades_por_llm_handles_noise():
    texto = "Ejemplo ..."
    fake = FakeListChatModel(
        responses=[
            "Output: "
            + json.dumps({"fields": {"UNO": "", "DOS": ""}})
            + " gracias"
        ]
    )
    entidades = extraer_entidades_por_llm(texto, fake)
    assert sorted(entidades) == ["DOS", "UNO"]


def test_extraer_entidades_por_llm_invalid_json():
    texto = "Ejemplo ..."
    fake = FakeListChatModel(responses=["Sin datos"])
    entidades = extraer_entidades_por_llm(texto, fake)
    assert entidades == []

