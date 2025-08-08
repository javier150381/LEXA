from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any, List

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from src.schema_utils import (
    load_or_generate_schema,
    available_schema_types,
    load_schema as _load_schema,
    load_form_data,
    cache_form_data,
)


def load_schema(name: str) -> Dict[str, Any]:
    """Load a schema by name from ``forms/schemas``.

    ``name`` can include the ``demanda_`` prefix and an optional extension.
    """
    base = Path(name).stem
    if base.startswith("demanda_"):
        base = base[len("demanda_"):]
    return _load_schema(base)


def validate_data(schema: Dict[str, Any], data: Dict[str, str]) -> List[str]:
    """Validate *data* against *schema*.

    Only pattern validations are enforced; the ``required`` attribute is
    ignored so that forms may be submitted even when fields are empty.
    """

    errors: List[str] = []
    for field in schema.get("fields", []):
        name = field.get("name")
        value = (data.get(name, "") or "").strip()
        pattern = field.get("validations", {}).get("pattern")
        if pattern and value and not re.fullmatch(pattern, value):
            errors.append(name)
    return errors


def _infer_lines(label: str) -> int:
    """Infer the number of lines for a field based on trailing dots."""
    match = re.search(r"[.\u2026]+$", label)
    if not match:
        return 1
    dots = match.group(0)
    # treat each Unicode ellipsis as three dots so forms that
    # use "…" can still expand to multiple lines
    count = dots.count(".") + 3 * dots.count("\u2026")
    return max(1, count // 2)


class SchemaForm(tk.Toplevel):
    """Tk form generated from a schema and demand type selector."""

    def __init__(
        self,
        master: tk.Misc | None,
        on_ready=None,
        tipo: str | None = None,
        schema: Dict[str, Any] | None = None,
        initial_data: Dict[str, str] | None = None,
        **kw: Any,
    ) -> None:
        super().__init__(master, **kw)
        self.on_ready = on_ready
        self.fields: Dict[str, tk.Widget] = {}
        self.tipo_var = tk.StringVar()
        self._schema_override = schema
        self._initial_data = initial_data or {}
        # Remember which "tipo" corresponds to the provided schema/data
        self._override_tipo = tipo if schema is not None else None

        tipos = available_schema_types()
        if tipo:
            self.tipo_var.set(tipo)
        elif tipos:
            self.tipo_var.set(tipos[0])
        selector = ttk.Combobox(
            self, textvariable=self.tipo_var, values=tipos, state="readonly"
        )
        selector.pack(fill="x", padx=10, pady=5)
        selector.bind("<<ComboboxSelected>>", self._on_tipo_change)

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.form_frame = ttk.Frame(canvas)
        self.form_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        frame_id = canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        canvas.bind(
            "<Configure>", lambda e: canvas.itemconfigure(frame_id, width=e.width)
        )

        self._build_form()

    def _on_tipo_change(self, event=None) -> None:
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.fields.clear()
        self._build_form()

    def _build_form(self) -> None:
        tipo = self.tipo_var.get()
        if self._schema_override is not None and tipo == self._override_tipo:
            self.schema = self._schema_override
        else:
            self.schema = load_or_generate_schema(tipo)
        title = self.schema.get("title", "Formulario")
        self.title(title)
        single_line_fields: list[str] = []
        multi_line_fields: list[str] = []
        for field in self.schema.get("fields", []):
            name = field.get("name", "")
            row = ttk.Frame(self.form_frame)
            row.pack(fill="x", pady=2, padx=10)
            label_text = field.get("label", name)
            lines = field.get("lines") or _infer_lines(label_text)
            field["lines"] = lines
            ttk.Label(row, text=label_text, anchor="w").pack(fill="x")
            if field.get("type") == "text" or lines > 1:
                widget: tk.Widget = scrolledtext.ScrolledText(row, height=4, width=40)
                multi_line_fields.append(name)
                print(f"Campo de varias lineas: {name} - metadata: {field}")
            else:
                widget = ttk.Entry(row)
                single_line_fields.append(name)
                print(f"Campo de una linea: {name} - metadata: {field}")
            widget.pack(fill="x", expand=True)
            self.fields[name] = widget
        print(f"Campos una linea: {single_line_fields}")
        print(f"Campos varias lineas: {multi_line_fields}")
        cached = load_form_data(tipo)
        if self._override_tipo == tipo and self._initial_data:
            cached.update(self._initial_data)
        for name, widget in self.fields.items():
            value = cached.get(name)
            if not value:
                continue
            if isinstance(widget, tk.Text):
                widget.insert("1.0", value)
            else:
                widget.insert(0, value)
        btn_frame = ttk.Frame(self.form_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Aceptar", command=self._on_accept).pack(side="left")

    def _collect_data(self) -> Dict[str, str]:
        data: Dict[str, str] = {}
        for name, widget in self.fields.items():
            if isinstance(widget, tk.Text):
                value = widget.get("1.0", "end-1c")
            else:
                value = widget.get()
            data[name] = value
        data["TIPO_DEMANDA"] = self.tipo_var.get()
        return data

    def _validate(self, data: Dict[str, str]) -> bool:
        errors = validate_data(self.schema, data)
        if errors:
            labels = {
                f["name"]: f.get("label", f["name"])
                for f in self.schema.get("fields", [])
            }
            msg = "\n".join(labels[e] for e in errors)
            messagebox.showerror("Errores de validación", msg)
            return False
        missing = [
            f.get("label", f["name"])
            for f in self.schema.get("fields", [])
            if not (data.get(f["name"], "") or "").strip()
        ]
        if missing:
            messagebox.showwarning(
                "Información incompleta", "Faltan datos: " + ", ".join(missing)
            )
        cache_form_data(self.tipo_var.get(), data)
        return True

    def _on_accept(self) -> None:
        data = self._collect_data()
        if not self._validate(data):
            return
        if self.on_ready:
            try:
                self.on_ready(data, False)
            except TypeError:
                self.on_ready(data)
        self.destroy()


