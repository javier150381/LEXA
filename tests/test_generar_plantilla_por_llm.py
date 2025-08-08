import json
import os
import sys
from langchain_community.chat_models.fake import FakeListChatModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.plantillas import generar_plantilla_por_llm


def test_generar_plantilla_por_llm():
    texto = "Yo, Marco Javier Castelo, de cédula 060337380, vecino de Quito."
    respuesta = json.dumps(
        {
            "plantilla": "Yo, {{NOMBRE_COMPLETO}}, de cédula {{CEDULA}}, vecino de {{CIUDAD}}.",
            "campos": {
                "NOMBRE_COMPLETO": "Marco Javier Castelo",
                "CEDULA": "060337380",
                "CIUDAD": "Quito",
            },
        }
    )
    fake = FakeListChatModel(responses=[respuesta])
    plantilla, campos = generar_plantilla_por_llm(texto, fake)
    assert plantilla == "Yo, {{NOMBRE_COMPLETO}}, de cédula {{CEDULA}}, vecino de {{CIUDAD}}."
    assert campos == {
        "NOMBRE_COMPLETO": "Marco Javier Castelo",
        "CEDULA": "060337380",
        "CIUDAD": "Quito",
    }


def test_generar_plantilla_por_llm_fallback():
    texto = "Yo, Marco Javier Castelo, de cédula 060337380."
    fake = FakeListChatModel(responses=["no json"])
    plantilla, campos = generar_plantilla_por_llm(texto, fake)
    assert plantilla == texto
    assert campos == {}
