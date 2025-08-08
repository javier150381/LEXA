"""Interfaz web simple para interactuar con LEXA mediante Gradio.

El módulo `lib.demandas` requiere varias dependencias externas (incluyendo
`keyring`).  Para que esta interfaz pueda ejecutarse incluso en entornos donde
dichas dependencias no están instaladas, el import se realiza de forma
opcional.  Si la importación falla, la funcionalidad de generación de demandas
se deshabilita pero las demás herramientas continúan funcionando.
"""

import json
import gradio as gr

try:  # pragma: no cover - la importación depende de paquetes externos
    from lib import demandas as dem
except Exception:  # noqa: BLE001 - feedback amigable al usuario
    dem = None

from src.classifier.suggest_type import suggest_type
from src.validators.requirements import validate_requirements


def generar_demanda(tipo: str, caso: str) -> str:
    """Genera una demanda del tipo indicado para el caso dado.

    Cuando las dependencias del módulo ``lib.demandas`` no están disponibles,
    se informa al usuario en lugar de producir un error.
    """

    if dem is None:
        return "Función no disponible: faltan dependencias de 'lib.demandas'"
    return dem.generar_demanda_de_tipo(tipo, caso or "")


def clasificar_caso(descripcion: str, top_n: int) -> str:
    """Clasifica una descripción de caso en posibles categorías."""
    tipos = suggest_type(descripcion, top_n=top_n)
    return "\n".join(tipos)


def validar_requisitos(tipo: str, datos_json: str) -> str:
    """Valida los requisitos obligatorios para una demanda.

    ``datos_json`` debe ser un diccionario en formato JSON.
    """
    try:
        datos = json.loads(datos_json) if datos_json else {}
    except Exception as exc:  # pragma: no cover - feedback al usuario
        return f"Error de formato JSON: {exc}"
    faltantes = validate_requirements(tipo, datos)
    return "\n".join(faltantes) if faltantes else "Sin faltantes"


with gr.Blocks() as demo:
    gr.Markdown("# LEXA - Interfaz web con Gradio")

    with gr.Tab("Generar demanda"):
        tipo_in = gr.Textbox(label="Tipo de demanda")
        caso_in = gr.Textbox(label="Caso", lines=4)
        generar_btn = gr.Button("Generar")
        resultado_out = gr.Textbox(label="Resultado", lines=10)
        generar_btn.click(generar_demanda, inputs=[tipo_in, caso_in], outputs=resultado_out)

    with gr.Tab("Clasificar caso"):
        descripcion_in = gr.Textbox(label="Descripción del caso", lines=4)
        topn_in = gr.Slider(label="Top N", minimum=1, maximum=5, step=1, value=3)
        clasificar_btn = gr.Button("Clasificar")
        tipos_out = gr.Textbox(label="Tipos sugeridos", lines=4)
        clasificar_btn.click(clasificar_caso, inputs=[descripcion_in, topn_in], outputs=tipos_out)

    with gr.Tab("Validar requisitos"):
        tipo_v_in = gr.Textbox(label="Tipo de demanda")
        datos_in = gr.Textbox(label="Datos (JSON)", lines=4)
        validar_btn = gr.Button("Validar")
        faltantes_out = gr.Textbox(label="Requisitos faltantes", lines=4)
        validar_btn.click(validar_requisitos, inputs=[tipo_v_in, datos_in], outputs=faltantes_out)

if __name__ == "__main__":
    demo.launch()
