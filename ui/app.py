import os
import glob
import shutil
import re
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox, simpledialog
import threading
from tkcalendar import DateEntry
from datetime import datetime
import json
from decimal import Decimal, ROUND_HALF_UP
import unicodedata
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image, ImageTk
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from lib import tokens, demandas, costos, activation
from lib.feedback import save_feedback
from lib import database as db
from src.classifier.suggest_type import suggest_type
from ui.constants import (
    WINDOW_BG,
    FRAME_BG,
    PRIMARY_BTN_BG,
    SECONDARY_BTN_BG,
    DELETE_BTN_BG,
    TEXT_COLOR,
    TITLE_COLOR,
    LIST_BG,
    SUCCESS_COLOR,
    ERROR_COLOR,
    STATUS_BG,
    CONFIG_BTN_BG,
    CONFIG_PANEL_BG,
    BUTTON_TEXT_COLOR,
    ENTRY_FONT,
    ENTRY_BG,
    CHAT_WITH_AI_OPTION,
)

from lib.demandas import (
    guardar_jurisprudencia_por_carpeta,
    actualizar_jurisprudencia,
    eliminar_jurisprudencia,
    agregar_jurisprudencia_pdf,
    eliminar_jurisprudencia_pdf,
    guardar_caso_por_carpeta,
    crear_caso,
    agregar_pdf_a_caso,
    guardar_pdf_en_caso,
    eliminar_pdf_de_caso,
    actualizar_casos,
    eliminar_caso,
    guardar_demandas_por_carpeta,
    actualizar_demandas,
    eliminar_demandas,
    crear_carpeta_demanda,
    agregar_demanda_pdf,
    eliminar_demanda_pdf,
    crear_area,
    eliminar_area,
    agregar_pdf_a_area,
    eliminar_pdf_de_area,
    listar_pdfs_de_area,
    listar_areas,
    chat_fn,
    generar_demanda_desde_pdf,
    generar_demanda_cogep,
    generar_demanda_cogep_con_datos,
    obtener_dato_de_caso,
    cargar_textos_demandas,
    buscar_palabras_clave_fn,
    buscar_palabras_clave_exacta_fn,
    exportar_a_word,
    exportar_a_pdf,
    build_or_load_vectorstore,
    JURIS_DIR,
    VECTOR_DB_JURIS,
    CASOS_DIR_ROOT,
    VECTOR_DB_CASOS,
    VECTOR_DB_DEMANDAS,
    DEMANDAS_DIR,
    AREAS_DIR_ROOT,
    _resolve_path,
    default_context,
)


# Variables globales utilizadas durante la carga automática
# Se usan las instancias almacenadas en `default_context`


class AbogadoVirtualApp:
    def __init__(self, root):
        self.root = root
        # Make the main app instance accessible from the Tk root so that
        # child windows can interact with it.
        setattr(self.root, "app", self)
        self.root.title("⚖️ LEXA - tu asesor legal potenciado por IA")
        self.root.geometry("1000x800")
        self.root.configure(bg=WINDOW_BG)
        self.root.option_add("*Frame.Background", FRAME_BG)
        self.root.option_add("*Label.Background", FRAME_BG)
        self.root.option_add("*Label.Foreground", TEXT_COLOR)
        self.root.option_add("*Listbox.Background", LIST_BG)
        self.root.option_add("*Listbox.Foreground", TEXT_COLOR)
        # Use the same button colors across all tabs as in the Configuración tab
        self.root.option_add("*Button.Background", CONFIG_BTN_BG)
        self.root.option_add("*Button.Foreground", BUTTON_TEXT_COLOR)
        self.root.option_add("*Button.ActiveBackground", CONFIG_BTN_BG)
        self.root.option_add("*Button.ActiveForeground", BUTTON_TEXT_COLOR)
        self.root.option_add("*Entry.Background", ENTRY_BG)
        self.root.option_add("*Entry.Font", ENTRY_FONT)
        style = ttk.Style(self.root)
        style.configure("TFrame", background=FRAME_BG)
        style.configure("TLabelframe", background=FRAME_BG)
        style.configure("TLabelframe.Label", background=FRAME_BG)

        self.pdf_map = self._build_pdf_map()

        self.caso_seleccionado = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Espere mientras se carga...")
        self.chat_status_text = tk.StringVar(value="")
        self.palabras_status_text = tk.StringVar(value="")

        self.var_demanda_carpeta = tk.StringVar(value="")
        self.var_area = tk.StringVar(value="")

        self.folder_juris = ""
        self.folder_casos = ""
        self.folder_demandas = ""

        tokens.init_db()
        # Contador de tokens usados y saldo inicial
        self.tokens_usados = tokens.get_tokens()
        self.saldo_actual = tokens.get_credit()

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_percent_var = tk.StringVar(value="0%")
        self.progress_window = None
        self.progress = None

        self.chat_session_pdfs = []
        self.chat_pdf_widgets = {}
        self.chat_pdf_vars = {}
        self.chat_session_vs = None
        self.caso_pdf_trabajo = tk.StringVar(value="")
        self._case_pdf_photo = None

        self.root.bind("<Control-Alt-m>", self.toggle_admin_panel)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_app)

        self.build_interface()
        self.ensure_license_email()
        self.show_progress_dialog()
        threading.Thread(
            target=self.autocargar_si_existente, daemon=True
        ).start()
        # Eliminamos la reconstrucción automática de índices al iniciar para
        # evitar tiempos de carga innecesarios. Los usuarios pueden
        # actualizar manualmente desde la interfaz cuando lo requieran.

    def ensure_license_email(self):
        """Ensure a license email is configured via the Configuración tab."""
        email = default_context.config_global.get("license_email", "").strip()
        if email:
            return
        messagebox.showwarning(
            "Correo requerido",
            (
                "Debe ingresar un correo electrónico para registrar los "
                "créditos y generar el archivo de tokens."
            ),
            parent=self.root,
        )
        for idx in range(self.notebook.index("end")):
            if idx != 0:
                self.notebook.tab(idx, state="disabled")
        self.notebook.select(0)

    def _normalize_name(self, name: str) -> str:
        """Return ``name`` uppercased, stripped of spaces and accents."""
        nfkd = unicodedata.normalize("NFD", name)
        no_accents = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
        return no_accents.replace(" ", "").upper()

    def _build_pdf_map(self):
        """Map document names (normalized) to their PDF paths."""
        mapping = {}
        for path in glob.glob(os.path.join(JURIS_DIR, "*.pdf")):
            base = os.path.splitext(os.path.basename(path))[0]
            mapping[self._normalize_name(base)] = path
        return mapping

    def _extract_document_names(self, texto):
        """Extract document names from the search result text."""
        nombres = re.findall(r"de\s+([\w\sÁÉÍÓÚÑáéíóúñ]+):", texto)
        nombres += re.findall(r"-\s*([\w\sÁÉÍÓÚÑáéíóúñ]+):", texto)
        # Remove duplicates while preserving order
        seen = set()
        uniq = []
        for n in nombres:
            n = n.strip()
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        return uniq

    def _update_pdf_links(self, nombres):
        """Create buttons linking to PDFs for the given document names."""
        if not hasattr(self, "links_palabras"):
            return
        for w in self.links_palabras.winfo_children():
            w.destroy()
        for nombre in nombres:
            ruta = self.pdf_map.get(self._normalize_name(nombre))
            if ruta:
                btn = tk.Button(
                    self.links_palabras,
                    text=f"Ver {nombre}",
                    command=lambda p=ruta: self._abrir_archivo(p),
                )
                btn.pack(side="left", padx=5)

    def build_interface(self):
        header = tk.Frame(self.root)
        header.pack(fill="x")
        self.lbl_credito_header = tk.Label(header, font=("TkDefaultFont", 10))
        self.lbl_credito_header.pack(side="right", padx=5)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)
        # Store notebook so other components can change tabs
        self.notebook = notebook

        frame_config = ttk.Frame(notebook)
        notebook.add(frame_config, text="⚙️ Configuración")

        frame_chat_tab = ttk.Frame(notebook)
        notebook.add(frame_chat_tab, text="💬 Chat")

        frame_demanda = ttk.Frame(notebook)
        notebook.add(frame_demanda, text="📝 Generar Demanda")
        # Keep reference to this tab for later selection
        self.tab_generar_demanda = frame_demanda

        frame_palabras = ttk.Frame(notebook)
        notebook.add(frame_palabras, text="🔑 Palabras Clave")

        frame_casos_tab = ttk.Frame(notebook)
        notebook.add(frame_casos_tab, text="📂 Casos")

        frame_tokens = ttk.Frame(notebook)
        notebook.add(frame_tokens, text="🪙 Tokens")
        # Record index of the tokens tab for credit restrictions
        self.tokens_tab_index = notebook.index("end") - 1

        frame_id_clave = ttk.Frame(notebook)
        notebook.add(frame_id_clave, text="🆔 ID y Clave")
        # Record index of the recharge tab for credit restrictions
        self.id_clave_tab_index = notebook.index("end") - 1

        frame_creditos = ttk.Frame(notebook)
        notebook.add(frame_creditos, text="📜 Créditos")

        self.build_pestaña_config(frame_config)
        self.build_pestaña_chat(frame_chat_tab)
        self.build_pestaña_generar_demanda(frame_demanda)
        self.build_pestaña_palabras_clave(frame_palabras)
        self.build_pestaña_casos(frame_casos_tab)
        self.build_pestaña_tokens(frame_tokens)
        self.build_pestaña_id_clave(frame_id_clave)
        self.build_pestaña_creditos(frame_creditos)

    # ---------------------------- Pestaña Configuración ----------------------------
    def build_pestaña_config(self, parent):
        container = tk.Frame(parent, bg=CONFIG_PANEL_BG)
        container.pack(fill="both", expand=True)

        frame_uploads = tk.Frame(container, pady=10, bg=CONFIG_PANEL_BG)
        frame_uploads.pack(fill="both", expand=True)
        for i in range(4):
            frame_uploads.columnconfigure(i, weight=1)
        frame_uploads.rowconfigure(0, weight=1)

        frame_juris = tk.LabelFrame(
            frame_uploads,
            text="📁 Jurisprudencia",
            padx=10,
            pady=10,
            bg=CONFIG_PANEL_BG,
        )
        frame_juris.grid(row=0, column=0, sticky="nsew", padx=5)

        btn_agregar_juris = tk.Button(
            frame_juris,
            text="➕ Agregar PDF",
            command=self.on_agregar_juris_pdf,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_agregar_juris.pack(fill="x", pady=(0, 5))

        btn_eliminar_juris_pdf = tk.Button(
            frame_juris,
            text="❌ Eliminar Documentos seleccionados",
            command=self.on_eliminar_juris_pdf,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_eliminar_juris_pdf.pack(fill="x", pady=(0, 5))

        self.list_juris = tk.Listbox(
            frame_juris, height=6, exportselection=False, selectmode=tk.MULTIPLE
        )
        self.list_juris.pack(fill="both", expand=True, pady=(5, 0))
        self.list_juris.bind("<Double-Button-1>", self.on_abrir_juris_pdf)

        frame_casos = tk.LabelFrame(
            frame_uploads,
            text="📁 Casos (carpeta)",
            padx=10,
            pady=10,
            bg=CONFIG_PANEL_BG,
        )
        frame_casos.grid(row=0, column=1, sticky="nsew", padx=5)

        lbl_nombre_caso = tk.Label(
            frame_casos, text="Nombre de Carpeta de Caso (nuevo o existente):"
        )
        lbl_nombre_caso.pack(anchor="w")

        self.entry_nombre_caso = tk.Entry(frame_casos)
        self.entry_nombre_caso.pack(fill="x", pady=(0, 5))

        btn_sel_caso_folder = tk.Button(
            frame_casos,
            text="Seleccionar Carpeta de Caso",
            command=self.select_casos_folder,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_sel_caso_folder.pack(fill="x", pady=(0, 5))

        btn_cargar_caso = tk.Button(
            frame_casos,
            text="📂 Cargar Caso",
            command=self.on_cargar_caso,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_cargar_caso.pack(fill="x", pady=(0, 5))

        btn_crear_caso = tk.Button(
            frame_casos,
            text="🆕 Crear Caso",
            command=self.on_crear_caso,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_crear_caso.pack(fill="x", pady=(0, 5))

        btn_agregar_pdf_caso = tk.Button(
            frame_casos,
            text="➕ Agregar PDF",
            command=self.on_agregar_pdf_caso,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_agregar_pdf_caso.pack(fill="x", pady=(0, 5))

        btn_actualizar_casos = tk.Button(
            frame_casos,
            text="🔄 Actualizar Casos",
            command=self.on_actualizar_casos,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_actualizar_casos.pack(fill="x", pady=(0, 5))

        btn_eliminar_caso = tk.Button(
            frame_casos,
            text="🗑️ Eliminar Caso",
            command=self.on_eliminar_caso,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_eliminar_caso.pack(fill="x", pady=(0, 5))

        self.list_casos = tk.Listbox(frame_casos, height=6, exportselection=False)
        self.list_casos.pack(fill="both", expand=True, pady=(5, 0))
        self.list_casos.bind("<<ListboxSelect>>", self.on_case_selected)

        tk.Label(frame_casos, text="Documentos del Caso:").pack(anchor="w")
        self.list_pdfs_caso = tk.Listbox(
            frame_casos, height=6, exportselection=False, selectmode=tk.MULTIPLE
        )
        self.list_pdfs_caso.pack(fill="both", expand=True, pady=(0, 5))
        self.list_pdfs_caso.bind("<Double-Button-1>", self.on_abrir_caso_pdf)

        btn_eliminar_pdf_caso = tk.Button(
            frame_casos,
            text="❌ Eliminar Documentos seleccionados",
            command=self.on_eliminar_pdf_caso,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_eliminar_pdf_caso.pack(fill="x", pady=(0, 5))

        frame_areas = tk.LabelFrame(
            frame_uploads, text="📁 Demandas", padx=10, pady=10, bg=CONFIG_PANEL_BG
        )
        frame_areas.grid(row=0, column=2, sticky="nsew", padx=5)

        lbl_nombre_area = tk.Label(
            frame_areas, text="Nombre de Carpeta de Área (nueva o existente):"
        )
        lbl_nombre_area.pack(anchor="w")

        self.entry_nombre_area = tk.Entry(frame_areas)
        self.entry_nombre_area.pack(fill="x", pady=(0, 5))

        btn_crear_area = tk.Button(
            frame_areas,
            text="🆕 Crear Área",
            command=self.on_crear_area,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_crear_area.pack(fill="x", pady=(0, 5))

        btn_eliminar_area = tk.Button(
            frame_areas,
            text="🗑️ Eliminar Área",
            command=self.on_eliminar_area,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_eliminar_area.pack(fill="x", pady=(0, 5))

        btn_agregar_pdf_area = tk.Button(
            frame_areas,
            text="➕ Agregar PDF",
            command=self.on_agregar_pdf_area,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_agregar_pdf_area.pack(fill="x", pady=(0, 5))

        btn_eliminar_pdf_area = tk.Button(
            frame_areas,
            text="❌ Eliminar Documentos seleccionados",
            command=self.on_eliminar_pdf_area,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_eliminar_pdf_area.pack(fill="x", pady=(0, 5))

        self.list_areas = tk.Listbox(frame_areas, height=6, exportselection=False)
        self.list_areas.pack(fill="both", expand=True, pady=(5, 0))
        self.list_areas.bind("<<ListboxSelect>>", self.on_area_selected)

        tk.Label(frame_areas, text="Documentos:").pack(anchor="w")
        self.list_area_pdfs = tk.Listbox(
            frame_areas, height=6, exportselection=False, selectmode=tk.MULTIPLE
        )
        self.list_area_pdfs.pack(fill="both", expand=True, pady=(0, 5))
        self.list_area_pdfs.bind("<Double-Button-1>", self.on_abrir_area_pdf)

        frame_status = tk.Frame(frame_uploads, padx=10, pady=10, bg=CONFIG_PANEL_BG)
        frame_status.grid(row=0, column=3, sticky="nsew", padx=5)

        lbl_estado = tk.Label(
            frame_status, text="Estado:", anchor="w", bg=CONFIG_PANEL_BG
        )
        lbl_estado.pack(anchor="w")
        self.txt_estado = tk.Label(
            frame_status,
            textvariable=self.status_text,
            fg=SUCCESS_COLOR,
            wraplength=200,
            justify="left",
            bg=CONFIG_PANEL_BG,
        )
        self.txt_estado.pack(anchor="w", fill="x")

        self.lbl_info = tk.Label(
            frame_status, text="", anchor="w", justify="left", bg=CONFIG_PANEL_BG
        )
        self.lbl_info.pack(anchor="w", fill="x", pady=(10, 0))

        # Mostrar logo y botón para cambiarlo
        logo_path = default_context.config_global.get(
            "logo_path",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png"),
        )
        if not os.path.isfile(logo_path):
            logo_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "logo.png",
            )
        try:
            img = Image.open(logo_path)
            img = img.resize((img.width // 2, img.height // 2))
            self.logo_img = ImageTk.PhotoImage(img)
            self.lbl_logo = tk.Label(frame_status, image=self.logo_img, bg=CONFIG_PANEL_BG)
            self.lbl_logo.pack(pady=(5, 0))
        except Exception as e:
            print(f"Error loading logo: {e}")


        btn_cambiar_logo = tk.Button(
            frame_status,
            text="Cambiar logo",
            command=self.on_cambiar_logo,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_cambiar_logo.pack(fill="x", pady=(5, 0))

        # ----- Modelo de IA -----
        frame_llm = tk.LabelFrame(
            frame_status, text="Modelo de IA", padx=10, pady=10, bg=CONFIG_PANEL_BG
        )
        frame_llm.pack(fill="x", pady=(10, 0))

        tk.Label(frame_llm, text="Proveedor:", bg=CONFIG_PANEL_BG).pack(anchor="w")
        self.var_llm_provider = tk.StringVar(
            value=default_context.config_global.get("llm_provider", "openai")
        )
        cmb_llm = ttk.Combobox(
            frame_llm, textvariable=self.var_llm_provider, state="readonly"
        )
        cmb_llm["values"] = ("deepseek", "openai")
        cmb_llm.pack(fill="x")

        btn_save_llm = tk.Button(
            frame_llm,
            text="Guardar",
            command=self.on_save_llm_provider,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_save_llm.pack(pady=(5, 0))


        # ----- Licencia -----
        frame_license = tk.LabelFrame(
            container, text="Licencia", padx=10, pady=10, bg=CONFIG_PANEL_BG
        )
        frame_license.pack(fill="x", padx=10, pady=(5, 10))

        tk.Label(frame_license, text="Correo electrónico:", bg=CONFIG_PANEL_BG).pack(
            anchor="w"
        )
        self.var_license_email = tk.StringVar(
            value=default_context.config_global.get("license_email", "")
        )
        self.entry_license_email = tk.Entry(
            frame_license, textvariable=self.var_license_email
        )
        self.entry_license_email.pack(fill="x")

        self.lbl_license_status = tk.Label(frame_license, text="", bg=CONFIG_PANEL_BG)
        self.lbl_license_status.pack(anchor="w", pady=(5, 0))

        btn_save_email = tk.Button(
            frame_license,
            text="Guardar correo",
            command=self.on_save_license_email,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_save_email.pack(pady=(5, 0))

        self.update_license_status()
        self.refresh_list_areas()

    # ------------------------ Pestaña Chat / Consulta General -----------------------
    def build_pestaña_chat(self, parent):
        frame_chat = ttk.PanedWindow(parent, orient="horizontal")
        frame_chat.pack(fill="both", expand=True, pady=10)

        frame_chat_left = tk.Frame(frame_chat)
        frame_chat.add(frame_chat_left, weight=3)

        frame_pdfs_right = tk.Frame(frame_chat)
        frame_chat.add(frame_pdfs_right, weight=1)
        self.frame_pdfs_right = frame_pdfs_right

        frame_case = tk.Frame(frame_chat_left)
        frame_case.pack(fill="x", padx=5, pady=(0, 5))
        tk.Label(frame_case, text="Caso:").pack(side="left")
        self.var_dropdown_casos_chat = tk.StringVar(value=CHAT_WITH_AI_OPTION)
        self.dropdown_casos_chat = ttk.Combobox(
            frame_case,
            textvariable=self.var_dropdown_casos_chat,
            state="readonly",
        )
        cases = [CHAT_WITH_AI_OPTION] + self.get_lista_carpeta_casos()
        self.dropdown_casos_chat["values"] = cases
        self.dropdown_casos_chat.set(CHAT_WITH_AI_OPTION)
        self.dropdown_casos_chat.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.dropdown_casos_chat.bind(
            "<<ComboboxSelected>>", self.on_chat_case_selected
        )

        self.lbl_caso_actual = tk.Label(frame_case, textvariable=self.caso_seleccionado)
        self.lbl_caso_actual.pack(side="left")

        frame_pdfs = tk.Frame(frame_chat_left)
        frame_pdfs.pack(fill="x", padx=5, pady=(0, 5))
        btn_upload_pdf = tk.Button(
            frame_pdfs, text="📄 Subir PDF", command=self.on_upload_chat_pdfs
        )
        btn_upload_pdf.pack(side="left")

        self.chat_pdf_preview_frame = tk.Frame(frame_pdfs_right)
        self.chat_pdf_preview_frame.pack(fill="both", expand=True)
        self.var_jurisprudencia = tk.BooleanVar(value=True)
        self._render_jurisprudencia_checkbox()

        self.chat_general_area = scrolledtext.ScrolledText(
            frame_chat_left, wrap="word", state="normal", height=30
        )
        self.chat_general_area.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.chat_general_area.bind("<Key>", lambda _: "break")
        self.chat_general_area.bind("<Control-c>", self.on_copy_chat_selected)

        self.chat_general_area.tag_config(
            "user", foreground="blue", font=("TkDefaultFont", 10, "bold")
        )
        self.chat_general_area.tag_config(
            "bot", foreground="darkgreen", font=("TkDefaultFont", 10, "normal")
        )

        frame_input = tk.Frame(frame_chat_left, pady=5)
        frame_input.pack(fill="x", padx=5)

        self.entry_chat_general = tk.Entry(frame_input, font=ENTRY_FONT, bg=ENTRY_BG)
        self.entry_chat_general.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_chat_general.bind(
            "<Control-c>", lambda e: self.entry_chat_general.event_generate("<<Copy>>")
        )
        self.entry_chat_general.bind(
            "<Control-x>", lambda e: self.entry_chat_general.event_generate("<<Cut>>")
        )
        self.entry_chat_general.bind(
            "<Control-v>", lambda e: self.entry_chat_general.event_generate("<<Paste>>")
        )

        btn_send = tk.Button(
            frame_input, text="▶️ Enviar", command=self.on_send_chat_general
        )
        btn_send.pack(side="left")
        btn_clear = tk.Button(
            frame_input, text="🧹 Limpiar", command=self.on_clear_chat_general
        )
        btn_clear.pack(side="left", padx=(5, 0))

        btn_copy = tk.Button(
            frame_input,
            text="Copiar texto seleccionado",
            command=self.on_copy_chat_selected,
        )
        btn_copy.pack(side="left", padx=(5, 0))

        self.lbl_chat_status = tk.Label(
            frame_chat_left,
            textvariable=self.chat_status_text,
            anchor="w",
        )
        self.lbl_chat_status.pack(fill="x", padx=5, pady=(5, 0))

    # ----------------------------- Pestaña Generar Demanda ----------------------------
    def build_pestaña_generar_demanda(self, parent):
        frame_dem = tk.Frame(parent, pady=10)
        frame_dem.pack(fill="both", expand=True)

        frame_case = tk.Frame(frame_dem)
        frame_case.pack(fill="x", padx=5, pady=(0, 5))
        tk.Label(frame_case, text="Área:").pack(side="left")
        self.dropdown_areas_demanda = ttk.Combobox(
            frame_case,
            textvariable=self.var_area,
            state="readonly",
        )
        self.dropdown_areas_demanda["values"] = self.get_lista_areas()
        self.dropdown_areas_demanda.pack(
            side="left", fill="x", expand=True, padx=(5, 5)
        )
        self.dropdown_areas_demanda.bind(
            "<<ComboboxSelected>>", self.on_dropdown_area_selected
        )

        frame_select = tk.Frame(frame_dem)
        frame_select.pack(fill="x", padx=5, pady=(0, 5))

        tk.Label(frame_select, text="Ejemplo:").pack(side="left")
        self.var_demanda = tk.StringVar(value="")
        # Ajustamos el ancho del desplegable a la mitad de la pantalla para
        # facilitar la lectura de nombres largos
        pantalla_ancho = self.root.winfo_screenwidth()
        ancho_chars = max(20, (pantalla_ancho // 2) // 10)
        self.dropdown_demandas = ttk.Combobox(
            frame_select,
            textvariable=self.var_demanda,
            state="readonly",
            width=ancho_chars,
        )
        self.dropdown_demandas["values"] = self.get_lista_demandas()
        self.dropdown_demandas.pack(side="left", padx=(5, 15))

        self.dropdown_demandas.bind(
            "<<ComboboxSelected>>", lambda e: self.on_generar_desde_dropdown()
        )

        # Botón para visualizar el PDF original
        btn_abrir = tk.Button(
            frame_select,
            text="Abrir PDF",
            command=self.on_abrir_demanda_desde_dropdown,
        )
        btn_abrir.pack(side="left", padx=(5, 0))

        btn_form = tk.Button(
            frame_select,
            text="Formulario Demanda",
            command=self.on_formulario_demanda,
        )
        btn_form.pack(side="left", padx=(5, 0))

        self.chat_demanda_area = scrolledtext.ScrolledText(
            frame_dem,
            wrap="word",
            height=25,
            undo=True,
            autoseparators=True,
            maxundo=-1,
        )
        self.chat_demanda_area.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.chat_demanda_area.tag_config("highlight", background="yellow")
        for seq in ("<Control-z>", "<Control-Z>"):
            self.chat_demanda_area.bind(
                seq, lambda e: self.chat_demanda_area.edit_undo()
            )

        self.chat_demanda_menu = tk.Menu(self.chat_demanda_area, tearoff=0)
        self.chat_demanda_menu.add_command(
            label="Mejorar con IA", command=self.on_mejorar_fragmento_demanda
        )
        self.chat_demanda_area.bind("<Button-3>", self._show_chat_demanda_menu)

        self.btn_export_word = tk.Button(
            frame_dem,
            text="📄 Descargar Demanda a Word",
            command=self.on_exportar_word_demanda,
        )
        self.btn_export_word.pack(fill="x", padx=5, pady=(5, 0))

        self.btn_export_pdf = tk.Button(
            frame_dem,
            text="📄 Descargar Demanda a PDF",
            command=self.on_exportar_pdf_demanda,
        )
        self.btn_export_pdf.pack(fill="x", padx=5, pady=(5, 0))

    # ----------------------------- Pestaña Palabras Clave ----------------------------
    def build_pestaña_palabras_clave(self, parent):
        frame_ej = tk.Frame(parent, pady=10)
        frame_ej.pack(fill="both", expand=True, padx=10, pady=10)

        lbl_desc = tk.Label(frame_ej, text="Ingresa palabras clave o temas:")
        lbl_desc.pack(anchor="w")

        self.palabras_mode = tk.StringVar(value="semantica")
        frame_mode = tk.Frame(frame_ej, bg=FRAME_BG)
        frame_mode.pack(anchor="w", pady=(5, 5))
        tk.Radiobutton(
            frame_mode,
            text="Búsqueda exacta",
            variable=self.palabras_mode,
            value="exacta",
            bg=FRAME_BG,
            fg=TEXT_COLOR,
            selectcolor=FRAME_BG,
        ).pack(side="left")
        tk.Radiobutton(
            frame_mode,
            text="Búsqueda semántica",
            variable=self.palabras_mode,
            value="semantica",
            bg=FRAME_BG,
            fg=TEXT_COLOR,
            selectcolor=FRAME_BG,
        ).pack(side="left", padx=(10, 0))

        self.entry_palabras = tk.Entry(frame_ej, font=ENTRY_FONT, bg=ENTRY_BG)
        self.entry_palabras.pack(fill="x", pady=(0, 5))

        btn_buscar = tk.Button(
            frame_ej, text="🔍 Buscar Artículos", command=self.on_buscar_palabras_clave
        )
        btn_buscar.pack(pady=(0, 10))

        self.txt_respuesta = scrolledtext.ScrolledText(
            frame_ej, wrap="word", state="normal", height=12
        )
        self.txt_respuesta.pack(fill="both", expand=True)
        self.txt_respuesta.bind("<Key>", self.on_palabras_key)

        self.links_palabras = tk.Frame(frame_ej)
        self.links_palabras.pack(fill="x", pady=(5, 0))

        frame_pal_btn = tk.Frame(frame_ej)
        frame_pal_btn.pack(pady=(5, 0))

        btn_clear = tk.Button(
            frame_pal_btn, text="🧹 Limpiar", command=self.on_clear_palabras
        )
        btn_clear.pack(side="left")

        btn_copy = tk.Button(
            frame_pal_btn,
            text="Copiar texto seleccionado",
            command=self.on_copy_palabras_selected,
        )
        btn_copy.pack(side="left", padx=(5, 0))

        self.lbl_palabras_status = tk.Label(
            frame_ej,
            textvariable=self.palabras_status_text,
            anchor="w",
        )
        self.lbl_palabras_status.pack(fill="x", pady=(5, 0))

    # ----------------------------- Pestaña Casos -----------------------------
    def build_pestaña_casos(self, parent):
        frame = tk.Frame(parent, pady=10)
        frame.pack(fill="both", expand=True)

        frame_sel = tk.Frame(frame)
        frame_sel.pack(fill="x", padx=5, pady=(0, 5))
        tk.Label(frame_sel, text="Caso:").pack(side="left")
        self.var_caso_tab = tk.StringVar(value="")
        self.dropdown_casos_tab = ttk.Combobox(
            frame_sel, textvariable=self.var_caso_tab, state="readonly"
        )
        self.dropdown_casos_tab["values"] = self.get_lista_carpeta_casos()
        self.dropdown_casos_tab.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.dropdown_casos_tab.bind("<<ComboboxSelected>>", self.on_tab_case_selected)
        frame_content = tk.Frame(frame)
        frame_content.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        frame_content.columnconfigure(0, weight=1)
        frame_content.columnconfigure(1, weight=3)
        frame_content.rowconfigure(0, weight=1)

        frame_list = tk.Frame(frame_content)
        frame_list.grid(row=0, column=0, sticky="nsew")
        frame_list.columnconfigure(0, weight=1)
        frame_list.rowconfigure(0, weight=1)
        self.list_pdfs_caso_tab = tk.Listbox(
            frame_list, height=15, exportselection=False
        )
        self.list_pdfs_caso_tab.grid(row=0, column=0, sticky="nsew")
        self.list_pdfs_caso_tab.bind("<<ListboxSelect>>", self.on_select_pdf_caso_tab)

        frame_btn = tk.Frame(frame_list)
        frame_btn.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        btn_open = tk.Button(frame_btn, text="Ver PDF", command=self.on_tab_abrir_pdf)
        btn_open.pack(side="left")
        self.btn_resumen = tk.Button(frame_btn, text="Resumen", command=self.on_tab_resumen)
        self.btn_resumen.pack(side="left", padx=(5, 0))

        frame_preview = tk.Frame(frame_content)
        frame_preview.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.lbl_pdf_trabajo = tk.Label(frame_preview, text="Trabajando en: Ninguno")
        self.lbl_pdf_trabajo.pack(anchor="w")
        self.pdf_preview_label = tk.Label(frame_preview)
        self.pdf_preview_label.pack(fill="both", expand=True, pady=(5, 0))

        self.text_resumen_caso = scrolledtext.ScrolledText(
            frame, wrap="word", height=12
        )
        self.text_resumen_caso.pack(fill="both", expand=True, padx=5, pady=(5, 5))
        self.text_resumen_caso.bind("<Key>", lambda _: "break")

    # ----------------------------- Pestaña Tokens ----------------------------
    def build_pestaña_tokens(self, parent):
        tokens.init_db()
        self.tokens_usados = tokens.get_tokens()
        self.saldo_actual = tokens.get_credit()

        frame_info = tk.LabelFrame(parent, text="Saldo", pady=5, padx=10, bg=FRAME_BG)
        frame_info.pack(fill="x", padx=10, pady=(10, 5))

        self.lbl_tokens = tk.Label(frame_info, font=("TkDefaultFont", 12))
        self.lbl_tokens.pack()

        self.lbl_credito = tk.Label(frame_info, font=("TkDefaultFont", 12))
        self.lbl_credito.pack()

        frame_ops = tk.LabelFrame(parent, text="Créditos", pady=5, padx=10, bg=FRAME_BG)
        frame_ops.pack(fill="x", padx=10, pady=(0, 5))

        frm_add = tk.Frame(frame_ops, bg=FRAME_BG)
        frm_add.pack(pady=5)
        btn_import = tk.Button(
            frm_add,
            text="Importar archivo",
            command=self.on_import_credit_file,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_import.pack(side="left", padx=5)

        btn_reset = tk.Button(
            frame_ops,
            text="Reiniciar contador",
            command=self.on_reset_tokens,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_reset.pack(pady=5)

        frm_filter = tk.LabelFrame(parent, text="Filtro", pady=5, padx=10, bg=FRAME_BG)
        frm_filter.pack(fill="x", padx=10, pady=(0, 5))
        tk.Label(frm_filter, text="Fecha desde (YYYY-MM-DD)").pack(side="left")
        self.entry_fecha_desde = DateEntry(
            frm_filter, width=12, date_pattern="yyyy-mm-dd"
        )
        self.entry_fecha_desde.configure(validate="none")
        self.entry_fecha_desde.delete(0, tk.END)
        self.entry_fecha_desde.pack(side="left", padx=(0, 5))
        tk.Label(frm_filter, text="Fecha hasta (YYYY-MM-DD)").pack(side="left")
        self.entry_fecha_hasta = DateEntry(
            frm_filter, width=12, date_pattern="yyyy-mm-dd"
        )
        self.entry_fecha_hasta.configure(validate="none")
        self.entry_fecha_hasta.delete(0, tk.END)
        self.entry_fecha_hasta.pack(side="left", padx=(0, 5))
        btn_filtrar = tk.Button(
            frm_filter, text="Filtrar", command=self.update_token_log
        )
        btn_filtrar.pack(side="left", padx=5)

        frame_log = tk.LabelFrame(
            parent, text="Historial", pady=5, padx=10, bg=FRAME_BG
        )
        frame_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        columns = (
            "fecha",
            "actividad",
            "tokens_in",
            "tokens_out",
            "tokens",
            "costo_cliente",
        )
        self.tree_token_log = ttk.Treeview(
            frame_log, columns=columns, show="headings", height=5
        )
        self.tree_token_log.heading("fecha", text="Fecha/Hora")
        self.tree_token_log.heading("actividad", text="Actividad")
        self.tree_token_log.heading("tokens_in", text="Tokens entrada")
        self.tree_token_log.heading("tokens_out", text="Tokens salida")
        self.tree_token_log.heading("tokens", text="Tokens totales")
        self.tree_token_log.heading("costo_cliente", text="Precio cliente")
        self.tree_token_log.column("fecha", width=150)
        self.tree_token_log.column("actividad", width=200)
        self.tree_token_log.column("tokens_in", width=80, anchor="e")
        self.tree_token_log.column("tokens_out", width=80, anchor="e")
        self.tree_token_log.column("tokens", width=80, anchor="e")
        self.tree_token_log.column("costo_cliente", width=100, anchor="e")
        self.tree_token_log.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.tree_token_log.bind("<Double-Button-1>", self.on_edit_token_activity)
        self.update_token_log()

        self.update_token_label()
        self.root.after(2000, self.poll_tokens)

    # --------------------------- Pestaña ID y Clave -------------------------
    def build_pestaña_id_clave(self, parent):
        frame_user = tk.LabelFrame(
            parent, text="Usuario", pady=10, padx=10, bg=FRAME_BG
        )
        frame_user.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(frame_user, text="Correo electrónico:").pack(pady=(0, 5))
        self.var_id_email = tk.StringVar(
            value=default_context.config_global.get("license_email", "")
        )
        self.entry_id_email = tk.Entry(
            frame_user, textvariable=self.var_id_email, width=30, state="disabled"
        )
        self.entry_id_email.pack()

        btn_gen = tk.Button(
            frame_user,
            text="Generar ID",
            command=self.on_generate_user_id,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_gen.pack(pady=5)

        tk.Label(frame_user, text="ID generado:").pack(pady=(10, 5))
        self.var_id_output = tk.StringVar()
        tk.Entry(
            frame_user, textvariable=self.var_id_output, width=50, state="readonly"
        ).pack()

        btn_copy = tk.Button(
            frame_user,
            text="Copiar ID",
            command=self.on_copy_user_id,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_copy.pack(pady=5)

        self.frame_admin = tk.LabelFrame(
            parent, text="Administrador", pady=10, padx=10, bg=FRAME_BG
        )

        frame_credit = tk.LabelFrame(
            self.frame_admin, text="Créditos", pady=5, padx=5, bg=FRAME_BG
        )
        frame_credit.pack(fill="x")

        row = tk.Frame(frame_credit)
        row.pack(fill="x")
        tk.Label(row, text="Monto en dólares:").pack(side="left")
        self.var_credito_gen = tk.StringVar()
        tk.Entry(row, textvariable=self.var_credito_gen, width=10).pack(
            side="left", padx=(5, 0)
        )

        row = tk.Frame(frame_credit)
        row.pack(fill="x", pady=(5, 0))
        tk.Label(row, text="ID del usuario:").pack(side="left")
        self.var_credito_id = tk.StringVar()
        tk.Entry(row, textvariable=self.var_credito_id, width=30).pack(
            side="left", padx=(5, 0)
        )

        row = tk.Frame(frame_credit)
        row.pack(fill="x", pady=(5, 0))
        tk.Label(row, text="Correo del usuario:").pack(side="left")
        self.var_credito_email = tk.StringVar()
        tk.Entry(row, textvariable=self.var_credito_email, width=30).pack(
            side="left", padx=(5, 0)
        )

        row = tk.Frame(frame_credit)
        row.pack(pady=5)
        btn_gen_clave = tk.Button(
            row,
            text="Generar archivo",
            command=self.on_generate_credit_file,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_gen_clave.pack(side="left")
        btn_reset_credit = tk.Button(
            row,
            text="Dejar saldo en cero",
            command=self.on_reset_credit_balance,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_reset_credit.pack(side="left", padx=(5, 0))

        self.lbl_credito_gen = tk.Label(frame_credit, text="")
        self.lbl_credito_gen.pack()

        frame_enc = tk.LabelFrame(
            self.frame_admin, text="Encriptar texto", pady=5, padx=5, bg=FRAME_BG
        )
        frame_enc.pack(fill="x", pady=(10, 0))

        row = tk.Frame(frame_enc)
        row.pack(fill="x")
        tk.Label(row, text="Texto a encriptar:").pack(side="left")
        self.var_encrypt_input = tk.StringVar()
        tk.Entry(row, textvariable=self.var_encrypt_input, width=30).pack(
            side="left", padx=(5, 0), fill="x", expand=True
        )

        btn_encrypt = tk.Button(
            frame_enc,
            text="Encriptar",
            command=self.on_encrypt_text,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_encrypt.pack(pady=5)

        row = tk.Frame(frame_enc)
        row.pack(fill="x")
        tk.Label(row, text="Resultado:").pack(side="left")
        self.var_encrypt_output = tk.StringVar()
        tk.Entry(
            row, textvariable=self.var_encrypt_output, width=50, state="readonly"
        ).pack(side="left", padx=(5, 0), fill="x", expand=True)

        btn_copy_enc = tk.Button(
            frame_enc,
            text="Copiar",
            command=self.on_copy_encrypted_text,
            bg=CONFIG_BTN_BG,
            fg=BUTTON_TEXT_COLOR,
            activebackground=CONFIG_BTN_BG,
            activeforeground=BUTTON_TEXT_COLOR,
        )
        btn_copy_enc.pack(pady=5)

    # --------------------------- Pestaña Créditos -------------------------
    def build_pestaña_creditos(self, parent):
        logo_path = default_context.config_global.get(
            "logo_path",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png"),
        )
        if not os.path.isfile(logo_path):
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png")
        try:
            self.logo_credit_img = tk.PhotoImage(file=logo_path)
            self.lbl_logo_credit = tk.Label(parent, image=self.logo_credit_img)
            self.lbl_logo_credit.pack(pady=(20, 10))
        except Exception as e:
            print(f"Error loading logo: {e}")
        tk.Label(
            parent,
            text=(
                "LEXA - tu asesor legal potenciado por IA\n"
                "Desarrollado por Ing. Marco Castelo.\n"
                "Jurídico: Ab. Marcos Dávalos.\n"
                "Contactos: +593 99 569 9755 / +593959733823\n"
                "Riobamba, Ecuador\n"
                "Todos los derechos reservados."
            ),
            justify="center",
        ).pack(padx=20, pady=10)

    # ------------------------------- Métodos auxiliares -------------------------------
    def get_lista_carpeta_casos(self):
        return sorted(
            [
                os.path.basename(p)
                for p in glob.glob(os.path.join(CASOS_DIR_ROOT, "*"))
                if os.path.isdir(p)
            ]
        )

    def get_lista_demandas(self):
        return sorted(default_context.demandas_textos.keys())

    def get_lista_juris(self):
        return sorted(
            [
                os.path.relpath(p, JURIS_DIR)
                for p in glob.glob(
                    os.path.join(JURIS_DIR, "**", "*.pdf"), recursive=True
                )
            ]
        )

    def get_lista_carpetas_demandas(self):
        carpetas = {
            os.path.relpath(os.path.dirname(p), DEMANDAS_DIR)
            for p in glob.glob(
                os.path.join(DEMANDAS_DIR, "**", "*.pdf"), recursive=True
            )
        }
        return sorted(c if c != "." else "" for c in carpetas)

    def get_lista_pdfs_demandas(self, carpeta=""):
        patron = os.path.join(DEMANDAS_DIR, carpeta, "*.pdf")
        return sorted(os.path.basename(p) for p in glob.glob(patron))

    def get_lista_areas(self):
        return listar_areas()

    def get_lista_pdfs_area(self, nombre):
        return listar_pdfs_de_area(nombre)

    def get_lista_pdfs_caso(self, nombre):
        carpeta = os.path.join(CASOS_DIR_ROOT, nombre)
        archivos = []
        for patron in ("*.pdf", "*.txt"):
            archivos.extend(
                glob.glob(os.path.join(carpeta, "**", patron), recursive=True)
            )
        return sorted(os.path.relpath(p, carpeta) for p in archivos)

    def refresh_list_juris(self):
        if hasattr(self, "list_juris"):
            self.list_juris.delete(0, tk.END)
            for name in self.get_lista_juris():
                self.list_juris.insert(tk.END, name)

    def refresh_list_casos(self):
        lista = self.get_lista_carpeta_casos()
        if hasattr(self, "list_casos"):
            self.list_casos.delete(0, tk.END)
            for name in lista:
                self.list_casos.insert(tk.END, name)
            if self.caso_seleccionado.get() in lista:
                idx = lista.index(self.caso_seleccionado.get())
                self.list_casos.selection_set(idx)
        if hasattr(self, "dropdown_casos_chat"):
            current = self.caso_seleccionado.get()
            lista_chat = [CHAT_WITH_AI_OPTION] + lista
            self.dropdown_casos_chat["values"] = lista_chat
            if current:
                if current in lista:
                    self.dropdown_casos_chat.set(current)
                else:
                    self.dropdown_casos_chat.set(CHAT_WITH_AI_OPTION)
            else:
                self.dropdown_casos_chat.set(CHAT_WITH_AI_OPTION)
        if hasattr(self, "dropdown_casos_tab"):
            current = self.caso_seleccionado.get()
            self.dropdown_casos_tab["values"] = lista
            if current in lista:
                self.dropdown_casos_tab.set(current)
        self.refresh_list_pdfs_caso(self.caso_seleccionado.get())

    def refresh_list_pdfs_caso(self, nombre=None):
        if hasattr(self, "list_pdfs_caso"):
            self.list_pdfs_caso.delete(0, tk.END)
            if nombre:
                for pdf in self.get_lista_pdfs_caso(nombre):
                    self.list_pdfs_caso.insert(tk.END, pdf)
        if hasattr(self, "list_pdfs_caso_tab"):
            self.list_pdfs_caso_tab.delete(0, tk.END)
            if nombre:
                for pdf in self.get_lista_pdfs_caso(nombre):
                    self.list_pdfs_caso_tab.insert(tk.END, pdf)

    def refresh_list_demandas(self):
        if hasattr(self, "list_demanda_carpetas"):
            self.list_demanda_carpetas.delete(0, tk.END)
            for name in self.get_lista_carpetas_demandas():
                self.list_demanda_carpetas.insert(tk.END, name or "/")
        if hasattr(self, "list_demandas"):
            carpeta = (
                self.var_demanda_carpeta.get()
                if hasattr(self, "var_demanda_carpeta")
                else ""
            )
            self.list_demandas.delete(0, tk.END)
            for name in self.get_lista_pdfs_demandas(carpeta):
                self.list_demandas.insert(tk.END, name)

    def refresh_list_areas(self):
        if hasattr(self, "list_areas"):
            self.list_areas.delete(0, tk.END)
            for name in self.get_lista_areas():
                self.list_areas.insert(tk.END, name)
        if hasattr(self, "list_area_pdfs"):
            area = self.var_area.get() if hasattr(self, "var_area") else ""
            self.list_area_pdfs.delete(0, tk.END)
            for name in self.get_lista_pdfs_area(area):
                self.list_area_pdfs.insert(tk.END, name)
        if hasattr(self, "dropdown_areas_demanda"):
            lista = self.get_lista_areas()
            current = self.var_area.get()
            self.dropdown_areas_demanda["values"] = lista
            if current in lista:
                self.dropdown_areas_demanda.set(current)
            else:
                self.dropdown_areas_demanda.set("")
        if hasattr(self, "dropdown_demandas"):
            area = self.var_area.get() if hasattr(self, "var_area") else ""
            docs = self.get_lista_pdfs_area(area)
            self.dropdown_demandas["values"] = docs
            if self.var_demanda.get() not in docs:
                self.var_demanda.set("")

    def update_info_label(self):
        if hasattr(self, "lbl_info"):
            juris = default_context.ruta_juris or "N/A"
            count = len(default_context.demandas_textos)
            areas = len(self.get_lista_areas())
            self.lbl_info.config(
                text=f"Juris: {juris}\nPlantillas: {count}\nÁreas: {areas}"
            )

    def on_case_selected(self, event=None):
        if not hasattr(self, "list_casos"):
            return
        sel = self.list_casos.curselection()
        if sel:
            nombre = self.list_casos.get(sel[0])
            self.entry_nombre_caso.delete(0, tk.END)
            self.entry_nombre_caso.insert(0, nombre)
            self.caso_seleccionado.set(nombre)
            self.refresh_list_pdfs_caso(nombre)
            demandas.analizar_caso(nombre)

    def on_chat_case_selected(self, event=None):
        nombre = self.var_dropdown_casos_chat.get()
        if not nombre:
            return
        if nombre == CHAT_WITH_AI_OPTION:
            self.caso_seleccionado.set("")
            if hasattr(self, "list_casos"):
                self.list_casos.selection_clear(0, tk.END)
            self.refresh_list_pdfs_caso("")
            return
        self.caso_seleccionado.set(nombre)
        if hasattr(self, "list_casos"):
            items = list(self.list_casos.get(0, tk.END))
            if nombre in items:
                idx = items.index(nombre)
                self.list_casos.selection_clear(0, tk.END)
                self.list_casos.selection_set(idx)
        self.refresh_list_pdfs_caso(nombre)
        demandas.analizar_caso(nombre)
        self._suggest_area_for_case(nombre)

    def _suggest_area_for_case(self, nombre_caso):
        """Preselect an area based on the case description."""
        descripcion = ""
        try:
            for row in db.get_casos():
                if row[2] == nombre_caso:
                    descripcion = row[3] or ""
                    break
        except Exception:
            return
        if not descripcion:
            return
        sugerencias = suggest_type(descripcion)
        if not sugerencias:
            return
        areas = self.get_lista_areas()
        for sug in sugerencias:
            if sug in areas:
                self.var_area.set(sug)
                if hasattr(self, "dropdown_areas_demanda"):
                    self.dropdown_areas_demanda.set(sug)
                return
        messagebox.showinfo(
            "Sugerencia de área",
            f"Áreas sugeridas: {', '.join(sugerencias)}",
        )

    def on_demanda_carpeta_selected(self, event=None):
        sel = self.list_demanda_carpetas.curselection()
        carpeta = self.list_demanda_carpetas.get(sel[0]) if sel else ""
        self.var_demanda_carpeta.set(carpeta if carpeta != "/" else "")
        self.refresh_list_demandas()

    def select_juris_folder(self):
        carpeta = filedialog.askdirectory(title="Seleccionar Carpeta de Jurisprudencia")
        if carpeta:
            self.folder_juris = carpeta
            self.status_text.set(
                f"📂 Carpeta de Jurisprudencia seleccionada: {os.path.basename(carpeta)}"
            )

    def on_cargar_juris(self):
        if not getattr(self, "folder_juris", None):
            messagebox.showwarning(
                "Advertencia", "No seleccionaste ninguna carpeta de jurisprudencia."
            )
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()

        def worker():
            try:
                msg = guardar_jurisprudencia_por_carpeta(self.folder_juris)
            except Exception as e:  # pragma: no cover - UI error handling

                def report_error():
                    self.status_text.set(f"Error: {e}")
                    messagebox.showerror("Error", str(e))

                self.root.after(0, report_error)
                return

            def update_ui():
                self.status_text.set(msg)
                self.refresh_list_juris()
                self.update_info_label()
                messagebox.showinfo("Carga completada", msg)

            self.root.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()
    def actualizar_directorios(self):
        """Actualizar jurisprudencia, casos y demandas en secuencia."""
        self.status_text.set("Actualizando jurisprudencia...")
        self.root.update_idletasks()
        self.on_actualizar_juris()

        self.status_text.set("Actualizando casos...")
        self.root.update_idletasks()
        self.on_actualizar_casos()

        self.status_text.set("Actualizando demandas...")
        self.root.update_idletasks()
        self.on_actualizar_demandas()

        self.status_text.set("Directorios actualizados correctamente.")

    def on_actualizar_juris(self):
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msg = actualizar_jurisprudencia()
        self.status_text.set(msg)
        self.refresh_list_juris()
        self.update_info_label()
        messagebox.showinfo("Jurisprudencia actualizada", msg)

    def on_eliminar_juris(self):
        msg = eliminar_jurisprudencia()
        self.status_text.set(msg)
        self.refresh_list_juris()
        self.update_info_label()

    def on_eliminar_juris_pdf(self):
        sel = self.list_juris.curselection()
        if sel:
            nombres = [self.list_juris.get(i) for i in sel]
            if messagebox.askyesno("Confirmación", f"¿Eliminar {', '.join(nombres)}?"):
                msgs = []
                for nombre in nombres:
                    msgs.append(eliminar_jurisprudencia_pdf(nombre))
                self.status_text.set("\n".join(msgs))
                self.refresh_list_juris()
                self.update_info_label()

    def on_agregar_juris_pdf(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")]
        )
        if not archivos:
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()

        def worker():
            try:
                msgs = []
                for a in archivos:
                    try:
                        msgs.append(agregar_jurisprudencia_pdf(a))
                    except Exception as e:  # pragma: no cover - per-file error
                        msgs.append(f"Error: {e}")
                joined = "\n".join(msgs)
            except Exception as e:  # pragma: no cover - unexpected error

                def report_error():
                    self.status_text.set(f"Error: {e}")
                    messagebox.showerror("Error", str(e))

                self.root.after(0, report_error)
                return

            def update_ui():
                self.status_text.set(joined)
                self.refresh_list_juris()
                self.update_info_label()
                messagebox.showinfo("Carga completada", joined)

            self.root.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def select_casos_folder(self):
        carpeta = filedialog.askdirectory(title="Seleccionar Carpeta de Caso")
        if carpeta:
            self.folder_casos = carpeta
            nombre = os.path.basename(carpeta.rstrip(os.sep))
            self.entry_nombre_caso.delete(0, tk.END)
            self.entry_nombre_caso.insert(0, nombre)
            self.status_text.set(f"📂 Carpeta de Caso seleccionada: {nombre}")

    def on_cargar_caso(self):
        if not getattr(self, "folder_casos", None):
            messagebox.showwarning(
                "Advertencia", "No seleccionaste ninguna carpeta de caso."
            )
            return
        nombre_caso = self.entry_nombre_caso.get().strip()
        if not nombre_caso:
            messagebox.showwarning(
                "Advertencia", "Debes escribir un nombre de carpeta para el caso."
            )
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msg, lista_casos = guardar_caso_por_carpeta(self.folder_casos, nombre_caso)
        self.status_text.set(msg)
        if nombre_caso in lista_casos:
            self.caso_seleccionado.set(nombre_caso)
        self.refresh_list_casos()
        messagebox.showinfo("Carga completada", msg)

    def on_actualizar_casos(self):
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msg = actualizar_casos()
        self.status_text.set(msg)
        self.refresh_list_casos()
        messagebox.showinfo("Casos actualizados", msg)

    def on_eliminar_caso(self):
        nombre_caso = self.entry_nombre_caso.get().strip()
        if not nombre_caso:
            messagebox.showwarning(
                "Advertencia", "Debes escribir un nombre de carpeta para el caso."
            )
            return
        if messagebox.askyesno("Confirmación", f"¿Eliminar el caso '{nombre_caso}'?"):
            msg = eliminar_caso(nombre_caso)
            self.status_text.set(msg)
            if self.caso_seleccionado.get() == nombre_caso:
                self.caso_seleccionado.set("")
            self.refresh_list_casos()
            self.refresh_list_pdfs_caso("")

    def on_crear_caso(self):
        nombre = self.entry_nombre_caso.get().strip()
        if not nombre:
            messagebox.showwarning(
                "Advertencia", "Debes escribir un nombre para el caso."
            )
            return
        msg = crear_caso(nombre)
        self.status_text.set(msg)
        self.caso_seleccionado.set(nombre)
        self.refresh_list_casos()
        self.refresh_list_pdfs_caso(nombre)
        messagebox.showinfo("Caso creado", msg)

    def on_agregar_pdf_caso(self):
        nombre = self.entry_nombre_caso.get().strip()
        if not nombre:
            messagebox.showwarning(
                "Advertencia", "Debes escribir o seleccionar un caso."
            )
            return
        archivos = filedialog.askopenfilenames(
            title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")]
        )
        if not archivos:
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msgs = []
        for a in archivos:
            msgs.append(agregar_pdf_a_caso(a, nombre))
        self.status_text.set("\n".join(msgs))
        self.refresh_list_casos()
        self.refresh_list_pdfs_caso(nombre)
        messagebox.showinfo("Carga completada", "\n".join(msgs))

    def on_eliminar_pdf_caso(self):
        nombre = self.caso_seleccionado.get()
        if not nombre:
            messagebox.showwarning("Advertencia", "Debes seleccionar un caso.")
            return
        sel = self.list_pdfs_caso.curselection()
        if sel:
            docs = [self.list_pdfs_caso.get(i) for i in sel]
            if messagebox.askyesno(
                "Confirmación",
                f"¿Eliminar {', '.join(docs)} del caso '{nombre}'?",
            ):
                msgs = []
                for doc in docs:
                    msgs.append(eliminar_pdf_de_caso(doc, nombre))
                self.status_text.set("\n".join(msgs))
                self.refresh_list_pdfs_caso(nombre)
                self.refresh_list_casos()

    def select_demandas_folder(self):
        carpeta = filedialog.askdirectory(
            title="Seleccionar Carpeta de Demandas de Ejemplo"
        )
        if carpeta:
            self.folder_demandas = carpeta
            self.status_text.set(
                f"📂 Carpeta de Demandas seleccionada: {os.path.basename(carpeta)}"
            )

    def on_cargar_demandas(self):
        if not getattr(self, "folder_demandas", None):
            messagebox.showwarning(
                "Advertencia",
                "No seleccionaste ninguna carpeta de demandas de ejemplo.",
            )
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msg = guardar_demandas_por_carpeta(self.folder_demandas)
        self.status_text.set(msg)
        self.dropdown_demandas["values"] = self.get_lista_demandas()
        self.refresh_list_demandas()
        self.update_info_label()
        messagebox.showinfo("Carga completada", msg)

    def on_actualizar_demandas(self):
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msg = actualizar_demandas()
        self.status_text.set(msg)
        self.dropdown_demandas["values"] = self.get_lista_demandas()
        self.refresh_list_demandas()
        self.update_info_label()
        messagebox.showinfo("Demandas actualizadas", msg)

    def on_eliminar_demandas(self):
        msg = eliminar_demandas()
        self.status_text.set(msg)
        self.dropdown_demandas["values"] = self.get_lista_demandas()
        self.var_demanda.set("")
        self.refresh_list_demandas()
        self.update_info_label()

    def on_crear_carpeta_demanda(self):
        nombre = simpledialog.askstring(
            "Nueva Carpeta", "Nombre para la carpeta:", parent=self.root
        )
        if not nombre:
            return
        msg = crear_carpeta_demanda(nombre)
        self.status_text.set(msg)
        self.refresh_list_demandas()
        messagebox.showinfo("Carpeta", msg)

    def on_agregar_demanda_pdf(self):
        archivos = filedialog.askopenfilenames(
            title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")]
        )
        if not archivos:
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msgs = []
        for a in archivos:
            carpeta = self.var_demanda_carpeta.get()
            msgs.append(agregar_demanda_pdf(a, subcarpeta=carpeta))
        self.status_text.set("\n".join(msgs))
        self.dropdown_demandas["values"] = self.get_lista_demandas()
        self.refresh_list_demandas()
        self.update_info_label()
        messagebox.showinfo("Carga completada", "\n".join(msgs))

    def on_eliminar_demanda_pdf(self):
        carpeta = self.var_demanda_carpeta.get()
        sel = self.list_demandas.curselection()
        if not sel:
            messagebox.showwarning("Advertencia", "Debes seleccionar un documento.")
            return
        doc = self.list_demandas.get(sel[0])
        nombre_rel = os.path.join(carpeta, doc) if carpeta else doc
        if messagebox.askyesno("Confirmación", f"¿Eliminar '{doc}'?"):
            msg = eliminar_demanda_pdf(nombre_rel)
            self.status_text.set(msg)
            self.dropdown_demandas["values"] = self.get_lista_demandas()
            if self.var_demanda.get() == nombre_rel:
                self.var_demanda.set("")
            self.refresh_list_demandas()
            self.update_info_label()

    def on_crear_area(self):
        nombre = self.entry_nombre_area.get().strip()
        if not nombre:
            messagebox.showwarning(
                "Advertencia", "Debes escribir un nombre para el área."
            )
            return
        msg = crear_area(nombre)
        self.status_text.set(msg)
        self.var_area.set(nombre)
        self.refresh_list_areas()
        self.entry_nombre_area.delete(0, tk.END)
        messagebox.showinfo("Área", msg)

    def on_eliminar_area(self):
        nombre = self.var_area.get()
        if not nombre:
            messagebox.showwarning("Advertencia", "Debes seleccionar un área.")
            return
        if messagebox.askyesno("Confirmación", f"¿Eliminar el área '{nombre}'?"):
            msg = eliminar_area(nombre)
            self.status_text.set(msg)
            self.var_area.set("")
            self.refresh_list_areas()

    def on_agregar_pdf_area(self):
        nombre = self.var_area.get()
        if not nombre:
            messagebox.showwarning("Advertencia", "Debes seleccionar un área.")
            return
        archivos = filedialog.askopenfilenames(
            title="Seleccionar PDF", filetypes=[("PDF", "*.pdf")]
        )
        if not archivos:
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        msgs = []
        for a in archivos:
            msgs.append(agregar_pdf_a_area(a, nombre))
        self.status_text.set("\n".join(msgs))
        self.refresh_list_areas()
        messagebox.showinfo("Carga completada", "\n".join(msgs))

    def on_eliminar_pdf_area(self):
        nombre = self.var_area.get()
        if not nombre:
            messagebox.showwarning("Advertencia", "Debes seleccionar un área.")
            return
        sel = self.list_area_pdfs.curselection()
        if sel:
            docs = [self.list_area_pdfs.get(i) for i in sel]
            if messagebox.askyesno(
                "Confirmación",
                f"¿Eliminar {', '.join(docs)} del área '{nombre}'?",
            ):
                msgs = []
                for doc in docs:
                    msgs.append(eliminar_pdf_de_area(doc, nombre))
                self.status_text.set("\n".join(msgs))
                self.refresh_list_areas()

    def on_area_selected(self, event=None):
        sel = self.list_areas.curselection()
        area = self.list_areas.get(sel[0]) if sel else ""
        self.var_area.set(area)
        self.refresh_list_areas()

    def on_dropdown_area_selected(self, event=None):
        nombre = self.dropdown_areas_demanda.get()
        if nombre:
            self.var_area.set(nombre)
        self.refresh_list_areas()
        if hasattr(self, "dropdown_demandas"):
            docs = self.get_lista_pdfs_area(nombre)
            self.dropdown_demandas["values"] = docs
            self.var_demanda.set("")

    def on_abrir_area_pdf(self, event=None):
        nombre = self.var_area.get()
        if not nombre:
            return
        sel = self.list_area_pdfs.curselection()
        if sel:
            item = self.list_area_pdfs.get(sel[0])
            path = os.path.join(AREAS_DIR_ROOT, nombre, item)
            self._abrir_archivo(path)

    def on_demanda_seleccionada(self, event=None):
        nombre = self.var_demanda.get()
        demandas.parsear_plantilla_desde_pdf(nombre)
        mensaje = "Plantilla cargada."

        if hasattr(self, "chat_demanda_area"):
            self.chat_demanda_area.delete("1.0", tk.END)
            self.chat_demanda_area.insert(tk.END, self._format_text(mensaje))
            self.chat_demanda_area.tag_config("highlight", background="yellow")

    def on_abrir_juris_pdf(self, event=None):
        sel = self.list_juris.curselection()
        if sel:
            item = self.list_juris.get(sel[0])
            path = os.path.join(JURIS_DIR, item)
            self._abrir_archivo(path)

    def on_abrir_demanda_pdf(self, event=None):
        sel = self.list_demandas.curselection()
        if sel:
            item = self.list_demandas.get(sel[0])
            carpeta = self.var_demanda_carpeta.get()
            path = os.path.join(DEMANDAS_DIR, carpeta, item)
            self._abrir_archivo(path)

    def on_abrir_caso_pdf(self, event=None):
        nombre = self.caso_seleccionado.get()
        if not nombre:
            return
        sel = self.list_pdfs_caso.curselection()
        if sel:
            item = self.list_pdfs_caso.get(sel[0])
            path = os.path.join(CASOS_DIR_ROOT, nombre, item)
            self._abrir_archivo(path)

    def on_select_pdf_caso_tab(self, event=None):
        nombre = self.var_caso_tab.get()
        sel = self.list_pdfs_caso_tab.curselection()
        if not nombre or not sel:
            return
        archivo = self.list_pdfs_caso_tab.get(sel[0])
        path = os.path.join(CASOS_DIR_ROOT, nombre, archivo)
        self.caso_pdf_trabajo.set(archivo)
        if hasattr(self, "lbl_pdf_trabajo"):
            self.lbl_pdf_trabajo.config(text=f"Trabajando en: {archivo}")
        self._show_caso_pdf_preview(path)

    def _show_caso_pdf_preview(self, path):
        try:
            pages = convert_from_path(path, first_page=1, last_page=1)
            img = pages[0]
            img.thumbnail((300, 400))
            self._case_pdf_photo = ImageTk.PhotoImage(img)
            if hasattr(self, "pdf_preview_label"):
                self.pdf_preview_label.config(image=self._case_pdf_photo)
        except Exception as exc:  # noqa: BLE001
            print(f"Error al generar vista previa de {path}: {exc}")

    def on_tab_case_selected(self, event=None):
        nombre = self.dropdown_casos_tab.get()
        if nombre:
            self.caso_seleccionado.set(nombre)
            self.refresh_list_pdfs_caso(nombre)
            if hasattr(self, "lbl_pdf_trabajo"):
                self.lbl_pdf_trabajo.config(text="Trabajando en: Ninguno")
            if hasattr(self, "pdf_preview_label"):
                self.pdf_preview_label.config(image="")
            self._case_pdf_photo = None
            demandas.analizar_caso(nombre)
            self._suggest_area_for_case(nombre)

    def on_tab_abrir_pdf(self):
        nombre = self.var_caso_tab.get()
        if not nombre:
            messagebox.showwarning("Advertencia", "Debes seleccionar un caso.")
            return
        sel = self.list_pdfs_caso_tab.curselection()
        if sel:
            item = self.list_pdfs_caso_tab.get(sel[0])
            path = os.path.join(CASOS_DIR_ROOT, nombre, item)
            self._abrir_archivo(path)

    def on_tab_resumen(self):
        nombre = self.var_caso_tab.get()
        if not nombre:
            messagebox.showwarning("Advertencia", "Debes seleccionar un caso.")
            return

        sel = self.list_pdfs_caso_tab.curselection()
        if not sel:
            messagebox.showwarning("Advertencia", "Debes seleccionar un archivo.")
            return
        archivo = self.list_pdfs_caso_tab.get(sel[0])
        self.status_text.set("\u23f3 Pensando...")
        self.text_resumen_caso.delete("1.0", tk.END)
        self.text_resumen_caso.insert(tk.END, "Pensando...")
        if hasattr(self, "btn_resumen"):
            self.btn_resumen.config(state="disabled")

        def _worker():
            resumen = demandas.resumir_archivo_caso(nombre, archivo)

            def _update_ui():
                self.text_resumen_caso.delete("1.0", tk.END)
                if resumen:
                    self.text_resumen_caso.insert(
                        tk.END, self._format_text(resumen)
                    )
                self.status_text.set("")
                if hasattr(self, "btn_resumen"):
                    self.btn_resumen.config(state="normal")

            self.root.after(0, _update_ui)

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------- Chat General -------------------------------
    def _render_jurisprudencia_checkbox(self):
        frame = tk.Frame(self.chat_pdf_preview_frame)
        chk = tk.Checkbutton(
            frame, text="Jurisprudencia", variable=self.var_jurisprudencia
        )
        chk.pack(side="left")
        frame.pack(anchor="w", pady=2)

    def on_upload_chat_pdfs(self):
        paths = filedialog.askopenfilenames(
            title="Seleccionar PDFs", filetypes=[("PDF", "*.pdf")]
        )
        if not paths:
            return

        for p in paths:
            if p not in self.chat_session_pdfs:
                self.chat_session_pdfs.append(p)

        for w in self.chat_pdf_preview_frame.winfo_children():
            w.destroy()
        self.chat_pdf_widgets.clear()

        self._render_jurisprudencia_checkbox()

        for p in self.chat_session_pdfs:
            frame = tk.Frame(self.chat_pdf_preview_frame)
            var = self.chat_pdf_vars.get(p)
            if var is None:
                var = tk.BooleanVar(value=True)
                self.chat_pdf_vars[p] = var
            chk = tk.Checkbutton(
                frame, variable=var, command=self._rebuild_chat_session_vs
            )
            chk.pack(side="left")
            lbl = tk.Label(frame, text=os.path.basename(p), cursor="hand2")
            lbl.bind("<Button-1>", lambda e, path=p: self._abrir_archivo(path))
            lbl.pack(side="left")
            btn = tk.Button(
                frame,
                text="Eliminar",
                command=lambda path=p: self.on_remove_chat_pdf(path),
            )
            btn.pack(side="left", padx=5)
            frame.pack(anchor="w", pady=2)
            self.chat_pdf_widgets[p] = frame

        self._rebuild_chat_session_vs()

    def on_remove_chat_pdf(self, path):
        if path in self.chat_session_pdfs:
            self.chat_session_pdfs.remove(path)
        frame = self.chat_pdf_widgets.pop(path, None)
        if frame is not None:
            frame.destroy()
        self.chat_pdf_vars.pop(path, None)
        self._rebuild_chat_session_vs()

    def _rebuild_chat_session_vs(self):
        docs = []
        for pdf_path in self.chat_session_pdfs:
            var = self.chat_pdf_vars.get(pdf_path)
            if var is None or not var.get():
                continue
            try:
                loader = PyPDFLoader(pdf_path, extract_images=False)
                docs.extend(loader.load())
            except Exception as exc:  # noqa: BLE001
                print(f"Error al cargar {pdf_path}: {exc}")
        if docs:
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self.chat_session_vs = FAISS.from_documents(docs, embeddings)
        else:
            self.chat_session_vs = None

    def on_send_chat_general(self):
        texto = self.entry_chat_general.get().strip()
        if not texto:
            return
        self._insertar_en_chat(self.chat_general_area, texto, "user")
        self.entry_chat_general.delete(0, tk.END)
        caso = self.caso_seleccionado.get()
        self.chat_status_text.set("\u23f3 Pensando...")
        self.root.update_idletasks()

        threading.Thread(
            target=self._run_chat_general, args=(texto, caso), daemon=True
        ).start()

    def _run_chat_general(self, texto, caso):
        try:
            extra = (
                self.chat_session_vs.as_retriever(search_kwargs={"k": 15})
                if self.chat_session_vs
                else None
            )
            respuesta = chat_fn(
                texto,
                caso,
                extra_retriever=extra,
                usar_jurisprudencia=self.var_jurisprudencia.get(),
            )
        except ValueError as exc:

            def handle_error():
                messagebox.showerror("Cr\u00e9dito agotado", str(exc))
                self.update_token_label()
                self.chat_status_text.set("")

            self.root.after(0, handle_error)
            return

        def handle_success():
            self.chat_status_text.set("")
            self._insertar_en_chat(self.chat_general_area, respuesta, "bot")

        self.root.after(0, handle_success)

    def on_clear_chat_general(self):
        # Enable the widget temporarily so deletion works even if it is
        # currently disabled after previous messages were inserted.
        self.chat_general_area.configure(state="normal")
        self.chat_general_area.delete("1.0", tk.END)
        self.chat_general_area.configure(state="disabled")

        for p in list(self.chat_session_pdfs):
            self.on_remove_chat_pdf(p)

        if hasattr(self, "frame_pdfs_right"):
            for w in self.frame_pdfs_right.winfo_children():
                w.destroy()
            self.chat_pdf_preview_frame = tk.Frame(self.frame_pdfs_right)
            self.chat_pdf_preview_frame.pack(fill="both", expand=True)
            self._render_jurisprudencia_checkbox()
        self.chat_session_pdfs = []
        self.chat_pdf_vars.clear()
        self.chat_session_vs = None

    def on_copy_chat_selected(self, event=None):
        try:
            selected = self.chat_general_area.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return "break"
        self.root.clipboard_clear()
        self.root.clipboard_append(selected)
        return "break"

    def on_close_app(self):
        self.on_clear_chat_general()
        self.root.destroy()

    def on_generar_desde_dropdown(self):
        ejemplo = self.var_demanda.get()
        caso = self.caso_seleccionado.get()
        if not ejemplo:
            messagebox.showwarning(
                "Advertencia", "Debes seleccionar un ejemplo de demanda."
            )
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        area = self.var_area.get()
        carpeta = os.path.join(AREAS_DIR_ROOT, area) if area else None
        try:
            generar_demanda_desde_pdf(ejemplo, caso or "", carpeta=carpeta)
        except ValueError as exc:
            messagebox.showerror("Crédito agotado", str(exc))
            self.update_token_label()
            self.status_text.set("")
            return
        self.status_text.set("")
        self.chat_demanda_area.delete("1.0", tk.END)
        self.chat_demanda_area.insert(
            tk.END,
            self._format_text(
                self._strip_markdown(str(default_context.partial_document))
            ),
        )
        self.chat_demanda_area.tag_config("highlight", background="yellow")

        default_context.last_generated_document = str(default_context.partial_document)
        if default_context.partial_document:
            self.btn_export_word.config(state="normal")
            self.btn_export_pdf.config(state="normal")

    def on_redactar_demanda(self):
        caso = self.caso_seleccionado.get()
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        if caso:
            try:
                generar_demanda_cogep_con_datos(caso)
            except ValueError as exc:
                messagebox.showerror("Crédito agotado", str(exc))
                self.update_token_label()
                self.status_text.set("")
                return
        else:
            try:
                generar_demanda_cogep()
            except ValueError as exc:
                messagebox.showerror("Crédito agotado", str(exc))
                self.update_token_label()
                self.status_text.set("")
                return
        self.status_text.set("")
        self.chat_demanda_area.delete("1.0", tk.END)
        self.chat_demanda_area.insert(
            tk.END,
            self._format_text(
                self._strip_markdown(str(default_context.partial_document))
            ),
        )
        self.chat_demanda_area.tag_config("highlight", background="yellow")
        self.btn_export_word.config(state="normal")
        self.btn_export_pdf.config(state="normal")
        if default_context.pending_placeholders:
            self._mostrar_formulario_entidades()

    def on_abrir_demanda_desde_dropdown(self):
        nombre = self.var_demanda.get()
        if not nombre:
            messagebox.showwarning(
                "Advertencia",
                "Debes seleccionar un documento.",
            )
            return
        area = self.var_area.get()
        carpeta = os.path.join(AREAS_DIR_ROOT, area) if area else AREAS_DIR_ROOT
        path = os.path.join(carpeta, nombre)
        self._abrir_archivo(path)

    def on_resumen_caso(self):
        caso = self.caso_seleccionado.get()
        if not caso:
            messagebox.showwarning("Advertencia", "Debes seleccionar un caso.")
            return
        self.status_text.set("Espere mientras se carga...")
        self.root.update_idletasks()
        try:
            resumen = demandas.generar_resumen_demanda(caso)
        except ValueError as exc:
            messagebox.showerror("Crédito agotado", str(exc))
            self.update_token_label()
            self.status_text.set("")
            return
        self.status_text.set("")
        if resumen:
            self.chat_demanda_area.delete("1.0", tk.END)
            self.chat_demanda_area.insert(tk.END, self._format_text(resumen))
            self.btn_export_word.config(state="normal")
            self.btn_export_pdf.config(state="normal")
            default_context.last_generated_document = resumen

    def on_ingresar_datos(self):
        messagebox.showinfo(
            "Ingresar Datos",
            "Función deshabilitada.",
        )

    def on_formulario_demanda(self):
        from ui.forms.schema_form import SchemaForm
        from src.schema_utils import (
            SCHEMAS_DIR,
            _slugify,
            generate_schema_from_pdf,
            hash_for_pdf,
            update_schema_index,
            cache_form_data,
            load_form_data,
            cache_placeholder_mapping,
            fill_placeholders,
        )

        ejemplo = self.var_demanda.get()
        if not ejemplo:
            messagebox.showwarning(
                "Advertencia", "Debes seleccionar un ejemplo de demanda."
            )
            return

        tipo = _slugify(Path(ejemplo).stem)
        if tipo.startswith("demanda_"):
            tipo = tipo[len("demanda_") :]

        # Generate or refresh schema based on placeholders in the selected PDF
        area = self.var_area.get()
        if area:
            pdf_path = Path(AREAS_DIR_ROOT) / area / ejemplo
        else:
            pdf_path = Path(DEMANDAS_DIR) / ejemplo
        pdf_hash = hash_for_pdf(str(pdf_path)) if pdf_path.exists() else None
        schema_path = SCHEMAS_DIR / f"demanda_{tipo}.json"
        schema, data = generate_schema_from_pdf(str(pdf_path))
        SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
        with open(schema_path, "w", encoding="utf8") as fh:
            json.dump(schema, fh, indent=2, ensure_ascii=False)
        if pdf_hash:
            update_schema_index(tipo, pdf_hash)
        cached_data = load_form_data(tipo)
        if cached_data:
            if messagebox.askyesno(
                "Confirmación",
                "¿Desea borrar los datos del formulario anterior?",
            ):
                cache_form_data(tipo, data)
                initial_data = data
            else:
                initial_data = {k: v for k, v in data.items() if k not in cached_data}
        else:
            cache_form_data(tipo, data)
            initial_data = data
        placeholder_map = {
            f["name"]: f"{{{{{f['name']}}}}}" for f in schema.get("fields", [])
        }
        cache_placeholder_mapping(tipo, placeholder_map)

        def ready(data, use_llm=False):
            # Retrieve the original template text for the selected demand
            area = self.var_area.get()
            if area:
                carpeta = Path(AREAS_DIR_ROOT) / area
            else:
                carpeta = Path(DEMANDAS_DIR)

            texto_original = default_context.demandas_textos.get(ejemplo, "")
            if not texto_original:
                texto_original, _ = demandas.parsear_plantilla_desde_pdf(
                    ejemplo, carpeta=str(carpeta)
                )

            if use_llm:
                texto = demandas.generar_redaccion_demanda_llm(data)
            elif texto_original:
                texto = fill_placeholders(texto_original, data)
            else:
                # Fallback to the programmatic generation if template text is missing
                texto = demandas.generar_redaccion_demanda(data)

            self.chat_demanda_area.delete("1.0", tk.END)
            self.chat_demanda_area.insert(tk.END, self._format_text(texto))
            self.btn_export_word.config(state="normal")
            self.btn_export_pdf.config(state="normal")
            default_context.last_generated_document = texto

        SchemaForm(
            self.root,
            on_ready=ready,
            tipo=tipo,
            schema=schema,
            initial_data=initial_data,
        )

    def _show_chat_demanda_menu(self, event):
        try:
            self.chat_demanda_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.chat_demanda_menu.grab_release()

    def on_mejorar_fragmento_demanda(self):
        try:
            start = self.chat_demanda_area.index(tk.SEL_FIRST)
            end = self.chat_demanda_area.index(tk.SEL_LAST)
        except tk.TclError:
            return
        texto = self.chat_demanda_area.get(start, end)
        if not texto.strip():
            return
        threading.Thread(
            target=self._run_mejorar_fragmento_demanda,
            args=(start, end, texto),
            daemon=True,
        ).start()

    def _run_mejorar_fragmento_demanda(self, start, end, texto):
        try:
            mejorado = demandas.mejorar_hechos_llm(texto)
        except Exception as exc:

            def handle_error():
                messagebox.showerror("Error", str(exc))

            self.root.after(0, handle_error)
            return

        def replace_text():
            self.chat_demanda_area.edit_separator()
            self.chat_demanda_area.delete(start, end)
            self.chat_demanda_area.insert(start, mejorado)
            self.chat_demanda_area.edit_separator()

        self.root.after(0, replace_text)

    def on_exportar_word_demanda(self):
        texto = self.chat_demanda_area.get("1.0", tk.END).strip()
        if texto:
            save_feedback(default_context.last_generated_document, texto)
            default_context.last_generated_document = texto
        exportar_a_word(texto)

    def on_exportar_pdf_demanda(self):
        texto = self.chat_demanda_area.get("1.0", tk.END).strip()
        if texto:
            save_feedback(default_context.last_generated_document, texto)
            default_context.last_generated_document = texto
        exportar_a_pdf(texto)

    def _mostrar_formulario_entidades(self):
        pass

    def show_generar_demanda_tab(self):
        """Switch to the 'Generar Demanda' tab if available."""
        try:
            self.notebook.select(self.tab_generar_demanda)
        except Exception:
            pass

    # ------------------------------- Palabras Clave -------------------------------
    def on_buscar_palabras_clave(self):
        texto = self.entry_palabras.get().strip()
        if not texto:
            return
        modo = self.palabras_mode.get()
        # Clear previous answer and show a thinking placeholder so users know
        # a new search is in progress. This also helps when switching between
        # search modes using the same query.
        self.txt_respuesta.configure(state="normal")
        self.txt_respuesta.delete("1.0", tk.END)
        self.txt_respuesta.insert(tk.END, "\u23f3 Pensando...\n")
        self.txt_respuesta.configure(state="normal")
        self.palabras_status_text.set("\u23f3 Pensando...")
        self.root.update_idletasks()
        threading.Thread(
            target=self._run_buscar_palabras, args=(texto, modo), daemon=True
        ).start()

    def _run_buscar_palabras(self, texto, modo):
        try:
            if modo == "exacta":
                respuesta = buscar_palabras_clave_exacta_fn(texto)
            else:
                respuesta = buscar_palabras_clave_fn(texto)
        except ValueError as exc:

            def handle_error():
                messagebox.showerror("Cr\u00e9dito agotado", str(exc))
                self.update_token_label()
                self.palabras_status_text.set("")

            self.root.after(0, handle_error)
            return

        doc_names = self._extract_document_names(respuesta)

        def handle_success():
            self.txt_respuesta.configure(state="normal")
            self.txt_respuesta.delete("1.0", tk.END)
            # Use the same formatting as chat responses for consistency
            self.txt_respuesta.insert(tk.END, self._strip_markdown(respuesta))
            self.txt_respuesta.configure(state="normal")
            self.palabras_status_text.set("")
            default_context.last_generated_document = respuesta
            self._update_pdf_links(doc_names)

        self.root.after(0, handle_success)

    def on_exportar_word_palabras(self):
        exportar_a_word(default_context.last_generated_document)

    def on_clear_palabras(self):
        self.txt_respuesta.delete("1.0", tk.END)
        self._update_pdf_links([])

    def on_copy_palabras_selected(self):
        try:
            selected = self.txt_respuesta.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(selected)

    def on_palabras_key(self, event):
        if (event.state & 0x4) and event.keysym.lower() == "c":
            return
        return "break"

    def _strip_markdown(self, text):
        text = re.sub(r"^\s*#+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[*-]\s+", "", text, flags=re.MULTILINE)
        return text.replace("**", "").replace("__", "")

    def _fix_word_breaks(self, text):
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
        return text

    def _format_text(self, text):
        """Prepara el texto para mostrarlo en la caja de demanda."""
        text = self._fix_word_breaks(text)
        return self._strip_markdown(text)

    def _resaltar_placeholder(self, placeholder):
        """Highlight placeholder location in the demanda text area."""
        self.chat_demanda_area.tag_remove("highlight", "1.0", tk.END)
        search = f"[{placeholder}]"
        idx = self.chat_demanda_area.search(search, "1.0", tk.END)
        if idx:
            end = f"{idx}+{len(search)}c"
            self.chat_demanda_area.tag_add("highlight", idx, end)
            self.chat_demanda_area.see(idx)

    def _insertar_en_chat(self, widget, texto, etiqueta):
        widget.configure(state="normal")

        widget.insert(tk.END, f"{self._strip_markdown(texto)}\n\n", etiqueta)
        widget.configure(state="disabled")

        widget.yview(tk.END)

    def _abrir_archivo(self, ruta):
        if not os.path.isfile(ruta):
            messagebox.showwarning("Advertencia", f"Archivo no encontrado:\n{ruta}")
            return
        try:
            if os.name == "nt":
                os.startfile(ruta)
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")

    def show_progress_dialog(self, title="Cargando"):
        """Display a modal dialog with a progress bar."""
        if self.progress_window is not None:
            return
        self.progress_var.set(0)
        if hasattr(self, "progress_percent_var"):
            self.progress_percent_var.set("0%")
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title(title)
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        tk.Label(self.progress_window, text="Por favor espere...").pack(
            padx=10, pady=10
        )
        self.progress = ttk.Progressbar(
            self.progress_window,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            length=300,
        )
        self.progress.pack(fill="x", padx=10, pady=(0, 5))
        tk.Label(
            self.progress_window, textvariable=self.progress_percent_var
        ).pack(pady=(0, 10))
        self.progress_window.update_idletasks()

    def close_progress_dialog(self):
        """Close the progress dialog if it is open."""
        if self.progress_window is not None:
            self.progress_window.destroy()
            self.progress_window = None
            self.progress = None
            if hasattr(self, "progress_var"):
                self.progress_var.set(0)
            if hasattr(self, "progress_percent_var"):
                self.progress_percent_var.set("0%")

    def _set_progress(self, value):
        if hasattr(self, "progress_var"):
            value = max(0, min(100, value))
            self.progress_var.set(value)
            if hasattr(self, "progress_percent_var"):
                self.progress_percent_var.set(f"{int(value)}%")
            if self.progress_window is not None:
                self.progress_window.update_idletasks()

    def _inc_progress(self, step):
        self._set_progress(self.progress_var.get() + step)

    def _set_status(self, text):
        self.status_text.set(text)

    def autocargar_si_existente(self):
        mensajes_acc = []
        self.root.after(0, lambda: self._set_progress(0))

        ruta_juris = _resolve_path(default_context.ruta_juris, demandas.JURIS_DIR)
        ruta_demandas = _resolve_path(
            default_context.ruta_demandas, demandas.DEMANDAS_DIR
        )

        case_dirs = (
            [
                d
                for d in glob.glob(os.path.join(CASOS_DIR_ROOT, "*"))
                if os.path.isdir(d)
            ]
            if os.path.isdir(CASOS_DIR_ROOT)
            else []
        )

        total_steps = 0
        juris_needed = False
        demandas_needed = False

        if (
            ruta_juris
            and os.path.isdir(ruta_juris)
            and not os.path.samefile(ruta_juris, JURIS_DIR)
        ) or glob.glob(os.path.join(JURIS_DIR, "**", "*.pdf"), recursive=True):
            juris_needed = True
            total_steps += 1

        if case_dirs:
            total_steps += len(case_dirs)

        if (
            ruta_demandas
            and os.path.isdir(ruta_demandas)
            and ruta_demandas != DEMANDAS_DIR
        ) or glob.glob(os.path.join(DEMANDAS_DIR, "**", "*.pdf"), recursive=True):
            demandas_needed = True
            total_steps += 1

        step = 100 / total_steps if total_steps else 0

        if (
            ruta_juris
            and os.path.isdir(ruta_juris)
            and not os.path.samefile(ruta_juris, JURIS_DIR)
        ):
            for root, _, files in os.walk(ruta_juris):
                rel = os.path.relpath(root, ruta_juris)
                dest_folder = os.path.join(JURIS_DIR, rel)
                os.makedirs(dest_folder, exist_ok=True)
                for fname in files:
                    if fname.lower().endswith(".pdf"):
                        src = os.path.join(root, fname)
                        dest = os.path.join(dest_folder, fname)
                        if os.path.abspath(src) != os.path.abspath(
                            dest
                        ) and not os.path.exists(dest):
                            shutil.copy(src, dest)
            try:
                default_context.juris_vectorstore = build_or_load_vectorstore(
                    JURIS_DIR, VECTOR_DB_JURIS
                )
                mensajes_acc.append("✅ Jurisprudencia autocargada.")
            except Exception:
                mensajes_acc.append("❌ Error al autocargar jurisprudencia.")
            self.root.after(0, self.refresh_list_juris)
        elif glob.glob(os.path.join(JURIS_DIR, "**", "*.pdf"), recursive=True):
            try:
                default_context.juris_vectorstore = build_or_load_vectorstore(
                    JURIS_DIR, VECTOR_DB_JURIS
                )
                mensajes_acc.append("✅ Jurisprudencia autocargada.")
            except Exception:
                mensajes_acc.append("❌ Error al autocargar jurisprudencia.")
            self.root.after(0, self.refresh_list_juris)
        if juris_needed:
            self.root.after(0, lambda s=step: self._inc_progress(s))

        if case_dirs:
            try:
                default_context.vectorstores_por_caso.clear()
                for carpeta in case_dirs:
                    if os.path.isdir(carpeta):
                        nombre = os.path.basename(carpeta.rstrip(os.sep))
                        carpeta_index = os.path.join(VECTOR_DB_CASOS, nombre)
                        vs = build_or_load_vectorstore(carpeta, carpeta_index)
                        default_context.vectorstores_por_caso[nombre] = vs
                        if nombre not in default_context.memories_por_caso:
                            default_context.memories_por_caso[nombre] = (
                                demandas.ChatMessageHistory()
                            )
                        self.root.after(0, lambda s=step: self._inc_progress(s))
                mensajes_acc.append("✅ Casos autocargados.")
            except Exception:
                mensajes_acc.append("❌ Error al autocargar casos.")
            self.root.after(0, self.refresh_list_casos)

        if (
            ruta_demandas
            and os.path.isdir(ruta_demandas)
            and ruta_demandas != DEMANDAS_DIR
        ):
            try:
                default_context.demandas_vectorstore = build_or_load_vectorstore(
                    ruta_demandas, VECTOR_DB_DEMANDAS
                )
                default_context.demandas_textos.clear()
                default_context.demandas_textos.update(
                    cargar_textos_demandas(ruta_demandas)
                )
                mensajes_acc.append("✅ Demandas de ejemplo autocargadas.")
            except Exception:
                mensajes_acc.append("❌ Error al autocargar demandas de ejemplo.")
            if hasattr(self, "dropdown_demandas"):
                self.root.after(
                    0,
                    lambda docs=self.get_lista_demandas(): self.dropdown_demandas.configure(
                        values=docs
                    ),
                )
            self.root.after(0, self.refresh_list_demandas)
            self.root.after(0, self.refresh_list_areas)
            if demandas_needed:
                self.root.after(0, lambda s=step: self._inc_progress(s))
        elif glob.glob(os.path.join(DEMANDAS_DIR, "**", "*.pdf"), recursive=True):
            try:
                default_context.demandas_vectorstore = build_or_load_vectorstore(
                    DEMANDAS_DIR, VECTOR_DB_DEMANDAS
                )
                default_context.demandas_textos.clear()
                default_context.demandas_textos.update(
                    cargar_textos_demandas(DEMANDAS_DIR)
                )
                mensajes_acc.append("✅ Demandas de ejemplo autocargadas.")
            except Exception:
                mensajes_acc.append("❌ Error al autocargar demandas de ejemplo.")
            if hasattr(self, "dropdown_demandas"):
                self.root.after(
                    0,
                    lambda docs=self.get_lista_demandas(): self.dropdown_demandas.configure(
                        values=docs
                    ),
                )
            self.root.after(0, self.refresh_list_demandas)
            self.root.after(0, self.refresh_list_areas)
            if demandas_needed:
                self.root.after(0, lambda s=step: self._inc_progress(s))

        if mensajes_acc:
            self.root.after(0, lambda: self._set_status("\n".join(mensajes_acc)))
        self.root.after(0, self.update_info_label)
        if total_steps == 0:
            self.root.after(0, lambda: self._set_progress(100))
        self.root.after(0, self.close_progress_dialog)
        self.root.after(0, self.update_token_label)
        self.root.after(0, lambda: self._set_status(""))

    # ------------------------------- Tokens ---------------------------------
    def update_token_label(self):
        if hasattr(self, "lbl_tokens"):
            self.lbl_tokens.config(text=f"Tokens usados: {self.tokens_usados}")
        saldo_decimal = Decimal(tokens.get_credit()).quantize(
            Decimal("0.0001"), ROUND_HALF_UP
        )
        saldo = float(saldo_decimal)
        mensaje = f"Crédito disponible: ${saldo_decimal}"
        color = TEXT_COLOR
        if saldo <= 0:
            mensaje += " - CRÉDITO AGOTADO"
            color = ERROR_COLOR
        elif saldo < 0.10:
            mensaje += " - SALDO A PUNTO DE AGOTARSE"
            color = ERROR_COLOR
        if hasattr(self, "lbl_credito"):
            self.lbl_credito.config(text=mensaje, fg=color)
        if hasattr(self, "lbl_credito_header"):
            header_msg = f"Saldo: ${saldo_decimal}"
            if saldo <= 0:
                header_msg += " - CRÉDITO AGOTADO"
            elif saldo < 0.10:
                header_msg += " - SALDO A PUNTO DE AGOTARSE"
            self.lbl_credito_header.config(text=header_msg, fg=color)
        self.apply_credit_restrictions(saldo)

    def apply_credit_restrictions(self, credit: float) -> None:
        """Enable or disable tabs based on available credit."""
        if not hasattr(self, "notebook"):
            return
        total = self.notebook.index("end")
        id_tab = getattr(self, "id_clave_tab_index", -1)
        tokens_tab = getattr(self, "tokens_tab_index", -1)
        for idx in range(total):
            if credit <= 0:
                if idx in (id_tab, tokens_tab):
                    self.notebook.tab(idx, state="normal")
                else:
                    self.notebook.tab(idx, state="disabled")
            else:
                self.notebook.tab(idx, state="normal")
        if credit <= 0:
            self.notebook.select(id_tab if id_tab >= 0 else 0)

    def update_token_log(self):
        if not hasattr(self, "tree_token_log"):
            return
        start = None
        end = None
        if hasattr(self, "entry_fecha_desde"):
            val = self.entry_fecha_desde.get().strip()
            if val:
                start = val
        if hasattr(self, "entry_fecha_hasta"):
            val = self.entry_fecha_hasta.get().strip()
            if val:
                end = val
        for item in self.tree_token_log.get_children():
            self.tree_token_log.delete(item)
        for (
            row_id,
            ts,
            count,
            tokens_in,
            tokens_out,
            actividad,
            costo_cliente,
            _costo_ds,
        ) in tokens.get_token_log_with_id(start_date=start, end_date=end, limit=20):
            self.tree_token_log.insert(
                "",
                "end",
                iid=row_id,
                values=(
                    ts,
                    actividad or "",
                    tokens_in if tokens_in is not None else "",
                    tokens_out if tokens_out is not None else "",
                    count,
                    f"{costo_cliente:.4f}",
                ),
            )

    def on_edit_token_activity(self, event=None):
        sel = self.tree_token_log.selection()
        if not sel:
            return
        iid = sel[0]
        current = self.tree_token_log.item(iid, "values")[1]
        new_val = simpledialog.askstring(
            "Actividad",
            "Editar actividad:",
            initialvalue=current,
            parent=self.root,
        )
        if new_val is None:
            return
        tokens.update_token_activity(int(iid), new_val)
        self.update_token_log()

    def on_reset_tokens(self):
        tokens.reset_tokens()
        self.tokens_usados = 0
        self.update_token_label()
        self.update_token_log()

    def on_add_credit(self):
        if not hasattr(self, "var_credito"):
            return
        try:
            amount = float(self.var_credito.get())
        except ValueError:
            messagebox.showerror("Error", "Cantidad inválida")
            return
        password = simpledialog.askstring(
            "Contraseña", "Ingrese la contraseña", show="*", parent=self.root
        )
        try:
            tokens.add_credit(amount, password=password)
        except ValueError:
            messagebox.showerror("Error", "Contraseña incorrecta")
            return
        self.var_credito.set("")
        self.saldo_actual = tokens.get_credit()
        self.update_token_label()

    def on_import_credit_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de crédito",
            filetypes=[("JSON", "*.json"), ("Todos", "*")],
        )
        if not path:
            return
        try:
            tokens.add_credit_from_file(path)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.saldo_actual = tokens.get_credit()
        self.update_token_label()
        messagebox.showinfo("Ok", "Crédito aplicado")

    def on_set_password(self):
        p1 = simpledialog.askstring(
            "Contraseña", "Nueva contraseña", show="*", parent=self.root
        )
        if not p1:
            return
        p2 = simpledialog.askstring(
            "Contraseña", "Confirme contraseña", show="*", parent=self.root
        )
        if p1 != p2:
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return
        tokens.set_password(p1)
        messagebox.showinfo("Ok", "Contraseña actualizada")

    def on_generate_user_id(self):
        email = default_context.config_global.get("license_email", "").strip()
        if not email:
            messagebox.showerror("Error", "Debe registrar su correo primero")
            return
        ts = datetime.utcnow().isoformat(timespec="seconds")
        self.var_id_output.set(tokens.create_user_id(email, ts))

    def on_copy_user_id(self):
        value = self.var_id_output.get()
        if value:
            self.root.clipboard_clear()
            self.root.clipboard_append(value)

    def on_generate_credit_file(self):
        try:
            amount = float(self.var_credito_gen.get())
        except ValueError:
            messagebox.showerror("Error", "Cantidad inválida")
            return
        user_id = self.var_credito_id.get().strip()
        if not user_id:
            messagebox.showerror("Error", "Debe ingresar el ID del usuario")
            return
        email = self.var_credito_email.get().strip()
        if not email:
            messagebox.showerror("Error", "Debe ingresar el correo del usuario")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{tokens.normalize_identifier(email)}_{ts}.json"
        path = filedialog.asksaveasfilename(
            title="Guardar archivo de crédito",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos", "*")],
            initialfile=default_name,
        )
        if not path:
            return
        try:
            tokens.generate_credit_file(amount, path, email=email, user_id=user_id)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.var_credito_gen.set("")
        self.var_credito_id.set("")
        self.var_credito_email.set("")
        self.lbl_credito_gen.config(
            text=f"Archivo generado en {os.path.basename(path)}"
        )
        messagebox.showinfo("Ok", f"Archivo generado en {path}")

    def on_reset_credit_balance(self):
        password = simpledialog.askstring(
            "Contraseña", "Ingrese la contraseña", show="*", parent=self.root
        )
        if password is None:
            return
        try:
            tokens.reset_credit(password=password)
        except ValueError:
            messagebox.showerror("Error", "Contraseña incorrecta")
            return
        self.saldo_actual = tokens.get_credit()
        self.update_token_label()
        messagebox.showinfo("Ok", "Saldo reiniciado")

    def on_encrypt_text(self):
        value = self.var_encrypt_input.get()
        if not value:
            return
        import hashlib

        result = hashlib.sha256(value.encode("utf-8")).hexdigest()
        self.var_encrypt_output.set(result)

    def on_copy_encrypted_text(self):
        value = self.var_encrypt_output.get()
        if value:
            self.root.clipboard_clear()
            self.root.clipboard_append(value)

    def toggle_admin_panel(self, event=None):
        if not hasattr(self, "frame_admin"):
            return
        if self.frame_admin.winfo_manager():
            self.frame_admin.pack_forget()
        else:
            self.frame_admin.pack(fill="x", padx=10, pady=5)

    def poll_tokens(self):
        current = tokens.get_tokens()
        credit = tokens.get_credit()
        if current != self.tokens_usados or credit != self.saldo_actual:
            prev_credit = self.saldo_actual
            self.tokens_usados = current
            self.saldo_actual = credit
            self.update_token_label()
            self.update_token_log()
            if credit <= 0 and prev_credit > 0:
                messagebox.showerror(
                    "Crédito agotado",
                    "El saldo se ha agotado. Contacte al proveedor para recargar.",
                )
        self.root.after(2000, self.poll_tokens)

    def on_import_activation_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de licencia",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        email = self.var_license_email.get().strip()
        if not email:
            messagebox.showerror("Error", "Debe ingresar su correo electrónico")
            return
        try:
            data = activation.activate_from_file(path, email)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        default_context.config_global["license_email"] = data["email"]
        default_context.config_global["license_id"] = data["id"]
        default_context.config_global["license_expires"] = data["expires_at"]
        demandas.guardar_config(default_context.config_global)
        self.update_license_status()
        if hasattr(self, "var_id_email"):
            self.var_id_email.set(data["email"])
        messagebox.showinfo("Ok", "Licencia activada")

    def on_save_license_email(self):
        email = self.var_license_email.get().strip()
        if not email:
            messagebox.showerror("Error", "Debe ingresar su correo electrónico")
            return
        default_context.config_global["license_email"] = email
        demandas.guardar_config(default_context.config_global)
        self.update_license_status()
        if hasattr(self, "var_id_email"):
            self.var_id_email.set(email)
        messagebox.showinfo("Ok", "Correo guardado")
        for idx in range(self.notebook.index("end")):
            self.notebook.tab(idx, state="normal")

    def update_license_status(self):
        if not hasattr(self, "lbl_license_status"):
            return
        email = default_context.config_global.get("license_email")
        if email:
            self.lbl_license_status.config(
                text=f"Correo registrado: {email}", fg=SUCCESS_COLOR
            )
        else:
            self.lbl_license_status.config(text="Correo no registrado", fg=ERROR_COLOR)

    def on_cambiar_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar logo",
            filetypes=[("Imagen", "*.png *.ico")],
        )
        if not path:
            return
        base_dir = os.path.dirname(os.path.dirname(__file__))
        ext = os.path.splitext(path)[1].lower()
        dest_path = os.path.join(base_dir, f"custom_logo{ext}")
        try:
            shutil.copy(path, dest_path)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo copiar el archivo: {exc}")
            return

        width = height = None
        try:
            with Image.open(dest_path) as img:
                width, height = img.size
                if width > 412 or height > 412:
                    img = img.resize((400, 400), Image.LANCZOS)
                    img.save(dest_path)
                    width, height = img.size
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo procesar el logo: {exc}")
            return

        default_context.config_global["logo_path"] = dest_path
        demandas.guardar_config(default_context.config_global)

        try:
            self.logo_img = tk.PhotoImage(file=dest_path)
            width, height = self.logo_img.width(), self.logo_img.height()
        except Exception:
            pass

        try:
            self.logo_img = tk.PhotoImage(file=dest_path)

            if hasattr(self, "lbl_logo"):
                self.lbl_logo.config(image=self.logo_img)
        except Exception:
            pass

        try:
            self.logo_credit_img = tk.PhotoImage(file=dest_path)
            if hasattr(self, "lbl_logo_credit"):
                self.lbl_logo_credit.config(image=self.logo_credit_img)
        except Exception:
            pass

        try:
            self._logo_icon = tk.PhotoImage(file=dest_path)
            self.root.iconphoto(True, self._logo_icon)
        except Exception:
            try:
                self.root.iconbitmap(dest_path)
            except Exception:
                pass


        try:
            ext_no_dot = ext.lstrip('.')
            if width and height:
                messagebox.showinfo(
                    "Logo actualizado",
                    f"Dimensiones: {width}x{height}px\nExtensión: {ext_no_dot}",
                )
            else:
                messagebox.showinfo(
                    "Logo actualizado",
                    f"Extensión: {ext_no_dot}",
                )
        except Exception:
            pass


    def on_save_llm_provider(self):
        provider = self.var_llm_provider.get()
        default_context.llm_provider = provider
        default_context.config_global["llm_provider"] = provider
        demandas._llm = None
        demandas.guardar_config(default_context.config_global)
        messagebox.showinfo("Ok", "Modelo de IA guardado")


    def on_cargar_costos(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de costos",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            casos = costos._cargar_json(path)
            resultados = costos.calcular_costos(casos)
            tabla = costos.formatear_tabla_costos(resultados)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.text_costos.configure(state="normal")
        self.text_costos.delete("1.0", tk.END)
        self.text_costos.insert(tk.END, tabla)
        self.text_costos.configure(state="disabled")

    # ----------------------------- Pestaña Base de Datos ----------------------
    def build_pestaña_database(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        frame_cli = ttk.Frame(nb)
        nb.add(frame_cli, text="Clientes")
        self._build_clientes(frame_cli)

        frame_casos = ttk.Frame(nb)
        nb.add(frame_casos, text="Casos")
        self._build_casos(frame_casos)

        frame_aud = ttk.Frame(nb)
        nb.add(frame_aud, text="Audiencias")
        self._build_audiencias(frame_aud)

    def _build_clientes(self, parent):
        self.tree_clientes = ttk.Treeview(
            parent, columns=("nombre", "cedula"), show="headings"
        )
        self.tree_clientes.heading("nombre", text="Nombre")
        self.tree_clientes.heading("cedula", text="Cédula")
        self.tree_clientes.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_clientes.bind("<<TreeviewSelect>>", self.on_cliente_selected)

        form = tk.Frame(parent)
        form.pack(fill="x", padx=5, pady=5)
        tk.Label(form, text="Nombre").grid(row=0, column=0)
        self.ent_cli_nombre = tk.Entry(form)
        self.ent_cli_nombre.grid(row=0, column=1, sticky="ew")
        tk.Label(form, text="Cédula").grid(row=1, column=0)
        self.ent_cli_cedula = tk.Entry(form)
        self.ent_cli_cedula.grid(row=1, column=1, sticky="ew")

        btn_add = tk.Button(form, text="Agregar", command=self.on_add_cliente)
        btn_add.grid(row=0, column=2, padx=5, pady=2)
        btn_upd = tk.Button(form, text="Actualizar", command=self.on_update_cliente)
        btn_upd.grid(row=1, column=2, padx=5, pady=2)
        form.columnconfigure(1, weight=1)

        self.selected_cliente_id = None
        self.refresh_clientes()

    def _build_casos(self, parent):
        self.tree_casos_db = ttk.Treeview(
            parent, columns=("cliente_id", "nombre", "descripcion"), show="headings"
        )
        for col in ("cliente_id", "nombre", "descripcion"):
            self.tree_casos_db.heading(col, text=col.capitalize())
        self.tree_casos_db.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_casos_db.bind("<<TreeviewSelect>>", self.on_caso_db_selected)

        form = tk.Frame(parent)
        form.pack(fill="x", padx=5, pady=5)
        tk.Label(form, text="Cliente ID").grid(row=0, column=0)
        self.ent_caso_cliente = tk.Entry(form)
        self.ent_caso_cliente.grid(row=0, column=1, sticky="ew")
        tk.Label(form, text="Nombre").grid(row=1, column=0)
        self.ent_caso_nombre = tk.Entry(form)
        self.ent_caso_nombre.grid(row=1, column=1, sticky="ew")
        tk.Label(form, text="Descripción").grid(row=2, column=0)
        self.ent_caso_desc = tk.Entry(form)
        self.ent_caso_desc.grid(row=2, column=1, sticky="ew")

        btn_add = tk.Button(form, text="Agregar", command=self.on_add_caso)
        btn_add.grid(row=0, column=2, rowspan=2, padx=5)
        btn_upd = tk.Button(form, text="Actualizar", command=self.on_update_caso)
        btn_upd.grid(row=2, column=2, padx=5)
        form.columnconfigure(1, weight=1)

        self.selected_caso_id = None
        self.refresh_casos_db()

    def _build_audiencias(self, parent):
        self.tree_aud = ttk.Treeview(
            parent, columns=("caso_id", "fecha", "descripcion"), show="headings"
        )
        for col in ("caso_id", "fecha", "descripcion"):
            self.tree_aud.heading(col, text=col.capitalize())
        self.tree_aud.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_aud.bind("<<TreeviewSelect>>", self.on_aud_selected)

        form = tk.Frame(parent)
        form.pack(fill="x", padx=5, pady=5)
        tk.Label(form, text="Caso ID").grid(row=0, column=0)
        self.ent_aud_caso = tk.Entry(form)
        self.ent_aud_caso.grid(row=0, column=1, sticky="ew")
        tk.Label(form, text="Fecha").grid(row=1, column=0)
        self.ent_aud_fecha = tk.Entry(form)
        self.ent_aud_fecha.grid(row=1, column=1, sticky="ew")
        tk.Label(form, text="Descripción").grid(row=2, column=0)
        self.ent_aud_desc = tk.Entry(form)
        self.ent_aud_desc.grid(row=2, column=1, sticky="ew")

        btn_add = tk.Button(form, text="Agregar", command=self.on_add_audiencia)
        btn_add.grid(row=0, column=2, rowspan=2, padx=5)
        btn_upd = tk.Button(form, text="Actualizar", command=self.on_update_audiencia)
        btn_upd.grid(row=2, column=2, padx=5)
        form.columnconfigure(1, weight=1)

        self.selected_aud_id = None
        self.refresh_audiencias()

    def refresh_clientes(self):
        for i in getattr(self, "tree_clientes").get_children():
            self.tree_clientes.delete(i)
        for row in db.get_clientes():
            self.tree_clientes.insert("", "end", iid=row[0], values=row[1:])

    def refresh_casos_db(self):
        db.sync_casos_from_fs()
        for i in getattr(self, "tree_casos_db").get_children():
            self.tree_casos_db.delete(i)
        for row in db.get_casos():
            self.tree_casos_db.insert("", "end", iid=row[0], values=row[1:])

    def refresh_audiencias(self):
        for i in getattr(self, "tree_aud").get_children():
            self.tree_aud.delete(i)
        for row in db.get_audiencias():
            self.tree_aud.insert("", "end", iid=row[0], values=row[1:])

    def on_cliente_selected(self, event=None):
        sel = self.tree_clientes.selection()
        if sel:
            iid = sel[0]
            vals = self.tree_clientes.item(iid, "values")
            self.ent_cli_nombre.delete(0, tk.END)
            self.ent_cli_nombre.insert(0, vals[0])
            self.ent_cli_cedula.delete(0, tk.END)
            self.ent_cli_cedula.insert(0, vals[1])
            self.selected_cliente_id = int(iid)

    def on_add_cliente(self):
        nombre = self.ent_cli_nombre.get().strip()
        cedula = self.ent_cli_cedula.get().strip()
        if not nombre:
            return
        db.add_cliente(nombre, cedula)
        self.refresh_clientes()

    def on_update_cliente(self):
        if self.selected_cliente_id is None:
            return
        nombre = self.ent_cli_nombre.get().strip()
        cedula = self.ent_cli_cedula.get().strip()
        db.update_cliente(self.selected_cliente_id, nombre, cedula)
        self.refresh_clientes()

    def on_caso_db_selected(self, event=None):
        sel = self.tree_casos_db.selection()
        if sel:
            iid = sel[0]
            vals = self.tree_casos_db.item(iid, "values")
            self.ent_caso_cliente.delete(0, tk.END)
            self.ent_caso_cliente.insert(0, vals[0])
            self.ent_caso_nombre.delete(0, tk.END)
            self.ent_caso_nombre.insert(0, vals[1])
            self.ent_caso_desc.delete(0, tk.END)
            self.ent_caso_desc.insert(0, vals[2])
            self.selected_caso_id = int(iid)

    def on_add_caso(self):
        cliente_id = self.ent_caso_cliente.get().strip()
        nombre = self.ent_caso_nombre.get().strip()
        descripcion = self.ent_caso_desc.get().strip()
        if not nombre:
            return
        db.add_caso(cliente_id or None, nombre, descripcion)
        self.refresh_casos_db()

    def on_update_caso(self):
        if self.selected_caso_id is None:
            return
        cliente_id = self.ent_caso_cliente.get().strip()
        nombre = self.ent_caso_nombre.get().strip()
        descripcion = self.ent_caso_desc.get().strip()
        db.update_caso(self.selected_caso_id, cliente_id or None, nombre, descripcion)
        self.refresh_casos_db()

    def on_aud_selected(self, event=None):
        sel = self.tree_aud.selection()
        if sel:
            iid = sel[0]
            vals = self.tree_aud.item(iid, "values")
            self.ent_aud_caso.delete(0, tk.END)
            self.ent_aud_caso.insert(0, vals[0])
            self.ent_aud_fecha.delete(0, tk.END)
            self.ent_aud_fecha.insert(0, vals[1])
            self.ent_aud_desc.delete(0, tk.END)
            self.ent_aud_desc.insert(0, vals[2])
            self.selected_aud_id = int(iid)

    def on_add_audiencia(self):
        caso_id = self.ent_aud_caso.get().strip()
        fecha = self.ent_aud_fecha.get().strip()
        descripcion = self.ent_aud_desc.get().strip()
        db.add_audiencia(caso_id or None, fecha, descripcion)
        self.refresh_audiencias()

    def on_update_audiencia(self):
        if self.selected_aud_id is None:
            return
        caso_id = self.ent_aud_caso.get().strip()
        fecha = self.ent_aud_fecha.get().strip()
        descripcion = self.ent_aud_desc.get().strip()
        db.update_audiencia(self.selected_aud_id, caso_id or None, fecha, descripcion)
        self.refresh_audiencias()

