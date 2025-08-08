import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda


def generar_plantilla_por_llm(texto, llm_model=None):
    """Genera una plantilla con marcadores y los datos extraídos.

    Parameters
    ----------
    texto : str
        Texto de origen con datos personales.
    llm_model : ChatModel, optional
        Modelo de lenguaje a utilizar. Si no se proporciona, se obtiene con
        :func:`get_llm`.

    Returns
    -------
    tuple[str, dict]
        Una tupla ``(plantilla, campos)`` donde ``plantilla`` es el texto con
        los datos sustituidos por marcadores ``{{CAMPO}}`` y ``campos`` es un
        diccionario con los valores originales.
    """
    if llm_model is None:
        # Importing here avoids a circular import with ``lib.demandas``,
        # which imports ``schema_utils`` that depends on this module.
        from .demandas import get_llm  # lazy import to prevent cycle

        llm_model = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Devuelve un JSON con las claves 'plantilla' y 'campos'. "
            "En 'plantilla', reemplaza cada dato personal por un marcador "
            "entre llaves en mayúsculas (p. ej. {{NOMBRE}}). En 'campos', "
            "incluye un objeto donde cada clave sea el nombre del marcador "
            "sin llaves y el valor sea el dato original.",
        ),
        ("human", "{texto}"),
    ])

    def _run_llm(prompt_value):
        messages = (
            prompt_value.to_messages()
            if hasattr(prompt_value, "to_messages")
            else prompt_value
        )
        return llm_model.invoke(messages)

    chain = prompt | RunnableLambda(_run_llm) | StrOutputParser()
    try:
        salida = chain.invoke({"texto": texto})
        datos = json.loads(salida)
        plantilla = datos.get("plantilla", texto)
        campos = {k: str(v) for k, v in datos.get("campos", {}).items()}
        return plantilla, campos
    except Exception:
        return texto, {}
