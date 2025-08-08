import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import re
from src.validators.requirements import validate_requirements

from lib.demandas import (
    determinar_procedimiento as _determinar_proc,
    generar_formula_pretension,
    sugerir_datos_para_formulario,
    obtener_dato_de_caso,
    buscar_palabras_clave_fn,
    generar_redaccion_demanda,
    generar_redaccion_demanda_llm,
    extraer_json_demanda,
    )


BASE_LEGAL = {
    "DESIGNACION_JUZGADOR": "Art. 142 COGEP",
    "DATOS_ACTOR": "Art. 142 COGEP",
    "DATOS_DEFENSOR": "Art. 142 COGEP",
    "RUC": "Art. 142 COGEP",
    "DATOS_DEMANDADO": "Art. 142 COGEP",
    "HECHOS": "Art. 142 COGEP",
    "FUNDAMENTOS_DERECHO": "Art. 142 COGEP",
    "ACCESO_PRUEBAS": "Art. 142 COGEP",
    "PRETENSION": "Art. 142 COGEP",
    "CUANTIA": "Art. 142 COGEP",
    "PROCEDIMIENTO": "Art. 142 COGEP",
    "FIRMAS": "Art. 142 COGEP",
    "OTROS": "Art. 142 COGEP",
}

# Remove fields that are no longer part of the form
_EXCLUIR_SECCIONES = {
    "FUNDAMENTOS_DERECHO",
    "ACCESO_PRUEBAS",
    "PRETENSION",
    "PROCEDIMIENTO",
    "OTROS",
}


from ui.constants import (
    WINDOW_BG,
    FRAME_BG,
    CONFIG_BTN_BG,
    BUTTON_TEXT_COLOR,
    TEXT_COLOR,
    ENTRY_BG,
    ENTRY_FONT,
)


class DemandaForm(tk.Toplevel):
    def __init__(self, master, on_ready, caso=None, ejemplo=None, plantilla_widget=None, demanda_path=None, **kw):
        super().__init__(master, **kw)
        self.title("Formulario de Demanda")
        # Configure a consistent color scheme for the data form
        bg_color = WINDOW_BG
        self.configure(bg=bg_color)
        self.option_add("*Frame.Background", FRAME_BG)
        self.option_add("*Label.Background", FRAME_BG)
        self.option_add("*Label.Foreground", TEXT_COLOR)
        self.option_add("*Entry.Background", ENTRY_BG)
        self.option_add("*Entry.Foreground", TEXT_COLOR)
        self.option_add("*Entry.Font", ENTRY_FONT)
        self.option_add("*ScrolledText.Background", ENTRY_BG)
        self.option_add("*ScrolledText.Foreground", TEXT_COLOR)
        self.option_add("*ScrolledText.Font", ENTRY_FONT)
        self.option_add("*Checkbutton.Background", FRAME_BG)
        self.option_add("*Checkbutton.Foreground", TEXT_COLOR)
        self.option_add("*Button.Background", CONFIG_BTN_BG)
        self.option_add("*Button.Foreground", BUTTON_TEXT_COLOR)
        self.option_add("*Button.ActiveBackground", CONFIG_BTN_BG)
        self.option_add("*Button.ActiveForeground", BUTTON_TEXT_COLOR)

        style = ttk.Style(self)
        style.configure("Custom.TLabelframe", background=FRAME_BG)
        style.configure(
            "Custom.TLabelframe.Label",
            background=FRAME_BG,
            foreground=TEXT_COLOR,
        )
        self.on_ready = on_ready
        self.caso = caso
        self.ejemplo = ejemplo
        self.plantilla_widget = plantilla_widget
        self.entries = {}
        self.fields_config = {}
        self.hechos_counter = 0
        self.sugerencias = {}
        self.demanda_path = demanda_path

        # Maximizar la ventana al abrir el formulario
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)

        canvas = tk.Canvas(self)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        frame = tk.Frame(canvas)
        frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        # Ajustar el ancho del frame interno al ancho disponible en el canvas
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(frame_id, width=e.width),
        )

        self.seccion_datos = {}
        if self.demanda_path:
            try:
                data_json = extraer_json_demanda(self.demanda_path)
                self.seccion_datos = {
                    k: v for k, v in data_json.items() if k not in _EXCLUIR_SECCIONES
                }
            except Exception:
                self.seccion_datos = {}
        self.secciones = list(self.seccion_datos.keys())

        for i, sec in enumerate(self.secciones, 1):
            lf = ttk.LabelFrame(frame, text=f"{i}. {sec}", style="Custom.TLabelframe")
            lf.pack(fill="x", pady=2, padx=5)
            row = tk.Frame(lf)
            row.pack(fill="x")
            # Permitir dos columnas para aprovechar mejor el ancho
            for col in range(2):
                row.columnconfigure(col, weight=1)

            campos = self.seccion_datos.get(sec)
            if isinstance(campos, dict):
                for idx, (campo, valor) in enumerate(campos.items()):
                    sub = tk.Frame(row)
                    lbl = tk.Label(sub, text=self._format_label(campo))
                    lbl.pack(anchor="w")
                    key = f"{sec}.{campo}"
                    if (
                        isinstance(valor, str)
                        and re.match(r".+\.{3,}$", valor.strip())
                    ):

                        widget = scrolledtext.ScrolledText(sub, height=4, wrap="word")
                        widget.pack(fill="both", expand=True)
                        widget.insert("1.0", valor)


                        self.fields_config[key] = {"widget": "textarea", "max_words": 300}
                    else:
                        widget = tk.Entry(sub)
                        widget.pack(fill="x", expand=True)
                        if valor:
                            widget.insert(0, valor)

                        self.fields_config[key] = {"widget": "entry"}

                   
                    sub.grid(row=idx // 2, column=idx % 2, sticky="ew", padx=2, pady=1)
                continue

            if sec == "HECHOS":
                txt = scrolledtext.ScrolledText(row, height=4, wrap="word")
                txt.grid(row=0, column=0, sticky="nsew")
                btn_hecho = tk.Button(
                    lf, text="Agregar Hecho", command=lambda t=txt: self.add_hecho(t)
                )
                btn_hecho.pack(anchor="e", pady=2)
                if isinstance(campos, str):
                    txt.insert("1.0", campos)
                self.entries[sec] = txt
                self.fields_config[sec] = {"widget": "textarea"}
            elif sec == "DESIGNACION_JUZGADOR":
                ent = tk.Entry(row)
                ent.grid(row=0, column=0, sticky="nsew")
                if isinstance(campos, str):
                    ent.insert(0, campos)
                self.entries[sec] = ent
                self.fields_config[sec] = {"widget": "entry"}

                sub_pais = tk.Frame(lf)
                sub_pais.pack(fill="x", pady=1)
                lbl_pais = tk.Label(sub_pais, text="País")
                lbl_pais.pack(anchor="w")
                ent_pais = tk.Entry(sub_pais)
                ent_pais.pack(fill="x", expand=True)
                self.entries[f"{sec}.PAIS"] = ent_pais
                self.fields_config[f"{sec}.PAIS"] = {"widget": "entry"}

                sub_zona = tk.Frame(lf)
                sub_zona.pack(fill="x", pady=1)
                lbl_zona = tk.Label(sub_zona, text="Zona")
                lbl_zona.pack(anchor="w")
                ent_zona = tk.Entry(sub_zona)
                ent_zona.pack(fill="x", expand=True)
                self.entries[f"{sec}.ZONA"] = ent_zona
                self.fields_config[f"{sec}.ZONA"] = {"widget": "entry"}
            else:
                widget = scrolledtext.ScrolledText(row, height=4, wrap="word")
                widget.grid(row=0, column=0, sticky="nsew")
                if isinstance(campos, str):
                    widget.insert("1.0", campos)
                self.entries[sec] = widget
                self.fields_config[sec] = {"widget": "textarea"}

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Aceptar", command=self.finish).pack(side="left", padx=5)

        # Label de estado para mostrar mensajes como "Cargando..."
        self.lbl_status = tk.Label(btn_frame, text="")
        self.lbl_status.pack(side="left")

        if self.caso:
            # Si existe un caso proporcionado, autocompletar de forma automática
            # al iniciar el formulario
            self.after(100, self.prefill_async)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _format_label(self, campo):
        if campo.startswith("ACTOR_"):
            campo = campo.replace("ACTOR_", "")
        elif campo.startswith("DEMANDADO_"):
            campo = campo.replace("DEMANDADO_", "")
        return campo.replace("_", " ").title()

    def add_hecho(self, txt_widget):
        self.hechos_counter += 1
        txt_widget.insert(tk.END, f"{self.hechos_counter}. \n")

    def prefill_from_case(self, caso):
        datos = sugerir_datos_para_formulario(caso)
        self._apply_prefill(datos)

    def _set_value(self, sec, val):
        widget = self.entries.get(sec)
        if not widget:
            return
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", val)
        elif isinstance(widget, ttk.Combobox):
            widget.set(val)
        else:
            widget.delete(0, tk.END)
            widget.insert(0, val)

    def _sugerir_para(self, sec):
        if not self.caso:
            return ""
        val = obtener_dato_de_caso(sec, self.caso)
        if not val and sec in ("FUNDAMENTOS_DERECHO", "PRETENSION"):
            try:
                pregunta = f"¿Cuáles son los {sec.replace('_', ' ').lower()} para el caso {self.caso}?"
                val = buscar_palabras_clave_fn(pregunta)
            except Exception:
                val = ""
        return val


    def prefill_async(self):
        if not self.caso:
            return
        self.lbl_status.config(text="Cargando...")
        threading.Thread(target=self._prefill_worker, daemon=True).start()

    def _prefill_worker(self):
        datos = sugerir_datos_para_formulario(self.caso)
        self.after(0, lambda: self._apply_prefill(datos))

    def _apply_prefill(self, datos):
        for sec, val in datos.items():
            widget = self.entries.get(sec)
            if not widget:
                continue
            if isinstance(widget, tk.Text):
                if sec == "HECHOS":
                    self._seleccionar_hechos(val)
                else:
                    widget.insert("1.0", val)
            elif isinstance(widget, ttk.Combobox):
                widget.set(val)
            else:
                widget.insert(0, val)
        self.lbl_status.config(text="")

    def _seleccionar_hechos(self, texto):
        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
        if not lineas:
            widget = self.entries.get("HECHOS")
            if widget:
                widget.insert("1.0", texto)
            return

        top = tk.Toplevel(self)
        top.title("Seleccionar Hechos")
        top.configure(bg=WINDOW_BG)

        canvas = tk.Canvas(top)
        scrollbar = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        frame = tk.Frame(canvas)
        frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=frame, anchor="nw")

        vars_lines = []
        for ln in lineas:
            var = tk.BooleanVar(value=True)
            chk = tk.Checkbutton(frame, text=ln, variable=var, anchor="w", justify="left", wraplength=500)
            chk.pack(fill="x", anchor="w")
            vars_lines.append((var, ln))

        def aceptar():
            seleccionados = [ln for v, ln in vars_lines if v.get()]
            widget = self.entries.get("HECHOS")
            if widget:
                widget.delete("1.0", tk.END)
                widget.insert("1.0", "\n".join(seleccionados))
            top.destroy()

        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Aceptar", command=aceptar).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=top.destroy).pack(side="left")

    def _generar_para_campo(self, key, campo):
        widget = self.entries.get(key)
        if not isinstance(widget, tk.Text):
            return
        texto_base = widget.get("1.0", "end-1c").strip()
        from lib.demandas import get_llm

        prompt = (
            f"Corrige el texto de la sección '{self._format_label(campo)}' sin cambiar nombres ni datos. "
            "Para cada párrafo aplica las siguientes reglas:\n"
            "- Si el párrafo tiene más de tres líneas, reescríbelo por completo en castellano formal.\n"
            "- Si el párrafo tiene una sola línea, corrige únicamente faltas de ortografía o de sintaxis.\n"
            "Devuelve el texto manteniendo la estructura original."
        )
        if texto_base:
            prompt += f"\n\nTexto base:\n{texto_base}\n"

        self.lbl_status.config(text="Espere mientras se genera...")
        self.update_idletasks()
        try:
            respuesta = get_llm().invoke(prompt)
            if isinstance(respuesta, dict):
                nuevo = respuesta.get("answer", "")
            else:
                nuevo = getattr(respuesta, "content", str(respuesta))
            widget.delete("1.0", tk.END)
            widget.insert("1.0", nuevo.strip())
        except ValueError as e:
            messagebox.showerror("Crédito agotado", str(e))
        except Exception as e:
            messagebox.showerror("Error generando texto", str(e))
        finally:
            self.master.app.update_token_label() if hasattr(self.master, "app") else None
            self.lbl_status.config(text="")

    def update_procedimiento(self, _event=None):
        cuantia_entry = self.entries.get("CUANTIA")
        proc_entry = self.entries.get("PROCEDIMIENTO")
        if not cuantia_entry or not proc_entry:
            return
        cuantia = cuantia_entry.get().strip()
        if cuantia.isdigit():
            proc = _determinar_proc(int(cuantia), "")
            proc_entry.delete(0, tk.END)
            proc_entry.insert(0, proc)
        else:
            # Ensure the field is cleared if cuantia isn't numeric
            proc_entry.delete(0, tk.END)

    def _collect_data(self):
        data = {}
        for sec, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                val = widget.get("1.0", tk.END).strip()
            else:
                val = widget.get().strip()
            data[sec] = val
        return {"fields": data, "config": self.fields_config}

    def finish(self):
        collected = self._collect_data()
        data = collected["fields"]

        cuantia = data.get("CUANTIA")
        if cuantia.isdigit():
            proc = _determinar_proc(int(cuantia), "")
            proc_entry = self.entries.get("PROCEDIMIENTO")
            if proc_entry:
                proc_entry.delete(0, tk.END)
                proc_entry.insert(0, proc)
            data["PROCEDIMIENTO"] = proc

        faltantes = validate_requirements(data.get("TIPO_DEMANDA", "default"), data)
        if faltantes:
            messagebox.showwarning(
                "Información incompleta",
                "Faltan datos obligatorios: " + ", ".join(faltantes),
            )
            return

        if self.ejemplo:
            from lib.demandas import generar_demanda_desde_pdf

            texto = generar_demanda_desde_pdf(
                self.ejemplo,
                self.caso or "",
                datos=data,
            )
        else:
            texto = generar_redaccion_demanda(data)
        self.on_ready(texto)
        self.destroy()

