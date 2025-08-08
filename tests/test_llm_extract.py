import json
from lib.demandas import extraer_datos_por_llm
from langchain_community.chat_models.fake import FakeListChatModel


def test_extraer_datos_por_llm_dynamic_fields():
    texto = (
        "Yo, Juan Perez, ecuatoriano con cédula 1234567890, de 30 años de edad, "
        "profesión abogado y domicilio en Quito."
    )
    fake = FakeListChatModel(
        responses=[
            json.dumps(
                {
                    "NOMBRE": "Juan Perez",
                    "CEDULA": "1234567890",
                    "EDAD": "30",
                    "PROFESION": "abogado",
                    "DOMICILIO": "Quito",
                }
            )
        ]
    )
    datos = extraer_datos_por_llm(texto, fake)
    assert datos == {
        "NOMBRE": "Juan Perez",
        "CEDULA": "1234567890",
        "EDAD": "30",
        "PROFESION": "abogado",
        "DOMICILIO": "Quito",
    }
