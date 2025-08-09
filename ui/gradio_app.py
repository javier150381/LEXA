"""Interfaz web simple para interactuar con LEXA mediante Gradio.

El módulo `lib.demandas` requiere varias dependencias externas (incluyendo
`keyring`).  Para que esta interfaz pueda ejecutarse incluso en entornos donde
dichas dependencias no están instaladas, el import se realiza de forma
opcional.  Si la importación falla, la funcionalidad de generación de demandas
se deshabilita pero las demás herramientas continúan funcionando.
"""

import json
import os
import tempfile
import gradio as gr

try:  # pragma: no cover - la importación depende de paquetes externos
    from lib import demandas as dem

    from lib.demandas import (
        chat_fn,
        build_or_load_vectorstore,
        DemandasContext,
        agregar_jurisprudencia_pdf,
        listar_areas,
        generar_demanda_desde_pdf,
        generar_demanda_cogep_con_datos,
    )
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.chat_message_histories import ChatMessageHistory
    ctx = DemandasContext()
except Exception:  # noqa: BLE001 - feedback amigable al usuario
    dem = None
    chat_fn = build_or_load_vectorstore = None
    PyPDFLoader = ChatMessageHistory = None
    DemandasContext = agregar_jurisprudencia_pdf = None
    listar_areas = generar_demanda_desde_pdf = generar_demanda_cogep_con_datos = None
    ctx = None


from src.classifier.suggest_type import suggest_type
from src.validators.requirements import validate_requirements


def get_lista_demandas():
    return sorted(ctx.demandas_textos.keys()) if ctx else []


def generar_demanda(area: str, ejemplo: str, caso: str, datos_json: str, pdf_base) -> str:
    """Genera una demanda según las opciones proporcionadas."""

    if dem is None or generar_demanda_desde_pdf is None:
        return "Función no disponible: faltan dependencias de 'lib.demandas'"

    try:
        datos = json.loads(datos_json) if datos_json else {}
    except Exception as exc:
        return f"Error de formato JSON: {exc}"

    carpeta_area = os.path.join(ctx.ruta_areas_root, area) if area else None

    try:
        with gr.Progress() as prog:
            if pdf_base is not None:
                prog(0.3, desc="Leyendo PDF base...")
                nombre = os.path.basename(pdf_base.name)
                carpeta = os.path.dirname(pdf_base.name)
                texto = generar_demanda_desde_pdf(
                    nombre, caso or "", datos=datos, ctx=ctx, carpeta=carpeta
                )
            elif ejemplo:
                prog(0.3, desc="Generando desde plantilla...")
                texto = generar_demanda_desde_pdf(
                    ejemplo, caso or "", datos=datos, ctx=ctx, carpeta=carpeta_area
                )
            else:
                prog(0.3, desc="Generando plantilla COGEP...")
                if caso:
                    texto = generar_demanda_cogep_con_datos(caso, ctx=ctx)
                else:
                    texto = dem.generar_demanda_cogep(ctx=ctx)
            prog(1, desc="Completado")
        return texto
    except Exception as exc:  # noqa: BLE001
        return f"Error al generar demanda: {exc}"


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



def responder_chat(mensaje: str, pdf, history: ChatMessageHistory):
    """Responde preguntas sobre un PDF subido temporalmente."""

    if (
        dem is None
        or chat_fn is None
        or build_or_load_vectorstore is None
        or PyPDFLoader is None
    ):
        return ("Función no disponible: faltan dependencias de 'lib.demandas'", history)
    if pdf is None:
        return ("Debe proporcionar un archivo PDF", history)

    docs = PyPDFLoader(pdf.name).load()
    with tempfile.TemporaryDirectory() as tmpdir:
        index_dir = os.path.join(tmpdir, "index")
        vs = build_or_load_vectorstore(tmpdir, index_dir, extra_docs=docs, force_rebuild=True)
        ctx = dem.DemandasContext()
        ctx.memories_por_caso["_GLOBAL_"] = history
        respuesta = chat_fn(
            mensaje,
            caso_seleccionado=None,
            ctx=ctx,
            extra_retriever=vs.as_retriever(),
        )
    return respuesta, history

def subir_juris(files):
    """Carga archivos PDF de jurisprudencia."""
    if agregar_jurisprudencia_pdf is None:
        return "Función no disponible: faltan dependencias de 'lib.demandas'"
    msgs = []
    for file in files or []:
        try:
            agregar_jurisprudencia_pdf(file.name, ctx=ctx)
            msgs.append(f"Agregado: {file.name}")
        except Exception as exc:  # pragma: no cover - feedback amigable
            msgs.append(f"Error al agregar {file.name}: {exc}")
    return "\n".join(msgs)



with gr.Blocks() as demo:
    gr.Markdown("# LEXA - Interfaz web con Gradio")

    with gr.Tab("Generar demanda"):
        area_choices = listar_areas(ctx) if listar_areas else []
        ejemplo_choices = get_lista_demandas()
        area_in = gr.Dropdown(label="Área", choices=area_choices)
        ejemplo_in = gr.Dropdown(label="Modelo/Ejemplo", choices=ejemplo_choices)
        caso_in = gr.Textbox(label="Caso", lines=2)
        datos_in = gr.Textbox(label="Datos adicionales (JSON)", lines=4)
        pdf_in = gr.File(label="PDF base", file_types=[".pdf"], interactive=True)
        generar_btn = gr.Button("Generar")
        resultado_out = gr.Textbox(label="Resultado", lines=10)
        generar_btn.click(
            generar_demanda,
            inputs=[area_in, ejemplo_in, caso_in, datos_in, pdf_in],
            outputs=resultado_out,
        )

    with gr.Tab("Clasificar caso"):
        descripcion_in = gr.Textbox(label="Descripción del caso", lines=4)
        topn_in = gr.Slider(label="Top N", minimum=1, maximum=5, step=1, value=3)
        clasificar_btn = gr.Button("Clasificar")
        tipos_out = gr.Textbox(label="Tipos sugeridos", lines=4)
        clasificar_btn.click(clasificar_caso, inputs=[descripcion_in, topn_in], outputs=tipos_out)

    with gr.Tab("Chat"):
        pdf_temp = gr.File(label="Documento PDF", file_types=[".pdf"], interactive=True)
        input_text = gr.Textbox(label="Pregunta")
        btn_chat = gr.Button("Enviar")
        respuesta_out = gr.Textbox(label="Respuesta", lines=4)
        history_state = gr.State(ChatMessageHistory())
        btn_chat.click(
            responder_chat,
            inputs=[input_text, pdf_temp, history_state],
            outputs=[respuesta_out, history_state],
        )

    with gr.Tab("Validar requisitos"):
        tipo_v_in = gr.Textbox(label="Tipo de demanda")
        datos_in = gr.Textbox(label="Datos (JSON)", lines=4)
        validar_btn = gr.Button("Validar")
        faltantes_out = gr.Textbox(label="Requisitos faltantes", lines=4)
        validar_btn.click(validar_requisitos, inputs=[tipo_v_in, datos_in], outputs=faltantes_out)

    with gr.Tab("Configuración"):
        file_upload = gr.File(
            label="Subir jurisprudencia (PDF)",
            file_types=[".pdf"],
            interactive=True,
            file_count="multiple",
        )
        upload_msg = gr.Textbox(label="Resultado", lines=4)
        file_upload.upload(subir_juris, inputs=file_upload, outputs=upload_msg)

if __name__ == "__main__":
    disable_share = os.getenv("DISABLE_GRADIO_SHARE", "").lower() in ("1", "true", "yes")
    if disable_share:
        demo.launch()
    else:
        demo.launch(share=True)
