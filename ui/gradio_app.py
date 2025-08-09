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
from lib import tokens

try:  # pragma: no cover - la importación depende de paquetes externos
    from lib import demandas as dem

    from lib.demandas import (
        chat_fn,
        build_or_load_vectorstore,
        DemandasContext,
        agregar_jurisprudencia_pdf,

        buscar_palabras_clave_fn,
        buscar_palabras_clave_exacta_fn,

        default_context,

    )
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.chat_message_histories import ChatMessageHistory
    ctx = DemandasContext()
except Exception:  # noqa: BLE001 - feedback amigable al usuario
    dem = None
    chat_fn = build_or_load_vectorstore = None
    PyPDFLoader = ChatMessageHistory = None
    DemandasContext = agregar_jurisprudencia_pdf = None

    buscar_palabras_clave_fn = buscar_palabras_clave_exacta_fn = None

    default_context = None

    ctx = None


from src.classifier.suggest_type import suggest_type
from src.validators.requirements import validate_requirements

tokens.init_db()


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



def buscar_palabras_clave(texto: str, modo: str) -> str:
    """Busca artículos por palabras clave en modo exacto o semántico."""

    if (
        dem is None
        or buscar_palabras_clave_fn is None
        or buscar_palabras_clave_exacta_fn is None
    ):
        return "Función no disponible: faltan dependencias de 'lib.demandas'"
    if (modo or "").lower().startswith("exact"):
        return buscar_palabras_clave_exacta_fn(texto or "", ctx=ctx)
    return buscar_palabras_clave_fn(texto or "", ctx=ctx)

def update_token_log(start: str | None, end: str | None):
    """Obtiene el historial de tokens filtrado por fecha."""
    rows = tokens.get_token_log_with_id(start_date=start or None, end_date=end or None, limit=20)
    data = []
    for (
        _row_id,
        ts,
        count,
        tokens_in,
        tokens_out,
        actividad,
        costo_cliente,
        _costo_ds,
    ) in rows:
        data.append(
            [
                ts,
                actividad or "",
                tokens_in if tokens_in is not None else "",
                tokens_out if tokens_out is not None else "",
                count,
                f"{costo_cliente:.4f}",
            ]
        )
    return data


def on_reset_tokens():
    """Reinicia el contador de tokens."""
    tokens.reset_tokens()
    return tokens.get_tokens(), update_token_log(None, None)


def on_import_credit_file(file):
    """Aplica crédito desde un archivo subido."""
    if file is None:
        return tokens.get_credit(), "No se seleccionó archivo"
    try:
        tokens.add_credit_from_file(file.name)
        msg = "Crédito aplicado"
    except Exception as exc:  # pragma: no cover - feedback al usuario
        msg = f"Error: {exc}"
    return tokens.get_credit(), msg




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

    with gr.Tab("Palabras clave"):
        palabras_in = gr.Textbox(label="Ingresa palabras clave o temas")
        modo_in = gr.Radio(
            ["semántico", "exacto"],
            label="Modo de búsqueda",
            value="semántico",
        )
        buscar_pal_btn = gr.Button("Buscar artículos")
        palabras_out = gr.Textbox(
            label="Resultados",
            lines=10,
            show_copy_button=True,
        )
        btn_clear_pal = gr.Button("Limpiar")
        btn_copy_pal = gr.Button("Copiar")
        buscar_pal_btn.click(
            buscar_palabras_clave,
            inputs=[palabras_in, modo_in],
            outputs=palabras_out,
        )
        btn_clear_pal.click(lambda: "", outputs=palabras_out)
        btn_copy_pal.click(
            None,
            inputs=palabras_out,
            outputs=None,
            js="(text) => navigator.clipboard.writeText(text)",
        )

    with gr.Tab("Validar requisitos"):
        tipo_v_in = gr.Textbox(label="Tipo de demanda")
        datos_in = gr.Textbox(label="Datos (JSON)", lines=4)
        validar_btn = gr.Button("Validar")
        faltantes_out = gr.Textbox(label="Requisitos faltantes", lines=4)
        validar_btn.click(validar_requisitos, inputs=[tipo_v_in, datos_in], outputs=faltantes_out)

    with gr.Tab("Tokens"):
        saldo_out = gr.Number(label="Saldo actual", value=tokens.get_credit(), interactive=False)
        tokens_out = gr.Number(label="Tokens usados", value=tokens.get_tokens(), interactive=False)
        credit_file = gr.File(label="Archivo de crédito", file_types=[".json"], interactive=True)
        import_msg = gr.Textbox(label="Resultado", interactive=False)
        credit_file.upload(on_import_credit_file, inputs=credit_file, outputs=[saldo_out, import_msg])
        reset_btn = gr.Button("Reiniciar contador")
        fecha_desde = gr.Textbox(label="Desde (YYYY-MM-DD)")
        fecha_hasta = gr.Textbox(label="Hasta (YYYY-MM-DD)")
        actualizar_btn = gr.Button("Actualizar historial")
        token_log_df = gr.Dataframe(
            headers=[
                "Fecha",
                "Actividad",
                "Tokens entrada",
                "Tokens salida",
                "Tokens",
                "Costo",
            ],
            value=update_token_log(None, None),
            interactive=False,
        )
        actualizar_btn.click(update_token_log, inputs=[fecha_desde, fecha_hasta], outputs=token_log_df)
        reset_btn.click(on_reset_tokens, outputs=[tokens_out, token_log_df])

    with gr.Tab("Configuración"):
        file_upload = gr.File(
            label="Subir jurisprudencia (PDF)",
            file_types=[".pdf"],
            interactive=True,
            file_count="multiple",
        )
        upload_msg = gr.Textbox(label="Resultado", lines=4)
        file_upload.upload(subir_juris, inputs=file_upload, outputs=upload_msg)

    with gr.Tab("Créditos"):
        logo_path = None
        if default_context is not None:
            logo_path = default_context.config_global.get("logo_path")
        if not logo_path or not os.path.isfile(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png")
        gr.Image(value=logo_path, show_label=False)
        gr.Markdown(
            "LEXA - tu asesor legal potenciado por IA\n"
            "Desarrollado por Ing. Marco Castelo.\n"
            "Jurídico: Ab. Marcos Dávalos.\n"
            "Contactos: +593 99 569 9755 / +593959733823\n"
            "Riobamba, Ecuador\n"
            "Todos los derechos reservados."
        )

if __name__ == "__main__":
    disable_share = os.getenv("DISABLE_GRADIO_SHARE", "").lower() in ("1", "true", "yes")
    if disable_share:
        demo.launch()
    else:
        demo.launch(share=True)
