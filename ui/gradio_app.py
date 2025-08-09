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
from lib import tokens

try:  # pragma: no cover - la importación depende de paquetes externos
    from lib import demandas as dem

    from lib.demandas import (
        chat_fn,
        build_or_load_vectorstore,
        DemandasContext,
        agregar_jurisprudencia_pdf,

        CASOS_DIR_ROOT,


        listar_areas,
        generar_demanda_desde_pdf,
        generar_demanda_cogep_con_datos,


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

    CASOS_DIR_ROOT = ""


    listar_areas = generar_demanda_desde_pdf = generar_demanda_cogep_con_datos = None


    buscar_palabras_clave_fn = buscar_palabras_clave_exacta_fn = None

    default_context = None


    ctx = None


from src.classifier.suggest_type import suggest_type
from src.validators.requirements import validate_requirements
from ui.constants import CHAT_WITH_AI_OPTION

tokens.init_db()


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
