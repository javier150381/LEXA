"""Ejemplo de gramática nivel MCER B1."""

import gradio as gr


def render() -> None:
    """Renderiza el contenido de la pestaña de Grammar."""
    gr.Markdown("### Grammar - Nivel B1")
    gr.Markdown(
        "Completa la frase con la forma correcta: 'I ___ (visit) London twice.'"
    )
    gr.Textbox(label="Respuesta")
