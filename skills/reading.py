"""Ejemplo de comprensión lectora nivel MCER B1."""

import gradio as gr

TEXT = (
    "Last year I went to the mountains with my friends. We stayed in a small cabin "
    "and went hiking every day. On the last night, we had a big dinner in a local "
    "restaurant."
)
QUESTION = "Where did they have dinner on the last night?"


def render() -> None:
    """Renderiza el contenido de la pestaña de Reading."""
    gr.Markdown("### Reading - Nivel B1")
    gr.Markdown(TEXT)
    gr.Textbox(label=QUESTION)
