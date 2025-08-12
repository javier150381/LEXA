"""Ejemplo de vocabulario nivel MCER B1."""

import gradio as gr


def render() -> None:
    """Renderiza el contenido de la pestaña de Vocabulary."""
    gr.Markdown("### Vocabulary - Nivel B1")
    gr.Markdown("Escribe un sinónimo de 'journey'.")
    gr.Textbox(label="Respuesta")
