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
import glob
import gradio as gr

try:  # pragma: no cover - la importación depende de paquetes externos
    from lib import demandas as dem

    from lib.demandas import (
        chat_fn,
        build_or_load_vectorstore,
        DemandasContext,
        agregar_jurisprudencia_pdf,
        CASOS_DIR_ROOT,
    )
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.chat_message_histories import ChatMessageHistory
    ctx = DemandasContext()
except Exception:  # noqa: BLE001 - feedback amigable al usuario
    dem = None
    chat_fn = build_or_load_vectorstore = None
    PyPDFLoader = ChatMessageHistory = None
    DemandasContext = agregar_jurisprudencia_pdf = None
    CASOS_DIR_ROOT = ""
    ctx = None


from src.classifier.suggest_type import suggest_type
from src.validators.requirements import validate_requirements
from ui.constants import CHAT_WITH_AI_OPTION


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


def get_lista_carpeta_casos():
    """Lista los nombres de carpetas de casos existentes."""
    if not CASOS_DIR_ROOT or not os.path.isdir(CASOS_DIR_ROOT):
        return []
    return sorted(
        [
            os.path.basename(p)
            for p in glob.glob(os.path.join(CASOS_DIR_ROOT, "*"))
            if os.path.isdir(p)
        ]
    )


def _history_to_pairs(history: ChatMessageHistory):
    """Convierte ``history`` en pares (usuario, bot) para ``gr.Chatbot``."""
    pairs = []
    user_msg = None
    for msg in history.messages:
        if msg.type == "human":
            user_msg = msg.content
        else:
            pairs.append((user_msg or "", msg.content))
            user_msg = None
    return pairs


def responder_chat_general(
    mensaje: str,
    caso: str,
    pdfs,
    usar_jurisprudencia: bool,
    history: ChatMessageHistory,
):
    """Maneja la conversación del chat general."""

    if (
        dem is None
        or chat_fn is None
        or build_or_load_vectorstore is None
        or PyPDFLoader is None
    ):
        return [], history

    docs = []
    for file in pdfs or []:
        try:
            docs.extend(PyPDFLoader(file.name).load())
        except Exception:  # pragma: no cover - feedback al usuario
            continue
    retriever = None
    if docs:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_dir = os.path.join(tmpdir, "index")
            vs = build_or_load_vectorstore(
                tmpdir, index_dir, extra_docs=docs, force_rebuild=True
            )
            retriever = vs.as_retriever()

    caso_key = caso if caso and caso != CHAT_WITH_AI_OPTION else None
    ctx.memories_por_caso[caso_key or "_GLOBAL_"] = history or ChatMessageHistory()
    respuesta = chat_fn(
        mensaje,
        caso_key,
        ctx=ctx,
        extra_retriever=retriever,
        usar_jurisprudencia=usar_jurisprudencia,
    )
    history = ctx.memories_por_caso[caso_key or "_GLOBAL_"]
    pairs = _history_to_pairs(history)
    return pairs, history


def on_case_change(caso: str):
    """Actualiza el historial mostrado al cambiar de caso."""
    caso_key = caso if caso and caso != CHAT_WITH_AI_OPTION else None
    history = ctx.memories_por_caso.get(caso_key or "_GLOBAL_", ChatMessageHistory())
    ctx.memories_por_caso[caso_key or "_GLOBAL_"] = history
    return _history_to_pairs(history), history


def on_clear_chat(caso: str):
    """Limpia el historial del chat y PDFs cargados."""
    caso_key = caso if caso and caso != CHAT_WITH_AI_OPTION else None
    history = ChatMessageHistory()
    ctx.memories_por_caso[caso_key or "_GLOBAL_"] = history
    return [], history, None, ""


def on_copy_chat(history: ChatMessageHistory) -> str:
    """Devuelve el contenido del chat para copiar."""
    lines = []
    for msg in history.messages:
        role = "Usuario" if msg.type == "human" else "LEXA"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)



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

    with gr.Tab("Chat"):
        casos = [CHAT_WITH_AI_OPTION] + get_lista_carpeta_casos()
        caso_dd = gr.Dropdown(label="Caso", choices=casos, value=CHAT_WITH_AI_OPTION)
        chk_juris = gr.Checkbox(label="Jurisprudencia", value=True)
        pdfs_in = gr.File(
            label="Documentos PDF",
            file_types=[".pdf"],
            interactive=True,
            file_count="multiple",
        )
        chatbot = gr.Chatbot(label="Conversación")
        input_text = gr.Textbox(label="Mensaje")
        with gr.Row():
            btn_chat = gr.Button("Enviar")
            btn_clear = gr.Button("Limpiar")
            btn_copy = gr.Button("Copiar")
        copy_box = gr.Textbox(label="Texto copiado", lines=4)
        history_state = gr.State(ChatMessageHistory())
        caso_dd.change(on_case_change, inputs=caso_dd, outputs=[chatbot, history_state])
        btn_chat.click(
            responder_chat_general,
            inputs=[input_text, caso_dd, pdfs_in, chk_juris, history_state],
            outputs=[chatbot, history_state],
        )
        btn_clear.click(
            on_clear_chat,
            inputs=caso_dd,
            outputs=[chatbot, history_state, pdfs_in, copy_box],
        )
        btn_copy.click(on_copy_chat, inputs=history_state, outputs=copy_box)

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
